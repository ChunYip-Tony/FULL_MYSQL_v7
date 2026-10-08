from __future__ import annotations

"""Snapshot-first readers for latency-sensitive Yipman views.

A complete App Ready snapshot is preferred. If the requested key is outside
its precomputed horizon/window, callers fall back to the existing live engine.
"""

from copy import deepcopy
from datetime import date, timedelta
from typing import Any
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS


def _active():
    return APP_READY_SNAPSHOTS.active()


def _section(name: str) -> Any | None:
    snap = _active()
    if snap is None:
        return None
    return snap.sections.get(name)


def _mark(payload: Any, *, basis: str | None = None) -> Any:
    out = deepcopy(payload)
    if isinstance(out, dict):
        snap = _active()
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
