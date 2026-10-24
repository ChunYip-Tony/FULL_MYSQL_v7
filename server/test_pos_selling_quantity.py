import ast, json, unittest
from decimal import Decimal
import inventory_sales
from pathlib import Path
src=ast.parse(Path(__file__).with_name('mobile_pricing.py').read_text())
names={'num','guard_weight_counts'}
mod=ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
ns={'Decimal':Decimal};exec(compile(mod,'mobile_pricing.py','exec'),ns)
class POSUnitTests(unittest.TestCase):
 def test_unconfirmed_item_counts_remain_labeled_estimates(self):
  member={'upc':'99999999999','uom':'LB','cost':{'value':Decimal('4.797476'),'uom':'LB'},'current':None,
   'priceHistory':[{'date':'2026-10-03','type':'REG','price':Decimal('10.99')}],
   'days':[{'date':f'2026-10-{d:02d}','type':'REG','qty':1 if d in (5,7,10) else 0,
    'sales':Decimal({5:'16.38',7:'14.73',10:'15.72'}.get(d,'0')),'valid':True,
    'cost':{'value':Decimal('4.797476'),'uom':'LB'},'typeSales':[]} for d in range(4,11)]}
  page={'today':'2026-10-12','days':[d['date'] for d in member['days']], 'items':[{'members':[member]}]}
  for i in page['items']:
   for m in i['members']:
    m['quantityBasis']='POS_ITEM_COUNT' if m['uom']=='LB' else 'POS_SELLING_UNIT'
  ns['guard_weight_counts'](page['items'])
  result=inventory_sales.summarize(page,{})
  m=next(m for m in result['members'] if m['upc']=='99999999999')
  s=m['types'][0]['seven']
  self.assertAlmostEqual(float(s['quantity']),46.83/10.99)
  self.assertAlmostEqual(float(s['average']),46.83/10.99/7)
  self.assertAlmostEqual(float(s['price']),10.99)
  self.assertAlmostEqual(float(s['gpDay']),(46.83-46.83/10.99*4.797476)/7)
  self.assertEqual(s['estimated'],True)
  self.assertEqual(s['sellingDays'],3)
  self.assertEqual(s['appliedDays'],7)
  self.assertAlmostEqual(float(s['popularityPct']),300/7)
  self.assertTrue(all(not d['valid'] for d in page['items'][0]['members'][0]['days']))
 def test_missing_or_changed_ticket_never_invents_weight(self):
  m={'uom':'LB','quantityBasis':'POS_ITEM_COUNT','priceHistory':[{'date':'2026-10-01','price':Decimal('10.99'),'type':'REG'}, {'date':'2026-10-05','price':Decimal('9.99'),'type':'REG'}], 'days':[{'date':'2026-10-05','qty':1,'sales':Decimal('16.38'),'type':'REG','typeSales':[]}],'current':None}
  ns['guard_weight_counts']([{'members':[m]}])
  self.assertIsNone(m['days'][0]['qty']);self.assertIsNone(m['days'][0]['gp'])
 def test_ea_counts_remain_real_units(self):
  m={'quantityBasis':'POS_SELLING_UNIT','uom':'EA','days':[{'qty':3,'gp':6}]}
  ns['guard_weight_counts']([{'members':[m]}]);self.assertEqual(m['days'][0]['qty'],3)
if __name__=='__main__':unittest.main()

