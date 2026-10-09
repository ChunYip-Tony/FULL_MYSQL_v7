from __future__ import annotations

"""Fail closed when TPR Progress lacks enough evidence for a real decision."""


def polish_tpr_progress_guard_html(html: str) -> str:
    marker = "yipmanV1TprProgressGuard"
    if marker in html:
        return html

    old_decision = "function tprProgressDecision(p){const code=String(p?.recommendation_code||p?.recommendation_label||'CONTINUE').toUpperCase().replaceAll('_',' ');const next=p?.suggested_regular_price??p?.suggested_tpr_price;const label=code.includes('CANCEL')||code.includes('END')?'END TPR':code.includes('LOWER')?'LOWER TPR':code.includes('RAISE')?'RAISE TPR':code.includes('REG')?'RETURN TO REG':'KEEP TPR';return next!=null?label+' '+money(next):label}"
    new_decision = "function tprProgressDecision(p){const code=String(p?.recommendation_code||p?.recommendation_label||'').toUpperCase().replaceAll('_',' '),next=p?.suggested_regular_price??p?.suggested_tpr_price,cur=progressNum(p?.current_price??p?.tpr_price??p?.active_price),hasDecision=!!code;let label=code.includes('CANCEL')||code.includes('END')?'END TPR':code.includes('LOWER')?'LOWER TPR':code.includes('RAISE')?'RAISE TPR':code.includes('REG')?'RETURN TO REG':code.includes('CONTINUE')||code.includes('KEEP')?'KEEP TPR':'REVIEW TPR';if(!hasDecision||cur===null)return 'DATA NEEDED';return next!=null?label+' '+money(next):label}"
    if old_decision in html:
        html = html.replace(old_decision, new_decision, 1)

    old_state = "function tprProgressState(p){const raw=String(p?.progress_status??p?.pacing_status??p?.sell_through_status??p?.recommendation_status??'').toUpperCase();if(raw.includes('BEHIND'))return'BEHIND';if(raw.includes('AHEAD'))return'AHEAD';if(raw.includes('TRACK'))return'ON TRACK';const clear=progressNum(p?.projected_days_to_clear_oh),remain=progressNum(p?.days_remaining??p?.remaining_days_to_threshold);if(clear!==null&&remain!==null)return clear<=remain?'ON TRACK':'BEHIND';return'ACTIVE'}"
    new_state = "function tprProgressState(p){const raw=String(p?.progress_status??p?.pacing_status??p?.sell_through_status??p?.recommendation_status??'').toUpperCase();if(raw.includes('BEHIND'))return'BEHIND';if(raw.includes('AHEAD'))return'AHEAD';if(raw.includes('TRACK'))return'ON TRACK';const clear=progressNum(p?.projected_days_to_clear_oh),remain=progressNum(p?.days_remaining??p?.remaining_days_to_threshold);if(clear!==null&&remain!==null)return clear<=remain?'ON TRACK':'BEHIND';const cur=progressNum(p?.current_price??p?.tpr_price??p?.active_price),actual=progressNum(p?.tpr_velocity??p?.current_behavior?.velocity??p?.current_velocity),oh=progressNum(p?.effective_oh??p?.current_oh);if(cur===null||actual===null||oh===null)return'DATA NEEDED';return'ACTIVE'}"
    if old_state in html:
        html = html.replace(old_state, new_state, 1)

    html = html.replace("${esc(decision)}</div><div class=\"why\"><b>Status:</b>", "${cur==null?'DATA NEEDED':esc(decision)}</div><div class=\"why\"><b>Status:</b>", 1)
    html = html.replace("<span>${esc(dayText(clear))}</span></div>", "<span>${clear==null?'—':esc(dayText(clear))}</span></div>", 1)
    html = html.replace("<span>${esc(pctText(vel))}</span></div><div><b>GP$/DAY Δ</b><span>${esc(pctText(gp))}</span>", "<span>${vel==null?'—':esc(pctText(vel))}</span></div><div><b>GP$/DAY Δ</b><span>${gp==null?'—':esc(pctText(gp))}</span>", 1)
    html = html.replace("const rows=[...tprProgressByUpc.values()].filter(isActiveTprProgress);", "const rows=[...tprProgressByUpc.values()].filter(isActiveTprProgress);rows.sort((a,b)=>{const sa=tprProgressState(a),sb=tprProgressState(b),rank=x=>x==='BEHIND'?0:x==='DATA NEEDED'?1:2;return rank(sa)-rank(sb)});", 1)
    html = html.replace("rows.filter(x=>tprProgressState(x)==='BEHIND').length", "rows.filter(x=>['BEHIND','DATA NEEDED'].includes(tprProgressState(x))).length", 1)

    tag = '<script id="yipmanV1TprProgressGuard">window.YIPMAN_TPR_PROGRESS_GUARD=true;</script>'
    return html.replace("</head>", tag + "\n</head>", 1)
