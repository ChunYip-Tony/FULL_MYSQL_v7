from __future__ import annotations

"""RC-only OH display safety.

Prevent missing / unresolved OH values from being coerced to numeric zero in the
browser. A genuine numeric 0 remains 0; null / undefined / blank stays unavailable.
This protects Quick, Price, Ordering, detail overlays and True Stock editing.
"""


def polish_oh_safety_html(html: str) -> str:
    marker = "yipmanV1OhNullSafety"
    if marker in html:
        return html

    # Core shell formatter. JavaScript Number(null) and Number('') are 0, which
    # previously made missing OH look like real zero stock across the app.
    html = html.replace(
        "const num=v=>{const x=Number(v);return Number.isFinite(x)?x:null};",
        "const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};",
    )

    # UPC/action detail overlay has local formatters, so make those null-safe too.
    html = html.replace(
        "const money=v=>{const n=Number(v);return Number.isFinite(n)?'$'+n.toFixed(2):'—'};",
        "const money=v=>{if(v===null||v===undefined||v==='')return'—';const n=Number(v);return Number.isFinite(n)?'$'+n.toFixed(2):'—'};",
    )
    html = html.replace(
        "const fmt=v=>{const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:1}):'—'};",
        "const fmt=v=>{if(v===null||v===undefined||v==='')return'—';const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:1}):'—'};",
    )

    # Do not let a missing live Effective OH overwrite a valid OH shown on the
    # originating card with 0 in Action Detail.
    html = html.replace(
        "const qty=Number.isFinite(Number(eff?.quantity))?Number(eff.quantity):domOh.qty;",
        "const qty=(eff?.quantity===null||eff?.quantity===undefined||eff?.quantity==='')?domOh.qty:(Number.isFinite(Number(eff.quantity))?Number(eff.quantity):domOh.qty);",
    )

    return html.replace(
        "</head>",
        f'<meta name="{marker}" content="1">\n</head>',
        1,
    )
