from __future__ import annotations

"""Yipman / Back Office Data Center status consistency patch.

Key rules:
- "Current Processing" must show ONLY an actually active batch. Never fall back
  to the latest completed batch.
- The latest completed/terminal batch belongs in upload history / latest-server
  status, not in Current Processing.
- Browser refresh must not erase the most recent server-side upload result.
- Current file identity and live run telemetry should be shown when available.
- QA rows shown under Current Processing must be scoped to that active batch.
"""

_MARKER = 'data-center-v495-js'

_PATCH = r'''
<style id="data-center-v495-css">
@media (min-width:760px){
  #ydesk #yd-data .dc495-waiting{background:#fff4d8!important;color:#956000!important}
  #ydesk #yd-data .dc495-ok{background:#e9f8ef!important;color:#147b49!important}
  #ydesk #yd-data .dc495-idle{background:#edf2f6!important;color:#5d6d7d!important}
  #ydesk #yd-data .dc495-danger{background:#ffe9ed!important;color:#b82f45!important}
  #ydesk #yd-data .dc495-scope-note{margin:6px 0 8px;padding:8px 10px;border:1px solid #dbe7f2;border-radius:8px;background:#f7fbff;color:#5d7188;font-size:11px;line-height:1.4}
  #ydesk #yd-data .dc495-empty{padding:12px 9px!important;color:#6b7d92!important;text-align:center!important;font-size:11px!important}
  #ydesk #yd-data .dc495-count{font-weight:900;color:#223b56}
  #ydesk #yd-data .dc495-file{margin:9px 0 0;padding:9px 10px;border:1px solid #dbe5ef;border-radius:9px;background:#fbfdff;font-size:11px;line-height:1.45;color:#536981;overflow-wrap:anywhere}
  #ydesk #yd-data .dc495-file b{color:#183653}
  #ydesk #yd-data .dc495-latest{margin-top:7px;padding:8px 10px;border-radius:8px;background:#f1f6fb;border:1px solid #dce8f2;color:#536981;font-size:11px;line-height:1.4}
  #ydesk #yd-data .dc495-latest strong{color:#173653}
}
</style>
<script id="data-center-v495-js">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>Number.isFinite(Number(v))?Number(v):0;
  let busy=false,refreshTimer=null;

  function dataVisible(){const el=document.querySelector('#yd-data');return !!el&&el.classList.contains('active')}
  function processingCard(){return [...document.querySelectorAll('#yd-data .card')].find(c=>c.querySelector('.cardhead h3')?.textContent.trim()==='2. Current Processing')||null}
  function liveIssueMap(b){const v=b?.active_progress_issue_counts;return (!v||typeof v!=='object'||Array.isArray(v)||!Object.keys(v).length)?null:v}
  function issueRows(b){
    const live=liveIssueMap(b);
    const rows=live?Object.entries(live).map(([issue_code,issue_count])=>({issue_code,issue_count:num(issue_count)})):(Array.isArray(b?.active_issue_counts)?b.active_issue_counts.map(x=>({issue_code:x.issue_code||x.code||x.issue_summary||'UNKNOWN',issue_count:num(x.issue_count??x.count)})):[]);
    return rows.filter(x=>x.issue_count>0).sort((a,z)=>z.issue_count-a.issue_count||String(a.issue_code).localeCompare(String(z.issue_code)));
  }
  function activeIssueTotal(b,rows){
    const live=liveIssueMap(b);if(live)return Object.values(live).reduce((n,v)=>n+num(v),0);
    if(b?.active_issue_total!=null)return num(b.active_issue_total);
    if(b?.open_issue_total!=null)return num(b.open_issue_total);
    if(b?.error_count!=null)return num(b.error_count);
    return rows.reduce((n,x)=>n+x.issue_count,0);
  }
  function terminal(s){return /QUICK_CHECK_READY|COMPLETE|PUBLISHED|PHASE3_QA_HOLD|API_ABORTED/.test(String(s||'').toUpperCase())}
  function recentFiles(recent,latest){
    const bid=Number(latest?.batch_id||0);if(!bid)return [];
    const rows=recent?.batches||recent?.rows||[];
    const row=rows.find(x=>Number(x?.batch_id||0)===bid)||null;
    return Array.isArray(row?.files)?row.files:[];
  }
  function setKpi(card,label,value){[...card.querySelectorAll('.kpi')].forEach(k=>{if(k.querySelector('label')?.textContent.trim()===label&&k.querySelector('strong'))k.querySelector('strong').textContent=value})}
  function resetStages(card){[...card.querySelectorAll('.pipeline .stage')].forEach(s=>s.classList.remove('done','hold','dc495-waiting'))}
  function markStages(card,raw){
    const s=[...card.querySelectorAll('.pipeline .stage')];if(s.length<5)return;resetStages(card);
    if(raw==='API_UPLOADING'){s[0].classList.add('done');return}
    if(/INGESTED_PENDING_QA|RAW_RELEASED|RELEASED/.test(raw)){s[0].classList.add('done');s[1].classList.add('done');s[2].classList.add('dc495-waiting');return}
    if(raw==='PHASE2C_READY'){s[0].classList.add('done');s[1].classList.add('done');s[2].classList.add('done');s[3].classList.add('dc495-waiting');return}
    if(/PHASE3/.test(raw)){s[0].classList.add('done');s[1].classList.add('done');s[2].classList.add('done');raw.includes('HOLD')?s[3].classList.add('hold'):s[3].classList.add('done');return}
    if(/QUICK_CHECK_READY|COMPLETE|PUBLISHED/.test(raw)){s.forEach(x=>x.classList.add('done'))}
  }
  function patchCard(active,latest,recent,sig){
    const card=processingCard();if(!card)return;
    const b=active||null,raw=String(b?.processing_status||'NONE').toUpperCase();
    const rows=b?issueRows(b):[],total=b?activeIssueTotal(b,rows):0;
    const batch=b?.batch_id?('#'+b.batch_id):'None';
    const badge=card.querySelector('.cardhead .badge');
    if(badge){
      badge.classList.remove('dc495-waiting','dc495-ok','dc495-idle','dc495-danger','blue','green','amber','red','gray');
      if(!b){badge.textContent='NO ACTIVE PROCESSING';badge.classList.add('dc495-idle');badge.title='No active ingest or pipeline run'}
      else if(raw==='INGESTED_PENDING_QA'){badge.textContent='WAITING FOR QA';badge.classList.add('dc495-waiting');badge.title=raw}
      else if(/API_ABORTED|FAILED|ERROR/.test(raw)){badge.textContent=raw;badge.classList.add('dc495-danger');badge.title=raw}
      else if(terminal(raw)){badge.textContent=raw;badge.classList.add('dc495-ok');badge.title=raw}
      else{badge.textContent=raw;badge.classList.add('blue');badge.title=raw}
    }
    setKpi(card,'Batch',batch);setKpi(card,'Run',b?.active_pipeline_run_id?('#'+b.active_pipeline_run_id):'#—');setKpi(card,'Open Issues',String(total));
    if(b)markStages(card,raw);else resetStages(card);

    let file=card.querySelector('.dc495-file');
    if(b){
      if(!file){file=document.createElement('div');file.className='dc495-file';const pipe=card.querySelector('.pipeline');pipe?.insertAdjacentElement('afterend',file)}
      const fileName=b.active_file_name||'Waiting for file identity';
      const fileStatus=b.active_file_status||b.active_stage_name||raw;
      const source=b.active_source_type?(' · '+b.active_source_type):'';
      file.innerHTML='<b>Current file:</b> '+esc(fileName)+'<br><span>'+esc(fileStatus)+esc(source)+'</span>';
    }else if(file){file.remove()}

    const title=[...card.querySelectorAll('.sectiontitle')].find(x=>['Top QA Holds','Top Current-Batch QA Holds'].includes(x.textContent.trim()));
    const table=title?.nextElementSibling?.matches('.dc495-scope-note')?title.nextElementSibling.nextElementSibling?.querySelector('table'):title?.nextElementSibling?.querySelector('table');
    if(title&&table){
      const th=table.querySelectorAll('thead th');if(th.length>=3){th[0].textContent='Issue';th[1].textContent='Count';th[2].textContent='Scope'}
      const body=table.querySelector('tbody');
      if(body)body.innerHTML=!b?'<tr><td colspan="3" class="dc495-empty">No active batch. Current Processing is idle.</td></tr>':(rows.length?rows.slice(0,12).map(x=>'<tr><td>'+esc(x.issue_code)+'</td><td class="dc495-count">'+esc(x.issue_count)+'</td><td>Current batch</td></tr>').join(''):'<tr><td colspan="3" class="dc495-empty">No current-batch QA holds reported.</td></tr>');
      let note=card.querySelector('.dc495-scope-note');if(!note){note=document.createElement('div');note.className='dc495-scope-note';title.insertAdjacentElement('afterend',note)}
      note.innerHTML=b?('<b>Scope:</b> Batch '+esc(batch)+'. Historical/global QA items are not mixed into Current Processing.'):'<b>Scope:</b> No active batch. Historical/global QA items are intentionally excluded here.';
      title.textContent='Top Current-Batch QA Holds';
    }

    let latestBox=card.querySelector('.dc495-latest');if(!latestBox){latestBox=document.createElement('div');latestBox.className='dc495-latest';card.querySelector('.cardbody')?.appendChild(latestBox)}
    if(latest?.batch_id){
      const files=recentFiles(recent,latest),names=files.slice(0,3).map(f=>f.original_filename).filter(Boolean);
      latestBox.innerHTML='<strong>Latest server batch:</strong> #'+esc(latest.batch_id)+' · '+esc(latest.processing_status||'—')+(names.length?'<br><span>'+names.map(esc).join(' · ')+'</span>':'');
    }else latestBox.innerHTML='<strong>Latest server batch:</strong> —';
    card.dataset.dc495Sig=sig;
  }
  function patchUploadResult(active,latest,recent){
    const out=document.querySelector('#ydUploadResult');if(!out)return;
    const text=(out.textContent||'').trim();
    if(!/No upload in this session\.?/i.test(text))return;
    if(active?.batch_id){out.innerHTML='<b>Server processing · Batch #'+esc(active.batch_id)+'</b><br>'+esc(active.active_file_name||active.processing_status||'Active');return}
    if(latest?.batch_id){
      const files=recentFiles(recent,latest),names=files.slice(0,4).map(f=>f.original_filename).filter(Boolean);
      out.innerHTML='<b>Latest server upload · Batch #'+esc(latest.batch_id)+'</b><br>'+esc(latest.processing_status||'—')+(names.length?'<br>'+names.map(esc).join('<br>'):'');
    }
  }
  async function refresh(){
    if(busy||!dataVisible())return;busy=true;
    try{
      const [ar,rr]=await Promise.all([fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'}),fetch('/v1/web-upload/recent?limit=8',{cache:'no-store',credentials:'same-origin'})]);
      if(!ar.ok)return;
      const a=await ar.json(),recent=rr.ok?await rr.json():{};
      const active=a.active_batch||null,latest=a.latest_batch||null;
      const sig=JSON.stringify([active?.batch_id,active?.processing_status,active?.active_pipeline_run_id,active?.active_file_name,active?.active_file_status,active?.active_issue_total,active?.active_progress_issue_counts,latest?.batch_id,latest?.processing_status]);
      const card=processingCard();if(card&&card.dataset.dc495Sig!==sig)patchCard(active,latest,recent,sig);else if(card)patchUploadResult(active,latest,recent);
      patchUploadResult(active,latest,recent);
    }catch(_e){}finally{busy=false}
  }
  function scheduleRefresh(delay=80){clearTimeout(refreshTimer);refreshTimer=setTimeout(refresh,delay)}
  const root=document.querySelector('#yd-data');if(root){new MutationObserver(()=>{if(dataVisible())scheduleRefresh()}).observe(root,{subtree:true,childList:true})}
  document.addEventListener('click',e=>{if(e.target?.id==='ydDataRefresh'||e.target?.id==='ydUpload')scheduleRefresh(500)},true);
  setInterval(refresh,3000);scheduleRefresh(450);
})();
</script>
'''


def inject_data_center_fix(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)
