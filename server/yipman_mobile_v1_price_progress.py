from __future__ import annotations

"""RC-only UPC price-test progress presentation.

Price Review remains UPC-owned.  Active TPR lifecycle performance is loaded from
the existing backend current-TPR monitor and attached to the same UPC suggestion
card, so the user can see suggestion + test progress + next recommendation in one
place without turning Family rows into price decisions.
"""


_STYLE = r'''
<style id="yipmanV1PriceProgressStyle">
.price-progress{
  margin-top:9px;border:1px solid #314354;border-radius:13px;background:#101820;
  padding:10px;text-align:left
}
.price-progress-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.price-progress-title{font-size:9px;color:#8fa0ae;font-weight:1000;letter-spacing:.04em}
.price-progress-status{font-size:10px;font-weight:1000;color:#d7e8f6;text-align:right}
.price-progress-purpose{margin-top:4px;color:#9aa9b5;font-size:9px;font-weight:850}
.price-progress-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
.price-progress-grid>div{border:1px solid #293744;border-radius:10px;background:#0d151c;padding:7px;text-align:center;min-width:0}
.price-progress-grid b{display:block;color:#758795;font-size:6px}
.price-progress-grid span{display:block;margin-top:3px;font-size:10px;font-weight:1000;overflow-wrap:anywhere}
.price-progress-reason{margin-top:8px;color:#abb8c3;font-size:9px;line-height:1.35;font-weight:760}
.price-progress-next{margin-top:8px;border-top:1px solid #293744;padding-top:7px;color:#83c5f2;font-size:9px;font-weight:950}
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
  const reason=String(p?.recommendation_reason||'Tracking active TPR completed-day performance.');
  return `<div class="price-progress">
    <div class="price-progress-head"><div><div class="price-progress-title">TEST PROGRESS</div><div class="price-progress-purpose">${esc(purpose)} · ${esc(phase)}</div></div><div class="price-progress-status">${esc(rec)}</div></div>
    <div class="price-progress-grid">
      <div><b>VALID DAYS</b><span>${esc(dayText(days))}</span></div>
      <div><b>VELOCITY Δ</b><span>${esc(pctText(vel))}</span></div>
      <div><b>GP$/DAY Δ</b><span>${esc(pctText(gp))}</span></div>
      <div><b>TPR GP$/DAY</b><span>${tprGp==null?'—':money(tprGp)}</span></div>
      <div><b>BASE GP$/DAY</b><span>${baseGp==null?'—':money(baseGp)}</span></div>
      <div><b>${esc(nextLabel)}</b><span>${next==null?'—':money(next)}</span></div>
    </div>
    ${(clearDays!=null||needVel!=null)?`<div class="price-progress-grid"><div><b>DAYS TO CLEAR</b><span>${esc(dayText(clearDays))}</span></div><div><b>REQ VELOCITY</b><span>${needVel==null?'—':esc(fmt(needVel,1))+'/day'}</span></div><div><b>CURRENT TEST</b><span>${esc(String(p?.current_price??p?.tpr_price??'—'))}</span></div></div>`:''}
    <div class="price-progress-reason">${esc(reason)}</div>
    <div class="price-progress-next">Backend lifecycle tracking · completed valid data days only</div>
  </div>`;
}
'''


def polish_price_progress_html(html: str) -> str:
    marker = "yipmanV1PriceProgress"
    if marker in html:
        return html

    # Add backend lifecycle helpers inside the shell IIFE, immediately before
    # Price Review loading/rendering functions.
    anchor = "async function loadPrice(){"
    if anchor in html:
        html = html.replace(anchor, _SCRIPT_HELPERS + "\n" + anchor, 1)

    # Price Review paints immediately, then re-renders when the cached lifecycle
    # monitor arrives.  This keeps opening Price Review responsive.
    old_tail = "}renderPrice()}\nfunction actionablePrice"
    new_tail = "}renderPrice();if(!tprProgressLoaded&&!tprProgressLoading){loadTprProgress().then(()=>renderPrice()).catch(()=>{})}}\nfunction actionablePrice"
    if old_tail in html:
        html = html.replace(old_tail, new_tail, 1)

    # Attach progress to each direct UPC card, before Ignore 12h.
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
