"""Small, non-sensitive process diagnostics for the no-database health check."""
import os
import time
import resource
from pathlib import Path

_STARTED = time.monotonic()


def runtime_health(root=Path('/sys/fs/cgroup')):
    out = {'revision': 'bounded-pricing-reads-v1', 'pid': os.getpid(),
           'uptime_seconds': round(time.monotonic() - _STARTED)}
    out['uptime_source'] = 'diagnostics_module'
    try:
        # /proc stat field 22 is the process start time in clock ticks. The
        # command name in parentheses can itself contain spaces/parentheses.
        fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
        start_seconds = int(fields[19]) / os.sysconf('SC_CLK_TCK')
        system_seconds = float(Path('/proc/uptime').read_text().split()[0])
        out['uptime_seconds'] = max(0, round(system_seconds - start_seconds))
        out['uptime_source'] = 'process'
    except (OSError, ValueError, IndexError):
        pass
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
            out[key] = (None if value == 'max' or key == 'memory_limit_mb' and int(value) >= 2**60
                        else round(int(value) / 1048576, 1))
        except (OSError, ValueError):
            pass
    try:
        events = dict(line.split() for line in (root / 'memory.events').read_text().splitlines())
        out['oom_kills'] = int(events.get('oom_kill', 0))
    except (OSError, ValueError):
        pass
    # App Platform may expose a v1 memory controller rather than cgroup v2.
    if 'memory_mb' not in out:
        for filename, key in [('memory.usage_in_bytes', 'memory_mb'),
                              ('memory.max_usage_in_bytes', 'peak_memory_mb'),
                              ('memory.limit_in_bytes', 'memory_limit_mb')]:
            try:
                value = int((root / 'memory' / filename).read_text())
                out[key] = None if key == 'memory_limit_mb' and value >= 2**60 else round(value / 1048576, 1)
            except (OSError, ValueError):
                pass
    from supervisor_health import read_supervisor_health
    from request_capacity import capacity_status
    out['supervisor'] = read_supervisor_health()
    out['request_capacity'] = capacity_status()
    return out
