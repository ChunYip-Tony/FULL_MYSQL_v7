from __future__ import annotations


def backoffice_html(version: str = "") -> str:
    v = str(version or "")
    return BACKOFFICE_HTML.replace("__VERSION__", v)


BACKOFFICE_HTML = r'''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>FULL MYSQL · Dockside Backoffice</title>
<style>
:root{--bg:#f2f5f4;--paper:#fff;--ink:#153638;--muted:#6c7e7d;--line:#dbe6e2;--deep:#0b343a;--deep2:#103f46;--sea:#167985;--sea2:#2ca0a8;--foam:#e9f5f3;--green:#116b49;--greenbg:#e8f6ee;--amber:#946000;--amberbg:#fff4df;--red:#bd4f44;--redbg:#fff0ed;--blue:#275bb5;--bluebg:#edf3ff;--shadow:0 10px 28px rgba(9,49,54,.06)}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}body{font-size:16px;line-height:1.45}button,input,select,textarea{font:inherit;color:inherit}button{cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid rgba(44,160,168,.18);outline-offset:2px}
.shell{max-width:1720px;margin:auto;padding:10px 10px 70px}.appbar{background:linear-gradient(135deg,var(--deep),var(--deep2));color:#fff;border-radius:18px;overflow:hidden;box-shadow:var(--shadow)}.top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:12px 14px}.brand{display:flex;gap:10px;align-items:center}.mark{width:40px;height:40px;border-radius:12px;background:rgba(255,255,255,.1);display:grid;place-items:center;font-size:20px}.brand strong{display:block;font-size:15px}.brand small{display:block;color:rgba(255,255,255,.67);margin-top:2px}.topstat{display:flex;gap:6px;flex-wrap:wrap}.glass{border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.08);border-radius:999px;padding:6px 9px;font-size:10px;font-weight:800}.searchbar{display:flex;gap:7px;padding:0 14px 10px}.searchbar input{flex:1;min-width:0;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.13);color:#fff;border-radius:11px;padding:10px 12px}.searchbar input::placeholder{color:rgba(255,255,255,.55)}
.nav{display:flex;gap:3px;overflow:auto;padding:0 10px 10px}.nav button{border:0;background:transparent;color:#d2e6e6;border-radius:8px;padding:9px 11px;white-space:nowrap;font-size:13px}.nav button.on{background:#fff;color:var(--deep);font-weight:800}.btn{min-height:36px;border:1px solid var(--line);background:#fff;border-radius:9px;padding:7px 10px;font-weight:750}.btn.primary{background:var(--sea);border-color:var(--sea);color:#fff}.btn.soft{background:var(--foam);border-color:transparent;color:var(--sea)}.btn.danger{background:var(--red);border-color:var(--red);color:#fff}.btn.small{min-height:32px;font-size:11px;padding:6px 9px}.btn:disabled{opacity:.5;cursor:not-allowed}
.pill{display:inline-flex;align-items:center;border-radius:999px;padding:5px 8px;font-size:9px;font-weight:800;white-space:nowrap}.pill.green{background:var(--greenbg);color:var(--green)}.pill.amber{background:var(--amberbg);color:var(--amber)}.pill.red{background:var(--redbg);color:var(--red)}.pill.blue{background:var(--bluebg);color:var(--blue)}.pill.sea{background:var(--foam);color:var(--sea)}
.statusstrip{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:9px}.stat{background:#fff;border:1px solid var(--line);border-radius:12px;padding:9px 10px}.stat small{display:block;color:var(--muted);font-size:8px}.stat b{display:block;font-size:17px;margin-top:2px}.stat span{display:block;color:var(--muted);font-size:8px;margin-top:2px}
.view{display:none}.view.on{display:block}.subview{display:none}.subview.on{display:block}.panel{margin-top:9px;background:#fff;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:var(--shadow)}.panelhead{display:flex;align-items:flex-start;justify-content:space-between;gap:9px;flex-wrap:wrap;padding:11px 12px;border-bottom:1px solid var(--line)}.title{font-size:19px;font-weight:850}.sub{font-size:11px;color:var(--muted);margin-top:3px}.tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.toolrow{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:8px 11px;border-bottom:1px solid var(--line)}.filters{display:flex;gap:5px;flex-wrap:wrap}.filter{border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 10px;font-size:11px}.filter.on{background:var(--foam);border-color:transparent;color:var(--sea);font-weight:800}.select{border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 9px;font-size:12px}
.tablewrap{overflow:auto}.table{width:100%;min-width:980px;border-collapse:collapse;font-size:12px}.table th,.table td{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}.table th{background:#f7faf9;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.035em}.table tbody tr:hover td{background:#fbfdfc}.name{font-weight:800;font-size:13px}.meta{font-size:10px;color:var(--muted);margin-top:2px}.num{font-variant-numeric:tabular-nums}.linkbtn{border:0;background:transparent;padding:2px 0;text-decoration:underline;text-decoration-style:dotted;text-underline-offset:3px;font-weight:850}.suggest{font-weight:900;color:var(--sea);font-size:11px}.empty{padding:28px;text-align:center;color:var(--muted);font-size:10px}.loading{padding:22px;color:var(--muted);font-size:10px}.error{padding:10px 12px;background:var(--redbg);color:var(--red);font-size:10px;border-bottom:1px solid #f0cac4}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:11px}.kpi{border:1px solid var(--line);border-radius:10px;padding:8px;background:#fbfdfc}.kpi small{display:block;color:var(--muted);font-size:8px}.kpi b{display:block;font-size:14px;margin-top:2px}.kpi span{display:block;color:var(--muted);font-size:8px;margin-top:2px}
.reasonlist{display:grid;gap:6px}.reason{display:grid;grid-template-columns:auto 1fr;gap:7px;border:1px solid var(--line);border-radius:10px;padding:8px;background:#fbfdfc}.rdot{width:7px;height:7px;border-radius:50%;background:var(--sea);margin-top:4px}.reason b{display:block;font-size:10px}.reason span{display:block;color:var(--muted);font-size:9px;margin-top:1px}.sectiontitle{font-size:10px;font-weight:850;margin:13px 0 6px}.detailgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.detail{border:1px solid var(--line);border-radius:9px;padding:8px;background:#fbfdfc}.detail small{display:block;color:var(--muted);font-size:8px}.detail b{display:block;font-size:10px;margin-top:2px}.calc{border:1px dashed #b9d4cf;background:#f4fbf9;border-radius:9px;padding:8px;margin-top:8px;font-size:9px;color:var(--deep)}.logconsole{background:#0b272b;color:#d8efec;border-radius:10px;padding:9px;font:9px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-height:230px;overflow:auto}
.dbcardgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:11px}.dbcard{border:1px solid var(--line);background:#fff;border-radius:13px;padding:13px;text-align:left;display:flex;gap:11px;align-items:flex-start;box-shadow:0 4px 14px rgba(9,49,54,.03)}.dbcard:hover{border-color:#a8cbc6;background:#fbfdfc}.dbcard .dbicon{font-size:24px;line-height:1}.dbcard span:last-child{display:block}.dbcard small{display:block;color:var(--muted);font-size:9px;font-weight:800;text-transform:uppercase}.dbcard b{display:block;font-size:14px;margin-top:2px}.dbcard em{display:block;color:var(--muted);font-size:10px;font-style:normal;margin-top:3px}.dboverviewgrid{display:grid;grid-template-columns:1fr;gap:9px;padding:0 11px 11px}.dbsummary{border:1px solid var(--line);border-radius:12px;padding:0 10px 10px;background:#fbfdfc}.uploadgrid{display:grid;gap:9px;padding:11px}.drop{border:2px dashed #bad5d1;background:#f8fcfb;border-radius:13px;padding:18px;text-align:center}.drop .ico{font-size:29px}.drop h3{font-size:14px;margin:6px 0 2px}.drop p{font-size:9px;color:var(--muted);margin:0}.drop input{display:block;width:100%;margin-top:10px;border:1px solid var(--line);border-radius:9px;padding:8px;background:#fff}.upload-actions{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;margin-top:9px}.uploadresult{border:1px solid var(--line);border-radius:11px;padding:9px;background:#fbfdfc}.filelist{display:grid;gap:5px;margin-top:7px}.filerow{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--line);padding:6px 0;font-size:9px}.filerow:last-child{border:0}
.batchgrid{display:grid;gap:7px;padding:10px}.batch{border:1px solid var(--line);border-radius:11px;padding:9px;background:#fbfdfc}.batchtop{display:flex;justify-content:space-between;gap:8px}.batchid{font-weight:850;font-size:11px}.progress{height:6px;border-radius:999px;background:#e7efeb;overflow:hidden;margin-top:7px}.progress span{display:block;height:100%;background:linear-gradient(90deg,var(--sea),var(--sea2))}.batchmeta{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:7px}.batchmeta div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px}.batchmeta small{display:block;color:var(--muted);font-size:7px}.batchmeta b{display:block;font-size:9px;margin-top:1px}
.drawerback{position:fixed;inset:0;background:rgba(7,43,47,.24);z-index:30;display:none}.drawerback.on{display:block}.drawer{position:fixed;right:0;top:0;bottom:0;width:min(94vw,570px);background:#fff;z-index:31;transform:translateX(105%);transition:.18s;box-shadow:-20px 0 50px rgba(8,44,48,.18);display:flex;flex-direction:column}.drawer.on{transform:translateX(0)}.drawerhead{padding:12px 13px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:9px}.drawertitle{font-size:15px;font-weight:850}.drawersub{font-size:9px;color:var(--muted);margin-top:2px}.drawerbody{padding:12px;overflow:auto;flex:1}.drawerfoot{padding:10px 12px;border-top:1px solid var(--line);display:flex;justify-content:flex-end;gap:6px}.formfield{margin-top:9px}.formfield label{display:block;font-size:9px;font-weight:800;margin-bottom:4px}.formfield input,.formfield textarea,.formfield select{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}.toast{position:fixed;right:12px;bottom:12px;z-index:50;background:var(--deep);color:#fff;border-radius:9px;padding:9px 10px;font-size:10px;opacity:0;transform:translateY(8px);transition:.18s;pointer-events:none}.toast.on{opacity:1;transform:none}
@media(min-width:760px){.shell{padding:12px 12px 30px}.dbcardgrid{grid-template-columns:repeat(4,minmax(0,1fr))}.dboverviewgrid{grid-template-columns:1fr 1fr}.statusstrip{grid-template-columns:repeat(4,minmax(0,1fr))}.grid{grid-template-columns:repeat(4,minmax(0,1fr))}.detailgrid{grid-template-columns:repeat(4,minmax(0,1fr))}.uploadgrid{grid-template-columns:1fr 1fr}}
@media(max-width:620px){.shell{padding:7px 7px 76px}.appbar{border-radius:13px}.nav button{font-size:10px}.statusstrip{grid-template-columns:1fr 1fr}.table{min-width:900px}.panel{border-radius:13px}.searchbar{padding-left:10px;padding-right:10px}}
</style>
</head>
<body>
<div class="shell">
<header class="appbar">
  <div class="top">
    <div class="brand"><div class="mark">⚓</div><div><strong>Dockside Backoffice</strong><small>FULL MYSQL · Seafood Operations · v__VERSION__</small></div></div>
    <div class="topstat"><span id="readyPill" class="glass">Checking...</span><span id="posPill" class="glass">POS —</span><span id="pricePill" class="glass">Price —</span></div>
  </div>
  <form id="searchForm" class="searchbar"><input id="searchInput" placeholder="Search UPC, Article, Family, Item"><button class="btn glass">Search</button></form>
  <nav class="nav">
    <button class="navbtn on" data-view="inventory">Inventory</button>
    <button class="navbtn" data-view="sales">Sales Performance</button>
    <button class="navbtn" data-view="ordering">Ordering Overview</button>
    <button class="navbtn" data-view="pricing">Pricing Review</button>
    <button class="navbtn" data-view="database">Database Center</button>
  </nav>
</header>
<section id="inventory" class="view on"><div class="panel">
 <div class="panelhead"><div><div class="title">Inventory Ledger</div><div class="sub">Read-only system data. OH / True Stock is the only editable value.</div></div><span class="pill blue">OH WRITE ONLY</span></div>
 <div class="toolrow"><div class="filters"><button class="filter invfilter on" data-cat="ALL">All</button><button class="filter invfilter" data-cat="FRESH">Fresh</button><button class="filter invfilter" data-cat="LIVE">Live</button><button class="filter invfilter" data-cat="FROZEN">Frozen</button></div><div class="tools"><span id="invSearchState" class="pill blue" style="display:none"></span><button id="clearInventorySearch" class="btn small" style="display:none">Clear Search</button><span id="invCount" class="pill sea">—</span></div></div>
 <div id="invError"></div><div class="tablewrap"><table class="table"><thead><tr><th>Item</th><th>UPC</th><th>Family</th><th>OH</th><th>7D Qty</th><th>Price</th><th>Cost</th><th>GP%</th><th>DOS</th><th>Status</th></tr></thead><tbody id="invRows"></tbody></table></div>
</div></section>



<section id="ordering" class="view"><div class="panel">
 <div class="panelhead"><div><div class="title">Ordering Overview</div><div class="sub">Receiving / Ordering Article + Family Article decision level. Selling UPCs appear only inside Details.</div></div><span class="pill blue">READ ONLY</span></div>
 <div class="toolrow"><div class="filters"><button class="filter ordfilter on" data-filter="ALL">All</button><button class="filter ordfilter" data-filter="FRESH">Fresh</button><button class="filter ordfilter" data-filter="FROZEN">Frozen</button><button class="filter ordfilter" data-filter="ATTENTION">Needs Attention</button></div><div class="tools"><select id="orderSort" class="select"><option value="suggested">Highest Suggested Qty</option><option value="receipt">Most Recent Receipt</option><option value="oh">Lowest OH</option><option value="frequency">Ordering Frequency</option><option value="family">Family A → Z</option></select><span id="orderCount" class="pill sea">—</span></div></div>
 <div id="orderError"></div><div class="tablewrap"><table class="table"><thead><tr><th>Family Name</th><th>Receiving Article</th><th>Family Article</th><th>OH</th><th>Last Receipt Date</th><th>Last Receipt Qty · Base UOM</th><th>Ordering Frequency</th><th>Coming Delivery Qty Suggestion</th><th></th></tr></thead><tbody id="orderRows"></tbody></table></div>
</div></section>

<section id="sales" class="view">
<div class="panel">
 <div class="panelhead"><div><div class="title">Sales Performance</div><div class="sub">Latest completed canonical sales date, item movement, sales, selling price, and velocity performance.</div></div><span class="pill blue">READ ONLY</span></div>
 <div id="sellKpi" class="grid"></div><div id="sellError"></div><div class="tablewrap"><table class="table"><thead><tr><th>Item</th><th>UPC</th><th>Category</th><th>Qty</th><th>Sales</th><th>Avg Sold Price</th><th>7D Vel</th><th>28D Vel</th></tr></thead><tbody id="sellRows"></tbody></table></div>
</div>
</section>

<section id="pricing" class="view">
<div class="panel">
 <div class="panelhead"><div><div class="title">Pricing Review</div><div class="sub">Explainable price suggestions. No staging, approval, or system price changes.</div></div><span class="pill blue">READ ONLY</span></div>
 <div class="toolrow">
   <div class="filters"><button class="filter pricefilter on" data-cat="ALL">All</button><button class="filter pricefilter" data-cat="FRESH">Fresh</button><button class="filter pricefilter" data-cat="LIVE">Live</button><button class="filter pricefilter" data-cat="FROZEN">Frozen</button></div>
   <div class="tools">
     <input id="priceTextFilter" class="select" style="min-width:150px" placeholder="Filter item / UPC">
     <select id="priceStatusFilter" class="select">
       <option value="ALL">All Review Status</option>
       <option value="ACTIONABLE">Actionable</option>
       <option value="REVIEW_ONLY">Review Only</option>
       <option value="WAIT_ACTIVE_SALE">Wait / Active Sale</option>
       <option value="QA_HOLD">QA Hold</option>
     </select>
     <select id="priceSort" class="select">
       <option value="opportunity">Highest GP$/Day Opportunity</option>
       <option value="urgency">Highest Urgency</option>
       <option value="gap">Largest Price Gap %</option>
       <option value="qty7">Highest 7D Qty</option>
       <option value="qty28">Highest 28D Qty</option>
       <option value="lowgp">Lowest GP%</option>
       <option value="currentprice">Highest Current Price</option>
       <option value="name">Item A → Z</option>
     </select>
     <span id="priceCount" class="pill sea">—</span>
   </div>
 </div>
 <div id="priceError"></div><div class="tablewrap"><table class="table" style="min-width:1150px"><thead><tr><th>Item</th><th>UPC</th><th>Current</th><th>Candidate</th><th>Cost</th><th>GP%</th><th>7D Qty</th><th>28D Qty</th><th>Review Status</th><th>Primary Reason</th><th></th></tr></thead><tbody id="priceRows"></tbody></table></div>
</div>
</section>

<section id="database" class="view">
  <div class="panel">
    <div class="panelhead">
      <div><div class="title">Database Center</div><div class="sub">Upload → Processing → QA → Data Health. Start with Overview to see what needs attention.</div></div>
      <button id="dbRefreshAll" class="btn small">Refresh All</button>
    </div>
    <div class="toolrow">
      <div class="filters">
        <button class="filter dbtab on" data-dbtab="dboverview">Overview</button>
        <button class="filter dbtab" data-dbtab="dbupload">Upload Files</button>
        <button class="filter dbtab" data-dbtab="dbbatches">Processing</button>
        <button class="filter dbtab" data-dbtab="dbqa">QA Fixes</button>
        <button class="filter dbtab" data-dbtab="dbdata">Data Health</button>
      </div>
    </div>
  </div>

  <div id="dboverview" class="subview on">
    <div class="panel">
      <div class="panelhead">
        <div><div class="title">Database Overview</div><div class="sub">What is happening now and where you need to go next.</div></div>
        <span id="dbOverallStatus" class="pill blue">CHECKING</span>
      </div>
      <div id="dbOverviewError"></div>
      <div class="dbcardgrid">
        <button class="dbcard dbjump" data-target="dbupload"><span class="dbicon">📤</span><span><small>Step 1</small><b>Upload Files</b><em id="dbUploadSummary">Start a new source batch</em></span></button>
        <button class="dbcard dbjump" data-target="dbbatches"><span class="dbicon">⚙️</span><span><small>Step 2</small><b>Processing</b><em id="dbProcessingSummary">Checking current batch…</em></span></button>
        <button class="dbcard dbjump" data-target="dbqa"><span class="dbicon">🧩</span><span><small>Step 3</small><b>QA Fixes</b><em id="dbQASummary">Checking open issues…</em></span></button>
        <button class="dbcard dbjump" data-target="dbdata"><span class="dbicon">🩺</span><span><small>Step 4</small><b>Data Health</b><em id="dbHealthSummary">Checking service health…</em></span></button>
      </div>
      <div class="dboverviewgrid">
        <div class="dbsummary"><div class="sectiontitle">Current Processing</div><div id="dbOverviewActive" class="batchgrid" style="padding:0"></div></div>
        <div class="dbsummary"><div class="sectiontitle">Latest Completed Batch</div><div id="dbLatestBatch" class="batchgrid" style="padding:0"></div></div>
      </div>
    </div>
  </div>

  <div id="dbupload" class="subview"><div class="panel">
    <div class="panelhead"><div><div class="title">Upload Files</div><div class="sub">Select all source files that belong together. One upload action creates one immutable batch and starts processing.</div></div><span class="pill sea">DIRECT UPLOAD</span></div>
    <div class="uploadgrid" style="grid-template-columns:1fr">
      <div class="drop"><div class="ico">📤</div><h3>Select source files</h3><p>XLSX / XLS / XLSM / CSV / TXT / TSV. Files selected together are one batch.</p><input id="uploadFiles" type="file" multiple accept=".xlsx,.xls,.xlsm,.csv,.txt,.tsv"><div class="formfield"><label>Optional batch note</label><input id="uploadNote" placeholder="Daily seafood upload"></div><div class="upload-actions"><button id="uploadBtn" class="btn primary">Upload & Start Processing</button></div></div>
      <div><div class="sectiontitle">Latest Upload Result</div><div id="uploadResult" class="uploadresult"><span class="meta">No upload in this session.</span></div></div>
    </div>
  </div></div>

  <div id="dbbatches" class="subview"><div class="panel">
    <div class="panelhead"><div><div class="title">Processing</div><div class="sub">Current batch first. Completed / failed batches stay in history below.</div></div><button id="refreshBatch" class="btn small">Refresh</button></div>
    <div class="sectiontitle" style="padding:0 11px">Current Active Batch</div><div id="activeBatch" class="batchgrid"></div>
    <div class="sectiontitle" style="padding:0 11px">Processing History</div><div id="batchError"></div><div class="tablewrap"><table class="table"><thead><tr><th>Batch</th><th>Status</th><th>Files</th><th>Started</th><th>Completed</th><th>Publish</th><th>QC Ready / Hold</th></tr></thead><tbody id="batchRows"></tbody></table></div>
  </div></div>

  <div id="dbqa" class="subview"><div class="panel">
    <div class="panelhead"><div><div class="title">QA Fixes</div><div class="sub">Only issues that require review or user-confirmed correction. Raw source rows are never edited.</div></div><span class="pill amber">CONTROLLED FIX</span></div>
    <div class="toolrow"><div class="filters"><button class="filter qafilter on" data-qafilter="ALL">All Open</button><button class="filter qafilter" data-qafilter="FIXABLE">Fixable</button><button class="filter qafilter" data-qafilter="VIEW_ONLY">Review Only</button><button class="filter qafilter" data-qafilter="HIGH">High / Critical</button></div><div class="tools"><span id="qaCount" class="pill sea">—</span><button id="qaRefresh" class="btn small">Refresh</button></div></div>
    <div id="qaError"></div>
    <div class="tablewrap"><table class="table" style="min-width:1050px"><thead><tr><th>Severity</th><th>Issue</th><th>Entity</th><th>Current State</th><th>Fix Type</th><th></th></tr></thead><tbody id="qaRows"></tbody></table></div>
    <div class="sectiontitle" style="padding:0 11px">Recent Resolution History</div>
    <div class="tablewrap"><table class="table"><thead><tr><th>Time</th><th>Entity</th><th>Issue</th><th>Resolution</th><th>Actor</th><th>Note</th></tr></thead><tbody id="qaHistoryRows"></tbody></table></div>
  </div></div>

  <div id="dbdata" class="subview"><div class="panel">
    <div class="panelhead"><div><div class="title">Data Health</div><div class="sub">Service health, worker status, latest publish, and recent pipeline outcomes.</div></div><button id="refreshData" class="btn small">Refresh</button></div>
    <div id="dataGrid" class="grid"></div><div id="dataEvents" class="batchgrid"></div>
  </div></div>
</section>

<div id="drawerBack" class="drawerback"></div><aside id="drawer" class="drawer"><div class="drawerhead"><div><div id="drawerTitle" class="drawertitle">Details</div><div id="drawerSub" class="drawersub"></div></div><button id="drawerClose" class="btn small">Close</button></div><div id="drawerBody" class="drawerbody"></div><div id="drawerFoot" class="drawerfoot"></div></aside>
<div id="toast" class="toast"></div>
</div>
<script>
(()=>{
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const state={invCat:'ALL',inventorySearch:'',orderFilter:'ALL',priceCat:'ALL',priceStatus:'ALL',priceSort:'opportunity',priceText:'',qaFilter:'ALL',qaIssues:[],qaHistory:[],inventory:[],orders:[],prices:[],recent:[],active:null};
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmt(v,d=1){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):esc(v)}
function money(v){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?'$'+n.toFixed(2):esc(v)}
function pct(v){if(v===null||v===undefined||v==='')return '—';let n=Number(v);if(Math.abs(n)<=1.5)n*=100;return Number.isFinite(n)?n.toFixed(1)+'%':esc(v)}
function pill(status){const s=String(status||'UNKNOWN').toUpperCase();let c='blue';if(s.includes('READY')||s==='PASS'||s==='ACTIVE')c='green';else if(s.includes('FAIL')||s.includes('BLOCK')||s==='OUT')c='red';else if(s.includes('HOLD')||s.includes('PROCESS')||s.includes('QUEUED')||s.includes('WAIT')||s==='WATCH')c='amber';return `<span class="pill ${c}">${esc(s)}</span>`}
function toast(t){const x=$('#toast');x.textContent=t;x.classList.add('on');clearTimeout(toast.t);toast.t=setTimeout(()=>x.classList.remove('on'),2200)}
async function api(url,opts={}){const r=await fetch(url,{cache:'no-store',...opts});let data=null;try{data=await r.json()}catch{data={detail:await r.text()}}if(!r.ok){const d=data?.detail;throw new Error(typeof d==='string'?d:(d?.message||d?.reason||JSON.stringify(d)||`HTTP ${r.status}`))}return data}
function show(view){$$('.view').forEach(x=>x.classList.toggle('on',x.id===view));$$('.navbtn').forEach(x=>x.classList.toggle('on',x.dataset.view===view));if(view==='inventory')loadInventory();if(view==='sales')loadSell();if(view==='ordering')loadOrders();if(view==='pricing')loadPrices();if(view==='database')showDbTab('dboverview');window.scrollTo({top:0,behavior:'smooth'})}
function showDbTab(tab){$$('#database .subview').forEach(x=>x.classList.toggle('on',x.id===tab));$$('.dbtab').forEach(x=>x.classList.toggle('on',x.dataset.dbtab===tab));if(tab==='dboverview')loadDatabaseOverview();if(tab==='dbbatches')loadBatches();if(tab==='dbqa')loadQA();if(tab==='dbdata')loadData()}
$$('.navbtn').forEach(b=>b.onclick=()=>show(b.dataset.view));
$$('.dbtab').forEach(b=>b.onclick=()=>showDbTab(b.dataset.dbtab));
$$('.dbjump').forEach(b=>b.onclick=()=>showDbTab(b.dataset.target));
function openDrawer(title,sub,body,foot=''){ $('#drawerTitle').textContent=title;$('#drawerSub').textContent=sub||'';$('#drawerBody').innerHTML=body;$('#drawerFoot').innerHTML=foot;$('#drawerBack').classList.add('on');$('#drawer').classList.add('on') }
function closeDrawer(){$('#drawerBack').classList.remove('on');$('#drawer').classList.remove('on')}$('#drawerClose').onclick=closeDrawer;$('#drawerBack').onclick=closeDrawer;

async function loadHealth(){try{const h=await api('/healthz');$('#readyPill').textContent=h.ok?'SERVICE READY':'SERVICE ISSUE';$('#readyPill').style.color=h.ok?'#bff3d2':'#ffd0c8'}catch(e){$('#readyPill').textContent='SERVICE ERROR'}}
async function loadInventory(){const err=$('#invError');err.innerHTML='';$('#invRows').innerHTML='<tr><td colspan="10" class="loading">Loading...</td></tr>';try{const q=state.inventorySearch.trim();const url=`/v1/backoffice/inventory?category=${encodeURIComponent(state.invCat)}&limit=300${q?'&q='+encodeURIComponent(q):''}`;const d=await api(url);state.inventory=d.rows||[];$('#invCount').textContent=`${d.count||0} items`;const badge=$('#invSearchState'),clear=$('#clearInventorySearch');if(q){badge.textContent=`Search: ${q}`;badge.style.display='inline-flex';clear.style.display='inline-flex'}else{badge.style.display='none';clear.style.display='none'}renderInventory()}catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#invRows').innerHTML=''}}
function renderInventory(){const rows=state.inventory;$('#invRows').innerHTML=rows.map(r=>`<tr><td><div class="name">${esc(r.name)}</div><div class="meta">${esc(r.category||'')} · ${esc(r.price_type||'')}</div></td><td>${esc(r.upc)}</td><td><b>${esc(r.family_article||'—')}</b><div class="meta">${esc(r.family_name||'')}</div></td><td><button class="linkbtn ohbtn" data-family="${esc(r.family_article||'')}" data-uom="${esc(r.family_oh_uom||'')}" data-oh="${esc(r.family_oh??'')}" data-name="${esc(r.family_name||r.name)}">${fmt(r.family_oh)} ${esc(r.family_oh_uom||'')}</button></td><td>${fmt(r.qty_7d)}</td><td>${money(r.price)}</td><td>${money(r.cost)}</td><td>${pct(r.gp_pct)}</td><td>${fmt(r.dos)}</td><td>${pill(r.readiness)}</td></tr>`).join('')||`<tr><td colspan="10" class="empty">${state.inventorySearch?'No FULL MYSQL matches for: '+esc(state.inventorySearch):'No inventory rows available.'}</td></tr>`;$$('.ohbtn').forEach(b=>b.onclick=()=>openOH(b.dataset))}
$$('.invfilter').forEach(b=>b.onclick=()=>{state.invCat=b.dataset.cat;$$('.invfilter').forEach(x=>x.classList.toggle('on',x===b));loadInventory()});$('#clearInventorySearch').onclick=()=>{state.inventorySearch='';$('#searchInput').value='';loadInventory()};

function openOH(d){if(!d.family){toast('Family Article unavailable');return}const current=d.oh||'';openDrawer('OH / True Stock Adjustment',`${d.name} · Family ${d.family}`,`<div class="detailgrid"><div class="detail"><small>Family Article</small><b>${esc(d.family)}</b></div><div class="detail"><small>System / Effective OH</small><b>${fmt(current)} ${esc(d.uom)}</b></div></div><div class="formfield"><label>True Stock</label><input id="trueStockInput" type="number" min="0" step="0.01" value="${esc(current)}"></div><div class="formfield"><label>UOM</label><input id="trueStockUom" value="${esc(d.uom)}" readonly></div><div class="formfield"><label>Note</label><textarea id="trueStockNote" placeholder="Physical count / OH adjustment"></textarea></div><div id="ohPreview" class="calc">Difference: 0</div>`,`<button id="saveOH" class="btn primary">Save OH Adjustment</button>`);const inp=$('#trueStockInput');inp.oninput=()=>{const n=Number(inp.value||0),o=Number(current||0),diff=n-o;$('#ohPreview').textContent=`Difference: ${diff>=0?'+':''}${diff.toFixed(2)}${diff<0?' · shortage / pending dumping '+Math.abs(diff).toFixed(2):''}`};$('#saveOH').onclick=async()=>{try{$('#saveOH').disabled=true;await api(`/v1/app/v2/pi/${encodeURIComponent(d.family)}/true-stock`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:Number(inp.value),uom:d.uom,note:$('#trueStockNote').value||null})});toast('OH / True Stock saved');closeDrawer();await loadInventory()}catch(e){toast(e.message)}finally{const x=$('#saveOH');if(x)x.disabled=false}}}

async function loadSell(){try{const d=await api('/v1/app/v2/performance?category=ALL&limit=100');const s=d.summary||{};$('#sellKpi').innerHTML=`<div class="kpi"><small>Report Date</small><b>${esc(d.report_date||'—')}</b><span>${esc(d.report_date_weekday||'')}</span></div><div class="kpi"><small>Sales</small><b>${money(s.report_date_sales_dollars)}</b><span>Canonical report date</span></div><div class="kpi"><small>Active UPCs 28D</small><b>${fmt(s.active_upcs_28d,0)}</b><span>Seafood scope</span></div><div class="kpi"><small>Slowing Items</small><b>${fmt(s.slowing_items,0)}</b><span>7D below 80% of 28D</span></div>`;$('#sellRows').innerHTML=(d.report_date_top_sellers||[]).map(r=>`<tr><td><div class="name">${esc(r.name)}</div><div class="meta">Family ${esc(r.family_article_number||'')}</div></td><td>${esc(r.upc)}</td><td>${esc(r.category)}</td><td>${fmt(r.sold_quantity)} ${esc(r.qty_uom||'')}</td><td>${money(r.sales_amount)}</td><td>${money(r.avg_sold_price)}</td><td>${fmt(r.velocity_7d)}</td><td>${fmt(r.velocity_28d)}</td></tr>`).join('')||'<tr><td colspan="8" class="empty">No report rows.</td></tr>'}catch(e){$('#sellError').innerHTML=`<div class="error">${esc(e.message)}</div>`}}

async function loadOrders(){const err=$('#orderError');err.innerHTML='';$('#orderRows').innerHTML='<tr><td colspan="9" class="loading">Loading...</td></tr>';try{const d=await api('/v1/backoffice/ordering-review?category=ALL');state.orders=d.rows||[];renderOrders()}catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#orderRows').innerHTML=''}}
function orderRows(){let a=[...state.orders];if(state.orderFilter==='FRESH')a=a.filter(x=>String(x.category).toUpperCase()==='FRESH');if(state.orderFilter==='FROZEN')a=a.filter(x=>String(x.category).toUpperCase()==='FROZEN');if(state.orderFilter==='ATTENTION')a=a.filter(x=>x.attention);const s=$('#orderSort').value;if(s==='suggested')a.sort((x,y)=>Number(y.suggested_delivery_qty||0)-Number(x.suggested_delivery_qty||0));if(s==='receipt')a.sort((x,y)=>String(y.last_receipt_date||'').localeCompare(String(x.last_receipt_date||'')));if(s==='oh')a.sort((x,y)=>Number(x.oh??1e18)-Number(y.oh??1e18));if(s==='frequency')a.sort((x,y)=>String(x.ordering_frequency||'').localeCompare(String(y.ordering_frequency||'')));if(s==='family')a.sort((x,y)=>String(x.family_name||'').localeCompare(String(y.family_name||'')));return a}
function renderOrders(){const a=orderRows();$('#orderCount').textContent=`${a.length} families`;$('#orderRows').innerHTML=a.map(r=>`<tr><td><div class="name">${esc(r.family_name||'—')}</div></td><td><b>${esc(r.receiving_article||'—')}</b></td><td><b>${esc(r.family_article||'—')}</b></td><td>${fmt(r.oh)} ${esc(r.oh_uom||'')}</td><td>${esc(r.last_receipt_date||'—')}</td><td><b>${fmt(r.last_receipt_qty_base)} ${esc(r.last_receipt_base_uom||'')}</b></td><td>${esc(r.ordering_frequency||'—')}</td><td><span class="suggest">${fmt(r.suggested_delivery_qty)} ${esc(r.suggested_delivery_uom||'')}</span></td><td><button class="btn small orderdetail" data-family="${esc(r.family_article)}">Details / Why?</button></td></tr>`).join('')||'<tr><td colspan="9" class="empty">No ordering suggestions match this filter.</td></tr>';$$('.orderdetail').forEach(b=>b.onclick=()=>openOrderDetail(b.dataset.family))}
$$('.ordfilter').forEach(b=>b.onclick=()=>{state.orderFilter=b.dataset.filter;$$('.ordfilter').forEach(x=>x.classList.toggle('on',x===b));renderOrders()});$('#orderSort').onchange=renderOrders;
function openOrderDetail(fam){const r=state.orders.find(x=>String(x.family_article)===String(fam));if(!r)return;const d=r.details||{},reasons=d.reasons||[], recArts=d.receiving_articles_on_last_receipt||[];openDrawer('Ordering Detail / Why?',`${r.family_name} · Family ${r.family_article}`,`<div class="detailgrid"><div class="detail"><small>Receiving Article</small><b>${esc(r.receiving_article||'—')}</b></div><div class="detail"><small>Family OH</small><b>${fmt(r.oh)} ${esc(r.oh_uom||'')}</b></div><div class="detail"><small>Last Receipt</small><b>${esc(r.last_receipt_date||'—')}</b></div><div class="detail"><small>Receipt Qty · Base</small><b>${fmt(r.last_receipt_qty_base)} ${esc(r.last_receipt_base_uom||'')}</b></div><div class="detail"><small>Family 7D Movement</small><b>${fmt(d.qty_7d)}</b></div><div class="detail"><small>Family 28D Movement</small><b>${fmt(d.qty_28d)}</b></div><div class="detail"><small>7D Velocity</small><b>${fmt(d.velocity_7d)}/day</b></div><div class="detail"><small>DOS</small><b>${fmt(d.dos)}</b></div></div><div class="sectiontitle">Why this suggestion?</div><div class="reasonlist">${reasons.map(x=>`<div class="reason"><span class="rdot"></span><div><b>${esc(x.title)}</b><span>${esc(x.detail)}</span></div></div>`).join('')}</div><div class="calc">Coming delivery suggestion ≈ expected family usage through coverage window − usable family OH + promotion/safety adjustment. Incoming is not used as a displayed Ordering Review field.</div>${recArts.length?`<div class="sectiontitle">Receiving Articles on Last Receipt</div><div class="reasonlist">${recArts.map(x=>`<div class="reason"><span class="rdot"></span><div><b>${esc(x.article_number)}</b><span>${fmt(x.quantity)} ${esc(x.base_uom||'')} · Base UOM</span></div></div>`).join('')}</div>`:''}`,`<span class="pill blue">READ ONLY</span>`)}

async function loadPrices(){const err=$('#priceError');err.innerHTML='';$('#priceRows').innerHTML='<tr><td colspan="11" class="loading">Loading...</td></tr>';try{const d=await api(`/v1/backoffice/pricing-review?category=${encodeURIComponent(state.priceCat)}&limit=100`);state.prices=d.rows||[];renderPrices()}catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#priceRows').innerHTML=''}}
function filteredPrices(){
  let a=[...state.prices];
  const status=String(state.priceStatus||'ALL').toUpperCase();
  const text=String(state.priceText||'').trim().toLowerCase();
  if(status!=='ALL')a=a.filter(r=>String(r.review_status||'').toUpperCase()===status);
  if(text)a=a.filter(r=>[r.name,r.upc,r.family_name,r.family_article_number,r.review_status,r.review_blocker,...(r.reasons||[])].join(' ').toLowerCase().includes(text));
  const sort=state.priceSort||'opportunity';
  if(sort==='opportunity')a.sort((x,y)=>Number(y.gp_per_day_opportunity||0)-Number(x.gp_per_day_opportunity||0)||Number(y.urgency_score||0)-Number(x.urgency_score||0));
  if(sort==='urgency')a.sort((x,y)=>Number(y.urgency_score||0)-Number(x.urgency_score||0)||Number(y.gp_per_day_opportunity||0)-Number(x.gp_per_day_opportunity||0));
  if(sort==='gap')a.sort((x,y)=>Number(y.price_gap_pct||0)-Number(x.price_gap_pct||0));
  if(sort==='qty7')a.sort((x,y)=>Number(y.qty_7d||0)-Number(x.qty_7d||0));
  if(sort==='qty28')a.sort((x,y)=>Number(y.qty_28d||0)-Number(x.qty_28d||0));
  if(sort==='lowgp')a.sort((x,y)=>Number(x.current_gp_pct_reference??999)-Number(y.current_gp_pct_reference??999));
  if(sort==='currentprice')a.sort((x,y)=>Number(y.current_price||0)-Number(x.current_price||0));
  if(sort==='name')a.sort((x,y)=>String(x.name||'').localeCompare(String(y.name||'')));
  return a;
}
function renderPrices(){const rows=filteredPrices();$('#priceCount').textContent=`${rows.length} shown · ${state.prices.length} loaded`;$('#priceRows').innerHTML=rows.map(r=>`<tr><td><div class="name">${esc(r.name)}</div><div class="meta">${esc(r.family_name||'')}</div></td><td>${esc(r.upc)}</td><td>${money(r.current_price)}</td><td>${money(r.candidate_price)}</td><td>${esc(r.cost_basis||'—')}</td><td>${pct(r.current_gp_pct_reference)}</td><td>${fmt(r.qty_7d)}</td><td>${fmt(r.qty_28d)}</td><td>${pill(r.review_status)}</td><td><div class="meta" style="max-width:220px">${esc((r.reasons||[])[0]||r.review_blocker||r.suggestion_basis||'Review')}</div></td><td><button class="btn small pricedetail" data-upc="${esc(r.upc)}">Why?</button></td></tr>`).join('')||'<tr><td colspan="11" class="empty">No pricing review rows match the current filters.</td></tr>';$$('.pricedetail').forEach(b=>b.onclick=()=>openPriceDetail(b.dataset.upc))}
$$('.pricefilter').forEach(b=>b.onclick=()=>{state.priceCat=b.dataset.cat;$$('.pricefilter').forEach(x=>x.classList.toggle('on',x===b));loadPrices()});
$('#priceStatusFilter').onchange=e=>{state.priceStatus=e.target.value;renderPrices()};
$('#priceSort').onchange=e=>{state.priceSort=e.target.value;renderPrices()};
$('#priceTextFilter').oninput=e=>{state.priceText=e.target.value;renderPrices()};
function openPriceDetail(upc){const r=state.prices.find(x=>String(x.upc)===String(upc));if(!r)return;const rs=r.reasons||[];openDrawer('Price Suggestion Explanation',`${r.name} · UPC ${r.upc}`,`<div class="detailgrid"><div class="detail"><small>Current Price</small><b>${money(r.current_price)}</b></div><div class="detail"><small>Candidate Price</small><b>${money(r.candidate_price)}</b></div><div class="detail"><small>Current GP%</small><b>${pct(r.current_gp_pct_reference)}</b></div><div class="detail"><small>Candidate GP%</small><b>${pct(r.suggested_gp_pct_at_current_cost)}</b></div><div class="detail"><small>7D Qty</small><b>${fmt(r.qty_7d)}</b></div><div class="detail"><small>28D Qty</small><b>${fmt(r.qty_28d)}</b></div><div class="detail"><small>7D Velocity</small><b>${fmt(r.velocity_7d)}</b></div><div class="detail"><small>28D Velocity</small><b>${fmt(r.velocity_28d)}</b></div><div class="detail"><small>GP$/Day Current</small><b>${money(r.current_gp_per_day_7d)}</b></div><div class="detail"><small>GP$/Day Candidate</small><b>${money(r.candidate_expected_gp_per_day)}</b></div><div class="detail"><small>Company C Floor</small><b>${money(r.company_price_c_floor)}</b></div><div class="detail"><small>Cost Date</small><b>${esc(r.cost_date||'—')}</b></div></div><div class="sectiontitle">Reasons</div><div class="reasonlist">${rs.length?rs.map(x=>`<div class="reason"><span class="rdot"></span><div><b>${esc(x.replaceAll('_',' '))}</b><span>Observed evidence from the current pricing-analysis contract.</span></div></div>`).join(''):`<div class="reason"><span class="rdot"></span><div><b>${esc(r.review_blocker||'Review only')}</b><span>${esc(r.suggestion_basis||'')}</span></div></div>`}</div><div class="calc">Read-only: this screen never stages or changes system price.</div>`,`<span class="pill blue">READ ONLY</span>`)}

async function loadQA(){
 const err=$('#qaError');err.innerHTML='';$('#qaRows').innerHTML='<tr><td colspan="6" class="loading">Loading QA...</td></tr>';
 try{
   const d=await api('/v1/backoffice/qa-review?limit=300');
   state.qaIssues=d.issues||[];state.qaHistory=d.resolution_history||[];
   renderQA();
 }catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#qaRows').innerHTML=''}
}
function filteredQA(){
 let a=[...state.qaIssues];
 if(state.qaFilter==='FIXABLE')a=a.filter(x=>x.can_fix);
 if(state.qaFilter==='VIEW_ONLY')a=a.filter(x=>!x.can_fix);
 if(state.qaFilter==='HIGH')a=a.filter(x=>['HIGH','CRITICAL'].includes(String(x.severity||'').toUpperCase()));
 return a;
}
function renderQA(){
 const a=filteredQA();$('#qaCount').textContent=`${a.length} shown · ${state.qaIssues.length} open`;
 $('#qaRows').innerHTML=a.map(x=>{
   const cur=x.current||{};
   const stateText=[
     cur.article_number?('Article '+cur.article_number):'',
     cur.main_article_number?('Family '+cur.main_article_number):'',
     cur.selling_uom?('UOM '+cur.selling_uom):'UOM missing'
   ].filter(Boolean).join(' · ');
   return `<tr>
     <td>${pill(x.severity)}</td>
     <td><div class="name">${esc(x.issue_code)}</div><div class="meta" style="max-width:380px">${esc(x.issue_summary||'')}</div></td>
     <td><b>${esc(x.entity_key||'—')}</b><div class="meta">${esc(x.entity_type||'')}</div></td>
     <td>${esc(stateText||'No current serving row')}</td>
     <td>${x.can_fix?'<span class="pill amber">USER CONFIRM</span>':'<span class="pill blue">VIEW ONLY</span>'}</td>
     <td><button class="btn small qadetail" data-key="${esc(String(x.issue_id??('QC:'+x.entity_key)))}">${x.can_fix?'Fix':'Details'}</button></td>
   </tr>`;
 }).join('')||'<tr><td colspan="6" class="empty">No QA issues match this filter.</td></tr>';
 $$('.qadetail').forEach(b=>b.onclick=()=>openQAIssue(b.dataset.key));
 $('#qaHistoryRows').innerHTML=state.qaHistory.map(h=>`<tr><td>${esc(h.created_at||'—')}</td><td><b>${esc(h.entity_key||'')}</b><div class="meta">${esc(h.entity_type||'')}</div></td><td>${esc(h.issue_code||'')}</td><td>${esc(h.resolution_kind||'')}</td><td>${esc(h.actor||'')}</td><td>${esc(h.resolution_note||'—')}</td></tr>`).join('')||'<tr><td colspan="6" class="empty">No manual QA resolutions yet.</td></tr>';
}
function findQAIssue(key){
 if(String(key).startsWith('QC:'))return state.qaIssues.find(x=>x.issue_id===null&&('QC:'+x.entity_key)===key);
 return state.qaIssues.find(x=>String(x.issue_id)===String(key));
}
function openQAIssue(key){
 const x=findQAIssue(key);if(!x)return;
 const cur=x.current||{},detail=x.detail||{};
 const detailJson=esc(JSON.stringify(detail,null,2));
 if(!x.can_fix){
   openDrawer('QA Issue Details',`${x.issue_code} · ${x.entity_key}`,`<div class="detailgrid"><div class="detail"><small>Severity</small><b>${esc(x.severity)}</b></div><div class="detail"><small>Entity</small><b>${esc(x.entity_type)} · ${esc(x.entity_key)}</b></div><div class="detail"><small>Batch</small><b>#${esc(x.batch_id??'—')}</b></div><div class="detail"><small>Fix Scope</small><b>View only</b></div></div><div class="sectiontitle">Summary</div><div class="calc">${esc(x.issue_summary||'')}</div><div class="sectiontitle">Evidence / Detail</div><pre class="logconsole" style="white-space:pre-wrap">${detailJson}</pre>`,`<span class="pill blue">VIEW ONLY</span>`);
   return;
 }
 const article=cur.article_number||cur.main_article_number||'';
 const sell=cur.selling_uom||'';
 const base=cur.base_uom||'';
 const factor=cur.base_qty_per_selling_unit??'';
 openDrawer('Fix QA',`${x.issue_code} · UPC ${x.entity_key}`,`
   <div class="detailgrid">
     <div class="detail"><small>UPC</small><b>${esc(x.entity_key)}</b></div>
     <div class="detail"><small>Current Article</small><b>${esc(article||'—')}</b></div>
     <div class="detail"><small>Current Selling UOM</small><b>${esc(sell||'Missing')}</b></div>
     <div class="detail"><small>Fix Kind</small><b>${esc(x.fix_kind)}</b></div>
   </div>
   <div class="sectiontitle">Issue</div><div class="calc">${esc(x.issue_summary||'')}</div>
   <div class="sectiontitle">User-confirmed resolution</div>
   <div class="formfield"><label>Article Number</label><input id="qaArticle" value="${esc(article)}" placeholder="Required for unmapped UPC"></div>
   <div class="formfield"><label>Selling UOM</label><select id="qaSellingUom"><option value="">Select...</option>${['LB','EA','PACK','PAC','CASE','BAG','BX','TRAY'].map(u=>`<option value="${u}" ${String(sell).toUpperCase()===u?'selected':''}>${u}</option>`).join('')}</select></div>
   <div class="formfield"><label>Base UOM (optional; leave blank unless confirmed)</label><select id="qaBaseUom"><option value="">Not confirmed</option>${['LB','EA','PACK','PAC','CASE','BAG','BX','TRAY'].map(u=>`<option value="${u}" ${String(base).toUpperCase()===u?'selected':''}>${u}</option>`).join('')}</select></div>
   <div class="formfield"><label>Base Qty per Selling Unit (required only when Base UOM is confirmed)</label><input id="qaFactor" type="number" min="0" step="0.0001" value="${esc(factor)}"></div>
   <div class="formfield"><label>Resolution Note</label><textarea id="qaNote" placeholder="What you confirmed and why"></textarea></div>
   <label style="display:flex;gap:7px;align-items:flex-start;margin-top:10px;font-size:9px"><input id="qaConfirm" type="checkbox" style="margin-top:2px"><span>I confirm this correction. It will create/update a user-confirmed override, refresh the affected serving data, and preserve the original source rows.</span></label>
   <div class="calc">Allowed write scope: UPC identity / Selling UOM QA resolution only. Price, cost, sales, receipt quantities, and source files remain read-only.</div>
 `,`<button id="applyQAFix" class="btn primary">Apply QA Fix</button>`);
 $('#applyQAFix').onclick=async()=>{
   if(!$('#qaConfirm').checked){toast('Confirm the QA correction first');return}
   const body={
     issue_id:x.issue_id,
     ean_upc:x.entity_key,
     article_number:($('#qaArticle').value||'').trim()||null,
     selling_uom:$('#qaSellingUom').value,
     base_uom:$('#qaBaseUom').value||null,
     base_qty_per_selling_unit:($('#qaFactor').value||'').trim()===''?null:Number($('#qaFactor').value),
     note:($('#qaNote').value||'').trim()||null,
     confirm:'APPLY_QA_FIX'
   };
   const btn=$('#applyQAFix');btn.disabled=true;
   try{
     const r=await api('/v1/backoffice/qa-resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
     toast(`QA fix applied · resolution #${r.resolution_id}`);closeDrawer();await Promise.allSettled([loadQA(),loadInventory()]);
   }catch(e){toast(e.message)}finally{const z=$('#applyQAFix');if(z)z.disabled=false}
 };
}
$$('.qafilter').forEach(b=>b.onclick=()=>{state.qaFilter=b.dataset.qafilter;$$('.qafilter').forEach(x=>x.classList.toggle('on',x===b));renderQA()});
$('#qaRefresh').onclick=loadQA;

async function loadDatabaseOverview(){
  const err=$('#dbOverviewError');if(err)err.innerHTML='';
  try{
    const [h,a,r,q]=await Promise.all([api('/healthz'),api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=5'),api('/v1/backoffice/qa-review?limit=300')]);
    state.active=a.active_batch||null;state.recent=r.batches||[];state.qaIssues=q.issues||[];state.qaHistory=q.resolution_history||[];
    const latest=state.recent[0]||null;
    $('#dbOverviewActive').innerHTML=activeCard(state.active);
    $('#dbLatestBatch').innerHTML=latest?(activeCard({...latest,status:latest.processing_status||latest.phase3_status,batch_label:latest.batch_label||'Latest completed'})+rebuildActionHtml(latest,true)):'<div class="empty">No completed batch history.</div>';
    wireRebuildButtons($('#dbLatestBatch'));
    $('#dbProcessingSummary').textContent=state.active?`Batch #${state.active.batch_id||'—'} is processing`:(latest?`Latest #${latest.batch_id} · ${latest.phase3_status||latest.processing_status||'complete'}`:'No active batch');
    const fixable=state.qaIssues.filter(x=>x.can_fix).length;
    $('#dbQASummary').textContent=state.qaIssues.length?`${state.qaIssues.length} open · ${fixable} fixable`:'No open QA issues';
    $('#dbHealthSummary').textContent=h.ok?`Service healthy · ${h.version||''}`:'Service health needs attention';
    $('#dbUploadSummary').textContent=state.active?'Wait for current batch to finish':'Ready for a new source batch';
    const hasProblem=!h.ok||state.qaIssues.some(x=>['HIGH','CRITICAL'].includes(String(x.severity||'').toUpperCase()));
    const status=$('#dbOverallStatus');status.textContent=hasProblem?'ATTENTION':(state.active?'PROCESSING':'READY');status.className='pill '+(hasProblem?'amber':state.active?'sea':'green');
  }catch(e){if(err)err.innerHTML=`<div class="error">${esc(e.message)}</div>`;const st=$('#dbOverallStatus');if(st){st.textContent='CHECK FAILED';st.className='pill red'}}
}
function batchRebuildEligible(b){
  const p2=String(b?.phase2c_status||'').toUpperCase();
  const p3=String(b?.phase3_status||b?.processing_status||'').toUpperCase();
  return p2==='READY' && ['QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS','PHASE3_QA_HOLD'].includes(p3);
}
function rebuildActionHtml(b,compact=false){
  if(!b||!batchRebuildEligible(b))return '';
  return `<div style="${compact?'margin-top:8px':'margin-top:10px'};display:flex;justify-content:flex-end"><button class="btn primary batch-rebuild-btn" data-batch="${esc(b.batch_id)}">🔄 Rebuild Phase 3 / QA</button></div>`;
}
function wireRebuildButtons(root=document){
  root.querySelectorAll('.batch-rebuild-btn').forEach(btn=>{
    btn.onclick=e=>{e.stopPropagation();rebuildPhase3(btn.dataset.batch)}
  });
}
async function rebuildPhase3(id){
  const b=state.recent.find(x=>String(x.batch_id)===String(id));
  if(!b){toast('Batch detail is not loaded yet');return}
  if(!batchRebuildEligible(b)){toast('This batch is not currently eligible for Phase 3 rebuild');return}
  if(!window.confirm(`Rebuild Phase 3 / QA for Batch #${b.batch_id}?\n\nRAW files will not be re-uploaded. The current Quick Check snapshot remains active until the rebuild commits.`))return;
  const buttons=[...document.querySelectorAll(`.batch-rebuild-btn[data-batch="${CSS.escape(String(b.batch_id))}"]`)];
  buttons.forEach(x=>{x.disabled=true;x.textContent='Queuing Rebuild…'});
  try{
    const d=await api(`/v1/web-upload/batches/${encodeURIComponent(b.batch_id)}/rebuild-phase3`,{method:'POST'});
    toast(d.already_active?'Phase 3 rebuild is already active':'Phase 3 / QA rebuild queued');
    closeDrawer();
    showDbTab('dbbatches');
    await loadBatches();
  }catch(e){
    toast(e.message);
    buttons.forEach(x=>{x.disabled=false;x.textContent='🔄 Rebuild Phase 3 / QA'});
  }
}
function activeCard(a){if(!a)return '<div class="empty">No active batch.</div>';const id=a.batch_id||a.id||'—',status=a.processing_status||a.status||'PROCESSING';return `<div class="batch"><div class="batchtop"><div><div class="batchid">Batch #${esc(id)}</div><div class="meta">${esc(a.batch_label||'Active upload')}</div></div>${pill(status)}</div><div class="batchmeta"><div><small>Files</small><b>${fmt(a.file_count,0)}</b></div><div><small>Started</small><b>${esc(a.upload_started_at||'—')}</b></div><div><small>Status</small><b>${esc(status)}</b></div></div></div>`}
async function loadBatches(){try{const [a,r]=await Promise.all([api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=20')]);state.active=a.active_batch||null;state.recent=r.batches||[];const activeEl=$('#activeBatch');if(activeEl)activeEl.innerHTML=activeCard(state.active);const overviewActive=$('#dbOverviewActive');if(overviewActive)overviewActive.innerHTML=activeCard(state.active);const batchRows=$('#batchRows');if(batchRows){batchRows.innerHTML=state.recent.map(b=>`<tr class="batchrow" data-id="${esc(b.batch_id)}"><td><b>#${esc(b.batch_id)}</b><div class="meta">${esc(b.batch_label||'')}</div></td><td>${pill(b.processing_status)}</td><td>${fmt(b.file_count,0)}</td><td>${esc(b.upload_started_at||'—')}</td><td>${esc(b.completed_at||'—')}</td><td>${pill(b.phase3_status||'—')}</td><td>${fmt(b.quick_check_ready_rows,0)} / ${fmt(b.quick_check_hold_rows,0)}</td></tr>`).join('')||'<tr><td colspan="7" class="empty">No recent completed batches.</td></tr>';$$('.batchrow').forEach(x=>x.onclick=()=>openBatchDetail(x.dataset.id))}const latest=state.recent[0]||null;const latestEl=$('#dbLatestBatch');if(latestEl){latestEl.innerHTML=latest?(activeCard({...latest,status:latest.processing_status||latest.phase3_status,batch_label:latest.batch_label||'Latest completed'})+rebuildActionHtml(latest,true)):'<div class="empty">No completed batch history.</div>';wireRebuildButtons(latestEl)}const ps=$('#dbProcessingSummary');if(ps)ps.textContent=state.active?`Batch #${state.active.batch_id||'—'} is processing`:(latest?`Latest #${latest.batch_id} · ${latest.phase3_status||latest.processing_status||'complete'}`:'No active batch')}catch(e){const be=$('#batchError');if(be)be.innerHTML=`<div class="error">${esc(e.message)}</div>`;const oe=$('#dbOverviewError');if(oe)oe.innerHTML=`<div class="error">${esc(e.message)}</div>`}}
function openBatchDetail(id){
  const b=state.recent.find(x=>String(x.batch_id)===String(id));if(!b)return;
  const files=b.files||[],q=b.qa_summary||{},eligible=batchRebuildEligible(b);
  const foot=eligible
    ? `<span class="meta" style="margin-right:auto">Uses current OH / UOM / cost / identity / QA rules. RAW is not re-uploaded.</span><button id="rebuildPhase3Btn" class="btn primary">🔄 Rebuild Phase 3 / QA</button>`
    : `<span class="pill blue">READ ONLY</span>`;
  openDrawer(
    `Batch #${b.batch_id}`,
    `${b.processing_status||''} · ${b.phase3_status||''}`,
    `<div class="detailgrid"><div class="detail"><small>Files</small><b>${fmt(b.file_count,0)}</b></div><div class="detail"><small>Rows</small><b>${fmt(b.source_row_count,0)}</b></div><div class="detail"><small>Errors</small><b>${fmt(b.error_count,0)}</b></div><div class="detail"><small>Completed</small><b>${esc(b.completed_at||'—')}</b></div><div class="detail"><small>QC Ready</small><b>${fmt(b.quick_check_ready_rows,0)}</b></div><div class="detail"><small>QC Hold</small><b>${fmt(b.quick_check_hold_rows,0)}</b></div></div><div class="sectiontitle">Source Files</div><div class="reasonlist">${files.map(f=>`<div class="reason"><span class="rdot"></span><div><b>${esc(f.original_filename||'')}</b><span>${esc(f.source_type||'Unknown')} · ${esc(f.processing_status||'')}</span></div></div>`).join('')||'<span class="meta">No file detail.</span>'}</div>${q.phase3?`<div class="sectiontitle">QA</div><div class="calc">${esc(q.phase3.result_status||'')} · blockers ${fmt(q.phase3.blocking_issue_count,0)} · hold rows ${fmt(q.phase3.quick_check_hold_rows,0)}</div>`:''}${eligible?'<div class="calc" style="margin-top:10px"><b>Rebuild available.</b> Re-runs Phase 3 / QA only; the previous Quick Check snapshot stays live until commit.</div>':''}`,
    foot
  );
  const rb=$('#rebuildPhase3Btn');if(rb)rb.onclick=()=>rebuildPhase3(b.batch_id);
}
$('#refreshBatch').onclick=loadBatches;

$('#uploadBtn').onclick=async()=>{const files=[...$('#uploadFiles').files];if(!files.length){toast('Select files first');return}const btn=$('#uploadBtn');btn.disabled=true;$('#uploadResult').innerHTML='<span class="meta">Creating batch...</span>';try{const label=($('#uploadNote').value||'').trim()||`Web direct upload ${new Date().toLocaleString()}`;const created=await api('/v1/web-upload/batches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label})});if(created.created===false){$('#uploadResult').innerHTML='<b>Upload not started</b><div class="meta">A batch is already active. Wait for it to finish before uploading another batch.</div>';toast('Active batch already processing');showDbTab('dbbatches');await loadBatches();return}const session=created.session_id||created.batch_key||created.session?.session_id;if(!session)throw new Error('Upload batch session ID was not returned');const uploaded=[];for(let i=0;i<files.length;i++){const fd=new FormData();fd.append('file',files[i]);$('#uploadResult').innerHTML=`<span class="meta">Uploading ${i+1}/${files.length}: ${esc(files[i].name)}</span>`;const u=await api(`/v1/web-upload/batches/${encodeURIComponent(session)}/files`,{method:'POST',body:fd});uploaded.push(u)}$('#uploadResult').innerHTML='<span class="meta">Committing batch and starting processing...</span>';const commit=await api(`/v1/web-upload/batches/${encodeURIComponent(session)}/commit`,{method:'POST'});$('#uploadResult').innerHTML=`<b>Upload accepted</b><div class="meta">${files.length} file(s) · processing started</div><div class="filelist">${files.map(f=>`<div class="filerow"><span>${esc(f.name)}</span><span>${fmt(f.size/1024/1024,2)} MB</span></div>`).join('')}</div>`;$('#uploadFiles').value='';$('#uploadNote').value='';toast('Upload complete; batch processing started');showDbTab('dbbatches');await loadBatches()}catch(e){$('#uploadResult').innerHTML=`<div class="error" style="margin:-9px">${esc(e.message)}</div>`;toast(e.message)}finally{btn.disabled=false}};

async function loadData(){try{const [h,a,r]=await Promise.all([api('/healthz'),api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=5')]);const latest=(r.batches||[])[0]||a.latest_batch||{};$('#dataGrid').innerHTML=`<div class="kpi"><small>API Version</small><b>${esc(h.version||'—')}</b><span>${h.ok?'Healthy':'Issue'}</span></div><div class="kpi"><small>Worker</small><b>${esc(h.worker_state||'—')}</b><span>${h.worker_healthy?'Healthy':'Check worker'}</span></div><div class="kpi"><small>Serving / Latest Batch</small><b>#${esc(latest.batch_id||'—')}</b><span>${esc(latest.processing_status||latest.phase3_status||'')}</span></div><div class="kpi"><small>Active Batch</small><b>${a.active_batch?'Yes':'No'}</b><span>${a.active_batch?('#'+a.active_batch.batch_id):'Idle'}</span></div>`;$('#dataEvents').innerHTML=(r.batches||[]).map(b=>`<div class="batch"><div class="batchtop"><div><div class="batchid">Batch #${esc(b.batch_id)}</div><div class="meta">${esc(b.completed_at||b.upload_started_at||'')}</div></div>${pill(b.phase3_status||b.processing_status)}</div></div>`).join('')}catch(e){$('#dataEvents').innerHTML=`<div class="error">${esc(e.message)}</div>`}}
$('#refreshData').onclick=loadData;
$('#dbRefreshAll').onclick=()=>loadDatabaseOverview();

$('#searchForm').onsubmit=e=>{e.preventDefault();state.inventorySearch=$('#searchInput').value.trim();state.invCat='ALL';$$('.invfilter').forEach(x=>x.classList.toggle('on',x.dataset.cat==='ALL'));show('inventory')};
async function boot(){await Promise.allSettled([loadHealth(),loadInventory()]);setInterval(()=>{if(!document.hidden&&$('#database').classList.contains('on')){const current=$('#database .subview.on');if(current?.id==='dboverview')loadDatabaseOverview();if(current?.id==='dbbatches')loadBatches()}},15000)}boot();
})();
</script>
</body></html>'''
