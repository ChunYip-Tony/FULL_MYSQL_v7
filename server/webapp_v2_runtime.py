from __future__ import annotations

from collections import Counter
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from statistics import median
from typing import Any

from business_clock import business_today, completed_through_date
from data_coverage import source_data_days
from db import db_conn
from quick_check_app import (
    _active_true_stock,
    _actual_position,
    _system_oh_context,
    _system_position,
    _true_stock_history,
    _table_exists,
    ensure_true_stock_tables,
)
from inventory_position import latest_canonical_movement_day
from upc_aliases import source_ean_predicate
from phase3 import _current_price as _live_current_price


WEEKDAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _gr_5014_id(v: Any) -> str | None:
    if v is None:
        return None
    s=str(v).strip().replace(",","")
    if s.endswith(".0") and s[:-2].isdigit():
        s=s[:-2]
    return s if s.isdigit() and s.startswith("5014") else None


def _receipt_gr_from_row(row: dict[str,Any]) -> tuple[str|None,str|None]:
    """Resolve GR from normalized document first, then any raw MVT cell.

    Only 5014... values qualify as GR numbers for this store.
    """
    doc=_gr_5014_id(row.get("normalized_article_document"))
    if doc:
        return doc,"NORMALIZED_5014_DOCUMENT"
    payload=row.get("raw_payload")
    if isinstance(payload,(bytes,bytearray)):
        payload=payload.decode("utf-8",errors="replace")
    if isinstance(payload,str):
        try:
            payload=json.loads(payload)
        except Exception:
            payload={}
    if isinstance(payload,dict):
        # Reference Q is checked first because many SAP MVT exports place the
        # material document there; then scan remaining cells for a valid 5014.
        q=_gr_5014_id(payload.get("Q"))
        if q:
            return q,"RAW_REFERENCE_Q_5014"
        for value in payload.values():
            candidate=_gr_5014_id(value)
            if candidate:
                return candidate,"RAW_ROW_5014_SCAN"
    return None,None


def _overlay_live_current_price(cur, row: dict[str,Any]) -> dict[str,Any]:
    """Refresh CURRENT price fields from canonical price/POS observations at read time.

    quick_check_current remains the Phase 3 serving snapshot, but price is a
    point-in-time fact that can advance after that snapshot. This overlay
    prevents a later accepted Price List or later SINGLE_DATE POS sale from
    being hidden until the next full rebuild.
    """
    if not row or row.get("upc_id") is None:
        return row
    live=_live_current_price(cur,int(row["upc_id"]),row.get("ean_upc"))
    if not live:
        # Never preserve a stale snapshot as CURRENT price. Historical price
        # remains available in price/sales history, but current fields fail closed.
        row["current_price"]=None
        row["current_price_type"]=None
        row["current_price_source"]="STALE_OR_MISSING_FRESH_PRICE"
        row["current_price_asof_date"]=None
        row["gp_pct_current"]=None
        return row
    row["current_price"]=live.get("price")
    row["current_price_type"]=live.get("type")
    row["current_price_source"]=live.get("source")
    row["current_price_asof_date"]=live.get("date")
    cost=row.get("current_cost_per_selling_unit")
    price=live.get("price")
    if cost is not None and price is not None and _d(price)>0:
        row["gp_pct_current"]=(_d(price)-_d(cost))/_d(price)
    return row


def _norm_text(value: Any) -> str:
    return " ".join(str(value or "").upper().split())


