from __future__ import annotations

"""v7.0.492 ChatGPT daily GP selling-unit cost repair.

The Google analysis bridge resolves cost authority at family level, then converts
that cost to each selling UPC's UOM. The pre-v492 daily publisher cached the
*already converted* result by family_id, which incorrectly reused an LB/CASE/PACK
conversion across sibling UPCs in the same family.

Examples caught by Batch 30:
- 4029551780 OYSTER IN SHELL 60EA: 12 EA/pack cost was replaced by a CASE-sized
  family sibling cost in daily GP.
- 75339325301 16/20 H/L JUMBO WHITE SHRIMP: 2 LB/pack daily cost was replaced by
  the 1 LB family sibling cost.

This wrapper preserves the original canonical POS-day selection and cost-authority
logic, then recomputes every observed UPC independently with _family_cost_as_of().
That keeps family-level cost authority while applying selling-unit conversion at
UPC grain.
"""

from decimal import Decimal
from typing import Any

import chatgpt_sheet_bridge as _bridge

_ORIGINAL_FETCH_LATEST_DAILY = _bridge._fetch_latest_daily_sales


def _d(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _fetch_latest_daily_sales_per_upc(
    cur,
    batch_id: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Recompute daily COGS/GP with selling-unit cost resolved per UPC."""
    result = _ORIGINAL_FETCH_LATEST_DAILY(cur, batch_id, rows)
    business_date = result.get("business_date")
    if business_date is None:
        return result

    total_cogs = Decimal("0")
    total_gp = Decimal("0")
    unresolved_sales = abs(_d(result.get("unmapped_sales")))

    for row in rows:
        # The original publisher explicitly labels rows that had no POS record.
        # Leave those rows untouched and only re-resolve observed selling UPCs.
        if str(row.get("latest_daily_cost_status") or "").upper() == "ZERO_SALES":
            continue

        sales = _d(row.get("latest_daily_sales_dollars"))
        qty = _d(row.get("latest_daily_pos_qty"))

        # IMPORTANT: do not cache this resolved value by family_id. The raw cost
        # authority is family-level, but base_qty_per_selling_unit / selling_uom
        # belongs to the individual selling UPC.
        cost = _bridge._family_cost_as_of(cur, row, business_date)
        status = str(cost.get("status") or "")
        row["latest_daily_cost_status"] = status
        row["latest_daily_cost_per_selling_unit"] = cost.get("cost_per_selling_unit")
        row["latest_daily_cost_source"] = cost.get("source")
        row["latest_daily_cost_date"] = cost.get("date")

        if status == "RESOLVED":
            if qty != 0:
                cogs = qty * Decimal(str(cost["cost_per_selling_unit"]))
                gp = sales - cogs
                row["latest_daily_cogs"] = cogs
                row["latest_daily_gp_dollars"] = gp
                row["latest_daily_gp_pct"] = (gp / sales) if sales != 0 else None
                total_cogs += cogs
                total_gp += gp
            else:
                row["latest_daily_cogs"] = Decimal("0")
                row["latest_daily_gp_dollars"] = sales
                row["latest_daily_gp_pct"] = Decimal("1") if sales != 0 else None
                total_gp += sales
        else:
            row["latest_daily_cogs"] = None
            row["latest_daily_gp_dollars"] = None
            row["latest_daily_gp_pct"] = None
            unresolved_sales += abs(sales)

    gp_complete = unresolved_sales <= Decimal("0.0001")
    total_sales = _d(result.get("sales_dollars"))
    result.update(
        {
            "cogs": total_cogs if gp_complete else None,
            "gp_dollars": total_gp if gp_complete else None,
            "gp_pct": (total_gp / total_sales)
            if gp_complete and total_sales != 0
            else None,
            "gp_status": "COMPLETE" if gp_complete else "PARTIAL_COST_OR_MAPPING",
            "cost_unresolved_sales": unresolved_sales,
        }
    )
    return result


def apply_chatgpt_daily_gp_v492() -> None:
    """Apply the repair once in the publisher process."""
    if getattr(_bridge, "_v492_daily_gp_patch_applied", False):
        return
    _bridge._fetch_latest_daily_sales = _fetch_latest_daily_sales_per_upc
    _bridge._v492_daily_gp_patch_applied = True
