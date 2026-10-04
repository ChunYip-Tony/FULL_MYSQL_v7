from __future__ import annotations

YIPMAN_MOBILE_V2_CSS = r"""
@media(max-width:759px){
  html.yv2-active,html.yv2-active body{background:#eef1f4!important;overflow:hidden!important}
  html.yv2-active #app{display:none!important}
  #yv2{--bg:#eef1f4;--card:#fff;--ink:#111827;--muted:#5f6b7a;--line:#cfd6de;--nav:#17212b;--blue:#1358a8;--bluebg:#edf5ff;--red:#a82820;--redbg:#fff0ee;--amber:#7d5300;--amberbg:#fff4d1;--green:#166846;--greenbg:#e8f4ee;--purple:#5f4796;--purplebg:#f0ebf8;position:fixed;inset:0;z-index:9998;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;overflow:hidden}
  #yv2 *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  #yv2 button,#yv2 input,#yv2 select{font:inherit;color:inherit}
  #yv2 button{cursor:pointer}
  #yv2 .yv2-head{position:absolute;inset:0 0 auto 0;z-index:10;background:rgba(238,241,244,.98);border-bottom:2px solid #c7cfd8;padding:max(env(safe-area-inset-top,0px),10px) 14px 10px}
  @media(display-mode:standalone),(display-mode:fullscreen){#yv2 .yv2-head{padding-top:max(env(safe-area-inset-top,0px),26px)}}
  #yv2 .yv2-headrow{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px}
  #yv2 .yv2-headrow>div:first-child{min-width:0}
  #yv2 .yv2-brand{font-size:23px;font-weight:1000;letter-spacing:-.04em;white-space:nowrap}.yv2-brand span{color:var(--blue)}
  #yv2 .yv2-version{font-size:10px;color:#667085;font-weight:800;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #yv2 .yv2-health{max-width:55vw;overflow:hidden;text-overflow:ellipsis;border:1.5px solid #a8cfbb;background:#edf8f2;color:#155f43;border-radius:999px;padding:7px 9px;font-size:10px;font-weight:950;white-space:nowrap}
  #yv2 .yv2-search{display:flex;align-items:center;gap:7px;margin-top:9px;background:#fff;border:2px solid #c8d0d9;border-radius:14px;padding:0 11px}
  #yv2 .yv2-search input{flex:1;min-width:0;border:0;outline:0;background:transparent;padding:12px 4px;font-size:17px;font-weight:700}
  #yv2 .yv2-search button{border:0;background:transparent;font-size:18px;padding:8px 3px}
  #yv2 .yv2-main{position:absolute;left:0;right:0;top:66px;bottom:68px;overflow:hidden}
  #yv2.lookup-mode .yv2-main{top:122px}
  @media(display-mode:standalone),(display-mode:fullscreen){#yv2 .yv2-main{top:82px}#yv2.lookup-mode .yv2-main{top:138px}}
  #yv2 .yv2-page{display:none;height:100%;overflow-y:auto;overflow-x:hidden;padding:12px 13px 24px;scrollbar-width:none}
  #yv2 .yv2-page::-webkit-scrollbar{display:none}
  #yv2 .yv2-page.on{display:block}
  #yv2 .yv2-title{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin:3px 1px 10px}
  #yv2 .yv2-title h2{font-size:22px;font-weight:1000;margin:0;letter-spacing:-.03em}
  #yv2 .yv2-sub{font-size:12px;color:var(--muted);font-weight:800}
  #yv2 .yv2-card{background:#fff;border:2px solid #d2d8df;border-radius:16px;padding:14px;margin-bottom:12px;box-shadow:0 2px 8px rgba(15,23,42,.06)}
  #yv2 .yv2-familyname{font-size:23px;font-weight:1000;line-height:1.05;letter-spacing:-.03em}
  #yv2 .yv2-meta{font-size:12px;color:var(--muted);font-weight:760;margin-top:4px;line-height:1.35}
  #yv2 .yv2-badge{display:inline-flex;border-radius:999px;padding:5px 8px;font-size:10px;font-weight:950;border:1.5px solid #c8d0d8;background:#eef1f4;color:#384657;white-space:nowrap}
  #yv2 .yv2-badge.red{background:var(--redbg);color:var(--red);border-color:#dda8a2}
  #yv2 .yv2-badge.amber{background:var(--amberbg);color:var(--amber);border-color:#d9bb6d}
  #yv2 .yv2-badge.green{background:var(--greenbg);color:var(--green);border-color:#a8cdb8}
  #yv2 .yv2-badge.purple{background:var(--purplebg);color:var(--purple);border-color:#cbbce5}
  #yv2 .yv2-topline{display:flex;align-items:flex-start;justify-content:space-between;gap:9px}
  #yv2 .yv2-grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:11px}
  #yv2 .yv2-metric{border:1.8px solid #d4dae1;background:#fafbfc;border-radius:13px;padding:10px}
  #yv2 .yv2-metric.edit{background:#edf5ff;border:2px solid #7ea9d7}
  #yv2 .yv2-metric.warn{background:#fff7dc;border:2px solid #d9bb6d}
  #yv2 .yv2-metric.danger{background:#fff0ee;border:2px solid #dca6a0}
  #yv2 .yv2-metric.good{background:#edf7f1;border:2px solid #a8cdb8}
  #yv2 .yv2-label{font-size:10px;color:#566273;font-weight:950;letter-spacing:.04em;text-transform:uppercase}
  #yv2 .yv2-value{font-size:20px;font-weight:1000;margin-top:3px;letter-spacing:-.02em}
  #yv2 .yv2-minor{font-size:11px;color:#687485;font-weight:720;margin-top:3px}
  #yv2 .yv2-pricegrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:9px}
  #yv2 .yv2-price{border:1.6px solid #d4dae1;background:#fafbfc;border-radius:12px;padding:8px;min-width:0}
  #yv2 .yv2-price b{display:block;font-size:17px;font-weight:1000;margin-top:2px;white-space:nowrap}
  #yv2 .yv2-price span{display:block;font-size:9px;color:var(--muted);font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #yv2 .yv2-tabs{display:flex;gap:7px;overflow-x:auto;scrollbar-width:none;margin:0 0 10px}.yv2-tabs::-webkit-scrollbar{display:none}
  #yv2 .yv2-tab{border:2px solid #cfd6de;background:#fff;border-radius:999px;padding:8px 11px;font-size:12px;font-weight:950;color:#465466;white-space:nowrap}
  #yv2 .yv2-tab.on{background:var(--nav);border-color:var(--nav);color:#fff}
  #yv2 .yv2-action{border-left:6px solid #94a3b8;color:var(--ink)!important}.yv2-action.red{border-left-color:#c84a42}.yv2-action.amber{border-left-color:#d39a2c}.yv2-action.blue{border-left-color:#4e83bd}.yv2-action.purple{border-left-color:#8064b6}.yv2-action.green{border-left-color:#3b8a62}
  #yv2 .yv2-actiontype{font-size:10px;color:#627084;font-weight:1000;letter-spacing:.05em;text-transform:uppercase}
  #yv2 .yv2-actionname{font-size:19px;font-weight:1000;margin-top:2px}
  #yv2 .yv2-reason{font-size:13px;color:#465466;font-weight:700;line-height:1.45;margin-top:7px}
  #yv2 .yv2-btnrow{display:flex;gap:7px;margin-top:10px}
  #yv2 .yv2-btn{min-height:42px;flex:1;border:2px solid #cbd3dc;border-radius:11px;background:#fff;color:#233143;font-size:12px;font-weight:1000;padding:9px}
  #yv2 .yv2-btn.primary{background:var(--nav);border-color:var(--nav);color:#fff}
  #yv2 .yv2-btn.ignore{background:var(--redbg);border-color:#d9aaa5;color:var(--red)}
  #yv2 .yv2-orderhead{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:9px}
  #yv2 .yv2-datebox{border:2px solid #cfd6de;background:#fff;border-radius:12px;padding:8px}
  #yv2 .yv2-datebox label{display:block;font-size:9px;color:#667085;font-weight:950;text-transform:uppercase}
  #yv2 .yv2-datebox input{width:100%;border:0;outline:0;background:transparent;font-size:14px;font-weight:950;margin-top:2px}
  #yv2 .yv2-orderqty{background:#edf5ff;border:2px solid #9bbce0;border-radius:13px;padding:10px;margin-top:10px}
  #yv2 .yv2-orderqty b{display:block;font-size:29px;color:#124f91;font-weight:1000;line-height:1}
  #yv2 .yv2-recv{margin-top:8px;border-top:1px solid #d9dfe5;padding-top:7px;font-size:12px;font-weight:800;color:#455566}
  #yv2 .yv2-listrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;align-items:center;padding:10px 0;border-top:1px solid #e2e7ec}.yv2-listrow:first-child{border-top:0}
  #yv2 .yv2-listrow b{font-size:14px}.yv2-listrow span{display:block;font-size:11px;color:var(--muted);font-weight:700;margin-top:2px}
  #yv2 .yv2-kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  #yv2 .yv2-kpi{background:#fff;border:2px solid #d2d8df;border-radius:14px;padding:11px}
  #yv2 .yv2-kpi b{display:block;font-size:23px;font-weight:1000;margin-top:2px}
  #yv2 .yv2-kpi span{font-size:10px;color:#5f6b7a;font-weight:900}
  #yv2 .yv2-select{width:100%;border:2px solid #cfd6de;background:#fff;border-radius:12px;padding:10px;font-size:13px;font-weight:900}
  #yv2 .yv2-bottom{position:absolute;inset:auto 0 0 0;z-index:12;background:var(--nav);padding:5px 5px max(env(safe-area-inset-bottom,0px),5px);display:grid;grid-template-columns:repeat(5,1fr);gap:2px}
  #yv2 .yv2-nav{border:0;background:transparent;color:#bcc5cf;border-radius:11px;padding:6px 2px 5px;font-size:9px;font-weight:900;min-height:55px;pointer-events:auto!important;touch-action:manipulation}
  #yv2 .yv2-nav i{font-style:normal;display:block;font-size:20px;margin-bottom:1px}.yv2-nav.on{background:#2c3946;color:#fff}
  #yv2 .yv2-empty{background:#fff;border:2px solid #d2d8df;border-radius:15px;padding:22px 14px;text-align:center;color:#5f6b7a;font-size:13px;font-weight:720}
  #yv2 .yv2-loading{padding:18px;text-align:center;color:#5f6b7a;font-size:13px;font-weight:800}
  #yv2 .yv2-moregrid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  #yv2 .yv2-more{min-height:92px;text-align:left;border:2px solid #d2d8df;background:#fff;border-radius:14px;padding:13px}.yv2-more b{display:block;font-size:15px;font-weight:1000}.yv2-more span{display:block;font-size:11px;color:var(--muted);font-weight:700;margin-top:4px;line-height:1.35}
  #yv2 .yv2-modalback{position:fixed;inset:0;z-index:10000;background:rgba(15,23,42,.5);display:none;align-items:flex-end}.yv2-modalback.on{display:flex}
  #yv2 .yv2-modal{width:100%;max-height:88vh;overflow-y:auto;background:#fff;border-radius:22px 22px 0 0;padding:16px 14px max(env(safe-area-inset-bottom,0px),16px)}
  #yv2 .yv2-modal h3{font-size:21px;font-weight:1000;margin:0}.yv2-modal p{font-size:12px;color:var(--muted);font-weight:700;line-height:1.4;margin:5px 0}
  #yv2 .yv2-input{width:100%;border:2px solid #8798aa;border-radius:12px;background:#fff;padding:11px;font-size:20px;font-weight:950;outline:0;margin-top:9px}
  #yv2 .yv2-formgrid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.yv2-formgrid label{font-size:9px;color:#667085;font-weight:950}.yv2-formgrid input{display:block;width:100%;margin-top:3px;border:1.8px solid #cfd6de;border-radius:10px;padding:9px;font-size:13px;font-weight:850}
  #yv2 .yv2-promosearch{display:flex;gap:6px;margin-top:9px}.yv2-promosearch input{flex:1;min-width:0;border:2px solid #cfd6de;border-radius:11px;padding:10px;font-size:15px;font-weight:800}
  #yv2 .yv2-promoresult{width:100%;text-align:left;border:1.8px solid #d5dce3;background:#fafbfc;border-radius:11px;padding:9px;margin-top:6px}.yv2-promoresult b{display:block;font-size:15px}.yv2-promoresult span{display:block;font-size:10px;color:var(--muted);margin-top:2px}
  #yv2 .yv2-selected{border:1.8px solid #a8cdb8;background:#edf7f1;border-radius:11px;padding:9px;margin-top:7px}.yv2-selected b{font-size:14px}.yv2-selected button{float:right;border:1px solid #d9aaa5;background:#fff0ee;color:#a82820;border-radius:8px;font-size:10px;font-weight:950;padding:5px 7px}
  #yv2 .yv2-toast{position:fixed;left:50%;transform:translateX(-50%);bottom:78px;z-index:10002;background:#17212b;color:#fff;border-radius:999px;padding:9px 13px;font-size:12px;font-weight:900;opacity:0;pointer-events:none;transition:.18s;white-space:nowrap;max-width:92vw;overflow:hidden;text-overflow:ellipsis}.yv2-toast.on{opacity:1}
  #yv2 .yv2-line{height:1px;background:#d7dde4;margin:11px 0}
  #yv2 .yv2-link{color:#1358a8;text-decoration:none;font-weight:900}
}
"""

