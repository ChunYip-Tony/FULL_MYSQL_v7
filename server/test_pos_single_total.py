import ast
import json
import re
import sys
import types
import unittest
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

source = ast.parse(Path(__file__).with_name('phase3.py').read_text())
names = {'_process_sales', '_j', '_text', '_id', '_num', '_norm_header'}
module = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
ns = {'Any': object, 'Decimal': Decimal, 'InvalidOperation': InvalidOperation, 'json': json, 're': re,
      'SALES_COLS': {'REG': ('E', 'F'), 'IN STORE': ('G', 'H'), 'TPR': ('I', 'J'), 'SALE': ('K', 'L')},
      'DEPARTMENT_REGISTRY': {'400': 'SEAFOOD'}, 'SEAFOOD_DEPT_CODE': '400',
      '_department_from_pos_section': lambda a: '400' if a in ('400', '401') else None,
      'article_manual_pos_alias_index': lambda cur: {}, '_find_pos_upc_id': lambda *args: 1,
      '_find_upc_id': lambda *args: 1, '_issue': lambda *args, **kwargs: None}
exec(compile(module, 'phase3.py', 'exec'), ns)

class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sales = {}
    def execute(self, sql, args):
        if 'INSERT INTO sales_period_observation' in sql:
            self.sales[(args[1], args[3], args[11])] = args
    def fetchall(self):
        return [{'sheet_id': 160}]

def ingest(rows, cursor=None):
    cur = cursor or Cursor(rows)
    raw = types.ModuleType('raw_pages')
    raw.iter_raw_rows = lambda *args: iter(rows)
    sys.modules['raw_pages'] = raw
    ns['_process_sales'](cur, 46, {'file_id': 149, 'original_filename': 'sf-sales-101126.xls',
        'coverage_start_date': date(2026, 10, 11), 'coverage_end_date': date(2026, 10, 11)})
    return cur

class SingleTotalTests(unittest.TestCase):
    def test_weight_amount_and_separate_item_count(self):
        rows = [{'raw_id': i, 'source_row_number': i, 'raw_payload': p} for i,p in enumerate([
            {'A': 'Item Single Total by Sub-department'}, {'A': 400.0, 'B': 'Fish'},
            {'A': 24052700000.0, 'C': 'FRESH CATFISH', 'H': 52.06, 'I': 207.73, 'K': 10.0},
            {'C': 'Net Sales', 'H': 52.06, 'I': 207.73},
            {'G': 'Grand Total', 'H': 52.06, 'I': 207.73}], 1)]
        cur = ingest(rows)
        self.assertEqual(len(cur.sales), 1)
        record = next(iter(cur.sales.values()))
        self.assertEqual(record[11], 'TOTAL')
        self.assertEqual(record[13], Decimal('52.06'))
        self.assertEqual(record[12], Decimal('207.73'))
        ingest(rows, cur)
        self.assertEqual(len(cur.sales), 1)

    def test_existing_price_type_layout(self):
        rows = [{'raw_id':i, 'source_row_number':i, 'raw_payload':p} for i,p in enumerate([
            {'A':'Item Sales by Price Type by Sub-department'}, {'A':400.0,'B':'Fish'},
            {'A':24052700000.0,'B':'FRESH CATFISH','E':19.95,'F':5}],1)]
        cur=ingest(rows)
        self.assertEqual(next(iter(cur.sales.values()))[11], 'REG')
        self.assertEqual(next(iter(cur.sales.values()))[13], Decimal('5'))

    def test_actual_weight_survives_mobile_guard(self):
        src=ast.parse(Path(__file__).with_name('mobile_pricing.py').read_text())
        mod=ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in {'num','guard_weight_counts'}],type_ignores=[])
        env={'Decimal':Decimal};exec(compile(mod,'mobile_pricing.py','exec'),env)
        day={'quantityBasis':'POS_QTY_WEIGHT','qty':Decimal('52.06'),'sales':Decimal('207.73'),'gp':Decimal('67.6886')}
        member={'quantityBasis':'POS_ITEM_COUNT','uom':'LB','days':[day]}
        env['guard_weight_counts']([{'members':[member]}])
        self.assertEqual(day['qty'], Decimal('52.06'))
        self.assertNotIn('posItemCount', day)

if __name__ == '__main__':
    unittest.main()
