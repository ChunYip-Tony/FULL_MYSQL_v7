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


if __name__=='__main__':unittest.main()

