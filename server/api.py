from __future__ import annotations
import base64, hashlib, hmac, json, os, time
from datetime import date, datetime
from pathlib import Path
from decimal import Decimal
from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from config import get_settings
from db import db_conn, test_database
from data_coverage import required_daily_coverage
from ingest import recent_batches
from v7_ingest import API_PIPELINE, begin_batch, add_file, commit_batch, session_status, find_active_batch, abort_batch
from product_identity_audit import audit_product_identity
from maintenance_api import run_manual_authority_refresh, run_confirmed_uom_refresh, run_safe_cost_refresh, run_confirmed_cost_conversion_refresh, run_on_hand_repair, run_article_manual_roster_repair, run_operational_uom_quick_check_refresh, run_cost_authority_refresh
from uom_evidence_diagnostic import diagnose_uom_lineage
from global_cost_hold_diagnostic import diagnose_global_cost_holds, diagnose_oh_cost_schema
from quick_check_app import search_quick_check, get_quick_check_detail, submit_true_stock, submit_negative_stock_true_stock, cancel_true_stock, pending_dumping_discrepancies, negative_stock_queue, quick_check_lineage, ready_quick_checks_with_system_oh, diagnose_on_hand_lineage, inventory_position_diagnostic, inventory_rollforward_candidates, ordering_queue, price_change_queue, resolve_dumping_discrepancy, list_ordering_policies, upsert_ordering_policy, price_change_preview, create_price_change_proposal, list_price_change_proposals, review_price_change_proposal, mark_price_change_executed, dumping_discrepancy_history, operational_dashboard, add_order_recommendation_to_draft, update_order_draft_line, order_draft_history, transition_order_draft, order_delivery_reconciliation, update_order_external_reference
from movement_repair import repair_movement_history
from movement_snapshot_diagnostic import movement_same_day_compare
from coverage_backfill import diagnose_coverage_backfill
from current_work_verification import verify_current_work
from cost_backfill_queue import cost_backfill_queue
from web_quick_check import quick_check_web_html
from web_admin import admin_web_html
from webapp_v2_ui import webapp_v2_html
from webapp_v2_runtime import search_items as v2_search_items, family_info as v2_family_info, upc_info as v2_upc_info, price_analysis as v2_price_analysis, ordering_analysis as v2_ordering_analysis, family_promotion_history as v2_family_promotion_history, pi_search_items as v2_pi_search_items, pi_item as v2_pi_item, submit_family_true_stock as v2_submit_family_true_stock, performance_report as v2_performance_report, latest_performance_date as v2_latest_performance_date, performance_supported_dates as v2_performance_supported_dates

VERSION='7.0.133-single-service'
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

def public_app_actor(authorization: str|None):
    """Allow the public Quick Check web app to work without a manually entered API token.

    If a valid Bearer token is supplied by an existing trusted client, retain its
    device identity. Anonymous browser users are recorded as PUBLIC-WEB.
    Administrative, ingest, maintenance, and diagnostic endpoints continue to
    use device_from_auth() and remain protected.
    """
    if not authorization:
        return 'PUBLIC-WEB'
    return device_from_auth(authorization)

def _admin_login_id() -> str:
    return os.environ.get('FULLMYSQL_ADMIN_LOGIN_ID','admin').strip() or 'admin'

def _verify_pbkdf2_password(password: str, encoded: str) -> bool:
    """Verify pbkdf2_sha256$iterations$salt_b64$digest_b64."""
    try:
        scheme,iterations_text,salt_b64,digest_b64=encoded.split('$',3)
        if scheme!='pbkdf2_sha256':
            return False
        iterations=int(iterations_text)
        if iterations<100000 or iterations>2000000:
            return False
        salt=base64.urlsafe_b64decode(salt_b64+'='*((4-len(salt_b64)%4)%4))
        expected=base64.urlsafe_b64decode(digest_b64+'='*((4-len(digest_b64)%4)%4))
        actual=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,iterations,dklen=len(expected))
        return hmac.compare_digest(actual,expected)
    except Exception:
        return False

