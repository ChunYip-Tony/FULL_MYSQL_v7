from __future__ import annotations

"""RC-only interaction layer for Mobile V1 exact-mock shell.

Adds:
- suggestion-card -> focused detail overlay
- touch-to-edit Effective OH everywhere it is displayed
- True Stock persistence through the existing PI endpoint
- full page recalculation/reload after True Stock save, restoring the user's page/filter/date context
"""

_STYLE = r'''
<style id="yipmanV1InteractionFixStyle">
#urgentList .urgent-card,
#regularResults .card,
#priceQueue .direct-card,
#priceQueue .family-card,
#quickResults .quick-result{
  cursor:pointer;
  touch-action:manipulation;
}
#urgentList .urgent-card:active,
#regularResults .card:active,
#priceQueue .direct-card:active,
#priceQueue .family-card:active,
#quickResults .quick-result:active{transform:scale(.997)}
.v1-oh-editable{
  position:relative;
  cursor:pointer!important;
  border-color:#3f6f94!important;
  background:linear-gradient(180deg,#112535,#101820)!important;
  box-shadow:inset 0 0 0 1px rgba(79,161,255,.08);
}
.v1-oh-editable::after{
  content:"TAP TO EDIT";
  display:block;
  margin-top:4px;
  color:#6fb7f0;
  font-size:6px;
  font-weight:1000;
  letter-spacing:.06em;
}
.v1-oh-editable.v1-true-stock-active::after{
  content:"TRUE STOCK ACTIVE · TAP TO EDIT";
  color:#83ca98;
}
.v1-detail-overlay{
  position:fixed;inset:0;z-index:140;background:#0b1117;color:#f1f5f8;
  display:none;overflow:auto;padding:0 12px calc(28px + env(safe-area-inset-bottom));
}
.v1-detail-overlay.open{display:block}
.v1-detail-top{
  position:sticky;top:0;z-index:4;background:rgba(11,17,23,.97);backdrop-filter:blur(12px);
  display:grid;grid-template-columns:44px minmax(0,1fr) auto;align-items:center;gap:8px;
  padding:10px 0 8px;border-bottom:1px solid #202d38;
}
.v1-detail-back{
  width:42px;height:42px;border:1px solid #334351;border-radius:12px;background:#111922;
  color:#fff;font-size:25px;font-weight:1000
}
.v1-detail-kicker{font-size:8px;color:#7e8e9c;font-weight:1000;letter-spacing:.05em}
.v1-detail-title{font-size:20px;font-weight:1000;line-height:1.05;margin-top:2px}
.v1-detail-status{
  padding:6px 9px;border:1px solid #4b6073;border-radius:999px;background:#142332;
  color:#b9d9f2;font-size:8px;font-weight:1000
}
.v1-detail-body{padding-top:11px;max-width:720px;margin:auto}
.v1-detail-id{
  display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:9px
}
.v1-detail-id>div,.v1-detail-metrics>div{
  border:1px solid #2d3b47;border-radius:11px;background:#111920;padding:8px;min-width:0
}
.v1-detail-id b,.v1-detail-metrics b{
  display:block;color:#788996;font-size:7px
}
.v1-detail-id span,.v1-detail-metrics span{
  display:block;margin-top:4px;font-size:10px;font-weight:1000;overflow-wrap:anywhere
}
.v1-detail-decision{
  border:1px solid #3a4c5c;border-radius:15px;background:linear-gradient(180deg,#182632,#141e27);
  padding:13px;margin-bottom:9px
}
.v1-detail-decision small{color:#8495a4;font-size:8px;font-weight:1000}
.v1-detail-decision strong{display:block;font-size:23px;line-height:1.05;margin-top:5px}
.v1-detail-decision p{margin:7px 0 0;color:#aeb9c3;font-size:11px;line-height:1.35;font-weight:750}
.v1-detail-oh{
  width:100%;border:1px solid #3f6f94;border-radius:14px;background:linear-gradient(180deg,#112535,#101820);
  color:#fff;padding:12px;text-align:left;margin:0 0 9px
}
.v1-detail-oh small{display:block;color:#7caed1;font-size:8px;font-weight:1000}
.v1-detail-oh strong{display:block;font-size:25px;margin-top:4px}
.v1-detail-oh span{display:block;color:#77b5e4;font-size:8px;font-weight:900;margin-top:4px}
.v1-detail-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:9px}
.v1-detail-note{
  border:1px solid #2c3945;border-radius:13px;background:#111820;padding:11px;
  color:#aab6c0;font-size:10px;line-height:1.4
}
.v1-detail-loading{padding:28px 10px;text-align:center;color:#80909e;font-size:11px;font-weight:900}
.v1-stock-backdrop{
  position:fixed;inset:0;z-index:180;background:rgba(0,0,0,.7);display:none;align-items:flex-end;justify-content:center
}
.v1-stock-backdrop.open{display:flex}
.v1-stock-sheet{
  width:min(100%,680px);background:#17212b;border:1px solid #3a4855;border-radius:22px 22px 0 0;
  padding:17px 14px calc(17px + env(safe-area-inset-bottom));box-shadow:0 -16px 45px rgba(0,0,0,.45)
}
.v1-stock-sheet h3{margin:0;font-size:20px}
.v1-stock-meta{margin-top:4px;color:#8999a7;font-size:10px;font-weight:850}
.v1-stock-current{
  margin-top:11px;border:1px solid #2e3e4b;border-radius:12px;background:#101820;padding:10px
}
.v1-stock-current small{display:block;color:#758794;font-size:7px;font-weight:1000}
.v1-stock-current strong{display:block;font-size:22px;margin-top:3px}
.v1-stock-input{
  width:100%;height:58px;margin-top:10px;border:2px solid #4e86b0;border-radius:13px;background:#0c141b;
  color:#fff;padding:8px 12px;font-size:24px;font-weight:1000;outline:0
}
.v1-stock-uom{margin-top:5px;color:#7e8f9c;font-size:9px;font-weight:900}
.v1-stock-actions{display:grid;grid-template-columns:1fr 1.4fr;gap:8px;margin-top:11px}
.v1-stock-actions button{min-height:50px;border-radius:12px;font-size:11px;font-weight:1000}
.v1-stock-cancel{border:1px solid #3b4955;background:#101820;color:#aeb9c3}
.v1-stock-save{border:1px solid #3c76aa;background:#1b5687;color:#fff}
.v1-stock-save:disabled{opacity:.55}
.v1-stock-status{margin-top:8px;min-height:17px;color:#8fa1ae;font-size:9px;font-weight:850}
.v1-stock-status.error{color:#ff8d97}
.v1-stock-status.good{color:#8fd3a0}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1InteractionFixScript">
(function(){
  'use strict';
  const API={
    get:async function(url){
      const r=await fetch(url,{credentials:'same-origin',cache:'no-store'});
      if(!r.ok) throw new Error((await r.text().catch(()=>''))||('HTTP '+r.status));
      return r.json();
    },
    post:async function(url,body){
      const r=await fetch(url,{
        method:'POST',credentials:'same-origin',cache:'no-store',
        headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
      });
      if(!r.ok) throw new Error((await r.text().catch(()=>''))||('HTTP '+r.status));
      return r.json().catch(()=>({}));
    }
  };
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=v=>{const n=Number(v);return Number.isFinite(n)?'$'+n.toFixed(2):'—'};
  const fmt=v=>{const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:1}):'—'};
  const text=(el,sel)=>String(el?.querySelector(sel)?.textContent||'').trim();

  function currentPage(){
    return document.querySelector('.page.active')?.id || 'quick';
  }
  function currentFilter(){
    return document.querySelector('#price [data-pf].active')?.dataset?.pf || 'all';
  }
  function rememberResume(){
    const state={
      page:currentPage(),
      pf:currentFilter(),
      delivery:document.getElementById('deliveryDate')?.value||'',
      next:document.getElementById('nextDeliveryDate')?.value||'',
      quick:document.getElementById('quickSearch')?.value||''
    };
    sessionStorage.setItem('yipman-v1-resume-after-stock',JSON.stringify(state));
  }
  function restoreResume(){
    const raw=sessionStorage.getItem('yipman-v1-resume-after-stock');
    if(!raw) return;
    sessionStorage.removeItem('yipman-v1-resume-after-stock');
    let s={}; try{s=JSON.parse(raw)||{}}catch(_){}
    setTimeout(()=>{
      if(s.page==='price'){
        document.querySelector('[data-nav="price"]')?.click();
        setTimeout(()=>document.querySelector('#price [data-pf="'+CSS.escape(s.pf||'all')+'"]')?.click(),180);
      }else if(s.page==='regular'){
        document.querySelector('[data-nav="ordering"]')?.click();
        setTimeout(()=>{
          document.querySelector('[data-open="regular"]')?.click();
          setTimeout(()=>{
            const d=document.getElementById('deliveryDate'),n=document.getElementById('nextDeliveryDate');
            if(d&&s.delivery)d.value=s.delivery;
            if(n&&s.next)n.value=s.next;
            d?.dispatchEvent(new Event('change',{bubbles:true}));
          },180);
        },100);
      }else if(s.page==='ordering'){
        document.querySelector('[data-nav="ordering"]')?.click();
      }else if(s.page==='more'){
        document.querySelector('[data-nav="more"]')?.click();
      }else{
        document.querySelector('[data-nav="quick"]')?.click();
        if(s.quick){
          setTimeout(()=>{
            const q=document.getElementById('quickSearch');
            if(q){q.value=s.quick;q.dispatchEvent(new Event('input',{bubbles:true}))}
          },180);
        }
      }
    },420);
  }

  function extractIdentity(card){
    const all=String(card?.innerText||'').replace(/\s+/g,' ').trim();
    const family=(all.match(/Family\s+([0-9]{4,12})/i)||[])[1]||'';
    const upc=(all.match(/UPC\s*#?\s*([0-9]{8,14})/i)||[])[1]||'';
    const receiving=(all.match(/Receiving\s+([0-9]{4,12})/i)||[])[1]||'';
    const article=(all.match(/Article\s+([0-9]{4,14})/i)||[])[1]||receiving||family;
    const name=text(card,'.urgent-name')||text(card,'.card-title')||text(card,'.result-name')||text(card,'.family-title')||text(card,'h3')||'Item';
    const action=text(card,'.urgent-action')||text(card,'.order-main')||text(card,'.action-value')||text(card,'.pill')||'Review';
    const why=(text(card,'.urgent-why')||text(card,'.why')).replace(/^Why:\s*/i,'');
    return {family,upc,article,name,action,why};
  }
  function ohElementFromCard(card){
    return [...card.querySelectorAll('.metric,.stat')].find(x=>/^(EFFECTIVE OH|EFF OH)\b/i.test(text(x,'b')));
  }
  function ohFromElement(el){
    const raw=text(el,'span');
    const m=raw.match(/(-?\d+(?:\.\d+)?)\s*([A-Za-z]+)?/);
    return {qty:m?Number(m[1]):null,uom:(m?.[2]||'').toUpperCase()};
  }
  function markEditableOH(root=document){
    root.querySelectorAll('.metric,.stat').forEach(el=>{
      const label=text(el,'b');
      if(/^(EFFECTIVE OH|EFF OH)\b/i.test(label)){
        el.classList.add('v1-oh-editable');
        el.setAttribute('role','button');
        el.setAttribute('tabindex','0');
      }
    });
  }

  let detailCtx=null;
  function ensureDetail(){
    if(document.getElementById('v1DetailOverlay')) return;
    const el=document.createElement('div');
    el.className='v1-detail-overlay';
    el.id='v1DetailOverlay';
    el.innerHTML=`
      <div class="v1-detail-top">
        <button type="button" class="v1-detail-back" id="v1DetailBack">‹</button>
        <div><div class="v1-detail-kicker">ACTION DETAIL</div><div class="v1-detail-title" id="v1DetailTitle">Item</div></div>
        <span class="v1-detail-status" id="v1DetailStatus">LIVE</span>
      </div>
      <div class="v1-detail-body" id="v1DetailBody"></div>`;
    document.body.appendChild(el);
    document.getElementById('v1DetailBack').onclick=()=>el.classList.remove('open');
  }

  async function openDetail(card){
    ensureDetail();
    const id=extractIdentity(card);
    const overlay=document.getElementById('v1DetailOverlay');
    const body=document.getElementById('v1DetailBody');
    document.getElementById('v1DetailTitle').textContent=id.name;
    body.innerHTML='<div class="v1-detail-loading">Loading current item detail…</div>';
    overlay.classList.add('open');

    let live=null;
    if(id.upc){
      try{live=await API.get('/v1/app/v2/upc/'+encodeURIComponent(id.upc))}catch(_){}
    }
    const eff=live?.effective_oh||{};
    const sys=live?.system_oh||{};
    const q7=live?.qty_7d||{};
    const family=String(live?.family_article_number||id.family||'');
    const upc=String(live?.upc||id.upc||'');
    const article=String(id.article||family||'');
    const domEl=ohElementFromCard(card);
    const domOh=domEl?ohFromElement(domEl):{qty:null,uom:''};
    const uom=String(eff?.uom||live?.selling_uom||domOh.uom||'').toUpperCase();
    const qty=Number.isFinite(Number(eff?.quantity))?Number(eff.quantity):domOh.qty;
    detailCtx={family,upc,article,name:live?.upc_name||id.name,uom,qty};

    body.innerHTML=`
      <div class="v1-detail-id">
        <div><b>FAMILY</b><span>${esc(family||'—')}</span></div>
        <div><b>UPC</b><span>${esc(upc||'—')}</span></div>
        <div><b>ARTICLE</b><span>${esc(article||'—')}</span></div>
      </div>
      <div class="v1-detail-decision">
        <small>PRIMARY DECISION</small>
        <strong>${esc(id.action||'Review')}</strong>
        <p>${esc(id.why||'Open this item to review the current operational decision and supporting data.')}</p>
      </div>
      <button type="button" class="v1-detail-oh" id="v1DetailOh">
        <small>EFFECTIVE OH · TOUCH TO ENTER TRUE STOCK</small>
        <strong>${qty===null||qty===undefined?'—':fmt(qty)} ${esc(uom)}</strong>
        <span>Saved True Stock becomes the Effective OH and recalculates Price + Ordering.</span>
      </button>
      <div class="v1-detail-metrics">
        <div><b>SYSTEM OH</b><span>${fmt(sys?.quantity)} ${esc(sys?.uom||uom)}</span></div>
        <div><b>CURRENT PRICE</b><span>${money(live?.current_price)}</span></div>
        <div><b>CURRENT COST</b><span>${money(live?.current_cost_per_selling_unit)}</span></div>
        <div><b>7D SALES</b><span>${fmt(q7?.sold_quantity??live?.qty_7d)} ${esc(live?.qty_uom||uom)}</span></div>
        <div><b>7D AVG</b><span>${fmt(live?.upc_velocity_7d)} / day</span></div>
        <div><b>DOS</b><span>${fmt(live?.dos)}</span></div>
      </div>
      <div class="v1-detail-note">
        ${live
          ? 'Live FULL MYSQL detail loaded. Effective OH is authoritative for this view; entering True Stock records a physical count and forces a fresh recalculation after save.'
          : 'Family/action detail opened from the current suggestion card. Enter True Stock from Effective OH to update the authoritative inventory position and recalculate suggestions.'}
      </div>`;
    document.getElementById('v1DetailOh').onclick=()=>openStockEditor(detailCtx);
  }

  let stockCtx=null;
  function ensureStockSheet(){
    if(document.getElementById('v1StockBackdrop')) return;
    const el=document.createElement('div');
    el.className='v1-stock-backdrop';
    el.id='v1StockBackdrop';
    el.innerHTML=`
      <div class="v1-stock-sheet">
        <h3>Enter True Stock</h3>
        <div class="v1-stock-meta" id="v1StockMeta">Family</div>
        <div class="v1-stock-current"><small>CURRENT EFFECTIVE OH</small><strong id="v1StockCurrent">—</strong></div>
        <input id="v1StockInput" class="v1-stock-input" type="number" inputmode="decimal" min="0" step="0.1" aria-label="True Stock quantity">
        <div class="v1-stock-uom" id="v1StockUom"></div>
        <div class="v1-stock-actions"><button class="v1-stock-cancel" id="v1StockCancel" type="button">Cancel</button><button class="v1-stock-save" id="v1StockSave" type="button">Save + Recalculate</button></div>
        <div class="v1-stock-status" id="v1StockStatus"></div>
      </div>`;
    document.body.appendChild(el);
    document.getElementById('v1StockCancel').onclick=()=>el.classList.remove('open');
    document.getElementById('v1StockSave').onclick=saveTrueStock;
    el.addEventListener('click',e=>{if(e.target===el)el.classList.remove('open')});
  }
  function openStockEditor(ctx){
    if(!ctx)return;
    ensureStockSheet();
    stockCtx={...ctx};
    const sheet=document.getElementById('v1StockBackdrop');
    const input=document.getElementById('v1StockInput');
    const status=document.getElementById('v1StockStatus');
    document.getElementById('v1StockMeta').textContent=(ctx.name||'Item')+' · Family '+(ctx.family||'—');
    document.getElementById('v1StockCurrent').textContent=(ctx.qty===null||ctx.qty===undefined?'—':fmt(ctx.qty))+' '+(ctx.uom||'');
    document.getElementById('v1StockUom').textContent=ctx.uom?'Selling / family UOM: '+ctx.uom:'UOM unavailable — save is blocked until the item UOM is resolved.';
    input.value=ctx.qty===null||ctx.qty===undefined?'':String(ctx.qty);
    status.textContent='';
    status.className='v1-stock-status';
    const save=document.getElementById('v1StockSave');
    save.disabled=false;save.textContent='Save + Recalculate';
    sheet.classList.add('open');
    setTimeout(()=>{input.focus();input.select()},40);
  }
  function updateFamilyOhDom(family,qty,uom){
    if(!family) return;
    const cards=[...document.querySelectorAll('.urgent-card,#regularResults .card,#priceQueue .direct-card,#priceQueue .family-card,.quick-result')];
    cards.forEach(card=>{
      if(extractIdentity(card).family!==family) return;
      const oh=ohElementFromCard(card);
      if(oh){
        const span=oh.querySelector('span');
        if(span)span.textContent=fmt(qty)+' '+uom;
        oh.classList.add('v1-true-stock-active','v1-oh-editable');
      }
    });
    if(detailCtx?.family===family){
      detailCtx.qty=qty;detailCtx.uom=uom;
      const d=document.querySelector('#v1DetailOh strong');
      if(d)d.textContent=fmt(qty)+' '+uom;
    }
  }
  async function saveTrueStock(){
    const ctx=stockCtx||{};
    const input=document.getElementById('v1StockInput');
    const save=document.getElementById('v1StockSave');
    const status=document.getElementById('v1StockStatus');
    const qty=Number(input.value);
    const family=String(ctx.family||'').trim();
    const uom=String(ctx.uom||'').trim().toUpperCase();
    status.className='v1-stock-status';
    if(!family){status.textContent='Family Article unavailable. Cannot safely save True Stock.';status.classList.add('error');return}
    if(!uom){status.textContent='Selling UOM unavailable. Cannot safely save True Stock.';status.classList.add('error');return}
    if(!Number.isFinite(qty)||qty<0){status.textContent='Enter a valid physical True Stock quantity.';status.classList.add('error');input.focus();return}
    save.disabled=true;save.textContent='Saving…';status.textContent='Recording True Stock and rebuilding Effective OH…';
    try{
      await API.post('/v1/app/v2/pi/'+encodeURIComponent(family)+'/true-stock',{
        true_stock:qty,uom:uom,note:'YipMan Mobile V1 RC physical True Stock'
      });
      updateFamilyOhDom(family,qty,uom);
      status.textContent='Saved. Recalculating Price + Ordering with the new Effective OH…';
      status.classList.add('good');
      rememberResume();
      setTimeout(()=>location.reload(),420);
    }catch(e){
      status.textContent='Save failed · '+e.message;
      status.classList.add('error');
      save.disabled=false;save.textContent='Save + Recalculate';
    }
  }

  function contextForOh(el){
    const card=el.closest('.urgent-card,#regularResults .card,#priceQueue .direct-card,#priceQueue .family-card,.quick-result');
    if(!card)return null;
    const id=extractIdentity(card),oh=ohFromElement(el);
    return {family:id.family,upc:id.upc,article:id.article,name:id.name,uom:oh.uom,qty:oh.qty};
  }

  document.addEventListener('click',e=>{
    const oh=e.target.closest('.v1-oh-editable');
    if(oh){
      e.preventDefault();e.stopPropagation();
      openStockEditor(contextForOh(oh));
      return;
    }
    if(e.target.closest('button,input,select,textarea,a')) return;
    const card=e.target.closest('.urgent-card,#regularResults .card,#priceQueue .direct-card,#priceQueue .family-card,.quick-result');
    if(card){e.preventDefault();openDetail(card)}
  },true);

  document.addEventListener('keydown',e=>{
    if((e.key==='Enter'||e.key===' ')&&e.target.classList?.contains('v1-oh-editable')){
      e.preventDefault();openStockEditor(contextForOh(e.target));
    }
  });

  let raf=0;
  const observer=new MutationObserver(()=>{
    if(raf)return;
    raf=requestAnimationFrame(()=>{raf=0;markEditableOH(document)});
  });
  observer.observe(document.body,{childList:true,subtree:true});
  markEditableOH(document);
  ensureDetail();
  ensureStockSheet();
  restoreResume();
})();
</script>
'''

def polish_interactions_html(html: str) -> str:
    if 'yipmanV1InteractionFixStyle' in html:
        return html
    html = html.replace('</head>', _STYLE + '</head>', 1)
    html = html.replace('</body>', _SCRIPT + '</body>', 1)
    return html
