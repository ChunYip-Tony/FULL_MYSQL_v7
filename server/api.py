from __future__ import annotations
import hmac, json
from datetime import date, datetime
from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from pydantic import BaseModel
from config import get_settings
from db import db_conn, test_database
from data_coverage import required_daily_coverage
from ingest import recent_batches
from v7_ingest import begin_batch, add_file, commit_batch, session_status, find_active_batch, abort_batch

VERSION='7.0.14-single-service'
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

@app.get('/healthz')
def healthz(): return {'ok':True,'version':VERSION}

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
    try: return json.loads(json.dumps(session_status(session_id),default=j))
    except KeyError as exc: raise HTTPException(404,str(exc))


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
                      quick_check_hold_rows,updated_at
               FROM phase3_batch_result WHERE batch_id=%s""",
            (bid,),
        )
        p3=cur.fetchone()

        # Reason-level serving QA counts.
        cur.execute(
            """SELECT entity_key,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'
               ORDER BY issue_id""",
            (bid,),
        )
        reason_counts={}
        hold_upcs=[]
        for row in cur.fetchall():
            try:
                detail=json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail={}
            reasons=detail.get('reasons') or []
            for reason in reasons:
                reason_counts[str(reason)] = reason_counts.get(str(reason),0) + 1
            hold_upcs.append({'upc':str(row['entity_key']),'reasons':reasons})

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
