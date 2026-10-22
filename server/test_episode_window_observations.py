"""Regression coverage for positive POS rows previously dropped from episodes."""
import copy
import unittest
from price_history_analysis import HEADERS, HISTORY_CONTRACT, objects, rebuild_retained_analysis


class EpisodeWindowObservationTests(unittest.TestCase):
    def build(self, days, through='2026-10-20', tables=None):
        tables = tables or {k: [v[:]] for k, v in HEADERS.items()}
        member = {
            'upc': '24078500000', 'name': 'Yellow croaker', 'uom': 'LB',
            'cost': {'value': 4.6, 'uom': 'LB', 'source': 'RECEIPT', 'date': through},
            'current': {'price': 7.99, 'type': 'REG'},
            'priceHistory': [{'date': '2026-10-16', 'file_id': 159, 'price': 7.99, 'type': 'REG'}],
            'days': days,
        }
        out, audit = rebuild_retained_analysis(
            tables, [{'items': [{'article': '1341465', 'members': [member]}]}],
            [], [], through, 'MYSQL_BATCH_71;' + HISTORY_CONTRACT,
            {'confirmed_upcs': ['24078500000']},
        )
        return out, objects(out['ANALYSIS_PRICE_EPISODES'])[-1]

    def day(self, date, sales, qty, price=7.99, kind='REG', reason=None):
        return {'date': date, 'sales': sales, 'qty': qty, 'price': price,
                'type': kind, 'reason': reason, 'quantityBasis': 'POS_QTY_WEIGHT', 'valid': True}

    def test_croaker_rounded_price_and_total_do_not_become_zero_performance(self):
        days = [self.day('2026-10-17', 13.18, 2, 6.59),
                self.day('2026-10-18', 0, 0), self.day('2026-10-19', 0, 0),
                self.day('2026-10-20', 64, 8.01, 7.990012484, 'TOTAL', 'PRICE_TYPE_UNVERIFIED')]
        out, e = self.build(days)
        self.assertEqual(e['supported_days'], 4)
        self.assertAlmostEqual(e['sales'], 77.18)
        self.assertAlmostEqual(e['qty'], 10.01)
        self.assertAlmostEqual(e['sales_day'], 19.295)
        self.assertAlmostEqual(e['gp_day'], 7.7835)
        self.assertEqual(e['popularity'], .5)
        self.assertFalse(e['performance_ok'])
        self.assertIn('PRICE_ATTRIBUTION_UNVERIFIED:2/4', e['rationale'])
        tracking = objects(out['ANALYSIS_PRICE_TRACKING'])[0]
        self.assertEqual(tracking['sales_day'], e['sales_day'])
        self.assertEqual(tracking['gp_day'], e['gp_day'])
        self.assertEqual(tracking['status'], 'Unverified')

    def test_mixed_day_keeps_observed_sales_without_claiming_price_effect(self):
        _, e = self.build([self.day('2026-10-17', 15, 2, None, None, 'MIXED_PRICE_DAY')], '2026-10-17')
        self.assertEqual(e['sales'], 15)
        self.assertEqual(e['popularity'], 1)
        self.assertFalse(e['performance_ok'])

    def test_missing_day_is_not_imputed_zero_and_missing_weight_keeps_gp_null(self):
        day = self.day('2026-10-18', 19.99, None, None, 'TOTAL', 'POS_WEIGHT_MISSING')
        _, e = self.build([self.day('2026-10-17', 0, 0), day], '2026-10-19')
        self.assertEqual(e['applied_days'], 3)
        self.assertEqual(e['supported_days'], 2)
        self.assertEqual(e['sales'], 19.99)
        self.assertEqual(e['popularity'], .5)
        self.assertIsNone(e['qty'])
        self.assertIsNone(e['gp_day'])

    def test_clean_price_days_still_qualify_and_rebuild_is_idempotent(self):
        days = [self.day('2026-10-17', 79.9, 10), self.day('2026-10-18', 0, 0)]
        out, e = self.build(days, '2026-10-18')
        self.assertTrue(e['performance_ok'])
        again, _ = self.build(days, '2026-10-18', copy.deepcopy(out))
        self.assertEqual(out, again)


if __name__ == '__main__':
    unittest.main()
