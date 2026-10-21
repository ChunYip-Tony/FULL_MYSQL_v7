from __future__ import annotations
import json, os, socket, threading, time, traceback, uuid
from datetime import datetime, timezone
from pathlib import Path
from db import db_conn, test_database
from ingest import audit_batch, release_batch
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3
from phase3_runtime import connection_diagnostics, clear_terminal_phase3_owner
from v7_ingest import API_PIPELINE, API_VERSION
from chatgpt_sheet_bridge import publish_chatgpt_snapshot, bridge_enabled, enqueue_chatgpt_publish
from price_history_analysis import HISTORY_CONTRACT

POLL=int(os.environ.get('FULLMYSQL_WORKER_POLL_SECONDS','5'))
HEARTBEAT_SECONDS=max(10,int(os.environ.get('FULLMYSQL_WORKER_HEARTBEAT_SECONDS','15')))
STALE_STARTED_SECONDS=max(90,int(os.environ.get('FULLMYSQL_WORKER_STALE_STARTED_SECONDS','180')))
VERSION_MISMATCH_GRACE_SECONDS=max(30,int(os.environ.get('FULLMYSQL_WORKER_VERSION_MISMATCH_GRACE_SECONDS','45')))
HEARTBEAT_WRITE_RETRIES=max(1,min(5,int(os.environ.get('FULLMYSQL_HEARTBEAT_WRITE_RETRIES','3'))))
HEARTBEAT_RETRY_SECONDS=max(1,min(5,int(os.environ.get('FULLMYSQL_HEARTBEAT_RETRY_SECONDS','2'))))
SAME_VERSION_STALE_RECOVERY_LIMIT=max(0,min(3,int(os.environ.get('FULLMYSQL_SAME_VERSION_STALE_RECOVERY_LIMIT','1'))))
BRIDGE_STAGE='CHATGPT_SHEET_PUBLISH'
WORKER=f"{socket.gethostname()}:{os.getpid()}"
WORKER_INSTANCE=uuid.uuid4().hex
RUNTIME_HEALTH_PATH=Path(os.environ.get('FULLMYSQL_WORKER_HEALTH_PATH','/tmp/fullmysql_worker_health.json'))
_RUNTIME_LOCK=threading.Lock()
_RUNTIME_STATE={'state':'STARTING','run_id':None,'stage':None}

class Phase3PauseRequested(RuntimeError):
    def __init__(self, stage:str|None=None):
        self.stage=stage
        super().__init__('PHASE3_PAUSE_REQUESTED')


class RunClaimInvalid(RuntimeError):
    def __init__(self, run_id:int, status:str, code_version:str):
        self.run_id=run_id
        self.status=status
        self.code_version=code_version
        super().__init__(f'RUN_CLAIM_INVALID:{run_id}:{status}:{code_version}')


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


def _touch_run(run_id:int, *, stage:str|None=None, progress_payload:dict|None=None) -> None:
    payload={
        'worker':WORKER,
        'worker_instance':WORKER_INSTANCE,
        'heartbeat_at':datetime.utcnow().isoformat()+'Z',
        'heartbeat_epoch':int(time.time()),
    }
    # Linux/container memory evidence survives a worker restart in run detail.
    try:
        import resource
        payload['worker_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        for key,path in (
            ('worker_cgroup_memory_bytes','/sys/fs/cgroup/memory.current'),
            ('worker_cgroup_memory_limit','/sys/fs/cgroup/memory.max'),
            ('worker_cgroup_v1_memory_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes'),
            ('worker_cgroup_v1_memory_limit','/sys/fs/cgroup/memory/memory.limit_in_bytes'),
        ):
            if Path(path).exists():
                payload[key]=Path(path).read_text().strip()
    except (OSError,ImportError):
        pass
    if stage:
        payload['phase3_stage']=stage
        # Row-count data belongs to the stage that emitted it. Clear it when a
        # later Phase 3 stage starts so the UI cannot keep showing a stale
        # Quick Check percentage during Analysis/Audit/Finalize.
        if not progress_payload:
            for key in (
                'progress_kind','progress_unit','progress_current','progress_total',
                'progress_pct','progress_ready','progress_hold','progress_historical',
                'progress_issue_counts','progress_elapsed_seconds',
                'progress_rows_per_second','progress_eta_seconds',
                'progress_current_upc','progress_current_name',
            ):
                payload[key]=None
    if progress_payload:
        for key,value in progress_payload.items():
            if key.startswith('progress_') or key == 'db_connection_id':
                payload[key]=value
    with _RUNTIME_LOCK:
        db_id = (_RUNTIME_STATE.get('db_connection_id')
                 if _RUNTIME_STATE.get('run_id') == run_id else None)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute('SET SESSION innodb_lock_wait_timeout=5')
            if db_id:
                payload.update(connection_diagnostics(cur, db_id))
            cur.execute(
                """UPDATE pipeline_run
                   SET detail_json=JSON_MERGE_PATCH(COALESCE(detail_json,JSON_OBJECT()),%s)
                   WHERE pipeline_run_id=%s
                     AND code_version=%s
                     AND processing_status IN ('STARTED','PAUSE_REQUESTED')""",
                (json.dumps(payload,ensure_ascii=False),run_id,API_VERSION),
            )
            updated=int(cur.rowcount or 0)
            conn.commit()
            if updated != 1:
                raise RuntimeError(f'HEARTBEAT_RUN_NOT_ACTIVE:{run_id}')
        finally:
            cur.close()


