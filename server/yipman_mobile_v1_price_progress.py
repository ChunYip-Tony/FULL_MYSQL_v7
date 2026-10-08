from __future__ import annotations

"""RC-only UPC price-test progress presentation.

The progress panel belongs to the price action currently shown on the card.  A
backend TPR lifecycle for the same UPC must never be mistaken for progress on a
new, not-yet-applied suggestion.  Until the suggested price is actually observed
as CURRENT, the card remains STEP 0.
"""


_STYLE = r'''
<style id="yipmanV1PriceProgressStyle">
.price-progress{margin-top:7px;border:1px solid #314354;border-radius:11px;background:#101820;padding:8px;text-align:left}
.price-progress.compact-wait{border-color:#53482c;background:#17150f}
.price-progress-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.price-progress-title{font-size:11px;color:#91a2af;font-weight:1000;letter-spacing:.035em}
.price-progress-status{font-size:12px;font-weight:1000;color:#e3eef6;text-align:right;white-space:nowrap}
.price-progress-purpose{margin-top:2px;color:#8f9da9;font-size:10px;font-weight:850;line-height:1.2}
.price-progress-compact{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:5px;margin-top:6px}
.price-progress-chip{border:1px solid #293744;border-radius:9px;background:#0d151c;padding:6px;text-align:center;min-width:0}
.price-progress-chip b{display:block;color:#758795;font-size:8px}.price-progress-chip span{display:block;margin-top:2px;font-size:12px;font-weight:1000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.price-progress-waitline{margin-top:6px;color:#d7bf7f;font-size:11px;font-weight:900;line-height:1.25}
.price-progress-details{margin-top:5px;border-top:1px solid #293744;padding-top:4px}
.price-progress-details>summary{cursor:pointer;list-style:none;color:#79bce9;font-size:10px;font-weight:1000;padding:3px 0;user-select:none}
.price-progress-details>summary::-webkit-details-marker{display:none}
.price-progress-details>summary::after{content:'  ▾'}
.price-progress-details[open]>summary::after{content:'  ▴'}
.price-progress-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:6px}
.price-progress-grid>div{border:1px solid #293744;border-radius:9px;background:#0d151c;padding:6px;text-align:center;min-width:0}
.price-progress-grid b{display:block;color:#758795;font-size:7px}.price-progress-grid span{display:block;margin-top:2px;font-size:11px;font-weight:1000;overflow-wrap:anywhere}
.price-progress-reason{margin-top:6px;color:#aebac4;font-size:10px;line-height:1.3;font-weight:760}
.price-progress-next{margin-top:6px;color:#7fbde9;font-size:9px;font-weight:950}
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
function pctText(v){
  const n=Number(v);
  if(!Number.isFinite(n))return '—';
  return (n>0?'+':'')+n.toFixed(1)+'%';
}
function dayText(v){
  const n=Number(v);
  return Number.isFinite(n)?n.toFixed(n%1?1:0):'—';
}
function priceEq(a,b){
  const x=Number(a),y=Number(b);
  return Number.isFinite(x)&&Number.isFinite(y)&&Math.abs(x-y)<=0.011;
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
function stepZeroHtml(r,p,target,current){
  const targetType=String(priceType(r)||'TEST').toUpperCase();
  const currentDetected=priceEq(current,target);
  const backendDetected=!!p&&priceEq(p?.current_tpr_price??p?.current_price,target);
  const status=currentDetected?(backendDetected?'WAITING FOR FIRST VALID DAY':'PRICE DETECTED · SYNCING'):'WAITING FOR PRICE CHANGE';
  const note=currentDetected
    ? 'The target price is now visible as CURRENT. Progress remains at Step 0 until the backend confirms this exact price event and receives a completed canonical POS day.'
    : 'This suggestion has not been detected as the active selling price. Do not count prior UPC/TPR history toward this new test.';
  return `<div class="price-progress compact-wait">
    <div class="price-progress-head"><div><div class="price-progress-title">TEST · STEP 0 / 7</div><div class="price-progress-purpose">${esc(targetType)} PRICE VALIDATION</div></div><div class="price-progress-status">${esc(status)}</div></div>
    <div class="price-progress-compact">
      <div class="price-progress-chip"><b>CURRENT</b><span>${current==null?'—':money(current)}</span></div>
      <div class="price-progress-chip"><b>TARGET</b><span>${target==null?'—':money(target)}</span></div>
      <div class="price-progress-chip"><b>VALID DAYS</b><span>0 / 7</span></div>
    </div>
    <div class="price-progress-waitline">${esc(note)}</div>
  </div>`;
}
function priceProgressHtml(r){
  const target=suggestedPrice(r);
  const current=currentPrice(r);
  if(target==null)return '';
  const p=tprProgressByUpc.get(progressUpcKey(upcOf(r)));

  // The progress shown on a suggestion card is owned by THIS suggested price,
  // not merely by the UPC.  Old TPR lifecycle data is supporting history only.
  if(!priceEq(current,target))return stepZeroHtml(r,p,target,current);
  if(!p||!priceEq(p?.current_tpr_price??p?.current_price,target))return stepZeroHtml(r,p,target,current);

  const rec=String(p?.recommendation_label||p?.recommendation_code||'OBSERVE').replaceAll('_',' ');
  const phase=String(p?.monitoring_phase||'LEARNING').replaceAll('_',' ');
  const purpose=String(p?.tpr_purpose_label||p?.tpr_purpose||'PRICE TEST').replaceAll('_',' ');
  const gp=p?.gp_day_lift_pct;
  const vel=p?.velocity_lift_pct;
  const rawDays=p?.completed_tpr_days??p?.tpr_supported_days??p?.current_behavior?.supported_days??p?.post_tpr_supported_day_count??p?.post_supported_days;
  const validDays=Math.max(0,Math.min(7,Number(rawDays)||0));
  const tprGp=p?.tpr_gp_per_day_3d??p?.current_behavior?.gp_per_day_current_cost;
  const baseGp=p?.baseline_gp_per_day_current_cost??p?.baseline_behavior?.gp_per_day_current_cost;
  const next=p?.suggested_regular_price??p?.suggested_tpr_price;
  const nextLabel=p?.suggested_regular_price!=null?'NEW REG':(p?.suggested_tpr_price!=null?'NEXT TPR':'NEXT');
  const clearDays=p?.projected_days_to_clear_oh;
  const needVel=p?.required_velocity_to_clear;
  const reason=String(p?.recommendation_reason||'Tracking completed-day performance for the detected test price.');
  return `<div class="price-progress">
    <div class="price-progress-head"><div><div class="price-progress-title">TEST · STEP ${esc(String(validDays))} / 7</div><div class="price-progress-purpose">${esc(purpose)} · ${esc(phase)}</div></div><div class="price-progress-status">${esc(rec)}</div></div>
    <div class="price-progress-compact">
      <div class="price-progress-chip"><b>VALID DAYS</b><span>${esc(String(validDays))} / 7</span></div>
      <div class="price-progress-chip"><b>VELOCITY Δ</b><span>${esc(pctText(vel))}</span></div>
      <div class="price-progress-chip"><b>GP$/DAY Δ</b><span>${esc(pctText(gp))}</span></div>
    </div>
    <details class="price-progress-details"><summary>More test details</summary>
      <div class="price-progress-grid">
        <div><b>TEST GP$/DAY</b><span>${tprGp==null?'—':money(tprGp)}</span></div>
        <div><b>BASE GP$/DAY</b><span>${baseGp==null?'—':money(baseGp)}</span></div>
        <div><b>${esc(nextLabel)}</b><span>${next==null?'—':money(next)}</span></div>
      </div>
      ${(clearDays!=null||needVel!=null)?`<div class="price-progress-grid"><div><b>DAYS TO CLEAR</b><span>${esc(dayText(clearDays))}</span></div><div><b>REQ VELOCITY</b><span>${needVel==null?'—':esc(fmt(needVel,1))+'/day'}</span></div><div><b>TEST PRICE</b><span>${money(target)}</span></div></div>`:''}
      <div class="price-progress-reason">${esc(reason)}</div>
      <div class="price-progress-next">Detected price event · completed canonical POS days only</div>
    </details>
  </div>`;
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
    new_tail = "}renderPrice();if(!tprProgressLoaded&&!tprProgressLoading){loadTprProgress().then(()=>renderPrice()).catch(()=>{})}}\nfunction actionablePrice"
    if old_tail in html:
        html = html.replace(old_tail, new_tail, 1)

    old_card = "</div><button class=\"ignore\" data-pi=\"${esc(key)}\">Ignore 12h</button></div>`"
    new_card = "</div>${priceProgressHtml(r)}<button class=\"ignore\" data-pi=\"${esc(key)}\">Ignore 12h</button></div>`"
    if old_card in html:
        html = html.replace(old_card, new_card, 1)

    html = html.replace("</style>", "</style>\n" + _STYLE, 1)
    html = html.replace(
        "</head>",
        f'<meta name="{marker}" content="1">\n</head>',
        1,
    )
    return html
