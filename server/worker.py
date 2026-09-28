from __future__ import annotations
import json, os, socket, threading, time, traceback
from datetime import datetime
from db import db_conn, test_database
from ingest import audit_batch, release_batch
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3
from v7_ingest import API_PIPELINE, API_VERSION

POLL=int(os.environ.get('FULLMYSQL_WORKER_POLL_SECONDS','5'))
HEARTBEAT_SECONDS=max(10,int(os.environ.get('FULLMYSQL_WORKER_HEARTBEAT_SECONDS','15')))
STALE_STARTED_SECONDS=max(90,int(os.environ.get('FULLMYSQL_WORKER_STALE_STARTED_SECONDS','180')))
WORKER=f"{socket.gethostname()}:{os.getpid()}"

def _touch_run(run_id:int, *, stage:str|None=None) -> None:
    payload={
        'worker':WORKER,
        'heartbeat_at':datetime.utcnow().isoformat()+'Z',
        'heartbeat_epoch':int(time.time()),
    }
    if stage:
        payload['phase3_stage']=stage
    with db_conn() as conn:
        cur=conn.cursor()
        try:
            cur.execute(
                """UPDATE pipeline_run
                   SET detail_json=JSON_MERGE_PATCH(COALESCE(detail_json,JSON_OBJECT()),%s)
                   WHERE pipeline_run_id=%s""",
                (json.dumps(payload,ensure_ascii=False),run_id),
            )
            conn.commit()
        finally:
            cur.close()


def _heartbeat_loop(run_id:int, stop_event:threading.Event) -> None:
    while not stop_event.wait(HEARTBEAT_SECONDS):
        try:
            _touch_run(run_id)
        except Exception:
            # Heartbeat must never kill the worker's business transaction.
            pass


def _recover_stale_started(cur) -> int:
    # A healthy in-process job receives a heartbeat every HEARTBEAT_SECONDS.
    # If the worker/container dies, the outer run can otherwise remain STARTED
    # forever and block every later queue claim. Requeue only demonstrably stale
    # runs; Phase 3 itself commits atomically, so an interrupted business
    # transaction is rolled back by MySQL before this retry.
    cur.execute(
        """UPDATE pipeline_run
           SET processing_status='QUEUED',
               started_at=NULL,
               completed_at=NULL,
               error_count=0,
               detail_json=JSON_SET(
                   COALESCE(detail_json,JSON_OBJECT()),
                   '$.recovered_stale_started',TRUE,
                   '$.recovered_at',%s,
                   '$.recovery_reason','WORKER_HEARTBEAT_STALE'
               )
           WHERE pipeline_name=%s
             AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
             AND processing_status='STARTED'
             AND (
                 (
                   JSON_EXTRACT(detail_json,'$.heartbeat_epoch') IS NOT NULL
                   AND CAST(JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.heartbeat_epoch')) AS UNSIGNED)
                       < UNIX_TIMESTAMP()- %s
                 )
                 OR
                 (
                   JSON_EXTRACT(detail_json,'$.heartbeat_epoch') IS NULL
                   AND started_at < CURRENT_TIMESTAMP(6)-INTERVAL %s SECOND
                 )
             )""",
        (
            datetime.utcnow().isoformat()+'Z',
            API_PIPELINE,
            STALE_STARTED_SECONDS,
            STALE_STARTED_SECONDS,
        ),
    )
    return int(cur.rowcount or 0)


