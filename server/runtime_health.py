"""Small, non-sensitive process diagnostics for the no-database health check."""
import os
import time
import resource
from pathlib import Path

_STARTED = time.monotonic()


def runtime_health(root=Path('/sys/fs/cgroup')):
    out = {'revision': 'bounded-pricing-reads-v1', 'pid': os.getpid(),
           'uptime_seconds': round(time.monotonic() - _STARTED)}
    out['process_peak_mb'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    try:
        resident = int(Path('/proc/self/statm').read_text().split()[1])
        out['process_memory_mb'] = round(resident * os.sysconf('SC_PAGE_SIZE') / 1048576, 1)
    except (OSError, ValueError, IndexError):
        pass
    for filename, key in [('memory.current', 'memory_mb'), ('memory.peak', 'peak_memory_mb'),
                          ('memory.max', 'memory_limit_mb')]:
        try:
            value = (root / filename).read_text().strip()
            out[key] = round(int(value) / 1048576, 1) if value != 'max' else None
        except (OSError, ValueError):
            pass
    try:
        events = dict(line.split() for line in (root / 'memory.events').read_text().splitlines())
        out['oom_kills'] = int(events.get('oom_kill', 0))
    except (OSError, ValueError):
        pass
    return out
