from __future__ import annotations

"""Stable production API entrypoint.

Product channels are intentionally fixed:
- Mobile: Yipman Mobile V1 -> /app/yipman-v1/
- Desktop: Yipman Back Office -> /app/backoffice and /yipman

Versioned api_entry_v* modules are implementation layers only. The service
launcher must import this module so future internal releases do not create a
new production app identity or deployment entrypoint.
"""

from decimal import Decimal
import api as _api
import api_entry_v481 as _current
import yipman_price_policy_v488 as _pricing_policy
from yipman_qa_page_v485 import inject_qa_hard_link, register_qa_page

app = _current.app

# source_data_days is newest-first by design. The pricing policy evaluates a
# chronological 7-day price-step cycle, so give that policy an oldest-first
# view without changing the canonical helper for the rest of the application.
_policy_source_data_days = _pricing_policy.source_data_days

def _policy_days_chronological(*args, **kwargs):
    return sorted(_policy_source_data_days(*args, **kwargs), key=lambda x: x.get("date"))

_pricing_policy.source_data_days = _policy_days_chronological
apply_pricing_review_policy = _pricing_policy.apply_pricing_review_policy
apply_current_tpr_policy = _pricing_policy.apply_current_tpr_policy

# Capture the actual renderers used by both desktop URLs. /yipman calls
# api.yipman_html directly, while /app/backoffice calls api.backoffice_html.
_base_mobile_v1_html = _api.yipman_v1_html
_base_yipman_html = _api.yipman_html
_base_backoffice_html = _api.backoffice_html

# Capture API callables before wrapping them. The FastAPI endpoint functions
# resolve these module globals at request time, so replacing the globals here
# updates both /v1/backoffice/* and /v1/yipman/* without changing route identity.
_base_pricing_review = _api.backoffice_pricing_review
_base_cached_pricing_review = _api.backoffice_cached_pricing_review
_base_current_tpr_review = _api.backoffice_current_tpr_review
_base_cached_current_tpr_review = _api.backoffice_cached_current_tpr_review

_QA_BUTTON_STYLE = '''
<style id="ydQaButtonV487">
@media (min-width:760px){
  #ydesk #ydQaHardLinkV485{
    min-width:104px!important;background:#ffffff!important;color:#102842!important;
    border:2px solid #82bfff!important;border-radius:11px!important;
    box-shadow:0 2px 8px rgba(0,18,42,.22)!important;text-decoration:none!important;
    cursor:pointer!important;position:relative!important;
    transition:background .12s ease,border-color .12s ease,transform .12s ease,box-shadow .12s ease!important;
  }
  #ydesk #ydQaHardLinkV485:hover,#ydesk #ydQaHardLinkV485:focus-visible{
    background:#eaf5ff!important;border-color:#2f91ff!important;
    box-shadow:0 4px 12px rgba(0,18,42,.28)!important;transform:translateY(-1px)!important;outline:none!important;
  }
  #ydesk #ydQaHardLinkV485:after{
    content:'OPEN';position:absolute;top:5px;right:6px;padding:1px 4px;border-radius:999px;
    background:#0b72f4;color:#fff;font-size:7px;line-height:1.3;font-weight:950;letter-spacing:.25px;
  }
  #ydesk #ydQaHardLinkV485 b{color:#102842!important;font-size:17px!important}
}
</style>
'''

