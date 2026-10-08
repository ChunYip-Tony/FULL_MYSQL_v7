from __future__ import annotations

"""V504 production composition: consolidated official Mobile V1 renderer."""

import api_entry_v494 as _previous
import api as _api
from yipman_mobile_v1_exact_shell import yipman_mobile_v1_exact_html
from yipman_mobile_v1_price_guard import guard_price_html
from yipman_mobile_v1_price_polish import polish_price_html
from yipman_mobile_v1_price_upc_only import polish_price_upc_only_html
from yipman_mobile_v1_price_progress import polish_price_progress_html
from yipman_mobile_v1_interactions import polish_interactions_html
from yipman_mobile_v1_quick_search_polish import polish_quick_search_html
from yipman_mobile_v1_order_detail import polish_order_detail_html
from yipman_mobile_v1_order_evidence_bridge import polish_order_evidence_bridge_html
from yipman_mobile_v1_family_detail import polish_family_detail_html
from yipman_mobile_v1_ordering_context import polish_ordering_context_html
from yipman_mobile_v1_loading_hotfix import polish_loading_html
from yipman_mobile_v1_ordering_reliability import polish_ordering_reliability_html
from yipman_mobile_v1_ordering_home_decouple import polish_ordering_home_decouple_html
from yipman_mobile_v1_typography import polish_typography_html
from yipman_mobile_v1_navigation import polish_navigation_html
from yipman_mobile_v1_identity_guard import polish_identity_html
from yipman_mobile_v1_stock_flow_home import polish_stock_flow_home_html
from yipman_mobile_v1_stock_flow_compact import polish_stock_flow_compact_html
from yipman_mobile_v1_stock_flow_actions import polish_stock_flow_actions_html
from yipman_mobile_v1_family_mvt_fix import polish_family_mvt_fix_html
from yipman_mobile_v1_decision_compact import polish_decision_compact_html
from yipman_mobile_v1_all_decision_evidence import polish_all_decision_evidence_html
from yipman_mobile_v1_decision_snapshot import polish_decision_snapshot_html
from yipman_mobile_v1_app_ready_client import polish_app_ready_client_html
from yipman_mobile_v1_pwa import polish_pwa_html

app = _previous.app

_POLISHERS = (
    guard_price_html, polish_price_html, polish_price_upc_only_html,
    polish_price_progress_html, polish_quick_search_html, polish_identity_html,
    polish_interactions_html, polish_order_detail_html, polish_family_detail_html,
    polish_ordering_context_html, polish_loading_html, polish_ordering_reliability_html,
    polish_ordering_home_decouple_html,
    polish_typography_html, polish_stock_flow_home_html, polish_stock_flow_compact_html,
    polish_stock_flow_actions_html,
    polish_pwa_html, polish_navigation_html, polish_family_mvt_fix_html,
    polish_decision_compact_html, polish_order_evidence_bridge_html,
    polish_decision_snapshot_html, polish_all_decision_evidence_html,
    polish_app_ready_client_html,
)


def _official_mobile_v1_v504(version: str = "") -> str:
    html = yipman_mobile_v1_exact_html(version)
    for polish in _POLISHERS:
        html = polish(html)
    html = html.replace("<title>Yipman</title>", "<title>Yipman Mobile V1</title>", 1)
    return html


_api.yipman_v1_html = _official_mobile_v1_v504

app.state.yipman_mobile_v1_release = {
    "version": "v504",
    "channel": "Yipman Mobile V1",
    "path": "/app/yipman-v1/",
    "home": "STOCK_FLOW_ONLY",
    "ordering": "REGULAR_AND_PROMOTION",
    "price_lifecycle": ["REG", "TPR_SUGGESTIONS", "TPR_PROGRESS", "CLEARANCE"],
    "quick_check": "UPC_ORDERING_AND_PRICE_REVIEW",
    "primary_decision_evidence": True,
    "app_ready_snapshot_first": True,
    "decision_snapshot_hydration": True,
}
