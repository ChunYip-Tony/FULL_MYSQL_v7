from __future__ import annotations

"""Hard-navigation fallback for Yipman desktop QA Holds.

The desktop shell is assembled by JavaScript, so injected event handlers can be
fragile when the shell is replaced or a browser retains an older runtime. This
patch changes the shell template itself: QA Holds becomes a normal hyperlink to
a server-rendered QA review page. Navigation therefore works even when no
optional overlay JavaScript runs.
"""

from html import escape
from fastapi.responses import HTMLResponse

_LINK_MARKER = 'ydQaHardLinkV485'


def inject_qa_hard_link(html: str) -> str:
    """Replace the QA Holds stat in the desktop shell with a real hyperlink."""
    if _LINK_MARKER in html:
        return html

    escaped_old = '<div class=\\"topstat\\">QA holds<b id=\\"ydQc\\">—</b></div>'
    escaped_new = (
        '<a id=\\"ydQaHardLinkV485\\" class=\\"topstat\\" '
        'href=\\"/app/backoffice/qa\\" '
        'style=\\"color:inherit;text-decoration:none;cursor:pointer\\" '
        'title=\\"Open QA Fixes\\">QA holds<b id=\\"ydQc\\">—</b></a>'
    )
    if escaped_old in html:
        return html.replace(escaped_old, escaped_new, 1)

    plain_old = '<div class="topstat">QA holds<b id="ydQc">—</b></div>'
    plain_new = (
        '<a id="ydQaHardLinkV485" class="topstat" href="/app/backoffice/qa" '
        'style="color:inherit;text-decoration:none;cursor:pointer" '
        'title="Open QA Fixes">QA holds<b id="ydQc">—</b></a>'
    )
    return html.replace(plain_old, plain_new, 1)


def _num(value, default='—') -> str:
    if value is None or value == '':
        return default
    return escape(str(value))


def _qa_page_html(version: str, qa_payload: dict) -> str:
    issues = list(qa_payload.get('issues') or [])
    severity_rank = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    issues.sort(key=lambda x: (
        severity_rank.get(str(x.get('severity') or '').upper(), 9),
        str(x.get('issue_code') or ''),
        str(x.get('entity_key') or ''),
    ))

    rows = []
    for x in issues:
        cur = x.get('current') or {}
        sev = str(x.get('severity') or '—').upper()
        sev_class = 'bad' if sev in {'HIGH', 'CRITICAL'} else ('warn' if sev == 'MEDIUM' else 'info')
        entity = escape(str(x.get('entity_key') or '—'))
        issue = escape(str(x.get('issue_code') or '—'))
        summary = escape(str(x.get('issue_summary') or ''))
        item = escape(str(cur.get('item_name') or cur.get('selling_description') or x.get('entity_type') or ''))
        family_no = cur.get('main_article_number')
        family_desc = escape(str(cur.get('family_description') or ''))
        family = ''
        if family_no:
            family = f'<div class="muted">Family {escape(str(family_no))}' + (f' · {family_desc}' if family_desc else '') + '</div>'
        uom = cur.get('selling_uom')
        cost = cur.get('current_cost_per_selling_unit')
        oh = cur.get('current_oh')
        oh_uom = cur.get('current_oh_uom') or ''
        vel = cur.get('upc_velocity_7d')
        state_parts = []
        if uom:
            state_parts.append('Selling UOM ' + escape(str(uom)))
        if cost is not None:
            try:
                state_parts.append(f'Cost ${float(cost):.2f}')
            except Exception:
                state_parts.append('Cost ' + escape(str(cost)))
        state = ' · '.join(state_parts) or 'Missing serving authority'
        review = 'USER CONFIRM' if x.get('can_fix') else 'VIEW ONLY'
        rows.append(
            '<tr>'
            f'<td><span class="sev {sev_class}">{escape(sev)}</span><b>{issue}</b><div class="muted">{summary}</div></td>'
            f'<td><b>{entity}</b><div class="muted">{item}</div>{family}</td>'
            f'<td><b>{_num(oh)} {escape(str(oh_uom))}</b><div class="muted">7D velocity {_num(vel)} {escape(str(uom or ""))}/day</div></td>'
            f'<td>{state}</td>'
            f'<td><span class="review">{review}</span></td>'
            '</tr>'
        )

    body = ''.join(rows) if rows else '<tr><td colspan="5" class="empty">No open QA issues.</td></tr>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yipman QA Fixes</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f7fb;color:#10233d;font-family:Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif}}