def _heartbeat_loop(run_id:int, stop_event:threading.Event) -> None:
    consecutive_failures=0
    while not stop_event.wait(HEARTBEAT_SECONDS):
        last_error=None
        for attempt in range(HEARTBEAT_WRITE_RETRIES):
            try:
                _touch_run(run_id)
                last_error=None
                consecutive_failures=0
                break
            except Exception as exc:
                last_error=exc
                if attempt+1 < HEARTBEAT_WRITE_RETRIES:
                    if stop_event.wait(HEARTBEAT_RETRY_SECONDS):
                        return
        if last_error is not None:
            consecutive_failures += 1
            print(
                'Pipeline heartbeat write failed',
                {
                    'run_id':run_id,
                    'consecutive_failures':consecutive_failures,
                    'error':repr(last_error),
                },
                flush=True,
            )
            # Keep local worker health truthful even when MySQL heartbeat writes
            # are temporarily unavailable. Recovery still relies on the DB lease,
            # but transient failures now get multiple write attempts first.
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['heartbeat_db_failures']=consecutive_failures
                _RUNTIME_STATE['heartbeat_db_error']=repr(last_error)
            _write_runtime_health()
        else:
            with _RUNTIME_LOCK:
                _RUNTIME_STATE.pop('heartbeat_db_failures',None)
                _RUNTIME_STATE.pop('heartbeat_db_error',None)


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
        'worker_instance':WORKER_INSTANCE,
        'pid':os.getpid(),
        'state':current.get('state'),
        'run_id':current.get('run_id'),
        'stage':current.get('stage'),
        'heartbeat_at':datetime.now(timezone.utc).isoformat(),
        'heartbeat_epoch':int(time.time()),
        'code_version':API_VERSION,
        'error':current.get('error'),
        'heartbeat_db_failures':current.get('heartbeat_db_failures',0),
        'heartbeat_db_error':current.get('heartbeat_db_error'),
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


def _heartbeat_age_seconds(detail:dict, started_at) -> float|None:
    heartbeat_epoch=detail.get('heartbeat_epoch')
    if heartbeat_epoch is not None:
        try:
            return max(0.0,time.time()-float(heartbeat_epoch))
        except Exception:
            pass
    if started_at is not None:
        try:
            return max(0.0,(datetime.utcnow()-started_at).total_seconds())
        except Exception:
            pass
    return None


def _next_run_number(cur,batch_id:int,stage_name:str) -> int:
    cur.execute(
        """SELECT COALESCE(MAX(run_number),0)+1 AS next_run
           FROM pipeline_run
           WHERE batch_id=%s
             AND pipeline_name=%s
             AND stage_name=%s""",
        (batch_id,API_PIPELINE,stage_name),
    )
    return int((cur.fetchone() or {}).get('next_run') or 1)


def _replacement_exists(cur,batch_id:int,stage_name:str) -> bool:
    cur.execute(
        """SELECT 1
           FROM pipeline_run
           WHERE batch_id=%s
             AND pipeline_name=%s
             AND stage_name=%s
             AND code_version=%s
             AND processing_status IN ('QUEUED','STARTED','PAUSE_REQUESTED')
           LIMIT 1""",
        (batch_id,API_PIPELINE,stage_name,API_VERSION),
    )
    return bool(cur.fetchone())


