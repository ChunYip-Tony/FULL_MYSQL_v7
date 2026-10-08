from __future__ import annotations

"""RC-only UPC price-test progress presentation.

Progress is owned by the observed UPC price state, not merely by the existence
of a recommendation. A suggested test remains STEP 0 until the canonical current
price actually changes to the suggested target. Once activated, completed valid
POS days and backend lifecycle metrics are shown. The panel is collapsed by
default so Price Review can show substantially more than one card per screen.
"""


_STYLE = r'''
<style id="yipmanV1PriceProgressStyle">
.price-progress{margin-top:6px;border:1px solid #314354;border-radius:11px;background:#101820;text-align:left;overflow:hidden}
.price-progress-summary{width:100%;border:0;background:transparent;color:inherit;padding:8px 9px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;text-align:left}
.price-progress-summary-main{min-width:0}.price-progress-title{font-size:10px;color:#92a3b0;font-weight:1000;letter-spacing:.03em}.price-progress-purpose{margin-top:2px;color:#a9b6c0;font-size:10px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.price-progress-status{font-size:11px;font-weight:1000;color:#d7e8f6;text-align:right;white-space:nowrap}.price-progress-chevron{margin-left:5px;color:#6eaee0}
.price-progress.step0{border-color:#6a582e;background:#18170f}.price-progress.step0 .price-progress-status{color:#f2cf7e}.price-progress.step0 .price-progress-purpose{color:#c7b98f}
.price-progress-body{display:none;border-top:1px solid #293744;padding:8px 9px 9px}.price-progress.open .price-progress-body{display:block}
.price-progress-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
.price-progress-grid+ .price-progress-grid{margin-top:5px}.price-progress-grid>div{border:1px solid #293744;border-radius:9px;background:#0d151c;padding:6px 4px;text-align:center;min-width:0}
.price-progress-grid b{display:block;color:#7d8f9d;font-size:7px}.price-progress-grid span{display:block;margin-top:2px;font-size:11px;font-weight:1000;overflow-wrap:anywhere}
.price-progress-reason{margin-top:6px;color:#abb8c3;font-size:10px;line-height:1.28;font-weight:760}.price-progress-next{margin-top:6px;border-top:1px solid #293744;padding-top:6px;color:#83c5f2;font-size:9px;font-weight:950}
.price-progress-step0-line{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:6px;margin-top:1px}.price-progress-step0-line>div{border:1px solid #3d3a29;border-radius:9px;background:#12140f;padding:6px;text-align:center}.price-progress-step0-line b{display:block;font-size:7px;color:#998c69}.price-progress-step0-line span{display:block;font-size:12px;font-weight:1000;margin-top:2px}.price-progress-arrow{color:#d7b55e;font-size:14px;font-weight:1000;text-align:center}
</style>
'''


