"""Optional dashboard builds wait for ingest AND durable Google readback."""
import ast
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


def scope(connect,time=None):
    tree=ast.parse(Path(__file__).with_name('pipeline_priority.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
    ns={'db_conn':connect,'time':time}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'pipeline_priority.py','exec'),ns)
    return ns


class PriorityTests(unittest.TestCase):
    def pending(self,stage,status):
        class Cursor:
            def execute(self,sql):self.sql=sql
            def fetchone(self):return (int("'"+stage+"'" in self.sql and status in {'QUEUED','STARTED','PAUSE_REQUESTED'}),)
            def close(self):pass
        @contextmanager
        def connect():yield SimpleNamespace(cursor=lambda:Cursor())
        return scope(connect)['pipeline_pending']()

    def test_queued_and_running_google_work_defers_dashboard_build(self):
        for state in ('QUEUED','STARTED','PAUSE_REQUESTED'):
            self.assertTrue(self.pending('CHATGPT_SHEET_PUBLISH',state))

    def test_completed_google_work_releases_dashboard_build(self):
        for state in ('COMPLETED','FAILED'):
            self.assertFalse(self.pending('CHATGPT_SHEET_PUBLISH',state))
        self.assertFalse(self.pending('APP_READY','STARTED'))

    def test_existing_source_priority_is_preserved(self):
        for stage in ('POST_RAW_PIPELINE','PHASE3_RERUN'):
            self.assertTrue(self.pending(stage,'STARTED'))

    def test_waiter_resumes_after_publication_finishes(self):
        states=iter([True,True,False]);waits=[]
        ns=scope(None,SimpleNamespace(sleep=waits.append))
        ns['pipeline_pending']=lambda:next(states)
        ns['wait_for_pipeline_idle']()
        self.assertEqual(waits,[30,30])


if __name__=='__main__':unittest.main()
