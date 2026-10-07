from __future__ import annotations

"""RC-only display guard for invalid/missing price values.

The exact-mock shell historically used Number(null), which becomes 0 in JavaScript.
That can make a missing suggestion render as $0.00. This guard prevents any missing
or invalid zero price from being presented as an actionable price recommendation.
"""

_SCRIPT = r'''
<script id="yipmanV1ZeroPriceGuardScript">
(function(){
  'use strict';
  const zeroMoney = value => /^\s*\$\s*0(?:\.0+)?\s*$/i.test(String(value||''));

  function safeText(el, value){
    if(el && el.textContent !== value) el.textContent = value;
  }

  function sanitizeUrgentCard(card){
    if(!card) return;
    const action = card.querySelector('.urgent-action');
    if(action && /\$\s*0(?:\.0+)?\b/i.test(action.textContent||'')){
      const original=String(action.textContent||'');
      const replacement=original.replace(/\$\s*0(?:\.0+)?\b/ig,'REVIEW');
      safeText(action,replacement);
      card.dataset.invalidZeroPrice='true';
    }
    card.querySelectorAll('.metric').forEach(metric=>{
      const label=String(metric.querySelector('b')?.textContent||'').trim().toUpperCase();
      const value=metric.querySelector('span');
      if(!value || !zeroMoney(value.textContent)) return;
      if(label==='SUGGEST' || label==='CURRENT' || label==='PRICE'){
        safeText(value,'—');
        value.title='No valid positive price returned';
      }
    });
  }

  function sanitizePriceCard(card){
    if(!card) return;
    const action=card.querySelector('.action-value');
    if(action && /\$\s*0(?:\.0+)?\b/i.test(action.textContent||'')){
      const type=String(card.querySelector('.pill')?.textContent||'PRICE').trim().toUpperCase();
      safeText(action,'REVIEW '+(type||'PRICE')+' · NO VALID PRICE');
      card.dataset.invalidZeroPrice='true';
    }
    card.querySelectorAll('.stat').forEach(stat=>{
      const label=String(stat.querySelector('b')?.textContent||'').trim().toUpperCase();
      const value=stat.querySelector('span');
      if(!value || !zeroMoney(value.textContent)) return;
      if(/CURRENT|SUGGEST|PRICE/.test(label)){
        safeText(value,'—');
        value.title='No valid positive price returned';
      }
    });
  }

  function sanitizeDetail(root){
    if(!root) return;
    root.querySelectorAll('.v1-detail-metrics>div').forEach(box=>{
      const label=String(box.querySelector('b')?.textContent||'').trim().toUpperCase();
      const value=box.querySelector('span');
      if(value && zeroMoney(value.textContent) && /CURRENT|PRICE|SUGGEST/.test(label)) safeText(value,'—');
    });
    const decision=root.querySelector('.v1-detail-decision strong');
    if(decision && /\$\s*0(?:\.0+)?\b/i.test(decision.textContent||'')){
      safeText(decision,String(decision.textContent||'').replace(/\$\s*0(?:\.0+)?\b/ig,'REVIEW'));
    }
  }

  function sanitizeAll(){
    document.querySelectorAll('#urgentList .urgent-card').forEach(sanitizeUrgentCard);
    document.querySelectorAll('#priceQueue .direct-card,#priceQueue .family-card').forEach(sanitizePriceCard);
    sanitizeDetail(document.getElementById('v1DetailBody'));
  }

  let scheduled=false;
  function schedule(){
    if(scheduled) return;
    scheduled=true;
    requestAnimationFrame(()=>{scheduled=false;sanitizeAll();});
  }

  const observer=new MutationObserver(schedule);
  observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',schedule,{once:true});
  else schedule();
})();
</script>
'''


def guard_zero_price_html(html: str) -> str:
    if 'yipmanV1ZeroPriceGuardScript' in html:
        return html
    return html.replace('</body>', _SCRIPT + '</body>', 1)
