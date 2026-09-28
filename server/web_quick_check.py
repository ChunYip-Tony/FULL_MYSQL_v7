from __future__ import annotations

QUICK_CHECK_WEB_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111827">
<title>FULL MYSQL</title>
<style>
:root{color-scheme:light dark;--bg:#f4f6f8;--card:#fff;--text:#111827;--muted:#667085;--line:#e4e7ec;--accent:#175cd3;--bad:#b42318;--warn:#b54708;--ok:#067647;--nav:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--text:#f3f4f6;--muted:#98a2b3;--line:#2c313a;--accent:#84adff;--bad:#f97066;--warn:#fdb022;--ok:#47cd89;--nav:#171a21}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding-bottom:78px}
.wrap{max-width:1020px;margin:0 auto;padding:12px}.top{position:sticky;top:0;z-index:8;background:color-mix(in srgb,var(--bg) 93%,transparent);backdrop-filter:blur(10px);padding:8px 0 10px}
.brand{display:flex;justify-content:space-between;align-items:flex-end;gap:10px}.brand h1{font-size:20px;margin:0}.version{font-size:11px;color:var(--muted)}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.search-row{margin-top:10px}
input,button{font:inherit;border-radius:10px;border:1px solid var(--line);padding:11px 12px;background:var(--card);color:var(--text)}
input{min-width:0;flex:1}button{cursor:pointer;font-weight:700}button.primary{background:var(--accent);color:white;border-color:transparent}button.smallbtn{padding:7px 10px;font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin:10px 0;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}@media(min-width:760px){.grid.metrics{grid-template-columns:repeat(6,minmax(0,1fr))}.list-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.metric{border:1px solid var(--line);border-radius:12px;padding:10px}.metric .k{font-size:11px;color:var(--muted)}.metric .v{font-size:17px;font-weight:780;margin-top:3px;overflow-wrap:anywhere}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 8px;font-size:11px;font-weight:750}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.result,.module-card{cursor:pointer}.result:hover,.module-card:hover{border-color:var(--accent)}.name{font-weight:800}.meta{color:var(--muted);font-size:12px;margin-top:4px}
.section-title{font-size:13px;font-weight:800;margin:2px 0 8px}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:7px 5px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:650}
.scroll{overflow:auto}.hidden{display:none!important}.msg{font-size:12px;color:var(--muted);margin-top:8px}.error{color:var(--bad)}.notice{border-left:3px solid var(--accent);padding-left:10px}.hl{padding:8px 0;border-bottom:1px solid var(--line)}.hl:last-child{border-bottom:0}
.small{font-size:11px;color:var(--muted)}.module-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:12px 0 4px}.module-head h2{font-size:18px;margin:0}
.kv{display:grid;grid-template-columns:1fr auto;gap:5px 10px;font-size:12px;margin-top:8px}.kv .k{color:var(--muted)}.kv .v{text-align:right;font-weight:700}
.flags{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}.flag{font-size:10px;border:1px solid var(--line);border-radius:999px;padding:3px 6px;color:var(--muted)}
.nav{position:fixed;left:0;right:0;bottom:0;z-index:20;background:color-mix(in srgb,var(--nav) 96%,transparent);border-top:1px solid var(--line);backdrop-filter:blur(12px);padding:6px max(8px,env(safe-area-inset-right)) calc(6px + env(safe-area-inset-bottom)) max(8px,env(safe-area-inset-left))}
.nav-inner{max-width:1020px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);gap:5px}.nav button{border:0;background:transparent;padding:7px 3px;border-radius:10px;color:var(--muted);font-size:11px}.nav button.active{background:color-mix(in srgb,var(--accent) 12%,transparent);color:var(--accent)}.nav .ico{display:block;font-size:19px;line-height:22px}
.empty{text-align:center;color:var(--muted);padding:30px 10px}.count{font-size:12px;color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="brand"><h1>FULL MYSQL</h1><div class="version">Web App · v7.0.114</div></div>
    <div class="row" style="justify-content:space-between">
      <div id="globalStatus" class="msg">Public operational app</div>
      <a href="/admin" style="font-size:11px;color:var(--muted);text-decoration:none">Admin</a>
    </div>
  </div>

  <section id="mod-quick" class="module">
    <div class="card">
      <div class="row" style="justify-content:space-between"><div class="section-title" style="margin:0">Operations Overview</div><button id="refreshOverview" class="smallbtn">Refresh</button></div>
      <div id="overviewMetrics" class="grid metrics" style="margin-top:10px"></div>
      <div id="overviewMeta" class="msg">Loading operational status…</div>
    </div>
    <div class="module-head"><h2>🔎 Quick Check</h2></div>
    <div class="row search-row">
      <input id="q" placeholder="Search Article, UPC, or item name" autocomplete="off">
      <button id="search" class="primary">Search</button>
    </div>
    <div id="status" class="msg">Search an item.</div>
    <div id="results"></div>

    <div id="detail" class="hidden">
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <div><div id="itemName" class="name" style="font-size:20px"></div><div id="itemMeta" class="meta"></div></div>
          <div id="itemStatus"></div>
        </div>
        <div id="metrics" class="grid metrics" style="margin-top:12px"></div>
        <div id="highlights" style="margin-top:10px"></div>
      </div>

      <div class="card">
        <div class="section-title">Inventory / True Stock</div>
        <div id="inventorySummary" class="grid"></div>
        <div class="row" style="margin-top:10px">
          <input id="trueStock" inputmode="decimal" placeholder="Enter True Stock">
          <input id="trueStockUom" style="max-width:90px" readonly>
          <button id="submitTrueStock" class="primary">Submit</button>
        </div>
        <div id="trueStockMsg" class="msg"></div>
        <div class="small" style="margin-top:8px">True Stock becomes the active inventory reference until the next accepted OH upload. A lower count automatically creates/updates a Pending Dumping discrepancy.</div>
      </div>

      <div class="card"><div class="section-title">Ordering</div><div id="ordering"></div></div>

      <div class="card">
        <div class="section-title">Family / Related UPCs</div>
        <div id="familyMeta" class="meta"></div>
        <div id="familyArticles" class="small" style="margin-top:6px"></div>
        <div id="receivingArticles" class="small" style="margin-top:4px"></div>
        <div class="scroll" style="margin-top:8px"><table><thead><tr><th>UPC</th><th>Description</th><th>UOM</th><th>Price</th><th>7D</th><th>Status</th></tr></thead><tbody id="relatedRows"></tbody></table></div>
      </div>

      <div class="card"><div class="section-title">Sales Trend · source periods</div><div class="scroll"><table><thead><tr><th>Period</th><th>Type</th><th>Qty</th><th>Sales</th><th>Avg Price</th></tr></thead><tbody id="salesRows"></tbody></table></div></div>
      <div class="card"><div class="section-title">Cost Trend</div><div class="scroll"><table><thead><tr><th>Date</th><th>Source</th><th>Cost</th><th>UOM</th><th>Article</th></tr></thead><tbody id="costRows"></tbody></table></div></div>
    </div>
  </section>

  <section id="mod-order" class="module hidden">
    <div class="module-head"><h2>📦 Ordering</h2><button class="smallbtn" id="refreshOrdering">Refresh</button></div>
    <div class="small">Uses effective OH and current 7D UPC velocity. When a matching ordering policy is configured, the app calculates next order/delivery dates and a suggested order quantity.</div>
    <div id="orderingStatus" class="msg">Open this tab to load.</div>
    <div id="orderingList" class="grid list-grid"></div>
  </section>

  <section id="mod-dump" class="module hidden">
    <div class="module-head"><h2>🗑️ Dumping</h2><button class="smallbtn" id="refreshDumping">Refresh</button></div>
    <div class="small">Pending discrepancies created automatically when submitted True Stock is below System OH.</div>
    <div id="dumpingStatus" class="msg">Open this tab to load.</div>
    <div id="dumpingList" class="grid list-grid"></div>
    <div class="module-head" style="margin-top:18px">
      <h2 style="font-size:16px">Recent History</h2>
      <select id="dumpingHistoryFilter" style="width:auto;padding:7px 9px">
        <option value="">Resolved + Superseded</option>
        <option value="RESOLVED">Resolved</option>
        <option value="SUPERSEDED">Superseded</option>
      </select>
    </div>
    <div id="dumpingHistoryStatus" class="msg"></div>
    <div id="dumpingHistoryList" class="grid list-grid"></div>
  </section>

  <section id="mod-price" class="module hidden">
    <div class="module-head"><h2>💲 Price Change</h2><button class="smallbtn" id="refreshPrice">Refresh</button></div>
    <div class="small">Public users can review and run what-if price impact. Proposal creation, approval, rejection, and execution marking remain admin-only. No action here directly changes live retail.</div>
    <div id="priceStatus" class="msg">Open this tab to load.</div>
    <div id="priceList" class="grid list-grid"></div>
    <div class="module-head" style="margin-top:18px">
      <h2 style="font-size:16px">Proposal Queue</h2>
      <select id="proposalFilter" style="width:auto;padding:7px 9px">
        <option value="">All Statuses</option>
        <option value="PENDING_REVIEW">Pending Review</option>
        <option value="APPROVED_FOR_EXECUTION">Approved</option>
        <option value="MARKED_EXECUTED">Marked Executed</option>
        <option value="REJECTED">Rejected</option>
        <option value="CANCELLED">Cancelled</option>
      </select>
    </div>
    <div id="proposalStatus" class="msg">Loading with Price Change.</div>
    <div id="proposalList" class="grid list-grid"></div>
  </section>
</div>

<nav class="nav">
  <div class="nav-inner">
    <button data-tab="quick" class="active"><span class="ico">🔎</span>Quick Check</button>
    <button data-tab="order"><span class="ico">📦</span>Ordering</button>
    <button data-tab="dump"><span class="ico">🗑️</span>Dumping</button>
    <button data-tab="price"><span class="ico">💲</span>Price Change</button>
  </div>
</nav>

<script>
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=2)=>{if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):String(v)}
const money=v=>v===null||v===undefined||v===''?'—':'$'+fmt(v,2);
const pct=v=>v===null||v===undefined||v===''?'—':fmt(Number(v)*100,1)+'%';
let currentUpc=null, loadedOrdering=false, loadedDumping=false, loadedPrice=false;