def _numeric_key(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits.lstrip("0") or ("0" if digits else "")


def _sales_lineage_pred(
    cur,
    upc_id: int,
    column_upc_id: str = "upc_id",
    column_ean: str = "ean_upc",
) -> tuple[str, tuple[Any, ...]]:
    """Read sales by canonical UPC id OR every safe raw EAN/UPC alias."""
    cur.execute("SELECT ean_upc FROM selling_upc WHERE upc_id=%s LIMIT 1",(int(upc_id),))
    row=cur.fetchone()
    ean=str((row or {}).get("ean_upc") or "").strip()
    if not ean:
        return f"{column_upc_id}=%s",(int(upc_id),)
    ean_pred,ean_args=source_ean_predicate(column_ean,ean)
    return (
        f"({column_upc_id}=%s OR {ean_pred})",
        (int(upc_id),*ean_args),
    )

def _readiness_rank(status: Any) -> int:
    return {
        "READY": 0,
        "QA_HOLD": 1,
        "HISTORICAL_ONLY": 2,
    }.get(str(status or "").upper(), 3)


def _canonical_sales_days(
    cur,
    limit: int | None = None,
    up_to: date | None = None,
) -> list[dict[str, Any]]:
    cutoff=min(up_to,completed_through_date()) if up_to is not None else completed_through_date()
    return source_data_days(
        cur,
        "sales_by_price_type",
        limit=limit,
        up_to=cutoff,
    )


def _daily_sales_by_price_type(
    cur,
    upc_id: int,
    data_days: list[dict[str, Any]],
) -> dict[date, dict[str, Any]]:
    """Canonical completed POS days only.

    A missing source date never becomes a zero. A canonical supported date with
    no row for this UPC is a genuine supported zero-sale day for UPC-level
    velocity purposes.
    """
    out: dict[date, dict[str, Any]] = {
        x["date"]: {
            "date": x["date"],
            "supported": True,
            "source_file_id": int(x["file_id"]),
            "coverage_kind": x.get("coverage_kind"),
            "price_types": {},
            "sales_amount": Decimal("0"),
            "sold_quantity": Decimal("0"),
        }
        for x in data_days
    }
    if not data_days:
        return out

    direct = [x for x in data_days if x.get("coverage_kind") != "DERIVED_PERIOD_RESIDUAL"]
    if direct:
        clauses: list[str] = []
        args: list[Any] = []
        for x in direct:
            clauses.append("(file_id=%s AND period_start_date=%s AND period_end_date=%s)")
            args.extend([int(x["file_id"]), x["date"], x["date"]])
        sales_pred,sales_pred_args=_sales_lineage_pred(cur,int(upc_id))
        cur.execute(
            f"""SELECT period_end_date AS business_date,UPPER(TRIM(price_type)) AS price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM sales_period_observation
                WHERE {sales_pred}
                  AND temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                GROUP BY period_end_date,UPPER(TRIM(price_type))""",
            (*sales_pred_args, *args),
        )
        for row in cur.fetchall():
            day = row["business_date"]
            if day not in out:
                continue
            pt = str(row.get("price_type") or "UNKNOWN").upper()
            sales = _d(row.get("sales_amount"))
            qty = _d(row.get("sold_quantity"))
            out[day]["price_types"][pt] = {
                "sales_amount": sales,
                "sold_quantity": qty,
                "avg_sold_price": (sales / qty if qty != 0 else None),
            }
            out[day]["sales_amount"] += sales
            out[day]["sold_quantity"] += qty

    derived = [x for x in data_days if x.get("coverage_kind") == "DERIVED_PERIOD_RESIDUAL"]
    if derived:
        clauses = []
        args = []
        for x in derived:
            clauses.append("(source_file_id=%s AND business_date=%s)")
            args.extend([int(x["file_id"]), x["date"]])
        sales_pred,sales_pred_args=_sales_lineage_pred(cur,int(upc_id))
        cur.execute(
            f"""SELECT business_date,UPPER(TRIM(price_type)) AS price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM pos_daily_backfill_observation
                WHERE {sales_pred}
                  AND ({' OR '.join(clauses)})
                GROUP BY business_date,UPPER(TRIM(price_type))""",
            (*sales_pred_args, *args),
        )
        for row in cur.fetchall():
            day = row["business_date"]
            if day not in out:
                continue
            pt = str(row.get("price_type") or "UNKNOWN").upper()
            sales = _d(row.get("sales_amount"))
            qty = _d(row.get("sold_quantity"))
            prev = out[day]["price_types"].get(
                pt,
                {"sales_amount": Decimal("0"), "sold_quantity": Decimal("0"), "avg_sold_price": None},
            )
            ps = _d(prev.get("sales_amount")) + sales
            pq = _d(prev.get("sold_quantity")) + qty
            out[day]["price_types"][pt] = {
                "sales_amount": ps,
                "sold_quantity": pq,
                "avg_sold_price": (ps / pq if pq != 0 else None),
            }
            out[day]["sales_amount"] += sales
            out[day]["sold_quantity"] += qty

    return out


def _sales_metric(
    cur,
    upc_id: int,
    supported_day_count: int,
    up_to: date | None = None,
) -> dict[str, Any]:
    days = _canonical_sales_days(cur, limit=supported_day_count, up_to=up_to)
    daily = _daily_sales_by_price_type(cur, upc_id, days)
    qty = sum((_d(x["sold_quantity"]) for x in daily.values()), Decimal("0"))
    sales = sum((_d(x["sales_amount"]) for x in daily.values()), Decimal("0"))
    n = len(days)
    return {
        "requested_supported_days": supported_day_count,
        "supported_day_count": n,
        "coverage_status": "COMPLETE" if n >= supported_day_count else "PARTIAL",
        "start_date": min((x["date"] for x in days), default=None),
        "end_date": max((x["date"] for x in days), default=None),
        "sold_quantity": qty,
        "sales_amount": sales,
        "velocity_per_supported_day": (qty / Decimal(n) if n else None),
        "data_day_definition": "LATEST_COMPLETED_CANONICAL_SALES_DATA_DAYS",
    }


def _price_sales_trend(
    cur,
    upc_id: int,
    supported_day_count: int = 90,
    up_to: date | None = None,
    *,
    cost_per_selling_unit: Decimal|None = None,
    qty_uom: str|None = None,
) -> dict[str, Any]:
    days = _canonical_sales_days(
        cur,
        limit=max(1, min(int(supported_day_count), 365)),
        up_to=up_to,
    )
    daily = _daily_sales_by_price_type(cur, upc_id, days)
    rows = []
    for day in sorted(daily):
        x = daily[day]
        qty=_d(x["sold_quantity"])
        sales=_d(x["sales_amount"])
        avg=(sales/qty if qty != 0 else None)
        gp_dollars=(
            sales-(cost_per_selling_unit*qty)
            if cost_per_selling_unit is not None else None
        )
        rows.append({
            "date": day,
            "supported": True,
            "sold_quantity": qty,
            "qty_uom": qty_uom,
            "sales_amount": sales,
            "avg_sold_price": avg,
            "gp_dollars": gp_dollars,
            "gp_cost_basis":"CURRENT_AUTHORITATIVE_COST" if cost_per_selling_unit is not None else "UNAVAILABLE",
            "price_types": [
                {
                    "price_type": pt,
                    **vals,
                    "is_promotion": pt == "SALE",
                }
                for pt, vals in sorted(x["price_types"].items())
            ],
        })
    return {
        "supported_day_count": len(days),
        "requested_supported_days": supported_day_count,
        "rows": rows,
        "missing_calendar_dates_are_zero": False,
        "promotion_price_type": "SALE",
        "tpr_is_promotion": False,
        "qty_uom":qty_uom,
        "gp_curve_cost_basis":"CURRENT_AUTHORITATIVE_COST" if cost_per_selling_unit is not None else "UNAVAILABLE",
        "gp_curve_cost_per_selling_unit":cost_per_selling_unit,
    }

def _promotion_type(start: date, end: date) -> str:
    duration = (end - start).days + 1
    if start.weekday() == 4 and end.weekday() == 6 and duration == 3:
        return "WEEKEND"
    if start.weekday() == 3 and end.weekday() == 4 and duration == 9:
        return "WEEKLY"
    return "OTHER"


def _historical_sale_periods(
    cur,
    upc_id: int,
    supported_day_limit: int = 180,
) -> list[dict[str, Any]]:
    """Observed SALE-only periods.

    TPR is never promotion. Missing calendar source dates do not become zeros.
    A period is split only by supported non-SALE item evidence, or when observed
    SALE evidence exceeds the maximum nine-calendar-day promotion pattern.
    """
    days = _canonical_sales_days(cur, limit=max(1, min(int(supported_day_limit), 365)))
    daily = _daily_sales_by_price_type(cur, upc_id, days)
    ordered_days = sorted(daily)

    periods: list[tuple[date,date]] = []
    start: date | None = None
    last_sale: date | None = None

    for day in ordered_days:
        x = daily[day]
        types = set(x["price_types"])
        has_sale = "SALE" in types
        has_non_sale_item_data = bool(types - {"SALE"})

        if has_sale:
            if start is None:
                start = day
            elif (day - start).days + 1 > 9:
                if last_sale is not None:
                    periods.append((start,last_sale))
                start = day
            last_sale = day
            continue

        if start is not None and has_non_sale_item_data:
            if last_sale is not None:
                periods.append((start,last_sale))
            start = None
            last_sale = None

    if start is not None and last_sale is not None:
        periods.append((start,last_sale))

    results: list[dict[str, Any]] = []
    for start,end in periods:
        span_days = [d for d in ordered_days if start <= d <= end]
        sale_qty = Decimal("0")
        sale_sales = Decimal("0")
        sale_observed_days = 0
        for day in span_days:
            sale = daily[day]["price_types"].get("SALE")
            if not sale:
                continue
            sale_observed_days += 1
            sale_qty += _d(sale.get("sold_quantity"))
            sale_sales += _d(sale.get("sales_amount"))
        calendar_duration = (end - start).days + 1
        supported = len(span_days)
        results.append({
            "promotion_type": _promotion_type(start,end),
            "start_date": start,
            "end_date": end,
            "start_weekday": WEEKDAY_NAMES[start.weekday()],
            "end_weekday": WEEKDAY_NAMES[end.weekday()],
            "weekday_range": f"{WEEKDAY_NAMES[start.weekday()]} to {WEEKDAY_NAMES[end.weekday()]}",
            "calendar_duration_days": calendar_duration,
            "supported_sales_day_count": supported,
            "sale_observed_day_count": sale_observed_days,
            "coverage_ratio": (
                Decimal(supported) / Decimal(calendar_duration)
                if calendar_duration else None
            ),
            "sale_price": (sale_sales / sale_qty if sale_qty != 0 else None),
            "sale_quantity": sale_qty,
            "sale_velocity_per_supported_day": (
                sale_qty / Decimal(supported) if supported else None
            ),
            "coverage_status": (
                "COMPLETE" if supported == calendar_duration else "PARTIAL"
            ),
            "promotion_definition": "PRICE_TYPE_SALE_ONLY",
        })

    results.sort(key=lambda x: (x["end_date"],x["start_date"]), reverse=True)
    return results


def _search_tokens(value: Any) -> list[str]:
    normalized = "".join(
        ch if ch.isalnum() else " "
        for ch in _norm_text(value)
    )
    return [x for x in normalized.split() if x]


def _token_similarity(query_token: str, candidate_token: str) -> float:
    q = str(query_token or "")
    c = str(candidate_token or "")
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    if len(q) >= 3 and c.startswith(q):
        return 0.97
    if len(c) >= 3 and q.startswith(c):
        # Allow modest suffix mistakes/extra characters without making very
        # short prefixes overly broad.
        return 0.92 if min(len(q), len(c)) >= 4 else 0.0
    return SequenceMatcher(None, q, c).ratio()


def _fuzzy_name_relevance(query: str, name: Any) -> int:
    """Typo-tolerant text relevance.

    Every query token must match a candidate token. Short tokens remain strict;
    longer tokens allow a small edit distance via SequenceMatcher. This makes
    SALMOM -> SALMON work without turning an unrelated one-token query into a
    broad substring scan.
    """
    q_tokens = _search_tokens(query)
    n_tokens = _search_tokens(name)
    if not q_tokens or not n_tokens:
        return 0

    scores: list[float] = []
    for qtok in q_tokens:
        best = max((_token_similarity(qtok, ntok) for ntok in n_tokens), default=0.0)
        if len(qtok) <= 3:
            minimum = 0.97
        elif len(qtok) == 4:
            minimum = 0.80
        else:
            minimum = 0.74
        if best < minimum:
            return 0
        scores.append(best)

    avg = sum(scores) / len(scores)
    # Keep fuzzy results below exact/prefix matches but above weak substring
    # matches when all query tokens are convincingly accounted for.
    return 610 + int(round(avg * 120))


def _relevance(query: str, *, name: Any, number: Any, kind: str, matched_as: str | None = None) -> int:
    """Flexible search relevance for item names and identifiers.

    Exact match is not required. Supports identifier fragments, multi-word
    terms in any order, partial word prefixes, and bounded typo tolerance.
    """
    q = _norm_text(query)
    n = _norm_text(name)
    num = str(number or "").strip()
    if query.isdigit():
        qk = _numeric_key(query)
        nk = _numeric_key(num)
        if qk and qk == nk:
            return 1000 if kind in {"FAMILY","UPC"} else 980
        if qk and nk.startswith(qk):
            return 880
        if qk and nk.endswith(qk):
            return 840
        if qk and qk in nk:
            return 800
        return 0
    if q and n == q:
        return 950
    if q and n.startswith(q):
        return 870

    q_tokens = [x for x in q.split() if x]
    n_tokens = [x for x in n.split() if x]
    if q_tokens and all(t in n for t in q_tokens):
        return 790
    if q_tokens and n_tokens and all(
        any(nt.startswith(qt) for nt in n_tokens)
        for qt in q_tokens
    ):
        return 760
    if q and q in n:
        return 720
    return _fuzzy_name_relevance(query, name)


def _upc_role(row: dict[str,Any]) -> str:
    """Evidence-based selling UPC role for V2 display."""
    desc=str(row.get("selling_description") or "").upper()
    uom=str(row.get("selling_uom") or "").upper().strip()
    upc=_numeric_key(row.get("ean_upc"))
    prefix=int(upc[:3]) if len(upc)>=3 and upc[:3].isdigit() else None

    service_tokens=(
        "FRIED SERVICE","COOK SERVICE","COOKED SERVICE","STEAM SERVICE",
        "COOK/SERVICE","(FRIED SERVICE)","(COOKED SERVICE)","(STEAM SERVICE)",
    )
    # 249 is the Seafood service selling prefix.  Description evidence is kept
    # as a second path for service UPCs whose source label is explicit.
    if prefix==249 or any(token in desc for token in service_tokens):
        return "COOK / SERVICE UPC"
    if uom in {"PACK","PAC","PK","PKG","BAG","CASE","TRAY","EA","EACH","PCS","PC"}:
        return "PACKAGED UPC"
    weighted_prefix=(
        prefix is not None and (
            230<=prefix<=240
            or prefix in {242,245,247}
            or 250<=prefix<=269
        )
    )
    if uom in {"LB","LBS"} or weighted_prefix:
        return "CATCH-WEIGHT UPC"
    return "OTHER UPC"


def _safe_qty_uom(ean_upc: Any, selling_uom: Any=None) -> str|None:
    """Return a display-safe sales quantity UOM without guessing non-prefix UPCs."""
    uom=str(selling_uom or "").strip().upper()
    if uom:
        return "PACK" if uom in {"PAC","PK","PKG"} else ("EA" if uom in {"EACH","PCS","PC"} else uom)
    upc=_numeric_key(ean_upc)
    prefix=int(upc[:3]) if len(upc)>=3 and upc[:3].isdigit() else None
    if prefix is not None and (
        230<=prefix<=240
        or prefix in {242,245,247,249}
        or 250<=prefix<=269
    ):
        return "LB"
    return None


def _seafood_upc_group_signature(family_id: Any, ean_upc: Any) -> tuple[int,str] | None:
    """Return a confirmed-family Seafood selling-form group key.

    The numeric 240/245/247/249 form code is never sufficient by itself.
    Grouping is allowed only inside the same resolved Family and only when the
    three-digit Seafood product code immediately after the prefix also matches.
    A valid group is emitted later only when a 240 anchor exists.
    """
    if family_id is None:
        return None
    upc=_numeric_key(ean_upc)
    if len(upc)<6:
        return None
    prefix=upc[:3]
    if prefix not in {"240","245","247","249"}:
        return None
    return int(family_id),upc[3:6]


def _seafood_240_249_pair_signature(family_id: Any, ean_upc: Any) -> tuple[int,str] | None:
    """Canonical 240/249 display subgroup key.

    Pair only the 240 main and 249 cook/service forms. 245/247 remain siblings
    under the Family rather than being folded into this subgroup.
    """
    sig=_seafood_upc_group_signature(family_id,ean_upc)
    if sig is None:
        return None
    prefix=_numeric_key(ean_upc)[:3]
    return sig if prefix in {"240","249"} else None


def _seafood_upc_group_member_order(ean_upc: Any) -> tuple[int,str]:
    upc=_numeric_key(ean_upc)
    prefix=upc[:3] if len(upc)>=3 else ""
    rank={"240":0,"245":1,"247":2,"249":3}.get(prefix,9)
    return rank,str(ean_upc or "")


def search_items(query: str, limit: int = 30) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        return {"query": q, "count": 0, "results": []}
    limit = max(1,min(int(limit or 30),50))
    q_upper = _norm_text(q)
    like = f"%{q_upper}%"
    prefix = f"{q_upper}%"

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        if q.isdigit():
            nk = _numeric_key(q)
            cur.execute(
                """SELECT *
                   FROM quick_check_current
                   WHERE ean_upc=%s
                      OR (ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM ean_upc)=%s)
                      OR article_number=%s
                      OR main_article_number=%s
                      OR article_number LIKE %s
                      OR main_article_number LIKE %s
                      OR ean_upc LIKE %s
                   LIMIT 120""",
                (q,nk,q,q,f"%{q}%",f"%{q}%",f"%{q}%"),
            )
        else:
            cur.execute(
                """SELECT *
                   FROM quick_check_current
                   WHERE UPPER(COALESCE(selling_description,'')) LIKE %s
                      OR UPPER(COALESCE(family_description,'')) LIKE %s
                   LIMIT 120""",
                (like,like),
            )
        rows = cur.fetchall()
        if not q.isdigit() and not rows:
            # Only fall back to corpus-wide typo-tolerant scoring when strict
            # name matching found nothing. Exact text such as SALMON must not
            # pay the cost of scanning the full serving corpus.
            cur.execute(
                """SELECT *
                   FROM quick_check_current
                   ORDER BY upc_id
                   LIMIT 4000"""
            )
            fallback_rows = cur.fetchall()
            by_upc = {
                int(r["upc_id"]): r
                for r in rows
                if r.get("upc_id") is not None
            }
            for r in fallback_rows:
                if r.get("upc_id") is not None:
                    by_upc.setdefault(int(r["upc_id"]), r)
            rows = list(by_upc.values())

        # Article/receiving aliases may resolve to a family even when no UPC
        # description contains the query.
        if q.isdigit():
            cur.execute(
                """SELECT DISTINCT pf.family_id,pf.main_article_number,pf.family_description,
                                  a.article_number,a.article_description
                   FROM article a
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   WHERE a.article_number=%s
                      OR a.article_number LIKE %s
                   LIMIT 60""",
                (q,f"%{q}%"),
            )
        else:
            cur.execute(
                """SELECT DISTINCT pf.family_id,pf.main_article_number,pf.family_description,
                                  a.article_number,a.article_description
                   FROM article a
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   WHERE UPPER(COALESCE(a.article_description,'')) LIKE %s
                   LIMIT 60""",
                (like,),
            )
        article_matches = cur.fetchall()
        if not q.isdigit() and not article_matches:
            cur.execute(
                """SELECT DISTINCT pf.family_id,pf.main_article_number,pf.family_description,
                                  a.article_number,a.article_description
                   FROM article a
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   ORDER BY a.article_number,pf.family_id
                   LIMIT 4000"""
            )
            fallback_articles = cur.fetchall()
            seen = {
                (int(x["family_id"]), str(x.get("article_number") or ""))
                for x in article_matches
            }
            for x in fallback_articles:
                key = (int(x["family_id"]), str(x.get("article_number") or ""))
                if key not in seen:
                    article_matches.append(x)
                    seen.add(key)

        metric_cache: dict[int,dict[str,Any]] = {}
        def metric28(upc_id: int) -> dict[str,Any]:
            if upc_id not in metric_cache:
                metric_cache[upc_id] = _sales_metric(cur,upc_id,28)
            return metric_cache[upc_id]

        results: list[dict[str,Any]] = []
        family_map: dict[int,dict[str,Any]] = {}
        family_children: dict[int,list[dict[str,Any]]] = {}
        for row in rows:
            fid=int(row["family_id"]) if row.get("family_id") is not None else None
            if fid is not None:
                family_children.setdefault(fid,[]).append(row)
                rel=_relevance(q,name=row.get("family_description"),number=row.get("main_article_number"),kind="FAMILY")
                if rel>0:
                    fam=family_map.setdefault(fid,{
                        "result_type":"FAMILY",
                        "family_id":fid,
                        "number":row.get("main_article_number"),
                        "name":row.get("family_description"),
                        "category":row.get("product_class"),
                        "relevance":rel,
                        "readiness":"HISTORICAL_ONLY",
                        "qty_28d":Decimal("0"),
                        "supported_days_28d":0,
                        "matched_as":"FAMILY",
                    })
                    fam["relevance"]=max(int(fam["relevance"]),rel)

            rel=_relevance(q,name=row.get("selling_description"),number=row.get("ean_upc"),kind="UPC")
            if q.isdigit():
                rel=max(rel,_relevance(q,name=row.get("selling_description"),number=row.get("article_number"),kind="ARTICLE"))
            if rel>0:
                _overlay_live_current_price(cur,row)
                m28=metric28(int(row["upc_id"]))
                results.append({
                    "result_type":"UPC",
                    "upc_id":row.get("upc_id"),
                    "number":row.get("ean_upc"),
                    "article_number":row.get("article_number"),
                    "name":row.get("selling_description"),
                    "family_id":row.get("family_id"),
                    "family_article_number":row.get("main_article_number"),
                    "family_name":row.get("family_description"),
                    "category":row.get("product_class"),
                    "readiness":row.get("quick_check_status"),
                    "upc_role":_upc_role(row),
                    "selling_uom":row.get("selling_uom"),
                    "current_price":row.get("current_price"),
                    "current_price_type":row.get("current_price_type"),
                    "current_price_source":row.get("current_price_source"),
                    "current_price_asof_date":row.get("current_price_asof_date"),
                    "sales_dollars_7d":row.get("sales_dollars_7d"),
                    "pos_qty_7d":row.get("pos_qty_7d"),
                    "sales_days_7d":row.get("sales_days_7d"),
                    "relevance":rel,
                    "qty_28d":m28["sold_quantity"],
                    "qty_28d_uom":row.get("selling_uom"),
                    "supported_days_28d":m28["supported_day_count"],
                    "matched_as":"UPC" if _numeric_key(q)==_numeric_key(row.get("ean_upc")) else "ITEM",
                })

        # Enrich family aggregates from every serving child in that family,
        # not only children whose descriptions matched the query.
        for fid,fam in family_map.items():
            cur.execute("SELECT * FROM quick_check_current WHERE family_id=%s",(fid,))
            children=cur.fetchall()
            statuses=[str(child.get("quick_check_status") or "") for child in children]
            family_sales=_family_sales_series(cur,children,28)
            fam["qty_28d"]=family_sales.get("sold_quantity")
            fam["qty_28d_uom"]=family_sales.get("uom")
            fam["supported_days_28d"]=int(family_sales.get("supported_day_count") or 0)
            fam["family_sales_status"]=family_sales.get("status")
            fam["readiness"]=(
                "READY" if "READY" in statuses
                else ("QA_HOLD" if "QA_HOLD" in statuses else "HISTORICAL_ONLY")
            )
            results.append(fam)

        # Article / receiving aliases remain selectable ARTICLE results.
        # Do not relabel them as FAMILY; that previously caused broad text
        # searches to appear as an all-Family result list.
        article_seen:set[tuple[int,str]]=set()
        for match in article_matches:
            fid=int(match["family_id"])
            article_number=str(match.get("article_number") or "").strip()
            key=(fid,article_number)
            if not article_number or key in article_seen:
                continue
            article_seen.add(key)

            rel=_relevance(
                q,
                name=match.get("article_description"),
                number=article_number,
                kind="ARTICLE",
            )
            if rel<=0:
                continue

            cur.execute("SELECT * FROM quick_check_current WHERE family_id=%s",(fid,))
            children=cur.fetchall()
            statuses=[str(child.get("quick_check_status") or "") for child in children]
            category=next((child.get("product_class") for child in children if child.get("product_class")),None)
            family_sales=_family_sales_series(cur,children,28)

            results.append({
                "result_type":"ARTICLE",
                "family_id":fid,
                "number":article_number,
                "name":match.get("article_description") or match.get("family_description"),
                "family_article_number":match.get("main_article_number"),
                "family_name":match.get("family_description"),
                "category":category,
                "readiness":(
                    "READY" if "READY" in statuses
                    else ("QA_HOLD" if "QA_HOLD" in statuses else "HISTORICAL_ONLY")
                ),
                "relevance":rel,
                "qty_28d":family_sales.get("sold_quantity"),
                "qty_28d_uom":family_sales.get("uom"),
                "supported_days_28d":int(family_sales.get("supported_day_count") or 0),
                "family_sales_status":family_sales.get("status"),
                "matched_as":"ARTICLE",
            })

        family_results=[x for x in results if str(x.get("result_type") or "").upper()=="FAMILY"]
        raw_upc_results=[x for x in results if str(x.get("result_type") or "").upper()=="UPC"]
        article_results=[x for x in results if str(x.get("result_type") or "").upper()=="ARTICLE"]

        # Search-selection grouping for the canonical 240 / 249 subgroup.
        #
        # 240 is the main anchor and 249 is the cook/service companion. 245 /
        # 247 remain independent sibling UPC choices under the same Family.
        # Grouping still requires the same confirmed Family and Seafood product
        # code, so numeric similarity alone can never create a subgroup.
        # UPC-level POS quantities remain independent.
        family_child_cache: dict[int,list[dict[str,Any]]] = {}
        def _group_family_children(fid:int) -> list[dict[str,Any]]:
            if fid not in family_child_cache:
                cur.execute(
                    "SELECT * FROM quick_check_current WHERE family_id=%s ORDER BY ean_upc",
                    (fid,),
                )
                family_child_cache[fid]=cur.fetchall()
            return family_child_cache[fid]

        upc_results: list[dict[str,Any]] = []
        processed_group_keys:set[tuple[int,str]]=set()
        for item in raw_upc_results:
            signature=_seafood_240_249_pair_signature(item.get("family_id"),item.get("number"))
            if signature is None:
                upc_results.append(item)
                continue
            if signature in processed_group_keys:
                continue

            matched_members=[
                x for x in raw_upc_results
                if _seafood_240_249_pair_signature(x.get("family_id"),x.get("number"))==signature
            ]
            fid,product_code=signature
            all_children=_group_family_children(fid)
            group_by_upc:dict[str,dict[str,Any]]={}
            for child in all_children:
                if _seafood_240_249_pair_signature(child.get("family_id"),child.get("ean_upc"))!=signature:
                    continue
                ean=str(child.get("ean_upc") or "").strip()
                if ean:
                    group_by_upc.setdefault(ean,child)
            group_rows=sorted(
                group_by_upc.values(),
                key=lambda x:_seafood_upc_group_member_order(x.get("ean_upc")),
            )
            anchor=next(
                (
                    x for x in group_rows
                    if _numeric_key(x.get("ean_upc")).startswith("240")
                ),
                None,
            )

            # Require the canonical 240 anchor plus at least one related form.
            # Otherwise retain the original individual UPC choices.
            if anchor is None or len(group_rows)<2:
                upc_results.extend(matched_members)
                processed_group_keys.add(signature)
                continue

            members=[]
            member_uoms:set[str]=set()
            group_qty=Decimal("0")
            for child in group_rows:
                m28=metric28(int(child["upc_id"]))
                display_uom=_safe_qty_uom(child.get("ean_upc"),child.get("selling_uom"))
                if display_uom:
                    member_uoms.add(display_uom)
                group_qty+=_d(m28.get("sold_quantity"))
                prefix=_numeric_key(child.get("ean_upc"))[:3]
                members.append({
                    "upc_id":child.get("upc_id"),
                    "upc":child.get("ean_upc"),
                    "article_number":child.get("article_number"),
                    "name":child.get("selling_description"),
                    "readiness":child.get("quick_check_status"),
                    "upc_role":_upc_role(child),
                    "group_role":(
                        "MAIN" if prefix=="240"
                        else ("COOK / SERVICE" if prefix=="249" else "RELATED")
                    ),
                    "selling_uom":child.get("selling_uom"),
                    "current_price":child.get("current_price"),
                    "current_price_type":child.get("current_price_type"),
                    "current_price_source":child.get("current_price_source"),
                    "current_price_asof_date":child.get("current_price_asof_date"),
                    "sales_dollars_7d":child.get("sales_dollars_7d"),
                    "pos_qty_7d":child.get("pos_qty_7d"),
                    "sales_days_7d":child.get("sales_days_7d"),
                    "qty_28d":m28.get("sold_quantity"),
                    "qty_28d_uom":display_uom,
                    "supported_days_28d":m28.get("supported_day_count"),
                })

            aggregate_uom=next(iter(member_uoms)) if len(member_uoms)==1 else None
            statuses=[str(x.get("quick_check_status") or "").upper() for x in group_rows]
            matched_exact=next(
                (
                    x for x in matched_members
                    if q.isdigit() and _numeric_key(q)==_numeric_key(x.get("number"))
                ),
                None,
            )
            matched_choice=matched_exact or (
                max(matched_members,key=lambda x:int(x.get("relevance") or 0))
                if matched_members else None
            )
            upc_results.append({
                "result_type":"UPC_GROUP",
                "family_id":fid,
                "number":anchor.get("ean_upc"),
                "group_anchor_upc":anchor.get("ean_upc"),
                "group_product_code":product_code,
                "group_kind":"240_249_SUBGROUP",
                "name":anchor.get("selling_description") or item.get("name"),
                "family_article_number":anchor.get("main_article_number"),
                "family_name":anchor.get("family_description"),
                "category":anchor.get("product_class"),
                "current_price":anchor.get("current_price"),
                "current_price_type":anchor.get("current_price_type"),
                "current_price_source":anchor.get("current_price_source"),
                "current_price_asof_date":anchor.get("current_price_asof_date"),
                "current_price_basis":"CANONICAL_240_GROUP_ANCHOR",
                "sales_dollars_7d":sum(
                    (_d(x.get("sales_dollars_7d")) for x in group_rows),
                    Decimal("0"),
                ),
                "pos_qty_7d":(
                    sum((_d(x.get("pos_qty_7d")) for x in group_rows),Decimal("0"))
                    if len({
                        _safe_qty_uom(x.get("ean_upc"),x.get("selling_uom"))
                        for x in group_rows
                        if _safe_qty_uom(x.get("ean_upc"),x.get("selling_uom"))
                    })==1
                    else None
                ),
                "readiness":(
                    "READY" if "READY" in statuses
                    else ("QA_HOLD" if "QA_HOLD" in statuses else "HISTORICAL_ONLY")
                ),
                "relevance":max((int(x.get("relevance") or 0) for x in matched_members),default=0),
                "matched_as":"UPC_GROUP",
                "matched_upc":matched_choice.get("number") if matched_choice else None,
                "group_member_count":len(members),
                "group_members":members,
                "qty_28d":group_qty if aggregate_uom is not None else None,
                "qty_28d_uom":aggregate_uom,
                "qty_28d_status":"READY" if aggregate_uom is not None else "MIXED_UOM",
                "supported_days_28d":max(
                    (int(x.get("supported_days_28d") or 0) for x in members),
                    default=0,
                ),
                "grouping_basis":"CONFIRMED_FAMILY_PLUS_SEAFOOD_PRODUCT_CODE_240_249_ONLY",
            })
            processed_group_keys.add(signature)

        def _result_sort_key(x:dict[str,Any]):
            return (
                -float(x.get("qty_28d") or 0),
                -int(x.get("relevance") or 0),
                _readiness_rank(x.get("readiness")),
                str(x.get("name") or ""),
            )

        family_results.sort(key=_result_sort_key)
        upc_results.sort(key=_result_sort_key)
        article_results.sort(key=_result_sort_key)

        # Family remains first, but cannot consume the entire selectable list.
        # Reserve the majority of slots for actual selling UPCs / Articles.
        # Keep Family first without letting Family consume the first
        # screenful of selectable results. Three Family choices are enough to
        # expose the major family-level matches before showing selling UPCs.
        family_cap=min(3,limit)
        selected_families=family_results[:family_cap]
        remaining=max(0,limit-len(selected_families))

        # Selling UPCs are the primary selectable item after Family. Articles
        # fill any remaining slots and still resolve to their Family detail.
        selected_upcs=upc_results[:remaining]
        remaining=max(0,remaining-len(selected_upcs))
        selected_articles=article_results[:remaining]
        selected=selected_families+selected_upcs+selected_articles

        # If one result class is sparse, backfill from the unused ranked pool.
        if len(selected)<limit:
            used={
                (str(x.get("result_type") or ""),str(x.get("number") or ""),x.get("family_id"))
                for x in selected
            }
            overflow=family_results[family_cap:]+upc_results[len(selected_upcs):]+article_results[len(selected_articles):]
            overflow.sort(
                key=lambda x:(
                    0 if str(x.get("result_type") or "").upper()=="FAMILY" else
                    1 if str(x.get("result_type") or "").upper()=="UPC" else 2,
                    *_result_sort_key(x),
                )
            )
            for x in overflow:
                key=(str(x.get("result_type") or ""),str(x.get("number") or ""),x.get("family_id"))
                if key in used:
                    continue
                selected.append(x)
                used.add(key)
                if len(selected)>=limit:
                    break

        cur.close()

    return {
        "query":q,
        "count":len(selected),
        "results":selected,
        "sort_contract":[
            "FAMILY_FIRST_MAX_3",
            "UPC_GROUP_OR_UPC_THEN_ARTICLE",
            "QTY_28D_DESC",
            "RELEVANCE_TIEBREAK",
            "READINESS",
        ],
        "family_result_cap":family_cap,
        "sales_day_contract":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
    }


def _family_effective_oh(cur, rows: list[dict[str,Any]]) -> dict[str,Any]:
    owners: dict[tuple[str,int],dict[str,Any]] = {}
    for row in rows:
        ctx=_system_oh_context(cur,row)
        if not ctx:
            continue
        scope=str(ctx.get("scope_type") or "").upper()
        if scope=="UPC":
            oid=ctx.get("upc_id")
        elif scope=="ARTICLE":
            oid=ctx.get("article_id")
        elif scope=="FAMILY":
            oid=ctx.get("family_id")
        else:
            oid=None
        if oid is None:
            continue
        key=(scope,int(oid))
        if key in owners:
            continue
        system=_system_position(cur,ctx)
        true_stock=_active_true_stock(cur,ctx)
        actual=_actual_position(cur,true_stock)
        pos=actual if true_stock else system
        owners[key]={
            "scope_type":scope,
            "owner_id":int(oid),
            "quantity":pos.get("quantity") if pos else None,
            "uom":pos.get("uom") if pos else None,
            "source":"TRUE_STOCK" if true_stock else "SYSTEM_OH",
            "analysis_usable":bool(pos and pos.get("analysis_usable")),
            "blockers":pos.get("blockers") if pos else ["OH_POSITION_NOT_AVAILABLE"],
            "reason":_oh_display_reason(
                "OH_NOT_ANALYSIS_USABLE",
                pos.get("blockers") if pos else ["OH_POSITION_NOT_AVAILABLE"],
            ),
        }

    usable=[x for x in owners.values() if x.get("analysis_usable") and x.get("quantity") is not None and x.get("uom")]
    uoms={str(x["uom"]).upper() for x in usable}
    if not usable:
        return {"status":"UNAVAILABLE","quantity":None,"uom":None,"owners":list(owners.values())}
    if len(uoms)!=1:
        return {"status":"BLOCKED_MIXED_UOM","quantity":None,"uom":None,"owners":list(owners.values())}
    owner_sources=sorted({str(x.get("source") or "") for x in usable if x.get("source")})
    return {
        "status":"READY",
        "quantity":sum((_d(x["quantity"]) for x in usable),Decimal("0")),
        "uom":next(iter(uoms)),
        "source":" + ".join(owner_sources) if owner_sources else "SYSTEM_OH",
        "owners":list(owners.values()),
    }


def _family_receipt_events(
    cur,
    family_id: int,
    data_day_limit: int = 180,
    data_days: list[dict[str,Any]]|None=None,
) -> list[dict[str,Any]]:
    if data_days is None:
        days=source_data_days(
            cur,"movement",limit=max(1,min(int(data_day_limit),365)),
            up_to=completed_through_date(),
        )
    else:
        requested=max(1,min(int(data_day_limit),365))
        days=sorted(list(data_days),key=lambda x:x["date"])[-requested:]
    canonical={x["date"]:int(x["file_id"]) for x in days}
    if not canonical:
        return []
    file_ids=sorted(set(canonical.values()))
    ph=",".join(["%s"]*len(file_ids))
    cur.execute(
        f"""SELECT m.file_id,m.raw_id,m.source_row_number,m.article_id,m.article_number,
                   m.movement_type,m.posting_date,m.entry_quantity,m.entry_uom_code,
                   m.base_quantity,m.base_uom_code,m.amount_local_currency,
                   m.article_document AS normalized_article_document,
                   r.raw_payload,
                   m.purchase_order,m.vendor_code
            FROM movement_history m
            LEFT JOIN raw_movement r ON r.raw_id=m.raw_id
            WHERE m.family_id=%s
              AND m.file_id IN ({ph})
              AND m.movement_type IN ('101','102','107','108','109','110')
            ORDER BY m.posting_date,m.file_id,m.raw_id,m.source_row_number""",
        (int(family_id),*file_ids),
    )
    rows=[
        r for r in cur.fetchall()
        if r.get("posting_date") in canonical and canonical[r["posting_date"]]==int(r["file_id"])
    ]
    for r in rows:
        gr,gr_source=_receipt_gr_from_row(r)
        r["gr_number"]=gr
        r["gr_number_source"]=gr_source
    groups: dict[tuple[Any,...],list[dict[str,Any]]] = {}
    for r in rows:
        key=(
            r.get("posting_date"),r.get("article_id"),r.get("article_number"),
            r.get("purchase_order"),r.get("gr_number"),
        )
        groups.setdefault(key,[]).append(r)

    events=[]
    for key,group in groups.items():
        by_type: dict[str,list[dict[str,Any]]] = {}
        for r in group:
            by_type.setdefault(str(r.get("movement_type") or ""),[]).append(r)
        if by_type.get("101") or by_type.get("102"):
            chosen=(by_type.get("101") or [])+(by_type.get("102") or [])
            basis="101_102_DIRECT_GR_NET"
        elif by_type.get("107") or by_type.get("108"):
            chosen=(by_type.get("107") or [])+(by_type.get("108") or [])
            basis="107_108_BLOCKED_GR_NET"
        else:
            chosen=(by_type.get("109") or [])+(by_type.get("110") or [])
            basis="109_110_RELEASE_FALLBACK"

        entry_uoms={str(x.get("entry_uom_code") or "").upper() for x in chosen if x.get("entry_uom_code")}
        base_uoms={str(x.get("base_uom_code") or "").upper() for x in chosen if x.get("base_uom_code")}
        base_qty=None; base_uom=None
        if len(base_uoms)==1 and any(x.get("base_quantity") is not None for x in chosen):
            base_qty=sum((_d(x.get("base_quantity")) for x in chosen),Decimal("0"))
            base_uom=next(iter(base_uoms))

        qty=None; uom=None; qty_basis=None
        if len(entry_uoms)==1 and any(x.get("entry_quantity") is not None for x in chosen):
            qty=sum((_d(x.get("entry_quantity")) for x in chosen),Decimal("0"))
            uom=next(iter(entry_uoms)); qty_basis="ENTRY"
        elif base_qty is not None:
            qty=base_qty
            uom=base_uom; qty_basis="BASE"

        events.append({
            "posting_date":key[0],
            "article_id":key[1],
            "article_number":key[2],
            "purchase_order":key[3],
            "article_document":next((x.get("normalized_article_document") for x in chosen if x.get("normalized_article_document")),None),
            "gr_number":key[4],
            "gr_number_source":next((x.get("gr_number_source") for x in chosen if x.get("gr_number_source")),None),
            "vendor_code":next((x.get("vendor_code") for x in chosen if x.get("vendor_code")),None),
            "receipt_quantity":qty,
            "receipt_uom":uom,
            "base_receipt_quantity":base_qty,
            "base_receipt_uom":base_uom,
            "quantity_basis":qty_basis,
            "receipt_stage_basis":basis,
            "receipt_status":(
                "POSITIVE_RECEIPT"
                if qty is not None and qty > 0
                else "NON_POSITIVE_OR_UNRESOLVED"
            ),
            "source_rows":len(chosen),
        })

    events.sort(key=lambda x:(x["posting_date"],str(x.get("article_number") or "")),reverse=True)
    return events


def _family_receipt_events_bulk(
    cur,
    family_ids: list[int] | set[int] | tuple[int,...],
    data_day_limit: int = 180,
    data_days: list[dict[str,Any]]|None=None,
) -> dict[int,list[dict[str,Any]]]:
    """Load canonical receipt events for many families in one movement query."""
    ids=sorted({int(x) for x in family_ids if x is not None})
    out={fid:[] for fid in ids}
    if not ids:
        return out
    if data_days is None:
        days=source_data_days(
            cur,"movement",limit=max(1,min(int(data_day_limit),365)),
            up_to=completed_through_date(),
        )
    else:
        requested=max(1,min(int(data_day_limit),365))
        days=sorted(list(data_days),key=lambda x:x["date"])[-requested:]
    canonical={x["date"]:int(x["file_id"]) for x in days}
    if not canonical:
        return out

    file_ids=sorted(set(canonical.values()))
    fam_ph=",".join(["%s"]*len(ids))
    file_ph=",".join(["%s"]*len(file_ids))
    cur.execute(
        f"""SELECT m.family_id,m.file_id,m.raw_id,m.source_row_number,m.article_id,m.article_number,
                   m.movement_type,m.posting_date,m.entry_quantity,m.entry_uom_code,
                   m.base_quantity,m.base_uom_code,m.amount_local_currency,
                   m.article_document AS normalized_article_document,
                   r.raw_payload,
                   m.purchase_order,m.vendor_code
            FROM movement_history m
            LEFT JOIN raw_movement r ON r.raw_id=m.raw_id
            WHERE m.family_id IN ({fam_ph})
              AND m.file_id IN ({file_ph})
              AND m.movement_type IN ('101','102','107','108','109','110')
            ORDER BY m.family_id,m.posting_date,m.file_id,m.raw_id,m.source_row_number""",
        (*ids,*file_ids),
    )
    rows=[
        r for r in cur.fetchall()
        if r.get("posting_date") in canonical
        and canonical[r["posting_date"]]==int(r["file_id"])
    ]
    for r in rows:
        gr,gr_source=_receipt_gr_from_row(r)
        r["gr_number"]=gr
        r["gr_number_source"]=gr_source
    groups: dict[tuple[Any,...],list[dict[str,Any]]] = {}
    for r in rows:
        key=(
            int(r["family_id"]),
            r.get("posting_date"),r.get("article_id"),r.get("article_number"),
            r.get("purchase_order"),r.get("gr_number"),
        )
        groups.setdefault(key,[]).append(r)

    for key,group in groups.items():
        fid=int(key[0])
        by_type: dict[str,list[dict[str,Any]]] = {}
        for r in group:
            by_type.setdefault(str(r.get("movement_type") or ""),[]).append(r)
        if by_type.get("101") or by_type.get("102"):
            chosen=(by_type.get("101") or [])+(by_type.get("102") or [])
            basis="101_102_DIRECT_GR_NET"
        elif by_type.get("107") or by_type.get("108"):
            chosen=(by_type.get("107") or [])+(by_type.get("108") or [])
            basis="107_108_BLOCKED_GR_NET"
        else:
            chosen=(by_type.get("109") or [])+(by_type.get("110") or [])
            basis="109_110_RELEASE_FALLBACK"

        entry_uoms={str(x.get("entry_uom_code") or "").upper() for x in chosen if x.get("entry_uom_code")}
        base_uoms={str(x.get("base_uom_code") or "").upper() for x in chosen if x.get("base_uom_code")}
        base_qty=None; base_uom=None
        if len(base_uoms)==1 and any(x.get("base_quantity") is not None for x in chosen):
            base_qty=sum((_d(x.get("base_quantity")) for x in chosen),Decimal("0"))
            base_uom=next(iter(base_uoms))

        qty=None; uom=None; qty_basis=None
        if len(entry_uoms)==1 and any(x.get("entry_quantity") is not None for x in chosen):
            qty=sum((_d(x.get("entry_quantity")) for x in chosen),Decimal("0"))
            uom=next(iter(entry_uoms)); qty_basis="ENTRY"
        elif base_qty is not None:
            qty=base_qty
            uom=base_uom; qty_basis="BASE"

        out.setdefault(fid,[]).append({
            "posting_date":key[1],
            "article_id":key[2],
            "article_number":key[3],
            "purchase_order":key[4],
            "article_document":next((x.get("normalized_article_document") for x in chosen if x.get("normalized_article_document")),None),
            "gr_number":key[5],
            "gr_number_source":next((x.get("gr_number_source") for x in chosen if x.get("gr_number_source")),None),
            "vendor_code":next((x.get("vendor_code") for x in chosen if x.get("vendor_code")),None),
            "receipt_quantity":qty,
            "receipt_uom":uom,
            "base_receipt_quantity":base_qty,
            "base_receipt_uom":base_uom,
            "quantity_basis":qty_basis,
            "receipt_stage_basis":basis,
            "receipt_status":(
                "POSITIVE_RECEIPT"
                if qty is not None and qty > 0
                else "NON_POSITIVE_OR_UNRESOLVED"
            ),
            "source_rows":len(chosen),
        })

    for fid in out:
        out[fid].sort(
            key=lambda x:(x["posting_date"],str(x.get("article_number") or "")),
            reverse=True,
        )
    return out


def _delivery_pattern(
    receipt_events: list[dict[str,Any]],
    after_date: date | None = None,
    lookback_days: int = 84,
) -> dict[str,Any]:
    """Summarize recent canonical receipt weekdays for delivery planning.

    Only positive canonical 101/107/109 receipt events inside the recent
    calendar lookback are used for cadence. Older history remains available in
    receipt detail but does not make a stale weekday look current.
    """
    anchor=after_date or business_today()
    lookback=max(28,min(int(lookback_days or 84),180))
    window_start=anchor-timedelta(days=lookback-1)
    all_dates=sorted({
        x["posting_date"]
        for x in receipt_events
        if x.get("posting_date")
        and x.get("receipt_quantity") is not None
        and Decimal(str(x.get("receipt_quantity"))) > 0
    })
    dates=[d for d in all_dates if window_start <= d <= anchor]
    if not dates:
        return {
            "observed_delivery_days":[],
            "receipt_date_count":0,
            "historical_receipt_date_count":len(all_dates),
            "lookback_days":lookback,
            "lookback_start":window_start,
            "lookback_end":anchor,
            "frequency":"NO_DATA",
            "median_gap_days":None,
            "expected_weekdays":[],
            "next_expected_delivery_date":None,
            "confidence":"NONE",
            "confidence_percent":0,
            "basis":"CANONICAL_COMPLETED_MOVEMENT_RECEIPT_DATES_RECENT_WINDOW",
        }

    counts=Counter(d.weekday() for d in dates)
    total=len(dates)
    observed=[]
    for k,v in sorted(counts.items(),key=lambda kv:(-kv[1],kv[0])):
        share=(Decimal(v)/Decimal(total)) if total else Decimal("0")
        observed.append({
            "weekday":WEEKDAY_NAMES[k],
            "weekday_number":k,
            "receipt_date_count":v,
            "receipt_date_share":share,
            "confidence_percent":int((share*Decimal("100")).quantize(Decimal("1"))),
        })

    gaps=[(b-a).days for a,b in zip(dates,dates[1:])]
    med=float(median(gaps)) if gaps else None
    top=observed[0]
    top_share=Decimal(top["receipt_date_count"])/Decimal(total)

    frequency="IRREGULAR"
    expected_weekdays: list[int]=[]
    confidence="LOW"
    if total>=3 and med is not None and 5 <= med <= 9 and top_share >= Decimal("0.60"):
        frequency="WEEKLY"
        expected_weekdays=[int(top["weekday_number"])]
        confidence="HIGH" if top_share>=Decimal("0.75") else "MEDIUM"
    elif total>=4 and med is not None and 2 <= med <= 5 and len(observed)>=2:
        pair=observed[:2]
        pair_share=Decimal(sum(x["receipt_date_count"] for x in pair))/Decimal(total)
        if pair_share>=Decimal("0.70"):
            frequency="MULTIPLE_PER_WEEK"
            expected_weekdays=sorted(int(x["weekday_number"]) for x in pair)
            confidence="HIGH" if pair_share>=Decimal("0.85") else "MEDIUM"

    anchor_for_next=after_date or business_today()
    next_expected=None
    if expected_weekdays:
        candidates=[
            anchor_for_next+timedelta(days=(wd-anchor_for_next.weekday())%7)
            for wd in expected_weekdays
        ]
        next_expected=min(candidates)

    return {
        "observed_delivery_days":observed,
        "receipt_date_count":total,
        "historical_receipt_date_count":len(all_dates),
        "lookback_days":lookback,
        "lookback_start":window_start,
        "lookback_end":anchor,
        "frequency":frequency,
        "median_gap_days":med,
        "expected_weekdays":expected_weekdays,
        "next_expected_delivery_date":next_expected,
        "confidence":confidence,
        "confidence_percent":int((top_share*Decimal("100")).quantize(Decimal("1"))),
        "basis":"CANONICAL_COMPLETED_MOVEMENT_RECEIPT_DATES_RECENT_WINDOW",
    }


def _delivery_day_evidence(pattern: dict[str,Any], target_date: date | None) -> dict[str,Any]:
    if target_date is None:
        return {
            "target_date":None,
            "weekday":None,
            "weekday_number":None,
            "observed_count":0,
            "receipt_date_count":int(pattern.get("receipt_date_count") or 0),
            "share":Decimal("0"),
            "confidence_percent":0,
            "confidence":"NONE",
            "eligible":False,
        }

    wd=int(target_date.weekday())
    observed=next(
        (x for x in (pattern.get("observed_delivery_days") or [])
         if int(x.get("weekday_number"))==wd),
        None,
    )
    total=int(pattern.get("receipt_date_count") or 0)
    count=int((observed or {}).get("receipt_date_count") or 0)
    share=(Decimal(count)/Decimal(total)) if total else Decimal("0")
    expected={int(x) for x in (pattern.get("expected_weekdays") or [])}
    eligible=bool(
        wd in expected
        or (count>=2 and share>=Decimal("0.25"))
    )
    if count>=3 and share>=Decimal("0.75"):
        label="HIGH"
    elif count>=2 and share>=Decimal("0.50"):
        label="MEDIUM"
    elif count>=1:
        label="LOW"
    else:
        label="NONE"
    return {
        "target_date":target_date,
        "weekday":WEEKDAY_NAMES[wd],
        "weekday_number":wd,
        "observed_count":count,
        "receipt_date_count":total,
        "share":share,
        "confidence_percent":int((share*Decimal("100")).quantize(Decimal("1"))),
        "confidence":label,
        "eligible":eligible,
        "eligibility_rule":"EXPECTED_WEEKDAY_OR_AT_LEAST_2_RECEIPTS_AND_25_PERCENT_SHARE",
        "lookback_days":pattern.get("lookback_days"),
        "lookback_start":pattern.get("lookback_start"),
        "lookback_end":pattern.get("lookback_end"),
    }


def family_info(family_key: str) -> dict[str,Any]:
    raw=str(family_key or "").strip()
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        if raw.isdigit():
            cur.execute(
                """SELECT * FROM product_family
                   WHERE main_article_number=%s OR family_id=%s
                   ORDER BY CASE WHEN main_article_number=%s THEN 0 ELSE 1 END
                   LIMIT 1""",
                (raw,int(raw),raw),
            )
        else:
            cur.execute(
                """SELECT * FROM product_family
                   WHERE UPPER(family_description)=UPPER(%s)
                   LIMIT 1""",
                (raw,),
            )
        family=cur.fetchone()
        if not family:
            cur.close()
            raise KeyError("V2_FAMILY_NOT_FOUND")
        fid=int(family["family_id"])

        cur.execute("SELECT * FROM quick_check_current WHERE family_id=%s ORDER BY ean_upc",(fid,))
        upcs=cur.fetchall()
        for _row in upcs:
            _overlay_live_current_price(cur,_row)
        categories=sorted({str(x.get("product_class")) for x in upcs if x.get("product_class")})
        category=categories[0] if len(categories)==1 else ("MIXED" if categories else None)
        effective_oh=_family_effective_oh(cur,upcs)
        effective_oh["reason"]=_oh_display_reason(
            effective_oh.get("status"),
            effective_oh.get("blockers"),
            effective_oh.get("owners"),
        )
        family_sales_7d=_family_sales_series(cur,upcs,7)
        family_sales_28d=_family_sales_series(cur,upcs,28)

        events=_family_receipt_events(cur,fid)
        pattern=_delivery_pattern(events)
        positive_events=[
            x for x in events
            if x.get("receipt_quantity") is not None
            and Decimal(str(x.get("receipt_quantity"))) > 0
        ]
        last_date=max((x["posting_date"] for x in positive_events),default=None)
        last_events=[x for x in positive_events if x.get("posting_date")==last_date]
        receipt_uoms={x.get("receipt_uom") for x in last_events if x.get("receipt_uom")}
        receipt_qty=(
            sum((_d(x.get("receipt_quantity")) for x in last_events),Decimal("0"))
            if last_events and len(receipt_uoms)==1 and all(x.get("receipt_quantity") is not None for x in last_events)
            else None
        )
        receipt_uom=next(iter(receipt_uoms)) if len(receipt_uoms)==1 else None

        last_cost=None
        if last_date is not None:
            cur.execute(
                """SELECT co.business_date,
                          COALESCE(co.cost_per_base_uom,co.cost_amount) AS receipt_cost,
                          COALESCE(bu.uom_code,cu.uom_code) AS cost_uom,
                          co.movement_type,co.source_type,co.file_id,co.source_row_number
                   FROM article_cost_observation co
                   LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
                   LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
                   WHERE co.family_id=%s
                     AND co.business_date=%s
                     AND co.source_type='MOVEMENT_RECEIPT_VALUATION'
                     AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
                     AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
                   ORDER BY co.cost_observation_id DESC
                   LIMIT 1""",
                (fid,last_date),
            )
            last_cost=cur.fetchone()

        cur.execute(
            """SELECT a.article_id,a.article_number,a.article_description,
                      baf.relationship_type,baf.is_primary
               FROM bridge_article_family baf
               JOIN article a ON a.article_id=baf.article_id
               WHERE baf.family_id=%s
                 AND baf.mapping_status='CONFIRMED'
                 AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               ORDER BY CASE baf.relationship_type WHEN 'MAIN' THEN 0 ELSE 1 END,a.article_number""",
            (fid,),
        )
        articles=cur.fetchall()

        related=[]
        for row in upcs:
            m7=_sales_metric(cur,int(row["upc_id"]),7)
            m28=_sales_metric(cur,int(row["upc_id"]),28)
            related.append({
                "upc_id":row.get("upc_id"),
                "upc":row.get("ean_upc"),
                "name":row.get("selling_description"),
                "article_number":row.get("article_number"),
                "readiness":row.get("quick_check_status"),
                "current_price":row.get("current_price"),
                "current_price_type":row.get("current_price_type"),
                "current_price_source":row.get("current_price_source"),
                "current_price_asof_date":row.get("current_price_asof_date"),
                "selling_uom":row.get("selling_uom"),
                "qty_uom":_safe_qty_uom(row.get("ean_upc"),row.get("selling_uom")),
                "upc_role":_upc_role(row),
                "qty_7d":m7["sold_quantity"],
                "supported_days_7d":m7["supported_day_count"],
                "qty_28d":m28["sold_quantity"],
                "supported_days_28d":m28["supported_day_count"],
            })
        related.sort(key=lambda x:(-float(x.get("qty_28d") or 0),_readiness_rank(x.get("readiness")),str(x.get("name") or "")))
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_FAMILY_V4",
        "family_article_number":family.get("main_article_number"),
        "family_article_name":family.get("family_description"),
        "family_id":fid,
        "category":category,
        "receiving_ordering_articles":articles,
        "current_effective_oh":effective_oh,
        "family_sales_7d":family_sales_7d,
        "family_sales_28d":family_sales_28d,
        "observed_delivery":pattern,
        "last_receipt":{
            "date":last_date,
            "quantity":receipt_qty,
            "uom":receipt_uom,
            "events":last_events,
            "cost":last_cost.get("receipt_cost") if last_cost else None,
            "cost_uom":last_cost.get("cost_uom") if last_cost else None,
            "cost_movement_type":last_cost.get("movement_type") if last_cost else None,
        },
        "next_expected_delivery_date":pattern.get("next_expected_delivery_date"),
        "related_upcs":related,
        "related_upc_sort":["QTY_28_SUPPORTED_DAYS_DESC","READINESS"],
        "sales_day_contract":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
    }


