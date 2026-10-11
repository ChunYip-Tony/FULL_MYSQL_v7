import sys
import types
import unittest
from datetime import date
events=[]
class Cursor:
    def __init__(self):self.rows=[]
    def execute(self,sql,args):
        self.rows=[{'family_id':88,'main_article_number':'1361740','family_description':'Family name'}] if 'product_family' in sql else [{'article_number':'1361742','article_description':'FRESH SALMON 10/12 CS'}]
        if 'FROM article WHERE' in sql:assert args==('1361742','9999999')
    def fetchone(self):return self.rows[0]
    def fetchall(self):return self.rows
    def close(self):pass
class Connection:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def cursor(self,**kwargs):return Cursor()
sys.modules['db']=types.SimpleNamespace(db_conn=lambda:Connection())
sys.modules['webapp_v2_runtime']=types.SimpleNamespace(_family_receipt_events=lambda *args:events)
from yipman_mobile_v1_receipt_history import family_receipt_history
class ReceiptNamesTests(unittest.TestCase):
    def test_master_names_and_missing_name_preserve_receipt_facts(self):
        events[:]=[{'posting_date':date(2026,10,9),'article_number':code,'receipt_quantity':5,'receipt_uom':'LB','base_receipt_quantity':5,'base_receipt_uom':'LB'} for code in ['1361742','9999999']]
        value=family_receipt_history('1361740')['days'][0]
        self.assertEqual(value['quantity'],10)
        self.assertEqual(value['events'][0]['article_name'],'FRESH SALMON 10/12 CS')
        self.assertIsNone(value['events'][1]['article_name'])
        self.assertEqual(value['article_numbers'],['1361742','9999999'])
if __name__=='__main__':unittest.main()
