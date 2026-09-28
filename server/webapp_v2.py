from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal
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
)


WEEKDAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _norm_text(value: Any) -> str:
    return " ".join(str(value or "").upper().split())


def _numeric_key(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits.lstrip("0") or ("0" if digits else "")


def _readiness_rank(status: Any) -> int:
    return {
        "READY": 0,
        "QA_HOLD": 1,
        "HISTORICAL_ONLY": 2,
    }.get(str(status or "").upper(), 3)


def _canonical_sales_days(cur, limit: int | None = None) -> list[dict[str, Any]]:
    return source_data_days(
        cur,
        "sales_by_price_type",
        limit=limit,
        up_to=completed_through_date(),
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
        cur.execute(
            f"""SELECT period_end_date AS business_date,UPPER(TRIM(price_type)) AS price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM sales_period_observation
                WHERE upc_id=%s
                  AND temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                GROUP BY period_end_date,UPPER(TRIM(price_type))""",
            (int(upc_id), *args),
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
        cur.execute(
            f"""SELECT business_date,UPPER(TRIM(price_type)) AS price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM pos_daily_backfill_observation
                WHERE upc_id=%s
                  AND ({' OR '.join(clauses)})
                GROUP BY business_date,UPPER(TRIM(price_type))""",
            (int(upc_id), *args),
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
) -> dict[str, Any]:
    days = _canonical_sales_days(cur, limit=supported_day_count)
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
) -> dict[str, Any]:
    days = _canonical_sales_days(cur, limit=max(1, min(int(supported_day_count), 365)))
    daily = _daily_sales_by_price_type(cur, upc_id, days)
    rows = []
    for day in sorted(daily):
        x = daily[day]
        rows.append({
            "date": day,
            "supported": True,
            "sold_quantity": x["sold_quantity"],
            "sales_amount": x["sales_amount"],
            "avg_sold_price": (
                x["sales_amount"] / x["sold_quantity"]
                if x["sold_quantity"] != 0 else None
            ),
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


def _relevance(query: str, *, name: Any, number: Any, kind: str, matched_as: str | None = None) -> int:
    q = _norm_text(query)
    n = _norm_text(name)
    num = str(number or "").strip()
    if query.isdigit():
        qk = _numeric_key(query)
        nk = _numeric_key(num)
        if qk and qk == nk:
            return 1000 if kind in {"FAMILY","UPC"} else 980
        if qk and nk.startswith(qk):
            return 860
        return 0
    if q and n == q:
        return 950
    if q and n.startswith(q):
        return 850
    q_tokens = [x for x in q.split() if x]
    if q_tokens and all(t in n for t in q_tokens):
        return 760
    if q and q in n:
        return 700
    return 0


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
                (q,nk,q,q,f"{q}%",f"{q}%",f"{q}%"),
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
                (q,f"{q}%"),
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

        for match in article_matches:
            fid=int(match["family_id"])
            existing=next((x for x in results if x.get("result_type")=="FAMILY" and x.get("family_id")==fid),None)
            rel=_relevance(q,name=match.get("article_description"),number=match.get("article_number"),kind="ARTICLE")
            if rel<=0:
                continue
            if existing:
                existing["relevance"]=max(int(existing["relevance"]),rel)
                existing["matched_as"]="ARTICLE"
                existing["matched_article_number"]=match.get("article_number")
            else:
                cur.execute("SELECT * FROM quick_check_current WHERE family_id=%s",(fid,))
                children=cur.fetchall()
                statuses=[]; category=None
                for child in children:
                    statuses.append(str(child.get("quick_check_status") or ""))
                    category=category or child.get("product_class")
                family_sales=_family_sales_series(cur,children,28)
                results.append({
                    "result_type":"FAMILY",
                    "family_id":fid,
                    "number":match.get("main_article_number"),
                    "name":match.get("family_description"),
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
                    "matched_article_number":match.get("article_number"),
                })

        results.sort(
            key=lambda x:(
                -int(x.get("relevance") or 0),
                _readiness_rank(x.get("readiness")),
                -float(x.get("qty_28d") or 0),
                str(x.get("name") or ""),
            )
        )
        cur.close()

    return {
        "query":q,
        "count":min(len(results),limit),
        "results":results[:limit],
        "sort_contract":["RELEVANCE_DESC","READINESS","QTY_28_SUPPORTED_DAYS_DESC"],
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
        }

    usable=[x for x in owners.values() if x.get("analysis_usable") and x.get("quantity") is not None and x.get("uom")]
    uoms={str(x["uom"]).upper() for x in usable}
    if not usable:
        return {"status":"UNAVAILABLE","quantity":None,"uom":None,"owners":list(owners.values())}
    if len(uoms)!=1:
        return {"status":"BLOCKED_MIXED_UOM","quantity":None,"uom":None,"owners":list(owners.values())}
    return {
        "status":"READY",
        "quantity":sum((_d(x["quantity"]) for x in usable),Decimal("0")),
        "uom":next(iter(uoms)),
        "owners":list(owners.values()),
    }


def _family_receipt_events(cur, family_id: int, data_day_limit: int = 180) -> list[dict[str,Any]]:
    days=source_data_days(
        cur,"movement",limit=max(1,min(int(data_day_limit),365)),
        up_to=completed_through_date(),
    )
    canonical={x["date"]:int(x["file_id"]) for x in days}
    if not canonical:
        return []
    file_ids=sorted(set(canonical.values()))
    ph=",".join(["%s"]*len(file_ids))
    cur.execute(
        f"""SELECT file_id,raw_id,source_row_number,article_id,article_number,
                   movement_type,posting_date,entry_quantity,entry_uom_code,
                   base_quantity,base_uom_code,amount_local_currency,
                   article_document,purchase_order,vendor_code
            FROM movement_history
            WHERE family_id=%s
              AND file_id IN ({ph})
              AND movement_type IN ('101','102','107','108','109','110')
            ORDER BY posting_date,file_id,raw_id,source_row_number""",
        (int(family_id),*file_ids),
    )
    rows=[
        r for r in cur.fetchall()
        if r.get("posting_date") in canonical and canonical[r["posting_date"]]==int(r["file_id"])
    ]
    groups: dict[tuple[Any,...],list[dict[str,Any]]] = {}
    for r in rows:
        key=(
            r.get("posting_date"),r.get("article_id"),r.get("article_number"),
            r.get("purchase_order"),r.get("article_document"),
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
        qty=None; uom=None; qty_basis=None
        if len(entry_uoms)==1 and any(x.get("entry_quantity") is not None for x in chosen):
            qty=sum((_d(x.get("entry_quantity")) for x in chosen),Decimal("0"))
            uom=next(iter(entry_uoms)); qty_basis="ENTRY"
        elif len(base_uoms)==1 and any(x.get("base_quantity") is not None for x in chosen):
            qty=sum((_d(x.get("base_quantity")) for x in chosen),Decimal("0"))
            uom=next(iter(base_uoms)); qty_basis="BASE"

        events.append({
            "posting_date":key[0],
            "article_id":key[1],
            "article_number":key[2],
            "purchase_order":key[3],
            "article_document":key[4],
            "vendor_code":next((x.get("vendor_code") for x in chosen if x.get("vendor_code")),None),
            "receipt_quantity":qty,
            "receipt_uom":uom,
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


def _delivery_pattern(receipt_events: list[dict[str,Any]], after_date: date | None = None) -> dict[str,Any]:
    dates=sorted({
        x["posting_date"]
        for x in receipt_events
        if x.get("posting_date")
        and x.get("receipt_quantity") is not None
        and Decimal(str(x.get("receipt_quantity"))) > 0
    })
    if not dates:
        return {
            "observed_delivery_days":[],
            "frequency":"NO_DATA",
            "median_gap_days":None,
            "next_expected_delivery_date":None,
            "confidence":"NONE",
        }
    counts=Counter(d.weekday() for d in dates)
    observed=[
        {"weekday":WEEKDAY_NAMES[k],"weekday_number":k,"receipt_date_count":v}
        for k,v in sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))
    ]
    gaps=[(b-a).days for a,b in zip(dates,dates[1:])]
    med=float(median(gaps)) if gaps else None
    total=len(dates)
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
            confidence="MEDIUM"

    anchor=after_date or business_today()
    next_expected=None
    if expected_weekdays:
        candidates=[
            anchor+timedelta(days=(wd-anchor.weekday())%7)
            for wd in expected_weekdays
        ]
        next_expected=min(candidates)

    return {
        "observed_delivery_days":observed,
        "receipt_date_count":total,
        "frequency":frequency,
        "median_gap_days":med,
        "expected_weekdays":expected_weekdays,
        "next_expected_delivery_date":next_expected,
        "confidence":confidence,
        "basis":"CANONICAL_COMPLETED_MOVEMENT_RECEIPT_DATES",
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
        categories=sorted({str(x.get("product_class")) for x in upcs if x.get("product_class")})
        category=categories[0] if len(categories)==1 else ("MIXED" if categories else None)
        effective_oh=_family_effective_oh(cur,upcs)

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
                "qty_7d":m7["sold_quantity"],
                "supported_days_7d":m7["supported_day_count"],
                "qty_28d":m28["sold_quantity"],
                "supported_days_28d":m28["supported_day_count"],
            })
        related.sort(key=lambda x:(_readiness_rank(x.get("readiness")),-float(x.get("qty_28d") or 0),str(x.get("name") or "")))
        cur.close()

    return {
        "contract_version":"WEBAPP_V2_FAMILY_V1",
        "family_article_number":family.get("main_article_number"),
        "family_article_name":family.get("family_description"),
        "family_id":fid,
        "category":category,
        "receiving_ordering_articles":articles,
        "current_effective_oh":effective_oh,
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
        "related_upc_sort":["READINESS","QTY_28_SUPPORTED_DAYS_DESC"],
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
        m7=_sales_metric(cur,int(row["upc_id"]),7)
        m28=_sales_metric(cur,int(row["upc_id"]),28)
        cur.close()
    return {
        "contract_version":"WEBAPP_V2_UPC_V1",
        "upc":row.get("ean_upc"),
        "upc_name":row.get("selling_description"),
        "category":row.get("product_class"),
        "readiness":row.get("quick_check_status"),
        "family_article_number":row.get("main_article_number"),
        "family_article_name":row.get("family_description"),
        "current_price":row.get("current_price"),
        "current_price_type":row.get("current_price_type"),
        "qty_7d":m7,
        "qty_28d":m28,
        "actions":["FAMILY_ARTICLE","PRICE","ORDERING"],
    }


def price_analysis(upc: str, trend_supported_days: int = 90) -> dict[str,Any]:
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
        upc_id=int(row["upc_id"])
        result={
            "contract_version":"WEBAPP_V2_PRICE_V1",
            "upc":row.get("ean_upc"),
            "name":row.get("selling_description"),
            "category":row.get("product_class"),
            "readiness":row.get("quick_check_status"),
            "current":{
                "price":row.get("current_price"),
                "price_type":row.get("current_price_type"),
                "price_as_of":row.get("current_price_asof_date"),
                "cost":row.get("current_cost_per_selling_unit"),
                "cost_uom":row.get("selling_uom"),
                "cost_date":row.get("cost_date"),
                "cost_source":row.get("cost_source"),
                "gp_pct":row.get("gp_pct_current"),
                "gp_per_day_7d":row.get("gp_per_day_7d"),
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
            "price_vs_sales_trend":_price_sales_trend(cur,upc_id,trend_supported_days),
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


def _selling_equivalent_effective_oh(cur, row: dict[str,Any]) -> dict[str,Any]:
    ctx=_system_oh_context(cur,row)
    if not ctx:
        return {"status":"OH_NOT_AVAILABLE","quantity":None,"uom":row.get("selling_uom")}
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
) -> dict[str,Any]:
    days=_canonical_sales_days(cur,limit=max(1,min(int(supported_day_count),365)))
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


def _family_regular_baseline(
    cur,
    upc_rows: list[dict[str,Any]],
    supported_day_limit: int=28,
) -> dict[str,Any]:
    s=_family_sales_series(cur,upc_rows,supported_day_limit)
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
        classes=("FRESH",) if kind=="FRESH" else ("FROZEN",)
        ph=",".join(["%s"]*len(classes))
        cur.execute(
            f"""SELECT DISTINCT family_id,main_article_number,family_description
                FROM quick_check_current
                WHERE UPPER(COALESCE(product_class,'')) IN ({ph})
                ORDER BY family_description,main_article_number""",
            classes,
        )
        families=cur.fetchall()
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

            m28=_family_sales_series(cur,rows,28)
            m7=_family_sales_series(cur,rows,7)
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
            if not active_28 or dos is None or dos>=Decimal("7"):
                continue

            regular=_family_regular_baseline(cur,rows,28)
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
        "category_scope":["FRESH"] if kind=="FRESH" else ["FROZEN"],
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

