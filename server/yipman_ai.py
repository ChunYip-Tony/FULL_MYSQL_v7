from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import date
from decimal import Decimal
from typing import Any

import requests

from business_clock import business_today, completed_through_date
from quick_check_app import search_quick_check
from backoffice_runtime import (
    cached_ordering_review,
    cached_pricing_review,
    yipman_best_sellers,
    yipman_ordering_calendar,
)
from qa_resolution import qa_review
from webapp_v2_runtime import (
    family_info,
    latest_performance_date,
    performance_range,
    search_items,
    upc_info,
)


OPENAI_RESPONSES_URL = os.environ.get(
    "OPENAI_RESPONSES_URL",
    "https://api.openai.com/v1/responses",
).strip()
DEFAULT_MODEL = os.environ.get("OPENAI_YIPMAN_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"
MAX_HISTORY_MESSAGES = 10
MAX_MESSAGE_CHARS = 1600
MAX_TOOL_ROUNDS = 5
RATE_WINDOW_SECONDS = 60
RATE_MAX_REQUESTS = 12

_rate_lock = threading.Lock()
_rate_hits: dict[str, deque[float]] = defaultdict(deque)


def _json_default(value: Any) -> Any:
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _compact_json(value: Any) -> str:
    return json.dumps(value, default=_json_default, separators=(",", ":"), ensure_ascii=False)


def _parse_iso_date(value: Any, *, required: bool = True) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        if required:
            raise ValueError("DATE_REQUIRED")
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("DATE_MUST_BE_YYYY_MM_DD") from exc


def _norm_num(value: Any) -> str:
    raw = "".join(ch for ch in str(value or "") if ch.isdigit())
    return raw.lstrip("0") or raw


def _norm_text(value: Any) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in str(value or "")).split()
    )


def _check_rate_limit(client_key: str) -> None:
    key = str(client_key or "unknown")[:160]
    now = time.monotonic()
    with _rate_lock:
        q = _rate_hits[key]
        while q and now - q[0] > RATE_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= RATE_MAX_REQUESTS:
            raise RuntimeError("AI_RATE_LIMIT")
        q.append(now)


def _item_search_query(query: str) -> str:
    """Ignore conversational filler, preserving product and package qualifiers."""
    raw = str(query or "").strip()
    if raw.isdigit():
        return raw
    tokens = _norm_text(raw).split()
    stop = {"a", "an", "the", "in", "of", "for", "please"}
    meaningful = [token for token in tokens if token not in stop]
    return " ".join(meaningful) or raw


def _search_refs(query: str) -> tuple[set[str], set[str], list[dict[str, Any]]]:
    payload = search_items(_item_search_query(query), 30)
    rows = list(payload.get("results") or [])
    upcs: set[str] = set()
    families: set[str] = set()
    for row in rows:
        rtype = str(row.get("result_type") or "").upper()
        number = row.get("number")
        if rtype == "UPC" and number:
            upcs.add(_norm_num(number))
        fam = row.get("family_article_number")
        if fam:
            families.add(str(fam).strip())
        if rtype == "FAMILY" and number:
            families.add(str(number).strip())
    return upcs, families, rows


def _filter_item_rows(rows: list[dict[str, Any]], query: str | None) -> list[dict[str, Any]]:
    term = str(query or "").strip()
    if not term:
        return rows
    upcs, families, _ = _search_refs(term)
    tokens = [x for x in _norm_text(term).split() if x]
    out = []
    for row in rows:
        row_upc = _norm_num(row.get("upc") or row.get("ean_upc"))
        family = str(row.get("family_article_number") or row.get("family_article") or "").strip()
        hay = _norm_text(
            " ".join(
                str(x or "")
                for x in (
                    row.get("name"),
                    row.get("family_name"),
                    row.get("upc"),
                    row.get("family_article_number"),
                )
            )
        )
        if (
            (row_upc and row_upc in upcs)
            or (family and family in families)
            or (tokens and all(t in hay for t in tokens))
        ):
            out.append(row)
    return out


def _resolve_family(query: str) -> str:
    raw = str(query or "").strip()
    if not raw:
        raise ValueError("ITEM_QUERY_REQUIRED")
    if raw.isdigit():
        try:
            info = family_info(raw)
            return str(info.get("family_article_number") or raw)
        except Exception:
            pass
    _, _, results = _search_refs(raw)
    preferred = (
        next((x for x in results if str(x.get("result_type") or "").upper() == "FAMILY"), None)
        or next((x for x in results if x.get("family_article_number")), None)
    )
    if not preferred:
        raise ValueError("FAMILY_NOT_FOUND")
    key = preferred.get("number") if str(preferred.get("result_type") or "").upper() == "FAMILY" else preferred.get("family_article_number")
    if not key:
        raise ValueError("FAMILY_NOT_FOUND")
    return str(key)


