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
    def test_restart_uses_same_reconciliation_policy(self):
        calls=[]
        scope=dict(json=json,_reconcile_ready_publication=lambda:calls.append('reconcile') or {'queue':False,'reason':'WAITING_FOR_DATA'})
        functions('worker.py',{'_recover_chatgpt_bridge_on_startup'},scope)
        scope['_recover_chatgpt_bridge_on_startup']()
        self.assertEqual(calls,['reconcile'])


if __name__=='__main__':unittest.main()
