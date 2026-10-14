"""Historical REG/SALE weekly usage estimates, never purchase orders."""
from datetime import date, timedelta
from decimal import Decimal


def promotion_dates(start, end, weekend_only):
    start, end = date.fromisoformat(str(start)), date.fromisoformat(str(end))
    if end < start or (end - start).days > 30:
        raise ValueError('Promotion period must be between 1 and 31 days.')
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return days, [day for day in days if not weekend_only or day.weekday() in {4, 5, 6}]


def type_average(daily, price_type, limit):
    """Exclude unknown-type days; retain explicit, supported zero-sale rows."""
    chosen = []
    for day, row in sorted(daily.items(), reverse=True):
        values = (row.get('price_types') or {}).get(price_type)
        if values is None:
            continue
        qty = Decimal(str(values.get('sold_quantity', 0)))
        sales = Decimal(str(values.get('sales_amount', 0)))
        if not qty.is_finite() or qty < 0 or not sales.is_finite() or sales < 0:
            continue
        if qty == 0 and sales != 0:
            continue
        chosen.append((day, qty, sales))
        if len(chosen) >= limit:
            break
    quantity = sum((row[1] for row in chosen), Decimal(0))
    sales = sum((row[2] for row in chosen), Decimal(0))
    return {'average': quantity / len(chosen) if chosen else None,
            'days': len(chosen), 'quantity': quantity,
            'average_price': sales / quantity if quantity > 0 else None,
            'start': min((row[0] for row in chosen), default=None),
            'end': max((row[0] for row in chosen), default=None)}


def estimate_member(daily, regular_days, sale_days):
    # REG: latest 28 observed REG days. SALE: latest 90 observed SALE days,
    # searched across up to 365 completed source days.
    reg, sale = type_average(daily, 'REG', 28), type_average(daily, 'SALE', 90)
    reg_rate, sale_rate = reg['average'], sale['average']
    fallback = sale_days > 0 and sale['days'] < 7 and reg_rate is not None
    used_sale_rate = 2 * reg_rate if fallback else sale_rate
    regular_usage = reg_rate * regular_days if regular_days and reg_rate is not None else Decimal(0) if not regular_days else None
    sale_usage = used_sale_rate * sale_days if sale_days and used_sale_rate is not None else Decimal(0) if not sale_days else None
    total = regular_usage + sale_usage if regular_usage is not None and sale_usage is not None else None
    used_counts = ([reg['days']] if regular_days or fallback else []) + ([sale['days']] if sale_days and not fallback else [])
    confidence = 'LOW' if fallback or total is None or not used_counts or min(used_counts) < 7 else 'MEDIUM'
    return {'reg': reg, 'sale': sale, 'regular_usage': regular_usage,
            'promotion_usage': sale_usage, 'total': total,
            'sale_fallback_to_reg': fallback, 'confidence': confidence}


def _unit(value):
    value = str(value or '').strip().upper()
    return {'LBS': 'LB', 'POUNDS': 'LB', 'PAC': 'PACK', 'PK': 'PACK',
            'PKG': 'PACK', 'EACH': 'EA', 'PCS': 'EA'}.get(value, value)


