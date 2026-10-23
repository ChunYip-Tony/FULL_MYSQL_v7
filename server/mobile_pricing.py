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
    {'SELLING_MVT_251_252'},
    {'FROZEN_INVENTORY_OFFICIAL_COST', 'LIVE_FRESH_SUGGESTION_OFFICIAL_COST'},
    {'ON_HAND_EXPLICIT_COST_FALLBACK'},
)

def num(value):
    try:
        n = Decimal(str(value))
        return n if n.is_finite() else None
    except Exception:
        return None

def selling_unit(row):
    explicit = str(row.get('selling_uom') or '').strip().upper()
    if explicit:
        return 'PACK' if explicit == 'PAC' else explicit
    digits = str(row.get('ean_upc') or '').lstrip('0')
    if len(digits) == 11 and digits[:3].isdigit():
        prefix = int(digits[:3])
        if 230 <= prefix <= 239 or 250 <= prefix <= 269 or prefix in (240,242,245,247,249):
            return 'LB'
    return ''

def effective_cost_as_of(observations, day):
    # A base-unit cost remains visible even when selling-unit conversion is held.
    for sources in COST_ORDER:
        candidates = sorted((o for o in observations if o.get('source_type') in sources
            and o.get('business_date') and o['business_date'] <= day),
            key=lambda o:(o['business_date'],o.get('cost_observation_id') or 0), reverse=True)
        for obs in candidates:
            value, unit = num(obs.get('cost_value')), str(obs.get('cost_uom') or '').strip().upper()
            if value is not None and value > 0 and unit:
                return {'value':value,'uom':unit,'date':obs['business_date'],'source':obs['source_type']}
    return None

def cost_for_day(row, observations, day):
    from supplementary_movement_cost import eligible
    observations = [o for o in observations if eligible(row,o)]
    selling = selling_unit(row)
    base = str(row.get('base_uom') or '').strip().upper()
    base = 'PACK' if base == 'PAC' else base
    factor = num(row.get('base_qty_per_selling_unit'))
    for sources in COST_ORDER:
        candidates = sorted((o for o in observations if o.get('source_type') in sources
            and o.get('business_date') and o['business_date'] <= day),
            key=lambda o: (o['business_date'], o.get('cost_observation_id') or 0), reverse=True)
        for obs in candidates:
            value, unit = num(obs.get('cost_value')), str(obs.get('cost_uom') or '').upper()
            unit = 'PACK' if unit == 'PAC' else unit
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
    # A repeated identical ticket is not an intraday price change. Completed
    # canonical POS coverage establishes zero sales even if today's routine
    # price-list upload repeats the ticket already in effect before the day.
    on_day = [p for p in snapshots if p['date'] == day]
    stable_exposure = bool(configured) and all(
        p['type'] == configured['type'] and num(p['price']) == num(configured['price'])
        for p in on_day)

    cost = cost_for_day(row, costs, day)
    result = {'date': day, 'qty': None, 'sales': None, 'price': None, 'type': None,
        'gp': None, 'normalized_gp': None, 'valid': False, 'reason': None,
        'cost': cost, 'zero_sale': False}
    types = observation.get('price_types') or {} if observation else {}
    # Retain actual per-type POS for reference even when a day has mixed prices.
    result['typeSales'] = []
    for pt, values in types.items():
        q, s = num(values.get('sold_quantity')), num(values.get('sales_amount'))
        if (pt in PRIORITY or pt == 'TOTAL') and q is not None and s is not None and q > 0 and s > 0:
            result['typeSales'].append({'type':pt,'qty':q,'sales':s,'gp':s-q*cost['value'] if cost else None})
    if observation:
        qty, sales = num(observation.get('sold_quantity')), num(observation.get('sales_amount'))
        result.update(qty=qty, sales=sales, posReportedQty=qty, posReportedSales=sales)
        if 'TOTAL' in types:
            # The Single Total POS has actual Qty/Weight but no price-type split.
            # Keep the sales/GP reference without inventing REG/TPR exposure.
            result.update(type='TOTAL', quantityBasis='POS_QTY_WEIGHT',
                quantityEstimated=False, price=sales / qty if qty and sales is not None else None,
                gp=sales-qty*cost['value'] if qty is not None and sales is not None and cost else None,
                normalized_gp=sales-qty*current_cost['value'] if qty is not None and sales is not None and current_cost else None)
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
        elif stable_exposure:
            result.update(price=configured['price'], type=configured['type'], zero_sale=True)
        else:
            result['reason'] = 'PRICE_EXPOSURE_UNVERIFIED'
            return result
    elif stable_exposure:
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


