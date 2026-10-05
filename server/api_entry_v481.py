from __future__ import annotations

import api as _api
import api_entry_v479 as _prev
from yipman_data_center_v481 import inject_data_center_fix
from yipman_qa_click_v484 import inject_qa_click_fix

app = _prev.app

# v481 is a desktop-only Data Center status/QA-scope correction.
# v484 additionally attaches resilient QA Holds navigation at this stable layer
# so the handler is present even if later product wrappers are bypassed.
# Keep Mobile V1 untouched.
_base_backoffice_html = _api.backoffice_html


def _patched_backoffice_html(version: str = "") -> str:
    html = inject_data_center_fix(_base_backoffice_html(version))
    return inject_qa_click_fix(html)


_api.backoffice_html = _patched_backoffice_html
