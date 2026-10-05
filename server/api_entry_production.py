from __future__ import annotations

"""Stable production API entrypoint.

Product channels are intentionally fixed:
- Mobile: Yipman Mobile V1 -> /app/yipman-v1/
- Desktop: Yipman Back Office -> /app/backoffice and /yipman

Versioned api_entry_v* modules are implementation layers only. The service
launcher must import this module so future internal releases do not create a
new production app identity or deployment entrypoint.
"""

import api as _api
import api_entry_v481 as _current
from yipman_qa_page_v485 import inject_qa_hard_link, register_qa_page

app = _current.app

# Capture the actual renderers used by both desktop URLs. /yipman calls
# api.yipman_html directly, while /app/backoffice calls api.backoffice_html.
_base_mobile_v1_html = _api.yipman_v1_html
_base_yipman_html = _api.yipman_html
_base_backoffice_html = _api.backoffice_html

_QA_BUTTON_STYLE = '''
<style id="ydQaButtonV487">
@media (min-width:760px){
  #ydesk #ydQaHardLinkV485{
    min-width:96px!important;
    background:#ffffff!important;
    color:#102842!important;
    border:2px solid #82bfff!important;
    border-radius:10px!important;
    box-shadow:0 2px 8px rgba(0,18,42,.22)!important;
    text-decoration:none!important;
    cursor:pointer!important;
    position:relative!important;
    transition:background .12s ease,border-color .12s ease,transform .12s ease,box-shadow .12s ease!important;
  }
  #ydesk #ydQaHardLinkV485:hover,
  #ydesk #ydQaHardLinkV485:focus-visible{
    background:#eaf5ff!important;
    border-color:#2f91ff!important;
    box-shadow:0 4px 12px rgba(0,18,42,.28)!important;
    transform:translateY(-1px)!important;
    outline:none!important;
  }
  #ydesk #ydQaHardLinkV485:after{
    content:'OPEN';
    position:absolute;
    top:5px;
    right:6px;
    padding:1px 4px;
    border-radius:999px;
    background:#0b72f4;
    color:#fff;
    font-size:6px;
    line-height:1.3;
    font-weight:950;
    letter-spacing:.25px;
  }
  #ydesk #ydQaHardLinkV485 b{color:#102842!important;font-size:15px!important}
}
</style>
'''


def _decorate_qa_control(html: str) -> str:
    html = inject_qa_hard_link(html)
    if 'ydQaButtonV487' not in html:
        html = html.replace('</head>', _QA_BUTTON_STYLE + '</head>', 1)
    return html


def _official_mobile_v1_html(version: str = "") -> str:
    html = _base_mobile_v1_html(version)
    html = html.replace("<title>Yipman</title>", "<title>Yipman Mobile V1</title>", 1)
    html = html.replace(
        'content="Yipman">',
        'content="Yipman Mobile V1">',
        1,
    )
    return html


def _official_yipman_html(version: str = "") -> str:
    # This renderer serves the URL the store actually uses: /yipman#data.
    return _decorate_qa_control(_base_yipman_html(version))


def _official_backoffice_html(version: str = "") -> str:
    html = _base_backoffice_html(version)
    html = html.replace("<title>Yipman</title>", "<title>Yipman Back Office</title>", 1)
    return _decorate_qa_control(html)


_api.yipman_v1_html = _official_mobile_v1_html
_api.yipman_html = _official_yipman_html
_api.backoffice_html = _official_backoffice_html

# Dedicated server-rendered target for the QA Holds hyperlink.
register_qa_page(app, version=_api.VERSION, qa_loader=_api.backoffice_qa_review)

app.state.yipman_product_channels = {
    "mobile": {
        "name": "Yipman Mobile V1",
        "path": "/app/yipman-v1/",
        "install_path": "/app/yipman-v1/install/",
        "status": "production",
    },
    "desktop": {
        "name": "Yipman Back Office",
        "path": "/yipman",
        "alternate_path": "/app/backoffice",
        "status": "production",
    },
    "legacy": {
        "path": "/app/yipman",
        "status": "compatibility-only",
    },
}
