from __future__ import annotations

"""Concrete App Ready builders backed by existing authoritative engines."""
from datetime import timedelta
from typing import Any
import inspect
import api as _api
from business_clock import business_today, completed_through_date
from yipman_mobile_v1_stock_flow import stock_flow_review

def _call_supported(fn,**kwargs):
    sig=inspect.signature(fn)
    if any(p.kind==inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):return fn(**kwargs)
    return fn(**{k:v for k,v in kwargs.items() if k in sig.parameters})
def _rows(p):
    if isinstance(p,dict):return list(p.get('rows')) if isinstance(p.get('rows'),list) else []
    return list(p) if isinstance(p,list) else []
def _price_type(r):
    for k in ('suggestion_type','price_suggestion_type','recommendation_type','target_price_type','price_type'):
        v=str(r.get(k) or '').strip().upper().replace('-','_').replace(' ','_')
        if v:return v
    return ''
def _price_section_from(p,k):
    rows=_rows(p)
    if k=='REG':s=[r for r in rows if _price_type(r) in {'REG','REGULAR','KEEP_REG','CHANGE_REG'}]
    elif k=='TPR':s=[r for r in rows if 'TPR' in _price_type(r) and 'CLEAR' not in _price_type(r)]
    elif k=='CLEARANCE':s=[r for r in rows if 'CLEAR' in _price_type(r)]
    else:s=rows
    return {'source':'BACKOFFICE_CACHED_PRICING_REVIEW','kind':k,'rows':s,'all_row_count':len(rows)}
def _stock_flow():return {'source':'STOCK_FLOW_REVIEW','windows':{str(d):stock_flow_review(days=d,limit=120) for d in (7,14,28)}}
def _quick_check():return _call_supported(_api.search_quick_check,query='',q='',limit=5000)
def _regular_ordering():
    today=business_today();days={}
    for off in range(14):
        d=today+timedelta(days=off);n=d+timedelta(days=7)
        days[d.isoformat()]=_call_supported(_api.backoffice_cached_ordering_review,category='ALL',delivery_date=d,next_delivery_date=n,best_available_delivery_evidence=True)
    return {'source':'BACKOFFICE_CACHED_ORDERING_REVIEW','horizon_days':14,'deliveries':days}
def _promotion_ordering():return {'source':'PROMOTION_ORDERING','saved_lists':_call_supported(_api.list_yipman_promotion_lists,limit=1000)}
def _tpr_progress():return _api.backoffice_cached_current_tpr_review(category='ALL',limit=1000)
def _inventory():return _call_supported(_api.backoffice_inventory_review,category='ALL',limit=5000)
def _performance():return {'source':'PERFORMANCE_RUNTIME','latest':_call_supported(_api.v2_latest_performance_date),'supported_dates':_call_supported(_api.v2_performance_supported_dates,limit=28)}
def _digits(v):return ''.join(c for c in str(v or '') if c.isdigit()).lstrip('0')
def _family(r):return str(r.get('family') or r.get('family_article') or r.get('family_id') or r.get('main_article_number') or '').strip()
def _upc(r):return _digits(r.get('upc') or r.get('ean_upc') or r.get('ean'))
def _decision_index(pricing,tpr,ordering):
    """Exact UPC keys win; family keys are only family-level fallbacks."""
    by={}
    def add(r,action=''):
        if not isinstance(r,dict):return
        u,f=_upc(r),_family(r);a=str(action or _price_type(r)).strip().upper()
        if u:
            by.setdefault('UPC:'+u,r)
            if a:by.setdefault('UPC:'+u+':'+a,r)
        if f:
            by.setdefault('FAMILY:'+f,r)
            if a:by.setdefault('FAMILY:'+f+':'+a,r)
    for r in _rows(pricing):add(r)
    for r in _rows(tpr):add(r,'TPR_PROGRESS')
    for day in (ordering.get('deliveries') or {}).values():
        for r in _rows(day):add(r,'ORDERING')
    return by

def app_ready_builders()->dict[str,Any]:
    cache={}
    def once(k,fn):
        def get():
            if k not in cache:cache[k]=fn()
            return cache[k]
        return get
    pricing=once('pricing',lambda:_api.backoffice_cached_pricing_review(category='ALL',limit=1000));ordering=once('ordering',_regular_ordering);tpr=once('tpr',_tpr_progress);quick=once('quick',_quick_check)
    def decision():
        p,t,o=pricing(),tpr(),ordering()
        return {'source':'AUTHORITATIVE_EXISTING_ENGINES','pricing':p,'tpr_progress':t,'ordering':o,'by_key':_decision_index(p,t,o),'data_through':completed_through_date().isoformat(),'policy':'PRECOMPUTED_AFTER_DATA_CHANGE_NOT_ON_PAGE_OPEN'}
    return {'stock_flow':_stock_flow,'quick_check':quick,'ordering_regular':ordering,'ordering_promotion':_promotion_ordering,'price_reg':lambda:_price_section_from(pricing(),'REG'),'price_tpr_suggestions':lambda:_price_section_from(pricing(),'TPR'),'price_tpr_progress':tpr,'price_clearance':lambda:_price_section_from(pricing(),'CLEARANCE'),'inventory':_inventory,'performance':_performance,'decision_intelligence':decision}
