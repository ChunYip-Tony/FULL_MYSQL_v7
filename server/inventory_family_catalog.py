"""Family inventory browsing: rank the full matching roster before paging."""
from collections import OrderedDict
from decimal import Decimal
import threading
import time

def rank_page(rows, metrics, *, cursor=0, limit=30, sort='velocity7', status='all', unit='all', category='ALL', overrides=None):
    if cursor < 0 or not 1 <= limit <= 100 or sort not in ('velocity7','velocity14','name','article') or status not in ('all','verified','unknown'):
        raise ValueError('Invalid inventory controls')
    out=[]
    for original in rows:
        row=dict(original)
        row['category']=(overrides or {}).get(str(row['family_id']),row.get('category','UNKNOWN'))
        if category!='ALL' and row['category']!=category: continue
        row.update(metrics.get(int(row['family_id']), {'velocity7':None,'velocity14':None,'movement_uom':''}))
        value=row['velocity14' if sort=='velocity14' else 'velocity7']
        if status=='verified' and value is None or status=='unknown' and value is not None:
            continue
        if unit != 'all' and row['movement_uom'] != unit:
            continue
        out.append(row)
    if sort in ('velocity7','velocity14'):
        out.sort(key=lambda r:(r[sort] is None, -(r[sort] or 0),int(r['family_id'])))
    else:
        out.sort(key=lambda r:(str(r['family_description'] if sort=='name' else r['main_article_number']).casefold(),int(r['family_id'])))
    return {'contract_version':'MOBILE_INVENTORY_CATALOG_V2','scope':'ALL_PRODUCT_FAMILIES','total':len(out),'rows':out[cursor:cursor+limit],'next_cursor':str(cursor+limit) if cursor+limit<len(out) else None,'sort':sort,'status':status,'unit':unit}

def read_roster(query):
    from db import db_conn
    from mobile_inventory_catalog import read_catalog
    from data_coverage import source_data_days
    from business_clock import completed_through_date
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            rows=[]; after=0
            while True:
                page=read_catalog(cur,query=query,cursor=after,limit=100)
                rows.extend(page['rows'])
                if page['next_cursor'] is None: break
                after=int(page['next_cursor'])
            from mobile_pricing import category_index
            from business_clock import business_today
            categories=category_index(cur,rows,business_today())
            for row in rows: row['category']=categories.get(int(row['family_id']),{}).get('category','UNKNOWN')
            days=sorted(source_data_days(cur,'movement',limit=14,up_to=completed_through_date()),key=lambda d:d['date'])
            if not days: return rows,{},[]
            clauses=[];args=[]
            for day in days:
                clauses.append('(file_id=%s AND posting_date=%s)')
                args.extend([int(day['file_id']),day['date']])
            cur.execute('SELECT family_id,posting_date,base_uom_code,SUM(net_sold_quantity) AS q FROM family_movement_observation WHERE ('+' OR '.join(clauses)+') GROUP BY family_id,posting_date,base_uom_code',tuple(args))
            groups={}
            for row in cur.fetchall():
                if row['q'] is not None and str(row['base_uom_code'] or '').strip():
                    groups.setdefault(int(row['family_id']),[]).append(row)
            metrics={}
            for fid,observations in groups.items():
                m={}
                units=set()
                for count in (7,14):
                    window=days[-count:];selected={d['date'] for d in window}
                    evidence=[r for r in observations if r['posting_date'] in selected]
                    uoms={str(r['base_uom_code']).strip().upper() for r in evidence}
                    qty=sum((Decimal(str(r['q'])) for r in evidence),Decimal(0))
                    valid=bool(evidence) and len(uoms)==1 and qty.is_finite() and qty>=0
                    m['velocity'+str(count)]=qty/len(window) if valid else None
                    m['uom'+str(count)]=next(iter(uoms)) if valid else ''
                    units.update(uoms)
                m['movement_uom']=m['uom7'] or m['uom14']
                metrics[fid]=m
            # Search results are bounded; recover absent derived mirrors without
            # issuing thousands of per-family reads during the full roster scan.
            if query and len(rows)<=30:
                from webapp_v2_runtime import _ordering_family_movement_metrics
                for row in rows:
                    fid=int(row['family_id'])
                    if fid in metrics:
                        continue
                    recovered={}
                    for count in (7,14):
                        value=_ordering_family_movement_metrics(cur,fid,days[-count:])
                        valid=value.get('status')=='READY' and value.get('uom') and value.get('quantity') is not None
                        recovered['velocity'+str(count)]=value.get('velocity_per_supported_day') if valid else None
                        recovered['uom'+str(count)]=value.get('uom') if valid else ''
                    recovered['movement_uom']=recovered['uom7'] or recovered['uom14']
                    metrics[fid]=recovered
            return rows,metrics,[str(d['date']) for d in days]
        finally:
            cur.close()

_cache=OrderedDict()
_lock=threading.Lock()
def install_family_catalog(app):
    from fastapi import HTTPException
    from fastapi.encoders import jsonable_encoder
    from read_singleflight import ReadSingleFlight,ReadBusy
    reads=ReadSingleFlight(max_running=2,wait_seconds=20)
    @app.get('/v1/app/inventory-family-catalog')
    def catalog(q:str='',cursor:int=0,limit:int=30,sort:str='velocity7',status:str='all',unit:str='all',category:str='ALL',overrides:str='{}'):
        import json
        try:
            custom=json.loads(overrides)
            if not isinstance(custom,dict) or len(custom)>5000 or any(not str(k).isdigit() or v not in ('LIVE','FRESH','FROZEN') for k,v in custom.items()): raise ValueError()
        except (ValueError,TypeError): raise HTTPException(422,'Invalid category corrections')
        query=' '.join(q.strip().split()).lower()
        if category not in ('ALL','LIVE','FRESH','FROZEN','UNKNOWN') or len(query)>80 or cursor<0 or not 1<=limit<=100 or sort not in ('velocity7','velocity14','name','article') or status not in ('all','verified','unknown') or unit not in ('all','LB','EA','KG','OZ','PC','CS'):
            raise HTTPException(422,'Invalid inventory controls')
        def produce():
            with _lock:
                old=_cache.get(query)
                if old and time.monotonic()-old[0]<300: return old[1]
            result=read_roster(query)
            with _lock:
                _cache[query]=(time.monotonic(),result)
                while len(_cache)>30: _cache.popitem(last=False)
            return result
        try:
            rows,metrics,dates=reads.run(query,produce)
            result=rank_page(rows,metrics,cursor=cursor,limit=limit,sort=sort,status=status,unit=unit,category=category,overrides=custom)
            result.update(query=query,movement_dates=dates)
            return jsonable_encoder(result)
        except ReadBusy:
            raise HTTPException(503,'Inventory catalog busy. Retry shortly.')

