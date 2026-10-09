from __future__ import annotations

"""Immediate family-scoped App Ready overlay after an authoritative True Stock write.

This deliberately does not run global ordering/pricing engines. It makes the new
physical count visible everywhere in the active read model immediately and
fails dependent family decisions closed until a family-scoped calculator can
replace them. Unrelated families are byte-for-byte untouched.
"""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
import uuid

from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS

_FAMILY_KEYS = ("family_id", "family", "family_article", "main_article_number")
_OH_KEYS = ("effective_oh", "current_oh", "ordering_oh_used", "actual_position")


def _same_family(row: dict[str, Any], family_id: str, main_article: str) -> bool:
    targets = {x for x in (family_id, main_article) if x}
    if not targets:
        return False
    return any(str(row.get(k) or "").strip() in targets for k in _FAMILY_KEYS)


def _patch_row(row: dict[str, Any], family_id: str, main_article: str, qty: Any, uom: str | None) -> bool:
    if not _same_family(row, family_id, main_article):
        return False
    touched = False
    for key in _OH_KEYS:
        if key in row:
            row[key] = qty
            touched = True
    if "effective_oh_uom" in row:
        row["effective_oh_uom"] = uom
    if "current_oh_uom" in row:
        row["current_oh_uom"] = uom
    if "oh_source" in row:
        row["oh_source"] = "TRUE_STOCK"
    if "effective_oh_source" in row:
        row["effective_oh_source"] = "TRUE_STOCK"
    # Never leave a pre-count recommendation looking authoritative. A later
    # family-scoped calculator replaces this guard with recalculated evidence.
    for key in ("decision_evidence_ready",):
        if key in row:
            row[key] = False
    if any(k in row for k in ("recommendation_code", "operational_decision_code", "suggested_order_qty", "suggested_price")):
        row["decision_evidence_ready"] = False
        missing = row.get("decision_missing_evidence")
        missing = list(missing) if isinstance(missing, list) else []
        if "TRUE_STOCK_FAMILY_RECALC_PENDING" not in missing:
            missing.append("TRUE_STOCK_FAMILY_RECALC_PENDING")
        row["decision_missing_evidence"] = missing
        row["operational_decision_code"] = "DATA_NEEDED"
        row["operational_decision_label"] = "DATA NEEDED"
    row["true_stock_incremental_overlay"] = True
    touched = True
    return touched


def _walk(value: Any, family_id: str, main_article: str, qty: Any, uom: str | None) -> int:
    count = 0
    if isinstance(value, dict):
        if _patch_row(value, family_id, main_article, qty, uom):
            count += 1
        for child in value.values():
            count += _walk(child, family_id, main_article, qty, uom)
    elif isinstance(value, list):
        for child in value:
            count += _walk(child, family_id, main_article, qty, uom)
    return count


def apply_true_stock_family_overlay(result: dict[str, Any]) -> dict[str, Any]:
    active = APP_READY_SNAPSHOTS.active()
    if active is None:
        return {"status": "NO_ACTIVE_SNAPSHOT", "patched_rows": 0}
    family_id = str(result.get("family_id") or "").strip()
    main_article = str(result.get("main_article_number") or "").strip()
    qty = result.get("true_stock")
    uom = str(result.get("uom") or "").strip().upper() or None
    if qty is None or not (family_id or main_article):
        return {"status": "IDENTITY_OR_QUANTITY_MISSING", "patched_rows": 0}

    sections = deepcopy(active.sections)
    patched = _walk(sections, family_id, main_article, qty, uom)
    if patched == 0:
        return {"status": "FAMILY_NOT_IN_ACTIVE_SNAPSHOT", "patched_rows": 0}

    now = datetime.now(timezone.utc).isoformat()
    candidate = replace(
        active,
        build_id=str(uuid.uuid4()),
        source_batch_id=f"TRUE_STOCK_INCREMENTAL:{family_id or main_article}",
        started_at=now,
        completed_at=now,
        sections=sections,
        error=None,
        build_ms=0.0,
    )
    candidate.stage = "APP_READY"
    candidate.section_status = dict(active.section_status)
    from yipman_app_ready_persistence import persist_complete_snapshot
    persist_complete_snapshot(candidate)
    APP_READY_SNAPSHOTS.hydrate(candidate)
    return {"status": "APP_READY", "build_id": candidate.build_id, "patched_rows": patched}
