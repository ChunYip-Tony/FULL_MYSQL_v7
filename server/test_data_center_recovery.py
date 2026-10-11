import ast
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from health_watchdog import APIWatchdog, api_responds


class RecoveryTests(unittest.TestCase):
    def test_startup_grace_and_bounded_failure_threshold(self):
        watch = APIWatchdog(0)
        self.assertFalse(watch.due(179))
        self.assertTrue(watch.due(180))
        for now in (180, 195, 210):
            self.assertFalse(watch.observe(now, False))
            self.assertFalse(watch.due(now + 14))
        self.assertTrue(watch.observe(225, False))
        watch.reset(225)
        self.assertFalse(watch.due(404))
        self.assertEqual(watch.failures, 0)

    def test_one_success_clears_transient_failures(self):
        watch = APIWatchdog(0)
        for now in (180, 195, 210):
            watch.observe(now, False)
        self.assertFalse(watch.observe(225, True))
        self.assertFalse(watch.observe(240, False))
        self.assertEqual(watch.failures, 1)

    def test_probe_timeout_failure_and_verified_success(self):
        with patch('health_watchdog.urlopen', side_effect=TimeoutError) as open_url:
            self.assertFalse(api_responds(8080))
            open_url.assert_called_once_with('http://127.0.0.1:8080/healthz', timeout=3)
        with patch('health_watchdog.urlopen') as open_url:
            response = open_url.return_value.__enter__.return_value
            response.status = 200
            for body, expected in (({'ok': True}, True), ({'ok': False}, False)):
                response.read.return_value = json.dumps(body).encode()
                self.assertEqual(api_responds(8080), expected)
            response.read.return_value = b'not json'
            self.assertFalse(api_responds(8080))

    def test_static_shells_and_health_bypass_sync_query_threads(self):
        functions = {n.name: n for n in ast.parse(Path('api.py').read_text()).body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for name in ('standalone_data_center', 'standalone_stock_records', 'healthz'):
            self.assertIsInstance(functions[name], ast.AsyncFunctionDef)
            self.assertNotIn('db_conn', ast.unparse(functions[name]))

    def test_http_restart_preserves_worker_and_does_not_requeue_runs(self):
        source = ast.parse(Path('single_service.py').read_text())
        main = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        probe = next(n for n in ast.walk(main) if isinstance(n, ast.If) and 'watchdog.due' in ast.unparse(n.test))
        text = ast.unparse(probe)
        self.assertIn('stop_process(api', text)
        self.assertIn('api = start_api()', text)
        self.assertNotIn('start_worker', text)
        self.assertNotIn('requeue_interrupted_pipeline_runs', text)
        self.assertIn('if stopping:', text)


if __name__ == '__main__':
    unittest.main()
