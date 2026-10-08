from __future__ import annotations

"""Keep Ordering refresh independent from the Stock Flow-only Home.

The reliability layer still contains legacy behavior that rebuilds the old urgent
queue whenever ordering rows refresh. Home is now Stock Flow-only. Patch the
composed HTML at render time, inside the original lexical scope, rather than adding
a browser-side wrapper that could miss module/let state.
"""

_OLD = """function paintOrderRows(rows){
  orderRows=Array.isArray(rows)?rows:[];
  if(document.getElementById('regularResults'))renderOrdering();
  urgent=[...urgent.filter(x=>x.type!=='order'),...buildUrgentOrder(orderRows)].filter(x=>!isIgnored(x.key)).sort((a,b)=>b.score-a.score);
  renderUrgent();
}"""

_NEW = """function paintOrderRows(rows){
  orderRows=Array.isArray(rows)?rows:[];
  if(document.getElementById('regularResults'))renderOrdering();
  // Home is Stock Flow-only. Ordering refresh must not mutate the legacy urgent queue.
}"""


def polish_ordering_home_decouple_html(html: str) -> str:
    marker = "yipmanV1OrderingHomeDecoupled"
    if marker in html:
        return html
    if _OLD not in html:
        # Fail closed: do not claim the decoupling marker when the expected contract
        # is absent. This keeps composition drift visible during source/self tests.
        return html
    html = html.replace(_OLD, _NEW, 1)
    return html.replace("</head>", f'<meta name="{marker}" content="1">\n</head>', 1)
