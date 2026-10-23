"""Decide durable publication recovery without an open browser or startup."""
import json
from datetime import datetime, timezone


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
    if any(code in error for code in ('TAB_NOT_ALLOWED','UNAUTHORIZED','SPREADSHEET_ID_MISMATCH','readback mismatch','source omitted active UPC')):
        return {'queue':False,'reason':'REPAIR_REQUIRED','error':error}
    count=max(1,int(latest.get('retry_count') or 1))
    delay=min(3600,60*2**min(6,count-1))
    age=(now-(completed or now)).total_seconds()
    if age<delay:return {'queue':False,'reason':'RETRY_WAIT','retry_after_seconds':int(delay-age)}
    return {'queue':True,'reason':'TRANSIENT_PUBLICATION_RETRY'}
