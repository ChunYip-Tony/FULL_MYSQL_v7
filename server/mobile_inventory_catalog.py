"""Read-only, paginated family identities for the mobile inventory browser.

Do not reuse Stock Flow's ranked 120-row comparison as an inventory roster.
Missing OH, movements, POS, or a Quick Check row must not hide a master family.
Inventory quantities still come from the existing authoritative PI endpoint.
"""
from __future__ import annotations

from db import db_conn


def _like(value: str) -> str:
    return "%" + value.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"


def read_catalog(cur, *, query: str = "", cursor: int = 0, limit: int = 30) -> dict:
    q = " ".join(str(query or "").strip().split())
    after, size = int(cursor), int(limit)
    if after < 0 or after > 9223372036854775807 or not 1 <= size <= 100 or len(q) > 80:
        raise ValueError("INVALID_CATALOG_PAGE")
    where, params = "", []
    if q:
        like = _like(q.lower())
        where = """ WHERE (
            LOWER(COALESCE(f.family_description,'')) LIKE %s ESCAPE '!'
            OR f.main_article_number LIKE %s ESCAPE '!'
            OR EXISTS (
                SELECT 1 FROM quick_check_current qc WHERE qc.family_id=f.family_id
                AND (LOWER(COALESCE(qc.selling_description,'')) LIKE %s ESCAPE '!'
                     OR qc.article_number LIKE %s ESCAPE '!'
                     OR qc.ean_upc LIKE %s ESCAPE '!')
            )
            OR EXISTS (
                SELECT 1 FROM bridge_article_family baf
                JOIN article a ON a.article_id=baf.article_id
                WHERE baf.family_id=f.family_id AND baf.mapping_status='CONFIRMED'
                  AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                  AND (a.article_number LIKE %s ESCAPE '!'
                       OR LOWER(COALESCE(a.article_description,'')) LIKE %s ESCAPE '!')
            )
        )"""
        params = [like] * 7
        from article_search_aliases import confirmed_search_targets
        targets=confirmed_search_targets(q)
        if targets:
            where=where.rstrip()[:-1]+' OR f.main_article_number IN ('+','.join(['%s']*len(targets))+'))'
            params.extend(v['main_article_number'] for v in targets)
    cur.execute("SELECT COUNT(*) AS total FROM product_family f" + where, tuple(params))
    total = int(cur.fetchone()["total"])
    cursor_where = (" AND " if where else " WHERE ") + "f.family_id>%s"
    cur.execute(
        "SELECT f.family_id,f.main_article_number,f.family_description FROM product_family f"
        + where + cursor_where + " ORDER BY f.family_id LIMIT %s",
        tuple(params + [after, size + 1]),
    )
    found = [dict(row) for row in cur.fetchall()]
    more = len(found) > size
    rows = found[:size]
    by_family = {int(row["family_id"]): row for row in rows}
    for row in rows:
        row["matches"] = []
    if rows:
        placeholders = ",".join(["%s"] * len(rows))
        cur.execute(
            "SELECT family_id,article_number,ean_upc,selling_description FROM quick_check_current "
            f"WHERE family_id IN ({placeholders}) ORDER BY family_id,ean_upc",
            tuple(by_family),
        )
        for child in cur.fetchall():
            by_family[int(child["family_id"])]["matches"].append({
                "article": str(child.get("article_number") or ""),
                "upc": str(child.get("ean_upc") or ""),
                "name": str(child.get("selling_description") or ""),
            })
    return {
        "contract_version": "MOBILE_INVENTORY_CATALOG_V1",
        "scope": "ALL_PRODUCT_FAMILIES",
        "query": q, "total": total, "rows": rows,
        "next_cursor": str(rows[-1]["family_id"]) if more else None,
    }


def inventory_catalog(query: str = "", cursor: int = 0, limit: int = 30) -> dict:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            return read_catalog(cur, query=query, cursor=cursor, limit=limit)
        finally:
            cur.close()

