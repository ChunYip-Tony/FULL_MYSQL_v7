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
    targets=confirmed_search_targets(q)
    if targets:
        mains=[v['main_article_number'] for v in targets]
        cur.execute('SELECT family_id,main_article_number FROM product_family WHERE main_article_number IN ('+','.join(['%s']*len(mains))+')',tuple(mains))
        for row in cur.fetchall():
            for alias,target in CONFIRMED_SEARCH_ALIASES.items():
                if str(row['main_article_number'])==target['main_article_number'] and (q==alias or (len(q)>=4 and alias.startswith(q))):
                    values=result.setdefault(int(row['family_id']),[])
                    if alias not in values:values.append(alias)
    return result

# Search-only correction confirmed by Tony on 2026-10-19. This does not alter
# receiving identity, inventory, UPC sales, price, cost, or raw source records.
CONFIRMED_SEARCH_ALIASES = {
    # Historical UPC crosswalk: 2015994 -> 24271500000 -> 1340302.
    '2015994': {'main_article_number':'1340302','name':'CUTTLEFISH WHOLE CLEANED'},
    '2015950': {'main_article_number':'1341139','name':'SEA BASS STEAK'},
}

def confirmed_search_targets(query):
    q=str(query or '').strip()
    return [v for k,v in CONFIRMED_SEARCH_ALIASES.items() if q==k or (len(q)>=4 and k.startswith(q))]

def search_alias_priority(query, name):
    targets=confirmed_search_targets(query)
    text=' '.join(str(name or '').upper().split())
    return 0 if not targets or any(v['name'] in text for v in targets) else 1
