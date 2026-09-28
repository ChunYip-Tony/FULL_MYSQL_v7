"""Compatibility shim for FULL MYSQL Web App V2.

Canonical V2 business/data runtime lives in webapp_v2_runtime.py.
Keep this module import-compatible for older internal references.
"""

from webapp_v2_runtime import *  # noqa: F401,F403
