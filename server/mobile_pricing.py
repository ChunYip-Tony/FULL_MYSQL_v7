"""Read-only, canonical POS evidence shared by mobile pricing and Quick Check.

Never writes prices, counts or synthetic sales. Unknown exposure/cost stays null.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from collections import OrderedDict
import threading
import json
import time
from read_singleflight import ReadSingleFlight, ReadBusy
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

router = APIRouter()
PRIORITY = {'REG': 1, 'TPR': 2, 'SALE': 3, 'IN STORE': 4, 'IN_STORE': 4}
COST_ORDER = (
    {'MOVEMENT_RECEIPT_VALUATION'},
    {'FROZEN_INVENTORY_OFFICIAL_COST', 'LIVE_FRESH_SUGGESTION_OFFICIAL_COST'},
    {'ON_HAND_EXPLICIT_COST_FALLBACK'},
)

def num(value):
    try:
        n = Decimal(str(value))
        return n if n.is_finite() else None
    except Exception:
        return None

def cost_for_day(row, observations, day):
    selling = str(row.get('selling_uom') or '').strip().upper()
    base = str(row.get('base_uom') or '').strip().upper()
    factor = num(row.get('base_qty_per_selling_unit'))
    for sources in COST_ORDER:
        candidates = sorted((o for o in observations if o.get('source_type') in sources
            and o.get('business_date') and o['business_date'] <= day),
            key=lambda o: (o['business_date'], o.get('cost_observation_id') or 0), reverse=True)
        for obs in candidates:
            value, unit = num(obs.get('cost_value')), str(obs.get('cost_uom') or '').upper()
            if value is None or value <= 0 or not selling:
                continue
            if unit == selling:
                converted = value
            elif unit == base and factor is not None and factor > 0:
                converted = value * factor
            else:
                continue
            return {'value': converted, 'date': obs['business_date'], 'source': obs['source_type'], 'uom': selling}
    return None

def group_key(row):
    digits = ''.join(c for c in str(row.get('ean_upc') or '') if c.isdigit()).lstrip('0')
    if len(digits) >= 6 and digits[:3] in {'240', '249'} and row.get('family_id'):
        return 'pair:%s:%s' % (row['family_id'], digits[3:6])
    return 'upc:%s' % row['upc_id']

def price_snapshots(cur, rows):
    """Upload day is the authority; source_since_date never backdates a test."""
    from phase3 import _price_list_upload_business_date
    ids = [int(r['upc_id']) for r in rows]
    eans = [str(r['ean_upc']) for r in rows if r.get('ean_upc')]
    if not ids:
        return {}
    cur.execute("""SELECT file_id,upload_timestamp FROM ingest_file
        WHERE source_type='price_list' AND processing_status='INGESTED'
        AND error_count=0 AND duplicate_of_file_id IS NULL AND upload_timestamp IS NOT NULL
        ORDER BY upload_timestamp DESC,file_id DESC LIMIT 120""")
    files = {int(f['file_id']): f for f in cur.fetchall()}
    if not files:
        return {}
    placeholders = lambda xs: ','.join(['%s'] * len(xs))
    cur.execute(f"""SELECT file_id,upc_id,ean_upc,configured_price,price_type
        FROM price_list_observation WHERE file_id IN ({placeholders(files)})
        AND (upc_id IN ({placeholders(ids)}) OR ean_upc IN ({placeholders(eans) or 'NULL'}))
        AND configured_price>0""", (*files, *ids, *eans))
    aliases = {}
    for row in rows:
        key = str(row.get('ean_upc') or '').lstrip('0')
        aliases.setdefault(key, set()).add(int(row['upc_id']))
    choices = {}
    for p in cur.fetchall():
        uid = p.get('upc_id')
        if uid not in ids:
            found = aliases.get(str(p.get('ean_upc') or '').lstrip('0'), set())
            uid = next(iter(found)) if len(found) == 1 else None
        if uid not in ids:
            continue
        key = (uid, int(p['file_id']))
        pt = str(p.get('price_type') or '').upper()
        if pt not in PRIORITY:
            continue
        old = choices.get(key)
        if old is None or PRIORITY[pt] > PRIORITY[old['type']]:
            choices[key] = {'type': pt, 'price': num(p['configured_price']),
                'date': _price_list_upload_business_date(files[key[1]]['upload_timestamp']),
                'file_id': key[1], 'source': 'PRICE_LIST'}
    out = {}
    for (uid, _), value in choices.items():
        out.setdefault(uid, []).append(value)
    for values in out.values():
        values.sort(key=lambda p: (p['date'], p['file_id']))
    return out

def day_evidence(row, day, observation, snapshots, costs, current_cost):
    configured = next((p for p in reversed(snapshots) if p['date'] < day), None)
    # Intraday uploads do not prove a whole day of exposure or zero sales.
    on_day_upload = any(p['date'] == day for p in snapshots)
    cost = cost_for_day(row, costs, day)
    result = {'date': day, 'qty': None, 'sales': None, 'price': None, 'type': None,
        'gp': None, 'normalized_gp': None, 'valid': False, 'reason': None,
        'cost': cost, 'zero_sale': False}
    types = observation.get('price_types') or {} if observation else {}
    if observation:
        qty, sales = num(observation.get('sold_quantity')), num(observation.get('sales_amount'))
        result.update(qty=qty, sales=sales)
        if qty is None or sales is None or qty < 0 or sales < 0 or (qty == 0 and sales != 0):
            result['reason'] = 'QUANTITY_OR_RETURN_REVIEW'
            return result
        active = [(pt, v) for pt, v in types.items()
                  if num(v.get('sold_quantity')) != 0 or num(v.get('sales_amount')) != 0]
        if len(active) > 1:
            result['reason'] = 'MIXED_PRICE_DAY'
            return result
        if qty > 0:
            price, pt = sales / qty, active[0][0] if active else 'UNKNOWN'
            if pt not in PRIORITY or price <= 0:
                result['reason'] = 'PRICE_TYPE_UNVERIFIED'
                return result
            # A daily actual average is a reference, not a fabricated ticket price.
            if configured and configured['type'] == pt and abs(configured['price'] - price) <= Decimal('.02'):
                price = configured['price']
            result.update(price=price.quantize(Decimal('.01')), type=pt)
        elif configured and not on_day_upload:
            result.update(price=configured['price'], type=configured['type'], zero_sale=True)
        else:
            result['reason'] = 'PRICE_EXPOSURE_UNVERIFIED'
            return result
    elif configured and not on_day_upload:
        result.update(qty=Decimal(0), sales=Decimal(0), price=configured['price'], type=configured['type'], zero_sale=True)
    else:
        result['reason'] = 'PRICE_EXPOSURE_UNVERIFIED'
        return result
    if not cost:
        result['reason'] = 'COST_OR_UNIT_UNVERIFIED'
        return result
    result['gp'] = result['sales'] - result['qty'] * cost['value']
    if current_cost:
        result['normalized_gp'] = result['sales'] - result['qty'] * current_cost['value']
    result['valid'] = True
    return result


_category_cache = (0, {})
def category_index(cur, rows, today):
    """Same receipt-weekday rules and confirmed exceptions as the mobile stock model."""
    global _category_cache
    if _category_cache[0] > 0 and time.monotonic() - _category_cache[0] < 300 and all(int(r['family_id']) in _category_cache[1] for r in rows):
        return _category_cache[1]
    from data_coverage import source_data_days
    from business_clock import completed_through_date
    from receipt_semantics import physical_receipt_stage_rows
    fids = {int(r['family_id']) for r in rows if r.get('family_id')}
    # Category classification needs dates, not every raw receipt payload in
    # the whole store. Aggregate only the physical receipt evidence columns.
    days = source_data_days(cur, 'movement', limit=90, up_to=completed_through_date())
    canonical = {d['date']:int(d['file_id']) for d in days}
    dates_by_family = {}
    if canonical and fids:
        file_ids = sorted(set(canonical.values()))
        ph = lambda xs: ','.join(['%s'] * len(xs))
        cur.execute(f"""SELECT family_id,posting_date,file_id,article_id,purchase_order,
                article_document,movement_type,entry_uom_code,base_uom_code,
                SUM(entry_quantity) AS entry_quantity,SUM(base_quantity) AS base_quantity
            FROM movement_history WHERE family_id IN ({ph(fids)})
              AND file_id IN ({ph(file_ids)}) AND movement_type IN ('101','102','109','110')
            GROUP BY family_id,posting_date,file_id,article_id,purchase_order,
                article_document,movement_type,entry_uom_code,base_uom_code""", (*fids,*file_ids))
        receipt_groups = {}
        for r in cur.fetchall():
            if canonical.get(r['posting_date']) != int(r['file_id']):
                continue
            k = (int(r['family_id']),r['posting_date'],r['article_id'],r['purchase_order'],r['article_document'])
            receipt_groups.setdefault(k,[]).append(r)
        for key, values in receipt_groups.items():
            chosen,_ = physical_receipt_stage_rows(values)
            units = {r.get('base_uom_code') for r in chosen if r.get('base_quantity') is not None}
            if len(units)==1 and sum((num(r.get('base_quantity')) or Decimal(0) for r in chosen),Decimal(0))>0:
                dates_by_family.setdefault(key[0],set()).add(key[1])
            else:
                units = {r.get('entry_uom_code') for r in chosen if r.get('entry_quantity') is not None}
                if len(units)==1 and sum((num(r.get('entry_quantity')) or Decimal(0) for r in chosen),Decimal(0))>0:
                    dates_by_family.setdefault(key[0],set()).add(key[1])
    result = {}
    for row in rows:
        fid = int(row['family_id'])
        if fid in result:
            continue
        name = ' '.join(str(row.get('family_description') or '').upper().split())
        dates = sorted(d for d in dates_by_family.get(fid,set()) if 0 <= (today-d).days <= 84)
        weekdays = {d.weekday() for d in dates}
        if name in {'ATLANTIC SALMON STEAK','FRESH BIG MOUTH BASS'}:
            category = 'FRESH'
        elif str(row.get('product_class') or '').upper() == 'LIVE' or name.startswith('LIVE '):
            category = 'LIVE'
        elif weekdays and weekdays <= {1, 2}:
            category = 'FROZEN'
        elif weekdays and weekdays <= {4, 5}:
            category = 'FRESH'
        else:
            category = 'UNKNOWN'
        result[fid] = {'category': category}
    _category_cache = (time.monotonic(), result)
    return result

def build_page(category='ALL', prefix='ALL', q='', family='', cursor=0, limit=12, overrides=None):
    from db import db_conn
    from business_clock import business_today, completed_through_date
    from data_coverage import source_data_days
    from webapp_v2_runtime import _batch_daily_sales_by_price_type, _performance_range_cost_rows, _ordering_family_movement_metrics, _family_receipt_events_bulk
    today = business_today()
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute('SELECT * FROM quick_check_current ORDER BY family_id,ean_upc,upc_id')
            all_rows = [r for r in cur.fetchall() if r.get('family_id') is not None and r.get('upc_id') is not None]
            categories = {fid: dict(value) for fid, value in category_index(cur, all_rows, today).items()}
            for fid, cat in (overrides or {}).items():
                if int(fid) in categories:
                    categories[int(fid)]['category'] = cat
            groups = OrderedDict()
            for r in all_rows:
                groups.setdefault(group_key(r), []).append(r)
            selected = []
            for key, members in groups.items():
                cat = categories.get(int(members[0]['family_id']), {}).get('category', 'UNKNOWN')
                if category != 'ALL' and cat != category:
                    continue
                if prefix != 'ALL' and not any(str(r.get('ean_upc') or '').lstrip('0').startswith(tuple(prefix.split('+'))) for r in members):
                    continue
                if family and not any(family in {str(r.get('family_id')), str(r.get('main_article_number'))} for r in members):
                    continue
                if q and not any(q.lower() in ' '.join(str(r.get(k) or '') for k in ('ean_upc','selling_description','article_number','family_description','main_article_number')).lower() for r in members):
                    continue
                selected.append((key, members))
            selected.sort(key=lambda g: (-sum(float(r.get('pos_qty_7d') or 0) for r in g[1]), -int(any(r.get('quick_check_status') == 'READY' for r in g[1])), g[0]))
            total = len(selected)
            page = selected[cursor:cursor+limit]
            rows = [r for _, members in page for r in members]
            days = sorted(source_data_days(cur, 'sales_by_price_type', limit=90, up_to=completed_through_date()), key=lambda d:d['date'])
            through = days[-1]['date'] if days else None
            daily = _batch_daily_sales_by_price_type(cur, rows, days)
            costs = _performance_range_cost_rows(cur, rows, today)
            snapshots = price_snapshots(cur, rows)
            movement_days = sorted(source_data_days(cur, 'movement', limit=7, up_to=completed_through_date()), key=lambda d:d['date'])
            receipt_context = _family_receipt_events_bulk(cur, {int(r['family_id']) for r in rows}, data_day_limit=90)
            movements = {}
            for fid in {int(r['family_id']) for r in rows}:
                metrics = _ordering_family_movement_metrics(cur, fid, movement_days)
                movements[fid] = {**metrics, 'through': movement_days[-1]['date'] if movement_days else None}
            items = []
            for key, members in page:
                records = []
                for row in members:
                    uid, fid = int(row['upc_id']), int(row['family_id'])
                    observations = costs.get(fid, [])
                    cost = cost_for_day(row, observations, today)
                    history = snapshots.get(uid, [])
                    series = [day_evidence(row, d['date'], daily.get(uid, {}).get(d['date']), history, observations, cost) for d in days]
                    config = next((p for p in reversed(history) if p['date'] <= today), None)
                    latest_pos = next((d for d in reversed(series) if d['price'] is not None and d['qty'] is not None and d['qty'] > 0), None)
                    current = config if config and (not latest_pos or config['date'] >= latest_pos['date']) else ({'price': latest_pos['price'], 'type': latest_pos['type'], 'date': latest_pos['date'], 'source': 'CANONICAL_POS'} if latest_pos else None)
                    records.append({'upc': str(row['ean_upc']), 'name': row.get('selling_description'),
                        'article': str(row.get('article_number') or ''), 'uom': row.get('selling_uom'),
                        'status': row.get('quick_check_status'), 'blocking_reason': row.get('blocking_reason'),
                        'current': current, 'cost': cost, 'days': series})
                first = members[0]
                items.append({'id': key, 'familyId': str(first['family_id']),
                    'article': str(first.get('main_article_number') or ''),
                    'name': first.get('family_description') or first.get('selling_description'),
                    'category': categories[int(first['family_id'])]['category'], 'members': records,
                    'receipts': [{'date':r['posting_date'], 'quantity':r.get('base_receipt_quantity') if r.get('base_receipt_quantity') is not None else r.get('receipt_quantity'), 'uom':r.get('base_receipt_uom') or r.get('receipt_uom')} for r in receipt_context.get(int(first['family_id']),[])], 'movement': movements[int(first['family_id'])]})
            return {'contract': 'MOBILE_PRICING_V1', 'today': today, 'through': through,
                'checkedAt': datetime.now(timezone.utc).isoformat(), 'days': [d['date'] for d in days],
                'items': items, 'total': total, 'nextCursor': cursor+limit if cursor+limit < total else None,
                'scope': 'ALL_QUICK_CHECK_UPCS', 'costOrder': 'RECEIPT_REPORT_OH'}
        finally:
            cur.close()

_cache = OrderedDict()
_lock = threading.Lock()
_reads = ReadSingleFlight(max_running=2, wait_seconds=20)

@router.get('/v1/app/mobile-pricing')
def mobile_pricing(category: str='ALL', prefix: str='ALL', q: str='', family: str='', cursor: int=0, limit: int=12, overrides: str=''):
    category, prefix, q = category.upper(), prefix.upper(), q.strip()[:80]
    if category not in {'ALL','LIVE','FRESH','FROZEN','UNKNOWN'} or prefix not in {'ALL','240+249','245','247'} or cursor < 0 or (family and not family.isdigit()):
        raise HTTPException(422, 'Invalid pricing filter')
    try:
        custom = json.loads(overrides) if overrides else {}
        if not isinstance(custom, dict) or len(custom)>300 or any(not str(k).isdigit() or v not in {'LIVE','FRESH','FROZEN'} for k,v in custom.items()):
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(422, 'Invalid category corrections')
    limit = max(1, min(limit, 24))
    key = (category, prefix, q, family, cursor, limit, json.dumps(custom,sort_keys=True))
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < 120:
            return cached[1]
    def produce():
        with _lock:
            cached = _cache.get(key)
            if cached and time.monotonic() - cached[0] < 120:
                return cached[1]
        result = jsonable_encoder(build_page(category, prefix, q, family, cursor, limit, custom))
        with _lock:
            _cache[key] = (time.monotonic(), result)
            _cache.move_to_end(key)
            while len(_cache) > 64:
                _cache.popitem(last=False)
        return result
    try:
        return _reads.run(key, produce)
    except ReadBusy as exc:
        raise HTTPException(503, str(exc), headers={'Retry-After': '5'}) from exc
    except Exception as exc:
        import traceback
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        # Bounded code location only: never expose SQL, credentials or row data.
        raise HTTPException(500, 'Pricing evidence unavailable: %s in %s:%s' % (type(exc).__name__, frame.name, frame.lineno)) from exc
