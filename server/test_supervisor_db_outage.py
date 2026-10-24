import ast
import json
import socket
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

class SupervisorDatabaseOutageTests(unittest.TestCase):
    def scope(self, connect):
        tree=ast.parse(Path(__file__).with_name('single_service.py').read_text())
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'requeue_interrupted_pipeline_runs','main'}]
        logs=[]
        scope=dict(json=json,socket=socket,datetime=datetime,timezone=timezone,
                   db_conn=connect,API_VERSION='test',API_PIPELINE='pipeline',log=logs.append)
        exec(compile(ast.Module(body=functions,type_ignores=[]),'single_service.py','exec'),scope)
        return scope,logs

    def test_database_connection_failure_does_not_escape_supervisor(self):
        def unavailable(): raise ConnectionError('database unavailable')
        scope,logs=self.scope(unavailable)
        self.assertEqual(scope['requeue_interrupted_pipeline_runs']('WORKER_PROCESS_EXIT',42),0)
        self.assertTrue(any('worker recovery continues' in log for log in logs))

    def test_cursor_failure_does_not_escape_supervisor(self):
        class Connection:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def cursor(self): raise ConnectionError('cursor unavailable')
        scope,_=self.scope(Connection)
        self.assertEqual(scope['requeue_interrupted_pipeline_runs']('WORKER_PROCESS_EXIT',42),0)

    def test_stopped_worker_restarts_during_database_outage(self):
        def unavailable(): raise ConnectionError('database unavailable')
        scope,_=self.scope(unavailable)
        starts=[];stops=[];handlers={}
        api=SimpleNamespace(poll=lambda:None,pid=10,returncode=1)
        def start_worker():
            worker=SimpleNamespace(poll=lambda:1,pid=100+len(starts))
            starts.append(worker);return worker
        def sleep(seconds):
            if len(starts)>=2:handlers[15](15,None)
        scope.update(start_api=lambda:api,start_worker=start_worker,
            stop_process=lambda process,name:stops.append(name),RESTART_DELAY=0,
            APIWatchdog=lambda now:SimpleNamespace(due=lambda now:False),
            time=SimpleNamespace(monotonic=lambda:0,time=lambda:0,sleep=sleep),
            signal=SimpleNamespace(SIGTERM=15,SIGINT=2,signal=lambda sig,fn:handlers.update({sig:fn})))
        self.assertEqual(scope['main'](),0)
        self.assertEqual(len(starts),2)
        self.assertEqual(stops,['worker','api'])

    def test_missing_worker_owner_never_updates_other_work(self):
        def unexpected(): self.fail('database must not be opened without an owner')
        scope,_=self.scope(unexpected)
        self.assertEqual(scope['requeue_interrupted_pipeline_runs']('WORKER_PROCESS_EXIT'),0)

if __name__=='__main__': unittest.main()
