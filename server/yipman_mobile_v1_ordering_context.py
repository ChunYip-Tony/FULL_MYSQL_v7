from __future__ import annotations

"""RC-only ordering context polish.

Goals:
- always show the default next-delivery date (fallback D+7)
- let the user adjust Delivery Date and Next Delivery Date from the Order action view
- recalculate ordering live at the viewing moment using the current Effective OH state
- show weekday names beside every visible ordering date
"""

_STYLE = r'''
<style id="yipmanV1OrderingContextStyle">
#orderDateContext{display:none;margin:0 0 10px;padding:10px;border:1px solid #344553;border-radius:15px;background:#111922}
#orderDateContext.show{display:block}
.order-date-title{font-size:9px;color:#8fa2b0;font-weight:1000;letter-spacing:.04em;margin-bottom:7px}
.order-date-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.order-date-field{min-width:0}
.order-date-field label{display:block;font-size:7px;color:#7f8f9d;font-weight:1000;margin:0 0 4px}
.order-date-field input{width:100%;min-height:44px;border:1px solid #3b4d5b;border-radius:11px;background:#0d151d;color:#f2f6f8;padding:8px;font-size:13px;font-weight:900}
.order-date-day{display:block;margin-top:4px;color:#7db8e6;font-size:8px;font-weight:1000}
.order-date-actions{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;margin-top:8px}
.order-date-basis{color:#81919e;font-size:8px;line-height:1.35;font-weight:850}
.order-date-refresh{min-height:40px;border:1px solid #3d7197;border-radius:10px;background:#174c73;color:#fff;padding:0 12px;font-size:9px;font-weight:1000}
.order-date-status{min-height:15px;margin-top:6px;color:#7f909d;font-size:8px;font-weight:850}
.order-date-status.error{color:#ff8d97}
.date-weekday-hint{display:block;margin-top:3px;color:#6faee0;font-size:7px;font-weight:1000}
@media(max-width:390px){.order-date-grid{gap:6px}.order-date-field input{font-size:12px;padding:7px}}
</style>
'''


