from __future__ import annotations

YIPMAN_DESKTOP_CSS = r"""
@media (min-width:760px){
  html.yipman-desktop,html.yipman-desktop body{height:100%!important;min-height:100%!important;background:#f3f7fb!important;overflow:hidden!important;overscroll-behavior-y:auto!important}
  html.yipman-desktop #ydesk{height:100vh;overflow:hidden}
  html.yipman-desktop #app{display:none!important}
  #ydesk{--nav:#153351;--nav2:#0f2842;--blue:#0b72f4;--ink:#10233d;--muted:#6b7d92;--line:#dbe5ef;--bg:#f3f7fb;--card:#fff;--green:#21a867;--amber:#dda00e;--red:#d94159;--purple:#7658e8;--shadow:0 7px 24px rgba(22,49,79,.07);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
  #ydesk *{box-sizing:border-box}#ydesk button,#ydesk input,#ydesk select,#ydesk textarea{font:inherit}#ydesk button{cursor:pointer}
  #ydesk .app{height:100vh;min-height:0;display:grid;grid-template-columns:220px minmax(0,1fr);overflow:hidden}
  #ydesk .side{position:relative;top:auto;height:100vh;min-height:0;background:#fff;border-right:1px solid var(--line);padding:16px 12px;display:flex;flex-direction:column;z-index:30;overflow-y:auto;overscroll-behavior:contain}
  #ydesk .brand{padding:2px 8px 14px}#ydesk .brand h1{margin:0;font-size:25px;letter-spacing:-.8px}#ydesk .brand h1 span{color:var(--blue)}#ydesk .brand small{font-size:10px;color:var(--muted)}
  #ydesk .nav{position:static!important;left:auto!important;right:auto!important;bottom:auto!important;height:auto!important;display:flex!important;flex-direction:column!important;grid-template-columns:none!important;gap:3px!important;padding:0!important;background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important;backdrop-filter:none!important;z-index:auto!important}#ydesk .navbtn{border:0!important;background:transparent;color:#425873;border-radius:10px;padding:10px 11px!important;display:flex!important;flex-direction:row!important;align-items:center!important;justify-content:flex-start!important;gap:10px!important;text-align:left!important;font-size:13px!important;font-weight:780!important;width:100%!important;min-width:0!important;transform:none!important;box-shadow:none}#ydesk .navbtn:hover{background:#f2f6fb}#ydesk .navbtn.active{background:#e9f3ff;color:#0868dc}#ydesk .navbtn .ico{width:21px;text-align:center;font-size:16px}
  #ydesk .sep{height:1px;background:#edf2f6;margin:9px 4px}#ydesk .sidefoot{margin-top:auto}#ydesk .fresh{border:1px solid var(--line);border-radius:12px;padding:10px;background:#fbfdff}#ydesk .fresh h4{margin:0 0 7px;font-size:11px}#ydesk .frow{display:flex;justify-content:space-between;font-size:10px;color:#586a7f;margin:5px 0}#ydesk .fdot{width:7px;height:7px;border-radius:50%;display:inline-block;background:var(--green);margin-left:4px}#ydesk .fdot.warn{background:var(--amber)}#ydesk .version{font-size:9px;color:#8390a0;padding:8px 3px 0}
  #ydesk .shell{min-width:0;height:100vh;min-height:0;overflow-y:auto!important;overflow-x:hidden!important;overscroll-behavior-y:auto!important;scrollbar-gutter:stable;scroll-behavior:auto}#ydesk .topbar{height:62px;background:linear-gradient(100deg,var(--nav2),var(--nav));display:flex;align-items:center;gap:12px;padding:0 17px;color:#fff;position:sticky;top:0;z-index:25;box-shadow:0 2px 12px rgba(0,20,40,.13)}
  #ydesk .gsearch{height:40px;background:#fff;border-radius:13px;display:flex;align-items:center;gap:8px;padding:0 12px;width:min(680px,48vw);color:#6a7a8e}#ydesk .gsearch input{border:0;outline:0;flex:1;min-width:0;color:#142a43;font-size:13px}#ydesk .kbd{font-size:9px;background:#edf2f6;border-radius:5px;padding:2px 5px;color:#66778a}
  #ydesk .live{font-size:9px;background:#fff;color:#0868dc;border-radius:999px;padding:4px 7px;font-weight:900}#ydesk .topstats{margin-left:auto;display:flex;gap:7px}#ydesk .topstat{border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.07);border-radius:9px;padding:6px 9px;font-size:8px;min-width:72px}#ydesk .topstat b{display:block;font-size:14px}#ydesk .avatar{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#6f8398;font-size:10px;font-weight:900}
  #ydesk .work{padding:17px 18px 28px}#ydesk .mod{display:none}#ydesk .mod.active{display:block}#ydesk .pagehead{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin-bottom:12px}#ydesk .pagehead h2{font-size:29px;line-height:1;margin:0;letter-spacing:-.7px}#ydesk .pagehead p{font-size:11px;color:var(--muted);margin:5px 0 0}
  #ydesk .actions{display:flex;gap:7px;align-items:center;flex-wrap:wrap}#ydesk .btn{border:1px solid var(--line);background:#fff;color:#405970;border-radius:8px;padding:7px 10px;font-size:10px;font-weight:850}#ydesk .btn:hover{background:#f5f9fc}#ydesk .btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}#ydesk .btn.danger{background:#fff0f2;border-color:#ffcbd3;color:#b62e44}#ydesk .btn.good{background:#e9f8ef;border-color:#c2e7d1;color:#167d4a}
  #ydesk .input,#ydesk .select{height:34px;border:1px solid var(--line);border-radius:8px;background:#fff;padding:0 9px;color:#324a64;font-size:11px;outline:0}#ydesk .select{min-width:135px}
  #ydesk .card{background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);min-width:0;overflow:hidden}#ydesk .cardhead{padding:10px 12px;border-bottom:1px solid #e8eef4;display:flex;justify-content:space-between;align-items:center;gap:10px}#ydesk .cardhead h3{margin:0;font-size:12px}#ydesk .cardbody{padding:11px 12px}
  #ydesk .badge{display:inline-flex;align-items:center;gap:3px;border-radius:999px;padding:4px 7px;font-size:9px;font-weight:900;white-space:nowrap}#ydesk .badge.blue{background:#e8f3ff;color:#0868dc}#ydesk .badge.green{background:#e9f8ef;color:#147b49}#ydesk .badge.amber{background:#fff4d8;color:#956000}#ydesk .badge.red{background:#ffe9ed;color:#b82f45}#ydesk .badge.purple{background:#f1edff;color:#6145cb}#ydesk .badge.gray{background:#edf2f6;color:#5d6d7d}
  #ydesk .small{font-size:10px;color:var(--muted)}#ydesk .tiny{font-size:9px;color:var(--muted)}#ydesk .kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}#ydesk .kpi{border:1px solid #e1e8ef;border-radius:9px;padding:8px 9px;background:#fff;min-width:0}#ydesk .kpi label{display:block;font-size:8px;text-transform:uppercase;letter-spacing:.3px;color:#718197;font-weight:900}#ydesk .kpi strong{display:block;font-size:18px;margin-top:2px;white-space:nowrap}#ydesk .kpi small{font-size:9px;color:#758496}
  #ydesk .tabs{display:flex;gap:5px;flex-wrap:wrap}#ydesk .tab{border:1px solid var(--line);background:#fff;color:#4c647d;border-radius:8px;padding:6px 9px;font-size:10px;font-weight:850}#ydesk .tab.active{background:#e9f3ff;border-color:#b9d8ff;color:#0869dd}
  #ydesk .tablewrap{overflow:auto}#ydesk table{width:100%;border-collapse:collapse}#ydesk th{position:sticky;top:0;z-index:2;background:#fbfdff;border-bottom:1px solid #dde7ef;padding:7px 8px;text-align:left;font-size:8px;text-transform:uppercase;letter-spacing:.3px;color:#708095;white-space:nowrap}#ydesk td{border-bottom:1px solid #edf2f6;padding:7px 8px;font-size:10px;white-space:nowrap;vertical-align:middle}#ydesk tr.pick{cursor:pointer}#ydesk tr.pick:hover td{background:#f7fbff}#ydesk tr.selected td{background:#eef6ff}
  #ydesk .split{display:grid;grid-template-columns:minmax(650px,1.35fr) minmax(420px,.65fr);gap:10px;align-items:start}#ydesk .analysis{position:sticky;top:76px;align-self:start;max-height:none;overflow:visible}#ydesk .analysis::-webkit-scrollbar{width:7px}#ydesk .analysis::-webkit-scrollbar-thumb{background:#cad6e1;border-radius:999px}
  #ydesk .qtools{display:flex;align-items:center;gap:7px;margin-bottom:9px;flex-wrap:wrap}#ydesk .qf{border:1px solid var(--line);background:#fff;color:#4f647c;border-radius:8px;padding:7px 10px;font-size:10px;font-weight:850}#ydesk .qf.active{background:var(--blue);border-color:var(--blue);color:#fff}
  #ydesk .flist{display:flex;flex-direction:column;gap:7px}#ydesk .fam{border:1px solid var(--accent);border-left-width:5px;border-radius:11px;background:linear-gradient(90deg,var(--tint),#fff);overflow:hidden}#ydesk .fhead{display:grid;grid-template-columns:24px minmax(190px,1.22fr) repeat(5,minmax(86px,.7fr)) 130px;gap:7px;align-items:center;padding:8px 9px;cursor:pointer}#ydesk .chev{font-size:17px;color:#4b6178}#ydesk .fname .id{font-size:10px;font-weight:900}#ydesk .fname .desc{font-size:13px;font-weight:900;margin:1px 0}#ydesk .fm{border-left:1px solid rgba(25,60,90,.09);padding-left:7px}#ydesk .fm label{display:block;font-size:7px;text-transform:uppercase;color:#68798d;font-weight:900}#ydesk .fm strong{display:block;font-size:15px;white-space:nowrap}#ydesk .recent{font-size:8px;line-height:1.45}#ydesk .recent b{font-size:9px}
  #ydesk .fbody{display:none;background:rgba(255,255,255,.78);border-top:1px solid rgba(30,60,90,.1);padding:8px 9px}#ydesk .fam.open .fbody{display:block}#ydesk .hier{border-left:2px solid #cbdbe9;padding-left:9px}#ydesk .recv{border:1px solid #dfe7ef;border-radius:8px;background:#fff;margin-bottom:6px}#ydesk .recvhead{display:grid;grid-template-columns:minmax(170px,1.3fr) 1fr 1fr .72fr .8fr;gap:7px;align-items:center;padding:7px 8px;background:#f8fbfe;font-size:9px}#ydesk .sap{display:grid;grid-template-columns:minmax(180px,1.3fr) .7fr .7fr .8fr 1fr;gap:7px;align-items:center;padding:7px 8px;border-top:1px solid #edf2f6;font-size:9px}#ydesk .pair{margin:5px 7px 7px;border:1px dashed #c8d8e7;border-radius:7px;overflow:hidden}#ydesk .pairhead,#ydesk .upcrow{display:grid;grid-template-columns:minmax(190px,1.35fr) repeat(6,.65fr);gap:7px;align-items:center;padding:6px 7px;font-size:9px}#ydesk .pairhead{background:#edf6ff}#ydesk .upcrow{border-top:1px solid #e7eef5;background:#fff;cursor:pointer}#ydesk .upcrow:hover{background:#f7fbff}#ydesk .prefix{display:inline-block;min-width:28px;text-align:center;padding:3px 5px;border-radius:5px;background:#e9f3ff;color:#0766d8;font-weight:900}#ydesk .prefix.service{background:#e9f8ef;color:#157b49}#ydesk .prefix.package{background:#f1edff;color:#6247cb}
  #ydesk .qhero{padding:11px}#ydesk .qtitle{display:flex;justify-content:space-between;gap:9px}#ydesk .qtitle h3{font-size:17px;margin:0}#ydesk .qtitle p{margin:3px 0 0;font-size:9px;color:var(--muted)}#ydesk .qstats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px}#ydesk .qtabs{padding:0 11px 9px}#ydesk .qpanel{display:none;padding:0 11px 11px}#ydesk .qpanel.active{display:block}#ydesk .infobox{border:1px solid #e1e8ef;border-radius:8px;padding:8px;background:#fff}#ydesk .infobox h4{font-size:10px;margin:0 0 6px}#ydesk .kv{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px 10px;font-size:9px}#ydesk .kv span:nth-child(odd){color:#738398}#ydesk .kv span:nth-child(even){font-weight:900;text-align:right}#ydesk .row2{display:grid;grid-template-columns:1fr 1fr;gap:8px}#ydesk .row3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
  #ydesk .price{display:inline-block;padding:4px 6px;border-radius:6px;background:#e9f3ff;color:#0863d4;font-weight:900}#ydesk .price.tested{background:#e8f7fb;color:#00738d}#ydesk .price.testing{background:#f1edff;color:#6548d3}#ydesk .price.company{background:#e9f8ef;color:#147a48}
  #ydesk .sectiontitle{font-size:9px;text-transform:uppercase;letter-spacing:.35px;color:#66798f;font-weight:900;margin:10px 0 6px}#ydesk .note{border-radius:8px;padding:8px 9px;font-size:9px;line-height:1.45}#ydesk .note.blue{background:#eef6ff;border:1px solid #d3e7ff;color:#315e8f}#ydesk .note.amber{background:#fff7e6;border:1px solid #f5dfae;color:#82602b}#ydesk .note.green{background:#edf9f2;border:1px solid #cae9d6;color:#356d50}#ydesk .note.red{background:#fff0f2;border:1px solid #ffd0d8;color:#9d3d4a}
  #ydesk .timeline{display:flex;flex-direction:column;gap:5px}#ydesk .event{display:grid;grid-template-columns:82px 1fr 70px 100px 100px;gap:6px;align-items:center;border:1px solid #e1e8ef;border-radius:7px;padding:6px 7px;font-size:9px;background:#fff}
  #ydesk .chart{height:190px;border:1px solid #e1e8ef;border-radius:9px;background:linear-gradient(#fff,#fbfdff);display:flex;align-items:end;gap:5px;padding:14px 12px 22px}#ydesk .bar{flex:1;min-width:5px;max-width:34px;background:#72b3f4;border-radius:4px 4px 0 0;position:relative}#ydesk .bar span{position:absolute;bottom:-16px;left:50%;transform:translateX(-50%);font-size:7px;color:#718197}
  #ydesk .ordtop{display:grid;grid-template-columns:1fr 1fr 1.35fr;gap:7px}#ydesk .datebox{border:1px solid #dfe7ef;border-radius:9px;padding:8px;background:#fff}#ydesk .datebox label{font-size:8px;text-transform:uppercase;color:#708197;font-weight:900}#ydesk .datebox strong{font-size:15px;display:block}#ydesk .calendar{display:grid;grid-template-columns:repeat(14,1fr);gap:3px;margin-top:7px}#ydesk .day{border:1px solid #dfe7ef;border-radius:7px;background:#fff;text-align:center;padding:5px 2px;font-size:8px}#ydesk .day b{display:block;font-size:10px}#ydesk .day.obs{background:#edf9f2;border-color:#bce3cb}#ydesk .day.sel{background:#e9f3ff;border-color:#91c2ff;color:#0867d9}#ydesk .day.next{background:#f1edff;border-color:#b9abf5;color:#6045c9}#ydesk input.final{width:62px;height:28px;border:1px solid #b9d6f8;border-radius:6px;padding:0 5px;font-weight:900;color:#075fd0}
  #ydesk .pfilters{display:grid;grid-template-columns:.8fr 1.15fr 1.35fr;gap:8px;margin-bottom:9px}#ydesk .filterbox{border:1px solid var(--line);border-radius:9px;background:#fff;padding:8px}#ydesk .filterbox label{display:block;font-size:8px;text-transform:uppercase;color:#708197;font-weight:900;margin-bottom:5px}#ydesk .pqueue{display:flex;flex-direction:column;gap:7px}#ydesk .pcard{background:#fff;border:1px solid var(--line);border-left:5px solid var(--pc);border-radius:10px;padding:8px 9px;cursor:pointer}#ydesk .pcard.selected{box-shadow:0 0 0 2px rgba(11,114,244,.16)}#ydesk .ptop{display:grid;grid-template-columns:minmax(210px,1.35fr) repeat(3,.55fr) minmax(145px,.8fr) 80px;gap:8px;align-items:center}#ydesk .pname b{font-size:12px}#ydesk .pname div{font-size:9px;color:#728196;margin-top:2px}#ydesk .pm label{display:block;font-size:7px;text-transform:uppercase;color:#718197;font-weight:900}#ydesk .pm strong{font-size:15px}
  #ydesk .perfgrid,#ydesk .pigrid,#ydesk .datagrid{display:grid;grid-template-columns:minmax(660px,1.4fr) minmax(390px,.6fr);gap:10px}#ydesk .insight{border-left:3px solid var(--blue);padding:7px 8px;background:#f5f9ff;border-radius:0 7px 7px 0;font-size:9px;line-height:1.4;margin:6px 0}
  #ydesk .pirow{display:grid;grid-template-columns:minmax(190px,1.15fr) repeat(5,.58fr) 112px;gap:7px;align-items:center;padding:8px 9px;border-bottom:1px solid #edf2f6;font-size:9px;cursor:pointer}#ydesk .pirow:hover{background:#f8fbfe}#ydesk .pirow.selected{background:#eef6ff}#ydesk .trueinput{width:100%;height:32px;border:1px solid #d5e0ea;border-radius:7px;padding:0 7px}
  #ydesk .upload{border:1.5px dashed #b9cada;border-radius:9px;padding:15px;text-align:center;background:#fbfdff}#ydesk .upload h3{font-size:13px;margin:4px 0}#ydesk .upload p{font-size:9px;color:#6d7d90;margin:4px 0 8px}#ydesk .pipeline{display:grid;grid-template-columns:repeat(5,1fr);gap:4px}#ydesk .stage{text-align:center;border-radius:7px;padding:7px 3px;font-size:8px;font-weight:900;background:#edf2f6;color:#617287}#ydesk .stage.done{background:#e9f8ef;color:#167d49}#ydesk .stage.hold{background:#fff2d8;color:#946100}
  #ydesk .legend{display:flex;gap:11px;flex-wrap:wrap;font-size:8px;color:#52667e;padding:8px 0}#ydesk .legend span{display:flex;align-items:center;gap:4px}#ydesk .sw{width:10px;height:10px;border-radius:3px;display:inline-block}#ydesk .sw.g{background:#dff5e8;border:1px solid #9ed7b5}#ydesk .sw.r{background:#ffe5e9;border:1px solid #f2a7b2}#ydesk .sw.b{background:#e6f2ff;border:1px solid #9ac6fb}#ydesk .sw.a{background:#fff1cf;border:1px solid #e8c66d}#ydesk .sw.x{background:#edf1f5;border:1px solid #cfd8e1}
  #ydesk .healthstrip{display:grid;grid-template-columns:repeat(14,minmax(62px,1fr));gap:4px;overflow:auto}#ydesk .hday{border:1px solid #dfe7ef;border-radius:8px;padding:6px 5px;min-width:62px;background:#fff;cursor:pointer}#ydesk .hday.complete{background:#eef9f2;border-color:#b9dfc8}#ydesk .hday.missing{background:#fff0f2;border-color:#efbdc5}#ydesk .hday.current{background:#edf6ff;border-color:#b8d7fb}#ydesk .hday.partial{background:#fff8e8;border-color:#edd39a}#ydesk .hday .wd{font-size:7px;color:#718197;text-transform:uppercase}#ydesk .hday .dt{font-size:9px;font-weight:900}#ydesk .srcdots{display:flex;gap:2px;margin-top:4px}#ydesk .sd{font-size:6px;border-radius:4px;padding:2px 3px;background:#edf1f5;color:#68788b;font-weight:900}#ydesk .sd.ok{background:#dff5e8;color:#17784a}#ydesk .sd.miss{background:#ffe3e8;color:#b42e44}#ydesk .sd.nd{background:#e6f2ff;color:#0b67d5}
  #ydesk .loading{padding:24px;text-align:center;color:var(--muted);font-size:11px}#ydesk .error{padding:10px;border-radius:8px;background:#fff0f2;color:#9d3d4a;font-size:10px}#ydesk .toast{position:fixed;right:18px;bottom:18px;background:#17324f;color:#fff;border-radius:9px;padding:9px 12px;font-size:10px;box-shadow:var(--shadow);opacity:0;transform:translateY(8px);transition:.2s;z-index:90;pointer-events:none}#ydesk .toast.show{opacity:1;transform:translateY(0)}
  /* v7.0.372 desktop scale + denser workstation polish */
  #ydesk .app{grid-template-columns:244px minmax(0,1fr)}
  #ydesk .side{padding:18px 14px}
  #ydesk .brand{padding:3px 9px 16px}#ydesk .brand h1{font-size:29px}#ydesk .brand small{font-size:11.5px;line-height:1.35}
  #ydesk .navbtn{font-size:14.5px!important;padding:12px 13px!important;border-radius:11px}#ydesk .navbtn .ico{width:23px;font-size:18px}
  #ydesk .fresh{padding:11px}#ydesk .fresh h4{font-size:12px}#ydesk .frow{font-size:11px;margin:6px 0}#ydesk .version{font-size:10px;line-height:1.4}
  #ydesk .topbar{height:68px;padding:0 20px;gap:14px}#ydesk .gsearch{height:44px;width:min(760px,50vw);padding:0 14px}#ydesk .gsearch input{font-size:14px}#ydesk .kbd{font-size:10px}
  #ydesk .live{font-size:10px;padding:5px 8px}#ydesk .topstat{font-size:9.5px;min-width:82px;padding:7px 10px}#ydesk .topstat b{font-size:17px}#ydesk .avatar{width:38px;height:38px;font-size:11px}
  #ydesk .work{padding:20px 22px 34px}#ydesk .pagehead{margin-bottom:14px}#ydesk .pagehead h2{font-size:34px}#ydesk .pagehead p{font-size:12.5px;margin-top:6px}
  #ydesk .btn{font-size:11.5px;padding:8px 12px;border-radius:9px}#ydesk .input,#ydesk .select{height:38px;font-size:12.5px;padding:0 10px}
  #ydesk .cardhead{padding:12px 14px}#ydesk .cardhead h3{font-size:14px}#ydesk .cardbody{padding:13px 14px}
  #ydesk .badge{font-size:10px;padding:5px 8px}#ydesk .small{font-size:11.5px}#ydesk .tiny{font-size:10.5px}
  #ydesk .kpis{gap:9px}#ydesk .kpi{padding:9px 10px}#ydesk .kpi label{font-size:9.5px}#ydesk .kpi strong{font-size:20.5px}#ydesk .kpi small{font-size:10.5px}
  #ydesk .tab{font-size:11.5px;padding:7px 10px}
  #ydesk th{font-size:9.5px;padding:9px 10px}#ydesk td{font-size:11.5px;padding:9px 10px}
  #ydesk .split{grid-template-columns:minmax(720px,1.28fr) minmax(470px,.72fr);gap:12px}#ydesk .analysis{top:82px;max-height:none;overflow:visible}
  #ydesk .qtools{gap:8px;margin-bottom:10px}#ydesk .qf{font-size:11.5px;padding:8px 11px}
  #ydesk .flist{gap:8px}#ydesk .fhead{grid-template-columns:26px minmax(210px,1.25fr) repeat(5,minmax(96px,.72fr)) 145px;gap:8px;padding:10px 11px}
  #ydesk .chev{font-size:19px}#ydesk .fname .id{font-size:11.5px}#ydesk .fname .desc{font-size:15.5px}#ydesk .fm label{font-size:8.5px}#ydesk .fm strong{font-size:17px}#ydesk .recent{font-size:9.5px}#ydesk .recent b{font-size:10.5px}
  #ydesk .fbody{padding:10px 11px}#ydesk .recvhead,#ydesk .sap,#ydesk .pairhead,#ydesk .upcrow{font-size:10.5px;padding:8px 9px}
  #ydesk .qhero{padding:13px}#ydesk .qtitle h3{font-size:19px}#ydesk .qtitle p{font-size:10.5px}#ydesk .qstats{gap:7px;margin-top:10px}
  #ydesk .infobox{padding:10px}#ydesk .infobox h4{font-size:11.5px}#ydesk .kv{font-size:10.5px;gap:6px 11px}#ydesk .sectiontitle{font-size:10.5px;margin:12px 0 7px}#ydesk .note{font-size:10.5px;padding:9px 10px}
  #ydesk .event{font-size:10.5px;padding:8px 9px;grid-template-columns:88px 1fr 78px 108px 108px}
  #ydesk .datebox{padding:10px}#ydesk .datebox label{font-size:9px}#ydesk .datebox strong{font-size:17px}#ydesk .day{font-size:9px;padding:6px 3px}#ydesk .day b{font-size:11px}
  #ydesk input.final{width:70px;height:32px;font-size:12px}
  #ydesk .filterbox{padding:10px}#ydesk .filterbox label{font-size:9px}
  #ydesk .perfgrid,#ydesk .pigrid,#ydesk .datagrid{grid-template-columns:minmax(720px,1.35fr) minmax(430px,.65fr);gap:12px}
  #ydesk .insight{font-size:10.5px;padding:9px 10px}
  #ydesk .pirow{font-size:10.5px;padding:10px 11px;grid-template-columns:minmax(210px,1.2fr) repeat(5,.6fr) 120px}
  #ydesk .trueinput{height:36px;font-size:12px}
  #ydesk .upload h3{font-size:14.5px}#ydesk .upload p{font-size:10.5px}
  #ydesk .legend{font-size:9.5px}#ydesk .hday .wd{font-size:8px}#ydesk .hday .dt{font-size:10.5px}
  #ydesk .priceSummary{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin-bottom:9px}
  #ydesk .priceTable{min-width:1120px}#ydesk .priceTable td{vertical-align:middle}#ydesk .priceItem b{font-size:12.5px}#ydesk .priceItem .tiny{margin-top:2px}
  #ydesk .priceMain{font-weight:900;font-size:13.5px}#ydesk .priceTested{color:#087b94;font-weight:900;font-size:13.5px}#ydesk .priceTesting{color:#6a4bd8;font-weight:900;font-size:13.5px}
  #ydesk .reasonTag{display:inline-flex;align-items:center;border-radius:999px;padding:5px 7px;font-size:9.5px;font-weight:900;background:#eef3f8;color:#53677e}
  #ydesk .reasonTag.red{background:#ffe9ed;color:#b82f45}#ydesk .reasonTag.amber{background:#fff4d8;color:#956000}#ydesk .reasonTag.purple{background:#f1edff;color:#6145cb}#ydesk .reasonTag.blue{background:#e8f3ff;color:#0868dc}
  #ydesk .priceEmpty{background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px;box-shadow:var(--shadow)}#ydesk .priceEmpty h3{margin:0 0 6px;font-size:16px}#ydesk .priceEmpty p{font-size:11.5px;color:#66798f;line-height:1.45}
  #ydesk .diaggrid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}
  #ydesk .priceSearch{min-width:220px}
  #ydesk #ydOrderMain table{min-width:1180px}
  #ydesk #ydPerfMain table{min-width:1080px}
  #ydesk #ydPQueue table{min-width:1160px}
  #ydesk #ydOrderMain .tablewrap,#ydesk #ydPerfMain .tablewrap,#ydesk #ydPQueue .tablewrap{scrollbar-gutter:stable}
  @media(max-width:1450px){
    #ydesk .pfilters{grid-template-columns:1fr 1fr}
    #ydesk .pfilters .filterbox:last-child{grid-column:1 / -1}
  }
  @media(max-width:1280px){#ydesk .app{grid-template-columns:72px minmax(0,1fr)}#ydesk .brand h1{font-size:17px}#ydesk .brand small,#ydesk .navbtn span:last-child,#ydesk .fresh,#ydesk .version{display:none}#ydesk .navbtn{justify-content:center}#ydesk .split,#ydesk .perfgrid,#ydesk .pigrid,#ydesk .datagrid{grid-template-columns:1fr}#ydesk .analysis{position:relative;top:auto;max-height:none}#ydesk .fhead{grid-template-columns:24px minmax(180px,1.25fr) repeat(4,minmax(84px,.7fr)) 120px}#ydesk .hide1280{display:none!important}#ydesk .kpis{grid-template-columns:repeat(3,1fr)}}
}
"""

