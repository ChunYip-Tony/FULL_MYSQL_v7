from __future__ import annotations

"""Data Center v503: self-healing Phase 2C -> Phase 3 handoff.

When the browser confirms PHASE2C_READY with no queued/started Phase 3 run for
more than a short handoff grace period, expose a clear recovery action and make
one guarded resume request per batch/session. The existing server endpoint owns
all concurrency/version checks, so this UI cannot create a parallel Phase 3 run.
"""

_MARKER='ydDataCenterFocusV503'

_PATCH=r'''
<style id="ydDataCenterFocusV503">
@media (min-width:760px){
  #ydesk #yd-data .dc503-recovery{display:flex;align-items:center;gap:7px;margin-top:6px}
  #ydesk #yd-data .dc503-recovery button{border:0;border-radius:7px;background:#b42336;color:#fff;font-size:9px;font-weight:900;padding:7px 10px;cursor:pointer}
  #ydesk #yd-data .dc503-recovery button:disabled{opacity:.55;cursor:default}
  #ydesk #yd-data .dc503-recovery span{font-size:8px;color:#7d5260;line-height:1.25}
  #ydesk #yd-data .dc503-recovery.ok button{background:#17764a}
  #ydesk #yd-data .dc503-recovery.ok span{color:#32684f}
}
</style>
<script id="ydDataCenterFocusV503">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const $=(s,r=document)=>r.querySelector(s);
  let probeBusy=false;
  const retryKey=id=>'yd-dc503-phase3-resume-'+String(id||'none');
  function histAge(id){
    try{
      const h=JSON.parse(localStorage.getItem('yd-dc501-batch-'+String(id))||'null');
      const t=h?.lastChangeAt||h?.firstSeenAt;return t?Math.max(0,Date.now()-Number(t)):0;
    }catch(_e){return 0}
  }
  function card(){return [...document.querySelectorAll('#yd-data .card')].find(c=>$('.cardhead h3',c)?.textContent.trim()==='2. Current Processing')||null}
  function removeRecovery(){const c=card(),x=c&&$('.dc503-recovery',c);if(x)x.remove()}
  async function resume(batchId,box,automatic=false){
    const btn=$('button',box),msg=$('span',box);if(btn)btn.disabled=true;
    if(msg)msg.textContent=automatic?'Automatic recovery request sent…':'Starting Phase 3…';
    try{
      const r=await fetch('/v1/web-upload/batches/'+encodeURIComponent(batchId)+'/resume-phase3',{
        method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'}
      });
      let body=null;try{body=await r.json()}catch(_e){}
      if(r.ok){
        sessionStorage.setItem(retryKey(batchId),'requested');
        box.classList.add('ok');
        if(msg)msg.textContent='Phase 3 recovery queued. Waiting for worker claim…';
        setTimeout(()=>window.dispatchEvent(new Event('yd-dc503-refresh')),400);
      }else if(r.status===409){
        sessionStorage.setItem(retryKey(batchId),'handled');
        if(msg)msg.textContent='Server reports a pipeline state change. Refreshing status…';
        setTimeout(()=>window.dispatchEvent(new Event('yd-dc503-refresh')),400);
      }else{
        if(msg)msg.textContent='Recovery request failed'+(body?.detail?.reason?': '+body.detail.reason:'')+'. Use Start Phase 3 to retry.';
        if(btn)btn.disabled=false;
      }
    }catch(_e){
      if(msg)msg.textContent='Recovery request could not reach the server. Use Start Phase 3 to retry.';
      if(btn)btn.disabled=false;
    }
  }
  function ensureRecovery(batchId,age){
    const c=card();if(!c)return null;
    let x=$('.dc503-recovery',c);
    if(!x){
      x=document.createElement('div');x.className='dc503-recovery';
      x.innerHTML='<button type="button">Start Phase 3</button><span>Phase 2C is complete but no Phase 3 run is active.</span>';
      const anchor=$('.dc502-handoff',c)||$('.dc501-alert',c);anchor?.insertAdjacentElement('afterend',x);
      $('button',x)?.addEventListener('click',()=>resume(batchId,x,false));
    }
    const msg=$('span',x);if(msg&&age>=30000)msg.textContent='No Phase 3 Run ID after handoff grace period. One guarded recovery attempt is allowed.';
    return x;
  }
  async function probe(){
    if(probeBusy||!$('#yd-data.active'))return;probeBusy=true;
    try{
      const r=await fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'});if(!r.ok)return;
      const a=await r.json(),b=a.active_batch||null;if(!b){removeRecovery();return}
      const raw=String(b.processing_status||'').toUpperCase(),run=b.active_pipeline_run_id||null;
      if(raw!=='PHASE2C_READY'||run){removeRecovery();return}
      const age=histAge(b.batch_id),box=ensureRecovery(b.batch_id,age);if(!box)return;
      // Polling is read-only. Worker owns automatic recovery; reloading a
      // page must not reset the retry budget and create another run.
    }catch(_e){}finally{probeBusy=false}
  }
  window.addEventListener('yd-dc503-refresh',()=>setTimeout(probe,250));
  const root=$('#yd-data');if(root)new MutationObserver(()=>setTimeout(probe,120)).observe(root,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target?.id==='ydDataRefresh')setTimeout(probe,350)},true);
  setInterval(probe,3000);setTimeout(probe,1100);
})();
</script>
'''


def inject_data_center_focus_v503(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)

