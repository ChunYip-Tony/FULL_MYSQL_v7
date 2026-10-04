from __future__ import annotations

"""Stable Desktop UI import surface.

The versioned module remains in the repository as an implementation snapshot,
but production code imports this stable module so the product channel does not
change names every time the desktop implementation is revised.
"""

try:
    from .yipman_desktop_v369 import YIPMAN_DESKTOP_CSS, YIPMAN_DESKTOP_JS
except ImportError:
    from yipman_desktop_v369 import YIPMAN_DESKTOP_CSS, YIPMAN_DESKTOP_JS

__all__ = ["YIPMAN_DESKTOP_CSS", "YIPMAN_DESKTOP_JS"]
