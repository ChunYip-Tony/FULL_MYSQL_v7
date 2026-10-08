from __future__ import annotations

"""Internal implementation routes consumed by official Yipman Mobile V1."""

import json
from datetime import date
import api as _api
from fastapi.responses import HTMLResponse, Response
from yipman_mobile_v1_exact_shell import yipman_mobile_v1_exact_html
from yipman_mobile_v1_price_guard import guard_price_html
from yipman_mobile_v1_price_polish import polish_price_html
from yipman_mobile_v1_price_upc_only import polish_price_upc_only_html
from yipman_mobile_v1_price_progress import polish_price_progress_html
from yipman_mobile_v1_interactions import polish_interactions_html
from yipman_mobile_v1_quick_search_polish import polish_quick_search_html
from yipman_mobile_v1_order_detail import polish_order_detail_html
from yipman_mobile_v1_family_detail import polish_family_detail_html
from yipman_mobile_v1_ordering_context import polish_ordering_context_html
from yipman_mobile_v1_loading_hotfix import polish_loading_html
from yipman_mobile_v1_ordering_reliability import polish_ordering_reliability_html
from yipman_mobile_v1_typography import polish_typography_html
from yipman_mobile_v1_navigation import polish_navigation_html
from yipman_mobile_v1_identity_guard import polish_identity_html
from yipman_mobile_v1_receipt_history import family_receipt_history
from yipman_mobile_v1_force_order_detail import polish_force_order_detail_html
from yipman_mobile_v1_stock_flow import stock_flow_review
from yipman_mobile_v1_stock_flow_home import polish_stock_flow_home_html
from yipman_mobile_v1_stock_flow_compact import polish_stock_flow_compact_html
from yipman_mobile_v1_family_mvt_fix import polish_family_mvt_fix_html
from yipman_mobile_v1_decision_compact import polish_decision_compact_html
from yipman_mobile_v1_all_decision_evidence import polish_all_decision_evidence_html
from yipman_mobile_v1_pwa import install_html as pwa_install_html, polish_pwa_html, pwa_icon_svg, pwa_manifest, pwa_service_worker
from yipman_app_ready_readers import stock_flow_snapshot, regular_ordering_snapshot

_INSTALLED=False

