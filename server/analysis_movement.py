"""All canonical MVT postings, with cost valuation and immutable source lineage."""
from datetime import date
from decimal import Decimal
from collections import defaultdict

MOVEMENT_COLUMNS = 'file_id raw_id source_row_number posting_date article_number family_article_number description movement_type entry_quantity entry_uom_code base_quantity base_uom_code amount_local_currency article_document purchase_order vendor_code cost_center'.split()


def summarize_movements(export, start=None, end=None, family=None):
    dates = sorted(d for d in export['dates'] if (not start or d >= start) and (not end or d <= end))
    if not start and not end:
        dates = dates[-28:]
    selected = [r for r in export['rows'] if str(r['posting_date'])[:10] in set(dates)
                and r['department']=='Seafood' and (not family or str(r.get('family_article_number'))==str(family))]
    if not dates or not selected:
        return {'data_available':False,'reason':'NO_MATCHING_CANONICAL_MOVEMENT_EVIDENCE',
                'supported_dates':dates,'missing_dates_are_zero':False}
    totals = defaultdict(lambda: {'quantity':Decimal(0),'posted_cost':Decimal(0),'rows':0,'missing_values':0,'quantity_missing_rows':0,'posted_cost_missing_rows':0})
    for row in selected:
        value=totals[(str(row['movement_type']),row.get('base_uom_code') or 'UNVERIFIED_UNIT')]
        value['rows']+=1
        for source,target in [('base_quantity','quantity'),('amount_local_currency','posted_cost')]:
            try:
                number=Decimal(str(row.get(source)))
                valid=number.is_finite() and (target!='quantity' or bool(row.get('base_uom_code')))
            except Exception:
                valid=False
            if not valid:
                value['missing_values']+=1
                value[target+'_missing_rows']+=1
            else:value[target]+=number
    for value in totals.values():
        for key in ('quantity','posted_cost'):
            value['known_partial_'+key]=value[key]
            if value[key+'_missing_rows']:value[key]=None
    result=[{'movement_type':t,'unit':u,**values} for (t,u),values in sorted(totals.items())]
    return {'data_available':True,'family_article':family,'grain':'FAMILY_OR_DEPARTMENT; NEVER_ALLOCATED_TO_UPCS',
            'supported_dates':dates,'supported_day_count':len(dates),'row_count':len(selected),'by_movement_and_unit':result,
            'source_files':sorted({r['source_filename'] for r in selected}),
            'source':'CANONICAL_MVT_POSTED_COST_AND_QUANTITY',
            'interpretation':'Amount LC is posted cost, never sales revenue or selling price. Preserve signed reversals. Net 251/252 issue quantity is negative of signed postings. Dump cost is negative of net 551/552 valuation. Inventory count loss/gain is negative of net 701/702 valuation. Do not sum different units or count 107 and 109 as two receipts; use get_stock_flow for physical receipt totals. Observed postings alone do not prove complete loss coverage or final adjusted GP.'}


