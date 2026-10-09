from __future__ import annotations

"""Static regression contract for exact/action-aware Mobile V1 decision hydration."""

from yipman_mobile_v1_decision_snapshot import polish_decision_snapshot_html


def run_selftest():
    html = polish_decision_snapshot_html("<html><body></body></html>")
    assert "byKeyDecision" in html
    assert "UPC:${u}:${a}" in html
    assert "if(u)keys.push(`UPC:${u}`)" in html
    assert "FAMILY:${f}:${a}" in html
    assert "activeBuildId" in html
    assert "/api/yipman/app-ready/status" in html
    assert "decisionBuildId" in html
    assert "[build,family,digits(upc),action].join('|')" in html
    assert "decision_evidence_ready" in html
    assert "decision_missing_evidence" in html
    # Exact UPC is resolved before the family fallback loops.
    assert html.index("if(u){const exact=rows.find") < html.index("if(f){for(const g of groups)")
    return {
        "exact_upc_before_family": "PASS",
        "action_specific_key_first": "PASS",
        "build_id_cache_invalidation": "PASS",
        "evidence_integrity_fields": "PASS",
    }


if __name__ == "__main__":
    print(run_selftest())
