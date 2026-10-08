from __future__ import annotations

"""Compact Quick-home Stock Flow presentation.

Keeps Selling MVT vs Receipt Qty visible on every card while moving secondary
flow evidence behind an optional Details expansion. The objective is to show
multiple families per mobile viewport without reducing the core numbers.
"""

_STYLE = r'''
<style id="yipmanV1StockFlowCompactStyle">
#quick .top{padding-top:2px!important;padding-bottom:5px!important}
#quick .v1-home-switch{gap:5px!important;margin:0 0 5px!important}
#quick .v1-home-switch button{min-height:32px!important;border-radius:10px!important;font-size:11px!important}
#quick .v1-flow-summary{gap:4px!important;margin:0 0 5px!important}
#quick .v1-flow-summary div{padding:4px 3px!important;border-radius:9px!important}
#quick .v1-flow-summary b{font-size:15px!important;line-height:1!important}
#quick .v1-flow-summary span{font-size:7px!important;margin-top:1px!important}
#quick .v1-flow-controls{gap:4px!important;margin-bottom:5px!important}
#quick .v1-flow-control-row{gap:5px!important;grid-template-columns:150px minmax(0,1fr)!important}
#quick .v1-flow-window{gap:3px!important}
#quick .v1-flow-window button{height:31px!important;min-width:0!important;border-radius:9px!important;font-size:10px!important}
#quick .v1-flow-sort{height:31px!important;border-radius:9px!important;padding:0 7px!important;font-size:10px!important}
#quick .v1-flow-caption{padding:4px 7px!important;border-radius:8px!important;font-size:9px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
#quick #urgentList{gap:6px!important}
#quick .v1-flow-card{padding:8px 9px 8px!important;border-radius:14px!important;border-left-width:5px!important}
#quick .v1-flow-card .urgent-top{gap:6px!important;align-items:center!important}
#quick .v1-flow-card .urgent-name{font-size:18px!important;line-height:1.02!important}
#quick .v1-flow-card .urgent-meta{font-size:8px!important;margin-top:2px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
#quick .v1-flow-card .pill{min-height:22px!important;padding:3px 7px!important;font-size:7.5px!important}
#quick .v1-flow-action-row{margin-top:5px!important;gap:5px!important}
#quick .v1-flow-action{font-size:15px!important;line-height:1.05!important}
#quick .v1-flow-diff{padding:3px 6px!important;font-size:10px!important}
#quick .v1-flow-compare{gap:5px!important;margin-top:6px!important}
#quick .v1-flow-mainmetric{padding:6px 5px!important;border-radius:9px!important}
#quick .v1-flow-mainmetric b{font-size:7px!important}
#quick .v1-flow-mainmetric strong{margin-top:2px!important;font-size:16px!important;line-height:1!important}
#quick .v1-flow-grid{grid-template-columns:1fr 1fr!important;gap:5px!important;margin-top:5px!important}
#quick .v1-flow-metric{padding:5px!important;border-radius:9px!important}
#quick .v1-flow-metric b{font-size:7px!important}
#quick .v1-flow-metric strong{font-size:12px!important;margin-top:1px!important;line-height:1.05!important}
/* Keep inventory position + run-rate visible; move duplicate comparison details behind Details. */
#quick .v1-flow-card:not(.expanded) .v1-flow-grid .v1-flow-metric:nth-child(1),
#quick .v1-flow-card:not(.expanded) .v1-flow-grid .v1-flow-metric:nth-child(2),
#quick .v1-flow-card:not(.expanded) .v1-flow-reason,
#quick .v1-flow-card:not(.expanded) .v1-flow-range{display:none!important}
#quick .v1-flow-card:not(.expanded) .v1-flow-grid{grid-template-columns:1fr 1fr!important}
#quick .v1-flow-reason{margin-top:5px!important;font-size:10px!important;line-height:1.2!important}
#quick .v1-flow-range{margin-top:4px!important;font-size:8px!important;line-height:1.2!important}
#quick .v1-flow-more{width:100%;min-height:27px;margin-top:5px;border:1px solid #2e4050;border-radius:8px;background:#0e171e;color:#91a4b2;font-size:8px;font-weight:1000;letter-spacing:.02em}
#quick .v1-flow-card.expanded .v1-flow-more{color:#b9d8ee;border-color:#3b617d}
@media(max-width:390px){
  #quick .v1-flow-control-row{grid-template-columns:138px minmax(0,1fr)!important}
  #quick .v1-flow-sort{font-size:9px!important}
  #quick .v1-flow-card .urgent-name{font-size:17px!important}
  #quick .v1-flow-mainmetric strong{font-size:15px!important}
}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1StockFlowCompactScript">
(()=>{
  'use strict';
  let queued=false;
  function decorate(){
    queued=false;
    document.querySelectorAll('#quick .v1-flow-card').forEach(card=>{
      if(card.dataset.compactBound==='1')return;
      card.dataset.compactBound='1';
      const btn=document.createElement('button');
      btn.type='button';
      btn.className='v1-flow-more';
      btn.textContent='DETAILS ▾';
      btn.addEventListener('click',e=>{
        e.preventDefault();e.stopPropagation();
        const open=card.classList.toggle('expanded');
        btn.textContent=open?'HIDE DETAILS ▴':'DETAILS ▾';
      });
      card.appendChild(btn);
    });
  }
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(decorate)}
  const root=document.getElementById('urgentList');
  if(root)new MutationObserver(schedule).observe(root,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target.closest('[data-flow-days],#v1FlowSort,[data-home-mode]'))setTimeout(schedule,0)},true);
  schedule();
})();
</script>
'''


def polish_stock_flow_compact_html(html: str) -> str:
    if 'yipmanV1StockFlowCompactScript' in html:
        return html
    html = html.replace('</head>', _STYLE + '\n</head>', 1)
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
