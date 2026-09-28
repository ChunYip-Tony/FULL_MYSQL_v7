from __future__ import annotations

QUICK_CHECK_WEB_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#063b59">
<title>FULL MYSQL · Quick Check</title>
<style>
:root{
  color-scheme:light dark;
  --ocean:#073b59;--ocean2:#0b5d78;--ice:#eaf6fb;--card:rgba(249,253,255,.94);
  --text:#10243a;--muted:#5e7486;--line:rgba(74,118,145,.22);--accent:#0d6fb8;
  --blue:#0b5ec7;--orange:#ee7a16;--bad:#cf2f2f;--warn:#b66b06;--ok:#138447;
  --nav:rgba(4,46,71,.97);--shadow:0 2px 10px rgba(0,37,58,.16)
}
@media(prefers-color-scheme:dark){
  :root{--ice:#102736;--card:rgba(13,35,49,.94);--text:#eef9ff;--muted:#a7c0cf;--line:rgba(151,195,219,.19);--accent:#68b9f0;--blue:#6da8ff;--orange:#ff9b45;--bad:#ff746b;--warn:#ffc267;--ok:#5dda92}
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;color:var(--text);font:14px/1.35 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  padding-bottom:72px;min-height:100vh;
  background:
    linear-gradient(rgba(3,45,70,.78),rgba(3,50,73,.78)),
    radial-gradient(circle at 15% 20%,rgba(149,225,241,.30),transparent 34%),
    radial-gradient(circle at 85% 55%,rgba(4,119,153,.28),transparent 30%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='260' height='150' viewBox='0 0 260 150'%3E%3Cg fill='none' stroke='%23b9e6ef' stroke-opacity='.16' stroke-width='2'%3E%3Cpath d='M16 28c18-14 39-12 57 0-18 14-39 14-57 0zm57 0 16-10v20z'/%3E%3Cpath d='M154 95c22-15 46-13 66 1-20 16-45 16-66-1zm66 1 18-12v24z'/%3E%3Cpath d='M38 118c10-7 22-7 32 0-10 8-22 8-32 0zm32 0 9-6v12z'/%3E%3Cpath d='M112 24c9-6 20-6 29 0-9 7-20 7-29 0zm29 0 8-5v10z'/%3E%3C/g%3E%3C/svg%3E");
  background-size:auto,auto,auto,260px 150px
}
.wrap{max-width:1180px;margin:0 auto;padding:8px 8px 12px}
.top{
  position:sticky;top:0;z-index:20;margin:0 -8px;padding:8px 10px 7px;
  background:linear-gradient(90deg,rgba(4,48,74,.98),rgba(6,76,102,.96));
  border-bottom:1px solid rgba(218,246,255,.22);backdrop-filter:blur(12px);color:#f3fbff
}
.brand{display:flex;justify-content:space-between;align-items:center;gap:10px}
.brand h1{font-size:18px;margin:0;letter-spacing:.3px}.brand h1:before{content:"🐟 ";font-size:17px}.version{font-size:10px;opacity:.78}
.row{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.search-row{margin-top:7px}
input,button,select{font:inherit;border-radius:9px;border:1px solid var(--line);padding:9px 10px;background:var(--card);color:var(--text)}
input{min-width:0;flex:1}button{cursor:pointer;font-weight:760}
button.primary{background:linear-gradient(180deg,#0d79c5,#075d9c);color:#fff;border-color:transparent}
button.smallbtn{padding:6px 9px;font-size:11px}
button.danger{background:color-mix(in srgb,var(--bad) 12%,var(--card));color:var(--bad)}
.card{
  background:var(--card);border:1px solid rgba(182,222,238,.58);border-radius:12px;
  padding:10px;margin:7px 0;box-shadow:var(--shadow);backdrop-filter:blur(9px)
}
.compact{padding:8px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.metrics{grid-template-columns:repeat(4,minmax(0,1fr));gap:0;border:1px solid var(--line);border-radius:11px;overflow:hidden;background:var(--card)}
.metric{min-width:0;padding:8px 7px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
.metric:nth-child(4n){border-right:0}.metric:nth-last-child(-n+4){border-bottom:0}
.metric .k{font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.metric .v{font-size:16px;font-weight:820;margin-top:2px;line-height:1.12;overflow-wrap:anywhere}
.metric .trend{font-size:10px;margin-top:4px;font-weight:760;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tr-up{color:var(--ok)}.tr-down{color:var(--bad)}.tr-flat{color:var(--muted)}
.pill{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:2px 7px;font-size:10px;font-weight:780;background:color-mix(in srgb,var(--card) 88%,transparent)}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.name{font-weight:840}.meta{color:var(--muted);font-size:11px;margin-top:2px}
.section-title{font-size:13px;font-weight:840;margin:0 0 6px;display:flex;align-items:center;gap:5px}
.scroll{overflow:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:11px}
th,td{text-align:left;padding:5px 4px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:690;white-space:nowrap}
.hidden{display:none!important}.msg{font-size:11px;color:var(--muted);margin-top:5px}.error{color:var(--bad)}
.small{font-size:10px;color:var(--muted)}.count{font-size:11px;color:var(--muted)}
.module-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:9px 0 4px}.module-head h2{font-size:17px;margin:0;color:#f2fbff}
.kv{display:grid;grid-template-columns:1fr auto;gap:4px 8px;font-size:11px;margin-top:6px}.kv .k{color:var(--muted)}.kv .v{text-align:right;font-weight:760}
.flags{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px}.flag{font-size:9px;border:1px solid var(--line);border-radius:999px;padding:2px 5px;color:var(--muted)}
.item-hero{
  position:relative;overflow:hidden;background:
  linear-gradient(100deg,rgba(244,252,255,.97),rgba(219,243,249,.90)),
  repeating-linear-gradient(135deg,transparent 0 13px,rgba(10,100,136,.04) 13px 14px);
  color:#10243a
}
@media(prefers-color-scheme:dark){.item-hero{background:linear-gradient(100deg,rgba(15,42,59,.97),rgba(11,67,82,.90));color:#eef9ff}}
.item-hero:after{content:"🐟  🐠  🐟";position:absolute;right:8px;bottom:-5px;font-size:32px;opacity:.12;letter-spacing:3px}
.hero-main{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;position:relative;z-index:1}.hero-main .name{font-size:18px;line-height:1.1}
.badges{display:flex;gap:5px;flex-wrap:wrap;margin-top:5px}
.two-col{display:grid;grid-template-columns:minmax(0,1fr);gap:7px}
.price-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:7px}
.inventory-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:7px}
.inventory-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;border-bottom:1px solid var(--line);padding-bottom:7px;margin-bottom:7px}
.inv-cell{min-width:0;padding:0 6px;border-right:1px solid var(--line)}.inv-cell:first-child{padding-left:0}.inv-cell:last-child{border-right:0;padding-right:0}
.inv-cell .k{font-size:9px;color:var(--muted)}.inv-cell .v{font-size:14px;font-weight:820;margin-top:2px;overflow-wrap:anywhere}
.true-row{display:grid;grid-template-columns:minmax(0,1fr) 60px 92px;gap:6px}
.sweet-price{font-size:28px;font-weight:900;color:var(--ok);line-height:1.05;margin:3px 0 6px}
.sweet-note{font-size:10px;color:var(--muted)}
.chart-wrap{border-top:1px solid var(--line);padding-top:5px}
.chart-scroll{overflow-x:auto;overflow-y:hidden;padding-bottom:2px;-webkit-overflow-scrolling:touch}
.chart-scroll svg{display:block;height:250px}
.legend{display:flex;gap:11px;align-items:center;flex-wrap:wrap;font-size:10px;color:var(--muted)}
.legend .bar{display:inline-block;width:15px;height:8px;background:var(--blue);border-radius:2px;margin-right:3px}.legend .line{display:inline-block;width:17px;height:3px;background:var(--orange);border-radius:4px;margin-right:3px;vertical-align:middle}
.hl{padding:5px 0;border-bottom:1px solid var(--line)}.hl:last-child{border-bottom:0}
.result{cursor:pointer;padding:8px}.result:hover{border-color:var(--accent)}
.notice{border-left:3px solid var(--accent);padding-left:8px}
.empty{text-align:center;color:var(--muted);padding:22px 8px}
details summary{cursor:pointer;font-weight:780;font-size:12px}
.nav{
  position:fixed;left:0;right:0;bottom:0;z-index:30;background:var(--nav);border-top:1px solid rgba(208,240,252,.20);
  backdrop-filter:blur(12px);padding:5px max(7px,env(safe-area-inset-right)) calc(5px + env(safe-area-inset-bottom)) max(7px,env(safe-area-inset-left))
}
.nav-inner{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.nav button{border:0;background:transparent;padding:5px 2px;border-radius:9px;color:#b9d8e7;font-size:9px;line-height:1.05}
.nav button.active{background:rgba(120,205,244,.14);color:#fff}.nav .ico{display:block;font-size:19px;line-height:22px}
@media(min-width:560px){
  .wrap{padding:10px 12px 16px}.top{margin:0 -12px;padding-left:14px;padding-right:14px}
  .price-grid,.inventory-grid{grid-template-columns:1.15fr .85fr}.two-col{grid-template-columns:1fr 1fr}
  .metrics{grid-template-columns:repeat(8,minmax(0,1fr))}
  .metric{border-bottom:0}.metric:nth-child(4n){border-right:1px solid var(--line)}.metric:nth-child(8n){border-right:0}
}
@media(max-width:359px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.metric:nth-child(2n){border-right:0}.metric:nth-child(4n){border-right:0}.true-row{grid-template-columns:1fr 52px}.true-row button{grid-column:1/-1}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="brand"><h1>FULL MYSQL</h1><div class="version">Fish Market Ops · v7.0.124</div></div>
    <div class="row" style="justify-content:space-between">
      <div id="globalStatus" class="msg" style="color:#cfe7f2">Live operational view</div>
      <a href="/admin" style="font-size:10px;color:#d5edf6;text-decoration:none">Admin</a>
    </div>
  </div>

  <section id="mod-quick" class="module">
    <div class="module-head"><h2>🔎 Quick Check</h2></div>
    <div class="row search-row">
      <input id="q" placeholder="Search Article, UPC, or item name" autocomplete="off">
      <button id="search" class="primary">Search</button>
    </div>
    <div id="status" class="msg">Search an item.</div>
    <div id="results"></div>

    <div id="detail" class="hidden">
      <div class="card item-hero compact">
        <div class="hero-main">
          <div>
            <div id="itemName" class="name"></div>
            <div id="itemMeta" class="meta"></div>
            <div id="itemBadges" class="badges"></div>
          </div>
          <div id="itemStatus"></div>
        </div>
      </div>

      <div id="metrics" class="metrics"></div>

      <div class="price-grid">
        <div class="card compact">
          <div class="section-title">💲 Price vs Velocity History <span class="small">completed POS data days</span></div>
          <div class="scroll"><table>
            <thead><tr><th>Last Seen</th><th>Price</th><th>Velocity</th><th>GP$/day</th></tr></thead>
            <tbody id="priceVelocityRows"></tbody>
          </table></div>
        </div>
        <div class="card compact">
          <div class="section-title">🎯 Suggested Sweet Spot Price</div>
          <div id="sweetSpotPrice" class="sweet-price">—</div>
          <div id="sweetSpotNote" class="sweet-note"></div>
        </div>
      </div>

      <div class="inventory-grid">
        <div class="card compact">
          <div class="section-title">📦 Inventory / True Stock</div>
          <div id="inventoryStats" class="inventory-stats"></div>
          <div class="true-row">
            <input id="trueStock" inputmode="decimal" placeholder="Enter True Stock">
            <input id="trueStockUom" readonly>
            <button id="submitTrueStock" class="primary">Update</button>
          </div>
          <div id="trueStockMsg" class="msg"></div>
        </div>

        <div class="card compact">
          <div class="section-title">🛒 Ordering</div>
          <div id="ordering"></div>
        </div>
      </div>

      <div class="card compact">
        <div class="row" style="justify-content:space-between">
          <div class="section-title" style="margin:0">📊 Sales Trend <span class="small">latest 28 completed POS data days</span></div>
          <div class="legend"><span><i class="bar"></i>GP$</span><span><i class="line"></i>Avg Selling Price</span></div>
        </div>
        <div class="small" style="margin:2px 0 4px">Every point shows its Y value. Swipe horizontally on phone for full detail.</div>
        <div id="salesChart" class="chart-wrap"></div>
      </div>

      <div class="card compact">
        <div class="row" style="justify-content:space-between"><div class="section-title" style="margin:0">👥 Family / Ordering Article / Related UPC</div><span class="small">compact family view</span></div>
        <div id="familyMeta" class="meta"></div>
        <div id="familyArticles" class="small" style="margin-top:3px"></div>
        <div id="receivingArticles" class="small" style="margin-top:2px"></div>
        <div class="scroll" style="margin-top:5px"><table>
          <thead><tr><th>UPC</th><th>Description</th><th>UOM</th><th>Price</th><th>7D</th><th>Status</th></tr></thead>
          <tbody id="relatedRows"></tbody>
        </table></div>
      </div>

      <div class="card compact">
        <div class="section-title">⚠️ Highlights / QA</div>
        <div id="highlights"></div>
      </div>

      <details class="card compact">
        <summary>Cost history / source lineage</summary>
        <div class="scroll" style="margin-top:6px"><table>
          <thead><tr><th>Date</th><th>Source</th><th>Cost</th><th>UOM</th><th>Article</th></tr></thead>
          <tbody id="costRows"></tbody>
        </table></div>
      </details>
    </div>
  </section>

  <section id="mod-oh" class="module hidden">
    <div class="module-head"><h2>📋 OH Discrepancy Report & Clear</h2><button class="smallbtn" id="refreshOH">Refresh</button></div>
    <div class="card compact">
      <div class="small">True Stock below System OH creates a pending discrepancy. Clearing closes the discrepancy report only; it does not alter inventory.</div>
      <div id="ohStatus" class="msg">Open this tab to load.</div>
    </div>
    <div id="ohList"></div>
    <div class="module-head" style="margin-top:10px">
      <h2 style="font-size:14px">Recent cleared / superseded</h2>
      <select id="ohHistoryFilter" style="width:auto;padding:6px 8px">
        <option value="">All history</option>
        <option value="RESOLVED">Cleared</option>
        <option value="SUPERSEDED">Superseded</option>
      </select>
    </div>
    <div id="ohHistoryStatus" class="msg"></div>
    <div id="ohHistoryList"></div>
  </section>

  <section id="mod-price" class="module hidden">
    <div class="module-head"><h2>💲 Price Change</h2><button class="smallbtn" id="refreshPrice">Refresh</button></div>
    <div class="card compact"><div class="small">What-if pricing only. No action here directly changes live retail.</div><div id="priceStatus" class="msg">Open this tab to load.</div></div>
    <div id="priceList"></div>
  </section>
</div>

<nav class="nav">
  <div class="nav-inner">
    <button data-tab="quick" class="active"><span class="ico">🔎</span>Quick Check</button>
    <button data-tab="oh"><span class="ico">📋</span>OH Discrepancy<br>Report & Clear</button>
    <button data-tab="price"><span class="ico">💲</span>Price Change</button>
  </div>
</nav>

<script>
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=(v,d=2)=>{const n=num(v);return n===null?'—':n.toLocaleString(undefined,{maximumFractionDigits:d})};
const money=v=>num(v)===null?'—':'$'+fmt(v,2);
const dateLabel=v=>{if(!v)return '—';const s=String(v);const d=new Date(s.length===10?s+'T00:00:00':s);return Number.isNaN(d.getTime())?s:d.toLocaleDateString(undefined,{month:'short',day:'numeric'})};
const moneyUnit=(v,u)=>num(v)===null?'—':money(v)+(u?' / '+esc(u):'');
const qtyUnit=(v,u,d=1)=>num(v)===null?'—':fmt(v,d)+(u?' '+esc(u):'');
const days=v=>num(v)===null?'—':fmt(v,1)+' days';
const pct=v=>num(v)===null?'—':fmt(Number(v)*100,1)+'%';
let currentUpc=null,loadedOH=false,loadedPrice=false;

function setStatus(text,bad=false){$('status').textContent=text;$('status').className='msg'+(bad?' error':'')}
async function api(path,opts={}){
  const r=await fetch(path,opts);let body=null;try{body=await r.json()}catch{}
  if(!r.ok){const detail=body?.detail;throw new Error(typeof detail==='string'?detail:(detail?.reason||('HTTP '+r.status)))}
  return body;
}
function pill(status){
  const s=String(status||'UNKNOWN');const cls=s==='READY'||s==='COVERAGE_AVAILABLE'?'ok':(s==='QA_HOLD'||s==='BLOCKED'||s==='COUNT_REQUIRED'?'bad':'warn');
  return '<span class="pill '+cls+'">'+esc(s)+'</span>';
}
function trendHtml(t,kind,uom){
  if(!t||!t.direction||t.direction==='NA'||t.delta===null||t.delta===undefined)return '';
  const dir=t.direction,arrow=dir==='UP'?'▲':(dir==='DOWN'?'▼':'•'),cls=dir==='UP'?'tr-up':(dir==='DOWN'?'tr-down':'tr-flat');
  let delta=Number(t.delta);
  let val='—';
  if(kind==='money')val=(delta>=0?'+':'')+money(delta)+(uom?' / '+esc(uom):'');
  else if(kind==='pct')val=(delta>=0?'+':'')+fmt(delta*100,1)+' pts';
  else if(kind==='qty')val=(delta>=0?'+':'')+fmt(delta,1)+(uom?' '+esc(uom):'');
  else if(kind==='velocity')val=(delta>=0?'+':'')+fmt(delta,2)+(uom?' '+esc(uom)+'/day':'/day');
  else val=(delta>=0?'+':'')+fmt(delta,2);
  return '<div class="trend '+cls+'">'+arrow+' '+val+' <span class="small">vs prior 7D</span></div>';
}
function metric(k,v,trend){return '<div class="metric"><div class="k">'+esc(k)+'</div><div class="v">'+v+'</div>'+(trend||'')+'</div>'}
function invCell(k,v,cls){return '<div class="inv-cell"><div class="k">'+esc(k)+'</div><div class="v '+(cls||'')+'">'+v+'</div></div>'}

function switchTab(tab){
  document.querySelectorAll('.module').forEach(x=>x.classList.add('hidden'));
  $('mod-'+tab).classList.remove('hidden');
  document.querySelectorAll('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
  window.scrollTo({top:0,behavior:'smooth'});
  if(tab==='oh'&&!loadedOH)loadOH();
  if(tab==='price'&&!loadedPrice)loadPrice();
}
document.querySelectorAll('.nav button').forEach(b=>b.addEventListener('click',()=>switchTab(b.dataset.tab)));

async function search(){
  const q=$('q').value.trim();if(!q)return;
  setStatus('Searching…');$('detail').classList.add('hidden');$('results').innerHTML='';
  try{
    const d=await api('/v1/app/quick-check/search?q='+encodeURIComponent(q)+'&limit=20');
    setStatus(d.count+' result(s)');
    $('results').innerHTML=(d.results||[]).map(r=>
      '<div class="card result" data-upc="'+esc(r.ean_upc)+'">'+
      '<div class="row" style="justify-content:space-between"><div class="name">'+esc(r.selling_description||r.family_description||r.ean_upc)+'</div>'+pill(r.quick_check_status)+'</div>'+
      '<div class="meta">UPC '+esc(r.ean_upc)+' · Article '+esc(r.article_number)+' · Family '+esc(r.main_article_number||r.family_id)+'</div>'+
      '<div class="meta">'+moneyUnit(r.current_price,r.selling_uom)+' · OH '+qtyUnit(r.current_oh,r.current_oh_uom)+'</div></div>'
    ).join('');
    document.querySelectorAll('.result').forEach(el=>el.addEventListener('click',()=>loadDetail(el.dataset.upc)));
  }catch(e){setStatus(e.message,true)}
}

function salesChart(rows,uom){
  const data=(rows||[]).filter(r=>r.business_date);
  if(!data.length)return '<div class="empty">No canonical daily sales trend available.</div>';
  const w=Math.max(780,90+data.length*30),h=250,l=42,r=54,t=34,b=34,plotW=w-l-r,plotH=h-t-b;
  const gps=data.map(x=>num(x.gp_dollars)).filter(x=>x!==null);
  const prices=data.map(x=>num(x.avg_sold_price)).filter(x=>x!==null);
  const gpMax=Math.max(1,...gps,0)*1.16;
  const pMin=prices.length?Math.max(0,Math.min(...prices)*.92):0;
  const pMax=prices.length?Math.max(pMin+1,Math.max(...prices)*1.08):1;
  const step=plotW/data.length,barW=Math.max(8,Math.min(20,step*.62));
  const x=i=>l+step*i+step/2;
  const yg=v=>t+plotH-(Math.max(0,v)/gpMax)*plotH;
  const yp=v=>t+plotH-((v-pMin)/(pMax-pMin))*plotH;
  let s='<div class="chart-scroll"><svg viewBox="0 0 '+w+' '+h+'" style="width:'+w+'px;min-width:'+w+'px" role="img" aria-label="GP dollars bars and average selling price line">';
  s+='<line x1="'+l+'" y1="'+(t+plotH)+'" x2="'+(w-r)+'" y2="'+(t+plotH)+'" stroke="rgba(90,125,145,.45)"/>';
  for(let g=0;g<=4;g++){const v=gpMax*g/4,y=yg(v);s+='<line x1="'+l+'" y1="'+y+'" x2="'+(w-r)+'" y2="'+y+'" stroke="rgba(90,125,145,.13)"/><text x="'+(l-5)+'" y="'+(y+3)+'" text-anchor="end" font-size="9" fill="currentColor">'+fmt(v,0)+'</text>'}
  let points=[];
  data.forEach((d,i)=>{
    const gp=num(d.gp_dollars),p=num(d.avg_sold_price),cx=x(i);
    if(gp!==null){
      const y=yg(gp),bh=t+plotH-y;
      s+='<rect x="'+(cx-barW/2)+'" y="'+y+'" width="'+barW+'" height="'+bh+'" rx="2" fill="var(--blue)" opacity=".83"/>';
      s+='<text x="'+cx+'" y="'+Math.max(10,y-4)+'" text-anchor="middle" font-size="8" font-weight="700" fill="var(--blue)">'+fmt(gp,0)+'</text>';
    }
    if(p!==null)points.push([cx,yp(p),p]);
    if(i===0||i===data.length-1||i%7===0)s+='<text x="'+cx+'" y="'+(h-10)+'" text-anchor="middle" font-size="9" fill="currentColor">'+esc(dateLabel(d.business_date))+'</text>';
  });
  if(points.length){
    s+='<polyline points="'+points.map(p=>p[0]+','+p[1]).join(' ')+'" fill="none" stroke="var(--orange)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>';
    points.forEach(p=>{
      s+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="3.2" fill="var(--orange)"/>';
      s+='<text x="'+p[0]+'" y="'+Math.min(h-b-3,p[1]+13)+'" text-anchor="middle" font-size="8" font-weight="700" fill="var(--orange)">'+fmt(p[2],2)+'</text>';
    });
  }
  s+='<text x="4" y="13" font-size="9" fill="currentColor">GP$</text><text x="'+(w-3)+'" y="13" text-anchor="end" font-size="9" fill="var(--orange)">Price $/'+esc(uom||'unit')+'</text>';
  s+='<text x="'+(w-r+5)+'" y="'+(t+4)+'" font-size="9" fill="var(--orange)">'+fmt(pMax,2)+'</text><text x="'+(w-r+5)+'" y="'+(t+plotH)+'" font-size="9" fill="var(--orange)">'+fmt(pMin,2)+'</text>';
  s+='</svg></div>';
  return s;
}

async function loadDetail(upc){
  currentUpc=upc;setStatus('Loading '+upc+'…');
  try{
    const d=await api('/v1/app/quick-check/'+encodeURIComponent(upc));
    const x=d.item||{},eff=d.effective_oh||{},sys=d.system_oh||{},promo=d.promotion||{},ord=d.ordering||{},tr=d.metric_trends||{};
    const uom=x.selling_uom||'unit',ohUom=eff.uom||sys.uom||x.current_oh_uom||uom;
    $('itemName').textContent=x.selling_description||x.family_description||x.ean_upc;
    $('itemMeta').textContent='Family '+(x.main_article_number||x.family_id||'—')+' · Article '+(x.article_number||'—')+' · UPC '+(x.ean_upc||'—');
    $('itemStatus').innerHTML=pill(x.quick_check_status);
    $('itemBadges').innerHTML='<span class="pill '+(String(x.product_class||'').toUpperCase()==='FRESH'?'ok':'')+'">'+esc(x.product_class||'ITEM')+'</span><span class="pill">'+esc(x.current_price_type||promo.classification||'—')+'</span>';

    $('metrics').innerHTML=[
      metric('Price',moneyUnit(x.current_price,uom),trendHtml(tr.price,'money',uom)),
      metric('Cost',moneyUnit(x.current_cost_per_selling_unit,uom),trendHtml(tr.cost,'money',uom)),
      metric('GP%',pct(x.gp_pct_current),trendHtml(tr.gp_pct,'pct')),
      metric('GP$/Day',num(x.gp_per_day_7d)===null?'—':money(x.gp_per_day_7d)+' / day',trendHtml(tr.gp_per_day,'money','day')),
      metric('7D Qty',qtyUnit(x.pos_qty_7d,uom,1)+' / 7D',trendHtml(tr.qty_7d,'qty',uom)),
      metric('Velocity',num(x.upc_velocity_7d)===null?'—':fmt(x.upc_velocity_7d,2)+' '+esc(uom)+' / day',trendHtml(tr.velocity,'velocity',uom)),
      metric('DOS',days(ord.days_supply??x.dos),''),
      metric('DOH',days(x.doh),'')
    ].join('');

    const hist=d.price_velocity_history||[];
    $('priceVelocityRows').innerHTML=hist.map(r=>
      '<tr><td>'+esc(dateLabel(r.last_date))+'</td><td>'+moneyUnit(r.price,uom)+'</td><td>'+fmt(r.velocity,2)+' '+esc(uom)+'/day</td><td>'+((num(r.gp_per_day)===null)?'—':money(r.gp_per_day)+'/day')+'</td></tr>'
    ).join('')||'<tr><td colspan="4">No price/velocity history.</td></tr>';

    const sweet=x.sweet_spot_price??d.sweet_spot?.price;
    $('sweetSpotPrice').innerHTML=num(sweet)===null?'—':moneyUnit(sweet,uom);
    const sweetDelta=(num(sweet)!==null&&num(x.current_price)!==null)?Number(sweet)-Number(x.current_price):null;
    $('sweetSpotNote').innerHTML=num(sweet)===null
      ?'Not enough validated historical price/cost observations to calculate a sweet spot.'
      :'Canonical 30 completed POS-data-day sweet spot: price with the highest historical average GP$/data day.'+
       (sweetDelta===null?'':'<br><b>'+(sweetDelta===0?'Matches current price.':((sweetDelta>0?'▲ ':'▼ ')+money(Math.abs(sweetDelta))+' / '+esc(uom)+' vs current'))+'</b>');

    const active=d.active_true_stock||{},trueQty=active.true_stock_quantity;
    const diff=(num(sys.quantity)!==null&&num(eff.quantity)!==null)?Number(eff.quantity)-Number(sys.quantity):null;
    $('inventoryStats').innerHTML=[
      invCell('System OH',qtyUnit(sys.quantity,sys.uom||ohUom,1)),
      invCell('True Stock',qtyUnit(trueQty,active.uom_code||ohUom,1),num(trueQty)!==null?'tr-up':''),
      invCell('Effective OH',qtyUnit(eff.quantity,ohUom,1)),
      invCell('Difference',num(diff)===null?'—':((diff>0?'+':'')+fmt(diff,1)+' '+esc(ohUom)),diff<0?'bad':(diff>0?'ok':''))
    ].join('');
    $('trueStockUom').value=d.true_stock_input?.required_uom||ohUom||'';
    $('trueStock').value='';
    $('trueStockMsg').className='msg';$('trueStockMsg').textContent='';

    $('ordering').innerHTML=
      '<div class="kv">'+
      '<div class="k">Status</div><div class="v">'+esc(ord.status||'—')+'</div>'+
      '<div class="k">Suggested Qty</div><div class="v">'+qtyUnit(ord.suggested_order_qty,ord.suggested_order_uom||uom,1)+'</div>'+
      '<div class="k">Next Order</div><div class="v">'+esc(ord.next_order_date||'—')+'</div>'+
      '<div class="k">Delivery</div><div class="v">'+esc(ord.next_delivery_date||'—')+'</div>'+
      '<div class="k">Coverage</div><div class="v">'+days(ord.coverage_days_after_delivery)+'</div>'+
      '<div class="k">Effective DOS</div><div class="v">'+days(ord.days_supply??ord.effective_dos?.days_supply)+'</div>'+
      '</div><div class="small" style="margin-top:5px">'+esc(ord.reason||'')+'</div>';

    $('salesChart').innerHTML=salesChart(d.daily_sales_trend||[],uom);

    const rel=d.family_relationships||{},fam=rel.family||{};
    $('familyMeta').textContent='Main Article '+(fam.main_article_number||x.main_article_number||'—')+' · '+(fam.family_description||x.family_description||'');
    $('familyArticles').textContent='Articles: '+((rel.articles||[]).map(a=>(a.article_number||'—')+' ['+(a.relationship_type||'')+']').join(', ')||'—');
    $('receivingArticles').textContent='Receiving: '+((rel.receiving_articles_observed||[]).map(a=>(a.article_number||'—')+' · '+(a.receiving_uoms||'')+' · '+(a.latest_receipt_date||'—')).join(' | ')||'—');
    $('relatedRows').innerHTML=(d.related_upcs||[]).map(r=>
      '<tr><td>'+esc(r.ean_upc)+'</td><td>'+esc(r.selling_description)+'</td><td>'+esc(r.selling_uom||'')+'</td><td>'+moneyUnit(r.current_price,r.selling_uom||'')+'</td><td>'+qtyUnit(r.pos_qty_7d,r.selling_uom||'',1)+'</td><td>'+pill(r.quick_check_status)+'</td></tr>'
    ).join('');

    $('highlights').innerHTML=(d.highlights||[]).map(h=>'<div class="hl"><b>'+esc(h.code)+'</b><div class="small">'+esc(h.text)+'</div></div>').join('')||'<div class="small">No current highlights.</div>';
    $('costRows').innerHTML=(d.cost_trend||[]).slice(0,20).map(r=>'<tr><td>'+esc(r.business_date||'')+'</td><td>'+esc(r.source_type||'')+'</td><td>'+moneyUnit(r.cost_per_base_uom??r.cost_amount,r.base_uom||r.cost_uom||'')+'</td><td>'+esc(r.base_uom||r.cost_uom||'')+'</td><td>'+esc(r.article_number||'')+'</td></tr>').join('');

    $('detail').classList.remove('hidden');
    setStatus('Loaded '+upc+' · '+(tr.basis||d.contract_version||''));
    $('detail').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){setStatus(e.message,true)}
}

async function submitTrueStock(){
  if(!currentUpc)return;
  const qty=$('trueStock').value.trim(),uom=$('trueStockUom').value.trim();
  if(qty===''||!uom){$('trueStockMsg').textContent='True Stock and UOM are required.';return}
  $('trueStockMsg').textContent='Submitting…';
  try{
    const r=await api('/v1/app/quick-check/'+encodeURIComponent(currentUpc)+'/true-stock',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:qty,uom})
    });
    const saved='Saved · discrepancy '+qtyUnit(r.discrepancy,r.uom,1)+' · OH report '+(r.dumping_queue_action||'NONE');
    loadedOH=false;await loadDetail(currentUpc);
    $('trueStockMsg').className='msg ok';$('trueStockMsg').textContent=saved;
  }catch(e){$('trueStockMsg').textContent=e.message;$('trueStockMsg').className='msg error'}
}

async function openQuickCheck(upc){if(!upc)return;switchTab('quick');$('q').value=upc;$('results').innerHTML='';await loadDetail(upc)}

async function loadOH(){
  $('ohStatus').textContent='Loading discrepancies…';$('ohList').innerHTML='';$('ohHistoryList').innerHTML='';
  const hs=$('ohHistoryFilter').value;
  const hp='/v1/app/dumping/history?limit=80'+(hs?'&status='+encodeURIComponent(hs):'');
  try{
    const [d,h]=await Promise.all([api('/v1/app/dumping/pending'),api(hp)]);
    loadedOH=true;
    $('ohStatus').textContent=(d.count??(d.rows||[]).length)+' pending discrepancy item(s)';
    $('ohHistoryStatus').textContent=h.count+' history item(s)';
    $('ohList').innerHTML=(d.rows||[]).map(r=>
      '<div class="card compact" data-open-upc="'+esc(r.ean_upc||'')+'">'+
      '<div class="row" style="justify-content:space-between"><div class="name">Family '+esc(r.main_article_number||r.family_id||'—')+'</div><span class="pill warn">'+esc(r.queue_status||'PENDING')+'</span></div>'+
      '<div class="meta">UPC '+esc(r.ean_upc||'—')+' · Article '+esc(r.article_number||'—')+'</div>'+
      '<div class="kv"><div class="k">System OH</div><div class="v">'+qtyUnit(r.system_oh_quantity,r.uom_code,1)+'</div><div class="k">True Stock</div><div class="v">'+qtyUnit(r.true_stock_quantity,r.uom_code,1)+'</div><div class="k">OH Discrepancy</div><div class="v bad">'+qtyUnit(r.discrepancy_quantity,r.uom_code,1)+'</div></div>'+
      '<div class="row" style="margin-top:7px;justify-content:flex-end"><button class="smallbtn danger resolveOH" data-id="'+esc(r.discrepancy_id)+'">Clear Report</button></div></div>'
    ).join('')||'<div class="card compact empty">No pending OH discrepancies.</div>';
    $('ohHistoryList').innerHTML=(h.rows||[]).map(r=>
      '<div class="card compact" data-open-upc="'+esc(r.ean_upc||'')+'"><div class="row" style="justify-content:space-between"><div class="name">Family '+esc(r.main_article_number||r.family_id||'—')+'</div>'+pill(r.queue_status)+'</div>'+
      '<div class="meta">UPC '+esc(r.ean_upc||'—')+' · '+qtyUnit(r.system_oh_quantity,r.uom_code,1)+' → '+qtyUnit(r.true_stock_quantity,r.uom_code,1)+' · Δ '+qtyUnit(r.discrepancy_quantity,r.uom_code,1)+'</div></div>'
    ).join('')||'<div class="card compact empty">No matching history.</div>';
    bindOpenCards('ohList');bindOpenCards('ohHistoryList');
    $('ohList').querySelectorAll('.resolveOH').forEach(btn=>btn.addEventListener('click',e=>{e.stopPropagation();resolveOH(btn.dataset.id,btn)}));
  }catch(e){$('ohStatus').textContent=e.message;$('ohStatus').className='msg error'}
}

async function resolveOH(id,btn){
  if(!id)return;
  if(!window.confirm('Clear this OH discrepancy report? This closes the report only and does not change inventory.'))return;
  btn.disabled=true;btn.textContent='Clearing…';
  try{
    await api('/v1/app/dumping/'+encodeURIComponent(id)+'/resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:'RESOLVE_DUMPING_DISCREPANCY'})});
    loadedOH=false;await loadOH();
  }catch(e){$('ohStatus').textContent=e.message;$('ohStatus').className='msg error';btn.disabled=false;btn.textContent='Clear Report'}
}

async function previewPrice(upc,inputId,outputId){
  const input=$(inputId),out=$(outputId),raw=input?.value?.trim();
  if(!raw){out.textContent='Enter a proposed price.';out.className='msg error';return}
  out.textContent='Calculating…';out.className='msg';
  try{
    const d=await api('/v1/app/price-change/'+encodeURIComponent(upc)+'/preview?proposed_price='+encodeURIComponent(raw));
    const x=d.impact||{},u=d.item?.selling_uom||'unit';
    out.className='card notice compact';
    out.innerHTML='<div class="kv"><div class="k">Proposed Price</div><div class="v">'+moneyUnit(x.proposed_price,u)+'</div><div class="k">Proposed GP%</div><div class="v">'+pct(x.proposed_gp_pct)+'</div><div class="k">Projected GP$/day</div><div class="v">'+money(x.projected_gp_per_day_7d)+' / day</div><div class="k">GP$/day Delta</div><div class="v">'+money(x.projected_gp_per_day_delta)+' / day</div></div>';
  }catch(e){out.textContent=e.message;out.className='msg error'}
}

async function loadPrice(){
  $('priceStatus').textContent='Loading price review…';$('priceList').innerHTML='';
  try{
    const d=await api('/v1/app/price-change?limit=160');loadedPrice=true;
    $('priceStatus').textContent=d.count+' item(s) · '+esc(d.mode||'');
    $('priceList').innerHTML=(d.rows||[]).map((r,idx)=>{
      const inputId='priceInput_'+idx,outputId='pricePreview_'+idx,u=r.selling_uom||'unit';
      return '<div class="card compact" data-open-upc="'+esc(r.ean_upc)+'">'+
        '<div class="row" style="justify-content:space-between"><div class="name">'+esc(r.selling_description||r.ean_upc)+'</div>'+pill(r.quick_check_status)+'</div>'+
        '<div class="meta">UPC '+esc(r.ean_upc)+' · '+moneyUnit(r.current_price,u)+' · '+esc(r.current_price_type||'')+'</div>'+
        '<div class="kv"><div class="k">Cost</div><div class="v">'+moneyUnit(r.current_cost_per_selling_unit,u)+'</div><div class="k">GP%</div><div class="v">'+pct(r.gp_pct_current)+'</div><div class="k">Velocity</div><div class="v">'+fmt(r.upc_velocity_7d,2)+' '+esc(u)+'/day</div><div class="k">Sweet Spot</div><div class="v">'+moneyUnit(r.sweet_spot_price,u)+'</div></div>'+
        '<div class="row" style="margin-top:7px"><input id="'+inputId+'" class="priceInput" inputmode="decimal" placeholder="What-if price" value="'+esc(r.current_price??'')+'"><button class="smallbtn previewPriceBtn" data-upc="'+esc(r.ean_upc)+'" data-input="'+inputId+'" data-output="'+outputId+'">Preview</button></div>'+
        '<div id="'+outputId+'" class="msg"></div></div>';
    }).join('')||'<div class="card compact empty">No active price review rows.</div>';
    bindOpenCards('priceList');
    $('priceList').querySelectorAll('.previewPriceBtn').forEach(btn=>btn.addEventListener('click',e=>{e.stopPropagation();previewPrice(btn.dataset.upc,btn.dataset.input,btn.dataset.output)}));
    $('priceList').querySelectorAll('.priceInput').forEach(input=>input.addEventListener('click',e=>e.stopPropagation()));
  }catch(e){$('priceStatus').textContent=e.message;$('priceStatus').className='msg error'}
}

function bindOpenCards(containerId){$(containerId).querySelectorAll('[data-open-upc]').forEach(el=>el.addEventListener('click',()=>{const upc=el.dataset.openUpc;if(upc)openQuickCheck(upc)}))}

$('search').addEventListener('click',search);
$('q').addEventListener('keydown',e=>{if(e.key==='Enter')search()});
$('submitTrueStock').addEventListener('click',submitTrueStock);
$('refreshOH').addEventListener('click',()=>{loadedOH=false;loadOH()});
$('ohHistoryFilter').addEventListener('change',()=>{loadedOH=false;loadOH()});
$('refreshPrice').addEventListener('click',()=>{loadedPrice=false;loadPrice()});
</script>
</body>
</html>"""


def quick_check_web_html() -> str:
    return QUICK_CHECK_WEB_HTML
