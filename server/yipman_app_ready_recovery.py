"""Recover missed App Ready rebuilds from committed serving publications.

Runs outside request/startup threads. A durable generation can survive restarts
while its ingest callback was lost or fired before Phase 3 finished. Compare
publication times, including same-batch repairs, instead of trusting existence.
"""
from datetime import datetime, timezone
import logging
import threading

_LOG = logging.getLogger(__name__)
_LOCK = threading.Lock()
_THREAD = None
_STOP = None
_STATUS = {"state": "NOT_CHECKED"}


def _utc(value):
    if not value:
        return None
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def publication_needs_rebuild(snapshot, serving):
    if serving.get("processing_status") not in {"QUICK_CHECK_READY", "QUICK_CHECK_READY_WITH_HOLDS"}:
        return False
    updated = _utc(serving.get("updated_at"))
    if not serving.get("batch_id") or updated is None:
        return False
    if snapshot is None:
        return True
    # Use build start, not completion: data committed during a build must get
    # another pass. Never mistake the age of the business date for cache age.
    started = _utc(snapshot.started_at)
    return started is None or updated > started


def _serving_publication():
    from db import db_conn
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("""SELECT MAX(publish_batch_id) AS batch_id,
                                  MAX(published_at) AS updated_at
                           FROM quick_check_current
                           WHERE COALESCE(quick_check_status,'') <> 'HISTORICAL_ONLY'""")
            serving = cur.fetchone() or {}
            if serving.get("batch_id"):
                cur.execute("SELECT processing_status FROM ingest_batch WHERE batch_id=%s", (serving["batch_id"],))
                serving.update(cur.fetchone() or {})
            return serving
        finally:
            cur.close()


def reconcile_app_ready_source():
    global _STATUS
    from pipeline_priority import pipeline_pending
    from yipman_app_ready_api import _coordinator_status, request_app_ready_rebuild
    from yipman_app_ready_readers import refresh_hot_cache_if_stale
    from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS
    checked = datetime.now(timezone.utc).isoformat()
    try:
        if _coordinator_status()[0]:
            _STATUS = {"state": "REBUILD_RUNNING", "checked_at": checked}
            return
        if pipeline_pending():
            _STATUS = {"state": "WAITING_FOR_PIPELINE", "checked_at": checked}
            return
        refresh_hot_cache_if_stale()
        serving = _serving_publication()
        due = publication_needs_rebuild(APP_READY_SNAPSHOTS.active(), serving)
        _STATUS = {"state": "REBUILD_REQUESTED" if due else "NO_REBUILD_DUE",
                   "checked_at": checked, "source_batch_id": serving.get("batch_id"),
                   "source_updated_at": str(serving.get("updated_at") or "")}
        if due:
            request_app_ready_rebuild(source_batch_id=str(serving["batch_id"]))
    except Exception as exc:
        _STATUS = {"state": "CHECK_FAILED", "checked_at": checked,
                   "error": f"{type(exc).__name__}: {exc}"}
        _LOG.exception("App Ready source recovery failed; will retry")


def recovery_status():
    return dict(_STATUS)


def start_app_ready_recovery():
    global _THREAD, _STOP
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return
        stop = threading.Event()
        _STOP = stop

        def run():
            while not stop.is_set():
                reconcile_app_ready_source()
                # Bounded retries also recover failed builders. Unchanged
                # publications do not cause another expensive snapshot build.
                stop.wait(60)

        _THREAD = threading.Thread(target=run, name="app-ready-source-recovery", daemon=True)
        _THREAD.start()


def stop_app_ready_recovery():
    with _LOCK:
        if _STOP is not None:
            _STOP.set()
