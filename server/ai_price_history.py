"""Bounded, read-only posted-price evidence, separate from realized POS prices."""
import base64
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from business_clock import BUSINESS_TIMEZONE
from db import db_conn


def _day(value):
    if value is None or value == '':
        return None
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value)):
        raise ValueError('USE_ISO_DATES')
    return date.fromisoformat(value)


def posted_price_history(args):
    upc = str(args.get('upc') or '').strip()
    if not re.fullmatch(r'[0-9]{1,18}', upc):
        raise ValueError('EXACT_UPC_REQUIRED')
    start, end = _day(args.get('start_date')), _day(args.get('end_date'))
    if start and end and start > end:
        raise ValueError('START_AFTER_END')
    scope = [upc, start.isoformat() if start else None, end.isoformat() if end else None]
    filters = ["p.ean_upc=%s", "f.source_type='price_list'",
               "f.processing_status='INGESTED'", 'f.error_count=0',
               'f.duplicate_of_file_id IS NULL', 'f.upload_timestamp IS NOT NULL']
    params = [upc]
    zone = ZoneInfo(BUSINESS_TIMEZONE)
    for day, op in ((start, '>='), (end + timedelta(days=1) if end else None, '<')):
        if day:
            utc = datetime.combine(day, time.min, zone).astimezone(timezone.utc).replace(tzinfo=None)
            filters.append('f.upload_timestamp ' + op + ' %s')
            params.append(utc)
    cursor = args.get('cursor')
    if cursor:
        try:
            if not isinstance(cursor, str) or len(cursor) > 512:
                raise ValueError()
            decoded = json.loads(base64.b64decode(cursor, altchars=b'-_', validate=True))
            if decoded['scope'] != scope:
                raise ValueError()
            stamp, fid, rid = decoded['after']
            stamp = datetime.fromisoformat(stamp)
            if stamp.tzinfo is not None or any(type(n) is not int or n < 0 or n >= 2**63 for n in (fid, rid)):
                raise ValueError()
        except Exception as exc:
            raise ValueError('INVALID_PRICE_HISTORY_CURSOR') from exc
        filters.append('(f.upload_timestamp,p.file_id,p.raw_id) < (%s,%s,%s)')
        params.extend((stamp, fid, rid))
    sql = '''SELECT p.ean_upc,p.description,p.configured_price,p.price_quantity,
        p.price_type,p.source_since_date,p.snapshot_at,p.batch_id,p.file_id,
        p.sheet_id,p.raw_id,p.source_row_number,f.upload_timestamp,f.original_filename
        FROM price_list_observation p JOIN ingest_file f ON f.file_id=p.file_id
        WHERE ''' + ' AND '.join(filters) + '''
        ORDER BY f.upload_timestamp DESC,p.file_id DESC,p.raw_id DESC LIMIT 51'''
    with db_conn(read_timeout=10, connection_timeout=5) as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, tuple(params))
            fetched = cur.fetchall()
        finally:
            cur.close()
    more, rows = len(fetched) > 50, fetched[:50]
    next_cursor = None
    if more:
        last = rows[-1]
        payload = {'scope': scope, 'after': [last['upload_timestamp'].isoformat(),
                                            int(last['file_id']), int(last['raw_id'])]}
        next_cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    for row in rows:
        stamp = row['upload_timestamp'].replace(tzinfo=timezone.utc)
        row['source_business_date'] = stamp.astimezone(zone).date().isoformat()
        row['source'] = 'PRICE_LIST'
        row['historical_selling_unit'] = None
    return {
        'upc': upc, 'source': 'PRICE_LIST', 'evidence_kind': 'POSTED_PRICE_OBSERVATIONS',
        'start_date': scope[1], 'end_date': scope[2], 'rows': rows,
        'returned_count': len(rows), 'data_available': bool(rows),
        'has_more': more, 'next_cursor': next_cursor, 'matching_scan_complete': not more,
        'historical_coverage_complete': False,
        'scope': 'EXACT_UPC_PARSED_ACCEPTED_PRICE_LIST_FILES',
        'note': 'Posted price-list observations, never actual POS prices. Follow next_cursor for all matches. '
                'Upload business date is the observation date; source_since_date does not prove earlier exposure. '
                'Preserve every price type and source row; repeated tickets are not necessarily price changes. '
                'Current priority within the latest file is IN STORE, SALE, TPR, REG. Never choose current price '
                'from this historical scan alone. Historical UOM is unverified: preserve price_quantity and do '
                'not invent pack conversions. Failed/duplicate/unparsed sources are outside this scan. '
                'An exhausted scan does not establish complete calendar coverage or absence of missing uploads.'
    }
