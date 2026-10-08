from __future__ import annotations

"""Last-resort Family ORDER detail renderer for Mobile V1 RC.

The generic interaction layer always opens a UPC-shaped shell first.  Earlier
Family decorators could miss a later render because the same detail body is
reused.  This final layer watches the *rendered* detail itself and, whenever it
sees an ORDER/NO ORDER decision with no selling UPC, force-converts it to a
Family ordering view.  It does not depend on click-source state.
"""

_STYLE = r'''
<style id="yipmanV1ForceOrderDetailStyle">
.v1-force-order-block{margin:8px 0;padding:11px;border:1px solid #304452;border-radius:14px;background:#101a22}
.v1-force-order-title{font-size:11px;font-weight:1000;color:#90a6b6;letter-spacing:.05em;margin-bottom:8px}
.v1-force-order-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
.v1-force-order-cell{border:1px solid #2b3d49;border-radius:11px;background:#0d161e;padding:9px;min-width:0}
.v1-force-order-cell b{display:block;font-size:9px;color:#7f94a4;font-weight:1000}
.v1-force-order-cell strong{display:block;margin-top:3px;font-size:16px;line-height:1.15;color:#f2f6f8;font-weight:1000;overflow-wrap:anywhere}
.v1-force-order-cell span{display:block;margin-top:3px;font-size:11px;line-height:1.3;color:#93a6b4}
.v1-force-receiving{font-size:21px!important;color:#dff1ff!important}
.v1-force-last-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.v1-force-last-date,.v1-force-last-qty{font-size:18px;font-weight:1000}.v1-force-last-qty{color:#88c8f3}
.v1-force-last-meta{margin-top:7px;font-size:12px;line-height:1.45;color:#a9b8c2}
.v1-force-history{margin-top:8px;border:1px solid #304452;border-radius:13px;background:#0d171f;overflow:hidden}
.v1-force-history>summary{list-style:none;padding:12px;cursor:pointer;font-size:14px;font-weight:1000;color:#edf3f7;display:flex;justify-content:space-between;align-items:center}
.v1-force-history>summary::-webkit-details-marker{display:none}.v1-force-history>summary::after{content:'›';font-size:22px;color:#75b8e8;transform:rotate(90deg)}
.v1-force-history[open]>summary::after{transform:rotate(-90deg)}
.v1-force-history-body{border-top:1px solid #283a47;padding:4px 10px 9px}
.v1-force-receipt-day{padding:9px 1px;border-bottom:1px solid #22323e}.v1-force-receipt-day:last-child{border-bottom:0}
.v1-force-receipt-head{display:flex;justify-content:space-between;gap:8px;font-size:13px;font-weight:1000;color:#eef4f7}.v1-force-receipt-head span:last-child{color:#8dc8ef}
.v1-force-receipt-event{margin-top:5px;color:#98aab7;font-size:11px;line-height:1.4}.v1-force-receipt-event b{color:#d6e7f3;font-size:12px}
.v1-force-loading{padding:10px;color:#8da0ae;font-size:12px;font-weight:850}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1ForceOrderDetailScript">
(()=>{
  'use strict';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=(v,d=1)=>{const x=num(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:d})};
  const text=(el,sel)=>String(el?.querySelector(sel)?.textContent||'').trim();
  const value=(r,keys)=>{for(const k of keys){if(r&&r[k]!==null&&r[k]!==undefined&&r[k]!=='')return r[k]}return null};
  const famOf=r=>String(r?.family_article_number||r?.family_article||r?.main_article_number||r?.family_id||'');
  const artOf=r=>String(r?.receiving_article||r?.receiving_article_number||r?.article_number||r?.recommended_receiving_article||r?.family_article_number||r?.family_article||'');
  const nameOf=r=>String(r?.family_description||r?.family_name||r?.description||r?.name||'');
  let runningKey='',generation=0;

  function dateLabel(v){
    if(!v)return'—';
    if(typeof window.yipmanDateLabel==='function')return window.yipmanDateLabel(String(v));
    const s=String(v),m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return s;
    const d=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]));
    return ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()]+' · '+Number(m[2])+'/'+Number(m[3])+'/'+m[1];
  }
  function currentRow(family){
    try{
      if(typeof orderRows==='undefined'||!Array.isArray(orderRows))return null;
      return orderRows.find(r=>famOf(r)===String(family))||null;
    }catch(_){return null}
  }
  function isFamilyOrder(body){
    const decision=text(body,'.v1-detail-decision strong').toUpperCase();
    if(!/^(ORDER|NO ORDER)\b/.test(decision))return false;
    const cells=[...body.querySelectorAll('.v1-detail-id>div')];
    if(cells.length<3)return false;
    const upc=String(cells[1]?.querySelector('span')?.textContent||'').trim();
    return !upc||upc==='—'||upc==='-';
  }
  function cell(label,val,sub='',cls=''){
    if(val===null||val===undefined||val===''||val==='—')return'';
    return `<div class="v1-force-order-cell"><b>${esc(label)}</b><strong class="${cls}">${esc(val)}</strong>${sub?`<span>${esc(sub)}</span>`:''}</div>`;
  }
  function recoverFamily(body){
    const cells=[...body.querySelectorAll('.v1-detail-id span')];
    return String(cells[0]?.textContent||'').trim();
  }
  function recoverArticle(body,row,family){
    const fromRow=artOf(row);if(fromRow)return fromRow;
    const cells=[...body.querySelectorAll('.v1-detail-id span')];
    const raw=String(cells[2]?.textContent||'').trim();
    return raw&&raw!=='—'?raw:String(family||'');
  }
  function patchIdentity(body,family,article){
    const cells=[...body.querySelectorAll('.v1-detail-id>div')];
    if(cells[0])cells[0].innerHTML=`<b>FAMILY</b><span>${esc(family||'—')}</span>`;
    if(cells[1])cells[1].innerHTML='<b>ORDER LEVEL</b><span>FAMILY</span>';
    if(cells[2])cells[2].innerHTML=`<b>RECOMMENDED RECEIVING</b><span class="v1-force-receiving">${esc(article||'—')}</span>`;
  }
  function localEvidence(row,article){
    const uom=String(value(row,['suggested_delivery_uom','order_uom','effective_oh_uom','family_group_movement_uom'])||'').toUpperCase();
    const familyMvt=value(row,['family_group_movement_7d','family_movement_7d','movement_7d']);
    const avg=value(row,['family_group_avg_qty_day','family_avg_qty_day','avg_daily_movement']);
    const delivery=value(row,['selected_delivery_date','delivery_date']);
    const next=value(row,['selected_next_delivery_date','next_delivery_date']);
    const projected=value(row,['projected_oh_at_delivery','projected_oh_at_expected_delivery','usable_oh_at_delivery']);
    const coverage=value(row,['forecast_coverage_usage','forecast_requested_coverage_usage','coverage_usage']);
    const before=value(row,['forecast_usage_before_expected_delivery','forecast_before_delivery_usage','before_delivery_usage']);
    const suggested=value(row,['suggested_delivery_qty','suggested_order_qty']);
    const receivingName=value(row,['receiving_article_name','article_name','article_description','receiving_description']);
    const pack=value(row,['pack_size','pack_qty','order_pack_size','case_pack','pack']);
    const packUom=value(row,['pack_uom','order_pack_uom']);
    return `<section class="v1-force-order-block" id="v1ForceOrderEvidence"><div class="v1-force-order-title">ORDERING EVIDENCE</div><div class="v1-force-order-grid">
      ${cell('FAMILY 7D MVT',familyMvt!==null&&familyMvt!==undefined?fmt(familyMvt)+' '+uom:'—')}
      ${cell('AVG / DAY',avg!==null&&avg!==undefined?fmt(avg)+' '+uom+'/day':'—')}
      ${cell('DELIVERY',delivery?dateLabel(delivery):'—')}
      ${cell('NEXT DELIVERY',next?dateLabel(next):'—')}
      ${cell('PROJECTED OH @ DELIVERY',projected!==null&&projected!==undefined?fmt(projected)+' '+uom:'—')}
      ${cell('COVERAGE USE',coverage!==null&&coverage!==undefined?fmt(coverage)+' '+uom:'—')}
      ${cell('USE BEFORE DELIVERY',before!==null&&before!==undefined?fmt(before)+' '+uom:'—')}
      ${cell('SUGGESTED ORDER',suggested!==null&&suggested!==undefined?fmt(suggested)+' '+uom:'—')}
      ${cell('RECEIVING ARTICLE',article||'—',receivingName||'','v1-force-receiving')}
      ${cell('PACK',pack!==null&&pack!==undefined?fmt(pack)+(packUom?' '+packUom:''):'—')}
    </div></section>`;
  }
  function receiptMeta(events){
    const ev=Array.isArray(events)&&events.length?events[0]:null;if(!ev)return'';
    const bits=[];if(ev.article_number)bits.push('Article '+ev.article_number);if(ev.gr_number)bits.push('GR '+ev.gr_number);if(ev.purchase_order)bits.push('PO '+ev.purchase_order);if(ev.vendor_code)bits.push('Vendor '+ev.vendor_code);
    return bits.join(' · ');
  }
  function lastReceiptBlock(day){
    if(!day)return `<section class="v1-force-order-block"><div class="v1-force-order-title">LAST RECEIPT</div><div class="v1-force-loading">No recent positive canonical receipt found.</div></section>`;
    const qty=day.quantity!==null&&day.quantity!==undefined?fmt(day.quantity)+' '+String(day.uom||''):'—';
    const meta=receiptMeta(day.events);
    return `<section class="v1-force-order-block" id="v1ForceLastReceipt"><div class="v1-force-order-title">LAST RECEIPT</div><div class="v1-force-last-head"><div class="v1-force-last-date">${esc(dateLabel(day.date))}</div><div class="v1-force-last-qty">${esc(qty)}</div></div>${meta?`<div class="v1-force-last-meta">${esc(meta)}</div>`:''}</section>`;
  }
  function historyBlock(family){
    return `<details class="v1-force-history" data-family="${esc(family)}"><summary>Recent Receipt History <span style="font-size:11px;color:#8094a3">tap to view</span></summary><div class="v1-force-history-body"><div class="v1-force-loading">Open to view recent receipts.</div></div></details>`;
  }
  function historyHtml(data){
    const days=Array.isArray(data?.days)?data.days:[];if(!days.length)return'<div class="v1-force-loading">No recent positive canonical receipts found.</div>';
    return days.map(day=>{const qty=day.quantity!==null&&day.quantity!==undefined?fmt(day.quantity)+' '+String(day.uom||''):'—';const events=Array.isArray(day.events)?day.events:[];return `<div class="v1-force-receipt-day"><div class="v1-force-receipt-head"><span>${esc(dateLabel(day.date))}</span><span>${esc(qty)}</span></div>${events.map(ev=>{const bits=[];if(ev.receipt_quantity!==null&&ev.receipt_quantity!==undefined)bits.push(fmt(ev.receipt_quantity)+' '+String(ev.receipt_uom||''));if(ev.gr_number)bits.push('GR '+ev.gr_number);if(ev.purchase_order)bits.push('PO '+ev.purchase_order);if(ev.vendor_code)bits.push('Vendor '+ev.vendor_code);return `<div class="v1-force-receipt-event"><b>Article ${esc(ev.article_number||'—')}</b>${bits.length?' · '+esc(bits.join(' · ')):''}</div>`}).join('')}</div>`}).join('');
  }
  async function fetchReceipts(family){
    const r=await fetch('/app/yipman-v1-rc/api/family-receipts?family='+encodeURIComponent(family)+'&limit_days=12&_ts='+Date.now(),{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw new Error('Receipt history unavailable');return r.json();
  }
  async function force(){
    const overlay=document.getElementById('v1DetailOverlay'),body=document.getElementById('v1DetailBody');
    if(!overlay?.classList.contains('open')||!body||!isFamilyOrder(body))return;
    const family=recoverFamily(body);if(!family)return;
    const row=currentRow(family),article=recoverArticle(body,row,family);const key=family+'|'+article+'|'+text(body,'.v1-detail-decision strong');
    if(body.dataset.forceOrderKey===key&&body.querySelector('.v1-force-order-root'))return;
    const gen=++generation;runningKey=key;body.dataset.forceOrderKey=key;body.dataset.orderFamilyPolished='1';
    patchIdentity(body,family,article);
    const genericMetrics=body.querySelector('.v1-detail-metrics');if(genericMetrics)genericMetrics.remove();
    const genericNote=body.querySelector('.v1-detail-note');if(genericNote)genericNote.remove();
    body.querySelectorAll('.v1-order-section,.v1-receipt-history,.v1-force-order-root').forEach(el=>el.remove());
    const root=document.createElement('div');root.className='v1-force-order-root';root.innerHTML=localEvidence(row,article)+`<section class="v1-force-order-block" id="v1ForceLastReceipt"><div class="v1-force-order-title">LAST RECEIPT</div><div class="v1-force-loading">Loading last receipt…</div></section>`+historyBlock(family);body.appendChild(root);
    try{const data=await fetchReceipts(family);if(gen!==generation||!overlay.classList.contains('open')||body.dataset.forceOrderKey!==key)return;const last=root.querySelector('#v1ForceLastReceipt');if(last){const tmp=document.createElement('div');tmp.innerHTML=lastReceiptBlock((data.days||[])[0]||null);last.replaceWith(tmp.firstElementChild)}root.dataset.receipts=JSON.stringify(data)}catch(e){const last=root.querySelector('#v1ForceLastReceipt .v1-force-loading');if(last)last.textContent='Receipt data unavailable · '+(e.message||String(e))}
  }
  document.addEventListener('toggle',async e=>{const d=e.target;if(!(d instanceof HTMLDetailsElement)||!d.matches('.v1-force-history')||!d.open||d.dataset.loaded==='1')return;const body=d.querySelector('.v1-force-history-body');const root=d.closest('.v1-force-order-root');try{let data=null;if(root?.dataset.receipts){try{data=JSON.parse(root.dataset.receipts)}catch(_){}}if(!data)data=await fetchReceipts(d.dataset.family||'');if(body)body.innerHTML=historyHtml(data);d.dataset.loaded='1'}catch(err){if(body)body.innerHTML='<div class="v1-force-loading">'+esc(err.message||String(err))+'</div>'}},true);
  const kick=()=>{requestAnimationFrame(force);setTimeout(force,40);setTimeout(force,180);setTimeout(force,600)};
  new MutationObserver(kick).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('click',kick,true);document.addEventListener('pointerup',kick,true);
  setInterval(force,750);
})();
</script>
'''


def polish_force_order_detail_html(html: str) -> str:
    if 'yipmanV1ForceOrderDetailScript' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
