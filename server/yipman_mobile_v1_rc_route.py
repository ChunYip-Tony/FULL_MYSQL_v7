from __future__ import annotations

"""Non-disruptive preview route for the consolidated YipMan Mobile V1 RC."""

import api as _api
from fastapi.responses import HTMLResponse
from yipman_mobile_v1_consolidated_rc import _decorate_html
from yipman_mobile_v1_rc_polish import polish_rc_html

_INSTALLED = False


def install_mobile_v1_rc_route(app) -> None:
    """Expose the consolidated RC without changing /app/yipman-v1/."""
    global _INSTALLED
    if _INSTALLED:
        return

    base_renderer = _api.yipman_v1_html
    version = str(getattr(_api, "VERSION", ""))

    def rc_page():
        html = _decorate_html(base_renderer(version), version)
        html = polish_rc_html(html, version)
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-YipMan-Mobile-V1-RC": "consolidated-polish-1",
            },
        )

    app.add_api_route(
        "/app/yipman-v1-rc/",
        rc_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="yipman_mobile_v1_consolidated_rc",
    )
    app.add_api_route(
        "/app/yipman-v1-rc",
        rc_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="yipman_mobile_v1_consolidated_rc_noslash",
    )
    app.state.yipman_mobile_v1_consolidated_rc = {
        "enabled": True,
        "path": "/app/yipman-v1-rc/",
        "production_v1_unchanged": True,
        "polish": "1",
    }
    _INSTALLED = True
