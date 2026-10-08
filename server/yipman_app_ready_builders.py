from __future__ import annotations

"""Concrete App Ready builders backed by the existing authoritative engines.

No business rules are duplicated here.  The snapshot layer calls the same
runtime functions already used by Mobile/Desktop, then stores their results for
fast reads.  Expensive work therefore happens after a data change, not on page
open.
"""

from datetime import timedelta
from typing import Any
import inspect

import api as _api
from business_clock import business_today, completed_through_date
from yipman_mobile_v1_stock_flow import stock_flow_review


def _call_supported(fn, **kwargs):
    """Call a runtime function with only kwargs supported by its signature."""
    sig = inspect.signature(fn)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return fn(**kwargs)
    accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return fn(**accepted)


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("rows")
        return list(rows) if isinstance(rows, list) else []
    return list(payload) if isinstance(payload, list) else []


def _price_type(row: dict[str, Any]) -> str:
    for key in ("suggestion_type", "price_suggestion_type", "recommendation_type", "target_price_type", "price_type"):
        value = str(row.get(key) or "").strip().upper().replace("-", "_").replace(" ", "_")
        if value:
            return value
    return ""


def _pricing_payload() -> Any:
    return _api.backoffice_cached_pricing_review(category="ALL", limit=1000)


def _price_section(kind: str) -> dict[str, Any]:
    payload = _pricing_payload()
    rows = _rows(payload)
    if kind == "REG":
        selected = [r for r in rows if _price_type(r) in {"REG", "REGULAR", "KEEP_REG", "CHANGE_REG"}]
    elif kind == "TPR":
        selected = [r for r in rows if "TPR" in _price_type(r) and "CLEAR" not in _price_type(r)]
    elif kind == "CLEARANCE":
        selected = [r for r in rows if "CLEAR" in _price_type(r)]
    else:
        selected = rows
    return {"source": "BACKOFFICE_CACHED_PRICING_REVIEW", "kind": kind, "rows": selected, "all_row_count": len(rows)}


def _stock_flow() -> dict[str, Any]:
    return {
        "source": "STOCK_FLOW_REVIEW",
        "windows": {
            "7": stock_flow_review(days=7, limit=120),
            "14": stock_flow_review(days=14, limit=120),
            "28": stock_flow_review(days=28, limit=120),
        },
    }


def _quick_check() -> Any:
    # Empty query is intentionally used as the all-active roster request when
    # supported. Signature filtering preserves compatibility with older builds.
    return _call_supported(_api.search_quick_check, query="", q="", limit=5000)


def _regular_ordering() -> dict[str, Any]:
    today = business_today()
    days: dict[str, Any] = {}
    # Precompute the complete upcoming 14-day delivery horizon.  Each delivery
    # covers to D+7 by the established regular ordering cadence.
    for offset in range(0, 14):
        delivery = today + timedelta(days=offset)
        next_delivery = delivery + timedelta(days=7)
        days[delivery.isoformat()] = _call_supported(
            _api.backoffice_cached_ordering_review,
            category="ALL",
            delivery_date=delivery,
            next_delivery_date=next_delivery,
            best_available_delivery_evidence=True,
        )
    return {"source": "BACKOFFICE_CACHED_ORDERING_REVIEW", "horizon_days": 14, "deliveries": days}


def _promotion_ordering() -> dict[str, Any]:
    # Promotion lists and their historical SALE evidence are persisted by the
    # existing promotion subsystem.  Preload all saved lists; individual order
    # calculations remain deterministic functions of the saved promo inputs.
    lists = _call_supported(_api.list_yipman_promotion_lists, limit=1000)
    return {"source": "PROMOTION_ORDERING", "saved_lists": lists}


def _tpr_progress() -> Any:
    return _api.backoffice_cached_current_tpr_review(category="ALL", limit=1000)


def _inventory() -> Any:
    return _call_supported(_api.backoffice_inventory_review, category="ALL", limit=5000)


def _performance() -> dict[str, Any]:
    latest = _call_supported(_api.v2_latest_performance_date)
    supported = _call_supported(_api.v2_performance_supported_dates, limit=28)
    return {"source": "PERFORMANCE_RUNTIME", "latest": latest, "supported_dates": supported}


def _decision_intelligence() -> dict[str, Any]:
    # Store the authoritative ingredients used by the UI's decision/WHY layer.
    # This avoids a second expensive fetch when a manager opens a detail card.
    pricing = _pricing_payload()
    tpr = _tpr_progress()
    ordering = _regular_ordering()
    return {
        "source": "AUTHORITATIVE_EXISTING_ENGINES",
        "pricing": pricing,
        "tpr_progress": tpr,
        "ordering": ordering,
        "data_through": completed_through_date().isoformat(),
        "policy": "PRECOMPUTED_AFTER_DATA_CHANGE_NOT_ON_PAGE_OPEN",
    }


def app_ready_builders() -> dict[str, Any]:
    return {
        "stock_flow": _stock_flow,
        "quick_check": _quick_check,
        "ordering_regular": _regular_ordering,
        "ordering_promotion": _promotion_ordering,
        "price_reg": lambda: _price_section("REG"),
        "price_tpr_suggestions": lambda: _price_section("TPR"),
        "price_tpr_progress": _tpr_progress,
        "price_clearance": lambda: _price_section("CLEARANCE"),
        "inventory": _inventory,
        "performance": _performance,
        "decision_intelligence": _decision_intelligence,
    }
