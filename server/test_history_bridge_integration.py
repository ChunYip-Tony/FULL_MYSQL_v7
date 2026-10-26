import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).parent

def load_function(filename,name,env):
 tree=ast.parse((ROOT/filename).read_text())
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),filename,'exec'),env)
 return env[name]

class BridgeIntegrationTests(unittest.TestCase):
 def test_history_short_read_retries_without_weakening_cell_comparison(self):
  from price_history_analysis import verify_history_tables
  from unittest.mock import Mock
  expected=[['upc','sales'],['000611338042',10.25]]
  reader=Mock(side_effect=[[],expected])
  self.assertTrue(verify_history_tables({'ANALYSIS_UPC_DAILY':expected},reader)['pass'])
  self.assertEqual(reader.call_count,2)
  reader=Mock(return_value=[['upc','sales'],['611338042',10.25]])
  with self.assertRaisesRegex(ValueError,'expected.*000611338042.*actual.*611338042'):
   verify_history_tables({'ANALYSIS_UPC_DAILY':expected},reader)
  self.assertEqual(reader.call_count,3)

 def test_history_readback_uses_the_same_numeric_rounding_as_the_writer(self):
  from decimal import Decimal
  from datetime import date,datetime
  from price_history_analysis import verify_history_tables
  wire=load_function('chatgpt_sheet_bridge.py','_wire',{'Any':object,'Decimal':Decimal,'date':date,'datetime':datetime})
  expected=[['upc','price','sales'],['000611338042',33.57/7,Decimal('33.57')]]
  actual=[[wire(v) for v in row] for row in expected]
  self.assertEqual(actual[1][1],4.79571428571429)
  verify_history_tables({'ANALYSIS_UPC_DAILY':expected},lambda *a:actual)
  actual[1][1]=4.79571428571428
  with self.assertRaisesRegex(ValueError,'price'):
   verify_history_tables({'ANALYSIS_UPC_DAILY':expected},lambda *a:actual)

 def test_old_current_only_pass_does_not_skip_history_recovery(self):
  class Cursor:
   def execute(self,*args):pass
   def fetchone(self):return {'processing_status':'COMPLETED','publish_status':'PASS','readback_pass':'true','completed_at':2,'snapshot_updated_at':1}
  fn=load_function('worker.py','_startup_bridge_already_verified',{'API_PIPELINE':'x','HISTORY_CONTRACT':'UPLOAD_HISTORY_V1'})
  self.assertFalse(fn(Cursor(),67))
 def test_incremental_write_skips_equal_chunks_and_never_clears_history(self):
  calls=[]
  env={'_wire':lambda v:'' if v is None else v,'_col_letters':lambda n:'B','_apps_script_post':lambda p,**kw:calls.append(p)}
  fn=load_function('chatgpt_sheet_bridge.py','_write_changed_history',env)
  env['Any']=object
  env['_apps_script_wire']=load_function('chatgpt_sheet_bridge.py','_apps_script_wire',env)
  old=[['upc','price'],['123',3.99]]
  fn(None,'sheet','ANALYSIS_PRICE_EVENTS',old,old,'APPS_SCRIPT')
  self.assertEqual(calls,[])
  fn(None,'sheet','ANALYSIS_PRICE_EVENTS',old+[['456',4.99]],old,'APPS_SCRIPT')
  self.assertEqual(len(calls),1);self.assertFalse(calls[0]['clear'])
 def test_success_receipt_requires_history_readback_before_bridge_pass(self):
  source=(ROOT/'chatgpt_sheet_bridge.py').read_text()
  self.assertLess(source.index('history = publish_upload_history'),source.index('status="PASS",',source.index('history = publish_upload_history')))
  self.assertIn('"history_contract":HISTORY_CONTRACT',source)


 def test_leading_zero_upc_is_literal_text_and_exact_readback_remains_required(self):
  from price_history_analysis import verify_history_tables
  calls=[]
  env={'Any':object,'_wire':lambda v:'' if v is None else v,'_col_letters':lambda n:'B',
       '_apps_script_post':lambda p,**kw:calls.append(p)}
  env['_apps_script_wire']=load_function('chatgpt_sheet_bridge.py','_apps_script_wire',env)
  fn=load_function('chatgpt_sheet_bridge.py','_write_changed_history',env)
  matrix=[['upc','name'],['000611338042','UNAGI']]
  fn(None,'sheet','ANALYSIS_COVERAGE',matrix,[matrix[0]],'APPS_SCRIPT')
  self.assertEqual(calls[0]['values'][1][0],"'000611338042")
  self.assertEqual(matrix[1][0],'000611338042')
  # Google treats the single leading apostrophe as a literal-text marker.
  readback=[[v[1:] if isinstance(v,str) and v.startswith("'") else v for v in r] for r in calls[0]['values']]
  verify_history_tables({'ANALYSIS_COVERAGE':matrix},lambda *a:readback)
  readback[1][0]='611338042'
  with self.assertRaisesRegex(ValueError,'upc'):
   verify_history_tables({'ANALYSIS_COVERAGE':matrix},lambda *a:readback)

 def test_raw_transport_does_not_add_literal_text_marker(self):
  calls=[]
  env={'_wire':lambda v:'' if v is None else v,'_col_letters':lambda n:'A',
       'quote':lambda v,**kw:v,'API_ROOT':'root','_put_json':lambda *a:calls.append(a)}
  fn=load_function('chatgpt_sheet_bridge.py','_write_changed_history',env)
  fn(None,'sheet','ANALYSIS_COVERAGE',[['upc'],['000611338042']],[['upc']],'SHEETS_API')
  self.assertEqual(calls[0][2]['values'][1][0],'000611338042')

 def test_singular_dated_sale_filename_is_pos_but_price_list_stays_price(self):
  import re
  fn=load_function('ingest.py','classify_source',{'re':re})
  self.assertEqual(fn('sf-sale-090526.xls')[0],'sales_by_price_type')
  self.assertEqual(fn('sf-sale-price-090526.xls')[0],'price_list')
  self.assertEqual(fn('sale-photo.jpg')[0],'unclassified')



 def test_coverage_repairs_only_unique_canonical_upc_in_the_same_family(self):
  from price_history_analysis import reconcile_coverage_identifiers
  coverage={'611338042':{'upc':'611338042','family':'3480308'}}
  current={'000611338042':{'main_article_number':'3480308'}}
  self.assertEqual(reconcile_coverage_identifiers(coverage,current),1)
  self.assertEqual(list(coverage),['000611338042'])
  self.assertEqual(reconcile_coverage_identifiers(coverage,current),0)
  ambiguous={'0611338042':{'main_article_number':'3480308'},**current}
  orphan={'611338042':{'upc':'611338042','family':'3480308'}}
  self.assertEqual(reconcile_coverage_identifiers(orphan,ambiguous),0)
  self.assertEqual(reconcile_coverage_identifiers(orphan,{'000611338042':{'main_article_number':'OTHER'}}),0)


