from __future__ import annotations

import api as _api
import api_entry_v478 as _prev

app = _prev.app

# Keep one desktop experience. /app/backoffice now renders the same Yipman
# desktop shell as /app/yipman, including the v476 promotion workflow and the
# v477/v478 ordering stability patches already layered into api.yipman_html.
def _yipman_backoffice_html(version: str = "") -> str:
    return _api.yipman_html(version)

_api.backoffice_html = _yipman_backoffice_html