def _enqueue_current_version_replacement(
    cur,
    batch_id:int,
    stage_name:str,
    old_run_id:int,
    reason:str,
    *,
    extra_detail:dict|None=None,
) -> int|None:
    if _replacement_exists(cur,batch_id,stage_name):
        return None
    run_number=_next_run_number(cur,batch_id,stage_name)
    detail={
        'auto_recovery':True,
        'reason':reason,
        'supersedes_pipeline_run_id':old_run_id,
        'queued_at':datetime.now(timezone.utc).isoformat(),
        'required_code_version':API_VERSION,
    }
    if extra_detail:
        detail.update(extra_detail)
    cur.execute(
        """INSERT INTO pipeline_run
           (batch_id,pipeline_name,stage_name,run_number,
            processing_status,code_version,detail_json)
           VALUES (%s,%s,%s,%s,'QUEUED',%s,%s)""",
        (
            batch_id,
            API_PIPELINE,
            stage_name,
            run_number,
            API_VERSION,
            json.dumps(detail,ensure_ascii=False),
        ),
    )
    return int(cur.lastrowid)


def _phase3_result_publishable(cur,batch_id:int) -> bool:
    cur.execute(
        """SELECT ib.processing_status AS batch_status,
                  p3.result_status,p3.blocking_issue_count
           FROM ingest_batch ib
           LEFT JOIN phase3_batch_result p3 ON p3.batch_id=ib.batch_id
           WHERE ib.batch_id=%s
           LIMIT 1""",
        (batch_id,),
    )
    row=cur.fetchone() or {}
    allowed={'QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS'}
    return (
        str(row.get('batch_status') or '').upper() in allowed
        and str(row.get('result_status') or '').upper() in allowed
        and int(row.get('blocking_issue_count') or 0)==0
    )


