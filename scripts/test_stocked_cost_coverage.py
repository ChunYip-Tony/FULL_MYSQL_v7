"""Regression: inventory-backed no-sale items receive source-derived cost repair."""
import ast
import re
import sqlite3
import unittest
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

source=Path(__file__).resolve().parents[1]/'server/current_active_cost_repair.py'
names={'_stocked_cost_upc_ids','_active_products','_text','_num','_oh_cost_candidate'}
module=ast.parse(source.read_text())
scope={'Any':Any,'Decimal':Decimal,'InvalidOperation':InvalidOperation,'re':re}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(source),'exec'),scope)

class Tests(unittest.TestCase):
    def test_stock_targets_exclude_zero_negative_old_and_historical(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        db.executescript('CREATE TABLE inventory_observation(article_id INT,batch_id INT,on_hand_quantity REAL); CREATE TABLE bridge_article_upc(article_id INT,upc_id INT,mapping_status TEXT,is_primary INT,valid_to TEXT); CREATE TABLE quick_check_current(upc_id INT,quick_check_status TEXT,current_oh REAL);')
        db.executemany('INSERT INTO inventory_observation VALUES (?,?,?)',[(1,71,22),(2,71,0),(3,71,-1),(4,70,5),(5,71,1)])
        db.executemany('INSERT INTO bridge_article_upc VALUES (?,?,?,?,?)',[(i,i,'CONFIRMED' if i!=5 else 'CANDIDATE',1,None) for i in range(1,6)])
        db.executemany('INSERT INTO quick_check_current VALUES (?,?,?)',[(6,'READY',1),(7,'HISTORICAL_ONLY',2),(8,'QA_HOLD',0),(9,'QA_HOLD',1)])
        class Cursor:
            def execute(self,q,args):self.cur=db.execute(q.replace('%s','?').replace('CURRENT_TIMESTAMP(6)','CURRENT_TIMESTAMP'),args)
            def fetchall(self):return [dict(r) for r in self.cur.fetchall()]
        self.assertEqual(scope['_stocked_cost_upc_ids'](Cursor(),71),{1,6,9})
        db.close()
    def test_cost_scope_never_fabricates_pos_quantity(self):
        local=dict(scope)
        local['source_data_days']=lambda *a,**kw:[{'date':date(2026,10,20)}]
        local['completed_through_date']=lambda:date(2026,10,20)
        local['canonical_pos_qty_by_upc']=lambda *a:{2:Decimal('3.5')}
        local['_stocked_cost_upc_ids']=lambda *a:{1}
        function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='_active_products')
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),local)
        class Cursor:
            def execute(self,q,args):self.args=args
            def fetchall(self):return [{'upc_id':n} for n in self.args]
        rows,_,_=local['_active_products'](Cursor(),71)
        self.assertEqual({r['upc_id']:r['recent_qty'] for r in rows},{1:Decimal('0'),2:Decimal('3.5')})
    def test_exact_oh_valuation_per_pound(self):
        cols={'unrestricted_qty':'G','total_value':'I','base_uom':'H','currency':'J'}
        for qty,value,cost in [('22','250.37',Decimal('250.37')/22),('1','7.38',Decimal('7.38'))]:
            r=scope['_oh_cost_candidate']({'G':qty,'I':value,'H':'LB','J':'USD'},cols)
            self.assertEqual(r['cost'],cost);self.assertEqual(r['cost_uom'],'LB')
            self.assertEqual(r['derivation_mode'],'TOTAL_VALUE_DIV_UNRESTRICTED')
        self.assertIsNone(scope['_oh_cost_candidate']({'G':'0','I':'7.38','H':'LB'},cols)['cost'])

if __name__=='__main__':unittest.main()
