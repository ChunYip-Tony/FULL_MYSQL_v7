import unittest
from decimal import Decimal
from inventory_family_catalog import rank_page

class FamilyRankingTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'family_id':i,'main_article_number':str(100+i),'family_description':str(i),'matches':[]} for i in range(1,76)]
        self.metrics={i:{'velocity7':Decimal(i),'velocity14':Decimal(76-i),'movement_uom':'LB'} for i in range(1,75)}
    def test_global_rank_before_pagination(self):
        a=rank_page(self.rows,self.metrics)
        b=rank_page(self.rows,self.metrics,cursor=30)
        self.assertEqual([r['family_id'] for r in a['rows']],list(range(74,44,-1)))
        self.assertEqual(a['next_cursor'],'30')
        self.assertFalse(set(r['family_id'] for r in a['rows']) & set(r['family_id'] for r in b['rows']))
        self.assertEqual(rank_page(self.rows,self.metrics,cursor=60)['rows'][-1]['family_id'],75)
    def test_windows_filters_zero_and_unknown(self):
        self.metrics[1]['velocity7']=Decimal(0)
        self.assertEqual(rank_page(self.rows,self.metrics,sort='velocity14')['rows'][0]['family_id'],1)
        self.assertEqual(rank_page(self.rows,self.metrics,status='unknown')['total'],1)
        self.assertEqual(rank_page(self.rows,self.metrics,status='verified')['total'],74)
        self.assertEqual(rank_page(self.rows,self.metrics,unit='EA')['total'],0)
        self.assertEqual(rank_page(self.rows,self.metrics,cursor=60)['rows'][-2]['velocity7'],0)
    def test_missing_evidence_families_remain(self):
        self.assertEqual(rank_page(self.rows,{},cursor=60)['total'],75)
        self.assertEqual(rank_page(self.rows,{},cursor=60)['rows'][-1]['family_id'],75)
    def test_controls_validated(self):
        with self.assertRaises(ValueError):rank_page(self.rows,self.metrics,sort='POS')
if __name__=='__main__':unittest.main()
