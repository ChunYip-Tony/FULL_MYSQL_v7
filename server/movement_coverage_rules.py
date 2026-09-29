from __future__ import annotations

import re
from datetime import date
from typing import Any


_DAILY_MVT_STEM = re.compile(
    r"^(?:sf[-_ ]*)?mvt[-_ ]*(?:\d{6}|\d{8})(?:[-_ ]*full)?$",
    re.IGNORECASE,
)


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
