from __future__ import annotations

"""Snapshot-first readers for latency-sensitive Yipman views.

A complete App Ready snapshot is preferred. If the requested key is outside
its precomputed horizon/window, callers fall back to the existing live engine.
"""

from copy import deepcopy
from datetime import date, timedelta
from typing import Any
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS


def _section(name: str) -> Any | None:
    snap = APP_READY_SNAPSHOTS.active()
    if snap is None:
        return None
    return snap.sections.get(name)


def stock_flow_snapshot(days: int, limit: int | None = None) -> Any | None:
    section = _section("stock_flow")
    if not isinstance(section, dict):
        return None
    payload = (section.get("windows") or {}).get(str(int(days)))
    if payload is None:
        return None
    out = deepcopy(payload)
    if isinstance(out, dict):
        rows = out.get("rows")
        if isinstance(rows, list) and limit is not None:
            out["rows"] = rows[: max(0, int(limit))]
        out["app_ready_snapshot"] = True
        snap = APP_READY_SNAPSHOTS.active()
        out["app_ready_build_id"] = snap.build_id if snap else None
        out["data_through"] = out.get("data_through") or (snap.data_through if snap else None)
    return out


def regular_ordering_snapshot(delivery_date: str | None, next_delivery_date: str | None = None) -> Any | None:
    if not delivery_date:
        return None
    # The precompute builder stores the standard D -> D+7 coverage window.
    # A manager-entered custom next-delivery date must use the live engine.
    try:
        expected_next = (date.fromisoformat(str(delivery_date)) + timedelta(days=7)).isoformat()
    except ValueError:
        return None
    if next_delivery_date and str(next_delivery_date) != expected_next:
        return None
    section = _section("ordering_regular")
    if not isinstance(section, dict):
        return None
    payload = (section.get("deliveries") or {}).get(str(delivery_date))
    if payload is None:
        return None
    out = deepcopy(payload)
    if isinstance(out, dict):
        out["app_ready_snapshot"] = True
        snap = APP_READY_SNAPSHOTS.active()
        out["app_ready_build_id"] = snap.build_id if snap else None
        out["data_through"] = out.get("data_through") or (snap.data_through if snap else None)
        out["calculation_basis"] = "PRECOMPUTED_APP_READY_AUTHORITATIVE_ORDERING"
    return out


def tpr_progress_snapshot() -> Any | None:
    payload = _section("price_tpr_progress")
    if payload is None:
        return None
    out = deepcopy(payload)
    if isinstance(out, dict):
        out["app_ready_snapshot"] = True
        snap = APP_READY_SNAPSHOTS.active()
        out["app_ready_build_id"] = snap.build_id if snap else None
    return out
