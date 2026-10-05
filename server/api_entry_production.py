from __future__ import annotations

"""Stable production API entrypoint.

Product channels are intentionally fixed:
- Mobile: Yipman Mobile V1 -> /app/yipman-v1/
- Desktop: Yipman Back Office -> /app/backoffice

Versioned api_entry_v* modules are implementation layers only. The service
launcher must import this module so future internal releases do not create a
new production app identity or deployment entrypoint.
"""

import api as _api
import api_entry_v481 as _current

app = _current.app

# Apply product-channel branding at the stable production boundary. This keeps
# the underlying operational HTML/JS and data contracts unchanged.
_base_mobile_v1_html = _api.yipman_v1_html
_base_backoffice_html = _api.backoffice_html


def _official_mobile_v1_html(version: str = "") -> str:
    html = _base_mobile_v1_html(version)
    html = html.replace("<title>Yipman</title>", "<title>Yipman Mobile V1</title>", 1)
    html = html.replace(
        'content="Yipman">',
        'content="Yipman Mobile V1">',
        1,
    )
    return html


def _official_backoffice_html(version: str = "") -> str:
    html = _base_backoffice_html(version)
    return html.replace("<title>Yipman</title>", "<title>Yipman Back Office</title>", 1)


_api.yipman_v1_html = _official_mobile_v1_html
_api.backoffice_html = _official_backoffice_html

# Expose channel metadata for diagnostics without introducing another UI route.
app.state.yipman_product_channels = {
    "mobile": {
        "name": "Yipman Mobile V1",
        "path": "/app/yipman-v1/",
        "install_path": "/app/yipman-v1/install/",
        "status": "production",
    },
    "desktop": {
        "name": "Yipman Back Office",
        "path": "/app/backoffice",
        "status": "production",
    },
    "legacy": {
        "path": "/app/yipman",
        "status": "compatibility-only",
    },
}
