from __future__ import annotations

ADMIN_WEB_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111827">
<title>FULL MYSQL Admin</title>
<style>
:root{color-scheme:light dark;--bg:#f4f6f8;--card:#fff;--text:#111827;--muted:#667085;--line:#e4e7ec;--accent:#175cd3;--bad:#b42318;--warn:#b54708;--ok:#067647}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--text:#f3f4f6;--muted:#98a2b3;--line:#2c313a;--accent:#84adff;--bad:#f97066;--warn:#fdb022;--ok:#47cd89}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:14px}.top{position:sticky;top:0;z-index:8;background:color-mix(in srgb,var(--bg) 93%,transparent);backdrop-filter:blur(10px);padding:10px 0}
h1{font-size:20px;margin:0}.sub{font-size:12px;color:var(--muted)}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin:10px 0}.section{font-size:17px;font-weight:800;margin:18px 0 8px}
input,select,textarea,button{font:inherit;border-radius:10px;border:1px solid var(--line);padding:10px 11px;background:var(--card);color:var(--text)}
input,select,textarea{width:100%}textarea{min-height:72px;resize:vertical}button{cursor:pointer;font-weight:700}button.primary{background:var(--accent);color:white;border-color:transparent}.danger{color:var(--bad)}.ok{color:var(--ok)}.warn{color:var(--warn)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}@media(max-width:680px){.grid{grid-template-columns:1fr}}.field label{display:block;font-size:11px;color:var(--muted);margin:0 0 4px}
.msg{font-size:12px;color:var(--muted);margin-top:8px}.hidden{display:none!important}.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 8px;font-size:11px;font-weight:700}
.item{border-top:1px solid var(--line);padding:10px 0}.item:first-child{border-top:0}.name{font-weight:800}.meta{font-size:12px;color:var(--muted);margin-top:3px}.kv{display:grid;grid-template-columns:1fr auto;gap:4px 10px;font-size:12px;margin-top:8px}.kv .k{color:var(--muted)}.kv .v{text-align:right;font-weight:700}
.actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.smallbtn{padding:6px 9px;font-size:12px}.receipt{border-left:3px solid var(--line);padding-left:8px;margin-top:6px}.toplinks{display:flex;gap:8px;align-items:center}.toplinks a{color:var(--accent);text-decoration:none;font-size:12px}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="row" style="justify-content:space-between">
      <div><h1>FULL MYSQL · Admin Console</h1><div class="sub">v7.0.108 · ID/password secure session</div></div>
      <div class="toplinks"><a href="/app">Open App</a><button id="logout" class="smallbtn hidden">Logout</button></div>
    </div>
    <div id="sessionMsg" class="msg">Checking admin session…</div>
  </div>

  <div id="loginCard" class="card hidden">
    <div class="section" style="margin-top:0">Admin Sign In</div>
    <div class="sub">Sign in with Admin ID and Password. Credentials are sent only to the server and are not stored in browser page storage.</div>
    <div class="grid" style="margin-top:10px">
      <div class="field"><label>Admin ID</label><input id="adminId" value="admin" autocomplete="username"></div>
      <div class="field"><label>Password</label><input id="adminPassword" type="password" placeholder="Password" autocomplete="current-password"></div>
    </div>
    <div class="actions"><button id="login" class="primary">Sign In</button></div>
    <div id="loginMsg" class="msg"></div>
  </div>

  <div id="console" class="hidden">
    <div class="section">📦 Ordering Policy</div>
    <div class="card">
      <div class="grid">
        <div class="field"><label>Scope</label><select id="scopeType"><option>GLOBAL</option><option>PRODUCT_CLASS</option><option>FAMILY</option><option>ARTICLE</option><option>UPC</option></select></div>
        <div class="field"><label>Scope Key</label><input id="scopeKey" value="*" placeholder="* / FROZEN / family / article / UPC"></div>
        <div class="field"><label>Order weekday</label><select id="orderDay"></select></div>
        <div class="field"><label>Delivery weekday</label><select id="deliveryDay"></select></div>
        <div class="field"><label>Coverage days after delivery</label><input id="coverageDays" inputmode="decimal" placeholder="e.g. 7"></div>
        <div class="field"><label>Safety days</label><input id="safetyDays" inputmode="decimal" value="0"></div>
        <div class="field"><label>Minimum order qty</label><input id="minOrder" inputmode="decimal" placeholder="optional"></div>
        <div class="field"><label>Order multiple</label><input id="orderMultiple" inputmode="decimal" placeholder="optional"></div>
      </div>
      <div class="field" style="margin-top:8px"><label>Notes</label><textarea id="policyNotes" placeholder="Authoritative source / reason"></textarea></div>
      <div class="actions"><button id="savePolicy" class="primary">Save Policy</button><button id="refreshPolicies">Refresh</button></div>
      <div id="policyMsg" class="msg"></div>
    </div>
    <div id="policyList" class="card"></div>

    <div class="section">📋 Final Order Workflow</div>
    <div class="card">
      <div class="actions">
        <button id="refreshOrderWorkflow">Refresh</button>
        <select id="orderDraftFilter" style="width:auto">
          <option value="">All Draft Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="CONFIRMED">Confirmed</option>
          <option value="MARKED_SUBMITTED">Marked Submitted</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>
      <div class="sub">Only items with a valid ordering policy and positive Suggested Order Qty can be added. Mark Submitted is audit-only; it does not transmit an order to a supplier.</div>
      <div id="orderRecommendationStatus" class="msg"></div>
      <div id="orderRecommendationList"></div>
    </div>
    <div id="orderDraftList" class="card"></div>

    <div class="section">💲 Create Price Proposal</div>
    <div class="card">
      <div class="grid">
        <div class="field"><label>UPC</label><div class="row"><input id="proposalUpc" placeholder="UPC"><button id="loadProposalUpc" class="smallbtn">Load</button></div></div>
        <div class="field"><label>Proposed price</label><input id="proposalPrice" inputmode="decimal" placeholder="0.00"></div>
        <div class="field"><label>Basis</label><select id="proposalBasis"><option>MANUAL</option><option>SWEET_SPOT</option><option>WGPM</option><option>COMPANY_A</option><option>COMPANY_B</option><option>COMPANY_C</option><option>CURRENT</option></select></div>
        <div class="field"><label>Price type</label><select id="proposalType"><option value="">Unspecified</option><option>REG</option><option>TPR</option><option>SALE</option><option>IN STORE</option></select></div>
      </div>
      <div id="proposalItemSummary" class="msg"></div>
      <div class="field" style="margin-top:8px"><label>Reason</label><textarea id="proposalReason" placeholder="Why this proposal is being created"></textarea></div>
      <div class="actions"><button id="createProposal" class="primary">Create Proposal</button></div>
      <div id="proposalCreateMsg" class="msg"></div>
    </div>

    <div class="section">🧾 Proposal Queue</div>
    <div class="card">
      <div class="actions">
        <select id="adminProposalFilter" style="width:auto">
          <option value="">All Statuses</option>
          <option value="PENDING_REVIEW">Pending Review</option>
          <option value="APPROVED_FOR_EXECUTION">Approved</option>
          <option value="MARKED_EXECUTED">Marked Executed</option>
          <option value="REJECTED">Rejected</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <button id="refreshProposals">Refresh</button>
      </div>
      <div id="proposalList"></div>
    </div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=2)=>{if(v===null||v===undefined||v==='')return '—';const n=Number(v);return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):String(v)}