# Item categories confirmed by Tony after the 2026-10-15 receiving review.
# Includes family and observed receiving aliases; never infer from a name.
CONFIRMED_CATEGORIES = {
    '1363489':'FROZEN', '3400489':'FROZEN',
    '1351010':'FROZEN', '3467050':'FROZEN',
    '1341262':'FROZEN', '1341274':'FROZEN',
    '1343317':'FROZEN', '3461000':'FROZEN',
    '3400200':'FROZEN', '3401200':'FROZEN',
    '1341020':'FROZEN', '1341138':'FROZEN', '1342207':'FROZEN',
    '1361760':'FRESH', '3500527':'FRESH', '3540032':'FRESH',
    # Active item classifications confirmed on 2026-10-15.
    '1341080':'FRESH',
    '1341069':'FROZEN',
    '3408098':'FROZEN',
    '1341046':'FROZEN',
    '3400137':'FROZEN',
    '1361684':'FRESH',
    '1341613':'FROZEN',
    '3480144':'FROZEN',
    '1354810':'FROZEN',
    '3401403':'FROZEN',
    '3480715':'FROZEN',
    '3480169':'FROZEN',
    '1354803':'FROZEN',
    '1363589':'FRESH',
    '1347125':'FROZEN',
    '3480684':'FROZEN',
    '3480721':'FROZEN',
    '3480564':'FROZEN',
    '3400186':'FROZEN',
    '3400166':'FROZEN',
    '3480567':'FROZEN',
    '3400070':'FROZEN',
    '2001682':'FROZEN',
    '3400136':'FROZEN',
    '3400043':'FROZEN',
    '3480660':'FROZEN',
    '2348072':'FROZEN',
    '3400129':'FROZEN',
    '3480745':'FROZEN',
    '3480452':'FROZEN',
    '3480742':'FROZEN',
    '3480061':'FROZEN',
    '3480652':'FROZEN',
    '3480762':'FROZEN',
    '1345958':'FROZEN',
    '3440076':'FROZEN',
    '1347012':'FROZEN',
    '3480504':'FROZEN',
    '3480665':'FROZEN',
    '3480602':'FROZEN',
    '3480685':'FROZEN',
    '3468360':'FROZEN',
    '1347017':'FROZEN',
    '1341555':'FROZEN',
    '3467100':'FROZEN',
    '1341655':'FROZEN',
    '3400922':'FROZEN',
    '1345959':'FROZEN',
    '1365555':'FRESH',
    '3400135':'FROZEN',
    '3467160':'FROZEN',
    '3440077':'FROZEN',
    '3480644':'FROZEN',
    '3480439':'FROZEN',
    '3480655':'FROZEN',
    '1341648':'FROZEN',
    '3401856':'FROZEN',
    '3480773':'FROZEN',
    '1340302':'FROZEN',
    '3467130':'FROZEN',
    '1348072':'FROZEN',
    '1341139':'FROZEN',
    '1341715':'FROZEN',
    '3400184':'FROZEN',
    '1345962':'FROZEN',
    '3400955':'FROZEN',
    '3400234':'FROZEN',
    '3480420':'FROZEN',
    '3480319':'FROZEN',
    '3461890':'FROZEN',
    '3480686':'FROZEN',
    '3480713':'FROZEN',
    '3480691':'FROZEN',
    '3405986':'FROZEN',
    '3404004':'FROZEN',
    '1342316':'FROZEN',
    '3400932':'FROZEN',
    '1345965':'FROZEN',
    '3400797':'FROZEN',
    '1345957':'FROZEN',
    '1345969':'FROZEN',
    '1341651':'FROZEN',
    '3469020':'FROZEN',
    '3461300':'FROZEN',
    '1345989':'FROZEN',
}
def confirmed_category(*articles):
    for article in articles:
        category = CONFIRMED_CATEGORIES.get(str(article or '').strip())
        if category:
            return category
    return None

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
        confirmed = confirmed_category(row.get('main_article_number'), row.get('article_number'))
        if confirmed:
            category = confirmed
        elif name in {'ATLANTIC SALMON STEAK','FRESH BIG MOUTH BASS'}:
            category = 'FRESH'
        elif str(row.get('product_class') or '').upper() == 'LIVE' or name.startswith('LIVE '):
            category = 'LIVE'
        elif 1 in weekdays and 4 not in weekdays:
            category = 'FROZEN'
        elif 4 in weekdays and 1 not in weekdays:
            category = 'FRESH'
        else:
            category = 'UNKNOWN'
        result[fid] = {'category': category}
    _category_cache = (time.monotonic(), result)
    return result

