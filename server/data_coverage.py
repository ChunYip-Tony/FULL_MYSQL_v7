from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from db import db_conn
from business_clock import business_today, completed_through_date
from movement_coverage_rules import movement_daily_close_filename_evidence

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


def _movement_snapshot_completeness(row: dict[str, Any], business_date: date) -> str | None:
    """Return the exact source-backed reason a movement day is complete.

    Authority order:
    1) the source was generated on a later date than the posting business day;
    2) the source matches the store's exact closed-day, date-only MVT filename
       contract for a one-day report.

    Upload timestamp is never used as completeness evidence.
    """
    snapshot_date = _source_snapshot_date(row)
    if snapshot_date is not None and snapshot_date > business_date:
        return 'COMPLETE_AFTER_BUSINESS_DATE'

    ok, reason = movement_daily_close_filename_evidence(
        original_filename=row.get('original_filename'),
        filename_date_candidate=_as_date(row.get('filename_date_candidate')),
        filename_time_candidate=row.get('filename_time_candidate'),
        coverage_start_date=_as_date(row.get('coverage_start_date')),
        coverage_end_date=_as_date(row.get('coverage_end_date')),
        business_date=business_date,
    )
    return reason if ok else None


def _movement_daily_snapshot_complete(row: dict[str, Any], business_date: date) -> bool:
    return _movement_snapshot_completeness(row, business_date) is not None


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """SELECT 1
           FROM information_schema.TABLES
           WHERE TABLE_SCHEMA=DATABASE()
             AND TABLE_NAME=%s
           LIMIT 1""",
        (table_name,),
    )
    return bool(cur.fetchone())


def _as_datetime(v: Any) -> datetime | None:
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


def _candidate_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """Authority first, then latest source chronology."""
    generated = _as_datetime(row.get('report_generated_at')) or datetime.min
    filename_date = _as_date(row.get('filename_date_candidate')) or date.min
    filename_time = str(row.get('filename_time_candidate') or '')
    uploaded = _as_datetime(row.get('upload_timestamp')) or datetime.min
    return (
        int(row.get('_authority_rank') or 0),
        generated,
        filename_date,
        filename_time,
        uploaded,
        int(row.get('file_id') or 0),
    )


