from __future__ import annotations

DESKTOP_DATA_CENTER_V368_CSS = r"""
@media (min-width:760px){
  .v368-upload-dock{margin:0 0 10px;background:#fff;border:1px solid #dbe5ef;border-radius:12px;box-shadow:0 5px 20px rgba(31,61,91,.045);overflow:hidden}
  .v368-upload-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 12px;border-bottom:1px solid #e7edf4;background:linear-gradient(180deg,#fff,#fbfdff)}
  .v368-upload-head h3{margin:0;font-size:14px}.v368-upload-head p{margin:3px 0 0;font-size:9px;color:#6c7d91}
  .v368-upload-dock .uploadgrid{display:grid!important;grid-template-columns:minmax(440px,1.2fr) minmax(320px,.8fr)!important;gap:9px;padding:10px!important}
  .v368-upload-dock .drop{margin:0!important;min-height:140px!important;border:1.5px dashed #aebfd0!important;border-radius:10px!important;background:#f9fcff!important;padding:14px!important}
  .v368-upload-dock .drop .ico{font-size:24px!important}.v368-upload-dock .drop h3{font-size:13px!important;margin:4px 0!important}
  .v368-upload-dock .drop p{font-size:9px!important;margin:4px 0 8px!important;color:#6b7c8f!important}.v368-upload-dock input[type=file]{font-size:10px!important}
  .v368-health-guide{margin:0 10px 10px;border:1px solid #dce6ef;border-radius:11px;background:#fff;overflow:hidden}
  .v368-health-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;padding:9px}
  .v368-health-kpi{border:1px solid #e2e9f0;border-radius:9px;padding:8px;background:#fbfdff}
  .v368-health-kpi small{display:block;font-size:7px;text-transform:uppercase;letter-spacing:.04em;font-weight:900;color:#738397}
  .v368-health-kpi b{display:block;font-size:16px;margin-top:2px;color:#142b43}.v368-health-kpi span{font-size:8px;color:#76869a}
  .v368-health-explain{padding:9px 10px;border-top:1px solid #e9eef4;border-bottom:1px solid #e9eef4;background:#f8fbfe}
  .v368-health-explain strong{font-size:10px}.v368-health-explain p{margin:3px 0 0;font-size:9px;line-height:1.45;color:#5f7187}
  .v368-health-legend{display:flex;gap:12px;flex-wrap:wrap;padding:8px 10px;border-bottom:1px solid #edf2f6;font-size:9px;color:#52667e}
  .v368-legend-item{display:flex;align-items:center;gap:5px}.v368-swatch{width:11px;height:11px;border-radius:3px;border:1px solid transparent}
  .v368-swatch.complete{background:#dff5e8;border-color:#9ed7b5}.v368-swatch.missing{background:#ffe5e9;border-color:#f2a7b2}
  .v368-swatch.current{background:#e6f2ff;border-color:#9ac6fb}.v368-swatch.snapshot{background:#edf1f5;border-color:#cfd8e1}.v368-swatch.partial{background:#fff1cf;border-color:#e8c66d}
  .v368-complete-strip{display:grid;grid-template-columns:repeat(14,minmax(58px,1fr));gap:5px;padding:9px 10px;overflow:auto}
  .v368-dayhealth{border:1px solid #dfe7ef;border-radius:8px;padding:6px 5px;min-width:58px;cursor:pointer;background:#fff}.v368-dayhealth:hover{box-shadow:0 0 0 2px rgba(11,114,244,.12)}
  .v368-dayhealth.complete{background:#eef9f2;border-color:#b9dfc8}.v368-dayhealth.missing{background:#fff0f2;border-color:#efbdc5}.v368-dayhealth.current{background:#edf6ff;border-color:#b8d7fb}.v368-dayhealth.partial{background:#fff8e8;border-color:#edd39a}
  .v368-dayhealth .date{font-size:9px;font-weight:900}.v368-dayhealth .weekday{font-size:7px;color:#718197;text-transform:uppercase}
  .v368-source-dots{display:flex;gap:3px;margin-top:5px}.v368-dot{font-size:7px;border-radius:4px;padding:2px 3px;font-weight:900;background:#edf1f5;color:#68788b}
  .v368-dot.ok{background:#dff5e8;color:#17784a}.v368-dot.miss{background:#ffe3e8;color:#b42e44}.v368-dot.nd{background:#e6f2ff;color:#0b67d5}.v368-dayhealth .snap{font-size:7px;color:#6f8094;margin-top:4px}
  .v368-health-note{padding:0 10px 10px;font-size:8px;color:#748398;line-height:1.4}
  #dbdata .panelhead .title:after{content:" · 14-Day Completeness & Source Coverage"}
  @media(max-width:1200px){.v368-upload-dock .uploadgrid{grid-template-columns:1fr!important}.v368-health-summary{grid-template-columns:repeat(2,1fr)}}
}
"""

