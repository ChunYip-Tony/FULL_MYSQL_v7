from __future__ import annotations

"""RC-only visual hierarchy polish for UPC identity and compact card density.

User-facing rules:
- any UPC number shown in the mobile app must be visually prominent
- cards should use less vertical space without shrinking the newly enlarged text
- identity / action / metrics should read in a consistent order
"""

_STYLE = r'''
<style id="yipmanV1IdentityCompactStyle">
/* UPC identity is operationally important: make it visually distinct everywhere. */
.v1-upc-emphasis{
  display:inline-block;
  font-size:15px!important;
  line-height:1.05!important;
  font-weight:1000!important;
  letter-spacing:.015em;
  color:#dceeff!important;
  background:#142838;
  border:1px solid #35566d;
  border-radius:7px;
  padding:3px 6px;
  margin:1px 2px;
  vertical-align:baseline;
}
.v1-detail-id>div:nth-child(2) span{
  font-size:16px!important;
  font-weight:1000!important;
  color:#dceeff!important;
}

/* Compact but readable card rhythm. */
.urgent-card,.card,.direct-card,.family-card,.quick-result{
  padding:13px 14px!important;
  border-radius:17px!important;
}
.urgent-card,.card,.direct-card,.family-card{margin-bottom:10px!important}
.urgent-name,.card-title,.family-title,.result-name{line-height:1.08!important;margin-bottom:3px!important}
.urgent-meta,.card-sub,.family-sub,.action-meta,.result-meta{line-height:1.22!important;margin-top:3px!important;margin-bottom:5px!important}
.urgent-action,.order-main,.action-value{line-height:1.06!important;margin-top:7px!important;margin-bottom:4px!important}
.urgent-why,.why{margin-top:3px!important;margin-bottom:7px!important}
.metric,.stat{padding:8px 7px!important;border-radius:12px!important;min-height:0!important}
.metric b,.stat b{margin-bottom:2px!important}
.metric span,.stat span{margin-top:1px!important;line-height:1.1!important}
.ignore{min-height:48px!important;padding:8px 10px!important;margin-top:8px!important;border-radius:13px!important}
.pill{padding:6px 9px!important;line-height:1.05!important}

/* Reduce unused gaps while preserving large type. */
#urgentList,#regularResults,#priceQueue,#quickResults{gap:9px!important}
.urgent-summary,.price-summary{gap:0!important;margin-bottom:8px!important}
.urgent-summary>*,.price-summary>*{padding-top:9px!important;padding-bottom:9px!important}
.filters,.filterrow,.price-filters{gap:6px!important;margin:7px 0!important}
.filterbtn{min-height:42px!important;padding:7px 10px!important}
.metrics,.stats,.metric-grid,.stat-grid{gap:6px!important}

/* Detail page hierarchy: identity first, decision second, metrics third. */
.v1-detail-body{padding-top:8px!important}
.v1-detail-id{gap:5px!important;margin-bottom:7px!important}
.v1-detail-id>div,.v1-detail-metrics>div{padding:8px!important}
.v1-detail-decision{padding:11px!important;margin-bottom:7px!important}
.v1-detail-oh{padding:10px!important;margin-bottom:7px!important}
.v1-detail-metrics{gap:5px!important;margin-bottom:7px!important}
.v1-detail-note{padding:9px!important}

/* Search stays large but consumes less vertical chrome. */
.searchdock{padding-top:7px!important;padding-bottom:7px!important}
.searchdock input{min-height:48px!important}

@media(max-width:390px){
  .v1-upc-emphasis{font-size:14px!important;padding:3px 5px!important}
  .urgent-card,.card,.direct-card,.family-card,.quick-result{padding:12px!important}
}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1IdentityCompactScript">
(()=>{
  'use strict';
  let queued=false;
  const targets=[
    '.urgent-meta','.card-sub','.family-sub','.action-meta','.result-meta',
    '.quick-result','.v1-detail-id','.v1-detail-note','.tpr-progress-sub',
    '.price-progress-sub','.tpr-progress-meta','.price-progress-meta'
  ];
  const upcRe=/(UPC\s*#?\s*)([0-9]{4,14})/gi;

  function wrapTextNode(node){
    if(!node || node.parentElement?.closest('.v1-upc-emphasis'))return;
    const raw=node.nodeValue||'';
    upcRe.lastIndex=0;
    if(!upcRe.test(raw))return;
    upcRe.lastIndex=0;
    const frag=document.createDocumentFragment();
    let last=0,m;
    while((m=upcRe.exec(raw))){
      if(m.index>last)frag.append(document.createTextNode(raw.slice(last,m.index)));
      const span=document.createElement('span');
      span.className='v1-upc-emphasis';
      span.textContent=(m[1]||'UPC ')+(m[2]||'');
      frag.append(span);
      last=upcRe.lastIndex;
    }
    if(last<raw.length)frag.append(document.createTextNode(raw.slice(last)));
    node.replaceWith(frag);
  }

  function emphasize(root=document){
    const seen=new Set();
    targets.forEach(sel=>root.querySelectorAll?.(sel).forEach(el=>{
      if(seen.has(el))return;seen.add(el);
      const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
      const nodes=[];let n;
      while((n=walker.nextNode()))nodes.push(n);
      nodes.forEach(wrapTextNode);
    }));
  }
  function schedule(){
    if(queued)return;queued=true;
    requestAnimationFrame(()=>{queued=false;emphasize(document)});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
})();
</script>
'''


def polish_identity_compact_html(html: str) -> str:
    if 'yipmanV1IdentityCompactStyle' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    html = html.replace('</body>', _SCRIPT + '</body>', 1)
    return html
