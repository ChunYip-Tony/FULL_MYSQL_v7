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
.tablewrap{overflow:auto}.table{width:100%;min-width:980px;border-collapse:collapse;font-size:12px}.table th,.table td{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}.table th{background:#f7faf9;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.035em}.table tbody tr:hover td{background:#fbfdfc}.table tbody tr.velocity-active td{background:#f2fbf8}.table tbody tr.velocity-active:hover td{background:#e8f7f2}.table tbody tr.velocity-active td:first-child{box-shadow:inset 3px 0 0 #6aaea4}.name{font-weight:800;font-size:13px}.meta{font-size:10px;color:var(--muted);margin-top:2px}.num{font-variant-numeric:tabular-nums}.linkbtn{border:0;background:transparent;padding:2px 0;text-decoration:underline;text-decoration-style:dotted;text-underline-offset:3px;font-weight:850}.suggest{font-weight:900;color:var(--sea);font-size:11px}.pair249{margin-top:5px;padding:5px 7px;border-radius:8px;background:#fff4df;color:#8a5c00;font-size:9px;font-weight:900;line-height:1.35}.pair249.mismatch{background:#ffe7e2;color:#a53a2c}.empty{padding:28px;text-align:center;color:var(--muted);font-size:10px}.loading{padding:22px;color:var(--muted);font-size:10px}.error{padding:10px 12px;background:var(--redbg);color:var(--red);font-size:10px;border-bottom:1px solid #f0cac4}
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
  .m-module .ico{display:block;font-size:23px;line-height:1}.m-module b{display:block;font-size:15px;line-height:1.18;margin-top:10px}.m-module .m-desc{display:block;font-size:10px;line-height:1.35;color:var(--muted);margin-top:5px}
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
  .m-module .ico{font-size:21px}.m-module b{font-size:14px;margin-top:8px}.m-module .m-desc{font-size:9px;margin-top:4px}
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
  .m-module .m-desc{font-size:10px}
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

  /* Approved mobile home: 2 columns × 3 rows */
  .m-modgrid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:15px}
  .m-module{
    min-height:176px;
    border-radius:20px;
    padding:15px 14px 18px;
    display:flex;
    flex-direction:column;
    align-items:flex-start;
    justify-content:flex-start;
  }
  .m-module .ico{
    position:static;
    width:50px;height:50px;border-radius:16px;
    display:grid;place-items:center;
    font-size:23px;
    margin:0 0 16px;
  }
  .m-module:after{
    right:12px;top:12px;transform:none;
    width:28px;height:28px;font-size:20px
  }
  .m-module:before{
    content:"";position:absolute;left:0;right:0;bottom:0;height:16px;
    border-radius:0 0 20px 20px;background:linear-gradient(90deg,rgba(22,121,133,.08),rgba(44,160,168,.16))
  }
  .m-module:nth-child(1):before{background:linear-gradient(90deg,#eaf5ff,#dceeff)}
  .m-module:nth-child(2):before{background:linear-gradient(90deg,#fff0f0,#ffe0e2)}
  .m-module:nth-child(3):before{background:linear-gradient(90deg,#eef9ec,#dcf4dc)}
  .m-module:nth-child(4):before{background:linear-gradient(90deg,#fff6e8,#ffebc9)}
  .m-module:nth-child(5):before{background:linear-gradient(90deg,#f3efff,#e7ddff)}
  .m-module:nth-child(6):before{background:linear-gradient(90deg,#e9fbfa,#d2f4f1)}
  .m-module b{
    font-size:17px;line-height:1.18;margin:0;
    padding-right:25px;letter-spacing:-.02em
  }
  .m-module .m-desc{
    font-size:11px;line-height:1.42;margin-top:8px;padding:0 5px 0 0;
    display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden
  }
  .m-module-meta{font-size:10px!important;margin-top:8px!important;padding:0!important;background:transparent!important}

  .m-pagehead{padding-bottom:13px;margin-bottom:13px}
  .m-back{width:48px;height:48px;min-width:48px;font-size:22px}
  .m-pagetitle{font-size:22px}.m-pagesub{font-size:11px;max-width:315px;margin-top:4px}

  .m-chipbar{gap:8px;padding-bottom:12px}
  .m-chip{min-height:42px;padding:8px 14px;font-size:11px}
  .m-quicktools{display:none;gap:8px;margin-bottom:12px;padding:12px;background:#fff;border-radius:17px;box-shadow:0 8px 22px rgba(9,49,54,.06)}
  .m-quicktools.on{display:grid}
  .m-quickrow{display:grid;grid-template-columns:minmax(0,1fr) 82px;gap:8px}
  .m-quicktools input{min-width:0;min-height:50px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:16px;background:#fff}
  .m-quicktools .btn{min-height:50px;border-radius:12px}
  .m-qatools{grid-template-columns:1fr;gap:8px;margin-bottom:12px}
  .m-qatools input,.m-qatools select{min-height:48px;font-size:14px;padding:10px 12px}.m-qatools input{font-size:17px}
  .m-perftools{display:none;gap:10px;margin:0 0 13px;padding:13px;background:#fff;border-radius:17px;box-shadow:0 8px 22px rgba(9,49,54,.06)}
  .m-perftools.on{display:grid}.m-perftools label{display:grid;gap:5px;font-size:10px;font-weight:900;color:var(--muted)}
  .m-perftools select{width:100%;min-width:0;min-height:48px;border:1px solid var(--line);border-radius:12px;background:#fff;padding:9px 10px;font-size:14px}
  .m-perf-dates{display:grid;grid-template-columns:1fr 1fr;gap:9px}.m-perftools .btn{min-height:50px;border-radius:12px}
  .m-perftools.working{box-shadow:0 0 0 2px rgba(22,121,133,.15),0 8px 22px rgba(9,49,54,.06)}
  .m-perftools.working .btn{opacity:.78}


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


  /* Mobile viewport fit: responsive to the actual visible window */
  .mobilehome,.mobile-listpage,.mobile-detailpage{
    width:100%;max-width:100%;min-width:0;box-sizing:border-box
  }
  .mobilehome.on{min-height:calc(100dvh - env(safe-area-inset-top) - env(safe-area-inset-bottom))}
  .m-topbar,.m-modgrid,.m-module,.m-bottomnav,.m-pagehead,.m-list,.m-row{max-width:100%;min-width:0;box-sizing:border-box}
  .m-modgrid{
    width:100%;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:clamp(8px,2.6vw,12px)
  }
  .m-module{
    width:100%;min-width:0;
    min-height:clamp(148px,42vw,176px);
    padding:clamp(11px,3.4vw,15px) clamp(10px,3.2vw,14px) clamp(16px,4vw,18px)
  }
  .m-module .ico{
    width:clamp(42px,12vw,50px);height:clamp(42px,12vw,50px);
    margin-bottom:clamp(10px,3vw,16px)
  }
  .m-module b{font-size:clamp(14px,4.1vw,17px)}
  .m-module .m-desc{font-size:clamp(9px,2.7vw,11px);overflow-wrap:anywhere}
  .m-brand strong{font-size:clamp(20px,6vw,24px)}
  .m-brand span{font-size:clamp(9px,2.7vw,11px)}
  .m-bottomnav{width:auto}
  @media(max-width:360px){
    .m-modgrid{gap:8px}
    .m-module{min-height:146px;padding:10px 9px 15px}
    .m-module .ico{width:40px;height:40px;font-size:20px;margin-bottom:9px}
    .m-module:after{right:8px;top:8px;width:25px;height:25px}
    .m-module b{font-size:14px}
    .m-module .m-desc{font-size:9px;line-height:1.32}
    .m-status{padding:5px 8px;font-size:9px}
  }


  /* Home fits the visible mobile window: header + equal 2×3 grid */
  body.mobile-home-active{
    overflow-y:hidden;
  }
  body.mobile-home-active .shell{
    height:100dvh;
    min-height:100dvh;
    max-height:100dvh;
    padding-top:max(8px,env(safe-area-inset-top));
    padding-bottom:max(24px,calc(env(safe-area-inset-bottom) + 14px));
    box-sizing:border-box;
    overflow:hidden;
  }
  .mobilehome.on{
    height:100%;
    min-height:0;
    display:flex;
    flex-direction:column;
    overflow:hidden;
  }
  .mobilehome.on .m-topbar{
    flex:0 0 auto;
    margin-bottom:clamp(6px,1.4dvh,12px);
  }
  .mobilehome.on .m-modgrid{
    flex:1 1 auto;
    min-height:0;
    margin-top:clamp(6px,1.3dvh,12px);
    grid-template-columns:repeat(2,minmax(0,1fr));
    grid-template-rows:repeat(3,minmax(0,1fr));
    gap:clamp(7px,1.25dvh,12px);
  }
  .mobilehome.on .m-module{
    height:100%;
    min-height:0;
    padding:
      clamp(9px,1.6dvh,15px)
      clamp(9px,2.8vw,14px)
      clamp(13px,1.8dvh,18px);
  }
  .mobilehome.on .m-module .ico{
    width:clamp(38px,5.4dvh,50px);
    height:clamp(38px,5.4dvh,50px);
    font-size:clamp(19px,2.8dvh,23px);
    margin-bottom:clamp(7px,1.25dvh,14px);
  }
  .mobilehome.on .m-module b{
    font-size:clamp(13px,2.05dvh,17px);
  }
  .mobilehome.on .m-module .m-desc{
    font-size:clamp(8px,1.35dvh,11px);
    line-height:1.3;
    margin-top:clamp(4px,.8dvh,8px);
    -webkit-line-clamp:2;
  }
  @media(max-height:700px) and (max-width:759px){
    .mobilehome.on .m-topbar{margin-bottom:4px}
    .mobilehome.on .m-brand span{display:none}
    .mobilehome.on .m-modgrid{margin-top:4px;gap:7px}
    .mobilehome.on .m-module{padding:8px 9px 12px}
    .mobilehome.on .m-module .ico{width:36px;height:36px;font-size:18px;margin-bottom:6px}
    .mobilehome.on .m-module b{font-size:13px}
    .mobilehome.on .m-module .m-desc{font-size:8px;margin-top:3px}
  }

  /* Final Home polish: stronger header and vertically balanced cards */
  body.mobile-home-active{
    background:
      radial-gradient(circle at 18% -8%,rgba(46,166,176,.18),transparent 30%),
      linear-gradient(180deg,#edf8f7 0%,#f7faf9 44%,#f3f6f5 100%);
  }
  .mobilehome.on:before{
    z-index:0!important;
    height:clamp(116px,16dvh,154px)!important;
    background:
      radial-gradient(circle at 84% 0%,rgba(59,181,192,.35),transparent 38%),
      linear-gradient(145deg,#08363d 0%,#0c5963 55%,#117783 100%)!important;
    box-shadow:0 18px 38px rgba(7,48,55,.18)!important;
  }
  .mobilehome.on .m-topbar{
    position:relative;
    z-index:2;
    color:#fff;
    padding:clamp(7px,1.2dvh,11px) 7px clamp(9px,1.4dvh,13px);
  }
  .mobilehome.on .m-brand strong{
    color:#fff;
    text-shadow:0 1px 1px rgba(0,0,0,.08);
    letter-spacing:-.045em;
  }
  .mobilehome.on .m-brand span{color:rgba(255,255,255,.76)}
  .mobilehome.on .m-status{
    background:rgba(255,255,255,.14)!important;
    border:1px solid rgba(255,255,255,.24)!important;
    color:#fff!important;
    box-shadow:0 6px 18px rgba(0,0,0,.08)!important;
  }
  .mobilehome.on .m-modgrid{
    position:relative;
    z-index:2;
  }
  .mobilehome.on .m-module{
    justify-content:center;
    background:linear-gradient(180deg,#ffffff 0%,#fcfdfd 100%);
    border:1px solid rgba(219,230,226,.72);
    border-radius:22px;
    box-shadow:
      0 12px 28px rgba(10,56,61,.085),
      0 2px 6px rgba(10,56,61,.035);
    transition:transform .12s ease,box-shadow .12s ease;
  }
  .mobilehome.on .m-module:active{
    transform:scale(.975);
    box-shadow:0 7px 18px rgba(10,56,61,.08);
  }
  .mobilehome.on .m-module:after{
    background:#f2f8f7;
    color:#277d84;
    box-shadow:inset 0 0 0 1px #e3eeec;
  }
  .mobilehome.on .m-module .ico{
    flex:0 0 auto;
    box-shadow:inset 0 0 0 1px rgba(255,255,255,.55);
  }
  .mobilehome.on .m-module:nth-child(1) .ico{background:#e1f1ff;color:#126fd1}
  .mobilehome.on .m-module:nth-child(2) .ico{background:#fff0d9;color:#0e9f69}
  .mobilehome.on .m-module:nth-child(3) .ico{background:#e8f7e8;color:#1ba95b}
  .mobilehome.on .m-module:nth-child(4) .ico{background:#fff0dc;color:#e48616}
  .mobilehome.on .m-module:nth-child(5) .ico{background:#eee8ff;color:#6343cf}
  .mobilehome.on .m-module:nth-child(6) .ico{background:#e4f8f6;color:#12979a}
  .mobilehome.on .m-module b{
    color:#123c41;
    font-weight:950;
    letter-spacing:-.025em;
  }
  .mobilehome.on .m-module .m-desc{
    color:#6a7f80;
    font-weight:650;
  }
  .mobilehome.on .m-module:before{
    height:10px;
    opacity:.95;
  }
  @media(max-height:700px) and (max-width:759px){
    .mobilehome.on:before{height:104px!important}
    .mobilehome.on .m-module{border-radius:18px}
  }

  /* Seafood Market Home theme */
  body.mobile-home-active{
    background:
      linear-gradient(30deg,rgba(19,118,128,.025) 12%,transparent 12.5%,transparent 87%,rgba(19,118,128,.025) 87.5%,rgba(19,118,128,.025)),
      linear-gradient(150deg,rgba(19,118,128,.025) 12%,transparent 12.5%,transparent 87%,rgba(19,118,128,.025) 87.5%,rgba(19,118,128,.025)),
      linear-gradient(30deg,rgba(19,118,128,.025) 12%,transparent 12.5%,transparent 87%,rgba(19,118,128,.025) 87.5%,rgba(19,118,128,.025)),
      linear-gradient(180deg,#eaf7f7 0%,#f8fbfb 39%,#f2f7f6 100%)!important;
    background-size:28px 49px,28px 49px,28px 49px,auto!important;
    background-position:0 0,0 0,14px 24px,0 0!important;
  }
  .mobilehome.on:before{
    height:clamp(122px,16.5dvh,158px)!important;
    border-radius:0 0 34px 34px!important;
    background:
      radial-gradient(ellipse at 18% -12%,rgba(134,235,232,.28) 0%,transparent 42%),
      radial-gradient(ellipse at 92% 4%,rgba(47,173,188,.34) 0%,transparent 38%),
      linear-gradient(145deg,#052f38 0%,#07515e 48%,#0a7480 100%)!important;
    box-shadow:0 18px 38px rgba(4,48,57,.20)!important;
  }
  .mobilehome.on:after{
    content:"";
    position:absolute;
    left:-4%;
    right:-4%;
    top:clamp(94px,12.8dvh,122px);
    height:32px;
    z-index:1;
    pointer-events:none;
    opacity:.55;
    background:
      radial-gradient(ellipse at 18% 100%,rgba(255,255,255,.18) 0 43%,transparent 45%),
      radial-gradient(ellipse at 52% 100%,rgba(255,255,255,.12) 0 45%,transparent 47%),
      radial-gradient(ellipse at 84% 100%,rgba(255,255,255,.15) 0 42%,transparent 44%);
  }
  .mobilehome.on .m-topbar{
    padding-left:8px;
    padding-right:8px;
  }
  .mobilehome.on .m-brand strong{
    font-weight:950;
    letter-spacing:-.05em;
  }
  .mobilehome.on .m-brand span{
    display:inline-flex;
    align-items:center;
    width:max-content;
    margin-top:6px;
    padding:4px 8px;
    border:1px solid rgba(200,246,242,.20);
    border-radius:999px;
    background:rgba(255,255,255,.10);
    color:#d7f7f4;
    font-weight:800;
    letter-spacing:.04em;
    backdrop-filter:blur(6px);
  }
  .mobilehome.on .m-status{
    min-height:32px;
    background:rgba(255,255,255,.13)!important;
    border-color:rgba(255,255,255,.24)!important;
    box-shadow:0 6px 18px rgba(0,0,0,.08)!important;
    backdrop-filter:blur(8px);
  }
  .mobilehome.on .m-status.good:before{
    box-shadow:0 0 0 4px rgba(131,239,184,.10),0 0 10px rgba(131,239,184,.35);
    border-radius:50%;
  }

  .mobilehome.on .m-module{
    --market-accent:#167f8b;
    --market-soft:#e9f7f7;
    --market-line:#d5eaea;
    justify-content:center;
    overflow:hidden;
    background:
      radial-gradient(circle at 96% 2%,var(--market-soft) 0%,transparent 33%),
      linear-gradient(180deg,#ffffff 0%,#fcfefe 100%)!important;
    border:1px solid var(--market-line)!important;
    border-radius:21px!important;
    box-shadow:
      0 12px 28px rgba(5,59,67,.085),
      0 2px 5px rgba(5,59,67,.035),
      inset 0 1px 0 rgba(255,255,255,.95)!important;
  }
  .mobilehome.on .m-module:nth-child(1){--market-accent:#1677c8;--market-soft:#e8f4ff;--market-line:#d8e8f4}
  .mobilehome.on .m-module:nth-child(2){--market-accent:#df5b55;--market-soft:#fff0ee;--market-line:#f2deda}
  .mobilehome.on .m-module:nth-child(3){--market-accent:#20a36a;--market-soft:#e9f8ef;--market-line:#d8eddf}
  .mobilehome.on .m-module:nth-child(4){--market-accent:#df8a28;--market-soft:#fff4e5;--market-line:#f0e2cc}
  .mobilehome.on .m-module:nth-child(5){--market-accent:#6550c7;--market-soft:#f0ecff;--market-line:#e2dcf6}
  .mobilehome.on .m-module:nth-child(6){--market-accent:#118f94;--market-soft:#e5f8f7;--market-line:#d3ecea}

  .mobilehome.on .m-module .ico{
    background:var(--market-soft)!important;
    color:var(--market-accent)!important;
    border:1px solid var(--market-line);
    box-shadow:
      0 7px 16px rgba(12,89,98,.08),
      inset 0 1px 0 rgba(255,255,255,.9)!important;
  }
  .mobilehome.on .m-module:after{
    color:var(--market-accent)!important;
    background:rgba(255,255,255,.78)!important;
    border:1px solid var(--market-line);
    box-shadow:0 3px 9px rgba(8,70,78,.06)!important;
  }
  .mobilehome.on .m-module:before{
    height:14px!important;
    opacity:1!important;
    border-radius:55% 55% 18px 18px / 100% 100% 18px 18px!important;
    background:
      repeating-linear-gradient(
        115deg,
        var(--market-soft) 0 12px,
        #ffffff 12px 20px,
        var(--market-soft) 20px 32px
      )!important;
    border-top:1px solid var(--market-line);
  }
  .mobilehome.on .m-module b{
    color:#123c42!important;
    font-weight:950!important;
    letter-spacing:-.025em!important;
  }
  .mobilehome.on .m-module .m-desc{
    color:#6b7f81!important;
    font-weight:650!important;
  }
  .mobilehome.on .m-module:active{
    transform:scale(.975);
    box-shadow:0 7px 18px rgba(5,59,67,.08)!important;
  }
  @media(max-height:700px) and (max-width:759px){
    .mobilehome.on:before{height:106px!important}
    .mobilehome.on:after{top:78px;height:26px}
    .mobilehome.on .m-brand span{display:none}
  }


  /* Larger Home typography while preserving 2×3 viewport fit */
  .mobilehome.on .m-brand strong{
    font-size:clamp(24px,3.25dvh,29px)!important;
    line-height:1!important;
  }
  .mobilehome.on .m-brand span{
    font-size:clamp(10px,1.35dvh,12px)!important;
    line-height:1.15;
  }
  .mobilehome.on .m-status{
    font-size:clamp(10px,1.4dvh,12px)!important;
    font-weight:950!important;
    padding:6px 10px!important;
  }
  .mobilehome.on .m-module b{
    font-size:clamp(15px,2.3dvh,19px)!important;
    line-height:1.12!important;
  }
  .mobilehome.on .m-module .m-desc{
    font-size:clamp(10px,1.55dvh,12px)!important;
    line-height:1.28!important;
    -webkit-line-clamp:2!important;
  }
  @media(max-height:700px) and (max-width:759px){
    .mobilehome.on .m-brand strong{font-size:22px!important}
    .mobilehome.on .m-module b{font-size:15px!important}
    .mobilehome.on .m-module .m-desc{font-size:10px!important}
    .mobilehome.on .m-status{font-size:10px!important}
  }


  /* Mock v2: premium seafood-market display cards */
  .mobilehome.on .m-topbar{
    min-height:clamp(92px,12.5dvh,118px);
    align-items:flex-start;
    overflow:hidden;
  }
  .mobilehome.on .m-brand{position:relative;z-index:3;min-width:0}
  .mobilehome.on .m-market-title{
    padding:0!important;
    margin-top:7px!important;
    border:0!important;
    background:transparent!important;
    backdrop-filter:none!important;
    color:#dff9f6!important;
    font-size:clamp(12px,1.7dvh,15px)!important;
    letter-spacing:.18em!important;
    font-weight:850!important;
  }
  .mobilehome.on .m-storeline{
    display:block;
    margin-top:6px;
    color:rgba(255,255,255,.82);
    font-size:clamp(10px,1.4dvh,12px);
    font-weight:700;
    letter-spacing:.01em;
  }
  .mobilehome.on .m-header-fish{
    position:absolute;
    right:clamp(52px,14vw,72px);
    bottom:-18px;
    z-index:1;
    font-size:clamp(62px,10dvh,88px);
    line-height:1;
    opacity:.30;
    transform:rotate(-4deg);
    filter:saturate(.8) drop-shadow(0 8px 12px rgba(0,0,0,.10));
    pointer-events:none;
  }
  .mobilehome.on .m-status{position:relative;z-index:4}

  .mobilehome.on .m-module{
    justify-content:flex-start!important;
    padding-top:clamp(12px,1.75dvh,17px)!important;
    padding-bottom:clamp(36px,5.8dvh,54px)!important;
    isolation:isolate;
  }
  .mobilehome.on .m-module .ico{
    position:relative;
    z-index:4;
    margin-bottom:clamp(8px,1.25dvh,12px)!important;
  }
  .mobilehome.on .m-module b{
    position:relative;
    z-index:4;
    max-width:88%;
  }
  .mobilehome.on .m-module .m-desc{
    position:relative;
    z-index:4;
    max-width:82%;
    margin-top:clamp(5px,.8dvh,8px)!important;
  }
  .mobilehome.on .m-module:before{
    z-index:1;
    height:clamp(29px,5.2dvh,46px)!important;
    bottom:-2px!important;
    border:0!important;
    border-radius:48% 55% 19px 19px / 48% 46% 19px 19px!important;
    background:
      linear-gradient(135deg,var(--market-accent),color-mix(in srgb,var(--market-accent) 45%,white))!important;
    opacity:.82!important;
    clip-path:polygon(0 46%,18% 61%,39% 46%,62% 65%,81% 45%,100% 57%,100% 100%,0 100%);
  }
  .mobilehome.on .m-module:after{
    z-index:6;
  }
  .mobilehome.on .seafood-art{
    position:absolute;
    right:clamp(8px,2.2vw,13px);
    bottom:clamp(16px,2.5dvh,23px);
    z-index:3;
    display:block;
    font-size:clamp(38px,6.8dvh,62px);
    line-height:1;
    transform:rotate(-6deg);
    filter:drop-shadow(0 8px 9px rgba(8,64,72,.14));
    pointer-events:none;
  }
  .mobilehome.on .m-module:nth-child(even) .seafood-art{transform:rotate(5deg)}
  .mobilehome.on .m-module:nth-child(1) .seafood-art{font-size:clamp(42px,7.4dvh,68px)}
  .mobilehome.on .m-module:nth-child(2) .seafood-art{font-size:clamp(40px,7.1dvh,65px)}
  .mobilehome.on .m-module:nth-child(4) .seafood-art{font-size:clamp(43px,7.5dvh,70px)}
  .mobilehome.on .m-module:nth-child(5) .seafood-art{font-size:clamp(39px,6.9dvh,64px)}
  .mobilehome.on .m-module:nth-child(6) .seafood-art{font-size:clamp(40px,7dvh,66px)}

  @media(max-height:700px) and (max-width:759px){
    .mobilehome.on .m-topbar{min-height:72px}
    .mobilehome.on .m-storeline{font-size:9px;margin-top:3px}
    .mobilehome.on .m-market-title{font-size:10px!important;margin-top:4px!important}
    .mobilehome.on .m-header-fish{font-size:48px;right:50px;bottom:-12px}
    .mobilehome.on .m-module{
      padding-top:8px!important;
      padding-bottom:29px!important;
    }
    .mobilehome.on .seafood-art{
      font-size:34px!important;
      bottom:11px;
    }
    .mobilehome.on .m-module:before{height:26px!important}
  }


  /* Keep deployed Web App version on one line */
  .mobilehome.on .m-brand{
    max-width:calc(100% - 96px);
  }
  .mobilehome.on .m-brand strong{
    display:block;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    font-size:clamp(18px,5.2vw,24px)!important;
    letter-spacing:-.035em!important;
  }
  @media(max-width:380px){
    .mobilehome.on .m-brand strong{
      font-size:17px!important;
    }
  }


  /* Keep deployed Web App version on one line */
  .mobilehome.on .m-version-title{
    display:block;
    white-space:nowrap;
    font-size:clamp(16px,4.7vw,24px)!important;
    line-height:1!important;
    letter-spacing:-.035em!important;
    max-width:calc(100vw - 112px);
  }
  @media(max-width:380px){
    .mobilehome.on .m-version-title{
      font-size:15px!important;
      letter-spacing:-.045em!important;
    }
  }

  /* Non-home mobile navigation: always pinned to the viewing-window bottom */
  .mobile-listpage.on,.mobile-detailpage.on{
    padding-bottom:calc(82px + env(safe-area-inset-bottom));
  }
  .mobile-listpage .m-bottomnav,
  .mobile-detailpage .m-bottomnav{
    position:fixed!important;
    left:50%;
    right:auto;
    bottom:0;
    transform:translateX(-50%);
    z-index:60;
    width:min(520px,100vw)!important;
    max-width:520px!important;
    margin:0!important;
    padding:7px 8px calc(7px + env(safe-area-inset-bottom))!important;
    border-top:1px solid rgba(219,230,226,.95);
    border-radius:18px 18px 0 0;
    background:rgba(255,255,255,.97);
    backdrop-filter:blur(14px);
    box-shadow:0 -10px 30px rgba(9,49,54,.12);
  }
  .mobile-listpage .m-bottomnav button,
  .mobile-detailpage .m-bottomnav button{
    min-height:54px;
  }

@media(min-width:760px){.shell{padding:12px 12px 30px}.dbcardgrid{grid-template-columns:repeat(4,minmax(0,1fr))}.dboverviewgrid{grid-template-columns:1fr 1fr}.statusstrip{grid-template-columns:repeat(4,minmax(0,1fr))}.grid{grid-template-columns:repeat(4,minmax(0,1fr))}.detailgrid{grid-template-columns:repeat(4,minmax(0,1fr))}.uploadgrid{grid-template-columns:1fr 1fr}}
@media(max-width:620px){.shell{padding:7px 7px 76px}.appbar{border-radius:13px}.nav button{font-size:10px}.statusstrip{grid-template-columns:1fr 1fr}.table{min-width:0}.panel{border-radius:13px}.searchbar{padding-left:10px;padding-right:10px}}

.m-quick7d{margin-top:12px}
.m-trendcard{margin-top:12px}
.m-chartnote{font-size:10px;color:var(--muted);margin-top:5px}
.m-trendlegend{display:flex;gap:14px;align-items:center;margin:13px 0 5px;font-size:10px;font-weight:850;color:var(--muted)}
.m-trendlegend span{display:flex;align-items:center;gap:5px}.m-trendlegend i{display:inline-block}
.m-trendlegend .bar{width:12px;height:9px;border-radius:3px;background:#86bbb4}
.m-trendlegend .line{width:15px;height:3px;border-radius:99px;background:#1f7180}
.m-trendwrap{overflow:hidden;border:1px solid #e3eeeb;border-radius:14px;background:#fbfdfd;padding:6px 3px 0}
.m-trendwrap svg{display:block;width:100%;height:auto;min-height:205px}
.m-chart-zero{stroke:#d8e5e2;stroke-width:1}.m-chart-bar{fill:#86bbb4;opacity:.86}
.m-chart-line{fill:none;stroke:#1f7180;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
.m-chart-dot{fill:#fff;stroke:#1f7180;stroke-width:4}
.m-chart-date{font-size:14px;fill:#6d7f80;font-weight:800}
.m-chart-gpval{font-size:12px;fill:#47716d;font-weight:900}
.m-chart-priceval{font-size:13px;fill:#0e5963;font-weight:950}
.m-history7{display:grid;gap:7px;margin-top:8px}
.m-history7-row{display:grid;grid-template-columns:1.35fr repeat(4,minmax(0,1fr));gap:6px;align-items:center;padding:9px;border:1px solid #e3ece9;border-radius:12px;background:#f9fbfa}
.m-history7-row>div{min-width:0}.m-history7-row small{display:block;font-size:8px;color:var(--muted);font-weight:850;text-transform:uppercase}
.m-history7-row b{display:block;font-size:11px;line-height:1.2;overflow-wrap:anywhere}.m-history7-date span{display:block;font-size:8px;color:var(--muted);margin-top:2px}
@media(max-width:420px){
  .m-history7-row{grid-template-columns:1.35fr 1fr 1fr;row-gap:8px}
  .m-history7-row>div:nth-child(4),.m-history7-row>div:nth-child(5){grid-column:auto}
  .m-trendwrap{margin-left:-3px;margin-right:-3px}
}

/* Quick Check live-search Receiving Article grouping */
.m-quicktools.on{display:grid!important;grid-template-columns:1fr!important}
.m-quicktools>input{width:100%;min-height:52px;border:1px solid var(--line);border-radius:13px;padding:11px 13px;font-size:17px;background:#fff}
.m-receiving-group{
  --recv-bg:#eef9f2;
  --recv-bg-strong:#e4f5ea;
  --recv-border:#c6e3d0;
  --recv-accent:#4f9468;
  display:grid;
  gap:8px;
  margin-bottom:14px;
  padding:8px;
  border:2px solid var(--recv-border);
  border-radius:19px;
  background:var(--recv-bg);
  box-shadow:0 5px 14px rgba(7,55,62,.045);
}
.m-receiving-group.recv-tone-1{--recv-bg:#edf6ff;--recv-bg-strong:#e1effc;--recv-border:#c8deef;--recv-accent:#4f86b0}
.m-receiving-group.recv-tone-2{--recv-bg:#f5efff;--recv-bg-strong:#ece3fb;--recv-border:#decef1;--recv-accent:#8066ae}
.m-receiving-group.recv-tone-3{--recv-bg:#fff3e9;--recv-bg-strong:#fbe7d7;--recv-border:#edd1bd;--recv-accent:#b9754c}
.m-receiving-group.recv-tone-4{--recv-bg:#ebf9f7;--recv-bg-strong:#ddf1ee;--recv-border:#c4e5e1;--recv-accent:#478f88}
.m-receiving-group.recv-tone-5{--recv-bg:#fff9e7;--recv-bg-strong:#f7edc9;--recv-border:#eadca7;--recv-accent:#9f8435}
.m-receiving-head{
  display:flex;
  justify-content:space-between;
  gap:10px;
  align-items:center;
  padding:12px 13px;
  border:1px solid var(--recv-border);
  border-radius:15px;
  background:var(--recv-bg-strong);
}
.m-receiving-head small,.m-receiving-movement small{display:block;font-size:9px;color:var(--muted);font-weight:900;letter-spacing:.04em}
.m-receiving-head>div:first-child>small{font-size:11px}
.m-receiving-head>div:first-child>b{display:block;font-size:20px;line-height:1.16;margin-top:2px;color:var(--ink)}
.m-receiving-head .recv-map{font-size:9px;color:var(--muted);font-weight:800;margin-top:3px}
.m-receiving-movement{text-align:right;flex:0 0 auto;min-width:112px;padding-left:10px;border-left:1px solid var(--recv-border)}
.m-receiving-movement b{display:block;font-size:15px;margin-top:2px;color:var(--recv-accent)}
.m-receiving-movement small:last-child{margin-top:3px}
.m-receiving-upcs{display:grid;gap:8px;padding-left:2px}
.m-receiving-group .m-row{
  background:color-mix(in srgb,var(--recv-bg) 84%,#fff)!important;
  border-color:var(--recv-border)!important;
  border-left:4px solid var(--recv-accent)!important;
  box-shadow:0 3px 10px rgba(7,55,62,.035)!important;
}
.m-receiving-group .m-pair-subgroup{
  background:color-mix(in srgb,var(--recv-bg-strong) 78%,#fff)!important;
  border-color:var(--recv-border)!important;
}
.m-receiving-group .m-pair-label{color:var(--recv-accent)!important}
.m-receiving-group .m-pair-subgroup .m-row[data-pair-role="MAIN_240"]{border-left-color:var(--recv-accent)!important}
.m-receiving-group .m-pair-subgroup .m-row[data-pair-role="COOK_SERVICE_249"]{border-left-color:color-mix(in srgb,var(--recv-accent) 58%,#c47b1e)!important}

/* Global value hierarchy: operational values must visually outrank provenance */
.m-metric b{font-size:21px!important;font-weight:950!important;line-height:1.08!important}
.m-metric small{font-size:9px!important}
.m-metric span{font-size:10px!important;color:var(--muted)!important;line-height:1.3!important}
.detail b{font-size:15px!important;font-weight:950!important;line-height:1.12!important}
.detail small{font-size:9px!important;color:var(--muted)!important}
.detail span{font-size:10px!important;color:var(--muted)!important}
.kpi b{font-size:17px!important;font-weight:950!important}
.kpi small,.kpi span{font-size:9px!important;color:var(--muted)!important}
.table td>b,.table td>.linkbtn{font-size:14px!important;font-weight:900!important}
.table .meta{font-size:9px!important;line-height:1.3!important;color:var(--muted)!important}
.batchmeta b{font-size:11px!important}.batchmeta small{font-size:8px!important;color:var(--muted)!important}
.dbcard b{font-size:15px!important}.dbcard small,.dbcard em{font-size:9px!important;color:var(--muted)!important}
@media(max-width:759px){
  .m-metric b{font-size:clamp(20px,5.5vw,24px)!important}
  .m-metric small{font-size:9px!important}
  .m-metric span{font-size:10px!important}
  .detail b{font-size:16px!important}
  .detail small{font-size:9px!important}
  .detail span,.meta{font-size:10px!important}
  .m-history7-row b{font-size:12px!important}
  .m-history7-row small,.m-history7-date span{font-size:8px!important}
}

/* Persistent mobile page identity: version remains visible at the top */
@media(max-width:759px){
  .mobile-listpage.on .m-pagehead,
  .mobile-detailpage.on .m-pagehead{
    position:sticky;
    top:0;
    z-index:75;
    margin:0 -9px 10px;
    padding:max(8px,env(safe-area-inset-top)) 9px 8px;
    background:rgba(245,248,247,.96);
    border-bottom:1px solid rgba(210,224,220,.9);
    box-shadow:0 5px 14px rgba(9,49,54,.045);
    backdrop-filter:blur(12px);
    -webkit-backdrop-filter:blur(12px);
  }
  .m-pagecopy{min-width:0;flex:1}
  .m-pageversion{
    flex:0 0 auto;
    display:inline-flex;
    align-items:center;
    min-height:28px;
    max-width:42vw;
    padding:5px 8px;
    border:1px solid #cfe1de;
    border-radius:999px;
    background:#fff;
    color:#37666a;
    font-size:9px;
    line-height:1;
    font-weight:900;
    letter-spacing:-.025em;
    white-space:nowrap;
  }
  @media(max-width:380px){
    .m-pagehead{gap:7px!important}
    .m-pageversion{font-size:8px;padding:5px 6px;max-width:43vw}
    .m-pagetitle{font-size:18px!important}
  }
}

/* Stronger value > source typography hierarchy */
.m-metric b{
  font-size:24px!important;
  font-weight:950!important;
  line-height:1.05!important;
}
.m-metric small{
  font-size:9px!important;
  font-weight:850!important;
}
.m-metric span{
  font-size:9px!important;
  line-height:1.25!important;
  color:var(--muted)!important;
  font-weight:600!important;
}
.detail b{
  font-size:18px!important;
  font-weight:950!important;
  line-height:1.1!important;
}
.detail small{
  font-size:9px!important;
  font-weight:850!important;
  color:var(--muted)!important;
}
.detail span{
  font-size:9px!important;
  line-height:1.25!important;
  color:var(--muted)!important;
}
.kpi b{
  font-size:19px!important;
  font-weight:950!important;
}
.kpi small,.kpi span{
  font-size:9px!important;
  color:var(--muted)!important;
}
.table td>b,.table td>.linkbtn{
  font-size:15px!important;
  font-weight:950!important;
}
.table .meta{
  font-size:9px!important;
  line-height:1.25!important;
  color:var(--muted)!important;
}
.batchmeta b{font-size:13px!important;font-weight:950!important}
.batchmeta small{font-size:8px!important;color:var(--muted)!important}
.dbcard b{font-size:17px!important;font-weight:950!important}
.dbcard small,.dbcard em{font-size:9px!important;color:var(--muted)!important}
.m-history7-row b{font-size:13px!important;font-weight:900!important}
.m-history7-row small,.m-history7-date span{font-size:8px!important;color:var(--muted)!important}

@media(max-width:759px){
  .m-metric b{font-size:clamp(22px,6.2vw,27px)!important}
  .m-metric span{font-size:9px!important}
  .detail b{font-size:18px!important}
  .detail span{font-size:9px!important}
  .m-history7-row b{font-size:13px!important}
}

/* High-contrast sticky mobile page header */
@media(max-width:759px){
  .mobile-listpage.on .m-pagehead,
  .mobile-detailpage.on .m-pagehead{
    background:
      radial-gradient(circle at 88% -25%,rgba(71,190,195,.32),transparent 38%),
      linear-gradient(135deg,#073d46 0%,#0a5c67 58%,#0c737c 100%)!important;
    border-bottom:1px solid rgba(255,255,255,.14)!important;
    box-shadow:0 8px 22px rgba(4,48,57,.18)!important;
    color:#fff!important;
  }
  .mobile-listpage.on .m-pagetitle,
  .mobile-detailpage.on .m-pagetitle{
    color:#fff!important;
    font-size:clamp(23px,6.4vw,29px)!important;
    font-weight:950!important;
    line-height:1.05!important;
    text-shadow:0 1px 1px rgba(0,0,0,.08);
  }
  .mobile-listpage.on .m-pagesub,
  .mobile-detailpage.on .m-pagesub{
    color:rgba(231,250,248,.88)!important;
    font-size:clamp(11px,3vw,13px)!important;
    line-height:1.35!important;
    font-weight:650!important;
    max-width:none!important;
  }
  .mobile-listpage.on .m-back,
  .mobile-detailpage.on .m-back{
    color:#fff!important;
    background:rgba(255,255,255,.12)!important;
    border:1px solid rgba(255,255,255,.18)!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.08)!important;
  }
  .mobile-listpage.on .m-pageversion,
  .mobile-detailpage.on .m-pageversion{
    background:rgba(255,255,255,.96)!important;
    border-color:rgba(255,255,255,.9)!important;
    color:#155b64!important;
    box-shadow:0 3px 10px rgba(0,0,0,.10)!important;
  }
}

/* Performance auto-analysis: no extra Apply button */
.m-perf-status{
  min-height:16px;
  font-size:10px;
  line-height:1.3;
  font-weight:750;
  color:var(--muted);
}
.m-perftools.working .m-perf-status{color:var(--sea)}

/* v7.0.256 Mobile UX refresh */
@media(max-width:759px){
  :root{
    --m-surface:#ffffff;
    --m-surface-soft:#f6faf9;
    --m-ink:#103c41;
    --m-muted:#6b7f80;
    --m-line:#d9e8e5;
    --m-accent:#0d6f79;
    --m-accent-2:#15909a;
    --m-shadow:0 10px 28px rgba(7,55,62,.075);
    --m-shadow-soft:0 5px 16px rgba(7,55,62,.055);
  }

  html{scroll-behavior:smooth;overscroll-behavior-y:contain}
  body{color:var(--m-ink);text-rendering:optimizeLegibility}
  button,.m-row,.m-module,.m-chip{touch-action:manipulation}
  .num,.m-metric b,.detail b,.kpi b,.m-row-code,.m-family-velocity b,.m-history7-row b{
    font-variant-numeric:tabular-nums lining-nums;
  }

  .mobile-listpage.on,.mobile-detailpage.on{
    background:linear-gradient(180deg,#f4f9f8 0,#f8fbfa 34%,#f3f7f6 100%);
  }

  .mobile-listpage.on .m-pagehead,
  .mobile-detailpage.on .m-pagehead{
    min-height:76px;
    padding-left:12px!important;
    padding-right:12px!important;
    border-radius:0 0 18px 18px;
  }
  .mobile-listpage.on .m-pagetitle,
  .mobile-detailpage.on .m-pagetitle{
    letter-spacing:-.035em!important;
  }
  .m-pageversion{
    min-height:30px!important;
    padding:6px 9px!important;
  }

  .m-chipbar{
    gap:8px;
    padding:3px 2px 12px;
    scroll-snap-type:x proximity;
  }
  .m-chip{
    scroll-snap-align:start;
    border-color:var(--m-line);
    font-weight:900;
  }

  .m-quicktools,.m-qatools,.m-perftools{
    border:1px solid rgba(211,229,225,.95);
    box-shadow:var(--m-shadow-soft)!important;
  }
  .m-quicktools>input,
  .m-qatools input,.m-qatools select,
  .m-perftools select{
    border:1px solid #d4e5e1!important;
    background:#fbfdfd!important;
  }
  .m-quicktools>input:focus,
  .m-qatools input:focus,.m-qatools select:focus,
  .m-perftools select:focus{
    background:#fff!important;
    border-color:#72b9b7!important;
    box-shadow:0 0 0 4px rgba(44,160,168,.10);
    outline:none;
  }

  .m-list{gap:10px}
  .m-row{
    position:relative;
    overflow:hidden;
    border:1px solid rgba(214,230,226,.9)!important;
    border-left:4px solid #8dbfba!important;
    background:linear-gradient(180deg,#fff,#fcfefe)!important;
    box-shadow:var(--m-shadow-soft)!important;
  }
  .m-row:after{
    content:"";
    position:absolute;
    inset:0 0 auto 0;
    height:1px;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,.9),transparent);
    pointer-events:none;
  }
  .m-row-code{color:#0b5860!important}
  .m-row-name{color:#193f43}
  .m-row-meta{
    border:1px solid #e4efed;
    background:#f6faf9!important;
  }
  .m-row:focus-visible{
    outline:3px solid rgba(21,144,154,.20);
    outline-offset:2px;
  }

  .m-family-group,.m-receiving-group{
    gap:8px;
    margin-bottom:12px;
    content-visibility:auto;
    contain-intrinsic-size:360px;
  }
  .m-family-head,.m-receiving-head{
    padding:13px 14px;
    border-radius:17px;
    box-shadow:0 5px 14px rgba(7,55,62,.045);
  }
  .m-family-head>div:first-child>small,.m-receiving-head>div:first-child>small{
    font-size:11px!important;
    letter-spacing:.02em;
  }
  .m-family-head>div:first-child>b,.m-receiving-head>div:first-child>b{
    font-size:20px!important;
    letter-spacing:-.025em;
  }
  .m-family-velocity,.m-receiving-movement{
    min-width:96px;
    padding-left:10px;
    border-left:1px solid color-mix(in srgb,var(--family-accent) 28%,transparent);
  }
  .m-family-velocity b,.m-receiving-movement b{font-size:16px!important}
  .m-family-upcs,.m-receiving-upcs{gap:8px;padding-left:7px}

  .m-detailcard{
    border:1px solid rgba(214,230,226,.9)!important;
    background:linear-gradient(180deg,#fff 0%,#fcfefe 100%);
    box-shadow:var(--m-shadow)!important;
  }
  .m-detailgrid{gap:9px}
  .m-metric{
    background:linear-gradient(180deg,#fbfdfc,#f3f8f7)!important;
    border:1px solid #dce9e6!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.9);
  }
  .m-metric small{letter-spacing:.055em!important}
  .m-metric b{color:#0c4b52!important}
  .m-metric span{color:#748687!important}
  .m-detailsection{
    border-top:1px solid #e1ece9!important;
  }
  .m-detailsection h3{
    color:#0b5e66!important;
    letter-spacing:.01em;
  }

  .m-action{
    box-shadow:none;
    transition:transform .08s ease,box-shadow .08s ease,background .08s ease;
  }
  .m-action.primary{
    background:linear-gradient(135deg,var(--m-accent),var(--m-accent-2))!important;
    box-shadow:0 8px 18px rgba(13,111,121,.18)!important;
  }
  .m-action:active{transform:scale(.985)}

  .m-trendwrap{
    border-color:#dce9e6!important;
    background:#fff!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.85);
  }
  .m-history7-row{
    border-color:#deebe8!important;
    background:linear-gradient(180deg,#fbfdfc,#f6faf9)!important;
  }

  .m-bottomnav{
    border:1px solid rgba(213,229,226,.96)!important;
    border-bottom:0!important;
    box-shadow:0 -10px 28px rgba(7,55,62,.13)!important;
  }
  .m-bottomnav button{
    min-height:56px!important;
    font-weight:900!important;
    letter-spacing:.005em;
  }
  .m-bottomnav button.on{
    background:linear-gradient(135deg,#0d6f79,#11838d)!important;
    color:#fff!important;
  }

  .m-row,.m-detailcard,.qa-step{
    content-visibility:auto;
    contain-intrinsic-size:100px;
  }
  .m-detailcard{contain-intrinsic-size:420px}
  .qa-step{contain-intrinsic-size:180px}

  .m-empty,.m-loading,.m-error{
    border-radius:18px;
    box-shadow:var(--m-shadow-soft);
  }

  @media(max-width:380px){
    .m-family-head>div:first-child>b,.m-receiving-head>div:first-child>b{font-size:18px!important}
    .m-family-velocity,.m-receiving-movement{min-width:86px}
    .m-family-velocity b,.m-receiving-movement b{font-size:15px!important}
  }
}

@media(prefers-reduced-motion:reduce){
  html{scroll-behavior:auto!important}
  *,*::before,*::after{
    animation-duration:.01ms!important;
    animation-iteration-count:1!important;
    transition-duration:.01ms!important;
  }
}


/* Canonical 240 / 249 display subgroup */
.m-pair-subgroup{display:grid;gap:6px;padding:7px;border:1px solid var(--unit-border,#c6dfdb);border-radius:15px;background:var(--unit-bg,rgba(232,247,244,.72))}
.m-pair-label{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:3px 5px;font-size:9px;font-weight:950;letter-spacing:.055em;color:#0b6670;text-transform:uppercase}
.m-pair-name{display:flex;align-items:center;gap:5px}
.m-pair-stats{text-align:right;line-height:1.18;text-transform:none;letter-spacing:0}
.m-pair-stats small{display:block;font-size:8px;color:var(--muted);font-weight:900}
.m-pair-stats b{display:block;font-size:13px;color:#0b6670;margin:2px 0}
.m-pair-subgroup .m-row{background:var(--unit-bg,#eef9f7)!important;border-color:var(--unit-border,#c6dfdb)!important}
.m-family-upcs> :nth-child(6n+1){--unit-bg:#eef8ff;--unit-border:#cde4f2}
.m-family-upcs> :nth-child(6n+2){--unit-bg:#f0faee;--unit-border:#d3e9cf}
.m-family-upcs> :nth-child(6n+3){--unit-bg:#f7f2ff;--unit-border:#e1d6f2}
.m-family-upcs> :nth-child(6n+4){--unit-bg:#fff6eb;--unit-border:#f0dec7}
.m-family-upcs> :nth-child(6n+5){--unit-bg:#eefaf8;--unit-border:#cee8e3}
.m-family-upcs> :nth-child(6n+6){--unit-bg:#fff9e9;--unit-border:#eadfb9}
.m-family-upcs> .m-row{background:var(--unit-bg,#fff)!important;border-color:var(--unit-border,#dce8e5)!important}
.m-pair-subgroup .m-row{margin:0!important;box-shadow:none!important;border-left-width:4px!important}
.m-pair-subgroup .m-row[data-pair-role="MAIN_240"]{border-left-color:#167985!important}
.m-pair-subgroup .m-row[data-pair-role="COOK_SERVICE_249"]{border-left-color:#d18b2f!important}
.m-pair-price-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}
.m-pair-price-member{padding:8px;border:1px solid #dce9e6;border-radius:10px;background:#fff}
.m-pair-price-member small{display:block;font-size:8px;font-weight:900;color:var(--muted)}
.m-pair-price-member b{display:block;font-size:13px;margin-top:2px;color:var(--ink)}
.pair-subgroup-head td{background:#eaf6f4!important;color:#0b6670!important;font-size:10px!important;font-weight:950!important;letter-spacing:.04em;text-transform:uppercase;border-top:2px solid #b9d9d4!important}
.pair-subgroup-main td{background:#f7fcfb!important}.pair-subgroup-service td{background:#fffbf3!important}
.pair-inline{margin-top:6px;padding:7px 8px;border:1px solid #c6dfdb;border-radius:9px;background:#eef9f7;font-size:9px;font-weight:850;line-height:1.45;color:#315f62}
.pair-inline b{color:#0b6670}
@media(max-width:759px){.m-pair-subgroup{padding:7px;border-radius:17px}.m-pair-label{font-size:9px}.m-pair-price-grid{grid-template-columns:1fr 1fr}}
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
    <div class="m-brand">
      <strong class="m-version-title">v__VERSION__</strong>
      <span class="m-market-title">SEAFOOD MARKET</span>
      <small class="m-storeline">Store #1032 · Las Vegas</small>
    </div>
    <span class="m-header-fish" aria-hidden="true">🐟</span>
    <span id="mServicePill" class="m-status">Checking…</span>
  </div>
  <div class="m-modgrid">
    <button class="m-module" type="button" data-mobile-module="quick"><span class="ico">🔎</span><b>Quick Check</b><span class="m-desc">Check price, cost and recent sales</span><span class="seafood-art" aria-hidden="true">🐟</span></button>
    <button class="m-module" type="button" data-mobile-module="price"><span class="ico">🏷️</span><b>Price Change</b><span class="m-desc">Review and accept price changes</span><span class="seafood-art" aria-hidden="true">🦐</span></button>
    <button class="m-module" type="button" data-mobile-module="performance"><span class="ico">📊</span><b>Performance</b><span class="m-desc">Analyze sales, velocity and GP$</span><span class="seafood-art" aria-hidden="true">🐚</span></button>
    <button class="m-module" type="button" data-mobile-module="ordering"><span class="ico">🛒</span><b>Ordering</b><span class="m-desc">Review family-level order suggestions</span><span class="seafood-art" aria-hidden="true">🦀</span></button>
    <button class="m-module" type="button" data-mobile-module="inventory"><span class="ico">📦</span><b>Inventory</b><span class="m-desc">View stock, OH and DOS</span><span class="seafood-art" aria-hidden="true">🦪</span></button>
    <button class="m-module" type="button" data-mobile-module="data"><span class="ico">🗄️</span><b>Data</b><span class="m-desc" id="mDataModuleMeta">Uploads, QA, processing and data health</span><span class="seafood-art" aria-hidden="true">🐠</span></button>
  </div>
</section>

<section id="mobileListPage" class="mobile-listpage" aria-label="Mobile Backoffice List">
  <div class="m-pagehead"><button id="mobileListBack" class="m-back" type="button" aria-label="Back to Home">←</button><div class="m-pagecopy"><div id="mobileListTitle" class="m-pagetitle">Backoffice</div><div id="mobileListSub" class="m-pagesub"></div></div><span class="m-pageversion">v__VERSION__</span></div>
  <div id="mobileListChips" class="m-chipbar"></div>
  <div id="mobileQuickTools" class="m-quicktools">
    <input id="mobileQuickSearch" type="search" autocomplete="off" enterkeyhint="search" placeholder="Type UPC / Article / Family / Item">
    <div class="m-hint">Results update automatically · grouped by Family · highest recent velocity first</div>
  </div>
  <div id="mobileQaTools" class="m-qatools"><input id="mobileQaSearch" placeholder="Search UPC / Article / item / reason"><select id="mobileQaSort"><option value="oh_vel_desc">OH ↓, then Velocity ↓</option><option value="vel_oh_desc">Velocity ↓, then OH ↓</option><option value="severity">Severity</option><option value="name">Item A → Z</option><option value="upc">UPC</option></select></div>
  <div id="mobilePerformanceTools" class="m-perftools">
    <div class="m-perf-dates">
      <label><span>Start Date</span><select id="mPerfStart"></select></label>
      <label><span>End Date</span><select id="mPerfEnd"></select></label>
    </div>
    <label><span>Sort By</span><select id="mPerfSort">
      <option value="gp_desc">Highest GP$</option>
      <option value="velocity_desc">Highest Velocity</option>
      <option value="sales_desc">Highest Sales $</option>
      <option value="qty_desc">Highest Qty</option>
      <option value="gp_pct_desc">Highest GP%</option>
      <option value="price_desc">Highest Avg Sold Price</option>
      <option value="name">Item A → Z</option>
    </select></label>
    <div id="mPerfStatus" class="m-perf-status" aria-live="polite"></div>
  </div>
  <div id="mobileListContent" class="m-list"></div>
  <nav class="m-bottomnav" aria-label="Mobile Backoffice navigation">
    <button type="button" data-mobile-home>⌂<br>Home</button><button type="button" data-mobile-module="quick">⌕<br>Quick</button><button type="button" data-mobile-module="price">$<br>Price</button><button type="button" data-mobile-module="data">▦<br>Data</button>
  </nav>
</section>

<section id="mobileDetailPage" class="mobile-detailpage" aria-label="Mobile Backoffice Detail">
  <div class="m-pagehead"><button id="mobileDetailBack" class="m-back" type="button" aria-label="Back to List">←</button><div class="m-pagecopy"><div id="mobileDetailTitle" class="m-pagetitle">Detail</div><div id="mobileDetailSub" class="m-pagesub"></div></div><span class="m-pageversion">v__VERSION__</span></div>
  <div id="mobileDetailContent"></div>
  <nav class="m-bottomnav" aria-label="Mobile Backoffice navigation">
    <button type="button" data-mobile-home>⌂<br>Home</button><button type="button" data-mobile-module="quick">⌕<br>Quick</button><button type="button" data-mobile-module="price">$<br>Price</button><button type="button" data-mobile-module="data">▦<br>Data</button>
  </nav>
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
 <div class="panelhead"><div><div class="title">Performance</div><div class="sub">All Seafood together. Select completed canonical dates, then sort the item-level analysis.</div></div><span class="pill blue">RANGE ANALYSIS</span></div>
 <div class="toolrow">
   <div class="tools">
     <label class="meta">Start Date <select id="salesStartDate" class="select"></select></label>
     <label class="meta">End Date <select id="salesEndDate" class="select"></select></label>
     <select id="salesSort" class="select">
       <option value="gp_desc">Highest GP$</option>
       <option value="velocity_desc">Highest Velocity</option>
       <option value="sales_desc">Highest Sales $</option>
       <option value="qty_desc">Highest Qty</option>
       <option value="gp_pct_desc">Highest GP%</option>
       <option value="price_desc">Highest Avg Sold Price</option>
       <option value="name">Item A → Z</option>
     </select>
     <button id="salesApplyRange" class="btn primary">Analyze Range</button>
     <span id="salesCount" class="pill sea">—</span>
   </div>
 </div>
 <div id="sellKpi" class="grid"></div><div id="sellError"></div>
 <div class="tablewrap"><table class="table"><thead><tr><th>Item</th><th>UPC</th><th>Qty</th><th>Velocity</th><th>Sales</th><th>GP$</th><th>GP%</th><th>Avg Sold Price</th></tr></thead><tbody id="sellRows"></tbody></table></div>
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
const state={invCat:'ALL',inventorySearch:'',invStatus:'ALL',invOH:'ALL',invSales:'ALL',invSort:'vel7_oh_desc',salesStartDate:'',salesEndDate:'',salesSupportedDates:[],salesSort:'gp_desc',salesRows:[],salesRange:null,orderFilter:'ALL',orderHealth:null,priceCat:'ALL',priceStatus:'ALL',priceSort:'opportunity',priceText:'',priceHealth:null,priceLoadError:'',priceMeta:null,qaFilter:'ALL',qaText:'',qaSort:'oh_vel_desc',qaIssues:[],qaHistory:[],inventory:[],orders:[],prices:[],recent:[],active:null,dataHealth:null};
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmt(v,d=1){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):esc(v)}
function money(v){if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?'$'+n.toFixed(2):esc(v)}
// Current Price is live serving evidence; "Report-Day Avg Sold Price" remains a separate historical POS concept.
function pct(v){if(v===null||v===undefined||v==='')return '—';let n=Number(v);if(Math.abs(n)<=1.5)n*=100;return Number.isFinite(n)?n.toFixed(1)+'%':esc(v)}
function pill(status){const s=String(status||'UNKNOWN').toUpperCase();let c='blue';if(s.includes('READY')||s==='PASS'||s==='ACTIVE')c='green';else if(s.includes('FAIL')||s.includes('BLOCK')||s==='OUT')c='red';else if(s.includes('HOLD')||s.includes('PROCESS')||s.includes('QUEUED')||s.includes('WAIT')||s==='WATCH')c='amber';return `<span class="pill ${c}">${esc(s)}</span>`}
function toast(t){const x=$('#toast');x.textContent=t;x.classList.add('on');clearTimeout(toast.t);toast.t=setTimeout(()=>x.classList.remove('on'),2200)}
async function api(url,opts={}){
  const o={...opts};const timeoutMs=Number(o.timeoutMs||0);delete o.timeoutMs;
  let ctl=null,timer=null;
  if(timeoutMs>0&&!o.signal){ctl=new AbortController();o.signal=ctl.signal;timer=setTimeout(()=>ctl.abort(),timeoutMs)}
  try{
    const r=await fetch(url,{cache:'no-store',...o});let data=null;
    try{data=await r.json()}catch{data={detail:await r.text()}}
    if(!r.ok){const d=data?.detail;throw new Error(typeof d==='string'?d:(d?.message||d?.reason||JSON.stringify(d)||`HTTP ${r.status}`))}
    return data
  }catch(e){
    if(e?.name==='AbortError')throw new Error(`Request timed out after ${Math.round(timeoutMs/1000)}s`);
    throw e
  }finally{if(timer)clearTimeout(timer)}
}
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
const mobileState={module:null,parentModule:null,currentDetailKey:null,filter:'all',query:'',freshness:[]};
let mobilePendingTopModule=null;
let mobileQuickSearchTimer=null;
let mobileQuickSearchSeq=0;
let inventoryLoadSeq=0;
const MOBILE_HISTORY_KEY='fullmysql_mobile_v1';
let mobileHistoryReady=false;
let mobileRestoringHistory=false;
let mobileAllowExit=false;

function isMobileBackoffice(){return mobileMedia.matches}
function mNode(id){return document.getElementById(id)}
function mobileHistoryState(screen,extra={}){
  return {[MOBILE_HISTORY_KEY]:true,screen,...extra};
}
function mobilePushHistory(screen,extra={}){
  if(!isMobileBackoffice()||mobileRestoringHistory)return;
  const cur=history.state||{};
  const next=mobileHistoryState(screen,extra);
  if(cur[MOBILE_HISTORY_KEY]&&cur.screen===screen&&String(cur.module||'')===String(next.module||''))return;
  history.pushState(next,'',location.href);
}
function mobileInitHistory(){
  if(!isMobileBackoffice()||mobileHistoryReady)return;
  mobileHistoryReady=true;
  const cur=history.state||{};
  if(cur[MOBILE_HISTORY_KEY])return;
  history.replaceState(mobileHistoryState('exit-guard'),'',
    location.href);
  history.pushState(mobileHistoryState('home'),'',
    location.href);
}
function mobileScreen(name,{scroll=true}={}){
  ['mobileHome','mobileListPage','mobileDetailPage'].forEach(id=>mNode(id)?.classList.toggle('on',id===name));
  document.body.classList.toggle('mobile-home-active',name==='mobileHome'&&isMobileBackoffice());
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
function numericUpcKey(v){
  const digits=String(v??'').replace(/\D/g,'').replace(/^0+/,'');
  return digits||'';
}
function seafood240249Identity(r,familyOverride=''){
  if(!r)return null;
  const upc=String(r.upc??r.number??r.ean_upc??'');
  const key=numericUpcKey(upc);
  if(key.length<6)return null;
  const prefix=key.slice(0,3);
  if(prefix!=='240'&&prefix!=='249')return null;
  const familyCandidate=r.family_id??r.family_article??r.family_article_number??r.main_article_number??'';
  const family=String(familyOverride||familyCandidate);
  if(!family)return null;
  const product=key.slice(3,6);
  const explicit=String(r.pair_240_249_key||'');
  return {
    key:explicit||family+':'+product,
    prefix,
    role:prefix==='240'?'MAIN_240':'COOK_SERVICE_249'
  };
}
function displayQtyUom(r){
  const raw=String(r?.qty_uom||r?.selling_uom||'').trim().toUpperCase();
  if(raw)return raw==='LBS'?'LB':raw;
  const key=numericUpcKey(r?.upc??r?.number??r?.ean_upc??'');
  const p=Number(key.slice(0,3));
  if(Number.isFinite(p)&&((p>=230&&p<=240)||p===242||p===245||p===247||p===249||(p>=250&&p<=269)))return 'LB';
  return 'unit';
}
function subgroupPosSummary(rows){
  const list=(rows||[]).filter(Boolean);
  if(!list.length)return {ready:false};
  const uoms=[...new Set(list.map(displayQtyUom).filter(Boolean))];
  if(uoms.length!==1||uoms[0]==='unit')return {ready:false,mixed:true};
  const qty=list.reduce((s,r)=>s+Number(r.qty_7d||0),0);
  const dayCounts=list.map(r=>Number(r.sales_days_7d||0)).filter(n=>Number.isFinite(n)&&n>0);
  const days=dayCounts.length?Math.max(...dayCounts):0;
  return {ready:true,uom:uoms[0],qty,days,avg:days>0?qty/days:null};
}
function quickSalesMeta(r){
  const uom=displayQtyUom(r);
  const noSales=String(r?.sales_evidence_status||'').includes('NO_POS_SALES_LATEST_28_VALID_DATA_DAYS');
  return '7D Vel '+fmt(r?.velocity_7d)+' '+uom+'/day · '+fmt(r?.qty_7d)+' '+uom+' 7D'+
    (noSales?' · No POS sales in latest 28 valid data days':'')+
    ' · tap for current price / OH';
}
function subgroup240249Units(rows,familyOverride=''){
  const list=Array.isArray(rows)?rows:[];
  const groups=new Map();
  list.forEach((r,i)=>{
    const id=seafood240249Identity(r,familyOverride);
    if(!id)return;
    if(!groups.has(id.key))groups.set(id.key,{key:id.key,first:i,main:null,service:null});
    const g=groups.get(id.key);
    g.first=Math.min(g.first,i);
    if(id.prefix==='240'&&!g.main)g.main=r;
    if(id.prefix==='249'&&!g.service)g.service=r;
  });
  const valid=new Map([...groups].filter(([,g])=>g.main&&g.service));
  const seen=new Set(),out=[];
  list.forEach(r=>{
    const id=seafood240249Identity(r,familyOverride);
    const g=id?valid.get(id.key):null;
    if(!g){out.push({type:'single',row:r});return}
    if(seen.has(id.key))return;
    seen.add(id.key);
    out.push({type:'pair',key:id.key,rows:[g.main,g.service]});
  });
  return out;
}
function mobileRowWithPairRole(r,code,name,meta,badge,cn){
  const id=seafood240249Identity(r);
  const html=mobileRow(String(r.upc||''),code,name,meta,badge,cn);
  return id?html.replace('class="m-row"','class="m-row" data-pair-role="'+id.role+'"'):html;
}
function pairPriceSummaryHtml(r){
  if(!r||!r.related_249_present||!r.related_240_upc||!r.related_249_upc)return '';
  const status=r.price_240_249_equal===false?' · PRICE MISMATCH':' · prices aligned';
  return '<div class="pair-inline"><b>240 / 249 SUBGROUP'+esc(status)+'</b><br>'+
    '240 MAIN · '+esc(r.related_240_upc)+' · '+money(r.related_240_current_price)+'<br>'+
    '249 COOK / SERVICE · '+esc(r.related_249_upc)+' · '+money(r.related_249_current_price)+'</div>';
}
function mobilePriceResultHtml(r){
  const rem=price249Reminder(r,true);
  if(!r.related_249_present||!r.related_240_upc||!r.related_249_upc){
    return mobileRow(String(r.upc||''),r.upc,r.name,money(r.current_price)+' current · '+money(r.candidate_price)+' candidate · '+(r.current_price_source||'—')+(r.current_price_observed_date?' · '+r.current_price_observed_date:'')+(rem?' · '+rem:''),r.priority_240_249_mismatch?'MOST URGENT':(r.review_status||'REVIEW'),'');
  }
  return '<section class="m-pair-subgroup"><div class="m-pair-label">240 / 249 SUBGROUP'+(r.price_240_249_equal===false?' · PRICE MISMATCH':'')+'</div>'+
    '<button type="button" class="m-row" data-mobile-key="'+esc(String(r.upc||''))+'">'+
      '<div class="m-row-main"><div class="m-row-copy"><div class="m-row-name">'+esc(r.name||'240 / 249 price review')+'</div>'+
      '<div class="m-pair-price-grid">'+
        '<div class="m-pair-price-member"><small>240 MAIN</small><b>'+esc(r.related_240_upc)+' · '+money(r.related_240_current_price)+'</b></div>'+
        '<div class="m-pair-price-member"><small>249 COOK / SERVICE</small><b>'+esc(r.related_249_upc)+' · '+money(r.related_249_current_price)+'</b></div>'+
      '</div>'+
      '<div class="m-row-meta">Suggestion '+esc(r.upc||'')+' · '+money(r.current_price)+' → '+money(r.candidate_price)+(rem?' · '+esc(rem):'')+'</div>'+
      '</div><span class="m-arrow">›</span></div></button></section>';
}
function price249Reminder(r,short=false){
  if(!r||!r.related_249_present||!r.related_249_upc)return '';
  const p249=r.related_249_current_price;
  const p240=r.related_240_current_price;
  const upc249=String(r.related_249_upc||'');
  const upc240=String(r.related_240_upc||'');
  if(r.price_240_249_equal===false){
    return (short?'240≠249 · ':'⚠ 240/249 PRICE MISMATCH · ')+
      '249 '+upc249+' '+money(p249)+' vs 240 '+upc240+' '+money(p240)+' · MUST MATCH';
  }
  const raw=String(r.upc||'').replace(/^0+/,'');
  const is240=raw.slice(0,3)==='240';
  if(is240&&r.candidate_price!==null&&r.candidate_price!==undefined&&
     p249!==null&&p249!==undefined&&Number(r.candidate_price)!==Number(p249)){
    return (short?'249 present · ':'⚠ 249 PRESENT · ')+upc249+' '+money(p249)+
      ' · if accepted, change 249 to '+money(r.candidate_price)+' too';
  }
  return (short?'249 present · ':'249 PRESENT · ')+upc249+
    (p249!==null&&p249!==undefined?' · '+money(p249):' · price unavailable');
}
function mobileModuleConfig(module){
  const map={
    quick:{title:'Quick Check',sub:'Most actively selling items first',chips:[['all','All'],['fresh','Fresh'],['live','Live'],['frozen','Frozen']]},
    price:{title:'Price Change',sub:'Current price, source and qualified price-change review',chips:[['all','All'],['actionable','Actionable'],['review_only','Review only'],['qa_hold','QA Hold']]},
    performance:{title:'Performance',sub:'Choose analysis dates · all Seafood together · sort by the metric you need',chips:[]},
    ordering:{title:'Ordering',sub:'Family / Receiving Article ordering review',chips:[['all','All'],['fresh','Fresh'],['frozen','Frozen'],['attention','Needs Attention']]},
    inventory:{title:'Inventory',sub:'Current stock, velocity, DOS and inventory status',chips:[['all','All'],['fresh','Fresh'],['live','Live'],['frozen','Frozen']]},
    data:{title:'Data',sub:'Uploads, QA fixes, processing and data health',chips:[]},
    qa:{title:'QA Holds',sub:'Choose one issue, review it, then fix',chips:[['all','All'],['fixable','Fixable'],['view_only','Review only'],['high','High / Critical']]},
    uploads:{title:'Uploads',sub:'New source batch and recent upload history',chips:[]},
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
function mobileRenderQuickTools(){
 const box=mNode('mobileQuickTools');if(!box)return;
 const on=mobileState.module==='quick';box.classList.toggle('on',on);
 if(!on)return;
 const input=mNode('mobileQuickSearch');
 input.value=state.inventorySearch||mobileState.query||'';
 const run=async()=>{
   const q=input.value.trim();
   state.inventorySearch=q;
   mobileState.query=q;
   const seq=++mobileQuickSearchSeq;
   mNode('mobileListSub').textContent=q?'Searching: '+q:'Most actively selling Families first';
   mNode('mobileListContent').innerHTML='<div class="m-loading">'+(q?'Searching…':'Loading recent activity…')+'</div>';
   try{
     const accepted=await loadInventory();
     if(seq!==mobileQuickSearchSeq||accepted===false)return;
     mobileRenderList();
     mNode('mobileListSub').textContent=q
       ? 'Results for “'+q+'” · Family grouped · 7D velocity ↓'
       : 'Family grouped · recent 7D velocity ↓';
   }catch(e){
     if(seq!==mobileQuickSearchSeq)return;
     mNode('mobileListContent').innerHTML='<div class="m-error">'+esc(e.message||String(e))+'</div>';
   }
 };
 input.oninput=()=>{
   clearTimeout(mobileQuickSearchTimer);
   mobileQuickSearchTimer=setTimeout(run,220);
 };
 const submitAndDismiss=()=>{
   clearTimeout(mobileQuickSearchTimer);
   input.blur();
   run();
 };
 input.onkeydown=e=>{
   if(e.key==='Enter'){
     e.preventDefault();
     submitAndDismiss();
   }
 };
 input.onsearch=()=>{
   if(document.activeElement===input)submitAndDismiss();
 };
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
function mobileRenderPerformanceTools(){
 const box=mNode('mobilePerformanceTools');if(!box)return;
 const on=mobileState.module==='performance';box.classList.toggle('on',on);
 if(!on)return;
 syncPerformanceDateControls();

 const start=mNode('mPerfStart'),end=mNode('mPerfEnd'),sort=mNode('mPerfSort'),status=mNode('mPerfStatus');
 sort.value=state.salesSort||'gp_desc';

 const refreshRange=async()=>{
   state.salesStartDate=start.value;
   state.salesEndDate=end.value;
   if(state.salesStartDate>state.salesEndDate){
     if(status)status.textContent='Start Date must be on or before End Date.';
     return;
   }
   box.classList.add('working');
   if(status)status.textContent='Updating…';
   mNode('mobileListContent').innerHTML='<div class="m-loading">Updating '+esc(state.salesStartDate)+' → '+esc(state.salesEndDate)+'…</div>';
   try{
     const ok=await loadSell();
     if(!ok)throw new Error(state.salesLastError||'Unable to analyze this date range.');
     mobileRenderList();
     mNode('mobileListSub').textContent='Showing '+state.salesStartDate+' → '+state.salesEndDate+' · '+(state.salesRows||[]).length+' items · '+sort.options[sort.selectedIndex].text;
     if(status)status.textContent='Updated';
   }catch(e){
     state.salesLastError=e.message||String(e);
     mNode('mobileListContent').innerHTML='<div class="m-error">'+esc(state.salesLastError)+'</div>';
     if(status)status.textContent=state.salesLastError;
   }finally{
     box.classList.remove('working');
   }
 };

 start.onchange=refreshRange;
 end.onchange=refreshRange;
 sort.onchange=()=>{
   state.salesSort=sort.value;
   renderSales();
   mobileRenderList();
   mNode('mobileListSub').textContent='Showing '+state.salesStartDate+' → '+state.salesEndDate+' · '+(state.salesRows||[]).length+' items · '+sort.options[sort.selectedIndex].text;
   if(status)status.textContent='';
 };
}
async function mobileRefreshHome(){
  if(!isMobileBackoffice())return;
  try{
    const res=await Promise.all([api('/healthz'),api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=5'),api('/v1/backoffice/qa-review?limit=300')]);
    const h=res[0]||{},a=res[1]||{},r=res[2]||{},q=res[3]||{};
    state.active=a.active_batch||null;state.recent=r.batches||[];state.qaIssues=q.issues||[];state.qaHistory=q.resolution_history||[];
    const sp=mNode('mServicePill');if(sp){sp.textContent=h.ok?'ONLINE':'SERVICE ISSUE';sp.className='m-status '+(h.ok?'good':'bad')}
    const dm=mNode('mDataModuleMeta'),latest=state.recent[0]||null;
    if(dm){
      const qa=state.qaIssues.length?state.qaIssues.length+' QA open':'No QA holds';
      const batch=state.active?'Batch #'+(state.active.batch_id||state.active.id||'—')+' processing':(latest?'Latest batch #'+(latest.batch_id||'—'):'No recent batch');
      dm.textContent=batch+' · '+qa;
    }
  }catch(e){
    const sp=mNode('mServicePill');if(sp){sp.textContent='CHECK FAILED';sp.className='m-status bad'}
  }
}
function showMobileHome({scroll=true,historyMode='push'}={}){
  if(!isMobileBackoffice())return;
  closeDrawer();
  mobileState.module=null;mobileState.parentModule=null;mobileState.currentDetailKey=null;mobileState.filter='all';mobileState.query='';
  mobileScreen('mobileHome',{scroll});
  if(historyMode==='push')mobilePushHistory('home');
  else if(historyMode==='replace')history.replaceState(mobileHistoryState('home'),'',location.href);
  mobileRefreshHome();
}
async function mobileOpenModule(module,{query='',historyMode='push',parentModule=null}={}){
  if(!isMobileBackoffice())return;
  closeDrawer();
  mobileState.module=module;mobileState.parentModule=parentModule;mobileState.currentDetailKey=null;mobileState.filter='all';mobileState.query=String(query||'').trim();
  const cfg=mobileModuleConfig(module);
  mNode('mobileListTitle').textContent=cfg.title;
  mNode('mobileListSub').textContent=mobileState.query&&module==='quick'?'Search: '+mobileState.query:cfg.sub;
  mNode('mobileListContent').innerHTML='<div class="m-loading">Loading…</div>';
  mobileScreen('mobileListPage');
  if(historyMode==='push')mobilePushHistory('list',{module,query:mobileState.query,parentModule:mobileState.parentModule});
  else if(historyMode==='replace')history.replaceState(mobileHistoryState('list',{module,query:mobileState.query,parentModule:mobileState.parentModule}),'',location.href);
  mobileRenderChips();
  mobileRenderQuickTools();
  mobileRenderQaTools();
  mobileRenderPerformanceTools();
  try{
    if(module==='quick'){
      state.inventorySearch=mobileState.query;state.invCat='ALL';state.invStatus='ALL';state.invOH='ALL';state.invSales='ALL';state.invSort='vel7_oh_desc';await loadInventory();
    }else if(module==='qa'){
      state.qaFilter='ALL';state.qaText='';state.qaSort='oh_vel_desc';mobileRenderQaTools();await loadQA();
    }else if(module==='price'){
      state.priceCat='ALL';state.priceStatus='ALL';state.priceSort='opportunity';state.priceText='';await loadPrices();
      if(state.priceLoadError)throw new Error(state.priceLoadError);
    }else if(module==='performance'){
      state.salesSort=state.salesSort||'gp_desc';await loadSell();mobileRenderPerformanceTools();
    }else if(module==='ordering'){
      state.orderFilter='ALL';await loadOrders();
    }else if(module==='inventory'){
      state.inventorySearch='';state.invCat='ALL';state.invStatus='ALL';state.invOH='ALL';state.invSales='ALL';state.invSort='vel7_oh_desc';await loadInventory();
    }else if(module==='data'){
      await Promise.all([loadBatches(),loadQA(),mobileLoadFreshness()]);
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
  if(mod==='performance')return filteredSalesRows();
  if(mod==='ordering'){
    let a=orderRows();
    if(f==='fresh')a=a.filter(x=>String(x.category||'').toLowerCase()==='fresh');
    if(f==='frozen')a=a.filter(x=>String(x.category||'').toLowerCase()==='frozen');
    if(f==='attention')a=a.filter(x=>x.attention);
    return a;
  }
  if(mod==='inventory'){
    let a=filteredInventoryRows();
    if(f!=='all')a=a.filter(r=>String(r.category||'').toLowerCase()===f);
    return a;
  }
  if(mod==='data'){
    return [
      {_dataMenu:'uploads',code:'Uploads',name:'Upload New Files',meta:'Create a source batch and review recent uploads',badge:'DATA'},
      {_dataMenu:'qa',code:'QA Holds',name:'Fix Data Issues',meta:(state.qaIssues.length?state.qaIssues.length+' open issue(s)':'No open QA issues'),badge:state.qaIssues.length?'REVIEW':'READY'},
      {_dataMenu:'batches',code:'Processing',name:'Batches',meta:state.active?'Current batch is processing':'Current and completed batch history',badge:state.active?'PROCESSING':'READY'},
      {_dataMenu:'freshness',code:'Data Health',name:'14-Day Coverage',meta:'POS, MVT, Price, OH, Live/Fresh and Frozen freshness',badge:'DATA'}
    ];
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
function mobileQuickReceivingGroups(rows){
  const groups=new Map();
  (rows||[]).forEach(r=>{
    const mapped=String(r.receiving_article_mapping_status||'')==='CONFIRMED_RECEIVING_ARTICLE';
    const receiving=String(r.receiving_article||'').trim();
    const fallbackKey=String(r.family_id??r.family_article??('UPC:'+String(r.upc||'')));
    const key=receiving?('RECV:'+receiving):('UNRESOLVED:'+fallbackKey);
    if(!groups.has(key))groups.set(key,{
      key,
      receiving_article:receiving||null,
      receiving_mapped:mapped,
      rows:[],
      max_velocity:Number.NEGATIVE_INFINITY,
      receiving_avg_qty_day:null,
      receiving_qty_7d:null,
      receiving_qty_uom:'',
      receiving_movement_days_7d:null,
      receiving_movement_status:'',
      category:r.category||''
    });
    const g=groups.get(key),v=Number(r.velocity_7d);
    g.rows.push(r);
    if(Number.isFinite(v))g.max_velocity=Math.max(g.max_velocity,v);
    if(g.receiving_qty_7d===null&&r.receiving_movement_7d!==null&&r.receiving_movement_7d!==undefined){
      g.receiving_qty_7d=Number(r.receiving_movement_7d);
    }
    if(g.receiving_avg_qty_day===null&&r.receiving_avg_qty_day!==null&&r.receiving_avg_qty_day!==undefined){
      g.receiving_avg_qty_day=Number(r.receiving_avg_qty_day);
    }
    if(!g.receiving_qty_uom&&r.receiving_movement_uom)g.receiving_qty_uom=String(r.receiving_movement_uom);
    if(g.receiving_movement_days_7d===null&&r.receiving_movement_days_7d!==null&&r.receiving_movement_days_7d!==undefined){
      g.receiving_movement_days_7d=Number(r.receiving_movement_days_7d);
    }
    if(!g.receiving_movement_status&&r.receiving_movement_status)g.receiving_movement_status=String(r.receiving_movement_status);
  });
  const out=[...groups.values()];
  // UPCs inside a Receiving Article stay sorted by actual recent POS velocity.
  out.forEach(g=>g.rows.sort((a,b)=>{
    const av=Number(a.velocity_7d),bv=Number(b.velocity_7d);
    const aa=Number.isFinite(av)?av:Number.NEGATIVE_INFINITY;
    const bb=Number.isFinite(bv)?bv:Number.NEGATIVE_INFINITY;
    return bb-aa||Number(b.qty_7d||0)-Number(a.qty_7d||0)||String(a.upc||'').localeCompare(String(b.upc||''));
  }));
  // Keep the most actively selling Receiving Article groups first.
  out.sort((a,b)=>b.max_velocity-a.max_velocity||(Number(b.receiving_qty_7d||0)-Number(a.receiving_qty_7d||0))||String(a.receiving_article||'').localeCompare(String(b.receiving_article||'')));
  return out;
}
function mobileQuickGroupedHtml(rows){
  return mobileQuickReceivingGroups(rows).map((g,idx)=>{
    const avg=g.receiving_avg_qty_day===null?'—':fmt(g.receiving_avg_qty_day);
    const total=g.receiving_qty_7d===null?'—':fmt(g.receiving_qty_7d);
    const uom=g.receiving_qty_uom||'';
    const avgText=avg==='—'?'—':avg+(uom?' '+uom:'')+'/day';
    const totalText=total==='—'?'—':total+(uom?' '+uom:'');
    const receivingLabel=g.receiving_mapped
      ? esc(g.receiving_article||'—')
      : 'UNRESOLVED';
    const mapText=g.receiving_mapped
      ? 'Group leader for linked selling UPCs'
      : 'Receiving Article mapping required';
    const movementSub=g.receiving_qty_7d===null
      ? esc(g.receiving_movement_status||'251−252 unavailable')
      : '251−252 · 7D MVT · '+esc(totalText);
    const header='<div class="m-receiving-head"><div><small>RECEIVING ARTICLE</small><b>'+receivingLabel+'</b><div class="recv-map">'+mapText+'</div></div><div class="m-receiving-movement"><small>MVT Avg Qty/Day</small><b>'+esc(avgText)+'</b><small>'+movementSub+'</small></div></div>';
    const children=subgroup240249Units(g.rows).map(unit=>{
      const rowHtml=r=>mobileRowWithPairRole(
        r,
        r.upc||r.family_article,
        r.name||r.family_name,
        quickSalesMeta(r),
        r.readiness||r.category,
        r.chinese_name||''
      );
      if(unit.type!=='pair')return rowHtml(unit.row);
      const sm=subgroupPosSummary(unit.rows);
      const stats=sm.ready
        ? '<div class="m-pair-stats"><small>POS Avg Qty/Day</small><b>'+esc(fmt(sm.avg)+' '+sm.uom+'/day')+'</b><small>7D Qty · '+esc(fmt(sm.qty)+' '+sm.uom)+'</small></div>'
        : '<div class="m-pair-stats"><small>POS 7D Qty</small><b>See UPC rows</b><small>Mixed / unresolved UOM</small></div>';
      return '<section class="m-pair-subgroup"><div class="m-pair-label"><div class="m-pair-name">↳ 240 / 249 SUBGROUP</div>'+stats+'</div>'+unit.rows.map(rowHtml).join('')+'</section>';
    }).join('');
    return '<section class="m-receiving-group recv-tone-'+(idx%6)+'">'+header+'<div class="m-receiving-upcs">'+children+'</div></section>';
  }).join('');
}
function mobileRenderList(){
  const box=mNode('mobileListContent');if(!box)return;
  const rows=mobileRows();let html='';
  if(mobileState.module==='quick'){
    html=mobileQuickGroupedHtml(rows);
  }else if(mobileState.module==='qa'){
    html=rows.map(x=>{const cur=x.current||{};const key=(x.issue_id===null||x.issue_id===undefined)?'QC:'+String(x.entity_key||''):String(x.issue_id);return mobileRow(key,x.entity_key||x.issue_code,cur.item_name||cur.selling_description||x.issue_code,'OH '+fmt(cur.current_oh)+' '+(cur.current_oh_uom||'')+' · 7D Vel '+fmt(cur.upc_velocity_7d)+'/'+(cur.selling_uom||'unit')+' · '+qaFixKindLabel(x.fix_kind)+' · '+(x.issue_summary||''),x.severity||x.fix_kind,cur.chinese_name||'')}).join('');
  }else if(mobileState.module==='price'){
    html=rows.map(r=>mobilePriceResultHtml(r)).join('');
  }else if(mobileState.module==='performance'){
    html=subgroup240249Units(rows).map(unit=>{
      const rr=r=>mobileRowWithPairRole(r,r.upc,r.name,money(r.sales_amount)+' Sales · '+money(r.gp_dollars)+' GP$ · '+fmt(r.velocity)+' '+(r.qty_uom||'')+'/day · '+fmt(r.sold_quantity)+' '+(r.qty_uom||''),r.gp_cost_complete?'GP READY':'GP HOLD','');
      return unit.type==='pair'?'<section class="m-pair-subgroup"><div class="m-pair-label">240 / 249 SUBGROUP</div>'+unit.rows.map(rr).join('')+'</section>':rr(unit.row);
    }).join('');
  }else if(mobileState.module==='ordering'){
    html=rows.map(r=>mobileRow(String(r.family_article||''),r.family_article||r.receiving_article,r.family_name||'Family Article','OH '+fmt(r.oh)+' '+(r.oh_uom||'')+' · Last receipt '+(r.last_receipt_date||'—')+' · Suggested '+fmt(r.suggested_delivery_qty)+' '+(r.suggested_delivery_uom||''),r.attention?'REVIEW':'READY','')).join('');
  }else if(mobileState.module==='inventory'){
    html=subgroup240249Units(rows).map(unit=>{
      const rr=r=>mobileRowWithPairRole(r,r.upc,r.name||r.family_name,'OH '+fmt(r.family_oh)+' '+(r.family_oh_uom||'')+' · 7D Vel '+fmt(r.velocity_7d)+' · DOS '+fmt(r.dos)+' · '+money(r.price),r.readiness||r.category,r.chinese_name||'');
      return unit.type==='pair'?'<section class="m-pair-subgroup"><div class="m-pair-label">240 / 249 SUBGROUP</div>'+unit.rows.map(rr).join('')+'</section>':rr(unit.row);
    }).join('');
  }else if(mobileState.module==='data'){
    html=rows.map(r=>mobileRow('data:'+r._dataMenu,r.code,r.name,r.meta,r.badge,'')).join('');
  }else if(mobileState.module==='pi'){
    html=rows.map(r=>mobileRow(String(r.family_article||r.upc||''),r.family_article||r.upc,r.family_name||r.name,fmt(r.family_oh)+' '+(r.family_oh_uom||'')+' OH · '+fmt(r.qty_7d)+' 7D · DOS '+fmt(r.dos),'OH',r.chinese_name||'')).join('');
  }else if(mobileState.module==='batches'){
    html=rows.map(b=>mobileRow((b._mobileActive?'active:':'batch:')+String(b.batch_id||b.id||''),'Batch #'+(b.batch_id||b.id||'—'),b.batch_label||(b._mobileActive?'Active processing':'Completed batch'),(b.file_count??'—')+' file(s) · '+(b.quick_check_ready_rows??'—')+' ready · '+(b.quick_check_hold_rows??'—')+' hold',b._mobileActive?(b.processing_status||b.status||'CURRENT'):(b.phase3_status||b.processing_status||'DONE'),'')).join('');
  }else if(mobileState.module==='uploads'){
    html=rows.map(b=>b._mobileNewUpload?mobileRow('new-upload','＋ New Upload','Create source batch','Choose one or more source files; file type is detected automatically','UPLOAD',''):mobileRow('uploadbatch:'+String(b.batch_id||b.id||''),'Batch #'+(b.batch_id||b.id||'—'),b.batch_label||(b._mobileActive?'Active processing':'Upload history'),(b.file_count??'—')+' file(s) · '+(b.upload_started_at||b.completed_at||'—'),b._mobileActive?(b.processing_status||'CURRENT'):(b.phase3_status||b.processing_status||'DONE'),'')).join('');
  }else if(mobileState.module==='freshness'){
    html=rows.map(r=>mobileDataHealthRow(r)).join('');
  }
  if(!html&&mobileState.module==='ordering'&&state.orderHealth?.blocked){
    const h=state.orderHealth;
    const missing=(h.missing||[]).join(' + ')||'POS / MVT';
    html='<div class="m-error"><b>Ordering blocked — required data is not current.</b><br><br>Required through '+esc(h.expectedThrough||'—')+'<br>POS through '+esc(h.posThrough||'—')+'<br>MVT through '+esc(h.movementThrough||'—')+'<br><br>Missing/currentness issue: '+esc(missing)+'.<br>Upload or finish ingestion for the missing completed day, then refresh Ordering.</div>';
  }
  if(!html&&mobileState.module==='price'&&state.priceHealth?.blocked){
    const h=state.priceHealth;
    const missing=(h.missing||[]).join(' + ')||'POS / MVT';
    html='<div class="m-error"><b>Price Change blocked — required data is not current.</b><br><br>Required through '+esc(h.expectedThrough||'—')+'<br>POS through '+esc(h.posThrough||'—')+'<br>MVT through '+esc(h.movementThrough||'—')+'<br><br>Missing/currentness issue: '+esc(missing)+'.<br>Upload or finish ingestion for the missing completed day, then refresh Price Change.</div>';
  }
  if(!html&&mobileState.module==='price'&&!state.priceHealth?.blocked&&!state.priceLoadError){
    const suppressed=Number(state.priceMeta?.suppressedAccepted||0);
    html='<div class="m-empty"><b>No qualified price changes in the current snapshot.</b>'+(suppressed?'<br><br>'+esc(suppressed)+' previously accepted suggestion(s) remain suppressed because the price evidence and candidate have not changed.':'')+'</div>';
  }
  box.innerHTML=html||'<div class="m-empty">No items match the current filter.</div>';
  box.querySelectorAll('[data-mobile-key]').forEach(b=>b.onclick=()=>mobileOpenItem(b.dataset.mobileKey));
}
function mobileShowDetail(title,sub,html,{historyMode='push'}={}){
  mNode('mobileDetailTitle').textContent=title||'Detail';mNode('mobileDetailSub').textContent=sub||'';mNode('mobileDetailContent').innerHTML=html;mobileScreen('mobileDetailPage');
  if(historyMode==='push')mobilePushHistory('detail',{
    module:mobileState.module,
    parentModule:mobileState.parentModule,
    query:mobileState.query||'',
    key:mobileState.currentDetailKey
  });
  else if(historyMode==='replace')history.replaceState(mobileHistoryState('detail',{
    module:mobileState.module,
    parentModule:mobileState.parentModule,
    query:mobileState.query||'',
    key:mobileState.currentDetailKey
  }),'',location.href);
}
function mobileOpenItem(key){
  mobileState.currentDetailKey=String(key??'');
  const mod=mobileState.module;
  if(mod==='quick')return mobileOpenQuickDetail(key);
  if(mod==='qa')return openQAIssue(key);
  if(mod==='price')return openPriceDetail(key);
  if(mod==='performance')return mobilePerformanceDetail(key);
  if(mod==='ordering')return mobileOrderingDetail(key);
  if(mod==='inventory')return mobileQuickDetail(key,false);
  if(mod==='data'){
    const target=String(key).replace(/^data:/,'');
    return mobileOpenModule(target,{parentModule:'data'});
  }
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
function mobileQuickTrendSvg(rows){
  const a=(rows||[]).slice(-7);
  if(!a.length)return '<div class="m-empty">No supported sales days available.</div>';
  const W=680,H=270,L=34,R=18,T=34,B=42;
  const plotW=W-L-R,plotH=H-T-B,step=plotW/Math.max(1,a.length);
  const gps=a.map(x=>x.gp_dollars===null||x.gp_dollars===undefined?null:Number(x.gp_dollars));
  const prices=a.map(x=>x.avg_sold_price===null||x.avg_sold_price===undefined?null:Number(x.avg_sold_price));
  const gpFinite=gps.filter(Number.isFinite),priceFinite=prices.filter(Number.isFinite);
  const gpMin=Math.min(0,...(gpFinite.length?gpFinite:[0]));
  const gpMax=Math.max(0,...(gpFinite.length?gpFinite:[1]));
  const gpSpan=(gpMax-gpMin)||1;
  const pMin=priceFinite.length?Math.min(...priceFinite):0;
  const pMax=priceFinite.length?Math.max(...priceFinite):1;
  const pSpan=(pMax-pMin)||1;
  const gy=v=>T+(gpMax-v)/gpSpan*plotH;
  const py=v=>T+12+(pMax-v)/pSpan*(plotH-24);
  const zeroY=gy(0);
  let bars='',labels='',linePts=[],dots='';
  a.forEach((x,i)=>{
    const cx=L+step*i+step/2;
    const gp=gps[i],pr=prices[i];
    const date=String(x.date||'').slice(5);
    labels+='<text x="'+cx.toFixed(1)+'" y="'+(H-12)+'" text-anchor="middle" class="m-chart-date">'+esc(date)+'</text>';
    if(Number.isFinite(gp)){
      const y=gy(gp),top=Math.min(y,zeroY),height=Math.max(2,Math.abs(zeroY-y));
      bars+='<rect x="'+(cx-step*.27).toFixed(1)+'" y="'+top.toFixed(1)+'" width="'+(step*.54).toFixed(1)+'" height="'+height.toFixed(1)+'" rx="5" class="m-chart-bar"/>';
      bars+='<text x="'+cx.toFixed(1)+'" y="'+(gp>=0?Math.max(12,top-5):Math.min(H-B+14,top+height+13)).toFixed(1)+'" text-anchor="middle" class="m-chart-gpval">'+esc(money(gp))+'</text>';
    }
    if(Number.isFinite(pr)){
      const y=py(pr);linePts.push(cx.toFixed(1)+','+y.toFixed(1));
      dots+='<circle cx="'+cx.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="5" class="m-chart-dot"/>'+
            '<text x="'+cx.toFixed(1)+'" y="'+Math.max(13,y-10).toFixed(1)+'" text-anchor="middle" class="m-chart-priceval">'+esc(money(pr))+'</text>';
    }
  });
  const line=linePts.length>1?'<polyline points="'+linePts.join(' ')+'" class="m-chart-line"/>':'';
  return '<div class="m-trendlegend"><span><i class="bar"></i>GP$</span><span><i class="line"></i>Avg Selling Price</span></div>'+
    '<div class="m-trendwrap"><svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="7-day GP dollars and average selling price trend">'+
    '<line x1="'+L+'" y1="'+zeroY.toFixed(1)+'" x2="'+(W-R)+'" y2="'+zeroY.toFixed(1)+'" class="m-chart-zero"/>'+
    bars+line+dots+labels+'</svg></div>';
}
function mobileQuick7dHistoryHtml(rows,qtyUom){
  const a=(rows||[]).slice(-7).reverse();
  if(!a.length)return '<div class="m-empty">No supported sales history available.</div>';
  return '<div class="m-history7">'+a.map(x=>
    '<div class="m-history7-row">'+
      '<div class="m-history7-date"><b>'+esc(String(x.date||''))+'</b><span>'+esc((x.price_types||[]).map(p=>p.price_type).filter(Boolean).join(' / ')||'No sale')+'</span></div>'+
      '<div><small>Qty</small><b>'+esc(fmt(x.sold_quantity))+' '+esc(qtyUom||x.qty_uom||'')+'</b></div>'+
      '<div><small>Sales</small><b>'+esc(money(x.sales_amount))+'</b></div>'+
      '<div><small>Avg Price</small><b>'+esc(money(x.avg_sold_price))+'</b></div>'+
      '<div><small>GP$</small><b>'+esc(money(x.gp_dollars))+'</b></div>'+
    '</div>'
  ).join('')+'</div>';
}
async function mobileLoadQuick7d(upc){
  const box=mNode('mQuick7dSection');if(!box)return;
  try{
    const d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc)+'/price?trend_supported_days=7');
    const trend=d.price_vs_sales_trend||{},rows=trend.rows||[];
    box.innerHTML=
      '<div class="m-detailcard m-trendcard">'+
        '<div class="m-label">Past 7 Data Days · Sales History & Trend</div>'+
        '<div class="m-chartnote">Completed canonical POS data days only · missing source dates are not zeros</div>'+
        mobileQuickTrendSvg(rows)+
        '<div class="m-detailsection"><h3>Daily Sales History</h3>'+mobileQuick7dHistoryHtml(rows,d.qty_uom||trend.qty_uom)+'</div>'+
      '</div>';
  }catch(e){
    box.innerHTML='<div class="m-error">7-day history unavailable: '+esc(e.message||String(e))+'</div>';
  }
}
async function mobileOpenQuickDetail(key){
  const upc=String(key||'').trim();
  const preview=state.inventory.find(x=>String(x.upc||'')===upc);
  const title=upc||'UPC Detail';
  const sub=(preview?.name||preview?.family_name||'')+(preview?.chinese_name?' · '+preview.chinese_name:'');
  mobileShowDetail(
    title,
    sub,
    '<div class="m-detailcard"><div class="m-loading">Loading current UPC detail…</div></div>',
    {historyMode:'push'}
  );
  try{
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),12000);
    let d;
    try{
      d=await api(
        '/v1/backoffice/inventory?category=ALL&limit=20&lightweight=false&q='+encodeURIComponent(upc),
        {signal:controller.signal}
      );
    }finally{
      clearTimeout(timeout);
    }
    const full=(d.rows||[]).find(x=>String(x.upc||'')===upc);
    if(!full)throw new Error('UPC detail was not found.');
    const idx=state.inventory.findIndex(x=>String(x.upc||'')===upc);
    if(idx>=0)state.inventory[idx]={...state.inventory[idx],...full};
    else state.inventory.push(full);
    mobileQuickDetail(upc,false,{historyMode:'none'});
  }catch(e){
    const msg=e?.name==='AbortError'
      ? 'UPC detail timed out. Please retry.'
      : (e.message||String(e));
    mNode('mobileDetailContent').innerHTML='<div class="m-error">'+esc(msg)+'</div>';
  }
}
function mobileQuickDetail(key,piMode,{historyMode='push'}={}){
  let r=null;
  if(piMode)r=state.inventory.find(x=>String(x.family_article||x.upc)===String(key));
  else r=state.inventory.find(x=>String(x.upc)===String(key));
  if(!r)return;
  const title=piMode?String(r.family_article||r.upc||'Item'):String(r.upc||r.family_article||'Item');
  const sub=(piMode?(r.family_name||r.name):(r.name||r.family_name))+(r.chinese_name?' · '+r.chinese_name:'');
  const ohStatus=String(r.family_oh_status||'').toUpperCase();
  const ohNote=ohStatus==='READY'
    ? 'Current effective family OH'
    : (r.family_oh_as_of?'Latest published family OH · through '+r.family_oh_as_of:'Family OH unavailable')+(r.family_oh_live_status?' · '+r.family_oh_live_status:'');
  let html='<div class="m-detailcard"><div class="m-label">'+(piMode?'Family / PI Summary':'UPC Summary')+'</div><div class="m-detailgrid">';
  html+=mobileMetric('Current Price',money(r.price),(r.price_type||'—')+' · '+(r.price_source||'—')+(r.price_as_of?' · '+r.price_as_of:''));
  html+=mobileMetric(
    'Current Cost',
    money(r.cost)+(r.cost_uom?' / '+r.cost_uom:''),
    (r.cost_source||'Source unavailable')+(r.cost_date?' · '+r.cost_date:'')
  );
  html+=mobileMetric('OH',fmt(r.family_oh)+' '+(r.family_oh_uom||''),ohNote);
  html+=mobileMetric('7D Sold',fmt(r.qty_7d)+' '+(r.selling_uom||''),'POS quantity');
  html+=mobileMetric('7D Velocity',fmt(r.velocity_7d),(r.selling_uom||'unit')+'/day');
  html+=mobileMetric('GP%',pct(r.gp_pct),'At current price / cost');
  html+=mobileMetric('DOS',fmt(r.dos),'Days of supply');
  html+=mobileMetric('Family',r.family_article||'—',r.family_name||'');
  html+='</div>';
  html+='<div class="m-detailsection"><h3>Pricing References</h3><div class="m-detailgrid">';
  html+=mobileMetric(
    'Sweet Spot',
    money(r.sweet_spot_price),
    r.sweet_spot_price===null||r.sweet_spot_price===undefined
      ? 'Not enough validated history'
      : 'Highest historical avg GP$/completed POS data day · latest 30 completed POS data days'
  );
  html+=mobileMetric('Company A',money(r.company_price_a),r.company_price_a===null||r.company_price_a===undefined?'No reference':'Company reference price');
  html+=mobileMetric('Company B',money(r.company_price_b),r.company_price_b===null||r.company_price_b===undefined?'No reference':'Company reference price');
  html+=mobileMetric('Company C',money(r.company_price_c),r.company_price_c===null||r.company_price_c===undefined?'No reference':'Company reference price');
  html+='</div></div>';
  if(r.family_article)html+='<button id="mAdjustOH" type="button" class="m-action primary">Update True Stock / OH</button>';
  html+='</div>';
  if(!piMode&&r.upc)html+='<div id="mQuick7dSection" class="m-quick7d"><div class="m-loading">Loading 7-day sales history…</div></div>';
  mobileShowDetail(title,sub,html,{historyMode});
  const btn=mNode('mAdjustOH');if(btn)btn.onclick=()=>openOH({family:r.family_article,uom:r.family_oh_uom||'',oh:r.family_oh??'',name:r.family_name||r.name||''});
  if(!piMode&&r.upc)mobileLoadQuick7d(r.upc);
}
function mobilePerformanceDetail(key){
  const r=state.salesRows.find(x=>String(x.upc)===String(key));if(!r)return;
  const range=state.salesRange||{};
  let html='<div class="m-detailcard"><div class="m-label">Range Performance</div><div class="m-detailgrid">';
  html+=mobileMetric('Sales',money(r.sales_amount),(range.start_date||'—')+' → '+(range.end_date||'—'));
  html+=mobileMetric('GP'+'$',money(r.gp_dollars),r.gp_cost_complete?'Historical applicable cost':'Cost missing on '+(r.gp_missing_cost_days||[]).length+' sold day(s)');
  html+=mobileMetric('GP%',pct(r.gp_pct),'Range gross margin');
  html+=mobileMetric('Sold Qty',fmt(r.sold_quantity)+' '+(r.qty_uom||''),'POS range total');
  html+=mobileMetric('Velocity',fmt(r.velocity)+' '+(r.qty_uom||'')+'/day',(r.supported_day_count||0)+' completed data days');
  html+=mobileMetric('Avg Sold Price',money(r.avg_sold_price),'Weighted range average');
  html+=mobileMetric('GP'+'$/Data Day',money(r.gp_per_supported_day),'Completed canonical days');
  html+=mobileMetric('Sold Days',fmt(r.sold_supported_day_count,0),'Days with positive POS qty');
  html+='</div></div>';
  mobileShowDetail(r.upc||'Performance',r.name||'',html);
}
function mobileOrderingDetail(key){
  const r=state.orders.find(x=>String(x.family_article||'')===String(key));if(!r)return;
  const d=r.details||{};
  let html='<div class="m-detailcard"><div class="m-label">Family / Receiving Article Order Review</div><div class="m-detailgrid">';
  html+=mobileMetric('Family Article',r.family_article||'—',r.family_name||'');
  html+=mobileMetric('Receiving Article',r.receiving_article||'—','Ordering / receiving level');
  html+=mobileMetric('OH',fmt(r.oh)+' '+(r.oh_uom||''),'Current family OH');
  html+=mobileMetric('Last Receipt',r.last_receipt_date||'—',fmt(r.last_receipt_qty_base)+' '+(r.last_receipt_base_uom||''));
  html+=mobileMetric('Frequency',r.ordering_frequency||'—','Observed ordering cadence');
  html+=mobileMetric('Coming Delivery Suggestion',fmt(r.suggested_delivery_qty)+' '+(r.suggested_delivery_uom||''),'Family-level suggestion');
  html+='</div>';
  if((d.reasons||[]).length)html+='<div class="m-detailsection"><h3>Why?</h3><p>'+esc((d.reasons||[]).join(' · '))+'</p></div>';
  html+='</div>';
  mobileShowDetail(r.family_article||'Ordering',r.family_name||'',html);
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

function mobileCurrentDepthToHome(){
  if(mNode('mobileHome')?.classList.contains('on'))return 0;
  let depth=1; // top-level list
  if(mobileState.parentModule)depth+=1; // Data -> child list
  if(mNode('mobileDetailPage')?.classList.contains('on'))depth+=1; // list -> detail
  return depth;
}
function mobileNavigateTopModule(module){
  if(!isMobileBackoffice())return;
  if(mNode('mobileHome')?.classList.contains('on')){
    mobileOpenModule(module,{historyMode:'push',parentModule:null});
    return;
  }
  const depth=mobileCurrentDepthToHome();
  mobilePendingTopModule=module;
  if(depth>0)history.go(-depth);
  else{
    mobilePendingTopModule=null;
    mobileOpenModule(module,{historyMode:'push',parentModule:null});
  }
}
function mobileNavigateHome(){
  if(!isMobileBackoffice())return;
  const depth=mobileCurrentDepthToHome();
  if(depth>0)history.go(-depth);
  else showMobileHome({historyMode:'none'});
}
async function mobileRestoreCurrentRoute(){
  mobileInitHistory();
  const s=history.state||{};
  if(!s[MOBILE_HISTORY_KEY]||s.screen==='exit-guard'){
    showMobileHome({scroll:false,historyMode:'none'});
    return;
  }
  mobileRestoringHistory=true;
  try{
    closeDrawer();
    if(s.screen==='home'){
      showMobileHome({scroll:false,historyMode:'none'});
      return;
    }
    if(s.screen==='list'&&s.module){
      await mobileOpenModule(s.module,{
        query:s.query||'',
        historyMode:'none',
        parentModule:s.parentModule||null
      });
      return;
    }
    if(s.screen==='detail'&&s.module){
      await mobileOpenModule(s.module,{
        query:s.query||'',
        historyMode:'none',
        parentModule:s.parentModule||null
      });
      if(s.key!==undefined&&s.key!==null&&String(s.key)!==''){
        mobileState.currentDetailKey=String(s.key);
        mobileOpenItem(String(s.key));
      }else{
        mobileScreen('mobileListPage',{scroll:false});
      }
      return;
    }
    showMobileHome({scroll:false,historyMode:'none'});
  }finally{
    mobileRestoringHistory=false;
  }
}

$$('[data-mobile-module]').forEach(b=>b.onclick=()=>{
  const module=b.dataset.mobileModule;
  if(b.closest('.m-bottomnav'))mobileNavigateTopModule(module);
  else mobileOpenModule(module,{historyMode:'push',parentModule:null});
});
$$('[data-mobile-home]').forEach(b=>b.onclick=()=>mobileNavigateHome());
function mobileBackOrClose(){
  if($('#drawer').classList.contains('on')){
    const st=history.state||{};
    if(st[MOBILE_HISTORY_KEY]&&st.drawer)history.back();
    else closeDrawer();
    return;
  }
  history.back();
}
mNode('mobileListBack').onclick=mobileBackOrClose;
mNode('mobileDetailBack').onclick=mobileBackOrClose;

window.addEventListener('popstate',async e=>{
  if(!isMobileBackoffice())return;
  const s=e.state||{};
  if(!s[MOBILE_HISTORY_KEY])return;

  if($('#drawer').classList.contains('on')&&!s.drawer){
    closeDrawer();
    return;
  }

  if(mobilePendingTopModule&&s.screen==='home'){
    const target=mobilePendingTopModule;
    mobilePendingTopModule=null;
    mobileRestoringHistory=true;
    try{showMobileHome({scroll:false,historyMode:'none'})}
    finally{mobileRestoringHistory=false}
    await mobileOpenModule(target,{historyMode:'push',parentModule:null});
    return;
  }

  if(s.screen==='exit-guard'){
    const leave=window.confirm('Exit FULL MYSQL app?');
    if(leave){
      mobileAllowExit=true;
      history.back();
    }else{
      history.pushState(mobileHistoryState('home'),'',
        location.href);
      mobileRestoringHistory=true;
      try{showMobileHome({scroll:false,historyMode:'none'})}
      finally{mobileRestoringHistory=false}
    }
    return;
  }

  mobileRestoringHistory=true;
  try{
    closeDrawer();
    if(s.screen==='home'){
      showMobileHome({scroll:false,historyMode:'none'});
    }else if(s.screen==='list'&&s.module){
      await mobileOpenModule(s.module,{query:s.query||'',historyMode:'none',parentModule:s.parentModule||null});
    }else if(s.screen==='detail'&&s.module){
      await mobileOpenModule(s.module,{
        query:s.query||'',
        historyMode:'none',
        parentModule:s.parentModule||null
      });
      if(s.key!==undefined&&s.key!==null&&String(s.key)!==''){
        mobileState.currentDetailKey=String(s.key);
        mobileOpenItem(String(s.key));
      }else{
        mobileScreen('mobileListPage',{scroll:false});
      }
    }
  }finally{
    mobileRestoringHistory=false;
  }
});

mobileMedia.addEventListener?.('change',e=>{
  if(e.matches){
    mobileRestoreCurrentRoute();
  }else{
    closeDrawer();mobileScreen('',{scroll:false});restoreRoute();
  }
});
function openDrawer(title,sub,body,foot=''){
  $('#drawerTitle').textContent=title;$('#drawerSub').textContent=sub||'';$('#drawerBody').innerHTML=body;$('#drawerFoot').innerHTML=foot;$('#drawerBack').classList.add('on');$('#drawer').classList.add('on');
  if(isMobileBackoffice()&&!mobileRestoringHistory){
    const st=history.state||{};
    if(st[MOBILE_HISTORY_KEY]&&!st.drawer)history.pushState({...st,drawer:true},'',location.href);
  }
}
function closeDrawer(){$('#drawerBack').classList.remove('on');$('#drawer').classList.remove('on')}
function closeDrawerUser(){
  const st=history.state||{};
  if(isMobileBackoffice()&&st[MOBILE_HISTORY_KEY]&&st.drawer)history.back();
  else closeDrawer();
}
$('#drawerClose').onclick=closeDrawerUser;$('#drawerBack').onclick=closeDrawerUser;

async function loadHealth(){try{const h=await api('/healthz');$('#readyPill').textContent=h.ok?'SERVICE READY':'SERVICE ISSUE';$('#readyPill').style.color=h.ok?'#bff3d2':'#ffd0c8'}catch(e){$('#readyPill').textContent='SERVICE ERROR'}}
async function loadInventory(){
 const requestSeq=++inventoryLoadSeq;
 const q=String(state.inventorySearch||'').trim();
 const cat=String(state.invCat||'ALL');
 const err=$('#invError');
 err.innerHTML='';
 $('#invRows').innerHTML='<tr><td colspan="11" class="loading">Loading...</td></tr>';
 try{
   const light=(isMobileBackoffice()&&mobileState.module==='quick');
   const url=`/v1/backoffice/inventory?category=${encodeURIComponent(cat)}&limit=${light?120:300}&lightweight=${light?'true':'false'}${q?'&q='+encodeURIComponent(q):''}`;
   const controller=new AbortController();
   const timeout=setTimeout(()=>controller.abort(),8000);
   let d;
   try{
     d=await api(url,{signal:controller.signal});
   }finally{
     clearTimeout(timeout);
   }

   // A slower previous live-search response must never overwrite the newest
   // query's results. The server echoes its query so we validate both request
   // sequence and query identity before mutating shared Inventory state.
   if(requestSeq!==inventoryLoadSeq)return false;
   if(String(state.inventorySearch||'').trim()!==q)return false;
   if(String(d.query||'').trim()!==q)return false;

   state.inventory=d.rows||[];
   const badge=$('#invSearchState'),clear=$('#clearInventorySearch');
   if(q){
     badge.textContent=`Search: ${q}`;
     badge.style.display='inline-flex';
     clear.style.display='inline-flex';
   }else{
     badge.style.display='none';
     clear.style.display='none';
   }
   renderInventory();
   return true;
 }catch(e){
   if(requestSeq!==inventoryLoadSeq)return false;
   const msg=e?.name==='AbortError'
     ? 'Search timed out. Please retry or refine the search.'
     : (e.message||String(e));
   err.innerHTML=`<div class="error">${esc(msg)}</div>`;
   $('#invRows').innerHTML='';
   throw new Error(msg);
 }
}
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
function renderInventory(){
  const rows=filteredInventoryRows();
  $('#invCount').textContent=`${rows.length} shown · ${state.inventory.length} loaded`;
  const rowHtml=(r,cls='')=>`<tr class="${cls} ${Number(r.velocity_7d||0)>0?'velocity-active':''}"><td><div class="name">${esc(r.name)}</div><div class="meta">${esc(r.category||'')} · ${esc(r.price_type||'')}</div></td><td>${esc(r.upc)}</td><td><b>${esc(r.family_article||'—')}</b><div class="meta">${esc(r.family_name||'')}</div></td><td><button class="linkbtn ohbtn" data-family="${esc(r.family_article||'')}" data-uom="${esc(r.family_oh_uom||'')}" data-oh="${esc(r.family_oh??'')}" data-name="${esc(r.family_name||r.name)}">${fmt(r.family_oh)} ${esc(r.family_oh_uom||'')}</button></td><td>${fmt(r.qty_7d)}</td><td><b>${fmt(r.velocity_7d)}</b><div class="meta">${esc(r.selling_uom||'unit')}/day</div></td><td><b>${money(r.price)}</b><div class="meta">${esc(r.price_type||'—')} · ${esc(r.price_source||'—')} ${r.price_as_of?'· '+esc(r.price_as_of):''}</div></td><td>${money(r.cost)}</td><td>${pct(r.gp_pct)}</td><td>${fmt(r.dos)}</td><td>${pill(r.readiness)}</td></tr>`;
  $('#invRows').innerHTML=subgroup240249Units(rows).map(unit=>{
    if(unit.type!=='pair')return rowHtml(unit.row);
    const fam=unit.rows[0]?.family_article||'—';
    return '<tr class="pair-subgroup-head"><td colspan="11">240 / 249 SUBGROUP · Family '+esc(fam)+'</td></tr>'+
      rowHtml(unit.rows[0],'pair-subgroup-main')+rowHtml(unit.rows[1],'pair-subgroup-service');
  }).join('')||`<tr><td colspan="11" class="empty">${state.inventorySearch?'No matching rows after current Inventory filters for: '+esc(state.inventorySearch):'No inventory rows match the current filters.'}</td></tr>`;
  $$('.ohbtn').forEach(b=>b.onclick=()=>openOH(b.dataset));
}
$$('.invfilter').forEach(b=>b.onclick=()=>{state.invCat=b.dataset.cat;$$('.invfilter').forEach(x=>x.classList.toggle('on',x===b));loadInventory()});
$('#invStatusFilter').onchange=e=>{state.invStatus=e.target.value;renderInventory()};
$('#invOHFilter').onchange=e=>{state.invOH=e.target.value;renderInventory()};
$('#invSalesFilter').onchange=e=>{state.invSales=e.target.value;renderInventory()};
$('#invSort').onchange=e=>{state.invSort=e.target.value;renderInventory()};
$('#clearInventorySearch').onclick=()=>{state.inventorySearch='';$('#searchInput').value='';loadInventory()};

function openOH(d){if(!d.family){toast('Family Article unavailable');return}const current=d.oh||'';openDrawer('OH / True Stock Adjustment',`${d.name} · Family ${d.family}`,`<div class="detailgrid"><div class="detail"><small>Family Article</small><b>${esc(d.family)}</b></div><div class="detail"><small>System / Effective OH</small><b>${fmt(current)} ${esc(d.uom)}</b></div></div><div class="formfield"><label>True Stock</label><input id="trueStockInput" type="number" min="0" step="0.01" value="${esc(current)}"></div><div class="formfield"><label>UOM</label><input id="trueStockUom" value="${esc(d.uom)}" readonly></div><div class="formfield"><label>Note</label><textarea id="trueStockNote" placeholder="Physical count / OH adjustment"></textarea></div><div id="ohPreview" class="calc">Difference: 0</div>`,`<button id="saveOH" class="btn primary">Save OH Adjustment</button>`);const inp=$('#trueStockInput');inp.oninput=()=>{const n=Number(inp.value||0),o=Number(current||0),diff=n-o;$('#ohPreview').textContent=`Difference: ${diff>=0?'+':''}${diff.toFixed(2)}${diff<0?' · shortage / pending dumping '+Math.abs(diff).toFixed(2):''}`};$('#saveOH').onclick=async()=>{try{$('#saveOH').disabled=true;await api(`/v1/app/v2/pi/${encodeURIComponent(d.family)}/true-stock`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:Number(inp.value),uom:d.uom,note:$('#trueStockNote').value||null})});toast('OH / True Stock saved');closeDrawer();await loadInventory()}catch(e){toast(e.message)}finally{const x=$('#saveOH');if(x)x.disabled=false}}}

async function ensurePerformanceDates(){
  if(state.salesSupportedDates.length){syncPerformanceDateControls();return}
  const d=await api('/v1/app/v2/performance/dates?limit=180');
  const dates=(d.dates||[]).map(x=>String(x.date||'')).filter(Boolean).sort();
  state.salesSupportedDates=dates;
  if(dates.length){
    if(!state.salesEndDate)state.salesEndDate=dates[dates.length-1];
    if(!state.salesStartDate)state.salesStartDate=dates[Math.max(0,dates.length-7)];
  }
  syncPerformanceDateControls();
}
function syncPerformanceDateControls(){
  const dates=state.salesSupportedDates||[];
  const opts=dates.map(d=>'<option value="'+esc(d)+'">'+esc(d)+'</option>').join('');
  [['salesStartDate',state.salesStartDate],['salesEndDate',state.salesEndDate],['mPerfStart',state.salesStartDate],['mPerfEnd',state.salesEndDate]].forEach(([id,val])=>{
    const el=document.getElementById(id);if(!el)return;
    if(el.options.length!==dates.length)el.innerHTML=opts;
    if(val)el.value=val;
  });
  const ds=$('#salesSort');if(ds)ds.value=state.salesSort||'gp_desc';
  const ms=mNode('mPerfSort');if(ms)ms.value=state.salesSort||'gp_desc';
}
async function loadSell(){
  const err=$('#sellError');if(err)err.innerHTML='';
  const body=$('#sellRows');if(body)body.innerHTML='<tr><td colspan="8" class="loading">Loading range analysis...</td></tr>';
  try{
    await ensurePerformanceDates();
    if(!state.salesStartDate||!state.salesEndDate)throw new Error('No supported Performance dates are available.');
    if(state.salesStartDate>state.salesEndDate)throw new Error('Start Date must be on or before End Date.');
    const d=await api('/v1/app/v2/performance/range?start_date='+encodeURIComponent(state.salesStartDate)+'&end_date='+encodeURIComponent(state.salesEndDate)+'&limit=1000');
    state.salesRange=d;state.salesRows=d.items||[];
    state.salesStartDate=d.start_date||state.salesStartDate;state.salesEndDate=d.end_date||state.salesEndDate;
    syncPerformanceDateControls();
    const s=d.summary||{};
    if($('#sellKpi'))$('#sellKpi').innerHTML=
      '<div class="kpi"><small>Date Range</small><b>'+esc(d.start_date||'—')+' → '+esc(d.end_date||'—')+'</b><span>'+fmt(d.supported_day_count,0)+' completed canonical data days</span></div>'+
      '<div class="kpi"><small>Sales</small><b>'+money(s.sales_dollars)+'</b><span>All Seafood · selected range</span></div>'+
      '<div class="kpi"><small>GP$</small><b>'+money(s.gp_dollars)+'</b><span>'+(s.gp_dollars_complete?'Historical applicable cost':'Some item GP$ unavailable due to missing cost')+'</span></div>'+
      '<div class="kpi"><small>Items Sold</small><b>'+fmt(s.sold_item_count,0)+'</b><span>'+fmt(s.ready_item_count,0)+' READY · '+fmt(s.qa_hold_item_count,0)+' QA HOLD</span></div>';
    renderSales();
    state.salesLastError='';
    return true;
  }catch(e){
    state.salesLastError=e.message||String(e);
    if(err)err.innerHTML='<div class="error">'+esc(state.salesLastError)+'</div>';
    if(body)body.innerHTML='';
    return false;
  }
}
function filteredSalesRows(){
  const rows=[...state.salesRows],s=state.salesSort||'gp_desc';
  const n=v=>Number(v??0),nullable=v=>(v===null||v===undefined||v===''?-Infinity:Number(v));
  if(s==='gp_desc')rows.sort((x,y)=>nullable(y.gp_dollars)-nullable(x.gp_dollars));
  if(s==='velocity_desc')rows.sort((x,y)=>n(y.velocity)-n(x.velocity));
  if(s==='sales_desc')rows.sort((x,y)=>n(y.sales_amount)-n(x.sales_amount));
  if(s==='qty_desc')rows.sort((x,y)=>n(y.sold_quantity)-n(x.sold_quantity));
  if(s==='gp_pct_desc')rows.sort((x,y)=>nullable(y.gp_pct)-nullable(x.gp_pct));
  if(s==='price_desc')rows.sort((x,y)=>n(y.avg_sold_price)-n(x.avg_sold_price));
  if(s==='name')rows.sort((x,y)=>String(x.name||'').localeCompare(String(y.name||'')));
  return rows;
}
function renderSales(){
  const rows=filteredSalesRows();
  if($('#salesCount'))$('#salesCount').textContent=rows.length+' items';
  const rowHtml=(r,cls='')=>'<tr class="'+cls+'"><td><div class="name">'+esc(r.name||'—')+'</div><div class="meta">Family '+esc(r.family_article_number||'—')+'</div></td>'+
    '<td>'+esc(r.upc||'—')+'</td>'+
    '<td>'+fmt(r.sold_quantity)+' '+esc(r.qty_uom||'')+'</td>'+
    '<td><b>'+fmt(r.velocity)+'</b><div class="meta">'+esc(r.qty_uom||'unit')+'/data day</div></td>'+
    '<td>'+money(r.sales_amount)+'</td>'+
    '<td><b>'+money(r.gp_dollars)+'</b><div class="meta">'+(r.gp_cost_complete?'historical cost complete':'cost unavailable on sold day(s)')+'</div></td>'+
    '<td>'+pct(r.gp_pct)+'</td>'+
    '<td>'+money(r.avg_sold_price)+'</td></tr>';
  if($('#sellRows'))$('#sellRows').innerHTML=subgroup240249Units(rows).map(unit=>{
    if(unit.type!=='pair')return rowHtml(unit.row);
    const fam=unit.rows[0]?.family_article_number||'—';
    return '<tr class="pair-subgroup-head"><td colspan="8">240 / 249 SUBGROUP · Family '+esc(fam)+'</td></tr>'+
      rowHtml(unit.rows[0],'pair-subgroup-main')+rowHtml(unit.rows[1],'pair-subgroup-service');
  }).join('')||'<tr><td colspan="8" class="empty">No sales in the selected analysis range.</td></tr>';
}
$('#salesSort').onchange=e=>{state.salesSort=e.target.value;renderSales();mobileRenderList()};
$('#salesApplyRange').onclick=async()=>{state.salesStartDate=$('#salesStartDate').value;state.salesEndDate=$('#salesEndDate').value;await loadSell()};
$('#salesStartDate').onchange=e=>{state.salesStartDate=e.target.value};
$('#salesEndDate').onchange=e=>{state.salesEndDate=e.target.value};

async function loadOrders(){
  const err=$('#orderError');err.innerHTML='';state.orderLoadError='';state.orderHealth=null;
  $('#orderRows').innerHTML='<tr><td colspan="9" class="loading">Loading...</td></tr>';
  try{
    // FRESH and FROZEN are independent workloads. Loading them concurrently
    // avoids making the mobile ALL view wait for two heavyweight reviews in sequence.
    const [fresh,frozen]=await Promise.all([
      api('/v1/backoffice/ordering-review?category=FRESH',{timeoutMs:30000}),
      api('/v1/backoffice/ordering-review?category=FROZEN',{timeoutMs:30000})
    ]);
    const health=fresh.data_health||frozen.data_health||{};
    const blocked=[fresh,frozen].some(x=>String(x.analysis_status||'').toUpperCase()==='BLOCKED_STALE_REQUIRED_DATA');
    const skipped={};
    [fresh.skipped_breakdown||{},frozen.skipped_breakdown||{}].forEach(m=>Object.entries(m).forEach(([k,v])=>skipped[k]=(skipped[k]||0)+Number(v||0)));
    state.orderHealth={
      blocked,
      analysisStatus:blocked?'BLOCKED_STALE_REQUIRED_DATA':'CURRENT',
      expectedThrough:health.expected_through||null,
      posThrough:health.pos_data_through||null,
      movementThrough:health.movement_data_through||null,
      missing:health.missing_required_sources||[],
      skipped
    };
    state.orders=blocked?[]:[...(fresh.rows||[]),...(frozen.rows||[])];
    renderOrders()
  }catch(e){
    state.orderLoadError=e.message||'Unable to load ordering review';
    err.innerHTML=`<div class="error">${esc(state.orderLoadError)}</div>`;
    $('#orderRows').innerHTML='';
    if(isMobileBackoffice())throw e
  }
}
function orderRows(){let a=[...state.orders];if(state.orderFilter==='FRESH')a=a.filter(x=>String(x.category).toUpperCase()==='FRESH');if(state.orderFilter==='FROZEN')a=a.filter(x=>String(x.category).toUpperCase()==='FROZEN');if(state.orderFilter==='ATTENTION')a=a.filter(x=>x.attention);const s=$('#orderSort').value;if(s==='suggested')a.sort((x,y)=>Number(y.suggested_delivery_qty||0)-Number(x.suggested_delivery_qty||0));if(s==='receipt')a.sort((x,y)=>String(y.last_receipt_date||'').localeCompare(String(x.last_receipt_date||'')));if(s==='oh')a.sort((x,y)=>Number(x.oh??1e18)-Number(y.oh??1e18));if(s==='frequency')a.sort((x,y)=>String(x.ordering_frequency||'').localeCompare(String(y.ordering_frequency||'')));if(s==='family')a.sort((x,y)=>String(x.family_name||'').localeCompare(String(y.family_name||'')));return a}
function renderOrders(){
  const h=state.orderHealth||{};
  if(h.blocked){
    $('#orderCount').textContent='BLOCKED';
    const missing=(h.missing||[]).join(' + ')||'POS / MVT';
    $('#orderRows').innerHTML=`<tr><td colspan="9" class="empty"><b>Ordering is blocked by stale required data.</b><br>Required through ${esc(h.expectedThrough||'—')} · POS through ${esc(h.posThrough||'—')} · MVT through ${esc(h.movementThrough||'—')}<br>Missing/currentness issue: ${esc(missing)}. Upload/finish ingestion for the missing completed day, then refresh.</td></tr>`;
    return
  }
  const a=orderRows();$('#orderCount').textContent=`${a.length} families`;$('#orderRows').innerHTML=a.map(r=>`<tr><td><div class="name">${esc(r.family_name||'—')}</div></td><td><b>${esc(r.receiving_article||'—')}</b></td><td><b>${esc(r.family_article||'—')}</b></td><td>${fmt(r.oh)} ${esc(r.oh_uom||'')}</td><td>${esc(r.last_receipt_date||'—')}</td><td><b>${fmt(r.last_receipt_qty_base)} ${esc(r.last_receipt_base_uom||'')}</b></td><td>${esc(r.ordering_frequency||'—')}</td><td><span class="suggest">${fmt(r.suggested_delivery_qty)} ${esc(r.suggested_delivery_uom||'')}</span></td><td><button class="btn small orderdetail" data-family="${esc(r.family_article)}">Details / Why?</button></td></tr>`).join('')||'<tr><td colspan="9" class="empty">No eligible families: none currently meet the Ordering rules.</td></tr>';$$('.orderdetail').forEach(b=>b.onclick=()=>openOrderDetail(b.dataset.family))
}
$$('.ordfilter').forEach(b=>b.onclick=()=>{state.orderFilter=b.dataset.filter;$$('.ordfilter').forEach(x=>x.classList.toggle('on',x===b));renderOrders()});$('#orderSort').onchange=renderOrders;
function openOrderDetail(fam){const r=state.orders.find(x=>String(x.family_article)===String(fam));if(!r)return;const d=r.details||{},reasons=d.reasons||[], recArts=d.receiving_articles_on_last_receipt||[];openDrawer('Ordering Detail / Why?',`${r.family_name} · Family ${r.family_article}`,`<div class="detailgrid"><div class="detail"><small>Receiving Article</small><b>${esc(r.receiving_article||'—')}</b></div><div class="detail"><small>Family OH</small><b>${fmt(r.oh)} ${esc(r.oh_uom||'')}</b></div><div class="detail"><small>Last Receipt</small><b>${esc(r.last_receipt_date||'—')}</b></div><div class="detail"><small>Receipt Qty · Base</small><b>${fmt(r.last_receipt_qty_base)} ${esc(r.last_receipt_base_uom||'')}</b></div><div class="detail"><small>Family 7D Movement</small><b>${fmt(d.qty_7d)}</b></div><div class="detail"><small>Family 28D Movement</small><b>${fmt(d.qty_28d)}</b></div><div class="detail"><small>7D Velocity</small><b>${fmt(d.velocity_7d)}/day</b></div><div class="detail"><small>DOS</small><b>${fmt(d.dos)}</b></div></div><div class="sectiontitle">Why this suggestion?</div><div class="reasonlist">${reasons.map(x=>`<div class="reason"><span class="rdot"></span><div><b>${esc(x.title)}</b><span>${esc(x.detail)}</span></div></div>`).join('')}</div><div class="calc">Coming delivery suggestion ≈ expected family usage through coverage window − usable family OH + promotion/safety adjustment. Incoming is not used as a displayed Ordering Review field.</div>${recArts.length?`<div class="sectiontitle">Receiving Articles on Last Receipt</div><div class="reasonlist">${recArts.map(x=>`<div class="reason"><span class="rdot"></span><div><b>${esc(x.article_number)}</b><span>${fmt(x.quantity)} ${esc(x.base_uom||'')} · Base UOM</span></div></div>`).join('')}</div>`:''}`,`<span class="pill blue">READ ONLY</span>`)}

async function loadPrices(){
  const err=$('#priceError');
  err.innerHTML='';
  state.priceLoadError='';
  state.priceHealth=null;
  state.priceMeta=null;
  $('#priceRows').innerHTML='<tr><td colspan="12" class="loading">Loading...</td></tr>';
  try{
    const d=await api(`/v1/backoffice/pricing-review?category=${encodeURIComponent(state.priceCat)}&limit=1000`,{timeoutMs:30000});
    const h=d.data_health||{};
    state.priceHealth={
      blocked:String(h.status||'').toUpperCase()==='BLOCKED_STALE_REQUIRED_DATA',
      analysisStatus:String(h.status||'CURRENT').toUpperCase(),
      expectedThrough:h.expected_through||null,
      posThrough:h.pos_data_through||null,
      movementThrough:h.movement_data_through||null,
      missing:h.missing_required_sources||[]
    };
    state.priceMeta={
      suppressedAccepted:Number(d.suppressed_accepted_count||0),
      summary:d.summary||{},
      reportDate:d.report_date||null
    };
    state.prices=state.priceHealth.blocked?[]:(d.rows||[]);
    renderPrices();
    return d
  }catch(e){
    state.prices=[];
    state.priceLoadError=e.message||'Unable to load Price Change review';
    err.innerHTML=`<div class="error"><b>Price Change failed to load.</b><br>${esc(state.priceLoadError)}</div>`;
    $('#priceCount').textContent='ERROR';
    $('#priceRows').innerHTML='<tr><td colspan="12" class="empty">Pricing review could not be loaded. Refresh to retry.</td></tr>';
    return null
  }
}
function filteredPrices(){
  let a=[...state.prices];
  const status=String(state.priceStatus||'ALL').toUpperCase();
  const text=String(state.priceText||'').trim().toLowerCase();
  if(status!=='ALL')a=a.filter(r=>String(r.review_status||'').toUpperCase()===status);
  if(text)a=a.filter(r=>[r.name,r.upc,r.family_name,r.family_article_number,r.related_240_upc,r.related_240_name,r.related_249_upc,r.related_249_name,r.review_status,r.review_blocker,r.primary_reason_text,...(r.reasons||[])].join(' ').toLowerCase().includes(text));
  const sort=state.priceSort||'opportunity';
  if(sort==='opportunity')a.sort((x,y)=>Number(y.gp_per_day_opportunity||0)-Number(x.gp_per_day_opportunity||0)||Number(y.urgency_score||0)-Number(x.urgency_score||0));
  if(sort==='urgency')a.sort((x,y)=>Number(y.urgency_score||0)-Number(x.urgency_score||0)||Number(y.gp_per_day_opportunity||0)-Number(x.gp_per_day_opportunity||0));
  if(sort==='gap')a.sort((x,y)=>Number(y.price_gap_pct||0)-Number(x.price_gap_pct||0));
  if(sort==='qty7')a.sort((x,y)=>Number(y.qty_7d||0)-Number(x.qty_7d||0));
  if(sort==='qty28')a.sort((x,y)=>Number(y.qty_28d||0)-Number(x.qty_28d||0));
  if(sort==='lowgp')a.sort((x,y)=>Number(x.current_gp_pct_reference??999)-Number(y.current_gp_pct_reference??999));
  if(sort==='currentprice')a.sort((x,y)=>Number(y.current_price||0)-Number(x.current_price||0));
  if(sort==='name')a.sort((x,y)=>String(x.name||'').localeCompare(String(y.name||'')));
  // Mandatory 240≠249 violations always stay above every other pricing review.
  a.sort((x,y)=>Number(Boolean(y.priority_240_249_mismatch))-Number(Boolean(x.priority_240_249_mismatch)));
  return a;
}
function renderPrices(){
  const h=state.priceHealth||{};
  if(h.blocked){
    $('#priceCount').textContent='BLOCKED';
    const missing=(h.missing||[]).join(' + ')||'POS / MVT';
    $('#priceRows').innerHTML=`<tr><td colspan="12" class="empty"><b>Price Change is blocked by stale required data.</b><br>Required through ${esc(h.expectedThrough||'—')} · POS through ${esc(h.posThrough||'—')} · MVT through ${esc(h.movementThrough||'—')}<br>Missing/currentness issue: ${esc(missing)}. Upload/finish ingestion for the missing completed day, then refresh.</td></tr>`;
    return
  }
  const rows=filteredPrices();
  $('#priceCount').textContent=`${rows.length} shown · ${state.prices.length} loaded`;
  $('#priceRows').innerHTML=rows.map(r=>{
    const range=(r.company_range_low!==null&&r.company_range_low!==undefined)?money(r.company_range_low)+' – '+money(r.company_range_high):'No A/B/C';
    const rem=price249Reminder(r,false);
    const remClass=r.price_240_249_equal===false?'pair249 mismatch':'pair249';
    return `<tr>
      <td><div class="name">${esc(r.name)}</div><div class="meta">${esc(r.family_name||'')}</div>${pairPriceSummaryHtml(r)}${rem?'<div class="'+remClass+'">'+esc(rem)+'</div>':''}</td>
      <td><div class="name">${esc(r.upc)}</div><div class="meta">${esc(r.name||'')}</div></td>
      <td><b>${money(r.current_price)}</b><div class="meta">${esc(r.current_price_type||'—')} · ${esc(r.current_price_source||'—')}${r.current_price_observed_date?' · '+esc(r.current_price_observed_date):''}</div></td>
      <td><b>${money(r.candidate_price)}</b><div class="meta">${esc(r.selection_basis||r.suggestion_basis||'')}</div></td>
      <td><b>${fmt(r.current_oh)} ${esc(r.current_oh_uom||'')}</b><div class="meta">DOH ${fmt(r.doh)}</div></td>
      <td><b>${esc(range)}</b><div class="meta">${r.has_company_reference?'Candidate constrained':'No company constraint'}</div></td>
      <td><b>${money(r.current_cost)}</b><div class="meta">${esc(r.current_cost_source||r.cost_basis||'—')}${r.cost_date?' · '+esc(r.cost_date):''}</div></td>
      <td>${pct(r.current_gp_pct_reference)}</td><td>${fmt(r.qty_14d)}</td>
      <td>${r.priority_240_249_mismatch?'<span class="pill red">MOST URGENT · 240≠249</span>':pill(r.review_status)}</td>
      <td><div class="meta" style="max-width:240px">${esc(r.primary_reason_text||r.review_blocker||'Pricing review')}</div></td>
      <td><div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn small pricedetail" data-upc="${esc(r.upc)}">Why?</button>${String(r.review_status||"").toUpperCase()==="ACTIONABLE"&&r.current_price!==null&&r.current_price!==undefined&&r.candidate_price!==null&&r.candidate_price!==undefined?`<button class="btn small primary priceaccept" data-upc="${esc(r.upc)}">Accepted</button>`:""}</div></td>
    </tr>`;
  }).join('')||`<tr><td colspan="12" class="empty"><b>No qualified price changes in the current snapshot.</b>${Number(state.priceMeta?.suppressedAccepted||0)?'<br>'+esc(state.priceMeta.suppressedAccepted)+' accepted suggestion(s) remain suppressed until price evidence or the candidate changes.':''}</td></tr>`;
  $$('.pricedetail').forEach(b=>b.onclick=()=>openPriceDetail(b.dataset.upc));
  $$('.priceaccept').forEach(b=>b.onclick=()=>acceptPriceSuggestion(b.dataset.upc,b));
}

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
async function loadPriceDetail7d(upc){
  const box=mNode('priceDetail7d');if(!box)return;
  try{
    const d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc)+'/price?trend_supported_days=7');
    const trend=d.price_vs_sales_trend||{},rows=trend.rows||[];
    box.innerHTML=
      '<div class="m-detailcard m-trendcard">'+
        '<div class="m-label">Past 7 Data Days · Sales History & Trend</div>'+
        '<div class="m-chartnote">Same view as Quick Check · completed canonical POS data days only · missing source dates are not zeros</div>'+
        mobileQuickTrendSvg(rows)+
        '<div class="m-detailsection"><h3>Daily Sales History</h3>'+mobileQuick7dHistoryHtml(rows,d.qty_uom||trend.qty_uom)+'</div>'+
      '</div>';
  }catch(e){
    box.innerHTML='<div class="m-error">7-day history unavailable: '+esc(e.message||String(e))+'</div>';
  }
}
function openPriceDetail(upc){
  const r=state.prices.find(x=>String(x.upc)===String(upc));if(!r)return;
  const company=[['A',r.company_price_a],['B',r.company_price_b],['C',r.company_price_c]].filter(x=>x[1]!==null&&x[1]!==undefined);
  const companyText=company.length?company.map(x=>x[0]+' '+money(x[1])).join(' · '):'No Company A/B/C reference';
  const rangeText=(r.company_range_low!==null&&r.company_range_low!==undefined)?money(r.company_range_low)+' – '+money(r.company_range_high):'—';
  const rem=price249Reminder(r,false);
  const pairBlock=r.related_249_present
    ? '<div class="sectiontitle">240 / 249 Price Rule</div>'+
      '<div class="'+(r.price_240_249_equal===false?'pair249 mismatch':'pair249')+'">'+esc(rem)+'</div>'+
      '<div class="detailgrid" style="margin-top:8px">'+
        '<div class="detail"><small>240 Main UPC</small><b>'+esc(r.related_240_upc||'—')+' · '+money(r.related_240_current_price)+'</b><span>'+esc(r.related_240_current_price_type||'—')+' · '+esc(r.related_240_current_price_source||'—')+(r.related_240_current_price_asof_date?' · '+esc(r.related_240_current_price_asof_date):'')+'</span></div>'+
        '<div class="detail"><small>249 Cook / Service UPC</small><b>'+esc(r.related_249_upc||'—')+' · '+money(r.related_249_current_price)+'</b><span>'+esc(r.related_249_current_price_type||'—')+' · '+esc(r.related_249_current_price_source||'—')+(r.related_249_current_price_asof_date?' · '+esc(r.related_249_current_price_asof_date):'')+'</span></div>'+
      '</div>'+
      (r.related_249_required_price!==null&&r.related_249_required_price!==undefined
        ? '<div class="calc"><b>Reminder:</b> 249 must be '+money(r.related_249_required_price)+' when this price change is accepted.</div>'
        : '')
    : '';
  const ruleText=r.priority_240_249_mismatch
    ? 'Mandatory rule: related 240 main and 249 cook/service UPC prices must be equal. This mismatch is ranked above all other price suggestions.'
    : (r.clearance_reason==='FROZEN_DOH_GT_60'
      ? 'Frozen DOH > 60: qualified price review. Candidate maximizes supported 14D GP$/day; Company A/B/C range is enforced when available.'
      : (r.clearance_due_to_doh
        ? 'Fresh DOH > 7: qualified price review. Candidate maximizes supported 14D GP$/day; Company A/B/C range is enforced when available.'
        : (r.has_company_reference
          ? 'Qualified stocked item: candidate maximizes 14D GP$/day and must stay inside the Company A/B/C range.'
          : 'Qualified stocked item with no Company A/B/C: candidate maximizes 14D GP$/day from observed sales history.')));
  openDrawer(
    'Price Suggestion Explanation',
    `${r.name} · UPC ${r.upc}`,
    '<div class="detailgrid">'+
      '<div class="detail"><small>Current Price</small><b>'+money(r.current_price)+'</b><span>'+esc(r.current_price_type||'—')+' · '+esc(r.current_price_source||'—')+(r.current_price_observed_date?' · '+esc(r.current_price_observed_date):'')+'</span></div>'+
      '<div class="detail"><small>Candidate Price</small><b>'+money(r.candidate_price)+'</b><span>'+esc(r.selection_basis||r.suggestion_basis||'')+'</span></div>'+
      '<div class="detail"><small>Current Cost</small><b>'+money(r.current_cost)+'</b><span>'+esc(r.current_cost_source||r.cost_basis||'—')+(r.cost_date?' · '+esc(r.cost_date):'')+'</span></div>'+
      '<div class="detail"><small>Current GP%</small><b>'+pct(r.current_gp_pct_reference)+'</b></div>'+
      '<div class="detail"><small>Candidate GP%</small><b>'+pct(r.suggested_gp_pct_at_current_cost)+'</b></div>'+
      '<div class="detail"><small>Company A/B/C</small><b>'+esc(companyText)+'</b><span>Range: '+esc(rangeText)+'</span></div>'+
      '<div class="detail"><small>DOH</small><b>'+fmt(r.doh)+'</b><span>'+(r.clearance_due_to_doh?'Clearance mode':'Standard pricing mode')+'</span></div>'+
      '<div class="detail"><small>14D Qty</small><b>'+fmt(r.qty_14d)+'</b></div>'+
      '<div class="detail"><small>7D Velocity</small><b>'+fmt(r.velocity_7d)+'</b></div>'+
      '<div class="detail"><small>14D Velocity</small><b>'+fmt(r.velocity_14d)+'</b></div>'+
      '<div class="detail"><small>GP$/Day Current</small><b>'+money(r.current_gp_per_day_7d)+'</b></div>'+
      '<div class="detail"><small>GP$/Day Candidate</small><b>'+money(r.candidate_expected_gp_per_day)+'</b></div>'+
    '</div>'+
    pairBlock+
    '<div class="sectiontitle">Primary reason</div><div class="calc">'+esc(r.primary_reason_text||'Pricing review')+'</div>'+
    '<div class="sectiontitle">Rule used</div><div class="calc">'+esc(ruleText)+'</div>'+
    '<div class="calc">Current Price and Current Cost come from the live Quick Check serving row. Pricing Review is read-only.</div>'+
    '<div id="priceDetail7d" class="m-quick7d"><div class="m-loading">Loading 7-day sales history…</div></div>',
    '<span class="pill blue">READ ONLY</span>'
  );
  loadPriceDetail7d(r.upc);
}


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
async function boot(){await loadHealth().catch(()=>{});if(isMobileBackoffice()){await mobileRestoreCurrentRoute()}else restoreRoute({replaceMissing:true});setInterval(()=>{if(!document.hidden&&!isMobileBackoffice()&&$('#database').classList.contains('on')){const current=$('#database .subview.on');if(current?.id==='dboverview'){loadDatabaseOverview();loadBatches()}}},15000)}boot();
})();
</script>
</body></html>'''
