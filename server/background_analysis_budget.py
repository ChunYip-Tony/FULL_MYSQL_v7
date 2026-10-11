"""Bound peak memory of optional background analyses in the shared API process."""
from functools import wraps
from threading import RLock

_BACKGROUND_ANALYSIS_LOCK = RLock()

def serialized_background(fn):
    @wraps(fn)
    def run(*args, **kwargs):
        with _BACKGROUND_ANALYSIS_LOCK:
            return fn(*args, **kwargs)
    return run
