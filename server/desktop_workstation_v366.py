from __future__ import annotations

DESKTOP_WORKSTATION_CSS = r"""
@media (min-width: 760px){
  :root{
    --ws-navy:#153351;
    --ws-navy2:#0f2842;
    --ws-blue:#0b72f4;
    --ws-bg:#f3f6fa;
    --ws-line:#dbe5ef;
    --ws-ink:#11263e;
    --ws-muted:#6d7e92;
    --ws-card:#fff;
  }
  html,body{background:var(--ws-bg)!important;color:var(--ws-ink)}
  .shell{grid-template-columns:212px minmax(0,1fr)!important;gap:0!important;padding:0!important;min-height:100vh}
  .workspace{background:var(--ws-bg);padding:0 16px 28px!important;min-width:0}
  .appbar{
    top:0!important;height:100vh!important;border-radius:0!important;
    background:#fff!important;color:var(--ws-ink)!important;border-right:1px solid var(--ws-line);
    box-shadow:none!important;overflow:auto!important
  }
  .appbar .top{padding:18px 15px 10px!important}
  .appbar .mark{display:none!important}
  .appbar .brand strong{font-size:24px!important;color:#102b46!important;letter-spacing:-.7px}
  .appbar .brand strong::first-letter{color:#102b46}
  .appbar .brand small{color:#728297!important;font-size:10px!important}
  .appbar .topstat,.appbar .searchbar{display:none!important}
  .appbar .nav{padding:5px 11px 16px!important;display:grid!important;gap:4px!important}
  .appbar .nav button{
    color:#425b74!important;background:transparent!important;border-radius:10px!important;
    padding:11px 12px!important;font-size:13px!important;font-weight:760!important
  }
  .appbar .nav button.on{background:#e9f3ff!important;color:#0868dc!important;font-weight:900!important}
  .appbar .nav button[data-view="overview"]{display:none!important}
  .desktop-rail-toggle,.desktop-rail-foot{display:none!important}
  .desktop-commandbar{
    position:sticky;top:0;z-index:24;margin:0 -16px 14px!important;
    min-height:58px!important;border-radius:0!important;padding:8px 16px!important;
    background:linear-gradient(100deg,var(--ws-navy2),var(--ws-navy))!important;color:#fff;
    box-shadow:0 3px 12px rgba(16,42,67,.10)
  }
  .desktop-command-copy{display:none!important}
  .desktop-global-search{max-width:680px!important;flex:1!important;background:#fff!important;border-radius:13px!important;border:0!important}
  .desktop-global-search input{color:#142a43!important;font-size:13px!important}
  .desktop-global-search input::placeholder{color:#7a899a!important}
  .desktop-global-search kbd{color:#8795a5!important}
  .desktop-global-search button{background:var(--ws-blue)!important;color:#fff!important}
  .desktop-command-meta{margin-left:auto!important}
  .desktop-store-chip,.desktop-version-chip{border-color:rgba(255,255,255,.2)!important;background:rgba(255,255,255,.08)!important;color:#fff!important}
  .desktop-module-hero{padding:8px 2px 11px!important;min-height:0!important;background:transparent!important;border:0!important;box-shadow:none!important}
  .desktop-module-hero h1{font-size:28px!important;letter-spacing:-.7px!important;margin:0!important}
  .desktop-module-hero p{font-size:11px!important;margin-top:3px!important;color:#6c7f94!important}
  .desktop-module-kicker,.desktop-hero-icon{display:none!important}
  .panel{border-color:var(--ws-line)!important;border-radius:12px!important;box-shadow:0 5px 20px rgba(31,61,91,.045)!important}
  .panelhead{padding:10px 12px!important}
  .toolrow{padding:7px 10px!important}
  .tablewrap{max-height:calc(100vh - 238px);overflow:auto!important}
  .table{font-size:11px!important}
  .table th{position:sticky;top:0;z-index:3;background:#f8fbfe!important;padding:7px 8px!important}
  .table td{padding:7px 8px!important}
  .name{font-size:12px!important}.meta{font-size:9px!important}
  .btn{min-height:32px!important;padding:6px 9px!important;font-size:11px!important}
  .select,.qa-search{font-size:11px!important;padding:6px 8px!important}
  .grid{padding:9px!important;gap:7px!important}
  .kpi{padding:7px 8px!important}
  .kpi b{font-size:15px!important}
  .v366-ws-grid{display:grid;grid-template-columns:minmax(0,1.48fr) minmax(385px,.72fr);gap:12px;align-items:start}
  .v366-ws-main{min-width:0}
  .v366-ws-side{min-width:0;position:sticky;top:72px;max-height:calc(100vh - 86px);overflow:auto}
  .v366-side-card{background:#fff;border:1px solid var(--ws-line);border-radius:12px;box-shadow:0 7px 24px rgba(27,55,84,.06);overflow:hidden}
  .v366-side-head{padding:11px 12px;border-bottom:1px solid #e8eef5;display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
  .v366-side-head h3{margin:0;font-size:15px;line-height:1.2}
  .v366-side-head p{margin:3px 0 0;color:var(--ws-muted);font-size:9px;line-height:1.35}
  .v366-side-body{padding:10px}
  .v366-side-empty{padding:28px 12px;text-align:center;color:var(--ws-muted);font-size:11px}
  .v366-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
  .v366-metric{border:1px solid #e1e8f0;border-radius:9px;padding:8px;background:#fff;min-width:0}
  .v366-metric small{display:block;color:#728297;font-size:8px;text-transform:uppercase;font-weight:900;letter-spacing:.03em}
  .v366-metric b{display:block;font-size:15px;margin-top:2px;overflow-wrap:anywhere}
  .v366-metric span{display:block;color:#78889a;font-size:8px;margin-top:2px}
  .v366-section{margin-top:9px;border:1px solid #e2e9f0;border-radius:9px;background:#fff;overflow:hidden}
  .v366-section h4{font-size:10px;margin:0;padding:8px 9px;border-bottom:1px solid #edf2f6;background:#fbfdff}
  .v366-kv{display:grid;grid-template-columns:1fr auto;gap:5px 9px;padding:8px 9px;font-size:9px}
  .v366-kv span:nth-child(odd){color:#748398}
  .v366-kv span:nth-child(even){font-weight:850;text-align:right}
  .v366-mini-table{width:100%;border-collapse:collapse;font-size:9px}
  .v366-mini-table th,.v366-mini-table td{padding:6px 7px;border-bottom:1px solid #edf2f6;text-align:left}
  .v366-mini-table th{font-size:8px;text-transform:uppercase;color:#748398;background:#fbfdff}
  .v366-price-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:8px}
  .v366-price{border:1px solid #e1e8f0;border-radius:8px;padding:7px}
  .v366-price small{font-size:7px;color:#748398;text-transform:uppercase;font-weight:900}
  .v366-price b{display:block;font-size:14px;margin-top:2px}
  .v366-note{padding:8px 9px;border-radius:8px;font-size:9px;line-height:1.45;background:#eef6ff;color:#315f92;border:1px solid #d5e8ff}
  .v366-note.warn{background:#fff6df;color:#836126;border-color:#f2ddb0}
  .v366-note.good{background:#ecfaf2;color:#347553;border-color:#ccebd8}
  .v366-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
  .v366-action{border:1px solid #cbd8e5;background:#fff;border-radius:8px;padding:7px 9px;font-size:9px;font-weight:850;color:#34506e}
  .v366-action.primary{background:var(--ws-blue);border-color:var(--ws-blue);color:#fff}
  .v366-trend{display:flex;align-items:end;gap:3px;height:86px;padding:8px;border-bottom:1px solid #edf2f6}
  .v366-bar{flex:1;min-width:3px;background:#78b9fb;border-radius:3px 3px 0 0}
  .v366-order-controls{margin-bottom:10px;background:#fff;border:1px solid var(--ws-line);border-radius:12px;padding:9px;box-shadow:0 4px 16px rgba(25,55,85,.035)}
  .v366-order-top{display:grid;grid-template-columns:1fr 1fr 1.35fr auto;gap:7px;align-items:end}
  .v366-field label{display:block;font-size:8px;text-transform:uppercase;color:#728196;font-weight:900;margin-bottom:4px}
  .v366-field input,.v366-field select{width:100%;height:34px;border:1px solid #dce5ee;border-radius:8px;padding:0 8px;background:#fff}
  .v366-calendar{display:grid;grid-template-columns:repeat(14,1fr);gap:3px;margin-top:7px}
  .v366-day{border:1px solid #e0e7ef;border-radius:7px;padding:5px 2px;text-align:center;font-size:8px;background:#fff}
  .v366-day b{display:block;font-size:10px}.v366-day.obs{background:#ebf9f1;border-color:#bce4cb}.v366-day.sel{background:#e8f3ff;border-color:#91c3ff;color:#0867d7}.v366-day.next{background:#f1edff;border-color:#b9aaf7;color:#5e43c8}
  .v366-secondary-panel{margin-top:10px}
  .v366-live-row{cursor:pointer}
  .v366-live-row:hover td{background:#f2f7fd!important}
  .v366-selected td{background:#eaf3ff!important}
  .v366-source-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
  .v366-source{border:1px solid #e1e8f0;border-radius:8px;padding:7px}
  .v366-source small{display:block;color:#758497;font-size:7px;text-transform:uppercase}
  .v366-source b{font-size:13px}
  .v366-copy-drawer .detailgrid{grid-template-columns:repeat(2,minmax(0,1fr))}
  body[data-desktop-view="quick"] #desktopInventoryHero{display:none!important}
  body[data-desktop-view="inventory"] #desktopQuickHero{display:none!important}
  @media(max-width:1200px){
    .shell{grid-template-columns:74px minmax(0,1fr)!important}
    .appbar .brand strong{font-size:15px!important}.appbar .brand small,.navlabel{display:none!important}
    .appbar .nav button{justify-content:center;text-align:center!important}
    .v366-ws-grid{grid-template-columns:1fr}
    .v366-ws-side{position:relative;top:auto;max-height:none}
  }
}
"""

