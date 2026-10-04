from __future__ import annotations

import api_entry_stable as _prev

app = _prev.app

_original_yipman_html = _prev._api.yipman_html

_PATCH = r'''
<style id="order-v478-css">
@media (min-width:760px){
#ydesk #yd-order .split{grid-template-columns:minmax(0,1fr) minmax(340px,430px)!important;gap:12px!important;align-items:start!important}
#ydesk #yd-order .split>div,#ydesk #yd-order .analysis{min-width:0!important}
#ydesk #yd-order .analysis{overflow:hidden!important}
#ydesk #yd-order .analysis .cardbody,#ydesk #yd-order .analysis .kv,#ydesk #yd-order .analysis .note{overflow-wrap:anywhere!important;word-break:break-word!important}
#ydesk #yd-order table{table-layout:auto!important;max-width:100%!important}
#ydesk #yd-order .tablewrap{max-width:100%!important;overflow-x:auto!important}
#ydesk #yd-order .order-refresh-banner{margin:0 0 8px;padding:8px 10px;border:1px solid #c8ddf5;border-radius:9px;background:#eef6ff;color:#2d5f92;font-size:10px;font-weight:850}
#ydesk #yd-order .order-slow{margin:12px 0;padding:14px;border:1px solid #ecd49b;border-radius:10px;background:#fff8e8;color:#76540a;font-size:11px;line-height:1.45}
#ydesk #yd-order .order-slow button{margin-top:9px;border:0;border-radius:8px;background:#0b72f4;color:#fff;padding:8px 11px;font-size:10px;font-weight:900;cursor:pointer}
#ydesk #yd-order .analysis-loading{padding:18px;color:#6b7d92;font-size:11px;text-align:center}
@media (max-width:1180px){#ydesk #yd-order .split{grid-template-columns:minmax(0,1fr)!important}#ydesk #yd-order .analysis{position:static!important;max-width:none!important}}
}
</style>
<script id="order-v478-js">
(()=>{
 if(!window.matchMedia('(min-width:760px)').matches)return;
 const $=(s,r=document)=>r.querySelector(s);
 const stable={regular:'',promotion:'',history:''};
 let slowTimer=null,lastMode='regular',guard=false;
 const mode=()=>$('#yd-order .tab.active[data-om]')?.dataset.om||lastMode||'regular';
 const isLoading=el=>!!el && /Calculating family order coverage|Loading promotion lists|Loading suggestions|Calculating…|Loading observed delivery days/i.test(el.textContent||'');
 const setAnalysisLoading=(m)=>{const a=$('#ydOrderAnalysis');if(!a)return;a.innerHTML='<div class="card"><div class="analysis-loading">'+(m==='promotion'?'Loading promotion order…':m==='history'?'Loading delivery history…':'Calculating order coverage…')+'</div></div>'};
 function armSlow(m){clearTimeout(slowTimer);slowTimer=setTimeout(()=>{const root=$('#ydOrderMain');if(!root||mode()!==m||!isLoading(root))return;root.innerHTML='<div class="order-slow"><b>Ordering is taking longer than normal.</b><br>The page is still responsive. Retry the current order calculation without changing your dates.<br><button id="order478Retry">RETRY CALCULATION</button></div>';const b=$('#order478Retry');if(b)b.onclick=()=>{$('#yd-order .tab.active[data-om]')?.click()},12000)}
 function onMain(){if(guard)return;const root=$('#ydOrderMain');if(!root)return;const m=mode();lastMode=m;if(isLoading(root)){
   setAnalysisLoading(m);armSlow(m);
   if(stable[m]){guard=true;root.innerHTML='<div class="order-refresh-banner">Refreshing '+(m==='regular'?'regular order coverage':m==='promotion'?'promotion order':'delivery history')+'… showing the last completed result until refresh finishes.</div>'+stable[m];guard=false}
   return;
 }
 clearTimeout(slowTimer);
 const text=(root.textContent||'').trim();
 if(text && !/Request timed out|failed|error/i.test(text) && !root.querySelector('.order-slow')) stable[m]=root.innerHTML;
 }
 function bindTabs(){document.querySelectorAll('#yd-order [data-om]').forEach(b=>{if(b.dataset.v478)return;b.dataset.v478='1';b.addEventListener('click',()=>{lastMode=b.dataset.om||'regular';setAnalysisLoading(lastMode);armSlow(lastMode)},true)})}
 const mo=new MutationObserver(()=>{bindTabs();onMain()});
 mo.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
 bindTabs();onMain();
})();
</script>
'''


def _patched_yipman_html(version: str = "") -> str:
    html = _original_yipman_html(version)
    return html.replace("</body>", _PATCH + "</body>", 1)

_prev._api.yipman_html = _patched_yipman_html
