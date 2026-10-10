from __future__ import annotations

"""Data Center v502 compact control-panel overlay.

Makes upload + current batch monitoring fit in one screen and treats a
PHASE2C_READY batch with no queued/started Phase 3 run as a handoff problem,
not an indefinitely-normal WAITING state.
"""

_MARKER='ydDataCenterFocusV502'

_PATCH=r'''
<style id="ydDataCenterFocusV502">
@media (min-width:760px){
  #ydesk #yd-data .pagehead{margin-bottom:8px!important;align-items:center!important}
  #ydesk #yd-data .pagehead h2{font-size:34px!important}
  #ydesk #yd-data .pagehead p{margin-top:3px!important;font-size:13px!important}
  #ydesk #yd-data .datagrid{grid-template-columns:minmax(0,1.7fr) minmax(400px,.72fr)!important;gap:10px!important}
  #ydesk #yd-data .cardhead{min-height:46px!important;padding:10px 14px!important}
  #ydesk #yd-data .cardhead h3{font-size:15px!important}
  #ydesk #yd-data .cardbody{padding:10px 12px!important}

  /* Upload is the primary action but no longer wastes vertical space. */
  #ydesk #yd-data .upload{min-height:190px!important;padding:13px 16px!important;justify-content:center!important}
  #ydesk #yd-data .upload>div:first-child{font-size:19px!important;line-height:1!important}
  #ydesk #yd-data .upload h3{font-size:17px!important;margin:3px 0!important}
  #ydesk #yd-data .upload p{font-size:10px!important;margin:1px 0 6px!important}
  #ydesk #yd-data .upload input[type=file]{font-size:11px!important}
  #ydesk #yd-data .upload .input{height:34px!important;font-size:12px!important}
  #ydesk #yd-data #ydUpload{min-height:38px!important;font-size:12px!important;padding:0 15px!important;margin-top:6px!important}
  #ydesk #yd-data #ydUploadResult{margin-top:7px!important;padding:6px 9px!important;line-height:1.3!important}
  #ydesk #yd-data .dc500-upload-note,#ydesk #yd-data .dc501-filelist{margin-top:5px!important;padding:5px 8px!important;font-size:9px!important}

  /* Current Processing: dense control panel. */
  #ydesk #yd-data .analysis{top:82px!important}
  #ydesk #yd-data .dc501-hero{margin:0 0 6px!important;padding:9px 10px!important;border-radius:9px!important}
  #ydesk #yd-data .dc501-hero h4{font-size:14px!important}
  #ydesk #yd-data .dc501-hero p{font-size:9px!important;margin-top:2px!important;line-height:1.3!important}
  #ydesk #yd-data .dc501-health{min-width:88px!important;padding:7px 9px!important;font-size:10px!important}
  #ydesk #yd-data .dc501-kv{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:5px!important;margin-top:5px!important}
  #ydesk #yd-data .dc501-box{padding:6px 7px!important;border-radius:7px!important;min-height:54px!important}
  #ydesk #yd-data .dc501-box label{font-size:7px!important}
  #ydesk #yd-data .dc501-box strong{font-size:11px!important;margin-top:2px!important}
  #ydesk #yd-data .dc501-box small{font-size:8px!important;margin-top:1px!important;line-height:1.2!important}
  #ydesk #yd-data .dc501-alert{margin-top:6px!important;padding:7px 8px!important;font-size:9px!important;line-height:1.35!important}
  #ydesk #yd-data .dc501-activity{margin-top:7px!important}
  #ydesk #yd-data .dc501-activity h4{font-size:10px!important;margin-bottom:3px!important}
  #ydesk #yd-data .dc501-event{grid-template-columns:52px 1fr!important;padding:3px 0!important;font-size:8px!important;line-height:1.25!important}
  #ydesk #yd-data .dc501-event b{font-size:9px!important}
  #ydesk #yd-data .dc501-activity .dc501-event:nth-of-type(n+4){display:none!important}

  /* Hide legacy monitor duplication; v501/v502 is the authoritative panel. */
  #ydesk #yd-data .analysis .dc496-file,
  #ydesk #yd-data .analysis .dc500-monitor,
  #ydesk #yd-data .analysis .row3,
  #ydesk #yd-data .analysis .pipeline,
  #ydesk #yd-data .analysis .sectiontitle,
  #ydesk #yd-data .analysis .dc496-scope-note,
  #ydesk #yd-data .analysis .tablewrap,
  #ydesk #yd-data .analysis .dc496-latest{display:none!important}

  #ydesk #yd-data .dc501-secondary{margin-top:7px!important}
  #ydesk #yd-data .dc501-secondary summary{padding:8px 10px!important;font-size:10px!important}

  #ydesk #yd-data .dc502-handoff{margin-top:6px;padding:7px 8px;border-radius:8px;border:1px solid #f0c9cf;background:#fff4f5;color:#922e3d;font-size:9px;line-height:1.35}
  #ydesk #yd-data .dc502-handoff b{font-size:10px}

  @media(max-width:1280px){
    #ydesk #yd-data .datagrid{grid-template-columns:minmax(0,1.45fr) minmax(370px,.75fr)!important}
    #ydesk #yd-data .dc501-kv{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  }
  @media(max-width:1120px){
    #ydesk #yd-data .datagrid{grid-template-columns:1fr!important}
    #ydesk #yd-data .analysis{position:static!important}
  }
}
</style>
<script id="ydDataCenterFocusV502">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const $=(s,r=document)=>r.querySelector(s);
  let busy=false;
  function histAge(batchId){
    try{
      const h=JSON.parse(localStorage.getItem('yd-dc501-batch-'+String(batchId))||'null');
      const t=h?.lastChangeAt||h?.firstSeenAt;return t?Math.max(0,Date.now()-Number(t)):0;
    }catch(_e){return 0}
  }
  function fmt(ms){const s=Math.floor(ms/1000);if(s<60)return s+' sec';const m=Math.floor(s/60);if(m<60)return m+' min';return Math.floor(m/60)+'h '+(m%60)+'m'}
  async function diagnose(){
    if(busy||!$('#yd-data.active'))return;busy=true;
    try{
      const r=await fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'});if(!r.ok)return;
      const a=await r.json(),b=a.active_batch||null;if(!b)return;
      const raw=String(b.processing_status||'').toUpperCase();
      const run=b.active_pipeline_run_id||null;
      const card=[...document.querySelectorAll('#yd-data .card')].find(c=>$('.cardhead h3',c)?.textContent.trim()==='2. Current Processing');if(!card)return;
      let note=$('.dc502-handoff',card);
      if(raw==='PHASE2C_READY'&&!run){
        const age=histAge(b.batch_id);
        if(!note){note=document.createElement('div');note.className='dc502-handoff';$('.dc501-alert',card)?.insertAdjacentElement('afterend',note)}
        if(note){
          note.innerHTML='<b>Phase 3 handoff not active</b><br>Phase 2C is ready, but the server reports no queued/started Phase 3 Run ID and no worker ownership. The production worker is designed to auto-queue a PHASE3_RERUN for this state. '+(age>=30000?('This has remained unchanged for '+fmt(age)+'. Check worker recovery/retry history; it should not stay here indefinitely.'):'A short handoff delay is normal immediately after Phase 2C.')
        }
        if(age>=30000){
          const pill=$('.dc501-health',card);if(pill){pill.className='dc501-health stuck';pill.textContent='PHASE 3 NOT STARTED'}
          const heroP=$('.dc501-hero p',card);if(heroP)heroP.textContent='Phase 2C is complete, but no Phase 3 run has been queued or claimed.';
        }
      }else if(note){note.remove()}
    }catch(_e){}finally{busy=false}
  }
  document.addEventListener('click',e=>{if(e.target?.id==='ydDataRefresh')setTimeout(diagnose,400)},true);
  setInterval(diagnose,3000);setTimeout(diagnose,900);
})();
</script>
'''


def inject_data_center_focus_v502(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)

