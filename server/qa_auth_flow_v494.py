from __future__ import annotations

"""v7.0.494 QA repair authorization UX.

The evidence-backed repair remains admin-only. This module fixes the browser
workflow so an unauthenticated QA page never presents a repair button that can
only fail with "Admin session required".

Behavior:
- QA Fixes GET checks the existing signed admin-session cookie.
- Without a valid session, the page shows an inline Admin Sign In card and no
  repair submit control.
- Sign-in uses the existing /v1/admin/login endpoint and same-origin cookie.
- After successful sign-in the QA page reloads and enables the repair button.
- Repair POST still requires admin_device_from_request(..., write=True); there
  is no bypass and cross-origin write protection remains enforced.
"""

from html import escape
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

import api as _api
from qa_evidence_repair_v491 import run_evidence_backed_qa_repair
from yipman_qa_page_v485 import _qa_page_html, _repair_result_html


_QA_PATH = "/app/backoffice/qa"
_QA_REPAIR_PATH = "/app/backoffice/qa/repair"


_LOGIN_BLOCK = r'''
<style id="qaAuthV494Css">
.qa-auth-v494{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;background:#fff7e8;border:1px solid #f0c56b;border-radius:12px;padding:15px 16px;margin:0 0 15px}
.qa-auth-v494 .qa-auth-copy{min-width:260px;flex:1}.qa-auth-v494 .qa-auth-title{font-size:16px;font-weight:900;color:#734d00}.qa-auth-v494 .qa-auth-note{font-size:12px;color:#78684a;margin-top:4px;line-height:1.45}
.qa-auth-v494 .qa-auth-fields{display:grid;grid-template-columns:150px 220px auto;gap:8px;align-items:end}.qa-auth-v494 label{display:block;font-size:10px;font-weight:900;text-transform:uppercase;color:#7a6a4a;margin:0 0 4px}.qa-auth-v494 input{height:40px;border:1px solid #d7c49b;border-radius:9px;padding:0 10px;font-size:14px;background:#fff;color:#10233d;width:100%}.qa-auth-v494 button{height:40px;border:0;border-radius:9px;background:#0b72f4;color:#fff;font-size:13px;font-weight:900;padding:0 15px;cursor:pointer;white-space:nowrap}.qa-auth-v494 button:disabled{opacity:.6;cursor:wait}.qa-auth-v494 .qa-auth-msg{font-size:11px;margin-top:6px;color:#8a5b00;min-height:16px}.qa-auth-v494 .qa-auth-msg.bad{color:#b42318}
@media(max-width:900px){.qa-auth-v494{align-items:stretch;flex-direction:column}.qa-auth-v494 .qa-auth-fields{grid-template-columns:1fr}.qa-auth-v494 .qa-auth-fields>div{width:100%}}
</style>
<div class="qa-auth-v494" id="qaAuthV494">
  <div class="qa-auth-copy">
    <div class="qa-auth-title">Admin sign-in required for QA repair</div>
    <div class="qa-auth-note">QA review remains visible. Evidence-backed repair is a protected write action, so sign in here first. The repair never bypasses admin authorization.</div>
    <div class="qa-auth-msg" id="qaAuthMsgV494"></div>
  </div>
  <div class="qa-auth-fields">
    <div><label for="qaAdminIdV494">Admin ID</label><input id="qaAdminIdV494" value="admin" autocomplete="username"></div>
    <div><label for="qaAdminPasswordV494">Password</label><input id="qaAdminPasswordV494" type="password" autocomplete="current-password" placeholder="Password"></div>
    <button id="qaAdminLoginV494" type="button">Sign In</button>
  </div>
</div>
<script id="qaAuthV494Js">
(()=>{
  const id=document.getElementById('qaAdminIdV494');
  const pw=document.getElementById('qaAdminPasswordV494');
  const btn=document.getElementById('qaAdminLoginV494');
  const msg=document.getElementById('qaAuthMsgV494');
  if(!id||!pw||!btn||!msg)return;
  async function login(){
    const loginId=id.value.trim(),password=pw.value;
    if(!loginId||!password){msg.textContent='Enter Admin ID and password.';msg.className='qa-auth-msg bad';return}
    btn.disabled=true;msg.textContent='Signing in…';msg.className='qa-auth-msg';
    try{
      const r=await fetch('/v1/admin/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({login_id:loginId,password})});
      let body={};try{body=await r.json()}catch{}
      if(!r.ok){throw new Error(typeof body?.detail==='string'?body.detail:'Admin sign-in failed (HTTP '+r.status+').')}
      pw.value='';msg.textContent='Signed in. Enabling QA repair…';
      location.replace('/app/backoffice/qa?auth=ok');
    }catch(e){msg.textContent=e.message||String(e);msg.className='qa-auth-msg bad';btn.disabled=false;pw.focus()}
  }
  btn.addEventListener('click',login);
  pw.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();login()}});
})();
</script>
'''


_ADMIN_STATUS_BLOCK = '''<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;background:#eaf8ef;border:1px solid #b8e1c8;border-radius:10px;padding:9px 12px;margin:0 0 12px;font-size:12px;color:#17643d"><b>Admin session active · QA repair enabled</b><span>Protected write mode</span></div>'''


def _with_auth_ui(html: str, *, actor: str | None, auth_error: str | None = None) -> str:
    anchor = '<div class="card">'
    if actor:
        block = _ADMIN_STATUS_BLOCK
    else:
        block = _LOGIN_BLOCK
        if auth_error:
            safe = escape(auth_error)
            block = block.replace(
                '<div class="qa-auth-msg" id="qaAuthMsgV494"></div>',
                f'<div class="qa-auth-msg bad" id="qaAuthMsgV494">{safe}</div>',
                1,
            )
    return html.replace(anchor, block + anchor, 1)


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

    # Replace only the two server-rendered QA browser routes. The API review,
    # login, session and repair helpers remain the canonical implementations.
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
            html = _with_auth_ui(html, actor=actor)
            return HTMLResponse(
                html,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "X-FULLMYSQL-QA-Auth-Flow": "v494",
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
                    "X-FULLMYSQL-QA-Auth-Flow": "v494",
                },
            )
        except HTTPException as exc:
            code = int(exc.status_code or 500)
            if code in {401, 403}:
                try:
                    payload = _api.backoffice_qa_review(limit=300)
                    if not isinstance(payload, dict):
                        payload = {"issues": []}
                    html = _qa_page_html(_api.VERSION, payload, repair_enabled=False)
                    html = _with_auth_ui(
                        html,
                        actor=None,
                        auth_error=str(exc.detail or "Admin sign-in required."),
                    )
                    return HTMLResponse(
                        html,
                        status_code=code,
                        headers={
                            "Cache-Control": "no-store",
                            "X-FULLMYSQL-QA-Auth-Flow": "v494",
                        },
                    )
                except Exception:
                    pass
            return HTMLResponse(
                '<h1>QA repair not run</h1><p>'
                + escape(str(exc.detail or exc))
                + '</p><p><a href="/app/backoffice/qa">Back to QA Fixes</a></p>',
                status_code=code,
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
