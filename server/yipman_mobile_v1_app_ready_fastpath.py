from __future__ import annotations

"""Install snapshot-first Mobile V1 endpoints for pre-analyzed price/decision data."""

import json
from fastapi.responses import Response
from yipman_app_ready_readers import tpr_progress_snapshot, decision_intelligence_snapshot, quick_check_snapshot, price_snapshot


def _response(payload, path: str):
    return Response(
        json.dumps(payload, default=str),
        media_type="application/json",
        headers={"Cache-Control": "no-store", "X-YipMan-Data-Path": path},
    )


def install_app_ready_fastpath(app) -> None:
    def tpr_progress(category: str = "ALL", limit: int = 1000):
        payload = tpr_progress_snapshot(limit=limit)
        if payload is None:
            return _response({"status": "SNAPSHOT_MISS", "rows": [], "app_ready_snapshot": False}, "SNAPSHOT_MISS")
        return _response(payload, "APP_READY")

    def decision(family: str | None = None, upc: str | None = None, action_type: str | None = None):
        payload = decision_intelligence_snapshot(family=family, upc=upc, action_type=action_type)
        if payload is None:
            return _response({"status": "SNAPSHOT_MISS", "app_ready_snapshot": False}, "SNAPSHOT_MISS")
        return _response(payload, "APP_READY")

    def quick(query: str | None = None):
        payload = quick_check_snapshot(query)
        if payload is None:
            return _response({"status": "SNAPSHOT_MISS", "rows": [], "app_ready_snapshot": False}, "SNAPSHOT_MISS")
        return _response(payload, "APP_READY")

    def prices(kind: str = "reg", limit: int = 1000):
        payload = price_snapshot(kind, limit=limit)
        if payload is None:
            return _response({"status": "SNAPSHOT_MISS", "rows": [], "app_ready_snapshot": False}, "SNAPSHOT_MISS")
        return _response(payload, "APP_READY")

    routes = (
        ("/app/yipman-v1-rc/api/app-ready/tpr-progress", tpr_progress, "yipman_app_ready_tpr_progress"),
        ("/app/yipman-v1-rc/api/app-ready/decision", decision, "yipman_app_ready_decision"),
        ("/app/yipman-v1-rc/api/app-ready/quick-check", quick, "yipman_app_ready_quick_check"),
        ("/app/yipman-v1-rc/api/app-ready/prices", prices, "yipman_app_ready_prices"),
    )
    existing = {getattr(r, "path", None) for r in app.routes}
    for path, fn, name in routes:
        if path not in existing:
            app.add_api_route(path, fn, methods=["GET"], include_in_schema=False, name=name)
