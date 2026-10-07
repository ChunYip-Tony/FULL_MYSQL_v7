from __future__ import annotations

"""Visual/behavior polish for the isolated YipMan Mobile V1 RC preview.

This layer does not change the official /app/yipman-v1/ route or any backend
calculation. It only refines the preview HTML after the consolidated RC
renderer has already been applied.
"""

_STYLE = r'''
<style id="yipmanV1RcPolish1">
/* Compact the oversized legacy V1 header so operational content starts higher. */
body.yipman-v1 .header{padding:6px 12px 6px!important}
body.yipman-v1 .brand{font-size:28px!important;line-height:1!important}
body.yipman-v1 .ver{font-size:9px!important;line-height:1.15!important;margin-top:3px!important;max-width:270px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
body.yipman-v1 .dbbtn{width:38px!important;height:38px!important;border-radius:12px!important}
body.yipman-v1 .workspace{height:calc(100% - 58px)!important}

/* Keep bottom controls large enough to tap without covering so much content. */
body.yipman-v1 .nav{height:68px!important;left:12px!important;right:12px!important;border-radius:22px!important}
body.yipman-v1 .nav button{font-size:9px!important}
body.yipman-v1 .nav i{font-size:23px!important}
body.yipman-v1 #quick{padding-bottom:calc(142px + env(safe-area-inset-bottom))!important}
body.yipman-v1 .quicksearch{left:12px!important;right:12px!important;bottom:calc(76px + env(safe-area-inset-bottom))!important;min-height:58px!important;border-radius:16px!important;grid-template-columns:40px minmax(0,1fr) 62px!important;padding:4px 7px!important}
body.yipman-v1 .quicksearch>span{width:32px!important;height:32px!important;font-size:19px!important}
body.yipman-v1 .quicksearch input{font-size:17px!important;padding:8px 4px!important}

/* Price page top controls stay within a compact review header zone. */
body.yipman-v1 #price>.topline{margin:0 0 3px!important}
body.yipman-v1 #price>.topline h2{font-size:22px!important}
body.yipman-v1 #price>.topline .hint{font-size:9px!important}
body.yipman-v1 #price .price-tabs{margin-bottom:5px!important;padding:3px!important;border-radius:11px!important}
body.yipman-v1 #price .price-tab{min-height:38px!important;padding:5px 2px!important;font-size:9px!important}
body.yipman-v1 #price .tpr-rule{padding:6px 8px!important;margin-bottom:5px!important;font-size:8.5px!important;line-height:1.3!important}
body.yipman-v1 #price .filters{gap:4px!important;margin-bottom:4px!important}
body.yipman-v1 #price .filters .pill{padding:7px 9px!important;font-size:10px!important}
body.yipman-v1 #price .price-tools{gap:5px!important;margin-bottom:5px!important}
body.yipman-v1 #price .price-tools label{font-size:7px!important}
body.yipman-v1 #price .price-tools select{padding-top:7px!important;padding-bottom:7px!important;font-size:9.5px!important}
body.yipman-v1 #priceStatus{font-size:9px!important;line-height:1.28!important}

/* Ordering title/date controls should remain visible above the first card. */
body.yipman-v1 #order>.topline h2{font-size:22px!important}
body.yipman-v1 #order>.topline .hint{font-size:9px!important}
body.yipman-v1 #order .order-tab{min-height:48px!important;font-size:12px!important}
body.yipman-v1 #order .order-coverage{margin-top:6px!important;padding:9px 10px!important}
body.yipman-v1 #order .order-coverage b{font-size:20px!important}
body.yipman-v1 #order .order-coverage span{font-size:9px!important}
body.yipman-v1 #order .order-tools{margin-bottom:6px!important}

/* RC urgent feed: only truly urgent price items remain in the feed. */
.v1polish-nonurgent{display:none!important}
.v1urgent-sticky{padding-top:4px!important;padding-bottom:5px!important}
.v1urgent-filter{height:36px!important}
.v1urgent-filter strong{font-size:13px!important}
.v1urgent-card{padding:10px!important}
.v1urgent-name{font-size:17px!important}
.v1urgent-action{font-size:17px!important}
.v1urgent-ignore{min-height:44px!important}

/* More page should read as a compact utility menu, not a landing poster. */
body.yipman-v1 #more>.topline h2{font-size:24px!important}
body.yipman-v1 #more>.topline .hint{font-size:9px!important}
.v1more{gap:7px!important}
.v1more-primary,.v1more-row{min-height:68px!important;padding:10px!important;border-radius:14px!important}
.v1more-primary b,.v1more-row b{font-size:15px!important}
.v1more-primary small,.v1more-row small{font-size:8.5px!important}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1RcPolish1Script">
(function(){
  'use strict';
  if(!document.body.classList.contains('yipman-v1') || window.__YIPMAN_V1_RC_POLISH1__) return;
  window.__YIPMAN_V1_RC_POLISH1__=true;

  function simplifyVersion(){
    const el=document.querySelector('.ver');
    if(!el) return;
    const raw=String(el.textContent||'').trim();
    const m=raw.match(/\d+\.\d+\.\d+/);
    el.title=raw;
    el.textContent='FULL MYSQL · '+(m?m[0]:'V1')+' · MOBILE V1 RC';
  }

  function isRealUrgent(card){
    if(card.classList.contains('fresh')) return true;
    if(card.classList.contains('order')) return true;
    if(card.classList.contains('inventory')) return true;
    if(!card.classList.contains('price')) return true;
    const t=String(card.innerText||'').toUpperCase();
    return /240\s*\/\s*249|MISMATCH|PRICE INTEGRITY|INTEGRITY CORRECTION|SALE WARNING|CLEARANCE|FRESHNESS/.test(t);
  }

  function applyUrgentScope(){
    const shell=document.querySelector('#v1UrgentHome');
    if(!shell) return;
    const cards=[...shell.querySelectorAll('.v1urgent-card')];
    cards.forEach(card=>card.classList.toggle('v1polish-nonurgent',!isRealUrgent(card)));

    const shown=cards.filter(c=>!c.classList.contains('v1polish-nonurgent'));
    const counts={all:shown.length,price:0,order:0,fresh:0,inventory:0};
    shown.forEach(c=>{
      for(const k of ['price','order','fresh','inventory']) if(c.classList.contains(k)){counts[k]++;break;}
    });
    shell.querySelectorAll('.v1urgent-filter').forEach(btn=>{
      const k=btn.dataset.filter||'all',num=btn.querySelector('strong');
      if(num) num.textContent=String(counts[k]??0);
    });
  }

  function watchUrgent(){
    const shell=document.querySelector('#v1UrgentHome');
    if(!shell){setTimeout(watchUrgent,150);return;}
    applyUrgentScope();
    let queued=false;
    new MutationObserver(()=>{
      if(queued) return;
      queued=true;
      requestAnimationFrame(()=>{queued=false;applyUrgentScope();});
    }).observe(shell,{childList:true,subtree:true,characterData:true});
  }

  function init(){
    simplifyVersion();
    watchUrgent();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
})();
</script>
'''


def polish_rc_html(html: str, version: str = "") -> str:
    if "yipmanV1RcPolish1" in html:
        return html
    html = html.replace("</head>", _STYLE + "</head>", 1)
    html = html.replace("</body>", _SCRIPT + "</body>", 1)
    return html
