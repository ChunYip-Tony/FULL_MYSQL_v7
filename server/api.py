from __future__ import annotations
import hmac, json, os, time
from datetime import date, datetime
from pathlib import Path
from decimal import Decimal
from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from pydantic import BaseModel
from config import get_settings
from db import db_conn, test_database
from data_coverage import required_daily_coverage
from ingest import recent_batches
from v7_ingest import API_PIPELINE, begin_batch, add_file, commit_batch, session_status, find_active_batch, abort_batch
from product_identity_audit import audit_product_identity
from maintenance_api import run_manual_authority_refresh, run_confirmed_uom_refresh, run_safe_cost_refresh, run_confirmed_cost_conversion_refresh, run_on_hand_repair, run_article_manual_roster_repair, run_operational_uom_quick_check_refresh
from uom_evidence_diagnostic import diagnose_uom_lineage
from global_cost_hold_diagnostic import diagnose_global_cost_holds
from quick_check_app import search_quick_check, get_quick_check_detail, submit_true_stock, submit_negative_stock_true_stock, cancel_true_stock, pending_dumping_discrepancies, negative_stock_queue, quick_check_lineage, ready_quick_checks_with_system_oh, diagnose_on_hand_lineage, inventory_position_diagnostic, inventory_rollforward_candidates
from movement_repair import repair_movement_history
from movement_snapshot_diagnostic import movement_same_day_compare
from coverage_backfill import diagnose_coverage_backfill
from current_work_verification import verify_current_work

VERSION='7.0.90-single-service'
app=FastAPI(title='FULL MYSQL Secure API',version=VERSION,docs_url=None,redoc_url=None)

def j(v):
    if isinstance(v,(date,datetime)): return v.isoformat()
    return str(v)

def device_from_auth(authorization: str|None):
    if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'Bearer token required')
    token=authorization.split(' ',1)[1].strip(); s=get_settings()
    for device,expected in s.api_tokens.items():
        if hmac.compare_digest(token,expected): return device
    raise HTTPException(401,'Invalid API token')

class BatchCreate(BaseModel):
    label: str|None=None

class ManualAuthorityRefreshRequest(BaseModel):
    confirm: str

class TrueStockSubmit(BaseModel):
    true_stock: Decimal
    uom: str

class TrueStockCancelRequest(BaseModel):
    confirm: str
    reason: str|None=None

@app.get('/healthz')
def healthz(): return {'ok':True,'version':VERSION}

