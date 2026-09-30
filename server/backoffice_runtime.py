from __future__ import annotations

from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from decimal import Decimal
from typing import Any

from business_clock import business_today, completed_through_date
from data_coverage import source_data_days
from coverage_backfill import canonical_pos_qty_by_upc
from db import db_conn
from phase3 import (
    PRICE_TYPE_PRIORITY,
    _current_price as _live_current_price,
    _price_list_upload_business_date,
)
from webapp_v2_runtime import (
    _delivery_pattern,
    _family_effective_oh,
    _family_receipt_events,
    bulk_ordering_suggestions,
    performance_report,
    _numeric_key,
    _safe_qty_uom,
    _seafood_upc_group_signature,
)


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


def ordering_review(category: str = "ALL") -> dict[str, Any]:
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
        pos_latest_days=source_data_days(
            cur,
            "sales_by_price_type",
            limit=1,
            up_to=expected_through,
        )
        mvt_latest_days=source_data_days(
            cur,
            "movement",
            limit=1,
            up_to=expected_through,
        )
        pos_through=pos_latest_days[0]["date"] if pos_latest_days else None
        mvt_through=mvt_latest_days[0]["date"] if mvt_latest_days else None
        missing_required_sources=[]
        if pos_through!=expected_through:
            missing_required_sources.append("POS")
        if mvt_through!=expected_through:
            missing_required_sources.append("MVT")
        ordering_data_health={
            "status":(
                "CURRENT"
                if not missing_required_sources
                else "BLOCKED_STALE_REQUIRED_DATA"
            ),
            "expected_through":expected_through,
            "pos_data_through":pos_through,
            "movement_data_through":mvt_through,
            "missing_required_sources":missing_required_sources,
            "rule":"ORDERING_REQUIRES_CURRENT_COMPLETED_POS_AND_MVT",
        }

        # Reuse the same canonical movement window for every suggested family.
        # The former path re-queried coverage and movement rows twice per family.
        receipt_days=source_data_days(
            cur,
            "movement",
            limit=180,
            up_to=expected_through,
        )
        for kind in kinds:
            bulk = bulk_ordering_suggestions(kind)
            inputs[kind] = bulk.get("inputs")
            skipped.extend(bulk.get("skipped") or [])
            for s in bulk.get("suggestions") or []:
                fid = int(s["family_id"])
                events = _family_receipt_events(cur, fid, data_days=receipt_days)
                receipt = _last_receipt_base_summary_from_events(events)
                pattern = _delivery_pattern(events)
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
                    "suggested_delivery_qty": s.get("suggested_order_qty"),
                    "suggested_delivery_uom": s.get("suggested_order_uom"),
                    "category": s.get("category"),
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
                        "reasons": _suggestion_reason(s, pattern, receipt),
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
    analysis_status=(
        ordering_data_health["status"]
        if ordering_data_health["status"]!="CURRENT"
        else ("READY" if rows else "READY_NO_ELIGIBLE_ITEMS")
    )
    return {
        "contract_version": "BACKOFFICE_ORDERING_REVIEW_V2",
        "category": cat,
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
        },
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