def build_page(category='ALL', prefix='ALL', q='', family='', cursor=0, limit=12, overrides=None, history_days=90, requested_upcs=None, history_only=False):
    from db import db_conn
    from business_clock import business_today, completed_through_date
    from data_coverage import source_data_days
    from webapp_v2_runtime import _batch_daily_sales_by_price_type, _performance_range_cost_rows, _ordering_family_movement_metrics, _family_receipt_events_bulk
    today = business_today()
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            if requested_upcs is None:
                cur.execute('SELECT * FROM quick_check_current ORDER BY family_id,ean_upc,upc_id')
            else:
                requested = sorted({str(upc) for upc in requested_upcs})
                placeholders = ','.join(['%s'] * len(requested))
                cur.execute('SELECT * FROM quick_check_current WHERE ' +
                            ('ean_upc IN (' + placeholders + ')' if requested else '1=0') +
                            ' ORDER BY family_id,ean_upc,upc_id', tuple(requested))
            from family_daily_gp import apply_confirmed_selling_profile
            all_rows = [apply_confirmed_selling_profile(r) for r in cur.fetchall() if r.get('family_id') is not None and r.get('upc_id') is not None and (requested_upcs is None or str(r.get('ean_upc')) in requested_upcs)]
            categories = ({int(r['family_id']):{'category':'UNKNOWN'} for r in all_rows} if history_only else {fid: dict(value) for fid, value in category_index(cur, all_rows, today).items()})
            for fid, cat in (overrides or {}).items():
                if int(fid) in categories:
                    categories[int(fid)]['category'] = cat
            from article_search_aliases import article_alias_families
            alias_families = article_alias_families(cur,q) if q.strip().isdigit() else {}
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
                if q and int(members[0]['family_id']) not in alias_families and not any(q.lower() in ' '.join(str(r.get(k) or '') for k in ('ean_upc','selling_description','article_number','family_description','main_article_number')).lower() for r in members):
                    continue
                selected.append((key, members))
            from article_search_aliases import search_alias_priority
            selected.sort(key=lambda g: (min(search_alias_priority(q,r.get('selling_description')) for r in g[1]), -sum(float(r.get('pos_qty_7d') or 0) for r in g[1]), -int(any(r.get('quick_check_status') == 'READY' for r in g[1])), g[0]))
            total = len(selected)
            page = selected[cursor:cursor+limit]
            rows = [r for _, members in page for r in members]
            days = sorted(source_data_days(cur, 'sales_by_price_type', limit=history_days, up_to=completed_through_date()), key=lambda d:d['date'])
            through = days[-1]['date'] if days else None
            daily = _batch_daily_sales_by_price_type(cur, rows, days)
            costs = _performance_range_cost_rows(cur, rows, today)
            snapshots = price_snapshots(cur, rows)
            movement_days = sorted(source_data_days(cur, 'movement', limit=7, up_to=completed_through_date()), key=lambda d:d['date'])
            receipt_context = {} if history_only else _family_receipt_events_bulk(cur, {int(r['family_id']) for r in rows}, data_day_limit=90)
            movements = {}
            for fid in {int(r['family_id']) for r in rows}:
                metrics = {} if history_only else _ordering_family_movement_metrics(cur, fid, movement_days)
                movements[fid] = {**metrics, 'through': movement_days[-1]['date'] if movement_days else None}
            items = []
            for key, members in page:
                records = []
                for row in members:
                    uid, fid = int(row['upc_id']), int(row['family_id'])
                    from supplementary_movement_cost import eligible
                    observations = [o for o in costs.get(fid, []) if eligible(row,o)]
                    cost = cost_for_day(row, observations, today)
                    history = snapshots.get(uid, [])
                    series = [day_evidence(row, d['date'], daily.get(uid, {}).get(d['date']), history, observations, cost) for d in days]
                    config = next((p for p in reversed(history) if p['date'] <= today), None)
                    latest_pos = next((d for d in reversed(series) if d['price'] is not None and d['qty'] is not None and d['qty'] > 0), None)
                    current = config if config and (not latest_pos or config['date'] >= latest_pos['date']) else ({'price': latest_pos['price'], 'type': latest_pos['type'], 'date': latest_pos['date'], 'source': 'CANONICAL_POS'} if latest_pos else None)
                    records.append({'upc': str(row['ean_upc']), 'name': row.get('selling_description'),
                        'article': str(row.get('article_number') or ''), 'uom': selling_unit(row) or None,
                        'quantityBasis': 'POS_ITEM_COUNT' if selling_unit(row) == 'LB' else 'POS_SELLING_UNIT',
                        'status': row.get('quick_check_status'), 'blocking_reason': row.get('blocking_reason'),
                        'canonicalUpc':row.get('canonical_upc',str(row['ean_upc'])),'upcAliases':row.get('upc_aliases',[]),
                        'current': current, 'priceHistory': history, 'cost': cost,
                        'effectiveCost': cost or effective_cost_as_of(observations,today), 'days': series})
                first = members[0]
                items.append({'id': key, 'familyId': str(first['family_id']),
                    'article': str(first.get('main_article_number') or ''),
                    'name': first.get('family_description') or first.get('selling_description'),
                    'category': categories[int(first['family_id'])]['category'], 'members': records,
                    'receipts': [{'date':r['posting_date'], 'quantity':r.get('base_receipt_quantity') if r.get('base_receipt_quantity') is not None else r.get('receipt_quantity'), 'uom':r.get('base_receipt_uom') or r.get('receipt_uom')} for r in receipt_context.get(int(first['family_id']),[])], 'movement': movements[int(first['family_id'])]})
            return {'contract': 'MOBILE_PRICING_V1', 'today': today, 'through': through,
                'checkedAt': datetime.now(timezone.utc).isoformat(), 'days': [d['date'] for d in days],
                'items': guard_weight_counts(items), 'total': total, 'nextCursor': cursor+limit if cursor+limit < total else None,
                'scope': 'ALL_QUICK_CHECK_UPCS', 'costOrder': 'FAMILY_RECEIPT_251_OH_V1'}
        finally:
            cur.close()


