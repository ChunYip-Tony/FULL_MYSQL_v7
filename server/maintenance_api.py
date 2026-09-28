from __future__ import annotations

from decimal import Decimal
from typing import Any

from db import db_conn
from manual_overrides import (
    USER_CONFIRMED_UOM_REVIEW_20260926,
    USER_CONFIRMED_COST_SELLING_CONVERSIONS_20260926,
    USER_CONFIRMED_FAMILY_COSTS_20260926,
    USER_CONFIRMED_OPERATIONAL_UOM_BASIS_20260927,
    ensure_override_table,
    ensure_retirement_table,
    ensure_cost_conversion_table,
    ensure_family_cost_table,
    apply_manual_upc_overrides,
    apply_manual_upc_retirements,
    apply_manual_cost_conversions,
    apply_manual_family_costs,
    apply_manual_family_subarticles,
)
from product_identity_audit import audit_product_identity
from current_active_cost_repair import repair_current_active_cost, _scan_and_backfill_oh_cost, _backfill_receipt_cost, _backfill_official_cost, _relink_target_company_rows, _relink_existing_cost_observations
from global_cost_hold_diagnostic import diagnose_global_cost_holds
from normalize import _preload_article_manual_authority
from phase3 import rebuild_quick_check, refresh_quick_check_subset, repair_company_cost_uom_observations, _latest_cost, _norm_cost_serving_uom, _process_on_hand, relink_history, resolve_late_identity_issues


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
            ensure_cost_conversion_table(cur)
            ensure_family_cost_table(cur)
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
            conversions = apply_manual_cost_conversions(cur)
            family_costs = apply_manual_family_costs(cur)
            family_subarticles = apply_manual_family_subarticles(cur)

            if overrides.get("held"):
                raise RuntimeError(
                    "One or more confirmed manual overrides could not be applied: "
                    + str(overrides.get("held"))
                )
            if conversions.get("held"):
                raise RuntimeError(
                    "One or more confirmed cost conversions could not be applied: "
                    + str(conversions.get("held"))
                )
            if family_costs.get("held"):
                raise RuntimeError(
                    "One or more confirmed family costs could not be applied: "
                    + str(family_costs.get("held"))
                )
            if family_subarticles.get("held"):
                raise RuntimeError(
                    "One or more confirmed family subarticles could not be applied: "
                    + str(family_subarticles.get("held"))
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
                "manual_cost_conversions": conversions,
                "manual_family_costs": family_costs,
                "manual_family_subarticles": family_subarticles,
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



def run_cost_authority_refresh(device: str) -> dict[str, Any]:
    """Materialize OH cost evidence and refresh only families affected by authority order.

    Authority:
      1) valid 101/107/109 receipt valuation
      2) explicit supported OH-report cost
      3) Live/Fresh/Frozen official report cost
      4) explicit user-confirmed fallback
    """
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                     AND processing_status IN ('QUEUED','STARTED')"""
            )
            if int((cur.fetchone() or {}).get("c") or 0) > 0:
                conn.rollback()
                raise RuntimeError(
                    "Server pipeline is currently processing; cost-authority refresh "
                    "is blocked to prevent concurrent serving writes."
                )

            conn.commit()
            conn.start_transaction()
            batch_id = _latest_serving_batch_id(cur)

            cur.execute(
                """SELECT DISTINCT family_id
                   FROM quick_check_current
                   WHERE quick_check_status IN ('READY','QA_HOLD')
                     AND family_id IS NOT NULL
                   ORDER BY family_id"""
            )
            active_family_ids = [
                int(row["family_id"]) for row in cur.fetchall()
                if row.get("family_id") is not None
            ]
            if not active_family_ids:
                raise RuntimeError("No current-active families are available.")

            # Exhaust every configured authoritative source before deciding
            # that a current-active family still has no usable cost.
            #
            # Identity relinking comes first so receipt/OH/official observations
            # materialize against the correct Family.
            company_rows_relinked = _relink_target_company_rows(
                cur, active_family_ids
            )
            existing_cost_observations_relinked = _relink_existing_cost_observations(
                cur, active_family_ids
            )

            # Materialize in the same order as cost authority:
            # 1) receipt 101/107/109
            # 2) OH cost: explicit unit cost or Total Value / Unrestricted Qty
            # 3) Live/Fresh/Frozen official cost
            receipt_backfill_rows = _backfill_receipt_cost(
                cur, active_family_ids
            )
            oh_backfill = _scan_and_backfill_oh_cost(
                cur, active_family_ids
            )
            official_backfill_rows = _backfill_official_cost(
                cur, active_family_ids
            )

            ph = ",".join(["%s"] * len(active_family_ids))
            cur.execute(
                f"""SELECT ean_upc,family_id,main_article_number,cost_source,cost_date,
                           current_cost_per_base_uom,current_cost_per_selling_unit,
                           base_uom,quick_check_status,blocking_reason
                    FROM quick_check_current
                    WHERE family_id IN ({ph})
                      AND quick_check_status IN ('READY','QA_HOLD')
                    ORDER BY family_id,ean_upc""",
                tuple(active_family_ids),
            )
            before_rows = cur.fetchall()

            expected_by_family: dict[int, dict[str, Any] | None] = {}
            affected_family_ids: set[int] = set()
            before_mismatches: list[dict[str, Any]] = []
            for row in before_rows:
                fid = int(row["family_id"])
                if fid not in expected_by_family:
                    expected_by_family[fid] = _latest_cost(cur, fid)
                expected = expected_by_family[fid]
                expected_source = expected.get("source") if expected else None
                expected_amount = (
                    Decimal(str(expected.get("cost_per_base")))
                    if expected and expected.get("cost_per_base") is not None
                    else None
                )
                expected_date = expected.get("date") if expected else None
                expected_uom = (
                    str(expected.get("base_uom") or "").upper()
                    if expected else ""
                )
                actual_source = row.get("cost_source")
                actual_amount = (
                    Decimal(str(row.get("current_cost_per_base_uom")))
                    if row.get("current_cost_per_base_uom") is not None
                    else None
                )
                actual_date = row.get("cost_date")
                actual_uom = str(row.get("base_uom") or "").upper()
                mismatch = (
                    expected_source != actual_source
                    or expected_amount != actual_amount
                    or expected_date != actual_date
                    or (
                        expected_uom
                        and actual_uom
                        and expected_uom != actual_uom
                    )
                )
                if mismatch:
                    affected_family_ids.add(fid)
                    before_mismatches.append(
                        {
                            "ean_upc": str(row["ean_upc"]),
                            "family_id": fid,
                            "main_article_number": row.get("main_article_number"),
                            "before_cost_source": actual_source,
                            "expected_cost_source": expected_source,
                            "before_cost_amount": actual_amount,
                            "expected_cost_amount": expected_amount,
                            "before_cost_date": actual_date,
                            "expected_cost_date": expected_date,
                            "before_cost_uom": actual_uom or None,
                            "expected_cost_uom": expected_uom or None,
                        }
                    )

            targeted = None
            if affected_family_ids:
                targeted = refresh_quick_check_subset(
                    cur,
                    batch_id,
                    family_ids=sorted(affected_family_ids),
                )

            after_mismatches: list[dict[str, Any]] = []
            if affected_family_ids:
                target_ids = sorted(affected_family_ids)
                tph = ",".join(["%s"] * len(target_ids))
                cur.execute(
                    f"""SELECT ean_upc,family_id,main_article_number,cost_source,cost_date,
                               current_cost_per_base_uom,current_cost_per_selling_unit,
                               base_uom,quick_check_status,blocking_reason
                        FROM quick_check_current
                        WHERE family_id IN ({tph})
                          AND quick_check_status IN ('READY','QA_HOLD')
                        ORDER BY family_id,ean_upc""",
                    tuple(target_ids),
                )
                for row in cur.fetchall():
                    fid = int(row["family_id"])
                    expected = _latest_cost(cur, fid)
                    expected_source = expected.get("source") if expected else None
                    expected_amount = (
                        Decimal(str(expected.get("cost_per_base")))
                        if expected and expected.get("cost_per_base") is not None
                        else None
                    )
                    expected_date = expected.get("date") if expected else None
                    expected_uom = (
                        str(expected.get("base_uom") or "").upper()
                        if expected else ""
                    )
                    actual_amount = (
                        Decimal(str(row.get("current_cost_per_base_uom")))
                        if row.get("current_cost_per_base_uom") is not None
                        else None
                    )
                    actual_uom = str(row.get("base_uom") or "").upper()
                    mismatch = (
                        row.get("cost_source") != expected_source
                        or actual_amount != expected_amount
                        or row.get("cost_date") != expected_date
                        or (
                            expected_uom
                            and actual_uom
                            and expected_uom != actual_uom
                        )
                    )
                    if mismatch:
                        after_mismatches.append(
                            {
                                "ean_upc": str(row["ean_upc"]),
                                "family_id": fid,
                                "main_article_number": row.get("main_article_number"),
                                "actual_cost_source": row.get("cost_source"),
                                "expected_cost_source": expected_source,
                                "actual_cost_amount": actual_amount,
                                "expected_cost_amount": expected_amount,
                                "actual_cost_date": row.get("cost_date"),
                                "expected_cost_date": expected_date,
                                "actual_cost_uom": actual_uom or None,
                                "expected_cost_uom": expected_uom or None,
                            }
                        )

            if after_mismatches:
                raise RuntimeError(
                    "Cost-authority targeted refresh verification failed; "
                    "transaction rolled back. mismatches=" + str(after_mismatches[:20])
                )

            cur.execute(
                """SELECT COUNT(*) AS serving_rows_total,
                          SUM(CASE WHEN quick_check_status='HISTORICAL_ONLY' THEN 1 ELSE 0 END) AS historical_rows,
                          SUM(CASE WHEN quick_check_status IN ('READY','QA_HOLD') THEN 1 ELSE 0 END) AS current_active_rows,
                          SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS current_ready_rows,
                          SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS current_hold_rows
                   FROM quick_check_current"""
            )
            raw_scope = cur.fetchone() or {}
            scope = {
                k: int(raw_scope.get(k) or 0)
                for k in (
                    "serving_rows_total",
                    "historical_rows",
                    "current_active_rows",
                    "current_ready_rows",
                    "current_hold_rows",
                )
            }

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

            if blocking > 0 or scope["current_active_rows"] == 0:
                status = "PHASE3_QA_HOLD"
            elif scope["current_hold_rows"] > 0:
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
                    scope["current_active_rows"],
                    scope["current_ready_rows"],
                    scope["current_hold_rows"],
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
                "mode": "TARGETED_COST_AUTHORITY_REFRESH",
                "authority_order": [
                    "MOVEMENT_RECEIPT_VALUATION_101_107_109",
                    "ON_HAND_EXPLICIT_COST_FALLBACK",
                    "LIVE_FRESH_FROZEN_OFFICIAL_COST",
                    "USER_CONFIRMED_FAMILY_COST",
                ],
                "publish_batch_id": batch_id,
                "active_family_count": len(active_family_ids),
                "company_rows_relinked": company_rows_relinked,
                "existing_cost_observations_relinked":
                    existing_cost_observations_relinked,
                "receipt_backfill_rows": receipt_backfill_rows,
                "oh_backfill": oh_backfill,
                "official_backfill_rows": official_backfill_rows,
                "source_exhaustion_order": [
                    "RELINK_IDENTITY",
                    "MATERIALIZE_RECEIPT_101_107_109",
                    "MATERIALIZE_ON_HAND_COST_EXPLICIT_OR_TOTAL_VALUE_DERIVED",
                    "MATERIALIZE_LIVE_FRESH_FROZEN_OFFICIAL_COST",
                    "REFRESH_AFFECTED_QUICK_CHECK_FAMILIES",
                ],
                "affected_family_count": len(affected_family_ids),
                "affected_family_ids": sorted(affected_family_ids),
                "before_mismatch_count": len(before_mismatches),
                "before_mismatches": before_mismatches,
                "targeted_refresh": targeted,
                "after_mismatch_count": len(after_mismatches),
                "quick_check_scope": scope,
                "phase3_status": status,
                "blocking_issue_count": blocking,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def run_operational_uom_quick_check_refresh(device: str) -> dict[str, Any]:
    """Refresh only Quick Check rows affected by code-reviewed operational-UOM authority.

    This is a serving-layer refresh only. It does not re-ingest RAW files, replay
    Phase 3 history, or clean-replace the global Quick Check snapshot.
    """

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM pipeline_run
                   WHERE stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                     AND processing_status IN ('QUEUED','STARTED')"""
            )
            if int((cur.fetchone() or {}).get("c") or 0) > 0:
                conn.rollback()
                raise RuntimeError(
                    "Server pipeline is currently processing; targeted Quick Check "
                    "refresh is blocked to prevent concurrent serving writes."
                )

            conn.commit()
            conn.start_transaction()
            batch_id = _latest_serving_batch_id(cur)

            main_articles = sorted({
                str(x["main_article_number"])
                for x in USER_CONFIRMED_OPERATIONAL_UOM_BASIS_20260927
            })
            if not main_articles:
                raise RuntimeError("No code-reviewed operational-UOM targets are configured.")

            ph = ",".join(["%s"] * len(main_articles))
            cur.execute(
                f"""SELECT family_id,main_article_number
                    FROM product_family
                    WHERE main_article_number IN ({ph})
                    ORDER BY family_id""",
                tuple(main_articles),
            )
            family_rows = cur.fetchall()
            found_main = {str(x["main_article_number"]) for x in family_rows}
            missing_main = [x for x in main_articles if x not in found_main]
            if missing_main:
                raise RuntimeError(
                    "Operational-UOM target family identity is unresolved: "
                    + ",".join(missing_main)
                )

            family_ids = sorted({int(x["family_id"]) for x in family_rows})

            before_rows = {}
            cur.execute(
                f"""SELECT ean_upc,family_id,main_article_number,current_oh,current_oh_uom,
                           family_movement_7d,family_movement_uom,quick_check_status,blocking_reason,
                           published_at
                    FROM quick_check_current
                    WHERE family_id IN ({','.join(['%s'] * len(family_ids))})
                    ORDER BY ean_upc""",
                tuple(family_ids),
            )
            for row in cur.fetchall():
                before_rows[str(row["ean_upc"])] = row

            targeted = refresh_quick_check_subset(
                cur,
                batch_id,
                family_ids=family_ids,
            )

            cur.execute(
                f"""SELECT ean_upc,family_id,main_article_number,current_oh,current_oh_uom,
                           family_movement_7d,family_movement_uom,quick_check_status,blocking_reason,
                           published_at
                    FROM quick_check_current
                    WHERE family_id IN ({','.join(['%s'] * len(family_ids))})
                    ORDER BY ean_upc""",
                tuple(family_ids),
            )
            after_rows = cur.fetchall()

            authority_by_main = {
                str(x["main_article_number"]): x
                for x in USER_CONFIRMED_OPERATIONAL_UOM_BASIS_20260927
            }
            target_checks = []
            failed = []
            for row in after_rows:
                authority = authority_by_main.get(str(row.get("main_article_number") or ""))
                expected_uom = (
                    str(authority.get("operational_uom_code") or "").upper()
                    if authority else None
                )
                reasons = {
                    x.strip()
                    for x in str(row.get("blocking_reason") or "").split(",")
                    if x and x.strip()
                }
                active = str(row.get("quick_check_status") or "") in {"READY", "QA_HOLD"}
                oh_uom_ok = (
                    (not active)
                    or row.get("current_oh") is None
                    or str(row.get("current_oh_uom") or "").upper() == expected_uom
                )
                movement_uom_ok = (
                    row.get("family_movement_7d") is None
                    or str(row.get("family_movement_uom") or "").upper() == expected_uom
                )
                rollforward_hold_cleared = "OH_MOVEMENT_ROLLFORWARD_BLOCKED" not in reasons
                passed = bool(authority and oh_uom_ok and movement_uom_ok and rollforward_hold_cleared)
                check = {
                    "ean_upc": str(row["ean_upc"]),
                    "family_id": int(row["family_id"]),
                    "main_article_number": str(row["main_article_number"]),
                    "expected_operational_uom": expected_uom,
                    "current_oh": row.get("current_oh"),
                    "current_oh_uom": row.get("current_oh_uom"),
                    "family_movement_7d": row.get("family_movement_7d"),
                    "family_movement_uom": row.get("family_movement_uom"),
                    "quick_check_status": row.get("quick_check_status"),
                    "blocking_reason": row.get("blocking_reason"),
                    "pass": passed,
                }
                target_checks.append(check)
                if not passed:
                    failed.append(check)

            if failed:
                raise RuntimeError(
                    "Targeted operational-UOM Quick Check verification failed; "
                    "transaction rolled back. failed=" + str(failed)
                )

            cur.execute(
                """SELECT COUNT(*) AS serving_rows_total,
                          SUM(CASE WHEN quick_check_status='HISTORICAL_ONLY' THEN 1 ELSE 0 END) AS historical_rows,
                          SUM(CASE WHEN quick_check_status IN ('READY','QA_HOLD') THEN 1 ELSE 0 END) AS current_active_rows,
                          SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS current_ready_rows,
                          SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS current_hold_rows
                   FROM quick_check_current"""
            )
            scope = cur.fetchone() or {}
            scope = {
                k: int(scope.get(k) or 0)
                for k in (
                    "serving_rows_total",
                    "historical_rows",
                    "current_active_rows",
                    "current_ready_rows",
                    "current_hold_rows",
                )
            }

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

            if blocking > 0 or scope["current_active_rows"] == 0:
                status = "PHASE3_QA_HOLD"
            elif scope["current_hold_rows"] > 0:
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
                    scope["current_active_rows"],
                    scope["current_ready_rows"],
                    scope["current_hold_rows"],
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
                "mode": "TARGETED_OPERATIONAL_UOM_QUICK_CHECK_REFRESH",
                "publish_batch_id": batch_id,
                "target_family_ids": family_ids,
                "target_main_articles": main_articles,
                "targeted_refresh": targeted,
                "target_checks": target_checks,
                "before": before_rows,
                "quick_check_scope": scope,
                "phase3_status": status,
                "blocking_issue_count": blocking,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


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
    """Apply the exact user-confirmed Selling UOM set and rebuild Quick Check atomically.

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
            ensure_cost_conversion_table(cur)
            ensure_family_cost_table(cur)
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
            conversions = apply_manual_cost_conversions(cur)
            family_costs = apply_manual_family_costs(cur)
            family_subarticles = apply_manual_family_subarticles(cur)
            if overrides.get("held"):
                raise RuntimeError(
                    "One or more confirmed manual overrides could not be applied: "
                    + str(overrides.get("held"))
                )
            if conversions.get("held"):
                raise RuntimeError(
                    "One or more confirmed cost conversions could not be applied: "
                    + str(conversions.get("held"))
                )
            if family_costs.get("held"):
                raise RuntimeError(
                    "One or more confirmed family costs could not be applied: "
                    + str(family_costs.get("held"))
                )
            if family_subarticles.get("held"):
                raise RuntimeError(
                    "One or more confirmed family subarticles could not be applied: "
                    + str(family_subarticles.get("held"))
                )

            if family_costs.get("held"):
                raise RuntimeError("One or more confirmed family costs could not be applied: " + str(family_costs.get("held")))
            if family_subarticles.get("held"):
                raise RuntimeError("One or more confirmed family subarticles could not be applied: " + str(family_subarticles.get("held")))

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
                "manual_cost_conversions": conversions,
                "manual_family_costs": family_costs,
                "manual_family_subarticles": family_subarticles,
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


def run_on_hand_repair(device: str) -> dict[str, Any]:
    """Reparse authoritative ON_HAND RAW with corrected SAP header semantics.

    The repair is deterministic and source-backed:
    - quantity = exact Unrestr./Unrestricted/On Hand field
    - quantity UOM = exact BUn/Base UOM/UOM field
    - article/family links are resolved from current confirmed identity
    - RAW rows are never rewritten
    - Quick Check is rebuilt atomically
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
                conn.rollback()
                raise RuntimeError(
                    "Server pipeline is currently processing; retry the ON_HAND repair later."
                )

            conn.commit()
            conn.start_transaction()

            batch_id = _latest_serving_batch_id(cur)

            cur.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN family_id IS NOT NULL THEN 1 ELSE 0 END) AS family_mapped,
                          SUM(CASE WHEN uom_code IS NOT NULL AND TRIM(uom_code)<>'' THEN 1 ELSE 0 END) AS uom_present,
                          SUM(CASE WHEN on_hand_quantity IS NOT NULL THEN 1 ELSE 0 END) AS qty_present
                   FROM inventory_observation"""
            )
            before_inventory = cur.fetchone() or {}

            cur.execute(
                """SELECT batch_id,file_id,original_filename,source_type,coverage_start_date,coverage_end_date,
                          header_period_start_date,header_period_end_date,report_generated_at,
                          upload_timestamp,filename_date_candidate
                   FROM ingest_file
                   WHERE source_type='on_hand'
                   ORDER BY file_id"""
            )
            files = cur.fetchall()
            if not files:
                raise RuntimeError("No ON_HAND source file is available to repair.")

            reparsed_rows = 0
            file_results = []
            for f in files:
                n = int(_process_on_hand(cur, int(f["batch_id"]), f) or 0)
                reparsed_rows += n
                file_results.append(
                    {
                        "file_id": int(f["file_id"]),
                        "filename": f.get("original_filename"),
                        "rows_reparsed": n,
                    }
                )

            relink_history(cur)

            qc = rebuild_quick_check(cur, batch_id)

            cur.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN family_id IS NOT NULL THEN 1 ELSE 0 END) AS family_mapped,
                          SUM(CASE WHEN article_id IS NOT NULL THEN 1 ELSE 0 END) AS article_mapped,
                          SUM(CASE WHEN uom_code IS NOT NULL AND TRIM(uom_code)<>'' THEN 1 ELSE 0 END) AS uom_present,
                          SUM(CASE WHEN on_hand_quantity IS NOT NULL THEN 1 ELSE 0 END) AS qty_present,
                          MAX(observation_date) AS latest_observation_date
                   FROM inventory_observation"""
            )
            after_inventory = cur.fetchone() or {}

            cur.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN current_oh IS NOT NULL THEN 1 ELSE 0 END) AS with_oh,
                          SUM(CASE WHEN current_oh IS NOT NULL
                                        AND current_oh_uom IS NOT NULL
                                        AND TRIM(current_oh_uom)<>''
                                   THEN 1 ELSE 0 END) AS with_oh_and_uom,
                          SUM(CASE WHEN quick_check_status='READY'
                                        AND current_oh IS NOT NULL
                                        AND current_oh_uom IS NOT NULL
                                        AND TRIM(current_oh_uom)<>''
                                   THEN 1 ELSE 0 END) AS ready_with_oh
                   FROM quick_check_current"""
            )
            serving = cur.fetchone() or {}

            identity = audit_product_identity(cur)
            if not bool(identity.get("pass")):
                raise RuntimeError(
                    "Product identity audit blocked the ON_HAND repair; "
                    f"blockers={identity.get('blockers')}"
                )

            family_mapped = int(after_inventory.get("family_mapped") or 0)
            uom_present = int(after_inventory.get("uom_present") or 0)
            with_oh_and_uom = int(serving.get("with_oh_and_uom") or 0)
            if reparsed_rows <= 0 or family_mapped <= 0 or uom_present <= 0 or with_oh_and_uom <= 0:
                raise RuntimeError(
                    "ON_HAND repair verification failed; transaction rolled back. "
                    f"reparsed_rows={reparsed_rows}, family_mapped={family_mapped}, "
                    f"uom_present={uom_present}, with_oh_and_uom={with_oh_and_uom}"
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
                phase3_status = "PHASE3_QA_HOLD"
            elif int(qc.get("hold") or 0) > 0:
                phase3_status = "QUICK_CHECK_READY_WITH_HOLDS"
            else:
                phase3_status = "QUICK_CHECK_READY"

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
                    phase3_status,
                    batch_id,
                ),
            )
            cur.execute(
                """UPDATE ingest_batch
                   SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6)
                   WHERE batch_id=%s""",
                (phase3_status, batch_id),
            )

            conn.commit()
            return {
                "status": "COMMITTED",
                "device": device,
                "mode": "SERVER_SIDE_ON_HAND_RAW_REPARSE_RELINK_QC_REBUILD",
                "publish_batch_id": batch_id,
                "files": file_results,
                "rows_reparsed": reparsed_rows,
                "before_inventory": before_inventory,
                "after_inventory": after_inventory,
                "quick_check": qc,
                "quick_check_oh": serving,
                "phase3_status": phase3_status,
                "identity_summary": identity.get("summary"),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()




def run_article_manual_roster_repair(device: str) -> dict[str, Any]:
    """Re-run authoritative Article Manual roster preload with formatted UPC support.

    This repairs identities skipped when Article Manual UPC cells were visually
    formatted with spaces/hyphens (for example 4 71106163078 0). It does not
    invent digits or infer fuzzy barcode substitutions.
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
                conn.rollback()
                raise RuntimeError(
                    "Server pipeline is currently processing; retry the Article Manual repair later."
                )

            cur.execute(
                """SELECT batch_id
                   FROM ingest_file
                   WHERE source_type='article_manual'
                   ORDER BY file_id DESC
                   LIMIT 1"""
            )
            identity_row = cur.fetchone()
            if not identity_row:
                conn.rollback()
                raise RuntimeError("No Article Manual source is available.")

            identity_batch_id = int(identity_row["batch_id"])
            serving_batch_id = _latest_serving_batch_id(cur)

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM inventory_observation
                   WHERE article_id IS NULL OR family_id IS NULL"""
            )
            before_unmapped = int((cur.fetchone() or {}).get("c") or 0)

            cur.execute(
                """SELECT article_number,on_hand_quantity,uom_code,observation_date,file_id
                   FROM inventory_observation
                   WHERE article_id IS NULL OR family_id IS NULL
                   ORDER BY observation_date DESC,file_id DESC,raw_id DESC"""
            )
            before_rows = cur.fetchall()

            conn.commit()
            conn.start_transaction()

            preload = _preload_article_manual_authority(cur, identity_batch_id)

            # Article Manual is source authority, but explicit user-confirmed
            # overrides/retirements outrank automated/source replay. Reapply the
            # same final authority lock used by normal Phase 3 before and after
            # rebuilding serving data so a repair can never resurrect a retired
            # UPC such as 26510500000.
            override_lock_pre = apply_manual_upc_overrides(cur)
            retirement_lock_pre = apply_manual_upc_retirements(cur)

            relink_history(cur)
            late_identity = resolve_late_identity_issues(cur, serving_batch_id)
            qc = rebuild_quick_check(cur, serving_batch_id)

            override_lock_final = apply_manual_upc_overrides(cur)
            retirement_lock_final = apply_manual_upc_retirements(cur)

            identity = audit_product_identity(cur)
            if not bool(identity.get("pass")):
                raise RuntimeError(
                    "Product identity audit blocked the Article Manual roster repair; "
                    f"blockers={identity.get('blockers')}"
                )

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM inventory_observation
                   WHERE article_id IS NULL OR family_id IS NULL"""
            )
            after_unmapped = int((cur.fetchone() or {}).get("c") or 0)

            cur.execute(
                """SELECT article_number,on_hand_quantity,uom_code,observation_date,file_id
                   FROM inventory_observation
                   WHERE article_id IS NULL OR family_id IS NULL
                   ORDER BY observation_date DESC,file_id DESC,raw_id DESC"""
            )
            after_rows = cur.fetchall()

            if before_unmapped > 0 and after_unmapped >= before_unmapped:
                raise RuntimeError(
                    "Article Manual roster repair did not improve unresolved OH identity; "
                    f"before={before_unmapped}, after={after_unmapped}"
                )

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM qa_phase3_issue
                   WHERE batch_id=%s
                     AND issue_status='OPEN'
                     AND UPPER(severity) IN ('HIGH','CRITICAL')
                     AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'""",
                (serving_batch_id,),
            )
            blocking = int((cur.fetchone() or {}).get("c") or 0)
            if blocking > 0 or int(qc.get("rows") or 0) == 0:
                phase3_status = "PHASE3_QA_HOLD"
            elif int(qc.get("hold") or 0) > 0:
                phase3_status = "QUICK_CHECK_READY_WITH_HOLDS"
            else:
                phase3_status = "QUICK_CHECK_READY"

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
                    phase3_status,
                    serving_batch_id,
                ),
            )
            cur.execute(
                """UPDATE ingest_batch
                   SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6)
                   WHERE batch_id=%s""",
                (phase3_status, serving_batch_id),
            )

            conn.commit()
            return {
                "status": "COMMITTED",
                "device": device,
                "mode": "ARTICLE_MANUAL_FORMATTED_UPC_ROSTER_REPAIR",
                "identity_batch_id": identity_batch_id,
                "publish_batch_id": serving_batch_id,
                "before_unmapped_inventory_count": before_unmapped,
                "after_unmapped_inventory_count": after_unmapped,
                "inventory_rows_relinked": before_unmapped - after_unmapped,
                "before_unmapped_inventory": before_rows,
                "after_unmapped_inventory": after_rows,
                "article_manual_preload": preload,
                "user_authority_lock_pre": {
                    "overrides": override_lock_pre,
                    "retirements": retirement_lock_pre,
                },
                "user_authority_lock_final": {
                    "overrides": override_lock_final,
                    "retirements": retirement_lock_final,
                },
                "late_identity": late_identity,
                "quick_check": qc,
                "phase3_status": phase3_status,
                "identity_summary": identity.get("summary"),
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
            ensure_cost_conversion_table(cur)
            ensure_family_cost_table(cur)
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

            # v7.0.42: apply authoritative company-source Cost-UOM semantics before deciding
            # what is actually safe. Frozen uses BUN, Live/Fresh uses source-rule LB, while old substring matching could let "Unit"
            # match "Unit Cost", storing a numeric cost value as cost_uom_code.
            company_cost_uom_repair = repair_company_cost_uom_observations(cur)

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
            conversions = apply_manual_cost_conversions(cur)
            family_costs = apply_manual_family_costs(cur)
            family_subarticles = apply_manual_family_subarticles(cur)
            if overrides.get("held"):
                raise RuntimeError(
                    "One or more confirmed manual overrides could not be applied: "
                    + str(overrides.get("held"))
                )
            if conversions.get("held"):
                raise RuntimeError(
                    "One or more confirmed cost conversions could not be applied: "
                    + str(conversions.get("held"))
                )
            if family_costs.get("held"):
                raise RuntimeError(
                    "One or more confirmed family costs could not be applied: "
                    + str(family_costs.get("held"))
                )
            if family_subarticles.get("held"):
                raise RuntimeError(
                    "One or more confirmed family subarticles could not be applied: "
                    + str(family_subarticles.get("held"))
                )

            if family_costs.get("held"):
                raise RuntimeError("One or more confirmed family costs could not be applied: " + str(family_costs.get("held")))
            if family_subarticles.get("held"):
                raise RuntimeError("One or more confirmed family subarticles could not be applied: " + str(family_subarticles.get("held")))

            cost_repair = repair_current_active_cost(cur, batch_id)

            # Rebuild current per-UPC core holds from the resulting evidence state.
            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_status='RESOLVED',
                       detail_json=JSON_SET(
                         COALESCE(detail_json,JSON_OBJECT()),
                         '$.resolution',
                         'Superseded by v7.0.42 source-aware safe cost serving refresh'
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
                "mode": "SERVER_SIDE_SOURCE_AWARE_SAFE_COST_REPAIR_AND_QC_REBUILD_V7042",
                "publish_batch_id": batch_id,
                "before_safe_candidate_count": before_safe_count,
                "company_cost_uom_repair": company_cost_uom_repair,
                "verified_target_count": len(target_checks),
                "prior_core_holds_resolved": prior_core_holds_resolved,
                "cost_repair": cost_repair,
                "manual_cost_conversions": conversions,
                "manual_family_costs": family_costs,
                "manual_family_subarticles": family_subarticles,
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

def _confirmed_cost_conversion_target_checks(
    cur,
    before_base_state: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for expected in USER_CONFIRMED_COST_SELLING_CONVERSIONS_20260926:
        ean = str(expected["ean_upc"])
        cur.execute(
            """SELECT ean_upc,family_id,selling_uom,base_uom,
                      base_qty_per_selling_unit,current_cost_per_base_uom,
                      current_cost_per_selling_unit,quick_check_status,
                      blocking_reason,cost_source,cost_date
               FROM quick_check_current
               WHERE ean_upc=%s
               LIMIT 1""",
            (ean,),
        )
        row = cur.fetchone()
        before = before_base_state.get(ean) or {}
        latest_cost = _latest_cost(cur, int(row["family_id"])) if row else None

        actual_sell = _norm_cost_serving_uom(row.get("selling_uom")) if row else None
        expected_sell = _norm_cost_serving_uom(expected["selling_uom_code"])
        actual_cost_uom = _norm_cost_serving_uom(latest_cost.get("base_uom")) if latest_cost else None
        expected_cost_uom = _norm_cost_serving_uom(expected["cost_uom_code"])

        expected_cost_per_selling = None
        if row and row.get("current_cost_per_base_uom") is not None:
            expected_cost_per_selling = (
                Decimal(str(row["current_cost_per_base_uom"]))
                * Decimal(str(expected["cost_qty"]))
                / Decimal(str(expected["selling_qty"]))
            )
        actual_cost_per_selling = (
            Decimal(str(row["current_cost_per_selling_unit"]))
            if row and row.get("current_cost_per_selling_unit") is not None
            else None
        )
        cost_value_ok = bool(
            expected_cost_per_selling is not None
            and actual_cost_per_selling is not None
            and abs(actual_cost_per_selling - expected_cost_per_selling) <= Decimal("0.000001")
        )

        before_factor = before.get("base_qty_per_selling_unit")
        after_factor = row.get("base_qty_per_selling_unit") if row else None
        factor_unchanged = (
            (before_factor is None and after_factor is None)
            or (
                before_factor is not None
                and after_factor is not None
                and Decimal(str(before_factor)) == Decimal(str(after_factor))
            )
        )
        base_unchanged = bool(
            row
            and (before.get("base_uom") or None) == (row.get("base_uom") or None)
            and factor_unchanged
        )
        reasons = {
            x.strip()
            for x in str((row or {}).get("blocking_reason") or "").split(",")
            if x and x.strip()
        }
        conversion_hold_cleared = bool(
            row
            and "COST_TO_SELLING_UOM_UNRESOLVED" not in reasons
            and row.get("current_cost_per_selling_unit") is not None
        )

        passed = bool(
            row
            and actual_sell == expected_sell
            and actual_cost_uom == expected_cost_uom
            and cost_value_ok
            and base_unchanged
            and conversion_hold_cleared
        )
        checks.append(
            {
                "ean_upc": ean,
                "expected_equation": (
                    f'{expected["selling_qty"]} {expected["selling_uom_code"]} = '
                    f'{expected["cost_qty"]} {expected["cost_uom_code"]}'
                ),
                "expected_selling_uom": expected_sell,
                "actual_selling_uom": actual_sell,
                "expected_cost_uom": expected_cost_uom,
                "actual_cost_uom": actual_cost_uom,
                "cost_per_cost_uom": row.get("current_cost_per_base_uom") if row else None,
                "expected_cost_per_selling_unit": expected_cost_per_selling,
                "actual_cost_per_selling_unit": actual_cost_per_selling,
                "base_uom_before": before.get("base_uom"),
                "base_uom_after": row.get("base_uom") if row else None,
                "base_factor_before": before_factor,
                "base_factor_after": after_factor,
                "base_inventory_uom_unchanged": base_unchanged,
                "quick_check_status": row.get("quick_check_status") if row else None,
                "blocking_reason": row.get("blocking_reason") if row else None,
                "conversion_hold_cleared": conversion_hold_cleared,
                "pass": passed,
            }
        )
    return checks


def run_confirmed_cost_conversion_refresh(device: str) -> dict[str, Any]:
    """Apply the exact user-confirmed cost-to-selling conversions atomically."""

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Bootstrap schema before the business transaction because MySQL DDL
            # implicitly commits.
            ensure_override_table(cur)
            ensure_retirement_table(cur)
            ensure_cost_conversion_table(cur)
            ensure_family_cost_table(cur)
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
                    "Server pipeline is currently processing; retry the confirmed cost conversion refresh later."
                )

            conn.commit()
            conn.start_transaction()

            batch_id = _latest_serving_batch_id(cur)
            identity_before = audit_product_identity(cur)
            if not bool(identity_before.get("pass")):
                raise RuntimeError(
                    "Pre-refresh product identity audit is blocked; conversion refresh refused. "
                    f"blockers={identity_before.get('blockers')}"
                )

            before_diag = diagnose_global_cost_holds(cur)
            before_cost_summary = before_diag.get("summary") or {}

            before_base_state: dict[str, dict[str, Any]] = {}
            for expected in USER_CONFIRMED_COST_SELLING_CONVERSIONS_20260926:
                ean = str(expected["ean_upc"])
                cur.execute(
                    """SELECT base_uom,base_qty_per_selling_unit
                       FROM quick_check_current
                       WHERE ean_upc=%s
                       LIMIT 1""",
                    (ean,),
                )
                before_base_state[ean] = cur.fetchone() or {}

            overrides = apply_manual_upc_overrides(cur)
            retirements = apply_manual_upc_retirements(cur)
            conversions = apply_manual_cost_conversions(cur)
            family_costs = apply_manual_family_costs(cur)
            family_subarticles = apply_manual_family_subarticles(cur)
            if overrides.get("held"):
                raise RuntimeError(
                    "One or more confirmed manual UPC overrides could not be applied: "
                    + str(overrides.get("held"))
                )
            if conversions.get("held"):
                raise RuntimeError(
                    "One or more confirmed cost conversions could not be applied: "
                    + str(conversions.get("held"))
                )
            if family_costs.get("held"):
                raise RuntimeError(
                    "One or more confirmed family costs could not be applied: "
                    + str(family_costs.get("held"))
                )
            if family_subarticles.get("held"):
                raise RuntimeError(
                    "One or more confirmed family subarticles could not be applied: "
                    + str(family_subarticles.get("held"))
                )

            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_status='RESOLVED',
                       detail_json=JSON_SET(
                         COALESCE(detail_json,JSON_OBJECT()),
                         '$.resolution',
                         'Superseded by v7.0.41 confirmed cost conversion refresh'
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

            target_checks = _confirmed_cost_conversion_target_checks(
                cur,
                before_base_state,
            )
            failed_targets = [x for x in target_checks if not x.get("pass")]
            if failed_targets:
                raise RuntimeError(
                    "Confirmed cost conversion verification failed; transaction rolled back. "
                    f"failed_targets={failed_targets}"
                )

            after_diag = diagnose_global_cost_holds(cur)
            after_cost_summary = after_diag.get("summary") or {}
            before_conversion_holds = int(
                before_cost_summary.get("cost_to_selling_uom_unresolved_count") or 0
            )
            after_conversion_holds = int(
                after_cost_summary.get("cost_to_selling_uom_unresolved_count") or 0
            )
            if after_conversion_holds > before_conversion_holds:
                raise RuntimeError(
                    "Cost-to-selling hold count increased; transaction rolled back. "
                    f"before={before_conversion_holds}; after={after_conversion_holds}"
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
                "mode": "SERVER_SIDE_CONFIRMED_COST_TO_SELLING_CONVERSION_V7041",
                "publish_batch_id": batch_id,
                "target_count": len(USER_CONFIRMED_COST_SELLING_CONVERSIONS_20260926),
                "verified_target_count": len(target_checks),
                "manual_conversions": conversions,
                "manual_family_costs": family_costs,
                "manual_family_subarticles": family_subarticles,
                "manual_overrides": overrides,
                "manual_retirements": retirements,
                "prior_core_holds_resolved": prior_core_holds_resolved,
                "quick_check": qc,
                "phase3_status": status,
                "before_cost_summary": before_cost_summary,
                "after_cost_summary": after_cost_summary,
                "target_checks": target_checks,
                "identity_before_summary": identity_before.get("summary"),
                "identity_after_summary": identity_after.get("summary"),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

