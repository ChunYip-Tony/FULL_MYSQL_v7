from __future__ import annotations
import json, os, socket, threading, time, traceback
from datetime import datetime, timezone
from pathlib import Path
from db import db_conn, test_database
from ingest import audit_batch, release_batch
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3
from v7_ingest import API_PIPELINE, API_VERSION

POLL=int(os.environ.get('FULLMYSQL_WORKER_POLL_SECONDS','5'))
HEARTBEAT_SECONDS=max(10,int(os.environ.get('FULLMYSQL_WORKER_HEARTBEAT_SECONDS','15')))
STALE_STARTED_SECONDS=max(90,int(os.environ.get('FULLMYSQL_WORKER_STALE_STARTED_SECONDS','180')))
WORKER=f"{socket.gethostname()}:{os.getpid()}"
RUNTIME_HEALTH_PATH=Path(os.environ.get('FULLMYSQL_WORKER_HEALTH_PATH','/tmp/fullmysql_worker_health.json'))

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


def _write_runtime_health(state:str='IDLE', run_id:int|None=None, stage:str|None=None) -> None:
    payload={
        'worker':WORKER,
        'pid':os.getpid(),
        'state':state,
        'run_id':run_id,
        'stage':stage,
        'heartbeat_at':datetime.now(timezone.utc).isoformat(),
        'heartbeat_epoch':int(time.time()),
        'code_version':API_VERSION,
    }
    try:
        RUNTIME_HEALTH_PATH.parent.mkdir(parents=True,exist_ok=True)
        tmp=RUNTIME_HEALTH_PATH.with_suffix('.tmp')
        tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        tmp.replace(RUNTIME_HEALTH_PATH)
    except Exception:
        pass


def _runtime_heartbeat_loop(stop_event:threading.Event) -> None:
    while not stop_event.is_set():
        _write_runtime_health()
        stop_event.wait(10)


def _recover_stale_started(cur) -> int:
    # Inspect only the tiny set of currently STARTED outer API jobs. Parse the
    # heartbeat in Python instead of JSON_EXTRACT/JSON_SET so recovery does not
    # depend on MySQL JSON execution or large sort buffers.
    cur.execute(
        """SELECT pipeline_run_id,started_at,code_version,detail_json
           FROM pipeline_run
           WHERE pipeline_name=%s
             AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
             AND processing_status='STARTED'""",
        (API_PIPELINE,),
    )
    now=time.time()
    recovered=0
    for row in cur.fetchall():
        detail={}
        try:
            detail=json.loads(row.get('detail_json') or '{}')
        except Exception:
            detail={}
        heartbeat_epoch=detail.get('heartbeat_epoch')
        started_at=row.get('started_at')
        stale=False
        if heartbeat_epoch is not None:
            try:
                stale=(now-float(heartbeat_epoch)) > STALE_STARTED_SECONDS
            except Exception:
                stale=False
        elif started_at is not None:
            try:
                stale=(datetime.utcnow()-started_at).total_seconds() > STALE_STARTED_SECONDS
            except Exception:
                stale=False
        if not stale:
            continue
        recovery_detail={
            'recovered_stale_started':True,
            'recovered_at':datetime.now(timezone.utc).isoformat(),
            'recovery_reason':'WORKER_HEARTBEAT_STALE',
            'previous_worker':detail.get('worker'),
            'previous_code_version':row.get('code_version'),
        }
        cur.execute(
            """UPDATE pipeline_run
               SET processing_status='QUEUED',
                   started_at=NULL,
                   completed_at=NULL,
                   error_count=0,
                   detail_json=%s
               WHERE pipeline_run_id=%s
                 AND processing_status='STARTED'""",
            (json.dumps(recovery_detail,ensure_ascii=False,default=str),row['pipeline_run_id']),
        )
        recovered += int(cur.rowcount or 0)
    return recovered


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
                """SELECT MIN(pipeline_run_id) AS pipeline_run_id
                   FROM pipeline_run
                   WHERE pipeline_name=%s
                     AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                     AND processing_status='QUEUED'""",
                (API_PIPELINE,),
            )
            queued=cur.fetchone() or {}
            queued_id=queued.get('pipeline_run_id')
            if queued_id is None:
                return None
            cur.execute(
                """SELECT pipeline_run_id,batch_id,stage_name
                   FROM pipeline_run
                   WHERE pipeline_run_id=%s
                     AND processing_status='QUEUED'
                   FOR UPDATE""",
                (queued_id,),
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
        _write_runtime_health('BUSY',run_id,stage)
        try:
            _touch_run(run_id,stage=stage)
        except Exception:
            pass

    try:
        _write_runtime_health('BUSY',run_id,'STARTING')
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
        _write_runtime_health('IDLE')

def main():
    _write_runtime_health('STARTING')
    db=test_database(); print('FULL MYSQL v7 worker DB:',db,flush=True)
    runtime_stop=threading.Event()
    runtime_thread=threading.Thread(target=_runtime_heartbeat_loop,args=(runtime_stop,),daemon=True)
    runtime_thread.start()
    try:
        while True:
            try:
                job=claim_job()
            except Exception as exc:
                _write_runtime_health('ERROR',stage=f'CLAIM_ERROR:{type(exc).__name__}')
                print('Worker claim error:',repr(exc),flush=True)
                time.sleep(max(2,POLL))
                continue
            if job:
                print('Processing',job,flush=True); process(*job)
            else:
                _write_runtime_health('IDLE')
                time.sleep(max(2,POLL))
    finally:
        runtime_stop.set()
        runtime_thread.join(timeout=2)
        _write_runtime_health('STOPPED')

if __name__=='__main__': main()
