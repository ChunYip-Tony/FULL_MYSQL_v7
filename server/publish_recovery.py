"""Decide durable publication recovery without an open browser or startup."""
import json
from datetime import datetime, timezone

STALE_PUBLISH_SECONDS = 15 * 60


def _utc_stamp(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)



def owned_legacy_handoff(row, code_version, worker, worker_instance):
    """Recover only this live owner's job requeued by an older supervisor."""
    detail=row.get('detail_json') or {}
    if isinstance(detail,str):
        try:detail=json.loads(detail)
        except ValueError:return False
    version_key=lambda v:tuple(int(p) for p in str(v).split('-',1)[0].split('.') if p.isdigit())
    old=detail.get('requeued_by_code_version')
    return bool(row.get('processing_status')=='QUEUED' and row.get('code_version')==code_version
        and detail.get('worker')==worker and detail.get('worker_instance')==worker_instance
        and detail.get('recovery_reason')=='SERVICE_DEPLOYMENT_SHUTDOWN' and old
        and version_key(old)<version_key(code_version))


def publish_recovery_decision(latest, snapshot_updated_at, code_version, history_contract, now=None):
    now=now or datetime.now(timezone.utc)
    if not latest:
        return {'queue':True,'reason':'MISSING_PUBLICATION'}
    detail=latest.get('detail_json') or {}
    if isinstance(detail,str):
        try: detail=json.loads(detail)
        except ValueError: detail={}
    status=str(latest.get('processing_status') or '').upper()
    if status in {'STARTED','QUEUED','PAUSE_REQUESTED'}:
        # Report stale jobs but never enqueue a duplicate while a lease may exist.
        heartbeat = next((stamp for stamp in (
            _utc_stamp(detail.get('heartbeat_at')),
            _utc_stamp(latest.get('heartbeat_at')),
            _utc_stamp(latest.get('started_at')),
            _utc_stamp(latest.get('created_at'))
        ) if stamp is not None), None)
        if heartbeat is not None and (now - heartbeat).total_seconds() > STALE_PUBLISH_SECONDS:
            return {'queue': False, 'reason': 'STALE_PUBLICATION_RECLAIM_REQUIRED',
                    'stale_seconds': int((now - heartbeat).total_seconds()),
                    'status': status}
        return {'queue':False,'reason':'ACTIVE_PUBLICATION'}
    result=detail.get('publish_result') or {}
    readback=result.get('readback') or {}
    completed=latest.get('completed_at')
    def stamp(value):
        if value is None:return None
        if isinstance(value,str):value=datetime.fromisoformat(value.replace('Z','+00:00'))
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    completed=stamp(completed);snapshot=stamp(snapshot_updated_at)
    current=(status=='COMPLETED' and result.get('status')=='PASS'
             and readback.get('pass') is True and result.get('history_contract')==history_contract
             and (readback.get('history') or {}).get('pass') is True
             and (readback.get('inventory_adjustments') or {}).get('pass') is True
             and (readback.get('inventory_adjustments') or {}).get('contract')=='INVENTORY_GP_V1'
             and completed is not None and snapshot is not None and completed>=snapshot)
    if current:return {'queue':False,'reason':'VERIFIED_CURRENT'}
    def version_key(value):return tuple(int(p) for p in str(value).split('-',1)[0].split('.') if p.isdigit())
    if version_key(latest.get('code_version'))>version_key(code_version):
        return {'queue':False,'reason':'NEWER_RUNTIME_REQUIRED'}
    # A committed same-batch rebuild invalidates the old export immediately.
    if status=='COMPLETED':return {'queue':True,'reason':'SOURCE_OR_VERIFICATION_CHANGED'}
    if latest.get('code_version')!=code_version:return {'queue':True,'reason':'NEW_RECOVERY_CODE'}
    error=str(result.get('error') or detail.get('error') or '')
    if result.get('status') in {'FAILED_READBACK','FAILED_BRIDGE_READBACK'}:
        return {'queue':False,'reason':'REPAIR_REQUIRED','error':'; '.join(readback.get('failures') or [result['status']])}
    if any(code in error for code in ('TAB_NOT_ALLOWED','UNAUTHORIZED','SPREADSHEET_ID_MISMATCH','readback mismatch','source omitted active UPC')):
        return {'queue':False,'reason':'REPAIR_REQUIRED','error':error}
    count=max(1,int(latest.get('retry_count') or 1))
    delay=min(3600,60*2**min(6,count-1))
    age=(now-(completed or now)).total_seconds()
    if age<delay:return {'queue':False,'reason':'RETRY_WAIT','retry_after_seconds':int(delay-age)}
    return {'queue':True,'reason':'TRANSIENT_PUBLICATION_RETRY'}