function setStatus(text,bad=false){$('status').textContent=text;$('status').className='msg'+(bad?' error':'')}
async function api(path,opts={}){
  const r=await fetch(path,opts);
  let body=null; try{body=await r.json()}catch{}
  if(!r.ok){const detail=body?.detail;throw new Error(typeof detail==='string'?detail:(detail?.reason||('HTTP '+r.status)))}
  return body;
}
function pill(status){
  const s=String(status||'UNKNOWN'); const cls=s==='READY'||s==='COVERAGE_AVAILABLE'?'ok':(s==='QA_HOLD'||s==='BLOCKED'||s==='COUNT_REQUIRED'?'bad':'warn');
  return '<span class="pill '+cls+'">'+esc(s)+'</span>';
}
function metric(k,v){return '<div class="metric"><div class="k">'+esc(k)+'</div><div class="v">'+esc(v)+'</div></div>'}
function flags(items){return '<div class="flags">'+(items||[]).map(x=>'<span class="flag">'+esc(x)+'</span>').join('')+'</div>'}

async function loadDashboard(){
  $('overviewMeta').textContent='Loading operational status…';
  try{
    const d=await api('/v1/app/dashboard');
    const q=d.quick_check||{}, inv=d.inventory_attention||{}, ts=d.true_stock||{}, du=d.dumping||{}, pc=d.price_change||{}, ord=d.ordering||{}, ow=d.order_workflow||{};
    $('overviewMetrics').innerHTML=[
      metric('Quick READY',fmt(q.ready_rows,0)),
      metric('QA HOLD',fmt(q.qa_hold_rows,0)),
      metric('Negative Stock',fmt(inv.negative_stock_actionable_owner_count,0)),
      metric('Active True Stock',fmt(ts.active_count,0)),
      metric('Pending Dumping',fmt(du.pending,0)),
      metric('Submitted Orders',fmt(ow.marked_submitted,0)),
      metric('Price Review',fmt(pc.pending_review,0))
    ].join('');
    $('overviewMeta').textContent='Batch '+(q.latest_publish_batch_id??'—')+
      ' · published '+(q.latest_published_at||'—')+
      ' · Ordering policies '+fmt(ord.enabled_policy_count??ord.configured_policy_count,0)+
      ' · Draft/Confirmed '+fmt(ow.draft,0)+'/'+fmt(ow.confirmed,0)+
      ' · Price approved '+fmt(pc.approved_for_execution,0);
  }catch(e){$('overviewMeta').textContent=e.message;$('overviewMeta').className='msg error'}
}