def _recover_stale_started(cur) -> int:
    # Version is a lease boundary. A newer worker must never steal a run that
    # still has a fresh heartbeat from an older deployment. Once that heartbeat
    # expires, the old run is terminally superseded and a new current-version
    # run is queued. Same-version stale jobs never restart in place: the old
    # Run ID is terminal and at most one replacement Run ID is auto-created.
    cur.execute(
        """SELECT pipeline_run_id,batch_id,stage_name,processing_status,
                  started_at,code_version,detail_json
           FROM pipeline_run
           WHERE pipeline_name=%s
             AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN','CHATGPT_SHEET_PUBLISH')
             AND processing_status IN ('STARTED','PAUSE_REQUESTED')""",
        (API_PIPELINE,),
    )
    recovered=0
    for row in cur.fetchall():
        detail={}
        try:
            detail=json.loads(row.get('detail_json') or '{}')
        except Exception:
            detail={}
        previous_version=str(row.get('code_version') or '')
        version_mismatch=bool(previous_version and previous_version!=API_VERSION)
        age=_heartbeat_age_seconds(detail,row.get('started_at'))
        stale_after=VERSION_MISMATCH_GRACE_SECONDS if version_mismatch else STALE_STARTED_SECONDS
        stale=age is not None and age > stale_after
        if not stale:
            continue

        previous_status=str(row.get('processing_status') or '').upper()
        run_id=int(row['pipeline_run_id'])
        bid=int(row['batch_id'])
        stage_name=str(row['stage_name'])

        last_stage=str(detail.get('phase3_stage') or detail.get('last_phase3_stage') or '')
        if (
            version_mismatch
            and stage_name in {'POST_RAW_PIPELINE','PHASE3_RERUN'}
            and last_stage.startswith('CHATGPT_SHEET_')
            and _phase3_result_publishable(cur,bid)
        ):
            recovery_detail={
                **detail,
                'bridge_decoupled_recovery':True,
                'recovered_at':datetime.now(timezone.utc).isoformat(),
                'recovery_reason':'PHASE3_ALREADY_COMMITTED_BRIDGE_DECOUPLED',
                'previous_processing_status':previous_status,
                'previous_code_version':previous_version,
                'required_code_version':API_VERSION,
                'recovered_by_code_version':API_VERSION,
                'last_phase3_stage':last_stage,
            }
            cur.execute(
                """UPDATE pipeline_run
                   SET processing_status='COMPLETED',
                       completed_at=CURRENT_TIMESTAMP(6),
                       error_count=0,
                       detail_json=%s
                   WHERE pipeline_run_id=%s
                     AND processing_status=%s
                     AND code_version=%s""",
                (
                    json.dumps(recovery_detail,ensure_ascii=False,default=str),
                    run_id,
                    previous_status,
                    previous_version,
                ),
            )
            if int(cur.rowcount or 0):
                if bridge_enabled():
                    _enqueue_current_version_replacement(
                        cur,bid,BRIDGE_STAGE,run_id,'PHASE3_COMMITTED_BRIDGE_ASYNC_RECOVERY'
                    )
                recovered += 1
            continue

        if version_mismatch:
            recovery_detail={
                **detail,
                'superseded':True,
                'superseded_at':datetime.now(timezone.utc).isoformat(),
                'recovery_reason':'OLD_DEPLOYMENT_WORKER_HEARTBEAT_EXPIRED',
                'previous_processing_status':previous_status,
                'previous_code_version':previous_version,
                'required_code_version':API_VERSION,
                'recovered_by_code_version':API_VERSION,
                'previous_worker':detail.get('worker'),
                'previous_heartbeat_at':detail.get('heartbeat_at'),
                'previous_heartbeat_epoch':detail.get('heartbeat_epoch'),
                'last_phase3_stage':detail.get('phase3_stage') or detail.get('last_phase3_stage'),
            }
            cur.execute(
                """UPDATE pipeline_run
                   SET processing_status='FAILED',
                       completed_at=CURRENT_TIMESTAMP(6),
                       error_count=GREATEST(COALESCE(error_count,0),1),
                       detail_json=%s
                   WHERE pipeline_run_id=%s
                     AND processing_status=%s
                     AND code_version=%s""",
                (
                    json.dumps(recovery_detail,ensure_ascii=False,default=str),
                    run_id,
                    previous_status,
                    previous_version,
                ),
            )
            if int(cur.rowcount or 0):
                _enqueue_current_version_replacement(
                    cur,bid,stage_name,run_id,'SUPERSEDE_OLD_DEPLOYMENT_RUN'
                )
                recovered += 1
            continue

        prior_same_version_recoveries=detail.get('same_version_stale_recovery_count')
        try:
            prior_same_version_recoveries=int(prior_same_version_recoveries)
        except Exception:
            # Compatibility with runs created before the counter existed.
            prior_same_version_recoveries=1 if detail.get('recovered_stale_started') else 0

        terminal=prior_same_version_recoveries >= SAME_VERSION_STALE_RECOVERY_LIMIT
        recovery_detail={
            **detail,
            'recovered_stale_started':not terminal,
            'recovered_at':datetime.now(timezone.utc).isoformat(),
            'recovery_reason':(
                'WORKER_HEARTBEAT_STALE_RETRY_LIMIT'
                if terminal
                else 'WORKER_HEARTBEAT_STALE_NEW_RUN'
            ),
            'previous_processing_status':previous_status,
            'recovered_processing_status':'FAILED',
            'recovered_by_code_version':API_VERSION,
            'previous_worker':detail.get('worker'),
            'previous_heartbeat_at':detail.get('heartbeat_at'),
            'previous_heartbeat_epoch':detail.get('heartbeat_epoch'),
            'stale_age_seconds':age,
            'last_phase3_stage':detail.get('phase3_stage') or detail.get('last_phase3_stage'),
            'same_version_stale_recovery_count':prior_same_version_recoveries,
            'same_version_stale_recovery_limit':SAME_VERSION_STALE_RECOVERY_LIMIT,
            'auto_recovery_exhausted':terminal,
        }
        cur.execute(
            """UPDATE pipeline_run
               SET processing_status='FAILED',
                   completed_at=CURRENT_TIMESTAMP(6),
                   error_count=GREATEST(COALESCE(error_count,0),1),
                   detail_json=%s
               WHERE pipeline_run_id=%s
                 AND processing_status=%s
                 AND code_version=%s""",
            (
                json.dumps(recovery_detail,ensure_ascii=False,default=str),
                run_id,
                previous_status,
                API_VERSION,
            ),
        )
        changed=int(cur.rowcount or 0)
        if changed and not terminal:
            _enqueue_current_version_replacement(
                cur,
                bid,
                stage_name,
                run_id,
                'WORKER_HEARTBEAT_STALE_NEW_RUN',
                extra_detail={
                    'same_version_stale_recovery_count':prior_same_version_recoveries+1,
                    'same_version_stale_recovery_limit':SAME_VERSION_STALE_RECOVERY_LIMIT,
                    'previous_worker':detail.get('worker'),
                    'previous_heartbeat_at':detail.get('heartbeat_at'),
                    'last_phase3_stage':detail.get('phase3_stage') or detail.get('last_phase3_stage'),
                },
            )
        recovered += changed
    return recovered


