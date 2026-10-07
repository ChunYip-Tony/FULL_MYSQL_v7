from __future__ import annotations

"""Non-disruptive preview route for the exact-mock YipMan Mobile V1 RC."""

import api as _api
from fastapi.responses import HTMLResponse
from yipman_mobile_v1_exact_shell import yipman_mobile_v1_exact_html
from yipman_mobile_v1_price_guard import guard_price_html
from yipman_mobile_v1_price_polish import polish_price_html
from yipman_mobile_v1_interactions import polish_interactions_html
from yipman_mobile_v1_quick_search_polish import polish_quick_search_html
from yipman_mobile_v1_order_detail import polish_order_detail_html

_INSTALLED = False


def install_mobile_v1_rc_route(app) -> None:
    """Expose the exact-mock RC without changing /app/yipman-v1/."""
    global _INSTALLED
    if _INSTALLED:
        return

    version = str(getattr(_api, "VERSION", ""))

    def rc_page():
        html = yipman_mobile_v1_exact_html(version)
        html = guard_price_html(html)
        html = polish_price_html(html)
        html = polish_quick_search_html(html)
        html = polish_interactions_html(html)
        html = polish_order_detail_html(html)
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-YipMan-Mobile-V1-RC": "exact-mock-shell-price-guard-polish-fast-search-interactions-order-family-detail",
            },
        )

    app.add_api_route(
        "/app/yipman-v1-rc/",
        rc_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="yipman_mobile_v1_exact_mock_rc",
    )
    app.add_api_route(
        "/app/yipman-v1-rc",
        rc_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="yipman_mobile_v1_exact_mock_rc_noslash",
    )
    app.state.yipman_mobile_v1_consolidated_rc = {
        "enabled": True,
        "path": "/app/yipman-v1-rc/",
        "production_v1_unchanged": True,
        "shell": "exact-mock",
        "price_guard": True,
        "price_polish": True,
        "quick_search_fast_enriched": True,
        "card_detail": True,
        "order_family_detail": True,
        "true_stock_inline": True,
    }
    _INSTALLED = True
