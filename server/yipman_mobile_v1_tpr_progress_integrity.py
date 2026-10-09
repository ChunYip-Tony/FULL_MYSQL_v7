from __future__ import annotations

"""TPR Progress integrity guard.

The active-TPR page must never turn missing evidence into a KEEP decision or
zero-valued performance.  A card can remain visible because the UPC is truly on
TPR, but incomplete metrics are explicitly marked DATA NEEDED / NOT ENOUGH DATA.
"""


def polish_tpr_progress_integrity_html(html: str) -> str:
    marker = "yipmanV1TprProgressIntegrity"
    if marker in html:
        return html

    # pctText(unknown) used to render 0.0%, which falsely looked like measured
    # performance. Preserve unknown as an em dash everywhere in TPR progress.
    html = html.replace(
        "function pctText(v){const n=Number(v);if(!Number.isFinite(n))return '—';return (n>0?'+':'')+n.toFixed(1)+'%'}",
        "function pctText(v){if(v===null||v===undefined||v==='')return '—';const n=Number(v);if(!Number.isFinite(n))return '—';return (n>0?'+':'')+n.toFixed(1)+'%'}",
        1,
    )

    # dayText(null) had the same Number(null) => 0 problem. This is the direct
    # cause of misleading DAYS TO CLEAR 0 when no calculation exists.
    html = html.replace(
        "function dayText(v){const n=Number(v);return Number.isFinite(n)?n.toFixed(n%1?1:0):'—'}",
        "function dayText(v){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toFixed(n%1?1:0):'—'}",
        1,
    )

    # The previous guard only changed the displayed decision to DATA NEEDED
    # when current price itself was absent. The screenshot case has a regular
    # price but no observed TPR price, OH or velocity; it must fail closed too.
    old = "${cur==null?'DATA NEEDED':esc(decision)}</div><div class=\"why\"><b>Status:</b>"
    new = "${state==='DATA NEEDED'?'DATA NEEDED':esc(decision)}</div><div class=\"why\"><b>Status:</b>"
    html = html.replace(old, new, 1)

    # Replace the generic recommendation reason when the evidence set is not
    # sufficient. Do not tell the user to KEEP a TPR unchanged merely because
    # price/cost/readiness is unresolved.
    old_reason = "${esc(state)}</span> · ${esc(reason)}</div>"
    new_reason = "${esc(state)}</span> · ${esc(state==='DATA NEEDED'?'Missing TPR price, Effective OH, or completed POS velocity. No keep/change decision until required evidence is available.':reason)}</div>"
    html = html.replace(old_reason, new_reason, 1)

    # REG -> TPR should never display '$7.99 -> —' as if it were a usable
    # comparison. Explicitly identify the missing observed TPR price.
    old_price = "${reg==null?'—':money(reg)} → ${cur==null?'—':money(cur)}"
    new_price = "${reg==null?'—':money(reg)} → ${cur==null?'TPR PRICE NEEDED':money(cur)}"
    html = html.replace(old_price, new_price, 1)

    # Give the True Stock control a stronger call-to-action when OH is absent.
    old_oh = "<div class=\"stat\"><b>EFF OH</b><span>${ohNow==null?'—':esc(fmt(ohNow,1))}</span></div>"
    new_oh = "<div class=\"stat\"><b>EFF OH</b><span>${ohNow==null?'ENTER TRUE STOCK':esc(fmt(ohNow,1))}</span></div>"
    html = html.replace(old_oh, new_oh, 1)

    tag = '<script id="yipmanV1TprProgressIntegrity">window.YIPMAN_TPR_PROGRESS_INTEGRITY=true;</script>'
    return html.replace("</head>", tag + "\n</head>", 1)
