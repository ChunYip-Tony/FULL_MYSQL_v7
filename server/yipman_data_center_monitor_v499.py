from __future__ import annotations

"""Data Center v499 operational processing monitor.

The monitor uses server-reported telemetry when available. It never invents
row counts, throughput, worker state, checkpoints or ETA; missing telemetry is
shown as unavailable and progress falls back to clearly labelled pipeline
stage progress.
"""

_MARKER = "ydDataCenterMonitorV499"

_PATCH = r'''
<style id="ydDataCenterMonitorV499">
@media (min-width:760px){
  #ydesk #yd-data .dc499-monitor{margin:9px 0 0;padding:10px;border:1px solid #dbe5ef;border-radius:10px;background:#fbfdff}
  #ydesk #yd-data .dc499-statusline{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:7px}
  #ydesk #yd-data .dc499-statuscopy{min-width:0}
  #ydesk #yd-data .dc499-statuscopy b{display:block;font-size:13px;color:#183653;line-height:1.25}
  #ydesk #yd-data .dc499-statuscopy span{display:block;margin-top:2px;font-size:10px;color:#718197;line-height:1.3}
  #ydesk #yd-data .dc499-pct{font-size:18px;font-weight:950;color:#173653;white-space:nowrap;font-variant-numeric:tabular-nums}
  #ydesk #yd-data .dc499-track{height:9px;border-radius:999px;background:#e8eef4;overflow:hidden;box-shadow:inset 0 1px 2px rgba(20,44,70,.08)}
  #ydesk #yd-data .dc499-fill{height:100%;border-radius:999px;background:#0b72f4;transition:width .22s ease}
  #ydesk #yd-data .dc499-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:9px}
  #ydesk #yd-data .dc499-metric{min-width:0;padding:8px 9px;border:1px solid #e3eaf1;border-radius:8px;background:#fff}
  #ydesk #yd-data .dc499-metric label{display:block;font-size:8px;font-weight:900;letter-spacing:.28px;text-transform:uppercase;color:#74859a;line-height:1.25}
  #ydesk #yd-data .dc499-metric strong{display:block;margin-top:2px;font-size:13px;line-height:1.25;color:#193a58;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
  #ydesk #yd-data .dc499-metric small{display:block;margin-top:2px;font-size:9px;color:#7a8999;line-height:1.3;overflow-wrap:anywhere}
  #ydesk #yd-data .dc499-source{margin-top:7px;font-size:9px;color:#728399;line-height:1.35}
  #ydesk #yd-data .dc499-ready{background:#fff4d8!important;color:#956000!important}
  #ydesk #yd-data .dc499-running{background:#e8f3ff!important;color:#0868dc!important}
  #ydesk #yd-data .dc499-publishing{background:#f1edff!important;color:#6145cb!important}
  #ydesk #yd-data .dc499-done{background:#e9f8ef!important;color:#147b49!important}
  #ydesk #yd-data .dc499-failed{background:#ffe9ed!important;color:#b82f45!important}
  #ydesk #yd-data .dc499-idle{background:#edf2f6!important;color:#5d6d7d!important}
  #ydesk #yd-data .dc499-upload-note{margin-top:8px;padding:7px 9px;border-radius:8px;background:#eef6ff;border:1px solid #d7e8fb;color:#536f89;font-size:10px;line-height:1.35;text-align:left;width:100%;max-width:620px}
  #ydesk .live.dc499-gap{background:#fff4d8!important;color:#8b5a00!important}
  #ydesk .live.dc499-ok{background:#fff!important;color:#0868dc!important}
  @media(max-width:1180px){#ydesk #yd-data .dc499-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
  @media(max-width:900px){#ydesk #yd-data .dc499-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
}
</style>
<script id="ydDataCenterMonitorV499">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const x=Number(v);return Number.isFinite(x)?x:null};
  const first=(o,keys)=>{for(const k of keys){if(o&&o[k]!=null&&o[k]!=='')return o[k]}return null};
  const firstNum=(o,keys)=>num(first(o,keys));
  const fmt=v=>{const x=num(v);return x==null?'—':Math.round(x).toLocaleString()};
  const clock=v=>{if(!v)return '—';const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleTimeString([],{hour:'numeric',minute:'2-digit',second:'2-digit'})};
  let busy=false,healthBusy=false;

  function visible(){const x=$('#yd-data');return !!x&&x.classList.contains('active')}
  function processingCard(){return [...document.querySelectorAll('#yd-data .card')].find(x=>$('.cardhead h3',x)?.textContent.trim()==='2. Current Processing')||null}
  function state(raw){
    raw=String(raw||'NONE').toUpperCase();
    if(raw==='NONE')return {text:'IDLE',cls:'dc499-idle',stage:'No active processing',done:0};
    if(/ABORT|FAIL|ERROR/.test(raw))return {text:'FAILED',cls:'dc499-failed',stage:raw.replaceAll('_',' '),done:0};
    if(/QUICK_CHECK_READY|COMPLETE|PUBLISHED/.test(raw))return {text:'PUBLISHED',cls:'dc499-done',stage:'Published / ready',done:5};
    if(/PUBLISH/.test(raw))return {text:'PUBLISHING',cls:'dc499-publishing',stage:'Publishing',done:4};
    if(raw==='PHASE2C_READY')return {text:'READY · PHASE 3 QA',cls:'dc499-ready',stage:'Phase 2C complete · waiting for Phase 3 QA',done:3};
    if(/PHASE3.*HOLD/.test(raw))return {text:'QA HOLD',cls:'dc499-ready',stage:'Phase 3 QA hold',done:3};
    if(/PHASE3/.test(raw))return {text:'RUNNING · PHASE 3 QA',cls:'dc499-running',stage:'Phase 3 QA',done:3};
    if(/INGESTED_PENDING_QA|RAW_RELEASED|RELEASED/.test(raw))return {text:'READY · PHASE 2C',cls:'dc499-ready',stage:'Ingest complete · waiting for Phase 2C',done:2};
    if(/INGEST/.test(raw))return {text:'RUNNING · INGEST',cls:'dc499-running',stage:'Ingesting source file',done:1};
    if(/API_UPLOADING|UPLOAD/.test(raw))return {text:'UPLOADING',cls:'dc499-running',stage:'Receiving source file',done:1};
    if(/PHASE2/.test(raw))return {text:'RUNNING · PHASE 2C',cls:'dc499-running',stage:'Phase 2C normalization',done:2};
    return {text:raw.replaceAll('_',' '),cls:'dc499-running',stage:raw.replaceAll('_',' '),done:1};
  }
  function telemetry(b,s){
    const processed=firstNum(b,['active_processed_rows','processed_rows','rows_processed','active_rows_processed','progress_rows']);
    const total=firstNum(b,['active_total_rows','total_rows','rows_total','active_row_total','source_row_count']);
    const passed=firstNum(b,['active_passed_rows','passed_rows','rows_passed']);
    const rejected=firstNum(b,['active_rejected_rows','rejected_rows','rows_rejected','error_rows']);
    const speed=firstNum(b,['active_rows_per_second','rows_per_second','processing_rate','rate_rows_per_sec']);
    const eta=first(b,['active_eta_seconds','eta_seconds','processing_eta_seconds','eta']);
    const worker=first(b,['active_worker_name','worker_name','active_worker_id','worker_id']);
    const workerStatus=first(b,['active_worker_status','worker_status']);
    const heartbeat=first(b,['active_worker_heartbeat_at','worker_heartbeat_at','heartbeat_at']);
    const checkpoint=first(b,['active_checkpoint_name','checkpoint_name','active_checkpoint','checkpoint']);
    const checkpointAt=first(b,['active_checkpoint_at','checkpoint_at','updated_at','active_updated_at']);
    const rowBased=processed!=null&&total!=null&&total>0;
    const pct=rowBased?Math.max(0,Math.min(100,Math.round(processed/total*100))):Math.round((s.done/5)*100);
    let etaText='—';
    if(eta!=null&&eta!==''){const x=num(eta);etaText=x==null?String(eta):(x<60?Math.round(x)+' sec':Math.floor(x/60)+'m '+Math.round(x%60)+'s')}
    return {processed,total,passed,rejected,speed,etaText,worker,workerStatus,heartbeat,checkpoint,checkpointAt,rowBased,pct};
  }
  function metric(label,value,sub=''){return '<div class="dc499-metric"><label>'+esc(label)+'</label><strong>'+esc(value)+'</strong>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div>'}
  function render(b){
    const c=processingCard();if(!c)return;
    const raw=String(b?.processing_status||'NONE').toUpperCase(),s=state(raw),t=telemetry(b||{},s);
    const badge=$('.cardhead .badge',c);
    if(badge){badge.classList.remove('blue','green','amber','red','gray','dc496-waiting','dc496-ok','dc496-idle','dc496-danger','dc499-ready','dc499-running','dc499-publishing','dc499-done','dc499-failed','dc499-idle');badge.textContent=s.text;badge.classList.add(s.cls);badge.title=raw}
    const f=$('.dc496-file',c);
    if(f&&b){const name=first(b,['active_file_name','file_name'])||'Waiting for file identity',source=String(first(b,['active_source_type','source_type'])||'').toLowerCase();f.innerHTML='<b>Current file:</b> '+esc(name)+'<br><span>'+esc(s.stage)+(source?' · '+esc(source):'')+'</span>'}
    let m=$('.dc499-monitor',c);
    if(!m){m=document.createElement('div');m.className='dc499-monitor';(f||$('.pipeline',c))?.insertAdjacentElement('afterend',m)}
    if(!m)return;
    if(!b){m.innerHTML='<div class="dc499-statusline"><div class="dc499-statuscopy"><b>No active batch</b><span>Waiting for the next upload or pipeline run.</span></div><div class="dc499-pct">0/5</div></div><div class="dc499-track"><div class="dc499-fill" style="width:0%"></div></div>';return}
    const rowText=t.rowBased?(fmt(t.processed)+' / '+fmt(t.total)+' rows'):(s.done+' / 5 stages');
    const mode=t.rowBased?'Row progress reported by server':'Pipeline stage progress';
    const remaining=t.rowBased?Math.max(0,t.total-t.processed):null;
    const workerText=t.worker||t.workerStatus||'Not reported';
    const workerSub=[t.workerStatus,t.heartbeat?('heartbeat '+clock(t.heartbeat)):null].filter(Boolean).join(' · ');
    const checkpointText=t.checkpoint||'Not reported';
    const checkpointSub=t.checkpointAt?('updated '+clock(t.checkpointAt)):'';
    m.innerHTML='<div class="dc499-statusline"><div class="dc499-statuscopy"><b>'+esc(s.stage)+'</b><span>'+esc(mode)+' · '+esc(rowText)+'</span></div><div class="dc499-pct">'+esc(t.pct)+'%</div></div><div class="dc499-track"><div class="dc499-fill" style="width:'+esc(t.pct)+'%"></div></div><div class="dc499-grid">'+
      metric('Processed',t.processed==null?'—':fmt(t.processed),t.total!=null?'of '+fmt(t.total):'row telemetry not reported')+
      metric('Remaining',remaining==null?'—':fmt(remaining),t.passed!=null?'passed '+fmt(t.passed):'')+
      metric('Rejected',t.rejected==null?'—':fmt(t.rejected),t.rejected==null?'not reported by server':'')+
      metric('Speed / ETA',t.speed==null?'—':fmt(t.speed)+' rows/s','ETA '+t.etaText)+
      metric('Worker',workerText,workerSub)+
      metric('Checkpoint',checkpointText,checkpointSub)+
      '</div><div class="dc499-source">“—” means the server does not currently report that telemetry. No row count, worker state, speed or ETA is estimated.</div>';
  }
  function uploadNote(b){
    const up=$('#yd-data .upload');if(!up)return;
    let x=$('.dc499-upload-note',up);if(!x){x=document.createElement('div');x.className='dc499-upload-note';up.appendChild(x)}
    x.innerHTML=b?.batch_id?('<b>Batch #'+esc(b.batch_id)+' is active.</b> Files selected here create a separate immutable upload batch.'):('<b>No active processing.</b> The next upload creates a new immutable batch.');
  }
  async function refresh(){
    if(busy||!visible())return;busy=true;
    try{const r=await fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'});if(!r.ok)return;const a=await r.json(),b=a.active_batch||null;render(b);uploadNote(b)}catch(_e){}finally{busy=false}
  }
  function renderDataBadge(dh){
    const live=$('#ydesk .topbar .live');if(!live)return;
    const latest=dh?.latest||{},missing=[];
    [['POS','POS'],['MVT','MVT'],['PRICE','Price'],['OH','OH'],['LIVE_FRESH','Live/Fresh'],['FROZEN','Frozen']].forEach(([k,label])=>{if(!latest[k]?.date)missing.push(label)});
    live.classList.remove('dc499-gap','dc499-ok');
    if(missing.length){live.textContent='SOURCE GAP';live.classList.add('dc499-gap');live.title='Missing source date: '+missing.join(', ')}
    else{live.textContent='LIVE DATA';live.classList.add('dc499-ok');live.title='All Data Center source categories have a reported date'}
  }
  async function refreshHealth(){
    if(healthBusy)return;healthBusy=true;
    try{const r=await fetch('/v1/backoffice/data-health?days=14',{cache:'no-store',credentials:'same-origin'});if(r.ok)renderDataBadge(await r.json())}catch(_e){}finally{healthBusy=false}
  }
  const root=$('#yd-data');if(root)new MutationObserver(()=>{if(visible()){setTimeout(refresh,120);setTimeout(refreshHealth,160)}}).observe(root,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target?.id==='ydDataRefresh'||e.target?.id==='ydUpload'){setTimeout(refresh,500);setTimeout(refreshHealth,600)}},true);
  setInterval(refresh,3000);setInterval(refreshHealth,15000);setTimeout(refresh,800);setTimeout(refreshHealth,900);
})();
</script>
'''


def inject_data_center_monitor_v499(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)
