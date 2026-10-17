import ast
import sys
import types
import unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch

# Isolate database I/O while exercising the real transaction and SQL write scope.
with patch.dict(sys.modules, {'db': types.SimpleNamespace(db_conn=None)}):
    import selling_status as status

class Cursor:
    def __init__(self, conn): self.conn=conn; self.sql=''; self.lastrowid=42
    def execute(self, sql, params=None):
        self.sql=sql; self.conn.calls.append((sql,params))
        if self.conn.fail_audit and 'INSERT INTO qa_manual_resolution' in sql: raise RuntimeError('audit unavailable')
    def fetchone(self):
        if 'FROM information_schema.tables' in self.sql: return {'exists':1} if self.conn.table_exists else None
        if 'FROM pipeline_run' in self.sql: return {'busy':1} if self.conn.busy else None
        if 'FROM selling_upc WHERE' in self.sql: return self.conn.identity
        return None
    def fetchall(self): return self.conn.rows
    def close(self): pass
class Connection:
    def __init__(self):
        self.calls=[];self.table_exists=True;self.rows=[];self.busy=False;self.fail_audit=False
        self.identity={'upc_id':10,'ean_upc':'23523700000','record_status':'ACTIVE'}
        self.commits=0;self.rollbacks=0;self.starts=0
    def cursor(self, **kw): return Cursor(self)
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1
    def start_transaction(self): self.starts+=1
    def __enter__(self): return self
    def __exit__(self,*a): pass

class SellingStatusTests(unittest.TestCase):
    def setUp(self):
        self.conn=Connection(); self.refreshed=[]
        self.qa=types.SimpleNamespace(_ensure_resolution_table=lambda c:None,_latest_phase3_batch=lambda c:57)
        self.phase=types.SimpleNamespace(refresh_quick_check_subset=lambda *a,**kw:self.refreshed.append(kw))
    def apply(self, **kw):
        data=dict(ean_upc='23523700000',selling_status='INACTIVE',note='Tony confirms not currently sold',actor='PUBLIC-WEB',confirm='APPLY_SELLING_STATUS');data.update(kw)
        with patch.object(status,'db_conn',lambda:self.conn),patch.dict(sys.modules,{'qa_resolution':self.qa,'phase3':self.phase}):
            return status.set_selling_status(**data)
    def test_inactive_preserves_history_and_targets_only_confirmed_upc(self):
        result=self.apply()
        self.assertEqual(result['status'],'APPLIED');self.assertTrue(result['rules']['historical_sales_preserved'])
        updates=[(q,p) for q,p in self.conn.calls if q.lstrip().startswith(('UPDATE','INSERT INTO'))]
        self.assertEqual(len(updates),4)
        self.assertTrue(all(any(t in q for t in ['manual_upc_selling_status','quick_check_current','qa_phase3_issue','qa_manual_resolution']) for q,p in updates))
        self.assertIn("quick_check_status='HISTORICAL_ONLY'",updates[1][0]);self.assertEqual(updates[1][1],('23523700000',))
        self.assertEqual(self.conn.rollbacks,0);self.assertEqual(self.conn.starts,1)
    def test_reactivate_rechecks_only_target_and_does_not_force_ready(self):
        self.apply(selling_status='ACTIVE')
        self.assertEqual(self.refreshed,[{'upcs':['23523700000']}])
        self.assertFalse(any("quick_check_status='READY'" in q for q,p in self.conn.calls))
    def test_busy_pipeline_blocks_business_writes(self):
        self.conn.busy=True
        with self.assertRaisesRegex(RuntimeError,'PIPELINE_BUSY'):self.apply()
        self.assertEqual(self.conn.starts,0)
        self.assertFalse(any(q.lstrip().startswith(('INSERT','UPDATE')) for q,p in self.conn.calls))
    def test_audit_failure_rolls_back_status(self):
        self.conn.fail_audit=True
        with self.assertRaisesRegex(RuntimeError,'audit unavailable'):self.apply()
        self.assertEqual(self.conn.rollbacks,1)
    def test_rejects_invalid_unconfirmed_or_missing_upc(self):
        for kw in [dict(confirm=''),dict(ean_upc=''),dict(selling_status='RETIRED'),dict(note='')]:
            with self.assertRaises(ValueError):self.apply(**kw)
        self.conn.identity=None
        with self.assertRaisesRegex(ValueError,'UPC_NOT_FOUND'):self.apply()
    def test_no_new_table_is_required_for_old_deployments_reads(self):
        self.conn.table_exists=False
        self.assertEqual(status.confirmed_inactive_upcs(Cursor(self.conn)),set())
    def test_exact_upc_scope_and_reactivation_persisted(self):
        self.conn.rows=[dict(ean_upc='23523700000',selling_status='INACTIVE'),dict(ean_upc='24523700000',selling_status='ACTIVE')]
        self.assertEqual(status.confirmed_inactive_upcs(Cursor(self.conn)),{'23523700000'})

class RebuildScopeTests(unittest.TestCase):
    def setUp(self):
        tree=ast.parse(Path(__file__).with_name('phase3.py').read_text())
        names={'_mapped_current_activity_scope','_active_selling_evidence_for_unmapped'}
        subset=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
        self.env={'Any':object,'Decimal':Decimal,'completed_through_date':lambda:None,
                  'confirmed_inactive_upcs':lambda cur:{'23523700000'},
                  'source_data_days':lambda *a,**kw:[{}],
                  '_sales_daily_aggregates':lambda *a,**kw:{'2026-10-01':{'qty':Decimal(3)}}}
        exec(compile(subset,'phase3_scope','exec'),self.env)
    def test_positive_old_sales_do_not_reopen_confirmed_inactive_qa(self):
        f=self.env['_mapped_current_activity_scope']
        self.assertEqual(f({'qty':3},inactive=True),('HISTORICAL_ONLY','USER_CONFIRMED_NOT_CURRENTLY_SOLD'))
        self.assertEqual(f({'qty':3}),('ACTIVE_SELLING','POS_LATEST_28_VALID_DATA_DAYS'))
    def test_unmapped_guard_respects_exact_status_but_keeps_sales_evidence(self):
        f=self.env['_active_selling_evidence_for_unmapped']
        inactive=f(None,'23523700000',57,inactive_upcs={'23523700000'})
        self.assertEqual(inactive['activity_scope'],'HISTORICAL_ONLY');self.assertEqual(inactive['recent_pos_qty_28_valid_days'],'3')
        self.assertEqual(f(None,'24523700000',57,inactive_upcs={'23523700000'})['activity_scope'],'ACTIVE_SELLING')

if __name__=='__main__':unittest.main()
