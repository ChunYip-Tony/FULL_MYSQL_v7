"""Read-only, canonical POS evidence shared by mobile pricing and Quick Check.

Never writes prices, counts or synthetic sales. Unknown exposure/cost stays null.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from collections import OrderedDict
import threading
import time
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

def build_page(category='ALL', prefix='ALL', q='', family='', cursor=0, limit=12):
    from db import db_conn
    from business_clock import business_today, completed_through_date
    from data_coverage import source_data_days
    from webapp_v2_runtime import _batch_daily_sales_by_price_type, _performance_range_cost_rows
    today = business_today()
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute('SELECT * FROM quick_check_current ORDER BY family_id,ean_upc,upc_id')
            all_rows = cur.fetchall()
            groups = OrderedDict()
            for r in all_rows:
                groups.setdefault(group_key(r), []).append(r)
            selected = []
            for key, members in groups.items():
                cat = str(members[0].get('product_class') or 'UNKNOWN').upper()
                if category != 'ALL' and cat != category:
                    continue
                if prefix != 'ALL' and not any(str(r.get('ean_upc') or '').lstrip('0').startswith(tuple(prefix.split('+'))) for r in members):
                    continue
                if family and not any(family in {str(r.get('family_id')), str(r.get('main_article_number'))} for r in members):
                    continue
                if q and not any(q.lower() in ' '.join(str(r.get(k) or '') for k in ('ean_upc','selling_description','article_number','family_description','main_article_number')).lower() for r in members):
                    continue
                selected.append((key, members))
            total = len(selected)
            page = selected[cursor:cursor+limit]
            rows = [r for _, members in page for r in members]
            days = sorted(source_data_days(cur, 'sales_by_price_type', limit=28, up_to=completed_through_date()), key=lambda d:d['date'])
            through = days[-1]['date'] if days else None
            daily = _batch_daily_sales_by_price_type(cur, rows, days)
            costs = _performance_range_cost_rows(cur, rows, today)
            snapshots = price_snapshots(cur, rows)
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
                    'category': str(first.get('product_class') or 'UNKNOWN').upper(), 'members': records})
            return {'contract': 'MOBILE_PRICING_V1', 'today': today, 'through': through,
                'checkedAt': datetime.now(timezone.utc).isoformat(), 'days': [d['date'] for d in days],
                'items': items, 'total': total, 'nextCursor': cursor+limit if cursor+limit < total else None,
                'scope': 'ALL_QUICK_CHECK_UPCS', 'costOrder': 'RECEIPT_REPORT_OH'}
        finally:
            cur.close()

_cache = OrderedDict()
_lock = threading.Lock()

@router.get('/v1/app/mobile-pricing')
def mobile_pricing(category: str='ALL', prefix: str='ALL', q: str='', family: str='', cursor: int=0, limit: int=12):
    category, prefix, q = category.upper(), prefix.upper(), q.strip()[:80]
    if category not in {'ALL','LIVE','FRESH','FROZEN','UNKNOWN'} or prefix not in {'ALL','240+249','245','247'} or cursor < 0 or (family and not family.isdigit()):
        raise HTTPException(422, 'Invalid pricing filter')
    limit = max(1, min(limit, 24))
    key = (category, prefix, q, family, cursor, limit)
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < 120:
            return cached[1]
    result = jsonable_encoder(build_page(category, prefix, q, family, cursor, limit))
    with _lock:
        _cache[key] = (time.monotonic(), result)
        _cache.move_to_end(key)
        while len(_cache) > 64:
            _cache.popitem(last=False)
    return result
