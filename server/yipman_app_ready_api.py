from __future__ import annotations

"""Fast-read API and coalescing rebuild coordinator for App Ready snapshots."""

import threading
from fastapi import HTTPException
from business_clock import completed_through_date
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS,SNAPSHOT_SECTIONS,build_app_ready_snapshot
from yipman_app_ready_builders import app_ready_builders

_BUILD_LOCK=threading.Lock();_REQUEST_LOCK=threading.Lock();_PENDING_SOURCE: str|None=None

def _take_pending():
    global _PENDING_SOURCE
    with _REQUEST_LOCK:
        value=_PENDING_SOURCE;_PENDING_SOURCE=None;return value

def rebuild_app_ready_snapshot(*,source_batch_id=None)->None:
    """Build atomically and immediately coalesce one mutation arriving mid-build."""
    if not _BUILD_LOCK.acquire(blocking=False):return
    try:
        source=source_batch_id
        while source:
            build_app_ready_snapshot(app_ready_builders(),source_batch_id=source,data_through=completed_through_date().isoformat())
            source=_take_pending()
    finally:_BUILD_LOCK.release()

def request_app_ready_rebuild(*,source_batch_id=None)->bool:
    global _PENDING_SOURCE
    source=str(source_batch_id or "UNSPECIFIED")
    with _REQUEST_LOCK:
        if _BUILD_LOCK.locked():
            _PENDING_SOURCE=source
            return True
    threading.Thread(target=rebuild_app_ready_snapshot,kwargs={"source_batch_id":source},name="yipman-app-ready-rebuild",daemon=True).start();return True

def install_app_ready_api(app)->None:
    if getattr(app.state,"yipman_app_ready_api_installed",False):return
    @app.on_event("startup")
    def _build_app_ready_on_startup():request_app_ready_rebuild(source_batch_id="STARTUP")
    @app.get("/api/yipman/app-ready/status")
    def yipman_app_ready_status():
        out=APP_READY_SNAPSHOTS.status();out["rebuild_queued"]=_PENDING_SOURCE is not None;out["queued_source"]=_PENDING_SOURCE;return out
    @app.get("/api/yipman/app-ready/snapshot")
    def yipman_app_ready_snapshot():
        snap=APP_READY_SNAPSHOTS.active()
        if snap is None:raise HTTPException(status_code=503,detail="APP_READY_SNAPSHOT_NOT_AVAILABLE")
        return {"status":"APP_READY","build_id":snap.build_id,"source_batch_id":snap.source_batch_id,"data_through":snap.data_through,"completed_at":snap.completed_at,"build_ms":snap.build_ms,"sections":snap.sections}
    @app.get("/api/yipman/app-ready/{section}")
    def yipman_app_ready_section(section:str):
        if section not in SNAPSHOT_SECTIONS:raise HTTPException(status_code=404,detail="UNKNOWN_APP_READY_SECTION")
        snap=APP_READY_SNAPSHOTS.active()
        if snap is None:raise HTTPException(status_code=503,detail="APP_READY_SNAPSHOT_NOT_AVAILABLE")
        return {"status":"APP_READY","build_id":snap.build_id,"data_through":snap.data_through,"section":section,"payload":snap.sections[section]}
    app.state.yipman_app_ready_api_installed=True;app.state.request_yipman_app_ready_rebuild=request_app_ready_rebuild
