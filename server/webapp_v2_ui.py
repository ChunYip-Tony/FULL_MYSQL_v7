from __future__ import annotations

WEBAPP_V2_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>FULL MYSQL V2</title>
<style>
:root{color-scheme:light dark;--bg:#f3f6fb;--card:#fff;--text:#101828;--muted:#596579;--line:#d8e0eb;--a:#185adb;--a2:#1246ad;--soft:#edf4ff;--ok:#067647;--bad:#b42318;--warn:#a84707;--sale:#b4236a;--shadow:0 7px 22px rgba(15,23,42,.08)}
@media(prefers-color-scheme:dark){:root{--bg:#0b1018;--card:#151c26;--text:#f7f8fa;--muted:#b1bac8;--line:#334052;--a:#82adff;--a2:#9abaff;--soft:#18263d;--ok:#63d8a0;--bad:#ff8a83;--warn:#ffc15a;--sale:#ff8bd1;--shadow:0 9px 26px rgba(0,0,0,.28)}}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top,var(--soft),transparent 460px),var(--bg);color:var(--text);font:19px/1.62 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding-bottom:108px}
.w{max-width:1080px;margin:auto;padding:14px}
.top{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(16px);padding:10px 0 12px;border-bottom:1px solid color-mix(in srgb,var(--line) 65%,transparent)}
.brand{display:flex;justify-content:space-between;align-items:flex-end;gap:10px}.brand h1{font-size:29px;margin:0;letter-spacing:.01em}.ver,.meta,.msg,.small{font-size:16px;color:var(--muted)}
button,input,select{font:inherit;color:var(--text);background:var(--card);border:2px solid var(--line);border-radius:16px;padding:15px 16px;min-height:60px;font-size:19px}
button{font-weight:800;cursor:pointer;transition:.15s transform,.15s border-color}.primary{background:linear-gradient(135deg,var(--a),var(--a2));color:#fff;border-color:transparent;box-shadow:0 6px 17px color-mix(in srgb,var(--a) 22%,transparent)}
button:active{transform:scale(.985)} input,select{width:100%}input:focus,select:focus{outline:4px solid color-mix(in srgb,var(--a) 18%,transparent);border-color:var(--a)}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.grow{flex:1}.card{background:color-mix(in srgb,var(--card) 98%,transparent);border:1.5px solid var(--line);border-radius:20px;padding:17px;margin:13px 0;box-shadow:var(--shadow)}
.result{cursor:pointer;position:relative;padding-right:43px}.result:after{content:'›';position:absolute;right:15px;top:50%;transform:translateY(-50%);font-size:30px;font-weight:400;color:var(--muted)}.result:hover{border-color:var(--a)}
.name{font-weight:900;font-size:21px}.screen{display:none;animation:fade .16s ease}.screen.on{display:block}@keyframes fade{from{opacity:.5;transform:translateY(3px)}to{opacity:1;transform:none}}
.head{display:flex;gap:13px;align-items:center;margin:18px 0}.title{font-size:29px;font-weight:950;line-height:1.18}.back{width:60px;min-width:60px;height:60px;padding:0;border-radius:50%;font-size:27px;background:var(--card)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.m{background:color-mix(in srgb,var(--soft) 58%,var(--card));border:1.5px solid color-mix(in srgb,var(--line) 86%,transparent);border-radius:17px;padding:14px;min-height:92px}.m .k{font-size:14px;letter-spacing:.02em;color:var(--muted);font-weight:850}.m .v{font-size:23px;font-weight:950;margin-top:5px;overflow-wrap:anywhere}
.form{display:grid;grid-template-columns:1fr;gap:13px}label{display:block;font-size:16px;color:var(--muted);font-weight:850;margin-bottom:6px}.pill{display:inline-flex;align-items:center;border:1.5px solid currentColor;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:850;background:color-mix(in srgb,currentColor 7%,transparent)}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.sale{color:var(--sale)}
.actions{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:15px}.actions button{min-height:82px;border-radius:18px;font-size:19px;background:var(--card);box-shadow:var(--shadow)}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:16px}th,td{padding:14px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--muted);font-size:14px;text-transform:uppercase;letter-spacing:.025em;background:var(--card)}.scroll{overflow:auto;border-radius:14px}.hide{display:none!important}
.chart{width:100%;height:270px;border:1.5px solid var(--line);border-radius:16px;background:var(--card);margin-top:10px}.big{font-size:40px;font-weight:950;letter-spacing:-.02em}.order{border-left:6px solid var(--a)}.promo{border:1.5px solid var(--line);border-radius:16px;padding:12px;margin:9px 0;background:color-mix(in srgb,var(--soft) 52%,var(--card))}
.section{font-size:22px;font-weight:950;margin:2px 0 8px}.hint{padding:12px 14px;border-radius:14px;background:var(--soft);color:var(--muted);font-size:16px}.hero-number{font-size:32px;font-weight:950}.price-arrow{font-size:22px;font-weight:900}.report-item{border-left:6px solid var(--warn)}
.nav{position:fixed;left:0;right:0;bottom:0;z-index:20;background:color-mix(in srgb,var(--card) 95%,transparent);border-top:1.5px solid var(--line);padding:7px max(8px,env(safe-area-inset-right)) calc(7px + env(safe-area-inset-bottom)) max(8px,env(safe-area-inset-left));backdrop-filter:blur(18px);box-shadow:0 -8px 26px rgba(15,23,42,.08)}.navin{max-width:1080px;margin:auto;display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.nav button{border:0;background:transparent;color:var(--muted);font-size:14px;line-height:1.25;border-radius:15px;min-height:72px;padding:8px 4px}.nav button.on{color:var(--a);background:color-mix(in srgb,var(--a) 11%,transparent)}
.search-bar{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;align-items:center}
.clear-btn{background:transparent;color:var(--muted);border-color:var(--line);min-width:82px}
.result{transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}
.result:active{transform:scale(.992)}
.family-result{border:2px solid color-mix(in srgb,var(--a) 62%,var(--line));background:linear-gradient(135deg,color-mix(in srgb,var(--a) 10%,var(--card)),var(--card))}
.family-badge{display:inline-block;padding:5px 10px;border-radius:999px;background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a);font-size:14px;font-weight:950;letter-spacing:.02em;margin-bottom:7px}
.result-upc{font-size:25px;font-weight:950;letter-spacing:.025em;margin-top:4px;color:var(--text)}
.result-number{font-size:21px;font-weight:900;margin-top:4px}
.result-type{font-size:14px;font-weight:850;color:var(--muted)}
.audit-ok{border-left:6px solid var(--ok)}
.audit-warn{border-left:6px solid var(--warn)}
html,body{max-width:100%;overflow-x:hidden}
.w,.screen,.card,.head,.head>div,.row,.row>*{min-width:0;max-width:100%}
.meta,.msg,.small,.name,.title,.result-upc,.result-number,.result-type{overflow-wrap:anywhere;word-break:break-word}
.grid,.actions,.form,.search-bar,.navin{min-width:0;max-width:100%}
.group-block{border:1.5px solid var(--line);border-radius:20px;padding:15px;margin:12px 0;box-shadow:var(--shadow)}
.group-title{font-size:18px;font-weight:950;margin-bottom:10px}
.group-identity{background:linear-gradient(135deg,color-mix(in srgb,#4f7cff 15%,var(--card)),var(--card));border-color:color-mix(in srgb,#4f7cff 38%,var(--line))}
.group-sales{background:linear-gradient(135deg,color-mix(in srgb,#16a36a 14%,var(--card)),var(--card));border-color:color-mix(in srgb,#16a36a 36%,var(--line))}
.group-inventory{background:linear-gradient(135deg,color-mix(in srgb,#f59e0b 16%,var(--card)),var(--card));border-color:color-mix(in srgb,#f59e0b 40%,var(--line))}
.group-delivery{background:linear-gradient(135deg,color-mix(in srgb,#8b5cf6 14%,var(--card)),var(--card));border-color:color-mix(in srgb,#8b5cf6 36%,var(--line))}
.group-price{background:linear-gradient(135deg,color-mix(in srgb,#ec4899 13%,var(--card)),var(--card));border-color:color-mix(in srgb,#ec4899 34%,var(--line))}
.group-block .m{background:color-mix(in srgb,var(--card) 82%,transparent);box-shadow:none}
.related-list{display:grid;gap:10px;margin-top:10px}
.related-card{border:1.5px solid var(--line);border-radius:17px;padding:13px;background:var(--card);box-shadow:var(--shadow);cursor:pointer}
.related-upc{font-size:22px;font-weight:950;letter-spacing:.02em;overflow-wrap:anywhere}
.review-actionable{border-left:7px solid var(--ok)}
.review-only{border-left:7px solid var(--warn)}
.review-hold{border-left:7px solid var(--bad)}
.review-badge{font-weight:950;font-size:13px}
@media(max-width:560px){
  .grid{grid-template-columns:1fr}
  .m{min-height:78px}
  .card,.group-block{width:100%;max-width:100%}
  table{font-size:14px}
  .result{padding-right:34px}
  .result:after{right:10px}
  .hero-number{font-size:28px}
}

@media(max-width:560px){.search-bar{grid-template-columns:minmax(0,1fr) auto}.search-bar .primary{grid-column:1/-1}.clear-btn{min-width:76px}}
@media(min-width:760px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}.form{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){body{font-size:18px}.w{padding:11px}.card{padding:15px}.m .v{font-size:21px}.m .k{font-size:13px}.title{font-size:26px}.actions{grid-template-columns:1fr}.actions button{font-size:19px;min-height:72px}.nav button{font-size:13px;min-height:68px}.scroll{margin-left:-4px;margin-right:-4px}}

/* v7.0.122 modern flat UI */
:root{--gp:#7c3aed;--section-blue:#2563eb;--section-green:#059669;--section-amber:#d97706;--section-purple:#7c3aed;--section-pink:#db2777}
body{font-size:17px;line-height:1.5;padding-bottom:86px;background:var(--bg)}
.w{max-width:980px;padding:12px 16px}
.brand h1{font-size:24px}.ver,.meta,.msg,.small{font-size:14px}
button,input,select{min-height:50px;font-size:16px;padding:11px 13px;border-radius:12px;border-width:1.5px}
.head{margin:14px 0;gap:10px}.title{font-size:24px}.back{width:48px;min-width:48px;height:48px;font-size:22px}
.nav{box-shadow:none;border-top:1px solid var(--line);padding-top:5px}.nav button{min-height:58px;font-size:12px;border-radius:10px}
.card{background:transparent;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:16px 0;margin:0;box-shadow:none}
.promo{background:transparent;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:12px 0;margin:0}
.hint{background:transparent;border-left:3px solid var(--a);border-radius:0;padding:6px 10px;font-size:14px}
.section{font-size:18px;margin:6px 0 10px}
.group-block{background:transparent!important;border:0!important;border-radius:0;padding:0;margin:0 0 18px;box-shadow:none!important}
.group-title{font-size:15px;text-transform:uppercase;letter-spacing:.055em;padding:8px 0;margin:0;border-bottom:2px solid var(--line)}
.group-identity .group-title{color:var(--section-blue);border-color:color-mix(in srgb,var(--section-blue) 35%,var(--line))}
.group-sales .group-title{color:var(--section-green);border-color:color-mix(in srgb,var(--section-green) 35%,var(--line))}
.group-inventory .group-title{color:var(--section-amber);border-color:color-mix(in srgb,var(--section-amber) 38%,var(--line))}
.group-delivery .group-title{color:var(--section-purple);border-color:color-mix(in srgb,var(--section-purple) 35%,var(--line))}
.group-price .group-title{color:var(--section-pink);border-color:color-mix(in srgb,var(--section-pink) 35%,var(--line))}
.group-block .grid{display:block}
.group-block .m{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;background:transparent;border:0;border-bottom:1px solid color-mix(in srgb,var(--line) 75%,transparent);border-radius:0;padding:11px 0;min-height:0}
.group-block .m .k{font-size:13px;min-width:120px;text-transform:none}
.group-block .m .v{font-size:17px;text-align:right;margin:0}
.metric-section{margin:0 0 19px}
.metric-section-title{font-size:14px;font-weight:900;text-transform:uppercase;letter-spacing:.065em;padding:8px 0;border-bottom:2px solid var(--line)}
.metric-section.blue .metric-section-title{color:var(--section-blue);border-color:color-mix(in srgb,var(--section-blue) 38%,var(--line))}
.metric-section.green .metric-section-title{color:var(--section-green);border-color:color-mix(in srgb,var(--section-green) 38%,var(--line))}
.metric-section.amber .metric-section-title{color:var(--section-amber);border-color:color-mix(in srgb,var(--section-amber) 40%,var(--line))}
.metric-section.purple .metric-section-title{color:var(--section-purple);border-color:color-mix(in srgb,var(--section-purple) 38%,var(--line))}
.metric-section.pink .metric-section-title{color:var(--section-pink);border-color:color-mix(in srgb,var(--section-pink) 38%,var(--line))}
.metric-row{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding:10px 0;border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent)}
.metric-row:last-child{border-bottom:0}.metric-key{font-size:13px;color:var(--muted);font-weight:750;min-width:120px}.metric-value{font-size:16px;font-weight:800;text-align:right;overflow-wrap:anywhere}
.metric-note{font-size:12px;color:var(--muted);margin-top:2px;text-align:right}
.related-list{gap:0}.related-card{background:transparent;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:13px 0;box-shadow:none}
.result{background:transparent!important;border:0!important;border-bottom:1px solid var(--line)!important;border-radius:0!important;box-shadow:none!important;margin:0!important;padding:13px 36px 13px 0!important}
.result:hover{background:color-mix(in srgb,var(--soft) 42%,transparent)!important}
.family-result{background:linear-gradient(90deg,color-mix(in srgb,var(--a) 10%,transparent),transparent 78%)!important;border-left:4px solid var(--a)!important;padding-left:10px!important}
.family-badge{font-size:11px;padding:3px 7px;border-radius:6px;margin-bottom:4px}
.result-upc{font-size:21px}.result-number{font-size:18px}.name{font-size:18px}
.upc-type{display:inline-flex;margin-top:5px;padding:3px 7px;border-radius:999px;background:color-mix(in srgb,var(--a) 9%,transparent);color:var(--a);font-size:11px;font-weight:850}
.actions{gap:8px;margin-top:12px}.actions button{min-height:54px;font-size:15px;border-radius:11px;box-shadow:none}
.chart{height:285px;border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent}
.big,.hero-number{font-size:27px}
.search-bar{gap:8px}
@media(max-width:560px){
  body{font-size:16px}.w{padding:10px 13px}.title{font-size:22px}.brand h1{font-size:22px}
  .metric-row{gap:12px}.metric-key{min-width:105px}.metric-value{font-size:15px}
  .actions{grid-template-columns:repeat(3,1fr)}.actions button{font-size:14px;min-height:52px;padding:8px 5px}
  .grid{grid-template-columns:1fr 1fr}.m{min-height:0}.m .v{font-size:16px}.m .k{font-size:12px}
  .nav button{min-height:56px;font-size:11px}.search-bar .primary{grid-column:auto}
}

</style></head><body><div class="w">
<div class="top"><div class="brand"><h1>FULL MYSQL</h1><div class="ver">Web App V2 · v7.0.122</div></div><div class="msg">CORE · PI · PERFORMANCE</div></div>

<section id="core" class="screen on"><div class="head"><div><div class="title">🔎 CORE</div><div class="meta">Search item name, Family Article, Article, or UPC.</div></div></div><div class="search-bar"><input id="cq" placeholder="Search item" autocomplete="off"><button id="cc" class="clear-btn" type="button">Clear</button><button id="cs" class="primary">Search</button></div><div id="cmsg" class="msg"></div><div id="cres"></div></section>

<section id="family" class="screen"><div class="head"><button class="back" data-go="core">←</button><div><div id="ft" class="title"></div><div id="fs" class="meta"></div></div></div><div id="fsummary"></div><div class="metric-section blue"><div class="metric-section-title">Related UPCs</div><div class="hint">Sorted by 28D Qty Sold, then readiness.</div><div id="fu" class="related-list"></div></div></section>

<section id="upc" class="screen"><div class="head"><button class="back" id="ub">←</button><div><div id="ut" class="title"></div><div id="us" class="meta"></div></div></div><div id="usum"></div><div class="actions"><button id="uf">Family Article</button><button id="upr">Price</button><button id="uo">Ordering</button></div></section>

<section id="price" class="screen"><div class="head"><button class="back" data-go="upc">←</button><div><div id="pt" class="title"></div><div id="ps" class="meta"></div></div></div><div id="pc"></div><div class="card"><div class="section">7 Supported-Day GP$ vs Avg Selling Price</div><canvas id="chart" class="chart"></canvas><div class="row" style="margin-top:9px"><span class="pill ok">● Qty Sold</span><span class="pill" style="color:var(--a)">● Avg Price</span><span class="pill" style="color:var(--gp)">● GP$ (current cost)</span><span class="pill sale">▮ SALE</span></div><div class="hint" style="margin-top:8px">Each point is labeled. Only the latest 7 completed supported sales dates are graphed. Missing source dates are skipped, not counted as zero.</div></div><div class="card"><div class="section">Past 14 Supported-Day Sales History</div><div id="p14"></div></div><div class="card"><div class="section">Historical SALE Promotions</div><div id="ph"></div></div></section>

<section id="corder" class="screen"><div class="head"><button class="back" data-go="upc">←</button><div><div id="cot" class="title"></div><div id="cos" class="meta"></div></div></div><div class="card"><div class="form"><div><label>Ordering Date</label><input id="cod" type="date"></div><div><label>Expected Delivery Date</label><input id="cdd" type="date"></div><div><label>Context</label><select id="cop"><option value="0">Regular</option><option value="1">Promotion Involved</option></select></div></div><div id="cpf" class="form hide" style="margin-top:8px"><div><label>Promotion Start</label><input id="cps" type="date"></div><div><label>Promotion End</label><input id="cpe" type="date"></div><div><label>Promotion Price</label><input id="cpp"></div></div><div id="cohist"></div><button id="coa" class="primary" style="margin-top:9px">Analyze</button></div><div id="coout"></div></section>

<section id="ordering" class="screen hide" aria-hidden="true"><div class="head"><div><div class="title">📦 ORDERING</div><div class="meta">Family-level Fresh / Frozen ordering suggestions.</div></div></div><div class="card"><div class="form"><div><label>Fresh or Frozen</label><select id="ot"><option>FRESH</option><option>FROZEN</option></select></div><div><label>Ordering Date</label><input id="od" type="date"></div><div><label>Expected Delivery</label><input id="dd" type="date"></div><div><label>Context</label><select id="op"><option value="0">Regular</option><option value="1">Promotion Involved</option></select></div></div><div id="opa" class="hide"><div class="form" style="margin-top:8px"><div><label>Promotion Start</label><input id="ops" type="date"></div><div><label>Promotion End</label><input id="ope" type="date"></div></div><div class="row" style="margin-top:8px"><input id="oiq" class="grow" placeholder="Search promotion UPC or item name"><button id="ois">Search</button></div><div id="oim" class="msg"></div><div id="oir"></div><div id="oil"></div><div id="ohist"></div></div><button id="ogen" class="primary" style="margin-top:10px">Generate Suggestions</button><div id="omsg" class="msg"></div></div><div id="ores"></div></section>

<section id="pi" class="screen"><div class="head"><div><div class="title">🧮 PI</div><div class="meta">Physical Inventory · Family Article True Stock.</div></div></div><div class="search-bar"><input id="piq" placeholder="Search Family, item, article, or UPC" autocomplete="off"><button id="pic" class="clear-btn" type="button">Clear</button><button id="pis" class="primary">Search</button></div><div id="pim" class="msg"></div><div id="pir"></div></section>

<section id="performance" class="screen"><div class="head"><div><div class="title">📊 PERFORMANCE</div><div class="meta">Analyze one completed sales date and generate price suggestions using history through that date.</div></div></div><div class="card"><div class="form"><div><label>Report Date</label><select id="perdate"><option value="">Loading supported dates…</option></select></div><div><label>Category</label><select id="percat"><option>ALL</option><option>LIVE</option><option>FRESH</option><option>FROZEN</option></select></div></div><div class="hint" style="margin-top:10px">Report Date must have completed canonical sales data. The app defaults to the latest supported date.</div><button id="perrun" class="primary" style="margin-top:12px;width:100%">Generate Performance Report</button><div id="permsg" class="msg" style="margin-top:8px"></div></div><div id="persummary"></div><div id="peranalysis"></div><div class="card"><div class="section">Report Date Top Sellers</div><div id="pertop"></div></div><div class="card"><div class="section">Top 100 Urgent Price Reviews</div><div class="hint">Suggestions are analysis only. Sales evidence stops at the selected Report Date. Company C is the bottom line when applicable. Current authoritative cost is used until historical daily cost lineage is exposed.</div><div id="peritems"></div></div></section>

<section id="pid" class="screen"><div class="head"><button class="back" data-go="pi">←</button><div><div id="pit" class="title"></div><div id="pisub" class="meta"></div></div></div><div id="pisum"></div><div class="card"><b>Apply True Stock</b><div class="form" style="margin-top:8px"><div><label>True Stock</label><input id="pqty"></div><div><label>UOM</label><input id="puom" readonly></div></div><div style="margin-top:8px"><label>Note</label><input id="pnote"></div><button id="papply" class="primary" style="margin-top:9px">Apply True Stock</button><div id="pamsg" class="msg"></div></div><div class="card"><b>PI History</b><div class="scroll"><table><thead><tr><th>Time</th><th>System</th><th>True</th><th>Diff</th><th>Status</th><th>Note</th></tr></thead><tbody id="pih"></tbody></table></div></div></section>
</div>

<nav class="nav"><div class="navin"><button data-main="core" class="on">🔎<br>CORE</button><button data-main="pi">🧮<br>PI</button><button data-main="performance">📊<br>PERFORMANCE</button></div></nav>

<script>
const $=x=>document.getElementById(x),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=2)=>{if(v===null||v===undefined||v==='')return '—';let n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):String(v)},money=v=>v===null||v===undefined?'—':'$'+fmt(v,2);
const today=()=>new Date().toLocaleDateString('en-CA'),nextwd=(s,t)=>{let d=new Date(s+'T12:00:00'),x=(t-d.getDay()+7)%7;if(!x)x=7;d.setDate(d.getDate()+x);return d.toLocaleDateString('en-CA')};const dayName=s=>{if(!s)return '—';return new Intl.DateTimeFormat('en-US',{weekday:'long'}).format(new Date(s+'T12:00:00'))};const promoRange=p=>p.weekday_range||((p.start_weekday||dayName(p.start_date))+' → '+(p.end_weekday||dayName(p.end_date)));
let cupc=null,uback='core',pifamily=null,pitems=[];
async function api(p,o={}){let r=await fetch(p,o),b=null;try{b=await r.json()}catch{}if(!r.ok){let d=b?.detail;throw new Error(typeof d==='string'?d:(d?.reason||'HTTP '+r.status))}return b}
function mainForScreen(id){if(['family','upc','price','corder'].includes(id))return 'core';if(id==='pid')return 'pi';return id}
function showScreen(id){document.querySelectorAll('.screen').forEach(x=>x.classList.remove('on'));$(id).classList.add('on');let main=mainForScreen(id);document.querySelectorAll('[data-main]').forEach(x=>x.classList.toggle('on',x.dataset.main===main));scrollTo({top:0,behavior:'smooth'})}
function go(id){let cur=document.querySelector('.screen.on')?.id;if(cur===id)return;showScreen(id);history.pushState({fullmysqlV2:true,screen:id},'',location.pathname+location.search+'#'+id)}
history.replaceState({fullmysqlV2:true,screen:'guard'},'',location.pathname+location.search+'#core');history.pushState({fullmysqlV2:true,screen:'core'},'',location.pathname+location.search+'#core');
window.addEventListener('popstate',e=>{let s=e.state;if(s&&s.fullmysqlV2&&s.screen&&s.screen!=='guard'){showScreen(s.screen);return}history.pushState({fullmysqlV2:true,screen:'core'},'',location.pathname+location.search+'#core');showScreen('core')})
function pill(s){s=String(s||'UNKNOWN');let c=s==='READY'?'ok':(s.includes('BLOCK')||s==='QA_HOLD'?'bad':'warn');return '<span class="pill '+c+'">'+esc(s)+'</span>'}
function m(k,v){return '<div class="m"><div class="k">'+esc(k)+'</div><div class="v">'+esc(v)+'</div></div>'}
function qv(v,u){return fmt(v)+' '+esc(u||'UOM UNKNOWN')}
function mr(k,v,note=''){return '<div class="metric-row"><div class="metric-key">'+esc(k)+'</div><div><div class="metric-value">'+esc(v)+'</div>'+(note?'<div class="metric-note">'+esc(note)+'</div>':'')+'</div></div>'}
function ms(title,tone,rows){return '<div class="metric-section '+tone+'"><div class="metric-section-title">'+esc(title)+'</div>'+rows.join('')+'</div>'}
document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>history.back());document.querySelectorAll('[data-main]').forEach(b=>b.onclick=()=>go(b.dataset.main));

async function csearch(){
  let q=$('cq').value.trim();
  if(!q){$('cmsg').textContent='Enter an item, Family Article, Article, or UPC.';return}
  $('cmsg').textContent='Searching…';$('cres').innerHTML='';
  try{
    let d=await api('/v1/app/v2/search?q='+encodeURIComponent(q)+'&limit=30');
    $('cmsg').textContent=d.count+' result(s) · sorted by 28D Qty, then readiness';
    $('cres').innerHTML=(d.results||[]).map((r,i)=>{
      let isFamily=r.result_type==='FAMILY',isUpc=r.result_type==='UPC';
      let numberHtml=isUpc
        ? '<div class="result-upc">UPC '+esc(r.number||'—')+'</div>'
        : '<div class="result-number">'+esc(r.number||'—')+'</div>';
      return '<div class="card result '+(isFamily?'family-result':'')+'" data-i="'+i+'">'
        +(isFamily?'<div class="family-badge">★ FAMILY ARTICLE</div>':'')
        +'<div class="row" style="justify-content:space-between"><div class="name">'+esc(r.name)+'</div>'+pill(r.readiness)+'</div>'
        +numberHtml
        +'<div class="result-type">'+esc(r.result_type)+' · '+esc(r.category||'—')+'</div>'
        +(isUpc?'<span class="upc-type">'+esc(r.upc_role||'OTHER UPC')+'</span>':'')
        +'<div class="meta">28 supported-day Qty '+qv(r.qty_28d,r.qty_28d_uom)+'</div>'
        +'</div>';
    }).join('')||'<div class="card small">No match found.</div>';
    document.querySelectorAll('#cres .result').forEach(e=>e.onclick=()=>{
      let r=d.results[+e.dataset.i];
      r.result_type==='FAMILY'?family(r.family_id||r.number):upc(r.number,'core');
    });
  }catch(e){$('cmsg').textContent=e.message}
}
$('cs').onclick=csearch;
$('cc').onclick=()=>{$('cq').value='';$('cres').innerHTML='';$('cmsg').textContent='';$('cq').focus()};
$('cq').onkeydown=e=>{if(e.key==='Enter')csearch()};


async function family(k){try{
  let d=await api('/v1/app/v2/family/'+encodeURIComponent(k)),o=d.current_effective_oh||{},z=d.observed_delivery||{},r=d.last_receipt||{};
  $('ft').textContent=d.family_article_name;
  $('fs').textContent='Family '+(d.family_article_number||'—')+' · '+(d.category||'—');
  let articleText=(d.receiving_ordering_articles||[]).map(a=>String(a.article_number||'')+(a.article_description?' · '+String(a.article_description):'')).join(' | ')||'—';
  let ohText=o.quantity==null?'No OH':qv(o.quantity,o.uom);
  let ohReason=o.quantity==null?(o.reason||o.status||'OH unavailable'):(o.source||o.status||'READY');
  $('fsummary').innerHTML=
    ms('Identity','blue',[
      mr('Family Article',d.family_article_number||'—'),
      mr('Category',d.category||'—'),
      mr('Receiving / Ordering',articleText)
    ])+
    ms('Sales','green',[
      mr('7D Sold',qv(d.family_sales_7d?.sold_quantity,d.family_sales_7d?.uom),fmt(d.family_sales_7d?.supported_day_count,0)+' supported days'),
      mr('28D Sold',qv(d.family_sales_28d?.sold_quantity,d.family_sales_28d?.uom),fmt(d.family_sales_28d?.supported_day_count,0)+' supported days')
    ])+
    ms('Inventory','amber',[
      mr('Effective OH',ohText,ohReason),
      mr('OH Status',o.status||'—'),
      mr('OH Source',o.source||'—'),
      mr('OH Anchor',o.anchor_date||o.submitted_at||'—')
    ])+
    ms('Delivery & Receipt','purple',[
      mr('Next Expected Delivery',d.next_expected_delivery_date||'Uncertain'),
      mr('Observed Days',(z.observed_delivery_days||[]).map(x=>x.weekday).join(', ')||'—'),
      mr('Frequency',z.frequency||'—'),
      mr('Last Receipt',r.date||'—'),
      mr('Receipt Qty',qv(r.quantity,r.uom)),
      mr('Receipt Cost',money(r.cost)+' '+(r.cost_uom||'—'))
    ]);
  $('fu').innerHTML=(d.related_upcs||[]).map((x,i)=>
    '<div class="related-card" data-i="'+i+'">'+
      '<div class="row" style="justify-content:space-between"><div><div class="name">'+esc(x.name)+'</div><div class="related-upc">UPC '+esc(x.upc)+'</div><span class="upc-type">'+esc(x.upc_role||'OTHER UPC')+'</span></div>'+pill(x.readiness)+'</div>'+
      mr('Price',money(x.current_price)+' '+esc(x.current_price_type||'—'))+
      mr('7D Qty',qv(x.qty_7d,x.selling_uom),fmt(x.supported_days_7d,0)+' supported days')+
      mr('28D Qty',qv(x.qty_28d,x.selling_uom),fmt(x.supported_days_28d,0)+' supported days')+
    '</div>'
  ).join('')||'<div class="small">No related UPCs.</div>';
  document.querySelectorAll('#fu [data-i]').forEach(e=>e.onclick=()=>upc(d.related_upcs[+e.dataset.i].upc,'family'));
  go('family')
}catch(e){alert(e.message)}}


async function upc(u,b='core'){try{
  let d=await api('/v1/app/v2/upc/'+encodeURIComponent(u));cupc=d.upc;uback=b;
  let o=d.effective_oh||{};
  $('ut').textContent=d.upc_name;
  $('us').textContent='UPC '+d.upc+' · '+(d.category||'—')+' · '+(d.upc_role||'OTHER UPC');
  $('usum').innerHTML=
    ms('Identity','blue',[
      mr('UPC',d.upc),
      mr('UPC Type',d.upc_role||'OTHER UPC'),
      mr('Family Article',d.family_article_number||'—'),
      mr('Category',d.category||'—'),
      mr('Status',d.readiness||'—'),
      mr('Selling UOM',d.selling_uom||'—')
    ])+
    ms('Sales','green',[
      mr('7D Qty',qv(d.qty_7d?.sold_quantity,d.selling_uom),fmt(d.qty_7d?.supported_day_count,0)+' supported days'),
      mr('28D Qty',qv(d.qty_28d?.sold_quantity,d.selling_uom),fmt(d.qty_28d?.supported_day_count,0)+' supported days')
    ])+
    ms('Inventory','amber',[
      mr('Effective OH',o.quantity==null?'No OH':qv(o.quantity,o.uom),o.quantity==null?(o.reason||o.status||'OH unavailable'):(o.source||o.status||'READY')),
      mr('OH Status',o.status||'—')
    ])+
    ms('Price','pink',[
      mr('Current Price',money(d.current_price)),
      mr('Price Type',d.current_price_type||'—')
    ]);
  $('uf').onclick=()=>family(d.family_article_number);
  $('upr').onclick=()=>price(d.upc);
  $('uo').onclick=()=>corder(d.upc);
  go('upc')
}catch(e){alert(e.message)}}
$('ub').onclick=()=>history.back();


async function price(u){try{
  let d=await api('/v1/app/v2/upc/'+encodeURIComponent(u)+'/price?trend_supported_days=7'),c0=d.current||{},r=d.references||{},s=d.sales||{},uom=d.qty_uom||d.selling_uom||'—';
  $('pt').textContent=d.name;
  $('ps').textContent='UPC '+d.upc+' · '+(d.category||'—')+' · '+(d.upc_role||'OTHER UPC');
  $('pc').innerHTML=
    ms('Current Price & Margin','pink',[
      mr('Current Price',money(c0.price)+' '+(c0.price_type||'—')),
      mr('Cost',money(c0.cost)+' '+(c0.cost_uom||'—')),
      mr('GP%',c0.gp_pct==null?'—':fmt(Number(c0.gp_pct)*100,1)+'%'),
      mr('GP$/Day',money(c0.gp_per_day_7d))
    ])+
    ms('Sales','green',[
      mr('7D Qty',qv(s['7d']?.sold_quantity,uom),fmt(s['7d']?.supported_day_count,0)+' supported days'),
      mr('28D Qty',qv(s['28d']?.sold_quantity,uom),fmt(s['28d']?.supported_day_count,0)+' supported days')
    ])+
    ms('Price References','purple',[
      mr('Sweet Spot',money(r.sweet_spot)),
      mr('WGPM',money(r.wgpm)),
      mr('Company A',money(r.company_a)),
      mr('Company B',money(r.company_b)),
      mr('Company C',money(r.company_c))
    ]);
  chart(d.price_vs_sales_trend?.rows||[]);
  $('p14').innerHTML=(d.sales_history_14d?.rows||[]).slice().reverse().map(x=>
    '<div class="promo"><div class="row" style="justify-content:space-between"><b>'+esc(dayName(x.date))+' · '+esc(x.date)+'</b><b>'+qv(x.sold_quantity,x.qty_uom||uom)+' sold</b></div>'+
    '<div class="meta">Sales '+money(x.sales_amount)+' · Avg price '+money(x.avg_sold_price)+' · GP$ '+money(x.gp_dollars)+' · '+((x.price_types||[]).map(p=>esc(p.price_type)).join(', ')||'No item sale')+'</div></div>'
  ).join('')||'<div class="small">No 14-day supported sales history.</div>';
  $('ph').innerHTML=(d.historical_promotions||[]).map(p=>
    '<div class="promo"><b>'+esc(p.promotion_type)+' Promotion · '+esc(promoRange(p))+'</b>'+
    '<div class="meta">'+esc(p.start_date)+' → '+esc(p.end_date)+' · '+money(p.sale_price)+'</div>'+
    '<div class="meta">'+qv(p.sale_quantity,uom)+' sold · '+qv(p.sale_velocity_per_supported_day,uom)+'/supported day · coverage '+fmt(p.supported_sales_day_count,0)+'/'+fmt(p.calendar_duration_days,0)+'</div></div>'
  ).join('')||'<div class="small">No historical SALE periods.</div>';
  go('price')
}catch(e){alert(e.message)}}

function chart(rows){
  let c=$('chart'),ctx=c.getContext('2d'),R=devicePixelRatio||1,w=Math.max(300,c.clientWidth),h=310;
  c.width=w*R;c.height=h*R;ctx.setTransform(R,0,0,R,0,0);ctx.clearRect(0,0,w,h);
  let a=rows.slice(-7),p={l:38,r:30,t:42,b:54};
  if(!a.length){
    ctx.fillStyle=getComputedStyle(document.body).color;
    ctx.font='16px system-ui';
    ctx.fillText('No trend data',20,30);
    return;
  }

  let gpVals=a.map(z=>Number(z.gp_dollars)).filter(Number.isFinite);
  let priceVals=a.map(z=>Number(z.avg_sold_price)).filter(Number.isFinite);
  let gpMin=Math.min(...gpVals,0),gpMax=Math.max(...gpVals,1);
  let priceMin=Math.min(...priceVals,0),priceMax=Math.max(...priceVals,1);
  if(gpMax===gpMin)gpMax=gpMin+1;
  if(priceMax===priceMin)priceMax=priceMin+1;

  let pw=w-p.l-p.r,ph=h-p.t-p.b;
  let xx=i=>p.l+(a.length===1?pw/2:pw*i/(a.length-1));
  let ygp=v=>p.t+ph*(1-(v-gpMin)/(gpMax-gpMin));
  let yp=v=>p.t+ph*(1-(v-priceMin)/(priceMax-priceMin));

  let line=getComputedStyle(document.documentElement).getPropertyValue('--line');
  let gpColor=getComputedStyle(document.documentElement).getPropertyValue('--ok');
  let priceColor=getComputedStyle(document.documentElement).getPropertyValue('--a');
  let saleColor=getComputedStyle(document.documentElement).getPropertyValue('--sale');
  let muted=getComputedStyle(document.documentElement).getPropertyValue('--muted');
  let textColor=getComputedStyle(document.documentElement).getPropertyValue('--text');

  ctx.strokeStyle=line;ctx.lineWidth=1;
  for(let i=0;i<5;i++){
    let y=p.t+ph*i/4;
    ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();
  }

  ctx.strokeStyle=gpColor;ctx.lineWidth=3;ctx.beginPath();
  let gpOn=false;
  a.forEach((z,i)=>{
    let v=Number(z.gp_dollars);
    if(!Number.isFinite(v)){gpOn=false;return}
    let x=xx(i),y=ygp(v);
    if(!gpOn){ctx.moveTo(x,y);gpOn=true}else ctx.lineTo(x,y);
  });
  ctx.stroke();
  a.forEach((z,i)=>{
    let v=Number(z.gp_dollars);if(!Number.isFinite(v))return;
    let x=xx(i),y=ygp(v);
    ctx.fillStyle=gpColor;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill();
    ctx.font='800 12px system-ui';ctx.textAlign='center';ctx.fillStyle=gpColor;
    ctx.fillText('$'+fmt(v,2),x,Math.min(h-p.b-8,y+19));
  });

  ctx.strokeStyle=priceColor;ctx.lineWidth=3;ctx.beginPath();
  let priceOn=false;
  a.forEach((z,i)=>{
    let v=Number(z.avg_sold_price);
    if(!Number.isFinite(v)){priceOn=false;return}
    let x=xx(i),y=yp(v);
    if(!priceOn){ctx.moveTo(x,y);priceOn=true}else ctx.lineTo(x,y);
  });
  ctx.stroke();
  a.forEach((z,i)=>{
    let v=Number(z.avg_sold_price);if(!Number.isFinite(v))return;
    let x=xx(i),y=yp(v);
    ctx.fillStyle=priceColor;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill();
    ctx.font='800 12px system-ui';ctx.textAlign='center';ctx.fillStyle=priceColor;
    ctx.fillText('$'+fmt(v,2),x,Math.max(14,y-10));
  });

  ctx.font='11px system-ui';ctx.textAlign='center';
  a.forEach((z,i)=>{
    let x=xx(i);
    if((z.price_types||[]).some(v=>v.price_type==='SALE')){
      ctx.fillStyle=saleColor;ctx.fillRect(x-4,h-p.b+5,8,11);
    }
    ctx.fillStyle=muted;
    ctx.fillText(dayName(z.date).slice(0,3),x,h-23);
    ctx.fillText(String(z.date).slice(5),x,h-8);
  });

  ctx.font='10px system-ui';ctx.textAlign='left';ctx.fillStyle=textColor;
  ctx.fillText('GP$ '+(gpVals.length?'$'+fmt(gpMax,2):'—'),4,p.t+3);
  ctx.textAlign='right';
  ctx.fillText('Avg $ '+(priceVals.length?'$'+fmt(priceMax,2):'—'),w-4,p.t+3);
}


async function corder(u){cupc=u;$('cod').value=today();$('cop').value='0';$('cpf').classList.add('hide');try{let d=await api('/v1/app/v2/upc/'+encodeURIComponent(u)+'/ordering');$('cot').textContent=d.family_article_name||d.name;$('cos').textContent='Family '+(d.family_article_number||'—')+' · '+(d.category||'—')+' · from UPC '+(d.source_upc||u);$('cdd').value=d.inputs?.expected_delivery_date||'';corender(d);go('corder')}catch(e){$('coout').innerHTML='<div class="card bad">'+esc(e.message)+'</div>';go('corder')}}$('cop').onchange=()=> $('cpf').classList.toggle('hide',$('cop').value!=='1');$('coa').onclick=async()=>{let q=new URLSearchParams();q.set('ordering_date',$('cod').value);q.set('expected_delivery_date',$('cdd').value);let p=$('cop').value==='1';q.set('promotion_involved',p);if(p){q.set('promotion_start_date',$('cps').value);q.set('promotion_end_date',$('cpe').value);q.set('promotion_price',$('cpp').value)}try{corender(await api('/v1/app/v2/upc/'+encodeURIComponent(cupc)+'/ordering?'+q))}catch(e){$('coout').innerHTML='<div class="card bad">'+esc(e.message)+'</div>'}};
function corender(d){let i=d.inventory||{},f=d.forecast||{},r=d.regular_baseline||{};$('cohist').innerHTML=(d.historical_promotions||[]).slice(0,5).map(p=>'<div class="promo"><b>'+esc(p.promotion_type)+' Promotion · '+esc(promoRange(p))+'</b><div class="meta">'+esc(p.start_date)+' → '+esc(p.end_date)+' · '+money(p.sale_price)+' · '+qv(p.sale_quantity,f.suggested_order_uom)+' sold</div></div>').join('');$('coout').innerHTML='<div class="card order"><div class="grid">'+m('Effective OH',qv(i.raw_effective_oh_qty,f.suggested_order_uom))+m('OH Used',qv(i.ordering_oh_qty,f.suggested_order_uom))+m('Regular Velocity',qv(r.regular_velocity_per_supported_day,f.suggested_order_uom)+'/day')+m('Next Next Delivery',d.next_next_delivery_date||'—')+m('Forecast Usage',qv(f.forecast_usage_until_next_next_delivery,f.suggested_order_uom))+m('Projected OH @ Delivery',qv(f.projected_oh_at_expected_delivery,f.suggested_order_uom))+'</div><div class="small">Suggested Order Qty</div><div class="big">'+fmt(f.suggested_order_qty)+' '+esc(f.suggested_order_uom||'')+'</div>'+(i.negative_oh_treated_as_zero?'<div class="warn">Negative OH treated as 0 for ordering.</div>':'')+'</div>'}

function orderDefaults(){let t=today();$('od').value=t;$('dd').value=nextwd(t,5)}orderDefaults();$('ot').onchange=()=>{$('dd').value=nextwd($('od').value||today(),$('ot').value==='FRESH'?5:2)};$('od').onchange=()=>$('ot').onchange();$('op').onchange=()=> $('opa').classList.toggle('hide',$('op').value!=='1');
$('ois').onclick=async()=>{let q=$('oiq').value.trim();if(!q)return;$('oim').textContent='Searching UPCs…';try{let d=await api('/v1/app/v2/search?q='+encodeURIComponent(q)+'&limit=30'),u=(d.results||[]).filter(r=>r.result_type==='UPC'&&String(r.category||'').toUpperCase()===$('ot').value);$('oim').textContent=u.length+' UPC match(es) · sorted by 28D Qty, then readiness';$('oir').innerHTML=u.slice(0,12).map((z,i)=>'<div class="card result" data-i="'+i+'"><div class="row" style="justify-content:space-between"><div><div class="name">'+esc(z.name)+'</div><div class="meta">UPC '+esc(z.number)+' · Family '+esc(z.family_article_number||'—')+'</div></div>'+pill(z.readiness)+'</div><div class="meta">28D Qty '+qv(z.qty_28d,z.qty_28d_uom)+'</div></div>').join('');document.querySelectorAll('#oir .result').forEach(e=>e.onclick=()=>addPromoUPC(u[+e.dataset.i]))}catch(e){$('oim').textContent=e.message}};
async function addPromoUPC(z){let upc=String(z.number||'');if(!upc||pitems.some(x=>x.upc===upc))return;pitems.push({upc,name:z.name,family_article_number:z.family_article_number,family_name:z.family_name,promotion_price:''});drawPromo();$('oir').innerHTML='';$('oiq').value='';try{let d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc)+'/price?trend_supported_days=7');$('ohist').innerHTML='<div class="card"><div class="section">Historical SALE · '+esc(z.name)+'</div><div class="meta">UPC '+esc(upc)+' · this UPC history only</div>'+((d.historical_promotions||[]).slice(0,6).map((p,i)=>'<div class="promo result" data-i="'+i+'"><b>'+esc(p.promotion_type)+' · '+esc(promoRange(p))+'</b><div class="meta">'+esc(p.start_date)+' → '+esc(p.end_date)+' · '+money(p.sale_price)+'</div><div class="meta">'+qv(p.sale_quantity,d.qty_uom||d.selling_uom)+' sold · '+qv(p.sale_velocity_per_supported_day,d.qty_uom||d.selling_uom)+'/supported day</div></div>').join('')||'<div class="small">No historical SALE periods for this UPC.</div>')+'</div>';document.querySelectorAll('#ohist .promo').forEach(e=>e.onclick=()=>{let p=d.historical_promotions[+e.dataset.i],it=pitems.find(x=>x.upc===upc);if(it&&p.sale_price!=null)it.promotion_price=Number(p.sale_price).toFixed(2);drawPromo();$('oim').textContent='Loaded historical '+promoRange(p)+' SALE price as reference. Enter the upcoming promotion dates.'})}catch(e){$('ohist').innerHTML='<div class="card bad">'+esc(e.message)+'</div>'}}
function drawPromo(){$('oil').innerHTML=pitems.length?'<div class="card"><div class="section">Selected Promotion UPCs</div>'+pitems.map((z,i)=>'<div class="row" style="margin-top:10px"><div class="grow"><b>'+esc(z.name)+'</b><div class="meta">UPC '+esc(z.upc)+' · Family '+esc(z.family_article_number||'—')+'</div></div><input data-p="'+i+'" placeholder="SALE price" value="'+esc(z.promotion_price)+'" style="max-width:132px"><button data-r="'+i+'">Remove</button></div>').join('')+'</div>':'';document.querySelectorAll('[data-p]').forEach(e=>e.oninput=()=>pitems[+e.dataset.p].promotion_price=e.value);document.querySelectorAll('[data-r]').forEach(e=>e.onclick=()=>{pitems.splice(+e.dataset.r,1);drawPromo()})}
$('ogen').onclick=async()=>{let promo=$('op').value==='1',body={order_type:$('ot').value,ordering_date:$('od').value,expected_delivery_date:$('dd').value,promotion_involved:promo,promotion_start_date:promo?$('ops').value:null,promotion_end_date:promo?$('ope').value:null,promotion_items:promo?pitems.map(x=>({upc:x.upc,promotion_price:x.promotion_price})):[]};$('omsg').textContent='Calculating…';try{let d=await api('/v1/app/v2/ordering/suggestions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('omsg').textContent=d.suggestion_count+' suggestion(s) · next-next '+(d.inputs?.next_next_delivery_date||'—');$('ores').innerHTML=(d.suggestions||[]).map(r=>'<div class="card order"><div class="row" style="justify-content:space-between"><div><div class="name">'+esc(r.family_article_name)+'</div><div class="meta">Family '+esc(r.family_article_number)+' · '+esc(r.category)+(r.promotion_involved?' · SALE':'')+'</div></div>'+pill(r.readiness)+'</div><div class="grid" style="margin-top:10px">'+m('DOS',fmt(r.dos,1))+m('Effective OH',qv(r.effective_oh_raw,r.uom))+m('OH Used',qv(r.ordering_oh_used,r.uom))+m('28D Qty',qv(r.qty_28d,r.uom))+m('Forecast',qv(r.forecast_total_usage,r.uom))+m('Projected OH @ Delivery',qv(r.projected_oh_at_delivery,r.uom))+'</div>'+(r.promotion_items?.length?'<div class="promo"><b>Promotion UPC</b><div class="meta">'+r.promotion_items.map(x=>esc(x.upc)+' · '+esc(x.upc_name)+' @ '+money(x.promotion_price)).join('<br>')+'</div></div>':'')+'<div class="small">Suggested Order Qty</div><div class="big">'+fmt(r.suggested_order_qty)+' '+esc(r.suggested_order_uom||'')+'</div></div>').join('')||'<div class="card small">No family meets Active 28 supported-day selling + DOS &lt; 7.</div>'}catch(e){$('omsg').textContent=e.message}};
async function pisearch(){
  let q=$('piq').value.trim();if(!q)return;
  $('pim').textContent='Searching Family Articles…';
  try{
    let d=await api('/v1/app/v2/pi/search?q='+encodeURIComponent(q)+'&limit=30');
    $('pim').textContent=d.count+' Family Article(s) · sorted by 28D Qty, then readiness';
    $('pir').innerHTML=(d.results||[]).map((r,i)=>{
      let sys=r.system_oh||{},eff=r.effective_oh||{};
      let sysText=sys.quantity==null?'No OH · '+esc(sys.reason||sys.status||'Reason unavailable'):qv(sys.quantity,sys.uom);
      let effText=eff.quantity==null?'No OH · '+esc(eff.reason||eff.status||'Reason unavailable'):qv(eff.quantity,eff.uom);
      return '<div class="result" data-i="'+i+'">'+
        '<div class="row" style="justify-content:space-between"><div class="name">'+esc(r.family_article_name)+'</div>'+pill(r.readiness)+'</div>'+
        '<div class="meta">Family Article '+esc(r.family_article_number||r.family_id)+' · '+esc(r.category||'—')+'</div>'+
        mr('28D Qty',qv(r.qty_28d,r.qty_28d_uom))+
        mr('System OH',sysText)+
        mr('Effective OH',effText)+
      '</div>';
    }).join('')||'<div class="small">No Family Article found.</div>';
    document.querySelectorAll('#pir .result').forEach(e=>e.onclick=()=>pid(d.results[+e.dataset.i].family_article_number||d.results[+e.dataset.i].family_id));
  }catch(e){$('pim').textContent=e.message}
}
$('pis').onclick=pisearch;$('pic').onclick=()=>{$('piq').value='';$('pir').innerHTML='';$('pim').textContent='';$('piq').focus()};$('piq').onkeydown=e=>{if(e.key==='Enter')pisearch()};
async function pid(k){try{
  let d=await api('/v1/app/v2/pi/'+encodeURIComponent(k)),s=d.system_oh||{},f=d.effective_oh||{},x=d.current_discrepancy||{},r=d.last_receipt||{},fam=d.family||{};
  pifamily=fam.family_article_number||fam.family_id;
  $('pit').textContent=fam.family_article_name||'Family PI';
  $('pisub').textContent='Family Article '+(fam.family_article_number||fam.family_id)+' · '+(fam.category||'—');
  $('pisum').innerHTML=
    ms('Inventory','amber',[
      mr('Family Article',fam.family_article_number||fam.family_id),
      mr('System OH',s.quantity==null?'No OH':qv(s.quantity,s.uom),s.quantity==null?(s.reason||s.status||'OH unavailable'):(s.source||s.status||'')),
      mr('Effective OH',f.quantity==null?'No OH':qv(f.quantity,f.uom),f.quantity==null?(f.reason||f.status||'OH unavailable'):(f.source||f.status||'')),
      mr('Current Difference',qv(x.signed_difference_true_minus_system,x.uom)),
      mr('Last Receipt',r.posting_date||'—')
    ]);
  $('puom').value=d.required_true_stock_uom||'';
  $('pqty').value='';$('pnote').value='';
  $('pih').innerHTML=(d.true_stock_history||[]).map(h=>
    '<tr><td>'+esc(h.submitted_at||'')+'</td><td>'+qv(h.system_oh_quantity,h.uom)+'</td><td>'+qv(h.true_stock_quantity,h.uom)+'</td><td>'+qv(h.signed_difference_true_minus_system,h.uom)+'</td><td>'+esc(h.status||'')+'</td><td>'+esc(h.count_note||'')+'</td></tr>'
  ).join('');
  go('pid')
}catch(e){alert(e.message)}}
$('papply').onclick=async()=>{let q=$('pqty').value.trim(),u=$('puom').value;if(q===''||!u)return;$('pamsg').textContent='Applying Family True Stock…';try{let d=await api('/v1/app/v2/pi/'+encodeURIComponent(pifamily)+'/true-stock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:q,uom:u,note:$('pnote').value||null})});await pid(pifamily);$('pamsg').className='msg success';$('pamsg').textContent='Applied to Family Article · difference '+qv(d.signed_difference_true_minus_system,u)+' · shortage '+qv(d.shortage_quantity,u)+' · overage '+qv(d.overage_quantity,u)}catch(e){$('pamsg').className='msg bad';$('pamsg').textContent=e.message}};

async function initPerformanceDate(){try{let d=await api('/v1/app/v2/performance/dates?limit=180'),rows=d.dates||[];$('perdate').innerHTML=rows.map(x=>'<option value="'+esc(x.date)+'">'+esc(x.weekday)+' · '+esc(x.date)+'</option>').join('');if(!rows.length)$('perdate').innerHTML='<option value="">No supported dates</option>'}catch(e){$('perdate').innerHTML='<option value="">Date list unavailable</option>';$('permsg').textContent=e.message}}
async function performance(){
  let cat=$('percat').value,rd=$('perdate').value;
  $('permsg').textContent='Generating report…';
  $('persummary').innerHTML='';
  $('peranalysis').innerHTML='';
  $('pertop').innerHTML='';
  $('peritems').innerHTML='';
  try{
    let q='/v1/app/v2/performance?category='+encodeURIComponent(cat)+'&limit=100'+(rd?'&report_date='+encodeURIComponent(rd):'');
    let d=await api(q),s=d.summary||{};
    if(d.report_date)$('perdate').value=d.report_date;
    $('permsg').textContent=esc(d.report_date_weekday||'')+' '+esc(d.report_date||'')+' · '+(d.top_urgent_price_suggestions||[]).length+' urgent review item(s)';

    let rec=d.report_date_reconciliation||null;
    $('persummary').innerHTML=
      '<div class="card"><div class="section">'+esc(cat)+' · '+esc(d.report_date_weekday||'')+' '+esc(d.report_date||'')+'</div><div class="grid">'+
        m('Report Date Sales',money(s.report_date_sales_dollars))+
        m('UPCs Sold That Day',fmt(s.upcs_sold_report_date,0))+
        m('Active UPCs 28D',fmt(s.active_upcs_28d,0))+
        m('7D Sales',money(s.sales_dollars_7d))+
        m('14D Sales',money(s.sales_dollars_14d))+
        m('28D Sales',money(s.sales_dollars_28d))+
        m('Slowing Items',fmt(s.slowing_items,0))+
        m('Actionable Price Reviews',fmt(s.price_review_candidates,0))+
      '</div></div>'+
      (cat==='ALL'&&rec
        ? '<div class="card '+(rec.matches_to_cent?'audit-ok':'audit-warn')+'"><div class="section">Sales Audit</div><div class="grid">'+
            m('Canonical POS',money(rec.canonical_source_sales))+
            m('Mapped UPC Total',money(rec.mapped_report_sales))+
            m('Difference',money(rec.difference))+
            m('Unmapped POS',money(rec.unmapped_source_sales))+
            m('Unmapped Qty',rec.unmapped_source_qty==null?(rec.unmapped_qty_mixed_or_unknown?'Mixed / unknown UOM':'—'):qv(rec.unmapped_source_qty,rec.unmapped_source_qty_uom))+
            m('Unmapped UPCs',fmt(rec.unmapped_upc_count,0))+
            m('Source File',rec.canonical_source?.source_file_id??'—')+
          '</div><div class="meta">'+esc(rec.canonical_source?.basis||'')+' · '+esc(rec.canonical_source?.coverage_kind||'')+' · '+(rec.matches_to_cent?'MATCH':'REVIEW REQUIRED')+'</div>'+
          ((rec.top_unmapped_upcs||[]).length
            ? '<div class="section" style="margin-top:16px">Why the Difference</div><div class="hint">Canonical POS rows below are not represented by the current V2 Quick Check serving set.</div>'+
              rec.top_unmapped_upcs.slice(0,12).map(x=>
                '<div class="promo"><div class="row" style="justify-content:space-between"><div><b>UPC '+esc(x.ean_upc||'—')+'</b><div class="meta">'+esc(x.description||x.mapping_status||'Unmapped POS row')+'</div></div><b>'+money(x.sales_amount)+'</b></div><div class="meta">Qty '+qv(x.sold_quantity,x.qty_uom)+' · '+esc(x.mapping_status||'')+'</div></div>'
              ).join('')
            : '')+
          '</div>'
        : '');

    $('peranalysis').innerHTML=
      '<div class="card"><div class="section">Analysis for '+esc(d.report_date||'')+'</div>'+
      (d.analysis||[]).map(x=>
        '<div class="promo"><b>'+esc(x.type.replaceAll('_',' '))+'</b>'+
        '<div class="meta">'+esc(x.message)+'</div>'+
        (x.value_pct!=null?'<div class="'+(Number(x.value_pct)>=0?'ok':'warn')+'">'+fmt(Number(x.value_pct)*100,1)+'%</div>':'')+
        '</div>'
      ).join('')+
      '</div>';

    $('pertop').innerHTML=(d.report_date_top_sellers||[]).map((x,i)=>
      '<div class="promo clickable" data-upc="'+esc(x.upc)+'">'+
        '<div class="row" style="justify-content:space-between"><div><div class="name">#'+(i+1)+' · '+esc(x.name)+'</div><div class="result-upc">UPC '+esc(x.upc)+'</div><div class="meta">'+esc(x.category)+' · Family '+esc(x.family_article_number||'—')+'</div></div>'+pill(x.readiness)+'</div>'+
        '<div class="grid" style="margin-top:10px">'+
          m('Day Sales',money(x.sales_amount))+
          m('Day Qty',qv(x.sold_quantity,x.qty_uom))+
          m('Avg Sold Price',money(x.avg_sold_price))+
          m('7D Velocity',qv(x.velocity_7d,x.qty_uom)+'/day')+
        '</div>'+
        '<div class="meta">'+(x.price_types||[]).map(esc).join(' · ')+'</div>'+
      '</div>'
    ).join('')||'<div class="small">No sales for this category on the selected report date.</div>';

    $('peritems').innerHTML=(d.top_urgent_price_suggestions||[]).map((x,i)=>{
      let cls=x.actionable?'review-actionable':(x.review_status==='QA_HOLD'?'review-hold':'review-only');
      let badge=x.actionable?'ACTIONABLE':(x.review_status||'REVIEW ONLY').replaceAll('_',' ');
      let suggestion=x.suggested_price!=null?money(x.suggested_price):'Review Only';
      let gpopp=x.gp_per_day_opportunity!=null?money(x.gp_per_day_opportunity):'Unproven';
      return '<div class="promo report-item clickable '+cls+'" data-upc="'+esc(x.upc)+'">'+
        '<div class="row" style="justify-content:space-between"><div><div class="name">#'+(i+1)+' · '+esc(x.name)+'</div><div class="result-upc">UPC '+esc(x.upc)+'</div><div class="meta">'+esc(x.category)+' · Family '+esc(x.family_article_number||'—')+'</div></div><span class="pill '+(x.actionable?'ok':'warn')+' review-badge">'+esc(badge)+'</span></div>'+
        '<div class="row" style="margin-top:10px"><div><div class="small">Price Used</div><div class="hero-number">'+money(x.current_price)+'</div></div><div class="price-arrow">→</div><div><div class="small">'+(x.actionable?'Suggested':'Review Status')+'</div><div class="hero-number">'+suggestion+'</div></div></div>'+
        '<div class="grid" style="margin-top:10px">'+
          m('GP$/day Opportunity',gpopp)+
          m('Urgency',fmt(x.urgency_score,1))+
          m('7D Qty',qv(x.qty_7d,x.qty_uom))+
          m('28D Qty',qv(x.qty_28d,x.qty_uom))+
        '</div>'+
        '<div class="meta">Sales evidence through '+esc(x.report_date)+' · '+(x.review_blocker?'Review reason '+esc(x.review_blocker.replaceAll('_',' ')):'Price evidence supports action')+'</div>'+
        '<div class="meta">Company C floor '+money(x.company_price_c_floor)+' · Basis '+esc(x.suggestion_basis||'—')+'</div>'+
        '<div class="meta">'+(x.reasons||[]).map(r=>esc(r.replaceAll('_',' '))).join(' · ')+'</div>'+
      '</div>';
    }).join('')||'<div class="small">No active items available for review.</div>';

    document.querySelectorAll('#pertop [data-upc],#peritems [data-upc]').forEach(e=>e.onclick=()=>price(e.dataset.upc));
  }catch(e){
    $('permsg').textContent=e.message;
  }
}
$('perrun').onclick=performance;
initPerformanceDate();
</script></body></html>"""

def webapp_v2_html() -> str:
    return WEBAPP_V2_HTML
