"""Exercise real endpoint functions without importing the DB-backed app graph."""
from __future__ import annotations
import ast
import asyncio
import json
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager


def functions(path, names, scope):
    tree=ast.parse(Path(__file__).with_name(path).read_text())
    body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list=[]
            body.append(node)
    exec(compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),path,'exec'),scope)
    return scope


class HTTPError(Exception):
    def __init__(self,status,detail):self.status_code=status;self.detail=detail


class UploadResponsivenessTests(unittest.IsolatedAsyncioTestCase):
    def scope(self):
        calls=[]
        def status(session):
            calls.append(('status',threading.get_ident()))
            time.sleep(.2)
            return {'files':[]}
        def ingest(*args):
            calls.append(('ingest',threading.get_ident()))
            time.sleep(.2)
            return {'file_id':42,'idempotent':True}
        async def threadpool(fn,*args):return await asyncio.to_thread(fn,*args)
        scope=dict(File=lambda *a,**k:None,HTTPException=HTTPError,
            _browser_upload_guard=lambda r:None,_web_upload_filename_ok=lambda n:True,
            get_settings=lambda:SimpleNamespace(upload_limit_mb=1),
            session_status=status,add_file=ingest,run_in_threadpool=threadpool,
            _web_upload_set_active_file=lambda *a:None,WEB_UPLOAD_MAX_FILES=40,
            WEB_UPLOAD_DEVICE='PUBLIC-WEB-UPLOAD',device_from_auth=lambda a:'device')
        functions('api.py',{'web_upload_file','_web_upload_file_sync','upload_file'},scope)
        return scope,calls

    async def file(self):
        async def read():return b'workbook'
        return SimpleNamespace(filename='mvt.xlsx',read=read)

    async def test_public_upload_keeps_event_loop_responsive_during_database_and_ingest(self):
        scope,calls=self.scope();loop_thread=threading.get_ident()
        task=asyncio.create_task(scope['web_upload_file']('session',None,await self.file()))
        await asyncio.sleep(.03)
        self.assertFalse(task.done(),'slow ingest must still be running when health can respond')
        self.assertTrue(calls)
        self.assertNotEqual(calls[0][1],loop_thread)
        self.assertEqual(await task,{'file_id':42,'idempotent':True})
        self.assertTrue(all(tid!=loop_thread for _,tid in calls))

    async def test_authenticated_upload_also_keeps_event_loop_responsive(self):
        scope,calls=self.scope();loop_thread=threading.get_ident()
        task=asyncio.create_task(scope['upload_file']('session',await self.file(),None))
        await asyncio.sleep(.03)
        self.assertFalse(task.done())
        self.assertEqual((await task)['file_id'],42)
        self.assertTrue(all(tid!=loop_thread for _,tid in calls))

    async def test_upload_error_keeps_original_status(self):
        scope,_=self.scope()
        def denied(*args):raise PermissionError('different owner')
        scope['add_file']=denied
        with self.assertRaises(HTTPError) as caught:
            await scope['web_upload_file']('session',None,await self.file())
        self.assertEqual(caught.exception.status_code,403)

    async def test_empty_upload_is_not_ingested(self):
        scope,calls=self.scope()
        with self.assertRaises(HTTPError) as caught:
            await asyncio.to_thread(scope['_web_upload_file_sync'],'session','mvt.xlsx',b'')
        self.assertEqual(caught.exception.status_code,400)
        self.assertFalse(any(name=='ingest' for name,_ in calls))


class StartupRecoveryTests(unittest.TestCase):
    def test_default_startup_does_not_build_duplicate_analytical_caches(self):
        scope={'os':SimpleNamespace(environ={})}
        functions('api.py',{'_warm_mobile_home_summary_cache'},scope)
        self.assertIsNone(scope['_warm_mobile_home_summary_cache']())

    def test_restart_uses_same_reconciliation_policy(self):
        calls=[]
        scope=dict(json=json,_reconcile_ready_publication=lambda:calls.append('reconcile') or {'queue':False,'reason':'WAITING_FOR_DATA'})
        functions('worker.py',{'_recover_chatgpt_bridge_on_startup'},scope)
        scope['_recover_chatgpt_bridge_on_startup']()
        self.assertEqual(calls,['reconcile'])

    def test_new_source_takes_priority_over_old_snapshot_export(self):
        calls=[]
        class Cursor:
            def execute(self,sql,params=None):self.sql=sql;calls.append(sql)
            def fetchone(self):
                if 'GET_LOCK' in self.sql:return {'ok':1}
                if 'source_pending' in self.sql:return {'source_pending':1}
                return {}
            def close(self):pass
        @contextmanager
        def connect():yield SimpleNamespace(cursor=lambda **kwargs:Cursor())
        scope=dict(bridge_enabled=lambda:True,db_conn=connect,API_PIPELINE='test')
        functions('worker.py',{'_reconcile_ready_publication'},scope)
        self.assertEqual(scope['_reconcile_ready_publication'](),{'reason':'SOURCE_NOT_READY'})
        self.assertFalse(any('MAX(publish_batch_id)' in sql for sql in calls))


class PublicationPreflightTests(unittest.TestCase):
    def test_global_source_blocker_skips_expensive_exports_and_external_writes(self):
        class Cursor:
            def close(self):pass
        @contextmanager
        def connect():yield SimpleNamespace(cursor=lambda **kwargs:Cursor())
        def forbidden(*args):raise AssertionError('source hold must return before analytical export')
        scope=dict(time=time,bridge_enabled=lambda:True,_sheet_id=lambda:'sheet',
            _bridge_transport=lambda:'APPS_SCRIPT',db_conn=connect,
            _fetch_batch_state=lambda *a:({'processing_status':'QUICK_CHECK_READY_WITH_HOLDS'},{'blocking_issue_count':1}),
            _fetch_quick_rows=forbidden,
            _canonical_freshness=forbidden)
        functions('chatgpt_sheet_bridge.py',{'publish_chatgpt_snapshot'},scope)
        result=scope['publish_chatgpt_snapshot'](75)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['reason'],'Phase 3 blocking_issue_count is non-zero.')


if __name__=='__main__':unittest.main()

