from __future__ import annotations

"""Fast-read API and lossless coalescing rebuild coordinator for App Ready snapshots."""

import threading

from fastapi import HTTPException

from business_clock import completed_through_date
from yipman_app_ready_builders import app_ready_builders
from yipman_app_ready_snapshot import (
    APP_READY_SNAPSHOTS,
    SNAPSHOT_SECTIONS,
    build_app_ready_snapshot,
)

# Coordinator state is protected by one lock.  A request first records its
# source and only then decides whether it must start the single worker.  This
# closes the old check-then-start race where two callers could both see an idle
# build lock, start two threads, and have the losing thread silently return.
_COORDINATOR_LOCK = threading.Lock()
_WORKER_RUNNING = False
_PENDING_SOURCE: str | None = None


def _coordinator_status() -> tuple[bool, str | None]:
    with _COORDINATOR_LOCK:
        return _WORKER_RUNNING, _PENDING_SOURCE


def rebuild_app_ready_snapshot(*, source_batch_id=None) -> None:
    """Run one worker until the latest queued rebuild request is consumed.

    Direct callers are safe too: a missing source is normalized instead of
    producing the previous no-op `while source` behavior.
    """
    global _WORKER_RUNNING, _PENDING_SOURCE

    source = str(source_batch_id or "UNSPECIFIED")
    with _COORDINATOR_LOCK:
        if _WORKER_RUNNING:
            _PENDING_SOURCE = source
            return
        _WORKER_RUNNING = True

    try:
        while True:
            build_app_ready_snapshot(
                app_ready_builders(),
                source_batch_id=source,
                data_through=completed_through_date().isoformat(),
            )
            with _COORDINATOR_LOCK:
                if _PENDING_SOURCE is None:
                    _WORKER_RUNNING = False
                    return
                source = _PENDING_SOURCE
                _PENDING_SOURCE = None
    except Exception:
        # Do not strand the coordinator in RUNNING after a builder failure.
        # Keep any queued source available for the next request/status view.
        with _COORDINATOR_LOCK:
            _WORKER_RUNNING = False
        raise


def request_app_ready_rebuild(*, source_batch_id=None) -> bool:
    """Queue a rebuild without dropping requests during worker startup/build."""
    global _WORKER_RUNNING, _PENDING_SOURCE

    source = str(source_batch_id or "UNSPECIFIED")
    with _COORDINATOR_LOCK:
        if _WORKER_RUNNING:
            # Coalesce to the newest source. One complete replacement after the
            # current generation is enough because builders read current truth.
            _PENDING_SOURCE = source
            return True
        _WORKER_RUNNING = True

    # Worker ownership was reserved atomically above. The worker therefore
    # starts in the already-running state and cannot race another requester.
    def worker() -> None:
        global _WORKER_RUNNING, _PENDING_SOURCE
        current = source
        try:
            while True:
                build_app_ready_snapshot(
                    app_ready_builders(),
                    source_batch_id=current,
                    data_through=completed_through_date().isoformat(),
                )
                with _COORDINATOR_LOCK:
                    if _PENDING_SOURCE is None:
                        _WORKER_RUNNING = False
                        return
                    current = _PENDING_SOURCE
                    _PENDING_SOURCE = None
        except Exception:
            with _COORDINATOR_LOCK:
                _WORKER_RUNNING = False
            # Background refresh failure must not crash an authoritative write
            # request. Snapshot status retains the last complete generation.
            return

    try:
        threading.Thread(
            target=worker,
            name="yipman-app-ready-rebuild",
            daemon=True,
        ).start()
    except Exception:
        with _COORDINATOR_LOCK:
            _WORKER_RUNNING = False
        raise
    return True


def install_app_ready_api(app) -> None:
    if getattr(app.state, "yipman_app_ready_api_installed", False):
        return

    @app.on_event("startup")
    def _build_app_ready_on_startup():
        request_app_ready_rebuild(source_batch_id="STARTUP")

    @app.get("/api/yipman/app-ready/status")
    def yipman_app_ready_status():
        worker_running, queued_source = _coordinator_status()
        out = APP_READY_SNAPSHOTS.status()
        out["rebuild_worker_running"] = worker_running
        out["rebuild_queued"] = queued_source is not None
        out["queued_source"] = queued_source
        return out

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
            "build_ms": snap.build_ms,
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
