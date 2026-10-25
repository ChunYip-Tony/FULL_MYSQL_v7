from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
import unittest

from ai_price_history import posted_price_history


class PostedPriceHistoryTests(unittest.TestCase):
    def page(self, rows, **args):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        context = MagicMock()
        context.__enter__.return_value.cursor.return_value = cur
        with patch('ai_price_history.db_conn', return_value=context):
            result = posted_price_history({'upc': '0000123', **args})
        return result, cur.execute.call_args.args

    def rows(self, n):
        return [dict(ean_upc='0000123', upload_timestamp=datetime(2026, 10, 24, 1),
                     file_id=199, raw_id=100-i, configured_price=Decimal('14.99'),
                     price_quantity=None, price_type='TPR') for i in range(n)]

    def test_paging_keeps_identity_source_and_unknown_unit(self):
        result, (sql, params) = self.page(self.rows(51))
        self.assertEqual(result['returned_count'], 50)
        self.assertTrue(result['has_more'])
        self.assertFalse(result['historical_coverage_complete'])
        self.assertEqual(result['rows'][0]['source_business_date'], '2026-10-23')
        self.assertIsNone(result['rows'][0]['historical_selling_unit'])
        self.assertIsNone(result['rows'][0]['price_quantity'])
        self.assertEqual(params, ('0000123',))
        self.assertNotIn('sales_period_observation', sql)
        self.assertNotIn('quick_check_current', sql)
        final, (_, values) = self.page(self.rows(1), cursor=result['next_cursor'])
        self.assertEqual(values[-3:], (datetime(2026, 10, 24, 1), 199, 51))
        self.assertTrue(final['matching_scan_complete'])
        self.assertIsNone(final['next_cursor'])

    def test_requested_dates_use_store_timezone_and_remain_parameterized(self):
        result, (sql, params) = self.page([], start_date='2026-10-23', end_date='2026-10-23')
        self.assertEqual(params, ('0000123', datetime(2026, 10, 23, 7), datetime(2026, 10, 24, 7)))
        self.assertIn('f.error_count=0', sql)
        self.assertIn('duplicate_of_file_id IS NULL', sql)
        self.assertFalse(result['data_available'])
        self.assertFalse(result['historical_coverage_complete'])

    def test_invalid_identity_dates_and_cross_query_cursor_fail_before_db(self):
        result, _ = self.page(self.rows(51))
        cases = [{'upc': '123 OR 1=1'}, {'start_date': '2026-02-31'},
                 {'start_date': '2026-10-24', 'end_date': '2026-10-23'},
                 {'cursor': 'not base64'},
                 {'upc': '0000456', 'cursor': result['next_cursor']},
                 {'start_date': '2026-10-23', 'cursor': result['next_cursor']}]
        with patch('ai_price_history.db_conn') as db:
            for args in cases:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    posted_price_history({'upc': '0000123', **args})
            db.assert_not_called()


if __name__ == '__main__':
    unittest.main()
