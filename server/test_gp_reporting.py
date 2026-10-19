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
if __name__=='__main__':unittest.main()
