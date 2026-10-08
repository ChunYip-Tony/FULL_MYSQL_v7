from __future__ import annotations

"""Connect successful ingest commits to the Yipman App Ready rebuild pipeline.

The canonical v7_ingest.commit_batch implementation remains the only commit
engine.  This hook wraps the API module's imported callable after routes are
registered; FastAPI endpoint functions resolve that module global at request
time, so both authenticated and browser-upload commit routes gain the same
post-commit behavior without duplicating ingest logic.
"""

from typing import Any, Callable


def _batch_id(result: Any, session_id: str) -> str:
    if isinstance(result, dict):
        for key in ("batch_id", "ingest_batch_id", "batch", "session_id"):
            value = result.get(key)
            if value not in (None, ""):
                return str(value)
    return str(session_id)


def install_app_ready_ingest_hook(app, api_module, request_rebuild: Callable[..., bool]) -> None:
    if getattr(app.state, "yipman_app_ready_ingest_hook_installed", False):
        return

    base_commit = api_module.commit_batch
    if getattr(base_commit, "_yipman_app_ready_wrapped", False):
        app.state.yipman_app_ready_ingest_hook_installed = True
        return

    def commit_batch_with_app_ready(session_id: str, device: str):
        # Rebuild is requested only after the canonical commit returns
        # successfully.  Any commit exception propagates unchanged and cannot
        # publish a snapshot from failed/partial ingest work.
        result = base_commit(session_id, device)
        request_rebuild(source_batch_id=_batch_id(result, session_id))
        return result

    commit_batch_with_app_ready._yipman_app_ready_wrapped = True
    commit_batch_with_app_ready._yipman_app_ready_base = base_commit
    api_module.commit_batch = commit_batch_with_app_ready
    app.state.yipman_app_ready_ingest_hook_installed = True
