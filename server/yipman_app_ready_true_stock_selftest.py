from __future__ import annotations
"""Dependency-light True Stock/App Ready integration regression test."""
from types import SimpleNamespace
from yipman_app_ready_true_stock_hook import install_app_ready_true_stock_hook

def run_selftest():
    events=[]
    class API:pass
    api=API();app=SimpleNamespace(state=SimpleNamespace())
    def invalidate():events.append('invalidate')
    def ok(*a,**k):events.append('commit');return {'status':'COMMITTED','family_id':32}
    def fail(*a,**k):events.append('failed-write');raise ValueError('REJECTED')
    api.backoffice_invalidate_true_stock_dependent_caches=invalidate
    api.submit_true_stock=ok;api.submit_negative_stock_true_stock=fail;api.cancel_true_stock=ok;api.v2_submit_family_true_stock=ok
    def broken_rebuild(**kwargs):events.append(('rebuild',kwargs['source_batch_id']));raise RuntimeError('snapshot unavailable')
    install_app_ready_true_stock_hook(app,api,broken_rebuild)
    result=api.submit_true_stock('123',1,'LB','tester')
    assert result['status']=='COMMITTED'
    assert events[0]=='commit' and 'invalidate' in events
    assert ('rebuild','TRUE_STOCK:submit_true_stock:32') in events
    before=len([x for x in events if isinstance(x,tuple) and x[0]=='rebuild'])
    try:api.submit_negative_stock_true_stock('123',-1,'LB','tester')
    except ValueError:pass
    else:raise AssertionError('failed authoritative mutation must propagate')
    after=len([x for x in events if isinstance(x,tuple) and x[0]=='rebuild'])
    assert before==after
    return {'committed_write_survives_refresh_failure':'PASS','failed_write_does_not_refresh':'PASS','family_refresh_identity':'PASS'}

if __name__=='__main__':print(run_selftest())
