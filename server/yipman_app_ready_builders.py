from __future__ import annotations

"""Concrete App Ready builders backed by existing authoritative engines."""

from copy import deepcopy
from datetime import timedelta
import inspect
from typing import Any

import api as _api
from business_clock import business_today, completed_through_date
from yipman_mobile_v1_stock_flow import stock_flow_review


def _call_supported(fn, **kwargs):
    sig = inspect.signature(fn)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return fn(**kwargs)
    return fn(**{k: v for k, v in kwargs.items() if k in sig.parameters})


def _rows(payload):
    if isinstance(payload, dict):
        return list(payload.get("rows")) if isinstance(payload.get("rows"), list) else []
    return list(payload) if isinstance(payload, list) else []


def _price_type(row):
    for key in (
        "suggestion_type",
        "price_suggestion_type",
        "recommendation_type",
        "target_price_type",
        "price_type",
    ):
        value = str(row.get(key) or "").strip().upper().replace("-", "_").replace(" ", "_")
        if value:
            return value
    return ""


def _price_section_from(payload, kind):
    rows = _rows(payload)
    if kind == "REG":
        selected = [r for r in rows if _price_type(r) in {"REG", "REGULAR", "KEEP_REG", "CHANGE_REG"}]
    elif kind == "TPR":
        selected = [r for r in rows if "TPR" in _price_type(r) and "CLEAR" not in _price_type(r)]
    elif kind == "CLEARANCE":
        selected = [r for r in rows if "CLEAR" in _price_type(r)]
    else:
        selected = rows
    return {
        "source": "BACKOFFICE_CACHED_PRICING_REVIEW",
        "kind": kind,
        "rows": selected,
        "all_row_count": len(rows),
    }


def _stock_flow():
    return {
        "source": "STOCK_FLOW_REVIEW",
        "windows": {str(days): stock_flow_review(days=days, limit=120) for days in (7, 14, 28)},
    }


def _quick_check():
    return _call_supported(_api.search_quick_check, query="", q="", limit=5000)


def _regular_ordering():
    today = business_today()
    deliveries = {}
    for offset in range(14):
        delivery = today + timedelta(days=offset)
        next_delivery = delivery + timedelta(days=7)
        deliveries[delivery.isoformat()] = _call_supported(
            _api.backoffice_cached_ordering_review,
            category="ALL",
            delivery_date=delivery,
            next_delivery_date=next_delivery,
            best_available_delivery_evidence=True,
        )
    return {
        "source": "BACKOFFICE_CACHED_ORDERING_REVIEW",
        "horizon_days": 14,
        "deliveries": deliveries,
    }


def _promotion_ordering():
    return {
        "source": "PROMOTION_ORDERING",
        "saved_lists": _call_supported(_api.list_yipman_promotion_lists, limit=1000),
    }


def _normalize_tpr_progress(payload):
    """Expose one unambiguous App Ready TPR evidence contract.

    The authoritative runtime names the current price `current_tpr_price` and the
    observed velocity `tpr_velocity_3d`.  Preserve those fields and add stable
    aliases used by generic decision/detail renderers.  A row blocked by Quick
    Check readiness is explicitly DATA_NEEDED even if the legacy runtime kept
    the temporary price unchanged with a CONTINUE_TPR compatibility action.
    """
    if not isinstance(payload, dict):
        return payload
    out = deepcopy(payload)
    normalized = []
    for source in _rows(out):
        row = dict(source)
        current_price = row.get("current_tpr_price")
        if current_price is None:
            current_price = row.get("current_price")
        velocity = row.get("tpr_velocity_3d")
        if velocity is None:
            velocity = (row.get("current_behavior") or {}).get("velocity")

        row["current_price"] = current_price
        row["tpr_velocity"] = velocity
        row["effective_oh"] = row.get("current_oh")

        readiness = str(row.get("readiness") or "").strip().upper()
        blocker = str(row.get("blocking_reason") or "").strip()
        missing = []
        if current_price is None:
            missing.append("CURRENT_TPR_PRICE")
        if row.get("current_oh") is None:
            missing.append("EFFECTIVE_OH")
        if velocity is None:
            missing.append("TPR_VELOCITY")
        if readiness and readiness != "READY":
            missing.append("ITEM_READINESS")
        if blocker:
            missing.append("BLOCKING_REASON")

        row["decision_evidence_ready"] = not missing
        row["decision_missing_evidence"] = list(dict.fromkeys(missing))
        if missing:
            row["operational_decision_code"] = "DATA_NEEDED"
            row["operational_decision_label"] = "DATA NEEDED"
        else:
            row["operational_decision_code"] = row.get("recommendation_code")
            row["operational_decision_label"] = row.get("recommendation_label")
        normalized.append(row)

    out["rows"] = normalized
    out["app_ready_evidence_contract"] = "TPR_PROGRESS_V2_EXPLICIT_READINESS"
    return out