def upc_info(upc: str) -> dict[str,Any]:
    raw=str(upc or "").strip()
    nk=_numeric_key(raw)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM quick_check_current
               WHERE ean_upc=%s
                  OR (ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM ean_upc)=%s)
               ORDER BY CASE quick_check_status WHEN 'READY' THEN 0 WHEN 'QA_HOLD' THEN 1 ELSE 2 END
               LIMIT 1""",
            (raw,nk),
        )
        row=cur.fetchone()
        if not row:
            cur.close()
            raise KeyError("V2_UPC_NOT_FOUND")
        _overlay_live_current_price(cur,row)
        m7=_sales_metric(cur,int(row["upc_id"]),7)
        m28=_sales_metric(cur,int(row["upc_id"]),28)
        effective_oh=_selling_equivalent_effective_oh(cur,row)
        if not effective_oh.get("reason"):
            effective_oh["reason"]=_oh_display_reason(
                effective_oh.get("status"),
                effective_oh.get("blockers"),
                effective_oh.get("owners"),
            )
        cur.close()
    return {
        "contract_version":"WEBAPP_V2_UPC_V4",
        "upc":row.get("ean_upc"),
        "upc_name":row.get("selling_description"),
        "category":row.get("product_class"),
        "readiness":row.get("quick_check_status"),
        "selling_uom":row.get("selling_uom"),
        "qty_uom":_safe_qty_uom(row.get("ean_upc"),row.get("selling_uom")),
        "upc_role":_upc_role(row),
        "family_article_number":row.get("main_article_number"),
        "family_article_name":row.get("family_description"),
        "current_price":row.get("current_price"),
        "current_price_type":row.get("current_price_type"),
        "current_price_source":row.get("current_price_source"),
        "current_price_asof_date":row.get("current_price_asof_date"),
        "current_cost_per_selling_unit":row.get("current_cost_per_selling_unit"),
        "gp_pct_current":row.get("gp_pct_current"),
        "gp_dollars_7d":row.get("gp_dollars_7d"),
        "gp_per_day_7d":row.get("gp_per_day_7d"),
        "upc_velocity_7d":row.get("upc_velocity_7d"),
        "dos":row.get("dos"),
        "doh":row.get("doh"),
        "effective_oh":effective_oh,
        "qty_7d":m7,
        "qty_28d":m28,
        "actions":["FAMILY_ARTICLE","PRICE","ORDERING"],
    }


def _historical_cost_per_selling_as_of(
    cur,
    row: dict[str,Any],
    day: date,
) -> dict[str,Any]|None:
    family_id=row.get("family_id")
    if family_id is None:
        return None
    selling=str(row.get("selling_uom") or "").strip().upper()
    base=str(row.get("base_uom") or "").strip().upper()
    factor=(
        Decimal(str(row["base_qty_per_selling_unit"]))
        if row.get("base_qty_per_selling_unit") is not None else None
    )
    source_groups=[
        ("MOVEMENT_RECEIPT_VALUATION",),
        ("ON_HAND_EXPLICIT_COST_FALLBACK",),
        ("FROZEN_INVENTORY_OFFICIAL_COST","LIVE_FRESH_SUGGESTION_OFFICIAL_COST"),
        ("USER_CONFIRMED_FAMILY_COST",),
    ]
    for sources in source_groups:
        ph=",".join(["%s"]*len(sources))
        cur.execute(
            f"""SELECT COALESCE(co.cost_per_base_uom,co.cost_amount) AS cost_value,
                       co.business_date,co.source_type,
                       COALESCE(bu.uom_code,cu.uom_code) AS cost_uom
                FROM article_cost_observation co
                LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
                LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
                WHERE co.family_id=%s
                  AND co.business_date<=%s
                  AND co.source_type IN ({ph})
                  AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
                  AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
                ORDER BY co.business_date DESC,co.cost_observation_id DESC
                LIMIT 1""",
            (int(family_id),day,*sources),
        )
        x=cur.fetchone()
        if not x:
            continue
        cost=_d(x.get("cost_value"))
        cuom=str(x.get("cost_uom") or "").strip().upper()
        if selling and cuom==selling:
            sell_cost=cost
        elif base and cuom==base and factor is not None and factor>0:
            sell_cost=cost*factor
        elif base and selling and base==selling and cuom==base:
            sell_cost=cost
        else:
            continue
        return {
            "cost_per_selling_unit":sell_cost,
            "cost_date":x.get("business_date"),
            "cost_source":x.get("source_type"),
            "cost_uom":selling or cuom or None,
        }
    return None


def _historical_gp_trend(
    cur,
    row: dict[str,Any],
    trend: dict[str,Any],
) -> dict[str,Any]:
    qty_uom=_safe_qty_uom(row.get("ean_upc"),row.get("selling_uom"))
    for x in trend.get("rows",[]):
        x["qty_uom"]=qty_uom
        cost=_historical_cost_per_selling_as_of(cur,row,x["date"])
        if cost is None:
            x["gp_dollars"]=None
            x["gp_cost_basis"]="HISTORICAL_COST_UNAVAILABLE"
            x["cost_per_selling_unit"]=None
            x["cost_date"]=None
            x["cost_source"]=None
            continue
        qty=_d(x.get("sold_quantity"))
        sales=_d(x.get("sales_amount"))
        x["cost_per_selling_unit"]=cost["cost_per_selling_unit"]
        x["cost_date"]=cost["cost_date"]
        x["cost_source"]=cost["cost_source"]
        x["gp_dollars"]=sales-(qty*_d(cost["cost_per_selling_unit"]))
        x["gp_cost_basis"]="HISTORICAL_APPLICABLE_COST"
    trend["qty_uom"]=qty_uom
    trend["gp_curve_cost_basis"]="HISTORICAL_APPLICABLE_COST_AS_OF_EACH_SUPPORTED_DATE"
    trend["missing_gp_cost_dates_are_zero"]=False
    return trend


def price_analysis(upc: str, trend_supported_days: int = 28) -> dict[str,Any]:
    raw=str(upc or "").strip()
    nk=_numeric_key(raw)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM quick_check_current
               WHERE ean_upc=%s
                  OR (ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM ean_upc)=%s)
               ORDER BY CASE quick_check_status WHEN 'READY' THEN 0 WHEN 'QA_HOLD' THEN 1 ELSE 2 END
               LIMIT 1""",
            (raw,nk),
        )
        row=cur.fetchone()
        if not row:
            cur.close()
            raise KeyError("V2_UPC_NOT_FOUND")
        _overlay_live_current_price(cur,row)
        upc_id=int(row["upc_id"])
        qty_uom=_safe_qty_uom(row.get("ean_upc"),row.get("selling_uom"))
        current_cost=(
            Decimal(str(row["current_cost_per_selling_unit"]))
            if row.get("current_cost_per_selling_unit") is not None else None
        )
        result={
            "contract_version":"WEBAPP_V2_PRICE_V4",
            "upc":row.get("ean_upc"),
            "name":row.get("selling_description"),
            "category":row.get("product_class"),
            "readiness":row.get("quick_check_status"),
            "selling_uom":row.get("selling_uom"),
            "qty_uom":qty_uom,
            "upc_role":_upc_role(row),
            "current":{
                "price":row.get("current_price"),
                "price_type":row.get("current_price_type"),
                "price_source":row.get("current_price_source"),
                "price_as_of":row.get("current_price_asof_date"),
                "cost":row.get("current_cost_per_selling_unit"),
                "cost_uom":row.get("selling_uom"),
                "cost_date":row.get("cost_date"),
                "cost_source":row.get("cost_source"),
                "gp_pct":row.get("gp_pct_current"),
                "gp_dollars_7d":row.get("gp_dollars_7d"),
                "gp_per_day_7d":row.get("gp_per_day_7d"),
                "velocity_7d":row.get("upc_velocity_7d"),
                "dos":row.get("dos"),
                "doh":row.get("doh"),
            },
            "sales":{
                "7d":_sales_metric(cur,upc_id,7),
                "28d":_sales_metric(cur,upc_id,28),
            },
            "references":{
                "sweet_spot":row.get("sweet_spot_price"),
                "wgpm":row.get("wgpm_price"),
                "company_a":row.get("company_price_a"),
                "company_b":row.get("company_price_b"),
                "company_c":row.get("company_price_c"),
            },
            "price_vs_sales_trend":_historical_gp_trend(
                cur,row,_price_sales_trend(
                    cur,upc_id,min(max(int(trend_supported_days or 28),1),28),
                    qty_uom=qty_uom,
                )
            ),
            "sales_history_14d":_historical_gp_trend(
                cur,row,_price_sales_trend(
                    cur,upc_id,14,
                    qty_uom=qty_uom,
                )
            ),
            "historical_promotions":_historical_sale_periods(cur,upc_id),
            "promotion_definition":{
                "promotion_price_type":"SALE",
                "tpr_is_promotion":False,
                "weekly_pattern":"THURSDAY_TO_FOLLOWING_FRIDAY",
                "weekend_pattern":"FRIDAY_TO_SUNDAY",
            },
        }
        cur.close()
    return result


def _oh_display_reason(status: Any, blockers: Any=None, owners: Any=None) -> str|None:
    s=str(status or "").upper()
    if s=="READY":
        return None
    if s=="BLOCKED_MIXED_UOM":
        return "Inventory exists under more than one UOM, so OH cannot be safely totaled."
    if s=="OH_UOM_CONVERSION_UNRESOLVED":
        return "OH exists, but its UOM cannot be safely converted to the selling UOM."
    if s=="OH_NOT_ANALYSIS_USABLE":
        return "OH exists, but the inventory position is not analysis-usable."
    if s=="FAMILY_TRUE_STOCK_ROLLFORWARD_BLOCKED":
        return "Family True Stock exists, but movement roll-forward is blocked."
    if s=="FAMILY_SYSTEM_OH_ROLLFORWARD_BLOCKED":
        return "Family OH snapshot exists, but movement roll-forward is blocked."
    flat=[]
    if isinstance(blockers,(list,tuple,set)):
        flat=[str(x) for x in blockers if x]
    elif blockers:
        flat=[str(blockers)]
    if flat:
        return "OH unavailable: " + ", ".join(flat)
    if owners:
        return "OH owner records were found, but none produced a usable inventory position."
    return "No compatible OH snapshot was found for this item/family."


def _selling_equivalent_effective_oh(cur, row: dict[str,Any]) -> dict[str,Any]:
    ctx=_system_oh_context(cur,row)
    if not ctx:
        return {
            "status":"OH_NOT_AVAILABLE","quantity":None,"uom":row.get("selling_uom"),
            "reason":_oh_display_reason("OH_NOT_AVAILABLE"),
        }
    system=_system_position(cur,ctx)
    true_stock=_active_true_stock(cur,ctx)
    actual=_actual_position(cur,true_stock)
    pos=actual if true_stock else system
    if not pos or not pos.get("analysis_usable") or pos.get("quantity") is None:
        return {
            "status":"OH_NOT_ANALYSIS_USABLE",
            "quantity":None,
            "uom":row.get("selling_uom"),
            "source":"TRUE_STOCK" if true_stock else "SYSTEM_OH",
            "blockers":pos.get("blockers") if pos else ["OH_POSITION_NOT_AVAILABLE"],
        }

    qty=_d(pos.get("quantity"))
    oh_uom=str(pos.get("uom") or "").strip().upper()
    selling=str(row.get("selling_uom") or "").strip().upper()
    base=str(row.get("base_uom") or "").strip().upper()
    factor=(Decimal(str(row["base_qty_per_selling_unit"])) if row.get("base_qty_per_selling_unit") is not None else None)

    if oh_uom and selling and oh_uom==selling:
        selling_qty=qty
        basis="DIRECT_SELLING_UOM"
    elif oh_uom and base and selling and oh_uom==base and factor is not None and factor>0:
        selling_qty=qty/factor
        basis="BASE_TO_SELLING_FACTOR"
    else:
        return {
            "status":"OH_UOM_CONVERSION_UNRESOLVED",
            "quantity":None,
            "uom":row.get("selling_uom"),
            "source":"TRUE_STOCK" if true_stock else "SYSTEM_OH",
            "source_quantity":qty,
            "source_uom":oh_uom or None,
            "base_uom":row.get("base_uom"),
            "base_qty_per_selling_unit":factor,
            "reason":_oh_display_reason("OH_UOM_CONVERSION_UNRESOLVED"),
        }
    return {
        "status":"READY",
        "quantity":selling_qty,
        "uom":row.get("selling_uom"),
        "source":"TRUE_STOCK" if true_stock else "SYSTEM_OH",
        "source_quantity":qty,
        "source_uom":oh_uom,
        "conversion_basis":basis,
    }


def _regular_baseline(cur, upc_id: int, supported_day_limit: int = 28) -> dict[str,Any]:
    days=_canonical_sales_days(cur,limit=max(1,min(int(supported_day_limit),90)))
    daily=_daily_sales_by_price_type(cur,upc_id,days)
    regular_days=[]
    qty=Decimal("0")
    for day in sorted(daily):
        x=daily[day]
        # Any SALE evidence makes the whole supported day promotional.
        # TPR remains regular by explicit business rule.
        if "SALE" in x["price_types"]:
            continue
        regular_days.append(day)
        qty+=_d(x.get("sold_quantity"))
    n=len(regular_days)
    return {
        "requested_supported_days":supported_day_limit,
        "regular_supported_day_count":n,
        "regular_sold_quantity":qty,
        "regular_velocity_per_supported_day":(qty/Decimal(n) if n else None),
        "start_date":min(regular_days) if regular_days else None,
        "end_date":max(regular_days) if regular_days else None,
        "sale_days_excluded":len(days)-n,
        "tpr_treated_as_regular":True,
        "missing_calendar_dates_are_zero":False,
    }


def _promotion_forecast_baseline(
    cur,
    upc_id: int,
    start_date: date,
    end_date: date,
    promotion_price: Decimal,
) -> dict[str,Any]:
    requested_type=_promotion_type(start_date,end_date)
    history=_historical_sale_periods(cur,upc_id,365)
    same=[x for x in history if x.get("promotion_type")==requested_type and x.get("sale_velocity_per_supported_day") is not None]
    def price_distance(x: dict[str,Any]) -> Decimal:
        p=x.get("sale_price")
        return abs(Decimal(str(p))-promotion_price) if p is not None else Decimal("999999")
    same.sort(key=lambda x:(price_distance(x),-x["end_date"].toordinal()))
    selected=same[:3]
    if not selected:
        return {
            "status":"NO_MATCHING_PROMOTION_HISTORY",
            "promotion_type":requested_type,
            "promotion_velocity_per_day":None,
            "selected_history":[],
            "confidence":"LOW",
        }
    weighted_qty=sum((_d(x.get("sale_quantity")) for x in selected),Decimal("0"))
    weighted_days=sum((int(x.get("supported_sales_day_count") or 0) for x in selected),0)
    velocity=(weighted_qty/Decimal(weighted_days) if weighted_days else None)
    coverage_complete=all(x.get("coverage_status")=="COMPLETE" for x in selected)
    return {
        "status":"READY",
        "promotion_type":requested_type,
        "promotion_velocity_per_day":velocity,
        "selected_history":selected,
        "selected_period_count":len(selected),
        "confidence":"HIGH" if coverage_complete and len(selected)>=2 else "MEDIUM",
        "selection_basis":"SAME_PROMOTION_TYPE_THEN_CLOSEST_SALE_PRICE_THEN_RECENCY",
    }


def _next_delivery_after(pattern: dict[str,Any], after_date: date) -> date | None:
    weekdays=[int(x) for x in (pattern.get("expected_weekdays") or [])]
    if not weekdays:
        return None
    candidates=[]
    for wd in weekdays:
        delta=(wd-after_date.weekday())%7
        if delta==0:
            delta=7
        candidates.append(after_date+timedelta(days=delta))
    return min(candidates) if candidates else None


