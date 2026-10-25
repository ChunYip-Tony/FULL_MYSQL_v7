"""Read-only, paginated identification across the whole published item catalog.

No sales/price inference and no READY-only filtering. History is read by the
existing dated evidence tools after identity resolution.
"""
from db import db_conn


def research_item_catalog(args):
    query = str(args.get('query') or '').strip()
    cursor = str(args.get('cursor') or '0')
    if len(query) > 100 or not cursor.isdigit() or len(cursor) > 18:
        raise ValueError('INVALID_CATALOG_QUERY_OR_CURSOR')
    terms = query.split()
    if len(terms) > 10:
        raise ValueError('USE_AT_MOST_TEN_CATALOG_SEARCH_TERMS')
    filters, values = ['q.upc_id > %s'], [int(cursor)]
    for term in terms:
        # Bound text scans, parameterize every user value, and retain exact IDs.
        filters.append("""(q.ean_upc LIKE %s OR q.article_number LIKE %s
          OR q.main_article_number LIKE %s OR q.selling_description LIKE %s
          OR q.family_description LIKE %s OR EXISTS (
            SELECT 1 FROM article a JOIN bridge_article_family b ON b.article_id=a.article_id
            WHERE b.family_id=q.family_id AND b.mapping_status='CONFIRMED'
              AND (b.valid_to IS NULL OR b.valid_to>CURRENT_TIMESTAMP(6))
              AND (a.article_number LIKE %s OR a.article_description LIKE %s)))""")
        values.extend(['%' + term + '%'] * 7)
    sql = """SELECT q.upc_id,q.ean_upc,q.article_number,q.main_article_number,
        q.selling_description,q.family_description,q.selling_uom,q.quick_check_status
        FROM quick_check_current q WHERE """ + ' AND '.join(filters) + ' ORDER BY q.upc_id LIMIT 51'
    with db_conn(read_timeout=10, connection_timeout=5) as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, tuple(values))
        rows = cur.fetchall()
        cur.close()
    more = len(rows) > 50
    rows = rows[:50]
    return {
        'query': query, 'results': rows, 'returned_count': len(rows),
        'has_more': more, 'next_cursor': str(rows[-1]['upc_id']) if more else None,
        'scope': 'PUBLISHED_CATALOG_ALL_READINESS_STATES',
        'history_verified': False,
        'note': 'Identification only. Continue next_cursor until null for all matches. '
                'QA-held and historical-only items remain visible. Use dated sales, price, '
                'cost and movement tools for analysis; catalog presence is not verified history.',
    }
