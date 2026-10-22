import unittest
from datetime import date
from decimal import Decimal
from inventory_gp_adjustments import ledger

class AdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.dt=date(2026,10,20)
        self.days=[{'date':self.dt,'file_id':9}]
        self.identities={'1540604':{'family':'1362604','upcs':{'24060400000'}},
                         '1362604':{'family':'1362604','upcs':{'24060400000','24033000000'}}}
    def row(self, raw=1, mvt='551', value='-9', **kw):
        return dict(file_id=9,raw_id=raw,posting_date=self.dt,movement_type=mvt,
                    article_number='1540604',amount_local_currency=value,
                    base_quantity='-1' if mvt in ('551','702') else '1',**kw)
    def run_rows(self,rows):
        return ledger(rows,self.days,self.dt,self.dt,'Seafood','test',self.identities)
    def test_repeated_upload_and_query_rows_count_once(self):
        row=self.row();old={**row,'file_id':8}
        data,cov=self.run_rows([row,row,old])
        self.assertEqual(len(data),2);self.assertEqual(data[1][6],Decimal('-9'))
        self.assertEqual(cov[1][4],'COMPLETE')
    def test_identical_legitimate_lines_preserved(self):
        data,_=self.run_rows([self.row(),self.row(raw=2)])
        self.assertEqual(sum(r[6] for r in data[1:]),Decimal('-18'))
    def test_reversal_and_count_signs(self):
        data,_=self.run_rows([self.row(),self.row(2,'552','9'),
                             self.row(3,'701','12'),self.row(4,'702','-3')])
        self.assertEqual(sum(r[6] for r in data[1:]),Decimal('9'))
    def test_family_not_allocated_to_upcs(self):
        row={**self.row(),'article_number':'1362604'}
        data,_=self.run_rows([row]);self.assertEqual(data[1][4],'1362604')
        self.assertEqual(data[1][5],'')
    def test_unique_selling_article_and_no_cross_department(self):
        data,_=self.run_rows([self.row(),self.row(2,cost_center='MEAT-LAS VEGAS')])
        self.assertEqual(len(data),2);self.assertEqual(data[1][5],'24060400000')
    def test_missing_amount_not_zero(self):
        data,cov=self.run_rows([{**self.row(),'amount_local_currency':None}])
        self.assertIsNone(data[1][6]);self.assertEqual(cov[1][4],'PARTIAL')
    def test_sign_conflict_blocked(self):
        data,cov=self.run_rows([self.row(value='9')])
        self.assertNotEqual(data[1][11],'VERIFIED');self.assertEqual(cov[1][4],'PARTIAL')
    def test_missing_date_not_zero_but_verified_zero_day_is_complete(self):
        _,cov=ledger([],[],self.dt,self.dt,'Seafood','test',{})
        self.assertEqual(cov[1][4],'PARTIAL')
        _,cov=self.run_rows([]);self.assertEqual(cov[1][4],'COMPLETE')

class ReadbackTests(unittest.TestCase):
    def test_numeric_text_and_empty_cells(self):
        from inventory_gp_adjustments import verify_readback
        rows,cov=ledger([],[],date(2026,10,20),date(2026,10,20),'Seafood','test',{})
        def reader(a1):
            matrix=cov if 'COVERAGE' in a1 else rows
            return [[str(v) for v in r] for r in matrix]
        self.assertTrue(verify_readback(reader,rows,cov)['pass'])
    def test_truncated_ledger_rejected(self):
        from inventory_gp_adjustments import verify_readback
        fixture=AdjustmentTests();fixture.setUp()
        rows,cov=fixture.run_rows([fixture.row()])
        with self.assertRaisesRegex(RuntimeError,'ledger'):
            verify_readback(lambda a1:rows[:1],rows,cov)

if __name__=='__main__': unittest.main()
