"""Do not let a similar transfer-output name displace evidenced UPC identity."""
import ast
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
import unittest


class SellingArticleAssignmentTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(Path(__file__).with_name('backoffice_runtime.py').read_text())
        names = {'_assign_upc', '_norm_desc', '_fallback_selling_article_compatible', '_d'}
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
        self.ns = dict(Any=Any, Decimal=Decimal, SequenceMatcher=SequenceMatcher,
                       _numeric_key=lambda value: str(value or '').lstrip('0'),
                       manual_selling_by_upc={}, manual_authoritative_fids=set())
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<assignment>', 'exec'), self.ns)
        self.row = dict(family_id=28, ean_upc='24073900000', selling_description='SABA MACKEREL',
                        main_article_number='1341297', article_number='1341297')
        self.main = dict(article_number='1341297', article_description='SABA MACKEREL 400/600 up',
                         lineage_basis='FAMILY_SOURCE_251_252', movement_7d=Decimal('38.454'),
                         article_role='FAMILY_AND_SAP_SELLING_ARTICLE')
        self.related = dict(article_number='2044864', article_description='SABA MACKEREL',
                            lineage_basis='SAP_DOCUMENT_317_318', movement_7d=Decimal('2.98'),
                            article_role='SAP_SELLING_ARTICLE')

    def assign(self, row=None, main=None):
        return self.ns['_assign_upc'](row or self.row, [main or self.main, self.related])

    def test_current_main_identity_beats_transfer_description_similarity(self):
        self.assertEqual(self.assign(), ('1341297', 'CURRENT_UPC_MAIN_ARTICLE_WITH_251_252'))

    def test_confirmed_zero_movement_does_not_erase_identity(self):
        self.assertEqual(self.assign(main={**self.main, 'movement_7d': Decimal(0)})[0], '1341297')

    def test_explicit_manual_authority_still_wins_and_manual_gap_blocks(self):
        self.ns['manual_selling_by_upc'][(28, '24073900000')] = '2044864'
        self.assertEqual(self.assign(), ('2044864', 'ARTICLE_MANUAL_COLUMN_B_TO_D_EXACT'))
        self.ns['manual_selling_by_upc'].clear()
        self.ns['manual_authoritative_fids'].add(28)
        self.assertIsNone(self.assign()[0])

    def test_missing_or_incompatible_evidence_cannot_gain_priority(self):
        for candidate in ({**self.main, 'movement_7d': None},
                          {**self.main, 'lineage_basis': 'RELATED'},
                          {**self.main, 'article_description': 'Fried Service'}):
            self.assertNotEqual(self.assign(main=candidate)[1], 'CURRENT_UPC_MAIN_ARTICLE_WITH_251_252')

    def test_different_current_article_and_service_upc_are_not_forced_to_main(self):
        for row in ({**self.row, 'article_number': '2044864'},
                    {**self.row, 'ean_upc': '24973900000'}):
            self.assertNotEqual(self.assign(row=row)[1], 'CURRENT_UPC_MAIN_ARTICLE_WITH_251_252')


if __name__ == '__main__':
    unittest.main()
