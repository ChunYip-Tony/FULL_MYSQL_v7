from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from db import db_conn

DAILY_REQUIRED_SOURCES = {
    'POS_SALES': 'sales_by_price_type',
    'MVT': 'movement',
}


def _as_date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if v is None:
        return None
    try:
        return datetime.fromisoformat(str(v)).date()
    except Exception:
        return None


def _file_business_date(row: dict[str, Any], source_type: str) -> date | None:
    """Return a date only when the file proves complete single-day coverage.

    A range/mixed-date report is preserved as history evidence, but it is not allowed
    to manufacture individual daily coverage days. This is especially important for
    POS reports whose multi-day sold price is a period average, not a daily event.
    """
    if source_type == 'sales_by_price_type':
        hs = _as_date(row.get('header_period_start_date'))
        he = _as_date(row.get('header_period_end_date'))
        if hs and he:
            return hs if hs == he else None
    cs = _as_date(row.get('coverage_start_date'))
    ce = _as_date(row.get('coverage_end_date'))
    if cs and ce and cs == ce:
        return cs
    return None


def _source_snapshot_date(row: dict[str, Any]) -> date | None:
    """Return the latest source-evidenced snapshot date, never upload time.

    report_generated_at and the structured filename date are both source evidence.
    Use the later proven date so a next-morning filename such as mvt-091926-0830
    can prove that a 2026-09-18 posting-day snapshot was produced after day close,
    even when an internal report date field still carries the posting date.
    """
    candidates = [
        d for d in (
            _as_date(row.get('report_generated_at')),
            _as_date(row.get('filename_date_candidate')),
        )
        if d is not None
    ]
    return max(candidates) if candidates else None


def _movement_daily_snapshot_complete(row: dict[str, Any], business_date: date) -> bool:
    """True only when a movement export proves the business day was already closed.

    FULL MYSQL movement exports observed in production include same-day intraday
    snapshots (for example 12:30) and next-morning completed snapshots for the
    prior posting date. Same-day snapshots remain preserved in RAW/history but
    must not become canonical daily movement coverage.
    """
    snapshot_date = _source_snapshot_date(row)
    return snapshot_date is not None and snapshot_date > business_date


def source_data_days(cur, source_type: str, *, limit: int | None = None,
                     include_batch_id: int | None = None, up_to: date | None = None) -> list[dict[str, Any]]:
    """Return canonical valid data days, newest first.

    Rules:
    - Only successfully ingested, error-free, non-duplicate source files qualify.
    - Only single-day coverage qualifies as a daily data day.
    - A historical batch must have reached Phase 3 at least once; the currently
      processing batch may be explicitly included.
    - Movement daily coverage is fail-closed: a same-business-date export is
      provisional/intraday evidence only. The source snapshot date must be later
      than the posting business date before the file can become canonical.
    - If multiple valid COMPLETE exports exist for one business date, choose the
      latest SOURCE snapshot chronology (report_generated_at, then filename date/time),
      using upload/file order only as a final tie-break. RAW/history are never deleted.
    """
    params: list[Any] = [source_type]
    current_clause = ''
    if include_batch_id is not None:
        current_clause = ' OR f.batch_id=%s'
        params.append(include_batch_id)
    cur.execute(
        f"""SELECT f.file_id,f.batch_id,f.source_type,f.processing_status,f.error_count,
                   f.duplicate_of_file_id,f.source_row_count,f.date_semantics_status,
                   f.coverage_type,f.coverage_start_date,f.coverage_end_date,
                   f.header_period_start_date,f.header_period_end_date,
                   f.report_generated_at,f.filename_date_candidate,f.filename_time_candidate,
                   f.upload_timestamp,p.batch_id AS phase3_batch_id
            FROM ingest_file f
            LEFT JOIN phase3_batch_result p ON p.batch_id=f.batch_id
            WHERE f.source_type=%s
              AND f.processing_status='INGESTED'
              AND f.error_count=0
              AND f.duplicate_of_file_id IS NULL
              AND f.source_row_count>0
              AND f.date_semantics_status='RESOLVED'
              AND (p.batch_id IS NOT NULL{current_clause})
            ORDER BY
              CASE WHEN f.report_generated_at IS NULL THEN 1 ELSE 0 END,
              f.report_generated_at DESC,
              CASE WHEN f.filename_date_candidate IS NULL THEN 1 ELSE 0 END,
              f.filename_date_candidate DESC,
              CASE WHEN f.filename_time_candidate IS NULL THEN 1 ELSE 0 END,
              f.filename_time_candidate DESC,
              f.upload_timestamp DESC,
              f.file_id DESC""",
        tuple(params),
    )
    by_date: dict[date, dict[str, Any]] = {}
    for r in cur.fetchall():
        d = _file_business_date(r, source_type)
        if d is None:
            continue
        if up_to is not None and d > up_to:
            continue
        if source_type == 'movement' and not _movement_daily_snapshot_complete(r, d):
            continue
        if d not in by_date:
            by_date[d] = {
                'date': d,
                'file_id': int(r['file_id']),
                'batch_id': int(r['batch_id']),
                'report_generated_at': r.get('report_generated_at'),
                'filename_date_candidate': r.get('filename_date_candidate'),
                'filename_time_candidate': r.get('filename_time_candidate'),
                'upload_timestamp': r.get('upload_timestamp'),
                'source_snapshot_date': _source_snapshot_date(r),
                'snapshot_completeness': (
                    'COMPLETE_AFTER_BUSINESS_DATE' if source_type == 'movement'
                    else 'NOT_APPLICABLE'
                ),
            }
    out = [by_date[d] for d in sorted(by_date, reverse=True)]
    return out[:limit] if limit is not None else out


def coverage_summary(cur, source_type: str, *, include_batch_id: int | None = None,
                     expected_through: date | None = None, lookback_days: int = 35) -> dict[str, Any]:
    expected = expected_through or (date.today() - timedelta(days=1))
    days = source_data_days(cur, source_type, include_batch_id=include_batch_id, up_to=expected)
    valid = {x['date'] for x in days}
    latest = max(valid) if valid else None

    floor = expected - timedelta(days=max(lookback_days, 1) - 1)
    if valid:
        start = max(min(valid), floor)
    else:
        start = floor

    missing: list[date] = []
    d = start
    while d <= expected:
        if d not in valid:
            missing.append(d)
        d += timedelta(days=1)

    status = 'CURRENT' if latest == expected and not missing else ('BACKFILL_NEEDED' if valid else 'NO_DATA')
    latest7 = sorted(valid, reverse=True)[:7]
    latest30 = sorted(valid, reverse=True)[:30]
    return {
        'source_type': source_type,
        'expected_through': expected,
        'latest_valid_date': latest,
        'status': status,
        'missing_dates': missing,
        'valid_days_in_window': len([x for x in valid if x >= start]),
        'window_start': start,
        'latest_7_data_days': sorted(latest7),
        'latest_30_data_days': sorted(latest30),
    }


def required_daily_coverage(*, lookback_days: int = 35) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            pos = coverage_summary(cur, 'sales_by_price_type', lookback_days=lookback_days)
            mvt = coverage_summary(cur, 'movement', lookback_days=lookback_days)
            return {'POS_SALES': pos, 'MVT': mvt}
        finally:
            cur.close()


def fmt_date_list(values: list[date], max_items: int = 8) -> str:
    if not values:
        return 'none'
    shown = values[-max_items:] if len(values) > max_items else values
    txt = ', '.join(d.isoformat() for d in shown)
    extra = len(values) - len(shown)
    return f'{txt} (+{extra} more)' if extra > 0 else txt
