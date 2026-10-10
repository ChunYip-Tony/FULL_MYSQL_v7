from __future__ import annotations

"""Fast-read API and lossless coalescing rebuild coordinator for App Ready snapshots."""

import threading
from fastapi import HTTPException
from business_clock import completed_through_date
from yipman_app_ready_builders import app_ready_builders
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS, SNAPSHOT_SECTIONS, SnapshotBuild, build_app_ready_snapshot

_COORDINATOR_LOCK = threading.Lock()
_WORKER_RUNNING = False
_PENDING_SOURCE: str | None = None


def _coordinator_status() -> tuple[bool, str | None]:
    with _COORDINATOR_LOCK:
        return _WORKER_RUNNING, _PENDING_SOURCE


def _finish_failed_worker(failed_source: str) -> None:
    global _WORKER_RUNNING, _PENDING_SOURCE
    with _COORDINATOR_LOCK:
        _WORKER_RUNNING = False
        if _PENDING_SOURCE is None:
            _PENDING_SOURCE = failed_source


def rebuild_app_ready_snapshot(*, source_batch_id=None) -> None:
    global _WORKER_RUNNING, _PENDING_SOURCE
    source = str(source_batch_id or "UNSPECIFIED")
    with _COORDINATOR_LOCK:
        if _WORKER_RUNNING:
            _PENDING_SOURCE = source
            return
        _WORKER_RUNNING = True
    try:
        while True:
            build_app_ready_snapshot(app_ready_builders(), source_batch_id=source, data_through=completed_through_date().isoformat())
            with _COORDINATOR_LOCK:
                if _PENDING_SOURCE is None:
                    _WORKER_RUNNING = False
                    return
                source = _PENDING_SOURCE
                _PENDING_SOURCE = None
    except Exception:
        _finish_failed_worker(source)
        raise


def request_app_ready_rebuild(*, source_batch_id=None) -> bool:
    global _WORKER_RUNNING, _PENDING_SOURCE
    source = str(source_batch_id or "UNSPECIFIED")
    with _COORDINATOR_LOCK:
        if _WORKER_RUNNING:
            _PENDING_SOURCE = source
            return True
        _PENDING_SOURCE = None
        _WORKER_RUNNING = True

    def worker() -> None:
        global _WORKER_RUNNING, _PENDING_SOURCE
        current = source
        try:
            while True:
                from pipeline_priority import wait_for_pipeline_idle
                wait_for_pipeline_idle()
                build_app_ready_snapshot(app_ready_builders(), source_batch_id=current, data_through=completed_through_date().isoformat())
                with _COORDINATOR_LOCK:
                    if _PENDING_SOURCE is None:
                        _WORKER_RUNNING = False
                        return
                    current = _PENDING_SOURCE
                    _PENDING_SOURCE = None
        except Exception:
            _finish_failed_worker(current)

    try:
        threading.Thread(target=worker, name="yipman-app-ready-rebuild", daemon=True).start()
    except Exception:
        _finish_failed_worker(source)
        raise
    return True


def hydrate_durable_app_ready() -> bool:
    """Make the last complete shared generation readable before rebuilding."""
    try:
        from yipman_app_ready_persistence import load_active_snapshot
        snap = load_active_snapshot(SnapshotBuild)
        if snap is None:
            return False
        APP_READY_SNAPSHOTS.hydrate(snap)
        return True
    except Exception:
        return False


def _refresh_shared_pointer() -> None:
    from yipman_app_ready_readers import refresh_hot_cache_if_stale
    refresh_hot_cache_if_stale()


def install_app_ready_api(app) -> None:
    if getattr(app.state, "yipman_app_ready_api_installed", False):
        return

    @app.on_event("startup")
    def _build_app_ready_on_startup():
        hydrated = hydrate_durable_app_ready()
        app.state.yipman_app_ready_durable_hydrated = hydrated
        request_app_ready_rebuild(source_batch_id="STARTUP")

    @app.get("/api/yipman/app-ready/status")
    def yipman_app_ready_status():
        _refresh_shared_pointer()
        worker_running, queued_source = _coordinator_status()
        out = APP_READY_SNAPSHOTS.status()
        out["rebuild_worker_running"] = worker_running
        out["rebuild_queued"] = queued_source is not None
        out["queued_source"] = queued_source
        out["durable_hydrated"] = bool(getattr(app.state, "yipman_app_ready_durable_hydrated", False))
        from yipman_app_ready_readers import pointer_refresh_status
        out.update(pointer_refresh_status())
        return out

    @app.get("/api/yipman/app-ready/snapshot")
    def yipman_app_ready_snapshot():
        _refresh_shared_pointer()
        snap = APP_READY_SNAPSHOTS.active()
        if snap is None:
            raise HTTPException(status_code=503, detail="APP_READY_SNAPSHOT_NOT_AVAILABLE")
        return {"status":"APP_READY","build_id":snap.build_id,"source_batch_id":snap.source_batch_id,"data_through":snap.data_through,"completed_at":snap.completed_at,"build_ms":snap.build_ms,"sections":snap.sections}

    @app.get("/api/yipman/app-ready/{section}")
    def yipman_app_ready_section(section: str):
        if section not in SNAPSHOT_SECTIONS:
            raise HTTPException(status_code=404, detail="UNKNOWN_APP_READY_SECTION")
        _refresh_shared_pointer()
        snap = APP_READY_SNAPSHOTS.active()
        if snap is None:
            raise HTTPException(status_code=503, detail="APP_READY_SNAPSHOT_NOT_AVAILABLE")
        return {"status":"APP_READY","build_id":snap.build_id,"data_through":snap.data_through,"section":section,"payload":snap.sections[section]}

    app.state.yipman_app_ready_api_installed = True
    app.state.request_yipman_app_ready_rebuild = request_app_ready_rebuild

