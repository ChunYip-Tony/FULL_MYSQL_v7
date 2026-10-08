from __future__ import annotations

"""Concrete App Ready builders backed by existing authoritative engines.

Expensive authoritative engines are memoized only for one snapshot generation,
so the same pricing/ordering/TPR calculation is not repeated for multiple
materialized sections. A new app_ready_builders() call creates a fresh cache.
"""

from datetime import timedelta
from typing import Any
import inspect
import api as _api
from business_clock import business_today, completed_through_date
from yipman_mobile_v1_stock_flow import stock_flow_review


def _call_supported(fn, **kwargs):
    sig=inspect.signature(fn)
    if any(p.kind==inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):return fn(**kwargs)
    return fn(**{k:v for k,v in kwargs.items() if k in sig.parameters})

def _rows(payload:Any)->list[dict[str,Any]]:
    if isinstance(payload,dict):
        rows=payload.get("rows");return list(rows) if isinstance(rows,list) else []
    return list(payload) if isinstance(payload,list) else []

def _price_type(row):
    for key in ("suggestion_type","price_suggestion_type","recommendation_type","target_price_type","price_type"):
        value=str(row.get(key) or "").strip().upper().replace("-","_").replace(" ","_")
        if value:return value
    return ""

def _price_section_from(payload,kind):
    rows=_rows(payload)
    if kind=="REG":selected=[r for r in rows if _price_type(r) in {"REG","REGULAR","KEEP_REG","CHANGE_REG"}]
    elif kind=="TPR":selected=[r for r in rows if "TPR" in _price_type(r) and "CLEAR" not in _price_type(r)]
    elif kind=="CLEARANCE":selected=[r for r in rows if "CLEAR" in _price_type(r)]
    else:selected=rows
    return {"source":"BACKOFFICE_CACHED_PRICING_REVIEW","kind":kind,"rows":selected,"all_row_count":len(rows)}

def _stock_flow():
    return {"source":"STOCK_FLOW_REVIEW","windows":{str(d):stock_flow_review(days=d,limit=120) for d in (7,14,28)}}

def _quick_check():return _call_supported(_api.search_quick_check,query="",q="",limit=5000)

def _regular_ordering():
    today=business_today();days={}
    for offset in range(14):
        delivery=today+timedelta(days=offset);nxt=delivery+timedelta(days=7)
        days[delivery.isoformat()]=_call_supported(_api.backoffice_cached_ordering_review,category="ALL",delivery_date=delivery,next_delivery_date=nxt,best_available_delivery_evidence=True)
    return {"source":"BACKOFFICE_CACHED_ORDERING_REVIEW","horizon_days":14,"deliveries":days}

def _promotion_ordering():return {"source":"PROMOTION_ORDERING","saved_lists":_call_supported(_api.list_yipman_promotion_lists,limit=1000)}
def _tpr_progress():return _api.backoffice_cached_current_tpr_review(category="ALL",limit=1000)
def _inventory():return _call_supported(_api.backoffice_inventory_review,category="ALL",limit=5000)
def _performance():return {"source":"PERFORMANCE_RUNTIME","latest":_call_supported(_api.v2_latest_performance_date),"supported_dates":_call_supported(_api.v2_performance_supported_dates,limit=28)}

def app_ready_builders()->dict[str,Any]:
    # Cache lifetime == one build generation. Never reuse across rebuilds.
    cache:dict[str,Any]={}
    def once(key,fn):
        def get():
            if key not in cache:cache[key]=fn()
            return cache[key]
        return get
    pricing=once("pricing",lambda:_api.backoffice_cached_pricing_review(category="ALL",limit=1000))
    ordering=once("ordering",_regular_ordering)
    tpr=once("tpr",_tpr_progress)
    quick=once("quick",_quick_check)
    def decision():
        return {"source":"AUTHORITATIVE_EXISTING_ENGINES","pricing":pricing(),"tpr_progress":tpr(),"ordering":ordering(),"data_through":completed_through_date().isoformat(),"policy":"PRECOMPUTED_AFTER_DATA_CHANGE_NOT_ON_PAGE_OPEN"}
    return {
        "stock_flow":_stock_flow,
        "quick_check":quick,
        "ordering_regular":ordering,
        "ordering_promotion":_promotion_ordering,
        "price_reg":lambda:_price_section_from(pricing(),"REG"),
        "price_tpr_suggestions":lambda:_price_section_from(pricing(),"TPR"),
        "price_tpr_progress":tpr,
        "price_clearance":lambda:_price_section_from(pricing(),"CLEARANCE"),
        "inventory":_inventory,
        "performance":_performance,
        "decision_intelligence":decision,
    }
