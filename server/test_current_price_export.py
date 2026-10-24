import ast
from datetime import date
from decimal import Decimal as D
from pathlib import Path
import unittest
from typing import Any

from current_price_export import apply_current_prices


class CurrentPriceExport(unittest.TestCase):
    def row(self):
        return {'upc_id': 1, 'ean_upc': '24052400000', 'selling_uom': 'LB',
                'current_cost_per_selling_unit': D('3.29'),
                'latest_daily_sales_dollars': 0, 'latest_daily_pos_qty': 0,
                'latest_daily_avg_sold_price': None, 'oh_date': '2026-10-22'}

    def ticket(self, price='4.99', day='2026-10-23', kind='REG', fid=201):
        return {'price': D(price), 'date': day, 'type': kind, 'file_id': fid,
                'filename': 'all-price-102326-1800.xls'}

    def pos(self, day='2026-10-22', qty=10, sales=39.9, **kwargs):
        return dict({'upc': '24052400000', 'date': day, 'verified_quantity': qty,
                     'sales_amount': sales, 'price_type': 'REG', 'mapping_status': 'RESOLVED',
                     'department': 'Seafood', 'source_file_id': 196,
                     'coverage_kind': 'DIRECT_SINGLE_DATE'}, **kwargs)

    def resolve(self, tickets=(), pos=()):
        row = self.row()
        apply_current_prices([row], {1: list(tickets)}, list(pos), '2026-10-22')
        return row

    def test_new_list_survives_zero_sales_and_does_not_manufacture_sales(self):
        row = self.resolve([self.ticket()])
        self.assertEqual(row['current_price'], D('4.99'))
        self.assertEqual(row['current_price_source'], 'PRICE_LIST')
        self.assertEqual(row['current_price_asof_date'], date(2026, 10, 23))
        self.assertEqual(row['current_price_filename'], 'all-price-102326-1800.xls')
        self.assertEqual(row['latest_daily_sales_dollars'], 0)
        self.assertIsNone(row['latest_daily_avg_sold_price'])
        self.assertEqual(row['gp_pct_current'], (D('4.99')-D('3.29'))/D('4.99'))

    def test_list_newer_than_pos_wins(self):
        self.assertEqual(self.resolve([self.ticket()], [self.pos()])['current_price'], D('4.99'))

    def test_pos_newer_than_list_uses_actual_revenue_over_quantity(self):
        row = self.resolve([self.ticket(day='2026-10-20')], [self.pos()])
        self.assertEqual(row['current_price'], D('3.99'))
        self.assertEqual(row['current_price_source'], 'CANONICAL_POS_REALIZED_AVERAGE')

    def test_same_day_list_wins(self):
        self.assertEqual(self.resolve([self.ticket(day='2026-10-22')], [self.pos()])['current_price'], D('4.99'))

    def test_latest_file_precedes_priority_across_files(self):
        row = self.resolve([self.ticket('9.99', kind='IN STORE', fid=200), self.ticket()])
        self.assertEqual(row['current_price'], D('4.99'))

    def test_priority_within_snapshot(self):
        for kinds, expected in [(['REG','TPR','SALE','IN STORE'],'IN STORE'),
                                (['REG','TPR','SALE'],'SALE'),(['REG','TPR'],'TPR')]:
            self.assertEqual(self.resolve([self.ticket(kind=k) for k in kinds])['current_price_type'], expected)

    def test_last_positive_pos_survives_later_zero_day(self):
        row = self.resolve(pos=[self.pos('2026-10-12'), self.pos(qty=0, sales=0)])
        self.assertEqual(row['current_price_asof_date'], date(2026, 10, 12))

    def test_partial_intraday_derived_and_unverified_quantity_do_not_set_price(self):
        for bad in [self.pos('2026-10-23'), self.pos(coverage_kind='DERIVED_PERIOD_RESIDUAL'),
                    self.pos(qty=None), self.pos(mapping_status='ITEM_IDENTITY_UNRESOLVED'),
                    self.pos(department='UNASSIGNED_DEPARTMENT')]:
            self.assertIsNone(self.resolve(pos=[bad])['current_price'])

    def test_partial_quantity_day_is_not_reported_as_complete_price(self):
        self.assertIsNone(self.resolve(pos=[self.pos(),self.pos(qty=None)])['current_price'])

    def test_mixed_price_day_is_weighted_and_labeled(self):
        row = self.resolve(pos=[self.pos(sales=40),self.pos(sales=30,price_type='SALE')])
        self.assertEqual(row['current_price'], D('3.5'))
        self.assertEqual(row['current_price_type'], 'MIXED')

    def test_no_family_or_unrelated_upc_allocation(self):
        self.assertIsNone(self.resolve(pos=[self.pos(upc='24952400000')])['current_price'])

    def test_invalid_values_do_not_create_prices(self):
        for price in ['0','-1','NaN','Infinity']:
            self.assertIsNone(self.resolve([self.ticket(price)])['current_price'])

    def test_analysis_exports_source_dates_and_oh_date_without_column_shift(self):
        source=Path(__file__).with_name('chatgpt_sheet_bridge.py')
        tree=ast.parse(source.read_text()); names={'ANALYSIS_COLUMNS','POS_3D_COLUMNS','LATEST_DAILY_COLUMNS'}
        nodes=[n for n in tree.body if (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)) or (isinstance(n,ast.FunctionDef) and n.name=='_build_analysis')]
        env={'Any':Any};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),env)
        row=self.resolve([self.ticket()]);row['quick_check_status']='READY'
        table=env['_build_analysis']([row]);out=dict(zip(*table))
        self.assertEqual(len(table[0]),len(table[1]))
        self.assertEqual(out['oh_date'],'2026-10-22')
        self.assertEqual(out['current_price_source'],'PRICE_LIST')

    def test_history_reference_retains_new_list_without_backfilling_achieved_price(self):
        from price_history_analysis import HEADERS, objects, rebuild_retained_analysis
        row=self.resolve([self.ticket()])
        row.update(main_article_number='1363524', selling_description='WHITE PERCH')
        member={'upc':row['ean_upc'],'name':'WHITE PERCH','uom':'LB',
                'current':{'price':4.99,'type':'REG'},'cost':{},'priceHistory':[],
                'days':[{'date':'2026-10-22','sales':0,'qty':0,'type':'REG',
                         'quantityBasis':'POS_QTY_WEIGHT','valid':True}]}
        tables={k:[v[:]] for k,v in HEADERS.items()}
        output,_=rebuild_retained_analysis(tables,[{'items':[{'article':'1363524','members':[member]}]}],
                                           [],[row],'2026-10-22','TEST',{'confirmed_upcs':[]})
        ref=objects(output['ANALYSIS_ITEM_REFERENCE'])[0]
        self.assertEqual(ref['price'],D('4.99'))
        self.assertEqual(ref['price_source'],'PRICE_LIST')
        self.assertEqual(ref['price_asof_date'],date(2026,10,23))
        self.assertIsNone(objects(output['ANALYSIS_UPC_DAILY'])[0]['price'])


if __name__ == '__main__':
    unittest.main()
