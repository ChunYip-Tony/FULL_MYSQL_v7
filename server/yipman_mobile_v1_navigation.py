from __future__ import annotations

"""RC-only in-app history/back navigation layer for the standalone Mobile V1 PWA.

Android's system Back button operates on browser history.  The exact-mock shell
uses client-side page/overlay swaps, so without explicit history states Android
can close the standalone PWA immediately.  This layer maps YipMan views to the
history stack so Back behaves like a native app:

True Stock sheet -> action detail -> previous page -> prior page -> confirm exit.
"""

_SCRIPT = r'''
<script id="yipmanV1NavigationStackScript">
(function(){
  'use strict';
  if(window.__YIPMAN_V1_NAV_STACK__) return;
  window.__YIPMAN_V1_NAV_STACK__=true;

  const GEN=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,8);
  const KEY='yipmanV1Nav';
  let restoring=false;
  let allowExit=false;
  let syncQueued=false;

  function activePage(){
    return document.querySelector('.page.active')?.id || 'quick';
  }
  function navState(type,page,extra){
    return {[KEY]:true,gen:GEN,type:type,page:page||activePage(),...(extra||{})};
  }
  function isOurState(s){return !!(s&&s[KEY]);}
  function currentState(){return history.state||{};}
  function stockOpen(){return document.getElementById('v1StockBackdrop')?.classList.contains('open')||false;}
  function detailOpen(){return document.getElementById('v1DetailOverlay')?.classList.contains('open')||false;}
  function searchOpen(){
    const box=document.getElementById('quickResults');
    const input=document.getElementById('quickSearch');
    return activePage()==='quick' && !!box?.classList.contains('show') && !!String(input?.value||'').trim();
  }

  function closeStock(){
    document.getElementById('v1StockBackdrop')?.classList.remove('open');
    const input=document.getElementById('v1StockInput');
    if(input) input.blur();
  }
  function closeDetail(){document.getElementById('v1DetailOverlay')?.classList.remove('open');}
  function closeSearch(){
    const input=document.getElementById('quickSearch');
    const box=document.getElementById('quickResults');
    const list=document.getElementById('urgentList');
    if(input){input.value='';input.blur();}
    const clear=document.getElementById('quickClear');
    if(clear) clear.style.visibility='hidden';
    box?.classList.remove('show');
    if(list) list.style.display='grid';
  }
  function closeTransientAbove(targetType){
    if(targetType!=='stock') closeStock();
    if(targetType!=='stock' && targetType!=='detail') closeDetail();
    if(!['stock','detail','search'].includes(targetType)) closeSearch();
  }

  function directShow(page){
    document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id===page));
    document.querySelectorAll('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.nav===page));
    document.getElementById('app')?.classList.toggle('quick-on',page==='quick');
  }
  function showPage(page){
    if(!page || activePage()===page) return;
    const target=document.querySelector('[data-nav="'+CSS.escape(page)+'"]') ||
                 document.querySelector('[data-open="'+CSS.escape(page)+'"]');
    if(target){target.click();return;}
    directShow(page);
  }

  function push(type,page,extra){
    if(restoring) return;
    const s=currentState();
    if(isOurState(s) && s.gen===GEN && s.type===type && s.page===(page||activePage())) return;
    history.pushState(navState(type,page,extra),'',location.href);
  }

  function syncUiToHistory(){
    if(restoring) return;
    const s=currentState();
    const page=activePage();
    if(stockOpen()){
      if(!(isOurState(s)&&s.gen===GEN&&s.type==='stock')) push('stock',page);
      return;
    }
    if(detailOpen()){
      if(!(isOurState(s)&&s.gen===GEN&&s.type==='detail')) push('detail',page);
      return;
    }
    if(searchOpen()){
      if(!(isOurState(s)&&s.gen===GEN&&s.type==='search')) push('search','quick');
      return;
    }
    if(!(isOurState(s)&&s.gen===GEN&&s.type==='page'&&s.page===page)) push('page',page);
  }
  function queueSync(){
    if(syncQueued||restoring) return;
    syncQueued=true;
    requestAnimationFrame(()=>{syncQueued=false;syncUiToHistory();});
  }

  function exitAttempt(){
    document.activeElement?.blur?.();
    const leave=window.confirm('Exit YipMan?');
    if(!leave){
      history.pushState(navState('page','quick',{root:true}),'',location.href);
      restoring=true;
      closeTransientAbove('page');
      showPage('quick');
      setTimeout(()=>{restoring=false;},0);
      return;
    }
    allowExit=true;
    history.back();
  }

  window.addEventListener('popstate',e=>{
    const s=e.state||{};

    // After confirmed exit, unwind every older YipMan-generated entry.  This
    // also handles a prior reload after saving True Stock without reopening a
    // stale detail/page state.
    if(allowExit){
      if(isOurState(s)) setTimeout(()=>history.back(),0);
      return;
    }

    // A history entry from an older document generation is stale app history,
    // so treat it as the root exit boundary rather than reopening old UI.
    if(isOurState(s) && s.gen!==GEN){
      exitAttempt();
      return;
    }

    if(!isOurState(s)){
      // If the standalone app reaches a non-YipMan history entry, keep the app
      // in place unless the user explicitly confirmed Exit.
      history.pushState(navState('page','quick',{root:true}),'',location.href);
      restoring=true;
      closeTransientAbove('page');
      showPage('quick');
      setTimeout(()=>{restoring=false;},0);
      exitAttempt();
      return;
    }

    if(s.type==='exit-base'){
      exitAttempt();
      return;
    }

    restoring=true;
    closeTransientAbove(s.type);
    if(s.page) showPage(s.page);
    if(s.type==='search'){
      // Backward navigation normally goes FROM search to page, but preserve a
      // visible search state if browser Forward is used later.
      const box=document.getElementById('quickResults');
      if(box) box.classList.add('show');
    }
    setTimeout(()=>{restoring=false;},0);
  });

  // Use the same stack for visible in-app Back/Cancel controls.
  document.addEventListener('click',e=>{
    const back=e.target.closest('#v1DetailBack,.iconbtn[data-open]');
    if(back){
      const s=currentState();
      if(isOurState(s)&&s.gen===GEN){
        e.preventDefault();e.stopImmediatePropagation();history.back();
        return;
      }
    }
    const cancel=e.target.closest('#v1StockCancel');
    if(cancel){
      const s=currentState();
      if(isOurState(s)&&s.gen===GEN&&s.type==='stock'){
        e.preventDefault();e.stopImmediatePropagation();history.back();
        return;
      }
    }
    const clear=e.target.closest('#quickClear');
    if(clear){
      const s=currentState();
      if(isOurState(s)&&s.gen===GEN&&s.type==='search'){
        e.preventDefault();e.stopImmediatePropagation();history.back();
      }
    }
    if(e.target.id==='v1StockBackdrop'){
      const s=currentState();
      if(isOurState(s)&&s.gen===GEN&&s.type==='stock'){
        e.preventDefault();e.stopImmediatePropagation();history.back();
      }
    }
  },true);

  const observer=new MutationObserver(queueSync);
  observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});

  // Reserve one root boundary. Android Back at this boundary asks before exit.
  history.replaceState(navState('exit-base','quick'),'',location.href);
  history.pushState(navState('page',activePage(),{root:true}),'',location.href);
  queueSync();
})();
</script>
'''


def polish_navigation_html(html: str) -> str:
    if 'yipmanV1NavigationStackScript' in html:
        return html
    return html.replace('</body>', _SCRIPT + '</body>', 1)