_DESKTOP_READABILITY_STYLE = '''
<style id="ydReadabilityV488">
@media (min-width:760px){
  #ydesk .app{grid-template-columns:248px minmax(0,1fr)!important}
  #ydesk .side{padding:18px 14px!important}
  #ydesk .brand h1{font-size:30px!important}
  #ydesk .brand small{font-size:11px!important}
  #ydesk .navbtn{font-size:15px!important;padding:12px 12px!important;gap:11px!important}
  #ydesk .navbtn .ico{font-size:18px!important;width:23px!important}
  #ydesk .fresh h4{font-size:12px!important}
  #ydesk .frow{font-size:11px!important}
  #ydesk .version{font-size:10px!important;line-height:1.35!important}
  #ydesk .topbar{height:68px!important;padding:0 20px!important;gap:14px!important}
  #ydesk .gsearch{height:44px!important;width:min(760px,50vw)!important}
  #ydesk .gsearch input{font-size:15px!important}
  #ydesk .kbd{font-size:10px!important}
  #ydesk .live{font-size:10px!important;padding:5px 9px!important}
  #ydesk .topstats{gap:9px!important}
  #ydesk .topstat{font-size:9.5px!important;min-width:84px!important;padding:7px 10px!important}
  #ydesk .topstat b{font-size:17px!important}
  #ydesk .avatar{width:38px!important;height:38px!important;font-size:11px!important}
  #ydesk .work{padding:21px 22px 34px!important}
  #ydesk .pagehead h2{font-size:34px!important}
  #ydesk .pagehead p{font-size:13px!important}
  #ydesk .btn{font-size:12px!important;padding:8px 11px!important}
  #ydesk .input,#ydesk .select{height:38px!important;font-size:13px!important}
  #ydesk .cardhead{padding:12px 14px!important}
  #ydesk .cardhead h3{font-size:14px!important}
  #ydesk .cardbody{padding:13px 14px!important}
  #ydesk .badge{font-size:10.5px!important;padding:5px 8px!important}
  #ydesk .small{font-size:12px!important}
  #ydesk .tiny{font-size:10.5px!important;line-height:1.35!important}
  #ydesk .kpi{padding:10px 11px!important}
  #ydesk .kpi label{font-size:9.5px!important}
  #ydesk .kpi strong{font-size:21px!important}
  #ydesk .kpi small{font-size:10.5px!important}
  #ydesk .tab,#ydesk .qf{font-size:11.5px!important;padding:8px 10px!important}
  #ydesk th{font-size:9.5px!important;padding:9px 9px!important}
  #ydesk td{font-size:11.5px!important;padding:9px 9px!important}
  #ydesk .stockflow-head h3{font-size:19px!important}
  #ydesk .stockflow-head p{font-size:10.5px!important}
  #ydesk .stockflow-count{font-size:11.5px!important}
  #ydesk .sfid b{font-size:14.5px!important}
  #ydesk .sfid strong{font-size:16px!important}
  #ydesk .sfmetric b,#ydesk .sfdiff b{font-size:20px!important}
  #ydesk .fname .id{font-size:11.5px!important}
  #ydesk .fname .desc{font-size:15.5px!important}
  #ydesk .fm label{font-size:8.5px!important}
  #ydesk .fm strong{font-size:17px!important}
  #ydesk .recvhead,#ydesk .sap{font-size:10.5px!important}
  #ydesk .upcrow{font-size:11.5px!important}
  #ydesk .priceTable .priceItem b{font-size:12.5px!important}
  #ydesk .sectiontitle{font-size:12px!important}
  #ydesk .note{font-size:11.5px!important;line-height:1.45!important}
  #ydesk .kv{font-size:11.5px!important}
  #ydesk .split{grid-template-columns:minmax(0,1.35fr) minmax(360px,.65fr)!important}
}
</style>
'''

_UPC_ROLE_SCRIPT = r'''
<script id="ydUpcRoleV488">
(function(){
  const rank={"240":0,"249":1,"245":2,"247":3};
  function pfx(v){return String(v||'').replace(/^0+/,'').slice(0,3)}
  function rr(v){const p=pfx(v);return Object.prototype.hasOwnProperty.call(rank,p)?rank[p]:9}
  function reorderPair(pair){
    const rows=[...pair.querySelectorAll(':scope > .upcrow')];if(rows.length<2)return;
    const sorted=rows.slice().sort((a,b)=>rr(a.dataset.upc)-rr(b.dataset.upc));
    if(rows.every((x,i)=>x===sorted[i]))return;sorted.forEach(x=>pair.appendChild(x));
  }
  function reorderDetail(tbody){
    const rows=[...tbody.querySelectorAll(':scope > tr')];if(rows.length<2)return;
    const upc=r=>((r.cells&&r.cells[0])?r.cells[0].textContent:'');
    const sorted=rows.slice().sort((a,b)=>rr(upc(a))-rr(upc(b)));
    if(rows.every((x,i)=>x===sorted[i]))return;sorted.forEach(x=>tbody.appendChild(x));
  }
  function apply(){
    document.querySelectorAll('#ydesk .pair').forEach(reorderPair);
    document.querySelectorAll('#ydesk .qpanel[data-qp="1"] tbody').forEach(reorderDetail);
    document.querySelectorAll('#ydesk .upcrow').forEach(r=>{
      const p=pfx(r.dataset.upc),label=p==='240'?'MAIN':p==='249'?'2ND':p==='245'?'3RD':p==='247'?'LAST':'';
      const badge=r.querySelector('.prefix');
      if(badge&&label&&!badge.dataset.roleDone){badge.dataset.roleDone='1';badge.title=(label==='MAIN'?'Main selling UPC':label==='2ND'?'Secondary 249 service UPC':label==='3RD'?'Third 245 UPC':'Last 247 UPC');}
    });
  }
  let queued=false;
  new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;apply()})}).observe(document.documentElement,{childList:true,subtree:true});
  addEventListener('DOMContentLoaded',apply);setTimeout(apply,700);setInterval(apply,2500);
})();
</script>
'''


