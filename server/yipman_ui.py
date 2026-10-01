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
const CACHE='yipman-v335';
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
@media (display-mode:standalone),(display-mode:fullscreen){#app{padding-top:max(env(safe-area-inset-top,0px),30px)}}
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
.list{background:#fff;border-radius:16px;box-shadow:var(--shadow);overflow:hidden}.lh,.orow{display:grid;grid-template-columns:1fr 58px 64px;padding:0 11px}.lh{background:#eef2f5;padding-top:8px;padding-bottom:8px;font-size:7px;font-weight:900;color:#5d6974}.orow{border-top:1px solid var(--line)}.orow>div{padding:10px 0}.orow .name{font-size:11px;font-weight:900}.orow .sub{font-size:7px;color:var(--muted);margin-top:2px}.cell{text-align:right;font-size:11px;font-weight:900}.cell span{display:block;font-size:7px;color:var(--muted)}.orow.urgent{box-shadow:inset 4px 0 0 var(--red)}.orow.review{box-shadow:inset 4px 0 0 #d19a00}.orow.zero{box-shadow:inset 4px 0 0 #9aa6af}.orderstate{display:inline-flex;margin-left:4px;padding:2px 5px;border-radius:999px;background:#edf2f6;color:#5b6873;font-size:6px;font-weight:950;vertical-align:1px}.orderstate.order{background:#e8f6ee;color:#167648}.orderstate.review{background:#fff4d6;color:#805d00}.rtrace{display:grid;gap:4px;margin-top:6px}.rtrace-line{display:flex;align-items:center;gap:4px;min-width:0;font-size:8px;font-weight:950;line-height:1.15}.rpo,.rgr{display:inline-flex;align-items:center;max-width:46%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-radius:7px;padding:4px 5px;border:1px solid}.rpo{background:var(--amberbg);border-color:#ecd99f;color:#775500}.rgr{background:var(--greenbg);border-color:#cbe6d6;color:var(--green)}.rtrace-arrow{color:#91a0ab;font-weight:950;flex:0 0 auto}.rtrace-more{font-size:7px;color:var(--muted);font-weight:850}.receipt-event{padding:8px 0;border-top:1px solid var(--line)}.receipt-event:first-child{border-top:0}.receipt-pair{font-weight:950;color:#263743}.receipt-meta{font-size:9px;color:var(--muted);margin-top:2px}
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

</style>
</head>
<body>
<div id="app">
  <div class="ptr" id="ptr"><div id="ptrText">Pull to refresh</div></div>
  <header class="header">
    <div class="head"><div><div class="brand">Yip<span>man</span></div><span class="ver">FULL MYSQL · __VERSION__</span></div><button class="dbbtn" data-go="data" aria-label="Data Center">▦</button></div>
    <form class="search" id="globalForm"><span>⌕</span><input id="globalInput" placeholder="Search item, UPC, article..." autocomplete="off"></form>
  </header>
  <main class="workspace">
    <section class="page on" id="home">
      <div class="topline"><h2>Today</h2><div class="hint" id="todayLabel">YIPMAN</div></div>
      <div class="hero"><small>SEAFOOD OPERATIONS</small><h3 id="attentionTitle">Loading current work…</h3><p id="attentionSub">Current FULL MYSQL serving data</p><div class="stats"><div class="stat"><b id="homeOrder">—</b><span>POS SALES</span></div><div class="stat"><b id="homePrice">—</b><span>MVT</span></div><div class="stat"><b id="homeHealth">—</b><span>PRICE LIST</span></div></div></div>
      <div class="launch"><button data-go="quick"><i>⌕</i><b>Quick Check</b><span>Search current Family / UPC data</span><em>MOST USED</em></button><button data-go="order"><i>▤</i><b>Ordering</b><span>Receipt cadence + sales history</span><em id="orderMini">LOADING</em></button><button data-go="price"><i>$</i><b>Price Review</b><span>Completed-day price optimization</span><em id="priceMini">LOADING</em></button><button data-go="data"><i>▦</i><b>Data Center</b><span>Freshness / uploads / batches</span><em id="dataMini">LOADING</em></button></div>
      <div class="priority"><div class="ph"><span>NEEDS ATTENTION</span><span>NOW</span></div><div id="priorityRows"><div class="loading">Loading priorities…</div></div></div>
    </section>

    <section class="page" id="quick"><div class="topline"><h2>Quick Check</h2><div class="hint">CURRENT MODULE DATA</div></div><div id="quickRows"><div class="empty">Use the search bar above. Results appear automatically.</div></div></section>

    <section class="page" id="order"><div class="topline"><h2>Ordering</h2><div class="hint">14-DAY DELIVERY VIEW</div></div><div class="daybar" id="dayBar"></div><div class="order-tools" id="orderTools"><div class="order-summary" id="orderSummary">Observed roster loading…</div><div class="order-controls"><label>FILTER<select id="orderFilter"><option value="ALL">ALL</option><option value="ORDER">NEED ORDER</option><option value="ZERO_ORDER">0 ORDER</option><option value="REVIEW">REVIEW</option></select></label><label>SORT<select id="orderSort"><option value="ACTION">ACTION FIRST</option><option value="QTY">ORDER QTY ↓</option><option value="DOS">DOS ↑</option><option value="OBSERVED">OBSERVED ↓</option><option value="NAME">NAME A–Z</option></select></label></div></div><div id="orderStatus" class="hint" style="margin:0 2px 7px"></div><div class="list"><div class="lh"><div id="orderCol1">FAMILY / RECEIVING</div><div id="orderCol2">OH</div><div id="orderCol3">ORDER</div></div><div id="orderRows"><div class="loading">Choose a delivery day.</div></div></div></section>

    <section class="page" id="price"><div class="topline"><h2>Price Review</h2><div class="hint">BY DELIVERY PATTERN</div></div><div class="filters"><button class="pill on" data-price-filter="LIVE">LIVE</button><button class="pill" data-price-filter="TUE">OBSERVED TUE</button><button class="pill" data-price-filter="FRI_SAT">OBSERVED FRI / SAT</button></div><div id="priceStatus" class="hint" style="margin:0 2px 7px"></div><div class="pricecards" id="priceRows"><div class="loading">Loading price review…</div></div></section>

    <section class="page" id="data"><div class="topline"><h2>Data Center</h2><div class="hint">BACK OFFICE UNCHANGED</div></div><div class="datagrid"><div class="dcard"><h3>Processing Pipeline</h3><div class="pipe" id="pipe"><div class="stage"><b>UPLOAD</b><span>—</span></div><div class="stage"><b>INGEST</b><span>—</span></div><div class="stage"><b>QA</b><span>—</span></div><div class="stage"><b>PUBLISH</b><span>—</span></div></div></div><div class="dcard"><h3>14-Day Completeness</h3><div class="cal" id="calendar"></div></div><div class="dcard"><h3>Current Batch</h3><div id="currentBatch"><div class="loading">Loading…</div></div></div><div class="dcard"><h3>Recent Batches</h3><div id="recentBatches"><div class="loading">Loading…</div></div></div></div></section>

    <nav class="nav"><button class="on" data-go="home"><i>⌂</i>HOME</button><button data-go="quick"><i>⌕</i>QUICK</button><button data-go="order"><i>▤</i>ORDER</button><button data-go="price"><i>$</i>PRICE</button></nav>
    <div class="overlay" id="overlay"><div class="sheet"><div class="shead"><div><h3 id="sheetTitle">Detail</h3><p id="sheetSub"></p></div><button class="close" id="closeSheet">×</button></div><div class="sbody" id="sheetBody"></div></div></div>
    <div class="exitoverlay" id="exitOverlay"><div class="exitbox"><h3>Exit Yipman?</h3><p>Your current view will close. No inventory, ordering, or price data will be changed.</p><div class="exitactions"><button class="exitcancel" id="exitCancel">Stay</button><button class="exitconfirm" id="exitConfirm">Exit</button></div></div></div>
    <div class="toast" id="toast"></div>
  </main>
</div>
<script>
(()=>{
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
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
let current='home', priceFilter='LIVE', orderDate=null, pullStart=null, pull=0;
let historyReady=false, detailHistory=false, exitAllowed=false;
let quickSearchTimer=null, quickRequestSeq=0, lastQuickQuery='', orderRequestSeq=0;
let orderSort='ACTION', orderFilter='ALL', lastOrderRows=[], lastOrderData=null, lastOrderStale=false, renderedOrderRows=[];
function toast(t){const n=$('#toast');n.textContent=t;n.classList.add('on');setTimeout(()=>n.classList.remove('on'),1600)}
async function api(url,opt={}){const c=new AbortController();let timedOut=false;const tm=setTimeout(()=>{timedOut=true;c.abort()},opt.timeoutMs||18000);try{const r=await fetch(url,{...opt,signal:c.signal,headers:{'Accept':'application/json',...(opt.headers||{})},cache:'no-store'});const text=await r.text();let data={};try{data=text?JSON.parse(text):{}}catch{}if(!r.ok)throw new Error(data?.detail?.reason||data?.detail||text||('HTTP '+r.status));return data}catch(e){if(timedOut||e?.name==='AbortError')throw new Error('Request timed out while the server was calculating. Retrying is safe.');throw e}finally{clearTimeout(tm)}}
function renderView(id){
  if(!$('#'+id))id='home';
  current=id;
  pages.forEach(p=>p.classList.toggle('on',p.id===id));
  nav.forEach(b=>b.classList.toggle('on',b.dataset.go===id));
  const p=$('#'+id);if(p)p.scrollTop=0;
  if(id==='order'&&!orderDate)loadOrder(0);
  if(id==='price')loadPrices();
  if(id==='data')loadData();
}
function go(id,{push=true}={}){
  if(id===current&&!$('#overlay').classList.contains('on'))return;
  renderView(id);
  if(push&&historyReady)history.pushState({yipman:true,view:id},'', '#'+id);
}
$$('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));
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
    history.pushState({yipman:true,view:'home',guard:true},'', '#home');
    hideExitConfirm();renderView('home');return;
  }
  if($('#overlay').classList.contains('on')){
    $('#overlay').classList.remove('on');detailHistory=false;
    if(e.state?.yipman&&e.state.view)renderView(e.state.view);
    return;
  }
  const st=e.state;
  if(st?.yipman&&st.root){
    renderView('home');
    history.pushState({yipman:true,view:'home',guard:true},'', '#home');
    showExitConfirm();
    return;
  }
  if(st?.yipman&&st.view){renderView(st.view);return}
});
window.addEventListener('beforeunload',e=>{if(exitAllowed)return;e.preventDefault();e.returnValue=''});
const today=new Date();$('#todayLabel').textContent=today.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'}).toUpperCase();

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
     family_receipt_history:Array.isArray(r.family_receipt_history)?r.family_receipt_history:[]
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
 const role=quickRole(r),uom=r.qty_uom||r.selling_uom||'';
 return '<div class="qupc" data-upc="'+esc(r.upc||'')+'"><div class="qupcmain"><div class="qupctop"><span class="qrole '+role.cls+'">'+esc(role.label)+'</span><span class="qupccode">'+esc(r.upc||'—')+'</span></div><div class="qupcname">'+esc(r.name||r.upc||'')+'</div></div><div class="qupcmetrics"><b>'+fmt(r.qty_7d)+' '+esc(uom)+'</b><span>7D Qty · '+fmt(r.velocity_7d)+' /day</span><span class="qready">'+esc(r.readiness||'')+'</span></div></div>';
}
function hiddenUpcs(rows,id){
 if(!rows.length)return '';
 return '<button class="qhidebtn" data-qhide="'+esc(id)+'" data-noun="UPC">Show '+rows.length+' inactive UPC'+(rows.length===1?'':'s')+' ▾</button><div class="qhidden" id="'+esc(id)+'"><div class="qhiddennote">Hidden by default · UPC 7D POS Qty = 0 / none.</div>'+rows.map(quickUpcHtml).join('')+'</div>';
}
function quickDeliveryCell(x,label){
 if(!x)return '<div class="qdelivery"><small>'+label+'</small><b>—</b><span>No receipt</span></div>';
 const uom=String(x.uom||'').trim();
 return '<div class="qdelivery"><small>'+label+'</small><b>'+esc(appDate(x.date))+'</b><span>'+fmt(x.quantity)+' '+esc(uom)+'</span></div>';
}
function quickReceivingRowHtml(a){
 const history=(Array.isArray(a.receipt_history)?a.receipt_history:[]).slice(0,2);
 return '<div class="qreceivingrow"><div class="qrecvidentity"><span class="qricon">R</span><div><div class="qrnum">'+esc(a.article_number||'—')+'</div><div class="qrname">'+esc(a.article_description||'Receiving Article')+'</div></div></div>'+
   quickDeliveryCell(history[0],'LATEST DELIVERY')+quickDeliveryCell(history[1],'PREV DELIVERY')+'</div>';
}
function quickSellingHtml(a,idx,seq,{inactive=false}={}){
 const uom=String(a.movement_uom||''),rows=Array.isArray(a.rows)?a.rows:[],active=rows.filter(r=>hasActivity(r.qty_7d)),inactiveRows=rows.filter(r=>!hasActivity(r.qty_7d));
 const hid='q-upc-'+idx+'-'+seq;
 return '<section class="qsap"><div class="qsaphead"><div><div class="qsaprole">SAP SELLING ARTICLE</div><div class="qsaptop"><span class="qsapnum">'+esc(a.article_number||'UNRESOLVED')+'</span></div></div><div class="qsapkpis"><div class="qsapkpi"><small>7D MVT</small><b>'+fmt(a.movement_7d)+' '+esc(uom)+'</b></div><div class="qsapkpi"><small>AVG/DAY</small><b>'+fmt(a.avg_qty_day)+' '+esc(uom)+'</b></div></div></div>'+
   active.map(quickUpcHtml).join('')+hiddenUpcs(inactiveRows,hid)+(inactive?'<div class="qhiddennote">Inactive SAP Selling Article · no 7D MVT and no active UPC.</div>':'')+'</section>';
}
function quickGroupedHtml(rows){
 return quickFamilyGroups(rows).slice(0,12).map((g,idx)=>{
   const uom=g.group_uom||'',recon=String(g.reconciliation||'').toUpperCase();
   const familyHead='<div class="qfhead"><div><div class="qlabel">FAMILY ARTICLE</div><div class="qfnum">'+esc(g.family_article||'—')+(g.family_receipt_verified?'<span class="qreceipt">O</span>':'')+'</div><div class="qfname">'+esc(g.family_name||'Unmapped Family')+'</div><div class="qmeta">'+esc(g.category||'')+(recon?' · '+(recon==='PASS'?'TOTAL SELLING MVT RECONCILED':'TOTAL SELLING MVT HOLD'):'')+'</div></div><div class="qfkpis"><div class="qkpi"><small>7D TOTAL SELLING MVT</small><b>'+fmt(g.group_qty_7d)+' '+esc(uom)+'</b></div><div class="qkpi"><small>AVG/DAY</small><b>'+fmt(g.group_avg_qty_day)+' '+esc(uom)+'</b></div></div></div>';
   const receivingHtml=g.receiving.map(quickReceivingRowHtml).join('');
   const visible=[],hidden=[];
   for(const a of (g.selling||[])){
     const hasMvt=hasActivity(a.movement_7d),hasUpc=(a.rows||[]).some(r=>hasActivity(r.qty_7d));
     (hasMvt||hasUpc?visible:hidden).push(a);
   }
   const visibleHtml=visible.map((a,i)=>quickSellingHtml(a,idx,i)).join('');
   const hiddenId='q-art-'+idx;
   const hiddenHtml=hidden.length?'<button class="qhidebtn" data-qhide="'+hiddenId+'" data-noun="SAP Selling Article">Show '+hidden.length+' inactive SAP Selling Article'+(hidden.length===1?'':'s')+' ▾</button><div class="qhidden" id="'+hiddenId+'">'+hidden.map((a,i)=>quickSellingHtml(a,idx,100+i,{inactive:true})).join('')+'</div>':'';
   return '<section class="qfamily tone'+(idx%5)+'">'+familyHead+receivingHtml+visibleHtml+hiddenHtml+'</section>';
 }).join('');
}
function bindQuickRows(){
 $$('[data-upc]').forEach(x=>x.onclick=()=>openUpc(x.dataset.upc));
 $$('[data-qhide]').forEach(b=>b.onclick=()=>{const n=$('#'+CSS.escape(b.dataset.qhide));if(!n)return;const on=n.classList.toggle('on');b.textContent=(on?'Hide ':'Show ')+(b.dataset.noun||'inactive')+(on?' ▴':' ▾')});
}
async function loadQuick(q){
 const query=String(q||'').trim(), box=$('#quickRows');
 if(!query){quickRequestSeq++;lastQuickQuery='';box.innerHTML='<div class="empty">Use the search bar above. Results appear automatically.</div>';return}
 const requestId=++quickRequestSeq;lastQuickQuery=query;box.innerHTML='<div class="loading">Searching current Quick Check…</div>';
 try{
  const d=await api('/v1/backoffice/inventory?category=ALL&limit=120&lightweight=true&q='+encodeURIComponent(query),{timeoutMs:18000});
  if(requestId!==quickRequestSeq)return;
  const rows=d.rows||[];
  if(!rows.length){box.innerHTML='<div class="empty">No matching items.</div>';return}
  box.innerHTML=quickGroupedHtml(rows);
  bindQuickRows();
 }catch(e){if(requestId===quickRequestSeq)box.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
$('#globalForm').onsubmit=e=>{e.preventDefault();const q=$('#globalInput').value.trim();if(!q)return;go('quick');clearTimeout(quickSearchTimer);loadQuick(q);$('#globalInput').blur()};
$('#globalInput').addEventListener('input',()=>{if(current!=='quick')return;clearTimeout(quickSearchTimer);const q=$('#globalInput').value.trim();if(!q){loadQuick('');return}quickSearchTimer=setTimeout(()=>loadQuick(q),260)});

async function openUpc(upc){
 sheet('Loading…',upc,'<div class="loading">Loading current item detail…</div>');
 try{
  const d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc),{timeoutMs:16000});
  const oh=d.effective_oh||{}, q7=d.qty_7d||{};
  sheet(d.upc_name||upc,(d.upc||upc)+' · Family '+(d.family_article_number||'—'),'<div class="dmetrics"><div class="dm"><b>'+fmt(oh.quantity)+' '+esc(oh.uom||'')+'</b><span>EFFECTIVE OH</span></div><div class="dm"><b>'+fmt(d.upc_velocity_7d)+'</b><span>'+esc(d.qty_uom||d.selling_uom||'UNIT')+' / DAY</span></div><div class="dm"><b>'+money(d.current_price)+'</b><span>CURRENT '+esc(d.current_price_type||'PRICE')+'</span></div></div><div class="detail"><b>7D sales</b><br>'+fmt(q7.sold_quantity)+' '+esc(d.qty_uom||'')+' across '+fmt(q7.supported_day_count,0)+' completed data day(s).<br><br><b>Current price source</b><br>'+esc(d.current_price_source||'—')+(d.current_price_asof_date?' · '+esc(d.current_price_asof_date):'')+'<br><br><b>Current cost</b><br>'+money(d.current_cost_per_selling_unit)+' / '+esc(d.selling_uom||'unit')+'<br><br><b>OH status</b><br>'+esc(oh.status||'—')+(oh.reason?'<br>'+esc(oh.reason):'')+'</div>');
 }catch(e){sheet('Unable to load',upc,'<div class="detail">'+esc(e.message)+'</div>')}
}

function buildDays(){
 const bar=$('#dayBar');bar.innerHTML='';
 // 14 dates: prior 7 days through the next 6 days. Today is initially centered.
 for(let offset=-7;offset<=6;offset++){
  const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+offset);
  const b=document.createElement('button');
  b.className='day'+(offset<0?' past':'')+(offset===0?' today':'');
  b.dataset.offset=offset;
  b.innerHTML='<b>'+d.toLocaleDateString(undefined,{weekday:'short'}).toUpperCase()+'</b><strong>'+d.getDate()+'</strong><span>'+d.toLocaleDateString(undefined,{month:'short'}).toUpperCase()+'</span>';
  b.onclick=()=>loadOrder(offset);
  bar.appendChild(b);
 }
 requestAnimationFrame(()=>bar.querySelector('.day.today')?.scrollIntoView({behavior:'auto',block:'nearest',inline:'center'}));
}
function receiptTracePairs(r){
 const events=Array.isArray(r?.receipt_events)?r.receipt_events:[];
 const pairs=[], seen=new Set();
 events.forEach(x=>{
  const po=String(x?.purchase_order||'').trim();
  const gr=String(x?.gr_number||'').trim();
  if(!po&&!gr)return;
  const key=po+'|'+gr;
  if(seen.has(key))return;
  seen.add(key);pairs.push({po,gr});
 });
 return pairs;
}
function receiptTraceHtml(r){
 const pairs=receiptTracePairs(r), shown=pairs.slice(0,3);
 if(!shown.length)return '';
 return '<div class="rtrace">'+shown.map(p=>
  '<div class="rtrace-line"><span class="rpo">PO '+esc(p.po||'—')+'</span><span class="rtrace-arrow">→</span><span class="rgr">GR '+esc(p.gr||'—')+'</span></div>'
 ).join('')+(pairs.length>shown.length?'<div class="rtrace-more">+'+(pairs.length-shown.length)+' more PO / GR pair'+(pairs.length-shown.length===1?'':'s')+'</div>':'')+'</div>';
}
function receiptMovementLabel(x){
 const s=String(x?.receipt_stage_basis||'').toUpperCase();
 if(s.startsWith('101_102'))return '101/102';
 if(s.startsWith('107_108'))return '107/108';
 if(s.startsWith('109_110'))return '109/110';
 return s||'—';
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
 visible=[...visible].sort((a,b)=>{
  if(orderSort==='QTY')return (orderQty(b)??-1)-(orderQty(a)??-1)||String(a.family_name||'').localeCompare(String(b.family_name||''));
  if(orderSort==='DOS')return (dos(a)??999999)-(dos(b)??999999)||String(a.family_name||'').localeCompare(String(b.family_name||''));
  if(orderSort==='OBSERVED')return obs(b)-obs(a)||String(a.family_name||'').localeCompare(String(b.family_name||''));
  if(orderSort==='NAME')return String(a.family_name||'').localeCompare(String(b.family_name||''));
  const rank=r=>orderState(r)==='ORDER'?0:orderState(r)==='REVIEW'?1:2;
  return rank(a)-rank(b)||((orderQty(b)??-1)-(orderQty(a)??-1))||String(a.family_name||'').localeCompare(String(b.family_name||''));
 });
 renderedOrderRows=visible;
 $('#orderStatus').innerHTML=stale
  ? '<div class="estimatebar">ESTIMATE · Existing POS + MVT through '+esc(h?.data_through||'—')+'. Missing day(s) are forecast forward to delivery.</div>'
  : esc(data?.selected_delivery_weekday||'Selected day')+' · complete observed-delivery roster';
 $('#orderRows').innerHTML=visible.map((r,i)=>{
  const state=orderState(r), q=orderQty(r), reason=orderReasonLabel(r.roster_reason);
  const cls=(r.attention?' urgent':'')+(state==='REVIEW'?' review':state==='ZERO_ORDER'?' zero':'');
  const stateLabel=state==='ORDER'?'ORDER':state==='REVIEW'?'REVIEW':'0 ORDER';
  const orderText=state==='REVIEW'?'REVIEW':fmtNullable(q);
  const orderSub=state==='REVIEW'?reason:esc(r.suggested_delivery_uom||'');
  return '<div class="orow'+cls+'" data-order="'+i+'"><div><div class="name">'+esc(r.family_name||r.family_article||'Family')+'<span class="orderstate '+(state==='ORDER'?'order':state==='REVIEW'?'review':'')+'">'+stateLabel+'</span></div><div class="sub">Receiving '+esc(r.receiving_article||'—')+' · '+esc(r.ordering_frequency||'')+' · '+fmt(r.delivery_day_observed_count,0)+' observed '+esc(r.delivery_day||'day')+(r.roster_reason?' · '+esc(reason):'')+(r.estimate_only?' · ESTIMATE':'')+'</div></div><div class="cell">'+fmtNullable(r.oh)+'<span>'+esc(r.oh_uom||'')+'</span></div><div class="cell">'+orderText+'<span>'+orderSub+'</span></div></div>';
 }).join('')||'<div class="empty">No rows match this filter. The complete observed roster has '+counts.total+' families.</div>';
 $('[data-order]').forEach(x=>x.onclick=()=>openOrder(renderedOrderRows[Number(x.dataset.order)]));
}
$('#orderFilter').onchange=e=>{orderFilter=e.target.value;renderOrderRoster(lastOrderRows,lastOrderData,lastOrderData?.data_health||{},lastOrderStale)};
$('#orderSort').onchange=e=>{orderSort=e.target.value;renderOrderRoster(lastOrderRows,lastOrderData,lastOrderData?.data_health||{},lastOrderStale)};
async function loadOrder(offset){
 const requestId=++orderRequestSeq;
 const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+offset);orderDate=iso(d);
 $$('.day').forEach(x=>x.classList.toggle('on',Number(x.dataset.offset)===offset));
 const isPast=offset<0;
 $('#orderTools').style.display=isPast?'none':'grid';
 $('#orderCol1').textContent='FAMILY / RECEIVING';
 $('#orderCol2').textContent=isPast?'RECEIPT':'OH';
 $('#orderCol3').textContent=isPast?'UOM':'ORDER';
 $('#orderStatus').textContent=(isPast?'Loading delivery history for ':'Loading ')+d.toLocaleDateString(undefined,{weekday:'long',month:'short',day:'numeric'})+'…';
 $('#orderRows').innerHTML='<div class="loading">'+(isPast?'Checking actual canonical receipts…':'Checking receiving cadence and coverage…')+'</div>';
 const url='/v1/yipman/ordering-review?category=ALL&delivery_date='+orderDate;
 try{
  let data=null;
  for(let i=0;i<10;i++){
   try{data=await api(url,{timeoutMs:26000})}catch(e){if(requestId!==orderRequestSeq)return;if(/timed out/i.test(String(e?.message||''))&&i<9){$('#orderStatus').textContent='Still calculating '+appDate(orderDate)+' · waiting for ordering cache';await new Promise(r=>setTimeout(r,1200));continue}throw e}
   if(requestId!==orderRequestSeq)return;
   const status=String(data.analysis_status||'').toUpperCase();
   if(!['REFRESHING','WARMING','STALE_DATA_REFRESHING'].includes(status)&&!['WARMING','STALE_DATA_REFRESHING'].includes(String(data.cache_status||'').toUpperCase()))break;
   $('#orderStatus').textContent='Calculating '+appDate(orderDate)+' · receipt cadence first';
   await new Promise(r=>setTimeout(r,1500));
  }
  const finalStatus=String(data?.analysis_status||'').toUpperCase(), h=data?.data_health||{};
  if(['REFRESHING','WARMING'].includes(finalStatus)||['WARMING','STALE_DATA_REFRESHING'].includes(String(data?.cache_status||'').toUpperCase())){
    $('#orderStatus').textContent='Still calculating best-available delivery view…';
    $('#orderRows').innerHTML='<div class="empty">Yipman is analyzing receipt history, OH and sales. Pull down to refresh in a few seconds.</div>';
    return;
  }
  if(finalStatus==='REFRESH_FAILED'){
    $('#orderStatus').textContent='Ordering calculation failed';
    $('#orderRows').innerHTML='<div class="empty">'+esc(data?.refresh_error||'Pull down to retry.')+'</div>';
    return;
  }
  if(finalStatus==='UNAVAILABLE'){
    const missing=(h.missing_required_sources||[]).join(' + ')||'POS / MVT';
    $('#orderStatus').textContent='Ordering unavailable';
    $('#orderRows').innerHTML='<div class="empty">No common usable POS + MVT date.<br>Required through '+esc(h.expected_through||'—')+' · POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'<br>'+esc(missing)+'</div>';
    return;
  }

  const rows=data?.rows||[];
  if(data?.history_mode||finalStatus==='HISTORY_READY'){
    $('#orderCol2').textContent='RECEIPT';
    $('#orderCol3').textContent='UOM';
    $('#orderStatus').textContent=(data.selected_delivery_weekday||'Past date')+' '+appDate(orderDate)+' · '+rows.length+' family receipt'+(rows.length===1?'':'s')+(data.movement_date_available?'':' · no canonical MVT snapshot for this date');
    $('#orderRows').innerHTML=rows.map((r,i)=>'<div class="orow" data-order-history="'+i+'"><div><div class="name">'+esc(r.family_name||r.family_article||'Family')+'</div><div class="sub">Receiving '+esc(r.receiving_article||'—')+' · '+fmt(r.receipt_event_count,0)+' receipt event'+(Number(r.receipt_event_count||0)===1?'':'s')+'</div>'+receiptTraceHtml(r)+'</div><div class="cell">'+fmt(r.receipt_qty)+'<span>ACTUAL</span></div><div class="cell">'+esc(r.receipt_uom||'—')+'<span>'+esc(r.receipt_qty_basis||'')+'</span></div></div>').join('')||'<div class="empty">No positive canonical 101/107/109 receipt was recorded on '+esc(appDate(orderDate))+'.</div>';
    $$('[data-order-history]').forEach(x=>x.onclick=()=>openOrderHistory(rows[Number(x.dataset.orderHistory)]));
    return;
  }

  $('#orderCol2').textContent='OH';
  $('#orderCol3').textContent='ORDER';
  const stale=String(h.status||'').toUpperCase()==='STALE_ESTIMATE_AVAILABLE'||finalStatus.startsWith('READY_STALE_ESTIMATE');
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
 sheet(r.family_name||'Delivery history','Family '+esc(r.family_article||'—')+' · '+esc(appDate(r.selected_delivery_date||orderDate)),
 '<div class="dmetrics"><div class="dm"><b>'+fmt(r.receipt_qty)+' '+esc(r.receipt_uom||'')+'</b><span>ACTUAL RECEIPT</span></div><div class="dm"><b>'+fmt(poCount,0)+'</b><span>PO #</span></div><div class="dm"><b>'+fmt(grCount,0)+'</b><span>GR #</span></div></div>'+
 '<div class="detail"><b>Receiving article(s)</b><br>'+esc((r.receiving_articles||[]).join(' + ')||r.receiving_article||'—')+
 (events.length?'<br><br><b>PO → GR receipt trace</b>'+events.map(x=>'<div class="receipt-event"><div class="receipt-pair">PO '+esc(x.purchase_order||'—')+' → GR '+esc(x.gr_number||'—')+'</div><div class="receipt-meta">Article '+esc(x.article_number||'—')+' · '+fmt(x.quantity)+' '+esc(x.uom||'')+' · MVT '+esc(receiptMovementLabel(x))+(x.vendor_code?' · Vendor '+esc(x.vendor_code):'')+(x.gr_number_source==='RAW_REFERENCE_Q_5014'?' · GR from Reference':x.gr_number_source==='RAW_ROW_5014_SCAN'?' · GR from MVT row':'')+'</div></div>').join(''):'')+
 '<br><b>Basis</b><br>Actual canonical receipt movements on the selected past date. PO and GR are paired from the same canonical receipt event. Base UOM is used when all receipt events reconcile; otherwise the common entry UOM is shown.</div>');
}
function openOrder(r){
 const d=r.details||{}, reasons=d.reasons||[], state=orderState(r), reason=orderReasonLabel(r.roster_reason);
 const orderMetric=state==='REVIEW'?'REVIEW':fmtNullable(orderQty(r))+' '+esc(r.suggested_delivery_uom||'');
 const orderMetricLabel=state==='REVIEW'?'ORDER STATUS':(r.estimate_only?'ESTIMATE ORDER':'SUGGESTED ORDER');
 sheet(r.family_name||'Ordering','Family '+esc(r.family_article||'—')+' · Delivery '+esc(appDate(r.selected_delivery_date||orderDate)),
 '<div class="dmetrics"><div class="dm"><b>'+fmtNullable(r.oh)+' '+esc(r.oh_uom||'')+'</b><span>CURRENT OH</span></div><div class="dm"><b>'+fmtNullable(d.velocity_7d)+'</b><span>7D VELOCITY</span></div><div class="dm"><b>'+orderMetric+'</b><span>'+orderMetricLabel+'</span></div></div>'+
 (r.estimate_only?'<div class="estimatebar">Best available estimate · data through '+esc(r.data_through||'—')+' · required through '+esc(r.expected_through||'—')+'.</div>':'')+
 '<div class="detail"><b>Roster status</b><br>'+(state==='ORDER'?'Needs order':state==='ZERO_ORDER'?'Observed delivery family · no order suggested':'Review required · '+esc(reason))+
 '<br><br><b>Receiving article</b><br>'+esc(r.receiving_article||'—')+
 '<br><br><b>Last receipt</b><br>'+esc(appDate(r.last_receipt_date))+' · '+fmtNullable(r.last_receipt_qty_base)+' '+esc(r.last_receipt_base_uom||'')+
 '<br><br><b>Demand</b><br>7D '+fmtNullable(d.qty_7d)+' · 28D '+fmtNullable(d.qty_28d)+' · DOS '+fmtNullable(d.dos)+
 '<br><br><b>Projected at delivery</b><br>'+fmtNullable(d.projected_oh_at_delivery)+' '+esc(r.oh_uom||'')+
 '<br><br><b>Delivery evidence</b><br>'+fmt(r.delivery_day_observed_count,0)+' / '+fmt(r.delivery_day_receipt_count,0)+' receipt dates · '+fmt(r.delivery_day_confidence_pct,0)+'% confidence'+
 (reasons.length?'<br><br><b>Why</b><br>'+reasons.map(x=>'• '+esc(x.detail||x.title||'')).join('<br>'):'')+'</div>');
}