def _date_span(start: date, end: date) -> list[date]:
    out: list[date] = []
    d = start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def source_data_days(cur, source_type: str, *, limit: int | None = None,
                     include_batch_id: int | None = None, up_to: date | None = None) -> list[dict[str, Any]]:
    """Return canonical valid data days, newest first.

    Daily authority can come from:
    - DIRECT_SINGLE_DATE: explicit one-day source file.
    - DERIVED_PERIOD_RESIDUAL (POS only): exactly one missing day solved by
      period totals minus all already-canonical daily days at price-type grain.
    - MULTI_DATE_ROW_EXACT (movement only): a multi-date MVT file whose rows
      carry exact posting_date; each completed posting date can be canonical.

    Direct one-day evidence outranks a derived POS residual for the same date.
    Movement candidates must be produced after the posting business date.
    RAW/history are never deleted.
    """
    params: list[Any] = [source_type]
    current_clause = ''
    if include_batch_id is not None:
        current_clause = ' OR f.batch_id=%s'
        params.append(include_batch_id)

    cur.execute(
        f"""SELECT f.file_id,f.batch_id,f.original_filename,f.source_type,f.processing_status,f.error_count,
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
              AND (p.batch_id IS NOT NULL{current_clause})""",
        tuple(params),
    )
    eligible_files = cur.fetchall()
    by_file = {int(r['file_id']): r for r in eligible_files}
    candidates: list[dict[str, Any]] = []

    # Explicit single-day files.
    for r in eligible_files:
        d = _file_business_date(r, source_type)
        if d is None:
            continue
        if up_to is not None and d > up_to:
            continue
        if source_type == 'movement' and not _movement_daily_snapshot_complete(r, d):
            continue
        candidates.append({
            'date': d,
            'file_id': int(r['file_id']),
            'batch_id': int(r['batch_id']),
            'original_filename': r.get('original_filename'),
            'report_generated_at': r.get('report_generated_at'),
            'filename_date_candidate': r.get('filename_date_candidate'),
            'filename_time_candidate': r.get('filename_time_candidate'),
            'upload_timestamp': r.get('upload_timestamp'),
            'source_snapshot_date': _source_snapshot_date(r),
            'snapshot_completeness': (
                _movement_snapshot_completeness(r, d)
                if source_type == 'movement'
                else 'NOT_APPLICABLE'
            ),
            'coverage_kind': 'DIRECT_SINGLE_DATE',
            '_authority_rank': 30,
        })

    # Movement multi-date authority:
    # 1) If the source explicitly declares a header period, every date in that
    #    period is covered; a date with no rows is a verified zero-movement day.
    # 2) Without explicit period evidence, only dates actually present in
    #    movement_history.posting_date are eligible. This remains fail-closed.
    if source_type == 'movement' and eligible_files:
        candidate_dates_by_file: dict[int, set[date]] = {}

        fallback_file_ids: list[int] = []
        for r in eligible_files:
            fid = int(r['file_id'])
            hs = _as_date(r.get('header_period_start_date'))
            he = _as_date(r.get('header_period_end_date'))
            if hs is not None and he is not None and hs <= he:
                candidate_dates_by_file[fid] = set(_date_span(hs, he))
            else:
                fallback_file_ids.append(fid)

        if fallback_file_ids:
            placeholders = ','.join(['%s'] * len(fallback_file_ids))
            cur.execute(
                f"""SELECT DISTINCT file_id,posting_date
                    FROM movement_history
                    WHERE file_id IN ({placeholders})
                      AND posting_date IS NOT NULL
                    ORDER BY posting_date,file_id""",
                tuple(fallback_file_ids),
            )
            for x in cur.fetchall():
                fid = int(x['file_id'])
                d = _as_date(x.get('posting_date'))
                if d is not None:
                    candidate_dates_by_file.setdefault(fid, set()).add(d)

        for fid, candidate_dates in candidate_dates_by_file.items():
            r = by_file.get(fid)
            if r is None:
                continue
            direct_day = _file_business_date(r, source_type)
            for d in sorted(candidate_dates):
                if up_to is not None and d > up_to:
                    continue
                if not _movement_daily_snapshot_complete(r, d):
                    continue
                candidates.append({
                    'date': d,
                    'file_id': fid,
                    'batch_id': int(r['batch_id']),
                    'original_filename': r.get('original_filename'),
                    'report_generated_at': r.get('report_generated_at'),
                    'filename_date_candidate': r.get('filename_date_candidate'),
                    'filename_time_candidate': r.get('filename_time_candidate'),
                    'upload_timestamp': r.get('upload_timestamp'),
                    'source_snapshot_date': _source_snapshot_date(r),
                    'snapshot_completeness': _movement_snapshot_completeness(r, d),
                    'coverage_kind': (
                        'DIRECT_SINGLE_DATE'
                        if direct_day == d
                        else (
                            'MULTI_DATE_PERIOD_EXACT'
                            if r.get('header_period_start_date') is not None
                               and r.get('header_period_end_date') is not None
                            else 'MULTI_DATE_ROW_EXACT'
                        )
                    ),
                    '_authority_rank': 30 if direct_day == d else 25,
                })

    # POS range reports are aggregates and cannot normally become daily coverage.
    # The only exception is an explicitly materialized one-missing-day residual.
    if source_type == 'sales_by_price_type' and _table_exists(cur, 'pos_daily_backfill_coverage'):
        args: list[Any] = []
        batch_clause = ''
        if include_batch_id is not None:
            batch_clause = ' OR b.source_batch_id=%s'
            args.append(include_batch_id)
        cur.execute(
            f"""SELECT b.business_date,b.source_file_id AS file_id,
                       b.source_batch_id AS batch_id,b.derivation_method,
                       f.report_generated_at,f.filename_date_candidate,
                       f.filename_time_candidate,f.upload_timestamp,
                       p.batch_id AS phase3_batch_id
                FROM pos_daily_backfill_coverage b
                JOIN ingest_file f ON f.file_id=b.source_file_id
                LEFT JOIN phase3_batch_result p ON p.batch_id=b.source_batch_id
                WHERE b.backfill_status='READY'
                  AND (p.batch_id IS NOT NULL{batch_clause})
                ORDER BY b.business_date,b.source_file_id""",
            tuple(args),
        )
        for r in cur.fetchall():
            d = _as_date(r.get('business_date'))
            if d is None:
                continue
            if up_to is not None and d > up_to:
                continue
            candidates.append({
                'date': d,
                'file_id': int(r['file_id']),
                'batch_id': int(r['batch_id']),
                'report_generated_at': r.get('report_generated_at'),
                'filename_date_candidate': r.get('filename_date_candidate'),
                'filename_time_candidate': r.get('filename_time_candidate'),
                'upload_timestamp': r.get('upload_timestamp'),
                'source_snapshot_date': _source_snapshot_date(r),
                'snapshot_completeness': 'DERIVED_FROM_COMPLETE_PERIOD',
                'coverage_kind': 'DERIVED_PERIOD_RESIDUAL',
                'derivation_method': r.get('derivation_method'),
                '_authority_rank': 20,
            })

    # Canonicalize one source per business date. Higher authority wins first;
    # ties use the existing latest-source chronology rule.
    by_date: dict[date, dict[str, Any]] = {}
    for r in candidates:
        d = r['date']
        prev = by_date.get(d)
        if prev is None or _candidate_sort_key(r) > _candidate_sort_key(prev):
            by_date[d] = r

    out = []
    for d in sorted(by_date, reverse=True):
        row = dict(by_date[d])
        row.pop('_authority_rank', None)
        out.append(row)
    return out[:limit] if limit is not None else out