const money=v=>v===null||v===undefined||v===''?'—':'$'+fmt(v,2);
const pct=v=>v===null||v===undefined||v===''?'—':fmt(Number(v)*100,1)+'%';
const days=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
for(const id of ['orderDay','deliveryDay']) $(id).innerHTML=days.map((d,i)=>'<option value="'+i+'">'+d+'</option>').join('');

async function api(path,opts={}){
  const r=await fetch(path,Object.assign({credentials:'same-origin'},opts));
  let body=null;try{body=await r.json()}catch{}
  if(!r.ok){const d=body?.detail;throw new Error(typeof d==='string'?d:(d?.reason||('HTTP '+r.status)))}
  return body;
}
function setSession(ok,txt){
  $('loginCard').classList.toggle('hidden',ok);$('console').classList.toggle('hidden',!ok);$('logout').classList.toggle('hidden',!ok);
  $('sessionMsg').textContent=txt;$('sessionMsg').className='msg '+(ok?'ok':'warn');
}
async function checkSession(){
  try{const d=await api('/v1/admin/session');setSession(true,'Signed in as '+(d.login_id||d.device||'admin')+' · expires '+(d.expires_at||''));await Promise.all([loadPolicies(),loadOrderWorkflow(),loadProposals()])}
  catch{setSession(false,'Admin sign-in required.')}
}
async function login(){
  const loginId=$('adminId').value.trim(), password=$('adminPassword').value;
  if(!loginId||!password)return;
  $('loginMsg').textContent='Signing in…';
  try{
    const d=await api('/v1/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({login_id:loginId,password})});
    $('adminPassword').value='';$('loginMsg').textContent='';setSession(true,'Signed in as '+(d.login_id||loginId));await Promise.all([loadPolicies(),loadOrderWorkflow(),loadProposals()]);
  }catch(e){$('loginMsg').textContent=e.message;$('loginMsg').className='msg danger'}
}
async function logout(){
  try{await api('/v1/admin/logout',{method:'POST'})}catch{}
  setSession(false,'Signed out.');
}
async function loadPolicies(){
  try{
    const d=await api('/v1/app/ordering/policies');
    $('policyList').innerHTML='<div class="name">'+d.count+' configured policy(s)</div>'+
      (d.rows||[]).map(r=>'<div class="item"><div class="row" style="justify-content:space-between"><div class="name">'+esc(r.scope_type)+' · '+esc(r.scope_key)+'</div><span class="pill">'+(r.enabled?'ENABLED':'DISABLED')+'</span></div>'+
      '<div class="kv"><div class="k">Order → Delivery</div><div class="v">'+esc(days[r.order_weekday])+' → '+esc(days[r.delivery_weekday])+'</div>'+
      '<div class="k">Coverage + Safety</div><div class="v">'+fmt(r.coverage_days_after_delivery,1)+' + '+fmt(r.safety_days,1)+' days</div>'+
      '<div class="k">Min / Multiple</div><div class="v">'+fmt(r.min_order_qty)+' / '+fmt(r.order_multiple)+'</div></div>'+
      '<div class="meta">'+esc(r.notes||'')+'</div></div>').join('');
  }catch(e){$('policyMsg').textContent=e.message;$('policyMsg').className='msg danger'}
}
async function savePolicy(){
  $('policyMsg').textContent='Saving…';
  const body={
    scope_type:$('scopeType').value,
    scope_key:$('scopeType').value==='GLOBAL'?'*':$('scopeKey').value.trim(),
    order_weekday:Number($('orderDay').value),
    delivery_weekday:Number($('deliveryDay').value),
    coverage_days_after_delivery:$('coverageDays').value,
    safety_days:$('safetyDays').value||0,
    min_order_qty:$('minOrder').value||null,
    order_multiple:$('orderMultiple').value||null,
    enabled:true,
    notes:$('policyNotes').value.trim()||null
  };
  try{await api('/v1/admin/ordering/policy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('policyMsg').textContent='Saved.';$('policyMsg').className='msg ok';await Promise.all([loadPolicies(),loadOrderWorkflow()])}
  catch(e){$('policyMsg').textContent=e.message;$('policyMsg').className='msg danger'}
}
async function addOrderRecommendation(upc){
  try{
    const d=await api('/v1/admin/ordering/drafts/add-recommendation',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({upc})
    });
    $('orderRecommendationStatus').textContent='Added '+upc+' to Draft #'+d.order_draft_id+'.';
    $('orderRecommendationStatus').className='msg ok';
    await loadOrderWorkflow();
  }catch(e){
    $('orderRecommendationStatus').textContent=e.message;
    $('orderRecommendationStatus').className='msg danger';
  }
}

async function saveOrderLine(lineId){
  const input=$('orderQty_'+lineId);
  if(!input)return;
  const note=window.prompt('Adjustment note (optional):','');
  try{
    await api('/v1/admin/ordering/drafts/lines/'+lineId,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({final_qty:input.value,adjustment_note:note||null})
    });
    await loadOrderWorkflow();
  }catch(e){alert(e.message)}
}

async function transitionOrderDraft(id,action){
  const labels={
    CONFIRM:'Confirm this order draft?',
    MARK_SUBMITTED:'Mark this order as submitted? This is audit-only and does not transmit to a supplier.',
    CANCEL_DRAFT:'Cancel this draft?',
    CANCEL_CONFIRMED:'Cancel this confirmed order?'
  };
  if(!window.confirm(labels[action]||'Continue?'))return;
  const note=window.prompt('Workflow note (optional):','');
  let external_order_reference=null;
  if(action==='MARK_SUBMITTED'){
    external_order_reference=window.prompt('Supplier PO / order reference (recommended, optional):','')||null;
  }
  try{
    await api('/v1/admin/ordering/drafts/'+id+'/transition',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action,note:note||null,external_order_reference})
    });
    await loadOrderWorkflow();
  }catch(e){alert(e.message)}
}

