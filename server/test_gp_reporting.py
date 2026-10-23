import ast,unittest
from pathlib import Path
from decimal import Decimal
from collections import defaultdict,Counter

def function(file,name,ns):
 tree=ast.parse(Path(__file__).with_name(file).read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),file,'exec'),ns);return ns[name]
class ReportingTests(unittest.TestCase):
 def test_positive_sales_zero_quantity_is_active(self):
  fn=function('phase3.py','_mapped_current_activity_scope',{'Any':object,'Decimal':Decimal})
  self.assertEqual(fn({'sales':'11.74','qty':0})[0],'ACTIVE_SELLING')
  self.assertEqual(fn({'sales':0,'qty':0})[0],'HISTORICAL_ONLY')
  self.assertEqual(fn({'sales':10,'qty':0},inactive=True)[0],'HISTORICAL_ONLY')
 def test_sold_historical_family_stays_in_reconciliation(self):
  fn=function('chatgpt_sheet_bridge.py','_build_family',{'Any':object,'defaultdict':defaultdict,'Counter':Counter,'Decimal':Decimal})
  r={'family_id':1050,'quick_check_status':'HISTORICAL_ONLY','latest_daily_sales_dollars':'11.74','ean_upc':'24570200000'}
  self.assertEqual(len(fn([r])),2)
  self.assertEqual(len(fn([dict(r,latest_daily_sales_dollars=0)])),1)
 def test_mussel_shared_receipt_cost_preserves_uom(self):
  from unittest.mock import Mock
  from datetime import date
  fn=function('chatgpt_sheet_bridge.py','_family_cost_as_of',{'Any':object,'Decimal':Decimal,'date':date,'REJECTED_RECEIPT_SQL':"TRUE",'_norm_uom':lambda x:str(x).upper() if x else None})
  cur=Mock();cur.fetchone.side_effect=[{'family_id':354},{'cost_per_base_uom':'4.79166667','base_uom':'LB','source_type':'MOVEMENT_RECEIPT_VALUATION','business_date':date(2026,10,13)}]
  r=fn(cur,{'family_id':583,'main_article_number':'3400136','selling_uom':'LB','base_uom':'LB','base_qty_per_selling_unit':1},date(2026,10,18))
  self.assertEqual(r['cost_per_selling_unit'],Decimal('4.79166667'))
  self.assertEqual(cur.execute.call_args.args[1],(354,date(2026,10,18)))
  self.assertIn('SHARED_1348021',r['source'])
if __name__=='__main__':unittest.main()

