from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from difflib import SequenceMatcher
from decimal import Decimal
import json
import inspect
import threading
import time
from typing import Any

from business_clock import business_today, completed_through_date
from data_coverage import source_data_days
from coverage_backfill import canonical_pos_qty_by_upc
from db import db_conn
from manual_overrides import USER_CONFIRMED_SELLING_ARTICLE_OVERRIDES_20260930
from phase3 import (
    PRICE_TYPE_PRIORITY,
    _current_price as _live_current_price,
    _price_list_upload_business_date,
)
from webapp_v2_runtime import (
    _batch_daily_sales_by_price_type,
    _batch_sales_metric,
    _canonical_report_date_sales,
    _delivery_pattern,
    _delivery_day_evidence,
    _family_effective_oh,
    _family_receipt_events,
    _family_receipt_events_bulk,
    _ordering_candidate_families,
    _gp_day_price_suggestion_from_batch,
    _performance_cost_for_day,
    _performance_range_cost_rows,
    bulk_ordering_suggestions,
    performance_report,
    _numeric_key,
    _safe_qty_uom,
    _seafood_upc_group_signature,
)


def _fallback_selling_article_compatible(
    prefix: str,
    article_number: str,
    article_description: str,
) -> bool:
    """Reject only deterministic Seafood fallback channel conflicts.

    Exact Article Manual / user-confirmed mappings are resolved before this
    helper. Fallback guards are intentionally conservative: 240 and 245 are
    regular selling channels and cannot inherit another structural channel or a
    SERVICE article. 249 is not hard-restricted because valid service lineage
    can legitimately resolve to several SAP Article number families (1549xxx,
    20xxxxx, Family/Main, etc.) when supported by 317/318 or other evidence.
    """
    p = str(prefix or "")
    art = str(article_number or "")
    raw = str(article_description or "").upper()
    desc = " ".join("".join(ch if ch.isalnum() else " " for ch in raw).split())
    is_service_desc = "SERVICE" in desc

    if p == "240":
        if art.startswith("1545") or art.startswith("1549"):
            return False
        if is_service_desc:
            return False

    if p == "245":
        if art.startswith("1540") or art.startswith("1549"):
            return False
        if is_service_desc:
            return False

    return True


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _bulk_live_current_prices(cur, rows: list[dict[str, Any]]) -> dict[int, dict[str, Any] | None]:
    """Resolve CURRENT price for many Quick Check rows without N×SQL fan-out.

    The authority remains identical to phase3._current_price:
      newest applicable Price List vs latest completed SINGLE_DATE sold event;
      newer business-date evidence wins and Price List wins same-day ties.

    Canonical upc_id is handled in bulk. 249/service rows that need raw-EAN
    lineage fall back to the full resolver individually.
    """
    targets = {
        int(r["upc_id"]): str(r.get("ean_upc") or "").strip()
        for r in rows
        if r.get("upc_id") is not None
    }
    if not targets:
        return {}

    ids = list(targets)
    current_day = business_today()
    completed_day = completed_through_date()
    config_by_id: dict[int, dict[str, Any]] = {}

    # Match phase3 semantics: inspect accepted Price List files newest-first,
    # and for each UPC use the newest file containing that UPC.
    cur.execute(
        """SELECT file_id,upload_timestamp,report_generated_at
           FROM ingest_file
           WHERE source_type='price_list'
             AND processing_status='INGESTED'
             AND error_count=0
             AND duplicate_of_file_id IS NULL
           ORDER BY COALESCE(upload_timestamp,report_generated_at) DESC,file_id DESC
           LIMIT 12"""
    )
    price_files = cur.fetchall()
    unresolved = set(ids)
    for pf in price_files:
        if not unresolved:
            break
        uid_list = sorted(unresolved)
        ph = ",".join(["%s"] * len(uid_list))
        cur.execute(
            f"""SELECT p.upc_id,p.configured_price,p.price_type,p.source_since_date,
                       p.snapshot_at,p.file_id,f.upload_timestamp
                FROM price_list_observation p
                JOIN ingest_file f ON f.file_id=p.file_id
                WHERE p.file_id=%s
                  AND p.upc_id IN ({ph})
                  AND p.configured_price>0
                  AND (p.source_since_date IS NULL OR p.source_since_date<=%s)""",
            (int(pf["file_id"]), *uid_list, current_day),
        )
        grouped: dict[int, list[dict[str, Any]]] = {}
        for pr in cur.fetchall():
            if pr.get("upc_id") is None:
                continue
            grouped.setdefault(int(pr["upc_id"]), []).append(pr)
        for uid, candidates in grouped.items():
            candidates.sort(
                key=lambda x: PRICE_TYPE_PRIORITY.get(
                    str(x.get("price_type") or "").upper(), 0
                ),
                reverse=True,
            )
            chosen = candidates[0]
            if chosen.get("upload_timestamp") is None:
                chosen["upload_timestamp"] = pf.get("upload_timestamp")
            config_by_id[uid] = chosen
            unresolved.discard(uid)

    pos_by_id: dict[int, dict[str, Any]] = {}
    if completed_day is not None and ids:
        ph = ",".join(["%s"] * len(ids))
        # Latest sold day for every canonical UPC in one query, then aggregate
        # that day's price types in one second bulk query.
        cur.execute(
            f"""SELECT s.upc_id,MAX(s.period_end_date) AS sold_date
                FROM sales_period_observation s
                JOIN ingest_file f ON f.file_id=s.file_id
                WHERE s.upc_id IN ({ph})
                  AND s.temporal_grain='SINGLE_DATE'
                  AND s.period_start_date=s.period_end_date
                  AND s.period_end_date<=%s
                  AND s.sold_quantity<>0
                  AND f.source_type='sales_by_price_type'
                  AND f.processing_status='INGESTED'
                  AND f.error_count=0
                  AND f.duplicate_of_file_id IS NULL
                  AND f.date_semantics_status='RESOLVED'
                GROUP BY s.upc_id""",
            (*ids, completed_day),
        )
        latest_rows = [
            x for x in cur.fetchall()
            if x.get("upc_id") is not None and x.get("sold_date") is not None
        ]
        if latest_rows:
            clauses = []
            args: list[Any] = []
            for x in latest_rows:
                clauses.append("(s.upc_id=%s AND s.period_end_date=%s)")
                args.extend([int(x["upc_id"]), x["sold_date"]])
            cur.execute(
                f"""SELECT s.upc_id,s.period_end_date,
                           UPPER(TRIM(s.price_type)) AS price_type,
                           SUM(s.sales_amount) AS sales_amount,
                           SUM(s.sold_quantity) AS sold_quantity
                    FROM sales_period_observation s
                    JOIN ingest_file f ON f.file_id=s.file_id
                    WHERE ({' OR '.join(clauses)})
                      AND s.temporal_grain='SINGLE_DATE'
                      AND s.period_start_date=s.period_end_date
                      AND s.sold_quantity<>0
                      AND f.source_type='sales_by_price_type'
                      AND f.processing_status='INGESTED'
                      AND f.error_count=0
                      AND f.duplicate_of_file_id IS NULL
                      AND f.date_semantics_status='RESOLVED'
                    GROUP BY s.upc_id,s.period_end_date,UPPER(TRIM(s.price_type))""",
                tuple(args),
            )
            sold_grouped: dict[int, list[dict[str, Any]]] = {}
            for sr in cur.fetchall():
                if sr.get("upc_id") is None:
                    continue
                sold_grouped.setdefault(int(sr["upc_id"]), []).append(sr)
            for uid, candidates in sold_grouped.items():
                candidates = [x for x in candidates if _d(x.get("sold_quantity")) != 0]
                if not candidates:
                    continue
                candidates.sort(
                    key=lambda x: PRICE_TYPE_PRIORITY.get(
                        str(x.get("price_type") or "").upper(), 0
                    ),
                    reverse=True,
                )
                chosen = candidates[0]
                qty = _d(chosen.get("sold_quantity"))
                pos_by_id[uid] = {
                    "price": _d(chosen.get("sales_amount")) / qty,
                    "type": chosen.get("price_type") or "UNKNOWN",
                    "source": "POS_CALCULATED",
                    "date": chosen.get("period_end_date"),
                }

    out: dict[int, dict[str, Any] | None] = {}
    for uid, ean in targets.items():
        config = config_by_id.get(uid)
        pos = pos_by_id.get(uid)
        price_date = None
        if config is not None:
            if config.get("upload_timestamp") is not None:
                price_date = _price_list_upload_business_date(config.get("upload_timestamp"))
            elif config.get("snapshot_at") is not None:
                price_date = config.get("snapshot_at").date()

        if config is not None and price_date is not None and (
            pos is None or price_date >= pos.get("date")
        ):
            out[uid] = {
                "price": config.get("configured_price"),
                "type": config.get("price_type"),
                "source": "PRICE_LIST",
                "date": price_date,
            }
        elif pos is not None:
            out[uid] = pos
        elif config is not None:
            out[uid] = {
                "price": config.get("configured_price"),
                "type": config.get("price_type"),
                "source": "PRICE_LIST",
                "date": price_date,
            }
        else:
            out[uid] = None

        # 249 service POS lineage can live under raw service EAN aliases. Keep
        # the proven alias-aware resolver only for those exceptional rows.
        numeric = "".join(ch for ch in ean if ch.isdigit()).lstrip("0")
        if numeric.startswith("249"):
            alias_resolved = _live_current_price(cur, uid, ean)
            if alias_resolved is not None:
                out[uid] = alias_resolved

    return out