def _supersede_incompatible_queued(cur) -> int:
    # QUEUED work is safe to supersede immediately because no worker owns it.
    cur.execute(
        """SELECT pipeline_run_id,batch_id,stage_name,code_version,detail_json
           FROM pipeline_run
           WHERE pipeline_name=%s
             AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN','CHATGPT_SHEET_PUBLISH')
             AND processing_status='QUEUED'
             AND COALESCE(code_version,'')<>%s""",
        (API_PIPELINE,API_VERSION),
    )
    superseded=0
    for row in cur.fetchall():
        run_id=int(row['pipeline_run_id'])
        bid=int(row['batch_id'])
        stage_name=str(row['stage_name'])
        detail={}
        try:
            detail=json.loads(row.get('detail_json') or '{}')
        except Exception:
            detail={}
        detail.update({
            'superseded':True,
            'superseded_at':datetime.now(timezone.utc).isoformat(),
            'recovery_reason':'QUEUED_CODE_VERSION_MISMATCH',
            'previous_code_version':str(row.get('code_version') or ''),
            'required_code_version':API_VERSION,
        })
        cur.execute(
            """UPDATE pipeline_run
               SET processing_status='FAILED',
                   completed_at=CURRENT_TIMESTAMP(6),
                   error_count=GREATEST(COALESCE(error_count,0),1),
                   detail_json=%s
               WHERE pipeline_run_id=%s
                 AND processing_status='QUEUED'""",
            (json.dumps(detail,ensure_ascii=False,default=str),run_id),
        )
        if int(cur.rowcount or 0):
            _enqueue_current_version_replacement(
                cur,bid,stage_name,run_id,'SUPERSEDE_QUEUED_VERSION_MISMATCH'
            )
            superseded += 1
    return superseded


