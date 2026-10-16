import sys, types, unittest
from pathlib import Path
from datetime import date
from decimal import Decimal as D
sys.path.insert(0,str(Path(__file__).parent))
# Pure calculation tests do not require database or production credentials.
fastapi=types.ModuleType('fastapi')
class Router:
    def get(self,*a,**k): return lambda f:f
fastapi.APIRouter=Router
fastapi.HTTPException=Exception
enc=types.ModuleType('fastapi.encoders'); enc.jsonable_encoder=lambda x:x
sys.modules['fastapi']=fastapi; sys.modules['fastapi.encoders']=enc
from mobile_pricing import cost_for_day, day_evidence, group_key
import mobile_pricing as module
from unittest.mock import patch
DAY=date(2026,10,8)
ROW={'upc_id':1,'family_id':5,'ean_upc':'24012300000','selling_uom':'LB','base_uom':'LB','base_qty_per_selling_unit':1}
def obs(source,value,unit='LB',day=DAY):return {'business_date':day,'source_type':source,'cost_value':value,'cost_uom':unit}
COSTS=[obs('MOVEMENT_RECEIPT_VALUATION',6)]
CONFIG=[{'date':date(2026,10,1),'price':D('9.99'),'type':'REG'}]
def sales(q,s,types=None):return {'sold_quantity':q,'sales_amount':s,'price_types':types or {'REG':{'sold_quantity':q,'sales_amount':s}}}
class EvidenceTests(unittest.TestCase):
    def test_tony_confirmed_categories(self):
        frozen=['1363489','3400489','1351010','3467050','1341262','1341274','1343317','3461000','3400200','3401200','1341020','1341138','1342207']
        fresh=['1361760','3500527','3540032']
        for code in frozen: self.assertEqual(module.confirmed_category(code),'FROZEN')
        for code in fresh: self.assertEqual(module.confirmed_category(code),'FRESH')
        self.assertIsNone(module.confirmed_category('1361120'))
        self.assertIsNone(module.confirmed_category('unknown'))
    def test_confirmed_family_wins_without_receipts(self):
        coverage=types.ModuleType('data_coverage');coverage.source_data_days=lambda *a,**kw:[]
        clock=types.ModuleType('business_clock');clock.completed_through_date=lambda:DAY
        semantics=types.ModuleType('receipt_semantics');semantics.physical_receipt_stage_rows=lambda rows:(rows,'TEST')
        rows=[{**ROW,'family_id':1,'main_article_number':'1341138','product_class':'FRESH'}, {**ROW,'family_id':2,'main_article_number':'1361760','product_class':'FROZEN'}]
        with patch.dict(sys.modules,{'data_coverage':coverage,'business_clock':clock,'receipt_semantics':semantics}), patch.object(module,'_category_cache',(0,{})):
            result=module.category_index(None,rows,DAY)
            self.assertEqual(result[1]['category'],'FROZEN')
            self.assertEqual(result[2]['category'],'FRESH')

    def evidence(self,o=None,config=CONFIG,costs=COSTS):
        return day_evidence(ROW,DAY,o,config,costs,cost_for_day(ROW,costs,DAY))
    def test_cold_start_empty_cache_is_not_valid(self):
        coverage=types.ModuleType('data_coverage');coverage.source_data_days=lambda *a,**kw:[]
        clock=types.ModuleType('business_clock');clock.completed_through_date=lambda:DAY
        semantics=types.ModuleType('receipt_semantics');semantics.physical_receipt_stage_rows=lambda rows:(rows,'TEST')
        row={**ROW,'family_description':'ATLANTIC SALMON STEAK'}
        with patch.dict(sys.modules,{'data_coverage':coverage,'business_clock':clock,'receipt_semantics':semantics}), patch.object(module.time,'monotonic',return_value=100), patch.object(module,'_category_cache',(0,{})):
            result=module.category_index(None,[row],DAY)
            self.assertEqual(result[5]['category'],'FRESH')
    def test_new_family_invalidates_complete_category_index(self):
        coverage=types.ModuleType('data_coverage');coverage.source_data_days=lambda *a,**kw:[]
        clock=types.ModuleType('business_clock');clock.completed_through_date=lambda:DAY
        semantics=types.ModuleType('receipt_semantics');semantics.physical_receipt_stage_rows=lambda rows:(rows,'TEST')
        row={**ROW,'family_id':6,'family_description':'LIVE LOBSTER'}
        with patch.dict(sys.modules,{'data_coverage':coverage,'business_clock':clock,'receipt_semantics':semantics}), patch.object(module.time,'monotonic',return_value=101), patch.object(module,'_category_cache',(100,{5:{'category':'FRESH'}})):
            self.assertEqual(module.category_index(None,[row],DAY)[6]['category'],'LIVE')
    def test_cost_authority_and_conversion(self):
        sources=[obs('ON_HAND_EXPLICIT_COST_FALLBACK',2),obs('LIVE_FRESH_SUGGESTION_OFFICIAL_COST',4),obs('MOVEMENT_RECEIPT_VALUATION',6)]
        self.assertEqual(cost_for_day(ROW,sources,DAY)['value'],6)
        self.assertEqual(cost_for_day(ROW,sources[:2],DAY)['value'],4)
        self.assertIsNone(cost_for_day(ROW,[obs('MOVEMENT_RECEIPT_VALUATION',5,'CASE')],DAY))
        r={**ROW,'selling_uom':'PAC','base_qty_per_selling_unit':2}
        self.assertEqual(cost_for_day(r,sources,DAY)['value'],12)
    def test_no_future_cost(self):
        self.assertIsNone(cost_for_day(ROW,[obs('MOVEMENT_RECEIPT_VALUATION',6,day=date(2026,10,9))],DAY))
    def test_supported_zero_sales_count_when_exposure_known(self):
        e=self.evidence(); self.assertTrue(e['valid']); self.assertEqual(e['qty'],0); self.assertEqual(e['gp'],0)
    def test_missing_price_exposure_is_not_zero(self):
        e=self.evidence(config=[]); self.assertFalse(e['valid']); self.assertIsNone(e['qty'])
    def test_upload_day_cannot_invent_zero_exposure(self):
        e=self.evidence(config=[{**CONFIG[0],'date':DAY}]); self.assertFalse(e['valid'])
    def test_positive_revenue_zero_qty_excluded(self):
        e=self.evidence(sales(0,D('12.82'))); self.assertFalse(e['valid']); self.assertIsNone(e['price']); self.assertIsNone(e['gp'])
    def test_mixed_price_day_not_pooled(self):
        e=self.evidence(sales(2,18,{'REG':{'sold_quantity':1,'sales_amount':10},'TPR':{'sold_quantity':1,'sales_amount':8}})); self.assertFalse(e['valid'])
    def test_historical_gp_and_current_cost_normalization(self):
        e=day_evidence(ROW,DAY,sales(10,100),CONFIG,COSTS,{'value':D(7)})
        self.assertEqual(e['gp'],40); self.assertEqual(e['normalized_gp'],30)
    def test_missing_cost_never_zero_cost(self):
        e=self.evidence(sales(10,100),costs=[]); self.assertFalse(e['valid']); self.assertIsNone(e['gp'])
    def test_pair_requires_same_family_and_code(self):
        self.assertEqual(group_key(ROW),group_key({**ROW,'ean_upc':'24912300000'}))
        self.assertNotEqual(group_key(ROW),group_key({**ROW,'ean_upc':'24999900000'}))
        self.assertNotEqual(group_key(ROW),group_key({**ROW,'family_id':6}))
        self.assertNotEqual(group_key(ROW),group_key({**ROW,'ean_upc':'24512300000'}))
    def test_returns_are_not_price_trials(self):
        self.assertFalse(self.evidence(sales(-1,-10))['valid'])
if __name__=='__main__':unittest.main()

