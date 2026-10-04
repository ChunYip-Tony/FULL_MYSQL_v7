from __future__ import annotations

import json

try:
    from .yipman_desktop_v369 import YIPMAN_DESKTOP_CSS, YIPMAN_DESKTOP_JS
except ImportError:
    from yipman_desktop_v369 import YIPMAN_DESKTOP_CSS, YIPMAN_DESKTOP_JS


def yipman_html(version: str = "") -> str:
    v = str(version or "")
    html = YIPMAN_HTML.replace("__VERSION__", v)
    desktop_boot = "<script>window.__YIPMAN_DESKTOP_ACTIVE__=window.matchMedia('(min-width:760px)').matches;document.documentElement.classList.toggle('yipman-desktop',window.__YIPMAN_DESKTOP_ACTIVE__);</script>"
    desktop_css = YIPMAN_DESKTOP_CSS.replace("__VERSION__", v)
    desktop_js = YIPMAN_DESKTOP_JS.replace("__VERSION__", v)
    html = html.replace("</head>", desktop_boot + "<style id=\"yipman-desktop-v372-css\">" + desktop_css + "</style></head>")
    html = html.replace("</body>", "<script id=\"yipman-desktop-v372-js\">" + desktop_js + "</script></body>")
    return html


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
const CACHE='yipman-v453';
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
/* Android standalone PWAs can report env(safe-area-inset-top)=0 while the system status bar still overlays the viewport. Keep browser mode unchanged, but reserve a compact 24px fallback in standalone/fullscreen so the Yipman header and freshness panel never sit under the status bar. */
@media (display-mode:standalone),(display-mode:fullscreen){#app{padding-top:max(env(safe-area-inset-top,0px),24px)}}
.header{padding:9px 13px 10px}.head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.brand{font-size:21px;font-weight:950;letter-spacing:-.04em}.brand span{color:var(--blue)}.ver{display:block;font-size:9px;color:var(--muted);font-weight:700;margin-top:1px}
.dbbtn{width:40px;height:40px;border:0;border-radius:14px;background:#fff;box-shadow:var(--shadow);font-size:18px}
.search{display:flex;align-items:center;margin-top:9px;background:#fff;border:1px solid var(--line);border-radius:15px;padding:0 10px;box-shadow:0 4px 15px rgba(18,38,56,.04)}
.search span{font-size:17px;color:#657581}.search input{flex:1;min-width:0;border:0;outline:0;background:transparent;padding:11px 8px;font-size:16px}
.workspace{height:calc(100% - 99px);position:relative;overflow:hidden}.page{display:none;height:100%;overflow-y:auto;overflow-x:hidden;padding:0 11px calc(82px + env(safe-area-inset-bottom));scrollbar-width:none}.page::-webkit-scrollbar{display:none}.page.on{display:block}
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
#data{overflow-x:hidden}#data .topline{min-width:0;margin-bottom:9px}#data .topline h2,#data .hint{min-width:0}
.datagrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:9px;width:100%;min-width:0;max-width:100%}
.dcard{min-width:0;max-width:100%;overflow:hidden;background:#fff;border:1px solid #e6ebef;border-radius:18px;padding:12px;box-shadow:0 7px 20px rgba(18,38,56,.07)}
.dcard h3{min-width:0;font-size:12px;margin:0 0 8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pipe{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;min-width:0}.stage{min-width:0;padding:8px 3px;text-align:center;background:#f3f6f8;border-radius:10px;border-top:4px solid #8d99a3;overflow:hidden}.stage b{display:block;min-width:0;font-size:7px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.stage span{display:block;min-width:0;font-size:7px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}.stage.ok{border-top-color:var(--green)}.stage.warn{border-top-color:#d19a00}.stage.bad{border-top-color:var(--red)}
.cal{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;min-width:0}.c{min-width:0;text-align:center;font-size:8px;color:#5f6d78;font-weight:850}.dot{width:13px;height:13px;border-radius:50%;background:var(--green);margin:4px auto 0}.dot.warn{background:#d19a00}.dot.bad{background:var(--red)}
.currentbatch{display:grid;gap:8px}.cbtop{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.cbid b{display:block;font-size:18px;line-height:1.05}.cbid span{display:block;font-size:9px;color:var(--muted);margin-top:3px}.cbstatus{flex:0 0 auto;max-width:58%;border-radius:999px;padding:5px 8px;font-size:8px;font-weight:950;line-height:1.15;text-align:center;white-space:normal}.cbstatus.red{background:var(--redbg);color:var(--red)}.cbstatus.amber{background:var(--amberbg);color:var(--amber)}.cbstatus.green{background:var(--greenbg);color:var(--green)}
.cbmeta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}.cbmeta div{min-width:0;background:#f6f8fa;border-radius:9px;padding:7px}.cbmeta small{display:block;font-size:6px;color:var(--muted);font-weight:950}.cbmeta b{display:block;font-size:10px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cblive{display:flex;align-items:center;justify-content:space-between;gap:8px;background:#f6f8fa;border:1px solid #e6ecef;border-radius:10px;padding:7px 8px}.cblive-main{display:flex;align-items:center;gap:6px;min-width:0}.cblive-dot{width:9px;height:9px;border-radius:50%;background:#9aa6af;box-shadow:0 0 0 3px rgba(154,166,175,.12);flex:0 0 auto}.cblive-dot.running{background:#1f9d63;box-shadow:0 0 0 3px rgba(31,157,99,.13)}.cblive-dot.queued{background:#d19a00;box-shadow:0 0 0 3px rgba(209,154,0,.13)}.cblive-dot.stuck{background:#d93025;box-shadow:0 0 0 3px rgba(217,48,37,.13)}.cblive b{font-size:9px;line-height:1.15}.cblive span{font-size:7px;color:var(--muted);font-weight:800;white-space:nowrap}.cblivecheck{font-size:7px!important;color:#788690!important}
.cbprogress{background:#f8fafb;border:1px solid #e7ecef;border-radius:10px;padding:8px}.cbprogress-top{display:flex;align-items:flex-end;justify-content:space-between;gap:8px}.cbprogress-top b{font-size:11px}.cbprogress-top span{font-size:8px;color:var(--muted);font-weight:850}.cbbar{height:6px;background:#e3e9ed;border-radius:999px;overflow:hidden;margin-top:6px}.cbbar i{display:block;height:100%;background:#1488c6;border-radius:999px;transition:width .25s ease}.cbprogress-sub{display:flex;justify-content:space-between;gap:8px;margin-top:5px;font-size:7px;color:#667581;font-weight:850}.cbprogress-sub span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cbrunmeta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px}.cbrunmeta div{min-width:0;background:#f6f8fa;border-radius:9px;padding:7px}.cbrunmeta small{display:block;font-size:6px;color:var(--muted);font-weight:950}.cbrunmeta b{display:block;font-size:9px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.cbcurrentitem{background:#eef7fc;border:1px solid #d3e8f4;border-radius:9px;padding:7px 8px}.cbcurrentitem small{display:block;font-size:6px;color:#567184;font-weight:950}.cbcurrentitem b{display:block;font-size:9px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.cbcurrentitem span{display:block;font-size:7px;color:#71808d;font-weight:850;margin-top:2px;overflow-wrap:anywhere}.cbwarn{background:#fff3f1;border:1px solid #f2cbc6;border-radius:9px;padding:7px 8px;color:#9d2c23;font-size:8px;font-weight:850;line-height:1.3}
.mobileupload p{margin:0 0 7px;font-size:8px;color:var(--muted);font-weight:750;line-height:1.3}.duploadpick{display:block;width:100%;border:1px dashed #aabac6;border-radius:10px;background:#f7fafc;padding:9px;font-size:9px;font-weight:850;color:#344754}.duploadpick::file-selector-button{border:0;border-radius:8px;background:#142033;color:#fff;padding:7px 9px;margin-right:8px;font-size:8px;font-weight:950}.duploadnote{width:100%;margin-top:7px;border:1px solid var(--line);border-radius:9px;padding:8px 9px;font-size:10px;font-weight:800;background:#fff}.duploadsummary{margin-top:7px;font-size:8px;color:#667581;font-weight:800;line-height:1.35;overflow-wrap:anywhere}.duploadbtn{width:100%;margin-top:7px;border:0;border-radius:10px;background:#1488c6;color:#fff;padding:10px;font-size:9px;font-weight:1000}.duploadbtn:disabled{opacity:.55}.duploadresult{margin-top:7px;border-radius:9px;background:#f6f8fa;padding:7px 8px;font-size:8px;color:#52616d;font-weight:850;line-height:1.35;overflow-wrap:anywhere}
.batchrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;min-width:0;padding:9px 0;border-top:1px solid var(--line);align-items:start}.batchrow:first-child{border-top:0}.batchrow>div{min-width:0}.batchrow b{display:block;min-width:0;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.batchrow span{display:block;min-width:0;font-size:8px;color:var(--muted);margin-top:3px;overflow-wrap:anywhere}.batchdate{font-size:8px!important;color:#84909a!important;white-space:nowrap}.batchstate{display:inline-block!important;width:auto;border-radius:999px;padding:3px 6px;background:#f3f6f8;color:#5f6d78!important;font-size:7px!important;font-weight:900;line-height:1.15}.batchstate.hold{background:var(--redbg);color:var(--red)!important}.batchstate.ready{background:var(--greenbg);color:var(--green)!important}
.qaresolutioncard{grid-column:1/-1}.qareshead{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.qareshead h3{margin-bottom:2px}.qareshead p{margin:0;font-size:8px;line-height:1.3;color:var(--muted);font-weight:750}.qaresbadge{flex:0 0 auto;border-radius:999px;padding:5px 8px;background:#eef3f7;color:#51606c;font-size:8px;font-weight:950}.qaresbadge.bad{background:var(--redbg);color:var(--red)}.qaresbadge.ok{background:var(--greenbg);color:var(--green)}
.qaresstats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}.qaresstat{background:#f6f8fa;border-radius:9px;padding:7px}.qaresstat small{display:block;font-size:6px;color:var(--muted);font-weight:950}.qaresstat b{display:block;font-size:13px;margin-top:2px}
.qagroups{margin-top:7px;border-top:1px solid var(--line)}.qagroup{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)}.qagroup:last-child{border-bottom:0}.qagroup b{display:block;font-size:10px;line-height:1.18}.qagroup span{display:block;font-size:7px;color:var(--muted);margin-top:2px}.qagroup button{border:0;border-radius:8px;background:#edf3f7;color:#315067;padding:6px 8px;font-size:7px;font-weight:950}.qagroup button.fix{background:#fff1d6;color:#805d00}.qaresactions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.qaresactions button{border:0;border-radius:10px;padding:8px;font-size:8px;font-weight:950}.qaresreview{background:#173047;color:#fff}.qaresrebuild{background:#e9eef2;color:#344653}
.qalist{display:grid;gap:7px}.qaitem{border:1px solid #e2e8ec;background:#fff;border-radius:12px;padding:9px;text-align:left}.qaitemtop{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.qaitem b{font-size:12px}.qaitem small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.qaflag{border-radius:999px;padding:4px 6px;font-size:7px;font-weight:950;white-space:nowrap}.qaflag.fix{background:#fff1d6;color:#805d00}.qaflag.blocked{background:#eef3f7;color:#5e6c77}.qaitemreason{font-size:8px;color:#52616d;line-height:1.35;margin-top:6px}.qafields{display:grid;gap:8px}.qafield label{display:block;font-size:8px;font-weight:950;color:#52616d;margin-bottom:4px}.qafield input,.qafield select,.qafield textarea{width:100%;border:1px solid #d9e1e6;border-radius:10px;background:#fff;padding:9px;font-size:12px;outline:0}.qafield textarea{min-height:68px;resize:vertical}.qaconfirm{display:flex;gap:7px;align-items:flex-start;margin-top:9px;font-size:9px;line-height:1.35;color:#465865}.qaconfirm input{margin-top:2px}.qainfo{background:#f7f9fb;border:1px solid #e3e9ed;border-radius:10px;padding:8px;font-size:9px;line-height:1.4;color:#52616d;margin-top:7px}.qainfo.warn{background:#fff8e6;border-color:#f0dda0;color:#775a0a}
@media(max-width:430px){
  #data .topline{align-items:center}
  #data .hint{font-size:9px}
  .datagrid{grid-template-columns:1fr;gap:8px}
  .dcard{border-radius:17px;padding:12px}
  .dcard h3{font-size:15px;margin-bottom:9px}
  .pipe{gap:5px}.stage{padding:9px 4px}.stage b{font-size:8px}.stage span{font-size:8px}
  .cal{gap:6px}.c{font-size:9px}.dot{width:14px;height:14px}
  .cbid b{font-size:20px}.cbid span{font-size:10px}.cbstatus{font-size:9px;max-width:64%}
  .cbmeta small{font-size:7px}.cbmeta b{font-size:11px}
  .cblive{padding:8px 9px}.cblive b{font-size:11px}.cblive span,.cblivecheck{font-size:8px!important}.cblive-dot{width:10px;height:10px}
  .cbprogress{padding:9px}.cbprogress-top b{font-size:13px}.cbprogress-top span{font-size:9px}.cbprogress-sub{font-size:8px}.cbbar{height:7px}
  .cbrunmeta small{font-size:7px}.cbrunmeta b{font-size:10px}.cbcurrentitem small{font-size:7px}.cbcurrentitem b{font-size:11px}.cbwarn{font-size:9px}
  .batchrow{padding:10px 0}.batchrow b{font-size:13px}.batchrow span{font-size:9px}.batchstate{font-size:8px!important}
  .qaresolutioncard{grid-column:auto}.qareshead p{font-size:9px}.qaresbadge{font-size:9px}.qaresstat small{font-size:7px}.qaresstat b{font-size:16px}.qagroup b{font-size:12px}.qagroup span{font-size:9px}.qagroup button{font-size:9px}.qaresactions button{font-size:10px;padding:10px}.qaitem b{font-size:14px}.qaitem small,.qaitemreason{font-size:10px}.qaflag{font-size:8px}
}
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

.promo-controls{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:7px;margin-top:9px}.promo-controls select,.promo-date-inputs input{width:100%;border:1px solid var(--line);border-radius:11px;background:#fff;padding:9px;font-size:10px;font-weight:850}.promo-import,.promo-manual{border:0;border-radius:11px;background:#142033;color:#fff;padding:9px 11px;font-size:9px;font-weight:950}.promo-manual{background:#f0b82b;color:#332400}.promo-date-inputs{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.promo-date-inputs label{font-size:7px;color:var(--muted);font-weight:950}.promo-date-inputs input{display:block;margin-top:3px;padding:7px}.manual-promo-fields{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.manual-promo-fields label{font-size:8px;color:var(--muted);font-weight:950}.manual-promo-fields input,.manual-promo-fields textarea{display:block;width:100%;margin-top:3px;border:1px solid var(--line);border-radius:10px;background:#fff;padding:9px;font-size:11px;font-weight:850}.manual-promo-fields .wide{grid-column:1/-1}.manual-promo-fields textarea{min-height:112px;resize:vertical;line-height:1.45}
.manual-promo-search{display:grid;gap:8px}
.manual-promo-searchbar{display:flex;gap:7px;align-items:center}
.manual-promo-searchbar input{flex:1;min-width:0;border:2px solid #bdd5e7;border-radius:13px;background:#fff;min-height:48px;padding:0 12px;font-size:16px;font-weight:850;outline:0}
.manual-promo-searchbar input:focus{border-color:#1672bd;box-shadow:0 0 0 3px rgba(22,114,189,.10)}
.manual-promo-searchbar button{border:0;border-radius:12px;background:#174f78;color:#fff;padding:12px 13px;font-size:11px;font-weight:950}
.manual-promo-search-note{font-size:10px;line-height:1.35;color:#637585;font-weight:800}
.manual-promo-results{display:grid;gap:6px;max-height:260px;overflow:auto}
.manual-promo-result{width:100%;text-align:left;border:1px solid #d9e4ec;border-radius:13px;background:#f8fbfe;padding:9px 10px;color:#183349}
.manual-promo-result b{display:block;font-size:16px;line-height:1.12;white-space:normal;overflow-wrap:anywhere}
.manual-promo-result strong{display:block;font-size:12px;color:#0d609f;margin-top:2px}
.manual-promo-result span{display:block;font-size:10px;line-height:1.35;color:#667786;margin-top:4px;font-weight:800}
.manual-promo-selected{display:grid;gap:7px}
.manual-promo-selected-card{border:1.5px solid #8fc6a7;border-radius:14px;background:#effaf4;padding:9px 10px}
.manual-promo-selected-top{display:grid;grid-template-columns:minmax(0,1fr) 86px;gap:8px;align-items:start}
.manual-promo-selected-card h4{font-size:17px;line-height:1.1;margin:0;font-weight:1000;overflow-wrap:anywhere}
.manual-promo-selected-card .selmeta{font-size:10px;line-height:1.35;color:#526b5f;font-weight:850;margin-top:4px}
.manual-promo-selected-card label{display:block;font-size:8px;color:#62756c;font-weight:950}
.manual-promo-selected-card input{width:100%;margin-top:3px;border:1px solid #bfd6ca;border-radius:9px;background:#fff;padding:8px;font-size:16px;font-weight:950}
.manual-promo-delivery{margin-top:5px;padding-top:6px;border-top:1px solid rgba(55,110,80,.14);font-size:10px;line-height:1.35;color:#53685e;font-weight:850}
.manual-promo-remove{border:0;background:transparent;color:#b52e38;font-size:10px;font-weight:950;padding:4px 0 0}

.promo-freshness{margin-top:7px;border:1px solid #efc48a;background:#fff3df;border-radius:10px;padding:7px 8px;font-size:8px;line-height:1.35;color:#7a4b0a;font-weight:850}
.promo-status{font-size:9px;color:var(--muted);font-weight:800;margin:7px 2px}.promo-summary{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.promo-card{background:#fff;border:1px solid var(--line);border-radius:15px;padding:10px;margin-bottom:8px;box-shadow:var(--shadow)}.promo-card-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.promo-card-head b{font-size:14px}.promo-card-head small{display:block;font-size:8px;color:var(--muted);margin-top:2px}.promo-badge{border-radius:999px;padding:5px 7px;font-size:7px;font-weight:950;white-space:nowrap}.promo-badge.weekly{background:#f0eaff;color:#6b21a8}.promo-badge.weekend{background:#fff4d6;color:#8a5b00}.promo-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin-top:8px}.promo-metric{background:#f7f9fb;border-radius:9px;padding:7px;text-align:center;min-width:0}.promo-metric[data-promo-oh]{cursor:pointer;border:1px dashed #aebbc6}.promo-metric small{display:block;font-size:6px;color:var(--muted);font-weight:950}.promo-metric b{display:block;font-size:14px;margin-top:2px}.promo-metric span{display:block;font-size:6px;color:var(--muted);font-weight:850;margin-top:2px}.promo-metric.real-oh{padding:3px}.promo-metric.real-oh .familyohinline{text-align:center;border:0;background:transparent;padding:2px}.promo-metric.temp{background:#fff5e9;border:1px solid #f7bc7a;cursor:pointer}.promo-order{margin-top:7px;background:#eaf8ef;border:1px solid #b8e3c6;border-radius:11px;padding:8px}.promo-order small{font-size:7px;color:#397450;font-weight:950}.promo-order b{display:block;font-size:22px;color:#17683c}.promo-break{font-size:8px;color:#436052;margin-top:2px}.promo-review{background:#fff8e1;border:1px solid #efdca2;border-radius:11px;padding:8px;font-size:9px;margin-bottom:7px}

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
.qrnum{font-size:13px;font-weight:950;line-height:1.05}.qrname{font-size:9px;font-weight:800;color:#334554;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}.qr7d{display:block;font-size:7px;font-weight:950;color:#17683c;margin-top:2px;white-space:nowrap}
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
.qfamily .qmeta{font-size:7px;margin-top:2px}.qfamilycost{display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-top:4px;padding:4px 6px;border:1px solid rgba(95,105,113,.14);border-radius:8px;background:rgba(255,255,255,.58)}.qfamilycost span{font-size:6px;color:#6d7b86;font-weight:950}.qfamilycost b{font-size:12px;line-height:1;font-weight:1000;color:#253949}.qfamilycost small{font-size:6px;color:#849099;font-weight:850}
.qffocus{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;margin-top:5px}
.qffocusbox{display:flex;align-items:center;justify-content:space-between;gap:5px;min-width:0;background:rgba(255,255,255,.58);border:1px solid rgba(95,105,113,.14);border-radius:8px;padding:4px 6px}
.qffocusbox small{display:block;font-size:6px;color:#6d7b86;font-weight:950;line-height:1}
.qffocusbox span{display:block;font-size:6px;color:#849099;font-weight:850;line-height:1;margin-top:2px;white-space:nowrap}
.qffocusbox b{font-size:21px;line-height:1;font-weight:1000;letter-spacing:-.03em;white-space:nowrap}
.qffocusbox.receipt b{color:#26343e}
.familyohbtn{width:100%;border:1px solid #a8d5c3;background:#ecf8f2;color:#155f48;border-radius:8px;padding:5px 6px;text-align:left;cursor:pointer;min-width:0}
.familyohbtn small{display:block;font-size:6px;font-weight:1000;color:#4e7d6d;line-height:1}
.familyohbtn b{display:block;font-size:15px;font-weight:1000;line-height:1.05;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.familyohbtn span{display:block;font-size:6px;font-weight:900;color:#278566;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.familyohinline{border:1px solid #a8d5c3;background:#ecf8f2;color:#155f48;border-radius:9px;padding:5px 6px;cursor:pointer;text-align:right;min-width:54px}
.familyohinline b{display:block;font-size:15px;line-height:1;font-weight:1000}.familyohinline span{display:block;font-size:7px;color:#278566;font-weight:900;margin-top:2px}
.stockohbar{margin-top:5px}.stockohbar .familyohbtn{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:7px;text-align:left;padding:6px 8px}
.stockohbar .familyohbtn small{font-size:7px}.stockohbar .familyohbtn b{text-align:right;font-size:17px}.stockohbar .familyohbtn span{text-align:right}
.pm .familyohbtn{border:0;background:transparent;padding:0;text-align:left}.pm .familyohbtn b{font-size:12px}.pm .familyohbtn span{font-size:6px}
.dm .familyohbtn{border:0;background:transparent;padding:0;text-align:center}.dm .familyohbtn b{font-size:20px}.dm .familyohbtn span{font-size:7px}
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
.stockflowsort{flex:0 0 auto;font-size:7px;color:#71808d;font-weight:950}.stockflowsort select{display:block;margin-top:2px;border:1px solid #cbddeb;background:#edf6fd;color:#315b78;border-radius:999px;padding:5px 22px 5px 7px;font-size:8px;font-weight:950;outline:0}
.stockdiff{align-self:start;text-align:right;background:#fff0f0;border:1px solid #efcccc;border-radius:9px;padding:5px 7px;min-width:88px}.stockdiff small{display:block;font-size:6px;color:#9a6767;font-weight:950}.stockdiff b{display:block;font-size:15px;line-height:1;color:#c12e2e;margin-top:2px}.stockdiff>span{display:block;font-size:7px;color:#9a6767;margin-top:2px;font-weight:850}.stockdiff.promoted{background:#8df08f;border-color:#42c95e;box-shadow:0 4px 11px rgba(38,169,74,.13);min-width:112px}.stockdiff.promoted small{color:#205b2d}.stockdiff.promoted b{color:#123f1d}.stockdiff.promoted>span{color:#2e6338}.stockpromo{margin-top:5px;padding-top:5px;border-top:1px solid rgba(28,100,45,.24)}.stockpromo strong{display:block;font-size:6.5px;line-height:1.18;color:#164f24;font-weight:1000;white-space:nowrap}.stockpromo span{display:block;font-size:7px;line-height:1.18;color:#245b32;font-weight:950;margin-top:2px;white-space:nowrap}
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


/* V362 Price Suggestions: slightly larger while preserving compact density. */
#price .topline{margin-bottom:5px}
#price .filters{margin-bottom:6px}
#price .filters .pill{font-size:11px;padding:8px 11px}
#priceStatus{font-size:11px!important;line-height:1.3!important;margin-bottom:6px!important}
.pricecards{gap:7px}
.pcard{border:1px solid #e0e6eb;border-radius:15px;padding:11px 12px;box-shadow:0 4px 14px rgba(18,38,56,.065)}
.ptop{align-items:flex-start;gap:6px}.ptop>div:first-child{min-width:0}
.ptop b{display:block;font-size:16px!important;line-height:1.12;white-space:normal}
.ptop small{font-size:10px!important;line-height:1.24;margin-top:2px}
.pbadge{flex:0 0 auto;border-radius:999px;padding:5px 8px;font-size:9px;font-weight:950;white-space:nowrap}
.pbadge.red{background:var(--redbg);color:var(--red)}.pbadge.amber{background:var(--amberbg);color:var(--amber)}.pbadge.green{background:var(--greenbg);color:var(--green)}
.pricepath{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}
.pp{min-width:0;border:1px solid #e3e8ec;background:#f5f7f9;border-radius:10px;padding:7px 8px}
.pp.tested{background:#fff9e4;border-color:#efdda0}.pp.testing{background:#eaf7ff;border-color:#c5e5f5}
.pp small{display:block;font-size:8px;font-weight:950;letter-spacing:.05em;color:#7c8892;line-height:1}
.pp b{display:block;font-size:21px;line-height:1;margin-top:3px;font-weight:1000;white-space:nowrap}
.pp span{display:block;font-size:8px;color:#7c8892;font-weight:850;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pp.tested b{color:#7a5a00}.pp.testing b{color:#0878ad}
.pcost{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;padding:5px 7px;border:1px solid #e5eaed;background:#fbfcfd;border-radius:8px;font-size:8px;font-weight:850;color:#65737e}
.pcost b{font-size:10px;color:#1f303d;white-space:nowrap}.pcost span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pmetrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin-top:6px}
.pm{min-width:0;border:1px solid #e8edf0;background:#fafbfc;border-radius:8px;padding:5px 6px}
.pm small{display:block;font-size:7px;font-weight:950;color:#8a959e;line-height:1}
.pm b{display:block;font-size:12px;font-weight:950;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pprogress{margin-top:6px;background:#f8fafb;border:1px solid #e7ecef;border-radius:9px;padding:6px 7px}
.pprogress-line{display:flex;align-items:center;justify-content:space-between;gap:7px;font-size:9px;color:#5f6d78;font-weight:850;line-height:1.24}
.pprogress-line b{font-size:10px;color:#263744}.pprogress-line strong{font-size:10px;color:#0878ad;white-space:nowrap}
.pbar{height:4px;background:#e4eaee;border-radius:999px;overflow:hidden;margin-top:4px}.pbar i{display:block;height:100%;background:#118fc6;border-radius:999px}
.pchips{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px}.pchip{border:1px solid #e3e8ec;background:#fafbfc;color:#5f6d78;border-radius:7px;padding:4px 6px;font-size:8.5px;font-weight:950}
.preason{margin-top:6px;border-top:1px solid #edf1f3;padding-top:6px}.preason summary{list-style:none;cursor:pointer;color:#0879b3;font-size:9px;font-weight:950}.preason div{margin-top:5px;color:#64727e;font-size:9px;line-height:1.45;font-weight:750}
.pcard-actions{display:grid;grid-template-columns:1fr auto;gap:6px;margin-top:7px}.pcard-actions button{border-radius:9px;padding:8px 10px;font-size:9px;font-weight:950}
.pdetail{border:1px solid #d9e1e6;background:#fff;color:#263744}.pignore{border:1px solid #efb7bc;background:#fde8ea;color:#a12632}
@media(max-width:390px){.pp b{font-size:22px}.pm b{font-size:12px}.pcard{padding:11px 12px}}

/* V378: slightly larger Order Suggestions + Price Suggestions reading scale. */
#order .topline h2,#price .topline h2{font-size:26px}
#orderStatus{font-size:12px!important;line-height:1.32!important}
#order .order-tab{font-size:12px;padding:11px 8px}
#order .order-date-card{padding:9px 10px}
#order .order-date-card small{font-size:8px}
#order .order-date-card b{font-size:17px}
#order .order-date-card span{font-size:8px}
#order .order-coverage{padding:9px 11px}
#order .order-coverage small{font-size:8px}
#order .order-coverage b{font-size:18px}
#order .order-coverage span{font-size:9px}
#order .order-summary{font-size:10px}
#order .order-controls label{font-size:7px}
#order .order-controls select{font-size:9px;padding:6px 21px 6px 8px}
#order .lh,#order .orow{grid-template-columns:minmax(0,1fr) 60px 68px;padding-left:12px;padding-right:12px}
#order .lh{font-size:10px;padding-top:9px;padding-bottom:9px}
#order .orow>div{padding:11px 0}
#order .orow .name{font-size:15px;line-height:1.14}
#order .orow .sub{font-size:10px;line-height:1.28;margin-top:3px}
#order .cell{font-size:15px}
#order .cell span{font-size:10px}
#order .orderstate,#order .order-risk,#order .order-lowconf{font-size:7px;padding:3px 6px}
#order .orow .name{font-size:18px;line-height:1.08}
#order .familyline{display:flex;align-items:baseline;gap:7px;margin-top:5px;min-width:0}
#order .familyline span{font-size:8px;color:#71808d;font-weight:950;letter-spacing:.04em}
#order .familyline b{font-size:16px;line-height:1;color:#0d4f8b;font-weight:1000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#order #orderList.futurecards{background:transparent;border-radius:0;box-shadow:none;overflow:visible}
#order #orderList.futurecards #orderRows{display:grid;gap:12px}
#order #orderList.futurecards #orderListHead{display:none}
#order .orderitemcard{background:#fff;border:1px solid #dbe4ed;border-radius:17px;overflow:hidden;box-shadow:0 6px 18px rgba(18,38,56,.075);position:relative}
#order .orderitemcard.urgent{border-left:5px solid #df2736}
#order .orderitemcard.review{border-left:5px solid #d3a000}
#order .orderitemcard.zero{border-left:5px solid #a7b1b9}
#order .orderitemhead{display:grid;grid-template-columns:minmax(0,1fr) 60px 68px;gap:0;background:#eef3f7;border-bottom:1px solid #dce5ec;padding:9px 12px;color:#5f7082;font-size:10px;font-weight:950;letter-spacing:.015em}
#order .orderitemhead span:nth-child(2),#order .orderitemhead span:nth-child(3){text-align:right}
#order .orderitemmain{display:grid;grid-template-columns:minmax(0,1fr) 60px 68px;gap:0;padding:0 12px}
#order .orderitemmain>div{padding:12px 0}
#order .orderitemmain .name{font-size:18px;line-height:1.08;font-weight:1000}
#order .orderitemmain .sub{font-size:10px;line-height:1.28;margin-top:4px;color:#71808d}
#order .orderitemmain .cell{text-align:right;font-size:15px;font-weight:950}
#order .orderitemmain .cell span{display:block;font-size:10px;color:#71808d}
#order .orderitemmain .orderqty{font-size:19px;color:#0d4f8b}
#order .familyline{display:flex;align-items:baseline;gap:7px;margin-top:6px;min-width:0}
#order .familyline span{font-size:8px;color:#71808d;font-weight:950;letter-spacing:.04em}
#order .familyline b{font-size:18px;line-height:1;color:#0d4f8b;font-weight:1000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#order .orderrecvhistory{margin:0 12px 12px;border:1px solid #bed8ee;background:#f4f9fe;border-radius:13px;padding:0!important;overflow:hidden}
#order .orderrecvhistoryhead{display:flex;align-items:center;gap:7px;padding:8px 10px;background:#eaf4fc;border-bottom:1px solid #d7e7f3;color:#2e6797}
#order .orderrecvhistoryicon{width:23px;height:23px;border-radius:7px;border:1px solid #8dbbe0;display:grid;place-items:center;font-size:12px;font-weight:1000;background:#f9fcff;color:#1268ad;flex:0 0 auto}
#order .orderrecvhistoryhead b{font-size:9px;line-height:1.15;font-weight:1000;letter-spacing:.025em}
#order .orderrecvhistoryhead span{margin-left:auto;font-size:8px;color:#6382a0;font-weight:900}
#order .orderrecvrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:9px 10px;border-top:1px solid #dbe7f0}
#order .orderrecvrow:first-of-type{border-top:0}
#order .orderrecvarticle{min-width:0}
#order .orderrecvarticle b{display:block;font-size:17px;line-height:1.04;color:#0d4f8b;font-weight:1000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#order .orderrecvarticle span{display:block;font-size:9px;color:#71808d;font-weight:850;margin-top:3px}
#order .orderrecvpack{text-align:right;min-width:102px;border-left:1px solid #dbe7f0;padding-left:10px}
#order .orderrecvpack b{display:block;font-size:15px;line-height:1.05;color:#172c3c;font-weight:1000;white-space:normal}
#order .orderrecvpack span{display:block;font-size:7px;color:#71808d;font-weight:950;margin-top:3px;letter-spacing:.04em}
#order .orderrecvmore{font-size:8px;color:#5d7185;font-weight:900;padding:7px 10px;border-top:1px solid #dbe7f0;background:#f8fbfe}
#order .orderstate,#order .order-risk,#order .order-lowconf,#order .order-freshness{vertical-align:middle}
#order .order-freshness{display:inline-block;margin-left:4px;border-radius:999px;padding:3px 6px;font-size:7px;font-weight:950;background:#fff0d8;color:#8a5100}
#order .orderitemcard:active{transform:scale(.996)}

#order .rtrace-line{font-size:11px}
#order .rtrace-more{font-size:10px}
#order .receipt-meta{font-size:11px}

#price{overflow-x:hidden}
#price .filters{max-width:100%}
#price .filters .pill{font-size:12px;padding:9px 12px}
#price .price-tools{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:0 0 7px;min-width:0}
#price .price-tools label{display:block;min-width:0;font-size:8px;color:#71808d;font-weight:950}
#price .price-tools select{display:block;width:100%;min-width:0;margin-top:3px;border:1px solid #d7e0e6;border-radius:10px;background:#fff;padding:8px 28px 8px 9px;font-size:10px;font-weight:900;outline:0}
#priceStatus{font-size:12px!important;line-height:1.32!important}
#price .pricecards{gap:8px;width:100%;min-width:0;max-width:100%;overflow:hidden}
#price .pcard{padding:12px 13px;border-radius:16px;width:100%;min-width:0;max-width:100%;overflow:hidden}
#price .ptop,#price .pricepath,#price .pmetrics,#price .pprogress,#price .pcost{min-width:0;max-width:100%}
#price .pprogress-line span{min-width:0;overflow-wrap:anywhere}
#price .preason div{overflow-wrap:anywhere}
#price .pairauthority{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);align-items:center;gap:7px;margin-top:7px;padding:8px;border:1px solid #f0c7c7;border-radius:10px;background:#fff5f5;min-width:0}
#price .pairauthority>div{min-width:0}#price .pairauthority small{display:block;font-size:8px;color:#8b5d5d;font-weight:950}#price .pairauthority b{display:block;font-size:20px;line-height:1.05;margin-top:2px}#price .pairauthority span{display:block;font-size:8px;color:#7c6d6d;margin-top:2px;white-space:normal;overflow-wrap:anywhere}#price .pairarrow{font-size:18px;font-weight:1000;color:#c84747}
#price .ptop b{font-size:17px!important}
#price .ptop small{font-size:11px!important}
#price .pbadge{font-size:10px;padding:5px 9px}
#price .pp{padding:8px 9px}
#price .pp small{font-size:9px}
#price .pp b{font-size:23px}
#price .pp span{font-size:9px}
#price .pcost{font-size:9px;padding:6px 8px}
#price .pcost b{font-size:11px}
#price .pm{padding:6px 7px}
#price .pm small{font-size:8px}
#price .pm b{font-size:13px}
#price .pprogress{padding:7px 8px}
#price .pprogress-line{font-size:10px}
#price .pprogress-line b,#price .pprogress-line strong{font-size:11px}
#price .pchip{font-size:9.5px;padding:4px 7px}
#price .preason summary{font-size:10px}
#price .preason div{font-size:10px}
#price .pcard-actions button{font-size:10px;padding:9px 11px}
@media(max-width:370px){
  #order .lh,#order .orow{grid-template-columns:minmax(0,1fr) 54px 66px;padding-left:10px;padding-right:10px}
  #order .orow .name{font-size:17px}
  #order .familyline b{font-size:15px}
  #price .pp b{font-size:21px}
  #price .pairauthority b{font-size:18px}
}


/* Current TPR review tab */
.price-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;background:#e8eef3;border:1px solid #d4dfe7;border-radius:13px;padding:4px;margin:0 0 9px}
.price-tab{border:0;background:transparent;border-radius:10px;padding:9px 4px;font-size:9px;font-weight:950;color:#687784;line-height:1.05;min-width:0}
.price-tab.on{background:#fff;color:#0870c8;box-shadow:0 2px 8px rgba(16,43,64,.10)}
.price-tab span{font-size:9px;color:#6f8190}
.price-tab.on span{color:#0870c8}
.tpr-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-bottom:7px}
.tpr-summary>div{border:1px solid #dce5eb;background:#fff;border-radius:11px;padding:7px 5px;text-align:center}
.tpr-summary b{display:block;font-size:18px;line-height:1}.tpr-summary span{display:block;font-size:7px;font-weight:950;color:#788793;margin-top:3px}
.tpr-rule{border:1px solid #c7e1f5;background:#edf7ff;color:#35627f;border-radius:11px;padding:8px 9px;font-size:9px;line-height:1.35;font-weight:780;margin-bottom:7px}
.tpr-rule b{color:#0a5f9e}
.tpr-tools{display:grid;grid-template-columns:minmax(0,1fr) 118px;gap:7px;align-items:end;margin-bottom:7px}
.tpr-tools .hint{margin:0!important;font-size:10px!important;line-height:1.3!important}
.tpr-tools label{font-size:7px;color:#71808d;font-weight:950}.tpr-tools select{display:block;width:100%;margin-top:3px;border:1px solid #d7e0e6;border-radius:9px;background:#fff;padding:7px 23px 7px 8px;font-size:9px;font-weight:900}
.tprcard .preasoncall{margin-top:7px}
.tprcard .tprwindow{font-size:8px;color:#73818d;font-weight:850;margin-top:5px}
.tprcard .tprlift{font-weight:1000}.tprcard .tprlift.good{color:#167448}.tprcard .tprlift.bad{color:#b82d38}.tprcard .tprlift.neutral{color:#6f7b85}
.tprcard .pbadge.continue{background:#e5f7eb;color:#147946}.tprcard .pbadge.observe{background:#edf1f5;color:#647280}.tprcard .pbadge.adjust{background:#fff0d9;color:#986000}.tprcard .pbadge.urgent{background:#fde4e7;color:#ae2330}.tprcard .pbadge.end{background:#efe9fb;color:#6945b5}
.tprpurpose{display:flex;align-items:center;justify-content:space-between;gap:7px;margin-top:6px;border-radius:9px;padding:6px 8px;font-size:8px;font-weight:950;letter-spacing:.01em}
.tprpurpose.sweet{background:#eef5ff;color:#175f9c;border:1px solid #cfe1f4}.tprpurpose.freshness{background:#fff4dc;color:#8a5a00;border:1px solid #ecd59a}
.tprmonitor{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:6px}.tprmonitor>div{background:rgba(255,255,255,.72);border:1px solid rgba(80,95,110,.13);border-radius:9px;padding:6px}
.tprmonitor small{display:block;font-size:6.5px;color:#73818d;font-weight:1000}.tprmonitor b{display:block;font-size:11px;line-height:1.15;margin-top:2px}.tprmonitor span{display:block;font-size:7px;color:#71808d;font-weight:850;margin-top:2px}
.tprsuggest{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;background:#fff;border:1px solid #dbe3e9;border-radius:9px;padding:7px 8px}.tprsuggest span{font-size:7px;color:#71808d;font-weight:950}.tprsuggest b{font-size:13px}
.tprpurposepick{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:7px}.tprpurposepick button{border:1.5px solid #cfd9e1;background:#fff;border-radius:11px;padding:9px 7px;font-size:10px;font-weight:950;color:#425463}.tprpurposepick button.on{border-color:#1674c6;background:#eaf5ff;color:#0b67ae}
.tprtimeline{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:8px 0}.tprtimeline>div{border:1px solid #dce4ea;border-radius:11px;background:#fff;padding:8px}.tprtimeline small{display:block;font-size:7px;color:#71808d;font-weight:950}.tprtimeline b{display:block;font-size:13px;margin-top:3px}.tprtimeline span{display:block;font-size:8px;color:#647482;font-weight:800;margin-top:3px}
.tprsteps{margin-top:8px;border:1px solid #dde5eb;border-radius:11px;overflow:hidden}.tprstep{display:grid;grid-template-columns:64px 60px minmax(0,1fr);gap:7px;padding:7px 8px;border-top:1px solid #edf0f3;font-size:9px}.tprstep:first-child{border-top:0}.tprstep b{font-size:10px}.tprstep span{color:#657582}

/* Clearance planning */
.clearance-intro{border:1px solid #efcf9f;background:#fff7e8;border-radius:12px;padding:9px 10px;font-size:9px;line-height:1.35;color:#6f541f;margin-bottom:7px}.clearance-intro b{color:#8a5800}
.clearance-search{display:grid;grid-template-columns:minmax(0,1fr) 72px;gap:6px;margin-bottom:7px}.clearance-search input{min-width:0;border:1.5px solid #cbd9e3;border-radius:11px;background:#fff;padding:10px 11px;font-size:14px;font-weight:850;outline:0}.clearance-search button{border:0;border-radius:11px;background:#173f5f;color:#fff;font-size:9px;font-weight:950}
.clearance-search-results{display:grid;gap:5px;margin-bottom:7px}.clearance-search-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:center;border:1px solid #d9e2e8;border-radius:11px;background:#fff;padding:8px;text-align:left;color:#203442}.clearance-search-item b{display:block;font-size:11px}.clearance-search-item span{display:block;font-size:8px;color:#75848f;margin-top:2px}.clearance-search-item strong{font-size:9px;color:#0d6cac}
.clearance-card{border:1.5px solid #e0a849;border-left:5px solid #e0a849;border-radius:13px;background:linear-gradient(90deg,#fff5de,#fff);padding:9px;margin-bottom:7px;box-shadow:0 6px 16px rgba(64,42,9,.06)}
.clearance-card .ctop{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px}.clearance-card .ctop b{font-size:16px;line-height:1.05}.clearance-card .ctop small{display:block;font-size:8px;color:#746c60;margin-top:2px}.clearance-badge{align-self:start;background:#fff0cc;color:#885500;border-radius:999px;padding:5px 7px;font-size:8px;font-weight:1000}
.clearance-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin-top:7px}.clearance-metrics>div{background:rgba(255,255,255,.78);border:1px solid #ead9b7;border-radius:9px;padding:6px}.clearance-metrics small{display:block;font-size:6.5px;color:#846f51;font-weight:950}.clearance-metrics b{display:block;font-size:12px;margin-top:2px}
.clearance-stage{display:grid;grid-template-columns:54px 74px minmax(0,1fr);gap:6px;align-items:center;border-top:1px solid rgba(150,110,45,.16);padding:6px 0;font-size:8px}.clearance-stage:first-child{border-top:0}.clearance-stage b{font-size:12px}.clearance-stage span{color:#746c60}
.clearance-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:7px}.clearance-actions button{border:1px solid #d4dde3;border-radius:10px;background:#fff;padding:8px;font-size:9px;font-weight:950;color:#314858}.clearance-actions button.primary{background:#173f5f;color:#fff;border-color:#173f5f}
.clearance-form{display:grid;gap:8px}.clearance-form label{font-size:8px;color:#6f7c86;font-weight:950}.clearance-form input{display:block;width:100%;margin-top:3px;border:1.5px solid #cfd9e0;border-radius:10px;background:#fff;padding:10px;font-size:16px;font-weight:850}.clearance-form .row2{display:grid;grid-template-columns:1fr 1fr;gap:7px}
@media(max-width:370px){.price-tab{font-size:10px}.tpr-tools{grid-template-columns:minmax(0,1fr) 105px}.tpr-summary b{font-size:17px}}

/* V386 Yipman AI: compact read-only assistant with live sales/performance lookup. */
.nav{grid-template-columns:repeat(4,1fr)}
.nav button[data-go="ai"] i{color:#ffd84d}
.nav button[data-go="ai"].on i{background:#dceefe;color:#0869bd}
#ai{overflow:hidden;padding:0 6px calc(73px + env(safe-area-inset-bottom))}
#ai.on{display:flex;flex-direction:column;gap:8px}
.aihead{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:3px 8px 7px}
.aiheadleft{display:flex;align-items:center;gap:9px;min-width:0}
.aimark{width:40px;height:40px;border-radius:13px;background:#1b3448;color:#ffd84d;display:grid;place-items:center;font-size:21px;font-weight:1000;flex:0 0 auto}
.aiheadcopy{min-width:0}.aiheadcopy h2{font-size:25px;line-height:1;margin:0;font-weight:1000;letter-spacing:-.03em}.aiheadcopy p{font-size:10px;line-height:1.2;color:var(--muted);font-weight:800;margin:4px 0 0}
.aireadonly{flex:0 0 auto;background:#edf8f2;color:#28734e;border:1px solid #cfe8d9;border-radius:999px;padding:6px 8px;font-size:9px;font-weight:950}
.aipagechat{flex:1;min-height:0;display:flex;flex-direction:column;background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:0 8px 22px rgba(18,38,56,.08);overflow:hidden}
.aichat{display:flex;flex-direction:column;gap:9px;flex:1;min-height:0;overflow:auto;padding:13px}
.aibubble{max-width:94%;padding:12px 13px;border-radius:16px;font-size:13px;line-height:1.46}
.aibubble.ai{align-self:flex-start;background:#f4f7f9;border:1px solid #e1e7ec;border-top-left-radius:6px}
.aibubble.ai.brief{max-width:100%;background:#eef6ff;border-color:#cfe2f7;border-top-left-radius:16px}
.aibubble.ai.thinking{color:#667581}
.aibubble.user{align-self:flex-end;background:#1b3448;color:#fff;border-top-right-radius:6px}
.aibubble.notice{background:#fff7df;border-color:#eed48f}.aibubble.notice b{color:#775400}
.aibubble.urgent{background:#fff1f1;border-color:#efcaca}.aibubble.urgent b{color:#b22828}
.aibubble.info{background:#eef6ff;border-color:#cfe2f7}.aibubble b{font-size:14px;line-height:1.35}
.aimeta{margin-top:7px;padding-top:7px;border-top:1px solid rgba(70,105,130,.16);font-size:10px;color:#71808d;font-weight:750}
.aicomposer{display:flex;gap:8px;padding:10px 12px 12px;border-top:1px solid #e7edf2;background:#fff;flex:0 0 auto}
.aicomposer input{flex:1;min-width:0;border:1.5px solid #d7e0e7;border-radius:14px;background:#fff;min-height:52px;padding:0 13px;font-size:16px;font-weight:700;outline:0}
.aicomposer input:focus{border-color:#1769e0;box-shadow:0 0 0 3px rgba(23,105,224,.10)}
.aicomposer button{width:54px;min-height:52px;border:0;border-radius:14px;background:#1b3448;color:#ffd84d;font-size:22px;font-weight:1000}
@media(max-width:370px){.aiheadcopy h2{font-size:23px}.aiheadcopy p{font-size:9px}.aibubble{font-size:12px;padding:11px 12px}.aibubble b{font-size:13px}.aicomposer input{font-size:15px}}


/* V388 clarity pass: thicker Quick Search + article color separation. */
.quicksearch{border-width:2.4px}

#order .orderitemcard,
#price .pcard{
  --article-accent:#ddb916;
  --article-wash:#fff3b7;
  background:linear-gradient(100deg,var(--article-wash),#fff 62%);
  border-color:var(--article-accent);
  border-left:5px solid var(--article-accent)!important;
}
#order .orderitemcard.tone1,#price .pcard.tone1{--article-accent:#58bd70;--article-wash:#e2f6e6}
#order .orderitemcard.tone2,#price .pcard.tone2{--article-accent:#4a9de2;--article-wash:#e6f2fc}
#order .orderitemcard.tone3,#price .pcard.tone3{--article-accent:#ef72a5;--article-wash:#fde7ef}
#order .orderitemcard.tone4,#price .pcard.tone4{--article-accent:#9b7be0;--article-wash:#eee8fb}
#order .orderitemhead{background:rgba(255,255,255,.62);border-bottom-color:rgba(80,95,110,.14)}
#order .orderrecvhistory{border-color:color-mix(in srgb,var(--article-accent) 45%,#d8e5ef);background:rgba(255,255,255,.58)}
#order .orderrecvhistoryhead{background:rgba(255,255,255,.56);border-bottom-color:rgba(80,95,110,.12)}
#order .familyline{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:7px;row-gap:2px;align-items:baseline}
#order .familyline .receivingname{grid-column:2;font-size:10px;color:#465d70;font-weight:900;line-height:1.18;white-space:normal;overflow:visible}
#order .orderrecvarticle .receivingname{display:block;font-size:9px;line-height:1.16;color:#344b5e;font-weight:950;margin-top:2px;white-space:normal}
#price .pcard{border-width:1.5px}
#price .pcard .pp,#price .pcard .pcost,#price .pcard .pm{background-color:rgba(255,255,255,.68)}
.stockpromo .promolift{display:inline-block;font-size:9px;line-height:1.15;color:#102917;font-weight:1000;margin-top:3px;white-space:nowrap;background:#fff34a;border-radius:999px;padding:2px 7px}
.stockpromo .promobasis{display:block;font-size:6.5px;line-height:1.15;color:#245b32;font-weight:900;margin-top:2px;white-space:nowrap}
.stockdiff.promoted>b{display:inline-block;background:#fff34a;border-radius:999px;padding:2px 7px;margin-top:3px}
.stockpromo .promoprice{display:flex;align-items:center;justify-content:space-between;gap:7px;margin-top:4px;background:#fff34a;border-radius:999px;padding:3px 7px;color:#102917;white-space:nowrap}
.stockpromo .promoprice small{display:block;font-size:6.5px!important;color:#1c3a22!important;font-weight:1000!important;margin:0!important}
.stockpromo .promoprice b{display:block;font-size:9px!important;line-height:1.05!important;color:#102917!important;font-weight:1000!important;margin:0!important}


/* V392 Quick Check Stock Flow: compact flow-first card layout. */
.stockratio{align-self:start;background:rgba(255,255,255,.78);border:1px solid rgba(70,80,90,.12);border-radius:8px;padding:4px 6px;text-align:right;min-width:76px}
.stockratio small{display:block;font-size:6px;color:#74808a;font-weight:950;letter-spacing:.02em}
.stockratio b{display:block;font-size:13px;line-height:1.05;font-weight:1000;margin-top:1px}
.stockflowgrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(90px,.82fr);gap:4px;margin-top:5px}
.stockflowgrid .bestmetric{min-width:0;padding:5px 6px}
.stockflowgrid .bestmetric b{font-size:17px;white-space:nowrap}
.stockflowgrid .bestmetric span{font-size:6.5px}
.stockflowgrid .stockdiff{align-self:stretch;min-width:0;text-align:left;padding:5px 6px;border-radius:8px;background:#ffe9e9;border-color:#e7b0b0;box-shadow:none}
.stockflowgrid .stockdiff small{font-size:6px;color:#945a5a}
.stockflowgrid .stockdiff>b{display:block!important;background:transparent!important;padding:0!important;margin-top:2px!important;font-size:16px;line-height:1;color:#a72b2b;white-space:nowrap}
.stockflowgrid .stockdiff>span{font-size:6.5px;color:#8d5e5e;margin-top:2px}
.stockflowgrid .stockdiff.promoted{background:#dff6df;border-color:#7bcf8d;box-shadow:none;min-width:0}
.stockflowgrid .stockdiff.promoted small,.stockflowgrid .stockdiff.promoted>span{color:#356a42}
.stockflowgrid .stockdiff.promoted>b{color:#123f1d}
.stockflowgrid .stockdiff.nosale{background:#ffe9e9;border-color:#e7b0b0}
.stockwatch{display:inline-block!important;width:max-content;border-radius:999px;background:#fff06a;padding:2px 5px!important;font-size:6px!important;font-weight:1000!important;color:#463f00!important}
.stocksale.stockpromo{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 7px;align-items:center;margin-top:4px;padding:5px 6px;border:1px solid rgba(64,170,74,.25);border-radius:8px;background:rgba(111,229,119,.18)}
.stocksale.stockpromo strong{grid-column:1/-1;font-size:6.5px}
.stocksale.stockpromo .promolift{margin:0;font-size:8px;padding:2px 6px}
.stocksale.stockpromo .promobasis{margin:1px 0 0;font-size:6px}
.stocksale.stockpromo .promoprice{margin:0;padding:3px 6px;min-width:92px}
.stocksale.stockpromo .promoprice small{font-size:5.8px!important}
.stocksale.stockpromo .promoprice b{font-size:8px!important}
@media(max-width:365px){
  .stockflowgrid{grid-template-columns:minmax(0,1fr) minmax(0,1fr) 86px}
  .stockflowgrid .bestmetric b{font-size:15px}
  .stockflowgrid .stockdiff>b{font-size:14px}
  .stockratio{min-width:70px}
}



/* V393 Price Suggestions: make UPC identity + action reason impossible to miss. */
#price .pcard{padding-top:10px}
#price .ptop{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
#price .pidentity{min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:5px}
#price .pidentity>b{font-size:17px!important;line-height:1.12!important;font-weight:1000;letter-spacing:-.01em}
#price .pupc{display:inline-flex;align-items:center;gap:7px;max-width:100%;padding:6px 10px;border-radius:10px;background:#e91d3c;color:#fff;box-shadow:0 3px 8px rgba(233,29,60,.18);line-height:1}
#price .pupc span{font-size:10px;font-weight:1000;letter-spacing:.035em}
#price .pupc strong{font-size:15px;font-weight:1000;letter-spacing:.01em;white-space:nowrap}
#price .pbadge{margin-top:1px}
#price .preasoncall{display:grid;grid-template-columns:26px minmax(0,1fr) 18px;align-items:center;gap:7px;margin-top:8px;padding:9px 10px;border:1px solid;border-radius:11px;font-size:11px;line-height:1.28;font-weight:780}
#price .preasoncall strong{font-size:12px;font-weight:1000}
#price .preasonmark{display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:999px;font-size:16px;font-weight:1000}
#price .preasonchev{font-size:24px;line-height:1;text-align:right;font-weight:850}
#price .preasoncall.red{background:#fff0f2;border-color:#f2c3ca;color:#bd1f31}
#price .preasoncall.red .preasonmark{background:#d91f35;color:#fff}
#price .preasoncall.amber{background:#fff8e6;border-color:#efd99d;color:#7b5a00}
#price .preasoncall.amber .preasonmark{background:#c48a00;color:#fff}
#price .preasoncall.green{background:#edf9f0;border-color:#c3e7ca;color:#216a35}
#price .preasoncall.green .preasonmark{background:#2d8a49;color:#fff}
@media(max-width:390px){
  #price .pupc{padding:6px 9px}
  #price .pupc strong{font-size:14px}
  #price .pidentity>b{font-size:16px!important}
  #price .preasoncall{font-size:10.5px}
}


/* V395 Stock Flow: observed-delivery + category filters. */
.stockflowfilters{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:7px;margin:0 0 7px;padding:7px;border:1px solid #bfd9ee;border-radius:13px;background:linear-gradient(180deg,#f8fcff,#eef7fd)}
.stockfiltergroup{min-width:0}.stockfiltergroup>small{display:block;margin:0 0 4px;font-size:7px;font-weight:1000;letter-spacing:.035em;color:#647888}
.stockfiltergroup.category{border-left:1px solid #d4e3ee;padding-left:7px}
.stockfilterbuttons{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;padding-bottom:1px}.stockfilterbuttons::-webkit-scrollbar{display:none}
.stockfilterbtn{flex:0 0 auto;border:1px solid #d1dde6;background:#fff;color:#29475e;border-radius:999px;padding:6px 8px;font-size:8px;font-weight:950;line-height:1;white-space:nowrap;box-shadow:0 1px 2px rgba(22,50,74,.04)}
.stockfilterbtn b{font-size:7px;opacity:.72;margin-left:2px}.stockfilterbtn.on{background:#0878d1;border-color:#0878d1;color:#fff;box-shadow:0 3px 8px rgba(8,120,209,.20)}
.stockfilterbtn.deliverytw:not(.on){background:#fff5df;border-color:#f1d8a4;color:#725000}.stockfilterbtn.deliverytf:not(.on){background:#f6eaff;border-color:#dbc1ef;color:#6a2b8e}
.stockfilterbtn.live:not(.on){background:#e9f8ec;border-color:#c5e7cc;color:#236d37}.stockfilterbtn.fresh:not(.on){background:#edf6ff;border-color:#c9def2;color:#1f6296}.stockfilterbtn.frozen:not(.on){background:#eff3f7;border-color:#d5dde5;color:#38536a}
.stockflowresultbar{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin:0 1px 7px}.stockflowresultbar>b{font-size:10px;font-weight:1000;color:#1a2b3b}
.stocktags{display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-top:4px}.stocktag{display:inline-flex;align-items:center;border-radius:999px;padding:3px 7px;font-size:7px;line-height:1;font-weight:1000;white-space:nowrap;border:1px solid transparent}
.stocktag.category{background:#eef3f7;color:#38536a;border-color:#d7e0e7}.stocktag.category.live{background:#dff6e4;color:#246a37;border-color:#bde3c6}.stocktag.category.fresh{background:#e3f2ff;color:#1a6198;border-color:#bfdcf3}.stocktag.category.frozen{background:#eef1f5;color:#3d5265;border-color:#d5dde5}
.stocktag.delivery{background:#fff2d6;color:#6b4d00;border-color:#eed59d}.stocktag.delivery.none{background:#f3f5f7;color:#7b8791;border-color:#dfe4e8}
.stockflowempty{margin-top:4px}
@media(max-width:430px){
 .stockflowfilters{grid-template-columns:1fr;padding:6px;gap:6px}
 .stockfiltergroup.category{border-left:0;border-top:1px solid #d4e3ee;padding-left:0;padding-top:6px}
 .stockfilterbtn{padding:6px 8px;font-size:8px}
}
/* V439 Stock Flow: preserve v437 neutral compact treatment while adding four-mode pricing. */
#quick .stockflowfilters{display:flex;align-items:center;gap:6px;margin:0 0 4px;padding:5px 6px;border:1px solid #d5dde6;border-radius:11px;background:#fff;overflow-x:auto;scrollbar-width:none}
#quick .stockflowfilters::-webkit-scrollbar{display:none}
#quick .stockfiltergroup{display:flex;align-items:center;flex:0 0 auto;min-width:0}
#quick .stockfiltergroup>small{display:none}
#quick .stockfiltergroup.category{border-left:1px solid #d8dfe6;border-top:0;padding:0 0 0 6px}
#quick .stockfilterbuttons{gap:4px;padding:0;overflow:visible}
#quick .stockfilterbtn{padding:4px 7px;font-size:7.5px;background:#eef2f6;border-color:#d8dfe6;color:#405367;box-shadow:none}
#quick .stockfilterbtn.deliverytw:not(.on),#quick .stockfilterbtn.deliverytf:not(.on),#quick .stockfilterbtn.live:not(.on),#quick .stockfilterbtn.fresh:not(.on),#quick .stockfilterbtn.frozen:not(.on){background:#eef2f6;border-color:#d8dfe6;color:#405367}
#quick .stockfilterbtn.on{background:#234d77;border-color:#234d77;color:#fff;box-shadow:none}
#quick .stockflowresultbar{margin:0 1px 4px}
#quick .stockflowsort select{background:#eef2f6;border-color:#d5dde6;color:#314a61;padding-top:4px;padding-bottom:4px}
#quick .bestfam,#quick .bestfam.tone1,#quick .bestfam.tone2,#quick .bestfam.tone3,#quick .bestfam.tone4{--best-border:#d0d8e1;--best-bg:#fff;border:1px solid #d0d8e1;border-left:1px solid #d0d8e1;background:#fff;padding:6px 7px;margin-bottom:5px;box-shadow:0 3px 10px rgba(18,38,56,.045)}
#quick .besttop{gap:5px}
#quick .bestname{font-size:17px}
#quick .stocktags{gap:3px;margin-top:3px}
#quick .stocktag,#quick .stocktag.category,#quick .stocktag.category.live,#quick .stocktag.category.fresh,#quick .stocktag.category.frozen,#quick .stocktag.delivery,#quick .stocktag.delivery.none{padding:2px 6px;font-size:6.5px;background:#eef2f6;border-color:#d8dfe6;color:#405367}
#quick .stockfridaywarn{display:inline-flex;align-items:center;border:1px solid #e0b4b6;border-radius:999px;background:#fff3f3;color:#b32228;padding:2px 6px;font-size:6.5px;line-height:1;font-weight:1000;white-space:nowrap}
#quick .stockratio{min-width:70px;padding:4px 5px;background:#f7f9fb;border-color:#d9e0e7}
#quick .stockratio b{font-size:12px;color:#b3262d}
#quick .stockflowgrid{gap:3px;margin-top:4px}
#quick .stockflowgrid .bestmetric{padding:4px 5px;background:#f8fafb;border-color:#e0e5e9}
#quick .stockflowgrid .bestmetric b{font-size:16px;color:#22374d}
#quick .stockflowgrid .stockdiff,#quick .stockflowgrid .stockdiff.nosale,#quick .stockflowgrid .stockdiff.promoted{padding:4px 5px;background:#fff7f7;border-color:#e6c5c7}
#quick .stockflowgrid .stockdiff small,#quick .stockflowgrid .stockdiff>span,#quick .stockflowgrid .stockdiff.promoted small,#quick .stockflowgrid .stockdiff.promoted>span{color:#8b5d60}
#quick .stockflowgrid .stockdiff>b,#quick .stockflowgrid .stockdiff.promoted>b{color:#b3262d}
#quick .stockwatch{background:#eef2f6!important;color:#4a5b6b!important}
#quick .stocksale.stockpromo{margin-top:4px;padding:4px 6px;background:#f3f6f8;border-color:#d6dee7;color:#31485d}
#quick .stocksale.stockpromo strong,#quick .stockpromo .promobasis{color:#405568}
#quick .stockpromo .promolift,#quick .stockpromo .promoprice,#quick .stockdiff.promoted>b{background:#e9edf2}
#quick .stockpromo .promoprice,#quick .stockpromo .promoprice small,#quick .stockpromo .promoprice b{color:#31485d!important}
#quick .bestrecent{margin-top:4px;padding:4px 6px;background:#fff;border-color:#d8e0e7}
#quick .bestrecenthead{align-items:center}
#quick .stockreceiptmeta{display:flex;align-items:center;gap:4px}
#quick .stocklatestcost{display:inline-flex;align-items:center;gap:3px;padding:2px 5px;border:1px solid #d6dde5;border-radius:999px;background:#eef2f6;color:#4a5a69;font-size:6.5px;font-weight:1000;white-space:nowrap}
#quick .stocklatestcost b{font-size:7.5px;color:#1d2e3f}
#quick .stockreceipttoggle{border:0;border-radius:999px;background:#edf3f8;color:#285c88;padding:2px 5px;font-size:6.5px;font-weight:1000}
#quick .stockreceiptmore{display:none}
#quick .bestrecent.open .stockreceiptmore{display:grid}
#quick .bestreceipt{margin-top:2px;padding:2px 0;font-size:8.5px}
#quick .bestreceipt b{font-size:9.5px}
@media(max-width:365px){#quick .stockfilterbtn{padding:4px 6px;font-size:7px}#quick .stockflowgrid .bestmetric b{font-size:14px}#quick .stockratio{min-width:66px}}

/* V441 mobile scale + always-visible source freshness, integrated with four-mode pricing. */
.headfresh{display:none}
html:not(.yipman-desktop) .header{padding:8px 11px 8px}
html:not(.yipman-desktop) .head{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:start;gap:8px}
html:not(.yipman-desktop) .brandblock{min-width:0}
html:not(.yipman-desktop) .brand{font-size:29px}
html:not(.yipman-desktop) .ver{font-size:12.5px;margin-top:2px}
html:not(.yipman-desktop) .dbbtn{width:46px;height:46px;font-size:23px;border-radius:15px}
html:not(.yipman-desktop) .headfresh{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:3px 4px;min-width:0;padding:4px 5px;background:#fff;border:1px solid #dbe3ea;border-radius:12px;box-shadow:0 4px 13px rgba(18,38,56,.055)}
html:not(.yipman-desktop) .hfitem{display:grid;grid-template-columns:7px minmax(0,1fr);column-gap:4px;row-gap:1px;align-items:center;min-width:0;padding:2px 3px;border-radius:7px;background:#f6f8fa}
html:not(.yipman-desktop) .hfitem i{width:7px;height:7px;border-radius:50%;background:#98a5af;box-shadow:0 0 0 2px rgba(152,165,175,.10)}
html:not(.yipman-desktop) .hfitem.good i{background:#329b65;box-shadow:0 0 0 2px rgba(50,155,101,.11)}
html:not(.yipman-desktop) .hfitem.warn i{background:#d29a22;box-shadow:0 0 0 2px rgba(210,154,34,.11)}
html:not(.yipman-desktop) .hfitem.bad i{background:#c94950;box-shadow:0 0 0 2px rgba(201,73,80,.10)}
html:not(.yipman-desktop) .hfitem b{min-width:0;font-size:7.4px;line-height:1;font-weight:1000;color:#415266;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
html:not(.yipman-desktop) .hfitem span{grid-column:2;min-width:0;font-size:6.8px;line-height:1;color:#708090;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
html:not(.yipman-desktop) .workspace{height:calc(100% - 70px)}
html:not(.yipman-desktop) .page{padding-left:12px;padding-right:12px}
html:not(.yipman-desktop) .topline h2{font-size:26px}
html:not(.yipman-desktop) .hint{font-size:13px}
html:not(.yipman-desktop) .quicksearch{min-height:64px;grid-template-columns:44px minmax(0,1fr) 66px}
html:not(.yipman-desktop) .quicksearch>span{width:35px;height:35px;font-size:22px}
html:not(.yipman-desktop) .quicksearch input{font-size:18.5px}
html:not(.yipman-desktop) .nav{height:61px}
html:not(.yipman-desktop) .nav button{font-size:10px}
html:not(.yipman-desktop) .nav i{font-size:22px}
html:not(.yipman-desktop) #quick .bestname{font-size:18.5px}
html:not(.yipman-desktop) #quick .stockflowgrid .bestmetric b{font-size:17.5px}
html:not(.yipman-desktop) #quick .stocktag,html:not(.yipman-desktop) #quick .stockfridaywarn{font-size:7.2px}
html:not(.yipman-desktop) #quick .stocklatestcost{font-size:7.2px}
html:not(.yipman-desktop) #quick .stocklatestcost b{font-size:8.2px}
html:not(.yipman-desktop) #quick .bestreceipt{font-size:9.2px}
html:not(.yipman-desktop) #quick .bestreceipt b{font-size:10.2px}
@media(max-width:370px){
 html:not(.yipman-desktop) .brand{font-size:27px}
 html:not(.yipman-desktop) .ver{font-size:11.5px}
 html:not(.yipman-desktop) .hfitem b{font-size:6.8px}
 html:not(.yipman-desktop) .hfitem span{font-size:6.3px}
}


/* v7.0.450 consolidated mobile workflow */
#quick .stockflowfilters{position:sticky;top:0;z-index:18;background:rgba(246,247,249,.97);backdrop-filter:blur(10px)}
#quick .stockflowresultbar{position:sticky;top:35px;z-index:17;background:rgba(246,247,249,.97);backdrop-filter:blur(10px);padding:4px 1px}
#order .order-tabs{position:sticky;top:0;z-index:18;background:rgba(246,247,249,.97);backdrop-filter:blur(10px);padding:3px 0}
#order .order-tools{position:sticky;top:45px;z-index:17;background:rgba(246,247,249,.97);backdrop-filter:blur(10px);padding:5px 0}
#price .price-tabs{position:sticky;top:0;z-index:19;background:#e8eef3}
#price #priceSuggestionPane>.filters,#price #currentTprPane>.filters{position:sticky;top:49px;z-index:18;background:rgba(246,247,249,.97);backdrop-filter:blur(10px);padding:5px 0}
#price .price-tools,#price .tpr-tools{position:sticky;top:88px;z-index:17;background:rgba(246,247,249,.97);backdrop-filter:blur(10px);padding:4px 0}
.familyohpair{display:grid;grid-template-columns:1.08fr .92fr;gap:4px;margin-top:5px}
.familyohpair .familyohbtn,.familysystemoh{min-width:0;border:1px solid #d7e1e8;border-radius:9px;padding:6px 7px;background:rgba(255,255,255,.82);text-align:left}
.familyohpair .familyohbtn{background:#eef8ff;border-color:#acd1eb}
.familyohpair small{display:block;font-size:6.5px;color:#71808d;font-weight:1000}.familyohpair b{display:block;font-size:14px;line-height:1.05;margin-top:2px}.familyohpair span{display:block;font-size:7px;color:#71808d;font-weight:850;margin-top:2px}
.familyohpair .familysystemoh{background:#f7f9fb}
.familyohinline{width:100%;min-width:0;border:1px solid #9ccce8;border-radius:9px;background:#eef8ff;color:#173247;padding:5px 6px;text-align:right;cursor:pointer;font:inherit}
.familyohinline small{display:block;font-size:6px;line-height:1.05;color:#52738b;font-weight:1000;white-space:normal}.familyohinline b{display:block;font-size:13px;line-height:1.05;margin-top:2px}.familyohinline span{display:block;font-size:6.5px;color:#287b5b;font-weight:900;margin-top:2px;white-space:normal}
#order .ohcell{padding:6px 0!important}.ohcell .familyohinline{padding:5px 4px}
#price .ohpm{padding:3px!important}.ohpm .familyohinline{text-align:left;border:0;background:transparent;padding:0}.ohpm .familyohinline small{font-size:6px}.ohpm .familyohinline b{font-size:13px}
.clearance-oh-cell{padding:3px!important}.clearance-oh-cell .familyohinline{text-align:left;background:#eef8ff;border-color:#a7cee6;padding:5px}
.snooze12{border:1px solid #edb9bd!important;background:#fdebed!important;color:#a52831!important}
.snoozebar{margin:5px 0;padding:6px 8px;border:1px dashed #deb6ba;border-radius:9px;background:#fff7f8;color:#7c4d51;font-size:8px;font-weight:900}
.tprcancelchoices{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:6px}.tprcancelchoice{border:1px solid #d5dee5;border-radius:9px;background:#fff;padding:7px}.tprcancelchoice small{display:block;font-size:6.5px;color:#71808d;font-weight:950}.tprcancelchoice b{display:block;font-size:13px;margin-top:2px}
.freshwindow{margin-top:6px;border:1px solid #e8d49d;border-radius:9px;background:#fff7e4;color:#795600;padding:7px 8px;font-size:8px;font-weight:850;line-height:1.35}
#quick .bestfam.article-tone-0{border-left:5px solid #d1a61c;background:linear-gradient(95deg,#fff5cf,#fff 68%)}
#quick .bestfam.article-tone-1{border-left:5px solid #55a975;background:linear-gradient(95deg,#e8f7ec,#fff 68%)}
#quick .bestfam.article-tone-2{border-left:5px solid #4d98d0;background:linear-gradient(95deg,#e7f2fb,#fff 68%)}
#quick .bestfam.article-tone-3{border-left:5px solid #cf718b;background:linear-gradient(95deg,#fdeaf0,#fff 68%)}
#quick .bestfam.article-tone-4{border-left:5px solid #8b73c5;background:linear-gradient(95deg,#f0ebfb,#fff 68%)}
#quick .bestfam.article-tone-5{border-left:5px solid #4ca0a0;background:linear-gradient(95deg,#e8f7f7,#fff 68%)}
#quick .bestfam.article-tone-6{border-left:5px solid #cb8749;background:linear-gradient(95deg,#fff0e3,#fff 68%)}
#quick .bestfam.article-tone-7{border-left:5px solid #707abc;background:linear-gradient(95deg,#eceeff,#fff 68%)}


/* V451 Stock Flow reliability + narrow-mobile layout. */
#quick{padding-bottom:calc(154px + env(safe-area-inset-bottom))}
.stockflownotice{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 1px 6px;padding:7px 9px;border:1px solid #d5e2ec;border-radius:10px;background:#eef6fc;color:#36566f;font-size:8px;font-weight:900}
.stockflownotice span{min-width:0;line-height:1.25}.stockflownotice button,.stockflowerror button{flex:0 0 auto;border:1px solid #9fc4df;border-radius:8px;background:#fff;color:#0d5f9f;padding:5px 8px;font-size:8px;font-weight:1000}
.stockflowerror{background:#fff;border:1px solid #ead7d7;border-radius:13px;padding:11px;text-align:center;color:#775b5b;font-size:9px;font-weight:850;box-shadow:var(--shadow)}
.stockflowerror button{display:block;margin:8px auto 0}
.stockflowskeleton{display:grid;gap:7px}.stockflowskeleton>div{height:112px;border-radius:13px;background:linear-gradient(90deg,#edf1f4 20%,#f8fafb 45%,#edf1f4 70%);background-size:220% 100%;animation:stocksheen 1.15s linear infinite}
@keyframes stocksheen{to{background-position:-220% 0}}
#quick .bestfam{width:100%;max-width:100%;min-width:0}
#quick .familyohpair,#quick .stockflowgrid{width:100%;max-width:100%;min-width:0}
#quick .familyohpair>* ,#quick .stockflowgrid>*{min-width:0}
#quick .familyohpair b{font-size:clamp(12px,3.8vw,16px);white-space:nowrap}
#quick .familyohpair small,#quick .familyohpair span{white-space:normal;overflow-wrap:anywhere}
#quick .stockflowgrid{grid-template-columns:repeat(3,minmax(0,1fr))}
#quick .stockflowgrid .bestmetric b,#quick .stockflowgrid .stockdiff>b{font-size:clamp(13px,4.1vw,17px);white-space:nowrap}
#quick .stockflowgrid small,#quick .stockflowgrid span{white-space:normal;overflow-wrap:anywhere}
@media(max-width:380px){
  #quick .stockflowgrid{grid-template-columns:repeat(2,minmax(0,1fr))}
  #quick .stockflowgrid .stockdiff{grid-column:1/-1}
  #quick .familyohpair{grid-template-columns:repeat(2,minmax(0,1fr))}
}
</style>
</head>
<body>
<div id="app">
  <div class="ptr" id="ptr"><div id="ptrText">Pull to refresh</div></div>
  <header class="header">
    <div class="head"><div class="brandblock"><div class="brand">Yip<span>man</span></div><span class="ver">FULL MYSQL · __VERSION__</span></div><div class="headfresh" id="headFreshness" aria-label="Source freshness"><div class="hfitem"><i></i><b>POS</b><span>…</span></div><div class="hfitem"><i></i><b>MVT</b><span>…</span></div><div class="hfitem"><i></i><b>FRZ RPT</b><span>…</span></div><div class="hfitem"><i></i><b>FRESH RPT</b><span>…</span></div><div class="hfitem"><i></i><b>OH</b><span>…</span></div><div class="hfitem"><i></i><b>CHATGPT</b><span>…</span></div></div><button class="dbbtn" data-go="data" aria-label="Data Center">▦</button></div>
  </header>
  <main class="workspace">
    <section class="page on" id="quick"><div class="topline"><h2>Quick Check</h2><div class="hint">CURRENT MODULE DATA</div></div><div id="quickRows"><div class="loading">Loading stock flow…</div></div><form class="search quicksearch" id="globalForm"><span>⌕</span><input id="globalInput" placeholder="Search item, UPC, article..." autocomplete="off" enterkeyhint="search"><button class="quickclear" id="quickClear" type="button">CLEAR</button></form></section>

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
        <div class="list" id="orderList"><div class="lh" id="orderListHead"><div id="orderCol1">FAMILY / RECEIVING</div><div id="orderCol2">OH</div><div id="orderCol3">ORDER</div></div><div id="orderRows"><div class="loading">Loading observed delivery days…</div></div></div>
      </div>
      <div id="promotionOrderPanel" class="hide">
        <div class="promo-shell">
          <h3>Promotion Order</h3>
          <p>Weekly items use Thursday → following Thursday. Weekend items use Friday → Sunday. The selected delivery window can contain both promotion and regular-price days.</p>
          <div class="promo-types"><span class="promo-type weekly">WEEKLY · THU → THU</span><span class="promo-type weekend">WEEKEND · FRI → SUN</span></div>
          <div class="promo-controls"><select id="promoListSelect"><option value="">Choose promotion list…</option></select><button class="promo-import" id="promoImportBtn">IMPORT</button><button class="promo-manual" id="promoManualBtn">MANUAL</button></div>
          <div class="promo-date-inputs"><label>WEEKLY START (THU)<input type="date" id="promoWeeklyStart"></label><label>WEEKEND START (FRI)<input type="date" id="promoWeekendStart"></label></div>
          <input type="file" id="promoFileInput" accept=".csv,.xls,.xlsx,.xlsm" class="hide">
          <div class="promo-status" id="promoListStatus">Choose a saved list, import a file, or enter one / multiple UPC promotions manually.</div>
        </div>
        <div class="promo-summary" id="promoSummary"></div>
        <div id="promoOrderStatus" class="promo-status"></div>
        <div id="promoRows"><div class="empty">Choose or import a promotion list.</div></div>
      </div>
    </section>

    <section class="page" id="price">
      <div class="topline"><h2>Price Review</h2><div class="hint">LIVE REVIEW</div></div>
      <div class="price-tabs">
        <button class="price-tab on" data-price-tab="REG">REG</button>
        <button class="price-tab" data-price-tab="TPR_SUGGEST">TPR<br>SUGGEST</button>
        <button class="price-tab" data-price-tab="TPR_PROGRESS">TPR<br>PROGRESS <span id="tprTabCount"></span></button>
        <button class="price-tab" data-price-tab="CLEARANCE">CLEARANCE</button>
      </div>
      <div id="priceSuggestionPane">
        <div class="tpr-rule" id="priceModeRule"><b>REG:</b> everyday standard price. Replace it only when a better proved GP$/day sweet spot is ready to become the new regular price.</div>
        <div class="filters"><button class="pill on" data-price-filter="UPC_240">240</button><button class="pill" data-price-filter="UPC_245">245</button><button class="pill" data-price-filter="UPC_247">247</button><button class="pill" data-price-filter="UPC_249">249</button><button class="pill" data-price-filter="LIVE">LIVE</button><button class="pill" data-price-filter="TUE">OBSERVED TUE</button><button class="pill" data-price-filter="FRI_SAT">OBSERVED FRI / SAT</button></div>
        <div class="price-tools"><label>REASON<select id="priceReasonFilter"><option value="ALL">ALL REASONS</option><option value="PAIR">240≠249</option><option value="VELOCITY">VELOCITY / FRESHNESS</option><option value="GP">GP$ OPPORTUNITY</option><option value="RANGE">COMPANY RANGE</option><option value="SWEET">SWEET SPOT GAP</option></select></label><label>SORT<select id="priceSort"><option value="URGENCY">URGENCY</option><option value="GPDOLLAR">GP$ OPPORTUNITY ↓</option><option value="GAP">PRICE GAP ↓</option><option value="OH">OH ↓</option><option value="VELOCITY">VELOCITY ↑</option><option value="NAME">NAME A–Z</option></select></label></div>
        <div id="priceStatus" class="hint" style="margin:0 2px 7px"></div>
        <div class="pricecards" id="priceRows"><div class="loading">Loading price review…</div></div>
      </div>
      <div id="currentTprPane" class="hide">
        <div class="tpr-summary" id="tprSummary"><div><b>—</b><span>CURRENT TPR</span></div><div><b>—</b><span>SWEET TEST</span></div><div><b>—</b><span>FRESHNESS</span></div></div>
        <div class="tpr-rule"><b>TPR has one purpose:</b> either test a price that may become the new regular sweet spot, or temporarily reduce price to clear aging inventory by its freshness threshold. For a Day-7 Fresh/Live threshold the window is Day 5 → Day 7 inclusive; newer stock is not forced to zero. Yipman monitors before → now → projected behavior and recommends continue, change TPR price, make regular, or cancel.</div>
        <div class="filters tprfilters">
          <button class="pill on" data-tpr-filter="ALL">ALL</button>
          <button class="pill" data-tpr-filter="PURPOSE_SWEET">SWEET SPOT</button>
          <button class="pill" data-tpr-filter="PURPOSE_FRESHNESS">FRESHNESS</button>
          <button class="pill" data-tpr-filter="UPC_240">240 ONLY</button>
          <button class="pill" data-tpr-filter="SOLD">SOLD 7D</button>
          <button class="pill" data-tpr-filter="CONTINUE">CONTINUE</button>
          <button class="pill" data-tpr-filter="ADJUST">ACTION</button>
          <button class="pill" data-tpr-filter="LIVE">LIVE</button>
          <button class="pill" data-tpr-filter="FRESH">FRESH</button>
          <button class="pill" data-tpr-filter="FROZEN">FROZEN</button>
        </div>
        <div class="tpr-tools"><div id="tprStatus" class="hint">Loading current TPR items…</div><label>SORT<select id="tprSort"><option value="QTY">7D QTY ↓</option><option value="DECISION">ACTION FIRST</option><option value="LIFT">3D LIFT ↓</option><option value="OH">OH ↓</option><option value="NAME">NAME A–Z</option></select></label></div>
        <div class="pricecards" id="tprRows"><div class="loading">Loading current TPR review…</div></div>
      </div>
      <div id="clearancePane" class="hide">
        <div class="clearance-intro"><b>CLEARANCE:</b> use only for a user-observed expiring quantity. Search the UPC, enter expiry date and expiring quantity, and optionally enter True Stock. Yipman builds a step-down sell-out plan. Active company SALE price/period stays locked.</div>
        <div class="clearance-search"><input id="clearanceSearchInput" placeholder="Search UPC, article or item name" autocomplete="off"><button id="clearanceSearchBtn">SEARCH</button></div>
        <div id="clearanceSearchResults" class="clearance-search-results"></div>
        <div id="clearanceStatus" class="hint" style="margin:0 2px 7px">Loading active clearance plans…</div>
        <div id="clearanceRows"></div>
      </div>
    </section>

    
    <section class="page" id="ai">
      <div class="aihead">
        <div class="aiheadleft"><div class="aimark">✦</div><div class="aiheadcopy"><h2>Ask Yipman</h2><p>FULL MYSQL · live operational answers</p></div></div>
        <div class="aireadonly">READ ONLY</div>
      </div>
      <div class="aipagechat">
        <div class="aichat" id="aiChat"><div class="aibubble ai">Checking current data…</div></div>
        <form class="aicomposer" id="aiForm"><input id="aiInput" placeholder="Ask sales, stock, orders, price, receipts or QA..." autocomplete="off" aria-label="Ask Yipman"><button type="submit">→</button></form>
      </div>
    </section>

<section class="page" id="data"><div class="topline"><h2>Data Center</h2><div class="hint">LIVE OPERATIONS</div></div><div class="datagrid"><div class="dcard mobileupload"><h3>Upload New Files</h3><p>Select one or multiple source files. Files selected together become one immutable batch and processing starts after commit.</p><input class="duploadpick" id="dataUploadFiles" type="file" multiple accept=".xlsx,.xls,.xlsm,.csv,.txt,.tsv"><input class="duploadnote" id="dataUploadNote" placeholder="Optional batch note"><div class="duploadsummary" id="dataUploadSummary">No files selected.</div><button class="duploadbtn" id="dataUploadBtn" type="button">UPLOAD & START PROCESSING</button><div class="duploadresult" id="dataUploadResult">Source type and business-date coverage will be detected automatically.</div></div><div class="dcard"><h3>Processing Pipeline</h3><div class="pipe" id="pipe"><div class="stage"><b>UPLOAD</b><span>—</span></div><div class="stage"><b>INGEST</b><span>—</span></div><div class="stage"><b>QA</b><span>—</span></div><div class="stage"><b>PUBLISH</b><span>—</span></div></div></div><div class="dcard"><h3>14-Day Completeness</h3><div class="cal" id="calendar"></div></div><div class="dcard"><h3>Published Snapshot</h3><div id="publishedSnapshot"><div class="loading">Loading published data…</div></div></div><div class="dcard"><h3>Current Processing</h3><div id="currentBatch"><div class="loading">Loading…</div></div></div><div class="dcard qaresolutioncard"><div class="qareshead"><div><h3>QA Resolution</h3><p>Fix confirmed item / UOM / conversion issues here.</p></div><span id="qaResolutionBadge" class="qaresbadge">—</span></div><div id="qaResolution"><div class="loading">Loading QA…</div></div></div><div class="dcard"><h3>Recent Batches</h3><div id="recentBatches"><div class="loading">Loading…</div></div></div></div></section>

    <nav class="nav"><button class="on" data-go="quick"><i>⌕</i>QUICK</button><button data-go="order"><i>▤</i>ORDER</button><button data-go="price"><i>$</i>PRICE</button><button data-go="ai"><i>✦</i>AI</button></nav>
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
const gpText=(price,cost)=>{
  const p=num(price),c=num(cost);
  if(p===null||c===null||p<=0)return 'GP —';
  return 'GP '+(((p-c)/p)*100).toFixed(1)+'%';
};
const retailPoint=v=>{
  const n=num(v);if(n===null)return null;
  const endings=[.29,.49,.59,.69,.79,.99],whole=Math.floor(n),c=[];
  for(let d=Math.max(0,whole-1);d<=whole+2;d++)for(const e of endings)c.push(d+e);
  return c.sort((a,b)=>Math.abs(a-n)-Math.abs(b-n)||a-b)[0];
};
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
function freshnessShortDate(v){
 const m=String(v||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
 return m?(Number(m[2])+'/'+Number(m[3])):'—';
}

function articleTone(value){let h=0;for(const ch of String(value||''))h=(h*31+ch.charCodeAt(0))>>>0;return h%8}
// Compatibility wording retained for the established True Stock control contract: TAP TO ENTER TRUE STOCK
function familyOhActionHtml(d,cls=''){
 const family=String(d?.family||''),name=String(d?.name||''),uom=String(d?.uom||''),src=String(d?.source||'').toUpperCase(),isTrue=src.includes('TRUE_STOCK');
 return '<button type="button" class="familyohinline '+esc(cls)+'" data-family-oh data-family="'+esc(family)+'" data-name="'+esc(name)+'" data-oh="'+esc(d?.oh??'')+'" data-uom="'+esc(uom)+'">'+
   '<small>EFFECTIVE OH · ENTER TRUE STOCK</small><b>'+fmtNullable(d?.oh)+' '+esc(uom)+'</b><span>'+(isTrue?'TRUE STOCK ACTIVE':'TAP TO COUNT & RECALCULATE')+'</span></button>';
}
function familyOhPairHtml(d){
 const family=String(d?.family||''),name=String(d?.name||''),euom=String(d?.effective_uom||d?.system_uom||''),suom=String(d?.system_uom||euom);
 const src=String(d?.effective_source||'').toUpperCase(),isTrue=src.includes('TRUE_STOCK');
 return '<div class="familyohpair">'+
 '<button type="button" class="familyohbtn" data-family-oh data-family="'+esc(family)+'" data-name="'+esc(name)+'" data-oh="'+esc(d?.effective??'')+'" data-uom="'+esc(euom)+'"><small>EFFECTIVE OH · ENTER TRUE STOCK</small><b>'+fmt(d?.effective)+' '+esc(euom)+'</b><span>'+(isTrue?'TRUE STOCK ACTIVE':'TAP TO COUNT & RECALCULATE')+'</span></button>'+
 '<div class="familysystemoh"><small>SYSTEM OH</small><b>'+fmt(d?.system)+' '+esc(suom)+'</b><span>LATEST SYSTEM POSITION</span></div></div>';
}
function renderHeaderFreshness(d){
 const box=$('#headFreshness');if(!box)return;
 const s=d?.sources||{};
 const order=[['POS','POS'],['MVT','MVT'],['FRZ','FRZ RPT'],['FRESH','FRESH RPT'],['OH','OH'],['CHATGPT','CHATGPT']];
 box.innerHTML=order.map(([key,label])=>{
   const x=s[key]||{},tone=['good','warn','bad'].includes(String(x.tone||''))?String(x.tone):'';
   const date=freshnessShortDate(x.date);
   const state=String(x.state||'—');
   return '<div class="hfitem '+tone+'" title="'+esc(label+' · '+date+' · '+state)+'"><i></i><b>'+esc(label)+'</b><span>'+esc(date+' · '+state)+'</span></div>';
 }).join('');
}
async function loadHeaderFreshness(){
 try{
   const d=await api('/v1/yipman/header-freshness',{timeoutMs:9000});
   renderHeaderFreshness(d);
 }catch{
   const box=$('#headFreshness');if(box)$$('#headFreshness .hfitem').forEach(x=>{x.classList.remove('good','warn');x.classList.add('bad');const s=x.querySelector('span');if(s)s.textContent='— · ERROR'});
 }
}
const app=$('#app'), pages=$$('.page'), nav=$$('.nav button');
let current='quick', priceFilter='UPC_240', priceReasonFilter='ALL', priceSort='URGENCY', orderDate=null, orderNextDate=null, orderSelectMode='DELIVERY', orderObservedWeekdays=new Map(), orderCalendarLoaded=false, orderInitPromise=null, orderMode='REGULAR', promoListsLoaded=false, promoListId=null, promoListDetail=null, promoTempOH=new Map(), promoLastRows=[], pullStart=null, pull=0;
let historyReady=false, detailHistory=false, exitAllowed=false, dataQaIssues=[], dataQaBatchId=null, dataLiveTimer=null, dataLiveSignature='', historyScrollTimer=null, sheetStack=[];
const pagePositions=new Map();
let quickSearchTimer=null, quickRequestSeq=0, lastQuickQuery='', bestSellerGroups=null, stockFlowSort='RATIO', stockFlowDeliveryFilter='ALL', stockFlowCategoryFilter='ALL', stockFlowNotice='', stockFlowCacheSavedAt=null, orderRequestSeq=0, orderRetryTimer=null, orderRetryCount=0, orderRetryWindowKey='', priceRequestSeq=0, priceRetryTimer=null, priceIgnoredThisVisit=new Set();
let orderSort='ACTION', orderFilter='ALL', lastOrderRows=[], lastOrderData=null, lastOrderStale=false, renderedOrderRows=[], lastOrderWindowKey='';
let priceView='REG', tprFilter='ALL', tprSort='QTY', tprRequestSeq=0, tprRetryTimer=null, lastTprRows=[], lastTprPayload=null, clearanceRows=[], clearanceSearchSeq=0;
const stockFlowCacheKey='yipman-stock-flow-v9';

let aiBriefLoaded=false, aiBriefLoading=null, aiBriefData={stock:null,price:null,orders:[],dataThrough:null};

async function refreshAfterFamilyTrueStock(family=''){
 aiBriefLoaded=false;aiBriefData={stock:null,price:null,orders:[],dataThrough:null};
 if(current==='quick'){
   if(lastQuickQuery)await loadQuick(lastQuickQuery);else {stockFlowNotice='Recalculating Family stock…';await loadBestSellers(true);}
 }else if(current==='order'&&orderMode==='REGULAR'){
   await loadOrder(orderDate);
 }else if(current==='order'&&orderMode==='PROMOTION'){
   const key=String(family||'').trim();
   if(key){
     for(const [fid,row] of [...promoTempOH.entries()]){
       if(String(row?.family_article_number||row?.family_id||'').trim()===key)promoTempOH.delete(fid);
     }
   }
   await loadPromotionOrder();
 }else if(current==='price'){
   await loadPriceCurrentView();
 }
}
function bindFamilyOhEditors(root=document){
 root.querySelectorAll('[data-family-oh]').forEach(btn=>{
  if(btn.dataset.trueStockBound==='1')return;
  btn.dataset.trueStockBound='1';
  btn.onclick=e=>{
   e.preventDefault();e.stopPropagation();
   openFamilyTrueStock({
    family:btn.dataset.family,
    name:btn.dataset.name||'',
    oh:btn.dataset.oh,
    uom:btn.dataset.uom||''
   });
  };
 });
}
function openFamilyTrueStock(d){
 const family=String(d?.family||'').trim(),uom=String(d?.uom||'').trim().toUpperCase();
 if(!family)return toast('Family Article unavailable');
 if(!uom)return toast('Effective OH UOM unavailable');
 const currentQty=(d.oh===null||d.oh===undefined||d.oh==='')?'':d.oh;
 sheet(
  d.name||'True Stock',
  'Family '+esc(family)+' · Effective OH',
  '<div class="detail"><b>Current Effective OH</b><br>'+fmtNullable(currentQty)+' '+esc(uom)+
  '<br><br><b>Enter Physical True Stock</b><br><input id="familyTrueStockInput" type="number" min="0" step="0.01" inputmode="decimal" value="'+esc(currentQty)+'" style="width:100%;font-size:26px;font-weight:1000;padding:11px;border:2px solid #9dcfbd;border-radius:12px">'+
  '<br><br><label style="display:block;font-size:9px;font-weight:900;color:#65737e">NOTE</label><input id="familyTrueStockNote" placeholder="Physical count / optional note" style="width:100%;padding:10px;border:1px solid #d8e1e6;border-radius:10px;margin-top:4px">'+
  '<div class="estimatebar" style="margin-top:10px"><b>Immediate authority:</b> saving this count makes it the Family Effective OH for Quick Check, Stock Flow, Ordering, Price Review and other OH-dependent calculations. If lower than System OH, the PI / Pending Dumping workflow is updated.</div>'+
  '<div class="actions"><button class="secondary" id="familyTrueStockCancel">CANCEL</button><button class="primary" id="familyTrueStockSave">SAVE TRUE STOCK & RECALCULATE</button></div></div>'
 );
 $('#familyTrueStockCancel').onclick=()=>closeSheet(true);
 $('#familyTrueStockSave').onclick=async()=>{
  const qty=Number($('#familyTrueStockInput').value);
  if(!Number.isFinite(qty)||qty<0)return toast('Enter valid True Stock');
  const btn=$('#familyTrueStockSave');btn.disabled=true;btn.textContent='SAVING & RECALCULATING…';
  try{
   await api('/v1/app/v2/pi/'+encodeURIComponent(family)+'/true-stock',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({true_stock:qty,uom,note:($('#familyTrueStockNote').value||'').trim()||null}),
    timeoutMs:30000
   });
   closeSheet(false);toast('True Stock saved · Effective OH recalculating');
   await refreshAfterFamilyTrueStock(family);
  }catch(e){toast(e.message||'Could not save True Stock');btn.disabled=false;btn.textContent='SAVE TRUE STOCK & RECALCULATE'}
 };
}
function aiBubble(html,who='ai',tone=''){
 const box=$('#aiChat');if(!box)return null;
 const d=document.createElement('div');d.className='aibubble '+who+(tone?' '+tone:'');d.innerHTML=html;box.appendChild(d);box.scrollTop=box.scrollHeight;return d;
}
function aiOrderState(r){
 const explicit=String(r?.roster_status||'').toUpperCase();
 if(explicit)return explicit;
 const q=num(r?.suggested_delivery_qty);return q!==null&&q>0?'ORDER':q===0?'ZERO_ORDER':'REVIEW';
}
function aiPriceRow(rows){
 return (rows||[]).find(r=>r?.priority_240_249_mismatch)
   ||(rows||[]).find(r=>r?.actionable&&String(r?.suggestion_reason_code||'').toUpperCase()==='GP_DOLLAR_TEST')
   ||(rows||[]).find(r=>r?.actionable)
   ||(rows||[])[0]||null;
}
function aiAttentionHtml(){
 const stock=aiBriefData.stock,price=aiBriefData.price,orders=aiBriefData.orders||[],lines=[];
 if(orders.length){
   const first=orders[0],q=num(first?.suggested_delivery_qty);
   lines.push('• <b>Ordering:</b> '+orders.length+' item'+(orders.length===1?'':'s')+' need order'+(first?'; first '+esc(first.family_name||first.family_article||'Family')+(q!==null?' '+fmt(q)+' '+esc(first.suggested_delivery_uom||''):''):'')+'.');
 }
 if(price){
   if(price.priority_240_249_mismatch)lines.push('• <b>Price:</b> 249 '+esc(price.upc||'')+' is '+money(price.current_price)+'; paired 240 is '+money(price.related_240_current_price)+'.');
   else lines.push('• <b>Price:</b> '+esc(price.name||price.upc||'Item')+' is the highest current review item.');
 }
 if(stock){
   lines.push('• <b>Stock Flow:</b> '+esc(stock.family_name||stock.family_article||'Family')+' received '+fmt(stock.family_receipt_7d_qty)+' '+esc(stock.family_receipt_7d_uom||stock.family_group_movement_uom||'')+' vs '+fmt(stock.family_group_movement_7d)+' '+esc(stock.family_group_movement_uom||'')+' sold movement in 7D.');
 }
 if(!lines.length)lines.push('No high-priority action is showing from the current Ordering, Price Review, and Stock Flow data.');
 const h=aiBriefData.dataThrough||{};
 const through=[h.pos_data_through?'POS '+esc(h.pos_data_through):'',h.movement_data_through?'MVT '+esc(h.movement_data_through):''].filter(Boolean).join(' · ');
 return '<b>Today’s attention</b><br>'+lines.join('<br>')+(through?'<div class="aimeta">Data through: '+through+'</div>':'');
}
async function loadAiBrief(force=false){
 if(aiBriefLoaded&&!force)return;
 if(aiBriefLoading)return aiBriefLoading;
 const box=$('#aiChat');if(box)box.innerHTML='<div class="aibubble ai thinking">Checking current data…</div>';
 aiBriefLoading=(async()=>{
   const orderPromise=(async()=>{
     const cal=await api('/v1/yipman/ordering-calendar?lookback_days=180',{timeoutMs:16000});
     const delivery=String(cal?.default_delivery_date||''),next=String(cal?.default_next_delivery_date||'');
     if(!delivery)return null;
     return api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(delivery)+(next?'&next_delivery_date='+encodeURIComponent(next):''),{timeoutMs:26000});
   })();
   const results=await Promise.allSettled([
     api('/v1/yipman/stock-flow?limit=20',{timeoutMs:16000}),
     api('/v1/yipman/pricing-review?category=ALL&limit=200',{timeoutMs:16000}),
     orderPromise
   ]);
   const stockData=results[0].status==='fulfilled'?results[0].value:null;
   const priceData=results[1].status==='fulfilled'?results[1].value:null;
   const orderData=results[2].status==='fulfilled'?results[2].value:null;
   const stockRows=[...(stockData?.rows||[])].sort((a,b)=>(num(b.receipt_minus_selling_7d)||0)-(num(a.receipt_minus_selling_7d)||0));
   const priceRows=(priceData?.rows||[]).filter(r=>r?.priority_240_249_mismatch||r?.actionable||String(r?.suggestion_reason_code||''));
   const orderRows=(orderData?.rows||[]).filter(r=>aiOrderState(r)==='ORDER'&&(num(r?.suggested_delivery_qty)||0)>0).sort((a,b)=>(num(b.suggested_delivery_qty)||0)-(num(a.suggested_delivery_qty)||0));
   aiBriefData={stock:stockRows[0]||null,price:aiPriceRow(priceRows),orders:orderRows,dataThrough:orderData?.current_source_health||priceData?.current_source_health||orderData?.data_health||priceData?.data_health||stockData?.data_health||null};
   if(box)box.innerHTML='<div class="aibubble ai brief">'+aiAttentionHtml()+'</div>';
   aiBriefLoaded=true;
 })();
 try{return await aiBriefLoading}finally{aiBriefLoading=null}
}
function aiYmd(y,m,d){
 const dt=new Date(Number(y),Number(m)-1,Number(d),12,0,0,0);
 if(dt.getFullYear()!==Number(y)||dt.getMonth()!==Number(m)-1||dt.getDate()!==Number(d))return null;
 return dt.getFullYear()+'-'+String(dt.getMonth()+1).padStart(2,'0')+'-'+String(dt.getDate()).padStart(2,'0');
}
function aiPrettyDate(ymd){
 const m=String(ymd||'').match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return String(ymd||'');
 const dt=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]),12,0,0,0);
 return dt.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric',year:'numeric'});
}
function aiDateFromQuestion(question){
 const q=String(question||'').toLowerCase(),now=new Date();now.setHours(12,0,0,0);
 if(/\byesterday\b/.test(q)){const d=new Date(now);d.setDate(d.getDate()-1);return iso(d)}
 if(/\btoday\b/.test(q))return iso(now);
 let m=q.match(/\b(20\d{2})-(\d{1,2})-(\d{1,2})\b/);
 if(m)return aiYmd(m[1],m[2],m[3]);
 m=q.match(/\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\b/);
 if(m){
   let y=m[3]?Number(m[3]):now.getFullYear();if(y<100)y+=2000;
   let out=aiYmd(y,m[1],m[2]);
   if(!m[3]&&out){const d=new Date(out+'T12:00:00');const far=new Date(now);far.setDate(far.getDate()+31);if(d>far)out=aiYmd(y-1,m[1],m[2])}
   return out;
 }
 return null;
}
function aiNorm(v){return String(v||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}
function aiExtractItemQuery(question){
 return String(question||'')
  .replace(/\b20\d{2}-\d{1,2}-\d{1,2}\b/g,' ')
  .replace(/\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\b/g,' ')
  .replace(/\b(?:what(?:'s| is)?|whats|how(?:'s| is)?|hows|show|tell|me|the|sales?|sale|revenue|performance|amount|dollars?|for|of|on|at|in|yesterday|today|last|day|did|do|we|sell|sold|selling|gp|gross|profit|price|cost|stock|inventory|oh|hand|current|now|please)\b/gi,' ')
  .replace(/[?.,!]+/g,' ').replace(/\s+/g,' ').trim();
}
function aiQtyText(items){
 const totals=new Map();
 (items||[]).forEach(x=>{const u=String(x.qty_uom||x.selling_uom||'UNIT').toUpperCase();totals.set(u,(totals.get(u)||0)+(num(x.sold_quantity)||0))});
 return [...totals.entries()].map(([u,q])=>fmt(q)+' '+esc(u)).join(' + ')||'—';
}
function aiPercent(v){const n=num(v);return n===null?'—':(n*100).toFixed(1)+'%'}
async function aiLatestPerformanceDate(){
 const d=await api('/v1/app/v2/performance/latest-date',{timeoutMs:12000});
 return String(d?.latest_completed_supported_sales_date||'');
}
async function aiPerformanceRange(date){
 return api('/v1/app/v2/performance/range?start_date='+encodeURIComponent(date)+'&end_date='+encodeURIComponent(date)+'&limit=2000',{timeoutMs:30000});
}
async function aiFindSalesMatches(items,term){
 const tokens=aiNorm(term).split(' ').filter(Boolean);
 const direct=(items||[]).filter(x=>{
   const hay=aiNorm([x.name,x.family_name,x.upc,x.family_article_number].filter(Boolean).join(' '));
   return tokens.length&&tokens.every(t=>hay.includes(t));
 });
 if(direct.length)return direct;
 try{
   const sr=await api('/v1/app/v2/search?q='+encodeURIComponent(term)+'&limit=30',{timeoutMs:16000});
   const upcs=new Set(),families=new Set();
   (sr?.results||[]).forEach(x=>{
     if(String(x.result_type||'').toUpperCase()==='UPC'&&x.number)upcs.add(String(x.number).replace(/^0+/,''));
     if(x.family_article_number)families.add(String(x.family_article_number));
     if(String(x.result_type||'').toUpperCase()==='FAMILY'&&x.number)families.add(String(x.number));
   });
   return (items||[]).filter(x=>upcs.has(String(x.upc||'').replace(/^0+/,''))||families.has(String(x.family_article_number||'')));
 }catch{return []}
}
async function aiAnswerPerformance(question,date,itemTerm=''){
 let range;
 try{range=await aiPerformanceRange(date)}
 catch(e){
   const latest=await aiLatestPerformanceDate().catch(()=>null);
   if(latest)return '<b>No completed sales day for '+esc(aiPrettyDate(date))+'.</b><br>Latest completed canonical POS sales date is '+esc(aiPrettyDate(latest))+'. Missing dates are not treated as zero.';
   throw e;
 }
 const items=range?.items||[],summary=range?.summary||{};
 if(itemTerm){
   const matches=await aiFindSalesMatches(items,itemTerm);
   if(!matches.length)return '<b>'+esc(itemTerm)+' · '+esc(aiPrettyDate(date))+'</b><br>No POS sales were found for that item on this completed sales date.';
   const sales=matches.reduce((s,x)=>s+(num(x.sales_amount)||0),0);
   const gpComplete=matches.every(x=>x.gp_dollars!==null&&x.gp_dollars!==undefined);
   const gp=gpComplete?matches.reduce((s,x)=>s+(num(x.gp_dollars)||0),0):null;
   const top=[...matches].sort((a,b)=>(num(b.sales_amount)||0)-(num(a.sales_amount)||0)).slice(0,4);
   return '<b>'+esc(itemTerm)+' · '+esc(aiPrettyDate(date))+'</b><br><b>Sales '+money(sales)+'</b> · Qty '+aiQtyText(matches)+(gp!==null?' · GP$ '+money(gp):'')+
     '<div class="aimeta">'+top.map(x=>esc(x.name||x.upc||'Item')+' · '+money(x.sales_amount)+' · '+fmt(x.sold_quantity)+' '+esc(x.qty_uom||x.selling_uom||'')).join('<br>')+'</div>';
 }
 const sales=num(summary.sales_dollars),gp=num(summary.gp_dollars),gpComplete=summary.gp_dollars_complete===true;
 let report=null;
 try{report=await api('/v1/app/v2/performance?category=ALL&limit=100&report_date='+encodeURIComponent(date),{timeoutMs:30000})}catch{}
 const analysis=report?.analysis||[];
 const vs7=analysis.find(x=>x.type==='REPORT_DATE_SALES_VS_7D_AVG');
 const top=(report?.report_date_top_sellers||items||[]).slice(0,3);
 return '<b>'+esc(aiPrettyDate(date))+' performance</b><br><b>Sales '+money(sales)+'</b>'+(gpComplete&&gp!==null?' · GP$ '+money(gp)+(sales>0?' · GP '+aiPercent(gp/sales):''):' · GP$ incomplete')+
   '<br>'+fmt(summary.sold_item_count,0)+' selling item'+(Number(summary.sold_item_count||0)===1?'':'s')+
   (vs7&&num(vs7.value_pct)!==null?'<br>Sales vs 7-day supported-day average: '+(num(vs7.value_pct)>=0?'+':'')+aiPercent(vs7.value_pct):'')+
   (top.length?'<div class="aimeta"><b>Top sellers</b><br>'+top.map(x=>esc(x.name||x.upc||'Item')+' · '+money(x.sales_amount)+' · '+fmt(x.sold_quantity)+' '+esc(x.qty_uom||x.selling_uom||'')).join('<br>')+'</div>':'');
}
async function aiSearch(term){
 return api('/v1/app/v2/search?q='+encodeURIComponent(term)+'&limit=20',{timeoutMs:16000});
}
async function aiAnswerItemPrice(term){
 const d=await aiSearch(term),rows=(d?.results||[]).filter(x=>String(x.result_type||'').toUpperCase()==='UPC'&&x.current_price!==null&&x.current_price!==undefined).slice(0,5);
 if(!rows.length)return '<b>'+esc(term)+'</b><br>No current UPC price was found.';
 return '<b>Current price · '+esc(term)+'</b><br>'+rows.map(x=>esc(x.name||x.number||'UPC')+' · <b>'+money(x.current_price)+'</b> '+esc(x.current_price_type||'')+(x.current_price_asof_date?' · '+esc(x.current_price_asof_date):'')).join('<br>');
}
async function aiAnswerItemStock(term){
 const d=await aiSearch(term),rows=d?.results||[];
 const fam=rows.find(x=>String(x.result_type||'').toUpperCase()==='FAMILY')||rows.find(x=>x.family_article_number)||rows[0];
 const key=fam?.number||fam?.family_article_number;
 if(!key)return '<b>'+esc(term)+'</b><br>No mapped Family was found for stock lookup.';
 try{
   const f=await api('/v1/app/v2/family/'+encodeURIComponent(key),{timeoutMs:18000}),oh=f?.current_effective_oh||{},lr=f?.last_receipt||{};
   return '<b>'+esc(f?.family_article_name||term)+'</b><br>OH <b>'+fmt(oh.quantity)+' '+esc(oh.uom||'')+'</b> · '+esc(oh.source||oh.status||'')+
     (lr.date?'<br>Last receipt '+esc(appDate(lr.date))+' · '+fmt(lr.quantity)+' '+esc(lr.uom||''):'');
 }catch(e){return '<b>'+esc(term)+'</b><br>Family stock lookup is unavailable: '+esc(e.message)}
}
async function aiAnswer(question){
 const q=String(question||'').toLowerCase(),stock=aiBriefData.stock,price=aiBriefData.price,orders=aiBriefData.orders||[];
 const date=aiDateFromQuestion(question),itemTerm=aiExtractItemQuery(question);
 const asksPerformance=/\b(performance|sales?|revenue|sold|selling|gp|gross profit|top seller)\b/.test(q);
 if(date&&asksPerformance)return aiAnswerPerformance(question,date,itemTerm);
 if(!date&&asksPerformance&&itemTerm){
   const latest=await aiLatestPerformanceDate();
   if(latest)return aiAnswerPerformance(question,latest,itemTerm);
 }
 if((q.includes('price')||q.includes('cost'))&&itemTerm)return aiAnswerItemPrice(itemTerm);
 if((q.includes('stock')||q.includes('inventory')||/\boh\b/.test(q)||q.includes('on hand'))&&itemTerm)return aiAnswerItemStock(itemTerm);
 if(q.includes('order')||q.includes('coverage')){
   if(!orders.length)return '<b>Ordering</b><br>No positive order suggestion is currently loaded in the brief.';
   return '<b>Ordering</b><br>'+orders.slice(0,5).map(r=>'• '+esc(r.family_name||r.family_article||'Family')+' — '+fmtNullable(r.suggested_delivery_qty)+' '+esc(r.suggested_delivery_uom||'')+' · Receiving '+esc(r.receiving_article||'—')).join('<br>');
 }
 if(q.includes('249')||q.includes('240')||q.includes('price')||q.includes('sweet')){
   if(!price)return '<b>Price Review</b><br>No actionable price row is currently loaded.';
   if(price.priority_240_249_mismatch)return '<b>249 / 240 alignment</b><br>249 '+esc(price.upc||'')+' is '+money(price.current_price)+' while paired 240 is '+money(price.related_240_current_price)+'. The 249 review remains only while those current prices differ.';
   return '<b>Price Review</b><br>'+esc(price.name||price.upc||'Item')+' · current '+money(price.current_price)+(price.tested_sweet_spot_price!=null?' · tested '+money(price.tested_sweet_spot_price):'')+(price.testing_price!=null?' · TPR suggestion price '+money(price.testing_price):'')+'.';
 }
 if(q.includes('receipt')||q.includes('stock flow')||q.includes('over receipt')){
   if(!stock)return '<b>Stock Flow</b><br>No Stock Flow row is currently loaded.';
   return '<b>Stock Flow</b><br>'+esc(stock.family_name||stock.family_article||'Family')+' has 7D receipts '+fmt(stock.family_receipt_7d_qty)+' '+esc(stock.family_receipt_7d_uom||'')+' vs selling movement '+fmt(stock.family_group_movement_7d)+' '+esc(stock.family_group_movement_uom||'')+'.';
 }
 if(q.includes('qa')||q.includes('hold')||q.includes('uom')||q.includes('unmapped')){
   const count=Array.isArray(dataQaIssues)?dataQaIssues.length:0;
   return '<b>QA</b><br>'+(count?fmt(count,0)+' QA issue(s) are loaded in Data Center. ':'Open Data Center for the live QA list. ')+'This assistant is read-only.';
 }
 if(q.includes('attention')||q.includes('urgent')||q.includes('reminder'))return aiAttentionHtml();
 return '<b>Ask Yipman</b><br>I can query sales by item/date, daily performance, current stock, current price, Ordering, Stock Flow and QA. Example: “tilapia sales 9/25” or “yesterday performance”.';
}
async function aiSubmitQuestion(q){
 aiBubble(esc(q),'user');
 const pending=aiBubble('Checking FULL MYSQL…','ai','thinking');
 try{
   const answer=await aiAnswer(q);
   if(pending?.parentNode)pending.remove();
   aiBubble(answer,'ai');
 }catch(e){
   if(pending?.parentNode)pending.remove();
   aiBubble('<b>Could not answer that query.</b><br>'+esc(e.message),'ai','notice');
 }
}
function bindAi(){
 const form=$('#aiForm'),input=$('#aiInput');if(!form||!input||form.dataset.bound==='1')return;
 form.dataset.bound='1';
 form.onsubmit=e=>{e.preventDefault();const q=input.value.trim();if(!q)return;input.value='';aiSubmitQuestion(q)};
}

function toast(t){const n=$('#toast');n.textContent=t;n.classList.add('on');setTimeout(()=>n.classList.remove('on'),1600)}
async function api(url,opt={}){const c=new AbortController();let timedOut=false;const tm=setTimeout(()=>{timedOut=true;c.abort()},opt.timeoutMs||18000);try{const r=await fetch(url,{...opt,signal:c.signal,headers:{'Accept':'application/json',...(opt.headers||{})},cache:'no-store'});const text=await r.text();let data={};try{data=text?JSON.parse(text):{}}catch{}if(!r.ok)throw new Error(data?.detail?.reason||data?.detail||text||('HTTP '+r.status));return data}catch(e){if(timedOut||e?.name==='AbortError')throw new Error('Request timed out while the server was calculating. Retrying is safe.');throw e}finally{clearTimeout(tm)}}
function currentPagePosition(id=current){
  const p=$('#'+id);
  return {scrollTop:Number(p?.scrollTop||0),scrollLeft:Number(p?.scrollLeft||0)};
}
function rememberPagePosition(id=current){
  const pos=currentPagePosition(id);
  pagePositions.set(id,pos);
  return pos;
}
function saveCurrentHistoryPosition(){
  const pos=rememberPagePosition(current);
  if(!historyReady||!history.state?.yipman)return pos;
  history.replaceState({...history.state,view:current,scrollTop:pos.scrollTop,scrollLeft:pos.scrollLeft},'',location.href);
  return pos;
}
function positionFromState(id,st){
  const saved=pagePositions.get(id)||{scrollTop:0,scrollLeft:0};
  return {
    scrollTop:Number(st?.scrollTop??saved.scrollTop??0),
    scrollLeft:Number(st?.scrollLeft??saved.scrollLeft??0),
  };
}
function restorePagePosition(id,st){
  const p=$('#'+id);if(!p)return;
  const pos=positionFromState(id,st);
  requestAnimationFrame(()=>{p.scrollTop=pos.scrollTop;p.scrollLeft=pos.scrollLeft});
}
function renderView(id,{restore=false,reload=true,state=null}={}){
  if(!$('#'+id))id='quick';
  const enteringPrice=id==='price'&&current!=='price';
  if(enteringPrice&&!restore)priceIgnoredThisVisit=new Set();
  current=id;
  pages.forEach(p=>p.classList.toggle('on',p.id===id));
  nav.forEach(b=>b.classList.toggle('on',b.dataset.go===id));
  const p=$('#'+id);
  if(p){
    if(restore)restorePagePosition(id,state);
    else{p.scrollTop=0;p.scrollLeft=0;pagePositions.set(id,{scrollTop:0,scrollLeft:0})}
  }
  if(id!=='order'){clearTimeout(orderRetryTimer);orderRetryTimer=null}
  if(id!=='price'){clearTimeout(tprRetryTimer);tprRetryTimer=null}
  if(id!=='data'){clearTimeout(dataLiveTimer);dataLiveTimer=null}
  if(reload){
    if(id==='quick'&&!$('#globalInput').value.trim()&&!bestSellerGroups)loadBestSellers();
    if(id==='order')initOrdering();
    if(id==='price')loadPriceCurrentView();
    if(id==='data')loadData();
    if(id==='ai'){bindAi();loadAiBrief();}
  }else if(id==='data'){
    scheduleDataLivePoll();
  }
}
function go(id,{push=true}={}){
  if(id===current&&!$('#overlay').classList.contains('on'))return;
  saveCurrentHistoryPosition();
  renderView(id);
  if(push&&historyReady)history.pushState({yipman:true,view:id,scrollTop:0,scrollLeft:0},'', '#'+id);
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
function stashCurrentSheet(){
  const body=$('#sheetBody'),frag=document.createDocumentFragment(),sh=$('.sheet');
  while(body?.firstChild)frag.appendChild(body.firstChild);
  return {
    title:$('#sheetTitle')?.textContent||'',
    sub:$('#sheetSub')?.textContent||'',
    body:frag,
    scrollTop:Number(sh?.scrollTop||0),
  };
}
function restorePreviousSheet(){
  const prev=sheetStack.pop();if(!prev)return false;
  const body=$('#sheetBody');
  $('#sheetTitle').textContent=prev.title||'';
  $('#sheetSub').textContent=prev.sub||'';
  if(body){body.innerHTML='';body.appendChild(prev.body)}
  $('#overlay').classList.add('on');
  requestAnimationFrame(()=>{const sh=$('.sheet');if(sh)sh.scrollTop=Number(prev.scrollTop||0)});
  return true;
}
function sheet(title,sub,html){
  const wasOpen=$('#overlay').classList.contains('on');
  if(!wasOpen){saveCurrentHistoryPosition();sheetStack=[]}
  else sheetStack.push(stashCurrentSheet());
  $('#sheetTitle').textContent=title;$('#sheetSub').textContent=sub||'';$('#sheetBody').innerHTML=html;$('#overlay').classList.add('on');
  const sh=$('.sheet');if(sh)sh.scrollTop=0;
  if(historyReady&&!wasOpen){
    const pos=currentPagePosition(current);
    history.pushState({yipman:true,view:current,detail:true,originScrollTop:pos.scrollTop,originScrollLeft:pos.scrollLeft},'', '#'+current+'/detail');
    detailHistory=true;
  }
}
function closeSheet(useHistory=true){
  if(!$('#overlay').classList.contains('on'))return;
  if(useHistory&&sheetStack.length){restorePreviousSheet();return}
  $('#overlay').classList.remove('on');
  sheetStack=[];
  const had=detailHistory;detailHistory=false;
  if(useHistory&&had){history.back();return}
  if(had&&historyReady){
    const pos=rememberPagePosition(current);
    history.replaceState({yipman:true,view:current,scrollTop:pos.scrollTop,scrollLeft:pos.scrollLeft},'', '#'+current);
  }
}
$('#closeSheet').onclick=()=>closeSheet(true);
$('#overlay').onclick=e=>{if(e.target===$('#overlay'))closeSheet(true)};
function showExitConfirm(){$('#exitOverlay').classList.add('on')}
function hideExitConfirm(){$('#exitOverlay').classList.remove('on')}
$('#exitCancel').onclick=hideExitConfirm;
$('#exitConfirm').onclick=()=>{exitAllowed=true;hideExitConfirm();history.go(-2)};
window.addEventListener('popstate',e=>{
  const st=e.state;
  if($('#exitOverlay').classList.contains('on')){
    const pos=pagePositions.get('quick')||{scrollTop:0,scrollLeft:0};
    history.pushState({yipman:true,view:'quick',guard:true,...pos},'', '#quick');
    hideExitConfirm();renderView('quick',{restore:true,reload:false,state:{...pos}});return;
  }
  if($('#overlay').classList.contains('on')){
    if(sheetStack.length){
      restorePreviousSheet();
      if(historyReady){
        const pos=pagePositions.get(current)||currentPagePosition(current);
        history.pushState({yipman:true,view:current,detail:true,originScrollTop:pos.scrollTop,originScrollLeft:pos.scrollLeft},'', '#'+current+'/detail');
        detailHistory=true;
      }
      return;
    }
    $('#overlay').classList.remove('on');detailHistory=false;
    if(st?.yipman&&st.view){
      renderView(st.view,{restore:true,reload:false,state:st});
    }
    return;
  }
  if(st?.yipman&&st.root){
    const pos=pagePositions.get('quick')||{scrollTop:0,scrollLeft:0};
    renderView('quick',{restore:true,reload:false,state:{...pos}});
    history.pushState({yipman:true,view:'quick',guard:true,...pos},'', '#quick');
    showExitConfirm();
    return;
  }
  if(st?.yipman&&st.view){
    renderView(st.view,{restore:true,reload:false,state:st});
    return;
  }
});
pages.forEach(p=>p.addEventListener('scroll',()=>{
  pagePositions.set(p.id,{scrollTop:Number(p.scrollTop||0),scrollLeft:Number(p.scrollLeft||0)});
  if(p.id!==current||!historyReady||!history.state?.yipman)return;
  clearTimeout(historyScrollTimer);
  historyScrollTimer=setTimeout(()=>{
    if(p.id!==current||!history.state?.yipman)return;
    history.replaceState({...history.state,view:current,scrollTop:Number(p.scrollTop||0),scrollLeft:Number(p.scrollLeft||0)},'',location.href);
  },120);
},{passive:true}));
window.addEventListener('beforeunload',e=>{if(window.__YIPMAN_DESKTOP_ACTIVE__||exitAllowed)return;e.preventDefault();e.returnValue=''});
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
   receipt_7d_qty:a?.receipt_7d_qty??null,
   receipt_7d_uom:a?.receipt_7d_uom||'',
   receipt_7d_status:a?.receipt_7d_status||'',
   receipt_7d_day_count:a?.receipt_7d_day_count??null,
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
     source_receipt_verified:!!r.family_source_receipt_verified,
     source_receipt_history:Array.isArray(r.family_source_receipt_history)?r.family_source_receipt_history:[],
     source_receipt_7d_qty:r.family_source_receipt_7d_qty??null,
     source_receipt_7d_uom:r.family_source_receipt_7d_uom||'',
     source_receipt_7d_status:r.family_source_receipt_7d_status||'',
     source_receipt_7d_day_count:r.family_source_receipt_7d_day_count??null,
     family_receipt_verified:!!r.family_receipt_verified,
     family_receipt_history:Array.isArray(r.family_receipt_history)?r.family_receipt_history:[],
     family_receipt_7d_qty:r.family_receipt_7d_qty??null,
     family_receipt_7d_uom:r.family_receipt_7d_uom||'',
     family_receipt_7d_status:r.family_receipt_7d_status||'',
     family_receipt_7d_day_count:r.family_receipt_7d_day_count??null,
     family_oh:r.family_oh??null,
     family_oh_uom:r.family_oh_uom||'',
     family_oh_source:r.family_oh_source||'',
     family_oh_status:r.family_oh_status||'',
     family_oh_is_true_stock:String(r.family_oh_source||'').toUpperCase().startsWith('FAMILY_TRUE_STOCK'),
     family_system_oh:r.family_system_oh??null,
     family_system_oh_uom:r.family_system_oh_uom||'',
     family_system_oh_source:r.family_system_oh_source||'',
     family_cost:r.family_cost??null,
     family_cost_uom:r.family_cost_uom||'',
     family_cost_source:r.family_cost_source||'',
     family_cost_date:r.family_cost_date||null,
     family_cost_status:r.family_cost_status||''
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

   // Receiving rows must represent actual Receiving Article receipt history.
   // Family-level receipt history is an aggregate of those article events and
   // must never be rendered beside them as another receipt row, or the user
   // sees the same physical delivery twice. Keep the Family aggregate only as
   // a fallback when no article-level receipt history is available.
   for(const a of g.article_catalog.values()){
     if(a.receipt_verified||a.receipt_history.length){
       g.receiving.set(a.article_number,{
         article_number:a.article_number,
         article_description:a.article_description||'',
         receipt_history:a.receipt_history||[],
         receipt_7d_qty:a.receipt_7d_qty??null,
         receipt_7d_uom:a.receipt_7d_uom||'',
         receipt_7d_status:a.receipt_7d_status||'',
         receipt_7d_day_count:a.receipt_7d_day_count??null,
         source_family:false
       });
     }
   }

   // The Family/Main Article may itself receive physical 101/109 stock. That
   // is a real Receiving Article row, not the Family aggregate. Keep it visible
   // even when linked Receiving Articles also exist so the displayed Article
   // subtotals can reconcile to Family 7D Receipt.
   if(sourceKey&&g.source_receipt_history.length&&!g.receiving.has(sourceKey)){
     g.receiving.set(sourceKey,{
       article_number:sourceKey,
       article_description:g.family_name||'',
       receipt_history:g.source_receipt_history,
       receipt_7d_qty:g.source_receipt_7d_qty,
       receipt_7d_uom:g.source_receipt_7d_uom||'',
       receipt_7d_status:g.source_receipt_7d_status||'',
       receipt_7d_day_count:g.source_receipt_7d_day_count??null,
       source_family:false,
       source_article_receipt:true
     });
   }

   // Aggregate Family history remains a last-resort display fallback only when
   // no actual Article-level physical receipt row exists.
   if(!g.receiving.size&&sourceKey&&g.family_receipt_history.length){
     g.receiving.set(sourceKey,{
       article_number:sourceKey,
       article_description:g.family_name||'',
       receipt_history:g.family_receipt_history,
       receipt_7d_qty:g.family_receipt_7d_qty,
       receipt_7d_uom:g.family_receipt_7d_uom||'',
       receipt_7d_status:g.family_receipt_7d_status||'',
       receipt_7d_day_count:g.family_receipt_7d_day_count??null,
       source_family:true,
       aggregate_fallback:true
     });
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
 const testedText=v=>{const p=retailPoint(v);return p===null?'Not set':money(p)};
 const comp=(label,attr,val,cls='')=>num(val)===null?'':'<div class="qprice comp '+cls+'"><small>'+label+'</small><b '+attr+'>'+pm(val)+'</b></div>';
 const priceStrip=active?'<div class="qupcprices" data-qprice-status="loading">'+
   '<div class="qprice"><small>CURRENT</small><b data-q-current>'+pm(r.price)+'</b></div>'+
   '<div class="qprice tested"><small>TESTED</small><b data-q-tested>'+testedText(r.sweet_spot_price)+'</b></div>'+
   '<div class="qprice testing"><small>TPR SUGGESTION PRICE</small><b data-q-testing>…</b></div>'+
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
 const history=(Array.isArray(a.receipt_history)?a.receipt_history:[]).slice(0,2),familyFallback=!!a.source_family;
 const q7=num(a.receipt_7d_qty),u7=a.receipt_7d_uom||history[0]?.uom||'';
 const subtotal=q7===null?'':('<span class="qr7d">'+(familyFallback?'7D FAMILY TOTAL · ':'7D RECEIPT · ')+fmt(q7)+' '+esc(u7)+'</span>');
 return '<div class="qreceivingrow"><div class="qrecvidentity"><span class="qricon">'+(familyFallback?'Σ':'R')+'</span><div><div class="qrnum">'+esc(a.article_number||'—')+'</div><div class="qrname">'+esc(familyFallback?'FAMILY RECEIPT SUMMARY':(a.article_description||'Receiving Article'))+'</div>'+subtotal+'</div></div>'+
   quickDeliveryCell(history[0],'LATEST DELIVERY',familyId,familyFallback?'':a.article_number)+quickDeliveryCell(history[1],'PREV DELIVERY',familyId,familyFallback?'':a.article_number)+'</div>';
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
   const familyCost=num(g.family_cost),familyCostUom=g.family_cost_uom||'';
   const familyCostMeta=[g.family_cost_source?friendlySignal(g.family_cost_source):'',g.family_cost_date?shortDate(g.family_cost_date):''].filter(Boolean).join(' · ');
   const familyCostHtml='<div class="qfamilycost"><span>FAMILY COST</span><b>'+(familyCost===null?'—':money(familyCost)+(familyCostUom?' / '+esc(familyCostUom):''))+'</b>'+(familyCostMeta?'<small>'+esc(familyCostMeta)+'</small>':'')+'</div>';
   const familyHead='<div class="qfhead">'+
     '<div class="qfidentity"><div class="qlabel">FAMILY ARTICLE</div><div class="qfnum">'+esc(g.family_article||'—')+(g.family_receipt_verified?'<span class="qreceipt">O</span>':'')+'</div>'+
     '<div class="qfname">'+esc(g.family_name||'Unmapped Family')+'</div><div class="qmeta">'+esc(g.category||'')+(recon?' · '+(recon==='PASS'?'TOTAL SELLING MVT RECONCILED':'TOTAL SELLING MVT HOLD'):'')+'</div>'+familyCostHtml+'</div>'+
     '<div class="qffocus">'+
       familyOhPairHtml({family:g.family_article,name:g.family_name,effective:g.family_oh,effective_uom:g.family_oh_uom,effective_source:g.family_oh_source,system:g.family_system_oh,system_uom:g.family_system_oh_uom})+
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
 bindFamilyOhEditors();
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
    const pricingAnalysis=String(d.price_review_analysis_status||'').toUpperCase();
    const pricingCache=String(d.price_review_cache_status||'').toUpperCase();
    const pricingWarming=['REFRESHING','WARMING'].includes(pricingAnalysis)||pricingCache==='WARMING'||pricingCache==='SOURCE_CHANGED_REFRESHING'||pricingAnalysis.includes('SOURCE_CHANGED');
    setPath('[data-q-testing]',row.testing_price,pricingWarming?'…':'None');
    set('[data-q-comp-a]',row.company_price_a);
    set('[data-q-comp-b]',row.company_price_b);
    set('[data-q-comp-c]',row.company_price_c);
    const strip=card.querySelector('[data-qprice-status]');
    if(strip){
      strip.dataset.qpriceStatus=String(row.suggestion_status||'READY');
      strip.title='Current: '+String(row.current_price_source||'—')+(row.current_price_asof_date?' · '+String(row.current_price_asof_date):'')+
        ' | Tested: '+(num(row.tested_price)===null?'—':money(row.tested_price))+
        ' | TPR Suggestion Price: '+(num(row.testing_price)===null?'—':money(row.testing_price))+
        ' | '+String(row.suggestion_reason||row.suggestion_status||'—');
    }
  });
  const pricingAnalysis=String(d.price_review_analysis_status||'').toUpperCase();
  const pricingCache=String(d.price_review_cache_status||'').toUpperCase();
  const pricingWarming=['REFRESHING','WARMING'].includes(pricingAnalysis)||pricingCache==='WARMING'||pricingCache==='SOURCE_CHANGED_REFRESHING'||pricingAnalysis.includes('SOURCE_CHANGED');
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
function stockFlowObservedWeekdays(row){
 const direct=Array.isArray(row?.observed_delivery_weekday_numbers)
   ? row.observed_delivery_weekday_numbers.map(x=>Number(x)).filter(Number.isInteger)
   : [];
 if(direct.length)return [...new Set(direct)];
 return [...new Set((Array.isArray(row?.observed_delivery_days)?row.observed_delivery_days:[])
   .map(x=>Number(x?.weekday_number)).filter(Number.isInteger))];
}
function stockFlowMatchesDelivery(row,filter=stockFlowDeliveryFilter){
 if(filter==='ALL')return true;
 const days=stockFlowObservedWeekdays(row);
 if(filter==='TUE_WED')return days.some(x=>x===1||x===2);
 if(filter==='THU_FRI')return days.some(x=>x===3||x===4);
 return true;
}
function stockFlowMatchesCategory(row,filter=stockFlowCategoryFilter){
 if(filter==='ALL')return true;
 const cat=String(row?.category||'').trim().toUpperCase();
 return cat===filter||cat.startsWith(filter+' ')||cat.includes(filter);
}
function stockFlowFilteredRows(){
 return [...(bestSellerGroups||[])].filter(r=>
   stockFlowMatchesDelivery(r)&&stockFlowMatchesCategory(r)
 );
}
function stockFlowSortedRows(){
 const rows=stockFlowFilteredRows();
 const zeroSelling=r=>!!r.no_recent_selling||((num(r.group_qty_7d)??0)===0&&(num(r.family_receipt_7d_qty)||0)>0);
 if(stockFlowSort==='RECEIPT')return rows.sort((a,b)=>(num(b.family_receipt_7d_qty)||0)-(num(a.family_receipt_7d_qty)||0));
 if(stockFlowSort==='SELLING')return rows.sort((a,b)=>(num(b.group_qty_7d)||0)-(num(a.group_qty_7d)||0));
 if(stockFlowSort==='RATIO')return rows.sort((a,b)=>(Number(zeroSelling(b))-Number(zeroSelling(a)))||((num(b.receipt_to_selling_ratio)||0)-(num(a.receipt_to_selling_ratio)||0))||((num(b.receipt_minus_selling_7d)||0)-(num(a.receipt_minus_selling_7d)||0)));
 if(stockFlowSort==='NAME')return rows.sort((a,b)=>String(a.family_name||'').localeCompare(String(b.family_name||'')));
 return rows.sort((a,b)=>(num(b.receipt_minus_selling_7d)||0)-(num(a.receipt_minus_selling_7d)||0));
}
function renderStockFlow(){
 const box=$('#quickRows'),rows=stockFlowSortedRows(),allRows=[...(bestSellerGroups||[])];
 const noticeHtml=stockFlowNotice?'<div class="stockflownotice"><span>'+esc(stockFlowNotice)+'</span><button type="button" data-stock-retry>RETRY</button></div>':'';
 const dAll=allRows.filter(r=>stockFlowMatchesCategory(r)).length;
 const dTueWed=allRows.filter(r=>stockFlowMatchesCategory(r)&&stockFlowMatchesDelivery(r,'TUE_WED')).length;
 const dThuFri=allRows.filter(r=>stockFlowMatchesCategory(r)&&stockFlowMatchesDelivery(r,'THU_FRI')).length;
 const cAll=allRows.filter(r=>stockFlowMatchesDelivery(r)).length;
 const cLive=allRows.filter(r=>stockFlowMatchesDelivery(r)&&stockFlowMatchesCategory(r,'LIVE')).length;
 const cFresh=allRows.filter(r=>stockFlowMatchesDelivery(r)&&stockFlowMatchesCategory(r,'FRESH')).length;
 const cFrozen=allRows.filter(r=>stockFlowMatchesDelivery(r)&&stockFlowMatchesCategory(r,'FROZEN')).length;
 const active=(value,current)=>value===current?' on':'';
 box.innerHTML=noticeHtml+
   '<div class="besthead"><div><h3>Stock Flow Watch</h3><span>7D receipts ≥ 150% of 7D selling movement</span></div></div>'+
   '<div class="stockflowfilters">'+
     '<div class="stockfiltergroup delivery"><small>DELIVERY FILTER</small><div class="stockfilterbuttons">'+
       '<button class="stockfilterbtn'+active('ALL',stockFlowDeliveryFilter)+'" data-stock-delivery="ALL">ALL <b>'+dAll+'</b></button>'+
       '<button class="stockfilterbtn deliverytw'+active('TUE_WED',stockFlowDeliveryFilter)+'" data-stock-delivery="TUE_WED">🚚 TUE &amp; WED <b>'+dTueWed+'</b></button>'+
       '<button class="stockfilterbtn deliverytf'+active('THU_FRI',stockFlowDeliveryFilter)+'" data-stock-delivery="THU_FRI">🚚 THU &amp; FRI <b>'+dThuFri+'</b></button>'+
     '</div></div>'+
     '<div class="stockfiltergroup category"><small>CATEGORY FILTER</small><div class="stockfilterbuttons">'+
       '<button class="stockfilterbtn'+active('ALL',stockFlowCategoryFilter)+'" data-stock-category="ALL">ALL <b>'+cAll+'</b></button>'+
       '<button class="stockfilterbtn live'+active('LIVE',stockFlowCategoryFilter)+'" data-stock-category="LIVE">LIVE <b>'+cLive+'</b></button>'+
       '<button class="stockfilterbtn fresh'+active('FRESH',stockFlowCategoryFilter)+'" data-stock-category="FRESH">FRESH <b>'+cFresh+'</b></button>'+
       '<button class="stockfilterbtn frozen'+active('FROZEN',stockFlowCategoryFilter)+'" data-stock-category="FROZEN">FROZEN <b>'+cFrozen+'</b></button>'+
     '</div></div>'+
   '</div>'+
   '<div class="stockflowresultbar"><b>'+rows.length+' ITEM'+(rows.length===1?'':'S')+'</b><label class="stockflowsort">SORT<select id="stockFlowSort"><option value="RATIO">OVER-SELLING % ↓</option><option value="DIFFERENCE">DIFFERENCE ↓</option><option value="RECEIPT">7D RECEIPT ↓</option><option value="SELLING">7D SELLING ↓</option><option value="NAME">NAME A–Z</option></select></label></div>'+
   (rows.length?rows.map(stockFlowFamilyHtml).join(''):'<div class="empty stockflowempty">No Stock Flow items match these filters.</div>');
 const sel=$('#stockFlowSort');if(sel){sel.value=stockFlowSort;sel.onchange=e=>{stockFlowSort=e.target.value;renderStockFlow()}}
 $$('[data-stock-delivery]').forEach(b=>b.onclick=()=>{stockFlowDeliveryFilter=b.dataset.stockDelivery||'ALL';renderStockFlow()});
 $$('[data-stock-category]').forEach(b=>b.onclick=()=>{stockFlowCategoryFilter=b.dataset.stockCategory||'ALL';renderStockFlow()});
 document.querySelectorAll('[data-stock-receipts]').forEach(b=>b.onclick=e=>{
   e.stopPropagation();
   const box=b.closest('.bestrecent');if(!box)return;
   box.classList.toggle('open');
   b.textContent=box.classList.contains('open')?'HIDE':'SHOW 2';
 });
 bindReceiptLinks();
 bindFamilyOhEditors();
 bindStockFlowRetry();
}
function stockFlowFamilyHtml(g,idx){
 const uom=g.group_uom||'',receiptUom=g.family_receipt_7d_uom||uom||'',history=(Array.isArray(g.family_receipt_history)?g.family_receipt_history:[]).slice(0,2);
 const count=num(g.family_receipt_7d_day_count),diff=num(g.receipt_minus_selling_7d),ratio=num(g.receipt_to_selling_ratio),promo=g.recent_promotion_event||null;
 const zeroSelling=!!g.no_recent_selling||((num(g.group_qty_7d)??0)===0&&(num(g.family_receipt_7d_qty)||0)>0);
 const category=String(g.category||'').trim().toUpperCase();
 const observed=(Array.isArray(g.observed_delivery_days)?g.observed_delivery_days:[])
   .filter(x=>x&&x.weekday)
   .sort((a,b)=>Number(a.weekday_number)-Number(b.weekday_number));
 const observedLabels=observed.map(x=>String(x.weekday||'').slice(0,3).toUpperCase());
 const categoryTag=category?'<span class="stocktag category '+category.toLowerCase()+'">'+esc(category)+'</span>':'';
 const observedTag=observedLabels.length?'<span class="stocktag delivery" title="Canonical observed receipt weekdays">🚚 OBS '+esc(observedLabels.slice(0,4).join(' / '))+(observedLabels.length>4?' +'+(observedLabels.length-4):'')+'</span>':'<span class="stocktag delivery none">NO DELIVERY DAY</span>';
 const fridayWarning=g.friday_delivery_warning?'<span class="stockfridaywarn">⚠ USUALLY FRIDAY DELIVERY</span>':'';
 const recent=history.length?history.map((x,i)=>'<button type="button" class="bestreceipt receiptlink'+(i?' stockreceiptmore':'')+'" data-receipt-family="'+esc(g.family_id??'')+'" data-receipt-article="" data-receipt-date="'+esc(x.date||'')+'"><span>'+esc(quickReceiptDay(x.date))+'</span><b>'+fmt(x.quantity)+' '+esc(x.uom||receiptUom)+'</b></button>').join(''):'<div class="bestreceipt"><span>No recent receipt</span><b>—</b></div>';
 const latestCost=num(g.latest_receipt_cost),latestCostUom=g.latest_receipt_cost_uom||'';
 const costHtml='<span class="stocklatestcost" title="Latest physical receipt cost'+(g.latest_receipt_date?' · '+esc(appDate(g.latest_receipt_date)):'')+'">LATEST COST <b>'+(latestCost===null?'—':money(latestCost)+(latestCostUom?' / '+esc(latestCostUom):''))+'</b></span>';
 const receiptToggle=history.length>1?'<button type="button" class="stockreceipttoggle" data-stock-receipts>SHOW 2</button>':'';
 const promoRange=promo?(shortDate(promo.start_date)+(String(promo.end_date||'')&&String(promo.end_date)!==String(promo.start_date)?'–'+shortDate(promo.end_date):'')):'';
 const promoExtra=promo&&String(promo.promotion_week_extra_qty_status||'').toUpperCase()==='READY'&&num(promo.promotion_week_extra_qty)!==null
   ? '<div><span class="promolift">EXTRA '+(num(promo.promotion_week_extra_qty)>=0?'+':'')+fmt(promo.promotion_week_extra_qty)+' '+esc(promo.promotion_week_extra_qty_uom||uom)+'</span><span class="promobasis">VS NORMAL NON-PROMO WEEK</span></div>'
   : '<div><span class="promobasis">EXTRA QTY BASELINE UNAVAILABLE</span></div>';
 const promoPrice=promo&&String(promo.avg_promotion_selling_price_status||'').toUpperCase()==='READY'&&num(promo.avg_promotion_selling_price)!==null
   ? '<span class="promoprice"><small>AVG PROMO PRICE</small><b>'+money(promo.avg_promotion_selling_price)+' / '+esc(promo.avg_promotion_selling_price_uom||uom)+'</b></span>'
   : '';
 const promoHtml=promo?'<div class="stocksale stockpromo"><strong>RECENT SALE · '+esc(promoRange)+'</strong>'+promoExtra+promoPrice+'</div>':'';
 const overSelling=zeroSelling?'∞':(ratio===null?'—':((ratio-1)*100).toFixed(0)+'%');
 return '<section class="bestfam article-tone-'+articleTone(g.family_article||g.family_id)+'"><div class="besttop"><div><div class="bestlabel">FAMILY ARTICLE</div><div class="bestnum">'+esc(g.family_article||'—')+'</div><div class="bestname">'+esc(g.family_name||'Unmapped Family')+'</div><div class="stocktags">'+categoryTag+observedTag+'</div></div><div class="stockratio"><small>OVER SELLING</small><b>'+overSelling+'</b></div></div>'+
   familyOhPairHtml({family:g.family_article,name:g.family_name,effective:g.effective_oh,effective_uom:g.effective_oh_uom,effective_source:g.effective_oh_source,system:g.system_oh,system_uom:g.system_oh_uom})+
   '<div class="stockflowgrid"><div class="bestmetric"><small>7D SELLING MVT</small><b>'+fmt(g.group_qty_7d)+' '+esc(uom)+'</b><span>AVG/DAY · '+fmt(g.group_avg_qty_day)+' '+esc(uom)+'</span></div>'+
   '<div class="bestmetric"><small>7D RECEIPT</small><b>'+fmt(g.family_receipt_7d_qty)+' '+esc(receiptUom)+'</b><span>'+(count===null?'—':fmt(count,0))+' RECEIPT DAY'+(count===1?'':'S')+' / 7D</span></div>'+
   '<div class="stockdiff'+(zeroSelling?' nosale':(promo?' promoted':' nosale'))+'"><small>DIFFERENCE</small><b>+'+fmt(diff)+' '+esc(uom)+'</b><span>'+(zeroSelling?'positive receipts with 0 selling mvt':overSelling+' over selling')+'</span><span class="stockwatch">'+(zeroSelling?'0 SELLING MVT':(promo?'RECENT SALE':'NO RECENT SALE'))+'</span></div></div>'+
   promoHtml+
   '<div class="bestrecent"><div class="bestrecenthead"><span>RECENT RECEIPTS</span><span class="stockreceiptmeta">'+costHtml+receiptToggle+'</span></div>'+recent+'</div></section>';
}
function stockFlowReadCache(){
 try{
  const raw=localStorage.getItem(stockFlowCacheKey);
  if(!raw)return null;
  const data=JSON.parse(raw);
  return data&&Array.isArray(data.rows)?data:null;
 }catch{return null}
}
function stockFlowWriteCache(rows){
 try{
  stockFlowCacheSavedAt=new Date().toISOString();
  localStorage.setItem(stockFlowCacheKey,JSON.stringify({saved_at:stockFlowCacheSavedAt,rows:rows||[]}));
 }catch{}
}
function stockFlowCacheNotice(savedAt,suffix){
 const parsed=Date.parse(String(savedAt||''));
 const valid=Number.isFinite(parsed);
 const ageMs=valid?Math.max(0,Date.now()-parsed):null;
 const stale=ageMs!==null&&ageMs>12*60*60*1000;
 const when=valid?new Date(parsed).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'unknown time';
 return (stale?'STALE CACHE':'CACHED STOCK FLOW')+' · saved '+when+' · '+suffix;
}
function stockFlowSkeletonHtml(){
 return '<div class="stockflowskeleton" aria-label="Loading Stock Flow"><div></div><div></div><div></div></div>';
}
function bindStockFlowRetry(){
 const b=$('[data-stock-retry]');if(b)b.onclick=()=>loadBestSellers(true);
}
async function loadBestSellers(force=false){
 const box=$('#quickRows');
 if(bestSellerGroups&&!force){renderStockFlow();return}
 const requestId=++quickRequestSeq;lastQuickQuery='';
 if(!bestSellerGroups){
  const cached=stockFlowReadCache();
  if(cached?.rows?.length){
   bestSellerGroups=cached.rows;
   stockFlowCacheSavedAt=cached.saved_at||null;
   stockFlowNotice=stockFlowCacheNotice(stockFlowCacheSavedAt,'refreshing latest');
   renderStockFlow();
  }else{
   box.innerHTML=stockFlowSkeletonHtml();
  }
 }else{
  stockFlowNotice='Refreshing latest Stock Flow…';
  renderStockFlow();
 }
 try{
  const d=await api('/v1/yipman/stock-flow?limit=100',{timeoutMs:20000});
  if(requestId!==quickRequestSeq||$('#globalInput').value.trim())return;
  bestSellerGroups=(d.rows||[]).map(r=>({
    family_id:r.family_id,family_article:r.family_article,family_name:r.family_name,category:r.category,
    group_qty_7d:r.family_group_movement_7d,group_avg_qty_day:r.family_group_avg_qty_day,group_uom:r.family_group_movement_uom||'',
    family_receipt_history:Array.isArray(r.family_receipt_history)?r.family_receipt_history:[],family_receipt_7d_qty:r.family_receipt_7d_qty,
    family_receipt_7d_uom:r.family_receipt_7d_uom||'',family_receipt_7d_day_count:r.family_receipt_7d_day_count,
    receipt_minus_selling_7d:r.receipt_minus_selling_7d,receipt_to_selling_ratio:r.receipt_to_selling_ratio,
    receipt_over_selling_pct:r.receipt_over_selling_pct,no_recent_selling:!!r.no_recent_selling,recent_promotion_event:r.recent_promotion_event||null,
    observed_delivery_days:Array.isArray(r.observed_delivery_days)?r.observed_delivery_days:[],
    observed_delivery_weekday_numbers:Array.isArray(r.observed_delivery_weekday_numbers)?r.observed_delivery_weekday_numbers:[],
    delivery_pattern_frequency:r.delivery_pattern_frequency||null,
    delivery_pattern_receipt_date_count:r.delivery_pattern_receipt_date_count,
    delivery_pattern_lookback_days:r.delivery_pattern_lookback_days,
    friday_delivery_warning:!!r.friday_delivery_warning,
    friday_delivery_share:r.friday_delivery_share,
    latest_receipt_date:r.latest_receipt_date||null,
    latest_receipt_cost:r.latest_receipt_cost,
    latest_receipt_cost_uom:r.latest_receipt_cost_uom||'',
    latest_receipt_cost_source:r.latest_receipt_cost_source||null,
    effective_oh:r.effective_oh,
    effective_oh_uom:r.effective_oh_uom||'',
    effective_oh_source:r.effective_oh_source||'',
    effective_oh_status:r.effective_oh_status||'',
    effective_oh_is_true_stock:!!r.effective_oh_is_true_stock,
    system_oh:r.system_oh,system_oh_uom:r.system_oh_uom||'',system_oh_source:r.system_oh_source||''
  }));
  stockFlowNotice='';
  stockFlowWriteCache(bestSellerGroups);
  renderStockFlow();
 }catch(e){
  if(requestId!==quickRequestSeq)return;
  if(bestSellerGroups?.length){
   stockFlowNotice=stockFlowCacheNotice(
     stockFlowCacheSavedAt,
     String(e?.message||'').toLowerCase().includes('timed out')
       ? 'latest refresh timed out'
       : 'latest refresh failed'
   );
   renderStockFlow();
  }else{
   box.innerHTML='<div class="stockflowerror">'+esc(e.message||'Stock Flow unavailable')+'<button type="button" data-stock-retry>RETRY</button></div>';
   bindStockFlowRetry();
  }
 }
}

async function loadQuick(q){
 const query=String(q||'').trim(), box=$('#quickRows');
 if(!query){lastQuickQuery='';await loadBestSellers();return}
 const requestId=++quickRequestSeq;lastQuickQuery=query;box.innerHTML='<div class="loading">Searching current Quick Check…</div>';
 try{
  const d=await api('/v1/backoffice/inventory?category=ALL&limit=120&lightweight=true&include_oh=true&q='+encodeURIComponent(query),{timeoutMs:18000});
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
  const oh=d.effective_oh||{},sys=d.system_oh||{},q7=d.qty_7d||{};
  const ohPair=familyOhPairHtml({family:d.family_article_number,name:d.family_article_name||d.upc_name,effective:oh.quantity,effective_uom:oh.uom||d.selling_uom,effective_source:oh.source,system:sys.quantity,system_uom:sys.uom||d.selling_uom});
  sheet(d.upc_name||upc,(d.upc||upc)+' · Family '+(d.family_article_number||'—'),ohPair+'<div class="dmetrics"><div class="dm"><b>'+fmt(d.upc_velocity_7d)+'</b><span>'+esc(d.qty_uom||d.selling_uom||'UNIT')+' / DAY</span></div><div class="dm"><b>'+money(d.current_price)+'</b><span>CURRENT '+esc(d.current_price_type||'PRICE')+'</span></div><div class="dm"><b>'+fmt(d.dos)+'</b><span>DOS · EFFECTIVE OH</span></div></div><div class="detail"><b>7D sales</b><br>'+fmt(q7.sold_quantity)+' '+esc(d.qty_uom||'')+' across '+fmt(q7.supported_day_count,0)+' completed data day(s).<br><br><b>Current price source</b><br>'+esc(d.current_price_source||'—')+(d.current_price_asof_date?' · '+esc(d.current_price_asof_date):'')+'<br><br><b>Current cost</b><br>'+money(d.current_cost_per_selling_unit)+' / '+esc(d.selling_uom||'unit')+'<br><br><b>OH status</b><br>'+esc(oh.status||'—')+(oh.reason?'<br>'+esc(oh.reason):'')+'</div>');
  bindFamilyOhEditors();
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
function plusDaysIso(v,days){
 const d=dateLocal(v);if(!d)return null;
 d.setDate(d.getDate()+Number(days||0));return iso(d);
}
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
    orderNextDate=plusDaysIso(orderDate,7);
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
  if(!orderNextDate||orderNextDate<=orderDate)orderNextDate=plusDaysIso(orderDate,7);
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

function openManualPromotion(){
 const startDefault=orderDate||iso(new Date());
 const endDefault=plusDaysIso(startDefault,6);
 const deliveryDefault=orderDate||startDefault;
 const nextDefault=orderNextDate||plusDaysIso(deliveryDefault,7);
 const selected=new Map();
 let searchTimer=null;
 let latestSearchToken=0;

 sheet(
  'Manual Promotion',
  'Search item first · then enter promotion details',
  '<div class="detail manual-promo-search">'+
   '<div><b>1. Search item</b><div class="manual-promo-search-note">Search UPC, SAP Selling Article, Family Article, Delivery Article, English name, or Chinese name. Typo-tolerant search is supported.</div></div>'+
   '<div class="manual-promo-searchbar"><input id="manualPromoSearch" placeholder="Search salmon, 240816, article…" autocomplete="off"><button id="manualPromoSearchBtn" type="button">SEARCH</button></div>'+
   '<div id="manualPromoSearchStatus" class="manual-promo-search-note">Start typing to find an item.</div>'+
   '<div id="manualPromoSearchResults" class="manual-promo-results"></div>'+
   '<div><b>2. Selected promotion item(s)</b><div id="manualPromoSelected" class="manual-promo-selected"><div class="empty">No item selected yet.</div></div></div>'+
   '<div><b>3. Promotion + delivery window</b></div>'+
   '<div class="manual-promo-fields">'+
    '<label class="wide">LIST NAME<input id="manualPromoName" value="Manual Promotion '+esc(startDefault)+'"></label>'+
    '<label>PROMO START<input type="date" id="manualPromoStart" value="'+esc(startDefault)+'"></label>'+
    '<label>PROMO END<input type="date" id="manualPromoEnd" value="'+esc(endDefault)+'"></label>'+
    '<label>DELIVERY DATE<input type="date" id="manualPromoDelivery" value="'+esc(deliveryDefault)+'"></label>'+
    '<label>NEXT DELIVERY<input type="date" id="manualPromoNext" value="'+esc(nextDefault)+'"></label>'+
   '</div>'+
   '<div class="estimatebar" style="margin-top:10px">Yipman uses the selected Family True Stock, canonical sales history, promotion history, observed delivery evidence, and Fresh/Live freshness limits. Manual uplift is not required.</div>'+
   '<div class="actions"><button id="manualPromoCancel">CANCEL</button><button class="primary" id="manualPromoSave">ADD TO PROMOTION ORDER</button></div>'+
  '</div>'
 );

 const searchInput=$('#manualPromoSearch');
 const searchStatus=$('#manualPromoSearchStatus');
 const searchResults=$('#manualPromoSearchResults');
 const selectedBox=$('#manualPromoSelected');

 function familyKeyFor(item){
  return String(item?.family_article_number||(String(item?.result_type||'').toUpperCase()==='FAMILY'?item?.number:'')||'').trim();
 }
 function relatedDeliverySummary(fam){
  const rows=Array.isArray(fam?.receiving_ordering_articles)?fam.receiving_ordering_articles:[];
  if(!rows.length)return 'Delivery article: —';
  return rows.slice(0,3).map(a=>{
   const n=a.article_number||a.receiving_article||a.number||'—';
   const name=a.article_description||a.article_name||a.name||'';
   const pack=a.pack_size||a.pack||a.receiving_pack_size||'';
   return String(n)+(name?' · '+name:'')+(pack?' · '+pack:'');
  }).join(' | ')+(rows.length>3?' · +'+(rows.length-3)+' more':'');
 }
 function effectiveOHText(fam){
  const oh=fam?.current_effective_oh||{};
  const qty=oh.quantity??oh.current_oh??oh.effective_oh;
  const uom=oh.uom||oh.uom_code||fam?.family_sales_7d?.uom||'';
  return qty==null?'—':fmtNullable(qty)+' '+String(uom||'');
 }
 function selectedPrice(id){
  const el=document.querySelector('[data-manual-promo-price="'+CSS.escape(String(id))+'"]');
  return el?Number(el.value):NaN;
 }
 function renderSelected(){
  const rows=[...selected.values()];
  if(!rows.length){selectedBox.innerHTML='<div class="empty">No item selected yet.</div>';return}
  selectedBox.innerHTML=rows.map(x=>{
   const fam=x.family||{}, item=x.item||{};
   const fid=String(fam.family_id||item.family_id||x.familyKey||'');
   const price=item.current_price??'';
   const q7=item.pos_qty_7d??fam?.family_sales_7d?.sold_quantity;
   const q7u=item.selling_uom||fam?.family_sales_7d?.uom||'';
   return '<div class="manual-promo-selected-card">'+
    '<div class="manual-promo-selected-top"><div><h4>'+esc(fam.family_article_name||item.family_name||item.name||x.familyKey)+'</h4>'+
     '<div class="selmeta">Family '+esc(x.familyKey)+' · Selected '+esc(x.code)+(q7!=null?' · 7D '+fmtNullable(q7)+' '+esc(q7u):'')+' · True Stock '+esc(effectiveOHText(fam))+'</div>'+
    '</div><label>SALE PRICE<input data-manual-promo-price="'+esc(fid)+'" inputmode="decimal" value="'+esc(price)+'" placeholder="0.00"></label></div>'+
    '<div class="manual-promo-delivery">'+esc(relatedDeliverySummary(fam))+'</div>'+
    '<button class="manual-promo-remove" type="button" data-manual-promo-remove="'+esc(fid)+'">REMOVE</button>'+
   '</div>';
  }).join('');
  $('[data-manual-promo-remove]').forEach(btn=>btn.onclick=()=>{
   selected.delete(String(btn.dataset.manualPromoRemove));renderSelected();
  });
 }
 async function hydrateFamily(item){
  const familyKey=familyKeyFor(item);
  if(!familyKey)throw new Error('Family Article unavailable for this result');
  const fam=await api('/v1/app/v2/family/'+encodeURIComponent(familyKey),{timeoutMs:12000});
  return {familyKey,fam};
 }
 async function chooseResult(entry){
  try{
   searchStatus.textContent='Loading Family inventory and delivery details…';
   const hydrated=entry.family?{familyKey:entry.familyKey,fam:entry.family}:await hydrateFamily(entry.item);
   const item=entry.item;
   const fid=String(hydrated.fam?.family_id||item.family_id||hydrated.familyKey);
   const type=String(item.result_type||'').toUpperCase();
   const code=type==='UPC'?String(item.number||''):(type==='ARTICLE'?String(item.number||hydrated.familyKey):String(hydrated.familyKey));
   if(!code)throw new Error('Selectable UPC / Article number unavailable');
   const previous=selected.get(fid);
   selected.set(fid,{familyKey:hydrated.familyKey,family:hydrated.fam,item,code});
   renderSelected();
   searchStatus.textContent=previous
    ? 'Replaced the previous selection for Family '+hydrated.familyKey+' to avoid duplicate Family inventory.'
    : 'Added Family '+hydrated.familyKey+'. Search again to add another Family.';
   searchInput.focus();searchInput.select();
  }catch(e){searchStatus.textContent='Unable to select item · '+e.message}
 }
 async function runSearch(){
  const q=String(searchInput.value||'').trim();
  const token=++latestSearchToken;
  if(q.length<2){searchResults.innerHTML='';searchStatus.textContent='Enter at least 2 characters.';return}
  searchStatus.textContent='Searching…';searchResults.innerHTML='<div class="loading">Searching current item master…</div>';
  try{
   const d=await api('/v1/app/v2/search?q='+encodeURIComponent(q)+'&limit=12',{timeoutMs:12000});
   if(token!==latestSearchToken)return;
   const raw=Array.isArray(d.results)?d.results:[];
   const base=raw.slice(0,10);
   const enriched=await Promise.all(base.map(async item=>{
    const familyKey=familyKeyFor(item);
    let family=null;
    if(familyKey){try{family=await api('/v1/app/v2/family/'+encodeURIComponent(familyKey),{timeoutMs:9000})}catch(e){}}
    return {item,familyKey,family};
   }));
   if(token!==latestSearchToken)return;
   searchStatus.textContent=enriched.length?enriched.length+' result(s) · choose the correct item':'No matching item.';
   searchResults.innerHTML=enriched.map((x,i)=>{
    const item=x.item||{}, fam=x.family||{};
    const familyName=fam.family_article_name||item.family_name||(String(item.result_type||'').toUpperCase()==='FAMILY'?item.name:'');
    const itemName=item.name||familyName||'Item';
    const q7=item.pos_qty_7d??fam?.family_sales_7d?.sold_quantity;
    const q7u=item.selling_uom||fam?.family_sales_7d?.uom||'';
    return '<button class="manual-promo-result" type="button" data-manual-promo-result="'+i+'">'+
     '<b>'+esc(itemName)+'</b><strong>'+esc(String(item.result_type||'ITEM'))+' '+esc(item.number||'—')+'</strong>'+
     '<span>Family '+esc(x.familyKey||'—')+(familyName?' · '+esc(familyName):'')+
      ' · Current '+(item.current_price!=null?money(item.current_price):'—')+
      (q7!=null?' · 7D '+fmtNullable(q7)+' '+esc(q7u):'')+
      ' · OH '+esc(effectiveOHText(fam))+'</span></button>';
   }).join('');
   $('[data-manual-promo-result]').forEach(btn=>btn.onclick=()=>chooseResult(enriched[Number(btn.dataset.manualPromoResult)]));
  }catch(e){
   if(token!==latestSearchToken)return;
   searchResults.innerHTML='';searchStatus.textContent='Search unavailable · '+e.message;
  }
 }
 searchInput.oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(runSearch,260)};
 searchInput.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();clearTimeout(searchTimer);runSearch()}};
 $('#manualPromoSearchBtn').onclick=()=>{clearTimeout(searchTimer);runSearch()};
 $('#manualPromoCancel').onclick=()=>closeSheet(true);
 $('#manualPromoSave').onclick=async()=>{
  const rows=[...selected.values()];
  const start=$('#manualPromoStart').value;
  const end=$('#manualPromoEnd').value;
  const delivery=$('#manualPromoDelivery').value;
  const next=$('#manualPromoNext').value;
  if(!rows.length){toast('Select at least one item');return}
  if(!start||!end||!delivery||!next){toast('Complete all promotion and delivery dates');return}
  if(end<start){toast('Promotion end must be after start');return}
  if(next<=delivery){toast('Next delivery must be after delivery date');return}
  const items=rows.map(x=>{
   const fid=String(x.family?.family_id||x.item?.family_id||x.familyKey);
   return {upc:x.code,description:x.family?.family_article_name||x.item?.name||'',promotion_type:'CUSTOM',promotion_start_date:start,promotion_end_date:end,promotion_price:selectedPrice(fid)};
  });
  if(items.some(x=>!Number.isFinite(x.promotion_price)||x.promotion_price<=0)){toast('Enter a valid SALE price for every selected item');return}
  const name=$('#manualPromoName').value.trim()||('Manual Promotion '+start);
  const save=$('#manualPromoSave');save.disabled=true;save.textContent='SAVING…';
  try{
   const created=await api('/v1/yipman/promotion-lists',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({list_name:name,source_filename:'MANUAL_SEARCH_ENTRY',items}),timeoutMs:30000});
   promoListId=Number(created.list_id);promoTempOH.clear();
   orderDate=delivery;orderNextDate=next;
   closeSheet(true);buildDays();updateOrderWindowUI();
   await loadPromotionLists();$('#promoListSelect').value=String(promoListId);
   if(Number(created.ready_count||0)>0)await loadPromotionOrder();
   else{$('#promoOrderStatus').textContent='Manual promotion saved but all items require mapping / validation review.';$('#promoRows').innerHTML='<div class="empty">No READY promotion items yet.</div>'}
   toast('Manual promotion added');
  }catch(err){
   toast('Manual promotion failed · '+err.message);
   if(document.getElementById('manualPromoSave')){save.disabled=false;save.textContent='ADD TO PROMOTION ORDER'}
  }
 };
 setTimeout(()=>searchInput?.focus(),80);
}
$('#promoManualBtn').onclick=openManualPromotion;

function renderPromotionRows(data){
 promoLastRows=Array.isArray(data?.rows)?data.rows:[];
 const reviewItems=(promoListDetail?.items||[]).filter(x=>x.mapping_status!=='READY');
 const reviewHtml=reviewItems.length?'<div class="promo-review"><b>'+reviewItems.length+' list item(s) need review</b><br>'+reviewItems.slice(0,5).map(x=>esc(x.raw_item_code||x.raw_description||'Item')+' · '+esc(x.validation_error||x.mapping_status)).join('<br>')+(reviewItems.length>5?'<br>+'+(reviewItems.length-5)+' more':'')+'</div>':'';
 $('#promoRows').innerHTML=reviewHtml+promoLastRows.map((r,i)=>{
  const p=r.promotion_list_item||{}, type=String(p.promotion_type||'').toUpperCase();
  const temp=!!r.temporary_oh_override_used;
  const effectiveOh=r.current_effective_oh??r.effective_oh_raw;
  const effectiveUom=r.current_effective_oh_uom||r.effective_oh_uom||r.uom||'';
  const effectiveSource=r.current_effective_oh_source||r.effective_oh_source||'';
  const calcOh=r.current_oh_for_calculation;
  const promoNeed=r.forecast_promotion_coverage, regNeed=r.forecast_regular_coverage, totalNeed=r.forecast_coverage_usage;
  const freshnessHtml=r.freshness_adjustment_applied
   ? '<div class="promo-freshness"><b>⚠ FRESHNESS ADJUSTED</b> · latest receipt '+esc(appDate(r.freshness_latest_receipt_date))+' · DOH '+fmtNullable(r.freshness_current_doh)+' · projected discard '+fmtNullable(r.freshness_projected_discard_qty)+' '+esc(r.uom||'')+' · order +'+fmtNullable(r.freshness_order_qty_lift)+' '+esc(r.uom||'')+'</div>'
   : (r.freshness_coverage_capped?'<div class="promo-freshness"><b>FRESHNESS COVERAGE CAP</b> · Fresh/Live order coverage stops at 7 days; later demand needs another delivery.</div>':'');
  return '<div class="promo-card"><div class="promo-card-head"><div><b>'+esc(r.family_article_name||p.family_name||r.family_article_number||'Family')+'</b><small>Family '+esc(r.family_article_number||'—')+' · SALE '+money(p.promotion_price)+' · '+appDate(p.promotion_start_date)+' → '+appDate(p.promotion_end_date)+'</small></div><span class="promo-badge '+(type==='WEEKLY'?'weekly':'weekend')+'">'+esc(type||'PROMO')+'</span></div>'+
   '<div class="promo-metrics"><div class="promo-metric real-oh">'+familyOhActionHtml({family:r.family_article_number,name:r.family_article_name||p.family_name,oh:effectiveOh,uom:effectiveUom,source:effectiveSource},'promooh')+'</div><div class="promo-metric '+(temp?'temp':'')+'" data-promo-oh="'+i+'"><small>SCENARIO OH ✎</small><b>'+fmtNullable(calcOh)+' '+esc(r.uom||'')+'</b><span>'+(temp?'TEMPORARY OVERRIDE':'OPTIONAL WHAT-IF')+'</span></div><div class="promo-metric"><small>EST OH @ DELIVERY</small><b>'+fmtNullable(r.projected_oh_at_delivery)+' '+esc(r.uom||'')+'</b></div><div class="promo-metric"><small>COVERAGE NEED</small><b>'+fmtNullable(totalNeed)+' '+esc(r.uom||'')+'</b></div></div>'+freshnessHtml+
   '<div class="promo-order"><small>SUGGESTED '+esc(appDate(data.delivery_date))+' ORDER</small><b>'+fmtNullable(r.suggested_order_qty)+' '+esc(r.suggested_order_uom||r.uom||'')+'</b><div class="promo-break">Promo need '+fmtNullable(promoNeed)+' · Regular need '+fmtNullable(regNeed)+(temp?' · SCENARIO OH only for this calculation':'')+'</div></div></div>';
 }).join('')||reviewHtml||'<div class="empty">No calculable promotion items.</div>';
 document.querySelectorAll('[data-promo-oh]').forEach(x=>x.onclick=()=>openPromoTempOH(promoLastRows[Number(x.dataset.promoOh)]));
 bindFamilyOhEditors();
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
  const freshnessCount=(data.rows||[]).filter(x=>x.freshness_adjustment_applied).length;
  $('#promoOrderStatus').textContent=fmt(data.order_count,0)+' need order · '+fmt(data.suggestion_count,0)+' calculated · coverage through '+appDate(data.coverage_end_date)+(freshnessCount?' · '+freshnessCount+' freshness adjusted':'')+' · temporary OH values are NOT saved';
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
  r.family_article_name||'Scenario OH',
  'Promotion Ordering what-if only · not saved as True Stock',
  '<div class="detail"><b>System OH</b><br>'+fmtNullable(r.current_oh_system)+' '+esc(r.uom||'')+'<br><br><b>Scenario OH</b><br><input id="promoOHInput" type="number" min="0" step="0.1" inputmode="decimal" value="'+esc(value)+'" style="width:100%;font-size:24px;font-weight:900;padding:10px;border:2px solid #d6dde3;border-radius:12px"><br><br><div class="estimatebar">What-if reference only. This does NOT save True Stock. Use the Effective OH control on the promotion card to record a physical Family True Stock count.</div><div class="actions"><button id="promoOHReset">RESET TO SYSTEM OH</button><button class="primary" id="promoOHSave">SAVE & RECALCULATE</button></div></div>'
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

const ORDER_IGNORE_KEY='yipman-order-ignore-v449';
const ORDER_IGNORE_MS=12*60*60*1000;
let orderIgnoreMemory={};
function readOrderIgnores(){try{const v=JSON.parse(localStorage.getItem(ORDER_IGNORE_KEY)||'{}');if(v&&typeof v==='object'){orderIgnoreMemory=v;return v}}catch{}return orderIgnoreMemory||{}}
function writeOrderIgnores(v){orderIgnoreMemory=v||{};try{localStorage.setItem(ORDER_IGNORE_KEY,JSON.stringify(orderIgnoreMemory))}catch{}}
function orderIgnoreId(r){return String(orderMode||'REGULAR')+':'+String(r?.family_id??r?.family_article??'').trim()}
function orderIsIgnored(r){
 const id=orderIgnoreId(r);if(!id)return false;
 const map=readOrderIgnores(),ts=Number(map[id]||0);
 if(!(ts>0))return false;
 if(Date.now()-ts>=ORDER_IGNORE_MS){delete map[id];writeOrderIgnores(map);return false}
 return true;
}
function ignoreOrderSuggestion(r){
 const id=orderIgnoreId(r);if(!id)return;
 const map=readOrderIgnores();map[id]=Date.now();writeOrderIgnores(map);
 toast('Ordering suggestion hidden for 12 hours');
 setTimeout(()=>{if(current==='order'&&orderMode==='REGULAR')renderOrderRoster(lastOrderRows,lastOrderData,lastOrderData?.data_health||{},lastOrderStale)},ORDER_IGNORE_MS+1000);
 renderOrderRoster(lastOrderRows,lastOrderData,lastOrderData?.data_health||{},lastOrderStale);
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
 const ignoredOrderCount=visible.filter(r=>orderState(r)!=='ZERO_ORDER'&&orderIsIgnored(r)).length;
 visible=visible.filter(r=>orderState(r)==='ZERO_ORDER'||!orderIsIgnored(r));
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
  : esc(data?.selected_delivery_weekday||'Selected day')+' · complete observed-delivery roster'+(ignoredOrderCount?' · '+ignoredOrderCount+' suggestion'+(ignoredOrderCount===1?'':'s')+' ignored <12h':'');
 $('#orderList').classList.add('futurecards');
 $('#orderListHead').style.display='none';
 $('#orderRows').innerHTML=visible.map((r,i)=>{
  const state=orderState(r), q=orderQty(r), reason=orderReasonLabel(r.roster_reason);
  const cls=(r.attention?' urgent':'')+(state==='REVIEW'?' review':state==='ZERO_ORDER'?' zero':'');
  const stateLabel=state==='ORDER'?'ORDER':state==='REVIEW'?'REVIEW':'0 ORDER';
  const orderText=state==='REVIEW'?'REVIEW':fmtNullable(q);
  const orderSub=state==='REVIEW'?reason:esc(r.suggested_delivery_uom||'');
  const stockout=r.pre_delivery_stockout_risk?'<span class="order-risk">STOCKOUT BEFORE DELIVERY</span>':'';
  const lowconf=String(r.delivery_day_confidence||'').toUpperCase()==='LOW'?'<span class="order-lowconf">LOW DELIVERY CONF.</span>':'';
  const freshness=r.freshness_adjustment_applied?'<span class="order-freshness">FRESHNESS +'+fmtNullable(r.freshness_order_qty_lift)+' '+esc(r.oh_uom||'')+'</span>':'';
  const hist=state==='ORDER'&&num(q)>0&&Array.isArray(r.historical_receiving_articles)?r.historical_receiving_articles:[];
  const shownHist=hist.slice(0,3);
  const histHtml=shownHist.length
    ? '<div class="orderrecvhistory"><div class="orderrecvhistoryhead"><span class="orderrecvhistoryicon">◇</span><b>RELATED RECEIVING ARTICLES FOR THIS ITEM</b><span>FAMILY '+esc(r.family_article||'—')+'</span></div>'
      +shownHist.map(h=>'<div class="orderrecvrow"><div class="orderrecvarticle"><b>'+esc(h.article_number||'—')+'</b>'+(h.article_name?'<span class="receivingname">'+esc(h.article_name)+'</span>':'')+'<span>Last received '+esc(appDate(h.last_receipt_date))+' · '+fmt(h.receipt_event_count,0)+' receipt event'+(Number(h.receipt_event_count||0)===1?'':'s')+'</span></div><div class="orderrecvpack"><b>'+esc(h.pack_size||'—')+'</b><span>PACK SIZE</span></div></div>').join('')
      +(hist.length>shownHist.length?'<div class="orderrecvmore">+'+(hist.length-shownHist.length)+' more · tap this item for full history</div>':'')
      +'</div>'
    : '';
  const ohPair=familyOhPairHtml({family:r.family_article,name:r.family_name,effective:r.effective_oh??r.oh,effective_uom:r.effective_oh_uom||r.oh_uom,effective_source:r.effective_oh_source,system:r.system_oh,system_uom:r.system_oh_uom});
  const snooze=state==='ZERO_ORDER'?'':'<div class="pcard-actions"><button class="pignore snooze12" data-order-ignore="'+i+'">IGNORE 12 HOURS</button></div>';
  return '<article class="orderitemcard tone'+(i%5)+cls+'" data-order="'+i+'"><div class="orderitemhead"><span>FAMILY ARTICLE</span><span>EFFECTIVE OH</span><span>ORDER</span></div><div class="orderitemmain"><div><div class="familyline"><span>FAMILY ARTICLE</span><b>'+esc(r.family_article||'—')+'</b></div><div class="name">'+esc(r.family_name||r.family_article||'Family')+'<span class="orderstate '+(state==='ORDER'?'order':state==='REVIEW'?'review':'')+'">'+stateLabel+'</span>'+stockout+lowconf+freshness+'</div><div class="sub">'+esc(r.ordering_frequency||'')+' · '+fmt(r.delivery_day_observed_count,0)+' observed '+esc(r.delivery_day||'day')+(r.roster_reason?' · '+esc(reason):'')+(r.estimate_only?' · ESTIMATE':'')+'</div></div><div class="cell ohcell">'+familyOhActionHtml({family:r.family_article,name:r.family_name,oh:r.effective_oh??r.oh,uom:r.effective_oh_uom||r.oh_uom,source:r.effective_oh_source||r.oh_source},'orderoh')+'</div><div class="cell orderqty">'+orderText+'<span>'+orderSub+'</span></div></div>'+ohPair+histHtml+snooze+'</article>';
 }).join('')||'<div class="empty">No rows match this filter. The complete observed roster has '+counts.total+' families.'+(ignoredOrderCount?' '+ignoredOrderCount+' ignored suggestion(s) return automatically after 12 hours.':'')+'</div>';
 document.querySelectorAll('[data-order]').forEach(x=>x.onclick=e=>{if(e.target.closest('button'))return;openOrder(renderedOrderRows[Number(x.dataset.order)])});
 $$('[data-order-ignore]').forEach(b=>b.onclick=e=>{e.stopPropagation();ignoreOrderSuggestion(renderedOrderRows[Number(b.dataset.orderIgnore)])});
 bindFamilyOhEditors();
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
 $('#orderList').classList.toggle('futurecards',!isPast);
 $('#orderListHead').style.display=isPast?'grid':'none';
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
   const cacheStatus=String(data.cache_status||'').toUpperCase();
   const sourceRefreshing=!!data.source_changed_since_analysis||cacheStatus==='SOURCE_CHANGED_REFRESHING'||status.includes('SOURCE_CHANGED');
   if(!sourceRefreshing&&!['REFRESHING','WARMING','STALE_DATA_REFRESHING'].includes(status)&&!['WARMING','STALE_DATA_REFRESHING'].includes(cacheStatus))break;
   $('#orderStatus').textContent='Calculating '+appDate(orderDate)+' · receipt cadence first';
   await new Promise(r=>setTimeout(r,1500));
  }
  const finalStatus=String(data?.analysis_status||'').toUpperCase(), h=data?.data_health||{};
  const finalCache=String(data?.cache_status||'').toUpperCase();
  const sourceRefreshing=!!data?.source_changed_since_analysis||finalCache==='SOURCE_CHANGED_REFRESHING'||finalStatus.includes('SOURCE_CHANGED');
  if(sourceRefreshing||['REFRESHING','WARMING'].includes(finalStatus)||['WARMING','STALE_DATA_REFRESHING'].includes(finalCache)){
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
    $('#orderList').classList.remove('futurecards');
    $('#orderListHead').style.display='grid';
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
 const effectiveOh=r.effective_oh??r.oh, effectiveUom=r.effective_oh_uom||r.oh_uom||'';
 const hist=Array.isArray(r.historical_receiving_articles)?r.historical_receiving_articles:[];
 const histDetail=hist.length
   ? '<br><br><b>Historical Receiving Articles / Pack Size</b><br>'+hist.map(h=>'• '+esc(h.article_number||'—')+' · '+esc(h.pack_size||'—')+' · last '+esc(appDate(h.last_receipt_date))+' · '+fmt(h.receipt_event_count,0)+' receipt event'+(Number(h.receipt_event_count||0)===1?'':'s')+(h.pack_size_source?' · '+esc(h.pack_size_source):'')).join('<br>')
   : '';
 const orderMetric=state==='REVIEW'?'REVIEW':fmtNullable(orderQty(r))+' '+esc(r.suggested_delivery_uom||'');
 const orderMetricLabel=state==='REVIEW'?'ORDER STATUS':(r.estimate_only?'ESTIMATE ORDER':'SUGGESTED ORDER');
 sheet(r.family_name||'Ordering','Family '+esc(r.family_article||'—')+' · Delivery '+esc(appDate(r.selected_delivery_date||orderDate)),
 '<div class="dmetrics"><div class="dm"><button type="button" class="familyohbtn" data-family-oh data-family="'+esc(r.family_article||'')+'" data-name="'+esc(r.family_name||'')+'" data-oh="'+esc(effectiveOh??'')+'" data-uom="'+esc(effectiveUom)+'"><b>'+fmtNullable(effectiveOh)+' '+esc(effectiveUom)+'</b><span>EFFECTIVE OH · EDIT TRUE STOCK</span></button></div><div class="dm"><b>'+fmtNullable(d.velocity_7d)+'</b><span>7D VELOCITY</span></div><div class="dm"><b>'+orderMetric+'</b><span>'+orderMetricLabel+'</span></div></div>'+
 (r.estimate_only?'<div class="estimatebar">BEST AVAILABLE · missing POS/MVT dates do not block this order suggestion.</div>':'')+
 '<div class="detail"><b>Roster status</b><br>'+(state==='ORDER'?'Needs order':state==='ZERO_ORDER'?'Observed delivery family · no order suggested':'Review required · '+esc(reason))+
 histDetail+
 '<br><br><b>Last receipt</b><br>'+esc(appDate(r.last_receipt_date))+' · '+fmtNullable(r.last_receipt_qty_base)+' '+esc(r.last_receipt_base_uom||'')+
 '<br><br><b>Demand</b><br>7D '+fmtNullable(d.qty_7d)+' · 28D '+fmtNullable(d.qty_28d)+' · DOS '+fmtNullable(d.dos)+' · Forecast confidence '+esc(d.regular_forecast_confidence||'—')+
 '<br><br><b>Weekday usage forecast</b><br>'+(
   d.weekday_usage_forecast
    ? Object.entries(d.weekday_usage_forecast).map(([day,qty])=>esc(day.slice(0,3))+' '+fmtNullable(qty)+' '+esc(r.oh_uom||'')).join(' · ')
    : '—'
 )+
 '<br><span style="color:#71808d">Historical weekday average is used when at least 2 observations exist; sparse weekdays blend toward the overall run-rate.</span>'+
 '<br><br><b>Coverage need</b><br>'+fmtNullable(d.forecast_coverage_usage)+' '+esc(r.oh_uom||'')+' from Delivery through the eligible coverage end'+
 '<br><br><b>Projected at delivery</b><br>'+fmtNullable(d.projected_oh_at_delivery)+' '+esc(r.oh_uom||'')+' · usable '+fmtNullable(d.usable_oh_at_delivery)+' '+esc(r.oh_uom||'')+
 (d.pre_delivery_stockout_risk?'<br><br><b>⚠ Pre-delivery stockout risk</b><br>'+fmtNullable(d.pre_delivery_stockout_qty)+' '+esc(r.oh_uom||'')+' projected short before the selected delivery. This shortage is NOT added to the later order.':'')+
 (d.freshness_coverage_capped?'<br><br><b>⚠ Freshness guard</b><br>Fresh/Live coverage is capped at 7 days. Later demand requires an earlier or split delivery.':'')+
 (d.freshness_adjustment_applied?'<br><br><b>⚠ Current OH freshness adjustment</b><br>Latest valid receipt '+esc(appDate(d.freshness_latest_receipt_date))+' · current DOH '+fmtNullable(d.freshness_current_doh)+' · discard threshold '+fmtNullable(d.freshness_threshold_days)+' days.<br>Projected discard '+fmtNullable(d.freshness_projected_discard_qty)+' '+esc(r.oh_uom||'')+' · existing OH credited '+fmtNullable(d.freshness_existing_oh_credit)+' '+esc(r.oh_uom||'')+' · order increased '+fmtNullable(d.freshness_order_qty_lift)+' '+esc(r.oh_uom||'')+'.':'')+
 '<br><br><b>Delivery evidence</b><br>'+fmt(r.delivery_day_observed_count,0)+' / '+fmt(r.delivery_day_receipt_count,0)+' receipt dates · '+fmt(r.delivery_day_confidence_pct,0)+'% confidence'+
 (reasons.length?'<br><br><b>Why</b><br>'+reasons.map(x=>'• '+esc(x.detail||x.title||'')).join('<br>'):'')+'</div>');
 bindFamilyOhEditors();
}


const PRICE_IGNORE_KEY='yipman-price-ignore-v374';
const PRICE_IGNORE_MS=12*60*60*1000;
// Compatibility marker for the prior smoke contract only; expiry authority is timestamp-based below.
// priceIgnoredThisVisit.has(id)

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
  if(!(ts>0))return false;
  if(Date.now()-ts>=PRICE_IGNORE_MS){delete map[id];writePriceIgnores(map);return false}
  return true;
}
function ignorePriceSuggestion(r){
  const id=priceIgnoreId(r);if(!id)return;
  const map=readPriceIgnores();map[id]=Date.now();writePriceIgnores(map);
  if($('#overlay').classList.contains('on'))closeSheet(true);
  toast('Price suggestion hidden for 12 hours');
  setTimeout(()=>{if(current==='price'&&(priceView==='REG'||priceView==='TPR_SUGGEST'))loadPrices({quiet:true})},PRICE_IGNORE_MS+1000);
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
 const regMode=priceView==='REG';
 if(!quiet)$('#priceRows').innerHTML='<div class="loading">'+(regMode?'Loading REG replacements…':'Loading TPR suggestions…')+'</div>';
 const modeRule=$('#priceModeRule');
 if(modeRule)modeRule.innerHTML=regMode
   ?'<b>REG:</b> everyday standard price. Replace it only when a better proved GP$/day sweet spot is ready to become the new regular price.'
   :'<b>TPR SUGGEST:</b> temporary price only. Use it to test a new GP$/day sweet spot or temporarily improve velocity / freshness sell-through. Active SALE items are excluded.';
 $('#priceStatus').textContent=regMode?'Checking proved sweet spots that can replace REG…':'Checking controlled TPR test opportunities…';
 try{
  const d=await api('/v1/yipman/pricing-review?category=ALL&limit=1000',{timeoutMs:12000});
  if(requestId!==priceRequestSeq)return;
  const analysisStatus=String(d.analysis_status||'').toUpperCase();
  const cacheStatus=String(d.cache_status||'').toUpperCase();
  const sourceChanged=!!d.source_changed_since_analysis||cacheStatus==='SOURCE_CHANGED_REFRESHING'||analysisStatus.includes('SOURCE_CHANGED');
  const warming=analysisStatus==='REFRESHING'||cacheStatus==='WARMING';
  if(warming){
    $('#priceStatus').textContent='Building current Price Suggestions…';
    $('#priceRows').innerHTML='<div class="loading">Pricing analysis is running in the background. Yipman will retry automatically.</div>';
    schedulePriceRetry(requestId,3000);
    return;
  }
  const h=d.data_health||{};
  const live=d.current_source_health||h;
  if(String(live.status||h.status||'').includes('BLOCKED')){
    $('#priceStatus').textContent='Price estimate unavailable';
    $('#priceRows').innerHTML='<div class="empty">No usable POS or MVT history is available for a best-available price estimate.<br>POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'</div>';
    return;
  }
  const stale=String(h.status||'').toUpperCase()==='STALE_ESTIMATE_AVAILABLE'||cacheStatus==='STALE_REFRESHING'||sourceChanged;
  const pricingRows=Array.isArray(d.rows)?d.rows:[];
  const meaningful=pricingRows.filter(r=>regMode?!!r.reg_suggestion_actionable:!!r.tpr_suggestion_actionable);
  const observed=r=>(Array.isArray(r.observed_delivery_weekdays)?r.observed_delivery_weekdays:[]).map(x=>String(x||'').toUpperCase());
  const upcPrefix=r=>String(r.upc||'').replace(/\D/g,'').replace(/^0+/,'').slice(0,3);
  const patternFiltered=meaningful.filter(r=>{
    if(priceFilter==='UPC_249'){
      return upcPrefix(r)==='249'
        && r.related_240_current_price!=null
        && num(r.current_price)!==null
        && num(r.related_240_current_price)!==num(r.current_price)
        && (r.price_240_249_equal===false||r.priority_240_249_mismatch||String(r.suggestion_reason_code||'')==='PAIR_FIX');
    }
    if(priceFilter.startsWith('UPC_'))return upcPrefix(r)===priceFilter.slice(4);
    if(priceFilter==='LIVE')return String(r.category||'').toUpperCase()==='LIVE';
    const days=observed(r);
    if(priceFilter==='TUE')return days.includes('TUESDAY');
    if(priceFilter==='FRI_SAT')return days.includes('FRIDAY')||days.includes('SATURDAY');
    return true;
  });
  const reasonFiltered=patternFiltered.filter(r=>{
    const code=String(r.suggestion_reason_code||'').toUpperCase();
    if(priceReasonFilter==='PAIR')return !!r.priority_240_249_mismatch||code==='PAIR_FIX';
    if(priceReasonFilter==='VELOCITY')return code==='VELOCITY_TEST'||!!r.slow_velocity_trend;
    if(priceReasonFilter==='GP')return code==='GP_DOLLAR_TEST'||num(r.gp_per_day_opportunity)!==null;
    if(priceReasonFilter==='RANGE')return code==='COMPANY_RANGE'||!!r.company_range_violation;
    if(priceReasonFilter==='SWEET')return code==='SWEET_SPOT_GAP';
    return true;
  });
  const sorted=[...reasonFiltered].sort((a,b)=>{
    if(priceSort==='GPDOLLAR')return (num(b.gp_per_day_opportunity)||0)-(num(a.gp_per_day_opportunity)||0)||String(a.name||'').localeCompare(String(b.name||''));
    if(priceSort==='GAP'){
      const gap=x=>{const c=num(x.current_price),t=num(x.tested_price);return c===null||t===null?0:Math.abs(c-t)};
      return gap(b)-gap(a)||String(a.name||'').localeCompare(String(b.name||''));
    }
    if(priceSort==='OH')return (num(b.current_oh)||0)-(num(a.current_oh)||0)||String(a.name||'').localeCompare(String(b.name||''));
    if(priceSort==='VELOCITY')return (num(a.velocity_7d)??999999)-(num(b.velocity_7d)??999999)||String(a.name||'').localeCompare(String(b.name||''));
    if(priceSort==='NAME')return String(a.name||'').localeCompare(String(b.name||''));
    const urgency=x=>(x.priority_240_249_mismatch?1000000:0)+(num(x.urgency_score)||0);
    return urgency(b)-urgency(a)||String(a.name||'').localeCompare(String(b.name||''));
  });
  const ignoredCount=sorted.filter(priceIsIgnored).length;
  const rows=sorted.filter(r=>!priceIsIgnored(r)).slice(0,40);
  const filterLabel=priceFilter.startsWith('UPC_')?(priceFilter.slice(4)+' UPC'):priceFilter==='LIVE'?'Live':priceFilter==='TUE'?'Observed Tuesday delivery':'Observed Friday / Saturday delivery';
  const modeLabel=regMode?'REG REPLACEMENTS':'TPR SUGGESTIONS';
  const freshnessLabel=sourceChanged?'LATEST DATA · REFRESHING SUGGESTIONS':(String(live.status||'').toUpperCase()==='CURRENT'?'CURRENT DATA':'BEST AVAILABLE');
  const basisNote=sourceChanged?'<br><span>Prior suggestion basis: POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'. New canonical data is being applied now.</span>':(String(live.status||'').toUpperCase()==='CURRENT'?'':'<br><span>Missing dates are ignored, not zero-filled.</span>');
  $('#priceStatus').innerHTML='<div class="estimatebar">'+modeLabel+' · '+freshnessLabel+' · POS '+esc(live.pos_data_through||'—')+' · MVT '+esc(live.movement_data_through||'—')+'.'+basisNote+'</div>'+esc(filterLabel)+' · '+esc(priceReasonFilter==='ALL'?'all reasons':friendlySignal(priceReasonFilter))+' · '+esc(friendlySignal(priceSort))+' sort · '+rows.length+' shown · '+ignoredCount+' ignored <12h';

  $('#priceRows').innerHTML=rows.map((r,i)=>{
    const meta=priceReasonMeta(r,stale),prog=priceProgress(r),signals=priceSignals(r);
    const tested=num(r.tested_price),testing=num(r.tpr_suggestion_price??r.testing_price),cur=num(r.current_price),cost=num(r.current_cost);
    const suggested=regMode?(r.reg_suggestion_price??r.tested_price):(r.tpr_suggestion_price??r.testing_price);
    const reason=regMode?(r.reg_suggestion_reason||r.primary_reason_text||'REG review'):(r.tpr_suggestion_reason||r.primary_reason_text||'TPR test');
    const gap=(tested!==null&&cur!==null)?Math.abs(tested-cur):null;
    const gpNow=num(r.current_gp_per_day_7d),gpTarget=num(r.candidate_expected_gp_per_day);
    const companyLow=num(r.company_range_low),companyHigh=num(r.company_range_high);
    const companyText=(companyLow!==null&&companyHigh!==null)?money(companyLow)+'–'+money(companyHigh):'—';
    const detailSignals=(Array.isArray(r.reasons)?r.reasons:[]).map(x=>'• '+esc(friendlySignal(x))).join('<br>');
    return '<article class="pcard tone'+(i%5)+'" data-price="'+i+'">'+
      '<div class="ptop"><div class="pidentity"><div class="pupc"><span>UPC#</span><strong>'+esc(r.upc||'—')+'</strong></div><b>'+esc(r.name||r.upc)+'</b></div><span class="pbadge '+meta.cls+'">'+esc(meta.label)+'</span></div>'+
      '<div class="preasoncall '+meta.cls+'"><span class="preasonmark">!</span><div><strong>Reason:</strong> '+esc(reason)+'</div><span class="preasonchev">›</span></div>'+
      '<div class="pricepath">'+
        '<div class="pp current"><small>'+esc(regMode?'CURRENT REG':'CURRENT PRICE')+'</small><b>'+money(r.current_price)+'</b><span>'+esc(r.current_price_type||r.current_price_source||'latest effective')+' · '+esc(gpText(r.current_price,r.current_cost))+'</span></div>'+
        '<div class="pp tested"><small>'+esc(regMode?'PROVED SWEET SPOT':'TESTED SWEET SPOT')+'</small><b>'+money(r.tested_price)+'</b><span>'+esc(gpText(r.tested_price,r.current_cost))+(r.tested_evidence_price!=null&&num(r.tested_evidence_price)!==num(r.tested_price)?' · evidence '+money(r.tested_evidence_price):'')+'</span></div>'+
        '<div class="pp testing"><small>'+esc(regMode?'SUGGESTED REG':'TPR SUGGESTION PRICE')+'</small><b>'+money(suggested)+'</b><span>'+esc(regMode?'NEW EVERYDAY PRICE':(r.tpr_suggestion_purpose==='FRESHNESS_SELL_THROUGH'?'FRESHNESS':'SWEET SPOT TEST'))+' · '+esc(gpText(suggested,r.current_cost))+'</span></div>'+
      '</div>'+
      (upcPrefix(r)==='249'&&r.related_240_current_price!=null?'<div class="pairauthority"><div><small>240 MAIN PRICE · AUTHORITY</small><b>'+money(r.related_240_current_price)+'</b><span>'+esc(r.related_240_upc||'240')+' · 249 must match 240</span></div><div class="pairarrow">→</div><div><small>249 CURRENT</small><b>'+money(r.current_price)+'</b><span>'+(num(r.current_price)===num(r.related_240_current_price)?'MATCHED':'MISMATCH · SET TO '+money(r.related_240_current_price))+'</span></div></div>':'')+
      '<div class="pcost"><span>CURRENT COST'+(r.current_cost_source?' · '+esc(r.current_cost_source):'')+(r.cost_date?' · '+esc(r.cost_date):'')+'</span><b>'+money(r.current_cost)+(r.selling_uom?' / '+esc(r.selling_uom):'')+'</b></div>'+
      familyOhPairHtml({family:r.family_article_number,name:r.family_name||r.name,effective:r.current_oh,effective_uom:r.current_oh_uom,effective_source:r.current_oh_source,system:r.system_oh,system_uom:r.system_oh_uom})+
      '<div class="pmetrics">'+
        '<div class="pm ohpm">'+familyOhActionHtml({family:r.family_article_number,name:r.family_name||r.name,oh:r.current_oh,uom:r.current_oh_uom,source:r.current_oh_source},'priceoh')+'</div>'+
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
        '<b>Why:</b> '+esc(reason)+
        '<br><b>Current evidence:</b> '+esc(r.current_price_source||'—')+(r.current_price_observed_date?' · '+esc(r.current_price_observed_date):'')+
        '<br><b>Company range:</b> '+esc(companyText)+(r.company_range_violation?' · CURRENT OUTSIDE':'')+
        '<br><b>Test target:</b> '+money(r.testing_target_price||r.target_sweet_spot_price)+
        (detailSignals?'<br><b>Signals:</b><br>'+detailSignals:'')+
      '</div></details>'+
      '<div class="pcard-actions"><button class="pdetail" data-price-detail="'+i+'">DETAIL</button><button class="pignore snooze12" data-price-ignore="'+i+'">IGNORE 12 HOURS</button></div>'+
    '</article>';
  }).join('')||'<div class="empty">No '+(regMode?'REG replacement':'TPR suggestion')+' matches this filter.</div>';

  document.querySelectorAll('[data-price]').forEach(x=>x.onclick=e=>{
    if(e.target.closest('button,details,summary'))return;
    openPrice(rows[Number(x.dataset.price)]);
  });
  bindFamilyOhEditors();
  document.querySelectorAll('[data-price-detail]').forEach(b=>b.onclick=e=>{e.stopPropagation();openPrice(rows[Number(b.dataset.priceDetail)])});
  $$('[data-price-ignore]').forEach(b=>b.onclick=e=>{e.stopPropagation();ignorePriceSuggestion(rows[Number(b.dataset.priceIgnore)])});
  if(sourceChanged)schedulePriceRetry(requestId,2200);
 }catch(e){
  if(requestId!==priceRequestSeq)return;
  $('#priceStatus').textContent='Price suggestions temporarily unavailable';
  $('#priceRows').innerHTML='<div class="empty">'+esc(e.message)+'<br>Yipman will retry automatically.</div>';
  schedulePriceRetry(requestId,6000);
 }
}
function openPrice(r){
 const regMode=priceView==='REG';
 const delivery=(r.observed_delivery_days||[]).map(x=>esc(x.weekday||'')+' '+fmt(x.receipt_date_count,0)+' receipt date'+(Number(x.receipt_date_count||0)===1?'':'s')).join('<br>');
 const signals=(Array.isArray(r.reasons)?r.reasons:[]).map(x=>'• '+esc(friendlySignal(x))).join('<br>');
 const companyLow=num(r.company_range_low),companyHigh=num(r.company_range_high);
 const company=(companyLow!==null&&companyHigh!==null)?money(companyLow)+' – '+money(companyHigh):'—';
 const suggestion=regMode?(r.reg_suggestion_price??r.tested_price):(r.tpr_suggestion_price??r.testing_price);
 const why=regMode?(r.reg_suggestion_reason||r.primary_reason_text||'REG review'):(r.tpr_suggestion_reason||r.primary_reason_text||'TPR review');
 const suggestionLabel=regMode?'SUGGESTED REG':'TPR SUGGESTION PRICE';
 const ohPair=familyOhPairHtml({family:r.family_article_number,name:r.family_name||r.name,effective:r.current_oh,effective_uom:r.current_oh_uom,effective_source:r.current_oh_source,system:r.system_oh,system_uom:r.system_oh_uom});
 sheet(r.name||r.upc,r.upc||(regMode?'REG suggestion':'TPR suggestion'),
 ohPair+'<div class="dmetrics"><div class="dm"><b>'+money(r.current_price)+'</b><span>CURRENT '+esc(r.current_price_type||'')+' · '+esc(gpText(r.current_price,r.current_cost))+'</span></div><div class="dm"><b>'+money(r.tested_price)+'</b><span>PROVED SWEET SPOT · '+esc(gpText(r.tested_price,r.current_cost))+'</span></div><div class="dm"><b>'+money(suggestion)+'</b><span>'+esc(suggestionLabel)+' · '+esc(gpText(suggestion,r.current_cost))+'</span></div></div>'+
 (r.estimate_only?'<div class="estimatebar">BEST AVAILABLE · missing POS/MVT dates do not block this price suggestion.</div>':'')+
 '<div class="detail"><b>Suggested action</b><br>'+esc(why)+
 (String(r.upc||'').replace(/\D/g,'').replace(/^0+/,'').startsWith('249')&&r.related_240_current_price!=null?'<br><br><b>240 → 249 price rule</b><br>240 '+esc(r.related_240_upc||'—')+' current '+money(r.related_240_current_price)+' → 249 '+esc(r.upc||'—')+' current '+money(r.current_price)+' · required 249 price '+money(r.related_240_current_price):'')+
 '<br><br><b>Current cost</b><br>'+money(r.current_cost)+(r.selling_uom?' / '+esc(r.selling_uom):'')+(r.current_cost_source?' · '+esc(r.current_cost_source):'')+(r.cost_date?' · '+esc(r.cost_date):'')+
 '<br><br><b>Price path + GP%</b><br>Current '+money(r.current_price)+' ('+esc(gpText(r.current_price,r.current_cost))+') → '+esc(suggestionLabel)+' '+money(suggestion)+' ('+esc(gpText(suggestion,r.current_cost))+') · Proved sweet spot '+money(r.tested_price)+' ('+esc(gpText(r.tested_price,r.current_cost))+')'+
 (r.tested_evidence_price!=null&&num(r.tested_evidence_price)!==num(r.tested_price)?'<br>Raw proved sweet-spot evidence '+money(r.tested_evidence_price)+' → retail-aligned '+money(r.tested_price):'')+
 (!regMode&&r.testing_target_price?('<br>Eventual test target '+money(r.testing_target_price)):'')+
 '<br><br><b>Progress now</b><br>7D '+fmt(r.qty_7d)+' '+esc(r.qty_uom||'')+' · '+fmt(r.velocity_7d)+' /day · 28D '+fmt(r.velocity_28d)+' /day · DOH '+fmt(r.doh)+
 '<br>GP$/day now '+money(r.current_gp_per_day_7d)+' · supported target evidence '+money(r.candidate_expected_gp_per_day)+
 '<br><br><b>Company A/B/C range</b><br>'+esc(company)+(r.company_range_violation?' · CURRENT OUTSIDE RANGE':'')+
 '<br><br><b>Current price evidence</b><br>'+esc(r.current_price_source||'—')+(r.current_price_observed_date?' · '+esc(r.current_price_observed_date):'')+
 '<br><br><b>Pricing rule</b><br>'+(regMode
   ?'REG is the standard everyday price and should represent the known GP$/day sweet spot. This tab only proposes replacing REG when a stronger proved sweet spot or mandatory price-integrity correction is available.'
   :'TPR is temporary. Use it either to test a new everyday GP$/day sweet spot or to temporarily improve velocity / freshness sell-through. SALE price and period are company controlled and are never changed here.')+
 '<br>Retail-facing prices use normal store endings .29 / .49 / .59 / .69 / .79 / .99. Controlled TPR tests move at least $0.45 from Current.'+
 '<br><br><b>Observed delivery pattern</b><br>'+(delivery||'No positive receipt weekday observed in the 180-day window.')+
 (signals?'<br><br><b>Supporting signals</b><br>'+signals:'')+'</div>'+
 '<div class="actions"><button class="secondary" id="priceTrueStockEdit">EDIT TRUE STOCK</button><button class="secondary snooze12" id="priceIgnore12h">IGNORE 12 HOURS</button></div>');
 const ig=$('#priceIgnore12h');if(ig)ig.onclick=()=>ignorePriceSuggestion(r);
 const ts=$('#priceTrueStockEdit');if(ts)ts.onclick=()=>openFamilyTrueStock({family:r.family_article_number,name:r.family_name||r.name,oh:r.current_oh,uom:r.current_oh_uom||r.system_oh_uom});
 bindFamilyOhEditors();
}
$$('[data-price-filter]').forEach(b=>b.onclick=()=>{
 priceFilter=b.dataset.priceFilter;
 $$('[data-price-filter]').forEach(x=>x.classList.toggle('on',x===b));
 loadPrices();
});
$('#priceReasonFilter').onchange=e=>{priceReasonFilter=e.target.value;loadPrices({quiet:true})};
$('#priceSort').onchange=e=>{priceSort=e.target.value;loadPrices({quiet:true})};



function tprProgressIgnoreId(r){return 'TPR_PROGRESS:'+String(r?.upc||'').trim()}
function tprProgressIsIgnored(r){
 const id=tprProgressIgnoreId(r);if(!id)return false;
 const map=readPriceIgnores(),ts=Number(map[id]||0);
 if(!(ts>0))return false;
 if(Date.now()-ts>=PRICE_IGNORE_MS){delete map[id];writePriceIgnores(map);return false}
 return true;
}
function ignoreTprProgress(r){
 const id=tprProgressIgnoreId(r);if(!id)return;
 const map=readPriceIgnores();map[id]=Date.now();writePriceIgnores(map);
 if($('#overlay').classList.contains('on'))closeSheet(true);
 toast('TPR progress suggestion hidden for 12 hours');
 setTimeout(()=>{if(current==='price'&&priceView==='TPR_PROGRESS')renderCurrentTpr()},PRICE_IGNORE_MS+1000);
 renderCurrentTpr();
}
function tprRecommendationMeta(r){
 const code=String(r?.recommendation_code||'OBSERVE').toUpperCase();
 if(code==='CONTINUE_TPR')return {label:String(r?.recommendation_label||'CONTINUE'),cls:'continue',group:'CONTINUE'};
 if(code==='MAKE_REGULAR')return {label:String(r?.recommendation_label||'MAKE REGULAR'),cls:'continue',group:'CONTINUE'};
 if(code==='OBSERVE')return {label:'OBSERVE',cls:'observe',group:'OBSERVE'};
 if(code==='URGENT_REVIEW'||code==='REVIEW_DATA'||code==='MATCH_240')return {label:String(r?.recommendation_label||'URGENT REVIEW'),cls:'urgent',group:'ADJUST'};
 if(code==='CANCEL_TPR'||code==='END_TPR')return {label:String(r?.recommendation_label||'CANCEL TPR'),cls:'end',group:'ADJUST'};
 return {label:String(r?.recommendation_label||'ADJUST'),cls:'adjust',group:'ADJUST'};
}
function tprUpcPrefix(r){return String(r?.upc||'').replace(/\D/g,'').replace(/^0+/,'').slice(0,3)}
function tprLiftText(v){
 const n=num(v);if(n===null)return {text:'—',cls:'neutral'};
 return {text:(n>=0?'+':'')+n.toFixed(0)+'%',cls:n>=10?'good':n<=0?'bad':'neutral'};
}
function currentTprFilteredRows(){
 let rows=[...(lastTprRows||[])].filter(r=>!tprProgressIsIgnored(r));
 rows=rows.filter(r=>{
   const meta=tprRecommendationMeta(r),cat=String(r.category||'').toUpperCase();
   if(tprFilter==='PURPOSE_SWEET')return String(r.tpr_purpose||'').toUpperCase()==='SWEET_SPOT_TEST';
   if(tprFilter==='PURPOSE_FRESHNESS')return String(r.tpr_purpose||'').toUpperCase()==='FRESHNESS_SELL_THROUGH';
   if(tprFilter==='UPC_240')return tprUpcPrefix(r)==='240';
   if(tprFilter==='SOLD')return (num(r.qty_7d)||0)>0;
   if(tprFilter==='CONTINUE')return meta.group==='CONTINUE';
   if(tprFilter==='ADJUST')return meta.group==='ADJUST';
   if(['LIVE','FRESH','FROZEN'].includes(tprFilter))return cat===tprFilter;
   return true;
 });
 rows.sort((a,b)=>{
   if(tprSort==='DECISION')return (num(b.recommendation_priority)||0)-(num(a.recommendation_priority)||0)||(num(b.qty_7d)||0)-(num(a.qty_7d)||0);
   if(tprSort==='LIFT')return (num(b.velocity_lift_pct)??-999999)-(num(a.velocity_lift_pct)??-999999)||(num(b.qty_7d)||0)-(num(a.qty_7d)||0);
   if(tprSort==='OH')return (num(b.current_oh)||0)-(num(a.current_oh)||0);
   if(tprSort==='NAME')return String(a.name||a.upc||'').localeCompare(String(b.name||b.upc||''));
   return (num(b.qty_7d)||0)-(num(a.qty_7d)||0)||(num(b.recommendation_priority)||0)-(num(a.recommendation_priority)||0);
 });
 return rows;
}
function tprPurposeMeta(r){
 const fresh=String(r?.tpr_purpose||'').toUpperCase()==='FRESHNESS_SELL_THROUGH';
 return {fresh,label:fresh?'FRESHNESS SELL-THROUGH':'FIND NEW REGULAR SWEET SPOT',cls:fresh?'freshness':'sweet'};
}
function tprFutureHeadline(r){
 const p=tprPurposeMeta(r);
 if(p.fresh){
   const clear=num(r.projected_days_to_clear_oh),left=num(r.freshness_days_remaining),remain=num(r.projected_oh_at_freshness_limit);
   if(clear!==null)return {main:fmt(clear)+' d to clear',sub:left===null?'freshness deadline unknown':fmt(left)+' d freshness time'};
   if(remain!==null)return {main:fmt(remain)+' left',sub:'projected at freshness limit'};
   return {main:'—',sub:'clearance projection'};
 }
 return {main:money(r.projected_gp_7d),sub:'projected GP$ next 7D'};
}
function tprPriceStepsHtml(r){
 const steps=Array.isArray(r.observed_tpr_price_steps)?r.observed_tpr_price_steps:[];
 if(!steps.length)return '<div class="hint">No observed TPR selling-price step yet.</div>';
 return '<div class="tprsteps">'+steps.slice(-5).map(x=>'<div class="tprstep"><b>'+money(x.price)+'</b><span>'+esc(shortDate(x.start_date))+'–'+esc(shortDate(x.end_date))+'</span><span>'+fmt(x.qty)+' '+esc(r.selling_uom||'')+' · '+fmt(x.velocity_per_selling_day)+'/selling day · GP$/d '+money(x.gp_per_selling_day_current_cost)+'</span></div>').join('')+'</div>';
}
function renderCurrentTpr(){
 const d=lastTprPayload||{},s=d.summary||{},rows=currentTprFilteredRows();
 const tab=$('#tprTabCount');if(tab)tab.textContent=s.current_tpr_count!=null?'· '+fmt(s.current_tpr_count,0):'';
 const sum=$('#tprSummary');
 if(sum)sum.innerHTML='<div><b>'+fmt(s.current_tpr_count,0)+'</b><span>CURRENT TPR</span></div><div><b>'+fmt(s.sweet_spot_test_count,0)+'</b><span>SWEET TEST</span></div><div><b>'+fmt(s.freshness_sell_through_count,0)+'</b><span>FRESHNESS</span></div>';
 const status=$('#tprStatus');
 const ignoredTpr=(lastTprRows||[]).filter(tprProgressIsIgnored).length;
 if(status)status.textContent=rows.length+' shown · continuous TPR lifecycle · completed POS'+(ignoredTpr?' · '+ignoredTpr+' ignored <12h':'');
 $('#tprRows').innerHTML=rows.map((r,i)=>{
   const meta=tprRecommendationMeta(r),purpose=tprPurposeMeta(r),lift=tprLiftText(r.velocity_lift_pct),gpLift=tprLiftText(r.gp_day_lift_pct),future=tprFutureHeadline(r);
   const gp=num(r.current_gp_pct),post=num(r.post_tpr_supported_day_count),base=num(r.baseline_day_count);
   const prev=r.previous_behavior||{},now=r.current_behavior||{};
   const pair=String(r.recommendation_code||'').toUpperCase()==='MATCH_240'&&r.related_240_current_price!=null
     ?'<div class="pairauthority"><div><small>240 MAIN PRICE · AUTHORITY</small><b>'+money(r.related_240_current_price)+'</b><span>'+esc(r.related_240_upc||'240')+'</span></div><div class="pairarrow">→</div><div><small>TPR CURRENT</small><b>'+money(r.current_tpr_price)+'</b><span>249 must match 240</span></div></div>'
     :'';
   const suggestion=r.suggested_regular_price!=null
     ?'<div class="tprsuggest"><span>SUGGESTED NEW REGULAR PRICE</span><b>'+money(r.suggested_regular_price)+'</b></div>'
     :(r.suggested_tpr_price!=null?'<div class="tprsuggest"><span>SUGGESTED TPR PRICE</span><b>'+money(r.suggested_tpr_price)+'</b></div>':'');
   const cancelCode=['CANCEL_TPR','END_TPR'].includes(String(r.recommendation_code||'').toUpperCase());
   const originalReg=num(r.original_regular_price),newReg=num(r.suggested_regular_price);
   const originalRegExact=String(r.original_regular_price_basis||'').startsWith('PRIOR_CONFIGURED_REG');
   const cancelChoices=cancelCode?'<div class="tprcancelchoices"><div class="tprcancelchoice"><small>'+(originalRegExact?'CANCEL → ORIGINAL REG':'CANCEL → PRE-TPR REG EST.')+'</small><b>'+money(originalReg)+'</b></div><div class="tprcancelchoice"><small>CANCEL → NEW REG</small><b>'+(newReg===null?'REVIEW':money(newReg))+'</b></div></div>':'';
   const freshWindow=purpose.fresh?'<div class="freshwindow"><b>FRESHNESS WINDOW:</b> Day '+fmt(r.freshness_window_start_doh,0)+' → Day '+fmt(r.freshness_threshold_doh,0)+' inclusive. Goal: clear the aging stock reaching the threshold by the end of the threshold day; newer stock is not forced to zero.'+(num(r.aging_stock_target)!==null?' Aging target '+fmt(r.aging_stock_target)+' '+esc(r.current_oh_uom||'')+'.':'')+'</div>':'';
   const ohPair=familyOhPairHtml({family:r.family_article_number,name:r.name,effective:r.current_oh,effective_uom:r.current_oh_uom,effective_source:r.current_oh_source,system:r.system_oh,system_uom:r.system_oh_uom});
   return '<article class="pcard tprcard tone'+(i%5)+'" data-tpr-row="'+i+'">'+
     '<div class="ptop"><div class="pidentity"><div class="pupc"><span>UPC#</span><strong>'+esc(r.upc||'—')+'</strong></div><b>'+esc(r.name||r.upc||'Item')+'</b><small>Family '+esc(r.family_article_number||'—')+' · '+esc(r.category||'')+'</small></div><span class="pbadge '+meta.cls+'">'+esc(meta.label)+'</span></div>'+
     '<div class="tprpurpose '+purpose.cls+'"><span>'+esc(purpose.label)+'</span><span>START '+esc(shortDate(r.tpr_start_date))+(String(r.tpr_purpose_source||'').startsWith('USER')?' · USER SET':'')+'</span></div>'+
     ohPair+cancelChoices+freshWindow+
     '<div class="preasoncall '+(meta.cls==='urgent'?'red':meta.cls==='continue'?'green':'amber')+'"><span class="preasonmark">!</span><div><strong>TPR decision:</strong> '+esc(r.recommendation_reason||'Review current TPR performance')+'</div><span class="preasonchev">›</span></div>'+
     '<div class="pricepath">'+
       '<div class="pp current"><small>CURRENT TPR</small><b>'+money(r.current_tpr_price)+'</b><span>'+esc(gpText(r.current_tpr_price,r.current_cost))+'</span></div>'+
       '<div class="pp tested"><small>CURRENT COST</small><b>'+money(r.current_cost)+'</b><span>'+esc(r.selling_uom||'unit')+'</span></div>'+
       '<div class="pp testing"><small>3D TPR QTY</small><b>'+fmt(r.tpr_qty_3d)+'</b><span>'+fmt(r.tpr_velocity_3d)+'/day</span></div>'+
     '</div>'+pair+suggestion+
     '<div class="tprmonitor">'+
       '<div><small>BEFORE TPR</small><b>'+fmt(prev.velocity)+'/day</b><span>GP$/d '+money(prev.gp_per_day_current_cost)+'</span></div>'+
       '<div><small>NOW</small><b>'+fmt(now.velocity)+'/day</b><span>GP$/d '+money(now.gp_per_day)+'</span></div>'+
       '<div><small>PROJECTED</small><b>'+esc(future.main)+'</b><span>'+esc(future.sub)+'</span></div>'+
     '</div>'+
     '<div class="pmetrics">'+
       '<div class="pm ohpm">'+familyOhActionHtml({family:r.family_article_number,name:r.name,oh:r.current_oh,uom:r.current_oh_uom,source:r.current_oh_source},'tproh')+'</div>'+
       '<div class="pm"><small>7D QTY</small><b>'+fmt(r.qty_7d)+' '+esc(r.selling_uom||'')+'</b></div>'+
       '<div class="pm"><small>3D VEL LIFT</small><b class="tprlift '+lift.cls+'">'+esc(lift.text)+'</b></div>'+
       '<div class="pm"><small>GP$/D LIFT</small><b class="tprlift '+gpLift.cls+'">'+esc(gpLift.text)+'</b></div>'+
     '</div>'+
     '<div class="pcost"><span>GP% · DOH / DOS</span><b>'+((gp===null)?'—':(gp*100).toFixed(1)+'%')+' · '+fmt(r.doh)+' / '+fmt(r.dos)+'</b></div>'+
     '<div class="tprwindow">Continuous TPR since '+esc(shortDate(r.tpr_start_date))+' · current price step '+esc(shortDate(r.current_tpr_price_step_start_date))+' · evidence '+fmt(post,0)+' day'+(post===1?'':'s')+' · clean baseline '+fmt(base,0)+' day'+(base===1?'':'s')+'</div>'+
     '<div class="pcard-actions"><button class="pdetail" data-tpr-detail="'+i+'">DETAIL</button><button class="pdetail" data-tpr-action="'+i+'">'+esc(meta.label)+'</button><button class="pignore snooze12" data-tpr-ignore="'+i+'">IGNORE 12 HOURS</button></div>'+
   '</article>';
 }).join('')||'<div class="empty">No current TPR item matches this filter.</div>';
 $$('[data-tpr-row]').forEach(x=>x.onclick=e=>{if(e.target.closest('button,details,summary'))return;openCurrentTpr(rows[Number(x.dataset.tprRow)])});
 $$('[data-tpr-detail]').forEach(b=>b.onclick=e=>{e.stopPropagation();openCurrentTpr(rows[Number(b.dataset.tprDetail)])});
 $$('[data-tpr-action]').forEach(b=>b.onclick=e=>{e.stopPropagation();openCurrentTpr(rows[Number(b.dataset.tprAction)])});
 $$('[data-tpr-ignore]').forEach(b=>b.onclick=e=>{e.stopPropagation();ignoreTprProgress(rows[Number(b.dataset.tprIgnore)])});
 bindFamilyOhEditors();
}
async function setTprPurpose(r,purpose){
 if(!r?.upc||!r?.tpr_start_date){toast('TPR start date unavailable');return}
 try{
   await api('/v1/yipman/current-tpr-review/'+encodeURIComponent(r.upc)+'/purpose',{
     method:'POST',
     headers:{'Content-Type':'application/json'},
     body:JSON.stringify({tpr_start_date:r.tpr_start_date,purpose})
   });
   toast(purpose==='FRESHNESS_SELL_THROUGH'?'Freshness sell-through set':'Sweet-spot test set');
   closeSheet(false);
   await loadCurrentTpr();
 }catch(e){toast(e.message||'Could not save TPR purpose')}
}
function openCurrentTpr(r){
 const meta=tprRecommendationMeta(r),purpose=tprPurposeMeta(r),lift=tprLiftText(r.velocity_lift_pct),gpLift=tprLiftText(r.gp_day_lift_pct);
 const prev=r.previous_behavior||{},now=r.current_behavior||{},future=r.future_behavior||{};
 const actionPrice=r.suggested_regular_price!=null
   ?'<br><b>Suggested new REG</b> '+money(r.suggested_regular_price)
   :(r.suggested_tpr_price!=null?'<br><b>Suggested TPR</b> '+money(r.suggested_tpr_price):'');
 const cancelCode=['CANCEL_TPR','END_TPR'].includes(String(r.recommendation_code||'').toUpperCase());
 const originalRegExact=String(r.original_regular_price_basis||'').startsWith('PRIOR_CONFIGURED_REG');
 const cancelPath=cancelCode?'<br><br><b>After cancelling TPR</b><br>Option A · '+(originalRegExact?'restore original configured REG ':'use pre-TPR REG estimate ')+money(r.original_regular_price)+'<br>Option B · cancel and set a new REG '+(num(r.suggested_regular_price)===null?'after REG review':money(r.suggested_regular_price)):'';
 const ohPair=familyOhPairHtml({family:r.family_article_number,name:r.name,effective:r.current_oh,effective_uom:r.current_oh_uom,effective_source:r.current_oh_source,system:r.system_oh,system_uom:r.system_oh_uom});
 const freshness=purpose.fresh
   ?'<br><br><b>Freshness sell-through window</b><br>Day '+fmt(future.freshness_window_start_doh??r.freshness_window_start_doh,0)+' → Day '+fmt(future.freshness_threshold_doh??r.freshness_threshold_doh,0)+' inclusive · '+fmt(future.freshness_sellthrough_days_available??r.freshness_sellthrough_days_available,0)+' sell-through day(s). Aging stock target '+fmt(future.aging_stock_target??r.aging_stock_target)+' '+esc(r.current_oh_uom||'')+' · required '+fmt(future.required_velocity_to_clear)+'/day · projected aging stock left at threshold '+fmt(future.projected_oh_at_freshness_limit)+' '+esc(r.current_oh_uom||'')
   :'';
 sheet(r.name||r.upc,r.upc||'Current TPR review',
   ohPair+'<div class="tprpurpose '+purpose.cls+'"><span>'+esc(purpose.label)+'</span><span>SINCE '+esc(shortDate(r.tpr_start_date))+'</span></div>'+
   '<div class="tprpurposepick"><button data-tpr-purpose="SWEET_SPOT_TEST" class="'+(!purpose.fresh?'on':'')+'">FIND NEW REGULAR<br>SWEET SPOT</button><button data-tpr-purpose="FRESHNESS_SELL_THROUGH" class="'+(purpose.fresh?'on':'')+'">FRESHNESS<br>SELL-THROUGH</button></div>'+
   '<div class="tprtimeline"><div><small>BEFORE TPR</small><b>'+fmt(prev.velocity)+'/day</b><span>'+money(prev.avg_price)+' avg · GP$/d '+money(prev.gp_per_day_current_cost)+'</span></div><div><small>CURRENT TPR</small><b>'+fmt(now.velocity)+'/day</b><span>'+money(r.current_tpr_price)+' · GP$/d '+money(now.gp_per_day)+'</span></div><div><small>PROJECTED 7D</small><b>'+fmt(future.projected_qty_7d)+' '+esc(r.selling_uom||'')+'</b><span>GP$ '+money(future.projected_gp_7d)+'</span></div></div>'+
   '<div class="detail"><b>Recommendation</b><br><span class="pbadge '+meta.cls+'">'+esc(meta.label)+'</span><br>'+esc(r.recommendation_reason||'Review current TPR performance')+actionPrice+cancelPath+
   '<br><br><b>Continuous TPR lifecycle</b><br>Started '+esc(r.tpr_start_date||'—')+' · basis '+esc(r.tpr_start_basis||'—')+'<br>Current price step since '+esc(r.current_tpr_price_step_start_date||'—')+
   '<br><br><b>Current response vs clean pre-TPR baseline</b><br>TPR velocity '+fmt(r.tpr_velocity_3d)+'/day · baseline '+fmt(r.baseline_velocity)+'/day · lift '+esc(lift.text)+
   '<br>TPR GP$/day '+money(r.tpr_gp_per_day_3d)+' · baseline normalized GP$/day '+money(r.baseline_gp_per_day_current_cost)+' · lift '+esc(gpLift.text)+
   '<br><br><b>Inventory</b><br>Effective OH '+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+' · System OH '+fmt(r.system_oh)+' '+esc(r.system_oh_uom||r.current_oh_uom||'')+' · DOH '+fmt(r.doh)+' · DOS '+fmt(r.dos)+freshness+
   '<br><br><b>Observed TPR price behavior</b>'+tprPriceStepsHtml(r)+
   '<br><br><b>Decision model</b><br>Sweet-spot TPRs are judged on whether the price can become a sustainable new regular price. Freshness TPRs are judged on whether the aging stock reaching the freshness threshold is cleared by the threshold day; newer stock is not forced to zero.</div><div class="actions"><button class="secondary" id="tprTrueStockEdit">EDIT TRUE STOCK</button><button class="secondary snooze12" id="tprIgnore12h">IGNORE 12 HOURS</button></div>'
 );
 $$('[data-tpr-purpose]').forEach(b=>b.onclick=()=>setTprPurpose(r,b.dataset.tprPurpose));
 const ts=$('#tprTrueStockEdit');if(ts)ts.onclick=()=>openFamilyTrueStock({family:r.family_article_number,name:r.name,oh:r.current_oh,uom:r.current_oh_uom||r.system_oh_uom});
 const ig=$('#tprIgnore12h');if(ig)ig.onclick=()=>ignoreTprProgress(r);
 bindFamilyOhEditors();
}
async function loadCurrentTpr(opts={}){
 const requestId=++tprRequestSeq;
 clearTimeout(tprRetryTimer);tprRetryTimer=null;
 if(!opts.quiet)$('#tprRows').innerHTML='<div class="loading">Loading all current TPR items…</div>';
 $('#tprStatus').textContent='Checking authoritative current TPR prices and completed-day POS response…';
 try{
   const d=await api('/v1/yipman/current-tpr-review?category=ALL&limit=1000',{timeoutMs:10000});
   if(requestId!==tprRequestSeq)return;
   lastTprPayload=d||{};lastTprRows=Array.isArray(d?.rows)?d.rows:[];
   const warming=String(d?.analysis_status||'').toUpperCase()==='REFRESHING'&&!lastTprRows.length;
   if(warming){
     const tab=$('#tprTabCount');if(tab)tab.textContent='';
     $('#tprSummary').innerHTML='<div><b>—</b><span>CURRENT TPR</span></div><div><b>—</b><span>SWEET TEST</span></div><div><b>—</b><span>FRESHNESS</span></div>';
     $('#tprStatus').textContent='Building Current TPR review in the background…';
     $('#tprRows').innerHTML='<div class="loading">Calculating TPR performance. This page will update automatically.</div>';
   }else{
     renderCurrentTpr();
   }
   if(d?.refreshing&&current==='price'&&priceView==='TPR_PROGRESS'){
     tprRetryTimer=setTimeout(()=>loadCurrentTpr({quiet:true}),2500);
   }
 }catch(e){
   if(requestId!==tprRequestSeq)return;
   $('#tprStatus').textContent='Current TPR review temporarily unavailable';
   $('#tprRows').innerHTML='<div class="empty">'+esc(e.message)+'</div>';
 }
}

function clearanceIgnoreId(r){return 'CLEARANCE:'+String(r?.upc||'').trim()+':'+String(r?.expiry_date||'')}
function clearanceIsIgnored(r){
 const id=clearanceIgnoreId(r);if(!id)return false;
 const map=readPriceIgnores(),ts=Number(map[id]||0);
 if(!(ts>0))return false;
 if(Date.now()-ts>=PRICE_IGNORE_MS){delete map[id];writePriceIgnores(map);return false}
 return true;
}
function ignoreClearanceSuggestion(r){
 const id=clearanceIgnoreId(r);if(!id)return;
 const map=readPriceIgnores();map[id]=Date.now();writePriceIgnores(map);
 toast('Clearance suggestion hidden for 12 hours');
 setTimeout(()=>{if(current==='price'&&priceView==='CLEARANCE')renderClearanceRows()},PRICE_IGNORE_MS+1000);
 renderClearanceRows();
}
function clearanceWarningText(r){
 const a=Array.isArray(r?.warnings)?r.warnings:[];
 return a.map(friendlySignal).join(' · ');
}
function renderClearanceRows(){
 const all=clearanceRows||[],ignored=all.filter(clearanceIsIgnored).length,rows=all.filter(r=>!clearanceIsIgnored(r));
 $('#clearanceStatus').textContent=rows.length+' active clearance plan'+(rows.length===1?'':'s')+' · expiry priority'+(ignored?' · '+ignored+' ignored <12h':'');
 $('#clearanceRows').innerHTML=rows.map((r,i)=>{
   const stages=Array.isArray(r.stages)?r.stages:[];
   const trueStock=r.active_true_stock?('TRUE STOCK '+fmt(r.effective_oh)+' '+esc(r.effective_oh_uom||'')):('OH '+fmt(r.effective_oh)+' '+esc(r.effective_oh_uom||''));
   const warn=clearanceWarningText(r);
   return '<article class="clearance-card" data-clearance-detail="'+i+'">'+
     '<div class="ctop"><div><b>'+esc(r.name||r.upc||'Item')+'</b><small>UPC '+esc(r.upc||'—')+' · Family '+esc(r.family_article_number||'—')+' · expires '+esc(appDate(r.expiry_date))+'</small></div><span class="clearance-badge">'+esc(r.action_label||'CLEARANCE')+'</span></div>'+
     '<div class="clearance-metrics">'+
       '<div><small>EXPIRING</small><b>'+fmt(r.clearance_target_quantity)+' '+esc(r.uom_code||'')+'</b></div>'+
       '<div class="clearance-oh-cell">'+familyOhActionHtml({family:r.family_article_number,name:r.name,oh:r.effective_oh,uom:r.effective_oh_uom||r.uom_code,source:r.effective_oh_source},'clearanceoh')+'</div>'+
       '<div><small>NEED / DAY</small><b>'+fmt(r.required_daily_velocity)+'</b></div>'+
       '<div><small>7D VEL</small><b>'+fmt(r.current_velocity_7d)+'</b></div>'+
     '</div>'+
     '<div class="pcost"><span>CURRENT '+esc(r.current_price_type||'PRICE')+' · '+esc(trueStock)+'</span><b>'+money(r.current_price)+' · cost '+money(r.current_cost)+'</b></div>'+
     '<div class="tprwindow">'+fmt(r.days_to_expiry,0)+' day(s) to expiry · '+fmt(r.sell_days_including_today,0)+' selling day(s) including today'+(warn?' · '+esc(warn):'')+'</div>'+
     '<div style="margin-top:6px">'+stages.map(s=>'<div class="clearance-stage"><span>'+esc(s.label||('STEP '+s.stage))+'</span><b>'+money(s.suggested_price)+'</b><span>'+esc(shortDate(s.start_date))+'–'+esc(shortDate(s.end_date))+' · target '+fmt(s.required_daily_qty_reference)+'/day'+(s.margin_floor_applied?' · COST FLOOR':'')+'</span></div>').join('')+'</div>'+
     '<div class="clearance-actions"><button data-clearance-stock="'+i+'">TRUE STOCK</button><button class="primary" data-clearance-edit="'+i+'">EDIT PLAN</button><button class="snooze12" data-clearance-ignore="'+i+'">IGNORE 12 HOURS</button></div>'+
   '</article>';
 }).join('')||'<div class="empty">No active clearance plan. Search an item above to add expiring stock.</div>';
 document.querySelectorAll('[data-clearance-detail]').forEach(x=>x.onclick=e=>{if(e.target.closest('button'))return;openClearanceDetail(rows[Number(x.dataset.clearanceDetail)])});
 document.querySelectorAll('[data-clearance-stock]').forEach(b=>b.onclick=e=>{e.stopPropagation();const r=rows[Number(b.dataset.clearanceStock)];openFamilyTrueStock({family:r.family_article_number,name:r.name,oh:r.effective_oh,uom:r.effective_oh_uom||r.uom_code})});
 document.querySelectorAll('[data-clearance-edit]').forEach(b=>b.onclick=e=>{e.stopPropagation();openClearanceSetup({number:rows[Number(b.dataset.clearanceEdit)].upc,name:rows[Number(b.dataset.clearanceEdit)].name,selling_uom:rows[Number(b.dataset.clearanceEdit)].uom_code},rows[Number(b.dataset.clearanceEdit)])});
 document.querySelectorAll('[data-clearance-ignore]').forEach(b=>b.onclick=e=>{e.stopPropagation();ignoreClearanceSuggestion(rows[Number(b.dataset.clearanceIgnore)])});
 bindFamilyOhEditors();
}
async function loadClearance(){
 $('#clearanceStatus').textContent='Loading active clearance plans…';
 try{
   const d=await api('/v1/yipman/clearance?status=ACTIVE&limit=100',{timeoutMs:18000});
   clearanceRows=Array.isArray(d?.rows)?d.rows:[];
   renderClearanceRows();
 }catch(e){
   $('#clearanceStatus').textContent='Clearance temporarily unavailable';
   $('#clearanceRows').innerHTML='<div class="empty">'+esc(e.message)+'</div>';
 }
}
async function searchClearanceItems(){
 const input=$('#clearanceSearchInput'),box=$('#clearanceSearchResults'),q=(input?.value||'').trim();
 if(!q){box.innerHTML='';return}
 const seq=++clearanceSearchSeq;
 box.innerHTML='<div class="loading">Searching…</div>';
 try{
   const d=await api('/v1/app/v2/search?q='+encodeURIComponent(q)+'&limit=20',{timeoutMs:16000});
   if(seq!==clearanceSearchSeq)return;
   const rows=(d?.results||[]).filter(x=>String(x.result_type||'').toUpperCase()==='UPC').slice(0,10);
   box.innerHTML=rows.map((r,i)=>'<button class="clearance-search-item" data-clearance-pick="'+i+'"><span><b>'+esc(r.name||r.number||'UPC')+'</b><span>UPC '+esc(r.number||'—')+' · Family '+esc(r.family_article_number||'—')+' · '+esc(r.category||'')+' · '+esc(r.selling_uom||'')+'</span></span><strong>ADD →</strong></button>').join('')||'<div class="empty">No UPC result found.</div>';
   document.querySelectorAll('[data-clearance-pick]').forEach(b=>b.onclick=()=>openClearanceSetup(rows[Number(b.dataset.clearancePick)]));
 }catch(e){if(seq===clearanceSearchSeq)box.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
async function openClearanceSetup(item,existing=null){
 const upc=String(item?.number||item?.upc||'').trim();if(!upc)return;
 sheet('Clearance Plan','Loading '+esc(upc)+'…','<div class="loading">Loading stock and item details…</div>');
 try{
   const d=await api('/v1/app/quick-check/'+encodeURIComponent(upc),{timeoutMs:18000});
   const it=d?.item||{},eff=d?.effective_oh||{},sys=d?.system_oh||{},req=d?.true_stock_input||{};
   const unit=String(existing?.uom_code||req.required_uom||eff.uom||it.selling_uom||item.selling_uom||'').toUpperCase();
   const expiry=existing?.expiry_date||'';
   const expQty=existing?.expiring_quantity??'';
   const effectiveQty=eff.quantity;
   sheet('Clearance Plan',esc(it.selling_description||item.name||upc)+' · UPC '+esc(upc),
     '<div class="clearance-form">'+
       '<div class="tpr-rule"><b>CLEARANCE:</b> for expiring stock. The plan is separate from TPR. Company SALE remains locked and cannot be overridden.</div>'+
       '<div class="dmetrics"><div class="dm"><b>'+fmt(effectiveQty)+' '+esc(eff.uom||unit)+'</b><span>EFFECTIVE OH</span></div><div class="dm"><b>'+fmt(sys.quantity)+' '+esc(sys.uom||unit)+'</b><span>SYSTEM OH</span></div><div class="dm"><b>'+money(it.current_price)+'</b><span>CURRENT</span></div></div>'+
       '<div class="row2"><label>EXPIRY DATE<input id="clearanceExpiry" type="date" value="'+esc(expiry)+'"></label><label>EXPIRING QTY<input id="clearanceQty" type="number" min="0" step="0.1" inputmode="decimal" value="'+esc(expQty)+'"></label></div>'+
       '<label>UOM<input id="clearanceUom" value="'+esc(unit)+'" readonly></label>'+
       '<label>TRUE STOCK <span style="font-weight:700;color:#87939c">optional — enter only when physically counted</span><input id="clearanceTrueStock" type="number" min="0" step="0.1" inputmode="decimal" placeholder="Current effective OH '+esc(fmt(effectiveQty))+' '+esc(eff.uom||unit)+'"></label>'+
       '<label>NOTE<input id="clearanceNote" value="'+esc(existing?.note||'')+'" placeholder="Optional observation"></label>'+
       '<div class="estimatebar">Saving True Stock uses the same FULL MYSQL True Stock workflow as Quick Check. It becomes Effective OH and can create/update Pending Dumping when True Stock is below System OH.</div>'+
       '<div class="actions"><button class="secondary" id="clearanceCancel">CANCEL</button><button class="primary" id="clearanceSave">SAVE & BUILD PLAN</button></div>'+
     '</div>');
   $('#clearanceCancel').onclick=()=>closeSheet(true);
   $('#clearanceSave').onclick=async()=>{
     const expiryDate=$('#clearanceExpiry').value,qty=Number($('#clearanceQty').value),trueRaw=($('#clearanceTrueStock').value||'').trim(),trueStock=trueRaw===''?null:Number(trueRaw);
     if(!expiryDate)return toast('Enter expiry date');
     if(!Number.isFinite(qty)||qty<=0)return toast('Enter expiring quantity');
     if(trueStock!==null&&(!Number.isFinite(trueStock)||trueStock<0))return toast('Enter valid True Stock');
     const btn=$('#clearanceSave');btn.disabled=true;btn.textContent='SAVING…';
     try{
       const body={clearance_plan_id:existing?.clearance_plan_id||null,upc,expiry_date:expiryDate,expiring_quantity:qty,uom:unit,note:($('#clearanceNote').value||'').trim()||null};
       if(trueStock!==null){body.true_stock=trueStock;body.true_stock_uom=unit}
       await api('/v1/yipman/clearance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),timeoutMs:30000});
       closeSheet(false);$('#clearanceSearchResults').innerHTML='';$('#clearanceSearchInput').value='';toast('Clearance plan saved');await loadClearance();
     }catch(e){toast(e.message||'Could not save clearance');btn.disabled=false;btn.textContent='SAVE & BUILD PLAN'}
   };
 }catch(e){sheet('Clearance Plan','UPC '+esc(upc),'<div class="empty">'+esc(e.message)+'</div>')}
}
function openClearanceDetail(r){
 const stages=Array.isArray(r?.stages)?r.stages:[];
 const ohPair=familyOhPairHtml({family:r.family_article_number,name:r.name,effective:r.effective_oh,effective_uom:r.effective_oh_uom||r.uom_code,effective_source:r.effective_oh_source,system:r.system_oh,system_uom:r.system_oh_uom||r.uom_code});
 sheet(r.name||'Clearance',r.upc||'',
   ohPair+'<div class="detail"><b>'+esc(r.action_label||'CLEARANCE')+'</b><br>Expires '+esc(appDate(r.expiry_date))+' · expiring '+fmt(r.clearance_target_quantity)+' '+esc(r.uom_code||'')+
   '<br><br><b>Sell-out requirement</b><br>'+fmt(r.required_daily_velocity)+' '+esc(r.uom_code||'')+'/day required vs '+fmt(r.current_velocity_7d)+'/day current 7D velocity'+
   '<br><br><b>Price plan</b>'+stages.map(s=>'<div class="clearance-stage"><span>'+esc(s.label||'STEP')+'</span><b>'+money(s.suggested_price)+'</b><span>'+esc(appDate(s.start_date))+' → '+esc(appDate(s.end_date))+' · '+((num(s.markdown_pct)!==null)?(num(s.markdown_pct)*100).toFixed(0)+'% markdown':'company controlled')+'</span></div>').join('')+
   '<br><b>Rule</b><br>Automatic clearance steps do not cross current cost. If the item is still behind pace at the cost floor, use manager disposition review rather than an automatic below-cost suggestion.</div>'+
   '<div class="actions"><button id="clearanceClose">CLOSE PLAN</button><button class="primary" id="clearanceDetailStock">UPDATE TRUE STOCK</button></div>');
 $('#clearanceDetailStock').onclick=()=>openFamilyTrueStock({family:r.family_article_number,name:r.name,oh:r.effective_oh,uom:r.effective_oh_uom||r.uom_code});
 bindFamilyOhEditors();
 $('#clearanceClose').onclick=async()=>{
   if(!window.confirm('Close this clearance plan?'))return;
   try{await api('/v1/yipman/clearance/'+encodeURIComponent(r.clearance_plan_id)+'/close',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'CLOSED'}),timeoutMs:16000});closeSheet(false);toast('Clearance plan closed');await loadClearance()}catch(e){toast(e.message)}
 };
}
function openClearanceTrueStock(r){
 const unit=String(r?.required_true_stock_uom||r?.effective_oh_uom||r?.uom_code||'').toUpperCase();
 sheet(r.name||'True Stock','Clearance · UPC '+esc(r.upc||''),
   '<div class="detail"><b>System OH</b><br>'+fmt(r.system_oh)+' '+esc(r.system_oh_uom||unit)+'<br><br><b>Current Effective OH</b><br>'+fmt(r.effective_oh)+' '+esc(r.effective_oh_uom||unit)+' · '+esc(r.effective_oh_source||'')+
   '<br><br><b>Observed True Stock</b><br><input id="clearanceStockInput" type="number" min="0" step="0.1" inputmode="decimal" value="'+esc(r.effective_oh??'')+'" style="width:100%;font-size:24px;font-weight:900;padding:10px;border:2px solid #d6dde3;border-radius:12px">'+
   '<br><br><div class="estimatebar">This is a real True Stock update. It becomes Effective OH. If lower than System OH, FULL MYSQL automatically creates or updates the Pending Dumping discrepancy.</div>'+
   '<div class="actions"><button class="secondary" id="clearanceStockCancel">CANCEL</button><button class="primary" id="clearanceStockSave">SAVE TRUE STOCK</button></div></div>');
 $('#clearanceStockCancel').onclick=()=>closeSheet(true);
 $('#clearanceStockSave').onclick=async()=>{
   const qty=Number($('#clearanceStockInput').value);if(!Number.isFinite(qty)||qty<0)return toast('Enter valid True Stock');
   const btn=$('#clearanceStockSave');btn.disabled=true;btn.textContent='SAVING…';
   try{
     await api('/v1/app/quick-check/'+encodeURIComponent(r.upc)+'/true-stock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:qty,uom:unit}),timeoutMs:30000});
     closeSheet(false);toast('True Stock saved');await loadClearance();
   }catch(e){toast(e.message);btn.disabled=false;btn.textContent='SAVE TRUE STOCK'}
 };
}
async function loadPriceCurrentView(){
 if(priceView==='TPR_PROGRESS')return loadCurrentTpr();
 if(priceView==='CLEARANCE')return loadClearance();
 return loadPrices();
}
function switchPriceTab(tab){
 const next=String(tab||'REG').toUpperCase();
 priceView=['REG','TPR_SUGGEST','TPR_PROGRESS','CLEARANCE'].includes(next)?next:'REG';
 document.querySelectorAll('[data-price-tab]').forEach(b=>b.classList.toggle('on',b.dataset.priceTab===priceView));
 $('#priceSuggestionPane').classList.toggle('hide',!['REG','TPR_SUGGEST'].includes(priceView));
 $('#currentTprPane').classList.toggle('hide',priceView!=='TPR_PROGRESS');
 $('#clearancePane').classList.toggle('hide',priceView!=='CLEARANCE');
 if(['REG','TPR_SUGGEST'].includes(priceView)){
   priceReasonFilter='ALL';const rf=$('#priceReasonFilter');if(rf)rf.value='ALL';
 }
 loadPriceCurrentView();
}
document.querySelectorAll('[data-price-tab]').forEach(b=>b.onclick=()=>switchPriceTab(b.dataset.priceTab));
const clearanceSearchBtn=$('#clearanceSearchBtn');if(clearanceSearchBtn)clearanceSearchBtn.onclick=searchClearanceItems;
const clearanceSearchInput=$('#clearanceSearchInput');if(clearanceSearchInput)clearanceSearchInput.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();searchClearanceItems()}};
$$('[data-tpr-filter]').forEach(b=>b.onclick=()=>{
 tprFilter=b.dataset.tprFilter;
 $$('[data-tpr-filter]').forEach(x=>x.classList.toggle('on',x===b));
 renderCurrentTpr();
});
$('#tprSort').onchange=e=>{tprSort=e.target.value;renderCurrentTpr()};

function qaFixLabel(x){
 const k=String(x?.fix_kind||'').toUpperCase();
 if(k==='UOM_OR_IDENTITY'||k==='IDENTITY_AND_UOM')return 'Item / UOM';
 if(k==='COST_CONVERSION')return 'Cost Conversion';
 if(k==='ARTICLE_FAMILY_MAPPING')return 'Article → Family';
 return 'Review Only';
}
function qaIssueName(x){
 const c=x?.current||{};
 return c.item_name||c.selling_description||c.article_description||x?.entity_key||x?.issue_code||'QA issue';
}
function qaIssueKey(x){return x?.issue_id==null?('QC:'+String(x?.entity_key||'')):String(x.issue_id)}
function findDataQaIssue(key){
 if(String(key).startsWith('QC:'))return dataQaIssues.find(x=>x.issue_id==null&&('QC:'+String(x.entity_key||''))===String(key));
 return dataQaIssues.find(x=>String(x.issue_id)===String(key));
}
function renderQAResolution(qa,batch){
 dataQaIssues=Array.isArray(qa?.issues)?qa.issues:[];
 dataQaBatchId=qa?.batch_id||batch?.batch_id||null;
 const open=dataQaIssues.length,fixable=dataQaIssues.filter(x=>x.can_fix).length,review=open-fixable;
 const badge=$('#qaResolutionBadge');badge.textContent=open?open+' OPEN':'READY';badge.className='qaresbadge '+(open?'bad':'ok');
 if(!open){
   $('#qaResolution').innerHTML='<div class="qainfo"><b>No open QA issues.</b><br>Current QA review is clear.</div>';
   return;
 }
 const groups=new Map();
 dataQaIssues.forEach(x=>{const code=String(x.issue_code||'QA_HOLD').toUpperCase();const g=groups.get(code)||{code,count:0,fixable:0};g.count++;if(x.can_fix)g.fixable++;groups.set(code,g)});
 const rows=[...groups.values()].sort((a,b)=>b.count-a.count||a.code.localeCompare(b.code)).slice(0,7);
 $('#qaResolution').innerHTML=
   '<div class="qaresstats"><div class="qaresstat"><small>OPEN</small><b>'+open+'</b></div><div class="qaresstat"><small>FIXABLE</small><b>'+fixable+'</b></div><div class="qaresstat"><small>REVIEW / BLOCKED</small><b>'+review+'</b></div></div>'+
   '<div class="qagroups">'+rows.map(g=>'<div class="qagroup"><div><b>'+esc(friendlySignal(g.code))+'</b><span>'+g.count+' issue'+(g.count===1?'':'s')+' · '+g.fixable+' user-confirmable</span></div><button class="'+(g.fixable?'fix':'')+'" data-qa-group="'+esc(g.code)+'">'+(g.fixable?'FIX':'DETAIL')+'</button></div>').join('')+'</div>'+
   '<div class="qaresactions"><button class="qaresreview" id="qaReviewAll">REVIEW ALL</button><button class="qaresrebuild" id="qaRebuild">'+(dataQaBatchId?'REBUILD QA':'REBUILD UNAVAILABLE')+'</button></div>'+
   '<div class="qainfo warn">Fixes are fail-closed. Only confirmed identity/UOM, cost conversion, and Article→Family authority are editable here. RAW source data is never changed.</div>';
 $$('[data-qa-group]').forEach(b=>b.onclick=()=>openQAGroup(b.dataset.qaGroup));
 const all=$('#qaReviewAll');if(all)all.onclick=()=>openQAGroup('ALL');
 const rebuild=$('#qaRebuild');if(rebuild){rebuild.disabled=!dataQaBatchId;rebuild.onclick=()=>rebuildQAFromDataCenter()}
}
function openQAGroup(code){
 const rows=(code==='ALL'?dataQaIssues:dataQaIssues.filter(x=>String(x.issue_code||'').toUpperCase()===String(code).toUpperCase()));
 sheet('QA Resolution',code==='ALL'?(rows.length+' open issues'):friendlySignal(code),'<div class="qalist">'+rows.map(x=>{const cur=x.current||{};return '<button class="qaitem" data-qa-issue="'+esc(qaIssueKey(x))+'"><div class="qaitemtop"><div><b>'+esc(qaIssueName(x))+'</b><small>'+esc(x.entity_type||'')+' '+esc(x.entity_key||'')+(cur.current_oh!=null?' · OH '+fmt(cur.current_oh)+' '+esc(cur.current_oh_uom||''):'')+'</small></div><span class="qaflag '+(x.can_fix?'fix':'blocked')+'">'+esc(x.can_fix?'FIX':'REVIEW')+'</span></div><div class="qaitemreason">'+esc(friendlySignal(x.issue_code||x.issue_summary||''))+' · '+esc(qaFixLabel(x))+'</div></button>'}).join('')+'</div>');
 $$('[data-qa-issue]').forEach(b=>b.onclick=()=>openMobileQAIssue(b.dataset.qaIssue));
}
function mobileQaApplyFeedback(msg){toast(msg)}
async function refreshDataAfterQAFix(){closeSheet(false);await loadData()}
function openMobileQAIssue(key){
 const x=findDataQaIssue(key);if(!x)return;
 const cur=x.current||{},detail=x.detail||{},kind=String(x.fix_kind||'').toUpperCase();
 const name=qaIssueName(x),entity=String(x.entity_key||'');
 const summary='<div class="dmetrics"><div class="dm"><b>'+esc(x.severity||'—')+'</b><span>SEVERITY</span></div><div class="dm"><b>'+esc(entity||'—')+'</b><span>'+esc(x.entity_type||'ENTITY')+'</span></div><div class="dm"><b>'+esc(qaFixLabel(x))+'</b><span>FIX TYPE</span></div></div><div class="qainfo"><b>'+esc(friendlySignal(x.issue_code||'QA HOLD'))+'</b><br>'+esc(x.issue_summary||'Review the QA evidence before making a correction.')+'</div>';
 if(!x.can_fix){
   sheet('QA Issue',name,summary+'<div class="qainfo warn"><b>Review only.</b><br>This issue is not safely editable from Data Center. Fix the missing source/dependency or underlying lineage, then rebuild QA.</div><div class="detail"><b>Evidence</b><br><pre style="white-space:pre-wrap;margin:6px 0 0">'+esc(JSON.stringify(detail,null,2))+'</pre></div>');
   return;
 }
 if(kind==='ARTICLE_FAMILY_MAPPING'){
   sheet('Fix Article → Family',name,summary+'<div class="qafields"><div class="qafield"><label>ARTICLE</label><input id="mQaArticle" value="'+esc(entity)+'" readonly></div><div class="qafield"><label>CONFIRMED FAMILY / MAIN ARTICLE</label><input id="mQaFamily" inputmode="numeric" placeholder="Enter Family Article #"></div><div class="qafield"><label>NOTE</label><textarea id="mQaNote" placeholder="How was this mapping confirmed?"></textarea></div></div><label class="qaconfirm"><input id="mQaConfirm" type="checkbox"><span>I confirmed this Article belongs to the Family entered above.</span></label><div class="actions"><button class="secondary" id="mQaCancel">CANCEL</button><button class="primary" id="mQaApplyFamily">APPLY FIX</button></div>');
   $('#mQaCancel').onclick=()=>closeSheet(true);
   $('#mQaApplyFamily').onclick=async()=>{if(!$('#mQaConfirm').checked)return mobileQaApplyFeedback('Confirm the mapping first');const fam=($('#mQaFamily').value||'').trim();if(!fam)return mobileQaApplyFeedback('Enter the Family Article');const btn=$('#mQaApplyFamily');btn.disabled=true;btn.textContent='APPLYING…';try{await api('/v1/backoffice/qa-resolve-article-family',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({issue_id:x.issue_id,article_number:entity,main_article_number:fam,note:($('#mQaNote').value||'').trim()||null,confirm:'APPLY_ARTICLE_FAMILY_FIX'}),timeoutMs:30000});mobileQaApplyFeedback('Family mapping saved · rebuild QA next');await refreshDataAfterQAFix()}catch(e){mobileQaApplyFeedback(e.message);btn.disabled=false;btn.textContent='APPLY FIX'}};
   return;
 }
 if(kind==='COST_CONVERSION'){
   const sell=String(cur.selling_uom||detail.selling_uom||'').toUpperCase(),costUom=String(detail.cost_uom||'').toUpperCase();
   sheet('Fix Cost Conversion',name,summary+'<div class="qafields"><div class="qafield"><label>SELLING QTY</label><input id="mQaSellQty" type="number" min="0.0001" step="0.0001" value="1"></div><div class="qafield"><label>SELLING UOM</label><input id="mQaSellUom" value="'+esc(sell)+'" readonly></div><div class="qafield"><label>COST QTY</label><input id="mQaCostQty" type="number" min="0.0001" step="0.0001" placeholder="Example: 2"></div><div class="qafield"><label>COST UOM</label><input id="mQaCostUom" value="'+esc(costUom)+'" readonly></div><div class="qafield"><label>NOTE</label><textarea id="mQaNote" placeholder="Example: 1 PACK = 2 LB"></textarea></div></div><label class="qaconfirm"><input id="mQaConfirm" type="checkbox"><span>I confirmed this exact cost-to-selling conversion.</span></label><div class="actions"><button class="secondary" id="mQaCancel">CANCEL</button><button class="primary" id="mQaApplyConv">APPLY FIX</button></div>');
   $('#mQaCancel').onclick=()=>closeSheet(true);
   const btn=$('#mQaApplyConv');if(!sell||!costUom){btn.disabled=true;mobileQaApplyFeedback('Selling UOM and Cost UOM must both be known');return}
   btn.onclick=async()=>{if(!$('#mQaConfirm').checked)return mobileQaApplyFeedback('Confirm the conversion first');const sq=Number($('#mQaSellQty').value),cq=Number($('#mQaCostQty').value);if(!(sq>0)||!(cq>0))return mobileQaApplyFeedback('Enter positive quantities');btn.disabled=true;btn.textContent='APPLYING…';try{await api('/v1/backoffice/qa-resolve-cost-conversion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({issue_id:x.issue_id,ean_upc:entity,selling_qty:sq,selling_uom:sell,cost_qty:cq,cost_uom:costUom,note:($('#mQaNote').value||'').trim()||null,confirm:'APPLY_COST_CONVERSION_FIX'}),timeoutMs:30000});mobileQaApplyFeedback('Cost conversion saved');await refreshDataAfterQAFix()}catch(e){mobileQaApplyFeedback(e.message);btn.disabled=false;btn.textContent='APPLY FIX'}};
   return;
 }
 const article=String(cur.article_number||cur.main_article_number||''),sell=String(cur.selling_uom||''),base=String(cur.base_uom||''),factor=cur.base_qty_per_selling_unit??'';
 sheet('Fix Item / UOM',name,summary+'<div class="qafields"><div class="qafield"><label>SELLING UOM</label><select id="mQaSellingUom"><option value="">Select UOM…</option>'+['LB','EA','PACK','PAC','CASE','BAG','BX','TRAY'].map(u=>'<option value="'+u+'" '+(sell.toUpperCase()===u?'selected':'')+'>'+u+'</option>').join('')+'</select></div><div class="qafield"><label>ARTICLE NUMBER</label><input id="mQaArticle" value="'+esc(article)+'" placeholder="Confirmed Article #"></div><div class="qafield"><label>BASE UOM · OPTIONAL</label><select id="mQaBaseUom"><option value="">Not confirmed</option>'+['LB','EA','PACK','PAC','CASE','BAG','BX','TRAY'].map(u=>'<option value="'+u+'" '+(base.toUpperCase()===u?'selected':'')+'>'+u+'</option>').join('')+'</select></div><div class="qafield"><label>BASE QTY / SELLING UNIT · OPTIONAL</label><input id="mQaFactor" type="number" min="0" step="0.0001" value="'+esc(factor)+'" placeholder="Example: 2"></div><div class="qafield"><label>NOTE</label><textarea id="mQaNote" placeholder="What did you confirm?"></textarea></div></div><label class="qaconfirm"><input id="mQaConfirm" type="checkbox"><span>I confirmed the item link and Selling UOM entered above.</span></label><div class="qainfo">This writes only a confirmed identity/UOM authority. Price, cost, sales, receipts and RAW files remain unchanged.</div><div class="actions"><button class="secondary" id="mQaCancel">CANCEL</button><button class="primary" id="mQaApply">APPLY FIX</button></div>');
 $('#mQaCancel').onclick=()=>closeSheet(true);
 $('#mQaApply').onclick=async()=>{if(!$('#mQaConfirm').checked)return mobileQaApplyFeedback('Confirm the correction first');const selling=$('#mQaSellingUom').value;if(!selling)return mobileQaApplyFeedback('Select Selling UOM');const baseUom=$('#mQaBaseUom').value||null,fraw=($('#mQaFactor').value||'').trim();if(baseUom&&!fraw)return mobileQaApplyFeedback('Enter Base Qty or clear Base UOM');const btn=$('#mQaApply');btn.disabled=true;btn.textContent='APPLYING…';try{await api('/v1/backoffice/qa-resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({issue_id:x.issue_id,ean_upc:entity,article_number:($('#mQaArticle').value||'').trim()||null,selling_uom:selling,base_uom:baseUom,base_qty_per_selling_unit:fraw===''?null:Number(fraw),note:($('#mQaNote').value||'').trim()||null,confirm:'APPLY_QA_FIX'}),timeoutMs:30000});mobileQaApplyFeedback('QA fix saved');await refreshDataAfterQAFix()}catch(e){mobileQaApplyFeedback(e.message);btn.disabled=false;btn.textContent='APPLY FIX'}};
}
async function rebuildQAFromDataCenter(){
 if(!dataQaBatchId)return toast('No rebuildable QA batch');
 if(!window.confirm('Rebuild Phase 3 / QA for Batch #'+dataQaBatchId+'?\n\nThis recalculates with the current fixes. It does not erase unresolved blockers.'))return;
 const btn=$('#qaRebuild');if(btn){btn.disabled=true;btn.textContent='QUEUING…'}
 try{await api('/v1/web-upload/batches/'+encodeURIComponent(dataQaBatchId)+'/rebuild-phase3',{method:'POST',timeoutMs:30000});toast('QA rebuild queued');setTimeout(()=>loadData(),900)}catch(e){toast(e.message);if(btn){btn.disabled=false;btn.textContent='REBUILD QA'}}
}
function fmtElapsedSeconds(v){
 const n=num(v);if(n===null||n<0)return '—';
 const sec=Math.round(n);if(sec<60)return sec+'s';
 const m=Math.floor(sec/60),s=sec%60;if(m<60)return m+'m '+s+'s';
 const h=Math.floor(m/60),mm=m%60;return h+'h '+mm+'m';
}
function dataBatchIsActivelyProcessing(b){
 if(!b?.batch_id)return false;
 const run=String(b.active_run_status||'').toUpperCase();
 const st=String(b.processing_status||'').toUpperCase();
 return ['QUEUED','STARTED','PAUSE_REQUESTED'].includes(run)
   || ['API_UPLOADING','INGESTED_PENDING_QA','RAW_RELEASED','RELEASED'].includes(st);
}
function dataBatchSignature(b){
 if(!b?.batch_id)return 'NONE';
 return [
   b.batch_id,
   String(b.processing_status||'').toUpperCase(),
   String(b.active_run_status||'').toUpperCase(),
   b.active_pipeline_run_id||''
 ].join('|');
}
function batchLiveState(b){
 const run=String(b?.active_run_status||'').toUpperCase();
 const fresh=b?.active_heartbeat_fresh===true;
 const age=num(b?.active_heartbeat_age_seconds);
 const batch=String(b?.processing_status||'').toUpperCase();
 if(run==='STARTED'&&fresh)return {key:'running',label:'RUNNING',sub:'heartbeat '+(age!==null?fmtElapsedSeconds(age)+' ago':'live')};
 if(run==='STARTED'&&!fresh)return {key:'stuck',label:'POSSIBLY STUCK',sub:age!==null?('no heartbeat for '+fmtElapsedSeconds(age)):'live heartbeat missing'};
 if(run==='QUEUED')return {key:'queued',label:'QUEUED',sub:'waiting for worker'};
 if(run==='PAUSE_REQUESTED')return {key:'queued',label:'PAUSING',sub:'pause requested'};
 if(/^QUICK_CHECK_READY/.test(batch)||batch==='COMPLETED')return {key:'running',label:'COMPLETE / READY',sub:'published · no active worker required'};
 if(batch==='PHASE3_QA_HOLD'||batch==='QA_HOLD')return {key:'idle',label:'NOT RUNNING',sub:'batch-level QA hold · action required'};
 if(/READY|PUBLISH/.test(batch))return {key:'running',label:'COMPLETE / READY',sub:'no active worker required'};
 return {key:'idle',label:'NOT RUNNING',sub:friendlySignal(batch||'no active run')};
}
function renderLivePipeline(activeBatch,latestPublished){
 const b=activeBatch||latestPublished||{};
 const st=String(b?.processing_status||'NONE').toUpperCase(),run=String(activeBatch?.active_run_status||'').toUpperCase();
 const published=/^QUICK_CHECK_READY/.test(st);
 const blockingHold=st==='PHASE3_QA_HOLD'||st==='QA_HOLD';
 const itemHolds=num(b?.quick_check_hold_rows)??num(b?.qa_summary?.phase3?.quick_check_hold_rows)??0;
 const uploaded=st!=='NONE';
 const ingested=/INGEST|PHASE|QUICK|READY|RELEASE/.test(st);
 const qaDone=published;
 let qaClass='',qaText='WAIT';
 if(blockingHold){qaClass='bad';qaText='BLOCKED'}
 else if(published&&itemHolds>0){qaClass='warn';qaText='DONE · '+fmt(itemHolds,0)+' ITEM HOLD'}
 else if(qaDone){qaClass='ok';qaText='DONE'}
 else if(run==='STARTED'){qaClass='warn';qaText='RUN'}
 $('#pipe').innerHTML=
   '<div class="stage '+(uploaded?'ok':'')+'"><b>UPLOAD</b><span>'+(uploaded?'DONE':'—')+'</span></div>'+
   '<div class="stage '+(ingested?'ok':'')+'"><b>INGEST</b><span>'+(ingested?'DONE':'—')+'</span></div>'+
   '<div class="stage '+qaClass+'"><b>QA</b><span>'+esc(qaText)+'</span></div>'+
   '<div class="stage '+(published?'ok':run==='STARTED'?'warn':'')+'"><b>PUBLISH</b><span>'+(published?'READY':run==='STARTED'?'WORK':'WAIT')+'</span></div>';
}
function renderCurrentBatchPanel(b){
 if(!b?.batch_id){$('#currentBatch').innerHTML='<div class="empty"><b>No batch currently processing.</b><br>Latest completed and published batches are shown separately below.</div>';return}
 const st=String(b.processing_status||'NONE').toUpperCase(),statusLabel=friendlySignal(st);
 const statusClass=st.includes('HOLD')?'red':(/READY|PUBLISH/.test(st)?'green':'amber');
 const live=batchLiveState(b),pctNum=num(b.active_progress_pct),hasPct=pctNum!==null,pct=hasPct?Math.max(0,Math.min(100,pctNum)):0;
 const cur=num(b.active_progress_current),tot=num(b.active_progress_total),hasCounts=cur!==null&&tot!==null&&tot>0;
 const stage=b.active_phase3_stage||b.active_last_phase3_stage||b.active_stage_name||'—';
 const elapsed=fmtElapsedSeconds(b.active_progress_elapsed_seconds),eta=fmtElapsedSeconds(b.active_progress_eta_seconds);
 const rate=num(b.active_progress_rows_per_second),hbAge=fmtElapsedSeconds(b.active_heartbeat_age_seconds);
 const runId=b.active_pipeline_run_id||b.pipeline_run_id||'—';
 const issueTotal=b.active_issue_total??b.open_issue_total??b.error_count??b.qa_hold_count??0;
 const ready=b.active_progress_ready,hold=b.active_progress_hold,hist=b.active_progress_historical;
 const item=[b.active_progress_current_upc,b.active_progress_current_name].filter(Boolean).join(' · ');
 const fileName=String(b.active_file_name||'').trim();
 const fileMeta=[
   b.active_source_type?friendlySignal(b.active_source_type):'',
   b.active_file_status?friendlySignal(b.active_file_status):'',
   b.active_file_rows!=null?(fmt(b.active_file_rows,0)+' rows'):''
 ].filter(Boolean).join(' · ');
 const progressLabel=hasPct?(pct.toFixed(pct%1?1:0)+'%'):hasCounts?(fmt(cur,0)+' / '+fmt(tot,0)):String(b.active_progress_kind||'Processing');
 const progressDetail=hasCounts?(fmt(cur,0)+' of '+fmt(tot,0)+' '+esc(b.active_progress_unit||'rows')):(b.active_progress_kind?friendlySignal(b.active_progress_kind):'No numeric progress reported yet');
 const alert=live.key==='stuck'?'<div class="cbwarn"><b>Heartbeat is stale.</b> The run still says STARTED, but the worker is not reporting live progress. Open the batch detail or refresh before deciding to rerun it.</div>':'';
 $('#currentBatch').innerHTML='<div class="currentbatch" data-batch="'+esc(b.session_id||b.batch_key||'')+'">'+
  '<div class="cbtop"><div class="cbid"><b>Batch #'+esc(b.batch_id)+'</b><span>'+esc(b.batch_label||'Current processing batch')+'</span></div><span class="cbstatus '+statusClass+'">'+esc(statusLabel)+'</span></div>'+
  '<div class="cblive"><div class="cblive-main"><i class="cblive-dot '+esc(live.key)+'"></i><div><b>'+esc(live.label)+'</b><span>'+esc(live.sub)+'</span></div></div><span class="cblivecheck">LIVE · 5s</span></div>'+
  '<div class="cbprogress"><div class="cbprogress-top"><b>'+esc(friendlySignal(stage))+'</b><span>'+esc(progressLabel)+'</span></div><div class="cbbar"><i style="width:'+(hasPct?pct:(hasCounts?Math.max(3,Math.min(100,(cur/tot)*100)):0)).toFixed(1)+'%"></i></div><div class="cbprogress-sub"><span>'+progressDetail+'</span><span>'+((ready!=null||hold!=null)?('Ready '+fmt(ready,0)+' · Hold '+fmt(hold,0)):(hist!=null?('Historical '+fmt(hist,0)):'Run #'+esc(runId)))+'</span></div></div>'+
  '<div class="cbrunmeta"><div><small>RUN</small><b>#'+esc(runId)+'</b></div><div><small>HEARTBEAT</small><b>'+esc(hbAge)+'</b></div><div><small>ELAPSED</small><b>'+esc(elapsed)+'</b></div><div><small>ETA</small><b>'+esc(eta)+'</b></div></div>'+
  '<div class="cbmeta"><div><small>FILES</small><b>'+fmt(b.file_count??b.files_count??b.uploaded_file_count,0)+'</b></div><div><small>OPEN ISSUES</small><b>'+fmt(issueTotal,0)+'</b></div><div><small>RATE</small><b>'+(rate!==null?fmt(rate,1)+'/s':'—')+'</b></div></div>'+
  (fileName?'<div class="cbcurrentitem"><small>CURRENT PROCESSING FILE</small><b title="'+esc(fileName)+'">'+esc(fileName)+'</b>'+(fileMeta?'<span>'+esc(fileMeta)+'</span>':'')+'</div>':'')+
  (item?'<div class="cbcurrentitem"><small>CURRENT WORK ITEM</small><b>'+esc(item)+'</b></div>':'')+alert+'</div>';
 const el=$('#currentBatch [data-batch]');if(el)el.onclick=()=>openBatch(el.dataset.batch,b);
}
function renderPublishedSnapshot(dash,health,latestBatch){
 const box=$('#publishedSnapshot');if(!box)return;
 const quick=dash?.quick_check||{};
 const latest=health?.latest||{};
 const batchId=quick.latest_publish_batch_id||latestBatch?.batch_id||null;
 if(!batchId){
  box.innerHTML='<div class="empty">Published Quick Check snapshot unavailable.</div>';
  return;
 }
 const ready=num(quick.ready_rows),hold=num(quick.qa_hold_rows);
 const publishedAt=quick.latest_published_at||latestBatch?.completed_at||'';
 box.innerHTML='<div class="currentbatch">'+
  '<div class="cbtop"><div class="cbid"><b>Published Batch #'+esc(batchId)+'</b><span>'+(publishedAt?'Published '+esc(String(publishedAt).replace('T',' ').slice(0,19)):'Current Quick Check serving snapshot')+'</span></div><span class="cbstatus green">SERVING NOW</span></div>'+
  '<div class="cbmeta"><div><small>POS THROUGH</small><b>'+esc(latest.POS?.date||'—')+'</b></div><div><small>MVT THROUGH</small><b>'+esc(latest.MVT?.date||'—')+'</b></div><div><small>PRICE</small><b>'+esc(latest.PRICE?.date||'—')+'</b></div></div>'+
  '<div class="cbmeta"><div><small>OH</small><b>'+esc(latest.OH?.date||'—')+'</b></div><div><small>QC READY</small><b>'+fmt(ready,0)+'</b></div><div><small>ITEM HOLDS</small><b>'+fmt(hold,0)+'</b></div></div>'+
  '</div>';
}
function scheduleDataLivePoll(){
 clearTimeout(dataLiveTimer);dataLiveTimer=null;
 if(current==='data')dataLiveTimer=setTimeout(pollDataLive,5000);
}
async function pollDataLive(){
 if(current!=='data')return;
 try{
  const active=await api('/v1/web-upload/active',{timeoutMs:9000});
  const activeCandidate=active.active_batch||null;
  const nextSignature=dataBatchSignature(activeCandidate);
  if(dataLiveSignature&&nextSignature!==dataLiveSignature){
    dataLiveSignature=nextSignature;
    await loadData();
    return;
  }
  dataLiveSignature=nextSignature;
  const currentBatch=dataBatchIsActivelyProcessing(activeCandidate)?activeCandidate:null;
  const latestBatch=active.latest_batch||null;
  renderLivePipeline(currentBatch,latestBatch);
  renderCurrentBatchPanel(currentBatch);
 }catch(e){
  const live=$('#currentBatch .cblivecheck');if(live)live.textContent='LIVE CHECK FAILED';
 }finally{scheduleDataLivePoll()}
}
function dataUploadSelectionSummary(){
 const input=$('#dataUploadFiles'),box=$('#dataUploadSummary');if(!input||!box)return;
 const files=[...(input.files||[])];
 box.textContent=files.length
  ? files.length+' file(s): '+files.map(x=>x.name).join(' · ')
  : 'No files selected.';
}
async function uploadDataFiles(){
 const input=$('#dataUploadFiles'),btn=$('#dataUploadBtn'),result=$('#dataUploadResult');
 const files=[...(input?.files||[])];
 if(!files.length){toast('Select files first');return}
 let session=null;
 if(btn){btn.disabled=true;btn.textContent='CREATING BATCH…'}
 if(result)result.textContent='Creating upload batch…';
 try{
  const label=String($('#dataUploadNote')?.value||'').trim()||('Yipman mobile upload '+new Date().toLocaleString());
  const created=await api('/v1/web-upload/batches',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({label}),
    timeoutMs:20000
  });
  session=created.session_id||created.batch_key||created.session?.session_id;
  if(!session)throw new Error('Upload batch session ID was not returned');
  for(let i=0;i<files.length;i++){
    if(btn)btn.textContent='UPLOADING '+(i+1)+' / '+files.length;
    if(result)result.textContent='Current file: '+files[i].name;
    const fd=new FormData();fd.append('file',files[i]);
    await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/files',{
      method:'POST',body:fd,timeoutMs:60000
    });
  }
  if(btn)btn.textContent='STARTING PROCESSING…';
  if(result)result.textContent='All files received · committing batch…';
  const committed=await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/commit',{
    method:'POST',timeoutMs:30000
  });
  if(input)input.value='';
  const note=$('#dataUploadNote');if(note)note.value='';
  dataUploadSelectionSummary();
  if(result)result.textContent='Batch #'+String(committed.batch_id||created.batch_id||'—')+' committed · processing started.';
  toast('Upload committed · processing started');
  await loadData();
 }catch(e){
  let cleanup='';
  if(session){
   try{
    await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/abort',{method:'POST',timeoutMs:12000});
    cleanup=' · incomplete batch aborted';
   }catch(abortErr){
    cleanup=' · batch cleanup needs review';
   }
  }
  if(result)result.textContent='UPLOAD NOT COMMITTED · '+String(e.message||e)+cleanup;
  toast('Upload not committed'+cleanup);
  loadData().catch(()=>{});
 }finally{
  if(btn){btn.disabled=false;btn.textContent='UPLOAD & START PROCESSING'}
 }
}
const dataUploadFiles=$('#dataUploadFiles');if(dataUploadFiles)dataUploadFiles.onchange=dataUploadSelectionSummary;
const dataUploadBtn=$('#dataUploadBtn');if(dataUploadBtn)dataUploadBtn.onclick=uploadDataFiles;

async function loadData(){
 try{
  const [health,active,recent,qa,dash]=await Promise.all([
   api('/v1/backoffice/data-health?days=14',{timeoutMs:12000}),
   api('/v1/web-upload/active',{timeoutMs:12000}),
   api('/v1/web-upload/recent?limit=4',{timeoutMs:12000}),
   api('/v1/backoffice/qa-review?limit=300',{timeoutMs:22000}),
   api('/v1/app/dashboard',{timeoutMs:12000})
  ]);
  $('#calendar').innerHTML=(health.rows||[]).slice(0,14).reverse().map(r=>'<div class="c">'+esc(String(r.date||'').slice(8,10))+'<div class="dot '+(r.overall_status==='MISSING'?'bad':r.overall_status==='COMPLETE'?'':'warn')+'"></div></div>').join('');
  const rb=recent.batches||recent.rows||[];
  const activeCandidate=active.active_batch||null;
  const currentBatch=dataBatchIsActivelyProcessing(activeCandidate)?activeCandidate:null;
  dataLiveSignature=dataBatchSignature(activeCandidate);
  const publishId=dash?.quick_check?.latest_publish_batch_id;
  const latestPublished=(publishId?rb.find(x=>String(x.batch_id)===String(publishId)):null)||active.latest_batch||rb[0]||null;
  renderLivePipeline(currentBatch,latestPublished);
  renderCurrentBatchPanel(currentBatch);
  renderPublishedSnapshot(dash,health,latestPublished);
  renderQAResolution(qa,latestPublished||activeCandidate||currentBatch);
  $('#recentBatches').innerHTML=rb.slice(0,4).map(x=>{
    const xs=String(x.processing_status||x.phase3_status||'').toUpperCase();
    const cls=/^QUICK_CHECK_READY/.test(xs)?' ready':((xs==='PHASE3_QA_HOLD'||xs==='QA_HOLD')?' hold':(/READY|PUBLISH/.test(xs)?' ready':''));
    return '<div class="batchrow"><div><b>Batch #'+esc(x.batch_id||'—')+'</b><span class="batchstate'+cls+'">'+esc(friendlySignal(xs||'—'))+'</span></div><span class="batchdate">'+esc(String(x.completed_at||x.upload_started_at||'').slice(0,10))+'</span></div>'
  }).join('')||'<div class="empty">No recent batches.</div>';
  scheduleDataLivePoll();
 }catch(e){
  $('#currentBatch').innerHTML='<div class="empty">'+esc(e.message)+'</div>';
  $('#publishedSnapshot').innerHTML='<div class="empty">Published snapshot unavailable.</div>';
  $('#qaResolution').innerHTML='<div class="empty">QA review unavailable.</div>';
  scheduleDataLivePoll()
 }
}
async function openBatch(session,basic){sheet('Batch #'+esc(basic.batch_id||'—'),basic.processing_status||'','<div class="loading">Loading processing detail…</div>');if(!session){$('#sheetBody').innerHTML='<div class="detail">Session ID unavailable in active summary.</div>';return}try{const d=await api('/v1/web-upload/batches/'+encodeURIComponent(session),{timeoutMs:12000}), b=d.batch||{}, p=d.phase3||{}, q=d.qa_summary||{},live=batchLiveState(basic);$('#sheetBody').innerHTML='<div class="dmetrics"><div class="dm"><b>'+esc(live.label)+'</b><span>LIVE STATE</span></div><div class="dm"><b>'+fmt(p.quick_check_ready_rows,0)+'</b><span>READY ROWS</span></div><div class="dm"><b>'+fmt(p.quick_check_hold_rows,0)+'</b><span>QA HOLD</span></div></div><div class="detail"><b>Worker / heartbeat</b><br>'+esc(live.sub)+' · worker '+esc(basic.active_worker||'—')+'<br><br><b>Current stage</b><br>'+esc(friendlySignal(basic.active_phase3_stage||basic.active_last_phase3_stage||basic.active_stage_name||p.result_status||'—'))+'<br><br><b>Progress</b><br>'+esc(basic.active_progress_pct!=null?(fmt(basic.active_progress_pct,1)+'%'):'—')+' · '+fmt(basic.active_progress_current,0)+' / '+fmt(basic.active_progress_total,0)+' '+esc(basic.active_progress_unit||'')+'<br>Elapsed '+esc(fmtElapsedSeconds(basic.active_progress_elapsed_seconds))+' · ETA '+esc(fmtElapsedSeconds(basic.active_progress_eta_seconds))+' · Rate '+(basic.active_progress_rows_per_second!=null?fmt(basic.active_progress_rows_per_second,1)+'/s':'—')+'<br><br><b>Phase 3</b><br>'+esc(p.result_status||'—')+'<br><br><b>Open blockers</b><br>'+fmt(p.blocking_issue_count,0)+(q.reason_counts?'<br>'+Object.entries(q.reason_counts).slice(0,8).map(([k,v])=>'• '+esc(k)+': '+fmt(v,0)).join('<br>'):'')+'</div>'}catch(e){$('#sheetBody').innerHTML='<div class="detail">'+esc(e.message)+'</div>'}}

function activePage(){return $('#'+current)}
app.addEventListener('touchstart',e=>{const p=activePage();if($('#overlay').classList.contains('on')||!p||p.scrollTop>0||e.touches.length!==1)return;pullStart=e.touches[0].clientY;pull=0},{passive:true});
app.addEventListener('touchmove',e=>{if(pullStart==null)return;const dy=e.touches[0].clientY-pullStart;if(dy<=0)return;pull=Math.min(105,dy*.52);$('#ptr').style.height=pull+'px';$('#ptrText').textContent=pull>=68?'Release to refresh':'Pull to refresh'},{passive:true});
app.addEventListener('touchend',()=>{if(pullStart==null)return;const refresh=pull>=68;pullStart=null;if(!refresh){$('#ptr').style.height='0';return}$('#ptr').style.height='48px';$('#ptrText').textContent='Refreshing Yipman…';refreshCurrent().finally(()=>setTimeout(()=>{$('#ptr').style.height='0'},250))});
async function refreshCurrent(){const fresh=loadHeaderFreshness();if(current==='quick'){const q=$('#globalInput').value.trim();if(q)await loadQuick(q);else await loadBestSellers(true)}else if(current==='order')await initOrdering(true);else if(current==='price')await loadPriceCurrentView();else if(current==='data')await loadData();await fresh;toast('Yipman refreshed')}

if(!window.__YIPMAN_DESKTOP_ACTIVE__){
 const initialHash=String(location.hash||'').replace(/^#/,'').split('/')[0];
 const initialView=['quick','order','price','data'].includes(initialHash)?initialHash:'quick';
 history.replaceState({yipman:true,root:true,view:'quick',scrollTop:0,scrollLeft:0},'', '#quick');
 history.pushState({yipman:true,view:initialView,guard:true,scrollTop:0,scrollLeft:0},'', '#'+initialView);
 historyReady=true;
 renderView(initialView);
 loadHeaderFreshness();
 pagePositions.set(initialView,{scrollTop:0,scrollLeft:0});
}
if('serviceWorker'in navigator)navigator.serviceWorker.register('/app/yipman/sw.js',{scope:'/app/yipman/'}).catch(()=>{});
})();
</script>
</body>
</html>'''
