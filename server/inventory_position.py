from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from data_coverage import source_data_days


# FULL MYSQL System OH is based on SAP Unrestricted stock. Only movement types
# whose stock effect on Unrestricted is explicit are allowed to roll the anchor.
# Quantities are already source-signed in movement_history.
UNRESTRICTED_APPLY_AS_SIGNED = {
    "101", "102",  # direct GR / reversal
    "105", "106",  # release from GR blocked stock / reversal
    "109", "110",  # release from valuated GR blocked stock / reversal
    "251", "252",  # store-confirmed sale / return movement
}
UNRESTRICTED_NO_EFFECT = {
    "103", "104",  # GR blocked stock / reversal
    "107", "108",  # valuated GR blocked stock / reversal
}


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None


def latest_canonical_movement_day(
    cur,
    *,
    include_batch_id: int | None = None,
    up_to: date | None = None,
) -> dict[str, Any] | None:
    days = source_data_days(
        cur,
        "movement",
        include_batch_id=include_batch_id,
        up_to=up_to,
    )
    return days[0] if days else None


def movement_rollforward(
    cur,
    *,
    scope_type: str,
    article_id: int | None,
    family_id: int | None,
    upc_id: int | None,
    anchor_date: date | datetime | str | None,
    anchor_uom: str | None,
    include_batch_id: int | None = None,
) -> dict[str, Any]:
    """Return signed post-anchor inventory movement using canonical MVT data days.

    Policy:
    - movement_history.base_quantity is already source-signed and is summed as-is;
    - only the canonical valid MVT file for each business date is used;
    - the physical/OH anchor owns its entire anchor business date, because the
      current source does not provide transaction posting timestamps;
    - therefore only posting dates STRICTLY AFTER anchor_date roll the anchor;
    - UOM must match the anchor UOM exactly (case-insensitive). No inferred
      conversion is allowed;
    - UPC-scoped inventory cannot safely consume article-level movement because
      movement_history has no UPC key. That case fails closed when post-anchor
      movement days exist.
    """
    anchor_day = _as_date(anchor_date)
    uom = str(anchor_uom or "").strip().upper() or None
    scope = str(scope_type or "").strip().upper()

    result: dict[str, Any] = {
        "status": "READY",
        "analysis_usable": True,
        "scope_type": scope or None,
        "anchor_date": anchor_day,
        "anchor_uom": uom,
        "movement_delta": Decimal("0"),
        "movement_through_date": anchor_day,
        "movement_days": [],
        "movement_file_ids": [],
        "movement_row_count": 0,
        "by_movement_type": [],
        "ignored_by_movement_type": [],
        "unresolved_movement_types": [],
        "stock_basis": "SAP_UNRESTRICTED",
        "same_day_policy": "ANCHOR_OWNS_ENTIRE_BUSINESS_DATE",
        "blockers": [],
    }

    if anchor_day is None:
        result["status"] = "BLOCKED"
        result["analysis_usable"] = False
        result["blockers"].append("ANCHOR_DATE_MISSING")
        return result
    if not uom:
        result["status"] = "BLOCKED"
        result["analysis_usable"] = False
        result["blockers"].append("ANCHOR_UOM_MISSING")
        return result

    days = source_data_days(
        cur,
        "movement",
        include_batch_id=include_batch_id,
    )
    post_days = [d for d in days if d["date"] > anchor_day]
    if not post_days:
        return result

    if scope == "UPC":
        result["status"] = "BLOCKED"
        result["analysis_usable"] = False
        result["blockers"].append("UPC_SCOPE_HAS_NO_EXACT_MOVEMENT_KEY")
        result["movement_days"] = [d["date"] for d in sorted(post_days, key=lambda x: x["date"])]
        result["movement_file_ids"] = [int(d["file_id"]) for d in sorted(post_days, key=lambda x: x["date"])]
        result["movement_through_date"] = max(d["date"] for d in post_days)
        return result

    if scope == "ARTICLE":
        if article_id is None:
            result["status"] = "BLOCKED"
            result["analysis_usable"] = False
            result["blockers"].append("ARTICLE_SCOPE_ID_MISSING")
            return result
        scope_sql = "article_id=%s"
        scope_arg = int(article_id)
    elif scope == "FAMILY":
        if family_id is None:
            result["status"] = "BLOCKED"
            result["analysis_usable"] = False
            result["blockers"].append("FAMILY_SCOPE_ID_MISSING")
            return result
        scope_sql = "family_id=%s"
        scope_arg = int(family_id)
    else:
        result["status"] = "BLOCKED"
        result["analysis_usable"] = False
        result["blockers"].append("INVENTORY_SCOPE_UNRESOLVED")
        return result

    canonical_by_file = {int(d["file_id"]): d["date"] for d in post_days}
    file_ids = sorted(canonical_by_file)
    placeholders = ",".join(["%s"] * len(file_ids))

    cur.execute(
        f"""SELECT file_id,posting_date,movement_type,
                   UPPER(TRIM(COALESCE(base_uom_code,''))) AS base_uom_code,
                   COALESCE(SUM(base_quantity),0) AS movement_quantity,
                   COUNT(*) AS row_count
            FROM movement_history
            WHERE file_id IN ({placeholders})
              AND {scope_sql}
              AND base_quantity IS NOT NULL
            GROUP BY file_id,posting_date,movement_type,
                     UPPER(TRIM(COALESCE(base_uom_code,'')))
            ORDER BY posting_date,file_id,movement_type""",
        (*file_ids, scope_arg),
    )
    rows = cur.fetchall()

    delta = Decimal("0")
    movement_row_count = 0
    by_type: dict[str, Decimal] = {}
    ignored_by_type: dict[str, Decimal] = {}
    unresolved_types: dict[str, Decimal] = {}
    bad_dates: list[dict[str, Any]] = []
    bad_uoms: list[dict[str, Any]] = []

    for row in rows:
        fid = int(row["file_id"])
        posting_day = _as_date(row.get("posting_date"))
        canonical_day = canonical_by_file.get(fid)
        qty = Decimal(str(row.get("movement_quantity") or 0))
        if qty == 0:
            continue

        if posting_day != canonical_day:
            bad_dates.append({
                "file_id": fid,
                "canonical_date": canonical_day,
                "posting_date": posting_day,
                "movement_type": row.get("movement_type"),
                "quantity": qty,
            })
            continue

        row_uom = str(row.get("base_uom_code") or "").strip().upper() or None
        if row_uom != uom:
            bad_uoms.append({
                "file_id": fid,
                "posting_date": posting_day,
                "movement_type": row.get("movement_type"),
                "movement_uom": row_uom,
                "anchor_uom": uom,
                "quantity": qty,
            })
            continue

        mt = str(row.get("movement_type") or "UNKNOWN").strip().upper()
        if mt in UNRESTRICTED_NO_EFFECT:
            ignored_by_type[mt] = ignored_by_type.get(mt, Decimal("0")) + qty
            continue
        if mt not in UNRESTRICTED_APPLY_AS_SIGNED:
            unresolved_types[mt] = unresolved_types.get(mt, Decimal("0")) + qty
            continue

        delta += qty
        movement_row_count += int(row.get("row_count") or 0)
        by_type[mt] = by_type.get(mt, Decimal("0")) + qty

    if bad_dates:
        result["blockers"].append("CANONICAL_FILE_POSTING_DATE_MISMATCH")
        result["posting_date_mismatches"] = bad_dates
    if bad_uoms:
        result["blockers"].append("MOVEMENT_UOM_MISMATCH")
        result["uom_mismatches"] = bad_uoms
    if unresolved_types:
        result["blockers"].append("MOVEMENT_TYPE_UNRESTRICTED_EFFECT_UNRESOLVED")
        result["unresolved_movement_types"] = [
            {"movement_type": mt, "quantity": qty, "uom": uom}
            for mt, qty in sorted(unresolved_types.items())
        ]

    result["movement_delta"] = delta
    result["movement_row_count"] = movement_row_count
    result["movement_days"] = [d["date"] for d in sorted(post_days, key=lambda x: x["date"])]
    result["movement_file_ids"] = [int(d["file_id"]) for d in sorted(post_days, key=lambda x: x["date"])]
    result["movement_through_date"] = max(d["date"] for d in post_days)
    result["by_movement_type"] = [
        {"movement_type": mt, "quantity": qty, "uom": uom, "inventory_effect": "APPLY_SIGNED"}
        for mt, qty in sorted(by_type.items())
    ]
    result["ignored_by_movement_type"] = [
        {"movement_type": mt, "quantity": qty, "uom": uom, "inventory_effect": "NO_UNRESTRICTED_EFFECT"}
        for mt, qty in sorted(ignored_by_type.items())
    ]

    if result["blockers"]:
        result["status"] = "BLOCKED"
        result["analysis_usable"] = False
    return result


