import ast,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'server/chatgpt_sheet_bridge.py';t=ast.parse(p.read_text());f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='publish_chatgpt_snapshot')
pre=next(n.test for n in ast.walk(f) if isinstance(n,ast.If) and 'max(' in ast.unparse(n.test) and 'publish_batch_id' in ast.unparse(n.test))
post=next(n.test for n in ast.walk(f) if isinstance(n,ast.If) and 'current.get' in ast.unparse(n.test) and "'hi'" in ast.unparse(n.test))
def check(expr,**scope):return eval(compile(ast.Expression(expr),str(p),'eval'),{},scope)
class Tests(unittest.TestCase):
 def test_preserved_historical_rows_can_publish(self):
  self.assertFalse(check(pre,rows=[{'publish_batch_id':70},{'publish_batch_id':71}],batch_id=71))
  self.assertFalse(check(post,current={'lo':70,'hi':71},batch_id=71))
 def test_newer_snapshot_rejected(self):
  self.assertTrue(check(pre,rows=[{'publish_batch_id':71},{'publish_batch_id':72}],batch_id=71))
  self.assertTrue(check(post,current={'lo':70,'hi':72},batch_id=71))
 def test_requested_snapshot_not_ready_is_rejected(self):
  self.assertTrue(check(pre,rows=[{'publish_batch_id':70}],batch_id=71))
if __name__=='__main__':unittest.main()