def _sales_tool(args: dict[str, Any]) -> dict[str, Any]:
    start = _parse_iso_date(args.get("start_date"))
    end = _parse_iso_date(args.get("end_date"), required=False) or start
    if start > end:
        raise ValueError("START_DATE_AFTER_END_DATE")
    item_query = _item_search_query(str(args.get("item_query") or "")) or None
    result = performance_range(start, end, 2000, item_query=item_query, include_gp=not args.get('_quantity_only', False))
    items = list(result.get("items") or [])
    matched = items  # The canonical range query already scopes item names/identities.
    chosen = matched if item_query else items
    chosen = sorted(
        chosen,
        key=lambda x: (
            -float(x.get("sales_amount") or 0),
            -float(x.get("sold_quantity") or 0),
            str(x.get("name") or ""),
        ),
    )
    sales = sum((Decimal(str(x.get("sales_amount") or 0)) for x in chosen), Decimal("0"))
    qty_by_uom: dict[str, Decimal] = {}
    gp_complete = bool(chosen) and all(x.get("gp_dollars") is not None for x in chosen)
    gp = Decimal("0")
    for row in chosen:
        uom = str(row.get("qty_uom") or row.get("selling_uom") or "UNIT").upper()
        qty_by_uom[uom] = qty_by_uom.get(uom, Decimal("0")) + Decimal(str(row.get("sold_quantity") or 0))
        if row.get("gp_dollars") is not None:
            gp += Decimal(str(row.get("gp_dollars") or 0))

    payload: dict[str, Any] = {
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "supported_day_count": result.get("supported_day_count"),
        "supported_dates": result.get("supported_dates"),
        "missing_calendar_dates_are_zero": result.get("missing_calendar_dates_are_zero"),
        "item_query": item_query,
        "matched_item_count": len(chosen),
        "sales_dollars": sales,
        "sold_quantity_by_uom": qty_by_uom,
        "gp_dollars": gp if gp_complete else None,
        "gp_complete": gp_complete,
        "top_items": chosen[:20],
    }
    if not item_query:
        payload["department_summary"] = result.get("summary")
    return payload