def ordering_analysis(
    upc: str,
    *,
    ordering_date: date | None = None,
    expected_delivery_date: date | None = None,
    promotion_involved: bool = False,
    promotion_start_date: date | None = None,
    promotion_end_date: date | None = None,
    promotion_price: Decimal | None = None,
) -> dict[str,Any]:
    raw=str(upc or "").strip()
    nk=_numeric_key(raw)
    order_day=ordering_date or business_today()

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM quick_check_current
               WHERE ean_upc=%s
                  OR (ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM ean_upc)=%s)
               ORDER BY CASE quick_check_status WHEN 'READY' THEN 0 WHEN 'QA_HOLD' THEN 1 ELSE 2 END
               LIMIT 1""",
            (raw,nk),
        )
        row=cur.fetchone()
        if not row:
            cur.close()
            raise KeyError("V2_UPC_NOT_FOUND")

        upc_id=int(row["upc_id"])
        family_id=int(row["family_id"])
        events=_family_receipt_events(cur,family_id)
        pattern=_delivery_pattern(events,after_date=order_day)
        delivery=expected_delivery_date or pattern.get("next_expected_delivery_date")
        effective_oh=_selling_equivalent_effective_oh(cur,row)
        regular=_regular_baseline(cur,upc_id,28)
        historical_promotions=_historical_sale_periods(cur,upc_id,365)

        blockers=[]
        if delivery is None:
            blockers.append("EXPECTED_DELIVERY_DATE_REQUIRED")
        elif delivery < order_day:
            blockers.append("EXPECTED_DELIVERY_BEFORE_ORDER_DATE")
        if effective_oh.get("status")!="READY":
            blockers.append(str(effective_oh.get("status")))
        if regular.get("regular_velocity_per_supported_day") is None:
            blockers.append("REGULAR_BASELINE_UNAVAILABLE")

        promo_baseline=None
        if promotion_involved:
            if promotion_start_date is None or promotion_end_date is None or promotion_price is None:
                blockers.append("PROMOTION_INPUTS_REQUIRED")
            elif promotion_end_date < promotion_start_date:
                blockers.append("PROMOTION_END_BEFORE_START")
            else:
                promo_baseline=_promotion_forecast_baseline(
                    cur,upc_id,promotion_start_date,promotion_end_date,Decimal(str(promotion_price))
                )

        next_next=_next_delivery_after(pattern,delivery) if delivery is not None else None
        if delivery is not None and next_next is None:
            blockers.append("NEXT_NEXT_DELIVERY_UNRESOLVED")

        regular_velocity=regular.get("regular_velocity_per_supported_day")
        promotion_velocity=(
            promo_baseline.get("promotion_velocity_per_day")
            if promo_baseline and promo_baseline.get("status")=="READY"
            else None
        )

        # No invented promotion uplift. If matching SALE history is unavailable,
        # use the regular baseline for those future dates and expose LOW confidence.
        promo_forecast_fallback=False
        if promotion_involved and promo_baseline and promotion_velocity is None and regular_velocity is not None:
            promotion_velocity=regular_velocity
            promo_forecast_fallback=True

        forecast_rows=[]
        total_usage=Decimal("0")
        before_delivery_usage=Decimal("0")
        if not blockers or (
            set(blockers) <= {"PROMOTION_INPUTS_REQUIRED"} and not promotion_involved
        ):
            if next_next is not None and regular_velocity is not None:
                day=order_day
                while day < next_next:
                    is_promo=bool(
                        promotion_involved
                        and promotion_start_date is not None
                        and promotion_end_date is not None
                        and promotion_start_date <= day <= promotion_end_date
                    )
                    velocity=promotion_velocity if is_promo else regular_velocity
                    basis=(
                        "HISTORICAL_SALE_PROMOTION"
                        if is_promo and promo_baseline and promo_baseline.get("status")=="READY"
                        else ("REGULAR_FALLBACK_NO_MATCHING_SALE_HISTORY" if is_promo else "REGULAR_BASELINE")
                    )
                    usage=_d(velocity)
                    total_usage+=usage
                    if delivery is not None and day < delivery:
                        before_delivery_usage+=usage
                    forecast_rows.append({
                        "date":day,
                        "demand_type":"PROMOTION" if is_promo else "REGULAR",
                        "forecast_usage":usage,
                        "uom":row.get("selling_uom"),
                        "basis":basis,
                    })
                    day+=timedelta(days=1)

        raw_oh_qty=(
            Decimal(str(effective_oh["quantity"]))
            if effective_oh.get("quantity") is not None else None
        )
        # V2 global ordering rule: negative Effective OH is an inventory exception
        # visible to the user, but every ordering calculation treats it as zero.
        ordering_oh_qty=(
            max(Decimal("0"),raw_oh_qty)
            if raw_oh_qty is not None else None
        )
        projected_oh_at_delivery=(
            ordering_oh_qty-before_delivery_usage
            if ordering_oh_qty is not None and delivery is not None else None
        )
        raw_suggested=(
            max(Decimal("0"),total_usage-ordering_oh_qty)
            if ordering_oh_qty is not None and next_next is not None else None
        )

        result={
            "contract_version":"WEBAPP_V2_ORDERING_V1",
            "upc":row.get("ean_upc"),
            "name":row.get("selling_description"),
            "category":row.get("product_class"),
            "readiness":row.get("quick_check_status"),
            "inputs":{
                "ordering_date":order_day,
                "expected_delivery_date":delivery,
                "expected_delivery_default_source":(
                    "USER_INPUT" if expected_delivery_date is not None else "OBSERVED_DELIVERY_PATTERN"
                ),
                "promotion_involved":bool(promotion_involved),
                "promotion_start_date":promotion_start_date,
                "promotion_end_date":promotion_end_date,
                "promotion_price":promotion_price,
                "promotion_price_type":"SALE" if promotion_involved else None,
            },
            "inventory":{
                "effective_oh":effective_oh,
                "raw_effective_oh_qty":raw_oh_qty,
                "ordering_oh_qty":ordering_oh_qty,
                "negative_oh_treated_as_zero":bool(raw_oh_qty is not None and raw_oh_qty < 0),
                "last_receipt_date":row.get("last_receipt_date"),
                "dos":row.get("dos"),
                "doh":row.get("doh"),
            },
            "observed_delivery":pattern,
            "next_next_delivery_date":next_next,
            "regular_baseline":regular,
            "promotion_baseline":promo_baseline,
            "historical_promotions":historical_promotions,
            "forecast":{
                "horizon_start":order_day,
                "horizon_end_exclusive":next_next,
                "regular_or_sale_by_calendar_date":forecast_rows,
                "forecast_usage_until_next_next_delivery":total_usage if forecast_rows else None,
                "forecast_usage_before_expected_delivery":before_delivery_usage if forecast_rows else None,
                "projected_oh_at_expected_delivery":projected_oh_at_delivery,
                "suggested_order_qty":raw_suggested,
                "suggested_order_uom":row.get("selling_uom"),
                "promotion_fallback_to_regular":promo_forecast_fallback,
                "rounding_applied":False,
            },
            "status":"READY" if not blockers else "BLOCKED",
            "blockers":blockers,
            "rules":{
                "sales_history":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
                "missing_source_dates_count_as_zero":False,
                "promotion_definition":"PRICE_TYPE_SALE_ONLY",
                "tpr_is_promotion":False,
                "coverage_target":"USAGE_UNTIL_NEXT_NEXT_DELIVERY_DATE",
                "negative_effective_oh_for_ordering":"TREAT_AS_ZERO",
                "saved":False,
                "submitted":False,
            },
        }
        cur.close()
    return result


def _strict_next_weekday(anchor: date, weekday: int) -> date:
    """Return the following weekday, never the same calendar date."""
    delta=(int(weekday)-anchor.weekday())%7
    if delta==0:
        delta=7
    return anchor+timedelta(days=delta)


def _family_sales_series(
    cur,
    upc_rows: list[dict[str,Any]],
    supported_day_count: int,
    data_days: list[dict[str,Any]]|None=None,
) -> dict[str,Any]:
    requested=max(1,min(int(supported_day_count),365))
    if data_days is None:
        days=_canonical_sales_days(cur,limit=requested)
    else:
        ordered=sorted(list(data_days),key=lambda x:x["date"])
        days=ordered[-requested:]
    selling_uoms={
        str(x.get("selling_uom") or "").strip().upper()
        for x in upc_rows if x.get("selling_uom")
    }
    if not upc_rows or len(selling_uoms)!=1:
        return {
            "status":"BLOCKED_FAMILY_UOM",
            "uom":None,
            "supported_day_count":len(days),
            "rows":[],
            "sold_quantity":None,
            "velocity_per_supported_day":None,
        }

    uom=next(iter(selling_uoms))
    series={
        x["date"]:{
            "date":x["date"],
            "sold_quantity":Decimal("0"),
            "sale_quantity":Decimal("0"),
            "sale_sales_amount":Decimal("0"),
            "has_sale":False,
            "supported":True,
        }
        for x in days
    }
    for row in upc_rows:
        daily=_daily_sales_by_price_type(cur,int(row["upc_id"]),days)
        for d,x in daily.items():
            series[d]["sold_quantity"]+=_d(x.get("sold_quantity"))
            sale=x.get("price_types",{}).get("SALE")
            if sale:
                series[d]["has_sale"]=True
                series[d]["sale_quantity"]+=_d(sale.get("sold_quantity"))
                series[d]["sale_sales_amount"]+=_d(sale.get("sales_amount"))
    qty=sum((_d(x["sold_quantity"]) for x in series.values()),Decimal("0"))
    n=len(days)
    return {
        "status":"READY",
        "uom":uom,
        "supported_day_count":n,
        "coverage_status":"COMPLETE" if n>=supported_day_count else "PARTIAL",
        "rows":[series[d] for d in sorted(series)],
        "sold_quantity":qty,
        "velocity_per_supported_day":(qty/Decimal(n) if n else None),
    }


def _family_sales_tail(
    series: dict[str,Any],
    supported_day_count: int,
) -> dict[str,Any]:
    requested=max(1,min(int(supported_day_count),365))
    if series.get("status")!="READY":
        return {
            **series,
            "supported_day_count":min(int(series.get("supported_day_count") or 0),requested),
        }
    rows=sorted(list(series.get("rows") or []),key=lambda x:x["date"])[-requested:]
    qty=sum((_d(x.get("sold_quantity")) for x in rows),Decimal("0"))
    n=len(rows)
    return {
        "status":"READY",
        "uom":series.get("uom"),
        "supported_day_count":n,
        "coverage_status":"COMPLETE" if n>=requested else "PARTIAL",
        "rows":rows,
        "sold_quantity":qty,
        "velocity_per_supported_day":(qty/Decimal(n) if n else None),
    }


def _family_regular_baseline(
    cur,
    upc_rows: list[dict[str,Any]],
    supported_day_limit: int=28,
    prepared_series: dict[str,Any]|None=None,
) -> dict[str,Any]:
    s=prepared_series if prepared_series is not None else _family_sales_series(cur,upc_rows,supported_day_limit)
    if s.get("status")!="READY":
        return {
            **s,
            "regular_supported_day_count":0,
            "regular_sold_quantity":None,
            "regular_velocity_per_supported_day":None,
        }
    regular=[x for x in s["rows"] if not x.get("has_sale")]
    qty=sum((_d(x["sold_quantity"]) for x in regular),Decimal("0"))
    n=len(regular)
    return {
        "status":"READY" if n else "NO_REGULAR_BASELINE",
        "uom":s["uom"],
        "requested_supported_days":supported_day_limit,
        "regular_supported_day_count":n,
        "regular_sold_quantity":qty,
        "regular_velocity_per_supported_day":(qty/Decimal(n) if n else None),
        "sale_days_excluded":len(s["rows"])-n,
        "tpr_treated_as_regular":True,
        "missing_calendar_dates_are_zero":False,
    }


def _family_historical_sale_periods(
    cur,
    upc_rows: list[dict[str,Any]],
    supported_day_limit: int=365,
) -> list[dict[str,Any]]:
    s=_family_sales_series(cur,upc_rows,supported_day_limit)
    if s.get("status")!="READY":
        return []
    rows={x["date"]:x for x in s["rows"]}
    ordered=sorted(rows)
    periods=[]
    start=None
    last_sale=None
    for day in ordered:
        has_sale=bool(rows[day].get("has_sale"))
        if has_sale:
            if start is None:
                start=day
            elif (day-start).days+1>9:
                if last_sale is not None:
                    periods.append((start,last_sale))
                start=day
            last_sale=day
        elif start is not None:
            if last_sale is not None:
                periods.append((start,last_sale))
            start=None
            last_sale=None
    if start is not None and last_sale is not None:
        periods.append((start,last_sale))

    out=[]
    for start,end in periods:
        span=[d for d in ordered if start<=d<=end]
        sale_qty=sum((_d(rows[d].get("sale_quantity")) for d in span),Decimal("0"))
        sale_sales=sum((_d(rows[d].get("sale_sales_amount")) for d in span),Decimal("0"))
        sale_days=sum(1 for d in span if rows[d].get("has_sale"))
        calendar=(end-start).days+1
        out.append({
            "promotion_type":_promotion_type(start,end),
            "start_date":start,
            "end_date":end,
            "start_weekday":WEEKDAY_NAMES[start.weekday()],
            "end_weekday":WEEKDAY_NAMES[end.weekday()],
            "weekday_range":f"{WEEKDAY_NAMES[start.weekday()]} to {WEEKDAY_NAMES[end.weekday()]}",
            "calendar_duration_days":calendar,
            "supported_sales_day_count":len(span),
            "sale_observed_day_count":sale_days,
            "coverage_ratio":Decimal(len(span))/Decimal(calendar) if calendar else None,
            "sale_price":(sale_sales/sale_qty if sale_qty!=0 else None),
            "sale_quantity":sale_qty,
            "sale_velocity_per_supported_day":(
                sale_qty/Decimal(len(span)) if span else None
            ),
            "coverage_status":"COMPLETE" if len(span)==calendar else "PARTIAL",
            "promotion_definition":"PRICE_TYPE_SALE_ONLY",
            "uom":s["uom"],
        })
    out.sort(key=lambda x:(x["end_date"],x["start_date"]),reverse=True)
    return out


def family_promotion_history(family_key: str) -> dict[str,Any]:
    raw=str(family_key or "").strip()
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        if raw.isdigit():
            cur.execute(
                """SELECT family_id,main_article_number,family_description
                   FROM product_family
                   WHERE main_article_number=%s OR family_id=%s
                   ORDER BY CASE WHEN main_article_number=%s THEN 0 ELSE 1 END
                   LIMIT 1""",
                (raw,int(raw),raw),
            )
        else:
            cur.execute(
                """SELECT family_id,main_article_number,family_description
                   FROM product_family
                   WHERE UPPER(family_description)=UPPER(%s)
                   LIMIT 1""",
                (raw,),
            )
        fam=cur.fetchone()
        if not fam:
            cur.close()
            raise KeyError("V2_FAMILY_NOT_FOUND")
        cur.execute(
            """SELECT * FROM quick_check_current
               WHERE family_id=%s
               ORDER BY ean_upc""",
            (int(fam["family_id"]),),
        )
        rows=cur.fetchall()
        hist=_family_historical_sale_periods(cur,rows,365)
        cur.close()
    return {
        "contract_version":"WEBAPP_V2_FAMILY_PROMOTION_V1",
        "family_id":fam["family_id"],
        "family_article_number":fam["main_article_number"],
        "family_article_name":fam["family_description"],
        "historical_promotions":hist,
        "promotion_definition":"PRICE_TYPE_SALE_ONLY",
        "tpr_is_promotion":False,
    }


def _family_promotion_baseline(
    history: list[dict[str,Any]],
    start_date: date,
    end_date: date,
    promotion_price: Decimal|None=None,
) -> dict[str,Any]:
    requested=_promotion_type(start_date,end_date)
    same=[
        x for x in history
        if x.get("promotion_type")==requested
        and x.get("sale_velocity_per_supported_day") is not None
    ]
    target_price=Decimal(str(promotion_price)) if promotion_price is not None else None
    def promo_sort_key(x: dict[str,Any]):
        p=x.get("sale_price")
        distance=(abs(_d(p)-target_price) if target_price is not None and p is not None else Decimal("999999"))
        return (distance,-x["end_date"].toordinal())
    same.sort(key=promo_sort_key)
    selected=same[:3]
    if not selected:
        return {
            "status":"NO_MATCHING_PROMOTION_HISTORY",
            "promotion_type":requested,
            "promotion_velocity_per_day":None,
            "selected_history":[],
            "confidence":"LOW",
        }
    qty=sum((_d(x.get("sale_quantity")) for x in selected),Decimal("0"))
    days=sum((int(x.get("supported_sales_day_count") or 0) for x in selected),0)
    vel=qty/Decimal(days) if days else None
    return {
        "status":"READY",
        "promotion_type":requested,
        "promotion_velocity_per_day":vel,
        "selected_history":selected,
        "confidence":"HIGH" if len(selected)>=2 and all(x.get("coverage_status")=="COMPLETE" for x in selected) else "MEDIUM",
        "selection_basis":"SAME_PROMOTION_TYPE_THEN_CLOSEST_SALE_PRICE_THEN_RECENCY",
    }



def _ordering_family_bucket(
    cur,
    family_id: int,
    product_class: Any=None,
    current_cost_source: Any=None,
    official_source: Any=None,
) -> str | None:
    """Resolve the operational Ordering bucket.

    Ordering exposes FRESH and FROZEN. LIVE belongs to the FRESH ordering
    bucket. When Quick Check product_class is blank, use official report
    evidence instead of silently excluding the family.
    """
    pclass=str(product_class or "").strip().upper()
    if pclass=="FROZEN":
        return "FROZEN"
    if pclass in {"FRESH","LIVE"}:
        return "FRESH"

    for raw_source in (current_cost_source, official_source):
        source=str(raw_source or "").strip().upper()
        if source=="FROZEN_INVENTORY_OFFICIAL_COST":
            return "FROZEN"
        if source=="LIVE_FRESH_SUGGESTION_OFFICIAL_COST":
            return "FRESH"

    # Report membership is the category authority even when the report has
    # no usable Official Cost. company_price_observation is populated for the
    # Live/Fresh and Frozen reports whenever A/B/C or Cost evidence exists.
    cur.execute(
        """SELECT source_type
           FROM company_price_observation
           WHERE family_id=%s
             AND source_type IN ('frozen_inventory','live_fresh_suggestion')
           ORDER BY observation_date DESC,company_price_observation_id DESC
           LIMIT 1""",
        (int(family_id),),
    )
    row=cur.fetchone()
    source=str((row or {}).get("source_type") or "").strip().lower()
    if source=="frozen_inventory":
        return "FROZEN"
    if source=="live_fresh_suggestion":
        return "FRESH"
    return None


def _ordering_candidate_families(cur, kind: str) -> list[dict[str,Any]]:
    """Return families for one operational Ordering bucket in one bulk read."""
    target=str(kind or "").strip().upper()
    if target not in {"FRESH","FROZEN"}:
        raise ValueError("ORDER_TYPE_MUST_BE_FRESH_OR_FROZEN")

    cur.execute(
        """WITH ranked_qc AS (
             SELECT family_id,main_article_number,family_description,
                    product_class,cost_source,
                    ROW_NUMBER() OVER (
                      PARTITION BY family_id
                      ORDER BY CASE quick_check_status
                                 WHEN 'READY' THEN 0
                                 WHEN 'QA_HOLD' THEN 1
                                 ELSE 2
                               END,
                               COALESCE(upc_velocity_7d,0) DESC,
                               ean_upc
                    ) AS rn
             FROM quick_check_current
             WHERE family_id IS NOT NULL
           ),
           ranked_report AS (
             SELECT family_id,source_type,
                    ROW_NUMBER() OVER (
                      PARTITION BY family_id
                      ORDER BY observation_date DESC,company_price_observation_id DESC
                    ) AS rn
             FROM company_price_observation
             WHERE source_type IN ('frozen_inventory','live_fresh_suggestion')
               AND family_id IS NOT NULL
           )
           SELECT q.family_id,q.main_article_number,q.family_description,
                  q.product_class,q.cost_source,
                  o.source_type AS official_source
           FROM ranked_qc q
           LEFT JOIN ranked_report o
             ON o.family_id=q.family_id AND o.rn=1
           WHERE q.rn=1
           ORDER BY q.family_description,q.main_article_number"""
    )
    out=[]
    for fam in cur.fetchall():
        pclass=str(fam.get("product_class") or "").strip().upper()
        cost_source=str(fam.get("cost_source") or "").strip().upper()
        official_source=str(fam.get("official_source") or "").strip().upper()
        if pclass=="FROZEN":
            bucket="FROZEN"
        elif pclass in {"FRESH","LIVE"}:
            bucket="FRESH"
        elif cost_source=="FROZEN_INVENTORY_OFFICIAL_COST":
            bucket="FROZEN"
        elif cost_source=="LIVE_FRESH_SUGGESTION_OFFICIAL_COST":
            bucket="FRESH"
        elif official_source.lower()=="frozen_inventory":
            bucket="FROZEN"
        elif official_source.lower()=="live_fresh_suggestion":
            bucket="FRESH"
        else:
            bucket=None
        if bucket==target:
            fam["ordering_category"]=bucket
            out.append(fam)
    return out


def bulk_ordering_suggestions(
    order_type: str,
    *,
    ordering_date: date|None=None,
    expected_delivery_date: date|None=None,
    include_sufficient_stock: bool=False,
    family_ids: set[int]|list[int]|tuple[int,...]|None=None,
    promotion_involved: bool=False,
    promotion_start_date: date|None=None,
    promotion_end_date: date|None=None,
    promotion_items: list[dict[str,Any]]|None=None,
) -> dict[str,Any]:
    """Read-only Family Article ordering simulator for the main Ordering page."""
    kind=str(order_type or "").strip().upper()
    if kind not in {"FRESH","FROZEN"}:
        raise ValueError("ORDER_TYPE_MUST_BE_FRESH_OR_FROZEN")
    order_day=ordering_date or business_today()
    default_weekday=4 if kind=="FRESH" else 1  # Friday / Tuesday
    delivery=expected_delivery_date or _strict_next_weekday(order_day,default_weekday)
    if delivery < order_day:
        raise ValueError("EXPECTED_DELIVERY_BEFORE_ORDER_DATE")
    next_next=delivery+timedelta(days=7)

    promo_map={}
    for item in promotion_items or []:
        key=str(item.get("family_article_number") or item.get("family_id") or "").strip()
        if key:
            promo_map[key]=item

    if promotion_involved:
        if promotion_start_date is None or promotion_end_date is None:
            raise ValueError("PROMOTION_DATES_REQUIRED")
        if promotion_end_date < promotion_start_date:
            raise ValueError("PROMOTION_END_BEFORE_START")
        if not promo_map:
            raise ValueError("PROMOTION_ITEMS_REQUIRED")
        for item in promo_map.values():
            if item.get("promotion_price") is None:
                raise ValueError("PROMOTION_ITEM_PRICE_REQUIRED")
            if Decimal(str(item.get("promotion_price"))) <= 0:
                raise ValueError("PROMOTION_ITEM_PRICE_INVALID")

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        shared_sales_days_28=_canonical_sales_days(cur,limit=28)
        families=_ordering_candidate_families(cur,kind)
        if family_ids is not None:
            allowed_family_ids={int(x) for x in family_ids}
            families=[x for x in families if int(x.get("family_id")) in allowed_family_ids]
        suggestions=[]
        skipped=[]

        for fam in families:
            fid=int(fam["family_id"])
            cur.execute(
                """SELECT * FROM quick_check_current
                   WHERE family_id=%s
                     AND quick_check_status IN ('READY','QA_HOLD','HISTORICAL_ONLY')
                   ORDER BY ean_upc""",
                (fid,),
            )
            rows=cur.fetchall()
            if not rows:
                continue

            m28=_family_sales_series(cur,rows,28,data_days=shared_sales_days_28)
            m7=_family_sales_tail(m28,7)
            if m28.get("status")!="READY" or m7.get("status")!="READY":
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":"FAMILY_UOM_UNRESOLVED",
                })
                continue

            active_28=_d(m28.get("sold_quantity"))>0
            vel7=m7.get("velocity_per_supported_day")
            family_oh=_family_effective_oh(cur,rows)
            if family_oh.get("status")!="READY" or family_oh.get("quantity") is None:
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":str(family_oh.get("status") or "OH_UNAVAILABLE"),
                })
                continue

            oh_uom=str(family_oh.get("uom") or "").upper()
            demand_uom=str(m7.get("uom") or "").upper()
            if not oh_uom or oh_uom!=demand_uom:
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":"OH_TO_FAMILY_DEMAND_UOM_UNRESOLVED",
                })
                continue

            raw_oh=_d(family_oh.get("quantity"))
            ordering_oh=max(Decimal("0"),raw_oh)
            dos=(ordering_oh/_d(vel7)) if vel7 is not None and _d(vel7)>0 else None
            if not active_28 or dos is None or (dos>=Decimal("7") and not include_sufficient_stock):
                continue

            regular=_family_regular_baseline(cur,rows,28,prepared_series=m28)
            reg_vel=regular.get("regular_velocity_per_supported_day")
            if reg_vel is None:
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":"REGULAR_BASELINE_UNAVAILABLE",
                })
                continue

            fam_key=str(fam.get("main_article_number") or "")
            promo_item=promo_map.get(fam_key) or promo_map.get(str(fid))
            promo_history=_family_historical_sale_periods(cur,rows,365) if promo_item else []
            promo_baseline=None
            promo_vel=None
            promo_fallback=False
            if promotion_involved and promo_item:
                promo_baseline=_family_promotion_baseline(
                    promo_history,
                    promotion_start_date,
                    promotion_end_date,
                    promo_item.get("promotion_price"),
                )
                promo_vel=promo_baseline.get("promotion_velocity_per_day")
                if promo_vel is None:
                    promo_vel=reg_vel
                    promo_fallback=True

            total=Decimal("0")
            before_delivery=Decimal("0")
            day=order_day
            segments={"REGULAR":Decimal("0"),"PROMOTION":Decimal("0")}
            while day<next_next:
                is_promo=bool(
                    promotion_involved and promo_item
                    and promotion_start_date<=day<=promotion_end_date
                )
                use_vel=_d(promo_vel if is_promo else reg_vel)
                total+=use_vel
                segments["PROMOTION" if is_promo else "REGULAR"]+=use_vel
                if day<delivery:
                    before_delivery+=use_vel
                day+=timedelta(days=1)

            suggested=max(Decimal("0"),total-ordering_oh)
            suggestions.append({
                "family_id":fid,
                "family_article_number":fam.get("main_article_number"),
                "family_article_name":fam.get("family_description"),
                "category":kind,
                "effective_oh_raw":raw_oh,
                "ordering_oh_used":ordering_oh,
                "negative_oh_treated_as_zero":raw_oh<0,
                "uom":demand_uom,
                "qty_7d":m7.get("sold_quantity"),
                "supported_days_7d":m7.get("supported_day_count"),
                "qty_28d":m28.get("sold_quantity"),
                "supported_days_28d":m28.get("supported_day_count"),
                "velocity_7d":vel7,
                "dos":dos,
                "regular_baseline":regular,
                "promotion_involved":bool(promo_item),
                "promotion_item":promo_item,
                "promotion_baseline":promo_baseline,
                "historical_promotions":promo_history[:5],
                "promotion_fallback_to_regular":promo_fallback,
                "forecast_regular_usage":segments["REGULAR"],
                "forecast_promotion_usage":segments["PROMOTION"],
                "forecast_total_usage":total,
                "forecast_usage_before_delivery":before_delivery,
                "projected_oh_at_delivery":ordering_oh-before_delivery,
                "suggested_order_qty":suggested,
                "suggested_order_uom":demand_uom,
                "readiness":(
                    "READY" if any(str(x.get("quick_check_status") or "")=="READY" for x in rows)
                    else str(rows[0].get("quick_check_status") or "UNKNOWN")
                ),
            })

        suggestions.sort(key=lambda x:(float(x.get("dos") or 999999),-float(x.get("qty_28d") or 0),str(x.get("family_article_name") or "")))
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_BULK_ORDERING_V1",
        "order_type":kind,
        "category_scope":["FRESH","LIVE"] if kind=="FRESH" else ["FROZEN"],
        "inputs":{
            "ordering_date":order_day,
            "expected_delivery_date":delivery,
            "expected_delivery_default_source":(
                "USER_INPUT" if expected_delivery_date is not None
                else ("FOLLOWING_FRIDAY" if kind=="FRESH" else "FOLLOWING_TUESDAY")
            ),
            "next_next_delivery_date":next_next,
            "promotion_involved":bool(promotion_involved),
            "promotion_start_date":promotion_start_date,
            "promotion_end_date":promotion_end_date,
            "promotion_items":promotion_items or [],
        },
        "eligibility":{
            "active_selling":"POSITIVE_QTY_IN_LATEST_28_COMPLETED_CANONICAL_POS_DAYS",
            "dos_threshold":(
                "ALL_ACTIVE_FAMILIES_WHEN_DELIVERY_DATE_ROSTER"
                if include_sufficient_stock else "LESS_THAN_7_DAYS"
            ),
            "include_sufficient_stock":bool(include_sufficient_stock),
            "family_prefilter_applied":family_ids is not None,
            "negative_effective_oh_for_ordering":"TREAT_AS_ZERO",
        },
        "suggestion_count":len(suggestions),
        "suggestions":suggestions,
        "skipped_count":len(skipped),
        "skipped":skipped,
        "rules":{
            "sales_history":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
            "missing_source_dates_count_as_zero":False,
            "promotion_definition":"PRICE_TYPE_SALE_ONLY",
            "tpr_is_promotion":False,
            "coverage_target":"THROUGH_DAY_BEFORE_NEXT_NEXT_DELIVERY",
            "saved":False,
            "submitted":False,
        },
    }

def _pi_owner_key(system_oh: dict[str,Any]) -> tuple[str,int] | None:
    scope=str(system_oh.get("scope_type") or "").upper()
    if scope=="UPC" and system_oh.get("upc_id") is not None:
        return scope,int(system_oh["upc_id"])
    if scope=="ARTICLE" and system_oh.get("article_id") is not None:
        return scope,int(system_oh["article_id"])
    if scope=="FAMILY" and system_oh.get("family_id") is not None:
        return scope,int(system_oh["family_id"])
    return None


def _pi_owner_summary(cur,row:dict[str,Any]) -> dict[str,Any] | None:
    system_oh=_system_oh_context(cur,row)
    if not system_oh:
        return None
    owner_key=_pi_owner_key(system_oh)
    if owner_key is None:
        return None

    system_position=_system_position(cur,system_oh)
    active_true_stock=_active_true_stock(cur,system_oh)
    actual_position=_actual_position(cur,active_true_stock)
    effective_position=actual_position if active_true_stock else system_position

    scope,owner_id=owner_key
    owner_name=None
    if scope=="UPC":
        owner_name=row.get("selling_description")
    elif scope=="ARTICLE":
        cur.execute(
            "SELECT article_description FROM article WHERE article_id=%s LIMIT 1",
            (owner_id,),
        )
        a=cur.fetchone() or {}
        owner_name=a.get("article_description") or row.get("selling_description")
    else:
        owner_name=row.get("family_description")

    return {
        "owner_scope":scope,
        "owner_id":owner_id,
        "owner_name":owner_name,
        "family_id":row.get("family_id"),
        "family_article_number":row.get("main_article_number"),
        "family_name":row.get("family_description"),
        "article_id":row.get("article_id"),
        "article_number":row.get("article_number"),
        "representative_upc":row.get("ean_upc"),
        "representative_upc_name":row.get("selling_description"),
        "category":row.get("product_class"),
        "readiness":row.get("quick_check_status"),
        "system_oh":{
            "quantity":system_position.get("quantity") if system_position else None,
            "uom":system_position.get("uom") if system_position else system_oh.get("uom_code"),
            "analysis_usable":bool(system_position and system_position.get("analysis_usable")),
            "blockers":system_position.get("blockers") if system_position else ["SYSTEM_OH_POSITION_NOT_AVAILABLE"],
            "anchor_quantity":system_position.get("anchor_quantity") if system_position else system_oh.get("on_hand_quantity"),
            "anchor_date":system_position.get("anchor_date") if system_position else system_oh.get("observation_date"),
            "movement_delta":system_position.get("movement_delta") if system_position else None,
            "movement_through_date":system_position.get("movement_through_date") if system_position else None,
            "source_file_id":system_oh.get("file_id"),
            "snapshot_date":system_oh.get("observation_date"),
        },
        "effective_oh":{
            "quantity":effective_position.get("quantity") if effective_position else None,
            "uom":effective_position.get("uom") if effective_position else (system_position.get("uom") if system_position else system_oh.get("uom_code")),
            "analysis_usable":bool(effective_position and effective_position.get("analysis_usable")),
            "source":"TRUE_STOCK" if active_true_stock else "SYSTEM_OH",
            "movement_through_date":effective_position.get("movement_through_date") if effective_position else None,
        },
        "active_true_stock":active_true_stock,
        "required_true_stock_uom":(
            system_position.get("uom")
            if system_position and system_position.get("uom")
            else system_oh.get("uom_code")
        ),
    }


def pi_search_items(query:str,limit:int=30) -> dict[str,Any]:
    """Search PI targets and deduplicate UPCs that share one inventory owner."""
    core=search_items(query,max(1,min(int(limit or 30)*2,50)))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        targets:dict[tuple[str,int],dict[str,Any]]={}
        for result in core.get("results",[]):
            rows=[]
            if result.get("result_type")=="UPC":
                cur.execute(
                    "SELECT * FROM quick_check_current WHERE ean_upc=%s LIMIT 1",
                    (result.get("number"),),
                )
                row=cur.fetchone()
                if row:
                    rows=[row]
            elif result.get("result_type")=="FAMILY" and result.get("family_id") is not None:
                cur.execute(
                    "SELECT * FROM quick_check_current WHERE family_id=%s ORDER BY ean_upc",
                    (int(result["family_id"]),),
                )
                rows=cur.fetchall()

            for row in rows:
                summary=_pi_owner_summary(cur,row)
                if not summary:
                    continue
                key=(summary["owner_scope"],int(summary["owner_id"]))
                m28=_sales_metric(cur,int(row["upc_id"]),28)
                existing=targets.get(key)
                if existing is None:
                    targets[key]={
                        **summary,
                        "relevance":int(result.get("relevance") or 0),
                        "qty_28d":_d(m28.get("sold_quantity")),
                        "qty_28d_uom":row.get("selling_uom"),
                        "supported_days_28d":int(m28.get("supported_day_count") or 0),
                        "_upc_ids":{int(row["upc_id"])},
                        "_qty_uoms":{str(row.get("selling_uom") or "").strip().upper()},
                    }
                else:
                    existing["relevance"]=max(int(existing.get("relevance") or 0),int(result.get("relevance") or 0))
                    uid=int(row["upc_id"])
                    if uid not in existing["_upc_ids"]:
                        existing["_upc_ids"].add(uid)
                        uom=str(row.get("selling_uom") or "").strip().upper()
                        existing["_qty_uoms"].add(uom)
                        if len({x for x in existing["_qty_uoms"] if x})==1:
                            existing["qty_28d"]=_d(existing.get("qty_28d"))+_d(m28.get("sold_quantity"))
                        else:
                            existing["qty_28d"]=None
                            existing["qty_28d_uom"]=None
                    existing["supported_days_28d"]=min(
                        int(existing.get("supported_days_28d") or 0),
                        int(m28.get("supported_day_count") or 0),
                    )

        rows=[]
        for x in targets.values():
            x.pop("_upc_ids",None)
            x.pop("_qty_uoms",None)
            rows.append(x)
        rows.sort(
            key=lambda x:(
                -int(x.get("relevance") or 0),
                _readiness_rank(x.get("readiness")),
                -float(x.get("qty_28d") or 0),
                str(x.get("owner_name") or ""),
            )
        )
        cur.close()
    rows=rows[:max(1,min(int(limit or 30),50))]
    return {
        "contract_version":"WEBAPP_V2_PI_SEARCH_V1",
        "query":str(query or "").strip(),
        "count":len(rows),
        "results":rows,
        "dedupe_contract":"ONE_RESULT_PER_INVENTORY_OWNER",
        "inventory_owner_scopes":["UPC","ARTICLE","FAMILY"],
    }


def pi_item(upc:str,history_limit:int=20) -> dict[str,Any]:
    raw=str(upc or "").strip()
    nk=_numeric_key(raw)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM quick_check_current
               WHERE ean_upc=%s
                  OR (ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM ean_upc)=%s)
               ORDER BY CASE quick_check_status WHEN 'READY' THEN 0 WHEN 'QA_HOLD' THEN 1 ELSE 2 END
               LIMIT 1""",
            (raw,nk),
        )
        row=cur.fetchone()
        if not row:
            cur.close()
            raise KeyError("V2_PI_ITEM_NOT_FOUND")

        summary=_pi_owner_summary(cur,row)
        if not summary:
            cur.close()
            raise ValueError("PI_INVENTORY_OWNER_UNRESOLVED")

        system_oh=_system_oh_context(cur,row)
        history=_true_stock_history(cur,system_oh,max(1,min(int(history_limit or 20),50)))
        hist=[]
        for h in history:
            system_qty=(Decimal(str(h["system_oh_quantity"])) if h.get("system_oh_quantity") is not None else None)
            true_qty=(Decimal(str(h["true_stock_quantity"])) if h.get("true_stock_quantity") is not None else None)
            signed=(true_qty-system_qty if true_qty is not None and system_qty is not None else None)
            hist.append({
                "true_stock_id":h.get("true_stock_id"),
                "submitted_at":h.get("submitted_at"),
                "submitted_by":h.get("submitted_by"),
                "system_oh_quantity":system_qty,
                "true_stock_quantity":true_qty,
                "uom":h.get("uom_code"),
                "signed_difference_true_minus_system":signed,
                "shortage_quantity":max(Decimal("0"),-signed) if signed is not None else None,
                "overage_quantity":max(Decimal("0"),signed) if signed is not None else None,
                "count_note":h.get("count_note"),
                "status":h.get("override_status"),
                "superseded_at":h.get("superseded_at"),
                "superseded_by_oh_file_id":h.get("superseded_by_oh_file_id"),
            })

        events=_family_receipt_events(cur,int(row["family_id"]),180)
        article_id=int(row["article_id"]) if row.get("article_id") is not None else None
        relevant_events=[
            x for x in events
            if x.get("receipt_quantity") is not None
            and _d(x.get("receipt_quantity"))>0
            and (article_id is None or x.get("article_id")==article_id)
        ]
        last_receipt=relevant_events[0] if relevant_events else None

        sys_qty=summary["system_oh"].get("quantity")
        eff_qty=summary["effective_oh"].get("quantity")
        sys_uom=str(summary["system_oh"].get("uom") or "").upper()
        eff_uom=str(summary["effective_oh"].get("uom") or "").upper()
        current_signed=(
            _d(eff_qty)-_d(sys_qty)
            if sys_qty is not None and eff_qty is not None and sys_uom and sys_uom==eff_uom
            else None
        )
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_PI_ITEM_V1",
        "identity":{
            "upc":row.get("ean_upc"),
            "upc_name":row.get("selling_description"),
            "article_number":row.get("article_number"),
            "family_article_number":row.get("main_article_number"),
            "family_name":row.get("family_description"),
            "category":row.get("product_class"),
            "readiness":row.get("quick_check_status"),
        },
        "inventory_owner":{
            "scope":summary.get("owner_scope"),
            "owner_id":summary.get("owner_id"),
            "owner_name":summary.get("owner_name"),
        },
        "system_oh":summary.get("system_oh"),
        "effective_oh":summary.get("effective_oh"),
        "active_true_stock":summary.get("active_true_stock"),
        "required_true_stock_uom":summary.get("required_true_stock_uom"),
        "current_discrepancy":{
            "signed_difference_true_minus_system":current_signed,
            "shortage_quantity":max(Decimal("0"),-current_signed) if current_signed is not None else None,
            "overage_quantity":max(Decimal("0"),current_signed) if current_signed is not None else None,
            "uom":sys_uom or eff_uom or None,
        },
        "last_receipt":last_receipt,
        "true_stock_history":hist,
        "rules":{
            "negative_true_stock_allowed":False,
            "true_stock_authority":"ACTIVE_UNTIL_LATER_ACCEPTED_OH_UPLOAD",
            "shortage_creates_pending_dumping_discrepancy":True,
            "overage_creates_dumping_quantity":False,
        },
    }

# ---- V2 latest overrides ----

def _family_system_oh_anchor(
    cur,
    rows: list[dict[str,Any]],
) -> dict[str,Any] | None:
    """Resolve an OH upload row owned by the Family Article itself.

    Inventory uploads can resolve their main family article into article_id,
    so requiring article_id IS NULL incorrectly hides valid Family OH.
    Prefer the main_article_number row, then a true family-scope row.
    """
    if not rows:
        return None
    family_id=next(
        (int(x["family_id"]) for x in rows if x.get("family_id") is not None),
        None,
    )
    main_article=next(
        (str(x.get("main_article_number")) for x in rows if x.get("main_article_number")),
        None,
    )
    if family_id is None:
        return None

    cur.execute(
        """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                  observation_date,article_id,article_number,family_id,
                  ean_upc,upc_id,on_hand_quantity,uom_code,source_type
           FROM inventory_observation
           WHERE family_id=%s
             AND upc_id IS NULL
             AND on_hand_quantity IS NOT NULL
             AND (
                  article_id IS NULL
                  OR article_number=%s
             )
           ORDER BY observation_date DESC,file_id DESC,
                    CASE WHEN article_number=%s THEN 0 ELSE 1 END,
                    raw_id DESC
           LIMIT 1""",
        (family_id,main_article,main_article),
    )
    r=cur.fetchone()
    if not r:
        return None

    # The uploaded row represents the Family Article OH baseline. Roll it
    # forward at FAMILY scope so all compatible family movements are applied.
    r["scope_type"]="FAMILY"
    r["article_id"]=None
    r["upc_id"]=None
    return r


