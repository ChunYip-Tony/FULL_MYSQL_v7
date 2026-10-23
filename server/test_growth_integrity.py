import unittest, ast
from pathlib import Path
from decimal import Decimal as D
from datetime import date
from typing import Any
from unittest.mock import MagicMock
from pos_evidence import verified_pos_quantity, eligible_sales_days
from analysis_movement import summarize_movements
from performance_advice import growth_opportunities, compare_performance

def extract(filename,names,env):
    tree=ast.parse(Path(__file__).with_name(filename).read_text())
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),filename,'exec'),env)

class GrowthIntegrity(unittest.TestCase):
    def test_typed_pos_bulk_department_lookup_retains_financial_rows(self):
        import sys,types
        from unittest.mock import patch
        from analysis_pos import build_pos_export
        day=date(2026,10,19);cur=MagicMock()
        scopes=[{'file_id':178,'sheet_id':1,'source_row_number':r,'department_code':dep} for r,dep in [(1,'400'),(2,'300'),(3,'300'),(3,'400')]]
        raw=[{'file_id':178,'raw_id':r,'sheet_id':1,'source_row_number':r,'period_end_date':day,'ean_upc':'000'+str(r),'price_type':'REG','sales_amount':D('10'),'sold_quantity':1} for r in (1,2,3)]
        cur.fetchall.side_effect=[scopes,raw]
        with patch.dict(sys.modules,{'data_coverage':types.SimpleNamespace(source_data_days=lambda *a,**k:[{'date':day,'file_id':178,'original_filename':'all-sales.xlsx'}])}):
            result=build_pos_export(cur,[],73)
        self.assertEqual(cur.execute.call_count,2)
        self.assertNotIn('(SELECT',cur.execute.call_args.args[0])
        self.assertEqual([r['upc'] for r in result['rows']],['0001','0003'])
        self.assertEqual(sum(r['sales_amount'] for r in result['rows']),20)
        self.assertEqual(result['rows'][1]['department'],'UNASSIGNED_DEPARTMENT')
        self.assertEqual(result['rows'][1]['source_department_codes'],['300','400'])

    def test_production_publisher_wrapper_forwards_progress_and_keeps_quantity_guard(self):
        import types
        row={'latest_daily_pos_qty':None,'latest_daily_pos_reported_qty':2,'latest_daily_quantity_basis':'UNVERIFIED','latest_daily_gp_dollars':None}
        original=MagicMock(return_value={'sales_dollars':D('30'),'gp_dollars':None})
        bridge=types.SimpleNamespace(publish_chatgpt_snapshot=MagicMock(return_value={'status':'PASS'}))
        env={'Any':Any,'_bridge':bridge,'_ORIGINAL_FETCH_LATEST_DAILY':original,'apply_chatgpt_daily_gp_v493':lambda:None}
        extract('chatgpt_daily_gp_v493.py',{'publish_chatgpt_snapshot_v493','_fetch_latest_daily_sales_per_upc'},env)
        callback=MagicMock();env['publish_chatgpt_snapshot_v493'](73,progress=callback)
        bridge.publish_chatgpt_snapshot.assert_called_once_with(73,progress=callback)
        result=env['_fetch_latest_daily_sales_per_upc'](None,73,[row]);original.assert_called_once()
        self.assertIsNone(row['latest_daily_pos_qty']);self.assertEqual(row['latest_daily_pos_reported_qty'],2)
        self.assertIsNone(result['gp_dollars'])

    def test_persistent_readback_mismatch_waits_for_repair(self):
        from publish_recovery import publish_recovery_decision
        from datetime import datetime,timezone,timedelta
        latest={'processing_status':'FAILED','code_version':'v1','completed_at':datetime.now(timezone.utc)-timedelta(hours=2),
            'detail_json':{'publish_result':{'status':'FAILED_READBACK','readback':{'failures':['UPC mismatch']}}}}
        self.assertEqual(publish_recovery_decision(latest,None,'v1','x')['reason'],'REPAIR_REQUIRED')
        self.assertTrue(publish_recovery_decision(latest,None,'v2','x')['queue'])

    def test_movement_advice_filters_dates_and_family_before_loading_rows(self):
        import sys,types
        from unittest.mock import patch
        from analysis_movement import build_movement_export
        days=[{'date':date(2026,10,d),'file_id':d,'original_filename':'sf-mvt.xls'} for d in (20,19,18)]
        cur=MagicMock();cur.fetchall.return_value=[]
        with patch.dict(sys.modules,{'data_coverage':types.SimpleNamespace(source_data_days=lambda *a,**k:days)}):
            result=build_movement_export(cur,[],73,None,start=date(2026,10,19),end=date(2026,10,20),family='1340001')
        sql,params=cur.execute.call_args.args
        self.assertIn(') AND pf.main_article_number=%s',sql)
        self.assertEqual(params,(20,date(2026,10,20),19,date(2026,10,19),'1340001'))
        self.assertEqual(result['dates'],['2026-10-19','2026-10-20'])

    def test_google_date_transport_and_numeric_precision_preserve_values(self):
        from datetime import datetime
        env={'Any':Any,'Decimal':D,'date':date,'datetime':datetime}
        extract('chatgpt_sheet_bridge.py',{'_wire','_apps_script_wire'},env)
        wire=env['_apps_script_wire']
        self.assertEqual(wire(date(2026,10,20)),"'2026-10-20")
        self.assertEqual(wire('2026-10-23T06:30:45.146593Z'),"'2026-10-23T06:30:45.146593Z")
        self.assertEqual(wire('000611338042'),"'000611338042")
        self.assertEqual(wire('2026-99-99'),"'2026-99-99")
        self.assertEqual(wire('24043900000,4029551780'),"'24043900000,4029551780")
        self.assertEqual(wire('=SOURCE_NAME'),"'=SOURCE_NAME")
        self.assertEqual(wire(3316.98),3316.98)
        from price_history_analysis import verify_history_tables
        expected={'current':[['Field','Value'],['POS_Data_Through','2026-10-20'],['GP',D('1110.2380970783202')]]}
        actual=[['Field','Value'],['POS_Data_Through','2026-10-20'],['GP',1110.23809707832]]
        self.assertTrue(verify_history_tables(expected,lambda *a:actual)['pass'])
        actual[2][1]=1110.24
        with self.assertRaises(ValueError):verify_history_tables(expected,lambda *a:actual)

    def test_shutdown_handoff_is_scoped_to_stopped_worker(self):
        import json,socket
        from datetime import datetime,timezone
        cur=MagicMock();cur.rowcount=1;conn=MagicMock();conn.cursor.return_value=cur;ctx=MagicMock();ctx.__enter__.return_value=conn
        env={'json':json,'socket':socket,'datetime':datetime,'timezone':timezone,'API_VERSION':'7.0.541','API_PIPELINE':'p','db_conn':lambda:ctx,'log':lambda *a:None}
        extract('single_service.py',{'requeue_interrupted_pipeline_runs'},env)
        self.assertEqual(env['requeue_interrupted_pipeline_runs']('SERVICE_DEPLOYMENT_SHUTDOWN'),0)
        self.assertEqual(env['requeue_interrupted_pipeline_runs']('SERVICE_DEPLOYMENT_SHUTDOWN',3),1)
        sql,params=cur.execute.call_args.args
        self.assertIn('code_version=%s',sql);self.assertIn("$.worker",sql)
        self.assertEqual(params[-2:],('7.0.541',socket.gethostname()+':3'))
        from publish_recovery import owned_legacy_handoff
        row={'processing_status':'QUEUED','code_version':'7.0.541','detail_json':{'worker':'new:3','worker_instance':'new-owner','recovery_reason':'SERVICE_DEPLOYMENT_SHUTDOWN','requeued_by_code_version':'7.0.540'}}
        self.assertTrue(owned_legacy_handoff(row,'7.0.541','new:3','new-owner'))
        self.assertFalse(owned_legacy_handoff(row,'7.0.541','other:3','new-owner'))
        self.assertFalse(owned_legacy_handoff(row,'7.0.541','new:3','other-owner'))
        row['detail_json']['requeued_by_code_version']='7.0.542'
        self.assertFalse(owned_legacy_handoff(row,'7.0.541','new:3','new-owner'))

    def test_google_current_holds_do_not_leak_legacy_sales_or_ticket_prices(self):
        env={};extract('chatgpt_sheet_bridge.py',{'_protect_current_export'},env)
        row={'ean_upc':'000123','selling_uom':'LB','current_price':99,
             'latest_daily_avg_sold_price':None,'sales_dollars_7d':123,'pos_qty_7d':9,
             'latest_daily_business_date':date(2026,10,19),'company_price_a':8}
        held=env['_protect_current_export']([row],[{'date':date(2026,10,20),'file_id':179}])
        self.assertEqual(len(held),1);self.assertIsNone(row['sales_dollars_7d'])
        self.assertIsNone(row['pos_qty_7d']);self.assertIsNone(row['current_price'])
        self.assertEqual(row['company_price_a'],8)
        good={'ean_upc':'24053300000','selling_uom':'LB','current_price':99,
              'latest_daily_avg_sold_price':D('3.987'),'latest_daily_business_date':date(2026,10,19)}
        env['_protect_current_export']([good],[{'date':date(2026,10,20),'file_id':180}])
        self.assertEqual(good['current_price'],D('3.987'))
        self.assertEqual(good['current_price_source'],'CANONICAL_POS_REALIZED_AVERAGE')

    def test_quantity_authority_and_held_source(self):
        row={'ean_upc':'000123','selling_uom':'LB'}
        obs={'sold_quantity':2,'sales_amount':30,'price_types':{'REG':{}}}
        self.assertIsNone(verified_pos_quantity(row,obs,'2026-10-19')[0])
        self.assertEqual(verified_pos_quantity(row,{**obs,'sold_quantity':D('3.5'),'price_types':{'TOTAL':{}}},'2026-10-19')[0],D('3.5'))
        self.assertEqual(verified_pos_quantity({**row,'ean_upc':'24053300000'},obs,'2026-10-19')[0],2)
        days=[{'file_id':179,'date':date(2026,10,20)},{'file_id':178,'date':date(2026,10,19)}]
        self.assertEqual(eligible_sales_days(days,1),[days[1]])
        self.assertEqual(len(eligible_sales_days([{**days[0],'file_id':180}])),1)

    def performance(self,qty,sales,unit='EA',types=None):
        row={'upc_id':1,'ean_upc':'000123','selling_uom':unit,'publish_batch_id':73}
        day=date(2026,10,19);cur=MagicMock();cur.fetchall.return_value=[row]
        conn=MagicMock();conn.cursor.return_value=cur;ctx=MagicMock();ctx.__enter__.return_value=conn
        env={'date':date,'Any':Any,'Decimal':D,'db_conn':lambda:ctx,'_d':lambda v:D(str(v or 0)),
             '_canonical_sales_days':lambda *a,**k:[{'date':day,'file_id':178}],
             '_select_performance_range_days':lambda *a,**k:(day,day,[{'date':day,'file_id':178}]),
             '_batch_daily_sales_by_price_type':lambda *a:{1:{day:{'sales_amount':sales,'sold_quantity':qty,'price_types':types or {'REG':{}}}}},
             '_performance_range_cost_rows':lambda *a:{},'_performance_cost_for_day':lambda *a:{'cost_per_selling_unit':8},
             '_safe_qty_uom':lambda upc,u:u}
        extract('webapp_v2_runtime.py',{'performance_range'},env)
        return env['performance_range']()

    def test_revenue_survives_zero_missing_and_return_quantities(self):
        for qty,sales in [(0,100),(None,100),(-1,-10)]:
            result=self.performance(qty,sales)
            self.assertEqual(result['summary']['sales_dollars'],sales)
            self.assertIsNone(result['summary']['gp_dollars'])
            self.assertIsNone(result['items'][0]['sold_quantity'])

    def test_weight_count_never_claims_gp_or_price(self):
        result=self.performance(2,30,'LB')
        self.assertEqual(result['summary']['sales_dollars'],30)
        for key in ('sold_quantity','avg_sold_price','gp_dollars'):self.assertIsNone(result['items'][0][key])
        result=self.performance(D('3.5'),30,'LB',{'TOTAL':{}})
        self.assertEqual(result['items'][0]['gp_dollars'],2)

    def test_partial_movement_cost_is_not_total(self):
        row={'posting_date':'2026-10-19','department':'Seafood','movement_type':'551','base_quantity':-1,'base_uom_code':'LB','amount_local_currency':-10,'source_filename':'a'}
        result=summarize_movements({'dates':['2026-10-19'],'rows':[row,{**row,'amount_local_currency':None}]})['by_movement_and_unit'][0]
        self.assertIsNone(result['posted_cost']);self.assertEqual(result['known_partial_posted_cost'],-10)
        self.assertEqual(result['posted_cost_missing_rows'],1);self.assertEqual(result['quantity'],-2)

    def test_current_interior_corruption_fails_readback(self):
        env={'Any':Any,'MYSQL_TABS':{'source':'source','lookup':'lookup','analysis':'analysis','family':'family'},'_col_letters':lambda n:'B','_wire':lambda v:v}
        extract('chatgpt_sheet_bridge.py',{'_validate_readback_once'},env)
        matrix=[['ean_upc','sales'],['000123',10],['000456',20],['000789',30]]
        def read(session,sid,a1):
            if a1=="'current'!A1:B4":return [matrix[0],matrix[1],[456,20],matrix[3]]
            return []
        result=env['_validate_readback_once'](None,'s',73,3,analysis_row_count=3,reader=read,expected_matrices={'current':matrix})
        self.assertFalse(result['pass']);self.assertTrue(any('row 3' in x and 'ean_upc' in x for x in result['failures']))

    def test_unknown_quantities_compare_as_null_and_actions_do_not_forecast(self):
        def reader(args):
            return {'data_available':True,'supported_dates':['2026-10-18','2026-10-19'],'supported_day_count':1,
              'sales_dollars':30,'gp_dollars':None,'sold_quantity_by_uom':{'LB':None},
              '_comparison_rows':[{'upc':'000123','name':'Fish','sales_amount':30,'sold_quantity':None,'gp_dollars':None}]}
        comparison=compare_performance({'supported_days':1},reader)
        self.assertIsNone(comparison['quantity_per_supported_day_by_uom']['LB']['change'])
        result=growth_opportunities({'supported_days':1},reader)
        self.assertIsNone(result['forecast_or_uplift']);self.assertEqual(result['actions'][0]['action'],'RESOLVE_HIGH_REVENUE_EVIDENCE_GAPS')

if __name__=='__main__':unittest.main()
