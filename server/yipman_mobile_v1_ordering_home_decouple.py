from __future__ import annotations

"""Keep Ordering state independent from the Stock Flow-only Home.

The legacy shell historically rebuilt the Home urgent queue whenever Ordering rows
were refreshed. Home is now Stock Flow-only, so Ordering must update only Ordering
state/rendering. This late composition patch deliberately overrides only the shared
paintOrderRows helper and leaves action-detail generation available to explicit
ordering/Quick Check flows.
"""

_SCRIPT = r'''
<script id="yipmanV1OrderingHomeDecoupleScript">
(()=>{'use strict';
  function install(){
    if(typeof window.paintOrderRows!=='function' || window.paintOrderRows.__stockFlowHomeSafe)return;
    const safe=function(rows){
      window.orderRows=Array.isArray(rows)?rows:[];
      if(document.getElementById('regularResults') && typeof window.renderOrdering==='function'){
        window.renderOrdering();
      }
      // Intentionally do not rebuild `urgent` or call renderUrgent(). Home owns its
      // Stock Flow list; Ordering owns orderRows. This prevents an ordering refresh,
      // date change, or True Stock recalculation from mutating the Home panel.
    };
    safe.__stockFlowHomeSafe=true;
    window.paintOrderRows=safe;
  }
  install();
  document.addEventListener('DOMContentLoaded',install,{once:true});
  setTimeout(install,0);
})();
</script>
'''


def polish_ordering_home_decouple_html(html: str) -> str:
    marker = "yipmanV1OrderingHomeDecoupleScript"
    if marker in html:
        return html
    return html.replace("</body>", _SCRIPT + "\n</body>", 1)
