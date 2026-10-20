import json,pathlib,unittest
P=pathlib.Path('/tmp/history-repair')
def records(name):
 x=json.loads((P/(name+'-rebuilt.json')).read_text());return [dict(zip(x[0],r)) for r in x[1:]]
class HistoryRepairTests(unittest.TestCase):
 def test_no_retained_keys_lost(self):
  for name,keys in [('ANALYSIS_UPC_DAILY',['upc','date']),('ANALYSIS_PRICE_EPISODES',['episode_id']),('ANALYSIS_PRICE_TRACKING',['upc'])]:
   old=json.loads((P/(name+'.json')).read_text());oldrows=[dict(zip(old[0],r)) for r in old[1:]];new=records(name)
   oldkeys={tuple(str(r.get(k)) for k in keys) for r in oldrows};newkeys=[tuple(str(r.get(k)) for k in keys) for r in new]
   self.assertTrue(oldkeys<=set(newkeys));self.assertEqual(len(newkeys),len(set(newkeys)))
 def test_tilapia_uses_observed_pos_quantity(self):
  r=next(x for x in records('ANALYSIS_UPC_DAILY') if str(x['upc'])=='24053300000' and x['date']=='2026-10-18')
  self.assertEqual(r['qty'],66);self.assertEqual(r['sales'],261.61);self.assertEqual(r['pos_reported_count'],66)
  self.assertAlmostEqual(r['normalized_gp'],146.11)
 def test_zero_quantity_sale_never_gets_gp(self):
  r=next(x for x in records('ANALYSIS_UPC_DAILY') if str(x['upc'])=='24570200000' and x['date']=='2026-10-18')
  self.assertEqual(r['sales'],11.74);self.assertIsNone(r['normalized_gp']);self.assertFalse(r['valid'])
 def test_sales_and_price_coverage_do_not_become_fake_zero(self):
  for r in records('ANALYSIS_UPC_DAILY'):
   if r['sales'] is None:self.assertIsNone(r['normalized_gp'])
 def test_comparisons_reconcile_and_disclose_partial(self):
  rows=records('ANALYSIS_PRICE_EPISODES');byid={x['episode_id']:x for x in rows}
  for r in rows:
   if r.get('previous_gp_day') is None:continue
   old=byid[r['preceding_comparable_id']]
   self.assertAlmostEqual(r['gp_day_change'],r['gp_day']-old['gp_day'])
   if not(old['performance_ok'] and r['performance_ok']):self.assertEqual(r['confidence'],'PARTIAL_OBSERVED_COMPARISON')
if __name__=='__main__':unittest.main()
