from __future__ import annotations

DESKTOP_DATA_CENTER_V368_CSS = r"""
@media (min-width:760px){
  .v368-upload-dock{margin:0 0 10px;background:#fff;border:1px solid #dbe5ef;border-radius:12px;box-shadow:0 5px 20px rgba(31,61,91,.045);overflow:hidden}
  .v368-upload-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 12px;border-bottom:1px solid #e7edf4;background:linear-gradient(180deg,#fff,#fbfdff)}
  .v368-upload-head h3{margin:0;font-size:14px}.v368-upload-head p{margin:3px 0 0;font-size:9px;color:#6c7d91}
  .v368-upload-dock .uploadgrid{display:grid!important;grid-template-columns:minmax(440px,1.2fr) minmax(320px,.8fr)!important;gap:9px;padding:10px!important}
  .v368-upload-dock .drop{margin:0!important;min-height:140px!important;border:1.5px dashed #aebfd0!important;border-radius:10px!important;background:#f9fcff!important;padding:14px!important}
  .v368-upload-dock .drop .ico{font-size:24px!important}.v368-upload-dock .drop h3{font-size:13px!important;margin:4px 0!important}
  .v368-upload-dock .drop p{font-size:9px!important;margin:4px 0 8px!important;color:#6b7c8f!important}.v368-upload-dock input[type=file]{font-size:10px!important}
  .v368-health-guide{margin:0 10px 10px;border:1px solid #dce6ef;border-radius:11px;background:#fff;overflow:hidden}
  .v368-health-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;padding:9px}
  .v368-health-kpi{border:1px solid #e2e9f0;border-radius:9px;padding:8px;background:#fbfdff}
  .v368-health-kpi small{display:block;font-size:7px;text-transform:uppercase;letter-spacing:.04em;font-weight:900;color:#738397}
  .v368-health-kpi b{display:block;font-size:16px;margin-top:2px;color:#142b43}.v368-health-kpi span{font-size:8px;color:#76869a}
  .v368-health-explain{padding:9px 10px;border-top:1px solid #e9eef4;border-bottom:1px solid #e9eef4;background:#f8fbfe}
  .v368-health-explain strong{font-size:10px}.v368-health-explain p{margin:3px 0 0;font-size:9px;line-height:1.45;color:#5f7187}
  .v368-health-legend{display:flex;gap:12px;flex-wrap:wrap;padding:8px 10px;border-bottom:1px solid #edf2f6;font-size:9px;color:#52667e}
  .v368-legend-item{display:flex;align-items:center;gap:5px}.v368-swatch{width:11px;height:11px;border-radius:3px;border:1px solid transparent}
  .v368-swatch.complete{background:#dff5e8;border-color:#9ed7b5}.v368-swatch.missing{background:#ffe5e9;border-color:#f2a7b2}
  .v368-swatch.current{background:#e6f2ff;border-color:#9ac6fb}.v368-swatch.snapshot{background:#edf1f5;border-color:#cfd8e1}.v368-swatch.partial{background:#fff1cf;border-color:#e8c66d}
  .v368-complete-strip{display:grid;grid-template-columns:repeat(14,minmax(58px,1fr));gap:5px;padding:9px 10px;overflow:auto}
  .v368-dayhealth{border:1px solid #dfe7ef;border-radius:8px;padding:6px 5px;min-width:58px;cursor:pointer;background:#fff}.v368-dayhealth:hover{box-shadow:0 0 0 2px rgba(11,114,244,.12)}
  .v368-dayhealth.complete{background:#eef9f2;border-color:#b9dfc8}.v368-dayhealth.missing{background:#fff0f2;border-color:#efbdc5}.v368-dayhealth.current{background:#edf6ff;border-color:#b8d7fb}.v368-dayhealth.partial{background:#fff8e8;border-color:#edd39a}
  .v368-dayhealth .date{font-size:9px;font-weight:900}.v368-dayhealth .weekday{font-size:7px;color:#718197;text-transform:uppercase}
  .v368-source-dots{display:flex;gap:3px;margin-top:5px}.v368-dot{font-size:7px;border-radius:4px;padding:2px 3px;font-weight:900;background:#edf1f5;color:#68788b}
  .v368-dot.ok{background:#dff5e8;color:#17784a}.v368-dot.miss{background:#ffe3e8;color:#b42e44}.v368-dot.nd{background:#e6f2ff;color:#0b67d5}.v368-dayhealth .snap{font-size:7px;color:#6f8094;margin-top:4px}
  .v368-health-note{padding:0 10px 10px;font-size:8px;color:#748398;line-height:1.4}
  #dbdata .panelhead .title:after{content:" · 14-Day Completeness & Source Coverage"}

  /* V502 live batch operations monitor */
  .v502-live-monitor{margin:0 0 10px;border:1px solid #d7e1ee;border-radius:13px;background:#fff;box-shadow:0 7px 22px rgba(31,61,91,.06);overflow:hidden}
  .v502-live-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:12px 13px;border-bottom:1px solid #e7edf4;background:linear-gradient(180deg,#fff,#fafcff)}
  .v502-live-head small{display:block;font-size:7px;font-weight:950;letter-spacing:.08em;color:#74869c;text-transform:uppercase}.v502-live-head h3{margin:2px 0 0;font-size:15px;color:#132b47}.v502-live-head p{margin:3px 0 0;font-size:8.5px;color:#6f8094}
  .v502-state{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;padding:5px 8px;border-radius:999px;font-size:8px;font-weight:950;background:#e9f7ef;color:#15734e}.v502-state:before{content:"";width:7px;height:7px;border-radius:50%;background:#1aa56f;box-shadow:0 0 0 3px rgba(26,165,111,.10)}
  .v502-state.warn{background:#fff4df;color:#996111}.v502-state.warn:before{background:#e3a027}.v502-state.bad{background:#ffeded;color:#b23f43}.v502-state.bad:before{background:#d94f55}.v502-state.idle{background:#eef2f6;color:#667589}.v502-state.idle:before{background:#9aa7b5}
  .v502-progress-wrap{padding:11px 13px 9px}.v502-progress-top{display:flex;align-items:flex-end;justify-content:space-between;gap:10px}.v502-progress-top small{display:block;font-size:7.5px;font-weight:900;color:#748398;text-transform:uppercase}.v502-progress-top b{display:block;font-size:12px;margin-top:2px;color:#19304b}.v502-progress-top strong{font-size:21px;line-height:1;color:#1768d8}
  .v502-bar{height:10px;margin-top:8px;border-radius:999px;background:#e8eef5;overflow:hidden}.v502-bar>span{display:block;height:100%;min-width:0;border-radius:inherit;background:linear-gradient(90deg,#1768d8,#22a1b8);transition:width .35s ease}
  .v502-progress-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin-top:8px}.v502-progress-meta>div{padding:7px 8px;border:1px solid #e5eaf0;border-radius:8px;background:#fbfcfe}.v502-progress-meta small{display:block;font-size:7px;color:#7c8999;text-transform:uppercase}.v502-progress-meta b{display:block;font-size:10px;margin-top:2px;color:#20344d;overflow-wrap:anywhere}
  .v502-checkpoints{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px;padding:0 13px 10px}.v502-checkpoint{position:relative;padding:8px 7px 7px 27px;border:1px solid #e4e9ef;border-radius:8px;background:#f8fafc;min-height:45px}.v502-checkpoint:before{position:absolute;left:8px;top:9px;width:14px;height:14px;display:grid;place-items:center;border-radius:50%;content:"·";background:#dfe5eb;color:#718094;font-size:10px;font-weight:950}.v502-checkpoint b{display:block;font-size:8px;color:#42536a}.v502-checkpoint small{display:block;font-size:7px;color:#8a96a5;margin-top:2px}.v502-checkpoint.done{background:#f0f8f4;border-color:#d3e9dc}.v502-checkpoint.done:before{content:"✓";background:#18825e;color:#fff}.v502-checkpoint.live{background:#eef5ff;border-color:#c9dbfb}.v502-checkpoint.live:before{content:"";background:#2764e7;box-shadow:0 0 0 4px rgba(39,100,231,.10)}.v502-checkpoint.live b{color:#245ecb}
  .v502-rowgrid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;padding:0 13px 10px}.v502-rowmetric{padding:8px;border:1px solid #e3e9ef;border-radius:8px;background:#fff}.v502-rowmetric small{display:block;font-size:7px;text-transform:uppercase;color:#7e8c9e}.v502-rowmetric b{display:block;font-size:13px;margin-top:2px;color:#162c47}.v502-rowmetric span{display:block;font-size:7px;color:#8a96a6;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .v502-worker{display:grid;grid-template-columns:minmax(0,1.3fr) repeat(3,minmax(100px,.7fr));gap:6px;padding:9px 13px;border-top:1px solid #edf1f5;background:#fbfcfe}.v502-worker>div{min-width:0}.v502-worker small{display:block;font-size:7px;text-transform:uppercase;color:#8190a1}.v502-worker b{display:block;font-size:9px;margin-top:2px;color:#26394f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.v502-worker .good b{color:#14764f}.v502-worker .warn b{color:#a86a10}.v502-worker .bad b{color:#ba4045}
  .v502-fileline{padding:9px 13px;border-top:1px solid #edf1f5;font-size:8px;color:#6f8094}.v502-fileline b{color:#293d56}.v502-blocked{margin:0 13px 10px;padding:8px 9px;border:1px solid #f0cf9c;border-radius:8px;background:#fff7e9;color:#8d5d18;font-size:8.5px}.v502-blocked.bad{border-color:#efc2c5;background:#fff0f1;color:#a63d43}
  .v502-monitor-link{width:calc(100% - 26px);margin:0 13px 12px!important}
  .v502-live-empty{padding:16px;color:#75869a;font-size:9px;text-align:center}
  .v502-live-error{margin:9px 13px;padding:8px;border-radius:8px;background:#fff0f1;color:#ac4147;font-size:8px}
  .v502-live-mounted #dbOverviewActive{display:none!important}

  @media(max-width:1200px){.v368-upload-dock .uploadgrid{grid-template-columns:1fr!important}.v368-health-summary{grid-template-columns:repeat(2,1fr)}.v502-progress-meta{grid-template-columns:repeat(2,1fr)}.v502-rowgrid{grid-template-columns:repeat(3,1fr)}.v502-worker{grid-template-columns:repeat(2,1fr)}}
}
"""

