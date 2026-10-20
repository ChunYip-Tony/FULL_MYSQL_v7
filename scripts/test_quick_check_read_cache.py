"""Regression tests for transaction-local Quick Check input caching."""
import ast
import pathlib
import re
import unittest

source = pathlib.Path(__file__).resolve().parents[1] / 'server' / 'phase3.py'
node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == '_QuickCheckReadCache')
namespace = {'re': re}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
Cache = namespace['_QuickCheckReadCache']

class Cursor:
    def __init__(self):
        self.calls = []
        self.rows = []
        self.value = 12
    def execute(self, sql, args=None):
        self.calls.append((sql, args))
        self.rows = [{'v': self.value}]
        return 1
    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows
    def fetchone(self):
        return self.rows.pop(0) if self.rows else None
    def executemany(self, sql, args):
        return self.execute(sql, args)

SQL = 'SELECT v FROM article_cost_observation WHERE family_id=%s'
class Tests(unittest.TestCase):
    def test_repeated_family_reads_and_mutation_isolation(self):
        raw = Cursor(); cur = Cache(raw)
        for _ in range(1000):
            cur.execute(SQL, (1,)); row = cur.fetchone()
            self.assertEqual(row['v'], 12); row['v'] = 999
            self.assertIsNone(cur.fetchone())
        self.assertEqual(len(raw.calls), 1)
        self.assertEqual(cur.hits, 999)
        cur.execute(SQL, (2,)); self.assertEqual(cur.fetchall(), [{'v': 12}])
        self.assertEqual(len(raw.calls), 2)
    def test_qa_and_joined_mutable_tables_never_cached(self):
        raw = Cursor(); cur = Cache(raw)
        for sql in ['SELECT v FROM qa_phase3_issue', 'SELECT v FROM article_cost_observation JOIN quick_check_current USING(family_id)', 'SELECT v FROM ingest_file FOR UPDATE']:
            for _ in range(2):
                cur.execute(sql); cur.fetchall()
        self.assertEqual(len(raw.calls), 6)
    def test_source_write_invalidates_but_serving_write_does_not(self):
        raw = Cursor(); cur = Cache(raw)
        cur.execute(SQL, (1,)); cur.fetchall()
        cur.execute('INSERT INTO quick_check_current VALUES(1)')
        cur.execute(SQL, (1,)); self.assertEqual(cur.fetchone()['v'], 12)
        self.assertEqual(cur.hits, 1)
        cur.execute('UPDATE article_cost_observation SET cost_amount=20')
        raw.value = 20
        cur.execute(SQL, (1,)); self.assertEqual(cur.fetchone()['v'], 20)
    def test_bounded_and_fresh_per_rebuild(self):
        raw = Cursor(); cur = Cache(raw, max_entries=2)
        for family in range(10):
            cur.execute(SQL, (family,)); cur.fetchall()
        self.assertEqual(len(cur._cache), 2)
        raw.value = 30
        fresh = Cache(raw); fresh.execute(SQL, (9,))
        self.assertEqual(fresh.fetchone()['v'], 30)
    def test_preserves_fetch_sequence_on_hits(self):
        raw = Cursor(); cur = Cache(raw)
        for _ in range(2):
            cur.execute(SQL, (1,))
            self.assertEqual(cur.fetchall(), [{'v': 12}])
            self.assertEqual(cur.fetchall(), [])

if __name__ == '__main__':
    unittest.main()
