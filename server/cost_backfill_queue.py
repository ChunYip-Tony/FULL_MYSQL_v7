from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from business_clock import completed_through_date
from db import db_conn
from global_cost_hold_diagnostic import diagnose_global_cost_holds


def cost_backfill_queue(lookback_days: int = 90) -> dict[str, Any]:
    """Plan historical MVT backfill for current CURRENT_COST_MISSING holds.

    This endpoint is intentionally read-only. It never invents a cost and never
    auto-resolves a hold. It groups current missing-cost UPCs by Family and shows
    whether loaded movement history reaches the requested completed-day window.
    """
    lookback_days = max(30, min(int(lookback_days or 90), 365))
    through = completed_through_date()
    requested_start = through - timedelta(days=lookback_days - 1)

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        diagnostic = diagnose_global_cost_holds(cur)

        missing_items = [
            item for item in (diagnostic.get("items") or [])
            if "CURRENT_COST_MISSING" in (item.get("reasons") or [])
        ]

        groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for item in missing_items:
            fid = item.get("family_id")
            if fid is not None:
                groups[int(fid)].append(item)

        actions: list[dict[str, Any]] = []
        for family_id, items in sorted(groups.items()):
            article_ids = sorted({
                int(a.get("article_id"))
                for item in items
                for a in (item.get("confirmed_family_articles") or [])
                if a.get("article_id") is not None
            })
            article_numbers = sorted({
                str(a.get("article_number"))
                for item in items
                for a in (item.get("confirmed_family_articles") or [])
                if a.get("article_number")
            })
            upcs = sorted({str(item.get("ean_upc")) for item in items if item.get("ean_upc")})

            if article_ids:
                ph = ",".join(["%s"] * len(article_ids))
                where = f"(family_id=%s OR article_id IN ({ph}))"
                params: tuple[Any, ...] = tuple([family_id] + article_ids)
            else:
                where = "family_id=%s"
                params = (family_id,)

            cur.execute(
                f"""SELECT
                       MIN(posting_date) AS earliest_movement_date,
                       MAX(posting_date) AS latest_movement_date,
                       COUNT(*) AS movement_row_count
                    FROM movement_history
                    WHERE {where}""",
                params,
            )
            movement = cur.fetchone() or {}

            cur.execute(
                f"""SELECT
                       MIN(posting_date) AS earliest_receipt_date,
                       MAX(posting_date) AS latest_receipt_date,
                       COUNT(*) AS receipt_row_count,
                       SUM(CASE
                             WHEN amount_local_currency IS NOT NULL
                              AND amount_local_currency<>0
                              AND (
                                   (
                                     entry_quantity IS NOT NULL
                                     AND entry_quantity<>0
                                     AND NULLIF(TRIM(entry_uom_code),'') IS NOT NULL
                                   )
                                   OR
                                   (
                                     base_quantity IS NOT NULL
                                     AND base_quantity<>0
                                     AND NULLIF(TRIM(base_uom_code),'') IS NOT NULL
                                   )
                              )
                             THEN 1 ELSE 0 END) AS valid_valuation_row_count
                    FROM movement_history
                    WHERE {where}
                      AND movement_type IN ('101','107','109')""",
                params,
            )
            receipt = cur.fetchone() or {}

            earliest_movement = movement.get("earliest_movement_date")
            latest_movement = movement.get("latest_movement_date")
            earliest_receipt = receipt.get("earliest_receipt_date")
            latest_receipt = receipt.get("latest_receipt_date")
            valid_receipts = int(receipt.get("valid_valuation_row_count") or 0)

            representative = max(
                items,
                key=lambda x: (
                    float(x.get("pos_qty_30d") or 0),
                    float(x.get("pos_qty_7d") or 0),
                    str(x.get("ean_upc") or ""),
                ),
            )
            receipt_evidence = representative.get("receipt_evidence") or {}
            missing_class = representative.get("missing_cost_classification") or {}
            diagnostic_classification = str(
                missing_class.get("classification") or ""
            )
            diagnostic_action = str(
                missing_class.get("proposed_action") or ""
            )

            if earliest_movement is None:
                coverage_status = "NO_MOVEMENT_HISTORY"
                backfill_needed = True
                backfill_mode = "INITIAL_LOOKBACK"
                required_upload_scope = "FULL_MVT_HISTORY_NOT_FILTERED"
                action_code = "UPLOAD_FULL_MVT_BACKFILL"
            elif earliest_movement > requested_start:
                coverage_status = "PARTIAL_HISTORY_NEEDS_BACKFILL"
                backfill_needed = True
                backfill_mode = "INITIAL_LOOKBACK"
                required_upload_scope = "FULL_MVT_HISTORY_NOT_FILTERED"
                action_code = "UPLOAD_FULL_MVT_BACKFILL"
            elif (
                diagnostic_classification
                == "NO_RECEIVING_HISTORY_OR_AUTHORITATIVE_REPORT_COST"
            ):
                coverage_status = "LOOKBACK_COVERED_NO_RECEIVING_HISTORY"
                backfill_needed = True
                backfill_mode = "EXTEND_BEYOND_LOOKBACK"
                required_upload_scope = (
                    "FULL_MVT_HISTORY_BEFORE_REQUESTED_START_NOT_FILTERED"
                )
                action_code = "EXTEND_MVT_BACKFILL_BEYOND_LOOKBACK"
            elif diagnostic_classification == "RECEIPT_ROWS_WITHOUT_VALID_VALUATION":
                coverage_status = "LOOKBACK_COVERED_RECEIPT_VALUATION_INVALID"
                backfill_needed = False
                backfill_mode = "NONE"
                required_upload_scope = (
                    "NO_ADDITIONAL_MVT_REQUIRED_BY_CURRENT_DIAGNOSIS"
                )
                action_code = "REVIEW_RECEIPT_VALUATION_FIELDS"
            elif valid_receipts > 0:
                coverage_status = "VALID_RECEIPT_PRESENT_REVIEW_HOLD"
                backfill_needed = False
                backfill_mode = "NONE"
                required_upload_scope = (
                    "NO_ADDITIONAL_MVT_REQUIRED_BY_CURRENT_DIAGNOSIS"
                )
                action_code = (
                    diagnostic_action or "REVIEW_EXISTING_COST_EVIDENCE"
                )
            else:
                coverage_status = "LOOKBACK_COVERED_DIAGNOSTIC_REVIEW_REQUIRED"
                backfill_needed = False
                backfill_mode = "NONE"
                required_upload_scope = (
                    "NO_ADDITIONAL_MVT_REQUIRED_BY_CURRENT_DIAGNOSIS"
                )
                action_code = (
                    diagnostic_action or "REVIEW_EXISTING_COST_EVIDENCE"
                )

            if earliest_movement is None:
                missing_days_before_loaded_history = lookback_days
            elif earliest_movement > requested_start:
                missing_days_before_loaded_history = (
                    earliest_movement - requested_start
                ).days
            else:
                missing_days_before_loaded_history = 0

            actions.append(
                {
                    "family_id": family_id,
                    "main_article_number": representative.get("main_article_number"),
                    "family_description": representative.get("family_description"),
                    "representative_upc": representative.get("ean_upc"),
                    "related_upcs": upcs,
                    "related_upc_count": len(upcs),
                    "confirmed_article_numbers": article_numbers,
                    "current_hold_row_count": len(items),
                    "current_hold_reason": "CURRENT_COST_MISSING",
                    "safe_to_auto_resolve": all(
                        bool(x.get("safe_to_auto_resolve_cost_hold")) for x in items
                    ),
                    "diagnostic_classification": diagnostic_classification or None,
                    "diagnostic_proposed_action": diagnostic_action or None,
                    "requested_lookback_days": lookback_days,
                    "requested_backfill_start": requested_start,
                    "requested_backfill_end": through,
                    "earliest_loaded_movement_date": earliest_movement,
                    "latest_loaded_movement_date": latest_movement,
                    "loaded_movement_row_count": int(movement.get("movement_row_count") or 0),
                    "missing_days_before_loaded_history": missing_days_before_loaded_history,
                    "earliest_loaded_receipt_date": earliest_receipt,
                    "latest_loaded_receipt_date": latest_receipt,
                    "loaded_receipt_row_count": int(receipt.get("receipt_row_count") or 0),
                    "valid_receipt_valuation_row_count": valid_receipts,
                    "diagnostic_receipt_row_count": int(receipt_evidence.get("receipt_rows") or 0),
                    "diagnostic_valid_valuation_rows": int(receipt_evidence.get("valid_valuation_rows") or 0),
                    "coverage_status": coverage_status,
                    "backfill_needed": backfill_needed,
                    "backfill_mode": backfill_mode,
                    "required_upload_scope": required_upload_scope,
                    "required_receipt_movements": ["101","107","109"],
                    "action_code": action_code,
                }
            )

        actions.sort(
            key=lambda r: (
                0 if r.get("backfill_needed") else 1,
                -int(r.get("missing_days_before_loaded_history") or 0),
                str(r.get("main_article_number") or ""),
            )
        )
        for index, row in enumerate(actions, start=1):
            row["backfill_sequence"] = index

        cur.close()

    return {
        "status": "OK",
        "queue_type": "CURRENT_COST_MISSING_BACKFILL_QUEUE",
        "queue_grain": "FAMILY",
        "lookback_days": lookback_days,
        "requested_backfill_start": requested_start,
        "requested_backfill_end": through,
        "current_cost_missing_upc_count": len(missing_items),
        "family_action_count": len(actions),
        "backfill_needed_family_count": sum(1 for x in actions if x.get("backfill_needed")),
        "review_existing_evidence_family_count": sum(1 for x in actions if not x.get("backfill_needed")),
        "safe_to_auto_resolve_upc_count": sum(
            1 for x in missing_items if x.get("safe_to_auto_resolve_cost_hold")
        ),
        "actions": actions,
    }