DESKTOP_WORKSTATION_JS = r"""
(function(){
  if(window.matchMedia('(max-width:759px)').matches)return;
  var cache={pricing:null,pricingAt:0,ordering:{},promotionLists:null};
  var activeAnalysis={view:null,key:null};

  function q(s,r){return (r||document).querySelector(s)}
  function qa(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function n(v,d){var x=Number(v);return Number.isFinite(x)?x:(d==null?0:d)}
  function fmt(v,d){if(v===null||v===undefined||v==='')return '—';var x=Number(v);return Number.isFinite(x)?x.toLocaleString(undefined,{maximumFractionDigits:d==null?1:d}):esc(v)}
  function money(v){if(v===null||v===undefined||v==='')return '—';var x=Number(v);return Number.isFinite(x)?'$'+x.toFixed(2):esc(v)}
  function pct(v){if(v===null||v===undefined||v==='')return '—';var x=Number(v);if(!Number.isFinite(x))return esc(v);if(Math.abs(x)<=1.5)x*=100;return x.toFixed(1)+'%'}
  async function getJson(url,opts){var r=await fetch(url,Object.assign({cache:'no-store'},opts||{}));var raw=await r.text(),d={};if(raw){try{d=JSON.parse(raw)}catch(e){d={detail:raw}}}if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:'HTTP '+r.status);return d}
  function metric(label,value,sub){return '<div class="v366-metric"><small>'+esc(label)+'</small><b>'+esc(value)+'</b>'+(sub?'<span>'+esc(sub)+'</span>':'')+'</div>'}
  function kv(rows){return '<div class="v366-kv">'+rows.map(function(x){return '<span>'+esc(x[0])+'</span><span>'+esc(x[1])+'</span>'}).join('')+'</div>'}
  function side(view){return q('#v366-side-'+view)}
  function setSide(view,title,sub,html){
    var s=side(view);if(!s)return;
    q('.v366-side-title',s).textContent=title||'Analysis Workspace';
    q('.v366-side-sub',s).textContent=sub||'';
    q('.v366-side-body',s).innerHTML=html;
  }
  function loading(view,title,sub){setSide(view,title,sub,'<div class="v366-side-empty">Loading live analysis…</div>')}
  function moduleName(id){return ({inventory:'quick',ordering:'ordering',pricing:'pricing',sales:'sales',database:'database'})[id]||id}
  function ensureWorkstation(id,title,sub){
    var view=q('#'+id);if(!view||q(':scope > .v366-ws-grid',view))return;
    var grid=document.createElement('div');grid.className='v366-ws-grid';
    var main=document.createElement('div');main.className='v366-ws-main';
    var sideBox=document.createElement('aside');sideBox.className='v366-ws-side';sideBox.id='v366-side-'+moduleName(id);
    var children=Array.prototype.slice.call(view.children);
    children.forEach(function(x){main.appendChild(x)});
    sideBox.innerHTML='<div class="v366-side-card"><div class="v366-side-head"><div><h3 class="v366-side-title">'+esc(title)+'</h3><p class="v366-side-sub">'+esc(sub)+'</p></div><span class="pill blue">LIVE</span></div><div class="v366-side-body"><div class="v366-side-empty">Select a row to open the desktop analysis workspace.</div></div></div>';
    grid.appendChild(main);grid.appendChild(sideBox);view.appendChild(grid);
  }
  function navSetup(){
    var brand=q('.appbar .brand strong');if(brand)brand.textContent='Yipman';
    var small=q('.appbar .brand small');if(small)small.textContent='FULL MYSQL · Store #1032';
    var nav=q('.appbar .nav');if(!nav)return;
    var order=['quick','ordering','pricing','sales','inventory','database'];
    var labels={quick:'Quick Check',ordering:'Ordering',pricing:'Price Suggestions',sales:'Performance',inventory:'PI / True Stock',database:'Data Center'};
    order.forEach(function(v){
      var b=q('.navbtn[data-view="'+v+'"]',nav);if(!b)return;
      var l=q('.navlabel',b);if(l)l.textContent=labels[v];
      nav.appendChild(b);
    });
    var ov=q('.navbtn[data-view="overview"]',nav);if(ov)ov.style.display='none';
  }
  function makeCalendar(delivery,next){
    var start=new Date();start.setDate(start.getDate()-7);
    var html='<div class="v366-calendar">';
    for(var i=0;i<14;i++){
      var d=new Date(start);d.setDate(start.getDate()+i);
      var iso=d.toISOString().slice(0,10),wd=d.toLocaleDateString(undefined,{weekday:'short'}).toUpperCase();
      var cls='v366-day';
      if([2,5].indexOf(d.getDay())>=0)cls+=' obs';
      if(iso===delivery)cls+=' sel';
      if(iso===next)cls+=' next';
      html+='<div class="'+cls+'"><span>'+wd+'</span><b>'+d.getDate()+'</b></div>';
    }
    return html+'</div>';
  }
  function addOrderingControls(){
    var view=q('#ordering .v366-ws-main');if(!view||q('#v366OrderControls',view))return;
    var hero=q('.desktop-ordering-hero',view);
    var box=document.createElement('div');box.id='v366OrderControls';box.className='v366-order-controls';
    var today=new Date(),delivery=new Date(today),next=new Date(today);
    delivery.setDate(today.getDate()+((5-today.getDay()+7)%7||7));next.setDate(delivery.getDate()+4);
    var di=delivery.toISOString().slice(0,10),ni=next.toISOString().slice(0,10);
    box.innerHTML='<div class="v366-order-top">'+
      '<div class="v366-field"><label>Delivery Date</label><input id="v366Delivery" type="date" value="'+di+'"></div>'+
      '<div class="v366-field"><label>Next Delivery Date</label><input id="v366NextDelivery" type="date" value="'+ni+'"></div>'+
      '<div class="v366-field"><label>Mode</label><select id="v366OrderMode"><option value="regular">Regular Order</option><option value="promotion">Promotion Order</option><option value="history">Delivery History</option></select></div>'+
      '<button id="v366AnalyzeOrder" class="btn primary" type="button">Analyze</button></div>'+
      '<div id="v366Calendar">'+makeCalendar(di,ni)+'</div>';
    if(hero&&hero.nextSibling)view.insertBefore(box,hero.nextSibling);else view.insertBefore(box,view.firstChild);
    q('#v366AnalyzeOrder').onclick=runOrderWorkspace;
    q('#v366Delivery').onchange=function(){q('#v366Calendar').innerHTML=makeCalendar(q('#v366Delivery').value,q('#v366NextDelivery').value)};
    q('#v366NextDelivery').onchange=function(){q('#v366Calendar').innerHTML=makeCalendar(q('#v366Delivery').value,q('#v366NextDelivery').value)};
    q('#v366OrderMode').onchange=function(){runOrderWorkspace()};
  }
  async function getPricing(){
    if(cache.pricing&&Date.now()-cache.pricingAt<60000)return cache.pricing;
    cache.pricing=await getJson('/v1/yipman/pricing-review?category=ALL&limit=1000');cache.pricingAt=Date.now();return cache.pricing;
  }
  async function stockFlowFamilyAnalysis(family){
    if(!family)return;
    loading('quick','Item Intelligence','Family '+family);
    try{
      var d=await getJson('/v1/backoffice/inventory?category=ALL&limit=80&lightweight=false&q='+encodeURIComponent(family));
      var rows=(d.rows||[]).filter(function(x){return String(x.family_article||'')===String(family)});
      if(!rows.length)rows=d.rows||[];
      if(!rows.length)throw new Error('Family not found');
      rows.sort(function(a,b){return n(b.qty_7d)-n(a.qty_7d)});
      var best=rows.find(function(x){return x.upc})||rows[0];
      if(!best||!best.upc)throw new Error('No selling UPC found for this family');
      await quickAnalysis(String(best.upc));
    }catch(e){
      setSide('quick','Item Intelligence','Family '+family,'<div class="v366-note warn">'+esc(e.message||e)+'</div>');
    }
  }
  async function quickAnalysis(upc){
    activeAnalysis={view:'quick',key:upc};loading('quick','Item Intelligence','UPC '+upc);
    try{
      var d=await getJson('/v1/backoffice/inventory?category=ALL&limit=60&lightweight=false&q='+encodeURIComponent(upc));
      var r=(d.rows||[]).find(function(x){return String(x.upc||'')===String(upc)})||(d.rows||[])[0];if(!r)throw new Error('UPC not found');
      var family=String(r.family_article||'');
      var fd=family?await getJson('/v1/backoffice/inventory?category=ALL&limit=80&lightweight=false&q='+encodeURIComponent(family)):d;
      var related=(fd.rows||[]).filter(function(x){return !family||String(x.family_article||'')===family}).sort(function(a,b){return n(b.qty_7d)-n(a.qty_7d)});
      var pr=null;try{var p=await getPricing();pr=(p.rows||[]).find(function(x){return String(x.upc||'')===String(upc)})||null}catch(e){}
      var rec=Array.isArray(r.family_receipt_history)?r.family_receipt_history:[];
      var prices=[
        ['Current',money(r.price),(r.price_type||'—')+' · '+(r.price_source||'—')],
        ['Tested',money(r.sweet_spot_price),r.sweet_spot_price==null?'Not established':'strongest proved sweet spot'],
        ['Testing',money(pr&&pr.testing_price),pr&&pr.testing_price!=null?'controlled test':'none active']
      ];
      var html='<div class="v366-metrics">'+
        metric('Family 7D MVT',fmt(r.family_group_movement_7d)+' '+(r.family_group_movement_uom||''),fmt(r.family_group_avg_qty_day)+' / day')+
        metric('UPC 7D Qty',fmt(r.qty_7d)+' '+(r.selling_uom||''),fmt(r.velocity_7d)+' / day')+
        metric('Effective OH',fmt(r.family_oh)+' '+(r.family_oh_uom||''),'DOS '+fmt(r.dos))+
      '</div>'+
      '<div class="v366-section"><h4>Current / Tested / Testing Price</h4><div class="v366-price-strip">'+prices.map(function(x){return '<div class="v366-price"><small>'+esc(x[0])+'</small><b>'+esc(x[1])+'</b><span class="meta">'+esc(x[2])+'</span></div>'}).join('')+'</div>'+
        kv([['Company A',money(r.company_price_a)],['Company B',money(r.company_price_b)],['Company C',money(r.company_price_c)],['Current Cost',money(r.cost)+(r.cost_uom?' / '+r.cost_uom:'')],['GP%',pct(r.gp_pct)],['Readiness',r.readiness||'—']])+
      '</div>'+
      '<div class="v366-section"><h4>Recent Family Receipts</h4>'+
        (rec.length?'<table class="v366-mini-table"><thead><tr><th>Date</th><th>Qty</th><th>MVT</th><th>Source</th></tr></thead><tbody>'+rec.slice(0,4).map(function(x){return '<tr><td>'+esc(x.receipt_date||x.date||'—')+'</td><td><b>'+fmt(x.receipt_qty!=null?x.receipt_qty:x.quantity)+' '+esc(x.receipt_uom||x.uom||'')+'</b></td><td>'+esc(x.receipt_movement_type||x.movement_type||'—')+'</td><td>'+esc(x.receipt_source||x.source||'—')+'</td></tr>'}).join('')+'</tbody></table>':'<div class="v366-side-empty">No recent receipt detail in current row.</div>')+
      '</div>'+
      '<div class="v366-section"><h4>Related Selling UPCs</h4><table class="v366-mini-table"><thead><tr><th>UPC</th><th>7D Qty</th><th>Price</th><th>OH</th></tr></thead><tbody>'+related.slice(0,8).map(function(x){return '<tr><td><b>'+esc(x.upc||'—')+'</b><div class="meta">'+esc(x.name||'')+'</div></td><td>'+fmt(x.qty_7d)+' '+esc(x.selling_uom||'')+'</td><td>'+money(x.price)+'</td><td>'+fmt(x.family_oh)+' '+esc(x.family_oh_uom||'')+'</td></tr>'}).join('')+'</tbody></table></div>'+
      '<div id="v366QuickTrend" class="v366-section"><h4>14-Day GP$ + Avg Price</h4><div class="v366-side-empty">Loading trend…</div></div>'+
      '<div class="v366-actions"><button class="v366-action primary" data-v366-open-original="quick" data-key="'+esc(upc)+'">Open Full Detail</button><button class="v366-action" data-v366-oh="'+esc(family)+'" data-uom="'+esc(r.family_oh_uom||'')+'" data-oh="'+esc(r.family_oh==null?'':r.family_oh)+'" data-name="'+esc(r.family_name||r.name||'')+'">Adjust True Stock</button></div>';
      setSide('quick',String(r.family_article||'')+' · '+(r.family_name||r.name||'Item Intelligence'),'UPC '+upc+' · '+(r.category||''),html);
      wireSideActions();
      try{
        var t=await getJson('/v1/app/v2/upc/'+encodeURIComponent(upc)+'/price?trend_supported_days=14');
        var rows=(t.price_vs_sales_trend&&t.price_vs_sales_trend.rows)||[];
        var mx=Math.max.apply(null,rows.map(function(x){return Math.max(0,n(x.gp_dollars))}).concat([1]));
        var trend=q('#v366QuickTrend');if(trend)trend.innerHTML='<h4>14-Day GP$ + Avg Price</h4><div class="v366-trend">'+rows.slice(-14).map(function(x){return '<div class="v366-bar" title="'+esc((x.date||'')+' · GP '+money(x.gp_dollars)+' · Avg '+money(x.avg_sold_price))+'" style="height:'+Math.max(4,Math.round(n(x.gp_dollars)/mx*74))+'px"></div>'}).join('')+'</div>'+kv([['Completed data days',String(rows.length)],['Latest avg sold price',rows.length?money(rows[rows.length-1].avg_sold_price):'—'],['Latest GP$',rows.length?money(rows[rows.length-1].gp_dollars):'—']]);
      }catch(e){}
    }catch(e){setSide('quick','Item Intelligence','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
  }
  async function orderAnalysis(family,dataOverride){
    activeAnalysis={view:'ordering',key:family};loading('ordering','Order Forecast','Family '+family);
    try{
      var d=dataOverride||await getJson('/v1/yipman/ordering-review?category=ALL');
      var r=(d.rows||[]).find(function(x){return String(x.family_article||'')===String(family)});if(!r)throw new Error('Family not found in current order review');
      var x=r.details||{},reasons=x.reasons||[],recArts=x.receiving_articles_on_last_receipt||[];
      var html='<div class="v366-metrics">'+
        metric('Effective OH',fmt(r.oh)+' '+(r.oh_uom||''),'family level')+
        metric('28D Movement',fmt(x.qty_28d),fmt(x.velocity_28d||x.velocity_7d)+' / day')+
        metric('Suggested Order',fmt(r.suggested_delivery_qty)+' '+(r.suggested_delivery_uom||''),r.estimate_only?'BEST AVAILABLE':'current')+
      '</div>'+
      '<div class="v366-section"><h4>Coverage / Demand Evidence</h4>'+kv([
        ['Delivery',d.selected_delivery_date||r.delivery_date||'—'],['Next delivery',d.next_delivery_date||r.next_delivery_date||'—'],
        ['Family 7D movement',fmt(x.qty_7d)],['7D velocity',fmt(x.velocity_7d)+'/day'],['DOS',fmt(x.dos)],
        ['Last receipt',r.last_receipt_date||'—'],['Last receipt qty',fmt(r.last_receipt_qty_base)+' '+(r.last_receipt_base_uom||'')],
        ['Observed frequency',r.ordering_frequency||'—']
      ])+'</div>'+
      '<div class="v366-section"><h4>Why This Quantity</h4><div class="v366-side-body">'+(reasons.length?reasons.map(function(z){return '<div class="v366-note '+(String(z.title||'').toLowerCase().indexOf('risk')>=0?'warn':'')+'" style="margin-bottom:6px"><b>'+esc(z.title||'Reason')+'</b><br>'+esc(z.detail||'')+'</div>'}).join(''):'<div class="v366-note">Suggestion uses best available family movement, OH, receipt cadence and selected coverage window.</div>')+'</div></div>'+
      (recArts.length?'<div class="v366-section"><h4>Receiving Articles on Last Receipt</h4><table class="v366-mini-table"><thead><tr><th>Article</th><th>Qty</th><th>Base UOM</th></tr></thead><tbody>'+recArts.map(function(z){return '<tr><td>'+esc(z.article_number||'—')+'</td><td>'+fmt(z.quantity)+'</td><td>'+esc(z.base_uom||'')+'</td></tr>'}).join('')+'</tbody></table></div>':'')+
      '<div class="v366-actions"><button class="v366-action primary" data-v366-open-original="order" data-key="'+esc(family)+'">Open Full Evidence</button></div>';
      setSide('ordering',(r.family_name||'Family')+' · '+family,'Receiving '+(r.receiving_article||'—'),html);wireSideActions();
    }catch(e){setSide('ordering','Order Forecast','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
  }
  async function runOrderWorkspace(){
    var mode=q('#v366OrderMode')?q('#v366OrderMode').value:'regular';
    var delivery=q('#v366Delivery')?q('#v366Delivery').value:'';
    var next=q('#v366NextDelivery')?q('#v366NextDelivery').value:'';
    q('#v366Calendar').innerHTML=makeCalendar(delivery,next);
    if(mode==='history'){
      loading('ordering','Delivery History','PO ↔ GR / receipt evidence');
      try{
        var cal=await getJson('/v1/yipman/ordering-calendar?lookback_days=180');
        var rows=cal.rows||cal.days||cal.receipts||[];
        setSide('ordering','Delivery History','Observed receiving cadence','<div class="v366-section"><h4>Recent Delivery Evidence</h4><table class="v366-mini-table"><thead><tr><th>Date</th><th>Family / Article</th><th>Qty</th><th>Trace</th></tr></thead><tbody>'+rows.slice(0,18).map(function(x){return '<tr><td>'+esc(x.date||x.receipt_date||'—')+'</td><td>'+esc(x.family_article||x.article_number||x.name||'—')+'</td><td>'+fmt(x.quantity||x.receipt_qty)+' '+esc(x.uom||x.base_uom||'')+'</td><td>'+esc(x.gr_number||x.document_number||x.movement_type||'—')+'</td></tr>'}).join('')+'</tbody></table></div>');
      }catch(e){setSide('ordering','Delivery History','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
      return;
    }
    if(mode==='promotion'){
      loading('ordering','Promotion Ordering','Weekly + weekend promotion windows');
      try{
        var lists=await getJson('/v1/yipman/promotion-lists?limit=20'),arr=lists.lists||lists.rows||[];
        var options=arr.map(function(x){return '<option value="'+esc(x.list_id||x.id)+'">'+esc(x.list_name||x.name||('List #'+(x.list_id||x.id)))+'</option>'}).join('');
        setSide('ordering','Promotion Ordering','Promotion-specific forecast + temporary True Stock','<div class="v366-section"><h4>Promotion List</h4><div class="v366-side-body"><select id="v366PromoList" class="select" style="width:100%">'+options+'</select><div class="v366-note" style="margin-top:8px">Weekly Thu→Thu and Weekend Fri→Sun windows remain separate. Temporary True Stock applies only to the promotion calculation.</div><div class="v366-actions"><button id="v366CalcPromo" class="v366-action primary">Calculate Promotion Order</button></div></div></div><div id="v366PromoResult"></div>');
        var btn=q('#v366CalcPromo');if(btn)btn.onclick=calculatePromotion;
      }catch(e){setSide('ordering','Promotion Ordering','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
      return;
    }
    loading('ordering','Regular Order Forecast',delivery+' → '+next);
    try{
      var d=await getJson('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(delivery)+'&next_delivery_date='+encodeURIComponent(next));
      var rows=d.rows||[];
      var top=rows.slice().sort(function(a,b){return n(b.suggested_delivery_qty)-n(a.suggested_delivery_qty)}).slice(0,8);
      var html='<div class="v366-metrics">'+metric('Candidates',String(rows.length),'selected window')+metric('Suggested Total',fmt(rows.reduce(function(s,x){return s+n(x.suggested_delivery_qty)},0)),'mixed UOM · directional')+metric('Data Through',(d.data_health&&d.data_health.data_through)||'—',(d.analysis_status||''))+'</div>'+
        '<div class="v366-section"><h4>Top Suggestions</h4><table class="v366-mini-table"><thead><tr><th>Family</th><th>OH</th><th>Suggested</th></tr></thead><tbody>'+top.map(function(x){return '<tr class="v366-order-pick" data-family="'+esc(x.family_article)+'"><td><b>'+esc(x.family_name||'—')+'</b><div class="meta">'+esc(x.family_article||'')+'</div></td><td>'+fmt(x.oh)+' '+esc(x.oh_uom||'')+'</td><td><b>'+fmt(x.suggested_delivery_qty)+' '+esc(x.suggested_delivery_uom||'')+'</b></td></tr>'}).join('')+'</tbody></table></div><div class="v366-note" style="margin-top:8px">Missing completed dates are ignored rather than zero-filled. Forecast uses the best currently available source history.</div>';
      setSide('ordering','Regular Order Forecast',delivery+' → '+next,html);
      qa('.v366-order-pick').forEach(function(tr){tr.onclick=function(){orderAnalysis(tr.dataset.family,d)}});
    }catch(e){setSide('ordering','Regular Order Forecast','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
  }
  async function calculatePromotion(){
    var id=q('#v366PromoList')&&q('#v366PromoList').value,delivery=q('#v366Delivery').value,next=q('#v366NextDelivery').value,res=q('#v366PromoResult');if(!id||!res)return;
    res.innerHTML='<div class="v366-side-empty">Calculating…</div>';
    try{
      var d=await getJson('/v1/yipman/promotion-ordering/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({list_id:Number(id),delivery_date:delivery,next_delivery_date:next,temporary_oh_overrides:{}})});
      var rows=d.rows||d.items||[];
      res.innerHTML='<div class="v366-section"><h4>Promotion Forecast</h4><table class="v366-mini-table"><thead><tr><th>Family / UPC</th><th>Promo</th><th>Use</th><th>Suggested</th></tr></thead><tbody>'+rows.slice(0,20).map(function(x){return '<tr><td>'+esc(x.family_name||x.item_name||x.upc||'—')+'</td><td>'+esc(x.promotion_type||x.promo_type||'—')+'</td><td>'+fmt(x.predicted_usage||x.forecast_usage)+'</td><td><b>'+fmt(x.suggested_qty||x.suggested_order_qty)+' '+esc(x.uom||x.order_uom||'')+'</b></td></tr>'}).join('')+'</tbody></table></div>';
    }catch(e){res.innerHTML='<div class="v366-note warn">'+esc(e.message||e)+'</div>'}
  }
  async function priceAnalysis(upc){
    activeAnalysis={view:'pricing',key:upc};loading('pricing','Price Analysis','UPC '+upc);
    try{
      var p=await getPricing(),r=(p.rows||[]).find(function(x){return String(x.upc||'')===String(upc)});if(!r)throw new Error('Price suggestion not found');
      var inv=null;try{var d=await getJson('/v1/backoffice/inventory?category=ALL&limit=20&lightweight=false&q='+encodeURIComponent(upc));inv=(d.rows||[]).find(function(x){return String(x.upc||'')===String(upc)})||(d.rows||[])[0]}catch(e){}
      var tested=r.tested_price!=null?r.tested_price:(inv?inv.sweet_spot_price:null),testing=r.testing_price;
      var html='<div class="v366-metrics">'+metric('Current',money(r.current_price),(r.current_price_type||'—')+' · '+(r.current_price_source||'—'))+metric('Tested',money(tested),tested==null?'Not established':'proved sweet spot')+metric('Testing',money(testing),testing==null?'None active':'controlled test · min $0.45 from Current')+'</div>'+
      '<div class="v366-section"><h4>Inventory + Sales Evidence</h4>'+kv([
        ['OH',fmt(r.current_oh)+' '+(r.current_oh_uom||'')],['DOH',fmt(r.doh)],['7D Qty',fmt(r.qty_7d)],['14D Qty',fmt(r.qty_14d)],['28D Qty',fmt(r.qty_28d)],
        ['7D Velocity',fmt(r.velocity_7d)],['Current GP%',pct(r.current_gp_pct_reference)],['Current GP$/day',money(r.current_gp_per_day_7d)],['Candidate GP$/day',money(r.candidate_expected_gp_per_day)]
      ])+'</div>'+
      '<div class="v366-section"><h4>Company Range + 240 / 249</h4>'+kv([
        ['Company A',money(r.company_price_a)],['Company B',money(r.company_price_b)],['Company C',money(r.company_price_c)],
        ['Range',(r.company_range_low!=null?money(r.company_range_low)+' – '+money(r.company_range_high):'No company range')],
        ['240 Main',String(r.related_240_upc||'—')+' · '+money(r.related_240_current_price)],['249 Service',String(r.related_249_upc||'—')+' · '+money(r.related_249_current_price)],
        ['240 = 249',r.related_249_present?(r.price_240_249_equal===false?'MISMATCH':'PASS'):'N/A']
      ])+'</div>'+
      '<div class="v366-section"><h4>Why Suggested</h4><div class="v366-side-body"><div class="v366-note '+(r.priority_240_249_mismatch?'warn':'')+'">'+esc(r.primary_reason_text||r.review_blocker||'Pricing review')+'</div></div></div>'+
      '<div id="v366PriceTrend" class="v366-section"><h4>Price Response History</h4><div class="v366-side-empty">Loading…</div></div>'+
      '<div class="v366-actions"><button class="v366-action primary" data-v366-open-original="price" data-key="'+esc(upc)+'">Open Full Evidence</button></div>';
      setSide('pricing',(r.name||'Price Analysis'),'UPC '+upc,html);wireSideActions();
      try{
        var t=await getJson('/v1/app/v2/upc/'+encodeURIComponent(upc)+'/price?trend_supported_days=14'),rows=(t.price_vs_sales_trend&&t.price_vs_sales_trend.rows)||[];
        var box=q('#v366PriceTrend');if(box)box.innerHTML='<h4>Price Response History</h4><table class="v366-mini-table"><thead><tr><th>Date</th><th>Qty</th><th>Avg Price</th><th>GP$</th></tr></thead><tbody>'+rows.slice(-14).reverse().map(function(x){return '<tr><td>'+esc(x.date||'')+'</td><td>'+fmt(x.sold_quantity)+'</td><td>'+money(x.avg_sold_price)+'</td><td>'+money(x.gp_dollars)+'</td></tr>'}).join('')+'</tbody></table>';
      }catch(e){}
    }catch(e){setSide('pricing','Price Analysis','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
  }
  function performanceAnalysisFromRow(tr){
    var cells=qa('td',tr);if(cells.length<8)return;
    qa('#sellRows tr').forEach(function(x){x.classList.remove('v366-selected')});tr.classList.add('v366-selected');
    var html='<div class="v366-metrics">'+metric('Qty',cells[2].innerText.trim(),'selected range')+metric('Sales',cells[4].innerText.trim(),'range total')+metric('GP$',cells[5].innerText.trim(),'historical cost')+'</div>'+
      '<div class="v366-section"><h4>Selected Item Performance</h4>'+kv([['UPC',cells[1].innerText.trim()],['Velocity',cells[3].innerText.trim()],['GP%',cells[6].innerText.trim()],['Avg Sold Price',cells[7].innerText.trim()]])+'</div>'+
      '<div class="v366-note" style="margin-top:8px">Use the main table sort to compare GP$, velocity, sales, quantity, GP%, or average sold price across the completed canonical date range.</div>';
    setSide('sales',(q('.name',tr)?q('.name',tr).textContent:'Performance Detail'),'Range item analysis',html);
  }
  function performanceSummary(){
    var rows=qa('#sellRows tr').filter(function(x){return q('.name',x)});
    var kpis=qa('#sellKpi .kpi');
    var html='<div class="v366-metrics">'+kpis.slice(0,3).map(function(x){return metric(q('small',x)?q('small',x).textContent:'Metric',q('b',x)?q('b',x).textContent:'—',q('span',x)?q('span',x).textContent:'')}).join('')+'</div>'+
      '<div class="v366-section"><h4>Top Contributors</h4><table class="v366-mini-table"><thead><tr><th>Item</th><th>GP$</th><th>Sales</th></tr></thead><tbody>'+rows.slice(0,8).map(function(tr){var td=qa('td',tr);return '<tr><td>'+esc(q('.name',tr)?q('.name',tr).textContent:'—')+'</td><td>'+esc(td[5]?td[5].innerText.trim():'—')+'</td><td>'+esc(td[4]?td[4].innerText.trim():'—')+'</td></tr>'}).join('')+'</tbody></table></div>'+
      '<div class="v366-note" style="margin-top:8px">Click any performance row for item-level analysis. Desktop keeps the selected item visible while you continue sorting the range.</div>';
    setSide('sales','Management Analysis','Completed canonical dates only',html);
  }
  async function dataAnalysis(){
    loading('database','Data Diagnostics','Live batch + QA + source freshness');
    try{
      var rs=await Promise.allSettled([getJson('/v1/web-upload/active'),getJson('/v1/web-upload/recent?limit=8'),getJson('/v1/backoffice/qa-review?limit=300'),getJson('/v1/backoffice/data-health?days=14')]);
      var active=rs[0].status==='fulfilled'?rs[0].value.active_batch:null,recent=rs[1].status==='fulfilled'?(rs[1].value.batches||[]):[],qaData=rs[2].status==='fulfilled'?rs[2].value:null,dh=rs[3].status==='fulfilled'?rs[3].value:null;
      var issues=qaData?(qaData.issues||[]):[],latest=dh?(dh.latest||{}):{};
      var html='<div class="v366-metrics">'+metric('Current Batch',active?'#'+(active.batch_id||active.id||'—'):'None',active?(active.active_run_status||active.processing_status||'processing'):'idle')+metric('Open QA',String(issues.length),'controlled fixes')+metric('Recent Batches',String(recent.length),'history')+'</div>'+
      '<div class="v366-section"><h4>Source Freshness</h4><div class="v366-side-body"><div class="v366-source-grid">'+['POS','MVT','PRICE','OH','LIVE_FRESH','FROZEN'].map(function(k){var x=latest[k]||{};return '<div class="v366-source"><small>'+esc(k.replace('_',' / '))+'</small><b>'+esc(x.date||'—')+'</b><div class="meta">'+esc(x.file||'')+'</div></div>'}).join('')+'</div></div></div>'+
      '<div class="v366-section"><h4>Top QA Holds</h4><table class="v366-mini-table"><thead><tr><th>Issue</th><th>Entity</th><th>Severity</th></tr></thead><tbody>'+issues.slice(0,10).map(function(x){return '<tr><td>'+esc(x.issue_code||x.issue_summary||'—')+'</td><td>'+esc(x.entity_key||'—')+'</td><td>'+esc(x.severity||'—')+'</td></tr>'}).join('')+'</tbody></table></div>'+
      (active?'<div class="v366-section"><h4>Current Processing</h4>'+kv([['Batch','#'+(active.batch_id||active.id||'—')],['Run','#'+(active.active_pipeline_run_id||'—')],['Status',active.active_run_status||active.processing_status||'—'],['Stage',active.active_phase3_stage||active.active_last_phase3_stage||'—'],['Ready',fmt(active.quick_check_ready_rows)],['Hold',fmt(active.quick_check_hold_rows)],['Open issues',fmt(active.open_issue_total||active.error_count)]])+'</div>':'');
      setSide('database','Data Diagnostics','Live operational health',html);
    }catch(e){setSide('database','Data Diagnostics','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
  }
  async function piAnalysis(family){
    activeAnalysis={view:'quick',key:family};loading('quick','PI / True Stock','Family '+family);
    try{
      var d=await getJson('/v1/backoffice/inventory?category=ALL&limit=80&lightweight=false&q='+encodeURIComponent(family)),rows=d.rows||[],r=rows.find(function(x){return String(x.family_article||'')===String(family)})||rows[0];if(!r)throw new Error('Family not found');
      var rec=Array.isArray(r.family_receipt_history)?r.family_receipt_history:[];
      var html='<div class="v366-metrics">'+metric('Effective OH',fmt(r.family_oh)+' '+(r.family_oh_uom||''),'family')+metric('7D MVT',fmt(r.family_group_movement_7d)+' '+(r.family_group_movement_uom||''),'family movement')+metric('UPC Activity',String(rows.length),'linked rows')+'</div>'+
      '<div class="v366-section"><h4>OH / Evidence</h4>'+kv([['OH status',r.family_oh_status||'—'],['OH as-of',r.family_oh_as_of||'—'],['DOS',fmt(r.dos)],['Readiness',r.readiness||'—'],['Latest receipt',rec[0]?(rec[0].receipt_date||rec[0].date||'—'):'—'],['Latest receipt qty',rec[0]?fmt(rec[0].receipt_qty!=null?rec[0].receipt_qty:rec[0].quantity)+' '+(rec[0].receipt_uom||rec[0].uom||''):'—']])+'</div>'+
      '<div class="v366-note warn" style="margin-top:8px">True Stock is family-level. When submitted below System / Effective OH, the existing workflow creates Pending Dumping for the difference.</div>'+
      '<div class="v366-actions"><button class="v366-action primary" data-v366-oh="'+esc(family)+'" data-uom="'+esc(r.family_oh_uom||'')+'" data-oh="'+esc(r.family_oh==null?'':r.family_oh)+'" data-name="'+esc(r.family_name||r.name||'')+'">Submit True Stock</button></div>';
      setSide('quick',(r.family_name||'PI / True Stock')+' · '+family,'Family stock verification',html);wireSideActions();
    }catch(e){setSide('quick','PI / True Stock','Unable to load','<div class="v366-note warn">'+esc(e.message||e)+'</div>')}
  }
  function wireSideActions(){
    qa('[data-v366-open-original]').forEach(function(b){b.onclick=function(){
      var kind=b.dataset.v366OpenOriginal,key=b.dataset.key;
      if(kind==='quick'){var x=q('.quickdetailbtn[data-upc="'+CSS.escape(key)+'"]');if(x)x.click()}
      if(kind==='order'){var o=q('.orderdetail[data-family="'+CSS.escape(key)+'"]');if(o)o.click()}
      if(kind==='price'){var p=q('.pricedetail[data-upc="'+CSS.escape(key)+'"]');if(p)p.click()}
    }});
    qa('[data-v366-oh]').forEach(function(b){b.onclick=function(){
      var fam=b.dataset.v366Oh;
      var x=q('.ohbtn[data-family="'+CSS.escape(fam)+'"]');
      if(x)x.click();
      else{
        var nav=q('.navbtn[data-view="inventory"]');if(nav)nav.click();
        setTimeout(function(){var y=q('.ohbtn[data-family="'+CSS.escape(fam)+'"]');if(y)y.click()},500)
      }
    }});
  }
  function copyDrawerToWorkspace(){
    var drawer=q('.drawer.on');if(!drawer)return;
    var current=q('.view.on'),id=current?current.id:'';
    var view=moduleName(id),target=side(view);if(!target)return;

    // A live batch monitor is time-sensitive and must never be frozen into the
    // persistent workstation panel. The drawer itself now polls every 3s.
    // Keep the right-side Data Diagnostics panel current instead.
    if(view==='database'&&drawer.dataset.liveBatchId){
      setTimeout(dataAnalysis,0);
      return;
    }

    var title=q('#drawerTitle')?q('#drawerTitle').textContent:'Detail',sub=q('#drawerSub')?q('#drawerSub').textContent:'';
    var body=q('#drawerBody')?q('#drawerBody').cloneNode(true):null;
    if(!body)return;
    qa('[id]',body).forEach(function(x){x.removeAttribute('id')});
    setSide(view,title,sub,'<div class="v366-copy-drawer">'+body.innerHTML+'</div><div class="v366-note" style="margin-top:8px">This persistent desktop copy remains visible after the full interactive drawer is closed.</div>');
  }
  document.addEventListener('fullmysql:stockflow-family',function(e){
    var family=e&&e.detail?e.detail.family:null;
    if(family)setTimeout(function(){stockFlowFamilyAnalysis(family)},0);
  });
  document.addEventListener('fullmysql:active-batch-finished',function(){
    if(document.body.dataset.desktopView==='database')setTimeout(dataAnalysis,80);
  });
  function observe(){
    var drawer=q('.drawer');if(drawer)new MutationObserver(function(){if(drawer.classList.contains('on'))setTimeout(copyDrawerToWorkspace,30)}).observe(drawer,{attributes:true,attributeFilter:['class']});
    var sell=q('#sellRows');if(sell)new MutationObserver(function(){setTimeout(performanceSummary,60)}).observe(sell,{childList:true,subtree:true});
    // Do NOT observe Database Center child mutations here. dataAnalysis() itself
    // updates that subtree; observing childList caused a self-triggering request
    // loop that repeatedly fired active/recent/QA/data-health calls.
  }
  document.addEventListener('click',function(e){
    var sf=e.target.closest('.stockflow-family-btn');if(sf){e.preventDefault();e.stopPropagation();setTimeout(function(){stockFlowFamilyAnalysis(sf.dataset.family)},0);return}
    var qd=e.target.closest('.quickdetailbtn');if(qd){setTimeout(function(){quickAnalysis(qd.dataset.upc)},0);return}
    var od=e.target.closest('.orderdetail');if(od){setTimeout(function(){orderAnalysis(od.dataset.family)},0);return}
    var pd=e.target.closest('.pricedetail');if(pd){setTimeout(function(){priceAnalysis(pd.dataset.upc)},0);return}
    var oh=e.target.closest('.ohbtn');if(oh&&document.body.dataset.desktopView==='inventory'){setTimeout(function(){piAnalysis(oh.dataset.family)},0);return}
    var sr=e.target.closest('#sellRows tr');if(sr&&q('.name',sr)){performanceAnalysisFromRow(sr);return}
    var nav=e.target.closest('.navbtn[data-view]');
    if(nav&&nav.dataset.view==='database')setTimeout(dataAnalysis,250);
  },true);
  function init(){
    navSetup();
    ensureWorkstation('inventory','Item Intelligence','Select a UPC or family to see receipts, pricing, stock and trend together.');
    ensureWorkstation('ordering','Order Forecast','Select a family or choose a delivery window.');
    ensureWorkstation('pricing','Price Analysis','Select a suggestion to see current, tested, testing, company range and GP$/day.');
    ensureWorkstation('sales','Management Analysis','Completed-day performance and item drill-down.');
    ensureWorkstation('database','Data Diagnostics','Batch, source freshness and QA in one workspace.');
    addOrderingControls();
    performanceSummary();
    // Data Diagnostics loads only when Data Center is actually opened.
    observe();
    var hash=(location.hash||'').toLowerCase();
    if(!hash||hash==='#overview'){
      var quick=q('.navbtn[data-view="quick"]');if(quick)setTimeout(function(){quick.click()},0);
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
"""
