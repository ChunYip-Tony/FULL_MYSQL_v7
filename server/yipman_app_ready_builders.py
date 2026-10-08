from __future__ import annotations

"""Concrete App Ready builders backed by the existing authoritative engines."""
from datetime import timedelta
import inspect
import api as _api
from business_clock import business_today, completed_through_date
from yipman_mobile_v1_stock_flow import stock_flow_review

_BUILD_CONTEXT = {}

def _memo(name, fn):
    if name not in _BUILD_CONTEXT:
        _BUILD_CONTEXT[name] = fn()
    return _BUILD_CONTEXT[name]
def _call_supported(fn, **kwargs):
    sig=inspect.signature(fn)
    if any(p.kind==inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):return fn(**kwargs)
    return fn(**{k:v for k,v in kwargs.items() if k in sig.parameters})
def _rows(payload):
    if isinstance(payload,dict):
        rows=payload.get('rows');return list(rows) if isinstance(rows,list) else []
    return list(payload) if isinstance(payload,list) else []
def _price_type(row):
    for key in ('suggestion_type','price_suggestion_type','recommendation_type','target_price_type','price_type'):
        value=str(row.get(key) or '').strip().upper().replace('-','_').replace(' ','_')
        if value:return value
    return ''
def _pricing_payload():return _memo('pricing',lambda:_api.backoffice_cached_pricing_review(category='ALL',limit=1000))
def _price_section(kind):
    rows=_rows(_pricing_payload())
    if kind=='REG':selected=[r for r in rows if _price_type(r) in {'REG','REGULAR','KEEP_REG','CHANGE_REG'}]
    elif kind=='TPR':selected=[r for r in rows if 'TPR' in _price_type(r) and 'CLEAR' not in _price_type(r)]
    elif kind=='CLEARANCE':selected=[r for r in rows if 'CLEAR' in _price_type(r)]
    else:selected=rows
    return {'source':'BACKOFFICE_CACHED_PRICING_REVIEW','kind':kind,'rows':selected,'all_row_count':len(rows)}
def _stock_flow():return {'source':'STOCK_FLOW_REVIEW','windows':{str(d):stock_flow_review(days=d,limit=120) for d in (7,14,28)}}
def _quick_check():return _call_supported(_api.search_quick_check,query='',q='',limit=5000)
def _regular_ordering_uncached():
    today=business_today();days={}
    for offset in range(14):
        delivery=today+timedelta(days=offset);nxt=delivery+timedelta(days=7)
        days[delivery.isoformat()]=_call_supported(_api.backoffice_cached_ordering_review,category='ALL',delivery_date=delivery,next_delivery_date=nxt,best_available_delivery_evidence=True)
    return {'source':'BACKOFFICE_CACHED_ORDERING_REVIEW','horizon_days':14,'deliveries':days}
def _regular_ordering():return _memo('ordering_regular',_regular_ordering_uncached)
def _promotion_ordering():return {'source':'PROMOTION_ORDERING','saved_lists':_call_supported(_api.list_yipman_promotion_lists,limit=1000)}
def _tpr_progress():return _memo('tpr_progress',lambda:_api.backoffice_cached_current_tpr_review(category='ALL',limit=1000))
def _inventory():return _call_supported(_api.backoffice_inventory_review,category='ALL',limit=5000)
def _performance():return {'source':'PERFORMANCE_RUNTIME','latest':_call_supported(_api.v2_latest_performance_date),'supported_dates':_call_supported(_api.v2_performance_supported_dates,limit=28)}
def _digits(v):return ''.join(c for c in str(v or '') if c.isdigit()).lstrip('0')
def _family(r):return str(r.get('family') or r.get('family_article') or r.get('family_id') or '').strip()
def _upc(r):return _digits(r.get('upc') or r.get('ean_upc') or r.get('ean'))
def _decision_intelligence():
    pricing=_pricing_payload();tpr=_tpr_progress();ordering=_regular_ordering();by_key={}
    def add(row,source,action):
        if not isinstance(row,dict):return
        item=dict(row);item['_snapshot_source']=source;item['_action_type']=action
        f=_family(row);u=_upc(row)
        for key in ((f'UPC:{u}:{action}' if u else ''),(f'UPC:{u}' if u else ''),(f'FAMILY:{f}:{action}' if f else ''),(f'FAMILY:{f}' if f else '')):
            if key and key not in by_key:by_key[key]=item
    for r in _rows(pricing):add(r,'PRICING','PRICE')
    for r in _rows(tpr):add(r,'TPR_PROGRESS','TPR')
    for delivery,payload in ordering['deliveries'].items():
        for r in _rows(payload):
            item=dict(r);item['_delivery_date']=delivery;add(item,'ORDERING','ORDER')
    return {'source':'AUTHORITATIVE_EXISTING_ENGINES','by_key':by_key,'pricing':pricing,'tpr_progress':tpr,'ordering':ordering,'data_through':completed_through_date().isoformat(),'policy':'PRECOMPUTED_AFTER_DATA_CHANGE_NOT_ON_PAGE_OPEN'}
def app_ready_builders():
    _BUILD_CONTEXT.clear()
    return {'stock_flow':_stock_flow,'quick_check':_quick_check,'ordering_regular':_regular_ordering,'ordering_promotion':_promotion_ordering,'price_reg':lambda:_price_section('REG'),'price_tpr_suggestions':lambda:_price_section('TPR'),'price_tpr_progress':_tpr_progress,'price_clearance':lambda:_price_section('CLEARANCE'),'inventory':_inventory,'performance':_performance,'decision_intelligence':_decision_intelligence}
