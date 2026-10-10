"""Standalone Data Center. Uses existing guarded upload and QA endpoints."""
DATA_CENTER_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Yipman · Data Center</title>
<style>
:root{--ink:#172c42;--muted:#64778b;--line:#dce5eb;--blue:#0969da;--teal:#087c72;--red:#b3263c}
*{box-sizing:border-box}
body{margin:0;background:#f3f6f8;color:var(--ink);font:14px/1.4 system-ui,sans-serif}
button,input{font:inherit}button,a{touch-action:manipulation}
button{cursor:pointer;border:1px solid var(--line);background:white;border-radius:7px;padding:7px 11px;color:var(--ink);font-weight:650}
button:disabled{opacity:.5;cursor:not-allowed}button.primary{background:var(--blue);border-color:var(--blue);color:white}a{color:var(--blue)}
header{background:#102b43;color:white;padding:10px max(18px,calc((100vw - 1544px)/2));display:flex;justify-content:space-between;align-items:center;gap:14px}
header strong{font-size:21px}header small{display:block;color:#b4c9d8;font-size:11px}
main{max-width:1580px;margin:auto;padding:14px 18px 28px}
h1{font-size:25px;margin:0}h2{font-size:17px;margin:0 0 9px}h3{font-size:15px;margin:0}
p{margin:4px 0 9px}.muted{color:var(--muted)}
.bar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}.bar h2{margin:0}
.pagebar p{margin:2px 0 4px;font-size:12px}.pagebar{margin-bottom:10px}
.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:12px;align-items:start}
.panel{background:white;border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:12px;min-width:0}
.fresh{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:0;margin:0 0 12px;background:white;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.tile{padding:9px 12px;min-width:0;border-right:1px solid var(--line)}.tile:last-child{border-right:0}
.tile span,.metric span{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
.tile b{display:block;font-size:15px;margin-top:2px;white-space:nowrap}.tile small{font-size:11px}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:10px 0}
.metric{background:#f5f8fa;border-radius:6px;padding:8px;overflow-wrap:anywhere;min-width:0}
.metric b{display:block;margin-top:3px;font-size:13px;font-weight:650;line-height:1.35;font-variant-numeric:tabular-nums}
#health .metrics{grid-template-columns:repeat(2,minmax(0,1fr))}#health p{font-size:12px;margin-bottom:0;overflow-wrap:anywhere}
.badge{display:inline-block;border-radius:20px;padding:4px 9px;font-size:12px;font-weight:750;background:#eaf0f5}
.bad{background:#fff0f2;color:var(--red)}.good{background:#e5f5ef;color:#116649}.warn{background:#fff5dc;color:#815800}
.notice{border:1px solid var(--line);background:#f6f9fc;padding:9px 10px;border-radius:7px;margin:9px 0;overflow-wrap:anywhere;font-size:12px}
.notice.bad{border-color:#f3bfc7;background:#fff3f4;color:var(--red)}
.drop{border:1px dashed #bccfdf;border-radius:8px;padding:12px;background:#fafcfe}
input[type=file]{width:100%;margin:8px 0;font-size:12px}input[type=file]::file-selector-button{padding:6px 8px;margin-right:8px;border:1px solid var(--line);border-radius:5px;background:white;color:var(--ink);cursor:pointer}
input[type=text]{padding:7px 9px;border:1px solid var(--line);border-radius:6px;width:100%;margin:5px 0 9px}
.drop label{font-size:12px}.upload-panel>p{font-size:12px}.upload-panel>p:last-child{margin-bottom:0}
table{width:100%;border-collapse:collapse;text-align:left}th{font-size:10px;color:var(--muted);text-transform:uppercase;background:#f8fafb;position:sticky;top:0;z-index:1}
td,th{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}td{font-size:12px;line-height:1.4}
details{margin-top:8px;border-top:1px solid var(--line);padding-top:8px}summary{cursor:pointer;font-weight:650;font-size:12px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f9;padding:10px;border-radius:7px;font-size:11px;max-height:320px;overflow:auto}
.scroll{overflow:auto;overscroll-behavior:contain}#recent{max-height:270px}#coverage{max-height:288px}#monitor details .scroll{max-height:300px}
.files{overflow-wrap:anywhere;font-size:12px}.steps{display:flex;gap:4px;flex-wrap:wrap;margin-top:10px}
.steps span{font-size:11px;border-radius:5px;padding:4px 7px;background:#eef2f5}.steps .done{background:#e5f5ef;color:#116649}.steps .hold{background:#fff5dc;color:#815800}
#sync{font-size:11px}footer{font-size:11px;color:var(--muted);margin-top:10px}
.linkbtn{border:0;background:none;padding:0;color:var(--blue);text-decoration:underline}.empty{padding:12px;color:var(--muted)}
:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
@media(max-width:1050px){.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:800px){.grid{grid-template-columns:1fr}.fresh{grid-template-columns:repeat(3,minmax(0,1fr))}.tile:nth-child(3n){border-right:0}.tile:nth-child(-n+3){border-bottom:1px solid var(--line)}.metrics{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:520px){main{padding:10px}.panel{padding:12px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.fresh{grid-template-columns:repeat(2,minmax(0,1fr))}.tile:nth-child(3n){border-right:1px solid var(--line)}.tile:nth-child(2n){border-right:0}.tile:nth-child(-n+4){border-bottom:1px solid var(--line)}header{padding:10px 12px;gap:10px}.bar{align-items:flex-start}h1{font-size:23px}.tile{padding:8px 10px}button{min-height:36px}.linkbtn{min-height:28px}#monitor>.bar{flex-wrap:wrap}td,th{padding:7px 6px}}

/* DC-3: compact operations view. */
header{padding-top:8px;padding-bottom:8px}header strong{font-size:19px}
main{padding-top:10px}.pagebar{align-items:center;margin-bottom:8px}.pagebar>div{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}.pagebar p{display:none}h1{font-size:21px}
.fresh{margin-bottom:10px}.tile{padding:7px 10px;display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}.tile b{font-size:13px;margin:0}.tile small{font-size:10px}
.panel{padding:12px;margin-bottom:10px}.grid{gap:10px}.bar{margin-bottom:7px}h2{font-size:16px;margin-bottom:7px}
.metrics{margin:8px 0;gap:5px;grid-template-columns:repeat(3,minmax(0,1fr))}.metric{padding:6px 8px}.metric b{font-size:12px;margin-top:2px}
.notice{padding:7px 9px;margin:7px 0}.steps{margin-top:8px}.files{margin-bottom:7px}
#recent{max-height:220px}#coverage{max-height:270px}#coverage th,#coverage td{padding:6px 5px;font-size:10px}
#health{font-size:12px;display:flex;gap:7px;align-items:center;flex-wrap:wrap}#health .muted{font-size:11px}
.drop{padding:10px}.drop details{border:0;margin:0 0 8px;padding:0}.drop input[type=text]{margin-bottom:0}.upload-panel>p{margin-bottom:6px}#uploadStatus:empty{display:none}
.activity{border:1px solid #c4e1d4;border-radius:8px;background:#f1faf5;padding:9px 10px;margin:8px 0}.activity.warn{border-color:#e8d19b;background:#fff9ec}.activity.bad{border-color:#ecc3c9;background:#fff3f4}
.activity-head{display:flex;align-items:center;gap:7px;font-size:13px}.activity-head strong{flex:1}.pulse{width:8px;height:8px;border-radius:50%;background:#168957;flex:none}.pulse.live{animation:heartbeat 1.8s ease-in-out infinite}.warn .pulse{background:#a67613;animation:none}.bad .pulse{background:#b3263c;animation:none}
.activity-lines{display:flex;gap:5px 15px;flex-wrap:wrap;margin-top:5px;font-size:11px}.activity-note{font-size:11px;margin-top:4px}.retry{font-size:11px;margin-top:6px;padding-top:6px;border-top:1px solid #dce5eb}.retry strong{font-weight:750}
@keyframes heartbeat{50%{box-shadow:0 0 0 4px #16895720;opacity:.65}}
@media(prefers-reduced-motion:reduce){.pulse.live{animation:none}}
@media(max-width:800px){.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.fresh{grid-template-columns:repeat(3,minmax(0,1fr))}.pagebar>div{gap:3px}.tile{display:block}.tile b{margin-top:2px}.tile small{margin-left:4px}}
@media(max-width:520px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.fresh{grid-template-columns:repeat(3,minmax(0,1fr))}.tile:nth-child(n){border-right:1px solid var(--line);border-bottom:0}.tile:nth-child(3n){border-right:0}.tile:nth-child(-n+3){border-bottom:1px solid var(--line)}.tile{padding:6px}.tile b{font-size:12px}.tile small{display:none}.pagebar>div{display:block}#sync{font-size:10px}.activity-head{flex-wrap:wrap}#coverage td,#coverage th{font-size:11px}.panel{padding:10px}}
</style></head><body>
<header><div><strong>Yipman</strong><small>DATA CENTER · Store #1032</small></div><div><b>FULL MYSQL</b><small id="version">Connecting…</small></div></header>
<main><div class="bar pagebar"><div><h1>Data Center</h1><p class="muted">Upload once. Track processing. Verify published data.</p><div id="sync" role="status">Loading live status…</div></div><button id="refresh">Refresh</button></div>
<div id="globalError" role="alert"></div><div id="freshness" class="fresh"></div>
<div class="grid"><div><section class="panel"><div class="bar"><h2>Batch monitor</h2><button id="follow" hidden>Follow current batch</button></div><div id="monitor" aria-live="polite">Loading current batch…</div></section>
<section class="panel"><h2>Recent batches</h2><p class="muted">Select a batch to inspect its complete run history.</p><div id="recent" class="scroll">Loading…</div></section></div>
<div><section class="panel upload-panel"><h2>Upload new files</h2><p class="muted">Upload new files together as one batch.</p><div class="drop"><label for="files"><b>Select source files</b></label><input id="files" type="file" multiple accept=".xlsx,.xls,.xlsm,.csv,.txt,.tsv"><details><summary>Batch note (optional)</summary><label for="note" hidden>Batch note</label><input id="note" type="text" placeholder="For example: October 9 movement"></details><button id="upload" class="primary">Upload &amp; start processing</button></div><div id="uploadStatus" role="status" class="notice"></div><p class="muted">Existing files are saved. No re-upload needed.</p></section>
<section class="panel"><div id="health">Loading service health…</div></section>
<section class="panel"><h2>14-day completeness</h2><p class="muted">Completed days · canonical POS and MVT.</p><div id="coverage" class="scroll">Loading…</div></section></div></div>
<footer>Data Center DC-3 · Live activity monitor · Live server evidence · Times shown in your browser’s local time. A healthy worker does not by itself confirm publication.</footer></main>
<script>
(()=>{'use strict';
const $=id=>document.getElementById(id), esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const metric=(k,v)=>'<div class="metric"><span>'+esc(k)+'</span><b>'+esc(v)+'</b></div>';
const parse=v=>{if(v&&typeof v==='object')return v;try{return JSON.parse(v||'{}')}catch{return {}}};
const time=v=>{if(!v)return 'Not reported';const s=String(v);const d=new Date(/Z$|[+-]\d\d:\d\d$/.test(s)?s:s+'Z');return isNaN(d)?s:d.toLocaleString()};
let selected=null,busy=false,uploading=false,resuming=false,lastSnapshot=null;
const observations=new Map();
let activityState=null;
async function api(path,options={}){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),options.method?120000:20000);try{const r=await fetch(path,{...options,credentials:'same-origin',cache:'no-store',signal:controller.signal});let d;try{d=await r.json()}catch{throw Error('Server returned a non-JSON response ('+r.status+')')}if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail||d));return d}finally{clearTimeout(timer)}}
function problem(id,e){$(id).innerHTML='<div class="notice bad">Unable to load: '+esc(e.message||e)+'. Use Refresh to retry.</div>'}
function classify(b,r,detail){if(r?.processing_status==='QUEUED')return ['Queued','warn'];if(['STARTED','PAUSE_REQUESTED'].includes(r?.processing_status)){const stamp=detail.heartbeat_at;const age=stamp?(Date.now()-new Date(/Z$/.test(stamp)?stamp:stamp+'Z').getTime())/1000:null;return age===null||!Number.isFinite(age)?['Running · heartbeat unreported','warn']:age>180?['Heartbeat stale · needs review','bad']:['Processing','good']}if(['FAILED','ABORTED','FAILED_QA'].includes(r?.processing_status))return ['Failed · recovery required','bad'];if(/HOLD/.test(r?.processing_status||'')||b.processing_status==='PHASE3_QA_HOLD')return ['QA hold','warn'];if(r?.processing_status==='PAUSED')return ['Paused','warn'];if(r?.processing_status==='COMPLETED')return [b.processing_status==='QUICK_CHECK_READY_WITH_HOLDS'?'Run completed · item holds remain':'Run completed · check publication','good'];if(b.processing_status==='PHASE2C_READY')return ['Phase 2C ready · waiting for Phase 3','warn'];return [b.processing_status||'No active batch',''];}
const epoch=v=>{if(!v)return null;const s=String(v),n=Date.parse(/Z$|[+-]\d\d:\d\d$/.test(s)?s:s+'Z');return Number.isFinite(n)?n:null};
const elapsed=n=>n===null||!Number.isFinite(n)?'Not reported':n<60?Math.floor(Math.max(0,n))+'s':Math.floor(n/60)+'m '+Math.floor(n%60)+'s';
function failureKey(run){const d=parse(run?.detail_json),e=String(d.error||d.recovery_reason||'');const code=e.match(/(?:DatabaseError|Error)\((\d+)/);return code?'Database error '+code[1]:e.includes('HEARTBEAT')?'Heartbeat expired':e.split('\n')[0].slice(0,120)}
function activityView(state,now=Date.now()){
 const {run:r,detail:d,health:h,receivedAt,observation:o,pipeline}=state;
 const active=['STARTED','PAUSE_REQUESTED'].includes(r?.processing_status),queued=r?.processing_status==='QUEUED';
 const age=epoch(d.heartbeat_at)===null?null:Math.max(0,(now-epoch(d.heartbeat_at))/1000),snapshotAge=Math.max(0,(now-receivedAt)/1000);
 const workerAge=h?.worker_heartbeat_age_seconds==null?null:Number(h.worker_heartbeat_age_seconds)+snapshotAge;
 const workerLive=!!h?.worker_healthy&&workerAge!==null&&workerAge<=30&&snapshotAge<=45;
 const sinceProgress=(now-o.changedAt)/1000,waiting=Array.isArray(d.db_lock_waits)&&d.db_lock_waits.length>0;
 let label='No active run',tone='warn',note='Worker availability does not confirm that this batch is processing.',live=false;
 if(snapshotAge>45){label='Status feed delayed';tone='warn';note='Last successful check '+elapsed(snapshotAge)+' ago. Refresh to verify current state.';}
 else if(active){
  if(h?.worker===d.worker&&h?.worker_instance&&d.worker_instance&&h.worker_instance!==d.worker_instance){label='Worker restarted · recovery pending';tone='bad';note='This run belongs to an earlier worker instance. Wait for recovery; do not upload again.';}
  else if(waiting){label='Database lock wait';tone='bad';note='Worker is alive, but the transaction is waiting for another database connection.';}
  else if(age===null){label='Run heartbeat not reported';tone='warn';note='The server has not supplied a run heartbeat. Progress is unconfirmed.';}
  else if(age>90){label='Run heartbeat delayed';tone=age>180?'bad':'warn';note=workerLive?'Worker is online; this run has not reported a fresh heartbeat.':'Run and worker heartbeats need attention.';}
  else if(sinceProgress>120){label='Alive · progress not advancing';tone='warn';note='No checkpoint, row counter or database activity change observed for '+elapsed(sinceProgress)+'. This does not prove a failure.';}
  else if(o.advanced){label='Processing · activity observed';tone='good';live=true;note='Checkpoint or database row counters changed '+elapsed(sinceProgress)+' ago.';}
  else{label='Worker alive · observing progress';tone='good';live=true;note='Waiting for the next checkpoint or row-counter change.';}
  if(r?.processing_status==='PAUSE_REQUESTED'){label='Pause requested';tone='warn';live=false;note='Waiting for the worker to reach a safe checkpoint.';}
 }
 else if(queued){label='Queued · waiting for worker';note='No running task has claimed this run yet.';}
 else if(r?.processing_status==='COMPLETED'){label='Run completed';tone='good';note='Check the QA and publish result below.';}
 else if(['FAILED','FAILED_QA','ABORTED'].includes(r?.processing_status)){label='Stopped · recovery required';tone='bad';note='This run is no longer processing, even when the worker is online.';}
 else if(['QA_HOLD','PAUSED'].includes(r?.processing_status)){label=r.processing_status==='PAUSED'?'Paused':'QA hold';note='This run is not actively processing.';}
 const previous=pipeline.filter(x=>x.pipeline_run_id<(r?.pipeline_run_id||0)&&['FAILED','FAILED_QA','ABORTED'].includes(x.processing_status));
 const recoveries=pipeline.filter(x=>x.stage_name==='PHASE3_RERUN'&&x.pipeline_run_id<=(r?.pipeline_run_id||0));
 const currentFailure=failureKey(r),sameFailures=currentFailure?pipeline.filter(x=>['FAILED','FAILED_QA','ABORTED'].includes(x.processing_status)&&failureKey(x)===currentFailure).length:0;
 let retry='';
 if(previous.length&&r?.processing_status==='COMPLETED')retry='Recovered after '+previous.length+' earlier failed runs.';
 else if(sameFailures>=2)retry='REPEATED ERROR · '+currentFailure+' appears in '+sameFailures+' failed runs.';
 else if(previous.length&&active)retry=(d.auto_recovery?'AUTOMATIC RECOVERY':'RECOVERY')+' · attempt '+(r.run_number||recoveries.length)+' · '+previous.length+' previous failed runs. Current Run #'+r.pipeline_run_id+'.';
 else if(previous.length)retry='REPEATED FAILURES · '+(previous.length+(['FAILED','FAILED_QA','ABORTED'].includes(r?.processing_status)?1:0))+' failed runs recorded. See run history.';
 return {label,tone,note,live,retry,runAge:active?elapsed(age):'Stopped',workerLabel:workerLive?'Online · '+elapsed(workerAge)+' ago':workerAge===null?'Not reported':'Delayed · '+elapsed(workerAge)+' ago',snapshotAge:elapsed(snapshotAge),progress:active?(d.progress_current!==undefined?d.progress_current+' '+(d.progress_unit||'rows'):d.db_rows_modified!==undefined?d.db_rows_modified+' DB row changes':'Waiting for counter'):'—'};
}
function setActivity(id,run,pipeline,detail,health){
 const now=Date.now(),fingerprint=JSON.stringify([detail.phase3_stage,detail.progress_current,detail.progress_total,detail.db_rows_modified,detail.db_rows_locked]);
 let observation=observations.get(id);
 if(!observation||observation.runId!==run?.pipeline_run_id)observation={runId:run?.pipeline_run_id,fingerprint,changedAt:now,advanced:false};
 else if(observation.fingerprint!==fingerprint)observation={...observation,fingerprint,changedAt:now,advanced:true};
 observations.set(id,observation);activityState={run,pipeline,detail,health,receivedAt:now,observation};renderActivity();
}
function renderActivity(){
 const box=$('liveness');if(!box||!activityState)return;const v=activityView(activityState);
 const html='<div class="activity '+v.tone+'"><div class="activity-head"><span class="pulse '+(v.live?'live':'')+'" aria-hidden="true"></span><strong>'+esc(v.label)+'</strong><small>Checked '+esc(v.snapshotAge)+' ago</small></div><div class="activity-lines"><span><b>Run heartbeat</b> '+esc(v.runAge)+(v.runAge==='Stopped'||v.runAge==='Not reported'?'':' ago')+'</span><span><b>Worker</b> '+esc(v.workerLabel)+'</span><span>'+esc(v.progress)+'</span></div><div class="activity-note">'+esc(v.note)+'</div>'+(v.retry?'<div class="retry"><strong>'+esc(v.retry)+'</strong></div>':'')+'</div>';
 if(box.innerHTML!==html)box.innerHTML=html;
}

async function inspect(id,health){const responses=await Promise.allSettled([api('/v1/web-upload/diagnostics/batch-id/'+id),api('/v1/web-upload/batches/'+id+'/qa-summary'),api('/v1/web-upload/batches/'+id+'/chatgpt-publish-status')]);if(responses[0].status!=='fulfilled'){problem('monitor',responses[0].reason);return}const d=responses[0].value,b=d.batch||{},runs=(d.runs||[]).slice().sort((a,b)=>b.pipeline_run_id-a.pipeline_run_id),pipeline=runs.filter(r=>['PHASE3_RERUN','POST_RAW_PIPELINE'].includes(r.stage_name));const r=pipeline.find(r=>['STARTED','QUEUED','PAUSE_REQUESTED'].includes(r.processing_status))||pipeline[0]||runs[0],detail=parse(r?.detail_json),qa=responses[1].status==='fulfilled'?responses[1].value:null,publish=responses[2].status==='fulfilled'?responses[2].value:null;const [label,tone]=classify(b,r,detail),active=pipeline.some(x=>['QUEUED','STARTED','PAUSE_REQUESTED'].includes(x.processing_status)),attempts=pipeline.filter(x=>x.stage_name==='PHASE3_RERUN'&&x.code_version===health?.version&&['FAILED','FAILED_QA','QA_HOLD','ABORTED','PAUSED','COMPLETED'].includes(x.processing_status)).length,canResume=!!health?.version&&b.processing_status==='PHASE2C_READY'&&!active&&attempts<3&&qa&&qa.phase3===null;const openDetails=[...($('monitor').querySelectorAll?.('details')||[])].map(x=>({open:x.open,scroll:x.querySelector('.scroll')?.scrollTop||0}));lastSnapshot={diagnostics:d,qa,publish};const error=detail.error||detail.recovery_reason;
$('monitor').innerHTML='<div class="bar"><h3>Batch #'+esc(id)+'</h3><span class="badge '+tone+'">'+esc(label)+'</span></div><div class="files">'+(d.files||[]).map(f=>esc(f.original_filename)).join('<br>')+'</div><div id="liveness"></div><div class="metrics">'+metric('Run',r?'#'+r.pipeline_run_id:'None')+metric('Checkpoint',detail.phase3_stage||detail.last_phase3_stage||'Not reported')+metric('Source rows',b.source_row_count)+metric('QA blockers',qa?.phase3?.blocking_issue_count??'Pending QA')+metric('Ready / held',qa?.phase3?(qa.phase3.quick_check_ready_rows??'—')+' / '+(qa.phase3.quick_check_hold_rows??'—'):'Pending QA')+metric('Publish',publish?.status||'Unknown')+'</div>'+(error?'<div class="notice bad"><b>Latest failure:</b> '+esc(error)+'</div>':'')+'<div class="steps"><span class="'+(d.files?.length?'done':'')+'">Source stored</span><span class="'+(['PASS','READY'].includes(d.phase2c?.result_status)?'done':'')+'">Phase 2C: '+esc(d.phase2c?.result_status||'Unknown')+'</span><span>Phase 3 QA: '+esc(qa?(qa.qa_available?'Available — see result':'Not available'):'Unavailable')+'</span><span>Publish: '+esc(publish?.status||'Unknown')+'</span></div><div class="notice">'+(active?'An existing run owns this batch. No additional run will be requested.':attempts>=3?'Recovery limit reached for this worker version. Resolve the failure before retrying.':canResume?'Resume Phase 3 uses the stored Phase 2C state. No source file upload is needed.':'Review the QA and publish results below. No recovery action is available for this state.')+'</div>'+(canResume?'<button id="resume" class="primary">Resume Phase 3</button>':'')+'<div id="actionStatus" role="status"></div><details><summary>Technical details</summary><div class="metrics">'+metric('Batch state',b.processing_status)+metric('Run status',r?.processing_status)+metric('Run worker',detail.worker||'Not reported')+metric('Last run heartbeat',time(detail.heartbeat_at))+metric('Phase 2C rows',d.phase2c?.normalized_row_count)+metric('Database changes',detail.db_rows_modified??'Not reported')+'</div></details><details><summary>Run history · '+runs.length+' recorded runs</summary><div class="scroll"><table><thead><tr><th>Run</th><th>Stage / status</th><th>Started</th><th>Ended</th></tr></thead><tbody>'+runs.map(x=>'<tr><td>#'+esc(x.pipeline_run_id)+'</td><td>'+esc(x.stage_name)+'<br>'+esc(x.processing_status)+'</td><td>'+esc(time(x.started_at))+'</td><td>'+esc(time(x.completed_at))+'</td></tr>').join('')+'</tbody></table></div></details><details><summary>QA and publish evidence</summary><pre>'+esc(JSON.stringify({qa:qa||{error:String(responses[1].reason)},publish:publish||{error:String(responses[2].reason)}},null,2))+'</pre></details><details><summary>Full batch diagnostics</summary><button id="download">Download diagnostics</button><pre>'+esc(JSON.stringify(d,null,2))+'</pre></details>';
[...($('monitor').querySelectorAll?.('details')||[])].forEach((x,i)=>{x.open=!!openDetails[i]?.open;const area=x.querySelector('.scroll');if(area)area.scrollTop=openDetails[i]?.scroll||0});
setActivity(id,r,pipeline,detail,health);
if($('resume'))$('resume').onclick=async()=>{if(resuming)return;resuming=true;$('resume').disabled=true;try{const result=await api('/v1/web-upload/batches/'+id+'/resume-phase3',{method:'POST',headers:{'Content-Type':'application/json'}});$('actionStatus').textContent='Server response: '+JSON.stringify(result)}catch(e){$('actionStatus').textContent=e.message}finally{resuming=false;refresh()}};
$('download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(lastSnapshot,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='yipman-batch-'+id+'-diagnostics.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
}
async function refresh(){if(busy||uploading||resuming)return;busy=true;$('refresh').disabled=true;try{const paths=['/healthz','/v1/web-upload/active','/v1/web-upload/recent?limit=12','/v1/yipman/header-freshness','/v1/backoffice/data-health?days=14'];const result=await Promise.allSettled(paths.map(p=>api(p)));const val=i=>result[i].status==='fulfilled'?result[i].value:null,h=val(0),a=val(1),recent=val(2),fresh=val(3),coverage=val(4);let failures=result.filter(x=>x.status==='rejected').length;
if(h){$('version').textContent='API '+h.version;$('health').innerHTML='<b>Worker</b><span class="badge '+(h.worker_healthy?'good':'bad')+'">'+esc(h.worker_state||'Unknown')+'</span><span class="muted">'+esc(h.worker_version)+'</span>'}else problem('health',result[0].reason);
if(fresh)$('freshness').innerHTML=['POS','MVT','PRICE','OH','FRESH','FRZ'].map(k=>{const s=fresh.sources?.[k]||(coverage?.latest?.[k]?{...coverage.latest[k],state:'Latest snapshot'}:{});return '<div class="tile"><span>'+esc(k==='FRZ'?'Frozen':k==='FRESH'?'Live / Fresh':k)+'</span><b>'+esc(s.date)+'</b><small class="muted">'+esc(s.state||'Unknown')+'</small></div>'}).join('');else problem('freshness',result[3].reason);
if(recent){const rows=(recent.batches||recent.rows||[]).slice();if(a?.active_batch&&!rows.some(x=>x.batch_id===a.active_batch.batch_id))rows.unshift(a.active_batch);$('recent').innerHTML='<table><thead><tr><th>Batch</th><th>Files</th><th>Status</th><th>Ready / held</th></tr></thead><tbody>'+rows.map(x=>'<tr><td><button class="linkbtn" data-batch="'+Number(x.batch_id)+'">#'+esc(x.batch_id)+'</button></td><td>'+esc((x.files||[]).map(f=>f.original_filename).join(', ')||x.batch_label||'—')+'</td><td>'+esc(x.processing_status)+'</td><td>'+esc(x.quick_check_ready_rows)+' / '+esc(x.quick_check_hold_rows)+'</td></tr>').join('')+'</tbody></table>';if(!rows.length)$('recent').innerHTML='<div class="empty">No batches returned.</div>';document.querySelectorAll('[data-batch]').forEach(btn=>btn.onclick=()=>{selected=Number(btn.dataset.batch);$('follow').hidden=false;refresh()})}else problem('recent',result[2].reason);
if(coverage){const rows=coverage.rows||[];const cell=(x,k)=>esc(x.sources?.[k]?.status||'—');$('coverage').innerHTML='<table><thead><tr><th>Date</th><th>Day status</th><th>POS</th><th>MVT</th><th>Price</th><th>OH</th></tr></thead><tbody>'+rows.map(x=>'<tr><td>'+esc(x.date)+'</td><td>'+esc(x.overall_status)+'</td><td>'+cell(x,'POS')+'</td><td>'+cell(x,'MVT')+'</td><td>'+cell(x,'PRICE')+'</td><td>'+cell(x,'OH')+'</td></tr>').join('')+'</tbody></table>';if(!rows.length)$('coverage').innerHTML='<div class="empty">No coverage rows returned.</div>'}else problem('coverage',result[4].reason);
const bid=selected||a?.active_batch?.batch_id||a?.latest_batch?.batch_id;if(bid)await inspect(bid,h);else if(!a)problem('monitor',result[1].reason);else $('monitor').innerHTML='<div class="empty">No active or latest batch returned.</div>';$('sync').textContent=(failures?'Some panels unavailable · ':'Updated · ')+new Date().toLocaleTimeString()+' · refreshes every 15 seconds while visible';
}catch(e){problem('globalError',e)}finally{busy=false;$('refresh').disabled=false}}
$('refresh').onclick=refresh;$('follow').onclick=()=>{selected=null;$('follow').hidden=true;refresh()};
$('upload').onclick=async()=>{if(uploading)return;const files=[...$('files').files];if(!files.length){$('uploadStatus').textContent='Select at least one source file.';return}uploading=true;$('upload').disabled=true;$('files').disabled=true;let created=null;try{created=await api('/v1/web-upload/batches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label:$('note').value.trim()||'Data Center '+new Date().toLocaleString()})});const session=created.session_id||created.batch_key||created.session?.session_id;if(!session)throw Error('No upload session returned. Inspect recent batches before trying again.');for(let i=0;i<files.length;i++){const fd=new FormData();fd.append('file',files[i]);$('uploadStatus').textContent='Uploading '+(i+1)+' / '+files.length+': '+files[i].name;await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/files',{method:'POST',body:fd})}$('uploadStatus').textContent='Committing batch…';const done=await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/commit',{method:'POST'});selected=done.batch_id||created.batch_id||null;$('follow').hidden=!selected;$('uploadStatus').textContent='Batch #'+(selected||'—')+' committed. Processing and QA are tracked in the monitor.';$('files').value=''}catch(e){$('uploadStatus').textContent='Upload stopped: '+e.message+(created?' Batch/session was created. Inspect recent batches before uploading again.':' No successful creation response received; check recent batches before retrying.')}finally{uploading=false;$('files').disabled=false;$('upload').disabled=!!created&&!!$('files').files.length;refresh()}};
refresh();setInterval(()=>{if(!document.hidden)refresh()},15000);
setInterval(()=>{if(!document.hidden)renderActivity()},1000);
})();
</script></body></html>'''
