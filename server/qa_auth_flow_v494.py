from __future__ import annotations

"""QA browser flow without an inline admin sign-in prompt.

QA review is always visible. The page no longer asks the store user for an
Admin ID or password. If an authorized write session already exists, the
manual Evidence-Backed Repair button is enabled; otherwise the page remains a
clean QA review surface. The protected repair POST keeps its existing server
write authorization.
"""

from html import escape

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

import api as _api
from qa_evidence_repair_v491 import run_evidence_backed_qa_repair
from yipman_qa_page_v485 import _qa_page_html, _repair_result_html

_QA_PATH = "/app/backoffice/qa"
_QA_REPAIR_PATH = "/app/backoffice/qa/repair"


def _session_actor(request: Request) -> str | None:
    try:
        return _api.admin_device_from_request(
            request,
            request.headers.get("authorization"),
            write=False,
        )
    except Exception:
        return None


def _remove_route(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == path
            and method in set(getattr(route, "methods", set()) or set())
        )
    ]


def install_qa_auth_flow_v494(app) -> None:
    if getattr(app.state, "qa_auth_flow_v494_installed", False):
        return

    _remove_route(app, _QA_PATH, "GET")
    _remove_route(app, _QA_REPAIR_PATH, "POST")

    async def qa_page(request: Request):
        try:
            payload = _api.backoffice_qa_review(limit=300)
            if not isinstance(payload, dict):
                payload = {"issues": []}
            actor = _session_actor(request)
            html = _qa_page_html(
                _api.VERSION,
                payload,
                repair_enabled=actor is not None,
            )
            return HTMLResponse(
                html,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "X-FULLMYSQL-QA-Auth-Flow": "v499-no-inline-admin-prompt",
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

    async def qa_repair(request: Request):
        try:
            actor = _api.admin_device_from_request(
                request,
                request.headers.get("authorization"),
                write=True,
            )
            result = run_evidence_backed_qa_repair(actor)
            return HTMLResponse(
                _repair_result_html(_api.VERSION, result),
                headers={
                    "Cache-Control": "no-store",
                    "X-FULLMYSQL-QA-Auth-Flow": "v499-no-inline-admin-prompt",
                },
            )
        except HTTPException as exc:
            return HTMLResponse(
                '<h1>QA repair not run</h1><p>'
                + escape(str(exc.detail or exc))
                + '</p><p><a href="/app/backoffice/qa">Back to QA Fixes</a></p>',
                status_code=int(exc.status_code or 500),
                headers={"Cache-Control": "no-store"},
            )
        except Exception as exc:
            return HTMLResponse(
                '<h1>QA repair not run</h1><p>'
                + escape(str(exc))
                + '</p><p><a href="/app/backoffice/qa">Back to QA Fixes</a></p>',
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
    app.add_api_route(
        _QA_REPAIR_PATH,
        qa_repair,
        methods=["POST"],
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    app.state.qa_auth_flow_v494_installed = True
