from __future__ import annotations

"""Family-scoped authoritative recalculation primitives for App Ready.

These functions deliberately pass the affected family into the heavy engine before
calculation. They are not full-review-then-filter adapters.
"""

from datetime import date
from typing import Any

from webapp_v2_runtime import bulk_ordering_suggestions


def recalculate_ordering_family(
    family_id: int,
    *,
    ordering_date: date | None = None,
    delivery_date: date | None = None,
    next_delivery_date: date | None = None,
) -> dict[str, Any]:
    """Recalculate one Family through the authoritative bulk ordering engine.

    FRESH and FROZEN are both probed because category is authoritative engine
    metadata; only a result belonging to ``family_id`` is retained. The heavy
    engine receives ``family_ids=[family_id]`` up front, so unrelated Family
    calculators are not intentionally invoked by this entry point.
    """
    fid = int(family_id)
    if fid <= 0:
        raise ValueError("FAMILY_ID_MUST_BE_POSITIVE")

    results: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    engine_inputs: dict[str, Any] = {}

    for category in ("FRESH", "FROZEN"):
        payload = bulk_ordering_suggestions(
            category,
            ordering_date=ordering_date,
            expected_delivery_date=delivery_date,
            next_delivery_date=next_delivery_date,
            include_sufficient_stock=True,
            family_ids=[fid],
        )
        engine_inputs[category] = payload.get("inputs")
        for row in payload.get("suggestions") or []:
            if int(row.get("family_id") or 0) == fid:
                results.append(row)
        for row in payload.get("skipped") or []:
            if int(row.get("family_id") or 0) == fid:
                skipped.append(row)

    # A Family must not appear as two independent category decisions. Fail
    # closed if upstream identity/category data violates that invariant.
    if len(results) > 1:
        raise RuntimeError("FAMILY_CATEGORY_IDENTITY_AMBIGUOUS")

    return {
        "contract_version": "YIPMAN_FAMILY_INCREMENTAL_ORDERING_V1",
        "family_id": fid,
        "scope": {"family_ids": [fid]},
        "status": "READY" if results else ("SKIPPED" if skipped else "NOT_FOUND"),
        "row": results[0] if results else None,
        "skipped": skipped,
        "engine_inputs": engine_inputs,
        "rules": {
            "authoritative_engine": "webapp_v2_runtime.bulk_ordering_suggestions",
            "scope_applied_before_heavy_calculation": True,
            "full_review_then_filter": False,
        },
    }
