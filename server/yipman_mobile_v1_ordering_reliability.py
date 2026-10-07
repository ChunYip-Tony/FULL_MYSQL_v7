from __future__ import annotations

"""RC-only ordering reliability + weekday presentation patch.

Goals:
- Regular Ordering must never become blank just because the uncached live refresh times out.
- Use the normal date-scoped ordering review immediately, then opportunistically replace it
  with the uncached current-view calculation when that finishes.
- True Stock writes already invalidate ordering caches, so the fast path remains consistent
  with a newly saved Effective OH while avoiding an empty mobile screen.
- Every editable date shows a human weekday label (Mon/Tue/...) alongside the date.
"""

_STYLE = r'''
<style id="yipmanV1OrderingReliabilityStyle">
.date-weekday-hint{
  display:block!important;
  margin-top:6px!important;
  color:#78b9ec!important;
  font-size:10px!important;
  line-height:1!important;
  font-weight:1000!important;
  letter-spacing:.04em!important;
}
.ordering-fallback-note{
  margin:8px 0 10px;padding:9px 11px;border:1px solid #5f512f;border-radius:11px;
  background:#282216;color:#e9c975;font-size:9px;font-weight:900;line-height:1.35
}
.order-date-field label,.field label{display:flex!important;align-items:center;gap:6px;flex-wrap:wrap}
.weekday-chip{
  display:inline-flex;align-items:center;min-height:19px;padding:2px 7px;border-radius:999px;
  border:1px solid #315f83;background:#14283a;color:#8fc9f2;font-size:8px;font-weight:1000
}
</style>
'''


