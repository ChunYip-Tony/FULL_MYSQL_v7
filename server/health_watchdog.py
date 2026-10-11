"""Bounded local HTTP liveness checks; no database access or pipeline mutation."""
import json
from urllib.request import urlopen


def api_responds(port, timeout=3):
    try:
        with urlopen(f'http://127.0.0.1:{int(port)}/healthz', timeout=timeout) as response:
            return response.status == 200 and json.loads(response.read(16384)).get('ok') is True
    except Exception:
        return False


class APIWatchdog:
    def __init__(self, now, startup_grace=180, interval=15, failures=4):
        self.startup_grace = startup_grace
        self.interval = interval
        self.threshold = failures
        self.reset(now)

    def reset(self, now):
        self.next_check = now + self.startup_grace
        self.failures = 0

    def due(self, now):
        return now >= self.next_check

    def observe(self, now, healthy):
        self.next_check = now + self.interval
        self.failures = 0 if healthy else self.failures + 1
        return self.failures >= self.threshold