YIPMAN_DESKTOP_JS = r"""
(function(){
 if(!window.__YIPMAN_DESKTOP_ACTIVE__)return;
 const D={mod:'quick',best:[],families:[],inventory:[],prices:[],orderRows:[],orderData:null,perf:null,piGroups:[],health:null,qa:[],ignored:new Set(),pricePrefix:'all',priceOperational:'all',priceReason:'all',priceSearch:'',priceSort:'urgency',priceShowIgnored:false,priceRetry:0,priceMeta:null,quickFilter:'all',quickSearchSeq:0,quickSearchTimer:null,quickSearchQuery:'',delivery:null,next:null,calendar:null,promoLists:[]};
 const ctx=r=>typeof r==='string'?document.querySelector(r):r;
 const $=(s,r=document)=>ctx(r)?.querySelector(s)||null, $$=(s,r=document)=>Array.from(ctx(r)?.querySelectorAll(s)||[]);
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=v=>{if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null};
 const fmt=(v,d=1)=>{const n=num(v);return n===null?'—':n.toLocaleString(undefined,{maximumFractionDigits:d})};
 const money=v=>{const n=num(v);return n===null?'—':'$'+n.toFixed(2)};
 const pct=v=>{let n=num(v);if(n===null)return'—';if(Math.abs(n)<=1.5)n*=100;return n.toFixed(1)+'%'};
 const ymd=d=>d.toISOString().slice(0,10);
 const api=async(url,opt={})=>{const r=await fetch(url,{...opt,cache:'no-store',headers:{'Accept':'application/json',...(opt.headers||{})}});const t=await r.text();let d={};try{d=t?JSON.parse(t):{}}catch{}if(!r.ok)throw new Error(d?.detail?.reason||d?.detail||t||('HTTP '+r.status));return d};
 const toast=t=>{const x=$('#ydToast');if(!x)return;x.textContent=t;x.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>x.classList.remove('show'),2000)};
 const tone=c=>String(c||'').toUpperCase()==='LIVE'?['#ef6f90','#ffedf2']:String(c||'').toUpperCase()==='FRESH'?['#e4b500','#fff6c9']:String(c||'').toUpperCase()==='FROZEN'?['#2f91ec','#eaf5ff']:['#8465e5','#f1edff'];
 const appDate=v=>{const m=String(v||'').match(/^(\d{4})-(\d{2})-(\d{2})/);if(!m)return'—';const d=new Date(Number(m[1]),Number(m[2])-1,Number(m[3]),12);return Number(m[2])+'/'+Number(m[3])+' '+d.toLocaleDateString(undefined,{weekday:'short'})};
 function enableDesktopWheelScroll(){
  const shell=$('#ydesk .shell');
  if(!shell)return;
  // One vertical scroll owner for desktop.  Horizontal table scrolling remains native.
  shell.addEventListener('wheel',e=>{
    if(e.ctrlKey)return;
    const t=e.target;
    const horizontal=t&&t.closest?t.closest('.tablewrap,.healthstrip'):null;
    if(horizontal&&Math.abs(e.deltaX)>Math.abs(e.deltaY))return;
    if(Math.abs(e.deltaY)<=0)return;
    shell.scrollTop+=e.deltaY;
    e.preventDefault();
  },{passive:false});
 }
 function root(){
  const r=document.createElement('div');r.id='ydesk';r.innerHTML='<div class="app"><aside class="side"><div class="brand"><h1>Yip<span>man</span></h1><small>FULL MYSQL · DESKTOP WORKSTATION</small></div><nav class="nav"><button class="navbtn active" data-m="quick"><span class="ico">⌕</span><span>Quick Check</span></button><button class="navbtn" data-m="order"><span class="ico">▤</span><span>Ordering</span></button><button class="navbtn" data-m="price"><span class="ico">$</span><span>Price Suggestions</span></button><button class="navbtn" data-m="performance"><span class="ico">▥</span><span>Performance</span></button><div class="sep"></div><button class="navbtn" data-m="pi"><span class="ico">◎</span><span>PI / True Stock</span></button><button class="navbtn" data-m="data"><span class="ico">▦</span><span>Data Center</span></button></nav><div class="sidefoot"><div class="fresh"><h4>DATA FRESHNESS</h4><div id="ydFresh"><div class="loading">Loading…</div></div></div><div class="version">Store #1032 · Seafood<br>v__VERSION__</div></div></aside><section class="shell"><header class="topbar"><div class="gsearch"><span>⌕</span><input id="ydSearch" placeholder="Search Article / UPC / Receiving / SAP / Name..."><span class="kbd">Ctrl K</span></div><span class="live">LIVE DATA</span><div class="topstats"><div class="topstat">Price actions<b id="ydPc">—</b></div><div class="topstat">Order candidates<b id="ydOc">—</b></div><div class="topstat">QA holds<b id="ydQc">—</b></div></div><div class="avatar">TY</div></header><main class="work"><section class="mod active" id="yd-quick"></section><section class="mod" id="yd-order"></section><section class="mod" id="yd-price"></section><section class="mod" id="yd-performance"></section><section class="mod" id="yd-pi"></section><section class="mod" id="yd-data"></section></main></section></div><div class="toast" id="ydToast"></div>';document.body.appendChild(r);
  $('.navbtn',r).forEach(b=>b.onclick=()=>openMod(b.dataset.m));
  const search=$('#ydSearch');
  const runSearch=()=>{
    const q=search.value.trim();D.quickSearchQuery=q;
    clearTimeout(D.quickSearchTimer);
    if(D.mod!=='quick')openMod('quick');else loadQuick(q);
  };
  search.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();runSearch()}});
  search.addEventListener('input',e=>{clearTimeout(D.quickSearchTimer);const q=e.target.value.trim();D.quickSearchQuery=q;D.quickSearchTimer=setTimeout(()=>{if(q.length===0||q.length>=2){if(D.mod!=='quick')openMod('quick');else loadQuick(q)}},500)});
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();search.focus();search.select()}});
 }
 function openMod(m){D.mod=m;$$('.mod','#ydesk').forEach(x=>x.classList.toggle('active',x.id==='yd-'+m));$$('.navbtn','#ydesk').forEach(x=>x.classList.toggle('active',x.dataset.m===m));if(m==='quick')loadQuick($('#ydSearch').value.trim());if(m==='order')loadOrder();if(m==='price')loadPrice();if(m==='performance')loadPerformance();if(m==='pi')loadPI();if(m==='data')loadData();history.replaceState({yipdesktop:true,view:m},'', '#'+m);window.scrollTo({top:0})}
 async function topStatus(){try{
   const [h,dh,q,p]=await Promise.all([
     api('/v1/backoffice/home-summary'),
     api('/v1/backoffice/data-health?days=14'),
     api('/v1/backoffice/qa-review?limit=300'),
     api('/v1/yipman/pricing-review?category=ALL&limit=1000').catch(()=>null)
   ]);
   const latest=dh.latest||{};
   $('#ydFresh').innerHTML=[['POS',latest.POS],['MVT',latest.MVT],['Price',latest.PRICE],['OH',latest.OH],['L/F/F',latest.LIVE_FRESH||latest.FROZEN]].map(x=>'<div class="frow"><span>'+x[0]+'</span><b>'+(x[1]?.date||'—')+' <i class="fdot '+(x[1]?.date?'':'warn')+'"></i></b></div>').join('');
   const pRows=(p?.rows||[]).filter(x=>x.priority_240_249_mismatch||x.actionable||String(x.suggestion_reason_code||''));
   $('#ydPc').textContent=p? pRows.length : (h?.pricing?.qualified_count??'—');
   $('#ydOc').textContent=h?.ordering?.attention_count??h?.ordering?.family_count??'—';
   D.qa=q.issues||[];$('#ydQc').textContent=D.qa.length;
   if(p&&pRows.length===0&&(p.refreshing||String(p.cache_status||'').includes('STALE')||String(p.cache_status||'')==='WARMING')){
     setTimeout(()=>{if(document.getElementById('ydesk'))topStatus()},3500);
   }
 }catch{}}
 function recHist(r){return Array.isArray(r?.family_receipt_history)?r.family_receipt_history:[]} function recDate(x){return x?.date||x?.receipt_date||''} function recQty(x){return x?.quantity??x?.receipt_qty} function recUom(x){return x?.uom||x?.receipt_uom||''}
 function group(rows){const m=new Map();(rows||[]).forEach(r=>{const id=String(r.family_article||r.family_id||'UNRESOLVED'),g=m.get(id)||{id,name:r.family_name||r.name||'Unresolved Family',cat:r.category||'',rows:[],row:r,rank:0};g.rows.push(r);g.rank=Math.max(g.rank,num(r.family_group_movement_7d)??0,num(r.qty_7d)??0);if(!recHist(g.row).length&&recHist(r).length)g.row=r;m.set(id,g)});return [...m.values()].sort((a,b)=>b.rank-a.rank)}
 async function loadQuick(q=''){
  const root=$('#yd-quick');
  if(!root.dataset.init){
    root.dataset.init='1';
    root.innerHTML='<div class="pagehead"><div><h2>Quick Check</h2><p>Family → Receiving Article → SAP Selling Article → UPC. Desktop keeps receipt, inventory, pricing and trend evidence visible together.</p></div><div class="actions"><button class="btn">Export</button><button class="btn">Columns</button><button class="btn primary">Analysis Workspace</button></div></div><div class="split"><div><div class="qtools"><button class="qf active" data-f="all">Best Sellers</button><button class="qf" data-f="live">Live</button><button class="qf" data-f="fresh">Fresh</button><button class="qf" data-f="frozen">Frozen</button><select class="select" id="ydQSort"><option value="selling">Most selling first</option><option value="doh">Highest DOH</option><option value="oh">Lowest OH</option></select></div><div id="ydFList" class="flist"><div class="loading">Loading current families…</div></div></div><aside id="ydQAnalysis" class="analysis"><div class="card"><div class="loading">Select a Family or UPC</div></div></aside></div>';
    $$('.qf',root).forEach(b=>b.onclick=()=>{$$('.qf',root).forEach(x=>x.classList.remove('active'));b.classList.add('active');D.quickFilter=b.dataset.f;renderFamilies()});
    $('#ydQSort').onchange=renderFamilies;
  }
  const seq=++D.quickSearchSeq;
  const list=$('#ydFList');
  if(q)list.innerHTML='<div class="loading">Searching “'+esc(q)+'”…</div>';
  try{
    if(q){
      // Fast serving-table search first so Enter always responds immediately.
      const fast=await api('/v1/backoffice/inventory?category=ALL&limit=120&lightweight=true&include_price_preview=true&q='+encodeURIComponent(q));
      if(seq!==D.quickSearchSeq)return;
      D.inventory=fast.rows||[];D.families=group(D.inventory);renderFamilies();
      if(D.families[0])selectFamily(D.families[0].id);
      if(!D.families.length){list.innerHTML='<div class="priceEmpty"><h3>No match for “'+esc(q)+'”</h3><p>Search checks Article #, UPC, Receiving/SAP mapping, family name and item description. Typo-tolerant fallback is enabled.</p></div>';return}
      // Enrich the visible search with full current OH / receipt evidence without blocking the first response.
      api('/v1/backoffice/inventory?category=ALL&limit=120&lightweight=false&q='+encodeURIComponent(q)).then(full=>{
        if(seq!==D.quickSearchSeq)return;
        D.inventory=full.rows||D.inventory;D.families=group(D.inventory);renderFamilies();if(D.families[0])selectFamily(D.families[0].id);
      }).catch(()=>{});
    }else{
      const b=await api('/v1/yipman/best-sellers?limit=12');
      if(seq!==D.quickSearchSeq)return;
      D.best=b.rows||[];
      const ids=D.best.map(x=>x.family_article).filter(Boolean).slice(0,12);
      const sets=await Promise.all(ids.map(id=>api('/v1/backoffice/inventory?category=ALL&limit=50&lightweight=false&q='+encodeURIComponent(id)).catch(()=>({rows:[]}))));
      if(seq!==D.quickSearchSeq)return;
      D.inventory=sets.flatMap(x=>x.rows||[]);D.families=group(D.inventory);
      if(!D.families.length)D.families=(D.best||[]).map(x=>({id:String(x.family_article),name:x.family_name,cat:x.category,rows:[],row:x,rank:num(x.family_group_movement_7d)||0}));
      renderFamilies();if(D.families[0])selectFamily(D.families[0].id);
    }
  }catch(e){
    if(seq!==D.quickSearchSeq)return;
    list.innerHTML='<div class="error">'+esc(e.message)+'</div>';
  }
 }
 function renderFamilies(){let a=D.families.slice();if(D.quickFilter!=='all')a=a.filter(g=>String(g.cat).toLowerCase()===D.quickFilter);const s=$('#ydQSort')?.value||'selling';if(s==='doh')a.sort((x,y)=>(num(y.row.doh)??-1)-(num(x.row.doh)??-1));if(s==='oh')a.sort((x,y)=>(num(x.row.family_oh)??1e9)-(num(y.row.family_oh)??1e9));$('#ydFList').innerHTML=a.map((g,i)=>famHtml(g,i)).join('')||'<div class="loading">No matching family.</div>';$$('.fam','#ydFList').forEach(c=>{$('.fhead',c).onclick=()=>{const on=c.classList.toggle('open');$('.chev',c).textContent=on?'⌄':'›';selectFamily(c.dataset.family)};$$('.upcrow',c).forEach(r=>r.onclick=e=>{e.stopPropagation();selectUpc(r.dataset.upc)})})}
 function observed(r){const h=recHist(r).slice(0,12),c={};h.forEach(x=>{const d=new Date(recDate(x)+'T12:00:00');if(isNaN(d))return;const w=d.toLocaleDateString(undefined,{weekday:'short'}).toUpperCase();c[w]=(c[w]||0)+1});return Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,2).map(x=>x[0]).join(' / ')||'—'}
 function famHtml(g,i){const r=g.row,h=recHist(r),h1=h[0],h2=h[1],u=r.family_group_movement_uom||r.family_source_movement_uom||r.family_receipt_7d_uom||r.selling_uom||'',colors=tone(g.cat),rows=g.rows.slice().sort((a,b)=>(num(b.qty_7d)||0)-(num(a.qty_7d)||0)),receiving=r.receiving_article||r.family_source_article||g.id,paired=rows.filter(x=>['240','249'].includes(String(x.upc||'').replace(/^0+/,'').slice(0,3))),pq=paired.reduce((s,x)=>s+(num(x.qty_7d)||0),0);return '<article class="fam '+(i===0?'open':'')+'" data-family="'+esc(g.id)+'" style="--accent:'+colors[0]+';--tint:'+colors[1]+'"><div class="fhead"><div class="chev">'+(i===0?'⌄':'›')+'</div><div class="fname"><div class="id">'+esc(g.id)+' <span class="badge gray">#'+(i+1)+'</span></div><div class="desc">'+esc(g.name)+'</div><div class="tiny">'+esc(String(g.cat||'').toUpperCase())+' · '+rows.length+' linked UPCs</div></div><div class="fm"><label>Family 7D MVT</label><strong>'+fmt(r.family_group_movement_7d??r.family_source_movement_7d)+' '+esc(u)+'</strong><span class="tiny">'+fmt(r.family_group_avg_qty_day??r.family_source_avg_qty_day)+'/day</span></div><div class="fm"><label>7D Receipt</label><strong>'+fmt(r.family_receipt_7d_qty)+' '+esc(r.family_receipt_7d_uom||u)+'</strong><span class="tiny">'+fmt(r.family_receipt_7d_day_count,0)+' receipt day / 7D</span></div><div class="fm"><label>Effective OH</label><strong>'+fmt(r.family_oh)+' '+esc(r.family_oh_uom||u)+'</strong><span class="tiny">'+esc(r.family_oh_status||'current')+'</span></div><div class="fm"><label>DOH</label><strong>'+fmt(r.doh)+'</strong><span class="tiny">days</span></div><div class="fm hide1280"><label>Observed Delivery</label><strong>'+esc(observed(r))+'</strong><span class="tiny">receipt history</span></div><div class="recent"><span class="tiny">RECENT RECEIPTS</span><br><b>'+(h1?esc(appDate(recDate(h1)))+' · '+fmt(recQty(h1))+' '+esc(recUom(h1)):'No recent receipt')+'</b><br>'+(h2?esc(appDate(recDate(h2)))+' · '+fmt(recQty(h2))+' '+esc(recUom(h2)):'—')+'</div></div><div class="fbody"><div class="hier"><div class="recv"><div class="recvhead"><div><b>Receiving Article '+esc(receiving)+'</b><div class="tiny">'+esc(g.name)+'</div></div><div><span class="tiny">Latest</span><br><b>'+(h1?esc(appDate(recDate(h1)))+' · '+fmt(recQty(h1))+' '+esc(recUom(h1)):'—')+'</b></div><div><span class="tiny">Previous</span><br><b>'+(h2?esc(appDate(recDate(h2)))+' · '+fmt(recQty(h2))+' '+esc(recUom(h2)):'—')+'</b></div><div><span class="tiny">Frequency</span><br><b>'+esc(observed(r))+'</b></div><div><span class="tiny">Receipt Cost</span><br><b>'+money(r.cost)+(r.cost_uom?' / '+esc(r.cost_uom):'')+'</b></div></div><div class="sap"><div><b>SAP Selling Article '+esc(r.selling_article||r.article_number||'—')+'</b><div class="tiny">selling article</div></div><div><span class="tiny">7D Selling MVT</span><br><b>'+fmt(r.receiving_movement_7d??r.family_group_movement_7d)+'</b></div><div><span class="tiny">Avg/Day</span><br><b>'+fmt(r.family_group_avg_qty_day)+'</b></div><div><span class="tiny">Current Price</span><br><span class="price">'+money(r.price)+'</span></div><div><span class="tiny">Source</span><br><b>'+esc(r.price_source||'—')+' '+esc(r.price_as_of||'')+'</b></div></div><div class="pair"><div class="pairhead"><b>240 + 249 pair total</b><span>7D Qty <b>'+fmt(pq)+'</b></span><span>Avg/day <b>'+fmt(pq/7)+'</b></span><span>Rule <b>'+pairStatus(rows)+'</b></span><span>Current <b>'+money((paired[0]||r).price)+'</b></span><span>Tested <b>'+money((paired[0]||r).sweet_spot_price)+'</b></span><span>Testing <b>live review</b></span></div>'+rows.map(upcHtml).join('')+'</div></div></div></article>'}
 function pairStatus(rows){const a=rows.find(x=>String(x.upc||'').replace(/^0+/,'').startsWith('240')),b=rows.find(x=>String(x.upc||'').replace(/^0+/,'').startsWith('249'));if(!a||!b)return'N/A';const x=num(a.price),y=num(b.price);return x!==null&&y!==null&&Math.abs(x-y)<.001?'PASS':'CHECK'}
 function upcHtml(r){const p=String(r.upc||'').replace(/^0+/,'').slice(0,3),cl=p==='249'?'service':p==='245'?'package':'';return '<div class="upcrow" data-upc="'+esc(r.upc)+'"><div><span class="prefix '+cl+'">'+esc(p||'UPC')+'</span> <b>'+esc(r.upc||'—')+'</b><div class="tiny">'+esc(r.name||'')+'</div></div><span>'+fmt(r.qty_7d)+' '+esc(r.selling_uom||'')+'</span><span>'+fmt(r.velocity_7d)+'/d</span><span>'+money(r.price)+'</span><span>OH '+fmt(r.family_oh)+'</span><span>Tested '+money(r.sweet_spot_price)+'</span><span>'+esc(r.readiness||'—')+'</span></div>'}
 function selectFamily(id){const g=D.families.find(x=>String(x.id)===String(id));if(g)renderQAnalysis(g,g.rows[0]||g.row)}
 function selectUpc(upc){const r=D.inventory.find(x=>String(x.upc)===String(upc)),g=r&&D.families.find(x=>String(x.id)===String(r.family_article));if(g&&r)renderQAnalysis(g,r)}
 async function renderQAnalysis(g,r){const h=recHist(r),pr=await priceFor(r.upc),receipt=h.slice(0,6).map(x=>'<div class="event"><b>'+esc(appDate(recDate(x)))+'</b><span>'+fmt(recQty(x))+' '+esc(recUom(x))+'</span><span>'+esc(x.movement_type||x.receipt_movement_type||'GR')+'</span><span>'+esc(x.purchase_order||x.po_number||'PO —')+'</span><span>'+esc(x.gr_number||x.document_number||'GR —')+'</span></div>').join('');$('#ydQAnalysis').innerHTML='<div class="card"><div class="qhero"><div class="qtitle"><div><h3>'+esc(g.id)+' · '+esc(g.name)+'</h3><p>Family Article · '+esc(g.cat||'')+' · '+g.rows.length+' linked selling UPCs</p></div><span class="badge '+(String(r.readiness||'').includes('READY')?'green':'amber')+'">'+esc(r.readiness||'CURRENT')+'</span></div><div class="qstats"><div class="kpi"><label>Family 7D MVT</label><strong>'+fmt(r.family_group_movement_7d??r.family_source_movement_7d)+' '+esc(r.family_group_movement_uom||'')+'</strong><small>'+fmt(r.family_group_avg_qty_day)+'/day</small></div><div class="kpi"><label>7D Receipt</label><strong>'+fmt(r.family_receipt_7d_qty)+' '+esc(r.family_receipt_7d_uom||'')+'</strong><small>'+fmt(r.family_receipt_7d_day_count,0)+' day / 7D</small></div><div class="kpi"><label>Effective OH</label><strong>'+fmt(r.family_oh)+' '+esc(r.family_oh_uom||'')+'</strong><small>'+esc(r.family_oh_status||'current')+'</small></div><div class="kpi"><label>DOH</label><strong>'+fmt(r.doh)+'</strong><small>freshness / coverage</small></div></div></div><div class="qtabs tabs">'+['Overview','UPCs','Receipts','Price + GP','Trend','Ordering','Lineage'].map((x,i)=>'<button class="tab '+(i===0?'active':'')+'" data-qt="'+i+'">'+x+'</button>').join('')+'</div><div><div class="qpanel active" data-qp="0"><div class="row2"><div class="infobox"><h4>Identity / Inventory</h4><div class="kv"><span>Family Article</span><span>'+esc(g.id)+'</span><span>Category</span><span>'+esc(g.cat||'—')+'</span><span>Receiving / Ordering #</span><span>'+esc(r.receiving_article||r.family_source_article||g.id)+'</span><span>UPC</span><span>'+esc(r.upc||'—')+'</span><span>System / Effective OH</span><span>'+fmt(r.family_oh)+' '+esc(r.family_oh_uom||'')+'</span><span>DOS</span><span>'+fmt(r.dos)+'</span></div></div><div class="infobox"><h4>Current Economics</h4><div class="kv"><span>Current Price</span><span>'+money(r.price)+'</span><span>Price Source</span><span>'+esc(r.price_source||'—')+'</span><span>Current Cost</span><span>'+money(r.cost)+' '+esc(r.cost_uom||'')+'</span><span>GP%</span><span>'+pct(r.gp_pct)+'</span><span>7D POS Qty</span><span>'+fmt(r.qty_7d)+' '+esc(r.selling_uom||'')+'</span></div></div></div></div><div class="qpanel" data-qp="1"><div class="tablewrap"><table><thead><tr><th>UPC</th><th>Description</th><th>7D Qty</th><th>Velocity</th><th>Current</th><th>Cost</th><th>OH</th><th>Status</th></tr></thead><tbody>'+g.rows.map(x=>'<tr><td><b>'+esc(x.upc||'—')+'</b></td><td>'+esc(x.name||'')+'</td><td>'+fmt(x.qty_7d)+' '+esc(x.selling_uom||'')+'</td><td>'+fmt(x.velocity_7d)+'/d</td><td>'+money(x.price)+'</td><td>'+money(x.cost)+'</td><td>'+fmt(x.family_oh)+' '+esc(x.family_oh_uom||'')+'</td><td>'+esc(x.readiness||'—')+'</td></tr>').join('')+'</tbody></table></div></div><div class="qpanel" data-qp="2"><div class="timeline">'+(receipt||'<div class="loading">No recent receipt details.</div>')+'</div></div><div class="qpanel" data-qp="3"><div class="row3"><div class="kpi"><label>Current</label><strong>'+money(pr?.current_price??r.price)+'</strong><small>'+esc(pr?.current_price_source||r.price_source||'—')+' · '+pct(pr?.current_price_gp_pct??r.gp_pct)+'</small></div><div class="kpi"><label>Tested</label><strong>'+money(pr?.tested_price??r.sweet_spot_price)+'</strong><small>retail aligned · '+pct(pr?.tested_price_gp_pct)+'</small></div><div class="kpi"><label>Testing</label><strong>'+money(pr?.testing_price)+'</strong><small>'+(num(pr?.testing_price)===null?'None active':'controlled test · '+pct(pr?.testing_price_gp_pct))+'</small></div></div><div class="sectiontitle">Cost</div><div class="kv"><span>Current Cost</span><span>'+money(r.cost)+' '+esc(r.cost_uom||r.selling_uom||'')+'</span></div><div class="sectiontitle">Company Prices</div><div class="row3"><div class="kpi"><label>Company A</label><strong>'+money(pr?.company_price_a??r.company_price_a)+'</strong></div><div class="kpi"><label>Company B</label><strong>'+money(pr?.company_price_b??r.company_price_b)+'</strong></div><div class="kpi"><label>Company C</label><strong>'+money(pr?.company_price_c??r.company_price_c)+'</strong></div></div><div class="sectiontitle">GP$/day</div><div class="kv"><span>Current</span><span>'+money(pr?.current_gp_per_day_7d)+'</span><span>Testing / Candidate</span><span>'+money(pr?.candidate_expected_gp_per_day)+'</span></div></div><div class="qpanel" data-qp="4"><div id="ydQTrend" class="loading">Loading 14-day GP$ + Avg Price…</div></div><div class="qpanel" data-qp="5"><div class="note blue">Ordering uses Family / Receiving Article coverage. Select Delivery Date and Next Delivery Date to calculate current usage and suggested quantity.</div><button class="btn primary" data-jump="order" style="margin-top:8px">Open Ordering</button></div><div class="qpanel" data-qp="6"><div class="kv"><span>UPC sold qty</span><span>POS only</span><span>Family movement</span><span>251 − 252</span><span>Receipt event</span><span>101 OR paired 107 + 109</span><span>Current price</span><span>newest Price List / sold event</span><span>OH</span><span>latest snapshot + canonical MVT</span></div></div></div></div>';$$('[data-qt]','#ydQAnalysis').forEach(b=>b.onclick=()=>{$$('[data-qt]','#ydQAnalysis').forEach(x=>x.classList.remove('active'));b.classList.add('active');$$('.qpanel','#ydQAnalysis').forEach(x=>x.classList.toggle('active',x.dataset.qp===b.dataset.qt));if(b.dataset.qt==='4')qTrend(r.upc)});$$('[data-jump]','#ydQAnalysis').forEach(b=>b.onclick=()=>openMod(b.dataset.jump))}
 async function priceFor(upc){if(!D.prices.length)try{const d=await api('/v1/yipman/pricing-review?category=ALL&limit=1000');D.prices=d.rows||[];$('#ydPc').textContent=D.prices.length}catch{}return D.prices.find(x=>String(x.upc)===String(upc))}
 async function qTrend(upc){const box=$('#ydQTrend');if(!box||box.dataset.loaded)return;box.dataset.loaded='1';try{const d=await api('/v1/app/v2/upc/'+encodeURIComponent(upc)+'/price?trend_supported_days=14'),a=d.price_vs_sales_trend?.rows||[],mx=Math.max(1,...a.map(x=>num(x.gp_dollars)||0));box.className='chart';box.innerHTML=a.slice(-14).map(x=>'<div class="bar" title="'+esc((x.date||'')+' · GP '+money(x.gp_dollars)+' · Avg '+money(x.avg_sold_price))+'" style="height:'+Math.max(5,Math.round((num(x.gp_dollars)||0)/mx*150))+'px"><span>'+esc(String(x.date||'').slice(5))+'</span></div>').join('')}catch(e){box.className='error';box.textContent=e.message}}
 async function loadOrder(){
  const root=$('#yd-order');if(!root.dataset.init){root.dataset.init='1';const t=new Date(),d=new Date(t);d.setDate(t.getDate()+((5-t.getDay()+7)%7||7));const n=new Date(d);n.setDate(d.getDate()+4);D.delivery=ymd(d);D.next=ymd(n);root.innerHTML='<div class="pagehead"><div><h2>Ordering</h2><p>Desktop order workstation: coverage window, editable final order, forecast reasoning and receipt evidence together.</p></div><div class="actions"><button class="btn">Export</button><button class="btn primary">Save Notes</button></div></div><div class="tabs" style="margin-bottom:9px"><button class="tab active" data-om="regular">Regular Order</button><button class="tab" data-om="promotion">Promotion Order</button><button class="tab" data-om="history">Delivery History / PO → GR</button></div><div class="split"><div><div class="card"><div class="cardbody"><div class="ordtop"><div class="datebox"><label>Delivery Date</label><input id="ydDel" class="input" type="date" value="'+D.delivery+'" style="width:100%;margin-top:4px"></div><div class="datebox"><label>Next Delivery</label><input id="ydNext" class="input" type="date" value="'+D.next+'" style="width:100%;margin-top:4px"></div><div class="datebox"><label>Coverage Window</label><strong id="ydCover">'+D.delivery+' → '+D.next+'</strong><span class="tiny">Best available OH + POS + receipt/MVT history</span></div></div><div id="ydCal"></div></div></div><div id="ydOrderMain" style="margin-top:9px"><div class="loading">Loading suggestions…</div></div></div><aside id="ydOrderAnalysis" class="analysis"><div class="card"><div class="loading">Select an order candidate.</div></div></aside></div>';$$('[data-om]',root).forEach(b=>b.onclick=()=>{$$('[data-om]',root).forEach(x=>x.classList.remove('active'));b.classList.add('active');renderOrderMode(b.dataset.om)});['ydDel','ydNext'].forEach(id=>$('#'+id).onchange=()=>{D.delivery=$('#ydDel').value;D.next=$('#ydNext').value;$('#ydCover').textContent=D.delivery+' → '+D.next;drawCal();renderOrderMode($('.tab.active',root).dataset.om)});drawCal()}
  renderOrderMode($('.tab.active',root).dataset.om)
 }
 async function loadCalendar(){if(D.calendar)return;try{D.calendar=await api('/v1/yipman/ordering-calendar?lookback_days=180');if(D.calendar.default_delivery_date)D.delivery=D.calendar.default_delivery_date;if(D.calendar.default_next_delivery_date)D.next=D.calendar.default_next_delivery_date}catch{D.calendar={rows:[]}}}
 function drawCal(){const s=new Date();s.setHours(12,0,0,0);s.setDate(s.getDate()-7);let h='<div class="calendar">';for(let i=0;i<14;i++){const d=new Date(s);d.setDate(s.getDate()+i);const iso=ymd(d),wd=d.toLocaleDateString(undefined,{weekday:'short'}).toUpperCase();let c='day';if([2,5,6].includes(d.getDay()))c+=' obs';if(iso===D.delivery)c+=' sel';if(iso===D.next)c+=' next';h+='<div class="'+c+'"><span>'+wd+'</span><b>'+d.getDate()+'</b></div>'}$('#ydCal').innerHTML=h+'</div>'}
 async function renderOrderMode(mode){await loadCalendar();if($('#ydDel')){$('#ydDel').value=D.delivery;$('#ydNext').value=D.next;$('#ydCover').textContent=D.delivery+' → '+D.next;drawCal()}if(mode==='regular')return regularOrders();if(mode==='promotion')return promoOrders();return historyOrders()}
 async function regularOrders(){const box=$('#ydOrderMain');box.innerHTML='<div class="loading">Calculating family order coverage…</div>';try{const d=await api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(D.delivery)+'&next_delivery_date='+encodeURIComponent(D.next));D.orderData=d;D.orderRows=d.rows||[];$('#ydOc').textContent=D.orderRows.length;box.innerHTML='<div class="card"><div class="cardhead"><h3>Coming Delivery Suggestions</h3><span class="badge blue">'+esc(d.analysis_status||'CURRENT')+'</span></div><div class="tablewrap"><table><thead><tr><th>Family / Receiving</th><th>Category</th><th>OH</th><th>7D MVT</th><th>28D Velocity</th><th>Last Receipt</th><th>Predicted Use</th><th>Suggested</th><th>Final Order</th><th>Reason</th></tr></thead><tbody>'+D.orderRows.map(oRow).join('')+'</tbody></table></div></div>';$$('.orow',box).forEach(tr=>tr.onclick=e=>{if(e.target.matches('input'))return;$$('.orow',box).forEach(x=>x.classList.remove('selected'));tr.classList.add('selected');orderAnalysis(tr.dataset.family)});if(D.orderRows[0])orderAnalysis(D.orderRows[0].family_article)}catch(e){box.innerHTML='<div class="error">'+esc(e.message)+'</div>'}}
 function oRow(r){const x=r.details||{};return '<tr class="pick orow" data-family="'+esc(r.family_article)+'"><td><b>'+esc(r.family_name||'—')+'</b><div class="tiny">Family '+esc(r.family_article)+' · Receiving '+esc(r.receiving_article||'—')+'</div></td><td><span class="badge '+(String(r.category).toUpperCase()==='LIVE'?'amber':String(r.category).toUpperCase()==='FRESH'?'green':'blue')+'">'+esc(r.category||'—')+'</span></td><td>'+fmt(r.oh)+' '+esc(r.oh_uom||'')+'</td><td>'+fmt(x.qty_7d)+'</td><td>'+fmt(x.velocity_28d??x.velocity_7d)+'/d</td><td>'+esc(r.last_receipt_date||'—')+' · '+fmt(r.last_receipt_qty_base)+' '+esc(r.last_receipt_base_uom||'')+'</td><td>'+fmt(x.predicted_use??x.expected_usage)+'</td><td><b style="color:#0764d8">'+fmt(r.suggested_delivery_qty)+' '+esc(r.suggested_delivery_uom||'')+'</b></td><td><input class="final" value="'+fmt(r.suggested_delivery_qty,0)+'"></td><td><span class="badge '+(r.attention?'red':'amber')+'">'+(r.attention?'ATTENTION':'COVERAGE')+'</span></td></tr>'}
 function orderAnalysis(fam){const r=D.orderRows.find(x=>String(x.family_article)===String(fam));if(!r)return;const x=r.details||{},reasons=x.reasons||[];$('#ydOrderAnalysis').innerHTML='<div class="card"><div class="cardhead"><div><h3>'+esc(r.family_name||'Family')+'</h3><div class="tiny">Family '+esc(r.family_article)+' · Receiving '+esc(r.receiving_article||'—')+'</div></div><span class="badge '+(r.attention?'red':'green')+'">'+(r.attention?'URGENT':'REVIEW')+'</span></div><div class="cardbody"><div class="row3"><div class="kpi"><label>Effective OH</label><strong>'+fmt(r.oh)+' '+esc(r.oh_uom||'')+'</strong></div><div class="kpi"><label>Predicted Use</label><strong>'+fmt(x.predicted_use??x.expected_usage??x.qty_7d)+'</strong></div><div class="kpi"><label>Suggested</label><strong>'+fmt(r.suggested_delivery_qty)+' '+esc(r.suggested_delivery_uom||'')+'</strong></div></div><div class="sectiontitle">Demand / Inventory</div><div class="kv"><span>7D Family MVT</span><span>'+fmt(x.qty_7d)+'</span><span>28D Family MVT</span><span>'+fmt(x.qty_28d)+'</span><span>7D Velocity</span><span>'+fmt(x.velocity_7d)+'/day</span><span>DOS</span><span>'+fmt(x.dos)+'</span><span>Last receipt</span><span>'+esc(r.last_receipt_date||'—')+' · '+fmt(r.last_receipt_qty_base)+' '+esc(r.last_receipt_base_uom||'')+'</span><span>Observed cadence</span><span>'+esc(r.ordering_frequency||'—')+'</span><span>Coverage window</span><span>'+esc(D.delivery)+' → '+esc(D.next)+'</span></div><div class="sectiontitle">Why this quantity?</div>'+(reasons.length?reasons.map(z=>'<div class="note blue" style="margin-bottom:5px"><b>'+esc(z.title||'Reason')+'</b><br>'+esc(z.detail||'')+'</div>').join(''):'<div class="note blue">Best available Family movement, OH, receipt cadence and selected coverage window.</div>')+'</div></div>'}
 async function promoOrders(){const box=$('#ydOrderMain');box.innerHTML='<div class="loading">Loading promotion lists…</div>';try{const d=await api('/v1/yipman/promotion-lists?limit=30');D.promoLists=d.rows||d.lists||[];box.innerHTML='<div class="card"><div class="cardhead"><h3>Promotion Ordering</h3><span class="badge purple">WEEKLY + WEEKEND</span></div><div class="cardbody"><div class="row2"><div><div class="tiny">PROMOTION LIST</div><select class="select" id="ydPromo" style="width:100%;margin-top:4px">'+D.promoLists.map(x=>'<option value="'+esc(x.list_id||x.id)+'">'+esc(x.list_name||x.name||('List #'+(x.list_id||x.id)))+'</option>').join('')+'</select></div><div><div class="tiny">TEMPORARY TRUE STOCK</div><div class="note amber" style="margin-top:4px">Promotion only. Regular Order continues to use system/current inventory.</div></div></div><button class="btn primary" id="ydPromoCalc" style="margin-top:9px">Calculate Promotion Forecast</button><div id="ydPromoOut"></div></div></div>';$('#ydPromoCalc').onclick=calcPromo}catch(e){box.innerHTML='<div class="error">'+esc(e.message)+'</div>'}}
 async function calcPromo(){const out=$('#ydPromoOut');out.innerHTML='<div class="loading">Calculating…</div>';try{const d=await api('/v1/yipman/promotion-ordering/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({list_id:Number($('#ydPromo').value),delivery_date:D.delivery,next_delivery_date:D.next,temporary_oh_overrides:{}})}),a=d.rows||d.items||[];out.innerHTML='<div class="tablewrap" style="margin-top:10px"><table><thead><tr><th>Item</th><th>Promo Type</th><th>Predicted Use</th><th>System OH</th><th>Suggested</th></tr></thead><tbody>'+a.map(x=>'<tr><td><b>'+esc(x.family_name||x.item_name||x.upc||'—')+'</b></td><td>'+esc(x.promotion_type||x.promo_type||'—')+'</td><td>'+fmt(x.predicted_usage||x.forecast_usage)+'</td><td>'+fmt(x.current_oh||x.system_oh)+' '+esc(x.uom||x.order_uom||'')+'</td><td><b>'+fmt(x.suggested_qty||x.suggested_order_qty)+' '+esc(x.uom||x.order_uom||'')+'</b></td></tr>').join('')+'</tbody></table></div>'}catch(e){out.innerHTML='<div class="error">'+esc(e.message)+'</div>'}}
 async function historyOrders(){const box=$('#ydOrderMain');box.innerHTML='<div class="card"><div class="cardbody"><div class="actions"><label class="tiny">PAST DELIVERY DATE</label><input id="ydHistDate" class="input" type="date"><button id="ydHistRun" class="btn primary">Load Actual Receipts</button></div><div id="ydHistOut" style="margin-top:9px"></div></div></div>';$('#ydHistRun').onclick=async()=>{const o=$('#ydHistOut'),d=$('#ydHistDate').value;if(!d)return;o.innerHTML='<div class="loading">Loading receipt events…</div>';try{const x=await api('/v1/yipman/ordering-review?category=ALL&delivery_date='+encodeURIComponent(d)),a=x.rows||[];o.innerHTML='<div class="tablewrap"><table><thead><tr><th>Family / Receiving</th><th>Receipt</th><th>UOM</th><th>Events</th></tr></thead><tbody>'+a.map(r=>'<tr><td><b>'+esc(r.family_name||r.family_article)+'</b><div class="tiny">Receiving '+esc(r.receiving_article||'—')+'</div></td><td>'+fmt(r.receipt_qty)+'</td><td>'+esc(r.receipt_uom||'—')+'</td><td>'+fmt(r.receipt_event_count,0)+'</td></tr>').join('')+'</tbody></table></div>'}catch(e){o.innerHTML='<div class="error">'+esc(e.message)+'</div>'}}}
 async function loadPrice(force=false){
  const root=$('#yd-price');
  if(!root.dataset.init){
    root.dataset.init='1';
    root.innerHTML='<div class="pagehead"><div><h2>Price Suggestions</h2><p>Current price integrity + freshness velocity + GP$/day + strongest proved Tested price + controlled Testing price.</p></div><div class="actions"><span class="badge red" id="ydPActions">— actionable</span><button class="btn" id="ydPShowIgnored">Show ignored</button><button class="btn" id="ydPRefresh">Refresh analysis</button><button class="btn">Export</button></div></div>'+
      '<div class="pfilters">'+
        '<div class="filterbox"><label>UPC / RULE</label><div class="actions"><button class="btn primary" data-pfx="all">All UPC</button>'+['240','245','247','249'].map(x=>'<button class="btn" data-pfx="'+x+'">'+x+'</button>').join('')+'</div></div>'+
        '<div class="filterbox"><label>OPERATIONAL GROUP</label><div class="actions"><button class="btn primary" data-pop="all">All actionable</button><button class="btn" data-pop="live">Live</button><button class="btn" data-pop="tue">Observed Tuesday</button><button class="btn" data-pop="fri">Observed Friday / Sat</button></div></div>'+
        '<div class="filterbox"><label>REASON</label><div class="actions"><button class="btn primary" data-pr="all">All</button><button class="btn" data-pr="pair">240 ≠ 249</button><button class="btn" data-pr="velocity">Velocity / Freshness</button><button class="btn" data-pr="sweet">Sweet spot</button><button class="btn" data-pr="range">Outside range</button><button class="btn" data-pr="gp">GP$/day</button></div></div>'+
      '</div>'+
      '<div class="actions stickyTools" style="margin:0 0 9px"><input id="ydPSearch" class="input priceSearch" placeholder="Search price suggestions by UPC / name / family"><select id="ydPSort" class="select"><option value="urgency">Sort: Urgency first</option><option value="gp_lift">Sort: GP$/day opportunity</option><option value="doh">Sort: Highest DOH</option><option value="oh">Sort: Highest OH</option><option value="velocity_low">Sort: Lowest 7D velocity</option><option value="gap">Sort: Largest price gap</option><option value="name">Sort: Name A–Z</option></select><span class="small" id="ydPStatus">Loading current analysis…</span></div>'+
      '<div id="ydPriceSummary" class="priceSummary"></div>'+
      '<div class="split"><div id="ydPQueue"><div class="loading">Loading pricing review…</div></div><aside id="ydPAnalysis" class="analysis"><div class="card"><div class="loading">Select a price suggestion.</div></div></aside></div>';
    $('[data-pfx]',root).forEach(b=>b.onclick=()=>{D.pricePrefix=b.dataset.pfx;$('[data-pfx]',root).forEach(x=>x.classList.remove('primary'));b.classList.add('primary');renderPriceQueue()});
    $('[data-pop]',root).forEach(b=>b.onclick=()=>{D.priceOperational=b.dataset.pop;$('[data-pop]',root).forEach(x=>x.classList.remove('primary'));b.classList.add('primary');renderPriceQueue()});
    $('[data-pr]',root).forEach(b=>b.onclick=()=>{D.priceReason=b.dataset.pr;$('[data-pr]',root).forEach(x=>x.classList.remove('primary'));b.classList.add('primary');renderPriceQueue()});
    $('#ydPSearch').oninput=e=>{D.priceSearch=e.target.value.trim().toLowerCase();renderPriceQueue()};
    $('#ydPSort').value=D.priceSort||'urgency';
    $('#ydPSort').onchange=e=>{D.priceSort=e.target.value||'urgency';renderPriceQueue()};
    $('#ydPShowIgnored').onclick=()=>{D.priceShowIgnored=!D.priceShowIgnored;$('#ydPShowIgnored').textContent=D.priceShowIgnored?'Hide ignored':'Show ignored';renderPriceQueue()};
    $('#ydPRefresh').onclick=()=>{D.priceRetry=0;refreshPriceData(true,0)};
  }
  if(force||!D.priceMeta) await refreshPriceData(force,0); else renderPriceQueue();
}
function priceIgnoreMap(){
  try{
    const raw=JSON.parse(localStorage.getItem('yipman_price_ignore_v374')||'{}'),now=Date.now(),out={};
    Object.entries(raw).forEach(([k,v])=>{if(Number(v)>now)out[k]=Number(v)});
    localStorage.setItem('yipman_price_ignore_v374',JSON.stringify(out));
    return out;
  }catch{return {}}
}
function priceIsIgnored(upc){return Number(priceIgnoreMap()[String(upc)]||0)>Date.now()}
function ignorePrice12h(upc){
  const m=priceIgnoreMap();m[String(upc)]=Date.now()+12*60*60*1000;
  localStorage.setItem('yipman_price_ignore_v374',JSON.stringify(m));
}
function clearPriceIgnore(upc){const m=priceIgnoreMap();delete m[String(upc)];localStorage.setItem('yipman_price_ignore_v374',JSON.stringify(m))}
async function refreshPriceData(force=false,attempt=0){
  const q=$('#ydPQueue');if(q)q.innerHTML='<div class="loading">'+(attempt?'Refreshing price evidence…':'Loading current Price Suggestions…')+'</div>';
  try{
    const d=await api('/v1/yipman/pricing-review?category=ALL&limit=1000'+(force?'&force=true':''));
    D.priceMeta=d;
    const raw=d.rows||[];
    const meaningful=raw.filter(r=>r.priority_240_249_mismatch||r.actionable||String(r.suggestion_reason_code||''));
    D.prices=meaningful;
    $('#ydPc').textContent=meaningful.length;
    $('#ydPActions').textContent=meaningful.length+' actionable';
    const h=d.data_health||{},status=String(d.analysis_status||'READY'),cache=String(d.cache_status||'');
    $('#ydPStatus').textContent=(h.status||status)+' · POS '+(h.pos_data_through||'—')+' · MVT '+(h.movement_data_through||'—')+(cache?' · '+cache:'');
    renderPriceSummary();
    if(meaningful.length){
      D.priceRetry=0;renderPriceQueue();return;
    }
    const accepted=Number(d.suppressed_accepted_count||0);
    const shouldRetry=attempt<4&&(d.refreshing||cache==='WARMING'||cache==='STALE_REFRESHING'||attempt===0);
    if(shouldRetry){
      renderPriceQueue(true);
      if(attempt===0&&!force){try{await api('/v1/yipman/pricing-review?category=ALL&limit=1000&force=true')}catch{}}
      setTimeout(()=>{if(D.mod==='price')refreshPriceData(false,attempt+1)},1800+attempt*900);
      return;
    }
    renderPriceQueue(false);
    if(accepted>0)$('#ydPStatus').textContent+=' · '+accepted+' accepted suggestions hidden';
  }catch(e){
    D.priceMeta={refresh_error:e.message};
    renderPriceSummary();
    if(q)q.innerHTML='<div class="priceEmpty"><h3>Price analysis temporarily unavailable</h3><p>'+esc(e.message)+'</p><button class="btn primary" id="ydPriceRetryNow">Retry now</button></div>';
    const b=$('#ydPriceRetryNow');if(b)b.onclick=()=>refreshPriceData(true,0);
  }
}
function prefix(r){return String(r.upc||'').replace(/\D/g,'').replace(/^0+/,'').slice(0,3)}
function priceReasonMatch(r){
  const code=String(r.suggestion_reason_code||'').toUpperCase();
  if(D.priceReason==='pair')return r.priority_240_249_mismatch||code==='PAIR_FIX';
  if(D.priceReason==='velocity')return code==='VELOCITY_TEST';
  if(D.priceReason==='sweet')return code==='SWEET_SPOT_GAP';
  if(D.priceReason==='range')return code==='COMPANY_RANGE'||r.company_range_violation;
  if(D.priceReason==='gp')return code==='GP_DOLLAR_TEST';
  return true;
}
function priceGpOpportunity(r){
  const direct=num(r.gp_per_day_opportunity);
  if(direct!==null)return direct;
  const a=num(r.candidate_expected_gp_per_day),b=num(r.current_gp_per_day_7d);
  return a!==null&&b!==null?a-b:0;
}
function priceUrgencyScore(r){
  const code=String(r.suggestion_reason_code||'').toUpperCase();
  let score=(
    (r.priority_240_249_mismatch||code==='PAIR_FIX')?1000:
    (r.company_range_violation||code==='COMPANY_RANGE')?900:
    code==='VELOCITY_TEST'?800:
    code==='SWEET_SPOT_GAP'?650:
    code==='GP_DOLLAR_TEST'?550:300
  );
  const cat=String(r.category||'').toUpperCase(),d=num(r.doh),v7=num(r.velocity_7d),v28=num(r.velocity_28d);
  if(d!==null){
    if(cat==='LIVE'||cat==='FRESH'){
      if(d>=10)score+=250;else if(d>=8)score+=180;else if(d>=5)score+=100;
    }else if(cat==='FROZEN'){
      if(d>=90)score+=180;else if(d>=60)score+=100;
    }
  }
  if(v28!==null&&v28>0&&v7!==null){
    const ratio=v7/v28;
    if(ratio<.5)score+=120;else if(ratio<.8)score+=60;
  }
  const gp=priceGpOpportunity(r);if(gp>0)score+=Math.min(120,gp*4);
  const gap=num(r.price_gap_pct);if(gap!==null)score+=Math.min(80,gap*2);
  return score;
}
function priceUrgencyMeta(r){
  const s=priceUrgencyScore(r);
  if(s>=950)return {score:s,label:'CRITICAL',cls:'red'};
  if(s>=750)return {score:s,label:'HIGH',cls:'amber'};
  if(s>=550)return {score:s,label:'MEDIUM',cls:'purple'};
  return {score:s,label:'REVIEW',cls:'blue'};
}
function sortPriceRows(a){
  const mode=D.priceSort||'urgency';
  const n=(r,k,fallback)=>{const v=num(r[k]);return v===null?fallback:v};
  if(mode==='urgency')a.sort((x,y)=>priceUrgencyScore(y)-priceUrgencyScore(x)||(n(y,'doh',-1)-n(x,'doh',-1))||(priceGpOpportunity(y)-priceGpOpportunity(x)));
  else if(mode==='gp_lift')a.sort((x,y)=>priceGpOpportunity(y)-priceGpOpportunity(x)||priceUrgencyScore(y)-priceUrgencyScore(x));
  else if(mode==='doh')a.sort((x,y)=>n(y,'doh',-1)-n(x,'doh',-1)||priceUrgencyScore(y)-priceUrgencyScore(x));
  else if(mode==='oh')a.sort((x,y)=>n(y,'current_oh',-1)-n(x,'current_oh',-1)||priceUrgencyScore(y)-priceUrgencyScore(x));
  else if(mode==='velocity_low')a.sort((x,y)=>n(x,'velocity_7d',1e12)-n(y,'velocity_7d',1e12)||priceUrgencyScore(y)-priceUrgencyScore(x));
  else if(mode==='gap')a.sort((x,y)=>n(y,'price_gap_pct',-1)-n(x,'price_gap_pct',-1)||priceUrgencyScore(y)-priceUrgencyScore(x));
  else if(mode==='name')a.sort((x,y)=>String(x.name||'').localeCompare(String(y.name||'')));
  return a;
}
function pfRows(){
  const rows=D.prices.filter(r=>{
    const ignored=priceIsIgnored(r.upc);
    if(ignored&&!D.priceShowIgnored)return false;
    if(!priceReasonMatch(r))return false;
    if(D.priceSearch&&!([r.upc,r.name,r.family_article_number,r.family_name].join(' ').toLowerCase().includes(D.priceSearch)))return false;
    if(['240','245','247','249'].includes(D.pricePrefix)&&prefix(r)!==D.pricePrefix)return false;
    if(D.priceOperational==='live'&&String(r.category||'').toUpperCase()!=='LIVE')return false;
    const days=(r.observed_delivery_weekdays||[]).map(x=>String(x).toUpperCase());
    if(D.priceOperational==='tue'&&!days.includes('TUESDAY'))return false;
    if(D.priceOperational==='fri'&&!days.includes('FRIDAY')&&!days.includes('SATURDAY'))return false;
    return true;
  });
  return sortPriceRows(rows).slice(0,120);
}
function renderPriceSummary(){
  const rows=D.prices||[],count=code=>rows.filter(r=>String(r.suggestion_reason_code||'').toUpperCase()===code).length;
  const pair=rows.filter(r=>r.priority_240_249_mismatch||String(r.suggestion_reason_code||'').toUpperCase()==='PAIR_FIX').length;
  const lift=rows.reduce((s,r)=>{const a=num(r.candidate_expected_gp_per_day),b=num(r.current_gp_per_day_7d);return s+(a!==null&&b!==null&&a>b?a-b:0)},0);
  const box=$('#ydPriceSummary');if(!box)return;
  box.innerHTML='<div class="kpi"><label>Actionable</label><strong>'+rows.length+'</strong><small>current queue</small></div>'+
    '<div class="kpi"><label>240 ≠ 249</label><strong>'+pair+'</strong><small>mandatory integrity</small></div>'+
    '<div class="kpi"><label>Velocity tests</label><strong>'+count('VELOCITY_TEST')+'</strong><small>freshness control</small></div>'+
    '<div class="kpi"><label>Sweet spot gap</label><strong>'+count('SWEET_SPOT_GAP')+'</strong><small>> $0.25 from Tested</small></div>'+
    '<div class="kpi"><label>Company range</label><strong>'+count('COMPANY_RANGE')+'</strong><small>outside A/B/C range</small></div>'+
    '<div class="kpi"><label>Est. GP$/day lift</label><strong>'+money(lift)+'</strong><small>supported candidates</small></div>';
}
function reasonMeta(r){
  const code=String(r.suggestion_reason_code||'').toUpperCase();
  if(r.priority_240_249_mismatch||code==='PAIR_FIX')return ['240 ≠ 249','red'];
  if(code==='COMPANY_RANGE')return ['Outside range','red'];
  if(code==='VELOCITY_TEST')return ['Velocity / freshness','blue'];
  if(code==='SWEET_SPOT_GAP')return ['Sweet spot','amber'];
  if(code==='GP_DOLLAR_TEST')return ['GP$/day','purple'];
  return ['Review','blue'];
}
function renderPriceQueue(refreshing=false){
  const a=pfRows(),box=$('#ydPQueue');if(!box)return;
  if(!a.length){
    const d=D.priceMeta||{},h=d.data_health||{},accepted=Number(d.suppressed_accepted_count||0);
    box.innerHTML='<div class="priceEmpty"><h3>'+(refreshing?'Rebuilding current Price Suggestions…':'No actionable suggestion matches the current filters')+'</h3>'+
      '<p>'+(refreshing?'The pricing cache is refreshing automatically. This page will update without a manual reload.':accepted&&!(D.prices||[]).length?'All current matching suggestions are accepted/hidden until price evidence changes.':'Try All actionable, clear the search, or refresh the analysis. If the queue is truly empty, the diagnostics below show why.')+'</p>'+
      '<div class="diaggrid"><div class="kpi"><label>Analysis</label><strong>'+esc(d.analysis_status||'—')+'</strong></div><div class="kpi"><label>Data health</label><strong>'+esc(h.status||'—')+'</strong><small>POS '+esc(h.pos_data_through||'—')+' · MVT '+esc(h.movement_data_through||'—')+'</small></div><div class="kpi"><label>Accepted hidden</label><strong>'+accepted+'</strong><small>'+esc(d.refresh_error||'no refresh error')+'</small></div></div>'+
      '<div class="actions" style="margin-top:10px"><button class="btn primary" id="ydPriceEmptyRefresh">Refresh analysis</button><button class="btn" id="ydPriceEmptyAll">Show all actionable</button></div></div>';
    const r=$('#ydPriceEmptyRefresh');if(r)r.onclick=()=>refreshPriceData(true,0);
    const all=$('#ydPriceEmptyAll');if(all)all.onclick=()=>{D.pricePrefix='all';D.priceOperational='all';D.priceReason='all';D.priceSearch='';$('#ydPSearch').value='';$('[data-pfx]').forEach(x=>x.classList.toggle('primary',x.dataset.pfx==='all'));$('[data-pop]').forEach(x=>x.classList.toggle('primary',x.dataset.pop==='all'));$('[data-pr]').forEach(x=>x.classList.toggle('primary',x.dataset.pr==='all'));renderPriceQueue()};
    $('#ydPAnalysis').innerHTML='<div class="card"><div class="loading">Select a price suggestion when the queue is available.</div></div>';
    return;
  }
  box.innerHTML='<div class="card"><div class="cardhead"><h3>Price Action Queue</h3><span class="badge blue">Showing '+a.length+' of '+D.prices.length+'</span></div><div class="tablewrap"><table class="priceTable"><thead><tr><th>#</th><th>Article / UPC</th><th>Current</th><th>Tested</th><th>Testing</th><th>OH</th><th>DOH</th><th>7D Vel</th><th>28D Vel</th><th>GP$/day</th><th>Urgency</th><th>Reason</th><th>Action</th></tr></thead><tbody>'+
    a.map((r,i)=>{const m=reasonMeta(r),u=priceUrgencyMeta(r),ignored=priceIsIgnored(r.upc);return '<tr class="pick priceRow '+(ignored?'ignored':'')+'" data-upc="'+esc(r.upc)+'"><td>'+(i+1)+'</td><td class="priceItem"><b>'+esc(r.name||r.upc)+'</b><div class="tiny">'+esc(r.upc)+' · '+esc(r.family_article_number||r.family_name||'')+'</div></td><td><span class="priceMain">'+money(r.current_price)+'</span><div class="tiny">'+esc(r.current_price_type||r.current_price_source||'')+'</div></td><td><span class="priceTested">'+money(r.tested_price)+'</span><div class="tiny">'+pct(r.tested_price_gp_pct)+'</div></td><td><span class="priceTesting">'+money(r.testing_price)+'</span><div class="tiny">'+(num(r.testing_price)===null?'None active':pct(r.testing_price_gp_pct))+'</div></td><td><b>'+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+'</b></td><td>'+fmt(r.doh)+'</td><td>'+fmt(r.velocity_7d)+'/d</td><td>'+fmt(r.velocity_28d)+'/d</td><td><b>'+money(r.current_gp_per_day_7d)+'</b></td><td><span class="reasonTag '+u.cls+'">'+u.label+'</span><div class="tiny">score '+Math.round(u.score)+'</div></td><td><span class="reasonTag '+m[1]+'">'+esc(m[0])+'</span></td><td><button class="btn priceReviewBtn" data-review="'+esc(r.upc)+'">'+(ignored?'Restore':'Review')+'</button></td></tr>'}).join('')+
    '</tbody></table></div></div>';
  $$('.priceRow',box).forEach(tr=>tr.onclick=e=>{if(e.target.closest('button'))return;$$('.priceRow',box).forEach(x=>x.classList.remove('selected'));tr.classList.add('selected');selectPrice(tr.dataset.upc)});
  $$('.priceReviewBtn',box).forEach(b=>b.onclick=e=>{e.stopPropagation();const upc=b.dataset.review;if(priceIsIgnored(upc)){clearPriceIgnore(upc);renderPriceQueue()}else selectPrice(upc)});
  const first=a.find(r=>!priceIsIgnored(r.upc))||a[0];if(first)selectPrice(first.upc);
}
async function selectPrice(upc){
  const r=D.prices.find(x=>String(x.upc)===String(upc));if(!r)return;
  const meta=reasonMeta(r),lift=(num(r.candidate_expected_gp_per_day)!==null&&num(r.current_gp_per_day_7d)!==null)?num(r.candidate_expected_gp_per_day)-num(r.current_gp_per_day_7d):null;
  const companyRange=(num(r.company_range_low)!==null&&num(r.company_range_high)!==null)?money(r.company_range_low)+' – '+money(r.company_range_high):'—';
  $('#ydPAnalysis').innerHTML='<div class="card"><div class="cardhead"><div><h3>'+esc(r.name||'Price Analysis')+'</h3><div class="tiny">UPC '+esc(r.upc)+' · Family '+esc(r.family_article_number||r.family_name||'—')+' · '+esc(r.category||'')+'</div></div><span class="reasonTag '+meta[1]+'">'+esc(meta[0])+'</span></div>'+
    '<div class="cardbody">'+
      '<div class="row3"><div class="kpi"><label>Current Price</label><strong>'+money(r.current_price)+'</strong><small>'+esc(r.current_price_type||r.current_price_source||'—')+' · '+pct(r.current_price_gp_pct)+'</small></div><div class="kpi"><label>Tested Price</label><strong style="color:#087b94">'+money(r.tested_price)+'</strong><small>strongest proved · '+pct(r.tested_price_gp_pct)+'</small></div><div class="kpi"><label>Testing Price</label><strong style="color:#6a4bd8">'+money(r.testing_price)+'</strong><small>'+(num(r.testing_price)===null?'None active':'controlled step · '+pct(r.testing_price_gp_pct))+'</small></div></div>'+
      '<div class="row3" style="margin-top:8px"><div class="kpi"><label>Effective OH</label><strong>'+fmt(r.current_oh)+' '+esc(r.current_oh_uom||'')+'</strong><small>current stock evidence</small></div><div class="kpi"><label>DOH</label><strong>'+fmt(r.doh)+'</strong><small>freshness / coverage</small></div><div class="kpi"><label>GP$/day</label><strong>'+money(r.current_gp_per_day_7d)+'</strong><small>'+(lift!==null?(lift>=0?'+':'')+money(lift)+' candidate lift':'candidate lift —')+'</small></div></div>'+
      '<div class="sectiontitle">Demand & Test Progress</div><div class="row3"><div class="kpi"><label>7D Velocity</label><strong>'+fmt(r.velocity_7d)+'/day</strong><small>'+fmt(r.qty_7d)+' '+esc(r.qty_uom||r.selling_uom||'')+' sold</small></div><div class="kpi"><label>14D Velocity</label><strong>'+fmt(r.velocity_14d)+'/day</strong><small>'+fmt(r.qty_14d)+' sold</small></div><div class="kpi"><label>28D Velocity</label><strong>'+fmt(r.velocity_28d)+'/day</strong><small>'+fmt(r.qty_28d)+' sold</small></div></div>'+
      '<div class="sectiontitle">Company Price Range</div><div class="row3"><div class="kpi"><label>Company A</label><strong>'+money(r.company_price_a)+'</strong></div><div class="kpi"><label>Company B</label><strong>'+money(r.company_price_b)+'</strong></div><div class="kpi"><label>Company C</label><strong>'+money(r.company_price_c)+'</strong></div></div>'+
      '<div class="note '+(r.company_range_violation?'amber':'green')+'" style="margin-top:8px"><b>Applicable range:</b> '+esc(companyRange)+(r.company_range_violation?' · Current price is outside range.':' · Current price is within/has no applicable range.')+'</div>'+
      '<div class="sectiontitle">240 / 249 Integrity</div><div class="kv"><span>240 Main</span><span>'+esc(r.related_240_upc||'—')+' · '+money(r.related_240_current_price)+'</span><span>249 Service</span><span>'+esc(r.related_249_upc||'—')+' · '+money(r.related_249_current_price)+'</span><span>Rule</span><span>'+((r.related_249_present&&r.price_240_249_equal===false)?'MISMATCH · must match':'PASS / N/A')+'</span></div>'+
      '<div class="sectiontitle">Why Suggested</div><div class="note '+(r.priority_240_249_mismatch?'red':'blue')+'"><b>'+esc(r.primary_reason_text||r.suggestion_reason||'Pricing review')+'</b><br>Current '+money(r.current_price)+' → Testing '+money(r.testing_price)+' → Tested '+money(r.tested_price)+'. Current cost '+money(r.current_cost)+' / '+esc(r.selling_uom||'unit')+'.</div>'+
      '<div class="sectiontitle">Price Response History</div><div id="ydPTrendBox" class="loading">Loading 14-day response…</div>'+
      '<div class="actions" style="margin-top:10px"><button class="btn danger" id="ydIgnore">Ignore 12 hours</button></div>'+
    '</div></div>';
  $('#ydIgnore').onclick=()=>{ignorePrice12h(r.upc);renderPriceQueue();toast('Ignored for 12 hours')};
  try{
    const d=await api('/v1/app/v2/upc/'+encodeURIComponent(r.upc)+'/price?trend_supported_days=14'),a=d.price_vs_sales_trend?.rows||[];
    $('#ydPTrendBox').className='tablewrap';
    $('#ydPTrendBox').innerHTML='<table><thead><tr><th>Date</th><th>Qty</th><th>Avg Price</th><th>GP$</th></tr></thead><tbody>'+a.slice(-14).reverse().map(x=>'<tr><td>'+esc(x.date||'')+'</td><td>'+fmt(x.sold_quantity)+'</td><td>'+money(x.avg_sold_price)+'</td><td>'+money(x.gp_dollars)+'</td></tr>').join('')+'</tbody></table>';
  }catch(e){$('#ydPTrendBox').innerHTML='<div class="error">'+esc(e.message)+'</div>'}
}
async function acceptPrice(r){
  try{
    await api('/v1/yipman/pricing-review/'+encodeURIComponent(r.upc)+'/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_price:r.current_price,current_price_source:r.current_price_source,current_price_asof_date:r.current_price_observed_date,candidate_price:r.candidate_price})});
    D.priceMeta=null;toast('Accepted · hidden until price evidence changes');await refreshPriceData(true,0);
  }catch(e){toast(e.message)}
}
async function loadPerformance(){const root=$('#yd-performance');if(!root.dataset.init){root.dataset.init='1';root.innerHTML='<div class="pagehead"><div><h2>Performance</h2><p>Completed-day sales and GP analysis with top sellers, negative movers and management drivers.</p></div><div class="actions"><select id="ydPerfStart" class="select"></select><select id="ydPerfEnd" class="select"></select><button id="ydPerfRun" class="btn primary">Run Report</button></div></div><div id="ydPerfMain"><div class="loading">Loading performance dates…</div></div>';$('#ydPerfRun').onclick=runPerf}
  try{const d=await api('/v1/app/v2/performance/dates?limit=180'),a=(d.dates||[]).map(x=>String(x.date||'')).filter(Boolean).sort();if(!$('#ydPerfStart').options.length){$('#ydPerfStart').innerHTML=a.map(x=>'<option>'+x+'</option>').join('');$('#ydPerfEnd').innerHTML=a.map(x=>'<option>'+x+'</option>').join('');if(a.length){$('#ydPerfEnd').value=a[a.length-1];$('#ydPerfStart').value=a[Math.max(0,a.length-7)]}}runPerf()}catch(e){$('#ydPerfMain').innerHTML='<div class="error">'+esc(e.message)+'</div>'}}
 async function runPerf(){const box=$('#ydPerfMain');box.innerHTML='<div class="loading">Running range analysis…</div>';try{const d=await api('/v1/app/v2/performance/range?start_date='+encodeURIComponent($('#ydPerfStart').value)+'&end_date='+encodeURIComponent($('#ydPerfEnd').value)+'&limit=1000');D.perf=d;const s=d.summary||{},a=(d.items||[]).slice().sort((x,y)=>(num(y.gp_dollars)??-1)-(num(x.gp_dollars)??-1));box.innerHTML='<div class="kpis" style="margin-bottom:9px"><div class="kpi"><label>Date Range</label><strong>'+esc(d.start_date)+' → '+esc(d.end_date)+'</strong><small>'+fmt(d.supported_day_count,0)+' completed days</small></div><div class="kpi"><label>Sales</label><strong>'+money(s.sales_dollars)+'</strong></div><div class="kpi"><label>GP$</label><strong>'+money(s.gp_dollars)+'</strong></div><div class="kpi"><label>Items Sold</label><strong>'+fmt(s.sold_item_count,0)+'</strong></div><div class="kpi"><label>READY</label><strong>'+fmt(s.ready_item_count,0)+'</strong></div><div class="kpi"><label>QA HOLD</label><strong>'+fmt(s.qa_hold_item_count,0)+'</strong></div></div><div class="perfgrid"><div><div class="card"><div class="cardhead"><h3>Top Sellers / GP$</h3></div><div class="tablewrap"><table><thead><tr><th>#</th><th>Item</th><th>UPC</th><th>Qty</th><th>Velocity</th><th>Sales</th><th>GP$</th><th>GP%</th><th>Avg Price</th></tr></thead><tbody>'+a.slice(0,20).map((r,i)=>'<tr class="pick perfrow" data-i="'+i+'"><td>'+(i+1)+'</td><td><b>'+esc(r.name||'—')+'</b><div class="tiny">Family '+esc(r.family_article_number||'—')+'</div></td><td>'+esc(r.upc||'—')+'</td><td>'+fmt(r.sold_quantity)+' '+esc(r.qty_uom||'')+'</td><td>'+fmt(r.velocity)+'</td><td>'+money(r.sales_amount)+'</td><td><b>'+money(r.gp_dollars)+'</b></td><td>'+pct(r.gp_pct)+'</td><td>'+money(r.avg_sold_price)+'</td></tr>').join('')+'</tbody></table></div></div></div><aside class="analysis"><div class="card"><div class="cardhead"><h3>Management Analysis</h3><span class="badge blue">LIVE RANGE</span></div><div class="cardbody" id="ydPerfAnalysis"><div class="insight"><b>Sales concentration</b><br>Top contributors are ranked by GP$ by default so high-volume items can be reviewed for margin quality, not sales alone.</div><div class="insight"><b>Completed-day rule</b><br>'+fmt(d.supported_day_count,0)+' canonical completed day(s) are included. Missing dates are not treated as zero.</div><div class="insight"><b>Cross-module action</b><br>Use Quick Check and Price Suggestions to inspect the same item without losing the range report.</div></div></div></aside></div>';$$('.perfrow',box).forEach(tr=>tr.onclick=()=>{const r=a[Number(tr.dataset.i)];$('#ydPerfAnalysis').innerHTML='<div class="row2"><div class="kpi"><label>Sales</label><strong>'+money(r.sales_amount)+'</strong></div><div class="kpi"><label>GP$</label><strong>'+money(r.gp_dollars)+'</strong></div></div><div class="sectiontitle">'+esc(r.name||'Item')+'</div><div class="kv"><span>UPC</span><span>'+esc(r.upc||'—')+'</span><span>Family</span><span>'+esc(r.family_article_number||'—')+'</span><span>Qty</span><span>'+fmt(r.sold_quantity)+' '+esc(r.qty_uom||'')+'</span><span>Velocity</span><span>'+fmt(r.velocity)+'</span><span>GP%</span><span>'+pct(r.gp_pct)+'</span><span>Avg Sold Price</span><span>'+money(r.avg_sold_price)+'</span></div>'})}catch(e){box.innerHTML='<div class="error">'+esc(e.message)+'</div>'}}
 async function loadPI(force=false){
  const root=$('#yd-pi');
  if(!root.dataset.init){
    root.dataset.init='1';
    root.innerHTML='<div class="pagehead"><div><h2>PI / True Stock</h2><p>Family-level verification, effective OH evidence and Pending Dumping behavior.</p></div><div class="actions"><input id="ydPiSearch" class="input" placeholder="Search Family / Item"><select id="ydPiSort" class="select"><option value="selling">Most selling</option><option value="oh">Highest OH</option><option value="negative">Negative OH first</option></select><button id="ydPiRefresh" class="btn">Refresh</button></div></div><div id="ydPiMain"><div class="loading">Loading family inventory…</div></div>';
    $('#ydPiSearch').oninput=renderPI;$('#ydPiSort').onchange=renderPI;$('#ydPiRefresh').onclick=()=>loadPI(true);
  }
  if(D.piGroups.length&&!force){renderPI();return}
  $('#ydPiMain').innerHTML='<div class="loading">Loading current family inventory…</div>';
  try{
    const d=await api('/v1/backoffice/inventory?category=ALL&limit=400&lightweight=true');
    D.piGroups=group(d.rows||[]);
    renderPI();
  }catch(e){
    $('#ydPiMain').innerHTML='<div class="priceEmpty"><h3>PI inventory did not finish loading</h3><p>'+esc(e.message)+'</p><button id="ydPiRetry" class="btn primary">Retry</button></div>';
    const b=$('#ydPiRetry');if(b)b.onclick=()=>loadPI(true);
  }
 }
 function renderPI(){let a=D.piGroups.slice(),q=$('#ydPiSearch')?.value.trim().toLowerCase()||'';if(q)a=a.filter(g=>(g.id+' '+g.name).toLowerCase().includes(q));const s=$('#ydPiSort')?.value||'selling';if(s==='oh')a.sort((x,y)=>(num(y.row.family_oh)||0)-(num(x.row.family_oh)||0));if(s==='negative')a.sort((x,y)=>(num(x.row.family_oh)||0)-(num(y.row.family_oh)||0));$('#ydPiMain').innerHTML='<div class="pigrid"><div class="card"><div class="cardhead"><h3>Family True Stock Worklist</h3><span class="badge blue">'+a.length+' families</span></div>'+a.slice(0,120).map(g=>'<div class="pirow" data-family="'+esc(g.id)+'"><div><b>'+esc(g.name)+'</b><div class="tiny">Family '+esc(g.id)+'</div></div><span>System OH<br><b>'+fmt(g.row.family_oh)+' '+esc(g.row.family_oh_uom||'')+'</b></span><span>7D MVT<br><b>'+fmt(g.row.family_group_movement_7d)+'</b></span><span>DOH<br><b>'+fmt(g.row.doh)+'</b></span><span>Last Receipt<br><b>'+(recHist(g.row)[0]?esc(appDate(recDate(recHist(g.row)[0]))):'—')+'</b></span><span>Status<br><b>'+esc(g.row.readiness||'—')+'</b></span><div><button class="btn primary">Count</button></div></div>').join('')+'</div><aside class="analysis" id="ydPiAnalysis"><div class="card"><div class="loading">Select a family to submit True Stock.</div></div></aside></div>';$$('.pirow','#ydPiMain').forEach(x=>x.onclick=()=>{selectPI(x.dataset.family);$$('.pirow','#ydPiMain').forEach(y=>y.classList.remove('selected'));x.classList.add('selected')});if(a[0])selectPI(a[0].id)}
 async function selectPI(id){
  const g=D.piGroups.find(x=>String(x.id)===String(id));if(!g)return;
  const panel=$('#ydPiAnalysis');if(!panel)return;
  panel.innerHTML='<div class="card"><div class="loading">Loading family stock evidence…</div></div>';
  let row=g.row;
  try{
    const d=await api('/v1/backoffice/inventory?category=ALL&limit=60&lightweight=false&q='+encodeURIComponent(g.id));
    const candidates=(d.rows||[]).filter(x=>String(x.family_article||x.family_id||'')===String(g.id));
    if(candidates.length){
      row=candidates.find(x=>Array.isArray(x.family_receipt_history)&&x.family_receipt_history.length)||candidates[0];
      g.row=row;
      g.rows=candidates;
    }
  }catch(e){
    // PI list data is still sufficient for counting; detailed receipt evidence is supplemental.
  }
  const r=row,h=recHist(r);
  panel.innerHTML='<div class="card"><div class="cardhead"><div><h3>'+esc(g.name)+'</h3><div class="tiny">Family '+esc(g.id)+'</div></div><span class="badge amber">FAMILY LEVEL</span></div><div class="cardbody">'+
    '<div class="row3"><div class="kpi"><label>Effective OH</label><strong>'+fmt(r.family_oh)+' '+esc(r.family_oh_uom||'')+'</strong><small>'+esc(r.family_oh_status||'current')+'</small></div><div class="kpi"><label>7D Family MVT</label><strong>'+fmt(r.family_group_movement_7d??r.family_source_movement_7d)+'</strong><small>'+fmt(r.family_group_avg_qty_day??r.family_source_avg_qty_day)+'/day</small></div><div class="kpi"><label>DOH / DOS</label><strong>'+fmt(r.doh)+' / '+fmt(r.dos)+'</strong><small>coverage evidence</small></div></div>'+
    '<div class="sectiontitle">OH / Receipt Evidence</div><div class="kv"><span>OH status</span><span>'+esc(r.family_oh_status||'—')+'</span><span>Latest receipt</span><span>'+(h[0]?esc(appDate(recDate(h[0])))+' · '+fmt(recQty(h[0]))+' '+esc(recUom(h[0])):'—')+'</span><span>Previous receipt</span><span>'+(h[1]?esc(appDate(recDate(h[1])))+' · '+fmt(recQty(h[1]))+' '+esc(recUom(h[1])):'—')+'</span><span>Linked UPCs</span><span>'+fmt((g.rows||[]).length,0)+'</span><span>Readiness</span><span>'+esc(r.readiness||r.quick_check_status||'—')+'</span></div>'+
    '<div class="sectiontitle">Observed True Stock</div><div class="actions"><input id="ydTrue" class="trueinput" type="number" step="0.01" placeholder="Enter '+esc(r.family_oh_uom||'qty')+'"><button id="ydTrueSave" class="btn primary">Submit True Stock</button></div>'+
    '<div class="note amber" style="margin-top:8px">One submit saves Family True Stock. If the count is lower than System / Effective OH, the existing workflow creates Pending Dumping for the difference.</div>'+
    '</div></div>';
  $('#ydTrueSave').onclick=()=>saveTrue(g);
 }
 async function saveTrue(g){const v=num($('#ydTrue').value);if(v===null){toast('Enter True Stock');return}try{await api('/v1/app/v2/pi/'+encodeURIComponent(g.id)+'/true-stock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({true_stock:v,uom:g.row.family_oh_uom||'',note:'Yipman desktop True Stock'})});toast('True Stock saved');loadPI()}catch(e){toast(e.message)}}
 async function loadData(){const root=$('#yd-data');if(!root.dataset.init){root.dataset.init='1';root.innerHTML='<div class="pagehead"><div><h2>Data Center</h2><p>File upload, current processing, 14-Day Completeness, recent batches and QA diagnostics in one desktop page.</p></div><div class="actions"><button class="btn" id="ydDataRefresh">Refresh</button></div></div><div id="ydDataMain"><div class="loading">Loading Data Center…</div></div>';$('#ydDataRefresh').onclick=loadDataInner}loadDataInner()}
 async function loadDataInner(){const box=$('#ydDataMain');box.innerHTML='<div class="loading">Loading current data operations…</div>';try{const [dh,active,recent,qa]=await Promise.all([api('/v1/backoffice/data-health?days=14'),api('/v1/web-upload/active'),api('/v1/web-upload/recent?limit=8'),api('/v1/backoffice/qa-review?limit=300')]);D.health=dh;D.qa=qa.issues||[];$('#ydQc').textContent=D.qa.length;const b=active.active_batch||active.latest_batch||{},st=String(b.processing_status||'NONE').toUpperCase(),latest=dh.latest||{},rows=dh.rows||[],complete=rows.filter(x=>String(x.overall_status).toUpperCase()==='COMPLETE').length,missing=rows.filter(x=>String(x.overall_status).toUpperCase()==='MISSING').length,judged=complete+missing,pc=judged?Math.round(complete/judged*100):100;box.innerHTML='<div class="datagrid"><div><div class="card"><div class="cardhead"><h3>1. Upload New Files</h3><span class="badge blue">REAL UPLOADER</span></div><div class="cardbody"><div class="upload"><div style="font-size:24px">⇧</div><h3>Select source files</h3><p>XLSX / XLS / XLSM / CSV / TXT / TSV. Files selected together create one immutable batch.</p><input id="ydFiles" type="file" multiple accept=".xlsx,.xls,.xlsm,.csv,.txt,.tsv"><div style="margin-top:8px"><input id="ydNote" class="input" placeholder="Optional batch note" style="width:100%"></div><button id="ydUpload" class="btn primary" style="margin-top:8px">Upload & Start Processing</button><div id="ydUploadResult" class="small" style="margin-top:8px">No upload in this session.</div></div></div></div><div class="card" style="margin-top:9px"><div class="cardhead"><h3>3. 14-Day Completeness & Source Coverage</h3><span class="badge '+(missing?'amber':'green')+'">'+pc+'%</span></div><div class="cardbody"><div class="row3"><div class="kpi"><label>Required-day completeness</label><strong>'+pc+'%</strong><small>'+complete+' complete / '+judged+' judged</small></div><div class="kpi"><label>Missing required days</label><strong>'+missing+'</strong><small>POS and/or MVT missing</small></div><div class="kpi"><label>Latest POS / MVT</label><strong>'+esc(latest.POS?.date||'—')+' / '+esc(latest.MVT?.date||'—')+'</strong></div></div><div class="note blue" style="margin-top:8px"><b>How completeness works:</b> A completed business day is Complete only when canonical POS + canonical MVT are both present. Price, OH, Live/Fresh and Frozen are snapshot sources and are not required every day.</div><div class="legend"><span><i class="sw g"></i><b>Green</b> Complete</span><span><i class="sw r"></i><b>Red</b> Missing POS/MVT</span><span><i class="sw b"></i><b>Blue</b> Current/Open day</span><span><i class="sw a"></i><b>Amber</b> Partial/other</span><span><i class="sw x"></i><b>Gray / —</b> No snapshot update; not automatically an error</span></div><div class="healthstrip">'+rows.slice(0,14).map(hDay).join('')+'</div></div></div><div class="card" style="margin-top:9px"><div class="cardhead"><h3>4. Recent Batches</h3></div><div class="tablewrap"><table><thead><tr><th>Batch</th><th>Time</th><th>Status</th><th>Ready</th><th>Hold</th></tr></thead><tbody>'+((recent.batches||recent.rows||[]).map(x=>'<tr><td>#'+esc(x.batch_id||'—')+'</td><td>'+esc(String(x.completed_at||x.upload_started_at||'').slice(0,16))+'</td><td>'+esc(x.processing_status||x.phase3_status||'—')+'</td><td>'+fmt(x.quick_check_ready_rows,0)+'</td><td>'+fmt(x.quick_check_hold_rows,0)+'</td></tr>').join('')||'<tr><td colspan="5">No recent batches.</td></tr>')+'</tbody></table></div></div></div><aside class="analysis"><div class="card"><div class="cardhead"><h3>2. Current Processing</h3><span class="badge '+(st.includes('HOLD')?'amber':'blue')+'">'+esc(st)+'</span></div><div class="cardbody"><div class="row3"><div class="kpi"><label>Batch</label><strong>'+(b.batch_id?'#'+esc(b.batch_id):'None')+'</strong></div><div class="kpi"><label>Run</label><strong>#'+esc(b.active_pipeline_run_id||'—')+'</strong></div><div class="kpi"><label>Open Issues</label><strong>'+fmt(b.open_issue_total??b.error_count,0)+'</strong></div></div><div class="pipeline" style="margin-top:8px"><div class="stage '+(st!=='NONE'?'done':'')+'">REGISTERED</div><div class="stage '+(/INGEST|PHASE|QUICK|READY/.test(st)?'done':'')+'">INGESTED</div><div class="stage '+(/PHASE|QUICK|READY/.test(st)?'done':'')+'">PHASE 2C</div><div class="stage '+(st.includes('HOLD')?'hold':/PHASE3|QUICK|READY/.test(st)?'done':'')+'">PHASE 3 QA</div><div class="stage '+(/QUICK_CHECK_READY/.test(st)?'done':'')+'">PUBLISH</div></div><div class="sectiontitle">Top QA Holds</div><div class="tablewrap"><table><thead><tr><th>Issue</th><th>Entity</th><th>Severity</th></tr></thead><tbody>'+D.qa.slice(0,12).map(x=>'<tr><td>'+esc(x.issue_code||x.issue_summary||'—')+'</td><td>'+esc(x.entity_key||'—')+'</td><td>'+esc(x.severity||'—')+'</td></tr>').join('')+'</tbody></table></div></div></div></aside></div>';$('#ydUpload').onclick=uploadFiles}catch(e){box.innerHTML='<div class="error">'+esc(e.message)+'</div>'}}
 function hDay(r){const s=r.sources||{},v=String(r.overall_status||'').toUpperCase(),cl=v==='COMPLETE'?'complete':v==='MISSING'?'missing':v.includes('CURRENT')?'current':'partial',sc=x=>String(x?.status||'').toUpperCase()==='OK'?'ok':String(x?.status||'').toUpperCase()==='MISSING'?'miss':String(x?.status||'').toUpperCase()==='NOT_DUE'?'nd':'';return '<div class="hday '+cl+'" title="'+esc((r.date||'')+' · '+v)+'"><div class="wd">'+esc(r.weekday||'')+'</div><div class="dt">'+esc(String(r.date||'').slice(5))+'</div><div class="srcdots"><span class="sd '+sc(s.POS)+'">POS</span><span class="sd '+sc(s.MVT)+'">MVT</span></div><div class="tiny" style="margin-top:4px">Snapshots '+['PRICE','OH','LIVE_FRESH','FROZEN'].filter(k=>String(s[k]?.status||'').toUpperCase()==='OK').length+'/4</div></div>'}
 async function uploadFiles(){const files=[...$('#ydFiles').files];if(!files.length){toast('Select files first');return}const btn=$('#ydUpload'),out=$('#ydUploadResult');btn.disabled=true;try{const label=$('#ydNote').value.trim()||('Yipman desktop upload '+new Date().toLocaleString()),created=await api('/v1/web-upload/batches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label})}),session=created.session_id||created.batch_key||created.session?.session_id;if(!session)throw new Error('Upload batch session ID not returned');for(let i=0;i<files.length;i++){const fd=new FormData();fd.append('file',files[i]);out.textContent='Uploading '+(i+1)+'/'+files.length+': '+files[i].name;await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/files',{method:'POST',body:fd})}out.textContent='Committing batch and starting processing…';const commit=await api('/v1/web-upload/batches/'+encodeURIComponent(session)+'/commit',{method:'POST'});out.innerHTML='<b>Upload verified · Batch #'+esc(commit.batch_id||created.batch_id||'—')+'</b><br>'+files.length+' file(s) committed';$('#ydFiles').value='';$('#ydNote').value='';toast('Upload verified');setTimeout(loadDataInner,600)}catch(e){out.innerHTML='<div class="error">'+esc(e.message)+'</div>';toast('Upload not committed')}finally{btn.disabled=false}}
 async function init(){root();enableDesktopWheelScroll();await topStatus();const h=String(location.hash||'').replace(/^#/,'');const m=['quick','order','price','performance','pi','data'].includes(h)?h:'quick';openMod(m)}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
"""
