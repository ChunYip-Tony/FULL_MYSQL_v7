from __future__ import annotations

import api as _api
import api_entry_v479 as _prev
from yipman_data_center_v481 import inject_data_center_fix

app = _prev.app

# v481 is a desktop-only Data Center status/QA-scope correction.
# Keep Mobile V1 untouched. QA navigation is intentionally handled only at
# the production boundary so older overlay handlers cannot intercept clicks.
_base_backoffice_html = _api.backoffice_html


def _patched_backoffice_html(version: str = "") -> str:
    return inject_data_center_fix(_base_backoffice_html(version))


_api.backoffice_html = _patched_backoffice_html