def _queue_orphaned_phase2c_ready(cur) -> int:
    # A deployment can terminate the worker after Phase 2C committed but before
    # Phase 3 publishes a result. Any PHASE2C_READY batch with no Phase 3 result
    # and no currently active pipeline work must converge automatically.
    #
    # The previous rule refused to queue when ANY prior PHASE3_RERUN existed for
    # the current code version. That could strand a batch forever after a
    # terminal/aborted recovery attempt. Allow a new recovery unless there have
    # already been 3 terminal current-version recovery attempts, which prevents
    # an infinite failure loop while still making ordinary upload completion
    # automatic.
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
             AND (
                 SELECT COUNT(*)
                 FROM pipeline_run prior
                 WHERE prior.batch_id=ib.batch_id
                   AND prior.pipeline_name=%s
                   AND prior.stage_name='PHASE3_RERUN'
                   AND prior.code_version=%s
                   AND prior.processing_status IN ('FAILED','FAILED_QA','QA_HOLD','ABORTED','PAUSED','COMPLETED')
             ) < 3
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
            _supersede_incompatible_queued(cur)
            conn.commit()
            if not clear_terminal_phase3_owner(cur, API_PIPELINE):
                return None
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
                     AND processing_status='QUEUED'
                     AND code_version=%s""",
                (API_PIPELINE,API_VERSION),
            )
            queued=cur.fetchone() or {}
            queued_id=queued.get('pipeline_run_id')
            if queued_id is None:
                return None
            cur.execute(
                """SELECT pipeline_run_id,batch_id,stage_name,code_version
                   FROM pipeline_run
                   WHERE pipeline_run_id=%s
                     AND processing_status='QUEUED'
                     AND code_version=%s
                   FOR UPDATE""",
                (queued_id,API_VERSION),
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
                "detail_json=JSON_MERGE_PATCH(COALESCE(detail_json,JSON_OBJECT()),%s) "
                "WHERE pipeline_run_id=%s "
                "AND processing_status='QUEUED' "
                "AND code_version=%s",
                (
                    json.dumps({
                        'worker':WORKER,
                        'heartbeat_at':datetime.utcnow().isoformat()+'Z',
                        'heartbeat_epoch':int(time.time()),
                        'phase3_stage':'CLAIMED' if str(row['stage_name'])=='PHASE3_RERUN' else 'POST_RAW_CLAIMED',
                        'claimed_by_code_version':API_VERSION,
                    }),
                    row['pipeline_run_id'],
                    API_VERSION,
                ),
            )
            if int(cur.rowcount or 0) != 1:
                conn.rollback()
                return None
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

def _assert_run_claim_valid(run_id:int) -> None:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT processing_status,code_version FROM pipeline_run WHERE pipeline_run_id=%s",
                (run_id,),
            )
            row=cur.fetchone() or {}
        finally:
            cur.close()
    status=str(row.get('processing_status') or '').upper()
    code_version=str(row.get('code_version') or '')
    if status not in {'STARTED','PAUSE_REQUESTED'} or code_version!=API_VERSION:
        raise RunClaimInvalid(run_id,status,code_version)


def finish(run_id:int,status:str,detail:dict,error_count:int=0):
    with db_conn() as conn:
        cur=conn.cursor()
        cur.execute(
            """UPDATE pipeline_run
               SET processing_status=%s,
                   completed_at=CURRENT_TIMESTAMP(6),
                   error_count=%s,
                   detail_json=JSON_MERGE_PATCH(COALESCE(detail_json,JSON_OBJECT()),CAST(%s AS JSON))
               WHERE pipeline_run_id=%s
                 AND code_version=%s
                 AND processing_status IN ('STARTED','PAUSE_REQUESTED')""",
            (
                status,
                error_count,
                json.dumps(detail,ensure_ascii=False,default=str),
                run_id,
                API_VERSION,
            ),
        )
        conn.commit()
        cur.close()


def _queue_chatgpt_bridge_async(batch_id:int, source_run_id:int, reason:str) -> dict:
    if not bridge_enabled():
        return {'status':'DISABLED','batch_id':batch_id,'async_nonblocking':True}
    try:
        result=enqueue_chatgpt_publish(
            batch_id,
            pipeline_name=API_PIPELINE,
            code_version=API_VERSION,
            requested_by='FULL_MYSQL_WORKER',
            source_pipeline_run_id=source_run_id,
            reason=reason,
        )
        return {**result,'async_nonblocking':True}
    except Exception as exc:
        # Sheet publishing is secondary. Never fail or hold a committed MySQL
        # Quick Check snapshot because the external queue could not be written.
        return {
            'status':'QUEUE_FAILED',
            'batch_id':batch_id,
            'async_nonblocking':True,
            'error':repr(exc),
        }


def claim_bridge_job():
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True, buffered=True)
        lock_acquired=False
        try:
            cur.execute("SELECT GET_LOCK('fullmysql_v7_bridge_worker',0) ok")
            lock_row=cur.fetchone() or {}
            lock_acquired=int(lock_row.get('ok') or 0)==1
            if not lock_acquired:
                return None

            _recover_stale_started(cur)
            _supersede_incompatible_queued(cur)
            conn.commit()

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE pipeline_name=%s
                     AND stage_name=%s
                     AND processing_status IN ('STARTED','PAUSE_REQUESTED')
                     AND code_version=%s""",
                (API_PIPELINE,BRIDGE_STAGE,API_VERSION),
            )
            if int((cur.fetchone() or {}).get('c') or 0)>0:
                return None

            cur.execute(
                """SELECT MIN(pipeline_run_id) AS pipeline_run_id
                   FROM pipeline_run
                   WHERE pipeline_name=%s
                     AND stage_name=%s
                     AND processing_status='QUEUED'
                     AND code_version=%s""",
                (API_PIPELINE,BRIDGE_STAGE,API_VERSION),
            )
            queued_id=(cur.fetchone() or {}).get('pipeline_run_id')
            if queued_id is None:
                return None

            cur.execute(
                """SELECT pipeline_run_id,batch_id,code_version
                   FROM pipeline_run
                   WHERE pipeline_run_id=%s
                     AND stage_name=%s
                     AND processing_status='QUEUED'
                     AND code_version=%s
                   FOR UPDATE""",
                (queued_id,BRIDGE_STAGE,API_VERSION),
            )
            row=cur.fetchone()
            if not row:
                return None

            cur.execute(
                """UPDATE pipeline_run
                   SET processing_status='STARTED',
                       started_at=CURRENT_TIMESTAMP(6),
                       completed_at=NULL,
                       error_count=0,
                       detail_json=JSON_MERGE_PATCH(
                           COALESCE(detail_json,JSON_OBJECT()),%s
                       )
                   WHERE pipeline_run_id=%s
                     AND processing_status='QUEUED'
                     AND code_version=%s""",
                (
                    json.dumps({
                        'worker':WORKER,
                        'heartbeat_at':datetime.utcnow().isoformat()+'Z',
                        'heartbeat_epoch':int(time.time()),
                        'bridge_stage':'CLAIMED',
                        'claimed_by_code_version':API_VERSION,
                        'async_nonblocking':True,
                    }),
                    row['pipeline_run_id'],
                    API_VERSION,
                ),
            )
            if int(cur.rowcount or 0)!=1:
                conn.rollback()
                return None
            conn.commit()
            return int(row['pipeline_run_id']),int(row['batch_id'])
        except Exception:
            conn.rollback()
            raise
        finally:
            if lock_acquired:
                try:
                    cur.execute("SELECT RELEASE_LOCK('fullmysql_v7_bridge_worker') released")
                    cur.fetchone()
                except Exception:
                    pass
            try:
                cur.close()
            except Exception:
                pass