_SCRIPT_HELPERS = r'''
let tprProgressLoaded=false;
let tprProgressLoading=false;
let tprProgressByUpc=new Map();
function progressUpcKey(v){
  const d=String(v??'').replace(/\D/g,'').replace(/^0+/,'');
  return d||'';
}
function progressNum(v){
  if(v===null||v===undefined||v==='')return null;
  const n=Number(v);return Number.isFinite(n)?n:null;
}
function pctText(v){
  const n=Number(v);
  if(!Number.isFinite(n))return '—';
  return (n>0?'+':'')+n.toFixed(1)+'%';
}
function dayText(v){
  const n=Number(v);
  return Number.isFinite(n)?n.toFixed(n%1?1:0):'—';
}
function samePrice(a,b){
  const x=progressNum(a),y=progressNum(b);
  return x!==null&&y!==null&&Math.abs(x-y)<0.011;
}
function progressCurrentType(r){
  return String(r?.current_price_type??r?.current_type??r?.observed_price_type??'').trim().toUpperCase();
}
function progressTargetType(r){
  try{return String(priceType(r)||'').trim().toUpperCase()}catch(_){return''}
}
function progressActivation(r,p){
  const current=progressNum(currentPrice(r));
  const target=progressNum(suggestedPrice(r));
  const currentType=progressCurrentType(r),targetType=progressTargetType(r);
  const backendPrice=progressNum(p?.current_price??p?.tpr_price??p?.active_price);
  const priceChangeRequired=current!==null&&target!==null&&!samePrice(current,target);
  const backendPriceMismatch=backendPrice!==null&&current!==null&&!samePrice(backendPrice,current);
  const typeChangeRequired=!!currentType&&!!targetType&&currentType!==targetType&&targetType!=='KEEP';
  return {
    active:!priceChangeRequired&&!backendPriceMismatch&&!typeChangeRequired,
    current,target,currentType,targetType,backendPrice,
    priceChangeRequired,backendPriceMismatch,typeChangeRequired
  };
}
async function loadTprProgress(){
  if(tprProgressLoaded||tprProgressLoading)return;
  tprProgressLoading=true;
  try{
    const d=await api('/v1/yipman/current-tpr-review?category=ALL&limit=1000');
    const rows=d?.rows||[];
    tprProgressByUpc=new Map();
    rows.forEach(x=>{
      const k=progressUpcKey(x?.upc??x?.ean_upc??x?.ean);
      if(k)tprProgressByUpc.set(k,x);
    });
    tprProgressLoaded=true;
  }catch(_){
    tprProgressLoaded=false;
  }finally{
    tprProgressLoading=false;
  }
}
function priceProgressHtml(r){
  const p=tprProgressByUpc.get(progressUpcKey(upcOf(r)));
  const activation=progressActivation(r,p||{});
  const hasTarget=activation.target!==null;
  if(!p&&!hasTarget)return '';

  if(!activation.active){
    const current=activation.current===null?'—':money(activation.current);
    const target=activation.target===null?'—':money(activation.target);
    let wait='Waiting for canonical current price to detect the suggested target.';
    if(activation.typeChangeRequired&&!activation.priceChangeRequired)wait='Waiting for the suggested price type to become the observed current state.';
    if(activation.backendPriceMismatch)wait='The backend lifecycle price does not match the current observed UPC price, so test days are not counted.';
    return `<div class="price-progress step0">
      <button type="button" class="price-progress-summary" data-progress-toggle>
        <div class="price-progress-summary-main"><div class="price-progress-title">STEP 0 · TEST NOT STARTED</div><div class="price-progress-purpose">No performance comparison until price activation is detected</div></div>
        <div class="price-progress-status">WAITING<span class="price-progress-chevron">⌄</span></div>
      </button>
      <div class="price-progress-body">
        <div class="price-progress-step0-line"><div><b>CURRENT</b><span>${esc(current)}</span></div><div class="price-progress-arrow">→</div><div><b>TEST TARGET</b><span>${esc(target)}</span></div></div>
        <div class="price-progress-reason">${esc(wait)} Valid days stay at 0 until activation; prior/stale lifecycle metrics are not shown as current test progress.</div>
      </div>
    </div>`;
  }

  if(!p)return '';
  const rec=String(p?.recommendation_label||p?.recommendation_code||'OBSERVE').replaceAll('_',' ');
  const phase=String(p?.monitoring_phase||'LEARNING').replaceAll('_',' ');
  const purpose=String(p?.tpr_purpose_label||p?.tpr_purpose||'TPR TEST').replaceAll('_',' ');
  const gp=p?.gp_day_lift_pct;
  const vel=p?.velocity_lift_pct;
  const days=p?.completed_tpr_days??p?.tpr_supported_days??p?.current_behavior?.supported_days??p?.post_supported_days;
  const tprGp=p?.tpr_gp_per_day_3d??p?.current_behavior?.gp_per_day_current_cost;
  const baseGp=p?.baseline_gp_per_day_current_cost??p?.baseline_behavior?.gp_per_day_current_cost;
  const next=p?.suggested_regular_price??p?.suggested_tpr_price;
  const nextLabel=p?.suggested_regular_price!=null?'NEW REG':(p?.suggested_tpr_price!=null?'NEXT TPR':'NEXT');
  const clearDays=p?.projected_days_to_clear_oh;
  const needVel=p?.required_velocity_to_clear;
  const reason=String(p?.recommendation_reason||'Tracking active test on completed valid POS days.');
  const daySummary=Number.isFinite(Number(days))?`DAY ${dayText(days)}/7`:'ACTIVE';
  return `<div class="price-progress">
    <button type="button" class="price-progress-summary" data-progress-toggle>
      <div class="price-progress-summary-main"><div class="price-progress-title">TEST ACTIVE · ${esc(daySummary)}</div><div class="price-progress-purpose">${esc(purpose)} · GP$/DAY ${esc(pctText(gp))}</div></div>
      <div class="price-progress-status">${esc(rec)}<span class="price-progress-chevron">⌄</span></div>
    </button>
    <div class="price-progress-body">
      <div class="price-progress-grid">
        <div><b>VALID DAYS</b><span>${esc(dayText(days))}</span></div>
        <div><b>VELOCITY Δ</b><span>${esc(pctText(vel))}</span></div>
        <div><b>GP$/DAY Δ</b><span>${esc(pctText(gp))}</span></div>
        <div><b>TEST GP$/DAY</b><span>${tprGp==null?'—':money(tprGp)}</span></div>
        <div><b>BASE GP$/DAY</b><span>${baseGp==null?'—':money(baseGp)}</span></div>
        <div><b>${esc(nextLabel)}</b><span>${next==null?'—':money(next)}</span></div>
      </div>
      ${(clearDays!=null||needVel!=null)?`<div class="price-progress-grid"><div><b>DAYS TO CLEAR</b><span>${esc(dayText(clearDays))}</span></div><div><b>REQ VELOCITY</b><span>${needVel==null?'—':esc(fmt(needVel,1))+'/day'}</span></div><div><b>CURRENT TEST</b><span>${esc(String(p?.current_price??p?.tpr_price??'—'))}</span></div></div>`:''}
      <div class="price-progress-reason">${esc(reason)}</div>
      <div class="price-progress-next">Backend lifecycle tracking · completed valid data days only</div>
    </div>
  </div>`;
}
function wirePriceProgressToggles(){
  document.querySelectorAll('#price [data-progress-toggle]').forEach(btn=>{
    if(btn.dataset.progressBound==='1')return;
    btn.dataset.progressBound='1';
    btn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();const p=btn.closest('.price-progress');if(p)p.classList.toggle('open')});
  });
}
'''


