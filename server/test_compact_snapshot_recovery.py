import ast
import json
import os
import signal
import threading
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from snapshot_graph import dumps, loads


def function(filename, name, scope):
    tree = ast.parse(Path(__file__).with_name(filename).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), filename, 'exec'), scope)
    return scope[name]


class CompactSnapshotTests(unittest.TestCase):
    def test_roundtrip_restores_shared_identity_and_values(self):
        @dataclass
        class Snapshot:
            build_id: str
            sections: dict
        row = {'upc': '00123', 'cost': Decimal('4.17'), 'date': date(2026,10,23), 'text': '魚'}
        source = Snapshot('build', {'rows': [row], 'by_key': {'00123': row}})
        restored = loads(dumps(source))
        self.assertEqual(restored['sections']['rows'][0], {'upc':'00123','cost':'4.17','date':'2026-10-23','text':'魚'})
        self.assertIs(restored['sections']['rows'][0], restored['sections']['by_key']['00123'])
        self.assertEqual(source.sections['rows'][0]['cost'], Decimal('4.17'))

    def test_repeated_indexes_no_longer_expand_large_rows(self):
        row = {'evidence': 'x' * 10000}
        payload = {'rows': [row], 'index': {str(n): row for n in range(100)}}
        compact = dumps(payload)
        self.assertLess(len(compact), len(json.dumps(payload)) / 20)
        result = loads(compact)
        self.assertIs(result['index']['99'], result['rows'][0])

    def test_legacy_json_remains_readable(self):
        self.assertEqual(loads('{"build_id":"legacy","sections":{}}'), {'build_id':'legacy','sections':{}})

    def test_reserved_looking_user_keys_remain_literal(self):
        value = {'app_ready_graph_version': 'ordinary payload', 'ref': 42, 'nested': {'ref': 0}}
        self.assertEqual(loads(dumps(value)), value)

    def test_invalid_references_fail_closed(self):
        with self.assertRaises(ValueError):
            loads(json.dumps({'app_ready_graph_version':1, 'root':{'ref':7}, 'nodes':[]}))

    def loader(self, records):
        queries = []
        class Cursor:
            def execute(self, query, args=None): queries.append((query,args))
            def fetchone(self): return records.pop(0)
            def close(self): pass
        conn = SimpleNamespace(cursor=lambda **kw:Cursor(), commit=lambda:None)
        @contextmanager
        def db(): yield conn
        run = function('yipman_app_ready_persistence.py', 'load_active_snapshot', {'db_conn':db,'ensure_schema':lambda c:None,'os':os})
        return run, queries

    def test_oversized_cache_rejected_before_blob_download(self):
        run, queries = self.loader([{'build_id':'huge','payload_bytes':100*1048576}])
        with self.assertRaisesRegex(RuntimeError, 'SAFE_LOAD_LIMIT'): run(SimpleNamespace)
        self.assertEqual(len(queries), 1)
        self.assertNotIn('SELECT g.snapshot_json', queries[0][0])

    def test_generation_read_is_pinned_to_inspected_size(self):
        run, queries = self.loader([{'build_id':'checked','payload_bytes':50},{'snapshot_json':dumps({'build_id':'checked','sections':{}})}])
        self.assertEqual(run(SimpleNamespace).build_id, 'checked')
        self.assertEqual(queries[1][1], ('checked',))

    def test_api_exit_restarts_without_interrupting_worker(self):
        events, handlers = [], {}
        clock = [0]
        processes = [SimpleNamespace(poll=lambda:-9), SimpleNamespace(poll=lambda:None)]
        worker = SimpleNamespace(poll=lambda:None, pid=123)
        def start_api(): events.append('start_api'); return processes.pop(0)
        def sleep(seconds):
            clock[0] += seconds
            if seconds == 1 and events.count('start_api') == 2:
                handlers[signal.SIGTERM](signal.SIGTERM,None)
        watchdog = SimpleNamespace(due=lambda now:False,reset=lambda now:events.append('watchdog_reset'))
        scope = {'start_api':start_api,'start_worker':lambda:worker,
                 'APIWatchdog':lambda now:watchdog,'time':SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,time=lambda:clock[0]),
                 'signal':SimpleNamespace(SIGTERM=signal.SIGTERM,SIGINT=signal.SIGINT,signal=lambda sig,fn:handlers.update({sig:fn})),
                 'RESTART_DELAY':1,'log':lambda msg:None,
                 'stop_process':lambda proc,name:events.append('stop_'+name),
                 'requeue_interrupted_pipeline_runs':lambda *args:0}
        self.assertEqual(function('single_service.py','main',scope)(),0)
        self.assertEqual(events.count('start_api'),2)
        self.assertEqual(events[-2:],['stop_worker','stop_api'])
        self.assertLess(events.index('watchdog_reset'), events.index('stop_worker'))


if __name__ == '__main__': unittest.main()
