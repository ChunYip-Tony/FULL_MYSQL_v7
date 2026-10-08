from __future__ import annotations

"""Add direct operational actions to Stock Flow family cards.

Stock Flow answers which Families need attention. The next tap should take the
manager to the workflow that resolves that signal, rather than forcing a trip
through the bottom navigation or a second manual search.
"""

_STYLE = r'''<style id="yipmanV1StockFlowActionsStyle">
.v1-flow-actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.v1-flow-actions button{min-height:44px;border:1px solid #3b5262;border-radius:11px;background:#13212b;color:#dce9f2;font-size:11px;font-weight:1000}.v1-flow-actions button.primary{background:#1f5f8f;border-color:#4b8fbd;color:#fff}.v1-flow-actions button:active{transform:scale(.985)}
</style>'''

_SCRIPT = r'''<script id="yipmanV1StockFlowActionsScript">
(()=>{'use strict';
  const escSel=v=>window.CSS?.escape?CSS.escape(String(v)):String(v).replace(/["\\]/g,'\\$&');
  function openPage(page){
    const target=document.querySelector('[data-nav="'+escSel(page)+'"]')||document.querySelector('[data-open="'+escSel(page)+'"]');
    target?.click();
  }
  function familyName(card){return String(card.querySelector('.urgent-name')?.textContent||'').trim()}
  function quickCheck(card){
    const name=familyName(card);openPage('quick');
    const input=document.getElementById('quickSearch');
    if(!input)return;
    input.value=name;input.dispatchEvent(new Event('input',{bubbles:true}));input.focus();
  }
  function enhance(){
    document.querySelectorAll('#urgentList .v1-flow-card').forEach(card=>{
      if(card.querySelector('.v1-flow-actions'))return;
      const row=document.createElement('div');row.className='v1-flow-actions';
      row.innerHTML='<button type="button" class="primary" data-flow-action="ordering">CHECK ORDERING</button><button type="button" data-flow-action="quick">QUICK CHECK</button>';
      row.querySelector('[data-flow-action="ordering"]').onclick=e=>{e.stopPropagation();openPage('ordering')};
      row.querySelector('[data-flow-action="quick"]').onclick=e=>{e.stopPropagation();quickCheck(card)};
      card.appendChild(row);
    });
  }
  const boot=()=>{enhance();const box=document.getElementById('urgentList');if(box)new MutationObserver(enhance).observe(box,{childList:true})};
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',boot):setTimeout(boot,0);
})();
</script>'''


def polish_stock_flow_actions_html(html: str) -> str:
    if 'yipmanV1StockFlowActionsScript' in html:
        return html
    return html.replace('</head>', _STYLE + '</head>', 1).replace('</body>', _SCRIPT + '</body>', 1)