def polish_ordering_reliability_html(html: str) -> str:
    marker = "yipmanV1OrderingReliability"
    if marker in html:
        return html

    html = html.replace('</head>', _STYLE + f'<meta name="{marker}" content="1">\n</head>', 1)

    # Add a fast date-scoped fallback that uses the established cached ordering API.
    anchor = "async function refreshOrderAtViewingMoment(){"
    helper = r'''async function cachedOrderRows(d,n){
  if(!d)return[];
  const url='/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(d)+(n?'&next_delivery_date='+encodeURIComponent(n):'')+'&_ts='+Date.now();
  const data=await api(url);
  return data?.rows||[];
}
function paintOrderRows(rows){
  orderRows=Array.isArray(rows)?rows:[];
  if(document.getElementById('regularResults'))renderOrdering();
  urgent=[...urgent.filter(x=>x.type!=='order'),...buildUrgentOrder(orderRows)].filter(x=>!isIgnored(x.key)).sort((a,b)=>b.score-a.score);
  renderUrgent();
}
function showOrderingFallbackNote(msg){
  const root=document.getElementById('regularResults');if(!root)return;
  let note=document.getElementById('orderingFallbackNote');
  if(!note){note=document.createElement('div');note.id='orderingFallbackNote';note.className='ordering-fallback-note';root.insertAdjacentElement('beforebegin',note)}
  note.textContent=msg||'';note.style.display=msg?'block':'none';
}
async function refreshOrderAtViewingMoment(){'''
    if anchor in html:
        html = html.replace(anchor, helper, 1)

    old_refresh = r'''async function refreshOrderAtViewingMoment(){
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
}'''
    new_refresh = r'''async function refreshOrderAtViewingMoment(){
  if(orderViewBusy)return;orderViewBusy=true;setOrderStatus('Updating current ordering…');
  try{
    const d=document.getElementById('quickOrderDelivery')?.value||orderViewDelivery;
    let n=document.getElementById('quickOrderNext')?.value||orderViewNext||isoPlusDays(d,7);
    if(!d)throw new Error('Choose a Delivery Date.');
    if(!n)n=isoPlusDays(d,7);
    if(n<=d)throw new Error('Next Delivery Date must be after Delivery Date.');
    orderViewDelivery=d;orderViewNext=n;
    const di=document.getElementById('deliveryDate'),ni=document.getElementById('nextDeliveryDate');if(di)di.value=d;if(ni)ni.value=n;
    const qn=document.getElementById('quickOrderNext');if(qn)qn.value=n;
    syncOrderDateDayHints();syncAllOrderingWeekdays();

    // Fast usable result first. This cache is invalidated after True Stock saves.
    let fast=[];
    try{fast=await cachedOrderRows(d,n);paintOrderRows(fast);setOrderStatus('Current results shown · refreshing live Effective OH…')}catch(_){}

    // Then replace with uncached viewing-moment results if the heavier calculation finishes.
    try{
      const live=await liveOrderRows(d,n);paintOrderRows(live);showOrderingFallbackNote('');
      setOrderStatus('Live recalculation complete · '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}));
    }catch(e){
      if(fast.length){
        setOrderStatus('Showing current available calculation · live refresh timed out.',false);
      }else{
        throw e;
      }
    }
    const u=document.getElementById('updated');if(u)u.textContent='Updated '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});
  }catch(e){setOrderStatus(e.message||String(e),true)}finally{orderViewBusy=false}
}'''
    if old_refresh in html:
        html = html.replace(old_refresh, new_refresh, 1)

    # Regular Ordering: paint the fast result first, then refresh live without ever blanking the page.
    old_load = r'''async function loadOrdering(){const d=$('#deliveryDate').value,n=$('#nextDeliveryDate').value||isoPlusDays(d,7);if(!d){await getOrdering();return loadOrdering()}if(!$('#nextDeliveryDate').value)$('#nextDeliveryDate').value=n;orderViewDelivery=d;orderViewNext=n;decorateDateInputs(document);$('#regularResults').innerHTML='<div class="loading">Recalculating from current Effective OH…</div>';try{orderRows=await liveOrderRows(d,n);renderOrdering()}catch(e){$('#regularResults').innerHTML='<div class="empty">Ordering unavailable · '+esc(e.message)+'</div>'}}'''
    new_load = r'''async function loadOrdering(){
  const d=$('#deliveryDate').value,n=$('#nextDeliveryDate').value||isoPlusDays(d,7);
  if(!d){await getOrdering();return loadOrdering()}
  if(!$('#nextDeliveryDate').value)$('#nextDeliveryDate').value=n;
  orderViewDelivery=d;orderViewNext=n;decorateDateInputs(document);syncAllOrderingWeekdays();
  $('#regularResults').innerHTML='<div class="loading">Loading current ordering…</div>';
  let fast=[];
  try{
    fast=await cachedOrderRows(d,n);orderRows=fast;renderOrdering();showOrderingFallbackNote('');
  }catch(e){
    $('#regularResults').innerHTML='<div class="empty">Unable to load ordering · '+esc(e.message)+'</div>';return;
  }
  try{
    const live=await liveOrderRows(d,n);orderRows=live;renderOrdering();showOrderingFallbackNote('');
  }catch(e){
    if(fast.length){
      showOrderingFallbackNote('Showing the latest available calculation for these dates. Live Effective OH refresh timed out; the list remains usable.');
    }
  }
}'''
    if old_load in html:
        html = html.replace(old_load, new_load, 1)

    # Make weekday text explicit and robust instead of relying on the browser's native date rendering.
    weekday_anchor = "function decorateDateInputs(root=document){"
    weekday_helper = r'''function syncAllOrderingWeekdays(){
  document.querySelectorAll('input[type="date"]').forEach(inp=>{
    const value=inp.value||'';
    const full=value?dateLabel(value):'';
    const wd=full&&full.includes(' · ')?full.split(' · ')[0]:'';
    let hint=inp.parentElement?.querySelector(':scope > .date-weekday-hint');
    if(!hint){hint=document.createElement('span');hint.className='date-weekday-hint';inp.insertAdjacentElement('afterend',hint)}
    hint.textContent=full;
    const wrap=inp.closest('.field,.order-date-field');
    const label=wrap?.querySelector('label');
    if(label){
      if(!label.dataset.baseDateLabel)label.dataset.baseDateLabel=label.textContent.trim().replace(/\s*·\s*(SUN|MON|TUE|WED|THU|FRI|SAT)$/i,'');
      label.innerHTML='<span>'+label.dataset.baseDateLabel+'</span>'+(wd?'<span class="weekday-chip">'+wd+'</span>':'');
    }
  });
  const qd=document.getElementById('quickOrderDeliveryDay'),qn=document.getElementById('quickOrderNextDay');
  const qdi=document.getElementById('quickOrderDelivery'),qni=document.getElementById('quickOrderNext');
  if(qd)qd.textContent=qdi?.value?dateLabel(qdi.value):'';
  if(qn)qn.textContent=qni?.value?dateLabel(qni.value):'';
}
function decorateDateInputs(root=document){'''
    if weekday_anchor in html:
        html = html.replace(weekday_anchor, weekday_helper, 1)

    # Existing decorateDateInputs update should now show full weekday + date in the helper line.
    html = html.replace("const update=()=>{hint.textContent=inp.value?dateLabel(inp.value).split(' · ')[0]:''};",
                        "const update=()=>{hint.textContent=inp.value?dateLabel(inp.value):'';syncAllOrderingWeekdays()};")
    html = html.replace("if(dd)dd.textContent=d?.value?dateLabel(d.value).split(' · ')[0]:'';",
                        "if(dd)dd.textContent=d?.value?dateLabel(d.value):'';")
    html = html.replace("if(nd)nd.textContent=n?.value?dateLabel(n.value).split(' · ')[0]:'';",
                        "if(nd)nd.textContent=n?.value?dateLabel(n.value):'';")

    # Re-run after navigation/rendering so native date controls always get their weekday companion.
    html = html.replace("setTimeout(()=>{decorateDateInputs(document);syncOrderDateDayHints()},0);",
                        "setTimeout(()=>{decorateDateInputs(document);syncOrderDateDayHints();syncAllOrderingWeekdays()},0);")
    html = html.replace("if(id==='regular')loadOrdering();", "if(id==='regular'){loadOrdering();setTimeout(syncAllOrderingWeekdays,0);}")

    return html