def guard_weight_counts(items):
    """Keep item counts out of LB metrics; provide labeled ticket-based estimates.

    Actual UPC weight is unavailable in this POS format. Family MVT is never
    allocated to UPCs. Changed/missing/mixed tickets cannot estimate weight.
    """
    for item in items:
        for member in item['members']:
            if member.get('quantityBasis') != 'POS_ITEM_COUNT':
                continue
            member['quantityStatus'] = 'POS_WEIGHT_ESTIMATED'
            history = sorted(member.get('priceHistory', []), key=lambda p:(p['date'],p.get('file_id',0)))
            for day in member['days']:
                from family_daily_gp import confirmed_pos_lb
                confirmed=confirmed_pos_lb({'ean_upc':member.get('upc'),'selling_uom':member.get('uom'),'latest_daily_pos_reported_qty':day.get('qty')},day.get('date'))
                if confirmed is not None and day.get('sales') is not None:
                    cost=day.get('cost');current_cost=member.get('cost')
                    day.update(qty=confirmed,quantityBasis='POS_QTY_WEIGHT',quantityEstimated=False,
                        quantityConfirmation='TONY_CONFIRMED_POS_LB_2026_10_19',quantityReconciliation='COMPARE_AT_FAMILY_LEVEL_NO_UPC_ALLOCATION',
                        gp=num(day['sales'])-confirmed*num(cost['value']) if cost else None,
                        normalized_gp=num(day['sales'])-confirmed*num(current_cost['value']) if current_cost else None,
                        valid=bool(cost and day.get('type') in PRIORITY and day.get('reason') in (None,'COST_OR_UNIT_UNVERIFIED') and not (confirmed==0 and num(day.get('sales'))!=0)),reason=day.get('reason') if day.get('reason') not in (None,'COST_OR_UNIT_UNVERIFIED') else (None if cost else 'COST_OR_UNIT_UNVERIFIED'))
                    for value in day.get('typeSales',[]):
                        value['gp']=num(value['sales'])-num(value['qty'])*num(cost['value']) if cost and num(value.get('qty')) is not None else None
                    continue
                if day.get('quantityBasis') == 'POS_QTY_WEIGHT':
                    continue
                day['posItemCount'] = day['qty']
                prior = next((p for p in reversed(history) if p['date'] < day['date']), None)
                on_day = [p for p in history if p['date'] == day['date']]
                stable = prior and all(p['type'] == prior['type'] and p['price'] == prior['price'] for p in on_day)
                def estimate(row, pt):
                    sales = num(row.get('sales'))
                    if not stable or prior['type'] != pt or sales is None or sales < 0 or num(prior['price']) is None or num(prior['price']) <= 0:
                        return None
                    return sales / num(prior['price'])
                for row in day.get('typeSales', []):
                    row['posItemCount'] = row['qty']
                    row['qty'] = estimate(row, row['type'])
                    cost = day.get('cost')
                    row['gp'] = row['sales'] - row['qty'] * cost['value'] if row['qty'] is not None and cost else None
                qty = estimate(day, day.get('type'))
                if len(day.get('typeSales', [])) > 1:
                    qty = None
                cost = day.get('cost')
                day.update(qty=qty, price=num(prior['price']) if qty is not None else None,
                    gp=day['sales']-qty*cost['value'] if qty is not None and cost else None,
                    normalized_gp=day['sales']-qty*member['cost']['value'] if qty is not None and member.get('cost') else None,
                    valid=False, reason='POS_WEIGHT_ESTIMATED' if qty is not None else 'POS_WEIGHT_MISSING',
                    quantityBasis='POS_SALES_DIVIDED_BY_STABLE_HISTORICAL_TICKET', quantityEstimated=True)
            from family_daily_gp import CONFIRMED_POS_LB_UPCS
            confirmed_member=str(member.get('upc')) in CONFIRMED_POS_LB_UPCS or str(member.get('upc')) in {'24053300000','24953300000'}
            if confirmed_member:
                member['quantityStatus']='USER_CONFIRMED_POS_LB'
                member['quantityBasis']='POS_QTY_WEIGHT'
            if not confirmed_member and member.get('current') and member['current'].get('source') == 'CANONICAL_POS':
                member['current'] = next(iter(reversed(history)), None)
    return items

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






