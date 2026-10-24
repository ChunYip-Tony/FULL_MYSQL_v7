"""Exercise the production SQL builder without database/provider credentials."""
import ast
from pathlib import Path
import sqlite3
import unittest

tree = ast.parse(Path(__file__).with_name('mobile_pricing.py').read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pricing_rows_query')
namespace = {}
exec(compile(ast.Module(body=[function], type_ignores=[]), 'mobile_pricing.py', 'exec'), namespace)
query = namespace['pricing_rows_query']

class FamilyScopeTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE quick_check_current(family_id INTEGER,main_article_number TEXT,ean_upc TEXT,upc_id INTEGER)')
        self.db.executemany('INSERT INTO quick_check_current VALUES(?,?,?,?)', [
            (89,'1361760','24052700000',1),(89,'1361760','24952700000',2),
            (89,'1361760','24545500000',3),(737,'1361601','24060100000',4)])
    def tearDown(self):
        self.db.close()
    def read(self, family='', upcs=None):
        sql, args = query(family, upcs)
        return self.db.execute(sql.replace('%s','?'), args).fetchall()
    def test_family_article_and_internal_id_keep_all_siblings(self):
        for family in ('1361760','89'):
            self.assertEqual({r[2] for r in self.read(family)}, {'24052700000','24952700000','24545500000'})
    def test_requested_upc_path_stays_exact(self):
        self.assertEqual([r[2] for r in self.read(upcs={'24952700000'})], ['24952700000'])
        self.assertEqual(self.read(upcs=set()), [])
    def test_unknown_family_is_not_global_fallback(self):
        self.assertEqual(self.read('9999999'), [])
    def test_unfiltered_browse_preserved(self):
        self.assertEqual(len(self.read()),4)
    def test_invalid_family_never_interpolated(self):
        with self.assertRaises(ValueError):query("1361760' OR 1=1")
    def test_builder_scopes_before_category_evidence(self):
        fn=next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='build_page')
        calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call)]
        scope=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='pricing_rows_query')
        category=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='category_index')
        self.assertLess(scope.lineno, category.lineno)

if __name__=='__main__':unittest.main()
