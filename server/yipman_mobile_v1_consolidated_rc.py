from __future__ import annotations

"""YipMan Mobile V1 consolidated RC front-end decorator.

This module is intentionally isolated from the canonical YipMan UI source.
It wraps only the dedicated Mobile V1 renderer after api_entry_production has
assembled the stable product channel. The live Ordering / Price / True Stock /
Data Center implementations remain owned by the existing V1 application.

RC scope:
- Quick Check starts as a live Unified Urgent Action Feed.
- Search continues to use the existing live Quick Check search implementation.
- Urgent cards are built from live pricing + ordering endpoints.
- 249 never owns an independent price suggestion card; 240 remains authority.
- Ignore 12h is independent per urgent action.
- A focused full-screen urgent-action detail view is provided.
- Bottom navigation is Quick / Order / Price / More.
- More exposes Back Office, Ask Yipman, Settings, and App Info.
"""

import api as _api

_INSTALLED = False

_MORE_PAGE = r'''
<section class="page" id="more">
  <div class="topline"><h2>More</h2><div class="hint">YIPMAN MOBILE V1</div></div>
  <div class="v1more">
    <a class="v1more-primary" href="/app/backoffice">
      <span>▦</span><div><b>Back Office</b><small>Desktop-grade operations, Data Center, QA and PI.</small></div><em>OPEN</em>
    </a>
    <button class="v1more-row" type="button" data-go="ai">
      <span>✦</span><div><b>Ask Yipman</b><small>Live operational answers · read only.</small></div><em>›</em>
    </button>
    <div class="v1more-row passive">
      <span>⚙</span><div><b>Settings</b><small>Mobile V1 uses the established store rules and device display settings.</small></div>
    </div>
    <div class="v1more-row passive">
      <span>ⓘ</span><div><b>App Info</b><small>FULL MYSQL · consolidated Mobile V1 release candidate.</small></div>
    </div>
  </div>
</section>
'''

