from __future__ import annotations

QUICK_CHECK_WEB_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>FULL MYSQL Quick Check</title>
<style>
:root{color-scheme:light dark;--bg:#f5f6f8;--card:#fff;--text:#16181d;--muted:#667085;--line:#e4e7ec;--accent:#175cd3;--bad:#b42318;--warn:#b54708;--ok:#067647}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--text:#f3f4f6;--muted:#98a2b3;--line:#2c313a;--accent:#84adff;--bad:#f97066;--warn:#fdb022;--ok:#47cd89}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:14px}.top{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(10px);padding:10px 0 12px}
h1{font-size:20px;margin:0 0 8px}.sub{color:var(--muted);font-size:12px}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
input,button{font:inherit;border-radius:10px;border:1px solid var(--line);padding:11px 12px;background:var(--card);color:var(--text)}
input{min-width:0;flex:1}button{cursor:pointer;font-weight:650}button.primary{background:var(--accent);color:white;border-color:transparent}.token{max-width:300px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin:10px 0;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}@media(min-width:760px){.grid.metrics{grid-template-columns:repeat(6,minmax(0,1fr))}}
.metric{border:1px solid var(--line);border-radius:12px;padding:10px}.metric .k{font-size:11px;color:var(--muted)}.metric .v{font-size:17px;font-weight:750;margin-top:3px;overflow-wrap:anywhere}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 8px;font-size:11px;font-weight:700}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.result{cursor:pointer}.result:hover{border-color:var(--accent)}.name{font-weight:800}.meta{color:var(--muted);font-size:12px;margin-top:4px}
.section-title{font-size:13px;font-weight:800;margin:2px 0 8px}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:7px 5px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:650}
.scroll{overflow:auto}.hidden{display:none!important}.msg{font-size:12px;color:var(--muted);margin-top:8px}.error{color:var(--bad)}.notice{border-left:3px solid var(--accent);padding-left:10px}.hl{padding:8px 0;border-bottom:1px solid var(--line)}.hl:last-child{border-bottom:0}
.sticky-action{position:sticky;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px;margin:14px -14px -14px;border-radius:0 0 14px 14px}
.small{font-size:11px;color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1>FULL MYSQL · Quick Check</h1>
    <div class="row">
      <input id="token" class="token" type="password" placeholder="API token (session only)" autocomplete="off">
      <button id="saveToken">Use token</button>
      <button id="clearToken">Clear</button>
    </div>
    <div class="row" style="margin-top:8px">
      <input id="q" placeholder="Search Article, UPC, or item name">
      <button id="search" class="primary">Search</button>
    </div>
    <div id="status" class="msg">Enter a token and search.</div>
  </div>

  <div id="results"></div>

  <div id="detail" class="hidden">
    <div class="card">
      <div class="row" style="justify-content:space-between">
        <div>
          <div id="itemName" class="name" style="font-size:20px"></div>
          <div id="itemMeta" class="meta"></div>
        </div>
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
      <div class="small" style="margin-top:8px">Submitting True Stock makes it the active inventory reference until the next OH upload. If lower than System OH, a Pending Dumping discrepancy is created/updated automatically.</div>
    </div>

    <div class="card">
      <div class="section-title">Ordering</div>
      <div id="ordering"></div>
    </div>

    <div class="card">
      <div class="section-title">Family / Related UPCs</div>
      <div id="familyMeta" class="meta"></div>
      <div id="familyArticles" class="small" style="margin-top:6px"></div>
      <div id="receivingArticles" class="small" style="margin-top:4px"></div>
      <div class="scroll" style="margin-top:8px"><table><thead><tr><th>UPC</th><th>Description</th><th>UOM</th><th>Price</th><th>7D</th><th>Status</th></tr></thead><tbody id="relatedRows"></tbody></table></div>
    </div>

    <div class="card">
      <div class="section-title">Sales Trend · source periods</div>
      <div class="scroll"><table><thead><tr><th>Period</th><th>Type</th><th>Qty</th><th>Sales</th><th>Avg Price</th></tr></thead><tbody id="salesRows"></tbody></table></div>
    </div>

    <div class="card">
      <div class="section-title">Cost Trend</div>
      <div class="scroll"><table><thead><tr><th>Date</th><th>Source</th><th>Cost</th><th>UOM</th><th>Article</th></tr></thead><tbody id="costRows"></tbody></table></div>
    </div>

    <div class="card notice">
      <div class="section-title">Inventory Policy</div>
      <div class="small">System OH uses Unrestricted only. Stock in Transit, Value in Transit, In Transfer (Site), and Value in Stock Tfr are ignored for OH, OH cost, inventory valuation, DOS, and cost conversion.</div>
    </div>
  </div>
</div>
<script>
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=2)=>{if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):String(v)}
const money=v=>v===null||v===undefined||v===''?'—':'$'+fmt(v,2);
const token=()=>sessionStorage.getItem('fullmysql_token')||$('token').value.trim();
let currentUpc=null;

function setStatus(text,bad=false){$('status').textContent=text;$('status').className='msg'+(bad?' error':'')}
async function api(path,opts={}){
  const t=token(); if(!t) throw new Error('API token required');
  const headers=Object.assign({'Authorization':'Bearer '+t},opts.headers||{});
  const r=await fetch(path,Object.assign({},opts,{headers}));
  let body=null; try{body=await r.json()}catch{}
  if(!r.ok){const detail=body?.detail;throw new Error(typeof detail==='string'?detail:(detail?.reason||('HTTP '+r.status)))}
  return body;
}
function pill(status){
  const s=String(status||'UNKNOWN'); const cls=s==='READY'?'ok':(s==='QA_HOLD'?'bad':'warn');
  return '<span class="pill '+cls+'">'+esc(s)+'</span>';
}
function metric(k,v){return '<div class="metric"><div class="k">'+esc(k)+'</div><div class="v">'+esc(v)+'</div></div>'}

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

    $('ordering').innerHTML='<div><b>'+esc(ord.status||'—')+'</b> · '+esc(ord.action||'—')+'</div><div class="small">'+esc(ord.reason||'')+'</div>'+(ord.days_supply!==undefined?'<div class="small">Effective DOS: '+fmt(ord.days_supply,1)+'</div>':'');
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
    await loadDetail(currentUpc);
    $('trueStockMsg').className='msg ok';
    $('trueStockMsg').textContent=saved;
  }catch(e){$('trueStockMsg').textContent=e.message;$('trueStockMsg').className='msg error'}
}

$('saveToken').addEventListener('click',()=>{const t=$('token').value.trim();if(t){sessionStorage.setItem('fullmysql_token',t);$('token').value='';setStatus('Token stored for this browser session.')}});
$('clearToken').addEventListener('click',()=>{sessionStorage.removeItem('fullmysql_token');$('token').value='';setStatus('Token cleared.')});
$('search').addEventListener('click',search);
$('q').addEventListener('keydown',e=>{if(e.key==='Enter')search()});
$('submitTrueStock').addEventListener('click',submitTrueStock);
if(sessionStorage.getItem('fullmysql_token'))setStatus('Session token available. Search an item.');
</script>
</body>
</html>"""


def quick_check_web_html() -> str:
    return QUICK_CHECK_WEB_HTML
