from __future__ import annotations

"""RC-only ordering presentation cleanup.

User-facing goals:
- editable delivery dates should appear once, with the weekday chip in the label
  instead of repeating the full date underneath the native date input
- Receiving Article numbers are operationally important and should be visually
  stronger than surrounding Family/metadata text
- preserve existing ordering calculations, date edit behavior and live refresh
"""

_STYLE = r'''
<style id="yipmanV1OrderingDisplayCompactStyle">
/* One date display only: keep the native editable date + weekday chip in label. */
#regular .date-weekday-hint,
#regular .order-date-day,
#orderDateContext .date-weekday-hint,
#orderDateContext .order-date-day{
  display:none!important;
}
#regular .field,
#orderDateContext .order-date-field{margin-bottom:0!important}
#regular .card:first-of-type .card-body{padding-bottom:10px!important}

/* Recommended / receiving article identity is a primary ordering identifier. */
.v1-receiving-emphasis{
  display:inline-block;
  font-size:18px!important;
  line-height:1.05!important;
  font-weight:1000!important;
  letter-spacing:.012em;
  color:#f3df9a!important;
  background:#2b2518;
  border:1px solid #6b5930;
  border-radius:7px;
  padding:3px 6px;
  margin:1px 2px;
  vertical-align:baseline;
}
.v1-detail-id>div.v1-receiving-cell span{
  font-size:18px!important;
  font-weight:1000!important;
  color:#f3df9a!important;
}
@media(max-width:390px){
  .v1-receiving-emphasis{font-size:17px!important;padding:3px 5px!important}
}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1OrderingDisplayCompactScript">
(()=>{
  'use strict';
  let queued=false;
  const receivingRe=/(Receiving(?:\s+Article)?\s*#?\s*)([0-9]{4,14})/gi;

  function wrapReceiving(node){
    if(!node || node.parentElement?.closest('.v1-receiving-emphasis'))return;
    const raw=node.nodeValue||'';
    receivingRe.lastIndex=0;
    if(!receivingRe.test(raw))return;
    receivingRe.lastIndex=0;
    const frag=document.createDocumentFragment();
    let last=0,m;
    while((m=receivingRe.exec(raw))){
      if(m.index>last)frag.append(document.createTextNode(raw.slice(last,m.index)));
      frag.append(document.createTextNode(m[1]||'Receiving '));
      const span=document.createElement('span');
      span.className='v1-receiving-emphasis';
      span.textContent=m[2]||'';
      frag.append(span);
      last=receivingRe.lastIndex;
    }
    if(last<raw.length)frag.append(document.createTextNode(raw.slice(last)));
    node.replaceWith(frag);
  }

  function polish(root=document){
    const selectors=['#regularResults .card-sub','#urgentList .urgent-meta','.v1-order-extra','.v1-detail-note'];
    selectors.forEach(sel=>root.querySelectorAll?.(sel).forEach(el=>{
      const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
      const nodes=[];let n;while((n=walker.nextNode()))nodes.push(n);
      nodes.forEach(wrapReceiving);
    }));

    root.querySelectorAll?.('.v1-detail-id>div').forEach(cell=>{
      const label=String(cell.querySelector('b')?.textContent||'').trim().toUpperCase();
      cell.classList.toggle('v1-receiving-cell',label==='RECEIVING'||label==='RECEIVING ARTICLE');
    });
  }

  function schedule(){
    if(queued)return;queued=true;
    requestAnimationFrame(()=>{queued=false;polish(document)});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
})();
</script>
'''


def polish_ordering_display_compact_html(html: str) -> str:
    if 'yipmanV1OrderingDisplayCompactStyle' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    return html.replace('</body>', _SCRIPT + '</body>', 1)
