from __future__ import annotations

from typing import Any

from db import db_conn
from manual_overrides import (
    USER_CONFIRMED_UOM_REVIEW_20260926,
    apply_manual_upc_overrides,
    apply_manual_upc_retirements,
)
from product_identity_audit import audit_product_identity
from phase3 import rebuild_quick_check


def _retirement_ok(row: dict[str, Any]) -> bool:
    return (
        (row.get("record_status") is None or str(row.get("record_status")).upper() == "RETIRED")
        and int(row.get("active_article_links") or 0) == 0
        and int(row.get("active_uom_rows") or 0) == 0
        and int(row.get("quick_check_rows") or 0) == 0
    )


def run_manual_authority_refresh(device: str) -> dict[str, Any]:
    """Apply only pre-defined, user-confirmed identity/UOM authority server-side.

    This is intentionally narrow: the caller cannot submit arbitrary UPC/article/UOM
    values. It re-applies the authority already encoded in manual_overrides.py.
    """

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Do not race the server-side post-RAW worker.
            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE stage_name='POST_RAW_PIPELINE'
                     AND processing_status='STARTED'"""
            )
            if int((cur.fetchone() or {}).get("c") or 0) > 0:
                raise RuntimeError(
                    "Server pipeline is currently processing a batch; retry the "
                    "manual authority refresh after processing finishes."
                )

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
                "mode": "SERVER_SIDE_API_ONLY_NO_QC_REBUILD",
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
    """Apply the exact 22 user-confirmed UOMs and rebuild current Quick Check atomically.

    No arbitrary caller-supplied product values are accepted. The authoritative tuples
    are code-reviewed constants in manual_overrides.py.
    """

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE stage_name='POST_RAW_PIPELINE'
                     AND processing_status='STARTED'"""
            )
            if int((cur.fetchone() or {}).get("c") or 0) > 0:
                raise RuntimeError(
                    "Server pipeline is currently processing; retry the confirmed UOM refresh later."
                )

            batch_id = _latest_serving_batch_id(cur)
            before = audit_product_identity(cur)

            cur.execute("SAVEPOINT confirmed_uom_refresh")
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
                         'Superseded by v7.0.34 confirmed UOM serving refresh'
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
                cur.execute("ROLLBACK TO SAVEPOINT confirmed_uom_refresh")
                cur.execute("RELEASE SAVEPOINT confirmed_uom_refresh")
                raise RuntimeError(
                    "Product identity audit blocked the refreshed serving snapshot; "
                    f"blockers={after.get('blockers')}"
                )

            target_checks = _target_uom_verification(cur)
            failed_targets = [x for x in target_checks if not x.get("pass")]
            if failed_targets:
                cur.execute("ROLLBACK TO SAVEPOINT confirmed_uom_refresh")
                cur.execute("RELEASE SAVEPOINT confirmed_uom_refresh")
                raise RuntimeError(
                    "Confirmed UOM target verification failed; serving snapshot restored. "
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

            cur.execute("RELEASE SAVEPOINT confirmed_uom_refresh")
            conn.commit()
            return {
                "status": "COMMITTED",
                "device": device,
                "mode": "SERVER_SIDE_CONFIRMED_UOM_APPLY_AND_QC_REBUILD",
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
