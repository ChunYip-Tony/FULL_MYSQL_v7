import unittest
from datetime import date
from inventory_sales import summarize, DESKTOP_SCRIPT

class SalesTests(unittest.TestCase):
    def test_price_weight_and_exposure_days(self):
        page = {'today':date(2026,10,11),'days':[date(2026,9,25),date(2026,10,1),date(2026,10,2),date(2026,10,3),date(2026,10,4),date(2026,10,5),date(2026,10,6),date(2026,10,7),date(2026,10,8),date(2026,10,9),date(2026,10,10)],'items':[]}
        rows=[{'date':'2026-10-10','qty':10,'sales':40,'type':'REG','valid':True},{'date':'2026-10-09','qty':30,'sales':180,'type':'REG','valid':True},{'date':'2026-10-08','qty':0,'sales':0,'type':'REG','valid':True},{'date':'2026-10-07','qty':99,'sales':999,'type':'REG','valid':False},{'date':'2026-10-01','qty':5,'sales':15,'type':'TPR','valid':True},{'date':'2026-10-11','qty':999,'sales':999,'type':'REG','valid':True}]
        m={'upc':'001','name':'Fish','uom':'LB','days':rows};page['items']=[{'members':[m]},{'members':[m]}]
        result=summarize(page,{'seven':{'average':20},'fourteen':{'average':30}})
        self.assertEqual(len(result['members']),1)
        reg,tpr=result['members'][0]['types'];self.assertAlmostEqual(float(reg['seven']['average']),40/3);self.assertEqual(reg['seven']['price'],5.5);self.assertEqual(reg['seven']['days'],3)
        self.assertIsNone(tpr['seven']['average']);self.assertEqual(tpr['fourteen']['average'],5);self.assertEqual(result['movement']['fourteen']['average'],30)
        m['uom']='';self.assertIsNone(summarize(page,{})['members'][0]['types'][0]['seven']['average'])
    def test_both_inventory_surfaces(self):
        self.assertIn('#yd-pi .pirow[data-family]', DESKTOP_SCRIPT)
        self.assertIn('#invRows tr', DESKTOP_SCRIPT)
        self.assertIn('running<2', DESKTOP_SCRIPT)
        self.assertIn('Price-type rows use UPC POS only', DESKTOP_SCRIPT)
        self.assertIn('/v1/app/inventory-sales?family=', DESKTOP_SCRIPT)


class SellingDayTests(unittest.TestCase):
    def test_selling_days_dedup_zero_cost_and_mixed_price(self):
        rows=[{'date':'2026-10-10','qty':2,'sales':10,'type':'SALE','valid':True,'gp':3},
              {'date':'2026-10-09','qty':0,'sales':0,'type':'SALE','valid':True,'gp':0},
              {'date':'2026-10-08','qty':1,'sales':5,'type':'SALE','valid':False,'reason':'COST_OR_UNIT_UNVERIFIED'},
              {'date':'2026-10-07','valid':False,'reason':'MIXED_PRICE_DAY','typeSales':[{'type':'SALE','qty':1,'sales':5,'gp':2}]},
              {'date':'2026-10-11','qty':99,'sales':99,'type':'SALE','valid':True}]
        member={'upc':'001','uom':'PACK','days':rows+[rows[0]]}
        page={'today':'2026-10-11','days':['2026-10-07','2026-10-08','2026-10-09','2026-10-10'],'items':[{'members':[member,member]}]}
        sale=summarize(page,{})['members'][0]['types'][0]
        self.assertEqual(sale['seven']['sellingDays'],3)
        self.assertEqual(sale['seven']['periodDays'],7)
        self.assertEqual(sale['fourteen']['sellingDays'],3)
        self.assertEqual(sale['fourteen']['periodDays'],14)
        self.assertEqual(sale['recent']['sellingDays'],3)
        self.assertEqual(sale['recent']['periodDays'],92)
        self.assertEqual(sale['seven']['days'],3)
        member['uom']=''
        self.assertIsNone(summarize(page,{})['members'][0]['types'][0]['seven']['sellingDays'])

if __name__=='__main__': unittest.main()
