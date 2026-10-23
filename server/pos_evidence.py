"""Shared POS authority gates. Revenue never depends on quantity availability."""
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import json
from pathlib import Path

@lru_cache(maxsize=1)
def source_holds():
    return json.loads(Path(__file__).with_name('pos_quantity_confirmations.json').read_text()).get('source_quality_holds', [])

def eligible_sales_days(days, limit=None):
    result = [r for r in days if not any(
        str(r.get('file_id', r.get('source_file_id', ''))) == str(h.get('file_id'))
        and (not h.get('date') or str(r['date'])[:10] == h['date']) for h in source_holds())]
    return result[:limit] if limit is not None else result

def verified_pos_quantity(row, observation, day):
    value = observation.get('sold_quantity')
    try:
        qty = Decimal(str(value))
        sales = Decimal(str(observation.get('sales_amount') or 0))
    except (InvalidOperation, TypeError, ValueError):
        return None, 'QUANTITY_UNAVAILABLE'
    if not qty.is_finite() or not sales.is_finite():
        return None, 'QUANTITY_UNAVAILABLE'
    if qty < 0 or sales < 0 or (qty == 0 and sales != 0):
        return None, 'QUANTITY_OR_RETURN_REVIEW'
    unit = str(row.get('selling_uom') or '').upper()
    if not unit:
        return None, 'SELLING_UNIT_UNVERIFIED'
    if unit != 'LB':
        return qty, 'POS_SELLING_UNIT'
    if 'TOTAL' in (observation.get('price_types') or {}):
        return qty, 'POS_QTY_WEIGHT'
    from family_daily_gp import confirmed_pos_lb
    confirmed = confirmed_pos_lb({**row, 'latest_daily_pos_reported_qty': qty,
                                  'latest_daily_sales_dollars': sales}, day)
    if confirmed is not None:
        return confirmed, 'POS_QTY_WEIGHT'
    if qty == 0 and sales == 0:
        return qty, 'CANONICAL_ZERO_SALES'
    return None, 'POS_WEIGHT_UNVERIFIED'