DESKTOP_DATA_CENTER_V368_JS = r"""
(function(){
  if(window.matchMedia('(max-width:759px)').matches)return;
  function q(s,r){return (r||document).querySelector(s)}
  function qa(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  async function getJson(url){var r=await fetch(url,{cache:'no-store'}),raw=await r.text(),d={};if(raw){try{d=JSON.parse(raw)}catch(e){d={detail:raw}}}if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:'HTTP '+r.status);return d}
  function enhance(){
    var main=q('#database .v366-ws-main')||q('#database');if(!main)return false;
    if(!q('#v368UploadDock')){
      var grid=q('#dboverview .uploadgrid');
      if(grid){
        var title=grid.previousElementSibling&&grid.previousElementSibling.classList.contains('sectiontitle')?grid.previousElementSibling:null;
        var dock=document.createElement('section');dock.id='v368UploadDock';dock.className='v368-upload-dock';
        dock.innerHTML='<div class="v368-upload-head"><div><h3>Upload New Files</h3><p>Always visible in Data Center · XLSX / XLS / XLSM / CSV / TXT / TSV · files selected together create one immutable batch.</p></div><span class="pill blue">FILE UPLOADER</span></div>';
        if(title)title.remove();grid.parentNode.removeChild(grid);dock.appendChild(grid);
        var hero=q('.desktop-data-hero',main);if(hero&&hero.nextSibling)main.insertBefore(dock,hero.nextSibling);else main.insertBefore(dock,main.firstChild);
      }
    }
    var panel=q('#dbdata .panel');
    if(panel&&!q('#v368HealthGuide',panel)){
      var g=document.createElement('div');g.id='v368HealthGuide';g.className='v368-health-guide';
      g.innerHTML='<div id="v368HealthSummary" class="v368-health-summary"><div class="v368-health-kpi"><small>Required-day completeness</small><b>Loading…</b><span>POS + MVT</span></div></div>'+
      '<div class="v368-health-explain"><strong>How the colors work</strong><p>A completed business day is <b>Complete</b> only when both canonical POS and canonical MVT exist. Missing POS or MVT makes the day <b>Missing</b>. Price List, OH, Live/Fresh and Frozen are snapshot sources: they are not expected every day, and a gray / no-update cell does not by itself make the day incomplete.</p></div>'+
      '<div class="v368-health-legend"><span class="v368-legend-item"><i class="v368-swatch complete"></i><b>Green · Complete</b> — POS + MVT available</span><span class="v368-legend-item"><i class="v368-swatch missing"></i><b>Red · Missing</b> — POS or MVT absent</span><span class="v368-legend-item"><i class="v368-swatch current"></i><b>Blue · Current/Open Day</b> — not judged complete yet</span><span class="v368-legend-item"><i class="v368-swatch partial"></i><b>Amber · Partial/Other</b> — transitional status</span><span class="v368-legend-item"><i class="v368-swatch snapshot"></i><b>Gray / —</b> — no snapshot update that date; not automatically an error</span></div>'+
      '<div id="v368CompletenessStrip" class="v368-complete-strip"><div class="loading">Loading 14-day coverage…</div></div>'+
      '<div class="v368-health-note"><b>Inside each day:</b> POS and MVT show their own status. “Snapshots x/4” counts Price, OH, Live/Fresh and Frozen updates. Click a date to open full source evidence.</div>';
      var head=q('.panelhead',panel);if(head&&head.nextSibling)panel.insertBefore(g,head.nextSibling);else panel.appendChild(g);
    }
    return true;
  }
  function sc(x){var s=String((x&&x.status)||'NONE').toUpperCase();return s==='OK'?'ok':s==='MISSING'?'miss':s==='NOT_DUE'?'nd':''}
  function dc(s){s=String(s||'').toUpperCase();return s==='COMPLETE'?'complete':s==='MISSING'?'missing':(s.indexOf('CURRENT')>=0||s.indexOf('OPEN')>=0)?'current':'partial'}
  async function loadBoard(){
    if(!enhance())return;
    var strip=q('#v368CompletenessStrip'),sum=q('#v368HealthSummary');if(!strip||!sum)return;
    try{
      var d=await getJson('/v1/backoffice/data-health?days=14'),rows=d.rows||[],latest=d.latest||{};
      var complete=rows.filter(function(r){return String(r.overall_status||'').toUpperCase()==='COMPLETE'}).length;
      var missing=rows.filter(function(r){return String(r.overall_status||'').toUpperCase()==='MISSING'}).length;
      var judged=complete+missing,pc=judged?Math.round(complete/judged*100):100;
      sum.innerHTML='<div class="v368-health-kpi"><small>Required-day completeness</small><b>'+pc+'%</b><span>'+complete+' complete / '+judged+' judged</span></div>'+
        '<div class="v368-health-kpi"><small>Missing required days</small><b>'+missing+'</b><span>POS and/or MVT missing</span></div>'+
        '<div class="v368-health-kpi"><small>Latest POS</small><b>'+esc((latest.POS&&latest.POS.date)||'—')+'</b><span>'+esc((latest.POS&&latest.POS.file)||'No source')+'</span></div>'+
        '<div class="v368-health-kpi"><small>Latest MVT</small><b>'+esc((latest.MVT&&latest.MVT.date)||'—')+'</b><span>'+esc((latest.MVT&&latest.MVT.file)||'No source')+'</span></div>';
      strip.innerHTML=rows.slice(0,14).map(function(r){var s=r.sources||{},snap=['PRICE','OH','LIVE_FRESH','FROZEN'].filter(function(k){return String((s[k]&&s[k].status)||'').toUpperCase()==='OK'}).length;return '<div class="v368-dayhealth '+dc(r.overall_status)+'" data-date="'+esc(r.date||'')+'" title="'+esc((r.date||'')+' · '+(r.overall_status||''))+'"><div class="weekday">'+esc(r.weekday||'')+'</div><div class="date">'+esc(String(r.date||'').slice(5))+'</div><div class="v368-source-dots"><span class="v368-dot '+sc(s.POS)+'">POS</span><span class="v368-dot '+sc(s.MVT)+'">MVT</span></div><div class="snap">Snapshots '+snap+'/4</div></div>'}).join('');
      qa('.v368-dayhealth').forEach(function(x){x.onclick=function(){var d=x.dataset.date,b=q('.data-health-detail[data-date="'+CSS.escape(d)+'"]');if(b)b.click();else{var tr=q('.data-health-row[data-date="'+CSS.escape(d)+'"]');if(tr)tr.click()}}});
    }catch(e){strip.innerHTML='<div class="error">Unable to load 14-Day Completeness: '+esc(e.message||e)+'</div>'}
  }
  function init(){
    var tries=0,t=setInterval(function(){tries++;if(enhance()||tries>20){clearInterval(t);loadBoard()}},60);
    document.addEventListener('click',function(e){
      if(e.target.closest('.dbtab[data-dbtab="dbdata"]')||e.target.closest('#refreshData')||e.target.closest('#dbRefreshAll'))setTimeout(loadBoard,120);
    },true);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
"""