def process_bridge_job(run_id:int,batch_id:int) -> None:
    detail={
        'worker':WORKER,
        'batch_id':batch_id,
        'stage_name':BRIDGE_STAGE,
        'started_at':datetime.utcnow().isoformat()+'Z',
        'async_nonblocking':True,
    }
    stop_event=threading.Event()
    heartbeat=threading.Thread(target=_heartbeat_loop,args=(run_id,stop_event),daemon=True)
    heartbeat.start()
    try:
        _assert_run_claim_valid(run_id)
        _touch_run(run_id,stage='CHATGPT_SHEET_PUBLISH_ASYNC')
        result=publish_chatgpt_snapshot(batch_id)
        detail['publish_result']=result
        if str(result.get('status') or '').upper() in {'PASS','DISABLED'}:
            finish(run_id,'COMPLETED',detail,0)
        else:
            detail['error']='CHATGPT_SHEET_PUBLISH_FAILED'
            finish(run_id,'FAILED',detail,1)
    except RunClaimInvalid:
        return
    except Exception as exc:
        detail['error']=repr(exc)
        detail['traceback']=traceback.format_exc()
        finish(run_id,'FAILED',detail,1)
    finally:
        stop_event.set()
        heartbeat.join(timeout=2)


def _bridge_worker_loop(stop_event:threading.Event) -> None:
    while not stop_event.is_set():
        try:
            job=claim_bridge_job()
        except Exception as exc:
            print('Bridge worker claim error:',repr(exc),flush=True)
            stop_event.wait(max(2,POLL))
            continue
        if job:
            print('Processing async ChatGPT Sheet publish',job,flush=True)
            process_bridge_job(*job)
        else:
            stop_event.wait(max(2,POLL))



def process(run_id:int,batch_id:int,stage_name:str='POST_RAW_PIPELINE'):
    detail={'worker':WORKER,'batch_id':batch_id,'stage_name':stage_name,'started_at':datetime.utcnow().isoformat()+'Z'}
    last_progress_stage={'value':'STARTING'}
    stop_event=threading.Event()
    heartbeat=threading.Thread(target=_heartbeat_loop,args=(run_id,stop_event),daemon=True)
    heartbeat.start()

    def progress(stage:str, payload:dict|None=None):
        last_progress_stage['value']=stage
        if payload and payload.get('db_connection_id'):
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['db_connection_id']=int(payload['db_connection_id'])
        _assert_run_claim_valid(run_id)
        if _run_pause_requested(run_id):
            _write_runtime_health('PAUSING',run_id,stage)
            raise Phase3PauseRequested(stage)
        _write_runtime_health('BUSY',run_id,stage)
        try:
            _touch_run(run_id,stage=stage,progress_payload=payload)
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
            detail['chatgpt_sheet_bridge']=_queue_chatgpt_bridge_async(
                batch_id,run_id,'PHASE3_RERUN_COMPLETED'
            )
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
        detail['chatgpt_sheet_bridge']=_queue_chatgpt_bridge_async(
            batch_id,run_id,'POST_RAW_PIPELINE_COMPLETED'
        )
        finish(run_id,'COMPLETED',detail,0)
    except RunClaimInvalid as exc:
        detail['superseded']=True
        detail['superseded_at']=datetime.now(timezone.utc).isoformat()
        detail['superseded_status']=exc.status
        detail['superseded_code_version']=exc.code_version
        detail['required_code_version']=API_VERSION
        _write_runtime_health('SUPERSEDED',run_id,last_progress_stage.get('value'))
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
        with _RUNTIME_LOCK:
            _RUNTIME_STATE.pop('db_connection_id',None)
        _write_runtime_health('IDLE')

