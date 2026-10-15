"""Regression cases found by the 500-question seafood operations evaluation."""
import sys
import types
import unittest
import ast
import re
import json
from pathlib import Path
from typing import Any
from datetime import date
from decimal import Decimal
from unittest.mock import patch, Mock

from fisherman_weekly_usage import weekly_usage, promotion_schedule
import test_ai_sales_dates as sales_dates


class ItemSalesSelectionTest(unittest.TestCase):
    def setUp(self):
        self.helper = sales_dates.SalesDateTests()
        self.helper.setUp()
        self.result = self.helper.result
        self.ai = self.helper.ai

    def test_latest_n_uses_supported_days_instead_of_calendar_guess(self):
        start, end, days = self.helper.select(self.helper.days, None, None, latest_supported_day_count=10)
        self.assertEqual((start.day, end.day, len(days)), (1, 13, 10))
        tool, performance = self.ai(self.result())
        tool({'item_query': '24053300000', 'supported_days': 14})
        self.assertEqual(performance.call_args.kwargs['latest_supported_day_count'], 14)

    def test_live_tilapia_does_not_include_fresh_family_members(self):
        result = self.result()
        result['items'] = [
            {'upc': '24060200000', 'name': 'LIVE TILAPIA', 'sold_quantity': 58.56, 'sales_amount': 555.82, 'qty_uom': 'LB'},
            {'upc': '24053500000', 'name': 'FRESH TILAPIA', 'sold_quantity': 63.26, 'sales_amount': 300, 'qty_uom': 'LB'},
            {'upc': '24960200000', 'name': 'LIVE TILAPIA(Fried Service)', 'sold_quantity': 17.8, 'sales_amount': 100, 'qty_uom': 'LB'}]
        tool, _ = self.ai(result)
        out = tool({'item_query': 'live tilapia'})
        self.assertEqual(out['matched_item_count'], 1)
        self.assertEqual(out['sold_quantity_by_uom'], {'LB': Decimal('58.56')})

    def test_broad_tilapia_asks_instead_of_summing_variants(self):
        result = self.result()
        result['items'] += [{'upc': '24060200000', 'name': 'LIVE TILAPIA', 'qty_uom': 'LB'}]
        tool, _ = self.ai(result)
        out = tool({'item_query': 'tilapia'})
        self.assertTrue(out['needs_details'])
        self.assertNotIn('sold_quantity_by_uom', out)
        self.assertEqual({x['number'] for x in out['options']}, {'24053300000', '24060200000'})


class WeeklyQuickCheckTest(unittest.TestCase):
    def call(self, query='24060200000', unit=None, count=3, weekend=False, members=None):
        rows = members or [
            {'upc_id': 1, 'ean_upc': '24060200000', 'selling_uom': 'LB'},
            {'upc_id': 2, 'ean_upc': '24960200000', 'selling_uom': 'LB'},
            {'upc_id': 3, 'ean_upc': '24053500000', 'selling_uom': 'LB'},
            {'upc_id': 4, 'ean_upc': '24560200000', 'selling_uom': 'PACK'}]
        class Cursor:
            def execute(self, sql, args):
                self.members = 'SELECT * FROM quick_check_current' in sql
            def fetchall(self):
                return rows if self.members else [{'family_id': 1, 'main_article_number': '1361602'}]
            def close(self): pass
        class Conn:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self, **kwargs): return Cursor()
        runtime = types.SimpleNamespace(db_conn=Conn,
            _canonical_sales_days=lambda cur, limit: [{'date': date(2026, 10, 13)}],
            _daily_sales_by_price_type=lambda cur, upc_id, supported: {
                date(2026, 10, 13): {'price_types': {'REG': {'sold_quantity': upc_id * 10, 'sales_amount': upc_id * 50}}}},
            _safe_qty_uom=lambda upc, unit: unit)
        with patch.dict(sys.modules, {'webapp_v2_runtime': runtime}):
            return weekly_usage({'start_date': '2026-10-16', 'end_date': '2026-10-22', 'items': [{
                'article_or_upc': query, 'name': 'Fish', 'selling_unit': unit,
                'weekend_only': weekend, 'promotion_applies': count != 0, 'promotion_days': count}]})

    def test_three_days_not_replaced_by_full_week(self):
        row = self.call()['items'][0]
        self.assertEqual((row['regular_days'], row['promotion_days']), (4, 3))
        self.assertIsNone(row['promotion_dates'])
        self.assertEqual(row['total'], Decimal(300))

    def test_null_or_guessed_ea_uses_verified_lb(self):
        for unit in (None, 'EA'):
            row = self.call(unit=unit)['items'][0]
            self.assertEqual(row['unit'], 'LB')
            self.assertEqual(row['total'], Decimal(300))
        self.assertIn('not used or converted', row['unit_note'])

    def test_live_upc_includes_service_not_fresh_or_pack(self):
        row = self.call()['items'][0]
        self.assertEqual({m['upc'] for m in row['members']}, {'24060200000', '24960200000'})

    def test_short_upc_uses_verified_each(self):
        row = self.call(query='4843', members=[{'upc_id': 1, 'ean_upc': '4843', 'selling_uom': 'EA'}])['items'][0]
        self.assertEqual(row['unit'], 'EA')
        self.assertEqual(row['total'], Decimal(100))

    def test_family_mixed_units_needs_choice(self):
        row = self.call(query='1361602')['items'][0]
        self.assertEqual(row['status'], 'SELLING_UNIT_NEEDS_CONFIRMATION')
        self.assertEqual(row['available_units'], ['LB', 'PACK'])
        self.assertNotIn('total', row)

    def test_zero_and_seven_days(self):
        self.assertEqual(self.call(count=0)['items'][0]['total'], Decimal(210))
        self.assertEqual(self.call(count=7)['items'][0]['total'], Decimal(420))

    def test_weekend_dates_are_preserved(self):
        row = self.call(weekend=True)['items'][0]
        self.assertEqual(row['promotion_dates'], ['2026-10-16', '2026-10-17', '2026-10-18'])

    def test_invalid_or_conflicting_counts_are_rejected(self):
        for count in (-1, 8, True, 3.5):
            with self.assertRaises(ValueError):
                self.call(count=count)
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            promotion_schedule('2026-10-16', '2026-10-22', {'weekend_only': True, 'promotion_days': 7})