_STYLE = r'''
<style id="yipmanV1ConsolidatedRcStyle">
body.yipman-v1 #quick{padding-top:0}
body.yipman-v1 #quick>.topline{display:none!important}
body.yipman-v1 #quick.v1-urgent-home #quickRows{display:none}
body.yipman-v1 #quick.v1-search-mode #v1UrgentHome{display:none}
body.yipman-v1 #quick.v1-search-mode #quickRows{display:block}
body.yipman-v1 #quick .quicksearch{z-index:46}
#v1UrgentHome{display:block;margin:0 -1px 10px}
.v1urgent-sticky{position:sticky;top:0;z-index:18;background:rgba(246,247,249,.97);backdrop-filter:blur(12px);padding:6px 0 7px;transition:.16s ease}
.v1urgent-summary{display:grid;grid-template-columns:1.12fr repeat(4,minmax(0,1fr));overflow:hidden;border:1px solid #d8e1e8;border-radius:13px;background:#fff;box-shadow:0 4px 14px rgba(18,38,56,.05)}
.v1urgent-filter{appearance:none;border:0;border-right:1px solid #e4e9ed;background:transparent;min-width:0;height:39px;padding:0 4px;display:flex;align-items:center;justify-content:center;gap:4px;color:#687987;font-size:8px;font-weight:950}
.v1urgent-filter:last-child{border-right:0}.v1urgent-filter strong{font-size:14px;color:#263746}
.v1urgent-filter.on{background:#eaf4fd;color:#0b659e}.v1urgent-filter.on strong{color:#0b659e}
.v1urgent-filter[data-filter="price"].on{background:#faeaf7;color:#8b357d}.v1urgent-filter[data-filter="price"].on strong{color:#8b357d}
.v1urgent-filter[data-filter="order"].on{background:#fff4dc;color:#8a5e00}.v1urgent-filter[data-filter="order"].on strong{color:#8a5e00}
.v1urgent-filter[data-filter="fresh"].on{background:#e8f6fa;color:#2f7184}.v1urgent-filter[data-filter="fresh"].on strong{color:#2f7184}
.v1urgent-filter[data-filter="inventory"].on{background:#edf7ef;color:#347348}.v1urgent-filter[data-filter="inventory"].on strong{color:#347348}
.v1urgent-updated{font-size:8px;color:#7c8a96;font-weight:850;padding:4px 2px 0}
.v1urgent-sticky.compact{padding-top:3px;padding-bottom:4px}.v1urgent-sticky.compact .v1urgent-filter{height:30px}.v1urgent-sticky.compact .v1urgent-updated{display:none}
.v1urgent-list{display:grid;gap:9px}
.v1urgent-loading,.v1urgent-empty{border:1px solid #e0e6eb;border-radius:16px;background:#fff;padding:22px 16px;text-align:center;color:#71808d;font-size:10px;font-weight:850;box-shadow:0 7px 20px rgba(18,38,56,.05)}
.v1urgent-empty b{display:block;color:#25734a;font-size:17px;margin-bottom:4px}
.v1urgent-card{--accent:#6d8293;border:1px solid #dce4ea;border-left:5px solid var(--accent);border-radius:16px;background:#fff;padding:11px;box-shadow:0 6px 18px rgba(18,38,56,.065);cursor:pointer}
.v1urgent-card.price{--accent:#bd68ad}.v1urgent-card.order{--accent:#d2a74d}.v1urgent-card.fresh{--accent:#59a8be}.v1urgent-card.inventory{--accent:#6aa278}
.v1urgent-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}.v1urgent-name{min-width:0;font-size:18px;line-height:1.08;font-weight:1000}.v1urgent-meta{font-size:8.5px;color:#71808d;font-weight:850;margin-top:3px;overflow-wrap:anywhere}
.v1urgent-pill{flex:0 0 auto;border-radius:999px;padding:5px 7px;background:#eef3f6;color:#536979;font-size:7px;font-weight:1000}
.v1urgent-card.price .v1urgent-pill{background:#faeaf7;color:#8b357d}.v1urgent-card.order .v1urgent-pill{background:#fff4dc;color:#8a5e00}.v1urgent-card.fresh .v1urgent-pill{background:#e8f6fa;color:#2f7184}.v1urgent-card.inventory .v1urgent-pill{background:#edf7ef;color:#347348}
.v1urgent-action{margin-top:7px;font-size:18px;line-height:1.06;font-weight:1000;color:#1b3448}.v1urgent-why{margin-top:5px;color:#657685;font-size:10.5px;line-height:1.35;font-weight:780}
.v1urgent-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}.v1urgent-metrics>div{min-width:0;border:1px solid #e1e7eb;border-radius:9px;background:#f8fafb;padding:6px;text-align:center}.v1urgent-metrics b{display:block;color:#798793;font-size:6.5px}.v1urgent-metrics span{display:block;margin-top:3px;font-size:10px;font-weight:1000;overflow-wrap:anywhere}
.v1urgent-ignore{display:block;width:100%;min-height:46px;margin-top:9px;border:1px solid #ecd29a;border-radius:11px;background:#fff7e7;color:#805900;font-size:10px;font-weight:1000}
.v1urgent-error{padding:9px 10px;border:1px solid #efcccc;border-radius:11px;background:#fff3f3;color:#a23a43;font-size:9px;font-weight:850}
.v1urgent-hidden{display:none!important}
#v1UrgentDetail{position:fixed;inset:0;z-index:120;background:#f6f7f9;display:none;overflow-y:auto;padding:calc(env(safe-area-inset-top,0px) + 10px) 12px calc(20px + env(safe-area-inset-bottom,0px))}
#v1UrgentDetail.on{display:block}.v1detail-head{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:9px;background:rgba(246,247,249,.96);backdrop-filter:blur(10px);padding:5px 0 9px}.v1detail-back{width:42px;height:42px;border:1px solid #d6dfe6;border-radius:12px;background:#fff;font-size:24px;font-weight:900}.v1detail-headcopy{flex:1}.v1detail-headcopy b{display:block;font-size:18px}.v1detail-headcopy span{font-size:9px;color:#71808d;font-weight:850}.v1detail-status{border-radius:999px;padding:5px 8px;background:#fff3dc;color:#895d00;font-size:8px;font-weight:1000}.v1detail-status.resolved{background:#edf7ef;color:#347348}
.v1detail-card{border:1px solid #dbe3e9;border-radius:16px;background:#fff;padding:13px;margin-bottom:10px;box-shadow:0 6px 18px rgba(18,38,56,.05)}.v1detail-name{font-size:21px;line-height:1.08;font-weight:1000}.v1detail-type{margin-top:4px;color:#71808d;font-size:9px;font-weight:900}.v1detail-id{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:10px}.v1detail-id>div,.v1detail-evidence>div{border:1px solid #e2e7eb;border-radius:9px;background:#f8fafb;padding:7px;min-width:0}.v1detail-id b,.v1detail-evidence b{display:block;font-size:6.5px;color:#798793}.v1detail-id span,.v1detail-evidence span{display:block;margin-top:3px;font-size:9.5px;font-weight:1000;overflow-wrap:anywhere}
.v1detail-decision small{font-size:7px;color:#71808d;font-weight:1000}.v1detail-decision strong{display:block;margin-top:5px;font-size:24px;line-height:1.05}.v1detail-decision p{margin:7px 0 0;color:#60717f;font-size:10.5px;line-height:1.4;font-weight:780}.v1detail-evidence{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}
.v1detail-actions{display:grid;gap:8px}.v1detail-actions button{width:100%;min-height:50px;border-radius:13px;font-size:11px;font-weight:1000}.v1detail-open{border:0;background:#0d4f8b;color:#fff}.v1detail-ignore{border:1px solid #ecd29a;background:#fff7e7;color:#805900}.v1detail-refresh{border:1px solid #ccd9e2;background:#fff;color:#38556c}.v1detail-backquick{border:0;background:#0d4f8b;color:#fff}.v1detail-resolved{display:none;text-align:center}.v1detail-resolved.on{display:block}.v1detail-resolved b{display:block;font-size:18px;color:#347348}.v1detail-resolved p{font-size:10px;line-height:1.4;color:#71808d}
#more{padding-top:1px}.v1more{display:grid;gap:9px}.v1more-primary,.v1more-row{width:100%;min-height:76px;border:1px solid #dce4ea;border-radius:16px;background:#fff;padding:12px;display:grid;grid-template-columns:42px minmax(0,1fr) auto;align-items:center;gap:10px;text-decoration:none;color:#16202a;text-align:left;box-shadow:0 6px 18px rgba(18,38,56,.05)}.v1more-primary{background:linear-gradient(135deg,#0d4f8b,#1d6fb8);color:#fff;border:0}.v1more-primary>span,.v1more-row>span{font-size:22px;text-align:center}.v1more-primary b,.v1more-row b{display:block;font-size:16px}.v1more-primary small,.v1more-row small{display:block;margin-top:3px;font-size:9px;line-height:1.3;color:inherit;opacity:.72}.v1more-primary em,.v1more-row em{font-style:normal;font-size:9px;font-weight:1000}.v1more-row.passive{cursor:default}
body.yipman-v1 .nav button[data-go="more"] i{font-size:20px}
body.yipman-v1 .pcard-actions .snooze12,body.yipman-v1 #order .snooze12,body.yipman-v1 .clearance-actions .snooze12{width:100%!important;grid-column:1/-1!important;min-height:48px!important}
body.yipman-v1 #price>.topline{margin-bottom:4px}
body.yipman-v1 #price .price-tabs{margin-bottom:6px}
body.yipman-v1 #price .price-tab{min-height:44px!important;padding:7px 3px!important}
body.yipman-v1 #price .filters{gap:4px;margin-bottom:5px}
body.yipman-v1 #price .filters .pill{padding:8px 10px!important}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1ConsolidatedRcScript">
(function(){
  'use strict';
  if(!document.body.classList.contains('yipman-v1') || window.__YIPMAN_V1_CONSOLIDATED_RC__)return;
  window.__YIPMAN_V1_CONSOLIDATED_RC__=true;
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n=v=>{const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=(v,d=1)=>{const x=n(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:d})};
  const money=v=>{const x=n(v);return x===null?'—':'$'+x.toFixed(2)};
  const prefix=v=>String(v||'').replace(/^0+/,'').slice(0,3);
  const IGNORE_MS=12*60*60*1000;
  let urgentItems=[], activeFilter='all', activeDetailKey=null, pullY=null;
  function fetchJSON(url,timeout=22000){
    const c=new AbortController(),t=setTimeout(()=>c.abort(),timeout);
    return fetch(url,{credentials:'same-origin',cache:'no-store',signal:c.signal}).then(async r=>{if(!r.ok)throw new Error((await r.text().catch(()=>''))||('HTTP '+r.status));return r.json()}).finally(()=>clearTimeout(t));
  }
  function ignoreKey(item){return 'yipman-v1-urgent-ignore:'+item.key}
  function ignored(item){const until=Number(localStorage.getItem(ignoreKey(item))||0);if(until>Date.now())return true;if(until)localStorage.removeItem(ignoreKey(item));return false}
  function setIgnore(item){localStorage.setItem(ignoreKey(item),String(Date.now()+IGNORE_MS));renderUrgent()}
  function familyOf(r){return String(r?.family_article_number||r?.family_article||r?.family_id||'').trim()}
  function nameOf(r){return String(r?.family_name||r?.name||r?.description||r?.family_article_name||r?.family_article||'Item').trim()}
  function upcOf(r){return String(r?.upc||r?.selling_upc||r?.upc_number||'').trim()}
  function articleOf(r){return String(r?.receiving_article||r?.receiving_article_number||r?.article_number||r?.family_article||r?.family_article_number||'').trim()}
  function priceReason(r){return String(r?.why||r?.reason||r?.suggestion_reason||r?.suggestion_reason_text||r?.suggestion_reason_code||r?.final_tpr_reason||'Price action requires review.').trim()}
  function isFreshnessPrice(r){const blob=[r?.suggestion_reason_code,r?.suggestion_reason,r?.why,r?.final_tpr_reason,r?.final_tpr_decision,r?.recommendation_type,r?.action_type].join(' ').toUpperCase();return /FRESH|CLEAR|EXPIR|AGING|DOH|SELL.?THROUGH/.test(blob)}
  function suggestedPrice(r){return r?.final_tpr_price_suggestion??r?.tpr_suggestion_price??r?.testing_price??r?.suggested_price??r?.candidate_price??null}
  function currentPrice(r){return r?.current_price??r?.effective_price??null}
  function priceUrgency(r,fresh){if(fresh)return 100;if(r?.priority_240_249_mismatch)return 96;const u=n(r?.urgency_score);return u===null?75:75+Math.min(20,u)}
  function orderUrgency(r){const q=n(r?.suggested_delivery_qty)||0,stockout=!!r?.projected_stockout||!!r?.stockout_risk;return (stockout?94:82)+Math.min(10,q/20)}
  function buildPriceItems(rows){
    const seen=new Set(),out=[];
    for(const r of rows||[]){
      const upc=upcOf(r);if(!upc||prefix(upc)==='249')continue;
      const actionable=!!r?.actionable||!!r?.tpr_suggestion_actionable||!!r?.priority_240_249_mismatch||String(r?.review_status||'').toUpperCase()==='ACTIONABLE';if(!actionable)continue;
      const key='price:'+upc;if(seen.has(key))continue;seen.add(key);
      const fresh=isFreshnessPrice(r),sp=suggestedPrice(r),cp=currentPrice(r),oh=r?.current_oh??r?.effective_oh??r?.oh,uom=r?.current_oh_uom||r?.effective_oh_uom||r?.oh_uom||'',qty=r?.sold_qty_7d??r?.qty_7d??r?.velocity_7d_qty;
      const action=fresh?((String(r?.recommendation_type||r?.action_type||'').toUpperCase().includes('CLEAR'))?'CLEARANCE ':'TPR-FRESH ')+(sp!==null?money(sp):'REVIEW'):(r?.priority_240_249_mismatch?'ALIGN 240/249 PRICE':('PRICE REVIEW '+(sp!==null?money(sp):''))).trim();
      out.push({key,type:fresh?'fresh':'price',score:priceUrgency(r,fresh),name:nameOf(r),family:familyOf(r),upc,article:articleOf(r),pill:fresh?'FRESH / PRICE':'PRICE',action,why:priceReason(r),metrics:[['EFF OH',oh==null?'—':fmt(oh)+' '+uom],['CURRENT',money(cp)],[sp!==null?'SUGGEST':'7D QTY',sp!==null?money(sp):fmt(qty)]],evidence:[['Current price',money(cp)],['Suggested',sp!==null?money(sp):'Review'],['Effective OH',oh==null?'—':fmt(oh)+' '+uom]],target:'price',raw:r});
    }return out;
  }
  function buildOrderItems(rows){
    const out=[];for(const r of rows||[]){const q=n(r?.suggested_delivery_qty),state=String(r?.roster_status||r?.order_state||'').toUpperCase();if(!(q>0)||(state&&state!=='ORDER'&&!state.includes('URGENT')))continue;const family=familyOf(r),upc=upcOf(r),article=articleOf(r),uom=r?.suggested_delivery_uom||r?.order_uom||r?.effective_oh_uom||'',eff=r?.effective_oh??r?.oh,delivery=r?.delivery_date||r?.selected_delivery_date||'',next=r?.next_delivery_date||'',key='order:'+(family||article||upc||nameOf(r))+':'+delivery,why=String(r?.roster_reason||r?.reason||r?.suggestion_reason||'Projected stock is below the expected demand through the next delivery.');out.push({key,type:'order',score:orderUrgency(r),name:nameOf(r),family,upc,article,pill:'ORDER',action:'ORDER '+fmt(q,1)+' '+uom,why,metrics:[['EFF OH',eff==null?'—':fmt(eff)+' '+(r?.effective_oh_uom||'')],['DELIVERY',delivery||'—'],['NEXT',next||'—']],evidence:[['Suggested order',fmt(q,1)+' '+uom],['Effective OH',eff==null?'—':fmt(eff)+' '+(r?.effective_oh_uom||'')],['Observed days',fmt(r?.delivery_window_observed_count??r?.delivery_day_observed_count,0)]],target:'order',raw:r})}return out;
  }
  async function getUrgentLive(){
    const calendarPromise=fetchJSON('/v1/yipman/ordering-calendar?lookback_days=180',16000).catch(()=>null),pricePromise=fetchJSON('/v1/yipman/pricing-review?category=ALL&limit=1000',18000).catch(()=>null),cal=await calendarPromise,delivery=String(cal?.default_delivery_date||''),next=String(cal?.default_next_delivery_date||''),orderPromise=delivery?fetchJSON('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(delivery)+(next?'&next_delivery_date='+encodeURIComponent(next):''),26000).catch(()=>null):Promise.resolve(null),[priceData,orderData]=await Promise.all([pricePromise,orderPromise]);let rows=[...buildPriceItems(priceData?.rows||[]),...buildOrderItems(orderData?.rows||[])];rows=rows.filter(x=>!ignored(x));rows.sort((a,b)=>b.score-a.score||String(a.family||a.name).localeCompare(String(b.family||b.name)));return {rows,health:orderData?.current_source_health||priceData?.current_source_health||orderData?.data_health||priceData?.data_health||null};
  }
  function ensureUrgentHome(){
    const quick=$('#quick');if(!quick||$('#v1UrgentHome'))return;const shell=document.createElement('div');shell.id='v1UrgentHome';shell.innerHTML='<div class="v1urgent-sticky"><div class="v1urgent-summary">'+[['all','Urgent'],['price','Price'],['order','Order'],['fresh','Fresh'],['inventory','Inventory']].map((x,i)=>'<button class="v1urgent-filter'+(i===0?' on':'')+'" type="button" data-filter="'+x[0]+'"><strong>0</strong><span>'+x[1]+'</span></button>').join('')+'</div><div class="v1urgent-updated">Updating…</div></div><div class="v1urgent-list"><div class="v1urgent-loading">Loading urgent actions…</div></div>';const quickRows=$('#quickRows',quick);quick.insertBefore(shell,quickRows||quick.firstChild);quick.classList.add('v1-urgent-home');$$('.v1urgent-filter',shell).forEach(b=>b.addEventListener('click',()=>{activeFilter=b.dataset.filter||'all';$$('.v1urgent-filter',shell).forEach(x=>x.classList.toggle('on',x===b));renderUrgent()}));quick.addEventListener('scroll',()=>{$('.v1urgent-sticky',shell)?.classList.toggle('compact',quick.scrollTop>36)},{passive:true});quick.addEventListener('touchstart',e=>{if(quick.scrollTop<=1&&e.touches.length===1)pullY=e.touches[0].clientY},{passive:true});quick.addEventListener('touchend',e=>{if(pullY===null)return;const end=e.changedTouches?.[0]?.clientY??pullY,delta=end-pullY;pullY=null;if(delta>72&&quick.scrollTop<=2)loadUrgent()},{passive:true});
  }
  function metricHtml(m){return '<div><b>'+esc(m[0])+'</b><span>'+esc(m[1])+'</span></div>'}
  function renderUrgent(){
    ensureUrgentHome();const shell=$('#v1UrgentHome');if(!shell)return;const visible=urgentItems.filter(x=>!ignored(x)),counts={all:visible.length,price:0,order:0,fresh:0,inventory:0};visible.forEach(x=>{if(counts[x.type]!=null)counts[x.type]++});$$('.v1urgent-filter',shell).forEach(b=>{const s=$('strong',b);if(s)s.textContent=String(counts[b.dataset.filter]??0)});const filtered=activeFilter==='all'?visible:visible.filter(x=>x.type===activeFilter),list=$('.v1urgent-list',shell);if(!filtered.length){list.innerHTML='<div class="v1urgent-empty"><b>✓ No urgent actions</b>'+(visible.length?'No urgent actions in this filter.':'Nothing needs immediate attention right now.')+'</div>';return}list.innerHTML=filtered.map(x=>'<article class="v1urgent-card '+esc(x.type)+'" tabindex="0" role="button" data-urgent-key="'+esc(x.key)+'"><div class="v1urgent-top"><div><div class="v1urgent-name">'+esc(x.name)+'</div><div class="v1urgent-meta">'+(x.family?'Family '+esc(x.family):'')+(x.upc?' · UPC '+esc(x.upc):'')+(x.article?' · Article '+esc(x.article):'')+'</div></div><span class="v1urgent-pill">'+esc(x.pill)+'</span></div><div class="v1urgent-action">'+esc(x.action)+'</div><div class="v1urgent-why">'+esc(x.why)+'</div><div class="v1urgent-metrics">'+x.metrics.map(metricHtml).join('')+'</div><button class="v1urgent-ignore" type="button" data-ignore="'+esc(x.key)+'">IGNORE 12 HOURS</button></article>').join('');$$('[data-urgent-key]',list).forEach(card=>{card.addEventListener('click',e=>{if(e.target.closest('[data-ignore]'))return;openDetail(card.dataset.urgentKey)});card.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&!e.target.closest('[data-ignore]')){e.preventDefault();openDetail(card.dataset.urgentKey)}})});$$('[data-ignore]',list).forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();const item=urgentItems.find(x=>x.key===b.dataset.ignore);if(item)setIgnore(item)}));
  }
  async function loadUrgent(){ensureUrgentHome();const shell=$('#v1UrgentHome'),list=$('.v1urgent-list',shell);if(list)list.innerHTML='<div class="v1urgent-loading">Refreshing urgent actions…</div>';try{const result=await getUrgentLive();urgentItems=result.rows;const up=$('.v1urgent-updated',shell);if(up)up.textContent='Updated '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});renderUrgent();if(activeDetailKey)refreshOpenDetailState()}catch(err){if(list)list.innerHTML='<div class="v1urgent-error">Urgent feed unavailable · '+esc(err?.message||'refresh failed')+'</div>'}}
  function ensureDetail(){if($('#v1UrgentDetail'))return;const d=document.createElement('div');d.id='v1UrgentDetail';d.innerHTML='<div class="v1detail-head"><button class="v1detail-back" type="button">‹</button><div class="v1detail-headcopy"><b>Urgent Action</b><span>Focused single-action view</span></div><span class="v1detail-status">OPEN</span></div><div class="v1detail-body"></div>';document.body.appendChild(d);$('.v1detail-back',d).onclick=closeDetail}
  function renderDetail(item,resolved=false){ensureDetail();const d=$('#v1UrgentDetail'),body=$('.v1detail-body',d),status=$('.v1detail-status',d);status.textContent=resolved?'RESOLVED':'OPEN';status.classList.toggle('resolved',resolved);if(resolved){body.innerHTML='<div class="v1detail-card v1detail-resolved on"><b>Resolved / No longer urgent</b><p>The live urgent condition is no longer present. This focused urgent view is now read-only.</p></div><div class="v1detail-actions"><button class="v1detail-backquick" type="button">BACK TO QUICK CHECK</button></div>';$('.v1detail-backquick',body).onclick=()=>{closeDetail();loadUrgent()};return}if(!item){renderDetail(null,true);return}body.innerHTML='<div class="v1detail-card"><div class="v1detail-name">'+esc(item.name)+'</div><div class="v1detail-type">'+esc(item.pill)+'</div><div class="v1detail-id"><div><b>FAMILY</b><span>'+esc(item.family||'—')+'</span></div><div><b>UPC</b><span>'+esc(item.upc||'—')+'</span></div><div><b>ARTICLE</b><span>'+esc(item.article||'—')+'</span></div></div></div><div class="v1detail-card v1detail-decision"><small>PRIMARY DECISION</small><strong>'+esc(item.action)+'</strong><p>'+esc(item.why)+'</p></div><div class="v1detail-card"><small style="font-size:8px;font-weight:1000;color:#71808d">KEY DECISION DATA</small><div class="v1detail-evidence">'+item.evidence.map(metricHtml).join('')+'</div></div><div class="v1detail-actions"><button class="v1detail-open" type="button">OPEN '+(item.target==='order'?'ORDERING':'PRICE')+' CONTROLS</button><button class="v1detail-refresh" type="button">REFRESH STATUS</button><button class="v1detail-ignore" type="button">IGNORE 12 HOURS</button></div>';$('.v1detail-open',body).onclick=()=>openModule(item.target);$('.v1detail-refresh',body).onclick=()=>refreshDetail();$('.v1detail-ignore',body).onclick=()=>{setIgnore(item);closeDetail()}}
  function openDetail(key){const item=urgentItems.find(x=>x.key===key);if(!item)return;activeDetailKey=key;ensureDetail();$('#v1UrgentDetail').classList.add('on');renderDetail(item,false)}
  function closeDetail(){const d=$('#v1UrgentDetail');if(d)d.classList.remove('on');activeDetailKey=null}
  function openModule(target){closeDetail();const btn=$('.nav button[data-go="'+target+'"]');if(btn)btn.click()}
  async function refreshDetail(){const key=activeDetailKey;if(!key)return;try{const result=await getUrgentLive();urgentItems=result.rows;const item=urgentItems.find(x=>x.key===key);renderUrgent();renderDetail(item,!item)}catch(_){}}
  function refreshOpenDetailState(){if(!activeDetailKey)return;const item=urgentItems.find(x=>x.key===activeDetailKey);renderDetail(item,!item)}
  function syncQuickMode(){const quick=$('#quick'),input=$('#globalInput');if(!quick||!input)return;const searching=!!input.value.trim();quick.classList.toggle('v1-search-mode',searching);quick.classList.toggle('v1-urgent-home',!searching);const rows=$('#quickRows',quick);if(rows)rows.style.display=searching?'':'none'}
  function init(){ensureUrgentHome();ensureDetail();const input=$('#globalInput'),form=$('#globalForm'),clear=$('#quickClear');input?.addEventListener('input',syncQuickMode);form?.addEventListener('submit',()=>{syncQuickMode();input?.blur()});clear?.addEventListener('click',()=>setTimeout(()=>{syncQuickMode();loadUrgent()},0));const quickNav=$('.nav button[data-go="quick"]');quickNav?.addEventListener('click',()=>setTimeout(()=>{if(input){input.value='';input.blur()}syncQuickMode();loadUrgent()},0));syncQuickMode();loadUrgent()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
</script>
'''


