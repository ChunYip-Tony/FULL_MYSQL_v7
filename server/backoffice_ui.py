from __future__ import annotations


def backoffice_html(version: str = "") -> str:
    v = str(version or "")
    return BACKOFFICE_HTML.replace("__VERSION__", v)


BACKOFFICE_HTML = r'''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>FULL MYSQL · Dockside Backoffice</title>
<style>
:root{--bg:#f2f5f4;--paper:#fff;--ink:#153638;--muted:#6c7e7d;--line:#dbe6e2;--deep:#0b343a;--deep2:#103f46;--sea:#167985;--sea2:#2ca0a8;--foam:#e9f5f3;--green:#116b49;--greenbg:#e8f6ee;--amber:#946000;--amberbg:#fff4df;--red:#bd4f44;--redbg:#fff0ed;--blue:#275bb5;--bluebg:#edf3ff;--shadow:0 10px 28px rgba(9,49,54,.06)}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}body{font-size:16px;line-height:1.45}button,input,select,textarea{font:inherit;color:inherit}button{cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid rgba(44,160,168,.18);outline-offset:2px}
.shell{max-width:1720px;margin:auto;padding:10px 10px 70px}.appbar{background:linear-gradient(135deg,var(--deep),var(--deep2));color:#fff;border-radius:18px;overflow:hidden;box-shadow:var(--shadow)}.top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:12px 14px}.brand{display:flex;gap:10px;align-items:center}.mark{width:40px;height:40px;border-radius:12px;background:rgba(255,255,255,.1);display:grid;place-items:center;font-size:20px}.brand strong{display:block;font-size:15px}.brand small{display:block;color:rgba(255,255,255,.67);margin-top:2px}.topstat{display:flex;gap:6px;flex-wrap:wrap}.glass{border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.08);border-radius:999px;padding:6px 9px;font-size:10px;font-weight:800}.searchbar{display:flex;gap:7px;padding:0 14px 10px}.searchbar input{flex:1;min-width:0;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.13);color:#fff;border-radius:11px;padding:10px 12px}.searchbar input::placeholder{color:rgba(255,255,255,.55)}
.nav{display:flex;gap:3px;overflow:auto;padding:0 10px 10px}.nav button{border:0;background:transparent;color:#d2e6e6;border-radius:8px;padding:9px 11px;white-space:nowrap;font-size:13px}.nav button.on{background:#fff;color:var(--deep);font-weight:800}.btn{min-height:36px;border:1px solid var(--line);background:#fff;border-radius:9px;padding:7px 10px;font-weight:750}.btn.primary{background:var(--sea);border-color:var(--sea);color:#fff}.btn.soft{background:var(--foam);border-color:transparent;color:var(--sea)}.btn.danger{background:var(--red);border-color:var(--red);color:#fff}.btn.small{min-height:32px;font-size:11px;padding:6px 9px}.btn:disabled{opacity:.5;cursor:not-allowed}
.pill{display:inline-flex;align-items:center;border-radius:999px;padding:5px 8px;font-size:9px;font-weight:800;white-space:nowrap}.pill.green{background:var(--greenbg);color:var(--green)}.pill.amber{background:var(--amberbg);color:var(--amber)}.pill.red{background:var(--redbg);color:var(--red)}.pill.blue{background:var(--bluebg);color:var(--blue)}.pill.sea{background:var(--foam);color:var(--sea)}
.statusstrip{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:9px}.stat{background:#fff;border:1px solid var(--line);border-radius:12px;padding:9px 10px}.stat small{display:block;color:var(--muted);font-size:8px}.stat b{display:block;font-size:17px;margin-top:2px}.stat span{display:block;color:var(--muted);font-size:8px;margin-top:2px}
.view{display:none}.view.on{display:block}.subview{display:none}.subview.on{display:block}.panel{margin-top:9px;background:#fff;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:var(--shadow)}.panelhead{display:flex;align-items:flex-start;justify-content:space-between;gap:9px;flex-wrap:wrap;padding:11px 12px;border-bottom:1px solid var(--line)}.title{font-size:19px;font-weight:850}.sub{font-size:11px;color:var(--muted);margin-top:3px}.tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.toolrow{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:8px 11px;border-bottom:1px solid var(--line)}.filters{display:flex;gap:5px;flex-wrap:wrap}.filter{border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 10px;font-size:11px}.filter.on{background:var(--foam);border-color:transparent;color:var(--sea);font-weight:800}.select{border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 9px;font-size:12px}.qa-search{min-width:220px;border:1px solid var(--line);background:#fff;border-radius:8px;padding:8px 10px;font-size:12px}
.tablewrap{overflow:auto}.table{width:100%;min-width:980px;border-collapse:collapse;font-size:12px}.table th,.table td{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}.table th{background:#f7faf9;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.035em}.table tbody tr:hover td{background:#fbfdfc}.table tbody tr.velocity-active td{background:#f2fbf8}.table tbody tr.velocity-active:hover td{background:#e8f7f2}.table tbody tr.velocity-active td:first-child{box-shadow:inset 3px 0 0 #6aaea4}.name{font-weight:800;font-size:13px}.meta{font-size:10px;color:var(--muted);margin-top:2px}.num{font-variant-numeric:tabular-nums}.linkbtn{border:0;background:transparent;padding:2px 0;text-decoration:underline;text-decoration-style:dotted;text-underline-offset:3px;font-weight:850}.suggest{font-weight:900;color:var(--sea);font-size:11px}.empty{padding:28px;text-align:center;color:var(--muted);font-size:10px}.loading{padding:22px;color:var(--muted);font-size:10px}.error{padding:10px 12px;background:var(--redbg);color:var(--red);font-size:10px;border-bottom:1px solid #f0cac4}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:11px}.kpi{border:1px solid var(--line);border-radius:10px;padding:8px;background:#fbfdfc}.kpi small{display:block;color:var(--muted);font-size:8px}.kpi b{display:block;font-size:14px;margin-top:2px}.kpi span{display:block;color:var(--muted);font-size:8px;margin-top:2px}
.reasonlist{display:grid;gap:6px}.reason{display:grid;grid-template-columns:auto 1fr;gap:7px;border:1px solid var(--line);border-radius:10px;padding:8px;background:#fbfdfc}.rdot{width:7px;height:7px;border-radius:50%;background:var(--sea);margin-top:4px}.reason b{display:block;font-size:10px}.reason span{display:block;color:var(--muted);font-size:9px;margin-top:1px}.sectiontitle{font-size:10px;font-weight:850;margin:13px 0 6px}.detailgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.detail{border:1px solid var(--line);border-radius:9px;padding:8px;background:#fbfdfc}.detail small{display:block;color:var(--muted);font-size:8px}.detail b{display:block;font-size:10px;margin-top:2px}.calc{border:1px dashed #b9d4cf;background:#f4fbf9;border-radius:9px;padding:8px;margin-top:8px;font-size:9px;color:var(--deep)}.logconsole{background:#0b272b;color:#d8efec;border-radius:10px;padding:9px;font:9px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-height:230px;overflow:auto}
.dbcardgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:11px}.dbcard{border:1px solid var(--line);background:#fff;border-radius:13px;padding:13px;text-align:left;display:flex;gap:11px;align-items:flex-start;box-shadow:0 4px 14px rgba(9,49,54,.03)}.dbcard:hover{border-color:#a8cbc6;background:#fbfdfc}.dbcard .dbicon{font-size:24px;line-height:1}.dbcard span:last-child{display:block}.dbcard small{display:block;color:var(--muted);font-size:9px;font-weight:800;text-transform:uppercase}.dbcard b{display:block;font-size:14px;margin-top:2px}.dbcard em{display:block;color:var(--muted);font-size:10px;font-style:normal;margin-top:3px}.dboverviewgrid{display:grid;grid-template-columns:1fr;gap:9px;padding:0 11px 11px}.dbsummary{border:1px solid var(--line);border-radius:12px;padding:0 10px 10px;background:#fbfdfc}.uploadgrid{display:grid;gap:9px;padding:11px}.drop{border:2px dashed #bad5d1;background:#f8fcfb;border-radius:13px;padding:18px;text-align:center}.drop .ico{font-size:29px}.drop h3{font-size:14px;margin:6px 0 2px}.drop p{font-size:9px;color:var(--muted);margin:0}.drop input{display:block;width:100%;margin-top:10px;border:1px solid var(--line);border-radius:9px;padding:8px;background:#fff}.upload-actions{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;margin-top:9px}.uploadresult{border:1px solid var(--line);border-radius:11px;padding:9px;background:#fbfdfc}.filelist{display:grid;gap:5px;margin-top:7px}.filerow{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--line);padding:6px 0;font-size:9px}.filerow:last-child{border:0}
.batchgrid{display:grid;gap:7px;padding:10px}.batch{border:1px solid var(--line);border-radius:11px;padding:9px;background:#fbfdfc}.batchtop{display:flex;justify-content:space-between;gap:8px}.batchid{font-weight:850;font-size:11px}.progress{height:6px;border-radius:999px;background:#e7efeb;overflow:hidden;margin-top:7px}.progress span{display:block;height:100%;background:linear-gradient(90deg,var(--sea),var(--sea2))}.batchmeta{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:7px}.batchmeta div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px}.batchmeta small{display:block;color:var(--muted);font-size:7px}.batchmeta b{display:block;font-size:9px;margin-top:1px}
.drawerback{position:fixed;inset:0;background:rgba(7,43,47,.24);z-index:30;display:none}.drawerback.on{display:block}.drawer{position:fixed;right:0;top:0;bottom:0;width:min(94vw,570px);background:#fff;z-index:31;transform:translateX(105%);transition:.18s;box-shadow:-20px 0 50px rgba(8,44,48,.18);display:flex;flex-direction:column}.drawer.on{transform:translateX(0)}.drawerhead{padding:12px 13px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:9px}.drawertitle{font-size:15px;font-weight:850}.drawersub{font-size:9px;color:var(--muted);margin-top:2px}.drawerbody{padding:12px;overflow:auto;flex:1}.drawerfoot{padding:10px 12px;border-top:1px solid var(--line);display:flex;justify-content:flex-end;gap:6px}.formfield{margin-top:9px}.formfield label{display:block;font-size:9px;font-weight:800;margin-bottom:4px}.formfield input,.formfield textarea,.formfield select{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}.toast{position:fixed;right:12px;bottom:12px;z-index:140;background:var(--deep);color:#fff;border-radius:9px;padding:9px 10px;font-size:10px;opacity:0;transform:translateY(8px);transition:.18s;pointer-events:none}.toast.on{opacity:1;transform:none}

/* QA detail readability */
.drawer{width:min(96vw,680px)}
.drawerhead{padding:15px 16px}.drawertitle{font-size:18px}.drawersub{font-size:11px;line-height:1.35}
.drawerbody{padding:16px}.drawerfoot{padding:12px 16px;background:#fff;position:sticky;bottom:0}
.formfield{margin-top:12px}.formfield label{font-size:11px;margin-bottom:6px}
.formfield input,.formfield textarea,.formfield select{font-size:14px;line-height:1.3;padding:11px 12px;border-radius:10px}
.formfield textarea{min-height:78px}.sectiontitle{font-size:12px;margin:16px 0 7px}
.qa-identity{border:1px solid #b7d8d3;background:linear-gradient(135deg,#f2fbf9,#fff);border-radius:14px;padding:13px 14px;margin-bottom:12px}
.qa-name{font-size:18px;font-weight:900;line-height:1.2}.qa-zh{font-size:15px;font-weight:750;margin-top:4px}
.qa-idmeta{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px}.qa-idmeta span{font-size:10px;font-weight:800;background:#fff;border:1px solid var(--line);border-radius:999px;padding:4px 7px}
.qa-step{border:1px solid var(--line);border-radius:13px;padding:13px;margin-top:11px;background:#fff}
.qa-stephead{display:flex;gap:9px;align-items:flex-start;margin-bottom:8px}.qa-stepnum{display:grid;place-items:center;min-width:24px;height:24px;border-radius:50%;background:var(--sea);color:#fff;font-size:11px;font-weight:900}
.qa-stephead b{display:block;font-size:13px}.qa-stephead span:last-child{display:block;color:var(--muted);font-size:10px;line-height:1.4;margin-top:2px}
.qa-reasons{display:grid;gap:6px}.qa-reason{border-left:4px solid #d79b2e;background:#fff8e8;border-radius:8px;padding:9px 10px;font-size:11px;line-height:1.4}
.qa-technical{margin-top:8px}.qa-technical summary,.qa-advanced summary{cursor:pointer;font-size:10px;font-weight:850;color:var(--muted)}
.qa-technical .calc{font-size:9px;overflow-wrap:anywhere}.qa-required{display:inline-block;margin-left:6px;padding:2px 6px;border-radius:999px;background:#fff1d8;color:#8a5c00;font-size:8px;font-weight:900;vertical-align:middle}
.qa-field-help{font-size:9px;color:var(--muted);line-height:1.4;margin-top:5px}
.qa-advanced{margin-top:12px;border:1px dashed #bfd6d2;background:#f8fcfb;border-radius:10px;padding:10px}
.qa-confirm{display:flex;gap:9px;align-items:flex-start;margin-top:8px;font-size:11px;line-height:1.45}.qa-confirm input{width:19px;height:19px;margin-top:0;flex:0 0 auto}
.qa-scope{font-size:9px;color:var(--muted);line-height:1.45;margin-top:8px}.qa-inline-feedback{display:none;flex:1 0 100%;width:100%;border-radius:9px;padding:8px 10px;font-size:10px;font-weight:800;line-height:1.4;border:1px solid var(--line);background:#f7faf9;color:var(--deep)}.qa-inline-feedback.on{display:block}.qa-inline-feedback.error{background:var(--redbg);border-color:#f1c9c4;color:var(--red)}.qa-inline-feedback.working{background:var(--bluebg);border-color:#c8d9f2;color:#245b8f}.qa-inline-feedback.success{background:var(--greenbg);border-color:#bfe4cf;color:var(--green)}
.detailgrid.qa-detailgrid{grid-template-columns:repeat(2,minmax(0,1fr))}.qa-detailgrid .detail small{font-size:9px}.qa-detailgrid .detail b{font-size:12px}
.qa-cn-list{font-size:10px;color:var(--muted);margin-top:2px}
@media(max-width:620px){.drawer{width:100vw}.drawerbody{padding:12px}.qa-detailgrid{grid-template-columns:1fr}.qa-name{font-size:17px}.qa-zh{font-size:14px}}

/* Mobile-only Backoffice: independent Home → List → Detail; desktop remains unchanged */
.mobilehome,.mobile-listpage,.mobile-detailpage{display:none}
@media(max-width:759px){
  html,body{overflow-x:hidden}
  body{background:#f5f8f7}
  .shell{max-width:520px;margin:auto;padding:9px 9px 76px}
  .appbar,.view{display:none!important}

  .mobilehome.on,.mobile-listpage.on,.mobile-detailpage.on{display:block}
  .m-topbar{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin:2px 2px 12px}
  .m-brand strong{display:block;font-size:20px;line-height:1.05}.m-brand span{display:block;font-size:11px;color:var(--muted);margin-top:4px}
  .m-status{display:inline-flex;align-items:center;min-height:28px;padding:5px 9px;border:1px solid var(--line);border-radius:999px;background:#fff;font-size:10px;font-weight:900;white-space:nowrap}
  .m-status.good{background:var(--greenbg);border-color:#bfe4cf;color:var(--green)}.m-status.bad{background:var(--redbg);border-color:#f1c9c4;color:var(--red)}
  .m-searchbox{background:#fff;border:1px solid var(--line);border-radius:17px;padding:11px;margin-bottom:10px}
  .m-label{display:block;font-size:9px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
  .m-searchrow{display:flex;gap:7px;margin-top:7px}.m-searchrow input{min-width:0;flex:1;min-height:48px;border:1px solid var(--line);border-radius:12px;padding:10px 11px;font-size:16px;background:#fff}.m-searchrow button{min-width:76px;min-height:48px}
  .m-hint{display:flex;justify-content:space-between;gap:10px;font-size:10px;color:var(--muted);margin-top:7px}

  .m-spotlight{width:100%;min-height:78px;border:1px solid #b8d7d2;background:linear-gradient(135deg,#f2fbf9,#fff);border-radius:17px;padding:13px 14px;text-align:left;display:flex;align-items:center;justify-content:space-between;gap:10px}
  .m-spotlight small{display:block;font-size:9px;font-weight:900;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
  .m-spotlight b{display:block;font-size:15px;line-height:1.25;margin-top:3px}.m-spotlight em{display:block;font-size:10px;line-height:1.35;color:var(--muted);font-style:normal;margin-top:3px}.m-arrow{font-size:24px;color:var(--sea);flex:0 0 auto}
  .m-modgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:10px}
  .m-module{min-height:112px;border:1px solid var(--line);background:#fff;border-radius:17px;padding:14px;text-align:left;box-shadow:0 4px 14px rgba(9,49,54,.025)}
  .m-module:active,.m-row:active{transform:scale(.987)}
  .m-module .ico{display:block;font-size:23px;line-height:1}.m-module b{display:block;font-size:15px;line-height:1.18;margin-top:10px}.m-module span:last-child{display:block;font-size:10px;line-height:1.35;color:var(--muted);margin-top:5px}
  .m-module-meta{font-weight:850;color:var(--sea)!important}

  .m-pagehead{display:flex;align-items:center;gap:10px;margin:2px 0 10px}
  .m-back{width:46px;height:46px;min-width:46px;border:1px solid var(--line);background:#fff;border-radius:13px;font-size:20px;font-weight:900}
  .m-pagetitle{font-size:20px;font-weight:900;line-height:1.1}.m-pagesub{font-size:10px;line-height:1.35;color:var(--muted);margin-top:3px}
  .m-chipbar{display:flex;gap:7px;overflow-x:auto;padding:1px 0 8px;scrollbar-width:none}.m-chipbar::-webkit-scrollbar{display:none}
  .m-chip{flex:0 0 auto;min-height:39px;padding:7px 12px;border:1px solid var(--line);background:#fff;border-radius:999px;font-size:11px;font-weight:850}
  .m-chip.on{background:var(--foam);border-color:#aad2cc;color:var(--sea)}.m-qatools{display:none;grid-template-columns:minmax(0,1fr) 145px;gap:7px;margin:0 0 9px}.m-qatools.on{display:grid}.m-qatools input,.m-qatools select{min-width:0;min-height:44px;border:1px solid var(--line);border-radius:12px;background:#fff;padding:9px 10px;font-size:13px}.m-qatools input{font-size:16px}
  .m-list{display:grid;gap:9px}
  .m-row{width:100%;min-height:82px;border:1px solid var(--line);background:#fff;border-radius:16px;padding:13px;text-align:left}
  .m-row-main{display:flex;gap:10px;align-items:center}.m-row-copy{min-width:0;flex:1}
  .m-row-code{font-size:17px;font-weight:900;line-height:1.15;overflow-wrap:anywhere}.m-row-name{font-size:13px;font-weight:800;line-height:1.3;margin-top:4px}.m-row-cn{font-size:12px;line-height:1.3;color:var(--muted);margin-top:2px}.m-row-meta{font-size:10px;line-height:1.4;color:var(--muted);margin-top:6px}
  .m-badge{display:inline-flex;align-items:center;justify-content:center;min-height:24px;padding:4px 8px;border:1px solid var(--line);border-radius:999px;background:#f8faf9;font-size:9px;font-weight:900;white-space:nowrap}.m-badge.good{background:var(--greenbg);border-color:#bfe4cf;color:var(--green)}.m-badge.warn{background:var(--amberbg);border-color:#efd49d;color:var(--amber)}.m-badge.bad{background:var(--redbg);border-color:#f1c9c4;color:var(--red)}
  .m-dh-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}.m-dh-chip{display:flex;align-items:center;justify-content:space-between;gap:4px;padding:5px 6px;border:1px solid var(--line);border-radius:9px;background:#f8faf9;font-size:8px;font-weight:850}.m-dh-chip b{font-size:8px}.m-dh-chip.good{background:var(--greenbg);border-color:#c7e9d5;color:var(--green)}.m-dh-chip.bad{background:var(--redbg);border-color:#f1c9c4;color:var(--red)}.m-dh-chip.warn{background:var(--amberbg);border-color:#efd49d;color:var(--amber)}
  .m-empty,.m-loading{padding:28px 16px;text-align:center;border:1px solid var(--line);background:#fff;border-radius:16px;color:var(--muted);font-size:11px}
  .m-error{padding:12px;border:1px solid #f1c9c4;background:var(--redbg);border-radius:14px;color:var(--red);font-size:11px}

  .m-detailcard{background:#fff;border:1px solid var(--line);border-radius:17px;padding:14px}
  .m-detailgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}
  .m-metric{min-width:0;padding:11px;border-radius:13px;background:#f7faf9;border:1px solid #e5eeeb}.m-metric small{display:block;font-size:8px;font-weight:900;letter-spacing:.045em;text-transform:uppercase;color:var(--muted)}.m-metric b{display:block;font-size:18px;line-height:1.12;margin-top:4px;overflow-wrap:anywhere}.m-metric span{display:block;font-size:9px;line-height:1.3;color:var(--muted);margin-top:4px}
  .m-detailsection{margin-top:14px;padding-top:13px;border-top:1px solid var(--line)}.m-detailsection h3{font-size:11px;margin:0 0 6px}.m-detailsection p{font-size:11px;line-height:1.5;color:var(--muted);margin:0}
  .m-action{width:100%;min-height:48px;margin-top:10px;border-radius:12px;font-weight:850}.m-action.primary{border:1px solid var(--sea);background:var(--sea);color:#fff}.m-action.secondary{border:1px solid var(--line);background:#fff}

  .m-bottomnav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin-top:14px;padding-top:10px;border-top:1px solid var(--line)}
  .m-bottomnav button{min-height:52px;border:0;background:transparent;border-radius:12px;font-size:10px;font-weight:850;line-height:1.2}.m-bottomnav button.on{background:var(--foam);color:var(--sea)}

  .btn{min-height:44px;padding:9px 11px}.btn.small{min-height:40px;font-size:11px}
  .drawerback.on{display:none!important}
  .drawer{display:none;left:0;right:0;top:0;bottom:0;width:100vw!important;max-width:none;transform:none!important;transition:none;box-shadow:none;z-index:80}
  .drawer.on{display:flex}
  .drawerhead{padding:12px 13px;align-items:center;background:#fff;position:sticky;top:0;z-index:2}.drawertitle{font-size:18px}.drawersub{font-size:11px}.drawerhead .btn{min-width:64px}
  .drawerbody{padding:12px;background:#f7faf9}.drawerfoot{padding:10px 12px;gap:7px;flex-direction:column;align-items:stretch}.drawerfoot .btn{width:100%}
  .detailgrid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.detail{padding:10px;border-radius:11px}.detail small{font-size:9px}.detail b{font-size:12px}
  .qa-step{padding:12px}.qa-name{font-size:17px}.qa-zh{font-size:14px}.qa-detailgrid{grid-template-columns:1fr 1fr!important}
  .toast{left:10px;right:10px;bottom:calc(12px + env(safe-area-inset-bottom));text-align:center;font-size:11px}

  /* Mobile polish · touch-first, compact, safe-area aware */
  body{font-size:15px;-webkit-tap-highlight-color:transparent}
  .shell{padding-top:max(8px,env(safe-area-inset-top));padding-left:max(9px,env(safe-area-inset-left));padding-right:max(9px,env(safe-area-inset-right));padding-bottom:calc(86px + env(safe-area-inset-bottom))}
  .m-topbar{align-items:center;margin:1px 1px 10px}
  .m-brand strong{font-size:19px;letter-spacing:-.025em}.m-brand span{font-size:10px}
  .m-status{min-height:30px;padding:5px 10px;box-shadow:0 2px 8px rgba(9,49,54,.04)}
  .m-searchbox{border-radius:16px;padding:10px;box-shadow:0 5px 18px rgba(9,49,54,.035)}
  .m-searchrow{margin-top:6px}.m-searchrow input{min-height:46px;border-radius:11px}.m-searchrow button{min-width:72px;min-height:46px;border-radius:11px}
  .m-hint{font-size:9px;margin-top:6px}
  .m-spotlight{min-height:72px;border-radius:15px;padding:12px 13px;box-shadow:0 5px 18px rgba(9,49,54,.035)}
  .m-spotlight b{font-size:14px}.m-spotlight em{font-size:9px}
  .m-modgrid{gap:8px;margin-top:9px}
  .m-module{min-height:102px;border-radius:15px;padding:12px;box-shadow:0 5px 18px rgba(9,49,54,.035);transition:transform .08s ease,border-color .08s ease,background .08s ease}
  .m-module .ico{font-size:21px}.m-module b{font-size:14px;margin-top:8px}.m-module span:last-child{font-size:9px;margin-top:4px}
  .m-module:active,.m-row:active,.m-spotlight:active{transform:scale(.985);background:#fbfdfc}
  .m-pagehead{position:sticky;top:0;z-index:12;margin:0 -1px 9px;padding:7px 1px;background:linear-gradient(180deg,#f5f8f7 82%,rgba(245,248,247,0));backdrop-filter:blur(8px)}
  .m-back{width:44px;height:44px;min-width:44px;border-radius:12px;box-shadow:0 2px 8px rgba(9,49,54,.035)}
  .m-pagetitle{font-size:19px;letter-spacing:-.02em}.m-pagesub{font-size:10px;max-width:290px}
  .m-chipbar{margin:0 -1px 1px;padding:0 1px 8px}
  .m-chip{min-height:37px;padding:7px 11px;font-size:10px}
  .m-qatools{grid-template-columns:minmax(0,1fr) 132px;gap:6px}.m-qatools input,.m-qatools select{min-height:42px;border-radius:11px;font-size:12px}.m-qatools input{font-size:16px}
  .m-list{gap:7px}
  .m-row{min-height:76px;border-radius:14px;padding:11px 12px;box-shadow:0 3px 12px rgba(9,49,54,.025);transition:transform .08s ease,background .08s ease}
  .m-row-main{gap:8px}.m-row-code{font-size:16px}.m-row-name{font-size:13px;margin-top:3px}.m-row-cn{font-size:11px}.m-row-meta{font-size:9px;margin-top:5px}
  .m-badge{min-height:22px;padding:3px 7px;font-size:8px}
  .m-arrow{font-size:22px}
  .m-dh-grid{gap:4px;margin-top:7px}.m-dh-chip{padding:5px;font-size:8px}
  .m-detailcard{border-radius:15px;padding:12px;box-shadow:0 5px 18px rgba(9,49,54,.035)}
  .m-detailgrid{gap:7px;margin-top:10px}.m-metric{padding:10px;border-radius:12px}.m-metric b{font-size:17px}.m-metric span{font-size:8px}
  .m-detailsection{margin-top:12px;padding-top:11px}.m-detailsection h3{font-size:11px}.m-detailsection p{font-size:10px}
  .m-action{min-height:50px;border-radius:12px;font-size:14px}
  .m-bottomnav{position:sticky;bottom:0;z-index:20;margin:14px -9px calc(-76px - env(safe-area-inset-bottom));padding:7px 8px calc(7px + env(safe-area-inset-bottom));border-top:1px solid rgba(219,230,226,.95);background:rgba(255,255,255,.96);backdrop-filter:blur(14px);box-shadow:0 -8px 24px rgba(9,49,54,.07)}
  .m-bottomnav button{min-height:50px;border-radius:11px;font-size:9px}
  .m-bottomnav button.on{background:var(--foam);box-shadow:inset 0 0 0 1px #c5e1dc}
  .drawerhead{padding-top:max(12px,env(safe-area-inset-top))}
  .drawerfoot{padding-bottom:calc(10px + env(safe-area-inset-bottom))}

  /* Obvious mobile visual refresh */
  body{
    background:
      radial-gradient(circle at 15% -5%,rgba(44,160,168,.18),transparent 34%),
      linear-gradient(180deg,#eef8f6 0,#f7faf9 230px,#f3f6f5 100%);
  }
  .mobilehome.on{position:relative}
  .mobilehome.on:before{
    content:"";position:absolute;left:-9px;right:-9px;top:-8px;height:154px;z-index:-1;
    background:linear-gradient(145deg,#0b343a 0%,#10606a 55%,#1b8e98 100%);
    border-radius:0 0 28px 28px;
    box-shadow:0 14px 34px rgba(11,52,58,.14)
  }
  .m-topbar{color:#fff;padding:5px 4px 7px}
  .m-brand strong{font-size:22px;letter-spacing:-.04em}
  .m-brand span{color:rgba(255,255,255,.72)}
  .m-status{background:rgba(255,255,255,.12)!important;border-color:rgba(255,255,255,.22)!important;color:#fff!important;box-shadow:none}
  .m-status.good:before{content:"●";margin-right:5px;color:#83efb8}
  .m-status.bad:before{content:"●";margin-right:5px;color:#ffaaa0}

  .m-searchbox{
    border:0;
    background:#fff;
    box-shadow:0 14px 34px rgba(11,52,58,.13);
    border-radius:19px;
    padding:12px
  }
  .m-label{color:#1a6c74;font-size:10px}
  .m-searchrow input{background:#f5f9f8;border:2px solid #d8ebe7}
  .m-searchrow input:focus{border-color:#59aaa9;background:#fff}
  .m-searchrow button{background:linear-gradient(135deg,#167985,#0f646e);box-shadow:0 7px 16px rgba(22,121,133,.22)}
  .m-hint span:first-child:before{content:"⚡ ";color:#167985}

  .m-spotlight{
    margin-top:11px;
    border:0;
    color:#fff;
    background:linear-gradient(135deg,#173f73 0%,#275bb5 60%,#4b75c7 100%);
    box-shadow:0 12px 28px rgba(39,91,181,.18);
    min-height:84px
  }
  .m-spotlight small,.m-spotlight em{color:rgba(255,255,255,.72)}
  .m-spotlight b{font-size:16px}
  .m-spotlight .m-arrow{color:#fff;background:rgba(255,255,255,.13);width:34px;height:34px;border-radius:50%;display:grid;place-items:center}

  .m-modgrid{gap:10px;margin-top:12px}
  .m-module{
    position:relative;
    min-height:118px;
    overflow:hidden;
    border:0;
    background:#fff;
    border-radius:19px;
    padding:14px;
    box-shadow:0 10px 26px rgba(10,56,61,.08)
  }
  .m-module:after{
    content:"›";position:absolute;right:11px;top:10px;width:25px;height:25px;border-radius:50%;
    display:grid;place-items:center;background:#f1f7f6;color:#357f83;font-size:18px;font-weight:900
  }
  .m-module .ico{
    width:42px;height:42px;border-radius:13px;display:grid;place-items:center;
    font-size:21px;background:#eaf6f4
  }
  .m-module b{font-size:15px;margin-top:11px;letter-spacing:-.015em}
  .m-module span:last-child{font-size:10px}
  .m-module:nth-child(1) .ico{background:#e8f6ee}
  .m-module:nth-child(2) .ico{background:#fff4df}
  .m-module:nth-child(3) .ico{background:#edf3ff}
  .m-module:nth-child(4) .ico{background:#f0ecff}
  .m-module:nth-child(5) .ico{background:#eaf6f4}
  .m-module:nth-child(6) .ico{background:#fff0ed}
  .m-module:nth-child(7) .ico{background:#f4f1ea}
  .m-module:nth-child(8) .ico{background:#edf3ff}
  .m-module-meta{display:inline-block!important;width:auto;margin-top:7px!important;padding:3px 7px;border-radius:999px;background:#fff4df;color:#8a5c00!important}

  .m-pagehead{
    margin:0 -9px 10px;
    padding:calc(8px + env(safe-area-inset-top)) 10px 10px;
    background:linear-gradient(135deg,#0b343a,#126b74);
    color:#fff;
    box-shadow:0 8px 22px rgba(11,52,58,.12)
  }
  .m-back{border:0;background:rgba(255,255,255,.12);color:#fff;box-shadow:none}
  .m-pagesub{color:rgba(255,255,255,.7)}
  .m-chipbar{padding:3px 1px 10px}
  .m-chip{background:#fff;box-shadow:0 3px 10px rgba(9,49,54,.04)}
  .m-chip.on{background:#126f78;color:#fff;border-color:#126f78;box-shadow:0 5px 14px rgba(18,111,120,.18)}

  .m-list{gap:9px}
  .m-row{
    border:0;
    border-left:4px solid #c9dfdc;
    border-radius:16px;
    padding:12px 12px 12px 13px;
    box-shadow:0 7px 20px rgba(9,49,54,.055)
  }
  .m-row:hover{border-left-color:#58a6a4}
  .m-row-code{font-size:17px;color:#0d545b}
  .m-row-name{font-size:14px}
  .m-row-meta{background:#f5f9f8;border-radius:9px;padding:5px 7px;margin-top:7px}
  .m-badge.good{background:#dff4e8;border-color:#b8e2c8}
  .m-badge.warn{background:#fff0cb;border-color:#efd18c}
  .m-badge.bad{background:#ffe5e0;border-color:#f0bcb4}

  .m-detailcard{
    border:0;
    border-radius:19px;
    box-shadow:0 10px 28px rgba(9,49,54,.08)
  }
  .m-detailgrid{gap:8px}
  .m-metric{
    background:linear-gradient(180deg,#fbfdfc,#f2f7f5);
    border:1px solid #dbe9e5;
    border-radius:14px
  }
  .m-metric small{color:#557371}
  .m-metric b{font-size:19px;color:#0b444a}
  .m-detailsection h3{font-size:12px;color:#0d5a61}

  .m-action.primary{
    border:0;
    background:linear-gradient(135deg,#167985,#0f626b);
    box-shadow:0 8px 18px rgba(22,121,133,.2)
  }

  .m-bottomnav{
    border-top:0;
    box-shadow:0 -10px 30px rgba(9,49,54,.12);
    border-radius:18px 18px 0 0
  }
  .m-bottomnav button{font-size:10px}
  .m-bottomnav button.on{background:#126f78;color:#fff;box-shadow:none}

  .m-qatools input,.m-qatools select{
    border:0;background:#fff;box-shadow:0 5px 14px rgba(9,49,54,.05)
  }

  /* Spacious mobile mode: readability over minimizing scroll */
  .mobilehome.on:before{height:176px}
  .m-topbar{padding:8px 5px 10px;margin-bottom:12px}
  .m-brand strong{font-size:24px}.m-brand span{font-size:11px;margin-top:5px}
  .m-status{min-height:34px;padding:6px 11px;font-size:10px}

  .m-searchbox{padding:15px;border-radius:21px;margin-bottom:14px}
  .m-label{font-size:11px}
  .m-searchrow{gap:9px;margin-top:9px}
  .m-searchrow input{min-height:52px;padding:12px 13px;font-size:17px;border-radius:13px}
  .m-searchrow button{min-width:82px;min-height:52px;font-size:14px;border-radius:13px}
  .m-hint{font-size:10px;margin-top:9px}

  .m-spotlight{min-height:100px;padding:16px 17px;border-radius:20px;margin-top:14px}
  .m-spotlight small{font-size:10px}.m-spotlight b{font-size:18px;margin-top:5px}.m-spotlight em{font-size:11px;margin-top:5px}
  .m-spotlight .m-arrow{width:40px;height:40px;font-size:24px}

  .m-modgrid{grid-template-columns:1fr;gap:12px;margin-top:15px}
  .m-module{
    min-height:108px;
    border-radius:20px;
    padding:16px 17px 15px 76px;
    display:block
  }
  .m-module .ico{
    position:absolute;left:16px;top:17px;
    width:48px;height:48px;border-radius:15px;font-size:23px
  }
  .m-module:after{right:16px;top:50%;transform:translateY(-50%);width:32px;height:32px;font-size:22px}
  .m-module b{font-size:17px;margin-top:1px;padding-right:38px}
  .m-module span:last-child{font-size:11px;line-height:1.45;margin-top:7px;padding-right:35px}
  .m-module-meta{font-size:10px!important;padding:4px 8px!important;margin-top:9px!important}

  .m-pagehead{padding-bottom:13px;margin-bottom:13px}
  .m-back{width:48px;height:48px;min-width:48px;font-size:22px}
  .m-pagetitle{font-size:22px}.m-pagesub{font-size:11px;max-width:315px;margin-top:4px}

  .m-chipbar{gap:8px;padding-bottom:12px}
  .m-chip{min-height:42px;padding:8px 14px;font-size:11px}
  .m-qatools{grid-template-columns:1fr;gap:8px;margin-bottom:12px}
  .m-qatools input,.m-qatools select{min-height:48px;font-size:14px;padding:10px 12px}.m-qatools input{font-size:17px}

  .m-list{gap:11px}
  .m-row{min-height:92px;padding:15px 14px 14px 15px;border-radius:18px}
  .m-row-main{gap:11px}.m-row-code{font-size:18px}.m-row-name{font-size:15px;line-height:1.35;margin-top:5px}.m-row-cn{font-size:12px;margin-top:3px}.m-row-meta{font-size:10px;line-height:1.5;padding:7px 8px;margin-top:8px}
  .m-badge{min-height:25px;padding:4px 8px;font-size:9px}
  .m-arrow{font-size:25px}

  .m-detailcard{padding:16px;border-radius:20px}
  .m-detailgrid{grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}
  .m-metric{padding:13px;border-radius:15px}
  .m-metric small{font-size:9px}.m-metric b{font-size:21px;margin-top:5px}.m-metric span{font-size:9px;margin-top:5px}
  .m-detailsection{margin-top:17px;padding-top:15px}
  .m-detailsection h3{font-size:13px;margin-bottom:8px}
  .m-detailsection p{font-size:12px;line-height:1.6}
  .m-action{min-height:54px;font-size:15px;margin-top:12px}

  .m-bottomnav{margin-top:18px}
  .m-bottomnav button{min-height:56px;font-size:10px}

@media(min-width:760px){.shell{padding:12px 12px 30px}.dbcardgrid{grid-template-columns:repeat(4,minmax(0,1fr))}.dboverviewgrid{grid-template-columns:1fr 1fr}.statusstrip{grid-template-columns:repeat(4,minmax(0,1fr))}.grid{grid-template-columns:repeat(4,minmax(0,1fr))}.detailgrid{grid-template-columns:repeat(4,minmax(0,1fr))}.uploadgrid{grid-template-columns:1fr 1fr}}
@media(max-width:620px){.shell{padding:7px 7px 76px}.appbar{border-radius:13px}.nav button{font-size:10px}.statusstrip{grid-template-columns:1fr 1fr}.table{min-width:0}.panel{border-radius:13px}.searchbar{padding-left:10px;padding-right:10px}}
</style>
</head>
<body>
<div class="shell">
<header class="appbar">
  <div class="top">
    <div class="brand"><div class="mark">⚓</div><div><strong>Dockside Backoffice</strong><small>FULL MYSQL · Seafood Operations · v__VERSION__</small></div></div>
    <div class="topstat"><span id="readyPill" class="glass">Checking...</span><span id="posPill" class="glass">POS —</span><span id="pricePill" class="glass">Price —</span></div>
  </div>
  <form id="searchForm" class="searchbar"><input id="searchInput" placeholder="Search UPC, Article, Family, Item"><button class="btn glass">Search</button></form>
  <nav class="nav">
    <button class="navbtn on" data-view="inventory">Inventory</button>
    <button class="navbtn" data-view="sales">Sales Performance</button>
    <button class="navbtn" data-view="ordering">Ordering Overview</button>
    <button class="navbtn" data-view="pricing">Pricing Review</button>
    <button class="navbtn" data-view="database">Database Center</button>
  </nav>
</header>
<section id="mobileHome" class="mobilehome" aria-label="Mobile Backoffice Home">
  <div class="m-topbar">
    <div class="m-brand"><strong>FULL MYSQL</strong><span>Backoffice · Seafood · v__VERSION__</span></div>
    <span id="mServicePill" class="m-status">Checking…</span>
  </div>
  <form id="mobileSearchForm" class="m-searchbox">
    <label class="m-label" for="mobileSearchInput">Quick Search</label>
    <div class="m-searchrow"><input id="mobileSearchInput" placeholder="UPC / Article / Family / Item"><button class="btn primary" type="submit">Search</button></div>
    <div class="m-hint"><span>Most active items first</span><span>Typo tolerant</span></div>
  </form>
  <button id="mobileBatchSpotlight" class="m-spotlight" type="button">
    <span><small>Current Batch</small><b id="mobileBatchTitle">Checking processing status…</b><em id="mobileBatchMeta">Tap to open batch list</em></span><span class="m-arrow">›</span>
  </button>
  <div class="m-modgrid">
    <button class="m-module" type="button" data-mobile-module="quick"><span class="ico">🔎</span><b>Quick Check</b><span>Family, Article and UPC lookup</span></button>
    <button class="m-module" type="button" data-mobile-module="qa"><span class="ico">⚠️</span><b>QA Holds</b><span id="mQaModuleMeta" class="m-module-meta">Review unresolved issues</span></button>
    <button class="m-module" type="button" data-mobile-module="price"><span class="ico">💲</span><b>Price Overview</b><span>Current price, source and review</span></button>
    <button class="m-module" type="button" data-mobile-module="uploads"><span class="ico">⬆️</span><b>Uploads</b><span>New batch and upload history</span></button>
    <button class="m-module" type="button" data-mobile-module="performance"><span class="ico">📊</span><b>Performance</b><span>Completed-day sales performance</span></button>
    <button class="m-module" type="button" data-mobile-module="pi"><span class="ico">📦</span><b>PI / OH</b><span>True Stock and OH discrepancy</span></button>
    <button class="m-module" type="button" data-mobile-module="batches"><span class="ico">🧩</span><b>Batches</b><span>Current processing and history</span></button>
    <button class="m-module" type="button" data-mobile-module="freshness"><span class="ico">🕒</span><b>Data Health</b><span>Serving and pipeline freshness</span></button>
  </div>
  <nav class="m-bottomnav" aria-label="Mobile Backoffice navigation">
    <button class="on" type="button" data-mobile-home>⌂<br>Home</button><button type="button" data-mobile-module="quick">⌕<br>Search</button><button type="button" data-mobile-module="uploads">⇧<br>Uploads</button><button type="button" data-mobile-module="qa">⚠<br>QA</button>
  </nav>
</section>

<section id="mobileListPage" class="mobile-listpage" aria-label="Mobile Backoffice List">
  <div class="m-pagehead"><button id="mobileListBack" class="m-back" type="button" aria-label="Back to Home">←</button><div><div id="mobileListTitle" class="m-pagetitle">Backoffice</div><div id="mobileListSub" class="m-pagesub"></div></div></div>
  <div id="mobileListChips" class="m-chipbar"></div>
  <div id="mobileQaTools" class="m-qatools"><input id="mobileQaSearch" placeholder="Search UPC / Article / item / reason"><select id="mobileQaSort"><option value="oh_vel_desc">OH ↓, then Velocity ↓</option><option value="vel_oh_desc">Velocity ↓, then OH ↓</option><option value="severity">Severity</option><option value="name">Item A → Z</option><option value="upc">UPC</option></select></div>
  <div id="mobileListContent" class="m-list"></div>
  <nav class="m-bottomnav" aria-label="Mobile Backoffice navigation">
    <button type="button" data-mobile-home>⌂<br>Home</button><button type="button" data-mobile-module="quick">⌕<br>Search</button><button type="button" data-mobile-module="uploads">⇧<br>Uploads</button><button type="button" data-mobile-module="qa">⚠<br>QA</button>
  </nav>
</section>

<section id="mobileDetailPage" class="mobile-detailpage" aria-label="Mobile Backoffice Detail">
  <div class="m-pagehead"><button id="mobileDetailBack" class="m-back" type="button" aria-label="Back to List">←</button><div><div id="mobileDetailTitle" class="m-pagetitle">Detail</div><div id="mobileDetailSub" class="m-pagesub"></div></div></div>
  <div id="mobileDetailContent"></div>
</section>
<section id="inventory" class="view on"><div class="panel">
 <div class="panelhead"><div><div class="title">Inventory Ledger</div><div class="sub">Read-only system data. OH / True Stock is the only editable value.</div></div><span class="pill blue">OH WRITE ONLY</span></div>
 <div class="toolrow">
   <div class="filters"><button class="filter invfilter on" data-cat="ALL">All</button><button class="filter invfilter" data-cat="FRESH">Fresh</button><button class="filter invfilter" data-cat="LIVE">Live</button><button class="filter invfilter" data-cat="FROZEN">Frozen</button></div>
   <div class="tools">
     <select id="invStatusFilter" class="select"><option value="ALL">All Status</option><option value="READY">READY</option><option value="QA_HOLD">QA HOLD</option><option value="HISTORICAL_ONLY">Historical Only</option></select>
     <select id="invOHFilter" class="select"><option value="ALL">All OH</option><option value="POSITIVE">OH &gt; 0</option><option value="ZERO_NEGATIVE">OH ≤ 0</option><option value="UNKNOWN">OH Unknown</option></select>
     <select id="invSalesFilter" class="select"><option value="ALL">All 7D Sales</option><option value="SOLD">Sold in 7D</option><option value="NO_SALES">No Sales 7D</option></select>
     <select id="invSort" class="select"><option value="vel7_oh_desc">Highest 7D Velocity → Highest OH</option><option value="qty7_desc">Highest 7D Qty</option><option value="oh_asc">Lowest OH</option><option value="oh_desc">Highest OH</option><option value="dos_asc">Lowest DOS</option><option value="dos_desc">Highest DOS</option><option value="gp_asc">Lowest GP%</option><option value="gp_desc">Highest GP%</option><option value="price_desc">Highest Price</option><option value="name">Item A → Z</option></select>
     <span id="invSearchState" class="pill blue" style="display:none"></span><button id="clearInventorySearch" class="btn small" style="display:none">Clear Search</button><span id="invCount" class="pill sea">—</span>
   </div>
 </div>
 <div id="invError"></div><div class="tablewrap"><table class="table"><thead><tr><th>Item</th><th>UPC</th><th>Family</th><th>OH</th><th>7D Qty</th><th>7D Velocity</th><th>Current Price</th><th>Cost</th><th>GP%</th><th>DOS</th><th>Status</th></tr></thead><tbody id="invRows"></tbody></table></div>
</div></section>



<section id="ordering" class="view"><div class="panel">
 <div class="panelhead"><div><div class="title">Ordering Overview</div><div class="sub">Receiving / Ordering Article + Family Article decision level. Selling UPCs appear only inside Details.</div></div><span class="pill blue">READ ONLY</span></div>
 <div class="toolrow"><div class="filters"><button class="filter ordfilter on" data-filter="ALL">All</button><button class="filter ordfilter" data-filter="FRESH">Fresh</button><button class="filter ordfilter" data-filter="FROZEN">Frozen</button><button class="filter ordfilter" data-filter="ATTENTION">Needs Attention</button></div><div class="tools"><select id="orderSort" class="select"><option value="suggested">Highest Suggested Qty</option><option value="receipt">Most Recent Receipt</option><option value="oh">Lowest OH</option><option value="frequency">Ordering Frequency</option><option value="family">Family A → Z</option></select><span id="orderCount" class="pill sea">—</span></div></div>
 <div id="orderError"></div><div class="tablewrap"><table class="table"><thead><tr><th>Family Name</th><th>Receiving Article</th><th>Family Article</th><th>OH</th><th>Last Receipt Date</th><th>Last Receipt Qty · Base UOM</th><th>Ordering Frequency</th><th>Coming Delivery Qty Suggestion</th><th></th></tr></thead><tbody id="orderRows"></tbody></table></div>
</div></section>

<section id="sales" class="view">
<div class="panel">
 <div class="panelhead"><div><div class="title">Sales Performance</div><div class="sub">Latest completed canonical sales date. Report-day average sold price is historical; Current Price is live serving data.</div></div><span class="pill blue">READ ONLY</span></div>
 <div class="toolrow">
   <div class="filters"><button class="filter salescat on" data-cat="ALL">All</button><button class="filter salescat" data-cat="FRESH">Fresh</button><button class="filter salescat" data-cat="LIVE">Live</button><button class="filter salescat" data-cat="FROZEN">Frozen</button></div>
   <div class="tools"><input id="salesTextFilter" class="select" style="min-width:150px" placeholder="Filter item / UPC"><select id="salesTrendFilter" class="select"><option value="ALL">All Velocity</option><option value="SLOWING">Slowing</option><option value="STABLE_GROWING">Stable / Growing</option></select><select id="salesSort" class="select"><option value="sales_desc">Highest Sales $</option><option value="qty_desc">Highest Qty</option><option value="price_desc">Highest Avg Sold Price</option><option value="vel7_desc">Highest 7D Velocity</option><option value="vel28_desc">Highest 28D Velocity</option><option value="drop_desc">Largest Velocity Drop</option><option value="name">Item A → Z</option></select><span id="salesCount" class="pill sea">—</span></div>
 </div>
 <div id="sellKpi" class="grid"></div><div id="sellError"></div><div class="tablewrap"><table class="table"><thead><tr><th>Item</th><th>UPC</th><th>Category</th><th>Qty</th><th>Sales</th><th>Report-Day Avg Sold Price</th><th>Current Price</th><th>7D Vel</th><th>28D Vel</th></tr></thead><tbody id="sellRows"></tbody></table></div>
</div>
</section>

<section id="pricing" class="view">
<div class="panel">
 <div class="panelhead"><div><div class="title">Pricing Review</div><div class="sub">Explainable price suggestions. Accepted records your decision only; change the actual price on the other computer.</div></div><span class="pill blue">REVIEW / ACCEPT</span></div>
 <div class="toolrow">
   <div class="filters"><button class="filter pricefilter on" data-cat="ALL">All</button><button class="filter pricefilter" data-cat="FRESH">Fresh</button><button class="filter pricefilter" data-cat="LIVE">Live</button><button class="filter pricefilter" data-cat="FROZEN">Frozen</button></div>
   <div class="tools">
     <input id="priceTextFilter" class="select" style="min-width:150px" placeholder="Filter item / UPC">
     <select id="priceStatusFilter" class="select">
       <option value="ALL">All Review Status</option>
       <option value="ACTIONABLE">Actionable</option>
       <option value="REVIEW_ONLY">Review Only</option>
       <option value="WAIT_ACTIVE_SALE">Wait / Active Sale</option>
       <option value="QA_HOLD">QA Hold</option>
     </select>
     <select id="priceSort" class="select">
       <option value="opportunity">Highest GP$/Day Opportunity</option>
       <option value="urgency">Highest Urgency</option>
       <option value="gap">Largest Price Gap %</option>
       <option value="qty7">Highest 7D Qty</option>
       <option value="qty28">Highest 28D Qty</option>
       <option value="lowgp">Lowest GP%</option>
       <option value="currentprice">Highest Current Price</option>
       <option value="name">Item A → Z</option>
     </select>
     <span id="priceCount" class="pill sea">—</span>
   </div>
 </div>
 <div id="priceError"></div><div class="tablewrap"><table class="table" style="min-width:1200px"><thead><tr><th>Item</th><th>UPC</th><th>Current Price</th><th>Candidate</th><th>OH / DOH</th><th>Company Range</th><th>Cost</th><th>GP%</th><th>14D Qty</th><th>Review Status</th><th>Primary Reason</th><th></th></tr></thead><tbody id="priceRows"></tbody></table></div>
</div>
</section>

<section id="database" class="view">
  <div class="panel">
    <div class="panelhead">
      <div><div class="title">Database Center</div><div class="sub">Upload, current processing, latest result, history, QA, and Data Health.</div></div>
      <button id="dbRefreshAll" class="btn small">Refresh All</button>
    </div>
    <div class="toolrow">
      <div class="filters">
        <button class="filter dbtab on" data-dbtab="dboverview">Database Home</button>
        <button class="filter dbtab" data-dbtab="dbdata">Data Health</button>
        <button class="filter dbtab" data-dbtab="dbqa">QA Fixes</button>
      </div>
    </div>
  </div>

  <div id="dboverview" class="subview on">
    <div class="panel">
      <div class="panelhead">
        <div><div class="title">Database Home</div><div class="sub">Upload → process → review result. Everything needed for the normal daily workflow is on this page.</div></div>
        <span id="dbOverallStatus" class="pill blue">CHECKING</span>
      </div>
      <div id="dbOverviewError"></div>

      <div class="sectiontitle" style="padding:2px 11px">1. Upload New Files</div>
      <div class="uploadgrid" style="grid-template-columns:1fr">
        <div class="drop" style="margin:0 11px 10px">
          <div class="ico">📤</div><h3>Select source files</h3>
          <p>XLSX / XLS / XLSM / CSV / TXT / TSV. Files selected together create one immutable batch.</p>
          <input id="uploadFiles" type="file" multiple accept=".xlsx,.xls,.xlsm,.csv,.txt,.tsv">
          <div class="formfield"><label>Optional batch note</label><input id="uploadNote" placeholder="Daily seafood upload"></div>
          <div class="upload-actions"><button id="uploadBtn" class="btn primary">Upload & Start Processing</button></div>
        </div>
        <div style="padding:0 11px 8px"><div class="sectiontitle">Latest Upload Result</div><div id="uploadResult" class="uploadresult"><span class="meta">No upload in this session.</span></div></div>
      </div>

      <div class="dboverviewgrid">
        <div class="dbsummary">
          <div class="sectiontitle">2. Current Processing</div>
          <div id="dbOverviewActive" class="batchgrid" style="padding:0"></div>
        </div>
        <div class="dbsummary">
          <div class="sectiontitle">3. Latest Completed Batch</div>
          <div id="dbLatestBatch" class="batchgrid" style="padding:0"></div>
        </div>
      </div>

      <div class="sectiontitle" style="padding:2px 11px">4. Recent Processing History</div>
      <div style="padding:0 11px 8px;display:flex;justify-content:flex-end"><button id="refreshBatch" class="btn small">Refresh Processing</button></div>
      <div id="batchError"></div>
      <div class="tablewrap"><table class="table"><thead><tr><th>Batch</th><th>Status</th><th>Files</th><th>Started</th><th>Completed</th><th>Publish</th><th>QC Ready / Hold</th></tr></thead><tbody id="batchRows"></tbody></table></div>

      <div class="dbcardgrid" style="padding-top:10px">
        <button class="dbcard dbjump" data-target="dbqa"><span class="dbicon">🧩</span><span><small>Review</small><b>QA Fixes</b><em id="dbQASummary">Checking open issues…</em></span></button>
        <button class="dbcard dbjump" data-target="dbdata"><span class="dbicon">🩺</span><span><small>Coverage</small><b>Data Health</b><em id="dbHealthSummary">Checking data coverage…</em></span></button>
      </div>
      <span id="dbUploadSummary" style="display:none"></span><span id="dbProcessingSummary" style="display:none"></span>
    </div>
  </div>

  <div id="dbqa" class="subview"><div class="panel">
    <div class="panelhead"><div><div class="title">QA Fixes</div><div class="sub">Only issues that require review or user-confirmed correction. Raw source rows are never edited.</div></div><span class="pill amber">CONTROLLED FIX</span></div>
    <div class="toolrow"><div class="filters"><button class="filter qafilter on" data-qafilter="ALL">All Open</button><button class="filter qafilter" data-qafilter="FIXABLE">Fixable</button><button class="filter qafilter" data-qafilter="VIEW_ONLY">Review Only</button><button class="filter qafilter" data-qafilter="HIGH">High / Critical</button></div><div class="tools"><input id="qaSearch" class="qa-search" placeholder="Search UPC / Article / Family / item / reason"><select id="qaSort" class="select"><option value="oh_vel_desc">Highest OH → Highest Velocity</option><option value="vel_oh_desc">Highest Velocity → Highest OH</option><option value="severity">Severity</option><option value="name">Item A → Z</option><option value="upc">UPC</option></select><span id="qaCount" class="pill sea">—</span><button id="qaRefresh" class="btn small">Refresh</button></div></div>
    <div id="qaError"></div>
    <div class="tablewrap"><table class="table" style="min-width:1180px"><thead><tr><th>Severity</th><th>Issue</th><th>Entity</th><th>OH</th><th>7D Velocity</th><th>Current State</th><th>Fix Type</th><th></th></tr></thead><tbody id="qaRows"></tbody></table></div>
    <div class="sectiontitle" style="padding:0 11px">Recent Resolution History</div>
    <div class="tablewrap"><table class="table"><thead><tr><th>Time</th><th>Entity</th><th>Issue</th><th>Resolution</th><th>Actor</th><th>Note</th></tr></thead><tbody id="qaHistoryRows"></tbody></table></div>
  </div></div>

  <div id="dbdata" class="subview"><div class="panel">
    <div class="panelhead"><div><div class="title">Data Health · Last 14 Days</div><div class="sub">Most recent first. POS / MVT are daily-required; Price, OH, Live/Fresh and Frozen show source update dates.</div></div><button id="refreshData" class="btn small">Refresh</button></div>
    <div id="dataGrid" class="grid"></div>
    <div id="dataHealthError"></div>
    <div class="tablewrap"><table class="table data-health-table"><thead><tr><th>Date</th><th>Status</th><th>POS</th><th>MVT</th><th>Price</th><th>OH</th><th>Live/Fresh</th><th>Frozen</th><th></th></tr></thead><tbody id="dataHealthRows"></tbody></table></div>
    <div id="dataEvents" class="batchgrid" style="display:none"></div>
  </div></div>
</section>

<div id="drawerBack" class="drawerback"></div><aside id="drawer" class="drawer"><div class="drawerhead"><div><div id="drawerTitle" class="drawertitle">Details</div><div id="drawerSub" class="drawersub"></div></div><button id="drawerClose" class="btn small">Close</button></div><div id="drawerBody" class="drawerbody"></div><div id="drawerFoot" class="drawerfoot"></div></aside>
<div id="toast" class="toast"></div>
</div>
<script>
(()=>{
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const state={invCat:'ALL',inventorySearch:'',invStatus:'ALL',invOH:'ALL',invSales:'ALL',invSort:'vel7_oh_desc',salesCat:'ALL',salesTrend:'ALL',salesText:'',salesSort:'sales_desc',salesRows:[],orderFilter:'ALL',priceCat:'ALL',priceStatus:'ALL',priceSort:'opportunity',priceText:'',qaFilter:'ALL',qaText:'',qaSort:'oh_vel_desc',qaIssues:[],qaHistory:[],inventory:[],orders:[],prices:[],recent:[],active:null,dataHealth:null};
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmt(v,d=1){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):esc(v)}
function money(v){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?'$'+n.toFixed(2):esc(v)}
function pct(v){if(v===null||v===undefined||v==='')return '—';let n=Number(v);if(Math.abs(n)<=1.5)n*=100;return Number.isFinite(n)?n.toFixed(1)+'%':esc(v)}
function pill(status){const s=String(status||'UNKNOWN').toUpperCase();let c='blue';if(s.includes('READY')||s==='PASS'||s==='ACTIVE')c='green';else if(s.includes('FAIL')||s.includes('BLOCK')||s==='OUT')c='red';else if(s.includes('HOLD')||s.includes('PROCESS')||s.includes('QUEUED')||s.includes('WAIT')||s==='WATCH')c='amber';return `<span class="pill ${c}">${esc(s)}</span>`}
function toast(t){const x=$('#toast');x.textContent=t;x.classList.add('on');clearTimeout(toast.t);toast.t=setTimeout(()=>x.classList.remove('on'),2200)}
async function api(url,opts={}){const r=await fetch(url,{cache:'no-store',...opts});let data=null;try{data=await r.json()}catch{data={detail:await r.text()}}if(!r.ok){const d=data?.detail;throw new Error(typeof d==='string'?d:(d?.message||d?.reason||JSON.stringify(d)||`HTTP ${r.status}`))}return data}
const DB_TAB_HASH={dboverview:'home',dbdata:'health',dbqa:'qa'};
const HASH_DB_TAB={home:'dboverview',overview:'dboverview',upload:'dboverview',processing:'dboverview',qa:'dbqa',health:'dbdata'};
function routeFromHash(){
  const raw=decodeURIComponent((location.hash||'').replace(/^#/,'').trim().toLowerCase());
  if(!raw)return {view:'inventory',dbTab:null};
  const [view,sub]=raw.split('/');
  if(['inventory','sales','ordering','pricing'].includes(view))return {view,dbTab:null};
  if(view==='database')return {view:'database',dbTab:HASH_DB_TAB[sub]||'dboverview'};
  return {view:'inventory',dbTab:null};
}
function routeHash(view,dbTab=null){
  if(view==='database')return '#database/'+(DB_TAB_HASH[dbTab]||'overview');
  return '#'+view;
}
function syncRouteHash(view,dbTab=null,{replace=false}={}){
  const next=routeHash(view,dbTab);
  if(location.hash===next)return;
  if(replace)history.replaceState(null,'',next);
  else history.pushState(null,'',next);
}
function show(view,{syncHash=true,scroll=true,dbTab=null}={}){
  $$('.view').forEach(x=>x.classList.toggle('on',x.id===view));
  $$('.navbtn').forEach(x=>x.classList.toggle('on',x.dataset.view===view));
  if(view==='inventory')loadInventory();
  if(view==='sales')loadSell();
  if(view==='ordering')loadOrders();
  if(view==='pricing')loadPrices();
  if(view==='database')showDbTab(dbTab||'dboverview',{syncHash:false});
  if(syncHash)syncRouteHash(view,view==='database'?(dbTab||'dboverview'):null);
  if(scroll)window.scrollTo({top:0,behavior:'smooth'});
}
function showDbTab(tab,{syncHash=true}={}){
  $$('#database .subview').forEach(x=>x.classList.toggle('on',x.id===tab));
  $$('.dbtab').forEach(x=>x.classList.toggle('on',x.dataset.dbtab===tab));
  if(tab==='dboverview'){loadDatabaseOverview();loadBatches();}
  if(tab==='dbqa')loadQA();
  if(tab==='dbdata')loadData();
  if(syncHash)syncRouteHash('database',tab);
}
function restoreRoute({replaceMissing=false}={}){
  const hadHash=Boolean(location.hash);
  const route=routeFromHash();
  show(route.view,{syncHash:false,scroll:false,dbTab:route.dbTab});
  if(!hadHash&&replaceMissing)syncRouteHash(route.view,route.dbTab,{replace:true});
}
$$('.navbtn').forEach(b=>b.onclick=()=>show(b.dataset.view));
$$('.dbtab').forEach(b=>b.onclick=()=>showDbTab(b.dataset.dbtab));
$$('.dbjump').forEach(b=>b.onclick=()=>showDbTab(b.dataset.target));
window.addEventListener('hashchange',()=>restoreRoute());

const mobileMedia=window.matchMedia('(max-width:759px)');
const mobileState={module:null,filter:'all',query:'',freshness:[]};

function isMobileBackoffice(){return mobileMedia.matches}
function mNode(id){return document.getElementById(id)}
function mobileScreen(name,{scroll=true}={}){
  ['mobileHome','mobileListPage','mobileDetailPage'].forEach(id=>mNode(id)?.classList.toggle('on',id===name));
  if(scroll)window.scrollTo({top:0,behavior:'smooth'});
}
function mobileBadgeClass(v){
  const s=String(v||'').toUpperCase();
  if(['READY','CURRENT','DONE','MATCH','HEALTHY','QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS'].includes(s))return 'good';
  if(['QA_HOLD','HIGH','CRITICAL','REVIEW','ACTIONABLE','PROCESSING','PHASE3_QA_HOLD','CURRENT_DAY'].includes(s))return 'warn';
  if(['MISSING','MISS','ISSUE','FAIL','FAILED'].includes(s))return 'bad';
  return '';
}
function mobileMetric(label,value,sub){
  return '<div class="m-metric"><small>'+esc(label)+'</small><b>'+esc(value??'—')+'</b>'+(sub?'<span>'+esc(sub)+'</span>':'')+'</div>';
}
function mobileRow(key,code,name,meta,badge,cn){
  return '<button type="button" class="m-row" data-mobile-key="'+esc(key)+'"><div class="m-row-main"><div class="m-row-copy"><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap"><div class="m-row-code">'+esc(code||'—')+'</div>'+(badge?'<span class="m-badge '+mobileBadgeClass(badge)+'">'+esc(badge)+'</span>':'')+'</div>'+(name?'<div class="m-row-name">'+esc(name)+'</div>':'')+(cn?'<div class="m-row-cn">'+esc(cn)+'</div>':'')+(meta?'<div class="m-row-meta">'+esc(meta)+'</div>':'')+'</div><span class="m-arrow">›</span></div></button>';
}
function mobileModuleConfig(module){
  const map={
    quick:{title:'Quick Check',sub:'Most actively selling items first',chips:[['all','All'],['fresh','Fresh'],['live','Live'],['frozen','Frozen']]},
    qa:{title:'QA Holds',sub:'Choose one issue, review it, then fix',chips:[['all','All'],['fixable','Fixable'],['view_only','Review only'],['high','High / Critical']]},
    price:{title:'Price Overview',sub:'Current price, source and qualified review',chips:[['all','All'],['actionable','Actionable'],['review_only','Review only'],['qa_hold','QA Hold']]},
    uploads:{title:'Uploads',sub:'New source batch and recent upload history',chips:[]},
    performance:{title:'Performance',sub:'Latest completed canonical sales date',chips:[['all','All'],['fresh','Fresh'],['live','Live'],['frozen','Frozen']]},
    pi:{title:'PI / OH',sub:'Family True Stock and OH review',chips:[['all','All'],['positive','OH > 0'],['zero','OH ≤ 0']]},
    batches:{title:'Batches',sub:'Current processing first, then completed history',chips:[['all','All'],['current','Current'],['completed','Completed']]},
    freshness:{title:'Data Health',sub:'Last 14 days · newest first · tap a date for source details',chips:[]}
  };
  return map[module]||{title:'Backoffice',sub:'',chips:[]};
}
function mobileRenderChips(){
  const cfg=mobileModuleConfig(mobileState.module),box=mNode('mobileListChips');
  if(!box)return;
  box.innerHTML=cfg.chips.map(x=>'<button type="button" class="m-chip '+(mobileState.filter===x[0]?'on':'')+'" data-m-filter="'+esc(x[0])+'">'+esc(x[1])+'</button>').join('');
  box.style.display=cfg.chips.length?'flex':'none';
  box.querySelectorAll('[data-m-filter]').forEach(b=>b.onclick=()=>{mobileState.filter=b.dataset.mFilter;mobileRenderChips();mobileRenderList()});
}
function mobileRenderQaTools(){
 const box=mNode('mobileQaTools');if(!box)return;
 const on=mobileState.module==='qa';box.classList.toggle('on',on);
 if(!on)return;
 const input=mNode('mobileQaSearch'),sort=mNode('mobileQaSort');
 input.value=state.qaText||'';sort.value=state.qaSort||'oh_vel_desc';
 input.oninput=()=>{state.qaText=input.value;mobileRenderList()};
 sort.onchange=()=>{state.qaSort=sort.value;mobileRenderList()};
}
async function mobileRefreshHome(){
  if(!isMobileBackoffice())return;
  try{
    const res=await Promise.all([api('/healthz'),api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=5'),api('/v1/backoffice/qa-review?limit=300')]);
    const h=res[0]||{},a=res[1]||{},r=res[2]||{},q=res[3]||{};
    state.active=a.active_batch||null;state.recent=r.batches||[];state.qaIssues=q.issues||[];state.qaHistory=q.resolution_history||[];
    const sp=mNode('mServicePill');if(sp){sp.textContent=h.ok?'● ONLINE':'SERVICE ISSUE';sp.className='m-status '+(h.ok?'good':'bad')}
    const title=mNode('mobileBatchTitle'),meta=mNode('mobileBatchMeta'),latest=state.recent[0]||null;
    if(state.active){title.textContent='Batch #'+(state.active.batch_id||state.active.id||'—')+' · '+(state.active.processing_status||state.active.status||'PROCESSING');meta.textContent=(state.active.file_count??'—')+' file(s) · active processing'}
    else if(latest){title.textContent='Latest Batch #'+(latest.batch_id||'—')+' · '+(latest.phase3_status||latest.processing_status||'COMPLETE');meta.textContent=(latest.quick_check_ready_rows??'—')+' ready · '+(latest.quick_check_hold_rows??'—')+' hold'}
    else{title.textContent='No active batch';meta.textContent='Tap to open batch history'}
    const qm=mNode('mQaModuleMeta');if(qm)qm.textContent=state.qaIssues.length?state.qaIssues.length+' open · '+state.qaIssues.filter(x=>x.can_fix).length+' fixable':'No open QA issues';
  }catch(e){
    const sp=mNode('mServicePill');if(sp){sp.textContent='CHECK FAILED';sp.className='m-status bad'}
  }
}
function showMobileHome({scroll=true}={}){
  if(!isMobileBackoffice())return;
  closeDrawer();
  mobileState.module=null;mobileState.filter='all';mobileState.query='';
  mobileScreen('mobileHome',{scroll});
  mobileRefreshHome();
}
async function mobileOpenModule(module,{query=''}={}){
  if(!isMobileBackoffice())return;
  closeDrawer();
  mobileState.module=module;mobileState.filter='all';mobileState.query=String(query||'').trim();
  const cfg=mobileModuleConfig(module);
  mNode('mobileListTitle').textContent=cfg.title;
  mNode('mobileListSub').textContent=mobileState.query&&module==='quick'?'Search: '+mobileState.query:cfg.sub;
  mNode('mobileListContent').innerHTML='<div class="m-loading">Loading…</div>';
  mobileScreen('mobileListPage');
  mobileRenderChips();
  mobileRenderQaTools();
  try{
    if(module==='quick'){
      state.inventorySearch=mobileState.query;state.invCat='ALL';state.invStatus='ALL';state.invOH='ALL';state.invSales='ALL';state.invSort='vel7_oh_desc';await loadInventory();
    }else if(module==='qa'){
      state.qaFilter='ALL';state.qaText='';state.qaSort='oh_vel_desc';mobileRenderQaTools();await loadQA();
    }else if(module==='price'){
      state.priceCat='ALL';state.priceStatus='ALL';state.priceSort='opportunity';state.priceText='';await loadPrices();
    }else if(module==='performance'){
      state.salesCat='ALL';state.salesTrend='ALL';state.salesText='';state.salesSort='sales_desc';await loadSell();
    }else if(module==='pi'){
      state.inventorySearch='';state.invCat='ALL';state.invStatus='ALL';state.invOH='ALL';state.invSales='ALL';state.invSort='vel7_oh_desc';await loadInventory();
    }else if(module==='batches'||module==='uploads'){
      await loadBatches();
    }else if(module==='freshness'){
      await mobileLoadFreshness();
    }
    mobileRenderList();
  }catch(e){mNode('mobileListContent').innerHTML='<div class="m-error">'+esc(e.message||'Unable to load this section')+'</div>'}
}
function mobileRows(){
  const mod=mobileState.module,f=mobileState.filter;
  if(mod==='quick'){
    let a=filteredInventoryRows();
    if(f!=='all')a=a.filter(r=>String(r.category||'').toLowerCase()===f);
    return a;
  }
  if(mod==='qa'){
    let a=[...state.qaIssues];
    if(f==='fixable')a=a.filter(x=>x.can_fix);
    if(f==='view_only')a=a.filter(x=>!x.can_fix);
    if(f==='high')a=a.filter(x=>['HIGH','CRITICAL'].includes(String(x.severity||'').toUpperCase()));
    const q=String(state.qaText||'').trim().toLowerCase();
    if(q)a=a.filter(x=>qaSearchBlob(x).includes(q));
    return qaSortRows(a);
  }
  if(mod==='price'){
    let a=filteredPrices();
    if(f!=='all')a=a.filter(x=>String(x.review_status||'').toLowerCase()===f);
    return a;
  }
  if(mod==='performance'){
    let a=filteredSalesRows();
    if(f!=='all')a=a.filter(r=>String(r.category||'').toLowerCase()===f);
    return a;
  }
  if(mod==='pi'){
    const map=new Map();
    filteredInventoryRows().forEach(r=>{const k=String(r.family_article||r.upc||'');if(!k)return;const old=map.get(k);if(!old||Number(r.velocity_7d||0)>Number(old.velocity_7d||0))map.set(k,r)});
    let a=[...map.values()];
    if(f==='positive')a=a.filter(r=>r.family_oh!==null&&r.family_oh!==undefined&&Number(r.family_oh)>0);
    if(f==='zero')a=a.filter(r=>r.family_oh!==null&&r.family_oh!==undefined&&Number(r.family_oh)<=0);
    return a;
  }
  if(mod==='batches'){
    const a=[];
    if(state.active)a.push(Object.assign({_mobileActive:true},state.active));
    state.recent.forEach(b=>{if(!state.active||String(b.batch_id)!==String(state.active.batch_id))a.push(Object.assign({_mobileActive:false},b))});
    if(f==='current')return a.filter(x=>x._mobileActive);
    if(f==='completed')return a.filter(x=>!x._mobileActive);
    return a;
  }
  if(mod==='uploads'){
    const a=[{_mobileNewUpload:true}];
    if(state.active)a.push(Object.assign({_mobileActive:true},state.active));
    state.recent.slice(0,8).forEach(b=>{if(!state.active||String(b.batch_id)!==String(state.active.batch_id))a.push(Object.assign({_mobileActive:false},b))});
    return a;
  }
  if(mod==='freshness')return mobileState.freshness;
  return [];
}
function mobileDataHealthStatus(x){
  const s=String(x?.status||'NONE').toUpperCase();
  if(s==='OK')return {text:'OK',cls:'good'};
  if(s==='MISSING')return {text:'MISS',cls:'bad'};
  if(s==='NOT_DUE')return {text:'N/D',cls:'warn'};
  return {text:'—',cls:''};
}
function mobileDataHealthRow(r){
  const s=r.sources||{},overall=String(r.overall_status||'').toUpperCase();
  const items=[['POS',s.POS],['MVT',s.MVT],['Price',s.PRICE],['OH',s.OH],['Live/Fresh',s.LIVE_FRESH],['Frozen',s.FROZEN]];
  const chips=items.map(([label,x])=>{const st=mobileDataHealthStatus(x);return '<span class="m-dh-chip '+st.cls+'"><span>'+esc(label)+'</span><b>'+esc(st.text)+'</b></span>'}).join('');
  return '<button type="button" class="m-row" data-mobile-key="date:'+esc(r.date)+'"><div class="m-row-main"><div class="m-row-copy"><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap"><div class="m-row-code">'+esc(r.date||'—')+'</div><span class="m-badge '+mobileBadgeClass(overall)+'">'+esc(overall||'INFO')+'</span></div><div class="m-row-name">'+esc(r.weekday||'')+'</div><div class="m-dh-grid">'+chips+'</div></div><span class="m-arrow">›</span></div></button>';
}
function mobileRenderList(){
  const box=mNode('mobileListContent');if(!box)return;
  const rows=mobileRows();let html='';
  if(mobileState.module==='quick'){
    html=rows.map(r=>mobileRow(String(r.upc||''),r.upc||r.family_article,r.name||r.family_name,(r.family_article?'Family '+r.family_article+' · ':'')+fmt(r.qty_7d)+' 7D · '+money(r.price)+' '+(r.price_type||'')+' · '+(r.price_source||'—')+(r.price_as_of?' · '+r.price_as_of:''),r.readiness||r.category,r.chinese_name||'')).join('');
  }else if(mobileState.module==='qa'){
    html=rows.map(x=>{const cur=x.current||{};const key=(x.issue_id===null||x.issue_id===undefined)?'QC:'+String(x.entity_key||''):String(x.issue_id);return mobileRow(key,x.entity_key||x.issue_code,cur.item_name||cur.selling_description||x.issue_code,'OH '+fmt(cur.current_oh)+' '+(cur.current_oh_uom||'')+' · 7D Vel '+fmt(cur.upc_velocity_7d)+'/'+(cur.selling_uom||'unit')+' · '+qaFixKindLabel(x.fix_kind)+' · '+(x.issue_summary||''),x.severity||x.fix_kind,cur.chinese_name||'')}).join('');
  }else if(mobileState.module==='price'){
    html=rows.map(r=>mobileRow(String(r.upc||''),r.upc,r.name,money(r.current_price)+' current · '+money(r.candidate_price)+' candidate · '+(r.current_price_source||'—')+(r.current_price_observed_date?' · '+r.current_price_observed_date:''),r.review_status||'REVIEW','')).join('');
  }else if(mobileState.module==='performance'){
    html=rows.map(r=>mobileRow(String(r.upc||''),r.upc,r.name,money(r.sales_amount)+' sales · '+fmt(r.sold_quantity)+' '+(r.qty_uom||'')+' · '+money(r.current_price)+' current · '+(r.current_price_source||'—')+(r.current_price_asof_date?' · '+r.current_price_asof_date:''),r.category||'READY','')).join('');
  }else if(mobileState.module==='pi'){
    html=rows.map(r=>mobileRow(String(r.family_article||r.upc||''),r.family_article||r.upc,r.family_name||r.name,fmt(r.family_oh)+' '+(r.family_oh_uom||'')+' OH · '+fmt(r.qty_7d)+' 7D · DOS '+fmt(r.dos),'OH',r.chinese_name||'')).join('');
  }else if(mobileState.module==='batches'){
    html=rows.map(b=>mobileRow((b._mobileActive?'active:':'batch:')+String(b.batch_id||b.id||''),'Batch #'+(b.batch_id||b.id||'—'),b.batch_label||(b._mobileActive?'Active processing':'Completed batch'),(b.file_count??'—')+' file(s) · '+(b.quick_check_ready_rows??'—')+' ready · '+(b.quick_check_hold_rows??'—')+' hold',b._mobileActive?(b.processing_status||b.status||'CURRENT'):(b.phase3_status||b.processing_status||'DONE'),'')).join('');
  }else if(mobileState.module==='uploads'){
    html=rows.map(b=>b._mobileNewUpload?mobileRow('new-upload','＋ New Upload','Create source batch','Choose one or more source files; file type is detected automatically','UPLOAD',''):mobileRow('uploadbatch:'+String(b.batch_id||b.id||''),'Batch #'+(b.batch_id||b.id||'—'),b.batch_label||(b._mobileActive?'Active processing':'Upload history'),(b.file_count??'—')+' file(s) · '+(b.upload_started_at||b.completed_at||'—'),b._mobileActive?(b.processing_status||'CURRENT'):(b.phase3_status||b.processing_status||'DONE'),'')).join('');
  }else if(mobileState.module==='freshness'){
    html=rows.map(r=>mobileDataHealthRow(r)).join('');
  }
  box.innerHTML=html||'<div class="m-empty">No items match the current filter.</div>';
  box.querySelectorAll('[data-mobile-key]').forEach(b=>b.onclick=()=>mobileOpenItem(b.dataset.mobileKey));
}
function mobileShowDetail(title,sub,html){
  mNode('mobileDetailTitle').textContent=title||'Detail';mNode('mobileDetailSub').textContent=sub||'';mNode('mobileDetailContent').innerHTML=html;mobileScreen('mobileDetailPage');
}
function mobileOpenItem(key){
  const mod=mobileState.module;
  if(mod==='quick')return mobileQuickDetail(key,false);
  if(mod==='qa')return openQAIssue(key);
  if(mod==='price')return openPriceDetail(key);
  if(mod==='performance')return mobilePerformanceDetail(key);
  if(mod==='pi')return mobileQuickDetail(key,true);
  if(mod==='batches'){
    if(String(key).startsWith('active:'))return mobileActiveBatchDetail();
    return openBatchDetail(String(key).replace(/^batch:/,''));
  }
  if(mod==='uploads'){
    if(key==='new-upload')return mobileUploadDetail();
    const id=String(key).replace(/^uploadbatch:/,'');
    if(state.active&&String(state.active.batch_id||state.active.id)===id)return mobileActiveBatchDetail();
    return openBatchDetail(id);
  }
  if(mod==='freshness')return mobileFreshnessDetail(key);
}
function mobileQuickDetail(key,piMode){
  let r=null;
  if(piMode)r=state.inventory.find(x=>String(x.family_article||x.upc)===String(key));
  else r=state.inventory.find(x=>String(x.upc)===String(key));
  if(!r)return;
  const title=piMode?String(r.family_article||r.upc||'Item'):String(r.upc||r.family_article||'Item');
  const sub=(piMode?(r.family_name||r.name):(r.name||r.family_name))+(r.chinese_name?' · '+r.chinese_name:'');
  let html='<div class="m-detailcard"><div class="m-label">'+(piMode?'Family / PI Summary':'UPC Summary')+'</div><div class="m-detailgrid">';
  html+=mobileMetric('Current Price',money(r.price),(r.price_type||'—')+' · '+(r.price_source||'—')+(r.price_as_of?' · '+r.price_as_of:''));
  html+=mobileMetric('Cost',money(r.cost),'Current cost');
  html+=mobileMetric('OH',fmt(r.family_oh)+' '+(r.family_oh_uom||''),'Current effective family OH');
  html+=mobileMetric('7D Sold',fmt(r.qty_7d)+' '+(r.selling_uom||''),'POS quantity');
  html+=mobileMetric('7D Velocity',fmt(r.velocity_7d),(r.selling_uom||'unit')+'/day');
  html+=mobileMetric('GP%',pct(r.gp_pct),'At current price / cost');
  html+=mobileMetric('DOS',fmt(r.dos),'Days of supply');
  html+=mobileMetric('Family',r.family_article||'—',r.family_name||'');
  html+='</div>';
  if(r.family_article)html+='<button id="mAdjustOH" type="button" class="m-action primary">Update True Stock / OH</button>';
  html+='</div>';
  mobileShowDetail(title,sub,html);
  const btn=mNode('mAdjustOH');if(btn)btn.onclick=()=>openOH({family:r.family_article,uom:r.family_oh_uom||'',oh:r.family_oh??'',name:r.family_name||r.name||''});
}
function mobilePerformanceDetail(key){
  const r=state.salesRows.find(x=>String(x.upc)===String(key));if(!r)return;
  let html='<div class="m-detailcard"><div class="m-label">Completed-day Performance</div><div class="m-detailgrid">';
  html+=mobileMetric('Sales',money(r.sales_amount),'Report date');
  html+=mobileMetric('Sold Qty',fmt(r.sold_quantity)+' '+(r.qty_uom||''),'POS');
  html+=mobileMetric('Avg Sold Price',money(r.avg_sold_price),'Historical report-day average');
  html+=mobileMetric('Current Price',money(r.current_price),(r.current_price_type||'—')+' · '+(r.current_price_source||'—')+(r.current_price_asof_date?' · '+r.current_price_asof_date:''));
  html+=mobileMetric('7D Velocity',fmt(r.velocity_7d),'per day');
  html+=mobileMetric('28D Velocity',fmt(r.velocity_28d),'per day');
  html+='</div></div>';
  mobileShowDetail(r.upc||'Performance',r.name||'',html);
}
function mobileActiveBatchDetail(){
  const b=state.active;if(!b)return;
  const waiting=batchResumeEligible(b);
  let html='<div class="m-detailcard"><div class="m-label">Current Batch</div><div class="m-detailgrid">';
  html+=mobileMetric('Batch','#'+(b.batch_id||b.id||'—'),b.batch_label||'Active processing');
  html+=mobileMetric('Files',String(b.file_count??'—'),'Source files');
  html+=mobileMetric('Started',b.upload_started_at||'—','Upload start');
  html+=mobileMetric('Status',b.processing_status||b.status||'PROCESSING','Current pipeline state');
  html+='</div><div class="m-detailsection"><h3>Processing</h3><p>'+(waiting?'Past: Phase 2C complete. Current: waiting for Phase 3. Next: Phase 3 rebuild → QA → Quick Check.':'This batch is still active.')+'</p></div>';
  if(waiting)html+='<button id="mResumePhase3" type="button" class="m-action primary">Retry Phase 3</button>';
  html+='</div>';
  mobileShowDetail('Batch #'+(b.batch_id||b.id||'—'),b.processing_status||b.status||'PROCESSING',html);
  const btn=mNode('mResumePhase3');if(btn)btn.onclick=()=>resumePhase3(b.batch_id||b.id);
}
async function mobileLoadFreshness(){
  const d=await api('/v1/backoffice/data-health?days=14');
  state.dataHealth=d;
  mobileState.freshness=d.rows||[];
}

function mobileFreshnessDetail(key){
  const dateKey=String(key||'').replace(/^date:/,'');
  const r=mobileState.freshness.find(x=>String(x.date)===dateKey);if(!r)return;
  const names={POS:'POS',MVT:'MVT',PRICE:'Price List',OH:'OH',LIVE_FRESH:'Live / Fresh',FROZEN:'Frozen'};
  let html='<div class="m-detailcard"><div class="m-label">14-Day Data Health</div><div class="m-detailgrid">';
  Object.keys(names).forEach(k=>{
    const x=(r.sources||{})[k]||{},st=mobileDataHealthStatus(x);
    html+=mobileMetric(names[k],st.text,(x.file||'No source')+(x.batch_id?' · Batch #'+x.batch_id:''));
  });
  html+='</div><div class="m-detailsection"><h3>Coverage rule</h3><p>POS and MVT are daily-required through the latest completed business day. Price, OH, Live/Fresh and Frozen are snapshot sources; “—” means no new snapshot was ingested on that date.</p></div></div>';
  mobileShowDetail(r.date||'Data Health',(r.weekday||'')+' · '+(r.overall_status||''),html);
}

function mobileUploadDetail(){
  let html='<div class="m-detailcard"><div class="m-label">New Source Batch</div><div class="m-detailsection" style="border-top:0;padding-top:0;margin-top:9px"><p>Select XLSX / XLS / XLSM / CSV / TXT / TSV files. Files selected together create one immutable batch.</p></div><button id="mChooseUploadFiles" type="button" class="m-action secondary">Choose Files</button><div id="mUploadFileSummary" class="m-detailsection"><p>No files selected.</p></div><div class="formfield"><label>Optional batch note</label><input id="mUploadNote" placeholder="Daily seafood upload"></div><button id="mStartUpload" type="button" class="m-action primary">Upload & Start Processing</button><div id="mUploadResult" class="m-detailsection"><p>File type is detected automatically.</p></div></div>';
  mobileShowDetail('New Upload','Create one source batch',html);
  const fileInput=$('#uploadFiles');
  mNode('mChooseUploadFiles').onclick=()=>fileInput.click();
  fileInput.onchange=()=>{
    const files=[...fileInput.files],box=mNode('mUploadFileSummary');
    box.innerHTML=files.length?'<h3>Selected Files</h3><p>'+files.map(f=>esc(f.name)+' · '+fmt(f.size/1024/1024,2)+' MB').join('<br>')+'</p>':'<p>No files selected.</p>';
  };
  mNode('mStartUpload').onclick=mobileSubmitUpload;
}
async function mobileSubmitUpload(){
  const files=[...$('#uploadFiles').files],result=mNode('mUploadResult'),btn=mNode('mStartUpload');
  if(!files.length){toast('Select files first');return}
  btn.disabled=true;result.innerHTML='<p>Creating batch…</p>';
  try{
    const label=(mNode('mUploadNote').value||'').trim()||('Mobile Backoffice upload '+new Date().toLocaleString());
    const created=await api('/v1/web-upload/batches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label})});
    if(created.created===false){result.innerHTML='<p>An active batch is already processing. Upload was not started.</p>';toast('Active batch already processing');return}
    const session=created.session_id||created.batch_key||created.session?.session_id;if(!session)throw new Error('Upload batch session ID was not returned');
    for(let i=0;i<files.length;i++){
      result.innerHTML='<p>Uploading '+(i+1)+' / '+files.length+' · '+esc(files[i].name)+'</p>';
      const fd=new FormData();fd.append('file',files[i]);await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/files',{method:'POST',body:fd});
    }
    result.innerHTML='<p>Committing batch and starting processing…</p>';
    await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/commit',{method:'POST'});
    $('#uploadFiles').value='';toast('Upload accepted; batch processing started');await mobileOpenModule('batches');
  }catch(e){result.innerHTML='<p>'+esc(e.message)+'</p>';toast(e.message)}finally{const z=mNode('mStartUpload');if(z)z.disabled=false}
}

$$('[data-mobile-module]').forEach(b=>b.onclick=()=>mobileOpenModule(b.dataset.mobileModule));
$$('[data-mobile-home]').forEach(b=>b.onclick=()=>showMobileHome());
mNode('mobileListBack').onclick=()=>showMobileHome();
mNode('mobileDetailBack').onclick=()=>mobileScreen('mobileListPage');
mNode('mobileBatchSpotlight').onclick=()=>mobileOpenModule('batches');
mNode('mobileSearchForm').onsubmit=e=>{e.preventDefault();mobileOpenModule('quick',{query:mNode('mobileSearchInput').value})};
mobileMedia.addEventListener?.('change',e=>{
  if(e.matches)showMobileHome({scroll:false});
  else{closeDrawer();mobileScreen('',{scroll:false});restoreRoute()}
});
function openDrawer(title,sub,body,foot=''){ $('#drawerTitle').textContent=title;$('#drawerSub').textContent=sub||'';$('#drawerBody').innerHTML=body;$('#drawerFoot').innerHTML=foot;$('#drawerBack').classList.add('on');$('#drawer').classList.add('on') }
function closeDrawer(){$('#drawerBack').classList.remove('on');$('#drawer').classList.remove('on')}$('#drawerClose').onclick=closeDrawer;$('#drawerBack').onclick=closeDrawer;

async function loadHealth(){try{const h=await api('/healthz');$('#readyPill').textContent=h.ok?'SERVICE READY':'SERVICE ISSUE';$('#readyPill').style.color=h.ok?'#bff3d2':'#ffd0c8'}catch(e){$('#readyPill').textContent='SERVICE ERROR'}}
async function loadInventory(){const err=$('#invError');err.innerHTML='';$('#invRows').innerHTML='<tr><td colspan="11" class="loading">Loading...</td></tr>';try{const q=state.inventorySearch.trim();const url=`/v1/backoffice/inventory?category=${encodeURIComponent(state.invCat)}&limit=300${q?'&q='+encodeURIComponent(q):''}`;const d=await api(url);state.inventory=d.rows||[];const badge=$('#invSearchState'),clear=$('#clearInventorySearch');if(q){badge.textContent=`Search: ${q}`;badge.style.display='inline-flex';clear.style.display='inline-flex'}else{badge.style.display='none';clear.style.display='none'}renderInventory()}catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#invRows').innerHTML=''}}
function filteredInventoryRows(){
  let rows=[...state.inventory];
  const status=String(state.invStatus||'ALL').toUpperCase();
  if(status!=='ALL')rows=rows.filter(r=>String(r.readiness||'').toUpperCase()===status);
  if(state.invOH==='POSITIVE')rows=rows.filter(r=>r.family_oh!==null&&r.family_oh!==undefined&&Number(r.family_oh)>0);
  if(state.invOH==='ZERO_NEGATIVE')rows=rows.filter(r=>r.family_oh!==null&&r.family_oh!==undefined&&Number(r.family_oh)<=0);
  if(state.invOH==='UNKNOWN')rows=rows.filter(r=>r.family_oh===null||r.family_oh===undefined||r.family_oh==='');
  if(state.invSales==='SOLD')rows=rows.filter(r=>Number(r.qty_7d||0)>0);
  if(state.invSales==='NO_SALES')rows=rows.filter(r=>Number(r.qty_7d||0)<=0);
  const s=state.invSort||'vel7_oh_desc';
  const num=(v,fallback)=>v===null||v===undefined||v===''?fallback:Number(v);
  if(s==='vel7_oh_desc')rows.sort((x,y)=>{
    const xv=num(x.velocity_7d,Number.NEGATIVE_INFINITY);
    const yv=num(y.velocity_7d,Number.NEGATIVE_INFINITY);
    if(yv!==xv)return yv-xv;
    return num(y.family_oh,Number.NEGATIVE_INFINITY)-num(x.family_oh,Number.NEGATIVE_INFINITY);
  });
  if(s==='qty7_desc')rows.sort((x,y)=>num(y.qty_7d,-1)-num(x.qty_7d,-1));
  if(s==='oh_asc')rows.sort((x,y)=>num(x.family_oh,Number.POSITIVE_INFINITY)-num(y.family_oh,Number.POSITIVE_INFINITY));
  if(s==='oh_desc')rows.sort((x,y)=>num(y.family_oh,Number.NEGATIVE_INFINITY)-num(x.family_oh,Number.NEGATIVE_INFINITY));
  if(s==='dos_asc')rows.sort((x,y)=>num(x.dos,Number.POSITIVE_INFINITY)-num(y.dos,Number.POSITIVE_INFINITY));
  if(s==='dos_desc')rows.sort((x,y)=>num(y.dos,Number.NEGATIVE_INFINITY)-num(x.dos,Number.NEGATIVE_INFINITY));
  if(s==='gp_asc')rows.sort((x,y)=>num(x.gp_pct,Number.POSITIVE_INFINITY)-num(y.gp_pct,Number.POSITIVE_INFINITY));
  if(s==='gp_desc')rows.sort((x,y)=>num(y.gp_pct,Number.NEGATIVE_INFINITY)-num(x.gp_pct,Number.NEGATIVE_INFINITY));
  if(s==='price_desc')rows.sort((x,y)=>num(y.price,Number.NEGATIVE_INFINITY)-num(x.price,Number.NEGATIVE_INFINITY));
  if(s==='name')rows.sort((x,y)=>String(x.name||'').localeCompare(String(y.name||'')));
  return rows;
}
function renderInventory(){const rows=filteredInventoryRows();$('#invCount').textContent=`${rows.length} shown · ${state.inventory.length} loaded`;$('#invRows').innerHTML=rows.map(r=>`<tr class="${Number(r.velocity_7d||0)>0?'velocity-active':''}"><td><div class="name">${esc(r.name)}</div><div class="meta">${esc(r.category||'')} · ${esc(r.price_type||'')}</div></td><td>${esc(r.upc)}</td><td><b>${esc(r.family_article||'—')}</b><div class="meta">${esc(r.family_name||'')}</div></td><td><button class="linkbtn ohbtn" data-family="${esc(r.family_article||'')}" data-uom="${esc(r.family_oh_uom||'')}" data-oh="${esc(r.family_oh??'')}" data-name="${esc(r.family_name||r.name)}">${fmt(r.family_oh)} ${esc(r.family_oh_uom||'')}</button></td><td>${fmt(r.qty_7d)}</td><td><b>${fmt(r.velocity_7d)}</b><div class="meta">${esc(r.selling_uom||'unit')}/day</div></td><td><b>${money(r.price)}</b><div class="meta">${esc(r.price_type||'—')} · ${esc(r.price_source||'—')} ${r.price_as_of?'· '+esc(r.price_as_of):''}</div></td><td>${money(r.cost)}</td><td>${pct(r.gp_pct)}</td><td>${fmt(r.dos)}</td><td>${pill(r.readiness)}</td></tr>`).join('')||`<tr><td colspan="11" class="empty">${state.inventorySearch?'No matching rows after current Inventory filters for: '+esc(state.inventorySearch):'No inventory rows match the current filters.'}</td></tr>`;$$('.ohbtn').forEach(b=>b.onclick=()=>openOH(b.dataset))}
$$('.invfilter').forEach(b=>b.onclick=()=>{state.invCat=b.dataset.cat;$$('.invfilter').forEach(x=>x.classList.toggle('on',x===b));loadInventory()});
$('#invStatusFilter').onchange=e=>{state.invStatus=e.target.value;renderInventory()};
$('#invOHFilter').onchange=e=>{state.invOH=e.target.value;renderInventory()};
$('#invSalesFilter').onchange=e=>{state.invSales=e.target.value;renderInventory()};
$('#invSort').onchange=e=>{state.invSort=e.target.value;renderInventory()};
$('#clearInventorySearch').onclick=()=>{state.inventorySearch='';$('#searchInput').value='';loadInventory()};

function openOH(d){if(!d.family){toast('Family Article unavailable');return}const current=d.oh||'';openDrawer('OH / True Stock Adjustment',`${d.name} · Family ${d.family}`,`<div class="detailgrid"><div class="detail"><small>Family Article</small><b>${esc(d.family)}</b></div><div class="detail"><small>System / Effective OH</small><b>${fmt(current)} ${esc(d.uom)}</b></div></div><div class="formfield"><label>True Stock</label><input id="trueStockInput" type="number" min="0" step="0.01" value="${esc(current)}"></div><div class="formfield"><label>UOM</label><input id="trueStockUom" value="${esc(d.uom)}" readonly></div><div class="formfield"><label>Note</label><textarea id="trueStockNote" placeholder="Physical count / OH adjustment"></textarea></div><div id="ohPreview" class="calc">Difference: 0</div>`,`<button id="saveOH" class="btn primary">Save OH Adjustment</button>`);const inp=$('#trueStockInput');inp.oninput=()=>{const n=Number(inp.value||0),o=Number(current||0),diff=n-o;$('#ohPreview').textContent=`Difference: ${diff>=0?'+':''}${diff.toFixed(2)}${diff<0?' · shortage / pending dumping '+Math.abs(diff).toFixed(2):''}`};$('#saveOH').onclick=async()=>{try{$('#saveOH').disabled=true;await api(`/v1/app/v2/pi/${encodeURIComponent(d.family)}/true-stock`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:Number(inp.value),uom:d.uom,note:$('#trueStockNote').value||null})});toast('OH / True Stock saved');closeDrawer();await loadInventory()}catch(e){toast(e.message)}finally{const x=$('#saveOH');if(x)x.disabled=false}}}

async function loadSell(){const err=$('#sellError');err.innerHTML='';$('#sellRows').innerHTML='<tr><td colspan="9" class="loading">Loading...</td></tr>';try{const d=await api(`/v1/app/v2/performance?category=${encodeURIComponent(state.salesCat)}&limit=100`);const s=d.summary||{};state.salesRows=d.report_date_items||d.report_date_top_sellers||[];$('#sellKpi').innerHTML=`<div class="kpi"><small>Report Date</small><b>${esc(d.report_date||'—')}</b><span>${esc(d.report_date_weekday||'')}</span></div><div class="kpi"><small>Sales</small><b>${money(s.report_date_sales_dollars)}</b><span>${esc(state.salesCat)} · canonical report date</span></div><div class="kpi"><small>Active UPCs 28D</small><b>${fmt(s.active_upcs_28d,0)}</b><span>Selected category scope</span></div><div class="kpi"><small>Slowing Items</small><b>${fmt(s.slowing_items,0)}</b><span>7D below 80% of 28D</span></div>`;renderSales()}catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#sellRows').innerHTML=''}}
function filteredSalesRows(){
  let rows=[...state.salesRows];
  const text=String(state.salesText||'').trim().toLowerCase();
  if(text)rows=rows.filter(r=>[r.name,r.upc,r.family_article_number,r.category].join(' ').toLowerCase().includes(text));
  if(state.salesTrend==='SLOWING')rows=rows.filter(r=>Number(r.velocity_28d||0)>0&&Number(r.velocity_7d||0)<Number(r.velocity_28d||0)*0.8);
  if(state.salesTrend==='STABLE_GROWING')rows=rows.filter(r=>Number(r.velocity_28d||0)>0&&Number(r.velocity_7d||0)>=Number(r.velocity_28d||0)*0.8);
  const s=state.salesSort||'sales_desc';
  const n=v=>Number(v||0);
  if(s==='sales_desc')rows.sort((x,y)=>n(y.sales_amount)-n(x.sales_amount));
  if(s==='qty_desc')rows.sort((x,y)=>n(y.sold_quantity)-n(x.sold_quantity));
  if(s==='price_desc')rows.sort((x,y)=>n(y.avg_sold_price)-n(x.avg_sold_price));
  if(s==='vel7_desc')rows.sort((x,y)=>n(y.velocity_7d)-n(x.velocity_7d));
  if(s==='vel28_desc')rows.sort((x,y)=>n(y.velocity_28d)-n(x.velocity_28d));
  if(s==='drop_desc')rows.sort((x,y)=>(n(y.velocity_28d)-n(y.velocity_7d))-(n(x.velocity_28d)-n(x.velocity_7d)));
  if(s==='name')rows.sort((x,y)=>String(x.name||'').localeCompare(String(y.name||'')));
  return rows;
}
function renderSales(){const rows=filteredSalesRows();$('#salesCount').textContent=`${rows.length} shown · ${state.salesRows.length} loaded`;$('#sellRows').innerHTML=rows.map(r=>`<tr><td><div class="name">${esc(r.name)}</div><div class="meta">Family ${esc(r.family_article_number||'')}</div></td><td>${esc(r.upc)}</td><td>${esc(r.category)}</td><td>${fmt(r.sold_quantity)} ${esc(r.qty_uom||'')}</td><td>${money(r.sales_amount)}</td><td>${money(r.avg_sold_price)}<div class="meta">Historical · report date</div></td><td><b>${money(r.current_price)}</b><div class="meta">${esc(r.current_price_type||'—')} · ${esc(r.current_price_source||'—')}${r.current_price_asof_date?' · '+esc(r.current_price_asof_date):''}</div></td><td>${fmt(r.velocity_7d)}</td><td>${fmt(r.velocity_28d)}</td></tr>`).join('')||'<tr><td colspan="9" class="empty">No sales rows match the current filters.</td></tr>'}
$$('.salescat').forEach(b=>b.onclick=()=>{state.salesCat=b.dataset.cat;$$('.salescat').forEach(x=>x.classList.toggle('on',x===b));loadSell()});
$('#salesTextFilter').oninput=e=>{state.salesText=e.target.value;renderSales()};
$('#salesTrendFilter').onchange=e=>{state.salesTrend=e.target.value;renderSales()};
$('#salesSort').onchange=e=>{state.salesSort=e.target.value;renderSales()};

async function loadOrders(){const err=$('#orderError');err.innerHTML='';$('#orderRows').innerHTML='<tr><td colspan="9" class="loading">Loading...</td></tr>';try{const d=await api('/v1/backoffice/ordering-review?category=ALL');state.orders=d.rows||[];renderOrders()}catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#orderRows').innerHTML=''}}
function orderRows(){let a=[...state.orders];if(state.orderFilter==='FRESH')a=a.filter(x=>String(x.category).toUpperCase()==='FRESH');if(state.orderFilter==='FROZEN')a=a.filter(x=>String(x.category).toUpperCase()==='FROZEN');if(state.orderFilter==='ATTENTION')a=a.filter(x=>x.attention);const s=$('#orderSort').value;if(s==='suggested')a.sort((x,y)=>Number(y.suggested_delivery_qty||0)-Number(x.suggested_delivery_qty||0));if(s==='receipt')a.sort((x,y)=>String(y.last_receipt_date||'').localeCompare(String(x.last_receipt_date||'')));if(s==='oh')a.sort((x,y)=>Number(x.oh??1e18)-Number(y.oh??1e18));if(s==='frequency')a.sort((x,y)=>String(x.ordering_frequency||'').localeCompare(String(y.ordering_frequency||'')));if(s==='family')a.sort((x,y)=>String(x.family_name||'').localeCompare(String(y.family_name||'')));return a}
function renderOrders(){const a=orderRows();$('#orderCount').textContent=`${a.length} families`;$('#orderRows').innerHTML=a.map(r=>`<tr><td><div class="name">${esc(r.family_name||'—')}</div></td><td><b>${esc(r.receiving_article||'—')}</b></td><td><b>${esc(r.family_article||'—')}</b></td><td>${fmt(r.oh)} ${esc(r.oh_uom||'')}</td><td>${esc(r.last_receipt_date||'—')}</td><td><b>${fmt(r.last_receipt_qty_base)} ${esc(r.last_receipt_base_uom||'')}</b></td><td>${esc(r.ordering_frequency||'—')}</td><td><span class="suggest">${fmt(r.suggested_delivery_qty)} ${esc(r.suggested_delivery_uom||'')}</span></td><td><button class="btn small orderdetail" data-family="${esc(r.family_article)}">Details / Why?</button></td></tr>`).join('')||'<tr><td colspan="9" class="empty">No ordering suggestions match this filter.</td></tr>';$$('.orderdetail').forEach(b=>b.onclick=()=>openOrderDetail(b.dataset.family))}
$$('.ordfilter').forEach(b=>b.onclick=()=>{state.orderFilter=b.dataset.filter;$$('.ordfilter').forEach(x=>x.classList.toggle('on',x===b));renderOrders()});$('#orderSort').onchange=renderOrders;
function openOrderDetail(fam){const r=state.orders.find(x=>String(x.family_article)===String(fam));if(!r)return;const d=r.details||{},reasons=d.reasons||[], recArts=d.receiving_articles_on_last_receipt||[];openDrawer('Ordering Detail / Why?',`${r.family_name} · Family ${r.family_article}`,`<div class="detailgrid"><div class="detail"><small>Receiving Article</small><b>${esc(r.receiving_article||'—')}</b></div><div class="detail"><small>Family OH</small><b>${fmt(r.oh)} ${esc(r.oh_uom||'')}</b></div><div class="detail"><small>Last Receipt</small><b>${esc(r.last_receipt_date||'—')}</b></div><div class="detail"><small>Receipt Qty · Base</small><b>${fmt(r.last_receipt_qty_base)} ${esc(r.last_receipt_base_uom||'')}</b></div><div class="detail"><small>Family 7D Movement</small><b>${fmt(d.qty_7d)}</b></div><div class="detail"><small>Family 28D Movement</small><b>${fmt(d.qty_28d)}</b></div><div class="detail"><small>7D Velocity</small><b>${fmt(d.velocity_7d)}/day</b></div><div class="detail"><small>DOS</small><b>${fmt(d.dos)}</b></div></div><div class="sectiontitle">Why this suggestion?</div><div class="reasonlist">${reasons.map(x=>`<div class="reason"><span class="rdot"></span><div><b>${esc(x.title)}</b><span>${esc(x.detail)}</span></div></div>`).join('')}</div><div class="calc">Coming delivery suggestion ≈ expected family usage through coverage window − usable family OH + promotion/safety adjustment. Incoming is not used as a displayed Ordering Review field.</div>${recArts.length?`<div class="sectiontitle">Receiving Articles on Last Receipt</div><div class="reasonlist">${recArts.map(x=>`<div class="reason"><span class="rdot"></span><div><b>${esc(x.article_number)}</b><span>${fmt(x.quantity)} ${esc(x.base_uom||'')} · Base UOM</span></div></div>`).join('')}</div>`:''}`,`<span class="pill blue">READ ONLY</span>`)}

async function loadPrices(){const err=$('#priceError');err.innerHTML='';$('#priceRows').innerHTML='<tr><td colspan="12" class="loading">Loading...</td></tr>';try{const d=await api(`/v1/backoffice/pricing-review?category=${encodeURIComponent(state.priceCat)}&limit=1000`);state.prices=d.rows||[];renderPrices()}catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#priceRows').innerHTML=''}}
function filteredPrices(){
  let a=[...state.prices];
  const status=String(state.priceStatus||'ALL').toUpperCase();
  const text=String(state.priceText||'').trim().toLowerCase();
  if(status!=='ALL')a=a.filter(r=>String(r.review_status||'').toUpperCase()===status);
  if(text)a=a.filter(r=>[r.name,r.upc,r.family_name,r.family_article_number,r.review_status,r.review_blocker,r.primary_reason_text,...(r.reasons||[])].join(' ').toLowerCase().includes(text));
  const sort=state.priceSort||'opportunity';
  if(sort==='opportunity')a.sort((x,y)=>Number(y.gp_per_day_opportunity||0)-Number(x.gp_per_day_opportunity||0)||Number(y.urgency_score||0)-Number(x.urgency_score||0));
  if(sort==='urgency')a.sort((x,y)=>Number(y.urgency_score||0)-Number(x.urgency_score||0)||Number(y.gp_per_day_opportunity||0)-Number(x.gp_per_day_opportunity||0));
  if(sort==='gap')a.sort((x,y)=>Number(y.price_gap_pct||0)-Number(x.price_gap_pct||0));
  if(sort==='qty7')a.sort((x,y)=>Number(y.qty_7d||0)-Number(x.qty_7d||0));
  if(sort==='qty28')a.sort((x,y)=>Number(y.qty_28d||0)-Number(x.qty_28d||0));
  if(sort==='lowgp')a.sort((x,y)=>Number(x.current_gp_pct_reference??999)-Number(y.current_gp_pct_reference??999));
  if(sort==='currentprice')a.sort((x,y)=>Number(y.current_price||0)-Number(x.current_price||0));
  if(sort==='name')a.sort((x,y)=>String(x.name||'').localeCompare(String(y.name||'')));
  return a;
}
function renderPrices(){const rows=filteredPrices();$('#priceCount').textContent=`${rows.length} shown · ${state.prices.length} loaded`;$('#priceRows').innerHTML=rows.map(r=>{const range=(r.company_range_low!==null&&r.company_range_low!==undefined)?money(r.company_range_low)+' – '+money(r.company_range_high):'No A/B/C';return `<tr><td><div class="name">${esc(r.name)}</div><div class="meta">${esc(r.family_name||'')}</div></td><td><div class="name">${esc(r.upc)}</div><div class="meta">${esc(r.name||'')}</div></td><td><b>${money(r.current_price)}</b><div class="meta">${esc(r.current_price_type||'—')} · ${esc(r.current_price_source||'—')}${r.current_price_observed_date?' · '+esc(r.current_price_observed_date):''}</div></td><td><b>${money(r.candidate_price)}</b><div class="meta">${esc(r.selection_basis||r.suggestion_basis||'')}</div></td><td><b>${fmt(r.current_oh)} ${esc(r.current_oh_uom||'')}</b><div class="meta">DOH ${fmt(r.doh)}</div></td><td><b>${esc(range)}</b><div class="meta">${r.has_company_reference?'Candidate constrained':'No company constraint'}</div></td><td><b>${money(r.current_cost)}</b><div class="meta">${esc(r.current_cost_source||r.cost_basis||'—')}${r.cost_date?' · '+esc(r.cost_date):''}</div></td><td>${pct(r.current_gp_pct_reference)}</td><td>${fmt(r.qty_14d)}</td><td>${pill(r.review_status)}</td><td><div class="meta" style="max-width:240px">${esc(r.primary_reason_text||r.review_blocker||'Pricing review')}</div></td><td><div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn small pricedetail" data-upc="${esc(r.upc)}">Why?</button>${String(r.review_status||"").toUpperCase()==="ACTIONABLE"&&r.current_price!==null&&r.current_price!==undefined&&r.candidate_price!==null&&r.candidate_price!==undefined?`<button class="btn small primary priceaccept" data-upc="${esc(r.upc)}">Accepted</button>`:""}</div></td></tr>`}).join('')||'<tr><td colspan="12" class="empty">No pricing review rows match the current filters.</td></tr>';$$('.pricedetail').forEach(b=>b.onclick=()=>openPriceDetail(b.dataset.upc));$$('.priceaccept').forEach(b=>b.onclick=()=>acceptPriceSuggestion(b.dataset.upc,b))}
async function acceptPriceSuggestion(upc,button){
 const r=state.prices.find(x=>String(x.upc)===String(upc));if(!r)return;
 if(button){button.disabled=true;button.textContent='Saving…'}
 try{
   await api('/v1/backoffice/pricing-review/'+encodeURIComponent(upc)+'/accept',{
     method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({current_price:r.current_price,current_price_source:r.current_price_source,current_price_asof_date:r.current_price_observed_date,candidate_price:r.candidate_price})
   });
   state.prices=state.prices.filter(x=>String(x.upc)!==String(upc));
   renderPrices();
   toast('Accepted · hidden until new price evidence or a new suggestion');
 }catch(e){
   toast(e.message);
   if(button){button.disabled=false;button.textContent='Accepted'}
   if(String(e.message||'').includes('REFRESH')||String(e.message||'').includes('CHANGED'))loadPrices();
 }
}
$$('.pricefilter').forEach(b=>b.onclick=()=>{state.priceCat=b.dataset.cat;$$('.pricefilter').forEach(x=>x.classList.toggle('on',x===b));loadPrices()});
$('#priceStatusFilter').onchange=e=>{state.priceStatus=e.target.value;renderPrices()};
$('#priceSort').onchange=e=>{state.priceSort=e.target.value;renderPrices()};
$('#priceTextFilter').oninput=e=>{state.priceText=e.target.value;renderPrices()};
function openPriceDetail(upc){const r=state.prices.find(x=>String(x.upc)===String(upc));if(!r)return;const company=[['A',r.company_price_a],['B',r.company_price_b],['C',r.company_price_c]].filter(x=>x[1]!==null&&x[1]!==undefined);const companyText=company.length?company.map(x=>x[0]+' '+money(x[1])).join(' · '):'No Company A/B/C reference';const rangeText=(r.company_range_low!==null&&r.company_range_low!==undefined)?money(r.company_range_low)+' – '+money(r.company_range_high):'—';openDrawer('Price Suggestion Explanation',`${r.name} · UPC ${r.upc}`,`<div class="detailgrid"><div class="detail"><small>Current Price</small><b>${money(r.current_price)}</b><span>${esc(r.current_price_type||'—')} · ${esc(r.current_price_source||'—')}${r.current_price_observed_date?' · '+esc(r.current_price_observed_date):''}</span></div><div class="detail"><small>Candidate Price</small><b>${money(r.candidate_price)}</b><span>${esc(r.selection_basis||r.suggestion_basis||'')}</span></div><div class="detail"><small>Current Cost</small><b>${money(r.current_cost)}</b><span>${esc(r.current_cost_source||r.cost_basis||'—')}${r.cost_date?' · '+esc(r.cost_date):''}</span></div><div class="detail"><small>Current GP%</small><b>${pct(r.current_gp_pct_reference)}</b></div><div class="detail"><small>Candidate GP%</small><b>${pct(r.suggested_gp_pct_at_current_cost)}</b></div><div class="detail"><small>Company A/B/C</small><b>${esc(companyText)}</b><span>Range: ${esc(rangeText)}</span></div><div class="detail"><small>DOH</small><b>${fmt(r.doh)}</b><span>${r.clearance_due_to_doh?'Clearance mode':'Standard pricing mode'}</span></div><div class="detail"><small>14D Qty</small><b>${fmt(r.qty_14d)}</b></div><div class="detail"><small>7D Velocity</small><b>${fmt(r.velocity_7d)}</b></div><div class="detail"><small>14D Velocity</small><b>${fmt(r.velocity_14d)}</b></div><div class="detail"><small>GP$/Day Current</small><b>${money(r.current_gp_per_day_7d)}</b></div><div class="detail"><small>GP$/Day Candidate</small><b>${money(r.candidate_expected_gp_per_day)}</b></div></div><div class="sectiontitle">Primary reason</div><div class="calc">${esc(r.primary_reason_text||'Pricing review')}</div><div class="sectiontitle">Rule used</div><div class="calc">${r.clearance_reason==='FROZEN_DOH_GT_60'?'Frozen DOH > 60: qualified price review. Candidate maximizes supported 14D GP$/day; Company A/B/C range is enforced when available.':(r.clearance_due_to_doh?'Fresh DOH > 7: qualified price review. Candidate maximizes supported 14D GP$/day; Company A/B/C range is enforced when available.':(r.has_company_reference?'Qualified stocked item: candidate maximizes 14D GP$/day and must stay inside the Company A/B/C range.':'Qualified stocked item with no Company A/B/C: candidate maximizes 14D GP$/day from observed sales history.'))}</div><div class="calc">Current Price and Current Cost come from the live Quick Check serving row. Pricing Review is read-only.</div>`,`<span class="pill blue">READ ONLY</span>`)}

async function loadQA(){
 const err=$('#qaError');err.innerHTML='';$('#qaRows').innerHTML='<tr><td colspan="8" class="loading">Loading QA...</td></tr>';
 try{
   const d=await api('/v1/backoffice/qa-review?limit=300');
   state.qaIssues=d.issues||[];state.qaHistory=d.resolution_history||[];
   renderQA();
 }catch(e){err.innerHTML=`<div class="error">${esc(e.message)}</div>`;$('#qaRows').innerHTML=''}
}
function qaNumeric(v,fallback=-Infinity){const n=Number(v);return Number.isFinite(n)?n:fallback}
function qaSearchBlob(x){
 const cur=x.current||{};
 return [x.entity_key,x.issue_code,x.issue_summary,x.entity_type,cur.article_number,cur.main_article_number,cur.family_description,cur.item_name,cur.selling_description,cur.chinese_name,cur.selling_uom].filter(Boolean).join(' ').toLowerCase();
}
function qaSortRows(a){
 const sev={CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3};
 const sort=state.qaSort||'oh_vel_desc';
 return a.sort((x,y)=>{
   const xc=x.current||{},yc=y.current||{};
   const xoh=qaNumeric(xc.current_oh),yoh=qaNumeric(yc.current_oh);
   const xv=qaNumeric(xc.upc_velocity_7d),yv=qaNumeric(yc.upc_velocity_7d);
   if(sort==='vel_oh_desc')return (yv-xv)||(yoh-xoh)||String(x.entity_key||'').localeCompare(String(y.entity_key||''));
   if(sort==='severity')return ((sev[String(x.severity||'').toUpperCase()]??9)-(sev[String(y.severity||'').toUpperCase()]??9))||(yoh-xoh)||(yv-xv);
   if(sort==='name')return String(xc.item_name||xc.selling_description||'').localeCompare(String(yc.item_name||yc.selling_description||''))||String(x.entity_key||'').localeCompare(String(y.entity_key||''));
   if(sort==='upc')return String(x.entity_key||'').localeCompare(String(y.entity_key||''),undefined,{numeric:true});
   return (yoh-xoh)||(yv-xv)||String(x.entity_key||'').localeCompare(String(y.entity_key||''));
 });
}
function filteredQA(){
 let a=[...state.qaIssues];
 if(state.qaFilter==='FIXABLE')a=a.filter(x=>x.can_fix);
 if(state.qaFilter==='VIEW_ONLY')a=a.filter(x=>!x.can_fix);
 if(state.qaFilter==='HIGH')a=a.filter(x=>['HIGH','CRITICAL'].includes(String(x.severity||'').toUpperCase()));
 const q=String(state.qaText||'').trim().toLowerCase();
 if(q)a=a.filter(x=>qaSearchBlob(x).includes(q));
 return qaSortRows(a);
}
function renderQA(){
 const a=filteredQA();$('#qaCount').textContent=`${a.length} shown · ${state.qaIssues.length} open`;
 $('#qaRows').innerHTML=a.map(x=>{
   const cur=x.current||{};
   const entityType=String(x.entity_type||'').toUpperCase();
   const code=String(x.issue_code||'').toUpperCase();
   const stateParts=[
     cur.article_number?('Article '+cur.article_number):'',
     cur.main_article_number?('Family '+cur.main_article_number):''
   ];
   if(entityType==='UPC'){
     stateParts.push(cur.selling_uom?('UOM '+cur.selling_uom):'UOM missing');
   }else if(entityType==='ARTICLE' && code.includes('ARTICLE_UNMAPPED')){
     stateParts.push('Family mapping missing');
   }
   const stateText=stateParts.filter(Boolean).join(' · ');
   return `<tr>
     <td>${pill(x.severity)}</td>
     <td><div class="name">${esc(x.issue_code)}</div><div class="meta" style="max-width:380px">${esc(x.issue_summary||'')}</div></td>
     <td><b>${esc(x.entity_key||'—')}</b><div class="meta">${esc(entityType==='UPC'?(cur.item_name||cur.selling_description||'Item name unavailable'):(cur.item_name||x.entity_type||''))}</div>${cur.chinese_name?`<div class="qa-cn-list">${esc(cur.chinese_name)}</div>`:''}${cur.main_article_number?`<div class="meta">Family ${esc(cur.main_article_number)}${cur.family_description?' · '+esc(cur.family_description):''}</div>`:''}</td>
     <td><b>${fmt(cur.current_oh)}</b><div class="meta">${esc(cur.current_oh_uom||'')}</div></td>
     <td><b>${fmt(cur.upc_velocity_7d)}</b><div class="meta">${esc(cur.selling_uom||'unit')}/day</div></td>
     <td>${esc(stateText||'No current serving row')}</td>
     <td>${x.can_fix?'<span class="pill amber">USER CONFIRM</span>':'<span class="pill blue">VIEW ONLY</span>'}</td>
     <td><button class="btn small qadetail" data-key="${esc(String(x.issue_id??('QC:'+x.entity_key)))}">${x.can_fix?'Fix':'Details'}</button></td>
   </tr>`;
 }).join('')||'<tr><td colspan="8" class="empty">No QA issues match this search / filter.</td></tr>';
 $$('.qadetail').forEach(b=>b.onclick=()=>openQAIssue(b.dataset.key));
 $('#qaHistoryRows').innerHTML=state.qaHistory.map(h=>`<tr><td>${esc(h.created_at||'—')}</td><td><b>${esc(h.entity_key||'')}</b><div class="meta">${esc(h.entity_type||'')}</div></td><td>${esc(h.issue_code||'')}</td><td>${esc(h.resolution_kind||'')}</td><td>${esc(h.actor||'')}</td><td>${esc(h.resolution_note||'—')}</td></tr>`).join('')||'<tr><td colspan="6" class="empty">No manual QA resolutions yet.</td></tr>';
}
function findQAIssue(key){
 if(String(key).startsWith('QC:'))return state.qaIssues.find(x=>x.issue_id===null&&('QC:'+x.entity_key)===key);
 return state.qaIssues.find(x=>String(x.issue_id)===String(key));
}
function qaFixKindLabel(kind){
 const k=String(kind||'').toUpperCase();
 if(k==='UOM_OR_IDENTITY'||k==='IDENTITY_AND_UOM')return 'Selling unit / item link';
 if(k==='COST_CONVERSION')return 'Cost conversion';
 if(k==='ARTICLE_FAMILY_MAPPING')return 'Article → Family mapping';
 return String(kind||'Review');
}
function qaFriendlyReasons(x,detail){
 const codes=Array.isArray(detail?.reasons)?detail.reasons.map(v=>String(v||'').toUpperCase()):[];
 const labels={
  SELLING_UOM_MISSING:'Selling UOM is missing. Select the unit represented by POS Qty = 1 for this UPC.',
  CURRENT_ACTIVE_SELLING_UOM_MISSING:'Selling UOM is missing for an actively selling UPC. Select the POS selling unit.',
  COST_TO_SELLING_UOM_UNRESOLVED:'Cost cannot yet be converted to the selling unit. Confirm the Selling UOM first; a separate cost-conversion QA step may remain afterward.',
  CURRENT_COST_MISSING:'Current cost is missing. This cannot be corrected from the identity/UOM form.',
  CURRENT_PRICE_MISSING:'Current selling price is missing. This form does not edit price.',
  OH_MOVEMENT_ROLLFORWARD_BLOCKED:'Current OH roll-forward has a movement/UOM blocker. Review the inventory lineage after the unit is corrected.'
 };
 const out=[];
 codes.forEach(c=>{if(labels[c]&&!out.includes(labels[c]))out.push(labels[c])});
 if(!out.length&&x.issue_summary)out.push(x.issue_summary);
 if(!out.length)out.push('Review the current item identity and unit information before applying a correction.');
 return out;
}
function qaApplyFeedback(msg,kind=''){
 const foot=$('#drawerFoot');
 if(foot){let el=$('#qaApplyFeedback');if(!el){el=document.createElement('div');el.id='qaApplyFeedback';foot.prepend(el)}el.textContent=String(msg||'');el.className='qa-inline-feedback on'+(kind?' '+kind:'')}
 toast(String(msg||''));
}
function qaClearFeedback(){const el=$('#qaApplyFeedback');if(el)el.remove()}
function qaRemainingForEntity(entityKey){return state.qaIssues.filter(x=>String(x.entity_key||'')===String(entityKey||''))}
function qaRemainingMessage(entityKey,savedLabel='QA fix saved'){
 const remaining=qaRemainingForEntity(entityKey);
 if(!remaining.length)return savedLabel+' · no QA issues remain';
 const first=remaining[0];
 const kind=qaFixKindLabel(first.fix_kind);
 const code=String(first.issue_code||first.issue_summary||'QA HOLD');
 return savedLabel+' · '+remaining.length+' QA '+(remaining.length===1?'issue':'issues')+' remain · '+kind+' · '+code;
}
async function qaRefreshAfterApply(entityKey,{withInventory=true,withBatches=false}={}){
 const jobs=[loadQA()];
 if(withInventory)jobs.push(loadInventory());
 if(withBatches)jobs.push(loadBatches());
 await Promise.allSettled(jobs);
 if(isMobileBackoffice()&&mobileState.module==='qa')mobileRenderList();
 return qaRemainingForEntity(entityKey);
}
function openQAIssue(key){
 qaClearFeedback();
 const x=findQAIssue(key);if(!x)return;
 const cur=x.current||{},detail=x.detail||{};
 const itemName=cur.item_name||cur.selling_description||cur.article_description||(Array.isArray(detail.descriptions)&&detail.descriptions[0])||'Item name unavailable';
 const chineseName=cur.chinese_name||detail.chinese_name||detail.chinese_description||'';
 const detailJson=esc(JSON.stringify(detail,null,2));
 if(x.fix_kind==='ARTICLE_FAMILY_MAPPING'){
   const article=String(x.entity_key||'').trim();
   const descriptions=Array.isArray(detail.descriptions)?detail.descriptions.join(' · '):'';
   const dates=Array.isArray(detail.posting_dates)?detail.posting_dates.join(', '):'';
   const movements=Array.isArray(detail.movement_types)?detail.movement_types.join(', '):'';
   openDrawer('Map Article to Family',`${itemName}${chineseName?' · '+chineseName:''} · Article ${esc(article)}`,`
     <div class="qa-identity"><div class="qa-name">${esc(itemName)}</div>${chineseName?`<div class="qa-zh">${esc(chineseName)}</div>`:''}<div class="qa-idmeta"><span>Article ${esc(article)}</span><span>Article → Family mapping</span></div></div>
     <div class="detailgrid">
       <div class="detail"><small>Unmapped Article</small><b>${esc(article)}</b></div>
       <div class="detail"><small>Movement Rows</small><b>${fmt(detail.row_count,0)}</b></div>
       <div class="detail"><small>Movement Types</small><b>${esc(movements||'—')}</b></div>
       <div class="detail"><small>Posting Dates</small><b>${esc(dates||'—')}</b></div>
     </div>
     <div class="sectiontitle">Movement evidence</div>
     <div class="calc">${esc(descriptions||x.issue_summary||'No description evidence available.')}</div>
     <div class="sectiontitle">User-confirmed Family mapping</div>
     <div class="formfield"><label>Article Number</label><input id="qaMapArticle" value="${esc(article)}" readonly></div>
     <div class="formfield"><label>Main / Family Article Number</label><input id="qaMapFamily" placeholder="Enter the confirmed Main/Family Article"></div>
     <div class="formfield"><label>Resolution Note</label><textarea id="qaMapNote" placeholder="How the Article → Family relationship was confirmed"></textarea></div>
     <label style="display:flex;gap:7px;align-items:flex-start;margin-top:10px;font-size:9px"><input id="qaMapConfirm" type="checkbox" style="margin-top:2px"><span>I confirm this Article belongs to the Family/Main Article entered above. This affects family movement and downstream family calculations after Phase 3 rebuild.</span></label>
     <div class="calc"><b>Fail-closed.</b> The target Family must already exist, and an Article already mapped to a different confirmed Family will be blocked. RAW movement values are never changed.</div>
   `,`<button id="applyQAArticleFamily" class="btn primary">Apply Family Mapping</button>`);
   $('#applyQAArticleFamily').onclick=async()=>{
     if(!$('#qaMapConfirm').checked){qaApplyFeedback('Confirm the Article → Family mapping first','error');return}
     const main=($('#qaMapFamily').value||'').trim();
     if(!main){qaApplyFeedback('Enter the Main / Family Article number','error');return}
     const btn=$('#applyQAArticleFamily');btn.disabled=true;btn.textContent='Applying…';qaApplyFeedback('Applying Family mapping…','working');
     try{
       const d=await api('/v1/backoffice/qa-resolve-article-family',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
         issue_id:x.issue_id,
         article_number:article,
         main_article_number:main,
         note:($('#qaMapNote').value||'').trim()||null,
         confirm:'APPLY_ARTICLE_FAMILY_FIX'
       })});
       qaApplyFeedback('Family mapping saved. Refreshing QA and batch status…','success');
       closeDrawer();
       await qaRefreshAfterApply(article,{withInventory:false,withBatches:true});
       toast(qaRemainingMessage(article,'Family mapping saved')+' · Rebuild Phase 3 / QA to recalculate family movement.');
     }catch(e){qaApplyFeedback(e.message,'error')}finally{const z=$('#applyQAArticleFamily');if(z){z.disabled=false;z.textContent='Apply Family Mapping'}}
   };
   return;
 }
 if(x.fix_kind==='COST_CONVERSION'){
   const sell=String(cur.selling_uom||detail.selling_uom||'').toUpperCase();
   const costUom=String(detail.cost_uom||'').toUpperCase();
   openDrawer('Confirm Cost Conversion',`${itemName}${chineseName?' · '+chineseName:''} · UPC ${x.entity_key}`,`
     <div class="qa-identity"><div class="qa-name">${esc(itemName)}</div>${chineseName?`<div class="qa-zh">${esc(chineseName)}</div>`:''}<div class="qa-idmeta"><span>UPC ${esc(x.entity_key)}</span><span>Article ${esc(cur.article_number||cur.main_article_number||'—')}</span><span>Family ${esc(cur.main_article_number||'—')}</span></div></div>
     <div class="detailgrid">
       <div class="detail"><small>UPC</small><b>${esc(x.entity_key)}</b></div>
       <div class="detail"><small>Article</small><b>${esc(cur.article_number||cur.main_article_number||'—')}</b></div>
       <div class="detail"><small>Selling UOM</small><b>${esc(sell||'Missing')}</b></div>
       <div class="detail"><small>Cost UOM</small><b>${esc(costUom||'Unknown')}</b></div>
     </div>
     <div class="sectiontitle">Issue</div><div class="calc">${esc(x.issue_summary||'')}</div>
     <div class="sectiontitle">User-confirmed conversion</div>
     <div class="formfield"><label>Selling Quantity</label><input id="qaConvSellQty" type="number" min="0.0001" step="0.0001" value="1"></div>
     <div class="formfield"><label>Selling UOM</label><input id="qaConvSellUom" value="${esc(sell)}" readonly></div>
     <div class="formfield"><label>Cost Quantity represented by that selling quantity</label><input id="qaConvCostQty" type="number" min="0.0001" step="0.0001" placeholder="Example: 2"></div>
     <div class="formfield"><label>Cost UOM</label><input id="qaConvCostUom" value="${esc(costUom)}" readonly></div>
     <div class="formfield"><label>Resolution Note</label><textarea id="qaConvNote" placeholder="What you confirmed, e.g. 1 PACK = 2 LB"></textarea></div>
     <label style="display:flex;gap:7px;align-items:flex-start;margin-top:10px;font-size:9px"><input id="qaConvConfirm" type="checkbox" style="margin-top:2px"><span>I confirm this exact cost-to-selling conversion. This does not change the source cost value or RAW data.</span></label>
     <div class="calc">Write scope: conversion authority only. Existing cost, POS sales, receipts, and source files remain unchanged.</div>
   `,`<button id="applyQACostConversion" class="btn primary">Apply Cost Conversion</button>`);
   const btn=$('#applyQACostConversion');
   if(!sell||!costUom){btn.disabled=true;qaApplyFeedback('Selling UOM and Cost UOM must both be known before conversion can be confirmed','error');return}
   btn.onclick=async()=>{
     if(!$('#qaConvConfirm').checked){qaApplyFeedback('Confirm the conversion first','error');return}
     const sq=Number($('#qaConvSellQty').value),cq=Number($('#qaConvCostQty').value);
     if(!(sq>0)||!(cq>0)){qaApplyFeedback('Enter positive conversion quantities','error');return}
     btn.disabled=true;btn.textContent='Applying…';qaApplyFeedback('Applying cost conversion…','working');
     try{
       await api('/v1/backoffice/qa-resolve-cost-conversion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
         issue_id:x.issue_id,
         ean_upc:x.entity_key,
         selling_qty:sq,
         selling_uom:sell,
         cost_qty:cq,
         cost_uom:costUom,
         note:($('#qaConvNote').value||'').trim()||null,
         confirm:'APPLY_COST_CONVERSION_FIX'
       })});
       qaApplyFeedback('Cost conversion saved. Refreshing QA and inventory…','success');
       closeDrawer();
       await qaRefreshAfterApply(x.entity_key);
       toast(qaRemainingMessage(x.entity_key,'Cost conversion saved'));
     }catch(e){qaApplyFeedback(e.message,'error')}finally{const z=$('#applyQACostConversion');if(z){z.disabled=false;z.textContent='Apply Cost Conversion'}}
   };
   return;
 }
 if(!x.can_fix){
   openDrawer('QA Issue Details',`${itemName}${chineseName?' · '+chineseName:''} · ${x.entity_key}`,`<div class="qa-identity"><div class="qa-name">${esc(itemName)}</div>${chineseName?`<div class="qa-zh">${esc(chineseName)}</div>`:''}<div class="qa-idmeta"><span>${esc(x.entity_type)} ${esc(x.entity_key)}</span><span>Article ${esc(cur.article_number||'—')}</span><span>Family ${esc(cur.main_article_number||'—')}</span></div></div><div class="detailgrid"><div class="detail"><small>Severity</small><b>${esc(x.severity)}</b></div><div class="detail"><small>Entity</small><b>${esc(x.entity_type)} · ${esc(x.entity_key)}</b></div><div class="detail"><small>Batch</small><b>#${esc(x.batch_id??'—')}</b></div><div class="detail"><small>Fix Scope</small><b>View only</b></div></div><div class="sectiontitle">Summary</div><div class="calc">${esc(x.issue_summary||'')}</div><div class="sectiontitle">Evidence / Detail</div><pre class="logconsole" style="white-space:pre-wrap">${detailJson}</pre>`,`<span class="pill blue">VIEW ONLY</span>`);
   return;
 }
 const article=cur.article_number||cur.main_article_number||'';
 const sell=cur.selling_uom||'';
 const base=cur.base_uom||'';
 const factor=cur.base_qty_per_selling_unit??'';
 const friendlyReasons=qaFriendlyReasons(x,detail);
 const advancedOpen=(base||factor!=='')?' open':'';
 openDrawer('Fix QA',`${itemName} · UPC ${x.entity_key}`,`
   <div class="qa-identity">
     <div class="qa-name">${esc(itemName)}</div>
     ${chineseName?`<div class="qa-zh">${esc(chineseName)}</div>`:''}
     <div class="qa-idmeta">
       <span>UPC ${esc(x.entity_key)}</span>
       <span>Article ${esc(article||'Not linked')}</span>
       <span>${esc(qaFixKindLabel(x.fix_kind))}</span>
     </div>
   </div>

   <div class="qa-step">
     <div class="qa-stephead"><span class="qa-stepnum">1</span><div><b>What needs fixing</b><span>Start with the field that is blocking Quick Check.</span></div></div>
     <div class="qa-reasons">${friendlyReasons.map(r=>`<div class="qa-reason">${esc(r)}</div>`).join('')}</div>
     <details class="qa-technical"><summary>Show technical QA reason</summary><div class="calc">${esc(x.issue_summary||'')}</div></details>
   </div>

   <div class="qa-step">
     <div class="qa-stephead"><span class="qa-stepnum">2</span><div><b>Enter the confirmed correction</b><span>Only change values you have verified. No price, cost, sales, receipt, or RAW source value is edited here.</span></div></div>
     <div class="detailgrid qa-detailgrid">
       <div class="detail"><small>Current Selling UOM</small><b>${esc(sell||'Missing')}</b></div>
       <div class="detail"><small>Current Article</small><b>${esc(article||'Not linked')}</b></div>
     </div>
     <div class="formfield"><label>Selling UOM <span class="qa-required">REQUIRED</span></label><select id="qaSellingUom"><option value="">Select how this UPC is sold...</option>${['LB','EA','PACK','PAC','CASE','BAG','BX','TRAY'].map(u=>`<option value="${u}" ${String(sell).toUpperCase()===u?'selected':''}>${u}</option>`).join('')}</select><div class="qa-field-help">Choose the unit represented by POS Qty = 1. Example: weighted seafood sold by the pound = LB; one retail bag = BAG or PACK only when confirmed.</div></div>
     <div class="formfield"><label>Article Number</label><input id="qaArticle" value="${esc(article)}" placeholder="Required if the UPC is not linked to an Article"><div class="qa-field-help">Keep the current Article unless you have confirmed the UPC is linked to a different Article.</div></div>

     <details class="qa-advanced"${advancedOpen}><summary>Advanced: Base UOM / conversion (optional)</summary>
       <div class="qa-field-help">Leave this section blank unless the Base UOM and conversion are specifically confirmed.</div>
       <div class="formfield"><label>Base UOM</label><select id="qaBaseUom"><option value="">Not confirmed</option>${['LB','EA','PACK','PAC','CASE','BAG','BX','TRAY'].map(u=>`<option value="${u}" ${String(base).toUpperCase()===u?'selected':''}>${u}</option>`).join('')}</select></div>
       <div class="formfield"><label>Base Qty per Selling Unit</label><input id="qaFactor" type="number" min="0" step="0.0001" value="${esc(factor)}" placeholder="Example: 2"><div class="qa-field-help">Example only when confirmed: 1 PACK = 2 LB → Base UOM LB and quantity 2.</div></div>
     </details>

     <div class="formfield"><label>Resolution Note</label><textarea id="qaNote" placeholder="Optional: what you confirmed and the source of the confirmation"></textarea></div>
   </div>

   <div class="qa-step">
     <div class="qa-stephead"><span class="qa-stepnum">3</span><div><b>Confirm and apply</b><span>The original source rows stay unchanged. The system records an audited user-confirmed override and refreshes the affected serving data.</span></div></div>
     <label class="qa-confirm"><input id="qaConfirm" type="checkbox"><span>I confirmed the item link and Selling UOM entered above.</span></label>
     <div class="qa-scope">Write scope: UPC identity / Selling UOM QA resolution only. Price, cost, sales, receipt quantities, and source files remain read-only.</div>
   </div>
 `,`<button id="applyQAFix" class="btn primary">Apply Confirmed QA Fix</button>`);
 $('#applyQAFix').onclick=async()=>{
   if(!$('#qaConfirm').checked){qaApplyFeedback('Check the confirmation box before applying the correction','error');return}
   const sellingUom=$('#qaSellingUom').value;
   if(!sellingUom){qaApplyFeedback('Select the Selling UOM first','error');return}
   const baseUom=$('#qaBaseUom').value||null;
   const factorRaw=($('#qaFactor').value||'').trim();
   if(baseUom&&factorRaw===''){qaApplyFeedback('Enter Base Qty per Selling Unit, or leave Base UOM unconfirmed','error');return}
   const body={
     issue_id:x.issue_id,
     ean_upc:x.entity_key,
     article_number:($('#qaArticle').value||'').trim()||null,
     selling_uom:sellingUom,
     base_uom:baseUom,
     base_qty_per_selling_unit:factorRaw===''?null:Number(factorRaw),
     note:($('#qaNote').value||'').trim()||null,
     confirm:'APPLY_QA_FIX'
   };
   const btn=$('#applyQAFix');btn.disabled=true;btn.textContent='Applying…';qaApplyFeedback('Applying confirmed QA correction…','working');
   try{
     const r=await api('/v1/backoffice/qa-resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
     qaApplyFeedback(`Saved · resolution #${r.resolution_id}. Refreshing QA and inventory…`,'success');closeDrawer();await qaRefreshAfterApply(x.entity_key);toast(qaRemainingMessage(x.entity_key,`QA fix saved · resolution #${r.resolution_id}`));
   }catch(e){qaApplyFeedback(e.message,'error')}finally{const z=$('#applyQAFix');if(z){z.disabled=false;z.textContent='Apply Confirmed QA Fix'}}
 };
}
$('#qaSearch').oninput=e=>{state.qaText=e.currentTarget.value;renderQA()};
$('#qaSort').onchange=e=>{state.qaSort=e.currentTarget.value;renderQA()};
$$('.qafilter').forEach(b=>b.onclick=()=>{state.qaFilter=b.dataset.qafilter;$$('.qafilter').forEach(x=>x.classList.toggle('on',x===b));renderQA()});
$('#qaRefresh').onclick=loadQA;

async function loadDatabaseOverview(){
  const err=$('#dbOverviewError');if(err)err.innerHTML='';
  try{
    const [h,a,r,q]=await Promise.all([api('/healthz'),api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=5'),api('/v1/backoffice/qa-review?limit=300')]);
    state.active=a.active_batch||null;state.recent=r.batches||[];state.qaIssues=q.issues||[];state.qaHistory=q.resolution_history||[];
    const latest=state.recent[0]||null;
    $('#dbOverviewActive').innerHTML=activeCard(state.active);
    $('#dbLatestBatch').innerHTML=latest?(activeCard({...latest,status:latest.processing_status||latest.phase3_status,batch_label:latest.batch_label||'Latest completed'})+rebuildActionHtml(latest,true)):'<div class="empty">No completed batch history.</div>';
    wireRebuildButtons($('#dbLatestBatch'));
    $('#dbProcessingSummary').textContent=state.active?`Batch #${state.active.batch_id||'—'} is processing`:(latest?`Latest #${latest.batch_id} · ${latest.phase3_status||latest.processing_status||'complete'}`:'No active batch');
    const fixable=state.qaIssues.filter(x=>x.can_fix).length;
    $('#dbQASummary').textContent=state.qaIssues.length?`${state.qaIssues.length} open · ${fixable} fixable`:'No open QA issues';
    $('#dbHealthSummary').textContent=h.ok?`Service healthy · ${h.version||''}`:'Service health needs attention';
    $('#dbUploadSummary').textContent=state.active?'Wait for current batch to finish':'Ready for a new source batch';
    const hasProblem=!h.ok||state.qaIssues.some(x=>['HIGH','CRITICAL'].includes(String(x.severity||'').toUpperCase()));
    const status=$('#dbOverallStatus');status.textContent=hasProblem?'ATTENTION':(state.active?'PROCESSING':'READY');status.className='pill '+(hasProblem?'amber':state.active?'sea':'green');
  }catch(e){if(err)err.innerHTML=`<div class="error">${esc(e.message)}</div>`;const st=$('#dbOverallStatus');if(st){st.textContent='CHECK FAILED';st.className='pill red'}}
}
function batchResumeEligible(b){
  const status=String(b?.processing_status||b?.status||'').toUpperCase();
  return status==='PHASE2C_READY';
}
function batchRebuildEligible(b){
  const p2=String(b?.phase2c_status||'').toUpperCase();
  const p3=String(b?.phase3_status||b?.processing_status||'').toUpperCase();
  return p2==='READY' && ['QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS','PHASE3_QA_HOLD'].includes(p3);
}
function resumeActionHtml(b,compact=false){
  if(!b||!batchResumeEligible(b))return '';
  return `<div style="${compact?'margin-top:8px':'margin-top:10px'}"><div class="calc" style="margin:0 0 8px"><b>Past:</b> Phase 2C complete ✅ &nbsp; <b>Current:</b> Waiting for Phase 3 ⚠️ &nbsp; <b>Next:</b> Phase 3 rebuild → QA → Quick Check</div><div style="display:flex;justify-content:flex-end"><button class="btn primary batch-resume-btn" data-batch="${esc(b.batch_id||b.id)}">▶ Retry Phase 3</button></div></div>`;
}
function rebuildActionHtml(b,compact=false){
  if(!b||!batchRebuildEligible(b))return '';
  return `<div style="${compact?'margin-top:8px':'margin-top:10px'};display:flex;justify-content:flex-end"><button class="btn primary batch-rebuild-btn" data-batch="${esc(b.batch_id)}">🔄 Rebuild Phase 3 / QA</button></div>`;
}
function wireRecoveryButtons(root=document){
  root.querySelectorAll('.batch-resume-btn').forEach(btn=>{
    btn.onclick=e=>{e.stopPropagation();resumePhase3(btn.dataset.batch)}
  });
  root.querySelectorAll('.batch-rebuild-btn').forEach(btn=>{
    btn.onclick=e=>{e.stopPropagation();rebuildPhase3(btn.dataset.batch)}
  });
}
async function resumePhase3(id){
  const b=(state.active&&String(state.active.batch_id||state.active.id)===String(id))?state.active:null;
  if(!b){toast('Current batch detail is not loaded yet');return}
  if(!batchResumeEligible(b)){toast('This batch is not waiting at Phase 2C');return}
  if(!window.confirm(`Retry Phase 3 for Batch #${b.batch_id||b.id}?\n\nRAW files will not be re-uploaded. This resumes the existing batch directly from Phase 3.`))return;
  const buttons=[...document.querySelectorAll(`.batch-resume-btn[data-batch="${CSS.escape(String(b.batch_id||b.id))}"]`)];
  buttons.forEach(x=>{x.disabled=true;x.textContent='Queuing Phase 3…'});
  try{
    const d=await api(`/v1/web-upload/batches/${encodeURIComponent(b.batch_id||b.id)}/resume-phase3`,{method:'POST'});
    toast(d.already_active?'Phase 3 job is already active':'Phase 3 retry queued');
    await loadBatches();
    if(isMobileBackoffice()&&mobileState.module==='batches')mobileRenderList();
  }catch(e){
    toast(e.message);
    buttons.forEach(x=>{x.disabled=false;x.textContent='▶ Retry Phase 3'});
  }
}
async function loadChatgptBridgeStatus(batchId){
  const box=$('#batchBridgeStatus');if(!box)return;
  box.innerHTML='<div class="meta">Checking ChatGPT analysis bridge…</div>';
  try{
    const d=await api(`/v1/web-upload/batches/${encodeURIComponent(batchId)}/chatgpt-publish-status`);
    const result=d.publish_result||{};
    const publishStatus=String(result.status||'').toUpperCase();
    const runStatus=String(d.status||'').toUpperCase();
    const ok=runStatus==='COMPLETED'&&publishStatus==='PASS';
    box.innerHTML=`<div class="detailgrid">
      <div class="detail"><small>Bridge Job</small><b>${esc(runStatus||'NONE')}</b></div>
      <div class="detail"><small>Sheet Publish</small><b>${esc(publishStatus||'—')}</b></div>
      <div class="detail"><small>Run ID</small><b>${esc(d.publish_run_id||'—')}</b></div>
      <div class="detail"><small>Completed</small><b>${esc(d.completed_at||'—')}</b></div>
    </div>
    <div class="calc" style="margin-top:8px">${ok?'<b>Bridge PASS.</b> ChatGPT analysis snapshot is published.':'<b>Bridge not PASS.</b> MySQL Quick Check remains live; republish affects only the ChatGPT/Google Sheet analysis snapshot.'}</div>
    <div style="display:flex;justify-content:flex-end;margin-top:8px"><button id="republishChatgptBtn" class="btn ${ok?'soft':'primary'}">↻ Republish ChatGPT Analysis</button></div>`;
    const rb=$('#republishChatgptBtn');if(rb)rb.onclick=()=>republishChatgptAnalysis(batchId,rb);
  }catch(e){box.innerHTML=`<div class="error" style="margin:0">${esc(e.message)}</div>`}
}
async function republishChatgptAnalysis(batchId,btn=null){
  if(btn){btn.disabled=true;btn.textContent='Queuing Republish…'}
  try{
    const d=await api(`/v1/web-upload/batches/${encodeURIComponent(batchId)}/republish-chatgpt-analysis`,{method:'POST'});
    toast(d.already_active?'ChatGPT analysis publish is already active':'ChatGPT analysis republish queued');
    if(btn)btn.textContent='Publishing…';
    setTimeout(()=>loadChatgptBridgeStatus(batchId),1500);
  }catch(e){
    toast(e.message);
    if(btn){btn.disabled=false;btn.textContent='↻ Republish ChatGPT Analysis'}
  }
}

async function rebuildPhase3(id){
  const b=state.recent.find(x=>String(x.batch_id)===String(id));
  if(!b){toast('Batch detail is not loaded yet');return}
  if(!batchRebuildEligible(b)){toast('This batch is not currently eligible for Phase 3 rebuild');return}
  if(!window.confirm(`Rebuild Phase 3 / QA for Batch #${b.batch_id}?\n\nRAW files will not be re-uploaded. The current Quick Check snapshot remains active until the rebuild commits.`))return;
  const buttons=[...document.querySelectorAll(`.batch-rebuild-btn[data-batch="${CSS.escape(String(b.batch_id))}"]`)];
  buttons.forEach(x=>{x.disabled=true;x.textContent='Queuing Rebuild…'});
  try{
    const d=await api(`/v1/web-upload/batches/${encodeURIComponent(b.batch_id)}/rebuild-phase3`,{method:'POST'});
    toast(d.already_active?'Phase 3 rebuild is already active':'Phase 3 / QA rebuild queued');
    closeDrawer();
    showDbTab('dboverview');
    await loadBatches();
  }catch(e){
    toast(e.message);
    buttons.forEach(x=>{x.disabled=false;x.textContent='🔄 Rebuild Phase 3 / QA'});
  }
}
function activeCard(a){if(!a)return '<div class="empty">No active batch.</div>';const id=a.batch_id||a.id||'—',status=a.processing_status||a.status||'PROCESSING';return `<div class="batch"><div class="batchtop"><div><div class="batchid">Batch #${esc(id)}</div><div class="meta">${esc(a.batch_label||'Active upload')}</div></div>${pill(status)}</div><div class="batchmeta"><div><small>Files</small><b>${fmt(a.file_count,0)}</b></div><div><small>Started</small><b>${esc(a.upload_started_at||'—')}</b></div><div><small>Status</small><b>${esc(status)}</b></div></div></div>`}
async function loadBatches(){try{const [a,r]=await Promise.all([api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=20')]);state.active=a.active_batch||null;state.recent=r.batches||[];const activeEl=$('#activeBatch');if(activeEl){activeEl.innerHTML=activeCard(state.active)+resumeActionHtml(state.active,true);wireRecoveryButtons(activeEl)}const overviewActive=$('#dbOverviewActive');if(overviewActive){overviewActive.innerHTML=activeCard(state.active)+resumeActionHtml(state.active,true);wireRecoveryButtons(overviewActive)}const batchRows=$('#batchRows');if(batchRows){batchRows.innerHTML=state.recent.map(b=>`<tr class="batchrow" data-id="${esc(b.batch_id)}"><td><b>#${esc(b.batch_id)}</b><div class="meta">${esc(b.batch_label||'')}</div></td><td>${pill(b.processing_status)}</td><td>${fmt(b.file_count,0)}</td><td>${esc(b.upload_started_at||'—')}</td><td>${esc(b.completed_at||'—')}</td><td>${pill(b.phase3_status||'—')}</td><td>${fmt(b.quick_check_ready_rows,0)} / ${fmt(b.quick_check_hold_rows,0)}</td></tr>`).join('')||'<tr><td colspan="7" class="empty">No recent completed batches.</td></tr>';$$('.batchrow').forEach(x=>x.onclick=()=>openBatchDetail(x.dataset.id))}const latest=state.recent[0]||null;const latestEl=$('#dbLatestBatch');if(latestEl){latestEl.innerHTML=latest?(activeCard({...latest,status:latest.processing_status||latest.phase3_status,batch_label:latest.batch_label||'Latest completed'})+rebuildActionHtml(latest,true)):'<div class="empty">No completed batch history.</div>';wireRecoveryButtons(latestEl)}const ps=$('#dbProcessingSummary');if(ps)ps.textContent=state.active?`Batch #${state.active.batch_id||'—'} is processing`:(latest?`Latest #${latest.batch_id} · ${latest.phase3_status||latest.processing_status||'complete'}`:'No active batch')}catch(e){const be=$('#batchError');if(be)be.innerHTML=`<div class="error">${esc(e.message)}</div>`;const oe=$('#dbOverviewError');if(oe)oe.innerHTML=`<div class="error">${esc(e.message)}</div>`}}
function openBatchDetail(id){
  const b=state.recent.find(x=>String(x.batch_id)===String(id));if(!b)return;
  const files=b.files||[],q=b.qa_summary||{},eligible=batchRebuildEligible(b);
  const foot=eligible
    ? `<span class="meta" style="margin-right:auto">Uses current OH / UOM / cost / identity / QA rules. RAW is not re-uploaded.</span><button id="rebuildPhase3Btn" class="btn primary">🔄 Rebuild Phase 3 / QA</button>`
    : `<span class="pill blue">READ ONLY</span>`;
  openDrawer(
    `Batch #${b.batch_id}`,
    `${b.processing_status||''} · ${b.phase3_status||''}`,
    `<div class="detailgrid"><div class="detail"><small>Files</small><b>${fmt(b.file_count,0)}</b></div><div class="detail"><small>Rows</small><b>${fmt(b.source_row_count,0)}</b></div><div class="detail"><small>Errors</small><b>${fmt(b.error_count,0)}</b></div><div class="detail"><small>Completed</small><b>${esc(b.completed_at||'—')}</b></div><div class="detail"><small>QC Ready</small><b>${fmt(b.quick_check_ready_rows,0)}</b></div><div class="detail"><small>QC Hold</small><b>${fmt(b.quick_check_hold_rows,0)}</b></div></div><div class="sectiontitle">ChatGPT Analysis Bridge</div><div id="batchBridgeStatus"><div class="meta">Checking bridge status…</div></div><div class="sectiontitle">Source Files</div><div class="reasonlist">${files.map(f=>`<div class="reason"><span class="rdot"></span><div><b>${esc(f.original_filename||'')}</b><span>${esc(f.source_type||'Unknown')} · ${esc(f.processing_status||'')}</span></div></div>`).join('')||'<span class="meta">No file detail.</span>'}</div>${q.phase3?`<div class="sectiontitle">QA</div><div class="calc">${esc(q.phase3.result_status||'')} · blockers ${fmt(q.phase3.blocking_issue_count,0)} · hold rows ${fmt(q.phase3.quick_check_hold_rows,0)}</div>`:''}${eligible?'<div class="calc" style="margin-top:10px"><b>Rebuild available.</b> Re-runs Phase 3 / QA only; the previous Quick Check snapshot stays live until commit.</div>':''}`,
    foot
  );
  const rb=$('#rebuildPhase3Btn');if(rb)rb.onclick=()=>rebuildPhase3(b.batch_id);
  loadChatgptBridgeStatus(b.batch_id);
}
$('#refreshBatch').onclick=loadBatches;

$('#uploadBtn').onclick=async()=>{const files=[...$('#uploadFiles').files];if(!files.length){toast('Select files first');return}const btn=$('#uploadBtn');btn.disabled=true;$('#uploadResult').innerHTML='<span class="meta">Creating batch...</span>';try{const label=($('#uploadNote').value||'').trim()||`Web direct upload ${new Date().toLocaleString()}`;const created=await api('/v1/web-upload/batches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label})});if(created.created===false){$('#uploadResult').innerHTML='<b>Upload not started</b><div class="meta">A batch is already active. Wait for it to finish before uploading another batch.</div>';toast('Active batch already processing');showDbTab('dboverview');await loadBatches();return}const session=created.session_id||created.batch_key||created.session?.session_id;if(!session)throw new Error('Upload batch session ID was not returned');const uploaded=[];for(let i=0;i<files.length;i++){const fd=new FormData();fd.append('file',files[i]);$('#uploadResult').innerHTML=`<span class="meta">Uploading ${i+1}/${files.length}: ${esc(files[i].name)}</span>`;const u=await api(`/v1/web-upload/batches/${encodeURIComponent(session)}/files`,{method:'POST',body:fd});uploaded.push(u)}$('#uploadResult').innerHTML='<span class="meta">Committing batch and starting processing...</span>';const commit=await api(`/v1/web-upload/batches/${encodeURIComponent(session)}/commit`,{method:'POST'});$('#uploadResult').innerHTML=`<b>Upload accepted</b><div class="meta">${files.length} file(s) · processing started</div><div class="filelist">${files.map(f=>`<div class="filerow"><span>${esc(f.name)}</span><span>${fmt(f.size/1024/1024,2)} MB</span></div>`).join('')}</div>`;$('#uploadFiles').value='';$('#uploadNote').value='';toast('Upload complete; batch processing started');showDbTab('dboverview');await loadBatches()}catch(e){$('#uploadResult').innerHTML=`<div class="error" style="margin:-9px">${esc(e.message)}</div>`;toast(e.message)}finally{btn.disabled=false}};

async function loadData(){
  const err=$('#dataHealthError');if(err)err.innerHTML='';
  try{
    const d=await api('/v1/backoffice/data-health?days=14');
    state.dataHealth=d;
    const latest=d.latest||{};
    const sourceKeys=['POS','MVT','PRICE','OH','LIVE_FRESH','FROZEN'];
    const labels={POS:'POS',MVT:'MVT',PRICE:'Price',OH:'OH',LIVE_FRESH:'Live / Fresh',FROZEN:'Frozen'};
    $('#dataGrid').innerHTML=sourceKeys.map(k=>{
      const x=latest[k]||{};
      return '<div class="kpi"><small>'+esc(labels[k])+'</small><b>'+esc(x.date||'—')+'</b><span>'+esc(x.file||'No recent source')+'</span></div>';
    }).join('');
    const stateTag=x=>{
      const s=String(x?.status||'NONE').toUpperCase();
      if(s==='OK')return '<span class="pill green">OK</span>';
      if(s==='MISSING')return '<span class="pill red">MISS</span>';
      if(s==='NOT_DUE')return '<span class="pill blue">NOT DUE</span>';
      return '<span class="pill blue">—</span>';
    };
    const overallTag=s=>{
      const v=String(s||'').toUpperCase();
      if(v==='COMPLETE')return '<span class="pill green">COMPLETE</span>';
      if(v==='MISSING')return '<span class="pill red">MISSING</span>';
      return '<span class="pill blue">CURRENT DAY</span>';
    };
    $('#dataHealthRows').innerHTML=(d.rows||[]).map(r=>{
      const s=r.sources||{};
      return '<tr class="data-health-row" data-date="'+esc(r.date)+'">'+
        '<td><b>'+esc(r.date)+'</b><div class="meta">'+esc(r.weekday||'')+'</div></td>'+
        '<td>'+overallTag(r.overall_status)+'</td>'+
        '<td>'+stateTag(s.POS)+'</td>'+
        '<td>'+stateTag(s.MVT)+'</td>'+
        '<td>'+stateTag(s.PRICE)+'</td>'+
        '<td>'+stateTag(s.OH)+'</td>'+
        '<td>'+stateTag(s.LIVE_FRESH)+'</td>'+
        '<td>'+stateTag(s.FROZEN)+'</td>'+
        '<td><button class="btn small data-health-detail" data-date="'+esc(r.date)+'">Details</button></td>'+
      '</tr>';
    }).join('')||'<tr><td colspan="9" class="empty">No Data Health rows.</td></tr>';
    $$('.data-health-detail').forEach(b=>b.onclick=e=>{e.stopPropagation();openDataHealthDetail(b.dataset.date)});
    $$('.data-health-row').forEach(tr=>tr.onclick=()=>openDataHealthDetail(tr.dataset.date));
  }catch(e){
    if(err)err.innerHTML='<div class="error">'+esc(e.message)+'</div>';
    $('#dataHealthRows').innerHTML='<tr><td colspan="9" class="empty">Unable to load Data Health.</td></tr>';
  }
}
function openDataHealthDetail(dateKey){
  const data=state.dataHealth||{},r=(data.rows||[]).find(x=>String(x.date)===String(dateKey));if(!r)return;
  const names={POS:'POS',MVT:'MVT',PRICE:'Price List',OH:'OH',LIVE_FRESH:'Live / Fresh',FROZEN:'Frozen'};
  const blocks=Object.keys(names).map(k=>{
    const x=(r.sources||{})[k]||{};
    const requirement=(k==='POS'||k==='MVT')?'Daily required':'Snapshot source';
    return '<div class="reason"><span class="rdot"></span><div><b>'+esc(names[k])+' · '+esc(x.status||'NONE')+'</b><span>'+
      esc(requirement)+' · '+esc(x.file||'No source')+(x.batch_id?' · Batch #'+esc(x.batch_id):'')+
    '</span></div></div>';
  }).join('');
  openDrawer('Data Health · '+r.date,(r.weekday||'')+' · '+(r.overall_status||''),'<div class="reasonlist">'+blocks+'</div>','<span class="pill blue">READ ONLY</span>');
}
$('#refreshData').onclick=loadData;
$('#dbRefreshAll').onclick=()=>{loadDatabaseOverview();loadBatches();};

$('#searchForm').onsubmit=e=>{e.preventDefault();state.inventorySearch=$('#searchInput').value.trim();state.invCat='ALL';$$('.invfilter').forEach(x=>x.classList.toggle('on',x.dataset.cat==='ALL'));show('inventory')};
async function boot(){await loadHealth().catch(()=>{});if(isMobileBackoffice())showMobileHome({scroll:false});else restoreRoute({replaceMissing:true});setInterval(()=>{if(!document.hidden&&!isMobileBackoffice()&&$('#database').classList.contains('on')){const current=$('#database .subview.on');if(current?.id==='dboverview'){loadDatabaseOverview();loadBatches()}}},15000)}boot();
})();
</script>
</body></html>'''
