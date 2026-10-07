from __future__ import annotations

"""QA review UX: keep review visible without presenting an unusable repair action.

The protected repair POST remains unchanged. This module only replaces the QA
GET route so normal Back Office users can review issues without seeing an admin
prompt or a repair button that will fail.
"""

from html import escape
from fastapi.responses import HTMLResponse

import api as _api
from yipman_qa_page_v485 import _qa_page_html

_QA_PATH = "/app/backoffice/qa"


def _remove_get(app) -> None:
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == _QA_PATH
            and "GET" in set(getattr(route, "methods", set()) or set())
        )
    ]


def install_qa_review_only_v501(app) -> None:
    if getattr(app.state, "qa_review_only_v501_installed", False):
        return

    _remove_get(app)

    async def qa_page():
        try:
            payload = _api.backoffice_qa_review(limit=300)
            if not isinstance(payload, dict):
                payload = {"issues": []}
            html = _qa_page_html(_api.VERSION, payload, repair_enabled=False)
            html = html.replace(
                "Live open QA review. Raw source rows are not changed from this page.",
                "Live open QA review. No admin sign-in is required to review QA. Correct source data through the normal Back Office workflows; this page refreshes the resulting QA state.",
                1,
            )
            return HTMLResponse(
                html,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "X-FULLMYSQL-QA-Flow": "v501-review-only",
                },
            )
        except Exception as exc:
            return HTMLResponse(
                '<h1>QA Fixes unavailable</h1><p>'
                + escape(str(exc))
                + '</p><p><a href="/yipman#data">Back to Data Center</a></p>',
                status_code=500,
                headers={"Cache-Control": "no-store"},
            )

    app.add_api_route(
        _QA_PATH,
        qa_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    app.state.qa_review_only_v501_installed = True
