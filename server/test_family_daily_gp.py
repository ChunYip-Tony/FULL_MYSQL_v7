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
  self.assertEqual(confirmed_pos_lb(row,'2026-10-17'),2)
  self.assertIsNone(confirmed_pos_lb(dict(row,ean_upc='99999999999'),'2026-10-18'))
 def test_tilapia_confirmation_covers_retained_history_only_exact_upcs(self):
  from family_daily_gp import confirmed_pos_lb
  for upc in ['24053300000','24953300000']:
   self.assertEqual(confirmed_pos_lb({'ean_upc':upc,'selling_uom':'LB','latest_daily_pos_reported_qty':66},'2026-09-01'),66)
  self.assertIsNone(confirmed_pos_lb({'ean_upc':'4883','selling_uom':'LB','latest_daily_pos_reported_qty':66},'2026-09-01'))
 def test_confirmed_lb_registry_excludes_pack_profiles(self):
  from family_daily_gp import CONFIRMED_POS_LB_UPCS,POS_LB_CONFIRMATIONS,confirmed_pos_lb
  self.assertEqual(len(CONFIRMED_POS_LB_UPCS),243)
  for upc in ['4298','4917','4918']:
   self.assertEqual(confirmed_pos_lb({'ean_upc':upc,'selling_uom':'LB','latest_daily_pos_reported_qty':2},'2026-09-01'),2)
  for upc in POS_LB_CONFIRMATIONS['exceptions']:
   self.assertNotIn(upc,CONFIRMED_POS_LB_UPCS)
   self.assertIsNone(confirmed_pos_lb({'ean_upc':upc,'selling_uom':'LB','latest_daily_pos_reported_qty':2},'2026-09-01'))
 def test_zero_quantity_positive_sales_not_confirmed(self):
  from family_daily_gp import confirmed_pos_lb
  self.assertIsNone(confirmed_pos_lb({'ean_upc':'24053300000','selling_uom':'LB','latest_daily_pos_reported_qty':0,'latest_daily_sales_dollars':10},'2026-10-18'))
 def test_egg_yolk_aliases_are_pack_without_changing_family_lb_cost(self):
  from family_daily_gp import apply_confirmed_selling_profile
  for upc in ['695892380548','6958923805483']:
   r=apply_confirmed_selling_profile({'ean_upc':upc,'selling_uom':'LB'})
   self.assertEqual(r['selling_uom'],'PACK');self.assertEqual(r['base_qty_per_selling_unit'],Decimal('2.2'))
   self.assertEqual(r['canonical_upc'],'6958923805483')
   family=apply_confirmed_selling_profile({'ean_upc':upc,'selling_uom':'LB','base_qty_per_selling_unit':1,'cost_scope':'FAMILY_MOVEMENT_UNIT'})
   self.assertEqual(family['selling_uom'],'LB');self.assertEqual(family['base_qty_per_selling_unit'],1)
 def test_confirmed_pack_cost_and_current_gp_are_per_pack(self):
  from family_daily_gp import apply_confirmed_selling_profile
  r=apply_confirmed_selling_profile({'ean_upc':'695892380546','selling_uom':'LB','current_cost_per_base_uom':'4','current_cost_per_selling_unit':'4','current_price':'12','current_oh':22,'current_oh_uom':'LB','upc_velocity_7d':1})
  self.assertEqual(r['selling_uom'],'PACK');self.assertEqual(r['current_cost_per_selling_unit'],Decimal('8.8'));self.assertEqual(r['dos'],Decimal('10'))
  self.assertEqual(apply_confirmed_selling_profile(r)['current_cost_per_selling_unit'],Decimal('8.8'))
 def test_scallop_ea_aliases_are_one_lb_each(self):
  from family_daily_gp import apply_confirmed_selling_profile
  for upc in ['823180600','8231806002']:
   r=apply_confirmed_selling_profile({'ean_upc':upc,'selling_uom':'EA','current_cost_per_base_uom':'15.833333'})
   self.assertEqual(r['selling_uom'],'EA');self.assertEqual(r['base_qty_per_selling_unit'],Decimal('1'));self.assertEqual(r['current_cost_per_selling_unit'],Decimal('15.833333'))
   self.assertEqual(r['canonical_upc'],'8231806002')
if __name__=='__main__':unittest.main()
