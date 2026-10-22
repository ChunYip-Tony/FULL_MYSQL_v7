"""Supplemental booked cost from canonical selling-article 251/252 valuations.

This module never returns or allocates an individual UPC's sold quantity.
"""
from decimal import Decimal

SOURCE = 'SELLING_MVT_251_252'
COST_POLICY = 'FAMILY_RECEIPT_251_OH_V1'


def eligible(row, observation):
    article = observation.get('selling_article_number')
    return not article or str(article) == str(row.get('article_number') or '')


def movement_cost_rows(cur, rows, end_date):
    from data_coverage import source_data_days
    articles = sorted({str(r['article_number']) for r in rows if r.get('article_number')})
    if not articles:
        return {}
    cache_key=(str(end_date),'supplementary_cost_movement_days')
    coverage_cache=getattr(cur,'_finder_cost_coverage',{})
    days=coverage_cache.get(cache_key)
    if days is None:
        days = source_data_days(cur, 'movement', limit=180, up_to=end_date)
        try:
            cur._finder_cost_coverage={cache_key:days}
        except (AttributeError,TypeError):
            pass
    canonical = {d['date']: int(d['file_id']) for d in days}
    files = sorted(set(canonical.values()))
    if not files:
        return {}
    ph = lambda xs: ','.join(['%s'] * len(xs))
    cur.execute(f"""SELECT article_number,posting_date,file_id,base_uom_code,
            SUM(base_quantity) AS qty,SUM(amount_local_currency) AS amount
        FROM movement_history
        WHERE article_number IN ({ph(articles)}) AND file_id IN ({ph(files)})
          AND posting_date<=%s AND movement_type IN ('251','252')
        GROUP BY article_number,posting_date,file_id,base_uom_code""",
        (*articles,*files,end_date))
    by_article = {}
    for r in cur.fetchall():
        if canonical.get(r['posting_date']) != int(r['file_id']):
            continue
        qty, amount = Decimal(str(r.get('qty') or 0)), Decimal(str(r.get('amount') or 0))
        unit = str(r.get('base_uom_code') or '').strip().upper()
        if qty >= 0 or amount >= 0 or not unit:
            continue
        by_article.setdefault(str(r['article_number']), []).append({
            'source_type': SOURCE, 'business_date': r['posting_date'],
            'cost_value': amount/qty, 'cost_uom': unit,
            'cost_observation_id': 0,
            'selling_article_number': str(r['article_number']),
            'cost_basis': 'BOOKED_SELLING_MOVEMENT_VALUATION',
        })
    # Mixed base units for one article/day are unresolved, never averaged.
    for article, observations in by_article.items():
        units = {}
        for o in observations:
            units.setdefault(o['business_date'], set()).add(o['cost_uom'])
        by_article[article] = sorted([o for o in observations if len(units[o['business_date']]) == 1],
            key=lambda o:o['business_date'], reverse=True)
    return by_article


def latest_movement_cost(cur, row, day):
    return next(iter(movement_cost_rows(cur,[row],day).get(str(row.get('article_number') or ''),[])),None)
