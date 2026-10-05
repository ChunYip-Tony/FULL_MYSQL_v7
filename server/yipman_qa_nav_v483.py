from __future__ import annotations

"""Desktop Yipman QA navigation patch.

Makes the top-bar QA holds KPI actionable and exposes the existing QA review
queue inside the stable Yipman desktop shell. This is UI-only: no QA issue is
waived, resolved, or mutated by this layer.
"""

_MARKER = "yipman-qa-nav-v483-js"

_PATCH = r'''
<style id="yipman-qa-nav-v483-css">
@media (min-width:760px){
  #ydesk .topstat.ydqa-open{cursor:pointer;user-select:none;transition:background .14s ease,border-color .14s ease,transform .14s ease}
  #ydesk .topstat.ydqa-open:hover,#ydesk .topstat.ydqa-open:focus-visible{background:rgba(255,255,255,.15)!important;border-color:rgba(255,255,255,.45)!important;outline:none;transform:translateY(-1px)}
  #ydQa483{position:fixed;inset:0;z-index:4000;display:none;background:rgba(8,25,43,.48);backdrop-filter:blur(2px);padding:34px}
  #ydQa483.open{display:flex;align-items:flex-start;justify-content:center}
  #ydQa483 .qa483-panel{width:min(1420px,calc(100vw - 68px));max-height:calc(100vh - 68px);display:flex;flex-direction:column;background:#f5f8fc;border:1px solid #d8e3ee;border-radius:16px;box-shadow:0 24px 70px rgba(5,27,49,.28);overflow:hidden}
  #ydQa483 .qa483-head{display:flex;align-items:center;gap:12px;padding:14px 16px;background:#fff;border-bottom:1px solid #dce6ef}
  #ydQa483 .qa483-head h2{margin:0;font-size:22px;color:#102842;letter-spacing:-.3px}
  #ydQa483 .qa483-head p{margin:3px 0 0;font-size:10px;color:#6d7f92}
  #ydQa483 .qa483-close{margin-left:auto;border:1px solid #d7e1eb;background:#fff;border-radius:9px;width:36px;height:36px;font-size:20px;color:#52677c;cursor:pointer}
  #ydQa483 .qa483-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;padding:10px 12px;background:#f8fbfe;border-bottom:1px solid #e2e9f0}
  #ydQa483 .qa483-kpi{border:1px solid #dfe7ef;border-radius:9px;background:#fff;padding:8px 10px}
  #ydQa483 .qa483-kpi small{display:block;font-size:8px;text-transform:uppercase;color:#748397;font-weight:900;letter-spacing:.3px}
  #ydQa483 .qa483-kpi b{display:block;font-size:20px;color:#132d49;margin-top:2px}
  #ydQa483 .qa483-tools{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:9px 12px;background:#fff;border-bottom:1px solid #e2e9f0}
  #ydQa483 .qa483-filter{border:1px solid #dbe5ef;background:#fff;border-radius:8px;padding:7px 10px;font-size:10px;font-weight:850;color:#50667e;cursor:pointer}
  #ydQa483 .qa483-filter.active{background:#0b72f4;border-color:#0b72f4;color:#fff}
  #ydQa483 .qa483-search{margin-left:auto;min-width:300px;height:34px;border:1px solid #dbe5ef;border-radius:8px;padding:0 10px;font-size:11px;color:#263d56;background:#fff}
  #ydQa483 .qa483-count{font-size:9px;color:#6c7d90;font-weight:850}
  #ydQa483 .qa483-body{min-height:220px;overflow:auto;padding:0 12px 12px}
  #ydQa483 table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #dfe7ef;border-radius:10px;overflow:hidden;margin-top:10px;table-layout:fixed}
  #ydQa483 th{position:sticky;top:0;z-index:2;background:#f8fbfe;border-bottom:1px solid #dce6ef;text-align:left;padding:8px;font-size:8px;text-transform:uppercase;color:#718197;letter-spacing:.3px}
  #ydQa483 td{padding:9px 8px;border-bottom:1px solid #edf2f6;vertical-align:top;font-size:10px;color:#273f59;white-space:normal;overflow-wrap:anywhere}
  #ydQa483 th:nth-child(1){width:30%}#ydQa483 th:nth-child(2){width:22%}#ydQa483 th:nth-child(3){width:14%}#ydQa483 th:nth-child(4){width:24%}#ydQa483 th:nth-child(5){width:10%}
  #ydQa483 .qa483-code{font-weight:900;color:#173451}.qa483-summary{font-size:9px;color:#718197;margin-top:3px;line-height:1.35}
  #ydQa483 .qa483-entity{font-weight:900;font-size:11px}.qa483-meta{font-size:9px;color:#718197;margin-top:2px}
  #ydQa483 .qa483-pill{display:inline-flex;border-radius:999px;padding:3px 6px;font-size:8px;font-weight:900}.qa483-pill.high{background:#ffe8ec;color:#b93148}.qa483-pill.med{background:#fff2d5;color:#8d6100}.qa483-pill.low{background:#e9f3ff;color:#1764b8}.qa483-pill.current{background:#e9f8ef;color:#17794a;margin-left:4px}
  #ydQa483 .qa483-empty{padding:34px;text-align:center;color:#718197;font-size:11px}
  #ydQa483 .qa483-error{margin:12px;padding:10px 12px;border-radius:8px;background:#fff0f2;color:#b32e44;border:1px solid #f3c9d0;font-size:10px}
  @media(max-width:1050px){#ydQa483{padding:18px}#ydQa483 .qa483-panel{width:calc(100vw - 36px);max-height:calc(100vh - 36px)}#ydQa483 .qa483-kpis{grid-template-columns:repeat(2,1fr)}#ydQa483 .qa483-search{min-width:210px;margin-left:0}}
}
</style>
<script id="yipman-qa-nav-v483-js">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let issues=[],currentBatch=null,filter='ALL',query='';

  function ensure(){
    let m=document.querySelector('#ydQa483');
    if(m)return m;
    m=document.createElement('div');m.id='ydQa483';m.innerHTML='<section class="qa483-panel" role="dialog" aria-modal="true" aria-labelledby="ydQa483Title"><div class="qa483-head"><div><h2 id="ydQa483Title">QA Fixes</h2><p>Open QA review queue · raw source rows remain unchanged until an explicit controlled fix is applied.</p></div><button class="qa483-close" type="button" aria-label="Close QA Fixes">×</button></div><div id="ydQa483Kpis" class="qa483-kpis"></div><div class="qa483-tools"><button class="qa483-filter active" data-f="ALL">All Open</button><button class="qa483-filter" data-f="CURRENT">Current Batch</button><button class="qa483-filter" data-f="HIGH">High / Critical</button><input id="ydQa483Search" class="qa483-search" placeholder="Search UPC / Article / Family / issue / item"><span id="ydQa483Count" class="qa483-count"></span></div><div id="ydQa483Body" class="qa483-body"><div class="qa483-empty">Loading QA…</div></div></section>';
    document.body.appendChild(m);
    m.querySelector('.qa483-close').onclick=close;
    m.addEventListener('click',e=>{if(e.target===m)close()});
    m.querySelectorAll('.qa483-filter').forEach(b=>b.onclick=()=>{filter=b.dataset.f;m.querySelectorAll('.qa483-filter').forEach(x=>x.classList.toggle('active',x===b));render()});
    m.querySelector('#ydQa483Search').addEventListener('input',e=>{query=e.target.value.trim().toLowerCase();render()});
    return m;
  }
  function close(){document.querySelector('#ydQa483')?.classList.remove('open')}
  function severityClass(s){s=String(s||'').toUpperCase();return ['HIGH','CRITICAL'].includes(s)?'high':s==='MEDIUM'?'med':'low'}
  function batchId(x){const v=x?.batch_id??x?.source_batch_id??x?.current?.batch_id;return v==null?null:String(v)}
  function searchBlob(x){const c=x.current||{};return [x.issue_code,x.issue_summary,x.entity_type,x.entity_key,x.severity,c.item_name,c.selling_description,c.chinese_name,c.main_article_number,c.family_description,c.selling_uom,c.current_cost_per_selling_unit].filter(Boolean).join(' ').toLowerCase()}
  function filtered(){
    let a=issues.slice();
    if(filter==='CURRENT')a=a.filter(x=>currentBatch!=null&&batchId(x)===String(currentBatch));
    if(filter==='HIGH')a=a.filter(x=>['HIGH','CRITICAL'].includes(String(x.severity||'').toUpperCase()));
    if(query)a=a.filter(x=>searchBlob(x).includes(query));
    return a;
  }
  function stateText(x){
    const c=x.current||{},p=[];
    if(c.selling_uom)p.push('Selling UOM '+c.selling_uom);
    if(c.current_cost_per_selling_unit!=null)p.push('Cost $'+Number(c.current_cost_per_selling_unit).toFixed(2));
    if(c.current_oh!=null)p.push('OH '+c.current_oh+(c.current_oh_uom?' '+c.current_oh_uom:''));
    if(c.upc_velocity_7d!=null)p.push('7D vel '+c.upc_velocity_7d);
    return p.join(' · ')||'No current serving state';
  }
  function render(){
    const m=ensure(),a=filtered(),high=issues.filter(x=>['HIGH','CRITICAL'].includes(String(x.severity||'').toUpperCase())).length,fixable=issues.filter(x=>x.can_fix).length,cur=issues.filter(x=>currentBatch!=null&&batchId(x)===String(currentBatch)).length;
    m.querySelector('#ydQa483Kpis').innerHTML='<div class="qa483-kpi"><small>All open</small><b>'+issues.length+'</b></div><div class="qa483-kpi"><small>Current batch'+(currentBatch!=null?' #'+esc(currentBatch):'')+'</small><b>'+cur+'</b></div><div class="qa483-kpi"><small>High / Critical</small><b>'+high+'</b></div><div class="qa483-kpi"><small>User-fixable</small><b>'+fixable+'</b></div>';
    m.querySelector('#ydQa483Count').textContent=a.length+' shown';
    const body=m.querySelector('#ydQa483Body');
    if(!a.length){body.innerHTML='<div class="qa483-empty">No QA issues match this filter.</div>';return}
    body.innerHTML='<table><thead><tr><th>Issue</th><th>Entity</th><th>Activity</th><th>Current State</th><th>Review</th></tr></thead><tbody>'+a.map(x=>{const c=x.current||{},sev=String(x.severity||'—').toUpperCase(),isCur=currentBatch!=null&&batchId(x)===String(currentBatch);return '<tr><td><span class="qa483-pill '+severityClass(sev)+'">'+esc(sev)+'</span>'+(isCur?'<span class="qa483-pill current">BATCH #'+esc(currentBatch)+'</span>':'')+'<div class="qa483-code">'+esc(x.issue_code||'—')+'</div><div class="qa483-summary">'+esc(x.issue_summary||'')+'</div></td><td><div class="qa483-entity">'+esc(x.entity_key||'—')+'</div><div class="qa483-meta">'+esc(c.item_name||c.selling_description||x.entity_type||'')+'</div>'+(c.main_article_number?'<div class="qa483-meta">Family '+esc(c.main_article_number)+(c.family_description?' · '+esc(c.family_description):'')+'</div>':'')+'</td><td><div>OH <b>'+esc(c.current_oh??'—')+' '+esc(c.current_oh_uom||'')+'</b></div><div class="qa483-meta">7D velocity '+esc(c.upc_velocity_7d??'—')+' '+esc(c.selling_uom||'')+'/day</div></td><td>'+esc(stateText(x))+'</td><td>'+(x.can_fix?'<span class="qa483-pill med">USER CONFIRM</span>':'<span class="qa483-pill low">VIEW ONLY</span>')+'</td></tr>'}).join('')+'</tbody></table>';
  }
  async function load(){
    const m=ensure();m.classList.add('open');m.querySelector('#ydQa483Body').innerHTML='<div class="qa483-empty">Loading QA…</div>';
    try{
      const [qr,ar]=await Promise.all([fetch('/v1/backoffice/qa-review?limit=300',{cache:'no-store',credentials:'same-origin'}),fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'})]);
      if(!qr.ok)throw new Error('QA review HTTP '+qr.status);
      const qd=await qr.json(),ad=ar.ok?await ar.json():{};
      issues=Array.isArray(qd.issues)?qd.issues:[];
      const b=ad.active_batch||ad.latest_batch||{};currentBatch=b.batch_id??null;
      const counter=document.querySelector('#ydQc');if(counter)counter.textContent=String(issues.length);
      render();
    }catch(e){m.querySelector('#ydQa483Body').innerHTML='<div class="qa483-error">Unable to load QA review: '+esc(e.message||e)+'</div>'}
  }
  function wire(){
    const count=document.querySelector('#ydQc');if(!count)return false;
    const box=count.closest('.topstat');if(!box)return false;
    box.classList.add('ydqa-open');box.setAttribute('role','button');box.setAttribute('tabindex','0');box.setAttribute('title','Open QA Fixes');
    if(box.dataset.qa483Wired)return true;box.dataset.qa483Wired='1';
    box.addEventListener('click',load);
    box.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();load()}});
    return true;
  }
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
  let tries=0,t=setInterval(()=>{tries++;if(wire()||tries>80)clearInterval(t)},100);
})();
</script>
'''


def inject_qa_nav_fix(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)
