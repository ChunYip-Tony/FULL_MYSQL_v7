"""Bound expensive read work and share identical in-flight results."""
from concurrent.futures import Future, TimeoutError
from threading import Lock


class ReadBusy(Exception):
    pass


class ReadSingleFlight:
    def __init__(self, max_running=2, wait_seconds=20):
        self.max_running = max_running
        self.wait_seconds = wait_seconds
        self._lock = Lock()
        self._running = {}

    def run(self, key, build):
        with self._lock:
            future = self._running.get(key)
            owner = future is None
            if owner:
                if len(self._running) >= self.max_running:
                    raise ReadBusy('Pricing reads are busy; retry shortly.')
                future = Future()
                self._running[key] = future
        if not owner:
            try:
                return future.result(timeout=self.wait_seconds)
            except TimeoutError as exc:
                raise ReadBusy('Pricing read is still running; retry shortly.') from exc
        try:
            result = build()
            future.set_result(result)
            return result
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._running.pop(key, None)
