from __future__ import annotations


QUICK_CHECK_MOBILE_LAYOUT = r"""
<style id="yipman-quick-check-mobile-layout">
/*
 * Mobile V1 Quick Check readability patch.
 * Keep the large V1 type scale, but stop forcing operational metrics into
 * narrow columns. Inventory is one 2-column row, flow is a second 2-column
 * row, and UPC prices use two 3-column rows.
 */
@media (max-width: 759px) {
  body.yipman-v1 #quick {
    padding-bottom: calc(168px + env(safe-area-inset-bottom)) !important;
  }

  body.yipman-v1 #quick .qfamily {
    overflow: hidden;
  }

  body.yipman-v1 #quick .qfhead {
    display: block !important;
    padding: 10px 11px 11px !important;
  }

  body.yipman-v1 #quick .qfamily .qlabel {
    font-size: 9px !important;
    line-height: 1.05;
  }

  body.yipman-v1 #quick .qfamily .qfnum {
    font-size: 24px !important;
    line-height: 1.02;
    margin-top: 2px;
  }

  body.yipman-v1 #quick .qfamily .qfname {
    font-size: 25px !important;
    line-height: 1.04 !important;
    margin-top: 4px !important;
    overflow-wrap: anywhere;
  }

  body.yipman-v1 #quick .qfamily .qmeta {
    font-size: 10px !important;
    line-height: 1.25;
    margin-top: 5px !important;
  }

  /* Cost gets its own readable line instead of competing with the KPI row. */
  body.yipman-v1 #quick .qfamilycost {
    display: grid !important;
    grid-template-columns: auto auto !important;
    justify-content: start !important;
    align-items: baseline !important;
    gap: 4px 8px !important;
    margin-top: 7px !important;
    padding: 7px 8px !important;
    border-radius: 10px !important;
  }

  body.yipman-v1 #quick .qfamilycost span {
    font-size: 8px !important;
  }

  body.yipman-v1 #quick .qfamilycost b {
    font-size: 16px !important;
    line-height: 1.05 !important;
    white-space: nowrap;
  }

  body.yipman-v1 #quick .qfamilycost small {
    grid-column: 1 / -1;
    font-size: 8px !important;
    line-height: 1.2;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  /*
   * qffocus previously had three narrow columns while familyOhPair contains
   * two more cells. Make OH a full-width two-column row, then put Selling MVT
   * and Receipt underneath as a second two-column row.
   */
  body.yipman-v1 #quick .qffocus {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 8px !important;
    margin-top: 8px !important;
  }

  body.yipman-v1 #quick .qffocus > .familyohpair {
    grid-column: 1 / -1 !important;
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 8px !important;
    min-width: 0;
    margin: 0 !important;
  }

  body.yipman-v1 #quick .familyohbtn,
  body.yipman-v1 #quick .familysystemoh,
  body.yipman-v1 #quick .qffocusbox {
    min-width: 0 !important;
    min-height: 90px;
    padding: 9px 10px !important;
    border-radius: 12px !important;
    text-align: left !important;
    overflow: hidden;
  }

  body.yipman-v1 #quick .familyohbtn,
  body.yipman-v1 #quick .familysystemoh {
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-start !important;
    justify-content: center !important;
  }

  body.yipman-v1 #quick .familyohbtn small,
  body.yipman-v1 #quick .familysystemoh small,
  body.yipman-v1 #quick .qffocusbox small {
    display: block;
    max-width: 100%;
    font-size: 8px !important;
    line-height: 1.12 !important;
    white-space: normal !important;
    overflow-wrap: anywhere;
  }

  body.yipman-v1 #quick .familyohbtn b,
  body.yipman-v1 #quick .familysystemoh b {
    display: block;
    max-width: 100%;
    margin-top: 5px !important;
    font-size: 24px !important;
    line-height: 1 !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
  }

  body.yipman-v1 #quick .familyohbtn span,
  body.yipman-v1 #quick .familysystemoh span {
    display: block;
    max-width: 100%;
    margin-top: 6px !important;
    font-size: 8px !important;
    line-height: 1.15 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
  }

  body.yipman-v1 #quick .qffocusbox {
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-start !important;
    justify-content: space-between !important;
    gap: 7px !important;
  }

  body.yipman-v1 #quick .qffocusbox > div {
    min-width: 0;
    width: 100%;
  }

  body.yipman-v1 #quick .qffocusbox span {
    display: block;
    max-width: 100%;
    margin-top: 4px !important;
    font-size: 8px !important;
    line-height: 1.15 !important;
    white-space: normal !important;
    overflow-wrap: anywhere;
  }

  body.yipman-v1 #quick .qffocusbox > b {
    display: block;
    max-width: 100%;
    font-size: 25px !important;
    line-height: 1 !important;
    white-space: nowrap !important;
    text-align: left !important;
    overflow: visible !important;
    text-overflow: clip !important;
  }

  /* Receiving article: identity first, delivery history below in two columns. */
  body.yipman-v1 #quick .qreceivingrow {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 7px !important;
    padding: 8px 9px 9px !important;
    align-items: stretch !important;
  }

  body.yipman-v1 #quick .qrecvidentity {
    grid-column: 1 / -1 !important;
    display: grid !important;
    grid-template-columns: 28px minmax(0, 1fr) !important;
    gap: 7px !important;
    align-items: start !important;
    min-width: 0;
  }

  body.yipman-v1 #quick .qricon {
    width: 28px !important;
    height: 28px !important;
    border-radius: 8px !important;
    font-size: 12px !important;
  }

  body.yipman-v1 #quick .qrnum {
    font-size: 18px !important;
    line-height: 1.05;
  }

  body.yipman-v1 #quick .qrname {
    font-size: 11px !important;
    line-height: 1.18;
    margin-top: 2px !important;
    white-space: normal !important;
    overflow-wrap: anywhere;
  }

  body.yipman-v1 #quick .qr7d {
    display: block;
    margin-top: 4px;
    font-size: 9px !important;
    line-height: 1.15;
  }

  body.yipman-v1 #quick .qdelivery {
    width: 100%;
    min-width: 0;
    min-height: 58px;
    padding: 7px 8px !important;
    border-radius: 10px !important;
    text-align: left !important;
  }

  body.yipman-v1 #quick .qdelivery small {
    font-size: 7px !important;
    line-height: 1.05;
    white-space: normal;
  }

  body.yipman-v1 #quick .qdelivery b {
    font-size: 14px !important;
    line-height: 1.08;
    margin-top: 3px;
    white-space: nowrap;
  }

  body.yipman-v1 #quick .qdelivery span {
    font-size: 9px !important;
    line-height: 1.08;
    margin-top: 3px;
    white-space: normal;
  }

  /* UPC identity can remain prominent; price cells are now exactly 3 columns. */
  body.yipman-v1 #quick .qupc {
    padding: 9px 10px !important;
    gap: 7px !important;
  }

  body.yipman-v1 #quick .qupctop {
    gap: 6px !important;
  }

  body.yipman-v1 #quick .qrole {
    font-size: 8px !important;
    padding: 3px 6px !important;
  }

  body.yipman-v1 #quick .qupccode {
    font-size: 11px !important;
  }

  body.yipman-v1 #quick .qupcname {
    font-size: 19px !important;
    line-height: 1.05 !important;
    margin-top: 4px !important;
    overflow-wrap: anywhere;
  }

  body.yipman-v1 #quick .qready {
    font-size: 10px !important;
    margin-top: 5px !important;
  }

  body.yipman-v1 #quick .qupcmetrics small {
    font-size: 7px !important;
  }

  body.yipman-v1 #quick .qupcmetrics b {
    font-size: 20px !important;
  }

  body.yipman-v1 #quick .qupcmetrics span {
    font-size: 9px !important;
  }

  body.yipman-v1 #quick .qupcprices {
    grid-column: 1 / -1;
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    gap: 6px !important;
    margin-top: 8px !important;
    min-width: 0;
  }

  body.yipman-v1 #quick .qprice {
    min-width: 0 !important;
    min-height: 54px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 7px 5px !important;
    border-radius: 10px !important;
    overflow: hidden;
  }

  body.yipman-v1 #quick .qprice small {
    min-height: 16px;
    font-size: 7px !important;
    line-height: 1.08 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    overflow-wrap: anywhere;
  }

  body.yipman-v1 #quick .qprice b,
  body.yipman-v1 #quick .qprice b.qempty {
    margin-top: 4px !important;
    font-size: 15px !important;
    line-height: 1 !important;
    white-space: nowrap !important;
  }

  /* The first three cells are operational price state; 4–6 are company refs. */
  body.yipman-v1 #quick .qprice:nth-child(n+4) {
    border-top-width: 2px;
  }
}

@media (max-width: 380px) {
  body.yipman-v1 #quick .qfamily .qfname {
    font-size: 23px !important;
  }

  body.yipman-v1 #quick .familyohbtn b,
  body.yipman-v1 #quick .familysystemoh b,
  body.yipman-v1 #quick .qffocusbox > b {
    font-size: 22px !important;
  }

  body.yipman-v1 #quick .qupcname {
    font-size: 18px !important;
  }

  body.yipman-v1 #quick .qprice b,
  body.yipman-v1 #quick .qprice b.qempty {
    font-size: 14px !important;
  }
}
</style>
"""


def inject_quick_check_mobile_layout(html: str) -> str:
    """Inject the V1 Quick Check layout override exactly once."""
    if not html or 'id="yipman-quick-check-mobile-layout"' in html:
        return html
    return html.replace("</head>", QUICK_CHECK_MOBILE_LAYOUT + "</head>", 1)
