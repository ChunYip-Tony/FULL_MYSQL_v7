"""Exercise catalog SQL and pagination against a small relational database."""
import sqlite3
import sys
import types
import unittest

sys.modules.setdefault("db", types.SimpleNamespace(db_conn=None))
from mobile_inventory_catalog import read_catalog


class Cursor:
    def __init__(self, db):
        self.cur = db.cursor()

    def execute(self, sql, params=()):
        self.cur.execute(sql.replace("%s", "?").replace("CURRENT_TIMESTAMP(6)", "CURRENT_TIMESTAMP"), params)

    def fetchone(self):
        return dict(self.cur.fetchone())

    def fetchall(self):
        return [dict(r) for r in self.cur.fetchall()]


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE product_family(family_id INTEGER PRIMARY KEY,main_article_number TEXT,family_description TEXT);
            CREATE TABLE quick_check_current(family_id INTEGER,article_number TEXT,ean_upc TEXT,selling_description TEXT);
            CREATE TABLE article(article_id INTEGER,article_number TEXT,article_description TEXT);
            CREATE TABLE bridge_article_family(family_id INTEGER,article_id INTEGER,mapping_status TEXT,valid_to TEXT);
        """)
        self.db.executemany("INSERT INTO product_family VALUES(?,?,?)", [(i,str(100000+i),f"Item {i}") for i in range(1,246)])
        self.db.execute("UPDATE product_family SET family_description='FRESH SALMON' WHERE family_id=200")
        self.db.execute("UPDATE product_family SET family_description='100% WILD_FISH' WHERE family_id=201")
        self.db.executemany("INSERT INTO quick_check_current VALUES(?,?,?,?)", [(200,'1361740','0024647700000','SALMON BELLY'),(200,'1361740','24645000000','SALMON STEAK')])
        self.db.execute("INSERT INTO article VALUES(1,'9912345','RECEIVING SALMON')")
        self.db.execute("INSERT INTO bridge_article_family VALUES(200,1,'CONFIRMED',NULL)")
        self.cur = Cursor(self.db)

    def tearDown(self):
        self.db.close()

    def test_every_family_reachable_beyond_120_without_duplicates(self):
        ids, cursor = [], 0
        while True:
            page = read_catalog(self.cur,cursor=cursor,limit=30)
            self.assertEqual(page['total'],245)
            ids += [r['family_id'] for r in page['rows']]
            if page['next_cursor'] is None:
                break
            cursor = int(page['next_cursor'])
        self.assertEqual(ids,list(range(1,246)))

    def test_no_oh_or_quick_check_does_not_hide_master_family(self):
        page = read_catalog(self.cur,query='100001')
        self.assertEqual(page['rows'][0]['family_id'],1)
        self.assertEqual(page['rows'][0]['matches'],[])

    def test_salmon_name_upc_and_confirmed_receiving_article(self):
        for query in (' salmon ', 'SALMON BELLY', '0024647700000','9912345'):
            result = read_catalog(self.cur,query=query)
            self.assertEqual([r['family_id'] for r in result['rows']],[200])
            self.assertEqual(len(result['rows'][0]['matches']),2)

    def test_expired_or_unconfirmed_alias_does_not_match(self):
        self.db.execute("UPDATE bridge_article_family SET mapping_status='UNCONFIRMED'")
        self.assertEqual(read_catalog(self.cur,query='9912345')['rows'],[])
        self.db.execute("UPDATE bridge_article_family SET mapping_status='CONFIRMED',valid_to='2000-01-01'")
        self.assertEqual(read_catalog(self.cur,query='9912345')['rows'],[])

    def test_literal_percent_and_underscore(self):
        self.assertEqual(read_catalog(self.cur,query='%')['total'],1)
        self.assertEqual(read_catalog(self.cur,query='_')['total'],1)
        self.assertEqual(read_catalog(self.cur,query="' OR 1=1 --")['total'],0)

    def test_boundaries_and_last_page(self):
        for args in ({'limit':0},{'limit':101},{'cursor':-1},{'query':'a'*81}):
            with self.assertRaises(ValueError):read_catalog(self.cur,**args)
        self.assertIsNone(read_catalog(self.cur,cursor=240,limit=5)['next_cursor'])
        self.assertEqual(read_catalog(self.cur,cursor=999)['rows'],[])


if __name__ == '__main__':
    unittest.main()
