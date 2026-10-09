from yipman_app_ready_true_stock_overlay import _walk


def run():
    sections={
        'ordering_regular':{'rows':[
            {'family_id':10,'effective_oh':9,'suggested_order_qty':5,'decision_evidence_ready':True},
            {'family_id':20,'effective_oh':7,'suggested_order_qty':3,'decision_evidence_ready':True},
        ]},
        'decision_intelligence':{'by_key':{
            'FAMILY:10':{'family_id':10,'current_oh':9,'operational_decision_code':'ORDER'},
            'FAMILY:20':{'family_id':20,'current_oh':7,'operational_decision_code':'KEEP'},
        }},
    }
    untouched=repr(sections['ordering_regular']['rows'][1])+repr(sections['decision_intelligence']['by_key']['FAMILY:20'])
    count=_walk(sections,'10','',2,'LB')
    assert count==2
    a=sections['ordering_regular']['rows'][0]
    assert a['effective_oh']==2
    assert a['decision_evidence_ready'] is False
    assert 'TRUE_STOCK_FAMILY_RECALC_PENDING' in a['decision_missing_evidence']
    assert sections['decision_intelligence']['by_key']['FAMILY:10']['current_oh']==2
    after=repr(sections['ordering_regular']['rows'][1])+repr(sections['decision_intelligence']['by_key']['FAMILY:20'])
    assert untouched==after
    return {'family_only_patch':'PASS','stale_decision_fail_closed':'PASS','unrelated_family_untouched':'PASS'}


if __name__=='__main__':
    print(run())