def _family_owner_positions(cur, rows: list[dict[str,Any]], *, use_child_true_stock: bool) -> dict[str,Any]:
    owners: dict[tuple[str,int],dict[str,Any]] = {}
    for row in rows:
        ctx=_system_oh_context(cur,row)
        if not ctx:
            continue
        scope=str(ctx.get("scope_type") or "").upper()
        if scope=="UPC":
            oid=ctx.get("upc_id")
        elif scope=="ARTICLE":
            oid=ctx.get("article_id")
        elif scope=="FAMILY":
            oid=ctx.get("family_id")
        else:
            oid=None
        if oid is None:
            continue
        key=(scope,int(oid))
        if key in owners:
            continue

        system=_system_position(cur,ctx)
        true_stock=_active_true_stock(cur,ctx) if use_child_true_stock else None
        actual=_actual_position(cur,true_stock) if true_stock else None
        pos=actual if true_stock else system
        owners[key]={
            "scope_type":scope,
            "owner_id":int(oid),
            "quantity":pos.get("quantity") if pos else None,
            "uom":pos.get("uom") if pos else None,
            "source":"TRUE_STOCK" if true_stock else "SYSTEM_OH",
            "analysis_usable":bool(pos and pos.get("analysis_usable")),
            "blockers":pos.get("blockers") if pos else ["OH_POSITION_NOT_AVAILABLE"],
            "anchor_on_hand_file_id":ctx.get("file_id"),
            "anchor_date":ctx.get("observation_date"),
        }

    # Some inventory snapshots are owned by the receiving/main article rather
    # than the selling article attached to a UPC.  If child lookup found no
    # inventory owner, supplement from confirmed article-level OH in the same
    # family.  This fixes valid Family OH such as 1342107 without double
    # counting an already-resolved child owner.
    has_usable_child_owner=any(
        x.get("analysis_usable")
        and x.get("quantity") is not None
        and x.get("uom")
        for x in owners.values()
    )
    if not has_usable_child_owner and rows:
        family_id=next(
            (int(x["family_id"]) for x in rows if x.get("family_id") is not None),
            None,
        )
        if family_id is not None:
            cur.execute(
                """SELECT io.*
                   FROM inventory_observation io
                   JOIN (
                       SELECT article_id,MAX(observation_date) AS max_date
                       FROM inventory_observation
                       WHERE family_id=%s
                         AND article_id IS NOT NULL
                         AND upc_id IS NULL
                         AND on_hand_quantity IS NOT NULL
                       GROUP BY article_id
                   ) latest
                     ON latest.article_id=io.article_id
                    AND latest.max_date=io.observation_date
                   WHERE io.family_id=%s
                     AND io.article_id IS NOT NULL
                     AND io.upc_id IS NULL
                     AND io.on_hand_quantity IS NOT NULL
                   ORDER BY io.article_id,io.file_id DESC,io.raw_id DESC""",
                (family_id,family_id),
            )
            seen_articles=set()
            for ctx in cur.fetchall():
                aid=ctx.get("article_id")
                if aid is None or int(aid) in seen_articles:
                    continue
                seen_articles.add(int(aid))
                ctx["scope_type"]="ARTICLE"
                pos=_system_position(cur,ctx)
                owners[("ARTICLE",int(aid))]={
                    "scope_type":"ARTICLE",
                    "owner_id":int(aid),
                    "quantity":pos.get("quantity") if pos else None,
                    "uom":pos.get("uom") if pos else None,
                    "source":"SYSTEM_OH_RECEIVING_ARTICLE_FALLBACK",
                    "analysis_usable":bool(pos and pos.get("analysis_usable")),
                    "blockers":pos.get("blockers") if pos else ["OH_POSITION_NOT_AVAILABLE"],
                    "anchor_on_hand_file_id":ctx.get("file_id"),
                    "anchor_date":ctx.get("observation_date"),
                }

    usable=[
        x for x in owners.values()
        if x.get("analysis_usable")
        and x.get("quantity") is not None
        and x.get("uom")
    ]
    uoms={str(x["uom"]).upper() for x in usable}
    if not usable:
        result={
            "status":"UNAVAILABLE","quantity":None,"uom":None,
            "owners":list(owners.values()),
        }
        result["reason"]=_oh_display_reason(
            result["status"],
            [b for x in result["owners"] for b in (x.get("blockers") or [])],
            result["owners"],
        )
        return result
    if len(uoms)!=1:
        result={
            "status":"BLOCKED_MIXED_UOM","quantity":None,"uom":None,
            "owners":list(owners.values()),
        }
        result["reason"]=_oh_display_reason(result["status"],owners=result["owners"])
        return result
    owner_sources=sorted({str(x.get("source") or "") for x in usable if x.get("source")})
    return {
        "status":"READY",
        "quantity":sum((_d(x["quantity"]) for x in usable),Decimal("0")),
        "uom":next(iter(uoms)),
        "source":" + ".join(owner_sources) if owner_sources else "SYSTEM_OH",
        "reason":None,
        "owners":list(owners.values()),
    }


def _family_system_oh(cur, rows: list[dict[str,Any]]) -> dict[str,Any]:
    return _family_owner_positions(cur,rows,use_child_true_stock=False)


def _active_family_true_stock(cur, family_id: int) -> dict[str,Any] | None:
    if not _table_exists(cur,"manual_true_stock"):
        return None
    cur.execute(
        """SELECT *
           FROM manual_true_stock
           WHERE family_id=%s
             AND scope_type='FAMILY'
             AND override_status='ACTIVE'
           ORDER BY true_stock_id DESC
           LIMIT 1""",
        (int(family_id),),
    )
    return cur.fetchone()


def _family_effective_oh(cur, rows: list[dict[str,Any]]) -> dict[str,Any]:
    if not rows:
        return {
            "status":"UNAVAILABLE","quantity":None,"uom":None,"owners":[],
            "reason":_oh_display_reason("UNAVAILABLE"),
        }

    family_id=next(
        (int(x["family_id"]) for x in rows if x.get("family_id") is not None),
        None,
    )
    if family_id is not None:
        family_true=_active_family_true_stock(cur,family_id)
        if family_true:
            pos=_actual_position(cur,family_true)
            if pos and pos.get("analysis_usable") and pos.get("quantity") is not None:
                return {
                    "status":"READY",
                    "quantity":pos.get("quantity"),
                    "uom":pos.get("uom"),
                    "source":"FAMILY_TRUE_STOCK",
                    "family_true_stock_id":family_true.get("true_stock_id"),
                    "submitted_at":family_true.get("submitted_at"),
                    "movement_through_date":pos.get("movement_through_date"),
                    "reason":None,
                    "owners":[{
                        "scope_type":"FAMILY",
                        "owner_id":family_id,
                        "quantity":pos.get("quantity"),
                        "uom":pos.get("uom"),
                        "source":"FAMILY_TRUE_STOCK",
                        "analysis_usable":True,
                        "blockers":[],
                    }],
                }
            return {
                "status":"FAMILY_TRUE_STOCK_ROLLFORWARD_BLOCKED",
                "quantity":None,
                "uom":family_true.get("uom_code"),
                "source":"FAMILY_TRUE_STOCK",
                "family_true_stock_id":family_true.get("true_stock_id"),
                "owners":[],
                "blockers":pos.get("blockers") if pos else ["TRUE_STOCK_POSITION_NOT_AVAILABLE"],
                "reason":_oh_display_reason(
                    "FAMILY_TRUE_STOCK_ROLLFORWARD_BLOCKED",
                    pos.get("blockers") if pos else ["TRUE_STOCK_POSITION_NOT_AVAILABLE"],
                ),
            }

    family_anchor=_family_system_oh_anchor(cur,rows)
    if family_anchor:
        pos=_system_position(cur,family_anchor)
        if pos and pos.get("analysis_usable") and pos.get("quantity") is not None:
            return {
                "status":"READY",
                "quantity":pos.get("quantity"),
                "uom":pos.get("uom"),
                "source":"FAMILY_SYSTEM_OH",
                "anchor_on_hand_file_id":family_anchor.get("file_id"),
                "anchor_date":family_anchor.get("observation_date"),
                "movement_through_date":pos.get("movement_through_date"),
                "reason":None,
                "owners":[{
                    "scope_type":"FAMILY",
                    "owner_id":family_id,
                    "quantity":pos.get("quantity"),
                    "uom":pos.get("uom"),
                    "source":"FAMILY_SYSTEM_OH",
                    "analysis_usable":True,
                    "blockers":[],
                    "anchor_on_hand_file_id":family_anchor.get("file_id"),
                    "anchor_date":family_anchor.get("observation_date"),
                }],
            }
        return {
            "status":"FAMILY_SYSTEM_OH_ROLLFORWARD_BLOCKED",
            "quantity":None,
            "uom":family_anchor.get("uom_code"),
            "source":"FAMILY_SYSTEM_OH",
            "anchor_on_hand_file_id":family_anchor.get("file_id"),
            "anchor_date":family_anchor.get("observation_date"),
            "owners":[],
            "blockers":pos.get("blockers") if pos else ["OH_POSITION_NOT_AVAILABLE"],
            "reason":_oh_display_reason(
                "FAMILY_SYSTEM_OH_ROLLFORWARD_BLOCKED",
                pos.get("blockers") if pos else ["OH_POSITION_NOT_AVAILABLE"],
            ),
        }

    # Legacy fallback for families whose OH is genuinely child-owned.
    return _family_owner_positions(cur,rows,use_child_true_stock=True)

def bulk_ordering_suggestions(
    order_type: str,
    *,
    ordering_date: date|None=None,
    expected_delivery_date: date|None=None,
    promotion_involved: bool=False,
    promotion_start_date: date|None=None,
    promotion_end_date: date|None=None,
    promotion_items: list[dict[str,Any]]|None=None,
) -> dict[str,Any]:
    """Read-only Family Article ordering simulator for the main Ordering page.

    Promotion selection/evidence is UPC-level. Final replenishment remains
    Family Article level.
    """
    kind=str(order_type or "").strip().upper()
    if kind not in {"FRESH","FROZEN"}:
        raise ValueError("ORDER_TYPE_MUST_BE_FRESH_OR_FROZEN")

    order_day=ordering_date or business_today()
    default_weekday=4 if kind=="FRESH" else 1  # Friday / Tuesday
    delivery=expected_delivery_date or _strict_next_weekday(order_day,default_weekday)
    if delivery < order_day:
        raise ValueError("EXPECTED_DELIVERY_BEFORE_ORDER_DATE")
    next_next=delivery+timedelta(days=7)

    raw_promo_items=promotion_items or []
    if promotion_involved:
        if promotion_start_date is None or promotion_end_date is None:
            raise ValueError("PROMOTION_DATES_REQUIRED")
        if promotion_end_date < promotion_start_date:
            raise ValueError("PROMOTION_END_BEFORE_START")
        if not raw_promo_items:
            raise ValueError("PROMOTION_ITEMS_REQUIRED")
        for item in raw_promo_items:
            if not str(item.get("upc") or "").strip():
                raise ValueError("PROMOTION_ITEM_UPC_REQUIRED")
            if item.get("promotion_price") is None:
                raise ValueError("PROMOTION_ITEM_PRICE_REQUIRED")
            if Decimal(str(item.get("promotion_price"))) <= 0:
                raise ValueError("PROMOTION_ITEM_PRICE_INVALID")

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        # One canonical 28-day window is reused across every family. This
        # prevents the Ordering overview from re-reading the same POS coverage
        # and UPC history three times per family (28D, 7D, regular baseline).
        shared_sales_days_28=_canonical_sales_days(cur,limit=28)

        # Resolve every selected promotion item to one canonical UPC.
        promo_by_family: dict[int,list[dict[str,Any]]] = {}
        seen_promo_upcs=set()
        for item in raw_promo_items:
            raw_upc=str(item.get("upc") or "").strip()
            nk=_numeric_key(raw_upc)
            cur.execute(
                """SELECT * FROM quick_check_current
                   WHERE ean_upc=%s
                      OR (
                           ean_upc REGEXP '^[0-9]+$'
                           AND TRIM(LEADING '0' FROM ean_upc)=%s
                         )
                   ORDER BY CASE quick_check_status
                              WHEN 'READY' THEN 0
                              WHEN 'QA_HOLD' THEN 1
                              ELSE 2
                            END
                   LIMIT 1""",
                (raw_upc,nk),
            )
            prow=cur.fetchone()
            if not prow:
                raise ValueError(f"PROMOTION_UPC_NOT_FOUND:{raw_upc}")

            canonical_upc=str(prow.get("ean_upc") or raw_upc)
            if canonical_upc in seen_promo_upcs:
                raise ValueError(f"DUPLICATE_PROMOTION_UPC:{canonical_upc}")
            seen_promo_upcs.add(canonical_upc)

            pclass=_ordering_family_bucket(
                cur,
                int(prow["family_id"]),
                prow.get("product_class"),
                prow.get("cost_source"),
            )
            if pclass!=kind:
                raise ValueError(
                    f"PROMOTION_UPC_CATEGORY_MISMATCH:{canonical_upc}:{pclass or 'UNRESOLVED'}:{kind}"
                )

            upc_id=int(prow["upc_id"])
            upc_history=_historical_sale_periods(cur,upc_id,365)
            upc_regular=_regular_baseline(cur,upc_id,28)
            promo_baseline=(
                _promotion_forecast_baseline(
                    cur,
                    upc_id,
                    promotion_start_date,
                    promotion_end_date,
                    Decimal(str(item.get("promotion_price"))),
                )
                if promotion_involved else None
            )
            promo_by_family.setdefault(int(prow["family_id"]),[]).append({
                "upc":canonical_upc,
                "upc_id":upc_id,
                "upc_name":prow.get("selling_description"),
                "selling_uom":prow.get("selling_uom"),
                "family_id":prow.get("family_id"),
                "family_article_number":prow.get("main_article_number"),
                "family_article_name":prow.get("family_description"),
                "promotion_price":Decimal(str(item.get("promotion_price"))),
                "historical_promotions":upc_history,
                "regular_baseline":upc_regular,
                "promotion_baseline":promo_baseline,
            })

        families=_ordering_candidate_families(cur,kind)
        suggestions=[]
        skipped=[]

        for fam in families:
            fid=int(fam["family_id"])
            cur.execute(
                """SELECT * FROM quick_check_current
                   WHERE family_id=%s
                     AND quick_check_status IN ('READY','QA_HOLD','HISTORICAL_ONLY')
                   ORDER BY ean_upc""",
                (fid,),
            )
            rows=cur.fetchall()
            if not rows:
                continue

            m28=_family_sales_series(cur,rows,28,data_days=shared_sales_days_28)
            m7=_family_sales_tail(m28,7)
            if m28.get("status")!="READY" or m7.get("status")!="READY":
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":"FAMILY_UOM_UNRESOLVED",
                })
                continue

            active_28=_d(m28.get("sold_quantity"))>0
            vel7=m7.get("velocity_per_supported_day")
            family_oh=_family_effective_oh(cur,rows)
            if family_oh.get("status")!="READY" or family_oh.get("quantity") is None:
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":str(family_oh.get("status") or "OH_UNAVAILABLE"),
                })
                continue

            oh_uom=str(family_oh.get("uom") or "").upper()
            demand_uom=str(m7.get("uom") or "").upper()
            if not oh_uom or oh_uom!=demand_uom:
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":"OH_TO_FAMILY_DEMAND_UOM_UNRESOLVED",
                })
                continue

            raw_oh=_d(family_oh.get("quantity"))
            ordering_oh=max(Decimal("0"),raw_oh)
            dos=(ordering_oh/_d(vel7)) if vel7 is not None and _d(vel7)>0 else None

            # User rule: only active 28-supported-day sellers with DOS < 7.
            if not active_28 or dos is None or dos>=Decimal("7"):
                continue

            regular=_family_regular_baseline(cur,rows,28,prepared_series=m28)
            reg_vel=regular.get("regular_velocity_per_supported_day")
            if reg_vel is None:
                skipped.append({
                    "family_id":fid,
                    "family_article_number":fam.get("main_article_number"),
                    "family_article_name":fam.get("family_description"),
                    "reason":"REGULAR_BASELINE_UNAVAILABLE",
                })
                continue

            promo_items_for_family=promo_by_family.get(fid,[])
            promo_fallback=False
            promo_family_vel=_d(reg_vel)

            if promotion_involved and promo_items_for_family:
                # Family promotion-day demand:
                # family regular demand
                # - promoted UPC regular demand
                # + promoted UPC observed SALE demand.
                for pitem in promo_items_for_family:
                    upc_reg=(
                        pitem.get("regular_baseline",{})
                        .get("regular_velocity_per_supported_day")
                    )
                    baseline=pitem.get("promotion_baseline") or {}
                    upc_sale=baseline.get("promotion_velocity_per_day")

                    if upc_reg is None:
                        upc_reg=Decimal("0")
                    if upc_sale is None:
                        # No invented uplift: keep this UPC at its regular rate.
                        upc_sale=upc_reg
                        promo_fallback=True

                    promo_family_vel=max(
                        Decimal("0"),
                        promo_family_vel-_d(upc_reg)+_d(upc_sale),
                    )

            total=Decimal("0")
            before_delivery=Decimal("0")
            day=order_day
            segments={"REGULAR":Decimal("0"),"PROMOTION":Decimal("0")}

            while day<next_next:
                is_promo=bool(
                    promotion_involved
                    and promo_items_for_family
                    and promotion_start_date<=day<=promotion_end_date
                )
                use_vel=_d(promo_family_vel if is_promo else reg_vel)
                total+=use_vel
                segments["PROMOTION" if is_promo else "REGULAR"]+=use_vel
                if day<delivery:
                    before_delivery+=use_vel
                day+=timedelta(days=1)

            suggested=max(Decimal("0"),total-ordering_oh)
            suggestions.append({
                "family_id":fid,
                "family_article_number":fam.get("main_article_number"),
                "family_article_name":fam.get("family_description"),
                "category":kind,
                "effective_oh_raw":raw_oh,
                "ordering_oh_used":ordering_oh,
                "negative_oh_treated_as_zero":raw_oh<0,
                "uom":demand_uom,
                "qty_7d":m7.get("sold_quantity"),
                "supported_days_7d":m7.get("supported_day_count"),
                "qty_28d":m28.get("sold_quantity"),
                "supported_days_28d":m28.get("supported_day_count"),
                "velocity_7d":vel7,
                "dos":dos,
                "regular_baseline":regular,
                "promotion_involved":bool(promo_items_for_family),
                "promotion_items":promo_items_for_family,
                "promotion_family_velocity_per_day":(
                    promo_family_vel if promo_items_for_family else None
                ),
                "promotion_fallback_to_regular":promo_fallback,
                "forecast_regular_usage":segments["REGULAR"],
                "forecast_promotion_usage":segments["PROMOTION"],
                "forecast_total_usage":total,
                "forecast_usage_before_delivery":before_delivery,
                "projected_oh_at_delivery":ordering_oh-before_delivery,
                "suggested_order_qty":suggested,
                "suggested_order_uom":demand_uom,
                "readiness":(
                    "READY"
                    if any(
                        str(x.get("quick_check_status") or "")=="READY"
                        for x in rows
                    )
                    else str(rows[0].get("quick_check_status") or "UNKNOWN")
                ),
            })

        suggestions.sort(
            key=lambda x:(
                float(x.get("dos") or 999999),
                -float(x.get("qty_28d") or 0),
                str(x.get("family_article_name") or ""),
            )
        )
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_BULK_ORDERING_V2",
        "order_type":kind,
        "category_scope":["FRESH","LIVE"] if kind=="FRESH" else ["FROZEN"],
        "inputs":{
            "ordering_date":order_day,
            "expected_delivery_date":delivery,
            "expected_delivery_default_source":(
                "USER_INPUT"
                if expected_delivery_date is not None
                else ("FOLLOWING_FRIDAY" if kind=="FRESH" else "FOLLOWING_TUESDAY")
            ),
            "next_next_delivery_date":next_next,
            "promotion_involved":bool(promotion_involved),
            "promotion_start_date":promotion_start_date,
            "promotion_end_date":promotion_end_date,
            "promotion_items":raw_promo_items,
        },
        "eligibility":{
            "active_selling":"POSITIVE_QTY_IN_LATEST_28_COMPLETED_CANONICAL_POS_DAYS",
            "dos_threshold":"LESS_THAN_7_DAYS",
            "negative_effective_oh_for_ordering":"TREAT_AS_ZERO",
        },
        "suggestion_count":len(suggestions),
        "suggestions":suggestions,
        "skipped_count":len(skipped),
        "skipped":skipped,
        "rules":{
            "sales_history":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
            "missing_source_dates_count_as_zero":False,
            "promotion_definition":"PRICE_TYPE_SALE_ONLY",
            "promotion_item_identity":"UPC",
            "promotion_reference_history":"SELECTED_UPC_SALE_HISTORY",
            "family_promotion_demand_method":"FAMILY_REGULAR_MINUS_PROMO_UPC_REGULAR_PLUS_PROMO_UPC_SALE",
            "tpr_is_promotion":False,
            "coverage_target":"THROUGH_DAY_BEFORE_NEXT_NEXT_DELIVERY",
            "saved":False,
            "submitted":False,
        },
    }

def _resolve_family(cur, family_key: str) -> dict[str,Any] | None:
    raw=str(family_key or "").strip()
    if raw.isdigit():
        cur.execute(
            """SELECT family_id,main_article_number,family_description
               FROM product_family
               WHERE main_article_number=%s OR family_id=%s
               ORDER BY CASE WHEN main_article_number=%s THEN 0 ELSE 1 END
               LIMIT 1""",
            (raw,int(raw),raw),
        )
    else:
        cur.execute(
            """SELECT family_id,main_article_number,family_description
               FROM product_family
               WHERE UPPER(family_description)=UPPER(%s)
               LIMIT 1""",
            (raw,),
        )
    return cur.fetchone()


def _family_true_stock_history(cur, family_id: int, limit: int=20) -> list[dict[str,Any]]:
    if not _table_exists(cur,"manual_true_stock"):
        return []
    cur.execute(
        """SELECT *
           FROM manual_true_stock
           WHERE family_id=%s
             AND scope_type='FAMILY'
           ORDER BY true_stock_id DESC
           LIMIT %s""",
        (int(family_id),max(1,min(int(limit or 20),50))),
    )
    return cur.fetchall()


def pi_search_items(query:str,limit:int=30) -> dict[str,Any]:
    """PI search always resolves to Family Article targets."""
    core=search_items(query,max(1,min(int(limit or 30)*3,50)))
    family_ids=[]
    seen=set()
    for result in core.get("results",[]):
        fid=result.get("family_id")
        if fid is None and result.get("result_type")=="FAMILY":
            fid=result.get("family_id")
        if fid is not None and int(fid) not in seen:
            seen.add(int(fid)); family_ids.append(int(fid))

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        rows_out=[]
        for fid in family_ids:
            cur.execute(
                """SELECT pf.family_id,pf.main_article_number,pf.family_description
                   FROM product_family pf
                   WHERE pf.family_id=%s
                   LIMIT 1""",
                (fid,),
            )
            fam=cur.fetchone()
            if not fam:
                continue
            cur.execute(
                """SELECT * FROM quick_check_current
                   WHERE family_id=%s
                   ORDER BY ean_upc""",
                (fid,),
            )
            children=cur.fetchall()
            if not children:
                continue

            m28=_family_sales_series(cur,children,28)
            system=_family_system_oh(cur,children)
            effective=_family_effective_oh(cur,children)
            statuses=[str(x.get("quick_check_status") or "") for x in children]
            readiness=(
                "READY" if "READY" in statuses
                else ("QA_HOLD" if "QA_HOLD" in statuses else "HISTORICAL_ONLY")
            )
            categories=sorted({
                str(x.get("product_class") or "").upper()
                for x in children if x.get("product_class")
            })
            rows_out.append({
                "family_id":fid,
                "family_article_number":fam.get("main_article_number"),
                "family_article_name":fam.get("family_description"),
                "category":categories[0] if len(categories)==1 else ("MIXED" if categories else None),
                "readiness":readiness,
                "qty_28d":m28.get("sold_quantity"),
                "qty_28d_uom":m28.get("uom"),
                "supported_days_28d":int(m28.get("supported_day_count") or 0),
                "system_oh":system,
                "effective_oh":effective,
            })

        rows_out.sort(
            key=lambda x:(
                -float(x.get("qty_28d") or 0),
                _readiness_rank(x.get("readiness")),
                str(x.get("family_article_name") or ""),
            )
        )
        cur.close()

    rows_out=rows_out[:max(1,min(int(limit or 30),50))]
    return {
        "contract_version":"WEBAPP_V2_PI_SEARCH_V2",
        "query":str(query or "").strip(),
        "count":len(rows_out),
        "results":rows_out,
        "target_scope":"FAMILY_ARTICLE",
        "sort_contract":["QTY_28_SUPPORTED_DAYS_DESC","READINESS"],
    }


def pi_item(family_key:str,history_limit:int=20) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        fam=_resolve_family(cur,family_key)
        if not fam:
            cur.close()
            raise KeyError("V2_PI_FAMILY_NOT_FOUND")
        fid=int(fam["family_id"])
        cur.execute(
            """SELECT * FROM quick_check_current
               WHERE family_id=%s
               ORDER BY ean_upc""",
            (fid,),
        )
        children=cur.fetchall()
        if not children:
            cur.close()
            raise KeyError("V2_PI_FAMILY_NOT_FOUND")

        system=_family_system_oh(cur,children)
        effective=_family_effective_oh(cur,children)
        active=_active_family_true_stock(cur,fid)
        history=_family_true_stock_history(cur,fid,history_limit)
        hist=[]
        for h in history:
            system_qty=(
                Decimal(str(h["system_oh_quantity"]))
                if h.get("system_oh_quantity") is not None else None
            )
            true_qty=(
                Decimal(str(h["true_stock_quantity"]))
                if h.get("true_stock_quantity") is not None else None
            )
            signed=(
                true_qty-system_qty
                if true_qty is not None and system_qty is not None else None
            )
            hist.append({
                "true_stock_id":h.get("true_stock_id"),
                "submitted_at":h.get("submitted_at"),
                "submitted_by":h.get("submitted_by"),
                "system_oh_quantity":system_qty,
                "true_stock_quantity":true_qty,
                "uom":h.get("uom_code"),
                "signed_difference_true_minus_system":signed,
                "shortage_quantity":max(Decimal("0"),-signed) if signed is not None else None,
                "overage_quantity":max(Decimal("0"),signed) if signed is not None else None,
                "count_note":h.get("count_note"),
                "status":h.get("override_status"),
                "superseded_at":h.get("superseded_at"),
                "superseded_by_oh_file_id":h.get("superseded_by_oh_file_id"),
            })

        events=_family_receipt_events(cur,fid,180)
        last_receipt=next(
            (
                x for x in events
                if x.get("receipt_quantity") is not None
                and _d(x.get("receipt_quantity"))>0
            ),
            None,
        )
        categories=sorted({
            str(x.get("product_class") or "").upper()
            for x in children if x.get("product_class")
        })
        statuses=[str(x.get("quick_check_status") or "") for x in children]
        readiness=(
            "READY" if "READY" in statuses
            else ("QA_HOLD" if "QA_HOLD" in statuses else "HISTORICAL_ONLY")
        )

        sys_qty=system.get("quantity")
        eff_qty=effective.get("quantity")
        sys_uom=str(system.get("uom") or "").upper()
        eff_uom=str(effective.get("uom") or "").upper()
        current_signed=(
            _d(eff_qty)-_d(sys_qty)
            if sys_qty is not None and eff_qty is not None and sys_uom and sys_uom==eff_uom
            else None
        )
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_PI_FAMILY_V2",
        "family":{
            "family_id":fid,
            "family_article_number":fam.get("main_article_number"),
            "family_article_name":fam.get("family_description"),
            "category":categories[0] if len(categories)==1 else ("MIXED" if categories else None),
            "readiness":readiness,
        },
        "system_oh":system,
        "effective_oh":effective,
        "active_true_stock":active,
        "required_true_stock_uom":system.get("uom") if system.get("status")=="READY" else None,
        "current_discrepancy":{
            "signed_difference_true_minus_system":current_signed,
            "shortage_quantity":max(Decimal("0"),-current_signed) if current_signed is not None else None,
            "overage_quantity":max(Decimal("0"),current_signed) if current_signed is not None else None,
            "uom":sys_uom or eff_uom or None,
        },
        "last_receipt":last_receipt,
        "true_stock_history":hist,
        "rules":{
            "target_scope":"FAMILY_ARTICLE",
            "negative_true_stock_allowed":False,
            "true_stock_authority":"ACTIVE_UNTIL_LATER_ACCEPTED_OH_UPLOAD",
            "family_true_stock_supersedes_active_child_true_stock":True,
            "shortage_creates_pending_dumping_discrepancy":True,
            "overage_creates_dumping_quantity":False,
        },
    }


