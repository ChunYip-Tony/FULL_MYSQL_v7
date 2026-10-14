import ast
from pathlib import Path
import re
import unittest

# Exercise identity helpers without a live database or model request.
tree = ast.parse(Path(__file__).with_name('yipman_ai.py').read_text())
names = {'_norm_num', '_norm_text', '_item_search_query', '_catalog_search_rows', '_promotion_items_tool'}
module = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
scope = {'re': re, 'Any': object}
exec(compile(module, '<identity helpers>', 'exec'), scope)

class PromotionMatchingTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def search(query, limit):
            self.calls.append(query)
            if query == '9999999':
                return {'results': [{'result_type': 'ARTICLE', 'number': '19999999', 'family_article_number': '55'}]}
            if query == 'missing':
                return {'results': []}
            if query == 'unavailable':
                raise TimeoutError()
            if query == 'ambiguous':
                return {'results': [{'result_type': 'ARTICLE', 'number': '1', 'family_article_number': '11'}, {'result_type': 'ARTICLE', 'number': '2', 'family_article_number': '22'}]}
            if query == '3640365':
                return {'results': [{'result_type': 'FAMILY', 'number': query, 'name': 'SILK SNAPPER'}]}
            return {'results': [{'result_type': 'ARTICLE', 'number': query, 'family_article_number': '1361689'}]}
        scope['search_items'] = search
        scope['search_quick_check'] = lambda query, limit: {'results': [{'ean_upc': query, 'main_article_number': '1361689'}] if query == '24036500000' else []}

    def test_full_promotion_row(self):
        row = 'LV 99 3640365 FRESH SILK SNAP LB 1 新鮮紅鯛 $6.29 $8.99 1 LB Fri,Sat & Sun day only'
        result = scope['_catalog_search_rows'](row)
        self.assertEqual(self.calls, ['3640365'])
        self.assertEqual(result[0]['family_article_number'], '3640365')

    def test_receiving_alias_preserved(self):
        row = scope['_catalog_search_rows']('3407833')[0]
        self.assertEqual(row['result_type'], 'ARTICLE')
        self.assertEqual(row['number'], '3407833')

    def test_upc_fast_path(self):
        self.assertEqual(scope['_catalog_search_rows']('24036500000')[0]['result_type'], 'UPC')
        self.assertEqual(self.calls, [])

    def test_no_partial_numeric_mapping(self):
        self.assertEqual(scope['_catalog_search_rows']('9999999'), [])

    def test_keep_matches_when_other_rows_fail(self):
        result = scope['_promotion_items_tool']({'items': ['3640365', 'missing', 'ambiguous', 'unavailable', '1351626 26/30 SHRIMP $5.99 LB', '1351626 26/30 SHRIMP $10.99 PACK']})
        self.assertEqual([r['status'] for r in result['items']], ['MATCHED', 'NOT_FOUND', 'AMBIGUOUS', 'LOOKUP_UNAVAILABLE', 'MATCHED', 'MATCHED'])
        self.assertEqual(len(result['items']), 6)

    def test_multiple_ids_not_silently_chosen(self):
        self.assertEqual(scope['_item_search_query']('1361689 or 3640365'), '1361689 or 3640365')

if __name__ == '__main__':
    unittest.main()
