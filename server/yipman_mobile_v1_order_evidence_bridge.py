from __future__ import annotations

"""Bridge authoritative Ordering row.details fields into Mobile V1 detail evidence."""

_SCRIPT = r'''
<script id="yipmanV1OrderEvidenceBridge">
(function(){
  'use strict';
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=(v,d=1)=>{const x=n(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:d})};
  const famOf=r=>String(r?.family_article_number||r?.family_article||r?.family_id||'');
  const val=(o,k)=>o&&o[k]!==null&&o[k]!==undefined&&o[k]!==''?o[k]:null;
  const metric=(label,value,uom,key)=>value===null?'':`<div class="v1-order-evidence" data-evidence-key="${key}"><b>${label}</b><strong>${fmt(value)} ${uom||''}</strong></div>`;

  function selectedRow(body){
    try{
      if(typeof orderRows==='undefined'||!Array.isArray(orderRows))return null;
      const first=String(body?.querySelector('.v1-detail-id span')?.textContent||'').trim();
      return orderRows.find(r=>famOf(r)===first)||null;
    }catch(_){return null}
  }

  function patch(){
    const overlay=document.getElementById('v1DetailOverlay');
    const body=document.getElementById('v1DetailBody');
    if(!overlay?.classList.contains('open')||!body||body.dataset.orderEvidenceBridged==='1')return;
    const decision=String(body.querySelector('.v1-detail-decision strong')?.textContent||'').trim().toUpperCase();
    if(!/^(ORDER|NO ORDER)/.test(decision))return;
    const row=selectedRow(body);if(!row)return;
    const d=row.details||{};
    const uom=String(row.effective_oh_uom||row.suggested_delivery_uom||d.effective_oh_uom||'').toUpperCase();
    const grid=body.querySelector('.v1-detail-metrics');if(!grid)return;
    const fields=[
      ['ORDERING OH USED',val(d,'ordering_oh_used'),'ordering_oh_used'],
      ['PRE-DELIVERY USAGE',val(d,'forecast_usage_before_delivery'),'forecast_usage_before_delivery'],
      ['PROJECTED OH @ DELIVERY',val(d,'projected_oh_at_delivery'),'projected_oh_at_delivery'],
      ['USABLE OH @ DELIVERY',val(d,'usable_oh_at_delivery'),'usable_oh_at_delivery'],
      ['COVERAGE USAGE',val(d,'forecast_coverage_usage'),'forecast_coverage_usage'],
      ['REQUESTED COVERAGE',val(d,'forecast_requested_coverage_usage'),'forecast_requested_coverage_usage'],
      ['PRE-DELIVERY STOCKOUT',val(d,'pre_delivery_stockout_qty'),'pre_delivery_stockout_qty']
    ];
    for(const [label,value,key] of fields){
      if(value===null||grid.querySelector(`[data-evidence-key="${key}"]`))continue;
      grid.insertAdjacentHTML('beforeend',metric(label,value,uom,key));
    }
    body.dataset.orderEvidenceBridged='1';
  }
  const mo=new MutationObserver(()=>requestAnimationFrame(patch));
  mo.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','data-order-family-polished']});
  document.addEventListener('click',()=>setTimeout(patch,0),true);
})();
</script>
'''


def polish_order_evidence_bridge_html(html: str) -> str:
    if 'yipmanV1OrderEvidenceBridge' in html:
        return html
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
