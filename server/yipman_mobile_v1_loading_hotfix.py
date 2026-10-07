from __future__ import annotations

"""Keep the Quick/Urgent home responsive while live Ordering refreshes in background.

The viewing-moment Ordering endpoint is intentionally uncached and can be expensive.
It must not block initial app startup. Initial load uses the normal cached ordering
review for fast paint; Order view/date edits still run the live uncached recalculation.
"""


def polish_loading_html(html: str) -> str:
    marker = "yipmanV1NonBlockingOrderingLoad"
    if marker in html:
        return html

    old_live = """async function liveOrderRows(d,n){
  if(!d)return[];
  const url='/app/yipman-v1-rc/api/ordering-review-live?category=ALL&delivery_date='+encodeURIComponent(d)+(n?'&next_delivery_date='+encodeURIComponent(n):'')+'&_ts='+Date.now();
  const data=await api(url);
  return data?.rows||[];
}"""
    new_live = """async function liveOrderRows(d,n){
  if(!d)return[];
  const url='/app/yipman-v1-rc/api/ordering-review-live?category=ALL&delivery_date='+encodeURIComponent(d)+(n?'&next_delivery_date='+encodeURIComponent(n):'')+'&_ts='+Date.now();
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),12000);
  try{
    const r=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:controller.signal});
    const text=await r.text();
    let data={};try{data=text?JSON.parse(text):{}}catch(_){throw new Error('Invalid live ordering response')}
    if(!r.ok)throw new Error(data?.reason||data?.detail||('HTTP '+r.status));
    return data?.rows||[];
  }catch(e){
    if(e?.name==='AbortError')throw new Error('Live ordering refresh timed out; keeping the latest available results.');
    throw e;
  }finally{clearTimeout(timer)}
}"""
    html = html.replace(old_live, new_live, 1)

    old_get = """async function getOrdering(){const cal=await api('/v1/yipman/ordering-calendar?lookback_days=180&_ts='+Date.now()).catch(()=>null);const d=String(cal?.default_delivery_date||''),n=String(cal?.default_next_delivery_date||isoPlusDays(d,7)||'');orderViewDelivery=d;orderViewNext=n;if(d){$('#deliveryDate').value=d;$('#nextDeliveryDate').value=n;const qd=document.getElementById('quickOrderDelivery'),qn=document.getElementById('quickOrderNext');if(qd)qd.value=d;if(qn)qn.value=n;syncOrderDateDayHints();return await liveOrderRows(d,n).catch(()=>[])}return[]}"""
    new_get = """async function getOrdering(){const cal=await api('/v1/yipman/ordering-calendar?lookback_days=180&_ts='+Date.now()).catch(()=>null);const d=String(cal?.default_delivery_date||''),n=String(cal?.default_next_delivery_date||isoPlusDays(d,7)||'');orderViewDelivery=d;orderViewNext=n;if(d){$('#deliveryDate').value=d;$('#nextDeliveryDate').value=n;const qd=document.getElementById('quickOrderDelivery'),qn=document.getElementById('quickOrderNext');if(qd)qd.value=d;if(qn)qn.value=n;syncOrderDateDayHints();const data=await api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(d)+(n?'&next_delivery_date='+encodeURIComponent(n):'')).catch(()=>null);return data?.rows||[]}return[]}"""
    html = html.replace(old_get, new_get, 1)

    old_load = """urgent=[...buildUrgentPrice(priceRows),...buildUrgentOrder(orderRows)].filter(x=>!isIgnored(x.key)).sort((a,b)=>b.score-a.score);renderUrgent();$('#updated').textContent='Updated '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'})"""
    new_load = """urgent=[...buildUrgentPrice(priceRows),...buildUrgentOrder(orderRows)].filter(x=>!isIgnored(x.key)).sort((a,b)=>b.score-a.score);renderUrgent();$('#updated').textContent='Updated '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});setTimeout(()=>refreshOrderAtViewingMoment().catch(()=>{}),50)"""
    html = html.replace(old_load, new_load, 1)

    html = html.replace('</head>', f'<meta name="{marker}" content="1">\n</head>', 1)
    return html
