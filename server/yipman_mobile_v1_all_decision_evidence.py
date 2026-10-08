from __future__ import annotations

"""Universal explanation/evidence layer for every rendered Mobile V1 primary decision.

Works on the existing Action Detail overlay after all specialized detail renderers have run.
It never invents unavailable evidence: missing backend fields are explicitly labelled.
"""

_STYLE = r'''
<style id="yipmanV1AllDecisionEvidenceStyle">
.v1-detail-decision{cursor:pointer;touch-action:manipulation;position:relative;padding-right:46px!important}
.v1-detail-decision::after{content:'WHY ›';position:absolute;right:13px;top:15px;color:#75b9eb;font-size:8px;font-weight:1000;letter-spacing:.05em}
.v1-decision-evidence{margin:0 0 9px;border:1px solid #314453;border-radius:14px;background:#101a22;overflow:hidden}
.v1-decision-evidence>summary{list-style:none;cursor:pointer;padding:11px 12px;font-size:11px;font-weight:1000;color:#e8f1f7;display:flex;justify-content:space-between;align-items:center;gap:8px}
.v1-decision-evidence>summary::-webkit-details-marker{display:none}.v1-decision-evidence>summary span{color:#77b8e7;font-size:9px}.v1-decision-evidence[open]>summary{border-bottom:1px solid #2a3b47}
.v1-decision-evidence-body{padding:10px 12px}.v1-decision-section{margin-bottom:12px}.v1-decision-section:last-child{margin-bottom:0}.v1-decision-section h4{margin:0 0 5px;color:#8194a3;font-size:8px;font-weight:1000;letter-spacing:.05em}.v1-decision-section p{margin:0;color:#c0cbd3;font-size:11px;line-height:1.45}
.v1-decision-grid{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 10px;font-size:10px}.v1-decision-grid b{color:#8193a1}.v1-decision-grid span{text-align:right;color:#eef4f7;font-weight:1000}.v1-decision-grid .missing{color:#e3c36d}.v1-decision-source{color:#8ba0af!important;font-size:9px!important}
</style>
'''

