"""Standalone Data Center. Uses existing guarded upload and QA endpoints."""
DATA_CENTER_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FishFinder · Fish Base</title>
<style>
:root{color-scheme:dark;--ink:#65ff89;--muted:#91bd9b;--line:#245535;--blue:#85ecda;--teal:#85ecda;--red:#ff9090;--good:#65ff89;--warn:#ffd477;--shadow:none}
*{box-sizing:border-box}body{margin:0;background:#020a05;color:var(--ink);font:16px/1.35 "Cascadia Mono",Consolas,"Liberation Mono",monospace;-webkit-font-smoothing:antialiased}
button,input{font:inherit}button,a,summary{touch-action:manipulation}button{cursor:pointer;border:1px solid #245535;background:#041108;border-radius:0;padding:7px 11px;color:var(--ink);font-weight:650;transition:background .15s,border-color .15s,box-shadow .15s}button:hover:not(:disabled){background:#102f19;border-color:#36744a;box-shadow:none}button:disabled{opacity:.5;cursor:not-allowed}button.primary{background:#65ff89;border-color:#65ff89;color:#020a05;box-shadow:none}button.primary:hover:not(:disabled){background:#acffbf;border-color:#acffbf}a{color:var(--blue)}:focus-visible{outline:3px solid #85ecda;outline-offset:3px}
header{min-height:44px;padding:7px max(14px,calc((100vw - 1552px)/2));background:#020a05;border-bottom:1px solid #245535;display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--ink)}header>div{display:flex;align-items:center;gap:10px}header strong{font-size:21px;letter-spacing:0}header small{color:#91bd9b;font-size:14px}header b{font-size:12px;letter-spacing:.9px;font-weight:600}.brand-mark{width:27px;height:27px;display:grid;place-items:center;background:#65ff89;border-radius:0;color:#020a05;font-size:20px;font-weight:850;box-shadow:none}.brand-divider{width:1px;height:18px;background:#245535}
main{max-width:1580px;margin:auto;padding:10px 14px 16px}h1,h2,h3,p{margin:0}h1{font-size:22px;font-weight:750;letter-spacing:0}h2{font-size:19px;font-weight:700;letter-spacing:0}h3{font-size:17px}.muted{color:var(--muted)}.bar{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px}.pagebar{margin-bottom:9px;gap:12px}.pagebar>div:first-child{display:flex;align-items:baseline;gap:13px;flex-wrap:wrap}.pagebar p{display:none}#sync{font-size:14px;color:var(--muted)}.page-actions{display:flex;gap:6px;align-items:center}.page-actions button{padding:6px 10px;white-space:nowrap;font-size:14px}#refresh{display:inline-flex;align-items:center;gap:6px}.icon{width:17px;height:17px;stroke:currentColor;stroke-width:1.7;fill:none;stroke-linecap:round;stroke-linejoin:round;flex:none}#health{margin-left:auto;font-size:14px;display:flex;align-items:center;gap:7px;flex-wrap:wrap}#health>b{font-weight:500;color:var(--muted)}.worker-version{display:none}
.badge{display:inline-flex;align-items:center;gap:5px;border-radius:0;padding:4px 8px;font-size:14px;line-height:1.35;font-weight:700;background:#081b0e;color:#91bd9b}.badge.good{background:#092313;color:var(--good)}.badge.warn{background:#241e08;color:var(--warn)}.badge.bad{background:#2a1014;color:var(--red)}#health .badge:before{content:'';width:6px;height:6px;border-radius:0;background:currentColor}
.fresh{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));margin-bottom:10px;border:1px solid var(--line);border-radius:0;overflow:hidden;background:#041108;box-shadow:none}.tile{min-width:0;padding:8px 10px;border-right:1px solid var(--line);display:flex;align-items:center;gap:6px;flex-wrap:wrap}.tile:last-child{border-right:0}.tile>span{font-size:12px;letter-spacing:.4px;font-weight:700;text-transform:uppercase;color:var(--muted);display:flex;align-items:center;gap:5px}.tile>span:before{content:'';width:5px;height:5px;border-radius:0;background:#91bd9b}.tile[data-tone=good]>span:before{background:#65ff89}.tile[data-tone=warn]>span:before{background:#ffd477}.tile[data-tone=bad]>span:before{background:var(--red)}.tile b{font-size:15px;letter-spacing:0;font-variant-numeric:tabular-nums;white-space:nowrap}.tile small{font-size:12px;color:var(--muted)}
.grid{display:grid;grid-template-columns:minmax(0,2.15fr) minmax(310px,1fr);gap:10px;align-items:start}.panel{min-width:0;background:#041108;border:1px solid var(--line);border-radius:0;padding:11px;margin-bottom:10px;box-shadow:none}.panel>h2{display:flex;align-items:center;gap:7px;margin-bottom:8px}.panel>h2 .icon{color:#91bd9b;width:18px;height:18px}.panel>p{font-size:14px;margin:0 0 7px}.monitor-panel{border-top:2px solid #65ff89;padding-top:9px}.batch-title{display:flex;align-items:center;gap:8px}.batch-title .batch-icon{display:grid;place-items:center;width:29px;height:29px;border-radius:0;background:#081b0e;color:#85ecda}.batch-title h2{font-size:21px}.files{display:flex;gap:3px 12px;flex-wrap:wrap;color:#91bd9b;font-size:14px;margin:3px 0 7px}.files span{min-width:0;overflow-wrap:anywhere}
.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:8px 0}.metric{min-width:0;padding:7px 9px;background:#041108;border-radius:0;overflow-wrap:anywhere}.metric>span{display:block;color:var(--muted);font-size:12px;font-weight:650;letter-spacing:.35px;text-transform:uppercase}.metric>b{display:block;font-size:17px;margin-top:3px;line-height:1.25;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:0}.metric[data-tone=good]>b{color:var(--good)}.metric[data-tone=warn]>b{color:var(--warn)}.metric[data-tone=bad]>b{color:var(--red)}#monitor>.metrics{grid-template-columns:.65fr 1.5fr .9fr .85fr 1fr .75fr;gap:0;border:1px solid var(--line);border-radius:0;overflow:hidden;margin:8px 0}#monitor>.metrics>.metric{border-radius:0;background:#041108}#monitor>.metrics>.metric+ .metric{border-left:1px solid var(--line)}#currentCheckpoint{font-size:15px;line-height:1.4}
.activity{border:1px solid #36744a;border-radius:0;background:#092313;color:#65ff89;padding:7px 9px;margin:7px 0}.activity.warn{border-color:#76632b;background:#241e08;color:#ffd477}.activity.bad{border-color:#87414b;background:#2a1014;color:#ff9090}.activity-head{display:flex;align-items:center;gap:7px;font-size:15px}.activity-head strong{flex:1;font-weight:650}.activity-head small{font-size:12px;white-space:nowrap;opacity:.85}.pulse{width:7px;height:7px;border-radius:0;background:#65ff89;flex:none}.pulse.live{animation:heartbeat 1.8s ease-in-out infinite}.warn .pulse{background:#ffd477;animation:none}.bad .pulse{background:#ff9090;animation:none}.activity-lines{display:flex;flex-wrap:wrap;gap:3px 12px;margin-top:4px;font-size:14px}.activity-note{font-size:14px;margin-top:4px}.activity.terminal{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.activity.terminal .activity-head{flex:1}.activity.terminal .activity-lines{margin:0}.retry{font-size:14px;margin-top:5px;padding-top:5px;border-top:1px solid #245535}.retry strong{font-weight:650}@keyframes heartbeat{50%{box-shadow:none;opacity:.65}}
.notice{border:1px solid var(--line);background:#081b0e;padding:7px 9px;border-radius:0;margin:7px 0;overflow-wrap:anywhere;font-size:14px}.notice.bad{border-color:#87414b;background:#2a1014;color:var(--red)}details{margin-top:7px;border-top:1px solid var(--line);padding-top:7px}summary{cursor:pointer;font-size:14px;font-weight:650;color:#91bd9b}summary:hover{color:var(--blue)}#monitor>.monitor-details{margin-top:8px;padding-top:7px}.monitor-details[open]>summary{margin-bottom:8px;color:var(--ink)}.steps{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}.steps span{font-size:14px;border-radius:0;padding:4px 7px;background:#081b0e}.steps .done{background:#092313;color:var(--good)}.steps .hold{background:#241e08;color:var(--warn)}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#041108;padding:10px;border-radius:0;font-size:14px;max-height:320px;overflow:auto}
.drop{background:#081b0e;border:1px dashed #245535;border-radius:0;padding:9px}.drop>label{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.upload-controls{display:flex;align-items:center;gap:5px 8px;flex-wrap:wrap}.upload-controls input[type=file]{flex:1 1 180px;min-width:0;width:100%;margin:2px 0 5px;font-size:14px;color:var(--muted)}input[type=file]::file-selector-button{padding:6px 8px;margin-right:7px;border:1px solid #245535;border-radius:0;background:#041108;color:var(--ink);font:inherit;font-weight:600;cursor:pointer}.drop button.primary{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;font-size:14px}.drop button.primary .icon{width:15px;height:15px}.drop details{border:0;margin:6px 0 0;padding:0}.drop summary{font-size:14px;font-weight:500}input[type=text]{padding:8px 9px;border:1px solid #245535;border-radius:0;width:100%;margin:6px 0 0;background:#041108}.upload-panel>p:last-child{margin:6px 0 0;font-size:14px}#uploadStatus:empty{display:none}
table{width:100%;border-collapse:collapse;text-align:left;font-variant-numeric:tabular-nums}th{position:sticky;top:0;z-index:1;font-size:12px;letter-spacing:.4px;font-weight:650;text-transform:uppercase;color:var(--muted);background:#081b0e}td,th{padding:7px 8px;border-bottom:1px solid #245535;vertical-align:middle;overflow-wrap:anywhere}td{font-size:14px;line-height:1.45}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#081b0e}.scroll{overflow:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#36744a transparent}#recent{max-height:211px}#coverage{max-height:280px}#monitor details .scroll{max-height:300px}#recent td:nth-child(3){min-width:110px}.recent-files{display:flex;flex-wrap:wrap;gap:2px 9px}.recent-files span{overflow-wrap:anywhere}.status-text{display:inline-flex;border-radius:0;padding:2px 6px;background:#081b0e;font-size:14px;font-weight:550;color:#91bd9b}.status-text[data-tone=good]{color:var(--good);background:#092313}.status-text[data-tone=warn]{color:var(--warn);background:#241e08}.status-text[data-tone=bad]{color:var(--red);background:#2a1014}#recent tr[aria-selected=true]{background:#102f19}#recent tr[aria-selected=true] td:first-child{box-shadow:none}.linkbtn{border:0;background:none;color:#85ecda;padding:1px 3px;font-size:14px;font-weight:750;text-decoration:none}.linkbtn:hover{text-decoration:underline}#coverage td,#coverage th{padding:6px 5px;font-size:14px}#coverage td:first-child{white-space:nowrap;color:#91bd9b}#coverage .coverage-state{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:600}#coverage .coverage-state:before{content:'';width:4px;height:4px;border-radius:0;background:currentColor}.coverage-state[data-tone=good]{color:var(--good)}.coverage-state[data-tone=warn]{color:var(--warn)}.coverage-state[data-tone=bad]{color:var(--red)}.coverage-state[data-tone=neutral]{color:#91bd9b}.empty{padding:12px;color:var(--muted)}footer{font-size:12px;color:#91bd9b;margin-top:2px}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
@media(max-width:1100px){#monitor>.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}#monitor>.metrics>.metric:nth-child(4){border-left:0}#monitor>.metrics>.metric:nth-child(n+4){border-top:1px solid var(--line)}.pagebar{flex-wrap:wrap}#health{margin-left:0}.page-actions{margin-left:auto}.tile small{display:none}header #version{max-width:240px;overflow-wrap:anywhere}}
@media(max-width:800px){.grid{grid-template-columns:1fr}.fresh{grid-template-columns:repeat(3,minmax(0,1fr))}.tile:nth-child(3n){border-right:0}.tile:nth-child(-n+3){border-bottom:1px solid var(--line)}header>div:last-child{display:none}.pagebar #health{margin-left:auto}.page-actions{margin-left:0}#recent{max-height:211px}#coverage{max-height:260px}.tile small{display:inline}}
@media(max-width:520px){main{padding:8px}.panel{padding:9px;margin-bottom:8px}.grid{gap:0}header{padding:7px 10px;gap:8px}header>div{gap:7px}header small{font-size:12px}.brand-divider{display:none}.pagebar>div:first-child{flex:1 1 100%;justify-content:space-between;gap:5px}h1{font-size:21px}#sync{font-size:12px}.pagebar #health{margin-left:0}.page-actions{margin-left:auto}.tile{padding:6px;display:block}.tile b{font-size:14px}.tile small{display:none}.tile>span{font-size:12px;margin-bottom:2px}.metric{padding:6px}.metric>b{font-size:16px}.metric>span{font-size:12px}#currentCheckpoint{font-size:14px}.activity.terminal{display:block}.activity.terminal .activity-lines{margin-top:3px}.activity-head{flex-wrap:wrap}.bar{flex-wrap:wrap}.batch-title h2{font-size:20px}.files{font-size:14px}#recent td,#recent th{padding:6px 5px;font-size:14px}#recent td:nth-child(3){min-width:0}#recent td:nth-child(2){max-width:125px}.recent-files{display:block}.status-text{font-size:12px;padding:2px 4px}.page-actions button,.drop button.primary{min-height:36px}.linkbtn{min-height:30px}summary{padding:2px 0}}

.fresh-warning{grid-column:1/-1;border-top:1px solid #76632b;background:#241e08;color:#ffd477;padding:5px 10px;font-size:14px;display:flex;align-items:center;gap:6px}.fresh-warning:before{content:'!';font-weight:800}.tile[data-tone=warning]>span:before{background:#ffd477}

/* DC-6: reviewable QA, verified milestones and a compact coverage calendar. */
.pipeline-rail{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin:8px 0}.pipeline-step{display:flex;align-items:center;gap:6px;min-width:0;padding:6px 7px;border:1px solid #245535;border-radius:0;background:#041108;color:#91bd9b;font-size:14px;font-weight:600}.pipeline-step i{display:grid;place-items:center;font-style:normal;font-size:12px;width:17px;height:17px;border-radius:0;background:#245535;flex:none}.pipeline-step.done{background:#092313;border-color:#36744a;color:#65ff89}.pipeline-step.done i{background:#102f19}.pipeline-step.current{background:#062726;border-color:#317a70;color:#85ecda}.pipeline-step.current i{background:#062726}.pipeline-step.blocked{background:#2a1014;border-color:#87414b;color:#ff9090}.pipeline-step.blocked i{background:#2a1014}
.stage-meter{height:4px;border-radius:0;background:#102f19;margin-top:7px;overflow:hidden}.stage-meter span{display:block;height:100%;background:#65ff89;border-radius:0;transition:width .3s}.qa-holds{border:1px solid #76632b;border-radius:0;padding:0;margin:8px 0;background:#241e08}.qa-holds>summary{display:flex;align-items:center;gap:7px;padding:7px 9px;color:#ffd477;list-style:none}.qa-holds>summary:before{content:'›';font-size:20px;line-height:1;transition:transform .15s}.qa-holds[open]>summary:before{transform:rotate(90deg)}.qa-holds>summary::-webkit-details-marker{display:none}.qa-holds>summary strong{font-size:14px}.qa-holds>summary small{font-weight:400;margin-left:auto;font-size:14px}.qa-holds>summary .hold-count{font-weight:750}.qa-holds-body{border-top:1px solid #76632b;padding:9px}.qa-reasons{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.qa-reason{padding:7px 8px;background:#041108;border:1px solid #76632b;border-radius:0;min-width:0}.qa-reason b{font-size:20px;color:#ffd477;line-height:1}.qa-reason span{display:block;margin:3px 0 2px;font-size:14px;font-weight:650}.qa-reason small{font-size:14px;color:#91bd9b;display:block}.qa-holds-body>p{font-size:14px;color:#91bd9b;margin:7px 0}.qa-holds table{background:#041108}.qa-holds td{font-size:14px}.qa-holds td:first-child{font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}.qa-holds .scroll{max-height:230px}.issue-tag{display:inline-block;font-size:14px;padding:2px 5px;background:#241e08;color:#ffd477;border-radius:0;margin:2px 3px 2px 0}
.coverage-heading{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:6px;flex-wrap:wrap}.coverage-heading h2{display:flex;align-items:center;gap:6px;margin:0}.coverage-heading h2 .icon{color:#91bd9b}.view-toggle{display:flex;border:1px solid #245535;border-radius:0;padding:2px;gap:2px;background:#081b0e}.view-toggle button{font-size:12px;padding:3px 6px;border:0;background:none;color:#91bd9b;border-radius:0}.view-toggle button[aria-pressed=true]{color:#85ecda;background:#041108;box-shadow:none}.coverage-overview{display:flex;justify-content:space-between;gap:6px;font-size:14px;color:#91bd9b;margin:5px 0 8px}.coverage-overview b{color:#65ff89;font-weight:650}.calendar-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px}.calendar-day{min-width:0;border-radius:0;border:1px solid #36744a;background:#092313;padding:6px 1px;text-align:center;color:#65ff89}.calendar-day small{display:block;font-size:12px;font-weight:500;color:#91bd9b}.calendar-day b{display:block;font-size:14px;font-weight:700;margin:1px 0 4px;white-space:nowrap;letter-spacing:0}.calendar-day .day-sources{display:flex;justify-content:center;gap:5px;font-size:12px;font-weight:650}.day-sources span:before{content:'';display:inline-block;width:4px;height:4px;margin-right:2px;border-radius:0;background:currentColor;vertical-align:middle}.day-sources [data-tone=good]{color:#65ff89}.day-sources [data-tone=bad]{color:#ff9090}.day-sources [data-tone=neutral]{color:#91bd9b}.calendar-day[data-tone=bad]{background:#2a1014;border-color:#87414b;color:#ff9090}.calendar-day[data-tone=neutral]{background:#041108;border-color:#245535;color:#91bd9b}.calendar-day[aria-pressed=true]{outline:2px solid #85ecda;outline-offset:-2px;background:#102f19;color:#85ecda}.calendar-day:hover{border-color:#317a70!important;background:#102f19!important}.calendar-legend{display:flex;gap:9px;flex-wrap:wrap;align-items:center;font-size:12px;color:#91bd9b;margin-top:8px}.calendar-legend span:before{content:'';display:inline-block;width:5px;height:5px;border-radius:0;background:#65ff89;margin-right:4px}.calendar-legend span:nth-child(2):before{background:#ff9090}.calendar-legend span:nth-child(3):before{background:#91bd9b}.coverage-day-detail{border-top:1px solid var(--line);padding-top:7px;margin-top:7px;font-size:14px}.coverage-day-detail strong{font-size:14px}.coverage-day-detail .day-files{display:grid;grid-template-columns:35px minmax(0,1fr);gap:4px 7px;margin-top:6px;color:#91bd9b;overflow-wrap:anywhere}.coverage-day-detail .day-files b{font-size:12px;color:#91bd9b}.coverage-table{max-height:280px}.coverage-table[hidden],.coverage-calendar[hidden]{display:none}#coverage{max-height:none;overflow:visible}.coverage-controls-note{font-size:14px;color:#91bd9b;margin:6px 0 0}.pipeline-step span{overflow-wrap:anywhere}
@media(max-width:1100px){.pipeline-step{font-size:12px;padding:5px;gap:4px}.calendar-grid{gap:3px}.calendar-day b{font-size:14px}.view-toggle button{font-size:12px;padding:3px 5px}}
@media(max-width:520px){.pipeline-step{flex-direction:column;align-items:flex-start;padding:5px 6px;font-size:12px;gap:3px}.pipeline-step i{width:15px;height:15px}.qa-reasons{grid-template-columns:1fr}.qa-reason{display:grid;grid-template-columns:25px 1fr;gap:2px 5px}.qa-reason small{grid-column:2}.qa-reason span{margin:0}.qa-holds>summary{flex-wrap:wrap}.qa-holds>summary small{margin-left:0}.calendar-day{padding:6px 2px;min-height:58px}.coverage-heading h2{font-size:18px}.qa-holds td{font-size:14px}}

/* DC-7: AS/400 Classic Green Screen. Semantic status colors remain distinct. */
::selection{background:#65ff89;color:#020a05}
header{border-bottom:2px solid #36744a}header strong{font-size:21px;color:#65ff89}header b{color:#85ecda}
h1,h2{color:#65ff89}h1{font-size:21px}h2{text-transform:uppercase;font-size:18px;letter-spacing:.3px}
.panel{border-bottom:3px solid #36744a}.panel>h2 .icon,.coverage-heading h2 .icon{color:#65ff89}
button{border-color:#36744a;background:#06160b;color:#85ecda}button:hover:not(:disabled){color:#acffbf}
button:disabled{opacity:.65}input[type=text]{color:#b1ffc2;caret-color:#65ff89}input::placeholder{color:#91bd9b}
button.primary:hover:not(:disabled){color:#020a05}
.view-toggle button[aria-pressed=true]{color:#020a05;background:#65ff89}
.calendar-day[aria-pressed=true]{outline-color:#65ff89;background:#173c22;color:#b1ffc2}
.calendar-day[aria-pressed=true] small{color:#b1ffc2}
.status-text,.badge{border:1px solid currentColor}.badge.good{color:#65ff89}.badge.warn{color:#ffd477}.badge.bad{color:#ff9090}
th{color:#85ecda;border-bottom-color:#36744a}.metric>span{color:#91bd9b}.metric>b{color:#b1ffc2}
#recent tr[aria-selected=true] td:first-child{border-left:3px solid #65ff89}
.pipeline-step i{border:1px solid currentColor;background:transparent!important}
.pipeline-step.current{border-color:#85ecda}.pipeline-step.done{border-color:#36744a}
.pipeline-step.blocked{border-color:#87414b}.activity{border-left:3px solid currentColor}
.qa-holds{border-left:3px solid #ffd477}.qa-holds>summary{color:#ffd477}.qa-holds-body{color:#b1ffc2}
.notice.bad{border-left:3px solid #ff9090}.fresh-warning{color:#ffd477}
footer{border-top:1px solid #245535;padding-top:6px;color:#91bd9b}
@media(max-width:520px){header{flex-wrap:wrap}header>div:first-child{flex-wrap:wrap;gap:5px 8px}header strong{font-size:18px}.brand-mark{width:24px;height:24px}.coverage-heading h2{font-size:17px}.metric>span{font-size:12px}.tile>span{font-size:12px}}

/* DC-8: stable layout and independent, visible loading states. */
.load-status{display:flex;gap:8px 18px;flex-wrap:wrap;margin:0 0 10px;padding:6px 0;border-bottom:1px solid var(--line);font-size:14px;color:var(--muted)}
.load-chip{display:inline-flex;align-items:center;gap:6px}.load-chip b{color:#b1ffc2;font-weight:600}.load-chip i{width:5px;height:5px;background:#91bd9b}.load-chip[data-state=ready] i{background:#65ff89}.load-chip[data-state=error],.load-chip[data-state=saved]{color:#ffd477}.load-chip[data-state=error] i{background:#ffd477}
.panel-empty{display:grid;gap:5px;padding:8px 0;color:var(--muted);font-size:15px}.panel-empty b{color:#ffd477;font-size:17px}
.loading-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:16px 0 12px}.loading-grid span{display:block;font-size:12px;text-transform:uppercase;color:var(--muted)}.placeholder-line{display:block;width:70%;height:12px;background:#143820;margin-top:8px}.loading-note{font-size:14px;color:var(--muted);padding:5px 0}
.evidence-pending{font-size:14px;color:#ffd477;padding:5px 0}.tile{display:grid;grid-template-columns:auto 1fr;gap:2px 7px;padding:8px 10px}.tile b{color:#b1ffc2;font-size:17px}.tile small{grid-column:1/-1;font-size:12px}.tile>span{font-size:12px}
.panel{padding:12px}.metric>b{font-size:19px}#currentCheckpoint{font-size:16px}.files{font-size:15px;line-height:1.45}td{font-size:15px}.activity-head{font-size:16px}.activity-lines{font-size:15px}.pagebar{margin-bottom:5px}#sync{font-size:14px}.upload-controls{align-items:stretch}.upload-controls input[type=file]{flex-basis:100%;margin-bottom:3px}.drop button.primary{min-height:36px;width:100%;justify-content:center;font-size:15px}.drop details{margin-top:8px}.monitor-panel{min-height:170px}.brand-mark{background:#65ff89}#recent{max-height:226px}.calendar-day b{font-size:15px}
@media(max-width:800px){.load-status{gap:7px 12px}.tile b{font-size:16px}.tile small{display:block}.tile{display:block}.tile>span{margin-bottom:2px}.metric>b{font-size:18px}}
@media(max-width:520px){.load-chip{font-size:12px}.loading-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.tile b{font-size:14px}.tile>span{font-size:12px}.tile small{font-size:12px}.panel{padding:9px}}

/* Use the available workstation width and keep long history inside its panel. */
main{max-width:none;padding:8px 12px 10px}header{padding:6px 12px}.panel{margin-bottom:8px}.grid{gap:8px}
.load-status{margin-bottom:7px;padding:4px 0;gap:5px 16px}.fresh{margin-bottom:8px}.tile{padding:6px 9px}
#recent th:first-child,#recent td:first-child{min-width:52px;white-space:nowrap}#recent{max-height:clamp(132px,calc(100dvh - 570px),226px)}footer{font-size:12px;padding-top:5px}
@media(min-width:1500px){
 .grid{grid-template-columns:minmax(540px,1.45fr) minmax(300px,.8fr) minmax(340px,1fr);gap:8px 10px}
 .grid>div:first-child{display:contents}.grid>div:last-child{display:flex;flex-direction:column;gap:8px;grid-column:2;grid-row:1}.monitor-panel{grid-column:1;grid-row:1}.recent-panel{grid-column:3;grid-row:1}
 .panel{margin-bottom:0}.grid #recent{max-height:clamp(270px,calc(100dvh - 215px),650px)}
 #recent td,#recent th{padding:6px;font-size:14px}#recent td:nth-child(3){min-width:85px}.recent-files{font-size:14px}
 .upload-controls input[type=file]{flex-basis:100%;font-size:14px}.drop button.primary{padding:6px 8px;min-height:32px}
 .pipeline-step{padding:5px;font-size:12px}.pipeline-step i{width:15px;height:15px}
 .calendar-day{padding:5px 1px}.calendar-day b{font-size:14px}.calendar-legend{gap:7px;margin-top:6px}
 footer{margin-top:8px}
}
@media(max-height:760px) and (min-width:801px) and (max-width:1499px){.panel{padding:9px}.grid{grid-template-columns:minmax(0,2fr) minmax(315px,1fr)}.metrics{margin:6px 0}.activity{margin:5px 0}.pipeline-rail{margin:6px 0}.calendar-day{padding:4px 1px}.qa-holds{margin:6px 0}#recent{max-height:132px}}
@media(max-width:800px){main{padding:8px}#recent{max-height:230px}}

.tile{display:flex;align-content:center;gap:3px 7px}.tile small{flex-basis:100%;font-size:12px}.tile b{font-size:17px}.tile>span{font-size:12px}.metric>b{font-size:20px}.metric>span{font-size:12px}.activity-head{font-size:16px}.activity-lines{font-size:14px}.files{font-size:15px}
#recent th:first-child,#recent td:first-child{min-width:62px}.load-status{font-size:13px}.page-actions button{font-size:14px;min-height:36px}.pipeline-step{font-size:13px}.badge{font-size:13px}.qa-holds>summary strong{font-size:14px}.qa-holds>summary small{font-size:13px}
@media(min-width:1500px){.grid{grid-template-columns:minmax(560px,1.45fr) minmax(330px,.85fr) minmax(380px,1fr)}.pipeline-step{font-size:12px}.calendar-day b{font-size:15px}.calendar-day small{font-size:12px}.calendar-day .day-sources{font-size:11px}#recent td{font-size:14px;line-height:1.3}#recent th{font-size:12px}.recent-files{font-size:14px}}
@media(max-width:520px){.tile b{font-size:14px}.tile>span,.tile small{font-size:11px}.metric>b{font-size:18px}.files{font-size:14px}.pipeline-step{font-size:12px}.badge{font-size:12px}}

/* Fill the workstation height with useful records, keeping each pane scrollable. */
@media(min-width:1500px) and (min-height:760px){
 body{height:100dvh;display:flex;flex-direction:column}header{flex:none}
 main{width:100%;flex:1;min-height:0;display:flex;flex-direction:column}
 main>.pagebar,main>#globalError,main>.load-status,main>.fresh,main>footer{flex:none}
 main>.grid{flex:1;min-height:0;align-items:stretch}
 .grid>div:last-child{min-height:0;overflow:auto;overscroll-behavior:contain}
 .upload-panel{flex:none}.coverage-panel{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain}
 .monitor-panel,.recent-panel{height:100%;min-height:0;overflow:auto;overscroll-behavior:contain}
 .recent-panel{display:flex;flex-direction:column}.recent-panel>h2{flex:none}
 .grid #recent{flex:1;min-height:0;max-height:none}
 #monitor{height:100%;display:flex;flex-direction:column}#monitor>*{flex:none}
 #monitor>.qa-holds[open]{flex:1;min-height:240px;display:flex;flex-direction:column}
 .qa-holds[open]::details-content{display:contents}
 .qa-holds>summary,.qa-reasons,.qa-holds-body>p{flex:none}
 .qa-holds-body{flex:1;min-height:0;display:flex;flex-direction:column}
 .grid #monitor .qa-holds .scroll{flex:1;min-height:70px;max-height:none}
 .coverage-panel .coverage-table{max-height:none}
 .calendar-day{padding:7px 1px}.calendar-day b{font-size:17px}
}

.page-actions a{border:1px solid #36744a;padding:8px 10px;text-decoration:none;font-size:14px;white-space:nowrap}
.publication-panel{flex:none}.publication-panel h2{font-size:16px}.publish-top{display:flex;align-items:center;justify-content:space-between;gap:8px}.publish-time{font-size:12px;color:var(--muted);margin:4px 0 8px}.publish-dates{display:grid;grid-template-columns:1fr 1fr;gap:7px}.publish-dates span{font-size:12px;color:var(--muted);display:block}.publish-dates b{font-size:17px}.publish-counts{font-size:13px;color:var(--muted);margin-top:7px}.publish-files{font-size:13px;color:#b1ffc2;overflow-wrap:anywhere}.publish-files div{padding:5px 0;border-top:1px solid var(--line)}.publication-panel details{margin-top:7px;padding-top:6px}.publication-panel summary{font-size:13px}.publish-empty{font-size:14px;color:var(--muted)}.coverage-day-detail .day-files{grid-template-columns:58px minmax(0,1fr);gap:7px 9px}.coverage-day-detail .day-files b{white-space:nowrap;overflow-wrap:normal;color:#b1ffc2;font-size:12px}.coverage-day-detail>summary{font-size:13px;line-height:1.5}.coverage-day-detail .day-files span{font-size:13px;line-height:1.5}

/* DC-10: fit the CSS viewing window, including OS/browser display scaling. */
header>div,main>.grid>div{min-width:0}
header{flex-wrap:wrap}
header small{overflow-wrap:anywhere}
#monitor>.metrics{grid-template-columns:repeat(6,minmax(0,1fr))}
.metric>b{overflow-wrap:normal;word-break:normal}
#recent table{width:100%;table-layout:fixed}
#recent th:first-child,#recent td:first-child{min-width:0;width:14%}
#recent th:nth-child(2){width:43%}
#recent th:nth-child(3){width:28%}
#recent th:nth-child(4){width:15%}
#recent th,#recent td{min-width:0;overflow-wrap:anywhere}
#recent td:nth-child(3){min-width:0}
@media(min-width:801px){
 body{height:100dvh;display:flex;flex-direction:column;overflow:hidden;font-size:clamp(12px,.85vw,15px)}
 header{flex:none;padding:5px 10px;gap:4px 10px;min-height:36px}
 header strong{font-size:clamp(16px,1.2vw,21px)}
 header small{font-size:12px}
 main{width:100%;flex:1;min-height:0;display:flex;flex-direction:column;padding:6px 10px}
 main>.pagebar,main>#globalError,main>.load-status,main>.fresh,main>footer{flex:none}
 .pagebar{flex-wrap:wrap;gap:4px 8px}
 .pagebar>div:first-child{gap:8px}
 h1,.batch-title h2{font-size:clamp(17px,1.25vw,21px)}
 h2{font-size:clamp(15px,1vw,18px)}
 .panel{padding:9px}
 .fresh{margin-bottom:6px}.tile{padding:5px 7px}
 .tile b{font-size:clamp(13px,1vw,17px)}
 .tile>span,.tile small,.metric>span{font-size:11px}
 .metric{padding:6px}.metric>b{font-size:clamp(15px,1.1vw,20px)}
 .files,td,.activity-head,.activity-lines,.panel>p{font-size:13px}
 .load-status,#sync,.badge,.steps span,summary,.page-actions button,.page-actions a{font-size:12px}
 .page-actions button,.page-actions a{min-height:30px;padding:5px 8px}
 main>.grid{flex:1;min-height:0;align-items:stretch;overflow:hidden}
 .grid>div:first-child{min-height:0;overflow:auto;overscroll-behavior:contain}
 .grid>div:last-child{min-height:0;overflow:auto;overscroll-behavior:contain}
 .monitor-panel,.recent-panel{min-height:0}
 .recent-panel{display:flex;flex-direction:column}
 .grid #recent{flex:1;min-height:0;max-height:45dvh}
 .coverage-panel{min-height:0}
 #monitor{height:auto}
 #monitor>.qa-holds[open]{min-height:0}
 .calendar-day{padding:4px 1px}.calendar-day b{font-size:14px}
 footer{margin-top:4px;font-size:10px}
}
@media(min-width:1100px){
 .grid{grid-template-columns:minmax(0,1.5fr) minmax(0,.9fr) minmax(0,1.1fr);gap:8px}
 .grid>div:first-child{display:contents}
 .grid>div:last-child{display:flex;flex-direction:column;gap:8px;grid-column:2;grid-row:1}
 .monitor-panel{grid-column:1;grid-row:1;height:100%;overflow:auto}
 .recent-panel{grid-column:3;grid-row:1;height:100%;overflow:hidden}
 .panel{margin-bottom:0}
 .grid #recent{max-height:none;overflow:auto}
 #recent td,#recent th,.recent-files{font-size:12px;padding:5px}
 .publication-panel h2,.coverage-heading h2{font-size:15px}
 .publish-dates b{font-size:15px}
}
@media(min-width:801px) and (max-width:1099px){
 .grid{grid-template-columns:minmax(0,1.4fr) minmax(0,1fr)}
 .fresh{grid-template-columns:repeat(3,minmax(0,1fr))}
 #monitor>.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}
 .activity.terminal{gap:5px}
}
@media(max-width:800px){
 header{height:auto}.pagebar{flex-wrap:wrap}
 #monitor>.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}
}

</style></head><body>
<header><div><span class="brand-mark" aria-hidden="true">F</span><strong>FishFinder · Fish Base</strong><span class="brand-divider" aria-hidden="true"></span><small>Store #1032</small></div><div><b>FULL MYSQL</b><small id="version">Connecting…</small></div></header>
<nav class="dc-functions" aria-label="Fish Base functions">
 <button id="dataFunction" type="button" aria-pressed="true" aria-controls="dataWorkspace">Data &amp; Uploads</button>
 <button id="inventoryFunction" type="button" aria-pressed="false" aria-controls="inventoryWorkspace">Inventory</button>
 <button id="priceFunction" type="button" aria-pressed="false" aria-controls="priceWorkspace">Price Review</button>
 <a id="priceFullWindow" hidden href="https://seafood-stock-watch.bronzedove3.chatgpt.site/price-review" target="_blank" rel="noopener">Open full window ↗</a>
 <a href="/app/stock-records">Stock Records</a>
</nav>
<section id="inventoryWorkspace" hidden aria-label="Inventory">
 <p id="inventoryModuleStatus" role="status">Opening Inventory…</p>
 <iframe id="inventoryFrame" title="Fish Watch Inventory" data-src="https://seafood-stock-watch.bronzedove3.chatgpt.site/inventory" referrerpolicy="strict-origin-when-cross-origin"></iframe>
</section>
<section id="priceWorkspace" hidden aria-label="Price Review">
 <p id="priceModuleStatus" role="status">Opening Price Review…</p>
 <iframe id="priceReviewFrame" title="Fish Watch Price Review" data-src="https://seafood-stock-watch.bronzedove3.chatgpt.site/price-review" referrerpolicy="strict-origin-when-cross-origin"></iframe>
</section>
<main id="dataWorkspace"><div class="bar pagebar"><div><h1>DataCenter</h1><p class="muted">Upload once. Track processing. Verify published data.</p><div id="sync" role="status">Loading live status…</div></div><div id="health" aria-label="Worker health">Checking worker…</div><div class="page-actions"><button id="follow" hidden>Follow current batch</button><button id="refresh"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.2 7a7 7 0 0 1 11.5-2L20 8M4 16l2.3 3A7 7 0 0 0 18 17"/></svg>Refresh</button></div></div>
<div id="globalError" role="alert"></div><div id="loadStatus" class="load-status" role="status" aria-label="Panel update status"></div><div id="freshness" class="fresh"></div>
<div class="grid"><div class="monitor-column"><section class="panel monitor-panel" aria-label="Batch monitor"><div id="monitor" aria-live="polite">Loading current batch…</div></section>
<section class="panel coverage-panel"><div class="coverage-heading"><h2><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-13 5h2m4 0h2"/></svg>14-day completeness</h2><div class="view-toggle" aria-label="Completeness view"><button id="calendarView" aria-pressed="true">Calendar</button><button id="tableView" aria-pressed="false">Table</button></div></div><div id="coverage" class="scroll">Loading…</div></section></div><div class="tools-column"><section class="panel publication-panel" aria-label="Latest verified publish"><h2>Latest verified publish</h2><div id="publication"><span class="publish-empty">Checking published data…</span></div></section>
<section class="panel upload-panel"><h2><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m-4 4 4-4 4 4"/><path d="M4 15v5h16v-5"/></svg>Upload files</h2><div class="drop"><label for="files"><b>Select source files</b></label><div class="upload-controls"><input id="files" type="file" multiple accept=".xlsx,.xls,.xlsm,.csv,.txt,.tsv"><button id="upload" class="primary"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m-4 4 4-4 4 4"/><path d="M4 15v5h16v-5"/></svg>Upload &amp; process</button></div><details><summary>Batch note (optional)</summary><label for="note" hidden>Batch note</label><input id="note" type="text" placeholder="For example: October 9 movement"></details></div><div id="uploadStatus" role="status" class="notice"></div><p class="muted">Existing files are saved. No re-upload needed.</p></section></div><div class="history-column"><section class="panel recent-panel"><h2><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h12M8 12h12M8 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01"/></svg>Recent batches</h2><div id="recent" class="scroll">Loading…</div></section></div></div>
<footer>FishFinder · Fish Base DC-11 · AS/400 Classic Green · Times shown in your local time · Published status requires verification.</footer></main>
<style>
[hidden]{display:none!important}
.dc-functions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:8px 12px;border-bottom:1px solid var(--line);flex:none}
.dc-functions button,.dc-functions a{min-height:36px;padding:7px 12px;font-size:15px}
.dc-functions button[aria-pressed=true]{background:var(--ink);color:#020a05;border-color:var(--ink)}
.dc-functions a{margin-left:auto}
#priceWorkspace,#inventoryWorkspace{width:100%;padding:0 12px;flex:1;min-height:0;display:flex;flex-direction:column}
.price-module-bar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:8px 0;flex:none}
.price-module-bar a{font-size:14px;padding:6px;border:1px solid var(--line)}
#priceModuleStatus{color:var(--muted);font-size:14px;margin-bottom:8px;flex:none}
#priceReviewFrame,#inventoryFrame{display:block;width:100%;height:calc(100dvh - 170px);min-height:320px;flex:1;border:1px solid var(--line);background:#000}
body.price-review-active{height:100dvh;display:flex;flex-direction:column}
body.price-review-active #priceReviewFrame,body.price-review-active #inventoryFrame{height:auto;min-height:0}
@media(max-width:520px){#priceWorkspace,#inventoryWorkspace{padding:0 6px}.dc-functions{padding:6px;gap:5px}.dc-functions button,.dc-functions a{font-size:13px;padding:6px 8px}.price-module-bar h1{font-size:19px}}

/* DC-11: readable operations dashboard with useful content in every column. */
:root{--muted:#a2c7ac;--line:#295a3a}
body{background:#030c07}
header{background:#07180d}
.dc-functions{background:#041108}
.dc-functions button{min-height:40px;font-weight:700}
.dc-functions button[aria-pressed=true]{box-shadow:inset 0 -3px 0 #b1ffc2}
.panel{padding:14px;border-top:2px solid #36744a;border-bottom:2px solid #36744a;background:#06140b}
.panel>h2,.coverage-heading{padding-bottom:10px;border-bottom:1px solid var(--line);margin-bottom:12px}
h2{font-size:17px;letter-spacing:.4px}
.monitor-panel{border-top:3px solid var(--good)}
.publication-panel{border-top:3px solid var(--blue)}
.batch-title h2{font-size:24px}
.files{margin:8px 0 12px;color:#c0e6c9;font-size:14px}
#runBadge{max-width:55%;font-size:12px;text-align:right}
.pipeline-rail{gap:6px;margin:12px 0}
.pipeline-step{padding:8px;font-size:12px}
.activity{padding:12px;background:#0a2615;margin:12px 0}
.activity-head{font-size:15px;align-items:flex-start}
.activity-lines{font-size:12px;color:#b1d9bd;gap:5px 12px;margin-top:8px}
.stage-progress-text{color:#b1ffc2;font-weight:700}
.progress-heading{display:flex;align-items:center;justify-content:space-between;margin-top:8px;font-size:12px;color:var(--muted)}
.progress-heading>b{font-size:30px;line-height:1;color:var(--good);font-variant-numeric:tabular-nums}
.progress-heading small{font-size:15px;margin-left:2px}
.stage-meter{height:7px;margin-top:8px}
#monitor>.metrics{grid-template-columns:repeat(3,minmax(0,1fr));margin:12px 0}
#monitor>.metrics>.metric{padding:9px 10px;min-height:65px}
#monitor>.metrics>.metric:nth-child(4){border-left:0}
#monitor>.metrics>.metric:nth-child(n+4){border-top:1px solid var(--line)}
.metric>span{font-size:11px}.metric>b{font-size:21px}
#currentCheckpoint{font-size:15px;line-height:1.3}
.publish-dates{gap:10px;margin-top:12px}
.publish-dates>div{border-left:2px solid #36744a;padding-left:8px}
.publish-dates b{font-size:20px;color:#b1ffc2}
.publish-time,.publish-counts{font-size:12px;line-height:1.6}
.publish-counts{padding:8px;background:#0a2615;color:#b1ffc2}
.publication-panel h2{font-size:17px;color:var(--blue)}
.upload-panel .primary{width:100%;min-height:40px;justify-content:center;font-size:15px}
.upload-controls input[type=file]{font-size:13px;padding:4px 0}
.drop{padding:10px;background:#041108}
.upload-panel>p:last-child{font-size:12px;line-height:1.5}
.tile{grid-template-columns:1fr;padding:8px 12px;gap:3px}
.tile b{font-size:18px}.tile small{font-size:11px}.tile>span{font-size:11px}
.load-status{gap:6px 16px}.load-chip{font-size:11px}
.calendar-day{padding:7px 3px;min-height:64px}.calendar-day b{font-size:16px}
.coverage-heading h2{font-size:17px}.coverage-overview{font-size:13px}
summary{min-height:32px;display:list-item;align-content:center;font-size:13px}
#recent th{font-size:11px;padding:10px 7px}
#recent td{font-size:13px;padding:12px 7px;line-height:1.5}
#recent .recent-files{font-size:12px;color:#b1d9bd;gap:4px}
#recent .status-text{font-size:12px;padding:4px 6px}
#recent tr[aria-selected=true]{background:#10321c}
#recent tr[aria-selected=true] td:first-child{border-left:3px solid var(--good)}
#recent td:first-child .linkbtn{font-size:15px;min-height:32px}
@media(min-width:1100px){
 main>.grid{grid-template-columns:minmax(0,1.4fr) minmax(0,.85fr) minmax(0,1.05fr);gap:12px}
 main>.grid>.monitor-column,main>.grid>.tools-column,main>.grid>.history-column{display:flex;flex-direction:column;gap:12px;grid-column:auto;grid-row:auto;min-height:0;overflow:auto}
 .grid .monitor-panel{height:auto;overflow:visible;flex:none;grid-column:auto;grid-row:auto}
 .grid .coverage-panel{flex:none;overflow:visible}
 .grid .recent-panel{height:100%;flex:1;grid-column:auto;grid-row:auto;overflow:hidden}
 #monitor{height:auto;display:block}.panel{margin-bottom:0}
}
@media(min-width:801px) and (max-width:1099px){
 body{overflow:auto;height:auto;min-height:100dvh}
 main>.grid{overflow:visible;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);align-items:start}
 .grid>.history-column{grid-column:1/-1}
 .grid .monitor-panel,.grid .recent-panel{height:auto}
 .grid #recent{max-height:320px}
}
@media(max-width:800px){
 .grid{display:flex;flex-direction:column;gap:0}
 .grid>div{width:100%}.panel{margin-bottom:12px;padding:12px}
 .tile{padding:7px}.tile b{font-size:15px}
 .batch-title h2{font-size:22px}.publish-dates b{font-size:18px}
 #monitor>.metrics>.metric{padding:8px;min-height:60px}
 .metric>b{font-size:19px}.calendar-day b{font-size:14px}
 .activity-head small{font-size:11px}.progress-heading>b{font-size:26px}
}

/* Compact shell: one title and one navigation row above the shared view. */
header{min-height:34px;padding:3px 10px}
header strong{font-size:17px}header .brand-mark{width:24px;height:24px;font-size:18px}
header #version{font-size:11px;max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dc-functions{padding:4px 10px;gap:6px}
.dc-functions button,.dc-functions a{min-height:30px;padding:4px 10px;font-size:13px}
.dc-functions #priceFullWindow{margin-left:auto}.dc-functions #priceFullWindow:not([hidden])+a{margin-left:0}
#priceWorkspace,#inventoryWorkspace{padding:4px 8px 0}
#priceModuleStatus{font-size:12px;margin:3px 0}
#priceReviewFrame,#inventoryFrame{height:calc(100dvh - 76px)}
@media(max-width:520px){header strong{font-size:15px}.dc-functions{padding:4px 6px}.dc-functions button,.dc-functions a{font-size:12px;padding:4px 6px}#priceWorkspace,#inventoryWorkspace{padding:3px 4px 0}}
</style>
<script id="dc-shared-price-review">
(()=>{
 const views={data:{workspace:'dataWorkspace',button:'dataFunction'},inventory:{workspace:'inventoryWorkspace',button:'inventoryFunction',frame:'inventoryFrame',status:'inventoryModuleStatus',ready:'yipman:inventory-ready',path:'/inventory'},'price-review':{workspace:'priceWorkspace',button:'priceFunction',frame:'priceReviewFrame',status:'priceModuleStatus',ready:'yipman:price-review-ready',path:'/price-review'}};
 const ready=new Set(),timers={};
 function selected(){return views[location.hash.slice(1)]?location.hash.slice(1):'data';}
 function select(name){
  for(const [key,v] of Object.entries(views)){document.getElementById(v.workspace).hidden=key!==name;document.getElementById(v.button).setAttribute('aria-pressed',String(key===name));}
  const link=document.getElementById('priceFullWindow');link.hidden=name==='data';if(name!=='data')link.href='https://seafood-stock-watch.bronzedove3.chatgpt.site'+views[name].path;
  document.body.classList.toggle('price-review-active',name!=='data');
  const v=views[name],frame=v.frame&&document.getElementById(v.frame);
  if(frame&&!frame.hasAttribute('src')){frame.src=frame.dataset.src;timers[name]=setTimeout(()=>{if(!ready.has(name))document.getElementById(v.status).textContent=(name==='inventory'?'Inventory':'Price Review')+' is taking longer to open. Use Open full window if your browser blocks the embedded view.';},15000);}
  if(name==='data')window.dispatchEvent(new Event('dc:data-workspace-active'));
 }
 for(const [key,v] of Object.entries(views))document.getElementById(v.button).onclick=()=>{if(location.hash!=='#'+key)history.pushState(null,'','#'+key);select(key);};
 window.addEventListener('popstate',()=>select(selected()));window.addEventListener('hashchange',()=>select(selected()));
 window.addEventListener('message',event=>{if(event.origin!=='https://seafood-stock-watch.bronzedove3.chatgpt.site')return;for(const [key,v] of Object.entries(views)){if(v.frame&&event.source===document.getElementById(v.frame).contentWindow&&event.data?.type===v.ready){ready.add(key);clearTimeout(timers[key]);document.getElementById(v.status).hidden=true;}}});
 select(selected());
})();
</script>
<script>
(()=>{'use strict';
const $=id=>document.getElementById(id), esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stageLabel=v=>String(v||'Not reported').replace(/^PHASE3_/, '').replace(/_/g,' ').toLowerCase().replace(/\b[a-z]/g,c=>c.toUpperCase());
const metric=(k,v,tone='')=>'<div class="metric" data-tone="'+esc(tone)+'"><span>'+esc(k)+'</span><b>'+esc(v)+'</b></div>';
const statusTone=v=>['OK','COMPLETE','CURRENT','PASS','QUICK_CHECK_READY','COMPLETED'].includes(v)?'good':['MISSING','FAILED','FAILED_QA','ABORTED'].includes(v)?'bad':/HOLD|WARN|DELAY/.test(v||'')?'warn':'neutral';
const parse=v=>{if(v&&typeof v==='object')return v;try{return JSON.parse(v||'{}')}catch{return {}}};
const time=v=>{if(!v)return 'Not reported';const s=String(v);const d=new Date(/Z$|[+-]\d\d:\d\d$/.test(s)?s:s+'Z');return isNaN(d)?s:d.toLocaleString()};
let selected=null,busy=false,uploading=false,resuming=false,lastSnapshot=null;
const observations=new Map(),holdExpansion=new Map();
let activityState=null,freshnessCache=null,coverageData=null,coverageMode='calendar',coverageDate=null,coverageSelectionMade=false,coverageDetailOpen=false,publicationData=null;
const workstation=()=>typeof matchMedia==='function'&&matchMedia('(min-width:1500px) and (min-height:760px)').matches;
const requestCache=new Map(),panelState=new Map();
let currentHealth=null,activeData=null,recentData=null,requestedBatchId=null,inspectSequence=0;
const panelLabels={health:'Worker',monitor:'Batch',recent:'History',coverage:'Source dates',publication:'Published'};
function renderLoadStatus(){
 const entries=[...panelState.entries()];
 $('loadStatus').innerHTML=Object.keys(panelLabels).map(k=>{const p=panelState.get(k)||{};const label=p.pending?(p.checkedAt?'Updating':'Loading'):p.error?'Delayed':p.saved?'Saved reference':p.checkedAt?'Ready':'Waiting';return '<span class="load-chip" data-state="'+(p.error?'error':p.pending?'pending':p.saved?'saved':p.checkedAt?'ready':'pending')+'" title="'+esc(p.error||(p.checkedAt?'Last checked '+new Date(p.checkedAt).toLocaleTimeString():''))+'"><i aria-hidden="true"></i><b>'+panelLabels[k]+'</b> '+label+(p.elapsed&&!p.pending&&!p.error?' · '+(p.elapsed/1000).toFixed(1)+'s':'')+'</span>'}).join('');
 const pending=entries.filter(([,v])=>v.pending).length,failed=entries.filter(([,v])=>v.error).length;
 $('sync').textContent=pending?'Updating '+pending+' panel'+(pending===1?'':'s')+' · results appear as ready':failed?failed+' update'+(failed===1?'':'s')+' delayed · retrying automatically':'Live checks 15s · history & dates 60s';
}
function panelUpdate(name,values){panelState.set(name,{...panelState.get(name),...values});renderLoadStatus();}
function cachedRead(path,maxAge=0,force=false){
 const prior=requestCache.get(path)||{};
 if(prior.promise)return prior.promise;
 if(!force&&!prior.error&&prior.data&&Date.now()-prior.checkedAt<maxAge)return Promise.resolve(prior.data);
 const entry={...prior};requestCache.set(path,entry);
 entry.promise=api(path).then(data=>{entry.data=data;entry.checkedAt=Date.now();entry.error=null;return data}).catch(e=>{entry.error=e;throw e}).finally(()=>{entry.promise=null});
 return entry.promise;
}
function rememberReference(name,data,checkedAt){try{sessionStorage.setItem('yipman-dc8-'+name,JSON.stringify({data,checkedAt}));}catch{}}
function savedReference(name){try{const value=JSON.parse(sessionStorage.getItem('yipman-dc8-'+name)||'null');return value?.data&&Number.isFinite(value.checkedAt)&&Date.now()-value.checkedAt<86400000?value:null}catch{return null}}
function panelFailure(name,e){
 panelUpdate(name,{pending:false,error:e.message||String(e)});
 if(name==='health'){$('health').innerHTML='<b>Worker</b><span class="badge warn">Unconfirmed</span>';if(activityState){activityState.health=null;renderActivity();}return;}
 if(name==='coverage'&&coverageData){$('freshness').innerHTML=freshnessView(null,coverageData,freshnessCache);return;}
 if(name==='recent'&&recentData)return;
 if(name==='publication'&&publicationData){renderPublication(publicationData,true);return;}
 if(name==='monitor'&&lastSnapshot)return;
 $(name).innerHTML='<div class="panel-empty"><b>'+panelLabels[name]+' update delayed</b><span>Retrying automatically. Use Refresh to check now.</span></div>';
}
function loadingMonitor(id){return '<div class="bar"><h2>'+(id?'Batch #'+esc(id):'Batch monitor')+'</h2><span class="badge">Checking saved batch</span></div><div class="loading-grid">'+['Run','Checkpoint','Source rows','QA / Publish'].map(x=>'<div><span>'+x+'</span><b class="placeholder-line"></b></div>').join('')+'</div><p class="loading-note">Reading existing records. No upload needed.</p>';}
async function api(path,options={}){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),options.method?120000:15000);try{const r=await fetch(path,{...options,credentials:'same-origin',cache:'no-store',signal:controller.signal});let d;try{d=await r.json()}catch{throw Error([502,503,504].includes(r.status)?'Server temporarily unavailable ('+r.status+')':'Unexpected server response ('+r.status+')')}if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail||d));return d}catch(e){if(controller.signal.aborted)throw Error('Request timed out');throw e}finally{clearTimeout(timer)}}
function problem(id,e){$(id).innerHTML='<div class="notice bad">Unable to load: '+esc(e.message||e)+'. Retrying automatically; you can also use Refresh.</div>'}
function classify(b,r,detail){if(r?.processing_status==='QUEUED')return ['Queued','warn'];if(['STARTED','PAUSE_REQUESTED'].includes(r?.processing_status)){const stamp=detail.heartbeat_at;const age=stamp?(Date.now()-new Date(/Z$/.test(stamp)?stamp:stamp+'Z').getTime())/1000:null;return age===null||!Number.isFinite(age)?['Running · heartbeat unreported','warn']:age>180?['Heartbeat stale · needs review','bad']:['Processing','good']}if(['FAILED','ABORTED','FAILED_QA'].includes(r?.processing_status))return ['Failed · recovery required','bad'];if(/HOLD/.test(r?.processing_status||'')||b.processing_status==='PHASE3_QA_HOLD')return ['QA hold','warn'];if(r?.processing_status==='PAUSED')return ['Paused','warn'];if(r?.processing_status==='COMPLETED')return [b.processing_status==='QUICK_CHECK_READY_WITH_HOLDS'?'Completed · item holds':'Completed','good'];if(b.processing_status==='PHASE2C_READY')return ['Phase 2C ready · waiting for Phase 3','warn'];return [b.processing_status||'No active batch',''];}
const epoch=v=>{if(!v)return null;const s=String(v),n=Date.parse(/Z$|[+-]\d\d:\d\d$/.test(s)?s:s+'Z');return Number.isFinite(n)?n:null};
const elapsed=n=>n===null||!Number.isFinite(n)?'Not reported':n<60?Math.floor(Math.max(0,n))+'s':Math.floor(n/60)+'m '+Math.floor(n%60)+'s';
function failureKey(run){const d=parse(run?.detail_json),e=String(d.error||d.recovery_reason||'');const code=e.match(/(?:DatabaseError|Error)\((\d+)/);return code?'Database error '+code[1]:e.includes('HEARTBEAT')?'Heartbeat expired':e.split('\n')[0].slice(0,120)}
function runNotice(run,detail){
 const error=detail.error||detail.recovery_reason;if(!error)return '';
 const state=run?.processing_status;
 if(detail.recovery_reason==='SERVICE_DEPLOYMENT_SHUTDOWN'&&!detail.error&&['STARTED','QUEUED','PAUSE_REQUESTED','COMPLETED'].includes(state)){
  const message=state==='QUEUED'?'Deployment interruption · queued to resume.':state==='COMPLETED'?'Deployment interruption recovered.':'Previous deployment interruption · this run resumed.';
  return '<div class="notice"><b>'+esc(message)+'</b> Current activity is shown above.</div>';
 }
 return '<div class="notice bad"><b>Latest failure:</b> '+esc(error)+'</div>';
}
function activityView(state,now=Date.now()){
 const {run:r,detail:d,health:h,receivedAt,observation:o,pipeline}=state;
 const ownsRun=h?.worker_run_id===r?.pipeline_run_id&&h?.worker_instance&&h.worker_instance===d.worker_instance;
 const active=['STARTED','PAUSE_REQUESTED'].includes(r?.processing_status),queued=r?.processing_status==='QUEUED';
 const age=epoch(d.heartbeat_at)===null?null:Math.max(0,(now-epoch(d.heartbeat_at))/1000),snapshotAge=Math.max(0,(now-receivedAt)/1000);
 const workerAge=h?.worker_heartbeat_age_seconds==null?null:Number(h.worker_heartbeat_age_seconds)+Math.max(0,(now-(h.checkedAt||receivedAt))/1000);
 const workerLive=!!h?.worker_healthy&&workerAge!==null&&workerAge<=30&&snapshotAge<=45;
 const sinceProgress=(now-o.changedAt)/1000,waiting=Array.isArray(d.db_lock_waits)&&d.db_lock_waits.length>0;
 let label='No active run',tone='warn',note='Worker availability does not confirm that this batch is processing.',live=false;
 if(snapshotAge>45){label='Status feed delayed';tone='warn';note='Last successful check '+elapsed(snapshotAge)+' ago. Refresh to verify current state.';}
 else if(active){
  if(h?.worker===d.worker&&h?.worker_instance&&d.worker_instance&&h.worker_instance!==d.worker_instance){label='Worker restarted · recovery pending';tone='bad';note='This run belongs to an earlier worker instance. Wait for recovery; do not upload again.';}
  else if(waiting){label='Database lock wait';tone='bad';note='Worker is alive, but the transaction is waiting for another database connection.';}
  else if(age===null){label='Run heartbeat not reported';tone='warn';note='The server has not supplied a run heartbeat. Progress is unconfirmed.';}
  else if(age>90){label='Run heartbeat delayed';tone=age>180?'bad':'warn';note=workerLive&&ownsRun?'Worker is executing '+(h.worker_stage||'this run')+'; the database heartbeat is delayed.':workerLive?'Worker is online; this run has not reported a fresh heartbeat.':'Run and worker heartbeats need attention.';}
  else if(sinceProgress>120){label='Alive · progress not advancing';tone='warn';note='No checkpoint, row counter or database activity change observed for '+elapsed(sinceProgress)+'. This does not prove a failure.';}
  else if(o.advanced){label='Processing · activity observed';tone='good';live=true;note='Checkpoint or database row counters changed '+elapsed(sinceProgress)+' ago.';}
  else{label='Worker alive · observing progress';tone='good';live=true;note='Waiting for the next checkpoint or row-counter change.';}
  if(r?.processing_status==='PAUSE_REQUESTED'){label='Pause requested';tone='warn';live=false;note='Waiting for the worker to reach a safe checkpoint.';}
 }
 else if(queued){label='Queued · waiting for worker';note='No running task has claimed this run yet.';}
 else if(r?.processing_status==='COMPLETED'){label='Run completed';tone='good';note='Check the QA and publish result below.';}
 else if(['FAILED','FAILED_QA','ABORTED'].includes(r?.processing_status)){label='Stopped · recovery required';tone='bad';note='This run is no longer processing, even when the worker is online.';}
 else if(['QA_HOLD','PAUSED'].includes(r?.processing_status)){label=r.processing_status==='PAUSED'?'Paused':'QA hold';note='This run is not actively processing.';}
 const previous=pipeline.filter(x=>x.pipeline_run_id<(r?.pipeline_run_id||0)&&['FAILED','FAILED_QA','ABORTED'].includes(x.processing_status));
 const currentFailure=failureKey(r),sameFailures=currentFailure?pipeline.filter(x=>['FAILED','FAILED_QA','ABORTED'].includes(x.processing_status)&&failureKey(x)===currentFailure).length:0;
 let retry='';
 if(previous.length&&r?.processing_status==='COMPLETED')retry='Recovered after '+previous.length+' earlier failed runs.';
 else if(sameFailures>=2)retry='REPEATED ERROR · '+currentFailure+' appears in '+sameFailures+' failed runs.';
 else if(previous.length&&active)retry='CURRENT RECOVERY · Run #'+r.pipeline_run_id+' · '+previous.length+' earlier failed runs (history).';
 else if(previous.length)retry='REPEATED FAILURES · '+(previous.length+(['FAILED','FAILED_QA','ABORTED'].includes(r?.processing_status)?1:0))+' failed runs recorded. See run history.';
 return {label,tone,note,live,retry,eta:live&&Number.isFinite(d.progress_eta_seconds)&&d.progress_eta_seconds>0&&(!ownsRun||h.worker_stage===d.phase3_stage)?'Stage estimate ~'+Math.ceil(d.progress_eta_seconds/60)+'m left':'',runAge:active?elapsed(age):'Stopped',workerLabel:workerLive?'Online · '+elapsed(workerAge)+' ago':workerAge===null?'Not reported':'Delayed · '+elapsed(workerAge)+' ago',snapshotAge:elapsed(snapshotAge),progress:active?(d.progress_current!==undefined?d.progress_current+(d.progress_total?' / '+d.progress_total:'')+' '+(d.progress_unit||'rows')+(Number.isFinite(d.progress_pct)?' · '+d.progress_pct+'%':''):d.db_rows_modified!==undefined?d.db_rows_modified+' DB row changes':'Waiting for counter'):'—'};
}
function setActivity(id,run,pipeline,detail,health,checkedAt=Date.now()){
 const now=Date.now(),workerStage=health?.worker_run_id===run?.pipeline_run_id&&health?.worker_instance===detail.worker_instance?health.worker_stage:null,fingerprint=JSON.stringify([workerStage||detail.phase3_stage,detail.progress_current,detail.progress_total,detail.db_rows_modified,detail.db_rows_locked]);
 let observation=observations.get(id);
 if(!observation||observation.runId!==run?.pipeline_run_id)observation={runId:run?.pipeline_run_id,fingerprint,changedAt:now,advanced:false};
 else if(observation.fingerprint!==fingerprint)observation={...observation,fingerprint,changedAt:now,advanced:true};
 observations.set(id,observation);activityState={run,pipeline,detail,health,receivedAt:checkedAt,observation};renderActivity();
}
function renderActivity(){
 const box=$('liveness');if(!box||!activityState)return;const v=activityView(activityState);
 const terminal=activityState.run?.processing_status==='COMPLETED';const d=activityState.detail,h=activityState.health,owns=h?.worker_run_id===activityState.run?.pipeline_run_id&&h?.worker_instance===d.worker_instance;const showMeter=v.live&&Number.isFinite(d.progress_pct)&&d.progress_total>0&&(!owns||h.worker_stage===d.phase3_stage);const pct=showMeter?Math.max(0,Math.min(100,d.progress_pct)):null;
 const html='<div class="activity '+v.tone+(terminal?' terminal':'')+'"><div class="activity-head"><span class="pulse '+(v.live?'live':'')+'" aria-hidden="true"></span><strong>'+esc(v.label)+'</strong><small>Checked '+esc(v.snapshotAge)+' ago</small></div><div class="activity-lines">'+(!terminal?'<span><b>Run heartbeat</b> '+esc(v.runAge)+(v.runAge==='Stopped'||v.runAge==='Not reported'?'':' ago')+'</span>':'')+'<span><b>Worker</b> '+esc(v.workerLabel)+'</span>'+(!terminal?'<span class="stage-progress-text">'+esc(v.progress)+'</span>':'')+(v.eta?'<span>'+esc(v.eta)+'</span>':'')+'</div>'+(v.tone!=='good'?'<div class="activity-note">'+esc(v.note)+'</div>':'')+(v.retry&&!terminal?'<div class="retry"><strong>'+esc(v.retry)+'</strong></div>':'')+(pct!==null?'<div class="progress-heading"><span>Current stage</span><b>'+pct.toFixed(1)+'<small>%</small></b></div><div class="stage-meter" role="progressbar" aria-label="Current stage progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct+'"><span style="width:'+pct+'%"></span></div>':'')+'</div>';
 if(box.innerHTML!==html)box.innerHTML=html;
 const badge=$('runBadge');if(badge&&['STARTED','PAUSE_REQUESTED'].includes(activityState.run?.processing_status)){badge.className='badge '+v.tone;badge.textContent=v.label;}
 const stage=$('currentCheckpoint');if(stage&&h?.worker_healthy&&h.worker_run_id===activityState.run?.pipeline_run_id&&h.worker_instance&&h.worker_instance===d.worker_instance){stage.textContent=stageLabel(h.worker_stage||d.phase3_stage);stage.title=h.worker_stage||d.phase3_stage||'Not reported';}
}

const holdLabels={CURRENT_COST_MISSING:'Missing cost',COST_TO_SELLING_UOM_UNRESOLVED:'Unit conversion',SELLING_UOM_MISSING:'Selling unit'};
const holdActions={CURRENT_COST_MISSING:'Review receipt, report or OH cost evidence.',COST_TO_SELLING_UOM_UNRESOLVED:'Confirm the cost-to-selling unit conversion.',SELLING_UOM_MISSING:'Confirm the selling unit in the article master.'};
const publishVerified=p=>p?.status==='COMPLETED'&&p?.publish_result?.status==='PASS'&&p?.publish_result?.readback?.pass===true;
function pipelineView(d,qa,publish,run){
 const active=['STARTED','PAUSE_REQUESTED'].includes(run?.processing_status),p3=qa?.phase3;
 const steps=[
  {label:'Source saved',state:d.files?.length?'done':'waiting'},
  {label:'Normalized',state:['PASS','READY'].includes(d.phase2c?.result_status)?'done':'waiting'},
  {label:p3?.blocking_issue_count>0?'QA blocked':p3?'QA complete':'Phase 3',state:p3?.blocking_issue_count>0?'blocked':p3&&p3.blocking_issue_count===0?'done':active?'current':'waiting'},
  {label:publishVerified(publish)?'Published':publish?.status==='FAILED'?'Publish failed':'Publish',state:publishVerified(publish)?'done':publish?.status==='FAILED'?'blocked':['STARTED','QUEUED'].includes(publish?.status)?'current':'waiting'}
 ];
 return '<div class="pipeline-rail" aria-label="Batch milestones">'+steps.map((x,i)=>'<div class="pipeline-step '+x.state+'"><i aria-hidden="true">'+(x.state==='done'?'✓':x.state==='blocked'?'!':i+1)+'</i><span>'+esc(x.label)+'</span></div>').join('')+'</div>';
}
function holdView(qa){
 const count=qa?.phase3?.quick_check_hold_rows;if(!Number.isFinite(count)||count<=0)return '';
 const q=qa.quick_check||{},counts=Object.entries(q.reason_counts||{}).filter(([,n])=>Number(n)>0),rows=new Map();
 for(const [reason,upcs] of Object.entries(q.reason_upcs||{}))for(const upc of (Array.isArray(upcs)?upcs:[])){const key=String(upc);if(!rows.has(key))rows.set(key,new Set());rows.get(key).add(reason);}
 if(!rows.size)for(const item of q.hold_samples||[]){const key=String(item.upc||'');if(key)rows.set(key,new Set(item.reasons||[]));}
 const rowsHtml=[...rows].sort(([a],[b])=>a.localeCompare(b)).map(([upc,reasons])=>'<tr><td>'+esc(upc)+'</td><td>'+[...reasons].map(reason=>'<span class="issue-tag" title="'+esc(reason)+'">'+esc(holdLabels[reason]||stageLabel(reason))+'</span>').join('')+'</td></tr>').join('');
 return '<details class="qa-holds" data-detail="holds"><summary><strong><span class="hold-count">'+esc(count)+'</span> items need attention</strong><small>Review reasons &amp; UPCs</small></summary><div class="qa-holds-body"><div class="qa-reasons">'+counts.map(([reason,n])=>'<div class="qa-reason"><b>'+esc(n)+'</b><span>'+esc(holdLabels[reason]||stageLabel(reason))+'</span><small>'+esc(holdActions[reason]||'Review the item evidence before clearing this hold.')+'</small></div>').join('')+'</div><p>One item can have multiple reasons; reason counts overlap. '+(rows.size<count?'Showing '+rows.size+' available UPCs of '+count+'. ':'')+'Evidence for Batch #'+esc(qa.batch_id)+'.</p>'+(rowsHtml?'<div class="scroll"><table><thead><tr><th>UPC</th><th>Needs review</th></tr></thead><tbody>'+rowsHtml+'</tbody></table></div>':'<div class="empty">No UPC details returned. Open QA and publish evidence for the available result.</div>')+'</div></details>';
}
function renderCoverage(){
 const coverage=coverageData;if(!coverage)return;const rows=(coverage.rows||[]).slice().sort((a,b)=>a.date.localeCompare(b.date));
 if(!rows.length){$('coverage').innerHTML='<div class="empty">No coverage rows returned.</div>';return;}
 const due=rows.filter(x=>x.required_daily_due===true||x.pos_required_due===true||x.mvt_required_due===true),complete=due.filter(x=>x.overall_status==='COMPLETE').length;
 if(!coverageSelectionMade&&workstation()){coverageDate=(due[due.length-1]||rows[rows.length-1]).date;coverageSelectionMade=true;}
 const dateLabel=date=>date.slice(5).replace(/^0/,'').replace('-','/');
 const days=rows.map(x=>{const pos=x.sources?.POS?.status||'Unknown',mvt=x.sources?.MVT?.status||'Unknown';return '<button class="calendar-day" data-date="'+esc(x.date)+'" data-tone="'+statusTone(x.overall_status)+'" aria-pressed="'+(coverageDate===x.date)+'" aria-label="'+esc(x.date+' '+x.weekday+'; POS '+pos+'; MVT '+mvt)+'"><small>'+esc(x.weekday||'')+'</small><b>'+esc(dateLabel(x.date))+'</b><span class="day-sources"><span data-tone="'+statusTone(pos)+'">P</span><span data-tone="'+statusTone(mvt)+'">M</span></span></button>'}).join('');
 const selectedDay=rows.find(x=>x.date===coverageDate);
 const detail=selectedDay?'<details class="coverage-day-detail"'+(coverageDetailOpen?' open':'')+'><summary>Files for <strong>'+esc(selectedDay.date+' · '+selectedDay.weekday)+'</strong> <span class="status-text" data-tone="'+statusTone(selectedDay.overall_status)+'">'+esc(stageLabel(selectedDay.overall_status))+'</span></summary><div class="day-files">'+['POS','MVT','PRICE','OH'].map(k=>'<b>'+esc(k)+'</b><span>'+esc(selectedDay.sources?.[k]?.file||(selectedDay.sources?.[k]?.status==='NONE'?'No file for this date':selectedDay.sources?.[k]?.status)||'Unknown')+'</span>').join('')+'</div></details>':'';
 const cell=(x,k)=>{const value=x.sources?.[k]?.status||'—';return '<span class="coverage-state" data-tone="'+statusTone(value)+'">'+esc(value)+'</span>'};
 const table='<div class="scroll coverage-table"'+(coverageMode==='table'?'':' hidden')+'><table><thead><tr><th>Date</th><th>Day status</th><th>POS</th><th>MVT</th><th>Price</th><th>OH</th></tr></thead><tbody>'+rows.slice().reverse().map(x=>'<tr><td>'+esc(x.date)+'</td><td>'+esc(x.overall_status)+'</td><td>'+cell(x,'POS')+'</td><td>'+cell(x,'MVT')+'</td><td>'+cell(x,'PRICE')+'</td><td>'+cell(x,'OH')+'</td></tr>').join('')+'</tbody></table></div>';
 $('coverage').innerHTML='<div class="coverage-overview"><span><b>'+complete+' / '+due.length+'</b> due days complete</span><span>Daily POS · MVT</span></div><div class="coverage-calendar"'+(coverageMode==='calendar'?'':' hidden')+'><div class="calendar-grid">'+days+'</div><div class="calendar-legend"><span>Complete</span><span>Missing</span><span>Not due</span><b>P</b> POS <b>M</b> MVT</div>'+detail+'</div>'+table;
 const dayDetail=$('coverage').querySelector?.('.coverage-day-detail');if(dayDetail)dayDetail.ontoggle=()=>{coverageDetailOpen=dayDetail.open};
 $('calendarView').setAttribute('aria-pressed',String(coverageMode==='calendar'));$('tableView').setAttribute('aria-pressed',String(coverageMode==='table'));
 document.querySelectorAll('[data-date]').forEach(button=>button.onclick=()=>{coverageSelectionMade=true;coverageDate=coverageDate===button.dataset.date?null:button.dataset.date;coverageDetailOpen=!!coverageDate;renderCoverage();});
}

async function inspect(id,force=false){
 requestedBatchId=id;const sequence=++inspectSequence,started=Date.now();
 const same=lastSnapshot?.diagnostics?.batch?.batch_id===id;
 if(!same){lastSnapshot=null;activityState=null;$('monitor').innerHTML=loadingMonitor(id);}
 panelUpdate('monitor',{pending:true,error:null});
 const running=same&&['STARTED','QUEUED','PAUSE_REQUESTED'].includes(activityState?.run?.processing_status);
 const paths=['/v1/web-upload/diagnostics/batch-id/'+id,'/v1/web-upload/batches/'+id+'/qa-summary','/v1/web-upload/batches/'+id+'/chatgpt-publish-status'];
 const responses=paths.map(()=>({status:'pending'}));
 await Promise.allSettled(paths.map(async(path,index)=>{
  try{responses[index]={status:'fulfilled',value:await cachedRead(path,index===0?running?10000:30000:running?10000:60000,force)};}
  catch(reason){responses[index]={status:'rejected',reason};}
  if(sequence!==inspectSequence||requestedBatchId!==id)return;
  if(responses[0].status==='fulfilled')renderMonitor(id,responses,requestCache.get(paths[0]).checkedAt);
  else if(responses[0].status==='rejected')panelFailure('monitor',responses[0].reason);
 }));
 if(sequence===inspectSequence){const bad=responses.find(x=>x.status==='rejected');panelUpdate('monitor',{pending:false,error:bad?bad.reason.message:null,checkedAt:responses[0].status==='fulfilled'?requestCache.get(paths[0]).checkedAt:null,elapsed:Date.now()-started});}
}
function renderMonitor(id,responses,checkedAt){
const health=currentHealth,d=responses[0].value,b=d.batch||{},runs=(d.runs||[]).slice().sort((a,b)=>b.pipeline_run_id-a.pipeline_run_id),pipeline=runs.filter(r=>['PHASE3_RERUN','POST_RAW_PIPELINE'].includes(r.stage_name));const r=pipeline.find(r=>['STARTED','QUEUED','PAUSE_REQUESTED'].includes(r.processing_status))||pipeline[0]||runs[0],detail=parse(r?.detail_json),qa=responses[1].status==='fulfilled'?responses[1].value:null,publish=responses[2].status==='fulfilled'?responses[2].value:null;const publishLabel=publishVerified(publish)?'PASS':publish?.publish_result?.status==='PASS'?'Unverified':publish?.publish_result?.status||publish?.status||'Unknown';const [label,tone]=classify(b,r,detail),active=pipeline.some(x=>['QUEUED','STARTED','PAUSE_REQUESTED'].includes(x.processing_status)),attempts=pipeline.filter(x=>x.stage_name==='PHASE3_RERUN'&&x.code_version===health?.version&&['FAILED','FAILED_QA','QA_HOLD','ABORTED','PAUSED','COMPLETED'].includes(x.processing_status)).length,canResume=responses.every(x=>x?.status==='fulfilled')&&Date.now()-checkedAt<30000&&Date.now()-(health?.checkedAt||0)<30000&&!!health?.version&&b.processing_status==='PHASE2C_READY'&&!active&&attempts<3&&qa&&qa.phase3===null;const sameBatch=lastSnapshot?.diagnostics?.batch?.batch_id===id;const openDetails=new Map([...($('monitor').querySelectorAll?.('details')||[])].map((x,i)=>[x.dataset.detail||String(i),{open:sameBatch&&x.open,scroll:x.querySelector('.scroll')?.scrollTop||0}]));lastSnapshot={diagnostics:d,qa,publish};
$('monitor').innerHTML='<div class="bar"><div class="batch-title"><span class="batch-icon"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 8h8m-8 4h8m-8 4h4"/></svg></span><h2>Batch #'+esc(id)+'</h2></div><span id="runBadge" class="badge '+tone+'">'+esc(label)+'</span></div><div class="files">'+(d.files||[]).map(f=>'<span>'+esc(f.original_filename)+'</span>').join('')+'</div>'+pipelineView(d,qa,publish,r)+'<div id="liveness"></div><div class="metrics">'+metric('Run',r?'#'+r.pipeline_run_id:'None')+'<div class="metric"><span>Checkpoint</span><b id="currentCheckpoint" title="'+esc(detail.phase3_stage||detail.last_phase3_stage||'Not reported')+'">'+esc(stageLabel(detail.phase3_stage||detail.last_phase3_stage))+'</b></div>'+metric('Source rows',b.source_row_count)+metric('QA blockers',qa?.phase3?.blocking_issue_count??'Pending QA',qa?.phase3?.blocking_issue_count===0?'good':qa?.phase3?.blocking_issue_count>0?'warn':'')+metric('Ready / held',qa?.phase3?(qa.phase3.quick_check_ready_rows??'—')+' / '+(qa.phase3.quick_check_hold_rows??'—'):'Pending QA')+metric('Publish',publishLabel,statusTone(publishLabel))+'</div>'+holdView(qa)+((detail.error||(detail.recovery_reason&&detail.recovery_reason!=='SERVICE_DEPLOYMENT_SHUTDOWN')||['FAILED','FAILED_QA','ABORTED'].includes(r?.processing_status))?runNotice(r,detail):'')+(canResume?'<div class="notice">Resume Phase 3 from saved data. No upload needed.</div><button id="resume" class="primary">Resume Phase 3</button>':!active&&r?.processing_status!=='COMPLETED'&&attempts>=3?'<div class="notice bad">Recovery limit reached. Resolve the failure before retrying.</div>':'')+''+(responses.some(x=>x.status!=='fulfilled')?'<div class="evidence-pending">'+(responses.some(x=>x.status==='rejected')?'Some QA / publish evidence is unavailable; retrying.':'Checking QA and publish evidence…')+'</div>':'')+'<div id="actionStatus" role="status"></div><details class="monitor-details" data-detail="technical-root"><summary>Details &amp; history · '+runs.length+' runs</summary><div class="steps"><span class="'+(d.files?.length?'done':'')+'">Source stored</span><span class="'+(['PASS','READY'].includes(d.phase2c?.result_status)?'done':'')+'">Phase 2C: '+esc(d.phase2c?.result_status||'Unknown')+'</span><span>Phase 3 QA: '+esc(qa?(qa.qa_available?'Available — see result':'Not available'):'Unavailable')+'</span><span>Publish: '+esc(publishLabel)+'</span></div>'+((detail.recovery_reason==='SERVICE_DEPLOYMENT_SHUTDOWN'&&!detail.error)?runNotice(r,detail):'')+'<details data-detail="technical"><summary>Technical details</summary><div class="metrics">'+metric('Batch state',b.processing_status)+metric('Run status',r?.processing_status)+metric('Checkpoint',detail.phase3_stage||detail.last_phase3_stage||'Not reported')+metric('Run worker',detail.worker||'Not reported')+metric('Last run heartbeat',time(detail.heartbeat_at))+metric('Phase 2C rows',d.phase2c?.normalized_row_count)+metric('Database changes',detail.db_rows_modified??'Not reported')+'</div></details><details data-detail="runs"><summary>Run history · '+runs.length+' recorded runs</summary><div class="scroll"><table><thead><tr><th>Run</th><th>Stage / status</th><th>Started</th><th>Ended</th></tr></thead><tbody>'+runs.map(x=>'<tr><td>#'+esc(x.pipeline_run_id)+'</td><td>'+esc(x.stage_name)+'<br>'+esc(x.processing_status)+'</td><td>'+esc(time(x.started_at))+'</td><td>'+esc(time(x.completed_at))+'</td></tr>').join('')+'</tbody></table></div></details><details data-detail="qa"><summary>QA and publish evidence</summary><pre>'+esc(JSON.stringify({qa:qa||{status:responses[1].status,error:responses[1].reason?String(responses[1].reason):null},publish:publish||{status:responses[2].status,error:responses[2].reason?String(responses[2].reason):null}},null,2))+'</pre></details><details data-detail="diagnostics"><summary>Full batch diagnostics</summary><button id="download">Download diagnostics</button><pre id="fullDiagnostics" hidden></pre></details></details>';
[...($('monitor').querySelectorAll?.('details')||[])].forEach((x,i)=>{const previous=openDetails.get(x.dataset.detail||String(i));x.open=x.dataset.detail==='holds'?(holdExpansion.has(id)?holdExpansion.get(id):previous?previous.open:workstation()):!!previous?.open;const area=x.querySelector('.scroll');if(area)area.scrollTop=previous?.scroll||0});
const holdSection=$('monitor').querySelector?.('.qa-holds');if(holdSection)holdSection.querySelector('summary').onclick=()=>holdExpansion.set(id,!holdSection.open);
setActivity(id,r,pipeline,detail,health,checkedAt);
if($('resume'))$('resume').onclick=async()=>{if(resuming)return;resuming=true;$('resume').disabled=true;try{const result=await api('/v1/web-upload/batches/'+id+'/resume-phase3',{method:'POST',headers:{'Content-Type':'application/json'}});$('actionStatus').textContent='Server response: '+JSON.stringify(result)}catch(e){$('actionStatus').textContent=e.message}finally{resuming=false;refresh(true)}};
const diagnostics=$('monitor').querySelector?.('[data-detail=diagnostics]');if(diagnostics)diagnostics.ontoggle=()=>{if(diagnostics.open){$('fullDiagnostics').hidden=false;$('fullDiagnostics').textContent=JSON.stringify(d,null,2)}};
$('download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(lastSnapshot,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='yipman-batch-'+id+'-diagnostics.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
}
function renderPublication(data,stale=false){
 const p=data.published;
 if(!p?.verified){$('publication').innerHTML='<div class="publish-empty">No verified publish found.</div>';return;}
 const attempt=data.latest_attempt,newer=attempt&&attempt.publish_run_id>p.publish_run_id&&!attempt.verified;
 $('publication').innerHTML='<div class="publish-top"><button class="linkbtn" id="viewPublishedBatch">Batch #'+esc(p.batch_id)+'</button><span class="badge good">PASS · verified</span></div><div class="publish-time">Published '+esc(time(p.completed_at))+' · Run #'+esc(p.publish_run_id)+'</div><div class="publish-dates"><div><span>Published POS through</span><b>'+esc(p.pos_through?.slice(0,10))+'</b></div><div><span>Published MVT through</span><b>'+esc(p.mvt_through?.slice(0,10))+'</b></div></div><div class="publish-counts">'+esc(p.ready_rows??'—')+' ready · '+esc(p.held_rows??'—')+' QA holds excluded</div><details><summary>Published batch files · '+(p.files||[]).length+'</summary><div class="publish-files">'+(p.files||[]).map(f=>'<div>'+esc(f.original_filename)+'</div>').join('')+'</div></details>'+(newer?'<div class="notice">Newer publish #'+esc(attempt.publish_run_id)+': '+esc(stageLabel(attempt.status))+'. Showing last verified result.</div>':'')+(stale?'<div class="notice">Publish check delayed. Showing last verified result.</div>':'');
 $('viewPublishedBatch').onclick=()=>{selected=Number(p.batch_id);$('follow').hidden=false;inspect(selected,true);renderRecent();};
}
function freshnessFromCoverage(coverage){
 if(!coverage?.latest)return {sources:{}};
 const sources={},mapping={POS:'POS',MVT:'MVT',PRICE:'PRICE',OH:'OH',FRESH:'LIVE_FRESH',FRZ:'FROZEN'};
 for(const [key,sourceKey] of Object.entries(mapping)){
  const row=coverage?.latest?.[sourceKey]||{},daily=key==='POS'||key==='MVT',reference=daily?coverage?.[key==='POS'?'pos_required_through':'mvt_required_through']:coverage?.today;
  const age=row.date&&reference?Math.max(0,Math.round((Date.parse(reference)-Date.parse(row.date))/86400000)):null;
  sources[key]={...row,state:!row.date?'No snapshot':key==='PRICE'?'Latest snapshot':age===0?'CURRENT':age===null?'Latest snapshot':age+'D',tone:!row.date?'neutral':key==='PRICE'?'neutral':age===0?'good':age===1?'warn':'bad'};
 }
 return {sources};
}
function freshnessView(fresh,coverage,cached){
 const data=fresh||cached?.data||freshnessFromCoverage(coverage);
 const tiles=['POS','MVT','PRICE','OH','FRESH','FRZ'].map(k=>{const source=data.sources[k]||{};return '<div class="tile" data-tone="'+esc(source.tone||'neutral')+'" title="'+esc(source.file||'No source file returned')+'"><span>'+esc(k==='FRZ'?'Frozen':k==='FRESH'?'Live / Fresh':k)+'</span><b>'+esc(source.date)+'</b><small>'+esc(source.state||'Checking')+'</small></div>'}).join('');
 const warning=fresh?'':cached?'Saved source dates · checked '+new Date(cached.checkedAt).toLocaleString()+'. Updating independently.':'Reading source dates…';
 return tiles+(warning?'<div class="fresh-warning" role="status">'+esc(warning)+'</div>':'');
}
function renderRecent(){const recent=recentData,a=activeData;if(!recent)return;
const rows=(recent.batches||recent.rows||[]).slice();if(a?.active_batch&&!rows.some(x=>x.batch_id===a.active_batch.batch_id))rows.unshift(a.active_batch);$('recent').innerHTML='<table><thead><tr><th>Batch</th><th>Files</th><th>Status</th><th>Ready / held</th></tr></thead><tbody>'+rows.map(x=>'<tr aria-selected="'+(x.batch_id===(selected||a?.active_batch?.batch_id||a?.latest_batch?.batch_id))+'"><td><button class="linkbtn" data-batch="'+Number(x.batch_id)+'">#'+esc(x.batch_id)+'</button></td><td>'+'<div class="recent-files">'+((x.files||[]).length?(x.files||[]).map(f=>'<span>'+esc(f.original_filename)+'</span>').join(''):esc(x.batch_label||'—'))+'</div>'+'</td><td>'+'<span class="status-text" data-tone="'+esc(statusTone(x.processing_status))+'" title="'+esc(x.processing_status)+'">'+esc(x.processing_status==='QUICK_CHECK_READY_WITH_HOLDS'?'Ready · item holds':x.processing_status==='QUICK_CHECK_READY'?'Ready':stageLabel(x.processing_status))+'</span></td><td>'+esc(x.quick_check_ready_rows)+' / '+esc(x.quick_check_hold_rows)+'</td></tr>').join('')+'</tbody></table>';if(!rows.length)$('recent').innerHTML='<div class="empty">No batches returned.</div>';document.querySelectorAll('[data-batch]').forEach(btn=>btn.onclick=()=>{selected=Number(btn.dataset.batch);$('follow').hidden=false;inspect(selected,true);renderRecent()})
}
function acceptCoverage(coverage,checkedAt,saved=false){coverageData=coverage;freshnessCache={data:freshnessFromCoverage(coverage),checkedAt};$('freshness').innerHTML=freshnessView(saved?null:freshnessCache.data,coverage,freshnessCache);renderCoverage();}
async function refresh(force=false){
 if(uploading||resuming)return;
 const tasks=[];
 async function loadPanel(name,path,maxAge,accept){
  const started=Date.now();panelUpdate(name,{pending:true,error:null});
  try{const data=await cachedRead(path,maxAge,force),checkedAt=requestCache.get(path).checkedAt;await accept(data,checkedAt);panelUpdate(name,{pending:false,error:null,saved:false,checkedAt,elapsed:Date.now()-started});}
  catch(e){panelFailure(name,e);}
 }
 tasks.push(loadPanel('health','/healthz',10000,(h,checkedAt)=>{currentHealth={...h,checkedAt};$('version').textContent='API '+h.version;$('health').innerHTML='<b>Worker</b><span class="badge '+(h.worker_healthy?'good':'warn')+'">'+esc(h.worker_state||'Unknown')+'</span>';if(activityState){activityState.health=currentHealth;renderActivity();}}));
 tasks.push(loadPanel('recent','/v1/web-upload/recent?limit=12',60000,(data,checkedAt)=>{recentData=data;rememberReference('recent',data,checkedAt);renderRecent();}));
 tasks.push(loadPanel('publication','/v1/app/data-center/latest-publish',60000,(data)=>{publicationData=data;renderPublication(data);}));
 tasks.push(loadPanel('coverage','/v1/backoffice/data-health?days=14',60000,(data,checkedAt)=>{acceptCoverage(data,checkedAt);rememberReference('coverage',data,checkedAt);}));
 const activeTask=(async()=>{
  try{const previous=activeData;activeData=await cachedRead('/v1/web-upload/active',10000,force);renderRecent();const id=selected||activeData.active_batch?.batch_id||activeData.latest_batch?.batch_id;const changed=!!activeData.active_batch&&(!previous?.active_batch||previous.active_batch.active_pipeline_run_id!==activeData.active_batch.active_pipeline_run_id||previous.active_batch.processing_status!==activeData.active_batch.processing_status);if(changed&&id===activeData.active_batch.batch_id){lastSnapshot=null;activityState=null;}if(id)await inspect(id,force||changed);else{$('monitor').innerHTML='<div class="panel-empty"><b>No batches yet</b><span>Upload source files to begin.</span></div>';panelUpdate('monitor',{pending:false,error:null,checkedAt:Date.now()});}}
  catch(e){panelFailure('monitor',e);}
 })();tasks.push(activeTask);
 await Promise.allSettled(tasks);
}
function restoreReferences(){
 $('monitor').innerHTML=loadingMonitor();$('freshness').innerHTML=freshnessView(null,null,null);
 for(const name of ['recent','coverage']){const saved=savedReference(name);if(!saved)continue;panelUpdate(name,{saved:true,checkedAt:saved.checkedAt});if(name==='recent'){recentData=saved.data;renderRecent();}else acceptCoverage(saved.data,saved.checkedAt,true);}
 renderLoadStatus();
}
$('calendarView').onclick=()=>{coverageMode='calendar';renderCoverage()};$('tableView').onclick=()=>{coverageMode='table';renderCoverage()};
$('refresh').onclick=()=>refresh(true);$('follow').onclick=()=>{selected=null;$('follow').hidden=true;refresh(true)};
$('upload').onclick=async()=>{if(uploading)return;const files=[...$('files').files];if(!files.length){$('uploadStatus').textContent='Select at least one source file.';return}uploading=true;$('upload').disabled=true;$('files').disabled=true;let created=null;try{created=await api('/v1/web-upload/batches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label:$('note').value.trim()||'Data Center '+new Date().toLocaleString()})});const session=created.session_id||created.batch_key||created.session?.session_id;if(!session)throw Error('No upload session returned. Inspect recent batches before trying again.');for(let i=0;i<files.length;i++){const fd=new FormData();fd.append('file',files[i]);$('uploadStatus').textContent='Uploading '+(i+1)+' / '+files.length+': '+files[i].name;await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/files',{method:'POST',body:fd})}$('uploadStatus').textContent='Committing batch…';const done=await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/commit',{method:'POST'});selected=done.batch_id||created.batch_id||null;$('follow').hidden=!selected;$('uploadStatus').textContent='Batch #'+(selected||'—')+' committed. Processing and QA are tracked in the monitor.';$('files').value=''}catch(e){$('uploadStatus').textContent='Upload stopped: '+e.message+(created?' Batch/session was created. Inspect recent batches before uploading again.':' No successful creation response received; check recent batches before retrying.')}finally{uploading=false;$('files').disabled=false;$('upload').disabled=!!created&&!!$('files').files.length;refresh(true)}};
restoreReferences();if(!document.getElementById('dataWorkspace').hidden)refresh();setInterval(()=>{if(!document.hidden&&!document.getElementById('dataWorkspace').hidden)refresh()},15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!document.getElementById('dataWorkspace').hidden)refresh()});
window.addEventListener('dc:data-workspace-active',()=>refresh());
setInterval(()=>{if(!document.hidden&&!document.getElementById('dataWorkspace').hidden)renderActivity()},1000);
})();
</script></body></html>'''




from startup_logo import apply_startup_logo
DATA_CENTER_HTML = apply_startup_logo(DATA_CENTER_HTML)

from fishfinder_brand import rename_display
DATA_CENTER_HTML = rename_display(DATA_CENTER_HTML)
