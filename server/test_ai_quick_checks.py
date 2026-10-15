"""Regression cases found by the 500-question seafood operations evaluation."""
import sys
import types
import unittest
import ast
from pathlib import Path
from typing import Any
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fisherman_weekly_usage import weekly_usage, promotion_schedule
import test_ai_sales_dates as sales_dates


class ItemSalesSelectionTest(unittest.TestCase):
    def setUp(self):
        self.helper = sales_dates.SalesDateTests()
        self.helper.setUp()
        self.result = self.helper.result
        self.ai = self.helper.ai

    def test_latest_n_uses_supported_days_instead_of_calendar_guess(self):
        start, end, days = self.helper.select(self.helper.days, None, None, latest_supported_day_count=10)
        self.assertEqual((start.day, end.day, len(days)), (1, 13, 10))
        tool, performance = self.ai(self.result())
        tool({'item_query': '24053300000', 'supported_days': 14})
        self.assertEqual(performance.call_args.kwargs['latest_supported_day_count'], 14)

    def test_live_tilapia_does_not_include_fresh_family_members(self):
        result = self.result()
        result['items'] = [
            {'upc': '24060200000', 'name': 'LIVE TILAPIA', 'sold_quantity': 58.56, 'sales_amount': 555.82, 'qty_uom': 'LB'},
            {'upc': '24053500000', 'name': 'FRESH TILAPIA', 'sold_quantity': 63.26, 'sales_amount': 300, 'qty_uom': 'LB'},
            {'upc': '24960200000', 'name': 'LIVE TILAPIA(Fried Service)', 'sold_quantity': 17.8, 'sales_amount': 100, 'qty_uom': 'LB'}]
        tool, _ = self.ai(result)
        out = tool({'item_query': 'live tilapia'})
        self.assertEqual(out['matched_item_count'], 1)
        self.assertEqual(out['sold_quantity_by_uom'], {'LB': Decimal('58.56')})

    def test_broad_tilapia_asks_instead_of_summing_variants(self):
        result = self.result()
        result['items'] += [{'upc': '24060200000', 'name': 'LIVE TILAPIA', 'qty_uom': 'LB'}]
        tool, _ = self.ai(result)
        out = tool({'item_query': 'tilapia'})
        self.assertTrue(out['needs_details'])
        self.assertNotIn('sold_quantity_by_uom', out)
        self.assertEqual({x['number'] for x in out['options']}, {'24053300000', '24060200000'})


class WeeklyQuickCheckTest(unittest.TestCase):
    def call(self, query='24060200000', unit=None, count=3, weekend=False, members=None):
        rows = members or [
            {'upc_id': 1, 'ean_upc': '24060200000', 'selling_uom': 'LB'},
            {'upc_id': 2, 'ean_upc': '24960200000', 'selling_uom': 'LB'},
            {'upc_id': 3, 'ean_upc': '24053500000', 'selling_uom': 'LB'},
            {'upc_id': 4, 'ean_upc': '24560200000', 'selling_uom': 'PACK'}]
        class Cursor:
            def execute(self, sql, args):
                self.members = 'SELECT * FROM quick_check_current' in sql
            def fetchall(self):
                return rows if self.members else [{'family_id': 1, 'main_article_number': '1361602'}]
            def close(self): pass
        class Conn:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self, **kwargs): return Cursor()
        runtime = types.SimpleNamespace(db_conn=Conn,
            _canonical_sales_days=lambda cur, limit: [{'date': date(2026, 10, 13)}],
            _daily_sales_by_price_type=lambda cur, upc_id, supported: {
                date(2026, 10, 13): {'price_types': {'REG': {'sold_quantity': upc_id * 10, 'sales_amount': upc_id * 50}}}},
            _safe_qty_uom=lambda upc, unit: unit)
        with patch.dict(sys.modules, {'webapp_v2_runtime': runtime}):
            return weekly_usage({'start_date': '2026-10-16', 'end_date': '2026-10-22', 'items': [{
                'article_or_upc': query, 'name': 'Fish', 'selling_unit': unit,
                'weekend_only': weekend, 'promotion_applies': count != 0, 'promotion_days': count}]})

    def test_three_days_not_replaced_by_full_week(self):
        row = self.call()['items'][0]
        self.assertEqual((row['regular_days'], row['promotion_days']), (4, 3))
        self.assertIsNone(row['promotion_dates'])
        self.assertEqual(row['total'], Decimal(300))

    def test_null_or_guessed_ea_uses_verified_lb(self):
        for unit in (None, 'EA'):
            row = self.call(unit=unit)['items'][0]
            self.assertEqual(row['unit'], 'LB')
            self.assertEqual(row['total'], Decimal(300))
        self.assertIn('not used or converted', row['unit_note'])

    def test_live_upc_includes_service_not_fresh_or_pack(self):
        row = self.call()['items'][0]
        self.assertEqual({m['upc'] for m in row['members']}, {'24060200000', '24960200000'})

    def test_short_upc_uses_verified_each(self):
        row = self.call(query='4843', members=[{'upc_id': 1, 'ean_upc': '4843', 'selling_uom': 'EA'}])['items'][0]
        self.assertEqual(row['unit'], 'EA')
        self.assertEqual(row['total'], Decimal(100))

    def test_family_mixed_units_needs_choice(self):
        row = self.call(query='1361602')['items'][0]
        self.assertEqual(row['status'], 'SELLING_UNIT_NEEDS_CONFIRMATION')
        self.assertEqual(row['available_units'], ['LB', 'PACK'])
        self.assertNotIn('total', row)

    def test_zero_and_seven_days(self):
        self.assertEqual(self.call(count=0)['items'][0]['total'], Decimal(210))
        self.assertEqual(self.call(count=7)['items'][0]['total'], Decimal(420))

    def test_weekend_dates_are_preserved(self):
        row = self.call(weekend=True)['items'][0]
        self.assertEqual(row['promotion_dates'], ['2026-10-16', '2026-10-17', '2026-10-18'])

    def test_invalid_or_conflicting_counts_are_rejected(self):
        for count in (-1, 8, True, 3.5):
            with self.assertRaises(ValueError):
                self.call(count=count)
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            promotion_schedule('2026-10-16', '2026-10-22', {'weekend_only': True, 'promotion_days': 7})


