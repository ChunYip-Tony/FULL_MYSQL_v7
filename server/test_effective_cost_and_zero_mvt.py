import ast, unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
src=ast.parse(Path(__file__).with_name('mobile_pricing.py').read_text())
names={'num','selling_unit','effective_cost_as_of','cost_for_day'}
body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='COST_ORDER' for t in n.targets)]
ns={'Decimal':Decimal};exec(compile(ast.Module(body=body,type_ignores=[]),'mobile_pricing.py','exec'),ns)
class EffectiveCostTests(unittest.TestCase):
 def setUp(self):
  self.today=date(2026,10,12);self.row={'selling_uom':'LB','base_uom':'LB'}
  self.obs=[{'source_type':s,'cost_value':Decimal(v),'cost_uom':'LB','business_date':date(2026,10,d)} for s,v,d in [('MOVEMENT_RECEIPT_VALUATION','4',1),('MOVEMENT_RECEIPT_VALUATION','5',2),('ON_HAND_EXPLICIT_COST_FALLBACK','6',10),('FROZEN_INVENTORY_OFFICIAL_COST','7',11)]]
 def test_receipt_oh_report_priority_and_latest_within_source(self):
  f=ns['cost_for_day'];self.assertEqual(f(self.row,self.obs,self.today)['value'],5)
  self.assertEqual(f(self.row,self.obs[2:],self.today)['value'],6)
  self.assertEqual(f(self.row,self.obs[3:],self.today)['value'],7)
 def test_historical_cost_does_not_use_future_observations(self):
  self.assertEqual(ns['cost_for_day'](self.row,self.obs,date(2026,10,1))['value'],4)
 def test_base_cost_visible_without_unverified_conversion(self):
  row={'selling_uom':'PACK','base_uom':'LB'}
  self.assertIsNone(ns['cost_for_day'](row,self.obs,self.today))
  self.assertEqual(ns['effective_cost_as_of'](self.obs,self.today)['uom'],'LB')
 def test_confirmed_prefix_uom_and_nonprefix_needs_explicit_unit(self):
  self.assertEqual(ns['selling_unit']({'ean_upc':'24029800000'}),'LB')
  self.assertEqual(ns['selling_unit']({'ean_upc':'75339373655'}),'')
  self.assertEqual(ns['selling_unit']({'ean_upc':'75339373655','selling_uom':'PACK'}),'PACK')
 def test_pack_alias_is_the_same_unit(self):
  self.assertEqual(ns['cost_for_day']({'selling_uom':'PACK','base_uom':'PAC'},[{'source_type':'ON_HAND_EXPLICIT_COST_FALLBACK','cost_value':Decimal('9'),'cost_uom':'PAC','business_date':self.today}],self.today)['value'],9)
 def test_complete_zero_movement_keeps_unit_and_missing_coverage_does_not_become_zero(self):
  from inventory_sales import restore_completed_zero_window
  import copy
  m={'seven':{'basis':'NO_251_252_ROWS_IN_WINDOW','supportedDays':['1','2','3','4','5','6','7'],'quantity':0,'days':0,'receipt':{'quantity':None}},'fourteen':{'status':'READY','uom':'PAC','supportedDays':['0','1','2','3','4','5','6','7']}}
  other=copy.deepcopy(m);restore_completed_zero_window(m,True)
  self.assertEqual(m['seven']['days'],7);self.assertEqual(m['seven']['uom'],'PAC');self.assertEqual(m['seven']['receipt']['quantity'],0)
  other['seven']['basis']='NO_CANONICAL_MVT_DAYS';restore_completed_zero_window(other,True)
  self.assertEqual(other['seven']['days'],0)
if __name__=='__main__':unittest.main()
