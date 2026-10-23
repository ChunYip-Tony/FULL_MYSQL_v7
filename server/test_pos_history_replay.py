"""Routine uploads preserve committed POS history while replaying late files."""
from __future__ import annotations
import ast
import unittest
from datetime import date,datetime,timedelta
from pathlib import Path


class Cursor:
    def __init__(self,kinds=('movement',),watermark=datetime(2026,10,23,20)):
        self.kinds=kinds;self.watermark=watermark;self.calls=[];self.rows=[]
        self.files=[{'batch_id':74,'file_id':197,'upload_timestamp':datetime(2026,10,23,19)},
                    {'batch_id':77,'file_id':199,'upload_timestamp':datetime(2026,10,23,21)}]
    def execute(self,sql,args=None):
        self.calls.append((sql,args))
        if 'SELECT DISTINCT source_type' in sql:self.rows=[{'source_type':k} for k in self.kinds]
        elif 'SELECT pr.started_at' in sql:self.rows=[{'started_at':self.watermark}] if self.watermark else []
        elif 'FROM ingest_file' in sql:
            self.rows=[r for r in self.files if 'upload_timestamp>=' not in sql or r['upload_timestamp']>=args[-1]]
        else:raise AssertionError(sql)
    def fetchall(self):return self.rows
    def fetchone(self):return self.rows[0] if self.rows else None


class ReplayTests(unittest.TestCase):
    def run_replay(self,cur,force=False):
        parsed=[]
        def process(cursor,batch,row,**kwargs):parsed.append(row['file_id']);return 10
        source=Path(__file__).with_name('phase3.py');tree=ast.parse(source.read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_pos_history_replay_watermark','_backfill_recent_pos_history'}]
        nodes.insert(0,ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0))
        scope=dict(completed_through_date=lambda:date(2026,10,22),timedelta=timedelta,
                   article_manual_pos_alias_index=lambda c:{},_process_sales=process)
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(source),'exec'),scope)
        result=scope['_backfill_recent_pos_history'](cur,exclude_batch_id=78,force=force)
        return parsed,result

    def test_movement_reuses_committed_pos_but_includes_late_upload(self):
        parsed,result=self.run_replay(Cursor())
        self.assertEqual(parsed,[199]);self.assertEqual(result['files_reprocessed'],1)
        self.assertEqual(result['upc_qty_source'],'POS_ONLY')
        self.assertFalse(result['movement_used_as_upc_qty'])

    def test_manual_identity_update_replays_historical_raw(self):
        cur=Cursor(kinds=('article_manual',));parsed,result=self.run_replay(cur)
        self.assertEqual(parsed,[197,199]);self.assertIsNone(result['replay_watermark'])

    def test_no_successful_contract_checkpoint_replays_all(self):
        parsed,_=self.run_replay(Cursor(watermark=None));self.assertEqual(parsed,[197,199])

    def test_explicit_repair_can_force_full_replay(self):
        parsed,result=self.run_replay(Cursor(),force=True)
        self.assertEqual(parsed,[197,199]);self.assertIsNone(result['replay_watermark'])

    def test_boundary_timestamp_is_replayed_conservatively(self):
        parsed,_=self.run_replay(Cursor(watermark=datetime(2026,10,23,19)))
        self.assertEqual(parsed,[197,199])

    def test_checkpoint_requires_committed_matching_parser(self):
        cur=Cursor();self.run_replay(cur)
        query=next(sql for sql,_ in cur.calls if 'SELECT pr.started_at' in sql)
        self.assertIn("pr.processing_status='COMPLETED'",query)
        self.assertIn('POS_UPC_V547',query)
        self.assertIn("p3.result_status IN ('QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS')",query)


if __name__=='__main__':unittest.main()