def polish_price_progress_html(html: str) -> str:
    marker = "yipmanV1PriceProgress"
    if marker in html:
        return html

    anchor = "async function loadPrice(){"
    if anchor in html:
        html = html.replace(anchor, _SCRIPT_HELPERS + "\n" + anchor, 1)

    old_tail = "}renderPrice()}\nfunction actionablePrice"
    new_tail = "}renderPrice();wirePriceProgressToggles();if(!tprProgressLoaded&&!tprProgressLoading){loadTprProgress().then(()=>{renderPrice();wirePriceProgressToggles()}).catch(()=>{})}}\nfunction actionablePrice"
    if old_tail in html:
        html = html.replace(old_tail, new_tail, 1)

    old_card = "</div><button class=\"ignore\" data-pi=\"${esc(key)}\">Ignore 12h</button></div>`"
    new_card = "</div>${priceProgressHtml(r)}<button class=\"ignore\" data-pi=\"${esc(key)}\">Ignore 12h</button></div>`"
    if old_card in html:
        html = html.replace(old_card, new_card, 1)

    # Every filter change/search repaint needs toggle wiring too.
    html = html.replace(
        "$$('[data-pi]').forEach(b=>b.onclick=()=>{setIgnore(b.dataset.pi);renderPrice()})}}",
        "$$('[data-pi]').forEach(b=>b.onclick=()=>{setIgnore(b.dataset.pi);renderPrice()});wirePriceProgressToggles()}}",
        1,
    )

    html = html.replace("</style>", "</style>\n" + _STYLE, 1)
    html = html.replace(
        "</head>",
        f'<meta name="{marker}" content="1">\n</head>',
        1,
    )
    return html
