from __future__ import annotations

import api as _api
import api_entry_v479 as _prev
from data_health_snapshot_date_v498 import apply_snapshot_date_patch
from yipman_data_center_v481 import inject_data_center_fix
from yipman_data_center_ui_v497 import inject_data_center_ui
from yipman_data_center_ui_v498 import inject_data_center_ui_v498
from yipman_data_center_monitor_v500 import inject_data_center_monitor_v500
from yipman_data_center_focus_v501 import inject_data_center_focus_v501
from yipman_data_center_focus_v502 import inject_data_center_focus_v502
from yipman_data_center_focus_v503 import inject_data_center_focus_v503

app = _prev.app

# Repair legacy snapshot-date evidence before Data Health endpoints are called.
# This lets files such as F INV 1002.xlsx surface as 2026-10-02 without using
# upload time as the actual business/snapshot date.
apply_snapshot_date_patch()

# Data Center consistency correction + UI upgrades apply to both production
# desktop renderers. Mobile V1 remains untouched.
_base_backoffice_html = _api.backoffice_html
_base_yipman_html = _api.yipman_html


def _decorate(html: str) -> str:
    return inject_data_center_focus_v503(
        inject_data_center_focus_v502(
            inject_data_center_focus_v501(
                inject_data_center_monitor_v500(
                    inject_data_center_ui_v498(
                        inject_data_center_ui(
                            inject_data_center_fix(html)
                        )
                    )
                )
            )
        )
    )


def _patched_backoffice_html(version: str = "") -> str:
    return _decorate(_base_backoffice_html(version))


def _patched_yipman_html(version: str = "") -> str:
    return _decorate(_base_yipman_html(version))


_api.backoffice_html = _patched_backoffice_html
_api.yipman_html = _patched_yipman_html