@app.get('/v1/worker-health')
def worker_health(authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    path=Path(os.environ.get('FULLMYSQL_WORKER_HEALTH_PATH','/tmp/fullmysql_worker_health.json'))
    if not path.exists():
        return {
            'healthy':False,
            'reason':'WORKER_HEARTBEAT_FILE_MISSING',
            'path':str(path),
        }
    try:
        payload=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {
            'healthy':False,
            'reason':'WORKER_HEARTBEAT_FILE_UNREADABLE',
            'error':str(exc),
            'path':str(path),
        }
    epoch=payload.get('heartbeat_epoch')
    age_seconds=None
    try:
        age_seconds=max(0,int(time.time())-int(epoch))
    except Exception:
        pass
    healthy=age_seconds is not None and age_seconds <= 30
    return {
        **payload,
        'healthy':healthy,
        'heartbeat_age_seconds':age_seconds,
        'reason':None if healthy else 'WORKER_HEARTBEAT_STALE',
    }


@app.get('/v1/status')
def status(authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization)
    try: db=test_database(); cov=required_daily_coverage(lookback_days=35) if db.get('phase3_schema_ready') else None
    except Exception as exc: raise HTTPException(503,f'Database unavailable: {exc}')
    return json.loads(json.dumps({'version':VERSION,'device':device,'database':db,'active_batch':find_active_batch(),'coverage':cov,'recent_batches':recent_batches(12)},default=j))

@app.get('/v1/active')
def active(authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization); return {'active_batch':find_active_batch()}

@app.post('/v1/batches')
def create_batch(body:BatchCreate,authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization); r=begin_batch(device,body.label)
    if not r.get('created'): raise HTTPException(409,detail={'message':'Another ingest batch is active','active':r.get('active')})
    return r

@app.post('/v1/batches/{session_id}/files')
async def upload_file(session_id:str, file:UploadFile=File(...), authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization); s=get_settings(); data=await file.read()
    if len(data)>s.upload_limit_mb*1024*1024: raise HTTPException(413,f'File exceeds {s.upload_limit_mb} MB limit')
    try: return add_file(session_id,device,file.filename or 'upload.bin',data)
    except KeyError as exc: raise HTTPException(404,str(exc))
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post('/v1/batches/{session_id}/commit')
def commit(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization)
    try: return commit_batch(session_id,device)
    except KeyError as exc: raise HTTPException(404,str(exc))
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except Exception as exc: raise HTTPException(400,str(exc))


@app.post('/v1/batches/{session_id}/phase3-rerun')
def phase3_rerun(
    session_id:str,
    body:ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='RERUN_PHASE3_FOR_EXISTING_BATCH':
        raise HTTPException(
            400,
            "confirm must be RERUN_PHASE3_FOR_EXISTING_BATCH",
        )
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT batch_id,processing_status
                   FROM ingest_batch
                   WHERE batch_key=%s
                   LIMIT 1""",
                (session_id,),
            )
            b=cur.fetchone()
            if not b:
                raise HTTPException(404,'Batch session not found')
            if b['processing_status'] not in {
                'PHASE2C_READY',
                'PHASE3_QA_HOLD',
                'QUICK_CHECK_READY',
                'QUICK_CHECK_READY_WITH_HOLDS',
            }:
                raise HTTPException(
                    409,
                    f"Batch status {b['processing_status']} is not eligible for Phase 3 rerun",
                )
            bid=int(b['batch_id'])
            cur.execute(
                """SELECT pipeline_run_id,processing_status,code_version,
                          started_at,completed_at
                   FROM pipeline_run
                   WHERE batch_id=%s
                     AND pipeline_name=%s
                     AND stage_name='PHASE3_RERUN'
                     AND processing_status IN ('QUEUED','STARTED')
                   ORDER BY pipeline_run_id DESC
                   LIMIT 1""",
                (bid,API_PIPELINE),
            )
            existing=cur.fetchone()
            recovered_interrupted_run_id=None
            if existing:
                existing_status=str(existing['processing_status'])
                existing_version=str(existing.get('code_version') or '')
                if existing_status=='STARTED' and existing_version!=VERSION:
                    recovered_interrupted_run_id=int(existing['pipeline_run_id'])
                    cur.execute(
                        """UPDATE pipeline_run
                           SET processing_status='FAILED',
                               completed_at=CURRENT_TIMESTAMP(6),
                               error_count=GREATEST(COALESCE(error_count,0),1),
                               detail_json=JSON_SET(
                                   COALESCE(detail_json,JSON_OBJECT()),
                                   '$.deployment_interrupted',TRUE,
                                   '$.interrupted_run_code_version',%s,
                                   '$.recovered_by_code_version',%s,
                                   '$.recovery_reason','OLD_WORKER_RESTARTED_DURING_DEPLOYMENT'
                               )
                           WHERE pipeline_run_id=%s
                             AND processing_status='STARTED'""",
                        (
                            existing_version,
                            VERSION,
                            recovered_interrupted_run_id,
                        ),
                    )
                else:
                    return {
                        'batch_id':bid,
                        'session_id':session_id,
                        'queued':existing_status=='QUEUED',
                        'already_active':True,
                        'pipeline_run_id':int(existing['pipeline_run_id']),
                        'status':existing_status,
                        'code_version':existing_version,
                    }
            cur.execute(
                """SELECT COALESCE(MAX(run_number),0)+1 AS next_run
                   FROM pipeline_run
                   WHERE batch_id=%s
                     AND pipeline_name=%s
                     AND stage_name='PHASE3_RERUN'""",
                (bid,API_PIPELINE),
            )
            next_run=int((cur.fetchone() or {}).get('next_run') or 1)
            cur.execute(
                """INSERT INTO pipeline_run
                   (batch_id,pipeline_name,stage_name,run_number,
                    processing_status,code_version,detail_json)
                   VALUES (%s,%s,'PHASE3_RERUN',%s,'QUEUED',%s,%s)""",
                (
                    bid,
                    API_PIPELINE,
                    next_run,
                    VERSION,
                    json.dumps(
                        {
                            'requested_by':device,
                            'reason':'RERUN_EXISTING_PHASE3_AFTER_QA_POLICY_UPDATE',
                        }
                    ),
                ),
            )
            run_id=int(cur.lastrowid)
            conn.commit()
            return {
                'batch_id':bid,
                'session_id':session_id,
                'queued':True,
                'pipeline_run_id':run_id,
                'status':'QUEUED',
                'recovered_interrupted_run_id':recovered_interrupted_run_id,
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(500,f'Phase 3 rerun enqueue failed: {exc}')
        finally:
            cur.close()


@app.post('/v1/batches/{session_id}/abort')
def abort(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization); s=get_settings()
    try: return abort_batch(session_id,device,device in s.admin_devices)
    except KeyError as exc: raise HTTPException(404,str(exc))
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except Exception as exc: raise HTTPException(400,str(exc))

@app.get('/v1/batches/{session_id}')
def batch(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    try:
        return json.loads(json.dumps(session_status(session_id),default=j))
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Batch status failed: {exc}')


@app.get('/v1/batches/{session_id}/runs/{pipeline_run_id}')
def batch_run_detail(
    session_id:str,
    pipeline_run_id:int,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT ib.batch_id
                   FROM ingest_batch ib
                   WHERE ib.batch_key=%s
                   LIMIT 1""",
                (session_id,),
            )
            b=cur.fetchone()
            if not b:
                raise HTTPException(404,'Batch session not found')
            cur.execute(
                """SELECT pipeline_run_id,batch_id,pipeline_name,stage_name,run_number,
                          processing_status,started_at,completed_at,rows_inserted,
                          error_count,code_version,detail_json
                   FROM pipeline_run
                   WHERE pipeline_run_id=%s
                     AND batch_id=%s
                   LIMIT 1""",
                (pipeline_run_id,int(b['batch_id'])),
            )
            row=cur.fetchone()
            if not row:
                raise HTTPException(404,'Pipeline run not found for this batch')
            return json.loads(json.dumps(row,default=j))
        finally:
            cur.close()


@app.get('/v1/batches/{session_id}/runs/{pipeline_run_id}/summary')
def batch_run_summary(
    session_id:str,
    pipeline_run_id:int,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT ib.batch_id
                   FROM ingest_batch ib
                   WHERE ib.batch_key=%s
                   LIMIT 1""",
                (session_id,),
            )
            b=cur.fetchone()
            if not b:
                raise HTTPException(404,'Batch session not found')
            cur.execute(
                """SELECT pipeline_run_id,batch_id,pipeline_name,stage_name,run_number,
                          processing_status,started_at,completed_at,rows_inserted,
                          error_count,code_version,
                          JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.worker')) AS worker,
                          JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.heartbeat_at')) AS heartbeat_at,
                          JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.phase3_stage')) AS phase3_stage
                   FROM pipeline_run
                   WHERE pipeline_run_id=%s
                     AND batch_id=%s
                   LIMIT 1""",
                (pipeline_run_id,int(b['batch_id'])),
            )
            row=cur.fetchone()
            if not row:
                raise HTTPException(404,'Pipeline run not found for this batch')
            return json.loads(json.dumps(row,default=j))
        finally:
            cur.close()


@app.get('/v1/batches/{session_id}/qa-summary')
def batch_qa_summary(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT batch_id,processing_status FROM ingest_batch WHERE batch_key=%s LIMIT 1",(session_id,))
        b=cur.fetchone()
        if not b:
            cur.close()
            raise HTTPException(404,'Batch session not found')
        bid=int(b['batch_id'])

        def grouped(table, extra_where=''):
            cur.execute(
                f"""SELECT g.issue_code,g.severity,g.issue_count
                    FROM (
                        SELECT issue_code,UPPER(severity) AS severity,COUNT(*) AS issue_count
                        FROM {table}
                        WHERE batch_id=%s AND issue_status='OPEN' {extra_where}
                        GROUP BY issue_code,UPPER(severity)
                    ) AS g
                    ORDER BY FIELD(g.severity,'CRITICAL','HIGH','MEDIUM','LOW'),
                             g.issue_count DESC,g.issue_code""",
                (bid,),
            )
            return cur.fetchall()

        cur.execute(
            """SELECT result_status,blocking_issue_count,quick_check_rows,quick_check_ready_rows,
                      quick_check_hold_rows,detail_json,updated_at
               FROM phase3_batch_result WHERE batch_id=%s""",
            (bid,),
        )
        p3=cur.fetchone()
        p3_detail={}
        if p3:
            try:
                p3_detail=json.loads(p3.get('detail_json') or '{}')
            except Exception:
                p3_detail={}
            p3.pop('detail_json',None)

        # Reason-level CURRENT serving QA counts.
        # Source of truth is the serving snapshot itself so the returned
        # reason counts and UPC list always reconcile to current_hold_rows.
        cur.execute(
            """SELECT ean_upc,blocking_reason
               FROM quick_check_current
               WHERE quick_check_status='QA_HOLD'
               ORDER BY ean_upc"""
        )
        reason_counts={}
        hold_upcs=[]
        for row in cur.fetchall():
            raw_reason=str(row.get('blocking_reason') or '')
            reasons=[x.strip() for x in raw_reason.split(',') if x and x.strip()]
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason,0) + 1
            hold_upcs.append({'upc':str(row['ean_upc']),'reasons':reasons})

        # Remaining active sold-UPC identity issues.
        # HIGH/CRITICAL = real batch blockers.
        # MEDIUM + temporary_qa_waiver = explicitly waived, still unresolved.
        cur.execute(
            """SELECT entity_key,severity,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='SOLD_UPC_UNMAPPED'
               ORDER BY issue_id""",
            (bid,),
        )
        sold_unmapped=[]
        temporarily_waived_sold_unmapped=[]
        for row in cur.fetchall():
            try:
                detail=json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail={}
            item={
                'upc':str(row['entity_key']),
                'description':detail.get('description'),
                'activity_scope':detail.get('activity_scope'),
                'activity_basis':detail.get('activity_basis'),
                'repair_candidates':detail.get('v711_repair_candidates'),
                'multitab_repair':detail.get('v712_multitab_repair'),
                'multitab_candidates':detail.get('v712_cross_tab_candidates'),
                'cross_tab_signature_repair':detail.get('v713_cross_tab_signature_repair'),
                'temporary_qa_waiver':detail.get('temporary_qa_waiver'),
            }
            waiver=detail.get('temporary_qa_waiver') or {}
            is_waived=(
                isinstance(waiver,dict)
                and waiver.get('waiver_type')=='IDENTITY_PENDING'
                and waiver.get('non_blocking_current_readiness') is True
            )
            if is_waived:
                temporarily_waived_sold_unmapped.append(item)
            elif str(row.get('severity') or '').upper() in {'HIGH','CRITICAL'}:
                sold_unmapped.append(item)

        cur.execute(
            """SELECT entity_key,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='HISTORICAL_SOLD_UPC_UNMAPPED'
               ORDER BY issue_id""",
            (bid,),
        )
        historical_unmapped=[]
        for row in cur.fetchall():
            try:
                detail=json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail={}
            historical_unmapped.append({
                'upc':str(row['entity_key']),
                'description':detail.get('description'),
                'activity_scope':detail.get('activity_scope'),
                'activity_basis':detail.get('activity_basis'),
            })

        cur.execute(
            """SELECT
                   COUNT(*) AS serving_rows_total,
                   SUM(CASE WHEN quick_check_status='HISTORICAL_ONLY' THEN 1 ELSE 0 END) AS historical_rows,
                   SUM(CASE WHEN quick_check_status IN ('READY','QA_HOLD') THEN 1 ELSE 0 END) AS current_active_rows,
                   SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS current_ready_rows,
                   SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS current_hold_rows
               FROM quick_check_current"""
        )
        qc_scope=cur.fetchone() or {}
        qc_scope['hold_upc_list_count']=len(hold_upcs)
        qc_scope['hold_reason_row_parity']=(
            int(qc_scope.get('current_hold_rows') or 0) == len(hold_upcs)
        )

        result={
            'batch_id':bid,
            'processing_status':b['processing_status'],
            'phase2c_issue_counts':grouped('qa_identity_uom_issue'),
            'phase3_issue_counts':grouped('qa_phase3_issue'),
            'batch_blocking_issue_counts':grouped(
                'qa_phase3_issue',
                "AND UPPER(severity) IN ('HIGH','CRITICAL') AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'"
            ),
            'serving_issue_counts':grouped(
                'qa_phase3_issue',
                "AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'"
            ),
            'quick_check_reason_counts':reason_counts,
            'quick_check_scope':qc_scope,
            'current_active_cost_repair':p3_detail.get('current_active_cost_repair'),
            'product_identity_guard':p3_detail.get('product_identity_guard'),
            'sold_upc_unmapped':sold_unmapped,
            'temporarily_waived_sold_upc_unmapped':temporarily_waived_sold_unmapped,
            'historical_sold_upc_unmapped':historical_unmapped,
            'historical_nonblocking_issue_counts':grouped(
                'qa_phase3_issue',
                "AND issue_code='HISTORICAL_SOLD_UPC_UNMAPPED'"
            ),
            'quick_check_hold_upcs':hold_upcs,
            'phase3':p3,
        }
        cur.close()
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/operational-uom-quick-check-refresh')
def operational_uom_quick_check_refresh(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='REFRESH_OPERATIONAL_UOM_QUICK_CHECK_TARGETS':
        raise HTTPException(
            400,
            "confirm must be REFRESH_OPERATIONAL_UOM_QUICK_CHECK_TARGETS",
        )
    try:
        result=run_operational_uom_quick_check_refresh(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Operational-UOM targeted Quick Check refresh failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/article-manual-roster-repair')
def article_manual_roster_repair(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='REPAIR_ARTICLE_MANUAL_FORMATTED_UPCS_AND_REBUILD':
        raise HTTPException(
            400,
            "confirm must be REPAIR_ARTICLE_MANUAL_FORMATTED_UPCS_AND_REBUILD",
        )
    try:
        result=run_article_manual_roster_repair(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Article Manual roster repair failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/movement-history-repair')
def movement_history_repair(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='REPLAY_MOVEMENT_HISTORY_AND_REBUILD':
        raise HTTPException(
            400,
            "confirm must be REPLAY_MOVEMENT_HISTORY_AND_REBUILD",
        )
    try:
        result=repair_movement_history(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Movement history repair failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/on-hand-repair')
def on_hand_repair(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='REPARSE_ON_HAND_AND_REBUILD':
        raise HTTPException(
            400,
            "confirm must be REPARSE_ON_HAND_AND_REBUILD",
        )
    try:
        result=run_on_hand_repair(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'ON_HAND repair failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/confirmed-cost-conversion-refresh')
def confirmed_cost_conversion_refresh(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='APPLY_CONFIRMED_COST_CONVERSIONS_AND_REBUILD':
        raise HTTPException(
            400,
            "confirm must be APPLY_CONFIRMED_COST_CONVERSIONS_AND_REBUILD",
        )
    try:
        result=run_confirmed_cost_conversion_refresh(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Confirmed cost conversion refresh failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/safe-cost-refresh')
def safe_cost_refresh(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='APPLY_SAFE_COST_REPAIR_AND_REBUILD':
        raise HTTPException(
            400,
            "confirm must be APPLY_SAFE_COST_REPAIR_AND_REBUILD",
        )
    try:
        result=run_safe_cost_refresh(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Safe cost refresh failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/confirmed-uom-refresh')
def confirmed_uom_refresh(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='APPLY_CONFIRMED_UOM_AND_REBUILD':
        raise HTTPException(
            400,
            "confirm must be APPLY_CONFIRMED_UOM_AND_REBUILD",
        )
    try:
        result=run_confirmed_uom_refresh(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Confirmed UOM refresh failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/maintenance/manual-authority-refresh')
def manual_authority_refresh(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='APPLY_CONFIRMED_USER_AUTHORITY':
        raise HTTPException(
            400,
            "confirm must be APPLY_CONFIRMED_USER_AUTHORITY",
        )
    try:
        result=run_manual_authority_refresh(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Manual authority refresh failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/uom-lineage')
def uom_lineage_diagnostic(
    upc: str|None=None,
    only_holds: bool=True,
    authorization: Annotated[str|None,Header()]=None,
):
    """Read-only Selling-UOM evidence and safe-resolution diagnostic."""
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            try:
                result=diagnose_uom_lineage(cur,upc=upc,only_holds=only_holds)
            except Exception as exc:
                # This endpoint is itself a diagnostic. Return a structured
                # failure payload instead of hiding the failing stage behind
                # a generic HTTP 500.
                result={
                    'status':'FATAL_DIAGNOSTIC_ERROR',
                    'summary':{
                        'row_count':0,
                        'safe_to_auto_apply_count':0,
                        'needs_review_count':0,
                        'classification_counts':{},
                        'diagnostic_error_count':1,
                    },
                    'diagnostic_errors':[{
                        'stage':'top_level',
                        'error_type':type(exc).__name__,
                        'error':str(exc),
                    }],
                    'items':[],
                }
        finally:
            cur.close()
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/product-identity-audit')
def product_identity_audit(authorization: Annotated[str|None,Header()]=None):
    """Read-only audit of current authoritative product identity and Quick Check publishing state."""
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            result=audit_product_identity(cur)
        finally:
            cur.close()
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/cost-holds')
def global_cost_hold_diagnostic(
    upc: str|None=None,
    family_id: int|None=None,
    authorization: Annotated[str|None,Header()]=None,
):
    """Read-only global diagnostic for current Quick Check cost-related QA holds."""
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            try:
                result=diagnose_global_cost_holds(
                    cur,
                    upc=upc,
                    family_id=family_id,
                )
            except Exception as exc:
                result={
                    'status':'FATAL_DIAGNOSTIC_ERROR',
                    'scope':{'upc':upc,'family_id':family_id},
                    'summary':{
                        'all_current_hold_rows':0,
                        'cost_related_hold_rows':0,
                        'other_hold_rows':0,
                        'unique_cost_hold_families':0,
                        'current_cost_missing_count':0,
                        'cost_to_selling_uom_unresolved_count':0,
                        'safe_to_auto_resolve_cost_hold_count':0,
                        'needs_review_cost_hold_count':0,
                        'classification_counts':{},
                        'all_hold_reason_counts':{},
                        'diagnostic_error_count':1,
                    },
                    'diagnostic_errors':[{
                        'stage':'top_level',
                        'error_type':type(exc).__name__,
                        'error':str(exc),
                    }],
                    'items':[],
                }
        finally:
            cur.close()
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/cost-lineage')
def cost_lineage_diagnostic(
    family_id:int,
    authorization: Annotated[str|None,Header()]=None,
):
    """Read-only diagnostic endpoint for current cost lineage.

    v7.0.24 expands searches by confirmed family ARTICLE identity as well as
    family_id. This surfaces receipt/company/cost evidence whose derived family
    linkage is NULL or stale, without mutating any source or derived rows.
    """
    device_from_auth(authorization)

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)

        cur.execute(
            """SELECT family_id,main_article_number,family_description
               FROM product_family
               WHERE family_id=%s
               LIMIT 1""",
            (family_id,),
        )
        family=cur.fetchone()
        if not family:
            cur.close()
            raise HTTPException(404,'Family not found')

        cur.execute(
            """SELECT a.article_id,a.article_number
               FROM article a
               JOIN bridge_article_family baf
                 ON baf.article_id=a.article_id
                AND baf.mapping_status='CONFIRMED'
                AND baf.is_primary=TRUE
                AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               WHERE baf.family_id=%s
               ORDER BY a.article_id""",
            (family_id,),
        )
        family_articles=cur.fetchall()
        article_ids=[int(x['article_id']) for x in family_articles]
        article_numbers=[str(x['article_number']) for x in family_articles]

        cur.execute(
            """SELECT q.ean_upc,q.selling_description,q.article_number,
                      q.main_article_number,q.family_id,
                      q.selling_uom,q.base_uom,q.base_qty_per_selling_unit,
                      q.current_cost_per_base_uom,
                      q.current_cost_per_selling_unit,
                      q.cost_source,q.cost_date,
                      q.current_price,q.current_price_type,
                      q.pos_qty_7d,q.pos_qty_30d,
                      q.quick_check_status,q.blocking_reason,
                      CASE
                        WHEN q.quick_check_status='HISTORICAL_ONLY'
                          THEN 'HISTORICAL_ONLY'
                        ELSE 'CURRENT_ACTIVE'
                      END AS activity_scope
               FROM quick_check_current q
               WHERE q.family_id=%s
               ORDER BY
                 CASE q.quick_check_status
                   WHEN 'QA_HOLD' THEN 0
                   WHEN 'READY' THEN 1
                   WHEN 'HISTORICAL_ONLY' THEN 2
                   ELSE 3
                 END,
                 q.ean_upc""",
            (family_id,),
        )
        quick_check=cur.fetchall()

        if article_ids:
            ph=','.join(['%s']*len(article_ids))
            params=tuple([family_id]+article_ids)

            cur.execute(
                f"""SELECT company_price_observation_id,source_type,observation_date,
                           article_number,article_id,ean_upc,upc_id,family_id,
                           official_cost,cost_uom_code,
                           price_a,price_b,price_c,
                           batch_id,file_id,sheet_id,raw_id,source_row_number
                    FROM company_price_observation
                    WHERE family_id=%s OR article_id IN ({ph})
                    ORDER BY observation_date DESC,company_price_observation_id DESC
                    LIMIT 100""",
                params,
            )
            company_cost=cur.fetchall()

            cur.execute(
                f"""SELECT co.cost_observation_id,co.article_id,a.article_number,
                           co.family_id,co.cost_amount,co.cost_per_base_uom,
                           co.currency_code,
                           cu.uom_code AS cost_uom,
                           bu.uom_code AS base_uom,
                           co.source_type,co.movement_type,co.business_date,
                           co.cost_status,co.confidence,
                           co.batch_id,co.file_id,co.sheet_id,
                           co.raw_table_name,co.raw_id,co.source_row_number
                    FROM article_cost_observation co
                    LEFT JOIN article a ON a.article_id=co.article_id
                    LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
                    LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
                    WHERE co.family_id=%s OR co.article_id IN ({ph})
                    ORDER BY co.business_date DESC,co.cost_observation_id DESC
                    LIMIT 150""",
                params,
            )
            cost_observations=cur.fetchall()

            cur.execute(
                f"""SELECT article_number,article_id,family_id,description,
                           movement_type,posting_date,
                           entry_quantity,entry_uom_code,
                           base_quantity,base_uom_code,
                           amount_local_currency,
                           CASE
                             WHEN amount_local_currency IS NOT NULL
                              AND amount_local_currency<>0
                              AND base_quantity IS NOT NULL
                              AND base_quantity<>0
                             THEN ABS(amount_local_currency/base_quantity)
                             ELSE NULL
                           END AS derived_unit_cost,
                           article_document,purchase_order,vendor_code,
                           batch_id,file_id,sheet_id,raw_id,source_row_number
                    FROM movement_history
                    WHERE (family_id=%s OR article_id IN ({ph}))
                      AND movement_type IN ('101','107','109')
                    ORDER BY posting_date DESC,raw_id DESC
                    LIMIT 150""",
                params,
            )
            receipts=cur.fetchall()

            cur.execute(
                f"""SELECT
                      c.company_price_observation_id,
                      c.observation_date,
                      c.article_number AS company_article_number,
                      c.article_id AS company_article_id,
                      c.family_id AS company_family_id,
                      c.ean_upc,
                      c.official_cost,
                      c.cost_uom_code,
                      c.source_type AS company_source_type,
                      c.raw_id,
                      aco.cost_observation_id,
                      aco.article_id AS cost_article_id,
                      aco.family_id AS cost_family_id,
                      aco.cost_amount,
                      aco.cost_per_base_uom,
                      aco.source_type AS cost_source_type,
                      aco.raw_table_name
                    FROM company_price_observation c
                    LEFT JOIN article_cost_observation aco
                      ON aco.raw_id=c.raw_id
                     AND aco.file_id=c.file_id
                     AND aco.sheet_id=c.sheet_id
                    WHERE (c.family_id=%s OR c.article_id IN ({ph}))
                      AND c.official_cost IS NOT NULL
                      AND c.official_cost>0
                    ORDER BY c.observation_date DESC,c.company_price_observation_id DESC
                    LIMIT 150""",
                params,
            )
            official_raw_lineage=cur.fetchall()

            cur.execute(
                f"""SELECT
                      SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0 THEN 1 ELSE 0 END)
                        AS positive_official_cost_rows,
                      SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0
                                    AND cost_uom_code IS NOT NULL
                               THEN 1 ELSE 0 END)
                        AS positive_official_with_uom_rows,
                      COUNT(*) AS company_rows
                    FROM company_price_observation
                    WHERE family_id=%s OR article_id IN ({ph})""",
                params,
            )
            company_summary=cur.fetchone() or {}
        else:
            cur.execute(
                """SELECT company_price_observation_id,source_type,observation_date,
                          article_number,article_id,ean_upc,upc_id,family_id,
                          official_cost,cost_uom_code,
                          price_a,price_b,price_c,
                          batch_id,file_id,sheet_id,raw_id,source_row_number
                   FROM company_price_observation
                   WHERE family_id=%s
                   ORDER BY observation_date DESC,company_price_observation_id DESC
                   LIMIT 100""",
                (family_id,),
            )
            company_cost=cur.fetchall()

            cur.execute(
                """SELECT co.cost_observation_id,co.article_id,a.article_number,
                          co.family_id,co.cost_amount,co.cost_per_base_uom,
                          co.currency_code,
                          cu.uom_code AS cost_uom,
                          bu.uom_code AS base_uom,
                          co.source_type,co.movement_type,co.business_date,
                          co.cost_status,co.confidence,
                          co.batch_id,co.file_id,co.sheet_id,
                          co.raw_table_name,co.raw_id,co.source_row_number
                   FROM article_cost_observation co
                   LEFT JOIN article a ON a.article_id=co.article_id
                   LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
                   LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
                   WHERE co.family_id=%s
                   ORDER BY co.business_date DESC,co.cost_observation_id DESC
                   LIMIT 150""",
                (family_id,),
            )
            cost_observations=cur.fetchall()

            cur.execute(
                """SELECT article_number,article_id,family_id,description,
                          movement_type,posting_date,
                          entry_quantity,entry_uom_code,
                          base_quantity,base_uom_code,
                          amount_local_currency,
                          CASE
                            WHEN amount_local_currency IS NOT NULL
                             AND amount_local_currency<>0
                             AND base_quantity IS NOT NULL
                             AND base_quantity<>0
                            THEN ABS(amount_local_currency/base_quantity)
                            ELSE NULL
                          END AS derived_unit_cost,
                          article_document,purchase_order,vendor_code,
                          batch_id,file_id,sheet_id,raw_id,source_row_number
                   FROM movement_history
                   WHERE family_id=%s
                     AND movement_type IN ('101','107','109')
                   ORDER BY posting_date DESC,raw_id DESC
                   LIMIT 150""",
                (family_id,),
            )
            receipts=cur.fetchall()

            cur.execute(
                """SELECT
                     c.company_price_observation_id,c.observation_date,
                     c.article_number AS company_article_number,
                     c.article_id AS company_article_id,
                     c.family_id AS company_family_id,c.ean_upc,
                     c.official_cost,c.cost_uom_code,
                     c.source_type AS company_source_type,c.raw_id,
                     aco.cost_observation_id,aco.article_id AS cost_article_id,
                     aco.family_id AS cost_family_id,aco.cost_amount,
                     aco.cost_per_base_uom,aco.source_type AS cost_source_type,
                     aco.raw_table_name
                   FROM company_price_observation c
                   LEFT JOIN article_cost_observation aco
                     ON aco.raw_id=c.raw_id
                    AND aco.file_id=c.file_id
                    AND aco.sheet_id=c.sheet_id
                   WHERE c.family_id=%s
                     AND c.official_cost IS NOT NULL
                     AND c.official_cost>0
                   ORDER BY c.observation_date DESC,c.company_price_observation_id DESC
                   LIMIT 150""",
                (family_id,),
            )
            official_raw_lineage=cur.fetchall()

            cur.execute(
                """SELECT
                     SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0 THEN 1 ELSE 0 END)
                       AS positive_official_cost_rows,
                     SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0
                                   AND cost_uom_code IS NOT NULL
                              THEN 1 ELSE 0 END)
                       AS positive_official_with_uom_rows,
                     COUNT(*) AS company_rows
                   FROM company_price_observation
                   WHERE family_id=%s""",
                (family_id,),
            )
            company_summary=cur.fetchone() or {}

        cur.close()

    # Pure display diagnostic for suspicious short/long numeric UPC variants.
    def _upca_check_digit(first11:str) -> str | None:
        if len(first11)!=11 or not first11.isdigit():
            return None
        ds=[int(x) for x in first11]
        total=sum(ds[0::2])*3+sum(ds[1::2])
        return str((10-(total%10))%10)

    upcs=[str(x.get('ean_upc') or '') for x in quick_check]
    alias_checks=[]
    for u in upcs:
        if len(u)==11 and u.isdigit():
            expected=u+(_upca_check_digit(u) or '')
            longer=[x for x in upcs if len(x)==12 and x.startswith(u)]
            alias_checks.append({
                'short_upc':u,
                'expected_valid_upca':expected,
                'same_prefix_12_digit_rows':longer,
                'safe_append_check_digit_match': expected in longer,
            })

    return json.loads(json.dumps({
        'family':family,
        'family_articles':family_articles,
        'summary':{
            'company':company_summary,
            'quick_check_rows':len(quick_check),
            'article_cost_observation_rows':len(cost_observations),
            'receipt_101_107_109_rows':len(receipts),
            'official_raw_lineage_rows':len(official_raw_lineage),
            'search_scope':'FAMILY_ID_OR_CONFIRMED_ARTICLE_ID',
        },
        'quick_check':quick_check,
        'company_price_cost_evidence':company_cost,
        'article_cost_observations':cost_observations,
        'receipt_101_107_109_evidence':receipts,
        'official_cost_raw_lineage':official_raw_lineage,
        'upc_alias_checks':alias_checks,
        'family_article_numbers':article_numbers,
    },default=j))


@app.get('/v1/diagnostics/current-work-verification')
def current_work_verification(
    session_id:str|None=None,
    expected_version:str|None=None,
    focus_upc:str="74709410002",
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    try:
        result=verify_current_work(
            api_version=VERSION,
            expected_version=expected_version,
            session_id=session_id,
            focus_upc=focus_upc,
        )
    except Exception as exc:
        raise HTTPException(500,f'Current work verification failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/on-hand-lineage')
def diagnostics_on_hand_lineage(
    limit:int=50,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    return json.loads(json.dumps(diagnose_on_hand_lineage(limit),default=j))


@app.get('/v1/diagnostics/quick-check-lineage')
def diagnostics_quick_check_lineage(
    upc:str,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    result=quick_check_lineage(upc)
    if not result:
        raise HTTPException(404,'Quick Check UPC not found')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/quick-check/search')
def app_quick_check_search(q:str,limit:int=20,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    return json.loads(json.dumps(search_quick_check(q,limit),default=j))


@app.get('/v1/diagnostics/coverage-backfill')
def diagnostic_coverage_backfill(
    batch_id:int,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    try:
        return json.loads(json.dumps(diagnose_coverage_backfill(batch_id),default=j))
    except Exception as exc:
        raise HTTPException(500,f'Coverage backfill diagnostic failed: {exc}')


@app.get('/v1/diagnostics/movement-same-day-compare')
def diagnostic_movement_same_day_compare(
    date:str,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    try:
        result=movement_same_day_compare(date)
    except ValueError as exc:
        if str(exc)=='INVALID_MOVEMENT_DATE':
            raise HTTPException(422,detail={'status':'INVALID','reason':'INVALID_MOVEMENT_DATE','date':date})
        raise HTTPException(400,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Movement same-day comparison failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/inventory-rollforward-candidates')
def diagnostic_inventory_rollforward_candidates(
    date:str|None=None,
    limit:int=20,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    try:
        result=inventory_rollforward_candidates(date,limit)
    except ValueError as exc:
        if str(exc)=='INVALID_MOVEMENT_DATE':
            raise HTTPException(422,detail={'status':'INVALID','reason':'INVALID_MOVEMENT_DATE','date':date})
        raise HTTPException(400,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Inventory roll-forward candidate diagnostic failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/inventory-position')
def diagnostic_inventory_position(
    upc:str,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    try:
        result=inventory_position_diagnostic(upc)
    except KeyError:
        raise HTTPException(404,'Quick Check UPC not found')
    except Exception as exc:
        raise HTTPException(500,f'Inventory position diagnostic failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/inventory/negative-stock')
def app_negative_stock_queue(
    limit:int=100,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    return json.loads(json.dumps(negative_stock_queue(limit),default=j))


@app.post('/v1/app/inventory/negative-stock/{scope}/{owner_id}/true-stock')
def app_negative_stock_submit_true_stock(
    scope:str,
    owner_id:int,
    body:TrueStockSubmit,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    try:
        result=submit_negative_stock_true_stock(
            scope,
            owner_id,
            body.true_stock,
            body.uom,
            device,
        )
    except KeyError as exc:
        code=str(exc).strip("'")
        if code=='NEGATIVE_STOCK_ACTION_NOT_FOUND':
            raise HTTPException(
                404,
                detail={
                    'status':'NOT_FOUND',
                    'reason':code,
                    'inventory_owner_scope':scope.upper(),
                    'inventory_owner_id':owner_id,
                },
            )
        raise HTTPException(404,str(exc))
    except ValueError as exc:
        code=str(exc)
        if code in {
            'NEGATIVE_STOCK_OWNER_SCOPE_INVALID',
            'NEGATIVE_STOCK_ACTION_UPC_MISSING',
            'TRUE_STOCK_NEGATIVE',
            'TRUE_STOCK_UOM_REQUIRED',
        }:
            raise HTTPException(422,detail={'status':'INVALID','reason':code})
        if code.startswith('TRUE_STOCK_UOM_MISMATCH:'):
            required=code.split(':',1)[1]
            raise HTTPException(
                422,
                detail={
                    'status':'INVALID',
                    'reason':'TRUE_STOCK_UOM_MISMATCH',
                    'required_uom':required,
                },
            )
        if code in {
            'SYSTEM_OH_NOT_AVAILABLE',
            'SYSTEM_OH_LINEAGE_NOT_AVAILABLE',
            'SYSTEM_OH_SCOPE_UNRESOLVED',
            'SYSTEM_OH_ROLLFORWARD_BLOCKED',
            'FAMILY_ID_NOT_AVAILABLE',
        }:
            raise HTTPException(409,detail={'status':'BLOCKED','reason':code})
        raise HTTPException(400,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Negative-stock True Stock submit failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/quick-check/with-oh')
def app_quick_check_with_oh(
    limit:int=50,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    return json.loads(json.dumps(ready_quick_checks_with_system_oh(limit),default=j))


@app.get('/v1/app/quick-check/{upc}')
def app_quick_check_detail(upc:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    detail=get_quick_check_detail(upc)
    if not detail:
        raise HTTPException(404,'Quick Check UPC not found')
    return json.loads(json.dumps(detail,default=j))


@app.post('/v1/app/quick-check/{upc}/true-stock')
def app_submit_true_stock(
    upc:str,
    body:TrueStockSubmit,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    try:
        result=submit_true_stock(upc,body.true_stock,body.uom,device)
    except KeyError:
        raise HTTPException(404,'Quick Check UPC not found')
    except ValueError as exc:
        code=str(exc)
        if code in {
            'SYSTEM_OH_NOT_AVAILABLE',
            'SYSTEM_OH_LINEAGE_NOT_AVAILABLE',
            'SYSTEM_OH_SCOPE_UNRESOLVED',
            'SYSTEM_OH_ROLLFORWARD_BLOCKED',
            'FAMILY_ID_NOT_AVAILABLE',
        }:
            raise HTTPException(409,detail={'status':'BLOCKED','reason':code,'upc':upc})
        if code=='TRUE_STOCK_NEGATIVE':
            raise HTTPException(422,detail={'status':'INVALID','reason':code,'upc':upc})
        if code=='TRUE_STOCK_UOM_REQUIRED':
            raise HTTPException(422,detail={'status':'INVALID','reason':code,'upc':upc})
        if code.startswith('TRUE_STOCK_UOM_MISMATCH:'):
            required=code.split(':',1)[1]
            raise HTTPException(
                422,
                detail={
                    'status':'INVALID',
                    'reason':'TRUE_STOCK_UOM_MISMATCH',
                    'required_uom':required,
                    'upc':upc,
                },
            )
        raise HTTPException(400,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'True Stock submit failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/app/quick-check/{upc}/true-stock/cancel')
def app_cancel_true_stock(
    upc:str,
    body:TrueStockCancelRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='CANCEL_ACTIVE_TRUE_STOCK':
        raise HTTPException(400,'confirm must be CANCEL_ACTIVE_TRUE_STOCK')
    try:
        result=cancel_true_stock(upc,device,body.reason)
    except KeyError:
        raise HTTPException(404,'Quick Check UPC not found')
    except ValueError as exc:
        code=str(exc)
        if code in {
            'SYSTEM_OH_NOT_AVAILABLE',
            'SYSTEM_OH_LINEAGE_NOT_AVAILABLE',
            'FAMILY_ID_NOT_AVAILABLE',
            'NO_ACTIVE_TRUE_STOCK',
        }:
            raise HTTPException(409,detail={'status':'BLOCKED','reason':code,'upc':upc})
        raise HTTPException(400,str(exc))
    except RuntimeError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc),'upc':upc})
    except Exception as exc:
        raise HTTPException(500,f'True Stock cancel failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/dumping/pending')
def app_pending_dumping(authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    return json.loads(json.dumps({'rows':pending_dumping_discrepancies()},default=j))


@app.get('/v1/quick-check/{upc}')
def quick_check(upc:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization); q=''.join(ch for ch in upc if ch.isdigit()).lstrip('0') or '0'
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM quick_check_current WHERE ean_upc=%s OR TRIM(LEADING '0' FROM ean_upc)=%s LIMIT 1",(upc,q))
        row=cur.fetchone()
        if not row:
            cur.execute(
                """SELECT entity_key,severity,detail_json
                   FROM qa_phase3_issue
                   WHERE issue_status='OPEN'
                     AND issue_code='SOLD_UPC_UNMAPPED'
                     AND (entity_key=%s OR TRIM(LEADING '0' FROM entity_key)=%s)
                   ORDER BY batch_id DESC,issue_id DESC
                   LIMIT 1""",
                (upc,q),
            )
            unresolved=cur.fetchone()
            cur.close()
            if unresolved:
                try:
                    detail=json.loads(unresolved.get('detail_json') or '{}')
                except Exception:
                    detail={}
                waiver=detail.get('temporary_qa_waiver') or {}
                raise HTTPException(
                    409,
                    detail={
                        'status':'BLOCKED',
                        'reason':'IDENTITY_PENDING_TEMP_WAIVER' if waiver else 'SOLD_UPC_UNMAPPED',
                        'upc':str(unresolved['entity_key']),
                        'description':detail.get('description'),
                        'temporary_qa_waiver':waiver or None,
                    },
                )
            raise HTTPException(404,'Quick Check UPC not found')
        cur.close()
    return json.loads(json.dumps(row,default=j))
