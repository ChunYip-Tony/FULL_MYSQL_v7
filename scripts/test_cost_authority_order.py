import ast,unittest
from datetime import date
from pathlib import Path
from typing import Any
source=Path(__file__).resolve().parents[1]/'server/phase3.py'
f=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_latest_cost')
class Cursor:
 def __init__(self,receipt=None,report=None,oh=None):self.sources={'MOVEMENT_RECEIPT_VALUATION':receipt,'FROZEN_INVENTORY_OFFICIAL_COST':report,'ON_HAND_EXPLICIT_COST_FALLBACK':oh};self.row=None
 def execute(self,q,args):
  self.row=None
  for source,cost in self.sources.items():
   if source in q and cost is not None:
    self.row={'cost_per_base_uom':cost,'cost_amount':cost,'business_date':date(2026,10,21) if source.startswith('ON_HAND') else date(2026,9,25),'source_type':source,'base_uom':'LB','cost_uom':'LB'};break
 def fetchone(self):return self.row
class Tests(unittest.TestCase):
 def resolve(self,**kw):
  scope={'Any':Any,'confirmed_family_cost':lambda *a:None};exec(compile(ast.Module(body=[f],type_ignores=[]),str(source),'exec'),scope);return scope['_latest_cost'](Cursor(**kw),56)
 def test_receipt_is_first(self):self.assertEqual(self.resolve(receipt=12,report=11,oh=10)['source'],'MOVEMENT_RECEIPT_VALUATION')
 def test_report_beats_newer_oh(self):self.assertEqual(self.resolve(report=11,oh=10)['source'],'FROZEN_INVENTORY_OFFICIAL_COST')
 def test_oh_is_valid_fallback(self):self.assertEqual(self.resolve(oh=10)['source'],'ON_HAND_EXPLICIT_COST_FALLBACK')
 def test_missing_remains_missing(self):self.assertIsNone(self.resolve())
if __name__=='__main__':unittest.main()
