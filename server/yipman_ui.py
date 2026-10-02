from __future__ import annotations

import json


def yipman_html(version: str = "") -> str:
    return YIPMAN_HTML.replace("__VERSION__", str(version or ""))


def yipman_manifest() -> str:
    return json.dumps({
        "name": "Yipman",
        "short_name": "Yipman",
        "id": "/app/yipman",
        "start_url": "/app/yipman",
        "scope": "/app/yipman/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "background_color": "#f6f7f9",
        "theme_color": "#0d4f8b",
        "description": "FULL MYSQL seafood mobile operations",
        "icons": [{
            "src": "/app/yipman/icon.svg",
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable",
        }],
    }, separators=(",", ":"))


def yipman_service_worker() -> str:
    return r"""
const CACHE='yipman-v361';
const SHELL=['/app/yipman','/app/yipman/manifest.webmanifest','/app/yipman/icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  if(u.pathname.startsWith('/v1/'))return;
  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/app/yipman'))));
});
"""


def yipman_icon_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="112" fill="#0d4f8b"/><path d="M0 382h512v130H0z" fill="#d62828"/><path d="M143 112h72l43 91 43-91h70l-81 151v104h-66V263z" fill="#fff"/></svg>"""


YIPMAN_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#0d4f8b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Yipman">
<link rel="manifest" href="/app/yipman/manifest.webmanifest">
<link rel="icon" href="/app/yipman/icon.svg" type="image/svg+xml">
<title>Yipman</title>
<style>
:root{--bg:#f6f7f9;--paper:#fff;--ink:#16202a;--muted:#71808d;--line:#e1e6ea;--blue:#0d4f8b;--blue2:#1d6fb8;--red:#d62828;--redbg:#fff0f0;--green:#25734a;--greenbg:#edf8f2;--amber:#966700;--amberbg:#fff8e5;--ambersoft:#fff8e5;--shadow:0 9px 25px rgba(18,38,56,.08)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;overscroll-behavior-y:contain}
body{overflow:hidden}button,input{font:inherit;color:inherit}button{cursor:pointer}.hide{display:none!important}
#app{height:100%;position:relative;overflow:hidden;padding-top:env(safe-area-inset-top,0px)}
@media (display-mode:standalone),(display-mode:fullscreen){#app{padding-top:env(safe-area-inset-top,0px)}}
.header{padding:9px 13px 10px}.head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.brand{font-size:21px;font-weight:950;letter-spacing:-.04em}.brand span{color:var(--blue)}.ver{display:block;font-size:9px;color:var(--muted);font-weight:700;margin-top:1px}
.dbbtn{width:40px;height:40px;border:0;border-radius:14px;background:#fff;box-shadow:var(--shadow);font-size:18px}
.search{display:flex;align-items:center;margin-top:9px;background:#fff;border:1px solid var(--line);border-radius:15px;padding:0 10px;box-shadow:0 4px 15px rgba(18,38,56,.04)}
.search span{font-size:17px;color:#657581}.search input{flex:1;min-width:0;border:0;outline:0;background:transparent;padding:11px 8px;font-size:16px}
.workspace{height:calc(100% - 99px);position:relative;overflow:hidden}.page{display:none;height:100%;overflow-y:auto;padding:0 11px calc(82px + env(safe-area-inset-bottom));scrollbar-width:none}.page::-webkit-scrollbar{display:none}.page.on{display:block}
#home{overflow:hidden}.topline{display:flex;justify-content:space-between;align-items:end;margin:0 1px 7px}.topline h2{font-size:18px;margin:0}.hint{font-size:9px;color:var(--muted);font-weight:850}
.hero{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;border-radius:18px;padding:11px 12px;box-shadow:var(--shadow)}.hero small{font-size:8px;font-weight:900;letter-spacing:.08em;opacity:.8}.hero h3{font-size:18px;margin:3px 0 2px}.hero p{font-size:9px;line-height:1.25;margin:0;opacity:.85}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px}.stat{padding:7px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.11);border-radius:10px}.stat b{display:block;font-size:15px}.stat span{font-size:7px;opacity:.8}
.launch{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.launch button{min-height:86px;border:0;border-radius:15px;background:#fff;padding:9px 10px;text-align:left;box-shadow:var(--shadow)}.launch button:nth-child(2),.launch button:nth-child(3){background:linear-gradient(180deg,#fff7f7,#fff)}.launch i{font-style:normal;font-size:17px}.launch b{display:block;font-size:13px;margin-top:5px}.launch span{display:block;font-size:8px;color:var(--muted);margin-top:2px}.launch em{display:block;font-style:normal;font-size:7px;font-weight:900;color:var(--blue);margin-top:5px}
.priority{margin-top:8px;background:#fff;border-radius:15px;box-shadow:var(--shadow);overflow:hidden}.priority .ph{display:flex;justify-content:space-between;padding:7px 10px;border-bottom:1px solid var(--line);font-size:8px;font-weight:900;color:#53616d}.prio{display:grid;grid-template-columns:1fr auto;gap:8px;padding:8px 10px;border-bottom:1px solid var(--line)}.prio:last-child{border:0}.prio b{font-size:11px}.prio span{display:block;font-size:8px;color:var(--muted);margin-top:2px}
.badge{align-self:center;border-radius:999px;padding:4px 6px;font-size:7px;font-weight:900}.red{background:var(--redbg);color:var(--red)}.amber{background:var(--amberbg);color:var(--amber)}.green{background:var(--greenbg);color:var(--green)}
.search2{display:grid;grid-template-columns:1fr 70px;gap:6px;margin-bottom:8px}.search2 input{border:1px solid var(--line);background:#fff;border-radius:13px;padding:10px 11px;font-size:16px;outline:0}.search2 button{border:0;background:var(--blue);color:#fff;border-radius:13px;font-size:9px;font-weight:900}
.group{background:#fff;border-radius:16px;box-shadow:var(--shadow);overflow:hidden;margin-bottom:8px}.ghead{display:flex;justify-content:space-between;gap:8px;padding:11px 12px;background:#fafbfc}.ghead b{font-size:14px}.ghead small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.gmetric{text-align:right;font-size:12px;font-weight:900}.gmetric span{display:block;font-size:7px;color:var(--muted)}
.upc{display:grid;grid-template-columns:1fr auto;gap:8px;padding:10px 12px;border-top:1px solid var(--line)}.upc b{font-size:11px}.upc small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.upcv{text-align:right;font-size:10px;font-weight:900}
.qfamily{background:#fff;border-radius:17px;box-shadow:var(--shadow);overflow:hidden;margin-bottom:10px;border:1px solid #e7ebee}
.qfhead{display:grid;grid-template-columns:1fr auto;gap:10px;padding:11px 12px;background:linear-gradient(90deg,#fff8d9,#fffdf4);border-bottom:1px solid #eee5bd}
.qfamily:nth-child(6n+2) .qfhead{background:linear-gradient(90deg,#edf8ef,#f9fdf9)}.qfamily:nth-child(6n+3) .qfhead{background:linear-gradient(90deg,#eef6fd,#fafcff)}.qfamily:nth-child(6n+4) .qfhead{background:linear-gradient(90deg,#fff0f4,#fffafb)}.qfamily:nth-child(6n+5) .qfhead{background:linear-gradient(90deg,#f3efff,#fcfbff)}
.qlabel{font-size:7px;font-weight:950;letter-spacing:.08em;color:#7a6a28}.qfnum{font-size:16px;font-weight:950;line-height:1.05;margin-top:2px}.qfname{font-size:12px;font-weight:900;margin-top:4px;line-height:1.15}.qmeta{font-size:7px;color:var(--muted);font-weight:750;margin-top:3px}
.qfkpis{display:grid;grid-template-columns:1fr 1fr;gap:5px;align-content:start}.qkpi{text-align:right}.qkpi small{display:block;font-size:6px;color:var(--muted);font-weight:900}.qkpi b{font-size:12px}
.qsource{border-top:1px solid var(--line)}
.qrecv{margin:7px 8px 8px;border:1px solid #dfe5e9;border-left:4px solid #7c91a3;border-radius:13px;overflow:hidden;background:#fbfcfd}.qrecv.receipt{border-left-color:var(--red)}.qrecv.mvt{border-left-color:var(--blue)}
.qrecvhead{display:grid;grid-template-columns:1fr auto;gap:8px;padding:8px 9px;background:#f4f7f9;border-bottom:1px solid var(--line)}.qrecvrole{font-size:6px;font-weight:950;letter-spacing:.06em;color:#63717c}.qrecvnum{font-size:13px;font-weight:950;margin-top:2px}.qrecvname{font-size:9px;font-weight:800;margin-top:2px}.qreceipt{display:inline-flex;margin-left:4px;width:17px;height:17px;border-radius:50%;align-items:center;justify-content:center;background:#9e1f24;color:#fff;font-size:10px;font-weight:950;vertical-align:middle}
.qrecvkpis{display:grid;grid-template-columns:1fr 1fr;gap:5px}.qrecvkpi{text-align:right}.qrecvkpi small{display:block;font-size:6px;color:var(--muted);font-weight:900}.qrecvkpi b{font-size:11px}
.qupc{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px 10px;border-top:1px solid var(--line);background:#fff}.qupc:first-child{border-top:0}.qupcmain{min-width:0}.qupctop{display:flex;align-items:center;gap:5px;min-width:0}.qrole{font-size:6px;font-weight:950;padding:3px 5px;border-radius:999px;background:#edf2f6;color:#4b6171;white-space:nowrap}.qrole.main{background:#e9f3ff;color:var(--blue)}.qrole.service{background:#fff0f0;color:var(--red)}.qupccode{font-size:8px;color:var(--muted);font-weight:850;overflow:hidden;text-overflow:ellipsis}.qupcname{font-size:11px;font-weight:900;margin-top:4px;line-height:1.12}.qupcmetrics{text-align:right;white-space:nowrap}.qupcmetrics b{font-size:11px}.qupcmetrics span{display:block;font-size:7px;color:var(--muted);margin-top:2px}.qready{font-size:7px;font-weight:900;color:var(--green)}
.qhidebtn{width:100%;border:0;background:#f5f7f9;color:#5c6974;padding:7px 10px;text-align:left;font-size:8px;font-weight:900;border-top:1px solid var(--line)}.qhidden{display:none}.qhidden.on{display:block}.qhiddennote{font-size:7px;color:var(--muted);padding:6px 10px;background:#fafbfc;border-top:1px solid var(--line)}
.empty{background:#fff;border-radius:16px;padding:20px;text-align:center;font-size:10px;color:var(--muted);box-shadow:var(--shadow)}
.daybar{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px;margin-bottom:8px}.daybar::-webkit-scrollbar{display:none}.day{min-width:49px;border:0;border-radius:14px;background:#fff;padding:8px 4px;box-shadow:0 4px 12px rgba(18,38,56,.05);text-align:center}.day b{display:block;font-size:8px;color:var(--muted)}.day strong{display:block;font-size:17px;margin-top:1px}.day span{display:block;font-size:7px;color:var(--muted)}.day.on{background:var(--blue);color:#fff}.day.on b,.day.on span{color:#dbeafa}
.order-tools{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:center;margin:0 0 8px}.order-summary{font-size:8px;font-weight:900;color:#52616d;line-height:1.25}.order-controls{display:flex;gap:5px}.order-controls label{display:grid;gap:2px;font-size:6px;font-weight:950;color:var(--muted);letter-spacing:.04em}.order-controls select{border:1px solid var(--line);background:#fff;border-radius:9px;padding:5px 20px 5px 7px;font-size:8px;font-weight:900;color:#263743;max-width:118px}
.list{background:#fff;border-radius:16px;box-shadow:var(--shadow);overflow:hidden}.lh,.orow{display:grid;grid-template-columns:1fr 58px 64px;padding:0 11px}.lh{background:#eef2f5;padding-top:8px;padding-bottom:8px;font-size:7px;font-weight:900;color:#5d6974}.orow{border-top:1px solid var(--line)}.orow>div{padding:10px 0}.orow .name{font-size:11px;font-weight:900}.orow .sub{font-size:7px;color:var(--muted);margin-top:2px}.cell{text-align:right;font-size:11px;font-weight:900}.cell span{display:block;font-size:7px;color:var(--muted)}.orow.urgent{box-shadow:inset 4px 0 0 var(--red)}.orow.review{box-shadow:inset 4px 0 0 #d19a00}.orow.zero{box-shadow:inset 4px 0 0 #9aa6af}.orderstate{display:inline-flex;margin-left:4px;padding:2px 5px;border-radius:999px;background:#edf2f6;color:#5b6873;font-size:6px;font-weight:950;vertical-align:1px}.orderstate.order{background:#e8f6ee;color:#167648}.orderstate.review{background:#fff4d6;color:#805d00}.rtrace{display:grid;gap:4px;margin-top:6px}.rtrace-line{display:flex;align-items:center;gap:4px;min-width:0;font-size:8px;font-weight:950;line-height:1.15}.rpo,.rgr{display:inline-flex;align-items:center;max-width:46%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-radius:7px;padding:4px 5px;border:1px solid}.rpo{background:var(--amberbg);border-color:#ecd99f;color:#775500}.rgr{background:var(--greenbg);border-color:#cbe6d6;color:var(--green)}.rgr.unresolved{background:var(--redbg);border-color:#efcaca;color:var(--red)}.rtrace-arrow{color:#91a0ab;font-weight:950;flex:0 0 auto}.rtrace-more{font-size:7px;color:var(--muted);font-weight:850}.receipt-event{padding:8px 0;border-top:1px solid var(--line)}.receipt-event:first-child{border-top:0}.receipt-pair{font-weight:950;color:#263743}.receipt-meta{font-size:9px;color:var(--muted);margin-top:2px}
.filters{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;margin-bottom:8px}.filters::-webkit-scrollbar{display:none}.pill{border:0;border-radius:999px;background:#fff;padding:7px 10px;font-size:8px;font-weight:900;color:#5e6a75;white-space:nowrap}.pill.on{background:#1f2c38;color:#fff}
.pricecards{display:grid;gap:7px}.pcard{background:#fff;border-radius:16px;padding:11px 12px;box-shadow:var(--shadow)}.ptop{display:flex;justify-content:space-between;gap:8px}.ptop b{font-size:12px}.ptop small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.compare{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:7px;margin-top:9px}.pbox{background:#f5f7f9;border-radius:11px;padding:8px}.pbox b{font-size:16px}.pbox span{display:block;font-size:7px;color:var(--muted)}.arrow{font-size:15px;font-weight:900;color:#98a3ac}.why{font-size:8px;line-height:1.35;color:#5d6974;margin-top:8px}
.datagrid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.dcard{background:#fff;border-radius:16px;padding:10px;box-shadow:var(--shadow)}.dcard h3{font-size:10px;margin:0 0 7px}.pipe{display:grid;grid-template-columns:repeat(4,1fr);gap:3px}.stage{padding:6px 2px;text-align:center;background:#f1f4f6;border-radius:8px;border-top:4px solid #8d99a3}.stage b{display:block;font-size:6px}.stage span{font-size:6px;color:var(--muted)}.stage.ok{border-top-color:var(--green)}.stage.warn{border-top-color:#d19a00}.stage.bad{border-top-color:var(--red)}.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.c{text-align:center;font-size:7px}.dot{width:12px;height:12px;border-radius:50%;background:var(--green);margin:3px auto 0}.dot.warn{background:#d19a00}.dot.bad{background:var(--red)}.batchrow{display:grid;grid-template-columns:1fr auto;gap:6px;padding:8px 0;border-top:1px solid var(--line)}.batchrow b{font-size:9px}.batchrow span{display:block;font-size:7px;color:var(--muted);margin-top:2px}
.nav{position:absolute;left:10px;right:10px;bottom:calc(9px + env(safe-area-inset-bottom));height:57px;display:grid;grid-template-columns:repeat(4,1fr);background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:18px;box-shadow:0 9px 24px rgba(18,38,56,.12);backdrop-filter:blur(10px);z-index:10}.nav button{border:0;background:transparent;color:#73808a;font-size:7px;font-weight:850}.nav i{display:block;font-style:normal;font-size:16px;margin-bottom:2px}.nav button.on{color:var(--blue)}
.overlay{position:absolute;inset:0;background:rgba(15,25,34,.34);display:none;align-items:flex-end;z-index:30}.overlay.on{display:flex}.sheet{width:100%;max-height:68%;overflow:auto;background:#f7f8fa;border-radius:23px 23px 0 0}.shead{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:12px 13px;display:flex;justify-content:space-between;gap:8px;border-radius:23px 23px 0 0}.shead h3{font-size:17px;margin:0}.shead p{font-size:8px;color:var(--muted);margin:2px 0 0}.close{width:34px;height:34px;border:0;border-radius:11px;background:#eef1f3;font-size:17px}.sbody{padding:9px 11px 13px}.dmetrics{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.dm{background:#fff;border-radius:12px;padding:9px}.dm b{font-size:14px;display:block}.dm span{font-size:7px;color:var(--muted)}.detail{background:#fff;border-radius:12px;padding:9px;margin-top:6px;font-size:9px;line-height:1.4;color:#53616d}.actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:7px}.actions button{border:0;border-radius:11px;padding:9px;font-size:8px;font-weight:900}.primary{background:var(--blue);color:#fff}.secondary{background:#e6ebef;color:#2f3e49}
.toast{position:absolute;left:12px;right:12px;bottom:76px;background:#1f2d39;color:#fff;padding:9px 11px;border-radius:13px;font-size:9px;font-weight:850;display:none;z-index:40}.toast.on{display:block}
.ptr{position:absolute;left:0;right:0;top:0;height:0;overflow:hidden;z-index:50;display:flex;align-items:flex-end;justify-content:center;pointer-events:none}.ptr div{background:#fff;border:1px solid var(--line);box-shadow:var(--shadow);border-radius:999px;padding:6px 10px;margin-bottom:6px;font-size:9px;font-weight:900;color:var(--blue)}
.loading{padding:18px;text-align:center;color:var(--muted);font-size:9px}
@media(max-height:760px){#home .hero p{display:none}.launch button{min-height:74px}.launch button span{display:none}.priority .prio:nth-child(n+4){display:none}}

/* V328 readability: user-facing text is ~25-30% larger, with compact spacing retained. */
.brand{font-size:27px}.ver{font-size:12px}.dbbtn{width:44px;height:44px;font-size:22px}
.search input{font-size:20px;padding:12px 9px}.search span{font-size:21px}
.topline h2{font-size:24px}.hint{font-size:12px}
.hero small{font-size:10px}.hero h3{font-size:23px}.hero p{font-size:12px}.stat b{font-size:19px}.stat span{font-size:9px}
.launch i{font-size:21px}.launch b{font-size:17px}.launch span{font-size:10px}.launch em{font-size:9px}
.priority .ph{font-size:10px}.prio b{font-size:14px}.prio span{font-size:10px}.badge{font-size:9px;padding:5px 8px}
.search2 input{font-size:20px}.search2 button{font-size:12px}
.qlabel{font-size:9px}.qfnum{font-size:20px}.qfname{font-size:15px}.qmeta{font-size:9px}.qkpi small{font-size:8px}.qkpi b{font-size:15px}
.qrecvrole{font-size:8px}.qrecvnum{font-size:17px}.qrecvname{font-size:12px}.qrecvkpi small{font-size:8px}.qrecvkpi b{font-size:14px}
.qrole{font-size:8px}.qupccode{font-size:10px}.qupcname{font-size:14px}.qupcmetrics b{font-size:14px}.qupcmetrics span,.qready{font-size:9px}.qhidebtn{font-size:10px}.qhiddennote{font-size:9px}
.day b{font-size:10px}.day strong{font-size:21px}.day span{font-size:9px}.day.past{opacity:.72}.day.today{outline:2px solid rgba(13,79,139,.28);outline-offset:1px}
.order-tabs{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:8px}.order-tab{border:1px solid var(--line);background:#fff;border-radius:13px;padding:10px 7px;font-size:11px;font-weight:950}.order-tab.on{background:#142033;color:#fff;border-color:#142033}
.order-date-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:7px}.order-date-card{border:2px solid #d8e0e6;background:#fff;border-radius:14px;padding:8px 9px;text-align:left}.order-date-card small{display:block;font-size:7px;color:var(--muted);font-weight:950}.order-date-card b{display:block;font-size:15px;margin-top:2px}.order-date-card span{display:block;font-size:7px;color:var(--green);font-weight:900;margin-top:2px}.order-date-card.delivery{border-color:#3b82f6;background:#eff6ff}.order-date-card.next{border-color:#8b5cf6;background:#f5f3ff}.order-date-card.pick{box-shadow:0 0 0 2px rgba(17,24,39,.12)}
.day.observed{background:#eef9f2;border:1px solid #b9e4c8}.day.observed span{color:#23784d}.day.preferred{background:#def6e7;border:2px solid #70ca94}.day.preferred span{color:#17683c;font-weight:950}.day.delivery{background:#2563eb;color:#fff;outline:2px solid #2563eb}.day.delivery b,.day.delivery span{color:#dbeafe}.day.next{background:#7c3aed;color:#fff;outline:2px solid #7c3aed}.day.next b,.day.next span{color:#ede9fe}
.order-risk{display:inline-block;margin-left:5px;border-radius:999px;padding:2px 5px;font-size:6px;font-weight:950;background:#ffe7e7;color:#a12424}.order-lowconf{display:inline-block;margin-left:4px;border-radius:999px;padding:2px 5px;font-size:6px;font-weight:950;background:#fff4d8;color:#855d00}.order-coverage{background:#142033;color:#fff;border-radius:13px;padding:8px 10px;margin:0 0 8px}.order-coverage small{display:block;font-size:7px;color:#b8c4d2;font-weight:950}.order-coverage b{display:block;font-size:16px;margin-top:2px}.order-coverage span{display:block;font-size:8px;color:#ccd6e2;margin-top:2px}
.promo-shell{background:#fff;border-radius:16px;box-shadow:var(--shadow);padding:13px}.promo-shell h3{font-size:16px;margin:0}.promo-shell p{font-size:9px;color:var(--muted);line-height:1.4}.promo-types{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.promo-type{border-radius:999px;padding:6px 8px;font-size:8px;font-weight:950}.promo-type.weekly{background:#f0eaff;color:#6b21a8}.promo-type.weekend{background:#fff4d6;color:#8a5b00}

.promo-controls{display:grid;grid-template-columns:1fr auto;gap:7px;margin-top:9px}.promo-controls select,.promo-date-inputs input{width:100%;border:1px solid var(--line);border-radius:11px;background:#fff;padding:9px;font-size:10px;font-weight:850}.promo-import{border:0;border-radius:11px;background:#142033;color:#fff;padding:9px 11px;font-size:9px;font-weight:950}.promo-date-inputs{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.promo-date-inputs label{font-size:7px;color:var(--muted);font-weight:950}.promo-date-inputs input{display:block;margin-top:3px;padding:7px}
.promo-status{font-size:9px;color:var(--muted);font-weight:800;margin:7px 2px}.promo-summary{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.promo-card{background:#fff;border:1px solid var(--line);border-radius:15px;padding:10px;margin-bottom:8px;box-shadow:var(--shadow)}.promo-card-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.promo-card-head b{font-size:14px}.promo-card-head small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.promo-badge{border-radius:999px;padding:5px 7px;font-size:7px;font-weight:950;white-space:nowrap}.promo-badge.weekly{background:#f0eaff;color:#6b21a8}.promo-badge.weekend{background:#fff4d6;color:#8a5b00}.promo-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px}.promo-metric{background:#f7f9fb;border-radius:9px;padding:7px;text-align:center;min-width:0}.promo-metric[data-promo-oh]{cursor:pointer;border:1px dashed #aebbc6}.promo-metric small{display:block;font-size:6px;color:var(--muted);font-weight:950}.promo-metric b{display:block;font-size:14px;margin-top:2px}.promo-metric.temp{background:#fff5e9;border:1px solid #f7bc7a;cursor:pointer}.promo-order{margin-top:7px;background:#eaf8ef;border:1px solid #b8e3c6;border-radius:11px;padding:8px}.promo-order small{font-size:7px;color:#397450;font-weight:950}.promo-order b{display:block;font-size:22px;color:#17683c}.promo-break{font-size:8px;color:#436052;margin-top:2px}.promo-review{background:#fff8e1;border:1px solid #efdca2;border-radius:11px;padding:8px;font-size:9px;margin-bottom:7px}

.lh{font-size:9px}.orow .name{font-size:14px}.orow .sub{font-size:9px}.cell{font-size:14px}.cell span{font-size:9px}.rtrace-line{font-size:10px}.rtrace-more{font-size:9px}.receipt-meta{font-size:10px}
.pill{font-size:10px}.ptop b{font-size:15px}.ptop small{font-size:10px}.pbox b{font-size:20px}.pbox span{font-size:9px}.why{font-size:10px}
.dcard h3{font-size:13px}.stage b{font-size:8px}.stage span{font-size:8px}.batchrow b{font-size:11px}.batchrow span{font-size:9px}
.nav button{font-size:9px}.nav i{font-size:20px}
.shead h3{font-size:21px}.shead p{font-size:10px}.dm b{font-size:18px}.dm span{font-size:9px}.detail{font-size:11px}.actions button{font-size:10px}
.empty,.loading{font-size:12px}
.estimatebar{margin:0 0 8px;padding:9px 11px;border-radius:13px;background:var(--ambersoft);color:#765300;font-size:11px;font-weight:800;line-height:1.35;border:1px solid #efdca2}
.exitoverlay{position:absolute;inset:0;background:rgba(15,25,34,.42);display:none;align-items:center;justify-content:center;padding:24px;z-index:60}.exitoverlay.on{display:flex}
.exitbox{width:100%;max-width:330px;background:#fff;border-radius:22px;padding:18px;box-shadow:0 24px 55px rgba(0,0,0,.24)}.exitbox h3{font-size:22px;margin:0}.exitbox p{font-size:13px;line-height:1.4;color:var(--muted);margin:8px 0 15px}.exitactions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.exitactions button{border:0;border-radius:13px;padding:12px;font-size:12px;font-weight:900}.exitcancel{background:#e9eef2}.exitconfirm{background:var(--red);color:#fff}
@media(max-height:760px){
  .brand{font-size:24px}.topline h2{font-size:21px}.hero h3{font-size:20px}
  .launch b{font-size:15px}.priority .prio:nth-child(n+4){display:none}
}

/* V330 Home: explicit source dates and less ambiguous decision status. */
#home .stat span{font-size:10px;font-weight:850;letter-spacing:.03em}
#home .launch span{font-size:11px;line-height:1.2}
#home .launch em{font-size:10px;line-height:1.15}
#home .priority .ph{font-size:11px}

/* V332 Quick Check: compact hierarchy with unmistakable family color ownership. */
.qfamily{--grp-border:#d6b72d;--grp-head:#fff5bf;--grp-recv:#fff9df;border:1.5px solid var(--grp-border);border-left:6px solid var(--grp-border);border-radius:17px;margin-bottom:8px;background:#fff;box-shadow:0 7px 20px rgba(18,38,56,.07)}
.qfamily.tone0{--grp-border:#ddb916;--grp-head:#fff3b7;--grp-recv:#fff9dc}
.qfamily.tone1{--grp-border:#58bd70;--grp-head:#dff6df;--grp-recv:#effbef}
.qfamily.tone2{--grp-border:#4a9de2;--grp-head:#dcedfb;--grp-recv:#eef7fe}
.qfamily.tone3{--grp-border:#ef72a5;--grp-head:#fde2ec;--grp-recv:#fff0f5}
.qfamily.tone4{--grp-border:#9b7be0;--grp-head:#ece4fb;--grp-recv:#f7f2ff}
.qfhead{padding:8px 9px;background:linear-gradient(90deg,var(--grp-head),#fff);border-bottom:1px solid color-mix(in srgb,var(--grp-border) 45%,#fff);grid-template-columns:minmax(0,1fr) auto}
.qfamily:nth-child(n) .qfhead{background:linear-gradient(90deg,var(--grp-head),#fff)}
.qfamily .qlabel{color:#675c2d;font-size:8px}.qfamily .qfnum{font-size:19px}.qfamily .qfname{font-size:14px;margin-top:2px;white-space:normal}
.qfamily .qmeta{font-size:8px;margin-top:2px}.qfamily .qkpi small{font-size:7px}.qfamily .qkpi b{font-size:14px}
.qreceivingrow{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,.9fr) minmax(0,.9fr);gap:6px;align-items:center;padding:6px 9px;background:var(--grp-recv);border-bottom:1px solid color-mix(in srgb,var(--grp-border) 28%,#fff)}
.qrecvidentity{min-width:0;display:grid;grid-template-columns:23px minmax(0,1fr);gap:7px;align-items:center}
.qricon{width:23px;height:23px;border-radius:7px;display:flex;align-items:center;justify-content:center;background:#f47b35;color:#fff;font-size:10px;font-weight:950}
.qrnum{font-size:13px;font-weight:950;line-height:1.05}.qrname{font-size:9px;font-weight:800;color:#334554;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}
.qdelivery{min-width:0;text-align:right}.qdelivery small{display:block;font-size:6px;color:#667784;font-weight:900;letter-spacing:.03em}.qdelivery b{display:block;font-size:11px;line-height:1.1}.qdelivery span{font-size:8px;color:#435868;font-weight:800}
.qsap{margin:6px 7px;border:1px solid #d9e2e9;border-left:4px solid var(--grp-border);border-radius:12px;overflow:hidden;background:#fff}
.qsaphead{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:center;padding:6px 8px;background:#f3f7fa;border-bottom:1px solid #dfe6eb}
.qsaprole{font-size:7px;font-weight:950;letter-spacing:.06em;color:#5e7180}.qsaptop{display:flex;align-items:baseline;gap:7px;min-width:0}.qsapnum{font-size:15px;font-weight:950;white-space:nowrap}.qsapname{font-size:10px;font-weight:850;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qsapkpis{display:grid;grid-template-columns:auto auto;gap:11px}.qsapkpi{text-align:right}.qsapkpi small{display:block;font-size:6px;color:#6d7d89;font-weight:900}.qsapkpi b{font-size:12px}
.qupc{padding:6px 8px;gap:6px}.qupctop{gap:5px}.qrole{font-size:8px;padding:3px 6px;border-radius:8px}.qrole.main{background:#dff0ff;color:#075b9b}.qrole.service{background:#ffe3e6;color:#c9272f}.qrole.package{background:#eee2ff;color:#6c2ab7}
.qupccode{font-size:10px}.qupcname{font-size:11px;margin-top:2px}.qupcmetrics b{font-size:13px}.qupcmetrics span,.qready{font-size:8px}
.qhidebtn{padding:6px 8px}.qhiddennote{padding:5px 8px}
@media(max-width:430px){
  .qreceivingrow{grid-template-columns:minmax(0,1.2fr) minmax(0,.82fr) minmax(0,.82fr);gap:4px;padding:6px 7px}
  .qrname{font-size:8px}.qdelivery b{font-size:10px}.qdelivery span{font-size:7px}
  .qsapkpis{gap:8px}.qsapname{font-size:9px}
}


/* V334 moderate-size all-page UI: slightly smaller than the large-type mock. */
.brand{font-size:29px}.ver{font-size:12px}.dbbtn{width:42px;height:42px;font-size:21px}
.search input{font-size:19px;padding:11px 9px}.search span{font-size:20px}
.topline h2{font-size:24px}.hint{font-size:11px}
.hero h3{font-size:22px}.hero p{font-size:11px}.stat b{font-size:18px}
.launch b{font-size:16px}.launch span{font-size:10px}.launch em{font-size:9px}
.prio b{font-size:13px}.prio span{font-size:10px}
.day strong{font-size:20px}.orow .name{font-size:13px}.cell{font-size:13px}
.ptop b{font-size:14px}.pbox b{font-size:19px}.dcard h3{font-size:12px}
.shead h3{font-size:20px}.dm b{font-size:17px}.detail{font-size:11px}
.nav button{font-size:9px}.nav i{font-size:20px}

/* V334 Quick Check: tighter result density; SAP description hidden, UPC description retained. */
.qfamily{border-radius:15px;margin-bottom:6px;border-left-width:5px}
.qfhead{padding:6px 8px;gap:7px}
.qfamily .qlabel{font-size:7px}.qfamily .qfnum{font-size:17px}.qfamily .qfname{font-size:13px;margin-top:1px}
.qfamily .qmeta{font-size:7px;margin-top:1px}.qfamily .qkpi small{font-size:6px}.qfamily .qkpi b{font-size:12px}
.qreceivingrow{gap:4px;padding:4px 7px}
.qrecvidentity{grid-template-columns:20px minmax(0,1fr);gap:5px}
.qricon{width:20px;height:20px;border-radius:6px;font-size:9px}
.qrnum{font-size:12px}.qrname{font-size:8px;margin-top:1px}
.qdelivery small{font-size:5px}.qdelivery b{font-size:10px}.qdelivery span{font-size:7px}
.qsap{margin:4px 5px;border-left-width:3px;border-radius:10px}
.qsaphead{padding:4px 6px;gap:5px}
.qsaprole{font-size:6px}.qsaptop{gap:4px}.qsapnum{font-size:13px}
.qsapname{display:none!important}
.qsapkpis{gap:7px}.qsapkpi small{font-size:5px}.qsapkpi b{font-size:10px}
.qupc{padding:5px 7px;gap:5px}
.qupctop{gap:4px}.qrole{font-size:7px;padding:2px 5px}.qupccode{font-size:9px}
.qupcname{display:block;font-size:11px;margin-top:1px;line-height:1.08}
.qupcmetrics b{font-size:12px}.qupcmetrics span,.qready{font-size:7px}
.qhidebtn{padding:5px 7px;font-size:9px}.qhiddennote{padding:4px 7px;font-size:8px}
@media(max-width:430px){
  .qreceivingrow{padding:4px 6px}
  .qrname{font-size:8px}.qdelivery b{font-size:9px}.qdelivery span{font-size:7px}
  .qsapkpis{gap:6px}
}


/* V342 Quick Check: compact metric hierarchy + price strip. */
.qfamily{border-radius:13px;margin-bottom:6px;border-left-width:4px}
.qfhead{display:block;padding:6px 7px;gap:0}
.qfidentity{min-width:0}
.qfamily .qlabel{font-size:7px}
.qfamily .qfnum{font-size:17px;line-height:1}
.qfamily .qfname{font-size:21px;font-weight:1000;line-height:1.02;margin-top:2px;white-space:normal;overflow:visible;text-overflow:clip}
.qfamily .qmeta{font-size:7px;margin-top:2px}
.qffocus{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:5px}
.qffocusbox{display:flex;align-items:center;justify-content:space-between;gap:5px;min-width:0;background:rgba(255,255,255,.58);border:1px solid rgba(95,105,113,.14);border-radius:8px;padding:4px 6px}
.qffocusbox small{display:block;font-size:6px;color:#6d7b86;font-weight:950;line-height:1}
.qffocusbox span{display:block;font-size:6px;color:#849099;font-weight:850;line-height:1;margin-top:2px;white-space:nowrap}
.qffocusbox b{font-size:21px;line-height:1;font-weight:1000;letter-spacing:-.03em;white-space:nowrap}
.qffocusbox.receipt b{color:#26343e}
.qreceivingrow{padding:4px 6px}
.qsap{margin:4px 5px;border-left-width:3px;border-radius:9px}
.qsaphead{padding:4px 6px}
.qsaprole{font-size:6px}.qsapnum{font-size:13px}
.qsapkpis{display:none}
.qsapmetric{text-align:right;white-space:nowrap}
.qsapmetric small{display:block;font-size:5px;color:#75828c;font-weight:950;line-height:1}
.qsapmetric b{display:block;font-size:17px;font-weight:1000;line-height:1;margin-top:1px}
.qsapmetric span{display:block;font-size:6px;color:#7e8a93;font-weight:850;line-height:1;margin-top:2px}
.qupc{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px;padding:5px 6px}
.qupcmain{min-width:0}
.qupcname{font-size:16px!important;font-weight:1000;line-height:1.03;margin-top:2px;white-space:normal;overflow:visible;text-overflow:clip;word-break:break-word}
.qready{display:block;font-size:7px;margin-top:2px}
.qupcmetrics{text-align:right;white-space:nowrap;padding-top:1px}
.qupcmetrics small{display:block;font-size:5px;color:#75828c;font-weight:950;line-height:1}
.qupcmetrics b{display:block;font-size:16px!important;font-weight:1000;line-height:1;margin-top:1px}
.qupcmetrics span{display:block;font-size:6px!important;color:#7e8a93;margin-top:2px}
.qupcprices{grid-column:1/-1;display:grid;grid-template-columns:repeat(auto-fit,minmax(52px,1fr));gap:3px;margin-top:1px}
.qprice{min-width:0;border:1px solid #dce3e7;background:#f7f9fa;border-radius:6px;padding:3px 2px;text-align:center}
.qprice.tested{background:#ecf8ef;border-color:#b9dec3}
.qprice.testing{background:#fff5df;border-color:#ebcf93}
.qprice.comp{background:#fff}
.qprice.companyc{background:#fff8e6;border-color:#ead89d}
.qprice small{display:block;font-size:5px;font-weight:950;color:#7a8790;line-height:1;white-space:nowrap}
.qprice b{display:block;font-size:9px;font-weight:950;line-height:1;margin-top:2px;white-space:nowrap}
.qprice.tested b{color:#24723a}.qprice.testing b{color:#9a6200}.qprice.companyc b{color:#7b5a00}.qprice b.qempty{font-size:7.5px!important;font-weight:850;letter-spacing:-.01em}
.qhidebtn{padding:5px 6px}
@media(max-width:430px){
  .qfamily .qfname{font-size:20px}
  .qffocusbox b{font-size:20px}
  .qupcname,.qupcmetrics b{font-size:15px!important}
  .qprice b{font-size:8.5px}
}


/* V344 Quick Check: modestly larger operational numbers; density unchanged. */
.qfamily .qfnum{font-size:19px}
.qffocusbox b{font-size:24px}
.qffocusbox span{font-size:7px}
.qrnum{font-size:13px}
.qdelivery b{font-size:11px}
.qdelivery span{font-size:8px}
.qsapnum{font-size:15px}
.qsapmetric b{font-size:20px}
.qsapmetric span{font-size:7px}
.qupcmetrics b{font-size:18px!important}
.qupcmetrics span{font-size:7px!important}
.qprice b{font-size:10.5px}
@media(max-width:430px){
  .qfamily .qfnum{font-size:18px}
  .qffocusbox b{font-size:23px}
  .qrnum{font-size:13px}
  .qdelivery b{font-size:10px}
  .qdelivery span{font-size:8px}
  .qsapnum{font-size:14px}
  .qsapmetric b{font-size:19px}
  .qsapmetric span{font-size:7px}
  .qupcmetrics b{font-size:17px!important}
  .qupcmetrics span{font-size:7px!important}
  .qprice b{font-size:10px}
}


/* V350 Yipman: Quick Check home + fixed top + bottom live search + Best Sellers. */
.header{position:relative;z-index:20;background:rgba(246,247,249,.98);backdrop-filter:blur(12px)}
.workspace{height:calc(100% - 62px)}
#quick{padding-bottom:calc(154px + env(safe-area-inset-bottom))}
.nav{grid-template-columns:repeat(3,1fr);z-index:30}
.dbbtn{position:relative;z-index:31;pointer-events:auto}
.quicksearch{position:absolute;left:10px;right:10px;bottom:calc(74px + env(safe-area-inset-bottom));z-index:12;margin:0;display:grid;grid-template-columns:42px minmax(0,1fr) 64px;align-items:center;min-height:60px;border:2px solid #1769e0;border-radius:18px;padding:5px 7px;background:#fff;box-shadow:0 9px 24px rgba(13,79,139,.20)}
.quicksearch:focus-within{border-color:#075b9b;box-shadow:0 10px 27px rgba(13,79,139,.25)}
.quicksearch>span{display:flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:10px;background:#e8f3ff;color:#0d5f9f;font-size:20px;font-weight:950}
.quicksearch input{min-width:0;width:100%;border:0;outline:0;background:transparent;padding:10px 5px;font-size:17px;font-weight:800}
.quicksearch input::placeholder{color:#6f7d89;font-weight:750}
.quickclear{display:none;align-items:center;justify-content:center;height:39px;border:1px solid #cdd8e1;border-radius:10px;background:#edf3f7;color:#36516a;font-size:11px;font-weight:950;letter-spacing:.02em}
.quickclear.on{display:flex}
.besthead{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin:0 1px 7px}
.besthead h3{font-size:17px;margin:0;font-weight:950}.besthead span{font-size:8px;color:var(--muted);font-weight:900}
.bestsort{white-space:nowrap;border:1px solid #cbddeb;background:#edf6fd;color:#315b78;border-radius:999px;padding:5px 7px;font-size:8px!important}
.bestfam{--best-border:#ddb916;--best-bg:#fff3b7;border:1.5px solid var(--best-border);border-left:5px solid var(--best-border);border-radius:13px;background:linear-gradient(90deg,var(--best-bg),#fff);padding:7px 8px;margin-bottom:6px;box-shadow:0 6px 17px rgba(18,38,56,.06)}
.bestfam.tone1{--best-border:#58bd70;--best-bg:#e2f6e6}.bestfam.tone2{--best-border:#4a9de2;--best-bg:#e6f2fc}.bestfam.tone3{--best-border:#ef72a5;--best-bg:#fde7ef}.bestfam.tone4{--best-border:#9b7be0;--best-bg:#eee8fb}
.besttop{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px}.bestlabel{font-size:7px;font-weight:950;color:#6f6a53}.bestnum{font-size:17px;font-weight:1000;line-height:1}.bestname{font-size:18px;font-weight:1000;line-height:1.03;margin-top:2px}.bestrank{align-self:start;background:rgba(255,255,255,.72);border:1px solid rgba(70,80,90,.10);border-radius:7px;padding:4px 6px;font-size:8px;font-weight:950}
.bestmetrics{display:grid;grid-template-columns:1.35fr 1fr;gap:4px;margin-top:5px}.bestmetric{background:rgba(255,255,255,.62);border:1px solid rgba(90,100,110,.13);border-radius:8px;padding:4px 6px}.bestmetric small{display:block;font-size:6px;color:#6e7c87;font-weight:950}.bestmetric b{display:block;font-size:22px;line-height:1;font-weight:1000;margin-top:2px}.bestmetric span{display:block;font-size:7px;color:#7e8a93;font-weight:850;margin-top:2px}
.bestrecent{margin-top:4px;background:rgba(255,255,255,.62);border:1px solid rgba(90,100,110,.12);border-radius:8px;padding:4px 6px}.bestrecenthead{display:flex;justify-content:space-between;gap:6px;font-size:7px;color:#6d7a85;font-weight:950}.bestreceipt{display:grid;grid-template-columns:1fr auto;gap:8px;margin-top:3px;font-size:9px;font-weight:900}.bestreceipt b{font-size:10px}.bestreceipt.receiptlink{width:100%;padding:2px 0;border:0;background:transparent;text-align:left;color:inherit}.receiptlink{cursor:pointer}.receiptlink:active{opacity:.62}.qdelivery.receiptlink{border:0;background:transparent;padding:2px 0 2px 4px;font:inherit;color:inherit}
.qsap.nohead{border-left-width:1px;margin-top:3px}.qsap.nohead .qupc:first-child{border-top:0}
.qupcname{white-space:nowrap!important;overflow:hidden!important;text-overflow:clip!important;word-break:normal!important}
@media(max-width:430px){.bestname{font-size:17px}.bestmetric b{font-size:21px}.quicksearch{left:8px;right:8px}}


/* V355 Yipman: bottom navigation dock only. No other page UI changed. */
.nav{
  left:10px;
  right:10px;
  bottom:calc(9px + env(safe-area-inset-bottom));
  height:57px;
  grid-template-columns:repeat(3,1fr);
  gap:4px;
  padding:5px;
  background:rgba(27,43,60,.97);
  border:1px solid rgba(255,255,255,.08);
  border-radius:18px;
  box-shadow:0 10px 24px rgba(18,38,56,.18),0 1px 0 rgba(255,255,255,.10) inset;
  backdrop-filter:blur(12px);
}
.nav button{
  border:0;
  background:transparent;
  color:#c1ccd7;
  border-radius:13px;
  font-size:9px;
  font-weight:850;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  gap:1px;
  min-width:0;
  padding:3px 2px;
}
.nav i{
  display:flex;
  align-items:center;
  justify-content:center;
  min-width:37px;
  height:25px;
  margin:0 0 1px;
  border-radius:14px;
  color:#d4dde6;
  font-size:20px;
  line-height:1;
}
.nav button.on{
  background:#f7fbff;
  color:#0869bd;
  box-shadow:0 4px 12px rgba(0,0,0,.16);
}
.nav button.on i{
  background:#dceefe;
  color:#0869bd;
}
.nav button:active{transform:scale(.985)}


/* V361 Price Suggestions: compact three-price path + dense evidence/progress. */
#price .topline{margin-bottom:5px}
#price .filters{margin-bottom:5px}
#priceStatus{font-size:9px!important;line-height:1.25!important;margin-bottom:5px!important}
.pricecards{gap:6px}
.pcard{border:1px solid #e0e6eb;border-radius:14px;padding:9px 10px;box-shadow:0 4px 14px rgba(18,38,56,.065)}
.ptop{align-items:flex-start;gap:6px}.ptop>div:first-child{min-width:0}
.ptop b{display:block;font-size:14px!important;line-height:1.08;white-space:normal}
.ptop small{font-size:8px!important;line-height:1.2;margin-top:2px}
.pbadge{flex:0 0 auto;border-radius:999px;padding:4px 6px;font-size:7px;font-weight:950;white-space:nowrap}
.pbadge.red{background:var(--redbg);color:var(--red)}.pbadge.amber{background:var(--amberbg);color:var(--amber)}.pbadge.green{background:var(--greenbg);color:var(--green)}
.pricepath{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;margin-top:7px}
.pp{min-width:0;border:1px solid #e3e8ec;background:#f5f7f9;border-radius:9px;padding:6px 7px}
.pp.tested{background:#fff9e4;border-color:#efdda0}.pp.testing{background:#eaf7ff;border-color:#c5e5f5}
.pp small{display:block;font-size:6px;font-weight:950;letter-spacing:.05em;color:#7c8892;line-height:1}
.pp b{display:block;font-size:17px;line-height:1;margin-top:3px;font-weight:1000;white-space:nowrap}
.pp span{display:block;font-size:6px;color:#7c8892;font-weight:850;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pp.tested b{color:#7a5a00}.pp.testing b{color:#0878ad}
.pmetrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:3px;margin-top:5px}
.pm{min-width:0;border:1px solid #e8edf0;background:#fafbfc;border-radius:7px;padding:4px 5px}
.pm small{display:block;font-size:5.5px;font-weight:950;color:#8a959e;line-height:1}
.pm b{display:block;font-size:10px;font-weight:950;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pprogress{margin-top:5px;background:#f8fafb;border:1px solid #e7ecef;border-radius:8px;padding:5px 6px}
.pprogress-line{display:flex;align-items:center;justify-content:space-between;gap:7px;font-size:7px;color:#5f6d78;font-weight:850;line-height:1.2}
.pprogress-line b{font-size:8px;color:#263744}.pprogress-line strong{font-size:8px;color:#0878ad;white-space:nowrap}
.pbar{height:4px;background:#e4eaee;border-radius:999px;overflow:hidden;margin-top:4px}.pbar i{display:block;height:100%;background:#118fc6;border-radius:999px}
.pchips{display:flex;gap:3px;flex-wrap:wrap;margin-top:5px}.pchip{border:1px solid #e3e8ec;background:#fafbfc;color:#5f6d78;border-radius:6px;padding:3px 5px;font-size:6.5px;font-weight:950}
.preason{margin-top:5px;border-top:1px solid #edf1f3;padding-top:5px}.preason summary{list-style:none;cursor:pointer;color:#0879b3;font-size:7px;font-weight:950}.preason div{margin-top:4px;color:#64727e;font-size:7px;line-height:1.4;font-weight:750}
.pcard-actions{display:grid;grid-template-columns:1fr auto;gap:5px;margin-top:6px}.pcard-actions button{border-radius:8px;padding:6px 8px;font-size:7px;font-weight:950}
.pdetail{border:0;background:#173047;color:#fff}.pignore{border:1px solid #d9e1e6;background:#fff;color:#586773}
@media(max-width:390px){.pp b{font-size:16px}.pm b{font-size:9px}.pcard{padding:8px 9px}}

</style>
</head>
<body>
<div id="app">
  <div class="ptr" id="ptr"><div id="ptrText">Pull to refresh</div></div>
  <header class="header">
    <div class="head"><div><div class="brand">Yip<span>man</span></div><span class="ver">FULL MYSQL · __VERSION__</span></div><button class="dbbtn" data-go="data" aria-label="Data Center">▦</button></div>
  </header>
  <main class="workspace">
    <section class="page on" id="quick"><div class="topline"><h2>Quick Check</h2><div class="hint">CURRENT MODULE DATA</div></div><div id="quickRows"><div class="loading">Loading best sellers…</div></div><form class="search quicksearch" id="globalForm"><span>⌕</span><input id="globalInput" placeholder="Search item, UPC, article..." autocomplete="off" enterkeyhint="search"><button class="quickclear" id="quickClear" type="button">CLEAR</button></form></section>

    <section class="page" id="order">
      <div class="topline"><h2>Ordering</h2><div class="hint">DELIVERY WINDOW</div></div>
      <div class="order-tabs"><button class="order-tab on" data-order-mode="REGULAR">Regular Order</button><button class="order-tab" data-order-mode="PROMOTION">Promotion Order</button></div>
      <div id="orderDatePicker">
        <div class="order-date-grid">
          <button class="order-date-card delivery pick" id="deliveryDateCard"><small>DELIVERY DATE</small><b id="deliveryDateText">Loading…</b><span id="deliveryObservedText">Observed delivery day</span></button>
          <button class="order-date-card next" id="nextDeliveryDateCard"><small>NEXT DELIVERY</small><b id="nextDeliveryDateText">Loading…</b><span id="nextObservedText">Observed delivery day</span></button>
        </div>
        <div class="daybar" id="dayBar"></div>
        <div class="order-coverage"><small>COVERAGE WINDOW</small><b id="orderCoverageText">Choose two delivery dates</b><span id="orderCoverageSub">Predict usage from delivery through the day before next delivery using the best available data at viewing time.</span></div>
      </div>
      <div id="regularOrderPanel">
        <div class="order-tools" id="orderTools"><div class="order-summary" id="orderSummary">Observed roster loading…</div><div class="order-controls"><label>FILTER<select id="orderFilter"><option value="ALL">ALL</option><option value="ORDER">NEED ORDER</option><option value="ZERO_ORDER">0 ORDER</option><option value="REVIEW">REVIEW</option></select></label><label>SORT<select id="orderSort"><option value="ACTION">ACTION FIRST</option><option value="QTY">ORDER QTY ↓</option><option value="DOS">DOS ↑</option><option value="OBSERVED">OBSERVED ↓</option><option value="NAME">NAME A–Z</option></select></label></div></div>
        <div id="orderStatus" class="hint" style="margin:0 2px 7px"></div>
        <div class="list"><div class="lh"><div id="orderCol1">FAMILY / RECEIVING</div><div id="orderCol2">OH</div><div id="orderCol3">ORDER</div></div><div id="orderRows"><div class="loading">Loading observed delivery days…</div></div></div>
      </div>
      <div id="promotionOrderPanel" class="hide">
        <div class="promo-shell">
          <h3>Promotion Order</h3>
          <p>Weekly items use Thursday → following Thursday. Weekend items use Friday → Sunday. The selected delivery window can contain both promotion and regular-price days.</p>
          <div class="promo-types"><span class="promo-type weekly">WEEKLY · THU → THU</span><span class="promo-type weekend">WEEKEND · FRI → SUN</span></div>
          <div class="promo-controls"><select id="promoListSelect"><option value="">Choose promotion list…</option></select><button class="promo-import" id="promoImportBtn">IMPORT LIST</button></div>
          <div class="promo-date-inputs"><label>WEEKLY START (THU)<input type="date" id="promoWeeklyStart"></label><label>WEEKEND START (FRI)<input type="date" id="promoWeekendStart"></label></div>
          <input type="file" id="promoFileInput" accept=".csv,.xls,.xlsx,.xlsm" class="hide">
          <div class="promo-status" id="promoListStatus">Import CSV / XLS / XLSX, or choose a saved promotion list.</div>
        </div>
        <div class="promo-summary" id="promoSummary"></div>
        <div id="promoOrderStatus" class="promo-status"></div>
        <div id="promoRows"><div class="empty">Choose or import a promotion list.</div></div>
      </div>
    </section>

    <section class="page" id="price"><div class="topline"><h2>Price Suggestions</h2><div class="hint">COMPACT · LIVE PROGRESS</div></div><div class="filters"><button class="pill on" data-price-filter="LIVE">LIVE</button><button class="pill" data-price-filter="TUE">OBSERVED TUE</button><button class="pill" data-price-filter="FRI_SAT">OBSERVED FRI / SAT</button></div><div id="priceStatus" class="hint" style="margin:0 2px 7px"></div><div class="pricecards" id="priceRows"><div class="loading">Loading price review…</div></div></section>

    <section class="page" id="data"><div class="topline"><h2>Data Center</h2><div class="hint">BACK OFFICE UNCHANGED</div></div><div class="datagrid"><div class="dcard"><h3>Processing Pipeline</h3><div class="pipe" id="pipe"><div class="stage"><b>UPLOAD</b><span>—</span></div><div class="stage"><b>INGEST</b><span>—</span></div><div class="stage"><b>QA</b><span>—</span></div><div class="stage"><b>PUBLISH</b><span>—</span></div></div></div><div class="dcard"><h3>14-Day Completeness</h3><div class="cal" id="calendar"></div></div><div class="dcard"><h3>Current Batch</h3><div id="currentBatch"><div class="loading">Loading…</div></div></div><div class="dcard"><h3>Recent Batches</h3><div id="recentBatches"><div class="loading">Loading…</div></div></div></div></section>

    <nav class="nav"><button class="on" data-go="quick"><i>⌕</i>QUICK</button><button data-go="order"><i>▤</i>ORDER</button><button data-go="price"><i>$</i>PRICE</button></nav>
    <div class="overlay" id="overlay"><div class="sheet"><div class="shead"><div><h3 id="sheetTitle">Detail</h3><p id="sheetSub"></p></div><button class="close" id="closeSheet">×</button></div><div class="sbody" id="sheetBody"></div></div></div>
    <div class="exitoverlay" id="exitOverlay"><div class="exitbox"><h3>Exit Yipman?</h3><p>Your current view will close. No inventory, ordering, or price data will be changed.</p><div class="exitactions"><button class="exitcancel" id="exitCancel">Stay</button><button class="exitconfirm" id="exitConfirm">Exit</button></div></div></div>
    <div class="toast" id="toast"></div>
  </main>
</div>
<script>
(()=>{
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>{if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=(v,d=1)=>{const n=num(v);return n===null?'—':n.toLocaleString(undefined,{maximumFractionDigits:d})};
const money=v=>{const n=num(v);return n===null?'—':'$'+n.toFixed(2)};
const iso=d=>d.toISOString().slice(0,10);
const shortDate=v=>{const m=String(v||'').match(/^\d{4}-(\d{2})-(\d{2})/);return m?m[1]+'-'+m[2]:'—'};
const appDate=v=>{
  const m=String(v||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(!m)return '—';
  const y=Number(m[1]),mo=Number(m[2]),d=Number(m[3]);
  const dt=new Date(y,mo-1,d,12,0,0,0);
  const wd=dt.toLocaleDateString(undefined,{weekday:'short'});
  return mo+'/'+d+' '+wd;
};
const app=$('#app'), pages=$$('.page'), nav=$$('.nav button');
let current='quick', priceFilter='LIVE', orderDate=null, orderNextDate=null, orderSelectMode='DELIVERY', orderObservedWeekdays=new Map(), orderCalendarLoaded=false, orderInitPromise=null, orderMode='REGULAR', promoListsLoaded=false, promoListId=null, promoListDetail=null, promoTempOH=new Map(), promoLastRows=[], pullStart=null, pull=0;
let historyReady=false, detailHistory=false, exitAllowed=false;
let quickSearchTimer=null, quickRequestSeq=0, lastQuickQuery='', bestSellerGroups=null, orderRequestSeq=0, orderRetryTimer=null, orderRetryCount=0, orderRetryWindowKey='', priceRequestSeq=0, priceRetryTimer=null;
let orderSort='ACTION', orderFilter='ALL', lastOrderRows=[], lastOrderData=null, lastOrderStale=false, renderedOrderRows=[], lastOrderWindowKey='';
function toast(t){const n=$('#toast');n.textContent=t;n.classList.add('on');setTimeout(()=>n.classList.remove('on'),1600)}
async function api(url,opt={}){const c=new AbortController();let timedOut=false;const tm=setTimeout(()=>{timedOut=true;c.abort()},opt.timeoutMs||18000);try{const r=await fetch(url,{...opt,signal:c.signal,headers:{'Accept':'application/json',...(opt.headers||{})},cache:'no-store'});const text=await r.text();let data={};try{data=text?JSON.parse(text):{}}catch{}if(!r.ok)throw new Error(data?.detail?.reason||data?.detail||text||('HTTP '+r.status));return data}catch(e){if(timedOut||e?.name==='AbortError')throw new Error('Request timed out while the server was calculating. Retrying is safe.');throw e}finally{clearTimeout(tm)}}
function renderView(id){
  if(!$('#'+id))id='quick';
  current=id;
  pages.forEach(p=>p.classList.toggle('on',p.id===id));
  nav.forEach(b=>b.classList.toggle('on',b.dataset.go===id));
  const p=$('#'+id);if(p)p.scrollTop=0;
  if(id!=='order'){clearTimeout(orderRetryTimer);orderRetryTimer=null}
  if(id==='quick'&&!$('#globalInput').value.trim()&&!bestSellerGroups)loadBestSellers();
  if(id==='order')initOrdering();
  if(id==='price')loadPrices();
  if(id==='data')loadData();
}
function go(id,{push=true}={}){
  if(id===current&&!$('#overlay').classList.contains('on'))return;
  renderView(id);
  if(push&&historyReady)history.pushState({yipman:true,view:id},'', '#'+id);
}
async function resetQuickHome({push=true}={}){
  const wasQuick=current==='quick';
  clearTimeout(quickSearchTimer);
  quickRequestSeq++;
  lastQuickQuery='';
  $('#globalInput').value='';
  $('#quickClear').classList.remove('on');
  $('#globalForm').classList.remove('hide');
  renderView('quick');
  if(bestSellerGroups)await loadBestSellers();
  $('#quick').scrollTop=0;
  if(push&&historyReady&&!wasQuick)history.pushState({yipman:true,view:'quick'},'', '#quick');
}
$$('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));
const quickNav=$('.nav button[data-go="quick"]');
if(quickNav)quickNav.onclick=()=>resetQuickHome();
function sheet(title,sub,html){
  const wasOpen=$('#overlay').classList.contains('on');
  $('#sheetTitle').textContent=title;$('#sheetSub').textContent=sub||'';$('#sheetBody').innerHTML=html;$('#overlay').classList.add('on');
  if(historyReady&&!wasOpen){history.pushState({yipman:true,view:current,detail:true},'', '#'+current+'/detail');detailHistory=true}
}
function closeSheet(useHistory=true){
  if(!$('#overlay').classList.contains('on'))return;
  $('#overlay').classList.remove('on');
  const had=detailHistory;detailHistory=false;
  if(useHistory&&had)history.back();
}
$('#closeSheet').onclick=()=>closeSheet(true);
$('#overlay').onclick=e=>{if(e.target===$('#overlay'))closeSheet(true)};
function showExitConfirm(){$('#exitOverlay').classList.add('on')}
function hideExitConfirm(){$('#exitOverlay').classList.remove('on')}
$('#exitCancel').onclick=hideExitConfirm;
$('#exitConfirm').onclick=()=>{exitAllowed=true;hideExitConfirm();history.go(-2)};
window.addEventListener('popstate',e=>{
  if($('#exitOverlay').classList.contains('on')){
    history.pushState({yipman:true,view:'quick',guard:true},'', '#quick');
    hideExitConfirm();renderView('quick');return;
  }
  if($('#overlay').classList.contains('on')){
    $('#overlay').classList.remove('on');detailHistory=false;
    if(e.state?.yipman&&e.state.view)renderView(e.state.view);
    return;
  }
  const st=e.state;
  if(st?.yipman&&st.root){
    renderView('quick');
    history.pushState({yipman:true,view:'quick',guard:true},'', '#quick');
    showExitConfirm();
    return;
  }
  if(st?.yipman&&st.view){renderView(st.view);return}
});
window.addEventListener('beforeunload',e=>{if(exitAllowed)return;e.preventDefault();e.returnValue=''});
const today=new Date();

async function loadHome(){
 try{
  const [h,health]=await Promise.all([api('/v1/backoffice/home-summary',{timeoutMs:10000}),api('/v1/backoffice/data-health?days=14',{timeoutMs:10000})]);
  const oh=h?.ordering||{}, ph=h?.pricing||{}, sourceHealth=ph?.data_health||oh?.data_health||{}, latest=health?.latest||{};
  const stale=String(sourceHealth.status||'').toUpperCase()!=='CURRENT';
  const dataThrough=sourceHealth.data_through||sourceHealth.pos_data_through||sourceHealth.movement_data_through||null;
  const expectedThrough=sourceHealth.expected_through||health?.completed_through||null;
  const posDate=latest?.POS?.date||sourceHealth.pos_data_through||null;
  const mvtDate=latest?.MVT?.date||sourceHealth.movement_data_through||null;
  const ohDate=latest?.OH?.date||null;
  const priceListDate=latest?.PRICE?.date||null;
  const oc=num(oh.family_count)||0, oa=num(oh.attention_count)||0, pc=num(ph.qualified_count)||0, pairUrgent=num(ph.urgent_240_249_count)||0;
  const due=(health?.rows||[]).filter(x=>x.required_daily_due), complete=due.filter(x=>x.overall_status==='COMPLETE').length;
  const hp=due.length?Math.round(complete/due.length*100):100;

  // The blue card is source freshness, not a vague EST counter.
  $('#homeOrder').textContent=shortDate(posDate);
  $('#homePrice').textContent=shortDate(mvtDate);
  $('#homeHealth').textContent=shortDate(priceListDate);

  $('#orderMini').textContent=stale?'ESTIMATE · THRU '+shortDate(dataThrough):(oa?oa+' NEED ATTENTION':oc+' TO REVIEW');
  $('#priceMini').textContent=stale?'ESTIMATE · THRU '+shortDate(dataThrough):pc+' ACTIONABLE';
  $('#dataMini').textContent='PRICE '+shortDate(priceListDate)+' · OH '+shortDate(ohDate);

  const freshness='POS '+shortDate(posDate)+' · MVT '+shortDate(mvtDate)+' · PRICE '+shortDate(priceListDate);
  if(stale){
    $('#attentionTitle').textContent='Best-available analysis · thru '+shortDate(dataThrough);
    $('#attentionSub').textContent=freshness+' · ESTIMATE MODE';
  }else{
    const total=oa+pc+(hp<100?1:0);
    $('#attentionTitle').textContent=total?total+' actions need attention':'Current work is clear';
    $('#attentionSub').textContent=freshness+' · CURRENT';
  }

  const rows=[];
  const missing=[...(sourceHealth.missing_required_sources||[])].map(x=>String(x).toUpperCase());
  if(stale){
    if(missing.length){
      rows.push({
        title:'Latest daily sources behind target',
        sub:missing.join(' + ')+' · analysis thru '+shortDate(dataThrough)+' · target '+shortDate(expectedThrough),
        badge:'DATA',cls:'amber',go:'data'
      });
    }
    rows.push({
      title:'Ordering estimate available',
      sub:'Receipt cadence + completed sales through '+shortDate(dataThrough),
      badge:'EST',cls:'amber',go:'order'
    });
    rows.push({
      title:'Price estimate available',
      sub:'Completed-day sales / GP evidence through '+shortDate(dataThrough),
      badge:'EST',cls:'amber',go:'price'
    });
  }else{
    if(pairUrgent)rows.push({title:'240 / 249 price mismatch',sub:pairUrgent+' service price pair(s) need equality review',badge:'PRICE',cls:'red',go:'price'});
    if(oa)rows.push({title:'Ordering review',sub:oa+' family item(s) need attention',badge:'ORDER',cls:'red',go:'order'});
    if(pc)rows.push({title:'Price review',sub:pc+' actionable price suggestion(s)',badge:'PRICE',cls:'red',go:'price'});
    if(hp<100)rows.push({title:'Data completeness',sub:(100-hp)+'% of due daily coverage needs attention',badge:'DATA',cls:'amber',go:'data'});
  }
  if(!rows.length)rows.push({title:'No urgent actions',sub:'Use Quick Check for item lookup',badge:'READY',cls:'green',go:'quick'});
  $('#priorityRows').innerHTML=rows.slice(0,3).map(r=>'<div class="prio" data-prio="'+r.go+'"><div><b>'+esc(r.title)+'</b><span>'+esc(r.sub)+'</span></div><div class="badge '+r.cls+'">'+r.badge+'</div></div>').join('');
  $$('[data-prio]').forEach(x=>x.onclick=()=>go(x.dataset.prio));
 }catch(e){$('#attentionTitle').textContent='Home summary unavailable';$('#attentionSub').textContent=e.message;$('#priorityRows').innerHTML='<div class="loading">Pull down to retry.</div>'}
}

function hasActivity(v){const n=Number(v);return Number.isFinite(n)&&Math.abs(n)>0.0000001}
function quickRole(r){
 const raw=String(r?.upc||'').replace(/\D/g,'').replace(/^0+/,'');
 const p=raw.slice(0,3);
 if(p==='240')return {label:'MAIN · 240',cls:'main'};
 if(p==='249')return {label:'SERVICE · 249',cls:'service'};
 if(p==='245')return {label:'PACKAGE · 245',cls:'package'};
 if(p==='247')return {label:'RELATED · 247',cls:''};
 return {label:'UPC'+(p?' · '+p:''),cls:''};
}
function quickFamilyGroups(rows){
 const groups=new Map();
 const articleCopy=a=>({
   article_number:String(a?.article_number||'').trim(),
   article_description:a?.article_description||'',
   article_role:a?.article_role||'',
   relationship_type:a?.relationship_type||'',
   movement_7d:a?.movement_7d,
   movement_uom:a?.movement_uom||'',
   avg_qty_day:a?.avg_qty_day,
   movement_status:a?.movement_status||'',
   receipt_verified:!!a?.receipt_verified,
   receipt_history:Array.isArray(a?.receipt_history)?a.receipt_history:[],
   has_active_pos_upc:!!a?.has_active_pos_upc
 });
 for(const r of (rows||[])){
   const key=String(r.family_id??r.family_article??('UPC:'+String(r.upc||'')));
   if(!groups.has(key))groups.set(key,{
     key,family_id:r.family_id,family_article:r.family_article||null,family_name:r.family_name||'Unmapped Family',category:r.category||'',
     rows:[],article_catalog:new Map(),receiving:new Map(),selling:new Map(),max_velocity:Number.NEGATIVE_INFINITY,
     group_qty_7d:r.family_group_movement_7d??r.family_qty_7d??null,
     group_avg_qty_day:r.family_group_avg_qty_day??r.family_avg_qty_day??null,
     group_uom:r.family_group_movement_uom||r.family_qty_uom||'',
     reconciliation:r.family_group_reconciliation||'',
     source_article:r.family_source_article||r.family_article||null,
     source_movement_7d:r.family_source_movement_7d,
     source_avg_qty_day:r.family_source_avg_qty_day,
     source_movement_uom:r.family_source_movement_uom||'',
     family_receipt_verified:!!r.family_receipt_verified,
     family_receipt_history:Array.isArray(r.family_receipt_history)?r.family_receipt_history:[],
     family_receipt_7d_qty:r.family_receipt_7d_qty??null,
     family_receipt_7d_uom:r.family_receipt_7d_uom||'',
     family_receipt_7d_status:r.family_receipt_7d_status||'',
     family_receipt_7d_day_count:r.family_receipt_7d_day_count??null
   });
   const g=groups.get(key);g.rows.push(r);
   const v=Number(r.velocity_7d);if(Number.isFinite(v))g.max_velocity=Math.max(g.max_velocity,v);
   if(g.group_qty_7d==null&&r.family_group_movement_7d!=null)g.group_qty_7d=r.family_group_movement_7d;
   if(g.group_avg_qty_day==null&&r.family_group_avg_qty_day!=null)g.group_avg_qty_day=r.family_group_avg_qty_day;
   if(!g.group_uom&&r.family_group_movement_uom)g.group_uom=String(r.family_group_movement_uom);
   if(!g.reconciliation&&r.family_group_reconciliation)g.reconciliation=String(r.family_group_reconciliation);

   for(const rawA of (Array.isArray(r.receiving_articles)?r.receiving_articles:[])){
     const a=articleCopy(rawA),art=a.article_number;if(!art)continue;
     const prev=g.article_catalog.get(art);
     if(!prev||a.receipt_history.length>prev.receipt_history.length||hasActivity(a.movement_7d))g.article_catalog.set(art,a);
   }
 }
 const out=[...groups.values()];
 for(const g of out){
   const sourceKey=String(g.source_article||g.family_article||'').trim();

   if(sourceKey&&g.family_receipt_history.length){
     g.receiving.set(sourceKey,{
       article_number:sourceKey,
       article_description:g.family_name||'',
       receipt_history:g.family_receipt_history,
       source_family:true
     });
   }
   for(const a of g.article_catalog.values()){
     if(a.receipt_verified||a.receipt_history.length){
       g.receiving.set(a.article_number,{
         article_number:a.article_number,
         article_description:a.article_description||'',
         receipt_history:a.receipt_history||[],
         source_family:false
       });
     }
   }

   for(const r of g.rows){
     const assigned=String(r.receiving_article||'').trim();
     const art=assigned||String(r.article_number||'').trim();
     if(!art)continue;
     const catalog=g.article_catalog.get(art)||{};
     const isSource=sourceKey&&art===sourceKey;
     if(!g.selling.has(art))g.selling.set(art,{
       article_number:art,
       article_description:(isSource?(g.family_name||r.name):'')||catalog.article_description||r.name||'',
       movement_7d:isSource?g.source_movement_7d:(catalog.movement_7d??r.receiving_movement_7d),
       movement_uom:isSource?(g.source_movement_uom||g.group_uom):(catalog.movement_uom||r.receiving_movement_uom||g.group_uom),
       avg_qty_day:isSource?g.source_avg_qty_day:(catalog.avg_qty_day??r.receiving_avg_qty_day),
       rows:[],max_velocity:Number.NEGATIVE_INFINITY
     });
     const a=g.selling.get(art);a.rows.push(r);if(Number.isFinite(Number(r.velocity_7d)))a.max_velocity=Math.max(a.max_velocity,Number(r.velocity_7d));
   }

   for(const a of g.article_catalog.values()){
     const role=String(a.article_role||'').toUpperCase();
     if(!g.selling.has(a.article_number)&&(role.includes('SAP_SELLING_ARTICLE')||hasActivity(a.movement_7d))){
       g.selling.set(a.article_number,{
         article_number:a.article_number,article_description:a.article_description||'',
         movement_7d:a.movement_7d,movement_uom:a.movement_uom||g.group_uom,avg_qty_day:a.avg_qty_day,
         rows:[],max_velocity:Number.NEGATIVE_INFINITY
       });
     }
   }

   const sortRows=a=>a.sort((x,y)=>Number(y.velocity_7d||0)-Number(x.velocity_7d||0)||Number(y.qty_7d||0)-Number(x.qty_7d||0)||String(x.upc||'').localeCompare(String(y.upc||'')));
   for(const a of g.selling.values())sortRows(a.rows);
   g.receiving=[...g.receiving.values()].sort((a,b)=>{
     const ad=String(a.receipt_history?.[0]?.date||''),bd=String(b.receipt_history?.[0]?.date||'');
     return bd.localeCompare(ad)||Number(b.source_family)-Number(a.source_family)||String(a.article_number).localeCompare(String(b.article_number));
   });
   g.selling=[...g.selling.values()].sort((a,b)=>(Number.isFinite(b.max_velocity)?b.max_velocity:-999999)-(Number.isFinite(a.max_velocity)?a.max_velocity:-999999)||Number(b.movement_7d||0)-Number(a.movement_7d||0)||String(a.article_number).localeCompare(String(b.article_number)));
 }
 out.sort((a,b)=>b.max_velocity-a.max_velocity||Number(b.group_qty_7d||0)-Number(a.group_qty_7d||0)||String(a.family_name||'').localeCompare(String(b.family_name||'')));
 return out;
}
function quickUpcHtml(r){
 const role=quickRole(r),uom=r.qty_uom||r.selling_uom||'',active=hasActivity(r.qty_7d);
 const pm=v=>num(v)===null?'—':money(v);
 const testedText=v=>num(v)===null?'Not set':money(v);
 const comp=(label,attr,val,cls='')=>num(val)===null?'':'<div class="qprice comp '+cls+'"><small>'+label+'</small><b '+attr+'>'+pm(val)+'</b></div>';
 const priceStrip=active?'<div class="qupcprices" data-qprice-status="loading">'+
   '<div class="qprice"><small>CURRENT</small><b data-q-current>'+pm(r.price)+'</b></div>'+
   '<div class="qprice tested"><small>TESTED</small><b data-q-tested>'+testedText(r.sweet_spot_price)+'</b></div>'+
   '<div class="qprice testing"><small>TESTING</small><b data-q-testing>…</b></div>'+
   comp('COMP A','data-q-comp-a',r.company_price_a)+
   comp('COMP B','data-q-comp-b',r.company_price_b)+
   comp('COMP C','data-q-comp-c',r.company_price_c,'companyc')+
 '</div>':'';
 return '<div class="qupc" data-upc="'+esc(r.upc||'')+'">'+
   '<div class="qupcmain"><div class="qupctop"><span class="qrole '+role.cls+'">'+esc(role.label)+'</span><span class="qupccode">'+esc(r.upc||'—')+'</span></div>'+
   '<div class="qupcname">'+esc(r.name||r.upc||'')+'</div><span class="qready">'+esc(r.readiness||'')+'</span></div>'+
   '<div class="qupcmetrics"><small>UPC 7D QTY</small><b>'+fmt(r.qty_7d)+' '+esc(uom)+'</b><span>AVG/DAY · '+fmt(r.velocity_7d)+' '+esc(uom)+'</span></div>'+
   priceStrip+'</div>';
}
function hiddenUpcs(rows,id){
 if(!rows.length)return '';
 return '<button class="qhidebtn" data-qhide="'+esc(id)+'" data-noun="UPC">Show '+rows.length+' inactive UPC'+(rows.length===1?'':'s')+' ▾</button><div class="qhidden" id="'+esc(id)+'"><div class="qhiddennote">Hidden by default · UPC 7D POS Qty = 0 / none.</div>'+rows.map(quickUpcHtml).join('')+'</div>';
}
function quickDeliveryCell(x,label,familyId,articleNumber){
 if(!x)return '<div class="qdelivery"><small>'+label+'</small><b>—</b><span>No receipt</span></div>';
 const uom=String(x.uom||'').trim();
 return '<button type="button" class="qdelivery receiptlink" data-receipt-family="'+esc(familyId??'')+'" data-receipt-article="'+esc(articleNumber||'')+'" data-receipt-date="'+esc(x.date||'')+'"><small>'+label+'</small><b>'+esc(appDate(x.date))+'</b><span>'+fmt(x.quantity)+' '+esc(uom)+'</span></button>';
}
function quickReceivingRowHtml(a,familyId){
 const history=(Array.isArray(a.receipt_history)?a.receipt_history:[]).slice(0,2);
 return '<div class="qreceivingrow"><div class="qrecvidentity"><span class="qricon">R</span><div><div class="qrnum">'+esc(a.article_number||'—')+'</div><div class="qrname">'+esc(a.article_description||'Receiving Article')+'</div></div></div>'+
   quickDeliveryCell(history[0],'LATEST DELIVERY',familyId,a.article_number)+quickDeliveryCell(history[1],'PREV DELIVERY',familyId,a.article_number)+'</div>';
}
function quickSellingHtml(a,idx,seq){
 const uom=String(a.movement_uom||''),rows=Array.isArray(a.rows)?a.rows:[],active=rows.filter(r=>hasActivity(r.qty_7d)),inactiveRows=rows.filter(r=>!hasActivity(r.qty_7d));
 const hid='q-upc-'+idx+'-'+seq,mvt=num(a.movement_7d);
 const isLb=v=>['LB','LBS','POUND','POUNDS'].includes(String(v||'').trim().toUpperCase());
 const posRows=rows.filter(r=>num(r.qty_7d)!==null);
 const comparable=isLb(uom)&&posRows.every(r=>isLb(r.qty_uom||r.selling_uom||uom));
 const pos7=posRows.reduce((sum,r)=>sum+Number(r.qty_7d||0),0);
 const diff=comparable&&mvt!==null?Math.abs(mvt-pos7):null;
 const showSap=diff!==null&&diff>1.5;
 if(!showSap&&!rows.length)return '';
 const head=showSap?'<div class="qsaphead"><div><div class="qsaprole">SAP SELLING ARTICLE</div><div class="qsaptop"><span class="qsapnum">'+esc(a.article_number||'UNRESOLVED')+'</span></div></div>'+
   '<div class="qsapmetric"><small>SAP 7D MVT</small><b>'+fmt(a.movement_7d)+' '+esc(uom)+'</b><span>AVG/DAY · '+fmt(a.avg_qty_day)+' '+esc(uom)+'</span></div></div>':'';
 return '<section class="qsap'+(showSap?'':' nohead')+'">'+head+active.map(quickUpcHtml).join('')+hiddenUpcs(inactiveRows,hid)+'</section>';
}
function quickGroupedHtml(rows){
 return quickFamilyGroups(rows).slice(0,12).map((g,idx)=>{
   const uom=g.group_uom||'',receiptUom=g.family_receipt_7d_uom||uom||'',recon=String(g.reconciliation||'').toUpperCase();
   const familyHead='<div class="qfhead">'+
     '<div class="qfidentity"><div class="qlabel">FAMILY ARTICLE</div><div class="qfnum">'+esc(g.family_article||'—')+(g.family_receipt_verified?'<span class="qreceipt">O</span>':'')+'</div>'+
     '<div class="qfname">'+esc(g.family_name||'Unmapped Family')+'</div><div class="qmeta">'+esc(g.category||'')+(recon?' · '+(recon==='PASS'?'TOTAL SELLING MVT RECONCILED':'TOTAL SELLING MVT HOLD'):'')+'</div></div>'+
     '<div class="qffocus">'+
       '<div class="qffocusbox"><div><small>7D SELLING MVT</small><span>AVG/DAY · '+fmt(g.group_avg_qty_day)+' '+esc(uom)+'</span></div><b>'+fmt(g.group_qty_7d)+' '+esc(uom)+'</b></div>'+
       '<div class="qffocusbox receipt"><div><small>7D RECEIPT</small><span>PHYSICAL · DE-DUPED</span></div><b>'+fmt(g.family_receipt_7d_qty)+' '+esc(receiptUom)+'</b></div>'+
     '</div></div>';
   const receivingHtml=g.receiving.map(a=>quickReceivingRowHtml(a,g.family_id)).join('');
   const sellingHtml=(g.selling||[]).map((a,i)=>quickSellingHtml(a,idx,i)).join('');
   return '<section class="qfamily tone'+(idx%5)+'">'+familyHead+receivingHtml+sellingHtml+'</section>';
 }).join('');
}
function fitQuickUpcNames(){
 $$('.qupcname').forEach(el=>{
   el.style.fontSize='';el.style.letterSpacing='';
   let size=parseFloat(getComputedStyle(el).fontSize)||16;
   const available=el.clientWidth;if(!available)return;
   while(el.scrollWidth>available&&size>8){size-=0.5;el.style.fontSize=size+'px'}
   if(el.scrollWidth>available)el.style.letterSpacing='-.45px';
 });
}
function bindQuickRows(){
 $$('[data-upc]').forEach(x=>x.onclick=()=>openUpc(x.dataset.upc));
 $$('[data-qhide]').forEach(b=>b.onclick=()=>{const n=$('#'+CSS.escape(b.dataset.qhide));if(!n)return;const on=n.classList.toggle('on');b.textContent=(on?'Hide ':'Show ')+(b.dataset.noun||'inactive')+(on?' ▴':' ▾')});
 bindReceiptLinks();
 requestAnimationFrame(fitQuickUpcNames);
}
async function hydrateQuickPrices(rows,requestId,attempt=0){
 const upcs=[...new Set((rows||[])
   .filter(r=>hasActivity(r.qty_7d)&&String(r.upc||'').trim())
   .map(r=>String(r.upc).trim()))].slice(0,60);
 if(!upcs.length)return;
 try{
  const d=await api('/v1/yipman/quick-price-preview?upcs='+encodeURIComponent(upcs.join(',')),{timeoutMs:22000});
  if(requestId!==quickRequestSeq)return;
  const byUpc=new Map((d.rows||[]).map(r=>[String(r.upc||''),r]));
  $$('[data-upc]').forEach(card=>{
    const row=byUpc.get(String(card.dataset.upc||''));
    if(!row)return;
    const set=(sel,val)=>{const n=card.querySelector(sel);if(n)n.textContent=num(val)===null?'—':money(val)};
    const setPath=(sel,val,empty)=>{const n=card.querySelector(sel);if(n){const missing=num(val)===null;n.textContent=missing?empty:money(val);n.classList.toggle('qempty',missing)}};
    set('[data-q-current]',row.current_price);
    setPath('[data-q-tested]',row.tested_price,'Not set');
    const pricingWarming=['REFRESHING','WARMING'].includes(String(d.price_review_analysis_status||'').toUpperCase())||String(d.price_review_cache_status||'').toUpperCase()==='WARMING';
    setPath('[data-q-testing]',row.testing_price,pricingWarming?'…':'None');
    set('[data-q-comp-a]',row.company_price_a);
    set('[data-q-comp-b]',row.company_price_b);
    set('[data-q-comp-c]',row.company_price_c);
    const strip=card.querySelector('[data-qprice-status]');
    if(strip){
      strip.dataset.qpriceStatus=String(row.suggestion_status||'READY');
      strip.title='Current: '+String(row.current_price_source||'—')+(row.current_price_asof_date?' · '+String(row.current_price_asof_date):'')+
        ' | Tested: '+(num(row.tested_price)===null?'—':money(row.tested_price))+
        ' | Testing: '+(num(row.testing_price)===null?'—':money(row.testing_price))+
        ' | '+String(row.suggestion_reason||row.suggestion_status||'—');
    }
  });
  const pricingWarming=['REFRESHING','WARMING'].includes(String(d.price_review_analysis_status||'').toUpperCase())||String(d.price_review_cache_status||'').toUpperCase()==='WARMING';
  if(pricingWarming&&attempt<8){
    setTimeout(()=>{
      if(requestId===quickRequestSeq)hydrateQuickPrices(rows,requestId,attempt+1);
    },2500);
  }
 }catch(e){
  // Pricing is supplemental. Never blank otherwise valid Quick Check results.
  if(requestId!==quickRequestSeq)return;
  $$('[data-qprice-status="loading"]').forEach(x=>{x.dataset.qpriceStatus='unavailable';x.title='Price preview temporarily unavailable'});
 }
}

function quickReceiptDay(v){
 const m=String(v||'').match(/^(\d{4})-(\d{2})-(\d{2})/);if(!m)return '—';
 const dt=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]),12,0,0,0);
 return dt.toLocaleDateString(undefined,{weekday:'short'})+' '+Number(m[2])+'/'+Number(m[3]);
}
function bestSellerFamilyHtml(g,idx){
 const uom=g.group_uom||'',receiptUom=g.family_receipt_7d_uom||uom||'',history=(Array.isArray(g.family_receipt_history)?g.family_receipt_history:[]).slice(0,2);
 const count=num(g.family_receipt_7d_day_count);
 const recent=history.length?history.map(x=>'<button type="button" class="bestreceipt receiptlink" data-receipt-family="'+esc(g.family_id??'')+'" data-receipt-article="'+esc(g.family_article||'')+'" data-receipt-date="'+esc(x.date||'')+'"><span>'+esc(quickReceiptDay(x.date))+'</span><b>'+fmt(x.quantity)+' '+esc(x.uom||receiptUom)+'</b></button>').join(''):'<div class="bestreceipt"><span>No recent receipt</span><b>—</b></div>';
 return '<section class="bestfam tone'+(idx%5)+'"><div class="besttop"><div><div class="bestlabel">FAMILY ARTICLE</div><div class="bestnum">'+esc(g.family_article||'—')+'</div><div class="bestname">'+esc(g.family_name||'Unmapped Family')+'</div></div><div class="bestrank">#'+(idx+1)+'</div></div>'+
   '<div class="bestmetrics"><div class="bestmetric"><small>7D SELLING MVT</small><b>'+fmt(g.group_qty_7d)+' '+esc(uom)+'</b><span>AVG/DAY · '+fmt(g.group_avg_qty_day)+' '+esc(uom)+'</span></div>'+
   '<div class="bestmetric"><small>7D RECEIPT</small><b>'+fmt(g.family_receipt_7d_qty)+' '+esc(receiptUom)+'</b><span>'+(count===null?'—':fmt(count,0))+' RECEIPT DAY'+(count===1?'':'S')+' / 7D</span></div></div>'+
   '<div class="bestrecent"><div class="bestrecenthead"><span>RECENT RECEIPTS</span><span>LAST 2</span></div>'+recent+'</div></section>';
}
async function loadBestSellers(force=false){
 const box=$('#quickRows');
 if(bestSellerGroups&&!force){
   box.innerHTML='<div class="besthead"><div><h3>Best Sellers</h3><span>Family Articles only · 7D velocity</span></div><span class="bestsort">VELOCITY ↓</span></div>'+bestSellerGroups.map(bestSellerFamilyHtml).join('');bindReceiptLinks();return;
 }
 const requestId=++quickRequestSeq;lastQuickQuery='';box.innerHTML='<div class="loading">Loading best-selling families…</div>';
 try{
  const d=await api('/v1/yipman/best-sellers?limit=8',{timeoutMs:10000});
  if(requestId!==quickRequestSeq||$('#globalInput').value.trim())return;
  bestSellerGroups=(d.rows||[]).map(r=>({
    family_id:r.family_id,family_article:r.family_article,family_name:r.family_name,category:r.category,
    group_qty_7d:r.family_group_movement_7d,group_avg_qty_day:r.family_group_avg_qty_day,group_uom:r.family_group_movement_uom||'',
    family_receipt_history:Array.isArray(r.family_receipt_history)?r.family_receipt_history:[],family_receipt_7d_qty:r.family_receipt_7d_qty,
    family_receipt_7d_uom:r.family_receipt_7d_uom||'',family_receipt_7d_day_count:r.family_receipt_7d_day_count
  }));
  box.innerHTML='<div class="besthead"><div><h3>Best Sellers</h3><span>Family Articles only · 7D velocity</span></div><span class="bestsort">VELOCITY ↓</span></div>'+bestSellerGroups.map(bestSellerFamilyHtml).join('');bindReceiptLinks();
 }catch(e){if(requestId===quickRequestSeq)box.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
async function loadQuick(q){
 const query=String(q||'').trim(), box=$('#quickRows');
 if(!query){lastQuickQuery='';await loadBestSellers();return}
 const requestId=++quickRequestSeq;lastQuickQuery=query;box.innerHTML='<div class="loading">Searching current Quick Check…</div>';
 try{
  const d=await api('/v1/backoffice/inventory?category=ALL&limit=120&lightweight=true&q='+encodeURIComponent(query),{timeoutMs:18000});
  if(requestId!==quickRequestSeq)return;
  const rows=d.rows||[];
  if(!rows.length){box.innerHTML='<div class="empty">No matching items.</div>';return}
  box.innerHTML=quickGroupedHtml(rows);
  bindQuickRows();
  hydrateQuickPrices(rows,requestId);
 }catch(e){if(requestId===quickRequestSeq)box.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
$('#globalForm').onsubmit=e=>{e.preventDefault();const q=$('#globalInput').value.trim();if(!q)return;clearTimeout(quickSearchTimer);loadQuick(q);$('#globalInput').blur();$('#globalForm').classList.add('hide')};
$('#globalInput').addEventListener('input',()=>{if(current!=='quick')return;clearTimeout(quickSearchTimer);const q=$('#globalInput').value.trim();$('#quickClear').classList.toggle('on',!!q);if(!q){loadQuick('');return}quickSearchTimer=setTimeout(()=>loadQuick(q),260)});
$('#quickClear').onclick=()=>{$('#globalInput').value='';$('#quickClear').classList.remove('on');clearTimeout(quickSearchTimer);loadQuick('');$('#globalInput').focus()};
window.addEventListener('resize',()=>requestAnimationFrame(fitQuickUpcNames));

async function openUpc(upc){
 sheet('Loading…',upc,'<div class="loading">Loading current item detail…</div>');
 try{
  const d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc),{timeoutMs:16000});
  const oh=d.effective_oh||{}, q7=d.qty_7d||{};
  sheet(d.upc_name||upc,(d.upc||upc)+' · Family '+(d.family_article_number||'—'),'<div class="dmetrics"><div class="dm"><b>'+fmt(oh.quantity)+' '+esc(oh.uom||'')+'</b><span>EFFECTIVE OH</span></div><div class="dm"><b>'+fmt(d.upc_velocity_7d)+'</b><span>'+esc(d.qty_uom||d.selling_uom||'UNIT')+' / DAY</span></div><div class="dm"><b>'+money(d.current_price)+'</b><span>CURRENT '+esc(d.current_price_type||'PRICE')+'</span></div></div><div class="detail"><b>7D sales</b><br>'+fmt(q7.sold_quantity)+' '+esc(d.qty_uom||'')+' across '+fmt(q7.supported_day_count,0)+' completed data day(s).<br><br><b>Current price source</b><br>'+esc(d.current_price_source||'—')+(d.current_price_asof_date?' · '+esc(d.current_price_asof_date):'')+'<br><br><b>Current cost</b><br>'+money(d.current_cost_per_selling_unit)+' / '+esc(d.selling_uom||'unit')+'<br><br><b>OH status</b><br>'+esc(oh.status||'—')+(oh.reason?'<br>'+esc(oh.reason):'')+'</div>');
 }catch(e){sheet('Unable to load',upc,'<div class="detail">'+esc(e.message)+'</div>')}
}

function dateLocal(v){
 const m=String(v||'').match(/^(\d{4})-(\d{2})-(\d{2})$/);
 if(!m)return null;
 return new Date(Number(m[1]),Number(m[2])-1,Number(m[3]),12,0,0,0);
}
function orderWeekdayInfo(v){
 const d=dateLocal(v);if(!d)return null;
 return orderObservedWeekdays.get(d.getDay()===0?6:d.getDay()-1)||null;
}
function isObservedDate(v){return !!orderWeekdayInfo(v)?.observed}
function isPreferredDate(v){return !!orderWeekdayInfo(v)?.preferred}
function nextObservedAfter(v){
 const start=dateLocal(v)||new Date();
 for(const preferredOnly of [true,false]){
  for(let i=1;i<=21;i++){
   const d=new Date(start);d.setDate(d.getDate()+i);
   const wd=d.getDay()===0?6:d.getDay()-1;
   const info=orderObservedWeekdays.get(wd);
   if(info?.observed&&(!preferredOnly||info?.preferred))return iso(d);
  }
 }
 const fallback=new Date(start);fallback.setDate(fallback.getDate()+7);return iso(fallback);
}
function updateOrderWindowUI(){
 if(!orderDate||!orderNextDate)return;
 $('#deliveryDateText').textContent=appDate(orderDate);
 $('#nextDeliveryDateText').textContent=appDate(orderNextDate);
 $('#deliveryObservedText').textContent=isPreferredDate(orderDate)?'★ Preferred observed delivery day':isObservedDate(orderDate)?'★ Observed delivery day':'Manual delivery date';
 $('#nextObservedText').textContent=isPreferredDate(orderNextDate)?'★ Preferred observed delivery day':isObservedDate(orderNextDate)?'★ Observed delivery day':'Manual delivery date';
 $('#deliveryDateCard').classList.toggle('pick',orderSelectMode==='DELIVERY');
 $('#nextDeliveryDateCard').classList.toggle('pick',orderSelectMode==='NEXT');
 const end=dateLocal(orderNextDate);if(end)end.setDate(end.getDate()-1);
 $('#orderCoverageText').textContent=appDate(orderDate)+' → '+(end?appDate(iso(end)):'—');
 $('#orderCoverageSub').textContent=orderMode==='PROMOTION'
  ?'Each day is forecast as promotion-price or regular-price usage for the selected promotion list.'
  :'Predict usage from delivery through the day before next delivery using the best available data at viewing time.';
}
function upcomingWeekday(jsWeekday){
 const d=new Date();d.setHours(12,0,0,0);
 const add=(jsWeekday-d.getDay()+7)%7;
 d.setDate(d.getDate()+add);
 return iso(d);
}
function setPromotionDefaultDates(){
 if(!$('#promoWeeklyStart').value)$('#promoWeeklyStart').value=upcomingWeekday(4);
 if(!$('#promoWeekendStart').value)$('#promoWeekendStart').value=upcomingWeekday(5);
}
async function runActiveOrdering(){
 if(orderMode==='PROMOTION')return loadPromotionOrder();
 return loadOrder(orderDate);
}
function buildDays(){
 const bar=$('#dayBar');if(!bar)return;bar.innerHTML='';
 for(let offset=0;offset<=20;offset++){
  const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+offset);
  const dayIso=iso(d), wd=d.getDay()===0?6:d.getDay()-1, obs=orderObservedWeekdays.get(wd);
  const b=document.createElement('button');
  b.className='day'+(offset===0?' today':'')+(obs?.observed?' observed':'')+(obs?.preferred?' preferred':'')+(dayIso===orderDate?' delivery':'')+(dayIso===orderNextDate?' next':'');
  b.dataset.offset=offset;b.dataset.date=dayIso;
  b.innerHTML='<b>'+d.toLocaleDateString(undefined,{weekday:'short'}).toUpperCase()+'</b><strong>'+d.getDate()+'</strong><span>'+(obs?.observed?'OBS · '+Number(obs.family_count||0):d.toLocaleDateString(undefined,{month:'short'}).toUpperCase())+'</span>';
  b.onclick=()=>{
   if(orderSelectMode==='DELIVERY'){
    orderDate=dayIso;
    // A new Delivery date gets a fresh default Next Delivery. The user can
    // still override Next Delivery immediately afterward.
    orderNextDate=nextObservedAfter(orderDate);
    orderSelectMode='NEXT';
   }else{
    if(dayIso<=orderDate){toast('Next delivery must be after delivery date');return}
    orderNextDate=dayIso;orderSelectMode='DELIVERY';
   }
   buildDays();updateOrderWindowUI();runActiveOrdering();
  };
  bar.appendChild(b);
 }
 requestAnimationFrame(()=>bar.querySelector('.day.delivery')?.scrollIntoView({behavior:'auto',block:'nearest',inline:'center'}));
}
async function initOrdering(force=false){
 if(orderInitPromise&&!force)return orderInitPromise;
 orderInitPromise=(async()=>{
  if(!orderCalendarLoaded||force){
   try{
    const d=await api('/v1/yipman/ordering-calendar?lookback_days=180',{timeoutMs:18000});
    orderObservedWeekdays=new Map((d.rows||[]).map(x=>[Number(x.weekday_number),x]));
    orderCalendarLoaded=true;
    if(!orderDate&&d.default_delivery_date)orderDate=String(d.default_delivery_date);
    if(!orderNextDate&&d.default_next_delivery_date)orderNextDate=String(d.default_next_delivery_date);
   }catch(e){
    orderObservedWeekdays=new Map([[1,{observed:true,family_count:1}],[4,{observed:true,family_count:1}]]);
    if(orderMode==='REGULAR')$('#orderStatus').textContent='Observed calendar fallback · '+e.message;
    else $('#promoOrderStatus').textContent='Observed calendar fallback · '+e.message;
   }
  }
  if(!orderDate){
   const base=new Date();base.setHours(12,0,0,0);
   for(const preferredOnly of [true,false]){
    for(let i=1;i<=14&&!orderDate;i++){
     const d=new Date(base);d.setDate(d.getDate()+i);
     const wd=d.getDay()===0?6:d.getDay()-1, info=orderObservedWeekdays.get(wd);
     if(info?.observed&&(!preferredOnly||info?.preferred)){orderDate=iso(d);break}
    }
   }
   if(!orderDate){const d=new Date(base);d.setDate(d.getDate()+1);orderDate=iso(d)}
  }
  if(!orderNextDate||orderNextDate<=orderDate)orderNextDate=nextObservedAfter(orderDate);
  setPromotionDefaultDates();
  buildDays();updateOrderWindowUI();
  if(orderMode==='PROMOTION')await loadPromotionLists();
  await runActiveOrdering();
 })();
 try{return await orderInitPromise}finally{orderInitPromise=null}
}
$('#deliveryDateCard').onclick=()=>{orderSelectMode='DELIVERY';updateOrderWindowUI()};
$('#nextDeliveryDateCard').onclick=()=>{orderSelectMode='NEXT';updateOrderWindowUI()};

async function loadPromotionLists(){
 try{
  const data=await api('/v1/yipman/promotion-lists?limit=30',{timeoutMs:12000});
  const rows=data.rows||[];
  const select=$('#promoListSelect');
  const keep=String(promoListId||select.value||'');
  select.innerHTML='<option value="">Choose promotion list…</option>'+rows.map(x=>'<option value="'+esc(x.list_id)+'">'+esc(x.list_name)+' · '+fmt(x.ready_count,0)+' ready'+(Number(x.review_count||0)?' · '+fmt(x.review_count,0)+' review':'')+'</option>').join('');
  if(keep&&rows.some(x=>String(x.list_id)===keep)){select.value=keep;promoListId=Number(keep)}
  else if(!promoListId&&rows.length){promoListId=Number(rows[0].list_id);select.value=String(promoListId)}
  promoListsLoaded=true;
  if(promoListId)await loadPromotionListDetail(false);
 }catch(e){
  $('#promoListStatus').textContent='Promotion lists unavailable · '+e.message;
 }
}
async function loadPromotionListDetail(recalculate=true){
 if(!promoListId){promoListDetail=null;$('#promoListStatus').textContent='Choose or import a promotion list.';return}
 try{
  const d=await api('/v1/yipman/promotion-lists/'+promoListId,{timeoutMs:12000});
  promoListDetail=d;
  const weekly=(d.items||[]).filter(x=>x.mapping_status==='READY'&&x.promotion_type==='WEEKLY').length;
  const weekend=(d.items||[]).filter(x=>x.mapping_status==='READY'&&x.promotion_type==='WEEKEND').length;
  $('#promoListStatus').textContent=String(d.list_name||'Promotion List')+' · '+fmt(d.ready_count,0)+' READY · '+fmt(d.review_count,0)+' REVIEW';
  $('#promoSummary').innerHTML='<span class="promo-type weekly">WEEKLY '+weekly+'</span><span class="promo-type weekend">WEEKEND '+weekend+'</span>'+(Number(d.review_count||0)?'<span class="promo-type" style="background:#ffe8e8;color:#9a2f2f">REVIEW '+fmt(d.review_count,0)+'</span>':'');
  if(recalculate)await loadPromotionOrder();
 }catch(e){
  promoListDetail=null;$('#promoListStatus').textContent='Unable to load promotion list · '+e.message;
 }
}
$('#promoListSelect').onchange=async e=>{
 promoListId=e.target.value?Number(e.target.value):null;
 promoTempOH.clear();
 await loadPromotionListDetail(true);
};
$('#promoImportBtn').onclick=()=>$('#promoFileInput').click();
$('#promoFileInput').onchange=async e=>{
 const file=e.target.files?.[0];if(!file)return;
 const weekly=$('#promoWeeklyStart').value, weekend=$('#promoWeekendStart').value;
 if(!weekly||!weekend){toast('Choose Weekly and Weekend start dates first');e.target.value='';return}
 $('#promoListStatus').textContent='Importing '+file.name+'…';
 try{
  const form=new FormData();form.append('file',file);
  const qs=new URLSearchParams({list_name:file.name,weekly_start_date:weekly,weekend_start_date:weekend});
  const d=await api('/v1/yipman/promotion-lists/import?'+qs.toString(),{method:'POST',body:form,timeoutMs:45000});
  promoListId=Number(d.list_id);promoTempOH.clear();
  await loadPromotionLists();
  $('#promoListSelect').value=String(promoListId);
  await loadPromotionListDetail(true);
  toast('Promotion list imported');
 }catch(err){
  $('#promoListStatus').textContent='Import failed · '+err.message;
 }finally{e.target.value=''}
};

function renderPromotionRows(data){
 promoLastRows=Array.isArray(data?.rows)?data.rows:[];
 const reviewItems=(promoListDetail?.items||[]).filter(x=>x.mapping_status!=='READY');
 const reviewHtml=reviewItems.length?'<div class="promo-review"><b>'+reviewItems.length+' list item(s) need review</b><br>'+reviewItems.slice(0,5).map(x=>esc(x.raw_item_code||x.raw_description||'Item')+' · '+esc(x.validation_error||x.mapping_status)).join('<br>')+(reviewItems.length>5?'<br>+'+(reviewItems.length-5)+' more':'')+'</div>':'';
 $('#promoRows').innerHTML=reviewHtml+promoLastRows.map((r,i)=>{
  const p=r.promotion_list_item||{}, type=String(p.promotion_type||'').toUpperCase();
  const temp=!!r.temporary_oh_override_used;
  const oh=r.current_oh_for_calculation;
  const promoNeed=r.forecast_promotion_coverage, regNeed=r.forecast_regular_coverage, totalNeed=r.forecast_coverage_usage;
  return '<div class="promo-card"><div class="promo-card-head"><div><b>'+esc(r.family_article_name||p.family_name||r.family_article_number||'Family')+'</b><small>Family '+esc(r.family_article_number||'—')+' · SALE '+money(p.promotion_price)+' · '+appDate(p.promotion_start_date)+' → '+appDate(p.promotion_end_date)+'</small></div><span class="promo-badge '+(type==='WEEKLY'?'weekly':'weekend')+'">'+esc(type||'PROMO')+'</span></div>'+
   '<div class="promo-metrics"><div class="promo-metric '+(temp?'temp':'')+'" data-promo-oh="'+i+'"><small>'+(temp?'TEMP TRUE STOCK':'CURRENT OH ✎')+'</small><b>'+fmtNullable(oh)+' '+esc(r.uom||'')+'</b></div><div class="promo-metric"><small>EST OH @ DELIVERY</small><b>'+fmtNullable(r.projected_oh_at_delivery)+' '+esc(r.uom||'')+'</b></div><div class="promo-metric"><small>COVERAGE NEED</small><b>'+fmtNullable(totalNeed)+' '+esc(r.uom||'')+'</b></div></div>'+
   '<div class="promo-order"><small>SUGGESTED '+esc(appDate(data.delivery_date))+' ORDER</small><b>'+fmtNullable(r.suggested_order_qty)+' '+esc(r.suggested_order_uom||r.uom||'')+'</b><div class="promo-break">Promo need '+fmtNullable(promoNeed)+' · Regular need '+fmtNullable(regNeed)+(temp?' · TEMP OH only for this calculation':'')+'</div></div></div>';
 }).join('')||reviewHtml||'<div class="empty">No calculable promotion items.</div>';
 $$('[data-promo-oh]').forEach(x=>x.onclick=()=>openPromoTempOH(promoLastRows[Number(x.dataset.promoOh)]));
}
async function loadPromotionOrder(){
 if(orderMode!=='PROMOTION')return;
 if(!promoListId){$('#promoOrderStatus').textContent='Choose or import a promotion list.';$('#promoRows').innerHTML='<div class="empty">No promotion list selected.</div>';return}
 if(!orderDate||!orderNextDate)return;
 $('#promoOrderStatus').textContent='Calculating promotion + regular usage for '+appDate(orderDate)+' → '+appDate(orderNextDate)+'…';
 try{
  const body={
   list_id:promoListId,
   delivery_date:orderDate,
   next_delivery_date:orderNextDate,
   temporary_oh_overrides:[...promoTempOH.values()]
  };
  const data=await api('/v1/yipman/promotion-ordering/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),timeoutMs:45000});
  $('#promoOrderStatus').textContent=fmt(data.order_count,0)+' need order · '+fmt(data.suggestion_count,0)+' calculated · coverage through '+appDate(data.coverage_end_date)+' · temporary OH values are NOT saved';
  renderPromotionRows(data);
 }catch(e){
  $('#promoOrderStatus').textContent='Promotion calculation unavailable · '+e.message;
  $('#promoRows').innerHTML='<div class="empty">'+esc(e.message)+'</div>';
 }
}
function openPromoTempOH(r){
 if(!r)return;
 const fid=Number(r.family_id), existing=promoTempOH.get(fid);
 const value=existing?.quantity??r.current_oh_system??r.current_oh_for_calculation??0;
 sheet(
  r.family_article_name||'Temporary True Stock',
  'Promotion Ordering only · nothing is written to FULL MYSQL',
  '<div class="detail"><b>System OH</b><br>'+fmtNullable(r.current_oh_system)+' '+esc(r.uom||'')+'<br><br><b>Observed True Stock</b><br><input id="promoOHInput" type="number" min="0" step="0.1" inputmode="decimal" value="'+esc(value)+'" style="width:100%;font-size:24px;font-weight:900;padding:10px;border:2px solid #d6dde3;border-radius:12px"><br><br><div class="estimatebar">Temporary reference only. Save & Recalculate does not create True Stock, PI, dumping, OH history, or any database inventory change.</div><div class="actions"><button id="promoOHReset">RESET TO SYSTEM OH</button><button class="primary" id="promoOHSave">SAVE & RECALCULATE</button></div></div>'
 );
 $('#promoOHSave').onclick=()=>{
  const qty=Number($('#promoOHInput').value);
  if(!Number.isFinite(qty)||qty<0){toast('Enter a valid stock quantity');return}
  promoTempOH.set(fid,{family_id:fid,family_article_number:r.family_article_number,quantity:qty,uom:r.uom});
  closeSheet(true);setTimeout(loadPromotionOrder,80);
 };
 $('#promoOHReset').onclick=()=>{
  promoTempOH.delete(fid);closeSheet(true);setTimeout(loadPromotionOrder,80);
 };
}
$$('[data-order-mode]').forEach(b=>b.onclick=()=>{
 orderMode=b.dataset.orderMode;
 $$('[data-order-mode]').forEach(x=>x.classList.toggle('on',x===b));
 $('#regularOrderPanel').classList.toggle('hide',orderMode!=='REGULAR');
 $('#promotionOrderPanel').classList.toggle('hide',orderMode!=='PROMOTION');
 updateOrderWindowUI();
 if(orderMode==='PROMOTION')loadPromotionLists().then(()=>loadPromotionOrder());
 else loadOrder(orderDate);
});
function receiptTracePairs(r){
 const events=Array.isArray(r?.receipt_events)?r.receipt_events:[];
 const pairs=[], seen=new Set();
 events.forEach(x=>{
  const po=String(x?.purchase_order||'').trim();
  const gr=String(x?.gr_number||'').trim();
  const basis=String(x?.receipt_stage_basis||'').toUpperCase();
  if(!po&&!gr)return;
  const traceLabel=gr?'GR '+gr:'GR UNRESOLVED';
  const key=po+'|'+traceLabel;
  if(seen.has(key))return;
  seen.add(key);pairs.push({po,gr,traceLabel,basis,missingGr:!gr});
 });
 return pairs;
}
function receiptTraceHtml(r){
 const pairs=receiptTracePairs(r), shown=pairs.slice(0,3);
 if(!shown.length)return '';
 return '<div class="rtrace">'+shown.map(p=>
  '<div class="rtrace-line"><span class="rpo">PO '+esc(p.po||'—')+'</span><span class="rtrace-arrow">→</span><span class="rgr'+(p.missingGr?' unresolved':'')+'">'+esc(p.traceLabel||'GR UNRESOLVED')+'</span></div>'
 ).join('')+(pairs.length>shown.length?'<div class="rtrace-more">+'+(pairs.length-shown.length)+' more PO / GR pair'+(pairs.length-shown.length===1?'':'s')+'</div>':'')+'</div>';
}
function receiptMovementLabel(x){
 const s=String(x?.receipt_stage_basis||'').toUpperCase();
 if(s.startsWith('101_102'))return '101 physical GR';
 if(s.startsWith('107_109'))return '109 physical GR · 107 cost stage';
 if(s.startsWith('109_110'))return '109/110 physical GR';
 return s||'—';
}
function bindReceiptLinks(){
 $$('.receiptlink[data-receipt-family][data-receipt-date]').forEach(el=>{
  el.onclick=e=>{e.stopPropagation();openReceiptDetail(el)};
 });
}
async function openReceiptDetail(el){
 const fid=String(el.dataset.receiptFamily||'').trim(),day=String(el.dataset.receiptDate||'').trim(),article=String(el.dataset.receiptArticle||'').trim();
 if(!fid||!day)return;
 sheet('Receipt Details','Loading '+esc(appDate(day))+'…','<div class="loading">Loading canonical receipt event…</div>');
 try{
  const qs=new URLSearchParams({family_id:fid,receipt_date:day});
  if(article)qs.set('article_number',article);
  const d=await api('/v1/yipman/receipt-event?'+qs.toString(),{timeoutMs:16000});
  const events=Array.isArray(d.events)?d.events:[];
  const trace=events.length?events.map(x=>{
   const gr=x.gr_number?'GR '+x.gr_number:'GR UNRESOLVED';
   const po=x.purchase_order?'PO '+x.purchase_order:'PO —';
   const qty=x.base_receipt_quantity!=null?x.base_receipt_quantity:x.receipt_quantity;
   const uom=x.base_receipt_uom||x.receipt_uom||'';
   return '<div class="receipt-event"><div class="receipt-pair">'+esc(po)+' → '+esc(gr)+'</div><div class="receipt-meta">Article '+esc(x.article_number||'—')+' · '+fmt(qty)+' '+esc(uom)+' · '+esc(receiptMovementLabel(x))+(x.vendor_code?' · Vendor '+esc(x.vendor_code):'')+(x.gr_number_source==='RAW_REFERENCE_Q_5014'?' · GR from Reference':x.gr_number_source==='RAW_ROW_5014_SCAN'?' · GR from MVT row':'')+'</div></div>';
  }).join(''):'<div class="empty">No canonical receipt event found for this date.</div>';
  sheet(
   d.family_name||'Receipt Details',
   'Family '+esc(d.family_article||'—')+' · '+esc(appDate(d.receipt_date||day)),
   '<div class="dmetrics"><div class="dm"><b>'+fmtNullable(d.receipt_qty)+' '+esc(d.receipt_uom||'')+'</b><span>RECEIVED</span></div><div class="dm"><b>'+fmt(d.receipt_event_count,0)+'</b><span>EVENTS</span></div><div class="dm"><b>'+fmt(d.purchase_order_count,0)+' / '+fmt(d.gr_number_count,0)+'</b><span>PO / GR</span></div></div>'+
   '<div class="detail"><b>Receipt date</b><br>'+esc(appDate(d.receipt_date||day))+(article?'<br><br><b>Receiving article</b><br>'+esc(article):'')+'<br><br><b>PO → GR receipt trace</b>'+trace+'<br><b>Basis</b><br>Canonical physical receipt event. 101 is a direct receipt; for a 107 + 109 flow, 109 supplies physical received quantity while 107 remains cost evidence only.</div>'
  );
 }catch(e){
  sheet('Receipt Details','Family '+esc(fid)+' · '+esc(appDate(day)),'<div class="empty">'+esc(e.message)+'</div>');
 }
}
function fmtNullable(v,d=1){return v===null||v===undefined||v===''?'—':fmt(v,d)}
function orderQty(r){
 if(r?.suggested_delivery_qty===null||r?.suggested_delivery_qty===undefined||r?.suggested_delivery_qty==='')return null;
 const n=Number(r.suggested_delivery_qty);return Number.isFinite(n)?n:null;
}
function orderState(r){
 const explicit=String(r?.roster_status||'').toUpperCase();
 if(['ORDER','ZERO_ORDER','REVIEW'].includes(explicit))return explicit;
 const q=orderQty(r);return q===null?'REVIEW':q>0?'ORDER':'ZERO_ORDER';
}
function orderReasonLabel(reason){
 const x=String(reason||'').toUpperCase();
 const labels={
  'FAMILY_UOM_UNRESOLVED':'UOM',
  'OH_TO_FAMILY_DEMAND_UOM_UNRESOLVED':'OH / UOM',
  'REGULAR_BASELINE_UNAVAILABLE':'BASELINE',
  'NO_28D_SALES':'NO 28D SALES',
  'NO_7D_VELOCITY':'NO 7D VELOCITY',
  'ORDERING_CALCULATION_UNAVAILABLE':'CALCULATION'
 };
 return labels[x]||x.replaceAll('_',' ')||'REVIEW';
}
function renderOrderRoster(rows,data,h,stale){
 lastOrderRows=Array.isArray(rows)?rows:[];
 lastOrderData=data||{};
 lastOrderStale=!!stale;
 const all=lastOrderRows;
 const summary=data?.roster_summary||{};
 const counts={
  total:Number(summary.observed_family_count??all.length),
  order:Number(summary.order_count??all.filter(r=>orderState(r)==='ORDER').length),
  zero:Number(summary.zero_order_count??all.filter(r=>orderState(r)==='ZERO_ORDER').length),
  review:Number(summary.review_count??all.filter(r=>orderState(r)==='REVIEW').length)
 };
 $('#orderSummary').textContent='OBSERVED '+counts.total+' · ORDER '+counts.order+' · 0 ORDER '+counts.zero+' · REVIEW '+counts.review;
 let visible=all.filter(r=>orderFilter==='ALL'||orderState(r)===orderFilter);
 const dos=r=>{const v=r?.details?.dos;if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null};
 const obs=r=>Number(r?.delivery_day_observed_count||0);
 const conf=r=>({HIGH:0,MEDIUM:1,LOW:2,NONE:3}[String(r?.delivery_day_confidence||'NONE').toUpperCase()]??3);
 visible=[...visible].sort((a,b)=>{
  if(orderSort==='QTY')return (orderQty(b)??-1)-(orderQty(a)??-1)||String(a.family_name||'').localeCompare(String(b.family_name||''));
  if(orderSort==='DOS')return (dos(a)??999999)-(dos(b)??999999)||String(a.family_name||'').localeCompare(String(b.family_name||''));
  if(orderSort==='OBSERVED')return obs(b)-obs(a)||String(a.family_name||'').localeCompare(String(b.family_name||''));
  if(orderSort==='NAME')return String(a.family_name||'').localeCompare(String(b.family_name||''));
  const rank=r=>orderState(r)==='ORDER'?0:orderState(r)==='REVIEW'?1:2;
  return rank(a)-rank(b)||conf(a)-conf(b)||((orderQty(b)??-1)-(orderQty(a)??-1))||String(a.family_name||'').localeCompare(String(b.family_name||''));
 });
 renderedOrderRows=visible;
 $('#orderStatus').innerHTML=stale
  ? '<div class="estimatebar">BEST AVAILABLE · POS '+esc(h?.pos_data_through||'—')+' · MVT '+esc(h?.movement_data_through||'—')+'. Missing source dates are ignored, not zero-filled; missing MVT days are forecast forward.</div>'
  : esc(data?.selected_delivery_weekday||'Selected day')+' · complete observed-delivery roster';
 $('#orderRows').innerHTML=visible.map((r,i)=>{
  const state=orderState(r), q=orderQty(r), reason=orderReasonLabel(r.roster_reason);
  const cls=(r.attention?' urgent':'')+(state==='REVIEW'?' review':state==='ZERO_ORDER'?' zero':'');
  const stateLabel=state==='ORDER'?'ORDER':state==='REVIEW'?'REVIEW':'0 ORDER';
  const orderText=state==='REVIEW'?'REVIEW':fmtNullable(q);
  const orderSub=state==='REVIEW'?reason:esc(r.suggested_delivery_uom||'');
  const stockout=r.pre_delivery_stockout_risk?'<span class="order-risk">STOCKOUT BEFORE DELIVERY</span>':'';
  const lowconf=String(r.delivery_day_confidence||'').toUpperCase()==='LOW'?'<span class="order-lowconf">LOW DELIVERY CONF.</span>':'';
  return '<div class="orow'+cls+'" data-order="'+i+'"><div><div class="name">'+esc(r.family_name||r.family_article||'Family')+'<span class="orderstate '+(state==='ORDER'?'order':state==='REVIEW'?'review':'')+'">'+stateLabel+'</span>'+stockout+lowconf+'</div><div class="sub">Receiving '+esc(r.receiving_article||'—')+' · '+esc(r.ordering_frequency||'')+' · '+fmt(r.delivery_day_observed_count,0)+' observed '+esc(r.delivery_day||'day')+(r.roster_reason?' · '+esc(reason):'')+(r.estimate_only?' · ESTIMATE':'')+'</div></div><div class="cell">'+fmtNullable(r.oh)+'<span>'+esc(r.oh_uom||'')+'</span></div><div class="cell">'+orderText+'<span>'+orderSub+'</span></div></div>';
 }).join('')||'<div class="empty">No rows match this filter. The complete observed roster has '+counts.total+' families.</div>';
 $$('[data-order]').forEach(x=>x.onclick=()=>openOrder(renderedOrderRows[Number(x.dataset.order)]));
}
$('#orderFilter').onchange=e=>{orderFilter=e.target.value;renderOrderRoster(lastOrderRows,lastOrderData,lastOrderData?.data_health||{},lastOrderStale)};
$('#orderSort').onchange=e=>{orderSort=e.target.value;renderOrderRoster(lastOrderRows,lastOrderData,lastOrderData?.data_health||{},lastOrderStale)};
async function loadOrder(value){
 clearTimeout(orderRetryTimer);orderRetryTimer=null;
 const requestId=++orderRequestSeq;
 let d=null;
 if(typeof value==='string')d=dateLocal(value);
 else{d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+Number(value||0))}
 if(!d)return;
 orderDate=iso(d);
 const requestedDate=orderDate, requestedNext=orderNextDate;
 const windowKey=requestedDate+'|'+String(requestedNext||'');
 if(orderRetryWindowKey!==windowKey){orderRetryWindowKey=windowKey;orderRetryCount=0}
 buildDays();updateOrderWindowUI();
 const today0=new Date();today0.setHours(12,0,0,0);
 const isPast=d<today0;
 $('#orderTools').style.display=isPast?'none':'grid';
 $('#orderCol1').textContent='FAMILY / RECEIVING';
 $('#orderCol2').textContent=isPast?'RECEIPT':'OH';
 $('#orderCol3').textContent=isPast?'UOM':'ORDER';
 if(!isPast&&lastOrderWindowKey!==windowKey){
   $('#orderSummary').textContent='CALCULATING · '+appDate(requestedDate)+' → '+appDate(requestedNext);
 }
 $('#orderStatus').textContent=(isPast?'Loading delivery history for ':'Loading ')+d.toLocaleDateString(undefined,{weekday:'long',month:'short',day:'numeric'})+'…';
 $('#orderRows').innerHTML='<div class="loading">'+(isPast?'Checking actual canonical receipts…':'Checking receipt history, OH and sales…')+'</div>';
 const url='/v1/yipman/ordering-review?category=ALL&delivery_date='+requestedDate+(!isPast&&requestedNext?'&next_delivery_date='+encodeURIComponent(requestedNext):'');
 try{
  let data=null;
  for(let i=0;i<10;i++){
   try{data=await api(url,{timeoutMs:26000})}catch(e){if(requestId!==orderRequestSeq)return;if(/timed out|failed to fetch|network|aborted/i.test(String(e?.message||''))&&i<9){$('#orderStatus').textContent='Still calculating '+appDate(orderDate)+' · retrying best-available ordering data';await new Promise(r=>setTimeout(r,1200));continue}throw e}
   if(requestId!==orderRequestSeq)return;
   const status=String(data.analysis_status||'').toUpperCase();
   if(!['REFRESHING','WARMING','STALE_DATA_REFRESHING'].includes(status)&&!['WARMING','STALE_DATA_REFRESHING'].includes(String(data.cache_status||'').toUpperCase()))break;
   $('#orderStatus').textContent='Calculating '+appDate(orderDate)+' · receipt cadence first';
   await new Promise(r=>setTimeout(r,1500));
  }
  const finalStatus=String(data?.analysis_status||'').toUpperCase(), h=data?.data_health||{};
  if(['REFRESHING','WARMING'].includes(finalStatus)||['WARMING','STALE_DATA_REFRESHING'].includes(String(data?.cache_status||'').toUpperCase())){
    orderRetryCount++;
    const delay=Math.min(8000,2500+Math.max(0,orderRetryCount-1)*500);
    const err=data?.refresh_error;
    $('#orderStatus').textContent=(err?'Retrying after calculation error · ':'Still calculating · ')+'auto-refreshing '+appDate(requestedDate)+' → '+appDate(requestedNext);
    $('#orderRows').innerHTML='<div class="loading">Yipman is calculating receipt history, OH and predicted usage. This page will update automatically'+(err?'<br><br>'+esc(err):'')+'.</div>';
    orderRetryTimer=setTimeout(()=>{
      if(current==='order'&&orderMode==='REGULAR'&&orderDate===requestedDate&&orderNextDate===requestedNext){
        loadOrder(requestedDate);
      }
    },delay);
    return;
  }
  if(finalStatus==='REFRESH_FAILED'){
    clearTimeout(orderRetryTimer);orderRetryTimer=null;
    $('#orderSummary').textContent='CALCULATION FAILED';
    $('#orderStatus').textContent='Ordering calculation failed';
    $('#orderRows').innerHTML='<div class="empty">'+esc(data?.refresh_error||'Pull down to retry.')+'</div>';
    return;
  }
  if(finalStatus==='UNAVAILABLE'){
    const missing=(h.missing_required_sources||[]).join(' + ')||'POS / MVT';
    $('#orderStatus').textContent='Ordering unavailable';
    $('#orderRows').innerHTML='<div class="empty">No usable POS or MVT history is available for a best-available estimate.<br>POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'<br>'+esc(missing)+'</div>';
    return;
  }

  const rows=data?.rows||[];
  if(data?.history_mode||finalStatus==='HISTORY_READY'){
    $('#orderCol2').textContent='RECEIPT';
    $('#orderCol3').textContent='UOM';
    $('#orderStatus').textContent=(data.selected_delivery_weekday||'Past date')+' '+appDate(orderDate)+' · '+rows.length+' family receipt'+(rows.length===1?'':'s')+(data.movement_date_available?'':' · no canonical MVT snapshot for this date');
    $('#orderRows').innerHTML=rows.map((r,i)=>'<div class="orow" data-order-history="'+i+'"><div><div class="name">'+esc(r.family_name||r.family_article||'Family')+'</div><div class="sub">Receiving '+esc(r.receiving_article||'—')+' · '+fmt(r.receipt_event_count,0)+' receipt event'+(Number(r.receipt_event_count||0)===1?'':'s')+'</div>'+receiptTraceHtml(r)+'</div><div class="cell">'+fmt(r.receipt_qty)+'<span>ACTUAL</span></div><div class="cell">'+esc(r.receipt_uom||'—')+'<span>'+esc(r.receipt_qty_basis||'')+'</span></div></div>').join('')||'<div class="empty">No positive canonical physical 101/109 receipt was recorded on '+esc(appDate(orderDate))+'.</div>';
    $$('[data-order-history]').forEach(x=>x.onclick=()=>openOrderHistory(rows[Number(x.dataset.orderHistory)]));
    return;
  }

  $('#orderCol2').textContent='OH';
  $('#orderCol3').textContent='ORDER';
  const stale=String(h.status||'').toUpperCase()==='STALE_ESTIMATE_AVAILABLE'||finalStatus.startsWith('READY_STALE_ESTIMATE');
  lastOrderWindowKey=windowKey;
  orderRetryCount=0;
  clearTimeout(orderRetryTimer);orderRetryTimer=null;
  renderOrderRoster(rows,data,h,stale);
 }catch(e){
  if(requestId!==orderRequestSeq)return;
  $('#orderStatus').textContent='Ordering temporarily unavailable';
  $('#orderRows').innerHTML='<div class="empty">'+esc(e.message)+'<br>Pull down to retry.</div>';
 }
}
function openOrderHistory(r){
 const events=Array.isArray(r.receipt_events)?r.receipt_events:[];
 const pairs=receiptTracePairs(r);
 const poCount=new Set(pairs.map(x=>x.po).filter(Boolean)).size;
 const grCount=new Set(pairs.map(x=>x.gr).filter(Boolean)).size;
 const unresolvedGrCount=pairs.filter(x=>!x.gr).length;
 sheet(r.family_name||'Delivery history','Family '+esc(r.family_article||'—')+' · '+esc(appDate(r.selected_delivery_date||orderDate)),
 '<div class="dmetrics"><div class="dm"><b>'+fmt(r.receipt_qty)+' '+esc(r.receipt_uom||'')+'</b><span>ACTUAL RECEIPT</span></div><div class="dm"><b>'+fmt(poCount,0)+'</b><span>PO #</span></div><div class="dm"><b>'+fmt(grCount,0)+(unresolvedGrCount?' / '+fmt(unresolvedGrCount,0)+' ?':'')+'</b><span>GR #</span></div></div>'+
 '<div class="detail"><b>Receiving article(s)</b><br>'+esc((r.receiving_articles||[]).join(' + ')||r.receiving_article||'—')+
 (events.length?'<br><br><b>PO → GR receipt trace</b>'+events.map(x=>{const receiptRef=x.gr_number?'GR '+x.gr_number:'GR UNRESOLVED';return '<div class="receipt-event"><div class="receipt-pair">PO '+esc(x.purchase_order||'—')+' → '+esc(receiptRef)+'</div><div class="receipt-meta">Article '+esc(x.article_number||'—')+' · '+fmt(x.quantity)+' '+esc(x.uom||'')+' · '+esc(receiptMovementLabel(x))+(x.vendor_code?' · Vendor '+esc(x.vendor_code):'')+(x.gr_number_source==='RAW_REFERENCE_Q_5014'?' · GR from Reference':x.gr_number_source==='RAW_ROW_5014_SCAN'?' · GR from MVT row':'')+'</div></div>'}).join(''):'')+
 '<br><b>Basis</b><br>Actual canonical receipt movements on the selected past date. PO and GR are paired from the same canonical receipt event. Base UOM is used when all receipt events reconcile; otherwise the common entry UOM is shown.</div>');
}
function openOrder(r){
 const d=r.details||{}, reasons=d.reasons||[], state=orderState(r), reason=orderReasonLabel(r.roster_reason);
 const orderMetric=state==='REVIEW'?'REVIEW':fmtNullable(orderQty(r))+' '+esc(r.suggested_delivery_uom||'');
 const orderMetricLabel=state==='REVIEW'?'ORDER STATUS':(r.estimate_only?'ESTIMATE ORDER':'SUGGESTED ORDER');
 sheet(r.family_name||'Ordering','Family '+esc(r.family_article||'—')+' · Delivery '+esc(appDate(r.selected_delivery_date||orderDate)),
 '<div class="dmetrics"><div class="dm"><b>'+fmtNullable(r.oh)+' '+esc(r.oh_uom||'')+'</b><span>CURRENT OH</span></div><div class="dm"><b>'+fmtNullable(d.velocity_7d)+'</b><span>7D VELOCITY</span></div><div class="dm"><b>'+orderMetric+'</b><span>'+orderMetricLabel+'</span></div></div>'+
 (r.estimate_only?'<div class="estimatebar">BEST AVAILABLE · missing POS/MVT dates do not block this order suggestion.</div>':'')+
 '<div class="detail"><b>Roster status</b><br>'+(state==='ORDER'?'Needs order':state==='ZERO_ORDER'?'Observed delivery family · no order suggested':'Review required · '+esc(reason))+
 '<br><br><b>Receiving article</b><br>'+esc(r.receiving_article||'—')+
 '<br><br><b>Last receipt</b><br>'+esc(appDate(r.last_receipt_date))+' · '+fmtNullable(r.last_receipt_qty_base)+' '+esc(r.last_receipt_base_uom||'')+
 '<br><br><b>Demand</b><br>7D '+fmtNullable(d.qty_7d)+' · 28D '+fmtNullable(d.qty_28d)+' · DOS '+fmtNullable(d.dos)+' · Forecast confidence '+esc(d.regular_forecast_confidence||'—')+
 '<br><br><b>Coverage need</b><br>'+fmtNullable(d.forecast_coverage_usage)+' '+esc(r.oh_uom||'')+' from Delivery through the eligible coverage end'+
 '<br><br><b>Projected at delivery</b><br>'+fmtNullable(d.projected_oh_at_delivery)+' '+esc(r.oh_uom||'')+' · usable '+fmtNullable(d.usable_oh_at_delivery)+' '+esc(r.oh_uom||'')+
 (d.pre_delivery_stockout_risk?'<br><br><b>⚠ Pre-delivery stockout risk</b><br>'+fmtNullable(d.pre_delivery_stockout_qty)+' '+esc(r.oh_uom||'')+' projected short before the selected delivery. This shortage is NOT added to the later order.':'')+
 (d.freshness_coverage_capped?'<br><br><b>⚠ Freshness guard</b><br>Fresh/Live coverage is capped at 7 days. Later demand requires an earlier or split delivery.':'')+
 '<br><br><b>Delivery evidence</b><br>'+fmt(r.delivery_day_observed_count,0)+' / '+fmt(r.delivery_day_receipt_count,0)+' receipt dates · '+fmt(r.delivery_day_confidence_pct,0)+'% confidence'+
 (reasons.length?'<br><br><b>Why</b><br>'+reasons.map(x=>'• '+esc(x.detail||x.title||'')).join('<br>'):'')+'</div>');
}


const PRICE_IGNORE_KEY='yipman-price-ignore-v361';
const PRICE_IGNORE_MS=30*60*1000;
let priceIgnoreMemory={};
function readPriceIgnores(){
  try{
    const raw=JSON.parse(localStorage.getItem(PRICE_IGNORE_KEY)||'{}');
    if(raw&&typeof raw==='object'){priceIgnoreMemory=raw;return raw}
  }catch{}
  return priceIgnoreMemory||{};
}
function writePriceIgnores(v){
  priceIgnoreMemory=v||{};
  try{localStorage.setItem(PRICE_IGNORE_KEY,JSON.stringify(priceIgnoreMemory))}catch{}
}
function priceIgnoreId(r){return String(r?.upc||'').trim()}
function priceIsIgnored(r){
  const id=priceIgnoreId(r);if(!id)return false;
  const map=readPriceIgnores(),ts=Number(map[id]||0);
  return ts>0&&(Date.now()-ts)<PRICE_IGNORE_MS;
}
function ignorePriceSuggestion(r){
  const id=priceIgnoreId(r);if(!id)return;
  const map=readPriceIgnores();map[id]=Date.now();writePriceIgnores(map);
  if($('#overlay').classList.contains('on'))closeSheet(true);
  toast('Ignored for 30 minutes');
  loadPrices({quiet:true});
}
function priceReasonMeta(r,stale=false){
  const code=String(r?.suggestion_reason_code||'');
  if(r?.priority_240_249_mismatch||code==='PAIR_FIX')return {label:'240≠249',cls:'red',testing:'NOT A TEST'};
  if(code==='COMPANY_RANGE')return {label:'RANGE',cls:'red',testing:'NOT A TEST'};
  if(code==='VELOCITY_TEST')return {label:'VELOCITY',cls:'amber',testing:'FRESHNESS TEST'};
  if(code==='SWEET_SPOT_GAP')return {label:'SWEET SPOT',cls:'amber',testing:'NEXT STEP'};
  if(code==='GP_DOLLAR_TEST')return {label:'GP$ TEST',cls:'green',testing:'NEXT STEP'};
  return {label:stale?'ESTIMATE':'REVIEW',cls:stale?'amber':'green',testing:'NEXT STEP'};
}
function priceProgress(r){
  const v7=num(r?.velocity_7d),v28=num(r?.velocity_28d);
  if(v7===null||v28===null||v28<=0)return {pct:null,label:'Velocity '+fmt(v7)+' /day',delta:'28D baseline —'};
  const ratio=v7/v28,delta=(ratio-1)*100,pct=Math.max(0,Math.min(100,ratio*100));
  return {pct,label:'Velocity '+fmt(v7)+' /day',delta:'vs 28D '+fmt(v28)+' /day · '+(delta>=0?'+':'')+delta.toFixed(0)+'%'};
}
function priceSignals(r){
  const out=[],code=String(r?.suggestion_reason_code||'');
  if(r?.priority_240_249_mismatch||code==='PAIR_FIX')out.push('240≠249');
  if(code==='COMPANY_RANGE'||r?.company_range_violation)out.push('OUTSIDE COMPANY RANGE');
  if(code==='VELOCITY_TEST')out.push('SLOW / FRESHNESS');
  if(r?.slow_velocity_trend)out.push('7D < 80% OF 28D');
  const d=num(r?.doh);if(d!==null&&['FRESH','LIVE'].includes(String(r?.category||'').toUpperCase())&&d>=5)out.push('DOH 5+');
  if(code==='SWEET_SPOT_GAP')out.push('>$0.25 FROM TESTED');
  if(code==='GP_DOLLAR_TEST')out.push('GP$/DAY OPPORTUNITY');
  return out.slice(0,4);
}
function friendlySignal(v){return String(v||'').replaceAll('_',' ').replace(/\s+/g,' ').trim()}

function schedulePriceRetry(requestId,delayMs=3000){
 clearTimeout(priceRetryTimer);
 priceRetryTimer=setTimeout(()=>{
  if(current==='price'&&requestId===priceRequestSeq)loadPrices({quiet:true});
 },delayMs);
}
async function loadPrices(opts={}){
 const quiet=!!opts.quiet;
 const requestId=++priceRequestSeq;
 clearTimeout(priceRetryTimer);
 if(!quiet)$('#priceRows').innerHTML='<div class="loading">Loading actionable pricing…</div>';
 $('#priceStatus').textContent='Current · strongest proved Tested · controlled Testing';
 try{
  const d=await api('/v1/yipman/pricing-review?category=ALL&limit=1000',{timeoutMs:12000});
  if(requestId!==priceRequestSeq)return;
  const analysisStatus=String(d.analysis_status||'').toUpperCase();
  const cacheStatus=String(d.cache_status||'').toUpperCase();
  const warming=analysisStatus==='REFRESHING'||cacheStatus==='WARMING';
  if(warming){
    $('#priceStatus').textContent='Building current Price Suggestions…';
    $('#priceRows').innerHTML='<div class="loading">Pricing analysis is running in the background. Yipman will retry automatically.</div>';
    schedulePriceRetry(requestId,3000);
    return;
  }
  const h=d.data_health||{};
  if(String(h.status||'').includes('BLOCKED')){
    $('#priceStatus').textContent='Price estimate unavailable';
    $('#priceRows').innerHTML='<div class="empty">No usable POS or MVT history is available for a best-available price estimate.<br>POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'</div>';
    return;
  }
  const stale=String(h.status||'').toUpperCase()==='STALE_ESTIMATE_AVAILABLE'||String(d.cache_status||'').toUpperCase()==='STALE_REFRESHING';
  const meaningful=(d.rows||[]).filter(r=>r.priority_240_249_mismatch||r.actionable||String(r.suggestion_reason_code||''));
  const observed=r=>(Array.isArray(r.observed_delivery_weekdays)?r.observed_delivery_weekdays:[]).map(x=>String(x||'').toUpperCase());
  const patternFiltered=meaningful.filter(r=>{
    if(priceFilter==='LIVE')return String(r.category||'').toUpperCase()==='LIVE';
    const days=observed(r);
    if(priceFilter==='TUE')return days.includes('TUESDAY');
    if(priceFilter==='FRI_SAT')return days.includes('FRIDAY')||days.includes('SATURDAY');
    return true;
  });
  const ignoredCount=patternFiltered.filter(priceIsIgnored).length;
  const rows=patternFiltered.filter(r=>!priceIsIgnored(r)).slice(0,24);
  const filterLabel=priceFilter==='LIVE'?'Live':priceFilter==='TUE'?'Observed Tuesday delivery':'Observed Friday / Saturday delivery';
  $('#priceStatus').innerHTML=(stale?'<div class="estimatebar">BEST AVAILABLE · POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'. Missing dates are ignored, not zero-filled.</div>':'')+esc(filterLabel)+' · '+rows.length+' actionable · '+ignoredCount+' ignored <30m · '+Number(d.suppressed_accepted_count||0)+' accepted hidden';

  $('#priceRows').innerHTML=rows.map((r,i)=>{
    const meta=priceReasonMeta(r,stale),prog=priceProgress(r),signals=priceSignals(r);
    const tested=num(r.tested_price),testing=num(r.testing_price),cur=num(r.current_price);
    const gap=(tested!==null&&cur!==null)?Math.abs(tested-cur):null;
    const gpNow=num(r.current_gp_per_day_7d),gpTarget=num(r.candidate_expected_gp_per_day);
    const companyLow=num(r.company_range_low),companyHigh=num(r.company_range_high);
    const companyText=(companyLow!==null&&companyHigh!==null)?money(companyLow)+'–'+money(companyHigh):'—';
    const detailSignals=(Array.isArray(r.reasons)?r.reasons:[]).map(x=>'• '+esc(friendlySignal(x))).join('<br>');
    return '<article class="pcard" data-price="'+i+'">'+
      '<div class="ptop"><div><b>'+esc(r.name||r.upc)+'</b><small>'+esc(r.upc)+' · '+esc(r.primary_reason_text||r.suggestion_reason||'Pricing review')+'</small></div><span class="pbadge '+meta.cls+'">'+esc(meta.label)+'</span></div>'+
      '<div class="pricepath">'+
        '<div class="pp current"><small>CURRENT</small><b>'+money(r.current_price)+'</b><span>'+esc(r.current_price_type||r.current_price_source||'latest effective')+'</span></div>'+
        '<div class="pp tested"><small>TESTED</small><b>'+money(r.tested_price)+'</b><span>STRONGEST PROVED</span></div>'+
        '<div class="pp testing"><small>TESTING</small><b>'+money(r.testing_price)+'</b><span>'+esc(meta.testing)+'</span></div>'+
      '</div>'+
      '<div class="pmetrics">'+
        '<div class="pm"><small>OH</small><b>'+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+'</b></div>'+
        '<div class="pm"><small>7D QTY</small><b>'+fmt(r.qty_7d)+' '+esc(r.qty_uom||'')+'</b></div>'+
        '<div class="pm"><small>7D VEL</small><b>'+fmt(r.velocity_7d)+'/day</b></div>'+
        '<div class="pm"><small>'+(gap!==null?'TESTED GAP':'DOH')+'</small><b>'+(gap!==null?money(gap):fmt(r.doh))+'</b></div>'+
      '</div>'+
      '<div class="pprogress"><div class="pprogress-line"><span><b>'+esc(prog.label)+'</b> · '+esc(prog.delta)+'</span><strong>'+(gpNow!==null?('GP$/d '+money(gpNow)):'GP$/d —')+'</strong></div>'+
        (prog.pct===null?'':'<div class="pbar"><i style="width:'+prog.pct.toFixed(0)+'%"></i></div>')+
        (gpTarget!==null?'<div class="pprogress-line" style="margin-top:4px"><span>Supported target evidence</span><strong>'+money(gpTarget)+'/day</strong></div>':'')+
      '</div>'+
      (signals.length?'<div class="pchips">'+signals.map(x=>'<span class="pchip">'+esc(x)+'</span>').join('')+'</div>':'')+
      '<details class="preason"><summary>DETAIL REASON + EVIDENCE ▾</summary><div>'+
        '<b>Why:</b> '+esc(r.primary_reason_text||r.suggestion_reason||'Pricing review')+
        '<br><b>Current evidence:</b> '+esc(r.current_price_source||'—')+(r.current_price_observed_date?' · '+esc(r.current_price_observed_date):'')+
        '<br><b>Company range:</b> '+esc(companyText)+(r.company_range_violation?' · CURRENT OUTSIDE':'')+
        '<br><b>Test target:</b> '+money(r.testing_target_price||r.target_sweet_spot_price)+
        (detailSignals?'<br><b>Signals:</b><br>'+detailSignals:'')+
      '</div></details>'+
      '<div class="pcard-actions"><button class="pdetail" data-price-detail="'+i+'">DETAIL</button><button class="pignore" data-price-ignore="'+i+'">IGNORE 30 MIN</button></div>'+
    '</article>';
  }).join('')||'<div class="empty">No actionable price suggestion matches this delivery-pattern filter.</div>';

  $$('[data-price]').forEach(x=>x.onclick=e=>{
    if(e.target.closest('button,details,summary'))return;
    openPrice(rows[Number(x.dataset.price)]);
  });
  $$('[data-price-detail]').forEach(b=>b.onclick=e=>{e.stopPropagation();openPrice(rows[Number(b.dataset.priceDetail)])});
  $$('[data-price-ignore]').forEach(b=>b.onclick=e=>{e.stopPropagation();ignorePriceSuggestion(rows[Number(b.dataset.priceIgnore)])});
 }catch(e){
  if(requestId!==priceRequestSeq)return;
  $('#priceStatus').textContent='Price suggestions temporarily unavailable';
  $('#priceRows').innerHTML='<div class="empty">'+esc(e.message)+'<br>Yipman will retry automatically.</div>';
  schedulePriceRetry(requestId,6000);
 }
}
function openPrice(r){
 const delivery=(r.observed_delivery_days||[]).map(x=>esc(x.weekday||'')+' '+fmt(x.receipt_date_count,0)+' receipt date'+(Number(x.receipt_date_count||0)===1?'':'s')).join('<br>');
 const meta=priceReasonMeta(r,false),signals=(Array.isArray(r.reasons)?r.reasons:[]).map(x=>'• '+esc(friendlySignal(x))).join('<br>');
 const companyLow=num(r.company_range_low),companyHigh=num(r.company_range_high);
 const company=(companyLow!==null&&companyHigh!==null)?money(companyLow)+' – '+money(companyHigh):'—';
 sheet(r.name||r.upc,r.upc||'Price suggestion',
 '<div class="dmetrics"><div class="dm"><b>'+money(r.current_price)+'</b><span>CURRENT</span></div><div class="dm"><b>'+money(r.tested_price)+'</b><span>TESTED · BEST PROVED</span></div><div class="dm"><b>'+money(r.testing_price)+'</b><span>TESTING · '+esc(meta.testing)+'</span></div></div>'+
 (r.estimate_only?'<div class="estimatebar">BEST AVAILABLE · missing POS/MVT dates do not block this price suggestion.</div>':'')+
 '<div class="detail"><b>Suggested action</b><br>'+esc(r.primary_reason_text||r.suggestion_reason||'Pricing review')+
 '<br><br><b>Price path</b><br>Current '+money(r.current_price)+' → Testing '+money(r.testing_price)+' · Tested '+money(r.tested_price)+
 '<br>Action price '+money(r.candidate_price)+(r.testing_target_price?(' · eventual test target '+money(r.testing_target_price)):'')+
 '<br><br><b>Progress now</b><br>7D '+fmt(r.qty_7d)+' '+esc(r.qty_uom||'')+' · '+fmt(r.velocity_7d)+' /day · 28D '+fmt(r.velocity_28d)+' /day · DOH '+fmt(r.doh)+
 '<br>GP$/day now '+money(r.current_gp_per_day_7d)+' · supported target evidence '+money(r.candidate_expected_gp_per_day)+
 '<br><br><b>Company A/B/C range</b><br>'+esc(company)+(r.company_range_violation?' · CURRENT OUTSIDE RANGE':'')+
 '<br><br><b>Current price evidence</b><br>'+esc(r.current_price_source||'—')+(r.current_price_observed_date?' · '+esc(r.current_price_observed_date):'')+
 '<br><br><b>Testing rule</b><br>Start from CURRENT. Move one controlled step toward the applicable target; prefer an observed nearby price and cap ordinary tests at 5%. Re-check completed-day velocity and GP$/day before the next step.'+
 '<br><br><b>Observed delivery pattern</b><br>'+(delivery||'No positive receipt weekday observed in the 180-day window.')+
 (signals?'<br><br><b>Supporting signals</b><br>'+signals:'')+'</div>'+
 '<div class="actions"><button class="secondary" id="priceIgnore30">IGNORE 30 MIN</button>'+(String(r.review_status||'').toUpperCase()==='ACTIONABLE'&&r.current_price!=null&&r.candidate_price!=null?'<button class="primary" id="priceAccept">ACCEPTED</button>':'')+'</div>');
 const ig=$('#priceIgnore30');if(ig)ig.onclick=()=>ignorePriceSuggestion(r);
 const a=$('#priceAccept');if(a)a.onclick=()=>acceptPrice(r,a);
}
async function acceptPrice(r,b){
 b.disabled=true;b.textContent='SAVING…';
 try{
  await api('/v1/yipman/pricing-review/'+encodeURIComponent(r.upc)+'/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_price:r.current_price,current_price_source:r.current_price_source,current_price_asof_date:r.current_price_observed_date,candidate_price:r.candidate_price}),timeoutMs:30000});
  closeSheet(true);toast('Accepted · hidden until evidence changes');loadPrices();
 }catch(e){b.disabled=false;b.textContent='ACCEPTED';toast(e.message)}
}
$$('[data-price-filter]').forEach(b=>b.onclick=()=>{
 priceFilter=b.dataset.priceFilter;
 $$('[data-price-filter]').forEach(x=>x.classList.toggle('on',x===b));
 loadPrices();
});

async function loadData(){
 try{
  const [health,active,recent]=await Promise.all([api('/v1/backoffice/data-health?days=14',{timeoutMs:12000}),api('/v1/web-upload/active',{timeoutMs:12000}),api('/v1/web-upload/recent?limit=4',{timeoutMs:12000})]);
  $('#calendar').innerHTML=(health.rows||[]).slice(0,14).reverse().map(r=>'<div class="c">'+esc(String(r.date||'').slice(8,10))+'<div class="dot '+(r.overall_status==='MISSING'?'bad':r.overall_status==='COMPLETE'?'':'warn')+'"></div></div>').join('');
  const b=active.active_batch||active.latest_batch||{};const st=String(b.processing_status||'NONE').toUpperCase();
  $('#pipe').innerHTML='<div class="stage '+(st!=='NONE'?'ok':'')+'"><b>UPLOAD</b><span>'+(st==='NONE'?'—':'DONE')+'</span></div><div class="stage '+(/INGEST|PHASE|QUICK|READY/.test(st)?'ok':'')+'"><b>INGEST</b><span>'+(/INGEST|PHASE|QUICK|READY/.test(st)?'DONE':'—')+'</span></div><div class="stage '+(/HOLD/.test(st)?'bad':/PHASE3|QUICK|READY/.test(st)?'ok':'warn')+'"><b>QA</b><span>'+esc(st.includes('HOLD')?'HOLD':/PHASE3|QUICK|READY/.test(st)?'DONE':'WAIT')+'</span></div><div class="stage '+(/QUICK_CHECK_READY/.test(st)?'ok':'warn')+'"><b>PUBLISH</b><span>'+(/QUICK_CHECK_READY/.test(st)?'READY':'WAIT')+'</span></div>';
  $('#currentBatch').innerHTML=b.batch_id?'<div class="batchrow" data-batch="'+esc(b.session_id||b.batch_key||'')+'"><div><b>Batch #'+esc(b.batch_id)+'</b><span>'+esc(b.batch_label||'')+'</span></div><div class="badge '+(st.includes('HOLD')?'red':'amber')+'">'+esc(st)+'</div></div>':'<div class="empty">No active batch.</div>';
  const rb=recent.batches||recent.rows||[];$('#recentBatches').innerHTML=rb.slice(0,4).map(x=>'<div class="batchrow"><div><b>Batch #'+esc(x.batch_id||'—')+'</b><span>'+esc(x.processing_status||'')+'</span></div><span>'+esc(String(x.completed_at||x.upload_started_at||'').slice(0,10))+'</span></div>').join('')||'<div class="empty">No recent batches.</div>';
  $$('[data-batch]').forEach(x=>x.onclick=()=>openBatch(x.dataset.batch,b));
 }catch(e){$('#currentBatch').innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
async function openBatch(session,basic){sheet('Batch #'+esc(basic.batch_id||'—'),basic.processing_status||'','<div class="loading">Loading processing detail…</div>');if(!session){$('#sheetBody').innerHTML='<div class="detail">Session ID unavailable in active summary.</div>';return}try{const d=await api('/v1/web-upload/batches/'+encodeURIComponent(session),{timeoutMs:12000}), b=d.batch||{}, p=d.phase3||{}, q=d.qa_summary||{};$('#sheetBody').innerHTML='<div class="dmetrics"><div class="dm"><b>'+esc(b.processing_status||'—')+'</b><span>BATCH STATUS</span></div><div class="dm"><b>'+fmt(p.quick_check_ready_rows,0)+'</b><span>READY ROWS</span></div><div class="dm"><b>'+fmt(p.quick_check_hold_rows,0)+'</b><span>QA HOLD</span></div></div><div class="detail"><b>Phase 3</b><br>'+esc(p.result_status||'—')+'<br><br><b>Open blockers</b><br>'+fmt(p.blocking_issue_count,0)+(q.reason_counts?'<br>'+Object.entries(q.reason_counts).slice(0,8).map(([k,v])=>'• '+esc(k)+': '+fmt(v,0)).join('<br>'):'')+'</div>'}catch(e){$('#sheetBody').innerHTML='<div class="detail">'+esc(e.message)+'</div>'}}

function activePage(){return $('#'+current)}
app.addEventListener('touchstart',e=>{const p=activePage();if($('#overlay').classList.contains('on')||!p||p.scrollTop>0||e.touches.length!==1)return;pullStart=e.touches[0].clientY;pull=0},{passive:true});
app.addEventListener('touchmove',e=>{if(pullStart==null)return;const dy=e.touches[0].clientY-pullStart;if(dy<=0)return;pull=Math.min(105,dy*.52);$('#ptr').style.height=pull+'px';$('#ptrText').textContent=pull>=68?'Release to refresh':'Pull to refresh'},{passive:true});
app.addEventListener('touchend',()=>{if(pullStart==null)return;const refresh=pull>=68;pullStart=null;if(!refresh){$('#ptr').style.height='0';return}$('#ptr').style.height='48px';$('#ptrText').textContent='Refreshing Yipman…';refreshCurrent().finally(()=>setTimeout(()=>{$('#ptr').style.height='0'},250))});
async function refreshCurrent(){if(current==='quick'){const q=$('#globalInput').value.trim();if(q)await loadQuick(q);else await loadBestSellers(true)}else if(current==='order')await initOrdering(true);else if(current==='price')await loadPrices();else if(current==='data')await loadData();toast('Yipman refreshed')}

const initialHash=String(location.hash||'').replace(/^#/,'').split('/')[0];
const initialView=['quick','order','price','data'].includes(initialHash)?initialHash:'quick';
history.replaceState({yipman:true,root:true,view:'quick'},'', '#quick');
history.pushState({yipman:true,view:initialView,guard:true},'', '#'+initialView);
historyReady=true;
renderView(initialView);
if('serviceWorker'in navigator)navigator.serviceWorker.register('/app/yipman/sw.js',{scope:'/app/yipman/'}).catch(()=>{});
})();
</script>
</body>
</html>'''