async function saveOrderReference(id){
  const input=$('orderRef_'+id); if(!input)return;
  try{
    await api('/v1/admin/ordering/drafts/'+id+'/reference',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({external_order_reference:input.value.trim()||null})
    });
    await loadOrderWorkflow();
  }catch(e){alert(e.message)}
}

async function reconcileOrderDraft(id){
  const target=$('orderRecon_'+id); if(!target)return;
  target.className='msg'; target.textContent='Reconciling canonical receipt evidence…';
  try{
    const d=await api('/v1/admin/ordering/drafts/'+id+'/reconciliation');
    const lines=(d.lines||[]).map(l=>{
      const evidence=(l.receipt_evidence||[]).map(r=>
        '<div class="receipt"><div><b>MVT '+esc(r.movement_type)+'</b> · '+esc(r.posting_date||'')+
        ' · '+fmt(r.selling_equivalent_quantity)+' '+esc(r.selling_equivalent_uom||'')+'</div>'+
        '<div class="meta">PO '+esc(r.purchase_order||'—')+' · Doc '+esc(r.article_document||'—')+
        ' · '+esc(r.conversion_basis||'')+' · file '+esc(r.file_id||'')+'</div></div>'
      ).join('');
      const blocked=(l.uom_blocked_evidence||[]).map(r=>
        '<div class="receipt warn"><div><b>UOM REVIEW · MVT '+esc(r.movement_type)+'</b></div>'+
        '<div class="meta">'+esc(r.base_quantity)+' '+esc(r.base_uom_code||'')+
        ' / '+esc(r.entry_quantity)+' '+esc(r.entry_uom_code||'')+
        ' · '+esc(r.conversion_basis||'')+'</div></div>'
      ).join('');
      return '<div class="item"><div class="row" style="justify-content:space-between"><div class="name">'+
        esc(l.selling_description||l.ean_upc)+'</div><span class="pill">'+esc(l.reconciliation_status||'')+'</span></div>'+
        '<div class="meta">UPC '+esc(l.ean_upc)+' · '+esc(l.match_basis||'')+' · '+esc(l.identity_basis||'')+'</div>'+
        '<div class="kv"><div class="k">Ordered</div><div class="v">'+fmt(l.ordered_qty)+' '+esc(l.selling_uom||'')+'</div>'+
        '<div class="k">Received</div><div class="v">'+fmt(l.received_qty)+' '+esc(l.selling_uom||'')+'</div>'+
        '<div class="k">Variance</div><div class="v">'+fmt(l.variance_qty)+' '+esc(l.selling_uom||'')+'</div>'+
        '<div class="k">Receipt Basis</div><div class="v">'+esc(l.receipt_basis||'')+'</div>'+
        '<div class="k">Receipt Window</div><div class="v">'+esc(l.window_start||'')+' → '+esc(l.window_end_exclusive||'')+'</div>'+
        '<div class="k">MVT Data Through</div><div class="v">'+esc(l.movement_data_through||'—')+'</div></div>'+
        evidence+blocked+'</div>';
    }).join('');
    target.className='card';
    target.innerHTML='<div class="row" style="justify-content:space-between"><div class="name">Delivery Reconciliation</div><span class="pill">'+
      esc(d.overall_status||'')+'</span></div>'+
      '<div class="meta">Order #'+esc(d.order_draft_id)+' · '+esc(d.order_date)+' → '+esc(d.delivery_date)+
      ' · Ref '+esc(d.external_order_reference||'DATE-WINDOW FALLBACK')+'</div>'+lines+
      '<div class="sub">101/107 are receipt-stage evidence. 109 is ignored when 101/107 evidence exists and used only as fallback. 107 never changes unrestricted OH here.</div>';
  }catch(e){target.className='msg danger';target.textContent=e.message}
}