def polish_ordering_context_html(html: str) -> str:
    if 'yipmanV1OrderingContextStyle' in html:
        return html

    html = html.replace('</head>', _STYLE + '</head>', 1)

    quick_anchor = '<div class="updated" id="updated">Updating…</div></div>\n  <div id="urgentList"'
    quick_insert = '''<div class="updated" id="updated">Updating…</div></div>
  <div id="orderDateContext">
    <div class="order-date-title">ORDERING VIEW · LIVE RECALCULATION</div>
    <div class="order-date-grid">
      <div class="order-date-field"><label>DELIVERY DATE</label><input id="quickOrderDelivery" type="date"><span class="order-date-day" id="quickOrderDeliveryDay"></span></div>
      <div class="order-date-field"><label>NEXT DELIVERY DATE</label><input id="quickOrderNext" type="date"><span class="order-date-day" id="quickOrderNextDay"></span></div>
    </div>
    <div class="order-date-actions"><div class="order-date-basis">Need-to-order and quantity are recalculated from the current Effective OH at the moment you view or change these dates.</div><button type="button" class="order-date-refresh" id="quickOrderRefresh">RECALCULATE NOW</button></div>
    <div class="order-date-status" id="quickOrderStatus"></div>
  </div>
  <div id="urgentList"'''
    if quick_anchor in html:
        html = html.replace(quick_anchor, quick_insert, 1)

    helper_anchor = 'function buildUrgentOrder(rows){'
    helper = r'''
let orderViewDelivery='',orderViewNext='',orderNextManual=false,orderViewBusy=false;
function isoPlusDays(iso,days){
  const m=String(iso||'').match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return'';
  const d=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]));d.setDate(d.getDate()+Number(days||0));
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function dateLabel(v){
  const s=String(v||'').trim(),m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return s||'—';
  const d=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]));
  const wd=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()];
  return wd+' · '+String(Number(m[2]))+'/'+String(Number(m[3]))+'/'+m[1];
}
window.yipmanDateLabel=dateLabel;
function syncOrderDateDayHints(){
  const d=document.getElementById('quickOrderDelivery'),n=document.getElementById('quickOrderNext');
  const dd=document.getElementById('quickOrderDeliveryDay'),nd=document.getElementById('quickOrderNextDay');
  if(dd)dd.textContent=d?.value?dateLabel(d.value).split(' · ')[0]:'';
  if(nd)nd.textContent=n?.value?dateLabel(n.value).split(' · ')[0]:'';
}
function decorateDateInputs(root=document){
  root.querySelectorAll('input[type="date"]').forEach(inp=>{
    if(inp.dataset.weekdayDecorated==='1')return;inp.dataset.weekdayDecorated='1';
    const hint=document.createElement('span');hint.className='date-weekday-hint';
    const update=()=>{hint.textContent=inp.value?dateLabel(inp.value).split(' · ')[0]:''};
    inp.insertAdjacentElement('afterend',hint);inp.addEventListener('change',update);update();
  });
}
function setOrderStatus(msg,isError=false){const el=document.getElementById('quickOrderStatus');if(!el)return;el.textContent=msg||'';el.classList.toggle('error',!!isError)}
function syncOrderContextVisibility(){
  const box=document.getElementById('orderDateContext');if(!box)return;
  box.classList.toggle('show',uf==='order');
  if(uf==='order'){
    const d=document.getElementById('quickOrderDelivery'),n=document.getElementById('quickOrderNext');
    if(d&&!d.value&&orderViewDelivery)d.value=orderViewDelivery;
    if(n&&!n.value&&orderViewNext)n.value=orderViewNext;
    syncOrderDateDayHints();decorateDateInputs(box);
  }
}
async function liveOrderRows(d,n){
  if(!d)return[];
  const url='/app/yipman-v1-rc/api/ordering-review-live?category=ALL&delivery_date='+encodeURIComponent(d)+(n?'&next_delivery_date='+encodeURIComponent(n):'')+'&_ts='+Date.now();
  const data=await api(url);
  return data?.rows||[];
}
async function refreshOrderAtViewingMoment(){
  if(orderViewBusy)return;orderViewBusy=true;setOrderStatus('Recalculating from current Effective OH…');
  try{
    const d=document.getElementById('quickOrderDelivery')?.value||orderViewDelivery;
    let n=document.getElementById('quickOrderNext')?.value||orderViewNext||isoPlusDays(d,7);
    if(!d)throw new Error('Choose a Delivery Date.');
    if(!n)n=isoPlusDays(d,7);
    if(n<=d)throw new Error('Next Delivery Date must be after Delivery Date.');
    orderViewDelivery=d;orderViewNext=n;
    const di=document.getElementById('deliveryDate'),ni=document.getElementById('nextDeliveryDate');if(di)di.value=d;if(ni)ni.value=n;
    const qn=document.getElementById('quickOrderNext');if(qn)qn.value=n;
    syncOrderDateDayHints();
    orderRows=await liveOrderRows(d,n);
    urgent=[...urgent.filter(x=>x.type!=='order'),...buildUrgentOrder(orderRows)].filter(x=>!isIgnored(x.key)).sort((a,b)=>b.score-a.score);
    renderUrgent();
    setOrderStatus('Live recalculation complete · '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}));
    const u=document.getElementById('updated');if(u)u.textContent='Updated '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});
  }catch(e){setOrderStatus(e.message||String(e),true)}finally{orderViewBusy=false}
}
'''
    if helper_anchor in html:
        html = html.replace(helper_anchor, helper + '\nfunction buildUrgentOrder(rows){', 1)

    # Ensure NEXT has a default and every visible order date carries weekday text.
    html = html.replace("['DELIVERY',r?.delivery_date||r?.selected_delivery_date||'—'],['NEXT',r?.next_delivery_date||'—']",
                        "['DELIVERY',dateLabel(r?.delivery_date||r?.selected_delivery_date||orderViewDelivery)],['NEXT',dateLabel(r?.next_delivery_date||r?.selected_next_delivery_date||orderViewNext||isoPlusDays(r?.delivery_date||r?.selected_delivery_date||orderViewDelivery,7))]", 1)

    old_get = "async function getOrdering(){const cal=await api('/v1/yipman/ordering-calendar?lookback_days=180').catch(()=>null);const d=String(cal?.default_delivery_date||''),n=String(cal?.default_next_delivery_date||'');if(d){$('#deliveryDate').value=d;$('#nextDeliveryDate').value=n||'';const data=await api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(d)+(n?'&next_delivery_date='+encodeURIComponent(n):'')).catch(()=>null);return data?.rows||[]}return[]}"
    new_get = "async function getOrdering(){const cal=await api('/v1/yipman/ordering-calendar?lookback_days=180&_ts='+Date.now()).catch(()=>null);const d=String(cal?.default_delivery_date||''),n=String(cal?.default_next_delivery_date||isoPlusDays(d,7)||'');orderViewDelivery=d;orderViewNext=n;if(d){$('#deliveryDate').value=d;$('#nextDeliveryDate').value=n;const qd=document.getElementById('quickOrderDelivery'),qn=document.getElementById('quickOrderNext');if(qd)qd.value=d;if(qn)qn.value=n;syncOrderDateDayHints();return await liveOrderRows(d,n).catch(()=>[])}return[]}"
    if old_get in html:
        html = html.replace(old_get, new_get, 1)

    # Render context on every urgent re-render.
    html = html.replace('function renderUrgent(){const counts=', 'function renderUrgent(){syncOrderContextVisibility();const counts=', 1)

    old_filter = "$$('[data-uf]').forEach(b=>b.onclick=()=>{uf=b.dataset.uf;renderUrgent()});"
    new_filter = r"""$$('[data-uf]').forEach(b=>b.onclick=async()=>{uf=b.dataset.uf;renderUrgent();if(uf==='order')await refreshOrderAtViewingMoment()});
const qod=document.getElementById('quickOrderDelivery'),qon=document.getElementById('quickOrderNext'),qor=document.getElementById('quickOrderRefresh');
qod?.addEventListener('change',async()=>{const oldNext=orderViewNext||isoPlusDays(orderViewDelivery,7);orderViewDelivery=qod.value;if(!orderNextManual||qon?.value===oldNext){orderViewNext=isoPlusDays(orderViewDelivery,7);if(qon)qon.value=orderViewNext}syncOrderDateDayHints();await refreshOrderAtViewingMoment()});
qon?.addEventListener('change',async()=>{orderNextManual=true;orderViewNext=qon.value;syncOrderDateDayHints();await refreshOrderAtViewingMoment()});
qor?.addEventListener('click',refreshOrderAtViewingMoment);
setTimeout(()=>{decorateDateInputs(document);syncOrderDateDayHints()},0);"""
    if old_filter in html:
        html = html.replace(old_filter, new_filter, 1)

    old_load = "async function loadOrdering(){const d=$('#deliveryDate').value,n=$('#nextDeliveryDate').value;if(!d){await getOrdering();return loadOrdering()}$('#regularResults').innerHTML='<div class=\"loading\">Loading order suggestions…</div>';try{const data=await api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(d)+(n?'&next_delivery_date='+encodeURIComponent(n):''));orderRows=data.rows||[];renderOrdering()}catch(e){$('#regularResults').innerHTML='<div class=\"empty\">Ordering unavailable · '+esc(e.message)+'</div>'}}"
    new_load = "async function loadOrdering(){const d=$('#deliveryDate').value,n=$('#nextDeliveryDate').value||isoPlusDays(d,7);if(!d){await getOrdering();return loadOrdering()}if(!$('#nextDeliveryDate').value)$('#nextDeliveryDate').value=n;orderViewDelivery=d;orderViewNext=n;decorateDateInputs(document);$('#regularResults').innerHTML='<div class=\"loading\">Recalculating from current Effective OH…</div>';try{orderRows=await liveOrderRows(d,n);renderOrdering()}catch(e){$('#regularResults').innerHTML='<div class=\"empty\">Ordering unavailable · '+esc(e.message)+'</div>'}}"
    if old_load in html:
        html = html.replace(old_load, new_load, 1)

    html = html.replace("esc(r?.delivery_date||$('#deliveryDate').value)", "esc(dateLabel(r?.delivery_date||r?.selected_delivery_date||$('#deliveryDate').value))")
    html = html.replace("esc(r?.next_delivery_date||$('#nextDeliveryDate').value||'—')", "esc(dateLabel(r?.next_delivery_date||r?.selected_next_delivery_date||$('#nextDeliveryDate').value||isoPlusDays($('#deliveryDate').value,7)))")

    # Detail page dates use the same weekday format.
    html = html.replace("metric('DELIVERY',delivery),", "metric('DELIVERY',window.yipmanDateLabel?window.yipmanDateLabel(delivery):delivery),")
    html = html.replace("metric('NEXT DELIVERY',next),", "metric('NEXT DELIVERY',window.yipmanDateLabel?window.yipmanDateLabel(next):next),")
    html = html.replace("const lastText=last?.date ? `${last.date}${", "const lastText=last?.date ? `${window.yipmanDateLabel?window.yipmanDateLabel(last.date):last.date}${")

    return html
