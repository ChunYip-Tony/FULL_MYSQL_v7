from __future__ import annotations

"""V494 composition: current production entry plus Mobile V1 decision explainability."""

import api_entry_production as _production
import api as _api
from yipman_decision_details_v494 import inject_decision_details

app = _production.app

# api_entry_production has already captured and decorated the official Mobile V1
# renderer. Wrap that final renderer rather than creating another product route.
_base_official_mobile_v1_html = _api.yipman_v1_html


def _mobile_v1_with_decision_details(version: str = "") -> str:
    return inject_decision_details(_base_official_mobile_v1_html(version))


_api.yipman_v1_html = _mobile_v1_with_decision_details

# Diagnostic marker for deployment/runtime verification.
app.state.yipman_mobile_decision_details = {
    "version": "v494",
    "channel": "Yipman Mobile V1",
    "path": "/app/yipman-v1/",
    "behavior": "primary decisions open why/evidence drill-down",
}
