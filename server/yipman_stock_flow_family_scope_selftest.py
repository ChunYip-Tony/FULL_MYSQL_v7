from __future__ import annotations

"""Static contract for the True Stock family-scoped Stock Flow path.

This intentionally avoids MySQL so it can run in a dependency-light CI job.
Runtime DB verification remains a separate deployment check.
"""

import inspect
from pathlib import Path

from yipman_mobile_v1_stock_flow import stock_flow_review


def run_selftest():
    sig = inspect.signature(stock_flow_review)
    assert "family_id" in sig.parameters
    assert sig.parameters["family_id"].default is None

    source = Path(__file__).with_name("yipman_mobile_v1_stock_flow.py").read_text(encoding="utf-8")
    assert 'where_family = " AND family_id=%s" if target_family is not None else ""' in source
    assert '"family_scope": target_family' in source
    assert "_family_effective_oh(cur, children) if fid in active_true_stock_ids" in source
    assert "_family_receipt_events_bulk(cur, fids" in source

    return {
        "family_parameter": "PASS",
        "sql_scope_guard": "PASS",
        "family_scope_visible": "PASS",
        "true_stock_effective_oh_authority": "PASS",
        "scoped_receipt_bulk": "PASS",
    }


if __name__ == "__main__":
    print(run_selftest())
