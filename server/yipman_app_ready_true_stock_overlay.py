from __future__ import annotations

"""Immediate family-scoped App Ready inventory overlay after True Stock mutations."""

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
    return bool(targets) and any(str(row.get(k) or "").strip() in targets for k in _FAMILY_KEYS)


def _patch_row(row: dict[str, Any], family_id: str, main_article: str, qty: Any, uom: str | None, source: str) -> bool:
    if not _same_family(row, family_id, main_article):
        return False
    for key in _OH_KEYS:
        if key in row:
            row[key] = qty
    if "effective_oh_uom" in row: row["effective_oh_uom"] = uom
    if "current_oh_uom" in row: row["current_oh_uom"] = uom
    if "oh_source" in row: row["oh_source"] = source
    if "effective_oh_source" in row: row["effective_oh_source"] = source
    if any(k in row for k in ("recommendation_code", "operational_decision_code", "suggested_order_qty", "suggested_price")):
        row["decision_evidence_ready"] = False
        missing = list(row.get("decision_missing_evidence")) if isinstance(row.get("decision_missing_evidence"), list) else []
        marker = "INVENTORY_FAMILY_RECALC_PENDING"
        if marker not in missing: missing.append(marker)
        row["decision_missing_evidence"] = missing
        row["operational_decision_code"] = "DATA_NEEDED"
        row["operational_decision_label"] = "DATA NEEDED"
    row["true_stock_incremental_overlay"] = True
    row["inventory_overlay_source"] = source
    return True


def _walk(value: Any, family_id: str, main_article: str, qty: Any, uom: str | None, source: str = "TRUE_STOCK") -> int:
    count = 0
    if isinstance(value, dict):
        if _patch_row(value, family_id, main_article, qty, uom, source): count += 1
        for child in value.values(): count += _walk(child, family_id, main_article, qty, uom, source)
    elif isinstance(value, list):
        for child in value: count += _walk(child, family_id, main_article, qty, uom, source)
    return count


def apply_true_stock_family_overlay(result: dict[str, Any]) -> dict[str, Any]:
    active = APP_READY_SNAPSHOTS.active()
    if active is None: return {"status": "NO_ACTIVE_SNAPSHOT", "patched_rows": 0}
    family_id = str(result.get("family_id") or "").strip()
    main_article = str(result.get("main_article_number") or "").strip()
    cancelled = str(result.get("action") or "").upper() == "TRUE_STOCK_CANCELLED"
    qty = result.get("system_oh") if cancelled else result.get("true_stock")
    uom_raw = result.get("system_oh_uom") if cancelled else result.get("uom")
    uom = str(uom_raw or "").strip().upper() or None
    source = "SYSTEM_OH" if cancelled else "TRUE_STOCK"
    if qty is None or not (family_id or main_article):
        return {"status": "IDENTITY_OR_QUANTITY_MISSING", "patched_rows": 0}
    sections = deepcopy(active.sections)
    patched = _walk(sections, family_id, main_article, qty, uom, source)
    if patched == 0: return {"status": "FAMILY_NOT_IN_ACTIVE_SNAPSHOT", "patched_rows": 0}
    now = datetime.now(timezone.utc).isoformat()
    candidate = replace(active, build_id=str(uuid.uuid4()), source_batch_id=f"INVENTORY_INCREMENTAL:{source}:{family_id or main_article}", started_at=now, completed_at=now, sections=sections, error=None, build_ms=0.0)
    candidate.stage = "APP_READY"
    candidate.section_status = dict(active.section_status)
    from yipman_app_ready_persistence import persist_complete_snapshot
    persist_complete_snapshot(candidate)
    APP_READY_SNAPSHOTS.hydrate(candidate)
    return {"status": "APP_READY", "build_id": candidate.build_id, "patched_rows": patched, "source": source}