async function loadOrderWorkflow(){
  $('orderRecommendationStatus').textContent='Loading ordering recommendations…';
  const status=$('orderDraftFilter').value;
  const draftPath='/v1/admin/ordering/drafts?limit=60'+(status?'&status='+encodeURIComponent(status):'');
  try{
    const [rec,drafts]=await Promise.all([
      api('/v1/app/ordering?limit=160'),
      api(draftPath)
    ]);
    const ready=(rec.rows||[]).filter(r=>{
      const o=r.ordering||{};
      return o.status==='ORDER_RECOMMENDATION_READY' && Number(o.suggested_order_qty||0)>0;
    });
    $('orderRecommendationStatus').textContent=ready.length+' positive recommendation(s) ready for Draft.';
    $('orderRecommendationList').innerHTML=ready.map(r=>{
      const o=r.ordering||{};
      return '<div class="item"><div class="row" style="justify-content:space-between"><div class="name">'+esc(r.selling_description||r.ean_upc)+'</div><span class="pill">'+esc(o.action||'ORDER')+'</span></div>'+
        '<div class="meta">UPC '+esc(r.ean_upc)+' · Article '+esc(r.article_number||'—')+'</div>'+
        '<div class="kv"><div class="k">Suggested</div><div class="v">'+fmt(o.suggested_order_qty)+' '+esc(o.suggested_order_uom||'')+'</div>'+
        '<div class="k">Order → Delivery</div><div class="v">'+esc(o.next_order_date||'—')+' → '+esc(o.next_delivery_date||'—')+'</div>'+
        '<div class="k">Effective OH</div><div class="v">'+fmt(r.effective_oh)+' '+esc(r.effective_oh_uom||'')+'</div>'+
        '<div class="k">Velocity / DOS</div><div class="v">'+fmt(r.upc_velocity_7d,2)+' / '+fmt(o.days_supply,1)+'</div>'+
        '<div class="k">Policy</div><div class="v">'+esc(o.policy?.scope_type||'—')+' '+esc(o.policy?.scope_key||'')+'</div></div>'+
        '<div class="actions"><button class="smallbtn addOrderRec" data-upc="'+esc(r.ean_upc)+'">Add to Draft</button></div></div>';
    }).join('')||'<div class="msg">No positive order recommendations are ready. Items without authoritative policy remain excluded.</div>';

    $('orderRecommendationList').querySelectorAll('.addOrderRec').forEach(btn=>btn.addEventListener('click',()=>addOrderRecommendation(btn.dataset.upc)));

    $('orderDraftList').innerHTML='<div class="name">'+drafts.count+' order workflow record(s)</div>'+
      (drafts.rows||[]).map(d=>{
        const s=String(d.workflow_status||'');
        const lines=(d.lines||[]).map(l=>{
          const editable=s==='DRAFT';
          const qty=editable
            ? '<div class="row"><input id="orderQty_'+l.order_draft_line_id+'" inputmode="decimal" value="'+esc(l.final_qty)+'" style="max-width:110px"><button class="smallbtn" onclick="saveOrderLine('+l.order_draft_line_id+')">Save Qty</button></div>'
            : fmt(l.final_qty)+' '+esc(l.selling_uom||'');
          return '<div class="item"><div class="name">'+esc(l.selling_description||l.ean_upc)+'</div>'+
            '<div class="meta">UPC '+esc(l.ean_upc)+' · '+esc(l.article_number||'—')+'</div>'+
            '<div class="kv"><div class="k">Suggested</div><div class="v">'+fmt(l.suggested_qty)+' '+esc(l.selling_uom||'')+'</div>'+
            '<div class="k">Final Qty</div><div class="v">'+qty+'</div>'+
            '<div class="k">OH / Velocity / DOS</div><div class="v">'+fmt(l.effective_oh)+' / '+fmt(l.velocity_7d,2)+' / '+fmt(l.days_supply,1)+'</div>'+
            '<div class="k">Policy</div><div class="v">'+esc(l.ordering_policy_scope_type||'—')+' '+esc(l.ordering_policy_scope_key||'')+'</div></div>'+
            '<div class="meta">'+esc(l.adjustment_note||'')+'</div></div>';
        }).join('');
        let actions='';
        if(s==='DRAFT')actions='<div class="actions"><button class="smallbtn primary" onclick="transitionOrderDraft('+d.order_draft_id+',\'CONFIRM\')">Confirm</button><button class="smallbtn" onclick="transitionOrderDraft('+d.order_draft_id+',\'CANCEL_DRAFT\')">Cancel</button></div>';
        if(s==='CONFIRMED')actions='<div class="actions"><button class="smallbtn primary" onclick="transitionOrderDraft('+d.order_draft_id+',\'MARK_SUBMITTED\')">Mark Submitted</button><button class="smallbtn" onclick="transitionOrderDraft('+d.order_draft_id+',\'CANCEL_CONFIRMED\')">Cancel</button><button class="smallbtn" onclick="reconcileOrderDraft('+d.order_draft_id+')">Reconcile Delivery</button></div>';
        if(s==='MARKED_SUBMITTED')actions='<div class="actions"><button class="smallbtn" onclick="reconcileOrderDraft('+d.order_draft_id+')">Reconcile Delivery</button></div>';
        const refEditor=(s==='CONFIRMED'||s==='MARKED_SUBMITTED')
          ? '<div class="row" style="margin-top:8px"><input id="orderRef_'+d.order_draft_id+'" value="'+esc(d.external_order_reference||'')+'" placeholder="Supplier PO / order reference"><button class="smallbtn" onclick="saveOrderReference('+d.order_draft_id+')">Save Ref</button></div>'
          : '';
        const reconBox=(s==='CONFIRMED'||s==='MARKED_SUBMITTED')?'<div id="orderRecon_'+d.order_draft_id+'" class="msg"></div>':'';
        return '<div class="item"><div class="row" style="justify-content:space-between"><div class="name">Order #'+esc(d.order_draft_id)+' · '+esc(d.order_date)+' → '+esc(d.delivery_date)+'</div><span class="pill">'+esc(s)+'</span></div>'+
          '<div class="meta">'+fmt(d.line_count,0)+' line(s) · total final qty '+fmt(d.total_final_qty)+
          ' · Ref '+esc(d.external_order_reference||'—')+'</div>'+lines+refEditor+actions+reconBox+'</div>';
      }).join('');
  }catch(e){
    $('orderRecommendationStatus').textContent=e.message;
    $('orderRecommendationStatus').className='msg danger';
    $('orderDraftList').innerHTML='<div class="msg danger">'+esc(e.message)+'</div>';
  }
}

