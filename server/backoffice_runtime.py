from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from difflib import SequenceMatcher
from decimal import Decimal, ROUND_HALF_UP
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
    _latest_cost as _family_current_cost,
    _price_list_upload_business_date,
)
from receipt_semantics import physical_receipt_stage_rows
from webapp_v2_runtime import (
    _batch_daily_sales_by_price_type,
    _batch_sales_metric,
    _canonical_report_date_sales,
    _delivery_pattern,
    _delivery_day_evidence,
    _family_effective_oh,
    _overlay_active_true_stock_effective_oh,
    _family_system_oh,
    _family_receipt_events,
    _family_receipt_events_bulk,
    _ordering_candidate_families,
    _gp_day_price_suggestion_from_batch,
    _performance_cost_for_day,
    _performance_range_cost_rows,
    _retail_price_point,
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
                    "source_since_date": None,
                    "price_list_file_id": None,
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
                "source_since_date": config.get("source_since_date"),
                "price_list_file_id": config.get("file_id"),
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
    # One physical delivery is either 101 or the 109 side of a 107+109 flow.
    # 107 is cost-stage evidence only and must never add delivery quantity.
    return physical_receipt_stage_rows(rows)


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
              AND movement_type IN ('101','102','109','110')
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



def _article_manual_family_pack_context(
    cur,
    family_article: str | None,
) -> dict[str, Any]:
    """Return the newest Article Manual receiving-pack evidence for a Family.

    Authoritative Seafood tab semantics:
      Fresh Fish / Live Fish / Shrimp / Fish Ball / Frozen Fish -> column G
      Frozen Pack -> column E

    Do not fall back to an older Article Manual file when the newest file that
    contains the Family has a blank pack field; stale pack data must not be
    presented as current authority.
    """
    main=str(family_article or "").strip()
    if not main:
        return {
            "pack_size":None,
            "pack_size_options":[],
            "status":"FAMILY_ARTICLE_MISSING",
            "source":"ARTICLE_MANUAL",
            "file_id":None,
        }

    cur.execute(
        """SELECT f.file_id,sh.sheet_name,r.raw_id,
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
             AND TRIM(JSON_UNQUOTE(JSON_EXTRACT(r.raw_payload,'$.A')))=%s
           ORDER BY f.file_id DESC,r.raw_id DESC""",
        (main,),
    )
    rows=cur.fetchall()
    if not rows:
        return {
            "pack_size":None,
            "pack_size_options":[],
            "status":"NO_ARTICLE_MANUAL_ROW",
            "source":"ARTICLE_MANUAL",
            "file_id":None,
        }

    newest_file=int(rows[0]["file_id"])
    options=[]
    for row in rows:
        if int(row.get("file_id") or 0)!=newest_file:
            continue
        tab=str(row.get("sheet_name") or "").strip().lower()
        raw=row.get("col_e") if tab=="frozen pack" else row.get("col_g")
        value=str(raw or "").strip()
        if not value or value.upper() in {"N/A","NA","NONE","NULL","NAN","-","—"}:
            continue
        if value not in options:
            options.append(value)

    if len(options)==1:
        return {
            "pack_size":options[0],
            "pack_size_options":options,
            "status":"READY",
            "source":"ARTICLE_MANUAL",
            "file_id":newest_file,
        }
    if len(options)>1:
        return {
            "pack_size":None,
            "pack_size_options":options,
            "status":"MULTIPLE_PACK_SIZES",
            "source":"ARTICLE_MANUAL",
            "file_id":newest_file,
        }
    return {
        "pack_size":None,
        "pack_size_options":[],
        "status":"PACK_SIZE_MISSING",
        "source":"ARTICLE_MANUAL",
        "file_id":newest_file,
    }


def _observed_receipt_pack_size(event: dict[str, Any]) -> str | None:
    """Derive an observed Base-per-Receiving-UOM pack ratio from one receipt.

    This is fallback evidence only when Article Manual does not provide a single
    current pack size. It is intentionally not used when entry/base UOM are the
    same because that would invent a case/pack conversion.
    """
    entry_qty=event.get("receipt_quantity")
    base_qty=event.get("base_receipt_quantity")
    entry_uom=str(event.get("receipt_uom") or "").strip().upper()
    base_uom=str(event.get("base_receipt_uom") or "").strip().upper()
    if (
        entry_qty is None
        or base_qty is None
        or not entry_uom
        or not base_uom
        or entry_uom==base_uom
        or _d(entry_qty)<=0
        or _d(base_qty)<=0
    ):
        return None
    ratio=_d(base_qty)/_d(entry_qty)
    if ratio<=0:
        return None
    ratio_text=format(ratio.normalize(),"f")
    return f"{ratio_text} {base_uom} / {entry_uom}"



def _article_description_map(
    cur,
    article_numbers: list[str] | set[str] | tuple[str, ...],
) -> dict[str, str]:
    """Resolve human-readable SAP Article names without guessing."""
    arts=sorted({
        str(x or "").strip()
        for x in article_numbers or []
        if str(x or "").strip()
    })
    if not arts:
        return {}

    ph=",".join(["%s"]*len(arts))
    out: dict[str,str]={}
    cur.execute(
        f"""SELECT article_number,article_description
            FROM article
            WHERE article_number IN ({ph})
              AND article_description IS NOT NULL
              AND TRIM(article_description)<>''""",
        tuple(arts),
    )
    for row in cur.fetchall():
        art=str(row.get("article_number") or "").strip()
        desc=str(row.get("article_description") or "").strip()
        if art and desc:
            out[art]=desc

    missing=[x for x in arts if x not in out]
    if missing:
        mph=",".join(["%s"]*len(missing))
        cur.execute(
            f"""SELECT article_number,MAX(description) AS article_description
                FROM movement_history
                WHERE article_number IN ({mph})
                  AND description IS NOT NULL
                  AND TRIM(description)<>''
                GROUP BY article_number""",
            tuple(missing),
        )
        for row in cur.fetchall():
            art=str(row.get("article_number") or "").strip()
            desc=str(row.get("article_description") or "").strip()
            if art and desc:
                out[art]=desc
    return out


def _historical_receiving_article_summary(
    cur,
    family_article: str | None,
    events: list[dict[str, Any]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Summarize historically used Receiving Articles for an ordering Family."""
    pack=_article_manual_family_pack_context(cur,family_article)
    grouped: dict[str,dict[str,Any]] = {}

    for event in events or []:
        article=str(event.get("article_number") or "").strip()
        posting_date=event.get("posting_date")
        receipt_qty=event.get("receipt_quantity")
        base_qty=event.get("base_receipt_quantity")
        if not article or posting_date is None:
            continue
        if (
            (receipt_qty is None or _d(receipt_qty)<=0)
            and (base_qty is None or _d(base_qty)<=0)
        ):
            continue

        slot=grouped.setdefault(
            article,
            {
                "article_number":article,
                "last_receipt_date":posting_date,
                "receipt_event_count":0,
                "observed_pack_size":None,
                "observed_pack_date":None,
            },
        )
        slot["receipt_event_count"]+=1
        if posting_date>slot["last_receipt_date"]:
            slot["last_receipt_date"]=posting_date

        observed=_observed_receipt_pack_size(event)
        if observed and (
            slot.get("observed_pack_date") is None
            or posting_date>=slot["observed_pack_date"]
        ):
            slot["observed_pack_size"]=observed
            slot["observed_pack_date"]=posting_date

    article_names=_article_description_map(cur,set(grouped))
    out=[]
    for slot in grouped.values():
        if pack.get("status")=="READY" and pack.get("pack_size"):
            pack_size=pack.get("pack_size")
            pack_source="ARTICLE_MANUAL"
            pack_status="READY"
        elif slot.get("observed_pack_size"):
            pack_size=slot.get("observed_pack_size")
            pack_source="HISTORICAL_RECEIPT_CONVERSION"
            pack_status="OBSERVED"
        elif pack.get("pack_size_options"):
            opts=list(pack.get("pack_size_options") or [])
            pack_size=" / ".join(opts[:2])+(" …" if len(opts)>2 else "")
            pack_source="ARTICLE_MANUAL"
            pack_status="MULTIPLE"
        else:
            pack_size=None
            pack_source=pack.get("source") or "ARTICLE_MANUAL"
            pack_status=pack.get("status") or "MISSING"

        out.append({
            "article_number":slot["article_number"],
            "article_name":article_names.get(slot["article_number"]),
            "last_receipt_date":slot["last_receipt_date"],
            "receipt_event_count":slot["receipt_event_count"],
            "pack_size":pack_size,
            "pack_size_status":pack_status,
            "pack_size_source":pack_source,
            "article_manual_file_id":pack.get("file_id"),
        })

    out.sort(
        key=lambda x:(
            -(x["last_receipt_date"].toordinal() if x.get("last_receipt_date") else 0),
            -int(x.get("receipt_event_count") or 0),
            str(x.get("article_number") or ""),
        )
    )
    return out[:max(1,min(int(limit or 8),20))]



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



def yipman_ordering_calendar(
    lookback_days: int = 180,
    days: int = 28,
) -> dict[str, Any]:
    """Return observed delivery weekdays plus preferred future defaults.

    Every weekday with canonical physical receipt evidence remains highlighted.
    Defaults use the strongest observed weekdays so one-off receipt history does
    not become the automatic Delivery / Next Delivery pair.
    """
    lookback=max(28,min(int(lookback_days or 180),180))
    horizon=max(14,min(int(days or 28),42))
    today=business_today()
    names=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    weekday_stats={
        wd:{
            "weekday":names[wd],
            "weekday_number":wd,
            "family_ids":set(),
            "receipt_dates":set(),
            "receipt_event_count":0,
        }
        for wd in range(7)
    }

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        mvt_days=source_data_days(
            cur,
            "movement",
            limit=lookback,
            up_to=completed_through_date(),
        )
        families_by_id: dict[int,dict[str,Any]]={}
        for kind in ("FRESH","FROZEN"):
            for fam in _ordering_candidate_families(cur,kind):
                families_by_id[int(fam["family_id"])]=fam
        family_ids=sorted(families_by_id)
        event_map=_family_receipt_events_bulk(
            cur,
            family_ids,
            data_days=mvt_days,
        ) if family_ids else {}

        for fid in family_ids:
            family_weekdays=set()
            for event in event_map.get(fid) or []:
                posting_date=event.get("posting_date")
                quantity=event.get("receipt_quantity")
                if posting_date is None or quantity is None or _d(quantity)<=0:
                    continue
                wd=int(posting_date.weekday())
                family_weekdays.add(wd)
                weekday_stats[wd]["receipt_dates"].add(posting_date)
                weekday_stats[wd]["receipt_event_count"]+=1
            for wd in family_weekdays:
                weekday_stats[wd]["family_ids"].add(fid)
        cur.close()

    ranked=[
        {
            "weekday":x["weekday"],
            "weekday_number":x["weekday_number"],
            "family_count":len(x["family_ids"]),
            "receipt_date_count":len(x["receipt_dates"]),
            "receipt_event_count":x["receipt_event_count"],
            "observed":bool(x["family_ids"]),
        }
        for x in weekday_stats.values()
        if x["family_ids"]
    ]
    ranked.sort(
        key=lambda x:(
            -int(x["family_count"]),
            -int(x["receipt_date_count"]),
            int(x["weekday_number"]),
        )
    )

    preferred=set()
    if ranked:
        preferred.add(int(ranked[0]["weekday_number"]))
        if len(ranked)>=2:
            top_count=int(ranked[0]["family_count"])
            second_count=int(ranked[1]["family_count"])
            secondary_threshold=max(2,(top_count+9)//10)
            if second_count>=secondary_threshold:
                preferred.add(int(ranked[1]["weekday_number"]))

    row_by_wd={int(x["weekday_number"]):x for x in ranked}
    rows=[]
    for wd,name in enumerate(names):
        source=row_by_wd.get(wd) or {}
        rows.append({
            "weekday":name,
            "weekday_number":wd,
            "family_count":int(source.get("family_count") or 0),
            "receipt_date_count":int(source.get("receipt_date_count") or 0),
            "receipt_event_count":int(source.get("receipt_event_count") or 0),
            "observed":bool(source),
            "preferred":wd in preferred,
        })
    rows.sort(
        key=lambda x:(
            0 if x["preferred"] else 1,
            -int(x["family_count"]),
            -int(x["receipt_date_count"]),
            int(x["weekday_number"]),
        )
    )

    dates=[]
    for offset in range(0,horizon+1):
        d=today+timedelta(days=offset)
        wd=int(d.weekday())
        stat=next((x for x in rows if int(x["weekday_number"])==wd),None) or {}
        dates.append({
            "date":d,
            "weekday":names[wd],
            "weekday_number":wd,
            "observed":bool(stat.get("observed")),
            "preferred":bool(stat.get("preferred")),
            "family_count":int(stat.get("family_count") or 0),
            "receipt_date_count":int(stat.get("receipt_date_count") or 0),
        })

    future=[x for x in dates if x["date"]>today]
    observed_dates=[x for x in future if x["observed"]]

    # Default to the next occurrence of the weekday with the strongest
    # canonical delivery history. This is intentionally NOT "the earliest
    # observed day" when a weaker one happens to occur first.
    strongest_weekday=(
        int(ranked[0]["weekday_number"])
        if ranked else None
    )
    strongest_dates=[
        x for x in future
        if strongest_weekday is not None
        and int(x["weekday_number"])==strongest_weekday
    ]
    default_delivery=(
        strongest_dates[0]["date"]
        if strongest_dates else (
            observed_dates[0]["date"] if observed_dates else today+timedelta(days=1)
        )
    )
    # Regular Ordering assumes the next cycle is one week after the chosen
    # delivery unless the user explicitly overrides it in the UI.
    default_next=default_delivery+timedelta(days=7)

    return {
        "contract_version":"YIPMAN_ORDERING_CALENDAR_V3_STRONGEST_DAY_PLUS_7",
        "as_of":today,
        "movement_data_through":mvt_days[0]["date"] if mvt_days else None,
        "lookback_days":lookback,
        "horizon_days":horizon,
        "rows":rows,
        "dates":dates,
        "preferred_weekdays":sorted(preferred),
        "default_delivery_date":default_delivery,
        "default_next_delivery_date":default_next,
        "rules":{
            "receipt_basis":"CANONICAL_PHYSICAL_101_109",
            "all_observed_days_remain_visible":True,
            "preferred_defaults":"NEXT_OCCURRENCE_OF_STRONGEST_OBSERVED_WEEKDAY_BY_FAMILY_COUNT_THEN_RECEIPT_DATE_COUNT",
            "next_delivery_default":"CHOSEN_DELIVERY_PLUS_7_CALENDAR_DAYS",
            "one_off_observed_days_are_not_removed":True,
            "write_enabled":False,
        },
    }


def _suggestion_reason(row: dict[str, Any], pattern: dict[str, Any], receipt: dict[str, Any]) -> list[dict[str, str]]:
    uom=str(row.get("uom") or "")
    coverage=row.get("forecast_coverage_usage")
    projected=row.get("projected_oh_at_delivery")
    usable=row.get("usable_oh_at_delivery")
    shortage=row.get("pre_delivery_stockout_qty")
    reasons=[
        {
            "title":"Family demand",
            "detail":(
                f"7D family movement {row.get('qty_7d')} {uom}; "
                f"28D family movement {row.get('qty_28d')} {uom}. "
                f"Regular forecast confidence {row.get('regular_forecast_confidence') or '—'}."
            ),
        },
        {
            "title":"Inventory at delivery",
            "detail":(
                f"Current ordering OH {row.get('ordering_oh_used')} {uom}; "
                f"forecast usage before delivery {row.get('forecast_usage_before_delivery')} {uom}; "
                f"projected OH at delivery {projected} {uom}; usable {usable} {uom}."
            ),
        },
        {
            "title":"Coverage window",
            "detail":(
                f"Eligible demand after delivery is {coverage} {uom}; "
                f"suggested delivery quantity is {row.get('suggested_order_qty')} "
                f"{row.get('suggested_order_uom') or uom}."
            ),
        },
        {
            "title":"Receiving cadence",
            "detail":_frequency_label(pattern),
        },
    ]
    if _d(shortage)>0:
        reasons.append({
            "title":"Pre-delivery stockout risk",
            "detail":(
                f"Projected shortage before this delivery is {shortage} {uom}. "
                "That lost-sales risk is flagged separately and is not backordered into a delivery that arrives later."
            ),
        })
    if row.get("freshness_coverage_capped"):
        reasons.append({
            "title":"Freshness guard",
            "detail":(
                "The selected next-delivery interval exceeds the Fresh/Live 7-day freshness limit. "
                f"Order coverage is capped through {row.get('effective_coverage_end_date')}; "
                f"{row.get('freshness_uncovered_usage')} {uom} of later forecast demand requires an earlier/split delivery."
            ),
        })
    if row.get("freshness_adjustment_applied"):
        reasons.append({
            "title":"Current OH freshness adjustment",
            "detail":(
                f"Latest valid receipt {row.get('freshness_latest_receipt_date')}; "
                f"current DOH {row.get('freshness_current_doh')}; freshness threshold "
                f"{row.get('freshness_threshold_days')} days. "
                f"Projected discard {row.get('freshness_projected_discard_qty')} {uom}; "
                f"only {row.get('freshness_existing_oh_credit')} {uom} of existing OH is credited "
                f"to this delivery window. Ordering increased by "
                f"{row.get('freshness_order_qty_lift')} {uom} versus treating all OH as fresh."
            ),
        })
    if receipt.get("date"):
        reasons.append({
            "title":"Last receipt",
            "detail":(
                f"Last receipt {receipt.get('date')} · {receipt.get('quantity')} "
                f"{receipt.get('base_uom') or ''} in Base UOM."
            ),
        })
    return reasons


def ordering_review(
    category: str = "ALL",
    delivery_date: date | None = None,
    next_delivery_date: date | None = None,
    *,
    best_available_delivery_evidence: bool = True,
) -> dict[str, Any]:
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_FRESH_OR_FROZEN")
    if next_delivery_date is not None and delivery_date is None:
        raise ValueError("NEXT_DELIVERY_REQUIRES_DELIVERY_DATE")
    if (
        delivery_date is not None
        and next_delivery_date is not None
        and next_delivery_date <= delivery_date
    ):
        raise ValueError("NEXT_DELIVERY_MUST_BE_AFTER_DELIVERY_DATE")

    kinds = [cat] if cat != "ALL" else ["FRESH", "FROZEN"]
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    inputs: dict[str, Any] = {}

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        expected_through=completed_through_date()
        # Ordering never waits for a grace deadline. Read enough canonical
        # history to use the newest source data that actually exists.
        source_limit=60
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

        # Suggestions use each source independently. POS drives demand history;
        # MVT drives receipt cadence / inventory movement. Missing dates are
        # excluded, never zero-filled and never a freshness blocker.
        available_dates=[x for x in (pos_through,mvt_through) if x is not None]
        common_data_through=min(available_dates) if len(available_dates)==2 else None
        stale_days=(
            max(0,(expected_through-common_data_through).days)
            if common_data_through is not None else None
        )
        can_estimate=pos_through is not None and mvt_through is not None
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
            "rule":"ORDERING_USES_LATEST_AVAILABLE_POS_AND_MVT_INDEPENDENTLY_NO_FRESHNESS_GATE",
            "warning":(
                None
                if not missing_required_sources
                else (
                    f"Best available estimate uses POS through {pos_through} and "
                    f"MVT through {mvt_through}; missing dates are ignored, not zero-filled. "
                    f"Reference completed date is {expected_through}."
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
                "selected_next_delivery_date":next_delivery_date,
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
                    "requires_common_pos_mvt_date":False,
                    "missing_dates_block_suggestions":False,
                },
            }

        # Reuse the same canonical movement window for every suggested family.
        # The former path re-queried coverage and movement rows twice per family.
        receipt_days=source_data_days(
            cur,
            "movement",
            limit=180,
            up_to=mvt_through,
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
                                # SAP material/article document is the receipt document
                                # used by Yipman as the GR trace number.
                                "gr_number":x.get("gr_number"),
                                "gr_number_source":x.get("gr_number_source"),
                                "article_document":x.get("article_document"),
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
                "contract_version":"BACKOFFICE_ORDERING_REVIEW_V9_YIPMAN_GR_5014_AUTHORITY",
                "category":cat,
                "selected_delivery_date":delivery_date,
                "selected_next_delivery_date":next_delivery_date,
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
                    "history_basis":"ACTUAL_CANONICAL_PHYSICAL_101_109_RECEIPTS_ON_SELECTED_DATE",
                    "receipt_quantity_basis":"BASE_UOM_WHEN_RECONCILABLE_ELSE_ENTRY_UOM",
                    "write_enabled":False,
                },
            }

        for kind in kinds:
            delivery_cache: dict[int, tuple[dict[str,Any],dict[str,Any],dict[str,Any]]] = {}
            delivery_event_cache: dict[int,list[dict[str,Any]]] = {}
            candidate_family_map: dict[int,dict[str,Any]] = {}
            eligible_family_ids: list[int] | None = None

            # Delivery-date mode must filter on receipt cadence before running
            # expensive 28D family demand / OH / baseline calculations.
            if delivery_date is not None:
                eligible_family_ids=[]
                candidate_families=_ordering_candidate_families(cur,kind)
                candidate_family_map={
                    int(x["family_id"]):x for x in candidate_families
                }
                event_map=_family_receipt_events_bulk(
                    cur,
                    [int(x["family_id"]) for x in candidate_families],
                    data_days=receipt_days,
                )
                for fam in candidate_families:
                    fid=int(fam["family_id"])
                    events=event_map.get(fid) or []
                    delivery_event_cache[fid]=events
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

            # Inventory movement evidence is current through the newest usable
            # MVT date. Forecast missing later calendar days instead of blocking.
            forecast_start_date=mvt_through+timedelta(days=1)
            bulk_kwargs: dict[str,Any] = {
                "ordering_date":forecast_start_date,
                "expected_delivery_date":delivery_date,
                "next_delivery_date":next_delivery_date,
                "include_sufficient_stock":bool(delivery_date),
                "family_ids":eligible_family_ids,
            }
            supported=set(inspect.signature(bulk_ordering_suggestions).parameters)
            bulk_kwargs={k:v for k,v in bulk_kwargs.items() if k in supported}

            if delivery_date is not None and not eligible_family_ids:
                bulk={
                    "inputs":{
                        "expected_delivery_date":delivery_date,
                        "next_delivery_date":next_delivery_date,
                    },
                    "suggestions":[],
                    "skipped":[],
                    "rules":{"delivery_prefilter_short_circuit":True},
                }
            else:
                bulk=bulk_ordering_suggestions(kind,**bulk_kwargs)

            inputs[kind] = bulk.get("inputs")
            bulk_skipped=list(bulk.get("skipped") or [])
            skipped.extend(bulk_skipped)
            bulk_skipped_by_family={
                int(x["family_id"]):x
                for x in bulk_skipped
                if x.get("family_id") is not None
            }
            emitted_family_ids: set[int] = set()
            for s in bulk.get("suggestions") or []:
                fid = int(s["family_id"])
                if delivery_date is not None:
                    cached=delivery_cache.get(fid)
                    if not cached:
                        # Compatibility with an older worker that cannot accept
                        # family_ids: never leak a nonmatching delivery family.
                        continue
                    receipt,pattern,delivery_day=cached
                    events=delivery_event_cache.get(fid) or []
                else:
                    events = _family_receipt_events(cur, fid, data_days=receipt_days)
                    receipt = _last_receipt_base_summary_from_events(events)
                    pattern = _delivery_pattern(events)
                    delivery_day = None

                receiving_article = receipt.get("receiving_article") or _fallback_receiving_article(
                    cur, fid, str(s.get("family_article_number") or "") or None
                )
                suggested_qty=s.get("suggested_order_qty")
                historical_receiving_articles=(
                    _historical_receiving_article_summary(
                        cur,
                        str(s.get("family_article_number") or "") or None,
                        events,
                    )
                    if suggested_qty is not None and _d(suggested_qty)>0
                    else []
                )
                receiving_names=_article_description_map(
                    cur,
                    [receiving_article] if receiving_article else [],
                )
                receiving_article_name=receiving_names.get(str(receiving_article or "").strip())
                row = {
                    "family_id": fid,
                    "family_name": s.get("family_article_name"),
                    "family_article": s.get("family_article_number"),
                    "receiving_article": receiving_article,
                    "receiving_article_name": receiving_article_name,
                    "historical_receiving_articles": historical_receiving_articles,
                    "oh": s.get("ordering_oh_used"),
                    "oh_uom": s.get("uom"),
                    "last_receipt_date": receipt.get("date"),
                    "last_receipt_qty_base": receipt.get("quantity"),
                    "last_receipt_base_uom": receipt.get("base_uom"),
                    "last_receipt_status": receipt.get("status"),
                    "ordering_frequency": _frequency_label(pattern),
                    "ordering_frequency_raw": pattern.get("frequency"),
                    "selected_delivery_date": delivery_date,
                    "selected_next_delivery_date": next_delivery_date,
                    "delivery_day": delivery_day.get("weekday") if delivery_day else None,
                    "delivery_day_observed_count": delivery_day.get("observed_count") if delivery_day else None,
                    "delivery_day_receipt_count": delivery_day.get("receipt_date_count") if delivery_day else pattern.get("receipt_date_count"),
                    "delivery_day_confidence_pct": delivery_day.get("confidence_percent") if delivery_day else pattern.get("confidence_percent"),
                    "delivery_day_confidence": delivery_day.get("confidence") if delivery_day else pattern.get("confidence"),
                    "suggested_delivery_qty": s.get("suggested_order_qty"),
                    "suggested_delivery_uom": s.get("suggested_order_uom"),
                    "roster_status": (
                        "ORDER"
                        if _d(s.get("suggested_order_qty"))>0
                        else "ZERO_ORDER"
                    ),
                    "roster_reason": None,
                    "category": s.get("category"),
                    "data_status": ordering_data_health.get("status"),
                    "data_through": common_data_through,
                    "expected_through": expected_through,
                    "stale_calendar_days": stale_days,
                    "estimate_only": bool(missing_required_sources),
                    "pre_delivery_stockout_risk":bool(s.get("pre_delivery_stockout_risk")),
                    "pre_delivery_stockout_qty":s.get("pre_delivery_stockout_qty"),
                    "freshness_coverage_capped":bool(s.get("freshness_coverage_capped")),
                    "freshness_adjustment_applied":bool(s.get("freshness_adjustment_applied")),
                    "freshness_projected_discard_qty":s.get("freshness_projected_discard_qty"),
                    "freshness_current_doh":s.get("freshness_current_doh"),
                    "freshness_discard_date":s.get("freshness_discard_date"),
                    "freshness_order_qty_lift":s.get("freshness_order_qty_lift"),
                    "attention": bool(
                        (
                            s.get("dos") is not None
                            and _d(s.get("dos")) < Decimal("3")
                        )
                        or bool(s.get("pre_delivery_stockout_risk"))
                        or bool(s.get("freshness_coverage_capped"))
                        or bool(s.get("freshness_adjustment_applied"))
                    ),
                    "details": {
                        "qty_7d": s.get("qty_7d"),
                        "qty_28d": s.get("qty_28d"),
                        "velocity_7d": s.get("velocity_7d"),
                        "dos": s.get("dos"),
                        "effective_oh_raw": s.get("effective_oh_raw"),
                        "ordering_oh_used": s.get("ordering_oh_used"),
                        "forecast_total_usage":s.get("forecast_total_usage"),
                        "forecast_usage_before_delivery":s.get("forecast_usage_before_delivery"),
                        "forecast_coverage_usage":s.get("forecast_coverage_usage"),
                        "forecast_requested_coverage_usage":s.get("forecast_requested_coverage_usage"),
                        "projected_oh_at_delivery":s.get("projected_oh_at_delivery"),
                        "usable_oh_at_delivery":s.get("usable_oh_at_delivery"),
                        "pre_delivery_stockout_risk":s.get("pre_delivery_stockout_risk"),
                        "pre_delivery_stockout_qty":s.get("pre_delivery_stockout_qty"),
                        "freshness_coverage_capped":s.get("freshness_coverage_capped"),
                        "freshness_uncovered_usage":s.get("freshness_uncovered_usage"),
                        "effective_coverage_end_date":s.get("effective_coverage_end_date"),
                        "freshness_threshold_days":s.get("freshness_threshold_days"),
                        "freshness_reference_status":s.get("freshness_reference_status"),
                        "freshness_latest_receipt_date":s.get("freshness_latest_receipt_date"),
                        "freshness_current_doh":s.get("freshness_current_doh"),
                        "freshness_discard_date":s.get("freshness_discard_date"),
                        "freshness_existing_oh_credit":s.get("freshness_existing_oh_credit"),
                        "freshness_projected_discard_qty":s.get("freshness_projected_discard_qty"),
                        "freshness_projected_discard_before_delivery":s.get("freshness_projected_discard_before_delivery"),
                        "freshness_projected_discard_during_coverage":s.get("freshness_projected_discard_during_coverage"),
                        "suggested_order_qty_without_freshness":s.get("suggested_order_qty_without_freshness"),
                        "freshness_order_qty_lift":s.get("freshness_order_qty_lift"),
                        "freshness_adjustment_applied":s.get("freshness_adjustment_applied"),
                        "regular_forecast_confidence":s.get("regular_forecast_confidence"),
                        "daily_forecast":s.get("daily_forecast"),
                        "weekday_usage_forecast":s.get("weekday_usage_forecast"),
                        "weekday_usage_forecast_basis":s.get("weekday_usage_forecast_basis"),
                        "regular_baseline":s.get("regular_baseline"),
                        "receiving_articles_on_last_receipt": receipt.get("receiving_articles"),
                        "historical_receiving_articles": historical_receiving_articles,
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
                emitted_family_ids.add(fid)

            # Delivery-date mode is a receipt-cadence roster first. Never hide a
            # Family merely because demand/OH/UOM math could not produce a
            # numeric recommendation. Every Family with observed selected-day
            # receipt evidence is returned with ORDER, ZERO_ORDER, or REVIEW.
            if delivery_date is not None:
                no_recent_sales_reasons={"NO_28D_SALES","NO_7D_VELOCITY"}
                for fid in eligible_family_ids or []:
                    if fid in emitted_family_ids:
                        continue
                    fam=candidate_family_map.get(fid) or {}
                    cached=delivery_cache.get(fid)
                    if not cached:
                        continue
                    receipt,pattern,delivery_day=cached
                    calc=bulk_skipped_by_family.get(fid) or {}
                    reason=str(calc.get("reason") or "ORDERING_CALCULATION_UNAVAILABLE")
                    no_recent_sales=reason in no_recent_sales_reasons
                    receiving_article=receipt.get("receiving_article") or _fallback_receiving_article(
                        cur,
                        fid,
                        str(fam.get("main_article_number") or "") or None,
                    )
                    receiving_article_name=_article_description_map(
                        cur,
                        [receiving_article] if receiving_article else [],
                    ).get(str(receiving_article or "").strip())
                    roster_uom=(
                        calc.get("demand_uom")
                        or calc.get("oh_uom")
                        or receipt.get("base_uom")
                    )
                    rows.append({
                        "family_id":fid,
                        "family_name":fam.get("family_description"),
                        "family_article":fam.get("main_article_number"),
                        "receiving_article":receiving_article,
                        "receiving_article_name":receiving_article_name,
                        "historical_receiving_articles":[],
                        "oh":calc.get("oh"),
                        "oh_uom":calc.get("oh_uom") or roster_uom,
                        "last_receipt_date":receipt.get("date"),
                        "last_receipt_qty_base":receipt.get("quantity"),
                        "last_receipt_base_uom":receipt.get("base_uom"),
                        "last_receipt_status":receipt.get("status"),
                        "ordering_frequency":_frequency_label(pattern),
                        "ordering_frequency_raw":pattern.get("frequency"),
                        "selected_delivery_date":delivery_date,
                        "selected_next_delivery_date":next_delivery_date,
                        "delivery_day":delivery_day.get("weekday"),
                        "delivery_day_observed_count":delivery_day.get("observed_count"),
                        "delivery_day_receipt_count":delivery_day.get("receipt_date_count"),
                        "delivery_day_confidence_pct":delivery_day.get("confidence_percent"),
                        "delivery_day_confidence":delivery_day.get("confidence"),
                        "suggested_delivery_qty":Decimal("0") if no_recent_sales else None,
                        "suggested_delivery_uom":roster_uom,
                        "roster_status":"ZERO_ORDER" if no_recent_sales else "REVIEW",
                        "roster_reason":reason,
                        "category":kind,
                        "data_status":ordering_data_health.get("status"),
                        "data_through":common_data_through,
                        "expected_through":expected_through,
                        "stale_calendar_days":stale_days,
                        "estimate_only":bool(missing_required_sources),
                        "attention":not no_recent_sales,
                        "details":{
                            "qty_7d":calc.get("qty_7d"),
                            "qty_28d":calc.get("qty_28d"),
                            "velocity_7d":calc.get("velocity_7d"),
                            "dos":calc.get("dos"),
                            "effective_oh_raw":calc.get("oh"),
                            "ordering_oh_used":calc.get("oh"),
                            "forecast_total_usage":None,
                            "forecast_usage_before_delivery":None,
                            "projected_oh_at_delivery":None,
                            "regular_baseline":None,
                            "receiving_articles_on_last_receipt":receipt.get("receiving_articles"),
                            "delivery_pattern":pattern,
                            "delivery_day_evidence":delivery_day,
                            "roster_reason":reason,
                            "reasons":[
                                {
                                    "title":"Roster status",
                                    "detail":(
                                        "Observed delivery Family retained in the selected-day roster. "
                                        + (
                                            "No numeric order is suggested because recent demand is inactive or has no usable 7D velocity."
                                            if no_recent_sales else
                                            f"Order quantity requires review because {reason}."
                                        )
                                    ),
                                },
                                {
                                    "title":"Selected delivery day",
                                    "detail":(
                                        f"Observed {delivery_day.get('weekday')} "
                                        f"{delivery_day.get('observed_count')}/{delivery_day.get('receipt_date_count')} receipt dates "
                                        f"in the recent {delivery_day.get('lookback_days')} day window · "
                                        f"{delivery_day.get('confidence_percent')}% confidence."
                                    ),
                                },
                            ],
                        },
                    })
        cur.close()

    rows.sort(
        key=lambda x: (
            0 if str(x.get("roster_status") or "")=="ORDER" else (
                1 if str(x.get("roster_status") or "")=="REVIEW" else 2
            ),
            -float(x.get("suggested_delivery_qty") or 0),
            str(x.get("family_name") or ""),
        )
    )
    roster_summary={
        "observed_family_count":len(rows) if delivery_date is not None else None,
        "order_count":sum(
            1 for x in rows
            if str(x.get("roster_status") or "")=="ORDER"
        ),
        "zero_order_count":sum(
            1 for x in rows
            if str(x.get("roster_status") or "")=="ZERO_ORDER"
        ),
        "review_count":sum(
            1 for x in rows
            if str(x.get("roster_status") or "")=="REVIEW"
        ),
    }
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
        "contract_version": "BACKOFFICE_ORDERING_REVIEW_V19_RECEIVING_PACK",
        "category": cat,
        "selected_delivery_date": delivery_date,
        "selected_next_delivery_date": next_delivery_date,
        "selected_delivery_weekday": (
            ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][delivery_date.weekday()]
            if delivery_date else None
        ),
        "analysis_status": analysis_status,
        "data_health": ordering_data_health,
        "count": len(rows),
        "rows": rows,
        "roster_summary": roster_summary,
        "skipped": skipped,
        "skipped_breakdown": skipped_breakdown,
        "inputs": inputs,
        "rules": {
            "decision_level": "FAMILY_ARTICLE_AND_RECEIVING_ARTICLE",
            "selling_upcs_are_supporting_detail_only": True,
            "last_receipt_quantity_basis": "MOVEMENT_BASE_UOM_ONLY",
            "incoming_field_used": False,
            "write_enabled": False,
            "delivery_date_filter": "CANONICAL_PHYSICAL_101_109_WEEKDAY_EVIDENCE",
            "delivery_day_eligibility": (
                "ANY_OBSERVED_SELECTED_WEEKDAY_WITHIN_180_DAYS"
                if best_available_delivery_evidence
                else "EXPECTED_WEEKDAY_OR_AT_LEAST_2_RECEIPTS_AND_25_PERCENT_SHARE"
            ),
            "delivery_evidence_lookback_days": 180 if best_available_delivery_evidence else 84,
            "best_available_delivery_evidence": bool(best_available_delivery_evidence),
            "delivery_roster_complete": bool(delivery_date),
            "coverage_window_selected_by_user": bool(
                delivery_date is not None and next_delivery_date is not None
            ),
            "observed_family_is_never_hidden_by_order_math": bool(delivery_date),
            "delivery_day_prefilter_before_heavy_math": True,
            "stale_estimate_allowed": True,
            "stale_estimate_basis": "LATEST_AVAILABLE_CANONICAL_POS_AND_MVT_INDEPENDENT",
            "stale_forecast_starts_day_after_latest_mvt": True,
            "delivery_roster_oh_best_available": "IF_ONLY_MOVEMENT_DAILY_COVERAGE_GAP_USE_OH_ANCHOR_PLUS_AVAILABLE_CANONICAL_MVT",
            "uom_and_movement_semantic_errors_still_review":True,
            "regular_forecast_method":"HISTORICAL_WEEKDAY_AVERAGE_WHEN_2PLUS_OBSERVATIONS",
            "pre_delivery_shortage_is_not_added_to_future_order":True,
            "fresh_live_coverage_cap_days":7,
            "cache_schema":"V18_WEEKDAY_USAGE",
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
    next_delivery_date: date | None = None,
    *,
    best_available_delivery_evidence: bool = False,
) -> str:
    mode="YIPMAN180" if best_available_delivery_evidence else "STANDARD84"
    # Cache schema V8: GR semantics changed to validated 5014-only receipt docs.
    # Do not reuse persisted V7 payloads that may contain generic SAP document
    # numbers (for example 4920...) in the GR field.
    next_key=next_delivery_date.isoformat() if next_delivery_date is not None else "AUTO7"
    return f"V19_RECEIVING_PACK|{mode}|{str(category or 'ALL').upper()}|{delivery_date.isoformat()}|{next_key}"


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
    next_delivery_date: date | None,
    cache_key: str,
    best_available_delivery_evidence: bool = True,
) -> None:
    try:
        _ORDERING_REVIEW_LAST_ERROR.pop(cache_key,None)
        value=ordering_review(
            category=category,
            delivery_date=delivery_date,
            next_delivery_date=next_delivery_date,
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
    next_delivery_date: date | None,
    cache_key: str,
    best_available_delivery_evidence: bool = True,
) -> None:
    with _ORDERING_REVIEW_CACHE_LOCK:
        if cache_key in _ORDERING_REVIEW_REFRESHING:
            return
        _ORDERING_REVIEW_REFRESHING.add(cache_key)
    threading.Thread(
        target=_ordering_review_refresh_worker,
        args=(category,delivery_date,next_delivery_date,cache_key,best_available_delivery_evidence),
        name=f"ordering-review-{delivery_date.isoformat()}",
        daemon=True,
    ).start()


def cached_ordering_review(
    category: str = "ALL",
    delivery_date: date | None = None,
    next_delivery_date: date | None = None,
    force: bool = False,
    *,
    best_available_delivery_evidence: bool = True,
) -> dict[str,Any]:
    """Return delivery-date Ordering immediately; heavy analysis refreshes in background."""
    if delivery_date is None:
        return ordering_review(
            category=category,
            delivery_date=None,
            next_delivery_date=None,
            best_available_delivery_evidence=best_available_delivery_evidence,
        )

    cat=str(category or "ALL").strip().upper()
    if cat not in {"ALL","FRESH","FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_FRESH_OR_FROZEN")
    key=_ordering_review_cache_key(
        cat,
        delivery_date,
        next_delivery_date,
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
            "contract_version":"BACKOFFICE_ORDERING_REVIEW_V17_ASYNC_ORDERING_QUALITY",
            "category":cat,
            "selected_delivery_date":delivery_date,
            "selected_next_delivery_date":next_delivery_date,
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
    cached_health=dict((cached or {}).get("data_health") or {})
    cached_expected=str(cached_health.get("expected_through") or "")
    live_health=_pricing_review_data_health(allow_stale_estimate=True)
    source_changed=bool(cached) and (
        str(cached_health.get("pos_data_through") or "")
        != str(live_health.get("pos_data_through") or "")
        or str(cached_health.get("movement_data_through") or "")
        != str(live_health.get("movement_data_through") or "")
    )
    data_current=bool(cached and cached_expected==expected and not source_changed)
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
            next_delivery_date,
            key,
            best_available_delivery_evidence,
        )

    with _ORDERING_REVIEW_CACHE_LOCK:
        refreshing=key in _ORDERING_REVIEW_REFRESHING
    err=_ORDERING_REVIEW_LAST_ERROR.get(key)

    # Ordering is a best-available operating view. When an older cached
    # calculation is still the newest usable evidence, return it immediately
    # as an ESTIMATE while a refresh runs in the background.
    if cached is not None and not data_current and best_available_delivery_evidence:
        stale_health=dict((cached.get("data_health") or {}))
        stale_health.update({
            "status":"STALE_ESTIMATE_AVAILABLE",
            "decision_mode":"STALE_ESTIMATE",
            "expected_through":expected,
            "cache_expected_through":cached_expected or None,
            "warning":(
                "Newer canonical POS/MVT data is published; prior ordering results are shown only while the current analysis rebuilds."
                if source_changed else
                "Best-available cached ordering estimate is shown while current delivery analysis refreshes."
            ),
        })
        has_rows=bool(cached.get("rows"))
        return {
            **cached,
            "contract_version":"BACKOFFICE_ORDERING_REVIEW_V17_ASYNC_ORDERING_QUALITY",
            "analysis_status":(
                "READY_STALE_ESTIMATE_REFRESHING"
                if has_rows else
                "READY_STALE_ESTIMATE_NO_ELIGIBLE_ITEMS_REFRESHING"
            ),
            "cache_status":(
                "SOURCE_CHANGED_REFRESHING"
                if source_changed else "STALE_ESTIMATE_REFRESHING"
            ),
            "refreshing":refreshing,
            "refresh_error":err,
            "data_health":stale_health,
            "current_source_health":live_health,
            "source_changed_since_analysis":source_changed,
        }

    # Never present a prior completed-data-day snapshot as current Ordering
    # in the standard Back Office path.
    if cached is None or not data_current:
        return {
            "contract_version":"BACKOFFICE_ORDERING_REVIEW_V17_ASYNC_ORDERING_QUALITY",
            "category":cat,
            "selected_delivery_date":delivery_date,
            "selected_next_delivery_date":next_delivery_date,
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
            "current_source_health":live_health,
            "source_changed_since_analysis":source_changed,
        }

    return {
        **cached,
        "contract_version":"BACKOFFICE_ORDERING_REVIEW_V18_SOURCE_AWARE_CACHE",
        "cache_status":"STALE_REFRESHING" if stale else "HIT",
        "refreshing":refreshing,
        "refresh_error":err,
        "current_source_health":live_health,
        "source_changed_since_analysis":source_changed,
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

    # Receipt verification applies to the Family/source header and linked Articles.
    # V332 builds the two latest DELIVERY dates from canonical movement snapshots,
    # aggregates all positive receipt events on the same Article/date, and keeps
    # 251/252 selling movement completely separate from receiving quantity.
    receipt_articles = sorted(set(source_articles) | set(article_numbers))
    receipt_by_article: dict[str, dict[str, Any]] = {}
    receipt_history_by_article: dict[str, list[dict[str, Any]]] = {}
    if receipt_articles:
        receipt_days_180 = source_data_days(
            cur,
            "movement",
            limit=180,
            up_to=completed_through_date(),
        )
        canonical_receipt_files = {
            x["date"]: int(x["file_id"])
            for x in receipt_days_180
            if x.get("date") is not None and x.get("file_id") is not None
        }
        aph = ",".join(["%s"] * len(receipt_articles))
        receipt_types = ('101', '102', '109', '110')
        tph = ",".join(["%s"] * len(receipt_types))
        cur.execute(
            f"""SELECT article_number,movement_type,posting_date,
                       base_quantity,base_uom_code,file_id,
                       article_document,purchase_order,raw_id,source_row_number
                FROM movement_history
                WHERE article_number IN ({aph})
                  AND movement_type IN ({tph})
                ORDER BY article_number,posting_date DESC,file_id DESC,
                         raw_id DESC,source_row_number DESC""",
            tuple(receipt_articles) + receipt_types,
        )
        canonical_rows = [
            r for r in cur.fetchall()
            if r.get("posting_date") in canonical_receipt_files
            and canonical_receipt_files[r["posting_date"]] == int(r["file_id"])
        ]

        # Physical delivery quantity comes only from 101 or 109 (plus reversals).
        # 107 is the cost stage of a 107+109 flow and is never counted here,
        # including when its posting date differs from the 109 GR date.
        event_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for r in canonical_rows:
            art = str(r.get("article_number") or "").strip()
            posting_date = r.get("posting_date")
            if not art or posting_date is None:
                continue
            key = (
                art,
                posting_date,
                str(r.get("purchase_order") or ""),
                str(r.get("article_document") or ""),
            )
            event_groups.setdefault(key, []).append(r)

        daily_events: dict[tuple[str, Any], list[dict[str, Any]]] = {}
        for key, group in event_groups.items():
            chosen, stage = _receipt_stage_rows(group)
            if not chosen:
                continue
            uoms = {
                str(x.get("base_uom_code") or "").strip().upper()
                for x in chosen
                if str(x.get("base_uom_code") or "").strip()
            }
            if len(uoms) != 1:
                continue
            if not any(x.get("base_quantity") is not None for x in chosen):
                continue
            qty = sum((_d(x.get("base_quantity")) for x in chosen), Decimal("0"))
            if qty <= 0:
                continue
            daily_events.setdefault((key[0], key[1]), []).append(
                {
                    "quantity": qty,
                    "uom": next(iter(uoms)),
                    "stage_basis": stage,
                }
            )

        per_article: dict[str, list[dict[str, Any]]] = {}
        for (art, posting_date), events in daily_events.items():
            uoms = {str(x.get("uom") or "").upper() for x in events if x.get("uom")}
            quantity = None
            uom = None
            if len(uoms) == 1:
                uom = next(iter(uoms))
                quantity = sum((_d(x.get("quantity")) for x in events), Decimal("0"))
            entry = {
                "verified": True,
                "movement_type": "101/109",
                "date": posting_date,
                "weekday": (
                    posting_date.strftime("%A")
                    if hasattr(posting_date, "strftime")
                    else None
                ),
                "quantity": quantity,
                "uom": uom,
                "receipt_event_count": len(events),
                "source": "MVT_PHYSICAL_101_109_CANONICAL_DAILY_AGGREGATE",
            }
            per_article.setdefault(art, []).append(entry)

        for art, entries in per_article.items():
            entries.sort(key=lambda x: str(x.get("date") or ""), reverse=True)
            history = entries[:2]
            if history:
                receipt_history_by_article[art] = history
                receipt_by_article[art] = history[0]

    # Family 7D Receipt is a separate receiving metric from Family Selling MVT.
    # It sums only canonical physical 101/109 receipt events across the latest
    # seven completed movement-data days. 107 is cost evidence only and is
    # already excluded by the physical receipt stage selection above.
    receipt_dates_7 = {
        x["date"]
        for x in movement_days_7
        if x.get("date") is not None
    }

    # Keep a per-Article 7D receipt subtotal from the exact same canonical
    # physical 101/109 event pool used by the Family total. This makes every
    # Receiving Article row auditable against Family 7D Receipt even when an
    # Article has more than two receipt events inside the seven completed days.
    receipt_7d_by_article: dict[str, dict[str, Any]] = {}
    for art, entries in per_article.items():
        entries_7 = [
            e for e in entries
            if e.get("date") in receipt_dates_7
        ]
        uoms_7 = {
            str(e.get("uom") or "").strip().upper()
            for e in entries_7
            if str(e.get("uom") or "").strip()
        }
        if entries_7 and len(uoms_7) == 1 and all(
            e.get("quantity") is not None for e in entries_7
        ):
            receipt_7d_by_article[art] = {
                "quantity": sum(
                    (_d(e.get("quantity")) for e in entries_7),
                    Decimal("0"),
                ),
                "uom": next(iter(uoms_7)),
                "status": "READY",
                "receipt_day_count": len({
                    e.get("date") for e in entries_7 if e.get("date") is not None
                }),
            }
        elif entries_7:
            receipt_7d_by_article[art] = {
                "quantity": None,
                "uom": None,
                "status": "HOLD_MIXED_OR_MISSING_RECEIPT_UOM",
                "receipt_day_count": len({
                    e.get("date") for e in entries_7 if e.get("date") is not None
                }),
            }
        else:
            receipt_7d_by_article[art] = {
                "quantity": Decimal("0"),
                "uom": None,
                "status": "READY_ZERO_RECEIPTS",
                "receipt_day_count": 0,
            }

    receipt_7d_by_family: dict[int, dict[str, Any]] = {}
    family_receipt_history_by_family: dict[int, list[dict[str, Any]]] = {}
    for fid in fids:
        family_receipt_articles = {
            str(source_by_family.get(fid) or "").strip(),
            *{
                str(a or "").strip()
                for a in candidates.get(fid, {})
            },
        }
        family_receipt_articles.discard("")
        all_known_entries = [
            e
            for art in family_receipt_articles
            for e in per_article.get(art, [])
        ]

        # RECENT RECEIPTS must use the same Family-wide physical receipt pool as
        # the 7D Receipt total. Previously it looked only at the Family/source
        # Article, so a Family could correctly show positive 7D Receipt while
        # incorrectly displaying "No recent receipt" when the GR posted to a
        # linked Receiving Article.
        family_entries_by_date: dict[Any, list[dict[str, Any]]] = {}
        for entry in all_known_entries:
            if entry.get("date") is not None:
                family_entries_by_date.setdefault(entry.get("date"), []).append(entry)
        family_history: list[dict[str, Any]] = []
        for receipt_date, date_entries in family_entries_by_date.items():
            date_uoms = {
                str(x.get("uom") or "").strip().upper()
                for x in date_entries
                if str(x.get("uom") or "").strip()
            }
            date_qty = None
            date_uom = None
            if (
                len(date_uoms) == 1
                and all(x.get("quantity") is not None for x in date_entries)
            ):
                date_uom = next(iter(date_uoms))
                date_qty = sum(
                    (_d(x.get("quantity")) for x in date_entries),
                    Decimal("0"),
                )
            family_history.append({
                "verified": True,
                "movement_type": "101/109",
                "date": receipt_date,
                "weekday": (
                    receipt_date.strftime("%A")
                    if hasattr(receipt_date, "strftime")
                    else None
                ),
                "quantity": date_qty,
                "uom": date_uom,
                "receipt_event_count": sum(
                    int(x.get("receipt_event_count") or 0)
                    for x in date_entries
                ),
                "receiving_article_count": len(date_entries),
                "source": "MVT_PHYSICAL_101_109_FAMILY_DAILY_AGGREGATE",
            })
        family_history.sort(
            key=lambda x: str(x.get("date") or ""),
            reverse=True,
        )
        family_receipt_history_by_family[fid] = family_history[:2]

        entries_7 = [
            e for e in all_known_entries
            if e.get("date") in receipt_dates_7
        ]
        uoms_7 = {
            str(e.get("uom") or "").strip().upper()
            for e in entries_7
            if str(e.get("uom") or "").strip()
        }
        known_uoms = {
            str(e.get("uom") or "").strip().upper()
            for e in all_known_entries
            if str(e.get("uom") or "").strip()
        }
        if entries_7 and len(uoms_7) == 1 and all(
            e.get("quantity") is not None for e in entries_7
        ):
            receipt_7d_by_family[fid] = {
                "quantity": sum(
                    (_d(e.get("quantity")) for e in entries_7),
                    Decimal("0"),
                ),
                "uom": next(iter(uoms_7)),
                "status": "READY",
                "receipt_day_count": len({
                    e.get("date") for e in entries_7 if e.get("date") is not None
                }),
                "basis": "CANONICAL_PHYSICAL_101_109_LATEST_7_COMPLETED_MVT_DAYS",
            }
        elif entries_7:
            receipt_7d_by_family[fid] = {
                "quantity": None,
                "uom": None,
                "status": "HOLD_MIXED_OR_MISSING_RECEIPT_UOM",
                "receipt_day_count": len({
                    e.get("date") for e in entries_7 if e.get("date") is not None
                }),
                "basis": "CANONICAL_PHYSICAL_101_109_LATEST_7_COMPLETED_MVT_DAYS",
            }
        else:
            fallback_uom = (
                next(iter(known_uoms))
                if len(known_uoms) == 1
                else str((canonical_family_metric.get(fid) or {}).get("uom") or "").strip().upper() or None
            )
            receipt_7d_by_family[fid] = {
                "quantity": Decimal("0"),
                "uom": fallback_uom,
                "status": "READY_ZERO_RECEIPTS",
                "receipt_day_count": 0,
                "basis": "CANONICAL_PHYSICAL_101_109_LATEST_7_COMPLETED_MVT_DAYS",
            }

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
        source_article_key = str(source_article or "").strip()
        source_receipt_history = receipt_history_by_article.get(source_article_key, [])
        source_receipt_7d = receipt_7d_by_article.get(source_article_key, {})
        family_receipt_history = family_receipt_history_by_family.get(fid, [])
        family_receipt = (
            family_receipt_history[0]
            if family_receipt_history
            else receipt_by_article.get(source_article_key, {})
        )

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
                    "receipt_7d_qty": (receipt_7d_by_article.get(art) or {}).get("quantity"),
                    "receipt_7d_uom": (receipt_7d_by_article.get(art) or {}).get("uom"),
                    "receipt_7d_status": (receipt_7d_by_article.get(art) or {}).get("status"),
                    "receipt_7d_day_count": (receipt_7d_by_article.get(art) or {}).get("receipt_day_count"),
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
            "family_receipt_history": family_receipt_history,
            # Source/Main Article can itself be a real Receiving Article. Keep
            # its actual Article-level history separate from the Family daily
            # aggregate so the UI never has to hide or duplicate that receipt.
            "family_source_receipt_verified": bool(source_receipt_history),
            "family_source_receipt_history": source_receipt_history,
            "family_source_receipt_7d_qty": source_receipt_7d.get("quantity"),
            "family_source_receipt_7d_uom": source_receipt_7d.get("uom"),
            "family_source_receipt_7d_status": source_receipt_7d.get("status"),
            "family_source_receipt_7d_day_count": source_receipt_7d.get("receipt_day_count"),
            "family_receipt_7d_qty": (receipt_7d_by_family.get(fid) or {}).get("quantity"),
            "family_receipt_7d_uom": (receipt_7d_by_family.get(fid) or {}).get("uom"),
            "family_receipt_7d_status": (receipt_7d_by_family.get(fid) or {}).get("status"),
            "family_receipt_7d_day_count": (receipt_7d_by_family.get(fid) or {}).get("receipt_day_count"),
            "family_receipt_7d_basis": (receipt_7d_by_family.get(fid) or {}).get("basis"),
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


def _positive_price(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        price = _d(value)
    except Exception:
        return None
    return price if price > 0 else None


def _gp_pct_for_price(price: Any, cost: Any) -> Decimal | None:
    p = _positive_price(price)
    c = _positive_price(cost)
    if p is None or c is None:
        return None
    return (p - c) / p


MIN_TEST_PRICE_STEP = Decimal("0.45")


def _next_testing_price(
    anchor: Decimal | None,
    target: Decimal | None,
    observed_candidates: list[dict[str, Any]] | None = None,
    *,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
) -> Decimal | None:
    """Move one meaningful controlled test to a normal store price point.

    Testing is always >= $0.45 away from Current and always ends in one of the
    standard merchandising endings: .29/.49/.59/.69/.79/.99. The raw supported
    target is first snapped to the nearest allowed store price point. A ~5%
    step remains the gradual preference; when no valid store ending exists
    inside that exact cap, the nearest valid price point toward target is used.
    """
    anchor = _positive_price(anchor)
    target = _positive_price(target)
    low = _positive_price(min_price)
    high = _positive_price(max_price)
    if anchor is None or target is None:
        return None

    target_point = _retail_price_point(
        target,
        min_price=low,
        max_price=high,
    )
    if target_point is None:
        return None
    target = target_point
    delta = target - anchor
    if abs(delta) < MIN_TEST_PRICE_STEP:
        return None

    percent_step = (anchor * Decimal("0.05")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    cap = max(MIN_TEST_PRICE_STEP, percent_step)

    if delta > 0:
        floor=max(anchor + MIN_TEST_PRICE_STEP, low or Decimal("0.01"))
        ceiling=min(target, high) if high is not None else target
        strict_ceiling=min(ceiling, anchor + cap)
        raw_step=min(target, anchor + cap)
    else:
        floor=max(target, low) if low is not None else target
        ceiling=min(anchor - MIN_TEST_PRICE_STEP, high) if high is not None else anchor - MIN_TEST_PRICE_STEP
        strict_floor=max(floor, anchor - cap)
        raw_step=max(target, anchor - cap)

    if floor > ceiling:
        return None

    # Preserve nearby observed evidence when it is already a meaningful move.
    observed_points: list[Decimal] = []
    for item in observed_candidates or []:
        raw = _positive_price((item or {}).get("price"))
        if raw is None:
            continue
        raw_delta=raw-anchor
        if delta > 0 and not (MIN_TEST_PRICE_STEP <= raw_delta <= cap):
            continue
        if delta < 0 and not (-cap <= raw_delta <= -MIN_TEST_PRICE_STEP):
            continue
        snapped=_retail_price_point(
            raw,
            min_price=floor,
            max_price=ceiling,
        )
        if snapped is not None:
            observed_points.append(snapped)
    if observed_points:
        return min(
            set(observed_points),
            key=lambda p: (abs(p-anchor), abs(p-raw_step), p),
        )

    # Prefer a standard price point inside the gradual cap.
    if delta > 0:
        strict=_retail_price_point(
            raw_step,
            min_price=floor,
            max_price=strict_ceiling,
        ) if floor <= strict_ceiling else None
    else:
        strict=_retail_price_point(
            raw_step,
            min_price=strict_floor,
            max_price=ceiling,
        ) if strict_floor <= ceiling else None
    if strict is not None:
        return strict

    # If the exact cap lands between normal store endings, use the nearest
    # standard point in the correct direction rather than emitting e.g. $9.44.
    return _retail_price_point(
        raw_step,
        min_price=floor,
        max_price=ceiling,
    )


def _tested_testing_prices(
    *,
    current: Any,
    tested: Any,
    target: Any,
    observed_candidates: list[dict[str, Any]] | None = None,
    company_low: Any = None,
    company_high: Any = None,
) -> dict[str, Any]:
    current_price = _positive_price(current)
    tested_evidence_price = _positive_price(tested)
    low = _positive_price(company_low)
    high = _positive_price(company_high)
    tested_price = (
        _retail_price_point(
            tested_evidence_price,
            min_price=low,
            max_price=high,
        )
        if tested_evidence_price is not None
        else None
    )
    if tested_price is None:
        tested_price = tested_evidence_price
    raw_target_price = _positive_price(target)
    target_price = _retail_price_point(
        raw_target_price,
        min_price=low,
        max_price=high,
    ) if raw_target_price is not None else None
    # Testing always starts from the live CURRENT price. Tested is the
    # strongest proved reference, never the starting point for a new action.
    anchor = current_price
    testing_price = _next_testing_price(
        anchor,
        target_price,
        observed_candidates=observed_candidates,
        min_price=low,
        max_price=high,
    )
    return {
        "tested_price": tested_price,
        "tested_evidence_price": tested_evidence_price,
        "testing_price": testing_price,
        "target_sweet_spot_price": target_price,
        "raw_target_sweet_spot_price": raw_target_price,
        "price_point_rounding": "NEAREST_OF_29_49_59_69_79_99",
        "testing_anchor_price": anchor,
        "testing_step_rule": "CURRENT_TO_TARGET_MIN_0_45_STEP_NEAREST_OBSERVED_WITHIN_GRADUAL_CAP",
    }


def _freshness_velocity_target(
    *,
    current: Any,
    current_cost: Any,
    current_velocity: Any,
    observed_candidates: list[dict[str, Any]] | None = None,
    company_low: Any = None,
    company_high: Any = None,
) -> Decimal | None:
    """Choose a conservative lower target for a freshness/velocity test.

    Prefer a historically observed lower price that produced better velocity,
    while staying above current cost and inside the applicable Company range.
    If history has no qualifying lower point, use one exploratory markdown
    step of at least $0.45 (or about 5% for higher-priced items), subject to
    those same floors.
    """
    current_price = _positive_price(current)
    cost = _positive_price(current_cost)
    if current_price is None or cost is None:
        return None

    low = _positive_price(company_low)
    high = _positive_price(company_high)
    floor = cost + Decimal("0.01")
    if low is not None:
        floor = max(floor, low)
    if floor >= current_price:
        return None

    velocity = _d(current_velocity) if current_velocity is not None else Decimal("0")
    eligible: list[dict[str, Any]] = []
    for item in observed_candidates or []:
        price = _positive_price((item or {}).get("price"))
        if price is None or not (floor <= price < current_price):
            continue
        if high is not None and price > high:
            continue
        observed_velocity = (
            _d((item or {}).get("observed_velocity_per_day"))
            if (item or {}).get("observed_velocity_per_day") is not None
            else Decimal("0")
        )
        if observed_velocity <= velocity:
            continue
        eligible.append(item)

    if eligible:
        eligible.sort(
            key=lambda x: (
                float(x.get("gp_per_observed_day_at_current_cost") or Decimal("-999999")),
                float(x.get("observed_velocity_per_day") or Decimal("0")),
                float(x.get("price") or Decimal("0")),
            ),
            reverse=True,
        )
        return _positive_price(eligible[0].get("price"))

    exploratory_step = max(
        MIN_TEST_PRICE_STEP,
        (current_price * Decimal("0.05")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
    )
    exploratory = (current_price - exploratory_step).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    exploratory = max(exploratory, floor)
    if high is not None:
        exploratory = min(exploratory, high)
    return exploratory if exploratory < current_price - Decimal("0.01") else None


def _quick_price_preview_by_upc(
    cur,
    rows: list[dict[str, Any]],
    live_prices: dict[int, dict[str, Any] | None],
) -> dict[int, dict[str, Any]]:
    """Compact Quick Check pricing preview for the already-selected UPC rows.

    CURRENT price uses the same live resolver as Price Review. SUGGEST uses the
    same 14-completed-sales-day GP$/day candidate engine and qualification
    gates as the main Price Review, plus mandatory 240=249 price equality.
    """
    prepared: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        uid = int(row["upc_id"]) if row.get("upc_id") is not None else None
        live = live_prices.get(uid) if uid is not None else None
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
        prepared.append(row)

    days = source_data_days(
        cur,
        "sales_by_price_type",
        limit=14,
        up_to=completed_through_date(),
    )
    daily = _batch_daily_sales_by_price_type(cur, prepared, days)
    anchor = max((x["date"] for x in days), default=None)
    previews: dict[int, dict[str, Any]] = {}

    for row in prepared:
        if row.get("upc_id") is None:
            continue
        uid = int(row["upc_id"])
        current = row.get("current_price")
        tested = _positive_price(row.get("sweet_spot_price"))
        preview = {
            "suggested_price": None,
            "suggestion_status": "UNAVAILABLE",
            "suggestion_basis": None,
            "suggestion_reason": None,
            "tested_price": tested,
            "testing_price": None,
            "target_sweet_spot_price": None,
            "testing_step_rule": "MIN_0_45_FROM_CURRENT_NEAREST_OBSERVED_WITHIN_GRADUAL_CAP",
        }
        m14 = _batch_sales_metric(daily, days, uid, 14)
        q14 = _d(m14.get("sold_quantity"))
        current_oh = (
            _d(row.get("current_oh"))
            if row.get("current_oh") is not None else None
        )
        day_obs = (
            (daily.get(uid) or {}).get(anchor, {})
            if anchor is not None else {}
        )
        report_day_types = {
            str(k).upper()
            for k in (day_obs.get("price_types") or {}).keys()
        }
        base_qualified = bool(
            current_oh is not None
            and current_oh > 0
            and q14 > 0
            and str(row.get("quick_check_status") or "").upper() == "READY"
            and "SALE" not in report_day_types
        )
        if base_qualified:
            opt = _gp_day_price_suggestion_from_batch(
                row, uid, daily, days
            )
            target = (
                opt.get("suggested_price")
                if opt.get("status") == "READY"
                else None
            )
            path = _tested_testing_prices(
                current=current,
                tested=tested,
                target=target,
                observed_candidates=opt.get("top_observed_candidates"),
                company_low=opt.get("company_range_low"),
                company_high=opt.get("company_range_high"),
            )
            preview.update(path)
            cost = _positive_price(row.get("current_cost_per_selling_unit"))
            tested_retail = _positive_price(path.get("tested_price"))
            tested_actionable = bool(
                tested_retail is not None
                and current is not None
                and abs(tested_retail - _d(current)) > Decimal("0.01")
                and cost is not None
                and tested_retail > cost
            )
            if tested_actionable:
                preview.update({
                    "suggested_price": tested_retail,
                    "suggestion_status": "TESTED_PRICE_READY",
                    "suggestion_basis": "HISTORICAL_TESTED_SWEET_SPOT",
                    "suggestion_reason": "TESTED SWEET SPOT",
                })
            elif path.get("testing_price") is not None:
                preview.update({
                    "suggested_price": path.get("testing_price"),
                    "suggestion_status": "TESTING_PRICE_READY",
                    "suggestion_basis": opt.get("basis"),
                    "suggestion_reason": "SWEET SPOT TEST",
                })
            else:
                preview.update({
                    "suggestion_status": str(
                        opt.get("reason") or opt.get("status") or "NO_NEW_TEST"
                    ),
                    "suggestion_basis": opt.get("basis"),
                    "suggestion_reason": "NO NEW TEST",
                })
        elif "SALE" in report_day_types:
            preview["suggestion_status"] = "ACTIVE_SALE_EXCLUDED"
            preview["suggestion_reason"] = "ACTIVE SALE"
        elif str(row.get("quick_check_status") or "").upper() != "READY":
            preview["suggestion_status"] = "QA_NOT_READY"
            preview["suggestion_reason"] = "QA HOLD"
        elif current_oh is None or current_oh <= 0:
            preview["suggestion_status"] = "NO_POSITIVE_OH"
            preview["suggestion_reason"] = "NO STOCK"
        elif q14 <= 0:
            preview["suggestion_status"] = "NO_14D_SALES"
            preview["suggestion_reason"] = "NO 14D SALES"
        previews[uid] = preview

    # Canonical 240 is the price authority for its confirmed 249 service form.
    # A 249 form must not surface an independent candidate that breaks equality.
    pairs: dict[tuple[int, str], dict[str, dict[str, Any]]] = {}
    for row in prepared:
        sig = _seafood_upc_group_signature(
            row.get("family_id"), row.get("ean_upc")
        )
        prefix = _numeric_key(row.get("ean_upc"))[:3]
        if sig is not None and prefix in {"240", "249"}:
            pairs.setdefault(sig, {})[prefix] = row

    for members in pairs.values():
        main = members.get("240")
        service = members.get("249")
        if not main or not service:
            continue
        main_uid = int(main["upc_id"]) if main.get("upc_id") is not None else None
        service_uid = int(service["upc_id"]) if service.get("upc_id") is not None else None
        if main_uid is None or service_uid is None:
            continue
        main_preview = previews.setdefault(main_uid, {
            "suggested_price": None,
            "suggestion_status": "UNAVAILABLE",
            "suggestion_basis": None,
        })
        service_preview = previews.setdefault(service_uid, {
            "suggested_price": None,
            "suggestion_status": "UNAVAILABLE",
            "suggestion_basis": None,
        })
        main_current = main.get("current_price")
        service_current = service.get("current_price")
        main_candidate = main_preview.get("suggested_price")

        service_preview["tested_price"] = main_preview.get("tested_price")
        service_preview["testing_price"] = main_preview.get("testing_price")
        service_preview["target_sweet_spot_price"] = main_preview.get("target_sweet_spot_price")
        service_preview["testing_step_rule"] = main_preview.get("testing_step_rule")

        if main_candidate is not None:
            service_preview.update({
                "suggested_price": main_candidate,
                "suggestion_status": main_preview.get("suggestion_status") or "TESTING_PRICE_READY",
                "suggestion_basis": "MANDATORY_240_249_EQUALITY_TO_240_PRICE_PATH",
                "suggestion_reason": main_preview.get("suggestion_reason") or "240=249",
            })
        elif (
            main_current is not None
            and service_current is not None
            and _d(main_current) > 0
            and _d(service_current) > 0
            and _d(main_current) != _d(service_current)
        ):
            service_preview.update({
                "suggested_price": main_current,
                "suggestion_status": "READY_URGENT_240_249_MISMATCH",
                "suggestion_basis": "MANDATORY_240_249_EQUALITY_TO_240_CURRENT_PRICE",
                "suggestion_reason": "240=249 PRICE ALIGNMENT",
            })
        else:
            service_preview.update({
                "suggested_price": None,
                "suggestion_status": "NO_INDEPENDENT_249_CHANGE",
                "suggestion_basis": "MANDATORY_240_249_EQUALITY",
                "suggestion_reason": "240=249",
            })

    return previews


def quick_price_preview(upcs: list[str] | tuple[str, ...] | set[str]) -> dict[str, Any]:
    """Return Quick Check prices from the same canonical Price Review snapshot.

    Tested Price is the live established sweet spot from quick_check_current.
    Testing Price and any active price action come only from cached_pricing_review(),
    which is the same snapshot consumed by the Price Suggestions page. Quick
    Check never independently invents a second Testing Price.
    """
    requested=[]
    seen=set()
    for raw in upcs or []:
        value=str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        requested.append(value)
        if len(requested)>=60:
            break
    if not requested:
        return {
            "contract_version":"YIPMAN_QUICK_PRICE_PREVIEW_V2_CANONICAL_PRICE_REVIEW",
            "count":0,
            "rows":[],
            "price_review_analysis_status":"READY",
        }

    # Read exactly the same pricing snapshot used by Yipman's Price Suggestions
    # page. This may be a stale-while-refresh snapshot; that is intentional:
    # both screens must show the same Tested / Testing path at the same moment.
    pricing_snapshot=cached_pricing_review(
        category="ALL",
        limit=1000,
        force=False,
    )
    pricing_status=str(pricing_snapshot.get("analysis_status") or "").upper()
    pricing_cache_status=str(pricing_snapshot.get("cache_status") or "").upper()
    canonical_rows={
        str(x.get("upc") or ""):dict(x)
        for x in (pricing_snapshot.get("rows") or [])
        if str(x.get("upc") or "").strip()
    }
    canonical_ready=bool(
        canonical_rows
        or pricing_status.startswith("READY")
        or pricing_cache_status in {"HIT","STALE_REFRESHING"}
    )

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        ph=",".join(["%s"]*len(requested))
        cur.execute(
            f"""SELECT *
                FROM quick_check_current
                WHERE ean_upc IN ({ph})
                ORDER BY ean_upc""",
            tuple(requested),
        )
        rows=cur.fetchall()

        # Include confirmed 240/249 companions so the canonical 240 Tested /
        # Testing path can be mirrored to its service 249 form when appropriate.
        pair_signatures=set()
        for row in rows:
            sig=_seafood_upc_group_signature(row.get("family_id"),row.get("ean_upc"))
            prefix=_numeric_key(row.get("ean_upc"))[:3]
            if sig is not None and prefix in {"240","249"}:
                pair_signatures.add(sig)
        if pair_signatures:
            family_ids=sorted({x[0] for x in pair_signatures})
            fph=",".join(["%s"]*len(family_ids))
            cur.execute(
                f"""SELECT *
                    FROM quick_check_current
                    WHERE family_id IN ({fph})
                    ORDER BY family_id,ean_upc""",
                tuple(family_ids),
            )
            existing={str(x.get("ean_upc") or "") for x in rows}
            for extra in cur.fetchall():
                sig=_seafood_upc_group_signature(extra.get("family_id"),extra.get("ean_upc"))
                prefix=_numeric_key(extra.get("ean_upc"))[:3]
                ean=str(extra.get("ean_upc") or "")
                if sig in pair_signatures and prefix in {"240","249"} and ean not in existing:
                    rows.append(extra)
                    existing.add(ean)

        live_prices=_bulk_live_current_prices(cur,rows)

        # Build confirmed 240 -> 249 price-path inheritance only when the
        # canonical Price Review has a 240 row. This enforces 240=249 without
        # generating an independent Testing Price for 249.
        pair_path_by_sig={}
        for row in rows:
            sig=_seafood_upc_group_signature(row.get("family_id"),row.get("ean_upc"))
            prefix=_numeric_key(row.get("ean_upc"))[:3]
            upc=str(row.get("ean_upc") or "")
            canonical=canonical_rows.get(upc)
            if sig is not None and prefix=="240" and canonical is not None:
                pair_path_by_sig[sig]=canonical

        requested_set=set(requested)
        out=[]
        for row in rows:
            upc=str(row.get("ean_upc") or "")
            if upc not in requested_set or row.get("upc_id") is None:
                continue
            uid=int(row["upc_id"])
            live=live_prices.get(uid) or {}
            canonical=canonical_rows.get(upc)
            sig=_seafood_upc_group_signature(row.get("family_id"),upc)
            prefix=_numeric_key(upc)[:3]
            inherited_240=False
            if canonical is None and sig is not None and prefix=="249":
                canonical=pair_path_by_sig.get(sig)
                inherited_240=canonical is not None

            tested_evidence=_positive_price(row.get("sweet_spot_price"))
            fallback_low=_positive_price(row.get("current_cost_per_selling_unit"))
            if fallback_low is not None:
                fallback_low += Decimal("0.01")
            fallback_company_prices=[
                x for x in (
                    _positive_price(row.get("company_price_a")),
                    _positive_price(row.get("company_price_b")),
                    _positive_price(row.get("company_price_c")),
                ) if x is not None
            ]
            fallback_company_low=min(fallback_company_prices) if fallback_company_prices else None
            fallback_company_high=max(fallback_company_prices) if fallback_company_prices else None
            if fallback_company_low is not None:
                fallback_low=max(fallback_low or fallback_company_low,fallback_company_low)
            tested=(
                _retail_price_point(
                    tested_evidence,
                    min_price=fallback_low,
                    max_price=fallback_company_high,
                )
                if tested_evidence is not None else None
            ) or tested_evidence
            testing=(
                _positive_price(canonical.get("testing_price"))
                if canonical is not None else None
            )
            # Price Review is the retail-facing Tested authority. Preserve raw
            # proved historical evidence separately when the display is rounded.
            if canonical is not None and canonical.get("tested_price") is not None:
                tested=_positive_price(canonical.get("tested_price"))
                tested_evidence=_positive_price(
                    canonical.get("tested_evidence_price")
                ) or tested_evidence

            reason_code=(
                str(canonical.get("suggestion_reason_code") or "")
                if canonical is not None else ""
            )
            candidate=(
                canonical.get("candidate_price")
                if canonical is not None and not inherited_240
                else None
            )
            if inherited_240:
                suggestion_status="PAIR_240_PRICE_PATH"
                suggestion_reason="240=249 PRICE PATH"
            elif canonical is not None and reason_code:
                suggestion_status=reason_code
                suggestion_reason=(
                    canonical.get("suggestion_reason")
                    or canonical.get("primary_reason_text")
                    or reason_code
                )
            elif not canonical_ready:
                suggestion_status="PRICING_REVIEW_WARMING"
                suggestion_reason="PRICE REVIEW WARMING"
            else:
                suggestion_status="NO_ACTIVE_PRICE_SUGGESTION"
                suggestion_reason="NO ACTIVE PRICE TEST"

            out.append({
                "upc":upc,
                "current_price":live.get("price"),
                "current_price_type":live.get("type"),
                "current_price_source":live.get("source"),
                "current_price_asof_date":live.get("date"),
                "suggested_price":candidate,
                "suggestion_status":suggestion_status,
                "suggestion_basis":(
                    canonical.get("suggestion_basis")
                    if canonical is not None else None
                ),
                "suggestion_reason":suggestion_reason,
                "tested_price":tested,
                "tested_evidence_price":tested_evidence,
                "testing_price":testing,
                "tpr_suggestion_price":testing,
                "target_sweet_spot_price":(
                    canonical.get("target_sweet_spot_price")
                    if canonical is not None else None
                ),
                "testing_step_rule":(
                    canonical.get("testing_step_rule")
                    if canonical is not None else
                    "CANONICAL_PRICE_REVIEW_ONLY"
                ),
                "price_path_source":"BACKOFFICE_PRICING_REVIEW_CANONICAL_SNAPSHOT",
                "price_path_inherited_from_240":inherited_240,
                "company_price_a":row.get("company_price_a"),
                "company_price_b":row.get("company_price_b"),
                "company_price_c":row.get("company_price_c"),
            })
        cur.close()

    return {
        "contract_version":"YIPMAN_QUICK_PRICE_PREVIEW_V2_CANONICAL_PRICE_REVIEW",
        "count":len(out),
        "rows":out,
        "price_review_analysis_status":pricing_status or None,
        "price_review_cache_status":pricing_cache_status or None,
        "price_review_refreshing":bool(pricing_snapshot.get("refreshing")),
        "rules":{
            "current_price":"LIVE_CANONICAL_PRICE_AUTHORITY",
            "tested_price":"SAME_CANONICAL_TESTED_PRICE_AS_PRICE_SUGGESTIONS",
            "testing_price":"BACKWARD_COMPATIBILITY_ALIAS_FOR_TPR_SUGGESTION_PRICE",
            "tpr_suggestion_price":"SAME_CANONICAL_CONTROLLED_PRICE_OR_FRESHNESS_TEST_STEP_AS_PRICE_SUGGESTIONS;NO_INDEPENDENT_QUICK_CHECK_RECALCULATION",
            "price_path_source":"BACKOFFICE_PRICING_REVIEW_CANONICAL_SNAPSHOT",
            "pair_rule":"CONFIRMED_240_249_TESTED_TESTING_PATH_INHERITS_FROM_240",
        },
    }



def _recent_family_sale_event_from_batch(
    family_rows: list[dict[str, Any]],
    daily_by_upc: dict[int, dict[date, dict[str, Any]]],
    sales_days: list[dict[str, Any]],
    target_uom: str,
) -> dict[str, Any] | None:
    """Return the newest SALE event plus its full-week incremental sales lift.

    Promotion week = the latest 7 completed canonical POS sales days ending on
    the SALE event end date. Actual week quantity includes every price type for
    the Family. The normal-week baseline is the average Family quantity on
    non-SALE completed days outside that promotion week, multiplied by the
    promotion-week supported-day count. Missing dates are ignored, never zero.
    TPR is never promotion.
    """
    uom=str(target_uom or "").strip().upper()
    ordered_days=sorted(
        [x.get("date") for x in sales_days if x.get("date") is not None]
    )
    if not ordered_days or not family_rows:
        return None

    def convert_row_qty(row: dict[str,Any], qty: Decimal) -> Decimal | None:
        selling_uom=str(row.get("selling_uom") or "").strip().upper()
        base_uom=str(row.get("base_uom") or "").strip().upper()
        factor=row.get("base_qty_per_selling_unit")
        if not uom:
            return None
        if selling_uom and selling_uom==uom:
            return qty
        if base_uom and base_uom==uom and factor is not None:
            factor_d=_d(factor)
            if factor_d>0:
                return qty*factor_d
        return None

    family_day: dict[date,dict[str,Any]]={}
    for day in ordered_days:
        total=Decimal("0")
        total_ready=bool(uom)
        sale_total=Decimal("0")
        sale_sales_amount=Decimal("0")
        sale_ready=bool(uom)
        has_sale=False
        upcs:set[str]=set()
        for row in family_rows:
            if row.get("upc_id") is None:
                continue
            obs=(daily_by_upc.get(int(row["upc_id"])) or {}).get(day) or {}
            all_qty=_d(obs.get("sold_quantity"))
            if all_qty!=0:
                converted=convert_row_qty(row,all_qty)
                if converted is None:
                    total_ready=False
                else:
                    total+=converted

            sale=(obs.get("price_types") or {}).get("SALE")
            if sale:
                sale_qty=_d(sale.get("sold_quantity"))
                if sale_qty>0:
                    has_sale=True
                    upcs.add(str(row.get("ean_upc") or row.get("upc_id") or ""))
                    sale_sales_amount+=_d(sale.get("sales_amount"))
                    converted_sale=convert_row_qty(row,sale_qty)
                    if converted_sale is None:
                        sale_ready=False
                    else:
                        sale_total+=converted_sale

        family_day[day]={
            "total_quantity":total if total_ready else None,
            "total_quantity_ready":total_ready,
            "has_sale":has_sale,
            "sale_quantity":sale_total if sale_ready and has_sale else None,
            "sale_quantity_ready":sale_ready and has_sale,
            "sale_sales_amount":sale_sales_amount if has_sale else None,
            "related_upcs":sorted(x for x in upcs if x),
        }

    sale_days={
        day:info
        for day,info in family_day.items()
        if info.get("has_sale")
    }
    if not sale_days:
        return None

    events:list[dict[str,Any]]=[]
    start:date|None=None
    end:date|None=None
    event_qty=Decimal("0")
    event_sales_amount=Decimal("0")
    event_qty_ready=True
    event_sale_days=0
    event_upcs:set[str]=set()

    def close_event() -> None:
        nonlocal start,end,event_qty,event_sales_amount,event_qty_ready,event_sale_days,event_upcs
        if start is None or end is None:
            return
        events.append({
            "promotion_type":"SALE",
            "start_date":start,
            "end_date":end,
            "sale_quantity":event_qty if event_qty_ready else None,
            "sale_quantity_uom":uom if event_qty_ready and uom else None,
            "sale_quantity_status":"READY" if event_qty_ready and uom else "UNRESOLVED_MIXED_UOM",
            "sale_sales_amount":event_sales_amount,
            "avg_promotion_selling_price":(
                event_sales_amount/event_qty
                if event_qty_ready and event_qty>0 else None
            ),
            "avg_promotion_selling_price_uom":uom if event_qty_ready and event_qty>0 and uom else None,
            "avg_promotion_selling_price_status":(
                "READY"
                if event_qty_ready and event_qty>0 and uom
                else "UNRESOLVED_MIXED_UOM"
            ),
            "sale_observed_day_count":event_sale_days,
            "related_upcs":sorted(event_upcs),
            "window_supported_day_count":len(ordered_days),
            "is_active_on_latest_supported_day":end==ordered_days[-1],
            "promotion_definition":"PRICE_TYPE_SALE_ONLY",
            "tpr_is_promotion":False,
        })
        start=None
        end=None
        event_qty=Decimal("0")
        event_sales_amount=Decimal("0")
        event_qty_ready=True
        event_sale_days=0
        event_upcs=set()

    for day in ordered_days:
        info=sale_days.get(day)
        if info is None:
            close_event()
            continue
        if start is None:
            start=day
        end=day
        event_sale_days+=1
        event_upcs.update(info.get("related_upcs") or [])
        event_sales_amount+=_d(info.get("sale_sales_amount"))
        if info.get("sale_quantity_ready") and info.get("sale_quantity") is not None:
            event_qty+=_d(info.get("sale_quantity"))
        else:
            event_qty_ready=False
    close_event()
    if not events:
        return None

    latest=events[-1]
    event_end=latest["end_date"]
    supported_to_event=[d for d in ordered_days if d<=event_end]
    promo_week_days=supported_to_event[-7:]
    promo_week_set=set(promo_week_days)

    actual_ready=bool(promo_week_days)
    actual_qty=Decimal("0")
    for day in promo_week_days:
        info=family_day.get(day) or {}
        if not info.get("total_quantity_ready") or info.get("total_quantity") is None:
            actual_ready=False
            break
        actual_qty+=_d(info.get("total_quantity"))

    baseline_days=[
        day for day in ordered_days
        if day not in promo_week_set
        and not (family_day.get(day) or {}).get("has_sale")
        and (family_day.get(day) or {}).get("total_quantity_ready")
        and (family_day.get(day) or {}).get("total_quantity") is not None
    ]
    baseline_qty=sum(
        (_d((family_day.get(day) or {}).get("total_quantity")) for day in baseline_days),
        Decimal("0"),
    )
    baseline_daily=(
        baseline_qty/Decimal(len(baseline_days))
        if baseline_days else None
    )
    expected_week=(
        baseline_daily*Decimal(len(promo_week_days))
        if baseline_daily is not None and promo_week_days else None
    )
    extra_qty=(
        actual_qty-expected_week
        if actual_ready and expected_week is not None else None
    )

    latest.update({
        "promotion_week_start_date":promo_week_days[0] if promo_week_days else None,
        "promotion_week_end_date":promo_week_days[-1] if promo_week_days else None,
        "promotion_week_supported_day_count":len(promo_week_days),
        "promotion_week_actual_qty":actual_qty if actual_ready else None,
        "promotion_week_expected_nonpromo_qty":expected_week,
        "promotion_week_extra_qty":extra_qty,
        "promotion_week_extra_qty_uom":uom if extra_qty is not None and uom else None,
        "promotion_week_extra_qty_status":(
            "READY"
            if extra_qty is not None and uom and len(baseline_days)>=3
            else "INSUFFICIENT_NONPROMO_BASELINE"
            if len(baseline_days)<3
            else "UNRESOLVED_MIXED_UOM"
        ),
        "nonpromo_baseline_daily_qty":baseline_daily,
        "nonpromo_baseline_day_count":len(baseline_days),
        "week_comparison_definition":"LATEST_7_COMPLETED_POS_DAYS_ENDING_AT_PROMO_EVENT_END_VS_NON_SALE_28D_DAILY_BASELINE",
    })
    return latest



def yipman_best_sellers(limit: int = 40) -> dict[str, Any]:
    """Fast Family Stock Flow watch for the Yipman / desktop Quick Check home.

    Keep Stock Flow on published Family movement plus canonical physical receipt
    events. Do not invoke the full Family -> Receiving Article -> UPC lineage
    builder here; that path is appropriate for item detail but is too expensive
    for an empty-search dashboard.
    """
    lim = max(1, min(int(limit or 40), 100))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        movement_days_7 = source_data_days(
            cur,
            "movement",
            limit=7,
            up_to=completed_through_date(),
        )
        completed_7_dates = {x["date"] for x in movement_days_7}
        day_count = len(movement_days_7)

        # One row per active Family from the serving table. Family movement is
        # already published/reconciled there, so Stock Flow does not need to
        # rebuild article lineage on every page load.
        cur.execute(
            """SELECT family_id,
                      MAX(main_article_number) AS family_article,
                      MAX(family_description) AS family_name,
                      MAX(product_class) AS category,
                      MAX(family_movement_7d) AS family_movement_7d,
                      MAX(family_movement_uom) AS family_movement_uom
               FROM quick_check_current
               WHERE family_id IS NOT NULL
                 AND COALESCE(family_movement_7d,0) > 0
                 AND COALESCE(quick_check_status,'') <> 'HISTORICAL_ONLY'
               GROUP BY family_id
               ORDER BY family_id"""
        )
        families = cur.fetchall()
        family_ids = [
            int(x["family_id"])
            for x in families
            if x.get("family_id") is not None
        ]

        # One set-based canonical receipt read supplies both 7D receipt totals,
        # recent receipt history, and observed-delivery weekdays.
        receipt_events = (
            _family_receipt_events_bulk(
                cur,
                family_ids,
                data_day_limit=180,
            )
            if family_ids
            else {}
        )

        rows: list[dict[str, Any]] = []
        qualifying_ids: list[int] = []

        for family in families:
            fid = int(family["family_id"])
            sold = family.get("family_movement_7d")
            sold_d = _d(sold) if sold is not None else Decimal("0")
            if sold_d <= 0:
                continue

            sold_uom = str(family.get("family_movement_uom") or "").strip().upper()
            if not sold_uom:
                continue

            events = [
                x for x in receipt_events.get(fid, [])
                if x.get("posting_date") is not None
                and x.get("receipt_quantity") is not None
                and _d(x.get("receipt_quantity")) > 0
            ]

            def receipt_value(event: dict[str, Any]) -> tuple[Any, str | None]:
                base_uom = str(event.get("base_receipt_uom") or "").strip().upper()
                entry_uom = str(event.get("receipt_uom") or "").strip().upper()
                if (
                    base_uom == sold_uom
                    and event.get("base_receipt_quantity") is not None
                ):
                    return event.get("base_receipt_quantity"), base_uom
                if (
                    entry_uom == sold_uom
                    and event.get("receipt_quantity") is not None
                ):
                    return event.get("receipt_quantity"), entry_uom
                if event.get("base_receipt_quantity") is not None and base_uom:
                    return event.get("base_receipt_quantity"), base_uom
                return event.get("receipt_quantity"), entry_uom or None

            events_7 = [
                x for x in events
                if x.get("posting_date") in completed_7_dates
            ]
            normalized = [receipt_value(x) for x in events_7]
            uoms = {u for _, u in normalized if u}
            missing_qty = any(q is None for q, _ in normalized)

            if normalized and len(uoms) == 1 and not missing_qty:
                receipt_qty = sum((_d(q) for q, _ in normalized), Decimal("0"))
                receipt_uom = next(iter(uoms))
                receipt_status = "READY"
            elif not normalized:
                receipt_qty = Decimal("0")
                receipt_uom = sold_uom
                receipt_status = "READY_ZERO_RECEIPTS"
            else:
                continue

            # Stock Flow only compares like-for-like Family movement UOM.
            if receipt_uom != sold_uom:
                continue

            ratio = receipt_qty / sold_d if sold_d > 0 else None
            if ratio is None or ratio < Decimal("1.50"):
                continue

            history = []
            for event in events[:2]:
                qty, uom = receipt_value(event)
                history.append({
                    "date": event.get("posting_date"),
                    "quantity": qty,
                    "uom": uom,
                    "receipt_date": event.get("posting_date"),
                    "receipt_qty": qty,
                    "receipt_uom": uom,
                    "receipt_movement_type": event.get("movement_type"),
                    "receipt_source": event.get("receipt_source"),
                })

            delivery_pattern = _delivery_pattern(
                events,
                lookback_days=180,
            )
            observed_delivery_days = list(
                delivery_pattern.get("observed_delivery_days") or []
            )
            friday_observation = next(
                (
                    x for x in observed_delivery_days
                    if int(x.get("weekday_number")) == 4
                ),
                None,
            )
            friday_count = int(
                (friday_observation or {}).get("receipt_date_count") or 0
            )
            friday_share = _d(
                (friday_observation or {}).get("receipt_date_share")
            )
            other_max_count = max(
                (
                    int(x.get("receipt_date_count") or 0)
                    for x in observed_delivery_days
                    if int(x.get("weekday_number")) != 4
                ),
                default=0,
            )
            friday_delivery_warning = bool(
                friday_count >= 2
                and friday_count > other_max_count
                and friday_share >= Decimal("0.50")
            )

            rows.append({
                "family_id": fid,
                "family_article": family.get("family_article"),
                "family_name": family.get("family_name"),
                "category": family.get("category"),
                "family_group_movement_7d": sold_d,
                "family_group_avg_qty_day": (
                    sold_d / Decimal(day_count)
                    if day_count > 0 else None
                ),
                "family_group_movement_uom": sold_uom,
                "family_receipt_history": history,
                "family_receipt_7d_qty": receipt_qty,
                "family_receipt_7d_uom": receipt_uom,
                "family_receipt_7d_day_count": len({
                    x.get("posting_date") for x in events_7
                    if x.get("posting_date") is not None
                }),
                "family_receipt_7d_status": receipt_status,
                "receipt_minus_selling_7d": receipt_qty - sold_d,
                "receipt_to_selling_ratio": ratio,
                "receipt_over_selling_pct": (ratio - Decimal("1")) * Decimal("100"),
                "recent_promotion_event": None,
                "observed_delivery_days": observed_delivery_days,
                "observed_delivery_weekday_numbers": [
                    int(x.get("weekday_number"))
                    for x in observed_delivery_days
                    if x.get("weekday_number") is not None
                ],
                "delivery_pattern_frequency": delivery_pattern.get("frequency"),
                "delivery_pattern_receipt_date_count": delivery_pattern.get("receipt_date_count"),
                "delivery_pattern_lookback_days": delivery_pattern.get("lookback_days"),
                "delivery_pattern_basis": delivery_pattern.get("basis"),
                "friday_delivery_warning": friday_delivery_warning,
                "friday_delivery_share": friday_share if friday_observation else None,
                "friday_delivery_receipt_date_count": friday_count,
            })
            qualifying_ids.append(fid)

        # Promotion evidence is intentionally calculated only for the small set
        # of Families already qualified for Stock Flow.
        if rows and qualifying_ids:
            sales_days_28 = source_data_days(
                cur,
                "sales_by_price_type",
                limit=28,
                up_to=completed_through_date(),
            )
            if sales_days_28:
                ph = ",".join(["%s"] * len(qualifying_ids))
                cur.execute(
                    f"""SELECT *
                        FROM quick_check_current
                        WHERE family_id IN ({ph})
                        ORDER BY family_id,upc_id""",
                    tuple(qualifying_ids),
                )
                all_family_rows = [dict(x) for x in cur.fetchall()]
                promo_family_rows: dict[int, list[dict[str, Any]]] = {}
                for row in all_family_rows:
                    if row.get("family_id") is not None:
                        promo_family_rows.setdefault(int(row["family_id"]), []).append(row)
                promo_daily = _batch_daily_sales_by_price_type(
                    cur,
                    all_family_rows,
                    sales_days_28,
                )
                for row in rows:
                    row["recent_promotion_event"] = _recent_family_sale_event_from_batch(
                        promo_family_rows.get(int(row["family_id"]), []),
                        promo_daily,
                        sales_days_28,
                        str(row.get("family_group_movement_uom") or ""),
                    )

        # Latest receipt cost follows Family-detail receipt-cost authority:
        # MOVEMENT_RECEIPT_VALUATION on the latest physical receipt date.
        for row in rows:
            history = row.get("family_receipt_history") or []
            row["latest_receipt_date"] = (
                history[0].get("date") if history else None
            )
            row["latest_receipt_cost"] = None
            row["latest_receipt_cost_uom"] = None
            row["latest_receipt_cost_source"] = None

        cost_targets = {
            int(row["family_id"]): row.get("latest_receipt_date")
            for row in rows
            if row.get("family_id") is not None
            and row.get("latest_receipt_date") is not None
        }
        if cost_targets:
            cost_family_ids = sorted(cost_targets)
            cost_dates = sorted(set(cost_targets.values()))
            fam_ph = ",".join(["%s"] * len(cost_family_ids))
            date_ph = ",".join(["%s"] * len(cost_dates))
            cur.execute(
                f"""SELECT co.family_id,co.business_date,
                           COALESCE(co.cost_per_base_uom,co.cost_amount) AS receipt_cost,
                           COALESCE(bu.uom_code,cu.uom_code) AS cost_uom,
                           co.movement_type,co.source_type,co.file_id,
                           co.source_row_number,co.cost_observation_id
                    FROM article_cost_observation co
                    LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
                    LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
                    WHERE co.family_id IN ({fam_ph})
                      AND co.business_date IN ({date_ph})
                      AND co.source_type='MOVEMENT_RECEIPT_VALUATION'
                      AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
                      AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
                    ORDER BY co.family_id,co.business_date DESC,
                             co.cost_observation_id DESC""",
                (*cost_family_ids,*cost_dates),
            )
            latest_cost_by_family: dict[int, dict[str, Any]] = {}
            for cost_row in cur.fetchall():
                fid = int(cost_row["family_id"])
                if cost_targets.get(fid) != cost_row.get("business_date"):
                    continue
                if fid not in latest_cost_by_family:
                    latest_cost_by_family[fid] = dict(cost_row)
            for row in rows:
                cost_row = latest_cost_by_family.get(int(row["family_id"]))
                if not cost_row:
                    continue
                row["latest_receipt_cost"] = cost_row.get("receipt_cost")
                row["latest_receipt_cost_uom"] = cost_row.get("cost_uom")
                row["latest_receipt_cost_source"] = cost_row.get("source_type")

        # Stock Flow also shows live Effective OH. A Family True Stock count is
        # therefore visible here immediately instead of waiting for Phase 3.
        if rows:
            sf_ids=sorted({int(x["family_id"]) for x in rows if x.get("family_id") is not None})
            sf_ph=",".join(["%s"]*len(sf_ids))
            cur.execute(
                f"""SELECT * FROM quick_check_current
                    WHERE family_id IN ({sf_ph})
                    ORDER BY family_id,ean_upc""",
                tuple(sf_ids),
            )
            sf_children: dict[int,list[dict[str,Any]]]={}
            for child in cur.fetchall():
                if child.get("family_id") is not None:
                    sf_children.setdefault(int(child["family_id"]),[]).append(child)
            for row in rows:
                fid=int(row["family_id"])
                effective=_family_effective_oh(cur,sf_children.get(fid,[]))
                row["family_oh"]=effective.get("quantity")
                row["family_oh_uom"]=effective.get("uom")
                row["family_oh_source"]=effective.get("source")
                row["family_oh_status"]=effective.get("status")
                row["family_oh_reason"]=effective.get("reason")

        cur.close()

    rows.sort(
        key=lambda r: (
            -float(r.get("receipt_over_selling_pct") or 0),
            -float(r.get("receipt_minus_selling_7d") or 0),
            str(r.get("family_name") or ""),
        )
    )
    return {
        "contract_version": "YIPMAN_STOCK_FLOW_V7_OVERSALE_FRIDAY_COST",
        "count": len(rows),
        "movement_day_count_7d": day_count,
        "rows": rows[:lim],
        "rules": {
            "scope": "FAMILY_ARTICLE_ONLY",
            "qualification": "7D_RECEIPT_AT_LEAST_150_PERCENT_OF_7D_SELLING_MVT",
            "comparison_uom": "SAME_FAMILY_MOVEMENT_UOM_ONLY",
            "default_sort": "RECEIPT_OVER_SELLING_PCT_DESC",
            "receipt_history": "LAST_2_CANONICAL_PHYSICAL_RECEIPTS",
            "latest_receipt_cost": "MOVEMENT_RECEIPT_VALUATION_ON_LATEST_PHYSICAL_RECEIPT_DATE",
            "friday_warning": "FRIDAY_DOMINANT_AT_LEAST_2_DATES_AND_AT_LEAST_50_PERCENT_SHARE",
            "receipt_total": "DE_DUPED_7D_PHYSICAL_RECEIPT",
            "movement_source": "PUBLISHED_QUICK_CHECK_CURRENT_FAMILY_7D",
            "receipt_source": "CANONICAL_PHYSICAL_101_109_EVENTS",
            "recent_promotion_window": "LATEST_28_COMPLETED_CANONICAL_POS_SALES_DAYS",
            "promotion_scope": "QUALIFIED_FAMILIES_ONLY",
            "promotion_definition": "PRICE_TYPE_SALE_ONLY",
            "tpr_is_promotion": False,
            "observed_delivery_days": "CANONICAL_PHYSICAL_RECEIPTS_LATEST_180_COMPLETED_MVT_DAYS",
        },
    }



def invalidate_operational_review_caches_for_true_stock() -> dict[str,Any]:
    """Invalidate every OH-dependent operational snapshot after True Stock.

    True Stock is an immediate physical-count authority. Cached Ordering,
    Pricing, Current TPR, and Home summaries must never keep the previous OH
    after a successful count.
    """
    global _HOME_SUMMARY_CACHE_VALUE, _HOME_SUMMARY_CACHE_AT

    with _ORDERING_REVIEW_CACHE_LOCK:
        _ORDERING_REVIEW_CACHE_VALUES.clear()
        _ORDERING_REVIEW_CACHE_AT.clear()
    with _PRICING_REVIEW_CACHE_LOCK:
        _PRICING_REVIEW_CACHE_VALUES.clear()
        _PRICING_REVIEW_CACHE_AT.clear()
    with _TPR_REVIEW_CACHE_LOCK:
        _TPR_REVIEW_CACHE_VALUES.clear()
        _TPR_REVIEW_CACHE_AT.clear()
    with _HOME_SUMMARY_CACHE_LOCK:
        _HOME_SUMMARY_CACHE_VALUE=None
        _HOME_SUMMARY_CACHE_AT=0.0

    deleted=[]
    try:
        with db_conn() as conn:
            cur=conn.cursor(dictionary=True)
            for table in (
                "backoffice_ordering_review_cache",
                "backoffice_pricing_review_cache",
                "yipman_current_tpr_review_cache",
                "backoffice_home_summary_cache",
            ):
                try:
                    cur.execute(f"DELETE FROM {table}")
                    deleted.append(table)
                except Exception:
                    # A cache table may not exist yet on a new install.
                    pass
            conn.commit()
            cur.close()
    except Exception:
        pass
    return {
        "status":"INVALIDATED",
        "reason":"TRUE_STOCK_CHANGED",
        "memory_caches":["ORDERING","PRICING","CURRENT_TPR","HOME"],
        "persisted_caches":deleted,
    }


def best_sellers_review(limit: int = 8) -> dict[str, Any]:
    """Fast Family-level Best Sellers payload for the Yipman empty-search home.

    This intentionally avoids inventory_review() and the full Family -> Article
    -> UPC Quick Check lineage build. Family 7D movement is already published in
    quick_check_current; canonical physical receipts are loaded only for the
    small selected Family set.
    """
    limit=max(1,min(int(limit or 8),20))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        movement_days_7=source_data_days(
            cur,
            "movement",
            limit=7,
            up_to=completed_through_date(),
        )
        day_count=len(movement_days_7)

        cur.execute(
            """SELECT family_id,
                      MAX(main_article_number) AS family_article,
                      MAX(family_description) AS family_name,
                      MAX(product_class) AS category,
                      MAX(family_movement_7d) AS family_movement_7d,
                      MAX(family_movement_uom) AS family_movement_uom
               FROM quick_check_current
               WHERE family_id IS NOT NULL
                 AND family_movement_7d IS NOT NULL
                 AND family_movement_7d > 0
                 AND COALESCE(quick_check_status,'') <> 'HISTORICAL_ONLY'
               GROUP BY family_id
               ORDER BY MAX(family_movement_7d) DESC, family_id
               LIMIT %s""",
            (limit,),
        )
        families=cur.fetchall()
        fids=[int(x["family_id"]) for x in families if x.get("family_id") is not None]

        recent_events=_family_receipt_events_bulk(
            cur,
            fids,
            data_day_limit=60,
        ) if fids else {}
        completed_7_dates={x["date"] for x in movement_days_7}

        rows=[]
        for family in families:
            fid=int(family["family_id"])
            movement_qty=family.get("family_movement_7d")
            movement_uom=str(family.get("family_movement_uom") or "").strip().upper()
            events=[
                x for x in recent_events.get(fid,[])
                if x.get("posting_date") is not None
                and x.get("receipt_quantity") is not None
                and _d(x.get("receipt_quantity")) > 0
            ]

            def receipt_value(event: dict[str,Any]) -> tuple[Any,str|None]:
                base_uom=str(event.get("base_receipt_uom") or "").strip().upper()
                entry_uom=str(event.get("receipt_uom") or "").strip().upper()
                if (
                    movement_uom
                    and base_uom == movement_uom
                    and event.get("base_receipt_quantity") is not None
                ):
                    return event.get("base_receipt_quantity"),base_uom
                if (
                    movement_uom
                    and entry_uom == movement_uom
                    and event.get("receipt_quantity") is not None
                ):
                    return event.get("receipt_quantity"),entry_uom
                if event.get("base_receipt_quantity") is not None and base_uom:
                    return event.get("base_receipt_quantity"),base_uom
                return event.get("receipt_quantity"),entry_uom or None

            history=[]
            for event in events[:2]:
                qty,uom=receipt_value(event)
                history.append({
                    "date":event.get("posting_date"),
                    "quantity":qty,
                    "uom":uom,
                })

            events_7=[x for x in events if x.get("posting_date") in completed_7_dates]
            normalized=[receipt_value(x) for x in events_7]
            uoms={u for _,u in normalized if u}
            missing_qty=any(q is None for q,_ in normalized)
            if normalized and len(uoms)==1 and not missing_qty:
                receipt_qty=sum((_d(q) for q,_ in normalized),Decimal("0"))
                receipt_uom=next(iter(uoms))
                receipt_status="READY"
            elif not normalized:
                receipt_qty=Decimal("0")
                receipt_uom=movement_uom or None
                receipt_status="READY_ZERO_RECEIPTS"
            else:
                receipt_qty=None
                receipt_uom=None
                receipt_status="HOLD_MIXED_OR_MISSING_RECEIPT_UOM"

            rows.append({
                "family_id":fid,
                "family_article":family.get("family_article"),
                "family_name":family.get("family_name"),
                "category":family.get("category"),
                "family_group_movement_7d":movement_qty,
                "family_group_movement_uom":movement_uom or None,
                "family_group_avg_qty_day":(
                    _d(movement_qty)/Decimal(day_count)
                    if movement_qty is not None and day_count > 0
                    else None
                ),
                "family_group_movement_days_7d":day_count,
                "family_receipt_7d_qty":receipt_qty,
                "family_receipt_7d_uom":receipt_uom,
                "family_receipt_7d_count":len(events_7),
                "family_receipt_7d_status":receipt_status,
                "family_receipt_history":history,
            })

        rows.sort(
            key=lambda x:(
                -float(x.get("family_group_avg_qty_day") or 0),
                -float(x.get("family_group_movement_7d") or 0),
                str(x.get("family_name") or ""),
            )
        )
        cur.close()

    return {
        "contract_version":"YIPMAN_BEST_SELLERS_V1",
        "count":len(rows),
        "movement_day_count":day_count,
        "rows":rows,
    }



def yipman_receipt_event_detail(
    family_id: int,
    receipt_date: date,
    article_number: str | None = None,
) -> dict[str, Any]:
    """Return canonical physical receipt details for one Family/date event."""
    fid = int(family_id)
    article_filter = str(article_number or "").strip() or None
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT family_id,main_article_number,family_description
               FROM product_family
               WHERE family_id=%s
               LIMIT 1""",
            (fid,),
        )
        family = cur.fetchone()
        if not family:
            cur.close()
            raise ValueError("FAMILY_NOT_FOUND")

        events = [
            x for x in _family_receipt_events(
                cur,
                fid,
                data_day_limit=365,
            )
            if x.get("posting_date") == receipt_date
            and x.get("receipt_quantity") is not None
            and _d(x.get("receipt_quantity")) > 0
        ]
        if article_filter:
            events = [
                x for x in events
                if str(x.get("article_number") or "").strip() == article_filter
            ]
        cur.close()

    base_events = [
        x for x in events
        if x.get("base_receipt_quantity") is not None
        and _d(x.get("base_receipt_quantity")) > 0
        and x.get("base_receipt_uom")
    ]
    base_uoms = {
        str(x.get("base_receipt_uom") or "").strip().upper()
        for x in base_events
    }
    if events and len(base_events) == len(events) and len(base_uoms) == 1:
        total_qty = sum(
            (_d(x.get("base_receipt_quantity")) for x in base_events),
            Decimal("0"),
        )
        total_uom = next(iter(base_uoms))
        total_basis = "BASE_UOM"
    else:
        entry_uoms = {
            str(x.get("receipt_uom") or "").strip().upper()
            for x in events
            if x.get("receipt_uom")
        }
        if events and len(entry_uoms) == 1 and all(
            x.get("receipt_quantity") is not None for x in events
        ):
            total_qty = sum(
                (_d(x.get("receipt_quantity")) for x in events),
                Decimal("0"),
            )
            total_uom = next(iter(entry_uoms))
            total_basis = "ENTRY_UOM"
        else:
            total_qty = None
            total_uom = "MIXED" if events else None
            total_basis = "MIXED_OR_NO_EVENT"

    purchase_orders = sorted({
        str(x.get("purchase_order") or "").strip()
        for x in events
        if str(x.get("purchase_order") or "").strip()
    })
    gr_numbers = sorted({
        str(x.get("gr_number") or "").strip()
        for x in events
        if str(x.get("gr_number") or "").strip()
    })

    return {
        "contract_version": "YIPMAN_RECEIPT_EVENT_DETAIL_V1",
        "family_id": fid,
        "family_article": family.get("main_article_number"),
        "family_name": family.get("family_description"),
        "receipt_date": receipt_date,
        "article_filter": article_filter,
        "receipt_qty": total_qty,
        "receipt_uom": total_uom,
        "receipt_qty_basis": total_basis,
        "receipt_event_count": len(events),
        "purchase_order_count": len(purchase_orders),
        "gr_number_count": len(gr_numbers),
        "purchase_orders": purchase_orders,
        "gr_numbers": gr_numbers,
        "events": events,
        "rules": {
            "physical_receipt": "101_OR_109_WITH_REVERSALS_DEDUPED",
            "107_role": "COST_STAGE_ONLY_NOT_PHYSICAL_QTY",
            "canonical_movement_files_only": True,
        },
    }


def inventory_review(
    limit: int = 200,
    category: str = "ALL",
    query: str | None = None,
    lightweight: bool = False,
    include_price_preview: bool = False,
    include_oh: bool = False,
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
        family_system_cache: dict[int, dict[str, Any]] = {}
        family_cost_cache: dict[int, dict[str, Any] | None] = {}
        # Lightweight search stays fast by default. Yipman can explicitly request
        # one set-based CURRENT-price + SUGGEST preview pass for the returned
        # rows without enabling family OH roll-forward.
        resolve_live_price = (not lightweight) or bool(include_price_preview)
        live_prices = (
            _bulk_live_current_prices(cur, qrows)
            if resolve_live_price else {}
        )
        price_previews = (
            _quick_price_preview_by_upc(cur, qrows, live_prices)
            if include_price_preview else {}
        )
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

            # Family/Main Article cost is a separate authority from the UPC
            # converted selling-unit cost. Resolve it once per Family for Quick
            # Search so the Family header can show the actual current Family cost.
            if q and fid is not None and fid not in family_cost_cache:
                family_cost_cache[fid]=_family_current_cost(cur,fid)
            family_cost=family_cost_cache.get(fid) if fid is not None else None

            # Normal lightweight Quick Check search skips OH roll-forward for speed.
            # PI can explicitly request include_oh=True so System OH and Effective OH
            # are both resolved from the same Family inventory evidence.
            if lightweight and not include_oh:
                family_oh = {}
                family_system_oh = {}
            else:
                if fid is not None and fid not in family_cache:
                    cur.execute(
                        "SELECT * FROM quick_check_current WHERE family_id=%s ORDER BY ean_upc",
                        (fid,),
                    )
                    children = cur.fetchall()
                    live_system_oh = _family_system_oh(cur, children)
                    live_family_oh = _family_effective_oh(cur, children)
                    family_system_cache[fid] = live_system_oh
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
                family_system_oh = family_system_cache.get(fid or -1, {})
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
                    # Never substitute the Family aggregate when the assigned
                    # Receiving Article is the Family/Main Article itself.
                    # Keep the source Article's actual physical receipt history.
                    "receipt_history": family_ctx.get("family_source_receipt_history", []),
                    "receipt_7d_qty": family_ctx.get("family_source_receipt_7d_qty"),
                    "receipt_7d_uom": family_ctx.get("family_source_receipt_7d_uom"),
                    "receipt_7d_status": family_ctx.get("family_source_receipt_7d_status"),
                    "receipt_7d_day_count": family_ctx.get("family_source_receipt_7d_day_count"),
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
                    "family_source_receipt_verified": family_ctx.get("family_source_receipt_verified"),
                    "family_source_receipt_history": family_ctx.get("family_source_receipt_history", []),
                    "family_source_receipt_7d_qty": family_ctx.get("family_source_receipt_7d_qty"),
                    "family_source_receipt_7d_uom": family_ctx.get("family_source_receipt_7d_uom"),
                    "family_source_receipt_7d_status": family_ctx.get("family_source_receipt_7d_status"),
                    "family_source_receipt_7d_day_count": family_ctx.get("family_source_receipt_7d_day_count"),
                    "family_receipt_verified": family_ctx.get("family_receipt_verified"),
                    "family_receipt_movement_type": family_ctx.get("family_receipt_movement_type"),
                    "family_receipt_date": family_ctx.get("family_receipt_date"),
                    "family_receipt_qty": family_ctx.get("family_receipt_qty"),
                    "family_receipt_uom": family_ctx.get("family_receipt_uom"),
                    "family_receipt_source": family_ctx.get("family_receipt_source"),
                    "family_receipt_history": family_ctx.get("family_receipt_history", []),
                    "family_receipt_7d_qty": family_ctx.get("family_receipt_7d_qty"),
                    "family_receipt_7d_uom": family_ctx.get("family_receipt_7d_uom"),
                    "family_receipt_7d_status": family_ctx.get("family_receipt_7d_status"),
                    "family_receipt_7d_day_count": family_ctx.get("family_receipt_7d_day_count"),
                    "family_receipt_7d_basis": family_ctx.get("family_receipt_7d_basis"),
                    "receiving_receipt_history": assigned_receiving_row.get("receipt_history", []),
                    "receiving_receipt_7d_qty": assigned_receiving_row.get("receipt_7d_qty"),
                    "receiving_receipt_7d_uom": assigned_receiving_row.get("receipt_7d_uom"),
                    "receiving_receipt_7d_status": assigned_receiving_row.get("receipt_7d_status"),
                    "receiving_receipt_7d_day_count": assigned_receiving_row.get("receipt_7d_day_count"),
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
                    "suggest_price": (
                        price_previews.get(int(row["upc_id"]), {}).get("suggested_price")
                        if row.get("upc_id") is not None else None
                    ),
                    "suggest_price_status": (
                        price_previews.get(int(row["upc_id"]), {}).get("suggestion_status")
                        if row.get("upc_id") is not None else None
                    ),
                    "suggest_price_basis": (
                        price_previews.get(int(row["upc_id"]), {}).get("suggestion_basis")
                        if row.get("upc_id") is not None else None
                    ),
                    "sweet_spot_price": row.get("sweet_spot_price"),
                    "company_price_a": row.get("company_price_a"),
                    "company_price_b": row.get("company_price_b"),
                    "company_price_c": row.get("company_price_c"),
                    "cost": row.get("current_cost_per_selling_unit"),
                    "cost_uom": row.get("selling_uom"),
                    "cost_source": row.get("cost_source"),
                    "cost_date": row.get("cost_date"),
                    "family_cost": family_cost.get("cost_per_base") if family_cost else None,
                    "family_cost_uom": family_cost.get("base_uom") if family_cost else None,
                    "family_cost_source": family_cost.get("source") if family_cost else None,
                    "family_cost_date": family_cost.get("date") if family_cost else None,
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
                    "family_system_oh": family_system_oh.get("quantity"),
                    "family_system_oh_uom": family_system_oh.get("uom"),
                    "family_system_oh_source": family_system_oh.get("source"),
                    "family_system_oh_status": family_system_oh.get("status"),
                    "family_system_oh_reason": family_system_oh.get("reason"),
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
        "contract_version": "BACKOFFICE_INVENTORY_V8_QUICK_PRICE_RECEIPT",
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
            "include_price_preview": bool(include_price_preview),
            "include_oh": bool(include_oh),
            "quick_price_preview_rule": "SAME_14D_GP_PER_DAY_ENGINE_AND_QUALIFICATION_AS_PRICE_REVIEW_PLUS_240_249_EQUALITY",
            "family_receipt_7d_rule": "CANONICAL_PHYSICAL_101_109_LATEST_7_COMPLETED_MVT_DAYS;107_COST_STAGE_EXCLUDED",
            "lightweight_skips": (
                ([] if include_oh else ["FAMILY_SYSTEM_AND_EFFECTIVE_OH_ROLLFORWARD"])
                + ([] if include_price_preview else ["LIVE_CURRENT_PRICE_AND_SUGGEST_PREVIEW"])
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
                   WHERE cache_key='MOBILE_HOME_V339'
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
               VALUES ('MOBILE_HOME_V339',%s)
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
        _overlay_active_true_stock_effective_oh(cur,rows)
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

        if health.get("status") not in {"CURRENT","STALE_ESTIMATE_AVAILABLE"}:
            cur.close()
            return {
                "pricing": {
                    "status": "UNAVAILABLE_NO_USABLE_SOURCE_HISTORY",
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
            "status": health.get("status"),
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
    if health.get("status") not in {"CURRENT","STALE_ESTIMATE_AVAILABLE"}:
        price_perf = _home_price_performance_summary()
        ordering = {
            "status": "UNAVAILABLE_NO_USABLE_SOURCE_HISTORY",
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
            "status": health.get("status"),
            "family_count": int(fresh.get("family_count") or 0)+int(frozen.get("family_count") or 0),
            "attention_count": int(fresh.get("attention_count") or 0)+int(frozen.get("attention_count") or 0),
            "fresh_family_count": int(fresh.get("family_count") or 0),
            "frozen_family_count": int(frozen.get("family_count") or 0),
            "data_health": health,
            "basis": "BULK_ORDERING_SUGGESTIONS_WITHOUT_RECEIPT_DETAIL_ENRICHMENT",
        }

    return {
        "contract_version": "BACKOFFICE_HOME_SUMMARY_V3_BEST_AVAILABLE",
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

    # Cache age alone is not enough: a same-business-day upload can advance
    # canonical POS/MVT while completed_through_date() remains unchanged.
    # Compare the cached analysis basis to live canonical source coverage so
    # Home refreshes immediately after a newly published upload.
    live_health = _pricing_review_data_health(allow_stale_estimate=True)
    cached_health = (((cached or {}).get("ordering") or {}).get("data_health") or {})
    source_changed = bool(cached) and (
        str(cached_health.get("pos_data_through") or "")
        != str(live_health.get("pos_data_through") or "")
        or str(cached_health.get("movement_data_through") or "")
        != str(live_health.get("movement_data_through") or "")
    )

    age = time.monotonic() - _HOME_SUMMARY_CACHE_AT if cached is not None else None
    stale = (
        cached is None
        or source_changed
        or age is None
        or age >= _HOME_SUMMARY_CACHE_TTL_SECONDS
    )
    if force or stale:
        _request_home_summary_refresh()

    if cached is None:
        return {
            "contract_version": "BACKOFFICE_HOME_SUMMARY_V4_SOURCE_AWARE_CACHE",
            "cache_status": "WARMING",
            "refreshing": True,
            "refresh_error": _HOME_SUMMARY_LAST_ERROR,
            "current_source_health": live_health,
            "source_changed_since_analysis": False,
            "pricing": {},
            "performance": {},
            "ordering": {},
        }

    return {
        **cached,
        "contract_version": "BACKOFFICE_HOME_SUMMARY_V4_SOURCE_AWARE_CACHE",
        "cache_status": (
            "SOURCE_CHANGED_REFRESHING"
            if source_changed else ("STALE_REFRESHING" if stale else "HIT")
        ),
        "refreshing": bool(_HOME_SUMMARY_REFRESHING),
        "refresh_error": _HOME_SUMMARY_LAST_ERROR,
        "current_source_health": live_health,
        "source_changed_since_analysis": source_changed,
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


def _pricing_review_data_health(*, allow_stale_estimate: bool = True) -> dict[str, Any]:
    """Resolve completed POS/MVT freshness for pricing decisions.

    Ordering/Pricing never wait for a grace cutoff. The newest available
    canonical POS and MVT evidence is used independently. Missing source dates
    are excluded rather than treated as zero.
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
    missing = []
    if pos_through != expected_through:
        missing.append("POS")
    if mvt_through != expected_through:
        missing.append("MVT")

    current = not missing
    estimate_available = bool(
        allow_stale_estimate
        and not current
        and pos_through is not None
        and mvt_through is not None
    )
    status = (
        "CURRENT"
        if current
        else ("STALE_ESTIMATE_AVAILABLE" if estimate_available else "BLOCKED_STALE_REQUIRED_DATA")
    )
    # Price optimization is POS-driven; keep the newest usable POS day even
    # when MVT is a few days behind. MVT freshness remains visible separately.
    data_through = expected_through if current else pos_through
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
            "BEST_AVAILABLE_INDEPENDENT_POS_MVT_NO_FRESHNESS_GATE"
            if allow_stale_estimate
            else "PRICE_REVIEW_REQUIRES_CURRENT_COMPLETED_POS_AND_MVT"
        ),
        "warning": (
            None
            if current
            else (
                f"Best available estimate uses POS through {pos_through} and "
                f"MVT through {mvt_through}; missing dates are ignored, not zero-filled. "
                f"Reference completed date is {expected_through}."
                if estimate_available
                else "A usable pricing estimate requires at least one canonical POS day and one canonical MVT day."
            )
        ),
    }

def pricing_review(
    category: str = "ALL",
    limit: int = 1000,
    *,
    include_accepted: bool = False,
    allow_stale_estimate: bool = True,
) -> dict[str, Any]:
    """Pricing suggestions with CURRENT fields from live Quick Check serving.

    Accepted suggestions are suppressed only while the current-price evidence
    and candidate-price fingerprint remain unchanged. New current price evidence
    or a changed candidate automatically makes the UPC eligible to appear again.

    Operational review uses best-available canonical source days when recent
    POS or MVT uploads are missing; source gaps stay visible in data health.
    """
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "LIVE", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")

    data_health = _pricing_review_data_health(
        allow_stale_estimate=allow_stale_estimate
    )
    if data_health["status"] not in {"CURRENT", "STALE_ESTIMATE_AVAILABLE"}:
        return {
            "contract_version": "BACKOFFICE_PRICING_REVIEW_V9_PROACTIVE_TESTING",
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
        report_date=(data_health.get("pos_data_through") if estimate_only else None),
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
                           current_oh,current_oh_uom,doh,sweet_spot_price,
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
            _overlay_active_true_stock_effective_oh(cur,list(live_by_upc.values()))
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
        row["current_oh_source"] = live.get("current_oh_source") or live.get("live_effective_oh_source") or "QUICK_CHECK_CURRENT"
        row["current_oh_basis"] = live.get("current_oh_basis") or "PUBLISHED_QUICK_CHECK_CURRENT"
        row["doh"] = live.get("doh")
        row["dos"] = live.get("dos")

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

        raw_target_candidate = _positive_price(row.get("candidate_price"))
        company_low = _positive_price(row.get("company_range_low"))
        company_high = _positive_price(row.get("company_range_high"))
        target_candidate = (
            _retail_price_point(
                raw_target_candidate,
                min_price=company_low,
                max_price=company_high,
            )
            if raw_target_candidate is not None
            else None
        )
        tested_evidence_price = _positive_price(live.get("sweet_spot_price"))
        observed_candidates = list(row.get("top_observed_candidates") or [])
        current_dec = _positive_price(current_price)
        cost_dec = _positive_price(current_cost)
        tested_floor = (
            max(
                x for x in (
                    (cost_dec + Decimal("0.01")) if cost_dec is not None else None,
                    company_low,
                )
                if x is not None
            )
            if cost_dec is not None or company_low is not None
            else None
        )
        tested_price = (
            _retail_price_point(
                tested_evidence_price,
                min_price=tested_floor,
                max_price=company_high,
            )
            if tested_evidence_price is not None
            else None
        )
        if tested_price is None:
            tested_price = tested_evidence_price
        current_oh = _d(live.get("current_oh")) if live.get("current_oh") is not None else None

        row["tested_price"] = tested_price
        row["tested_evidence_price"] = tested_evidence_price
        row["tested_price_basis"] = "RETAIL_ALIGNED_STRONGEST_PROVED_HISTORICAL_SWEET_SPOT"
        row["target_sweet_spot_price"] = target_candidate
        row["raw_target_sweet_spot_price"] = raw_target_candidate
        row["price_point_rounding"] = "NEAREST_OF_29_49_59_69_79_99"
        row["testing_price"] = None
        row["testing_target_price"] = None
        row["testing_price_basis"] = None
        row["testing_step_rule"] = "CURRENT_TO_TARGET_MIN_0_45_STEP_NEAREST_OBSERVED_WITHIN_GRADUAL_CAP"

        # Re-evaluate actionability from the current serving row instead of
        # inheriting the upstream Performance queue's review_status.  The
        # Performance row is only the candidate/evidence seed; the pricing
        # review overlays live price, cost, OH and readiness immediately above.
        # Requiring the older review_status here can incorrectly collapse the
        # entire Price Suggestions queue to zero after a serving refresh.
        base_actionable = bool(
            str(live.get("quick_check_status") or "").upper() == "READY"
            and current_dec is not None
            and current_dec > 0
            and cost_dec is not None
            and cost_dec > 0
            and current_oh is not None
            and current_oh > 0
        )

        pair_fix = bool(row.get("priority_240_249_mismatch"))
        has_company = bool(row.get("has_company_reference"))
        current_within_company = row.get("current_within_company_range")
        outside_company = bool(
            has_company and current_within_company in (False, 0)
        )
        pclass = str(row.get("category") or live.get("product_class") or "").upper()
        velocity_7d = (
            _d(row.get("velocity_7d"))
            if row.get("velocity_7d") is not None else Decimal("0")
        )
        velocity_28d = (
            _d(row.get("velocity_28d"))
            if row.get("velocity_28d") is not None else Decimal("0")
        )
        doh = _d(row.get("doh")) if row.get("doh") is not None else None
        slow_velocity = bool(
            velocity_28d > 0 and velocity_7d < velocity_28d * Decimal("0.80")
        )
        freshness_test_needed = bool(
            base_actionable
            and (
                (
                    pclass in {"FRESH", "LIVE"}
                    and (
                        velocity_7d <= 0
                        or slow_velocity
                        or (doh is not None and doh >= Decimal("5"))
                    )
                )
                or (
                    pclass == "FROZEN"
                    and doh is not None
                    and doh >= Decimal("60")
                )
            )
        )
        tested_gap = bool(
            base_actionable
            and tested_price is not None
            and tested_price > cost_dec
            and abs(tested_price - current_dec) > Decimal("0.25")
        )
        gp_opportunity = (
            _d(row.get("gp_per_day_opportunity"))
            if row.get("gp_per_day_opportunity") is not None
            else Decimal("0")
        )

        action_price = None
        reason_code = None
        reason_text = None
        testing_target = None
        testing_price = None

        if pair_fix and raw_target_candidate is not None and base_actionable:
            # 240/249 equality is a price-integrity rule, not a sweet-spot test.
            # Copy the exact 240 authority price; do not merchandise-round it.
            action_price = raw_target_candidate
            reason_code = "PAIR_FIX"
            reason_text = "240=249 PRICE ALIGNMENT"
        elif outside_company and base_actionable:
            if company_low is not None and current_dec < company_low:
                action_price = company_low
            elif company_high is not None and current_dec > company_high:
                action_price = company_high
            if action_price is not None and action_price > cost_dec:
                reason_code = "COMPANY_RANGE"
                reason_text = "COMPANY PRICE RANGE CORRECTION"
            else:
                action_price = None
        elif freshness_test_needed:
            testing_target = _freshness_velocity_target(
                current=current_dec,
                current_cost=cost_dec,
                current_velocity=velocity_7d,
                observed_candidates=observed_candidates,
                company_low=company_low,
                company_high=company_high,
            )
            testing_price = _next_testing_price(
                current_dec,
                testing_target,
                observed_candidates=observed_candidates,
                min_price=company_low,
                max_price=company_high,
            )
            if (
                testing_price is not None
                and testing_price > cost_dec
                and abs(testing_price - current_dec) > Decimal("0.01")
            ):
                action_price = testing_price
                reason_code = "VELOCITY_TEST"
                reason_text = "FRESHNESS VELOCITY TEST"
        elif tested_gap:
            testing_target = tested_price
            testing_price = _next_testing_price(
                current_dec,
                testing_target,
                observed_candidates=observed_candidates,
                min_price=company_low,
                max_price=company_high,
            )
            if (
                testing_price is not None
                and testing_price > cost_dec
                and abs(testing_price - current_dec) > Decimal("0.01")
            ):
                action_price = testing_price
                reason_code = "SWEET_SPOT_GAP"
                reason_text = "STEP TOWARD TESTED SWEET SPOT"
        elif (
            base_actionable
            and gp_opportunity > 0
            and target_candidate is not None
            and target_candidate > cost_dec
            and abs(target_candidate - current_dec) > Decimal("0.01")
        ):
            testing_target = target_candidate
            testing_price = _next_testing_price(
                current_dec,
                testing_target,
                observed_candidates=observed_candidates,
                min_price=company_low,
                max_price=company_high,
            )
            if (
                testing_price is not None
                and testing_price > cost_dec
                and abs(testing_price - current_dec) > Decimal("0.01")
            ):
                action_price = testing_price
                reason_code = "GP_DOLLAR_TEST"
                reason_text = "GP$/DAY CONTROLLED TEST"

        row["testing_price"] = testing_price
        row["testing_target_price"] = testing_target
        # Backward-compatible API field names stay in place, while all new UI
        # language treats the controlled test step as the TPR Suggestion Price.
        row["tpr_suggestion_price"] = testing_price
        row["tpr_suggestion_target_price"] = testing_target
        row["tpr_suggestion_price_basis"] = (
            "CONTROLLED_TPR_PRICE_TEST"
            if testing_price is not None
            else None
        )
        row["testing_price_basis"] = (
            "SLOW_MOVING_FRESHNESS_VELOCITY_TEST"
            if reason_code == "VELOCITY_TEST"
            else (
                "CONTROLLED_STEP_TOWARD_STRONGEST_PROVED_TESTED_PRICE"
                if reason_code == "SWEET_SPOT_GAP"
                else (
                    "CONTROLLED_GP_DOLLAR_OPPORTUNITY_TEST"
                    if reason_code == "GP_DOLLAR_TEST"
                    else None
                )
            )
        )
        row["freshness_test_needed"] = freshness_test_needed
        row["slow_velocity_trend"] = slow_velocity
        row["company_range_violation"] = outside_company

        current_type_upper = str(row.get("current_price_type") or "").strip().upper()
        sale_locked = current_type_upper == "SALE"
        active_tpr = current_type_upper == "TPR"
        reg_like = current_type_upper in {"REG", "REGULAR", "IN STORE", "INSTORE", "STOR"}
        proven_sweet_spot = bool(
            reg_like
            and reason_code != "VELOCITY_TEST"
            and tested_price is not None
            and current_dec is not None
            and cost_dec is not None
            and tested_price > cost_dec
            and abs(tested_price - current_dec) > Decimal("0.25")
            and tested_evidence_price is not None
        )
        row["sale_price_locked"] = sale_locked
        row["price_control_scope"] = "COMPANY_CONTROLLED" if sale_locked else "STORE_CONTROLLED"
        row["reg_suggestion_price"] = (
            raw_target_candidate
            if reason_code == "PAIR_FIX" and raw_target_candidate is not None
            else (
                action_price
                if reason_code == "COMPANY_RANGE" and action_price is not None
                else (tested_price if proven_sweet_spot else None)
            )
        )
        row["reg_suggestion_actionable"] = bool(
            not sale_locked
            and not active_tpr
            and (
                (reason_code in {"PAIR_FIX", "COMPANY_RANGE"} and action_price is not None)
                or proven_sweet_spot
            )
        )
        row["reg_suggestion_reason"] = (
            "240/249 price equality correction"
            if reason_code == "PAIR_FIX"
            else (
                "Current regular/store price is outside the applicable Company A/B/C range"
                if reason_code == "COMPANY_RANGE"
                else (
                    "A stronger proved sweet spot is available; replace the current regular/store price"
                    if proven_sweet_spot
                    else None
                )
            )
        )
        row["tpr_suggestion_actionable"] = bool(
            not sale_locked
            and not active_tpr
            and testing_price is not None
            and reason_code in {"VELOCITY_TEST", "SWEET_SPOT_GAP", "GP_DOLLAR_TEST"}
            and not proven_sweet_spot
        )
        row["tpr_suggestion_purpose"] = (
            "FRESHNESS_SELL_THROUGH"
            if reason_code == "VELOCITY_TEST"
            else (
                "SWEET_SPOT_TEST"
                if reason_code in {"SWEET_SPOT_GAP", "GP_DOLLAR_TEST"}
                else None
            )
        )
        row["tpr_suggestion_reason"] = (
            "Temporarily reduce price to improve velocity before the freshness threshold"
            if reason_code == "VELOCITY_TEST"
            else (
                "Run a controlled TPR test to search for a stronger everyday GP$/day sweet spot"
                if reason_code in {"SWEET_SPOT_GAP", "GP_DOLLAR_TEST"}
                else None
            )
        )
        row["price_tab_policy"] = (
            "SALE_LOCKED"
            if sale_locked
            else (
                "CURRENT_TPR_PROGRESS"
                if active_tpr
                else (
                    "REG_REPLACEMENT"
                    if row["reg_suggestion_actionable"]
                    else (
                        "TPR_SUGGESTION"
                        if row["tpr_suggestion_actionable"]
                        else "NO_ACTION"
                    )
                )
            )
        )

        row["current_price_gp_pct"] = _gp_pct_for_price(current_dec, cost_dec)
        row["tested_price_gp_pct"] = _gp_pct_for_price(tested_price, cost_dec)
        row["testing_price_gp_pct"] = _gp_pct_for_price(testing_price, cost_dec)
        row["target_sweet_spot_gp_pct"] = _gp_pct_for_price(target_candidate, cost_dec)

        row["candidate_price"] = action_price
        row["suggested_price"] = action_price
        row["suggestion_reason_code"] = reason_code
        row["suggestion_reason"] = reason_text
        row["actionable"] = action_price is not None
        row["review_status"] = "ACTIONABLE" if action_price is not None else "NO_PRICE_ACTION"

        if action_price is not None and cost_dec is not None and _d(action_price) > 0:
            row["suggested_gp_pct_at_current_cost"] = (
                (_d(action_price) - cost_dec) / _d(action_price)
            )
        else:
            row["suggested_gp_pct_at_current_cost"] = None

        if current_dec is not None and action_price is not None:
            row["price_gap_pct"] = (
                abs(_d(action_price) - current_dec)
                / current_dec
                * Decimal("100")
            )
            row["direction"] = (
                "INCREASE"
                if _d(action_price) > current_dec
                else ("DECREASE" if _d(action_price) < current_dec else "KEEP")
            )
        else:
            row["price_gap_pct"] = None
            row["direction"] = "REVIEW"

        if reason_code == "PAIR_FIX":
            row["primary_reason_text"] = "240/249 price equality correction"
        elif reason_code == "COMPANY_RANGE":
            row["primary_reason_text"] = "Current price is outside the applicable Company A/B/C range"
        elif reason_code == "VELOCITY_TEST":
            row["primary_reason_text"] = "Slow movement / freshness risk: test a small price reduction and re-check velocity"
        elif reason_code == "SWEET_SPOT_GAP":
            row["primary_reason_text"] = "Current price is more than $0.25 from the strongest proved sweet spot; move gradually"
        elif reason_code == "GP_DOLLAR_TEST":
            row["primary_reason_text"] = "Observed price history indicates potential GP$/day improvement; test one small step"

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

    reason_counts={}
    for row in visible_rows:
        code=str(row.get("suggestion_reason_code") or "NO_PRICE_ACTION")
        reason_counts[code]=reason_counts.get(code,0)+1
    actionable_count=sum(1 for row in visible_rows if row.get("actionable"))

    return {
        "contract_version": "BACKOFFICE_PRICING_REVIEW_V11_REG_TPR_SPLIT",
        "category": report.get("category"),
        "report_date": report.get("report_date"),
        "summary": {
            **(report.get("summary") or {}),
            "pricing_review_actionable_count": actionable_count,
            "pricing_review_visible_count": len(visible_rows),
            "pricing_review_reason_counts": reason_counts,
            "reg_suggestion_count": sum(1 for row in visible_rows if row.get("reg_suggestion_actionable")),
            "tpr_suggestion_count": sum(1 for row in visible_rows if row.get("tpr_suggestion_actionable")),
            "sale_locked_count": sum(1 for row in visible_rows if row.get("sale_price_locked")),
        },
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
            "estimate_basis": "LATEST_AVAILABLE_CANONICAL_POS_AND_MVT_INDEPENDENT",
            "estimate_is_clearly_labelled": True,
            "tested_price": "RETAIL_ALIGNED_TO_NEAREST_STORE_ENDING_FROM_STRONGEST_PROVED_HISTORICAL_SWEET_SPOT;RAW_EVIDENCE_PRESERVED",
            "testing_price": "CURRENT_PRICE_BASED_CONTROLLED_STEP; MIN_ABSOLUTE_CHANGE_0_45; PRIORITIZE_FRESHNESS_VELOCITY_WHEN_SLOW; OTHERWISE_STEP_TOWARD_TESTED_OR_GP_DOLLAR_TARGET; HIGHER_PRICE_GRADUAL_CAP_ABOUT_5PCT",
            "price_tabs": "REG_REPLACEMENT_FROM_PROVED_SWEET_SPOT; TPR_SUGGESTIONS_FOR_CONTROLLED_SWEET_SPOT_OR_FRESHNESS_TESTS; CURRENT_TPR_PROGRESS; CLEARANCE_USER_ENTERED_EXPIRY_PLAN",
            "sale_policy": "SALE_PRICE_AND_PERIOD_ARE_COMPANY_CONTROLLED_AND_EXCLUDED_FROM_STORE_PRICE_SUGGESTIONS",
            "reg_policy": "REG_IS_STANDARD_EVERYDAY_PRICE_AND_SHOULD_BE_THE_KNOWN_GP_DOLLAR_PER_DAY_SWEET_SPOT",
            "tpr_policy": "TPR_IS_TEMPORARY_FOR_SWEET_SPOT_TESTING_OR_FRESHNESS_SELL_THROUGH",
            "clearance_policy": "CLEARANCE_IS_FOR_USER_IDENTIFIED_EXPIRING_QUANTITY_AND_IS_MANAGED_BY_THE_CLEARANCE_PLAN",
            "price_action_priority": "PAIR_FIX_THEN_COMPANY_RANGE_THEN_REG_PROVED_SWEET_SPOT_THEN_TPR_FRESHNESS_OR_SWEET_SPOT_TEST",
            "source_contract": report.get("price_suggestion_rules"),
        },
    }




def _ensure_tpr_purpose_table(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS yipman_tpr_purpose (
             ean_upc VARCHAR(32) NOT NULL PRIMARY KEY,
             tpr_start_date DATE NOT NULL,
             purpose VARCHAR(40) NOT NULL,
             set_by VARCHAR(128) NULL,
             note VARCHAR(500) NULL,
             updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
               ON UPDATE CURRENT_TIMESTAMP(6),
             KEY idx_yipman_tpr_purpose_start (tpr_start_date)
           )"""
    )


def _bulk_tpr_price_list_lifecycle(
    cur,
    rows: list[dict[str, Any]],
    live_prices: dict[int, dict[str, Any] | None],
) -> dict[int, dict[str, Any]]:
    """Resolve the continuous active TPR lifecycle from Price List history.

    A new Price List upload must not reset TPR age. Consecutive Price List
    observations remain one TPR lifecycle until a non-TPR observation appears.
    Price changes inside TPR create a new price step but stay in the same TPR.
    """
    targets = {
        int(r["upc_id"]): str(r.get("ean_upc") or "").strip()
        for r in rows
        if r.get("upc_id") is not None
    }
    if not targets:
        return {}

    cur.execute(
        """SELECT file_id,upload_timestamp,report_generated_at
           FROM ingest_file
           WHERE source_type='price_list'
             AND processing_status='INGESTED'
             AND error_count=0
             AND duplicate_of_file_id IS NULL
           ORDER BY COALESCE(upload_timestamp,report_generated_at) DESC,file_id DESC
           LIMIT 120"""
    )
    price_files = [dict(x) for x in cur.fetchall()]
    if not price_files:
        return {}

    file_meta = {int(x["file_id"]): x for x in price_files}
    file_ids = list(file_meta)
    ph = ",".join(["%s"] * len(file_ids))
    cur.execute(
        f"""SELECT p.file_id,p.upc_id,p.ean_upc,p.configured_price,p.price_type,
                   p.source_since_date,p.snapshot_at,f.upload_timestamp
            FROM price_list_observation p
            JOIN ingest_file f ON f.file_id=p.file_id
            WHERE p.file_id IN ({ph})
              AND p.configured_price>0
              AND (p.source_since_date IS NULL OR p.source_since_date<=%s)
            ORDER BY p.file_id DESC,p.source_row_number""",
        (*file_ids, business_today()),
    )
    raw = [dict(x) for x in cur.fetchall()]

    exact: dict[str, int] = {}
    numeric: dict[str, int] = {}
    for uid, ean in targets.items():
        if ean:
            exact[ean] = uid
            key = _numeric_key(ean)
            if key and key not in numeric:
                numeric[key] = uid

    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for obs in raw:
        uid = None
        if obs.get("upc_id") is not None:
            try:
                candidate = int(obs["upc_id"])
            except Exception:
                candidate = None
            if candidate in targets:
                uid = candidate
        if uid is None:
            ean = str(obs.get("ean_upc") or "").strip()
            uid = exact.get(ean)
            if uid is None:
                uid = numeric.get(_numeric_key(ean))
        if uid is None:
            continue
        grouped.setdefault((uid, int(obs["file_id"])), []).append(obs)

    snapshots: dict[int, list[dict[str, Any]]] = {}
    for (uid, file_id), candidates in grouped.items():
        candidates.sort(
            key=lambda x: PRICE_TYPE_PRIORITY.get(
                str(x.get("price_type") or "").upper(), 0
            ),
            reverse=True,
        )
        chosen = dict(candidates[0])
        fm = file_meta.get(file_id) or {}
        uploaded = chosen.get("upload_timestamp") or fm.get("upload_timestamp")
        file_day = (
            _price_list_upload_business_date(uploaded)
            if uploaded is not None else None
        )
        if file_day is None and chosen.get("snapshot_at") is not None:
            try:
                file_day = chosen["snapshot_at"].date()
            except Exception:
                file_day = None
        chosen["file_business_date"] = file_day
        snapshots.setdefault(uid, []).append(chosen)

    out: dict[int, dict[str, Any]] = {}
    for uid, states in snapshots.items():
        states.sort(
            key=lambda x: (
                x.get("file_business_date") or date.min,
                int(x.get("file_id") or 0),
            ),
            reverse=True,
        )
        live = live_prices.get(uid) or {}
        if str(live.get("type") or "").upper() != "TPR":
            continue

        current_price = _positive_price(live.get("price"))
        lifecycle_dates: list[date] = []
        current_step_dates: list[date] = []
        history: list[dict[str, Any]] = []
        in_current_step = True
        started = False

        for state in states:
            ptype = str(state.get("price_type") or "").upper()
            if not started:
                if ptype != "TPR":
                    break
                started = True
            elif ptype != "TPR":
                break

            p = _positive_price(state.get("configured_price"))
            fd = state.get("file_business_date")
            sd = state.get("source_since_date")
            if isinstance(fd, date):
                lifecycle_dates.append(fd)
            if isinstance(sd, date):
                lifecycle_dates.append(sd)

            same_current = bool(
                current_price is not None
                and p is not None
                and abs(p - current_price) <= Decimal("0.011")
            )
            if in_current_step and same_current:
                if isinstance(fd, date):
                    current_step_dates.append(fd)
                if isinstance(sd, date):
                    current_step_dates.append(sd)
            else:
                in_current_step = False

            history.append({
                "file_id": state.get("file_id"),
                "date": fd,
                "source_since_date": sd,
                "price": p,
                "price_type": ptype,
            })

        if not started:
            continue

        # Compress identical adjacent configured TPR price snapshots so the app
        # shows actual price steps rather than every upload.
        compressed: list[dict[str, Any]] = []
        for event in reversed(history):
            if (
                compressed
                and compressed[-1].get("price") is not None
                and event.get("price") is not None
                and abs(_d(compressed[-1]["price"]) - _d(event["price"])) <= Decimal("0.011")
            ):
                compressed[-1]["end_date"] = event.get("date")
                compressed[-1]["last_file_id"] = event.get("file_id")
            else:
                compressed.append({
                    "start_date": event.get("source_since_date") or event.get("date"),
                    "end_date": event.get("date"),
                    "price": event.get("price"),
                    "price_type": "TPR",
                    "first_file_id": event.get("file_id"),
                    "last_file_id": event.get("file_id"),
                })

        out[uid] = {
            "tpr_start_date": min(lifecycle_dates) if lifecycle_dates else None,
            "current_price_step_start_date": (
                min(current_step_dates) if current_step_dates else None
            ),
            "configured_tpr_price_steps": compressed[-8:],
        }
    return out


def _tpr_pos_run_start(
    by_day: dict[date, dict[str, Any]],
    data_days: list[dict[str, Any]],
) -> date | None:
    """Find the current contiguous TPR selling run from POS evidence.

    Zero-sale supported days do not break continuity. A later non-TPR sold day
    does break it, preventing an old TPR campaign from being reused.
    """
    ordered = sorted(data_days, key=lambda x: x["date"], reverse=True)
    latest_sold_type_is_tpr = False
    latest_sold_found = False
    for entry in ordered:
        obs = by_day.get(entry["date"], {})
        total = _d(obs.get("sold_quantity"))
        if total == 0:
            continue
        latest_sold_found = True
        tpr = (obs.get("price_types") or {}).get("TPR") or {}
        tpr_qty = _d(tpr.get("sold_quantity"))
        latest_sold_type_is_tpr = tpr_qty > 0
        break
    if not latest_sold_found or not latest_sold_type_is_tpr:
        return None

    start = None
    seen_tpr = False
    for entry in ordered:
        day = entry["date"]
        obs = by_day.get(day, {})
        total = _d(obs.get("sold_quantity"))
        tpr = (obs.get("price_types") or {}).get("TPR") or {}
        tpr_qty = _d(tpr.get("sold_quantity"))
        non_tpr_qty = total - tpr_qty
        if tpr_qty > 0:
            seen_tpr = True
            start = day
            continue
        if total == 0:
            continue
        if seen_tpr and non_tpr_qty > 0:
            break
    return start


def _tpr_price_behavior_segments(
    by_day: dict[date, dict[str, Any]],
    data_days: list[dict[str, Any]],
    *,
    tpr_start_date: date | None,
    current_cost: Decimal | None,
) -> list[dict[str, Any]]:
    """Summarize prior/current TPR price steps using observed POS response."""
    segments: list[dict[str, Any]] = []
    for entry in sorted(data_days, key=lambda x: x["date"]):
        day = entry["date"]
        if tpr_start_date is not None and day < tpr_start_date:
            continue
        obs = by_day.get(day, {})
        tpr = (obs.get("price_types") or {}).get("TPR") or {}
        qty = _d(tpr.get("sold_quantity"))
        sales = _d(tpr.get("sales_amount"))
        if qty <= 0:
            continue
        price = (sales / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if segments and abs(_d(segments[-1]["price"]) - price) <= Decimal("0.011"):
            seg = segments[-1]
            seg["end_date"] = day
            seg["qty"] += qty
            seg["sales"] += sales
            seg["selling_days"] += 1
        else:
            segments.append({
                "start_date": day,
                "end_date": day,
                "price": price,
                "qty": qty,
                "sales": sales,
                "selling_days": 1,
            })
    for seg in segments:
        n = Decimal(max(1, int(seg["selling_days"])))
        seg["velocity_per_selling_day"] = seg["qty"] / n
        seg["gp_per_selling_day_current_cost"] = (
            (seg["sales"] - seg["qty"] * current_cost) / n
            if current_cost is not None else None
        )
    return segments[-6:]


def _auto_tpr_purpose(
    product_class: str,
    doh: Decimal | None,
    dos: Decimal | None,
    current_oh: Decimal | None,
) -> tuple[str, str]:
    pclass = str(product_class or "").upper()
    has_stock = current_oh is None or current_oh > 0
    if pclass in {"FRESH", "LIVE"} and has_stock and (
        (doh is not None and doh >= Decimal("5"))
        or (dos is not None and dos >= Decimal("7"))
    ):
        return "FRESHNESS_SELL_THROUGH", "AUTO_FRESHNESS_RISK"
    if pclass == "FROZEN" and has_stock and doh is not None and doh >= Decimal("60"):
        return "FRESHNESS_SELL_THROUGH", "AUTO_FROZEN_AGE_RISK"
    return "SWEET_SPOT_TEST", "AUTO_SWEET_SPOT"


def set_current_tpr_purpose(
    *,
    ean_upc: str,
    tpr_start_date: date,
    purpose: str,
    actor: str | None,
    note: str | None = None,
) -> dict[str, Any]:
    upc = str(ean_upc or "").strip()
    if not upc:
        raise ValueError("UPC_REQUIRED")
    p = str(purpose or "").strip().upper()
    if p not in {"SWEET_SPOT_TEST", "FRESHNESS_SELL_THROUGH"}:
        raise ValueError("TPR_PURPOSE_MUST_BE_SWEET_SPOT_TEST_OR_FRESHNESS_SELL_THROUGH")
    if tpr_start_date is None:
        raise ValueError("TPR_START_DATE_REQUIRED")
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        _ensure_tpr_purpose_table(cur)
        cur.execute(
            """INSERT INTO yipman_tpr_purpose
                 (ean_upc,tpr_start_date,purpose,set_by,note)
               VALUES (%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 tpr_start_date=VALUES(tpr_start_date),
                 purpose=VALUES(purpose),
                 set_by=VALUES(set_by),
                 note=VALUES(note),
                 updated_at=CURRENT_TIMESTAMP(6)""",
            (upc, tpr_start_date, p, actor, (str(note)[:500] if note else None)),
        )
        conn.commit()
        cur.close()

    # Purpose is part of the recommendation contract. Drop persisted/in-memory
    # Current TPR snapshots so the next read cannot serve the old purpose.
    try:
        with _TPR_REVIEW_CACHE_LOCK:
            _TPR_REVIEW_CACHE_VALUES.clear()
            _TPR_REVIEW_CACHE_AT.clear()
        with db_conn() as conn:
            cur = conn.cursor(dictionary=True)
            _ensure_tpr_review_cache_table(cur)
            cur.execute("DELETE FROM yipman_current_tpr_review_cache")
            conn.commit()
            cur.close()
    except Exception:
        pass
    return {
        "status": "SAVED",
        "upc": upc,
        "tpr_start_date": tpr_start_date,
        "purpose": p,
        "set_by": actor,
    }


def current_tpr_review(
    category: str = "ALL",
    limit: int = 1000,
) -> dict[str, Any]:
    """Monitor every active TPR as a lifecycle, not a single Price List upload.

    Every TPR has one of two operational purposes:
      * SWEET_SPOT_TEST: learn whether the TPR price should become the new REG;
      * FRESHNESS_SELL_THROUGH: reduce price only to clear aging inventory.

    The monitor compares pre-TPR behavior, current response, prior TPR price
    steps and forward inventory/GP projections, then recommends continue,
    change TPR price, make the TPR price regular, or cancel the TPR.
    """
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "LIVE", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")
    lim = max(1, min(int(limit or 1000), 2000))

    def _pct_lift(now: Decimal | None, base: Decimal | None) -> Decimal | None:
        if now is None or base is None or base == 0:
            return None
        return ((now - base) / abs(base) * Decimal("100")).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    def _as_date(value: Any) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except Exception:
            return None

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        data_days = source_data_days(
            cur,
            "sales_by_price_type",
            limit=90,
            up_to=completed_through_date(),
        )
        data_days = sorted(data_days, key=lambda x: x["date"])

        cur.execute("SELECT * FROM quick_check_current")
        all_rows = [dict(x) for x in cur.fetchall()]
        _overlay_active_true_stock_effective_oh(cur,all_rows)
        live_prices = _bulk_live_current_prices(cur, all_rows)

        for row in all_rows:
            uid = int(row["upc_id"]) if row.get("upc_id") is not None else None
            live = live_prices.get(uid) if uid is not None else None
            if live:
                row["current_price"] = live.get("price")
                row["current_price_type"] = live.get("type")
                row["current_price_source"] = live.get("source")
                row["current_price_asof_date"] = live.get("date")
                row["current_price_source_since_date"] = live.get("source_since_date")
                row["current_price_list_file_id"] = live.get("price_list_file_id")
            else:
                row["current_price"] = None
                row["current_price_type"] = None
                row["current_price_source"] = "STALE_OR_MISSING_FRESH_PRICE"
                row["current_price_asof_date"] = None
                row["current_price_source_since_date"] = None
                row["current_price_list_file_id"] = None

        pair_groups: dict[tuple[int, str], dict[str, dict[str, Any]]] = {}
        for row in all_rows:
            sig = _seafood_upc_group_signature(
                row.get("family_id"), row.get("ean_upc")
            )
            prefix = _numeric_key(row.get("ean_upc"))[:3]
            if sig is not None and prefix in {"240", "249"}:
                pair_groups.setdefault(sig, {})[prefix] = row

        tpr_rows = [
            row for row in all_rows
            if str(row.get("current_price_type") or "").upper() == "TPR"
            and (
                cat == "ALL"
                or str(row.get("product_class") or "").upper() == cat
            )
        ]
        price_lifecycle = _bulk_tpr_price_list_lifecycle(
            cur, tpr_rows, live_prices
        )
        daily = _batch_daily_sales_by_price_type(cur, tpr_rows, data_days)

        _ensure_tpr_purpose_table(cur)
        conn.commit()
        cur.execute(
            """SELECT ean_upc,tpr_start_date,purpose,set_by,note,updated_at
               FROM yipman_tpr_purpose"""
        )
        purpose_rows = [dict(x) for x in cur.fetchall()]
        purpose_by_upc = {
            str(x.get("ean_upc") or "").strip(): x
            for x in purpose_rows
            if x.get("ean_upc")
        }
        cur.close()

    out: list[dict[str, Any]] = []
    for row in tpr_rows:
        if row.get("upc_id") is None:
            continue
        uid = int(row["upc_id"])
        upc = str(row.get("ean_upc") or "")
        pclass = str(row.get("product_class") or "").upper()
        current_price = _positive_price(row.get("current_price"))
        current_cost = _positive_price(row.get("current_cost_per_selling_unit"))
        current_oh = (
            _d(row.get("current_oh"))
            if row.get("current_oh") is not None
            else None
        )
        doh = _d(row.get("doh")) if row.get("doh") is not None else None
        dos = _d(row.get("dos")) if row.get("dos") is not None else None
        by_day = daily.get(uid, {})

        pl_life = price_lifecycle.get(uid) or {}
        source_since = _as_date(row.get("current_price_source_since_date"))
        pl_start = _as_date(pl_life.get("tpr_start_date"))
        pos_start = _tpr_pos_run_start(by_day, data_days)
        fallback_start = _as_date(row.get("current_price_asof_date"))
        start_candidates = [
            x for x in (source_since, pl_start, pos_start)
            if x is not None and x <= business_today()
        ]
        tpr_start_day = min(start_candidates) if start_candidates else fallback_start
        if tpr_start_day is None and data_days:
            tpr_start_day = data_days[-1]["date"]

        start_basis_parts = []
        if source_since is not None:
            start_basis_parts.append("PRICE_LIST_SOURCE_SINCE")
        if pl_start is not None:
            start_basis_parts.append("CONTINUOUS_PRICE_LIST_TPR")
        if pos_start is not None:
            start_basis_parts.append("CONTIGUOUS_POS_TPR")
        tpr_start_basis = "+".join(start_basis_parts) or "CURRENT_PRICE_ASOF_FALLBACK"

        # Latest three completed canonical data days since the continuous TPR
        # began. New Price List uploads do not change this boundary.
        post_pool = [
            x for x in data_days
            if tpr_start_day is None or x["date"] >= tpr_start_day
        ]
        post_days = post_pool[-3:]

        tpr_qty_3d = Decimal("0")
        tpr_sales_3d = Decimal("0")
        item_qty_3d = Decimal("0")
        item_sales_3d = Decimal("0")
        tpr_selling_days_3d = 0
        item_selling_days_3d = 0
        for day_entry in post_days:
            obs = by_day.get(day_entry["date"], {})
            item_qty = _d(obs.get("sold_quantity"))
            item_sales = _d(obs.get("sales_amount"))
            item_qty_3d += item_qty
            item_sales_3d += item_sales
            if item_qty != 0:
                item_selling_days_3d += 1
            tpr_obs = (obs.get("price_types") or {}).get("TPR") or {}
            tq = _d(tpr_obs.get("sold_quantity"))
            ts = _d(tpr_obs.get("sales_amount"))
            tpr_qty_3d += tq
            tpr_sales_3d += ts
            if tq != 0:
                tpr_selling_days_3d += 1

        post_n = len(post_days)
        tpr_velocity_3d = (
            tpr_qty_3d / Decimal(post_n) if post_n else None
        )
        item_velocity_3d = (
            item_qty_3d / Decimal(post_n) if post_n else None
        )

        # Previous behavior is strictly BEFORE the continuous current TPR.
        # SALE and earlier TPR selling days are excluded from the normal
        # baseline so a promotion is never mislabeled as regular behavior.
        baseline_candidates = [
            x for x in data_days
            if tpr_start_day is None or x["date"] < tpr_start_day
        ]
        baseline_days: list[dict[str, Any]] = []
        for day_entry in reversed(baseline_candidates):
            obs = by_day.get(day_entry["date"], {})
            types = obs.get("price_types") or {}
            promo_qty = _d((types.get("TPR") or {}).get("sold_quantity"))
            promo_qty += _d((types.get("SALE") or {}).get("sold_quantity"))
            if promo_qty != 0:
                continue
            baseline_days.append(day_entry)
            if len(baseline_days) >= 7:
                break
        baseline_days = list(reversed(baseline_days))
        baseline_qty = sum(
            (_d(by_day.get(x["date"], {}).get("sold_quantity")) for x in baseline_days),
            Decimal("0"),
        )
        baseline_sales = sum(
            (_d(by_day.get(x["date"], {}).get("sales_amount")) for x in baseline_days),
            Decimal("0"),
        )
        baseline_n = len(baseline_days)
        baseline_velocity = (
            baseline_qty / Decimal(baseline_n) if baseline_n else None
        )
        baseline_avg_price = (
            baseline_sales / baseline_qty if baseline_qty > 0 else None
        )

        current_gp_pct = (
            ((current_price - current_cost) / current_price)
            if current_price is not None
            and current_cost is not None
            and current_price > 0
            else None
        )
        tpr_gp_dollars_3d = (
            tpr_sales_3d - (tpr_qty_3d * current_cost)
            if current_cost is not None
            else None
        )
        tpr_gp_per_day_3d = (
            tpr_gp_dollars_3d / Decimal(post_n)
            if tpr_gp_dollars_3d is not None and post_n
            else None
        )
        baseline_gp_per_day = (
            (baseline_sales - baseline_qty * current_cost) / Decimal(baseline_n)
            if current_cost is not None and baseline_n
            else None
        )
        velocity_lift_pct = _pct_lift(tpr_velocity_3d, baseline_velocity)
        gp_day_lift_pct = _pct_lift(tpr_gp_per_day_3d, baseline_gp_per_day)

        # TPR price-step behavior lets the user see whether a prior adjustment
        # helped before another change is recommended.
        behavior_steps = _tpr_price_behavior_segments(
            by_day,
            data_days,
            tpr_start_date=tpr_start_day,
            current_cost=current_cost,
        )
        previous_step = behavior_steps[-2] if len(behavior_steps) >= 2 else None
        current_step = behavior_steps[-1] if behavior_steps else None

        auto_purpose, auto_purpose_source = _auto_tpr_purpose(
            pclass, doh, dos, current_oh
        )
        saved_purpose = purpose_by_upc.get(upc)
        saved_start = _as_date(saved_purpose.get("tpr_start_date")) if saved_purpose else None
        # Preserve a user choice if the lifecycle was later corrected backwards.
        # Do not carry an old choice into a genuinely newer TPR lifecycle.
        saved_applies = bool(
            saved_purpose
            and saved_start is not None
            and tpr_start_day is not None
            and saved_start >= tpr_start_day
        )
        if saved_applies:
            tpr_purpose = str(saved_purpose.get("purpose") or "").upper()
            purpose_source = "USER_SET"
        else:
            tpr_purpose = auto_purpose
            purpose_source = auto_purpose_source

        freshness_threshold = (
            Decimal("7")
            if pclass in {"FRESH", "LIVE"}
            else (Decimal("60") if pclass == "FROZEN" else None)
        )
        freshness_days_remaining = (
            max(Decimal("0"), freshness_threshold - doh)
            if freshness_threshold is not None and doh is not None
            else None
        )
        required_velocity_to_clear = (
            current_oh / freshness_days_remaining
            if current_oh is not None
            and current_oh > 0
            and freshness_days_remaining is not None
            and freshness_days_remaining > 0
            else None
        )
        projected_days_to_clear = (
            current_oh / tpr_velocity_3d
            if current_oh is not None
            and current_oh > 0
            and tpr_velocity_3d is not None
            and tpr_velocity_3d > 0
            else None
        )
        projected_oh_at_freshness_limit = (
            max(
                Decimal("0"),
                current_oh - (
                    (tpr_velocity_3d or Decimal("0")) * freshness_days_remaining
                ),
            )
            if current_oh is not None
            and freshness_days_remaining is not None
            else None
        )
        projected_qty_7d = (
            tpr_velocity_3d * Decimal("7")
            if tpr_velocity_3d is not None else None
        )
        projected_gp_7d = (
            tpr_gp_per_day_3d * Decimal("7")
            if tpr_gp_per_day_3d is not None else None
        )
        baseline_projected_gp_7d = (
            baseline_gp_per_day * Decimal("7")
            if baseline_gp_per_day is not None else None
        )

        prefix = _numeric_key(upc)[:3]
        related_240 = None
        if prefix == "249":
            sig = _seafood_upc_group_signature(row.get("family_id"), upc)
            related_240 = (pair_groups.get(sig or (-1, "")) or {}).get("240")
        pair_mismatch = bool(
            related_240
            and related_240.get("current_price") is not None
            and current_price is not None
            and _d(related_240.get("current_price")) != current_price
        )

        company_values = [
            _positive_price(row.get(k))
            for k in ("company_price_a", "company_price_b", "company_price_c")
        ]
        company_values = [x for x in company_values if x is not None]
        company_low = min(company_values) if company_values else None
        company_high = max(company_values) if company_values else None
        price_floor = (
            max(
                current_cost + Decimal("0.01"),
                company_low if company_low is not None else current_cost + Decimal("0.01"),
            )
            if current_cost is not None else company_low
        )

        def _freshness_tpr_candidate() -> Decimal | None:
            raw = _freshness_velocity_target(
                current=current_price,
                current_cost=current_cost,
                current_velocity=tpr_velocity_3d,
                observed_candidates=None,
                company_low=company_low,
                company_high=company_high,
            )
            if raw is None or current_price is None:
                return None
            candidate = _next_testing_price(
                current_price,
                raw,
                min_price=price_floor,
                max_price=company_high,
            )
            if candidate is not None:
                return candidate
            # If the exploratory raw target snaps too close to Current, move to
            # the next meaningful store price point rather than publishing an
            # odd-cent TPR.
            fallback_target = current_price - max(
                Decimal("0.70"),
                current_price * Decimal("0.08"),
            )
            if price_floor is not None:
                fallback_target = max(fallback_target, price_floor)
            return _next_testing_price(
                current_price,
                fallback_target,
                min_price=price_floor,
                max_price=company_high,
            )

        recommendation_code = "OBSERVE"
        recommendation_label = "OBSERVE"
        recommendation_reason = "Wait for enough completed-day TPR evidence."
        recommendation_final = False
        recommendation_priority = 50
        suggested_tpr_price = None
        suggested_regular_price = None
        monitoring_phase = "LEARNING"
        readiness = str(row.get("quick_check_status") or "").upper()

        if readiness != "READY":
            recommendation_code = "REVIEW_DATA"
            recommendation_label = "REVIEW DATA"
            recommendation_reason = (
                "This TPR UPC is not READY for operational pricing review"
                + (
                    f": {row.get('blocking_reason')}"
                    if row.get("blocking_reason")
                    else "."
                )
            )
            recommendation_priority = 95
            monitoring_phase = "DATA_BLOCKED"
        elif pair_mismatch:
            recommendation_code = "MATCH_240"
            recommendation_label = "MATCH 240 NOW"
            recommendation_reason = (
                "249 TPR price must equal the paired 240 current price."
            )
            recommendation_final = True
            recommendation_priority = 100
            monitoring_phase = "ACTION"
            suggested_tpr_price = _positive_price(
                related_240.get("current_price") if related_240 else None
            )
        elif (
            current_price is None
            or current_cost is None
            or current_cost <= 0
        ):
            recommendation_code = "REVIEW_DATA"
            recommendation_label = "REVIEW DATA"
            recommendation_reason = (
                "Current TPR price or authoritative selling-unit cost is unresolved."
            )
            recommendation_priority = 95
            monitoring_phase = "DATA_BLOCKED"
        elif current_price <= current_cost:
            recommendation_code = "RAISE_TPR_PRICE"
            recommendation_label = "RAISE TPR"
            recommendation_reason = (
                "Current TPR is at or below cost; raise the TPR price immediately."
            )
            recommendation_final = True
            recommendation_priority = 100
            monitoring_phase = "ACTION"
            target = max(
                current_cost * Decimal("1.08"),
                baseline_avg_price or current_price * Decimal("1.10"),
            )
            suggested_tpr_price = _next_testing_price(
                current_price,
                target,
                min_price=price_floor,
                max_price=company_high,
            )
        elif current_oh is not None and current_oh <= 0:
            recommendation_code = "CANCEL_TPR"
            recommendation_label = "CANCEL TPR"
            recommendation_reason = (
                "No positive effective stock remains; the TPR no longer has an item to sell through or test."
            )
            recommendation_final = True
            recommendation_priority = 90
            monitoring_phase = "COMPLETE"
        elif tpr_purpose == "FRESHNESS_SELL_THROUGH":
            monitoring_phase = "SELL_THROUGH"
            overdue = (
                freshness_threshold is not None
                and doh is not None
                and doh > freshness_threshold
            )
            extreme_age = (
                freshness_threshold is not None
                and doh is not None
                and doh > freshness_threshold + Decimal("3")
            )

            if extreme_age:
                recommendation_code = "CANCEL_TPR"
                recommendation_label = "CANCEL / DISPOSITION"
                recommendation_reason = (
                    "Freshness threshold is more than three days past; stop treating this as a normal TPR and review disposition."
                )
                recommendation_final = True
                recommendation_priority = 100
                monitoring_phase = "FRESHNESS_LIMIT"
            elif overdue:
                recommendation_code = "LOWER_TPR_PRICE"
                recommendation_label = "LOWER TPR"
                recommendation_reason = (
                    "Freshness threshold has been reached and stock remains. Use a stronger last-chance sell-through price."
                )
                recommendation_final = True
                recommendation_priority = 95
                monitoring_phase = "LAST_CHANCE"
                suggested_tpr_price = _freshness_tpr_candidate()
            elif post_n < 1:
                recommendation_code = "OBSERVE"
                recommendation_label = "OBSERVE"
                recommendation_reason = (
                    "Freshness sell-through TPR has no completed POS day yet; monitor the first completed-day response."
                )
                recommendation_priority = 65
            elif tpr_qty_3d <= 0:
                recommendation_code = "LOWER_TPR_PRICE"
                recommendation_label = "LOWER TPR"
                recommendation_reason = (
                    "Freshness sell-through TPR has completed-day evidence but no TPR sales; lower the price while freshness time remains."
                )
                recommendation_final = True
                recommendation_priority = 90
                suggested_tpr_price = _freshness_tpr_candidate()
            elif (
                projected_days_to_clear is not None
                and freshness_days_remaining is not None
                and freshness_days_remaining > 0
                and projected_days_to_clear <= freshness_days_remaining
            ):
                recommendation_code = "CONTINUE_TPR"
                recommendation_label = "CONTINUE"
                recommendation_reason = (
                    "Current TPR velocity is on pace to clear effective OH before the freshness threshold."
                )
                recommendation_final = True
                recommendation_priority = 25
                monitoring_phase = "ON_PACE"
            elif (
                required_velocity_to_clear is not None
                and tpr_velocity_3d is not None
                and tpr_velocity_3d < required_velocity_to_clear
            ):
                recommendation_code = "LOWER_TPR_PRICE"
                recommendation_label = "LOWER TPR"
                recommendation_reason = (
                    "Current TPR velocity is below the sell-through rate required to clear OH before the freshness threshold."
                )
                recommendation_final = True
                recommendation_priority = 85
                monitoring_phase = "BEHIND_PACE"
                suggested_tpr_price = _freshness_tpr_candidate()
            else:
                recommendation_code = "CONTINUE_TPR"
                recommendation_label = "CONTINUE"
                recommendation_reason = (
                    "Continue the freshness sell-through TPR and reassess after the next completed POS day."
                )
                recommendation_priority = 35
        else:
            # SWEET_SPOT_TEST: objective is to learn a sustainable new REG price,
            # not merely create short-term unit lift.
            if post_n < 2 or tpr_selling_days_3d < 1:
                recommendation_code = "OBSERVE"
                recommendation_label = "OBSERVE"
                recommendation_reason = (
                    "Sweet-spot TPR needs at least two completed data days with TPR response before changing course."
                )
                recommendation_priority = 60
            elif baseline_n < 3 or baseline_velocity is None or baseline_velocity <= 0:
                recommendation_code = "OBSERVE"
                recommendation_label = "OBSERVE"
                recommendation_reason = (
                    "Sweet-spot TPR is active, but fewer than three clean pre-TPR baseline days are available."
                )
                recommendation_priority = 55
            else:
                v_lift = (
                    velocity_lift_pct
                    if velocity_lift_pct is not None else Decimal("0")
                )
                g_lift = gp_day_lift_pct

                if (
                    post_n >= 3
                    and tpr_selling_days_3d >= 2
                    and g_lift is not None
                    and g_lift >= Decimal("5")
                    and v_lift >= Decimal("-5")
                ):
                    recommendation_code = "MAKE_REGULAR"
                    recommendation_label = "MAKE REGULAR"
                    recommendation_reason = (
                        "The current TPR price is producing a stronger GP$/day result without materially weakening velocity; promote it as the new regular-price sweet spot."
                    )
                    recommendation_final = True
                    recommendation_priority = 30
                    monitoring_phase = "PROVEN_SWEET_SPOT"
                    suggested_regular_price = current_price
                elif v_lift >= Decimal("15") and (
                    g_lift is None or g_lift >= Decimal("-10")
                ):
                    recommendation_code = "CONTINUE_TPR"
                    recommendation_label = "CONTINUE"
                    recommendation_reason = (
                        "Velocity response is strong and GP$/day is acceptable; continue the TPR test to confirm a durable sweet spot."
                    )
                    recommendation_priority = 25
                    monitoring_phase = "PROMISING"
                elif v_lift >= Decimal("10") and g_lift is not None and g_lift < Decimal("-10"):
                    recommendation_code = "RAISE_TPR_PRICE"
                    recommendation_label = "RAISE TPR"
                    recommendation_reason = (
                        "The TPR is buying velocity at too much GP$/day cost; test a higher TPR price."
                    )
                    recommendation_final = True
                    recommendation_priority = 80
                    monitoring_phase = "ACTION"
                    target = max(
                        baseline_avg_price or Decimal("0"),
                        current_price * Decimal("1.10"),
                    )
                    suggested_tpr_price = _next_testing_price(
                        current_price,
                        target,
                        min_price=price_floor,
                        max_price=company_high,
                    )
                elif v_lift <= Decimal("0") and (
                    g_lift is None or g_lift <= Decimal("0")
                ):
                    recommendation_code = "CANCEL_TPR"
                    recommendation_label = "CANCEL TPR"
                    recommendation_reason = (
                        "The sweet-spot TPR is not improving velocity or GP$/day versus the clean pre-TPR baseline."
                    )
                    recommendation_final = True
                    recommendation_priority = 85
                    monitoring_phase = "FAILED_TEST"
                elif g_lift is not None and g_lift < Decimal("-15"):
                    recommendation_code = "RAISE_TPR_PRICE"
                    recommendation_label = "RAISE TPR"
                    recommendation_reason = (
                        "The TPR has some demand response but GP$/day is materially weaker; test a higher TPR price."
                    )
                    recommendation_final = True
                    recommendation_priority = 75
                    monitoring_phase = "ACTION"
                    target = max(
                        baseline_avg_price or Decimal("0"),
                        current_price * Decimal("1.10"),
                    )
                    suggested_tpr_price = _next_testing_price(
                        current_price,
                        target,
                        min_price=price_floor,
                        max_price=company_high,
                    )
                else:
                    recommendation_code = "CONTINUE_TPR"
                    recommendation_label = "CONTINUE"
                    recommendation_reason = (
                        "Response is mixed but not failed; keep the TPR test active and use the next completed POS day to decide."
                    )
                    recommendation_priority = 40
                    monitoring_phase = "LEARNING"

        out.append({
            "upc": upc,
            "family_id": row.get("family_id"),
            "family_article_number": row.get("main_article_number"),
            "name": row.get("selling_description"),
            "category": pclass or "OTHER",
            "selling_uom": row.get("selling_uom"),
            "tpr_purpose": tpr_purpose,
            "tpr_purpose_label": (
                "FIND NEW REGULAR SWEET SPOT"
                if tpr_purpose == "SWEET_SPOT_TEST"
                else "FRESHNESS SELL-THROUGH"
            ),
            "tpr_purpose_source": purpose_source,
            "tpr_purpose_set_by": (
                saved_purpose.get("set_by") if saved_applies and saved_purpose else None
            ),
            "tpr_start_date": tpr_start_day,
            "tpr_start_basis": tpr_start_basis,
            "current_tpr_price_step_start_date": (
                _as_date(pl_life.get("current_price_step_start_date"))
                or (current_step.get("start_date") if current_step else None)
            ),
            "configured_tpr_price_steps": pl_life.get("configured_tpr_price_steps") or [],
            "observed_tpr_price_steps": behavior_steps,
            "previous_tpr_step": previous_step,
            "current_tpr_step": current_step,
            "current_tpr_price": current_price,
            "current_price_type": "TPR",
            "current_price_source": row.get("current_price_source"),
            "current_price_asof_date": row.get("current_price_asof_date"),
            "current_price_source_since_date": row.get("current_price_source_since_date"),
            "current_cost": current_cost,
            "current_cost_source": row.get("cost_source"),
            "cost_date": row.get("cost_date"),
            "current_gp_pct": current_gp_pct,
            "current_oh": current_oh,
            "current_oh_uom": row.get("current_oh_uom"),
            "dos": dos,
            "doh": doh,
            "qty_7d": row.get("pos_qty_7d"),
            "velocity_7d": row.get("upc_velocity_7d"),
            "gp_per_day_7d": row.get("gp_per_day_7d"),
            "previous_behavior": {
                "window_start": min((x["date"] for x in baseline_days), default=None),
                "window_end": max((x["date"] for x in baseline_days), default=None),
                "supported_days": baseline_n,
                "qty": baseline_qty,
                "sales": baseline_sales,
                "avg_price": baseline_avg_price,
                "velocity": baseline_velocity,
                "gp_per_day_current_cost": baseline_gp_per_day,
            },
            "current_behavior": {
                "window_start": min((x["date"] for x in post_days), default=None),
                "window_end": max((x["date"] for x in post_days), default=None),
                "supported_days": post_n,
                "tpr_selling_days": tpr_selling_days_3d,
                "qty": tpr_qty_3d,
                "sales": tpr_sales_3d,
                "velocity": tpr_velocity_3d,
                "gp_per_day": tpr_gp_per_day_3d,
                "velocity_lift_pct": velocity_lift_pct,
                "gp_day_lift_pct": gp_day_lift_pct,
            },
            "future_behavior": {
                "projected_qty_7d": projected_qty_7d,
                "projected_gp_7d": projected_gp_7d,
                "baseline_projected_gp_7d": baseline_projected_gp_7d,
                "projected_days_to_clear_oh": projected_days_to_clear,
                "freshness_threshold_doh": freshness_threshold,
                "freshness_days_remaining": freshness_days_remaining,
                "required_velocity_to_clear": required_velocity_to_clear,
                "projected_oh_at_freshness_limit": projected_oh_at_freshness_limit,
            },
            "post_tpr_window_start": min(
                (x["date"] for x in post_days), default=None
            ),
            "post_tpr_window_end": max(
                (x["date"] for x in post_days), default=None
            ),
            "post_tpr_supported_day_count": post_n,
            "tpr_selling_days_3d": tpr_selling_days_3d,
            "tpr_qty_3d": tpr_qty_3d,
            "tpr_sales_3d": tpr_sales_3d,
            "tpr_avg_sold_price_3d": (
                tpr_sales_3d / tpr_qty_3d if tpr_qty_3d != 0 else None
            ),
            "tpr_velocity_3d": tpr_velocity_3d,
            "item_qty_3d": item_qty_3d,
            "item_sales_3d": item_sales_3d,
            "item_selling_days_3d": item_selling_days_3d,
            "item_velocity_3d": item_velocity_3d,
            "baseline_day_count": baseline_n,
            "baseline_window_start": min(
                (x["date"] for x in baseline_days), default=None
            ),
            "baseline_window_end": max(
                (x["date"] for x in baseline_days), default=None
            ),
            "baseline_qty": baseline_qty,
            "baseline_sales": baseline_sales,
            "baseline_avg_price": baseline_avg_price,
            "baseline_velocity": baseline_velocity,
            "velocity_lift_pct": velocity_lift_pct,
            "tpr_gp_dollars_3d": tpr_gp_dollars_3d,
            "tpr_gp_per_day_3d": tpr_gp_per_day_3d,
            "baseline_gp_per_day_current_cost": baseline_gp_per_day,
            "gp_day_lift_pct": gp_day_lift_pct,
            "freshness_threshold_doh": freshness_threshold,
            "freshness_days_remaining": freshness_days_remaining,
            "required_velocity_to_clear": required_velocity_to_clear,
            "projected_days_to_clear_oh": projected_days_to_clear,
            "projected_oh_at_freshness_limit": projected_oh_at_freshness_limit,
            "projected_qty_7d": projected_qty_7d,
            "projected_gp_7d": projected_gp_7d,
            "suggested_tpr_price": suggested_tpr_price,
            "suggested_regular_price": suggested_regular_price,
            "monitoring_phase": monitoring_phase,
            "related_240_upc": (
                related_240.get("ean_upc") if related_240 else None
            ),
            "related_240_current_price": (
                related_240.get("current_price") if related_240 else None
            ),
            "price_240_249_equal": (not pair_mismatch) if related_240 else None,
            "recommendation_code": recommendation_code,
            "recommendation_label": recommendation_label,
            "recommendation_reason": recommendation_reason,
            "recommendation_final": recommendation_final,
            "recommendation_priority": recommendation_priority,
            "readiness": row.get("quick_check_status"),
            "blocking_reason": row.get("blocking_reason"),
            "publish_batch_id": row.get("publish_batch_id"),
        })

    out.sort(
        key=lambda r: (
            -int(r.get("recommendation_priority") or 0),
            -float(r.get("qty_7d") or 0),
            str(r.get("name") or r.get("upc") or ""),
        )
    )
    out = out[:lim]
    counts = Counter(str(r.get("recommendation_code") or "OBSERVE") for r in out)
    purposes = Counter(str(r.get("tpr_purpose") or "") for r in out)
    return {
        "contract_version": "YIPMAN_CURRENT_TPR_REVIEW_V3_LIFECYCLE",
        "category": cat,
        "data_day_definition": "LATEST_COMPLETED_CANONICAL_POS_DATA_DAYS",
        "summary": {
            "current_tpr_count": len(out),
            "sold_7d_count": sum(1 for r in out if _d(r.get("qty_7d")) > 0),
            "upc_240_count": sum(
                1 for r in out if _numeric_key(r.get("upc"))[:3] == "240"
            ),
            "sweet_spot_test_count": purposes.get("SWEET_SPOT_TEST", 0),
            "freshness_sell_through_count": purposes.get("FRESHNESS_SELL_THROUGH", 0),
            "recommendation_counts": dict(counts),
        },
        "rows": out,
        "rules": {
            "current_tpr_membership": "AUTHORITATIVE_LIVE_CURRENT_PRICE_TYPE_EQUALS_TPR",
            "tpr_lifecycle_start": "PRICE_LIST_SOURCE_SINCE_PLUS_CONTINUOUS_TPR_PRICE_LIST_AND_CONTIGUOUS_POS_TPR;NEW_UPLOAD_DOES_NOT_RESET",
            "tpr_purposes": "SWEET_SPOT_TEST_OR_FRESHNESS_SELL_THROUGH",
            "sweet_spot_objective": "FIND_SUSTAINABLE_TPR_PRICE_THAT_CAN_BECOME_NEW_REGULAR_PRICE",
            "freshness_objective": "CLEAR_EFFECTIVE_OH_BEFORE_FRESHNESS_THRESHOLD_WITH_CONTROLLED_TPR_MARKDOWN",
            "post_tpr_window": "LATEST_3_COMPLETED_CANONICAL_POS_DAYS_SINCE_CONTINUOUS_TPR_START",
            "baseline": "UP_TO_7_CLEAN_PRE_TPR_NON_SALE_NON_TPR_COMPLETED_POS_DAYS",
            "monitoring": "PREVIOUS_BASELINE_PLUS_CURRENT_TPR_PRICE_STEPS_PLUS_FORWARD_7D_AND_FRESHNESS_CLEARANCE_PROJECTION",
            "actions": "CONTINUE_TPR_OR_CHANGE_TPR_PRICE_OR_MAKE_REGULAR_OR_CANCEL_TPR",
            "gp_comparison_basis": "CURRENT_COST_NORMALIZED_FOR_BOTH_TPR_AND_BASELINE",
            "hard_safety_priority": "240_249_MISMATCH_THEN_PRICE_AT_OR_BELOW_COST_THEN_NO_STOCK",
        },
    }


_TPR_REVIEW_CACHE_LOCK=threading.Lock()
_TPR_REVIEW_CACHE_VALUES: dict[str,dict[str,Any]]={}
_TPR_REVIEW_CACHE_AT: dict[str,float]={}
_TPR_REVIEW_REFRESHING: set[str]=set()
_TPR_REVIEW_LAST_ERROR: dict[str,str]={}
_TPR_REVIEW_CACHE_TTL_SECONDS=120.0


def _tpr_review_cache_key(category: str, limit: int) -> str:
    return f"V3_CURRENT_TPR_LIFECYCLE|{str(category or 'ALL').upper()}|{max(1,min(int(limit or 1000),2000))}"


def _ensure_tpr_review_cache_table(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS yipman_current_tpr_review_cache (
             cache_key VARCHAR(96) NOT NULL PRIMARY KEY,
             payload_json LONGTEXT NOT NULL,
             generated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
             ON UPDATE CURRENT_TIMESTAMP(6)
           )"""
    )


def _load_persisted_tpr_review(cache_key: str) -> dict[str,Any] | None:
    try:
        with db_conn() as conn:
            cur=conn.cursor(dictionary=True)
            _ensure_tpr_review_cache_table(cur)
            conn.commit()
            cur.execute(
                """SELECT payload_json,generated_at
                   FROM yipman_current_tpr_review_cache
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


def _persist_tpr_review(cache_key: str, value: dict[str,Any]) -> None:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tpr_review_cache_table(cur)
        cur.execute(
            """INSERT INTO yipman_current_tpr_review_cache(cache_key,payload_json)
               VALUES (%s,%s)
               ON DUPLICATE KEY UPDATE
                 payload_json=VALUES(payload_json),
                 generated_at=CURRENT_TIMESTAMP(6)""",
            (cache_key,json.dumps(value,default=str)),
        )
        conn.commit()
        cur.close()


def _tpr_review_refresh_worker(category: str, limit: int, cache_key: str) -> None:
    try:
        _TPR_REVIEW_LAST_ERROR.pop(cache_key,None)
        value=current_tpr_review(category=category,limit=limit)
        _persist_tpr_review(cache_key,value)
        with _TPR_REVIEW_CACHE_LOCK:
            _TPR_REVIEW_CACHE_VALUES[cache_key]=value
            _TPR_REVIEW_CACHE_AT[cache_key]=time.monotonic()
    except Exception as exc:
        _TPR_REVIEW_LAST_ERROR[cache_key]=f"{type(exc).__name__}: {exc}"[:1000]
    finally:
        with _TPR_REVIEW_CACHE_LOCK:
            _TPR_REVIEW_REFRESHING.discard(cache_key)


def _request_tpr_review_refresh(category: str, limit: int, cache_key: str) -> None:
    with _TPR_REVIEW_CACHE_LOCK:
        if cache_key in _TPR_REVIEW_REFRESHING:
            return
        _TPR_REVIEW_REFRESHING.add(cache_key)
    threading.Thread(
        target=_tpr_review_refresh_worker,
        args=(category,limit,cache_key),
        name=f"current-tpr-review-{str(category or 'ALL').lower()}",
        daemon=True,
    ).start()


def cached_current_tpr_review(
    category: str="ALL",
    limit: int=1000,
    force: bool=False,
) -> dict[str,Any]:
    """Serve Current TPR without blocking the request on the heavy calculation.

    The latest completed result is persisted and returned immediately while a
    background refresh runs. This mirrors Pricing Review's stale-while-refresh
    pattern so mobile requests are not tied to the calculation duration.
    """
    cat=str(category or "ALL").strip().upper()
    if cat not in {"ALL","LIVE","FRESH","FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")
    lim=max(1,min(int(limit or 1000),2000))
    key=_tpr_review_cache_key(cat,lim)

    with _TPR_REVIEW_CACHE_LOCK:
        cached=_TPR_REVIEW_CACHE_VALUES.get(key)
        cached_at=_TPR_REVIEW_CACHE_AT.get(key)
        already_refreshing=key in _TPR_REVIEW_REFRESHING

    if cached is None and not already_refreshing:
        persisted=_load_persisted_tpr_review(key)
        if persisted is not None:
            with _TPR_REVIEW_CACHE_LOCK:
                _TPR_REVIEW_CACHE_VALUES[key]=persisted
                _TPR_REVIEW_CACHE_AT[key]=0.0
            cached=persisted
            cached_at=0.0

    if cached is None:
        if not already_refreshing:
            _request_tpr_review_refresh(cat,lim,key)
        return {
            "contract_version":"YIPMAN_CURRENT_TPR_REVIEW_V4_LIFECYCLE_ASYNC_CACHE",
            "category":cat,
            "analysis_status":"REFRESHING",
            "cache_status":"WARMING",
            "refreshing":True,
            "refresh_error":_TPR_REVIEW_LAST_ERROR.get(key),
            "summary":{},
            "rows":[],
            "rules":{
                "serving":"NON_BLOCKING_PERSISTED_STALE_WHILE_REFRESH",
                "calculation":"CURRENT_TPR_REVIEW_V3_LIFECYCLE",
            },
        }

    age=(time.monotonic()-cached_at) if cached_at is not None else None
    stale=age is None or age>=_TPR_REVIEW_CACHE_TTL_SECONDS
    if force or stale:
        _request_tpr_review_refresh(cat,lim,key)
    with _TPR_REVIEW_CACHE_LOCK:
        refreshing=key in _TPR_REVIEW_REFRESHING

    return {
        **cached,
        "contract_version":"YIPMAN_CURRENT_TPR_REVIEW_V4_LIFECYCLE_ASYNC_CACHE",
        "analysis_status":"READY_STALE_REFRESHING" if stale else "READY",
        "cache_status":"STALE_REFRESHING" if stale else "HIT",
        "refreshing":refreshing,
        "refresh_error":_TPR_REVIEW_LAST_ERROR.get(key),
    }


_PRICING_REVIEW_CACHE_LOCK=threading.Lock()
_PRICING_REVIEW_CACHE_VALUES: dict[str,dict[str,Any]]={}
_PRICING_REVIEW_CACHE_AT: dict[str,float]={}
_PRICING_REVIEW_REFRESHING: set[str]=set()
_PRICING_REVIEW_LAST_ERROR: dict[str,str]={}
_PRICING_REVIEW_CACHE_TTL_SECONDS=120.0


def _pricing_review_cache_key(category: str, limit: int) -> str:
    # V3 invalidates persisted V2 snapshots that may contain an empty queue
    # produced by the older inherited-review-status gate.
    return f"V4_REG_TPR_SPLIT|{str(category or 'ALL').upper()}|{max(1,min(int(limit or 1000),1000))}"


def _ensure_pricing_review_cache_table(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS backoffice_pricing_review_cache (
             cache_key VARCHAR(96) NOT NULL PRIMARY KEY,
             payload_json LONGTEXT NOT NULL,
             generated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
             ON UPDATE CURRENT_TIMESTAMP(6)
           )"""
    )


def _load_persisted_pricing_review(cache_key: str) -> dict[str,Any] | None:
    try:
        with db_conn() as conn:
            cur=conn.cursor(dictionary=True)
            _ensure_pricing_review_cache_table(cur)
            conn.commit()
            cur.execute(
                """SELECT payload_json,generated_at
                   FROM backoffice_pricing_review_cache
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


def _persist_pricing_review(cache_key: str, value: dict[str,Any]) -> None:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_pricing_review_cache_table(cur)
        cur.execute(
            """INSERT INTO backoffice_pricing_review_cache(cache_key,payload_json)
               VALUES (%s,%s)
               ON DUPLICATE KEY UPDATE
                 payload_json=VALUES(payload_json),
                 generated_at=CURRENT_TIMESTAMP(6)""",
            (cache_key,json.dumps(value,default=str)),
        )
        conn.commit()
        cur.close()


def _pricing_review_refresh_worker(category: str, limit: int, cache_key: str) -> None:
    try:
        _PRICING_REVIEW_LAST_ERROR.pop(cache_key,None)
        value=pricing_review(
            category=category,
            limit=limit,
            allow_stale_estimate=True,
        )
        _persist_pricing_review(cache_key,value)
        with _PRICING_REVIEW_CACHE_LOCK:
            _PRICING_REVIEW_CACHE_VALUES[cache_key]=value
            _PRICING_REVIEW_CACHE_AT[cache_key]=time.monotonic()
    except Exception as exc:
        _PRICING_REVIEW_LAST_ERROR[cache_key]=f"{type(exc).__name__}: {exc}"[:1000]
    finally:
        with _PRICING_REVIEW_CACHE_LOCK:
            _PRICING_REVIEW_REFRESHING.discard(cache_key)


def _request_pricing_review_refresh(category: str, limit: int, cache_key: str) -> None:
    with _PRICING_REVIEW_CACHE_LOCK:
        if cache_key in _PRICING_REVIEW_REFRESHING:
            return
        _PRICING_REVIEW_REFRESHING.add(cache_key)
    threading.Thread(
        target=_pricing_review_refresh_worker,
        args=(category,limit,cache_key),
        name=f"pricing-review-{str(category or 'ALL').lower()}",
        daemon=True,
    ).start()


def cached_pricing_review(
    category: str="ALL",
    limit: int=1000,
    force: bool=False,
) -> dict[str,Any]:
    """Non-blocking Pricing Review with persistent stale-while-refresh cache."""
    cat=str(category or "ALL").strip().upper()
    if cat not in {"ALL","LIVE","FRESH","FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")
    lim=max(1,min(int(limit or 1000),1000))
    key=_pricing_review_cache_key(cat,lim)

    with _PRICING_REVIEW_CACHE_LOCK:
        cached=_PRICING_REVIEW_CACHE_VALUES.get(key)
        cached_at=_PRICING_REVIEW_CACHE_AT.get(key)
        already_refreshing=key in _PRICING_REVIEW_REFRESHING

    if cached is None and not already_refreshing:
        persisted=_load_persisted_pricing_review(key)
        if persisted is not None:
            with _PRICING_REVIEW_CACHE_LOCK:
                _PRICING_REVIEW_CACHE_VALUES[key]=persisted
                _PRICING_REVIEW_CACHE_AT[key]=0.0
            cached=persisted
            cached_at=0.0

    if cached is None:
        if not already_refreshing:
            _request_pricing_review_refresh(cat,lim,key)
        return {
            "contract_version":"BACKOFFICE_PRICING_REVIEW_V9_ASYNC_CACHE",
            "category":cat,
            "analysis_status":"REFRESHING",
            "cache_status":"WARMING",
            "refreshing":True,
            "refresh_error":_PRICING_REVIEW_LAST_ERROR.get(key),
            "rows":[],
            "suppressed_accepted_count":0,
            "data_health":{
                "status":"REFRESHING",
                "expected_through":completed_through_date(),
                "rule":"PRICING_ASYNC_CACHE_WARMING",
            },
        }

    live_health=_pricing_review_data_health(allow_stale_estimate=True)
    cached_health=dict((cached.get("data_health") or {}))
    source_changed=(
        str(cached_health.get("pos_data_through") or "")
        != str(live_health.get("pos_data_through") or "")
        or str(cached_health.get("movement_data_through") or "")
        != str(live_health.get("movement_data_through") or "")
    )
    age=(time.monotonic()-cached_at) if cached_at is not None else None
    stale=(
        source_changed
        or age is None
        or age>=_PRICING_REVIEW_CACHE_TTL_SECONDS
    )
    if force or stale:
        _request_pricing_review_refresh(cat,lim,key)
    with _PRICING_REVIEW_CACHE_LOCK:
        refreshing=key in _PRICING_REVIEW_REFRESHING

    return {
        **cached,
        "contract_version":"BACKOFFICE_PRICING_REVIEW_V10_SOURCE_AWARE_CACHE",
        "analysis_status":(
            "READY_SOURCE_CHANGED_REFRESHING"
            if source_changed else ("READY_STALE_REFRESHING" if stale else "READY")
        ),
        "cache_status":(
            "SOURCE_CHANGED_REFRESHING"
            if source_changed else ("STALE_REFRESHING" if stale else "HIT")
        ),
        "refreshing":refreshing,
        "refresh_error":_PRICING_REVIEW_LAST_ERROR.get(key),
        "current_source_health":live_health,
        "source_changed_since_analysis":source_changed,
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
