"""POS rebuild scope preserves rolling metrics, family siblings and full fallback."""
import ast
from datetime import date
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / 'server' / 'phase3.py'
node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == '_routine_upload_quick_check_scope')
ns = {}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), ns)
select = ns[node.name]

def product(uid, family=None, status='HISTORICAL_ONLY', **fields):
    return dict(upc_id=uid, ean_upc=str(uid), article_id=uid, family_id=family or uid,
                selling_uom='LB', base_uom='LB', base_qty_per_selling_unit=1,
                quick_check_status=status, **fields)

class Cursor:
    def __init__(self, previous, sales=(), kinds=('sales_by_price_type',), affected=()):
        self.previous, self.sales, self.kinds = previous, sales, kinds
        self.calls = []; self.affected = affected
    def execute(self, sql, args=None):
        self.calls.append((sql, args))
        self.rows = ([dict(source_type=x) for x in self.kinds] if 'source_type FROM' in sql else
                     self.sales if 'sales_period_observation' in sql else [dict(family_id=f) for f in self.affected] if 'SELECT DISTINCT family_id' in sql else self.previous)
    def fetchall(self):
        return self.rows

class Tests(unittest.TestCase):
    def run_scope(self, products, previous=None, sales=(), kinds=('sales_by_price_type',), days=None, affected=()):
        cur = Cursor(products if previous is None else previous, sales, kinds, affected)
        rows = select(cur, 69, products, [date(2026, 9, 21)] if days is None else days)
        return rows, cur
    def test_source_types_and_bootstrap_require_full_rebuild(self):
        for kinds in [('price_list',), ('sales_by_price_type', 'article_manual'), ()]:
            self.assertIsNone(self.run_scope([product(1)], kinds=kinds)[0])
        self.assertIsNone(self.run_scope([product(1)], previous=[])[0])
        self.assertIsNone(self.run_scope([product(1)], days=[])[0])
    def test_sales_and_siblings_refresh_cold_family_preserved(self):
        products = [product(1, 10), product(2, 10), product(3, 20)]
        rows, cur = self.run_scope(products, sales=[dict(upc_id=1, ean_upc='1')])
        self.assertEqual([r['upc_id'] for r in rows], [1, 2])
        self.assertFalse(any(sql.startswith('DELETE') for sql, _ in cur.calls))
        self.assertEqual(cur.calls[2][1], (date(2026, 9, 21), 69))
    def test_previous_operational_items_refresh_when_last_sale_ages_out(self):
        products = [product(1, status='READY'), product(2, status='QA_HOLD'), product(3)]
        self.assertEqual([p['upc_id'] for p in self.run_scope(products)[0]], [1, 2])
    def test_raw_lineage_and_new_products_are_included(self):
        products = [product(1), product(2), product(3)]
        rows, _ = self.run_scope(products, previous=products[:2], sales=[dict(upc_id=None, ean_upc='2')])
        self.assertEqual([p['upc_id'] for p in rows], [2, 3])
    def test_mapping_uom_changes_and_removed_mapping_siblings(self):
        products = [product(1, 10), product(2, 20)]
        old = [dict(products[0], family_id=20), products[1], product(4, 10)]
        rows, cur = self.run_scope(products, previous=old)
        self.assertEqual(len(rows), 2)
        self.assertIn(('DELETE FROM quick_check_current WHERE upc_id=%s', (4,)), cur.calls)
        old = [dict(products[0], base_qty_per_selling_unit=2), products[1]]
        self.assertEqual([p['upc_id'] for p in self.run_scope(products, previous=old)[0]], [1])
    def test_cold_catalog_does_not_enter_heavy_calculator(self):
        products = [product(i, (i-1)//2+1) for i in range(1, 5463)]
        rows, _ = self.run_scope(products, sales=[dict(upc_id=i, ean_upc=str(i)) for i in range(1, 111)])
        self.assertEqual(len(rows), 110)
        self.assertEqual(len(products), 5462)
    def test_movement_and_oh_cover_affected_families(self):
        products = [product(1, 10), product(2, 10), product(3, 20)]
        for kinds in [('movement',), ('on_hand',), ('sales_by_price_type', 'movement', 'on_hand')]:
            rows, _ = self.run_scope(products, kinds=kinds, affected=[10])
            self.assertEqual([p['upc_id'] for p in rows], [1, 2])
    def test_existing_stock_refreshes_even_without_recent_sales(self):
        rows, _ = self.run_scope([product(1, current_oh=0), product(2, current_oh=-2), product(3)])
        self.assertEqual([p['upc_id'] for p in rows], [1, 2])
    def test_existing_authoritative_calculator_and_publish_guard_retained(self):
        tree = ast.parse(source.read_text())
        rebuild = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'rebuild_quick_check')
        text = ast.get_source_segment(source.read_text(), rebuild)
        self.assertIn('products = scoped', text)
        self.assertIn('_sales_metrics(cur, upc_id, pos_days_7', text)
        self.assertIn('_latest_cost(cur, family_id)', text)
        self.assertIn('SAVEPOINT before_quick_check_publish', source.read_text())
        self.assertIn('ROLLBACK TO SAVEPOINT before_quick_check_publish', source.read_text())

if __name__ == '__main__':
    unittest.main()
