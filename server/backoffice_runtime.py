from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from business_clock import completed_through_date
from data_coverage import source_data_days
from db import db_conn
from webapp_v2_runtime import (
    _delivery_pattern,
    _family_effective_oh,
    _family_receipt_events,
    bulk_ordering_suggestions,
    performance_report,
)


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


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
        for kind in kinds:
            bulk = bulk_ordering_suggestions(kind)
            inputs[kind] = bulk.get("inputs")
            skipped.extend(bulk.get("skipped") or [])
            for s in bulk.get("suggestions") or []:
                fid = int(s["family_id"])
                receipt = _last_receipt_base_summary(cur, fid)
                events = _family_receipt_events(cur, fid)
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
    return {
        "contract_version": "BACKOFFICE_ORDERING_REVIEW_V1",
        "category": cat,
        "count": len(rows),
        "rows": rows,
        "skipped": skipped,
        "inputs": inputs,
        "rules": {
            "decision_level": "FAMILY_ARTICLE_AND_RECEIVING_ARTICLE",
            "selling_upcs_are_supporting_detail_only": True,
            "last_receipt_quantity_basis": "MOVEMENT_BASE_UOM_ONLY",
            "incoming_field_used": False,
            "write_enabled": False,
        },
    }


def inventory_review(limit: int = 200, category: str = "ALL") -> dict[str, Any]:
    cat = str(category or "ALL").strip().upper()
    if cat not in {"ALL", "LIVE", "FRESH", "FROZEN"}:
        raise ValueError("CATEGORY_MUST_BE_ALL_LIVE_FRESH_OR_FROZEN")
    limit = max(1, min(int(limit or 200), 500))

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        if cat == "ALL":
            cur.execute(
                """SELECT * FROM quick_check_current
                   ORDER BY COALESCE(pos_qty_7d,0) DESC,ean_upc
                   LIMIT %s""",
                (limit,),
            )
        else:
            cur.execute(
                """SELECT * FROM quick_check_current
                   WHERE UPPER(COALESCE(product_class,''))=%s
                   ORDER BY COALESCE(pos_qty_7d,0) DESC,ean_upc
                   LIMIT %s""",
                (cat, limit),
            )
        qrows = cur.fetchall()
        family_cache: dict[int, dict[str, Any]] = {}
        out = []
        for row in qrows:
            fid = int(row["family_id"]) if row.get("family_id") is not None else None
            if fid is not None and fid not in family_cache:
                cur.execute("SELECT * FROM quick_check_current WHERE family_id=%s ORDER BY ean_upc", (fid,))
                children = cur.fetchall()
                family_cache[fid] = _family_effective_oh(cur, children)
            family_oh = family_cache.get(fid or -1, {})
            out.append(
                {
                    "upc": row.get("ean_upc"),
                    "name": row.get("selling_description"),
                    "family_id": fid,
                    "family_article": row.get("main_article_number"),
                    "family_name": row.get("family_description"),
                    "article_number": row.get("article_number"),
                    "category": row.get("product_class"),
                    "readiness": row.get("quick_check_status"),
                    "selling_uom": row.get("selling_uom"),
                    "price": row.get("current_price"),
                    "cost": row.get("current_cost_per_selling_unit"),
                    "gp_pct": row.get("gp_pct_current"),
                    "qty_7d": row.get("pos_qty_7d"),
                    "dos": row.get("dos"),
                    "doh": row.get("doh"),
                    "family_oh": family_oh.get("quantity"),
                    "family_oh_uom": family_oh.get("uom"),
                    "family_oh_source": family_oh.get("source"),
                    "last_receipt_date": row.get("last_receipt_date"),
                    "price_type": row.get("current_price_type"),
                }
            )
        cur.close()

    return {
        "contract_version": "BACKOFFICE_INVENTORY_V1",
        "category": cat,
        "count": len(out),
        "rows": out,
        "rules": {"write_enabled": "OH_TRUE_STOCK_ONLY"},
    }


def pricing_review(category: str = "ALL", limit: int = 100) -> dict[str, Any]:
    report = performance_report(category=category, limit=limit)
    return {
        "contract_version": "BACKOFFICE_PRICING_REVIEW_V1",
        "category": report.get("category"),
        "report_date": report.get("report_date"),
        "summary": report.get("summary"),
        "rows": report.get("top_urgent_price_suggestions") or [],
        "rules": {
            "write_enabled": False,
            "price_changes_are_review_only": True,
            "source_contract": report.get("price_suggestion_rules"),
        },
    }
