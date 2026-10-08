from __future__ import annotations

"""Fast-read API surface and rebuild coordinator for App Ready snapshots."""
import threading
from fastapi import HTTPException
from business_clock import completed_through_date
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS,SNAPSHOT_SECTIONS,build_app_ready_snapshot
from yipman_app_ready_builders import app_ready_builders
_BUILD_LOCK=threading.Lock();_REQUEST_LOCK=threading.Lock();_PENDING_BATCH=None

def _set_pending(batch):
    global _PENDING_BATCH
    with _REQUEST_LOCK:_PENDING_BATCH=batch or _PENDING_BATCH or 'DATA_CHANGE'
def _take_pending():
    global _PENDING_BATCH
    with _REQUEST_LOCK:
        value=_PENDING_BATCH;_PENDING_BATCH=None;return value
def rebuild_app_ready_snapshot(*,source_batch_id=None):
    if not _BUILD_LOCK.acquire(blocking=False):_set_pending(source_batch_id);return
    try:
        batch=source_batch_id
        while batch:
            build_app_ready_snapshot(app_ready_builders(),source_batch_id=batch,data_through=completed_through_date().isoformat())
            batch=_take_pending()
    finally:_BUILD_LOCK.release()
def request_app_ready_rebuild(*,source_batch_id=None):
    if _BUILD_LOCK.locked():_set_pending(source_batch_id);return True
    threading.Thread(target=rebuild_app_ready_snapshot,kwargs={'source_batch_id':source_batch_id or 'DATA_CHANGE'},name='yipman-app-ready-rebuild',daemon=True).start();return True
def install_app_ready_api(app):
    if getattr(app.state,'yipman_app_ready_api_installed',False):return
    @app.on_event('startup')
    def _build_app_ready_on_startup():request_app_ready_rebuild(source_batch_id='STARTUP')
    @app.get('/api/yipman/app-ready/status')
    def yipman_app_ready_status():
        status=APP_READY_SNAPSHOTS.status()
        with _REQUEST_LOCK:status['pending_rebuild_batch_id']=_PENDING_BATCH
        return status
    @app.get('/api/yipman/app-ready/snapshot')
    def yipman_app_ready_snapshot():
        snap=APP_READY_SNAPSHOTS.active()
        if snap is None:raise HTTPException(status_code=503,detail='APP_READY_SNAPSHOT_NOT_AVAILABLE')
        return {'status':'APP_READY','build_id':snap.build_id,'source_batch_id':snap.source_batch_id,'data_through':snap.data_through,'completed_at':snap.completed_at,'sections':snap.sections}
    @app.get('/api/yipman/app-ready/{section}')
    def yipman_app_ready_section(section:str):
        if section not in SNAPSHOT_SECTIONS:raise HTTPException(status_code=404,detail='UNKNOWN_APP_READY_SECTION')
        snap=APP_READY_SNAPSHOTS.active()
        if snap is None:raise HTTPException(status_code=503,detail='APP_READY_SNAPSHOT_NOT_AVAILABLE')
        return {'status':'APP_READY','build_id':snap.build_id,'data_through':snap.data_through,'section':section,'payload':snap.sections[section]}
    app.state.yipman_app_ready_api_installed=True;app.state.request_yipman_app_ready_rebuild=request_app_ready_rebuild
