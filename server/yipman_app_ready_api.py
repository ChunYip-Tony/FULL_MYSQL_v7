from __future__ import annotations

"""Fast-read API surface and rebuild coordinator for App Ready snapshots."""

import threading
from fastapi import HTTPException
from business_clock import completed_through_date
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS, SNAPSHOT_SECTIONS, build_app_ready_snapshot
from yipman_app_ready_builders import app_ready_builders

_BUILD_LOCK = threading.Lock()


def rebuild_app_ready_snapshot(*, source_batch_id: str | None = None) -> None:
    """Build in background; readers keep the previous complete snapshot."""
    if not _BUILD_LOCK.acquire(blocking=False):
        return
    try:
        build_app_ready_snapshot(
            app_ready_builders(),
            source_batch_id=source_batch_id,
            data_through=completed_through_date().isoformat(),
        )
    finally:
        _BUILD_LOCK.release()


def request_app_ready_rebuild(*, source_batch_id: str | None = None) -> bool:
    if _BUILD_LOCK.locked():
        return False
    threading.Thread(
        target=rebuild_app_ready_snapshot,
        kwargs={"source_batch_id": source_batch_id},
        name="yipman-app-ready-rebuild",
        daemon=True,
    ).start()
    return True


def install_app_ready_api(app) -> None:
    if getattr(app.state, "yipman_app_ready_api_installed", False):
        return

    @app.on_event("startup")
    def _build_app_ready_on_startup():
        request_app_ready_rebuild(source_batch_id="STARTUP")

    @app.get("/api/yipman/app-ready/status")
    def yipman_app_ready_status():
        return APP_READY_SNAPSHOTS.status()

    @app.get("/api/yipman/app-ready/snapshot")
    def yipman_app_ready_snapshot():
        snap = APP_READY_SNAPSHOTS.active()
        if snap is None:
            raise HTTPException(status_code=503, detail="APP_READY_SNAPSHOT_NOT_AVAILABLE")
        return {
            "status": "APP_READY",
            "build_id": snap.build_id,
            "source_batch_id": snap.source_batch_id,
            "data_through": snap.data_through,
            "completed_at": snap.completed_at,
            "sections": snap.sections,
        }

    @app.get("/api/yipman/app-ready/{section}")
    def yipman_app_ready_section(section: str):
        if section not in SNAPSHOT_SECTIONS:
            raise HTTPException(status_code=404, detail="UNKNOWN_APP_READY_SECTION")
        snap = APP_READY_SNAPSHOTS.active()
        if snap is None:
            raise HTTPException(status_code=503, detail="APP_READY_SNAPSHOT_NOT_AVAILABLE")
        return {
            "status": "APP_READY",
            "build_id": snap.build_id,
            "data_through": snap.data_through,
            "section": section,
            "payload": snap.sections[section],
        }

    app.state.yipman_app_ready_api_installed = True
    app.state.request_yipman_app_ready_rebuild = request_app_ready_rebuild
