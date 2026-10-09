from __future__ import annotations

"""Make TPR Progress fail visibly closed when the evidence required to judge it is missing.

The existing guard prevents a fabricated KEEP decision, but the card can still look like a
normal active evaluation with misleading zeroes (0/day, 0.0%, days-to-clear 0). This patch
makes missing evidence explicit and removes those synthetic-looking zero values.
"""


def polish_tpr_progress_clarity_html(html: str) -> str:
    marker = "yipmanV1TprProgressClarity"
    if marker in html:
        return html

    # Null is not zero. These helpers are used throughout the TPR progress card.
    html = html.replace(
        "function pctText(v){const n=Number(v);if(!Number.isFinite(n))return '—';return (n>0?'+':'')+n.toFixed(1)+'%'}",
        "function pctText(v){if(v===null||v===undefined||v==='')return '—';const n=Number(v);if(!Number.isFinite(n))return '—';return (n>0?'+':'')+n.toFixed(1)+'%'}",
        1,
    )
    html = html.replace(
        "function dayText(v){const n=Number(v);return Number.isFinite(n)?n.toFixed(n%1?1:0):'—'}",
        "function dayText(v){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toFixed(n%1?1:0):'—'}",
        1,
    )

    # Add one authoritative readiness gate for the visible card. Current TPR price alone is
    # not enough to recommend KEEP/LOWER/END: we need OH plus observed velocity and a backend
    # recommendation. This mirrors the fail-closed business rule instead of guessing.
    anchor = "function isActiveTprProgress(p){"
    helper = "function tprEvidenceReady(p){const cur=progressNum(p?.current_price??p?.tpr_price??p?.active_price),oh=progressNum(p?.effective_oh??p?.current_oh),actual=progressNum(p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity),code=String(p?.recommendation_code||p?.recommendation_label||'').trim();return cur!==null&&oh!==null&&actual!==null&&!!code}\nfunction tprMissingEvidence(p){const m=[];if(progressNum(p?.current_price??p?.tpr_price??p?.active_price)===null)m.push('current TPR price');if(progressNum(p?.effective_oh??p?.current_oh)===null)m.push('Effective OH');if(progressNum(p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity)===null)m.push('TPR sales velocity');if(!String(p?.recommendation_code||p?.recommendation_label||'').trim())m.push('backend recommendation');return m}\n"
    if anchor in html:
        html = html.replace(anchor, helper + anchor, 1)

    # Do not display ACTIVE as though the evaluation is complete.
    old_state = "function tprProgressState(p){const raw=String(p?.progress_status??p?.pacing_status??p?.sell_through_status??p?.recommendation_status??'').toUpperCase();if(raw.includes('BEHIND'))return'BEHIND';if(raw.includes('AHEAD'))return'AHEAD';if(raw.includes('TRACK'))return'ON TRACK';const clear=progressNum(p?.projected_days_to_clear_oh),remain=progressNum(p?.days_remaining??p?.remaining_days_to_threshold);if(clear!==null&&remain!==null)return clear<=remain?'ON TRACK':'BEHIND';const cur=progressNum(p?.current_price??p?.tpr_price??p?.active_price),actual=progressNum(p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity),oh=progressNum(p?.effective_oh??p?.current_oh);if(cur===null||actual===null||oh===null)return'DATA NEEDED';return'ACTIVE'}"
    new_state = "function tprProgressState(p){if(!tprEvidenceReady(p))return'DATA NEEDED';const raw=String(p?.progress_status??p?.pacing_status??p?.sell_through_status??p?.recommendation_status??'').toUpperCase();if(raw.includes('BEHIND'))return'BEHIND';if(raw.includes('AHEAD'))return'AHEAD';if(raw.includes('TRACK'))return'ON TRACK';const clear=progressNum(p?.projected_days_to_clear_oh),remain=progressNum(p?.days_remaining??p?.remaining_days_to_threshold);if(clear!==null&&remain!==null)return clear<=remain?'ON TRACK':'BEHIND';return'ACTIVE'}"
    if old_state in html:
        html = html.replace(old_state, new_state, 1)

    # The current screenshot showed "$7.99 -> —" and a normal-looking KEEP TPR card. Make the
    # missing TPR price/evidence explicit instead of rendering a price transition to nowhere.
    html = html.replace(
        "${reg==null?'—':money(reg)} → ${cur==null?'—':money(cur)}",
        "${reg==null?'—':money(reg)} → ${cur==null?'DATA NEEDED':money(cur)}",
        1,
    )

    # Explain exactly why the card is blocked. This is more useful than the generic
    # 'price/cost/readiness data is resolved' wording visible in the screenshot.
    old_reason = "reason=String(p?.recommendation_reason||'Active TPR lifecycle tracking on completed valid POS days.');return `<div class=\"direct-card tpr-progress-card\">"
    new_reason = "missing=tprMissingEvidence(p),ready=tprEvidenceReady(p),reason=ready?String(p?.recommendation_reason||'Active TPR lifecycle tracking on completed valid POS days.'):`Cannot evaluate current TPR yet. Missing: ${missing.join(', ')}.`;return `<div class=\"direct-card tpr-progress-card ${ready?'':'tpr-progress-incomplete'}\">"
    if old_reason in html:
        html = html.replace(old_reason, new_reason, 1)

    # Decision must be blocked whenever the evidence gate is not ready, even if a stale
    # recommendation label happens to exist in the row.
    html = html.replace(
        "${cur==null?'DATA NEEDED':esc(decision)}</div><div class=\"why\"><b>Status:</b>",
        "${ready?esc(decision):'DATA NEEDED'}</div><div class=\"why\"><b>Status:</b>",
        1,
    )

    style = """
<style id="yipmanV1TprProgressClarityStyle">
.tpr-progress-card.tpr-progress-incomplete{border-left-color:#d39b4a!important}
.tpr-progress-card.tpr-progress-incomplete .actionbox{border-color:#765c35!important;background:#211b12!important}
.tpr-progress-card.tpr-progress-incomplete .progress-state{color:#f0c477!important}
.tpr-progress-card.tpr-progress-incomplete .action-value{color:#ffd58a!important}
</style>
"""
    html = html.replace("</head>", style + f'<script id="{marker}">window.YIPMAN_TPR_PROGRESS_CLARITY=true;</script>\n</head>', 1)
    return html
