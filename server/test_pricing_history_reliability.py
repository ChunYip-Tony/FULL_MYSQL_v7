import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
import sqlite3
import sys
from threading import Event
import time
import types
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from mysql.connector.errors import ReadTimeoutError
import mobile_pricing as pricing
from read_singleflight import ReadSingleFlight


class PricingHistoryReliability(unittest.TestCase):
    def test_current_snapshots_fetch_latest_accepted_tickets_with_priority(self):
        db = sqlite3.connect(':memory:'); db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        db.executescript('''
            CREATE TABLE ingest_file(file_id,upload_timestamp,original_filename,source_type,
                processing_status,error_count,duplicate_of_file_id);
            CREATE TABLE price_list_observation(file_id,upc_id,ean_upc,configured_price,price_type);
        ''')
        # Many repeated old snapshots must not all cross into publisher memory.
        for fid in range(1, 151):
            db.execute('INSERT INTO ingest_file VALUES(?,?,?,\'price_list\',\'INGESTED\',0,NULL)',
                       (fid, '2026-10-22T10:00:00', 'old.xlsx'))
            db.execute('INSERT INTO price_list_observation VALUES(?,1,\'24052400000\',3.99,\'REG\')', (fid,))
        db.executescript('''
            INSERT INTO ingest_file VALUES
                (199,'2026-10-23T10:00:00','latest.xlsx','price_list','INGESTED',0,NULL),
                (200,'2026-10-23T11:00:00','failed.xlsx','price_list','INGESTED',1,NULL),
                (201,'2026-10-23T12:00:00','duplicate.xlsx','price_list','INGESTED',0,199);
            INSERT INTO price_list_observation VALUES
                (199,1,'24052400000',5.99,'REG'),(199,1,'24052400000',4.99,'SALE'),
                (200,1,'24052400000',1.99,'IN STORE'),(201,1,'24052400000',2.99,'IN STORE'),
                (1,2,'24053900000',3.99,'REG'),(199,2,'24053900000',0,'REG');
        ''')
        class Cursor:
            fetched = 0
            def execute(self, query, args=()):
                self.prices = 'price_list_observation' in query
                self.result = db.execute(query.replace('%s','?'), args)
            def fetchall(self):
                rows = [dict(r) for r in self.result.fetchall()]
                if self.prices: self.fetched += len(rows)
                return rows
        cur = Cursor()
        with patch.dict(sys.modules, {'phase3': types.SimpleNamespace(
                _price_list_upload_business_date=lambda v: date.fromisoformat(v[:10]))}):
            result = pricing.price_snapshots(cur, [
                {'upc_id':1,'ean_upc':'24052400000'}, {'upc_id':2,'ean_upc':'24053900000'}], latest_only=True)
        self.assertEqual(cur.fetched, 3)
        self.assertEqual(len(result[1]), 1)
        self.assertEqual(result[1][0]['price'], Decimal('4.99'))
        self.assertEqual(result[1][0]['type'], 'SALE')
        self.assertEqual(result[1][0]['filename'], 'latest.xlsx')
        # Current prices remain discoverable beyond the history endpoint's 120-file window.
        self.assertEqual(result[2][0]['file_id'], 1)

    def test_history_keeps_pos_cost_and_list_without_receipt_or_movement_summaries(self):
        row = {'upc_id': 1, 'family_id': 5, 'ean_upc': '24052400000',
               'selling_uom': 'LB', 'base_uom': 'LB', 'selling_description': 'WHITE PERCH',
               'main_article_number': '1363524'}
        cur = MagicMock(); cur.fetchall.return_value = [row]
        conn = MagicMock(); conn.cursor.return_value = cur
        connection_calls = []
        @contextmanager
        def connection(**kwargs):
            connection_calls.append(kwargs)
            yield conn
        day = date(2026, 10, 22)
        coverage = MagicMock(return_value=[{'date': day, 'file_id': 198}])
        runtime = types.SimpleNamespace(
            _batch_daily_sales_by_price_type=MagicMock(return_value={}),
            _performance_range_cost_rows=MagicMock(return_value={5: [{
                'source_type': 'MOVEMENT_RECEIPT_VALUATION', 'cost_value': Decimal('3.29'),
                'cost_uom': 'LB', 'business_date': date(2026, 10, 9)}]}),
            _ordering_family_movement_metrics=MagicMock(side_effect=AssertionError('movement summary')),
            _family_receipt_events_bulk=MagicMock(side_effect=AssertionError('receipts')))
        modules = {'db': types.SimpleNamespace(db_conn=connection),
                   'data_coverage': types.SimpleNamespace(source_data_days=coverage),
                   'webapp_v2_runtime': runtime,
                   'business_clock': types.SimpleNamespace(business_today=lambda: date(2026, 10, 23),
                                                          completed_through_date=lambda: day)}
        ticket = {'date': date(2026, 10, 23), 'price': Decimal('4.99'),
                  'type': 'REG', 'file_id': 199, 'source': 'PRICE_LIST'}
        with patch.dict(sys.modules, modules), patch.object(pricing, 'price_snapshots', return_value={1: [ticket]}), \
                patch.object(pricing, 'category_index', side_effect=AssertionError('category scan')):
            result = pricing.build_page(requested_upcs={'24052400000'}, history_only=True)
        self.assertEqual([call.args[1] for call in coverage.call_args_list], ['sales_by_price_type'])
        self.assertEqual(connection_calls, [{'read_timeout': 15, 'connection_timeout': 5}])
        member = result['items'][0]['members'][0]
        self.assertEqual(member['current']['price'], Decimal('4.99'))
        self.assertEqual(member['cost']['value'], Decimal('3.29'))
        self.assertEqual(result['through'], day)
        self.assertEqual(member['days'][0]['date'], day)
        self.assertIn('WHERE ean_upc IN', cur.execute.call_args.args[0])
        cur.close.assert_called_once()

    def test_identical_history_requests_share_one_build_regardless_of_upc_order(self):
        started, release = Event(), Event()
        def build(**kwargs):
            self.assertTrue(kwargs['history_only'])
            started.set(); release.wait(3)
            return {'items': []}
        with patch.object(pricing, '_reads', ReadSingleFlight()), \
                patch.object(pricing, 'build_page', side_effect=build) as builder:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(pricing.pricing_history_batch, '24052400000,24053900000')
                self.assertTrue(started.wait(3))
                second = pool.submit(pricing.pricing_history_batch, '24053900000,24052400000')
                time.sleep(.05); release.set()
                self.assertEqual(first.result(3), second.result(3))
            self.assertEqual(builder.call_count, 1)

    def test_history_shares_interactive_read_limit_and_returns_retry_after(self):
        started, release = Event(), Event()
        gate = ReadSingleFlight(max_running=1)
        def interactive():
            started.set(); release.wait(3)
        with patch.object(pricing, '_reads', gate), ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(gate.run, ('interactive',), interactive)
            self.assertTrue(started.wait(3))
            try:
                with self.assertRaises(HTTPException) as error:
                    pricing.pricing_history_batch('24052400000')
                self.assertEqual(error.exception.status_code, 503)
                self.assertEqual(error.exception.headers, {'Retry-After': '5'})
            finally:
                release.set(); pending.result(3)

    def test_timeout_is_retryable_and_does_not_poison_next_request(self):
        with patch.object(pricing, '_reads', ReadSingleFlight()), \
                patch.object(pricing, 'build_page', side_effect=[ReadTimeoutError('private query'), {'items': []}]):
            with self.assertRaises(HTTPException) as error:
                pricing.pricing_history_batch('24052400000')
            self.assertEqual(error.exception.status_code, 503)
            self.assertNotIn('private query', error.exception.detail)
            self.assertEqual(pricing.pricing_history_batch('24052400000')['items'], [])

    def test_invalid_batch_never_reaches_database(self):
        with patch.object(pricing, 'build_page') as build:
            for value in ['', '24052400000,', 'x', ','.join(str(i) for i in range(25))]:
                with self.assertRaises(HTTPException) as error:
                    pricing.pricing_history_batch(value)
                self.assertEqual(error.exception.status_code, 422)
            build.assert_not_called()

    def test_database_timeouts_are_opt_in_and_connections_close(self):
        import db
        settings = MagicMock()
        settings.db_parts.return_value = {'host':'example', 'port':3306, 'user':'test',
                                         'password':'test', 'database':'test'}
        settings.ca_path.return_value = None
        with patch.object(db, 'get_settings', return_value=settings), \
                patch('mysql.connector.connect') as connect:
            with db.db_conn():
                self.assertEqual(connect.call_args.kwargs['connection_timeout'], 20)
                self.assertNotIn('read_timeout', connect.call_args.kwargs)
            with self.assertRaises(ValueError):
                with db.db_conn(read_timeout=15, connection_timeout=5):
                    self.assertEqual(connect.call_args.kwargs['read_timeout'], 15)
                    self.assertEqual(connect.call_args.kwargs['connection_timeout'], 5)
                    raise ValueError('consumer failure')
            self.assertEqual(connect.return_value.close.call_count, 2)

    def test_new_oh_expires_prior_counts_but_preserves_counts_submitted_after_upload(self):
        tree = ast.parse(Path(__file__).with_name('quick_check_app.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'expire_true_stock_for_new_oh')
        env = {'_table_exists': lambda *args: True}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'quick_check_app.py', 'exec'), env)
        db = sqlite3.connect(':memory:'); db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        db.executescript('''
            CREATE TABLE ingest_file(file_id,upload_timestamp);
            INSERT INTO ingest_file VALUES(200,'2026-10-22T10:00:00');
            CREATE TABLE manual_true_stock(true_stock_id,family_id,override_status,
                anchor_on_hand_file_id,submitted_at,superseded_at,superseded_by_oh_file_id);
            INSERT INTO manual_true_stock VALUES
                (1,531,'ACTIVE',190,'2026-10-20T10:00:00',NULL,NULL),
                (2,532,'ACTIVE',190,'2026-10-22T11:00:00',NULL,NULL),
                (3,533,'ACTIVE',200,'2026-10-22T10:00:00',NULL,NULL);
            CREATE TABLE dumping_discrepancy_queue(source_true_stock_id,queue_status,resolved_at);
            INSERT INTO dumping_discrepancy_queue VALUES(1,'PENDING',NULL),(2,'PENDING',NULL);
        ''')
        class Cursor:
            def execute(self, query, args):
                self.result = db.execute(query.replace('%s','?').replace('CURRENT_TIMESTAMP(6)','CURRENT_TIMESTAMP'), args)
                self.rowcount = self.result.rowcount
            def fetchall(self):
                return [dict(r) for r in self.result.fetchall()]
        result = env['expire_true_stock_for_new_oh'](Cursor(), 200)
        self.assertEqual(result, {'true_stock_expired':1, 'dumping_rows_superseded':1})
        counts = [tuple(r) for r in db.execute('SELECT true_stock_id,override_status,superseded_by_oh_file_id FROM manual_true_stock ORDER BY 1')]
        self.assertEqual(counts, [(1,'SUPERSEDED_BY_OH_UPLOAD',200),(2,'ACTIVE',None),(3,'ACTIVE',None)])
        self.assertEqual(env['expire_true_stock_for_new_oh'](Cursor(), 200)['true_stock_expired'], 0)


if __name__ == '__main__':
    unittest.main()