class StockFlowScopeTest(unittest.TestCase):
    def setUp(self):
        class Cursor:
            def execute(self, sql, args=None):
                self.sql = sql
            def fetchall(self):
                if 'MAX(main_article_number)' in self.sql:
                    return [{'family_id': 1, 'family_article': '1361571', 'family_name': 'Pompano', 'family_movement_7d': 570, 'family_movement_uom': 'LB'}]
                return []
            def close(self): pass
        class Conn:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self, **kwargs): return Cursor()
        events = [{'posting_date': date(2026, 10, 13), 'receipt_quantity': 200, 'receipt_uom': 'LB'},
                  {'posting_date': date(2026, 10, 6), 'receipt_quantity': 200, 'receipt_uom': 'LB'}]
        ns = {'Any': Any, 'Decimal': Decimal, 'db_conn': Conn,
              'completed_through_date': lambda: date(2026, 10, 14),
              'source_data_days': lambda cur, source, **kwargs: [{'date': date(2026, 10, d)} for d in range(8, 15)] if source == 'movement' else [],
              '_family_receipt_events_bulk': lambda *args, **kwargs: {1: events},
              '_delivery_pattern': lambda *args, **kwargs: {},
              '_published_family_oh_fallback': lambda rows: {'quantity': 355, 'uom': 'LB'},
              '_d': lambda value: Decimal(str(value or 0))}
        sales_dates.extract('backoffice_runtime.py', {'yipman_best_sellers'}, ns)
        self.flow = ns['yipman_best_sellers']

    def test_department_watch_keeps_qualification_filter(self):
        self.assertEqual(self.flow()['rows'], [])

    def test_specific_item_returns_even_below_watch_threshold(self):
        out = self.flow(family_article='1361571')
        row = out['rows'][0]
        self.assertFalse(row['over_receiving'])
        self.assertEqual(row['family_receipt_7d_qty'], Decimal(200))
        self.assertEqual(row['family_group_movement_7d'], Decimal(570))
        self.assertEqual(len(row['family_receipt_history']), 2)
        self.assertEqual(len(out['movement_dates_7d']), 7)

    def test_unmatched_family_does_not_fall_back_to_department(self):
        self.assertEqual(self.flow(family_article='9999999')['rows'], [])


