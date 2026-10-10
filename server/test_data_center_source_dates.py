"""Latest source evidence must not disappear outside a short calendar window."""
import ast
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any
import unittest


class LatestSourceDatesTest(unittest.TestCase):
    def board(self, snapshots, daily=None):
        class Cursor:
            def execute(self, sql):
                self.sql = sql
            def fetchall(self):
                return snapshots
            def close(self):
                pass
        cursor = Cursor()
        class Connection:
            def cursor(self, **kwargs):
                return cursor
        @contextmanager
        def connect():
            yield Connection()
        today = date(2026, 10, 10)
        scope = {'Any': Any, 'date': date, 'timedelta': timedelta,
                 'db_conn': connect, 'business_today': lambda: today,
                 'completed_through_date': lambda: today - timedelta(days=1),
                 'pos_expected_through_date': lambda: today - timedelta(days=2),
                 'movement_expected_through_date': lambda: today - timedelta(days=2),
                 '_health_file_date': lambda row: row['date'],
                 'source_data_days': lambda cur, source, **kwargs: (daily or {}).get(source, [])}
        tree = ast.parse(Path(__file__).with_name('data_coverage.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'data_health_14_day_board')
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'data_coverage.py', 'exec'), scope)
        result = scope[node.name](days=14)
        self.assertIn("processing_status='INGESTED'", cursor.sql)
        self.assertIn('duplicate_of_file_id IS NULL', cursor.sql)
        return result

    def test_old_snapshots_remain_latest_without_extra_calendar_days(self):
        board = self.board([{'source_type': 'live_fresh_suggestion', 'date': date(2026,9,10), 'original_filename': 'fresh.xlsx'},
                            {'source_type': 'on_hand', 'date': date(2026,9,20), 'original_filename': 'oh.xls'}])
        self.assertEqual(len(board['rows']), 14)
        self.assertEqual(board['latest']['LIVE_FRESH']['file'], 'fresh.xlsx')
        self.assertEqual(board['latest']['OH']['date'], date(2026,9,20))
        self.assertTrue(all(r['sources']['OH']['status'] == 'NONE' for r in board['rows']))

    def test_business_date_wins_over_upload_order_and_future_dates(self):
        board = self.board([{'source_type':'price_list','date':date(2026,10,7),'original_filename':'older-reupload.xls'},
                            {'source_type':'price_list','date':date(2026,10,9),'original_filename':'newer.xls'},
                            {'source_type':'price_list','date':date(2026,10,11),'original_filename':'future.xls'}])
        self.assertEqual(board['latest']['PRICE'], {'date':date(2026,10,9),'file':'newer.xls'})
        self.assertIsNone(board['latest']['FROZEN']['date'])

    def test_old_canonical_daily_evidence_does_not_fill_missing_recent_days(self):
        board = self.board([], {'movement':[{'date':date(2026,9,1),'original_filename':'mvt-old.xls'}]})
        self.assertEqual(board['latest']['MVT']['date'], date(2026,9,1))
        self.assertEqual(board['rows'][2]['sources']['MVT']['status'], 'MISSING')
        self.assertEqual(sum(r['overall_status']=='CURRENT_DAY' for r in board['rows']), 1)
        self.assertEqual(board['rows'][1]['overall_status'], 'PENDING')


if __name__ == '__main__':
    unittest.main()
