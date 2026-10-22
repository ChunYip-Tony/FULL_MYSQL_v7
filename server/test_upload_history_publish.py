import copy
import unittest
from unittest.mock import patch
from datetime import date
from price_history_analysis import HEADERS, rebuild_retained_analysis, build_upload_history, verify_history_tables, read_retained_tables
from upload_history_publish import publish_upload_history

class HistoryPublishTests(unittest.TestCase):
 def test_all_histories_are_loaded_in_bounded_lazy_pages(self):
  tables,_=self.fixture();calls=[]
  rows=[{'ean_upc':str(i),'quick_check_status':'READY'} for i in range(61)]
  def loader(ids):
   calls.append(ids)
   return {'through':'2026-10-19','items':[]}
  def rebuild(t,pages,*args):
   self.assertFalse(isinstance(pages,list))
   self.assertEqual(calls,[])
   self.assertEqual(len(list(pages)),3)
   return {},{'missing_upcs':[]}
  with patch('business_clock.completed_through_date',return_value=date(2026,10,19)),patch('price_history_analysis.rebuild_retained_analysis',side_effect=rebuild):
   build_upload_history(rows,tables,[],71,'2026-10-19',loader)
  self.assertEqual([len(p) for p in calls],[25,25,11])
  self.assertEqual(set(sum(calls,[])),{str(i) for i in range(61)})
 def fixture(self):
  tables={k:[v[:]] for k,v in HEADERS.items()}
  member={'upc':'24053300000','name':'Tilapia','uom':'LB','cost':{'value':1.75,'uom':'LB','source':'MOVEMENT_RECEIPT_VALUATION','date':'2026-10-13'},'current':{'price':3.99,'type':'REG'},'priceHistory':[{'date':'2026-10-16','file_id':159,'price':3.99,'type':'REG'}], 'days':[{'date':d,'sales':s,'qty':q,'price':3.99,'type':'REG','quantityBasis':'POS_QTY_WEIGHT','valid':True} for d,s,q in [('2026-10-17',39.9,10),('2026-10-18',0,0),('2026-10-19',79.8,20)]]}
  pages=[{'through':'2026-10-19','items':[{'article':'1342107','members':[member]}]}]
  return tables,pages
 def build(self,tables,pages):
  return rebuild_retained_analysis(tables,pages,[],[],'2026-10-19','MYSQL_BATCH_67;UPLOAD_HISTORY_V1',{'confirmed_upcs':['24053300000']})
 def test_new_day_recomputes_progress_and_verified_zero_popularity(self):
  tables,pages=self.fixture();out,audit=self.build(tables,pages)
  e=dict(zip(out['ANALYSIS_PRICE_EPISODES'][0],out['ANALYSIS_PRICE_EPISODES'][1]))
  self.assertEqual(e['supported_days'],3);self.assertEqual(e['popularity'],2/3)
  self.assertAlmostEqual(e['gp_day'],(119.7-30*1.75)/3)
  self.assertEqual(e['last_full'],'2026-10-19')
 def test_missing_date_is_not_a_zero_and_unverified_lb_is_not_allocated(self):
  tables,pages=self.fixture();m=pages[0]['items'][0]['members'][0]
  m['days'].pop(1);m['days'][-1]['quantityBasis']='POS_ITEM_COUNT'
  out,_=self.build(tables,pages);e=dict(zip(out['ANALYSIS_PRICE_EPISODES'][0],out['ANALYSIS_PRICE_EPISODES'][1]))
  self.assertEqual(e['supported_days'],2);self.assertEqual(e['popularity'],1)
  self.assertIsNone(e['gp_day']);self.assertFalse(e['performance_ok'])
 def test_rebuild_is_idempotent_and_retains_superseded_episode(self):
  t,p=self.fixture();out,_=self.build(t,p)
  p[0]['items'][0]['members'][0]['priceHistory'].append({'date':'2026-10-19','file_id':170,'price':4.99,'type':'REG'})
  out2,_=self.build(out,p);out3,_=self.build(out2,p)
  self.assertEqual(out2,out3);self.assertEqual(len(out2['ANALYSIS_PRICE_EPISODES']),3)
 def test_interior_corruption_fails_readback(self):
  t,p=self.fixture();out,_=self.build(t,p)
  def reader(title,start,end,width):
   rows=copy.deepcopy(out[title][start-1:end])
   if title=='ANALYSIS_UPC_DAILY' and start==1:rows[2][7]=999
   return rows
  with self.assertRaisesRegex(ValueError,'readback mismatch'):verify_history_tables(out,reader)
 def test_mixed_source_cutoff_cannot_be_certified(self):
  t,p=self.fixture()
  with patch('business_clock.completed_through_date',return_value=date(2026,10,19)):
   with self.assertRaisesRegex(ValueError,'source changed'):
    build_upload_history([{'ean_upc':'24053300000','quick_check_status':'READY'}],t,[],67,'2026-10-19',lambda ids:{'through':'2026-10-18'})
 def test_failed_write_never_leaves_verified_status(self):
  t,p=self.fixture();out,audit=self.build(t,p);book={}
  def writer(title,matrix,previous=None):
   if title=='ANALYSIS_UPC_DAILY':raise OSError('transport failed')
   book[title]=copy.deepcopy(matrix)
  def reader(title,start,end,width):return t.get(title,[])[start-1:end]
  with patch('upload_history_publish.build_upload_history',return_value=(out,{**audit,'requested_upcs':1})),patch('upload_history_publish.read_retained_tables',return_value=t):
   with self.assertRaises(OSError):publish_upload_history(rows=[],source_days=[],batch_id=67,through='2026-10-19',reader=reader,writer=writer)
  self.assertEqual(book['ANALYSIS_STATUS'][5][1],'FAILED')

if __name__=='__main__':unittest.main()

