from __future__ import annotations

"""RC-only app-wide typography scale for Mobile V1.

The mobile UI must stay compact, but the current exact-mock shell inherited many
7-11px labels that are too small on a physical phone.  This layer increases text
sizes consistently across Quick, Ordering, Price, More, detail overlays, True
Stock sheets, date controls, filters, metrics, and status text without changing
business logic or card hierarchy.
"""

from yipman_mobile_v1_identity_compact import polish_identity_compact_html
from yipman_mobile_v1_oh_safety import polish_oh_safety_html

_STYLE = r'''
<style id="yipmanV1ReadableTypography">
/* Core page / navigation */
.title{font-size:31px!important}.sub{font-size:14px!important;line-height:1.25!important}
.nav button{font-size:12px!important}.nav button i{font-size:28px!important}
.searchdock input{font-size:22px!important}.searchdock button{font-size:12px!important}
.iconbtn,.searchbtn{font-size:26px!important}

/* Quick / urgent */
.urgent-summary strong{font-size:16px!important}.urgent-summary span{font-size:10px!important}
.updated{font-size:10px!important}.urgent-name{font-size:25px!important}.urgent-meta{font-size:12px!important}
.urgent-action{font-size:26px!important}.urgent-why{font-size:14px!important;line-height:1.38!important}
.metric b,.stat b{font-size:9px!important}.metric span,.stat span{font-size:15px!important}
.ignore{font-size:16px!important}.pill{font-size:11px!important}

/* Generic cards / ordering */
.card-title{font-size:24px!important}.card-sub{font-size:13px!important;line-height:1.3!important}
.big-entry b{font-size:24px!important}.big-entry span{font-size:13px!important;line-height:1.4!important}
.field label,.order-date-field label{font-size:10px!important}.input,.search,.order-date-field input{font-size:17px!important}
.order-main{font-size:27px!important}.why{font-size:14px!important;line-height:1.4!important}
.loading,.empty{font-size:14px!important;line-height:1.4!important}
.order-date-title{font-size:11px!important}.order-date-basis,.order-date-status{font-size:10px!important}
.order-date-refresh{font-size:11px!important}.date-weekday-hint{font-size:11px!important}.weekday-chip{font-size:10px!important}

/* Price Review */
.price-summary b{font-size:20px!important}.price-summary span{font-size:10px!important}
.filterbtn{font-size:12px!important}.family-title{font-size:24px!important}.family-sub{font-size:13px!important}
.family-side b{font-size:29px!important}.family-side span{font-size:10px!important}
.result-name{font-size:24px!important}.action-meta{font-size:12px!important}.action-label{font-size:10px!important}
.action-value{font-size:26px!important}

/* More */
.morebtn b{font-size:22px!important}.morebtn span{font-size:12px!important;line-height:1.35!important}

/* Detail overlay */
.v1-detail-kicker{font-size:10px!important}.v1-detail-title{font-size:24px!important}.v1-detail-status{font-size:10px!important}
.v1-detail-id b,.v1-detail-metrics b{font-size:9px!important}.v1-detail-id span,.v1-detail-metrics span{font-size:13px!important}
.v1-detail-decision small{font-size:10px!important}.v1-detail-decision strong{font-size:28px!important}
.v1-detail-decision p{font-size:14px!important;line-height:1.4!important}
.v1-detail-oh small{font-size:10px!important}.v1-detail-oh strong{font-size:30px!important}.v1-detail-oh span{font-size:10px!important}
.v1-detail-note{font-size:13px!important;line-height:1.45!important}.v1-detail-loading{font-size:14px!important}
.v1-oh-editable::after{font-size:8px!important}

/* True Stock sheet */
.v1-stock-sheet h3{font-size:24px!important}.v1-stock-meta{font-size:12px!important}
.v1-stock-current small{font-size:9px!important}.v1-stock-current strong{font-size:26px!important}
.v1-stock-input{font-size:28px!important}.v1-stock-uom{font-size:11px!important}
.v1-stock-actions button{font-size:14px!important}.v1-stock-status{font-size:11px!important}

/* Price lifecycle / progress add-ons */
.tpr-progress-title,.price-progress-title{font-size:13px!important}
.tpr-progress-sub,.price-progress-sub,.tpr-progress-meta,.price-progress-meta{font-size:11px!important;line-height:1.4!important}

/* General safety floor for common small text */
button{line-height:1.2}

@media(max-width:390px){
  .title{font-size:29px!important}
  .urgent-name{font-size:23px!important}.urgent-action{font-size:24px!important}
  .card-title,.family-title,.result-name{font-size:22px!important}
  .v1-detail-title{font-size:22px!important}
}
</style>
'''


def polish_typography_html(html: str) -> str:
    if 'yipmanV1ReadableTypography' not in html:
        html = html.replace('</head>', _STYLE + '</head>', 1)
    html = polish_identity_compact_html(html)
    return polish_oh_safety_html(html)
