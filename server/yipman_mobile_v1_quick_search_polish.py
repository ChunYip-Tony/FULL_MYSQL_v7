from __future__ import annotations

"""RC-only Quick Search performance + information polish.

Goals:
- return the initial search roster quickly (small lightweight query; no OH expansion)
- immediately render useful identity + family movement context
- enrich visible UPC rows asynchronously from the existing UPC detail endpoint
- prevent stale/slow searches from overwriting newer queries
- keep Effective OH touch-to-edit behavior compatible with the interaction layer
"""

_STYLE = r'''
<style id="yipmanV1QuickSearchPolishStyle">
#quickResults .quick-result{padding:12px 13px}
#quickResults .quick-result h3{font-size:19px;line-height:1.08}
#quickResults .quick-result p{line-height:1.35}
#quickResults .quick-search-status{margin:0 0 8px;padding:7px 9px;border:1px solid #263541;border-radius:10px;background:#0f171e;color:#78909f;font-size:9px;font-weight:900}
#quickResults .quick-search-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:9px}
#quickResults .quick-search-grid .stat{padding:7px 5px}
#quickResults .quick-search-grid .stat span{font-size:11px}
#quickResults .quick-search-foot{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px;color:#8293a0;font-size:8px;font-weight:900}
#quickResults .quick-search-foot span{padding:4px 7px;border:1px solid #2b3945;border-radius:999px;background:#101820}
#quickResults .quick-enriching{opacity:.72}
@media(max-width:390px){#quickResults .quick-search-grid{grid-template-columns:repeat(2,1fr)}}
</style>
'''


