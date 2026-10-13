from __future__ import annotations

import re
from functools import wraps

_BRAND = re.compile(r"\bYip[Mm]an\b")


def rename_display(value: str) -> str:
    # Keep routes, storage keys, API names and JavaScript identifiers stable.
    return _BRAND.sub("FishFinder", value).replace("Data Center", "Fish Base")


def install_fishfinder_brand(api) -> None:
    for name in (
        "yipman_html", "yipman_v1_html", "yipman_manifest",
        "yipman_v1_manifest", "yipman_v1_install_html", "yipman_v1_exit_html",
    ):
        original = getattr(api, name, None)
        if original is None or getattr(original, "_fishfinder_brand", False):
            continue

        @wraps(original)
        def branded(*args, _original=original, **kwargs):
            return rename_display(_original(*args, **kwargs))

        branded._fishfinder_brand = True
        setattr(api, name, branded)
