import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import patch
from typing import Any
from inventory_sales import build_summary

def _receipt_events_summary(events: list[dict[str,Any]]) -> dict[str,Any]:
    """Summarize one physical-receipt day without changing completed-day semantics."""
    positive=[
        x for x in (events or [])
        if x.get("receipt_quantity") is not None
        and _d(x.get("receipt_quantity")) > 0
    ]
    if not positive:
        return {
            "date":None,
            "quantity":None,
            "uom":None,
            "quantity_basis":None,
            "event_count":0,
            "article_numbers":[],
            "events":[],
        }

    dates=[x.get("posting_date") for x in positive if x.get("posting_date") is not None]
    base_uoms={
        str(x.get("base_receipt_uom") or "").strip().upper()
        for x in positive if x.get("base_receipt_uom")
    }
    if (
        len(base_uoms)==1
        and all(x.get("base_receipt_quantity") is not None for x in positive)
    ):
        qty=sum((_d(x.get("base_receipt_quantity")) for x in positive),Decimal("0"))
        uom=next(iter(base_uoms))
        basis="BASE_UOM"
    else:
        entry_uoms={
            str(x.get("receipt_uom") or "").strip().upper()
            for x in positive if x.get("receipt_uom")
        }
        if len(entry_uoms)==1 and all(x.get("receipt_quantity") is not None for x in positive):
            qty=sum((_d(x.get("receipt_quantity")) for x in positive),Decimal("0"))
            uom=next(iter(entry_uoms))
            basis="ENTRY_UOM"
        else:
            qty=None
            uom="MIXED" if positive else None
            basis="MIXED_OR_UNRESOLVED"

    return {
        "date":max(dates) if dates else None,
        "quantity":qty,
        "uom":uom,
        "quantity_basis":basis,
        "event_count":len(positive),
        "article_numbers":sorted({
            str(x.get("article_number") or "").strip()
            for x in positive if str(x.get("article_number") or "").strip()
        }),
        "events":positive,
    }



def _d(value):
    return Decimal(str(value or 0))

class ReceiptWindowTests(unittest.TestCase):
    def build(self, events):
        days=[{'date':date(2026,10,n),'file_id':n} for n in range(1,15)]
        selected=[]
        class Cursor:
            def close(self): pass
        class Connection:
            def cursor(self, **kwargs): return Cursor()
        def receipts(cur, fid, count, data_days):
            selected.append((count,[d['date'] for d in data_days]))
            chosen={d['date'] for d in data_days}
            return [e for e in events if e['posting_date'] in chosen]
        page={'today':'2026-10-15','days':[],'items':[{'familyId':'88','members':[]}]}
        modules={
            'mobile_pricing':SimpleNamespace(build_page=lambda **kw:page),
            'db':SimpleNamespace(db_conn=lambda:nullcontext(Connection())),
            'business_clock':SimpleNamespace(completed_through_date=lambda:date(2026,10,14)),
            'data_coverage':SimpleNamespace(source_data_days=lambda cur, typ, limit, up_to:days[-limit:]),
            'webapp_v2_runtime':SimpleNamespace(
                _ordering_family_movement_metrics=lambda cur,fid,selected:{'status':'READY','quantity':280,'uom':'EA'},
                _family_receipt_events=receipts,
                _receipt_events_summary=_receipt_events_summary)
        }
        with patch.dict('sys.modules',modules):
            result=build_summary('88')
        return result['movement'],selected

    def event(self, day, qty=600, uom='EA'):
        return {'posting_date':date(2026,10,day),'receipt_quantity':qty,'receipt_uom':uom,
                'base_receipt_quantity':qty,'base_receipt_uom':uom,'article_number':'88'}

    def test_windows_use_exact_same_completed_movement_dates(self):
        result,selected=self.build([self.event(2),self.event(9)])
        self.assertEqual(result['seven']['receipt']['quantity'],600)
        self.assertEqual(result['fourteen']['receipt']['quantity'],1200)
        for key in ['seven','fourteen']:
            self.assertEqual(result[key]['receipt']['start'],result[key]['start'])
            self.assertEqual(result[key]['receipt']['through'],result[key]['through'])
            self.assertEqual(result[key]['receipt']['uom'],'EA')
        self.assertEqual(selected[0][0],7)
        self.assertEqual(selected[1][0],14)
        self.assertEqual(selected[0][1],selected[1][1][-7:])

    def test_verified_no_receipt_is_zero(self):
        result,_=self.build([])
        self.assertEqual(result['seven']['receipt']['quantity'],0)
        self.assertEqual(result['seven']['receipt']['status'],'READY')

    def test_mixed_or_unresolved_receipts_are_not_added(self):
        result,_=self.build([self.event(9),self.event(10,100,'LB')])
        self.assertIsNone(result['seven']['receipt']['quantity'])
        self.assertEqual(result['seven']['receipt']['status'],'UNVERIFIED')
        result,_=self.build([self.event(9,None)])
        self.assertIsNone(result['seven']['receipt']['quantity'])

if __name__=='__main__':
    unittest.main()
