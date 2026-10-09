from yipman_app_ready_true_stock_overlay import _walk


def run():
    payload={'rows':[{'family_id':10,'effective_oh':2,'effective_oh_source':'TRUE_STOCK'},{'family_id':20,'effective_oh':7,'effective_oh_source':'SYSTEM_OH'}]}
    other=repr(payload['rows'][1])
    count=_walk(payload,'10','',11,'LB','SYSTEM_OH')
    assert count==1
    assert payload['rows'][0]['effective_oh']==11
    assert payload['rows'][0]['effective_oh_source']=='SYSTEM_OH'
    assert repr(payload['rows'][1])==other
    return {'cancel_restores_system_oh_scoped':'PASS','unrelated_family_untouched':'PASS'}

if __name__=='__main__':print(run())
