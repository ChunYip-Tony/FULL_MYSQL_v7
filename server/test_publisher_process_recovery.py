import ast
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest


class PublisherProcessRecoveryTests(unittest.TestCase):
    def test_stopped_worker_requeues_publisher_without_reimport(self):
        class Cursor:
            rowcount = 1
            def execute(self, sql, params):
                self.sql, self.params = sql, params
            def close(self): pass
        cur = Cursor()
        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self): return cur
            def commit(self): pass
        tree = ast.parse(Path(__file__).with_name('single_service.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'requeue_interrupted_pipeline_runs')
        scope = dict(json=json, datetime=datetime, timezone=timezone,
                     db_conn=Connection, API_VERSION='test', API_PIPELINE='pipeline',
                     log=lambda message: None)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'single_service.py', 'exec'), scope)
        self.assertEqual(scope[fn.name]('WORKER_PROCESS_EXIT'), 1)
        self.assertIn("'CHATGPT_SHEET_PUBLISH'", cur.sql)
        self.assertIn("processing_status IN ('STARTED','PAUSE_REQUESTED')", cur.sql)
        self.assertIn("SET processing_status='QUEUED'", cur.sql)
        self.assertEqual(json.loads(cur.params[0])['recovery_reason'], 'WORKER_PROCESS_EXIT')


if __name__ == '__main__': unittest.main()
