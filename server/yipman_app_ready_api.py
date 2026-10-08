from __future__ import annotations

"""Fast-read API surface for the precomputed Yipman App Ready snapshot."""

from fastapi import HTTPException
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS, SNAPSHOT_SECTIONS


def install_app_ready_api(app) -> None:
    if getattr(app.state, "yipman_app_ready_api_installed", False):
        return

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
