"""Logo startup gate for the desktop shell; read-only existing readiness events."""

STARTUP_HTML = r'''
<style>
#desktopStartup{position:fixed;inset:0;z-index:20000;display:flex;align-items:center;justify-content:center;padding:20px;overflow:auto;background:#020b08;color:#65ff89;font:14px/1.35 Consolas,monospace}
#desktopStartup[hidden]{display:none}#desktopStartup .startup-box{width:min(100%,520px);padding:20px;border:1px solid #439d78;border-radius:12px;background:#071a14}
#desktopStartup img{display:block;width:96px;height:96px;margin:0 auto 10px;border-radius:18px}#desktopStartup h1,#desktopStartup .startup-version{text-align:center;margin:4px 0}#desktopStartup h1{font-size:25px}#desktopStartup progress{width:100%;height:12px;accent-color:#65ff89}#desktopStartup strong{display:block;text-align:right;font-size:24px}#desktopStartup small{color:#91bd9b}#desktopStartup .startup-files{border-top:1px solid #335e4c;margin-top:12px;padding-top:6px}#desktopStartup .startup-files p{margin:4px 0;font-size:12px}#desktopStartup button{min-height:40px;padding:6px 10px;margin:4px;border:1px solid #439d78;background:#061510;color:#65ff89;cursor:pointer}
</style>
<section id="desktopStartup" role="dialog" aria-modal="true" aria-label="Preparing FishFinder · Fish Watch"><div class="startup-box"><img src="https://seafood-stock-watch.bronzedove3.chatgpt.site/icon-512.png" width="96" height="96" alt="FishFinder · Fish Watch"><h1>FishFinder · Fish Watch</h1><p class="startup-version">Desktop v131</p><p id="desktopStartupStep">Preparing your website…</p><progress id="desktopStartupBar" max="100" value="0" aria-label="Startup progress"></progress><strong id="desktopStartupPercent">0%</strong><small>Shown for at least 10 seconds. Opens at 80% when the selected workspace is ready. Remaining updates continue in the background.</small><div class="startup-files"><p>Latest accepted file data dates</p><div id="desktopStartupFiles">Checking uploaded files…</div></div><div id="desktopStartupRetry" hidden><p>Some updates are taking longer. Retry, or view available dated data.</p><button id="desktopStartupRetryButton" type="button">Retry updates</button><button id="desktopStartupUse" type="button">Use available data</button></div></div></section>
<script id="desktop-startup-logo">
(()=>{
 const root=document.getElementById('desktopStartup'),bar=document.getElementById('desktopStartupBar'),percent=document.getElementById('desktopStartupPercent'),step=document.getElementById('desktopStartupStep'),fileBox=document.getElementById('desktopStartupFiles');
 const done=new Set(['settings']),valid=new Set(['health','recent','publication','coverage','monitor']);let released=false,lastValue=0,lastUsable=false,releaseTimer=null;const startedAt=Date.now();
 const previousOverflow=document.body.style.overflow,inertBefore=new Map();document.body.style.overflow='hidden';
 function protect(){for(const node of document.body.children)if(node!==root&&!['SCRIPT','STYLE'].includes(node.tagName)){if(!inertBefore.has(node))inertBefore.set(node,node.inert);node.inert=true;}}
 const observer=new MutationObserver(protect);observer.observe(document.body,{childList:true});protect();
 const active=()=>['inventory','price-review'].includes(location.hash.slice(1))?location.hash.slice(1):'data';
 function release(){if(released)return;const remaining=10000-(Date.now()-startedAt);if(remaining>0){clearTimeout(releaseTimer);releaseTimer=setTimeout(release,remaining);return;}released=true;clearTimeout(releaseTimer);observer.disconnect();for(const [node,value] of inertBefore)node.inert=value;document.body.style.overflow=previousOverflow;root.hidden=true;clearTimeout(timeout);}
 function update(value,usable){value=Math.max(0,Math.min(100,Number(value)||0));bar.value=value;percent.textContent=value+'%';lastValue=value;lastUsable=usable;if(value>=80&&usable){const remaining=10000-(Date.now()-startedAt);if(remaining<=0)release();else{clearTimeout(releaseTimer);releaseTimer=setTimeout(()=>update(lastValue,lastUsable),remaining);}}}
 function showFiles(files,checkedAt){fileBox.replaceChildren();for(const file of files){const line=document.createElement('p');line.textContent=file.type+' · '+(file.date||'Unverified')+' · '+(file.current?'Current':file.ageDays==null?'Unverified':file.ageDays+' days old');line.style.color=file.current?'#65ff89':'#ffd477';line.title=file.name||'';fileBox.append(line);}if(checkedAt){const line=document.createElement('p');line.textContent='Checked '+new Date(checkedAt).toLocaleString();fileBox.append(line);}}
 window.addEventListener('dc:startup-step',event=>{if(!valid.has(event.detail?.name))return;done.add(event.detail.name);if(active()==='data'){step.textContent=done.size+'/6 preparation steps ready';update(Math.floor(done.size/6*100),done.has('coverage'));}});
 window.addEventListener('dc:startup-files',event=>{const {data,checkedAt}=event.detail||{};if(!data?.latest||active()!=='data')return;showFiles(Object.entries(data.latest).map(([type,row])=>{const date=row.date||null,required=type==='POS'?data.pos_required_through:type==='MVT'?data.mvt_required_through:data.today;return {type,date,name:row.file,current:!!date&&date>=required,ageDays:date?Math.max(0,Math.round((Date.parse(data.today)-Date.parse(date))/86400000)):null};}),checkedAt);});
 window.addEventListener('message',event=>{const name=active(),frame=name==='inventory'?document.getElementById('inventoryFrame'):name==='price-review'?document.getElementById('priceReviewFrame'):null;if(!frame||event.origin!=='https://seafood-stock-watch.bronzedove3.chatgpt.site'||event.source!==frame.contentWindow||event.data?.type!=='yipman:startup-progress')return;step.textContent='Preparing '+(name==='inventory'?'Inventory':'Price Review')+'…';if(event.data.version)root.querySelector('.startup-version').textContent='Desktop v'+event.data.version;if(event.data.files?.length)showFiles(event.data.files,event.data.checkedAt);update(event.data.percent,event.data.usable===true);if(event.data.errors)document.getElementById('desktopStartupRetry').hidden=false;});
 document.getElementById('desktopStartupRetryButton').onclick=()=>{const name=active();if(name==='data')window.dispatchEvent(new Event('dc:data-workspace-active'));else{const frame=document.getElementById(name==='inventory'?'inventoryFrame':'priceReviewFrame');if(frame){const url=new URL(frame.src);url.searchParams.set('_startup_retry',String(Date.now()));frame.src=url.href;}}};
 document.getElementById('desktopStartupUse').onclick=release;
 const timeout=setTimeout(()=>{document.getElementById('desktopStartupRetry').hidden=false;},20000);
 if(active()==='data')update(Math.floor(done.size/6*100),false);
})();
</script>
'''


def apply_startup_logo(html):
    if 'id="desktop-startup-logo"' in html:
        return html
    html = html.replace('<body>', '<body>' + STARTUP_HTML, 1)
    html = html.replace('function panelUpdate(name,values){', "function panelUpdate(name,values){if(values.pending===false&&!values.error&&!values.saved)window.dispatchEvent(new CustomEvent('dc:startup-step',{detail:{name}}));", 1)
    html = html.replace('function acceptCoverage(coverage,checkedAt,saved=false){', "function acceptCoverage(coverage,checkedAt,saved=false){window.dispatchEvent(new CustomEvent('dc:startup-files',{detail:{data:coverage,checkedAt,saved}}));", 1)
    return html
