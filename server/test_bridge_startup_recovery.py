"""A worker restart must not republish a still-current verified snapshot."""
import ast
from datetime import datetime, timedelta
from pathlib import Path
import unittest
from price_history_analysis import HISTORY_CONTRACT


def load_guard():
    tree=ast.parse(Path(__file__).with_name('worker.py').read_text())
    node=next(x for x in tree.body if isinstance(x,ast.FunctionDef)
              and x.name=='_startup_bridge_already_verified')
    scope={'API_PIPELINE':'FULLMYSQL_SECURE_API','HISTORY_CONTRACT':HISTORY_CONTRACT}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'worker.py','exec'),scope)
    return scope[node.name]


class Cursor:
    def __init__(self,row):
        self.row=row
        self.args=None
    def execute(self,sql,args):
        self.args=args
        self.sql=sql
    def fetchone(self):
        return self.row


class StartupPublishTest(unittest.TestCase):
    def setUp(self):
        self.guard=load_guard()
        stamp=datetime(2026,10,10,2,44,31)
        self.verified={'processing_status':'COMPLETED','publish_status':'PASS',
                       'history_contract':HISTORY_CONTRACT,
                       'readback_pass':'true','snapshot_updated_at':stamp,
                       'completed_at':stamp+timedelta(seconds=90)}

    def test_verified_current_snapshot_is_reused(self):
        cur=Cursor(self.verified)
        self.assertTrue(self.guard(cur,38))
        self.assertEqual(cur.args,(38,38,'FULLMYSQL_SECURE_API'))

    def test_changed_canonical_snapshot_requires_publish(self):
        row={**self.verified,'snapshot_updated_at':self.verified['completed_at']+timedelta(seconds=1)}
        self.assertFalse(self.guard(Cursor(row),38))

    def test_later_interrupted_attempt_is_not_hidden(self):
        for status in ('FAILED','STARTED','QUEUED'):
            with self.subTest(status=status):
                self.assertFalse(self.guard(Cursor({**self.verified,'processing_status':status}),38))

    def test_pass_without_successful_readback_is_not_reused(self):
        for readback in ('false',None):
            self.assertFalse(self.guard(Cursor({**self.verified,'readback_pass':readback}),38))

    def test_missing_or_failed_evidence_requires_recovery(self):
        for row in (None,{**self.verified,'publish_status':'FAILED'},
                    {**self.verified,'snapshot_updated_at':None}):
            with self.subTest(row=row):
                self.assertFalse(self.guard(Cursor(row),38))


if __name__=='__main__':
    unittest.main()

