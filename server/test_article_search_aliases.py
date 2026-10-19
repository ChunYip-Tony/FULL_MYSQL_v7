import ast,unittest
from pathlib import Path
from unittest.mock import Mock
from article_search_aliases import article_alias_families
class AliasSearchTests(unittest.TestCase):
 def test_selling_and_sub_article_reach_canonical_family(self):
  cur=Mock();cur.fetchall.return_value=[{'family_id':43,'article_number':'3400533'}]
  self.assertEqual(article_alias_families(cur,'3400533'),{43:['3400533']})
  sql,params=cur.execute.call_args.args;self.assertIn("mapping_status='CONFIRMED'",sql);self.assertIn('valid_to',sql);self.assertEqual(params,('3400533','3400533%'))
 def test_non_identifiers_never_expand(self):
  cur=Mock();self.assertEqual(article_alias_families(cur,"fish' OR 1=1"),{});cur.execute.assert_not_called()
 def test_duplicate_aliases_keep_family_identity(self):
  cur=Mock();cur.fetchall.return_value=[{'family_id':43,'article_number':'1342106'},{'family_id':43,'article_number':'1342108'}]
  self.assertEqual(list(article_alias_families(cur,'13421')),[43])
 def test_numeric_query_sql_placeholders_match_parameters(self):
  # Execute the actual search function with a fake database and real resolver.
  src=ast.parse(Path(__file__).with_name('quick_check_app.py').read_text());fn=next(n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='search_quick_check')
  cur=Mock();cur.fetchall.side_effect=[[{'family_id':43,'article_number':'3400533'}],[{'family_id':43,'ean_upc':'24053300000'}]]
  conn=Mock();conn.cursor.return_value=cur;ctx=Mock();ctx.__enter__=Mock(return_value=conn);ctx.__exit__=Mock(return_value=False)
  ns={'Any':object,'db_conn':lambda:ctx,'_numeric_key':lambda s:s.lstrip('0'),'_annotate_stock_state':lambda r:None}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'search','exec'),ns)
  result=ns['search_quick_check']('3400533',20)
  sql,params=cur.execute.call_args.args;self.assertEqual(sql.count('%s'),len(params));self.assertIn('OR family_id IN (%s)',sql);self.assertEqual(result['results'][0]['matched_article_numbers'],['3400533'])
if __name__=='__main__':unittest.main()
