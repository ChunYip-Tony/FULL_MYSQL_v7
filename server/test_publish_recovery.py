import copy
import unittest
from datetime import datetime,timedelta,timezone
from publish_recovery import publish_recovery_decision

class PublicationRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,23,tzinfo=timezone.utc);self.snapshot=self.now-timedelta(minutes=5)
  self.row={'processing_status':'COMPLETED','completed_at':self.now-timedelta(minutes=1),'code_version':'7.0.535','detail_json':{'publish_result':{'status':'PASS','history_contract':'H2','readback':{'pass':True,'history':{'pass':True},'inventory_adjustments':{'pass':True,'contract':'INVENTORY_GP_V1'}}}}}
 def decide(self,row):return publish_recovery_decision(row,self.snapshot,'7.0.535','H2',self.now)
 def test_missing_publish_is_queued(self):self.assertTrue(self.decide(None)['queue'])
 def test_verified_current_snapshot_is_not_rewritten(self):self.assertEqual(self.decide(self.row)['reason'],'VERIFIED_CURRENT')
 def test_same_batch_new_source_requires_followup(self):
  self.row['completed_at']=self.snapshot-timedelta(seconds=1);self.assertTrue(self.decide(self.row)['queue'])
 def test_missing_inventory_or_history_verification_cannot_count_as_done(self):
  for section in ('inventory_adjustments','history'):
   row=copy.deepcopy(self.row);row['detail_json']['publish_result']['readback'].pop(section)
   self.assertTrue(self.decide(row)['queue'])
 def test_running_or_queued_job_is_not_duplicated(self):
  for state in ('STARTED','QUEUED','PAUSE_REQUESTED'):
   self.assertFalse(self.decide({**self.row,'processing_status':state})['queue'])
 def test_transient_failure_retries_after_cooldown_without_lifetime_limit(self):
  row={**self.row,'processing_status':'FAILED','retry_count':200,'completed_at':self.now-timedelta(hours=2),'detail_json':{'error':'HTTP 503'}}
  self.assertTrue(self.decide(row)['queue'])
  row['completed_at']=self.now;self.assertEqual(self.decide(row)['reason'],'RETRY_WAIT')
 def test_deterministic_failure_needs_repair_then_new_code_can_retry(self):
  row={**self.row,'processing_status':'FAILED','detail_json':{'publish_result':{'error':'History readback mismatch'}}}
  self.assertEqual(self.decide(row)['reason'],'REPAIR_REQUIRED')
  row['code_version']='7.0.534';self.assertTrue(self.decide(row)['queue'])
 def blocked(self):
  return {**self.row,'processing_status':'FAILED','completed_at':self.now-timedelta(minutes=1),'detail_json':{'publish_result':{'status':'BLOCKED','reason':'No READY Quick Check rows'}}}
 def test_source_hold_does_not_retry_unchanged_snapshot(self):
  row=self.blocked();row['completed_at']=self.now-timedelta(hours=2)
  self.snapshot=row['completed_at']-timedelta(minutes=1)
  result=self.decide(row);self.assertFalse(result['queue']);self.assertEqual(result['reason'],'WAITING_FOR_DATA')
 def test_rebuilt_source_after_hold_retries(self):
  row=self.blocked();self.snapshot=self.now
  self.assertEqual(self.decide(row)['reason'],'SOURCE_CHANGED_AFTER_BLOCK')
 def test_new_runtime_can_recheck_source_hold(self):
  row=self.blocked();row['code_version']='7.0.534'
  self.assertTrue(self.decide(row)['queue'])
 def test_source_hold_without_timestamp_cannot_spin(self):
  row=self.blocked();row['completed_at']=None
  self.assertEqual(self.decide(row)['reason'],'WAITING_FOR_DATA')

if __name__=='__main__':unittest.main()

