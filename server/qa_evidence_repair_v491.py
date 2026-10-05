from __future__ import annotations

"""Evidence-backed repair helpers for current Quick Check QA holds."""

from typing import Any

from maintenance_api import (
    run_article_manual_roster_repair,
    run_confirmed_uom_refresh,
    run_confirmed_cost_conversion_refresh,
    run_cost_authority_refresh,
    run_safe_cost_refresh,
)


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
