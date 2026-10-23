"""Posted inventory valuation affects GP once; family rows are not UPC allocations."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

MOVEMENTS = frozenset(('551', '552', '701', '702'))
HEADERS = ['department','posting_date','movement_type','article','family','upc_verified_only',
           'signed_gp_impact','valuation_basis','document_id','document_line','source_revision',
           'status','quantity','uom','source_file']
COVERAGE_HEADERS = ['department','period_start','period_end','required_movements',
                    'coverage_status','source_revision','unresolved_lines','note']


def serial(day):
    return (day - date(1899, 12, 30)).days


def amount(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def ledger(rows, days, start, end, department, revision, identities):
    """Select one canonical file per date before reading ANY adjustment types.

    A document can have several identical legitimate lines. Do not collapse by
    article/document/amount. raw_id uniquely identifies a line in the selected
    file; repeated query results are ignored, and overlapping uploads are excluded.
    """
    canonical = {d['date']: int(d['file_id']) for d in days if start <= d['date'] <= end}
    seen = set()
    output = [HEADERS]
    holds = 0
    for row in rows:
        dt = row['posting_date']
        if canonical.get(dt) != int(row['file_id']) or str(row['movement_type']) not in MOVEMENTS:
            continue
        key = (int(row['file_id']), int(row['raw_id']))
        if key in seen:
            continue
        seen.add(key)
        article = str(row['article_number'])
        identity = identities.get(article, {})
        # Explicit department tags prevent another department's loss leaking in.
        tag = str(row.get('cost_center') or '').upper()
        tagged = next((d for d in ('Seafood','Meat','Produce') if d.upper() in tag), None)
        if tagged and tagged != department:
            continue
        if not tagged and not identity:
            continue
        family = identity.get('family') or row.get('main_article_number') or ''
        upcs = identity.get('upcs', set())
        # Never allocate a main-family posting to one of its many UPCs.
        upc = next(iter(upcs)) if len(upcs) == 1 and article != str(family) else ''
        value = amount(row.get('amount_local_currency'))
        qty = amount(row.get('base_quantity'))
        expected = -1 if str(row['movement_type']) in ('551','702') else 1
        sign_ok = value is not None and (value == 0 or (1 if value > 0 else -1) == expected)
        qty_ok = qty is not None and (qty == 0 or (1 if qty > 0 else -1) == expected)
        status = 'VERIFIED' if family and sign_ok and qty_ok else 'UNRESOLVED_MAPPING_OR_VALUATION_SIGN'
        holds += status != 'VERIFIED'
        output.append([department,serial(dt),str(row['movement_type']),article,str(family),upc,
                       value,'SIGNED_POSTED_AMOUNT_LC',str(row.get('article_document') or ''),
                       str(row['raw_id']),revision,status,qty,row.get('base_uom_code') or '',
                       str(row['file_id'])])
    missing = (end - start).days + 1 - len(canonical)
    complete = missing == 0 and holds == 0
    coverage = [COVERAGE_HEADERS, [department, serial(start), serial(end), '551,552,701,702',
                'COMPLETE' if complete else 'PARTIAL', revision, holds,
                f'{len(canonical)} canonical dates; {missing} missing dates; '
                'UPC adjustments only for unique selling-article mapping; family-only values retained.']]
    return output, coverage


def build_adjustment_export(cur, quick_rows, batch_id, through, department='Seafood'):
    from data_coverage import source_data_days
    start = date(2026,8,27)
    end = date.fromisoformat(str(through)[:10])
    revision = f'MYSQL_BATCH_{batch_id};INVENTORY_GP_V1'
    days = source_data_days(cur,'movement',limit=3650,up_to=end,include_batch_id=batch_id)
    days = [d for d in days if start <= d['date'] <= end]
    identities = {}
    # Current confirmed bridge authority also covers historical selling articles.
    cur.execute("""SELECT a.article_number,pf.main_article_number,su.ean_upc,
                   bau.sales_set_number
        FROM article a
        JOIN bridge_article_family baf ON baf.article_id=a.article_id
          AND baf.is_primary=TRUE AND baf.mapping_status='CONFIRMED'
          AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
        JOIN product_family pf ON pf.family_id=baf.family_id
        LEFT JOIN bridge_article_upc bau ON bau.article_id=a.article_id
          AND bau.is_primary=TRUE AND bau.mapping_status='CONFIRMED'
          AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
        LEFT JOIN selling_upc su ON su.upc_id=bau.upc_id""")
    family_scope = {str(r.get('main_article_number')) for r in quick_rows if r.get('main_article_number')}
    candidates = defaultdict(lambda: {'families':set(),'upcs':set()})
    for row in cur.fetchall():
        family = str(row['main_article_number'])
        if family not in family_scope:
            continue
        for key in (row.get('article_number'),row.get('sales_set_number'),family):
            if key:
                candidate = candidates[str(key)]
                candidate['families'].add(family)
                if row.get('ean_upc'):
                    candidate['upcs'].add(str(row['ean_upc']))
    for key, candidate in candidates.items():
        if len(candidate['families']) == 1:
            identities[key] = {'family':next(iter(candidate['families'])),'upcs':candidate['upcs']}
    if not days:
        return ledger([],[],start,end,department,revision,identities)
    clauses=[]; params=[]
    for day in days:
        clauses.append('(m.file_id=%s AND m.posting_date=%s)')
        params.extend([int(day['file_id']),day['date']])
    cur.execute("""SELECT m.file_id,m.raw_id,m.article_number,m.posting_date,m.movement_type,
                m.amount_local_currency,m.base_quantity,m.base_uom_code,m.article_document,
                m.cost_center,pf.main_article_number
        FROM movement_history m LEFT JOIN product_family pf ON pf.family_id=m.family_id
        WHERE m.movement_type IN ('551','552','701','702') AND (""" +
        ' OR '.join(clauses) + ') ORDER BY m.posting_date,m.raw_id',tuple(params))
    return ledger(cur.fetchall(),days,start,end,department,revision,identities)


def verify_readback(reader, rows, coverage):
    """Read all exported lines, not only row counts, before publication PASS."""
    actual = reader(f"'GP_INVENTORY_ADJUSTMENTS'!A1:O{len(rows)}")
    expected = [[float(v) if isinstance(v,Decimal) else '' if v is None else v
                 for v in row] for row in rows]
    def norm(matrix):
        return [[str(v) if not isinstance(v,(float,int)) else str(Decimal(str(v)).normalize())
                 for v in (row+['']*15)[:15]] for row in matrix]
    # Numeric text from Apps Script and native Sheets must compare identically.
    def canonical(matrix):
        result=[]
        for row in norm(matrix):
            result.append([str(Decimal(v).normalize()) if v and amount(v) is not None else v for v in row])
        return result
    if canonical(actual) != canonical(expected):
        raise RuntimeError('Inventory GP adjustment ledger readback mismatch')
    read_coverage=reader("'GP_ADJUSTMENT_COVERAGE'!A1:H2")
    if canonical(read_coverage) != canonical(coverage):
        raise RuntimeError('Inventory GP movement coverage readback mismatch')
    return {'pass':True,'rows':len(rows)-1,'coverage':coverage[1][4],
            'revision':coverage[1][5],'contract':'INVENTORY_GP_V1'}


def publish_supported_adjustments(reader, writer, ledger_rows, coverage, movement_export=None):
    """One full-width source ledger publishes adjustments and all MVT types together."""
    from analysis_movement import publish_source_records
    import json
    additions = []
    for row in ledger_rows[1:]:
        record = {'department': row[0], 'source_id': 'INVENTORY_GP:'+row[14]+':'+row[9],
                  'filename': row[14], 'source_type': 'INVENTORY_GP_ADJUSTMENT',
                  'status': row[11], 'source_revision': row[10], 'record_kind': 'INVENTORY_GP_ADJUSTMENT'}
        record.update({'gp_'+key: value for key,value in zip(HEADERS,row)})
        additions.append(record)
    owned = {'INVENTORY_GP_ADJUSTMENT'}
    if movement_export is not None:
        owned.add('MOVEMENT_LINE')
        for row in movement_export['rows']:
            additions.append({'department': row['department'], 'source_id':'MOVEMENT:'+row['source_line_id'],
                'filename':row['source_filename'], 'source_type':'MOVEMENT_LINE',
                'start_date':str(row['posting_date'])[:10], 'end_date':str(row['posting_date'])[:10],
                'status':row['mapping_status'], 'source_revision':row['source_revision'],
                'record_kind':'MOVEMENT_LINE',
                'movement_json':json.dumps(row,default=lambda v:float(v) if isinstance(v,Decimal) else str(v),sort_keys=True,separators=(',',':'))})
    source_readback = publish_source_records(reader, writer, additions, owned)
    status=reader('ANALYSIS_STATUS',1,100,2)
    status=[r for r in status if r and str(r[0]).strip()
            and not str(r[0]).startswith('Inventory GP ')]
    status.extend([['Inventory GP contract','INVENTORY_GP_V1'],
                   ['Inventory GP coverage',coverage[1][4]],
                   ['Inventory GP start',coverage[1][1]],['Inventory GP end',coverage[1][2]],
                   ['Inventory GP revision',coverage[1][5]],['Inventory GP unresolved',coverage[1][6]],
                   ['Inventory GP lines',len(ledger_rows)-1],['Inventory GP note',coverage[1][7]]])
    if movement_export is not None:
        status = [r for r in status if not str(r[0]).startswith('Movement ledger ')]
        status.extend([['Movement ledger contract',movement_export['contract']],['Movement ledger rows',len(movement_export['rows'])],['Movement ledger readback','VERIFIED'],['Movement ledger dates',json.dumps(movement_export['dates'])],['Movement ledger types',json.dumps(movement_export['counts'],sort_keys=True)],['Movement ledger amount basis','POSTED_COST_NOT_REVENUE']])
    writer('ANALYSIS_STATUS',status)
    reread=reader('ANALYSIS_STATUS',1,len(status),2)
    observed_status={r[0]:r[1] for r in reread if len(r)>1}
    if observed_status.get('Inventory GP revision')!=coverage[1][5]:
        raise RuntimeError('Inventory adjustment coverage readback mismatch')
    return {'pass':True,'rows':len(ledger_rows)-1,'coverage':coverage[1][4],
            'revision':coverage[1][5],'contract':'INVENTORY_GP_V1',
            'table':'ANALYSIS_SOURCES','record_kind':'INVENTORY_GP_ADJUSTMENT',
            'movement_lines':len(movement_export['rows']) if movement_export is not None else None,
            'movement_contract':movement_export['contract'] if movement_export is not None else None,
            'source_readback':source_readback}