def _decorate_html(html: str, version: str = "") -> str:
    if "yipmanV1ConsolidatedRcStyle" in html:
        return html
    html = html.replace("</head>", _STYLE + "</head>", 1)
    html = html.replace(
        '<nav class="nav"><button class="on" data-go="quick"><i>⌕</i>QUICK</button><button data-go="order"><i>▤</i>ORDER</button><button data-go="price"><i>$</i>PRICE</button><button data-go="ai"><i>✦</i>AI</button></nav>',
        '<nav class="nav"><button class="on" data-go="quick"><i>⌕</i>QUICK</button><button data-go="order"><i>▤</i>ORDER</button><button data-go="price"><i>$</i>PRICE</button><button data-go="more"><i>•••</i>MORE</button></nav>',
        1,
    )
    html = html.replace(
        '<section class="page" id="data">',
        _MORE_PAGE + '\n<section class="page" id="data">',
        1,
    )
    html = html.replace("</body>", _SCRIPT + "</body>", 1)
    html = html.replace("FULL MYSQL · " + str(version), "FULL MYSQL · " + str(version) + " · V1 RC", 1)
    return html


def install_mobile_v1_consolidated_rc(app=None) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    base_renderer = _api.yipman_v1_html

    def renderer(version: str = "") -> str:
        return _decorate_html(base_renderer(version), version)

    _api.yipman_v1_html = renderer
    if app is not None:
        app.state.yipman_mobile_v1_consolidated_rc = True
    _INSTALLED = True
