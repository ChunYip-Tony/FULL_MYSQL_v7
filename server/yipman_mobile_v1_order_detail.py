from __future__ import annotations

"""RC-only family-order detail polish for YipMan Mobile V1.

The generic detail renderer is UPC-centric. Ordering suggestions are Family-level,
so a card may legitimately have no UPC. This decorator converts those detail pages
to Family ordering context and fills live Family movement/receipt/delivery data.
"""

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
  let source=null, seq=0;

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
    if(c && !e.target.closest('button')) capture(c);
  },true);
  document.addEventListener('click',e=>{
    const c=e.target.closest('#regularResults .card,#urgentList .urgent-card.order');
    if(c && !e.target.closest('button')) capture(c);
  },true);

  function orderRow(family,article){
    try{
      if(typeof orderRows==='undefined'||!Array.isArray(orderRows)) return null;
      return orderRows.find(r=>famOf(r)===family && (!article||artOf(r)===article))
          || orderRows.find(r=>famOf(r)===family)
          || null;
    }catch(_){return null}
  }
  async function familyLive(family){
    if(!family)return null;
    try{
      const r=await fetch('/v1/app/v2/family/'+encodeURIComponent(family),{credentials:'same-origin',cache:'no-store'});
      if(!r.ok)return null;
      return await r.json();
    }catch(_){return null}
  }
  function metric(label,val){
    if(val===null||val===undefined||val===''||val==='—')return'';
    return `<div><b>${esc(label)}</b><span>${esc(val)}</span></div>`;
  }
  function articleInfo(f,article){
    const list=Array.isArray(f?.receiving_ordering_articles)?f.receiving_ordering_articles:[];
    return list.find(x=>String(value(x,['article_number','receiving_article','article','sap_article'])||'')===String(article||'')) || list[0] || null;
  }
  function patchIdentity(body,family,article){
    const cells=[...body.querySelectorAll('.v1-detail-id>div')];
    if(cells[0])cells[0].innerHTML=`<b>FAMILY</b><span>${esc(family||'—')}</span>`;
    if(cells[1])cells[1].innerHTML='<b>ORDER LEVEL</b><span>FAMILY</span>';
    if(cells[2])cells[2].innerHTML=`<b>RECEIVING</b><span>${esc(article||'—')}</span>`;
  }
  async function patch(){
    const overlay=document.getElementById('v1DetailOverlay');
    const body=document.getElementById('v1DetailBody');
    if(!overlay?.classList.contains('open')||!body||body.dataset.orderFamilyPolished==='1')return;
    const decision=txt(body,'.v1-detail-decision strong').toUpperCase();
    const orderLike=/^(ORDER|NO ORDER)/.test(decision);
    if(!orderLike && source?.type!=='order')return;

    const cells=[...body.querySelectorAll('.v1-detail-id span')];
    const family=source?.family||String(cells[0]?.textContent||'').trim();
    const article=source?.article||String(cells[2]?.textContent||'').trim();
    if(!family)return;
    const token=++seq;
    body.dataset.orderFamilyPolished='loading';
    const [f,row]=await Promise.all([familyLive(family),Promise.resolve(orderRow(family,article))]);
    if(token!==seq||!overlay.classList.contains('open'))return;

    const fs=f?.family_sales_7d||{};
    const oh=f?.current_effective_oh||{};
    const last=f?.last_receipt||{};
    const obs=f?.observed_delivery||{};
    const ai=articleInfo(f,article);
    const uom=String(oh?.uom||row?.effective_oh_uom||row?.suggested_delivery_uom||row?.order_uom||fs?.uom||'').toUpperCase();
    const familyMvt=value(row,['family_group_movement_7d']) ?? value(fs,['quantity']);
    const avg=value(row,['family_group_avg_qty_day']) ?? value(fs,['velocity_per_supported_day']);
    const delivery=value(row,['selected_delivery_date','delivery_date']) || document.getElementById('deliveryDate')?.value;
    const next=value(row,['selected_next_delivery_date','next_delivery_date']) || document.getElementById('nextDeliveryDate')?.value;
    const observed=value(row,['delivery_window_observed_count','delivery_day_observed_count','delivery_day_receipt_count']) ?? value(obs,['receipt_date_count','observed_count']);
    const suggested=value(row,['suggested_delivery_qty']);
    const orderUom=String(value(row,['suggested_delivery_uom','order_uom'])||uom);
    const pack=value(ai,['pack_size','pack_qty','order_pack_size','case_pack','pack']);
    const packUom=value(ai,['pack_uom','order_uom','uom']);
    const lastText=last?.date ? `${last.date}${last?.quantity!==null&&last?.quantity!==undefined?' · '+fmt(last.quantity)+' '+String(last.uom||uom):''}` : null;

    patchIdentity(body,family,article);
    const title=document.getElementById('v1DetailTitle');
    if(title && f?.family_article_name)title.textContent=String(f.family_article_name);

    const ohBtn=body.querySelector('#v1DetailOh');
    if(ohBtn && (n(oh?.quantity)!==null)){
      const strong=ohBtn.querySelector('strong');
      if(strong && /^—/.test(strong.textContent.trim())) strong.textContent=fmt(oh.quantity)+' '+uom;
    }

    const metrics=body.querySelector('.v1-detail-metrics');
    if(metrics){
      metrics.innerHTML=[
        metric('FAMILY 7D MVT',familyMvt!==null&&familyMvt!==undefined?fmt(familyMvt)+' '+String(fs?.uom||row?.family_group_movement_uom||uom):null),
        metric('AVG / DAY',avg!==null&&avg!==undefined?fmt(avg)+' '+String(fs?.uom||row?.family_group_movement_uom||uom)+'/day':null),
        metric('DELIVERY',delivery),
        metric('NEXT DELIVERY',next),
        metric('OBSERVED DAYS',observed!==null&&observed!==undefined?String(observed):null),
        metric('LAST RECEIPT',lastText),
      ].join('');
    }

    let extra=body.querySelector('.v1-order-extra');
    if(!extra){extra=document.createElement('div');extra.className='v1-detail-note v1-order-extra';body.querySelector('.v1-detail-note')?.before(extra)}
    const parts=[];
    if(article)parts.push(`<b>Receiving Article:</b> ${esc(article)}`);
    if(ai){const nm=value(ai,['article_name','description','name','receiving_article_name']);if(nm)parts.push(`<b>Receiving Name:</b> ${esc(nm)}`)}
    if(pack!==null&&pack!==undefined)parts.push(`<b>Pack:</b> ${esc(fmt(pack))}${packUom?' '+esc(packUom):''}`);
    if(suggested!==null&&suggested!==undefined)parts.push(`<b>Suggested Order:</b> ${esc(fmt(suggested))} ${esc(orderUom)}`);
    if(Array.isArray(value(row,['delivery_window_observed_weekdays'])))parts.push(`<b>Observed Window:</b> ${esc(row.delivery_window_observed_weekdays.join(' / '))}`);
    extra.innerHTML=parts.join('<br>') || 'Family-level ordering detail loaded.';

    const note=body.querySelector('.v1-detail-note:not(.v1-order-extra)');
    if(note)note.textContent='This is a Family-level ordering action. UPC price/sales tiles are intentionally replaced by Family movement, delivery, receipt and ordering evidence.';
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
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
