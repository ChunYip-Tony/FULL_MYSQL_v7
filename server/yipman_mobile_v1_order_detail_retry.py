from __future__ import annotations

"""Retry guard for Family ordering detail enrichment.

The shared detail body is reused between suggestion cards. The Family-order
polisher marks that body as already enriched; without resetting that marker a
later ORDER detail can reopen with the generic UPC-centric shell. This layer
resets the per-open state before an order card opens and makes urgent ORDER
cards visible to the existing Family-order capture logic.
"""

_SCRIPT = r'''
<script id="yipmanV1OrderDetailRetryHotfix">
(()=>{
  'use strict';
  function text(el,sel){return String(el?.querySelector(sel)?.textContent||'').trim()}
  function orderCard(card){
    if(!card)return false;
    const action=(text(card,'.urgent-action')||text(card,'.order-main')||text(card,'.action-value')||'').toUpperCase();
    return /^(ORDER|NO ORDER)\b/.test(action) || /\bORDER\s+\d/.test(String(card.innerText||'').toUpperCase());
  }
  function resetDetailState(){
    const body=document.getElementById('v1DetailBody');
    if(!body)return;
    delete body.dataset.orderFamilyPolished;
    delete body.dataset.orderFamilyKey;
  }
  function prepare(e){
    const target=e?.target;
    if(!(target instanceof Element))return;
    const card=target.closest('#regularResults .card,#urgentList .urgent-card');
    if(!orderCard(card))return;
    if(card.matches('#urgentList .urgent-card'))card.classList.add('order');
    resetDetailState();
  }
  window.addEventListener('pointerdown',prepare,true);
  window.addEventListener('touchstart',prepare,true);
  window.addEventListener('mousedown',prepare,true);
  window.addEventListener('click',e=>{prepare(e);const target=e?.target;const card=target instanceof Element?target.closest('#regularResults .card,#urgentList .urgent-card'):null;if(orderCard(card))resetDetailState()},true);
})();
</script>
'''


def polish_order_detail_retry_html(html: str) -> str:
    if 'yipmanV1OrderDetailRetryHotfix' in html:
        return html
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
