from __future__ import annotations

import json
from typing import Any

VERSION = "7.0.174-temporary-qa-waiver-registry"

# Explicit user-approved temporary identity waivers.
#
# These do NOT resolve identity, do NOT create Article/Family mappings,
# do NOT infer UOM/cost/conversions, and do NOT delete QA/history.
# They only remove these exact unresolved UPCs from CURRENT BATCH readiness blockers.
TEMPORARY_SOLD_UPC_IDENTITY_WAIVERS: dict[str, dict[str, str]] = {}

# The two prior identity waivers were retired after authoritative user confirmation
# on 2026-09-26:
#   75539372208 -> Article 3480452, Selling UOM PACK, source spec 24/12OZ
#   81223402610 -> Article 3461050, Selling UOM PACK, source spec 40/150G
# They now live in manual_upc_override and should resolve as confirmed identity.



def apply_temporary_identity_waivers(cur, batch_id: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "version": VERSION,
        "configured": len(TEMPORARY_SOLD_UPC_IDENTITY_WAIVERS),
        "issues_examined": 0,
        "issues_waived": 0,
        "upcs_waived": [],
        "not_present": [],
    }

    for upc, cfg in TEMPORARY_SOLD_UPC_IDENTITY_WAIVERS.items():
        cur.execute(
            """SELECT issue_id,severity,issue_summary,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s
                 AND issue_status='OPEN'
                 AND issue_code IN ('SOLD_UPC_UNMAPPED','CURRENT_ACTIVE_SOLD_UPC_UNMAPPED')
                 AND entity_key=%s
               ORDER BY issue_id""",
            (batch_id, upc),
        )
        rows = cur.fetchall()
        if not rows:
            result["not_present"].append(upc)
            continue

        waived_this_upc = 0
        for row in rows:
            result["issues_examined"] += 1
            try:
                detail = json.loads(row.get("detail_json") or "{}")
            except Exception:
                detail = {}

            detail["temporary_qa_waiver"] = {
                "waiver_type": "IDENTITY_PENDING",
                "non_blocking_current_readiness": True,
                "quick_check_allowed": False,
                "preserve_original_qa": True,
                "requested_by": cfg["requested_by"],
                "waiver_scope": cfg["waiver_scope"],
                "reason": cfg["reason"],
            }

            cur.execute(
                """UPDATE qa_phase3_issue
                   SET severity='MEDIUM',
                       issue_summary=%s,
                       detail_json=%s
                   WHERE issue_id=%s""",
                (
                    f"Temporary non-blocking identity waiver for active sold UPC {upc}. "
                    "Identity remains unresolved; Quick Check is blocked for this UPC until authoritative mapping is confirmed.",
                    json.dumps(detail, ensure_ascii=False, default=str),
                    row["issue_id"],
                ),
            )
            waived_this_upc += 1
            result["issues_waived"] += 1

        if waived_this_upc:
            result["upcs_waived"].append({
                "upc": upc,
                "issue_rows_waived": waived_this_upc,
                "reason": cfg["reason"],
            })

    return result


def is_temporarily_waived_detail(detail: dict[str, Any] | None) -> bool:
    if not isinstance(detail, dict):
        return False
    waiver = detail.get("temporary_qa_waiver")
    return bool(
        isinstance(waiver, dict)
        and waiver.get("waiver_type") == "IDENTITY_PENDING"
        and waiver.get("non_blocking_current_readiness") is True
    )
