from __future__ import annotations
import json, os, socket, time, traceback
from datetime import datetime
from db import db_conn, test_database
from ingest import audit_batch, release_batch
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3
from v7_ingest import API_PIPELINE

POLL=int(os.environ.get('FULLMYSQL_WORKER_POLL_SECONDS','5'))
WORKER=f"{socket.gethostname()}:{os.getpid()}"

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

            cur.execute(
                "SELECT COUNT(*) c FROM pipeline_run "
                "WHERE pipeline_name=%s AND stage_name='POST_RAW_PIPELINE' "
                "AND processing_status='STARTED'",
                (API_PIPELINE,),
            )
            if int((cur.fetchone() or {}).get('c') or 0) > 0:
                return None

            cur.execute(
                """SELECT pipeline_run_id,batch_id FROM pipeline_run
                   WHERE pipeline_name=%s
                     AND stage_name='POST_RAW_PIPELINE'
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
                "detail_json=%s "
                "WHERE pipeline_run_id=%s",
                (json.dumps({'worker':WORKER}), row['pipeline_run_id']),
            )
            conn.commit()
            return int(row['pipeline_run_id']), int(row['batch_id'])

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

def process(run_id:int,batch_id:int):
    detail={'worker':WORKER,'batch_id':batch_id,'started_at':datetime.utcnow().isoformat()+'Z'}
    try:
        a=audit_batch(batch_id); detail['raw_audit']=a
        if not a['pass']:
            finish(run_id,'QA_HOLD',detail,len(a.get('blocking_issues',[]))); return
        r=release_batch(batch_id); detail['raw_release']=r
        if not r.get('released'):
            finish(run_id,'FAILED',{**detail,'error':'RAW release failed'},1); return
        p2=normalize_batch(batch_id); a2=audit_phase2c(batch_id); detail['phase2c']=p2; detail['phase2c_audit']=a2
        if not a2['pass']:
            finish(run_id,'QA_HOLD',detail,len(a2.get('blocking_issues',[]))); return
        p3=process_phase3(batch_id); a3=audit_phase3(batch_id); detail['phase3']=p3; detail['phase3_audit']=a3
        if not a3['pass']:
            finish(run_id,'QA_HOLD',detail,len(a3.get('blocking_issues',[]))); return
        finish(run_id,'COMPLETED',detail,0)
    except Exception as exc:
        detail['error']=repr(exc); detail['traceback']=traceback.format_exc(); finish(run_id,'FAILED',detail,1)

def main():
    db=test_database(); print('FULL MYSQL v7 worker DB:',db,flush=True)
    while True:
        job=claim_job()
        if job:
            print('Processing',job,flush=True); process(*job)
        else: time.sleep(max(2,POLL))

if __name__=='__main__': main()
