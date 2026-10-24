"""Small, conservative progress index; detailed evidence still decides each card.

Stream one upload at a time instead of reading POS/cost/receipts for every UPC.
Missing tickets or POS newer than the ticket stay eligible for a full check.
"""
from collections import OrderedDict
from datetime import timedelta
import threading
import re

_cache = OrderedDict()
_lock = threading.Lock()
_priority = {'REG': 1, 'TPR': 2, 'SALE': 3, 'IN STORE': 4, 'IN_STORE': 4}


def positive_pos_dates(cur, identities, data_days):
    """Presence only; no sale, price, cost or recommendation is inferred here."""
    ids = {uid for uid, _ in identities}
    aliases = {}
    numeric = lambda value: re.sub(r'\D', '', str(value or '')).lstrip('0') or '0'
    for uid, ean in identities:
        aliases.setdefault(numeric(ean), set()).add(uid)
    dates = {}
    for derived in (False, True):
        days = [d for d in data_days if (d.get('coverage_kind') == 'DERIVED_PERIOD_RESIDUAL') == derived]
        if not days:
            continue
        table = 'pos_daily_backfill_observation' if derived else 'sales_period_observation'
        date_column = 'business_date' if derived else 'period_end_date'
        clauses, args = [], []
        for day in days:
            if derived:
                clauses.append('(source_file_id=%s AND business_date=%s)')
                args.extend((int(day['file_id']), day['date']))
            else:
                clauses.append('(file_id=%s AND period_start_date=%s AND period_end_date=%s)')
                args.extend((int(day['file_id']), day['date'], day['date']))
        grain = "AND temporal_grain='SINGLE_DATE'" if not derived else ''
        cur.execute(f"""SELECT upc_id,ean_upc,MAX({date_column}) AS last_date
            FROM {table} WHERE sold_quantity>0
            {grain}
            AND ({' OR '.join(clauses)}) GROUP BY upc_id,ean_upc""", tuple(args))
        while True:
            batch = cur.fetchmany(512)
            if not batch:
                break
            for row in batch:
                uid = row.get('upc_id')
                found = {uid} if uid in ids else aliases.get(numeric(row.get('ean_upc')), set())
                # Ambiguous aliases stay eligible; detailed evidence resolves them.
                for uid in found:
                    dates[uid] = max(dates.get(uid, row['last_date']), row['last_date'])
    return dates


def progress_candidates(cur, rows, today, through, data_days=None):
    from phase3 import _price_list_upload_business_date
    cur.execute("""SELECT file_id,upload_timestamp FROM ingest_file
        WHERE source_type='price_list' AND processing_status='INGESTED'
        AND error_count=0 AND duplicate_of_file_id IS NULL AND upload_timestamp IS NOT NULL
        ORDER BY upload_timestamp DESC,file_id DESC LIMIT 120""")
    files = {int(f['file_id']): _price_list_upload_business_date(f['upload_timestamp'])
             for f in cur.fetchall()}
    files = {fid: day for fid, day in files.items() if day <= today}
    identities = tuple(sorted({(int(r['upc_id']), str(r.get('ean_upc') or '')) for r in rows}))
    ids = {uid for uid, _ in identities}
    if not files or not ids:
        return {'REG': ids, 'TPR': ids}
    ordered_files = sorted(files, key=lambda fid: (files[fid], fid))
    coverage = None if data_days is None else tuple((d['date'], d['file_id'], d.get('coverage_kind')) for d in data_days)
    key = (identities, tuple((fid, files[fid]) for fid in ordered_files), today, through, coverage)
    with _lock:
        saved = _cache.get(key)
        if saved is not None:
            _cache.move_to_end(key)
            return saved
    aliases = {}
    for uid, ean in identities:
        aliases.setdefault(ean.lstrip('0'), set()).add(uid)
    eans = sorted({ean for _, ean in identities if ean})
    ph = lambda xs: ','.join(['%s'] * len(xs))
    # FIELD follows the exact (business date, file id) ordering of price_snapshots.
    cur.execute(f"""SELECT file_id,upc_id,ean_upc,configured_price,price_type
        FROM price_list_observation
        WHERE file_id IN ({ph(ordered_files)}) AND configured_price>0
        AND (upc_id IN ({ph(ids)}) OR ean_upc IN ({ph(eans) or 'NULL'}))
        ORDER BY FIELD(file_id,{ph(ordered_files)})""",
        (*ordered_files, *sorted(ids), *eans, *ordered_files))
    states, upload = {}, {}
    last_file = None

    def flush():
        for uid, ticket in upload.items():
            state = states.setdefault(uid, {})
            state['current'] = ticket
            if ticket['type'] == 'REG':
                previous = state.get('reg')
                if previous is None or abs(previous['price'] - ticket['price']) >= .011:
                    state['changed'] = ticket['date'] if previous is not None else None
                state['reg'] = ticket
        upload.clear()

    while True:
        batch = cur.fetchmany(512)
        if not batch:
            break
        for observation in batch:
            fid = int(observation['file_id'])
            if last_file is not None and fid != last_file:
                flush()
            last_file = fid
            uid = observation.get('upc_id')
            if uid not in ids:
                found = aliases.get(str(observation.get('ean_upc') or '').lstrip('0'), set())
                uid = next(iter(found)) if len(found) == 1 else None
            kind = str(observation.get('price_type') or '').upper()
            if uid not in ids or kind not in _priority:
                continue
            old = upload.get(uid)
            if old is None or _priority[kind] > _priority[old['type']]:
                upload[uid] = {'date': files[fid], 'price': float(observation['configured_price']), 'type': kind}
    flush()
    uncertain = any(not s.get('current') or through is not None and s['current']['date'] < through
                    for s in (states.get(uid, {}) for uid in ids))
    pos_dates = positive_pos_dates(cur, identities, data_days) if uncertain and data_days is not None else None
    result = {'REG': set(), 'TPR': set()}
    for uid in ids:
        state = states.get(uid, {})
        current = state.get('current')
        last_pos = pos_dates.get(uid) if pos_dates is not None else through
        if current is None and pos_dates is not None and last_pos is None:
            # Neither a ticket nor a positive canonical POS day can supply current.
            continue
        if current is None or last_pos is not None and current['date'] < last_pos:
            # Full canonical POS evidence may establish a different current price.
            result['REG'].add(uid)
            result['TPR'].add(uid)
        elif current['type'] == 'TPR':
            result['TPR'].add(uid)
        elif current['type'] == 'REG' and state.get('changed') is not None:
            if today - timedelta(days=7) <= state['changed'] <= today:
                result['REG'].add(uid)
    with _lock:
        _cache[key] = result
        _cache.move_to_end(key)
        while len(_cache) > 4:
            _cache.popitem(last=False)
    return result