def _published_family_oh_fallback(children: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the last published family OH only when child snapshots agree.

    quick_check_current repeats a family-owned OH on each related UPC.  Around
    midnight, read-time roll-forward can temporarily become blocked by the new
    completed-day requirement before the prior day's MVT is uploaded.  In that
    case, keep the last published effective family OH visible, but mark it as
    LAST_PUBLISHED rather than pretending it is current-through-today.
    """
    values: list[tuple[Decimal, str, Any]] = []
    for child in children:
        qty = child.get('current_oh')
        uom = str(child.get('current_oh_uom') or '').strip().upper()
        if qty is None or not uom:
            continue
        values.append((_d(qty), uom, child.get('oh_date')))
    if not values:
        return None
    uoms = {x[1] for x in values}
    qtys = {x[0] for x in values}
    if len(uoms) != 1 or len(qtys) != 1:
        return None
    dates = [str(x[2]) for x in values if x[2] is not None]
    return {
        'status': 'LAST_PUBLISHED',
        'quantity': values[0][0],
        'uom': values[0][1],
        'source': 'QUICK_CHECK_CURRENT_PUBLISHED_EFFECTIVE_OH',
        'as_of_date': max(dates) if dates else None,
    }


def _receipt_stage_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_type.setdefault(str(row.get("movement_type") or ""), []).append(row)
    if by_type.get("101") or by_type.get("102"):
        return (by_type.get("101") or []) + (by_type.get("102") or []), "101_102_DIRECT_GR_NET"
    if by_type.get("107") or by_type.get("108"):
        return (by_type.get("107") or []) + (by_type.get("108") or []), "107_108_BLOCKED_GR_NET"
    return (by_type.get("109") or []) + (by_type.get("110") or []), "109_110_RELEASE_FALLBACK"


def _last_receipt_base_summary(cur, family_id: int) -> dict[str, Any]:
    """Return the latest positive receipt expressed strictly in movement base UOM.

    Entry/receiving UOM is deliberately not substituted when base quantity is absent.
    This keeps the Ordering Review main list aligned to the user's requested Base UOM.
    """
    days = source_data_days(
        cur,
        "movement",
        limit=180,
        up_to=completed_through_date(),
    )
    canonical = {x["date"]: int(x["file_id"]) for x in days}
    if not canonical:
        return {
            "date": None,
            "quantity": None,
            "base_uom": None,
            "receiving_article": None,
            "receiving_articles": [],
            "status": "NO_MOVEMENT_DATA",
        }

    file_ids = sorted(set(canonical.values()))
    ph = ",".join(["%s"] * len(file_ids))
    cur.execute(
        f"""SELECT file_id,raw_id,source_row_number,article_id,article_number,
                   movement_type,posting_date,entry_quantity,entry_uom_code,
                   base_quantity,base_uom_code,article_document,purchase_order
            FROM movement_history
            WHERE family_id=%s
              AND file_id IN ({ph})
              AND movement_type IN ('101','102','107','108','109','110')
            ORDER BY posting_date DESC,file_id DESC,raw_id DESC,source_row_number DESC""",
        (int(family_id), *file_ids),
    )
    rows = [
        r for r in cur.fetchall()
        if r.get("posting_date") in canonical
        and canonical[r["posting_date"]] == int(r["file_id"])
    ]

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for r in rows:
        key = (
            r.get("posting_date"),
            r.get("article_id"),
            r.get("article_number"),
            r.get("purchase_order"),
            r.get("article_document"),
        )
        groups.setdefault(key, []).append(r)

    events: list[dict[str, Any]] = []
    for key, group in groups.items():
        chosen, stage = _receipt_stage_rows(group)
        base_uoms = {
            str(x.get("base_uom_code") or "").strip().upper()
            for x in chosen
            if x.get("base_uom_code")
        }
        if len(base_uoms) != 1:
            continue
        if not any(x.get("base_quantity") is not None for x in chosen):
            continue
        qty = sum((_d(x.get("base_quantity")) for x in chosen), Decimal("0"))
        if qty <= 0:
            continue
        events.append(
            {
                "date": key[0],
                "article_id": key[1],
                "article_number": key[2],
                "quantity": qty,
                "base_uom": next(iter(base_uoms)),
                "stage_basis": stage,
            }
        )

    if not events:
        return {
            "date": None,
            "quantity": None,
            "base_uom": None,
            "receiving_article": None,
            "receiving_articles": [],
            "status": "BASE_QTY_UNAVAILABLE",
        }

    last_date = max(x["date"] for x in events)
    last = [x for x in events if x["date"] == last_date]
    article_groups: dict[str, dict[str, Any]] = {}
    for x in last:
        art = str(x.get("article_number") or "").strip() or "UNKNOWN"
        slot = article_groups.setdefault(
            art,
            {"article_number": art, "quantity": Decimal("0"), "base_uom": x["base_uom"]},
        )
        if slot["base_uom"] == x["base_uom"]:
            slot["quantity"] += _d(x["quantity"])
        else:
            slot["quantity"] = None
            slot["base_uom"] = None

    articles = sorted(
        article_groups.values(),
        key=lambda x: (-float(x.get("quantity") or 0), str(x.get("article_number") or "")),
    )
    primary = articles[0] if articles else None

    same_uom = {x.get("base_uom") for x in articles if x.get("base_uom")}
    total_qty = None
    total_uom = None
    if articles and len(same_uom) == 1 and all(x.get("quantity") is not None for x in articles):
        total_qty = sum((_d(x["quantity"]) for x in articles), Decimal("0"))
        total_uom = next(iter(same_uom))

    return {
        "date": last_date,
        "quantity": total_qty,
        "base_uom": total_uom,
        "receiving_article": primary.get("article_number") if primary else None,
        "receiving_articles": articles,
        "status": "READY" if total_qty is not None and total_uom else "MIXED_BASE_UOM",
    }


def _last_receipt_base_summary_from_events(events: list[dict[str,Any]]) -> dict[str,Any]:
    """Build the Base-UOM last-receipt summary from already-loaded family events."""
    valid=[
        x for x in events
        if x.get("posting_date") is not None
        and x.get("base_receipt_quantity") is not None
        and _d(x.get("base_receipt_quantity"))>0
        and x.get("base_receipt_uom")
    ]
    if not valid:
        return {
            "date":None,
            "quantity":None,
            "base_uom":None,
            "receiving_article":None,
            "receiving_articles":[],
            "status":"BASE_QTY_UNAVAILABLE",
        }

    last_date=max(x["posting_date"] for x in valid)
    last=[x for x in valid if x.get("posting_date")==last_date]
    article_groups: dict[str,dict[str,Any]] = {}
    for x in last:
        art=str(x.get("article_number") or "").strip() or "UNKNOWN"
        slot=article_groups.setdefault(
            art,
            {
                "article_number":art,
                "quantity":Decimal("0"),
                "base_uom":str(x.get("base_receipt_uom") or "").upper() or None,
            },
        )
        uom=str(x.get("base_receipt_uom") or "").upper() or None
        if slot.get("base_uom")==uom:
            slot["quantity"]+=_d(x.get("base_receipt_quantity"))
        else:
            slot["quantity"]=None
            slot["base_uom"]=None

    articles=sorted(
        article_groups.values(),
        key=lambda x:(-float(x.get("quantity") or 0),str(x.get("article_number") or "")),
    )
    primary=articles[0] if articles else None
    same_uom={x.get("base_uom") for x in articles if x.get("base_uom")}
    total_qty=None
    total_uom=None
    if articles and len(same_uom)==1 and all(x.get("quantity") is not None for x in articles):
        total_qty=sum((_d(x["quantity"]) for x in articles),Decimal("0"))
        total_uom=next(iter(same_uom))

    return {
        "date":last_date,
        "quantity":total_qty,
        "base_uom":total_uom,
        "receiving_article":primary.get("article_number") if primary else None,
        "receiving_articles":articles,
        "status":"READY" if total_qty is not None and total_uom else "MIXED_BASE_UOM",
    }


def _fallback_receiving_article(cur, family_id: int, family_article: str | None) -> str | None:
    cur.execute(
        """SELECT a.article_number
           FROM bridge_article_family baf
           JOIN article a ON a.article_id=baf.article_id
           WHERE baf.family_id=%s
             AND baf.mapping_status='CONFIRMED'
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           ORDER BY CASE baf.relationship_type WHEN 'SUB' THEN 0 WHEN 'MAIN' THEN 1 ELSE 2 END,
                    baf.is_primary DESC,a.article_number
           LIMIT 1""",
        (int(family_id),),
    )
    row = cur.fetchone()
    return str(row.get("article_number")) if row and row.get("article_number") else family_article


def _frequency_label(pattern: dict[str, Any]) -> str:
    freq = str(pattern.get("frequency") or "NO_DATA").upper()
    observed = pattern.get("observed_delivery_days") or []
    weekdays = [str(x.get("weekday")) for x in observed[:2] if x.get("weekday")]
    if freq == "WEEKLY" and weekdays:
        return f"Weekly · {weekdays[0]} delivery"
    if freq == "MULTIPLE_PER_WEEK" and weekdays:
        return "Multiple/week · " + " / ".join(weekdays)
    if freq == "IRREGULAR":
        return "Irregular"
    return "No receipt pattern"


def _suggestion_reason(row: dict[str, Any], pattern: dict[str, Any], receipt: dict[str, Any]) -> list[dict[str, str]]:
    uom = str(row.get("uom") or "")
    reasons = [
        {
            "title": "Family demand",
            "detail": (
                f"7D family movement {row.get('qty_7d')} {uom}; "
                f"28D family movement {row.get('qty_28d')} {uom}."
            ),
        },
        {
            "title": "Inventory position",
            "detail": f"Usable Family OH for ordering: {row.get('ordering_oh_used')} {uom}; DOS {row.get('dos')}."
        },
        {
            "title": "Coverage window",
            "detail": (
                f"Forecast demand through the next delivery cycle is {row.get('forecast_total_usage')} {uom}; "
                f"suggested coming delivery quantity is {row.get('suggested_order_qty')} {row.get('suggested_order_uom') or uom}."
            ),
        },
        {
            "title": "Receiving cadence",
            "detail": _frequency_label(pattern),
        },
    ]
    if receipt.get("date"):
        reasons.append(
            {
                "title": "Last receipt",
                "detail": (
                    f"Last receipt {receipt.get('date')} · {receipt.get('quantity')} "
                    f"{receipt.get('base_uom') or ''} in Base UOM."
                ),
            }
        )
    return reasons


def ordering_review(
    category: str = "ALL",
    delivery_date: date | None = None,
    *,
    best_available_delivery_evidence: bool = False,
) -> dict[str, Any]:
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_FRESH_OR_FROZEN")

    kinds = [cat] if cat != "ALL" else ["FRESH", "FROZEN"]
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    inputs: dict[str, Any] = {}

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        expected_through=completed_through_date()
        source_limit=60 if best_available_delivery_evidence else 1
        pos_latest_days=source_data_days(
            cur,
            "sales_by_price_type",
            limit=source_limit,
            up_to=expected_through,
        )
        mvt_latest_days=source_data_days(
            cur,
            "movement",
            limit=source_limit,
            up_to=expected_through,
        )
        pos_through=pos_latest_days[0]["date"] if pos_latest_days else None
        mvt_through=mvt_latest_days[0]["date"] if mvt_latest_days else None
        missing_required_sources=[]
        if pos_through!=expected_through:
            missing_required_sources.append("POS")
        if mvt_through!=expected_through:
            missing_required_sources.append("MVT")

        if best_available_delivery_evidence:
            pos_dates={x["date"] for x in pos_latest_days if x.get("date") is not None}
            mvt_dates={x["date"] for x in mvt_latest_days if x.get("date") is not None}
            common_dates=sorted(pos_dates & mvt_dates)
            common_data_through=common_dates[-1] if common_dates else None
        else:
            available_dates=[x for x in (pos_through,mvt_through) if x is not None]
            common_data_through=min(available_dates) if len(available_dates)==2 else None
        stale_days=(
            max(0,(expected_through-common_data_through).days)
            if common_data_through is not None else None
        )
        can_estimate=common_data_through is not None
        ordering_data_health={
            "status":(
                "CURRENT"
                if not missing_required_sources
                else ("STALE_ESTIMATE_AVAILABLE" if can_estimate else "UNAVAILABLE")
            ),
            "decision_mode":(
                "CURRENT"
                if not missing_required_sources
                else ("STALE_ESTIMATE" if can_estimate else "UNAVAILABLE")
            ),
            "expected_through":expected_through,
            "data_through":common_data_through,
            "stale_calendar_days":stale_days,
            "pos_data_through":pos_through,
            "movement_data_through":mvt_through,
            "missing_required_sources":missing_required_sources,
            "rule":"ORDERING_USES_LATEST_COMMON_POS_MVT_AS_ESTIMATE_WHEN_CURRENT_COMPLETED_DAY_IS_MISSING",
            "warning":(
                None
                if not missing_required_sources
                else (
                    f"Estimate uses existing data through {common_data_through}; "
                    f"required completed data is through {expected_through}."
                    if can_estimate else
                    "Ordering estimate unavailable because POS and MVT do not have a common usable date."
                )
            ),
        }

        if not can_estimate:
            cur.close()
            return {
                "contract_version":"BACKOFFICE_ORDERING_REVIEW_V5_STALE_ESTIMATE",
                "category":cat,
                "selected_delivery_date":delivery_date,
                "selected_delivery_weekday":(
                    ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][delivery_date.weekday()]
                    if delivery_date else None
                ),
                "analysis_status":"UNAVAILABLE",
                "data_health":ordering_data_health,
                "count":0,
                "rows":[],
                "skipped":[],
                "skipped_breakdown":{},
                "inputs":{},
                "rules":{
                    "decision_level":"FAMILY_ARTICLE_AND_RECEIVING_ARTICLE",
                    "stale_estimate_allowed":True,
                    "requires_common_pos_mvt_date":True,
                },
            }

        # Reuse the same canonical movement window for every suggested family.
        # The former path re-queried coverage and movement rows twice per family.
        receipt_days=source_data_days(
            cur,
            "movement",
            limit=180,
            up_to=common_data_through,
        )

        # Yipman 14-day calendar includes the prior 7 dates. Past selections
        # are actual canonical receipt history, not a retroactive order forecast.
        if (
            best_available_delivery_evidence
            and delivery_date is not None
            and delivery_date < business_today()
        ):
            history_rows: list[dict[str, Any]] = []
            movement_dates={x["date"] for x in receipt_days if x.get("date") is not None}
            for kind in kinds:
                candidate_families=_ordering_candidate_families(cur,kind)
                event_map=_family_receipt_events_bulk(
                    cur,
                    [int(x["family_id"]) for x in candidate_families],
                    data_days=receipt_days,
                )
                for fam in candidate_families:
                    fid=int(fam["family_id"])
                    day_events=[
                        x for x in (event_map.get(fid) or [])
                        if x.get("posting_date")==delivery_date
                        and x.get("receipt_quantity") is not None
                        and _d(x.get("receipt_quantity"))>0
                    ]
                    if not day_events:
                        continue

                    base_events=[
                        x for x in day_events
                        if x.get("base_receipt_quantity") is not None
                        and _d(x.get("base_receipt_quantity"))>0
                        and x.get("base_receipt_uom")
                    ]
                    base_uoms={
                        str(x.get("base_receipt_uom") or "").upper()
                        for x in base_events
                    }
                    if base_events and len(base_events)==len(day_events) and len(base_uoms)==1:
                        receipt_qty=sum(
                            (_d(x.get("base_receipt_quantity")) for x in base_events),
                            Decimal("0"),
                        )
                        receipt_uom=next(iter(base_uoms))
                        receipt_qty_basis="BASE_UOM"
                    else:
                        entry_uoms={
                            str(x.get("receipt_uom") or "").upper()
                            for x in day_events if x.get("receipt_uom")
                        }
                        if len(entry_uoms)==1 and all(
                            x.get("receipt_quantity") is not None for x in day_events
                        ):
                            receipt_qty=sum(
                                (_d(x.get("receipt_quantity")) for x in day_events),
                                Decimal("0"),
                            )
                            receipt_uom=next(iter(entry_uoms))
                            receipt_qty_basis="ENTRY_UOM"
                        else:
                            receipt_qty=None
                            receipt_uom="MIXED"
                            receipt_qty_basis="MIXED_UOM"

                    receiving_articles=sorted({
                        str(x.get("article_number") or "").strip()
                        for x in day_events
                        if str(x.get("article_number") or "").strip()
                    })
                    history_rows.append({
                        "family_id":fid,
                        "family_name":fam.get("family_description"),
                        "family_article":fam.get("main_article_number"),
                        "receiving_article":(
                            receiving_articles[0] if len(receiving_articles)==1
                            else (" + ".join(receiving_articles) if receiving_articles else None)
                        ),
                        "receiving_articles":receiving_articles,
                        "selected_delivery_date":delivery_date,
                        "delivery_day":[
                            "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
                        ][delivery_date.weekday()],
                        "category":kind,
                        "receipt_qty":receipt_qty,
                        "receipt_uom":receipt_uom,
                        "receipt_qty_basis":receipt_qty_basis,
                        "receipt_event_count":len(day_events),
                        "receipt_events":[
                            {
                                "article_number":x.get("article_number"),
                                "quantity":x.get("base_receipt_quantity")
                                if x.get("base_receipt_quantity") is not None
                                else x.get("receipt_quantity"),
                                "uom":x.get("base_receipt_uom")
                                or x.get("receipt_uom"),
                                "purchase_order":x.get("purchase_order"),
                                "vendor_code":x.get("vendor_code"),
                                "receipt_stage_basis":x.get("receipt_stage_basis"),
                            }
                            for x in day_events
                        ],
                    })

            history_rows.sort(
                key=lambda x:(
                    -float(x.get("receipt_qty") or 0),
                    str(x.get("family_name") or ""),
                )
            )
            selected_weekday=[
                "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
            ][delivery_date.weekday()]
            cur.close()
            return {
                "contract_version":"BACKOFFICE_ORDERING_REVIEW_V6_YIPMAN_HISTORY",
                "category":cat,
                "selected_delivery_date":delivery_date,
                "selected_delivery_weekday":selected_weekday,
                "analysis_status":"HISTORY_READY",
                "history_mode":True,
                "movement_date_available":delivery_date in movement_dates,
                "data_health":ordering_data_health,
                "count":len(history_rows),
                "rows":history_rows,
                "skipped":[],
                "skipped_breakdown":{},
                "inputs":{"history_date":delivery_date},
                "rules":{
                    "decision_level":"FAMILY_ARTICLE_AND_RECEIVING_ARTICLE",
                    "history_basis":"ACTUAL_CANONICAL_101_107_109_RECEIPTS_ON_SELECTED_DATE",
                    "receipt_quantity_basis":"BASE_UOM_WHEN_RECONCILABLE_ELSE_ENTRY_UOM",
                    "write_enabled":False,
                },
            }

        for kind in kinds:
            delivery_cache: dict[int, tuple[dict[str,Any],dict[str,Any],dict[str,Any]]] = {}
            eligible_family_ids: list[int] | None = None

            # Delivery-date mode must filter on receipt cadence before running
            # expensive 28D family demand / OH / baseline calculations.
            if delivery_date is not None:
                eligible_family_ids=[]
                candidate_families=_ordering_candidate_families(cur,kind)
                event_map=_family_receipt_events_bulk(
                    cur,
                    [int(x["family_id"]) for x in candidate_families],
                    data_days=receipt_days,
                )
                for fam in candidate_families:
                    fid=int(fam["family_id"])
                    events=event_map.get(fid) or []
                    receipt=_last_receipt_base_summary_from_events(events)
                    pattern=_delivery_pattern(
                        events,
                        after_date=delivery_date,
                        lookback_days=(180 if best_available_delivery_evidence else 84),
                    )
                    delivery_day=_delivery_day_evidence(pattern,delivery_date)
                    observed_count=int(delivery_day.get("observed_count") or 0)
                    best_available_match=bool(
                        best_available_delivery_evidence and observed_count>=1
                    )
                    if delivery_day.get("eligible") or best_available_match:
                        if best_available_match and not delivery_day.get("eligible"):
                            delivery_day=dict(delivery_day)
                            delivery_day["eligible"]=True
                            delivery_day["best_available_low_confidence"]=True
                            delivery_day["eligibility_rule"]="YIPMAN_ANY_OBSERVED_RECEIPT_ON_SELECTED_WEEKDAY_WITHIN_180_DAYS"
                        eligible_family_ids.append(fid)
                        delivery_cache[fid]=(receipt,pattern,delivery_day)
                    else:
                        skipped.append({
                            "family_id":fid,
                            "family_article_number":fam.get("main_article_number"),
                            "family_article_name":fam.get("family_description"),
                            "reason":"DELIVERY_DAY_NOT_OBSERVED_ENOUGH",
                            "delivery_date":delivery_date,
                            "delivery_day_evidence":delivery_day,
                        })

            # OH / movement evidence is only current through common_data_through.
            # Start forecast depletion on the next calendar day so every missing
            # day between the evidence date and the delivery date is covered.
            forecast_start_date=common_data_through+timedelta(days=1)
            bulk_kwargs: dict[str,Any] = {
                "ordering_date":forecast_start_date,
                "expected_delivery_date":delivery_date,
                "include_sufficient_stock":bool(delivery_date),
                "family_ids":eligible_family_ids,
            }
            supported=set(inspect.signature(bulk_ordering_suggestions).parameters)
            bulk_kwargs={k:v for k,v in bulk_kwargs.items() if k in supported}

            if delivery_date is not None and not eligible_family_ids:
                bulk={
                    "inputs":{"expected_delivery_date":delivery_date},
                    "suggestions":[],
                    "skipped":[],
                    "rules":{"delivery_prefilter_short_circuit":True},
                }
            else:
                bulk=bulk_ordering_suggestions(kind,**bulk_kwargs)

            inputs[kind] = bulk.get("inputs")
            skipped.extend(bulk.get("skipped") or [])
            for s in bulk.get("suggestions") or []:
                fid = int(s["family_id"])
                if delivery_date is not None:
                    cached=delivery_cache.get(fid)
                    if not cached:
                        # Compatibility with an older worker that cannot accept
                        # family_ids: never leak a nonmatching delivery family.
                        continue
                    receipt,pattern,delivery_day=cached
                else:
                    events = _family_receipt_events(cur, fid, data_days=receipt_days)
                    receipt = _last_receipt_base_summary_from_events(events)
                    pattern = _delivery_pattern(events)
                    delivery_day = None

                receiving_article = receipt.get("receiving_article") or _fallback_receiving_article(
                    cur, fid, str(s.get("family_article_number") or "") or None
                )
                row = {
                    "family_id": fid,
                    "family_name": s.get("family_article_name"),
                    "family_article": s.get("family_article_number"),
                    "receiving_article": receiving_article,
                    "oh": s.get("ordering_oh_used"),
                    "oh_uom": s.get("uom"),
                    "last_receipt_date": receipt.get("date"),
                    "last_receipt_qty_base": receipt.get("quantity"),
                    "last_receipt_base_uom": receipt.get("base_uom"),
                    "last_receipt_status": receipt.get("status"),
                    "ordering_frequency": _frequency_label(pattern),
                    "ordering_frequency_raw": pattern.get("frequency"),
                    "selected_delivery_date": delivery_date,
                    "delivery_day": delivery_day.get("weekday") if delivery_day else None,
                    "delivery_day_observed_count": delivery_day.get("observed_count") if delivery_day else None,
                    "delivery_day_receipt_count": delivery_day.get("receipt_date_count") if delivery_day else pattern.get("receipt_date_count"),
                    "delivery_day_confidence_pct": delivery_day.get("confidence_percent") if delivery_day else pattern.get("confidence_percent"),
                    "delivery_day_confidence": delivery_day.get("confidence") if delivery_day else pattern.get("confidence"),
                    "suggested_delivery_qty": s.get("suggested_order_qty"),
                    "suggested_delivery_uom": s.get("suggested_order_uom"),
                    "category": s.get("category"),
                    "data_status": ordering_data_health.get("status"),
                    "data_through": common_data_through,
                    "expected_through": expected_through,
                    "stale_calendar_days": stale_days,
                    "estimate_only": bool(missing_required_sources),
                    "attention": bool(
                        _d(s.get("dos")) < Decimal("3")
                        or _d(s.get("projected_oh_at_delivery")) < 0
                    ),
                    "details": {
                        "qty_7d": s.get("qty_7d"),
                        "qty_28d": s.get("qty_28d"),
                        "velocity_7d": s.get("velocity_7d"),
                        "dos": s.get("dos"),
                        "effective_oh_raw": s.get("effective_oh_raw"),
                        "ordering_oh_used": s.get("ordering_oh_used"),
                        "forecast_total_usage": s.get("forecast_total_usage"),
                        "forecast_usage_before_delivery": s.get("forecast_usage_before_delivery"),
                        "projected_oh_at_delivery": s.get("projected_oh_at_delivery"),
                        "regular_baseline": s.get("regular_baseline"),
                        "receiving_articles_on_last_receipt": receipt.get("receiving_articles"),
                        "delivery_pattern": pattern,
                        "delivery_day_evidence": delivery_day,
                        "reasons": _suggestion_reason(s, pattern, receipt)
                        + (
                            [{
                                "title":"Selected delivery day",
                                "detail":(
                                    f"Observed {delivery_day.get('weekday')} "
                                    f"{delivery_day.get('observed_count')}/{delivery_day.get('receipt_date_count')} receipt dates "
                                    f"in the recent {delivery_day.get('lookback_days')} day window · "
                                    f"{delivery_day.get('confidence_percent')}% confidence."
                                ),
                            }] if delivery_day else []
                        )
                        + (
                            [{
                                "title":"Data freshness",
                                "detail":(
                                    f"ESTIMATE using existing POS and MVT through {common_data_through}. "
                                    f"Required completed data is through {expected_through}. "
                                    f"Forecast coverage begins {forecast_start_date} so the missing "
                                    f"{stale_days} calendar day(s) are included before delivery."
                                ),
                            }] if missing_required_sources else []
                        ),
                    },
                }
                rows.append(row)
        cur.close()

    rows.sort(
        key=lambda x: (
            -float(x.get("suggested_delivery_qty") or 0),
            str(x.get("family_name") or ""),
        )
    )
    skipped_breakdown=dict(
        Counter(str(x.get("reason") or "UNKNOWN") for x in skipped)
    )
    if ordering_data_health["status"]=="CURRENT":
        analysis_status="READY" if rows else "READY_NO_ELIGIBLE_ITEMS"
    elif ordering_data_health["status"]=="STALE_ESTIMATE_AVAILABLE":
        analysis_status="READY_STALE_ESTIMATE" if rows else "READY_STALE_ESTIMATE_NO_ELIGIBLE_ITEMS"
    else:
        analysis_status="UNAVAILABLE"
    return {
        "contract_version": "BACKOFFICE_ORDERING_REVIEW_V5_STALE_ESTIMATE",
        "category": cat,
        "selected_delivery_date": delivery_date,
        "selected_delivery_weekday": (
            ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][delivery_date.weekday()]
            if delivery_date else None
        ),
        "analysis_status": analysis_status,
        "data_health": ordering_data_health,
        "count": len(rows),
        "rows": rows,
        "skipped": skipped,
        "skipped_breakdown": skipped_breakdown,
        "inputs": inputs,
        "rules": {
            "decision_level": "FAMILY_ARTICLE_AND_RECEIVING_ARTICLE",
            "selling_upcs_are_supporting_detail_only": True,
            "last_receipt_quantity_basis": "MOVEMENT_BASE_UOM_ONLY",
            "incoming_field_used": False,
            "write_enabled": False,
            "delivery_date_filter": "RECENT_12_WEEK_CANONICAL_101_107_109_WEEKDAY_EVIDENCE",
            "delivery_day_eligibility": (
                "ANY_OBSERVED_SELECTED_WEEKDAY_WITHIN_180_DAYS"
                if best_available_delivery_evidence
                else "EXPECTED_WEEKDAY_OR_AT_LEAST_2_RECEIPTS_AND_25_PERCENT_SHARE"
            ),
            "delivery_evidence_lookback_days": 180 if best_available_delivery_evidence else 84,
            "best_available_delivery_evidence": bool(best_available_delivery_evidence),
            "delivery_day_prefilter_before_heavy_math": True,
            "stale_estimate_allowed": True,
            "stale_estimate_basis": "LATEST_COMMON_CANONICAL_POS_AND_MVT_DATE",
            "stale_forecast_starts_day_after_data_through": True,
        },
    }




_ORDERING_REVIEW_CACHE_LOCK = threading.Lock()
_ORDERING_REVIEW_CACHE_VALUES: dict[str,dict[str,Any]] = {}
_ORDERING_REVIEW_CACHE_AT: dict[str,float] = {}
_ORDERING_REVIEW_REFRESHING: set[str] = set()
_ORDERING_REVIEW_LAST_ERROR: dict[str,str] = {}
_ORDERING_REVIEW_CACHE_TTL_SECONDS = 120.0


def _ordering_review_cache_key(
    category: str,
    delivery_date: date,
    *,
    best_available_delivery_evidence: bool = False,
) -> str:
    mode="YIPMAN180" if best_available_delivery_evidence else "STANDARD84"
    return f"V6|{mode}|{str(category or 'ALL').upper()}|{delivery_date.isoformat()}"


def _ensure_ordering_review_cache_table(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS backoffice_ordering_review_cache (
             cache_key VARCHAR(96) NOT NULL PRIMARY KEY,
             payload_json LONGTEXT NOT NULL,
             generated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
             ON UPDATE CURRENT_TIMESTAMP(6)
           )"""
    )


