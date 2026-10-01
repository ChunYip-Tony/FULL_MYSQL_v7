from __future__ import annotations

from typing import Any


# FULL MYSQL receipt semantics:
# - 101 is a direct physical goods receipt and carries receipt/cost evidence.
# - 107 is a valuated blocked-stock/cost stage. It is NOT a second delivery.
# - 109 is the physical GR/release into inventory for the same 107+109 delivery
#   flow. Its posting date is the delivery date even when 107 posts on another day.
# - 102/108/110 are reversals of 101/107/109 respectively.
DIRECT_PHYSICAL_RECEIPT_MOVEMENTS = frozenset({"101", "102"})
RELEASE_PHYSICAL_RECEIPT_MOVEMENTS = frozenset({"109", "110"})
PHYSICAL_RECEIPT_MOVEMENTS = (
    DIRECT_PHYSICAL_RECEIPT_MOVEMENTS | RELEASE_PHYSICAL_RECEIPT_MOVEMENTS
)
POSITIVE_PHYSICAL_RECEIPT_MOVEMENTS = frozenset({"101", "109"})

# Cost authority is intentionally separate from physical receipt quantity.
# 101 carries direct-GR value. In the valuated-blocked flow, 107 carries cost
# while 109 carries the physical GR quantity/date.
RECEIPT_COST_MOVEMENTS = frozenset({"101", "107"})
RECEIPT_COST_REVERSAL_MOVEMENTS = frozenset({"102", "108"})


def movement_type(row: dict[str, Any]) -> str:
    return str(row.get("movement_type") or "").strip()


def is_physical_receipt_movement(value: Any) -> bool:
    return str(value or "").strip() in PHYSICAL_RECEIPT_MOVEMENTS


def is_positive_physical_receipt_movement(value: Any) -> bool:
    return str(value or "").strip() in POSITIVE_PHYSICAL_RECEIPT_MOVEMENTS


def is_receipt_cost_movement(value: Any) -> bool:
    return str(value or "").strip() in RECEIPT_COST_MOVEMENTS


def physical_receipt_stage_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Return rows allowed to contribute physical delivery quantity.

    107/108 are deliberately never returned. This makes a 107+109 flow one
    physical delivery regardless of whether the two postings share a date.
    Direct 101/102 is preferred when present; otherwise 109/110 is the physical
    release/GR stage.
    """
    by_type: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_type.setdefault(movement_type(row), []).append(row)

    direct = (by_type.get("101") or []) + (by_type.get("102") or [])
    if direct:
        return direct, "101_102_DIRECT_GR_NET"

    release = (by_type.get("109") or []) + (by_type.get("110") or [])
    if release:
        return release, "107_109_VALUATED_BLOCKED_RELEASE_NET"

    return [], "NON_PHYSICAL_RECEIPT_STAGE"
