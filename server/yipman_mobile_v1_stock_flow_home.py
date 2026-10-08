from __future__ import annotations

"""Mobile V1 Quick-home Stock Flow board.

Replaces the default Action board with a Family flow comparison while keeping
Actions one tap away. Search remains docked above bottom navigation.
"""

_STYLE = r'''
<style id="yipmanV1StockFlowHomeStyle">
.v1-home-switch{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:2px 0 8px}
.v1-home-switch button{min-height:42px;border:1px solid #344553;border-radius:13px;background:#111a22;color:#99a9b5;font-size:13px;font-weight:1000}
.v1-home-switch button.active{background:#1d405c;border-color:#477fa7;color:#eef7ff}
.v1-flow-controls{display:grid;gap:7px;margin-bottom:8px}
.v1-flow-control-row{display:grid;grid-template-columns:auto minmax(150px,1fr);gap:8px;align-items:center}
.v1-flow-window{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
.v1-flow-window button{min-width:48px;height:38px;border:1px solid #344653;border-radius:11px;background:#101820;color:#95a5b1;font-size:12px;font-weight:1000}
.v1-flow-window button.active{background:#214d70;color:#fff;border-color:#528ab2}
.v1-flow-sort{height:38px;width:100%;border:1px solid #344653;border-radius:11px;background:#101820;color:#edf4f8;padding:0 9px;font-size:12px;font-weight:1000;outline:0}
.v1-flow-caption{border:1px solid #273845;border-radius:10px;background:#0f171e;padding:7px 9px;color:#8ca0ae;font-size:11px;font-weight:900;line-height:1.3;text-align:left}
.v1-flow-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:0 0 9px}
.v1-flow-summary div{border:1px solid #2d3d49;border-radius:11px;background:#101820;padding:7px 5px;text-align:center}
.v1-flow-summary b{display:block;font-size:18px}.v1-flow-summary span{display:block;margin-top:2px;color:#8295a3;font-size:9px;font-weight:1000}
.v1-flow-card{border-left-width:6px!important}.v1-flow-card.over{border-left-color:#e0a84d!important}.v1-flow-card.under{border-left-color:#67aee4!important}.v1-flow-card.balanced{border-left-color:#67bb7b!important}.v1-flow-card.noactivity{border-left-color:#687986!important}
.v1-flow-action-row{display:flex;align-items:center;justify-content:space-between;gap:9px;margin-top:8px}
.v1-flow-action{font-size:20px;font-weight:1000}.v1-flow-action.over{color:#f1cb7a}.v1-flow-action.under{color:#9bd1f6}.v1-flow-action.balanced{color:#9bd6aa}
.v1-flow-diff{flex:0 0 auto;border:1px solid #435463;border-radius:999px;padding:5px 8px;background:#101920;color:#f4f8fa;font-size:12px;font-weight:1000;white-space:nowrap}
.v1-flow-compare{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:9px}
.v1-flow-mainmetric{border:1px solid #354958;border-radius:12px;background:#0e1921;padding:9px 8px;text-align:center;min-width:0}
.v1-flow-mainmetric b{display:block;color:#7f94a4;font-size:9px;font-weight:1000}.v1-flow-mainmetric strong{display:block;margin-top:4px;color:#f4f8fa;font-size:19px;font-weight:1000;overflow-wrap:anywhere}
.v1-flow-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:6px}
.v1-flow-metric{border:1px solid #2c3c48;border-radius:11px;background:#0f1820;padding:8px;min-width:0}
.v1-flow-metric b{display:block;color:#7f92a0;font-size:9px;font-weight:1000}.v1-flow-metric strong{display:block;margin-top:3px;color:#f0f5f8;font-size:15px;font-weight:1000;overflow-wrap:anywhere}
.v1-flow-reason{margin-top:7px;color:#a9b7c1;font-size:12px;line-height:1.35;font-weight:800}
.v1-flow-range{margin-top:6px;color:#718593;font-size:10px;font-weight:850;line-height:1.3}
@media(max-width:390px){.v1-flow-control-row{grid-template-columns:1fr}.v1-flow-mainmetric strong{font-size:18px}.v1-flow-action{font-size:18px}}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1StockFlowHomeScript">
(()=>{
  'use strict';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=(v,d=1)=>{const x=num(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:d})};
  let mode='flow',days=7,rows=[],payload=null,loading=false,sortKey='diffpct';
  const cache=new Map();
  const q=()=>String(document.getElementById('quickSearch')?.value||'').trim();
  const list=()=>document.getElementById('urgentList');

  function dateLabel(v){
    if(!v)return'—';if(typeof window.yipmanDateLabel==='function')return window.yipmanDateLabel(String(v));
    const m=String(v).match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return String(v);const d=new Date(+m[1],+m[2]-1,+m[3]);return ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()]+' · '+(+m[2])+'/'+(+m[3])+'/'+m[1];
  }
  function ensure(){
    const top=document.querySelector('#quick .top');if(!top||document.getElementById('v1HomeSwitch'))return;
    const wrap=document.createElement('div');wrap.innerHTML=`<div id="v1HomeSwitch" class="v1-home-switch"><button data-home-mode="flow" class="active">STOCK FLOW</button><button data-home-mode="actions">ACTIONS</button></div><div id="v1FlowControls" class="v1-flow-controls"><div class="v1-flow-control-row"><div class="v1-flow-window"><button data-flow-days="7" class="active">7D</button><button data-flow-days="14">14D</button><button data-flow-days="28">28D</button></div><select class="v1-flow-sort" id="v1FlowSort"><option value="diffpct">SORT: DIFFERENCE % ↓</option><option value="overpct">OVER-RECEIPT % ↓</option><option value="underpct">UNDER-RECEIPT % ↓</option><option value="selling">SELLING MVT ↓</option><option value="receipts">RECEIPTS ↓</option><option value="oh">EFFECTIVE OH ↓</option><option value="name">NAME A–Z</option></select></div><div class="v1-flow-caption" id="v1FlowCaption">Selected window · Selling MVT vs Receipt Qty</div></div><div id="v1FlowSummary" class="v1-flow-summary"><div><b>—</b><span>OVER WATCH</span></div><div><b>—</b><span>UNDER WATCH</span></div><div><b>—</b><span>BALANCED</span></div></div>`;
    while(wrap.firstChild)top.insertBefore(wrap.firstChild,top.firstChild);
    top.querySelectorAll('[data-home-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.homeMode));
    top.querySelectorAll('[data-flow-days]').forEach(b=>b.onclick=()=>{days=Number(b.dataset.flowDays);top.querySelectorAll('[data-flow-days]').forEach(x=>x.classList.toggle('active',x===b));load(true)});
    const sort=document.getElementById('v1FlowSort');if(sort){sort.value=sortKey;sort.onchange=()=>{sortKey=sort.value||'diffpct';render()}}
    syncChrome();
  }
  function syncChrome(){
    ensure();const flow=mode==='flow';
    document.querySelectorAll('[data-home-mode]').forEach(b=>b.classList.toggle('active',b.dataset.homeMode===mode));
    const summary=document.getElementById('urgentSummary'),updated=document.getElementById('updated'),controls=document.getElementById('v1FlowControls'),fs=document.getElementById('v1FlowSummary');
    if(summary)summary.style.display=flow?'none':'';if(updated)updated.style.display=flow?'none':'';if(controls)controls.style.display=flow?'grid':'none';if(fs)fs.style.display=flow?'grid':'none';
  }
  function setMode(next){
    mode=next==='actions'?'actions':'flow';syncChrome();
    if(q())return;
    if(mode==='actions'){
      if(typeof window.renderUrgent==='function')window.renderUrgent();
    }else if(payload){render()}else load(false);
  }
  function signalClass(s){return s==='OVER_ORDER_WATCH'?'over':s==='UNDER_ORDER_WATCH'?'under':s==='BALANCED'?'balanced':'noactivity'}
  function signalLabel(s){return s==='OVER_ORDER_WATCH'?'OVER-ORDER WATCH':s==='UNDER_ORDER_WATCH'?'UNDER-ORDER WATCH':s==='BALANCED'?'BALANCED FLOW':'NO ACTIVITY'}
  function differencePct(r){
    const explicit=num(r.receipt_vs_selling_difference_pct);if(explicit!==null)return explicit;
    const sell=num(r.family_group_movement_qty),rec=num(r.family_receipt_qty);if(sell!==null&&sell>0&&rec!==null)return((rec-sell)/sell)*100;return null;
  }
  function differenceLabel(r){
    const sell=num(r.family_group_movement_qty)||0,rec=num(r.family_receipt_qty)||0,p=differencePct(r);
    if(sell===0&&rec>0)return'RECEIPTS ONLY';
    if(p===null)return'—';return(p>=0?'+':'')+fmt(p,0)+'%';
  }
  function sortedRows(){
    const a=[...rows],pct=r=>differencePct(r),absPct=r=>{const p=pct(r);if(p!==null)return Math.abs(p);const s=num(r.family_group_movement_qty)||0,rc=num(r.family_receipt_qty)||0;return s===0&&rc>0?999999:0};
    if(sortKey==='overpct')a.sort((x,y)=>(pct(y)??-999999)-(pct(x)??-999999));
    else if(sortKey==='underpct')a.sort((x,y)=>(pct(x)??999999)-(pct(y)??999999));
    else if(sortKey==='selling')a.sort((x,y)=>(num(y.family_group_movement_qty)||0)-(num(x.family_group_movement_qty)||0));
    else if(sortKey==='receipts')a.sort((x,y)=>(num(y.family_receipt_qty)||0)-(num(x.family_receipt_qty)||0));
    else if(sortKey==='oh')a.sort((x,y)=>(num(y.effective_oh)||0)-(num(x.effective_oh)||0));
    else if(sortKey==='name')a.sort((x,y)=>String(x.family_name||'').localeCompare(String(y.family_name||'')));
    else a.sort((x,y)=>absPct(y)-absPct(x)||Math.abs(num(y.receipt_minus_selling)||0)-Math.abs(num(x.receipt_minus_selling)||0));
    return a;
  }
  function reason(r){
    const sell=num(r.family_group_movement_qty)||0,rec=num(r.family_receipt_qty)||0,gap=rec-sell;
    if(r.flow_signal==='OVER_ORDER_WATCH')return sell===0?`Receipt Qty exists in the selected window but supported selling MVT is zero.`:`Receipt Qty is ${fmt(Math.abs(gap))} ${r.family_group_movement_uom||''} above Selling MVT in this selected window.`;
    if(r.flow_signal==='UNDER_ORDER_WATCH')return `Selling MVT is ${fmt(Math.abs(gap))} ${r.family_group_movement_uom||''} above Receipt Qty in this selected window.`;
    if(r.flow_signal==='BALANCED')return `Receipt Qty and Selling MVT are within the normal comparison band for this selected window.`;
    return `No supported Receipt Qty or Selling MVT in this selected window.`;
  }
  function render(){
    if(mode!=='flow'||q())return;syncChrome();const box=list();if(!box)return;
    const c=payload?.signal_counts||{};const sums=document.querySelectorAll('#v1FlowSummary b');if(sums[0])sums[0].textContent=c.OVER_ORDER_WATCH||0;if(sums[1])sums[1].textContent=c.UNDER_ORDER_WATCH||0;if(sums[2])sums[2].textContent=c.BALANCED||0;
    const cap=document.getElementById('v1FlowCaption');if(cap)cap.textContent=`${payload?.movement_day_count||days} completed MVT days · ${dateLabel(payload?.window_start_date)} → ${dateLabel(payload?.window_end_date)} · Selling MVT vs Receipt Qty`;
    box.style.display='grid';
    const shown=sortedRows();
    box.innerHTML=shown.length?shown.map(r=>{const cls=signalClass(r.flow_signal),uom=String(r.family_group_movement_uom||''),ratio=num(r.receipt_to_selling_ratio),gap=num(r.receipt_minus_selling);return `<article class="urgent-card v1-flow-card ${cls}"><div class="urgent-top"><div><div class="urgent-name">${esc(r.family_name||'Family')}</div><div class="urgent-meta">Family ${esc(r.family_article||r.family_id||'—')} · ${esc(days+'D selected window')}</div></div><span class="pill ${cls==='over'?'warn':cls==='under'?'blue':cls==='balanced'?'good':''}">${esc(days+'D FLOW')}</span></div><div class="v1-flow-action-row"><div class="v1-flow-action ${cls}">${esc(signalLabel(r.flow_signal))}</div><div class="v1-flow-diff">DIFF ${esc(differenceLabel(r))}</div></div><div class="v1-flow-compare"><div class="v1-flow-mainmetric"><b>SELLING MVT · ${esc(days+'D')}</b><strong>${esc(fmt(r.family_group_movement_qty)+' '+uom)}</strong></div><div class="v1-flow-mainmetric"><b>RECEIPT QTY · ${esc(days+'D')}</b><strong>${esc(fmt(r.family_receipt_qty)+' '+uom)}</strong></div></div><div class="v1-flow-grid"><div class="v1-flow-metric"><b>QTY DIFFERENCE</b><strong>${esc((gap!==null&&gap>=0?'+':'')+fmt(gap)+' '+uom)}</strong></div><div class="v1-flow-metric"><b>RECEIPT / SELLING</b><strong>${esc(ratio===null?'—':fmt(ratio*100,0)+'%')}</strong></div><div class="v1-flow-metric metric"><b>EFFECTIVE OH</b><strong><span>${esc(fmt(r.effective_oh)+' '+String(r.effective_oh_uom||uom))}</span></strong></div><div class="v1-flow-metric"><b>SELL AVG / DAY</b><strong>${esc(fmt(r.family_group_avg_qty_day)+' '+uom+'/day')}</strong></div></div><div class="v1-flow-reason">${esc(reason(r))}</div><div class="v1-flow-range">Window: ${esc(dateLabel(r.window_start_date||payload?.window_start_date))} → ${esc(dateLabel(r.window_end_date||payload?.window_end_date))} · Receipt days: ${esc(r.family_receipt_day_count??'—')} · Last receipt in window: ${esc(dateLabel(r.last_receipt_date))}</div></article>`}).join(''):'<div class="empty">No Stock Flow rows for this selected window.</div>';
  }
  async function load(force){
    ensure();if(mode!=='flow'||q())return;const key=String(days);if(!force&&cache.has(key)){payload=cache.get(key);rows=payload.rows||[];render();return}if(loading)return;loading=true;const box=list();if(box)box.innerHTML='<div class="loading">Loading selected-window Selling MVT vs Receipt Qty…</div>';
    try{const r=await fetch('/app/yipman-v1-rc/api/stock-flow?days='+days+'&limit=120&_ts='+Date.now(),{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw new Error((await r.text().catch(()=>''))||('HTTP '+r.status));payload=await r.json();rows=payload.rows||[];cache.set(key,payload);render()}catch(e){if(box&&mode==='flow'&&!q())box.innerHTML='<div class="empty">Stock Flow unavailable · '+esc(e.message||String(e))+'</div>'}finally{loading=false}
  }
  ensure();
  const base=window.renderUrgent;
  if(typeof base==='function')window.renderUrgent=function(){base.apply(this,arguments);if(mode==='flow'&&!q())setTimeout(()=>{if(payload)render();else load(false)},0)};
  const search=document.getElementById('quickSearch');if(search)search.addEventListener('input',()=>setTimeout(()=>{if(!q()){if(mode==='flow'){if(payload)render();else load(false)}else if(typeof window.renderUrgent==='function')window.renderUrgent()}},0),true);
  const clear=document.getElementById('quickClear');if(clear)clear.addEventListener('click',()=>setTimeout(()=>{if(mode==='flow'){if(payload)render();else load(false)}},30),true);
  setTimeout(()=>load(false),40);
})();
</script>
'''


def polish_stock_flow_home_html(html: str) -> str:
    if 'yipmanV1StockFlowHomeScript' in html:
        return html
    html = html.replace('</head>', _STYLE + '\n</head>', 1)
    return html.replace('</body>', _SCRIPT + '\n</body>', 1)