.top{{position:sticky;top:0;z-index:5;height:64px;padding:0 24px;display:flex;align-items:center;gap:14px;background:#133552;color:#fff;box-shadow:0 2px 12px rgba(0,20,40,.14)}}
.brand{{font-size:25px;font-weight:900}}.brand span{{color:#2b8cff}}.back{{margin-left:auto;color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.3);border-radius:9px;padding:9px 12px;font-size:12px;font-weight:800}}
.wrap{{padding:22px;max-width:1500px;margin:auto}}h1{{margin:0;font-size:30px}}.sub{{margin:5px 0 16px;color:#6b7d92;font-size:12px}}.summary{{display:flex;gap:10px;margin:0 0 12px}}.kpi{{background:#fff;border:1px solid #dbe5ef;border-radius:10px;padding:10px 13px;min-width:140px}}.kpi small{{display:block;color:#718197;font-size:9px;text-transform:uppercase;font-weight:900}}.kpi b{{font-size:21px}}
.card{{background:#fff;border:1px solid #dbe5ef;border-radius:12px;overflow:hidden;box-shadow:0 6px 22px rgba(20,45,70,.05)}}.tablewrap{{overflow:auto;max-height:calc(100vh - 220px)}}table{{width:100%;border-collapse:collapse;table-layout:fixed}}th{{position:sticky;top:0;background:#f8fbfe;border-bottom:1px solid #dce6ef;padding:10px;text-align:left;font-size:9px;text-transform:uppercase;color:#718197}}td{{padding:11px 10px;border-bottom:1px solid #edf2f6;vertical-align:top;font-size:11px;overflow-wrap:anywhere}}th:nth-child(1){{width:31%}}th:nth-child(2){{width:24%}}th:nth-child(3){{width:14%}}th:nth-child(4){{width:21%}}th:nth-child(5){{width:10%}}
.sev{{display:inline-flex;margin-right:7px;border-radius:999px;padding:3px 7px;font-size:8px;font-weight:900}}.sev.bad{{background:#ffe8ec;color:#b93148}}.sev.warn{{background:#fff2d5;color:#8d6100}}.sev.info{{background:#e9f3ff;color:#1764b8}}.muted{{color:#718197;font-size:9px;margin-top:4px;line-height:1.35}}.review{{display:inline-flex;border-radius:999px;padding:4px 7px;background:#fff2d5;color:#8d6100;font-size:8px;font-weight:900}}.empty{{padding:36px;text-align:center;color:#718197}}.ver{{font-size:9px;color:#92a3b6}}
</style></head><body>
<div class="top"><div class="brand">Yip<span>man</span></div><div><b>QA Fixes</b><div class="ver">v{escape(version)}</div></div><a class="back" href="/app/backoffice#data">← Back to Data Center</a></div>
<main class="wrap"><h1>QA Fixes</h1><div class="sub">Live open QA review. Raw source rows are not changed from this page.</div>
<div class="summary"><div class="kpi"><small>Open QA issues</small><b>{len(issues)}</b></div><div class="kpi"><small>High / Critical</small><b>{sum(1 for x in issues if str(x.get('severity') or '').upper() in {'HIGH','CRITICAL'})}</b></div><div class="kpi"><small>User-fixable</small><b>{sum(1 for x in issues if x.get('can_fix'))}</b></div></div>
<div class="card"><div class="tablewrap"><table><thead><tr><th>Issue</th><th>Entity / Item</th><th>Activity</th><th>Current State</th><th>Review</th></tr></thead><tbody>{body}</tbody></table></div></div></main></body></html>'''


def register_qa_page(app, *, version: str, qa_loader) -> None:
    existing = {getattr(route, 'path', None) for route in app.routes}
    if '/app/backoffice/qa' in existing:
        return

    async def qa_page():
        try:
            payload = qa_loader(limit=300)
            if not isinstance(payload, dict):
                payload = {'issues': []}
            return HTMLResponse(
                _qa_page_html(version, payload),
                headers={'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'},
            )
        except Exception as exc:
            return HTMLResponse(
                '<h1>QA Fixes unavailable</h1><p>' + escape(str(exc)) + '</p><p><a href="/app/backoffice#data">Back to Data Center</a></p>',
                status_code=500,
                headers={'Cache-Control': 'no-store'},
            )

    app.add_api_route('/app/backoffice/qa', qa_page, methods=['GET'], response_class=HTMLResponse, include_in_schema=False)
