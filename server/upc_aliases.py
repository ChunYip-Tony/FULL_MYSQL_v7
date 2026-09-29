from __future__ import annotations

import re
from typing import Any

SERVICE_249_PREFIX = "249"


def numeric_digits(value: Any) -> str | None:
    """Return digits-only numeric text with leading zeroes removed."""
    if value is None:
        return None
    s=str(value).strip()
    if not re.fullmatch(r"\d+",s):
        return None
    s=s.lstrip("0")
    return s or "0"


def service_249_product_code(value: Any) -> str | None:
    """Return the six-digit 249 service product code.

    Store #1032 Seafood service UPCs use one canonical roster shape:
      249 + 3-digit product code + 00000
    Source exports may shorten that base identifier or emit a scale-derived
    barcode with additional trailing digits.  The first six digits are the
    stable service-product identity.  Callers must still require an exact
    authoritative canonical base UPC hit before resolving an alias.
    """
    s=numeric_digits(value)
    if not s or len(s)<6 or not s.startswith(SERVICE_249_PREFIX):
        return None
    return s[:6]


def service_249_canonical_base(value: Any) -> str | None:
    code=service_249_product_code(value)
    if not code:
        return None
    return code + "00000"


def service_249_source_prefix(value: Any) -> str | None:
    """SQL LIKE prefix for raw POS/Price-List service identifiers."""
    return service_249_product_code(value)
