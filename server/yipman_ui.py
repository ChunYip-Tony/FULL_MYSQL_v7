from __future__ import annotations

import json


def yipman_html(version: str = "") -> str:
    return YIPMAN_HTML.replace("__VERSION__", str(version or ""))


def yipman_manifest() -> str:
    return json.dumps({
        "name": "Yipman",
        "short_name": "Yipman",
        "id": "/app/yipman",
        "start_url": "/app/yipman",
        "scope": "/app/yipman/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "background_color": "#f6f7f9",
        "theme_color": "#0d4f8b",
        "description": "FULL MYSQL seafood mobile operations",
        "icons": [{
            "src": "/app/yipman/icon.svg",
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable",
        }],
    }, separators=(",", ":"))


def yipman_service_worker() -> str:
    return r"""
const CACHE='yipman-v1';
const SHELL=['/app/yipman','/app/yipman/manifest.webmanifest','/app/yipman/icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  if(u.pathname.startsWith('/v1/'))return;
  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/app/yipman'))));
});
"""


def yipman_icon_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="112" fill="#0d4f8b"/><path d="M0 382h512v130H0z" fill="#d62828"/><path d="M143 112h72l43 91 43-91h70l-81 151v104h-66V263z" fill="#fff"/></svg>"""


YIPMAN_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#0d4f8b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Yipman">
<link rel="manifest" href="/app/yipman/manifest.webmanifest">
<link rel="icon" href="/app/yipman/icon.svg" type="image/svg+xml">
<title>Yipman</title>
<style>
:root{--bg:#f6f7f9;--paper:#fff;--ink:#16202a;--muted:#71808d;--line:#e1e6ea;--blue:#0d4f8b;--blue2:#1d6fb8;--red:#d62828;--redbg:#fff0f0;--green:#25734a;--greenbg:#edf8f2;--amber:#966700;--amberbg:#fff8e5;--shadow:0 9px 25px rgba(18,38,56,.08)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;overscroll-behavior-y:contain}
body{overflow:hidden}button,input{font:inherit;color:inherit}button{cursor:pointer}.hide{display:none!important}
#app{height:100%;position:relative;overflow:hidden;padding-top:env(safe-area-inset-top)}
.header{padding:9px 13px 10px}.head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.brand{font-size:21px;font-weight:950;letter-spacing:-.04em}.brand span{color:var(--blue)}.ver{display:block;font-size:9px;color:var(--muted);font-weight:700;margin-top:1px}
.dbbtn{width:40px;height:40px;border:0;border-radius:14px;background:#fff;box-shadow:var(--shadow);font-size:18px}
.search{display:flex;align-items:center;margin-top:9px;background:#fff;border:1px solid var(--line);border-radius:15px;padding:0 10px;box-shadow:0 4px 15px rgba(18,38,56,.04)}
.search span{font-size:17px;color:#657581}.search input{flex:1;min-width:0;border:0;outline:0;background:transparent;padding:11px 8px;font-size:16px}
.workspace{height:calc(100% - 99px);position:relative;overflow:hidden}.page{display:none;height:100%;overflow-y:auto;padding:0 11px calc(82px + env(safe-area-inset-bottom));scrollbar-width:none}.page::-webkit-scrollbar{display:none}.page.on{display:block}
#home{overflow:hidden}.topline{display:flex;justify-content:space-between;align-items:end;margin:0 1px 7px}.topline h2{font-size:18px;margin:0}.hint{font-size:9px;color:var(--muted);font-weight:850}
.hero{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;border-radius:18px;padding:11px 12px;box-shadow:var(--shadow)}.hero small{font-size:8px;font-weight:900;letter-spacing:.08em;opacity:.8}.hero h3{font-size:18px;margin:3px 0 2px}.hero p{font-size:9px;line-height:1.25;margin:0;opacity:.85}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px}.stat{padding:7px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.11);border-radius:10px}.stat b{display:block;font-size:15px}.stat span{font-size:7px;opacity:.8}
.launch{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.launch button{min-height:86px;border:0;border-radius:15px;background:#fff;padding:9px 10px;text-align:left;box-shadow:var(--shadow)}.launch button:nth-child(2),.launch button:nth-child(3){background:linear-gradient(180deg,#fff7f7,#fff)}.launch i{font-style:normal;font-size:17px}.launch b{display:block;font-size:13px;margin-top:5px}.launch span{display:block;font-size:8px;color:var(--muted);margin-top:2px}.launch em{display:block;font-style:normal;font-size:7px;font-weight:900;color:var(--blue);margin-top:5px}
.priority{margin-top:8px;background:#fff;border-radius:15px;box-shadow:var(--shadow);overflow:hidden}.priority .ph{display:flex;justify-content:space-between;padding:7px 10px;border-bottom:1px solid var(--line);font-size:8px;font-weight:900;color:#53616d}.prio{display:grid;grid-template-columns:1fr auto;gap:8px;padding:8px 10px;border-bottom:1px solid var(--line)}.prio:last-child{border:0}.prio b{font-size:11px}.prio span{display:block;font-size:8px;color:var(--muted);margin-top:2px}
.badge{align-self:center;border-radius:999px;padding:4px 6px;font-size:7px;font-weight:900}.red{background:var(--redbg);color:var(--red)}.amber{background:var(--amberbg);color:var(--amber)}.green{background:var(--greenbg);color:var(--green)}
.search2{display:grid;grid-template-columns:1fr 70px;gap:6px;margin-bottom:8px}.search2 input{border:1px solid var(--line);background:#fff;border-radius:13px;padding:10px 11px;font-size:16px;outline:0}.search2 button{border:0;background:var(--blue);color:#fff;border-radius:13px;font-size:9px;font-weight:900}
.group{background:#fff;border-radius:16px;box-shadow:var(--shadow);overflow:hidden;margin-bottom:8px}.ghead{display:flex;justify-content:space-between;gap:8px;padding:11px 12px;background:#fafbfc}.ghead b{font-size:14px}.ghead small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.gmetric{text-align:right;font-size:12px;font-weight:900}.gmetric span{display:block;font-size:7px;color:var(--muted)}
.upc{display:grid;grid-template-columns:1fr auto;gap:8px;padding:10px 12px;border-top:1px solid var(--line)}.upc b{font-size:11px}.upc small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.upcv{text-align:right;font-size:10px;font-weight:900}
.empty{background:#fff;border-radius:16px;padding:20px;text-align:center;font-size:10px;color:var(--muted);box-shadow:var(--shadow)}
.daybar{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px;margin-bottom:8px}.daybar::-webkit-scrollbar{display:none}.day{min-width:49px;border:0;border-radius:14px;background:#fff;padding:8px 4px;box-shadow:0 4px 12px rgba(18,38,56,.05);text-align:center}.day b{display:block;font-size:8px;color:var(--muted)}.day strong{display:block;font-size:17px;margin-top:1px}.day span{display:block;font-size:7px;color:var(--muted)}.day.on{background:var(--blue);color:#fff}.day.on b,.day.on span{color:#dbeafa}
.list{background:#fff;border-radius:16px;box-shadow:var(--shadow);overflow:hidden}.lh,.orow{display:grid;grid-template-columns:1fr 58px 64px;padding:0 11px}.lh{background:#eef2f5;padding-top:8px;padding-bottom:8px;font-size:7px;font-weight:900;color:#5d6974}.orow{border-top:1px solid var(--line)}.orow>div{padding:10px 0}.orow .name{font-size:11px;font-weight:900}.orow .sub{font-size:7px;color:var(--muted);margin-top:2px}.cell{text-align:right;font-size:11px;font-weight:900}.cell span{display:block;font-size:7px;color:var(--muted)}.orow.urgent{box-shadow:inset 4px 0 0 var(--red)}
.filters{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;margin-bottom:8px}.filters::-webkit-scrollbar{display:none}.pill{border:0;border-radius:999px;background:#fff;padding:7px 10px;font-size:8px;font-weight:900;color:#5e6a75;white-space:nowrap}.pill.on{background:#1f2c38;color:#fff}
.pricecards{display:grid;gap:7px}.pcard{background:#fff;border-radius:16px;padding:11px 12px;box-shadow:var(--shadow)}.ptop{display:flex;justify-content:space-between;gap:8px}.ptop b{font-size:12px}.ptop small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.compare{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:7px;margin-top:9px}.pbox{background:#f5f7f9;border-radius:11px;padding:8px}.pbox b{font-size:16px}.pbox span{display:block;font-size:7px;color:var(--muted)}.arrow{font-size:15px;font-weight:900;color:#98a3ac}.why{font-size:8px;line-height:1.35;color:#5d6974;margin-top:8px}
.datagrid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.dcard{background:#fff;border-radius:16px;padding:10px;box-shadow:var(--shadow)}.dcard h3{font-size:10px;margin:0 0 7px}.pipe{display:grid;grid-template-columns:repeat(4,1fr);gap:3px}.stage{padding:6px 2px;text-align:center;background:#f1f4f6;border-radius:8px;border-top:4px solid #8d99a3}.stage b{display:block;font-size:6px}.stage span{font-size:6px;color:var(--muted)}.stage.ok{border-top-color:var(--green)}.stage.warn{border-top-color:#d19a00}.stage.bad{border-top-color:var(--red)}.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.c{text-align:center;font-size:7px}.dot{width:12px;height:12px;border-radius:50%;background:var(--green);margin:3px auto 0}.dot.warn{background:#d19a00}.dot.bad{background:var(--red)}.batchrow{display:grid;grid-template-columns:1fr auto;gap:6px;padding:8px 0;border-top:1px solid var(--line)}.batchrow b{font-size:9px}.batchrow span{display:block;font-size:7px;color:var(--muted);margin-top:2px}
.nav{position:absolute;left:10px;right:10px;bottom:calc(9px + env(safe-area-inset-bottom));height:57px;display:grid;grid-template-columns:repeat(5,1fr);background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:18px;box-shadow:0 9px 24px rgba(18,38,56,.12);backdrop-filter:blur(10px);z-index:10}.nav button{border:0;background:transparent;color:#73808a;font-size:7px;font-weight:850}.nav i{display:block;font-style:normal;font-size:16px;margin-bottom:2px}.nav button.on{color:var(--blue)}
.overlay{position:absolute;inset:0;background:rgba(15,25,34,.34);display:none;align-items:flex-end;z-index:30}.overlay.on{display:flex}.sheet{width:100%;max-height:68%;overflow:auto;background:#f7f8fa;border-radius:23px 23px 0 0}.shead{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:12px 13px;display:flex;justify-content:space-between;gap:8px;border-radius:23px 23px 0 0}.shead h3{font-size:17px;margin:0}.shead p{font-size:8px;color:var(--muted);margin:2px 0 0}.close{width:34px;height:34px;border:0;border-radius:11px;background:#eef1f3;font-size:17px}.sbody{padding:9px 11px 13px}.dmetrics{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.dm{background:#fff;border-radius:12px;padding:9px}.dm b{font-size:14px;display:block}.dm span{font-size:7px;color:var(--muted)}.detail{background:#fff;border-radius:12px;padding:9px;margin-top:6px;font-size:9px;line-height:1.4;color:#53616d}.actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:7px}.actions button{border:0;border-radius:11px;padding:9px;font-size:8px;font-weight:900}.primary{background:var(--blue);color:#fff}.secondary{background:#e6ebef;color:#2f3e49}
.toast{position:absolute;left:12px;right:12px;bottom:76px;background:#1f2d39;color:#fff;padding:9px 11px;border-radius:13px;font-size:9px;font-weight:850;display:none;z-index:40}.toast.on{display:block}
.ptr{position:absolute;left:0;right:0;top:0;height:0;overflow:hidden;z-index:50;display:flex;align-items:flex-end;justify-content:center;pointer-events:none}.ptr div{background:#fff;border:1px solid var(--line);box-shadow:var(--shadow);border-radius:999px;padding:6px 10px;margin-bottom:6px;font-size:9px;font-weight:900;color:var(--blue)}
.loading{padding:18px;text-align:center;color:var(--muted);font-size:9px}
@media(max-height:760px){#home .hero p{display:none}.launch button{min-height:74px}.launch button span{display:none}.priority .prio:nth-child(n+4){display:none}}
</style>
</head>
<body>
<div id="app">
  <div class="ptr" id="ptr"><div id="ptrText">Pull to refresh</div></div>
  <header class="header">
    <div class="head"><div><div class="brand">Yip<span>man</span></div><span class="ver">FULL MYSQL · __VERSION__</span></div><button class="dbbtn" data-go="data" aria-label="Data Center">▦</button></div>
    <form class="search" id="globalForm"><span>⌕</span><input id="globalInput" placeholder="Search item, UPC, article..." autocomplete="off"></form>
  </header>
  <main class="workspace">
    <section class="page on" id="home">
      <div class="topline"><h2>Today</h2><div class="hint" id="todayLabel">YIPMAN</div></div>
      <div class="hero"><small>SEAFOOD OPERATIONS</small><h3 id="attentionTitle">Loading current work…</h3><p id="attentionSub">Current FULL MYSQL serving data</p><div class="stats"><div class="stat"><b id="homeOrder">—</b><span>ORDER REVIEW</span></div><div class="stat"><b id="homePrice">—</b><span>PRICE ACTIONS</span></div><div class="stat"><b id="homeHealth">—</b><span>DATA HEALTH</span></div></div></div>
      <div class="launch"><button data-go="quick"><i>⌕</i><b>Quick Check</b><span>Family / UPC lookup</span><em>MOST USED</em></button><button data-go="order"><i>▤</i><b>Ordering</b><span>By delivery date</span><em id="orderMini">LOADING</em></button><button data-go="price"><i>$</i><b>Price Review</b><span>Material changes only</span><em id="priceMini">LOADING</em></button><button data-go="data"><i>▦</i><b>Data Center</b><span>Uploads / batches</span><em id="dataMini">LOADING</em></button></div>
      <div class="priority"><div class="ph"><span>NEEDS ATTENTION</span><span>LIVE</span></div><div id="priorityRows"><div class="loading">Loading priorities…</div></div></div>
    </section>

    <section class="page" id="quick"><div class="topline"><h2>Quick Check</h2><div class="hint">CURRENT MODULE DATA</div></div><form class="search2" id="quickForm"><input id="quickInput" placeholder="Search salmon, 240739, UPC…" autocomplete="off"><button>SEARCH</button></form><div id="quickRows"><div class="empty">Search an item to begin.</div></div></section>

    <section class="page" id="order"><div class="topline"><h2>Ordering</h2><div class="hint">UPCOMING 7 DAYS</div></div><div class="daybar" id="dayBar"></div><div id="orderStatus" class="hint" style="margin:0 2px 7px"></div><div class="list"><div class="lh"><div>FAMILY / RECEIVING</div><div>OH</div><div>ORDER</div></div><div id="orderRows"><div class="loading">Choose a delivery day.</div></div></div></section>

    <section class="page" id="price"><div class="topline"><h2>Price Review</h2><div class="hint">ACTIONABLE ONLY</div></div><div class="filters"><button class="pill on" data-cat="ALL">ALL</button><button class="pill" data-cat="FRESH">FRESH</button><button class="pill" data-cat="FROZEN">FROZEN</button><button class="pill" data-cat="LIVE">LIVE</button></div><div id="priceStatus" class="hint" style="margin:0 2px 7px"></div><div class="pricecards" id="priceRows"><div class="loading">Loading price review…</div></div></section>

    <section class="page" id="data"><div class="topline"><h2>Data Center</h2><div class="hint">BACK OFFICE UNCHANGED</div></div><div class="datagrid"><div class="dcard"><h3>Processing Pipeline</h3><div class="pipe" id="pipe"><div class="stage"><b>UPLOAD</b><span>—</span></div><div class="stage"><b>INGEST</b><span>—</span></div><div class="stage"><b>QA</b><span>—</span></div><div class="stage"><b>PUBLISH</b><span>—</span></div></div></div><div class="dcard"><h3>14-Day Completeness</h3><div class="cal" id="calendar"></div></div><div class="dcard"><h3>Current Batch</h3><div id="currentBatch"><div class="loading">Loading…</div></div></div><div class="dcard"><h3>Recent Batches</h3><div id="recentBatches"><div class="loading">Loading…</div></div></div></div></section>

    <nav class="nav"><button class="on" data-go="home"><i>⌂</i>HOME</button><button data-go="quick"><i>⌕</i>QUICK</button><button data-go="order"><i>▤</i>ORDER</button><button data-go="price"><i>$</i>PRICE</button><button data-go="data"><i>▦</i>DATA</button></nav>
    <div class="overlay" id="overlay"><div class="sheet"><div class="shead"><div><h3 id="sheetTitle">Detail</h3><p id="sheetSub"></p></div><button class="close" id="closeSheet">×</button></div><div class="sbody" id="sheetBody"></div></div></div>
    <div class="toast" id="toast"></div>
  </main>
</div>
<script>
(()=>{
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=(v,d=1)=>{const n=num(v);return n===null?'—':n.toLocaleString(undefined,{maximumFractionDigits:d})};
const money=v=>{const n=num(v);return n===null?'—':'$'+n.toFixed(2)};
const iso=d=>d.toISOString().slice(0,10);
const app=$('#app'), pages=$$('.page'), nav=$$('.nav button');
let current='home', priceCat='ALL', orderDate=null, pullStart=null, pull=0;
function toast(t){const n=$('#toast');n.textContent=t;n.classList.add('on');setTimeout(()=>n.classList.remove('on'),1600)}
async function api(url,opt={}){const c=new AbortController(),tm=setTimeout(()=>c.abort(),opt.timeoutMs||18000);try{const r=await fetch(url,{...opt,signal:c.signal,headers:{'Accept':'application/json',...(opt.headers||{})},cache:'no-store'});const text=await r.text();let data={};try{data=text?JSON.parse(text):{}}catch{}if(!r.ok)throw new Error(data?.detail?.reason||data?.detail||text||('HTTP '+r.status));return data}finally{clearTimeout(tm)}}
function go(id){current=id;pages.forEach(p=>p.classList.toggle('on',p.id===id));nav.forEach(b=>b.classList.toggle('on',b.dataset.go===id));const p=$('#'+id);if(p)p.scrollTop=0;if(id==='order'&&!orderDate)loadOrder(0);if(id==='price')loadPrices();if(id==='data')loadData()}
$$('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));
function sheet(title,sub,html){$('#sheetTitle').textContent=title;$('#sheetSub').textContent=sub||'';$('#sheetBody').innerHTML=html;$('#overlay').classList.add('on')}
$('#closeSheet').onclick=()=>$('#overlay').classList.remove('on');$('#overlay').onclick=e=>{if(e.target===$('#overlay'))$('#overlay').classList.remove('on')};

const today=new Date();$('#todayLabel').textContent=today.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'}).toUpperCase();

async function loadHome(){
 try{
  const [h,health]=await Promise.all([api('/v1/backoffice/home-summary',{timeoutMs:10000}),api('/v1/backoffice/data-health?days=14',{timeoutMs:10000})]);
  const oc=num(h?.ordering?.family_count)||0, oa=num(h?.ordering?.attention_count)||0, pc=num(h?.pricing?.qualified_count)||0;
  const due=(health?.rows||[]).filter(x=>x.required_daily_due), complete=due.filter(x=>x.overall_status==='COMPLETE').length;
  const hp=due.length?Math.round(complete/due.length*100):100;
  $('#homeOrder').textContent=oc;$('#homePrice').textContent=pc;$('#homeHealth').textContent=hp+'%';
  $('#orderMini').textContent=oa?oa+' NEED ATTENTION':oc+' TO REVIEW';$('#priceMini').textContent=pc+' ACTIONABLE';$('#dataMini').textContent=hp+'% READY';
  const total=oa+pc+(hp<100?1:0);$('#attentionTitle').textContent=total?total+' actions need attention':'Current work is clear';
  $('#attentionSub').textContent='Current through '+(h?.generated_at||health?.completed_through||'latest data');
  const rows=[];
  if(oa)rows.push({title:'Ordering review',sub:oa+' family item(s) need attention',badge:'ORDER',cls:'red',go:'order'});
  if(pc)rows.push({title:'Price review',sub:pc+' actionable price suggestion(s)',badge:'PRICE',cls:'red',go:'price'});
  if(hp<100)rows.push({title:'Data completeness',sub:(100-hp)+'% of required daily coverage needs attention',badge:'DATA',cls:'amber',go:'data'});
  if(!rows.length)rows.push({title:'No urgent actions',sub:'Use Quick Check for item lookup',badge:'READY',cls:'green',go:'quick'});
  $('#priorityRows').innerHTML=rows.slice(0,3).map(r=>'<div class="prio" data-prio="'+r.go+'"><div><b>'+esc(r.title)+'</b><span>'+esc(r.sub)+'</span></div><div class="badge '+r.cls+'">'+r.badge+'</div></div>').join('');
  $$('[data-prio]').forEach(x=>x.onclick=()=>go(x.dataset.prio));
 }catch(e){$('#attentionTitle').textContent='Home summary unavailable';$('#attentionSub').textContent=e.message;$('#priorityRows').innerHTML='<div class="loading">Pull down to retry.</div>'}
}

function groupRows(rows){
 const map=new Map();
 for(const r of rows){const k=String(r.family_id??r.family_article??r.upc);if(!map.has(k))map.set(k,[]);map.get(k).push(r)}
 return [...map.values()];
}
async function loadQuick(q){
 const box=$('#quickRows');box.innerHTML='<div class="loading">Searching current Quick Check…</div>';
 try{
  const d=await api('/v1/backoffice/inventory?category=ALL&limit=120&lightweight=true&q='+encodeURIComponent(q),{timeoutMs:14000});
  const groups=groupRows(d.rows||[]).slice(0,12);
  if(!groups.length){box.innerHTML='<div class="empty">No matching items.</div>';return}
  box.innerHTML=groups.map(g=>{g.sort((a,b)=>(Number(b.qty_7d||0)-Number(a.qty_7d||0)));const r=g[0], fq=r.family_group_movement_7d??r.family_qty_7d;return '<div class="group"><div class="ghead"><div><b>'+esc(r.family_name||r.name||'Family')+'</b><small>Family '+esc(r.family_article||'—')+' · '+esc(r.category||'')+'</small></div><div class="gmetric">'+fmt(fq)+' '+esc(r.family_group_movement_uom||r.family_qty_uom||'')+'<span>7D FAMILY MVT</span></div></div>'+g.slice(0,6).map(u=>'<div class="upc" data-upc="'+esc(u.upc)+'"><div><b>'+esc(u.name||u.upc)+'</b><small>'+esc(u.upc)+' · '+fmt(u.qty_7d)+' '+esc(u.qty_uom||u.selling_uom||'')+' / 7D</small></div><div class="upcv">'+fmt(u.velocity_7d)+' /day<br>'+esc(u.readiness||'')+'</div></div>').join('')+'</div>'}).join('');
  $$('[data-upc]').forEach(x=>x.onclick=()=>openUpc(x.dataset.upc));
 }catch(e){box.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
$('#quickForm').onsubmit=e=>{e.preventDefault();const q=$('#quickInput').value.trim();if(q)loadQuick(q)};
$('#globalForm').onsubmit=e=>{e.preventDefault();const q=$('#globalInput').value.trim();if(!q)return;$('#quickInput').value=q;go('quick');loadQuick(q);$('#globalInput').blur()};

async function openUpc(upc){
 sheet('Loading…',upc,'<div class="loading">Loading current item detail…</div>');
 try{
  const d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc),{timeoutMs:16000});
  const oh=d.effective_oh||{}, q7=d.qty_7d||{};
  sheet(d.upc_name||upc,(d.upc||upc)+' · Family '+(d.family_article_number||'—'),'<div class="dmetrics"><div class="dm"><b>'+fmt(oh.quantity)+' '+esc(oh.uom||'')+'</b><span>EFFECTIVE OH</span></div><div class="dm"><b>'+fmt(d.upc_velocity_7d)+'</b><span>'+esc(d.qty_uom||d.selling_uom||'UNIT')+' / DAY</span></div><div class="dm"><b>'+money(d.current_price)+'</b><span>CURRENT '+esc(d.current_price_type||'PRICE')+'</span></div></div><div class="detail"><b>7D sales</b><br>'+fmt(q7.sold_quantity)+' '+esc(d.qty_uom||'')+' across '+fmt(q7.supported_day_count,0)+' completed data day(s).<br><br><b>Current price source</b><br>'+esc(d.current_price_source||'—')+(d.current_price_asof_date?' · '+esc(d.current_price_asof_date):'')+'<br><br><b>Current cost</b><br>'+money(d.current_cost_per_selling_unit)+' / '+esc(d.selling_uom||'unit')+'<br><br><b>OH status</b><br>'+esc(oh.status||'—')+(oh.reason?'<br>'+esc(oh.reason):'')+'</div>');
 }catch(e){sheet('Unable to load',upc,'<div class="detail">'+esc(e.message)+'</div>')}
}

function buildDays(){
 const bar=$('#dayBar');bar.innerHTML='';
 for(let i=0;i<7;i++){const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+i);const b=document.createElement('button');b.className='day';b.dataset.offset=i;b.innerHTML='<b>'+d.toLocaleDateString(undefined,{weekday:'short'}).toUpperCase()+'</b><strong>'+d.getDate()+'</strong><span>'+d.toLocaleDateString(undefined,{month:'short'}).toUpperCase()+'</span>';b.onclick=()=>loadOrder(i);bar.appendChild(b)}
}
async function loadOrder(offset){
 const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+offset);orderDate=iso(d);$$('.day').forEach(x=>x.classList.toggle('on',Number(x.dataset.offset)===offset));$('#orderStatus').textContent='Loading '+d.toLocaleDateString(undefined,{weekday:'long',month:'short',day:'numeric'})+'…';$('#orderRows').innerHTML='<div class="loading">Checking receiving cadence and coverage…</div>';
 const url='/v1/backoffice/ordering-review?category=ALL&delivery_date='+orderDate;
 try{
  let data=null;
  for(let i=0;i<10;i++){data=await api(url,{timeoutMs:14000});const s=String(data.analysis_status||'').toUpperCase();if(!['REFRESHING','WARMING','STALE_DATA_REFRESHING'].includes(s)&&!['WARMING','STALE_DATA_REFRESHING'].includes(String(data.cache_status||'').toUpperCase()))break;$('#orderStatus').textContent='Calculating '+orderDate+' · receipt cadence first';await new Promise(r=>setTimeout(r,1500))}
  if(String(data?.analysis_status||'').toUpperCase()==='BLOCKED_STALE_REQUIRED_DATA'){const h=data.data_health||{};$('#orderStatus').textContent='Blocked: required POS/MVT not current';$('#orderRows').innerHTML='<div class="empty">Required through '+esc(h.expected_through||'—')+' · POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'</div>';return}
  const rows=data?.rows||[];$('#orderStatus').textContent=(data.selected_delivery_weekday||'Selected day')+' · '+rows.length+' receiving famil'+(rows.length===1?'y':'ies');
  $('#orderRows').innerHTML=rows.slice(0,12).map((r,i)=>'<div class="orow '+(r.attention?'urgent':'')+'" data-order="'+i+'"><div><div class="name">'+esc(r.family_name||r.family_article||'Family')+'</div><div class="sub">Receiving '+esc(r.receiving_article||'—')+' · '+esc(r.ordering_frequency||'')+'</div></div><div class="cell">'+fmt(r.oh)+'<span>'+esc(r.oh_uom||'')+'</span></div><div class="cell">'+fmt(r.suggested_delivery_qty)+'<span>'+esc(r.suggested_delivery_uom||'')+'</span></div></div>').join('')||'<div class="empty">No eligible receiving families for this delivery date.</div>';
  $$('[data-order]').forEach(x=>x.onclick=()=>openOrder(rows[Number(x.dataset.order)]));
 }catch(e){$('#orderStatus').textContent='Ordering failed';$('#orderRows').innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
function openOrder(r){const d=r.details||{}, reasons=d.reasons||[];sheet(r.family_name||'Ordering','Family '+esc(r.family_article||'—')+' · Delivery '+esc(r.selected_delivery_date||orderDate),'<div class="dmetrics"><div class="dm"><b>'+fmt(r.oh)+' '+esc(r.oh_uom||'')+'</b><span>CURRENT OH</span></div><div class="dm"><b>'+fmt(d.velocity_7d)+'</b><span>7D VELOCITY</span></div><div class="dm"><b>'+fmt(r.suggested_delivery_qty)+' '+esc(r.suggested_delivery_uom||'')+'</b><span>SUGGESTED ORDER</span></div></div><div class="detail"><b>Receiving article</b><br>'+esc(r.receiving_article||'—')+'<br><br><b>Last receipt</b><br>'+esc(r.last_receipt_date||'—')+' · '+fmt(r.last_receipt_qty_base)+' '+esc(r.last_receipt_base_uom||'')+'<br><br><b>Delivery evidence</b><br>'+fmt(r.delivery_day_observed_count,0)+' / '+fmt(r.delivery_day_receipt_count,0)+' observed receipt dates · '+fmt(r.delivery_day_confidence_pct,0)+'% confidence'+(reasons.length?'<br><br><b>Why</b><br>'+reasons.map(x=>'• '+esc(x.detail||x.title||'')).join('<br>'):'')+'</div>')}

async function loadPrices(){
 $('#priceRows').innerHTML='<div class="loading">Loading actionable pricing…</div>';$('#priceStatus').textContent='Current price uses latest valid evidence';
 try{
  const d=await api('/v1/backoffice/pricing-review?category='+encodeURIComponent(priceCat)+'&limit=1000',{timeoutMs:30000}), h=d.data_health||{};
  if(String(h.status||'').includes('BLOCKED')){$('#priceStatus').textContent='Blocked by stale required POS/MVT';$('#priceRows').innerHTML='<div class="empty">Required through '+esc(h.expected_through||'—')+' · POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'</div>';return}
  const rows=(d.rows||[]).filter(r=>r.priority_240_249_mismatch||num(r.price_gap_pct)===null||num(r.price_gap_pct)>=3).slice(0,20);
  $('#priceStatus').textContent=rows.length+' actionable · '+Number(d.suppressed_accepted_count||0)+' accepted hidden';
  $('#priceRows').innerHTML=rows.map((r,i)=>'<div class="pcard" data-price="'+i+'"><div class="ptop"><div><b>'+esc(r.name||r.upc)+'</b><small>'+esc(r.upc)+' · '+esc(r.primary_reason_text||r.review_status||'Pricing review')+'</small></div><div class="badge '+(r.priority_240_249_mismatch?'red':'amber')+'">'+(r.priority_240_249_mismatch?'240≠249':'REVIEW')+'</div></div><div class="compare"><div class="pbox"><b>'+money(r.current_price)+'</b><span>CURRENT</span></div><div class="arrow">→</div><div class="pbox"><b>'+money(r.candidate_price)+'</b><span>SUGGESTED</span></div></div><div class="why">OH '+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+' · DOH '+fmt(r.doh)+' · '+esc(r.current_price_source||'')+'</div></div>').join('')||'<div class="empty">No qualified price changes in the current snapshot.</div>';
  $$('[data-price]').forEach(x=>x.onclick=()=>openPrice(rows[Number(x.dataset.price)]));
 }catch(e){$('#priceStatus').textContent='Price review failed';$('#priceRows').innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
function openPrice(r){sheet(r.name||r.upc,r.upc||'Price review','<div class="dmetrics"><div class="dm"><b>'+money(r.current_price)+'</b><span>CURRENT</span></div><div class="dm"><b>'+money(r.candidate_price)+'</b><span>SUGGESTED</span></div><div class="dm"><b>'+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+'</b><span>OH</span></div></div><div class="detail"><b>Current evidence</b><br>'+esc(r.current_price_source||'—')+(r.current_price_observed_date?' · '+esc(r.current_price_observed_date):'')+'<br><br><b>Reason</b><br>'+esc(r.primary_reason_text||r.review_blocker||'Pricing review')+(Array.isArray(r.reasons)&&r.reasons.length?'<br>'+r.reasons.map(x=>'• '+esc(x)).join('<br>'):'')+'</div>'+(String(r.review_status||'').toUpperCase()==='ACTIONABLE'&&r.current_price!=null&&r.candidate_price!=null?'<div class="actions"><button class="secondary" id="priceClose">NOT NOW</button><button class="primary" id="priceAccept">ACCEPTED</button></div>':''));const c=$('#priceClose');if(c)c.onclick=()=>$('#overlay').classList.remove('on');const a=$('#priceAccept');if(a)a.onclick=()=>acceptPrice(r,a)}
async function acceptPrice(r,b){b.disabled=true;b.textContent='SAVING…';try{await api('/v1/backoffice/pricing-review/'+encodeURIComponent(r.upc)+'/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_price:r.current_price,current_price_source:r.current_price_source,current_price_asof_date:r.current_price_observed_date,candidate_price:r.candidate_price}),timeoutMs:30000});$('#overlay').classList.remove('on');toast('Accepted · hidden until evidence changes');loadPrices();loadHome()}catch(e){b.disabled=false;b.textContent='ACCEPTED';toast(e.message)}}
$$('.pill[data-cat]').forEach(b=>b.onclick=()=>{priceCat=b.dataset.cat;$$('.pill[data-cat]').forEach(x=>x.classList.toggle('on',x===b));loadPrices()});

async function loadData(){
 try{
  const [health,active,recent]=await Promise.all([api('/v1/backoffice/data-health?days=14',{timeoutMs:12000}),api('/v1/web-upload/active',{timeoutMs:12000}),api('/v1/web-upload/recent?limit=4',{timeoutMs:12000})]);
  $('#calendar').innerHTML=(health.rows||[]).slice(0,14).reverse().map(r=>'<div class="c">'+esc(String(r.date||'').slice(8,10))+'<div class="dot '+(r.overall_status==='MISSING'?'bad':r.overall_status==='COMPLETE'?'':'warn')+'"></div></div>').join('');
  const b=active.active_batch||active.latest_batch||{};const st=String(b.processing_status||'NONE').toUpperCase();
  $('#pipe').innerHTML='<div class="stage '+(st!=='NONE'?'ok':'')+'"><b>UPLOAD</b><span>'+(st==='NONE'?'—':'DONE')+'</span></div><div class="stage '+(/INGEST|PHASE|QUICK|READY/.test(st)?'ok':'')+'"><b>INGEST</b><span>'+(/INGEST|PHASE|QUICK|READY/.test(st)?'DONE':'—')+'</span></div><div class="stage '+(/HOLD/.test(st)?'bad':/PHASE3|QUICK|READY/.test(st)?'ok':'warn')+'"><b>QA</b><span>'+esc(st.includes('HOLD')?'HOLD':/PHASE3|QUICK|READY/.test(st)?'DONE':'WAIT')+'</span></div><div class="stage '+(/QUICK_CHECK_READY/.test(st)?'ok':'warn')+'"><b>PUBLISH</b><span>'+(/QUICK_CHECK_READY/.test(st)?'READY':'WAIT')+'</span></div>';
  $('#currentBatch').innerHTML=b.batch_id?'<div class="batchrow" data-batch="'+esc(b.session_id||b.batch_key||'')+'"><div><b>Batch #'+esc(b.batch_id)+'</b><span>'+esc(b.batch_label||'')+'</span></div><div class="badge '+(st.includes('HOLD')?'red':'amber')+'">'+esc(st)+'</div></div>':'<div class="empty">No active batch.</div>';
  const rb=recent.batches||recent.rows||[];$('#recentBatches').innerHTML=rb.slice(0,4).map(x=>'<div class="batchrow"><div><b>Batch #'+esc(x.batch_id||'—')+'</b><span>'+esc(x.processing_status||'')+'</span></div><span>'+esc(String(x.completed_at||x.upload_started_at||'').slice(0,10))+'</span></div>').join('')||'<div class="empty">No recent batches.</div>';
  $$('[data-batch]').forEach(x=>x.onclick=()=>openBatch(x.dataset.batch,b));
 }catch(e){$('#currentBatch').innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
async function openBatch(session,basic){sheet('Batch #'+esc(basic.batch_id||'—'),basic.processing_status||'','<div class="loading">Loading processing detail…</div>');if(!session){$('#sheetBody').innerHTML='<div class="detail">Session ID unavailable in active summary.</div>';return}try{const d=await api('/v1/web-upload/batches/'+encodeURIComponent(session),{timeoutMs:12000}), b=d.batch||{}, p=d.phase3||{}, q=d.qa_summary||{};$('#sheetBody').innerHTML='<div class="dmetrics"><div class="dm"><b>'+esc(b.processing_status||'—')+'</b><span>BATCH STATUS</span></div><div class="dm"><b>'+fmt(p.quick_check_ready_rows,0)+'</b><span>READY ROWS</span></div><div class="dm"><b>'+fmt(p.quick_check_hold_rows,0)+'</b><span>QA HOLD</span></div></div><div class="detail"><b>Phase 3</b><br>'+esc(p.result_status||'—')+'<br><br><b>Open blockers</b><br>'+fmt(p.blocking_issue_count,0)+(q.reason_counts?'<br>'+Object.entries(q.reason_counts).slice(0,8).map(([k,v])=>'• '+esc(k)+': '+fmt(v,0)).join('<br>'):'')+'</div>'}catch(e){$('#sheetBody').innerHTML='<div class="detail">'+esc(e.message)+'</div>'}}

function activePage(){return $('#'+current)}
app.addEventListener('touchstart',e=>{const p=activePage();if($('#overlay').classList.contains('on')||!p||p.scrollTop>0||e.touches.length!==1)return;pullStart=e.touches[0].clientY;pull=0},{passive:true});
app.addEventListener('touchmove',e=>{if(pullStart==null)return;const dy=e.touches[0].clientY-pullStart;if(dy<=0)return;pull=Math.min(105,dy*.52);$('#ptr').style.height=pull+'px';$('#ptrText').textContent=pull>=68?'Release to refresh':'Pull to refresh'},{passive:true});
app.addEventListener('touchend',()=>{if(pullStart==null)return;const refresh=pull>=68;pullStart=null;if(!refresh){$('#ptr').style.height='0';return}$('#ptr').style.height='48px';$('#ptrText').textContent='Refreshing Yipman…';refreshCurrent().finally(()=>setTimeout(()=>{$('#ptr').style.height='0'},250))});
async function refreshCurrent(){if(current==='home')await loadHome();else if(current==='quick'){const q=$('#quickInput').value.trim();if(q)await loadQuick(q)}else if(current==='order')await loadOrder(Number($('.day.on')?.dataset.offset||0));else if(current==='price')await loadPrices();else if(current==='data')await loadData();toast('Yipman refreshed')}

buildDays();loadHome();
if('serviceWorker'in navigator)navigator.serviceWorker.register('/app/yipman/sw.js',{scope:'/app/yipman/'}).catch(()=>{});
})();
</script>
</body>
</html>'''
