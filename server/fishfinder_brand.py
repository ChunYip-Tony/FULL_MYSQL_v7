from __future__ import annotations

import re
from functools import wraps
from pathlib import Path

_OCEAN_CSS = Path(__file__).with_name("fishfinder_ocean.css").read_text(encoding="utf-8")

_BRAND = re.compile(r"\b(?:Yip[Mm]an|YIPMAN)\b")
_ICON = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAjCAYAAAATx8MeAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAAEnQAABJ0Ad5mH3gAAADGSURBVFhHY2SX4P3PMMgAE7rAYACD0lGMyNEX97wGVZZOYJFkCwp/UIbUqKOIBaOOIhYMSkeRXiTcPcKwVm8Hwwd0cWxAy4Mh7LQNAy+6OBoYCUUCCwOXNC9uLMOKroEoQFn0ERk9hMBIiD7agEHpKMrSFAMLA5c0J7oKBqHSNAb3VEF0YZyAymnqD8O3p58x8Jev6OpIAxQ6ijaAsugbLRIGGIw6ilgwKB1Feu6jARjNfeSCUUcRC0YdRSxAKRIGCxiUIQUANoNGD4gEd7wAAAAASUVORK5CYII="



def rename_display(value: str) -> str:
    # Keep routes, storage keys, API names and JavaScript identifiers stable.
    value = value.replace("YIPMAN WORK", "FishFinder · Fish Watch")
    value = _BRAND.sub("FishFinder", value).replace("Data Center", "Fish Base")
    if "</head>" in value:
        # Each host needs its own favicon; the Fish Watch icon cannot brand Fish Base.
        value = re.sub(r'<link\b[^>]*\brel=["\\\'](?:shortcut )?icon["\\\'][^>]*>', "", value, flags=re.I)
        value = value.replace("</head>", '<link rel="icon" type="image/png" href="' + _ICON + '"></head>')
    if "</body>" in value and 'id="fishfinder-ocean-theme"' not in value:
        value = value.replace("</body>", '<style id="fishfinder-ocean-theme">' + _OCEAN_CSS + "</style></body>", 1)
        value = re.sub(r'(<meta\b[^>]*name=["\']theme-color["\'][^>]*content=["\'])[^"\']+', r"\g<1>#f3f7fa", value, flags=re.I)
    return value


def install_fishfinder_brand(api) -> None:
    for name in (
        "yipman_html", "backoffice_html", "data_center_html", "yipman_v1_html", "yipman_manifest",
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