def _decorate_desktop(html: str) -> str:
    html = inject_qa_hard_link(html)
    if 'ydQaButtonV487' not in html:
        html = html.replace('</head>', _QA_BUTTON_STYLE + '</head>', 1)
    if 'ydReadabilityV488' not in html:
        html = html.replace('</head>', _DESKTOP_READABILITY_STYLE + '</head>', 1)
    if 'ydUpcRoleV488' not in html:
        html = html.replace('</body>', _UPC_ROLE_SCRIPT + '</body>', 1)
    return html


def _official_mobile_v1_html(version: str = "") -> str:
    html = _base_mobile_v1_html(version)
    html = html.replace("<title>Yipman</title>", "<title>Yipman Mobile V1</title>", 1)
    html = html.replace('content="Yipman">','content="Yipman Mobile V1">',1)
    return html


def _official_yipman_html(version: str = "") -> str:
    return _decorate_desktop(_base_yipman_html(version))


def _official_backoffice_html(version: str = "") -> str:
    html = _base_backoffice_html(version)
    html = html.replace("<title>Yipman</title>", "<title>Yipman Back Office</title>", 1)
    return _decorate_desktop(html)


def _preserve_original_order(original: dict, patched: dict) -> dict:
    order = {str(r.get('upc') or ''): i for i, r in enumerate(original.get('rows') or [])}
    rows = list(patched.get('rows') or [])
    rows.sort(key=lambda r: order.get(str(r.get('upc') or ''), 10**9))
    patched['rows'] = rows
    return patched


def _finalize_price_action_fields(payload: dict) -> dict:
    for row in payload.get('rows') or []:
        final_price = row.get('final_tpr_price_suggestion')
        decision = str(row.get('final_tpr_decision') or '')
        if decision == 'START_TPR' and final_price is not None:
            row['testing_price'] = final_price
            row['tpr_suggestion_price'] = final_price
            row['candidate_price'] = final_price
            row['suggested_price'] = final_price
            row['tpr_suggestion_actionable'] = True
            row['actionable'] = True
            row['review_status'] = 'ACTIONABLE'
            cost = row.get('current_cost')
            try:
                p = Decimal(str(final_price)); c = Decimal(str(cost))
                if p > 0:
                    row['testing_price_gp_pct'] = (p-c)/p
            except Exception:
                pass
    return payload


def _pricing_review_v489(*args, **kwargs):
    original = _base_pricing_review(*args, **kwargs)
    patched = _finalize_price_action_fields(apply_pricing_review_policy(original))
    return _preserve_original_order(original, patched)


def _cached_pricing_review_v489(*args, **kwargs):
    original = _base_cached_pricing_review(*args, **kwargs)
    patched = _finalize_price_action_fields(apply_pricing_review_policy(original))
    return _preserve_original_order(original, patched)


def _current_tpr_review_v489(*args, **kwargs):
    original = _base_current_tpr_review(*args, **kwargs)
    return _preserve_original_order(original, apply_current_tpr_policy(original))


def _cached_current_tpr_review_v489(*args, **kwargs):
    original = _base_cached_current_tpr_review(*args, **kwargs)
    return _preserve_original_order(original, apply_current_tpr_policy(original))


_api.yipman_v1_html = _official_mobile_v1_html
_api.yipman_html = _official_yipman_html
_api.backoffice_html = _official_backoffice_html
_api.backoffice_pricing_review = _pricing_review_v489
_api.backoffice_cached_pricing_review = _cached_pricing_review_v489
_api.backoffice_current_tpr_review = _current_tpr_review_v489
_api.backoffice_cached_current_tpr_review = _cached_current_tpr_review_v489

# Dedicated server-rendered target for the QA Holds hyperlink.
register_qa_page(app, version=_api.VERSION, qa_loader=_api.backoffice_qa_review)

app.state.yipman_product_channels = {
    "mobile": {
        "name": "Yipman Mobile V1",
        "path": "/app/yipman-v1/",
        "install_path": "/app/yipman-v1/install/",
        "status": "production",
    },
    "desktop": {
        "name": "Yipman Back Office",
        "path": "/yipman",
        "alternate_path": "/app/backoffice",
        "status": "production",
    },
    "legacy": {
        "path": "/app/yipman",
        "status": "compatibility-only",
    },
}
