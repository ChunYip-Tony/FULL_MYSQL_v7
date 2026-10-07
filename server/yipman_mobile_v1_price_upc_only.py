from __future__ import annotations

"""RC-only Price Review presentation guard.

Every Price Review filter must render UPC-level price suggestion cards.  Family
summary cards are useful elsewhere, but they hide the actual price decision and
make All/Urgent inconsistent with REG/TPR/Clearance/SALE/prefix filters.

The existing 249 rule remains intact: linked 249 rows are supporting evidence
for the 240 decision and are not rendered as independent suggestion cards.
"""


def polish_price_upc_only_html(html: str) -> str:
    marker = "yipmanV1PriceUpcOnlyFilters"
    if marker in html:
        return html

    old = "const direct=!['all','urgent'].includes(pf);"
    new = "const direct=true;"
    if old in html:
        html = html.replace(old, new, 1)

    # Do not allow non-UPC rows to become blank direct suggestion cards.
    old_rows = "const rows=priceRows.filter(r=>actionablePrice(r)&&matchPriceFilter(r)&&!isIgnored('price:'+upcOf(r)));"
    new_rows = "const rows=priceRows.filter(r=>upcOf(r)&&actionablePrice(r)&&matchPriceFilter(r)&&!isIgnored('price:'+upcOf(r)));"
    if old_rows in html:
        html = html.replace(old_rows, new_rows, 1)

    html = html.replace(
        "</head>",
        f'<meta name="{marker}" content="1">\n</head>',
        1,
    )
    return html
