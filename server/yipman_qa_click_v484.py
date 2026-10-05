from __future__ import annotations

"""Resilient desktop QA Holds navigation.

This patch is deliberately attached at the v481 production layer so it is
present even when later product wrappers are bypassed. It uses document-level
capture delegation, so re-rendering the top bar cannot remove the handler.
Read-only UI only: no QA issue is resolved, waived, or mutated here.
"""

_MARKER = "yipman-qa-click-v484-js"

_PATCH = r'''
<style id="yipman-qa-click-v484-css">
@media (min-width:760px){
  #ydesk .topstat:has(#ydQc){cursor:pointer!important;user-select:none}
  #ydesk .topstat:has(#ydQc):hover{background:rgba(255,255,255,.16)!important;border-color:rgba(255,255,255,.48)!important}
  #ydQa484{position:fixed;inset:0;z-index:5000;display:none;background:rgba(7,24,41,.52);padding:28px;backdrop-filter:blur(2px)}
  #ydQa484.open{display:flex;align-items:flex-start;justify-content:center}
  #ydQa484 .q484-panel{width:min(1450px,calc(100vw - 56px));max-height:calc(100vh - 56px);display:flex;flex-direction:column;background:#f5f8fc;border:1px solid #d8e3ee;border-radius:16px;overflow:hidden;box-shadow:0 24px 70px rgba(5,27,49,.3)}
  #ydQa484 .q484-head{display:flex;align-items:center;gap:10px;padding:14px 16px;background:#fff;border-bottom:1px solid #dce6ef}
  #ydQa484 .q484-head h2{margin:0;font-size:22px;color:#102842}.q484-sub{font-size:10px;color:#6d7f92;margin-top:3px}
  #ydQa484 .q484-close{margin-left:auto;width:36px;height:36px;border:1px solid #d7e1eb;border-radius:9px;background:#fff;color:#52677c;font-size:20px;cursor:pointer}
  #ydQa484 .q484-tools{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:9px 12px;background:#fff;border-bottom:1px solid #e2e9f0}
  #ydQa484 .q484-btn{border:1px solid #dbe5ef;background:#fff;border-radius:8px;padding:7px 10px;font-size:10px;font-weight:850;color:#50667e;cursor:pointer}
  #ydQa484 .q484-btn.on{background:#0b72f4;border-color:#0b72f4;color:#fff}
  #ydQa484 .q484-search{margin-left:auto;min-width:310px;height:34px;border:1px solid #dbe5ef;border-radius:8px;padding:0 10px;font-size:11px}
  #ydQa484 .q484-count{font-size:9px;font-weight:850;color:#6c7d90}
  #ydQa484 .q484-body{overflow:auto;padding:10px 12px 14px;min-height:220px}
  #ydQa484 table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #dfe7ef;table-layout:fixed}
  #ydQa484 th{position:sticky;top:0;background:#f8fbfe;border-bottom:1px solid #dce6ef;padding:8px;text-align:left;font-size:8px;text-transform:uppercase;color:#718197}
  #ydQa484 td{border-bottom:1px solid #edf2f6;padding:9px 8px;vertical-align:top;font-size:10px;color:#273f59;white-space:normal;overflow-wrap:anywhere}
  #ydQa484 th:nth-child(1){width:30%}#ydQa484 th:nth-child(2){width:22%}#ydQa484 th:nth-child(3){width:15%}#ydQa484 th:nth-child(4){width:23%}#ydQa484 th:nth-child(5){width:10%}
  #ydQa484 .q484-code{font-weight:900;color:#173451}.q484-meta{font-size:9px;color:#718197;margin-top:3px;line-height:1.35}.q484-entity{font-weight:900;font-size:11px}
  #ydQa484 .q484-pill{display:inline-flex;border-radius:999px;padding:3px 6px;font-size:8px;font-weight:900}.q484-pill.high{background:#ffe8ec;color:#b93148}.q484-pill.med{background:#fff2d5;color:#8d6100}.q484-pill.low{background:#e9f3ff;color:#1764b8}.q484-pill.current{background:#e9f8ef;color:#17794a;margin-left:4px}
  #ydQa484 .q484-empty{padding:30px;text-align:center;color:#718197;font-size:11px}.q484-error{padding:10px;border:1px solid #f3c9d0;background:#fff0f2;color:#b32e44;border-radius:8px}
}
</style>
<script id="yipman-qa-click-v484-js">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let issues=[],batch=null,mode='ALL',term='';
  const bid=x=>{const v=x?.batch_id??x?.source_batch_id??x?.current?.batch_id;return v==null?null:String(v)};
  const sev=x=>String(x?.severity||'').toUpperCase();
  function modal(){
    let m=document.querySelector('#ydQa484');if(m)return m;
    m=document.createElement('div');m.id='ydQa484';
    m.innerHTML='<section class="q484-panel" role="dialog" aria-modal="true"><div class="q484-head"><div><h2>QA Fixes</h2><div class="q484-sub">Live QA review · read only until an explicit controlled fix is chosen.</div></div><button class="q484-close" aria-label="Close">×</button></div><div class="q484-tools"><button class="q484-btn on" data-mode="ALL">All Open</button><button class="q484-btn" data-mode="CURRENT">Current Batch</button><button class="q484-btn" data-mode="HIGH">High / Critical</button><input class="q484-search" placeholder="Search UPC / Article / Family / issue / item"><span class="q484-count"></span></div><div class="q484-body"><div class="q484-empty">Loading QA…</div></div></section>';
    document.body.appendChild(m);
    m.querySelector('.q484-close').onclick=()=>m.classList.remove('open');
    m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('open')});
    m.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;m.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('on',x===b));render()});
    m.querySelector('.q484-search').addEventListener('input',e=>{term=e.target.value.trim().toLowerCase();render()});
    return m;
  }
  function blob(x){const c=x.current||{};return [x.issue_code,x.issue_summary,x.entity_type,x.entity_key,x.severity,c.item_name,c.selling_description,c.chinese_name,c.main_article_number,c.family_description,c.selling_uom,c.current_cost_per_selling_unit].filter(Boolean).join(' ').toLowerCase()}
  function list(){let a=issues.slice();if(mode==='CURRENT')a=a.filter(x=>batch!=null&&bid(x)===String(batch));if(mode==='HIGH')a=a.filter(x=>['HIGH','CRITICAL'].includes(sev(x)));if(term)a=a.filter(x=>blob(x).includes(term));return a}
  function render(){const m=modal(),a=list();m.querySelector('.q484-count').textContent=a.length+' shown · '+issues.length+' open';const b=m.querySelector('.q484-body');if(!a.length){b.innerHTML='<div class="q484-empty">No QA issues match this filter.</div>';return}b.innerHTML='<table><thead><tr><th>Issue</th><th>Entity</th><th>Activity</th><th>Current State</th><th>Review</th></tr></thead><tbody>'+a.map(x=>{const c=x.current||{},s=sev(x)||'—',cur=batch!=null&&bid(x)===String(batch),cls=['HIGH','CRITICAL'].includes(s)?'high':s==='MEDIUM'?'med':'low',state=[c.selling_uom?'UOM '+c.selling_uom:'',c.current_cost_per_selling_unit!=null?'Cost $'+Number(c.current_cost_per_selling_unit).toFixed(2):'',c.current_oh!=null?'OH '+c.current_oh+(c.current_oh_uom?' '+c.current_oh_uom:''):''].filter(Boolean).join(' · ')||'No current serving state';return '<tr><td><span class="q484-pill '+cls+'">'+esc(s)+'</span>'+(cur?'<span class="q484-pill current">BATCH #'+esc(batch)+'</span>':'')+'<div class="q484-code">'+esc(x.issue_code||'—')+'</div><div class="q484-meta">'+esc(x.issue_summary||'')+'</div></td><td><div class="q484-entity">'+esc(x.entity_key||'—')+'</div><div class="q484-meta">'+esc(c.item_name||c.selling_description||x.entity_type||'')+'</div>'+(c.main_article_number?'<div class="q484-meta">Family '+esc(c.main_article_number)+(c.family_description?' · '+esc(c.family_description):'')+'</div>':'')+'</td><td>OH <b>'+esc(c.current_oh??'—')+' '+esc(c.current_oh_uom||'')+'</b><div class="q484-meta">7D velocity '+esc(c.upc_velocity_7d??'—')+' '+esc(c.selling_uom||'')+'/day</div></td><td>'+esc(state)+'</td><td>'+(x.can_fix?'<span class="q484-pill med">USER CONFIRM</span>':'<span class="q484-pill low">VIEW ONLY</span>')+'</td></tr>'}).join('')+'</tbody></table>'}
  async function openQA(){const m=modal();m.classList.add('open');m.querySelector('.q484-body').innerHTML='<div class="q484-empty">Loading QA…</div>';try{const [q,a]=await Promise.all([fetch('/v1/backoffice/qa-review?limit=300',{cache:'no-store',credentials:'same-origin'}),fetch('/v1/web-upload/active',{cache:'no-store',credentials:'same-origin'})]);if(!q.ok)throw new Error('QA review HTTP '+q.status);const qd=await q.json(),ad=a.ok?await a.json():{};issues=Array.isArray(qd.issues)?qd.issues:[];batch=(ad.active_batch||ad.latest_batch||{}).batch_id??null;const n=document.querySelector('#ydQc');if(n)n.textContent=String(issues.length);render()}catch(e){m.querySelector('.q484-body').innerHTML='<div class="q484-error">Unable to load QA review: '+esc(e.message||e)+'</div>'}}
  function isQaTarget(t){const count=t?.closest?.('#ydQc');if(count)return true;const stat=t?.closest?.('#ydesk .topstat');return !!stat?.querySelector?.('#ydQc')}
  document.addEventListener('click',e=>{if(!isQaTarget(e.target))return;e.preventDefault();e.stopImmediatePropagation();openQA()},true);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.querySelector('#ydQa484')?.classList.remove('open');return}if((e.key==='Enter'||e.key===' ')&&isQaTarget(e.target)){e.preventDefault();e.stopImmediatePropagation();openQA()}},true);
  const decorate=()=>{const n=document.querySelector('#ydQc'),s=n?.closest('.topstat');if(s){s.setAttribute('role','button');s.setAttribute('tabindex','0');s.setAttribute('title','Open QA Fixes')}};
  new MutationObserver(decorate).observe(document.documentElement,{childList:true,subtree:true});decorate();
})();
</script>
'''


def inject_qa_click_fix(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</body>', _PATCH + '</body>', 1)
