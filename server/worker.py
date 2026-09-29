from __future__ import annotations
import json, os, socket, threading, time, traceback
from datetime import datetime, timezone
from pathlib import Path
from db import db_conn, test_database
from ingest import audit_batch, release_batch
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3
from v7_ingest import API_PIPELINE, API_VERSION
from chatgpt_sheet_bridge import publish_chatgpt_snapshot, bridge_enabled, bridge_required

POLL=int(os.environ.get('FULLMYSQL_WORKER_POLL_SECONDS','5'))
HEARTBEAT_SECONDS=max(10,int(os.environ.get('FULLMYSQL_WORKER_HEARTBEAT_SECONDS','15')))
STALE_STARTED_SECONDS=max(90,int(os.environ.get('FULLMYSQL_WORKER_STALE_STARTED_SECONDS','180')))
WORKER=f"{socket.gethostname()}:{os.getpid()}"
RUNTIME_HEALTH_PATH=Path(os.environ.get('FULLMYSQL_WORKER_HEALTH_PATH','/tmp/fullmysql_worker_health.json'))
_RUNTIME_LOCK=threading.Lock()
_RUNTIME_STATE={'state':'STARTING','run_id':None,'stage':None}

class Phase3PauseRequested(RuntimeError):
    def __init__(self, stage:str|None=None):
        self.stage=stage
        super().__init__('PHASE3_PAUSE_REQUESTED')


def _run_pause_requested(run_id:int) -> bool:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT processing_status FROM pipeline_run WHERE pipeline_run_id=%s",
                (run_id,),
            )
            row=cur.fetchone() or {}
            return str(row.get('processing_status') or '').upper()=='PAUSE_REQUESTED'
        finally:
            cur.close()


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


def _set_runtime_state(state:str, run_id:int|None=None, stage:str|None=None) -> None:
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['state']=state
        _RUNTIME_STATE['run_id']=run_id
        _RUNTIME_STATE['stage']=stage
        if state != 'ERROR':
            _RUNTIME_STATE.pop('error',None)