def submit_family_true_stock(
    family_key:str,
    true_stock_quantity:Decimal,
    true_stock_uom:str,
    device:str,
    note:str|None=None,
) -> dict[str,Any]:
    qty=Decimal(str(true_stock_quantity))
    if qty<0:
        raise ValueError("TRUE_STOCK_NEGATIVE")
    submitted_uom=str(true_stock_uom or "").strip().upper()
    if not submitted_uom:
        raise ValueError("TRUE_STOCK_UOM_REQUIRED")
    count_note=str(note or "").strip()[:255] or None

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            ensure_true_stock_tables(cur)
            conn.commit()
            conn.start_transaction()

            fam=_resolve_family(cur,family_key)
            if not fam:
                raise KeyError("V2_PI_FAMILY_NOT_FOUND")
            fid=int(fam["family_id"])
            cur.execute(
                """SELECT * FROM quick_check_current
                   WHERE family_id=%s
                   ORDER BY ean_upc""",
                (fid,),
            )
            children=cur.fetchall()
            if not children:
                raise KeyError("V2_PI_FAMILY_NOT_FOUND")

            system=_family_system_oh(cur,children)
            if system.get("status")!="READY" or system.get("quantity") is None or not system.get("uom"):
                raise ValueError(str(system.get("status") or "FAMILY_SYSTEM_OH_UNAVAILABLE"))
            system_qty=_d(system.get("quantity"))
            system_uom=str(system.get("uom") or "").upper()
            if submitted_uom!=system_uom:
                raise ValueError(f"TRUE_STOCK_UOM_MISMATCH:{system_uom}")

            # One Family PI count becomes the single active count for this
            # family and supersedes any older child-level or family-level count.
            cur.execute(
                """UPDATE manual_true_stock
                   SET override_status='SUPERSEDED_BY_NEW_FAMILY_TRUE_STOCK',
                       superseded_at=CURRENT_TIMESTAMP(6)
                   WHERE family_id=%s
                     AND override_status='ACTIVE'""",
                (fid,),
            )

            movement_anchor=latest_canonical_movement_day(cur)
            anchor_files=[
                int(x["anchor_on_hand_file_id"])
                for x in system.get("owners",[])
                if x.get("anchor_on_hand_file_id") is not None
            ]
            anchor_oh_file=max(anchor_files) if anchor_files else None
            discrepancy=system_qty-qty

            cur.execute(
                """INSERT INTO manual_true_stock
                   (family_id,main_article_number,scope_type,article_id,article_number,
                    upc_id,ean_upc,true_stock_quantity,uom_code,
                    system_oh_quantity,system_oh_uom_code,
                    discrepancy_quantity,anchor_on_hand_file_id,
                    anchor_movement_date,anchor_movement_file_id,
                    override_status,count_note,submitted_by)
                   VALUES (%s,%s,'FAMILY',NULL,NULL,NULL,NULL,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s,%s)""",
                (
                    fid,
                    fam.get("main_article_number"),
                    qty,
                    system_uom,
                    system_qty,
                    system_uom,
                    discrepancy,
                    anchor_oh_file,
                    movement_anchor.get("date") if movement_anchor else None,
                    movement_anchor.get("file_id") if movement_anchor else None,
                    count_note,
                    device,
                ),
            )
            true_stock_id=int(cur.lastrowid)

            queue_action="NONE"
            if discrepancy>0:
                cur.execute(
                    """SELECT discrepancy_id
                       FROM dumping_discrepancy_queue
                       WHERE family_id=%s
                         AND scope_type='FAMILY'
                         AND queue_status='PENDING'
                       ORDER BY discrepancy_id DESC
                       LIMIT 1""",
                    (fid,),
                )
                pending=cur.fetchone()
                if pending:
                    cur.execute(
                        """UPDATE dumping_discrepancy_queue
                           SET source_true_stock_id=%s,
                               main_article_number=%s,
                               scope_type='FAMILY',
                               article_id=NULL,
                               article_number=NULL,
                               ean_upc=NULL,
                               system_oh_quantity=%s,
                               true_stock_quantity=%s,
                               discrepancy_quantity=%s,
                               uom_code=%s,
                               queue_status='PENDING',
                               resolved_at=NULL
                           WHERE discrepancy_id=%s""",
                        (
                            true_stock_id,
                            fam.get("main_article_number"),
                            system_qty,qty,discrepancy,system_uom,
                            pending["discrepancy_id"],
                        ),
                    )
                    queue_action="UPDATED_PENDING"
                else:
                    cur.execute(
                        """INSERT INTO dumping_discrepancy_queue
                           (family_id,main_article_number,scope_type,article_id,article_number,
                            source_true_stock_id,ean_upc,system_oh_quantity,true_stock_quantity,
                            discrepancy_quantity,uom_code,queue_status)
                           VALUES (%s,%s,'FAMILY',NULL,NULL,%s,NULL,%s,%s,%s,%s,'PENDING')""",
                        (
                            fid,fam.get("main_article_number"),true_stock_id,
                            system_qty,qty,discrepancy,system_uom,
                        ),
                    )
                    queue_action="CREATED_PENDING"
            else:
                cur.execute(
                    """UPDATE dumping_discrepancy_queue
                       SET queue_status='RESOLVED',
                           resolved_at=CURRENT_TIMESTAMP(6)
                       WHERE family_id=%s
                         AND scope_type='FAMILY'
                         AND queue_status='PENDING'""",
                    (fid,),
                )
                if int(cur.rowcount or 0)>0:
                    queue_action="RESOLVED_PENDING"

            conn.commit()
            return {
                "status":"COMMITTED",
                "family_id":fid,
                "main_article_number":fam.get("main_article_number"),
                "family_article_name":fam.get("family_description"),
                "scope_type":"FAMILY",
                "system_oh":system_qty,
                "true_stock":qty,
                "uom":system_uom,
                "discrepancy":discrepancy,
                "true_stock_id":true_stock_id,
                "anchor_on_hand_file_id":anchor_oh_file,
                "anchor_movement_date":movement_anchor.get("date") if movement_anchor else None,
                "anchor_movement_file_id":movement_anchor.get("file_id") if movement_anchor else None,
                "dumping_queue_action":queue_action,
                "count_note":count_note,
                "effective_oh_source":"FAMILY_TRUE_STOCK",
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

def _observed_price_gp_day_candidates(
    cur,
    upc_id: int,
    *,
    current_cost: Decimal,
    supported_day_limit: int=90,
    company_c_floor: Decimal|None=None,
    up_to: date|None=None,
) -> list[dict[str,Any]]:
    """Observed-price GP$/day candidates using completed canonical POS days.

    Demand response comes from actual quantity sold on supported days at the
    observed price. Current cost is used so candidates are comparable under
    today's cost structure.
    """
    days=_canonical_sales_days(
        cur,
        limit=max(7,min(int(supported_day_limit),180)),
        up_to=up_to,
    )
    daily=_daily_sales_by_price_type(cur,upc_id,days)
    buckets: dict[Decimal,dict[str,Any]]={}
    for day in sorted(daily):
        x=daily[day]
        qty=_d(x.get("sold_quantity"))
        sales=_d(x.get("sales_amount"))
        if qty<=0:
            continue
        price=(sales/qty).quantize(Decimal("0.01"))
        b=buckets.setdefault(price,{
            "price":price,
            "sales_qty":Decimal("0"),
            "observed_days":0,
            "gp_dollars":Decimal("0"),
            "price_types":set(),
        })
        b["sales_qty"]+=qty
        b["observed_days"]+=1
        b["gp_dollars"]+=(price-current_cost)*qty
        b["price_types"].update(str(k).upper() for k in (x.get("price_types") or {}).keys())

    out=[]
    for price,b in buckets.items():
        n=int(b["observed_days"])
        gp_day=(b["gp_dollars"]/Decimal(n)) if n else None
        velocity=(b["sales_qty"]/Decimal(n)) if n else None
        out.append({
            "price":price,
            "observed_days":n,
            "observed_velocity_per_day":velocity,
            "gp_per_observed_day_at_current_cost":gp_day,
            "price_types":sorted(b["price_types"]),
            "meets_company_c_floor":(
                True if company_c_floor is None else price>=company_c_floor
            ),
        })
    out.sort(
        key=lambda x:(
            -float(x.get("gp_per_observed_day_at_current_cost") or Decimal("-999999")),
            -int(x.get("observed_days") or 0),
            -float(x.get("price") or 0),
        )
    )
    return out


def _observed_price_as_of(
    cur,
    upc_id: int,
    as_of_date: date,
    lookback_supported_days: int=28,
) -> dict[str,Any]:
    days=_canonical_sales_days(
        cur,
        limit=max(1,min(int(lookback_supported_days),90)),
        up_to=as_of_date,
    )
    daily=_daily_sales_by_price_type(cur,upc_id,days)
    for day in sorted(daily,reverse=True):
        x=daily[day]
        qty=_d(x.get("sold_quantity"))
        sales=_d(x.get("sales_amount"))
        if qty>0:
            return {
                "status":"READY",
                "date":day,
                "price":sales/qty,
                "price_types":sorted(str(k).upper() for k in (x.get("price_types") or {}).keys()),
                "basis":"LAST_OBSERVED_SOLD_PRICE_ON_OR_BEFORE_REPORT_DATE",
            }
    return {
        "status":"UNAVAILABLE",
        "date":None,
        "price":None,
        "price_types":[],
        "basis":"NO_OBSERVED_SOLD_PRICE_ON_OR_BEFORE_REPORT_DATE",
    }


def _gp_day_price_suggestion(
    cur,
    row: dict[str,Any],
    upc_id: int,
    *,
    as_of_date: date|None=None,
) -> dict[str,Any]:
    cost=(
        Decimal(str(row["current_cost_per_selling_unit"]))
        if row.get("current_cost_per_selling_unit") is not None else None
    )
    observed_asof=(
        _observed_price_as_of(cur,upc_id,as_of_date)
        if as_of_date is not None else None
    )
    # "Current Price" is global/current-state data, never a report-date
    # historical reconstruction. It must already be freshness-gated to today's
    # latest valid Price List vs the latest completed business-day POS sold event.
    current=(
        Decimal(str(row["current_price"]))
        if row.get("current_price") is not None else None
    )
    company_c=(
        Decimal(str(row["company_price_c"]))
        if row.get("company_price_c") is not None
        and Decimal(str(row["company_price_c"]))>0
        else None
    )
    if cost is None or current is None or current<=0:
        return {
            "status":"UNAVAILABLE",
            "reason":"CURRENT_COST_OR_PRICE_UNAVAILABLE",
            "suggested_price":None,
            "company_c_floor":company_c,
            "candidates":[],
        }

    candidates=_observed_price_gp_day_candidates(
        cur,
        upc_id,
        current_cost=cost,
        supported_day_limit=90,
        company_c_floor=company_c,
        up_to=as_of_date,
    )
    eligible=[x for x in candidates if x["meets_company_c_floor"]]
    floor_constrained=False
    basis="OBSERVED_PRICE_MAX_GP_PER_DAY"

    if eligible:
        best=eligible[0]
        suggested=best["price"]
        expected_gp_day=best["gp_per_observed_day_at_current_cost"]
        expected_velocity=best["observed_velocity_per_day"]
    elif company_c is not None:
        # No historically observed selling price satisfied the current company
        # floor. Respect the floor, but do not invent demand response.
        floor_constrained=True
        basis="COMPANY_C_FLOOR_NO_OBSERVED_DEMAND_AT_OR_ABOVE_FLOOR"
        suggested=company_c
        expected_gp_day=None
        expected_velocity=None
        best=None
    else:
        return {
            "status":"UNAVAILABLE",
            "reason":"NO_OBSERVED_PRICE_HISTORY",
            "suggested_price":None,
            "company_c_floor":None,
            "candidates":candidates,
        }

    sweet=(
        Decimal(str(row["sweet_spot_price"]))
        if row.get("sweet_spot_price") is not None else None
    )
    if company_c is not None and sweet is not None and sweet<company_c:
        floor_constrained=True

    return {
        "status":"READY",
        "suggested_price":suggested,
        "basis":basis,
        "company_c_floor":company_c,
        "company_c_applied":company_c is not None,
        "floor_constrained":floor_constrained,
        "expected_gp_per_day_from_observed_demand":expected_gp_day,
        "expected_velocity_from_observed_price_days":expected_velocity,
        "sweet_spot_price":sweet,
        "candidate_count":len(candidates),
        "top_observed_candidates":candidates[:5],
        "current_price_used":current,
        "current_price_basis":"TODAY_PRICE_LIST_VS_LATEST_COMPLETED_DAY_POS_FRESHNESS_GATE",
        "current_price_source":row.get("current_price_source"),
        "current_price_observed_date":row.get("current_price_asof_date"),
        "historical_observed_price_asof_report_date":(
            observed_asof.get("price") if observed_asof else None
        ),
        "historical_observed_price_date":(
            observed_asof.get("date") if observed_asof else None
        ),
        "cost_basis":"CURRENT_AUTHORITATIVE_COST",
        "cost_date":row.get("cost_date"),
    }


def _batch_daily_sales_by_price_type(
    cur,
    rows: list[dict[str,Any]],
    data_days: list[dict[str,Any]],
) -> dict[int,dict[date,dict[str,Any]]]:
    """Load canonical POS history for all serving UPCs in a small fixed query set.

    This is the set-based equivalent of repeatedly calling
    _daily_sales_by_price_type() per UPC.  Direct canonical upc_id lineage wins;
    raw EAN/UPC fallback is used only when it resolves unambiguously to one
    serving UPC.
    """
    if not data_days or not rows:
        return {}

    serving_ids: set[int] = set()
    exact_candidates: dict[str,set[int]] = {}
    numeric_candidates: dict[str,set[int]] = {}
    for row in rows:
        if row.get("upc_id") is None:
            continue
        uid=int(row["upc_id"])
        serving_ids.add(uid)
        ean=str(row.get("ean_upc") or "").strip()
        if ean:
            exact_candidates.setdefault(ean,set()).add(uid)
            key=_numeric_key(ean)
            if key:
                numeric_candidates.setdefault(key,set()).add(uid)

    exact_map={
        key:next(iter(ids))
        for key,ids in exact_candidates.items()
        if len(ids)==1
    }
    numeric_map={
        key:next(iter(ids))
        for key,ids in numeric_candidates.items()
        if len(ids)==1
    }
    valid_days={x["date"] for x in data_days}
    out: dict[int,dict[date,dict[str,Any]]] = {}

    def resolve_upc(raw_upc_id: Any, raw_ean: Any) -> int|None:
        if raw_upc_id is not None:
            try:
                uid=int(raw_upc_id)
            except Exception:
                uid=None
            if uid is not None and uid in serving_ids:
                return uid
        ean=str(raw_ean or "").strip()
        if ean in exact_map:
            return exact_map[ean]
        key=_numeric_key(ean)
        return numeric_map.get(key) if key else None

    def absorb(obs: dict[str,Any]) -> None:
        uid=resolve_upc(obs.get("upc_id"),obs.get("ean_upc"))
        day=obs.get("business_date")
        if uid is None or day not in valid_days:
            return
        by_day=out.setdefault(uid,{})
        bucket=by_day.setdefault(day,{
            "date":day,
            "supported":True,
            "price_types":{},
            "sales_amount":Decimal("0"),
            "sold_quantity":Decimal("0"),
        })
        pt=str(obs.get("price_type") or "UNKNOWN").upper()
        sales=_d(obs.get("sales_amount"))
        qty=_d(obs.get("sold_quantity"))
        prev=bucket["price_types"].get(pt,{
            "sales_amount":Decimal("0"),
            "sold_quantity":Decimal("0"),
            "avg_sold_price":None,
        })
        ps=_d(prev.get("sales_amount"))+sales
        pq=_d(prev.get("sold_quantity"))+qty
        bucket["price_types"][pt]={
            "sales_amount":ps,
            "sold_quantity":pq,
            "avg_sold_price":(ps/pq if pq!=0 else None),
        }
        bucket["sales_amount"]+=sales
        bucket["sold_quantity"]+=qty

    direct=[x for x in data_days if x.get("coverage_kind")!="DERIVED_PERIOD_RESIDUAL"]
    if direct:
        clauses=[]
        args=[]
        for x in direct:
            clauses.append("(file_id=%s AND period_start_date=%s AND period_end_date=%s)")
            args.extend([int(x["file_id"]),x["date"],x["date"]])
        cur.execute(
            f"""SELECT period_end_date AS business_date,upc_id,ean_upc,
                       UPPER(TRIM(price_type)) AS price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                GROUP BY period_end_date,upc_id,ean_upc,UPPER(TRIM(price_type))""",
            tuple(args),
        )
        for obs in cur.fetchall():
            absorb(obs)

    derived=[x for x in data_days if x.get("coverage_kind")=="DERIVED_PERIOD_RESIDUAL"]
    if derived:
        clauses=[]
        args=[]
        for x in derived:
            clauses.append("(source_file_id=%s AND business_date=%s)")
            args.extend([int(x["file_id"]),x["date"]])
        cur.execute(
            f"""SELECT business_date,upc_id,ean_upc,
                       UPPER(TRIM(price_type)) AS price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM pos_daily_backfill_observation
                WHERE {' OR '.join(clauses)}
                GROUP BY business_date,upc_id,ean_upc,UPPER(TRIM(price_type))""",
            tuple(args),
        )
        for obs in cur.fetchall():
            absorb(obs)

    return out


def _batch_sales_metric(
    daily_by_upc: dict[int,dict[date,dict[str,Any]]],
    data_days: list[dict[str,Any]],
    upc_id: int,
    supported_day_count: int,
) -> dict[str,Any]:
    days=sorted(data_days,key=lambda x:x["date"],reverse=True)[:supported_day_count]
    by_day=daily_by_upc.get(int(upc_id),{})
    qty=sum((_d(by_day.get(x["date"],{}).get("sold_quantity")) for x in days),Decimal("0"))
    sales=sum((_d(by_day.get(x["date"],{}).get("sales_amount")) for x in days),Decimal("0"))
    n=len(days)
    return {
        "requested_supported_days":supported_day_count,
        "supported_day_count":n,
        "coverage_status":"COMPLETE" if n>=supported_day_count else "PARTIAL",
        "start_date":min((x["date"] for x in days),default=None),
        "end_date":max((x["date"] for x in days),default=None),
        "sold_quantity":qty,
        "sales_amount":sales,
        "velocity_per_supported_day":(qty/Decimal(n) if n else None),
        "data_day_definition":"LATEST_COMPLETED_CANONICAL_SALES_DATA_DAYS",
    }


def _batch_observed_price_as_of(
    daily_by_upc: dict[int,dict[date,dict[str,Any]]],
    data_days: list[dict[str,Any]],
    upc_id: int,
    lookback_supported_days: int=28,
) -> dict[str,Any]:
    days=sorted(data_days,key=lambda x:x["date"],reverse=True)[:lookback_supported_days]
    by_day=daily_by_upc.get(int(upc_id),{})
    for entry in days:
        day=entry["date"]
        x=by_day.get(day,{})
        qty=_d(x.get("sold_quantity"))
        sales=_d(x.get("sales_amount"))
        if qty>0:
            return {
                "status":"READY",
                "date":day,
                "price":sales/qty,
                "price_types":sorted(str(k).upper() for k in (x.get("price_types") or {}).keys()),
                "basis":"LAST_OBSERVED_SOLD_PRICE_ON_OR_BEFORE_REPORT_DATE",
            }
    return {
        "status":"UNAVAILABLE",
        "date":None,
        "price":None,
        "price_types":[],
        "basis":"NO_OBSERVED_SOLD_PRICE_ON_OR_BEFORE_REPORT_DATE",
    }


def _batch_observed_price_gp_day_candidates(
    daily_by_upc: dict[int,dict[date,dict[str,Any]]],
    data_days: list[dict[str,Any]],
    upc_id: int,
    *,
    current_cost: Decimal,
    supported_day_limit: int=90,
    company_c_floor: Decimal|None=None,
) -> list[dict[str,Any]]:
    days=sorted(data_days,key=lambda x:x["date"],reverse=True)[:max(7,min(int(supported_day_limit),180))]
    by_day=daily_by_upc.get(int(upc_id),{})
    buckets: dict[Decimal,dict[str,Any]]={}
    for entry in sorted(days,key=lambda x:x["date"]):
        x=by_day.get(entry["date"],{})
        qty=_d(x.get("sold_quantity"))
        sales=_d(x.get("sales_amount"))
        if qty<=0:
            continue
        price=(sales/qty).quantize(Decimal("0.01"))
        b=buckets.setdefault(price,{
            "price":price,
            "sales_qty":Decimal("0"),
            "observed_days":0,
            "gp_dollars":Decimal("0"),
            "price_types":set(),
        })
        b["sales_qty"]+=qty
        b["observed_days"]+=1
        b["gp_dollars"]+=(price-current_cost)*qty
        b["price_types"].update(str(k).upper() for k in (x.get("price_types") or {}).keys())

    out=[]
    for price,b in buckets.items():
        n=int(b["observed_days"])
        gp_day=(b["gp_dollars"]/Decimal(n)) if n else None
        velocity=(b["sales_qty"]/Decimal(n)) if n else None
        out.append({
            "price":price,
            "observed_days":n,
            "observed_velocity_per_day":velocity,
            "gp_per_observed_day_at_current_cost":gp_day,
            "price_types":sorted(b["price_types"]),
            "meets_company_c_floor":(
                True if company_c_floor is None else price>=company_c_floor
            ),
        })
    out.sort(
        key=lambda x:(
            -float(x.get("gp_per_observed_day_at_current_cost") or Decimal("-999999")),
            -int(x.get("observed_days") or 0),
            -float(x.get("price") or 0),
        )
    )
    return out


def _gp_day_price_suggestion_from_batch(
    row: dict[str,Any],
    upc_id: int,
    daily_by_upc: dict[int,dict[date,dict[str,Any]]],
    data_days: list[dict[str,Any]],
) -> dict[str,Any]:
    """Price candidate using 14 completed sales days, OH risk and freshness.

    Qualified UPCs are evaluated on current authoritative price/cost plus recent
    historical sales response. Company A/B/C constrains the candidate range but
    does not by itself exclude an otherwise qualified UPC.

    Fresh DOH > 7 and Frozen DOH > 60 are required freshness gates.
    For Live/other stocked UPCs, no additional DOH gate is applied.
    For every qualified UPC, the candidate objective remains maximum observed
    GP$/day from recent selling history. Company A/B/C, when present, is a
    hard candidate range; without Company price references, the best supported
    price is suggested directly.
    """
    cost=(
        Decimal(str(row["current_cost_per_selling_unit"]))
        if row.get("current_cost_per_selling_unit") is not None else None
    )
    current=(
        Decimal(str(row["current_price"]))
        if row.get("current_price") is not None else None
    )
    sweet=(
        Decimal(str(row["sweet_spot_price"]))
        if row.get("sweet_spot_price") is not None
        and Decimal(str(row["sweet_spot_price"]))>0
        else None
    )
    refs={}
    for label,key in (("A","company_price_a"),("B","company_price_b"),("C","company_price_c")):
        raw=row.get(key)
        if raw is not None and Decimal(str(raw))>0:
            refs[label]=Decimal(str(raw))

    company_low=min(refs.values()) if refs else None
    company_high=max(refs.values()) if refs else None
    pclass=str(row.get("product_class") or "").upper()
    doh=(Decimal(str(row["doh"])) if row.get("doh") is not None else None)
    clearance_reason=None
    if pclass=="FRESH" and doh is not None and doh>Decimal("7"):
        clearance_reason="FRESH_DOH_GT_7"
    elif pclass=="FROZEN" and doh is not None and doh>Decimal("60"):
        clearance_reason="FROZEN_DOH_GT_60"
    clearance=clearance_reason is not None

    observed_asof=_batch_observed_price_as_of(
        daily_by_upc,data_days,upc_id,lookback_supported_days=14
    )
    candidates=(
        _batch_observed_price_gp_day_candidates(
            daily_by_upc,data_days,upc_id,
            current_cost=cost,supported_day_limit=14,company_c_floor=None,
        )
        if cost is not None else []
    )

    base={
        "company_prices":refs,
        "company_range_low":company_low,
        "company_range_high":company_high,
        "has_company_reference":bool(refs),
        "historical_window_supported_days":14,
        "sweet_spot_price":sweet,
        "current_price_used":current,
        "current_price_basis":"TODAY_PRICE_LIST_VS_LATEST_COMPLETED_DAY_POS_FRESHNESS_GATE",
        "current_price_source":row.get("current_price_source"),
        "current_price_observed_date":row.get("current_price_asof_date"),
        "historical_observed_price_asof_report_date":observed_asof.get("price"),
        "historical_observed_price_date":observed_asof.get("date"),
        "cost_basis":"CURRENT_AUTHORITATIVE_COST",
        "cost_date":row.get("cost_date"),
        "doh":doh,
        "clearance_due_to_doh":clearance,
        "clearance_reason":clearance_reason,
        "candidate_count":len(candidates),
        "top_observed_candidates":candidates[:5],
    }

    if current is None or current<=0:
        return {**base,"status":"UNAVAILABLE","reason":"CURRENT_PRICE_UNAVAILABLE","suggested_price":None}
    if cost is None:
        return {**base,"status":"UNAVAILABLE","reason":"CURRENT_COST_UNAVAILABLE","suggested_price":None}

    def clamp_company(v: Decimal) -> Decimal:
        if not refs:
            return v
        return max(company_low,min(company_high,v))

    pool=[
        x for x in candidates
        if (not refs or company_low<=_d(x.get("price"))<=company_high)
    ]

    # DOH/freshness changes urgency, not the optimization objective.
    # The supported candidate is always the price with maximum observed GP$/day.
    if pool:
        best=pool[0]
        suggested=_d(best["price"])
        basis=("COMPANY_RANGE_14D_MAX_GP_PER_DAY" if refs else "14D_MAX_GP_PER_DAY")
        selection=("14D_OBSERVED_IN_COMPANY_RANGE" if refs else "14D_OBSERVED_MAX_GP_PER_DAY")
        expected_gp=best.get("gp_per_observed_day_at_current_cost")
        expected_vel=best.get("observed_velocity_per_day")
    elif candidates and refs:
        best=candidates[0]
        suggested=clamp_company(_d(best["price"]))
        basis="COMPANY_RANGE_CLAMPED_14D_MAX_GP_PER_DAY"
        selection="14D_MAX_GP_PER_DAY_CLAMPED_TO_COMPANY_RANGE"
        expected_gp=None
        expected_vel=None
    elif sweet is not None:
        suggested=clamp_company(sweet)
        basis=("COMPANY_RANGE_CLAMPED_HISTORICAL_SWEET_SPOT" if refs else "HISTORICAL_SWEET_SPOT")
        selection="HISTORICAL_SWEET_SPOT"
        expected_gp=None
        expected_vel=None
    else:
        return {
            **base,"status":"UNAVAILABLE",
            "reason":"NO_14D_PRICE_HISTORY_OR_SWEET_SPOT",
            "suggested_price":None,
        }

    return {
        **base,
        "status":"READY",
        "suggested_price":suggested,
        "basis":basis,
        "selection_basis":selection,
        "expected_gp_per_day_from_observed_demand":expected_gp,
        "expected_velocity_from_observed_price_days":expected_vel,
    }

def performance_supported_dates(limit: int=180) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        days=_canonical_sales_days(
            cur,
            limit=max(1,min(int(limit or 180),365)),
        )
        cur.close()
    ordered=sorted(days,key=lambda x:x["date"],reverse=True)
    return {
        "count":len(ordered),
        "dates":[
            {
                "date":x["date"],
                "weekday":WEEKDAY_NAMES[x["date"].weekday()],
                "source_file_id":x.get("file_id"),
                "coverage_kind":x.get("coverage_kind"),
            }
            for x in ordered
        ],
        "data_day_definition":"COMPLETED_CANONICAL_SALES_DATA_DAY",
    }


def _canonical_report_date_sales(
    cur,
    day_entry: dict[str,Any],
) -> dict[str,Any]:
    """Direct canonical Seafood POS total for one supported report date."""
    day=day_entry["date"]
    file_id=int(day_entry["file_id"])
    coverage=str(day_entry.get("coverage_kind") or "")
    if coverage!="DERIVED_PERIOD_RESIDUAL":
        cur.execute(
            """SELECT COALESCE(SUM(sales_amount),0) AS sales_amount,
                      COALESCE(SUM(sold_quantity),0) AS sold_quantity,
                      COUNT(DISTINCT ean_upc) AS source_upc_count,
                      COUNT(*) AS source_price_rows
               FROM sales_period_observation
               WHERE file_id=%s
                 AND period_start_date=%s
                 AND period_end_date=%s
                 AND temporal_grain='SINGLE_DATE'""",
            (file_id,day,day),
        )
        row=cur.fetchone() or {}
        basis="DIRECT_SINGLE_DATE_CANONICAL_POS"
    else:
        cur.execute(
            """SELECT COALESCE(SUM(sales_amount),0) AS sales_amount,
                      COALESCE(SUM(sold_quantity),0) AS sold_quantity,
                      COUNT(DISTINCT ean_upc) AS source_upc_count,
                      COUNT(*) AS source_price_rows
               FROM pos_daily_backfill_observation
               WHERE source_file_id=%s
                 AND business_date=%s""",
            (file_id,day),
        )
        row=cur.fetchone() or {}
        basis="DERIVED_PERIOD_RESIDUAL_CANONICAL_POS"
    return {
        "date":day,
        "source_file_id":file_id,
        "coverage_kind":coverage,
        "basis":basis,
        "sales_amount":_d(row.get("sales_amount")),
        "sold_quantity":_d(row.get("sold_quantity")),
        "source_upc_count":int(row.get("source_upc_count") or 0),
        "source_price_rows":int(row.get("source_price_rows") or 0),
    }


def _canonical_report_date_mapping_breakdown(
    cur,
    day_entry: dict[str,Any],
    mapped_upc_ids: set[int],
) -> dict[str,Any]:
    """Explain canonical POS vs current V2 serving-map differences."""
    day=day_entry["date"]
    file_id=int(day_entry["file_id"])
    coverage=str(day_entry.get("coverage_kind") or "")

    if coverage!="DERIVED_PERIOD_RESIDUAL":
        cur.execute(
            """SELECT ean_upc,upc_id,MAX(description) AS description,
                      COALESCE(SUM(sales_amount),0) AS sales_amount,
                      COALESCE(SUM(sold_quantity),0) AS sold_quantity
               FROM sales_period_observation
               WHERE file_id=%s
                 AND period_start_date=%s
                 AND period_end_date=%s
                 AND temporal_grain='SINGLE_DATE'
               GROUP BY ean_upc,upc_id
               ORDER BY sales_amount DESC""",
            (file_id,day,day),
        )
    else:
        cur.execute(
            """SELECT ean_upc,upc_id,NULL AS description,
                      COALESCE(SUM(sales_amount),0) AS sales_amount,
                      COALESCE(SUM(sold_quantity),0) AS sold_quantity
               FROM pos_daily_backfill_observation
               WHERE source_file_id=%s
                 AND business_date=%s
               GROUP BY ean_upc,upc_id
               ORDER BY sales_amount DESC""",
            (file_id,day),
        )

    source_rows=[]
    mapped_sales=Decimal("0")
    mapped_qty=Decimal("0")
    unmapped_sales=Decimal("0")
    unmapped_qty=Decimal("0")
    unmapped=[]

    for r in cur.fetchall():
        upc_id=int(r["upc_id"]) if r.get("upc_id") is not None else None
        sales=_d(r.get("sales_amount"))
        qty=_d(r.get("sold_quantity"))
        is_mapped=bool(upc_id is not None and upc_id in mapped_upc_ids)
        row={
            "ean_upc":r.get("ean_upc"),
            "upc_id":upc_id,
            "description":r.get("description"),
            "sales_amount":sales,
            "sold_quantity":qty,
            "qty_uom":_safe_qty_uom(r.get("ean_upc"),None),
            "mapping_status":"MAPPED_TO_CURRENT_V2" if is_mapped else (
                "SOURCE_UPC_ID_UNRESOLVED" if upc_id is None
                else "NOT_IN_CURRENT_QUICK_CHECK_SERVING"
            ),
        }
        source_rows.append(row)
        if is_mapped:
            mapped_sales+=sales
            mapped_qty+=qty
        else:
            unmapped_sales+=sales
            unmapped_qty+=qty
            unmapped.append(row)

    unmapped.sort(
        key=lambda x:(
            -float(x.get("sales_amount") or 0),
            -float(x.get("sold_quantity") or 0),
            str(x.get("ean_upc") or ""),
        )
    )
    unmapped_uoms={
        str(x.get("qty_uom") or "").upper()
        for x in unmapped
        if x.get("qty_uom")
    }
    safe_unmapped_qty=unmapped_qty if len(unmapped_uoms)==1 and len(unmapped)==sum(1 for x in unmapped if x.get("qty_uom")) else None
    safe_unmapped_uom=next(iter(unmapped_uoms)) if safe_unmapped_qty is not None else None
    return {
        "source_row_count":len(source_rows),
        "mapped_source_sales":mapped_sales,
        "mapped_source_qty":mapped_qty,
        "unmapped_source_sales":unmapped_sales,
        "unmapped_source_qty":safe_unmapped_qty,
        "unmapped_source_qty_uom":safe_unmapped_uom,
        "unmapped_qty_mixed_or_unknown":safe_unmapped_qty is None and bool(unmapped),
        "unmapped_upc_count":len(unmapped),
        "top_unmapped_upcs":unmapped[:25],
        "explanation":"UNMAPPED = canonical POS row not represented by the current V2 Quick Check serving set.",
    }


def latest_performance_date() -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        days=_canonical_sales_days(cur,limit=1)
        cur.close()
    latest=max((x["date"] for x in days),default=None)
    return {
        "latest_completed_supported_sales_date":latest,
        "weekday":WEEKDAY_NAMES[latest.weekday()] if latest is not None else None,
        "data_day_definition":"COMPLETED_CANONICAL_SALES_DATA_DAY",
    }


def _performance_narrative(
    *,
    anchor: date,
    summary: dict[str,Any],
    report_vs_7: Decimal|None,
    report_vs_14: Decimal|None,
) -> dict[str,Any]:
    def money_text(v: Any) -> str:
        try:
            return f"${Decimal(str(v or 0)):,.2f}"
        except Exception:
            return "$0.00"

    def pct_text(v: Decimal|None, label: str) -> str:
        if v is None:
            return f"{label} comparison is unavailable"
        direction="above" if v>=0 else "below"
        return f"{abs(v)*Decimal('100'):.1f}% {direction} the {label} average"

    text=(
        f"Performance for {anchor.isoformat()} closed at "
        f"{money_text(summary.get('report_date_sales_dollars'))}. "
        "This report uses completed canonical sales days only, so intraday or unresolved uploads are excluded from the comparison. "
        f"Daily sales were {pct_text(report_vs_7,'7-day')} and {pct_text(report_vs_14,'14-day')}. "
        f"Sales totalled {money_text(summary.get('sales_dollars_7d'))} across the latest 7 completed data days, "
        f"{money_text(summary.get('sales_dollars_14d'))} across 14 days, and "
        f"{money_text(summary.get('sales_dollars_28d'))} across 28 days. "
        f"There were {int(summary.get('active_upcs_28d') or 0)} active UPCs with movement in the 28-day window, "
        f"and {int(summary.get('upcs_sold_report_date') or 0)} UPCs recorded sales on the report date. "
        f"{int(summary.get('slowing_items') or 0)} items have 7-day velocity below 80% of their 28-day rate, which identifies products where recent demand has softened. "
        f"{int(summary.get('low_gp_items') or 0)} items are below their current category GP reference. "
        f"{int(summary.get('price_review_candidates') or 0)} items currently qualify for price review under the Company-range, 14-day GP$/day, or freshness-clearance rules; "
        "pricing actions are intentionally separated from this performance report. "
        f"Data quality also matters: {int(summary.get('ready_upcs') or 0)} UPCs are READY and "
        f"{int(summary.get('qa_hold_upcs') or 0)} are on QA HOLD. "
        "The Top Sellers section ranks the 20 highest sales-dollar UPCs for the selected date and shows sales dollars, quantity, and average sold price. "
        "Use this report to assess demand, sales concentration, item health, and data readiness; use the Price Change page for pricing actions. "
        "All comparisons are descriptive and anchored to the selected report date."
    )
    return {
        "text":text,
        "word_count":len(text.split()),
        "target_words":200,
    }

def _performance_range_cost_rows(
    cur,
    rows: list[dict[str,Any]],
    end_date: date,
) -> dict[int,list[dict[str,Any]]]:
    """Load historical family cost observations once for range GP analysis."""
    family_ids=sorted({
        int(x["family_id"])
        for x in rows
        if x.get("family_id") is not None
    })
    if not family_ids:
        return {}
    ph=",".join(["%s"]*len(family_ids))
    sources=(
        "MOVEMENT_RECEIPT_VALUATION",
        "ON_HAND_EXPLICIT_COST_FALLBACK",
        "FROZEN_INVENTORY_OFFICIAL_COST",
        "LIVE_FRESH_SUGGESTION_OFFICIAL_COST",
        "USER_CONFIRMED_FAMILY_COST",
    )
    sph=",".join(["%s"]*len(sources))
    cur.execute(
        f"""SELECT co.family_id,co.business_date,co.source_type,
                   COALESCE(co.cost_per_base_uom,co.cost_amount) AS cost_value,
                   COALESCE(bu.uom_code,cu.uom_code) AS cost_uom,
                   co.cost_observation_id
            FROM article_cost_observation co
            LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
            LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
            WHERE co.family_id IN ({ph})
              AND co.business_date<=%s
              AND co.source_type IN ({sph})
              AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
              AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
            ORDER BY co.family_id,co.business_date DESC,co.cost_observation_id DESC""",
        (*family_ids,end_date,*sources),
    )
    out: dict[int,list[dict[str,Any]]]={}
    for x in cur.fetchall():
        out.setdefault(int(x["family_id"]),[]).append(x)
    return out


def _performance_cost_for_day(
    row: dict[str,Any],
    observations: dict[int,list[dict[str,Any]]],
    day: date,
) -> dict[str,Any]|None:
    fid=row.get("family_id")
    if fid is None:
        return None
    selling=str(row.get("selling_uom") or "").strip().upper()
    base=str(row.get("base_uom") or "").strip().upper()
    factor=(
        Decimal(str(row["base_qty_per_selling_unit"]))
        if row.get("base_qty_per_selling_unit") is not None else None
    )
    precedence=(
        {"MOVEMENT_RECEIPT_VALUATION"},
        {"ON_HAND_EXPLICIT_COST_FALLBACK"},
        {"FROZEN_INVENTORY_OFFICIAL_COST","LIVE_FRESH_SUGGESTION_OFFICIAL_COST"},
        {"USER_CONFIRMED_FAMILY_COST"},
    )
    obs=observations.get(int(fid),[])
    for group in precedence:
        for x in obs:
            if x.get("source_type") not in group:
                continue
            if x.get("business_date") is None or x["business_date"]>day:
                continue
            cost=_d(x.get("cost_value"))
            cuom=str(x.get("cost_uom") or "").strip().upper()
            if selling and cuom==selling:
                sell_cost=cost
            elif base and cuom==base and factor is not None and factor>0:
                sell_cost=cost*factor
            elif base and selling and base==selling and cuom==base:
                sell_cost=cost
            else:
                continue
            return {
                "cost_per_selling_unit":sell_cost,
                "cost_date":x.get("business_date"),
                "cost_source":x.get("source_type"),
                "cost_uom":selling or cuom or None,
            }
    return None


def performance_range(
    start_date: date|None=None,
    end_date: date|None=None,
    limit: int=1000,
) -> dict[str,Any]:
    """Aggregate Seafood performance over a user-selected canonical date range.

    The range contains only completed canonical POS data days. Missing calendar
    dates are ignored, not converted to zero. UPC velocity is quantity divided by
    selected supported data days. GP$ uses the applicable historical cost as of
    each selling day and is withheld when a sold day has no resolvable cost.
    """
    limit=max(1,min(int(limit or 1000),2000))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        all_days=_canonical_sales_days(cur,limit=365,up_to=end_date)
        ordered=sorted(all_days,key=lambda x:x["date"])
        if not ordered:
            cur.close()
            raise ValueError("NO_COMPLETED_SUPPORTED_SALES_DATE")

        supported={x["date"] for x in ordered}
        resolved_end=end_date or ordered[-1]["date"]
        if resolved_end not in supported:
            cur.close()
            raise ValueError("END_DATE_NOT_SUPPORTED")
        eligible=[x for x in ordered if x["date"]<=resolved_end]
        if start_date is None:
            default_days=eligible[-7:]
            resolved_start=default_days[0]["date"]
        else:
            resolved_start=start_date
        if resolved_start not in supported:
            cur.close()
            raise ValueError("START_DATE_NOT_SUPPORTED")
        if resolved_start>resolved_end:
            cur.close()
            raise ValueError("START_DATE_AFTER_END_DATE")

        selected=[x for x in ordered if resolved_start<=x["date"]<=resolved_end]
        if not selected:
            cur.close()
            raise ValueError("NO_SUPPORTED_DATES_IN_RANGE")

        cur.execute("SELECT * FROM quick_check_current")
        rows=cur.fetchall()
        daily=_batch_daily_sales_by_price_type(cur,rows,selected)
        cost_obs=_performance_range_cost_rows(cur,rows,resolved_end)

        items=[]
        total_sales=Decimal("0")
        total_gp=Decimal("0")
        total_gp_complete=True
        sold_item_count=0
        ready_count=0
        qa_hold_count=0
        n_days=len(selected)

        for row in rows:
            uid=int(row["upc_id"])
            by_day=daily.get(uid,{})
            sales=Decimal("0")
            qty=Decimal("0")
            gp=Decimal("0")
            missing_cost_days=[]
            sold_days=0
            price_types=set()

            for entry in selected:
                day=entry["date"]
                obs=by_day.get(day,{})
                day_sales=_d(obs.get("sales_amount"))
                day_qty=_d(obs.get("sold_quantity"))
                sales+=day_sales
                qty+=day_qty
                price_types.update(str(k).upper() for k in (obs.get("price_types") or {}).keys())
                if day_qty<=0:
                    continue
                sold_days+=1
                cost=_performance_cost_for_day(row,cost_obs,day)
                if cost is None:
                    missing_cost_days.append(day)
                    continue
                gp+=day_sales-(day_qty*_d(cost.get("cost_per_selling_unit")))

            if qty<=0:
                continue

            sold_item_count+=1
            status=str(row.get("quick_check_status") or "")
            if status=="READY":
                ready_count+=1
            elif status=="QA_HOLD":
                qa_hold_count+=1

            gp_complete=not missing_cost_days
            gp_value=gp if gp_complete else None
            gp_pct=(gp/sales if gp_complete and sales>0 else None)
            gp_per_day=(gp/Decimal(n_days) if gp_complete and n_days else None)
            total_sales+=sales
            if gp_complete:
                total_gp+=gp
            else:
                total_gp_complete=False

            items.append({
                "upc":row.get("ean_upc"),
                "name":row.get("selling_description"),
                "family_article_number":row.get("main_article_number"),
                "family_name":row.get("family_description"),
                "category":str(row.get("product_class") or "").upper(),
                "readiness":status,
                "selling_uom":row.get("selling_uom"),
                "qty_uom":_safe_qty_uom(row.get("ean_upc"),row.get("selling_uom")),
                "sales_amount":sales,
                "sold_quantity":qty,
                "velocity":qty/Decimal(n_days),
                "avg_sold_price":sales/qty if qty else None,
                "gp_dollars":gp_value,
                "gp_pct":gp_pct,
                "gp_per_supported_day":gp_per_day,
                "gp_cost_complete":gp_complete,
                "gp_missing_cost_days":missing_cost_days,
                "sold_supported_day_count":sold_days,
                "supported_day_count":n_days,
                "price_types":sorted(price_types),
            })

        items.sort(
            key=lambda x:(
                -(float(x.get("gp_dollars")) if x.get("gp_dollars") is not None else float("-inf")),
                -float(x.get("sales_amount") or 0),
                str(x.get("name") or ""),
            )
        )
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_PERFORMANCE_RANGE_V1",
        "start_date":resolved_start,
        "end_date":resolved_end,
        "supported_day_count":len(selected),
        "supported_dates":[x["date"] for x in selected],
        "supported_day_contract":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
        "missing_calendar_dates_are_zero":False,
        "summary":{
            "sales_dollars":total_sales,
            "gp_dollars":total_gp if total_gp_complete else None,
            "gp_dollars_complete":total_gp_complete,
            "sold_item_count":sold_item_count,
            "ready_item_count":ready_count,
            "qa_hold_item_count":qa_hold_count,
        },
        "items":items[:limit],
        "item_limit":limit,
        "gp_basis":"HISTORICAL_APPLICABLE_COST_AS_OF_EACH_SUPPORTED_SELLING_DAY",
        "gp_missing_cost_rule":"ITEM_GP_WITHHELD_IF_ANY_SOLD_SUPPORTED_DAY_HAS_NO_RESOLVABLE_COST",
    }


