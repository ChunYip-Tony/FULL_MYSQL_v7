from __future__ import annotations

import api as _api
import api_entry_v479 as _prev
from yipman_data_center_v481 import inject_data_center_fix

app = _prev.app

# Data Center consistency correction applies to both production desktop
# renderers. Mobile V1 remains untouched.
_base_backoffice_html = _api.backoffice_html
_base_yipman_html = _api.yipman_html


def _patched_backoffice_html(version: str = "") -> str:
    return inject_data_center_fix(_base_backoffice_html(version))


def _patched_yipman_html(version: str = "") -> str:
    return inject_data_center_fix(_base_yipman_html(version))


_api.backoffice_html = _patched_backoffice_html
_api.yipman_html = _patched_yipman_html