class PriceTypeHistoryTest(unittest.TestCase):
    def setUp(self):
        ns = {'Any': Any, 'Decimal': Decimal}
        sales_dates.extract('webapp_v2_runtime.py', {'_summarize_price_types'}, ns)
        self.summarize = ns['_summarize_price_types']
        self.trend = {'rows': [
            {'date': date(2026, 10, 10), 'price_types': [
                {'price_type': 'REG', 'sold_quantity': 10, 'sales_amount': 50},
                {'price_type': 'TPR', 'sold_quantity': 20, 'sales_amount': 80}]},
            {'date': date(2026, 10, 11), 'price_types': [
                {'price_type': 'TOTAL', 'sold_quantity': 30, 'sales_amount': 120}]},
            {'date': date(2026, 10, 12), 'price_types': [
                {'price_type': 'REG', 'sold_quantity': 0, 'sales_amount': 0}]}]}

    def test_tpr_and_total_do_not_become_sale(self):
        out = {r['price_type']: r for r in self.summarize(self.trend, Decimal(2))}
        self.assertEqual(set(out), {'REG', 'TPR', 'TOTAL'})
        self.assertEqual(out['REG']['observed_type_days'], 2)
        self.assertEqual(out['REG']['velocity_per_observed_type_day'], Decimal(5))
        self.assertEqual(out['TPR']['velocity_per_observed_type_day'], Decimal(20))

    def test_current_cost_gp_is_computed_with_type_day_denominator(self):
        out = {r['price_type']: r for r in self.summarize(self.trend, Decimal(2))}
        self.assertEqual(out['REG']['gp_per_observed_type_day_at_current_cost'], Decimal(15))
        self.assertEqual(out['TPR']['gp_per_observed_type_day_at_current_cost'], Decimal(40))
        self.assertEqual(out['REG']['average_sold_price'], Decimal(5))

    def test_missing_cost_withholds_gp_without_dropping_sales(self):
        out = self.summarize(self.trend, None)
        self.assertTrue(all(r['gp_dollars_at_current_cost'] is None for r in out))
        self.assertTrue(any(r['sales_dollars'] > 0 for r in out))

    def test_no_records_returns_no_price_types(self):
        self.assertEqual(self.summarize({'rows': []}, Decimal(2)), [])


class PriceAdviceScopeTest(unittest.TestCase):
    def setUp(self):
        self.ns = {'Any': Any}
        sales_dates.extract('yipman_ai.py', {'_norm_num', '_filter_item_price_suggestions', '_item_price_decisions'}, self.ns)
        self.candidates = [{'number': '24060200000', 'name': 'Live Tilapia', 'family_article_number': '1361602'}]
        self.rows = [
            {'upc': '24060200000', 'family_article_number': '1361602', 'actionable': False, 'suggested_price': None, 'final_tpr_decision': 'NO_TPR_ACTION'},
            {'upc': '24960200000', 'family_article_number': '1361602', 'actionable': False, 'suggested_price': None},
            {'upc': '24053500000', 'family_article_number': '1361602', 'actionable': True, 'suggested_price': 5.49},
            {'upc': '24560200000', 'family_article_number': '1361602', 'actionable': True, 'suggested_price': 10.99}]

    def test_same_family_price_advice_excludes_fresh_and_package_variants(self):
        out = self.ns['_filter_item_price_suggestions'](self.rows, self.candidates)
        self.assertEqual({r['upc'] for r in out}, {'24060200000', '24960200000'})

    def test_no_action_for_exact_upc_cannot_become_sweet_spot_recommendation(self):
        out = self.ns['_item_price_decisions'](self.candidates, self.rows, {})[0]
        self.assertFalse(out['can_recommend_new_price_now'])
        self.assertIsNone(out['supported_price_for_dated_review'])
        self.assertEqual(out['policy_decision'], 'NO_TPR_ACTION')

    def test_stale_candidate_is_only_a_dated_review(self):
        rows = [{'upc': '24060200000', 'actionable': True, 'suggested_price': 9.99, 'final_tpr_decision': 'START_TPR'}]
        out = self.ns['_item_price_decisions'](self.candidates, rows, {'refreshing': True})[0]
        self.assertFalse(out['can_recommend_new_price_now'])
        self.assertEqual(out['supported_price_for_dated_review'], 9.99)
        fresh = self.ns['_item_price_decisions'](self.candidates, rows, {'refreshing': False})[0]
        self.assertTrue(fresh['can_recommend_new_price_now'])


