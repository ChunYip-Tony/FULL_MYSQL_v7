import ast,unittest
from datetime import date,datetime
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'server/phase3.py';tree=ast.parse(path.read_text());scope=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_routine_upload_quick_check_scope')
def parse_date(v):
 if isinstance(v,datetime):return v.date()
 if isinstance(v,date):return v
 try:return datetime.fromisoformat(str(v)).date()
 except (ValueError,TypeError):return None
ns={'_date':parse_date};exec(compile(ast.Module(body=[scope],type_ignores=[]),str(path),'exec'),ns)
class Cursor:
 def __init__(self,kind):self.kind=kind;self.rows=[];self.calls=[]
 def execute(self,sql,args=None):
  self.calls.append((sql,args))
  if 'source_type FROM' in sql:self.rows=[{'source_type':self.kind}]
  elif 'FROM quick_check_current' in sql:self.rows=[{'upc_id':1,'family_id':10,'quick_check_status':'READY'}]
  elif 'sales_period_observation' in sql:self.rows=[{'upc_id':1,'ean_upc':'123'}]
  else:self.rows=[]
 def fetchall(self):return self.rows
class Tests(unittest.TestCase):
 def test_oh_pos_mvt_extract_earliest_date(self):
  for kind in ['on_hand','movement','sales_by_price_type']:
   cur=Cursor(kind);p=[{'upc_id':1,'ean_upc':'123','family_id':10}]
   result=ns['_routine_upload_quick_check_scope'](cur,71,p,[{'date':date(2026,10,20),'file_id':2},{'date':date(2026,10,18),'file_id':1},{'date':date(2026,10,18),'file_id':3}])
   self.assertEqual(result,p)
   sales=next(args for sql,args in cur.calls if 'sales_period_observation' in sql)
   self.assertEqual(sales,(date(2026,10,18),71))
 def test_invalid_coverage_uses_full_rebuild(self):
  cur=Cursor('on_hand');self.assertIsNone(ns['_routine_upload_quick_check_scope'](cur,71,[],[{'date':None}]))
  self.assertFalse(any('sales_period_observation' in sql for sql,_ in cur.calls))
if __name__=='__main__':unittest.main()