function switchTab(tab){
  document.querySelectorAll('.module').forEach(x=>x.classList.add('hidden'));
  $('mod-'+tab).classList.remove('hidden');
  document.querySelectorAll('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
  window.scrollTo({top:0,behavior:'smooth'});
  if(tab==='order'&&!loadedOrdering)loadOrdering();
  if(tab==='dump'&&!loadedDumping)loadDumping();
  if(tab==='price'&&!loadedPrice)loadPrice();
}
document.querySelectorAll('.nav button').forEach(b=>b.addEventListener('click',()=>switchTab(b.dataset.tab)));

async function search(){
  const q=$('q').value.trim(); if(!q)return;
  setStatus('Searching…'); $('detail').classList.add('hidden'); $('results').innerHTML='';
  try{
    const d=await api('/v1/app/quick-check/search?q='+encodeURIComponent(q)+'&limit=20');
    setStatus(d.count+' result(s)');
    $('results').innerHTML=(d.results||[]).map(r=>`
      <div class="card result" data-upc="${esc(r.ean_upc)}">
        <div class="row" style="justify-content:space-between"><div class="name">${esc(r.selling_description||r.family_description||r.ean_upc)}</div>${pill(r.quick_check_status)}</div>
        <div class="meta">UPC ${esc(r.ean_upc)} · Article ${esc(r.article_number)} · Family ${esc(r.main_article_number||r.family_id)}</div>
        <div class="meta">Price ${money(r.current_price)} · OH ${fmt(r.current_oh)} ${esc(r.current_oh_uom||'')}</div>
      </div>`).join('');
    document.querySelectorAll('.result').forEach(el=>el.addEventListener('click',()=>loadDetail(el.dataset.upc)));
  }catch(e){setStatus(e.message,true)}
}

async function loadDetail(upc){
  currentUpc=upc; setStatus('Loading '+upc+'…');
  try{
    const d=await api('/v1/app/quick-check/'+encodeURIComponent(upc));
    const x=d.item||{}, eff=d.effective_oh||{}, sys=d.system_oh||{}, promo=d.promotion||{}, ord=d.ordering||{};
    $('itemName').textContent=x.selling_description||x.family_description||x.ean_upc;
    $('itemMeta').textContent='UPC '+(x.ean_upc||'—')+' · Article '+(x.article_number||'—')+' · Family '+(x.main_article_number||x.family_id||'—')+' · '+(promo.classification||'');
    $('itemStatus').innerHTML=pill(x.quick_check_status);
    $('metrics').innerHTML=[
      metric('Price',money(x.current_price)),
      metric('Cost / Selling',money(x.current_cost_per_selling_unit)),
      metric('Effective OH',fmt(eff.quantity)+' '+(eff.uom||'')),
      metric('7D Qty',fmt(x.pos_qty_7d)),
      metric('30D Qty',fmt(x.pos_qty_30d)),
      metric('DOS',fmt(ord.days_supply??x.dos,1))
    ].join('');
    $('highlights').innerHTML=(d.highlights||[]).map(h=>'<div class="hl"><b>'+esc(h.code)+'</b><div class="small">'+esc(h.text)+'</div></div>').join('')||'<div class="small">No current highlights.</div>';

    $('inventorySummary').innerHTML=[
      metric('System OH',fmt(sys.quantity)+' '+(sys.uom||'')),
      metric('Effective OH',fmt(eff.quantity)+' '+(eff.uom||'')),
      metric('Source',eff.source||'—'),
      metric('Through',eff.movement_through_date||eff.date||'—')
    ].join('');
    $('trueStockUom').value=d.true_stock_input?.required_uom||'';
    $('trueStock').value=''; $('trueStockMsg').className='msg'; $('trueStockMsg').textContent='';

    $('ordering').innerHTML='<div><b>'+esc(ord.status||'—')+'</b> · '+esc(ord.action||'—')+'</div>'+
      (ord.suggested_order_qty!==undefined&&ord.suggested_order_qty!==null?'<div><b>Suggested: '+fmt(ord.suggested_order_qty)+' '+esc(ord.suggested_order_uom||'')+'</b></div>':'')+
      (ord.next_order_date?'<div class="small">Next order: '+esc(ord.next_order_date)+' · delivery: '+esc(ord.next_delivery_date||'—')+'</div>':'')+
      '<div class="small">'+esc(ord.reason||'')+'</div>'+
      (ord.days_supply!==undefined?'<div class="small">Effective DOS: '+fmt(ord.days_supply,1)+'</div>':'');
    const rel=d.family_relationships||{}, fam=rel.family||{};
    $('familyMeta').textContent='Main Article '+(fam.main_article_number||x.main_article_number||'—')+' · '+(fam.family_description||x.family_description||'');
    $('familyArticles').textContent='Articles: '+((rel.articles||[]).map(a=>(a.article_number||'—')+' ['+(a.relationship_type||'')+']').join(', ')||'—');
    $('receivingArticles').textContent='Receiving observed: '+((rel.receiving_articles_observed||[]).map(a=>(a.article_number||'—')+' · '+(a.receiving_uoms||'')+' · last '+(a.latest_receipt_date||'—')).join(' | ')||'—');
    $('relatedRows').innerHTML=(d.related_upcs||[]).map(r=>'<tr><td>'+esc(r.ean_upc)+'</td><td>'+esc(r.selling_description)+'</td><td>'+esc(r.selling_uom||'')+'</td><td>'+money(r.current_price)+'</td><td>'+fmt(r.pos_qty_7d)+'</td><td>'+pill(r.quick_check_status)+'</td></tr>').join('');
    $('salesRows').innerHTML=(d.sales_trend||[]).slice(0,20).map(r=>'<tr><td>'+esc(r.period_start_date)+' → '+esc(r.period_end_date)+'</td><td>'+esc(r.price_type)+'</td><td>'+fmt(r.sold_quantity)+'</td><td>'+money(r.sales_amount)+'</td><td>'+money(r.avg_sold_price)+'</td></tr>').join('');
    $('costRows').innerHTML=(d.cost_trend||[]).slice(0,20).map(r=>'<tr><td>'+esc(r.business_date||'')+'</td><td>'+esc(r.source_type||'')+'</td><td>'+money(r.cost_per_base_uom??r.cost_amount)+'</td><td>'+esc(r.base_uom||r.cost_uom||'')+'</td><td>'+esc(r.article_number||'')+'</td></tr>').join('');
    $('detail').classList.remove('hidden');
    setStatus('Loaded '+upc+' · '+(d.contract_version||''));
    $('detail').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){setStatus(e.message,true)}
}

async function submitTrueStock(){
  if(!currentUpc)return;
  const qty=$('trueStock').value.trim(), uom=$('trueStockUom').value.trim();
  if(qty===''||!uom){$('trueStockMsg').textContent='True Stock and UOM are required.';return}
  $('trueStockMsg').textContent='Submitting…';
  try{
    const r=await api('/v1/app/quick-check/'+encodeURIComponent(currentUpc)+'/true-stock',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:qty,uom})
    });
    const saved='Saved. Discrepancy '+fmt(r.discrepancy)+' '+(r.uom||'')+' · Dumping: '+(r.dumping_queue_action||'NONE');
    loadedDumping=false; loadedOrdering=false;
    await Promise.all([loadDetail(currentUpc),loadDashboard()]);
    $('trueStockMsg').className='msg ok'; $('trueStockMsg').textContent=saved;
  }catch(e){$('trueStockMsg').textContent=e.message;$('trueStockMsg').className='msg error'}
}

