from __future__ import annotations

import json

RC_BASE = "/app/yipman-v1-rc/"

def pwa_manifest() -> str:
    return json.dumps({"name":"YipMan Mobile V1 RC","short_name":"YipMan","id":RC_BASE,"start_url":RC_BASE,"scope":RC_BASE,"display":"standalone","display_override":["standalone","minimal-ui"],"background_color":"#0b1117","theme_color":"#0b1117","description":"FULL MYSQL seafood Mobile V1 release candidate","icons":[{"src":RC_BASE+"icon.svg","sizes":"any","type":"image/svg+xml","purpose":"any maskable"}]},separators=(",",":"))

def pwa_service_worker() -> str:
    return r"""
const CACHE='yipman-v1-rc-standalone-v2';
const SHELL=['/app/yipman-v1-rc/','/app/yipman-v1-rc/manifest.webmanifest','/app/yipman-v1-rc/icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('yipman-v1-rc-standalone-')&&k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const u=new URL(e.request.url);if(u.origin!==self.location.origin)return;if(u.pathname.startsWith('/v1/'))return;if(!u.pathname.startsWith('/app/yipman-v1-rc/'))return;e.respondWith(fetch(e.request,{cache:'no-store'}).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/app/yipman-v1-rc/'))))});
"""

def pwa_icon_svg() -> str:
    return """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 512 512\"><rect width=\"512\" height=\"512\" rx=\"112\" fill=\"#0b1117\"/><rect x=\"38\" y=\"38\" width=\"436\" height=\"436\" rx=\"92\" fill=\"#174b77\"/><path d=\"M143 112h72l43 91 43-91h70l-81 151v104h-66V263z\" fill=\"#fff\"/><circle cx=\"390\" cy=\"390\" r=\"54\" fill=\"#0b1117\"/><text x=\"390\" y=\"410\" font-family=\"Arial,sans-serif\" font-size=\"52\" font-weight=\"900\" text-anchor=\"middle\" fill=\"#79c890\">1</text></svg>"""

def polish_pwa_html(html: str) -> str:
    marker="yipmanV1RcStandalonePwa"
    if marker in html:return html
    head=f'''\n<meta name="mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n<meta name="apple-mobile-web-app-title" content="YipMan">\n<link rel="manifest" href="{RC_BASE}manifest.webmanifest">\n<link rel="icon" href="{RC_BASE}icon.svg" type="image/svg+xml">\n<meta name="{marker}" content="1">\n'''
    boot=f'''\n<script id="{marker}">(function(){{const standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;document.documentElement.classList.toggle('standalone-app',standalone);if('serviceWorker' in navigator){{addEventListener('load',()=>navigator.serviceWorker.register('{RC_BASE}sw.js',{{scope:'{RC_BASE}'}}).catch(()=>{{}}))}}}})();</script>\n'''
    html=html.replace('</head>',head+'</head>',1)
    html=html.replace('</body>',boot+'</body>',1)
    return html

def install_html(version: str="") -> str:
    v=str(version or "")
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#0b1117"><meta name="mobile-web-app-capable" content="yes"><link rel="manifest" href="{RC_BASE}manifest.webmanifest"><link rel="icon" href="{RC_BASE}icon.svg" type="image/svg+xml"><title>Install YipMan Mobile V1 RC</title><style>*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:#0b1117;color:#eef5fa;font-family:Arial,sans-serif;display:grid;place-items:center;padding:22px}}.card{{width:min(100%,430px);background:#17212b;border:1px solid #314252;border-radius:24px;padding:22px}}h1{{margin:0;font-size:28px}}p,.status,.note{{line-height:1.45}}p{{color:#a8b5c0;font-size:13px}}button,a{{width:100%;min-height:54px;border-radius:14px;font-size:14px;font-weight:1000}}button{{border:0;background:#1769e0;color:#fff;margin-top:10px}}button:disabled{{background:#526577}}a{{display:grid;place-items:center;border:1px solid #425464;color:#cfe0ec;text-decoration:none;margin-top:9px}}.status{{margin-top:12px;padding:11px;border-radius:12px;background:#101820;color:#95a6b4;font-size:11px;font-weight:800}}.note{{margin-top:11px;color:#778997;font-size:10px}}</style></head><body><div class="card"><h1>YipMan Mobile V1</h1><p>Install the RC as a standalone Android app. Launching it from the installed Home-screen icon hides Chrome's address bar and browser controls.</p><button id="installBtn" disabled>PREPARING INSTALL…</button><a href="{RC_BASE}">OPEN RC</a><div class="status" id="status">Preparing the standalone installer…</div><div class="note">If you previously added the RC as a normal shortcut, remove that old shortcut/app first, then install again from this page. · {v}</div></div><script>let p=null;const b=document.getElementById('installBtn'),s=document.getElementById('status');const standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;function fallback(){{if(standalone){{b.disabled=true;b.textContent='ALREADY RUNNING STANDALONE';s.textContent='YipMan is already open in standalone mode.';return}}b.disabled=false;b.textContent='SHOW INSTALL STEPS';s.innerHTML='In Chrome: tap <b>⋮</b> → <b>Install app</b>. Then launch YipMan from the Home-screen app icon.'}}addEventListener('beforeinstallprompt',e=>{{e.preventDefault();p=e;b.disabled=false;b.textContent='INSTALL YIPMAN';s.textContent='Standalone installer is ready.'}});addEventListener('appinstalled',()=>{{p=null;b.disabled=true;b.textContent='INSTALLED';s.textContent='Installed. Launch YipMan from its Home-screen app icon.'}});b.onclick=async()=>{{if(p){{await p.prompt();await p.userChoice;p=null}}fallback()}};if('serviceWorker'in navigator)navigator.serviceWorker.register('{RC_BASE}sw.js',{{scope:'{RC_BASE}'}}).then(()=>navigator.serviceWorker.ready).then(fallback).catch(fallback);else fallback();</script></body></html>'''
