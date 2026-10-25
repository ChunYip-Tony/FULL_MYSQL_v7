import unittest
from unittest.mock import MagicMock, patch
from ai_catalog_research import research_item_catalog


class CatalogResearchTests(unittest.TestCase):
    def run_page(self, rows, args):
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        connection = MagicMock()
        connection.__enter__.return_value.cursor.return_value = cursor
        with patch('ai_catalog_research.db_conn', return_value=connection):
            result = research_item_catalog(args)
        return result, cursor.execute.call_args.args

    def test_pages_preserve_all_states_and_identifiers(self):
        rows = [{'upc_id': i, 'ean_upc': '000123', 'selling_uom': None,
                 'quick_check_status': 'HISTORICAL_ONLY'} for i in range(1, 52)]
        result, (sql, values) = self.run_page(rows, {'query': '', 'cursor': None})
        self.assertEqual(result['returned_count'], 50)
        self.assertEqual(result['next_cursor'], '50')
        self.assertTrue(result['has_more'])
        self.assertFalse(result['history_verified'])
        self.assertEqual(result['results'][0]['ean_upc'], '000123')
        self.assertIsNone(result['results'][0]['selling_uom'])
        self.assertNotIn("quick_check_status=", sql)
        self.assertEqual(values, (0,))
        final, (_, params) = self.run_page(rows[50:], {'query': '', 'cursor': '50'})
        self.assertEqual(params, (50,))
        self.assertIsNone(final['next_cursor'])

    def test_alias_search_is_parameterized_and_bounded(self):
        result, (sql, values) = self.run_page([], {'query': "oyster '", 'cursor': '0'})
        self.assertIn('bridge_article_family', sql)
        self.assertIn('LIMIT 51', sql)
        self.assertNotIn('oyster', sql)
        self.assertEqual(values[1], '%oyster%')
        self.assertEqual(result['returned_count'], 0)

    def test_bad_cursor_fails_before_database(self):
        with patch('ai_catalog_research.db_conn') as db:
            with self.assertRaises(ValueError):
                research_item_catalog({'query': '', 'cursor': '1 OR 1=1'})
            db.assert_not_called()
