"""Lifecycle tests using an isolated SQL database, never production inventory."""
import ast
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).parent
tree = ast.parse((ROOT/'quick_check_app.py').read_text())
names = {'_latest_on_hand_file_id', 'expire_true_stock_for_new_oh', '_refresh_expired_true_stock'}
quick = types.ModuleType('quick_check_app')
quick._table_exists = lambda cur, name: True
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), 'stock-lifecycle', 'exec'), quick.__dict__)
db_stub = types.ModuleType('db')
db_stub.db_conn = lambda: None
spec = importlib.util.spec_from_file_location('stock_records_test_target', ROOT/'data_center_records.py')
records = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'db': db_stub, 'quick_check_app': quick}):
    spec.loader.exec_module(records)


class Cursor:
    def __init__(self, conn): self.raw = conn.cursor()
    def execute(self, sql, params=()):
        sql = sql.replace('%s', '?').replace('CURRENT_TIMESTAMP(6)', 'CURRENT_TIMESTAMP').replace(' FOR UPDATE', '')
        self.raw.execute(sql, params)
        return self
    def fetchone(self):
        row = self.raw.fetchone()
        return dict(row) if row is not None else None
    def fetchall(self): return [dict(r) for r in self.raw.fetchall()]
    @property
    def rowcount(self): return self.raw.rowcount
    def close(self): self.raw.close()


class Connection:
    def __init__(self, raw): self.raw = raw
    def cursor(self, **kwargs): return Cursor(self.raw)
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def start_transaction(self): self.raw.execute('BEGIN')
    def __enter__(self): return self
    def __exit__(self, *args): pass


