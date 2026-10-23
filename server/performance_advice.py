"""Deterministic comparisons for FisherMan. No forecasts or price causality inferred."""
from datetime import date
from decimal import Decimal


def compare_performance(args, sales_reader):
    n = max(1, min(90, int(args.get('supported_days') or 7)))
    bounds = [args.get(k) for k in ('current_start', 'current_end', 'prior_start', 'prior_end')]
    query = args.get('item_query')
    if any(bounds) and not all(bounds):
        raise ValueError('Provide both complete comparison periods, or leave all dates empty.')
    if all(bounds):
        current_start, current_end, prior_start, prior_end = [date.fromisoformat(v).isoformat() for v in bounds]
        if prior_start > prior_end or current_start > current_end or prior_end >= current_start:
            raise ValueError('Comparison periods must be ordered and non-overlapping.')
    else:
        scope = sales_reader({'item_query': query, 'supported_days': 2*n})
        if scope.get('needs_details') or scope.get('data_available') is False:
            return scope
        days = sorted({str(d)[:10] for d in scope.get('supported_dates') or []})
        if len(days) < 2*n:
            return {'data_available': False, 'reason': 'INSUFFICIENT_COMPARABLE_SUPPORTED_DAYS',
                    'available_days': len(days), 'required_days': 2*n,
                    'advice': 'Describe available observations; do not claim a trend or fill missing dates with zero.'}
        prior_start, prior_end, current_start, current_end = days[-2*n], days[-n-1], days[-n], days[-1]
    periods = []
    for start, end in ((prior_start, prior_end), (current_start, current_end)):
        value = sales_reader({'item_query': query, 'start_date': start, 'end_date': end, '_comparison': True})
        if value.get('needs_details') or value.get('data_available') is False:
            return value
        if not value.get('supported_day_count'):
            return {'data_available': False, 'reason': 'NO_SUPPORTED_DAYS', 'start': start, 'end': end}
        periods.append(value)
    prior, current = periods
    def decimal(v):
        return Decimal(str(v)) if v is not None else None
    def per_day(period, key):
        value = decimal(period.get(key))
        return value / Decimal(str(period['supported_day_count'])) if value is not None else None
    def change(before, after):
        return {'prior': before, 'current': after, 'change': after-before if before is not None and after is not None else None,
                'change_pct': (after-before)/abs(before)*100 if before and after is not None else None}
    metrics = {key: change(per_day(prior, key), per_day(current, key)) for key in ('sales_dollars', 'gp_dollars')}
    units = set(prior.get('sold_quantity_by_uom', {})) | set(current.get('sold_quantity_by_uom', {}))
    quantity = {u: change(decimal(prior.get('sold_quantity_by_uom', {}).get(u))/Decimal(str(prior['supported_day_count']))
                         if u in prior.get('sold_quantity_by_uom', {}) else None,
                         decimal(current.get('sold_quantity_by_uom', {}).get(u))/Decimal(str(current['supported_day_count']))
                         if u in current.get('sold_quantity_by_uom', {}) else None) for u in sorted(units)}
    before = {str(r.get('upc')): r for r in prior.get('_comparison_rows') or []}
    after = {str(r.get('upc')): r for r in current.get('_comparison_rows') or []}
    drivers = []
    for upc in before.keys() & after.keys():
        a, b = before[upc], after[upc]
        old = decimal(a.get('sales_amount'))/Decimal(str(prior['supported_day_count']))
        new = decimal(b.get('sales_amount'))/Decimal(str(current['supported_day_count']))
        drivers.append({'upc': upc, 'name': b.get('name'), 'sales_per_day': change(old, new)})
    drivers.sort(key=lambda r: abs(r['sales_per_day']['change']), reverse=True)
    def evidence(p):
        return {k: v for k, v in p.items() if k not in {'_comparison_rows', 'top_items'}}
    return {'data_available': True, 'item_query': query, 'prior': evidence(prior), 'current': evidence(current),
            'per_supported_day': metrics, 'quantity_per_supported_day_by_uom': quantity,
            'largest_matched_upc_changes': drivers[:10], 'matched_upc_count': len(drivers),
            'unmatched_upcs': {'prior_only': len(before.keys()-after.keys()), 'current_only': len(after.keys()-before.keys())},
            'source': 'CANONICAL_POS; COST_FROM_VERIFIED_COST_EVIDENCE',
            'interpretation': 'Observed association, not proof of price/promotion causality. Missing dates and absent UPCs are not zero. Compare weekdays, price types, stock availability and units before advice. GP excludes unverified losses and must not be called final adjusted profit.'}
