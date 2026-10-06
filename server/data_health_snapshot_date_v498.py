from __future__ import annotations

"""Data Health snapshot-date repair for legacy snapshot files.

Some Frozen Inventory reports are named like ``F INV 1002.xlsx``. Older ingest
rows can have a valid source_type=frozen_inventory but no populated
report_generated_at / coverage / filename_date_candidate fields. Data Health
therefore showed Frozen as "—" even though the file was correctly classified
and published.

This patch preserves the existing source-evidence authority order. Only when
all existing structured date evidence is absent do we derive an MMDD date from
an explicitly recognized snapshot filename. Upload time is used only to infer
the year, never as the snapshot business date itself.
"""

from datetime import date, datetime, timedelta
import re
import data_coverage as _dc

_APPLIED = False
_BASE = _dc._health_file_date

_FROZEN_PATTERNS = (
    re.compile(r'(?i)\bF\s*INV\s*[-_ ]*([01]\d)([0-3]\d)\b'),
    re.compile(r'(?i)\bFROZEN(?:\s+INV(?:ENTORY)?)?\s*[-_ ]*([01]\d)([0-3]\d)\b'),
)

_LIVE_FRESH_PATTERNS = (
    re.compile(r'(?i)\b(?:LIVE|FRESH|L\s*F)\s*(?:INV|REPORT|SUGGESTION)?\s*[-_ ]*([01]\d)([0-3]\d)\b'),
)


def _dt(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, datetime.min.time())
    if v is None:
        return None
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        return None


def _infer_mmdd(filename: str, anchor: date, patterns) -> date | None:
    text=str(filename or '')
    for pat in patterns:
        m=pat.search(text)
        if not m:
            continue
        month=int(m.group(1)); day=int(m.group(2))
        try:
            candidate=date(anchor.year,month,day)
        except ValueError:
            return None
        # Filename MMDD usually belongs to the report uploaded near that date.
        # If it would be implausibly far in the future, treat it as prior year.
        if candidate > anchor + timedelta(days=31):
            try: candidate=date(anchor.year-1,month,day)
            except ValueError: return None
        return candidate
    return None


def _health_file_date_v498(row):
    existing=_BASE(row)
    if existing is not None:
        return existing

    source=str(row.get('source_type') or '').lower()
    uploaded=_dt(row.get('upload_timestamp'))
    anchor=(uploaded.date() if uploaded else _dc.business_today())
    filename=str(row.get('original_filename') or '')

    if source=='frozen_inventory':
        return _infer_mmdd(filename,anchor,_FROZEN_PATTERNS)
    if source=='live_fresh_suggestion':
        return _infer_mmdd(filename,anchor,_LIVE_FRESH_PATTERNS)
    return None


def apply_snapshot_date_patch() -> None:
    global _APPLIED
    if _APPLIED:
        return
    _dc._health_file_date=_health_file_date_v498
    _APPLIED=True