class HeldInventoryPublicationTests(unittest.TestCase):
 def test_empty_ready_readback_requires_header_only_and_preserves_full_cell_check(self):
  from price_history_analysis import verify_history_tables
  from unittest.mock import patch
  tabs={k:k for k in ['source','lookup','analysis','family']}
  source=[['Field','Value'],['MySQL_Batch_ID',80],['Serving_Rows_Total',1],['Analysis_READY_Rows',0]]
  values={"'source'!A1:B40":source,"'lookup'!A1:I2":[['Sheet_Row','upc_id'],[2,'000123']],
   "'lookup'!A2:I2":[[2,'000123']],"'analysis'!A1:B2":[['Sheet_Row','ean_upc']],
   "'analysis'!A1:B1":[['Sheet_Row','ean_upc']],
   "'family'!S1:AN2":[['daily_department','daily_date','daily_family_id']]}
  fn=load_function('chatgpt_sheet_bridge.py','_validate_readback_once',{'Any':object,'MYSQL_TABS':tabs,'_wire':lambda x:x,'_col_letters':lambda n:'B'})
  matrix={'analysis':[['Sheet_Row','ean_upc']]}
  def run():return fn(None,'sheet',80,1,analysis_row_count=0,reader=lambda s,i,r:values[r],expected_matrices=matrix)
  with patch('price_history_analysis.verify_history_tables',wraps=verify_history_tables) as verify:
   self.assertTrue(run()['full_cell_readback']);self.assertEqual(verify.call_count,1)
  values["'analysis'!A1:B2"].append([2,'stale-upc'])
  self.assertIn('ANALYSIS_UNEXPECTED_DATA_ROW',run()['failures'])
  values["'analysis'!A1:B2"].pop()
  values["'analysis'!A1:B1"]=[['Wrong','header']]
  self.assertFalse(run()['pass'])

 def test_nonempty_ready_readback_still_checks_last_row_and_batch(self):
  tabs={k:k for k in ['source','lookup','analysis','family']}
  values={"'source'!A1:B40":[['Field','Value'],['MySQL_Batch_ID',80],['Serving_Rows_Total',1],['Analysis_READY_Rows',1]],
   "'lookup'!A1:I2":[['Sheet_Row','upc_id']],"'lookup'!A2:I2":[[2,'000123']],
   "'analysis'!A1:B2":[['Sheet_Row','ean_upc'],[2,'000123']],"'analysis'!A2:B2":[[2,'000123']],
   "'family'!S1:AN2":[['daily_department','daily_date','daily_family_id']]}
  fn=load_function('chatgpt_sheet_bridge.py','_validate_readback_once',{'Any':object,'MYSQL_TABS':tabs})
  def run():return fn(None,'sheet',80,1,analysis_row_count=1,reader=lambda s,i,r:values[r])
  self.assertTrue(run()['pass'])
  values["'analysis'!A2:B2"][0][0]=3
  self.assertIn('ANALYSIS_LAST_ROW_MISMATCH',run()['failures'])
  values["'source'!A1:B40"][1][1]=79
  self.assertIn('BATCH_ID_MISMATCH',run()['failures'])

 def test_publisher_keeps_all_inventory_holds_but_publishes_dated_history(self):
  import contextlib,sys,time,types
  from unittest.mock import Mock,patch
  row={'ean_upc':'000123','quick_check_status':'QA_HOLD','blocking_reason':'OH_MOVEMENT_ROLLFORWARD_BLOCKED','publish_batch_id':80}
  cursor=Mock();cursor.fetchone.return_value={'hi':80}
  conn=Mock();conn.cursor.return_value=cursor
  tabs={k:k for k in ['source','lookup','quick','family','analysis','qa','negative','cost_backfill','bridge']}
  written={};events=[]
  def write(sid,title,matrix):written[title]=matrix;events.append(title)
  history=Mock(return_value={'readback':{'pass':True},'revision':'batch80','through':'2026-10-24'})
  def module(**kw):return types.SimpleNamespace(**kw)
  modules={
   'inventory_gp_adjustments':module(build_adjustment_export=lambda *a:([['header']],{}),publish_supported_adjustments=lambda *a:{'pass':True}),
   'analysis_movement':module(build_movement_export=lambda *a:{}),
   'analysis_pos':module(build_pos_export=lambda *a:{'rows':[{'date':'2026-10-24','sales':25}]}),
   'mobile_pricing':module(price_snapshots=lambda *a,**k:[]),
   'family_daily_gp':module(build_family_daily=lambda *a:([['department','date','family_id']],{})),
   'business_clock':module(completed_through_date=lambda:'2026-10-24'),
   'current_price_export':module(PRICE_COLUMNS=[],apply_current_prices=lambda *a:None),
   'upload_history_publish':module(publish_upload_history=history)}
  env={'Any':object,'time':time,'bridge_enabled':lambda:True,'_sheet_id':lambda:'sheet','_bridge_transport':lambda:'APPS_SCRIPT',
   'db_conn':lambda:contextlib.nullcontext(conn),'_fetch_batch_state':lambda *a:({'processing_status':'QUICK_CHECK_READY_WITH_HOLDS'},{'blocking_issue_count':0}),
   '_fetch_quick_rows':lambda *a:[row],'_canonical_freshness':lambda *a:{'pos_data_through':'2026-10-24'},
   '_fetch_latest_daily_sales':lambda *a:{},'_fetch_recent_3d_sales':lambda *a:{},'source_data_days':lambda *a,**k:['2026-10-24'],
   'negative_stock_queue':lambda **k:{},'cost_backfill_queue':lambda **k:{},'MYSQL_TABS':tabs,
   '_bridge_status':lambda **k:[['Field','Value'],['Last_Publish_Status',k['status']],['MySQL_Publish_Batch_ID',k['batch_id']]],
   '_apps_script_write_matrix':write,'_apps_script_read_values':lambda sid,a1:written['bridge'],
   '_protect_current_export':lambda *a:None,'_build_family':lambda *a:[['family']],
   '_source_status':lambda *a,**k:[['Field','Value'],['Analysis_READY_Rows',k['analysis_ready_rows']]],
   '_build_lookup':lambda *a:[['Sheet_Row','upc_id'],[2,'000123']], '_build_quick':lambda *a:[['upc'],['000123']],
   '_build_negative_stock':lambda *a:[['header']],'_build_cost_backfill':lambda *a:[['header']],
   '_validate_readback':lambda *a,**k:{'pass':True,'full_cell_readback':True},
   'HISTORY_CONTRACT':'TEST_HISTORY','_active_source':lambda:'MYSQL','ANALYSIS_COLUMNS':['ean_upc'],'POS_3D_COLUMNS':[],'LATEST_DAILY_COLUMNS':[]}
  load_function('chatgpt_sheet_bridge.py','_build_analysis',env)
  load_function('chatgpt_sheet_bridge.py','_build_qa',env)
  fn=load_function('chatgpt_sheet_bridge.py','publish_chatgpt_snapshot',env)
  with patch.dict(sys.modules,modules):
   result=fn(80)
   self.assertEqual(result['status'],'PASS',result)
   self.assertEqual(result['analysis_ready_row_count'],0)
   self.assertEqual(result['analysis_input_policy'],'READY_ONLY')
   self.assertEqual(len(written['analysis']),1)
   self.assertEqual(written['qa'][1][9:11],['QA_HOLD','OH_MOVEMENT_ROLLFORWARD_BLOCKED'])
   self.assertEqual(history.call_args.kwargs['through'],'2026-10-24')
   self.assertEqual(history.call_count,1)
   env['_fetch_batch_state']=lambda *a:({'processing_status':'QUICK_CHECK_READY_WITH_HOLDS'},{'blocking_issue_count':1})
   self.assertEqual(fn(80)['status'],'BLOCKED')
   self.assertEqual(history.call_count,1)
   env['_fetch_batch_state']=lambda *a:({'processing_status':'QUICK_CHECK_READY_WITH_HOLDS'},{'blocking_issue_count':0})
   cursor.fetchone.return_value={'hi':81}
   self.assertEqual(fn(80)['status'],'FAILED')
   self.assertEqual(written['bridge'][1][1],'FAILED')

 def test_manual_republish_allows_empty_ready_but_retains_global_and_revision_guards(self):
  import contextlib,json
  from unittest.mock import Mock
  class HTTPException(Exception):
   def __init__(self,status_code,detail):self.status_code=status_code;self.detail=detail
  cursor=Mock();conn=Mock();conn.cursor.return_value=cursor
  enqueue=Mock(return_value={'status':'QUEUED'})
  env={'Request':object,'HTTPException':HTTPException,'json':json,'j':str,
   'app':type('App',(),{'post':lambda s,*a:lambda fn:fn})(),'_browser_upload_guard':lambda r:None,
   'bridge_enabled':lambda:True,'db_conn':lambda:contextlib.nullcontext(conn),
   'enqueue_chatgpt_publish':enqueue,'API_PIPELINE':'api','VERSION':'test'}
  fn=load_function('api.py','web_upload_republish_chatgpt_analysis',env)
  phase={'result_status':'QUICK_CHECK_READY_WITH_HOLDS','blocking_issue_count':0,'quick_check_ready_rows':0}
  def rows(phase=phase,batch=80):cursor.fetchone.side_effect=[{'batch_id':80},phase,{'c':374,'min_batch':78,'max_batch':batch}]
  rows();self.assertEqual(fn(80,object())['status'],'QUEUED');self.assertEqual(enqueue.call_count,1)
  for state,batch,reason in [({**phase,'blocking_issue_count':1},80,'PHASE3_GLOBAL_BLOCKERS_PRESENT'),(phase,81,'BATCH_IS_NOT_CURRENT_SERVING_SNAPSHOT')]:
   rows(state,batch)
   with self.assertRaises(HTTPException) as raised:fn(80,object())
   self.assertEqual(raised.exception.detail['reason'],reason)
  self.assertEqual(enqueue.call_count,1)


if __name__=='__main__':unittest.main()


