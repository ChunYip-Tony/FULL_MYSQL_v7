"""Regression tests: a blocked durable snapshot read cannot block API startup."""
import asyncio
import sys
import threading
import time
import types
import unittest

# Builders are not exercised here; keep this liveness test database-free.
builders = types.ModuleType("yipman_app_ready_builders")
builders.app_ready_builders = lambda: {}
sys.modules.setdefault("yipman_app_ready_builders", builders)

from fastapi import FastAPI
import yipman_app_ready_api as subject


class StartupLivenessTests(unittest.TestCase):
    def setUp(self):
        self.hydrate = subject.hydrate_durable_app_ready
        self.rebuild = subject.request_app_ready_rebuild
        self.release = threading.Event()
        self.finished = threading.Event()

    def tearDown(self):
        self.release.set()
        self.finished.wait(3)
        subject.hydrate_durable_app_ready = self.hydrate
        subject.request_app_ready_rebuild = self.rebuild

    def test_blocked_snapshot_read_allows_health_and_preserves_order(self):
        entered = threading.Event()
        calls = []
        def hydrate():
            entered.set()
            if not self.release.wait(3):
                raise RuntimeError("test durable read remained blocked")
            calls.append("hydrated")
            return True
        def rebuild(**kwargs):
            calls.append(kwargs["source_batch_id"])
            self.finished.set()
            return True
        subject.hydrate_durable_app_ready = hydrate
        subject.request_app_ready_rebuild = rebuild
        app = FastAPI()
        @app.get("/healthz")
        async def health():
            return {"ok": True}
        subject.install_app_ready_api(app)

        async def exercise():
            started = time.monotonic()
            lifespan = app.router.lifespan_context(app)
            await lifespan.__aenter__()
            self.assertLess(time.monotonic() - started, .5)
            self.assertTrue(entered.wait(.5))
            self.assertTrue(app.state.yipman_app_ready_startup_loading)
            self.assertFalse(app.state.yipman_app_ready_durable_hydrated)
            messages = []
            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}
            async def send(message):
                messages.append(message)
            await app({"type": "http", "asgi": {"version": "3.0"},
                       "http_version": "1.1", "method": "GET",
                       "scheme": "http", "path": "/healthz", "raw_path": b"/healthz",
                       "query_string": b"", "headers": [],
                       "server": ("localhost", 8080), "client": ("localhost", 1234)},
                      receive, send)
            self.assertEqual(messages[0]["status"], 200)
            self.assertIn(b'"ok":true', messages[1]["body"])
            self.assertEqual(calls, [])
            self.release.set()
            self.assertTrue(self.finished.wait(1))
            for _ in range(100):
                if not app.state.yipman_app_ready_startup_loading:
                    break
                await asyncio.sleep(.01)
            self.assertEqual(calls, ["hydrated", "STARTUP"])
            self.assertTrue(app.state.yipman_app_ready_durable_hydrated)
            self.assertFalse(app.state.yipman_app_ready_startup_loading)
            await lifespan.__aexit__(None, None, None)
        asyncio.run(exercise())

    def test_missing_snapshot_still_requests_rebuild(self):
        subject.hydrate_durable_app_ready = lambda: False
        calls = []
        def rebuild(**kwargs):
            calls.append(kwargs["source_batch_id"])
            self.finished.set()
        subject.request_app_ready_rebuild = rebuild
        app = FastAPI()
        subject.install_app_ready_api(app)
        async def start():
            async with app.router.lifespan_context(app):
                pass
        asyncio.run(start())
        self.assertTrue(self.finished.wait(1))
        self.assertEqual(calls, ["STARTUP"])
        self.assertFalse(app.state.yipman_app_ready_durable_hydrated)


if __name__ == "__main__":
    unittest.main()