def _write_runtime_health(state:str|None=None, run_id:int|None=None, stage:str|None=None) -> None:
    if state is not None:
        _set_runtime_state(state,run_id,stage)
    with _RUNTIME_LOCK:
        current=dict(_RUNTIME_STATE)
    payload={
        'worker':WORKER,
        'pid':os.getpid(),
        'state':current.get('state'),
        'run_id':current.get('run_id'),
        'stage':current.get('stage'),
        'heartbeat_at':datetime.now(timezone.utc).isoformat(),
        'heartbeat_epoch':int(time.time()),
        'code_version':API_VERSION,
        'error':current.get('error'),
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
    # STARTED jobs from an older deployment cannot still be owned by the
    # current worker, so recover them immediately. Same-version jobs continue
    # to use heartbeat age as the stale guard.
    cur.execute(
        """SELECT pipeline_run_id,batch_id,processing_status,started_at,code_version,detail_json
           FROM pipeline_run
           WHERE pipeline_name=%s
             AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
             AND processing_status IN ('STARTED','PAUSE_REQUESTED')""",
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
        previous_version=str(row.get('code_version') or '')
        deployment_interrupted=bool(previous_version and previous_version!=API_VERSION)
        heartbeat_epoch=detail.get('heartbeat_epoch')
        started_at=row.get('started_at')
        stale=deployment_interrupted
        if not stale and heartbeat_epoch is not None:
            try:
                stale=(now-float(heartbeat_epoch)) > STALE_STARTED_SECONDS
            except Exception:
                stale=False
        elif not stale and started_at is not None:
            try:
                stale=(datetime.utcnow()-started_at).total_seconds() > STALE_STARTED_SECONDS
            except Exception:
                stale=False
        if not stale:
            continue
        recovery_detail={
            'recovered_stale_started':True,
            'recovered_at':datetime.now(timezone.utc).isoformat(),
            'recovery_reason':(
                'OLD_DEPLOYMENT_WORKER_GONE'
                if deployment_interrupted
                else 'WORKER_HEARTBEAT_STALE'
            ),
            'previous_worker':detail.get('worker'),
            'previous_code_version':previous_version,
            'recovered_by_code_version':API_VERSION,
            'batch_id':row.get('batch_id'),
        }
        previous_status=str(row.get('processing_status') or '').upper()
        recovered_status='PAUSED' if previous_status=='PAUSE_REQUESTED' else 'QUEUED'
        recovery_detail['previous_processing_status']=previous_status
        recovery_detail['recovered_processing_status']=recovered_status
        cur.execute(
            """UPDATE pipeline_run
               SET processing_status=%s,
                   completed_at=CASE WHEN %s='PAUSED' THEN CURRENT_TIMESTAMP(6) ELSE NULL END,
                   error_count=0,
                   detail_json=%s
               WHERE pipeline_run_id=%s
                 AND processing_status=%s""",
            (
                recovered_status,
                recovered_status,
                json.dumps(recovery_detail,ensure_ascii=False,default=str),
                row['pipeline_run_id'],
                previous_status,
            ),
        )
        recovered += int(cur.rowcount or 0)
    return recovered


def _queue_orphaned_phase2c_ready(cur) -> int:
    # A deployment can terminate the worker after Phase 2C committed but before
    # Phase 3 started. If no active outer job and no prior Phase3 rerun exists,
    # enqueue at most one recovery run per deployed code version. Old-version
    # interrupted/failed reruns must not permanently strand a Phase2C-ready batch.
    cur.execute(
        """SELECT ib.batch_id
           FROM ingest_batch ib
           LEFT JOIN phase3_batch_result p3 ON p3.batch_id=ib.batch_id
           WHERE ib.processing_status='PHASE2C_READY'
             AND p3.batch_id IS NULL
             AND NOT EXISTS (
                 SELECT 1
                 FROM pipeline_run active
                 WHERE active.batch_id=ib.batch_id
                   AND active.pipeline_name=%s
                   AND active.stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                   AND active.processing_status IN ('QUEUED','STARTED','PAUSE_REQUESTED')
             )
             AND NOT EXISTS (
                 SELECT 1
                 FROM pipeline_run prior
                 WHERE prior.batch_id=ib.batch_id
                   AND prior.pipeline_name=%s
                   AND prior.stage_name='PHASE3_RERUN'
                   AND prior.code_version=%s
             )
           ORDER BY ib.batch_id""",
        (API_PIPELINE,API_PIPELINE,API_VERSION),
    )
    queued=0
    for row in cur.fetchall():
        bid=int(row['batch_id'])
        cur.execute(
            """SELECT COALESCE(MAX(run_number),0)+1 AS next_run
               FROM pipeline_run
               WHERE batch_id=%s
                 AND pipeline_name=%s
                 AND stage_name='PHASE3_RERUN'""",
            (bid,API_PIPELINE),
        )
        run_number=int((cur.fetchone() or {}).get('next_run') or 1)
        cur.execute(
            """INSERT INTO pipeline_run
               (batch_id,pipeline_name,stage_name,run_number,
                processing_status,code_version,detail_json)
               VALUES (%s,%s,'PHASE3_RERUN',%s,'QUEUED',%s,%s)""",
            (
                bid,
                API_PIPELINE,
                run_number,
                API_VERSION,
                json.dumps({
                    'auto_recovery':True,
                    'reason':'ORPHANED_PHASE2C_READY',
                    'queued_at':datetime.now(timezone.utc).isoformat(),
                },ensure_ascii=False),
            ),
        )
        queued += 1
    return queued


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
            _queue_orphaned_phase2c_ready(cur)
            conn.commit()

            cur.execute(
                "SELECT COUNT(*) c FROM pipeline_run "
                "WHERE pipeline_name=%s "
                "AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN') "
                "AND processing_status IN ('STARTED','PAUSE_REQUESTED')",
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


def _publish_chatgpt_bridge(batch_id:int, detail:dict, progress) -> bool:
    if not bridge_enabled():
        detail['chatgpt_sheet_bridge']={'status':'DISABLED'}
        return True
    progress('CHATGPT_SHEET_PUBLISH')
    result=publish_chatgpt_snapshot(batch_id)
    detail['chatgpt_sheet_bridge']=result
    if result.get('status')=='PASS':
        progress('CHATGPT_SHEET_READBACK_PASS')
        return True
    progress('CHATGPT_SHEET_READBACK_FAILED', result)
    return not bridge_required()

def process(run_id:int,batch_id:int,stage_name:str='POST_RAW_PIPELINE'):
    detail={'worker':WORKER,'batch_id':batch_id,'stage_name':stage_name,'started_at':datetime.utcnow().isoformat()+'Z'}
    last_progress_stage={'value':'STARTING'}
    stop_event=threading.Event()
    heartbeat=threading.Thread(target=_heartbeat_loop,args=(run_id,stop_event),daemon=True)
    heartbeat.start()

    def progress(stage:str, payload:dict|None=None):
        last_progress_stage['value']=stage
        if _run_pause_requested(run_id):
            _write_runtime_health('PAUSING',run_id,stage)
            raise Phase3PauseRequested(stage)
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
            if not _publish_chatgpt_bridge(batch_id,detail,progress):
                finish(run_id,'FAILED',detail,1)
                return
            finish(run_id,'COMPLETED',detail,0)
            return

        with db_conn() as status_conn:
            status_cur=status_conn.cursor(dictionary=True)
            status_cur.execute(
                "SELECT processing_status FROM ingest_batch WHERE batch_id=%s",
                (batch_id,),
            )
            status_row=status_cur.fetchone() or {}
            status_cur.close()
        batch_status=str(status_row.get('processing_status') or '')

        if batch_status=='PHASE2C_READY':
            detail['resume_from']='PHASE2C_READY'
            progress('PHASE3_RESUME_FROM_PHASE2C')
        else:
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
        if not _publish_chatgpt_bridge(batch_id,detail,progress):
            finish(run_id,'FAILED',detail,1); return
        finish(run_id,'COMPLETED',detail,0)
    except Phase3PauseRequested as exc:
        # process_phase3 rolls its transaction back before propagating this
        # cooperative stop. Keep the batch at PHASE2C_READY so Resume can
        # restart Phase 3 cleanly from canonical Phase 2C state.
        detail['paused']=True
        detail['paused_at']=datetime.now(timezone.utc).isoformat()
        detail['paused_stage']=exc.stage
        finish(run_id,'PAUSED',detail,0)
        _write_runtime_health('PAUSED',run_id,exc.stage)
    except Exception as exc:
        detail['failure_stage']=last_progress_stage.get('value')
        detail['last_phase3_stage']=last_progress_stage.get('value')
        detail['error']=repr(exc)
        detail['traceback']=traceback.format_exc()
        finish(run_id,'FAILED',detail,1)
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
                _set_runtime_state('ERROR',None,f'CLAIM_ERROR:{type(exc).__name__}')
                with _RUNTIME_LOCK:
                    _RUNTIME_STATE['error']=repr(exc)
                _write_runtime_health()
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
