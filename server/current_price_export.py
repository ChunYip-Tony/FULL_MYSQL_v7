"""Current-price selection for Google exports; historical POS remains separate."""
from datetime import date
from decimal import Decimal, InvalidOperation

PRIORITY = {'REG': 1, 'TPR': 2, 'SALE': 3, 'IN STORE': 4, 'IN_STORE': 4}
PRICE_COLUMNS = ['current_price_source', 'current_price_asof_date',
                 'current_price_file_id', 'current_price_filename', 'current_price_basis']


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def apply_current_prices(rows, snapshots, pos_rows, completed_through):
    """Newest accepted UPC list vs latest completed canonical POS sold day.

    snapshots is the bulk, accepted-file output of mobile_pricing.price_snapshots;
    pos_rows is canonical typed POS from analysis_pos.build_pos_export. Do not
    manufacture sales, UPC quantity, or price-performance evidence from lists.
    """
    cutoff = day(completed_through)
    totals = {}
    for obs in pos_rows:
        when = day(obs.get('date'))
        if (not when or not cutoff or when > cutoff
                or obs.get('coverage_kind') == 'DERIVED_PERIOD_RESIDUAL'
                or obs.get('mapping_status') != 'RESOLVED'
                or obs.get('department') != 'Seafood'):
            continue
        key = (str(obs.get('upc')), when)
        total = totals.setdefault(key, {'sales': Decimal(0), 'qty': Decimal(0),
                                      'types': set(), 'valid': True, 'files': set(), 'names': set()})
        sales, qty = number(obs.get('sales_amount')), number(obs.get('verified_quantity'))
        if sales is None or qty is None or sales < 0 or qty < 0 or (sales != 0 and qty == 0):
            total['valid'] = False
            continue
        total['sales'] += sales
        total['qty'] += qty
        if sales > 0 and qty > 0:
            total['types'].add(str(obs.get('price_type') or 'UNKNOWN').upper())
        if obs.get('source_file_id') is not None:
            total['files'].add(str(obs['source_file_id']))
        if obs.get('source_filename'):
            total['names'].add(obs['source_filename'])
    sold = {}
    for (upc, when), obs in totals.items():
        if not obs['valid'] or obs['sales'] <= 0 or obs['qty'] <= 0:
            continue
        if upc in sold and sold[upc]['date'] >= when:
            continue
        types = obs['types']
        sold[upc] = {'price': obs['sales'] / obs['qty'], 'date': when,
                     'type': next(iter(types)) if len(types) == 1 else 'MIXED',
                     'source': 'CANONICAL_POS_REALIZED_AVERAGE',
                     'file_id': ','.join(sorted(obs['files'])),
                     'filename': ', '.join(sorted(obs['names'])),
                     'basis': 'POS_SALES_DIVIDED_BY_VERIFIED_POS_QUANTITY'}
    for row in rows:
        choices = []
        for value in snapshots.get(row.get('upc_id'), []):
            when, price = day(value.get('date')), number(value.get('price'))
            kind = str(value.get('type') or '').upper()
            if when and price is not None and price > 0 and kind in PRIORITY:
                choices.append({**value, 'date': when, 'price': price, 'type': kind,
                                'source': 'PRICE_LIST', 'basis': 'UPLOADED_PRICE_LIST'})
        ticket = max(choices, key=lambda v: (v['date'], int(v.get('file_id') or 0),
                                             PRIORITY[v['type']]), default=None)
        pos = sold.get(str(row.get('ean_upc')))
        # A list uploaded on the same business day takes precedence.
        chosen = ticket if ticket and (not pos or ticket['date'] >= pos['date']) else pos
        for key in ['current_price', 'current_price_type', *PRICE_COLUMNS, 'gp_pct_current']:
            row[key] = None
        if chosen is None:
            row['current_price_source'] = 'CURRENT_PRICE_UNVERIFIED'
            continue
        for dest, source in [('current_price', 'price'), ('current_price_type', 'type'),
                             ('current_price_source', 'source'), ('current_price_asof_date', 'date'),
                             ('current_price_file_id', 'file_id'), ('current_price_filename', 'filename'),
                             ('current_price_basis', 'basis')]:
            row[dest] = chosen.get(source)
        cost = number(row.get('current_cost_per_selling_unit'))
        if cost is not None and cost > 0:
            row['gp_pct_current'] = (chosen['price'] - cost) / chosen['price']
