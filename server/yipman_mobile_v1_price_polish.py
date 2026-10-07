from __future__ import annotations

"""RC-only Price Review polish for the standalone exact-mock Mobile V1 shell."""

_STYLE = r'''
<style id="yipmanV1PriceMockPolish">
#price{padding-top:8px}
#price .price-head{padding:0 0 5px!important}
#price .price-head-row{gap:7px!important}
#price .title{font-size:24px!important;line-height:1!important}
#price .sub{font-size:9px!important;margin-top:2px!important}
#price .searchbtn{width:42px!important;height:38px!important;border-radius:11px!important;font-size:19px!important}
#price .price-summary{gap:5px!important;margin-top:6px!important}
#price .price-summary div{height:37px!important;border-radius:11px!important;gap:4px!important}
#price .price-summary b{font-size:15px!important}
#price .price-summary span{font-size:7px!important}
#price .filter2{gap:5px!important;margin-top:6px!important}
#price .filter4{gap:5px!important;margin-top:5px!important}
#price .filterbtn{min-height:32px!important;font-size:9px!important;padding:4px 5px!important}
#price .price-queue{margin-top:8px!important}
#price .direct-card{padding:12px!important;margin-bottom:10px!important;border-radius:17px!important}
#price .result-name{font-size:19px!important;line-height:1.05!important}
#price .action-meta{font-size:9px!important;margin-top:3px!important}
#price .pill{min-height:24px!important;padding:4px 8px!important;font-size:8px!important}
#price .actionbox{margin-top:8px!important;padding:10px!important}
#price .action-value{font-size:21px!important}
#price .why{font-size:10px!important;line-height:1.3!important}
#price .summary3{gap:5px!important;margin-top:8px!important}
#price .stat{padding:7px 5px!important;border-radius:10px!important}
#price .stat b{font-size:6.5px!important}
#price .stat span{font-size:11px!important}
#price .ignore{min-height:44px!important;margin-top:8px!important}
#priceSearchWrap{margin-top:6px!important}
@media(max-width:390px){#price .title{font-size:22px!important}#price .filterbtn{font-size:8.5px!important}}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1PriceMockPolishScript">
(function(){
  'use strict';
  let decorating=false;
  let queued=false;

  function decoratePriceCards(){
    if(decorating) return;
    decorating=true;
    try{
      const cards=[...document.querySelectorAll('#price .direct-card')];
      for(const card of cards){
        const currentEl=[...card.querySelectorAll('.stat')].find(x=>/CURRENT/i.test(x.textContent||''))?.querySelector('span');
        const actionEl=card.querySelector('.action-value');
        if(!currentEl||!actionEl) continue;
        const current=Number((currentEl.textContent||'').replace(/[^0-9.\-]/g,''));
        const match=(actionEl.textContent||'').match(/\$([0-9]+(?:\.[0-9]+)?)/);
        const suggested=match?Number(match[1]):NaN;
        const type=(card.querySelector('.pill')?.textContent||'').trim().toUpperCase();
        if(!Number.isFinite(current)||!Number.isFinite(suggested)||Math.abs(current-suggested)>=0.25) continue;
        let desired='';
        if(type==='TPR') desired='KEEP TPR $'+suggested.toFixed(2);
        else if(type==='REG') desired='KEEP REG $'+suggested.toFixed(2);
        if(desired && actionEl.textContent!==desired) actionEl.textContent=desired;
      }
    }finally{
      decorating=false;
    }
  }

  function scheduleDecorate(){
    if(queued) return;
    queued=true;
    requestAnimationFrame(function(){
      queued=false;
      decoratePriceCards();
    });
  }

  const q=document.getElementById('priceQueue');
  if(q){
    const mo=new MutationObserver(scheduleDecorate);
    mo.observe(q,{childList:true,subtree:true});
    decoratePriceCards();
  }
})();
</script>
'''


def polish_price_html(html: str) -> str:
    if 'yipmanV1PriceMockPolish' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    html = html.replace('</body>', _SCRIPT + '</body>', 1)
    return html
