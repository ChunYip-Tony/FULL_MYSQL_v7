from __future__ import annotations

import re
from typing import Any

SERVICE_249_PREFIX = "249"

def normalize_selling_description(value: Any) -> str:
    """Normalize POS/roster descriptions for conservative exact matching."""
    s=str(value or "").upper().strip()
    s=re.sub(r"[^A-Z0-9]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()


def looks_like_249_service_description(value: Any) -> bool:
    """True only for explicit fried/cook service descriptions."""
    s=normalize_selling_description(value)
    if not s or "SERVICE" not in s:
        return False
    tokens=set(s.split())
    return bool(tokens.intersection({"FRIED","FRY","COOK","COOKED"}))



def numeric_digits(value: Any) -> str | None:
    """Return digits-only numeric text with leading zeroes removed."""
    if value is None:
        return None
    s=str(value).strip()
    if not re.fullmatch(r"\d+",s):
        return None
    s=s.lstrip("0")
    return s or "0"


def digits_only(value: Any) -> str | None:
    """Return a digits-only source spelling while preserving leading zeroes."""
    if value is None:
        return None
    s=str(value).strip()
    if not re.fullmatch(r"\d+",s):
        return None
    return s


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


def _upca_check_digit(body11: str) -> str | None:
    if not re.fullmatch(r"\d{11}", str(body11 or "")):
        return None
    digits=[int(x) for x in body11]
    total=sum(digits[0::2])*3 + sum(digits[1::2])
    return str((10-(total % 10)) % 10)


def _ean13_check_digit(body12: str) -> str | None:
    if not re.fullmatch(r"\d{12}", str(body12 or "")):
        return None
    digits=[int(x) for x in body12]
    total=sum(digits[0::2]) + sum(digits[1::2])*3
    return str((10-(total % 10)) % 10)


def retail_barcode_alias_candidates(value: Any) -> list[str]:
    """Canonical candidates for shortened raw UPC/EAN source identifiers.

    Candidates are never authority by themselves; callers must require an exact
    existing canonical roster hit before using one.
    """
    s=digits_only(value)
    if not s:
        return []
    out: list[str]=[]
    if len(s)==12:
        cd=_ean13_check_digit(s)
        if cd is not None:
            out.append(s+cd)
    elif len(s)==11:
        cd=_upca_check_digit(s)
        if cd is not None:
            out.append(s+cd)
    elif len(s)==10:
        body="0"+s
        cd=_upca_check_digit(body)
        if cd is not None:
            out.append(body+cd)
    return out


def source_barcode_aliases(canonical_value: Any) -> list[str]:
    """Safe raw-source spellings for one canonical retail barcode.

    This is the reverse of retail_barcode_alias_candidates() and covers only
    deterministic missing-check-digit forms. Leading-zero equivalence is handled
    separately by the SQL lineage predicate.
    """
    s=digits_only(canonical_value)
    if not s:
        return []
    out: list[str]=[]
    if len(s)==13:
        body=s[:12]
        if _ean13_check_digit(body)==s[-1]:
            out.append(body)
    elif len(s)==12:
        body=s[:11]
        if _upca_check_digit(body)==s[-1]:
            out.append(body)
            if s.startswith("0"):
                out.append(body[1:])
    return list(dict.fromkeys(x for x in out if x and x!=s))


def source_ean_predicate(column: str, canonical_value: Any) -> tuple[str, tuple[Any, ...]]:
    """SQL predicate for canonical UPC plus safe raw-source aliases.

    Covers:
      - exact raw EAN/UPC,
      - numeric leading-zero equivalence,
      - canonical 249 service prefix aliases,
      - deterministic shortened UPC-A/EAN forms.

    A shortened retail spelling is NOT treated as an alias when that spelling
    is itself an ACTIVE selling_upc. This prevents one active short UPC from
    being counted again under a separate long/check-digit UPC.
    """
    ean=str(canonical_value or "").strip()
    if not ean:
        return "1=0", tuple()
    parts=[f"{column}=%s"]
    args: list[Any]=[ean]
    key=numeric_digits(ean)
    if key:
        numeric_only=f"({column}<>'' AND {column} NOT REGEXP '[^0-9]')"
        parts.append(f"({numeric_only} AND TRIM(LEADING '0' FROM {column})=%s)")
        args.append(key)
    service_prefix=service_249_source_prefix(ean)
    if service_prefix:
        parts.append(f"{column} LIKE %s")
        args.append(service_prefix+"%")
    for alias in source_barcode_aliases(ean):
        parts.append(
            f"({column}=%s AND NOT EXISTS ("
            "SELECT 1 FROM selling_upc alias_su "
            "WHERE alias_su.ean_upc=%s "
            "AND alias_su.record_status='ACTIVE'"
            "))"
        )
        args.extend([alias,alias])
    return "("+" OR ".join(parts)+")", tuple(args)
