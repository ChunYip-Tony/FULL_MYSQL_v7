import unittest
from raw_pages import iter_raw_rows


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.result = []
        self.max_page = 0

    def execute(self, sql, args=()):
        if not sql.startswith('SELECT raw_id'):
            self.result = []  # Caller can safely reuse this cursor for writes.
            return
        sheet, row = args[:2]
        limit = args[-1]
        self.result = sorted(
            (r for r in self.rows if r['sheet_id'] == sheet and
             (r['source_row_number'] > row or
              (len(args) == 5 and r['source_row_number'] == row and r['raw_id'] > args[3]))),
            key=lambda r: (r['source_row_number'], r['raw_id']),
        )[:limit]
        self.max_page = max(self.max_page, len(self.result))

    def fetchall(self):
        result, self.result = self.result, []
        return result


class RawPagingTest(unittest.TestCase):
    def test_boundary_duplicates_header_filter_and_cursor_reuse(self):
        rows = [dict(sheet_id=1, source_row_number=i // 3, raw_id=i, raw_payload=str(i)) for i in range(1509)]
        rows += [dict(sheet_id=2, source_row_number=99, raw_id=9999, raw_payload='other')]
        cur = Cursor(list(reversed(rows)))
        got = []
        for row in iter_raw_rows(cur, 'raw_article_manual', 1, after_row=1, page_size=500):
            got.append(row['raw_id'])
            cur.execute('UPDATE derived_table SET value=1')
        self.assertEqual(got, list(range(6, 1509)))
        self.assertLessEqual(cur.max_page, 500)

    def test_empty_and_exact_full_page(self):
        self.assertEqual(list(iter_raw_rows(Cursor([]), 'raw_sales_by_price_type', 1)), [])
        rows = [dict(sheet_id=1, source_row_number=i, raw_id=i, raw_payload='') for i in range(1000)]
        self.assertEqual(len(list(iter_raw_rows(Cursor(rows), 'raw_sales_by_price_type', 1))), 1000)

    def test_reject_untrusted_identifier_and_bad_limit(self):
        for table, limit in [('raw_article_manual; DROP TABLE x', 500), ('raw_article_manual', 0)]:
            with self.assertRaises(ValueError):
                list(iter_raw_rows(Cursor([]), table, 1, page_size=limit))


if __name__ == '__main__':
    unittest.main()
