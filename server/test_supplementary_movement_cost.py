import sys,types,unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from supplementary_movement_cost import movement_cost_rows,eligible,SOURCE

class Cursor:
    def __init__(self,rows):self.rows=rows
    def execute(self,sql,args):self.sql,self.args=sql,args
    def fetchall(self):return self.rows

class SupplementTests(unittest.TestCase):
    def test_canonical_file_and_returns_are_net_and_quantity_not_exposed(self):
        coverage=types.ModuleType('data_coverage');coverage.source_data_days=lambda *a,**k:[{'date':date(2026,10,18),'file_id':2}]
        cur=Cursor([{'article_number':'1330347','posting_date':date(2026,10,18),'file_id':1,'base_uom_code':'LB','qty':-2,'amount':-100}, {'article_number':'1330347','posting_date':date(2026,10,18),'file_id':2,'base_uom_code':'LB','qty':Decimal('-2.028'),'amount':Decimal('-3.45')}])
        with patch.dict(sys.modules,{'data_coverage':coverage}):out=movement_cost_rows(cur,[{'article_number':'1330347'}],date(2026,10,20))
        cost=out['1330347'][0];self.assertEqual(cost['cost_value'],Decimal('3.45')/Decimal('2.028'));self.assertEqual(cost['source_type'],SOURCE)
        self.assertNotIn('qty',cost);self.assertIn("movement_type IN ('251','252')",cur.sql)
        self.assertTrue(eligible({'article_number':'1330347'},cost));self.assertFalse(eligible({'article_number':'9999999'},cost))
    def test_zero_or_return_only_and_mixed_units_cannot_supply_cost(self):
        coverage=types.ModuleType('data_coverage');coverage.source_data_days=lambda *a,**k:[{'date':date(2026,10,18),'file_id':2}]
        template={'article_number':'1','posting_date':date(2026,10,18),'file_id':2,'base_uom_code':'LB'}
        for values in [[dict(template,qty=0,amount=1)],[dict(template,qty=2,amount=4)],[dict(template,qty=-2,amount=-4),dict(template,qty=-1,amount=-4,base_uom_code='EA')]]:
            with patch.dict(sys.modules,{'data_coverage':coverage}):self.assertFalse(movement_cost_rows(Cursor(values),[{'article_number':'1'}],date(2026,10,20)).get('1'))

if __name__=='__main__':unittest.main()
