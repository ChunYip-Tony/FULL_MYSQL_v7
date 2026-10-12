import unittest
from datetime import date
from decimal import Decimal
from family_movement_read import summarize_history
D=date(2026,10,10);days=[{'date':date(2026,10,9),'file_id':1},{'date':D,'file_id':2}]
def row(raw,qty,unit='LB',kind='251'):
    return {'file_id':2,'raw_id':raw,'posting_date':D,'movement_type':kind,'base_quantity':qty,'base_uom_code':unit}
class Tests(unittest.TestCase):
    def test_sale_return_and_duplicates(self):
        r=row(1,-10);v=summarize_history([r,r,row(2,2,kind='252')],days)
        self.assertEqual(v['quantity'],8);self.assertEqual(v['supported_day_count'],2);self.assertEqual(v['rows'][0]['sold_quantity'],0)
    def test_no_evidence_not_zero(self):
        self.assertIsNone(summarize_history([],days))
    def test_other_movements_excluded(self):
        self.assertIsNone(summarize_history([row(1,-99,kind='317')],days))
    def test_invalid_units_quantity_and_net_returns_blocked(self):
        for rows in [[row(1,-1),row(2,-2,'EA')],[row(1,None)],[row(1,'NaN')],[row(1,2,kind='252')]]:
            self.assertEqual(summarize_history(rows,days)['status'],'BLOCKED')
    def test_confirmed_entry_authority(self):
        r={**row(1,-2,'CS'),'entry_quantity':-20,'entry_uom_code':'LB'}
        authority={'movement_quantity_basis':'ENTRY','operational_uom_code':'LB'}
        self.assertEqual(summarize_history([r],days,authority)['quantity'],20)
        r['entry_uom_code']='EA';self.assertEqual(summarize_history([r],days,authority)['status'],'BLOCKED')
    def test_outside_window(self):
        r=row(1,-10);r['posting_date']=date(2026,10,11)
        self.assertIsNone(summarize_history([r],days))
if __name__=='__main__': unittest.main()