def rollforward_position(
    cur,
    *,
    anchor_quantity: Decimal | int | float | str | None,
    anchor_uom: str | None,
    anchor_date: date | datetime | str | None,
    scope_type: str,
    article_id: int | None,
    family_id: int | None,
    upc_id: int | None,
    include_batch_id: int | None = None,
) -> dict[str, Any]:
    qty = Decimal(str(anchor_quantity)) if anchor_quantity is not None else None
    movement = movement_rollforward(
        cur,
        scope_type=scope_type,
        article_id=article_id,
        family_id=family_id,
        upc_id=upc_id,
        anchor_date=anchor_date,
        anchor_uom=anchor_uom,
        include_batch_id=include_batch_id,
    )

    current = None
    if qty is not None and movement["analysis_usable"]:
        current = qty + Decimal(str(movement["movement_delta"]))

    return {
        "anchor_quantity": qty,
        "quantity": current,
        "uom": str(anchor_uom or "").strip().upper() or None,
        "anchor_date": _as_date(anchor_date),
        "movement_delta": movement["movement_delta"],
        "movement_through_date": movement["movement_through_date"],
        "movement_days": movement["movement_days"],
        "movement_file_ids": movement["movement_file_ids"],
        "movement_row_count": movement["movement_row_count"],
        "by_movement_type": movement["by_movement_type"],
        "ignored_by_movement_type": movement["ignored_by_movement_type"],
        "unresolved_movement_types": movement["unresolved_movement_types"],
        "stock_basis": movement["stock_basis"],
        "same_day_policy": movement["same_day_policy"],
        "rollforward_status": movement["status"],
        "analysis_usable": movement["analysis_usable"],
        "blockers": movement["blockers"],
        **({"posting_date_mismatches": movement["posting_date_mismatches"]}
           if "posting_date_mismatches" in movement else {}),
        **({"uom_mismatches": movement["uom_mismatches"]}
           if "uom_mismatches" in movement else {}),
    }
