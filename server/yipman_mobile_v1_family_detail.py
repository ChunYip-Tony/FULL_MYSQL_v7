from __future__ import annotations

"""RC-only family detail fallback for Mobile V1.

The primary interaction renderer is UPC-centric. Quick Search and some Family
suggestion cards legitimately have no UPC, which previously produced a detail
screen full of dashes. This decorator detects those Family-only detail views,
loads live Family + PI data, and renders Family inventory/movement/receipt
context instead. It also provides Family True Stock editing that persists
through the existing PI endpoint and reloads calculations after save.
"""

_STYLE = r'''
<style id="yipmanV1FamilyDetailStyle">
.v1-family-related{margin:0 0 9px;border:1px solid #2d3b47;border-radius:13px;background:#111920;padding:10px}
.v1-family-related b{display:block;color:#7c8d99;font-size:8px;margin-bottom:6px}
.v1-family-related-row{padding:7px 0;border-top:1px solid #24313c;font-size:9px;color:#b8c3cc;font-weight:850}
.v1-family-related-row:first-of-type{border-top:0}
#v1FamilyStockBackdrop{position:fixed;inset:0;z-index:220;background:rgba(0,0,0,.72);display:none;align-items:flex-end;justify-content:center}
#v1FamilyStockBackdrop.open{display:flex}
.v1-family-stock-sheet{width:min(100%,680px);background:#17212b;border:1px solid #3a4855;border-radius:22px 22px 0 0;padding:17px 14px calc(17px + env(safe-area-inset-bottom))}
.v1-family-stock-sheet h3{margin:0;font-size:20px}.v1-family-stock-meta{margin-top:4px;color:#8999a7;font-size:10px;font-weight:850}
.v1-family-stock-input{width:100%;height:58px;margin-top:12px;border:2px solid #4e86b0;border-radius:13px;background:#0c141b;color:#fff;padding:8px 12px;font-size:24px;font-weight:1000;outline:0}
.v1-family-stock-actions{display:grid;grid-template-columns:1fr 1.4fr;gap:8px;margin-top:11px}.v1-family-stock-actions button{min-height:50px;border-radius:12px;font-size:11px;font-weight:1000}
.v1-family-stock-cancel{border:1px solid #3b4955;background:#101820;color:#aeb9c3}.v1-family-stock-save{border:1px solid #3c76aa;background:#1b5687;color:#fff}.v1-family-stock-save:disabled{opacity:.55}
.v1-family-stock-status{min-height:18px;margin-top:8px;color:#8fa1ae;font-size:9px;font-weight:850}.v1-family-stock-status.error{color:#ff8d97}.v1-family-stock-status.good{color:#8fd3a0}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1FamilyDetailScript">
(function(){
  'use strict';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
  const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=(v,d=1)=>{const x=num(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:d})};
  const val=(o,keys)=>{for(const k of keys){if(o&&o[k]!==null&&o[k]!==undefined&&o[k]!=='')return o[k]}return null};
  let token=0,ctx=null;

  async function getJson(url){const r=await fetch(url,{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw new Error(await r.text().catch(()=>('HTTP '+r.status)));return r.json()}
  function ensureSheet(){
    if(document.getElementById('v1FamilyStockBackdrop'))return;
    const x=document.createElement('div');x.id='v1FamilyStockBackdrop';x.innerHTML=`<div class="v1-family-stock-sheet"><h3>Enter True Stock</h3><div class="v1-family-stock-meta" id="v1FamilyStockMeta"></div><input class="v1-family-stock-input" id="v1FamilyStockInput" type="number" inputmode="decimal" min="0" step="0.1"><div class="v1-family-stock-status" id="v1FamilyStockStatus"></div><div class="v1-family-stock-actions"><button type="button" class="v1-family-stock-cancel" id="v1FamilyStockCancel">Cancel</button><button type="button" class="v1-family-stock-save" id="v1FamilyStockSave">Save + Recalculate</button></div></div>`;
    document.body.appendChild(x);document.getElementById('v1FamilyStockCancel').onclick=()=>x.classList.remove('open');x.addEventListener('click',e=>{if(e.target===x)x.classList.remove('open')});document.getElementById('v1FamilyStockSave').onclick=save;
  }
  function openSheet(){
    if(!ctx?.family||!ctx?.uom)return;
    ensureSheet();const b=document.getElementById('v1FamilyStockBackdrop'),i=document.getElementById('v1FamilyStockInput'),s=document.getElementById('v1FamilyStockStatus');
    document.getElementById('v1FamilyStockMeta').textContent=(ctx.name||'Family')+' · Family '+ctx.family+' · '+ctx.uom;
    i.value=ctx.qty===null?'':String(ctx.qty);s.textContent='';s.className='v1-family-stock-status';b.classList.add('open');setTimeout(()=>{i.focus();i.select()},40);
  }
  async function save(){
    const i=document.getElementById('v1FamilyStockInput'),b=document.getElementById('v1FamilyStockSave'),s=document.getElementById('v1FamilyStockStatus');const q=Number(i.value);
    if(!Number.isFinite(q)||q<0){s.textContent='Enter a valid physical True Stock quantity.';s.className='v1-family-stock-status error';return}
    b.disabled=true;b.textContent='Saving…';s.textContent='Recording True Stock and recalculating…';
    try{
      const r=await fetch('/v1/app/v2/pi/'+encodeURIComponent(ctx.family)+'/true-stock',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:q,uom:ctx.uom,note:'YIPMAN_MOBILE_V1_FAMILY_DETAIL'})});
      const t=await r.text();let d={};try{d=t?JSON.parse(t):{}}catch(_){}if(!r.ok)throw new Error(d?.detail?.reason||d?.reason||t||('HTTP '+r.status));
      s.textContent='Saved. Reloading live calculations…';s.className='v1-family-stock-status good';
      setTimeout(()=>location.reload(),350);
    }catch(e){s.textContent=e.message||String(e);s.className='v1-family-stock-status error';b.disabled=false;b.textContent='Save + Recalculate'}
  }
  function row(label,value){return `<div><b>${esc(label)}</b><span>${esc(value??'—')}</span></div>`}
  function familyId(body){const cells=[...body.querySelectorAll('.v1-detail-id>div')];for(const c of cells){if(/^FAMILY$/i.test(String(c.querySelector('b')?.textContent||'').trim()))return String(c.querySelector('span')?.textContent||'').trim()}return''}
  function upcId(body){const cells=[...body.querySelectorAll('.v1-detail-id>div')];for(const c of cells){if(/^UPC$/i.test(String(c.querySelector('b')?.textContent||'').trim()))return String(c.querySelector('span')?.textContent||'').trim()}return''}

  async function patch(){
    const overlay=document.getElementById('v1DetailOverlay'),body=document.getElementById('v1DetailBody');if(!overlay?.classList.contains('open')||!body)return;
    const family=familyId(body),upc=upcId(body);if(!family||family==='—'||(upc&&upc!=='—'))return;
    if(body.dataset.familyLive==='1'||body.dataset.orderFamilyPolished==='1')return;
    const my=++token;body.dataset.familyLive='loading';
    try{
      const [f,pi]=await Promise.all([getJson('/v1/app/v2/family/'+encodeURIComponent(family)),getJson('/v1/app/v2/pi/'+encodeURIComponent(family)).catch(()=>null)]);if(my!==token||!overlay.classList.contains('open'))return;
      const oh=f?.current_effective_oh||pi?.current_effective_oh||pi?.effective_oh||{};
      const fs=f?.family_sales_7d||{};const last=f?.last_receipt||{};const obs=f?.observed_delivery||{};const arts=Array.isArray(f?.receiving_ordering_articles)?f.receiving_ordering_articles:[];
      const uom=String(val(oh,['uom'])||val(fs,['uom'])||val(pi,['uom','effective_oh_uom'])||'').toUpperCase();const qty=num(val(oh,['quantity','qty','effective_oh']));
      const sys=pi?.system_oh||pi?.current_system_oh||{};const title=document.getElementById('v1DetailTitle');if(title&&f?.family_article_name)title.textContent=f.family_article_name;
      const cells=[...body.querySelectorAll('.v1-detail-id>div')];if(cells[1])cells[1].innerHTML='<b>DETAIL LEVEL</b><span>FAMILY</span>';if(cells[2])cells[2].innerHTML=`<b>FAMILY ARTICLE</b><span>${esc(f?.family_article_number||family)}</span>`;
      const dec=body.querySelector('.v1-detail-decision');if(dec){dec.querySelector('small').textContent='FAMILY STATUS';dec.querySelector('strong').textContent='FAMILY DETAIL';dec.querySelector('p').textContent='Live Family inventory, movement and receiving context. Select a related UPC for UPC-level price and POS performance.'}
      const ohBtn=body.querySelector('#v1DetailOh');if(ohBtn){ohBtn.querySelector('strong').textContent=(qty===null?'—':fmt(qty))+(uom?' '+uom:'');ohBtn.querySelector('span').textContent=uom?'Touch to record physical True Stock. Saving immediately rebuilds Effective OH, Price and Ordering.':'Family UOM is unresolved; True Stock save is blocked until UOM is confirmed.'}
      const metrics=body.querySelector('.v1-detail-metrics');if(metrics)metrics.innerHTML=[row('SYSTEM OH',num(val(sys,['quantity','qty']))===null?'—':fmt(val(sys,['quantity','qty']))+' '+String(val(sys,['uom'])||uom)),row('FAMILY 7D MVT',num(val(fs,['quantity']))===null?'—':fmt(fs.quantity)+' '+String(fs.uom||uom)),row('AVG / DAY',num(val(fs,['velocity_per_supported_day']))===null?'—':fmt(fs.velocity_per_supported_day)+' '+String(fs.uom||uom)+'/day'),row('VALID MVT DAYS',val(fs,['supported_day_count'])??'—'),row('LAST RECEIPT',last?.date?(window.yipmanDateLabel?window.yipmanDateLabel(last.date):last.date):'—'),row('DELIVERY PATTERN',val(obs,['frequency','confidence','next_expected_date'])??'—')].join('');
      let rel=body.querySelector('.v1-family-related');if(!rel){rel=document.createElement('div');rel.className='v1-family-related';body.querySelector('.v1-detail-note')?.before(rel)}
      rel.innerHTML='<b>RECEIVING / ORDERING ARTICLES</b>'+(arts.length?arts.slice(0,8).map(a=>`<div class="v1-family-related-row">${esc(val(a,['article_number','receiving_article','article'])||'Article')} · ${esc(val(a,['article_name','description','name'])||'')}</div>`).join(''):'<div class="v1-family-related-row">No receiving article detail available.</div>');
      const note=body.querySelector('.v1-detail-note');if(note)note.textContent='Family-level detail loaded from FULL MYSQL. UPC-specific Current Price, Cost, POS Qty and GP$ belong on the related UPC detail rather than being shown as blank Family fields.';
      ctx={family,name:f?.family_article_name||title?.textContent||'Family',uom,qty};if(ohBtn){ohBtn.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();if(ctx.uom)openSheet()};}
      body.dataset.familyLive='1';
    }catch(e){body.dataset.familyLive='error';const note=body.querySelector('.v1-detail-note');if(note)note.textContent='Family live detail could not be loaded: '+(e.message||String(e))}
  }
  const mo=new MutationObserver(()=>requestAnimationFrame(patch));mo.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});document.addEventListener('click',()=>setTimeout(patch,0),true);
})();
</script>
'''


def polish_family_detail_html(html: str) -> str:
    if 'yipmanV1FamilyDetailScript' in html:
        return html
    html = html.replace('</head>', _STYLE + '\n</head>', 1)
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