def _load_persisted_ordering_review(cache_key: str) -> dict[str,Any] | None:
    try:
        with db_conn() as conn:
            cur=conn.cursor(dictionary=True)
            _ensure_ordering_review_cache_table(cur)
            conn.commit()
            cur.execute(
                """SELECT payload_json,generated_at
                   FROM backoffice_ordering_review_cache
                   WHERE cache_key=%s
                   LIMIT 1""",
                (cache_key,),
            )
            row=cur.fetchone()
            cur.close()
        if not row:
            return None
        payload=json.loads(row.get("payload_json") or "{}")
        if not isinstance(payload,dict):
            return None
        payload["persisted_generated_at"]=row.get("generated_at")
        return payload
    except Exception:
        return None


def _persist_ordering_review(cache_key: str, value: dict[str,Any]) -> None:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_ordering_review_cache_table(cur)
        cur.execute(
            """INSERT INTO backoffice_ordering_review_cache(cache_key,payload_json)
               VALUES (%s,%s)
               ON DUPLICATE KEY UPDATE
                 payload_json=VALUES(payload_json),
                 generated_at=CURRENT_TIMESTAMP(6)""",
            (cache_key,json.dumps(value,default=str)),
        )
        conn.commit()
        cur.close()


def _ordering_review_refresh_worker(
    category: str,
    delivery_date: date,
    cache_key: str,
    best_available_delivery_evidence: bool = False,
) -> None:
    try:
        _ORDERING_REVIEW_LAST_ERROR.pop(cache_key,None)
        value=ordering_review(
            category=category,
            delivery_date=delivery_date,
            best_available_delivery_evidence=best_available_delivery_evidence,
        )
        _persist_ordering_review(cache_key,value)
        with _ORDERING_REVIEW_CACHE_LOCK:
            _ORDERING_REVIEW_CACHE_VALUES[cache_key]=value
            _ORDERING_REVIEW_CACHE_AT[cache_key]=time.monotonic()
    except Exception as exc:
        _ORDERING_REVIEW_LAST_ERROR[cache_key]=f"{type(exc).__name__}: {exc}"[:1000]
    finally:
        with _ORDERING_REVIEW_CACHE_LOCK:
            _ORDERING_REVIEW_REFRESHING.discard(cache_key)


def _request_ordering_review_refresh(
    category: str,
    delivery_date: date,
    cache_key: str,
    best_available_delivery_evidence: bool = False,
) -> None:
    with _ORDERING_REVIEW_CACHE_LOCK:
        if cache_key in _ORDERING_REVIEW_REFRESHING:
            return
        _ORDERING_REVIEW_REFRESHING.add(cache_key)
    threading.Thread(
        target=_ordering_review_refresh_worker,
        args=(category,delivery_date,cache_key,best_available_delivery_evidence),
        name=f"ordering-review-{delivery_date.isoformat()}",
        daemon=True,
    ).start()


def cached_ordering_review(
    category: str = "ALL",
    delivery_date: date | None = None,
    force: bool = False,
    *,
    best_available_delivery_evidence: bool = False,
) -> dict[str,Any]:
    """Return delivery-date Ordering immediately; heavy analysis refreshes in background."""
    if delivery_date is None:
        return ordering_review(
            category=category,
            delivery_date=None,
            best_available_delivery_evidence=best_available_delivery_evidence,
        )

    cat=str(category or "ALL").strip().upper()
    if cat not in {"ALL","FRESH","FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_FRESH_OR_FROZEN")
    key=_ordering_review_cache_key(
        cat,
        delivery_date,
        best_available_delivery_evidence=best_available_delivery_evidence,
    )

    with _ORDERING_REVIEW_CACHE_LOCK:
        cached=_ORDERING_REVIEW_CACHE_VALUES.get(key)
        cached_at=_ORDERING_REVIEW_CACHE_AT.get(key)
        already_refreshing=key in _ORDERING_REVIEW_REFRESHING

    # Polling a cache that is already warming must stay non-blocking.  The old
    # path re-opened MySQL on every poll while the heavy worker was using the
    # same database, which could make the mobile request hit its AbortController
    # timeout and surface "signal is aborted without reason".
    if cached is None and not already_refreshing:
        persisted=_load_persisted_ordering_review(key)
        if persisted is not None:
            with _ORDERING_REVIEW_CACHE_LOCK:
                _ORDERING_REVIEW_CACHE_VALUES[key]=persisted
                _ORDERING_REVIEW_CACHE_AT[key]=0.0
            cached=persisted
            cached_at=0.0

    if cached is None and already_refreshing:
        expected_now=completed_through_date()
        return {
            "contract_version":"BACKOFFICE_ORDERING_REVIEW_V6_ASYNC_BEST_AVAILABLE",
            "category":cat,
            "selected_delivery_date":delivery_date,
            "selected_delivery_weekday":[
                "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
            ][delivery_date.weekday()],
            "analysis_status":"REFRESHING",
            "cache_status":"WARMING",
            "refreshing":True,
            "refresh_error":None,
            "count":0,
            "rows":[],
            "skipped":[],
            "skipped_breakdown":{},
            "data_health":{
                "status":"REFRESHING",
                "expected_through":expected_now,
                "pos_data_through":None,
                "movement_data_through":None,
                "missing_required_sources":[],
                "rule":"ORDERING_ASYNC_REFRESH_ALREADY_RUNNING_NONBLOCKING_POLL",
            },
        }

    expected=str(completed_through_date())
    cached_expected=str(((cached or {}).get("data_health") or {}).get("expected_through") or "")
    data_current=bool(cached and cached_expected==expected)
    age=(time.monotonic()-cached_at) if cached is not None and cached_at is not None else None
    stale=(
        cached is None
        or not data_current
        or age is None
        or age>=_ORDERING_REVIEW_CACHE_TTL_SECONDS
    )
    if force or stale:
        _request_ordering_review_refresh(
            cat,
            delivery_date,
            key,
            best_available_delivery_evidence,
        )

    with _ORDERING_REVIEW_CACHE_LOCK:
        refreshing=key in _ORDERING_REVIEW_REFRESHING
    err=_ORDERING_REVIEW_LAST_ERROR.get(key)

    # Yipman is explicitly a best-available operating view.  When yesterday's
    # cache is still the newest usable evidence, return it immediately as an
    # ESTIMATE while a fresh delivery-date calculation runs in the background.
    # Standard Back Office behavior remains unchanged.
    if cached is not None and not data_current and best_available_delivery_evidence:
        stale_health=dict((cached.get("data_health") or {}))
        stale_health.update({
            "status":"STALE_ESTIMATE_AVAILABLE",
            "decision_mode":"STALE_ESTIMATE",
            "expected_through":expected,
            "cache_expected_through":cached_expected or None,
            "warning":"Best-available cached ordering estimate is shown while current delivery analysis refreshes.",
        })
        has_rows=bool(cached.get("rows"))
        return {
            **cached,
            "contract_version":"BACKOFFICE_ORDERING_REVIEW_V6_ASYNC_BEST_AVAILABLE",
            "analysis_status":(
                "READY_STALE_ESTIMATE_REFRESHING"
                if has_rows else
                "READY_STALE_ESTIMATE_NO_ELIGIBLE_ITEMS_REFRESHING"
            ),
            "cache_status":"STALE_ESTIMATE_REFRESHING",
            "refreshing":refreshing,
            "refresh_error":err,
            "data_health":stale_health,
        }

    # Never present a prior completed-data-day snapshot as current Ordering
    # in the standard Back Office path.
    if cached is None or not data_current:
        return {
            "contract_version":"BACKOFFICE_ORDERING_REVIEW_V5_ASYNC_STALE_ESTIMATE",
            "category":cat,
            "selected_delivery_date":delivery_date,
            "selected_delivery_weekday":[
                "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
            ][delivery_date.weekday()],
            "analysis_status":"REFRESHING" if refreshing else "REFRESH_FAILED",
            "cache_status":"WARMING" if cached is None else "STALE_DATA_REFRESHING",
            "refreshing":refreshing,
            "refresh_error":err,
            "count":0,
            "rows":[],
            "skipped":[],
            "skipped_breakdown":{},
            "data_health":{
                "status":"REFRESHING" if refreshing else "UNAVAILABLE",
                "expected_through":completed_through_date(),
                "pos_data_through":None,
                "movement_data_through":None,
                "missing_required_sources":[],
                "rule":"ORDERING_ASYNC_CACHE_REQUIRES_CURRENT_COMPLETED_DATA",
            },
        }

    return {
        **cached,
        "contract_version":"BACKOFFICE_ORDERING_REVIEW_V5_ASYNC_STALE_ESTIMATE",
        "cache_status":"STALE_REFRESHING" if stale else "HIT",
        "refreshing":refreshing,
        "refresh_error":err,
    }


def sales_lineage_audit() -> dict[str, Any]:
    """Audit every current Seafood UPC against lineage-aware canonical POS totals."""
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        days=source_data_days(
            cur,
            "sales_by_price_type",
            limit=7,
            up_to=completed_through_date(),
        )
        qty_by_upc=canonical_pos_qty_by_upc(cur,days)
        cur.execute(
            """SELECT q.upc_id,q.ean_upc,q.selling_description,q.main_article_number,
                      q.pos_qty_7d,q.upc_velocity_7d,q.sales_days_7d,
                      q.quick_check_status,q.blocking_reason
               FROM quick_check_current q
               WHERE EXISTS (
                 SELECT 1
                 FROM upc_department_observation d
                 WHERE d.upc_id=q.upc_id
                   AND d.department_code='400'
               )
               ORDER BY q.ean_upc"""
        )
        rows=cur.fetchall()
        cur.close()

    day_count=len(days)
    mismatches=[]
    historical_with_sales=[]
    velocity_mismatches=[]
    for row in rows:
        uid=int(row["upc_id"])
        expected=_d(qty_by_upc.get(uid,Decimal("0")))
        stored=_d(row.get("pos_qty_7d"))
        if expected!=stored:
            mismatches.append({
                "upc":row.get("ean_upc"),
                "name":row.get("selling_description"),
                "family_article":row.get("main_article_number"),
                "stored_pos_qty_7d":stored,
                "lineage_pos_qty_7d":expected,
                "status":row.get("quick_check_status"),
            })
        if expected>0 and str(row.get("quick_check_status") or "").upper()=="HISTORICAL_ONLY":
            historical_with_sales.append({
                "upc":row.get("ean_upc"),
                "name":row.get("selling_description"),
                "lineage_pos_qty_7d":expected,
                "blocking_reason":row.get("blocking_reason"),
            })
        expected_velocity=(expected/Decimal(day_count)) if day_count else Decimal("0")
        stored_velocity=_d(row.get("upc_velocity_7d"))
        if day_count and abs(expected_velocity-stored_velocity)>Decimal("0.000001"):
            velocity_mismatches.append({
                "upc":row.get("ean_upc"),
                "stored_velocity_7d":stored_velocity,
                "lineage_velocity_7d":expected_velocity,
                "completed_pos_days":day_count,
            })

    passed=not mismatches and not historical_with_sales and not velocity_mismatches
    return {
        "contract_version":"BACKOFFICE_SALES_LINEAGE_AUDIT_V1",
        "pass":passed,
        "seafood_upcs_checked":len(rows),
        "completed_pos_days":day_count,
        "data_days":[str(x.get("date")) for x in days],
        "qty_mismatch_count":len(mismatches),
        "historical_with_sales_count":len(historical_with_sales),
        "velocity_mismatch_count":len(velocity_mismatches),
        "qty_mismatches":mismatches[:100],
        "historical_with_sales":historical_with_sales[:100],
        "velocity_mismatches":velocity_mismatches[:100],
        "rules":{
            "qty_authority":"POS_RAW_EAN_LINEAGE_TO_CURRENT_CANONICAL_UPC",
            "family_movement_not_used_for_upc_qty":True,
            "missing_calendar_dates_are_zero":False,
        },
    }