def _verify_admin_password(login_id: str, password: str) -> tuple[bool,str]:
    configured_id=_admin_login_id()
    if not hmac.compare_digest(str(login_id or '').strip(),configured_id):
        return False,'INVALID_CREDENTIALS'

    password_hash=os.environ.get('FULLMYSQL_ADMIN_PASSWORD_HASH','').strip()
    if password_hash:
        return (
            _verify_pbkdf2_password(str(password or ''),password_hash),
            'CONFIGURED_HASH',
        )

    password_secret=os.environ.get('FULLMYSQL_ADMIN_PASSWORD','')
    if password_secret:
        return (
            hmac.compare_digest(str(password or ''),password_secret),
            'CONFIGURED_SECRET',
        )

    # Migration-safe fallback only when a dedicated admin password is not yet
    # configured. This lets the new ID/password screen work immediately while
    # preserving existing API-token access. Set FULLMYSQL_ADMIN_PASSWORD or
    # FULLMYSQL_ADMIN_PASSWORD_HASH to disable this browser fallback.
    s=get_settings()
    supplied=str(password or '')
    for device,expected in s.api_tokens.items():
        if device in s.admin_devices and hmac.compare_digest(supplied,expected):
            return True,'LEGACY_ADMIN_TOKEN_FALLBACK'
    return False,'INVALID_CREDENTIALS'

def _admin_session_principal(login_id: str) -> str:
    return 'ADMIN:'+str(login_id).strip()

ADMIN_SESSION_COOKIE='fullmysql_admin_session'
ADMIN_SESSION_TTL_SECONDS=12*60*60

def _admin_session_secret() -> bytes:
    explicit=os.environ.get('FULLMYSQL_ADMIN_SESSION_SECRET','').strip()
    if explicit:
        return explicit.encode('utf-8')
    s=get_settings()
    material='|'.join(f'{k}:{s.api_tokens[k]}' for k in sorted(s.api_tokens))
    return hashlib.sha256(('FULLMYSQL_ADMIN_SESSION_V1|'+material).encode('utf-8')).digest()

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')

def _make_admin_session(device: str) -> tuple[str,int]:
    expires=int(time.time())+ADMIN_SESSION_TTL_SECONDS
    payload=f'{device}|{expires}'
    sig=hmac.new(_admin_session_secret(),payload.encode('utf-8'),hashlib.sha256).digest()
    token=_b64url(payload.encode('utf-8'))+'.'+_b64url(sig)
    return token,expires

def _parse_admin_session(token: str|None) -> tuple[str,int] | None:
    if not token or '.' not in token:
        return None
    try:
        p64,s64=token.split('.',1)
        payload_raw=base64.urlsafe_b64decode(p64+'='*((4-len(p64)%4)%4))
        sig_raw=base64.urlsafe_b64decode(s64+'='*((4-len(s64)%4)%4))
        expected=hmac.new(_admin_session_secret(),payload_raw,hashlib.sha256).digest()
        if not hmac.compare_digest(sig_raw,expected):
            return None
        payload=payload_raw.decode('utf-8')
        device,expiry_text=payload.rsplit('|',1)
        expiry=int(expiry_text)
        if expiry<int(time.time()):
            return None
        s=get_settings()
        is_bearer_device=device in s.admin_devices
        is_admin_login=(
            device.startswith('ADMIN:')
            and hmac.compare_digest(device.split(':',1)[1],_admin_login_id())
        )
        if not (is_bearer_device or is_admin_login):
            return None
        return device,expiry
    except Exception:
        return None

def _same_origin_admin_request(request: Request) -> bool:
    origin=(request.headers.get('origin') or '').strip()
    if not origin:
        return True
    try:
        from urllib.parse import urlsplit
        return urlsplit(origin).netloc.lower()==(request.headers.get('host') or '').lower()
    except Exception:
        return False

def admin_device_from_request(
    request: Request,
    authorization: str|None=None,
    *,
    write: bool=False,
) -> str:
    if authorization:
        device=device_from_auth(authorization)
        s=get_settings()
        if device not in s.admin_devices:
            raise HTTPException(403,'Admin device required')
        return device
    parsed=_parse_admin_session(request.cookies.get(ADMIN_SESSION_COOKIE))
    if not parsed:
        raise HTTPException(401,'Admin session required')
    if write and not _same_origin_admin_request(request):
        raise HTTPException(403,'Same-origin admin request required')
    return parsed[0]

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

class DumpingResolveRequest(BaseModel):
    confirm: str
    note: str|None=None

class OrderingPolicyUpsertRequest(BaseModel):
    scope_type: str
    scope_key: str='*'
    order_weekday: int
    delivery_weekday: int
    coverage_days_after_delivery: Decimal
    safety_days: Decimal=Decimal('0')
    min_order_qty: Decimal|None=None
    order_multiple: Decimal|None=None
    enabled: bool=True
    notes: str|None=None

class OrderDraftAddRequest(BaseModel):
    upc: str

class OrderDraftLineUpdateRequest(BaseModel):
    final_qty: Decimal
    adjustment_note: str|None=None

