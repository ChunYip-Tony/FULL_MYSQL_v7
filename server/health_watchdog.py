"""Bounded local HTTP liveness checks; no database access or pipeline mutation."""
import json
import time
from urllib.request import urlopen

_LAST_EVIDENCE_AT = 0.0


def _record_health_evidence(payload):
    global _LAST_EVIDENCE_AT
    now = time.monotonic()
    if now - _LAST_EVIDENCE_AT < 30:
        return
    runtime = payload.get('runtime') or {}
    if not isinstance(runtime, dict):
        return
    # Container replacements erase /tmp and restart counters. Retain bounded,
    # non-sensitive evidence in platform logs before the next replacement.
    evidence = {key: runtime.get(key) for key in (
        'revision', 'pid', 'uptime_seconds', 'process_memory_mb', 'process_peak_mb',
        'memory_mb', 'memory_limit_mb', 'oom_kills', 'background_analysis')}
    print('[single-service] runtime ' + json.dumps(evidence, separators=(',', ':')), flush=True)
    _LAST_EVIDENCE_AT = now


def api_responds(port, timeout=3):
    try:
        with urlopen(f'http://127.0.0.1:{int(port)}/healthz', timeout=timeout) as response:
            payload = json.loads(response.read(16384))
            healthy = response.status == 200 and isinstance(payload, dict) and payload.get('ok') is True
            if healthy:
                try:
                    _record_health_evidence(payload)
                except Exception:
                    pass  # Diagnostics cannot turn a successful probe into a failure.
            return healthy
    except Exception:
        return False


class APIWatchdog:
    def __init__(self, now, startup_grace=180, interval=10, failures=3):
        self.startup_grace = startup_grace
        self.interval = interval
        self.threshold = failures
        self.reset(now)

    def reset(self, now):
        self.startup_deadline = now + self.startup_grace
        self.next_check = now
        self.has_responded = False
        self.failures = 0

    def due(self, now):
        return now >= self.next_check

    def observe(self, now, healthy):
        if healthy:
            self.has_responded = True
        elif not self.has_responded and now < self.startup_deadline:
            # Allow a genuinely cold process to start, but check immediately
            # and leave the startup grace as soon as it has served health.
            self.next_check = min(now + 5, self.startup_deadline)
            self.failures = 0
            return False
        self.next_check = now + self.interval
        self.failures = 0 if healthy else self.failures + 1
        return self.failures >= self.threshold

