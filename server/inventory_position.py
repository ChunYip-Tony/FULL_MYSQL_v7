from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from data_coverage import source_data_days
from business_clock import completed_through_date
from manual_overrides import confirmed_operational_uom_basis


# FULL MYSQL System OH is based on SAP Unrestricted stock. Only movement types
# whose stock effect on Unrestricted is explicit are allowed to roll the anchor.
# Quantities are already source-signed in movement_history.
UNRESTRICTED_APPLY_AS_SIGNED = {
    "101", "102",  # direct GR / reversal
    "105", "106",  # release from GR blocked stock / reversal
    "109", "110",  # release from valuated GR blocked stock / reversal
    "161", "162",  # purchase-order return / reversal
    "251", "252",  # goods issue for sale / reversal
    "309", "310",  # material-to-material transfer / reversal
    "317", "318",  # create structured article / reversal (SAP Retail)
    "551", "552",  # scrap unrestricted stock / reversal
    "701", "702",  # physical-inventory adjustment, unrestricted stock
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


def _movement_coverage_after_anchor(
    cur,
    *,
    anchor_day: date,
    include_batch_id: int | None = None,
) -> dict[str, Any]:
    """Return fail-closed completed-day MVT coverage after an inventory anchor.

    Current inventory may use only completed business days. Today is intentionally
    excluded because a same-day MVT export is provisional by policy. Every calendar
    business date from anchor+1 through yesterday must have one canonical COMPLETE
    movement snapshot; otherwise the roll-forward is not analysis-usable.
    """
    expected_through = completed_through_date()
    if anchor_day >= expected_through:
        return {
            "expected_through_date": expected_through,
            "complete": True,
            "required_day_count": 0,
            "complete_day_count": 0,
            "missing_day_count": 0,
            "missing_days": [],
            "latest_complete_date": anchor_day,
        }

    days = source_data_days(
        cur,
        "movement",
        include_batch_id=include_batch_id,
        up_to=expected_through,
    )
    complete_dates = {d["date"] for d in days if d["date"] > anchor_day}

    required_days: list[date] = []
    d = anchor_day + timedelta(days=1)
    while d <= expected_through:
        required_days.append(d)
        d += timedelta(days=1)

    missing_days = [d for d in required_days if d not in complete_dates]
    return {
        "expected_through_date": expected_through,
        "complete": not missing_days,
        "required_day_count": len(required_days),
        "complete_day_count": len(required_days) - len(missing_days),
        "missing_day_count": len(missing_days),
        "missing_days": missing_days,
        "latest_complete_date": max(complete_dates) if complete_dates else anchor_day,
    }


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
    source_anchor_uom = str(anchor_uom or "").strip().upper() or None
    operational = confirmed_operational_uom_basis(cur, family_id)
    operational_uom = (
        str(operational.get("operational_uom_code") or "").strip().upper()
        if operational else None
    )
    uom = operational_uom or source_anchor_uom
    scope = str(scope_type or "").strip().upper()

    result: dict[str, Any] = {
        "status": "READY",
        "analysis_usable": True,
        "scope_type": scope or None,
        "anchor_date": anchor_day,
        "anchor_uom": uom,
        "source_anchor_uom": source_anchor_uom,
        "operational_uom_authority": operational,
        "movement_delta": Decimal("0"),
        "movement_through_date": anchor_day,
        "movement_days": [],
        "movement_file_ids": [],
        "movement_row_count": 0,
        "by_movement_type": [],
        "ignored_by_movement_type": [],
        "unresolved_movement_types": [],
        "stock_basis": (
            "SAP_UNRESTRICTED_USER_CONFIRMED_OPERATIONAL_UOM"
            if operational else "SAP_UNRESTRICTED"
        ),
        "same_day_policy": "ANCHOR_OWNS_ENTIRE_BUSINESS_DATE",
        "movement_coverage_expected_through": None,
        "movement_coverage_complete": False,
        "movement_coverage_required_day_count": 0,
        "movement_coverage_complete_day_count": 0,
        "missing_movement_day_count": 0,
        "missing_movement_days": [],
        "latest_complete_movement_date": anchor_day,
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

    coverage = _movement_coverage_after_anchor(
        cur,
        anchor_day=anchor_day,
        include_batch_id=include_batch_id,
    )
    result["movement_coverage_expected_through"] = coverage["expected_through_date"]
    result["movement_coverage_complete"] = coverage["complete"]
    result["movement_coverage_required_day_count"] = coverage["required_day_count"]
    result["movement_coverage_complete_day_count"] = coverage["complete_day_count"]
    result["missing_movement_day_count"] = coverage["missing_day_count"]
    result["missing_movement_days"] = coverage["missing_days"]
    result["latest_complete_movement_date"] = coverage["latest_complete_date"]

    days = source_data_days(
        cur,
        "movement",
        include_batch_id=include_batch_id,
        up_to=coverage["expected_through_date"],
    )
    post_days = [d for d in days if d["date"] > anchor_day]

    if not coverage["complete"]:
        result["blockers"].append("MOVEMENT_DAILY_COVERAGE_GAP")
        result["status"] = "BLOCKED"
        result["analysis_usable"] = False

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

    canonical_by_date = {d["date"]: int(d["file_id"]) for d in post_days}
    file_ids = sorted(set(canonical_by_date.values()))
    placeholders = ",".join(["%s"] * len(file_ids))

    cur.execute(
        f"""SELECT file_id,posting_date,movement_type,
                   UPPER(TRIM(COALESCE(base_uom_code,''))) AS base_uom_code,
                   UPPER(TRIM(COALESCE(entry_uom_code,''))) AS entry_uom_code,
                   SUM(base_quantity) AS base_movement_quantity,
                   SUM(entry_quantity) AS entry_movement_quantity,
                   COUNT(*) AS row_count
            FROM movement_history
            WHERE file_id IN ({placeholders})
              AND {scope_sql}
              AND (base_quantity IS NOT NULL OR entry_quantity IS NOT NULL)
            GROUP BY file_id,posting_date,movement_type,
                     UPPER(TRIM(COALESCE(base_uom_code,''))),
                     UPPER(TRIM(COALESCE(entry_uom_code,'')))
            ORDER BY posting_date,file_id,movement_type""",
        (*file_ids, scope_arg),
    )
    rows = cur.fetchall()

    delta = Decimal("0")
    movement_row_count = 0
    by_type: dict[str, Decimal] = {}
    ignored_by_type: dict[str, Decimal] = {}
    unresolved_types: dict[str, Decimal] = {}
    bad_uoms: list[dict[str, Any]] = []

    for row in rows:
        fid = int(row["file_id"])
        posting_day = _as_date(row.get("posting_date"))

        # One multi-date MVT file may be canonical for several exact posting
        # dates. Accept only the canonical file/date pair and ignore other rows
        # from the same source file rather than treating them as a mismatch.
        if posting_day is None or canonical_by_date.get(posting_day) != fid:
            continue

        use_entry_basis = bool(
            operational
            and str(operational.get("movement_quantity_basis") or "").upper() == "ENTRY"
        )
        if use_entry_basis:
            raw_qty = row.get("entry_movement_quantity")
            row_uom = str(row.get("entry_uom_code") or "").strip().upper() or None
            quantity_basis = "ENTRY"
        else:
            raw_qty = row.get("base_movement_quantity")
            row_uom = str(row.get("base_uom_code") or "").strip().upper() or None
            quantity_basis = "BASE"

        if raw_qty is None:
            bad_uoms.append({
                "file_id": fid,
                "posting_date": posting_day,
                "movement_type": row.get("movement_type"),
                "movement_uom": row_uom,
                "anchor_uom": uom,
                "quantity": None,
                "quantity_basis": quantity_basis,
                "reason": "AUTHORIZED_QUANTITY_BASIS_MISSING",
            })
            continue

        qty = Decimal(str(raw_qty))
        if qty == 0:
            continue

        if row_uom != uom:
            bad_uoms.append({
                "file_id": fid,
                "posting_date": posting_day,
                "movement_type": row.get("movement_type"),
                "movement_uom": row_uom,
                "anchor_uom": uom,
                "quantity": qty,
                "quantity_basis": quantity_basis,
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
        "uom": movement["anchor_uom"],
        "source_anchor_uom": movement.get("source_anchor_uom"),
        "operational_uom_authority": movement.get("operational_uom_authority"),
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
        "movement_coverage_expected_through": movement["movement_coverage_expected_through"],
        "movement_coverage_complete": movement["movement_coverage_complete"],
        "movement_coverage_required_day_count": movement["movement_coverage_required_day_count"],
        "movement_coverage_complete_day_count": movement["movement_coverage_complete_day_count"],
        "missing_movement_day_count": movement["missing_movement_day_count"],
        "missing_movement_days": movement["missing_movement_days"],
        "latest_complete_movement_date": movement["latest_complete_movement_date"],
        "rollforward_status": movement["status"],
        "analysis_usable": movement["analysis_usable"],
        "blockers": movement["blockers"],
        **({"uom_mismatches": movement["uom_mismatches"]}
           if "uom_mismatches" in movement else {}),
    }
