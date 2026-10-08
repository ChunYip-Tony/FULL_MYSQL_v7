from __future__ import annotations
"""Dependency-light regression tests for decision identity indexing."""
from yipman_app_ready_builders import _decision_index

def run_selftest():
    pricing={'rows':[{'family':'F1','upc':'001111','price_type':'REG','suggested_price':5.99},{'family':'F1','upc':'002222','price_type':'TPR','suggested_price':4.99}]}
    tpr={'rows':[{'family':'F1','upc':'002222','current_price':4.99}]}
    ordering={'deliveries':{'2026-10-09':{'rows':[{'family':'F1','upc':'001111','suggested_order_qty':10}]}}}
    idx=_decision_index(pricing,tpr,ordering)
    assert idx['UPC:1111']['suggested_price']==5.99
    assert idx['UPC:2222']['suggested_price']==4.99
    assert idx['UPC:1111'] is not idx['UPC:2222']
    assert 'UPC:1111:REG' in idx and 'UPC:2222:TPR' in idx
    assert 'UPC:2222:TPR_PROGRESS' in idx
    assert 'UPC:1111:ORDERING' in idx
    assert 'FAMILY:F1' in idx
    return {'decision_exact_upc':'PASS','action_specific_keys':'PASS','family_fallback':'PASS','cross_upc_contamination_guard':'PASS'}

if __name__=='__main__':print(run_selftest())