async function loadPrices(){
 $('#priceRows').innerHTML='<div class="loading">Loading actionable pricing…</div>';
 $('#priceStatus').textContent='Current price uses latest valid evidence';
 try{
  const d=await api('/v1/yipman/pricing-review?category=ALL&limit=1000',{timeoutMs:30000}), h=d.data_health||{};
  if(String(h.status||'').includes('BLOCKED')){
    $('#priceStatus').textContent='Price estimate unavailable';
    $('#priceRows').innerHTML='<div class="empty">No common usable POS + MVT date.<br>Required '+esc(h.expected_through||'—')+' · POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'</div>';
    return;
  }
  const stale=String(h.status||'').toUpperCase()==='STALE_ESTIMATE_AVAILABLE';
  const meaningful=(d.rows||[]).filter(r=>r.priority_240_249_mismatch||num(r.price_gap_pct)===null||num(r.price_gap_pct)>=3);
  const observed=r=>(Array.isArray(r.observed_delivery_weekdays)?r.observed_delivery_weekdays:[]).map(x=>String(x||'').toUpperCase());
  const filtered=meaningful.filter(r=>{
    if(priceFilter==='LIVE')return String(r.category||'').toUpperCase()==='LIVE';
    const days=observed(r);
    if(priceFilter==='TUE')return days.includes('TUESDAY');
    if(priceFilter==='FRI_SAT')return days.includes('FRIDAY')||days.includes('SATURDAY');
    return true;
  });
  const rows=filtered.slice(0,24);
  const filterLabel=priceFilter==='LIVE'?'Live':priceFilter==='TUE'?'Observed Tuesday delivery':'Observed Friday / Saturday delivery';
  $('#priceStatus').innerHTML=(stale?'<div class="estimatebar">ESTIMATE · Sales + movement through '+esc(h.data_through||'—')+'. Current price/cost evidence is still resolved live where available.</div>':'')+esc(filterLabel)+' · '+rows.length+' actionable · '+Number(d.suppressed_accepted_count||0)+' accepted hidden';
  $('#priceRows').innerHTML=rows.map((r,i)=>{
    const days=(r.observed_delivery_days||[]).map(x=>String(x.weekday||'').slice(0,3).toUpperCase()+' '+fmt(x.receipt_date_count,0)).join(' · ');
    return '<div class="pcard" data-price="'+i+'"><div class="ptop"><div><b>'+esc(r.name||r.upc)+'</b><small>'+esc(r.upc)+' · '+esc(r.primary_reason_text||r.review_status||'Pricing review')+'</small></div><div class="badge '+(r.priority_240_249_mismatch?'red':stale?'amber':'green')+'">'+(r.priority_240_249_mismatch?'240≠249':stale?'ESTIMATE':'REVIEW')+'</div></div><div class="compare"><div class="pbox"><b>'+money(r.current_price)+'</b><span>CURRENT</span></div><div class="arrow">→</div><div class="pbox"><b>'+money(r.candidate_price)+'</b><span>BEST SUPPORTED</span></div></div><div class="why">OH '+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+' · DOH '+fmt(r.doh)+' · 7D '+fmt(r.qty_7d)+' '+esc(r.qty_uom||'')+' · '+fmt(r.velocity_7d)+' /day'+(r.gp_per_day_opportunity!=null?' · GP$/day lift '+money(r.gp_per_day_opportunity):'')+(days?' · RECEIPTS '+esc(days):'')+'</div></div>';
  }).join('')||'<div class="empty">No actionable price suggestion matches this delivery-pattern filter.</div>';
  $$('[data-price]').forEach(x=>x.onclick=()=>openPrice(rows[Number(x.dataset.price)]));
 }catch(e){
  $('#priceStatus').textContent='Price review failed';
  $('#priceRows').innerHTML='<div class="empty">'+esc(e.message)+'</div>';
 }
}
function openPrice(r){
 const delivery=(r.observed_delivery_days||[]).map(x=>esc(x.weekday||'')+' '+fmt(x.receipt_date_count,0)+' receipt date'+(Number(x.receipt_date_count||0)===1?'':'s')).join('<br>');
 sheet(r.name||r.upc,r.upc||'Price review',
 '<div class="dmetrics"><div class="dm"><b>'+money(r.current_price)+'</b><span>CURRENT</span></div><div class="dm"><b>'+money(r.candidate_price)+'</b><span>BEST SUPPORTED</span></div><div class="dm"><b>'+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+'</b><span>OH</span></div></div>'+
 (r.estimate_only?'<div class="estimatebar">ESTIMATE · completed POS/MVT evidence through '+esc(r.data_through||'—')+' · required through '+esc(r.expected_through||'—')+'.</div>':'')+
 '<div class="detail"><b>Optimization basis</b><br>Maximum supported GP$/day from recent completed selling-price history, constrained by Company A/B/C range when available; freshness and OH determine urgency.'+
 '<br><br><b>Observed delivery pattern</b><br>'+(delivery||'No positive receipt weekday observed in the 180-day window.')+
 '<br><br><b>Current evidence</b><br>'+esc(r.current_price_source||'—')+(r.current_price_observed_date?' · '+esc(r.current_price_observed_date):'')+
 '<br><br><b>Sales / stock</b><br>7D '+fmt(r.qty_7d)+' '+esc(r.qty_uom||'')+' · '+fmt(r.velocity_7d)+' /day · DOH '+fmt(r.doh)+
 (r.gp_per_day_opportunity!=null?'<br><br><b>Estimated GP$/day opportunity</b><br>'+money(r.gp_per_day_opportunity):'')+
 '<br><br><b>Reason</b><br>'+esc(r.primary_reason_text||r.review_blocker||'Pricing review')+(Array.isArray(r.reasons)&&r.reasons.length?'<br>'+r.reasons.map(x=>'• '+esc(x)).join('<br>'):'')+'</div>'+
 (String(r.review_status||'').toUpperCase()==='ACTIONABLE'&&r.current_price!=null&&r.candidate_price!=null?'<div class="actions"><button class="secondary" id="priceClose">NOT NOW</button><button class="primary" id="priceAccept">ACCEPTED</button></div>':''));
 const c=$('#priceClose');if(c)c.onclick=()=>closeSheet(true);
 const a=$('#priceAccept');if(a)a.onclick=()=>acceptPrice(r,a);
}
async function acceptPrice(r,b){
 b.disabled=true;b.textContent='SAVING…';
 try{
  await api('/v1/yipman/pricing-review/'+encodeURIComponent(r.upc)+'/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_price:r.current_price,current_price_source:r.current_price_source,current_price_asof_date:r.current_price_observed_date,candidate_price:r.candidate_price}),timeoutMs:30000});
  closeSheet(true);toast('Accepted · hidden until evidence changes');loadPrices();loadHome();
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
async function refreshCurrent(){if(current==='home')await loadHome();else if(current==='quick'){const q=$('#globalInput').value.trim();if(q)await loadQuick(q)}else if(current==='order')await loadOrder(Number($('.day.on')?.dataset.offset||0));else if(current==='price')await loadPrices();else if(current==='data')await loadData();toast('Yipman refreshed')}

const initialHash=String(location.hash||'').replace(/^#/,'').split('/')[0];
const initialView=['home','quick','order','price','data'].includes(initialHash)?initialHash:'home';
history.replaceState({yipman:true,root:true,view:'home'},'', '#home');
history.pushState({yipman:true,view:initialView,guard:true},'', '#'+initialView);
historyReady=true;
buildDays();
renderView(initialView);
loadHome();
if('serviceWorker'in navigator)navigator.serviceWorker.register('/app/yipman/sw.js',{scope:'/app/yipman/'}).catch(()=>{});
})();
</script>
</body>
</html>'''