let loadedProposalItem=null;
async function loadProposalUpc(){
  const upc=$('proposalUpc').value.trim(); if(!upc)return;
  $('proposalItemSummary').textContent='Loading…';
  try{
    const d=await api('/v1/app/quick-check/'+encodeURIComponent(upc));
    const x=d.item||{};
    loadedProposalItem=x;
    $('proposalItemSummary').className='card';
    $('proposalItemSummary').innerHTML='<div class="name">'+esc(x.selling_description||x.ean_upc)+'</div>'+
      '<div class="kv"><div class="k">Current</div><div class="v">'+money(x.current_price)+'</div>'+
      '<div class="k">Cost</div><div class="v">'+money(x.current_cost_per_selling_unit)+'</div>'+
      '<div class="k">GP%</div><div class="v">'+pct(x.gp_pct_current)+'</div>'+
      '<div class="k">Sweet / WGPM</div><div class="v">'+money(x.sweet_spot_price)+' / '+money(x.wgpm_price)+'</div>'+
      '<div class="k">Company A/B/C</div><div class="v">'+money(x.company_price_a)+' / '+money(x.company_price_b)+' / '+money(x.company_price_c)+'</div></div>';
    applyBasisPrice();
  }catch(e){loadedProposalItem=null;$('proposalItemSummary').textContent=e.message;$('proposalItemSummary').className='msg danger'}
}
function applyBasisPrice(){
  if(!loadedProposalItem)return;
  const map={SWEET_SPOT:'sweet_spot_price',WGPM:'wgpm_price',COMPANY_A:'company_price_a',COMPANY_B:'company_price_b',COMPANY_C:'company_price_c',CURRENT:'current_price'};
  const basis=$('proposalBasis').value, field=map[basis];
  if(field && loadedProposalItem[field]!==null && loadedProposalItem[field]!==undefined)$('proposalPrice').value=loadedProposalItem[field];
}

