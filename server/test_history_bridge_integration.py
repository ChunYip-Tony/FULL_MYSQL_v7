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
  old=[['upc','price'],['123',3.99]]
  fn(None,'sheet','ANALYSIS_PRICE_EVENTS',old,old,'APPS_SCRIPT')
  self.assertEqual(calls,[])
  fn(None,'sheet','ANALYSIS_PRICE_EVENTS',old+[['456',4.99]],old,'APPS_SCRIPT')
  self.assertEqual(len(calls),1);self.assertFalse(calls[0]['clear'])
 def test_success_receipt_requires_history_readback_before_bridge_pass(self):
  source=(ROOT/'chatgpt_sheet_bridge.py').read_text()
  self.assertLess(source.index('history = publish_upload_history'),source.index('status="PASS",',source.index('history = publish_upload_history')))
  self.assertIn('"history_contract":HISTORY_CONTRACT',source)

if __name__=='__main__':unittest.main()
