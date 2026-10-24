import ast
import sys
import types
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pricing_progress_candidates as module

TODAY = date(2026, 10, 24)
ROWS = [{'upc_id': 1, 'ean_upc': '24012300000'}, {'upc_id': 2, 'ean_upc': '24912300000'}]


class Cursor:
    def __init__(self, uploads):
        self.files = [{'file_id': i + 1, 'upload_timestamp': day} for i, (day, _) in enumerate(uploads)]
        self.observations = [dict(file_id=i + 1, upc_id=uid, ean_upc=ean, configured_price=price, price_type=kind)
                             for i, (_, rows) in enumerate(uploads) for uid, ean, price, kind in rows]
        self.queries = []
        self.offset = 0
        self.batches = 0

    def execute(self, sql, args=()):
        self.queries.append((sql, args))

    def fetchall(self):
        if len(self.queries) != 1:
            raise AssertionError('History must be streamed, never fetched all at once')
        return self.files

    def fetchmany(self, limit):
        assert limit <= 512
        self.batches += 1
        out = self.observations[self.offset:self.offset + limit]
        self.offset += len(out)
        return out


def ticket(price, kind='REG', uid=1, ean=None):
    return uid, ean or ROWS[uid - 1]['ean_upc'], price, kind


class CandidateTests(unittest.TestCase):
    def setUp(self):
        module._cache.clear()
        phase3 = types.ModuleType('phase3')
        phase3._price_list_upload_business_date = lambda value: value
        self.modules = patch.dict(sys.modules, {'phase3': phase3})
        self.modules.start()

    def tearDown(self):
        self.modules.stop()

    def read(self, uploads, through=TODAY - timedelta(days=2), rows=None):
        return module.progress_candidates(Cursor(uploads), rows or ROWS, TODAY, through)

    def test_same_price_uploads_do_not_restart_old_test(self):
        result = self.read([(date(2026, 10, 1), [ticket(8)]), (date(2026, 10, 10), [ticket(9)]),
                            (date(2026, 10, 23), [ticket(9)])])
        self.assertNotIn(1, result['REG'])

    def test_seventh_day_due_is_kept_eighth_day_is_not(self):
        for age in (7, 8):
            module._cache.clear()
            result = self.read([(date(2026, 10, 1), [ticket(8)]),
                                (TODAY - timedelta(days=age), [ticket(9)]), (date(2026, 10, 23), [ticket(9)])])
            self.assertEqual(1 in result['REG'], age == 7)

    def test_return_to_prior_price_starts_new_episode(self):
        result = self.read([(date(2026, 10, 1), [ticket(8)]), (date(2026, 10, 10), [ticket(9)]),
                            (date(2026, 10, 23), [ticket(8)])])
        self.assertIn(1, result['REG'])

    def test_first_unchanged_reg_is_not_a_test(self):
        self.assertNotIn(1, self.read([(date(2026, 10, 23), [ticket(9)])])['REG'])

    def test_tpr_and_sale_obey_same_upload_priority(self):
        for kinds, expected in [(['REG', 'TPR'], True), (['TPR', 'SALE'], False), (['TPR', 'IN STORE'], False)]:
            module._cache.clear()
            result = self.read([(date(2026, 10, 23), [ticket(9, kind) for kind in kinds])])
            self.assertEqual(1 in result['TPR'], expected)
            self.assertNotIn(1, result['REG'])

    def test_unknown_or_newer_pos_keeps_both_candidates(self):
        for uploads in [[], [(date(2026, 10, 20), [ticket(9, 'SALE')])]]:
            module._cache.clear()
            result = self.read(uploads)
            self.assertEqual(result, {'REG': {1, 2}, 'TPR': {1, 2}})

    def test_alias_identity_uses_unique_upc_without_losing_pair(self):
        result = self.read([(date(2026, 10, 23), [ticket(9, 'TPR', 999, '024012300000'), ticket(8, 'SALE', 2)])])
        self.assertEqual(result['TPR'], {1})

    def test_ambiguous_alias_remains_unknown(self):
        rows = [ROWS[0], {**ROWS[0], 'upc_id': 2}]
        result = self.read([(date(2026, 10, 23), [ticket(9, 'SALE', 999, '024012300000')])], rows=rows)
        self.assertEqual(result, {'REG': {1, 2}, 'TPR': {1, 2}})

    def test_same_day_files_follow_file_id_and_tpr_does_not_reset_reg(self):
        result = self.read([(date(2026, 10, 1), [ticket(8)]), (date(2026, 10, 20), [ticket(9)]),
                            (date(2026, 10, 21), [ticket(7, 'TPR')]), (date(2026, 10, 23), [ticket(9)])])
        self.assertIn(1, result['REG'])

    def test_index_streams_history_and_reuses_both_modes(self):
        cur = Cursor([(date(2026, 10, 23), [ticket(9, 'TPR')] * 2000)])
        first = module.progress_candidates(cur, ROWS, TODAY, date(2026, 10, 22))
        self.assertGreater(cur.batches, 3)
        repeated = Cursor([(date(2026, 10, 23), [])])
        self.assertIs(module.progress_candidates(repeated, ROWS, TODAY, date(2026, 10, 22)), first)
        self.assertEqual(len(repeated.queries), 1)

    def test_route_filters_groups_before_history_and_pagination(self):
        tree = ast.parse(Path(__file__).with_name('mobile_pricing.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_page')
        calls = {n.func.id: n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertLess(calls['progress_candidates'], calls['category_index'])
        self.assertLess(calls['progress_candidates'], calls['price_snapshots'])
        self.assertIn("group_key(r) in keys", ast.unparse(fn))


if __name__ == '__main__':
    unittest.main()
