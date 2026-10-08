from __future__ import annotations

"""Fill Family 7D MVT in Mobile V1 Family detail from live Family evidence."""

_SCRIPT = r'''
<script id="yipmanV1FamilyMvtFixScript">
(()=>{
  'use strict';
  const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=v=>{const x=num(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:1})};
  const text=(el,sel)=>String(el?.querySelector(sel)?.textContent||'').trim();
  let token=0;
  function familyOf(body){for(const c of body.querySelectorAll('.v1-detail-id>div')){if(/^FAMILY$/i.test(text(c,'b')))return text(c,'span')}return''}
  function metric(body,label){return [...body.querySelectorAll('.v1-detail-metrics>div')].find(x=>text(x,'b').toUpperCase()===label)}
  async function patch(){
    const overlay=document.getElementById('v1DetailOverlay'),body=document.getElementById('v1DetailBody');if(!overlay?.classList.contains('open')||!body)return;
    const m=metric(body,'FAMILY 7D MVT');if(!m||!/^[-—\s]*$/.test(text(m,'span')))return;
    const family=familyOf(body);if(!family||family==='—'||body.dataset.familyMvtLoading===family)return;body.dataset.familyMvtLoading=family;const my=++token;
    try{const r=await fetch('/v1/app/v2/family/'+encodeURIComponent(family),{credentials:'same-origin',cache:'no-store'});if(!r.ok)return;const d=await r.json();if(my!==token||!overlay.classList.contains('open'))return;const fs=d?.family_sales_7d||{};let qty=num(fs.quantity??fs.sold_quantity),avg=num(fs.velocity_per_supported_day),days=num(fs.supported_day_count);if(qty===null&&avg!==null&&days!==null)qty=avg*days;const uom=String(fs.uom||'').trim().toUpperCase();if(qty!==null){const span=m.querySelector('span');if(span)span.textContent=fmt(qty)+(uom?' '+uom:'')}}catch(_){ }finally{delete body.dataset.familyMvtLoading}
  }
  const kick=()=>{requestAnimationFrame(patch);setTimeout(patch,120)};
  new MutationObserver(kick).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});document.addEventListener('click',kick,true);
})();
</script>
'''


def polish_family_mvt_fix_html(html: str) -> str:
    if 'yipmanV1FamilyMvtFixScript' in html:
        return html
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
