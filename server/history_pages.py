"""Bound identity scans while derived UPC links are repaired in one transaction."""

_COLUMNS = {
    'sales_period_observation': 'ean_upc,description',
    'price_list_observation': 'ean_upc',
    'inventory_observation': 'ean_upc',
    'company_price_observation': 'ean_upc',
    'upc_department_observation': 'ean_upc,department_code,source_type',
}


def iter_history_identities(cur, table, progress=None, page_size=250):
    columns = _COLUMNS[table]
    if not isinstance(page_size, int) or not 1 <= page_size <= 500:
        raise ValueError('Invalid history page size')
    offset = 0
    while True:
        # All ordering columns are immutable during relinking (only upc_id
        # changes). Stable DISTINCT ordering preserves NULL descriptions and
        # includes already-linked identities that may need canonical repair.
        if progress:
            progress(offset)
        cur.execute(
            f'SELECT DISTINCT {columns} FROM {table} '
            f'WHERE ean_upc IS NOT NULL ORDER BY {columns} LIMIT %s OFFSET %s',
            (page_size, offset),
        )
        rows = cur.fetchall()
        yield from rows
        offset += len(rows)
        if len(rows) < page_size:
            return
