from __future__ import annotations

"""Fill Family 7D MVT in Mobile V1 Family detail from canonical 251-252 evidence."""

from yipman_mobile_v1_family_enrichment import polish_family_enrichment_html

_SCRIPT = r'''
<script id="yipmanV1FamilyMvtFixScript">
(()=>{
  'use strict';
  const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=v=>{const x=num(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:1})};
  const text=(el,sel)=>String(el?.querySelector(sel)?.textContent||'').trim();
  let token=0,cache=null;
  function familyOf(body){for(const c of body.querySelectorAll('.v1-detail-id>div')){if(/^FAMILY$/i.test(text(c,'b')))return text(c,'span')}return''}
  function metric(body,label){return [...body.querySelectorAll('.v1-detail-metrics>div')].find(x=>text(x,'b').toUpperCase()===label)}
  async function data(){if(cache)return cache;const r=await fetch('/app/yipman-v1-rc/api/stock-flow?days=7&limit=120&_ts='+Date.now(),{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw new Error('Stock Flow unavailable');cache=await r.json();return cache}
  async function patch(){
    const overlay=document.getElementById('v1DetailOverlay'),body=document.getElementById('v1DetailBody');if(!overlay?.classList.contains('open')||!body)return;
    const family=familyOf(body);if(!family||family==='—'||body.dataset.familyMvtLoading===family)return;
    const m=metric(body,'FAMILY 7D MVT'),a=metric(body,'AVG / DAY'),d=metric(body,'VALID MVT DAYS');if(!m&&!a&&!d)return;
    body.dataset.familyMvtLoading=family;const my=++token;
    try{const flow=await data();if(my!==token||!overlay.classList.contains('open'))return;const row=(flow.rows||[]).find(x=>String(x.family_article||x.family_id||'')===String(family));if(!row)return;const qty=num(row.family_group_movement_qty),avg=num(row.family_group_avg_qty_day),days=num(row.supported_movement_day_count),uom=String(row.family_group_movement_uom||'').trim().toUpperCase();if(m&&qty!==null){const span=m.querySelector('span');if(span)span.textContent=fmt(qty)+(uom?' '+uom:'')}if(a&&avg!==null){const span=a.querySelector('span');if(span)span.textContent=fmt(avg)+(uom?' '+uom+'/day':' /day')}if(d&&days!==null){const span=d.querySelector('span');if(span)span.textContent=String(days)}}catch(_){ }finally{delete body.dataset.familyMvtLoading}
  }
  const kick=()=>{requestAnimationFrame(patch);setTimeout(patch,120)};
  new MutationObserver(kick).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});document.addEventListener('click',kick,true);
})();
</script>
'''


def polish_family_mvt_fix_html(html: str) -> str:
    if 'yipmanV1FamilyMvtFixScript' not in html:
        html = html.replace('</body>', _SCRIPT + '\n</body>', 1)
    return polish_family_enrichment_html(html)
