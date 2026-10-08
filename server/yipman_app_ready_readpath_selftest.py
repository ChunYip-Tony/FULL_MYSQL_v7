from __future__ import annotations

"""Dependency-light regression checks for Mobile V1 App Ready composition."""


def run_readpath_contract_selftest()->dict[str,str]:
    from yipman_mobile_v1_decision_snapshot import polish_decision_snapshot_html
    base='<html><body><div id="v1DetailBody"></div></body></html>'
    html=polish_decision_snapshot_html(base)
    assert html.count('yipmanV1DecisionSnapshotScript')==1
    assert "decisionPromise" in html and "const preload=" in html
    assert "fetch('/api/yipman/app-ready/decision_intelligence'" in html
    # The click/detail path must reuse preload(), not contain a second fetch.
    assert html.count("fetch('/api/yipman/app-ready/decision_intelligence'")==1
    assert 'PRECOMPUTED_AFTER_DATA_CHANGE_NOT_ON_PAGE_OPEN' not in html
    return {"decision_prefetch":"PASS","single_snapshot_transfer":"PASS","why_no_business_compute":"PASS"}

if __name__=='__main__':print(run_readpath_contract_selftest())
