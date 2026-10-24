import asyncio
import ast
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from request_capacity import RequestCapacityMiddleware
from runtime_health import runtime_health
from supervisor_health import SupervisorHealth, read_supervisor_health


async def call(app, path, receive=None):
    messages=[]
    async def send(message): messages.append(message)
    async def empty(): return {'type':'http.request','body':b''}
    await app({'type':'http','path':path}, receive or empty, send)
    return messages


class CapacityTests(unittest.IsolatedAsyncioTestCase):
    async def test_flood_keeps_health_responsive_and_rejects_before_body_or_handler(self):
        release=asyncio.Event(); entered=[]
        async def application(scope,receive,send):
            path=scope['path'];entered.append(path)
            if path.startswith('/v1/slow'): await release.wait()
            await send({'type':'http.response.start','status':200,'headers':[]})
            await send({'type':'http.response.body','body':b'ok'})
        guard=RequestCapacityMiddleware(application,max_requests=2,max_ai=1)
        tasks=[asyncio.create_task(call(guard,'/v1/slow/'+str(i))) for i in range(2)]
        await asyncio.sleep(0)
        async def do_not_read(): self.fail('Overload must not consume upload body')
        rejected=await call(guard,'/v1/web-upload/files',do_not_read)
        self.assertEqual(rejected[0]['status'],503)
        self.assertFalse(json.loads(rejected[1]['body'])['detail']['request_started'])
        self.assertNotIn('/v1/web-upload/files',entered)
        for path in ('/healthz','/v1/yipman/ai/status'):
            self.assertEqual((await asyncio.wait_for(call(guard,path),.1))[0]['status'],200)
        release.set();await asyncio.gather(*tasks)
        self.assertEqual(guard.state['active'],0)
        self.assertEqual((await call(guard,'/v1/normal'))[0]['status'],200)

    async def test_ai_limit_leaves_capacity_for_item_lookups(self):
        release=asyncio.Event()
        async def application(scope,receive,send):
            if scope['path'].endswith('/chat'): await release.wait()
            await send({'type':'http.response.start','status':200,'headers':[]})
        guard=RequestCapacityMiddleware(application,max_requests=3,max_ai=1)
        task=asyncio.create_task(call(guard,'/v1/yipman/ai/chat'));await asyncio.sleep(0)
        self.assertEqual((await call(guard,'/v1/yipman/ai/chat'))[0]['status'],503)
        self.assertEqual((await call(guard,'/v1/app/search'))[0]['status'],200)
        release.set();await task
        self.assertEqual(guard.state['ai_active'],0)

    async def test_exception_and_cancellation_release_capacity(self):
        async def failing(scope,receive,send): raise ValueError('handler failed')
        guard=RequestCapacityMiddleware(failing,max_requests=1)
        with self.assertRaises(ValueError): await call(guard,'/v1/failure')
        self.assertEqual(guard.state['active'],0)
        async def blocked(scope,receive,send): await asyncio.Event().wait()
        guard=RequestCapacityMiddleware(blocked,max_requests=1)
        task=asyncio.create_task(call(guard,'/v1/yipman/ai/chat'));await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual(guard.state['active'],0)
        self.assertEqual(guard.state['ai_active'],0)


class DiagnosticsTests(unittest.TestCase):
    def test_ai_readiness_reflects_model_configuration_and_capacity(self):
        tree=ast.parse(Path(__file__).with_name('api.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='yipman_ai_status_endpoint')
        fn.decorator_list=[]
        scope={'json':json,'j':str,'yipman_ai_status':lambda:{'configured':True}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'api.py','exec'),scope)
        status=scope[fn.name]
        capacity={'enabled':True,'active':1,'limit':8,'ai_active':2,'ai_limit':2}
        with patch('request_capacity.capacity_status',return_value=capacity):
            self.assertFalse(status()['ready'])
            capacity['ai_active']=1;self.assertTrue(status()['ready'])
            capacity['active']=8;self.assertFalse(status()['ready'])
            scope['yipman_ai_status']=lambda:{'configured':False}
            capacity['active']=0;self.assertFalse(status()['ready'])

    def test_restart_evidence_is_bounded_and_survives_api_process_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'supervisor.json';state=SupervisorHealth(path)
            for i in range(12): state.event('api','PROCESS_EXIT',-9)
            observed=read_supervisor_health(path)
            self.assertEqual(observed['api_restarts'],12)
            self.assertEqual(len(observed['recent_events']),8)
            self.assertEqual(observed['recent_events'][-1]['exit_code'],-9)
            self.assertTrue(observed['healthy'])
            with patch('supervisor_health.time.time',return_value=observed['updated_epoch']+31):
                self.assertFalse(read_supervisor_health(path)['healthy'])

    def test_unwritable_or_corrupt_diagnostics_never_stop_supervision(self):
        state=SupervisorHealth('/missing-directory/service.json')
        state.event('worker','PROCESS_EXIT',1)
        self.assertIsNone(read_supervisor_health('/missing-directory/service.json'))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state';path.write_text('{invalid')
            self.assertIsNone(read_supervisor_health(path))

    def test_unlimited_memory_sentinel_is_not_a_real_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'memory').mkdir()
            (root/'memory/memory.usage_in_bytes').write_text(str(256*1048576))
            (root/'memory/memory.limit_in_bytes').write_text(str(2**63-4096))
            data=runtime_health(root)
            self.assertEqual(data['memory_mb'],256)
            self.assertIsNone(data['memory_limit_mb'])

    def test_uptime_uses_process_start_instead_of_first_health_request(self):
        original=Path.read_text
        def read(path,*args,**kwargs):
            if str(path)=='/proc/self/stat': return '123 (a name with ) spaces) '+ ' '.join(['S']+['0']*18+['90000'])
            if str(path)=='/proc/uptime': return '1000.0 100.0'
            return original(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as directory,patch.object(Path,'read_text',read),patch('runtime_health.os.sysconf',return_value=100):
            data=runtime_health(Path(directory))
            self.assertEqual(data['uptime_seconds'],100)
            self.assertEqual(data['uptime_source'],'process')


if __name__=='__main__': unittest.main()
