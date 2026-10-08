from __future__ import annotations

"""Shared explainability/drill-down layer for Yipman Mobile V1 primary decisions.

This is intentionally UI-only: the server payload remains the source of truth.
The detail sheet displays evidence already present on the rendered decision/card
and never invents a recommendation or silently recalculates one in JavaScript.
"""

DECISION_DETAILS_CSS = r'''
<style id="yipmanDecisionDetailsV494">
body.yipman-v1 .ym-decision-tap{cursor:pointer;position:relative;touch-action:manipulation}
body.yipman-v1 .ym-decision-tap:after{content:'›';display:inline-grid;place-items:center;margin-left:6px;min-width:22px;height:22px;border-radius:999px;background:#edf3f8;color:#0d4f8b;font-weight:1000;font-size:18px;line-height:1}
body.yipman-v1 .ym-decision-tap:active{transform:scale(.99)}
body.yipman-v1 .ym-decision-hint{display:block;margin-top:4px;color:#667784;font-size:9px;font-weight:850}
#ymDecisionOverlay{position:fixed;inset:0;z-index:2147483000;background:rgba(8,20,31,.55);display:none;align-items:flex-end;justify-content:center;padding-top:max(env(safe-area-inset-top,0px),20px)}
#ymDecisionOverlay.on{display:flex}
#ymDecisionSheet{width:100%;max-width:560px;max-height:94dvh;overflow:auto;background:#f7f9fb;border-radius:24px 24px 0 0;box-shadow:0 -18px 60px rgba(0,0,0,.22);padding:8px 14px calc(18px + env(safe-area-inset-bottom,0px));color:#17212b}
.ymd-handle{width:48px;height:5px;border-radius:99px;background:#bdc8d1;margin:2px auto 10px}.ymd-head{position:sticky;top:-8px;z-index:2;background:#f7f9fb;padding:5px 0 10px;border-bottom:1px solid #dde5eb}.ymd-top{display:flex;justify-content:space-between;gap:10px;align-items:start}.ymd-kicker{font-size:10px;font-weight:1000;color:#0d4f8b;letter-spacing:.06em;text-transform:uppercase}.ymd-title{font-size:24px;line-height:1.08;font-weight:1000;margin:3px 0}.ymd-close{border:0;background:#e7edf2;border-radius:13px;width:42px;height:42px;font-size:22px;font-weight:900}.ymd-decision{margin-top:10px;background:#0d4f8b;color:white;border-radius:17px;padding:13px 14px}.ymd-decision small{display:block;font-size:9px;font-weight:900;opacity:.78;text-transform:uppercase;letter-spacing:.05em}.ymd-decision strong{display:block;font-size:24px;line-height:1.12;margin-top:3px}.ymd-section{margin-top:11px;background:#fff;border:1px solid #dfe6eb;border-radius:16px;padding:12px}.ymd-section h4{font-size:12px;margin:0 0 7px;text-transform:uppercase;letter-spacing:.04em;color:#516575}.ymd-section p{font-size:13px;line-height:1.45;margin:0;white-space:pre-wrap}.ymd-evidence{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px 10px;font-size:12px;line-height:1.35}.ymd-evidence span:nth-child(odd){color:#667784;font-weight:800}.ymd-evidence span:nth-child(even){text-align:right;font-weight:950;color:#17212b;overflow-wrap:anywhere}.ymd-warn{background:#fff7e5;border-color:#ecd8a3}.ymd-source{font-size:11px!important;color:#61717e}.ymd-empty{color:#71808d!important}.ymd-back{width:100%;min-height:52px;margin-top:12px;border:0;border-radius:15px;background:#17212b;color:#fff;font-size:14px;font-weight:1000}
</style>
'''