def _quick_receiving_article_context(
    cur,
    qrows: list[dict[str, Any]],
    movement_days_7: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Resolve the operational Receiving Article above Quick Check UPC groups.

    Family Article remains relationship metadata. The displayed 251/252 movement
    belongs to the Receiving Article: 251 sold minus 252 returns in Base UOM.
    """
    family_rows: dict[int, dict[str, Any]] = {}
    for row in qrows:
        if row.get("family_id") is None:
            continue
        fid=int(row["family_id"])
        family_rows.setdefault(fid,row)
    if not family_rows:
        return {}

    fids=sorted(family_rows)
    ph=",".join(["%s"]*len(fids))
    cur.execute(
        f"""SELECT baf.family_id,a.article_number,baf.relationship_type,baf.is_primary
            FROM bridge_article_family baf
            JOIN article a ON a.article_id=baf.article_id
            WHERE baf.family_id IN ({ph})
              AND baf.mapping_status='CONFIRMED'
              AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
            ORDER BY baf.family_id,
                     CASE baf.relationship_type WHEN 'SUB' THEN 0 WHEN 'MAIN' THEN 1 ELSE 2 END,
                     baf.is_primary DESC,a.article_number""",
        tuple(fids),
    )
    receiving_by_family: dict[int,str] = {}
    for r in cur.fetchall():
        fid=int(r["family_id"])
        art=str(r.get("article_number") or "").strip()
        if art and fid not in receiving_by_family:
            receiving_by_family[fid]=art

    # Fail soft to the existing Family Article only when no confirmed Receiving
    # Article mapping exists. The UI labels that fallback explicitly.
    for fid,row in family_rows.items():
        if fid not in receiving_by_family:
            fallback=str(row.get("main_article_number") or "").strip()
            if fallback:
                receiving_by_family[fid]=fallback

    article_numbers=sorted({x for x in receiving_by_family.values() if x})
    movement_by_article: dict[str,dict[str,Any]] = {}
    if article_numbers and movement_days_7:
        aph=",".join(["%s"]*len(article_numbers))
        clauses=[]
        args: list[Any] = list(article_numbers)
        for d in movement_days_7:
            clauses.append("(file_id=%s AND posting_date=%s)")
            args.extend([int(d["file_id"]),d["date"]])
        cur.execute(
            f"""SELECT article_number,base_uom_code,
                       SUM(
                         CASE
                           WHEN movement_type='251' THEN ABS(COALESCE(base_quantity,0))
                           WHEN movement_type='252' THEN -ABS(COALESCE(base_quantity,0))
                           ELSE 0
                         END
                       ) AS qty_7d
                FROM movement_history
                WHERE article_number IN ({aph})
                  AND movement_type IN ('251','252')
                  AND ({' OR '.join(clauses)})
                  AND base_quantity IS NOT NULL
                GROUP BY article_number,base_uom_code""",
            tuple(args),
        )
        grouped: dict[str,list[dict[str,Any]]] = {}
        for r in cur.fetchall():
            grouped.setdefault(str(r.get("article_number") or ""),[]).append(r)
        for art,rows in grouped.items():
            valid=[r for r in rows if r.get("qty_7d") is not None]
            if len(valid)==1:
                movement_by_article[art]={
                    "quantity":_d(valid[0].get("qty_7d")),
                    "uom":valid[0].get("base_uom_code"),
                    "status":"READY",
                }
            elif len(valid)>1:
                movement_by_article[art]={
                    "quantity":None,
                    "uom":None,
                    "status":"MIXED_BASE_UOM",
                }

    day_count=len(movement_days_7)
    out: dict[int,dict[str,Any]] = {}
    for fid,row in family_rows.items():
        receiving=receiving_by_family.get(fid)
        mv=movement_by_article.get(str(receiving or ""),{})
        qty=mv.get("quantity")
        mapped=bool(receiving and str(receiving)!=str(row.get("main_article_number") or ""))
        out[fid]={
            "receiving_article":receiving,
            "receiving_article_mapping_status":"CONFIRMED_RECEIVING_ARTICLE" if mapped else "FAMILY_ARTICLE_FALLBACK",
            "receiving_movement_7d":qty,
            "receiving_movement_uom":mv.get("uom"),
            "receiving_avg_qty_day":(
                _d(qty)/Decimal(day_count)
                if qty is not None and day_count>0
                else None
            ),
            "receiving_movement_days_7d":day_count,
            "receiving_movement_status":mv.get("status") or "NO_251_252_IN_WINDOW",
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
        out = []
        for row in qrows:
            # Mobile Quick Check search is identity + recent-velocity discovery.
            # Do not make search wait for price-history resolution. Authoritative
            # CURRENT price is resolved when the user opens the UPC detail.
            if lightweight:
                live_price = None
            elif row.get("upc_id") is None:
                live_price = None
            else:
                live_price = _live_current_price(
                    cur,
                    int(row["upc_id"]),
                    row.get("ean_upc"),
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
                    "receiving_article": receiving_context.get(fid or -1,{}).get("receiving_article"),
                    "receiving_article_mapping_status": receiving_context.get(fid or -1,{}).get("receiving_article_mapping_status"),
                    "receiving_movement_7d": receiving_context.get(fid or -1,{}).get("receiving_movement_7d"),
                    "receiving_movement_uom": receiving_context.get(fid or -1,{}).get("receiving_movement_uom"),
                    "receiving_avg_qty_day": receiving_context.get(fid or -1,{}).get("receiving_avg_qty_day"),
                    "receiving_movement_days_7d": receiving_context.get(fid or -1,{}).get("receiving_movement_days_7d"),
                    "receiving_movement_status": receiving_context.get(fid or -1,{}).get("receiving_movement_status"),
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
                    # Family quantities are Movement 251-252 metrics and are
                    # expressed in the movement Base UOM, not summed UPC POS units.
                    "family_qty_7d": row.get("family_movement_7d"),
                    "family_qty_uom": row.get("family_movement_uom"),
                    "family_avg_qty_day": (
                        _d(row.get("family_movement_7d")) / Decimal(family_movement_day_count)
                        if row.get("family_movement_7d") is not None and family_movement_day_count > 0
                        else None
                    ),
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
        "contract_version": "BACKOFFICE_INVENTORY_V4",
        "category": cat,
        "query": q or None,
        "count": len(out),
        "rows": out,
        "search": search_meta,
        "rules": {
            "write_enabled": "OH_TRUE_STOCK_ONLY",
            "search_scope": "DIRECT_QUICK_CHECK_THEN_TYPO_FALLBACK",
            "search_sort": "DIRECT_RECENT_VELOCITY_THEN_FUZZY_RELEVANCE",
            "quick_check_group_leader": "RECEIVING_ARTICLE",
            "family_article_role": "RELATIONSHIP_METADATA_NOT_PRIMARY_GROUP_HEADER",
            "receiving_qty_basis": "RECEIVING_ARTICLE_MOVEMENT_251_MINUS_252_BASE_UOM",
            "receiving_avg_qty_day_denominator": "COMPLETED_MOVEMENT_DAYS",
            "family_qty_basis": "LEGACY_RELATIONSHIP_METRIC_ONLY",
            "family_avg_qty_day_denominator": "COMPLETED_MOVEMENT_DAYS",
            "subgroup_qty_basis": "SUM_INDIVIDUAL_UPC_POS_QTY_ONLY_WHEN_DISPLAY_UOM_MATCHES",
            "subgroup_avg_qty_day_denominator": "COMPLETED_POS_DATA_DAYS",
            "lightweight": bool(lightweight),
            "lightweight_skips": (
                ["FAMILY_EFFECTIVE_OH_ROLLFORWARD","LIVE_CURRENT_PRICE_RESOLUTION"]
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

def _pricing_review_data_health() -> dict[str, Any]:
    """Required-source freshness gate for operational price-change decisions.

    Price suggestions depend on completed POS history plus current OH/DOH, which
    in turn depends on movement roll-forward. If either required daily source is
    behind the latest completed business day, do not present an older queue as
    current.
    """
    expected_through = completed_through_date()
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        pos_days = source_data_days(
            cur,
            "sales_by_price_type",
            limit=1,
            up_to=expected_through,
        )
        mvt_days = source_data_days(
            cur,
            "movement",
            limit=1,
            up_to=expected_through,
        )
        cur.close()
    pos_through = pos_days[0]["date"] if pos_days else None
    mvt_through = mvt_days[0]["date"] if mvt_days else None
    missing = []
    if pos_through != expected_through:
        missing.append("POS")
    if mvt_through != expected_through:
        missing.append("MVT")
    return {
        "status": "CURRENT" if not missing else "BLOCKED_STALE_REQUIRED_DATA",
        "expected_through": expected_through,
        "pos_data_through": pos_through,
        "movement_data_through": mvt_through,
        "missing_required_sources": missing,
        "rule": "PRICE_REVIEW_REQUIRES_CURRENT_COMPLETED_POS_AND_MVT",
    }


def pricing_review(category: str = "ALL", limit: int = 1000, *, include_accepted: bool = False) -> dict[str, Any]:
    """Pricing suggestions with CURRENT fields from live Quick Check serving.

    Accepted suggestions are suppressed only while the current-price evidence
    and candidate-price fingerprint remain unchanged. New current price evidence
    or a changed candidate automatically makes the UPC eligible to appear again.

    Operational review fails closed when completed POS or MVT coverage is stale.
    """
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "LIVE", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")

    data_health = _pricing_review_data_health()
    if data_health["status"] != "CURRENT":
        return {
            "contract_version": "BACKOFFICE_PRICING_REVIEW_V6",
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

    report = performance_report(category=cat, limit=limit)
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
                f"""SELECT upc_id,ean_upc,current_price,current_price_type,
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
        "contract_version": "BACKOFFICE_PRICING_REVIEW_V6",
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
) -> dict[str, Any]:
    upc=str(ean_upc or "").strip()
    if not upc:
        raise ValueError("UPC_REQUIRED")
    if current_price is None or candidate_price is None:
        raise ValueError("CURRENT_AND_CANDIDATE_PRICE_REQUIRED")

    # Recompute including already accepted rows so the click is bound to the
    # currently valid server-side suggestion rather than a stale browser row.
    snapshot=pricing_review(category="ALL",limit=1000,include_accepted=True)
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