def performance_report(
    category: str="ALL",
    limit: int=100,
    report_date: date|None=None,
) -> dict[str,Any]:
    """Date-anchored performance analysis and urgent price suggestions.

    Sales evidence is strictly limited to completed canonical supported dates on
    or before report_date. Price suggestions are generated from sales response
    through report_date. Current authoritative cost and current Company C are
    used because historical daily cost/company-price lineage is not published
    in the V2 serving layer.
    """
    cat=str(category or "ALL").strip().upper()
    if cat not in {"ALL","LIVE","FRESH","FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")
    limit=max(1,min(int(limit or 100),1000))

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)

        latest_days=_canonical_sales_days(cur,limit=1,up_to=report_date)
        if not latest_days:
            cur.close()
            raise ValueError("NO_COMPLETED_SUPPORTED_SALES_DATE")
        anchor=max(x["date"] for x in latest_days)
        if report_date is not None and anchor!=report_date:
            cur.close()
            raise ValueError("REPORT_DATE_NOT_SUPPORTED")

        if cat=="ALL":
            # ALL means the complete Seafood serving scope, including QA/OTHER
            # classifications.  LIVE/FRESH/FROZEN are filters, not the definition
            # of department total.
            cur.execute("""SELECT * FROM quick_check_current""")
        else:
            cur.execute(
                """SELECT * FROM quick_check_current
                   WHERE UPPER(COALESCE(product_class,''))=%s""",
                (cat,),
            )
        rows=cur.fetchall()

        # Price Change and Daily Performance share this endpoint.  Load the
        # complete 90 supported-day sales window once, then reuse it for every
        # UPC.  This removes the prior per-UPC N+1 query pattern that could
        # exceed the gateway timeout on category=ALL.
        history_days=_canonical_sales_days(cur,limit=90,up_to=anchor)
        daily_history=_batch_daily_sales_by_price_type(cur,rows,history_days)

        # 240 main UPC and 249 cook/service UPC must always carry the same
        # current retail price when both forms exist in the same confirmed
        # Family/product group.  Resolve those pairs up front so mismatches can
        # bypass normal freshness/DOH qualification and surface as the highest
        # pricing-review priority.
        price_pair_meta: dict[str,dict[str,Any]] = {}
        pair_mismatch_suggestions: list[dict[str,Any]] = []
        pair_mismatch_service_upcs: set[str] = set()
        pair_groups: dict[tuple[int,str],dict[str,dict[str,Any]]] = {}
        for pair_row in rows:
            sig=_seafood_upc_group_signature(pair_row.get("family_id"),pair_row.get("ean_upc"))
            if sig is None:
                continue
            prefix=_numeric_key(pair_row.get("ean_upc"))[:3]
            if prefix not in {"240","249"}:
                continue
            pair_groups.setdefault(sig,{})[prefix]=pair_row

        for sig,members in pair_groups.items():
            main=members.get("240")
            service=members.get("249")
            if not main or not service:
                continue

            _overlay_live_current_price(cur,main)
            _overlay_live_current_price(cur,service)
            main_upc=str(main.get("ean_upc") or "")
            service_upc=str(service.get("ean_upc") or "")
            main_price=(
                _d(main.get("current_price"))
                if main.get("current_price") is not None else None
            )
            service_price=(
                _d(service.get("current_price"))
                if service.get("current_price") is not None else None
            )
            equal=(
                main_price is not None
                and service_price is not None
                and main_price==service_price
            )
            meta={
                "related_240_upc":main_upc,
                "related_240_name":main.get("selling_description"),
                "related_240_current_price":main_price,
                "related_240_current_price_type":main.get("current_price_type"),
                "related_240_current_price_source":main.get("current_price_source"),
                "related_240_current_price_asof_date":main.get("current_price_asof_date"),
                "related_249_present":True,
                "related_249_upc":service_upc,
                "related_249_name":service.get("selling_description"),
                "related_249_current_price":service_price,
                "related_249_current_price_type":service.get("current_price_type"),
                "related_249_current_price_source":service.get("current_price_source"),
                "related_249_current_price_asof_date":service.get("current_price_asof_date"),
                "price_240_249_equal":equal,
            }
            price_pair_meta[main_upc]=dict(meta)
            price_pair_meta[service_upc]=dict(meta)

            if (
                main_price is None
                or main_price<=0
                or service_price is None
                or service_price<=0
                or equal
            ):
                continue

            pair_mismatch_service_upcs.add(service_upc)
            m7_pair=_batch_sales_metric(daily_history,history_days,int(service["upc_id"]),7)
            m14_pair=_batch_sales_metric(daily_history,history_days,int(service["upc_id"]),14)
            m28_pair=_batch_sales_metric(daily_history,history_days,int(service["upc_id"]),28)
            v7_pair=m7_pair.get("velocity_per_supported_day")
            service_cost=(
                _d(service.get("current_cost_per_selling_unit"))
                if service.get("current_cost_per_selling_unit") is not None else None
            )
            current_gp=(
                (service_price-service_cost)/service_price
                if service_cost is not None and service_price>0 else None
            )
            target_gp=(
                (main_price-service_cost)/main_price
                if service_cost is not None and main_price>0 else None
            )
            current_gp_day=(
                (service_price-service_cost)*_d(v7_pair)
                if service_cost is not None and v7_pair is not None else None
            )
            target_gp_day=(
                (main_price-service_cost)*_d(v7_pair)
                if service_cost is not None and v7_pair is not None else None
            )
            ready=(
                str(main.get("quick_check_status") or "").upper()=="READY"
                and str(service.get("quick_check_status") or "").upper()=="READY"
            )
            pair_mismatch_suggestions.append({
                "urgency_score":Decimal("9999.00"),
                "priority_240_249_mismatch":True,
                "review_status":"ACTIONABLE" if ready else "QA_HOLD",
                "review_blocker":None if ready else "240_249_PAIR_NOT_READY",
                "actionable":ready,
                "report_date":anchor,
                "upc":service_upc,
                "name":service.get("selling_description"),
                "family_article_number":service.get("main_article_number"),
                "family_name":service.get("family_description"),
                "category":str(service.get("product_class") or main.get("product_class") or "").upper(),
                "readiness":service.get("quick_check_status"),
                "selling_uom":service.get("selling_uom"),
                "upc_role":_upc_role(service),
                "current_price":service_price,
                "current_price_type":service.get("current_price_type"),
                "current_price_basis":"LIVE_CANONICAL_249_PRICE",
                "current_price_source":service.get("current_price_source"),
                "current_price_observed_date":service.get("current_price_asof_date"),
                "suggested_price":main_price if ready else None,
                "candidate_price":main_price,
                "suggestion_basis":"MANDATORY_240_EQUALS_249",
                "selection_basis":"COPY_CURRENT_240_MAIN_PRICE_TO_249_SERVICE_PRICE",
                "historical_window_supported_days":14,
                "company_price_a":None,
                "company_price_b":None,
                "company_price_c":None,
                "company_range_low":None,
                "company_range_high":None,
                "has_company_reference":False,
                "current_within_company_range":None,
                "clearance_due_to_doh":False,
                "clearance_reason":None,
                "doh":service.get("doh"),
                "current_oh":service.get("current_oh"),
                "current_oh_uom":service.get("current_oh_uom"),
                "pricing_rule_priority":-1,
                "primary_reason_text":f"URGENT: 249 service price must equal 240 main price ({main_price})",
                "direction":"INCREASE" if main_price>service_price else "DECREASE",
                "price_gap_pct":abs(main_price-service_price)/service_price,
                "current_gp_pct_reference":current_gp,
                "suggested_gp_pct_at_current_cost":target_gp,
                "current_gp_per_day_7d":current_gp_day,
                "expected_gp_per_day_observed_price_demand":target_gp_day if ready else None,
                "candidate_expected_gp_per_day":target_gp_day,
                "gp_per_day_opportunity":(
                    target_gp_day-current_gp_day
                    if target_gp_day is not None
                    and current_gp_day is not None
                    and target_gp_day>current_gp_day
                    else None
                ),
                "gp_per_day_opportunity_pct":None,
                "observed_velocity_at_suggested_price":v7_pair,
                "qty_report_date":Decimal("0"),
                "sales_report_date":Decimal("0"),
                "qty_uom":_safe_qty_uom(service_upc,service.get("selling_uom")),
                "qty_7d":m7_pair.get("sold_quantity"),
                "qty_14d":m14_pair.get("sold_quantity"),
                "qty_28d":m28_pair.get("sold_quantity"),
                "velocity_7d":v7_pair,
                "velocity_14d":m14_pair.get("velocity_per_supported_day"),
                "velocity_28d":m28_pair.get("velocity_per_supported_day"),
                "velocity_7d_vs_28d_ratio":None,
                "cost_basis":"CURRENT_AUTHORITATIVE_COST",
                "cost_date":service.get("cost_date"),
                "reasons":["URGENT_240_249_PRICE_MISMATCH","MANDATORY_PRICE_EQUALITY"],
                **meta,
            })

        anchor_day_entry=[x for x in latest_days if x["date"]==anchor]
        canonical_day_sales=(
            _canonical_report_date_sales(cur,anchor_day_entry[0])
            if anchor_day_entry else None
        )
        current_serving_upc_ids={
            int(x["upc_id"])
            for x in rows
            if x.get("upc_id") is not None
        }
        mapping_breakdown=(
            _canonical_report_date_mapping_breakdown(
                cur,
                anchor_day_entry[0],
                current_serving_upc_ids,
            )
            if anchor_day_entry else None
        )
        summary={
            "report_date":anchor,
            "active_upcs_28d":0,
            "upcs_sold_report_date":0,
            "ready_upcs":0,
            "qa_hold_upcs":0,
            "report_date_sales_dollars":Decimal("0"),
            "sales_dollars_7d":Decimal("0"),
            "sales_dollars_14d":Decimal("0"),
            "sales_dollars_28d":Decimal("0"),
            "slowing_items":0,
            "low_gp_items":0,
            "price_review_candidates":0,
            "price_tolerance_suppressed":0,
            "price_240_249_mismatch_count":len(pair_mismatch_suggestions),
        }
        suggestions=[]
        day_items=[]
        targets={"LIVE":Decimal("0.15"),"FRESH":Decimal("0.30"),"FROZEN":Decimal("0.44")}

        for row in rows:
            upc_id=int(row["upc_id"])
            m7=_batch_sales_metric(daily_history,history_days,upc_id,7)
            m14=_batch_sales_metric(daily_history,history_days,upc_id,14)
            m28=_batch_sales_metric(daily_history,history_days,upc_id,28)
            q14=_d(m14.get("sold_quantity"))
            q28=_d(m28.get("sold_quantity"))
            pclass=str(row.get("product_class") or "").upper()

            current_oh=(
                _d(row.get("current_oh"))
                if row.get("current_oh") is not None else None
            )
            has_oh=bool(current_oh is not None and current_oh>0)
            doh_for_gate=(
                _d(row.get("doh")) if row.get("doh") is not None else None
            )
            clearance_gate=bool(
                (
                    pclass in {"FRESH","LIVE"}
                    and doh_for_gate is not None
                    and doh_for_gate>Decimal("7")
                )
                or (
                    pclass=="FROZEN"
                    and doh_for_gate is not None
                    and doh_for_gate>Decimal("60")
                )
            )
            history_gate=bool(q14>0)

            # Pricing Review qualification:
            # - usable positive OH is required; no stock => no price action
            # - recent 14 completed-day sales history is required so candidate
            #   pricing is grounded in observed sales/price performance
            # - Fresh requires DOH > 7
            # - Frozen requires DOH > 60
            # - Live/other stocked UPCs have no additional DOH gate
            freshness_qualified=(
                (pclass=="FRESH" and doh_for_gate is not None and doh_for_gate>Decimal("7"))
                or (pclass=="FROZEN" and doh_for_gate is not None and doh_for_gate>Decimal("60"))
                or (pclass not in {"FRESH","FROZEN"})
            )
            if not has_oh or not history_gate or not freshness_qualified:
                continue

            # Price is re-resolved at serving time so a newer accepted Price
            # List/SINGLE_DATE POS event is visible even before another full
            # Phase 3 Quick Check rebuild.
            _overlay_live_current_price(cur,row)

            status=str(row.get("quick_check_status") or "")
            if q28>0:
                summary["active_upcs_28d"]+=1
                if status=="READY":
                    summary["ready_upcs"]+=1
                elif status=="QA_HOLD":
                    summary["qa_hold_upcs"]+=1

            summary["sales_dollars_7d"]+=_d(m7.get("sales_amount"))
            summary["sales_dollars_14d"]+=_d(m14.get("sales_amount"))
            summary["sales_dollars_28d"]+=_d(m28.get("sales_amount"))

            day_obs=daily_history.get(upc_id,{}).get(anchor,{
                "sold_quantity":Decimal("0"),
                "sales_amount":Decimal("0"),
                "price_types":{},
            })
            day_qty=_d(day_obs.get("sold_quantity"))
            day_sales=_d(day_obs.get("sales_amount"))
            summary["report_date_sales_dollars"]+=day_sales
            if day_qty>0:
                summary["upcs_sold_report_date"]+=1

            v7=m7.get("velocity_per_supported_day")
            v14=m14.get("velocity_per_supported_day")
            v28=m28.get("velocity_per_supported_day")
            trend_ratio=(
                _d(v7)/_d(v28)
                if v7 is not None and v28 is not None and _d(v28)>0 else None
            )
            if trend_ratio is not None and trend_ratio<Decimal("0.80"):
                summary["slowing_items"]+=1

            target_gp=targets.get(pclass)
            gp=(
                Decimal(str(row["gp_pct_current"]))
                if row.get("gp_pct_current") is not None else None
            )
            if gp is not None and target_gp is not None and gp<target_gp:
                summary["low_gp_items"]+=1

            if day_qty>0:
                day_items.append({
                    "upc":row.get("ean_upc"),
                    "name":row.get("selling_description"),
                    "family_article_number":row.get("main_article_number"),
                    "category":pclass,
                    "readiness":status,
                    "selling_uom":row.get("selling_uom"),
                    "upc_role":_upc_role(row),
                    "sold_quantity":day_qty,
                    "qty_uom":_safe_qty_uom(row.get("ean_upc"),row.get("selling_uom")),
                    "sales_amount":day_sales,
                    "avg_sold_price":day_sales/day_qty if day_qty else None,
                    "price_types":sorted(str(k).upper() for k in (day_obs.get("price_types") or {}).keys()),
                    "current_price":row.get("current_price"),
                    "current_price_type":row.get("current_price_type"),
                    "current_price_source":row.get("current_price_source"),
                    "current_price_asof_date":row.get("current_price_asof_date"),
                    "velocity_7d":v7,
                    "velocity_14d":v14,
                    "velocity_28d":v28,
                })

            price_opt=_gp_day_price_suggestion_from_batch(
                row,upc_id,daily_history,history_days
            )
            current=price_opt.get("current_price_used")
            suggested=price_opt.get("suggested_price")
            basis=price_opt.get("basis")
            has_company=bool(price_opt.get("has_company_reference"))
            company_low=price_opt.get("company_range_low")
            company_high=price_opt.get("company_range_high")
            clearance=bool(price_opt.get("clearance_due_to_doh"))
            clearance_reason=price_opt.get("clearance_reason")
            doh_value=price_opt.get("doh")

            report_day_types=set(
                str(k).upper() for k in (day_obs.get("price_types") or {}).keys()
            )

            reasons=[]
            score=Decimal("0")
            price_gap_pct=None
            if current is not None and _d(current)>0 and suggested is not None:
                price_gap_pct=abs(_d(suggested)-_d(current))/_d(current)

            if clearance_reason=="FRESH_DOH_GT_7":
                reasons.append("FRESH_DOH_GT_7_CLEARANCE")
                score+=Decimal("70")
            elif clearance_reason=="FROZEN_DOH_GT_60":
                reasons.append("FROZEN_DOH_GT_60_MARKDOWN")
                score+=Decimal("60")
            elif has_company:
                reasons.append("COMPANY_RANGE_CONSTRAINED_14D_OPTIMIZATION")
                score+=Decimal("30")
            else:
                reasons.append("14D_MAX_GP_PER_DAY")
                score+=Decimal("25")

            if trend_ratio is not None and trend_ratio<Decimal("0.80"):
                reasons.append("7D_VELOCITY_BELOW_28D")
            if gp is not None and target_gp is not None and gp<target_gp:
                reasons.append("GP_BELOW_CATEGORY_REFERENCE")

            cost=(
                Decimal(str(row["current_cost_per_selling_unit"]))
                if row.get("current_cost_per_selling_unit") is not None else None
            )
            current_gp_day=(
                (_d(current)-cost)*_d(v7)
                if current is not None and cost is not None and v7 is not None
                else None
            )
            expected_gp_day=price_opt.get("expected_gp_per_day_from_observed_demand")
            gp_day_gain=(
                _d(expected_gp_day)-_d(current_gp_day)
                if expected_gp_day is not None and current_gp_day is not None
                else None
            )
            gp_day_gain_pct=(
                gp_day_gain/abs(_d(current_gp_day))
                if gp_day_gain is not None and current_gp_day not in (None,Decimal("0"))
                else None
            )

            # No price-change suggestion is needed when the live current
            # price is already within +/- $0.25 of the supported candidate.
            if (
                current is not None
                and suggested is not None
                and abs(_d(suggested)-_d(current)) <= Decimal("0.25")
            ):
                summary["price_tolerance_suppressed"]+=1
                continue

            blocked_reason=None
            if status!="READY":
                blocked_reason="NOT_READY"
            elif "SALE" in report_day_types:
                blocked_reason="REPORT_DATE_ACTIVE_SALE"
            elif current is None or _d(current)<=0:
                blocked_reason="CURRENT_PRICE_UNAVAILABLE"
            elif cost is None:
                blocked_reason="CURRENT_COST_UNAVAILABLE"
            elif price_opt.get("status")!="READY" or suggested is None:
                blocked_reason=price_opt.get("reason") or "PRICING_CANDIDATE_UNAVAILABLE"

            actionable=blocked_reason is None
            if actionable:
                summary["price_review_candidates"]+=1

            if gp_day_gain is not None and gp_day_gain>0:
                score+=min(Decimal("25"),gp_day_gain*Decimal("2"))
                reasons.append("POSITIVE_OBSERVED_GP_DAY_OPPORTUNITY")
            if gp_day_gain_pct is not None and gp_day_gain_pct>0:
                score+=min(Decimal("10"),gp_day_gain_pct*Decimal("10"))
            if trend_ratio is not None and trend_ratio<Decimal("0.80"):
                score+=min(Decimal("10"),(Decimal("1")-trend_ratio)*Decimal("20"))
            score+=min(Decimal("5"),q14/Decimal("10"))

            if clearance_reason=="FRESH_DOH_GT_7":
                primary_reason=f"Fresh DOH {float(_d(doh_value)):.1f} > 7; clearance priority"
            elif clearance_reason=="FROZEN_DOH_GT_60":
                primary_reason=f"Frozen DOH {float(_d(doh_value)):.1f} > 60; markdown priority"
            elif has_company:
                primary_reason="14D max GP$/day within Company A/B/C range"
            else:
                primary_reason="14D max GP$/day from sales history"

            review_status=(
                "ACTIONABLE" if actionable
                else (
                    "WAIT_ACTIVE_SALE" if blocked_reason=="REPORT_DATE_ACTIVE_SALE"
                    else ("QA_HOLD" if blocked_reason=="NOT_READY" else "REVIEW_ONLY")
                )
            )
            suggested_gp=(
                (_d(suggested)-cost)/_d(suggested)
                if actionable and cost is not None and suggested is not None and _d(suggested)>0
                else None
            )
            actionable_price=suggested if actionable else None
            suggestions.append({
                "urgency_score":score.quantize(Decimal("0.01")),
                "review_status":review_status,
                "review_blocker":blocked_reason,
                "actionable":actionable,
                "report_date":anchor,
                "upc":row.get("ean_upc"),
                "name":row.get("selling_description"),
                "family_article_number":row.get("main_article_number"),
                "family_name":row.get("family_description"),
                "category":pclass,
                "readiness":status,
                "selling_uom":row.get("selling_uom"),
                "upc_role":_upc_role(row),
                "current_price":current,
                "current_price_type":row.get("current_price_type"),
                "current_price_basis":price_opt.get("current_price_basis"),
                "current_price_source":price_opt.get("current_price_source"),
                "current_price_observed_date":price_opt.get("current_price_observed_date"),
                "historical_observed_price_asof_report_date":price_opt.get("historical_observed_price_asof_report_date"),
                "historical_observed_price_date":price_opt.get("historical_observed_price_date"),
                "suggested_price":actionable_price,
                "candidate_price":suggested,
                "suggestion_basis":basis,
                "selection_basis":price_opt.get("selection_basis"),
                "historical_window_supported_days":price_opt.get("historical_window_supported_days"),
                "company_price_a":price_opt.get("company_prices",{}).get("A"),
                "company_price_b":price_opt.get("company_prices",{}).get("B"),
                "company_price_c":price_opt.get("company_prices",{}).get("C"),
                "company_range_low":company_low,
                "company_range_high":company_high,
                "has_company_reference":has_company,
                "current_within_company_range":price_opt.get("current_within_company_range"),
                "clearance_due_to_doh":clearance,
                "clearance_reason":clearance_reason,
                "doh":doh_value,
                "current_oh":current_oh,
                "current_oh_uom":row.get("current_oh_uom"),
                "pricing_rule_priority":(
                    0 if clearance else (1 if has_company else 2)
                ),
                "primary_reason_text":primary_reason,
                "direction":(
                    (
                        "INCREASE" if _d(actionable_price)>_d(current)
                        else ("DECREASE" if _d(actionable_price)<_d(current) else "KEEP")
                    )
                    if actionable_price is not None and current is not None
                    else "REVIEW"
                ),
                "price_gap_pct":price_gap_pct,
                "current_gp_pct_reference":gp,
                "suggested_gp_pct_at_current_cost":suggested_gp,
                "current_gp_per_day_7d":current_gp_day,
                "expected_gp_per_day_observed_price_demand":(
                    expected_gp_day if actionable else None
                ),
                "candidate_expected_gp_per_day":expected_gp_day,
                "gp_per_day_opportunity":(
                    gp_day_gain if gp_day_gain is not None and gp_day_gain>0 else None
                ),
                "gp_per_day_opportunity_pct":(
                    gp_day_gain_pct if gp_day_gain_pct is not None and gp_day_gain_pct>0 else None
                ),
                "observed_velocity_at_suggested_price":price_opt.get("expected_velocity_from_observed_price_days"),
                "qty_report_date":day_qty,
                "sales_report_date":day_sales,
                "qty_uom":_safe_qty_uom(row.get("ean_upc"),row.get("selling_uom")),
                "qty_7d":m7.get("sold_quantity"),
                "qty_14d":m14.get("sold_quantity"),
                "qty_28d":m28.get("sold_quantity"),
                "velocity_7d":v7,
                "velocity_14d":v14,
                "velocity_28d":v28,
                "velocity_7d_vs_28d_ratio":trend_ratio,
                "cost_basis":price_opt.get("cost_basis"),
                "cost_date":price_opt.get("cost_date"),
                "reasons":reasons,
            })

        mapped_report_sales=_d(summary["report_date_sales_dollars"])
        canonical_report_sales=(
            _d(canonical_day_sales.get("sales_amount"))
            if canonical_day_sales else None
        )
        report_date_reconciliation={
            "canonical_source_sales":canonical_report_sales,
            "mapped_report_sales":mapped_report_sales,
            "difference":(
                mapped_report_sales-canonical_report_sales
                if canonical_report_sales is not None else None
            ),
            "matches_to_cent":(
                abs(mapped_report_sales-canonical_report_sales)<Decimal("0.005")
                if canonical_report_sales is not None else None
            ),
            "canonical_source":canonical_day_sales,
            "mapping_breakdown":mapping_breakdown,
            "unmapped_source_sales":(
                mapping_breakdown.get("unmapped_source_sales")
                if mapping_breakdown else None
            ),
            "unmapped_source_qty":(
                mapping_breakdown.get("unmapped_source_qty")
                if mapping_breakdown else None
            ),
            "unmapped_source_qty_uom":(
                mapping_breakdown.get("unmapped_source_qty_uom")
                if mapping_breakdown else None
            ),
            "unmapped_qty_mixed_or_unknown":(
                mapping_breakdown.get("unmapped_qty_mixed_or_unknown")
                if mapping_breakdown else None
            ),
            "unmapped_upc_count":(
                mapping_breakdown.get("unmapped_upc_count")
                if mapping_breakdown else None
            ),
            "top_unmapped_upcs":(
                mapping_breakdown.get("top_unmapped_upcs",[])
                if mapping_breakdown else []
            ),
            "mapped_source_sales":(
                mapping_breakdown.get("mapped_source_sales")
                if mapping_breakdown else None
            ),
            "mapped_source_vs_report_difference":(
                mapped_report_sales-_d(mapping_breakdown.get("mapped_source_sales"))
                if mapping_breakdown else None
            ),
            "canonical_minus_mapped_source":(
                canonical_report_sales-_d(mapping_breakdown.get("mapped_source_sales"))
                if canonical_report_sales is not None and mapping_breakdown else None
            ),
            "mapped_basis":"SUM_OF_V2_MAPPED_UPCS_IN_REPORT_SCOPE",
            "audit_rule":"CANONICAL_SOURCE_TOTAL_IS_REPORT_DATE_SALES_AUTHORITY",
        }

        # Add mandatory 240=249 mismatches ahead of the normal suggestion
        # queue and suppress a duplicate normal 249 suggestion for the same UPC.
        suggestions = pair_mismatch_suggestions + [
            x for x in suggestions
            if (
                str(x.get("upc") or "") not in pair_mismatch_service_upcs
                and not (
                    _numeric_key(x.get("upc")).startswith("249")
                    and str(x.get("upc") or "") in price_pair_meta
                )
            )
        ]
        for suggestion in suggestions:
            upc_key=str(suggestion.get("upc") or "")
            pair_meta=price_pair_meta.get(upc_key)
            if not pair_meta:
                continue
            suggestion.update(pair_meta)
            if _numeric_key(upc_key).startswith("240") and suggestion.get("candidate_price") is not None:
                suggestion["related_249_required_price"]=suggestion.get("candidate_price")
            elif _numeric_key(upc_key).startswith("249"):
                suggestion["related_249_required_price"]=suggestion.get("candidate_price")

        suggestions.sort(
            key=lambda x:(
                0 if x.get("priority_240_249_mismatch") else 1,
                0 if x.get("actionable") else 1,
                int(x.get("pricing_rule_priority") if x.get("pricing_rule_priority") is not None else 9),
                -float(x.get("gp_per_day_opportunity") or 0),
                -float(x.get("urgency_score") or 0),
                -float(x.get("qty_28d") or 0),
                str(x.get("name") or ""),
            )
        )
        suggestions=suggestions[:limit]
        day_items.sort(
            key=lambda x:(
                -float(x.get("sales_amount") or 0),
                -float(x.get("sold_quantity") or 0),
                str(x.get("name") or ""),
            )
        )

        avg7=summary["sales_dollars_7d"]/Decimal("7") if summary["sales_dollars_7d"] else Decimal("0")
        avg14=summary["sales_dollars_14d"]/Decimal("14") if summary["sales_dollars_14d"] else Decimal("0")
        report_vs_7=(
            (summary["report_date_sales_dollars"]-avg7)/avg7
            if avg7>0 else None
        )
        report_vs_14=(
            (summary["report_date_sales_dollars"]-avg14)/avg14
            if avg14>0 else None
        )

        analysis=[
            {
                "type":"REPORT_DATE_SALES_VS_7D_AVG",
                "value_pct":report_vs_7,
                "message":(
                    f"{anchor.isoformat()} sales were "
                    + ("above" if report_vs_7 is not None and report_vs_7>=0 else "below")
                    + " the 7-supported-day daily average."
                    if report_vs_7 is not None
                    else "7-day comparison unavailable."
                ),
            },
            {
                "type":"REPORT_DATE_SALES_VS_14D_AVG",
                "value_pct":report_vs_14,
                "message":(
                    f"{anchor.isoformat()} sales were "
                    + ("above" if report_vs_14 is not None and report_vs_14>=0 else "below")
                    + " the 14-supported-day daily average."
                    if report_vs_14 is not None
                    else "14-day comparison unavailable."
                ),
            },
            {
                "type":"ITEM_HEALTH",
                "message":f"{summary['slowing_items']} active items have 7D velocity below 80% of their 28D velocity as of {anchor.isoformat()}.",
            },
            {
                "type":"MARGIN_REFERENCE",
                "message":f"{summary['low_gp_items']} active items are below the current category GP reference.",
            },
            {
                "type":"PRICE_REVIEW",
                "message":f"{summary['price_review_candidates']} items are actionable under Company-range, 14-day GP$/day, or freshness-clearance pricing rules using sales evidence through {anchor.isoformat()}.",
            },
        ]
        narrative_analysis=_performance_narrative(
            anchor=anchor,
            summary=summary,
            report_vs_7=report_vs_7,
            report_vs_14=report_vs_14,
        )
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_PERFORMANCE_V11",
        "category":cat,
        "report_date":anchor,
        "report_date_weekday":WEEKDAY_NAMES[anchor.weekday()],
        "supported_day_contract":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
        "summary":{
            **summary,
            "report_date_sales_dollars":(
                canonical_report_sales
                if cat=="ALL" and canonical_report_sales is not None
                else summary["report_date_sales_dollars"]
            ),
        },
        "report_date_reconciliation":report_date_reconciliation,
        "analysis":analysis,
        "narrative_analysis":narrative_analysis,
        "report_date_top_sellers":day_items[:20],
        "report_date_items":day_items[:limit],
        "report_date_item_limit":limit,
        "top_urgent_price_suggestions":suggestions,
        "top_urgent_limit":limit,
        "price_suggestion_rules":{
            "execution":"ANALYSIS_ONLY_NO_SAVE",
            "sales_evidence_cutoff":anchor,
            "historical_window_supported_days":14,
            "company_reference_rule":"RANGE_IS_MIN_TO_MAX_OF_AVAILABLE_POSITIVE_A_B_C; QUALIFIED_UPCS_MAY_BE_REVIEWED_REGARDLESS_OF_CURRENT_IN_RANGE",
            "company_candidate_rule":"CANDIDATE_MUST_STAY_WITHIN_COMPANY_RANGE; ALL_QUALIFIED_UPCS_MAXIMIZE_14D_GP_DOLLARS_PER_DAY; FALLBACK_CLAMP_14D_OR_SWEET_SPOT_TO_RANGE",
            "no_company_reference_rule":"MAX_14D_OBSERVED_GP_DOLLARS_PER_DAY",
            "freshness_rule":"FRESH_REQUIRES_DOH_GT_7; FROZEN_REQUIRES_DOH_GT_60; LIVE_OR_OTHER_HAS_NO_EXTRA_DOH_GATE; GP_DOLLARS_PER_DAY_REMAINS_OPTIMIZATION_OBJECTIVE",
            "clearance_candidate_rule":"DOH_RAISES_URGENCY_ONLY; CANDIDATE_STILL_MAXIMIZES_SUPPORTED_14D_GP_DOLLARS_PER_DAY",
            "candidate_demand_basis":"ACTUAL_HISTORICAL_SALES_RESPONSE_AT_OBSERVED_PRICE",
            "cost_basis":"CURRENT_AUTHORITATIVE_COST",
            "cost_caveat":"Historical daily cost lineage is not yet exposed in V2 Performance; suggestions use current authoritative cost while sales evidence is cut off at report date.",
            "report_date_active_sale_excluded":True,
            "qa_hold_excluded":True,
            "price_change_tolerance":"SUPPRESS_WHEN_ABS_CURRENT_MINUS_SUGGESTED_LE_0.25",
            "review_queue":"POSITIVE_OH_AND_14D_SALES_HISTORY; FRESH_DOH_GT_7; FROZEN_DOH_GT_60; LIVE_OR_OTHER_NO_EXTRA_DOH_GATE",
            "price_240_249_rule":"WHEN_CONFIRMED_240_AND_249_FORMS_EXIST_IN_THE_SAME_FAMILY_PRODUCT_GROUP_THEIR_CURRENT_PRICES_MUST_MATCH; MISMATCH_IS_HIGHEST_PRIORITY",
            "price_249_reminder_rule":"ANY_240_PRICING_SUGGESTION_WITH_A_RELATED_249_MUST_REMIND_THE_USER_TO_CHANGE_249_TO_THE_SAME_ACCEPTED_PRICE",
            "urgency_primary_sort":"240_249_MISMATCH_FIRST_THEN_ACTIONABLE_THEN_FRESH_CLEARANCE_THEN_FROZEN_MARKDOWN_THEN_GP_DAY_OPPORTUNITY",
        },
    }