class StockRecordTests(unittest.TestCase):
    def setUp(self):
        self.raw = sqlite3.connect(':memory:')
        self.raw.row_factory = sqlite3.Row
        self.raw.create_function('JSON_UNQUOTE', 1, lambda value: value)
        self.raw.executescript('''
            CREATE TABLE ingest_file(file_id INTEGER PRIMARY KEY,original_filename TEXT,upload_timestamp TEXT,coverage_start_date TEXT,coverage_end_date TEXT,source_type TEXT,processing_status TEXT,error_count INTEGER,duplicate_of_file_id INTEGER,batch_id INTEGER);
            CREATE TABLE inventory_observation(file_id INTEGER,source_type TEXT);
            CREATE TABLE product_family(family_id INTEGER PRIMARY KEY,family_description TEXT);
            CREATE TABLE manual_true_stock(true_stock_id INTEGER PRIMARY KEY,family_id INTEGER,main_article_number TEXT,scope_type TEXT,article_number TEXT,ean_upc TEXT,true_stock_quantity NUMERIC,uom_code TEXT,system_oh_quantity NUMERIC,discrepancy_quantity NUMERIC,override_status TEXT,submitted_at TEXT,count_note TEXT,submitted_by TEXT,superseded_at TEXT,superseded_by_oh_file_id INTEGER,anchor_on_hand_file_id INTEGER);
            CREATE TABLE dumping_discrepancy_queue(discrepancy_id INTEGER PRIMARY KEY,source_true_stock_id INTEGER,queue_status TEXT,resolved_at TEXT,resolved_by TEXT,resolution_note TEXT);
            CREATE TABLE true_stock_record_clearance(true_stock_id INTEGER PRIMARY KEY,cleared_at TEXT DEFAULT CURRENT_TIMESTAMP,cleared_by TEXT,clear_note TEXT);
            CREATE TABLE pipeline_run(pipeline_run_id INTEGER PRIMARY KEY,batch_id INTEGER,processing_status TEXT,completed_at TEXT,detail_json TEXT,pipeline_name TEXT,stage_name TEXT);
            INSERT INTO ingest_file VALUES(1,'oh-old.xls','2026-09-28 10:00:00',NULL,'2026-09-28','on_hand','INGESTED',0,NULL,1);
            INSERT INTO inventory_observation VALUES(1,'ON_HAND');
            INSERT INTO product_family VALUES(1,'Seafood item');
            INSERT INTO manual_true_stock VALUES(1,1,'1361677','FAMILY',NULL,NULL,0,'LB',10,10,'ACTIVE','2026-10-04 10:00:00',NULL,'TEST',NULL,NULL,1);
            INSERT INTO manual_true_stock VALUES(2,1,'1361678','FAMILY',NULL,NULL,40,'LB',50,10,'ACTIVE','2026-10-04 11:00:00',NULL,'TEST',NULL,NULL,1);
            INSERT INTO manual_true_stock VALUES(3,1,'1361679','FAMILY',NULL,NULL,60,'LB',50,-10,'ACTIVE','2026-10-04 12:00:00',NULL,'TEST',NULL,NULL,1);
            INSERT INTO dumping_discrepancy_queue VALUES(1,1,'PENDING',NULL,NULL,NULL);
            INSERT INTO dumping_discrepancy_queue VALUES(2,2,'PENDING',NULL,NULL,NULL);
        ''')
        self.raw.commit()
        self.patch_db = patch.object(records, 'db_conn', lambda: Connection(self.raw))
        self.patch_schema = patch.object(records, '_ensure_clearance_table', lambda cur: None)
        self.patch_db.start(); self.patch_schema.start()
    def tearDown(self):
        self.patch_schema.stop(); self.patch_db.stop(); self.raw.close()
    def test_all_manual_counts_included_and_zero_search_is_explicit(self):
        result = records.list_stock_records()
        self.assertEqual([r['true_stock_id'] for r in result['rows']], [3, 2, 1])
        self.assertEqual(result['counts']['pending'], 3)
        self.assertEqual(result['counts']['zero_pending'], 1)
        self.assertEqual(result['counts']['dumping_pending'], 2)
        self.assertEqual(records.list_stock_records(kind='zero')['rows'][0]['true_stock_id'], 1)
        self.assertEqual(records.list_stock_records(query='1361679')['rows'][0]['record_status'], 'RECORDED')
    def test_clear_is_idempotent_and_does_not_change_stock(self):
        result = records.clear_stock_record(1, 'TEST', 'Dumping completed')
        self.assertTrue(result['effective_oh_retained'])
        row = self.raw.execute('SELECT true_stock_quantity,override_status FROM manual_true_stock WHERE true_stock_id=1').fetchone()
        self.assertEqual(tuple(row), (0, 'ACTIVE'))
        self.assertEqual(self.raw.execute('SELECT queue_status FROM dumping_discrepancy_queue WHERE discrepancy_id=1').fetchone()[0], 'RESOLVED')
        self.assertEqual(records.clear_stock_record(1, 'TEST')['status'], 'ALREADY_CLEARED')
        self.assertEqual(records.list_stock_records()['counts']['pending'], 2)
        self.assertEqual(records.list_stock_records(view='history')['rows'][0]['record_status'], 'CLEARED')
    def test_record_without_dumping_can_also_be_cleared(self):
        records.clear_stock_record(3, 'TEST')
        self.assertEqual(records.list_stock_records()['counts']['pending'], 2)
        self.assertEqual(self.raw.execute('SELECT COUNT(*) FROM dumping_discrepancy_queue').fetchone()[0], 2)
    def test_new_oh_clears_old_records_but_keeps_newer_counts(self):
        records.clear_stock_record(3, 'TEST')
        self.raw.execute("INSERT INTO ingest_file VALUES(2,'oh-new.xls','2026-10-10 08:00:00',NULL,'2026-10-10','on_hand','INGESTED',0,NULL,2)")
        self.raw.execute("INSERT INTO inventory_observation VALUES(2,'ON_HAND')")
        self.raw.execute("INSERT INTO manual_true_stock VALUES(4,1,'1361680','FAMILY',NULL,NULL,25,'LB',30,5,'ACTIVE','2026-10-10 09:00:00',NULL,'TEST',NULL,NULL,1)")
        self.raw.commit()
        result = records.list_stock_records()
        self.assertEqual([r['true_stock_id'] for r in result['rows']], [4])
        self.assertEqual(result['latest_oh']['file_id'], 2)
        history = records.list_stock_records(view='history')['rows']
        self.assertEqual({r['record_status'] for r in history}, {'REPLACED_BY_OH'})
        self.assertEqual(self.raw.execute("SELECT COUNT(*) FROM dumping_discrepancy_queue WHERE queue_status='PENDING'").fetchone()[0], 0)
        with self.assertRaisesRegex(ValueError, 'ALREADY_REPLACED'):
            records.clear_stock_record(1, 'TEST')
    def test_incomplete_failed_duplicate_and_empty_oh_do_not_clear(self):
        cases = [('UPLOADING',0,None,True), ('INGESTED',1,None,True), ('INGESTED',0,1,True), ('INGESTED',0,None,False)]
        for status, errors, duplicate, observed in cases:
            self.raw.execute('DELETE FROM ingest_file WHERE file_id=2')
            self.raw.execute('DELETE FROM inventory_observation WHERE file_id=2')
            self.raw.execute("INSERT INTO ingest_file VALUES(2,'bad.xls','2026-10-10 08:00:00',NULL,'2026-10-10','on_hand',?,?,?,2)", (status, errors, duplicate))
            if observed: self.raw.execute("INSERT INTO inventory_observation VALUES(2,'ON_HAND')")
            self.raw.commit()
            self.assertEqual(records.list_stock_records()['counts']['pending'], 3)
    def test_pagination_preserves_all_records(self):
        first = records.list_stock_records(limit=2)
        second = records.list_stock_records(limit=2, before=first['next_before'])
        self.assertEqual([r['true_stock_id'] for r in first['rows']+second['rows']], [3,2,1])
        self.assertIsNone(second['next_before'])
    def test_publish_requires_completed_pass_and_boolean_readback(self):
        good = {'publish_result': {'status':'PASS','readback':{'pass':True,'source_status':{'POS_Data_Through':'2026-10-08'}},'analysis_ready_row_count':357}}
        for run, status, detail in [(100,'COMPLETED',good),(101,'FAILED',{}),(102,'COMPLETED',{'publish_result':{'status':'PASS','readback':{'pass':'true'}}})]:
            self.raw.execute("INSERT INTO pipeline_run VALUES(?,39,?,'2026-10-10 07:00:00',?,'TEST','CHATGPT_SHEET_PUBLISH')", (run,status,json.dumps(detail)))
        self.raw.commit()
        result = records.latest_verified_publish('TEST')
        self.assertEqual(result['published']['publish_run_id'],100)
        self.assertTrue(result['published']['verified'])
        self.assertFalse(result['latest_attempt']['verified'])
    def test_failure_rolls_back_clearance_and_keeps_record(self):
        self.raw.execute("CREATE TRIGGER refuse_clear BEFORE INSERT ON true_stock_record_clearance BEGIN SELECT RAISE(FAIL,'storage unavailable'); END")
        self.raw.commit()
        with self.assertRaises(sqlite3.IntegrityError): records.clear_stock_record(1, 'TEST')
        self.assertEqual(self.raw.execute('SELECT queue_status FROM dumping_discrepancy_queue WHERE discrepancy_id=1').fetchone()[0], 'PENDING')
        self.assertEqual(records.list_stock_records()['counts']['pending'],3)


if __name__ == '__main__': unittest.main()
