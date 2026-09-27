from __future__ import annotations

from typing import Any

from db import db_conn
from manual_overrides import (
    USER_CONFIRMED_UOM_REVIEW_20260926,
    ensure_override_table,
    ensure_retirement_table,
    apply_manual_upc_overrides,
    apply_manual_upc_retirements,
)
from product_identity_audit import audit_product_identity
from current_active_cost_repair import repair_current_active_cost
from global_cost_hold_diagnostic import diagnose_global_cost_holds
from phase3 import rebuild_quick_check


def _retirement_ok(row: dict[str, Any]) -> bool:
    return (
        (row.get("record_status") is None or str(row.get("record_status")).upper() == "RETIRED")
        and int(row.get("active_article_links") or 0) == 0
        and int(row.get("active_uom_rows") or 0) == 0
        and int(row.get("quick_check_rows") or 0) == 0
    )


def run_manual_authority_refresh(device: str) -> dict[str, Any]:
    """Apply pre-defined user authority in one explicit transaction."""

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Manual tables may be absent only on bootstrap. Ensure them BEFORE the
            # business transaction because MySQL DDL implicitly commits.
            ensure_override_table(cur)
            ensure_retirement_table(cur)
            conn.commit()

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE stage_name='POST_RAW_PIPELINE'
                     AND processing_status='STARTED'"""
            )
            if int((cur.fetchone() or {}).get("c") or 0) > 0:
                conn.rollback()
                raise RuntimeError(
                    "Server pipeline is currently processing a batch; retry the "
                    "manual authority refresh after processing finishes."
                )

            # End the read transaction and begin the atomic authority transaction.
            conn.commit()
            conn.start_transaction()

            before = audit_product_identity(cur)
            overrides = apply_manual_upc_overrides(cur)
            retirements = apply_manual_upc_retirements(cur)

            if overrides.get("held"):
                raise RuntimeError(
                    "One or more confirmed manual overrides could not be applied: "
                    + str(overrides.get("held"))
                )

            after = audit_product_identity(cur)
            failed_overrides = [
                x for x in after.get("manual_override_checks", [])
                if not bool(x.get("pass"))
            ]
            failed_retirements = [
                x for x in after.get("retirement_checks", [])
                if not _retirement_ok(x)
            ]
            if failed_overrides or failed_retirements:
                raise RuntimeError(
                    "Post-refresh authority verification failed; transaction rolled back. "
                    f"failed_overrides={failed_overrides}; "
                    f"failed_retirements={failed_retirements}"
                )

            conn.commit()
            return {
                "status": "COMMITTED",
                "device": device,
                "mode": "SERVER_SIDE_API_ONLY_NO_QC_REBUILD_TRANSACTION_SAFE",
                "before_summary": before.get("summary"),
                "manual_overrides": overrides,
                "manual_retirements": retirements,
                "after_summary": after.get("summary"),
                "manual_override_checks": after.get("manual_override_checks"),
                "retirement_checks": after.get("retirement_checks"),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()



def _latest_serving_batch_id(cur) -> int:
    cur.execute(
        """SELECT publish_batch_id,COUNT(*) AS c
           FROM quick_check_current
           WHERE publish_batch_id IS NOT NULL
           GROUP BY publish_batch_id
           ORDER BY c DESC,publish_batch_id DESC
           LIMIT 1"""
    )
    row = cur.fetchone()
    if row and row.get("publish_batch_id") is not None:
        return int(row["publish_batch_id"])

    cur.execute(
        """SELECT batch_id
           FROM phase3_batch_result
           WHERE result_status IN ('QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS')
           ORDER BY updated_at DESC,batch_id DESC
           LIMIT 1"""
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("No published Phase 3 batch is available for a targeted Quick Check rebuild.")
    return int(row["batch_id"])


def _target_uom_verification(cur) -> list[dict[str, Any]]:
    result = []
    for expected in USER_CONFIRMED_UOM_REVIEW_20260926:
        ean = str(expected["ean_upc"])
        cur.execute(
            """SELECT ean_upc,article_number,main_article_number,selling_uom,base_uom,
                      base_qty_per_selling_unit,quick_check_status,blocking_reason
               FROM quick_check_current
               WHERE ean_upc=%s
               LIMIT 1""",
            (ean,),
        )
        row = cur.fetchone()
        actual_selling = str(row.get("selling_uom") or "").upper() if row else None
        expected_selling = str(expected["selling_uom_code"]).upper()
        actual_base = str(row.get("base_uom") or "").upper() if row and row.get("base_uom") else None
        expected_base = str(expected["base_uom_code"]).upper() if expected.get("base_uom_code") else None
        actual_factor = str(row.get("base_qty_per_selling_unit")) if row and row.get("base_qty_per_selling_unit") is not None else None
        expected_factor = str(expected.get("base_qty_per_selling_unit")) if expected.get("base_qty_per_selling_unit") is not None else None

        # Decimal(1) may render as 1.000000000000; compare numerically where present.
        factor_ok = actual_factor == expected_factor
        if actual_factor is not None and expected_factor is not None:
            try:
                factor_ok = float(actual_factor) == float(expected_factor)
            except Exception:
                factor_ok = actual_factor == expected_factor

        passed = bool(
            row
            and actual_selling == expected_selling
            and actual_base == expected_base
            and factor_ok
        )
        result.append(
            {
                "ean_upc": ean,
                "expected_selling_uom": expected_selling,
                "expected_base_uom": expected_base,
                "expected_factor": expected_factor,
                "actual_selling_uom": actual_selling,
                "actual_base_uom": actual_base,
                "actual_factor": actual_factor,
                "quick_check_status": row.get("quick_check_status") if row else None,
                "blocking_reason": row.get("blocking_reason") if row else None,
                "pass": passed,
            }
        )
    return result


def run_confirmed_uom_refresh(device: str) -> dict[str, Any]:
    """Apply the exact 22 user-confirmed Selling UOMs and rebuild Quick Check atomically.

    No arbitrary caller-supplied product values are accepted. The authoritative tuples
    are code-reviewed constants in manual_overrides.py.
    """

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # CRITICAL: CREATE TABLE causes an implicit MySQL commit, even when used
            # defensively. Perform schema bootstrap before the atomic transaction.
            ensure_override_table(cur)
            ensure_retirement_table(cur)
            conn.commit()

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE stage_name='POST_RAW_PIPELINE'
                     AND processing_status='STARTED'"""
            )
            if int((cur.fetchone() or {}).get("c") or 0) > 0:
                conn.rollback()
                raise RuntimeError(
                    "Server pipeline is currently processing; retry the confirmed UOM refresh later."
                )

            # Close the read transaction, then use one explicit transaction for all
            # authority writes + Quick Check rebuild + verification.
            conn.commit()
            conn.start_transaction()

            batch_id = _latest_serving_batch_id(cur)
            before = audit_product_identity(cur)

            overrides = apply_manual_upc_overrides(cur)
            retirements = apply_manual_upc_retirements(cur)
            if overrides.get("held"):
                raise RuntimeError(
                    "One or more confirmed manual overrides could not be applied: "
                    + str(overrides.get("held"))
                )

            # Re-evaluate per-UPC core holds from scratch for the currently published batch.
            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_status='RESOLVED',
                       detail_json=JSON_SET(
                         COALESCE(detail_json,JSON_OBJECT()),
                         '$.resolution',
                         'Superseded by v7.0.35 confirmed UOM serving refresh'
                       )
                   WHERE batch_id=%s
                     AND issue_status='OPEN'
                     AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
                (batch_id,),
            )
            prior_core_holds_resolved = int(cur.rowcount or 0)

            qc = rebuild_quick_check(cur, batch_id)
            after = audit_product_identity(cur)
            if not bool(after.get("pass")):
                raise RuntimeError(
                    "Product identity audit blocked the refreshed serving snapshot; "
                    f"blockers={after.get('blockers')}"
                )

            target_checks = _target_uom_verification(cur)
            failed_targets = [x for x in target_checks if not x.get("pass")]
            if failed_targets:
                raise RuntimeError(
                    "Confirmed UOM target verification failed; transaction rolled back. "
                    f"failed_targets={failed_targets}"
                )

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM qa_phase3_issue
                   WHERE batch_id=%s
                     AND issue_status='OPEN'
                     AND UPPER(severity) IN ('HIGH','CRITICAL')
                     AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'""",
                (batch_id,),
            )
            blocking = int((cur.fetchone() or {}).get("c") or 0)

            if blocking > 0 or int(qc.get("rows") or 0) == 0:
                status = "PHASE3_QA_HOLD"
            elif int(qc.get("hold") or 0) > 0:
                status = "QUICK_CHECK_READY_WITH_HOLDS"
            else:
                status = "QUICK_CHECK_READY"

            cur.execute(
                """UPDATE phase3_batch_result
                   SET quick_check_rows=%s,
                       quick_check_ready_rows=%s,
                       quick_check_hold_rows=%s,
                       blocking_issue_count=%s,
                       result_status=%s,
                       updated_at=CURRENT_TIMESTAMP(6)
                   WHERE batch_id=%s""",
                (
                    int(qc.get("rows") or 0),
                    int(qc.get("ready") or 0),
                    int(qc.get("hold") or 0),
                    blocking,
                    status,
                    batch_id,
                ),
            )
            cur.execute(
                """UPDATE ingest_batch
                   SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6)
                   WHERE batch_id=%s""",
                (status, batch_id),
            )

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM quick_check_current
                   WHERE quick_check_status='QA_HOLD'
                     AND COALESCE(blocking_reason,'') LIKE '%SELLING_UOM_MISSING%'"""
            )
            remaining_missing_selling_uom = int((cur.fetchone() or {}).get("c") or 0)

            conn.commit()
            return {
                "status": "COMMITTED",
                "device": device,
                "mode": "SERVER_SIDE_CONFIRMED_UOM_APPLY_AND_QC_REBUILD_TRANSACTION_SAFE",
                "publish_batch_id": batch_id,
                "target_count": len(USER_CONFIRMED_UOM_REVIEW_20260926),
                "prior_core_holds_resolved": prior_core_holds_resolved,
                "manual_overrides": overrides,
                "manual_retirements": retirements,
                "quick_check": qc,
                "phase3_status": status,
                "remaining_missing_selling_uom": remaining_missing_selling_uom,
                "target_checks": target_checks,
                "before_summary": before.get("summary"),
                "after_summary": after.get("summary"),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

def _safe_cost_target_checks(
    cur,
    before_diag: dict[str, Any],
) -> list[dict[str, Any]]:
    """Verify that each pre-refresh SAFE classification fixed its exact issue.

    Missing-cost repairs are allowed to reveal a new conversion hold. That is
    still a valid repair because the authoritative cost was restored without
    guessing the conversion.
    """

    checks: list[dict[str, Any]] = []
    for item in before_diag.get("items", []):
        if not bool(item.get("safe_to_auto_resolve_cost_hold")):
            continue

        ean = str(item.get("ean_upc") or "")
        missing_cls = (item.get("missing_cost_classification") or {}).get("classification")
        conversion_cls = (item.get("conversion_classification") or {}).get("classification")

        cur.execute(
            """SELECT ean_upc,quick_check_status,blocking_reason,
                      selling_uom,base_uom,base_qty_per_selling_unit,
                      current_cost_per_base_uom,current_cost_per_selling_unit,
                      cost_source,cost_date
               FROM quick_check_current
               WHERE ean_upc=%s
               LIMIT 1""",
            (ean,),
        )
        row = cur.fetchone()
        reasons = {
            x.strip()
            for x in str((row or {}).get("blocking_reason") or "").split(",")
            if x and x.strip()
        }

        missing_ok = True
        if missing_cls:
            missing_ok = bool(
                row
                and "CURRENT_COST_MISSING" not in reasons
                and row.get("current_cost_per_base_uom") is not None
            )

        conversion_ok = True
        if conversion_cls in {
            "DIRECT_COST_UOM_EQUALS_SELLING_UOM",
            "SERVING_CONVERSION_REBUILD_CANDIDATE",
        }:
            conversion_ok = bool(
                row
                and "COST_TO_SELLING_UOM_UNRESOLVED" not in reasons
                and row.get("current_cost_per_selling_unit") is not None
            )

        checks.append(
            {
                "ean_upc": ean,
                "before_missing_cost_classification": missing_cls,
                "before_conversion_classification": conversion_cls,
                "quick_check_status": row.get("quick_check_status") if row else None,
                "blocking_reason": row.get("blocking_reason") if row else None,
                "current_cost_per_base_uom": row.get("current_cost_per_base_uom") if row else None,
                "current_cost_per_selling_unit": row.get("current_cost_per_selling_unit") if row else None,
                "cost_source": row.get("cost_source") if row else None,
                "cost_date": row.get("cost_date") if row else None,
                "missing_cost_issue_resolved": missing_ok,
                "conversion_issue_resolved": conversion_ok,
                "pass": bool(row and missing_ok and conversion_ok),
            }
        )
    return checks


def run_safe_cost_refresh(device: str) -> dict[str, Any]:
    """Apply only evidence-backed cost repairs and rebuild current Quick Check.

    Scope:
    - authoritative current-cost lineage repair using existing receipt/report/OH rules
    - direct cost-to-selling factor 1 only when authoritative cost UOM equals
      POS Selling UOM exactly (PAC/PACK normalized)
    - no Base/Inventory UOM inference
    - no PACK-to-LB/EA or other cross-UOM inference
    """

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Keep DDL outside the business transaction for the same MySQL
            # implicit-commit reason fixed in v7.0.35.
            ensure_override_table(cur)
            ensure_retirement_table(cur)
            conn.commit()

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE stage_name='POST_RAW_PIPELINE'
                     AND processing_status='STARTED'"""
            )
            if int((cur.fetchone() or {}).get("c") or 0) > 0:
                conn.rollback()
                raise RuntimeError(
                    "Server pipeline is currently processing; retry the safe cost refresh later."
                )

            conn.commit()
            conn.start_transaction()

            batch_id = _latest_serving_batch_id(cur)
            before_diag = diagnose_global_cost_holds(cur)
            before_summary = before_diag.get("summary") or {}
            before_safe_count = int(
                before_summary.get("safe_to_auto_resolve_cost_hold_count") or 0
            )

            identity_before = audit_product_identity(cur)
            if not bool(identity_before.get("pass")):
                raise RuntimeError(
                    "Pre-refresh product identity audit is blocked; cost refresh refused. "
                    f"blockers={identity_before.get('blockers')}"
                )

            # Reapply user authority first so automatic cost repair operates
            # against the authoritative product/UOM identity.
            overrides = apply_manual_upc_overrides(cur)
            retirements = apply_manual_upc_retirements(cur)
            if overrides.get("held"):
                raise RuntimeError(
                    "One or more confirmed manual overrides could not be applied: "
                    + str(overrides.get("held"))
                )

            cost_repair = repair_current_active_cost(cur, batch_id)

            # Rebuild current per-UPC core holds from the resulting evidence state.
            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_status='RESOLVED',
                       detail_json=JSON_SET(
                         COALESCE(detail_json,JSON_OBJECT()),
                         '$.resolution',
                         'Superseded by v7.0.37 safe cost serving refresh'
                       )
                   WHERE batch_id=%s
                     AND issue_status='OPEN'
                     AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
                (batch_id,),
            )
            prior_core_holds_resolved = int(cur.rowcount or 0)

            qc = rebuild_quick_check(cur, batch_id)
            identity_after = audit_product_identity(cur)
            if not bool(identity_after.get("pass")):
                raise RuntimeError(
                    "Product identity audit blocked the refreshed serving snapshot; "
                    f"blockers={identity_after.get('blockers')}"
                )

            target_checks = _safe_cost_target_checks(cur, before_diag)
            failed_targets = [x for x in target_checks if not x.get("pass")]
            if failed_targets:
                raise RuntimeError(
                    "Safe cost target verification failed; transaction rolled back. "
                    f"failed_targets={failed_targets}"
                )

            after_diag = diagnose_global_cost_holds(cur)
            after_summary = after_diag.get("summary") or {}

            before_cost_holds = int(before_summary.get("cost_related_hold_rows") or 0)
            after_cost_holds = int(after_summary.get("cost_related_hold_rows") or 0)
            if after_cost_holds > before_cost_holds:
                raise RuntimeError(
                    "Cost-related hold count increased after safe refresh; transaction rolled back. "
                    f"before={before_cost_holds}; after={after_cost_holds}"
                )

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM qa_phase3_issue
                   WHERE batch_id=%s
                     AND issue_status='OPEN'
                     AND UPPER(severity) IN ('HIGH','CRITICAL')
                     AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'""",
                (batch_id,),
            )
            blocking = int((cur.fetchone() or {}).get("c") or 0)

            if blocking > 0 or int(qc.get("rows") or 0) == 0:
                status = "PHASE3_QA_HOLD"
            elif int(qc.get("hold") or 0) > 0:
                status = "QUICK_CHECK_READY_WITH_HOLDS"
            else:
                status = "QUICK_CHECK_READY"

            cur.execute(
                """UPDATE phase3_batch_result
                   SET quick_check_rows=%s,
                       quick_check_ready_rows=%s,
                       quick_check_hold_rows=%s,
                       blocking_issue_count=%s,
                       result_status=%s,
                       updated_at=CURRENT_TIMESTAMP(6)
                   WHERE batch_id=%s""",
                (
                    int(qc.get("rows") or 0),
                    int(qc.get("ready") or 0),
                    int(qc.get("hold") or 0),
                    blocking,
                    status,
                    batch_id,
                ),
            )
            cur.execute(
                """UPDATE ingest_batch
                   SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6)
                   WHERE batch_id=%s""",
                (status, batch_id),
            )

            conn.commit()
            return {
                "status": "COMMITTED",
                "device": device,
                "mode": "SERVER_SIDE_SAFE_COST_REPAIR_AND_QC_REBUILD_V7037",
                "publish_batch_id": batch_id,
                "before_safe_candidate_count": before_safe_count,
                "verified_target_count": len(target_checks),
                "prior_core_holds_resolved": prior_core_holds_resolved,
                "cost_repair": cost_repair,
                "quick_check": qc,
                "phase3_status": status,
                "before_cost_summary": before_summary,
                "after_cost_summary": after_summary,
                "target_checks": target_checks,
                "identity_before_summary": identity_before.get("summary"),
                "identity_after_summary": identity_after.get("summary"),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