def _tpr_progress():
    return _normalize_tpr_progress(
        _api.backoffice_cached_current_tpr_review(category="ALL", limit=1000)
    )


def _inventory():
    return _call_supported(_api.backoffice_inventory_review, category="ALL", limit=5000)


def _performance():
    return {
        "source": "PERFORMANCE_RUNTIME",
        "latest": _call_supported(_api.v2_latest_performance_date),
        "supported_dates": _call_supported(_api.v2_performance_supported_dates, limit=28),
    }


def _digits(value):
    return "".join(c for c in str(value or "") if c.isdigit()).lstrip("0")


def _family(row):
    return str(
        row.get("family")
        or row.get("family_article")
        or row.get("family_id")
        or row.get("main_article_number")
        or ""
    ).strip()


def _upc(row):
    return _digits(row.get("upc") or row.get("ean_upc") or row.get("ean"))


def _decision_index(pricing, tpr, ordering):
    """Exact UPC keys win; family keys are only family-level fallbacks."""
    by = {}

    def add(row, action=""):
        if not isinstance(row, dict):
            return
        upc = _upc(row)
        family = _family(row)
        action_name = str(action or _price_type(row)).strip().upper()
        if upc:
            by.setdefault("UPC:" + upc, row)
            if action_name:
                by.setdefault("UPC:" + upc + ":" + action_name, row)
        if family:
            by.setdefault("FAMILY:" + family, row)
            if action_name:
                by.setdefault("FAMILY:" + family + ":" + action_name, row)

    for row in _rows(pricing):
        add(row)
    for row in _rows(tpr):
        add(row, "TPR_PROGRESS")
    for day in (ordering.get("deliveries") or {}).values():
        for row in _rows(day):
            add(row, "ORDERING")
    return by


def app_ready_builders() -> dict[str, Any]:
    cache = {}

    def once(key, fn):
        def get():
            if key not in cache:
                cache[key] = fn()
            return cache[key]
        return get

    pricing = once(
        "pricing",
        lambda: _api.backoffice_cached_pricing_review(category="ALL", limit=1000),
    )
    ordering = once("ordering", _regular_ordering)
    tpr = once("tpr", _tpr_progress)
    quick = once("quick", _quick_check)

    def decision():
        pricing_payload, tpr_payload, ordering_payload = pricing(), tpr(), ordering()
        return {
            "source": "AUTHORITATIVE_EXISTING_ENGINES",
            "pricing": pricing_payload,
            "tpr_progress": tpr_payload,
            "ordering": ordering_payload,
            "by_key": _decision_index(pricing_payload, tpr_payload, ordering_payload),
            "data_through": completed_through_date().isoformat(),
            "policy": "PRECOMPUTED_AFTER_DATA_CHANGE_NOT_ON_PAGE_OPEN",
        }

    return {
        "stock_flow": _stock_flow,
        "quick_check": quick,
        "ordering_regular": ordering,
        "ordering_promotion": _promotion_ordering,
        "price_reg": lambda: _price_section_from(pricing(), "REG"),
        "price_tpr_suggestions": lambda: _price_section_from(pricing(), "TPR"),
        "price_tpr_progress": tpr,
        "price_clearance": lambda: _price_section_from(pricing(), "CLEARANCE"),
        "inventory": _inventory,
        "performance": _performance,
        "decision_intelligence": decision,
    }
