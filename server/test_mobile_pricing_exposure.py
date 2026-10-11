"""Regression checks for canonical POS zero days and repeated ticket uploads."""
import ast
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

def evidence_module():
    source = Path(__file__).with_name('mobile_pricing.py').read_text()
    tree = ast.parse(source)
    # Isolate the pure evidence functions; these checks need no DB or server.
    names = {'num', 'cost_for_day', 'day_evidence', 'PRIORITY', 'COST_ORDER'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names
             or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets)]
    env = {'Decimal': Decimal}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<mobile pricing evidence>', 'exec'), env)
    return env['day_evidence']

class PriceExposureTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 10, 3)
        self.row = {'selling_uom': 'LB', 'base_uom': 'LB'}
        self.costs = [{'source_type': 'MOVEMENT_RECEIPT_VALUATION', 'business_date': date(2026, 10, 2), 'cost_value': '1.79', 'cost_uom': 'LB'}]
        self.prior = {'date': date(2026, 10, 2), 'type': 'TPR', 'price': Decimal('3.99')}
        self.current_cost = {'value': Decimal('1.79')}
        self.evidence = evidence_module()
    def read(self, snapshots, observation=None):
        return self.evidence(self.row, self.day, observation, snapshots, self.costs, self.current_cost)
    def test_identical_daily_uploads_keep_canonical_zero_day(self):
        history = [self.prior, {**self.prior, 'date': self.day}, {**self.prior, 'date': self.day}]
        for observation in [None, {'sold_quantity': 0, 'sales_amount': 0}]:
            result = self.read(history, observation)
            self.assertTrue(result['valid']); self.assertTrue(result['zero_sale'])
            self.assertEqual((result['qty'], result['sales'], result['price'], result['type']), (0, 0, Decimal('3.99'), 'TPR'))
    def test_changed_ticket_or_type_remains_unverified(self):
        for change in [{'price': Decimal('3.49')}, {'type': 'REG'}]:
            result = self.read([self.prior, {**self.prior, 'date': self.day, **change}])
            self.assertFalse(result['valid']); self.assertEqual(result['reason'], 'PRICE_EXPOSURE_UNVERIFIED')
    def test_intraday_change_then_return_is_not_stable(self):
        result = self.read([self.prior, {**self.prior, 'date': self.day, 'price': Decimal('3.49')}, {**self.prior, 'date': self.day}])
        self.assertFalse(result['valid'])
    def test_first_ticket_does_not_backdate_exposure(self):
        self.assertFalse(self.read([{**self.prior, 'date': self.day}])['valid'])
        self.assertFalse(self.read([])['valid'])
    def test_real_pos_quantity_and_revenue_are_preserved(self):
        observation = {'sold_quantity': 2, 'sales_amount': '8.22', 'price_types': {'TPR': {'sold_quantity': 2, 'sales_amount': '8.22'}}}
        result = self.read([self.prior, {**self.prior, 'date': self.day}], observation)
        self.assertTrue(result['valid']); self.assertEqual(result['price'], Decimal('4.11'))
        self.assertEqual(result['sales'], Decimal('8.22')); self.assertEqual(result['qty'], 2)
    def test_missing_cost_is_not_fabricated(self):
        self.costs = []
        result = self.read([self.prior, {**self.prior, 'date': self.day}])
        self.assertFalse(result['valid']); self.assertEqual(result['reason'], 'COST_OR_UNIT_UNVERIFIED')
    def test_full_carp_observation_week_has_seven_usable_days(self):
        history = [self.prior]
        total = Decimal(0); usable = 0
        for offset in range(7):
            self.day = date(2026, 10, 2 + offset)
            if offset:
                history.append({**self.prior, 'date': self.day})
            qty, sales = (2, '8.22') if offset == 0 else (1, '5.88') if offset == 6 else (0, '0')
            observation = {'sold_quantity': qty, 'sales_amount': sales, 'price_types': {'TPR': {'sold_quantity': qty, 'sales_amount': sales}}} if qty else None
            result = self.read(history, observation)
            usable += result['valid']; total += result['qty'] or 0
        self.assertEqual(usable, 7); self.assertEqual(total, 3)
        self.assertEqual(total / usable, Decimal(3) / 7)

if __name__ == '__main__':
    unittest.main()