def install_mobile_v1_rc_route(app)->None:
 global _INSTALLED
 if _INSTALLED:return
 version=str(getattr(_api,"VERSION",""))
 def rc_page():
  html=yipman_mobile_v1_exact_html(version)
  for fn in (guard_price_html,polish_price_html,polish_price_upc_only_html,polish_price_progress_html,polish_quick_search_html,polish_identity_html,polish_interactions_html,polish_order_detail_html,polish_family_detail_html,polish_ordering_context_html,polish_loading_html,polish_ordering_reliability_html,polish_typography_html,polish_stock_flow_home_html,polish_stock_flow_compact_html,polish_pwa_html,polish_navigation_html,polish_force_order_detail_html,polish_family_mvt_fix_html,polish_decision_compact_html,polish_all_decision_evidence_html):html=fn(html)
  return HTMLResponse(html,headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-YipMan-Mobile-V1-RC":"app-ready-fast-read"})
 def rc_ordering_review_live(category:str="ALL",delivery_date:str|None=None,next_delivery_date:str|None=None):
  try:
   pd=date.fromisoformat(delivery_date) if delivery_date else None;pn=date.fromisoformat(next_delivery_date) if next_delivery_date else None
   # Normal app opens use the already-computed authoritative delivery snapshot.
   # Requests outside the precomputed 14-day horizon fall through to the same
   # live engine used before App Ready.
   result=regular_ordering_snapshot(delivery_date) if str(category or "ALL").upper()=="ALL" else None
   if result is None:
    result=_api.backoffice_ordering_review(category=category,delivery_date=pd,next_delivery_date=pn,best_available_delivery_evidence=True)
    if isinstance(result,dict):
     result=dict(result);result["viewing_moment_live"]=True;result["app_ready_snapshot"]=False;result["calculation_basis"]="CURRENT_EFFECTIVE_OH_AT_REQUEST_WITH_EXISTING_ORDERING_RULES"
   elif isinstance(result,dict):
    result=dict(result);result["viewing_moment_live"]=False
   return Response(json.dumps(result,default=_api.j),media_type="application/json",headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","X-YipMan-Data-Path":"APP_READY" if isinstance(result,dict) and result.get("app_ready_snapshot") else "LIVE_FALLBACK"})
  except ValueError as exc:return Response(json.dumps({"status":"INVALID","reason":str(exc)}),status_code=422,media_type="application/json",headers={"Cache-Control":"no-store"})
  except Exception as exc:return Response(json.dumps({"status":"ERROR","reason":str(exc)}),status_code=500,media_type="application/json",headers={"Cache-Control":"no-store"})
 def rc_family_receipt_history(family:str,limit_days:int=12):
  try:return Response(json.dumps(family_receipt_history(family,limit_days=limit_days),default=_api.j),media_type="application/json",headers={"Cache-Control":"no-store"})
  except KeyError as exc:return Response(json.dumps({"status":"NOT_FOUND","reason":str(exc)}),status_code=404,media_type="application/json",headers={"Cache-Control":"no-store"})
  except Exception as exc:return Response(json.dumps({"status":"ERROR","reason":str(exc)}),status_code=500,media_type="application/json",headers={"Cache-Control":"no-store"})
 def rc_stock_flow(days:int=7,limit:int=80):
  try:
   result=stock_flow_snapshot(days,limit)
   if result is None:
    result=stock_flow_review(days=days,limit=limit)
    if isinstance(result,dict):result=dict(result);result["app_ready_snapshot"]=False
   return Response(json.dumps(result,default=_api.j),media_type="application/json",headers={"Cache-Control":"no-store","X-YipMan-Data-Path":"APP_READY" if isinstance(result,dict) and result.get("app_ready_snapshot") else "LIVE_FALLBACK"})
  except ValueError as exc:return Response(json.dumps({"status":"INVALID","reason":str(exc)}),status_code=422,media_type="application/json",headers={"Cache-Control":"no-store"})
  except Exception as exc:return Response(json.dumps({"status":"ERROR","reason":str(exc)}),status_code=500,media_type="application/json",headers={"Cache-Control":"no-store"})
 def rc_manifest():return Response(pwa_manifest(),media_type="application/manifest+json",headers={"Cache-Control":"no-cache"})
 def rc_sw():return Response(pwa_service_worker(),media_type="application/javascript",headers={"Cache-Control":"no-cache","Service-Worker-Allowed":"/app/yipman-v1-rc/"})
 def rc_icon():return Response(pwa_icon_svg(),media_type="image/svg+xml",headers={"Cache-Control":"public, max-age=3600"})
 def rc_install():return HTMLResponse(pwa_install_html(version),headers={"Cache-Control":"no-store"})
 routes=[("/app/yipman-v1-rc/",rc_page,"yipman_mobile_v1_exact_mock_rc"),("/app/yipman-v1-rc",rc_page,"yipman_mobile_v1_exact_mock_rc_noslash"),("/app/yipman-v1-rc/api/ordering-review-live",rc_ordering_review_live,"yipman_mobile_v1_rc_ordering_review_live"),("/app/yipman-v1-rc/api/family-receipts",rc_family_receipt_history,"yipman_mobile_v1_rc_family_receipt_history"),("/app/yipman-v1-rc/api/stock-flow",rc_stock_flow,"yipman_mobile_v1_rc_stock_flow"),("/app/yipman-v1-rc/manifest.webmanifest",rc_manifest,"yipman_mobile_v1_rc_manifest"),("/app/yipman-v1-rc/sw.js",rc_sw,"yipman_mobile_v1_rc_service_worker"),("/app/yipman-v1-rc/icon.svg",rc_icon,"yipman_mobile_v1_rc_icon"),("/app/yipman-v1-rc/install",rc_install,"yipman_mobile_v1_rc_install"),("/app/yipman-v1-rc/install/",rc_install,"yipman_mobile_v1_rc_install_slash")]
 for path,fn,name in routes:app.add_api_route(path,fn,methods=["GET"],include_in_schema=False,name=name)
 app.state.yipman_mobile_v1_consolidated_rc={"enabled":True,"path":"/app/yipman-v1-rc/","production_v1_unchanged":False,"app_ready_fast_read":True,"live_fallback":True,"compact_ordering":True,"primary_decision_details":True,"all_primary_decisions_have_explanation_evidence":True,"decision_evidence_missing_is_explicit":True,"install_path":"/app/yipman-v1-rc/install"}
 _INSTALLED=True
