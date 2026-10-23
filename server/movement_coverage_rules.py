from __future__ import annotations

import re
from datetime import date
from typing import Any


_DAILY_MVT_STEM = re.compile(
    r"^(?:sf[-_ ]*)?mvt[-_ ]*(?:\d{6}|\d{8})(?:[-_ ]*full)?$",
    re.IGNORECASE,
)

_RANGE_MVT_STEM = re.compile(
    r"^(?:(?:sf|all)[-_ ]*)?mvt[-_ ]*(\d{6}|\d{8})[-_ ]+(\d{6}|\d{8})(?:[-_ ]*full)?$",
    re.IGNORECASE,
)


def _filename_token_date(token: str) -> date | None:
    text = str(token or "").strip()
    try:
        if len(text) == 8 and text.startswith("20"):
            return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
        if len(text) == 6:
            return date(2000 + int(text[4:6]), int(text[:2]), int(text[2:4]))
    except ValueError:
        return None
    return None


def movement_closed_range_filename_evidence(
    *,
    original_filename: str | None,
    coverage_start_date: date | None,
    coverage_end_date: date | None,
    business_date: date,
) -> tuple[bool, str | None]:
    """Recognize an exact date-only closed MVT range export.

    Example:
      sf-mvt-093026-100126.xls -> closed range 2026-09-30 through 2026-10-01

    The filename range must exactly match the parsed posting-date coverage.
    No extra timestamp token is allowed, so intraday/provisional exports do not
    qualify through this rule.
    """
    filename = str(original_filename or "").strip()
    if not filename or coverage_start_date is None or coverage_end_date is None:
        return False, None
    stem = filename.rsplit(".", 1)[0]
    m = _RANGE_MVT_STEM.fullmatch(stem)
    if not m:
        return False, None
    d1 = _filename_token_date(m.group(1))
    d2 = _filename_token_date(m.group(2))
    if d1 is None or d2 is None:
        return False, None
    start, end = (d1, d2) if d1 <= d2 else (d2, d1)
    if coverage_start_date != start or coverage_end_date != end:
        return False, None
    if business_date < start or business_date > end:
        return False, None
    return True, "COMPLETE_DATE_ONLY_MVT_RANGE_FILENAME_CONTRACT"


def movement_daily_close_filename_evidence(
    *,
    original_filename: str | None,
    filename_date_candidate: date | None,
    filename_time_candidate: str | None,
    coverage_start_date: date | None,
    coverage_end_date: date | None,
    business_date: date,
) -> tuple[bool, str | None]:
    """Recognize the store's closed-day MVT filename contract.

    Safety rules:
    - only an exact one-business-day movement file can qualify;
    - its structured filename date must equal that business date;
    - any explicit filename time means intraday/provisional and does NOT qualify;
    - only the established date-only MVT naming family is accepted.

    Examples:
      sf-mvt-092726.xls        -> closed daily export
      sf-mvt-092726-full.xls   -> closed daily export
      sf-mvt-092726-1630.xls   -> intraday, not closed
      mvt-092826-1420.xls      -> intraday, not closed

    Upload time is intentionally not evidence of source completeness.
    """
    if coverage_start_date != business_date or coverage_end_date != business_date:
        return False, None
    if filename_date_candidate != business_date:
        return False, None
    if str(filename_time_candidate or "").strip():
        return False, None

    filename = str(original_filename or "").strip()
    if not filename:
        return False, None
    stem = filename.rsplit(".", 1)[0]
    if not _DAILY_MVT_STEM.fullmatch(stem):
        return False, None

    reason = (
        "COMPLETE_EXPLICIT_FULL_FILENAME"
        if re.search(r"(?:^|[-_ ])full$", stem, re.IGNORECASE)
        else "COMPLETE_DATE_ONLY_MVT_FILENAME_CONTRACT"
    )
    return True, reason

