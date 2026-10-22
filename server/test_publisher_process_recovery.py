import ast
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest


class PublisherProcessRecoveryTests(unittest.TestCase):
    def test_older_worker_leaves_newer_queued_and_started_jobs_alone(self):
        class Cursor:
            def __init__(self): self.calls=[]
            def execute(self, sql, params): self.calls.append(sql)
            def fetchall(self):
                return [{'pipeline_run_id':1984,'batch_id':71,
                         'stage_name':'CHATGPT_SHEET_PUBLISH',
                         'code_version':'7.0.534-next-release'}]
        tree=ast.parse(Path(__file__).with_name('worker.py').read_text())
        for name in ('_recover_stale_started','_supersede_incompatible_queued'):
            fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            scope=dict(API_PIPELINE='pipeline',API_VERSION='7.0.533-bounded-google-history',json=json)
            exec(compile(ast.Module(body=[fn],type_ignores=[]),'worker.py','exec'),scope)
            cur=Cursor()
            self.assertEqual(scope[name](cur),0)
            self.assertEqual(len(cur.calls),1)

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
