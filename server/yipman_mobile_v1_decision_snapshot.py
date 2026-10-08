from __future__ import annotations

"""Mobile V1 decision-detail App Ready hydration.

Decision intelligence is prefetched once and cached in the browser. Opening a
detail/WHY panel performs presentation only; it does not start business analysis
or repeatedly transfer the full decision snapshot.
"""

_SCRIPT=r'''<script id="yipmanV1DecisionSnapshotScript">(()=>{'use strict';
const digits=v=>String(v??'').replace(/\D/g,'').replace(/^0+/,'');let decisionPromise=null;
const preload=()=>decisionPromise||(decisionPromise=fetch('/api/yipman/app-ready/decision_intelligence',{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null));
const text=(root,sel)=>String(root?.querySelector(sel)?.textContent||'').trim();const identity=(body,label)=>{for(const el of body.querySelectorAll('.v1-detail-id>div')){const k=text(el,'b').toUpperCase();if(k.includes(label))return text(el,'span')}return''};
const evidenceCell=(body,key,label,value)=>{if(value===null||value===undefined||value==='')return;let host=body.querySelector('.v1-detail-metrics');if(!host)return;let cell=[...host.querySelectorAll('[data-evidence-key]')].find(x=>x.dataset.evidenceKey===key);if(!cell){cell=document.createElement('div');cell.dataset.evidenceKey=key;cell.innerHTML='<b></b><span></span>';host.appendChild(cell)}cell.querySelector('b').textContent=label;cell.querySelector('span').textContent=String(value)};
function pick(obj,...keys){for(const k of keys){const v=obj?.[k];if(v!==null&&v!==undefined&&v!=='')return v}return null}function rowsOf(p){if(Array.isArray(p))return p;if(Array.isArray(p?.rows))return p.rows;return[]}
function findDecision(p,family,upc){const u=digits(upc),f=String(family||''),all=[...rowsOf(p?.pricing),...rowsOf(p?.tpr_progress)];for(const r of all){const ru=digits(r?.upc??r?.ean_upc??r?.ean),rf=String(r?.family??r?.family_article??r?.family_id??'');if((u&&ru===u)||(f&&rf===f))return r}for(const day of Object.values(p?.ordering?.deliveries||{})){for(const r of rowsOf(day)){const ru=digits(r?.upc??r?.ean_upc??r?.ean),rf=String(r?.family??r?.family_article??r?.family_id??'');if((u&&ru===u)||(f&&rf===f))return r}}return null}
async function hydrate(){const body=document.getElementById('v1DetailBody'),overlay=document.getElementById('v1DetailOverlay');if(!body||!overlay?.classList.contains('open'))return;const family=identity(body,'FAMILY'),upc=identity(body,'UPC'),sig=family+'|'+upc;if(body.dataset.appReadyDecision===sig)return;body.dataset.appReadyDecision=sig;const env=await preload();const p=env?.payload||{},r=findDecision(p,family,upc);if(!r)return;evidenceCell(body,'current_price','CURRENT PRICE',pick(r,'current_price','price'));evidenceCell(body,'suggested_price','SUGGESTED PRICE',pick(r,'suggested_price','testing_price','recommended_price'));evidenceCell(body,'current_cost','CURRENT COST',pick(r,'current_cost','cost'));evidenceCell(body,'effective_oh','EFFECTIVE OH',pick(r,'effective_oh','ordering_oh_used','actual_position'));evidenceCell(body,'sales_7d','7D SALES',pick(r,'sales_7d','qty_7d','pos_qty_7d'));evidenceCell(body,'avg_7d','7D AVG',pick(r,'avg_7d','velocity_7d','avg_per_day'));for(const [k,l] of [['forecast_usage_before_delivery','FORECAST USAGE BEFORE DELIVERY'],['projected_oh_at_delivery','PROJECTED OH AT DELIVERY'],['usable_oh_at_delivery','USABLE OH AT DELIVERY'],['pre_delivery_stockout_qty','PRE DELIVERY STOCKOUT QTY']])evidenceCell(body,k,l,pick(r,k));evidenceCell(body,'forecast_coverage_usage','FORECAST COVERAGE USAGE',pick(r,'forecast_coverage_usage','forecast_requested_coverage_usage'));body.dataset.appReadyBuildId=env?.build_id||'';body.dataset.causalDecisionEvidence='';body.dispatchEvent(new CustomEvent('yipman-app-ready-decision-hydrated',{bubbles:true,detail:{buildId:env?.build_id||null}}))}
const kick=()=>requestAnimationFrame(hydrate);if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',preload,{once:true});else preload();new MutationObserver(kick).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});document.addEventListener('click',()=>setTimeout(kick,0),true);})();</script>'''

def polish_decision_snapshot_html(html:str)->str:
    if 'yipmanV1DecisionSnapshotScript' in html:return html
    return html.replace('</body>',_SCRIPT+'</body>',1)