async function createProposal(){
  $('proposalCreateMsg').textContent='Creating…';
  const body={
    upc:$('proposalUpc').value.trim(),proposed_price:$('proposalPrice').value,
    proposal_basis:$('proposalBasis').value,proposed_price_type:$('proposalType').value||null,
    reason:$('proposalReason').value.trim()||null
  };
  try{
    const d=await api('/v1/admin/price-change/proposals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    $('proposalCreateMsg').textContent='Proposal #'+d.proposal.proposal_id+' created.';$('proposalCreateMsg').className='msg ok';await loadProposals();
  }catch(e){$('proposalCreateMsg').textContent=e.message;$('proposalCreateMsg').className='msg danger'}
}
async function reviewProposal(id,decision){
  const note=window.prompt(decision+' note (optional):','');
  try{await api('/v1/admin/price-change/proposals/'+id+'/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,note:note||null})});await loadProposals()}
  catch(e){alert(e.message)}
}
async function markExecuted(id){
  if(!window.confirm('Mark proposal #'+id+' executed? This is audit-only and does not directly mutate current retail price.'))return;
  const note=window.prompt('Execution note (optional):','');
  try{await api('/v1/admin/price-change/proposals/'+id+'/mark-executed',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:note||null})});await loadProposals()}
  catch(e){alert(e.message)}
}
async function loadProposals(){
  const status=$('adminProposalFilter').value;
  const path='/v1/app/price-change/proposals?limit=100'+(status?'&status='+encodeURIComponent(status):'');
  const d=await api(path);
  $('proposalList').innerHTML=(d.rows||[]).map(r=>{
    const s=String(r.proposal_status||'');
    let actions='';
    if(s==='PENDING_REVIEW')actions='<div class="actions"><button class="smallbtn" onclick="reviewProposal('+r.proposal_id+',\'APPROVE\')">Approve</button><button class="smallbtn" onclick="reviewProposal('+r.proposal_id+',\'REJECT\')">Reject</button><button class="smallbtn" onclick="reviewProposal('+r.proposal_id+',\'CANCEL\')">Cancel</button></div>';
    if(s==='APPROVED_FOR_EXECUTION')actions='<div class="actions"><button class="smallbtn primary" onclick="markExecuted('+r.proposal_id+')">Mark Executed</button></div>';
    return '<div class="item"><div class="row" style="justify-content:space-between"><div class="name">'+esc(r.selling_description||r.ean_upc)+'</div><span class="pill">'+esc(s)+'</span></div>'+
      '<div class="meta">#'+esc(r.proposal_id)+' · UPC '+esc(r.ean_upc)+' · '+esc(r.proposal_basis||'')+'</div>'+
      '<div class="kv"><div class="k">Current → Proposed</div><div class="v">'+money(r.current_price)+' → '+money(r.proposed_price)+'</div>'+
      '<div class="k">GP%</div><div class="v">'+pct(r.current_gp_pct)+' → '+pct(r.proposed_gp_pct)+'</div>'+
      '<div class="k">GP$/day Δ</div><div class="v">'+money(r.projected_gp_per_day_delta)+'</div></div>'+
      '<div class="meta">'+esc(r.reason||r.review_note||r.execution_note||'')+'</div>'+actions+'</div>';
  }).join('')||'<div class="msg">No proposals.</div>';
}
$('login').addEventListener('click',login);$('adminPassword').addEventListener('keydown',e=>{if(e.key==='Enter')login()});$('logout').addEventListener('click',logout);
$('savePolicy').addEventListener('click',savePolicy);$('refreshPolicies').addEventListener('click',loadPolicies);
$('refreshOrderWorkflow').addEventListener('click',loadOrderWorkflow);
$('orderDraftFilter').addEventListener('change',loadOrderWorkflow);
$('loadProposalUpc').addEventListener('click',loadProposalUpc);
$('proposalUpc').addEventListener('keydown',e=>{if(e.key==='Enter')loadProposalUpc()});
$('proposalBasis').addEventListener('change',applyBasisPrice);
$('createProposal').addEventListener('click',createProposal);$('refreshProposals').addEventListener('click',loadProposals);
$('adminProposalFilter').addEventListener('change',loadProposals);
$('scopeType').addEventListener('change',()=>{if($('scopeType').value==='GLOBAL')$('scopeKey').value='*'});
checkSession();
</script>
</body>
</html>"""


def admin_web_html() -> str:
    return ADMIN_WEB_HTML