def polish_quick_search_html(html: str) -> str:
    marker = "yipmanV1QuickSearchPolishApplied"
    if marker in html:
        return html

    start = html.find("async function searchQuick(q){")
    end = html.find("async function loadOrdering(){", start)
    if start < 0 or end < 0:
        return html

    new_block = r'''function quickSearchRank(r,q){
 const needle=String(q||'').trim().toLowerCase(); if(!needle)return 0;
 const up=upcOf(r).toLowerCase(),art=artOf(r).toLowerCase(),fam=famOf(r).toLowerCase(),name=nameOf(r).toLowerCase();
 if(up===needle||art===needle||fam===needle)return 100;
 if(up.startsWith(needle)||art.startsWith(needle)||fam.startsWith(needle))return 90;
 if(name===needle)return 80;
 if(name.startsWith(needle))return 75;
 if(name.includes(needle))return 65;
 return 10;
}
function quickSearchBaseCard(r){
 const up=upcOf(r),fam=famOf(r),art=artOf(r),uom=r?.effective_oh_uom||r?.oh_uom||r?.movement_uom||'';
 const fm=r?.family_group_movement_7d??r?.movement_7d??r?.group_qty_7d;
 const favg=r?.family_group_avg_qty_day??r?.group_avg_qty_day??r?.avg_qty_day;
 return `<div class="quick-result quick-enriching" data-quick-upc="${esc(up)}" data-quick-family="${esc(fam)}"><h3>${esc(nameOf(r))}</h3><p>${fam?'Family '+esc(fam):''}${up?' · UPC '+esc(up):''}${art?' · Article '+esc(art):''}</p><div class="quick-search-grid"><div class="stat"><b>EFFECTIVE OH</b><span>Loading…</span></div><div class="stat"><b>FAMILY 7D MVT</b><span>${fmt(fm)} ${esc(uom)}</span></div><div class="stat"><b>FAMILY AVG/DAY</b><span>${fmt(favg)} ${esc(uom)}</span></div><div class="stat"><b>UPC 7D QTY</b><span>Loading…</span></div><div class="stat"><b>UPC AVG/DAY</b><span>Loading…</span></div><div class="stat"><b>CURRENT PRICE</b><span>Loading…</span></div></div><div class="quick-search-foot"><span>COST Loading…</span><span>PRICE TYPE Loading…</span><span>DOS Loading…</span></div></div>`;
}
async function enrichQuickCard(card,seq){
 const up=card?.dataset?.quickUpc; if(!up)return;
 try{
  const d=await api('/v1/app/v2/upc/'+encodeURIComponent(up));
  if(searchQuick._seq!==seq||!card.isConnected)return;
  const oh=d?.effective_oh||{},q7=d?.qty_7d||{},uom=oh?.uom||d?.selling_uom||d?.qty_uom||'';
  const validDays=num(q7?.supported_day_count),sold=num(q7?.sold_quantity),avg=num(d?.upc_velocity_7d);
  const stats=[...card.querySelectorAll('.stat')];
  const put=(label,value)=>{const x=stats.find(s=>String(s.querySelector('b')?.textContent||'').trim()===label);if(x){const sp=x.querySelector('span');if(sp)sp.textContent=value}};
  const title=card.querySelector('h3'); if(title&&d?.upc_name)title.textContent=d.upc_name;
  put('EFFECTIVE OH',(num(oh?.quantity)===null?'—':fmt(oh.quantity)+' '+uom));
  put('UPC 7D QTY',(sold===null?'—':fmt(sold)+' '+(d?.qty_uom||uom)));
  put('UPC AVG/DAY',(avg===null?'—':fmt(avg)+' '+(d?.qty_uom||uom)+'/day'));
  put('CURRENT PRICE',validPrice(d?.current_price)!==null?money(d.current_price)+' '+String(d?.current_price_type||''):'—');
  const foot=card.querySelector('.quick-search-foot');
  if(foot)foot.innerHTML=`<span>COST ${validPrice(d?.current_cost_per_selling_unit)!==null?money(d.current_cost_per_selling_unit)+' / '+esc(d?.selling_uom||'unit'):'—'}</span><span>PRICE ${esc(d?.current_price_type||'—')}</span><span>DOS ${fmt(d?.dos)}</span><span>${validDays===null?'—':fmt(validDays,0)} VALID DAYS</span>`;
  card.classList.remove('quick-enriching');
 }catch(_){
  if(searchQuick._seq!==seq||!card.isConnected)return;
  card.classList.remove('quick-enriching');
  const foot=card.querySelector('.quick-search-foot'); if(foot)foot.innerHTML='<span>DETAIL UNAVAILABLE · TAP CARD TO RETRY</span>';
 }
}
async function enrichQuickCards(cards,seq){
 const queue=[...cards].filter(c=>c.dataset.quickUpc).slice(0,12); let i=0;
 async function worker(){while(i<queue.length){const card=queue[i++];await enrichQuickCard(card,seq)}}
 await Promise.all([worker(),worker(),worker(),worker()]);
}
async function searchQuick(q){
 const seq=(searchQuick._seq||0)+1;searchQuick._seq=seq;
 if(searchQuick._controller)try{searchQuick._controller.abort()}catch(_){}
 const controller=new AbortController();searchQuick._controller=controller;
 const box=$('#quickResults');$('#urgentList').style.display='none';box.classList.add('show');box.innerHTML='<div class="quick-search-status">Searching…</div>';
 try{
  const d=await api('/v1/backoffice/inventory?category=ALL&limit=20&lightweight=true&q='+encodeURIComponent(q),{signal:controller.signal});
  if(searchQuick._seq!==seq)return;
  const rows=(d.rows||[]).sort((a,b)=>quickSearchRank(b,q)-quickSearchRank(a,q));
  box.innerHTML=rows.length?'<div class="quick-search-status">'+rows.length+' matches · basic results ready · loading live OH / price / UPC sales…</div>'+rows.slice(0,20).map(quickSearchBaseCard).join(''):'<div class="empty">No matches</div>';
  requestAnimationFrame(()=>{ if(window.yipmanV1MarkEditableOH)window.yipmanV1MarkEditableOH(box); });
  enrichQuickCards([...box.querySelectorAll('.quick-result')],seq).then(()=>{if(searchQuick._seq===seq){const s=box.querySelector('.quick-search-status');if(s)s.textContent=rows.length+' matches · live details loaded'}});
 }catch(e){
  if(e?.name==='AbortError')return;
  if(searchQuick._seq!==seq)return;
  box.classList.add('show');box.innerHTML='<div class="empty">Search unavailable · '+esc(e.message)+'</div>';
 }
}
'''
    html = html[:start] + new_block + html[end:]

    # Shorter debounce: initial roster is intentionally lightweight.
    html = html.replace(
        "qt=setTimeout(()=>searchQuick(q),260)",
        "qt=setTimeout(()=>searchQuick(q),120)",
        1,
    )

    html = html.replace("</head>", _STYLE + '<meta name="yipmanV1QuickSearchPolishApplied" content="1">\n</head>', 1)
    return html
