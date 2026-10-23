from __future__ import annotations
import ast
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def function(file,name,scope):
    tree=ast.parse(Path(__file__).with_name(file).read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    nodes=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),node]
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),file,'exec'),scope)
    return scope[name]


class SnapshotMemoryPriorityTests(unittest.TestCase):
    def startup(self,wait):
        calls=[];events={};targets=[]
        app=SimpleNamespace(state=SimpleNamespace())
        app.on_event=lambda name:lambda fn:events.setdefault(name,fn)
        app.get=lambda path:lambda fn:fn
        class Thread:
            def __init__(self,*,target,**kwargs):targets.append(target)
            def start(self):pass
        scope=dict(threading=SimpleNamespace(Thread=Thread),hydrate_durable_app_ready=lambda:calls.append('hydrate') or True,
            start_app_ready_recovery=lambda:calls.append('recovery'),request_app_ready_rebuild=lambda **kwargs:calls.append('rebuild'),_LOG=SimpleNamespace(exception=lambda *a:None))
        install=function('yipman_app_ready_api.py','install_app_ready_api',scope)
        install(app);events['startup']()
        with patch.dict('sys.modules',{'pipeline_priority':SimpleNamespace(wait_for_pipeline_idle=lambda:calls.append('wait') or wait())}):targets[0]()
        return calls,app

    def test_startup_waits_before_loading_large_snapshot(self):
        order=[]
        def wait():order.append('wait')
        calls,_=self.startup(wait)
        self.assertEqual(order,['wait']);self.assertEqual(calls,['wait','hydrate','recovery'])

    def test_pending_publication_cannot_load_snapshot_on_startup(self):
        def blocked():raise RuntimeError('still waiting for publication')
        calls,_=self.startup(blocked)
        self.assertEqual(calls,['wait'])

    def test_interactive_pointer_refresh_preserves_old_cache_without_loading_new_one(self):
        loads=[];hydrated=[];old=SimpleNamespace(build_id='old');new=SimpleNamespace(build_id='new')
        scope=dict(time=SimpleNamespace(monotonic=lambda:100),_POINTER_TTL_SECONDS=0,
            _POINTER_LOCK=threading.Lock(),_POINTER_CHECKED_AT=0,_POINTER_LAST_ERROR=None,
            APP_READY_SNAPSHOTS=SimpleNamespace(active=lambda:old,hydrate=hydrated.append),SnapshotBuild=object)
        run=function('yipman_app_ready_readers.py','refresh_hot_cache_if_stale',scope)
        persistence=SimpleNamespace(active_build_id=lambda:'new',load_active_snapshot=lambda cls:loads.append('load') or new)
        with patch.dict('sys.modules',{'pipeline_priority':SimpleNamespace(pipeline_pending=lambda:True),'yipman_app_ready_persistence':persistence}):
            self.assertFalse(run(force=True));self.assertEqual(loads,[]);self.assertEqual(hydrated,[])
        with patch.dict('sys.modules',{'pipeline_priority':SimpleNamespace(pipeline_pending=lambda:False),'yipman_app_ready_persistence':persistence}):
            self.assertTrue(run(force=True))
        self.assertEqual(loads,['load']);self.assertEqual(hydrated,[new])


if __name__=='__main__':unittest.main()