class ToolSchemaTest(unittest.TestCase):
    def test_calculation_respects_ui_or_explicit_reply_language(self):
        ns = {'re': re}
        sales_dates.extract('yipman_ai.py', {'_calculation_requires_translation'}, ns)
        translate = ns['_calculation_requires_translation']
        self.assertTrue(translate('Estimate usage\nReply in Cantonese.'))
        self.assertTrue(translate('用廣東話估計今星期用量'))
        self.assertTrue(translate('Estimate usage in Spanish.'))
        self.assertFalse(translate('Estimate usage\nReply in English.'))

    def test_translated_calculation_finishes_through_model_without_recalculating(self):
        post = Mock(side_effect=[
            {'output': [{'type': 'function_call', 'name': 'estimate_weekly_usage', 'arguments': '{}', 'call_id': 'call-1'}]},
            {'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': '每週估計用量：100 LB'}]}]}])
        handler = Mock(return_value={'calculation_answer': 'Weekly usage: 100 LB'})
        ns = {'Any': Any, 're': re, 'json': json,
              '_check_rate_limit': lambda key: None, '_quick_order_question': lambda *args: None,
              '_quick_daily_answer': lambda *args: None, '_quick_quantity_answer': lambda *args: None,
              '_safe_history': lambda value: [], '_instructions': lambda: 'Use verified quantities.',
              'AI_REVISION': 'TEST', 'MAX_MESSAGE_CHARS': 1600, 'MAX_TOOL_ROUNDS': 5, 'DEFAULT_MODEL': 'test', 'TOOLS': [],
              '_TOOL_HANDLERS': {'estimate_weekly_usage': handler}, '_post_responses': post,
              '_compact_json': json.dumps}
        sales_dates.extract('yipman_ai.py', {'chat', '_calculation_requires_translation', '_output_text'}, ns)
        out = ns['chat']('Estimate usage\nReply in Cantonese.')
        self.assertEqual(out['answer'], '每週估計用量：100 LB')
        self.assertEqual(post.call_count, 2)
        handler.assert_called_once()

    def catalog(self, rows):
        ns = {'Any': Any, '_item_search_query': lambda value: value,
              'search_quick_check': lambda *args: {'results': rows},
              'search_items': Mock(return_value={'results': []})}
        sales_dates.extract('yipman_ai.py', {'_catalog_search_rows', '_norm_num', '_norm_text'}, ns)
        return ns['_catalog_search_rows'], ns['search_items']

    def test_short_upc_uses_exact_quick_check_instead_of_article_path(self):
        catalog, article_search = self.catalog([{'ean_upc': '4843', 'selling_description': 'Prawn', 'company_price_a': 29.99}])
        row = catalog('4843')[0]
        self.assertEqual(row['number'], '4843')
        self.assertEqual(row['company_price_a'], 29.99)
        article_search.assert_not_called()

    def test_named_live_product_excludes_fresh_and_service_aliases(self):
        catalog, _ = self.catalog([
            {'ean_upc': '24053500000', 'selling_description': 'FRESH TILAPIA'},
            {'ean_upc': '24960200000', 'selling_description': 'LIVE TILAPIA(Fried Service)'},
            {'ean_upc': '24060200000', 'selling_description': 'LIVE TILAPIA'}])
        self.assertEqual([r['number'] for r in catalog('live tilapia')], ['24060200000'])

    def test_article_falls_back_to_confirmed_bridge(self):
        catalog, article_search = self.catalog([])
        article_search.return_value = {'results': [{'result_type': 'ARTICLE', 'number': '1342107', 'family_article_number': '1342107'}]}
        self.assertEqual(catalog('1342107')[0]['number'], '1342107')
        article_search.assert_called_once()

    def test_ai_uses_same_wrapped_pricing_policy_as_app_api(self):
        published = Mock(return_value={'rows': [], 'contract_version': 'SHARED_POLICY'})
        ns = {'Any': Any}
        sales_dates.extract('yipman_ai.py', {'_published_pricing_review'}, ns)
        with patch.dict(sys.modules, {'api': types.SimpleNamespace(backoffice_cached_pricing_review=published)}):
            out = ns['_published_pricing_review']('FROZEN')
        self.assertEqual(out['contract_version'], 'SHARED_POLICY')
        published.assert_called_once_with(category='FROZEN', limit=1000)

    def test_item_search_preserves_company_prices_without_cost(self):
        ns = {'Any': Any,
              '_item_search_query': lambda value: value,
              'search_quick_check': lambda *args: {'results': [{
                  'ean_upc': '24953300000', 'selling_description': 'Tilapia Fried Service',
                  'selling_uom': 'LB', 'current_price': 4.99,
                  'company_price_a': 4.99, 'company_price_b': 3.99, 'company_price_c': 3.69}]}}
        sales_dates.extract('yipman_ai.py', {'_item_tool', '_catalog_search_rows'}, ns)
        row = ns['_item_tool']({'query': '24953300000'})['results'][0]
        self.assertEqual((row['company_price_a'], row['company_price_b'], row['company_price_c']), (4.99, 3.99, 3.69))
        self.assertNotIn('current_cost_per_selling_unit', row)

    def test_strict_object_schemas_require_exact_properties(self):
        tree = ast.parse(Path(__file__).with_name('yipman_ai.py').read_text())
        schema = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TOOLS' for t in node.targets))
        def check(value):
            if isinstance(value, dict):
                if value.get('type') == 'object':
                    self.assertEqual(set(value['required']), set(value['properties']))
                    self.assertFalse(value['additionalProperties'])
                for item in value.values(): check(item)
            elif isinstance(value, list):
                for item in value: check(item)
        check(schema)


if __name__ == '__main__':
    unittest.main()
