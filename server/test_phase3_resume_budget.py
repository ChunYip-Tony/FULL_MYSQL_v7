"""Exercise the real endpoint body without importing the production app."""
import ast
import json
from pathlib import Path
import unittest


class HTTPError(Exception):
    def __init__(self, status, detail):
        self.status_code, self.detail = status, detail


class DB:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.statements = []
        self.lastrowid = 123
        self.rolled_back = False

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def cursor(self, **kwargs): return self
    def execute(self, sql, args=()): self.statements.append((sql, args))
    def fetchone(self): return next(self.answers)
    def commit(self): pass
    def rollback(self): self.rolled_back = True
    def close(self): pass


def endpoint(db):
    source = ast.parse(Path(__file__).with_name('api.py').read_text())
    fn = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'web_upload_resume_phase3')
    fn.decorator_list = []
    scope = dict(db_conn=lambda: db, Request=object, HTTPException=HTTPError,
                 _browser_upload_guard=lambda r: None, API_PIPELINE='pipeline',
                 VERSION='test-version', WEB_UPLOAD_DEVICE='browser', json=json)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'api.py', 'exec'), scope)
    return scope[fn.name]


class ResumeBudgetTest(unittest.TestCase):
    def test_active_run_is_reused(self):
        db = DB([{'processing_status': 'PHASE2C_READY'}, None,
                 {'pipeline_run_id': 12, 'processing_status': 'STARTED'}])
        result = endpoint(db)(38, None)
        self.assertTrue(result['already_active'])
        self.assertEqual(result['pipeline_run_id'], 12)
        self.assertFalse(any('INSERT INTO' in sql for sql, _ in db.statements))

    def test_exhausted_version_cannot_create_another_run(self):
        db = DB([{'processing_status': 'PHASE2C_READY'}, None, None, {'next_run': 14}, {'attempts': 3}])
        with self.assertRaises(HTTPError) as caught:
            endpoint(db)(38, None)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.detail['reason'], 'PHASE3_RECOVERY_EXHAUSTED')
        self.assertTrue(db.rolled_back)
        self.assertFalse(any('INSERT INTO' in sql for sql, _ in db.statements))
        self.assertIn((38, 'pipeline', 'test-version'), [args for _, args in db.statements])

    def test_unexhausted_version_can_resume_without_ingest(self):
        db = DB([{'processing_status': 'PHASE2C_READY'}, None, None, {'next_run': 14}, {'attempts': 0}])
        result = endpoint(db)(38, None)
        self.assertEqual(result['pipeline_run_id'], 123)
        writes = [sql for sql, _ in db.statements if 'INSERT INTO' in sql]
        self.assertEqual(len(writes), 1)
        self.assertIn('INSERT INTO pipeline_run', writes[0])


if __name__ == '__main__': unittest.main()
