from __future__ import annotations

"""Evidence-backed repair helpers for current Quick Check QA holds."""

from typing import Any


def repair_contract() -> dict[str, Any]:
    return {
        "mode": "EVIDENCE_BACKED_ONLY",
        "invent_identity": False,
        "invent_uom": False,
        "invent_cost": False,
    }