@router.get('/v1/app/mobile-pricing/history-batch')
def pricing_history_batch(upcs: str):
    requested=set(upcs.split(','))
    if not requested or len(requested)>24 or any(not x.isdigit() or len(x)>18 for x in requested):
        raise HTTPException(422,'Supply 1-24 exact numeric UPCs')
    result=build_page(limit=24,history_days=90,requested_upcs=requested)
    result['requestedUpcs']=sorted(requested)
    result['purpose']='RETAINED_HISTORY_REPAIR_POS_ONLY'
    result['historyRepairVersion']=4
    from family_daily_gp import POS_QUANTITY_POLICY_REVISION
    result['quantityPolicyRevision']=POS_QUANTITY_POLICY_REVISION
    return jsonable_encoder(result)

@router.get('/v1/app/mobile-pricing/article-movement')
def pricing_article_movement(upcs: str, business_date: str):
    """Canonical exact-article evidence; never allocates article/family totals to UPC."""
    requested=sorted(set(upcs.split(',')))
    if not requested or len(requested)>24 or any(not u.isdigit() or len(u)>18 for u in requested):
        raise HTTPException(422,'Supply 1-24 exact numeric UPCs')
    try:
        date.fromisoformat(business_date)
    except ValueError:
        raise HTTPException(422,'Supply YYYY-MM-DD')
    from db import db_conn
    from data_coverage import source_data_days
    from business_clock import completed_through_date
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            days=source_data_days(cur,'movement',limit=365,up_to=completed_through_date())
            canonical=next((d for d in days if str(d['date'])[:10]==business_date),None)
            if not canonical:
                raise HTTPException(404,'No canonical completed movement file for date')
            ph=','.join(['%s']*len(requested))
            cur.execute('SELECT ean_upc,article_id,article_number,main_article_number,family_id,selling_description,selling_uom FROM quick_check_current WHERE ean_upc IN ('+ph+')',tuple(requested))
            members=cur.fetchall();families=sorted({int(r['family_id']) for r in members if r.get('family_id') is not None})
            if not families:
                return {'businessDate':business_date,'canonical':canonical,'members':[],'movementRows':[]}
            fp=','.join(['%s']*len(families))
            cur.execute('SELECT ean_upc,article_id,article_number,family_id,selling_description FROM quick_check_current WHERE family_id IN ('+fp+')',tuple(families))
            siblings=cur.fetchall()
            cur.execute("SELECT file_id,raw_id,source_row_number,article_number,article_id,family_id,description,movement_type,posting_date,entry_quantity,entry_uom_code,base_quantity,base_uom_code,amount_local_currency,sales_value FROM movement_history WHERE file_id=%s AND posting_date=%s AND family_id IN ("+fp+") AND movement_type IN ('251','252') ORDER BY article_number,raw_id LIMIT 2000",(canonical['file_id'],business_date,*families))
            movements=cur.fetchall()
            return jsonable_encoder({'businessDate':business_date,'canonical':canonical,'members':members,'familyMembers':siblings,'movementRows':movements,'quantityPolicy':'POS_ONLY; movement retained as independent exact-article reconciliation evidence; shared articles must not be allocated to UPC'})
        finally:
            cur.close()


