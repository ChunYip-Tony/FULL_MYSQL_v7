from __future__ import annotations

from typing import Any

from db import db_conn
from manual_overrides import apply_manual_upc_overrides, apply_manual_upc_retirements
from product_identity_audit import audit_product_identity


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
