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
    def test_gp_day_zero_negative_and_missing_cost(self):
        page={'today':'2026-10-11','days':['2026-10-08','2026-10-09','2026-10-10'],'items':[{'members':[{'upc':'001','uom':'LB','days':[
            {'date':'2026-10-08','qty':10,'sales':40,'gp':20,'type':'REG','valid':True},
            {'date':'2026-10-09','qty':0,'sales':0,'gp':0,'type':'REG','valid':True},
            {'date':'2026-10-10','qty':5,'sales':10,'gp':-5,'type':'REG','valid':True}
        ]}]}]}
        value=summarize(page,{})['members'][0]['types'][0]['seven']
        self.assertEqual(value['gpDay'],5)
        self.assertEqual(value['days'],3)
        page['items'][0]['members'][0]['days'][0]['gp']=None
        value=summarize(page,{})['members'][0]['types'][0]['seven']
        self.assertIsNone(value['gpDay'])
        self.assertEqual(value['average'],5)
        self.assertIn('GP$/day',DESKTOP_SCRIPT)

    def test_both_inventory_surfaces(self):
        self.assertIn('#yd-pi .pirow[data-family]', DESKTOP_SCRIPT)
        self.assertIn('#invRows tr', DESKTOP_SCRIPT)
        self.assertIn('running<2', DESKTOP_SCRIPT)
        self.assertIn('Price-type rows use UPC POS only', DESKTOP_SCRIPT)
        self.assertIn('/v1/app/inventory-sales?family=', DESKTOP_SCRIPT)

if __name__=='__main__': unittest.main()