class OrderDraftTransitionRequest(BaseModel):
    action: str
    note: str|None=None
    external_order_reference: str|None=None

class OrderDraftReferenceRequest(BaseModel):
    external_order_reference: str|None=None

class PriceChangeProposalCreateRequest(BaseModel):
    upc: str
    proposed_price: Decimal
    proposal_basis: str
    proposed_price_type: str|None=None
    reason: str|None=None

class PriceChangeReviewRequest(BaseModel):
    decision: str
    note: str|None=None

class PriceChangeExecutionRequest(BaseModel):
    note: str|None=None

class AdminLoginRequest(BaseModel):
    login_id: str
    password: str

class V2PromotionItem(BaseModel):
    upc: str
    promotion_price: Decimal

class V2BulkOrderingRequest(BaseModel):
    order_type: str
    ordering_date: date|None=None
    expected_delivery_date: date|None=None
    promotion_involved: bool=False
    promotion_start_date: date|None=None
    promotion_end_date: date|None=None
    promotion_items: list[V2PromotionItem]=[]

class V2PITrueStockRequest(BaseModel):
    true_stock: Decimal
    uom: str
    note: str|None=None


WEB_UPLOAD_DEVICE='PUBLIC-WEB-UPLOAD'
WEB_UPLOAD_MAX_FILES=40
WEB_UPLOAD_EXTENSIONS={'.xlsx','.xls','.xlsm','.csv','.txt','.tsv'}


def _browser_upload_guard(request: Request) -> None:
    """Narrow no-login upload transport guard for the public app."""
    origin=(request.headers.get('origin') or '').strip()
    host=(request.headers.get('host') or '').strip().lower()
    if origin:
        try:
            from urllib.parse import urlsplit
            if urlsplit(origin).netloc.lower()!=host:
                raise HTTPException(403,'Cross-site upload is not allowed')
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(403,'Invalid upload origin')
    fetch_site=(request.headers.get('sec-fetch-site') or '').strip().lower()
    if fetch_site and fetch_site not in {'same-origin','same-site','none'}:
        raise HTTPException(403,'Cross-site upload is not allowed')


def _web_upload_filename_ok(filename: str) -> bool:
    return Path(str(filename or '')).suffix.lower() in WEB_UPLOAD_EXTENSIONS

@app.get('/',response_class=HTMLResponse,include_in_schema=False)
@app.get('/app',response_class=HTMLResponse,include_in_schema=False)
@app.get('/app/quick-check',response_class=HTMLResponse,include_in_schema=False)
@app.get('/app/v2',response_class=HTMLResponse,include_in_schema=False)
def public_web_app():
    return HTMLResponse(webapp_v2_html())


@app.get('/admin',response_class=HTMLResponse,include_in_schema=False)
def admin_web():
    return HTMLResponse(admin_web_html())


@app.post('/v1/admin/login')
def admin_login(body:AdminLoginRequest,response:Response):
    login_id=str(body.login_id or '').strip()
    password=str(body.password or '')
    if not login_id or not password:
        raise HTTPException(401,'Admin ID and password required')

    valid,auth_mode=_verify_admin_password(login_id,password)
    if not valid:
        # Keep the response intentionally generic so login ID validity is not exposed.
        raise HTTPException(401,'Invalid Admin ID or password')

    principal=_admin_session_principal(login_id)
    token,expires=_make_admin_session(principal)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        max_age=ADMIN_SESSION_TTL_SECONDS,
        expires=ADMIN_SESSION_TTL_SECONDS,
        path='/',
        secure=True,
        httponly=True,
        samesite='lax',
    )
    return {
        'ok':True,
        'device':principal,
        'login_id':login_id,
        'expires_at':datetime.fromtimestamp(expires).isoformat(),
        'session_type':'HTTPONLY_COOKIE',
        'auth_mode':auth_mode,
    }


@app.get('/v1/admin/session')
def admin_session(request:Request,authorization: Annotated[str|None,Header()]=None):
    device=admin_device_from_request(request,authorization)
    parsed=_parse_admin_session(request.cookies.get(ADMIN_SESSION_COOKIE))
    return {
        'ok':True,
        'device':device,
        'login_id':(
            device.split(':',1)[1]
            if device.startswith('ADMIN:') else device
        ),
        'expires_at':(
            datetime.fromtimestamp(parsed[1]).isoformat()
            if parsed and parsed[0]==device else None
        ),
    }


@app.post('/v1/admin/logout')
def admin_logout(response:Response):
    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        path='/',
        secure=True,
        httponly=True,
        samesite='lax',
    )
    return {'ok':True}


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


