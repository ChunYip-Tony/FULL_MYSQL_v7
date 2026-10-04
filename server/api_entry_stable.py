from __future__ import annotations

import api_entry as _base
import api as _api

app = _base.app
_original_yipman_html = _api.yipman_html

_STABILITY_PATCH = r'''
<style id="ordering-v477-stability-css">
@media (min-width:760px){
  #ydesk #yd-order .split{grid-template-columns:minmax(0,1fr) minmax(310px,360px)!important;gap:10px!important;align-items:start!important}
  #ydesk #yd-order .split>div{min-width:0!important}
  #ydesk #yd-order #ydOrderMain{min-width:0;min-height:420px}
  #ydesk #yd-order #ydOrderAnalysis{min-width:0;max-width:360px;width:100%;overflow:hidden}
  #ydesk #yd-order #ydOrderAnalysis .card{min-width:0;overflow:hidden}
  #ydesk #yd-order #ydOrderAnalysis .kv{grid-template-columns:minmax(105px,.75fr) minmax(0,1.25fr)!important}
  #ydesk #yd-order #ydOrderAnalysis .kv span{min-width:0;overflow-wrap:anywhere;word-break:break-word}
  #ydesk #yd-order .ordtop{grid-template-columns:minmax(180px,.9fr) minmax(180px,.9fr) minmax(250px,1.2fr)!important}
  #ydesk #yd-order .promo476{min-width:0}
  #ydesk #yd-order .promo476 .grid2{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media (min-width:760px) and (max-width:1220px){
  #ydesk #yd-order .split{grid-template-columns:minmax(0,1fr) 300px!important}
  #ydesk #yd-order #ydOrderAnalysis{max-width:300px}
  #ydesk #yd-order .ordtop{grid-template-columns:1fr 1fr!important}
  #ydesk #yd-order .ordtop .datebox:last-child{grid-column:1/-1}
}
</style>
<script id="ordering-v477-stability-js">
(()=>{
  if(!window.matchMedia('(min-width:760px)').matches)return;
  let desiredMode='regular', recoverTimer=null, lastRecover=0;
  const q=(s,r=document)=>r.querySelector(s);
  const activeMode=()=>q('#yd-order [data-om].active')?.dataset.om||desiredMode;
  const promoAside=()=>'<div class="card"><div class="cardhead"><h3>Promotion Ordering</h3><span class="badge purple">PROMOTION MODE</span></div><div class="cardbody"><div class="note blue">Select a saved promotion, add items manually, or paste a promotion form. Promotion calculations stay isolated from Regular Order results.</div></div></div>';
  function keepLayoutStable(){
    const order=q('#yd-order'), main=q('#ydOrderMain'), aside=q('#ydOrderAnalysis');
    if(!order||!main)return;
    const mode=activeMode(); desiredMode=mode;
    if(mode!=='promotion')return;
    if(aside && !aside.dataset.promoStable){aside.dataset.promoStable='1';aside.innerHTML=promoAside()}
    if(main.querySelector('.promo476'))return;
    const text=(main.textContent||'').trim();
    if(/Loading promotion lists/i.test(text))return;
    const staleRegular=/Calculating family order coverage|Coming Delivery Suggestions|Ordering data|Family demand|Select an order candidate/i.test(text);
    if(!staleRegular && /Promotion Ordering/i.test(text))return;
    clearTimeout(recoverTimer);
    recoverTimer=setTimeout(()=>{
      if(activeMode()!=='promotion')return;
      const now=Date.now(); if(now-lastRecover<350)return; lastRecover=now;
      const btn=q('#yd-order [data-om="promotion"]');
      if(btn)btn.click();
    },80);
  }
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('#yd-order [data-om]');
    if(!b)return;
    desiredMode=b.dataset.om;
    const aside=q('#ydOrderAnalysis');
    if(aside){delete aside.dataset.promoStable;if(desiredMode==='promotion'){aside.dataset.promoStable='1';aside.innerHTML=promoAside()}}
    setTimeout(keepLayoutStable,0);setTimeout(keepLayoutStable,250);setTimeout(keepLayoutStable,900);
  },true);
  new MutationObserver(keepLayoutStable).observe(document.documentElement,{subtree:true,childList:true});
  window.addEventListener('resize',keepLayoutStable,{passive:true});
  setInterval(keepLayoutStable,1000);
})();
</script>
'''


def _stable_yipman_html(version: str = "") -> str:
    html = _original_yipman_html(version)
    return html.replace("</body>", _STABILITY_PATCH + "</body>", 1)

_api.yipman_html = _stable_yipman_html
