"""Small, conservative progress index; detailed evidence still decides each card.

Stream one upload at a time instead of reading POS/cost/receipts for every UPC.
Missing tickets or POS newer than the ticket stay eligible for a full check.
"""
from collections import OrderedDict
from datetime import timedelta
import threading

_cache = OrderedDict()
_lock = threading.Lock()
_priority = {'REG': 1, 'TPR': 2, 'SALE': 3, 'IN STORE': 4, 'IN_STORE': 4}


def progress_candidates(cur, rows, today, through):
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
    key = (identities, tuple((fid, files[fid]) for fid in ordered_files), today, through)
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
    result = {'REG': set(), 'TPR': set()}
    for uid in ids:
        state = states.get(uid, {})
        current = state.get('current')
        if current is None or through is not None and current['date'] < through:
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