PUBLIC_WEB_UPLOAD_DEVICE='WEBAPP-PUBLIC'
PUBLIC_WEB_UPLOAD_EXTENSIONS={'.xlsx','.xls','.xlsm','.csv','.txt','.tsv'}
PUBLIC_WEB_UPLOAD_MAX_FILES=50

def _public_upload_same_origin(request: Request):
    if not _same_origin_admin_request(request):
        raise HTTPException(403,'Same-origin upload request required')

def _public_upload_status_payload(session_id: str) -> dict:
    payload=session_status(session_id)
    batch=dict(payload.get('batch') or {})
    batch.pop('notes',None)
    files=[]
    for row in payload.get('files') or []:
        files.append({
            'file_id':row.get('file_id'),
            'filename':row.get('original_filename'),
            'source_type':row.get('source_type'),
            'status':row.get('processing_status'),
            'rows':row.get('source_row_count'),
            'errors':row.get('error_count'),
            'duplicate_of_file_id':row.get('duplicate_of_file_id'),
            'coverage_start':row.get('coverage_start_date'),
            'coverage_end':row.get('coverage_end_date'),
        })
    return {
        'batch':batch,
        'files':files,
        'phase2c':payload.get('phase2c'),
        'phase3':payload.get('phase3'),
        'pipeline_runs':payload.get('api_runs') or [],
    }

@app.post('/v1/public-upload/batches')
def public_upload_create(
    body:BatchCreate,
    request:Request,
):
    _public_upload_same_origin(request)
    result=begin_batch(
        PUBLIC_WEB_UPLOAD_DEVICE,
        body.label or f'Web App Raw Upload {datetime.now().isoformat(timespec="minutes")}',
    )
    if not result.get('created'):
        active=result.get('active') or {}
        raise HTTPException(
            409,
            detail={
                'reason':'ANOTHER_BATCH_IS_ACTIVE',
                'batch_id':active.get('batch_id'),
                'status':active.get('processing_status'),
                'started_at':active.get('upload_started_at'),
            },
        )
    return {
        'created':True,
        'batch_id':result.get('batch_id'),
        'session_id':result.get('session_id'),
    }

@app.post('/v1/public-upload/batches/{session_id}/files')
async def public_upload_file(
    session_id:str,
    request:Request,
    file:UploadFile=File(...),
):
    _public_upload_same_origin(request)
    s=get_settings()
    filename=(file.filename or 'upload.bin').strip()
    suffix=Path(filename).suffix.lower()
    if suffix not in PUBLIC_WEB_UPLOAD_EXTENSIONS:
        raise HTTPException(
            415,
            detail={
                'reason':'UNSUPPORTED_UPLOAD_EXTENSION',
                'filename':filename,
                'allowed':sorted(PUBLIC_WEB_UPLOAD_EXTENSIONS),
            },
        )
    data=await file.read()
    if len(data)>s.upload_limit_mb*1024*1024:
        raise HTTPException(413,f'File exceeds {s.upload_limit_mb} MB limit')
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            """SELECT COUNT(*) AS c
               FROM ingest_file f
               JOIN ingest_batch b ON b.batch_id=f.batch_id
               WHERE b.batch_key=%s""",
            (session_id,),
        )
        count=int((cur.fetchone() or {}).get('c') or 0)
        cur.close()
    if count>=PUBLIC_WEB_UPLOAD_MAX_FILES:
        raise HTTPException(
            413,
            f'Batch file limit is {PUBLIC_WEB_UPLOAD_MAX_FILES}',
        )
    try:
        result=add_file(
            session_id,
            PUBLIC_WEB_UPLOAD_DEVICE,
            filename,
            data,
        )
        return {
            'batch_id':result.get('batch_id'),
            'session_id':result.get('session_id'),
            'file_id':result.get('file_id'),
            'filename':result.get('filename'),
            'status':result.get('status'),
            'source_type':result.get('source_type'),
            'rows':result.get('raw_rows_inserted'),
            'idempotent':result.get('idempotent',False),
        }
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    except PermissionError as exc:
        raise HTTPException(403,str(exc))
    except Exception as exc:
        raise HTTPException(400,str(exc))

@app.post('/v1/public-upload/batches/{session_id}/commit')
def public_upload_commit(
    session_id:str,
    request:Request,
):
    _public_upload_same_origin(request)
    try:
        return commit_batch(
            session_id,
            PUBLIC_WEB_UPLOAD_DEVICE,
        )
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    except PermissionError as exc:
        raise HTTPException(403,str(exc))
    except Exception as exc:
        raise HTTPException(400,str(exc))

