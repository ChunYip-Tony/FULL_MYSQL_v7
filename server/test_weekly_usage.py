from datetime import date
from decimal import Decimal
import sys
import types
import unittest
from unittest.mock import patch
from fisherman_weekly_usage import promotion_dates, type_average, estimate_member, weekly_usage

def daily(reg=10, sale=20):
    return {date(2026, 10, 1): {'price_types': {'REG': {'sold_quantity': reg, 'sales_amount': reg * 5}}},
            date(2026, 10, 2): {'price_types': {'SALE': {'sold_quantity': sale, 'sales_amount': sale * 4}}}}

class WeeklyUsageTest(unittest.TestCase):
    def test_oct16_weekend(self):
        days, promo = promotion_dates('2026-10-16', '2026-10-22', True)
        self.assertEqual(len(days), 7)
        self.assertEqual([d.day for d in promo], [16, 17, 18])

    def test_partial_week(self):
        _, promo = promotion_dates('2026-10-17', '2026-10-23', True)
        self.assertEqual([d.day for d in promo], [17, 18, 23])

    def test_multiple_weekends(self):
        self.assertEqual(len(promotion_dates('2026-10-16', '2026-10-29', True)[1]), 6)

    def test_everyday(self):
        self.assertEqual(len(promotion_dates('2026-10-16', '2026-10-22', False)[1]), 7)

    def test_weighted_weekend(self):
        result = estimate_member(daily(), 4, 3)
        self.assertEqual(result['regular_usage'], Decimal(40))
        self.assertEqual(result['promotion_usage'], Decimal(60))
        self.assertEqual(result['total'], Decimal(100))

    def test_sale_only_does_not_require_reg(self):
        result = estimate_member({d: row for d, row in daily().items() if 'SALE' in row['price_types']}, 0, 7)
        self.assertEqual(result['total'], Decimal(140))

    def test_missing_sale_fallback_label(self):
        result = estimate_member({d: row for d, row in daily().items() if 'REG' in row['price_types']}, 4, 3)
        self.assertEqual(result['total'], Decimal(100))
        self.assertTrue(result['sale_fallback_to_reg'])
        self.assertEqual(result['confidence'], 'LOW')

    def test_zero_and_unknown_days(self):
        data = daily()
        data[date(2026, 10, 3)] = {'price_types': {'REG': {'sold_quantity': 0, 'sales_amount': 0}}}
        data[date(2026, 10, 4)] = {'price_types': {}}
        result = type_average(data, 'REG', 28)
        self.assertEqual(result['days'], 2)
        self.assertEqual(result['average'], Decimal(5))

    def test_supported_sale_average_wins(self):
        data = daily(10, 30)
        for day in range(3, 9):
            data[date(2026, 10, day)] = {'price_types': {'SALE': {'sold_quantity': 30, 'sales_amount': 120}}}
        result = estimate_member(data, 4, 3)
        self.assertEqual(result['total'], Decimal(130))
        self.assertFalse(result['sale_fallback_to_reg'])

    def test_weak_sale_uses_double_reg(self):
        result = estimate_member(daily(10, 30), 4, 3)
        self.assertEqual(result['total'], Decimal(100))
        self.assertTrue(result['sale_fallback_to_reg'])

    def test_no_history_remains_unknown(self):
        self.assertIsNone(estimate_member({}, 4, 3)['total'])

    def test_tpr_only_is_regular_baseline(self):
        data = {date(2026, 10, 1): {'price_types': {'TPR': {'sold_quantity': 10, 'sales_amount': 40}}}}
        result = estimate_member(data, 4, 3)
        self.assertEqual(result['reg']['average'], Decimal(10))
        self.assertEqual(result['regular_usage'], Decimal(40))
        self.assertEqual(result['promotion_usage'], Decimal(60))
        self.assertEqual(result['total'], Decimal(100))

    def test_reg_tpr_same_date_counts_once(self):
        data = {date(2026, 10, 1): {'price_types': {
            'REG': {'sold_quantity': 4, 'sales_amount': 20},
            'TPR': {'sold_quantity': 6, 'sales_amount': 24},
            'SALE': {'sold_quantity': 30, 'sales_amount': 90}}},
            date(2026, 10, 2): {'price_types': {'TPR': {'sold_quantity': 20, 'sales_amount': 80}}}}
        result = type_average(data, ('REG', 'TPR'), 28)
        self.assertEqual(result['days'], 2)
        self.assertEqual(result['quantity'], Decimal(30))
        self.assertEqual(result['average'], Decimal(15))

    def test_tpr_does_not_change_sale_rate(self):
        data = daily()
        data[date(2026, 10, 1)]['price_types']['TPR'] = {'sold_quantity': 90, 'sales_amount': 360}
        self.assertEqual(type_average(data, 'SALE', 90)['average'], Decimal(20))

    def test_family_249_and_units(self):
        class Cursor:
            def execute(self, sql, args):
                self.members = 'SELECT * FROM quick_check_current' in sql
            def fetchall(self):
                if not self.members:
                    return [{'family_id': 1, 'main_article_number': '1361689'}]
                return [{'upc_id': 1, 'ean_upc': '24068900000', 'selling_uom': 'LB'},
                        {'upc_id': 2, 'ean_upc': '24968900000', 'selling_uom': 'LB'},
                        {'upc_id': 3, 'ean_upc': '24568900000', 'selling_uom': 'PACK'}]
            def close(self): pass
        class Conn:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self, **kwargs): return Cursor()
        runtime = types.SimpleNamespace(db_conn=Conn,
            _canonical_sales_days=lambda cur, limit: [{'date': date(2026, 10, 13)}],
            _daily_sales_by_price_type=lambda cur, upc_id, supported: daily(10 if upc_id == 1 else 2, 20 if upc_id == 1 else 4),
            _safe_qty_uom=lambda upc, unit: unit)
        with patch.dict(sys.modules, {'webapp_v2_runtime': runtime}):
            result = weekly_usage({'start_date': '2026-10-16', 'end_date': '2026-10-22', 'items': [
                {'article_or_upc': '1361689', 'name': 'Fish', 'selling_unit': 'LB', 'weekend_only': True}]})
        row = result['items'][0]
        self.assertEqual(len(row['members']), 2)
        self.assertEqual(row['total'], Decimal(120))
        self.assertEqual(row['promotion_usage'], Decimal(72))

if __name__ == '__main__': unittest.main()
