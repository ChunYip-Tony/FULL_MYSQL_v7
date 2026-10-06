from __future__ import annotations

_MARKER = 'ydDataCenterUiV497'

_STYLE = r'''
<style id="ydDataCenterUiV497">
@media (min-width:760px){
  #ydesk .app{grid-template-columns:238px minmax(0,1fr)!important}
  #ydesk .side{padding:18px 14px!important;background:linear-gradient(180deg,#fff 0%,#fbfdff 100%)!important}
  #ydesk .brand{padding:0 10px 16px!important}
  #ydesk .brand h1{font-size:31px!important;line-height:1!important;letter-spacing:-1.1px!important}
  #ydesk .brand small{display:block!important;max-width:190px!important;font-size:11px!important;line-height:1.35!important;white-space:normal!important}
  #ydesk .navbtn{font-size:15px!important;padding:12px!important;border-radius:12px!important}
  #ydesk .navbtn.active{background:#e7f1ff!important;box-shadow:inset 0 0 0 1px #d3e6ff!important}
  #ydesk .fresh{border-radius:14px!important;padding:12px!important;background:#fff!important;box-shadow:0 4px 14px rgba(15,47,75,.05)!important}
  #ydesk .fresh h4{font-size:12px!important;letter-spacing:.03em!important;margin-bottom:8px!important}
  #ydesk .frow{font-size:11px!important;margin:7px 0!important;gap:8px!important}
  #ydesk .frow b{font-size:11px!important;white-space:nowrap!important;font-variant-numeric:tabular-nums!important}
  #ydesk .version{font-size:10px!important;line-height:1.45!important}

  #ydesk #yd-data .pagehead{align-items:center!important;margin-bottom:15px!important}
  #ydesk #yd-data .pagehead h2{font-size:36px!important;letter-spacing:-1px!important}
  #ydesk #yd-data .pagehead p{font-size:13px!important;max-width:820px!important}
  #ydesk #yd-data .pagehead .btn{min-height:42px!important;padding:0 16px!important;border-radius:11px!important;background:#fff!important;box-shadow:0 2px 8px rgba(16,35,61,.06)!important}
  #ydesk #yd-data .datagrid{display:grid!important;grid-template-columns:minmax(0,1.58fr) minmax(360px,.82fr)!important;gap:14px!important;align-items:start!important}
  #ydesk #yd-data .card{border-radius:16px!important;border:1px solid #dbe6f0!important;box-shadow:0 7px 22px rgba(22,49,79,.06)!important;background:#fff!important}
  #ydesk #yd-data .cardhead{padding:14px 16px!important;background:linear-gradient(180deg,#fff,#fbfdff)!important}
  #ydesk #yd-data .cardhead h3{font-size:16px!important;letter-spacing:-.15px!important}
  #ydesk #yd-data .cardbody{padding:16px!important}
  #ydesk #yd-data .badge{font-size:10px!important;padding:6px 9px!important}

  #ydesk #yd-data .upload{min-height:245px!important;border:1.5px dashed #b8cce0!important;border-radius:14px!important;background:linear-gradient(180deg,#fbfdff,#f7fbff)!important;padding:22px 20px!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important}
  #ydesk #yd-data .upload h3{font-size:18px!important;margin:4px 0 2px!important}
  #ydesk #yd-data .upload p{font-size:11px!important;margin:2px 0 10px!important;text-align:center!important;color:#70839a!important}
  #ydesk #yd-data .upload input[type=file]{font-size:12px!important;max-width:100%!important}
  #ydesk #yd-data .upload .input{height:42px!important;border-radius:10px!important;font-size:13px!important}
  #ydesk #yd-data #ydUpload{min-height:44px!important;padding:0 18px!important;border-radius:10px!important;font-size:13px!important;box-shadow:0 5px 12px rgba(11,114,244,.18)!important}
  #ydesk #yd-data #ydUploadResult{margin-top:11px!important;text-align:center!important;font-size:11px!important;line-height:1.45!important;color:#5c7188!important}
  #ydesk #yd-data #ydUploadResult b{font-size:12px!important;color:#163552!important}

  #ydesk #yd-data .analysis{position:sticky!important;top:88px!important}
  #ydesk #yd-data .row3{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:8px!important}
  #ydesk #yd-data .kpi{min-height:82px!important;border-radius:11px!important;background:#fbfdff!important;padding:11px!important}
  #ydesk #yd-data .kpi label{font-size:9px!important}
  #ydesk #yd-data .kpi strong{font-size:22px!important;line-height:1.05!important;overflow-wrap:anywhere!important}
  #ydesk #yd-data .pipeline{display:grid!important;grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:5px!important}
  #ydesk #yd-data .pipeline .stage{min-width:0!important;padding:8px 3px!important;border-radius:8px!important;font-size:8px!important;text-align:center!important;white-space:normal!important;line-height:1.15!important}
  #ydesk #yd-data .sectiontitle{font-size:12px!important;letter-spacing:.02em!important;margin-top:13px!important}
  #ydesk #yd-data table{table-layout:fixed!important;width:100%!important}
  #ydesk #yd-data th,#ydesk #yd-data td{white-space:normal!important;overflow-wrap:anywhere!important;font-size:10px!important;padding:8px!important}

  #ydesk #yd-data .healthstrip{display:grid!important;grid-template-columns:repeat(7,minmax(72px,1fr))!important;gap:6px!important;overflow:visible!important}
  #ydesk #yd-data .hday{min-width:0!important;border-radius:10px!important;padding:8px 7px!important}
  #ydesk #yd-data .hday .wd{font-size:8px!important}
  #ydesk #yd-data .hday .dt{font-size:12px!important;font-weight:900!important}
  #ydesk #yd-data .srcdots{gap:3px!important;flex-wrap:wrap!important}
  #ydesk #yd-data .sd{font-size:7px!important}
  #ydesk #yd-data .legend{font-size:9px!important;gap:9px!important;line-height:1.35!important}

  @media(max-width:1280px){
    #ydesk .app{grid-template-columns:210px minmax(0,1fr)!important}
    #ydesk #yd-data .datagrid{grid-template-columns:1fr!important}
    #ydesk #yd-data .analysis{position:static!important}
    #ydesk #yd-data .healthstrip{grid-template-columns:repeat(4,minmax(72px,1fr))!important}
  }
}
</style>
'''


def inject_data_center_ui(html: str) -> str:
    if _MARKER in html:
        return html
    return html.replace('</head>', _STYLE + '</head>', 1)