async function openQuickCheck(upc){
  if(!upc)return;
  switchTab('quick'); $('q').value=upc; $('results').innerHTML=''; await loadDetail(upc);
}

async function loadOrdering(){
  $('orderingStatus').textContent='Loading ordering review…'; $('orderingList').innerHTML='';
  try{
    const d=await api('/v1/app/ordering?limit=100'); loadedOrdering=true;
    $('orderingStatus').textContent=d.count+' item(s) · '+esc(d.quantity_policy||'');
    $('orderingList').innerHTML=(d.rows||[]).map(r=>{
      const o=r.ordering||{};
      return `<div class="card module-card" data-open-upc="${esc(r.ean_upc)}">
        <div class="row" style="justify-content:space-between"><div class="name">${esc(r.selling_description||r.ean_upc)}</div>${pill(o.status||r.quick_check_status)}</div>
        <div class="meta">UPC ${esc(r.ean_upc)} · Family ${esc(r.main_article_number||r.family_id||'—')}</div>
        <div class="kv">
          <div class="k">Effective OH</div><div class="v">${fmt(r.effective_oh)} ${esc(r.effective_oh_uom||'')}</div>
          <div class="k">7D velocity</div><div class="v">${fmt(r.upc_velocity_7d,2)}</div>
          <div class="k">Effective DOS</div><div class="v">${fmt(o.days_supply??o.effective_dos?.days_supply,1)}</div>
          <div class="k">Suggested Order</div><div class="v">${fmt(o.suggested_order_qty)} ${esc(o.suggested_order_uom||'')}</div>
          <div class="k">Next Order</div><div class="v">${esc(o.next_order_date||'—')}</div>
          <div class="k">Next Delivery</div><div class="v">${esc(o.next_delivery_date||'—')}</div>
          <div class="k">Coverage + Safety</div><div class="v">${fmt(o.coverage_days_after_delivery,1)} + ${fmt(o.safety_days,1)} days</div>
          <div class="k">Policy Scope</div><div class="v">${esc(o.policy?.scope_type||'—')} ${esc(o.policy?.scope_key||'')}</div>
          <div class="k">Price</div><div class="v">${money(r.current_price)}</div>
          <div class="k">Price type</div><div class="v">${esc(r.current_price_type||'—')}</div>
        </div>
        <div class="small" style="margin-top:8px">${esc(o.action||'')} · ${esc(o.reason||'')}</div>
      </div>`;
    }).join('')||'<div class="empty">No ordering review rows.</div>';
    bindOpenCards('orderingList');
  }catch(e){$('orderingStatus').textContent=e.message;$('orderingStatus').className='msg error'}
}

