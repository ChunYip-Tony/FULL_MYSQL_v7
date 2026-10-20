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
class ConfirmedSellingArticleTests(unittest.TestCase):
 def test_2015950_uses_existing_sea_bass_family(self):
  cur=Mock();cur.fetchall.side_effect=[[],[{'family_id':47,'main_article_number':'1341139'}]]
  self.assertEqual(article_alias_families(cur,'2015950'),{47:['2015950']})
  self.assertEqual(cur.execute.call_args.args[1],('1341139',))
 def test_2015994_reaches_cuttlefish_family(self):
  cur=Mock();cur.fetchall.side_effect=[[],[{'family_id':1,'main_article_number':'1340302'}]]
  self.assertEqual(article_alias_families(cur,'2015994'),{1:['2015994']})
 def test_exact_steak_is_ranked_before_other_family_cuts(self):
  from article_search_aliases import search_alias_priority
  self.assertLess(search_alias_priority('2015950','SEA BASS  STEAK'),search_alias_priority('2015950','CHILLEAN H&G SEA BASS FILLET'))
 def test_unknown_article_has_no_curated_mapping(self):
  from article_search_aliases import confirmed_search_targets
  self.assertEqual(confirmed_search_targets('2015951'),[])
class PackAliasTests(unittest.TestCase):
 def test_confirmed_short_and_long_upcs_find_same_family(self):
  for alias in ['695892380548','6958923805483','695892380551','6958923805513']:
   main='3467080' if '548' in alias else '3467060'
   cur=Mock();cur.fetchall.side_effect=[[],[{'family_id':327,'main_article_number':main}]]
   self.assertIn(alias,article_alias_families(cur,alias)[327])
if __name__=='__main__':unittest.main()