YIPMAN_MOBILE_V2_JS = r"""
(()=>{
  if(!window.matchMedia('(max-width:759px)').matches)return;
  if(new URLSearchParams(location.search).get('classic')==='1')return;
  document.documentElement.classList.add('yv2-active');
  window.__YV2_READY__=false;
  window.__YV2_LAST_ERROR__='';

  const V={
    page:'lookup', actionFilter:'all', orderMode:'regular', actions:[], orderRows:[],
    delivery:null,nextDelivery:null, orderCalendar:null, performanceEnd:null,
    promoListId:null,promoListDetail:null,promoSelected:new Map(),promoSearchRows:[],stockContext:null,dataThrough:null
  };
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null};
  const fmt=(v,d=1)=>{const n=num(v);return n===null?'—':n.toLocaleString(undefined,{maximumFractionDigits:d})};
  const money=v=>{const n=num(v);return n===null?'—':'$'+n.toFixed(2)};
  const iso=d=>{const z=new Date(d);z.setHours(12,0,0,0);return z.toISOString().slice(0,10)};
  const plus=(v,n)=>{const d=new Date(v+'T12:00:00');d.setDate(d.getDate()+n);return iso(d)};
  const api=async(url,opt={})=>{
    if(typeof window.api==='function')return window.api(url,opt);
    const c=new AbortController(),tm=setTimeout(()=>c.abort(),opt.timeoutMs||18000);
    try{const r=await fetch(url,{...opt,signal:c.signal,headers:{Accept:'application/json',...(opt.headers||{})},cache:'no-store'});const t=await r.text();let d={};try{d=t?JSON.parse(t):{}}catch{}if(!r.ok)throw new Error(d?.detail?.reason||d?.detail||t||('HTTP '+r.status));return d}finally{clearTimeout(tm)}
  };
  const root=document.createElement('div');root.id='yv2';root.classList.add('lookup-mode');
  root.innerHTML=`
    <header class="yv2-head">
      <div class="yv2-headrow"><div><div class="yv2-brand">Yipman <span>V2</span></div><div class="yv2-version">Easy Read · __VERSION__</div></div><div class="yv2-health" id="yv2Health">Checking data…</div></div>
      <form class="yv2-search" id="yv2SearchForm"><button type="submit" id="yv2SearchBtn" aria-label="Search" style="border:0;background:transparent;padding:8px 3px;font-size:18px">⌕</button><input id="yv2Search" placeholder="UPC / article / English / 中文" autocomplete="off" enterkeyhint="search"><button type="button" id="yv2SearchClear">×</button></form>
    </header>
    <main class="yv2-main">
      <section class="yv2-page on" id="yv2-lookup"><div class="yv2-title"><h2>Item Lookup</h2><span class="yv2-sub">One item · one screen</span></div><div id="yv2LookupRows"><div class="yv2-empty">Search a UPC, Family Article, Receiving Article, English name, or Chinese name.</div></div></section>
      <section class="yv2-page" id="yv2-actions"><div class="yv2-title"><h2>Action List</h2><span class="yv2-sub" id="yv2ActionCount">Loading…</span></div><div class="yv2-tabs" id="yv2ActionTabs"><button class="yv2-tab on" data-af="all">All</button><button class="yv2-tab" data-af="price">Price</button><button class="yv2-tab" data-af="stock">Stock</button><button class="yv2-tab" data-af="order">Order</button><button class="yv2-tab" data-af="freshness">Freshness</button></div><div id="yv2Actions"><div class="yv2-loading">Building action list…</div></div></section>
      <section class="yv2-page" id="yv2-order"><div class="yv2-title"><h2>Ordering</h2><span class="yv2-sub" id="yv2OrderStatus">Observed delivery</span></div><div class="yv2-orderhead"><div class="yv2-datebox"><label>Delivery</label><input type="date" id="yv2Delivery"></div><div class="yv2-datebox"><label>Next delivery</label><input type="date" id="yv2NextDelivery"></div></div><div class="yv2-tabs"><button class="yv2-tab on" data-om="regular">Regular</button><button class="yv2-tab" data-om="promotion">Promotion</button></div><div id="yv2OrderRows"><div class="yv2-loading">Loading ordering calendar…</div></div></section>
      <section class="yv2-page" id="yv2-performance"><div class="yv2-title"><h2>Performance</h2><span class="yv2-sub" id="yv2PerfStatus">Completed days only</span></div><div class="yv2-tabs" id="yv2PerfTabs"><button class="yv2-tab on" data-days="1">Yesterday</button><button class="yv2-tab" data-days="7">7D</button><button class="yv2-tab" data-days="14">14D</button><button class="yv2-tab" data-days="28">28D</button></div><div id="yv2Performance"><div class="yv2-loading">Loading performance…</div></div></section>
      <section class="yv2-page" id="yv2-more"><div class="yv2-title"><h2>More</h2><span class="yv2-sub">Secondary tools</span></div><div class="yv2-moregrid"><button class="yv2-more" data-more="pi"><b>True Stock / PI</b><span>Search Family stock and Pending Dumping.</span></button><button class="yv2-more" data-more="tpr"><b>Current TPR</b><span>All active TPR items and progress.</span></button><button class="yv2-more" data-more="receipt"><b>Receipts</b><span>Use Item Lookup to inspect receipt history.</span></button><button class="yv2-more" data-more="data"><b>Data Status</b><span>Published-through and source freshness.</span></button></div><div class="yv2-card" style="margin-top:10px;padding:11px 12px"><div class="yv2-meta"><b style="color:#344054">Desktop Back Office</b> keeps uploads, batches, QA fixes and mapping repair.</div><div class="yv2-btnrow" style="margin-top:7px"><button class="yv2-btn" id="yv2Classic">Classic mobile</button></div></div></section>
    </main>
    <nav class="yv2-bottom"><button class="yv2-nav on" data-page="lookup"><i>⌕</i>Lookup</button><button class="yv2-nav" data-page="actions"><i>✓</i>Actions</button><button class="yv2-nav" data-page="order"><i>▣</i>Order</button><button class="yv2-nav" data-page="performance"><i>▥</i>Performance</button><button class="yv2-nav" data-page="more"><i>•••</i>More</button></nav>
    <div class="yv2-modalback" id="yv2Modal"><div class="yv2-modal"><div id="yv2ModalBody"></div></div></div><div class="yv2-toast" id="yv2Toast"></div>`;
  document.body.appendChild(root);

  const $=s=>root.querySelector(s), $$=s=>[...root.querySelectorAll(s)];
  const setUiError=(msg)=>{
    window.__YV2_LAST_ERROR__=String(msg||'Unknown UI error');
    const box=$('#yv2Health');
    if(box){
      box.textContent='UI ERROR';
      box.title=window.__YV2_LAST_ERROR__;
      box.style.background='#fff0ee';box.style.color='#a82820';box.style.borderColor='#dca6a0';
    }
  };
  window.addEventListener('error',e=>setUiError(e?.error?.message||e?.message||'JavaScript error'));
  window.addEventListener('unhandledrejection',e=>setUiError(e?.reason?.message||e?.reason||'Unhandled promise error'));
  const toast=m=>{const e=$('#yv2Toast');e.textContent=m;e.classList.add('on');clearTimeout(V.toastTimer);V.toastTimer=setTimeout(()=>e.classList.remove('on'),1800)};
  const modal=(html)=>{$('#yv2ModalBody').innerHTML=html;$('#yv2Modal').classList.add('on')};
  const closeModal=()=>$('#yv2Modal').classList.remove('on');
  $('#yv2Modal').onclick=e=>{if(e.target.id==='yv2Modal')closeModal()};

  function go(p){
    if(!['lookup','actions','order','performance','more'].includes(p))return;
    V.page=p;
    root.classList.toggle('lookup-mode',p==='lookup');
    $$('.yv2-page').forEach(x=>x.classList.toggle('on',x.id==='yv2-'+p));
    $$('.yv2-nav').forEach(x=>x.classList.toggle('on',x.dataset.page===p));
    const searchForm=$('#yv2SearchForm');if(searchForm)searchForm.style.display=p==='lookup'?'flex':'none';
    const page=$('#yv2-'+p);if(page&&typeof page.scrollTo==='function')page.scrollTo(0,0);
    if(p==='actions'&&!V.actionsLoaded)loadActions();
    if(p==='order'&&!V.orderLoaded)initOrder();
    if(p==='performance'&&!V.performanceLoaded)loadPerformance(1);
  }
  let lastNavPointerAt=0;
  const navDispatch=e=>{
    const nav=e.target.closest?.('[data-page]');
    if(!nav||!root.contains(nav))return false;
    if(e.type==='click'&&Date.now()-lastNavPointerAt<700){e.preventDefault();return true}
    if(e.type==='pointerup')lastNavPointerAt=Date.now();
    e.preventDefault();go(nav.dataset.page);return true;
  };
  root.addEventListener('pointerup',navDispatch,true);
  root.addEventListener('click',navDispatch,true);

  let lastControlPointerAt=0,promoSearchTimer=null;
  const controlDispatch=e=>{
    const target=e.target;
    const actionable=target.closest?.('[data-stock-family],#yv2AddPromo,[data-promo-result],[data-promo-remove],[data-promo-remove-item],#yv2PromoCancel,#yv2PromoSave,#yv2StockCancel,#yv2StockSave,#yv2ModalClose');
    if(!actionable||!root.contains(actionable))return false;
    if(e.type==='click'&&Date.now()-lastControlPointerAt<650){e.preventDefault();return true}
    if(e.type==='pointerup')lastControlPointerAt=Date.now();
    e.preventDefault();e.stopPropagation();
    if(actionable.matches('[data-stock-family]')){openTrueStock({family:actionable.dataset.stockFamily,name:actionable.dataset.stockName,oh:actionable.dataset.stockOh,uom:actionable.dataset.stockUom});return true}
    if(actionable.id==='yv2AddPromo'){openPromoBuilder();return true}
    if(actionable.matches('[data-promo-result]')){selectPromo(V.promoSearchRows[Number(actionable.dataset.promoResult)]);return true}
    if(actionable.matches('[data-promo-remove]')){V.promoSelected.delete(actionable.dataset.promoRemove);renderPromoSelected();toast('Promotion item removed');return true}
    if(actionable.matches('[data-promo-remove-item]')){removePersistedPromoItem(actionable.dataset.promoRemoveItem,actionable);return true}
    if(actionable.id==='yv2PromoCancel'||actionable.id==='yv2StockCancel'||actionable.id==='yv2ModalClose'){V.stockContext=null;closeModal();return true}
    if(actionable.id==='yv2PromoSave'){savePromo();return true}
    if(actionable.id==='yv2StockSave'){saveTrueStock();return true}
    return false;
  };
  root.addEventListener('pointerup',controlDispatch,true);
  root.addEventListener('click',controlDispatch,true);
  root.addEventListener('submit',e=>{if(e.target?.id==='yv2PromoSearchForm'){e.preventDefault();runPromoSearch()}});
  root.addEventListener('input',e=>{if(e.target?.id==='yv2PromoSearch'){clearTimeout(promoSearchTimer);const q=e.target.value.trim();if(q.length>=2)promoSearchTimer=setTimeout(runPromoSearch,350)}});

  async function loadHealth(){
    const box=$('#yv2Health');
    box.textContent='Checking data…';
    box.className='yv2-health';
    box.style.background='';box.style.color='';box.style.borderColor='';
    try{
      const results=await Promise.allSettled([
        api('/v1/yipman/header-freshness',{timeoutMs:9000}),
        api('/v1/backoffice/data-health?days=14',{timeoutMs:10000}),
        api('/v1/backoffice/home-summary',{timeoutMs:10000})
      ]);
      const hf=results[0].status==='fulfilled'?results[0].value:{};
      const h=results[1].status==='fulfilled'?results[1].value:{};
      const home=results[2].status==='fulfilled'?results[2].value:{};
      const latest=h?.latest||{},ph=home?.pricing?.data_health||home?.ordering?.data_health||{};
      const src=hf?.sources||{};
      const posDate=src?.POS?.date||latest?.POS?.date||ph.pos_data_through||null;
      const mvtDate=src?.MVT?.date||latest?.MVT?.date||ph.movement_data_through||null;
      V.dataThrough=ph.data_through||ph.pos_data_through||posDate||mvtDate||null;
      const expected=ph.expected_through||h?.completed_through||null;
      const staleByDate=!!(V.dataThrough&&expected&&String(V.dataThrough)<String(expected));
      const staleBySource=['warn','bad'].includes(String(src?.POS?.tone||''))||['warn','bad'].includes(String(src?.MVT?.tone||''));
      const stale=staleByDate||staleBySource;
      if(V.dataThrough){
        const short=v=>String(v||'').slice(5).replace('-','/');
        box.textContent=stale?('DATA '+short(V.dataThrough)+' → '+short(expected||'')):('DATA '+short(V.dataThrough)+' ✓');
        box.title=stale?('Data through '+V.dataThrough+' · expected '+expected):('Published through '+V.dataThrough);
      }else if(posDate||mvtDate){
        box.textContent='DATA CHECK';
        box.title='POS '+String(posDate||'—')+' · MVT '+String(mvtDate||'—');
      }else{
        box.textContent='DATA unavailable';
      }
      if(stale||!V.dataThrough){box.style.background='#fff4d1';box.style.color='#7d5300';box.style.borderColor='#d9bb6d'}
    }catch(e){
      box.textContent='Data unavailable';
      box.style.background='#fff4d1';box.style.color='#7d5300';box.style.borderColor='#d9bb6d';
    }
  }

  function familyGroups(rows){
    const m=new Map();
    for(const r of rows||[]){
      const k=String(r.family_article||r.family_id||r.upc||'');
      if(!m.has(k))m.set(k,{family:k,name:r.family_name||r.name||'Item',category:r.category||'',rows:[],oh:r.family_oh??r.current_oh,oh_uom:r.family_oh_uom||r.current_oh_uom||r.selling_uom||'',system:r.family_system_oh??r.system_oh,cost:r.family_cost??r.current_cost,cost_uom:r.family_cost_uom||r.selling_uom||'',receipt:r.family_receipt_7d_qty,mvt:r.family_group_movement_7d??r.family_qty_7d,mvt_uom:r.family_group_movement_uom||r.family_qty_uom||r.selling_uom||''});
      const g=m.get(k);g.rows.push(r);
    }
    return [...m.values()];
  }
  function resultCard(g){
    const upcs=[...new Map(g.rows.map(r=>[String(r.upc||''),r])).values()].filter(r=>r.upc).slice(0,6);
    return `<article class="yv2-card"><div class="yv2-topline"><div><div class="yv2-familyname">${esc(g.name)}</div><div class="yv2-meta">Family ${esc(g.family)} · ${esc(g.category||'Seafood')}</div></div><span class="yv2-badge">${esc(g.category||'ITEM')}</span></div>
      <div class="yv2-grid2"><button class="yv2-metric edit" data-stock-family="${esc(g.family)}" data-stock-name="${esc(g.name)}" data-stock-oh="${esc(g.oh??'')}" data-stock-uom="${esc(g.oh_uom)}"><div class="yv2-label">Effective OH · tap</div><div class="yv2-value">${fmt(g.oh)} ${esc(g.oh_uom)}</div><div class="yv2-minor">System ${fmt(g.system)} ${esc(g.oh_uom)}</div></button><div class="yv2-metric"><div class="yv2-label">Family cost</div><div class="yv2-value">${money(g.cost)}</div><div class="yv2-minor">${esc(g.cost_uom||'current authority')}</div></div><div class="yv2-metric"><div class="yv2-label">7D selling mvt</div><div class="yv2-value">${fmt(g.mvt)} ${esc(g.mvt_uom)}</div></div><div class="yv2-metric"><div class="yv2-label">7D receipt</div><div class="yv2-value">${fmt(g.receipt)} ${esc(g.mvt_uom)}</div></div></div>
      <div class="yv2-line"></div>${upcs.map(r=>`<button class="yv2-listrow" data-upc="${esc(r.upc)}" style="width:100%;border-left:0;border-right:0;border-bottom:0;background:transparent;text-align:left"><div><b>${esc(r.name||r.upc)}</b><span>UPC ${esc(r.upc)} · 7D ${fmt(r.qty_7d)} ${esc(r.qty_uom||r.selling_uom||'')}</span></div><div><b>${money(r.current_price)}</b><span>${esc(r.current_price_type||'DETAIL')}</span></div></button>`).join('')||'<div class="yv2-meta">No selling UPC detail in this result.</div>'}</article>`;
  }
  async function searchLookup(q){
    const box=$('#yv2LookupRows');q=String(q||'').trim();
    if(q.length<2){box.innerHTML='<div class="yv2-empty">Enter at least 2 characters.</div>';return}
    box.innerHTML='<div class="yv2-loading">Searching current inventory…</div>';
    try{
      const d=await api('/v1/backoffice/inventory?category=ALL&limit=100&lightweight=true&include_oh=true&q='+encodeURIComponent(q),{timeoutMs:18000});
      const groups=familyGroups(d.rows||[]).slice(0,10);
      box.innerHTML=groups.map(resultCard).join('')||'<div class="yv2-empty">No matching items.</div>';
      bindStockButtons(box);box.querySelectorAll('[data-upc]').forEach(b=>b.onclick=()=>openUpc(b.dataset.upc));
    }catch(e){box.innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  $('#yv2SearchForm').addEventListener('submit',e=>{e.preventDefault();const q=$('#yv2Search').value.trim();if(q.length<2){toast('Enter at least 2 characters');$('#yv2Search').focus();return}searchLookup(q);$('#yv2Search').blur()});
  let st;$('#yv2Search').addEventListener('input',()=>{clearTimeout(st);const q=$('#yv2Search').value.trim();if(q.length>=2)st=setTimeout(()=>searchLookup(q),330)});
  root.addEventListener('click',e=>{
    if(e.target.closest?.('#yv2SearchClear')){$('#yv2Search').value='';$('#yv2LookupRows').innerHTML='<div class="yv2-empty">Search a UPC, Family Article, Receiving Article, English name, or Chinese name.</div>';$('#yv2Search').focus()}
  });

  async function openUpc(upc){
    modal('<h3>Loading item…</h3><p>'+esc(upc)+'</p><div class="yv2-loading">Loading current item detail…</div>');
    try{
      const d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc),{timeoutMs:16000}),oh=d.effective_oh||{},sys=d.system_oh||{},q7=d.qty_7d||{};
      modal(`<div class="yv2-topline"><div><h3>${esc(d.upc_name||upc)}</h3><p>UPC ${esc(d.upc||upc)} · Family ${esc(d.family_article_number||'—')}</p></div><span class="yv2-badge">${esc(d.category||d.product_class||'ITEM')}</span></div>
      <div class="yv2-grid2"><button class="yv2-metric edit" data-stock-family="${esc(d.family_article_number||'')}" data-stock-name="${esc(d.family_article_name||d.upc_name||'')}" data-stock-oh="${esc(oh.quantity??'')}" data-stock-uom="${esc(oh.uom||d.selling_uom||'')}"><div class="yv2-label">Effective OH · tap</div><div class="yv2-value">${fmt(oh.quantity)} ${esc(oh.uom||d.selling_uom||'')}</div><div class="yv2-minor">System ${fmt(sys.quantity)} ${esc(sys.uom||d.selling_uom||'')}</div></button><div class="yv2-metric"><div class="yv2-label">7D sold</div><div class="yv2-value">${fmt(q7.sold_quantity)} ${esc(d.qty_uom||'')}</div><div class="yv2-minor">${fmt(d.upc_velocity_7d)} / day</div></div><div class="yv2-metric"><div class="yv2-label">Current price</div><div class="yv2-value">${money(d.current_price)}</div><div class="yv2-minor">${esc(d.current_price_type||d.current_price_source||'')}</div></div><div class="yv2-metric"><div class="yv2-label">Current cost</div><div class="yv2-value">${money(d.current_cost_per_selling_unit)}</div><div class="yv2-minor">/${esc(d.selling_uom||'unit')}</div></div></div>
      <div class="yv2-card" style="margin-top:10px"><div class="yv2-label">Current basis</div><div class="yv2-reason">Price: ${esc(d.current_price_source||'—')} ${d.current_price_asof_date?'· '+esc(d.current_price_asof_date):''}<br>OH: ${esc(oh.status||oh.source||'—')}<br>DOS: ${fmt(d.dos)}</div></div><div class="yv2-btnrow"><button class="yv2-btn" id="yv2ModalClose">Close</button></div>`);
      bindStockButtons($('#yv2ModalBody'));$('#yv2ModalClose').onclick=closeModal;
    }catch(e){modal('<h3>Unable to load</h3><p>'+esc(e.message)+'</p><div class="yv2-btnrow"><button class="yv2-btn" id="yv2ModalClose">Close</button></div>');$('#yv2ModalClose').onclick=closeModal}
  }

  function bindStockButtons(ctx=root){return ctx}
  async function openTrueStock(d){
    if(!d.family)return toast('Family Article unavailable');
    let qty=d.oh,uom=d.uom;
    modal('<h3>True Stock · '+esc(d.name||d.family)+'</h3><p>Family '+esc(d.family)+' · loading latest Effective OH…</p><div class="yv2-loading">Loading…</div>');
    try{
      const pi=await api('/v1/app/v2/pi/'+encodeURIComponent(d.family),{timeoutMs:10000}),eff=pi?.effective_oh||{},sys=pi?.system_oh||{};
      qty=eff.quantity??qty;uom=pi?.required_true_stock_uom||eff.uom||sys.uom||uom;
      if(!uom)throw new Error('True Stock UOM unavailable');
      V.stockContext={family:String(d.family),name:d.name||d.family,uom:String(uom)};
      modal(`<h3>True Stock · ${esc(d.name||d.family)}</h3><p>Family ${esc(d.family)} · Current Effective OH ${fmt(qty)} ${esc(uom)}. Saving becomes immediate OH authority for every OH-dependent page.</p><input class="yv2-input" id="yv2StockQty" type="number" min="0" step="0.01" inputmode="decimal" value="${esc(qty??'')}"><input class="yv2-input" id="yv2StockNote" style="font-size:14px" placeholder="Physical count note (optional)"><div class="yv2-btnrow"><button class="yv2-btn" id="yv2StockCancel">Cancel</button><button class="yv2-btn primary" id="yv2StockSave">Save & Recalculate</button></div>`);
      setTimeout(()=>$('#yv2StockQty')?.select(),60);
    }catch(e){V.stockContext=null;modal('<h3>True Stock unavailable</h3><p>'+esc(e.message)+'</p><div class="yv2-btnrow"><button class="yv2-btn" id="yv2ModalClose">Close</button></div>')}
  }
  async function saveTrueStock(){
    const d=V.stockContext,qtyEl=$('#yv2StockQty');if(!d||!qtyEl)return;
    const n=Number(qtyEl.value);if(!Number.isFinite(n)||n<0)return toast('Enter valid True Stock');
    const btn=$('#yv2StockSave');if(btn){btn.disabled=true;btn.textContent='Saving…'}
    try{
      await api('/v1/app/v2/pi/'+encodeURIComponent(d.family)+'/true-stock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:n,uom:d.uom,note:$('#yv2StockNote')?.value?.trim()||null}),timeoutMs:30000});
      V.stockContext=null;closeModal();toast('True Stock saved · recalculating');
      V.actionsLoaded=false;V.orderLoaded=false;
      if(V.page==='lookup'&&$('#yv2Search')?.value?.trim())await searchLookup($('#yv2Search').value.trim());
      else if(V.page==='actions')await loadActions();
      else if(V.page==='order'&&V.orderMode==='promotion')await calcPromotion();
      else if(V.page==='order')await loadRegularOrder();
    }catch(e){toast(e.message||'Could not save True Stock');if(btn){btn.disabled=false;btn.textContent='Save & Recalculate'}}
  }

  const ignored=id=>{const t=Number(localStorage.getItem('yv2-ignore-'+id)||0);return t>Date.now()};
  const ignore=id=>{localStorage.setItem('yv2-ignore-'+id,String(Date.now()+12*3600*1000));V.actionsLoaded=false;loadActions()};
  function addAction(a){if(!a.id||ignored(a.id))return;V.actions.push(a)}
  async function orderingDefaults(){
    const cal=await api('/v1/yipman/ordering-calendar?lookback_days=180',{timeoutMs:18000});
    V.orderCalendar=cal;V.delivery=V.delivery||cal.default_delivery_date;V.nextDelivery=V.nextDelivery||cal.default_next_delivery_date||(V.delivery?plus(V.delivery,7):null);
    return cal;
  }
  async function loadActions(){
    V.actionsLoaded=true;V.actions=[];$('#yv2Actions').innerHTML='<div class="yv2-loading">Combining price, TPR, freshness and ordering actions…</div>';
    try{
      await orderingDefaults();
      const [p,t,c,o]=await Promise.all([
        api('/v1/yipman/pricing-review?category=ALL&limit=1000',{timeoutMs:16000}).catch(()=>({rows:[]})),
        api('/v1/yipman/current-tpr-review?category=ALL&limit=1000',{timeoutMs:16000}).catch(()=>({rows:[]})),
        api('/v1/yipman/clearance?status=ACTIVE&limit=100',{timeoutMs:16000}).catch(()=>({rows:[]})),
        V.delivery?api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(V.delivery)+'&next_delivery_date='+encodeURIComponent(V.nextDelivery),{timeoutMs:30000}).catch(()=>({rows:[]})):Promise.resolve({rows:[]})
      ]);
      for(const r of p.rows||[]){
        const prefix=String(r.upc||'').replace(/\D/g,'').replace(/^0+/,'').slice(0,3);
        const stock={family:r.family_article_number,name:r.family_name||r.name,oh:r.current_oh,uom:r.current_oh_uom||r.selling_uom};
        if(r.priority_240_249_mismatch)addAction({id:'pair-'+r.upc,type:'price',tone:'red',badge:'240≠249',name:r.name||r.upc,reason:'249 '+money(r.current_price)+' must match 240 '+money(r.related_240_current_price)+'.',upc:r.upc,...stock,rank:100});
        else if(r.reg_suggestion_actionable)addAction({id:'reg-'+r.upc,type:'price',tone:'blue',badge:'REG',name:r.name||r.upc,reason:'Current '+money(r.current_price)+' · proved sweet spot '+money(r.reg_suggestion_price??r.tested_price)+'. '+(r.reg_suggestion_reason||r.primary_reason_text||''),upc:r.upc,...stock,rank:55});
        else if(r.tpr_suggestion_actionable)addAction({id:'tpr-'+r.upc,type:(String(r.tpr_suggestion_purpose||'').includes('FRESH')?'freshness':'price'),tone:'purple',badge:'TPR',name:r.name||r.upc,reason:'TPR suggestion '+money(r.tpr_suggestion_price??r.testing_price)+' · '+(r.tpr_suggestion_reason||r.primary_reason_text||''),upc:r.upc,...stock,rank:50});
      }
      for(const r of t.rows||[]){
        const code=String(r.recommendation_code||'CONTINUE_TPR').toUpperCase();
        const fresh=String(r.tpr_purpose||r.tpr_purpose_source||'').toUpperCase().includes('FRESH')||num(r.doh)>=5;
        if(code!=='CONTINUE_TPR'||fresh)addAction({id:'progress-'+r.upc,type:fresh?'freshness':'price',tone:fresh?'red':'purple',badge:code==='CONTINUE_TPR'?'TPR CHECK':code.replaceAll('_',' '),name:r.name||r.upc,reason:(r.recommendation_reason||'Review current TPR performance')+' · current '+money(r.current_tpr_price)+(r.suggested_tpr_price!=null?' → '+money(r.suggested_tpr_price):''),upc:r.upc,family:r.family_article_number,nameStock:r.family_name||r.name,oh:r.current_oh,uom:r.current_oh_uom||r.selling_uom,rank:fresh?90:65});
      }
      for(const r of c.rows||[])addAction({id:'clear-'+(r.clearance_plan_id||r.upc),type:'freshness',tone:'red',badge:'CLEARANCE',name:r.name||r.upc||'Clearance',reason:'Active clearance · '+(r.reason||r.clearance_reason||'sell through before freshness/expiry threshold'),upc:r.upc,family:r.family_article_number||r.family_article,nameStock:r.family_name||r.name,oh:r.current_oh??r.effective_oh,uom:r.current_oh_uom||r.effective_oh_uom||r.selling_uom,rank:95});
      for(const r of o.rows||[]){
        const q=num(r.suggested_delivery_qty),state=String(r.roster_status||'').toUpperCase();
        if(r.pre_delivery_stockout_risk||r.attention||state==='REVIEW'||q>0)addAction({id:'order-'+(r.family_article||r.family_id),type:'order',tone:r.pre_delivery_stockout_risk?'red':'green',badge:r.pre_delivery_stockout_risk?'STOCKOUT':'ORDER',name:r.family_name||r.family_article,reason:(q===null?'Review order':('Suggested '+fmt(q)+' '+esc(r.suggested_delivery_uom||'')))+(r.freshness_adjustment_applied?' · freshness adjusted':''),family:r.family_article,nameStock:r.family_name,oh:r.effective_oh??r.oh,uom:r.effective_oh_uom||r.oh_uom||'',rank:r.pre_delivery_stockout_risk?85:40});
      }
      V.actions.sort((a,b)=>b.rank-a.rank);renderActions();
    }catch(e){$('#yv2Actions').innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  function renderActions(){
    const filtered=V.actions.filter(a=>V.actionFilter==='all'||a.type===V.actionFilter);
    const rows=filtered.slice(0,40);
    $('#yv2ActionCount').textContent=filtered.length>40?('Top 40 · '+filtered.length+' total'):(filtered.length+' need attention');
    $('#yv2Actions').innerHTML=rows.map((a,i)=>`<article class="yv2-card yv2-action ${esc(a.tone)}"><div class="yv2-topline"><div><div class="yv2-actiontype">${esc(a.type)}</div><div class="yv2-actionname">${esc(a.name)}</div></div><span class="yv2-badge ${esc(a.tone)}">${esc(a.badge)}</span></div><div class="yv2-reason">${a.reason}</div>${a.family?`<button class="yv2-metric edit" style="width:100%;margin-top:9px" data-stock-family="${esc(a.family)}" data-stock-name="${esc(a.nameStock||a.name)}" data-stock-oh="${esc(a.oh??'')}" data-stock-uom="${esc(a.uom||'')}"><div class="yv2-label">Effective OH · tap to enter True Stock</div><div class="yv2-value">${fmt(a.oh)} ${esc(a.uom||'')}</div></button>`:''}<div class="yv2-btnrow"><button class="yv2-btn primary" data-act-open="${i}">Review</button><button class="yv2-btn ignore" data-act-ignore="${i}">Ignore 12H</button></div></article>`).join('')||'<div class="yv2-empty">No actions in this filter.</div>';
    $$('[data-act-open]').forEach(b=>b.onclick=()=>{const a=rows[Number(b.dataset.actOpen)];if(a.upc){go('lookup');$('#yv2Search').value=a.upc;searchLookup(a.upc)}else if(a.type==='order')go('order')});
    $$('[data-act-ignore]').forEach(b=>b.onclick=()=>ignore(rows[Number(b.dataset.actIgnore)].id));
  }
  $$('#yv2ActionTabs [data-af]').forEach(b=>b.onclick=()=>{V.actionFilter=b.dataset.af;$$('#yv2ActionTabs .yv2-tab').forEach(x=>x.classList.toggle('on',x===b));renderActions()});

  async function initOrder(force=false){
    V.orderLoaded=true;$('#yv2OrderRows').innerHTML='<div class="yv2-loading">Loading observed delivery roster…</div>';
    try{await orderingDefaults();$('#yv2Delivery').value=V.delivery||'';$('#yv2NextDelivery').value=V.nextDelivery||'';if(V.orderMode==='promotion')loadPromotion();else loadRegularOrder()}catch(e){$('#yv2OrderRows').innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  async function loadRegularOrder(){
    V.orderMode='regular';if(!V.delivery||!V.nextDelivery)return;
    $('#yv2OrderStatus').textContent='Calculating '+V.delivery+' → '+V.nextDelivery;
    $('#yv2OrderRows').innerHTML='<div class="yv2-loading">Using receipts, Effective OH, sales and freshness…</div>';
    try{
      const d=await api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(V.delivery)+'&next_delivery_date='+encodeURIComponent(V.nextDelivery),{timeoutMs:35000});
      V.orderRows=(d.rows||[]).filter(r=>String(r.roster_status||'').toUpperCase()!=='ZERO_ORDER'||num(r.suggested_delivery_qty)>0).sort((a,b)=>(num(b.suggested_delivery_qty)||0)-(num(a.suggested_delivery_qty)||0));
      $('#yv2OrderStatus').textContent=(d.selected_delivery_weekday||'Delivery')+' · '+V.orderRows.length+' suggestions';
      $('#yv2OrderRows').innerHTML=V.orderRows.map((r,i)=>{
        const hist=Array.isArray(r.historical_receiving_articles)?r.historical_receiving_articles.slice(0,3):[];
        return `<article class="yv2-card"><div class="yv2-topline"><div><div class="yv2-familyname">${esc(r.family_name||r.family_article)}</div><div class="yv2-meta">Family ${esc(r.family_article||'—')} · ${fmt(r.delivery_day_observed_count,0)} observed delivery days</div></div><span class="yv2-badge ${r.pre_delivery_stockout_risk?'red':r.freshness_adjustment_applied?'amber':'green'}">${r.pre_delivery_stockout_risk?'STOCKOUT':r.freshness_adjustment_applied?'FRESHNESS':'ORDER'}</span></div><div class="yv2-grid2"><button class="yv2-metric edit" data-stock-family="${esc(r.family_article||'')}" data-stock-name="${esc(r.family_name||'')}" data-stock-oh="${esc(r.effective_oh??r.oh??'')}" data-stock-uom="${esc(r.effective_oh_uom||r.oh_uom||'')}"><div class="yv2-label">Effective OH · tap</div><div class="yv2-value">${fmt(r.effective_oh??r.oh)} ${esc(r.effective_oh_uom||r.oh_uom||'')}</div></button><div class="yv2-metric"><div class="yv2-label">DOS / DOH</div><div class="yv2-value">${fmt(r?.details?.dos)} / ${fmt(r?.details?.doh)}</div><div class="yv2-minor">${r.freshness_adjustment_applied?'Freshness adjusted':'Current coverage'}</div></div></div><div class="yv2-orderqty"><div class="yv2-label">Suggested order</div><b>${fmt(r.suggested_delivery_qty)} ${esc(r.suggested_delivery_uom||'')}</b><div class="yv2-minor">${esc(r.ordering_frequency||'')} · coverage through ${esc(V.nextDelivery)}</div></div>${hist.length?'<div class="yv2-recv"><b>Receiving Articles</b><br>'+hist.map(h=>esc(h.article_number||'—')+(h.article_name?' · '+esc(h.article_name):'')+(h.pack_size?' · '+esc(h.pack_size):'')).join('<br>')+'</div>':''}<div class="yv2-btnrow"><button class="yv2-btn ignore" data-order-ignore="${i}">Ignore 12H</button></div></article>`;
      }).join('')||'<div class="yv2-empty">No positive order suggestions.</div>';
      bindStockButtons($('#yv2OrderRows'));$$('[data-order-ignore]').forEach(b=>b.onclick=()=>{const r=V.orderRows[Number(b.dataset.orderIgnore)];localStorage.setItem('yv2-order-ignore-'+String(r.family_article||r.family_id),String(Date.now()+12*3600*1000));b.closest('.yv2-card').remove();toast('Hidden for 12 hours')});
    }catch(e){$('#yv2OrderRows').innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  $('#yv2Delivery').onchange=e=>{V.delivery=e.target.value;if(!V.nextDelivery||V.nextDelivery<=V.delivery){V.nextDelivery=plus(V.delivery,7);$('#yv2NextDelivery').value=V.nextDelivery}V.orderMode==='promotion'?loadPromotion():loadRegularOrder()};
  $('#yv2NextDelivery').onchange=e=>{V.nextDelivery=e.target.value;V.orderMode==='promotion'?loadPromotion():loadRegularOrder()};
  $$('[data-om]').forEach(b=>b.onclick=()=>{V.orderMode=b.dataset.om;$$('[data-om]').forEach(x=>x.classList.toggle('on',x===b));V.orderMode==='promotion'?loadPromotion():loadRegularOrder()});

  async function loadPromoDetail(){
    if(!V.promoListId){V.promoListDetail=null;return null}
    const d=await api('/v1/yipman/promotion-lists/'+encodeURIComponent(V.promoListId),{timeoutMs:12000});
    V.promoListDetail=d;return d;
  }
  async function loadPromotion(){
    $('#yv2OrderRows').innerHTML='<div class="yv2-loading">Loading promotion lists…</div>';
    try{
      const d=await api('/v1/yipman/promotion-lists?limit=30',{timeoutMs:12000}),rows=d.rows||[];
      if(!V.promoListId&&rows.length)V.promoListId=rows[0].list_id;
      $('#yv2OrderRows').innerHTML=`<div class="yv2-card"><div class="yv2-topline"><div><div class="yv2-familyname">Promotion Ordering</div><div class="yv2-meta">Search and add multiple items · manual items can be removed</div></div><button class="yv2-btn primary" id="yv2AddPromo" style="flex:0 0 auto">+ Add Items</button></div><select class="yv2-select" id="yv2PromoList"><option value="">Choose promotion list…</option>${rows.map(x=>'<option value="'+esc(x.list_id)+'">'+esc(x.list_name)+' · '+fmt(x.ready_count,0)+' ready</option>').join('')}</select><div id="yv2PromoCalc" style="margin-top:9px"></div></div>`;
      $('#yv2PromoList').value=String(V.promoListId||'');
      $('#yv2PromoList').addEventListener('change',async e=>{V.promoListId=e.target.value?Number(e.target.value):null;V.promoListDetail=null;if(V.promoListId){await loadPromoDetail();await calcPromotion()}else $('#yv2PromoCalc').innerHTML='<div class="yv2-empty">Create or choose a promotion list.</div>'});
      if(V.promoListId){await loadPromoDetail();await calcPromotion()}else $('#yv2PromoCalc').innerHTML='<div class="yv2-empty">Create or choose a promotion list.</div>';
    }catch(e){$('#yv2OrderRows').innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  async function calcPromotion(){
    const box=$('#yv2PromoCalc');if(!box||!V.promoListId)return;box.innerHTML='<div class="yv2-loading">Calculating promotion order…</div>';
    try{
      const detail=V.promoListDetail||await loadPromoDetail();
      const d=await api('/v1/yipman/promotion-ordering/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({list_id:Number(V.promoListId),delivery_date:V.delivery,next_delivery_date:V.nextDelivery,temporary_oh_overrides:[]}),timeoutMs:45000});
      const manual=Boolean(detail?.manual_item_removal_allowed)||String(detail?.source_filename||'').toUpperCase()==='MANUAL_SEARCH_ENTRY';
      const review=(detail?.items||[]).filter(x=>x.mapping_status!=='READY');
      const reviewHtml=review.map(x=>`<div class="yv2-selected"><button type="button" data-promo-remove-item="${esc(x.item_id||'')}">Remove</button><b>${esc(x.raw_description||x.raw_item_code||'Promotion item')}</b><div class="yv2-meta">${esc(x.mapping_status||'REVIEW')} · ${esc(x.validation_error||'Needs mapping review')}</div></div>`).join('');
      const rowsHtml=(d.rows||[]).map(r=>{
        const p=r.promotion_list_item||{},family=r.family_article_number||r.family_article||p.family_article_number||'',name=r.family_article_name||p.family_name||r.name||r.description||r.upc||'Promotion item';
        const oh=r.current_effective_oh??r.effective_oh_raw??r.effective_oh??r.current_oh,uom=r.current_effective_oh_uom||r.effective_oh_uom||r.oh_uom||r.uom||r.selling_uom||'';
        const remove=manual&&p.item_id?`<button class="yv2-btn ignore" type="button" data-promo-remove-item="${esc(p.item_id)}">Remove from promotion</button>`:'';
        return `<div class="yv2-card" style="margin-bottom:8px"><div class="yv2-topline"><div><div class="yv2-actionname">${esc(name)}</div><div class="yv2-meta">UPC ${esc(r.upc||p.upc||p.raw_item_code||'—')} · Family ${esc(family||'—')}</div></div><span class="yv2-badge ${r.freshness_adjustment_applied?'amber':'green'}">${r.freshness_adjustment_applied?'FRESHNESS':'PROMO'}</span></div><div class="yv2-grid2"><button class="yv2-metric edit" data-stock-family="${esc(family)}" data-stock-name="${esc(name)}" data-stock-oh="${esc(oh??'')}" data-stock-uom="${esc(uom)}"><div class="yv2-label">Effective OH · tap to enter True Stock</div><div class="yv2-value">${fmt(oh)} ${esc(uom)}</div></button><div class="yv2-metric"><div class="yv2-label">Promo price</div><div class="yv2-value">${money(p.promotion_price??r.promotion_price)}</div></div></div><div class="yv2-orderqty"><div class="yv2-label">Suggested promo order</div><b>${fmt(r.suggested_order_qty??r.suggested_delivery_qty)} ${esc(r.suggested_order_uom||r.suggested_delivery_uom||r.uom||r.selling_uom||'')}</b></div>${remove?'<div class="yv2-btnrow">'+remove+'</div>':''}</div>`;
      }).join('');
      box.innerHTML=(manual&&reviewHtml?'<div class="yv2-meta" style="margin:5px 0 7px"><b>Manual promotion items needing review</b></div>'+reviewHtml:'')+rowsHtml||'<div class="yv2-empty">No calculable promotion items.</div>';
    }catch(e){box.innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  async function removePersistedPromoItem(itemId,btn){
    const id=Number(itemId);if(!V.promoListId||!Number.isFinite(id))return toast('Promotion item unavailable');
    if(btn){btn.disabled=true;btn.textContent='Removing…'}
    try{
      V.promoListDetail=await api('/v1/yipman/promotion-lists/'+encodeURIComponent(V.promoListId)+'/items/'+encodeURIComponent(id),{method:'DELETE',timeoutMs:12000});
      toast('Promotion item removed');
      await loadPromotion();
    }catch(e){toast(e.message||'Could not remove promotion item');if(btn){btn.disabled=false;btn.textContent='Remove from promotion'}}
  }
  function openPromoBuilder(){
    V.promoSelected=new Map();
    modal(`<h3>Manual Promotion</h3><p>Search one or multiple UPC / Article / item names. Tap a result to add it; every selected item can be removed before saving.</p><form class="yv2-promosearch" id="yv2PromoSearchForm"><input id="yv2PromoSearch" placeholder="UPC / article / English / 中文" enterkeyhint="search" autocomplete="off"><button type="submit" class="yv2-btn primary" id="yv2PromoSearchBtn" style="flex:0 0 auto">Search</button></form><div id="yv2PromoResults"></div><div id="yv2PromoSelected"></div><div class="yv2-formgrid"><label>START<input type="date" id="yv2PromoStart" value="${esc(V.delivery||iso(new Date()))}"></label><label>END<input type="date" id="yv2PromoEnd" value="${esc(plus(V.delivery||iso(new Date()),2))}"></label><label>DELIVERY<input type="date" id="yv2PromoDelivery" value="${esc(V.delivery||'')}"></label><label>NEXT DELIVERY<input type="date" id="yv2PromoNext" value="${esc(V.nextDelivery||'')}"></label></div><input class="yv2-input" id="yv2PromoName" style="font-size:14px" value="Manual Promotion ${esc(V.delivery||'')}"><div class="yv2-btnrow"><button class="yv2-btn" id="yv2PromoCancel">Cancel</button><button class="yv2-btn primary" id="yv2PromoSave">Save Promotion</button></div>`);
    setTimeout(()=>$('#yv2PromoSearch')?.focus(),60);
  }
  async function runPromoSearch(){
    const q=$('#yv2PromoSearch').value.trim(),box=$('#yv2PromoResults');if(q.length<2)return toast('Enter at least 2 characters');box.innerHTML='<div class="yv2-loading">Searching…</div>';
    try{const d=await api('/v1/yipman/promotion-item-search?q='+encodeURIComponent(q)+'&limit=16',{timeoutMs:8000});V.promoSearchRows=d.results||[];box.innerHTML=V.promoSearchRows.slice(0,12).map((r,i)=>`<button type="button" class="yv2-promoresult" data-promo-result="${i}"><b>${esc(r.name||r.number||'Item')}</b><span>${esc(r.result_type||'ITEM')} ${esc(r.number||'—')} · Family ${esc(r.family_article_number||(String(r.result_type||'').toUpperCase()==='FAMILY'?r.number:'')||'—')} · Current ${money(r.current_price)} · TAP TO ADD</span></button>`).join('')||'<div class="yv2-empty">No matching item.</div>'}catch(e){box.innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  function selectPromo(r){if(!r)return;const family=String(r.family_article_number||(String(r.result_type||'').toUpperCase()==='FAMILY'?r.number:'')||'');const key=family||String(r.number||'');if(!key)return toast('Item mapping unavailable');V.promoSelected.set(key,{...r,familyKey:family,price:r.current_price});renderPromoSelected();toast('Promotion item added')}
  function renderPromoSelected(){const box=$('#yv2PromoSelected');if(!box)return;box.innerHTML=[...V.promoSelected.entries()].map(([k,r])=>`<div class="yv2-selected"><button type="button" data-promo-remove="${esc(k)}">Remove</button><b>${esc(r.name||r.number)}</b><div class="yv2-meta">Family ${esc(r.familyKey||'—')} · selected ${esc(r.number||'—')}</div><input class="yv2-input" style="font-size:16px" data-promo-price="${esc(k)}" value="${esc(r.price??'')}" placeholder="SALE price"></div>`).join('')||'<div class="yv2-meta" style="margin-top:8px">No promotion items selected yet.</div>'}
  async function savePromo(){
    const selected=[...V.promoSelected.entries()];if(!selected.length)return toast('Select at least one item');
    const start=$('#yv2PromoStart').value,end=$('#yv2PromoEnd').value,delivery=$('#yv2PromoDelivery').value,next=$('#yv2PromoNext').value;if(!start||!end||!delivery||!next)return toast('Complete all dates');if(end<start||next<=delivery)return toast('Check promotion / delivery dates');
    const items=selected.map(([k,r])=>{const price=Number(root.querySelector('[data-promo-price="'+CSS.escape(k)+'"]').value);return {upc:String(r.number||r.familyKey||''),description:r.name||'',promotion_type:'CUSTOM',promotion_start_date:start,promotion_end_date:end,promotion_price:price}});
    if(items.some(x=>!Number.isFinite(x.promotion_price)||x.promotion_price<=0))return toast('Enter valid SALE price for each item');
    const btn=$('#yv2PromoSave');btn.disabled=true;btn.textContent='Saving…';
    try{const d=await api('/v1/yipman/promotion-lists',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({list_name:$('#yv2PromoName').value.trim()||('Manual Promotion '+start),source_filename:'MANUAL_SEARCH_ENTRY',items}),timeoutMs:30000});V.promoListId=d.list_id;V.promoListDetail=null;V.delivery=delivery;V.nextDelivery=next;closeModal();$('#yv2Delivery').value=delivery;$('#yv2NextDelivery').value=next;toast('Promotion saved');await loadPromotion()}catch(e){toast(e.message);btn.disabled=false;btn.textContent='Save Promotion'}
  }

  async function loadPerformance(days){
    V.performanceLoaded=true;$('#yv2Performance').innerHTML='<div class="yv2-loading">Loading completed-day performance…</div>';
    try{
      if(!V.performanceEnd){const d=await api('/v1/app/v2/performance/latest-date',{timeoutMs:10000});V.performanceEnd=d.latest_completed_supported_sales_date}
      if(!V.performanceEnd)throw new Error('No completed supported sales date');
      const dates=await api('/v1/app/v2/performance/dates?limit=60',{timeoutMs:10000}).catch(()=>({dates:[],rows:[]}));
      const arr=(dates.dates||dates.rows||dates.supported_dates||[]).map(x=>typeof x==='string'?x:(x.date||x.report_date)).filter(Boolean).sort();
      let end=V.performanceEnd,start=end;if(days>1){const elig=arr.filter(x=>x<=end);start=elig[Math.max(0,elig.length-days)]||plus(end,-(days-1))}
      const d=await api('/v1/app/v2/performance/range?start_date='+encodeURIComponent(start)+'&end_date='+encodeURIComponent(end)+'&limit=200',{timeoutMs:30000}),s=d.summary||{},items=d.items||[];
      const gpPct=num(s.gp_dollars)!==null&&num(s.sales_dollars)>0?num(s.gp_dollars)/num(s.sales_dollars):null;
      $('#yv2PerfStatus').textContent=d.supported_day_count+' completed day'+(d.supported_day_count===1?'':'s')+' · thru '+end;
      $('#yv2Performance').innerHTML=`<div class="yv2-kpis"><div class="yv2-kpi"><span>SALES</span><b>${money(s.sales_dollars)}</b></div><div class="yv2-kpi"><span>GP$</span><b>${money(s.gp_dollars)}</b><small class="yv2-minor">${s.gp_dollars_complete===false?'Incomplete cost coverage':'Historical applicable cost'}</small></div><div class="yv2-kpi"><span>GP%</span><b>${gpPct===null?'—':(gpPct*100).toFixed(1)+'%'}</b><small class="yv2-minor">${s.gp_dollars_complete===false?'Withheld until GP is complete':'Range GP%'}</small></div><div class="yv2-kpi"><span>SOLD ITEMS</span><b>${fmt(s.sold_item_count,0)}</b></div></div><div class="yv2-card" style="margin-top:10px"><div class="yv2-actiontype">Top GP$ contributors</div>${items.slice(0,12).map((r,i)=>`<button class="yv2-listrow" data-perf-upc="${esc(r.upc||'')}" style="width:100%;border-left:0;border-right:0;border-bottom:0;background:transparent;text-align:left"><div><b>${i+1}. ${esc(r.name||r.upc)}</b><span>${fmt(r.sold_quantity)} ${esc(r.qty_uom||'')} · Sales ${money(r.sales_amount)}</span></div><div><b>${money(r.gp_dollars)}</b><span>${r.gp_pct==null?'GP incomplete':(Number(r.gp_pct)*100).toFixed(1)+'% GP'}</span></div></button>`).join('')}</div>`;
      $$('[data-perf-upc]').forEach(b=>b.onclick=()=>{go('lookup');$('#yv2Search').value=b.dataset.perfUpc;searchLookup(b.dataset.perfUpc)});
    }catch(e){$('#yv2Performance').innerHTML='<div class="yv2-empty">'+esc(e.message)+'</div>'}
  }
  $$('#yv2PerfTabs [data-days]').forEach(b=>b.onclick=()=>{$$('#yv2PerfTabs .yv2-tab').forEach(x=>x.classList.toggle('on',x===b));loadPerformance(Number(b.dataset.days))});

  $$('[data-more]').forEach(b=>b.onclick=()=>{const x=b.dataset.more;if(x==='tpr'){go('actions');V.actionFilter='price';renderActions()}else if(x==='data')modal('<h3>Data Status</h3><p>Published through '+esc(V.dataThrough||'—')+'. Detailed batch and QA administration remains on Desktop Back Office.</p><div class="yv2-btnrow"><button class="yv2-btn" id="yv2ModalClose">Close</button></div>'),$('#yv2ModalClose')&&($('#yv2ModalClose').onclick=closeModal);else if(x==='pi'){go('lookup');$('#yv2Search').focus()}else toast('Use Item Lookup for receipt details')});
  $('#yv2Classic').onclick=()=>{const u=new URL(location.href);u.searchParams.set('classic','1');location.href=u.toString()};

  window.__YV2_READY__=true;
  loadHealth().catch(e=>setUiError(e?.message||e));
})();
"""
