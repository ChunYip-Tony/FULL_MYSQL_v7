from __future__ import annotations

"""Compatibility import for the retired responsive/mobile-v2 layer.

This module is not an official product channel. It exists only because the
legacy /app/yipman compatibility shell still carries these assets for older
clients and for the shared responsive implementation. New mobile work belongs
to Yipman Mobile V1 at /app/yipman-v1/.
"""

try:
    from .yipman_mobile_v2 import YIPMAN_MOBILE_V2_CSS, YIPMAN_MOBILE_V2_JS
except ImportError:
    from yipman_mobile_v2 import YIPMAN_MOBILE_V2_CSS, YIPMAN_MOBILE_V2_JS

__all__ = ["YIPMAN_MOBILE_V2_CSS", "YIPMAN_MOBILE_V2_JS"]
