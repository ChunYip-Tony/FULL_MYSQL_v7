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

VERSION='7.0.5-single-service'
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
        def grouped(table):
            cur.execute(
                f"""SELECT issue_code,UPPER(severity) severity,COUNT(*) issue_count
                    FROM {table}
                    WHERE batch_id=%s AND issue_status='OPEN'
                    GROUP BY issue_code,UPPER(severity)
                    ORDER BY FIELD(UPPER(severity),'CRITICAL','HIGH','MEDIUM','LOW'),issue_count DESC,issue_code""",
                (bid,),
            )
            return cur.fetchall()
        cur.execute("""SELECT result_status,blocking_issue_count,quick_check_rows,quick_check_ready_rows,
                              quick_check_hold_rows,updated_at
                       FROM phase3_batch_result WHERE batch_id=%s""",(bid,))
        p3=cur.fetchone()
        result={
            'batch_id':bid,
            'processing_status':b['processing_status'],
            'phase2c_issue_counts':grouped('qa_identity_uom_issue'),
            'phase3_issue_counts':grouped('qa_phase3_issue'),
            'phase3':p3,
        }
        cur.close()
    return json.loads(json.dumps(result,default=j))

@app.get('/v1/quick-check/{upc}')
def quick_check(upc:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization); q=''.join(ch for ch in upc if ch.isdigit()).lstrip('0') or '0'
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM quick_check_current WHERE ean_upc=%s OR TRIM(LEADING '0' FROM ean_upc)=%s LIMIT 1",(upc,q)); row=cur.fetchone(); cur.close()
    if not row: raise HTTPException(404,'Quick Check UPC not found')
    return json.loads(json.dumps(row,default=j))
