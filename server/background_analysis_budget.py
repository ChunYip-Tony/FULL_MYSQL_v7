"""Bound peak memory of optional background analyses in the shared API process."""
from functools import wraps
from contextlib import contextmanager
from threading import RLock, Lock
import time

_BACKGROUND_ANALYSIS_LOCK = RLock()
_STATUS_LOCK = Lock()
_STATUS = {'active': None, 'started': None, 'waiting': 0}


def background_analysis_status():
    with _STATUS_LOCK:
        return {'active': _STATUS['active'], 'waiting': _STATUS['waiting'],
                'elapsed_seconds': round(time.monotonic() - _STATUS['started'], 1)
                if _STATUS['started'] is not None else None}


@contextmanager
def background_analysis(name):
    with _STATUS_LOCK:
        _STATUS['waiting'] += 1
    with _BACKGROUND_ANALYSIS_LOCK:
        with _STATUS_LOCK:
            _STATUS['waiting'] -= 1
            previous = (_STATUS['active'], _STATUS['started'])
            _STATUS.update(active=name, started=time.monotonic())
        try:
            yield
        finally:
            with _STATUS_LOCK:
                _STATUS.update(active=previous[0], started=previous[1])

def serialized_background(fn):
    @wraps(fn)
    def run(*args, **kwargs):
        with background_analysis(fn.__name__):
            return fn(*args, **kwargs)
    return run

