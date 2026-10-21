"""Retry policy for Apps Script bridge failures, without network or credentials."""
import ast
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "server" / "chatgpt_sheet_bridge.py"
nodes = [n for n in ast.parse(SOURCE.read_text()).body
         if isinstance(n, (ast.ClassDef, ast.FunctionDef))
         and n.name in {"_AppsScriptPermanentError", "_apps_script_post"}]
ns = {"Any": object, "_apps_script_secret": lambda: "test-secret",
      "_apps_script_url": lambda: "https://script.google.com/test"}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), ns)

class Response:
    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status
        self.text = "test response"
    def json(self):
        return self.data

class RetryTests(unittest.TestCase):
    def run_responses(self, responses):
        calls = []
        def post(*args, **kwargs):
            result = responses[len(calls)]
            calls.append(kwargs)
            if isinstance(result, Exception):
                raise result
            return result
        fake_requests = types.SimpleNamespace(post=post)
        with patch.dict(sys.modules, {"requests": fake_requests}), patch("time.sleep") as sleep:
            try:
                value = ns["_apps_script_post"]({"action": "read"}, timeout=9)
                return value, calls, sleep.call_count
            except Exception as error:
                return error, calls, sleep.call_count

    def test_permanent_bridge_errors_stop_after_one_attempt(self):
        for code in ["TAB_NOT_ALLOWED: ANALYSIS_UPC_DAILY", "UNAUTHORIZED",
                     "SPREADSHEET_ID_MISMATCH"]:
            with self.subTest(code=code):
                result, calls, sleeps = self.run_responses([Response({"ok": False, "error": code})])
                self.assertIsInstance(result, ns["_AppsScriptPermanentError"])
                self.assertEqual(len(calls), 1)
                self.assertEqual(sleeps, 0)

    def test_transient_bridge_rejection_retries(self):
        result, calls, sleeps = self.run_responses([
            Response({"ok": False, "error": "Service invoked too many times"}),
            Response({"ok": True, "rows": 3})])
        self.assertEqual(result["rows"], 3)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, 1)

    def test_transient_http_and_connection_errors_retry(self):
        for first in [Response({}, 429), Response({}, 503), TimeoutError("timed out")]:
            with self.subTest(first=first):
                result, calls, sleeps = self.run_responses([first, Response({"ok": True})])
                self.assertEqual(result, {"ok": True})
                self.assertEqual(len(calls), 2)
                self.assertEqual(sleeps, 1)
                self.assertEqual(calls[-1]["timeout"], 9)

    def test_unknown_rejection_remains_bounded(self):
        result, calls, sleeps = self.run_responses([
            Response({"ok": False, "error": "unknown"}) for _ in range(4)])
        self.assertIsInstance(result, RuntimeError)
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleeps, 3)

    def test_success_does_not_retry(self):
        result, calls, sleeps = self.run_responses([Response({"ok": True})])
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, 0)

if __name__ == "__main__":
    unittest.main()
