from __future__ import annotations

"""Data Center v501: upload-first control panel with live batch health.

Focuses the page on two primary jobs: upload new files and determine whether
an active batch is working, waiting, stuck, or repeatedly restarting. Health
classification is evidence-based: server timestamps/telemetry are preferred;
client-observed history is persisted in localStorage as supplemental evidence.
"""

_MARKER='ydDataCenterFocusV501'

_PATCH=r'''
<style id="ydDataCenterFocusV501">
@media (min-width:760px){
  #ydesk #yd-data .pagehead{margin-bottom:12px!important}
  #ydesk #yd-data .pagehead p{max-width:900px!important}
  #ydesk #yd-data .datagrid{grid-template-columns:minmax(0,1.55fr) minmax(390px,.72fr)!important;gap:14px!important}
  #ydesk #yd-data .analysis{position:sticky!important;top:88px!important}
  #ydesk #yd-data .card{border-radius:16px!important}
  #ydesk #yd-data .upload{min-height:300px!important;padding:22px!important}
  #ydesk #yd-data .upload h3{font-size:20px!important}
  #ydesk #yd-data #ydUpload{font-size:15px!important;min-height:48px!important;padding:0 22px!important}
  #ydesk #yd-data .dc501-hero{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;margin:10px 0;padding:12px;border:1px solid #dbe7f2;border-radius:12px;background:#f8fbff}
  #ydesk #yd-data .dc501-hero h4{margin:0;font-size:16px;color:#173653;line-height:1.25}
  #ydesk #yd-data .dc501-hero p{margin:4px 0 0;font-size:11px;color:#6a7d91;line-height:1.4}
  #ydesk #yd-data .dc501-health{display:inline-flex;align-items:center;justify-content:center;min-width:105px;padding:9px 11px;border-radius:999px;font-size:11px;font-weight:950;letter-spacing:.2px;white-space:nowrap}
  #ydesk #yd-data .dc501-health.working{background:#e9f8ef;color:#147b49}
  #ydesk #yd-data .dc501-health.waiting{background:#fff4d8;color:#956000}
  #ydesk #yd-data .dc501-health.stuck{background:#ffe9ed;color:#b82f45}
  #ydesk #yd-data .dc501-health.repeating{background:#fff0df;color:#a55700}
  #ydesk #yd-data .dc501-health.failed{background:#ffe9ed;color:#b82f45}
  #ydesk #yd-data .dc501-health.done{background:#e9f8ef;color:#147b49}
  #ydesk #yd-data .dc501-health.idle{background:#edf2f6;color:#5d6d7d}
  #ydesk #yd-data .dc501-kv{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:9px}
  #ydesk #yd-data .dc501-box{padding:9px 10px;border:1px solid #e1e9f1;border-radius:9px;background:#fff;min-width:0}
  #ydesk #yd-data .dc501-box label{display:block;font-size:8px;font-weight:900;text-transform:uppercase;letter-spacing:.28px;color:#718197}
  #ydesk #yd-data .dc501-box strong{display:block;margin-top:3px;font-size:13px;line-height:1.25;color:#193a58;overflow-wrap:anywhere}
  #ydesk #yd-data .dc501-box small{display:block;margin-top:3px;font-size:9px;line-height:1.3;color:#7c8a99;overflow-wrap:anywhere}
  #ydesk #yd-data .dc501-alert{margin-top:9px;padding:9px 10px;border-radius:9px;border:1px solid #e1e8ef;background:#fbfdff;font-size:10px;line-height:1.45;color:#536981}
  #ydesk #yd-data .dc501-alert.stuck{background:#fff4f5;border-color:#f1c7ce;color:#9e2f40}
  #ydesk #yd-data .dc501-alert.repeating{background:#fff8ed;border-color:#f0d6ae;color:#8c5600}
  #ydesk #yd-data .dc501-activity{margin-top:10px}
  #ydesk #yd-data .dc501-activity h4{margin:0 0 6px;font-size:12px;color:#24435f}
  #ydesk #yd-data .dc501-event{display:grid;grid-template-columns:62px 1fr;gap:8px;padding:6px 0;border-bottom:1px solid #edf2f6;font-size:9px;color:#65788b}
  #ydesk #yd-data .dc501-event:last-child{border-bottom:0}
  #ydesk #yd-data .dc501-event b{font-size:10px;color:#294761}
  #ydesk #yd-data .dc501-secondary{margin-top:10px}
  #ydesk #yd-data .dc501-secondary summary{cursor:pointer;list-style:none;padding:11px 13px;border:1px solid #dce6ef;border-radius:11px;background:#fff;font-size:12px;font-weight:900;color:#2d4a65;box-shadow:0 3px 10px rgba(20,45,70,.04)}
  #ydesk #yd-data .dc501-secondary summary::-webkit-details-marker{display:none}
  #ydesk #yd-data .dc501-secondary[open] summary{border-radius:11px 11px 0 0}
  #ydesk #yd-data .dc501-secondary-body{border:1px solid #dce6ef;border-top:0;border-radius:0 0 11px 11px;background:#fff;padding:10px}
  #ydesk #yd-data .dc501-filelist{width:100%;max-width:650px;margin:8px 0 2px;padding:7px 9px;border-radius:9px;background:#f7fbff;border:1px solid #dce8f2;font-size:10px;line-height:1.4;color:#587087;text-align:left}
  #ydesk #yd-data .dc501-fileitem{display:flex;justify-content:space-between;gap:10px;padding:3px 0;border-bottom:1px solid #e9f0f5}
  #ydesk #yd-data .dc501-fileitem:last-child{border-bottom:0}
  #ydesk #yd-data .dc501-filetype{font-weight:900;color:#1d5c96}
  #ydesk #yd-data .dc501-subtle{font-size:9px;color:#8090a1}
  @media(max-width:1220px){#ydesk #yd-data .datagrid{grid-template-columns:1fr!important}#ydesk #yd-data .analysis{position:static!important}}
}
</style>
<script id="ydDataCenterFocusV501">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const x=Number(v);return Number.isFinite(x)?x:null};
  const first=(o,keys)=>{for(const k of keys){if(o&&o[k]!=null&&o[k]!=='')return o[k]}return null};
  const now=()=>Date.now();
  const fmtAge=ms=>{if(ms==null||ms<0)return '—';const s=Math.floor(ms/1000);if(s<60)return s+' sec';const m=Math.floor(s/60);if(m<60)return m+' min';const h=Math.floor(m/60);return h+'h '+(m%60)+'m'};
  const clock=v=>{if(!v)return '—';const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleTimeString([],{hour:'numeric',minute:'2-digit',second:'2-digit'})};
  const cardByTitle=t=>$$('#yd-data .card').find(c=>$('.cardhead h3',c)?.textContent.trim()===t)||null;
  const storageKey=id=>'yd-dc501-batch-'+String(id||'none');
  let pollBusy=false, recentBusy=false, latestRecent=null;

  function loadHist(id){try{return JSON.parse(localStorage.getItem(storageKey(id))||'null')||{batch_id:id,events:[],runs:[],statuses:[],lastSig:null,lastChangeAt:null,firstSeenAt:now()}}catch(_e){return {batch_id:id,events:[],runs:[],statuses:[],lastSig:null,lastChangeAt:null,firstSeenAt:now()}}}
  function saveHist(id,h){try{localStorage.setItem(storageKey(id),JSON.stringify(h))}catch(_e){}}
  function addEvent(h,label,detail){h.events.unshift({t:now(),label,detail});h.events=h.events.slice(0,12)}
  function observe(b){
    if(!b?.batch_id)return null;const id=b.batch_id,h=loadHist(id),raw=String(b.processing_status||'NONE').toUpperCase(),run=String(b.active_pipeline_run_id||''),processed=first(b,['active_processed_rows','processed_rows','rows_processed','active_rows_processed','progress_rows']),checkpoint=first(b,['active_checkpoint_name','checkpoint_name','active_checkpoint','checkpoint']),file=first(b,['active_file_name','file_name']);
    const sig=JSON.stringify([raw,run,processed,checkpoint,file]);
    if(sig!==h.lastSig){
      if(h.lastSig!=null){h.lastChangeAt=now();addEvent(h,'Progress changed',raw+(run?' · Run #'+run:''))}else{h.lastChangeAt=now();addEvent(h,'Observed batch',raw)}
      h.lastSig=sig;
      if(run&&h.runs[h.runs.length-1]!==run){h.runs.push(run);h.runs=h.runs.slice(-10);if(h.runs.length>1)addEvent(h,'Run changed','Run #'+run)}
      if(raw&&h.statuses[h.statuses.length-1]!==raw){h.statuses.push(raw);h.statuses=h.statuses.slice(-20);addEvent(h,'Stage changed',raw.replaceAll('_',' '))}
    }
    saveHist(id,h);return h;
  }
  function serverActivityAt(b){
    const v=first(b,['active_worker_heartbeat_at','worker_heartbeat_at','heartbeat_at','active_checkpoint_at','checkpoint_at','updated_at','active_updated_at','processing_updated_at']);
    const d=v?new Date(v):null;return d&&!Number.isNaN(d.getTime())?d.getTime():null;
  }
  function classify(b,h){
    if(!b)return {kind:'idle',label:'IDLE',why:'No active batch.'};
    const raw=String(b.processing_status||'').toUpperCase();
    if(/FAIL|ERROR|ABORT/.test(raw))return {kind:'failed',label:'FAILED',why:'The current batch reports a failure state.'};
    if(/QUICK_CHECK_READY|COMPLETE|PUBLISHED/.test(raw))return {kind:'done',label:'PUBLISHED',why:'Processing reached a terminal published/ready state.'};
    const waiting=/READY|PENDING_QA|HOLD/.test(raw);
    const activityAt=serverActivityAt(b)||h?.lastChangeAt||h?.firstSeenAt||now();
    const age=now()-activityAt;
    const statuses=h?.statuses||[],runs=h?.runs||[];
    const visits=statuses.filter(x=>x===raw).length;
    const repeated=runs.length>=3||visits>=3;
    if(repeated)return {kind:'repeating',label:'REPEATING',why:runs.length>=3?('Same batch observed across '+runs.length+' run IDs.'):(raw.replaceAll('_',' ')+' was re-entered '+visits+' times.') ,age};
    if(waiting)return {kind:'waiting',label:'WAITING',why:raw==='PHASE2C_READY'?'Phase 2C is complete and the batch is waiting for Phase 3 QA.':'The current state is a waiting/hold state.',age};
    if(age>180000)return {kind:'stuck',label:'STUCK',why:'No observed stage, row, checkpoint, run, or server activity change for '+fmtAge(age)+'.',age};
    return {kind:'working',label:'WORKING',why:'Recent processing activity has been observed.',age};
  }
  function box(label,value,sub=''){return '<div class="dc501-box"><label>'+esc(label)+'</label><strong>'+esc(value)+'</strong>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div>'}
  function ensureHero(c){let x=$('.dc501-hero',c);if(!x){x=document.createElement('div');x.className='dc501-hero';const body=$('.cardbody',c);body?.prepend(x)}return x}
  function ensureActivity(c){let x=$('.dc501-activity',c);if(!x){x=document.createElement('div');x.className='dc501-activity';$('.cardbody',c)?.appendChild(x)}return x}
  function renderCurrent(b,h){
    const c=cardByTitle('2. Current Processing');if(!c)return;const health=classify(b,h),hero=ensureHero(c),raw=String(b?.processing_status||'NONE').toUpperCase();
    const activityAt=serverActivityAt(b)||h?.lastChangeAt||h?.firstSeenAt||null;
    const stageAge=h?.statuses?.length?fmtAge(now()-(h.lastChangeAt||h.firstSeenAt)):fmtAge(now()-(h?.firstSeenAt||now()));
    const file=first(b,['active_file_name','file_name'])||'—',run=b?.active_pipeline_run_id?('#'+b.active_pipeline_run_id):'—';
    const worker=first(b,['active_worker_name','worker_name','active_worker_id','worker_id','active_worker_status','worker_status'])||'Not reported';
    const heartbeat=first(b,['active_worker_heartbeat_at','worker_heartbeat_at','heartbeat_at']);
    const checkpoint=first(b,['active_checkpoint_name','checkpoint_name','active_checkpoint','checkpoint'])||'Not reported';
    const runs=h?.runs||[],statuses=h?.statuses||[];
    hero.innerHTML='<div><h4>Batch '+(b?.batch_id?'#'+esc(b.batch_id):'—')+' · '+esc(raw.replaceAll('_',' '))+'</h4><p>'+esc(health.why)+'</p></div><span class="dc501-health '+esc(health.kind)+'">'+esc(health.label)+'</span>';
    let kv=$('.dc501-kv',c);if(!kv){kv=document.createElement('div');kv.className='dc501-kv';hero.insertAdjacentElement('afterend',kv)}
    kv.innerHTML=box('Current file',file)+box('Run',run,runs.length>1?runs.length+' run IDs observed':'')+box('Last activity',activityAt?clock(activityAt):'—',activityAt?fmtAge(now()-activityAt)+' ago':'not reported')+box('Stage age',stageAge,statuses.length?statuses[statuses.length-1].replaceAll('_',' '):'')+box('Worker',worker,heartbeat?'heartbeat '+clock(heartbeat):'')+box('Checkpoint',checkpoint);
    let alert=$('.dc501-alert',c);if(!alert){alert=document.createElement('div');alert.className='dc501-alert';kv.insertAdjacentElement('afterend',alert)}
    alert.className='dc501-alert '+(health.kind==='stuck'?'stuck':health.kind==='repeating'?'repeating':'');
    alert.innerHTML='<b>Health judgment:</b> '+esc(health.why)+(health.kind==='waiting'?'<br><span class="dc501-subtle">Waiting is not treated as stuck unless the state should be actively processing.</span>':'');
    const act=ensureActivity(c),events=h?.events||[];act.innerHTML='<h4>Recent Batch Activity</h4>'+(events.length?events.slice(0,6).map(e=>'<div class="dc501-event"><span>'+esc(clock(e.t))+'</span><div><b>'+esc(e.label)+'</b><br>'+esc(e.detail||'')+'</div></div>').join(''):'<div class="dc501-subtle">No client-observed activity history yet.</div>');
  }
  function detectFileType(name){const n=String(name||'').toLowerCase();if(/pos|sales/.test(n))return 'POS';if(/mvt|movement/.test(n))return 'MVT';if(/price/.test(n))return 'PRICE';if(/\boh\b|inventory|inv/.test(n))return 'OH';if(/live|fresh/.test(n))return 'LIVE/FRESH';if(/frozen|frz/.test(n))return 'FROZEN';return 'AUTO DETECT'}
  function bindUploadList(){const input=$('#ydFiles');if(!input||input.dataset.dc501)return;input.dataset.dc501='1';input.addEventListener('change',()=>{const up=$('#yd-data .upload');if(!up)return;let list=$('.dc501-filelist',up);if(!list){list=document.createElement('div');list.className='dc501-filelist';input.insertAdjacentElement('afterend',list)}const files=[...input.files];list.innerHTML=files.length?files.map(f=>'<div class="dc501-fileitem"><span>'+esc(f.name)+'</span><span class="dc501-filetype">'+esc(detectFileType(f.name))+'</span></div>').join(''):'No files selected.'})}
  function collapseSecondary(){
    const grid=$('#yd-data .datagrid');if(!grid||grid.dataset.dc501)return;grid.dataset.dc501='1';
    const left=grid.firstElementChild;if(!left)return;
    const cards=$$('.card',left);const upload=cards.find(c=>$('.cardhead h3',c)?.textContent.trim()==='1. Upload New Files');
    const completeness=cards.find(c=>$('.cardhead h3',c)?.textContent.includes('14-Day Completeness'));
    const recent=cards.find(c=>$('.cardhead h3',c)?.textContent.trim()==='4. Recent Batches');
    if(completeness||recent){const d=document.createElement('details');d.className='dc501-secondary';d.innerHTML='<summary>Data History, Completeness & Recent Batches</summary><div class="dc501-secondary-body"></div>';const body=$('.dc501-secondary-body',d);if(completeness)body.appendChild(completeness);if(recent)body.appendChild(recent);left.appendChild(d)}
    if(upload)upload.style.marginTop='0';
  }
  async function poll(){
    if(pollBusy||!$('#yd-data')?.classList.contains('active'))return;pollBusy=true;try{const r=await fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'});if(!r.ok)return;const a=await r.json(),b=a.active_batch||null,h=observe(b);renderCurrent(b,h);bindUploadList();collapseSecondary()}catch(_e){}finally{pollBusy=false}}
  function boot(){bindUploadList();collapseSecondary();poll()}
  const root=$('#yd-data');if(root)new MutationObserver(()=>setTimeout(boot,80)).observe(root,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target?.id==='ydDataRefresh'||e.target?.id==='ydUpload')setTimeout(poll,450)},true);
  setInterval(poll,3000);setTimeout(boot,900);
})();
</script>
'''


def inject_data_center_focus_v501(html:str)->str:
    if _MARKER in html:return html
    return html.replace('</body>',_PATCH+'</body>',1)
