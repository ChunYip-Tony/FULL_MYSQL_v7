import sys, types, unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch
from family_daily_gp import family_result, build_family_daily

class FamilyGPTests(unittest.TestCase):
 def test_tilapia_same_date_family_cost(self):
  r=family_result('540.10',{'status':'READY','quantity':'135.364'},{'status':'RESOLVED','cost_per_selling_unit':'1.75'})
  self.assertEqual(r['gp'],Decimal('303.21300'))
 def test_missing_movement_not_zero(self):
  self.assertIsNone(family_result(100,{'status':'UNAVAILABLE'},{'status':'RESOLVED','cost_per_selling_unit':1})['gp'])
 def test_incompatible_cost_stays_null(self):
  self.assertIsNone(family_result(100,{'status':'READY','quantity':10},{'status':'UOM_MISMATCH'})['gp'])
 def test_movement_without_pos_needs_review(self):
  self.assertEqual(family_result(0,{'status':'READY','quantity':10},{'status':'RESOLVED','cost_per_selling_unit':1})['status'],'SALES_MOVEMENT_REVIEW')
 def fixture(self,movement_day=True,confirmed=False):
  day=date(2026,10,18);cur=Mock();cur.fetchall.return_value=[{'family_id':43,'base_uom_code':'LB','q':Decimal('135.364')}]
  rows=[{'family_id':43,'main_article_number':'1342107','family_description':'Tilapia','ean_upc':upc,'selling_uom':'LB','latest_daily_sales_dollars':sales,'latest_daily_pos_reported_qty':qty} for upc,sales,qty in [('24053300000','261.61',66),('24953300000','278.49',70)]]
  if confirmed:
   rows=[dict(rows[0],ean_upc='24929400000',latest_daily_sales_dollars='9.82',latest_daily_pos_reported_qty=2)];cur.fetchall.return_value=[]
  coverage=types.ModuleType('data_coverage');coverage.source_data_days=lambda *a,**kw:[{'date':day if movement_day else date(2026,10,17),'file_id':174}]
  bridge=types.ModuleType('chatgpt_sheet_bridge');bridge._family_cost_as_of=lambda *a:{'status':'RESOLVED','cost_per_selling_unit':'1.60' if confirmed else '1.75'}
  runtime=types.ModuleType('webapp_v2_runtime');runtime._ordering_family_movement_metrics=Mock(return_value={'status':'UNAVAILABLE'})
  with patch.dict(sys.modules,{'data_coverage':coverage,'chatgpt_sheet_bridge':bridge,'webapp_v2_runtime':runtime}):
   return build_family_daily(cur,rows,{'business_date':day,'sales_dollars':'9.82' if confirmed else '540.10'},64)
 def test_sibling_movement_counted_once(self):
  matrix,summary=self.fixture();self.assertEqual(len(matrix),2);self.assertEqual(matrix[1][6],Decimal('135.364'));self.assertEqual(summary['gp'],Decimal('303.21300'));self.assertEqual(matrix[1][19],'CONSISTENT_WITH_ROUNDING')
 def test_other_date_cannot_substitute(self):
  matrix,summary=self.fixture(False);self.assertIsNone(summary['gp']);self.assertEqual(summary['status'],'PARTIAL_FAMILY_MVT')
 def test_confirmed_pos_fallback_keeps_movement_unmatched(self):
  matrix,summary=self.fixture(confirmed=True)
  self.assertEqual(summary['gp'],Decimal('6.62'))
  self.assertEqual(summary['status'],'COMPLETE_WITH_CONFIRMED_POS')
  self.assertEqual(matrix[1][14],'RESOLVED_USER_CONFIRMED_POS')
  self.assertEqual(matrix[1][19],'POS_USED_251_252_UNMATCHED')
  self.assertEqual(matrix[1][-3:], [Decimal('2'),'LB','USER_CONFIRMED_POS_LB_251_252_UNMATCHED'])
  self.assertIsNone(matrix[1][6])
 def test_confirmation_is_exact_upc_and_dated(self):
  from family_daily_gp import confirmed_pos_lb
  row={'ean_upc':'24929400000','selling_uom':'LB','latest_daily_pos_reported_qty':2}
  self.assertEqual(confirmed_pos_lb(row,'2026-10-18'),2)
  self.assertIsNone(confirmed_pos_lb(row,'2026-10-17'))
  self.assertIsNone(confirmed_pos_lb(dict(row,ean_upc='24029400000'),'2026-10-18'))
if __name__=='__main__':unittest.main()