async function loadDumping(){
  $('dumpingStatus').textContent='Loading pending discrepancies…';
  $('dumpingHistoryStatus').textContent='Loading history…';
  $('dumpingList').innerHTML=''; $('dumpingHistoryList').innerHTML='';
  const historyStatus=$('dumpingHistoryFilter').value;
  const historyPath='/v1/app/dumping/history?limit=80'+(historyStatus?'&status='+encodeURIComponent(historyStatus):'');
  try{
    const [d,h]=await Promise.all([
      api('/v1/app/dumping/pending'),
      api(historyPath)
    ]);
    loadedDumping=true;
    $('dumpingStatus').textContent=(d.count??(d.rows||[]).length)+' pending discrepancy item(s)';
    $('dumpingHistoryStatus').textContent=h.count+' recent history item(s)';
    $('dumpingList').innerHTML=(d.rows||[]).map(r=>`
      <div class="card module-card" data-open-upc="${esc(r.ean_upc||'')}">
        <div class="row" style="justify-content:space-between"><div class="name">Family ${esc(r.main_article_number||r.family_id||'—')}</div><span class="pill warn">${esc(r.queue_status||'PENDING')}</span></div>
        <div class="meta">UPC ${esc(r.ean_upc||'—')} · Article ${esc(r.article_number||'—')} · ${esc(r.scope_type||'')}</div>
        <div class="kv">
          <div class="k">System OH</div><div class="v">${fmt(r.system_oh_quantity)} ${esc(r.uom_code||'')}</div>
          <div class="k">True Stock</div><div class="v">${fmt(r.true_stock_quantity)} ${esc(r.uom_code||'')}</div>
          <div class="k">Discrepancy</div><div class="v">${fmt(r.discrepancy_quantity)} ${esc(r.uom_code||'')}</div>
          <div class="k">Updated</div><div class="v">${esc(r.updated_at||'—')}</div>
        </div>
        <div class="row" style="margin-top:10px;justify-content:flex-end">
          <button class="smallbtn resolveDump" data-dumping-id="${esc(r.discrepancy_id)}">Mark handled</button>
        </div>
      </div>`).join('')||'<div class="empty">No pending dumping discrepancies.</div>';
    $('dumpingHistoryList').innerHTML=(h.rows||[]).map(r=>`
      <div class="card module-card" data-open-upc="${esc(r.ean_upc||'')}">
        <div class="row" style="justify-content:space-between"><div class="name">Family ${esc(r.main_article_number||r.family_id||'—')}</div>${pill(r.queue_status)}</div>
        <div class="meta">UPC ${esc(r.ean_upc||'—')} · Article ${esc(r.article_number||'—')}</div>
        <div class="kv">
          <div class="k">System OH → True</div><div class="v">${fmt(r.system_oh_quantity)} → ${fmt(r.true_stock_quantity)} ${esc(r.uom_code||'')}</div>
          <div class="k">Discrepancy</div><div class="v">${fmt(r.discrepancy_quantity)} ${esc(r.uom_code||'')}</div>
          <div class="k">Resolved</div><div class="v">${esc(r.resolved_at||'—')}</div>
          <div class="k">Resolved By</div><div class="v">${esc(r.resolved_by||'—')}</div>
        </div>
        <div class="small" style="margin-top:8px">${esc(r.resolution_note||'')}</div>
      </div>`).join('')||'<div class="empty">No matching dumping history.</div>';
    bindOpenCards('dumpingList'); bindOpenCards('dumpingHistoryList');
    $('dumpingList').querySelectorAll('.resolveDump').forEach(btn=>btn.addEventListener('click',e=>{
      e.stopPropagation(); resolveDumping(btn.dataset.dumpingId,btn);
    }));
  }catch(e){
    $('dumpingStatus').textContent=e.message;$('dumpingStatus').className='msg error';
    $('dumpingHistoryStatus').textContent=e.message;$('dumpingHistoryStatus').className='msg error';
  }
}