def build_movement_export(cur, quick_rows, batch_id, through):
    from data_coverage import source_data_days
    from business_clock import completed_through_date
    days = source_data_days(cur, 'movement', limit=3650, up_to=completed_through_date(), include_batch_id=batch_id)
    if not days:
        return {'rows': [], 'dates': [], 'counts': {}, 'contract': 'CANONICAL_MOVEMENT_LINES_V1'}
    clauses, params = [], []
    for day in days:
        clauses.append('(m.file_id=%s AND m.posting_date=%s)')
        params.extend([int(day['file_id']), day['date']])
    cur.execute('''SELECT m.file_id,m.raw_id,m.source_row_number,m.posting_date,m.article_number,
        pf.main_article_number AS family_article_number,m.description,m.movement_type,
        m.entry_quantity,m.entry_uom_code,m.base_quantity,m.base_uom_code,m.amount_local_currency,
        m.article_document,m.purchase_order,m.vendor_code,m.cost_center
        FROM movement_history m LEFT JOIN product_family pf ON pf.family_id=m.family_id
        WHERE ''' + ' OR '.join(clauses) + ' ORDER BY m.posting_date,m.file_id,m.raw_id', tuple(params))
    families = {str(r.get('main_article_number')) for r in quick_rows if r.get('main_article_number')}
    files = {(int(d['file_id']), str(d['date'])[:10]): d for d in days}
    result, seen, counts = [], set(), defaultdict(int)
    for row in cur.fetchall():
        key = (int(row['file_id']), int(row['raw_id']))
        if key in seen:
            raise ValueError('Duplicate canonical movement line: '+str(key))
        seen.add(key)
        tag = str(row.get('cost_center') or '').upper()
        if any(dep in tag for dep in ('MEAT', 'PRODUCE')):
            continue
        source = files[(key[0], str(row['posting_date'])[:10])]
        filename = str(source.get('original_filename') or '')
        seafood = ('SEAFOOD' in tag or str(row.get('family_article_number')) in families
                   or filename.lower().startswith(('sf-', 'sf_', 'seafood')))
        scope = 'Seafood' if seafood else 'UNASSIGNED_DEPARTMENT'
        record = {k: row.get(k) for k in MOVEMENT_COLUMNS}
        record.update(department=scope, source_filename=filename, source_line_id=f'{key[0]}:{key[1]}',
                      mapping_status='FAMILY_REFERENCE_ONLY_NO_UPC_ALLOCATION' if row.get('family_article_number') else 'ARTICLE_MAPPING_UNRESOLVED',
                      amount_basis='SIGNED_POSTED_COST_NOT_SALES_REVENUE', quantity_basis='RAW_POSTING_NOT_PHYSICAL_DELIVERY_COUNT',
                      source_revision=f'MYSQL_BATCH_{batch_id};CANONICAL_MOVEMENT_LINES_V1')
        result.append(record)
        counts[str(row['movement_type'])] += 1
    return {'rows': result, 'dates': sorted({str(d['date'])[:10] for d in days}),
            'counts': dict(counts), 'contract': 'CANONICAL_MOVEMENT_LINES_V1'}


def publish_source_records(reader, writer, additions, owned_kinds):
    """Preserve every existing column and unrelated typed record; compare all cells."""
    from price_history_analysis import _history_compare_value
    header_rows = reader('ANALYSIS_SOURCES', 1, 1, 128)
    if not header_rows:
        raise RuntimeError('Analysis source table is missing')
    header = list(header_rows[0])
    while header and header[-1] in ('', None):
        header.pop()
    if not header or len(set(header)) != len(header):
        raise RuntimeError('Analysis source schema is invalid')
    previous, kept = [header], []
    size = max(1, 20000//len(header))
    for start in range(2, 250000, size):
        page = reader('ANALYSIS_SOURCES', start, start+size-1, len(header))
        while page and not any(v not in ('', None) for v in page[-1]):
            page.pop()
        previous.extend(page)
        for row in page:
            if not any(v not in ('',None) for v in row):continue
            r = dict(zip(header, row))
            kind = r.get('record_kind') or ('INVENTORY_GP_ADJUSTMENT' if str(r.get('source_id') or '').startswith('INVENTORY_GP:') else 'SOURCE')
            if kind not in owned_kinds:
                kept.append({**r, 'record_kind': kind})
        if len(page) < size:
            break
    else:
        raise RuntimeError('Analysis source table exceeds safe read bound; refusing to truncate')
    all_rows = kept + additions
    columns = list(header)
    for r in all_rows:
        for key in r:
            if key not in columns:
                columns.append(key)
    matrix = [columns] + [[r.get(k, '') for k in columns] for r in all_rows]
    # Existing rows are retained in full, including columns introduced by other publishers.
    writer('ANALYSIS_SOURCES', matrix)
    size = max(1, 20000//len(columns))
    for start in range(1, len(matrix)+1, size):
        end = min(len(matrix), start+size-1)
        actual = reader('ANALYSIS_SOURCES', start, end, len(columns))
        if len(actual) != end-start+1:
            raise RuntimeError('Analysis source readback row count mismatch')
        for offset, (expected, observed) in enumerate(zip(matrix[start-1:end], actual)):
            observed = list(observed)+['']*max(0, len(columns)-len(observed))
            for index, (a,b) in enumerate(zip(expected, observed)):
                column = columns[index]
                if _history_compare_value(a, column) != _history_compare_value(b, column):
                    raise RuntimeError(f'Analysis source readback mismatch at row {start+offset}, {column}')
    return {'pass': True, 'rows': len(matrix)-1, 'columns': len(columns)}