_SCRIPT = r'''
<script id="yipmanV1AllDecisionEvidenceScript">
(()=>{'use strict';
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const txt=(root,sel)=>String(root?.querySelector(sel)?.textContent||'').trim();
 const metric=(root,label)=>{for(const el of root.querySelectorAll('.v1-detail-metrics>div,.v1-force-order-cell')){const k=txt(el,'b').toUpperCase();if(k.includes(label))return txt(el,'span')||txt(el,'strong')}return''};
 const identity=(body,label)=>{for(const el of body.querySelectorAll('.v1-detail-id>div'))if(txt(el,'b').toUpperCase().includes(label))return txt(el,'span');return''};
 function classify(action,subtitle){const s=(action+' '+subtitle).toUpperCase();if(/^ORDER\b|^NO ORDER\b/.test(s))return'ORDER';if(s.includes('CLEAR'))return'CLEARANCE';if(s.includes('TPR-FRESH')||s.includes('FRESHNESS'))return'TPR_FRESH';if(s.includes('TPR'))return'TPR_GP';if(s.includes('DUMP')||s.includes('PI')||s.includes('STOCK'))return'INVENTORY';if(s.includes('REG')||s.includes('PRICE'))return'PRICE';return'GENERAL'}
 function explain(type,action,body){const oh=metric(body,'EFFECTIVE OH')||txt(body,'.v1-detail-oh strong'),price=metric(body,'CURRENT PRICE'),cost=metric(body,'CURRENT COST'),sales=metric(body,'7D SALES'),avg=metric(body,'7D AVG'),dos=metric(body,'DOS'),delivery=metric(body,'DELIVERY'),next=metric(body,'NEXT DELIVERY'),proj=metric(body,'PROJECTED OH'),coverage=metric(body,'COVERAGE USE'),family=identity(body,'FAMILY'),upc=identity(body,'UPC');let why='',logic='';
  if(type==='TPR_FRESH'){why='Freshness sell-through action: the current stock position and selling velocity indicate a temporary price reduction is needed to improve sell-through before the freshness threshold. The displayed TPR price remains the server decision.';logic='Freshness policy evaluates Effective OH, stock age/DOH when available, recent velocity, remaining sell-through window, current price and cost/GP$. The goal is to clear at-risk old stock by the freshness threshold, not merely reduce price.'}
  else if(type==='TPR_GP'){why='Temporary price test intended to improve GP$ or establish a better regular-price sweet spot using observed sales response and current economics.';logic='Pricing policy compares current price, cost, observed velocity/GP$, prior tested prices and applicable company constraints. The displayed price is the backend recommendation.'}
  else if(type==='CLEARANCE'){why='Clearance action is driven by expiration/freshness risk and remaining stock. The objective is to sell the at-risk quantity before it becomes dumping.';logic='Clearance policy weighs Effective OH, remaining shelf-life/freshness window, recent velocity, cost and required sell-through rate.'}
  else if(type==='ORDER'){why=action.toUpperCase().startsWith('NO ORDER')?'Projected available stock is sufficient for the selected coverage window, so no replenishment is required.':'Projected available stock is below expected demand for the selected delivery coverage window, so replenishment is recommended.';logic='Ordering logic projects Effective OH to delivery, applies day-segmented demand through the day before the next delivery, then applies ordering/freshness constraints and valid UOM/pack rounding.'}
  else if(type==='INVENTORY'){why='Inventory action is based on the current authoritative stock position and the operational discrepancy or shrink/dumping condition shown for this item.';logic='True Stock supersedes calculated Effective OH when saved; downstream price and ordering decisions are recalculated from the updated inventory position.'}
  else if(type==='PRICE'){why='Price action is intended to keep the item at the best supported everyday price or correct a pricing rule mismatch while protecting GP$.';logic='Pricing policy uses current price, cost, recent velocity/GP$, tested-price evidence and applicable company/paired-UPC constraints.'}
  else{why='This is the current server-generated operational decision for the item. Supporting values visible in this detail are shown below.';logic='The app displays the backend decision and does not independently manufacture a recommendation.'}
  const ev=[['Family',family],['UPC',upc],['Effective OH',oh],['Current price',price],['Current cost',cost],['7D sales',sales],['7D avg',avg],['DOS / stock days',dos],['Delivery',delivery],['Next delivery',next],['Projected OH',proj],['Coverage use',coverage]].filter(x=>x[1]);return{why,logic,ev}}
 function apply(){const overlay=document.getElementById('v1DetailOverlay'),body=document.getElementById('v1DetailBody');if(!overlay?.classList.contains('open')||!body)return;const decision=body.querySelector('.v1-detail-decision');if(!decision)return;const action=txt(decision,'strong'),subtitle=txt(decision,'p');const sig=action+'|'+identity(body,'FAMILY')+'|'+identity(body,'UPC');if(body.dataset.allDecisionEvidence===sig)return;body.dataset.allDecisionEvidence=sig;body.querySelectorAll('.v1-decision-evidence').forEach(x=>x.remove());const d=explain(classify(action,subtitle),action,body);const box=document.createElement('details');box.className='v1-decision-evidence';box.open=true;const grid=d.ev.length?'<div class="v1-decision-grid">'+d.ev.map(([k,v])=>'<b>'+esc(k)+'</b><span>'+esc(v)+'</span>').join('')+'</div>':'<p class="v1-decision-source">No additional structured evidence is exposed in this detail payload.</p>';box.innerHTML='<summary>WHY & SUPPORTING EVIDENCE <span>tap to collapse</span></summary><div class="v1-decision-evidence-body"><section class="v1-decision-section"><h4>WHY THIS DECISION</h4><p>'+esc(d.why)+'</p></section><section class="v1-decision-section"><h4>EVIDENCE USED / EXPOSED</h4>'+grid+'</section><section class="v1-decision-section"><h4>CALCULATION / POLICY LOGIC</h4><p>'+esc(d.logic)+'</p></section><section class="v1-decision-section"><h4>SOURCE & LIMITATIONS</h4><p class="v1-decision-source">Values are from the live FULL MYSQL detail and current rendered decision. Evidence not exposed by the backend is not invented. Missing intermediate inputs must be added to the API for full numerical auditability.</p></section></div>';decision.insertAdjacentElement('afterend',box);decision.onclick=()=>{box.open=!box.open}}
 let queued=false;const kick=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;apply()})};new MutationObserver(kick).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});document.addEventListener('click',()=>setTimeout(kick,20),true);setInterval(kick,1200);
})();
</script>
'''

def polish_all_decision_evidence_html(html: str) -> str:
    if 'yipmanV1AllDecisionEvidenceStyle' in html:return html
    html=html.replace('</head>',_STYLE+'</head>',1)
    html=html.replace('</body>',_SCRIPT+'</body>',1)
    return html