async function resolveDumping(id,btn){
  if(!id)return;
  if(!window.confirm('Mark this dumping discrepancy handled? This closes the queue item only and does not change inventory.'))return;
  btn.disabled=true; btn.textContent='Saving…';
  try{
    await api('/v1/app/dumping/'+encodeURIComponent(id)+'/resolve',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({confirm:'RESOLVE_DUMPING_DISCREPANCY'})
    });
    loadedDumping=false; await Promise.all([loadDumping(),loadDashboard()]);
  }catch(e){
    $('dumpingStatus').textContent=e.message; $('dumpingStatus').className='msg error';
    btn.disabled=false; btn.textContent='Mark handled';
  }
}

async function previewPrice(upc,inputId,outputId){
  const input=$(inputId), out=$(outputId);
  const raw=input?.value?.trim();
  if(!raw){out.textContent='Enter a proposed price.';out.className='msg error';return}
  out.textContent='Calculating…';out.className='msg';
  try{
    const d=await api('/v1/app/price-change/'+encodeURIComponent(upc)+'/preview?proposed_price='+encodeURIComponent(raw));
    const x=d.impact||{};
    out.className='card notice';
    out.innerHTML='<div class="section-title">What-if Impact</div>'+
      '<div class="kv">'+
      '<div class="k">Proposed Price</div><div class="v">'+money(x.proposed_price)+'</div>'+
      '<div class="k">Proposed GP%</div><div class="v">'+pct(x.proposed_gp_pct)+'</div>'+
      '<div class="k">Projected GP$/day</div><div class="v">'+money(x.projected_gp_per_day_7d)+'</div>'+
      '<div class="k">GP$/day Delta</div><div class="v">'+money(x.projected_gp_per_day_delta)+'</div>'+
      '</div><div class="small" style="margin-top:8px">'+esc(x.caveat||'')+'</div>'+
      '<div class="small">Related UPC sync: '+esc(d.related_upc_sync_policy||'NOT_INFERRED')+' · Live price changed: No</div>';
  }catch(e){out.textContent=e.message;out.className='msg error'}
}

