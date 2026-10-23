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
    if prior.get("source_revision") != current.get("source_revision"):
        return {"data_available":False,"reason":"SOURCE_CHANGED_DURING_COMPARISON","advice":"Retry against one current revision."}
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
                         if prior.get('sold_quantity_by_uom', {}).get(u) is not None else None,
                         decimal(current.get('sold_quantity_by_uom', {}).get(u))/Decimal(str(current['supported_day_count']))
                         if current.get('sold_quantity_by_uom', {}).get(u) is not None else None) for u in sorted(units)}
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
            'driver_coverage_complete':not(prior.get('items_truncated') or current.get('items_truncated')),
            'unmatched_upcs': {'prior_only': len(before.keys()-after.keys()), 'current_only': len(after.keys()-before.keys())},
            'source': 'CANONICAL_POS; COST_FROM_VERIFIED_COST_EVIDENCE',
            'interpretation': 'Observed association, not proof of price/promotion causality. Missing dates and absent UPCs are not zero. Compare weekdays, price types, stock availability and units before advice. GP is before all inventory adjustments, dumping and shrinkage and must not be called final adjusted profit.'}


def growth_opportunities(args, sales_reader):
    """A ranked work queue based on facts; proposed gains are never manufactured."""
    current=sales_reader({'item_query':args.get('item_query'),
        'supported_days':args.get('supported_days') or 7,'_comparison':True})
    if current.get('data_available') is False or current.get('needs_details'):
        return current
    rows=current.get('_comparison_rows') or []
    days=current.get('supported_day_count') or 0
    if not days:return {'data_available':False,'reason':'NO_SUPPORTED_POS_DAYS'}
    known=[r for r in rows if r.get('gp_dollars') is not None and r.get('sold_quantity') is not None]
    unknown=[r for r in rows if r.get('gp_dollars') is None or r.get('sold_quantity') is None]
    actions=[]
    for r in sorted(known,key=lambda r:Decimal(str(r['gp_dollars'])))[:3]:
        if Decimal(str(r['gp_dollars']))>=0:continue
        actions.append({'priority':1,'action':'REVIEW_NEGATIVE_HISTORICAL_GP','upc':r['upc'],'name':r['name'],
            'sales':r['sales_amount'],'historical_gp_per_supported_day':Decimal(str(r['gp_dollars']))/days,
            'evidence_confidence':'VERIFIED_POS_QUANTITY_AND_HISTORICAL_COST',
            'next_step':'Check cost lineage, returns and price-type mix; use price-review gates before changing price.',
            'success_metric':'Improve comparable GP/day without increasing booked waste or hiding lost revenue.'})
    for r in sorted(known,key=lambda r:Decimal(str(r['gp_dollars'])),reverse=True)[:3]:
        if Decimal(str(r['gp_dollars']))<=0:continue
        actions.append({'priority':2,'action':'PROTECT_PROFITABLE_AVAILABILITY','upc':r['upc'],'name':r['name'],
            'sales':r['sales_amount'],'historical_gp_per_supported_day':Decimal(str(r['gp_dollars']))/days,
            'evidence_confidence':'VERIFIED_HISTORICAL_GP; STOCK_CHECK_REQUIRED',
            'next_step':'Check current family stock, usable condition and inbound receipts before proposing replenishment or display changes.',
            'success_metric':'Maintain or improve GP/day and same-unit sell-through; monitor disposal cost.'})
    if unknown:
        actions.append({'priority':3,'action':'RESOLVE_HIGH_REVENUE_EVIDENCE_GAPS',
            'items':[{'upc':r['upc'],'name':r['name'],'sales':r['sales_amount']} for r in sorted(unknown,key=lambda r:Decimal(str(r['sales_amount'])),reverse=True)[:3]],
            'evidence_confidence':'REVENUE_ONLY; GP_OR_QUANTITY_UNVERIFIED',
            'next_step':'Resolve POS weight, unit or historical-cost evidence before margin or price recommendations.',
            'success_metric':'Verified quantity and cost coverage; revenue remains included.'})
    comparison=compare_performance({'item_query':args.get('item_query'),'supported_days':args.get('supported_days') or 7},sales_reader)
    declines=[r for r in comparison.get('largest_matched_upc_changes',[]) if r['sales_per_day']['change']<0]
    for r in declines[:3]:
        actions.append({'priority':4,'action':'TEST_SALES_RECOVERY','upc':r['upc'],'name':r['name'],
            'sales_per_day':r['sales_per_day'],'evidence_confidence':'OBSERVED_DECLINE; CAUSE_UNPROVEN',
            'next_step':'Check availability, weekday mix and promotion changes; if appropriate test one display or assortment change for seven comparable supported days.',
            'success_metric':'GP/day first, with POS sales/day, verified quantity/day and booked waste as guardrails.'})
    return {'data_available':True,'supported_dates':current.get('supported_dates'),
        'source':'CANONICAL_POS_AND_HISTORICAL_COST','sales_dollars':current.get('sales_dollars'),
        'historical_gp_dollars':current.get('gp_dollars'),'actions':sorted(actions,key=lambda r:r['priority']),
        'comparison':comparison,'forecast_or_uplift':None,
        'coverage_note':'Rankings cover returned items only.' if current.get('items_truncated') else 'All returned POS items considered.',
        'profit_basis':'Historical selling GP before dumping, shrinkage and other inventory adjustments. No family-to-UPC loss allocation.',
        'experiment_rule':'Change one controllable factor; compare equivalent supported dates and price types. Before/after is observational, not proven causal lift.'}
