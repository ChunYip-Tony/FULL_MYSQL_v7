from __future__ import annotations

WEBAPP_V2_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>FULL MYSQL V2</title>
<style>
:root{color-scheme:light dark;--bg:#f3f6fb;--card:#fff;--text:#101828;--muted:#596579;--line:#d8e0eb;--a:#185adb;--a2:#1246ad;--soft:#edf4ff;--ok:#067647;--bad:#b42318;--warn:#a84707;--sale:#b4236a;--shadow:0 7px 22px rgba(15,23,42,.08)}
@media(prefers-color-scheme:dark){:root{--bg:#0b1018;--card:#151c26;--text:#f7f8fa;--muted:#b1bac8;--line:#334052;--a:#82adff;--a2:#9abaff;--soft:#18263d;--ok:#63d8a0;--bad:#ff8a83;--warn:#ffc15a;--sale:#ff8bd1;--shadow:0 9px 26px rgba(0,0,0,.28)}}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top,var(--soft),transparent 460px),var(--bg);color:var(--text);font:19px/1.62 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding-bottom:108px}
.w{max-width:1080px;margin:auto;padding:14px}
.top{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(16px);padding:10px 0 12px;border-bottom:1px solid color-mix(in srgb,var(--line) 65%,transparent)}
.brand{display:flex;justify-content:space-between;align-items:flex-end;gap:10px}.brand h1{font-size:29px;margin:0;letter-spacing:.01em}.ver,.meta,.msg,.small{font-size:16px;color:var(--muted)}
button,input,select{font:inherit;color:var(--text);background:var(--card);border:2px solid var(--line);border-radius:16px;padding:15px 16px;min-height:60px;font-size:19px}
button{font-weight:800;cursor:pointer;transition:.15s transform,.15s border-color}.primary{background:linear-gradient(135deg,var(--a),var(--a2));color:#fff;border-color:transparent;box-shadow:0 6px 17px color-mix(in srgb,var(--a) 22%,transparent)}
button:active{transform:scale(.985)} input,select{width:100%}input:focus,select:focus{outline:4px solid color-mix(in srgb,var(--a) 18%,transparent);border-color:var(--a)}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.grow{flex:1}.card{background:color-mix(in srgb,var(--card) 98%,transparent);border:1.5px solid var(--line);border-radius:20px;padding:17px;margin:13px 0;box-shadow:var(--shadow)}
.result{cursor:pointer;position:relative;padding-right:43px}.result:after{content:'›';position:absolute;right:15px;top:50%;transform:translateY(-50%);font-size:30px;font-weight:400;color:var(--muted)}.result:hover{border-color:var(--a)}
.name{font-weight:900;font-size:21px}.screen{display:none;animation:fade .16s ease}.screen.on{display:block}@keyframes fade{from{opacity:.5;transform:translateY(3px)}to{opacity:1;transform:none}}
.head{display:flex;gap:13px;align-items:center;margin:18px 0}.title{font-size:29px;font-weight:950;line-height:1.18}.back{width:60px;min-width:60px;height:60px;padding:0;border-radius:50%;font-size:27px;background:var(--card)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.m{background:color-mix(in srgb,var(--soft) 58%,var(--card));border:1.5px solid color-mix(in srgb,var(--line) 86%,transparent);border-radius:17px;padding:14px;min-height:92px}.m .k{font-size:14px;letter-spacing:.02em;color:var(--muted);font-weight:850}.m .v{font-size:23px;font-weight:950;margin-top:5px;overflow-wrap:anywhere}
.form{display:grid;grid-template-columns:1fr;gap:13px}label{display:block;font-size:16px;color:var(--muted);font-weight:850;margin-bottom:6px}.pill{display:inline-flex;align-items:center;border:1.5px solid currentColor;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:850;background:color-mix(in srgb,currentColor 7%,transparent)}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.sale{color:var(--sale)}
.actions{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:15px}.actions button{min-height:82px;border-radius:18px;font-size:19px;background:var(--card);box-shadow:var(--shadow)}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:16px}th,td{padding:14px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--muted);font-size:14px;text-transform:uppercase;letter-spacing:.025em;background:var(--card)}.scroll{overflow:auto;border-radius:14px}.hide{display:none!important}
.chart{width:100%;height:270px;border:1.5px solid var(--line);border-radius:16px;background:var(--card);margin-top:10px}.big{font-size:40px;font-weight:950;letter-spacing:-.02em}.order{border-left:6px solid var(--a)}.promo{border:1.5px solid var(--line);border-radius:16px;padding:12px;margin:9px 0;background:color-mix(in srgb,var(--soft) 52%,var(--card))}
.section{font-size:22px;font-weight:950;margin:2px 0 8px}.hint{padding:12px 14px;border-radius:14px;background:var(--soft);color:var(--muted);font-size:16px}.hero-number{font-size:32px;font-weight:950}.price-arrow{font-size:22px;font-weight:900}.report-item{border-left:6px solid var(--warn)}
.nav{position:fixed;left:0;right:0;bottom:0;z-index:20;background:color-mix(in srgb,var(--card) 95%,transparent);border-top:1.5px solid var(--line);padding:7px max(8px,env(safe-area-inset-right)) calc(7px + env(safe-area-inset-bottom)) max(8px,env(safe-area-inset-left));backdrop-filter:blur(18px);box-shadow:0 -8px 26px rgba(15,23,42,.08)}.navin{max-width:1080px;margin:auto;display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.nav button{border:0;background:transparent;color:var(--muted);font-size:14px;line-height:1.25;border-radius:15px;min-height:72px;padding:8px 4px}.nav button.on{color:var(--a);background:color-mix(in srgb,var(--a) 11%,transparent)}
.search-bar{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;align-items:center}
.clear-btn{background:transparent;color:var(--muted);border-color:var(--line);min-width:82px}
.result{transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}
.result:active{transform:scale(.992)}
.family-result{border:2px solid color-mix(in srgb,var(--a) 62%,var(--line));background:linear-gradient(135deg,color-mix(in srgb,var(--a) 10%,var(--card)),var(--card))}
.family-badge{display:inline-block;padding:5px 10px;border-radius:999px;background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a);font-size:14px;font-weight:950;letter-spacing:.02em;margin-bottom:7px}
.result-upc{font-size:25px;font-weight:950;letter-spacing:.025em;margin-top:4px;color:var(--text)}
.result-number{font-size:21px;font-weight:900;margin-top:4px}
.result-type{font-size:14px;font-weight:850;color:var(--muted)}
.audit-ok{border-left:6px solid var(--ok)}
.audit-warn{border-left:6px solid var(--warn)}
html,body{max-width:100%;overflow-x:hidden}
.w,.screen,.card,.head,.head>div,.row,.row>*{min-width:0;max-width:100%}
.meta,.msg,.small,.name,.title,.result-upc,.result-number,.result-type{overflow-wrap:anywhere;word-break:break-word}
.grid,.actions,.form,.search-bar,.navin{min-width:0;max-width:100%}
.group-block{border:1.5px solid var(--line);border-radius:20px;padding:15px;margin:12px 0;box-shadow:var(--shadow)}
.group-title{font-size:18px;font-weight:950;margin-bottom:10px}
.group-identity{background:linear-gradient(135deg,color-mix(in srgb,#4f7cff 15%,var(--card)),var(--card));border-color:color-mix(in srgb,#4f7cff 38%,var(--line))}
.group-sales{background:linear-gradient(135deg,color-mix(in srgb,#16a36a 14%,var(--card)),var(--card));border-color:color-mix(in srgb,#16a36a 36%,var(--line))}
.group-inventory{background:linear-gradient(135deg,color-mix(in srgb,#f59e0b 16%,var(--card)),var(--card));border-color:color-mix(in srgb,#f59e0b 40%,var(--line))}
.group-delivery{background:linear-gradient(135deg,color-mix(in srgb,#8b5cf6 14%,var(--card)),var(--card));border-color:color-mix(in srgb,#8b5cf6 36%,var(--line))}
.group-price{background:linear-gradient(135deg,color-mix(in srgb,#ec4899 13%,var(--card)),var(--card));border-color:color-mix(in srgb,#ec4899 34%,var(--line))}
.group-block .m{background:color-mix(in srgb,var(--card) 82%,transparent);box-shadow:none}
.related-list{display:grid;gap:10px;margin-top:10px}
.related-card{border:1.5px solid var(--line);border-radius:17px;padding:13px;background:var(--card);box-shadow:var(--shadow);cursor:pointer}
.related-upc{font-size:22px;font-weight:950;letter-spacing:.02em;overflow-wrap:anywhere}
.review-actionable{border-left:7px solid var(--ok)}
.review-only{border-left:7px solid var(--warn)}
.review-hold{border-left:7px solid var(--bad)}
.review-badge{font-weight:950;font-size:13px}
@media(max-width:560px){
  .grid{grid-template-columns:1fr}
  .m{min-height:78px}
  .card,.group-block{width:100%;max-width:100%}
  table{font-size:14px}
  .result{padding-right:34px}
  .result:after{right:10px}
  .hero-number{font-size:28px}
}

@media(max-width:560px){.search-bar{grid-template-columns:minmax(0,1fr) auto}.search-bar .primary{grid-column:1/-1}.clear-btn{min-width:76px}}
@media(min-width:760px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}.form{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){body{font-size:18px}.w{padding:11px}.card{padding:15px}.m .v{font-size:21px}.m .k{font-size:13px}.title{font-size:26px}.actions{grid-template-columns:1fr}.actions button{font-size:19px;min-height:72px}.nav button{font-size:13px;min-height:68px}.scroll{margin-left:-4px;margin-right:-4px}}

/* v7.0.123 modern flat UI */
:root{--gp:#7c3aed;--section-blue:#2563eb;--section-green:#059669;--section-amber:#d97706;--section-purple:#7c3aed;--section-pink:#db2777}
body{font-size:17px;line-height:1.5;padding-bottom:86px;background:var(--bg)}
.w{max-width:980px;padding:12px 16px}
.brand h1{font-size:24px}.ver,.meta,.msg,.small{font-size:14px}
button,input,select{min-height:50px;font-size:16px;padding:11px 13px;border-radius:12px;border-width:1.5px}
.head{margin:14px 0;gap:10px}.title{font-size:24px}.back{width:48px;min-width:48px;height:48px;font-size:22px}
.nav{box-shadow:none;border-top:1px solid var(--line);padding-top:5px}.nav button{min-height:58px;font-size:12px;border-radius:10px}
.card{background:transparent;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:16px 0;margin:0;box-shadow:none}
.promo{background:transparent;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:12px 0;margin:0}
.hint{background:transparent;border-left:3px solid var(--a);border-radius:0;padding:6px 10px;font-size:14px}
.section{font-size:18px;margin:6px 0 10px}
.group-block{background:transparent!important;border:0!important;border-radius:0;padding:0;margin:0 0 18px;box-shadow:none!important}
.group-title{font-size:15px;text-transform:uppercase;letter-spacing:.055em;padding:8px 0;margin:0;border-bottom:2px solid var(--line)}
.group-identity .group-title{color:var(--section-blue);border-color:color-mix(in srgb,var(--section-blue) 35%,var(--line))}
.group-sales .group-title{color:var(--section-green);border-color:color-mix(in srgb,var(--section-green) 35%,var(--line))}
.group-inventory .group-title{color:var(--section-amber);border-color:color-mix(in srgb,var(--section-amber) 38%,var(--line))}
.group-delivery .group-title{color:var(--section-purple);border-color:color-mix(in srgb,var(--section-purple) 35%,var(--line))}
.group-price .group-title{color:var(--section-pink);border-color:color-mix(in srgb,var(--section-pink) 35%,var(--line))}
.group-block .grid{display:block}
.group-block .m{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;background:transparent;border:0;border-bottom:1px solid color-mix(in srgb,var(--line) 75%,transparent);border-radius:0;padding:11px 0;min-height:0}
.group-block .m .k{font-size:13px;min-width:120px;text-transform:none}
.group-block .m .v{font-size:17px;text-align:right;margin:0}
.metric-section{margin:0 0 19px}
.metric-section-title{font-size:14px;font-weight:900;text-transform:uppercase;letter-spacing:.065em;padding:8px 0;border-bottom:2px solid var(--line)}
.metric-section.blue .metric-section-title{color:var(--section-blue);border-color:color-mix(in srgb,var(--section-blue) 38%,var(--line))}
.metric-section.green .metric-section-title{color:var(--section-green);border-color:color-mix(in srgb,var(--section-green) 38%,var(--line))}
.metric-section.amber .metric-section-title{color:var(--section-amber);border-color:color-mix(in srgb,var(--section-amber) 40%,var(--line))}
.metric-section.purple .metric-section-title{color:var(--section-purple);border-color:color-mix(in srgb,var(--section-purple) 38%,var(--line))}
.metric-section.pink .metric-section-title{color:var(--section-pink);border-color:color-mix(in srgb,var(--section-pink) 38%,var(--line))}
.metric-row{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding:10px 0;border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent)}
.metric-row:last-child{border-bottom:0}.metric-key{font-size:13px;color:var(--muted);font-weight:750;min-width:120px}.metric-value{font-size:16px;font-weight:800;text-align:right;overflow-wrap:anywhere}
.metric-note{font-size:12px;color:var(--muted);margin-top:2px;text-align:right}
.related-list{gap:0}.related-card{background:transparent;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:13px 0;box-shadow:none}
.result{background:transparent!important;border:0!important;border-bottom:1px solid var(--line)!important;border-radius:0!important;box-shadow:none!important;margin:0!important;padding:13px 36px 13px 0!important}
.result:hover{background:color-mix(in srgb,var(--soft) 42%,transparent)!important}
.family-result{background:linear-gradient(90deg,color-mix(in srgb,var(--a) 10%,transparent),transparent 78%)!important;border-left:4px solid var(--a)!important;padding-left:10px!important}
.family-badge{font-size:11px;padding:3px 7px;border-radius:6px;margin-bottom:4px}
.result-upc{font-size:21px}.result-number{font-size:18px}.name{font-size:18px}
.upc-type{display:inline-flex;margin-top:5px;padding:3px 7px;border-radius:999px;background:color-mix(in srgb,var(--a) 9%,transparent);color:var(--a);font-size:11px;font-weight:850}
.actions{gap:8px;margin-top:12px}.actions button{min-height:54px;font-size:15px;border-radius:11px;box-shadow:none}
.chart{height:285px;border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent}
.big,.hero-number{font-size:27px}
.search-bar{gap:8px}
@media(max-width:560px){
  body{font-size:16px}.w{padding:10px 13px}.title{font-size:22px}.brand h1{font-size:22px}
  .metric-row{gap:12px}.metric-key{min-width:105px}.metric-value{font-size:15px}
  .actions{grid-template-columns:repeat(3,1fr)}.actions button{font-size:14px;min-height:52px;padding:8px 5px}
  .grid{grid-template-columns:1fr 1fr}.m{min-height:0}.m .v{font-size:16px}.m .k{font-size:12px}
  .nav button{min-height:56px;font-size:11px}.search-bar .primary{grid-column:auto}
}


/* v7.0.124 fish-market compact mobile layer */
:root{--sea:#063b59;--sea2:#075a78;--ice:#dff4fa;--gpbar:#2563eb;--pricecurve:#f07b16}
body{
  background:
    linear-gradient(rgba(3,43,66,.77),rgba(4,57,77,.78)),
    radial-gradient(circle at 16% 12%,rgba(139,224,242,.28),transparent 31%),
    radial-gradient(circle at 84% 58%,rgba(16,132,159,.25),transparent 28%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='260' height='150' viewBox='0 0 260 150'%3E%3Cg fill='none' stroke='%23c8edf4' stroke-opacity='.15' stroke-width='2'%3E%3Cpath d='M16 28c18-14 39-12 57 0-18 14-39 14-57 0zm57 0 16-10v20z'/%3E%3Cpath d='M154 95c22-15 46-13 66 1-20 16-45 16-66-1zm66 1 18-12v24z'/%3E%3Cpath d='M38 118c10-7 22-7 32 0-10 8-22 8-32 0zm32 0 9-6v12z'/%3E%3C/g%3E%3C/svg%3E");
  background-size:auto,auto,auto,260px 150px;background-attachment:fixed
}
.top{margin:0 -16px;padding-left:16px;padding-right:16px;background:linear-gradient(90deg,rgba(4,49,74,.97),rgba(6,87,112,.94));border-bottom-color:rgba(206,239,249,.24);color:#f5fcff}
.top .ver,.top .msg{color:#c9e7f2}.brand h1:before{content:"🐟 ";font-size:.9em}
.screen{background:color-mix(in srgb,var(--bg) 91%,transparent);border-radius:15px;padding:0 11px 8px;backdrop-filter:blur(8px)}
.metric-section,.card{background:color-mix(in srgb,var(--card) 94%,transparent);border-radius:11px!important;padding:10px 11px!important;margin:7px 0!important;border:1px solid color-mix(in srgb,var(--line) 82%,transparent)!important}
.metric-section-title{padding-top:3px}
.nav{background:rgba(4,45,69,.97);border-top-color:rgba(205,239,249,.22)}.nav button{color:#bcdbe8}.nav button.on{color:#fff;background:rgba(108,197,237,.16)}
.navin{grid-template-columns:repeat(4,1fr)}
.price-duo{display:grid;grid-template-columns:1fr;gap:7px}.sweet-hero{font-size:28px;font-weight:950;color:var(--ok);line-height:1.05;margin:5px 0}
.price-history{width:100%;border-collapse:collapse;font-size:13px}.price-history th,.price-history td{padding:6px 5px}
.trend-up{color:var(--ok);font-weight:850}.trend-down{color:var(--bad);font-weight:850}.trend-flat{color:var(--muted);font-weight:750}
.chart-scroll{overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;border-bottom:1px solid var(--line)}.chart-scroll .chart{width:920px;min-width:920px;height:285px;border:0;margin:0}
.oh-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:7px}.oh-cell{border-right:1px solid var(--line);padding-right:5px}.oh-cell:last-child{border:0}.oh-cell .k{font-size:11px;color:var(--muted)}.oh-cell .v{font-size:15px;font-weight:850}
@media(min-width:760px){.price-duo{grid-template-columns:1.15fr .85fr}.screen{padding-left:16px;padding-right:16px}.chart-scroll .chart{width:100%;min-width:900px}}
@media(max-width:560px){.w{padding:8px}.top{margin:0 -8px;padding-left:10px;padding-right:10px}.screen{border-radius:11px;padding:0 8px 7px}.metric-section,.card{padding:8px 9px!important}.metric-row{padding:7px 0}.metric-section-title{font-size:12px}.nav button{font-size:9px;line-height:1.05}.oh-row{grid-template-columns:1fr 1fr 1fr}}


/* v7.0.125 mockup-faithful Quick Check detail */
body.detail-open .top{display:none}
#upc.qc-screen{padding:0 8px 10px;background:transparent;border-radius:0}
.qc-shell{
  position:relative;overflow:hidden;border-radius:22px;padding:0 0 12px;
  background:
    linear-gradient(rgba(1,45,68,.30),rgba(1,53,75,.38)),
    radial-gradient(circle at 18% 15%,rgba(185,241,248,.34),transparent 25%),
    radial-gradient(circle at 82% 42%,rgba(27,134,157,.26),transparent 26%),
    repeating-linear-gradient(132deg,rgba(255,255,255,.025) 0 9px,rgba(0,52,79,.05) 9px 18px);
  box-shadow:0 13px 36px rgba(0,27,43,.24)
}
.qc-shell:before,.qc-shell:after{content:"";position:absolute;inset:auto;pointer-events:none;opacity:.18;z-index:0}
.qc-shell:before{width:240px;height:120px;right:-35px;top:76px;background:
  url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='120' viewBox='0 0 240 120'%3E%3Cg fill='none' stroke='%23d8f4fa' stroke-width='3'%3E%3Cpath d='M20 54c35-28 77-27 112 0-35 28-77 28-112 0zm112 0 29-19v38z'/%3E%3Cpath d='M112 24c24-19 54-18 79 1-25 20-55 20-79-1zm79 1 22-14v28z'/%3E%3C/g%3E%3C/svg%3E") center/contain no-repeat}
.qc-shell:after{width:250px;height:160px;left:-55px;bottom:48px;background:
  radial-gradient(ellipse at center,rgba(211,246,251,.55),rgba(211,246,251,0) 66%)}
.qc-topbar{position:relative;z-index:2;height:62px;display:grid;grid-template-columns:44px 1fr auto;align-items:center;gap:7px;padding:8px 13px;color:#fff;background:linear-gradient(180deg,rgba(2,53,78,.82),rgba(2,66,91,.55));border-bottom:1px solid rgba(216,242,249,.18)}
.qc-back{border:0;background:transparent;color:#fff;min-height:42px;height:42px;padding:0;font-size:33px;box-shadow:none}
.qc-title{font-size:23px;font-weight:950;letter-spacing:.01em}
.qc-market-sign{border:1px solid rgba(255,255,255,.35);border-radius:8px;padding:4px 7px;background:linear-gradient(180deg,#5b3c22,#3b2617);color:#fff2d9;font:900 10px/1.05 Georgia,serif;letter-spacing:.04em;box-shadow:0 3px 8px rgba(0,0,0,.24)}
.qc-market-sign:before{content:"🐟 ";font-family:system-ui}
.qc-content{position:relative;z-index:1;padding:8px}
.qc-card{background:linear-gradient(135deg,rgba(249,254,255,.97),rgba(225,242,249,.95));color:#0c2b45;border:1px solid rgba(255,255,255,.78);border-radius:15px;box-shadow:0 5px 13px rgba(0,39,59,.20);margin:8px 0;overflow:hidden}
@media(prefers-color-scheme:dark){.qc-card{background:linear-gradient(135deg,rgba(239,249,252,.97),rgba(218,239,246,.96));color:#0c2b45}}
.qc-hero{display:grid;grid-template-columns:94px minmax(0,1fr) auto;gap:10px;align-items:center;padding:10px 11px;background:
  linear-gradient(90deg,rgba(246,253,255,.98),rgba(225,243,249,.88)),
  repeating-linear-gradient(135deg,transparent 0 12px,rgba(27,111,147,.05) 12px 13px)}
.qc-photo{height:78px;border-radius:10px;display:grid;place-items:center;font-size:46px;background:
  radial-gradient(circle at 50% 20%,rgba(255,255,255,.98),rgba(213,237,244,.74) 55%,rgba(140,195,215,.58) 100%);
  border:1px solid rgba(98,155,181,.24);box-shadow:inset 0 0 15px rgba(26,92,119,.10)}
.qc-name{font-size:19px;font-weight:950;line-height:1.05;color:#0b1b32}.qc-meta{font-size:11px;line-height:1.35;color:#3d5d74;margin-top:4px}
.qc-badges{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}.qc-badge{display:inline-flex;align-items:center;gap:3px;padding:3px 7px;border-radius:8px;font-size:10px;font-weight:900}.qc-fresh{background:#d9f4d4;color:#1d6d29}.qc-reg{background:#dceeff;color:#155e97}.qc-status{align-self:start}
.qc-metrics{display:grid;grid-template-columns:repeat(4,1fr);padding:0}
.qc-metric{padding:9px 10px;border-right:1px solid rgba(76,121,146,.20);border-bottom:1px solid rgba(76,121,146,.16);min-height:64px}
.qc-metric:nth-child(4n){border-right:0}.qc-metric:nth-child(n+5){border-bottom:0}
.qc-metric .k{font-size:11px;color:#3f627c;font-weight:700;white-space:nowrap}.qc-metric .v{font-size:18px;font-weight:950;line-height:1.08;color:#0b182a;margin-top:2px}.qc-metric .v.green{color:#176e32}.qc-metric .trend{font-size:8.5px;line-height:1.1;margin-top:3px;font-weight:850}
.qc-intel{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(120px,.65fr);gap:9px;padding:9px 10px}.qc-intel-title{font-size:13px;font-weight:950;margin-bottom:5px}.qc-intel table{font-size:10px}.qc-intel th,.qc-intel td{padding:4px 3px}.qc-sweet{display:flex;flex-direction:column;justify-content:center;border-left:1px solid rgba(67,117,145,.20);padding-left:10px}.qc-sweet .price{font-size:26px;font-weight:950;color:#0b6f45}.qc-sweet .small{font-size:9px;color:#4c6778}
.qc-two{display:grid;grid-template-columns:1.28fr 1fr;gap:9px}.qc-panel{padding:9px 10px}.qc-panel-title{display:flex;align-items:center;justify-content:space-between;font-size:14px;font-weight:950;margin-bottom:8px}.qc-unit{border:1px solid #7eb5d4;color:#105f94;border-radius:999px;padding:1px 7px;font-size:10px}
.qc-inv-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-bottom:8px}.qc-inv{padding:0 6px;border-right:1px solid rgba(68,115,141,.20)}.qc-inv:first-child{padding-left:0}.qc-inv:last-child{border-right:0;padding-right:0}.qc-inv .k{font-size:9px;color:#395a73}.qc-inv .v{font-size:18px;font-weight:950;margin-top:3px}.qc-inv .blue{color:#0d64d1}.qc-inv .red{color:#d12329}
.qc-true-form{display:grid;grid-template-columns:minmax(0,1fr) 48px 118px;gap:0}.qc-true-form input{min-height:42px;height:42px;padding:7px 9px;border-radius:9px 0 0 9px;border-width:1px;font-size:15px;background:#fff;color:#0b1b32}.qc-true-uom{display:grid;place-items:center;background:#fff;border:1px solid #bdd5e0;border-left:0;font-size:11px;color:#254b66}.qc-true-form button{min-height:42px;height:42px;border-radius:8px;margin-left:7px;padding:5px 10px;font-size:13px}
.qc-order-grid{display:grid;grid-template-columns:1fr 1fr;gap:0}.qc-order-cell{padding:7px 7px;border-right:1px solid rgba(68,115,141,.15);border-bottom:1px solid rgba(68,115,141,.15);min-height:55px}.qc-order-cell:nth-child(2n){border-right:0}.qc-order-cell:nth-child(n+3){border-bottom:0}.qc-order-cell .k{font-size:10px;color:#3f6079}.qc-order-cell .v{font-size:13px;font-weight:950;margin-top:2px}.qc-order-open{border:0;background:transparent;color:#0b66a2;min-height:24px;padding:2px 0;font-size:10px;text-align:left}
.qc-section-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px 0}.qc-section-title{font-size:15px;font-weight:950;display:flex;gap:6px;align-items:center}.qc-legend{display:flex;gap:9px;font-size:9px;color:#31556d;align-items:center}.qc-legend i{display:inline-block;vertical-align:middle;margin-right:3px}.qc-legend .gp{width:18px;height:5px;background:#154a9f;border-radius:4px}.qc-legend .pr{width:18px;height:4px;background:#f27c1a;border-radius:4px}
.qc-chart-scroll{overflow-x:auto;overflow-y:hidden;padding:0 5px 5px}.qc-chart{display:block;height:235px;min-width:760px;width:760px;background:transparent}
.qc-family-head{display:flex;align-items:center;justify-content:space-between;padding:9px 10px 4px}.qc-viewall{border:0;background:transparent;color:#154f77;min-height:28px;padding:2px 0;font-size:10px;box-shadow:none}.qc-family-table{width:100%;font-size:9.5px}.qc-family-table th,.qc-family-table td{padding:5px 6px;border-bottom:1px solid rgba(76,121,146,.17)}.qc-family-table th{background:rgba(196,225,237,.44);color:#244a64}.qc-rel{display:inline-flex;padding:2px 7px;border-radius:999px;background:#d5ebfb;color:#164d73;font-size:9px;white-space:nowrap}.qc-rel.same{background:#e4edf3}.qc-rel.related{background:#fae7c8}
.qc-highlights{padding:8px 10px}.qc-highlights-head{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:950}.qc-count{background:#f7a623;color:#182535;border-radius:999px;padding:2px 7px;font-size:9px}.qc-alert{display:grid;grid-template-columns:22px 1fr 16px;gap:5px;align-items:center;padding:6px 0;border-top:1px solid rgba(75,119,145,.18);font-size:10.5px}.qc-alert:first-of-type{margin-top:5px}.qc-alert-ico{font-size:14px}.qc-chevron{font-size:18px;color:#164e72}
.qc-inline-msg{font-size:9px;color:#49687a;margin-top:5px}
#upc .head,#upc #usum,#upc .actions{display:none!important}
@media(max-width:620px){
  .qc-shell{border-radius:0;margin:0 -8px}
  .qc-content{padding:6px}.qc-topbar{height:55px}
  .qc-hero{grid-template-columns:72px minmax(0,1fr) auto;padding:8px}.qc-photo{height:64px;font-size:37px}
  .qc-name{font-size:17px}.qc-meta{font-size:10px}
  .qc-metric{padding:7px 7px;min-height:58px}.qc-metric .k{font-size:9.5px}.qc-metric .v{font-size:16px}.qc-metric .trend{font-size:7.8px}
  .qc-two{grid-template-columns:1fr 1fr;gap:7px}.qc-panel{padding:8px}.qc-panel-title{font-size:13px}
  .qc-inv-grid{grid-template-columns:repeat(2,1fr);row-gap:8px}.qc-inv:nth-child(2){border-right:0}.qc-inv:nth-child(3){padding-left:0}.qc-inv .k{font-size:8.5px}.qc-inv .v{font-size:16px}
  .qc-true-form{grid-template-columns:minmax(0,1fr) 40px}.qc-true-form button{grid-column:1/-1;margin:6px 0 0;height:38px;min-height:38px}.qc-true-form input{height:38px;min-height:38px}.qc-true-uom{height:38px}
  .qc-order-cell{padding:6px 5px}.qc-order-cell .k{font-size:8.5px}.qc-order-cell .v{font-size:11px}
  .qc-intel{grid-template-columns:1fr}.qc-sweet{border-left:0;border-top:1px solid rgba(67,117,145,.20);padding:8px 0 0}.qc-sweet .price{font-size:22px}
  .qc-chart{height:220px}
  .qc-family-table{font-size:8.8px}.qc-family-table th,.qc-family-table td{padding:5px 4px}
}


/* v7.0.126 global fish-market design system */
:root{
  --fm-navy:#043a59;--fm-navy2:#075d7b;--fm-blue:#0b67a5;--fm-blue2:#07558c;
  --fm-ice:#f7fcff;--fm-ice2:#e3f2f8;--fm-ink:#0c2941;--fm-sub:#49677a;
  --fm-border:rgba(102,157,182,.32);--fm-shadow:0 5px 15px rgba(0,39,59,.18);
  --fm-green:#15723b;--fm-red:#c92a2f;--fm-orange:#f28a22
}
body{
  min-height:100vh;
  background:
    linear-gradient(rgba(2,50,74,.69),rgba(3,62,82,.74)),
    radial-gradient(circle at 15% 10%,rgba(178,237,246,.30),transparent 28%),
    radial-gradient(circle at 83% 48%,rgba(20,126,151,.27),transparent 28%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='280' height='170' viewBox='0 0 280 170'%3E%3Cg fill='none' stroke='%23d6f2f7' stroke-opacity='.13' stroke-width='2'%3E%3Cpath d='M12 37c25-19 55-19 80 0-25 20-55 20-80 0zm80 0 22-14v28z'/%3E%3Cpath d='M156 109c31-23 67-22 97 1-30 23-67 23-97-1zm97 1 25-16v32z'/%3E%3Cpath d='M46 145c13-10 29-10 42 0-13 11-29 11-42 0zm42 0 12-8v16z'/%3E%3C/g%3E%3C/svg%3E");
  background-size:auto,auto,auto,280px 170px;
  background-attachment:fixed;
  color:var(--fm-ink)
}
.top{display:none!important}
.w{max-width:980px;padding:8px 8px 18px}
.screen{background:transparent!important;border-radius:0!important;padding:0 0 8px!important;backdrop-filter:none!important}

/* Shared page header */
.screen:not(#upc)>.head{
  position:relative;overflow:hidden;min-height:64px;margin:0 -1px 8px;padding:9px 12px;
  display:flex;align-items:center;gap:10px;border-radius:0 0 16px 16px;
  background:
    linear-gradient(180deg,rgba(3,55,82,.97),rgba(3,74,99,.93)),
    radial-gradient(circle at 85% 20%,rgba(186,237,246,.18),transparent 30%);
  border:1px solid rgba(214,242,249,.18);border-top:0;
  box-shadow:0 5px 16px rgba(0,35,54,.23);color:#fff
}
.screen:not(#upc)>.head:before{
  content:"🐟";position:absolute;right:20px;bottom:-15px;font-size:64px;opacity:.09;transform:rotate(-8deg);pointer-events:none
}
.screen:not(#upc)>.head .title{color:#fff;font-size:22px;font-weight:950;line-height:1.08}
.screen:not(#upc)>.head .meta{color:#d6ecf4;font-size:11px;line-height:1.3;margin-top:3px}
.screen:not(#upc)>.head .back{
  position:relative;z-index:2;border:0!important;background:rgba(255,255,255,.08)!important;color:#fff!important;
  width:42px;min-width:42px;height:42px;min-height:42px;padding:0;border-radius:50%!important;box-shadow:none!important
}
#ohreport>.head #ohrefresh{position:relative;z-index:2;background:rgba(255,255,255,.13)!important;border:1px solid rgba(255,255,255,.28)!important;color:#fff!important}

/* Shared ice cards */
.screen:not(#upc) .card,
.screen:not(#upc) .metric-section,
.screen:not(#upc) .group-block,
.screen:not(#upc) .promo,
.screen:not(#upc) .related-card,
.screen:not(#upc) .order,
.screen:not(#upc) .report-item{
  background:linear-gradient(135deg,rgba(249,254,255,.97),rgba(226,243,249,.95))!important;
  color:var(--fm-ink)!important;border:1px solid rgba(255,255,255,.72)!important;
  border-radius:15px!important;padding:10px 11px!important;margin:8px 0!important;
  box-shadow:var(--fm-shadow)!important
}
.screen:not(#upc) .metric-section{overflow:hidden}
.screen:not(#upc) .metric-section-title,
.screen:not(#upc) .group-title,
.screen:not(#upc) .section{
  color:#123c5a!important;font-size:14px!important;font-weight:950!important;
  letter-spacing:.01em!important;text-transform:none!important;border:0!important;
  padding:1px 0 7px!important;margin:0!important
}
.screen:not(#upc) .metric-section-title:before,
.screen:not(#upc) .section:before{content:"▰ ";color:#1b6d9f;font-size:.8em}
.screen:not(#upc) .metric-row{
  padding:7px 0!important;border-bottom:1px solid rgba(82,129,153,.18)!important;gap:10px
}
.screen:not(#upc) .metric-row:last-child{border-bottom:0!important}
.screen:not(#upc) .metric-key{font-size:11px!important;color:#456579!important;min-width:105px!important}
.screen:not(#upc) .metric-value{font-size:14px!important;color:#0d2a42!important;font-weight:900!important}
.screen:not(#upc) .metric-note{font-size:9px!important;color:#658092!important}
.screen:not(#upc) .m{
  background:rgba(255,255,255,.54)!important;border:1px solid rgba(105,157,181,.22)!important;
  border-radius:10px!important;padding:8px!important;min-height:58px!important
}
.screen:not(#upc) .m .k{font-size:10px!important;color:#4b6b7d!important}
.screen:not(#upc) .m .v{font-size:15px!important;color:#0d2941!important}

/* Search bars + controls */
.screen:not(#upc) .search-bar{
  background:linear-gradient(135deg,rgba(248,253,255,.96),rgba(227,244,249,.94));
  border:1px solid rgba(255,255,255,.72);border-radius:14px;padding:7px;margin:7px 0;
  box-shadow:var(--fm-shadow);gap:6px
}
.screen:not(#upc) input,
.screen:not(#upc) select{
  background:rgba(255,255,255,.94)!important;color:#102c43!important;border:1px solid #b7d3e0!important;
  border-radius:9px!important;min-height:42px!important;padding:8px 10px!important;font-size:14px!important;
  box-shadow:inset 0 1px 2px rgba(0,46,69,.05)
}
.screen:not(#upc) input:focus,.screen:not(#upc) select:focus{
  outline:2px solid rgba(14,107,166,.17)!important;border-color:#5b9fc3!important
}
.screen:not(#upc) label{font-size:11px!important;color:#42647b!important;margin-bottom:3px!important}
.screen:not(#upc) button.primary{
  background:linear-gradient(180deg,var(--fm-blue),var(--fm-blue2))!important;color:#fff!important;
  border:0!important;border-radius:9px!important;min-height:42px!important;padding:8px 12px!important;
  box-shadow:0 3px 8px rgba(0,75,119,.20)!important;font-size:13px!important
}
.screen:not(#upc) .clear-btn{
  background:rgba(255,255,255,.70)!important;color:#49697e!important;border:1px solid #b9d2df!important;
  border-radius:9px!important;min-height:42px!important;font-size:12px!important
}
.screen:not(#upc) button:not(.primary):not(.back):not(.clear-btn){
  border-radius:9px;border-color:#b6d1de;background:rgba(248,253,255,.91);color:#164f73
}

/* Results and related entities */
.screen:not(#upc) .result,
.screen:not(#upc) .related-card{
  position:relative;background:linear-gradient(135deg,rgba(249,254,255,.97),rgba(228,244,249,.95))!important;
  border:1px solid rgba(255,255,255,.72)!important;border-radius:14px!important;
  padding:10px 34px 10px 11px!important;margin:7px 0!important;box-shadow:var(--fm-shadow)!important
}
.screen:not(#upc) .result:after{color:#22658c!important}
.screen:not(#upc) .family-result{
  border-left:4px solid #0c70ad!important;background:linear-gradient(90deg,rgba(216,239,249,.98),rgba(246,252,255,.96))!important
}
.screen:not(#upc) .name,.screen:not(#upc) .related-upc,.screen:not(#upc) .result-upc,.screen:not(#upc) .result-number{color:#0d2941!important}
.screen:not(#upc) .meta,.screen:not(#upc) .msg,.screen:not(#upc) .small{color:#526f81!important}
.screen:not(#upc) .family-badge,.screen:not(#upc) .upc-type{
  background:#dbeef9!important;color:#155c87!important;border:0!important;border-radius:999px!important
}

/* Pills */
.screen:not(#upc) .pill{background:rgba(244,251,254,.86)!important;font-size:10px!important;padding:2px 7px!important}
.screen:not(#upc) .pill.ok{color:var(--fm-green)!important}.screen:not(#upc) .pill.bad{color:var(--fm-red)!important}
.screen:not(#upc) .pill.warn{color:#9d5b05!important}.screen:not(#upc) .pill.sale{color:#ad2f6f!important}

/* Tables */
.screen:not(#upc) .scroll{border-radius:10px;overflow:auto}
.screen:not(#upc) table{font-size:11px!important;background:rgba(255,255,255,.28)}
.screen:not(#upc) th{
  background:rgba(185,220,235,.48)!important;color:#264d66!important;font-size:10px!important;
  text-transform:none!important;letter-spacing:0!important;padding:7px 6px!important
}
.screen:not(#upc) td{padding:7px 6px!important;color:#14324a!important;border-bottom-color:rgba(80,127,151,.16)!important}

/* Hints / promo / warnings */
.screen:not(#upc) .hint{
  background:rgba(221,241,249,.66)!important;border:1px solid rgba(126,176,198,.22)!important;border-left:4px solid #2f83ae!important;
  border-radius:9px!important;padding:7px 9px!important;color:#4b687a!important;font-size:10px!important
}
.screen:not(#upc) .promo{border-left:4px solid #2d7fa9!important}
.screen:not(#upc) .audit-ok,.screen:not(#upc) .review-actionable{border-left:4px solid var(--fm-green)!important}
.screen:not(#upc) .audit-warn,.screen:not(#upc) .review-only,.screen:not(#upc) .report-item{border-left:4px solid var(--fm-orange)!important}
.screen:not(#upc) .review-hold{border-left:4px solid var(--fm-red)!important}

/* Charts and report areas */
#price .chart{
  background:rgba(255,255,255,.30)!important;border:1px solid rgba(95,148,173,.18)!important;border-radius:10px!important
}
#price .price-duo{gap:7px}
#performance #persummary .grid,#performance #peranalysis .grid{gap:7px}
#performance .hero-number,#performance .big{color:#0b2940!important}
#ohreport>#ohmsg,#ohreport>#ohhmsg,#pi>#pim,#core>#cmsg{padding:0 4px;color:#d9eef5!important}
#ohreport>.section{color:#fff!important;padding:8px 4px 3px!important}
#ohreport>#ohfilter{max-width:220px;margin-left:4px}

/* PI detail */
#pid #pisum>.metric-section:first-child{border-top:4px solid #d58b18!important}
#pid .card b{color:#123c5a}
#pid #pamsg{margin-top:5px}

/* Ordering */
#corder .card:first-of-type{border-top:4px solid #176f9e!important}
#corder #coout .order{border-left:4px solid #176f9e!important}
#corder .form{gap:8px}

/* Bottom navigation */
.nav{
  background:linear-gradient(180deg,rgba(3,54,79,.97),rgba(2,42,64,.99))!important;
  border-top:1px solid rgba(212,242,250,.22)!important;box-shadow:0 -5px 16px rgba(0,30,47,.24)!important;
  backdrop-filter:blur(14px)!important
}
.navin{gap:6px}
.nav button{
  color:#c7e3ee!important;background:transparent!important;border:0!important;min-height:70px!important;
  border-radius:12px!important;padding:7px 4px!important;display:flex!important;flex-direction:column!important;
  align-items:center!important;justify-content:center!important;gap:4px!important
}
.nav .nav-icon{display:block;font-size:27px!important;line-height:1!important}
.nav .nav-label{display:block;font-size:13px!important;font-weight:900!important;line-height:1.08!important;letter-spacing:.01em}
.nav button.on{background:rgba(116,202,239,.17)!important;color:#fff!important}

/* Compact phone layout across all modules */
@media(max-width:560px){
  body{padding-bottom:88px!important}.w{padding:0 6px 10px!important}
  .screen:not(#upc)>.head{min-height:58px;margin:0 -1px 7px;padding:8px 9px}.screen:not(#upc)>.head .title{font-size:19px}.screen:not(#upc)>.head .meta{font-size:9.5px}
  .screen:not(#upc) .card,.screen:not(#upc) .metric-section,.screen:not(#upc) .group-block,.screen:not(#upc) .promo,.screen:not(#upc) .related-card{padding:8px 9px!important;margin:6px 0!important;border-radius:12px!important}
  .screen:not(#upc) .grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:6px!important}
  .screen:not(#upc) .form{gap:7px!important}
  .screen:not(#upc) .metric-row{padding:6px 0!important}.screen:not(#upc) .metric-key{font-size:10px!important;min-width:92px!important}.screen:not(#upc) .metric-value{font-size:13px!important}
  .screen:not(#upc) .search-bar{margin:6px 0;padding:6px}
  .screen:not(#upc) table{font-size:10px!important}.screen:not(#upc) th,.screen:not(#upc) td{padding:6px 4px!important}
  .nav button{min-height:68px!important;padding:6px 3px!important}
  .nav .nav-icon{font-size:26px!important}
  .nav .nav-label{font-size:12.5px!important}
}


/* v7.0.127 Quick Check search simplification */
#core #cres .result{
  background:linear-gradient(135deg,#effbea,#e2f6df)!important;
  border:1px solid #c4dfbd!important;
}
#core #cres .result.family-result{
  background:linear-gradient(135deg,#fff9dc,#fff1b9)!important;
  border:1px solid #ead78d!important;
  border-left:4px solid #d3a82c!important;
}
#core #cres .family-badge{
  background:#f5dfa0!important;
  color:#6e5710!important;
}


/* v7.0.133 no-client web raw upload */
.navin{grid-template-columns:repeat(3,1fr)!important}
#upload .upload-drop{
  border:2px dashed #75abc5!important;border-radius:14px!important;padding:22px 12px!important;
  text-align:center;background:linear-gradient(135deg,rgba(244,253,255,.97),rgba(222,242,248,.94))!important;
  cursor:pointer
}
#upload .upload-drop.drag{border-color:#1670aa!important;background:#e3f5fb!important}
#upload .upload-icon{font-size:38px;line-height:1;margin-bottom:7px}
#upload .upload-title{font-size:17px;font-weight:950;color:#123c5a}
#upload .upload-sub{font-size:10px;color:#537083;margin-top:4px}
#upload .upload-file{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:7px 0;border-bottom:1px solid rgba(82,129,153,.18)}
#upload .upload-file:last-child{border-bottom:0}
#upload .upload-file-name{font-size:12px;font-weight:850;color:#12344c;overflow-wrap:anywhere}
#upload .upload-file-meta{font-size:9px;color:#60798a;margin-top:2px}
#upload .upload-stage{display:grid;grid-template-columns:20px minmax(0,1fr) auto;gap:7px;align-items:center;padding:7px 0;border-bottom:1px solid rgba(82,129,153,.18)}
#upload .upload-stage:last-child{border-bottom:0}
#upload .upload-stage .ok{color:#15723b}.upload-stage .warn{color:#b46c08}.upload-stage .bad{color:#c92a2f}
#upload .upload-progress{height:8px;background:#d8eaf2;border-radius:999px;overflow:hidden;margin:8px 0}
#upload .upload-progress>div{height:100%;background:linear-gradient(90deg,#0b67a5,#27a2c7);width:0%;transition:width .25s ease}
@media(max-width:560px){.nav .nav-icon{font-size:26px!important}.nav .nav-label{font-size:12.5px!important;font-weight:900!important}}


/* v7.0.135 14-day daily upload coverage calendar */
#upload .upload-calendar-card{padding:10px!important}
#upload .upload-calendar-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap}
#upload .upload-calendar-summary{display:flex;gap:6px;flex-wrap:wrap}
#upload .upload-calendar-chip{border-radius:999px;padding:3px 8px;font-size:9px;font-weight:850;border:1px solid rgba(73,116,140,.16)}
#upload .upload-calendar-chip.updated{background:#dff4df;color:#176b34}
#upload .upload-calendar-chip.partial{background:#fff2c6;color:#855d04}
#upload .upload-calendar-chip.missing{background:#fde0df;color:#a12a31}
#upload .upload-calendar-legend{display:flex;gap:8px;flex-wrap:wrap;font-size:9px;color:#527084;margin:6px 0}
#upload .upload-calendar-legend span:before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:0}
#upload .upload-calendar-legend .updated:before{background:#49a963}
#upload .upload-calendar-legend .partial:before{background:#e7b63d}
#upload .upload-calendar-legend .missing:before{background:#dd5d62}
#upload .upload-calendar-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}
#upload .upload-day{
  min-width:0;min-height:92px;border-radius:10px;padding:6px 5px;border:1px solid rgba(72,118,142,.16);
  background:rgba(255,255,255,.70);display:flex;flex-direction:column;justify-content:space-between
}
#upload .upload-day.updated{background:linear-gradient(180deg,#effbef,#dcf2dd);border-color:#acd6b3}
#upload .upload-day.partial{background:linear-gradient(180deg,#fffbed,#fff0bd);border-color:#ead18a}
#upload .upload-day.missing{background:linear-gradient(180deg,#fff3f2,#fbdad8);border-color:#e4acab}
#upload .upload-day .dow{font-size:8px;text-transform:uppercase;font-weight:850;color:#60798a}
#upload .upload-day .date{font-size:14px;font-weight:950;color:#12364f;margin-top:1px}
#upload .upload-day .state{font-size:8px;font-weight:950;margin-top:4px}
#upload .upload-day.updated .state{color:#17703a}
#upload .upload-day.partial .state{color:#8a6205}
#upload .upload-day.missing .state{color:#a72e34}
#upload .upload-day .srcs{display:grid;grid-template-columns:1fr 1fr;gap:3px;margin-top:5px}
#upload .upload-day .src{
  border-radius:5px;padding:2px 3px;text-align:center;font-size:7.5px;font-weight:850;background:rgba(255,255,255,.60)
}
#upload .upload-day .src.ok{color:#146e37}.upload-day .src.no{color:#b22f36}
#upload .upload-day .need{font-size:7.5px;color:#765c32;margin-top:4px;line-height:1.1}
@media(max-width:560px){
  #upload .upload-calendar-grid{gap:3px}
  #upload .upload-day{min-height:83px;padding:5px 3px;border-radius:8px}
  #upload .upload-day .date{font-size:12px}
  #upload .upload-day .dow,#upload .upload-day .state,#upload .upload-day .need{font-size:7px}
  #upload .upload-day .src{font-size:6.8px;padding:2px 1px}
}


/* v7.0.136 latest OH / live-fresh / frozen report uploads */
#upload .latest-ref-card{padding:10px!important}
#upload .latest-ref-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}
#upload .latest-ref{
  border:1px solid rgba(90,145,171,.22);border-radius:11px;padding:9px;
  background:linear-gradient(135deg,rgba(255,255,255,.82),rgba(231,246,250,.75))
}
#upload .latest-ref .label{font-size:11px;font-weight:950;color:#123d59}
#upload .latest-ref .uploaded{font-size:14px;font-weight:950;color:#0b6a98;margin-top:4px}
#upload .latest-ref .coverage{font-size:9px;color:#536f80;margin-top:4px;line-height:1.25}
#upload .latest-ref .filename{font-size:8px;color:#6a8190;margin-top:5px;overflow-wrap:anywhere}
#upload .latest-ref.missing{background:linear-gradient(135deg,#fff8ed,#fff0dc);border-color:#e6c997}
#upload .latest-ref.missing .uploaded{color:#9b6509}
@media(max-width:560px){
  #upload .latest-ref-grid{grid-template-columns:1fr}
  #upload .latest-ref{padding:8px}
}


/* v7.0.137 OH Discrepancy nested under PI */
#pi .pi-module-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
#pi .pi-module{
  border-radius:13px;padding:11px;border:1px solid rgba(79,134,160,.22);
  background:linear-gradient(135deg,rgba(255,255,255,.92),rgba(229,245,250,.88));
  min-height:72px;display:flex;flex-direction:column;justify-content:center
}
#pi .pi-module.current{
  background:linear-gradient(135deg,#e8f5ff,#d9edf9);
  border-color:#9ec7df
}
#pi .pi-module.action{cursor:pointer;text-align:left}
#pi .pi-module.action:hover{filter:brightness(.985)}
#pi .pi-module .t{font-size:12px;font-weight:950;color:#143b56}
#pi .pi-module .s{font-size:9px;color:#5c7788;margin-top:3px;line-height:1.25}
@media(max-width:480px){#pi .pi-module-grid{grid-template-columns:1fr}}


/* v7.0.138 Upload nested under Reports */
#performance .report-module-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:10px}
#performance .report-module{
  border-radius:13px;padding:11px;border:1px solid rgba(79,134,160,.22);
  background:linear-gradient(135deg,rgba(255,255,255,.92),rgba(229,245,250,.88));
  min-height:72px;display:flex;flex-direction:column;justify-content:center
}
#performance .report-module.current{
  background:linear-gradient(135deg,#e8f5ff,#d9edf9);border-color:#9ec7df
}
#performance .report-module.action{cursor:pointer;text-align:left}
#performance .report-module.action:hover{filter:brightness(.985)}
#performance .report-module .t{font-size:12px;font-weight:950;color:#143b56}
#performance .report-module .s{font-size:9px;color:#5c7788;margin-top:3px;line-height:1.25}
@media(max-width:480px){#performance .report-module-grid{grid-template-columns:1fr}}


/* v7.0.140 Reports: Report / Price Change / Uploads */
#performance .report-analysis-text{
  font-size:11px;line-height:1.58;color:#28495d;white-space:normal
}
#performance .top-seller-compact{
  display:grid;grid-template-columns:minmax(0,1.55fr) .72fr .72fr .72fr;
  gap:7px;align-items:center;padding:7px 4px;border-bottom:1px solid rgba(82,129,153,.18);
  cursor:pointer
}
#performance .top-seller-compact:last-child{border-bottom:0}
#performance .top-seller-compact .rankname{min-width:0}
#performance .top-seller-compact .name{font-size:11px;font-weight:900;color:#123a56;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#performance .top-seller-compact .sub{font-size:8px;color:#6b8190;margin-top:2px}
#performance .top-seller-compact .sv{text-align:right}
#performance .top-seller-compact .sv .k{font-size:7.5px;color:#6b8190;text-transform:uppercase}
#performance .top-seller-compact .sv .v{font-size:10.5px;font-weight:900;color:#12364f;margin-top:1px}
#pricechange .pricechange-list .promo{margin:6px 0!important}
@media(max-width:560px){
  #performance .report-module-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}
  #performance .report-module{padding:8px 5px;min-height:68px}
  #performance .report-module .t{font-size:10px}
  #performance .report-module .s{font-size:7px}
  #performance .top-seller-compact{grid-template-columns:minmax(0,1.35fr) .7fr .7fr .7fr;gap:4px;padding:7px 2px}
  #performance .top-seller-compact .name{font-size:9.5px}
  #performance .top-seller-compact .sv .v{font-size:9px}
}


/* v7.0.143 guarded QA HOLD batch deletion */
#upload .delete-qa-batch{
  width:100%;margin-top:8px;min-height:38px;border:1px solid #d9a3a3!important;
  background:#fff0f0!important;color:#9b252b!important;font-weight:900!important;
}
#upload .delete-qa-batch:hover{background:#ffe5e5!important}

</style></head><body><div class="w">
<div class="top"><div class="brand"><h1>FULL MYSQL</h1><div class="ver">Fish Market V2 · v7.0.143</div></div><div class="msg">Quick Check · PI · OH Discrepancy · Reports</div></div>

<section id="core" class="screen on"><div class="head"><div><div class="title">🔎 Quick Check</div><div class="meta">Search item name, Family Article, Article, or UPC.</div></div></div><div class="search-bar"><input id="cq" placeholder="Search item" autocomplete="off"><button id="cc" class="clear-btn" type="button">Clear</button><button id="cs" class="primary">Search</button></div><div id="cmsg" class="msg"></div><div id="cres"></div></section>

<section id="family" class="screen"><div class="head"><button class="back" data-go="core">‹</button><div><div id="ft" class="title"></div><div id="fs" class="meta"></div></div></div><div id="fsummary"></div><div class="metric-section blue"><div class="metric-section-title">Related UPCs</div><div class="hint">Sorted by 28D Qty, then readiness.</div><div id="fu" class="related-list"></div></div></section>

<section id="upc" class="screen qc-screen">
<div class="qc-shell">
  <div class="qc-topbar"><button class="qc-back" id="ub">‹</button><div class="qc-title">Quick Check</div><div class="qc-market-sign">FISH MARKET</div></div>
  <div class="qc-content">
    <div id="qcHero" class="qc-card qc-hero"></div>
    <div id="qcMetrics" class="qc-card qc-metrics"></div>
    <div id="qcPriceIntel" class="qc-card qc-intel"></div>
    <div class="qc-two">
      <div class="qc-card qc-panel">
        <div class="qc-panel-title"><span>📦 Inventory</span><span id="qcInvUom" class="qc-unit">—</span></div>
        <div id="qcInventory" class="qc-inv-grid"></div>
        <div class="qc-true-form"><input id="qcTrueStock" inputmode="decimal" placeholder="True Stock"><div id="qcTrueUom" class="qc-true-uom">—</div><button id="qcTrueUpdate" class="primary">Update</button></div>
        <div id="qcTrueMsg" class="qc-inline-msg"></div>
      </div>
      <div class="qc-card qc-panel">
        <div class="qc-panel-title"><span>🛒 Ordering</span></div>
        <div id="qcOrdering" class="qc-order-grid"></div>
        <button id="qcOrderOpen" class="qc-order-open">Open ordering analysis ›</button>
      </div>
    </div>
    <div class="qc-card">
      <div class="qc-section-head"><div class="qc-section-title">📊 Sales Trend <span class="small">(Last 28 Days)</span></div><div class="qc-legend"><span><i class="gp"></i>GP$</span><span><i class="pr"></i>Avg Selling Price</span></div></div>
      <div class="qc-chart-scroll"><canvas id="qcChart" class="qc-chart"></canvas></div>
    </div>
    <div class="qc-card">
      <div class="qc-family-head"><div class="qc-section-title">👥 Family / Ordering Article / Related UPC</div><button id="qcFamilyView" class="qc-viewall">View All ›</button></div>
      <div class="scroll"><table class="qc-family-table"><thead><tr><th>Item / Description</th><th>Article</th><th>UPC</th><th>Relationship</th></tr></thead><tbody id="qcFamilyRows"></tbody></table></div>
    </div>
    <div id="qcHighlightsCard" class="qc-card qc-highlights"><div class="qc-highlights-head"><span>⚠️ Highlights / QA</span><span id="qcHighlightCount" class="qc-count">0 items</span></div><div id="qcHighlights"></div></div>
  </div>
</div>
<div id="ut" class="hide"></div><div id="us" class="hide"></div><div id="usum" class="hide"></div><button id="uf" class="hide"></button><button id="upr" class="hide"></button><button id="uo" class="hide"></button>
</section>

<section id="price" class="screen"><div class="head"><button class="back" data-go="upc">‹</button><div><div id="pt" class="title"></div><div id="ps" class="meta"></div></div></div><div id="pc"></div><div class="price-duo"><div class="metric-section pink"><div class="metric-section-title">Price vs Velocity History</div><div id="pvh"></div></div><div class="metric-section green"><div class="metric-section-title">Suggested Sweet Spot</div><div id="psweet"></div></div></div><div class="card"><div class="section">28D Sales Trend</div><div class="chart-scroll"><canvas id="chart" class="chart"></canvas></div><div class="row" style="margin-top:7px"><span class="pill" style="color:var(--gpbar)">▮ GP$</span><span class="pill" style="color:var(--pricecurve)">● Avg Selling Price</span><span class="pill sale">▮ SALE</span></div><div class="hint" style="margin-top:6px">GP$ is shown as columns and Avg Selling Price as a curve. Every plotted value is labeled. Missing supported dates are skipped, not counted as zero.</div></div><div class="card"><div class="section">Past 14D Sales History</div><div id="p14"></div></div><div class="card"><div class="section">Historical SALE Promotions</div><div id="ph"></div></div></section>

<section id="corder" class="screen"><div class="head"><button class="back" data-go="upc">‹</button><div><div id="cot" class="title"></div><div id="cos" class="meta"></div></div></div><div class="card"><div class="form"><div><label>Ordering Date</label><input id="cod" type="date"></div><div><label>Expected Delivery Date</label><input id="cdd" type="date"></div><div><label>Context</label><select id="cop"><option value="0">Regular</option><option value="1">Promotion Involved</option></select></div></div><div id="cpf" class="form hide" style="margin-top:8px"><div><label>Promotion Start</label><input id="cps" type="date"></div><div><label>Promotion End</label><input id="cpe" type="date"></div><div><label>Promotion Price</label><input id="cpp"></div></div><div id="cohist"></div><button id="coa" class="primary" style="margin-top:9px">Analyze</button></div><div id="coout"></div></section>

<section id="ordering" class="screen hide" aria-hidden="true"><div class="head"><div><div class="title">📦 ORDERING</div><div class="meta">Family-level Fresh / Frozen ordering suggestions.</div></div></div><div class="card"><div class="form"><div><label>Fresh or Frozen</label><select id="ot"><option>FRESH</option><option>FROZEN</option></select></div><div><label>Ordering Date</label><input id="od" type="date"></div><div><label>Expected Delivery</label><input id="dd" type="date"></div><div><label>Context</label><select id="op"><option value="0">Regular</option><option value="1">Promotion Involved</option></select></div></div><div id="opa" class="hide"><div class="form" style="margin-top:8px"><div><label>Promotion Start</label><input id="ops" type="date"></div><div><label>Promotion End</label><input id="ope" type="date"></div></div><div class="row" style="margin-top:8px"><input id="oiq" class="grow" placeholder="Search promotion UPC or item name"><button id="ois">Search</button></div><div id="oim" class="msg"></div><div id="oir"></div><div id="oil"></div><div id="ohist"></div></div><button id="ogen" class="primary" style="margin-top:10px">Generate Suggestions</button><div id="omsg" class="msg"></div></div><div id="ores"></div></section>

<section id="pi" class="screen"><div class="head"><div><div class="title">🧮 Physical Inventory</div><div class="meta">Inventory verification, True Stock and OH discrepancy controls.</div></div></div><div class="pi-module-grid"><div class="pi-module current"><div class="t">🧮 Physical Inventory</div><div class="s">Search Family Article and apply True Stock.</div></div><button id="piOHOpen" class="pi-module action" type="button"><div class="t">📋 OH Discrepancy Report</div><div class="s">Review pending discrepancies and cleared / superseded history.</div></button></div><div class="search-bar"><input id="piq" placeholder="Search Family, item, article, or UPC" autocomplete="off"><button id="pic" class="clear-btn" type="button">Clear</button><button id="pis" class="primary">Search</button></div><div id="pim" class="msg"></div><div id="pir"></div></section>

<section id="performance" class="screen">
  <div class="head"><div><div class="title">📊 Reports</div><div class="meta">Performance report, price changes and raw-data uploads.</div></div></div>
  <div class="report-module-grid">
    <div class="report-module current"><div class="t">📊 Report</div><div class="s">Daily performance and sales analysis.</div></div>
    <button id="reportsPriceOpen" class="report-module action" type="button"><div class="t">💲 Price Change</div><div class="s">Open price change suggestions.</div></button>
    <button id="reportsUploadOpen" class="report-module action" type="button"><div class="t">⬆ Uploads</div><div class="s">Raw files and readiness.</div></button>
  </div>
  <div class="card">
    <div><label>Report Date</label><select id="perdate"><option value="">Loading supported dates…</option></select></div>
    <div class="hint" style="margin-top:10px">Uses completed canonical sales data for the full Seafood scope.</div>
    <button id="perrun" class="primary" style="margin-top:12px;width:100%">Generate Report</button>
    <div id="permsg" class="msg" style="margin-top:8px"></div>
  </div>
  <div id="persummary"></div>
  <div id="peranalysis"></div>
  <div class="card">
    <div class="section">Report Date Top 20 Sellers</div>
    <div class="hint">Ranked by sales dollars. Sales, quantity and average sold price are shown for the selected date.</div>
    <div id="pertop"></div>
  </div>
</section>

<section id="pricechange" class="screen">
  <div class="head"><button class="back" id="priceChangeBack" type="button">‹</button><div><div class="title">💲 Price Change Suggestions</div><div class="meta">Reports · Pricing review based on observed sales response and GP$/day opportunity.</div></div></div>
  <div class="card">
    <div><label>Report Date</label><select id="pcdate"><option value="">Loading supported dates…</option></select></div>
    <div class="hint" style="margin-top:10px">Price suggestions use completed sales evidence through the selected date. QA HOLD and active SALE items remain blocked from automatic action.</div>
    <button id="pcrun" class="primary" style="margin-top:12px;width:100%">Generate Price Change Suggestions</button>
    <div id="pcmsg" class="msg" style="margin-top:8px"></div>
  </div>
  <div id="pcitems" class="pricechange-list"></div>
</section>

<section id="ohreport" class="screen"><div class="head"><button class="back" id="ohBack" type="button">‹</button><div><div class="title">📋 OH Discrepancy Report</div><div class="meta">PI · Review and clear inventory discrepancies without changing stock.</div></div><button id="ohrefresh" class="primary" style="margin-left:auto;min-height:44px;padding:8px 12px">Refresh</button></div><div id="ohmsg" class="msg"></div><div id="ohlist"></div><div class="section" style="margin-top:12px">Recent Cleared / Superseded</div><select id="ohfilter" style="margin-bottom:7px"><option value="">All history</option><option value="RESOLVED">Cleared</option><option value="SUPERSEDED">Superseded</option></select><div id="ohhmsg" class="msg"></div><div id="ohhist"></div></section>

<section id="pid" class="screen"><div class="head"><button class="back" data-go="pi">‹</button><div><div id="pit" class="title"></div><div id="pisub" class="meta"></div></div></div><div id="pisum"></div><div class="card"><b>Apply True Stock</b><div class="form" style="margin-top:8px"><div><label>True Stock</label><input id="pqty"></div><div><label>UOM</label><input id="puom" readonly></div></div><div style="margin-top:8px"><label>Note</label><input id="pnote"></div><button id="papply" class="primary" style="margin-top:9px">Apply True Stock</button><div id="pamsg" class="msg"></div></div><div class="card"><b>PI History</b><div class="scroll"><table><thead><tr><th>Time</th><th>System</th><th>True</th><th>Diff</th><th>Status</th><th>Note</th></tr></thead><tbody id="pih"></tbody></table></div></div></section>
<section id="upload" class="screen">
  <div class="head"><button class="back" id="uploadBack" type="button">‹</button><div><div class="title">⬆ Raw File Upload</div><div class="meta">Reports · Upload and view readiness directly in the Web App — no login or Windows client required.</div></div><button id="uploadRefresh" class="primary" style="margin-left:auto">Refresh</button></div>
  <div class="card latest-ref-card">
    <div class="section">Latest Reference Uploads</div>
    <div id="latestRefMsg" class="msg"></div>
    <div id="latestRefUploads" class="latest-ref-grid"></div>
  </div>
  <div id="uploadDrop" class="card upload-drop">
    <div class="upload-icon">📂</div>
    <div class="upload-title">Choose raw files</div>
    <div class="upload-sub">Select multiple XLSX / XLS / XLSM / CSV / TXT / TSV files for one batch.</div>
    <input id="uploadFiles" type="file" multiple accept=".xlsx,.xls,.xlsm,.csv,.txt,.tsv" class="hide">
  </div>
  <div id="uploadSelected" class="card hide">
    <div class="section">Selected Files</div>
    <div id="uploadSelectedList"></div>
    <div class="row" style="justify-content:space-between;margin-top:8px">
      <button id="uploadClear" type="button">Clear</button>
      <button id="uploadStart" class="primary" type="button">Upload Batch</button>
    </div>
  </div>
  <div id="uploadStatusCard" class="card hide">
    <div class="section">Batch Status</div>
    <div id="uploadBatchMeta" class="meta"></div>
    <div class="upload-progress"><div id="uploadProgressBar"></div></div>
    <div id="uploadStatus"></div>
    <div id="uploadServerFiles" style="margin-top:8px"></div>
  </div>
  <div id="uploadMsg" class="msg"></div>
  <div class="card upload-calendar-card">
    <div class="upload-calendar-top">
      <div>
        <div class="section">Past 14 Days</div>
        <div id="uploadCalendarRange" class="small"></div>
      </div>
      <div id="uploadCalendarSummary" class="upload-calendar-summary"></div>
    </div>
    <div class="upload-calendar-legend"><span class="updated">Updated</span><span class="partial">Partial</span><span class="missing">Needs Upload</span></div>
    <div class="small" style="margin-bottom:7px">A day is Updated when both POS and MVT canonical daily data are present.</div>
    <div id="uploadCalendarMsg" class="msg"></div>
    <div id="uploadCalendar" class="upload-calendar-grid"></div>
  </div>
  <div class="section" style="color:#fff!important;margin:13px 4px 5px!important">Recent Uploads</div>
  <div id="uploadRecentMsg" class="msg" style="color:#d9eef5!important"></div>
  <div id="uploadRecent"></div>
</section>

</div>

<nav class="nav"><div class="navin"><button data-main="core" class="on"><span class="nav-icon">🔎</span><span class="nav-label">Quick Check</span></button><button data-main="pi"><span class="nav-icon">🧮</span><span class="nav-label">PI</span></button><button data-main="performance"><span class="nav-icon">📊</span><span class="nav-label">Reports</span></button></div></nav>

<script>
const $=x=>document.getElementById(x),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=2)=>{if(v===null||v===undefined||v==='')return '—';let n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):String(v)},money=v=>v===null||v===undefined?'—':'$'+fmt(v,2);
const today=()=>new Date().toLocaleDateString('en-CA'),nextwd=(s,t)=>{let d=new Date(s+'T12:00:00'),x=(t-d.getDay()+7)%7;if(!x)x=7;d.setDate(d.getDate()+x);return d.toLocaleDateString('en-CA')};const dayName=s=>{if(!s)return '—';return new Intl.DateTimeFormat('en-US',{weekday:'long'}).format(new Date(s+'T12:00:00'))};const promoRange=p=>p.weekday_range||((p.start_weekday||dayName(p.start_date))+' → '+(p.end_weekday||dayName(p.end_date)));
let cupc=null,uback='core',pifamily=null,pitems=[],ohLoaded=false,webUploadFiles=[],webUploadSession=null,webUploadPoll=null;
async function api(p,o={}){let r=await fetch(p,o),b=null;try{b=await r.json()}catch{}if(!r.ok){let d=b?.detail;throw new Error(typeof d==='string'?d:(d?.reason||'HTTP '+r.status))}return b}
function mainForScreen(id){if(['family','upc','price','corder'].includes(id))return 'core';if(['pid','ohreport'].includes(id))return 'pi';if(['upload','pricechange'].includes(id))return 'performance';return id}
function showScreen(id){document.querySelectorAll('.screen').forEach(x=>x.classList.remove('on'));$(id).classList.add('on');document.body.classList.toggle('detail-open',id==='upc');let main=mainForScreen(id);document.querySelectorAll('[data-main]').forEach(x=>x.classList.toggle('on',x.dataset.main===main));if(id==='ohreport'&&!ohLoaded)loadOHReport();if(id==='upload'){loadWebUploadActive();loadLatestReferenceUploads();loadWebUploadCalendar();loadWebUploadRecent();}scrollTo({top:0,behavior:'smooth'})}
function go(id){let cur=document.querySelector('.screen.on')?.id;if(cur===id)return;showScreen(id);history.pushState({fullmysqlV2:true,screen:id},'',location.pathname+location.search+'#'+id)}
history.replaceState({fullmysqlV2:true,screen:'guard'},'',location.pathname+location.search+'#core');history.pushState({fullmysqlV2:true,screen:'core'},'',location.pathname+location.search+'#core');
window.addEventListener('popstate',e=>{let s=e.state;if(s&&s.fullmysqlV2&&s.screen&&s.screen!=='guard'){showScreen(s.screen);return}history.pushState({fullmysqlV2:true,screen:'core'},'',location.pathname+location.search+'#core');showScreen('core')})
function pill(s){s=String(s||'UNKNOWN');let c=s==='READY'?'ok':(s.includes('BLOCK')||s==='QA_HOLD'?'bad':'warn');return '<span class="pill '+c+'">'+esc(s)+'</span>'}
function m(k,v){return '<div class="m"><div class="k">'+esc(k)+'</div><div class="v">'+esc(v)+'</div></div>'}
function qv(v,u){return fmt(v)+' '+esc(u||'UOM UNKNOWN')}
function mr(k,v,note=''){return '<div class="metric-row"><div class="metric-key">'+esc(k)+'</div><div><div class="metric-value">'+esc(v)+'</div>'+(note?'<div class="metric-note">'+esc(note)+'</div>':'')+'</div></div>'}
function ms(title,tone,rows){return '<div class="metric-section '+tone+'"><div class="metric-section-title">'+esc(title)+'</div>'+rows.join('')+'</div>'}

function priceText(v,u){return v===null||v===undefined?'—':money(v)+' / '+String(u||'UOM UNKNOWN')}
function nv(v){let n=Number(v);return Number.isFinite(n)?n:null}
function mrh(k,v,note=''){return '<div class="metric-row"><div class="metric-key">'+esc(k)+'</div><div><div class="metric-value">'+esc(v)+'</div>'+(note?'<div class="metric-note">'+note+'</div>':'')+'</div></div>'}
function blockStats(rows){
  let a=(rows||[]).filter(x=>x&&x.date).slice().sort((x,y)=>String(x.date).localeCompare(String(y.date)));
  let qty=a.reduce((s,x)=>s+(nv(x.sold_quantity)||0),0),sales=a.reduce((s,x)=>s+(nv(x.sales_amount)||0),0);
  let gpVals=a.map(x=>nv(x.gp_dollars)),gpDay=(a.length&&gpVals.every(x=>x!==null))?gpVals.reduce((s,x)=>s+x,0)/a.length:null;
  let cost=null;for(let i=a.length-1;i>=0;i--){let v=nv(a[i].cost_per_selling_unit);if(v!==null){cost=v;break}}
  let avg=qty!==0?sales/qty:null,gpPct=(avg!==null&&avg>0&&cost!==null)?(avg-cost)/avg:null;
  return {rows:a,qty,days:a.length,velocity:a.length?qty/a.length:null,avgPrice:avg,gpDay,cost,gpPct};
}
function trendContext(rows,current,s7){
  let a=(rows||[]).filter(x=>x&&x.date).slice().sort((x,y)=>String(x.date).localeCompare(String(y.date)));
  let cur=blockStats(a.slice(-7)),prev=blockStats(a.slice(-14,-7));
  let cq=nv(s7?.sold_quantity);if(cq===null)cq=cur.qty;
  let cd=nv(s7?.supported_day_count);if(cd===null)cd=cur.days;
  let cv=cd>0?cq/cd:cur.velocity,cp=nv(current?.price),pp=null;
  if(cp!==null){for(let i=a.length-1;i>=0;i--){let p=nv(a[i].avg_sold_price);if(p!==null&&Math.abs(p-cp)>=.005){pp=p;break}}}
  if(pp===null)pp=prev.avgPrice;
  return {
    price:[cp,pp],cost:[nv(current?.cost),prev.cost],gpPct:[nv(current?.gp_pct),prev.gpPct],
    gpDay:[nv(current?.gp_per_day_7d),prev.gpDay],qty:[cq,prev.qty],velocity:[cv,prev.velocity],
    current:cur,previous:prev
  };
}
function trendNote(cur,prev,kind,uom){
  if(cur===null||prev===null||cur===undefined||prev===undefined)return '';
  let d=Number(cur)-Number(prev),cls=d>0?'trend-up':(d<0?'trend-down':'trend-flat'),arrow=d>0?'▲':(d<0?'▼':'•'),abs=Math.abs(d),val='';
  if(kind==='money')val=(d>=0?'+':'-')+'$'+fmt(abs,2)+' / '+esc(uom||'unit');
  else if(kind==='moneyday')val=(d>=0?'+':'-')+'$'+fmt(abs,2)+' / day';
  else if(kind==='pct')val=(d>=0?'+':'-')+fmt(abs*100,1)+' pts';
  else if(kind==='qty')val=(d>=0?'+':'-')+fmt(abs,2)+' '+esc(uom||'unit');
  else if(kind==='velocity')val=(d>=0?'+':'-')+fmt(abs,2)+' '+esc(uom||'unit')+'/day';
  else val=(d>=0?'+':'-')+fmt(abs,2);
  return '<span class="'+cls+'">'+arrow+' '+val+'</span> <span class="small">vs prior 7D</span>';
}
function priceVelocityBuckets(rows){
  let m=new Map();
  (rows||[]).forEach(x=>{
    let p=nv(x.avg_sold_price),q=nv(x.sold_quantity);if(p===null||q===null||q<=0)return;
    let k=p.toFixed(2),b=m.get(k)||{price:Number(k),qty:0,days:0,gp:0,gpDays:0,last:''};
    b.qty+=q;b.days+=1;let g=nv(x.gp_dollars);if(g!==null){b.gp+=g;b.gpDays+=1}
    if(String(x.date)>b.last)b.last=String(x.date);m.set(k,b);
  });
  return [...m.values()].map(b=>({...b,velocity:b.days?b.qty/b.days:null,gpDay:(b.gpDays===b.days&&b.days)?b.gp/b.days:null})).sort((a,b)=>b.last.localeCompare(a.last)||b.price-a.price);
}

function seafoodEmoji(name,category){
  let s=String(name||'').toUpperCase();
  if(s.includes('LOBSTER'))return '🦞';if(s.includes('CRAB'))return '🦀';if(s.includes('SHRIMP')||s.includes('PRAWN'))return '🦐';
  if(s.includes('OYSTER')||s.includes('CLAM')||s.includes('MUSSEL'))return '🦪';if(s.includes('SQUID')||s.includes('CALAMARI'))return '🦑';
  if(s.includes('SALMON'))return '🍣';return String(category||'').toUpperCase()==='LIVE'?'🐠':'🐟';
}
function qcMetric(k,v,trend='',cls=''){return '<div class="qc-metric"><div class="k">'+esc(k)+'</div><div class="v '+cls+'">'+v+'</div>'+(trend?'<div class="trend">'+trend+'</div>':'')+'</div>'}
function qcInv(k,v,cls=''){return '<div class="qc-inv"><div class="k">'+esc(k)+'</div><div class="v '+cls+'">'+v+'</div></div>'}
function qcOrderCell(k,v){return '<div class="qc-order-cell"><div class="k">'+esc(k)+'</div><div class="v">'+v+'</div></div>'}
function shortDate(v){if(!v)return '—';let d=new Date(String(v).slice(0,10)+'T12:00:00');return Number.isNaN(d.getTime())?String(v):d.toLocaleDateString('en-US',{month:'short',day:'numeric',weekday:'short'})}
function coverageDays(delivery,nextNext){if(!delivery||!nextNext)return null;let a=new Date(String(delivery).slice(0,10)+'T12:00:00'),b=new Date(String(nextNext).slice(0,10)+'T12:00:00');let n=Math.round((b-a)/86400000);return Number.isFinite(n)&&n>=0?n:null}


document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>history.back());document.querySelectorAll('[data-main]').forEach(b=>b.onclick=()=>go(b.dataset.main));
$('piOHOpen').onclick=()=>go('ohreport');$('ohBack').onclick=()=>go('pi');
$('reportsPriceOpen').onclick=()=>go('pricechange');$('priceChangeBack').onclick=()=>go('performance');
$('reportsUploadOpen').onclick=()=>go('upload');$('uploadBack').onclick=()=>go('performance');

async function loadOHReport(force=false){
  if(ohLoaded&&!force)return;
  $('ohmsg').textContent='Loading OH discrepancies…';$('ohlist').innerHTML='';$('ohhist').innerHTML='';
  let hs=$('ohfilter')?.value||'',hp='/v1/app/dumping/history?limit=80'+(hs?'&status='+encodeURIComponent(hs):'');
  try{
    let [d,h]=await Promise.all([api('/v1/app/dumping/pending'),api(hp)]);ohLoaded=true;
    $('ohmsg').textContent=(d.count??(d.rows||[]).length)+' pending discrepancy item(s)';
    $('ohhmsg').textContent=(h.count??(h.rows||[]).length)+' history item(s)';
    $('ohlist').innerHTML=(d.rows||[]).map(r=>
      '<div class="card"><div class="row" style="justify-content:space-between"><div><b>Family '+esc(r.main_article_number||r.family_id||'—')+'</b><div class="meta">UPC '+esc(r.ean_upc||'—')+' · Article '+esc(r.article_number||'—')+'</div></div>'+pill(r.queue_status||'PENDING')+'</div>'+
      '<div class="oh-row"><div class="oh-cell"><div class="k">System OH</div><div class="v">'+qv(r.system_oh_quantity,r.uom_code)+'</div></div><div class="oh-cell"><div class="k">True Stock</div><div class="v">'+qv(r.true_stock_quantity,r.uom_code)+'</div></div><div class="oh-cell"><div class="k">Discrepancy</div><div class="v bad">'+qv(r.discrepancy_quantity,r.uom_code)+'</div></div></div>'+
      '<button class="clearOH" data-id="'+esc(r.discrepancy_id)+'" style="margin-top:8px;width:100%">Clear Report</button></div>'
    ).join('')||'<div class="card small">No pending OH discrepancies.</div>';
    $('ohhist').innerHTML=(h.rows||[]).map(r=>
      '<div class="card"><div class="row" style="justify-content:space-between"><b>Family '+esc(r.main_article_number||r.family_id||'—')+'</b>'+pill(r.queue_status)+'</div><div class="meta">UPC '+esc(r.ean_upc||'—')+' · System '+qv(r.system_oh_quantity,r.uom_code)+' → True '+qv(r.true_stock_quantity,r.uom_code)+' · Discrepancy '+qv(r.discrepancy_quantity,r.uom_code)+'</div></div>'
    ).join('')||'<div class="card small">No matching history.</div>';
    document.querySelectorAll('.clearOH').forEach(b=>b.onclick=()=>resolveOHReport(b.dataset.id,b));
  }catch(e){$('ohmsg').textContent=e.message}
}
async function resolveOHReport(id,b){
  if(!id||!confirm('Clear this OH discrepancy report? This closes the report only and does not change inventory.'))return;
  b.disabled=true;b.textContent='Clearing…';
  try{await api('/v1/app/dumping/'+encodeURIComponent(id)+'/resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:'RESOLVE_DUMPING_DISCREPANCY'})});ohLoaded=false;await loadOHReport(true)}
  catch(e){$('ohmsg').textContent=e.message;b.disabled=false;b.textContent='Clear Report'}
}
$('ohrefresh').onclick=()=>{ohLoaded=false;loadOHReport(true)};
$('ohfilter').onchange=()=>{ohLoaded=false;loadOHReport(true)};



function uploadSize(n){
  n=Number(n||0);if(n<1024)return n+' B';if(n<1048576)return (n/1024).toFixed(1)+' KB';return (n/1048576).toFixed(1)+' MB'
}
function setWebUploadFiles(files){
  webUploadFiles=[...(files||[])];
  $('uploadSelected').classList.toggle('hide',webUploadFiles.length===0);
  $('uploadSelectedList').innerHTML=webUploadFiles.map((f,i)=>
    '<div class="upload-file"><div><div class="upload-file-name">'+esc(f.name)+'</div><div class="upload-file-meta">'+esc(uploadSize(f.size))+'</div></div><button type="button" data-rm="'+i+'">×</button></div>'
  ).join('');
  $('uploadSelectedList').querySelectorAll('[data-rm]').forEach(b=>b.onclick=()=>{webUploadFiles.splice(Number(b.dataset.rm),1);setWebUploadFiles(webUploadFiles)});
}
function uploadStage(icon,label,value,cls=''){
  return '<div class="upload-stage"><div>'+icon+'</div><div>'+esc(label)+'</div><div class="'+cls+'"><b>'+esc(value??'—')+'</b></div></div>'
}
function terminalUploadStatus(s){
  s=String(s||'').toUpperCase();
  return s.includes('QUICK_CHECK_READY')||s.includes('QA_HOLD')||s.includes('FAILED')||s.includes('ABORTED');
}
function renderWebUploadStatus(d){
  let b=d?.batch||{},files=d?.files||[],p2=d?.phase2c||{},p3=d?.phase3||{};
  $('uploadStatusCard').classList.remove('hide');
  $('uploadBatchMeta').textContent='Batch '+(b.batch_id??'—')+' · '+(b.batch_label||'Web upload');
  let status=String(b.processing_status||'—'),pct=0;
  if(status==='API_UPLOADING')pct=15;
  else if(status==='INGESTED_PENDING_QA')pct=35;
  else if(status.includes('PHASE2'))pct=55;
  else if(status.includes('PHASE3'))pct=75;
  else if(status.includes('QUICK_CHECK_READY'))pct=100;
  else if(status.includes('QA_HOLD'))pct=100;
  $('uploadProgressBar').style.width=pct+'%';
  $('uploadStatus').innerHTML=[
    uploadStage(status.includes('READY')?'✅':'⏳','Pipeline',status,status.includes('READY')?'ok':(status.includes('HOLD')||status.includes('FAIL')?'bad':'warn')),
    uploadStage('📄','Files',String(files.length)),
    uploadStage('🧩','Phase 2C',p2.result_status||'Pending',String(p2.result_status||'').includes('READY')?'ok':''),
    uploadStage('⚙️','Phase 3',p3.result_status||'Pending',String(p3.result_status||'').includes('READY')?'ok':''),
    uploadStage('🔎','Quick Check',p3.quick_check_rows==null?'Pending':(fmt(p3.quick_check_ready_rows,0)+' / '+fmt(p3.quick_check_rows,0)+' READY · '+fmt(p3.quick_check_hold_rows,0)+' HOLD'),Number(p3.quick_check_hold_rows||0)>0?'warn':(p3.quick_check_rows!=null?'ok':''))
  ].join('');
  $('uploadServerFiles').innerHTML=files.map(x=>
    '<div class="upload-file"><div><div class="upload-file-name">'+esc(x.original_filename||'')+'</div><div class="upload-file-meta">'+esc(x.source_type||'unclassified')+' · '+fmt(x.source_row_count,0)+' rows'+(x.coverage_start_date||x.coverage_end_date?' · '+esc(x.coverage_start_date||'')+' → '+esc(x.coverage_end_date||''):'')+'</div></div><span class="pill '+(x.error_count?'bad':'ok')+'">'+esc(x.processing_status||'')+'</span></div>'
  ).join('');
  return status;
}


function uploadDateTime(v){
  if(!v)return '—';
  let d=new Date(v);
  return Number.isNaN(d.getTime())?String(v):d.toLocaleString('en-US',{month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit'});
}
function referenceCoverage(x){
  let a=x?.coverage_start,b=x?.coverage_end;
  if(a&&b)return a===b?String(a):String(a)+' → '+String(b);
  if(a||b)return String(a||b);
  if(x?.report_generated_at)return 'Generated '+String(x.report_generated_at).slice(0,10);
  if(x?.filename_date_candidate)return 'Report date '+String(x.filename_date_candidate);
  return 'Coverage date unavailable';
}
function renderLatestReferenceUpload(x){
  if(!x?.available){
    return '<div class="latest-ref missing"><div class="label">'+esc(x?.label||'REPORT')+'</div><div class="uploaded">No valid upload</div><div class="coverage">No successful non-duplicate report is currently available.</div></div>';
  }
  return '<div class="latest-ref">'+
    '<div class="label">'+esc(x.label||x.source_type||'REPORT')+'</div>'+
    '<div class="uploaded">'+esc(uploadDateTime(x.uploaded_at))+'</div>'+
    '<div class="coverage"><b>Coverage:</b> '+esc(referenceCoverage(x))+'<br><b>Rows:</b> '+fmt(x.rows,0)+'</div>'+
    '<div class="filename">'+esc(x.filename||'')+'</div>'+
  '</div>';
}
async function loadLatestReferenceUploads(){
  $('latestRefMsg').textContent='Checking latest OH / Live-Fresh / Frozen reports…';
  try{
    let d=await api('/v1/web-upload/latest-reference-uploads');
    $('latestRefUploads').innerHTML=(d.sources||[]).map(renderLatestReferenceUpload).join('');
    $('latestRefMsg').textContent='';
  }catch(e){
    $('latestRefMsg').textContent=e.message;
    $('latestRefUploads').innerHTML='';
  }
}

function renderUploadCalendarDay(x){
  let cls=x.status==='UPDATED'?'updated':(x.status==='PARTIAL'?'partial':'missing');
  let label=x.status==='UPDATED'?'UPDATED':(x.status==='PARTIAL'?'PARTIAL':'NEEDS UPLOAD');
  let date=String(x.date||''),md=date.length>=10?date.slice(5).replace('-','/') : date;
  let miss=(x.missing_sources||[]).length?'Need '+(x.missing_sources||[]).join(' + '):'Complete';
  return '<div class="upload-day '+cls+'">'+
    '<div><div class="dow">'+esc(x.weekday||'')+'</div><div class="date">'+esc(md)+'</div><div class="state">'+label+'</div></div>'+
    '<div><div class="srcs"><div class="src '+(x.pos?.updated?'ok':'no')+'">POS '+(x.pos?.updated?'✓':'✕')+'</div><div class="src '+(x.mvt?.updated?'ok':'no')+'">MVT '+(x.mvt?.updated?'✓':'✕')+'</div></div>'+
    '<div class="need">'+esc(miss)+'</div></div>'+
  '</div>';
}
async function loadWebUploadCalendar(){
  $('uploadCalendarMsg').textContent='Checking daily coverage…';
  try{
    let d=await api('/v1/web-upload/calendar?days=14'),s=d.summary||{};
    $('uploadCalendarRange').textContent=(d.window_start||'')+' → '+(d.completed_through||'');
    $('uploadCalendarSummary').innerHTML=
      '<span class="upload-calendar-chip updated">'+fmt(s.updated_days,0)+' Updated</span>'+
      '<span class="upload-calendar-chip partial">'+fmt(s.partial_days,0)+' Partial</span>'+
      '<span class="upload-calendar-chip missing">'+fmt(s.needs_upload_days,0)+' Need Upload</span>';
    $('uploadCalendar').innerHTML=(d.days||[]).map(renderUploadCalendarDay).join('');
    $('uploadCalendarMsg').textContent='';
  }catch(e){
    $('uploadCalendarMsg').textContent=e.message;
    $('uploadCalendar').innerHTML='';
  }
}

function renderWebUploadRecentBatch(b){
  let files=b.files||[];
  let qc=b.quick_check_rows==null?'Pending':(fmt(b.quick_check_ready_rows,0)+' / '+fmt(b.quick_check_rows,0)+' READY · '+fmt(b.quick_check_hold_rows,0)+' HOLD');
  return '<div class="card">'+
    '<div class="row" style="justify-content:space-between"><div><div class="name">Batch '+esc(b.batch_id??'—')+'</div><div class="meta">'+esc(b.batch_label||'')+'</div>'+
      '<div class="meta" style="margin-top:3px"><b>Uploaded:</b> '+esc(uploadDateTime(b.upload_started_at))+
      (b.completed_at?' · <b>Completed:</b> '+esc(uploadDateTime(b.completed_at)):'')+
      '</div></div>'+pill(b.processing_status||'UNKNOWN')+'</div>'+
    '<div id="uploadRecentStages" style="margin-top:6px">'+
      uploadStage('📄','Files',String(b.file_count??files.length))+
      uploadStage('🧩','Phase 2C',b.phase2c_status||'Pending',String(b.phase2c_status||'').includes('READY')?'ok':'')+
      uploadStage('⚙️','Phase 3',b.phase3_status||'Pending',String(b.phase3_status||'').includes('READY')?'ok':'')+
      uploadStage('🔎','Quick Check',qc,Number(b.quick_check_hold_rows||0)>0?'warn':(b.quick_check_rows!=null?'ok':''))+
    '</div>'+
    '<div style="margin-top:7px">'+files.map(x=>
      '<div class="upload-file"><div><div class="upload-file-name">'+esc(x.original_filename||'')+'</div>'+
      '<div class="upload-file-meta">'+esc(x.source_type||'unclassified')+' · '+fmt(x.source_row_count,0)+' rows'+
      (x.upload_timestamp?' · Uploaded '+esc(uploadDateTime(x.upload_timestamp)):'')+
      (x.coverage_start_date||x.coverage_end_date?' · Coverage '+esc(x.coverage_start_date||'')+(x.coverage_end_date&&x.coverage_end_date!==x.coverage_start_date?' → '+esc(x.coverage_end_date):''):'')+
      (x.duplicate_of_file_id?' · duplicate of file '+esc(x.duplicate_of_file_id):'')+
      '</div></div><span class="pill '+(Number(x.error_count||0)>0?'bad':'ok')+'">'+esc(x.processing_status||'UNKNOWN')+'</span></div>'
    ).join('')+'</div>'+
    ((String(b.processing_status||'').toUpperCase()==='QA_HOLD'&&!b.phase2c_status&&!b.phase3_status)
      ? '<button class="delete-qa-batch" data-delete-batch="'+esc(b.batch_id)+'" type="button">Delete QA HOLD Batch</button>'
      : '')+
  '</div>';
}

async function deleteQAHoldBatch(batchId){
  let id=Number(batchId);
  if(!Number.isInteger(id)||id<1)return;
  if(!confirm('Delete QA HOLD Batch '+id+' permanently?\n\nThis is allowed only when Phase 2C / Phase 3 never started. READY batches cannot be deleted.'))return;
  try{
    let d=await api('/v1/web-upload/batches/'+id+'/delete',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({confirm:'DELETE_QA_HOLD_BATCH:'+id})
    });
    if(webUploadPoll){clearTimeout(webUploadPoll);webUploadPoll=null}
    webUploadSession=null;
    $('uploadStatusCard').classList.add('hide');
    $('uploadMsg').textContent='Batch '+id+' deleted · '+fmt(d.file_count,0)+' file(s) removed.';
    await loadWebUploadRecent();
    await loadWebUploadCalendar();
    await loadLatestReferenceUploads();
  }catch(e){
    $('uploadMsg').textContent='Delete blocked: '+e.message;
  }
}

async function loadWebUploadRecent(){
  $('uploadRecentMsg').textContent='Loading recent upload status…';
  try{
    let d=await api('/v1/web-upload/recent?limit=8');
    $('uploadRecentMsg').textContent=(d.count||0)+' recent batch(es)';
    $('uploadRecent').innerHTML=(d.batches||[]).map(renderWebUploadRecentBatch).join('')||'<div class="card small">No uploads yet.</div>';
    document.querySelectorAll('#uploadRecent [data-delete-batch]').forEach(
      b=>b.onclick=()=>deleteQAHoldBatch(b.dataset.deleteBatch)
    );
  }catch(e){$('uploadRecentMsg').textContent=e.message}
}
async function pollWebUpload(session){
  if(!session)return;
  webUploadSession=session;
  if(webUploadPoll){clearTimeout(webUploadPoll);webUploadPoll=null}
  try{
    let d=await api('/v1/web-upload/batches/'+encodeURIComponent(session));
    let status=renderWebUploadStatus(d);
    $('uploadMsg').textContent=terminalUploadStatus(status)
      ? (status.includes('READY')?'Batch complete. Quick Check has been refreshed.':'Batch finished with '+status+'. Review QA status before relying on held rows.')
      : 'Server is processing this batch…';
    await loadWebUploadRecent();
    if(terminalUploadStatus(status)){await loadLatestReferenceUploads();await loadWebUploadCalendar();}
    if(!terminalUploadStatus(status))webUploadPoll=setTimeout(()=>pollWebUpload(session),3000);
  }catch(e){$('uploadMsg').textContent=e.message}
}
async function loadWebUploadActive(){
  if(webUploadSession){pollWebUpload(webUploadSession);return}
  try{
    let d=await api('/v1/web-upload/active'),a=d.active_batch;
    if(a?.batch_key){webUploadSession=a.batch_key;pollWebUpload(a.batch_key)}
  }catch(e){$('uploadMsg').textContent=e.message}
}
async function startWebUpload(){
  if(!webUploadFiles.length){$('uploadMsg').textContent='Choose at least one raw file.';return}
  $('uploadStart').disabled=true;$('uploadClear').disabled=true;$('uploadMsg').textContent='Creating upload batch…';
  let committed=false;
  try{
    let create=await api('/v1/web-upload/batches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label:'Web raw upload '+new Date().toLocaleString()})});
    webUploadSession=create.session_id;
    $('uploadStatusCard').classList.remove('hide');
    for(let i=0;i<webUploadFiles.length;i++){
      let f=webUploadFiles[i];
      $('uploadMsg').textContent='Uploading '+(i+1)+'/'+webUploadFiles.length+' · '+f.name;
      $('uploadProgressBar').style.width=Math.round(((i+.3)/webUploadFiles.length)*30)+'%';
      let fd=new FormData();fd.append('file',f,f.name);
      await api('/v1/web-upload/batches/'+encodeURIComponent(webUploadSession)+'/files',{method:'POST',body:fd});
      let current=await api('/v1/web-upload/batches/'+encodeURIComponent(webUploadSession));
      renderWebUploadStatus(current);
    }
    $('uploadMsg').textContent='Files uploaded. Committing batch…';
    await api('/v1/web-upload/batches/'+encodeURIComponent(webUploadSession)+'/commit',{method:'POST'});
    committed=true;
    setWebUploadFiles([]);$('uploadFiles').value='';
    await loadWebUploadRecent();
    await pollWebUpload(webUploadSession);
  }catch(e){
    $('uploadMsg').textContent=e.message;
    if(webUploadSession&&!committed){
      try{await api('/v1/web-upload/batches/'+encodeURIComponent(webUploadSession)+'/abort',{method:'POST'})}catch{}
    }
    await loadWebUploadRecent();
  }finally{
    $('uploadStart').disabled=false;$('uploadClear').disabled=false;
  }
}
$('uploadDrop').onclick=()=>$('uploadFiles').click();
$('uploadFiles').onchange=e=>setWebUploadFiles(e.target.files);
$('uploadClear').onclick=()=>{setWebUploadFiles([]);$('uploadFiles').value=''};
$('uploadStart').onclick=startWebUpload;
$('uploadRefresh').onclick=()=>{loadWebUploadActive();loadLatestReferenceUploads();loadWebUploadCalendar();loadWebUploadRecent()};
['dragenter','dragover'].forEach(ev=>$('uploadDrop').addEventListener(ev,e=>{e.preventDefault();$('uploadDrop').classList.add('drag')}));
['dragleave','drop'].forEach(ev=>$('uploadDrop').addEventListener(ev,e=>{e.preventDefault();$('uploadDrop').classList.remove('drag')}));
$('uploadDrop').addEventListener('drop',e=>setWebUploadFiles(e.dataTransfer.files));

async function csearch(){
  let q=$('cq').value.trim();
  if(!q){$('cmsg').textContent='Enter an item, Family Article, Article, or UPC.';return}
  $('cmsg').textContent='Searching…';$('cres').innerHTML='';
  try{
    let d=await api('/v1/app/v2/search?q='+encodeURIComponent(q)+'&limit=30');
    $('cmsg').textContent=d.count+' result(s) · Family Article first · sorted by 28D Qty';
    $('cres').innerHTML=(d.results||[]).map((r,i)=>{
      let isFamily=r.result_type==='FAMILY',isUpc=r.result_type==='UPC';
      let numberHtml=isUpc
        ? '<div class="result-upc">UPC '+esc(r.number||'—')+'</div>'
        : '<div class="result-number">'+esc(r.number||'—')+'</div>';
      return '<div class="card result '+(isFamily?'family-result':'')+'" data-i="'+i+'">'
        +(isFamily?'<div class="family-badge">★ FAMILY ARTICLE</div>':'')
        +'<div class="row" style="justify-content:space-between"><div class="name">'+esc(r.name)+'</div>'+pill(r.readiness)+'</div>'
        +numberHtml
        +'<div class="result-type">'+esc(r.result_type)+' · '+esc(r.category||'—')+'</div>'
        
        +'<div class="meta">28D Qty '+qv(r.qty_28d,r.qty_28d_uom)+'</div>'
        +'</div>';
    }).join('')||'<div class="card small">No match found.</div>';
    document.querySelectorAll('#cres .result').forEach(e=>e.onclick=()=>{
      let r=d.results[+e.dataset.i];
      r.result_type==='FAMILY'?family(r.family_id||r.number):upc(r.number,'core');
    });
  }catch(e){$('cmsg').textContent=e.message}
}
$('cs').onclick=csearch;
$('cc').onclick=()=>{$('cq').value='';$('cres').innerHTML='';$('cmsg').textContent='';$('cq').focus()};
$('cq').onkeydown=e=>{if(e.key==='Enter')csearch()};


async function family(k){try{
  let d=await api('/v1/app/v2/family/'+encodeURIComponent(k)),o=d.current_effective_oh||{},z=d.observed_delivery||{},r=d.last_receipt||{};
  $('ft').textContent=d.family_article_name;
  $('fs').textContent='Family '+(d.family_article_number||'—')+' · '+(d.category||'—');
  let articleText=(d.receiving_ordering_articles||[]).map(a=>String(a.article_number||'')+(a.article_description?' · '+String(a.article_description):'')).join(' | ')||'—';
  let ohText=o.quantity==null?'No OH':qv(o.quantity,o.uom);
  let ohReason=o.quantity==null?(o.reason||o.status||'OH unavailable'):(o.source||o.status||'READY');
  $('fsummary').innerHTML=
    ms('Identity','blue',[
      mr('Family Article',d.family_article_number||'—'),
      mr('Category',d.category||'—'),
      mr('Receiving / Ordering',articleText)
    ])+
    ms('Sales','green',[
      mr('7D Sold',qv(d.family_sales_7d?.sold_quantity,d.family_sales_7d?.uom)),
      mr('28D Sold',qv(d.family_sales_28d?.sold_quantity,d.family_sales_28d?.uom))
    ])+
    ms('Inventory','amber',[
      mr('Effective OH',ohText,ohReason),
      mr('OH Status',o.status||'—'),
      mr('OH Source',o.source||'—'),
      mr('OH Anchor',o.anchor_date||o.submitted_at||'—')
    ])+
    ms('Delivery & Receipt','purple',[
      mr('Next Expected Delivery',d.next_expected_delivery_date||'Uncertain'),
      mr('Observed Days',(z.observed_delivery_days||[]).map(x=>x.weekday).join(', ')||'—'),
      mr('Frequency',z.frequency||'—'),
      mr('Last Receipt',r.date||'—'),
      mr('Receipt Qty',qv(r.quantity,r.uom)),
      mr('Receipt Cost',priceText(r.cost,r.cost_uom))
    ]);
  $('fu').innerHTML=(d.related_upcs||[]).map((x,i)=>
    '<div class="related-card" data-i="'+i+'">'+
      '<div class="row" style="justify-content:space-between"><div><div class="name">'+esc(x.name)+'</div><div class="related-upc">UPC '+esc(x.upc)+'</div></div>'+pill(x.readiness)+'</div>'+
      mr('Price',priceText(x.current_price,x.selling_uom)+' · '+(x.current_price_type||'—'))+
      mr('7D Qty',qv(x.qty_7d,x.selling_uom))+
      mr('28D Qty',qv(x.qty_28d,x.selling_uom))+
    '</div>'
  ).join('')||'<div class="small">No related UPCs.</div>';
  document.querySelectorAll('#fu [data-i]').forEach(e=>e.onclick=()=>upc(d.related_upcs[+e.dataset.i].upc,'family'));
  go('family')
}catch(e){alert(e.message)}}


async function upc(u,b='core'){try{
  let [d,p,o,q]=await Promise.all([
    api('/v1/app/v2/upc/'+encodeURIComponent(u)),
    api('/v1/app/v2/upc/'+encodeURIComponent(u)+'/price?trend_supported_days=28'),
    api('/v1/app/v2/upc/'+encodeURIComponent(u)+'/ordering'),
    api('/v1/app/quick-check/'+encodeURIComponent(u))
  ]);
  cupc=d.upc;uback=b;
  let c0=p.current||{},s=p.sales||{},uom=d.qty_uom||d.selling_uom||p.qty_uom||'UOM UNKNOWN',tc=trendContext(p.price_vs_sales_trend?.rows||[],c0,s['7d']);
  let vel=(nv(s['7d']?.supported_day_count)>0&&nv(s['7d']?.sold_quantity)!==null)?nv(s['7d'].sold_quantity)/nv(s['7d'].supported_day_count):nv(d.upc_velocity_7d);
  let item=q.item||{},cat=d.category||item.product_class||'ITEM',priceType=c0.price_type||d.current_price_type||'—';
  $('qcHero').innerHTML=
    '<div class="qc-photo">'+seafoodEmoji(d.upc_name,cat)+'</div>'+
    '<div><div class="qc-name">'+esc(d.upc_name||d.upc)+'</div>'+
    '<div class="qc-meta">Family: '+esc(d.family_article_name||d.family_article_number||'—')+' &nbsp; Article: '+esc(item.article_number||'—')+'<br>UPC: '+esc(d.upc)+'</div>'+
    '<div class="qc-badges"><span class="qc-badge qc-fresh">'+(String(cat).toUpperCase()==='FRESH'?'🌿 ':'')+esc(cat)+'</span><span class="qc-badge qc-reg">🏷 '+esc(priceType)+'</span></div></div>'+
    '<div class="qc-status">'+pill(d.readiness)+'</div>';

  $('qcMetrics').innerHTML=[
    qcMetric('💲 Price',priceText(c0.price,uom),trendNote(tc.price[0],tc.price[1],'money',uom)),
    qcMetric('🏷 Cost',priceText(c0.cost,c0.cost_uom||uom),trendNote(tc.cost[0],tc.cost[1],'money',uom)),
    qcMetric('📊 GP%',c0.gp_pct==null?'—':fmt(Number(c0.gp_pct)*100,1)+'%',trendNote(tc.gpPct[0],tc.gpPct[1],'pct'),'green'),
    qcMetric('📈 GP$/Day',c0.gp_per_day_7d==null?'—':money(c0.gp_per_day_7d)+'/day',trendNote(tc.gpDay[0],tc.gpDay[1],'moneyday')),
    qcMetric('💵 7D Qty',qv(s['7d']?.sold_quantity,uom),trendNote(tc.qty[0],tc.qty[1],'qty',uom)),
    qcMetric('📉 Velocity',vel==null?'—':fmt(vel,2)+' '+esc(uom)+'/day',trendNote(tc.velocity[0],tc.velocity[1],'velocity',uom)),
    qcMetric('◉ DOS',c0.dos==null?'—':fmt(c0.dos,1)+' days'),
    qcMetric('▣ DOH',c0.doh==null?'—':fmt(c0.doh,1)+' days')
  ].join('');

  let pv=priceVelocityBuckets(p.price_vs_sales_trend?.rows||[]).slice(0,4),sweet=p.references?.sweet_spot;
  $('qcPriceIntel').innerHTML=
    '<div><div class="qc-intel-title">💹 Price vs Velocity</div>'+
      (pv.length?'<div class="scroll"><table><thead><tr><th>Price</th><th>Velocity</th><th>GP$/day</th></tr></thead><tbody>'+
        pv.map(x=>'<tr><td>'+esc(priceText(x.price,uom))+'</td><td>'+fmt(x.velocity,2)+' '+esc(uom)+'/day</td><td>'+(x.gpDay==null?'—':money(x.gpDay)+'/day')+'</td></tr>').join('')+
      '</tbody></table></div>':'<div class="small">No validated price/velocity history.</div>')+
    '</div><div class="qc-sweet"><div class="qc-intel-title">🎯 Sweet Spot</div><div class="price">'+(sweet==null?'—':esc(priceText(sweet,uom)))+'</div><div class="small">Highest historical avg GP$/day.</div><button id="qcPriceOpen" class="qc-order-open">Full price analysis ›</button></div>';

  let sys=q.system_oh||{},ts=q.active_true_stock||{},actual=q.actual_oh||{},eff=q.effective_oh||{},invUom=eff.uom||sys.uom||uom;
  let trueQty=(actual.quantity??ts.true_stock_quantity),sysQty=sys.quantity,diff=null;
  if(nv(eff.quantity)!==null&&nv(sysQty)!==null)diff=nv(eff.quantity)-nv(sysQty);
  else if(nv(trueQty)!==null&&nv(sysQty)!==null)diff=nv(trueQty)-nv(sysQty);
  $('qcInvUom').textContent=invUom||'—';$('qcTrueUom').textContent=q.true_stock_input?.required_uom||invUom||'—';
  $('qcInventory').innerHTML=[
    qcInv('System OH',nv(sysQty)==null?'—':fmt(sysQty,1)),
    qcInv('True Stock',nv(trueQty)==null?'—':fmt(trueQty,1),'blue'),
    qcInv('Effective OH',nv(eff.quantity)==null?'—':fmt(eff.quantity,1)),
    qcInv('Difference',diff==null?'—':(diff>0?'+':'')+fmt(diff,1),diff<0?'red':'')
  ].join('');
  $('qcTrueStock').value=nv(trueQty)==null?'':String(trueQty);
  $('qcTrueMsg').textContent='';

  let fi=o.forecast||{},inp=o.inputs||{},cov=coverageDays(inp.expected_delivery_date,o.next_next_delivery_date),ou=fi.suggested_order_uom||uom;
  $('qcOrdering').innerHTML=[
    qcOrderCell('📅 Next Order',esc(shortDate(inp.ordering_date))),
    qcOrderCell('🚚 Delivery',esc(shortDate(inp.expected_delivery_date))),
    qcOrderCell('📋 Suggested Qty',fi.suggested_order_qty==null?'—':qv(fi.suggested_order_qty,ou)),
    qcOrderCell('🗓 Coverage',cov==null?'—':cov+' days')
  ].join('');

  quickChart(p.price_vs_sales_trend?.rows||[]);

  let related=q.related_upcs||[];
  $('qcFamilyRows').innerHTML=related.slice(0,4).map(r=>{
    let rel=String(r.ean_upc)===String(d.upc)?'This Item':'Same Family';
    let cls=rel==='This Item'?'':' same';
    return '<tr><td>'+esc(r.selling_description||r.ean_upc)+'</td><td>'+esc(r.article_number||'—')+'</td><td>'+esc(r.ean_upc||'—')+'</td><td><span class="qc-rel'+cls+'">'+rel+'</span></td></tr>';
  }).join('')||'<tr><td colspan="4">No related UPCs.</td></tr>';

  let highs=(q.highlights||[]);
  $('qcHighlightCount').textContent=highs.length+' item'+(highs.length===1?'':'s');
  $('qcHighlights').innerHTML=highs.map(h=>'<div class="qc-alert"><div class="qc-alert-ico">'+(h.severity==='HIGH'?'⚠️':'🏷️')+'</div><div>'+esc(h.text||h.code)+'</div><div class="qc-chevron">›</div></div>').join('');
  $('qcHighlightsCard').classList.toggle('hide',highs.length===0);

  $('qcPriceOpen').onclick=()=>price(d.upc);
  $('qcOrderOpen').onclick=()=>corder(d.upc);
  $('qcFamilyView').onclick=()=>family(d.family_article_number);
  $('qcTrueUpdate').onclick=()=>submitQcTrueStock(d.upc,q.true_stock_input?.required_uom||invUom||uom);
  $('uf').onclick=()=>family(d.family_article_number);$('upr').onclick=()=>price(d.upc);$('uo').onclick=()=>corder(d.upc);
  $('ut').textContent=d.upc_name;$('us').textContent='UPC '+d.upc;
  go('upc')
}catch(e){alert(e.message)}}
$('ub').onclick=()=>history.back();


async function price(u){try{
  let d=await api('/v1/app/v2/upc/'+encodeURIComponent(u)+'/price?trend_supported_days=28'),c0=d.current||{},r=d.references||{},s=d.sales||{},uom=d.qty_uom||d.selling_uom||'UOM UNKNOWN';
  let rows=d.price_vs_sales_trend?.rows||[],tc=trendContext(rows,c0,s['7d']);
  $('pt').textContent=d.name;
  $('ps').textContent='UPC '+d.upc+' · '+(d.category||'—');
  let vel=(nv(s['7d']?.supported_day_count)>0&&nv(s['7d']?.sold_quantity)!==null)?nv(s['7d'].sold_quantity)/nv(s['7d'].supported_day_count):nv(c0.velocity_7d);
  $('pc').innerHTML=
    ms('Key Metrics · 7D','pink',[
      mrh('Current Price',priceText(c0.price,uom)+' · '+(c0.price_type||'—'),trendNote(tc.price[0],tc.price[1],'money',uom)),
      mrh('Cost',priceText(c0.cost,c0.cost_uom||uom),trendNote(tc.cost[0],tc.cost[1],'money',uom)),
      mrh('GP%',c0.gp_pct==null?'—':fmt(Number(c0.gp_pct)*100,1)+' %',trendNote(tc.gpPct[0],tc.gpPct[1],'pct')),
      mrh('GP$/Day',c0.gp_per_day_7d==null?'—':money(c0.gp_per_day_7d)+' / day',trendNote(tc.gpDay[0],tc.gpDay[1],'moneyday')),
      mrh('7D Qty',qv(s['7d']?.sold_quantity,uom)+' / 7D',trendNote(tc.qty[0],tc.qty[1],'qty',uom)),
      mrh('Velocity',vel==null?'—':fmt(vel,2)+' '+uom+' / day',trendNote(tc.velocity[0],tc.velocity[1],'velocity',uom)),
      mr('DOS',c0.dos==null?'—':fmt(c0.dos,1)+' days'),
      mr('DOH',c0.doh==null?'—':fmt(c0.doh,1)+' days')
    ])+
    ms('Price References','purple',[
      mr('Sweet Spot',priceText(r.sweet_spot,uom)),
      mr('WGPM',priceText(r.wgpm,uom)),
      mr('Company A',priceText(r.company_a,uom)),
      mr('Company B',priceText(r.company_b,uom)),
      mr('Company C',priceText(r.company_c,uom))
    ]);

  let pv=priceVelocityBuckets(rows).slice(0,8);
  $('pvh').innerHTML=pv.length
    ? '<div class="scroll"><table class="price-history"><thead><tr><th>Last</th><th>Price</th><th>Velocity</th><th>GP$/day</th></tr></thead><tbody>'+
      pv.map(x=>'<tr><td>'+esc(x.last)+'</td><td>'+esc(priceText(x.price,uom))+'</td><td>'+fmt(x.velocity,2)+' '+esc(uom)+'/day</td><td>'+(x.gpDay==null?'—':money(x.gpDay)+'/day')+'</td></tr>').join('')+
      '</tbody></table></div>'
    : '<div class="small">No validated price/velocity history.</div>';
  $('psweet').innerHTML=r.sweet_spot==null
    ? '<div class="small">Not enough validated price/cost history to calculate a sweet spot.</div>'
    : '<div class="sweet-hero">'+esc(priceText(r.sweet_spot,uom))+'</div><div class="small">Canonical Sweet Spot = historical price with the highest average GP$/day. It is an analytical reference, not an automatic price change.</div>';

  chart(rows);
  $('p14').innerHTML=(d.sales_history_14d?.rows||[]).slice().reverse().map(x=>
    '<div class="promo"><div class="row" style="justify-content:space-between"><b>'+esc(dayName(x.date))+' · '+esc(x.date)+'</b><b>'+qv(x.sold_quantity,x.qty_uom||uom)+' sold</b></div>'+
    '<div class="meta">Sales '+money(x.sales_amount)+' · Avg price '+esc(priceText(x.avg_sold_price,uom))+' · GP$ '+money(x.gp_dollars)+' · '+((x.price_types||[]).map(p=>esc(p.price_type)).join(', ')||'No item sale')+'</div></div>'
  ).join('')||'<div class="small">No 14D sales history.</div>';
  $('ph').innerHTML=(d.historical_promotions||[]).map(p=>
    '<div class="promo"><b>'+esc(p.promotion_type)+' Promotion · '+esc(promoRange(p))+'</b>'+
    '<div class="meta">'+esc(p.start_date)+' → '+esc(p.end_date)+' · '+esc(priceText(p.sale_price,uom))+'</div>'+
    '<div class="meta">'+qv(p.sale_quantity,uom)+' sold · '+qv(p.sale_velocity_per_supported_day,uom)+'/day · coverage '+fmt(p.supported_sales_day_count,0)+'/'+fmt(p.calendar_duration_days,0)+'</div></div>'
  ).join('')||'<div class="small">No historical SALE periods.</div>';
  go('price')
}catch(e){alert(e.message)}}


async function submitQcTrueStock(upc,uom){
  let raw=$('qcTrueStock').value.trim();if(raw===''){ $('qcTrueMsg').textContent='Enter True Stock.';return }
  $('qcTrueMsg').textContent='Updating…';
  try{
    await api('/v1/app/quick-check/'+encodeURIComponent(upc)+'/true-stock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:raw,uom:uom})});
    ohLoaded=false;$('qcTrueMsg').textContent='Saved. Refreshing current OH…';await upc(upc,uback)
  }catch(e){$('qcTrueMsg').textContent=e.message}
}
function quickChart(rows){
  let c=$('qcChart'),ctx=c.getContext('2d'),R=devicePixelRatio||1,w=760,h=235;
  c.width=w*R;c.height=h*R;ctx.setTransform(R,0,0,R,0,0);ctx.clearRect(0,0,w,h);
  let a=(rows||[]).slice(-28),p={l:36,r:40,t:27,b:35};
  if(!a.length){ctx.fillStyle='#234b65';ctx.font='13px system-ui';ctx.fillText('No trend data',18,28);return}
  let gpVals=a.map(z=>nv(z.gp_dollars)).filter(z=>z!==null),prVals=a.map(z=>nv(z.avg_sold_price)).filter(z=>z!==null);
  let gpMin=Math.min(0,...gpVals),gpMax=Math.max(1,...gpVals),prMin=prVals.length?Math.max(0,Math.min(...prVals)*.94):0,prMax=prVals.length?Math.max(prMin+1,Math.max(...prVals)*1.06):1;
  if(gpMax===gpMin)gpMax=gpMin+1;if(prMax===prMin)prMax=prMin+1;
  let pw=w-p.l-p.r,ph=h-p.t-p.b,step=pw/a.length,xx=i=>p.l+step*i+step/2,yg=v=>p.t+ph*(1-(v-gpMin)/(gpMax-gpMin)),yp=v=>p.t+ph*(1-(v-prMin)/(prMax-prMin)),y0=yg(0),bw=Math.max(7,Math.min(17,step*.58));
  ctx.strokeStyle='rgba(44,92,120,.16)';ctx.lineWidth=1;
  for(let i=0;i<5;i++){let y=p.t+ph*i/4;ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke()}
  a.forEach((z,i)=>{let v=nv(z.gp_dollars);if(v===null)return;let x=xx(i),y=yg(v),top=Math.min(y,y0),bh=Math.max(1,Math.abs(y-y0));ctx.fillStyle='#164d9f';ctx.globalAlpha=.88;ctx.fillRect(x-bw/2,top,bw,bh);ctx.globalAlpha=1;ctx.font='800 8px system-ui';ctx.textAlign='center';ctx.fillStyle='#164d9f';ctx.fillText('$'+fmt(v,0),x,v>=0?Math.max(9,y-3):Math.min(h-p.b-2,y+10))});
  let pts=[];a.forEach((z,i)=>{let v=nv(z.avg_sold_price);if(v!==null)pts.push([xx(i),yp(v),v])});
  if(pts.length){ctx.strokeStyle='#f27c1a';ctx.lineWidth=2.4;ctx.beginPath();pts.forEach((q,i)=>i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]));ctx.stroke();pts.forEach(q=>{ctx.fillStyle='#f27c1a';ctx.beginPath();ctx.arc(q[0],q[1],2.7,0,Math.PI*2);ctx.fill();ctx.font='800 8px system-ui';ctx.textAlign='center';ctx.fillText('$'+fmt(q[2],2),q[0],Math.min(h-p.b-2,q[1]+11))})}
  ctx.font='9px system-ui';ctx.textAlign='center';ctx.fillStyle='#355d75';a.forEach((z,i)=>{if(i===0||i===a.length-1||i%7===0)ctx.fillText(String(z.date).slice(5),xx(i),h-9)});
  ctx.textAlign='left';ctx.fillText('GP$',3,p.t);ctx.textAlign='right';ctx.fillText('Price $',w-3,p.t);
}

function chart(rows){
  let c=$('chart'),ctx=c.getContext('2d'),R=devicePixelRatio||1,w=Math.max(920,c.clientWidth),h=285;
  c.width=w*R;c.height=h*R;ctx.setTransform(R,0,0,R,0,0);ctx.clearRect(0,0,w,h);
  let a=(rows||[]).slice(-28),p={l:42,r:48,t:36,b:50};
  if(!a.length){ctx.fillStyle=getComputedStyle(document.body).color;ctx.font='15px system-ui';ctx.fillText('No trend data',20,30);return}
  let gpVals=a.map(z=>nv(z.gp_dollars)).filter(z=>z!==null),priceVals=a.map(z=>nv(z.avg_sold_price)).filter(z=>z!==null);
  let gpMin=Math.min(0,...gpVals),gpMax=Math.max(1,...gpVals),priceMin=priceVals.length?Math.max(0,Math.min(...priceVals)*.94):0,priceMax=priceVals.length?Math.max(priceMin+1,Math.max(...priceVals)*1.06):1;
  if(gpMax===gpMin)gpMax=gpMin+1;if(priceMax===priceMin)priceMax=priceMin+1;
  let pw=w-p.l-p.r,ph=h-p.t-p.b,step=pw/a.length,xx=i=>p.l+step*i+step/2,yg=v=>p.t+ph*(1-(v-gpMin)/(gpMax-gpMin)),yp=v=>p.t+ph*(1-(v-priceMin)/(priceMax-priceMin)),y0=yg(0),bw=Math.max(8,Math.min(20,step*.62));
  let line=getComputedStyle(document.documentElement).getPropertyValue('--line'),gpColor=getComputedStyle(document.documentElement).getPropertyValue('--gpbar'),priceColor=getComputedStyle(document.documentElement).getPropertyValue('--pricecurve'),saleColor=getComputedStyle(document.documentElement).getPropertyValue('--sale'),muted=getComputedStyle(document.documentElement).getPropertyValue('--muted'),textColor=getComputedStyle(document.documentElement).getPropertyValue('--text');
  ctx.strokeStyle=line;ctx.lineWidth=1;
  for(let i=0;i<5;i++){let y=p.t+ph*i/4;ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke()}
  a.forEach((z,i)=>{
    let v=nv(z.gp_dollars),x=xx(i);if(v===null)return;let y=yg(v),top=Math.min(y,y0),bh=Math.max(1,Math.abs(y-y0));
    ctx.fillStyle=gpColor;ctx.globalAlpha=.84;ctx.fillRect(x-bw/2,top,bw,bh);ctx.globalAlpha=1;
    ctx.font='800 9px system-ui';ctx.textAlign='center';ctx.fillStyle=gpColor;ctx.fillText('$'+fmt(v,0),x,v>=0?Math.max(10,y-4):Math.min(h-p.b-3,y+11));
  });
  let pts=[];
  a.forEach((z,i)=>{let v=nv(z.avg_sold_price);if(v!==null)pts.push([xx(i),yp(v),v])});
  if(pts.length){ctx.strokeStyle=priceColor;ctx.lineWidth=2.5;ctx.beginPath();pts.forEach((q,i)=>i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]));ctx.stroke();
    pts.forEach(q=>{ctx.fillStyle=priceColor;ctx.beginPath();ctx.arc(q[0],q[1],3.2,0,Math.PI*2);ctx.fill();ctx.font='800 9px system-ui';ctx.textAlign='center';ctx.fillText('$'+fmt(q[2],2),q[0],Math.min(h-p.b-4,q[1]+13))})
  }
  ctx.font='10px system-ui';ctx.textAlign='center';
  a.forEach((z,i)=>{let x=xx(i);if((z.price_types||[]).some(v=>v.price_type==='SALE')){ctx.fillStyle=saleColor;ctx.fillRect(x-3,h-p.b+4,6,9)}if(i===0||i===a.length-1||i%4===0){ctx.fillStyle=muted;ctx.fillText(String(z.date).slice(5),x,h-11)}});
  ctx.font='10px system-ui';ctx.textAlign='left';ctx.fillStyle=textColor;ctx.fillText('GP$ columns',4,13);ctx.textAlign='right';ctx.fillStyle=priceColor;ctx.fillText('Avg Price curve',w-4,13);
}

async function corder(u){cupc=u;$('cod').value=today();$('cop').value='0';$('cpf').classList.add('hide');try{let d=await api('/v1/app/v2/upc/'+encodeURIComponent(u)+'/ordering');$('cot').textContent=d.family_article_name||d.name;$('cos').textContent='Family '+(d.family_article_number||'—')+' · '+(d.category||'—')+' · from UPC '+(d.source_upc||u);$('cdd').value=d.inputs?.expected_delivery_date||'';corender(d);go('corder')}catch(e){$('coout').innerHTML='<div class="card bad">'+esc(e.message)+'</div>';go('corder')}}$('cop').onchange=()=> $('cpf').classList.toggle('hide',$('cop').value!=='1');$('coa').onclick=async()=>{let q=new URLSearchParams();q.set('ordering_date',$('cod').value);q.set('expected_delivery_date',$('cdd').value);let p=$('cop').value==='1';q.set('promotion_involved',p);if(p){q.set('promotion_start_date',$('cps').value);q.set('promotion_end_date',$('cpe').value);q.set('promotion_price',$('cpp').value)}try{corender(await api('/v1/app/v2/upc/'+encodeURIComponent(cupc)+'/ordering?'+q))}catch(e){$('coout').innerHTML='<div class="card bad">'+esc(e.message)+'</div>'}};
function corender(d){let i=d.inventory||{},f=d.forecast||{},r=d.regular_baseline||{};$('cohist').innerHTML=(d.historical_promotions||[]).slice(0,5).map(p=>'<div class="promo"><b>'+esc(p.promotion_type)+' Promotion · '+esc(promoRange(p))+'</b><div class="meta">'+esc(p.start_date)+' → '+esc(p.end_date)+' · '+money(p.sale_price)+' · '+qv(p.sale_quantity,f.suggested_order_uom)+' sold</div></div>').join('');$('coout').innerHTML='<div class="card order"><div class="grid">'+m('Effective OH',qv(i.raw_effective_oh_qty,f.suggested_order_uom))+m('OH Used',qv(i.ordering_oh_qty,f.suggested_order_uom))+m('Regular Velocity',qv(r.regular_velocity_per_supported_day,f.suggested_order_uom)+'/day')+m('Next Next Delivery',d.next_next_delivery_date||'—')+m('Forecast Usage',qv(f.forecast_usage_until_next_next_delivery,f.suggested_order_uom))+m('Projected OH @ Delivery',qv(f.projected_oh_at_expected_delivery,f.suggested_order_uom))+'</div><div class="small">Suggested Order Qty</div><div class="big">'+fmt(f.suggested_order_qty)+' '+esc(f.suggested_order_uom||'')+'</div>'+(i.negative_oh_treated_as_zero?'<div class="warn">Negative OH treated as 0 for ordering.</div>':'')+'</div>'}

function orderDefaults(){let t=today();$('od').value=t;$('dd').value=nextwd(t,5)}orderDefaults();$('ot').onchange=()=>{$('dd').value=nextwd($('od').value||today(),$('ot').value==='FRESH'?5:2)};$('od').onchange=()=>$('ot').onchange();$('op').onchange=()=> $('opa').classList.toggle('hide',$('op').value!=='1');
$('ois').onclick=async()=>{let q=$('oiq').value.trim();if(!q)return;$('oim').textContent='Searching UPCs…';try{let d=await api('/v1/app/v2/search?q='+encodeURIComponent(q)+'&limit=30'),u=(d.results||[]).filter(r=>r.result_type==='UPC'&&String(r.category||'').toUpperCase()===$('ot').value);$('oim').textContent=u.length+' UPC match(es) · sorted by 28D Qty, then readiness';$('oir').innerHTML=u.slice(0,12).map((z,i)=>'<div class="card result" data-i="'+i+'"><div class="row" style="justify-content:space-between"><div><div class="name">'+esc(z.name)+'</div><div class="meta">UPC '+esc(z.number)+' · Family '+esc(z.family_article_number||'—')+'</div></div>'+pill(z.readiness)+'</div><div class="meta">28D Qty '+qv(z.qty_28d,z.qty_28d_uom)+'</div></div>').join('');document.querySelectorAll('#oir .result').forEach(e=>e.onclick=()=>addPromoUPC(u[+e.dataset.i]))}catch(e){$('oim').textContent=e.message}};
async function addPromoUPC(z){let upc=String(z.number||'');if(!upc||pitems.some(x=>x.upc===upc))return;pitems.push({upc,name:z.name,family_article_number:z.family_article_number,family_name:z.family_name,promotion_price:''});drawPromo();$('oir').innerHTML='';$('oiq').value='';try{let d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc)+'/price?trend_supported_days=7');$('ohist').innerHTML='<div class="card"><div class="section">Historical SALE · '+esc(z.name)+'</div><div class="meta">UPC '+esc(upc)+' · this UPC history only</div>'+((d.historical_promotions||[]).slice(0,6).map((p,i)=>'<div class="promo result" data-i="'+i+'"><b>'+esc(p.promotion_type)+' · '+esc(promoRange(p))+'</b><div class="meta">'+esc(p.start_date)+' → '+esc(p.end_date)+' · '+money(p.sale_price)+'</div><div class="meta">'+qv(p.sale_quantity,d.qty_uom||d.selling_uom)+' sold · '+qv(p.sale_velocity_per_supported_day,d.qty_uom||d.selling_uom)+'/supported day</div></div>').join('')||'<div class="small">No historical SALE periods for this UPC.</div>')+'</div>';document.querySelectorAll('#ohist .promo').forEach(e=>e.onclick=()=>{let p=d.historical_promotions[+e.dataset.i],it=pitems.find(x=>x.upc===upc);if(it&&p.sale_price!=null)it.promotion_price=Number(p.sale_price).toFixed(2);drawPromo();$('oim').textContent='Loaded historical '+promoRange(p)+' SALE price as reference. Enter the upcoming promotion dates.'})}catch(e){$('ohist').innerHTML='<div class="card bad">'+esc(e.message)+'</div>'}}
function drawPromo(){$('oil').innerHTML=pitems.length?'<div class="card"><div class="section">Selected Promotion UPCs</div>'+pitems.map((z,i)=>'<div class="row" style="margin-top:10px"><div class="grow"><b>'+esc(z.name)+'</b><div class="meta">UPC '+esc(z.upc)+' · Family '+esc(z.family_article_number||'—')+'</div></div><input data-p="'+i+'" placeholder="SALE price" value="'+esc(z.promotion_price)+'" style="max-width:132px"><button data-r="'+i+'">Remove</button></div>').join('')+'</div>':'';document.querySelectorAll('[data-p]').forEach(e=>e.oninput=()=>pitems[+e.dataset.p].promotion_price=e.value);document.querySelectorAll('[data-r]').forEach(e=>e.onclick=()=>{pitems.splice(+e.dataset.r,1);drawPromo()})}
$('ogen').onclick=async()=>{let promo=$('op').value==='1',body={order_type:$('ot').value,ordering_date:$('od').value,expected_delivery_date:$('dd').value,promotion_involved:promo,promotion_start_date:promo?$('ops').value:null,promotion_end_date:promo?$('ope').value:null,promotion_items:promo?pitems.map(x=>({upc:x.upc,promotion_price:x.promotion_price})):[]};$('omsg').textContent='Calculating…';try{let d=await api('/v1/app/v2/ordering/suggestions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('omsg').textContent=d.suggestion_count+' suggestion(s) · next-next '+(d.inputs?.next_next_delivery_date||'—');$('ores').innerHTML=(d.suggestions||[]).map(r=>'<div class="card order"><div class="row" style="justify-content:space-between"><div><div class="name">'+esc(r.family_article_name)+'</div><div class="meta">Family '+esc(r.family_article_number)+' · '+esc(r.category)+(r.promotion_involved?' · SALE':'')+'</div></div>'+pill(r.readiness)+'</div><div class="grid" style="margin-top:10px">'+m('DOS',fmt(r.dos,1))+m('Effective OH',qv(r.effective_oh_raw,r.uom))+m('OH Used',qv(r.ordering_oh_used,r.uom))+m('28D Qty',qv(r.qty_28d,r.uom))+m('Forecast',qv(r.forecast_total_usage,r.uom))+m('Projected OH @ Delivery',qv(r.projected_oh_at_delivery,r.uom))+'</div>'+(r.promotion_items?.length?'<div class="promo"><b>Promotion UPC</b><div class="meta">'+r.promotion_items.map(x=>esc(x.upc)+' · '+esc(x.upc_name)+' @ '+money(x.promotion_price)).join('<br>')+'</div></div>':'')+'<div class="small">Suggested Order Qty</div><div class="big">'+fmt(r.suggested_order_qty)+' '+esc(r.suggested_order_uom||'')+'</div></div>').join('')||'<div class="card small">No family meets Active 28 supported-day selling + DOS &lt; 7.</div>'}catch(e){$('omsg').textContent=e.message}};
async function pisearch(){
  let q=$('piq').value.trim();if(!q)return;
  $('pim').textContent='Searching Family Articles…';
  try{
    let d=await api('/v1/app/v2/pi/search?q='+encodeURIComponent(q)+'&limit=30');
    $('pim').textContent=d.count+' Family Article(s) · sorted by 28D Qty, then readiness';
    $('pir').innerHTML=(d.results||[]).map((r,i)=>{
      let sys=r.system_oh||{},eff=r.effective_oh||{};
      let sysText=sys.quantity==null?'No OH · '+esc(sys.reason||sys.status||'Reason unavailable'):qv(sys.quantity,sys.uom);
      let effText=eff.quantity==null?'No OH · '+esc(eff.reason||eff.status||'Reason unavailable'):qv(eff.quantity,eff.uom);
      return '<div class="result" data-i="'+i+'">'+
        '<div class="row" style="justify-content:space-between"><div class="name">'+esc(r.family_article_name)+'</div>'+pill(r.readiness)+'</div>'+
        '<div class="meta">Family Article '+esc(r.family_article_number||r.family_id)+' · '+esc(r.category||'—')+'</div>'+
        mr('28D Qty',qv(r.qty_28d,r.qty_28d_uom))+
        mr('System OH',sysText)+
        mr('Effective OH',effText)+
      '</div>';
    }).join('')||'<div class="small">No Family Article found.</div>';
    document.querySelectorAll('#pir .result').forEach(e=>e.onclick=()=>pid(d.results[+e.dataset.i].family_article_number||d.results[+e.dataset.i].family_id));
  }catch(e){$('pim').textContent=e.message}
}
$('pis').onclick=pisearch;$('pic').onclick=()=>{$('piq').value='';$('pir').innerHTML='';$('pim').textContent='';$('piq').focus()};$('piq').onkeydown=e=>{if(e.key==='Enter')pisearch()};
async function pid(k){try{
  let d=await api('/v1/app/v2/pi/'+encodeURIComponent(k)),s=d.system_oh||{},f=d.effective_oh||{},x=d.current_discrepancy||{},r=d.last_receipt||{},fam=d.family||{};
  pifamily=fam.family_article_number||fam.family_id;
  $('pit').textContent=fam.family_article_name||'Family PI';
  $('pisub').textContent='Family Article '+(fam.family_article_number||fam.family_id)+' · '+(fam.category||'—');
  $('pisum').innerHTML=
    ms('Inventory','amber',[
      mr('Family Article',fam.family_article_number||fam.family_id),
      mr('System OH',s.quantity==null?'No OH':qv(s.quantity,s.uom),s.quantity==null?(s.reason||s.status||'OH unavailable'):(s.source||s.status||'')),
      mr('Effective OH',f.quantity==null?'No OH':qv(f.quantity,f.uom),f.quantity==null?(f.reason||f.status||'OH unavailable'):(f.source||f.status||'')),
      mr('Current Difference',qv(x.signed_difference_true_minus_system,x.uom)),
      mr('Last Receipt',r.posting_date||'—')
    ]);
  $('puom').value=d.required_true_stock_uom||'';
  $('pqty').value='';$('pnote').value='';
  $('pih').innerHTML=(d.true_stock_history||[]).map(h=>
    '<tr><td>'+esc(h.submitted_at||'')+'</td><td>'+qv(h.system_oh_quantity,h.uom)+'</td><td>'+qv(h.true_stock_quantity,h.uom)+'</td><td>'+qv(h.signed_difference_true_minus_system,h.uom)+'</td><td>'+esc(h.status||'')+'</td><td>'+esc(h.count_note||'')+'</td></tr>'
  ).join('');
  go('pid')
}catch(e){alert(e.message)}}
$('papply').onclick=async()=>{let q=$('pqty').value.trim(),u=$('puom').value;if(q===''||!u)return;$('pamsg').textContent='Applying Family True Stock…';try{let d=await api('/v1/app/v2/pi/'+encodeURIComponent(pifamily)+'/true-stock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:q,uom:u,note:$('pnote').value||null})});await pid(pifamily);$('pamsg').className='msg success';$('pamsg').textContent='Applied to Family Article · difference '+qv(d.signed_difference_true_minus_system,u)+' · shortage '+qv(d.shortage_quantity,u)+' · overage '+qv(d.overage_quantity,u)}catch(e){$('pamsg').className='msg bad';$('pamsg').textContent=e.message}};

async function initPerformanceDate(){
  try{
    let d=await api('/v1/app/v2/performance/dates?limit=180'),rows=d.dates||[];
    let options=rows.map(x=>'<option value="'+esc(x.date)+'">'+esc(x.weekday)+' · '+esc(x.date)+'</option>').join('');
    $('perdate').innerHTML=options||'<option value="">No supported dates</option>';
    $('pcdate').innerHTML=options||'<option value="">No supported dates</option>';
  }catch(e){
    $('perdate').innerHTML='<option value="">Date list unavailable</option>';
    $('pcdate').innerHTML='<option value="">Date list unavailable</option>';
    $('permsg').textContent=e.message;
  }
}
async function performance(){
  let rd=$('perdate').value;
  $('permsg').textContent='Generating report…';
  $('persummary').innerHTML='';$('peranalysis').innerHTML='';$('pertop').innerHTML='';
  try{
    let q='/v1/app/v2/performance?category=ALL&limit=100'+(rd?'&report_date='+encodeURIComponent(rd):'');
    let d=await api(q),s=d.summary||{},rec=d.report_date_reconciliation||null;
    if(d.report_date){$('perdate').value=d.report_date;$('pcdate').value=d.report_date}
    $('permsg').textContent=esc(d.report_date_weekday||'')+' '+esc(d.report_date||'')+' · '+fmt(s.upcs_sold_report_date,0)+' UPCs sold';

    $('persummary').innerHTML=
      '<div class="card"><div class="section">'+esc(d.report_date_weekday||'')+' '+esc(d.report_date||'')+'</div><div class="grid">'+
        m('Report Date Sales',money(s.report_date_sales_dollars))+
        m('UPCs Sold',fmt(s.upcs_sold_report_date,0))+
        m('Active UPCs 28D',fmt(s.active_upcs_28d,0))+
        m('7D Sales',money(s.sales_dollars_7d))+
        m('14D Sales',money(s.sales_dollars_14d))+
        m('28D Sales',money(s.sales_dollars_28d))+
        m('Slowing Items',fmt(s.slowing_items,0))+
        m('QA HOLD',fmt(s.qa_hold_upcs,0))+
      '</div></div>'+
      (rec
        ? '<div class="card '+(rec.matches_to_cent?'audit-ok':'audit-warn')+'"><div class="section">Sales Audit</div><div class="grid">'+
            m('Canonical POS',money(rec.canonical_source_sales))+
            m('Mapped UPC Total',money(rec.mapped_report_sales))+
            m('Difference',money(rec.difference))+
            m('Unmapped POS',money(rec.unmapped_source_sales))+
            m('Unmapped UPCs',fmt(rec.unmapped_upc_count,0))+
          '</div><div class="meta">'+esc(rec.canonical_source?.basis||'')+' · '+(rec.matches_to_cent?'MATCH':'REVIEW REQUIRED')+'</div></div>'
        : '');

    let narrative=d.narrative_analysis||{};
    $('peranalysis').innerHTML=
      '<div class="card"><div class="section">Analysis · About 200 Words</div>'+
      '<div class="report-analysis-text">'+esc(narrative.text||'Analysis unavailable.')+'</div>'+
      '<div class="meta" style="margin-top:7px">'+fmt(narrative.word_count,0)+' words</div></div>';

    $('pertop').innerHTML=(d.report_date_top_sellers||[]).slice(0,20).map((x,i)=>
      '<div class="top-seller-compact" data-upc="'+esc(x.upc)+'">'+
        '<div class="rankname"><div class="name">#'+(i+1)+' · '+esc(x.name||'')+'</div><div class="sub">UPC '+esc(x.upc||'—')+' · '+esc(x.category||'')+'</div></div>'+
        '<div class="sv"><div class="k">Sales</div><div class="v">'+money(x.sales_amount)+'</div></div>'+
        '<div class="sv"><div class="k">Qty</div><div class="v">'+qv(x.sold_quantity,x.qty_uom)+'</div></div>'+
        '<div class="sv"><div class="k">Avg Price</div><div class="v">'+money(x.avg_sold_price)+'</div></div>'+
      '</div>'
    ).join('')||'<div class="small">No sales on the selected report date.</div>';
    document.querySelectorAll('#pertop [data-upc]').forEach(e=>e.onclick=()=>price(e.dataset.upc));
  }catch(e){$('permsg').textContent=e.message}
}
async function priceChanges(){
  let rd=$('pcdate').value;
  $('pcmsg').textContent='Generating price change suggestions…';$('pcitems').innerHTML='';
  try{
    let q='/v1/app/v2/performance?category=ALL&limit=100'+(rd?'&report_date='+encodeURIComponent(rd):'');
    let d=await api(q);
    if(d.report_date){$('pcdate').value=d.report_date;$('perdate').value=d.report_date}
    let rows=d.top_urgent_price_suggestions||[];
    $('pcmsg').textContent=esc(d.report_date_weekday||'')+' '+esc(d.report_date||'')+' · '+rows.length+' review item(s)';
    $('pcitems').innerHTML=rows.map((x,i)=>{
      let cls=x.actionable?'review-actionable':(x.review_status==='QA_HOLD'?'review-hold':'review-only');
      let badge=x.actionable?'ACTIONABLE':(x.review_status||'REVIEW ONLY').replaceAll('_',' ');
      let suggestion=x.suggested_price!=null?money(x.suggested_price):'Review Only';
      let gpopp=x.gp_per_day_opportunity!=null?money(x.gp_per_day_opportunity):'Unproven';
      return '<div class="promo report-item clickable '+cls+'" data-upc="'+esc(x.upc)+'">'+
        '<div class="row" style="justify-content:space-between"><div><div class="name">#'+(i+1)+' · '+esc(x.name)+'</div><div class="result-upc">UPC '+esc(x.upc)+'</div><div class="meta">'+esc(x.category)+' · Family '+esc(x.family_article_number||'—')+'</div></div><span class="pill '+(x.actionable?'ok':'warn')+' review-badge">'+esc(badge)+'</span></div>'+
        '<div class="row" style="margin-top:8px"><div><div class="small">Current</div><div class="hero-number">'+money(x.current_price)+'</div></div><div class="price-arrow">→</div><div><div class="small">Suggested</div><div class="hero-number">'+suggestion+'</div></div></div>'+
        '<div class="grid" style="margin-top:8px">'+
          m('GP$/day Opportunity',gpopp)+
          m('7D Qty',qv(x.qty_7d,x.qty_uom))+
          m('28D Qty',qv(x.qty_28d,x.qty_uom))+
          m('Company C Floor',money(x.company_price_c_floor))+
        '</div>'+
        '<div class="meta">Sales evidence through '+esc(x.report_date)+' · '+(x.review_blocker?'Reason: '+esc(x.review_blocker.replaceAll('_',' ')):'Price evidence supports action')+'</div>'+
      '</div>';
    }).join('')||'<div class="card small">No active price change review items.</div>';
    document.querySelectorAll('#pcitems [data-upc]').forEach(e=>e.onclick=()=>price(e.dataset.upc));
  }catch(e){$('pcmsg').textContent=e.message}
}
$('perrun').onclick=performance;
$('pcrun').onclick=priceChanges;
initPerformanceDate();
</script></body></html>"""

def webapp_v2_html() -> str:
    return WEBAPP_V2_HTML
