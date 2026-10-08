from __future__ import annotations

"""Final Family-detail enrichment for YipMan Mobile V1 RC.

Adds readable receiving/article names, compact recent sales context from the
existing Family API, and prevents long UPC identities in the detail header from
wrapping onto two lines.
"""

_STYLE = r'''
<style id="yipmanV1FamilyEnrichmentStyle">
.v1-upc-nowrap{
  white-space:nowrap!important;
  overflow-wrap:normal!important;
  word-break:keep-all!important;
  letter-spacing:-.025em!important;
  font-size:clamp(10px,3.1vw,14px)!important;
  overflow-x:auto;
  scrollbar-width:none;
}
.v1-upc-nowrap::-webkit-scrollbar{display:none}
.v1-family-related{padding:11px!important}
.v1-family-related-row{padding:9px 0!important;font-size:12px!important;line-height:1.3!important}
.v1-family-article-line{display:grid;grid-template-columns:auto minmax(0,1fr);gap:9px;align-items:start}
.v1-family-article-no{font-size:15px;font-weight:1000;color:#eef5fa;white-space:nowrap}
.v1-family-article-name{font-size:13px;font-weight:850;color:#b9c8d3;min-width:0}
.v1-family-article-role{display:inline-flex;margin-top:4px;padding:3px 6px;border:1px solid #385166;border-radius:999px;color:#83bce5;font-size:9px;font-weight:1000}
.v1-family-sales{margin:9px 0;border:1px solid #304452;border-radius:14px;background:#0f1820;overflow:hidden}
.v1-family-sales>summary{list-style:none;padding:12px 13px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:15px;font-weight:1000;color:#eef5f8}
.v1-family-sales>summary::-webkit-details-marker{display:none}
.v1-family-sales>summary::after{content:'⌄';color:#72b6e8;font-size:18px}
.v1-family-sales[open]>summary::after{content:'⌃'}
.v1-family-sales-body{border-top:1px solid #263743;padding:10px}
.v1-family-sales-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-bottom:9px}
.v1-family-sales-stat{border:1px solid #293a47;border-radius:11px;background:#111b23;padding:8px;min-width:0}
.v1-family-sales-stat b{display:block;color:#8195a5;font-size:9px;font-weight:1000}
.v1-family-sales-stat strong{display:block;margin-top:4px;font-size:15px;line-height:1.15;color:#f1f6f9;font-weight:1000;overflow-wrap:anywhere}
.v1-family-sales-note{margin:0 0 9px;color:#8296a5;font-size:10px;font-weight:800;line-height:1.35}
.v1-family-upc-row{border-top:1px solid #263643;padding:10px 1px}.v1-family-upc-row:first-of-type{border-top:0}
.v1-family-upc-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.v1-family-upc-id{font-size:15px;font-weight:1000;color:#eaf5ff;white-space:nowrap;letter-spacing:-.02em}
.v1-family-upc-type{padding:3px 6px;border:1px solid #3b5265;border-radius:999px;color:#9bc9e9;font-size:9px;font-weight:1000;white-space:nowrap}
.v1-family-upc-name{margin-top:3px;color:#b6c4ce;font-size:12px;font-weight:850;line-height:1.25}
.v1-family-upc-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:7px}
.v1-family-upc-metric{border:1px solid #273946;border-radius:9px;background:#101920;padding:7px;text-align:center;min-width:0}
.v1-family-upc-metric b{display:block;color:#778c9c;font-size:8px;font-weight:1000}
.v1-family-upc-metric span{display:block;margin-top:3px;color:#eff5f8;font-size:12px;font-weight:1000;overflow-wrap:anywhere}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1FamilyEnrichmentScript">
(()=>{
  'use strict';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null};
  const fmt=(v,d=1)=>{const n=num(v);return n===null?'—':n.toLocaleString(undefined,{maximumFractionDigits:d})};
  const money=v=>{const n=num(v);return n===null?'—':'$'+n.toFixed(2)};
  const text=(el,sel)=>String(el?.querySelector(sel)?.textContent||'').trim();
  const val=(o,keys)=>{for(const k of keys){if(o&&o[k]!==null&&o[k]!==undefined&&o[k]!=='')return o[k]}return null};
  let token=0,cache=new Map();

  function familyOf(body){
    for(const c of body.querySelectorAll('.v1-detail-id>div')){
      if(/^FAMILY$/i.test(text(c,'b')))return text(c,'span');
    }
    return'';
  }
  function markUpcNoWrap(root=document){
    root.querySelectorAll('.v1-detail-id>div').forEach(c=>{
      if(/^UPC$/i.test(text(c,'b'))){const s=c.querySelector('span');if(s)s.classList.add('v1-upc-nowrap')}
    });
  }
  async function familyData(family){
    if(cache.has(family))return cache.get(family);
    const r=await fetch('/v1/app/v2/family/'+encodeURIComponent(family),{credentials:'same-origin',cache:'no-store'});
    if(!r.ok)throw new Error('Family detail unavailable');
    const d=await r.json();cache.set(family,d);return d;
  }
  function articleHtml(a){
    const no=val(a,['article_number','receiving_article','article'])||'—';
    const name=val(a,['article_description','article_name','description','name'])||'Name unavailable';
    const role=val(a,['relationship_type'])||'';
    const primary=Boolean(a?.is_primary);
    const badge=primary?'PRIMARY':role;
    return `<div class="v1-family-related-row"><div class="v1-family-article-line"><span class="v1-family-article-no">${esc(no)}</span><span class="v1-family-article-name">${esc(name)}${badge?`<span class="v1-family-article-role">${esc(badge)}</span>`:''}</span></div></div>`;
  }
  function stat(label,value){return `<div class="v1-family-sales-stat"><b>${esc(label)}</b><strong>${esc(value)}</strong></div>`}
  function upcRow(u){
    const upc=val(u,['upc'])||'—',uom=String(val(u,['qty_uom','selling_uom'])||'').toUpperCase();
    const q7=num(val(u,['qty_7d'])),q28=num(val(u,['qty_28d']));
    const p=val(u,['current_price']),pt=String(val(u,['current_price_type'])||'').toUpperCase();
    return `<div class="v1-family-upc-row">
      <div class="v1-family-upc-head"><span class="v1-family-upc-id">UPC ${esc(upc)}</span>${pt?`<span class="v1-family-upc-type">${esc(pt)}</span>`:''}</div>
      <div class="v1-family-upc-name">${esc(val(u,['name'])||'UPC item')}</div>
      <div class="v1-family-upc-metrics">
        <div class="v1-family-upc-metric"><b>7D QTY</b><span>${esc(q7===null?'—':fmt(q7)+' '+uom)}</span></div>
        <div class="v1-family-upc-metric"><b>28D QTY</b><span>${esc(q28===null?'—':fmt(q28)+' '+uom)}</span></div>
        <div class="v1-family-upc-metric"><b>CURRENT</b><span>${esc(money(p))}</span></div>
      </div>
    </div>`;
  }
  function salesHtml(f){
    const s7=f?.family_sales_7d||{},s28=f?.family_sales_28d||{};
    const u7=String(s7.uom||'').toUpperCase(),u28=String(s28.uom||u7||'').toUpperCase();
    const q7=num(s7.sold_quantity??s7.quantity),q28=num(s28.sold_quantity??s28.quantity);
    const a7=num(s7.velocity_per_supported_day),a28=num(s28.velocity_per_supported_day);
    const upcs=Array.isArray(f?.related_upcs)?f.related_upcs:[];
    return `<details class="v1-family-sales"><summary>Recent Sales & UPC Performance <span style="color:#8398a7;font-size:10px">tap to view</span></summary><div class="v1-family-sales-body">
      <div class="v1-family-sales-summary">
        ${stat('FAMILY 7D MVT',q7===null?'—':fmt(q7)+' '+u7)}
        ${stat('7D AVG / DAY',a7===null?'—':fmt(a7)+' '+u7+'/day')}
        ${stat('FAMILY 28D MVT',q28===null?'—':fmt(q28)+' '+u28)}
        ${stat('28D AVG / DAY',a28===null?'—':fmt(a28)+' '+u28+'/day')}
      </div>
      <p class="v1-family-sales-note">Family movement is canonical 251−252. Related UPC quantities below are completed-day POS evidence and remain UPC-specific.</p>
      ${upcs.length?upcs.map(upcRow).join(''):'<div class="v1-family-sales-note">No related UPC sales evidence available.</div>'}
    </div></details>`;
  }
  async function patch(){
    markUpcNoWrap(document);
    const overlay=document.getElementById('v1DetailOverlay'),body=document.getElementById('v1DetailBody');
    if(!overlay?.classList.contains('open')||!body)return;
    const family=familyOf(body);if(!family||family==='—')return;
    if(body.dataset.familyEnriched===family)return;
    const rel=body.querySelector('.v1-family-related');
    if(!rel)return;
    const my=++token;body.dataset.familyEnriched='loading:'+family;
    try{
      const f=await familyData(family);if(my!==token||!overlay.classList.contains('open'))return;
      const arts=Array.isArray(f?.receiving_ordering_articles)?f.receiving_ordering_articles:[];
      rel.innerHTML='<b>RECEIVING / ORDERING ARTICLES</b>'+(arts.length?arts.slice(0,12).map(articleHtml).join(''):'<div class="v1-family-related-row">No receiving article detail available.</div>');
      let sales=body.querySelector('.v1-family-sales');
      if(!sales){const wrap=document.createElement('div');wrap.innerHTML=salesHtml(f);sales=wrap.firstElementChild;rel.before(sales)}
      body.dataset.familyEnriched=family;
    }catch(_){body.dataset.familyEnriched='error:'+family}
  }
  const kick=()=>{requestAnimationFrame(patch);setTimeout(patch,100);setTimeout(patch,350)};
  new MutationObserver(kick).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('click',kick,true);kick();
})();
</script>
'''


def polish_family_enrichment_html(html: str) -> str:
    if 'yipmanV1FamilyEnrichmentScript' in html:
        return html
    html = html.replace('</head>', _STYLE + '\n</head>', 1)
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
