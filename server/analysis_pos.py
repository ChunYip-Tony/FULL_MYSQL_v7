"""Canonical typed POS evidence retained at Google without mixing MVT revenue."""
from business_clock import completed_through_date
from pos_evidence import eligible_sales_days, verified_pos_quantity
from family_daily_gp import apply_confirmed_selling_profile

def build_pos_export(cur, quick_rows, batch_id):
    from data_coverage import source_data_days
    days=eligible_sales_days(source_data_days(cur,'sales_by_price_type',limit=3650,
        up_to=completed_through_date(),include_batch_id=batch_id))
    by_id={int(r['upc_id']):apply_confirmed_selling_profile(r) for r in quick_rows if r.get('upc_id')}
    by_upc={str(r['ean_upc']):apply_confirmed_selling_profile(r) for r in quick_rows if r.get('ean_upc')}
    result=[];seen=set()
    direct_files=sorted({int(d['file_id']) for d in days if d.get('coverage_kind')!='DERIVED_PERIOD_RESIDUAL'})
    departments={}
    if direct_files:
        # One bounded lookup avoids a correlated subquery for every POS row.
        # Keep conflicting observations explicit instead of choosing LIMIT 1.
        cur.execute("SELECT file_id,sheet_id,source_row_number,department_code FROM upc_department_observation WHERE source_type='POS' AND file_id IN ("+','.join(['%s']*len(direct_files))+')',tuple(direct_files))
        for row in cur.fetchall():
            code=str(row.get('department_code') or '')
            if code:departments.setdefault((int(row['file_id']),row.get('sheet_id'),row.get('source_row_number')),set()).add(code)
    for derived in (False,True):
        scope=[d for d in days if (d.get('coverage_kind')=='DERIVED_PERIOD_RESIDUAL')==derived]
        if not scope:continue
        sources={(int(d['file_id']),str(d['date'])[:10]):d for d in scope}
        params=tuple(v for d in scope for v in ((int(d['file_id']),d['date']) if derived else (int(d['file_id']),d['date'],d['date'])))
        if derived:
            where=' OR '.join('(source_file_id=%s AND business_date=%s)' for _ in scope)
            cur.execute('SELECT * FROM pos_daily_backfill_observation WHERE '+where,params)
        else:
            where=' OR '.join('(s.file_id=%s AND s.period_start_date=%s AND s.period_end_date=%s)' for _ in scope)
            cur.execute("SELECT s.* FROM sales_period_observation s WHERE s.temporal_grain='SINGLE_DATE' AND ("+where+')',params)
        for raw in cur.fetchall():
            file_id=int(raw.get('source_file_id') if derived else raw['file_id'])
            day=str(raw.get('business_date') if derived else raw['period_end_date'])[:10]
            master=by_id.get(int(raw.get('upc_id') or 0)) or by_upc.get(str(raw.get('ean_upc') or ''))
            codes=departments.get((file_id,raw.get('sheet_id'),raw.get('source_row_number')),set()) if not derived else {str(raw.get('department_code') or '')}-{''}
            ambiguous=len(codes)>1
            dep=next(iter(codes)) if len(codes)==1 else ''
            if dep and dep!='400':continue
            if derived and not master:continue  # unresolved derived scope cannot certify Seafood
            source=sources[(file_id,day)]
            kind=str(raw.get('price_type') or 'UNKNOWN')
            identity=f"{file_id}:{day}:{raw.get('raw_id',raw.get('upc_id',raw.get('ean_upc')))}:{kind}"
            if identity in seen:raise ValueError('Duplicate canonical typed POS record: '+identity)
            seen.add(identity)
            qty,basis=verified_pos_quantity(master or {},{**raw,'price_types':{kind:{}}},day)
            sales=raw.get('sales_amount')
            result.append({'source_line_id':identity,'source_file_id':file_id,'raw_id':raw.get('raw_id'),
                'source_row_number':raw.get('source_row_number'),'source_filename':source.get('original_filename'),
                'date':day,'upc':str(master.get('ean_upc')) if master else str(raw.get('ean_upc') or ''),
                'raw_upc':str(raw.get('ean_upc') or ''),'name':raw.get('description'),
                'family':master.get('main_article_number') if master else None,
                'department':'Seafood' if not ambiguous and (dep=='400' or master) else 'UNASSIGNED_DEPARTMENT',
                'source_department_codes':sorted(codes),
                'mapping_status':'RESOLVED' if master else 'ITEM_IDENTITY_UNRESOLVED',
                'price_type':kind,'sales_amount':sales,'reported_quantity':raw.get('sold_quantity'),
                'verified_quantity':qty,'selling_uom':master.get('selling_uom') if master else None,
                'quantity_basis':basis,'realized_average_price':sales/qty if sales is not None and qty is not None and qty>0 else None,
                'price_basis':'POS_REALIZED_AVERAGE_NOT_ONE_APPLIED_PRICE','sales_basis':'POS_ONLY',
                'coverage_kind':source.get('coverage_kind'),'source_revision':f'MYSQL_BATCH_{batch_id};CANONICAL_TYPED_POS_V1'})
    result.sort(key=lambda r:(r['date'],r['source_file_id'],r['source_line_id']))
    return {'rows':result,'dates':sorted({str(d['date'])[:10] for d in days}),'contract':'CANONICAL_TYPED_POS_V1'}
