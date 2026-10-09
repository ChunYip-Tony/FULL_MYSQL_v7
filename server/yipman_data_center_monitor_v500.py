from __future__ import annotations

"""Data Center v500 processing monitor.

Key correction: row counters are only allowed to drive the primary percentage
while the batch is actually in a row-processing stage. READY / QA / PUBLISH
states always use pipeline-stage progress so stale 0/N counters cannot turn a
completed Phase 2C state into a misleading 0% display.
"""

_MARKER = "ydDataCenterMonitorV500"

_PATCH = r'''
<style id="ydDataCenterMonitorV500">
@media (min-width:760px){
  #ydesk #yd-data .dc500-monitor{margin:9px 0 0;padding:10px;border:1px solid #dbe5ef;border-radius:10px;background:#fbfdff}
  #ydesk #yd-data .dc500-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:7px}
  #ydesk #yd-data .dc500-head b{display:block;font-size:13px;color:#183653;line-height:1.25}
  #ydesk #yd-data .dc500-head span{display:block;margin-top:2px;font-size:10px;color:#718197;line-height:1.3}
  #ydesk #yd-data .dc500-pct{font-size:18px;font-weight:950;color:#173653;white-space:nowrap;font-variant-numeric:tabular-nums}
  #ydesk #yd-data .dc500-track{height:9px;border-radius:999px;background:#e8eef4;overflow:hidden}
  #ydesk #yd-data .dc500-fill{height:100%;border-radius:999px;background:#0b72f4;transition:width .22s ease}
  #ydesk #yd-data .dc500-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:9px}
  #ydesk #yd-data .dc500-metric{padding:8px 9px;border:1px solid #e3eaf1;border-radius:8px;background:#fff;min-width:0}
  #ydesk #yd-data .dc500-metric label{display:block;font-size:8px;font-weight:900;letter-spacing:.28px;text-transform:uppercase;color:#74859a}
  #ydesk #yd-data .dc500-metric strong{display:block;margin-top:2px;font-size:13px;line-height:1.25;color:#193a58;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
  #ydesk #yd-data .dc500-metric small{display:block;margin-top:2px;font-size:9px;color:#7a8999;line-height:1.3;overflow-wrap:anywhere}
  #ydesk #yd-data .dc500-note{margin-top:7px;font-size:9px;color:#728399;line-height:1.35}
  #ydesk #yd-data .dc500-ready{background:#fff4d8!important;color:#956000!important}
  #ydesk #yd-data .dc500-running{background:#e8f3ff!important;color:#0868dc!important}
  #ydesk #yd-data .dc500-publish{background:#f1edff!important;color:#6145cb!important}
  #ydesk #yd-data .dc500-done{background:#e9f8ef!important;color:#147b49!important}
  #ydesk #yd-data .dc500-fail{background:#ffe9ed!important;color:#b82f45!important}
  #ydesk #yd-data .dc500-idle{background:#edf2f6!important;color:#5d6d7d!important}
  #ydesk #yd-data .dc500-upload-note{margin-top:8px;padding:7px 9px;border-radius:8px;background:#eef6ff;border:1px solid #d7e8fb;color:#536f89;font-size:10px;line-height:1.35;text-align:left;width:100%;max-width:620px}
  #ydesk .live.dc500-gap{background:#fff4d8!important;color:#8b5a00!important}
  #ydesk .live.dc500-ok{background:#fff!important;color:#0868dc!important}
  @media(max-width:1180px){#ydesk #yd-data .dc500-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
  @media(max-width:900px){#ydesk #yd-data .dc500-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
}
</style>
<script id="ydDataCenterMonitorV500">
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
  function card(){return [...document.querySelectorAll('#yd-data .card')].find(x=>$('.cardhead h3',x)?.textContent.trim()==='2. Current Processing')||null}
  function st(raw){
    raw=String(raw||'NONE').toUpperCase();
    if(raw==='NONE')return {text:'IDLE',cls:'dc500-idle',stage:'No active processing',done:0,rowStage:false};
    if(/ABORT|FAIL|ERROR/.test(raw))return {text:'FAILED',cls:'dc500-fail',stage:raw.replaceAll('_',' '),done:0,rowStage:false};
    if(/QUICK_CHECK_READY|COMPLETE|PUBLISHED/.test(raw))return {text:'PUBLISHED',cls:'dc500-done',stage:'Published / ready',done:5,rowStage:false};
    if(/PUBLISH/.test(raw))return {text:'PUBLISHING',cls:'dc500-publish',stage:'Publishing',done:4,rowStage:false};
    if(raw==='PHASE2C_READY')return {text:'READY · PHASE 3 QA',cls:'dc500-ready',stage:'Phase 2C complete · waiting for Phase 3 QA',done:3,rowStage:false};
    if(/PHASE3.*HOLD/.test(raw))return {text:'QA HOLD',cls:'dc500-ready',stage:'Phase 3 QA hold',done:3,rowStage:false};
    if(/PHASE3/.test(raw))return {text:'RUNNING · PHASE 3 QA',cls:'dc500-running',stage:'Phase 3 QA',done:3,rowStage:false};
    if(/INGESTED_PENDING_QA|RAW_RELEASED|RELEASED/.test(raw))return {text:'READY · PHASE 2C',cls:'dc500-ready',stage:'Ingest complete · waiting for Phase 2C',done:2,rowStage:false};
    if(/API_UPLOADING|UPLOAD/.test(raw))return {text:'UPLOADING',cls:'dc500-running',stage:'Receiving source file',done:1,rowStage:true};
    if(/INGEST/.test(raw))return {text:'RUNNING · INGEST',cls:'dc500-running',stage:'Ingesting source file',done:1,rowStage:true};
    if(/PHASE2/.test(raw))return {text:'RUNNING · PHASE 2C',cls:'dc500-running',stage:'Phase 2C normalization',done:2,rowStage:true};
    return {text:raw.replaceAll('_',' '),cls:'dc500-running',stage:raw.replaceAll('_',' '),done:1,rowStage:false};
  }
  function metric(label,value,sub=''){return '<div class="dc500-metric"><label>'+esc(label)+'</label><strong>'+esc(value)+'</strong>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div>'}
  function render(b){
    const c=card();if(!c)return;
    const raw=String(b?.processing_status||'NONE').toUpperCase(),s=st(raw);
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
    const validRows=s.rowStage&&processed!=null&&total!=null&&total>0;
    const pct=validRows?Math.max(0,Math.min(100,Math.round(processed/total*100))):Math.round((s.done/5)*100);
    const remaining=validRows?Math.max(0,total-processed):null;
    let etaText='—';if(s.rowStage&&eta!=null&&eta!==''){const x=num(eta);etaText=x==null?String(eta):(x<60?Math.round(x)+' sec':Math.floor(x/60)+'m '+Math.round(x%60)+'s')}
    const speedText=s.rowStage&&speed!=null&&speed>0?fmt(speed)+' rows/s':'—';
    const mode=validRows?'Row progress reported by server':'Pipeline stage progress';
    const progressText=validRows?(fmt(processed)+' / '+fmt(total)+' rows'):(s.done+' / 5 stages');
    const badge=$('.cardhead .badge',c);
    if(badge){badge.classList.remove('blue','green','amber','red','gray','dc496-waiting','dc496-ok','dc496-idle','dc496-danger','dc499-ready','dc499-running','dc499-publishing','dc499-done','dc499-failed','dc499-idle','dc500-ready','dc500-running','dc500-publish','dc500-done','dc500-fail','dc500-idle');badge.textContent=s.text;badge.classList.add(s.cls);badge.title=raw}
    const f=$('.dc496-file',c);if(f&&b){const name=first(b,['active_file_name','file_name'])||'Waiting for file identity',source=String(first(b,['active_source_type','source_type'])||'').toLowerCase();f.innerHTML='<b>Current file:</b> '+esc(name)+'<br><span>'+esc(s.stage)+(source?' · '+esc(source):'')+'</span>'}
    $('.dc499-monitor',c)?.remove();
    let m=$('.dc500-monitor',c);if(!m){m=document.createElement('div');m.className='dc500-monitor';(f||$('.pipeline',c))?.insertAdjacentElement('afterend',m)}
    if(!m)return;
    if(!b){m.innerHTML='<div class="dc500-head"><div><b>No active batch</b><span>Waiting for the next upload or pipeline run.</span></div><div class="dc500-pct">0/5</div></div><div class="dc500-track"><div class="dc500-fill" style="width:0%"></div></div>';return}
    const staleRowNote=!s.rowStage&&processed!=null&&total!=null?' · row counter '+fmt(processed)+' / '+fmt(total)+' is not used in this waiting stage':'';
    m.innerHTML='<div class="dc500-head"><div><b>'+esc(s.stage)+'</b><span>'+esc(mode)+' · '+esc(progressText)+esc(staleRowNote)+'</span></div><div class="dc500-pct">'+esc(pct)+'%</div></div><div class="dc500-track"><div class="dc500-fill" style="width:'+esc(pct)+'%"></div></div><div class="dc500-grid">'+
      metric('Processed',validRows?fmt(processed):'—',validRows?'of '+fmt(total):(processed!=null&&total!=null?'row counter not applicable in current stage':'not reported'))+
      metric('Remaining',remaining==null?'—':fmt(remaining),validRows&&passed!=null?'passed '+fmt(passed):'')+
      metric('Rejected',rejected==null?'—':fmt(rejected),rejected==null?'not reported by server':'')+
      metric('Speed / ETA',speedText,'ETA '+etaText)+
      metric('Worker',worker||workerStatus||'Not reported',[workerStatus,heartbeat?('heartbeat '+clock(heartbeat)):null].filter(Boolean).join(' · '))+
      metric('Checkpoint',checkpoint||'Not reported',checkpointAt?('updated '+clock(checkpointAt)):'')+
      '</div><div class="dc500-note">Primary percentage follows the active pipeline stage. Row telemetry drives percentage only while rows are actually being processed.</div>';
  }
  function uploadNote(b){const up=$('#yd-data .upload');if(!up)return;$('.dc499-upload-note',up)?.remove();let x=$('.dc500-upload-note',up);if(!x){x=document.createElement('div');x.className='dc500-upload-note';up.appendChild(x)}x.innerHTML=b?.batch_id?('<b>Batch #'+esc(b.batch_id)+' is active.</b> Files selected here create a separate immutable upload batch.'):('<b>No active processing.</b> The next upload creates a new immutable batch.')}
  async function refresh(){if(busy||!visible())return;busy=true;try{const r=await fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'});if(!r.ok)return;const a=await r.json(),b=a.active_batch||null;render(b);uploadNote(b)}catch(_e){}finally{busy=false}}
  function dataBadge(dh){const live=$('#ydesk .topbar .live');if(!live)return;const latest=dh?.latest||{},missing=[];[['POS','POS'],['MVT','MVT'],['PRICE','Price'],['OH','OH'],['LIVE_FRESH','Live/Fresh'],['FROZEN','Frozen']].forEach(([k,label])=>{if(!latest[k]?.date)missing.push(label)});live.classList.remove('dc499-gap','dc499-ok','dc500-gap','dc500-ok');if(missing.length){live.textContent='SOURCE GAP';live.classList.add('dc500-gap');live.title='Missing source date: '+missing.join(', ')}else{live.textContent='LIVE DATA';live.classList.add('dc500-ok');live.title='All Data Center source categories have a reported date'}}
  async function health(){if(healthBusy)return;healthBusy=true;try{const r=await fetch('/v1/backoffice/data-health?days=14',{cache:'no-store',credentials:'same-origin'});if(r.ok)dataBadge(await r.json())}catch(_e){}finally{healthBusy=false}}
  const root=$('#yd-data');if(root)new MutationObserver(()=>{if(visible()){setTimeout(refresh,120);setTimeout(health,160)}}).observe(root,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target?.id==='ydDataRefresh'||e.target?.id==='ydUpload'){setTimeout(refresh,500);setTimeout(health,600)}},true);
  setInterval(refresh,3000);setInterval(health,15000);setTimeout(refresh,800);setTimeout(health,900);
})();
</script>
'''


def inject_data_center_monitor_v500(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)
