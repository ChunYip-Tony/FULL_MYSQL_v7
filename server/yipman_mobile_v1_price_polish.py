from __future__ import annotations

"""RC-only Price Review polish for the standalone exact-mock Mobile V1 shell."""

_STYLE = r'''
<style id="yipmanV1PriceMockPolish">
#price{padding-top:5px}
#price .price-head{padding:0 0 4px!important}
#price .price-head-row{gap:6px!important}
#price .title{font-size:25px!important;line-height:1!important}
#price .sub{font-size:11px!important;margin-top:2px!important}
#price .searchbtn{width:40px!important;height:36px!important;border-radius:10px!important;font-size:19px!important}
#price .price-summary{gap:4px!important;margin-top:5px!important}
#price .price-summary div{height:34px!important;border-radius:10px!important;gap:3px!important;padding:0 3px!important}
#price .price-summary b{font-size:17px!important}
#price .price-summary span{font-size:9px!important}
#price .v1-price-filter-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin-top:5px}
#price .v1-price-filter-grid .filterbtn{min-height:34px!important;border-radius:11px!important;font-size:11px!important;padding:3px 4px!important;white-space:nowrap}
#price .v1-price-filter-grid .filterbtn[data-pf="240249"],#price .v1-price-filter-grid .filterbtn[data-pf="245"]{background:#17261a;border-color:#395e3d}
#price .v1-price-filter-grid .filterbtn.active{background:#245a87!important;border-color:#4c91cf!important;color:#fff!important}
#price .filter2,#price .filter4{margin:0!important}
#price .price-queue{margin-top:6px!important}
#price .direct-card{padding:9px 10px!important;margin-bottom:7px!important;border-radius:14px!important}
#price .direct-card>.row{gap:7px!important;align-items:flex-start!important}
#price .result-name{font-size:21px!important;line-height:1.03!important}
#price .action-meta{font-size:11px!important;margin-top:3px!important;line-height:1.2!important}
#price .pill{min-height:22px!important;padding:3px 7px!important;font-size:10px!important}
#price .actionbox{margin-top:6px!important;padding:8px 9px!important;border-radius:11px!important}
#price .action-label{font-size:9px!important}
#price .action-value{font-size:22px!important;line-height:1.05!important}
#price .why{font-size:12px!important;line-height:1.28!important;margin-top:4px!important;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}
#price .summary3{gap:4px!important;margin-top:6px!important}
#price .stat{padding:6px 4px!important;border-radius:9px!important;min-height:51px!important;display:flex!important;flex-direction:column!important;justify-content:center!important}
#price .stat b{font-size:8px!important}
#price .stat span{font-size:13px!important;margin-top:2px!important}
#price .ignore{min-height:37px!important;margin-top:6px!important;border-radius:10px!important;font-size:14px!important}
#priceSearchWrap{margin-top:5px!important}
#price .price-progress+ .ignore{margin-top:5px!important}
#price .price-progress-details,#price .price-progress-details *{touch-action:manipulation}
@media(max-width:390px){
 #price .title{font-size:23px!important}
 #price .v1-price-filter-grid .filterbtn{font-size:10px!important}
 #price .result-name{font-size:20px!important}
 #price .action-value{font-size:21px!important}
}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1PriceMockPolishScript">
(function(){
  'use strict';
  let decorating=false;
  let queued=false;

  function compactFilters(){
    const price=document.getElementById('price');
    if(!price||price.querySelector('.v1-price-filter-grid'))return;
    const buttons=[...price.querySelectorAll('[data-pf]')];
    if(!buttons.length)return;
    const grid=document.createElement('div');
    grid.className='v1-price-filter-grid';
    const first=buttons[0];
    const parent=first.closest('.filter2,.filter4')||first.parentElement;
    if(parent)parent.before(grid);
    buttons.forEach(b=>grid.appendChild(b));
    price.querySelectorAll('.filter2,.filter4').forEach(w=>{if(!w.querySelector('[data-pf]'))w.style.display='none'});
  }

  function decoratePriceCards(){
    if(decorating) return;
    decorating=true;
    try{
      compactFilters();
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

  // Expanding test details should not open the whole UPC Action Detail.
  document.addEventListener('click',function(e){
    if(e.target.closest('.price-progress-details'))e.stopPropagation();
  },true);

  const q=document.getElementById('priceQueue');
  if(q){
    const mo=new MutationObserver(scheduleDecorate);
    mo.observe(q,{childList:true,subtree:true});
  }
  compactFilters();
  decoratePriceCards();
})();
</script>
'''


def polish_price_html(html: str) -> str:
    if 'yipmanV1PriceMockPolish' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    html = html.replace('</body>', _SCRIPT + '</body>', 1)
    return html
