"""Bounded RAW reads; consume each page before reusing the same DB cursor."""

_TABLES = frozenset({'raw_article_manual', 'raw_sales_by_price_type'})


def iter_raw_rows(cur, table, sheet_id, after_row=-1, page_size=500):
    if table not in _TABLES:
        raise ValueError('Unsupported RAW table')
    if not isinstance(page_size, int) or not 1 <= page_size <= 1000:
        raise ValueError('Invalid RAW page size')
    last_row, last_id = after_row, None
    while True:
        if last_id is None:
            predicate = 'source_row_number>%s'
            args = (sheet_id, last_row, page_size)
        else:
            predicate = '(source_row_number>%s OR (source_row_number=%s AND raw_id>%s))'
            args = (sheet_id, last_row, last_row, last_id, page_size)
        cur.execute(
            f'SELECT raw_id,source_row_number,raw_payload FROM {table} '
            f'WHERE sheet_id=%s AND {predicate} '
            'ORDER BY source_row_number,raw_id LIMIT %s', args,
        )
        rows = cur.fetchall()
        if not rows:
            return
        last_row, last_id = rows[-1]['source_row_number'], rows[-1]['raw_id']
        yield from rows
        if len(rows) < page_size:
            return
