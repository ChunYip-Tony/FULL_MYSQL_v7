import copy
import unittest
from decimal import Decimal
from performance_advice import compare_performance
from analysis_movement import publish_source_records
from price_history_analysis import verify_member_performance


class EvidenceTests(unittest.TestCase):
    def test_uploaded_scope_does_not_invent_missing_calendar_days(self):
        member={'name':'Fish','family':'123','uom':'EA','days':[{'date':'2026-10-20','sales':20,'qty':2,'price':10,'type':'REG','cost':{'value':4,'uom':'EA','source':'receipt','date':'2026-10-19'},'gp':12}]}
        result=verify_member_performance(member,{}, {'2026-10-20':{'file_id':1}}, '2026-10-20', {'expected_completed_date':'2026-10-21'})
        self.assertTrue(result['uploaded_sales_verified'])
        self.assertTrue(result['uploaded_gp_verified'])
        self.assertFalse(result['calendar_current'])
        self.assertFalse(result['fully_verified'])
        self.assertNotIn('2026-10-19',result['uploaded_missing_item_dates'])

    def test_periods_normalize_days_and_keep_unknown_gp(self):
        def reader(args):
            prior=args['start_date']=='2026-10-01'
            return {'data_available':True,'supported_day_count':2 if prior else 4,
                    'sales_dollars':100 if prior else 300,'gp_dollars':20 if prior else None,
                    'sold_quantity_by_uom':{'LB':10 if prior else 30},
                    '_comparison_rows':[{'upc':'000123','name':'Fish','sales_amount':100 if prior else 300}]}
        result=compare_performance({'current_start':'2026-10-10','current_end':'2026-10-13','prior_start':'2026-10-01','prior_end':'2026-10-02'},reader)
        self.assertEqual(result['per_supported_day']['sales_dollars']['change'],25)
        self.assertIsNone(result['per_supported_day']['gp_dollars']['change'])
        self.assertEqual(result['largest_matched_upc_changes'][0]['upc'],'000123')
        self.assertEqual(result['quantity_per_supported_day_by_uom']['LB']['change'],Decimal('2.5'))

    def test_insufficient_days_and_overlapping_periods_fail_closed(self):
        result=compare_performance({'supported_days':7},lambda args:{'supported_dates':['2026-10-20']})
        self.assertFalse(result['data_available'])
        with self.assertRaises(ValueError):
            compare_performance({'current_start':'2026-10-02','current_end':'2026-10-04','prior_start':'2026-10-01','prior_end':'2026-10-03'},lambda args:None)

    def test_source_merge_preserves_wide_history_beyond_5000(self):
        saved=[['source_id','record_kind','upc','other_evidence']]+[[str(i),'SOURCE','000123',str(i)] for i in range(5100)]
        def reader(title,start,end,width):return [r[:width] for r in saved[start-1:end]]
        def writer(title,rows):saved[:]=copy.deepcopy(rows)
        result=publish_source_records(reader,writer,[{'source_id':'MOVEMENT:1:2','record_kind':'MOVEMENT_LINE','movement_json':'{"amount":-10}'}],{'MOVEMENT_LINE'})
        self.assertEqual(result['rows'],5101)
        self.assertEqual(saved[5001][3],'5000')
        self.assertEqual(saved[5001][2],'000123')
        def corrupted(title,start,end,width):
            rows=reader(title,start,end,width)
            if start<=2000<=end:
                rows[2000-start]=list(rows[2000-start]);rows[2000-start][2]=123
            return rows
        # Corrupt only the post-write readback, not the retained preflight.
        written=False
        def second_writer(title,rows):
            nonlocal written
            writer(title,rows);written=True
        with self.assertRaisesRegex(RuntimeError,'row 2000, upc'):
            publish_source_records(lambda *a:corrupted(*a) if written else reader(*a),second_writer,[],{'MOVEMENT_LINE'})


if __name__=='__main__':unittest.main()
