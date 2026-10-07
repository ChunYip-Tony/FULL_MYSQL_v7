from __future__ import annotations

"""RC-only price identity guard.

The pricing API can expose a legacy/internal short UPC alias beside the canonical
selling UPC for the same Family/item.  The Mobile V1 shell used the raw UPC as
its action key, so aliases such as `4843` and canonical `24084300000` could be
rendered as two separate Fresh/Price actions.

This renderer patch removes only short numeric aliases (<= 6 digits) when the
same Family + item name also has a canonical 8-14 digit selling UPC. Legitimate
separate full UPCs in the same Family remain independent.
"""

_HELPER = r'''
function priceIdentityName(r){return nameOf(r).toUpperCase().replace(/[^A-Z0-9]+/g,' ').trim()}
function dedupePriceAliasRows(rows){
  const arr=Array.isArray(rows)?rows:[];
  const canonical=new Set();
  for(const r of arr){
    const up=upcOf(r),fam=famOf(r),nm=priceIdentityName(r);
    if(/^\d{8,14}$/.test(up)&&fam&&nm)canonical.add(fam+'|'+nm);
  }
  return arr.filter(r=>{
    const up=upcOf(r),fam=famOf(r),nm=priceIdentityName(r);
    return !(/^\d{1,6}$/.test(up)&&fam&&nm&&canonical.has(fam+'|'+nm));
  });
}
'''


def polish_identity_html(html: str) -> str:
    if 'function dedupePriceAliasRows' in html:
        return html

    anchor = "function buildUrgentPrice(rows){"
    if anchor in html:
        html = html.replace(anchor, _HELPER + "\nfunction buildUrgentPrice(rows){rows=dedupePriceAliasRows(rows);", 1)

    old = "function renderPrice(){const rows=priceRows.filter("
    new = "function renderPrice(){const rows=dedupePriceAliasRows(priceRows).filter("
    if old in html:
        html = html.replace(old, new, 1)

    return html
