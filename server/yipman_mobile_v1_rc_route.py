from __future__ import annotations

"""Non-disruptive preview route for the exact-mock YipMan Mobile V1 RC."""

import json
from datetime import date

import api as _api
from fastapi.responses import HTMLResponse, Response
from yipman_mobile_v1_exact_shell import yipman_mobile_v1_exact_html
from yipman_mobile_v1_price_guard import guard_price_html
from yipman_mobile_v1_price_polish import polish_price_html
from yipman_mobile_v1_interactions import polish_interactions_html
from yipman_mobile_v1_quick_search_polish import polish_quick_search_html
from yipman_mobile_v1_order_detail import polish_order_detail_html
from yipman_mobile_v1_ordering_context import polish_ordering_context_html
from yipman_mobile_v1_loading_hotfix import polish_loading_html
from yipman_mobile_v1_navigation import polish_navigation_html
from yipman_mobile_v1_identity_guard import polish_identity_html
from yipman_mobile_v1_pwa import (
    install_html as pwa_install_html,
    polish_pwa_html,
    pwa_icon_svg,
    pwa_manifest,
    pwa_service_worker,
)

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
        html = polish_identity_html(html)
        html = polish_interactions_html(html)
        html = polish_order_detail_html(html)
        html = polish_ordering_context_html(html)
        html = polish_loading_html(html)
        html = polish_pwa_html(html)
        html = polish_navigation_html(html)
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-YipMan-Mobile-V1-RC": "exact-mock-shell-standalone-pwa-native-back-stack-upc-identity-guard-live-ordering-context-nonblocking-startup",
            },
        )

    def rc_ordering_review_live(
        category: str = "ALL",
        delivery_date: str | None = None,
        next_delivery_date: str | None = None,
    ):
        """RC-only uncached ordering review for the user's current viewing moment."""
        try:
            parsed_delivery = date.fromisoformat(delivery_date) if delivery_date else None
            parsed_next = date.fromisoformat(next_delivery_date) if next_delivery_date else None
            result = _api.backoffice_ordering_review(
                category=category,
                delivery_date=parsed_delivery,
                next_delivery_date=parsed_next,
                best_available_delivery_evidence=True,
            )
            if isinstance(result, dict):
                result = dict(result)
                result["viewing_moment_live"] = True
                result["calculation_basis"] = "CURRENT_EFFECTIVE_OH_AT_REQUEST_WITH_EXISTING_ORDERING_RULES"
            return Response(
                json.dumps(result, default=_api.j),
                media_type="application/json",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        except ValueError as exc:
            return Response(
                json.dumps({"status": "INVALID", "reason": str(exc)}),
                status_code=422,
                media_type="application/json",
                headers={"Cache-Control": "no-store"},
            )
        except Exception as exc:
            return Response(
                json.dumps({"status": "ERROR", "reason": str(exc)}),
                status_code=500,
                media_type="application/json",
                headers={"Cache-Control": "no-store"},
            )

    def rc_manifest():
        return Response(
            pwa_manifest(),
            media_type="application/manifest+json",
            headers={"Cache-Control": "no-cache"},
        )

    def rc_sw():
        return Response(
            pwa_service_worker(),
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/app/yipman-v1-rc/"},
        )

    def rc_icon():
        return Response(
            pwa_icon_svg(),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    def rc_install():
        return HTMLResponse(
            pwa_install_html(version),
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
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
    app.add_api_route(
        "/app/yipman-v1-rc/api/ordering-review-live",
        rc_ordering_review_live,
        methods=["GET"],
        include_in_schema=False,
        name="yipman_mobile_v1_rc_ordering_review_live",
    )
    app.add_api_route(
        "/app/yipman-v1-rc/manifest.webmanifest",
        rc_manifest,
        methods=["GET"],
        include_in_schema=False,
        name="yipman_mobile_v1_rc_manifest",
    )
    app.add_api_route(
        "/app/yipman-v1-rc/sw.js",
        rc_sw,
        methods=["GET"],
        include_in_schema=False,
        name="yipman_mobile_v1_rc_service_worker",
    )
    app.add_api_route(
        "/app/yipman-v1-rc/icon.svg",
        rc_icon,
        methods=["GET"],
        include_in_schema=False,
        name="yipman_mobile_v1_rc_icon",
    )
    app.add_api_route(
        "/app/yipman-v1-rc/install",
        rc_install,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="yipman_mobile_v1_rc_install",
    )
    app.add_api_route(
        "/app/yipman-v1-rc/install/",
        rc_install,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="yipman_mobile_v1_rc_install_slash",
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
        "standalone_pwa": True,
        "native_back_stack": True,
        "upc_identity_guard": True,
        "ordering_viewing_moment_live": True,
        "ordering_date_controls": True,
        "weekday_date_labels": True,
        "nonblocking_startup_ordering": True,
        "install_path": "/app/yipman-v1-rc/install",
    }
    _INSTALLED = True