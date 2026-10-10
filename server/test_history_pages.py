import sqlite3
import unittest
from history_pages import iter_history_identities


class Cursor:
    def __init__(self, db): self.cur = db.cursor()
    def execute(self, sql, args=()): self.cur.execute(sql.replace('%s', '?'), args)
    def fetchall(self): return [dict(r) for r in self.cur.fetchall()]


class HistoryPagingTest(unittest.TestCase):
    def test_updates_do_not_skip_identities_or_null_descriptions(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE sales_period_observation(ean_upc TEXT, description TEXT, upc_id INTEGER)')
        rows = [(str(i), None if i % 2 else 'name', 1) for i in range(503)]
        db.executemany('INSERT INTO sales_period_observation VALUES(?,?,?)', rows + rows + [(None, 'ignored', 1)])
        cur = Cursor(db)
        checkpoints, result = [], []
        for row in iter_history_identities(cur, 'sales_period_observation', checkpoints.append):
            result.append((row['ean_upc'], row['description']))
            cur.execute('UPDATE sales_period_observation SET upc_id=2 WHERE ean_upc=%s', (row['ean_upc'],))
        self.assertEqual(len(result), 503)
        self.assertEqual(set(result), {(r[0], r[1]) for r in rows})
        self.assertEqual(checkpoints, [0, 250, 500])
        self.assertEqual(db.execute('SELECT COUNT(*) FROM sales_period_observation WHERE upc_id=2').fetchone()[0], 1006)


if __name__ == '__main__': unittest.main()
