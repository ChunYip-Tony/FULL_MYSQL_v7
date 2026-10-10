"""Regression checks for startup fan-out and App Ready JSON memory use."""
import ast
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from threading import Event, Lock
import unittest

ROOT = Path(__file__).parent

def load_functions(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, 'exec'), namespace)
    return namespace

@dataclass
class SampleSnapshot:
    build_id: str
    sections: dict
    completed_at: object

class SnapshotResourceBounds(unittest.TestCase):
    def serializer(self):
        return load_functions('yipman_app_ready_persistence.py', {'_json_default','snapshot_json'},
            {'json':json,'fields':fields,'is_dataclass':is_dataclass,'Any':object})

    def test_json_contract_preserves_shared_sections_dates_and_decimals(self):
        ns = self.serializer()
        row = {'upc':'24012300000','quantity':Decimal('18.25'),'date':date(2026,10,8)}
        snapshot = SampleSnapshot('one', {'rows':[row], 'index':{'24012300000':row}}, datetime(2026,10,10,tzinfo=timezone.utc))
        old = json.dumps(asdict(snapshot), default=ns['_json_default'], separators=(',',':'))
        self.assertEqual(ns['snapshot_json'](snapshot), old)
        self.assertIs(snapshot.sections['rows'][0], snapshot.sections['index']['24012300000'])

    def test_serializer_does_not_copy_leaf_objects(self):
        class NoCopy:
            def __deepcopy__(self, memo): raise AssertionError('Unexpected object graph copy')
            def __str__(self): return 'preserved'
        snap = SampleSnapshot('two', {'leaf':NoCopy()}, None)
        self.assertEqual(json.loads(self.serializer()['snapshot_json'](snap))['sections']['leaf'],'preserved')

    def request_namespace(self, pool, worker):
        ns={'date':date,'_ORDERING_REVIEW_CACHE_LOCK':Lock(),'_ORDERING_REVIEW_REFRESHING':set(),
            '_ORDERING_REVIEW_REFRESH_EXECUTOR':pool,'_ordering_review_refresh_worker':worker}
        return load_functions('backoffice_runtime.py', {'_request_ordering_review_refresh'}, ns)

    def test_fourteen_startup_dates_queue_once_with_one_heavy_worker(self):
        started, release = Event(), Event()
        calls=[]
        def worker(category, delivery, next_delivery, key, evidence):
            calls.append(key);started.set();release.wait(3)
            with ns['_ORDERING_REVIEW_CACHE_LOCK']: ns['_ORDERING_REVIEW_REFRESHING'].discard(key)
        with ThreadPoolExecutor(max_workers=1) as pool:
            ns=self.request_namespace(pool,worker)
            request=ns['_request_ordering_review_refresh']
            try:
                for index in range(14):
                    for duplicate in range(2): request('ALL',date(2026,10,10),None,str(index))
                self.assertTrue(started.wait(3))
                self.assertEqual(calls,['0'])
                self.assertEqual(len(ns['_ORDERING_REVIEW_REFRESHING']),14)
            finally: release.set()
        self.assertEqual(calls,[str(n) for n in range(14)])
        self.assertFalse(ns['_ORDERING_REVIEW_REFRESHING'])

    def test_failed_queue_submission_releases_key(self):
        pool=ThreadPoolExecutor(max_workers=1);pool.shutdown()
        ns=self.request_namespace(pool,lambda *args:None)
        with self.assertRaises(RuntimeError): ns['_request_ordering_review_refresh']('ALL',date(2026,10,10),None,'one')
        self.assertFalse(ns['_ORDERING_REVIEW_REFRESHING'])

if __name__=='__main__': unittest.main()
