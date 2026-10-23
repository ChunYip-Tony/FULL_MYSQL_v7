"""Regression for the real shared Oct 21–22 file converted to an end-date name."""
from __future__ import annotations
import ast
import unittest
from datetime import date,datetime,timedelta
from pathlib import Path
from movement_coverage_rules import movement_daily_close_filename_evidence,movement_closed_range_filename_evidence


def scope():
    root=Path(__file__).parent
    names={'_as_date','_as_datetime','_file_business_date','_source_snapshot_date',
        '_movement_snapshot_completeness','_movement_daily_snapshot_complete',
        '_candidate_sort_key','_date_span','source_data_days','_movement_coverage_after_anchor'}
    nodes=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]
    for file in ('data_coverage.py','inventory_position.py'):
        nodes.extend(n for n in ast.parse((root/file).read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names)
    ns=dict(date=date,datetime=datetime,timedelta=timedelta,
        movement_daily_close_filename_evidence=movement_daily_close_filename_evidence,
        movement_closed_range_filename_evidence=movement_closed_range_filename_evidence,
        completed_through_date=lambda:date(2026,10,22),business_today=lambda:date(2026,10,23),
        movement_expected_through_date=lambda:date(2026,10,22))
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'source-range','exec'),ns)
    return ns


def file(label='Shared upload · all-mvt-102126-102226.xls'):
    return dict(file_id=198,batch_id=76,original_filename='sf-mvt-102226.xlsx',
        source_type='movement',processing_status='INGESTED',error_count=0,
        duplicate_of_file_id=None,source_row_count=524,date_semantics_status='RESOLVED',
        coverage_type='MULTI_DATE',coverage_start_date=date(2026,10,21),coverage_end_date=date(2026,10,22),
        filename_date_candidate=date(2026,10,22),filename_time_candidate=None,
        report_generated_at=None,upload_timestamp=datetime(2026,10,23,23,18),source_batch_label=label)


class Cursor:
    def __init__(self,row):self.row=row;self.calls=[]
    def execute(self,sql,args):
        self.calls.append((sql,args))
        if 'FROM ingest_file' in sql:self.rows=[self.row]
        elif 'FROM movement_history' in sql:self.rows=[dict(file_id=198,posting_date=date(2026,10,d)) for d in (21,22)]
        else:raise AssertionError(sql)
    def fetchall(self):return self.rows


class SharedRangeTests(unittest.TestCase):
    def test_reproduces_lost_last_day_without_original_range(self):
        ns=scope();self.assertIsNone(ns['_movement_snapshot_completeness'](file(''),date(2026,10,22)))

    def test_original_shared_range_restores_both_daily_slices(self):
        ns=scope();cur=Cursor(file())
        days=ns['source_data_days'](cur,'movement',include_batch_id=76,up_to=date(2026,10,22))
        self.assertEqual([row['date'] for row in days],[date(2026,10,22),date(2026,10,21)])
        self.assertEqual(days[0]['snapshot_completeness'],'COMPLETE_SHARED_SOURCE_MVT_RANGE_FILENAME_CONTRACT')
        self.assertTrue(all(row['file_id']==198 for row in days))
        self.assertIn('ib.batch_label AS source_batch_label',cur.calls[0][0])

    def test_stock_rollforward_accepts_current_batch_without_reimport(self):
        result=scope()['_movement_coverage_after_anchor'](Cursor(file()),anchor_day=date(2026,10,21),include_batch_id=76)
        self.assertTrue(result['complete']);self.assertEqual(result['missing_days'],[])

    def test_mismatched_range_remains_blocked(self):
        ns=scope()
        for label in ('Shared upload · all-mvt-102026-102226.xls','Shared upload · all-mvt-102126-102226-1600.xls','untrusted range 102126-102226'):
            self.assertIsNone(ns['_movement_snapshot_completeness'](file(label),date(2026,10,22)))

    def test_upload_timestamp_alone_never_proves_completeness(self):
        ns=scope();row=file('');row['upload_timestamp']=datetime(2030,1,1)
        self.assertIsNone(ns['_movement_snapshot_completeness'](row,date(2026,10,22)))

    def test_future_range_name_uses_existing_exact_coverage_contract(self):
        row=file('');row['original_filename']='sf-mvt-102126-102226.xlsx'
        self.assertEqual(scope()['_movement_snapshot_completeness'](row,date(2026,10,22)),'COMPLETE_DATE_ONLY_MVT_RANGE_FILENAME_CONTRACT')


if __name__=='__main__':unittest.main()