@app.get('/v1/public-upload/batches/{session_id}')
def public_upload_batch_status(session_id:str):
    try:
        return json.loads(
            json.dumps(
                _public_upload_status_payload(session_id),
                default=j,
            )
        )
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Upload status failed: {exc}')

@app.get('/v1/public-upload/recent')
def public_upload_recent(limit:int=8):
    limit=max(1,min(int(limit or 8),20))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT b.batch_id,b.batch_label,b.processing_status,
                       b.upload_started_at,b.completed_at,b.file_count,
                       b.source_row_count,b.error_count,
                       p2.result_status AS phase2c_status,
                       p2.blocking_issue_count AS phase2c_blockers,
                       p3.result_status AS phase3_status,
                       p3.blocking_issue_count AS phase3_blockers,
                       p3.quick_check_rows,p3.quick_check_ready_rows,
                       p3.quick_check_hold_rows
                FROM ingest_batch b
                LEFT JOIN phase2c_batch_result p2 ON p2.batch_id=b.batch_id
                LEFT JOIN phase3_batch_result p3 ON p3.batch_id=b.batch_id
                ORDER BY b.batch_id DESC
                LIMIT {limit}"""
        )
        batches=cur.fetchall()
        ids=[int(x['batch_id']) for x in batches]
        file_map={bid:[] for bid in ids}
        if ids:
            ph=','.join(['%s']*len(ids))
            cur.execute(
                f"""SELECT batch_id,file_id,original_filename,source_type,
                           processing_status,source_row_count,error_count,
                           coverage_start_date,coverage_end_date
                    FROM ingest_file
                    WHERE batch_id IN ({ph})
                    ORDER BY batch_id DESC,file_id""",
                tuple(ids),
            )
            for row in cur.fetchall():
                file_map[int(row['batch_id'])].append({
                    'file_id':row.get('file_id'),
                    'filename':row.get('original_filename'),
                    'source_type':row.get('source_type'),
                    'status':row.get('processing_status'),
                    'rows':row.get('source_row_count'),
                    'errors':row.get('error_count'),
                    'coverage_start':row.get('coverage_start_date'),
                    'coverage_end':row.get('coverage_end_date'),
                })
        cur.close()
    for b in batches:
        b['files']=file_map.get(int(b['batch_id']),[])
    return json.loads(json.dumps({'count':len(batches),'batches':batches},default=j))

@app.post('/v1/web-upload/batches')
def web_upload_create_batch(body:BatchCreate,request:Request):
    _browser_upload_guard(request)
    label=(str(body.label or '').strip() or f'Web raw upload {datetime.now().isoformat(timespec="minutes")}')
    r=begin_batch(WEB_UPLOAD_DEVICE,label)
    if not r.get('created'):
        raise HTTPException(409,detail={'message':'Another ingest batch is active','active':r.get('active')})
    return r


@app.post('/v1/web-upload/batches/{session_id}/files')
async def web_upload_file(session_id:str,request:Request,file:UploadFile=File(...)):
    _browser_upload_guard(request)
    filename=file.filename or 'upload.bin'
    if not _web_upload_filename_ok(filename):
        raise HTTPException(415,'Supported raw files: XLSX, XLS, XLSM, CSV, TXT, TSV')
    try:
        existing=session_status(session_id)
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    if len(existing.get('files') or [])>=WEB_UPLOAD_MAX_FILES:
        raise HTTPException(413,f'Batch file limit is {WEB_UPLOAD_MAX_FILES}')
    s=get_settings()
    data=await file.read()
    if not data:
        raise HTTPException(400,'Empty file is not allowed')
    if len(data)>s.upload_limit_mb*1024*1024:
        raise HTTPException(413,f'File exceeds {s.upload_limit_mb} MB limit')
    try:
        return add_file(session_id,WEB_UPLOAD_DEVICE,filename,data)
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    except PermissionError as exc:
        raise HTTPException(403,str(exc))
    except Exception as exc:
        raise HTTPException(400,str(exc))


@app.post('/v1/web-upload/batches/{session_id}/commit')
def web_upload_commit(session_id:str,request:Request):
    _browser_upload_guard(request)
    try:
        return commit_batch(session_id,WEB_UPLOAD_DEVICE)
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    except PermissionError as exc:
        raise HTTPException(403,str(exc))
    except Exception as exc:
        raise HTTPException(400,str(exc))


@app.get('/v1/web-upload/batches/{session_id}')
def web_upload_status(session_id:str,request:Request):
    _browser_upload_guard(request)
    try:
        return json.loads(json.dumps(session_status(session_id),default=j))
    except KeyError as exc:
        raise HTTPException(404,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Batch status failed: {exc}')


@app.get('/v1/web-upload/active')
def web_upload_active(request:Request):
    _browser_upload_guard(request)
    return {'active_batch':find_active_batch()}


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


@app.post('/v1/maintenance/cost-authority-refresh')
def cost_authority_refresh(
    body: ManualAuthorityRefreshRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=device_from_auth(authorization)
    if body.confirm!='REFRESH_COST_AUTHORITY_ORDER':
        raise HTTPException(
            400,
            "confirm must be REFRESH_COST_AUTHORITY_ORDER",
        )
    try:
        result=run_cost_authority_refresh(device)
    except RuntimeError as exc:
        raise HTTPException(409,str(exc))
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'Cost-authority refresh failed: {exc}')
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


@app.get('/v1/diagnostics/oh-cost-schema')
def oh_cost_schema_diagnostic(
    candidate_row_limit:int=20,
    authorization: Annotated[str|None,Header()]=None,
):
    """Read-only diagnostic for On-Hand cost header/schema matching."""
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            result=diagnose_oh_cost_schema(
                cur,
                candidate_row_limit=candidate_row_limit,
            )
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
def app_quick_check_search(q:str,limit:int=20):
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


@app.get('/v1/app/cost/backfill-queue')
def app_cost_backfill_queue(
    lookback_days:int=90,
    authorization: Annotated[str|None,Header()]=None,
):
    device_from_auth(authorization)
    try:
        result=cost_backfill_queue(lookback_days)
    except Exception as exc:
        raise HTTPException(500,f'Cost backfill queue failed: {exc}')
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
def app_quick_check_detail(upc:str):
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
    device=public_app_actor(authorization)
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


@app.get('/v1/app/dashboard')
def app_dashboard():
    try:
        result=operational_dashboard()
    except Exception as exc:
        raise HTTPException(500,f'Operations dashboard failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/search')
def app_v2_search(q:str,limit:int=30):
    try:
        result=v2_search_items(q,limit)
    except Exception as exc:
        raise HTTPException(500,f'V2 search failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/pi/search')
def app_v2_pi_search(q:str,limit:int=30):
    try:
        result=v2_pi_search_items(q,limit)
    except Exception as exc:
        raise HTTPException(500,f'V2 PI search failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/pi/{family_key}')
def app_v2_pi_item(family_key:str,history_limit:int=20):
    try:
        result=v2_pi_item(family_key,history_limit)
    except KeyError:
        raise HTTPException(
            404,
            detail={'status':'NOT_FOUND','reason':'V2_PI_FAMILY_NOT_FOUND'},
        )
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'V2 PI family failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/app/v2/pi/{family_key}/true-stock')
def app_v2_pi_submit_true_stock(
    family_key:str,
    body:V2PITrueStockRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    device=public_app_actor(authorization)
    try:
        committed=v2_submit_family_true_stock(
            family_key,
            body.true_stock,
            body.uom,
            device,
            body.note,
        )
        detail=v2_pi_item(family_key)
    except KeyError:
        raise HTTPException(
            404,
            detail={'status':'NOT_FOUND','reason':'V2_PI_FAMILY_NOT_FOUND'},
        )
    except ValueError as exc:
        code=str(exc)
        if code in {'TRUE_STOCK_NEGATIVE','TRUE_STOCK_UOM_REQUIRED'}:
            raise HTTPException(
                422,
                detail={'status':'INVALID','reason':code,'family_key':family_key},
            )
        if code.startswith('TRUE_STOCK_UOM_MISMATCH:'):
            required=code.split(':',1)[1]
            raise HTTPException(
                422,
                detail={
                    'status':'INVALID',
                    'reason':'TRUE_STOCK_UOM_MISMATCH',
                    'required_uom':required,
                    'family_key':family_key,
                },
            )
        if code in {'UNAVAILABLE','BLOCKED_MIXED_UOM','FAMILY_SYSTEM_OH_UNAVAILABLE'}:
            raise HTTPException(
                409,
                detail={'status':'BLOCKED','reason':code,'family_key':family_key},
            )
        raise HTTPException(400,str(exc))
    except Exception as exc:
        raise HTTPException(500,f'V2 PI Family True Stock submit failed: {exc}')

    system_qty=Decimal(str(committed['system_oh']))
    true_qty=Decimal(str(committed['true_stock']))
    signed=true_qty-system_qty
    return json.loads(json.dumps({
        'status':'COMMITTED',
        'commit':committed,
        'signed_difference_true_minus_system':signed,
        'shortage_quantity':max(Decimal('0'),-signed),
        'overage_quantity':max(Decimal('0'),signed),
        'pi':detail,
    },default=j))

@app.get('/v1/app/v2/performance/dates')
def app_v2_performance_dates(limit:int=180):
    try:
        result=v2_performance_supported_dates(limit)
    except Exception as exc:
        raise HTTPException(500,f'V2 performance dates failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/performance/latest-date')
def app_v2_performance_latest_date():
    try:
        result=v2_latest_performance_date()
    except Exception as exc:
        raise HTTPException(500,f'V2 performance latest date failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/performance')
def app_v2_performance(
    category:str='ALL',
    limit:int=100,
    report_date:date|None=None,
):
    try:
        result=v2_performance_report(category,limit,report_date)
    except ValueError as exc:
        raise HTTPException(422,detail={'status':'INVALID','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'V2 performance report failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/family/{family_key}')
def app_v2_family(family_key:str):
    try:
        result=v2_family_info(family_key)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'V2_FAMILY_NOT_FOUND'})
    except Exception as exc:
        raise HTTPException(500,f'V2 family info failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/upc/{upc}')
def app_v2_upc(upc:str):
    try:
        result=v2_upc_info(upc)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'V2_UPC_NOT_FOUND'})
    except Exception as exc:
        raise HTTPException(500,f'V2 UPC info failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/upc/{upc}/price')
def app_v2_price(upc:str,trend_supported_days:int=28):
    try:
        result=v2_price_analysis(upc,trend_supported_days)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'V2_UPC_NOT_FOUND'})
    except Exception as exc:
        raise HTTPException(500,f'V2 price analysis failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/family/{family_key}/promotions')
def app_v2_family_promotions(family_key:str):
    try:
        result=v2_family_promotion_history(family_key)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'V2_FAMILY_NOT_FOUND'})
    except Exception as exc:
        raise HTTPException(500,f'V2 family promotion history failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/v2/upc/{upc}/ordering')
def app_v2_ordering(
    upc:str,
    ordering_date:date|None=None,
    expected_delivery_date:date|None=None,
    promotion_involved:bool=False,
    promotion_start_date:date|None=None,
    promotion_end_date:date|None=None,
    promotion_price:Decimal|None=None,
):
    try:
        result=v2_ordering_analysis(
            upc,
            ordering_date=ordering_date,
            expected_delivery_date=expected_delivery_date,
            promotion_involved=promotion_involved,
            promotion_start_date=promotion_start_date,
            promotion_end_date=promotion_end_date,
            promotion_price=promotion_price,
        )
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'V2_UPC_NOT_FOUND'})
    except Exception as exc:
        raise HTTPException(500,f'V2 ordering analysis failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/ordering')
def app_ordering(limit:int=80):
    return json.loads(json.dumps(ordering_queue(limit),default=j))


@app.get('/v1/app/ordering/policies')
def app_ordering_policies():
    return json.loads(json.dumps(list_ordering_policies(),default=j))


@app.post('/v1/admin/ordering/policy')
def admin_upsert_ordering_policy(
    body:OrderingPolicyUpsertRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=upsert_ordering_policy(
            scope_type=body.scope_type,
            scope_key=body.scope_key,
            order_weekday=body.order_weekday,
            delivery_weekday=body.delivery_weekday,
            coverage_days_after_delivery=body.coverage_days_after_delivery,
            safety_days=body.safety_days,
            min_order_qty=body.min_order_qty,
            order_multiple=body.order_multiple,
            enabled=body.enabled,
            notes=body.notes,
            device=device,
        )
    except ValueError as exc:
        raise HTTPException(422,detail={'status':'INVALID','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Ordering policy save failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/admin/ordering/drafts')
def admin_order_drafts(
    request:Request,
    status:str|None=None,
    limit:int=60,
    authorization: Annotated[str|None,Header()]=None,
):
    admin_device_from_request(request,authorization)
    try:
        result=order_draft_history(status,limit)
    except Exception as exc:
        raise HTTPException(500,f'Order draft history failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/admin/ordering/drafts/add-recommendation')
def admin_add_order_recommendation(
    body:OrderDraftAddRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=add_order_recommendation_to_draft(body.upc,device=device)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'ORDERING_UPC_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Add order recommendation failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/admin/ordering/drafts/lines/{order_draft_line_id}')
def admin_update_order_draft_line(
    order_draft_line_id:int,
    body:OrderDraftLineUpdateRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=update_order_draft_line(
            order_draft_line_id,
            final_qty=body.final_qty,
            adjustment_note=body.adjustment_note,
            device=device,
        )
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'ORDER_DRAFT_LINE_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Order draft line update failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/admin/ordering/drafts/{order_draft_id}/transition')
def admin_transition_order_draft(
    order_draft_id:int,
    body:OrderDraftTransitionRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=transition_order_draft(
            order_draft_id,
            action=body.action,
            note=body.note,
            external_order_reference=body.external_order_reference,
            device=device,
        )
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'ORDER_DRAFT_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except RuntimeError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Order draft transition failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/admin/ordering/drafts/{order_draft_id}/reconciliation')
def admin_order_delivery_reconciliation(
    order_draft_id:int,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    admin_device_from_request(request,authorization)
    try:
        result=order_delivery_reconciliation(order_draft_id)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'ORDER_DRAFT_NOT_FOUND'})
    except Exception as exc:
        raise HTTPException(500,f'Delivery reconciliation failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/admin/ordering/drafts/{order_draft_id}/reference')
def admin_update_order_external_reference(
    order_draft_id:int,
    body:OrderDraftReferenceRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=update_order_external_reference(
            order_draft_id,
            external_order_reference=body.external_order_reference,
            device=device,
        )
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Order reference update failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/price-change')
def app_price_change(limit:int=120):
    return json.loads(json.dumps(price_change_queue(limit),default=j))


@app.get('/v1/app/price-change/proposals')
def app_price_change_proposals(status:str|None=None,limit:int=100):
    return json.loads(json.dumps(list_price_change_proposals(status,limit),default=j))


@app.get('/v1/app/price-change/{upc}/preview')
def app_price_change_preview(upc:str,proposed_price:Decimal):
    try:
        result=price_change_preview(upc,proposed_price)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'PRICE_CHANGE_UPC_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(422,detail={'status':'INVALID','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Price Change preview failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/admin/price-change/proposals')
def admin_create_price_change_proposal(
    body:PriceChangeProposalCreateRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=create_price_change_proposal(
            upc=body.upc,
            proposed_price=body.proposed_price,
            proposal_basis=body.proposal_basis,
            proposed_price_type=body.proposed_price_type,
            reason=body.reason,
            device=device,
        )
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'PRICE_CHANGE_UPC_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(422,detail={'status':'INVALID','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Price Change proposal create failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/admin/price-change/proposals/{proposal_id}/review')
def admin_review_price_change_proposal(
    proposal_id:int,
    body:PriceChangeReviewRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=review_price_change_proposal(
            proposal_id,
            decision=body.decision,
            note=body.note,
            device=device,
        )
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'PRICE_CHANGE_PROPOSAL_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except RuntimeError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Price Change review failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/admin/price-change/proposals/{proposal_id}/mark-executed')
def admin_mark_price_change_executed(
    proposal_id:int,
    body:PriceChangeExecutionRequest,
    request:Request,
    authorization: Annotated[str|None,Header()]=None,
):
    device=admin_device_from_request(request,authorization,write=True)
    try:
        result=mark_price_change_executed(
            proposal_id,
            note=body.note,
            device=device,
        )
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'PRICE_CHANGE_PROPOSAL_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except RuntimeError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Price Change execution mark failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/app/dumping/pending')
def app_pending_dumping():
    rows=pending_dumping_discrepancies()
    return json.loads(json.dumps({'count':len(rows),'rows':rows},default=j))


@app.get('/v1/app/dumping/history')
def app_dumping_history(limit:int=100,status:str|None=None):
    try:
        result=dumping_discrepancy_history(limit,status)
    except Exception as exc:
        raise HTTPException(500,f'Dumping history failed: {exc}')
    return json.loads(json.dumps(result,default=j))


@app.post('/v1/app/dumping/{discrepancy_id}/resolve')
def app_resolve_dumping(
    discrepancy_id:int,
    body:DumpingResolveRequest,
    authorization: Annotated[str|None,Header()]=None,
):
    if body.confirm!='RESOLVE_DUMPING_DISCREPANCY':
        raise HTTPException(400,'confirm must be RESOLVE_DUMPING_DISCREPANCY')
    device=public_app_actor(authorization)
    try:
        result=resolve_dumping_discrepancy(discrepancy_id,device,body.note)
    except KeyError:
        raise HTTPException(404,detail={'status':'NOT_FOUND','reason':'DUMPING_DISCREPANCY_NOT_FOUND'})
    except ValueError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except RuntimeError as exc:
        raise HTTPException(409,detail={'status':'BLOCKED','reason':str(exc)})
    except Exception as exc:
        raise HTTPException(500,f'Dumping resolve failed: {exc}')
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
