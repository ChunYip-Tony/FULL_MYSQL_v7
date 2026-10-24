"""Real MySQL 8.4 integration tests against a throwaway, explicitly selected DB.

No production db/config import or credentials. CI supplies FINDER_TEST_MYSQL_*.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import mysql.connector
from fastapi import HTTPException
from finder_department_store import MySQLStateStore, validate_state
from test_finder_department_store import state


@unittest.skipUnless(os.environ.get('FINDER_TEST_MYSQL_HOST'), 'Explicit disposable MySQL test service required')
class MySQLIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database = os.environ['FINDER_TEST_MYSQL_DATABASE']
        if not re.fullmatch(r'finder_test_[a-z0-9_]+', database):
            raise RuntimeError('Integration tests require a disposable finder_test_* database')
        cls.config = dict(host=os.environ['FINDER_TEST_MYSQL_HOST'],
                          port=int(os.environ.get('FINDER_TEST_MYSQL_PORT', '3306')),
                          user=os.environ['FINDER_TEST_MYSQL_USER'],
                          password=os.environ['FINDER_TEST_MYSQL_PASSWORD'],
                          database=database, autocommit=False, connection_timeout=5,
                          charset='utf8mb4')
        with cls.connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()[0]
            if not version.startswith('8.4.'):
                raise RuntimeError('MySQL 8.4 is required for this integration gate')
            schema = Path(__file__).with_name('finder_department_schema.sql').read_text()
            schema = '\n'.join(line for line in schema.splitlines() if not line.lstrip().startswith('--'))
            for statement in schema.split(';'):
                if statement.strip():
                    cursor.execute(statement)
            conn.commit()
            cursor.close()

    @classmethod
    @contextmanager
    def connection(cls):
        conn = mysql.connector.connect(**cls.config)
        try:
            yield conn
        finally:
            conn.close()

    def setUp(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM finder_department_head')
            cur.execute('DELETE FROM finder_department_state')
            conn.commit()
            cur.close()
        self.store = MySQLStateStore(self.connection)

    def save(self, value, expected=None, department='meat'):
        raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
        return self.store.put(department, raw, validate_state(raw, department), expected)

    def query(self, sql, args=()):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, args)
            rows = cur.fetchall()
            cur.close()
            return rows

    def test_exact_bytes_and_sql_views_preserve_evidence_grain(self):
        value = state(posEvents=[{'upc': '000012345678', 'date': '2026-10-22', 'units': 2}],
                      movements=[{'article': '1366580', 'date': '2026-10-22', 'quantity': 40}],
                      unknownHistory=[{'missing': None, 'zero': 0}])
        digest, duplicate = self.save(value)
        raw, actual = self.store.get('meat')
        self.assertFalse(duplicate)
        self.assertEqual(raw, json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode())
        self.assertEqual(actual, digest)
        self.assertEqual(self.query('SELECT upc,item_name FROM finder_upc_profiles'), [('000012345678', '海鮮')])
        self.assertEqual(self.query('SELECT upc,source_date FROM finder_pos_records'), [('000012345678', '2026-10-22')])
        self.assertEqual(self.query('SELECT article,source_date FROM finder_family_movements'), [('1366580', '2026-10-22')])
        self.assertEqual(json.loads(self.query('SELECT document FROM finder_department_current')[0][0]), value)

    def test_two_simultaneous_writers_have_one_commit_and_one_conflict(self):
        initial, _ = self.save(state())
        barrier = threading.Barrier(2)
        def writer(revision):
            barrier.wait(timeout=5)
            try:
                self.save(state(revision), initial)
                return 200
            except HTTPException as error:
                return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(writer, ['r2', 'r3'])), [200, 409])
        self.assertEqual(self.query('SELECT generation FROM finder_department_head'), [(2,)])
        self.assertEqual(self.query('SELECT COUNT(*) FROM finder_department_state'), [(2,)])

    def test_lost_reply_replay_and_department_isolation(self):
        digest, _ = self.save(state())
        self.assertEqual(self.save(state()), (digest, True))
        self.save(state('produce-r1'), department='produce')
        self.assertEqual(json.loads(self.store.get('meat')[0])['revision'], 'r1')
        self.assertEqual(json.loads(self.store.get('produce')[0])['revision'], 'produce-r1')
        self.assertEqual(self.query('SELECT generation FROM finder_department_head ORDER BY department'), [(1,), (1,)])

    def test_failed_readback_rolls_back_and_retains_prior_head(self):
        previous, _ = self.save(state())
        next_state = state('r2')
        raw = json.dumps(next_state, ensure_ascii=False, separators=(',', ':')).encode()
        digest = hashlib.sha256(raw).hexdigest()
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO finder_department_state '
                        '(department,sha256,source_revision,payload,byte_count,record_counts) '
                        'VALUES(%s,%s,%s,%s,%s,%s)', ('meat', digest, 'r2', b'{}', 2, '{}'))
            conn.commit()
            cur.close()
        with self.assertRaises(HTTPException) as raised:
            self.save(next_state, previous)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(self.store.get('meat')[1], previous)
        self.assertEqual(self.query('SELECT generation FROM finder_department_head'), [(1,)])

    def test_invalid_mysql_json_never_moves_head(self):
        previous, _ = self.save(state())
        value = state('bad', invalidSurrogate='\ud800')
        raw = json.dumps(value, ensure_ascii=True).encode()
        with self.assertRaises(HTTPException) as raised:
            self.store.put('meat', raw, validate_state(raw, 'meat'), previous)
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(self.store.get('meat')[1], previous)


if __name__ == '__main__':
    unittest.main()