def coverage_summary(cur, source_type: str, *, include_batch_id: int | None = None,
                     expected_through: date | None = None, lookback_days: int = 35) -> dict[str, Any]:
    expected = expected_through if expected_through is not None else completed_through_date()
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


SNAPSHOT_HEALTH_SOURCES = {
    'PRICE': 'price_list',
    'OH': 'on_hand',
    'LIVE_FRESH': 'live_fresh_suggestion',
    'FROZEN': 'frozen_inventory',
}


def _health_file_date(row: dict[str, Any]) -> date | None:
    """Best source-evidenced date for Data Health snapshot display."""
    generated = _as_datetime(row.get('report_generated_at'))
    candidates = [
        generated.date() if generated else None,
        _as_date(row.get('filename_date_candidate')),
        _as_date(row.get('coverage_end_date')),
        _as_date(row.get('coverage_start_date')),
    ]
    return next((d for d in candidates if d is not None), None)


def data_health_14_day_board(*, days: int = 14) -> dict[str, Any]:
    """Return newest-first Data Health board for required daily + snapshot sources.

    POS/MVT are required through completed_through_date(). Snapshot sources are
    informational updates: absence on a given day is not itself an error.
    """
    span = max(1, min(int(days or 14), 31))
    today = business_today()
    completed = completed_through_date()
    start = today - timedelta(days=span - 1)

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            pos_days = source_data_days(
                cur, 'sales_by_price_type', up_to=completed
            )
            mvt_days = source_data_days(
                cur, 'movement', up_to=completed
            )
            pos_by_date = {x['date']: dict(x) for x in pos_days if x['date'] >= start}
            mvt_by_date = {x['date']: dict(x) for x in mvt_days if x['date'] >= start}

            cur.execute(
                """SELECT file_id,batch_id,original_filename,source_type,
                          processing_status,error_count,duplicate_of_file_id,
                          coverage_start_date,coverage_end_date,
                          filename_date_candidate,report_generated_at,upload_timestamp
                   FROM ingest_file
                   WHERE source_type IN ('price_list','on_hand','live_fresh_suggestion','frozen_inventory')
                     AND processing_status='INGESTED'
                     AND COALESCE(error_count,0)=0
                     AND duplicate_of_file_id IS NULL
                   ORDER BY file_id DESC"""
            )
            snap_by_source_date: dict[tuple[str,date], dict[str,Any]] = {}
            for row in cur.fetchall():
                d = _health_file_date(row)
                if d is None or d < start or d > today:
                    continue
                key = (str(row.get('source_type') or ''), d)
                if key not in snap_by_source_date:
                    snap_by_source_date[key] = dict(row)

            labels = {
                'PRICE':'price_list',
                'OH':'on_hand',
                'LIVE_FRESH':'live_fresh_suggestion',
                'FROZEN':'frozen_inventory',
            }

            rows = []
            for offset in range(span):
                d = today - timedelta(days=offset)
                required = d <= completed
                p = pos_by_date.get(d)
                m = mvt_by_date.get(d)

                def daily_cell(obs: dict[str,Any] | None) -> dict[str,Any]:
                    if not required:
                        return {'status':'NOT_DUE','file':None,'batch_id':None,'source_type':None}
                    if not obs:
                        return {'status':'MISSING','file':None,'batch_id':None,'source_type':None}
                    return {
                        'status':'OK',
                        'file':obs.get('original_filename'),
                        'batch_id':obs.get('batch_id'),
                        'file_id':obs.get('file_id'),
                        'coverage_kind':obs.get('coverage_kind'),
                        'source_type':obs.get('source_type'),
                    }

                sources = {
                    'POS': daily_cell(p),
                    'MVT': daily_cell(m),
                }
                for label, source_type in labels.items():
                    obs = snap_by_source_date.get((source_type,d))
                    sources[label] = (
                        {
                            'status':'OK',
                            'file':obs.get('original_filename'),
                            'batch_id':obs.get('batch_id'),
                            'file_id':obs.get('file_id'),
                            'source_type':source_type,
                        }
                        if obs else
                        {
                            'status':'NONE',
                            'file':None,
                            'batch_id':None,
                            'file_id':None,
                            'source_type':source_type,
                        }
                    )

                missing_required = [
                    name for name in ('POS','MVT')
                    if sources[name]['status']=='MISSING'
                ]
                overall = (
                    'MISSING' if missing_required
                    else ('COMPLETE' if required else 'CURRENT_DAY')
                )
                rows.append({
                    'date':d,
                    'weekday':d.strftime('%a'),
                    'required_daily_due':required,
                    'overall_status':overall,
                    'missing_required':missing_required,
                    'sources':sources,
                })

            latest: dict[str,Any] = {}
            for label, source_type in labels.items():
                dates = [d for (st,d) in snap_by_source_date if st == source_type]
                last = max(dates) if dates else None
                latest[label] = {
                    'date':last,
                    'file':(
                        snap_by_source_date[(source_type,last)].get('original_filename')
                        if last else None
                    ),
                }
            latest['POS'] = {
                'date':max(pos_by_date) if pos_by_date else None,
                'file':pos_by_date[max(pos_by_date)].get('original_filename') if pos_by_date else None,
            }
            latest['MVT'] = {
                'date':max(mvt_by_date) if mvt_by_date else None,
                'file':mvt_by_date[max(mvt_by_date)].get('original_filename') if mvt_by_date else None,
            }

            return {
                'contract_version':'DATA_HEALTH_14_DAY_V1',
                'window_days':span,
                'today':today,
                'completed_through':completed,
                'rows':rows,
                'latest':latest,
                'rules':{
                    'sort':'MOST_RECENT_FIRST',
                    'daily_required':['POS','MVT'],
                    'snapshot_sources':['PRICE','OH','LIVE_FRESH','FROZEN'],
                    'current_day_required_status':'NOT_DUE_UNTIL_COMPLETED',
                },
            }
        finally:
            cur.close()
