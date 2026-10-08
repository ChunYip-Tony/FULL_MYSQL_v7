from __future__ import annotations

"""RC-only Price Review polish for the standalone exact-mock Mobile V1 shell."""

_STYLE = r'''
<style id="yipmanV1PriceMockPolish">
#price{padding-top:4px}
#price .price-head{padding:0 0 3px!important}
#price .price-head-row{gap:6px!important}
#price .title{font-size:23px!important;line-height:1!important}
#price .sub{font-size:10px!important;margin-top:1px!important}
#price .searchbtn{width:40px!important;height:36px!important;border-radius:10px!important;font-size:18px!important}
#price .price-summary{gap:4px!important;margin-top:4px!important}
#price .price-summary div{height:33px!important;border-radius:9px!important;gap:4px!important}
#price .price-summary b{font-size:16px!important}
#price .price-summary span{font-size:8px!important}
#price .filter2{gap:4px!important;margin-top:4px!important}
#price .filter4{gap:4px!important;margin-top:4px!important}
#price .filterbtn{min-height:30px!important;font-size:10px!important;padding:3px 5px!important}
#price .price-queue{margin-top:6px!important}
#price .direct-card{padding:9px 10px!important;margin-bottom:7px!important;border-radius:14px!important}
#price .direct-card>.row.space{gap:7px!important;align-items:flex-start!important}
#price .result-name{font-size:18px!important;line-height:1.02!important}
#price .action-meta{font-size:11px!important;margin-top:2px!important;line-height:1.15!important}
#price .pill{min-height:22px!important;padding:3px 7px!important;font-size:9px!important}
#price .actionbox{margin-top:5px!important;padding:7px 8px!important;border-radius:10px!important}
#price .action-label{font-size:8px!important}
#price .action-value{font-size:20px!important;line-height:1.05!important;margin-top:2px!important}
#price .actionbox .why{font-size:10px!important;line-height:1.2!important;margin-top:3px!important;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
#price .summary3{gap:4px!important;margin-top:5px!important}
#price .stat{padding:5px 4px!important;border-radius:9px!important;min-height:49px!important;display:flex!important;flex-direction:column!important;justify-content:center!important}
#price .stat b{font-size:7px!important}
#price .stat span{font-size:12px!important;margin-top:2px!important}
#price .ignore{min-height:36px!important;height:36px!important;margin-top:6px!important;border-radius:10px!important;font-size:12px!important}
#priceSearchWrap{margin-top:4px!important}
#priceSearchWrap .search{min-height:42px!important}
@media(max-width:390px){#price .title{font-size:21px!important}#price .filterbtn{font-size:9px!important}#price .result-name{font-size:17px!important}}
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