async function loadPrice(){
  $('priceStatus').textContent='Loading price review…';
  $('proposalStatus').textContent='Loading proposal queue…';
  $('priceList').innerHTML=''; $('proposalList').innerHTML='';
  try{
    const proposalStatusFilter=$('proposalFilter').value;
    const proposalPath='/v1/app/price-change/proposals?limit=60'+(proposalStatusFilter?'&status='+encodeURIComponent(proposalStatusFilter):'');
    const [d,p]=await Promise.all([
      api('/v1/app/price-change?limit=160'),
      api(proposalPath)
    ]);
    loadedPrice=true;
    $('priceStatus').textContent=d.count+' item(s) · '+esc(d.mode||'');
    $('proposalStatus').textContent=p.count+' proposal(s) in audit history';

    $('priceList').innerHTML=(d.rows||[]).map((r,idx)=>{
      const inputId='priceInput_'+idx, outputId='pricePreview_'+idx;
      const refButtons=[
        ['Sweet',r.sweet_spot_price],['WGPM',r.wgpm_price],
        ['A',r.company_price_a],['B',r.company_price_b],['C',r.company_price_c]
      ].filter(x=>x[1]!==null&&x[1]!==undefined&&x[1]!=='').map(x=>
        '<button class="smallbtn refPrice" data-input="'+inputId+'" data-value="'+esc(x[1])+'">'+esc(x[0])+' '+money(x[1])+'</button>'
      ).join('');
      return `<div class="card module-card" data-open-upc="${esc(r.ean_upc)}">
        <div class="row" style="justify-content:space-between"><div class="name">${esc(r.selling_description||r.ean_upc)}</div>${pill(r.quick_check_status)}</div>
        <div class="meta">UPC ${esc(r.ean_upc)} · Article ${esc(r.article_number||'—')} · ${esc(r.current_price_type||'')}</div>
        <div class="kv">
          <div class="k">Current Price</div><div class="v">${money(r.current_price)}</div>
          <div class="k">Cost / Selling</div><div class="v">${money(r.current_cost_per_selling_unit)}</div>
          <div class="k">GP%</div><div class="v">${pct(r.gp_pct_current)}</div>
          <div class="k">7D Qty / Velocity</div><div class="v">${fmt(r.pos_qty_7d)} / ${fmt(r.upc_velocity_7d,2)}</div>
          <div class="k">DOH / DOS</div><div class="v">${fmt(r.doh,1)} / ${fmt(r.dos,1)}</div>
          <div class="k">Sweet Spot</div><div class="v">${money(r.sweet_spot_price)}</div>
          <div class="k">WGPM</div><div class="v">${money(r.wgpm_price)}</div>
          <div class="k">Company A / B / C</div><div class="v">${money(r.company_price_a)} / ${money(r.company_price_b)} / ${money(r.company_price_c)}</div>
        </div>
        ${flags(r.review_flags)}
        <div class="row" style="margin-top:10px">${refButtons}</div>
        <div class="row" style="margin-top:8px">
          <input id="${inputId}" class="priceInput" inputmode="decimal" placeholder="What-if price" value="${esc(r.current_price??'')}">
          <button class="smallbtn previewPriceBtn" data-upc="${esc(r.ean_upc)}" data-input="${inputId}" data-output="${outputId}">Preview</button>
        </div>
        <div id="${outputId}" class="msg"></div>
      </div>`;
    }).join('')||'<div class="empty">No active price review rows.</div>';

    $('proposalList').innerHTML=(p.rows||[]).map(r=>`
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <div class="name">${esc(r.selling_description||r.ean_upc)}</div>
          <span class="pill ${String(r.proposal_status||'').includes('APPROVED')?'ok':(String(r.proposal_status||'').includes('REJECT')?'bad':'warn')}">${esc(r.proposal_status||'')}</span>
        </div>
        <div class="meta">Proposal #${esc(r.proposal_id)} · UPC ${esc(r.ean_upc)} · Basis ${esc(r.proposal_basis||'')}</div>
        <div class="kv">
          <div class="k">Current → Proposed</div><div class="v">${money(r.current_price)} → ${money(r.proposed_price)}</div>
          <div class="k">GP%</div><div class="v">${pct(r.current_gp_pct)} → ${pct(r.proposed_gp_pct)}</div>
          <div class="k">Projected GP$/day</div><div class="v">${money(r.projected_gp_per_day_7d)}</div>
          <div class="k">GP$/day Delta</div><div class="v">${money(r.projected_gp_per_day_delta)}</div>
          <div class="k">Proposed By</div><div class="v">${esc(r.proposed_by||'—')}</div>
          <div class="k">Proposed At</div><div class="v">${esc(r.proposed_at||'—')}</div>
        </div>
        <div class="small" style="margin-top:8px">${esc(r.reason||r.review_note||'')}</div>
      </div>`).join('')||'<div class="empty">No price-change proposals yet.</div>';

    bindOpenCards('priceList');
    $('priceList').querySelectorAll('.refPrice').forEach(btn=>btn.addEventListener('click',e=>{
      e.stopPropagation(); const input=$(btn.dataset.input); if(input)input.value=btn.dataset.value;
    }));
    $('priceList').querySelectorAll('.previewPriceBtn').forEach(btn=>btn.addEventListener('click',e=>{
      e.stopPropagation(); previewPrice(btn.dataset.upc,btn.dataset.input,btn.dataset.output);
    }));
    $('priceList').querySelectorAll('.priceInput').forEach(input=>input.addEventListener('click',e=>e.stopPropagation()));
  }catch(e){
    $('priceStatus').textContent=e.message;$('priceStatus').className='msg error';
    $('proposalStatus').textContent=e.message;$('proposalStatus').className='msg error';
  }
}

function bindOpenCards(containerId){
  $(containerId).querySelectorAll('[data-open-upc]').forEach(el=>el.addEventListener('click',()=>{
    const upc=el.dataset.openUpc; if(upc)openQuickCheck(upc);
  }));
}

$('search').addEventListener('click',search);
$('q').addEventListener('keydown',e=>{if(e.key==='Enter')search()});
$('submitTrueStock').addEventListener('click',submitTrueStock);
$('refreshOverview').addEventListener('click',loadDashboard);
$('refreshOrdering').addEventListener('click',()=>{loadedOrdering=false;loadOrdering()});
$('refreshDumping').addEventListener('click',()=>{loadedDumping=false;loadDumping()});
$('dumpingHistoryFilter').addEventListener('change',()=>{loadedDumping=false;loadDumping()});
$('refreshPrice').addEventListener('click',()=>{loadedPrice=false;loadPrice()});
$('proposalFilter').addEventListener('change',()=>{loadedPrice=false;loadPrice()});
loadDashboard();
</script>
</body>
</html>"""


def quick_check_web_html() -> str:
    return QUICK_CHECK_WEB_HTML
