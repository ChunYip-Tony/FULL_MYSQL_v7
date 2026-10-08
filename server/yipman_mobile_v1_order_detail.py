from __future__ import annotations

"""RC-only Family ordering detail for YipMan Mobile V1.

Ordering actions are Family-level decisions. This layer replaces the generic
UPC-centric detail with useful Family ordering evidence, prominent receiving
article information, last-receipt detail, and an on-demand recent receipt
history. True Stock editing remains owned by the shared detail interaction layer.
"""

_STYLE = r'''
<style id="yipmanV1OrderDetailStyle">
.v1-order-section{
  margin:8px 0;padding:11px 12px;border:1px solid #2e414f;border-radius:15px;
  background:#111b24;color:#e8f0f5
}
.v1-order-section-title{
  color:#8fa5b5;font-size:10px;font-weight:1000;letter-spacing:.06em;margin-bottom:8px
}
.v1-order-evidence-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
.v1-order-evidence{
  min-width:0;padding:9px;border:1px solid #2d3f4c;border-radius:12px;background:#0d171f
}
.v1-order-evidence b{display:block;color:#8095a5;font-size:9px;font-weight:1000;margin-bottom:3px}
.v1-order-evidence strong{display:block;color:#f2f6f8;font-size:16px;line-height:1.14;font-weight:1000;word-break:break-word}
.v1-order-evidence span{display:block;color:#8fa2b0;font-size:11px;line-height:1.3;margin-top:3px}
.v1-order-receiving-number{
  display:inline-block;margin-top:2px;padding:4px 8px;border:1px solid #4a7695;border-radius:8px;
  background:#142b3b;color:#dff1ff;font-size:20px!important;line-height:1!important;font-weight:1000!important;
  letter-spacing:.02em
}
.v1-last-receipt-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.v1-last-receipt-date{font-size:19px;font-weight:1000;color:#f4f7f9;line-height:1.1}
.v1-last-receipt-qty{font-size:19px;font-weight:1000;color:#87c8f4;white-space:nowrap}
.v1-last-receipt-meta{margin-top:7px;color:#aebbc4;font-size:12px;line-height:1.45}
.v1-last-receipt-meta b{color:#d9e4eb}
.v1-provisional-receipt{
  margin-top:8px;padding:8px 9px;border:1px solid #35694d;border-radius:10px;background:#10241b;
  color:#9be0b4;font-size:11px;font-weight:900;line-height:1.35
}
.v1-receipt-history{margin:8px 0;border:1px solid #304453;border-radius:14px;background:#0e1820;overflow:hidden}
.v1-receipt-history>summary{
  list-style:none;cursor:pointer;padding:12px;color:#e6eef3;font-size:14px;font-weight:1000;
  display:flex;align-items:center;justify-content:space-between;gap:8px
}
.v1-receipt-history>summary::-webkit-details-marker{display:none}
.v1-receipt-history>summary::after{content:'›';font-size:22px;color:#79b9e8;transform:rotate(90deg);transition:transform .15s ease}
.v1-receipt-history[open]>summary::after{transform:rotate(-90deg)}
.v1-receipt-history-body{border-top:1px solid #293b48;padding:6px 10px 10px}
.v1-receipt-day{padding:10px 2px;border-bottom:1px solid #23333f}
.v1-receipt-day:last-child{border-bottom:0}
.v1-receipt-day-head{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.v1-receipt-day-date{font-size:14px;font-weight:1000;color:#f0f5f8}
.v1-receipt-day-qty{font-size:14px;font-weight:1000;color:#8ec8ef;white-space:nowrap}
.v1-receipt-event{margin-top:5px;color:#9daeba;font-size:11px;line-height:1.4}
.v1-receipt-event .article{color:#d7e8f4;font-size:13px;font-weight:1000}
.v1-receipt-loading{padding:12px 2px;color:#8fa0ad;font-size:12px;font-weight:850}
.v1-order-generic-note-hidden{display:none!important}
@media(max-width:390px){
  .v1-order-section{padding:10px}
  .v1-order-evidence strong{font-size:15px}
  .v1-order-receiving-number{font-size:18px!important}
}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1OrderDetailPolish">
(function(){
  'use strict';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=(v,d=1)=>{const x=n(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:d})};
  const txt=(el,sel)=>String(el?.querySelector(sel)?.textContent||'').trim();
  const famOf=r=>String(r?.family_article_number||r?.family_article||r?.family_id||'');
  const artOf=r=>String(r?.receiving_article||r?.receiving_article_number||r?.article_number||r?.family_article_number||r?.family_article||'');
  const value=(r,keys)=>{for(const k of keys){if(r && r[k]!==null && r[k]!==undefined && r[k]!=='')return r[k]}return null};
  const firstEvent=list=>Array.isArray(list)&&list.length?list[0]:null;
  let source=null, seq=0;

  function dlabel(v){
    if(!v)return'—';
    if(typeof window.yipmanDateLabel==='function')return window.yipmanDateLabel(String(v));
    const s=String(v),m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return s;
    const d=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]));
    return ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()]+' · '+Number(m[2])+'/'+Number(m[3])+'/'+m[1];
  }
  function capture(card){
    const all=String(card?.innerText||'').replace(/\s+/g,' ').trim();
    source={
      family:(all.match(/Family\s+([0-9]{4,12})/i)||[])[1]||'',
      article:(all.match(/Receiving\s+([0-9]{4,14})/i)||[])[1]||(all.match(/Article\s+([0-9]{4,14})/i)||[])[1]||'',
      name:txt(card,'.card-title')||txt(card,'.urgent-name')||'Family Order',
      type:'order'
    };
  }
  document.addEventListener('pointerdown',e=>{
    const c=e.target.closest('#regularResults .card,#urgentList .urgent-card.order');
    if(c && !e.target.closest('button'))capture(c);
  },true);
  document.addEventListener('click',e=>{
    const c=e.target.closest('#regularResults .card,#urgentList .urgent-card.order');
    if(c && !e.target.closest('button'))capture(c);
  },true);

  function orderRow(family,article){
    try{
      if(typeof orderRows==='undefined'||!Array.isArray(orderRows))return null;
      return orderRows.find(r=>famOf(r)===family&&(!article||artOf(r)===article))
          ||orderRows.find(r=>famOf(r)===family)||null;
    }catch(_){return null}
  }
  async function familyLive(family){
    if(!family)return null;
    try{
      const r=await fetch('/v1/app/v2/family/'+encodeURIComponent(family),{credentials:'same-origin',cache:'no-store'});
      if(!r.ok)return null;return await r.json();
    }catch(_){return null}
  }
  async function receiptHistory(family){
    const r=await fetch('/app/yipman-v1-rc/api/family-receipts?family='+encodeURIComponent(family)+'&limit_days=12&_ts='+Date.now(),{credentials:'same-origin',cache:'no-store'});
    if(!r.ok)throw new Error('Receipt history unavailable');
    return await r.json();
  }
  function metric(label,val,sub=''){
    if(val===null||val===undefined||val===''||val==='—')return'';
    return `<div class="v1-order-evidence"><b>${esc(label)}</b><strong>${esc(val)}</strong>${sub?`<span>${esc(sub)}</span>`:''}</div>`;
  }
  function articleInfo(f,article){
    const list=Array.isArray(f?.receiving_ordering_articles)?f.receiving_ordering_articles:[];
    return list.find(x=>String(value(x,['article_number','receiving_article','article','sap_article'])||'')===String(article||''))||list[0]||null;
  }
  function patchIdentity(body,family,article){
    const cells=[...body.querySelectorAll('.v1-detail-id>div')];
    if(cells[0])cells[0].innerHTML=`<b>FAMILY</b><span>${esc(family||'—')}</span>`;
    if(cells[1])cells[1].innerHTML='<b>ORDER LEVEL</b><span>FAMILY</span>';
    if(cells[2])cells[2].innerHTML=`<b>RECEIVING</b><span class="v1-order-receiving-number">${esc(article||'—')}</span>`;
  }
  function receivingSection(f,row,article,ai,uom){
    const suggested=value(row,['suggested_delivery_qty','suggested_order_qty']);
    const orderUom=String(value(row,['suggested_delivery_uom','order_uom'])||uom||'').toUpperCase();
    const pack=value(ai,['pack_size','pack_qty','order_pack_size','case_pack','pack']);
    const packUom=value(ai,['pack_uom','order_uom','uom']);
    const nm=value(ai,['article_name','description','name','receiving_article_name','article_description']);
    const observed=value(row,['delivery_window_observed_count','delivery_day_observed_count','delivery_day_receipt_count']);
    const weekdays=Array.isArray(value(row,['delivery_window_observed_weekdays']))?row.delivery_window_observed_weekdays:[];
    return `<section class="v1-order-section v1-order-receiving">
      <div class="v1-order-section-title">RECEIVING & ORDER</div>
      <div class="v1-order-evidence-grid">
        ${metric('RECOMMENDED RECEIVING',article?String(article):'—',nm?String(nm):'')}
        ${metric('SUGGESTED ORDER',suggested!==null&&suggested!==undefined?fmt(suggested)+' '+orderUom:'—')}
        ${metric('PACK',pack!==null&&pack!==undefined?fmt(pack)+(packUom?' '+String(packUom):''):'—')}
        ${metric('OBSERVED DELIVERY',observed!==null&&observed!==undefined?String(observed)+' days':'—',weekdays.length?weekdays.join(' / '):'')}
      </div>
    </section>`;
  }
  function lastReceiptSection(f,uom){
    const last=f?.last_receipt||{};
    const ev=firstEvent(last?.events);
    const articles=Array.isArray(last?.events)?[...new Set(last.events.map(x=>String(x?.article_number||'').trim()).filter(Boolean))]:[];
    const qty=last?.quantity!==null&&last?.quantity!==undefined?fmt(last.quantity)+' '+String(last.uom||uom||''): '—';
    const gr=value(ev,['gr_number','article_document']);
    const po=value(ev,['purchase_order']);
    const vendor=value(ev,['vendor_code']);
    const cost=last?.cost!==null&&last?.cost!==undefined?'$'+Number(last.cost).toFixed(2)+(last?.cost_uom?' / '+String(last.cost_uom):''):null;
    const today=f?.today_receipt||{};
    const provisional=Number(today?.event_count||0)>0
      ? `<div class="v1-provisional-receipt">TODAY · PROVISIONAL RECEIPT: ${esc(fmt(today.quantity))} ${esc(today.uom||uom||'')} · visibility only until completed-day authority.</div>`:'';
    if(!last?.date&&!provisional)return'';
    return `<section class="v1-order-section v1-last-receipt">
      <div class="v1-order-section-title">LAST RECEIPT</div>
      ${last?.date?`<div class="v1-last-receipt-head"><div class="v1-last-receipt-date">${esc(dlabel(last.date))}</div><div class="v1-last-receipt-qty">${esc(qty)}</div></div>`:''}
      ${last?.date?`<div class="v1-last-receipt-meta">
        ${articles.length?`<div><b>Receiving Article:</b> ${articles.map(esc).join(' / ')}</div>`:''}
        ${cost?`<div><b>Receipt Cost:</b> ${esc(cost)}</div>`:''}
        ${gr?`<div><b>GR:</b> ${esc(gr)}</div>`:''}
        ${po?`<div><b>PO:</b> ${esc(po)}</div>`:''}
        ${vendor?`<div><b>Vendor:</b> ${esc(vendor)}</div>`:''}
      </div>`:''}
      ${provisional}
    </section>`;
  }
  function historyShell(family){
    return `<details class="v1-receipt-history" data-family="${esc(family)}">
      <summary>Recent Receipt History <span style="color:#7f95a4;font-size:11px">tap to view</span></summary>
      <div class="v1-receipt-history-body"><div class="v1-receipt-loading">Open to load recent canonical receipts.</div></div>
    </details>`;
  }
  function historyHtml(data){
    const days=Array.isArray(data?.days)?data.days:[];
    if(!days.length)return '<div class="v1-receipt-loading">No recent positive canonical receipts found.</div>';
    return days.map(day=>{
      const qty=day?.quantity!==null&&day?.quantity!==undefined?fmt(day.quantity)+' '+String(day.uom||''): '—';
      const events=Array.isArray(day?.events)?day.events:[];
      return `<div class="v1-receipt-day">
        <div class="v1-receipt-day-head"><div class="v1-receipt-day-date">${esc(dlabel(day.date))}</div><div class="v1-receipt-day-qty">${esc(qty)}</div></div>
        ${events.map(ev=>{
          const gr=value(ev,['gr_number','article_document']);
          const bits=[];
          if(ev?.receipt_quantity!==null&&ev?.receipt_quantity!==undefined)bits.push(fmt(ev.receipt_quantity)+' '+String(ev.receipt_uom||''));
          if(gr)bits.push('GR '+gr);
          if(ev?.purchase_order)bits.push('PO '+ev.purchase_order);
          if(ev?.vendor_code)bits.push('Vendor '+ev.vendor_code);
          return `<div class="v1-receipt-event"><span class="article">Article ${esc(ev?.article_number||'—')}</span>${bits.length?' · '+esc(bits.join(' · ')):''}</div>`;
        }).join('')}
      </div>`;
    }).join('');
  }
  async function onHistoryToggle(details){
    if(!details?.open||details.dataset.loaded==='1'||details.dataset.loading==='1')return;
    details.dataset.loading='1';
    const body=details.querySelector('.v1-receipt-history-body');if(body)body.innerHTML='<div class="v1-receipt-loading">Loading receipt history…</div>';
    try{
      const data=await receiptHistory(details.dataset.family||'');
      if(body)body.innerHTML=historyHtml(data);details.dataset.loaded='1';
    }catch(e){if(body)body.innerHTML='<div class="v1-receipt-loading">'+esc(e.message||String(e))+'</div>'}
    finally{details.dataset.loading='0'}
  }
  document.addEventListener('toggle',e=>{if(e.target?.matches?.('.v1-receipt-history'))onHistoryToggle(e.target)},true);

  async function patch(){
    const overlay=document.getElementById('v1DetailOverlay');
    const body=document.getElementById('v1DetailBody');
    if(!overlay?.classList.contains('open')||!body||body.dataset.orderFamilyPolished==='1'||body.dataset.orderFamilyPolished==='loading')return;
    const decision=txt(body,'.v1-detail-decision strong').toUpperCase();
    const orderLike=/^(ORDER|NO ORDER)/.test(decision);
    if(!orderLike&&source?.type!=='order')return;

    const cells=[...body.querySelectorAll('.v1-detail-id span')];
    const family=source?.family||String(cells[0]?.textContent||'').trim();
    const article=source?.article||String(cells[2]?.textContent||'').trim();
    if(!family)return;
    const token=++seq;body.dataset.orderFamilyPolished='loading';
    const [f,row]=await Promise.all([familyLive(family),Promise.resolve(orderRow(family,article))]);
    if(token!==seq||!overlay.classList.contains('open'))return;

    const fs=f?.family_sales_7d||{};
    const oh=f?.current_effective_oh||{};
    const ai=articleInfo(f,article);
    const uom=String(oh?.uom||row?.effective_oh_uom||row?.suggested_delivery_uom||row?.order_uom||fs?.uom||'').toUpperCase();
    const familyMvt=value(row,['family_group_movement_7d'])??value(fs,['quantity','sold_quantity']);
    const avg=value(row,['family_group_avg_qty_day'])??value(fs,['velocity_per_supported_day']);
    const delivery=value(row,['selected_delivery_date','delivery_date'])||document.getElementById('deliveryDate')?.value;
    const next=value(row,['selected_next_delivery_date','next_delivery_date'])||document.getElementById('nextDeliveryDate')?.value;
    const projected=value(row,['projected_oh_at_delivery','projected_oh_at_expected_delivery','usable_oh_at_delivery']);
    const coverage=value(row,['forecast_coverage_usage','forecast_requested_coverage_usage','coverage_usage']);
    const preDelivery=value(row,['forecast_usage_before_expected_delivery','forecast_before_delivery_usage','before_delivery_usage']);
    const suggested=value(row,['suggested_delivery_qty','suggested_order_qty']);
    const orderUom=String(value(row,['suggested_delivery_uom','order_uom'])||uom||'').toUpperCase();

    patchIdentity(body,family,article);
    const title=document.getElementById('v1DetailTitle');if(title&&f?.family_article_name)title.textContent=String(f.family_article_name);

    const ohBtn=body.querySelector('#v1DetailOh');
    if(ohBtn&&n(oh?.quantity)!==null){const strong=ohBtn.querySelector('strong');if(strong)strong.textContent=fmt(oh.quantity)+' '+uom}

    const metrics=body.querySelector('.v1-detail-metrics');
    if(metrics){
      metrics.innerHTML=[
        metric('FAMILY 7D MVT',familyMvt!==null&&familyMvt!==undefined?fmt(familyMvt)+' '+String(fs?.uom||row?.family_group_movement_uom||uom):null),
        metric('AVG / DAY',avg!==null&&avg!==undefined?fmt(avg)+' '+String(fs?.uom||row?.family_group_movement_uom||uom)+'/day':null),
        metric('DELIVERY',delivery?dlabel(delivery):null),
        metric('NEXT DELIVERY',next?dlabel(next):null),
        metric('PROJECTED OH @ DELIVERY',projected!==null&&projected!==undefined?fmt(projected)+' '+uom:null),
        metric('COVERAGE USAGE',coverage!==null&&coverage!==undefined?fmt(coverage)+' '+uom:null),
        metric('PRE-DELIVERY USAGE',preDelivery!==null&&preDelivery!==undefined?fmt(preDelivery)+' '+uom:null),
        metric('SUGGESTED ORDER',suggested!==null&&suggested!==undefined?fmt(suggested)+' '+orderUom:null),
      ].join('');
      metrics.classList.add('v1-order-evidence-grid');
    }

    body.querySelectorAll('.v1-order-section,.v1-receipt-history').forEach(el=>el.remove());
    const note=body.querySelector('.v1-detail-note');
    const insertBefore=note||null;
    const wrap=document.createElement('div');
    wrap.innerHTML=receivingSection(f,row,article,ai,uom)+lastReceiptSection(f,uom)+historyShell(family);
    [...wrap.children].forEach(el=>body.insertBefore(el,insertBefore));
    if(note){note.textContent='';note.classList.add('v1-order-generic-note-hidden')}

    body.dataset.orderFamilyPolished='1';
  }

  const mo=new MutationObserver(()=>requestAnimationFrame(patch));
  mo.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('click',()=>setTimeout(patch,0));
})();
</script>
'''


def polish_order_detail_html(html: str) -> str:
    if 'yipmanV1OrderDetailPolish' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
