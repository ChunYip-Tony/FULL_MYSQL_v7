from __future__ import annotations

"""Mobile V1 active TPR progress presentation with App Ready fast path."""

# Keep the established presentation intact and only redirect its expensive
# lifecycle fetch to the upload-time precomputed snapshot. If a snapshot is not
# ready, fall back to the authoritative live endpoint so correctness wins.
from pathlib import Path

# This module is source-patched at render time; no filesystem read is performed.

_STYLE = r'''<style id="yipmanV1PriceProgressStyle">#price .filter4.price-lifecycle-tabs{grid-template-columns:repeat(4,1fr)}</style>'''

_SCRIPT_HELPERS = r'''
let tprProgressLoaded=false;
let tprProgressLoading=false;
let tprProgressByUpc=new Map();
function progressUpcKey(v){const d=String(v??'').replace(/\D/g,'').replace(/^0+/,'');return d||''}
function progressNum(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function pctText(v){const n=Number(v);if(!Number.isFinite(n))return '—';return (n>0?'+':'')+n.toFixed(1)+'%'}
function dayText(v){const n=Number(v);return Number.isFinite(n)?n.toFixed(n%1?1:0):'—'}
function progressCurrentType(r){return String(r?.current_price_type??r?.current_type??r?.observed_price_type??r?.price_type??'').trim().toUpperCase()}
function isActiveTprProgress(p){const t=progressCurrentType(p);if(t)return t==='TPR';const active=String(p?.status??p?.tpr_status??p?.lifecycle_status??'').toUpperCase();return active==='ACTIVE'||active==='TPR_ACTIVE'}
async function loadTprProgress(){if(tprProgressLoaded||tprProgressLoading)return;tprProgressLoading=true;try{let d=await api('/app/yipman-v1-rc/api/app-ready/tpr-progress?category=ALL&limit=1000');if(d?.status==='SNAPSHOT_MISS'||!d?.app_ready_snapshot)d=await api('/v1/yipman/current-tpr-review?category=ALL&limit=1000');const rows=d?.rows||[];tprProgressByUpc=new Map();rows.forEach(x=>{const k=progressUpcKey(x?.upc??x?.ean_upc??x?.ean);if(k)tprProgressByUpc.set(k,x)});tprProgressLoaded=true}catch(_){tprProgressLoaded=false}finally{tprProgressLoading=false}}
function tprProgressDecision(p){const code=String(p?.recommendation_code||p?.recommendation_label||'CONTINUE').toUpperCase().replaceAll('_',' ');const next=p?.suggested_regular_price??p?.suggested_tpr_price;const label=code.includes('CANCEL')||code.includes('END')?'END TPR':code.includes('LOWER')?'LOWER TPR':code.includes('RAISE')?'RAISE TPR':code.includes('REG')?'RETURN TO REG':'KEEP TPR';return next!=null?label+' '+money(next):label}
function tprProgressState(p){const raw=String(p?.progress_status??p?.pacing_status??p?.sell_through_status??p?.recommendation_status??'').toUpperCase();if(raw.includes('BEHIND'))return'BEHIND';if(raw.includes('AHEAD'))return'AHEAD';if(raw.includes('TRACK'))return'ON TRACK';const clear=progressNum(p?.projected_days_to_clear_oh),remain=progressNum(p?.days_remaining??p?.remaining_days_to_threshold);if(clear!==null&&remain!==null)return clear<=remain?'ON TRACK':'BEHIND';return'ACTIVE'}
function activeTprProgressHtml(p){const up=String(p?.upc??p?.ean_upc??p?.ean??'—'),name=String(p?.item_name??p?.upc_name??p?.description??p?.name??'ACTIVE TPR'),fam=String(p?.family??p?.family_article??p?.family_id??'—'),state=tprProgressState(p),decision=tprProgressDecision(p),cur=p?.current_price??p?.tpr_price??p?.active_price,reg=p?.original_regular_price??p?.baseline_regular_price??p?.regular_price,days=p?.completed_tpr_days??p?.tpr_supported_days??p?.current_behavior?.supported_days,ohNow=p?.effective_oh??p?.current_oh,reason=String(p?.recommendation_reason||'Active TPR lifecycle tracking on completed valid POS days.');return `<div class="direct-card tpr-progress-card"><div class="row space"><div><div class="result-name">${esc(name)}</div><div class="action-meta">UPC ${esc(up)} · Family ${esc(fam)}</div></div><span class="pill blue">ACTIVE TPR</span></div><div class="actionbox progress-decision"><div class="action-label">PRIMARY DECISION · CURRENT TPR PROGRESS</div><div class="action-value">${esc(decision)}</div><div class="why"><b>Status:</b> ${esc(state)} · ${esc(reason)}</div></div><div class="summary3"><div class="stat"><b>REG → TPR</b><span>${reg==null?'—':money(reg)} → ${cur==null?'—':money(cur)}</span></div><div class="stat"><b>VALID DAYS</b><span>${esc(dayText(days))}</span></div><div class="stat"><b>EFF OH</b><span>${ohNow==null?'—':esc(fmt(ohNow,1))}</span></div></div></div>`}
function renderActiveTprProgressTab(){const q=$('#priceQueue');if(!q)return;if(!tprProgressLoaded){q.innerHTML='<div class="loading">Loading current TPR progress…</div>';loadTprProgress().then(()=>{if(pf==='tprprogress')renderPrice()});return}const rows=[...tprProgressByUpc.values()].filter(isActiveTprProgress);$('#priceActions').textContent=rows.length;$('#priceUrgent').textContent=rows.filter(x=>tprProgressState(x)==='BEHIND').length;$('#priceFamilies').textContent=new Set(rows.map(x=>x?.family??x?.family_article??x?.family_id).filter(Boolean)).size;q.innerHTML=rows.map(activeTprProgressHtml).join('')||'<div class="empty">No UPC is currently on active TPR.</div>'}
function priceProgressHtml(){return''}
function wirePriceProgressToggles(){}
'''


def polish_price_progress_html(html: str) -> str:
    marker="yipmanV1PriceProgress"
    if marker in html:return html
    old='<div class="filter4"><button class="filterbtn" data-pf="reg">REG</button><button class="filterbtn" data-pf="tpr">TPR</button><button class="filterbtn" data-pf="clearance">Clearance</button><button class="filterbtn" data-pf="sale">SALE</button></div>'
    new='<div class="filter4 price-lifecycle-tabs"><button class="filterbtn" data-pf="reg">REG</button><button class="filterbtn" data-pf="tpr">TPR Suggestions</button><button class="filterbtn" data-pf="tprprogress">TPR Progress</button><button class="filterbtn" data-pf="clearance">Clearance</button></div>'
    html=html.replace(old,new,1)
    anchor="async function loadPrice(){"
    if anchor in html:html=html.replace(anchor,_SCRIPT_HELPERS+"\n"+anchor,1)
    render_anchor="function renderPrice(){const rows=priceRows.filter"
    if render_anchor in html:html=html.replace(render_anchor,"function renderPrice(){if(pf==='tprprogress'){renderActiveTprProgressTab();return}const rows=priceRows.filter",1)
    tail="</head>"
    if tail in html:html=html.replace(tail,_STYLE+"\n<script id=\"yipmanV1PriceProgress\">document.addEventListener('click',e=>{const b=e.target.closest?.('[data-pf=\"tprprogress\"]');if(b){pf='tprprogress';renderPrice()}})</script>\n"+tail,1)
    return html