def _pending_pipeline_work() -> bool:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE pipeline_name=%s
                     AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                     AND processing_status IN ('QUEUED','STARTED','PAUSE_REQUESTED')""",
                (API_PIPELINE,),
            )
            row=cur.fetchone() or {}
            return int(row.get('c') or 0) > 0
        finally:
            cur.close()


def _startup_bridge_already_verified(cur, batch_id:int) -> bool:
    """Only reuse a verified publish newer than every current serving row.

    Checking the latest attempt also avoids hiding a later partial/failed
    publish behind an older PASS. Explicit post-Phase-3 publishes are unaffected.
    """
    cur.execute(
        """SELECT processing_status,completed_at,
                  JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.publish_result.status')) AS publish_status,
                  JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.publish_result.readback.pass')) AS readback_pass,
                  JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.publish_result.history_contract')) AS history_contract,
                  (SELECT MAX(published_at) FROM quick_check_current
                   WHERE publish_batch_id=%s) AS snapshot_updated_at
           FROM pipeline_run
           WHERE batch_id=%s AND pipeline_name=%s
             AND stage_name='CHATGPT_SHEET_PUBLISH'
           ORDER BY pipeline_run_id DESC LIMIT 1""",
        (batch_id,batch_id,API_PIPELINE),
    )
    row=cur.fetchone() or {}
    return bool(
        row.get('processing_status')=='COMPLETED'
        and row.get('publish_status')=='PASS'
        and row.get('history_contract')==HISTORY_CONTRACT
        and str(row.get('readback_pass')).lower()=='true'
        and row.get('completed_at') is not None
        and row.get('snapshot_updated_at') is not None
        and row['completed_at'] >= row['snapshot_updated_at']
    )


def _recover_chatgpt_bridge_on_startup() -> None:
    """Best-effort recovery for an interrupted ChatGPT Sheet publish.

    The publish operation is idempotent and already fail-closed. Re-running it
    for the one batch currently bound to quick_check_current lets a worker
    restart converge a stale PUBLISHING bridge state to PASS or a terminal
    FAILED state instead of leaving readers blocked indefinitely.
    """
    if not bridge_enabled():
        return
    try:
        with db_conn() as conn:
            cur=conn.cursor(dictionary=True)
            try:
                cur.execute(
                    """SELECT COUNT(*) AS c,
                              MIN(publish_batch_id) AS min_batch,
                              MAX(publish_batch_id) AS max_batch
                       FROM quick_check_current"""
                )
                serving=cur.fetchone() or {}
                if (int(serving.get('c') or 0)>0
                    and int(serving.get('min_batch') or 0)>0
                    and serving.get('min_batch')==serving.get('max_batch')
                    and _startup_bridge_already_verified(cur,int(serving['max_batch']))):
                    print('ChatGPT bridge startup recovery skipped: current snapshot already verified',
                          serving['max_batch'],flush=True)
                    return
            finally:
                cur.close()
        if int(serving.get('c') or 0) <= 0:
            return
        min_batch=int(serving.get('min_batch') or 0)
        max_batch=int(serving.get('max_batch') or 0)
        if min_batch <= 0 or min_batch != max_batch:
            print(
                'ChatGPT bridge startup recovery skipped: serving snapshot spans batches',
                serving,
                flush=True,
            )
            return
        result=enqueue_chatgpt_publish(
            max_batch,
            pipeline_name=API_PIPELINE,
            code_version=API_VERSION,
            requested_by='WORKER_STARTUP_RECOVERY',
            source_pipeline_run_id=None,
            reason='STARTUP_BRIDGE_RECOVERY',
        )
        print(
            'ChatGPT bridge startup recovery queued:',
            json.dumps(result,ensure_ascii=False,default=str),
            flush=True,
        )
    except Exception as exc:
        # Recovery must never prevent the worker from starting. The publisher
        # itself writes a terminal FAILED bridge status when possible.
        print('ChatGPT bridge startup recovery error:',repr(exc),flush=True)


def main():
    _write_runtime_health('STARTING')
    db=test_database(); print('FULL MYSQL v7 worker DB:',db,flush=True)

    # Start the runtime heartbeat BEFORE any best-effort startup repair. This
    # prevents a slow external ChatGPT-sheet publish from making the worker
    # look dead during deployment.
    runtime_stop=threading.Event()
    runtime_thread=threading.Thread(target=_runtime_heartbeat_loop,args=(runtime_stop,),daemon=True)
    runtime_thread.start()
    bridge_stop=threading.Event()
    bridge_thread=threading.Thread(target=_bridge_worker_loop,args=(bridge_stop,),daemon=True)
    bridge_thread.start()
    try:
        _write_runtime_health('STARTUP_RECOVERY')
        _recover_chatgpt_bridge_on_startup()
        _write_runtime_health('IDLE')
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
        bridge_stop.set()
        bridge_thread.join(timeout=2)
        runtime_stop.set()
        runtime_thread.join(timeout=2)
        _write_runtime_health('STOPPED')

if __name__=='__main__': main()


