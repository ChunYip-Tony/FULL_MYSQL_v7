"""Small local restart evidence, with no database or credential dependency."""
import json
import os
import time
from pathlib import Path


def _path():
    return Path(os.environ.get('FULLMYSQL_SUPERVISOR_HEALTH_PATH', '/tmp/fullmysql_supervisor_health.json'))


class SupervisorHealth:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else _path()
        self.last_write = 0
        self.data = {'revision': 'service-resilience-v1', 'supervisor_pid': os.getpid(),
                     'started_epoch': time.time(), 'api_restarts': 0,
                     'worker_restarts': 0, 'recent_events': []}

    def event(self, component, reason, exit_code=None):
        if component in ('api', 'worker'):
            self.data[component + '_restarts'] += 1
        self.data['recent_events'] = (self.data['recent_events'] + [
            {'epoch': time.time(), 'component': component, 'reason': reason, 'exit_code': exit_code}
        ])[-8:]
        self.write()

    def heartbeat(self, api_pid, worker_pid, failures):
        self.data.update(api_pid=api_pid, worker_pid=worker_pid, api_probe_failures=failures)
        if time.monotonic() - self.last_write >= 5:
            self.write()

    def write(self):
        self.data['updated_epoch'] = time.time()
        temporary = self.path.with_suffix(f'.{os.getpid()}.tmp')
        try:
            temporary.write_text(json.dumps(self.data), encoding='utf-8')
            os.replace(temporary, self.path)
            self.last_write = time.monotonic()
        except OSError:
            # Diagnostics must never prevent process supervision.
            pass


def read_supervisor_health(path=None):
    target = Path(path) if path is not None else _path()
    try:
        with target.open(encoding='utf-8') as handle:
            data = json.loads(handle.read(16384))
        if not isinstance(data, dict) or data.get('revision') != 'service-resilience-v1':
            return None
        age = max(0, round(time.time() - float(data['updated_epoch'])))
        return {**data, 'heartbeat_age_seconds': age, 'healthy': age <= 30}
    except (OSError, ValueError, TypeError, KeyError):
        return None
