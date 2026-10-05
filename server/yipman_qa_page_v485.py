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
            f'<td><b>{entity}</b><div class="muted item">{item}</div>{family}</td>'
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
*{{box-sizing:border-box}}
body{{margin:0;background:#f3f7fb;color:#10233d;font-family:Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif;font-size:15px;line-height:1.45}}
.top{{position:sticky;top:0;z-index:5;min-height:76px;padding:10px 26px;display:flex;align-items:center;gap:16px;background:#133552;color:#fff;box-shadow:0 2px 12px rgba(0,20,40,.14)}}
.brand{{font-size:32px;font-weight:900;line-height:1}}.brand span{{color:#2b8cff}}
.top b{{font-size:16px}}.back{{margin-left:auto;color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.38);border-radius:10px;padding:11px 15px;font-size:14px;font-weight:850;background:rgba(255,255,255,.07)}}.back:hover{{background:rgba(255,255,255,.14)}}
.wrap{{padding:26px;max-width:1680px;margin:auto}}h1{{margin:0;font-size:36px;line-height:1.1}}.sub{{margin:7px 0 18px;color:#5f7288;font-size:14px;line-height:1.45}}
.summary{{display:flex;gap:12px;margin:0 0 15px;flex-wrap:wrap}}.kpi{{background:#fff;border:1px solid #dbe5ef;border-radius:11px;padding:12px 15px;min-width:170px}}.kpi small{{display:block;color:#718197;font-size:11px;text-transform:uppercase;font-weight:900;letter-spacing:.25px}}.kpi b{{font-size:26px;line-height:1.15}}
.card{{background:#fff;border:1px solid #dbe5ef;border-radius:12px;overflow:hidden;box-shadow:0 6px 22px rgba(20,45,70,.05)}}.tablewrap{{overflow:auto;max-height:calc(100vh - 248px)}}table{{width:100%;border-collapse:collapse;table-layout:fixed}}
th{{position:sticky;top:0;background:#f8fbfe;border-bottom:1px solid #dce6ef;padding:12px 11px;text-align:left;font-size:11px;text-transform:uppercase;color:#65788e;line-height:1.3;letter-spacing:.25px}}
td{{padding:14px 11px;border-bottom:1px solid #edf2f6;vertical-align:top;font-size:14px;line-height:1.48;overflow-wrap:anywhere;word-break:normal}}
th:nth-child(1){{width:31%}}th:nth-child(2){{width:24%}}th:nth-child(3){{width:14%}}th:nth-child(4){{width:21%}}th:nth-child(5){{width:10%}}
td b{{font-size:14.5px;line-height:1.4}}
.sev{{display:inline-flex;margin-right:8px;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:900;vertical-align:1px}}.sev.bad{{background:#ffe8ec;color:#b93148}}.sev.warn{{background:#fff2d5;color:#8d6100}}.sev.info{{background:#e9f3ff;color:#1764b8}}
.muted{{color:#67798d;font-size:12px;margin-top:5px;line-height:1.45}}.muted.item{{font-size:12.5px;color:#52677d}}
.review{{display:inline-flex;border-radius:999px;padding:6px 9px;background:#fff2d5;color:#8d6100;font-size:10.5px;font-weight:900;line-height:1.2}}.empty{{padding:42px;text-align:center;color:#718197;font-size:15px}}.ver{{font-size:11px;color:#b5c4d2;margin-top:2px}}
@media (max-width:1000px){{
  body{{font-size:14px}}.wrap{{padding:16px}}h1{{font-size:31px}}.tablewrap{{max-height:none}}table{{table-layout:auto;min-width:920px}}td{{font-size:13px}}.muted{{font-size:11.5px}}
}}
</style></head><body>
<div class="top"><div class="brand">Yip<span>man</span></div><div><b>QA Fixes</b><div class="ver">v{escape(version)}</div></div><a class="back" href="/yipman#data">← Back to Data Center</a></div>
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
                '<h1>QA Fixes unavailable</h1><p>' + escape(str(exc)) + '</p><p><a href="/yipman#data">Back to Data Center</a></p>',
                status_code=500,
                headers={'Cache-Control': 'no-store'},
            )

    app.add_api_route('/app/backoffice/qa', qa_page, methods=['GET'], response_class=HTMLResponse, include_in_schema=False)