def weekly_usage(args):
    from webapp_v2_runtime import (db_conn, _canonical_sales_days,
                                   _daily_sales_by_price_type, _safe_qty_uom)
    items = args.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 30:
        raise ValueError('Provide between 1 and 30 items.')
    all_days, _ = promotion_dates(args.get('start_date'), args.get('end_date'), False)
    results, family_cache, daily_cache = [], {}, {}
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        supported = _canonical_sales_days(cur, limit=365)
        for item in items:
            query = str(item.get('article_or_upc') or '').strip()
            if not query.isdigit() or not 6 <= len(query) <= 14:
                raise ValueError('Use a confirmed article or UPC number for each item.')
            if query not in family_cache:
                cur.execute('''SELECT DISTINCT pf.family_id,pf.main_article_number,pf.family_description
                    FROM product_family pf
                    LEFT JOIN bridge_article_family baf ON baf.family_id=pf.family_id
                      AND baf.mapping_status='CONFIRMED'
                      AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                    LEFT JOIN article a ON a.article_id=baf.article_id
                    LEFT JOIN quick_check_current qc ON qc.family_id=pf.family_id
                    WHERE pf.main_article_number=%s OR a.article_number=%s
                      OR qc.ean_upc=%s
                      OR (qc.ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM qc.ean_upc)=%s)''',
                            (query, query, query, query.lstrip('0')))
                families = cur.fetchall()
                members = []
                if len(families) == 1:
                    cur.execute('SELECT * FROM quick_check_current WHERE family_id=%s ORDER BY ean_upc', (int(families[0]['family_id']),))
                    members = list({str(row['ean_upc']): row for row in cur.fetchall()}.values())
                family_cache[query] = (families, members)
            families, members = family_cache[query]
            _, promo_days = promotion_dates(args['start_date'], args['end_date'], bool(item.get('weekend_only')))
            result = {'article': query, 'name': str(item.get('name') or query),
                      'promotion_dates': [day.isoformat() for day in promo_days],
                      'regular_days': len(all_days) - len(promo_days), 'promotion_days': len(promo_days),
                      'requested_price': item.get('promotion_price'), 'unit': _unit(item.get('selling_unit')),
                      'members': [], 'status': 'AMBIGUOUS' if len(families) > 1 else 'NOT_FOUND'}
            if len(families) != 1:
                results.append(result)
                continue
            result['family_article'] = families[0]['main_article_number']
            # An exact UPC request includes its confirmed 240/249 companion;
            # an article request includes the family, separated by selling unit.
            if len(query.lstrip('0')) >= 11:
                exact = [row for row in members if str(row['ean_upc']).lstrip('0') == query.lstrip('0')]
                if exact:
                    key = query.lstrip('0')
                    members = [row for row in members if str(row['ean_upc']).lstrip('0') == key or
                               (key[:3] in {'240', '249'} and str(row['ean_upc']).lstrip('0')[:3] in {'240', '249'}
                                and str(row['ean_upc']).lstrip('0')[3:6] == key[3:6])]
            for row in members:
                unit = _unit(_safe_qty_uom(row.get('ean_upc'), row.get('selling_uom')))
                if not unit or unit != result['unit']:
                    continue
                upc_id = int(row['upc_id'])
                if upc_id not in daily_cache:
                    daily_cache[upc_id] = _daily_sales_by_price_type(cur, upc_id, supported)
                daily = daily_cache[upc_id]
                # Historical aliases with no REG/SALE evidence contribute no estimate.
                if not any(set((day.get('price_types') or {})) & {'REG', 'SALE'} for day in daily.values()):
                    continue
                estimate = estimate_member(daily, result['regular_days'], result['promotion_days'])
                result['members'].append({'upc': row['ean_upc'], 'name': row.get('selling_description'), 'unit': unit, **estimate})
            included = result['members']
            result['status'] = 'ESTIMATED' if included and all(row['total'] is not None for row in included) else 'INSUFFICIENT_HISTORY_OR_UNIT'
            result['total'] = sum((row['total'] for row in included), Decimal(0)) if result['status'] == 'ESTIMATED' else None
            result['regular_usage'] = sum((row['regular_usage'] for row in included), Decimal(0)) if included and all(row['regular_usage'] is not None for row in included) else None
            result['promotion_usage'] = sum((row['promotion_usage'] for row in included), Decimal(0)) if included and all(row['promotion_usage'] is not None for row in included) else None
            result['reg_rate'] = sum((row['reg']['average'] for row in included), Decimal(0)) if included and all(row['reg']['average'] is not None for row in included) else None
            result['sale_rate'] = sum((row['sale']['average'] for row in included), Decimal(0)) if included and all(row['sale']['average'] is not None for row in included) else None
            result['fallback'] = any(row['sale_fallback_to_reg'] for row in included)
            result['applied_promo_rate'] = sum((2 * row['reg']['average'] if row['sale_fallback_to_reg'] else row['sale']['average'] for row in included), Decimal(0)) if included and all(row['sale_fallback_to_reg'] or row['sale']['average'] is not None for row in included) else None
            result['confidence'] = 'LOW' if not included or result['status'] != 'ESTIMATED' or any(row['confidence'] == 'LOW' for row in included) else 'MEDIUM'
            results.append(result)
        cur.close()
    return {'start_date': args['start_date'], 'end_date': args['end_date'],
            'basis': 'HISTORICAL_REG_SALE_TYPE_OBSERVED_COMPLETED_DAYS',
            'supported_through': max((day['date'] for day in supported), default=None),
            'items': results, 'calculation_answer': format_usage(results, args['start_date'], args['end_date'])}


def format_usage(items, start, end):
    def num(value):
        return '—' if value is None else f'{value:.1f}'.rstrip('0').rstrip('.')
    lines = [f'Estimated usage for {start} to {end} (historical REG/SALE averages):', '',
             '| Item | Promo dates | REG usage | SALE usage | Weekly usage | Confidence |',
             '| --- | ---: | ---: | ---: | ---: | --- |']
    for row in items:
        name = row['name'].replace('|', '/').replace('\n', ' ')
        unit = row['unit'].lower()
        total = f"{num(row.get('total'))} {unit}" if row.get('total') is not None else 'Unavailable'
        sale = num(row.get('promotion_usage')) + (' (2× REG fallback)' if row.get('fallback') else '')
        dates = ', '.join(date.fromisoformat(day).strftime('%b %d') for day in row['promotion_dates']) or 'None'
        lines.append(f"| {name} | {dates} ({row['promotion_days']} days) | {num(row.get('regular_usage'))} {unit} | {sale} {unit} | {total} | {row.get('confidence', 'LOW').title()} |")
    lines += ['', 'Weekly usage = REG average × regular days + promotion rate × promotion days. With at least 7 supported SALE days, use the SALE average. Otherwise use 2× REG when REG history exists (low confidence). Weekend items use only Fri/Sat/Sun within the listed dates. These are estimates, not guaranteed demand; historical SALE prices can differ from the proposed price. Units stay separate; matching 249 sales are included in the family.']
    for row in items:
        for kind in ('reg', 'sale'):
            evidence = [member[kind] for member in row.get('members', []) if member[kind]['days']]
            if evidence:
                days = sorted({str(value) for e in evidence for value in (e['start'], e['end']) if value})
                counts = '/'.join(str(e['days']) for e in evidence)
                rate = row.get('reg_rate' if kind == 'reg' else 'sale_rate')
                lines.append(f"{row['name']} {kind.upper()}: {num(rate)} {row['unit'].lower()}/day; {days[0]}–{days[-1]}; {counts} observed type days per included UPC.")
    return '\n'.join(lines)