class StockFlowScopeTest(unittest.TestCase):
    def setUp(self):
        class Cursor:
            def execute(self, sql, args=None):
                self.sql = sql
            def fetchall(self):
                if 'MAX(main_article_number)' in self.sql:
                    return [{'family_id': 1, 'family_article': '1361571', 'family_name': 'Pompano', 'family_movement_7d': 570, 'family_movement_uom': 'LB'}]
                return []
            def close(self): pass
        class Conn:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self, **kwargs): return Cursor()
        events = [{'posting_date': date(2026, 10, 13), 'receipt_quantity': 200, 'receipt_uom': 'LB'},
                  {'posting_date': date(2026, 10, 6), 'receipt_quantity': 200, 'receipt_uom': 'LB'}]
        ns = {'Any': Any, 'Decimal': Decimal, 'db_conn': Conn,
              'completed_through_date': lambda: date(2026, 10, 14),
              'source_data_days': lambda cur, source, **kwargs: [{'date': date(2026, 10, d)} for d in range(8, 15)] if source == 'movement' else [],
              '_family_receipt_events_bulk': lambda *args, **kwargs: {1: events},
              '_delivery_pattern': lambda *args, **kwargs: {},
              '_published_family_oh_fallback': lambda rows: {'quantity': 355, 'uom': 'LB'},
              '_d': lambda value: Decimal(str(value or 0))}
        sales_dates.extract('backoffice_runtime.py', {'yipman_best_sellers'}, ns)
        self.flow = ns['yipman_best_sellers']

    def test_department_watch_keeps_qualification_filter(self):
        self.assertEqual(self.flow()['rows'], [])

    def test_specific_item_returns_even_below_watch_threshold(self):
        out = self.flow(family_article='1361571')
        row = out['rows'][0]
        self.assertFalse(row['over_receiving'])
        self.assertEqual(row['family_receipt_7d_qty'], Decimal(200))
        self.assertEqual(row['family_group_movement_7d'], Decimal(570))
        self.assertEqual(len(row['family_receipt_history']), 2)
        self.assertEqual(len(out['movement_dates_7d']), 7)

    def test_unmatched_family_does_not_fall_back_to_department(self):
        self.assertEqual(self.flow(family_article='9999999')['rows'], [])


class ToolSchemaTest(unittest.TestCase):
    def test_strict_object_schemas_require_exact_properties(self):
        tree = ast.parse(Path(__file__).with_name('yipman_ai.py').read_text())
        schema = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TOOLS' for t in node.targets))
        def check(value):
            if isinstance(value, dict):
                if value.get('type') == 'object':
                    self.assertEqual(set(value['required']), set(value['properties']))
                    self.assertFalse(value['additionalProperties'])
                for item in value.values(): check(item)
            elif isinstance(value, list):
                for item in value: check(item)
        check(schema)


if __name__ == '__main__':
    unittest.main()