def _quick_check_fuzzy_rows(
    cur,
    query: str,
    category: str,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fast typo-tolerant fallback over the already-built Quick Check serving table.

    This intentionally avoids the heavier V2 search aggregation used elsewhere.
    Quick Check only needs identity discovery here; the result list is then
    ordered by recent UPC velocity, matching the mobile search contract.
    """
    q = " ".join(
        "".join(ch if ch.isalnum() else " " for ch in str(query or "").upper()).split()
    )
    q_tokens = [x for x in q.split() if x]
    if not q_tokens:
        return [], {
            "query": query,
            "mode": "LIGHTWEIGHT_TYPO_MATCH",
            "count": 0,
        }

    if category == "ALL":
        cur.execute(
            """SELECT *
               FROM quick_check_current
               ORDER BY COALESCE(upc_velocity_7d,0) DESC,
                        COALESCE(pos_qty_7d,0) DESC,
                        ean_upc
               LIMIT 2500"""
        )
    else:
        cur.execute(
            """SELECT *
               FROM quick_check_current
               WHERE UPPER(COALESCE(product_class,''))=%s
               ORDER BY COALESCE(upc_velocity_7d,0) DESC,
                        COALESCE(pos_qty_7d,0) DESC,
                        ean_upc
               LIMIT 2500""",
            (category,),
        )

    corpus = cur.fetchall()

    def _threshold(token: str) -> float:
        n = len(token)
        if n <= 2:
            return 1.0
        if n <= 4:
            return 0.78
        if n <= 6:
            return 0.72
        return 0.68

    ranked: list[tuple[float, float, float, str, dict[str, Any]]] = []
    for row in corpus:
        text = " ".join(
            str(x or "")
            for x in (
                row.get("selling_description"),
                row.get("family_description"),
            )
        ).upper()
        normalized = " ".join(
            "".join(ch if ch.isalnum() else " " for ch in text).split()
        )
        tokens = [x for x in normalized.split() if x]
        if not tokens:
            continue

        token_scores: list[float] = []
        matched = True
        for needle in q_tokens:
            best = max(
                (SequenceMatcher(None, needle, candidate).ratio() for candidate in tokens),
                default=0.0,
            )
            if best < _threshold(needle):
                matched = False
                break
            token_scores.append(best)

        if not matched or not token_scores:
            continue

        min_score = min(token_scores)
        avg_score = sum(token_scores) / len(token_scores)
        velocity = float(row.get("upc_velocity_7d") or 0)
        upc = str(row.get("ean_upc") or "")
        ranked.append((-velocity, -min_score, -avg_score, upc, row))

    ranked.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    rows = [x[4] for x in ranked[:limit]]
    return rows, {
        "query": query,
        "mode": "LIGHTWEIGHT_TYPO_MATCH",
        "count": len(rows),
        "sort": "RECENT_VELOCITY_FIRST",
    }


def _manual_selling_article_map(
    cur,
    family_main_by_id: dict[int, str],
    family_qrows: list[dict[str, Any]],
) -> dict[tuple[int, str], str]:
    """Resolve operational UPC -> Selling Article from the raw Article Manual.

    User-confirmed schemas:
      Fresh Fish / Live Fish / Shrimp / Fish Ball / Frozen Fish:
        A=Family/Main, B=Selling Article, C=Toledo#, D=EAN/UPC,
        G=receiving pack size. Blank B on a D-UPC row means Selling Article=A.
      Frozen Pack:
        A=Family/Main, D=EAN/UPC, E=receiving pack size, G=Selling UOM;
        Selling Article=A.

    Raw Article Manual is read directly so Quick Check is not dependent on stale
    phase2c_row_state created before these tab semantics were corrected.
    """
    targets: dict[str, set[int]] = {}
    for row in family_qrows:
        if row.get("family_id") is None:
            continue
        upc = str(row.get("ean_upc") or "").strip()
        if not upc:
            continue
        key = _numeric_key(upc) or upc
        targets.setdefault(key, set()).add(int(row["family_id"]))
    if not targets:
        return {}

    confirmed_out: dict[tuple[int, str], str] = {}
    for confirmed in USER_CONFIRMED_SELLING_ARTICLE_OVERRIDES_20260930:
        main = str(confirmed.get("family_article") or "").strip()
        ean = str(confirmed.get("ean_upc") or "").strip()
        selling = str(confirmed.get("selling_article") or "").strip()
        key = _numeric_key(ean) or ean
        if not main or not key or not selling:
            continue
        for fid in targets.get(key, set()):
            if str(family_main_by_id.get(fid) or "") == main:
                confirmed_out[(fid, key)] = selling

    standard_tabs = {
        "fresh fish", "live fish", "shrimp", "fish ball", "frozen fish"
    }
    recognized_tabs = standard_tabs | {"frozen pack"}
    mains = sorted({
        str(main or "").strip()
        for main in family_main_by_id.values()
        if str(main or "").strip()
    })
    if not mains:
        return {}
    mph = ",".join(["%s"] * len(mains))
    cur.execute(
        f"""SELECT f.file_id,sh.sheet_name,r.raw_id,
                   JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.A')) AS col_a,
                   JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.B')) AS col_b,
                   JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.C')) AS col_c,
                   JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.D')) AS col_d,
                   JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.E')) AS col_e,
                   JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.G')) AS col_g
            FROM ingest_file f
            JOIN ingest_sheet sh ON sh.file_id=f.file_id
            JOIN raw_article_manual r ON r.sheet_id=sh.sheet_id
            WHERE f.source_type='article_manual'
              AND f.processing_status='INGESTED'
              AND LOWER(TRIM(sh.sheet_name)) IN
                  ('fresh fish','live fish','shrimp','fish ball','frozen fish','frozen pack')
              AND r.source_row_number>COALESCE(sh.header_row_number,0)
              AND TRIM(JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.A'))) IN ({mph})
            ORDER BY f.file_id DESC,r.raw_id DESC""",
        tuple(mains),
    )

    out: dict[tuple[int, str], str] = dict(confirmed_out)
    for row in cur.fetchall():
        tab = str(row.get("sheet_name") or "").strip().lower()
        if tab not in recognized_tabs:
            continue
        main = str(row.get("col_a") or "").strip()
        raw_upc = str(row.get("col_d") or "").strip()
        compact = raw_upc.replace(" ", "").replace("-", "")
        if not compact.isdigit():
            continue
        key = _numeric_key(compact) or compact
        if key not in targets:
            continue

        selling = (
            str(row.get("col_b") or "").strip() or main
            if tab in standard_tabs
            else main
        )
        if not selling.isdigit() or not main.isdigit():
            continue
        for fid in targets.get(key, set()):
            if str(family_main_by_id.get(fid) or "") != main:
                continue
            out.setdefault((fid, key), selling)

    # Toledo-only internal POS codes such as 4816 have no D EAN/UPC row. Keep
    # them eligible only through explicit confirmed user authority; never turn
    # every Toledo# into a UPC automatically.
    unresolved_keys = sorted({
        key
        for key, fids_for_key in targets.items()
        if any((fid, key) not in out for fid in fids_for_key)
    })
    if unresolved_keys:
        cur.execute(
            """SELECT m.ean_upc,m.article_number,baf.family_id,pf.main_article_number
               FROM manual_upc_override m
               JOIN article a ON a.article_number=m.article_number
               JOIN bridge_article_family baf
                 ON baf.article_id=a.article_id
                AND baf.mapping_status='CONFIRMED'
                AND baf.is_primary=TRUE
                AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               JOIN product_family pf ON pf.family_id=baf.family_id
               WHERE m.override_status='CONFIRMED'"""
        )
        unresolved = set(unresolved_keys)
        for row in cur.fetchall():
            ean = str(row.get("ean_upc") or "").strip()
            key = _numeric_key(ean) or ean
            if key not in unresolved:
                continue
            fid = int(row["family_id"])
            if fid not in targets.get(key, set()):
                continue
            main = str(row.get("main_article_number") or "")
            if str(family_main_by_id.get(fid) or "") != main:
                continue
            article = str(row.get("article_number") or "").strip()
            if article:
                out.setdefault((fid, key), article)

    return out

def _quick_receiving_article_context(
    cur,
    qrows: list[dict[str, Any]],
    movement_days_7: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Build Family -> classified SAP Article -> UPC lineage for Quick Check.

    SAP Article roles are evidence-based, not inferred from hierarchy alone:
    101-109 => Receiving Article, non-zero 251/252 => SAP Selling Article, both
    => Receiving / SAP Selling Article. The Family/source Article may itself own
    251/252 and stays in the Family header instead of being duplicated below.
    UPC sold quantity remains POS-only.
    """
    family_rows: dict[int, dict[str, Any]] = {}
    for row in qrows:
        if row.get("family_id") is None:
            continue
        fid = int(row["family_id"])
        family_rows.setdefault(fid, row)
    if not family_rows:
        return {}

    # Canonical Family movement metrics already published in quick_check_current
    # carry the serving-layer Family UOM. Preserve them as a reconciliation
    # authority when the raw canonical 251/252 total is numerically identical
    # but the movement row's base_uom_code is inconsistent (for example a
    # non-catchweight EA item mislabeled LB in raw MVT).
    canonical_family_metric: dict[int, dict[str, Any]] = {}
    canonical_family_conflict: set[int] = set()
    for row in qrows:
        if row.get("family_id") is None:
            continue
        fid = int(row["family_id"])
        qty = row.get("family_movement_7d")
        uom = str(row.get("family_movement_uom") or "").strip().upper()
        if qty is None or not uom:
            continue
        candidate = {"quantity": _d(qty), "uom": uom}
        current = canonical_family_metric.get(fid)
        if current is None:
            canonical_family_metric[fid] = candidate
        elif current != candidate:
            canonical_family_conflict.add(fid)
    for fid in canonical_family_conflict:
        canonical_family_metric.pop(fid, None)

    fids = sorted(family_rows)
    source_by_family = {
        fid: str(row.get("main_article_number") or "").strip()
        for fid, row in family_rows.items()
    }
    family_by_source = {
        art: fid for fid, art in source_by_family.items() if art
    }

    # A search can return only one UPC. Family usage must still reconcile every
    # UPC in that Family with positive 7D POS activity.
    fph_all = ",".join(["%s"] * len(fids))
    cur.execute(
        f"""SELECT family_id,ean_upc,selling_description,pos_qty_7d,upc_velocity_7d,
                   selling_uom,main_article_number
            FROM quick_check_current
            WHERE family_id IN ({fph_all})
            ORDER BY family_id,ean_upc""",
        tuple(fids),
    )
    family_qrows = cur.fetchall()
    manual_selling_by_upc = _manual_selling_article_map(
        cur,
        source_by_family,
        family_qrows,
    )
    manual_authoritative_fids = {fid for fid, _ in manual_selling_by_upc}

    # Start with confirmed bridge lineage, but do not duplicate the Family/source
    # Article as a second-level selling Article. It stays in the Family header.
    ph = ",".join(["%s"] * len(fids))
    cur.execute(
        f"""SELECT baf.family_id,
                   a.article_number,
                   a.article_description,
                   baf.relationship_type,
                   baf.is_primary
            FROM bridge_article_family baf
            JOIN article a ON a.article_id=baf.article_id
            WHERE baf.family_id IN ({ph})
              AND baf.mapping_status='CONFIRMED'
              AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
            ORDER BY baf.family_id,
                     baf.is_primary DESC,
                     CASE baf.relationship_type WHEN 'SUB' THEN 0 WHEN 'MAIN' THEN 1 ELSE 2 END,
                     a.article_number""",
        tuple(fids),
    )
    candidates: dict[int, dict[str, dict[str, Any]]] = {fid: {} for fid in fids}
    for r in cur.fetchall():
        fid = int(r["family_id"])
        art = str(r.get("article_number") or "").strip()
        if not art or art == source_by_family.get(fid):
            continue
        candidates[fid][art] = {
            "article_number": art,
            "article_description": r.get("article_description"),
            "relationship_type": r.get("relationship_type"),
            "is_primary": bool(r.get("is_primary")),
            "mapping_status": "CONFIRMED_BRIDGE",
            "lineage_basis": "CONFIRMED_BRIDGE",
            "lineage_hits": 0,
            "lineage_latest_date": None,
            "lineage_movement_types": None,
        }

    # Preserve the explicit Table 1 / Article Manual Selling Article relation.
    # 317/318 is lineage evidence only and must never replace this authority.
    manual_upcs_by_article: dict[tuple[int, str], list[str]] = {}
    for (fid, upc_key), art in manual_selling_by_upc.items():
        manual_upcs_by_article.setdefault((fid, art), []).append(upc_key)
        if art == source_by_family.get(fid):
            continue
        existing = candidates[fid].get(art, {})
        existing.update(
            {
                "article_number": art,
                "relationship_type": existing.get("relationship_type") or "ARTICLE_MANUAL_SELLING",
                "is_primary": bool(existing.get("is_primary")),
                "mapping_status": "ARTICLE_MANUAL_SELLING_EXACT",
                "lineage_basis": "ARTICLE_MANUAL_COLUMN_B_TO_D",
                "manual_selling_upcs": sorted(set(manual_upcs_by_article[(fid, art)])),
            }
        )
        candidates[fid][art] = existing

    # Discover actual SAP output/selling Articles from 317/318 conversion pairs:
    # same canonical file/date + same SAP document + same absolute quantity/UOM
    # + opposite signs. This is stronger than description-only grouping.
    conversion_by_family: dict[int, dict[str, Any]] = {}
    source_articles = sorted(family_by_source)
    if source_articles and movement_days_7:
        sph = ",".join(["%s"] * len(source_articles))
        canonical_clauses = []
        args: list[Any] = list(source_articles)
        for d in movement_days_7:
            canonical_clauses.append("(src.file_id=%s AND src.posting_date=%s)")
            args.extend([int(d["file_id"]), d["date"]])
        cur.execute(
            f"""SELECT src.article_number AS source_article,
                       dst.article_number AS article_number,
                       MAX(dst.description) AS article_description,
                       COUNT(*) AS lineage_hits,
                       MAX(dst.posting_date) AS lineage_latest_date,
                       GROUP_CONCAT(DISTINCT src.movement_type ORDER BY src.movement_type) AS lineage_movement_types
                FROM movement_history src
                JOIN movement_history dst
                  ON dst.file_id=src.file_id
                 AND dst.posting_date=src.posting_date
                 AND dst.article_document=src.article_document
                 AND dst.movement_type=src.movement_type
                 AND dst.article_number<>src.article_number
                 AND (dst.base_uom_code <=> src.base_uom_code)
                 AND dst.base_quantity IS NOT NULL
                 AND src.base_quantity IS NOT NULL
                 AND (dst.base_quantity * src.base_quantity) < 0
                 AND ABS(dst.base_quantity)=ABS(src.base_quantity)
                 AND (
                      src.amount_local_currency IS NULL
                      OR dst.amount_local_currency IS NULL
                      OR ABS(dst.amount_local_currency)=ABS(src.amount_local_currency)
                 )
                WHERE src.article_number IN ({sph})
                  AND src.movement_type IN ('317','318')
                  AND src.article_document IS NOT NULL
                  AND src.article_document<>''
                  AND ({' OR '.join(canonical_clauses)})
                GROUP BY src.article_number,dst.article_number""",
            tuple(args),
        )
        for r in cur.fetchall():
            source = str(r.get("source_article") or "").strip()
            art = str(r.get("article_number") or "").strip()
            fid = family_by_source.get(source)
            if fid is None or not art or art == source:
                continue
            existing = candidates[fid].get(art, {})
            existing.update(
                {
                    "article_number": art,
                    "article_description": (
                        r.get("article_description")
                        or existing.get("article_description")
                    ),
                    "relationship_type": existing.get("relationship_type") or "SAP_CONVERSION_OUTPUT",
                    "is_primary": bool(existing.get("is_primary")),
                    "mapping_status": "SAP_317_318_LINKED",
                    "lineage_basis": "SAP_DOCUMENT_317_318",
                    "lineage_hits": int(r.get("lineage_hits") or 0),
                    "lineage_latest_date": r.get("lineage_latest_date"),
                    "lineage_movement_types": r.get("lineage_movement_types"),
                }
            )
            candidates[fid][art] = existing

        # Family-level movement uses the Family/source side of a paired 317/318
        # conversion exactly once.  The destination Article is only lineage;
        # its later 251/252 sale must not be added again to the Family total.
        #
        # Source-side sign convention in SAP movement history:
        #   negative => quantity converted OUT of the Family/source Article
        #   positive => quantity converted back IN / reversed
        # Therefore net converted-out quantity is -SUM(source base quantity).
        canonical_clauses = []
        conversion_args: list[Any] = list(source_articles)
        for d in movement_days_7:
            canonical_clauses.append("(src.file_id=%s AND src.posting_date=%s)")
            conversion_args.extend([int(d["file_id"]), d["date"]])
        cur.execute(
            f"""SELECT src.article_number AS source_article,
                       src.base_uom_code,
                       -SUM(COALESCE(src.base_quantity,0)) AS converted_qty_7d,
                       COUNT(*) AS source_row_count
                FROM movement_history src
                WHERE src.article_number IN ({sph})
                  AND src.movement_type IN ('317','318')
                  AND src.base_quantity IS NOT NULL
                  AND ({' OR '.join(canonical_clauses)})
                  AND EXISTS (
                      SELECT 1
                      FROM movement_history dst
                      WHERE dst.file_id=src.file_id
                        AND dst.posting_date=src.posting_date
                        AND dst.article_document=src.article_document
                        AND dst.movement_type=src.movement_type
                        AND dst.article_number<>src.article_number
                        AND (dst.base_uom_code <=> src.base_uom_code)
                        AND dst.base_quantity IS NOT NULL
                        AND (dst.base_quantity * src.base_quantity) < 0
                        AND ABS(dst.base_quantity)=ABS(src.base_quantity)
                        AND (
                             src.amount_local_currency IS NULL
                             OR dst.amount_local_currency IS NULL
                             OR ABS(dst.amount_local_currency)=ABS(src.amount_local_currency)
                        )
                  )
                GROUP BY src.article_number,src.base_uom_code
                ORDER BY src.article_number,src.base_uom_code""",
            tuple(conversion_args),
        )
        conversion_rows_by_family: dict[int, list[dict[str, Any]]] = {}
        for conv_row in cur.fetchall():
            source = str(conv_row.get("source_article") or "").strip()
            fid = family_by_source.get(source)
            if fid is None:
                continue
            conversion_rows_by_family.setdefault(fid, []).append(conv_row)

        for fid, conv_rows in conversion_rows_by_family.items():
            valid = [
                x for x in conv_rows
                if x.get("converted_qty_7d") is not None
            ]
            uoms = {
                str(x.get("base_uom_code") or "").strip().upper()
                for x in valid
                if str(x.get("base_uom_code") or "").strip()
            }
            has_missing_uom = any(
                not str(x.get("base_uom_code") or "").strip()
                for x in valid
            )
            if valid and len(uoms) == 1 and not has_missing_uom:
                conversion_by_family[fid] = {
                    "quantity": sum(
                        (_d(x.get("converted_qty_7d")) for x in valid),
                        Decimal("0"),
                    ),
                    "uom": next(iter(uoms)),
                    "status": "READY",
                    "basis": "PAIRED_SOURCE_317_318_NET_CONVERTED_OUT",
                    "source_row_count": sum(
                        int(x.get("source_row_count") or 0) for x in valid
                    ),
                }
            elif valid:
                conversion_by_family[fid] = {
                    "quantity": None,
                    "uom": None,
                    "status": "MIXED_OR_MISSING_317_318_BASE_UOM",
                    "basis": "PAIRED_SOURCE_317_318_NET_CONVERTED_OUT",
                    "source_row_count": sum(
                        int(x.get("source_row_count") or 0) for x in valid
                    ),
                }

    # Some SAP Selling Articles have valid 251/252 rows but were ingested
    # before their Family bridge existed, leaving movement_history.family_id NULL.
    # Rescue them only when current evidence places that Article in exactly one
    # Family candidate set (e.g. Article Manual or paired 317/318 lineage).
    candidate_owner_sets: dict[str, set[int]] = {}
    for owner_fid, family_candidates in candidates.items():
        for candidate_article in family_candidates:
            candidate_owner_sets.setdefault(str(candidate_article), set()).add(owner_fid)
    unique_candidate_owner = {
        article: next(iter(owners))
        for article, owners in candidate_owner_sets.items()
        if len(owners) == 1
    }

    # Discover every SAP Article with actual 251/252 activity inside the
    # canonical Family window. Do not require the Article to already exist in
    # bridge_article_family or to have a recent 317/318 conversion. This is
    # important for established selling Articles whose conversion happened
    # outside the latest seven movement-data days.
    #
    # The Family header is calculated from ALL Family-owned 251/252 rows,
    # including movement posted directly to the Family/source Article. The
    # second-level SAP Selling Article cards remain Article-specific.
    movement_by_article: dict[tuple[int, str], dict[str, Any]] = {}
    family_movement_by_family: dict[int, dict[str, Any]] = {}
    if fids and movement_days_7:
        fph = ",".join(["%s"] * len(fids))
        canonical_clauses = []
        args: list[Any] = list(fids)
        for d in movement_days_7:
            canonical_clauses.append("(m.file_id=%s AND m.posting_date=%s)")
            args.extend([int(d["file_id"]), d["date"]])
        cur.execute(
            f"""SELECT m.family_id,
                       m.article_number,
                       MAX(m.description) AS article_description,
                       m.base_uom_code,
                       SUM(
                         CASE
                           WHEN m.movement_type='251' THEN ABS(COALESCE(m.base_quantity,0))
                           WHEN m.movement_type='252' THEN -ABS(COALESCE(m.base_quantity,0))
                           ELSE 0
                         END
                       ) AS qty_7d
                FROM movement_history m
                WHERE m.family_id IN ({fph})
                  AND m.movement_type IN ('251','252')
                  AND ({' OR '.join(canonical_clauses)})
                  AND m.base_quantity IS NOT NULL
                GROUP BY m.family_id,m.article_number,m.base_uom_code""",
            tuple(args),
        )
        movement_rows = cur.fetchall()

        orphan_articles = sorted(unique_candidate_owner)
        if orphan_articles:
            aph = ",".join(["%s"] * len(orphan_articles))
            orphan_clauses = []
            orphan_args: list[Any] = list(orphan_articles)
            for d in movement_days_7:
                orphan_clauses.append("(m.file_id=%s AND m.posting_date=%s)")
                orphan_args.extend([int(d["file_id"]), d["date"]])
            cur.execute(
                f"""SELECT m.article_number,
                           MAX(m.description) AS article_description,
                           m.base_uom_code,
                           SUM(
                             CASE
                               WHEN m.movement_type='251' THEN ABS(COALESCE(m.base_quantity,0))
                               WHEN m.movement_type='252' THEN -ABS(COALESCE(m.base_quantity,0))
                               ELSE 0
                             END
                           ) AS qty_7d
                    FROM movement_history m
                    WHERE m.family_id IS NULL
                      AND m.article_number IN ({aph})
                      AND m.movement_type IN ('251','252')
                      AND ({' OR '.join(orphan_clauses)})
                      AND m.base_quantity IS NOT NULL
                    GROUP BY m.article_number,m.base_uom_code""",
                tuple(orphan_args),
            )
            for orphan in cur.fetchall():
                art = str(orphan.get("article_number") or "").strip()
                owner_fid = unique_candidate_owner.get(art)
                if owner_fid is None:
                    continue
                orphan["family_id"] = owner_fid
                orphan["orphan_family_rescue"] = True
                movement_rows.append(orphan)

        article_groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
        family_groups: dict[int, list[dict[str, Any]]] = {}
        for r in movement_rows:
            if r.get("family_id") is None:
                continue
            fid = int(r["family_id"])
            art = str(r.get("article_number") or "").strip()
            if not r.get("orphan_family_rescue"):
                family_groups.setdefault(fid, []).append(r)
            if art:
                article_groups.setdefault((fid, art), []).append(r)

                # An Article with real canonical 251/252 activity is valid
                # second-level evidence even if its bridge/317-318 lineage was
                # not seen in the current seven-day conversion window.
                if art != source_by_family.get(fid):
                    existing = candidates[fid].get(art, {})
                    if not existing:
                        existing = {
                            "article_number": art,
                            "article_description": r.get("article_description"),
                            "relationship_type": "ACTIVE_SAP_SELLING_ARTICLE",
                            "is_primary": False,
                            "mapping_status": "MVT_251_252_ACTIVE",
                            "lineage_basis": "FAMILY_251_252_ACTIVE",
                            "lineage_hits": 0,
                            "lineage_latest_date": None,
                            "lineage_movement_types": "251,252",
                        }
                    else:
                        if not existing.get("article_description"):
                            existing["article_description"] = r.get("article_description")
                    existing["active_251_252"] = True
                    candidates[fid][art] = existing

        for key, rows in article_groups.items():
            valid = [r for r in rows if r.get("qty_7d") is not None]
            uoms = {
                str(r.get("base_uom_code") or "").strip().upper()
                for r in valid
                if str(r.get("base_uom_code") or "").strip()
            }
            has_missing_uom = any(
                not str(r.get("base_uom_code") or "").strip()
                for r in valid
            )
            if valid and len(uoms) == 1 and not has_missing_uom:
                rescued = any(bool(r.get("orphan_family_rescue")) for r in valid)
                movement_by_article[key] = {
                    "quantity": sum((_d(r.get("qty_7d")) for r in valid), Decimal("0")),
                    "uom": next(iter(uoms)),
                    "status": (
                        "READY_ORPHAN_251_252_RESCUED_BY_UNIQUE_SELLING_LINEAGE"
                        if rescued
                        else "READY"
                    ),
                    "article_description": next(
                        (
                            r.get("article_description")
                            for r in valid
                            if r.get("article_description")
                        ),
                        None,
                    ),
                    "orphan_family_rescued": rescued,
                }
            elif valid:
                movement_by_article[key] = {
                    "quantity": None,
                    "uom": None,
                    "status": "MIXED_OR_MISSING_BASE_UOM",
                    "article_description": next(
                        (
                            r.get("article_description")
                            for r in valid
                            if r.get("article_description")
                        ),
                        None,
                    ),
                    "orphan_family_rescued": any(
                        bool(r.get("orphan_family_rescue")) for r in valid
                    ),
                }

        for fid, rows in family_groups.items():
            valid = [r for r in rows if r.get("qty_7d") is not None]
            uoms = {
                str(r.get("base_uom_code") or "").strip().upper()
                for r in valid
                if str(r.get("base_uom_code") or "").strip()
            }
            has_missing_uom = any(
                not str(r.get("base_uom_code") or "").strip()
                for r in valid
            )
            if valid and len(uoms) == 1 and not has_missing_uom:
                family_movement_by_family[fid] = {
                    "quantity": sum((_d(r.get("qty_7d")) for r in valid), Decimal("0")),
                    "uom": next(iter(uoms)),
                    "status": "READY",
                }
            elif valid:
                family_movement_by_family[fid] = {
                    "quantity": None,
                    "uom": None,
                    "status": "MIXED_OR_MISSING_BASE_UOM",
                }

    article_numbers = sorted(
        {
            art
            for family_candidates in candidates.values()
            for art in family_candidates
        }
    )

    # Receipt verification applies to the Family/source header and also remains
    # available for any linked Article that independently has 101-109 history.
    receipt_articles = sorted(set(source_articles) | set(article_numbers))
    receipt_by_article: dict[str, dict[str, Any]] = {}
    receipt_history_by_article: dict[str, list[dict[str, Any]]] = {}
    if receipt_articles:
        aph = ",".join(["%s"] * len(receipt_articles))
        receipt_types = tuple(str(x) for x in range(101, 110))
        tph = ",".join(["%s"] * len(receipt_types))
        cur.execute(
            f"""SELECT article_number,movement_type,posting_date,
                       base_quantity,base_uom_code,file_id
                FROM movement_history
                WHERE article_number IN ({aph})
                  AND movement_type IN ({tph})
                ORDER BY article_number,
                         posting_date DESC,
                         CASE movement_type
                           WHEN '109' THEN 0
                           WHEN '107' THEN 1
                           ELSE 2
                         END,
                         file_id DESC""",
            tuple(receipt_articles) + receipt_types,
        )
        seen_receipt_dates: dict[str, set[str]] = {}
        for r in cur.fetchall():
            art = str(r.get("article_number") or "")
            posting_date = r.get("posting_date")
            if not art or posting_date is None:
                continue
            date_key = str(posting_date)
            seen = seen_receipt_dates.setdefault(art, set())
            if date_key in seen:
                continue
            history = receipt_history_by_article.setdefault(art, [])
            if len(history) >= 2:
                continue
            entry = {
                "verified": True,
                "movement_type": r.get("movement_type"),
                "date": posting_date,
                "weekday": (
                    posting_date.strftime("%A")
                    if hasattr(posting_date, "strftime")
                    else None
                ),
                "quantity": (
                    abs(_d(r.get("base_quantity")))
                    if r.get("base_quantity") is not None
                    else None
                ),
                "uom": r.get("base_uom_code"),
                "source": "MVT_101_109",
            }
            history.append(entry)
            seen.add(date_key)
            if art not in receipt_by_article:
                receipt_by_article[art] = entry

    day_count = len(movement_days_7)

    def _norm_desc(value: Any) -> str:
        raw = str(value or "").upper()
        return " ".join(
            "".join(ch if ch.isalnum() else " " for ch in raw).split()
        )

    def _assign_upc(
        row: dict[str, Any],
        articles: list[dict[str, Any]],
    ) -> tuple[str | None, str]:
        fid = int(row["family_id"]) if row.get("family_id") is not None else None
        upc_text = str(row.get("ean_upc") or "")
        upc_key = _numeric_key(upc_text) or upc_text
        exact_manual = manual_selling_by_upc.get((fid, upc_key)) if fid is not None else None
        if exact_manual:
            return exact_manual, "ARTICLE_MANUAL_COLUMN_B_TO_D_EXACT"
        if fid is not None and fid in manual_authoritative_fids:
            return None, "ARTICLE_MANUAL_COLUMN_B_TO_D_MISSING_FOR_UPC"

        if not articles:
            return None, "NO_SAP_SELLING_ARTICLE_CANDIDATE"

        digits = _numeric_key(row.get("ean_upc"))
        prefix = digits[:3]
        product_code = digits[3:6] if len(digits) >= 6 else ""
        sell_desc = _norm_desc(row.get("selling_description"))
        scored: list[tuple[float, str, dict[str, Any]]] = []

        for a in articles:
            art = str(a.get("article_number") or "")
            desc = _norm_desc(a.get("article_description"))
            if not _fallback_selling_article_compatible(prefix, art, desc):
                continue

            has_selling_mvt = (
                a.get("movement_7d") is not None
                and _d(a.get("movement_7d")) != 0
            )
            role = str(a.get("article_role") or "").upper()
            lineage = str(a.get("lineage_basis") or "").upper()

            # A receiving/related Article with no 251/252 and no explicit
            # selling lineage must never win heuristic UPC assignment. This
            # prevents cases such as 240739 being moved from a Fried-Service
            # Article onto a 101-109-only Receiving Article.
            if (
                not has_selling_mvt
                and role in {"RECEIVING_ARTICLE", "RELATED_SAP_ARTICLE"}
                and lineage not in {
                    "ARTICLE_MANUAL_COLUMN_B_TO_D",
                    "SAP_DOCUMENT_317_318",
                }
            ):
                continue

            score = (
                SequenceMatcher(None, sell_desc, desc).ratio() * 60.0
                if sell_desc and desc
                else 0.0
            )

            if sell_desc and desc and sell_desc == desc:
                score += 100.0
            if product_code and art.endswith(product_code):
                score += 45.0

            # Seafood article-number pattern is powerful when it agrees with the
            # UPC prefix/product code: 240xxx -> 1540xxx, 245xxx -> 1545xxx,
            # 249xxx -> 1549xxx.
            if product_code and art.endswith(product_code):
                if prefix == "240" and art.startswith("1540"):
                    score += 120.0
                elif prefix == "245" and art.startswith("1545"):
                    score += 120.0
                elif prefix == "249" and art.startswith("1549"):
                    score += 120.0

            if prefix == "249":
                if "FRIED" in desc:
                    score += 20.0
                if "SERVICE" in desc:
                    score += 20.0
            elif prefix == "247":
                if "FRIED" in sell_desc and "FRIED" in desc:
                    score += 24.0

            if str(a.get("lineage_basis") or "") == "SAP_DOCUMENT_317_318":
                score += 12.0
            if has_selling_mvt:
                score += 18.0
            scored.append((score, art, a))

        scored.sort(key=lambda x: (-x[0], x[1]))
        if not scored:
            return None, "NO_PREFIX_COMPATIBLE_SAP_SELLING_ARTICLE"
        best = scored[0]
        if best[0] < 30.0:
            return None, "NO_STRONG_SAP_SELLING_ARTICLE_MATCH"
        basis = (
            "SAP_317_318_PLUS_UPC_ARTICLE_PATTERN"
            if best[2].get("lineage_basis") == "SAP_DOCUMENT_317_318"
            else "CONFIRMED_LINEAGE_PLUS_UPC_PRODUCT_CODE_OR_DESCRIPTION"
        )
        return best[1], basis

    out: dict[int, dict[str, Any]] = {}
    for fid, row in family_rows.items():
        source_article = source_by_family.get(fid)
        family_receipt = receipt_by_article.get(str(source_article or ""), {})

        articles: list[dict[str, Any]] = []

        for art in sorted(candidates.get(fid, {})):
            a = dict(candidates[fid][art])
            mv = movement_by_article.get((fid, art), {})
            qty = mv.get("quantity")
            uom = mv.get("uom")
            receipt = receipt_by_article.get(art, {})
            has_article_movement = qty is not None and _d(qty) != 0
            has_article_receipt = bool(receipt.get("verified"))
            article_role = (
                "RECEIVING_AND_SAP_SELLING_ARTICLE"
                if has_article_receipt and has_article_movement
                else (
                    "RECEIVING_ARTICLE"
                    if has_article_receipt
                    else (
                        "SAP_SELLING_ARTICLE"
                        if has_article_movement
                        else "RELATED_SAP_ARTICLE"
                    )
                )
            )
            a.update(
                {
                    "article_role": article_role,
                    "movement_7d": qty,
                    "movement_uom": uom,
                    "avg_qty_day": (
                        _d(qty) / Decimal(day_count)
                        if qty is not None and day_count > 0
                        else None
                    ),
                    "movement_days_7d": day_count,
                    "movement_status": mv.get("status") or "NO_251_252_IN_WINDOW",
                    "receipt_verified": has_article_receipt,
                    "receipt_movement_type": receipt.get("movement_type"),
                    "receipt_date": receipt.get("date"),
                    "receipt_qty": receipt.get("quantity"),
                    "receipt_uom": receipt.get("uom"),
                    "receipt_source": receipt.get("source"),
                    "receipt_history": receipt_history_by_article.get(art, []),
                }
            )
            explicit_upc_keys = sorted(set(manual_upcs_by_article.get((fid, art), [])))
            active_explicit_upcs = []
            for fq in family_qrows:
                if fq.get("family_id") is None or int(fq["family_id"]) != fid:
                    continue
                fq_text = str(fq.get("ean_upc") or "")
                fq_key = _numeric_key(fq_text) or fq_text
                if fq_key in explicit_upc_keys and _d(fq.get("pos_qty_7d")) > 0:
                    active_explicit_upcs.append(fq_text)
            if explicit_upc_keys:
                a["manual_selling_upcs"] = explicit_upc_keys
                a["active_pos_upcs"] = sorted(set(active_explicit_upcs))
                a["has_active_pos_upc"] = bool(active_explicit_upcs)
                a["article_role"] = (
                    "RECEIVING_AND_SAP_SELLING_ARTICLE"
                    if has_article_receipt
                    else "SAP_SELLING_ARTICLE"
                )
                # For a Table-1 Selling Article, absence of 251/252 rows across
                # the selected completed movement days is a real 0 MVT, not an
                # unknown relationship.
                if qty is None:
                    a["movement_7d"] = Decimal("0")
                    a["avg_qty_day"] = (
                        Decimal("0") if day_count > 0 else None
                    )
                    a["movement_status"] = "ZERO_251_252_IN_COMPLETED_MVT_WINDOW"
            articles.append(a)

        raw_family_mv = family_movement_by_family.get(fid, {})

        source_mv = movement_by_article.get((fid, str(source_article or "")), {})
        source_qty = source_mv.get("quantity")
        source_raw_uom = source_mv.get("uom")
        source_uom = source_raw_uom
        source_status = source_mv.get("status") or "NO_251_252_IN_WINDOW"

        conversion_mv = conversion_by_family.get(fid, {})
        conversion_qty = conversion_mv.get("quantity")
        conversion_uom = conversion_mv.get("uom")
        conversion_status = conversion_mv.get("status") or "NO_PAIRED_317_318_IN_WINDOW"

        family_rows_all = [
            x for x in family_qrows
            if x.get("family_id") is not None and int(x["family_id"]) == fid
        ]
        active_pos_rows = [x for x in family_rows_all if _d(x.get("pos_qty_7d")) > 0]

        # Build the complete assignment surface first. The Family/Main Article is
        # itself a legitimate Selling Article whenever it owns 251/252 movement
        # or explicit UPC Selling-Article authority. Receiving-only SUB Articles
        # remain candidates for receipt display but are penalized for UPC assignment.
        upc_map: dict[str, dict[str, Any]] = {}
        article_lookup = {
            str(a.get("article_number") or ""): a for a in articles
        }
        assignable_articles = list(articles)
        source_manual_upcs = sorted(
            set(manual_upcs_by_article.get((fid, str(source_article or "")), []))
        )
        if source_article and (source_qty is not None or source_manual_upcs):
            source_assignable = {
                "article_number": str(source_article),
                "article_description": (
                    source_mv.get("article_description")
                    or row.get("selling_description")
                    or row.get("family_description")
                ),
                "relationship_type": "MAIN",
                "is_primary": True,
                "mapping_status": (
                    "ARTICLE_MANUAL_SELLING_EXACT"
                    if source_manual_upcs
                    else "FAMILY_SOURCE_251_252_ACTIVE"
                ),
                "lineage_basis": (
                    "ARTICLE_MANUAL_COLUMN_B_TO_D"
                    if source_manual_upcs
                    else "FAMILY_SOURCE_251_252"
                ),
                "article_role": "FAMILY_AND_SAP_SELLING_ARTICLE",
                "movement_7d": source_qty if source_qty is not None else Decimal("0"),
                "movement_uom": source_uom,
                "manual_selling_upcs": source_manual_upcs,
            }
            assignable_articles.append(source_assignable)
            article_lookup[str(source_article)] = source_assignable

        for qrow in family_rows_all:
            upc = str(qrow.get("ean_upc") or "")
            assigned, basis = _assign_upc(qrow, assignable_articles)
            assigned_row = article_lookup.get(str(assigned or ""), {})
            upc_map[upc] = {
                "article_number": assigned,
                "mapping_basis": basis,
                "mapping_status": (
                    assigned_row.get("mapping_status")
                    if assigned
                    else "UNRESOLVED"
                ),
            }

        # Family Total Selling MVT contract:
        # Sum SAP 251 minus 252 for EVERY UNIQUE Selling Article in the Family,
        # regardless of recent POS activity. The Family/Main Article is included
        # once when it is itself a Selling Article. Multiple UPCs that share one
        # Selling Article never multiply that Article's movement. 309 and 317/318
        # remain conversion lineage only and are never added as sales.
        active_selling_articles: set[str] = set()
        unmapped_active_pos_upcs: list[str] = []
        for pos_row in active_pos_rows:
            upc_text = str(pos_row.get("ean_upc") or "")
            assigned = (upc_map.get(upc_text) or {}).get("article_number")
            if assigned:
                active_selling_articles.add(str(assigned))
            else:
                unmapped_active_pos_upcs.append(upc_text)

        all_selling_articles: set[str] = set()

        for (movement_fid, movement_article), mv in movement_by_article.items():
            if int(movement_fid) != fid:
                continue
            art = str(movement_article or "").strip()
            if art and mv.get("quantity") is not None:
                all_selling_articles.add(art)

        for (manual_fid, _upc_key), selling_article in manual_selling_by_upc.items():
            art = str(selling_article or "").strip()
            if int(manual_fid) == fid and art:
                all_selling_articles.add(art)

        for a in articles:
            art = str(a.get("article_number") or "").strip()
            role = str(a.get("article_role") or "").upper()
            lineage = str(a.get("lineage_basis") or "").upper()
            if art and (
                "SAP_SELLING_ARTICLE" in role
                or lineage == "ARTICLE_MANUAL_COLUMN_B_TO_D"
                or bool(a.get("manual_selling_upcs"))
            ):
                all_selling_articles.add(art)

        if source_article and (source_qty is not None or source_manual_upcs):
            all_selling_articles.add(str(source_article))

        total_selling_movements: list[dict[str, Any]] = []
        zero_sap_mvt_articles: list[str] = []
        for art in sorted(all_selling_articles):
            mv = movement_by_article.get((fid, art))
            if mv and mv.get("quantity") is not None:
                total_selling_movements.append({"article": art, **mv})
            else:
                zero_sap_mvt_articles.append(art)
                total_selling_movements.append(
                    {
                        "article": art,
                        "quantity": Decimal("0"),
                        "uom": None,
                        "status": "ZERO_251_252_IN_COMPLETED_MVT_WINDOW",
                    }
                )

        movement_uoms = {
            str(x.get("uom") or "").strip().upper()
            for x in total_selling_movements
            if str(x.get("uom") or "").strip()
        }
        canonical_metric = canonical_family_metric.get(fid)
        family_raw_uom = next(iter(movement_uoms)) if len(movement_uoms) == 1 else None
        family_uom = (
            family_raw_uom
            or str((canonical_metric or {}).get("uom") or "").strip().upper()
            or None
        )
        family_uom_reconciled = bool(family_raw_uom)

        if len(movement_uoms) > 1:
            family_qty = None
            family_status = "HOLD_TOTAL_SELLING_ARTICLE_MIXED_MVT_UOM"
        else:
            family_qty = sum(
                (_d(x.get("quantity")) for x in total_selling_movements),
                Decimal("0"),
            )
            family_status = (
                "READY_TOTAL_SELLING_MVT_WITH_ZERO_ARTICLES"
                if zero_sap_mvt_articles
                else "READY_TOTAL_SELLING_MVT_RECONCILED"
            )
        family_basis = "SUM_UNIQUE_ALL_SELLING_ARTICLE_251_MINUS_252_IN_FAMILY"

        out[fid] = {
            "family_article": source_article,
            "family_name": row.get("family_description"),
            "family_receipt_verified": bool(family_receipt.get("verified")),
            "family_receipt_movement_type": family_receipt.get("movement_type"),
            "family_receipt_date": family_receipt.get("date"),
            "family_receipt_qty": family_receipt.get("quantity"),
            "family_receipt_uom": family_receipt.get("uom"),
            "family_receipt_source": family_receipt.get("source"),
            "family_receipt_history": receipt_history_by_article.get(str(source_article or ""), []),
            "receiving_articles": articles,
            "upc_map": upc_map,
            "family_group_movement_7d": family_qty,
            "family_group_movement_uom": family_uom,
            "family_group_raw_movement_uom": family_raw_uom,
            "family_group_uom_reconciled": family_uom_reconciled,
            "family_group_avg_qty_day": (
                _d(family_qty) / Decimal(day_count)
                if family_qty is not None and day_count > 0
                else None
            ),
            "family_group_movement_days_7d": day_count,
            "family_group_movement_status": family_status,
            "family_group_movement_basis": family_basis,
            "family_group_active_pos_upc_count": len(active_pos_rows),
            "family_group_active_selling_article_count": len(active_selling_articles),
            "family_group_active_selling_articles": sorted(active_selling_articles),
            "family_group_total_selling_article_count": len(all_selling_articles),
            "family_group_total_selling_articles": sorted(all_selling_articles),
            "family_group_unmapped_active_pos_upcs": sorted(set(unmapped_active_pos_upcs)),
            "family_group_zero_sap_mvt_articles": sorted(set(zero_sap_mvt_articles)),
            "family_group_reconciliation": (
                "PASS"
                if family_qty is not None and len(movement_uoms) <= 1
                else "HOLD"
            ),
            "family_all_251_252_7d_reference": raw_family_mv.get("quantity"),
            "family_all_251_252_uom_reference": raw_family_mv.get("uom"),
            "family_direct_251_252_7d": source_qty,
            "family_direct_251_252_uom": source_uom,
            "family_conversion_317_318_7d": conversion_qty,
            "family_conversion_317_318_uom": conversion_uom,
            "family_conversion_317_318_status": conversion_status,
            "family_source_article": source_article,
            "family_source_movement_7d": source_qty,
            "family_source_avg_qty_day": (
                _d(source_qty) / Decimal(day_count)
                if source_qty is not None and day_count > 0
                else None
            ),
            "family_source_movement_uom": source_uom,
            "family_source_raw_movement_uom": source_raw_uom,
            "family_source_movement_status": source_status,
        }
    return out

def inventory_review(
    limit: int = 200,
    category: str = "ALL",
    query: str | None = None,
    lightweight: bool = False,
) -> dict[str, Any]:
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "LIVE", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")
    limit = max(1, min(int(limit or 200), 500))
    q = str(query or "").strip()
    search_meta: dict[str, Any] | None = None

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        movement_days_7 = source_data_days(
            cur,
            "movement",
            limit=7,
            up_to=completed_through_date(),
        )
        family_movement_day_count = len(movement_days_7)

        # Fast path for normal Quick Check typing. Direct text / identifier
        # matches should never invoke the heavyweight V2 fuzzy aggregation.
        if q:
            params: list[Any] = []
            category_sql = ""
            if cat != "ALL":
                category_sql = " AND UPPER(COALESCE(product_class,''))=%s"
            if q.isdigit():
                like = f"%{q}%"
                sql = """SELECT *
                         FROM quick_check_current
                         WHERE (
                              ean_upc LIKE %s
                           OR article_number LIKE %s
                           OR main_article_number LIKE %s
                         )"""
                params.extend([like, like, like])
            else:
                like = f"%{q.upper()}%"
                sql = """SELECT *
                         FROM quick_check_current
                         WHERE (
                              UPPER(COALESCE(selling_description,'')) LIKE %s
                           OR UPPER(COALESCE(family_description,'')) LIKE %s
                         )"""
                params.extend([like, like])

            if cat != "ALL":
                sql += category_sql
                params.append(cat)
            sql += """ ORDER BY COALESCE(upc_velocity_7d,0) DESC,
                              COALESCE(pos_qty_7d,0) DESC,
                              ean_upc
                       LIMIT %s"""
            params.append(limit)
            cur.execute(sql, tuple(params))
            qrows = cur.fetchall()

            if qrows:
                search_meta = {
                    "query": q,
                    "mode": "DIRECT_QUICK_CHECK_MATCH",
                    "count": len(qrows),
                }
            else:
                # A misspelling such as SALMOM should stay on the lightweight
                # Quick Check serving table. The former search_items() fallback
                # could exceed the mobile 8-second request timeout.
                qrows, search_meta = _quick_check_fuzzy_rows(
                    cur,
                    q,
                    cat,
                    limit,
                )
        else:
            if cat == "ALL":
                cur.execute(
                    """SELECT * FROM quick_check_current
                       ORDER BY COALESCE(upc_velocity_7d,0) DESC,
                                COALESCE(pos_qty_7d,0) DESC,
                                ean_upc
                       LIMIT %s""",
                    (limit,),
                )
            else:
                cur.execute(
                    """SELECT * FROM quick_check_current
                       WHERE UPPER(COALESCE(product_class,''))=%s
                       ORDER BY COALESCE(upc_velocity_7d,0) DESC,
                                COALESCE(pos_qty_7d,0) DESC,
                                ean_upc
                       LIMIT %s""",
                    (cat, limit),
                )
            qrows = cur.fetchall()

        # Keep canonical 240 main + 249 cook/service forms together in
        # every Quick Check result set. Search may match only one member, so
        # expand the companion from the same confirmed Family + Seafood product
        # code before rendering. 245/247 remain separate siblings.
        pair_signatures: set[tuple[int,str]] = set()
        for pair_row in qrows:
            sig = _seafood_upc_group_signature(pair_row.get("family_id"), pair_row.get("ean_upc"))
            prefix = _numeric_key(pair_row.get("ean_upc"))[:3]
            if sig is not None and prefix in {"240","249"}:
                pair_signatures.add(sig)
        if pair_signatures:
            pair_family_ids = sorted({sig[0] for sig in pair_signatures})
            placeholders = ",".join(["%s"] * len(pair_family_ids))
            cur.execute(
                f"SELECT * FROM quick_check_current WHERE family_id IN ({placeholders}) ORDER BY family_id,ean_upc",
                tuple(pair_family_ids),
            )
            existing = {
                (int(r["upc_id"]) if r.get("upc_id") is not None else None, str(r.get("ean_upc") or ""))
                for r in qrows
            }
            for companion in cur.fetchall():
                sig = _seafood_upc_group_signature(companion.get("family_id"), companion.get("ean_upc"))
                prefix = _numeric_key(companion.get("ean_upc"))[:3]
                if sig not in pair_signatures or prefix not in {"240","249"}:
                    continue
                key = (
                    int(companion["upc_id"]) if companion.get("upc_id") is not None else None,
                    str(companion.get("ean_upc") or ""),
                )
                if key not in existing:
                    qrows.append(companion)
                    existing.add(key)
            qrows.sort(
                key=lambda r: (
                    -float(r.get("upc_velocity_7d") or 0),
                    -float(r.get("pos_qty_7d") or 0),
                    str(r.get("ean_upc") or ""),
                )
            )
            if search_meta is not None:
                search_meta["pair_240_249_expanded"] = True
                search_meta["pair_240_249_grouping_basis"] = "CONFIRMED_FAMILY_PLUS_SEAFOOD_PRODUCT_CODE"

        pair_members: dict[tuple[int,str], set[str]] = {}
        for pair_row in qrows:
            sig = _seafood_upc_group_signature(pair_row.get("family_id"), pair_row.get("ean_upc"))
            prefix = _numeric_key(pair_row.get("ean_upc"))[:3]
            if sig is not None and prefix in {"240","249"}:
                pair_members.setdefault(sig,set()).add(prefix)
        confirmed_pairs = {sig for sig,prefixes in pair_members.items() if {"240","249"}.issubset(prefixes)}

        receiving_context = _quick_receiving_article_context(
            cur,
            qrows,
            movement_days_7,
        )

        family_cache: dict[int, dict[str, Any]] = {}
        # Keep mobile Quick Check search on the identity / movement fast path.
        # Live current-price resolution can touch Price List + POS lineage and is
        # intentionally deferred to the asynchronous Pricing Review overlay in
        # the UI. Full/non-lightweight Inventory still resolves price here.
        live_prices = {} if lightweight else _bulk_live_current_prices(cur, qrows)
        out = []
        for row in qrows:
            live_price = (
                live_prices.get(int(row["upc_id"]))
                if row.get("upc_id") is not None
                else None
            )
            if live_price:
                row["current_price"] = live_price.get("price")
                row["current_price_type"] = live_price.get("type")
                row["current_price_source"] = live_price.get("source")
                row["current_price_asof_date"] = live_price.get("date")
                if (
                    row.get("current_cost_per_selling_unit") is not None
                    and live_price.get("price") is not None
                    and _d(live_price.get("price")) > 0
                ):
                    row["gp_pct_current"] = (
                        (_d(live_price.get("price")) - _d(row.get("current_cost_per_selling_unit")))
                        / _d(live_price.get("price"))
                    )
            else:
                row["current_price"] = None
                row["current_price_type"] = None
                row["current_price_source"] = (
                    "OPEN_DETAIL_FOR_CURRENT_PRICE"
                    if lightweight else "STALE_OR_MISSING_FRESH_PRICE"
                )
                row["current_price_asof_date"] = None
                row["gp_pct_current"] = None

            fid = int(row["family_id"]) if row.get("family_id") is not None else None

            # Live-search list mode intentionally skips the expensive family OH
            # roll-forward. The list does not display OH; full current OH is
            # resolved only when the user opens a UPC detail.
            if lightweight:
                family_oh = {}
            else:
                if fid is not None and fid not in family_cache:
                    cur.execute(
                        "SELECT * FROM quick_check_current WHERE family_id=%s ORDER BY ean_upc",
                        (fid,),
                    )
                    children = cur.fetchall()
                    live_family_oh = _family_effective_oh(cur, children)
                    if live_family_oh.get("status") == "READY" and live_family_oh.get("quantity") is not None:
                        live_family_oh["as_of_date"] = (
                            live_family_oh.get("movement_through_date")
                            or live_family_oh.get("anchor_date")
                        )
                        family_cache[fid] = live_family_oh
                    else:
                        published = _published_family_oh_fallback(children)
                        if published:
                            published["live_status"] = live_family_oh.get("status")
                            published["live_reason"] = live_family_oh.get("reason")
                            family_cache[fid] = published
                        else:
                            family_cache[fid] = live_family_oh
                family_oh = family_cache.get(fid or -1, {})
            pair_sig = _seafood_upc_group_signature(fid, row.get("ean_upc"))
            pair_prefix = _numeric_key(row.get("ean_upc"))[:3]
            pair_key = (
                f"{pair_sig[0]}:{pair_sig[1]}"
                if pair_sig in confirmed_pairs and pair_prefix in {"240","249"}
                else None
            )
            family_ctx = receiving_context.get(fid or -1, {})
            upc_ctx = family_ctx.get("upc_map", {}).get(str(row.get("ean_upc") or ""), {})
            assigned_receiving = upc_ctx.get("article_number")
            assigned_receiving_row = next(
                (
                    a for a in family_ctx.get("receiving_articles", [])
                    if str(a.get("article_number") or "") == str(assigned_receiving or "")
                ),
                {},
            )
            if (
                assigned_receiving
                and str(assigned_receiving)
                    == str(family_ctx.get("family_source_article") or "")
            ):
                assigned_receiving_row = {
                    "movement_7d": family_ctx.get("family_source_movement_7d"),
                    "movement_uom": family_ctx.get("family_source_movement_uom"),
                    "avg_qty_day": family_ctx.get("family_source_avg_qty_day"),
                    "movement_days_7d": family_ctx.get("family_group_movement_days_7d"),
                    "movement_status": family_ctx.get("family_source_movement_status"),
                    "receipt_history": family_ctx.get("family_receipt_history", []),
                }

            out.append(
                {
                    "upc": row.get("ean_upc"),
                    "pair_240_249_key": pair_key,
                    "pair_240_249_role": (
                        "MAIN_240" if pair_key and pair_prefix=="240"
                        else ("COOK_SERVICE_249" if pair_key and pair_prefix=="249" else None)
                    ),
                    "pair_240_249_grouping_basis": (
                        "CONFIRMED_FAMILY_PLUS_SEAFOOD_PRODUCT_CODE" if pair_key else None
                    ),
                    "name": row.get("selling_description"),
                    "receiving_article": assigned_receiving,
                    "receiving_article_mapping_status": upc_ctx.get("mapping_status"),
                    "receiving_article_mapping_basis": upc_ctx.get("mapping_basis"),
                    "receiving_movement_7d": assigned_receiving_row.get("movement_7d"),
                    "receiving_movement_uom": assigned_receiving_row.get("movement_uom"),
                    "receiving_avg_qty_day": assigned_receiving_row.get("avg_qty_day"),
                    "receiving_movement_days_7d": assigned_receiving_row.get("movement_days_7d"),
                    "receiving_movement_status": assigned_receiving_row.get("movement_status"),
                    "receiving_articles": family_ctx.get("receiving_articles", []),
                    "family_group_movement_7d": family_ctx.get("family_group_movement_7d"),
                    "family_group_movement_uom": family_ctx.get("family_group_movement_uom"),
                    "family_group_raw_movement_uom": family_ctx.get("family_group_raw_movement_uom"),
                    "family_group_uom_reconciled": family_ctx.get("family_group_uom_reconciled"),
                    "family_group_avg_qty_day": family_ctx.get("family_group_avg_qty_day"),
                    "family_group_movement_days_7d": family_ctx.get("family_group_movement_days_7d"),
                    "family_group_movement_status": family_ctx.get("family_group_movement_status"),
                    "family_group_movement_basis": family_ctx.get("family_group_movement_basis"),
                    "family_group_active_pos_upc_count": family_ctx.get("family_group_active_pos_upc_count"),
                    "family_group_active_selling_article_count": family_ctx.get("family_group_active_selling_article_count"),
                    "family_group_active_selling_articles": family_ctx.get("family_group_active_selling_articles", []),
                    "family_group_total_selling_article_count": family_ctx.get("family_group_total_selling_article_count"),
                    "family_group_total_selling_articles": family_ctx.get("family_group_total_selling_articles", []),
                    "family_group_unmapped_active_pos_upcs": family_ctx.get("family_group_unmapped_active_pos_upcs", []),
                    "family_group_zero_sap_mvt_articles": family_ctx.get("family_group_zero_sap_mvt_articles", []),
                    "family_group_reconciliation": family_ctx.get("family_group_reconciliation"),
                    "family_all_251_252_7d_reference": family_ctx.get("family_all_251_252_7d_reference"),
                    "family_all_251_252_uom_reference": family_ctx.get("family_all_251_252_uom_reference"),
                    "family_direct_251_252_7d": family_ctx.get("family_direct_251_252_7d"),
                    "family_direct_251_252_uom": family_ctx.get("family_direct_251_252_uom"),
                    "family_conversion_317_318_7d": family_ctx.get("family_conversion_317_318_7d"),
                    "family_conversion_317_318_uom": family_ctx.get("family_conversion_317_318_uom"),
                    "family_conversion_317_318_status": family_ctx.get("family_conversion_317_318_status"),
                    "family_source_article": family_ctx.get("family_source_article"),
                    "family_source_movement_7d": family_ctx.get("family_source_movement_7d"),
                    "family_source_avg_qty_day": family_ctx.get("family_source_avg_qty_day"),
                    "family_source_movement_uom": family_ctx.get("family_source_movement_uom"),
                    "family_source_raw_movement_uom": family_ctx.get("family_source_raw_movement_uom"),
                    "family_source_movement_status": family_ctx.get("family_source_movement_status"),
                    "family_receipt_verified": family_ctx.get("family_receipt_verified"),
                    "family_receipt_movement_type": family_ctx.get("family_receipt_movement_type"),
                    "family_receipt_date": family_ctx.get("family_receipt_date"),
                    "family_receipt_qty": family_ctx.get("family_receipt_qty"),
                    "family_receipt_uom": family_ctx.get("family_receipt_uom"),
                    "family_receipt_source": family_ctx.get("family_receipt_source"),
                    "family_receipt_history": family_ctx.get("family_receipt_history", []),
                    "receiving_receipt_history": assigned_receiving_row.get("receipt_history", []),
                    "family_id": fid,
                    "family_article": row.get("main_article_number"),
                    "family_name": row.get("family_description"),
                    "article_number": row.get("article_number"),
                    "category": row.get("product_class"),
                    "readiness": row.get("quick_check_status"),
                    "selling_uom": row.get("selling_uom"),
                    "qty_uom": _safe_qty_uom(row.get("ean_upc"), row.get("selling_uom")),
                    "sales_days_7d": row.get("sales_days_7d"),
                    "sales_evidence_status": row.get("blocking_reason"),
                    "price": row.get("current_price"),
                    "price_type": row.get("current_price_type"),
                    "price_source": row.get("current_price_source"),
                    "price_as_of": row.get("current_price_asof_date"),
                    "sweet_spot_price": row.get("sweet_spot_price"),
                    "company_price_a": row.get("company_price_a"),
                    "company_price_b": row.get("company_price_b"),
                    "company_price_c": row.get("company_price_c"),
                    "cost": row.get("current_cost_per_selling_unit"),
                    "cost_uom": row.get("selling_uom"),
                    "cost_source": row.get("cost_source"),
                    "cost_date": row.get("cost_date"),
                    "gp_pct": row.get("gp_pct_current"),
                    "qty_7d": row.get("pos_qty_7d"),
                    "velocity_7d": row.get("upc_velocity_7d"),
                    # Compatibility aliases now point to the canonical
                    # Total Selling MVT metric used by the Family header.
                    "family_qty_7d": family_ctx.get("family_group_movement_7d"),
                    "family_qty_uom": family_ctx.get("family_group_movement_uom"),
                    "family_avg_qty_day": family_ctx.get("family_group_avg_qty_day"),
                    "family_movement_days_7d": family_movement_day_count,
                    "dos": row.get("dos"),
                    "doh": row.get("doh"),
                    "family_oh": family_oh.get("quantity"),
                    "family_oh_uom": family_oh.get("uom"),
                    "family_oh_source": family_oh.get("source"),
                    "family_oh_status": family_oh.get("status"),
                    "family_oh_as_of": family_oh.get("as_of_date"),
                    "family_oh_live_status": family_oh.get("live_status"),
                    "family_oh_reason": family_oh.get("live_reason") or family_oh.get("reason"),
                    "last_receipt_date": row.get("last_receipt_date"),
                }
            )
        cur.close()

    return {
        "contract_version": "BACKOFFICE_INVENTORY_V7",
        "category": cat,
        "query": q or None,
        "count": len(out),
        "rows": out,
        "search": search_meta,
        "rules": {
            "write_enabled": "OH_TRUE_STOCK_ONLY",
            "search_scope": "DIRECT_QUICK_CHECK_THEN_TYPO_FALLBACK",
            "search_sort": "DIRECT_RECENT_VELOCITY_THEN_FUZZY_RELEVANCE",
            "quick_check_group_leader": "FAMILY_ARTICLE",
            "quick_check_second_level": "TABLE1_SELLING_ARTICLES_PLUS_MAIN_SUB_101_109_RECEIVING_ARTICLES",
            "quick_check_third_level": "INDIVIDUAL_UPCS_POS_ONLY",
            "receiving_qty_basis": "TABLE1_COLUMN_B_SELLING_ARTICLES_SHOW_251_MINUS_252_EVEN_WHEN_ZERO",
            "receiving_avg_qty_day_denominator": "COMPLETED_MOVEMENT_DAYS",
            "family_group_qty_basis": "SUM_UNIQUE_ALL_SELLING_ARTICLE_251_MINUS_252_IN_FAMILY",
            "sap_selling_article_discovery": "ARTICLE_MANUAL_COLUMN_B_TO_D_AUTHORITY;317_318_LINEAGE_ONLY",
            "receipt_verification": "FAMILY_SOURCE_AND_LINKED_ARTICLE_HAS_MOVEMENT_101_THROUGH_109",
            "upc_receiving_display_link": "ARTICLE_MANUAL_COLUMN_D_UPC_TO_COLUMN_B_SELLING_ARTICLE_EXACT;FALLBACK_ONLY_WITHOUT_MANUAL_AUTHORITY",
            "family_qty_basis": "TOTAL_SELLING_MVT_COMPATIBILITY_ALIAS",
            "family_avg_qty_day_denominator": "COMPLETED_MOVEMENT_DAYS",
            "subgroup_qty_basis": "SUM_INDIVIDUAL_UPC_POS_QTY_ONLY_WHEN_DISPLAY_UOM_MATCHES",
            "subgroup_avg_qty_day_denominator": "COMPLETED_POS_DATA_DAYS",
            "lightweight": bool(lightweight),
            "lightweight_skips": (
                ["FAMILY_EFFECTIVE_OH_ROLLFORWARD","LIVE_CURRENT_PRICE_RESOLUTION_DEFERRED_TO_UI"]
                if lightweight
                else []
            ),
        },
    }

def _ensure_price_acceptance_table(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS backoffice_price_suggestion_acceptance (
             acceptance_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
             ean_upc VARCHAR(64) NOT NULL,
             accepted_current_price DECIMAL(24,8) NULL,
             accepted_current_price_source VARCHAR(64) NULL,
             accepted_current_price_asof_date DATE NULL,
             accepted_candidate_price DECIMAL(24,8) NULL,
             accepted_by VARCHAR(128) NULL,
             accepted_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
             INDEX ix_price_acceptance_upc_id (ean_upc,acceptance_id),
             INDEX ix_price_acceptance_time (accepted_at)
           )"""
    )


def _latest_price_acceptances(cur, upcs: list[str]) -> dict[str, dict[str, Any]]:
    keys=sorted({str(x or "").strip() for x in upcs if str(x or "").strip()})
    if not keys:
        return {}
    _ensure_price_acceptance_table(cur)
    ph=",".join(["%s"]*len(keys))
    cur.execute(
        f"""SELECT a.*
            FROM backoffice_price_suggestion_acceptance a
            JOIN (
              SELECT ean_upc,MAX(acceptance_id) AS acceptance_id
              FROM backoffice_price_suggestion_acceptance
              WHERE ean_upc IN ({ph})
              GROUP BY ean_upc
            ) x ON x.acceptance_id=a.acceptance_id
            ORDER BY a.acceptance_id""",
        tuple(keys),
    )
    return {str(r.get("ean_upc") or ""):r for r in cur.fetchall()}


def _same_decimal(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return Decimal(str(a)) == Decimal(str(b))


def _accepted_snapshot_matches(row: dict[str, Any], accepted: dict[str, Any] | None) -> bool:
    if not accepted:
        return False
    return (
        _same_decimal(row.get("current_price"),accepted.get("accepted_current_price"))
        and str(row.get("current_price_source") or "") == str(accepted.get("accepted_current_price_source") or "")
        and str(row.get("current_price_observed_date") or "") == str(accepted.get("accepted_current_price_asof_date") or "")
        and _same_decimal(row.get("candidate_price"),accepted.get("accepted_candidate_price"))
    )

_HOME_SUMMARY_CACHE_LOCK = threading.Lock()
_HOME_SUMMARY_CACHE_VALUE: dict[str, Any] | None = None
_HOME_SUMMARY_CACHE_AT = 0.0
_HOME_SUMMARY_CACHE_TTL_SECONDS = 120.0
_HOME_SUMMARY_REFRESHING = False
_HOME_SUMMARY_LAST_ERROR: str | None = None


def _ensure_home_summary_cache_table(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS backoffice_home_summary_cache (
             cache_key VARCHAR(64) NOT NULL PRIMARY KEY,
             payload_json LONGTEXT NOT NULL,
             generated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
             ON UPDATE CURRENT_TIMESTAMP(6)
           )"""
    )


def _load_persisted_home_summary() -> dict[str, Any] | None:
    try:
        with db_conn() as conn:
            cur = conn.cursor(dictionary=True)
            _ensure_home_summary_cache_table(cur)
            conn.commit()
            cur.execute(
                """SELECT payload_json,generated_at
                   FROM backoffice_home_summary_cache
                   WHERE cache_key='MOBILE_HOME'
                   LIMIT 1"""
            )
            row = cur.fetchone()
            cur.close()
        if not row:
            return None
        payload = json.loads(row.get("payload_json") or "{}")
        if not isinstance(payload, dict):
            return None
        payload["persisted_generated_at"] = row.get("generated_at")
        return payload
    except Exception:
        return None


def _persist_home_summary(value: dict[str, Any]) -> None:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        _ensure_home_summary_cache_table(cur)
        cur.execute(
            """INSERT INTO backoffice_home_summary_cache(cache_key,payload_json)
               VALUES ('MOBILE_HOME',%s)
               ON DUPLICATE KEY UPDATE
                 payload_json=VALUES(payload_json),
                 generated_at=CURRENT_TIMESTAMP(6)""",
            (json.dumps(value, default=str),),
        )
        conn.commit()
        cur.close()


def _home_price_performance_summary() -> dict[str, Any]:
    """Fast Home-only pricing + latest-day performance summary.

    This intentionally reuses the same 14 completed-data-day price candidate
    logic as Pricing Review, but skips the full Performance narrative, 28/90-day
    analytics, row rendering, and second live-price overlay pass.
    """
    health = _pricing_review_data_health()
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        days = source_data_days(
            cur,
            "sales_by_price_type",
            limit=14,
            up_to=completed_through_date(),
        )
        days = sorted(days, key=lambda x: x["date"])
        if not days:
            cur.close()
            return {
                "pricing": {
                    "status": health.get("status"),
                    "qualified_count": 0,
                    "urgent_240_249_count": 0,
                    "data_health": health,
                },
                "performance": {
                    "status": "UNAVAILABLE",
                    "report_date": None,
                    "sales_dollars": None,
                    "gp_dollars": None,
                    "gp_dollars_complete": False,
                },
            }

        anchor = days[-1]["date"]
        anchor_entry = days[-1]
        cur.execute("SELECT * FROM quick_check_current")
        rows = [dict(x) for x in cur.fetchall()]
        daily = _batch_daily_sales_by_price_type(cur, rows, days)

        live_prices = _bulk_live_current_prices(cur, rows)
        for row in rows:
            if row.get("upc_id") is None:
                continue
            live = live_prices.get(int(row["upc_id"]))
            if live:
                row["current_price"] = live.get("price")
                row["current_price_type"] = live.get("type")
                row["current_price_source"] = live.get("source")
                row["current_price_asof_date"] = live.get("date")
            else:
                row["current_price"] = None
                row["current_price_type"] = None
                row["current_price_source"] = "STALE_OR_MISSING_FRESH_PRICE"
                row["current_price_asof_date"] = None

        canonical_sales = _canonical_report_date_sales(cur, anchor_entry)
        cost_obs = _performance_range_cost_rows(cur, rows, anchor)
        gp_total = Decimal("0")
        gp_complete = True
        for row in rows:
            uid = int(row["upc_id"])
            obs = (daily.get(uid) or {}).get(anchor) or {}
            qty = _d(obs.get("sold_quantity"))
            if qty <= 0:
                continue
            sales = _d(obs.get("sales_amount"))
            cost = _performance_cost_for_day(row, cost_obs, anchor)
            if cost is None:
                gp_complete = False
                continue
            gp_total += sales - qty * _d(cost.get("cost_per_selling_unit"))

        performance = {
            "status": "READY",
            "report_date": anchor,
            "sales_dollars": canonical_sales.get("sales_amount"),
            "gp_dollars": gp_total if gp_complete else None,
            "gp_dollars_complete": gp_complete,
            "gp_basis": "HISTORICAL_APPLICABLE_COST_AS_OF_LATEST_SUPPORTED_DAY",
        }

        if health.get("status") != "CURRENT":
            cur.close()
            return {
                "pricing": {
                    "status": "BLOCKED_STALE_REQUIRED_DATA",
                    "qualified_count": 0,
                    "urgent_240_249_count": 0,
                    "data_health": health,
                },
                "performance": performance,
            }

        pair_groups: dict[tuple[int, str], dict[str, dict[str, Any]]] = {}
        for row in rows:
            sig = _seafood_upc_group_signature(row.get("family_id"), row.get("ean_upc"))
            prefix = _numeric_key(row.get("ean_upc"))[:3]
            if sig is not None and prefix in {"240", "249"}:
                pair_groups.setdefault(sig, {})[prefix] = row

        candidates: list[dict[str, Any]] = []
        urgent_service_upcs: set[str] = set()
        for members in pair_groups.values():
            main = members.get("240")
            service = members.get("249")
            if not main or not service:
                continue
            main_price = _d(main.get("current_price")) if main.get("current_price") is not None else None
            service_price = _d(service.get("current_price")) if service.get("current_price") is not None else None
            if main_price is None or main_price <= 0 or service_price is None or service_price <= 0 or main_price == service_price:
                continue
            upc = str(service.get("ean_upc") or "")
            urgent_service_upcs.add(upc)
            candidates.append({
                "upc": upc,
                "current_price": service_price,
                "current_price_source": service.get("current_price_source"),
                "current_price_observed_date": service.get("current_price_asof_date"),
                "candidate_price": main_price,
                "urgent_240_249": True,
                "actionable": (
                    str(main.get("quick_check_status") or "").upper() == "READY"
                    and str(service.get("quick_check_status") or "").upper() == "READY"
                ),
            })

        for row in rows:
            uid = int(row["upc_id"])
            upc = str(row.get("ean_upc") or "")
            if upc in urgent_service_upcs:
                continue
            m14 = _batch_sales_metric(daily, days, uid, 14)
            q14 = _d(m14.get("sold_quantity"))
            current_oh = _d(row.get("current_oh")) if row.get("current_oh") is not None else None
            pclass = str(row.get("product_class") or "").upper()
            doh = _d(row.get("doh")) if row.get("doh") is not None else None
            freshness_qualified = (
                (pclass == "FRESH" and doh is not None and doh > Decimal("7"))
                or (pclass == "FROZEN" and doh is not None and doh > Decimal("60"))
                or (pclass not in {"FRESH", "FROZEN"})
            )
            if current_oh is None or current_oh <= 0 or q14 <= 0 or not freshness_qualified:
                continue
            if str(row.get("quick_check_status") or "").upper() != "READY":
                continue
            day_obs = (daily.get(uid) or {}).get(anchor) or {}
            report_day_types = {str(x).upper() for x in (day_obs.get("price_types") or {}).keys()}
            if "SALE" in report_day_types:
                continue
            price_opt = _gp_day_price_suggestion_from_batch(row, uid, daily, days)
            current = price_opt.get("current_price_used")
            suggested = price_opt.get("suggested_price")
            if (
                price_opt.get("status") != "READY"
                or current is None
                or _d(current) <= 0
                or row.get("current_cost_per_selling_unit") is None
                or suggested is None
                or abs(_d(suggested) - _d(current)) <= Decimal("0.25")
            ):
                continue
            candidates.append({
                "upc": upc,
                "current_price": current,
                "current_price_source": price_opt.get("current_price_source"),
                "current_price_observed_date": price_opt.get("current_price_observed_date"),
                "candidate_price": suggested,
                "urgent_240_249": False,
                "actionable": True,
            })

        acceptance = _latest_price_acceptances(cur,[str(x.get("upc") or "") for x in candidates])
        visible = [
            x for x in candidates
            if not _accepted_snapshot_matches(x,acceptance.get(str(x.get("upc") or "")))
        ]
        cur.close()

    actionable = [x for x in visible if x.get("actionable")]
    return {
        "pricing": {
            "status": "CURRENT",
            "qualified_count": len(actionable),
            "review_count": len(visible),
            "urgent_240_249_count": sum(1 for x in actionable if x.get("urgent_240_249")),
            "suppressed_accepted_count": len(candidates) - len(visible),
            "data_health": health,
            "basis": "FAST_14D_SAME_PRICE_CANDIDATE_AND_ACCEPTANCE_RULES",
        },
        "performance": performance,
    }


def _home_ordering_summary(order_type: str) -> dict[str, Any]:
    report = bulk_ordering_suggestions(order_type)
    rows = list(report.get("suggestions") or [])
    attention = sum(
        1
        for x in rows
        if (_d(x.get("dos")) < Decimal("3") or _d(x.get("projected_oh_at_delivery")) < 0)
    )
    return {
        "order_type": str(order_type or "").upper(),
        "family_count": len(rows),
        "attention_count": attention,
    }


def _build_backoffice_home_summary() -> dict[str, Any]:
    health = _pricing_review_data_health()
    if health.get("status") != "CURRENT":
        price_perf = _home_price_performance_summary()
        ordering = {
            "status": "BLOCKED_STALE_REQUIRED_DATA",
            "family_count": 0,
            "attention_count": 0,
            "data_health": health,
        }
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            price_future = pool.submit(_home_price_performance_summary)
            fresh_future = pool.submit(_home_ordering_summary, "FRESH")
            frozen_future = pool.submit(_home_ordering_summary, "FROZEN")
            price_perf = price_future.result()
            fresh = fresh_future.result()
            frozen = frozen_future.result()
        ordering = {
            "status": "CURRENT",
            "family_count": int(fresh.get("family_count") or 0)+int(frozen.get("family_count") or 0),
            "attention_count": int(fresh.get("attention_count") or 0)+int(frozen.get("attention_count") or 0),
            "fresh_family_count": int(fresh.get("family_count") or 0),
            "frozen_family_count": int(frozen.get("family_count") or 0),
            "data_health": health,
            "basis": "BULK_ORDERING_SUGGESTIONS_WITHOUT_RECEIPT_DETAIL_ENRICHMENT",
        }

    return {
        "contract_version": "BACKOFFICE_HOME_SUMMARY_V2",
        "pricing": price_perf.get("pricing") or {},
        "performance": price_perf.get("performance") or {},
        "ordering": ordering,
        "generated_at": str(business_today()),
    }


def _refresh_home_summary_worker() -> None:
    global _HOME_SUMMARY_CACHE_VALUE, _HOME_SUMMARY_CACHE_AT, _HOME_SUMMARY_REFRESHING, _HOME_SUMMARY_LAST_ERROR
    try:
        _HOME_SUMMARY_LAST_ERROR = None
        value = _build_backoffice_home_summary()
        _persist_home_summary(value)
        with _HOME_SUMMARY_CACHE_LOCK:
            _HOME_SUMMARY_CACHE_VALUE = value
            _HOME_SUMMARY_CACHE_AT = time.monotonic()
    except Exception as exc:
        # Keep the last successful cache. A failed refresh must never blank Home.
        _HOME_SUMMARY_LAST_ERROR = f"{type(exc).__name__}: {exc}"[:1000]
    finally:
        _HOME_SUMMARY_REFRESHING = False


def _request_home_summary_refresh() -> None:
    global _HOME_SUMMARY_REFRESHING
    if _HOME_SUMMARY_REFRESHING:
        return
    _HOME_SUMMARY_REFRESHING = True
    threading.Thread(
        target=_refresh_home_summary_worker,
        name="home-summary-refresh",
        daemon=True,
    ).start()


def backoffice_home_summary(force: bool = False) -> dict[str, Any]:
    """Return immediately from memory/persistent cache; refresh in background."""
    global _HOME_SUMMARY_CACHE_VALUE, _HOME_SUMMARY_CACHE_AT

    cached = _HOME_SUMMARY_CACHE_VALUE
    if cached is None:
        persisted = _load_persisted_home_summary()
        if persisted is not None:
            with _HOME_SUMMARY_CACHE_LOCK:
                _HOME_SUMMARY_CACHE_VALUE = persisted
                # Persisted snapshot is immediately usable but intentionally
                # stale so a current background refresh starts at once.
                _HOME_SUMMARY_CACHE_AT = 0.0
            cached = persisted

    age = time.monotonic() - _HOME_SUMMARY_CACHE_AT if cached is not None else None
    stale = cached is None or age is None or age >= _HOME_SUMMARY_CACHE_TTL_SECONDS
    if force or stale:
        _request_home_summary_refresh()

    if cached is None:
        return {
            "contract_version": "BACKOFFICE_HOME_SUMMARY_V2",
            "cache_status": "WARMING",
            "refreshing": True,
            "refresh_error": _HOME_SUMMARY_LAST_ERROR,
            "pricing": {},
            "performance": {},
            "ordering": {},
        }

    return {
        **cached,
        "cache_status": "STALE_REFRESHING" if stale else "HIT",
        "refreshing": bool(_HOME_SUMMARY_REFRESHING),
        "refresh_error": _HOME_SUMMARY_LAST_ERROR,
    }


def warm_backoffice_home_summary() -> None:
    # Load any prior successful snapshot immediately, then refresh asynchronously.
    persisted = _load_persisted_home_summary()
    global _HOME_SUMMARY_CACHE_VALUE, _HOME_SUMMARY_CACHE_AT
    if persisted is not None:
        with _HOME_SUMMARY_CACHE_LOCK:
            _HOME_SUMMARY_CACHE_VALUE = persisted
            _HOME_SUMMARY_CACHE_AT = 0.0
    _request_home_summary_refresh()


def _pricing_review_data_health(*, allow_stale_estimate: bool = False) -> dict[str, Any]:
    """Resolve completed POS/MVT freshness for pricing decisions.

    Back Office keeps the strict current-day gate by default. Yipman may opt
    into a clearly labelled best-available estimate using the latest date that
    is canonical in both POS and MVT.
    """
    expected_through = completed_through_date()
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        pos_days = source_data_days(
            cur,
            "sales_by_price_type",
            limit=60,
            up_to=expected_through,
        )
        mvt_days = source_data_days(
            cur,
            "movement",
            limit=60,
            up_to=expected_through,
        )
        cur.close()

    pos_through = pos_days[0]["date"] if pos_days else None
    mvt_through = mvt_days[0]["date"] if mvt_days else None
    pos_dates = {x["date"] for x in pos_days if x.get("date") is not None}
    mvt_dates = {x["date"] for x in mvt_days if x.get("date") is not None}
    common_dates = sorted(pos_dates & mvt_dates)
    common_data_through = common_dates[-1] if common_dates else None

    missing = []
    if pos_through != expected_through:
        missing.append("POS")
    if mvt_through != expected_through:
        missing.append("MVT")

    current = not missing
    estimate_available = bool(
        allow_stale_estimate
        and not current
        and common_data_through is not None
    )
    status = (
        "CURRENT"
        if current
        else ("STALE_ESTIMATE_AVAILABLE" if estimate_available else "BLOCKED_STALE_REQUIRED_DATA")
    )
    data_through = expected_through if current else common_data_through
    stale_days = (
        max(0, (expected_through - data_through).days)
        if data_through is not None else None
    )
    return {
        "status": status,
        "decision_mode": (
            "CURRENT"
            if current
            else ("STALE_ESTIMATE" if estimate_available else "BLOCKED")
        ),
        "expected_through": expected_through,
        "data_through": data_through,
        "stale_calendar_days": stale_days,
        "pos_data_through": pos_through,
        "movement_data_through": mvt_through,
        "missing_required_sources": missing,
        "rule": (
            "YIPMAN_BEST_AVAILABLE_COMMON_POS_MVT_DATE"
            if allow_stale_estimate
            else "PRICE_REVIEW_REQUIRES_CURRENT_COMPLETED_POS_AND_MVT"
        ),
        "warning": (
            None
            if current
            else (
                f"Estimate uses existing POS and MVT through {data_through}; "
                f"required completed data is through {expected_through}."
                if estimate_available
                else "Required POS/MVT sources are stale and no common usable date is available."
            )
        ),
    }

def pricing_review(
    category: str = "ALL",
    limit: int = 1000,
    *,
    include_accepted: bool = False,
    allow_stale_estimate: bool = False,
) -> dict[str, Any]:
    """Pricing suggestions with CURRENT fields from live Quick Check serving.

    Accepted suggestions are suppressed only while the current-price evidence
    and candidate-price fingerprint remain unchanged. New current price evidence
    or a changed candidate automatically makes the UPC eligible to appear again.

    Operational review fails closed when completed POS or MVT coverage is stale.
    """
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "LIVE", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")

    data_health = _pricing_review_data_health(
        allow_stale_estimate=allow_stale_estimate
    )
    if data_health["status"] not in {"CURRENT", "STALE_ESTIMATE_AVAILABLE"}:
        return {
            "contract_version": "BACKOFFICE_PRICING_REVIEW_V7_BEST_AVAILABLE",
            "category": cat,
            "report_date": None,
            "summary": {
                "price_review_candidates": 0,
                "blocked_by_stale_required_data": True,
            },
            "rows": [],
            "suppressed_accepted_count": 0,
            "data_health": data_health,
            "rules": {
                "write_enabled": "BLOCKED_STALE_REQUIRED_DATA",
                "price_changes_are_review_only": True,
                "current_price_display_authority": "LIVE_CANONICAL_PRICE_RESOLUTION_AT_RESPONSE_TIME_WITH_SOURCE_AND_ASOF",
                "current_price_rule": "TODAY_LATEST_VALID_PRICE_LIST_VS_LATEST_COMPLETED_BUSINESS_DAY_SINGLE_DATE_POS_SOLD_EVENT; OLDER_PRICE_EVIDENCE_IS_HISTORY_ONLY; SAME_DAY_PRICE_LIST_WINS",
                "current_cost_display_authority": "QUICK_CHECK_CURRENT_AT_RESPONSE_TIME",
                "freshness_gate": "CURRENT_COMPLETED_POS_AND_MVT_REQUIRED_BEFORE_OPERATIONAL_PRICE_REVIEW",
            },
        }

    estimate_only = data_health["status"] == "STALE_ESTIMATE_AVAILABLE"
    report = performance_report(
        category=cat,
        limit=limit,
        report_date=(data_health.get("data_through") if estimate_only else None),
    )
    rows = [dict(x) for x in (report.get("top_urgent_price_suggestions") or [])]

    upcs = [
        str(x.get("upc") or "").strip()
        for x in rows
        if str(x.get("upc") or "").strip()
    ]
    live_by_upc: dict[str, dict[str, Any]] = {}
    # performance_report() already resolves CURRENT price at response time for
    # every returned price-review row. Reuse that result instead of issuing a
    # second per-UPC live price lookup pass.
    resolved_by_upc: dict[str, dict[str, Any]] = {
        str(x.get("upc") or ""): {
            "price": x.get("current_price"),
            "type": x.get("current_price_type"),
            "source": x.get("current_price_source"),
            "date": x.get("current_price_observed_date"),
        }
        for x in rows
        if str(x.get("upc") or "").strip()
        and x.get("current_price") is not None
    }
    latest_acceptance_by_upc: dict[str, dict[str, Any]] = {}
    if upcs:
        with db_conn() as conn:
            cur = conn.cursor(dictionary=True)
            placeholders = ",".join(["%s"] * len(upcs))
            cur.execute(
                f"""SELECT upc_id,ean_upc,family_id,product_class,
                           current_price,current_price_type,
                           current_price_source,current_price_asof_date,
                           current_cost_per_selling_unit,cost_source,cost_date,
                           current_oh,current_oh_uom,doh,
                           gp_pct_current,gp_per_day_7d,quick_check_status,
                           published_at,publish_batch_id
                    FROM quick_check_current
                    WHERE ean_upc IN ({placeholders})""",
                tuple(upcs),
            )
            live_by_upc = {
                str(r.get("ean_upc") or ""): r
                for r in cur.fetchall()
            }
            latest_acceptance_by_upc=_latest_price_acceptances(cur,upcs)

            family_ids=sorted({
                int(r["family_id"])
                for r in live_by_upc.values()
                if r.get("family_id") is not None
            })
            delivery_pattern_by_family: dict[int,dict[str,Any]] = {}
            if family_ids:
                receipt_days=source_data_days(
                    cur,
                    "movement",
                    limit=180,
                    up_to=completed_through_date(),
                )
                event_map=_family_receipt_events_bulk(
                    cur,
                    family_ids,
                    data_days=receipt_days,
                )
                for fid in family_ids:
                    delivery_pattern_by_family[fid]=_delivery_pattern(
                        event_map.get(fid) or [],
                        after_date=business_today(),
                        lookback_days=180,
                    )
            cur.close()

    for row in rows:
        upc = str(row.get("upc") or "")
        live = live_by_upc.get(upc)
        if not live:
            row["current_serving_overlay_status"] = "MISSING_QUICK_CHECK_CURRENT"
            continue

        resolved_price = resolved_by_upc.get(upc)
        current_price = (
            resolved_price.get("price")
            if resolved_price else None
        )
        current_cost = live.get("current_cost_per_selling_unit")

        row["current_price"] = current_price
        row["current_price_type"] = (
            resolved_price.get("type") if resolved_price else None
        )
        row["current_price_source"] = (
            resolved_price.get("source") if resolved_price else "STALE_OR_MISSING_FRESH_PRICE"
        )
        row["current_price_observed_date"] = (
            resolved_price.get("date") if resolved_price else None
        )
        row["current_price_basis"] = "TODAY_PRICE_LIST_VS_LATEST_COMPLETED_DAY_POS_FRESHNESS_GATE"

        row["current_cost"] = current_cost
        row["current_cost_source"] = live.get("cost_source")
        row["cost_date"] = live.get("cost_date")
        row["cost_basis"] = "CURRENT_AUTHORITATIVE_COST"
        row["current_oh"] = live.get("current_oh")
        row["current_oh_uom"] = live.get("current_oh_uom")
        row["doh"] = live.get("doh")

        row["current_gp_pct_reference"] = live.get("gp_pct_current")
        row["current_gp_per_day_7d"] = live.get("gp_per_day_7d")
        row["readiness"] = live.get("quick_check_status")
        row["serving_publish_batch_id"] = live.get("publish_batch_id")
        row["serving_published_at"] = live.get("published_at")
        row["current_serving_overlay_status"] = (
            "READY" if resolved_price else "STALE_OR_MISSING_CURRENT_PRICE"
        )
        row["data_status"] = data_health.get("status")
        row["data_through"] = data_health.get("data_through")
        row["expected_through"] = data_health.get("expected_through")
        row["stale_calendar_days"] = data_health.get("stale_calendar_days")
        row["estimate_only"] = estimate_only

        family_id=live.get("family_id")
        pattern=(
            delivery_pattern_by_family.get(int(family_id))
            if family_id is not None else None
        )
        observed_days=list((pattern or {}).get("observed_delivery_days") or [])
        row["observed_delivery_days"]=[
            {
                "weekday":x.get("weekday"),
                "weekday_number":x.get("weekday_number"),
                "receipt_date_count":x.get("receipt_date_count"),
                "confidence_percent":x.get("confidence_percent"),
            }
            for x in observed_days
        ]
        row["observed_delivery_weekdays"]=[
            str(x.get("weekday") or "").upper()
            for x in observed_days
            if str(x.get("weekday") or "").strip()
        ]
        row["delivery_history_lookback_days"]=(pattern or {}).get("lookback_days")

        candidate = row.get("candidate_price")
        if candidate is not None and current_cost is not None and _d(candidate) > 0:
            row["suggested_gp_pct_at_current_cost"] = (
                (_d(candidate) - _d(current_cost)) / _d(candidate)
            )

        if current_price is not None and candidate is not None and _d(current_price) > 0:
            row["price_gap_pct"] = (
                abs(_d(candidate) - _d(current_price))
                / _d(current_price)
                * Decimal("100")
            )
            row["direction"] = (
                "INCREASE"
                if _d(candidate) > _d(current_price)
                else ("DECREASE" if _d(candidate) < _d(current_price) else "KEEP")
            )

    suppressed_count=0
    visible_rows=[]
    for row in rows:
        accepted=latest_acceptance_by_upc.get(str(row.get("upc") or ""))
        accepted_match=_accepted_snapshot_matches(row,accepted)
        row["accepted"] = accepted_match
        row["accepted_at"] = accepted.get("accepted_at") if accepted_match and accepted else None
        if accepted_match and not include_accepted:
            suppressed_count+=1
            continue
        visible_rows.append(row)

    return {
        "contract_version": "BACKOFFICE_PRICING_REVIEW_V7_BEST_AVAILABLE",
        "category": report.get("category"),
        "report_date": report.get("report_date"),
        "summary": report.get("summary"),
        "rows": visible_rows,
        "suppressed_accepted_count": suppressed_count,
        "data_health": data_health,
        "rules": {
            "write_enabled": "ACCEPTED_STATUS_ONLY",
            "price_changes_are_review_only": True,
            "accepted_rule": "SUPPRESS_ONLY_WHILE_CURRENT_PRICE_SOURCE_ASOF_VALUE_AND_CANDIDATE_FINGERPRINT_ARE_UNCHANGED",
            "current_price_display_authority": "LIVE_CANONICAL_PRICE_RESOLUTION_AT_RESPONSE_TIME_WITH_SOURCE_AND_ASOF",
            "current_price_rule": "TODAY_LATEST_VALID_PRICE_LIST_VS_LATEST_COMPLETED_BUSINESS_DAY_SINGLE_DATE_POS_SOLD_EVENT; OLDER PRICE EVIDENCE_IS_HISTORY_ONLY; SAME_DAY_PRICE_LIST_WINS",
            "current_cost_display_authority": "QUICK_CHECK_CURRENT_AT_RESPONSE_TIME",
            "best_available_estimate_allowed": bool(allow_stale_estimate),
            "estimate_basis": "LATEST_COMMON_CANONICAL_POS_AND_MVT_DATE",
            "estimate_is_clearly_labelled": True,
            "source_contract": report.get("price_suggestion_rules"),
        },
    }



def accept_price_suggestion(
    *,
    ean_upc: str,
    current_price: Decimal | None,
    current_price_source: str | None,
    current_price_asof_date: date | None,
    candidate_price: Decimal | None,
    actor: str | None,
    allow_stale_estimate: bool = False,
) -> dict[str, Any]:
    upc=str(ean_upc or "").strip()
    if not upc:
        raise ValueError("UPC_REQUIRED")
    if current_price is None or candidate_price is None:
        raise ValueError("CURRENT_AND_CANDIDATE_PRICE_REQUIRED")

    # Recompute including already accepted rows so the click is bound to the
    # currently valid server-side suggestion rather than a stale browser row.
    snapshot=pricing_review(
        category="ALL",
        limit=1000,
        include_accepted=True,
        allow_stale_estimate=allow_stale_estimate,
    )
    row=next((x for x in snapshot.get("rows",[]) if str(x.get("upc") or "")==upc),None)
    if not row:
        raise ValueError("PRICE_SUGGESTION_NOT_CURRENTLY_AVAILABLE")

    if not (
        _same_decimal(row.get("current_price"),current_price)
        and str(row.get("current_price_source") or "")==str(current_price_source or "")
        and str(row.get("current_price_observed_date") or "")==str(current_price_asof_date or "")
        and _same_decimal(row.get("candidate_price"),candidate_price)
    ):
        raise RuntimeError("PRICE_SUGGESTION_CHANGED_REFRESH_REQUIRED")

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_price_acceptance_table(cur)
        cur.execute(
            """INSERT INTO backoffice_price_suggestion_acceptance
               (ean_upc,accepted_current_price,accepted_current_price_source,
                accepted_current_price_asof_date,accepted_candidate_price,accepted_by)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (
                upc,row.get("current_price"),row.get("current_price_source"),
                row.get("current_price_observed_date"),row.get("candidate_price"),
                actor,
            ),
        )
        acceptance_id=int(cur.lastrowid)
        conn.commit()
        cur.close()
    return {
        "status":"ACCEPTED",
        "acceptance_id":acceptance_id,
        "upc":upc,
        "current_price":row.get("current_price"),
        "current_price_source":row.get("current_price_source"),
        "current_price_asof_date":row.get("current_price_observed_date"),
        "candidate_price":row.get("candidate_price"),
        "suppression_rule":"UNTIL_PRICE_EVIDENCE_OR_CANDIDATE_CHANGES",
    }
