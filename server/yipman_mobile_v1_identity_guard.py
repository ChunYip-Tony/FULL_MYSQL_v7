from __future__ import annotations

"""RC-only identity guard for duplicate price actions.

Some pricing-review rows can expose both a canonical full UPC and a short/legacy
numeric alias for the same Family/name/reason.  The Mobile V1 action feed should
not render both as separate customer-facing actions.  Keep the canonical UPC row
when the evidence clearly identifies the short row as a shadow alias; do not
collapse genuinely distinct UPC actions.
"""


def polish_identity_html(html: str) -> str:
    marker = "yipmanV1CanonicalIdentityGuard"
    if marker in html:
        return html

    old_anchor = "function buildUrgentPrice(rows){const out=[];for(const r of rows||[]){const upc=upcOf(r);if(!upc||prefix(upc)==='249'||!trueUrgentPrice(r))continue;"
    new_anchor = (
        "function shadowPriceAlias(r,rows){"
        "const upc=upcOf(r),fam=famOf(r),nm=nameOf(r).trim().toUpperCase(),why=priceReason(r).trim().toUpperCase();"
        "if(!/^\\d{1,7}$/.test(upc))return false;"
        "return (rows||[]).some(x=>{const xu=upcOf(x);return xu!==upc&&/^\\d{8,14}$/.test(xu)&&famOf(x)===fam&&nameOf(x).trim().toUpperCase()===nm&&priceReason(x).trim().toUpperCase()===why&&trueUrgentPrice(x)});"
        "}"
        "function buildUrgentPrice(rows){const out=[];for(const r of rows||[]){const upc=upcOf(r);if(!upc||prefix(upc)==='249'||shadowPriceAlias(r,rows)||!trueUrgentPrice(r))continue;"
    )
    if old_anchor not in html:
        return html
    html = html.replace(old_anchor, new_anchor, 1)

    old_price = "const rows=priceRows.filter(r=>actionablePrice(r)&&matchPriceFilter(r)&&!isIgnored('price:'+upcOf(r)));"
    new_price = "const rows=priceRows.filter(r=>actionablePrice(r)&&matchPriceFilter(r)&&!shadowPriceAlias(r,priceRows)&&!isIgnored('price:'+upcOf(r)));"
    html = html.replace(old_price, new_price, 1)

    html = html.replace("</head>", f'<meta name="{marker}" content="1">\n</head>', 1)
    return html
