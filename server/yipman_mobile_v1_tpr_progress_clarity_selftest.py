from __future__ import annotations

"""Static regression contract for Mobile V1 TPR Progress evidence rendering."""

from yipman_mobile_v1_price_progress import polish_price_progress_html
from yipman_mobile_v1_tpr_progress_guard import polish_tpr_progress_guard_html
from yipman_mobile_v1_tpr_progress_clarity import polish_tpr_progress_clarity_html


def run_selftest():
    shell = '<html><head></head><body><script>async function loadPrice(){} function renderPrice(){const rows=priceRows.filter(x=>x)} function actionablePrice(){}</script></body></html>'
    html = polish_price_progress_html(shell)
    html = polish_tpr_progress_guard_html(html)
    html = polish_tpr_progress_clarity_html(html)

    assert "function tprEvidenceReady" in html
    assert "function tprMissingEvidence" in html
    assert "function tprCurrentPrice" in html
    assert "function tprActualVelocity" in html
    assert "current_tpr_price" in html
    assert "tpr_velocity_3d" in html
    assert "tprReadinessBlocked" in html
    assert "Cannot evaluate current TPR yet. Missing:" in html
    assert "cur==null?'DATA NEEDED':money(cur)" in html
    assert "ready?esc(decision):'DATA NEEDED'" in html
    assert "v===null||v===undefined||v===''" in html
    assert "tpr-progress-incomplete" in html
    return {
        "authoritative_current_tpr_price_alias": "PASS",
        "authoritative_tpr_velocity_alias": "PASS",
        "readiness_blocker_gate": "PASS",
        "missing_evidence_gate": "PASS",
        "null_not_zero": "PASS",
        "decision_fail_closed": "PASS",
    }


if __name__ == "__main__":
    print(run_selftest())