def family_ordering_analysis(
    family_key: str,
    *,
    ordering_date: date | None = None,
    expected_delivery_date: date | None = None,
    promotion_involved: bool = False,
    promotion_start_date: date | None = None,
    promotion_end_date: date | None = None,
    promotion_price: Decimal | None = None,
) -> dict[str,Any]:
    """CORE family-level ordering calculator.

    Uses the same family demand/OH/promotion primitives as Main ORDERING.
    Access may originate from a UPC, but the ordering decision is made for the
    Family Article so related UPC demand is not analyzed independently.
    """
    raw=str(family_key or "").strip()
    order_day=ordering_date or business_today()

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        if raw.isdigit():
            cur.execute(
                """SELECT family_id,main_article_number,family_description
                   FROM product_family
                   WHERE main_article_number=%s OR family_id=%s
                   ORDER BY CASE WHEN main_article_number=%s THEN 0 ELSE 1 END
                   LIMIT 1""",
                (raw,int(raw),raw),
            )
        else:
            cur.execute(
                """SELECT family_id,main_article_number,family_description
                   FROM product_family
                   WHERE UPPER(family_description)=UPPER(%s)
                   LIMIT 1""",
                (raw,),
            )
        fam=cur.fetchone()
        if not fam:
            cur.close()
            raise KeyError("V2_FAMILY_NOT_FOUND")

        fid=int(fam["family_id"])
        cur.execute(
            """SELECT * FROM quick_check_current
               WHERE family_id=%s
               ORDER BY ean_upc""",
            (fid,),
        )
        rows=cur.fetchall()
        if not rows:
            cur.close()
            raise KeyError("V2_FAMILY_NOT_FOUND")

        categories=sorted({
            str(x.get("product_class") or "").upper()
            for x in rows if x.get("product_class")
        })
        category=categories[0] if len(categories)==1 else ("MIXED" if categories else None)

        m28=_family_sales_series(cur,rows,28)
        m7=_family_sales_series(cur,rows,7)
        regular=_family_regular_baseline(cur,rows,28)
        family_oh=_family_effective_oh(cur,rows)
        events=_family_receipt_events(cur,fid)
        pattern=_delivery_pattern(events,after_date=order_day)
        observed_delivery=pattern.get("next_expected_delivery_date")
        fallback_weekday=(
            4 if category=="FRESH"
            else (1 if category=="FROZEN" else None)
        )
        fallback_delivery=(
            _strict_next_weekday(order_day,fallback_weekday)
            if fallback_weekday is not None else None
        )
        delivery=expected_delivery_date or observed_delivery or fallback_delivery
        delivery_source=(
            "USER_INPUT" if expected_delivery_date is not None
            else (
                "OBSERVED_DELIVERY_PATTERN"
                if observed_delivery is not None
                else (
                    "FOLLOWING_FRIDAY_FALLBACK"
                    if category=="FRESH"
                    else (
                        "FOLLOWING_TUESDAY_FALLBACK"
                        if category=="FROZEN"
                        else "UNRESOLVED"
                    )
                )
            )
        )
        next_next=(
            _next_delivery_after(pattern,delivery)
            if delivery is not None else None
        )
        next_next_source="OBSERVED_DELIVERY_PATTERN" if next_next is not None else None
        if delivery is not None and next_next is None and category in {"FRESH","FROZEN"}:
            next_next=delivery+timedelta(days=7)
            next_next_source="WEEKLY_FALLBACK_PLUS_7_DAYS"

        blockers=[]
        if m28.get("status")!="READY" or m7.get("status")!="READY":
            blockers.append("FAMILY_UOM_UNRESOLVED")
        if family_oh.get("status")!="READY" or family_oh.get("quantity") is None:
            blockers.append(str(family_oh.get("status") or "OH_UNAVAILABLE"))
        if delivery is None:
            blockers.append("EXPECTED_DELIVERY_DATE_REQUIRED")
        elif delivery < order_day:
            blockers.append("EXPECTED_DELIVERY_BEFORE_ORDER_DATE")
        if delivery is not None and next_next is None:
            blockers.append("NEXT_NEXT_DELIVERY_UNRESOLVED")
        if regular.get("regular_velocity_per_supported_day") is None:
            blockers.append("REGULAR_BASELINE_UNAVAILABLE")

        demand_uom=str(m7.get("uom") or "").upper()
        oh_uom=str(family_oh.get("uom") or "").upper()
        if family_oh.get("status")=="READY" and demand_uom and oh_uom and demand_uom!=oh_uom:
            blockers.append("OH_TO_FAMILY_DEMAND_UOM_UNRESOLVED")

        promo_history=_family_historical_sale_periods(cur,rows,365)
        promo_baseline=None
        promo_vel=None
        promo_fallback=False
        if promotion_involved:
            if promotion_start_date is None or promotion_end_date is None or promotion_price is None:
                blockers.append("PROMOTION_INPUTS_REQUIRED")
            elif promotion_end_date < promotion_start_date:
                blockers.append("PROMOTION_END_BEFORE_START")
            else:
                promo_baseline=_family_promotion_baseline(
                    promo_history,
                    promotion_start_date,
                    promotion_end_date,
                    Decimal(str(promotion_price)),
                )
                promo_vel=promo_baseline.get("promotion_velocity_per_day")
                if promo_vel is None and regular.get("regular_velocity_per_supported_day") is not None:
                    promo_vel=regular.get("regular_velocity_per_supported_day")
                    promo_fallback=True

        raw_oh=(
            _d(family_oh.get("quantity"))
            if family_oh.get("quantity") is not None else None
        )
        ordering_oh=max(Decimal("0"),raw_oh) if raw_oh is not None else None
        vel7=m7.get("velocity_per_supported_day")
        dos=(
            ordering_oh/_d(vel7)
            if ordering_oh is not None and vel7 is not None and _d(vel7)>0
            else None
        )
        active_28=(
            m28.get("sold_quantity") is not None
            and _d(m28.get("sold_quantity"))>0
        )

        total=Decimal("0")
        before_delivery=Decimal("0")
        regular_usage=Decimal("0")
        promotion_usage=Decimal("0")
        forecast_rows=[]
        reg_vel=regular.get("regular_velocity_per_supported_day")
        if not blockers and next_next is not None and reg_vel is not None:
            day=order_day
            while day<next_next:
                is_promo=bool(
                    promotion_involved
                    and promotion_start_date is not None
                    and promotion_end_date is not None
                    and promotion_start_date<=day<=promotion_end_date
                )
                velocity=_d(promo_vel if is_promo else reg_vel)
                total+=velocity
                if is_promo:
                    promotion_usage+=velocity
                else:
                    regular_usage+=velocity
                if delivery is not None and day<delivery:
                    before_delivery+=velocity
                forecast_rows.append({
                    "date":day,
                    "demand_type":"PROMOTION" if is_promo else "REGULAR",
                    "forecast_usage":velocity,
                    "uom":demand_uom or family_oh.get("uom"),
                    "basis":(
                        "HISTORICAL_SALE_PROMOTION"
                        if is_promo and promo_baseline and promo_baseline.get("status")=="READY"
                        else (
                            "REGULAR_FALLBACK_NO_MATCHING_SALE_HISTORY"
                            if is_promo else "REGULAR_BASELINE"
                        )
                    ),
                })
                day+=timedelta(days=1)

        suggested=(
            max(Decimal("0"),total-ordering_oh)
            if ordering_oh is not None and next_next is not None and not blockers
            else None
        )
        projected=(
            ordering_oh-before_delivery
            if ordering_oh is not None and delivery is not None and not blockers
            else None
        )
        pre_delivery_shortage=(
            max(Decimal("0"),before_delivery-ordering_oh)
            if ordering_oh is not None else None
        )

        result={
            "contract_version":"WEBAPP_V2_FAMILY_ORDERING_V3",
            "family_id":fid,
            "family_article_number":fam.get("main_article_number"),
            "family_article_name":fam.get("family_description"),
            "name":fam.get("family_description"),
            "category":category,
            "readiness":(
                "READY"
                if any(str(x.get("quick_check_status") or "")=="READY" for x in rows)
                else str(rows[0].get("quick_check_status") or "UNKNOWN")
            ),
            "inputs":{
                "ordering_date":order_day,
                "expected_delivery_date":delivery,
                "expected_delivery_default_source":delivery_source,
                "promotion_involved":bool(promotion_involved),
                "promotion_start_date":promotion_start_date,
                "promotion_end_date":promotion_end_date,
                "promotion_price":promotion_price,
                "promotion_price_type":"SALE" if promotion_involved else None,
            },
            "inventory":{
                "effective_oh":family_oh,
                "raw_effective_oh_qty":raw_oh,
                "ordering_oh_qty":ordering_oh,
                "negative_oh_treated_as_zero":bool(raw_oh is not None and raw_oh<0),
                "dos":dos,
            },
            "sales":{
                "7d":m7,
                "28d":m28,
                "active_selling_28_supported_days":active_28,
            },
            "observed_delivery":pattern,
            "next_next_delivery_date":next_next,
            "next_next_delivery_source":next_next_source,
            "regular_baseline":regular,
            "promotion_baseline":promo_baseline,
            "historical_promotions":promo_history,
            "forecast":{
                "horizon_start":order_day,
                "horizon_end_exclusive":next_next,
                "regular_or_sale_by_calendar_date":forecast_rows,
                "forecast_regular_usage":regular_usage if forecast_rows else None,
                "forecast_promotion_usage":promotion_usage if forecast_rows else None,
                "forecast_usage_until_next_next_delivery":total if forecast_rows else None,
                "forecast_usage_before_expected_delivery":before_delivery if forecast_rows else None,
                "projected_oh_at_expected_delivery":projected,
                "pre_delivery_shortage":pre_delivery_shortage,
                "suggested_order_qty":suggested,
                "suggested_order_uom":demand_uom or family_oh.get("uom"),
                "promotion_fallback_to_regular":promo_fallback,
                "rounding_applied":False,
            },
            "status":"READY" if not blockers else "BLOCKED",
            "blockers":blockers,
            "rules":{
                "decision_level":"FAMILY_ARTICLE",
                "sales_history":"COMPLETED_CANONICAL_DATA_DAYS_ONLY",
                "missing_source_dates_count_as_zero":False,
                "promotion_definition":"PRICE_TYPE_SALE_ONLY",
                "tpr_is_promotion":False,
                "negative_effective_oh_for_ordering":"TREAT_AS_ZERO",
                "coverage_target":"THROUGH_DAY_BEFORE_NEXT_NEXT_DELIVERY",
                "saved":False,
                "submitted":False,
            },
        }
        cur.close()
    return result


# V2 CORE UPC Ordering is intentionally a Family Article decision.
# Resolve the selected UPC to its family, then run the same family-level engine.
def ordering_analysis(
    upc: str,
    *,
    ordering_date: date | None = None,
    expected_delivery_date: date | None = None,
    promotion_involved: bool = False,
    promotion_start_date: date | None = None,
    promotion_end_date: date | None = None,
    promotion_price: Decimal | None = None,
) -> dict[str,Any]:
    raw=str(upc or "").strip()
    nk=_numeric_key(raw)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            """SELECT ean_upc,family_id,main_article_number
               FROM quick_check_current
               WHERE ean_upc=%s
                  OR (ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM ean_upc)=%s)
               ORDER BY CASE quick_check_status WHEN 'READY' THEN 0 WHEN 'QA_HOLD' THEN 1 ELSE 2 END
               LIMIT 1""",
            (raw,nk),
        )
        row=cur.fetchone()
        cur.close()
    if not row:
        raise KeyError("V2_UPC_NOT_FOUND")
    result=family_ordering_analysis(
        str(row.get("main_article_number") or row.get("family_id")),
        ordering_date=ordering_date,
        expected_delivery_date=expected_delivery_date,
        promotion_involved=promotion_involved,
        promotion_start_date=promotion_start_date,
        promotion_end_date=promotion_end_date,
        promotion_price=promotion_price,
    )
    result["source_upc"]=row.get("ean_upc")
    return result
