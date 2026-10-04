from __future__ import annotations

import api as _api
import api_entry_v478 as _prev
from yipman_quick_check_layout import inject_quick_check_mobile_layout

app = _prev.app

# Layer the mobile Quick Check layout on top of the already-composed v479
# Yipman shells. Keep the underlying HTML/JS unchanged so True Stock,
# receiving history, pricing hydration, navigation, and ordering behavior retain
# their existing event bindings and data contracts.
_base_yipman_html = _api.yipman_html
_base_yipman_v1_html = _api.yipman_v1_html


def _patched_yipman_html(version: str = "") -> str:
    return inject_quick_check_mobile_layout(_base_yipman_html(version))


def _patched_yipman_v1_html(version: str = "") -> str:
    return inject_quick_check_mobile_layout(_base_yipman_v1_html(version))


_api.yipman_html = _patched_yipman_html
_api.yipman_v1_html = _patched_yipman_v1_html

# Keep one desktop experience. /app/backoffice now renders the same Yipman
# desktop shell as /app/yipman, including the v476 promotion workflow and the
# v477/v478 ordering stability patches already layered into api.yipman_html.
def _yipman_backoffice_html(version: str = "") -> str:
    return _api.yipman_html(version)


_api.backoffice_html = _yipman_backoffice_html
