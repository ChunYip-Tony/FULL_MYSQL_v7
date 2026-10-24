import unittest
from price_history_analysis import HEADERS, rebuild_retained_analysis

class HeldReplacementTests(unittest.TestCase):
 def build(self, tables=None, file_id=179):
  tables=tables or {k:[v[:]] for k,v in HEADERS.items()}
  member={'upc':'24053300000','name':'Tilapia','uom':'LB',
    'cost':{'value':1.75,'uom':'LB','source':'MOVEMENT_RECEIPT_VALUATION','date':'2026-10-13'},
    'current':{'price':3.99,'type':'REG'},
    'priceHistory':[{'date':'2026-10-19','file_id':159,'price':3.99,'type':'REG'}],
    'days':[{'date':'2026-10-20','sales':39.9,'qty':10,'price':3.99,'type':'REG','quantityBasis':'POS_QTY_WEIGHT','valid':True},
            {'date':'2026-10-21','sales':79.8,'qty':20,'price':3.99,'type':'REG','quantityBasis':'POS_QTY_WEIGHT','valid':True}]}
  sources=[{'date':'2026-10-20','file_id':file_id},{'date':'2026-10-21','file_id':197}]
  return rebuild_retained_analysis(tables,[{'items':[{'article':'1342107','members':[member]}]}],sources,[],
      '2026-10-21','test',{'confirmed_upcs':['24053300000'],'source_quality_holds':[{'file_id':179,'date':'2026-10-20'}]})
 def test_held_day_cannot_feed_daily_gp_or_price_metrics(self):
  out,audit=self.build()
  daily=dict(zip(out['ANALYSIS_UPC_DAILY'][0],out['ANALYSIS_UPC_DAILY'][1]))
  for key in ('sales','qty','price','normalized_gp','historical_gp'):self.assertIsNone(daily[key])
  self.assertEqual(daily['pos_file'],179)
  self.assertEqual(daily['pos_reported_count'],10)
  episode=dict(zip(out['ANALYSIS_PRICE_EPISODES'][0],out['ANALYSIS_PRICE_EPISODES'][1]))
  self.assertEqual(episode['supported_days'],1)
  self.assertAlmostEqual(episode['sales_day'],79.8)
  self.assertAlmostEqual(episode['gp_day'],44.8)
  self.assertFalse(episode['performance_ok'])
  self.assertEqual(audit['source_quality']['held_sources'],[{'date':'2026-10-20','file_id':179,'batch_id':None,'original_filename':None}])
 def test_replacement_overwrites_key_and_clears_only_matching_hold(self):
  held,_=self.build();out,audit=self.build(held,200)
  self.assertEqual(len(out['ANALYSIS_UPC_DAILY']),3)
  daily=dict(zip(out['ANALYSIS_UPC_DAILY'][0],out['ANALYSIS_UPC_DAILY'][1]))
  self.assertEqual(daily['pos_file'],200);self.assertAlmostEqual(daily['sales'],39.9)
  self.assertNotIn('SOURCE_QUALITY_HOLD',daily['reason'] or '')
  self.assertEqual(audit['source_quality']['held_sources'],[])
  episode=dict(zip(out['ANALYSIS_PRICE_EPISODES'][0],out['ANALYSIS_PRICE_EPISODES'][1]))
  self.assertEqual(episode['supported_days'],2)
  again,_=self.build(out,200);self.assertEqual(out,again)

if __name__=='__main__':unittest.main()
