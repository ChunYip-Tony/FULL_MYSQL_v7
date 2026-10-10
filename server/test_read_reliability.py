import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from threading import Event, Barrier
import time
import unittest

from read_singleflight import ReadSingleFlight, ReadBusy
from runtime_health import runtime_health

ROOT = Path(__file__).parent


def extract(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


class SQLCursor:
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.create_function('REGEXP_REPLACE', 3, lambda value, pattern, repl: re.sub(pattern, repl, value))
        self.db.execute('CREATE TABLE sales_period_observation(file_id, period_start_date, period_end_date, temporal_grain, upc_id, ean_upc, price_type, sales_amount, sold_quantity)')
        self.db.execute('CREATE TABLE pos_daily_backfill_observation(source_file_id, business_date, upc_id, ean_upc, price_type, sales_amount, sold_quantity)')
        self.fetched = 0

    def execute(self, query, args):
        query = query.replace("TRIM(LEADING '0' FROM REGEXP_REPLACE(COALESCE(ean_upc,''),'[^0-9]',''))", "LTRIM(REGEXP_REPLACE(COALESCE(ean_upc,''),'[^0-9]',''),'0')")
        self.result = self.db.execute(query.replace('%s', '?'), args)

    def fetchall(self):
        rows = [dict(r) for r in self.result.fetchall()]
        self.fetched += len(rows)
        return rows


class ReadReliabilityTests(unittest.TestCase):
    def test_same_key_computes_once(self):
        gate = ReadSingleFlight()
        start, release = Event(), Event()
        together = Barrier(12)
        calls = []
        def build():
            calls.append(1); start.set(); release.wait(3)
            return {'quantity': 18}
        def request():
            together.wait(3)
            return gate.run('same', build)
        with ThreadPoolExecutor(max_workers=12) as pool:
            requests = [pool.submit(request) for _ in range(12)]
            self.assertTrue(start.wait(3))
            # All requests have crossed the barrier; let waiters join before
            # releasing the deliberately blocked database read.
            time.sleep(.05)
            release.set()
            self.assertEqual([r.result(3) for r in requests], [{'quantity':18}]*12)
        self.assertEqual(len(calls), 1)

    def test_distinct_reads_are_bounded_and_failure_releases_slot(self):
        gate = ReadSingleFlight(max_running=2)
        both = Barrier(3); release = Event()
        def build():
            both.wait(3); release.wait(3); return 1
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(gate.run, key, build) for key in ('a','b')]
            both.wait(3)
            with self.assertRaises(ReadBusy): gate.run('c', lambda: 99)
            release.set()
            self.assertEqual([f.result(3) for f in pending], [1,1])
        with self.assertRaises(ValueError): gate.run('failed', lambda: int('bad'))
        self.assertEqual(gate.run('failed', lambda: 7), 7)

    def test_waiter_timeout_does_not_cancel_original(self):
        gate = ReadSingleFlight(wait_seconds=.01)
        started, release = Event(), Event()
        def build(): started.set(); release.wait(3); return 18
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(gate.run, 'a', build)
            self.assertTrue(started.wait(3))
            with self.assertRaises(ReadBusy): gate.run('a', lambda: 0)
            release.set()
            self.assertEqual(first.result(3), 18)

    def test_pos_scope_preserves_lineage_aliases_dates_and_price_types(self):
        ns={'Any':object,'date':date,'Decimal':Decimal,'_d':lambda v: Decimal(str(v or 0))}
        extract('webapp_v2_runtime.py','_numeric_key',ns)
        batch=extract('webapp_v2_runtime.py','_batch_daily_sales_by_price_type',ns)
        cur=SQLCursor()
        rows=[{'upc_id':1,'ean_upc':'24012300000'}, {'upc_id':2,'ean_upc':'24912300000'},
              {'upc_id':3,'ean_upc':'123'}, {'upc_id':4,'ean_upc':'00123'}]
        observations=[(1,'24012300000','REG',10,2), (None,'00240-12300000','REG',15,3),
                      (2,'24012300000','TPR',4,1), (999,'24012300000','REG',5,1),
                      (None,'000123','REG',999,999), (None,'00123','SALE',6,2)]
        for obs in observations:
            cur.db.execute('INSERT INTO sales_period_observation VALUES (11,?,?,?, ?,?,?,?,?)', ('2026-10-08','2026-10-08','SINGLE_DATE',*obs))
        for index in range(4000):
            cur.db.execute('INSERT INTO sales_period_observation VALUES (11,?,?,?, ?,?,?,?,?)', ('2026-10-08','2026-10-08','SINGLE_DATE',10000+index,str(9000000+index),'REG',100,20))
        cur.db.execute("INSERT INTO sales_period_observation VALUES (99,'2026-10-08','2026-10-08','SINGLE_DATE',1,'24012300000','REG',999,999)")
        cur.db.execute("INSERT INTO pos_daily_backfill_observation VALUES (22,'2026-10-07',NULL,'024012300000','SALE',8,2)")
        cur.db.execute("INSERT INTO pos_daily_backfill_observation VALUES (23,'2026-10-07',1,'24012300000','SALE',999,999)")
        days=[{'date':'2026-10-08','file_id':11}, {'date':'2026-10-07','file_id':22,'coverage_kind':'DERIVED_PERIOD_RESIDUAL'}]
        actual=batch(cur,rows,days)
        self.assertEqual(actual[1]['2026-10-08']['sold_quantity'],6)
        self.assertEqual(actual[1]['2026-10-08']['sales_amount'],30)
        self.assertEqual(actual[2]['2026-10-08']['price_types']['TPR']['sold_quantity'],1)
        self.assertNotIn(3, actual)
        self.assertEqual(actual[4]['2026-10-08']['sold_quantity'],2)
        self.assertEqual(actual[1]['2026-10-07']['sold_quantity'],2)
        self.assertLessEqual(cur.fetched,6)

    def test_health_runs_while_sync_worker_is_busy(self):
        health=extract('api.py','healthz',{'Path':Path,'os':os,'json':json,'time':time,'VERSION':'test'})
        async def check():
            started,release=Event(),Event()
            with ThreadPoolExecutor(max_workers=1) as pool:
                def busy(): started.set();release.wait(3)
                task=pool.submit(busy)
                self.assertTrue(started.wait(3))
                try:
                    result=await asyncio.wait_for(health(), .5)
                    self.assertTrue(result['ok'])
                    self.assertEqual(result['runtime']['revision'],'bounded-pricing-reads-v1')
                finally: release.set()
                task.result(3)
        asyncio.run(check())

    def test_runtime_diagnostics_are_small_and_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'memory.current').write_text(str(40*1048576))
            (root/'memory.max').write_text(str(64*1048576))
            (root/'memory.events').write_text('oom 3\noom_kill 2\n')
            data=runtime_health(root)
            self.assertEqual(data['memory_mb'],40)
            self.assertEqual(data['memory_limit_mb'],64)
            self.assertEqual(data['oom_kills'],2)
            self.assertNotIn('peak_memory_mb',data)


if __name__=='__main__': unittest.main()
