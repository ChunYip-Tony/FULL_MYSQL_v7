"""Read canonical 251/252 history when its derived family mirror is absent."""
from decimal import Decimal, InvalidOperation
import re


def summarize_history(rows, days, operational=None):
    dates={d['date'] for d in days}
    values={}; units=set(); seen=set()
    for row in rows:
        key=(row.get('file_id'),row.get('raw_id'))
        if key in seen:
            continue
        seen.add(key)
        if row.get('posting_date') not in dates or str(row.get('movement_type')) not in ('251','252'):
            continue
        qty=row.get('base_quantity'); unit=str(row.get('base_uom_code') or '').strip().upper()
        if operational and str(operational.get('movement_quantity_basis') or '').upper()=='ENTRY':
            expected=str(operational.get('operational_uom_code') or '').upper()
            if str(row.get('entry_uom_code') or '').upper()!=expected:
                return {'status':'BLOCKED','basis':'ENTRY_UOM_NOT_CONFIRMED'}
            qty=row.get('entry_quantity');unit=expected
        try:
            value=Decimal(str(qty))
        except (InvalidOperation,ValueError):
            return {'status':'BLOCKED','basis':'SOURCE_QUANTITY_MISSING'}
        if not value.is_finite() or not unit:
            return {'status':'BLOCKED','basis':'SOURCE_QUANTITY_OR_UOM_MISSING'}
        units.add(unit)
        values[row['posting_date']]=values.get(row['posting_date'],Decimal(0))-value
    if not values:
        return None
    if len(units)!=1:
        return {'status':'BLOCKED','basis':'MULTIPLE_FAMILY_MOVEMENT_UOMS'}
    quantity=sum(values.values(),Decimal(0))
    if quantity<0:
        return {'status':'BLOCKED','basis':'NET_RETURNS_EXCEED_SALES'}
    ordered=sorted(dates)
    return {'status':'READY','quantity':quantity,'uom':next(iter(units)),
            'supported_day_count':len(ordered),'velocity_per_supported_day':quantity/len(ordered),
            'rows':[{'date':dt,'sold_quantity':values.get(dt,Decimal(0))} for dt in ordered],
            'basis':'CANONICAL_MOVEMENT_HISTORY_251_MINUS_252_CONFIRMED_FAMILY',
            'source_row_count':len(seen)}


def read_family_history(cur, family_id, days):
    if not days:
        return None
    from phase3 import _structural_sap_selling_family
    from manual_overrides import confirmed_operational_uom_basis
    # Exact structural candidates still require the same unique ACTIVE,
    # CONFIRMED UPC -> Article -> Family authority as movement ingest.
    cur.execute("""SELECT DISTINCT su.ean_upc,bau.sales_set_number
        FROM selling_upc su
        JOIN bridge_article_upc bau ON bau.upc_id=su.upc_id
          AND bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
          AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
        JOIN bridge_article_family baf ON baf.article_id=bau.article_id
          AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
          AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
        WHERE baf.family_id=%s AND su.record_status='ACTIVE'""",(family_id,))
    candidates=[]
    for item in cur.fetchall():
        sales_set=str(item.get('sales_set_number') or '').strip()
        if re.fullmatch(r'\d{1,18}',sales_set):
            cur.execute("""SELECT COUNT(DISTINCT baf.family_id) AS family_count,
                MIN(baf.family_id) AS family_id
                FROM bridge_article_upc bau
                JOIN selling_upc su ON su.upc_id=bau.upc_id AND su.record_status='ACTIVE'
                JOIN bridge_article_family baf ON baf.article_id=bau.article_id
                  AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                  AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                WHERE bau.sales_set_number=%s AND bau.mapping_status='CONFIRMED'
                  AND bau.is_primary=TRUE
                  AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))""",(sales_set,))
            authority=cur.fetchone() or {}
            if int(authority.get('family_count') or 0)==1 and authority.get('family_id')==family_id:
                candidates.append(sales_set)
        match=re.fullmatch(r'(240|245|249)(\d{3})00000',str(item.get('ean_upc') or ''))
        if not match:
            continue
        article='154'+{'240':'0','245':'5','249':'9'}[match[1]]+match[2]
        if _structural_sap_selling_family(cur,article)==family_id:
            candidates.append(article)
    candidates=sorted(set(candidates))
    clauses=[];params=[family_id]
    scope='m.family_id=%s'
    if candidates:
        scope+=' OR (m.family_id IS NULL AND m.article_number IN ('+','.join(['%s']*len(candidates))+'))'
        params.extend(candidates)
    for day in days:
        clauses.append('(m.file_id=%s AND m.posting_date=%s)')
        params.extend([int(day['file_id']),day['date']])
    cur.execute("""SELECT m.file_id,m.raw_id,m.posting_date,m.movement_type,
        m.base_quantity,m.base_uom_code,m.entry_quantity,m.entry_uom_code
        FROM movement_history m WHERE ("""+scope+") AND m.movement_type IN ('251','252') AND ("+' OR '.join(clauses)+") ORDER BY m.raw_id",tuple(params))
    rows=cur.fetchall()
    result=summarize_history(rows,days,confirmed_operational_uom_basis(cur,family_id)) if rows else None
    if result is not None:
        result['confirmed_selling_articles']=candidates
    return result


def movement_evidence(cur, family_id, days):
    """Bounded read-only lineage check; name matches never become demand."""
    if not days:
        return {'status':'NO_CANONICAL_DAYS','rows':[]}
    cur.execute('SELECT main_article_number,family_description FROM product_family WHERE family_id=%s',(family_id,))
    family=cur.fetchone() or {}
    words=re.findall(r'[A-Za-z0-9]+',str(family.get('family_description') or ''))
    pattern='%'+'%'.join(words)+'%' if words else None
    dates=sorted(d['date'] for d in days)
    scope='family_id=%s OR article_number=%s';params=[family_id,str(family.get('main_article_number') or '')]
    if pattern and len(words)>=2:
        scope+=' OR description LIKE %s';params.append(pattern)
    params.extend([dates[0],dates[-1]])
    cur.execute("""SELECT file_id,article_number,family_id,movement_type,posting_date,
        base_uom_code,COUNT(*) AS row_count,SUM(base_quantity) AS signed_quantity
        FROM movement_history WHERE ("""+scope+") AND posting_date BETWEEN %s AND %s GROUP BY file_id,article_number,family_id,movement_type,posting_date,base_uom_code ORDER BY posting_date DESC,file_id DESC LIMIT 60",tuple(params))
    canonical={(int(d['file_id']),d['date']) for d in days}
    rows=[{**r,'canonical':(int(r['file_id']),r['posting_date']) in canonical,
           'confirmedFamily':r.get('family_id')==family_id} for r in cur.fetchall()]
    return {'status':'DIAGNOSTIC_ONLY','rows':rows,'basis':'NAME_MATCH_IS_NOT_FAMILY_AUTHORITY'}
