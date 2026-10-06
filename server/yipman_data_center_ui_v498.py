from __future__ import annotations

_MARKER='ydDataCenterUiV498'

_STYLE=r'''
<style id="ydDataCenterUiV498">
@media (min-width:760px){
  #ydesk #yd-data .datagrid{grid-template-columns:minmax(0,1.72fr) minmax(345px,.72fr)!important;gap:12px!important}
  #ydesk #yd-data .upload{min-height:205px!important;padding:18px!important}
  #ydesk #yd-data .upload h3{font-size:17px!important}
  #ydesk #yd-data .upload p{margin-bottom:8px!important}
  #ydesk #yd-data #ydUploadResult{max-width:620px!important;width:100%!important;padding:8px 10px!important;border-radius:10px!important;background:#f5f9fd!important;border:1px solid #deebf5!important}
  #ydesk #yd-data #ydUploadResult b{font-size:12px!important}
  #ydesk #yd-data .cardhead{min-height:54px!important}
  #ydesk #yd-data .analysis{top:86px!important}

  #ydesk #yd-data .card:has(.dc496-idle) .cardbody{padding:14px 16px!important}
  #ydesk #yd-data .card:has(.dc496-idle) .row3{margin-bottom:8px!important}
  #ydesk #yd-data .card:has(.dc496-idle) .sectiontitle,
  #ydesk #yd-data .card:has(.dc496-idle) .dc496-scope-note,
  #ydesk #yd-data .card:has(.dc496-idle) .tablewrap{display:none!important}
  #ydesk #yd-data .card:has(.dc496-idle) .dc496-latest{margin-top:10px!important;background:#eef6ff!important;border-color:#d5e7fb!important;padding:10px 11px!important}
  #ydesk #yd-data .card:has(.dc496-idle) .pipeline{opacity:.62!important}

  #ydesk #yd-data .row3{gap:7px!important}
  #ydesk #yd-data .kpi{min-height:72px!important;padding:10px!important}
  #ydesk #yd-data .kpi strong{font-size:21px!important}
  #ydesk #yd-data .pipeline .stage{padding:7px 2px!important}

  #ydesk #yd-data .healthstrip{grid-template-columns:repeat(7,minmax(82px,1fr))!important}
  #ydesk #yd-data .hday{min-height:78px!important}
  #ydesk #yd-data .legend{padding-top:2px!important}
  #ydesk #yd-data .note.blue{border-radius:10px!important}

  #ydesk .fresh{position:relative!important;overflow:hidden!important}
  #ydesk .fresh:before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:#0b72f4;opacity:.8}
  #ydesk .frow{padding:1px 0!important}
  #ydesk .frow span{font-weight:650!important;color:#566e86!important}
  #ydesk .frow b{color:#21415f!important}

  @media(max-width:1380px){
    #ydesk #yd-data .datagrid{grid-template-columns:minmax(0,1.45fr) minmax(330px,.75fr)!important}
    #ydesk #yd-data .healthstrip{grid-template-columns:repeat(4,minmax(82px,1fr))!important}
  }
  @media(max-width:1180px){
    #ydesk #yd-data .datagrid{grid-template-columns:1fr!important}
    #ydesk #yd-data .analysis{position:static!important}
  }
}
</style>
'''


def inject_data_center_ui_v498(html:str)->str:
    if _MARKER in html:
        return html
    return html.replace('</head>',_STYLE+'</head>',1)
