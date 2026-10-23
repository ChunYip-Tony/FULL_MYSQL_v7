from __future__ import annotations

"""Snapshot-first readers for latency-sensitive Yipman views.

A complete App Ready snapshot is preferred. Existing workers periodically check
the durable ACTIVE pointer so a generation built by another worker becomes
visible without restart or heavy business recomputation on the read path.
"""

from copy import deepcopy
from datetime import date, timedelta
import threading
import time
from typing import Any
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS, SnapshotBuild

_POINTER_TTL_SECONDS = 2.0
_POINTER_LOCK = threading.Lock()
_POINTER_CHECKED_AT = 0.0
_POINTER_LAST_ERROR: str | None = None


def refresh_hot_cache_if_stale(*, force: bool = False) -> bool:
    """Hydrate only when durable ACTIVE differs from this worker's hot cache."""
    global _POINTER_CHECKED_AT, _POINTER_LAST_ERROR
    now = time.monotonic()
    if not force and now - _POINTER_CHECKED_AT < _POINTER_TTL_SECONDS:
        return False
    with _POINTER_LOCK:
        now = time.monotonic()
        if not force and now - _POINTER_CHECKED_AT < _POINTER_TTL_SECONDS:
            return False
        _POINTER_CHECKED_AT = now
        try:
            from yipman_app_ready_persistence import active_build_id, load_active_snapshot
            durable_id = active_build_id()
            local = APP_READY_SNAPSHOTS.active()
            if not durable_id or (local is not None and local.build_id == durable_id):
                _POINTER_LAST_ERROR = None
                return False
            from pipeline_priority import pipeline_pending
            if pipeline_pending():
                _POINTER_LAST_ERROR = 'WAITING_FOR_INGEST_OR_GOOGLE_PUBLICATION'
                return False
            snap = load_active_snapshot(SnapshotBuild)
            if snap is None or snap.build_id != durable_id:
                return False
            APP_READY_SNAPSHOTS.hydrate(snap)
            _POINTER_LAST_ERROR = None
            return True
        except Exception as exc:
            # A read-model synchronization failure must not make the app fail.
            # Keep serving the last complete local generation and retry later.
            _POINTER_LAST_ERROR = f"{type(exc).__name__}: {exc}"
            return False


def pointer_refresh_status() -> dict[str, Any]:
    return {
        "pointer_check_ttl_seconds": _POINTER_TTL_SECONDS,
        "pointer_last_error": _POINTER_LAST_ERROR,
    }


def _active():
    refresh_hot_cache_if_stale()
    return APP_READY_SNAPSHOTS.active()


def _section(name: str) -> Any | None:
    snap = _active()
    if snap is None:
        return None
    return snap.sections.get(name)


def _mark(payload: Any, *, basis: str | None = None) -> Any:
    out = deepcopy(payload)
    if isinstance(out, dict):
        snap = APP_READY_SNAPSHOTS.active()
        out["app_ready_snapshot"] = True
        out["app_ready_build_id"] = snap.build_id if snap else None
        out["data_through"] = out.get("data_through") or (snap.data_through if snap else None)
        if basis:
            out["calculation_basis"] = basis
    return out


def stock_flow_snapshot(days: int, limit: int | None = None) -> Any | None:
    section = _section("stock_flow")
    if not isinstance(section, dict):
        return None
    payload = (section.get("windows") or {}).get(str(int(days)))
    if payload is None:
        return None
    out = _mark(payload, basis="PRECOMPUTED_APP_READY_STOCK_FLOW")
    if isinstance(out, dict):
        rows = out.get("rows")
        if isinstance(rows, list) and limit is not None:
            out["rows"] = rows[: max(0, int(limit))]
    return out


def regular_ordering_snapshot(delivery_date: str | None, next_delivery_date: str | None = None) -> Any | None:
    if not delivery_date:
        return None
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
    return _mark(payload, basis="PRECOMPUTED_APP_READY_AUTHORITATIVE_ORDERING")


def price_snapshot(kind: str, *, limit: int | None = None) -> Any | None:
    names = {
        "reg": "price_reg",
        "tpr": "price_tpr_suggestions",
        "tprprogress": "price_tpr_progress",
        "clearance": "price_clearance",
    }
    section_name = names.get(str(kind or "").lower())
    if not section_name:
        return None
    payload = _section(section_name)
    if payload is None:
        return None
    out = _mark(payload, basis="PRECOMPUTED_APP_READY_PRICE_LIFECYCLE")
    if isinstance(out, dict) and isinstance(out.get("rows"), list) and limit is not None:
        out["rows"] = out["rows"][: max(0, int(limit))]
    return out


def tpr_progress_snapshot(*, limit: int | None = None) -> Any | None:
    return price_snapshot("tprprogress", limit=limit)


def quick_check_snapshot(query: str | None = None) -> Any | None:
    section = _section("quick_check")
    if section is None:
        return None
    if not query:
        return _mark(section, basis="PRECOMPUTED_APP_READY_QUICK_CHECK")
    q = str(query).strip().lower()
    if isinstance(section, dict):
        by_key = section.get("by_key") or section.get("items")
        if isinstance(by_key, dict):
            exact = by_key.get(q) or by_key.get(str(query).strip())
            if exact is not None:
                return _mark(exact, basis="PRECOMPUTED_APP_READY_QUICK_CHECK")
        rows = section.get("rows")
        if isinstance(rows, list):
            matched = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                hay = " ".join(str(row.get(k) or "") for k in ("family", "family_id", "article", "receiving_article", "upc", "ean_upc", "name", "description")).lower()
                if q in hay:
                    matched.append(row)
            if matched:
                return _mark({"rows": matched}, basis="PRECOMPUTED_APP_READY_QUICK_CHECK")
    return None


def decision_intelligence_snapshot(*, family: str | None = None, upc: str | None = None, action_type: str | None = None) -> Any | None:
    section = _section("decision_intelligence")
    if section is None:
        return None
    if not isinstance(section, dict):
        return _mark(section, basis="PRECOMPUTED_APP_READY_DECISION_INTELLIGENCE")
    by_key = section.get("by_key") or section.get("decisions") or {}
    keys = []
    f = str(family or "").strip()
    u = "".join(ch for ch in str(upc or "") if ch.isdigit()).lstrip("0")
    a = str(action_type or "").strip().upper()
    if u and a: keys.extend((f"UPC:{u}:{a}", f"{u}:{a}"))
    if u: keys.extend((f"UPC:{u}", u))
    if f and a: keys.extend((f"FAMILY:{f}:{a}", f"{f}:{a}"))
    if f: keys.extend((f"FAMILY:{f}", f))
    if isinstance(by_key, dict):
        for key in keys:
            payload = by_key.get(key) or by_key.get(key.lower())
            if payload is not None:
                return _mark(payload, basis="PRECOMPUTED_APP_READY_DECISION_INTELLIGENCE")
    return None