def _item_tool(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("ITEM_QUERY_REQUIRED")
    results = _catalog_search_rows(query)
    compact = []
    for row in results[:12]:
        compact.append({
            "result_type": row.get("result_type"),
            "number": row.get("number"),
            "name": row.get("name"),
            "family_article_number": row.get("family_article_number"),
            "family_name": row.get("family_name"),
            "category": row.get("category"),
            "selling_uom": row.get("selling_uom"),
            "current_price": row.get("current_price"),
            "current_price_type": row.get("current_price_type"),
            "current_price_asof_date": row.get("current_price_asof_date"),
            "qty_28d": row.get("qty_28d"),
            "supported_days_28d": row.get("supported_days_28d"),
        })
    return {"query": query, "count": len(compact), "results": compact}


def _inventory_result(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_article_number": info.get("family_article_number"),
        "family_article_name": info.get("family_article_name"),
        "category": info.get("category"),
        "current_effective_oh": info.get("current_effective_oh"),
        "family_sales_7d": info.get("family_sales_7d"),
        "family_sales_28d": info.get("family_sales_28d"),
        "observed_delivery": info.get("observed_delivery"),
        "last_receipt": info.get("last_receipt"),
        "next_expected_delivery_date": info.get("next_expected_delivery_date"),
        "related_upcs": (info.get("related_upcs") or [])[:12],
        "receiving_ordering_articles": (info.get("receiving_ordering_articles") or [])[:12],
    }


def _inventory_tool(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        return {"needs_details": True, "question": "Which product do you mean?"}
    if query.isdigit():
        try:
            return _inventory_result(family_info(query))
        except (KeyError, ValueError):
            pass
    rows = _catalog_search_rows(query)
    if query.isdigit():
        exact = [row for row in rows if _norm_num(row.get("number")) == _norm_num(query)]
        if exact:
            rows = exact
    active = [row for row in rows if Decimal(str(row.get("pos_qty_7d") or 0)) > 0
              or str(row.get("readiness") or "").upper() == "READY"]
    if active:
        rows = active
    families = {}
    for row in rows:
        family = str(row.get("family_article_number") or "")
        if family:
            families.setdefault(family, row)
    if len(families) != 1:
        return {"needs_details": True, "question": "Which product do you mean?",
                "options": list(families.values())[:5]}
    return _inventory_result(family_info(next(iter(families))))



def _catalog_search_rows(query: str) -> list[dict[str, Any]]:
    """Price identification needs current catalog facts, not per-alias history."""
    data = search_quick_check(_item_search_query(query), 30)
    return [{
        "result_type": "UPC",
        "number": row.get("ean_upc"),
        "name": row.get("selling_description"),
        "family_article_number": row.get("main_article_number"),
        "readiness": row.get("quick_check_status"),
        "pos_qty_7d": row.get("pos_qty_7d"),
        "selling_uom": row.get("selling_uom"),
        "current_price": row.get("current_price"),
        "current_price_type": row.get("current_price_type"),
        "current_price_asof_date": row.get("current_price_asof_date"),
    } for row in data.get("results") or [] if row.get("ean_upc")]


def _clarification_result(result: dict[str, Any], tool_names: list[str], question: str = "") -> dict[str, Any]:
    language = "es" if "reply in spanish." in question.lower() else "yue" if "reply in cantonese" in question.lower() else "en"
    def copy(en: str, es: str, yue: str) -> str:
        return es if language == "es" else yue if language == "yue" else en
    original = str(result.get("question") or "Could you clarify what you mean?")
    translations = {
        "Which product do you mean?": copy(original, "¿Qué producto quieres decir?", "你指邊款商品？"),
        "What are the delivery date and the next delivery date?": copy(original, "¿Cuáles son la fecha de entrega y la siguiente fecha de entrega?", "今次同下一次幾時到貨？"),
        "I could not match that product. What name or UPC is on its label?": copy(original, "No pude encontrar ese producto. ¿Qué nombre o UPC aparece en la etiqueta?", "未搵到呢款商品，標籤有咩名稱或 UPC？"),
        "The next delivery must be after the first delivery. What are the two dates?": copy(original, "La siguiente entrega debe ser posterior a la primera. ¿Cuáles son las dos fechas?", "下一次到貨要喺今次之後，兩次到貨日期係幾時？"),
    }
    answer = translations.get(original, original if language == "en" else copy(original, "¿Puedes aclarar la información que falta?", "可唔可以補充缺少嘅資料？"))
    options = result.get("options") or []
    if options:
        lines = [answer, "", copy("| Product | Current price |", "| Producto | Precio actual |", "| 商品 | 現價 |"), "| --- | --- |"]
        dates = set()
        for row in options:
            name = str(row.get("name") or row.get("number") or "Product").replace("|", "/").replace("\n", " ")
            price = row.get("current_price")
            unit = str(row.get("selling_uom") or "").upper()
            unit = {"LB": "per lb", "LBS": "per lb", "EA": "each", "PACK": "per pack", "PAC": "per pack"}.get(unit, unit.lower())
            unit = {"per lb": copy("per lb", "por lb", "每磅"), "each": copy("each", "cada uno", "每件"), "per pack": copy("per pack", "por paquete", "每包")}.get(unit, unit)
            label = f"${Decimal(str(price)):,.2f} {unit}".strip() if price is not None else copy("Not confirmed", "Sin confirmar", "未確認")
            lines.append(f"| {name} | {label} |")
            if row.get("current_price_asof_date"):
                dates.add(str(row["current_price_asof_date"]))
        if dates:
            lines.extend(["", copy("Price records: ", "Precios registrados: ", "價格記錄：") + ", ".join(sorted(dates)) + "."])
        answer = "\n".join(lines)
    return {"answer": answer, "model": None, "read_only": True,
            "tool_calls": tool_names, "mode": "DETAILS_REQUIRED"}


def _price_tool(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    category = str(args.get("category") or "ALL").strip().upper()
    if category not in {"ALL", "LIVE", "FRESH", "FROZEN"}:
        category = "ALL"
    search_rows = _catalog_search_rows(query) if query else []
    candidates = [row for row in search_rows
                  if str(row.get("result_type") or "").upper() == "UPC"
                  and row.get("number")]
    if query.isdigit():
        exact = [row for row in candidates if _norm_num(row.get("number")) == _norm_num(query)]
        if exact:
            candidates = exact
    else:
        active = [row for row in candidates
                  if Decimal(str(row.get("qty_28d") or row.get("pos_qty_7d") or 0)) > 0
                  or str(row.get("readiness") or "").upper() == "READY"]
        if active:
            candidates = active
    families = {str(row.get("family_article_number") or row.get("number")) for row in candidates}
    if query and len(families) > 1:
        options = []
        seen = set()
        for row in candidates:
            family = str(row.get("family_article_number") or row.get("number"))
            if family in seen:
                continue
            seen.add(family)
            options.append({key: row.get(key) for key in
                            ("number", "name", "family_article_number", "selling_uom",
                             "current_price", "current_price_type", "current_price_asof_date")})
            if len(options) >= 5:
                break
        return {"needs_details": True, "question": "Which product do you mean?",
                "query": query, "options": options,
                "upc_details": [], "price_suggestions": []}
    if query and not candidates:
        return {"needs_details": True,
                "question": "I could not match that product. What name or UPC is on its label?",
                "query": query, "upc_details": [], "price_suggestions": []}
    # One product lookup includes stock/cost context; don't load historical aliases.
    upc_details = []
    for row in candidates[:1]:
        try:
            upc_details.append(upc_info(str(row["number"])))
        except Exception as exc:
            upc_details.append({"upc": row["number"], "data_error": str(exc)})
    review = cached_pricing_review(category=category, limit=1000)
    suggestions = list(review.get("rows") or [])
    if query:
        upcs = {_norm_num(row.get("number")) for row in candidates}
        family_keys = {str(row["family_article_number"]) for row in candidates if row.get("family_article_number")}
        suggestions = [row for row in suggestions
                       if _norm_num(row.get("upc") or row.get("ean_upc")) in upcs
                       or str(row.get("family_article_number") or row.get("family_article") or "") in family_keys]
    suggestions = sorted(
        suggestions,
        key=lambda x: (
            0 if x.get("priority_240_249_mismatch") else 1,
            0 if x.get("actionable") else 1,
            -float(x.get("gp_per_day_opportunity") or 0),
            str(x.get("name") or ""),
        ),
    )
    return {
        "query": query or None,
        "category": category,
        "analysis_status": review.get("analysis_status"),
        "source_changed_since_analysis": review.get("source_changed_since_analysis", False),
        "refreshing": review.get("refreshing", False),
        "data_health": review.get("current_source_health") or review.get("data_health"),
        "upc_details": upc_details,
        "price_suggestions": suggestions[:20],
    }


def _ordering_tool(args: dict[str, Any]) -> dict[str, Any]:
    delivery = _parse_iso_date(args.get("delivery_date"), required=False)
    next_delivery = _parse_iso_date(args.get("next_delivery_date"), required=False)
    query = str(args.get("item_query") or "").strip() or None
    if delivery is None or next_delivery is None:
        return {
            "needs_details": True,
            "question": "What are the delivery date and the next delivery date?",
            "missing": [key for key, value in
                        (("delivery_date", delivery), ("next_delivery_date", next_delivery))
                        if value is None],
        }
    if next_delivery <= delivery:
        return {"needs_details": True, "question": "The next delivery must be after the first delivery. What are the two dates?"}
    review = cached_ordering_review(
        category="ALL",
        delivery_date=delivery,
        next_delivery_date=next_delivery,
        best_available_delivery_evidence=True,
    )
    rows = list(review.get("rows") or [])
    if query:
        rows = _filter_item_rows(rows, query)
    rows = sorted(
        rows,
        key=lambda x: (
            0 if str(x.get("roster_status") or "").upper() == "ORDER" else 1,
            -float(x.get("suggested_delivery_qty") or 0),
            str(x.get("family_name") or ""),
        ),
    )
    return {
        "delivery_date": delivery,
        "next_delivery_date": next_delivery,
        "item_query": query,
        "analysis_status": review.get("analysis_status"),
        "data_health": review.get("current_source_health") or review.get("data_health"),
        "rows": rows[:30],
        "roster_summary": review.get("roster_summary"),
    }


def _stock_flow_tool(args: dict[str, Any]) -> dict[str, Any]:
    limit = max(1, min(int(args.get("limit") or 20), 40))
    result = yipman_best_sellers(limit=limit)
    rows = list(result.get("rows") or [])
    return {
        "count": len(rows),
        "data_health": result.get("data_health"),
        "rows": rows[:limit],
    }


def _qa_tool(args: dict[str, Any]) -> dict[str, Any]:
    limit = max(1, min(int(args.get("limit") or 30), 100))
    result = qa_review(limit=limit)
    rows = list(result.get("rows") or result.get("issues") or [])
    return {
        "count": len(rows),
        "summary": result.get("summary"),
        "rows": rows[:limit],
    }


def _today_attention_tool(args: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "business_date": business_today(),
        "completed_through": completed_through_date(),
    }
    try:
        out["stock_flow"] = _stock_flow_tool({"limit": 8})
    except Exception as exc:
        out["stock_flow_error"] = str(exc)
    try:
        out["pricing"] = _price_tool({"query": "", "category": "ALL"})
        out["pricing"]["price_suggestions"] = (out["pricing"].get("price_suggestions") or [])[:8]
        out["pricing"]["upc_details"] = []
    except Exception as exc:
        out["pricing_error"] = str(exc)
    try:
        out["ordering"] = _ordering_tool({
            "delivery_date": None,
            "next_delivery_date": None,
            "item_query": None,
        })
        out["ordering"]["rows"] = (out["ordering"].get("rows") or [])[:10]
    except Exception as exc:
        out["ordering_error"] = str(exc)
    try:
        out["qa"] = _qa_tool({"limit": 15})
    except Exception as exc:
        out["qa_error"] = str(exc)
    return out


TOOLS = [
    {
        "type": "function",
        "name": "search_items",
        "description": "Resolve seafood item names, typos, UPCs, receiving articles, and Family articles before answering item-specific questions.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_sales_performance",
        "description": "Get canonical POS sales, quantity, historical-cost GP, top sellers, and daily performance for a supported date or date range. Use this directly for sales/performance/GP questions; item_query resolves the item inside this tool, so no preliminary search is needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": ["string", "null"], "description": "YYYY-MM-DD or null for one day"},
                "item_query": {"type": ["string", "null"], "description": "Optional item, UPC, or Family query"},
            },
            "required": ["start_date", "end_date", "item_query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_inventory",
        "description": "Get current effective Family OH, sales velocity, delivery pattern, last receipt, receiving articles, and related UPCs for an item.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_price_review",
        "description": "Get current UPC prices/cost/GP plus current price suggestions and 240/249 alignment evidence.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Item query or empty string for department review"},
                "category": {"type": "string", "enum": ["ALL", "LIVE", "FRESH", "FROZEN"]},
            },
            "required": ["query", "category"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_ordering_review",
        "description": "Get current Family ordering recommendations. Dates may be null to use the strongest observed delivery day and next cycle.",
        "parameters": {
            "type": "object",
            "properties": {
                "delivery_date": {"type": ["string", "null"], "description": "YYYY-MM-DD or null"},
                "next_delivery_date": {"type": ["string", "null"], "description": "YYYY-MM-DD or null"},
                "item_query": {"type": ["string", "null"]},
            },
            "required": ["delivery_date", "next_delivery_date", "item_query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_stock_flow",
        "description": "Get Family over-receipt/stock-flow watch items using canonical physical receipts versus Family selling movement.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 40}},
            "required": ["limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_qa_summary",
        "description": "Get current read-only QA issues and blockers.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
            "required": ["limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_today_attention",
        "description": "Get a compact combined snapshot of current Ordering, Pricing, Stock Flow, and QA attention. Use this when the user asks what needs attention today.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

_TOOL_HANDLERS = {
    "search_items": _item_tool,
    "get_sales_performance": _sales_tool,
    "get_inventory": _inventory_tool,
    "get_price_review": _price_tool,
    "get_ordering_review": _ordering_tool,
    "get_stock_flow": _stock_flow_tool,
    "get_qa_summary": _qa_tool,
    "get_today_attention": _today_attention_tool,
}


def _instructions() -> str:
    today = business_today().isoformat()
    completed = completed_through_date().isoformat()
    return f"""You are FisherMan AI, the read-only seafood operations assistant for Store 1032.
Business date: {today}. Latest normally completed business day: {completed}.

CRITICAL DATA RULES:
- For a clearly hypothetical ordering calculation with user-provided numbers, use those numbers only and label the result hypothetical. Do not query actual store stock/history or request delivery dates when the requested weekly coverage and demand inputs are already supplied. Keep units consistent and show the arithmetic briefly.
- Do not use the delivery-order tool to invent dates for a weekly usage scenario. If current tools cannot provide a verified weekly promotion forecast for a fully specified product, state that limitation instead of turning it into a delivery-specific order.
- For stock questions call get_inventory directly with the item name or exact Family article; do not run a preliminary search. The tool performs fast identification and asks for a choice when several families match.
- For current-price-only questions, use search_items with the exact UPC and return only the current price, selling unit, price type and effective date. Save get_price_review for an actual recommendation/cost/profit question.
- For ordinary price suggestions, a change of $0.25 or less is ignored even if a small profit improvement is possible. Do not suggest such a change on generic profit/velocity grounds. A confirmed 240/249 mismatch or an explicit pricing error is a separate correction; do not invent that exception when the user merely asks about a 10-cent change.
- When the user asks for weekly usage or the 0/3/7-promotion-day estimate, do NOT ask for delivery dates. Ask only for the missing product identity, promotion days or promotion price needed for that weekly scenario. Example: "Estimate salmon this week with 3 promotion days" needs the salmon product, not delivery dates.
- Reuse user-provided details from history, including ordinary month-name dates such as "October 16" and "October 23". Never repeat a question for a detail already provided. A follow-up order question with known dates should ask only for the product if that is still missing.
- A current-price-only question should show the current price, selling unit, type and effective date; do not add a suggested price, cost or analysis that the user did not request.
- Store-specific definitions must be exact: Family sold quantity comes from Family movement 251 minus 252, in the verified Family/base unit. UPC sold quantity comes only from POS, in that UPC's selling unit. Never define Family movement as simply the sum of UPC POS quantities, and never add each/packs to pounds. Explain with distinct sources/units, not an example summing arbitrary UPC counts.
- 240 is the main selling UPC; do not label it "packaged" merely because its prefix is 240. 249 is the linked cooked/service selling UPC. 245 is generally the packaged form. Always verify the actual selling unit; prefixes do not prove a weight conversion.
- Explain True Stock precisely: the physical count is the starting point; later valid receipts/sales/adjustments change the displayed stock balance. A new accepted OH upload supersedes the earlier count. The count record is an anchor, not a permanently fixed current stock number.
- For an item price recommendation, call get_price_review directly with the item query, without preliminary search or department-wide reports. If it returns needs_details, ask that question and show only the relevant choices. Stop tool calls until the user chooses.
- If price analysis is refreshing or source_changed_since_analysis is true, distinguish the verified current price from dated suggestions; never describe an old recommendation as newly calculated. Give its data date and limitation plainly.
- If you do not understand the user's question, intent, product, unit, date or requested decision, ask for clarification before answering or calculating. Never choose an interpretation silently, invent missing details, or run broad expensive lookups to compensate for an unclear question.
- Ask one short, focused follow-up covering only the missing information. Use clear options when helpful. If several essential details are missing, a small two-column table is okay. Do not repeat questions already answered in the conversation.
- Distinguish uncertainty about the question from missing database evidence: clarify unclear wording; explain unavailable data plainly. Use bounded product search when the product wording is understandable but its identity needs matching; ask the user if multiple plausible matches remain.
- When the user supplies the missing details, continue their original task using the conversation context. Do not restart the discussion or give an unrelated generic answer.
- Before a delivery-specific order calculation, ask for missing delivery date, next delivery date and specific product. This does not apply to a weekly usage estimate. Do not call ordering or department review tools just to ask for these details. Use dates already supplied by the user in this conversation; do not silently infer delivery dates.
- Distinguish GENERAL SEAFOOD KNOWLEDGE from STORE DATA. Answer species, cuts, cooking, product differences, handling and freezing questions directly from general knowledge without database tools. The tool requirements below apply to Store 1032's current or historical operational facts, not universal knowledge or general cooking quantities.
- Never imply that general guidance describes this store's actual stock, costs, sales, supplier, inspection status or promotion. Use tools for those claims. For safety questions use conservative established guidance, distinguish quality from safety, and acknowledge uncertainty; never assure safety from smell or appearance alone.
- Resolve everyday names with search_items before declaring an item missing. Drop filler such as "the" and "in": "oyster in jar" -> "oyster jar". If no results, retry the core product word and inspect package qualifiers. Preserve fresh/frozen/live, jar/shell, size and pack distinctions. Prefer actively selling UPCs over historical aliases; never combine their POS quantities. Ask which item only if multiple plausible active items remain.
- A proposed future promotion price is a scenario, not the current database price. Resolve the item and acknowledge the proposed price first. Ask for actual promotion dates and the intended decision if needed before expensive analysis. Never ask for a photo: this chat accepts text only.
- For item sales questions, call get_sales_performance directly with item_query. Do not run search_items or a department attention report first.\n- Use tools for every current, numeric, sales, stock, receipt, price, ordering, GP, freshness, or QA claim. Never invent missing numbers.
- UPC sold quantity comes ONLY from sales records. Family movement 251-252 is Family-level quantity and must never be presented as an individual UPC sold quantity.
- Completed canonical sales/data days only. Missing calendar dates are excluded, never filled as zero.
- Physical delivery quantity follows canonical receipt semantics: 101 OR the 107+109 receipt event; never double count the same delivery.
- Cost authority: latest receipt valuation first; then Live/Fresh/Frozen official report; then OH fallback.
- Current UPC price is the newest authoritative sold-event POS price versus current Price List authority. Do not use SAP retail.
- 240 main and 249 service/cooked forms in the same product group must have equal current price; when 240 is promoted, 249 participates.
- For price decisions, GP dollars per day is primary while protecting velocity. A new REG test needs at least 7 completed observation days before judging the next step.
- Fresh/Live and frozen freshness/DOH warnings should use the values returned by tools. Do not make up expiry dates.
- Ordering uses effective OH, observed receipt cadence, completed-day demand, promotion evidence, and freshness constraints from the tool result.
- This assistant is READ ONLY. Never claim to update price, stock, true stock, orders, QA, or database records.

ANSWER STYLE:
- DEFAULT BREVITY: unless the user explicitly asks for more detail, answer in at most 60 words. Use a single compact table of at most 3 rows when useful. Do not add a second explanation paragraph, cooking suggestions or extra comparisons that the user did not request. For comparisons use only the 2-3 most useful differences. A short definition can be one sentence.
- General seafood knowledge: do not imply fresh, frozen, shucked or shell-on form alone proves quality or safety. Quality depends on handling and storage. Cooking time depends on fish size/thickness; safety depends on verified cooking temperature, not a fixed number of minutes. Mention raw-seafood risks when recommending raw consumption.
- Stay on point and brief by default. Answer only the exact question. Aim for 40-80 words unless the user asks for detail, explanation, a full report or more examples. Do not add unrelated rules, generic advice or repeated summaries.
- Prefer compact Markdown tables for answers with facts, comparisons, recommendations or steps, including general seafood knowledge. Usually one short table with 2 columns and 3-6 rows is enough. Use 3 columns only when needed; split wider tables into smaller ones. Keep cells short and headings simple. No HTML or code fences.
- Lead with one direct sentence if it helps, then the table. One short source/date or uncertainty note when needed. Avoid extra sections that repeat table content. For a simple yes/no or follow-up question, one sentence is enough.
- Write so a 15-year-old with no seafood department experience can understand. Be respectful and direct, not childish. Explain unfamiliar ideas with a short practical example when useful. Use plain everyday language a busy store manager can understand quickly. Short sentences, familiar words and concrete actions. Avoid technical terms and acronyms unless the user asks for them.
- Say "sales records" instead of POS/canonical, "stock on hand" instead of OH, "selling unit" instead of UOM, "discount" instead of TPR when the price-type code is not necessary, and "days of stock left" instead of DOH. Translate these naturally into the selected language.
- Explain gross profit as sales minus item cost when first relevant. Say "daily gross profit" instead of GP$/day. Explain uncertainty simply, e.g. "Some item costs are missing, so I cannot calculate the full gross profit."
- Do not mention MySQL, serving layers, identity resolution, tool names, internal processing stages or technical status codes in normal answers. Use actual dates, clear units and useful product names. Show UPC/article numbers only when needed to identify a product or requested.
- Keep required price codes like REG/SALE/TPR when distinguishing prices matters, with a plain label. Never simplify by changing the underlying units or pretending missing data is zero.
- Your name is FisherMan AI (exact capitalization). Do not repeat your name in every response.
- Organize answers for a mobile screen. Lead with the result or recommendation in one short sentence.
- For detailed answers requested by the user, use short section labels and small tables. Translate labels into the requested language.
- Use short "- " bullet lines for parallel facts. Keep UPC/name, price/UOM and supported dates together. Trim unnecessary decimal zeros.
- Simple questions need only a concise answer plus source/date when relevant; do not force empty sections or repeat the same fact.
- For a proposed promotion, separate the identified item, proposed scenario, historical evidence and missing details. Ask one focused follow-up question when needed. Never manufacture evidence to fill a section.
- Apply Store 1032 workflow without dumping these rules into every answer:
  * Pipeline: upload -> raw extraction -> identity/UOM validation -> analysis/publish. Use canonical FULL MYSQL tool data. Unknown or unsupported stock is never confirmed zero.
  * Preserve UPC, family, receiving article, pack and selling UOM. Never infer pounds from POS dollars or EA/PAC quantities.
  * Latest receipt cost -> Live/Fresh/Frozen report -> OH. Physical receipts are 101 OR 107+109, never double counted.
  * Price is the newer completed POS sold-event price (sales dollars / POS quantity) versus uploaded Price List. Price List priority: IN STORE -> SALE -> TPR -> REG.
  * Effective stock: latest OH baseline + valid receipts - valid sales +/- adjustments through completed day. True Stock/Zero anchors later movements until new OH or recorded dump supersedes it. Negative available stock is zero; unverified OH stays unknown.
  * Completed days only; exclude missing days. Always retain units, supported dates and coverage.
  * Sell old stock before delivery. Fresh usually Friday; Frozen Tuesday including promotions. Observed Tue/Wed suggests Frozen, Fri/Sat Fresh, Thu requires confirmation; Live has no fixed pattern. User corrections win.
  * Mobile freshness thresholds: Live 7 days, Fresh 10 days, Frozen 60 days. Clearance TPR starts 2 days before threshold and ends on threshold. Use actual freshness evidence; do not invent expiry.
  * Price objective: GP dollars/day while protecting velocity, then DOH and company A/B/C. Department GP target 36%; mix references Live 15%, Fresh 30%, Frozen 44%. Targets are not measured results.
  * Compare historical price/type events by qty/day, GP dollars/day, GP%, supported days and popularity (positive-sales days / supported days at that price type). Candidate GP% uses current effective cost.
  * REG tests need 7 completed days per step. Exclude tests still observing from new price changes. REG must exceed SALE, never equal SALE.
  * Company A/B/C min/max bounds apply except supported Fresh DOH>7 clearance. Ignore price deltas <=$0.25. Company SALE is evidence, not a controllable local change.
  * 240/249 share prices and promotions; count 249 service sales. 245 package premium reference 10-20%, bones/heads discount reference 10-20%; verify identities and costs first.
  * For delivery-specific orders without dates ask delivery and next delivery dates. Cover delivery through day before next delivery; split demand by REG/promo days; subtract usable effective stock; exclude stock that spoils before delivery.
  * Promo demand uses same/similar historical price events with dates, price, quantity/velocity and confidence. REG baseline is recent 28 supported completed days. Label weak promo fallback low confidence.
  * Mobile weekly estimator is separate: 0/3/7 promo days, weekly baseline, weekly usage and whether promotion applied. With 0 promo days baseline equals weekly usage. Do not confuse weekly usage with a delivery-specific order. Show verified receiving article and pack/UOM; do not guess case conversions.
  * Check stock, cost, history, selling UOM and period before recommending promo quantity. Remember user-proposed price in conversation; ask only for missing details needed for their decision.
- Answer the user's exact question first. Do not repeat generic capability descriptions.
- Be concise, operational, and manager-friendly.
- For date-specific questions, state the actual supported date(s) used.
- If data is unavailable, stale, refreshing, or incomplete, say exactly that rather than guessing.
- Keep item names, UPC/Family numbers, quantities, UOM, Sales$, GP$, GP%, price type, and data-through dates clear when relevant.
- Use Markdown tables as described above. Short plain sentences are okay.
"""


def _openai_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def ai_status() -> dict[str, Any]:
    return {
        "configured": bool(_openai_key()),
        "quantity_lookup": "DIRECT_POS_V1",
        "daily_summary": "DIRECT_DAILY_V1",
        "seafood_workflow": "STORE_1032_V2",
        "model": DEFAULT_MODEL,
        "mode": "OPENAI_RESPONSES_FUNCTION_CALLING" if _openai_key() else "LOCAL_FALLBACK",
        "read_only": True,
    }


def _post_responses(payload: dict[str, Any]) -> dict[str, Any]:
    key = _openai_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")
    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(5, 25),
        )
    except requests.Timeout as exc:
        raise RuntimeError("OPENAI_CONNECTION_TIMEOUT") from exc
    except requests.ConnectionError as exc:
        raise RuntimeError("OPENAI_CONNECTION_FAILED") from exc
    try:
        data = response.json()
    except Exception as exc:
        raise RuntimeError(f"OPENAI_INVALID_RESPONSE_HTTP_{response.status_code}") from exc
    if response.status_code >= 400:
        err = data.get("error") if isinstance(data, dict) else None
        code = str(err.get("code") or "") if isinstance(err, dict) else ""
        error_type = str(err.get("type") or "") if isinstance(err, dict) else ""
        if code in {"insufficient_quota", "credit_balance_exhausted"} or error_type == "insufficient_quota":
            raise RuntimeError("OPENAI_API_CREDITS_REQUIRED")
        if response.status_code == 401:
            raise RuntimeError("OPENAI_AUTHENTICATION_FAILED")
        if response.status_code == 429:
            raise RuntimeError("OPENAI_RATE_LIMITED")
        if response.status_code == 403 or code == "model_not_found":
            raise RuntimeError("OPENAI_MODEL_ACCESS_DENIED")
        # Do not pass provider messages through: they can contain credential fragments.
        raise RuntimeError(f"OPENAI_API_ERROR_{response.status_code}")
    return data


def _output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    parts: list[str] = []
    for item in response.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(str(content["text"]))
    return "\n".join(parts).strip()


def _safe_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in list(history or [])[-MAX_HISTORY_MESSAGES:]:
        role = str(item.get("role") or "").lower()
        if role not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "").strip()[:MAX_MESSAGE_CHARS]
        if not content:
            continue
        out.append({"role": role, "content": content})
    return out



def _quick_order_question(question: str, history: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Clarify an incomplete order request before any model or database call."""
    first = question.splitlines()[0].strip()
    match = re.fullmatch(r"how (?:many|much) (.{1,100}?) should (?:i|we) order[?!.]?", first, re.IGNORECASE)
    if not match:
        return None
    if any("reply in " in line.lower() and "english" not in line.lower()
           for line in question.splitlines()[1:]):
        return None
    date_words = r"\b(?:mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?|today|tomorrow)\b|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}\b"
    if re.search(date_words, first, re.IGNORECASE):
        return None
    # Earlier user-provided delivery dates can complete a follow-up request.
    for message in history or []:
        text = str(message.get("content") or "")
        if message.get("role") == "user" and re.search(r"deliver|arriv|order", text, re.IGNORECASE) and re.search(date_words, text, re.IGNORECASE):
            return None
    item = match.group(1).strip().replace("|", "/")
    answer = (
        "Tell me these details so I can calculate the order:\n\n"
        "| Detail | What I need |\n| --- | --- |\n"
        f"| Item | Which {item} product? |\n"
        "| Delivery | When will this order arrive? |\n"
        "| Next delivery | When will the following order arrive? |"
    )
    return {"answer": answer, "model": None, "read_only": True,
            "tool_calls": [], "mode": "ORDER_DETAILS_REQUIRED",
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}


def _quick_daily_answer(question: str) -> dict[str, Any] | None:
    """Common daily summary uses one canonical query, with no pricing review."""
    first = question.splitlines()[0].strip().rstrip("?!.").lower()
    if first not in {
        "how did we sell yesterday", "how were sales yesterday",
        "yesterday sales", "yesterday sales report", "yesterday performance report",
        "how did we do yesterday",
    }:
        return None
    # Respect the requested reply language; other languages use the model path.
    if any("reply in " in line.lower() and "english" not in line.lower()
           for line in question.splitlines()[1:]):
        return None
    day = completed_through_date()
    data = performance_range(day, day, 2000)
    summary = data.get("summary") or {}
    sales = Decimal(str(summary.get("sales_dollars") or 0))
    gp = summary.get("gp_dollars")
    items = sorted(data.get("items") or [],
                   key=lambda row: -Decimal(str(row.get("sales_amount") or 0)))[:3]
    lines = [
        f"Yesterday ({day.strftime('%a, %b %d, %Y')}):",
        "",
        "| Measure | Result |",
        "| --- | --- |",
        f"| Sales | ${sales:,.2f} |",
        f"| Products sold | {summary.get('sold_item_count', 0)} |",
    ]
    if summary.get("gp_dollars_complete") and gp is not None:
        profit = Decimal(str(gp))
        lines.append(f"| Gross profit (sales minus item cost) | ${profit:,.2f}" +
                     (f" ({profit / sales * 100:.1f}%)" if sales > 0 else "") + " |")
    else:
        lines.append("| Gross profit | Not available: some costs are missing. |")
    if items:
        lines.extend(["", "Top sellers:", "", "| Product | Sales / amount sold |", "| --- | --- |"])
        for row in items:
            qty = format(Decimal(str(row.get("sold_quantity") or 0)).normalize(), "f")
            unit = row.get("qty_uom") or row.get("selling_uom") or "unit not confirmed"
            unit = {"LB": "lb", "LBS": "lb", "EA": "each", "PAC": "packs", "PACK": "packs", "CASE": "cases"}.get(str(unit).upper(), unit)
            name = str(row.get("name") or "Unnamed item").replace("|", "/").replace("\n", " ")
            lines.append(f"| {name} | ${Decimal(str(row.get('sales_amount') or 0)):,.2f} / {qty} {unit} |")
    lines.extend(["", "Based on uploaded sales records for this completed day."])
    return {"answer": "\n".join(lines), "model": None, "read_only": True,
            "tool_calls": ["get_sales_performance"], "mode": "CANONICAL_DAILY_DIRECT",
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}


def _quick_quantity_answer(question: str) -> dict[str, Any] | None:
    """Answer a narrow completed-day POS quantity question without model round trips."""
    line=question.split("\n",1)[0].strip()
    match=re.fullmatch(
        r"how many (pounds|lbs?|units) of (.{1,100}?) did we sell yesterday[?!.]?",
        line, re.IGNORECASE,
    )
    if not match:
        return None
    # Preserve the selected UI language; other languages use the model path.
    if "\nReply in " in question and "\nReply in English." not in question:
        return None
    unit,item=match.groups()
    day=completed_through_date()
    data=_sales_tool({"start_date":day.isoformat(),"end_date":day.isoformat(),
                     "item_query":item,"_quantity_only":True})
    quantities=data.get("sold_quantity_by_uom") or {}
    label=day.strftime("%a, %b %d")
    if not data.get("matched_item_count"):
        answer=f"{item}: no matching positive POS sales were found for {label}. This does not establish stock availability."
    elif unit.lower() in {"pound","pounds","lb","lbs"}:
        pounds=sum((Decimal(str(q)) for u,q in quantities.items()
                    if str(u).upper() in {"LB","LBS","POUND","POUNDS"}),Decimal("0"))
        other={u:q for u,q in quantities.items()
               if str(u).upper() not in {"LB","LBS","POUND","POUNDS"}}
        if not any(str(u).upper() in {"LB","LBS","POUND","POUNDS"} for u in quantities):
            answer=f"{item}: Sales for {label} are recorded as "+", ".join(f"{q} {u}" for u,q in quantities.items())+". Pounds cannot be verified from these selling units."
        else:
            answer=f"{item}: {format(pounds.normalize(), 'f')} lb sold yesterday ({label}), from sales records."
            if other:
                answer+=" Other selling units: "+", ".join(f"{q} {u}" for u,q in other.items())+". These are not converted into pounds."
    else:
        answer=f"{item}, yesterday ({label}): "+", ".join(f"{q} {u}" for u,q in quantities.items())+" sold from sales records."
    return {"answer":answer,"model":None,"read_only":True,
            "tool_calls":["get_sales_performance"],"mode":"CANONICAL_POS_DIRECT",
            "usage":{"input_tokens":0,"output_tokens":0,"total_tokens":0}}


def chat(
    message: str,
    history: list[dict[str, Any]] | None = None,
    *,
    client_key: str = "unknown",
) -> dict[str, Any]:
    _check_rate_limit(client_key)
    question = str(message or "").strip()
    if not question:
        raise ValueError("MESSAGE_REQUIRED")
    if len(question) > MAX_MESSAGE_CHARS:
        raise ValueError("MESSAGE_TOO_LONG")

    quick = _quick_order_question(question, history)
    if quick is None:
        quick = _quick_daily_answer(question)
    if quick is None:
        quick = _quick_quantity_answer(question)
    if quick is not None:
        return quick

    input_items: list[dict[str, Any]] = list(_safe_history(history))
    input_items.append({"role": "user", "content": question})

    base_payload = {
        "model": DEFAULT_MODEL,
        "instructions": _instructions(),
        "tools": TOOLS,
        "tool_choice": "auto",
        "reasoning": {"effort": "none"},
        "store": False,
        "max_output_tokens": 1100,
    }

    tool_names: list[str] = []
    response: dict[str, Any] | None = None
    for _round in range(MAX_TOOL_ROUNDS):
        response = _post_responses({**base_payload, "input": input_items})
        output = list(response.get("output") or [])
        calls = [x for x in output if x.get("type") == "function_call"]
        if not calls:
            answer = _output_text(response)
            if not answer:
                raise RuntimeError("OPENAI_EMPTY_ANSWER")
            usage = response.get("usage") or {}
            return {
                "answer": answer,
                "model": response.get("model") or DEFAULT_MODEL,
                "read_only": True,
                "tool_calls": tool_names,
                "usage": {
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                },
            }

        input_items.extend(output)
        for call in calls:
            name = str(call.get("name") or "")
            tool_names.append(name)
            handler = _TOOL_HANDLERS.get(name)
            try:
                arguments = json.loads(call.get("arguments") or "{}")
                if not isinstance(arguments, dict):
                    arguments = {}
            except Exception:
                arguments = {}
            if handler is None:
                result: dict[str, Any] = {"error": "UNKNOWN_TOOL", "tool": name}
            else:
                try:
                    result = handler(arguments)
                    if result.get("needs_details"):
                        return _clarification_result(result, tool_names, question)
                except Exception as exc:
                    result = {"error": str(exc), "tool": name}
            input_items.append({
                "type": "function_call_output",
                "call_id": call.get("call_id"),
                "output": _compact_json(result),
            })

    raise RuntimeError("OPENAI_TOOL_LOOP_LIMIT")

