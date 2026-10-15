"""Date-boundary regressions without database or OpenAI network requests."""
import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest
from typing import Any
from unittest.mock import Mock, MagicMock


def extract(filename, names, namespace):
    tree = ast.parse(Path(__file__).with_name(filename).read_text())
    nodes = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, 'exec'), namespace)


class SalesDateTests(unittest.TestCase):
    def setUp(self):
        self.ns = {'date': date, 'Any': Any, 'Decimal': Decimal, 're': __import__('re')}
        extract('webapp_v2_runtime.py', {'_select_performance_range_days'}, self.ns)
        self.select = self.ns['_select_performance_range_days']
        self.days = [{'date': date(2026, 10, d)} for d in [1, 2, 3, 5, 6, 8, 9, 10, 12, 13]]

    def test_missing_end_uses_only_supported_days_in_range(self):
        start, end, days = self.select(self.days, date(2026, 10, 8), date(2026, 10, 14), allow_partial_range=True)
        self.assertEqual((start, end), (date(2026, 10, 8), date(2026, 10, 13)))
        self.assertEqual([x['date'].day for x in days], [8, 9, 10, 12, 13])

    def test_missing_start_moves_forward_inside_requested_range(self):
        start, end, days = self.select(self.days, date(2026, 10, 7), date(2026, 10, 11), allow_partial_range=True)
        self.assertEqual((start.day, end.day, len(days)), (8, 10, 3))

    def test_default_is_latest_seven_supported_days(self):
        start, end, days = self.select(self.days, None, None, allow_partial_range=True)
        self.assertEqual((start.day, end.day, len(days)), (5, 13, 7))

    def test_explicit_unavailable_day_never_falls_back_to_older_sales(self):
        with self.assertRaisesRegex(ValueError, '^NO_SUPPORTED_DATES_IN_RANGE$'):
            self.select(self.days, date(2026, 10, 14), date(2026, 10, 14), allow_partial_range=True)

    def test_missing_day_between_supported_days_is_not_zero(self):
        with self.assertRaisesRegex(ValueError, '^NO_SUPPORTED_DATES_IN_RANGE$'):
            self.select(self.days, date(2026, 10, 11), date(2026, 10, 11), allow_partial_range=True)

    def test_strict_callers_keep_existing_end_validation(self):
        with self.assertRaisesRegex(ValueError, '^END_DATE_NOT_SUPPORTED$'):
            self.select(self.days, date(2026, 10, 8), date(2026, 10, 14))

    def test_strict_callers_keep_existing_start_validation(self):
        with self.assertRaisesRegex(ValueError, '^START_DATE_NOT_SUPPORTED$'):
            self.select(self.days, date(2026, 10, 7), date(2026, 10, 13))

    def test_reversed_and_empty_ranges(self):
        with self.assertRaisesRegex(ValueError, '^START_DATE_AFTER_END_DATE$'):
            self.select(self.days, date(2026, 10, 14), date(2026, 10, 8), allow_partial_range=True)
        with self.assertRaisesRegex(ValueError, '^NO_COMPLETED_SUPPORTED_SALES_DATE$'):
            self.select([], None, None, allow_partial_range=True)

    def canonical(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        connection = MagicMock()
        connection.cursor.return_value = cursor
        context = MagicMock()
        context.__enter__.return_value = connection
        self.ns.update(db_conn=lambda: context,
                       _canonical_sales_days=lambda *args, **kwargs: self.days,
                       _batch_daily_sales_by_price_type=lambda *args: {},
                       _performance_range_cost_rows=lambda *args: {})
        extract('webapp_v2_runtime.py', {'performance_range'}, self.ns)
        return self.ns['performance_range'], cursor

    def test_canonical_partial_response_labels_requested_and_actual_bounds(self):
        performance, cursor = self.canonical()
        out = performance(date(2026, 10, 7), date(2026, 10, 14), item_query='24053300000', allow_partial_range=True)
        self.assertEqual(out['requested_start_date'], date(2026, 10, 7))
        self.assertEqual(out['requested_end_date'], date(2026, 10, 14))
        self.assertEqual((out['start_date'].day, out['end_date'].day), (8, 13))
        self.assertTrue(out['range_adjusted'])
        self.assertEqual(out['supported_day_count'], 5)
        self.assertFalse(out['missing_calendar_dates_are_zero'])
        self.assertEqual(cursor.execute.call_args.args[1], ('%24053300000%',) * 4)
        cursor.close.assert_called_once()

    def test_canonical_default_still_uses_seven_supported_days(self):
        performance, _ = self.canonical()
        out = performance()
        self.assertEqual(out['supported_day_count'], 7)
        self.assertFalse(out['range_adjusted'])

    def test_canonical_strict_boundary_error_closes_cursor(self):
        performance, cursor = self.canonical()
        with self.assertRaisesRegex(ValueError, '^END_DATE_NOT_SUPPORTED$'):
            performance(date(2026, 10, 8), date(2026, 10, 14))
        cursor.close.assert_called_once()

    def ai(self, result=None, error=None):
        performance = Mock(return_value=result, side_effect=error)
        self.ns.update(performance_range=performance, _item_search_query=lambda x: x,
                       latest_performance_date=lambda: {'latest_completed_supported_sales_date': date(2026, 10, 13)})
        extract('yipman_ai.py', {'_parse_iso_date', '_sales_tool', '_select_sales_item_rows', '_norm_text', '_norm_num'}, self.ns)
        return self.ns['_sales_tool'], performance

    def result(self):
        return {'start_date': date(2026, 10, 8), 'end_date': date(2026, 10, 13),
                'requested_start_date': date(2026, 10, 8), 'requested_end_date': date(2026, 10, 14),
                'range_adjusted': True, 'supported_day_count': 5,
                'supported_dates': [date(2026, 10, d) for d in [8, 9, 10, 12, 13]],
                'missing_calendar_dates_are_zero': False,
                'items': [{'upc': '24053300000', 'name': 'TILAPIA 750 GM UP S&G',
                           'sales_amount': '49.90', 'sold_quantity': '10', 'qty_uom': 'LB', 'gp_dollars': '12'}]}

    def test_tilapia_retains_exact_upc_pos_quantity_and_actual_dates(self):
        tool, perf = self.ai(self.result())
        out = tool({'start_date': '2026-10-08', 'end_date': '2026-10-14', 'item_query': '24053300000'})
        self.assertTrue(out['data_available'])
        self.assertTrue(out['range_adjusted'])
        self.assertEqual(out['end_date'], date(2026, 10, 13))
        self.assertEqual(out['supported_day_count'], 5)
        self.assertEqual(out['sales_dollars'], Decimal('49.90'))
        self.assertEqual(out['sold_quantity_by_uom'], {'LB': Decimal('10')})
        self.assertEqual(perf.call_args.kwargs['item_query'], '24053300000')
        self.assertTrue(perf.call_args.kwargs['allow_partial_range'])

    def test_general_question_passes_null_dates(self):
        tool, perf = self.ai(self.result())
        tool({'start_date': None, 'end_date': None, 'item_query': '24053300000'})
        self.assertEqual(perf.call_args.args[:2], (None, None))

    def test_null_end_with_start_is_still_one_exact_day(self):
        tool, perf = self.ai(self.result())
        tool({'start_date': '2026-10-13', 'end_date': None, 'item_query': '24053300000'})
        self.assertEqual(perf.call_args.args[:2], (date(2026, 10, 13), date(2026, 10, 13)))

    def test_no_supported_day_returns_unavailable_not_zero(self):
        tool, _ = self.ai(error=ValueError('NO_SUPPORTED_DATES_IN_RANGE'))
        out = tool({'start_date': '2026-10-14', 'end_date': '2026-10-14', 'item_query': '24053300000'})
        self.assertFalse(out['data_available'])
        self.assertNotIn('sales_dollars', out)
        self.assertNotIn('sold_quantity_by_uom', out)
        self.assertEqual(out['latest_completed_supported_sales_date'], date(2026, 10, 13))

    def test_database_errors_are_not_relabelled_as_missing_data(self):
        tool, _ = self.ai(error=RuntimeError('DATABASE_OFFLINE'))
        with self.assertRaisesRegex(RuntimeError, 'DATABASE_OFFLINE'):
            tool({'start_date': None, 'end_date': None, 'item_query': '24053300000'})

    def test_yesterday_quantity_does_not_call_unavailable_day_zero_sales(self):
        self.ns.update(re=__import__('re'), completed_through_date=lambda: date(2026, 10, 14),
                       _sales_tool=lambda args: {'data_available': False, 'latest_completed_supported_sales_date': date(2026, 10, 13)})
        extract('yipman_ai.py', {'_quick_quantity_answer'}, self.ns)
        out = self.ns['_quick_quantity_answer']('How many lb of tilapia did we sell yesterday?')
        self.assertIn('No sold quantity can be confirmed', out['answer'])
        self.assertNotIn('no matching positive', out['answer'])

    def test_yesterday_report_does_not_crash_on_missing_boundary(self):
        self.ns.update(completed_through_date=lambda: date(2026, 10, 14),
                       performance_range=Mock(side_effect=ValueError('END_DATE_NOT_SUPPORTED')),
                       latest_performance_date=lambda: {'latest_completed_supported_sales_date': date(2026, 10, 13)})
        extract('yipman_ai.py', {'_quick_daily_answer'}, self.ns)
        out = self.ns['_quick_daily_answer']('Yesterday sales')
        self.assertEqual(out['mode'], 'CANONICAL_DATE_UNAVAILABLE')
        self.assertIn('does not mean zero sales', out['answer'])


if __name__ == '__main__':
    unittest.main()
