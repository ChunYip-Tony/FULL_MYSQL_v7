from __future__ import annotations

"""Yipman Back Office Data Center consistency patch.

The desktop Data Center previously mixed two scopes:
- the Current Processing KPI came from the active batch; and
- Top QA Holds came from the global QA review queue.

That could render an impossible-looking state such as "Open Issues 0" while an
unrelated historical QA hold was listed directly underneath. This layer keeps
Current Processing strictly scoped to the current/latest batch and gives
INGESTED_PENDING_QA an explicit waiting state.
"""

_MARKER = 'data-center-v481-js'

_PATCH = r'''
<style id="data-center-v481-css">
@media (min-width:760px){
  #ydesk #yd-data .dc481-waiting{background:#fff4d8!important;color:#956000!important}
  #ydesk #yd-data .dc481-ok{background:#e9f8ef!important;color:#147b49!important}
  #ydesk #yd-data .dc481-scope-note{margin:6px 0 8px;padding:7px 9px;border:1px solid #dbe7f2;border-radius:8px;background:#f7fbff;color:#5d7188;font-size:9px;line-height:1.35}
  #ydesk #yd-data .dc481-empty{padding:12px 9px!important;color:#6b7d92!important;text-align:center!important;font-size:10px!important}
  #ydesk #yd-data .dc481-count{font-weight:900;color:#223b56}
}
</style>
<script id="data-center-v481-js">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>Number.isFinite(Number(v))?Number(v):0;
  let busy=false,refreshTimer=null;

  function dataVisible(){
    const el=document.querySelector('#yd-data');
    return !!el && el.classList.contains('active');
  }
  function processingCard(){
    return [...document.querySelectorAll('#yd-data .card')].find(c=>c.querySelector('.cardhead h3')?.textContent.trim()==='2. Current Processing')||null;
  }
  function liveIssueMap(b){
    const v=b?.active_progress_issue_counts;
    if(!v||typeof v!=='object'||Array.isArray(v)||!Object.keys(v).length)return null;
    return v;
  }
  function issueRows(b){
    const live=liveIssueMap(b);
    const rows=live
      ? Object.entries(live).map(([issue_code,issue_count])=>({issue_code,issue_count:num(issue_count)}))
      : (Array.isArray(b?.active_issue_counts)?b.active_issue_counts.map(x=>({issue_code:x.issue_code||x.code||x.issue_summary||'UNKNOWN',issue_count:num(x.issue_count??x.count)})):[]);
    return rows.filter(x=>x.issue_count>0).sort((a,z)=>z.issue_count-a.issue_count||String(a.issue_code).localeCompare(String(z.issue_code)));
  }
  function activeIssueTotal(b,rows){
    const live=liveIssueMap(b);
    if(live)return Object.values(live).reduce((n,v)=>n+num(v),0);
    if(b?.active_issue_total!=null)return num(b.active_issue_total);
    if(b?.open_issue_total!=null)return num(b.open_issue_total);
    if(b?.error_count!=null)return num(b.error_count);
    return rows.reduce((n,x)=>n+x.issue_count,0);
  }
  function patchCard(b,sig){
    const card=processingCard();if(!card)return;
    const raw=String(b?.processing_status||'NONE').toUpperCase();
    const rows=issueRows(b),total=activeIssueTotal(b,rows);
    const batch=b?.batch_id?('#'+b.batch_id):'None';

    const badge=card.querySelector('.cardhead .badge');
    if(badge){
      badge.classList.remove('dc481-waiting','dc481-ok');
      if(raw==='INGESTED_PENDING_QA'){
        badge.textContent='WAITING FOR QA';badge.classList.add('dc481-waiting');badge.title='INGESTED_PENDING_QA';
      }else if(/QUICK_CHECK_READY|COMPLETE|PUBLISHED/.test(raw)){
        badge.textContent=raw;badge.classList.add('dc481-ok');badge.title=raw;
      }else{badge.textContent=raw;badge.title=raw}
    }

    [...card.querySelectorAll('.kpi')].forEach(k=>{
      const label=k.querySelector('label')?.textContent.trim();
      if(label==='Batch'&&k.querySelector('strong'))k.querySelector('strong').textContent=batch;
      if(label==='Open Issues'&&k.querySelector('strong'))k.querySelector('strong').textContent=String(total);
    });

    const stages=[...card.querySelectorAll('.pipeline .stage')];
    if(raw==='INGESTED_PENDING_QA'&&stages.length>=5){
      stages[0].classList.add('done');
      stages[1].classList.add('done');
      stages[2].classList.remove('done','hold','dc481-waiting');
      stages[2].textContent='PHASE 2C';
      stages[3].classList.remove('done','hold');
      stages[3].classList.add('dc481-waiting');
      stages[3].textContent='PHASE 3 QA · WAITING';
      stages[4].classList.remove('done','hold','dc481-waiting');
      stages[4].textContent='PUBLISH';
    }

    const title=[...card.querySelectorAll('.sectiontitle')].find(x=>x.textContent.trim()==='Top QA Holds'||x.textContent.trim()==='Top Current-Batch QA Holds');
    const table=title?.nextElementSibling?.matches('.dc481-scope-note')?title.nextElementSibling.nextElementSibling?.querySelector('table'):title?.nextElementSibling?.querySelector('table');
    if(table){
      const th=table.querySelectorAll('thead th');
      if(th.length>=3){th[0].textContent='Issue';th[1].textContent='Count';th[2].textContent='Scope'}
      const body=table.querySelector('tbody');
      if(body){
        body.innerHTML=rows.length
          ? rows.slice(0,12).map(x=>'<tr><td>'+esc(x.issue_code)+'</td><td class="dc481-count">'+esc(x.issue_count)+'</td><td>Current batch</td></tr>').join('')
          : '<tr><td colspan="3" class="dc481-empty">No current-batch QA holds reported.</td></tr>';
      }
      let note=card.querySelector('.dc481-scope-note');
      if(!note){note=document.createElement('div');note.className='dc481-scope-note';title.insertAdjacentElement('afterend',note)}
      note.innerHTML='<b>Scope:</b> Batch '+esc(batch)+'. Historical/global QA items are not mixed into Current Processing.';
      title.textContent='Top Current-Batch QA Holds';
    }
    card.dataset.dc481Sig=sig;
  }
  async function refresh(){
    if(busy||!dataVisible())return;
    busy=true;
    try{
      const r=await fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'});
      if(!r.ok)return;
      const a=await r.json();
      const b=a.active_batch||a.latest_batch||{};
      const sig=JSON.stringify([b.batch_id,b.processing_status,b.active_issue_total,b.open_issue_total,b.error_count,b.active_progress_issue_counts,b.active_issue_counts]);
      const card=processingCard();
      if(card&&card.dataset.dc481Sig!==sig)patchCard(b,sig);
    }catch(_e){}finally{busy=false}
  }
  function scheduleRefresh(delay=80){
    clearTimeout(refreshTimer);
    refreshTimer=setTimeout(refresh,delay);
  }
  const root=document.querySelector('#yd-data');
  if(root){
    const mo=new MutationObserver(()=>{if(dataVisible())scheduleRefresh()});
    mo.observe(root,{subtree:true,childList:true});
  }
  document.addEventListener('click',e=>{if(e.target?.id==='ydDataRefresh')scheduleRefresh(250)},true);
  setInterval(refresh,4000);
  scheduleRefresh(500);
})();
</script>
'''


def inject_data_center_fix(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)
