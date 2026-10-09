from __future__ import annotations

"""Compatibility wrapper for the Data Center processing monitor.

Any older composition layer that still imports v499 now receives the corrected
v500 stage-aware monitor. This prevents PHASE2C_READY / QA / publish states
from being rendered as 0% merely because a stale 0/N row counter is present.
"""

from yipman_data_center_monitor_v500 import inject_data_center_monitor_v500


def inject_data_center_monitor_v499(html: str) -> str:
    return inject_data_center_monitor_v500(html)
