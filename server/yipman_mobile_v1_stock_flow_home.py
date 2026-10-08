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
.v1-flow-controls{display:grid;grid-template-columns:auto 1fr;gap:8px;align-items:center;margin-bottom:8px}
.v1-flow-window{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
.v1-flow-window button{min-width:48px;height:36px;border:1px solid #344653;border-radius:11px;background:#101820;color:#95a5b1;font-size:12px;font-weight:1000}
.v1-flow-window button.active{background:#214d70;color:#fff;border-color:#528ab2}
.v1-flow-caption{color:#8092a0;font-size:11px;font-weight:850;line-height:1.25;text-align:right}
.v1-flow-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:0 0 9px}
.v1-flow-summary div{border:1px solid #2d3d49;border-radius:11px;background:#101820;padding:7px 5px;text-align:center}
.v1-flow-summary b{display:block;font-size:18px}.v1-flow-summary span{display:block;margin-top:2px;color:#8295a3;font-size:9px;font-weight:1000}
.v1-flow-card{border-left-width:6px!important}.v1-flow-card.over{border-left-color:#e0a84d!important}.v1-flow-card.under{border-left-color:#67aee4!important}.v1-flow-card.balanced{border-left-color:#67bb7b!important}.v1-flow-card.noactivity{border-left-color:#687986!important}
.v1-flow-action{font-size:22px;font-weight:1000;margin-top:8px}.v1-flow-action.over{color:#f1cb7a}.v1-flow-action.under{color:#9bd1f6}.v1-flow-action.balanced{color:#9bd6aa}
.v1-flow-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:9px}
.v1-flow-metric{border:1px solid #2c3c48;border-radius:11px;background:#0f1820;padding:8px;min-width:0}
.v1-flow-metric b{display:block;color:#7f92a0;font-size:9px;font-weight:1000}.v1-flow-metric strong{display:block;margin-top:3px;color:#f0f5f8;font-size:16px;font-weight:1000;overflow-wrap:anywhere}
.v1-flow-reason{margin-top:8px;color:#a9b7c1;font-size:13px;line-height:1.35;font-weight:800}
.v1-flow-range{margin-top:4px;color:#6f8290;font-size:10px;font-weight:850}
@media(max-width:390px){.v1-flow-action{font-size:20px}.v1-flow-metric strong{font-size:15px}}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1StockFlowHomeScript">
(()=>{
  'use strict';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
  const fmt=(v,d=1)=>{const x=num(v);return x===null?'—':x.toLocaleString(undefined,{maximumFractionDigits:d})};
  let mode='flow',days=7,rows=[],payload=null,loading=false;
  const cache=new Map();
  const q=()=>String(document.getElementById('quickSearch')?.value||'').trim();
  const list=()=>document.getElementById('urgentList');

  function dateLabel(v){
    if(!v)return'—';if(typeof window.yipmanDateLabel==='function')return window.yipmanDateLabel(String(v));
    const m=String(v).match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return String(v);const d=new Date(+m[1],+m[2]-1,+m[3]);return ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()]+' · '+(+m[2])+'/'+(+m[3])+'/'+m[1];
  }
  function ensure(){
    const top=document.querySelector('#quick .top');if(!top||document.getElementById('v1HomeSwitch'))return;
    const wrap=document.createElement('div');wrap.innerHTML=`<div id="v1HomeSwitch" class="v1-home-switch"><button data-home-mode="flow" class="active">STOCK FLOW</button><button data-home-mode="actions">ACTIONS</button></div><div id="v1FlowControls" class="v1-flow-controls"><div class="v1-flow-window"><button data-flow-days="7" class="active">7D</button><button data-flow-days="14">14D</button><button data-flow-days="28">28D</button></div><div class="v1-flow-caption" id="v1FlowCaption">Selling MVT vs receipts</div></div><div id="v1FlowSummary" class="v1-flow-summary"><div><b>—</b><span>OVER WATCH</span></div><div><b>—</b><span>UNDER WATCH</span></div><div><b>—</b><span>BALANCED</span></div></div>`;
    while(wrap.firstChild)top.insertBefore(wrap.firstChild,top.firstChild);
    top.querySelectorAll('[data-home-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.homeMode));
    top.querySelectorAll('[data-flow-days]').forEach(b=>b.onclick=()=>{days=Number(b.dataset.flowDays);top.querySelectorAll('[data-flow-days]').forEach(x=>x.classList.toggle('active',x===b));load(true)});
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
  function reason(r){
    const sell=num(r.family_group_movement_qty)||0,rec=num(r.family_receipt_qty)||0,gap=rec-sell;
    if(r.flow_signal==='OVER_ORDER_WATCH')return sell===0?`Receipts entered this window with no supported selling movement.`:`Receipts exceed selling MVT by ${fmt(Math.abs(gap))} ${r.family_group_movement_uom||''}. Review upcoming orders and current OH.`;
    if(r.flow_signal==='UNDER_ORDER_WATCH')return `Selling MVT exceeds receipts by ${fmt(Math.abs(gap))} ${r.family_group_movement_uom||''}. Check coverage and next order.`;
    if(r.flow_signal==='BALANCED')return `Recent receipts and selling MVT are within the normal comparison band.`;
    return `No supported receipt or selling movement in this window.`;
  }
  function render(){
    if(mode!=='flow'||q())return;syncChrome();const box=list();if(!box)return;
    const c=payload?.signal_counts||{};const sums=document.querySelectorAll('#v1FlowSummary b');if(sums[0])sums[0].textContent=c.OVER_ORDER_WATCH||0;if(sums[1])sums[1].textContent=c.UNDER_ORDER_WATCH||0;if(sums[2])sums[2].textContent=c.BALANCED||0;
    const cap=document.getElementById('v1FlowCaption');if(cap)cap.textContent=`${days}D · ${dateLabel(payload?.window_start_date)} → ${dateLabel(payload?.window_end_date)}`;
    box.style.display='grid';
    box.innerHTML=rows.length?rows.map(r=>{const cls=signalClass(r.flow_signal),uom=String(r.family_group_movement_uom||'');const ratio=num(r.receipt_to_selling_ratio);return `<article class="urgent-card v1-flow-card ${cls}"><div class="urgent-top"><div><div class="urgent-name">${esc(r.family_name||'Family')}</div><div class="urgent-meta">Family ${esc(r.family_article||r.family_id||'—')} · Article ${esc(r.family_article||'—')}</div></div><span class="pill ${cls==='over'?'warn':cls==='under'?'blue':cls==='balanced'?'good':''}">${esc(days+'D FLOW')}</span></div><div class="v1-flow-action ${cls}">${esc(signalLabel(r.flow_signal))}</div><div class="v1-flow-reason">${esc(reason(r))}</div><div class="v1-flow-grid"><div class="v1-flow-metric"><b>SELLING MVT</b><strong>${esc(fmt(r.family_group_movement_qty)+' '+uom)}</strong></div><div class="v1-flow-metric"><b>RECEIPTS</b><strong>${esc(fmt(r.family_receipt_qty)+' '+uom)}</strong></div><div class="v1-flow-metric"><b>NET FLOW</b><strong>${esc((num(r.receipt_minus_selling)>=0?'+':'')+fmt(r.receipt_minus_selling)+' '+uom)}</strong></div><div class="v1-flow-metric metric"><b>EFFECTIVE OH</b><strong><span>${esc(fmt(r.effective_oh)+' '+String(r.effective_oh_uom||uom))}</span></strong></div><div class="v1-flow-metric"><b>AVG / DAY</b><strong>${esc(fmt(r.family_group_avg_qty_day)+' '+uom+'/day')}</strong></div><div class="v1-flow-metric"><b>RECEIPT / SELLING</b><strong>${esc(ratio===null?'—':fmt(ratio*100,0)+'%')}</strong></div></div><div class="v1-flow-range">Last receipt: ${esc(dateLabel(r.last_receipt_date))} · Flow signal only; final order suggestion remains in Ordering.</div></article>`}).join(''):'<div class="empty">No Stock Flow rows for this window.</div>';
  }
  async function load(force){
    ensure();if(mode!=='flow'||q())return;const key=String(days);if(!force&&cache.has(key)){payload=cache.get(key);rows=payload.rows||[];render();return}if(loading)return;loading=true;const box=list();if(box)box.innerHTML='<div class="loading">Loading Stock Flow comparison…</div>';
    try{const r=await fetch('/app/yipman-v1-rc/api/stock-flow?days='+days+'&limit=80&_ts='+Date.now(),{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw new Error((await r.text().catch(()=>''))||('HTTP '+r.status));payload=await r.json();rows=payload.rows||[];cache.set(key,payload);render()}catch(e){if(box&&mode==='flow'&&!q())box.innerHTML='<div class="empty">Stock Flow unavailable · '+esc(e.message||String(e))+'</div>'}finally{loading=false}
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
