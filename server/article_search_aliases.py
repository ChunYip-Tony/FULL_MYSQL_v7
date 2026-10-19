"""Search confirmed article identities without inferring UPC digits or changing mappings."""
def article_alias_families(cur, query):
    q=str(query or '').strip()
    if not q.isdigit() or len(q)>18:
        return {}
    cur.execute("""SELECT DISTINCT baf.family_id,a.article_number
        FROM article a JOIN bridge_article_family baf ON baf.article_id=a.article_id
        WHERE baf.mapping_status='CONFIRMED'
          AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
          AND (a.article_number=%s OR a.article_number LIKE %s)
        ORDER BY a.article_number,baf.family_id LIMIT 200""",(q,q+'%'))
    result={}
    for row in cur.fetchall():
        result.setdefault(int(row['family_id']),[]).append(str(row['article_number']))
    return result
