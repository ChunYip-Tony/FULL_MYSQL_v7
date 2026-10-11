from __future__ import annotations

"""Receipt-history helper for YipMan Mobile V1 RC ordering detail.

This is intentionally read-only. It reuses the canonical completed-day receipt
semantics from webapp_v2_runtime so 101 vs 107+109 is not double counted.
"""

from decimal import Decimal
from typing import Any

from db import db_conn
from webapp_v2_runtime import _family_receipt_events


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _resolve_family(cur, family_key: str) -> dict[str, Any] | None:
    raw = str(family_key or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        cur.execute(
            """SELECT family_id,main_article_number,family_description
               FROM product_family
               WHERE main_article_number=%s OR family_id=%s
               ORDER BY CASE WHEN main_article_number=%s THEN 0 ELSE 1 END
               LIMIT 1""",
            (raw, int(raw), raw),
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


def family_receipt_history(family_key: str, limit_days: int = 12) -> dict[str, Any]:
    """Return recent positive canonical physical receipt days for one Family."""
    limit_days = max(1, min(int(limit_days or 12), 30))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        family = _resolve_family(cur, family_key)
        if not family:
            cur.close()
            raise KeyError("FAMILY_NOT_FOUND")

        fid = int(family["family_id"])
        events = _family_receipt_events(cur, fid, 180)
        codes=sorted({str(e.get('article_number') or '').strip() for e in events if str(e.get('article_number') or '').strip()})
        names={}
        if codes:
            cur.execute("SELECT article_number,article_description FROM article WHERE article_number IN ("+','.join(['%s']*len(codes))+")",tuple(codes))
            names={str(row['article_number']).strip():str(row.get('article_description') or '').strip() for row in cur.fetchall()}
        cur.close()

    positive = [
        dict(x)
        for x in events
        if x.get("receipt_quantity") is not None and _d(x.get("receipt_quantity")) > 0
    ]

    by_date: dict[Any, list[dict[str, Any]]] = {}
    for event in positive:
        by_date.setdefault(event.get("posting_date"), []).append(event)

    days: list[dict[str, Any]] = []
    for posting_date in sorted((d for d in by_date if d is not None), reverse=True)[:limit_days]:
        rows = by_date[posting_date]
        base_uoms = {
            str(x.get("base_receipt_uom") or "").strip().upper()
            for x in rows
            if x.get("base_receipt_uom")
        }
        if len(base_uoms) == 1 and all(x.get("base_receipt_quantity") is not None for x in rows):
            qty = sum((_d(x.get("base_receipt_quantity")) for x in rows), Decimal("0"))
            uom = next(iter(base_uoms))
            qty_basis = "BASE_UOM"
        else:
            entry_uoms = {
                str(x.get("receipt_uom") or "").strip().upper()
                for x in rows
                if x.get("receipt_uom")
            }
            if len(entry_uoms) == 1 and all(x.get("receipt_quantity") is not None for x in rows):
                qty = sum((_d(x.get("receipt_quantity")) for x in rows), Decimal("0"))
                uom = next(iter(entry_uoms))
                qty_basis = "ENTRY_UOM"
            else:
                qty = None
                uom = "MIXED" if rows else None
                qty_basis = "MIXED_OR_UNRESOLVED"

        days.append(
            {
                "date": posting_date,
                "weekday": posting_date.strftime("%a") if posting_date else None,
                "quantity": qty,
                "uom": uom,
                "quantity_basis": qty_basis,
                "event_count": len(rows),
                "article_numbers": sorted(
                    {
                        str(x.get("article_number") or "").strip()
                        for x in rows
                        if str(x.get("article_number") or "").strip()
                    }
                ),
                "events": [
                    {
                        "article_number": x.get("article_number"),
                        "article_name": names.get(str(x.get("article_number") or '').strip()) or None,
                        "receipt_quantity": x.get("receipt_quantity"),
                        "receipt_uom": x.get("receipt_uom"),
                        "base_receipt_quantity": x.get("base_receipt_quantity"),
                        "base_receipt_uom": x.get("base_receipt_uom"),
                        "movement_type": x.get("movement_type"),
                        "receipt_stage_basis": x.get("receipt_stage_basis"),
                        "gr_number": x.get("gr_number"),
                        "purchase_order": x.get("purchase_order"),
                        "vendor_code": x.get("vendor_code"),
                        "article_document": x.get("article_document"),
                    }
                    for x in rows
                ],
            }
        )

    return {
        "status": "READY",
        "family_id": int(family["family_id"]),
        "family_article_number": family.get("main_article_number"),
        "family_article_name": family.get("family_description"),
        "receipt_day_count_returned": len(days),
        "positive_receipt_event_count": len(positive),
        "days": days,
        "rule": "CANONICAL_COMPLETED_PHYSICAL_RECEIPTS_ONLY_101_OR_109_STAGE_NOT_DOUBLE_COUNTED",
    }
