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
 def fixture(self,movement_day=True):
  day=date(2026,10,18);cur=Mock();cur.fetchall.return_value=[{'family_id':43,'base_uom_code':'LB','q':Decimal('135.364')}]
  rows=[{'family_id':43,'main_article_number':'1342107','family_description':'Tilapia','ean_upc':upc,'selling_uom':'LB','latest_daily_sales_dollars':sales,'latest_daily_pos_reported_qty':qty} for upc,sales,qty in [('24053300000','261.61',66),('24953300000','278.49',70)]]
  coverage=types.ModuleType('data_coverage');coverage.source_data_days=lambda *a,**kw:[{'date':day if movement_day else date(2026,10,17),'file_id':174}]
  bridge=types.ModuleType('chatgpt_sheet_bridge');bridge._family_cost_as_of=lambda *a:{'status':'RESOLVED','cost_per_selling_unit':'1.75'}
  runtime=types.ModuleType('webapp_v2_runtime');runtime._ordering_family_movement_metrics=Mock(return_value={'status':'UNAVAILABLE'})
  with patch.dict(sys.modules,{'data_coverage':coverage,'chatgpt_sheet_bridge':bridge,'webapp_v2_runtime':runtime}):
   return build_family_daily(cur,rows,{'business_date':day,'sales_dollars':'540.10'},64)
 def test_sibling_movement_counted_once(self):
  matrix,summary=self.fixture();self.assertEqual(len(matrix),2);self.assertEqual(matrix[1][6],Decimal('135.364'));self.assertEqual(summary['gp'],Decimal('303.21300'));self.assertEqual(matrix[1][19],'CONSISTENT_WITH_ROUNDING')
 def test_other_date_cannot_substitute(self):
  matrix,summary=self.fixture(False);self.assertIsNone(summary['gp']);self.assertEqual(summary['status'],'PARTIAL_FAMILY_MVT')
if __name__=='__main__':unittest.main()
