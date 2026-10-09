from __future__ import annotations

"""Make TPR Progress explicit, fail-closed, and aligned to the authoritative payload."""


def polish_tpr_progress_clarity_html(html: str) -> str:
    marker = "yipmanV1TprProgressClarity"
    if marker in html:
        return html

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

    # Backend current_tpr_review publishes current_tpr_price and tpr_velocity_3d.
    # Older UI aliases looked only for current_price/tpr_velocity, which made valid
    # authoritative evidence appear missing in the card.
    anchor = "function isActiveTprProgress(p){"
    helper = "function tprCurrentPrice(p){return progressNum(p?.current_tpr_price??p?.current_price??p?.tpr_price??p?.active_price)}\nfunction tprActualVelocity(p){return progressNum(p?.tpr_velocity_3d??p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity)}\nfunction tprReadinessBlocked(p){const r=String(p?.readiness??p?.quick_check_status??'').trim().toUpperCase(),b=String(p?.blocking_reason??'').trim();return (!!r&&r!=='READY')||!!b}\nfunction tprEvidenceReady(p){const cur=tprCurrentPrice(p),oh=progressNum(p?.effective_oh??p?.current_oh),actual=tprActualVelocity(p),code=String(p?.recommendation_code||p?.recommendation_label||'').trim();return cur!==null&&oh!==null&&actual!==null&&!!code&&!tprReadinessBlocked(p)}\nfunction tprMissingEvidence(p){const m=[];if(tprCurrentPrice(p)===null)m.push('current TPR price');if(progressNum(p?.effective_oh??p?.current_oh)===null)m.push('Effective OH');if(tprActualVelocity(p)===null)m.push('TPR sales velocity');if(!String(p?.recommendation_code||p?.recommendation_label||'').trim())m.push('backend recommendation');if(tprReadinessBlocked(p))m.push(String(p?.blocking_reason||'item readiness'));return [...new Set(m)]}\n"
    if anchor in html:
        html = html.replace(anchor, helper + anchor, 1)

    # Replace the field aliases used by the original progress renderer with the
    # authoritative contract fields before the renderer executes.
    html = html.replace(
        "cur=p?.current_price??p?.tpr_price??p?.active_price",
        "cur=p?.current_tpr_price??p?.current_price??p?.tpr_price??p?.active_price",
    )
    html = html.replace(
        "actual=p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity",
        "actual=p?.tpr_velocity_3d??p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity",
    )
    html = html.replace(
        "backendPrice=progressNum(p?.current_price??p?.tpr_price??p?.active_price)",
        "backendPrice=tprCurrentPrice(p)",
    )

    old_state = "function tprProgressState(p){const raw=String(p?.progress_status??p?.pacing_status??p?.sell_through_status??p?.recommendation_status??'').toUpperCase();if(raw.includes('BEHIND'))return'BEHIND';if(raw.includes('AHEAD'))return'AHEAD';if(raw.includes('TRACK'))return'ON TRACK';const clear=progressNum(p?.projected_days_to_clear_oh),remain=progressNum(p?.days_remaining??p?.remaining_days_to_threshold);if(clear!==null&&remain!==null)return clear<=remain?'ON TRACK':'BEHIND';const cur=progressNum(p?.current_price??p?.tpr_price??p?.active_price),actual=progressNum(p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity),oh=progressNum(p?.effective_oh??p?.current_oh);if(cur===null||actual===null||oh===null)return'DATA NEEDED';return'ACTIVE'}"
    new_state = "function tprProgressState(p){if(!tprEvidenceReady(p))return'DATA NEEDED';const raw=String(p?.progress_status??p?.pacing_status??p?.sell_through_status??p?.recommendation_status??'').toUpperCase();if(raw.includes('BEHIND'))return'BEHIND';if(raw.includes('AHEAD'))return'AHEAD';if(raw.includes('TRACK'))return'ON TRACK';const clear=progressNum(p?.projected_days_to_clear_oh),remain=progressNum(p?.days_remaining??p?.remaining_days_to_threshold);if(clear!==null&&remain!==null)return clear<=remain?'ON TRACK':'BEHIND';return'ACTIVE'}"
    if old_state in html:
        html = html.replace(old_state, new_state, 1)

    html = html.replace(
        "${reg==null?'—':money(reg)} → ${cur==null?'—':money(cur)}",
        "${reg==null?'—':money(reg)} → ${cur==null?'DATA NEEDED':money(cur)}",
        1,
    )

    old_reason = "reason=String(p?.recommendation_reason||'Active TPR lifecycle tracking on completed valid POS days.');return `<div class=\"direct-card tpr-progress-card\">"
    new_reason = "missing=tprMissingEvidence(p),ready=tprEvidenceReady(p),reason=ready?String(p?.recommendation_reason||'Active TPR lifecycle tracking on completed valid POS days.'):`Cannot evaluate current TPR yet. Missing: ${missing.join(', ')}.`;return `<div class=\"direct-card tpr-progress-card ${ready?'':'tpr-progress-incomplete'}\">"
    if old_reason in html:
        html = html.replace(old_reason, new_reason, 1)

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
