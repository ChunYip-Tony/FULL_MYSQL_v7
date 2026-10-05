from __future__ import annotations

"""Evidence-backed repair helpers for current Quick Check QA holds."""

import threading
import time
from typing import Any

from maintenance_api import (
    run_article_manual_roster_repair,
    run_confirmed_uom_refresh,
    run_confirmed_cost_conversion_refresh,
    run_cost_authority_refresh,
    run_safe_cost_refresh,
)

_SCHEDULED = False
_SCHEDULE_LOCK = threading.Lock()


def repair_contract() -> dict[str, Any]:
    return {
        "mode": "EVIDENCE_BACKED_ONLY",
        "invent_identity": False,
        "invent_uom": False,
        "invent_conversion": False,
        "invent_cost": False,
    }


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
    return results


def schedule_evidence_backed_qa_repair() -> None:
    """Run the user-approved evidence repair once per API process after deploy."""
    global _SCHEDULED
    with _SCHEDULE_LOCK:
        if _SCHEDULED:
            return
        _SCHEDULED = True

    def worker() -> None:
        # Let the API/worker settle, then retry only when maintenance was blocked
        # by an active pipeline. All underlying repair functions are transactional.
        time.sleep(12)
        for attempt in range(6):
            result = run_evidence_backed_qa_repair("USER_APPROVED_AUTO_QA_REPAIR_20261004")
            errors = " ".join(
                str(payload.get("error") or "")
                for payload in (result.get("steps") or {}).values()
                if isinstance(payload, dict)
            ).upper()
            pipeline_blocked = "PIPELINE" in errors and (
                "PROCESS" in errors or "BUSY" in errors or "QUEUED" in errors
            )
            if not pipeline_blocked:
                return
            if attempt < 5:
                time.sleep(20)

    threading.Thread(target=worker, name="qa-evidence-self-heal-v491", daemon=True).start()
