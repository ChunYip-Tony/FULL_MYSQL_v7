from __future__ import annotations

"""Evidence-backed repair helpers for current Quick Check QA holds."""

import json
from decimal import Decimal
from typing import Any

from db import db_conn
from maintenance_api import (
    run_article_manual_roster_repair,
    run_confirmed_uom_refresh,
    run_confirmed_cost_conversion_refresh,
    run_cost_authority_refresh,
    run_safe_cost_refresh,
)

CORE_CODE = "QUICK_CHECK_CORE_FIELD_MISSING"


def repair_contract() -> dict[str, Any]:
    return {
        "mode": "EVIDENCE_BACKED_ONLY",
        "invent_identity": False,
        "invent_uom": False,
        "invent_conversion": False,
        "invent_cost": False,
    }


def _positive(value: Any) -> bool:
    try:
        return Decimal(str(value)) > 0
    except Exception:
        return False


def _reason_fixed(reason: str, row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    reason = str(reason or "").upper().strip()
    if reason == "SELLING_UOM_MISSING":
        return bool(str(row.get("selling_uom") or "").strip())
    if reason == "COST_TO_SELLING_UOM_UNRESOLVED":
        return _positive(row.get("current_cost_per_selling_unit"))
    if reason == "CURRENT_COST_MISSING":
        return _positive(row.get("current_cost_per_base_uom")) or _positive(row.get("current_cost_per_selling_unit"))
    return str(row.get("quick_check_status") or "").upper() == "READY"


def _reconcile_fixed_core_issues(actor: str) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT MAX(batch_id) AS batch_id FROM phase3_batch_result")
        row = cur.fetchone() or {}
        batch_id = int(row["batch_id"]) if row.get("batch_id") is not None else None
        if batch_id is None:
            cur.close()
            return {"batch_id": None, "resolved": 0, "remaining": 0}

        cur.execute(
            """SELECT issue_id,entity_key,issue_summary,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code=%s AND UPPER(entity_type)='UPC'
               ORDER BY issue_id""",
            (batch_id, CORE_CODE),
        )
        issues = [dict(x) for x in cur.fetchall()]
        resolved: list[str] = []

        for issue in issues:
            upc = str(issue.get("entity_key") or "")
            cur.execute(
                """SELECT quick_check_status,selling_uom,current_cost_per_base_uom,
                          current_cost_per_selling_unit
                   FROM quick_check_current WHERE ean_upc=%s LIMIT 1""",
                (upc,),
            )
            current = cur.fetchone()
            try:
                detail = json.loads(issue.get("detail_json") or "{}")
                if not isinstance(detail, dict):
                    detail = {}
            except Exception:
                detail = {}
            reasons = [str(x).upper().strip() for x in (detail.get("reasons") or []) if str(x).strip()]
            if not reasons:
                summary = str(issue.get("issue_summary") or "").upper()
                reasons = [x for x in ("SELLING_UOM_MISSING", "COST_TO_SELLING_UOM_UNRESOLVED", "CURRENT_COST_MISSING") if x in summary]
            if reasons and all(_reason_fixed(reason, current) for reason in reasons):
                cur.execute(
                    """UPDATE qa_phase3_issue
                       SET issue_status='RESOLVED',
                           detail_json=JSON_SET(COALESCE(detail_json,JSON_OBJECT()),
                             '$.evidence_repair_actor',%s)
                       WHERE issue_id=%s AND issue_status='OPEN'""",
                    (actor, int(issue["issue_id"])),
                )
                if cur.rowcount:
                    resolved.append(upc)

        conn.commit()
        cur.execute(
            """SELECT COUNT(*) AS c FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN' AND issue_code=%s""",
            (batch_id, CORE_CODE),
        )
        remaining = int((cur.fetchone() or {}).get("c") or 0)
        cur.close()
    return {"batch_id": batch_id, "resolved": len(resolved), "resolved_upcs": resolved, "remaining": remaining}


def run_evidence_backed_qa_repair(actor: str) -> dict[str, Any]:
    results: dict[str, Any] = {"contract": repair_contract(), "steps": {}}
    for name, fn in (
        ("article_manual_roster", run_article_manual_roster_repair),
        ("confirmed_uom", run_confirmed_uom_refresh),
        ("confirmed_cost_conversion", run_confirmed_cost_conversion_refresh),
        ("cost_authority", run_cost_authority_refresh),
        ("safe_cost", run_safe_cost_refresh),
    ):
        try:
            results["steps"][name] = fn(actor)
        except Exception as exc:
            results["steps"][name] = {
                "status": "HELD_OR_SKIPPED",
                "error": f"{type(exc).__name__}: {exc}"[:1000],
            }
    results["reconcile"] = _reconcile_fixed_core_issues(actor)
    return results
