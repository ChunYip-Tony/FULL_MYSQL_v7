from __future__ import annotations

"""RC Mobile V1 compact ordering + explicit primary-decision evidence drill-down."""

_STYLE = r'''
<style id="yipmanV1DecisionCompactV502">
#regular .card{margin-bottom:8px;border-radius:15px}
#regular .card-head{padding:9px 11px 5px}
#regular .card-body{padding:6px 11px 9px}
#regular .card-title{font-size:18px;line-height:1.05}
#regular .card-sub{font-size:9px;margin-top:2px}
#regular .order-main{font-size:21px;line-height:1.05;margin-top:0}
#regular .why{font-size:9px;line-height:1.25;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#regular .summary3{gap:5px;margin-top:6px}
#regular .stat{padding:5px 4px;border-radius:9px;min-height:46px;display:flex;flex-direction:column;justify-content:center}
#regular .stat b{font-size:6px}
#regular .stat span{font-size:10px;margin-top:2px;line-height:1.15}
#regular .ignore{min-height:34px;margin-top:6px;border-radius:9px;font-size:10px}
#regular .pill{min-height:22px;padding:3px 7px;font-size:8px}
.ym-primary-decision{cursor:pointer;position:relative;padding-right:27px!important;touch-action:manipulation}
.ym-primary-decision:after{content:'WHY ›';position:absolute;right:0;top:50%;transform:translateY(-50%);font-size:8px;color:#74b8ee;font-weight:1000;letter-spacing:.03em}
.ym-primary-decision:active{opacity:.75}
#ymDecisionDetailV502{display:none;position:fixed;inset:0;z-index:1000;background:rgba(4,9,14,.76);align-items:flex-end}
#ymDecisionDetailV502.show{display:flex}
.ymd-sheet{width:100%;max-height:92dvh;overflow:auto;background:#101820;border:1px solid #344452;border-radius:22px 22px 0 0;padding:9px 13px calc(16px + env(safe-area-inset-bottom));box-shadow:0 -20px 50px rgba(0,0,0,.42)}
.ymd-handle{width:44px;height:4px;background:#50606d;border-radius:99px;margin:0 auto 8px}.ymd-top{display:flex;justify-content:space-between;gap:10px;align-items:start;position:sticky;top:-9px;background:#101820;padding:7px 0 9px;z-index:2;border-bottom:1px solid #263541}.ymd-kicker{font-size:8px;color:#70b6eb;font-weight:1000;letter-spacing:.06em}.ymd-name{font-size:19px;font-weight:1000;line-height:1.1;margin-top:3px}.ymd-close{width:38px;height:38px;border:1px solid #354654;border-radius:11px;background:#17212b;color:#fff;font-size:21px}.ymd-decision{margin-top:9px;border:1px solid #315f91;background:#172c42;border-radius:13px;padding:10px}.ymd-decision small,.ymd-sec h4{display:block;margin:0 0 5px;font-size:7px;color:#8295a5;font-weight:1000;letter-spacing:.06em}.ymd-decision strong{display:block;font-size:23px;line-height:1.1}.ymd-sec{margin-top:8px;border:1px solid #2b3945;background:#131d26;border-radius:12px;padding:9px 10px}.ymd-sec p{margin:0;color:#c0cad2;font-size:11px;line-height:1.4}.ymd-grid{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px 10px;font-size:10px}.ymd-grid span:nth-child(odd){color:#82919e;font-weight:850}.ymd-grid span:nth-child(even){text-align:right;color:#f0f4f7;font-weight:1000}.ymd-missing{color:#e7c676!important}.ymd-back{width:100%;min-height:44px;border:0;border-radius:12px;background:#e8eef3;color:#14212c;font-weight:1000;margin-top:10px}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1DecisionCompactJsV502">
(function(){
 const esc2=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const val=(r,keys)=>{for(const k of keys){const v=r?.[k];if(v!==undefined&&v!==null&&v!=='')return v}return null};
 function findRow(kind,id){const rows=kind==='order'?(window.orderRows||[]):(window.priceRows||[]);return rows.find(r=>String(kind==='order'?(r?.family_article_number||r?.family_article||r?.family_id||r?.receiving_article||''):(r?.upc||r?.selling_upc||r?.upc_number||''))===String(id))||null}
 function fmt2(v,d=1){const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):'—'}
 function money2(v){const n=Number(v);return Number.isFinite(n)?'$'+n.toFixed(2):'—'}
 function date2(v){if(!v)return'—';return window.yipmanDateLabel?window.yipmanDateLabel(String(v)):String(v)}
 function ensure(){let o=document.getElementById('ymDecisionDetailV502');if(o)return o;o=document.createElement('div');o.id='ymDecisionDetailV502';o.innerHTML='<div class="ymd-sheet"><div class="ymd-handle"></div><div class="ymd-top"><div><div class="ymd-kicker">PRIMARY DECISION · WHY & EVIDENCE</div><div class="ymd-name" id="ymdNameV502">Decision</div></div><button class="ymd-close">×</button></div><div id="ymdBodyV502"></div><button class="ymd-back">BACK</button></div>';document.body.appendChild(o);o.querySelector('.ymd-close').onclick=close;o.querySelector('.ymd-back').onclick=close;o.onclick=e=>{if(e.target===o)close()};return o}
 function close(){document.getElementById('ymDecisionDetailV502')?.classList.remove('show')}
 function evidenceGrid(items){return '<div class="ymd-grid">'+items.map(([a,b,miss])=>'<span>'+esc2(a)+'</span><span class="'+(miss?'ymd-missing':'')+'">'+esc2(b)+'</span>').join('')+'</div>'}
 function orderDetail(r){
  const q=val(r,['suggested_delivery_qty']),u=val(r,['suggested_delivery_uom','order_uom','effective_oh_uom'])||'';
  const eff=val(r,['effective_oh','current_oh','oh']),du=val(r,['effective_oh_uom','oh_uom'])||'';
  const delivery=val(r,['delivery_date','selected_delivery_date']),next=val(r,['next_delivery_date','selected_next_delivery_date']);
  const reason=val(r,['decision_explanation','why','reason','suggestion_reason','roster_reason']);
  const projected=val(r,['projected_oh_at_delivery','projected_delivery_oh','projected_oh']);
  const demand=val(r,['projected_coverage_demand','coverage_demand','projected_demand','demand_to_next_delivery']);
  const velocity=val(r,['regular_velocity','family_velocity_7d','avg_daily_movement','avg_daily_qty','velocity_7d']);
  const receipts=val(r,['receipt_qty_7d','receipts_7d','family_receipt_qty_7d']);
  const pack=val(r,['pack_size','order_pack_size','receiving_pack_size']);
  const source=val(r,['data_published_through','published_through','data_through','source_date','as_of_date']);
  const why=reason&&String(reason).toLowerCase()!=='coverage calculation complete.'?String(reason):((q??0)>0?'Projected stock is below the demand required to cover '+date2(delivery)+' through the day before '+date2(next)+'. The quantity shown is the server ordering decision using current Effective OH and established ordering rules.':'Projected stock is sufficient for the selected coverage window; no replenishment is currently required.');
  const calc=(demand!==null||projected!==null)?'Coverage demand'+(demand!==null?' '+fmt2(demand)+' '+u:'')+' − projected available stock'+(projected!==null?' '+fmt2(projected)+' '+u:'')+' → required quantity → pack/UOM rounding → final decision.':'The server calculates projected stock at delivery, day-segmented demand through the next delivery, freshness/ordering constraints, then rounds to the valid ordering UOM. Exact intermediate values not exposed by the API are marked below.';
  return {decision:(Number(q)>0?'ORDER '+fmt2(q)+' '+u:'NO ORDER'),why,calc,ev:[['Effective OH',eff===null?'Not exposed':fmt2(eff)+' '+du,eff===null],['Projected OH @ delivery',projected===null?'Not exposed':fmt2(projected)+' '+du,projected===null],['Coverage demand',demand===null?'Not exposed':fmt2(demand)+' '+u,demand===null],['Demand velocity',velocity===null?'Not exposed':fmt2(velocity)+' / day',velocity===null],['Delivery',date2(delivery),!delivery],['Next delivery',date2(next),!next],['7D receipts',receipts===null?'Not exposed':fmt2(receipts),receipts===null],['Pack / rounding',pack===null?'Not exposed':String(pack),pack===null],['Data through',source===null?'Not exposed by row':String(source),source===null]]};
 }
 function priceDetail(r){const sp=val(r,['final_tpr_price_suggestion','tpr_suggestion_price','testing_price','suggested_price','candidate_price','suggested_reg_price']),cp=val(r,['current_price','effective_price']),cost=val(r,['current_cost','cost']),oh=val(r,['current_oh','effective_oh','oh']),reason=val(r,['why','reason','suggestion_reason','recommendation_reason'])||'Review current pricing evidence.',source=val(r,['data_published_through','published_through','data_through','source_date']);return{decision:sp===null?'REVIEW':money2(sp),why:String(reason),calc:'The displayed price remains the server recommendation. Price type, current price, cost/GP$, velocity, stock/freshness and company constraints are evaluated by the pricing policy; this view does not recalculate the decision.',ev:[['Current price',money2(cp),cp===null],['Suggested price',money2(sp),sp===null],['Current cost',money2(cost),cost===null],['Effective OH',oh===null?'Not exposed':fmt2(oh),oh===null],['Data through',source===null?'Not exposed by row':String(source),source===null]]}}
 function open(kind,id,name){const r=findRow(kind,id);if(!r)return;const d=kind==='order'?orderDetail(r):priceDetail(r),o=ensure();document.getElementById('ymdNameV502').textContent=name||'Decision';document.getElementById('ymdBodyV502').innerHTML='<div class="ymd-decision"><small>DECISION</small><strong>'+esc2(d.decision)+'</strong></div><section class="ymd-sec"><h4>WHY</h4><p>'+esc2(d.why)+'</p></section><section class="ymd-sec"><h4>SUPPORTING EVIDENCE</h4>'+evidenceGrid(d.ev)+'</section><section class="ymd-sec"><h4>CALCULATION / LOGIC</h4><p>'+esc2(d.calc)+'</p></section><section class="ymd-sec"><h4>CONFIDENCE / LIMITATIONS</h4><p>Values marked “Not exposed” are not invented. The backend should expose those intermediate values for full auditability. The primary decision shown here remains the server result.</p></section>';o.classList.add('show');o.querySelector('.ymd-sheet').scrollTop=0}
 function decorate(){
  document.querySelectorAll('#regularResults .card').forEach(card=>{const sub=card.querySelector('.card-sub')?.textContent||'',m=sub.match(/Family\s+([^\s·]+)/i),main=card.querySelector('.order-main');if(!m||!main||main.dataset.v502)return;main.dataset.v502='1';main.classList.add('ym-primary-decision');main.setAttribute('role','button');main.setAttribute('tabindex','0');const go=()=>open('order',m[1],card.querySelector('.card-title')?.textContent||'Ordering decision');main.onclick=go;main.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}}});
  document.querySelectorAll('#priceQueue .direct-card').forEach(card=>{const meta=card.querySelector('.action-meta')?.textContent||'',m=meta.match(/UPC\s+([^\s·]+)/i),main=card.querySelector('.actionbox');if(!m||!main||main.dataset.v502)return;main.dataset.v502='1';main.classList.add('ym-primary-decision');main.setAttribute('role','button');main.setAttribute('tabindex','0');const go=()=>open('price',m[1],card.querySelector('.result-name')?.textContent||'Price decision');main.onclick=go;main.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}}});
 }
 let queued=false;new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;decorate()})}).observe(document.documentElement,{childList:true,subtree:true});setTimeout(decorate,300);setInterval(decorate,1800);addEventListener('keydown',e=>{if(e.key==='Escape')close()});
})();
</script>
'''

# expose the shell's lexical arrays so the evidence layer reads the exact rows used to render decisions
_EXPOSE = "let urgent=[],priceRows=[],orderRows=[],uf='all',pf='all';"
_EXPOSE_REPL = "let urgent=[],priceRows=[],orderRows=[],uf='all',pf='all';Object.defineProperties(window,{orderRows:{get:()=>orderRows},priceRows:{get:()=>priceRows}});"


def polish_decision_compact_html(html: str) -> str:
    if 'yipmanV1DecisionCompactV502' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    if _EXPOSE in html:
        html = html.replace(_EXPOSE, _EXPOSE_REPL, 1)
    html = html.replace('</body>', _SCRIPT + '</body>', 1)
    return html
