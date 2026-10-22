"""A same-batch rebuild completing during export must not lose its publish."""
import ast,json,unittest
from datetime import datetime,timezone
from pathlib import Path
source=Path(__file__).resolve().parents[1]/'server/chatgpt_sheet_bridge.py'
f=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='enqueue_chatgpt_publish')
class Cursor:
 def __init__(self,active):self.active=active;self.inserted=[];self.lastrowid=1973
 def execute(self,q,args):
  self.query=q
  if 'INSERT INTO pipeline_run' in q:self.inserted.append(args)
 def fetchone(self):return {'next_run':10} if 'MAX(run_number)' in self.query else self.active
 def close(self):pass
class Connection:
 def __init__(self,cur):self.cur=cur
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def cursor(self,**kw):return self.cur
 def commit(self):pass
class Tests(unittest.TestCase):
 def run_queue(self,status,prior,new=1972):
  active={'pipeline_run_id':1971,'processing_status':status,'code_version':'test','detail_json':json.dumps({'source_pipeline_run_id':prior})} if status else None
  cur=Cursor(active);scope={'Any':object,'json':json,'datetime':datetime,'timezone':timezone,'bridge_enabled':lambda:True,'db_conn':lambda:Connection(cur)}
  exec(compile(ast.Module(body=[f],type_ignores=[]),str(source),'exec'),scope)
  result=scope['enqueue_chatgpt_publish'](71,pipeline_name='API',code_version='test',requested_by='WORKER',source_pipeline_run_id=new)
  return result,cur.inserted
 def test_new_rebuild_gets_followup_after_running_export(self):
  result,inserts=self.run_queue('STARTED',None)
  self.assertEqual(result['status'],'QUEUED');self.assertEqual(len(inserts),1)
  self.assertEqual(json.loads(inserts[0][-1])['source_pipeline_run_id'],1972)
 def test_same_rebuild_deduplicates(self):
  result,inserts=self.run_queue('STARTED',1972)
  self.assertEqual(result['status'],'ALREADY_ACTIVE');self.assertFalse(inserts)
 def test_queued_job_absorbs_newer_revision(self):
  result,inserts=self.run_queue('QUEUED',1957)
  self.assertEqual(result['status'],'ALREADY_QUEUED');self.assertFalse(inserts)
 def test_first_export_is_queued(self):
  result,inserts=self.run_queue(None,None)
  self.assertEqual(result['status'],'QUEUED');self.assertEqual(len(inserts),1)
if __name__=='__main__':unittest.main()
