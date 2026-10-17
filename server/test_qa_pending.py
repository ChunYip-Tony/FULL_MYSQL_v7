import sys,types,unittest
from unittest.mock import patch
from decimal import Decimal
with patch.dict(sys.modules,{'db':types.SimpleNamespace(db_conn=None)}):
    import qa_pending as q

class Cur:
    def __init__(self,c):self.c=c;self.sql=''
    def execute(self,sql,args=None):self.sql=sql;self.c.calls.append((sql,args))
    def fetchone(self):return {'id':1} if self.c.exists else None
    def fetchall(self):return self.c.rows
    def close(self):pass
class Conn:
    def __init__(self):self.calls=[];self.rows=[];self.exists=True;self.committed=False
    def cursor(self,**kw):return Cur(self)
    def commit(self):self.committed=True
    def __enter__(self):return self
    def __exit__(self,*args):pass

class PendingTests(unittest.TestCase):
    def setUp(self):self.c=Conn()
    def queue(self,**kw):
        body=dict(ean_upc='70041420617',article_number='1354810',selling_uom='EA',base_uom='LB',base_qty_per_selling_unit='2',note='Tony confirmed same main and 2LB pack',actor='PUBLIC-WEB',confirm='QUEUE_CONFIRMED_QA_FIX');body.update(kw)
        with patch.object(q,'db_conn',lambda:self.c):return q.queue_confirmation(**body)
    def test_queue_commits_only_confirmation_and_never_business_records(self):
        r=self.queue();self.assertEqual(r['status'],'QUEUED');self.assertEqual(r['article_number'],'1354810')
        writes=[(s,a) for s,a in self.c.calls if s.lstrip().startswith(('UPDATE','INSERT','DELETE'))]
        self.assertEqual(len(writes),1);self.assertIn('INSERT INTO qa_pending_confirmation',writes[0][0]);self.assertTrue(self.c.committed)
        self.assertEqual(writes[0][1][:5],('70041420617','1354810','EA','LB',Decimal(2)))
    def test_unconfirmed_bad_units_and_nonfinite_factor_rejected(self):
        for kw in [dict(confirm=''),dict(note=''),dict(base_qty_per_selling_unit='0'),dict(base_qty_per_selling_unit='NaN'),dict(base_qty_per_selling_unit='Infinity')]:
            with self.assertRaises(ValueError):self.queue(**kw)
        self.c.exists=False
        with self.assertRaisesRegex(ValueError,'UOM_NOT_FOUND'):self.queue()
    def test_current_read_required_for_late_queue_records(self):
        q.pending_confirmations(Cur(self.c),lock=True)
        self.assertTrue(self.c.calls[-1][0].endswith('FOR UPDATE'))
    def test_apply_uses_confirmed_authority_refreshes_target_and_audits(self):
        self.c.rows=[dict(ean_upc='70041420617',article_number='1354810',selling_uom='EA',base_uom='LB',base_qty_per_selling_unit=Decimal(2),note='confirmed',actor='PUBLIC-WEB')]
        refresh=[]
        mods={'manual_overrides':types.SimpleNamespace(apply_manual_upc_overrides=lambda c:{'held':[]}),
              'phase3':types.SimpleNamespace(relink_history=lambda c:None,refresh_quick_check_subset=lambda *a,**kw:refresh.append(kw)),
              'qa_resolution':types.SimpleNamespace(_ensure_resolution_table=lambda c:None)}
        with patch.dict(sys.modules,mods):r=q.apply_pending_confirmations(Cur(self.c),57)
        self.assertEqual(r['applied'],1);self.assertEqual(refresh,[{'upcs':['70041420617']}])
        self.assertIn('INSERT INTO qa_manual_resolution',self.c.calls[-2][0])
        self.assertIn("status='APPLIED'",self.c.calls[-1][0])
        self.assertFalse(self.c.committed) # caller owns the atomic rebuild commit
    def test_authority_failure_does_not_mark_applied(self):
        self.c.rows=[dict(ean_upc='70041420617',article_number='1354810',selling_uom='EA',base_uom='LB',base_qty_per_selling_unit=Decimal(2),note='confirmed',actor='PUBLIC-WEB')]
        mods={'manual_overrides':types.SimpleNamespace(apply_manual_upc_overrides=lambda c:{'held':[{'ean_upc':'70041420617'}]}),
              'phase3':types.SimpleNamespace(relink_history=lambda c:None,refresh_quick_check_subset=lambda *a,**kw:None),
              'qa_resolution':types.SimpleNamespace(_ensure_resolution_table=lambda c:None)}
        with patch.dict(sys.modules,mods),self.assertRaisesRegex(RuntimeError,'AUTHORITY_VALIDATION'):q.apply_pending_confirmations(Cur(self.c),57)
        self.assertFalse(any("status='APPLIED'" in s for s,a in self.c.calls))

if __name__=='__main__':unittest.main()