DESKTOP_DATA_CENTER_V368_JS = r"""
(function(){
  if(window.matchMedia('(max-width:759px)').matches)return;
  function q(s,r){return (r||document).querySelector(s)}
  function qa(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  async function getJson(url){var r=await fetch(url,{cache:'no-store'}),raw=await r.text(),d={};if(raw){try{d=JSON.parse(raw)}catch(e){d={detail:raw}}}if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:'HTTP '+r.status);return d}
  function enhance(){
    var main=q('#database .v366-ws-main')||q('#database');if(!main)return false;
    if(!q('#v368UploadDock')){
      var grid=q('#dboverview .uploadgrid');
      if(grid){
        var title=grid.previousElementSibling&&grid.previousElementSibling.classList.contains('sectiontitle')?grid.previousElementSibling:null;
        var dock=document.createElement('section');dock.id='v368UploadDock';dock.className='v368-upload-dock';
        dock.innerHTML='<div class="v368-upload-head"><div><h3>Upload New Files</h3><p>Always visible in Data Center · XLSX / XLS / XLSM / CSV / TXT / TSV · files selected together create one immutable batch.</p></div><span class="pill blue">FILE UPLOADER</span></div>';
        if(title)title.remove();grid.parentNode.removeChild(grid);dock.appendChild(grid);
        var hero=q('.desktop-data-hero',main);if(hero&&hero.nextSibling)main.insertBefore(dock,hero.nextSibling);else main.insertBefore(dock,main.firstChild);
      }
    }
    var panel=q('#dbdata .panel');
    if(panel&&!q('#v368HealthGuide',panel)){
      var g=document.createElement('div');g.id='v368HealthGuide';g.className='v368-health-guide';
      g.innerHTML='<div id="v368HealthSummary" class="v368-health-summary"><div class="v368-health-kpi"><small>Required-day completeness</small><b>Loading…</b><span>POS + MVT</span></div></div>'+
      '<div class="v368-health-explain"><strong>How the colors work</strong><p>A completed business day is <b>Complete</b> only when both canonical POS and canonical MVT exist. Missing POS or MVT makes the day <b>Missing</b>. Price List, OH, Live/Fresh and Frozen are snapshot sources: they are not expected every day, and a gray / no-update cell does not by itself make the day incomplete.</p></div>'+
      '<div class="v368-health-legend"><span class="v368-legend-item"><i class="v368-swatch complete"></i><b>Green · Complete</b> — POS + MVT available</span><span class="v368-legend-item"><i class="v368-swatch missing"></i><b>Red · Missing</b> — required POS or MVT is absent after grace</span><span class="v368-legend-item"><i class="v368-swatch current"></i><b>Blue · Current Day</b> — store-local today only</span><span class="v368-legend-item"><i class="v368-swatch partial"></i><b>Amber · Pending / Not Due</b> — prior day still inside the daily grace window</span><span class="v368-legend-item"><i class="v368-swatch snapshot"></i><b>Gray / —</b> — no snapshot update that date; not a daily-file miss</span></div>'+
      '<div id="v368CompletenessStrip" class="v368-complete-strip"><div class="loading">Loading 14-day coverage…</div></div>'+
      '<div class="v368-health-note"><b>Inside each day:</b> POS and MVT show their own status. “Snapshots x/4” counts Price, OH, Live/Fresh and Frozen updates. Click a date to open full source evidence.</div>';
      var head=q('.panelhead',panel);if(head&&head.nextSibling)panel.insertBefore(g,head.nextSibling);else panel.appendChild(g);
    }
    return true;
  }
  function sc(x){var s=String((x&&x.status)||'NONE').toUpperCase();return s==='OK'?'ok':s==='MISSING'?'miss':s==='NOT_DUE'?'nd':''}
  function dc(s){s=String(s||'').toUpperCase();return s==='COMPLETE'?'complete':s==='MISSING'?'missing':(s.indexOf('CURRENT')>=0||s.indexOf('OPEN')>=0)?'current':'partial'}
  var boardSeq=0;
  function renderBoard(d){
    if(!enhance()||!d)return;
    var strip=q('#v368CompletenessStrip'),sum=q('#v368HealthSummary');if(!strip||!sum)return;
    var rows=d.rows||[],latest=d.latest||{};
    var complete=rows.filter(function(r){return String(r.overall_status||'').toUpperCase()==='COMPLETE'}).length;
    var missing=rows.filter(function(r){return String(r.overall_status||'').toUpperCase()==='MISSING'}).length;
    var judged=complete+missing,pc=judged?Math.round(complete/judged*100):100;
    sum.innerHTML='<div class="v368-health-kpi"><small>Required-day completeness</small><b>'+pc+'%</b><span>'+complete+' complete / '+judged+' judged</span></div>'+
      '<div class="v368-health-kpi"><small>Missing required days</small><b>'+missing+'</b><span>POS and/or MVT missing</span></div>'+
      '<div class="v368-health-kpi"><small>Latest POS</small><b>'+esc((latest.POS&&latest.POS.date)||'—')+'</b><span>'+esc((latest.POS&&latest.POS.file)||'No source')+'</span></div>'+
      '<div class="v368-health-kpi"><small>Latest MVT</small><b>'+esc((latest.MVT&&latest.MVT.date)||'—')+'</b><span>'+esc((latest.MVT&&latest.MVT.file)||'No source')+'</span></div>';
    strip.innerHTML=rows.slice(0,14).map(function(r){var s=r.sources||{},snap=['PRICE','OH','LIVE_FRESH','FROZEN'].filter(function(k){return String((s[k]&&s[k].status)||'').toUpperCase()==='OK'}).length;return '<div class="v368-dayhealth '+dc(r.overall_status)+'" data-date="'+esc(r.date||'')+'" title="'+esc((r.date||'')+' · '+(r.overall_status||''))+'"><div class="weekday">'+esc(r.weekday||'')+'</div><div class="date">'+esc(String(r.date||'').slice(5))+'</div><div class="v368-source-dots"><span class="v368-dot '+sc(s.POS)+'">POS</span><span class="v368-dot '+sc(s.MVT)+'">MVT</span></div><div class="snap">Snapshots '+snap+'/4</div></div>'}).join('');
    qa('.v368-dayhealth').forEach(function(x){x.onclick=function(){var day=x.dataset.date,b=q('.data-health-detail[data-date="'+CSS.escape(day)+'"]');if(b)b.click();else{var tr=q('.data-health-row[data-date="'+CSS.escape(day)+'"]');if(tr)tr.click()}}});
  }
  async function loadBoard(data){
    if(!enhance())return;
    var seq=++boardSeq,strip=q('#v368CompletenessStrip');
    try{
      var d=data||await getJson('/v1/backoffice/data-health?days=14');
      if(seq!==boardSeq)return;
      renderBoard(d);
    }catch(e){if(seq===boardSeq&&strip)strip.innerHTML='<div class="error">Unable to load 14-Day Completeness: '+esc(e.message||e)+'</div>'}
  }

  function num(v){var n=Number(v);return Number.isFinite(n)?n:null}
  function nfmt(v,d){var n=num(v);return n===null?'—':n.toLocaleString(undefined,{minimumFractionDigits:d||0,maximumFractionDigits:d||0})}
  function duration(sec){var n=num(sec);if(n===null||n<0)return '—';n=Math.round(n);var h=Math.floor(n/3600),m=Math.floor((n%3600)/60),s=n%60;if(h)return h+'h '+m+'m';if(m)return m+'m '+s+'s';return s+'s'}
  function sourceLabel(v){var s=String(v||'').toUpperCase().replace(/_/g,' ');return s||'Source'}
  function stageLabel(v){var s=String(v||'').toUpperCase();var map={STARTING:'Starting',PHASE3_CONNECT:'Connect DB',PHASE3_SCHEMA_READY:'Schema',PHASE3_MANUAL_AUTHORITY_READY:'Authority',PHASE3_HISTORY_INGESTED:'History',PHASE3_COVERAGE_BACKFILL_READY:'Coverage',PHASE3_IDENTITY_UOM_REPAIR_READY:'Identity / UOM',PHASE3_COST_REPAIR_READY:'Cost',PHASE3_QUICK_CHECK_REBUILD:'Quick Check',PHASE3_ANALYSIS_LAYER_REFRESH:'Analysis',PHASE3_IDENTITY_AUDIT:'Identity audit',PHASE3_FINALIZE:'Finalize',PHASE3_AUDIT:'Final audit'};return map[s]||String(v||'Waiting')}
  var stages=['PHASE3_CONNECT','PHASE3_SCHEMA_READY','PHASE3_MANUAL_AUTHORITY_READY','PHASE3_HISTORY_INGESTED','PHASE3_COVERAGE_BACKFILL_READY','PHASE3_IDENTITY_UOM_REPAIR_READY','PHASE3_COST_REPAIR_READY','PHASE3_QUICK_CHECK_REBUILD','PHASE3_ANALYSIS_LAYER_REFRESH','PHASE3_IDENTITY_AUDIT','PHASE3_FINALIZE','PHASE3_AUDIT'];
  function checkpointHtml(active){
    var current=String(active.active_phase3_stage||active.active_last_phase3_stage||'').toUpperCase(),idx=stages.indexOf(current);
    var groups=[['Ingest',true,'Source accepted'],['Phase 2C',String(active.processing_status||'').toUpperCase()!=='API_UPLOADING','Normalize / audit'],['Repair / rebuild',idx>=0,idx>=0?stageLabel(current):'Waiting'],['QA / audit',idx>=9,idx>=9?stageLabel(current):'Waiting'],['Finalize / publish',idx>=10,idx>=10?stageLabel(current):'Waiting']];
    return groups.map(function(x,i){var cls=x[1]?'done':'';if((i===2&&idx>=0&&idx<9)||(i===3&&idx>=9&&idx<10)||(i===4&&idx>=10))cls='live';return '<div class="v502-checkpoint '+cls+'"><b>'+esc(x[0])+'</b><small>'+esc(x[2])+'</small></div>'}).join('');
  }
  function monitorHost(){
    var active=q('#dbOverviewActive');if(!active)return null;
    var summary=active.closest('.dbsummary');if(!summary)return null;
    var box=q('#v502LiveMonitor',summary);if(!box){box=document.createElement('div');box.id='v502LiveMonitor';box.className='v502-live-monitor';summary.insertBefore(box,active)}
    return box;
  }
  function renderLiveMonitor(active){
    var box=monitorHost();if(!box)return;
    var summary=box.closest('.dbsummary');
    if(!active){if(summary)summary.classList.remove('v502-live-mounted');box.innerHTML='<div class="v502-live-empty"><b>No active processing batch.</b><br>New upload progress will appear here automatically.</div>';return}
    if(summary)summary.classList.add('v502-live-mounted');
    var run=String(active.active_run_status||active.processing_status||active.status||'PROCESSING').toUpperCase();
    var stale=active.active_run_stale===true;
    var hb=num(active.active_heartbeat_age_seconds);
    var stateClass=stale?'bad':(hb!==null&&hb>30?'warn':'');
    var stateText=stale?'POSSIBLY STALLED':(run==='QUEUED'?'QUEUED':'PROCESSING NORMALLY');
    var files=Array.isArray(active.active_files)?active.active_files:[],matched=files.find(function(x){return String(x.original_filename||'')===String(active.active_file_name||'')}),file=matched||files[files.length-1]||{};
    var fileName=active.active_file_name||file.original_filename||'—',src=sourceLabel(active.active_source_type||file.source_type||'');
    var sourceRows=num(active.active_file_rows);if(sourceRows===null)sourceRows=num(file.source_row_count);if(sourceRows===null)sourceRows=num(active.source_row_count);
    var current=num(active.active_progress_current),total=num(active.active_progress_total),pct=num(active.active_progress_pct),speed=num(active.active_progress_rows_per_second),eta=num(active.active_progress_eta_seconds),elapsed=num(active.active_progress_elapsed_seconds);
    if(total===null&&sourceRows!==null)total=sourceRows;
    if(pct===null&&current!==null&&total&&total>0)pct=Math.max(0,Math.min(100,current/total*100));
    if(pct===null){var si=stages.indexOf(String(active.active_phase3_stage||active.active_last_phase3_stage||'').toUpperCase());pct=si>=0?Math.min(96,25+(si+1)/stages.length*70):(run==='QUEUED'?3:12)}
    pct=Math.max(0,Math.min(100,pct));
    var ready=num(active.active_progress_ready),hold=num(active.active_progress_hold),hist=num(active.active_progress_historical),issues=0;
    if(active.active_progress_issue_counts&&typeof active.active_progress_issue_counts==='object')Object.keys(active.active_progress_issue_counts).forEach(function(k){issues+=Number(active.active_progress_issue_counts[k]||0)});else issues=num(active.active_issue_total)||0;
    var worker=active.active_worker||'—',stage=stageLabel(active.active_phase3_stage||active.active_last_phase3_stage||'');
    var currentItem=[active.active_progress_current_upc,active.active_progress_current_name].filter(Boolean).join(' · ')||'—';
    var heartbeatText=hb===null?'Pending':Math.round(hb)+'s ago',heartbeatClass=stale?'bad':(hb!==null&&hb>30?'warn':'good');
    var started=active.active_run_started_at||active.upload_started_at||'—';
    var coverage=file.coverage_start_date?(file.coverage_end_date&&file.coverage_end_date!==file.coverage_start_date?file.coverage_start_date+' → '+file.coverage_end_date:file.coverage_start_date):'date unresolved';
    var blocked='';
    if(stale)blocked='<div class="v502-blocked bad"><b>Worker heartbeat is stale.</b> The run may be stalled; recovery fencing should prevent a duplicate worker.</div>';
    else if(current!==null&&total!==null&&total>0&&current>=total&&hold!==null&&hold>0)blocked='<div class="v502-blocked"><b>Processing rows complete.</b> '+nfmt(hold)+' row(s) remain on HOLD. Processing completion and publish readiness are tracked separately.</div>';
    var progressLabel=current!==null&&total!==null?nfmt(current)+' / '+nfmt(total):stage;
    box.innerHTML='<div class="v502-live-head"><div><small>Live batch monitor</small><h3>Batch #'+esc(active.batch_id||active.id||'—')+' · Run #'+esc(active.active_pipeline_run_id||'—')+'</h3><p>'+esc(fileName)+' · '+esc(src)+'</p></div><span class="v502-state '+stateClass+'">'+esc(stateText)+'</span></div>'+
      '<div class="v502-progress-wrap"><div class="v502-progress-top"><div><small>Overall / current-stage progress</small><b>'+esc(progressLabel)+'</b></div><strong>'+nfmt(pct,1)+'%</strong></div><div class="v502-bar"><span style="width:'+pct.toFixed(1)+'%"></span></div><div class="v502-progress-meta">'+
        '<div><small>ETA</small><b>'+duration(eta)+'</b></div><div><small>Elapsed</small><b>'+duration(elapsed)+'</b></div><div><small>Throughput</small><b>'+(speed===null?'—':nfmt(speed,1)+' rows/s')+'</b></div><div><small>Current checkpoint</small><b>'+esc(stage)+'</b></div></div></div>'+
      '<div class="v502-checkpoints">'+checkpointHtml(active)+'</div>'+
      '<div class="v502-rowgrid"><div class="v502-rowmetric"><small>Source rows</small><b>'+nfmt(sourceRows)+'</b><span>discovered</span></div><div class="v502-rowmetric"><small>Processed</small><b>'+nfmt(current)+'</b><span>'+esc(currentItem)+'</span></div><div class="v502-rowmetric"><small>Ready</small><b>'+nfmt(ready)+'</b><span>live checkpoint</span></div><div class="v502-rowmetric"><small>Hold</small><b>'+nfmt(hold)+'</b><span>QA / lineage</span></div><div class="v502-rowmetric"><small>Open issues</small><b>'+nfmt(issues)+'</b><span>current batch</span></div></div>'+blocked+
      '<div class="v502-worker"><div><small>Worker</small><b title="'+esc(worker)+'">'+esc(worker)+'</b></div><div class="'+heartbeatClass+'"><small>Heartbeat</small><b>'+esc(heartbeatText)+'</b></div><div><small>Started</small><b>'+esc(started)+'</b></div><div><small>Code version</small><b>'+esc(active.active_code_version||'—')+'</b></div></div>'+
      '<div class="v502-fileline"><b>File:</b> '+esc(fileName)+' · '+esc(src)+' · '+esc(coverage)+(file.processing_status?' · '+esc(file.processing_status):'')+'</div>'+
      '<button type="button" class="btn soft v502-monitor-link">Open full live monitor / QA details</button>';
    var btn=q('.v502-monitor-link',box);if(btn)btn.onclick=function(){var original=q('.active-batch-monitor-btn');if(original)original.click()};
  }
  var monitorSeq=0,monitorTimer=null;
  async function loadLiveMonitor(){
    if(!enhance())return;
    var seq=++monitorSeq;
    try{var d=await getJson('/v1/web-upload/active');if(seq!==monitorSeq)return;renderLiveMonitor(d.active_batch||null)}catch(e){var box=monitorHost();if(box)box.innerHTML='<div class="v502-live-error">Live processing status unavailable · '+esc(e.message||e)+'</div>'}
  }
  function startMonitor(){if(monitorTimer)return;loadLiveMonitor();monitorTimer=setInterval(function(){if(!document.hidden&&q('#database')&&q('#database').classList.contains('on'))loadLiveMonitor()},2500)}

  function init(){
    var tries=0,t=setInterval(function(){tries++;if(enhance()||tries>20){clearInterval(t);loadBoard();startMonitor()}},60);
    document.addEventListener('fullmysql:data-health-updated',function(e){if(e&&e.detail)loadBoard(e.detail)});
    document.addEventListener('fullmysql:active-batch-finished',function(){setTimeout(loadLiveMonitor,250)});
    document.addEventListener('click',function(e){
      if(e.target.closest('.dbtab[data-dbtab="dbdata"]')||e.target.closest('#refreshData')||e.target.closest('#dbRefreshAll'))setTimeout(function(){loadBoard()},120);
      if(e.target.closest('[data-view="database"]')||e.target.closest('[data-go-view="database"]')||e.target.closest('.dbtab[data-dbtab="dboverview"]')||e.target.closest('#refreshData')||e.target.closest('#dbRefreshAll'))setTimeout(loadLiveMonitor,120);
    },true);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
"""