DECISION_DETAILS_JS = r'''
<script id="yipmanDecisionDetailsJsV494">
(function(){
 if(!document.body.classList.contains('yipman-v1'))return;
 const SELECTORS=[
  '.urgent-card','.action-card','.recommendation','.recommendation-card','.suggestion','.suggestion-card',
  '.order-card','.orderrow','.price-card','.priceRow','.price-row','.decision','.decision-card',
  '[data-decision]','[data-recommendation]','[data-suggested-price]','[data-suggested-qty]'
 ];
 const DECISION_WORDS=/(suggest|recommend|decision|action|required|order|reg\b|tpr|clearance|markdown|dump|urgent|change price|keep price|price change)/i;
 const EVIDENCE_WORDS=/(effective|true stock|system oh|\boh\b|7d|14d|28d|velocity|avg\/day|receipt|receiv|doh|fresh|cost|gp\$|gp%|margin|current price|tested|testing|company|promo|sale|movement|mvt|coverage|delivery|upc|family|article|source|published|data through|confidence|pack|uom|stock)/i;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const clean=s=>String(s||'').replace(/\s+/g,' ').trim();
 function overlay(){
  let o=document.getElementById('ymDecisionOverlay');if(o)return o;
  o=document.createElement('div');o.id='ymDecisionOverlay';o.innerHTML='<div id="ymDecisionSheet" role="dialog" aria-modal="true" aria-label="Decision details"><div class="ymd-handle"></div><div class="ymd-head"><div class="ymd-top"><div><div class="ymd-kicker">Decision details · Why & evidence</div><div class="ymd-title" id="ymdTitle">Decision</div></div><button class="ymd-close" aria-label="Close">×</button></div></div><div id="ymdBody"></div><button class="ymd-back">BACK</button></div>';
  document.body.appendChild(o);o.querySelector('.ymd-close').onclick=close;o.querySelector('.ymd-back').onclick=close;o.addEventListener('click',e=>{if(e.target===o)close()});return o;
 }
 function close(){const o=document.getElementById('ymDecisionOverlay');if(o)o.classList.remove('on')}
 function pairs(card){
  const out=[],seen=new Set();
  card.querySelectorAll('tr,.kv,.line,.metric,.stat,.fm,.row,[class*="metric"],[class*="evidence"]').forEach(n=>{
   const t=clean(n.innerText);if(!t||t.length>180||!EVIDENCE_WORDS.test(t))return;
   let label='',value='';const cells=n.querySelectorAll(':scope > td,:scope > th');
   if(cells.length>=2){label=clean(cells[0].innerText);value=clean([...cells].slice(1).map(x=>x.innerText).join(' · '))}
   else {const m=t.match(/^([^:]{2,45}):\s*(.+)$/);if(m){label=m[1];value=m[2]}else{label='Evidence';value=t}}
   const key=label+'|'+value;if(!value||seen.has(key))return;seen.add(key);out.push([label,value]);
  });
  if(!out.length){clean(card.innerText).split(/\n+/).filter(x=>EVIDENCE_WORDS.test(x)).slice(0,12).forEach(x=>out.push(['Evidence',x]))}
  return out.slice(0,16);
 }
 function primary(card){
  const explicit=card.dataset.decision||card.dataset.recommendation||card.dataset.suggestedPrice||card.dataset.suggestedQty;if(explicit)return clean(explicit);
  const nodes=[...card.querySelectorAll('strong,b,h3,h4,[class*="suggest"],[class*="decision"],[class*="action"]')];
  const hit=nodes.map(n=>clean(n.innerText)).find(t=>t&&t.length<120&&DECISION_WORDS.test(t));return hit||clean(card.innerText).slice(0,150)||'Open decision';
 }
 function reason(card){
  const explicit=card.dataset.reason||card.dataset.why;if(explicit)return clean(explicit);
  const nodes=[...card.querySelectorAll('[class*="reason"],[class*="why"],p,.note,.small')];
  return nodes.map(n=>clean(n.innerText)).find(t=>t&&t.length<420&&(DECISION_WORDS.test(t)||EVIDENCE_WORDS.test(t)))||'This recommendation is based on the operational evidence shown on the source card. Review the exact evidence below before acting.';
 }
 function source(card){
  const bits=[...card.querySelectorAll('*')].map(n=>clean(n.childNodes.length===1?n.innerText:''))
   .filter(t=>t&&t.length<140&&/(source|published|data through|as of|updated|pos|price list|mvt|receipt)/i.test(t));
  return [...new Set(bits)].slice(0,6).join(' · ')||'Uses the latest evidence supplied by the Yipman server for this rendered decision.';
 }
 function show(card){
  const o=overlay(),d=primary(card),r=reason(card),ev=pairs(card),src=source(card);
  document.getElementById('ymdTitle').textContent=clean(card.querySelector('h3,h4,b,strong')?.innerText)||'Decision';
  let h='<div class="ymd-decision"><small>Primary decision</small><strong>'+esc(d)+'</strong></div>';
  h+='<section class="ymd-section"><h4>Why</h4><p>'+esc(r)+'</p></section>';
  h+='<section class="ymd-section"><h4>Supporting evidence</h4>'+(ev.length?'<div class="ymd-evidence">'+ev.map(x=>'<span>'+esc(x[0])+'</span><span>'+esc(x[1])+'</span>').join('')+'</div>':'<p class="ymd-empty">No additional evidence fields are exposed on this card. The recommendation itself is shown, but the backend should expose more evidence before this is treated as fully auditable.</p>')+'</section>';
  h+='<section class="ymd-section"><h4>Calculation / logic</h4><p>'+esc(card.dataset.calculation||'The displayed recommendation remains the server decision. This detail view does not recalculate or replace backend ordering, pricing, freshness, or inventory logic.')+'</p></section>';
  h+='<section class="ymd-section"><h4>Source & recency</h4><p class="ymd-source">'+esc(src)+'</p></section>';
  h+='<section class="ymd-section ymd-warn"><h4>Confidence / limitations</h4><p>'+esc(card.dataset.confidence||'Check for missing, estimated, provisional, or stale values in the evidence above. A recommendation with incomplete evidence should not be presented as certain.')+'</p></section>';
  document.getElementById('ymdBody').innerHTML=h;o.classList.add('on');o.querySelector('#ymDecisionSheet').scrollTop=0;
 }
 function eligible(el){if(!el||el.closest('#ymDecisionOverlay'))return false;const t=clean(el.innerText);return t.length>3&&(DECISION_WORDS.test(t)||el.matches('[data-decision],[data-recommendation],[data-suggested-price],[data-suggested-qty]'))}
 function decorate(){
  document.querySelectorAll(SELECTORS.join(',')).forEach(el=>{if(el.dataset.ymDecisionBound||!eligible(el))return;el.dataset.ymDecisionBound='1';el.classList.add('ym-decision-tap');el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('aria-label','Open decision details and supporting evidence');el.addEventListener('click',e=>{if(e.target.closest('button,input,select,textarea,a'))return;show(el)});el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();show(el)}})});
 }
 let q=false;new MutationObserver(()=>{if(q)return;q=true;requestAnimationFrame(()=>{q=false;decorate()})}).observe(document.documentElement,{childList:true,subtree:true});
 addEventListener('DOMContentLoaded',decorate);setTimeout(decorate,400);setInterval(decorate,2200);
 addEventListener('keydown',e=>{if(e.key==='Escape')close()});
})();
</script>
'''


def inject_decision_details(html: str) -> str:
    if 'yipmanDecisionDetailsV494' not in html:
        html = html.replace('</head>', DECISION_DETAILS_CSS + '</head>', 1)
    if 'yipmanDecisionDetailsJsV494' not in html:
        html = html.replace('</body>', DECISION_DETAILS_JS + '</body>', 1)
    return html