def claim_job():
    # The MySQL named lock is connection-scoped.  Keep acquisition, job claim,
    # and release on the same connection, and ALWAYS consume SELECT results.
    # Connector/Python raises InternalError("Unread result found") if a SELECT
    # result (including RELEASE_LOCK()) is left unread when the cursor closes
    # or another statement is executed.
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True, buffered=True)
        lock_acquired=False
        try:
            cur.execute("SELECT GET_LOCK('fullmysql_v7_worker',0) ok")
            lock_row=cur.fetchone() or {}
            lock_acquired = int(lock_row.get('ok') or 0) == 1
            if not lock_acquired:
                return None

            _recover_stale_started(cur)
            conn.commit()

            cur.execute(
                "SELECT COUNT(*) c FROM pipeline_run "
                "WHERE pipeline_name=%s "
                "AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN') "
                "AND processing_status='STARTED'",
                (API_PIPELINE,),
            )
            if int((cur.fetchone() or {}).get('c') or 0) > 0:
                return None

            cur.execute(
                """SELECT pipeline_run_id,batch_id,stage_name FROM pipeline_run
                   WHERE pipeline_name=%s
                     AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                     AND processing_status='QUEUED'
                   ORDER BY pipeline_run_id
                   LIMIT 1
                   FOR UPDATE""",
                (API_PIPELINE,),
            )
            row=cur.fetchone()
            if not row:
                return None

            cur.execute(
                "UPDATE pipeline_run "
                "SET processing_status='STARTED',"
                "started_at=CURRENT_TIMESTAMP(6),"
                "completed_at=NULL,"
                "error_count=0,"
                "code_version=%s,"
                "detail_json=%s "
                "WHERE pipeline_run_id=%s",
                (
                    API_VERSION,
                    json.dumps({
                        'worker':WORKER,
                        'heartbeat_at':datetime.utcnow().isoformat()+'Z',
                        'heartbeat_epoch':int(time.time()),
                        'phase3_stage':'CLAIMED' if str(row['stage_name'])=='PHASE3_RERUN' else 'POST_RAW_CLAIMED',
                    }),
                    row['pipeline_run_id'],
                ),
            )
            conn.commit()
            return int(row['pipeline_run_id']), int(row['batch_id']), str(row['stage_name'])

        except Exception:
            conn.rollback()
            raise

        finally:
            if lock_acquired:
                try:
                    cur.execute("SELECT RELEASE_LOCK('fullmysql_v7_worker') released")
                    cur.fetchone()  # consume result; required by Connector/Python
                except Exception:
                    pass
            try:
                cur.close()
            except Exception:
                pass

def finish(run_id:int,status:str,detail:dict,error_count:int=0):
    with db_conn() as conn:
        cur=conn.cursor(); cur.execute("UPDATE pipeline_run SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6),error_count=%s,detail_json=%s WHERE pipeline_run_id=%s",
            (status,error_count,json.dumps(detail,ensure_ascii=False,default=str),run_id)); conn.commit(); cur.close()

def process(run_id:int,batch_id:int,stage_name:str='POST_RAW_PIPELINE'):
    detail={'worker':WORKER,'batch_id':batch_id,'stage_name':stage_name,'started_at':datetime.utcnow().isoformat()+'Z'}
    stop_event=threading.Event()
    heartbeat=threading.Thread(target=_heartbeat_loop,args=(run_id,stop_event),daemon=True)
    heartbeat.start()

    def progress(stage:str, payload:dict|None=None):
        try:
            _touch_run(run_id,stage=stage)
        except Exception:
            pass

    try:
        progress('STARTING')
        if stage_name == 'PHASE3_RERUN':
            p3=process_phase3(batch_id,progress=progress)
            progress('PHASE3_AUDIT')
            a3=audit_phase3(batch_id)
            detail['phase3']=p3
            detail['phase3_audit']=a3
            if not a3['pass']:
                finish(run_id,'QA_HOLD',detail,len(a3.get('blocking_issues',[])))
                return
            finish(run_id,'COMPLETED',detail,0)
            return

        a=audit_batch(batch_id); detail['raw_audit']=a
        if not a['pass']:
            finish(run_id,'QA_HOLD',detail,len(a.get('blocking_issues',[]))); return
        r=release_batch(batch_id); detail['raw_release']=r
        if not r.get('released'):
            finish(run_id,'FAILED',{**detail,'error':'RAW release failed'},1); return
        p2=normalize_batch(batch_id); a2=audit_phase2c(batch_id); detail['phase2c']=p2; detail['phase2c_audit']=a2
        if not a2['pass']:
            finish(run_id,'QA_HOLD',detail,len(a2.get('blocking_issues',[]))); return
        p3=process_phase3(batch_id,progress=progress)
        progress('PHASE3_AUDIT')
        a3=audit_phase3(batch_id); detail['phase3']=p3; detail['phase3_audit']=a3
        if not a3['pass']:
            finish(run_id,'QA_HOLD',detail,len(a3.get('blocking_issues',[]))); return
        finish(run_id,'COMPLETED',detail,0)
    except Exception as exc:
        detail['error']=repr(exc); detail['traceback']=traceback.format_exc(); finish(run_id,'FAILED',detail,1)
    finally:
        stop_event.set()
        heartbeat.join(timeout=2)

def main():
    db=test_database(); print('FULL MYSQL v7 worker DB:',db,flush=True)
    while True:
        job=claim_job()
        if job:
            print('Processing',job,flush=True); process(*job)
        else: time.sleep(max(2,POLL))

if __name__=='__main__': main()
