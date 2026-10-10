from __future__ import annotations

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any

from normalize import (
    RowContext,
    ARTICLE_MANUAL_RECEIVING_PACK_TABS,
    _article_manual_column_map,
    _build_column_map,
    _canonical_uom,
    _ensure_article,
    _ensure_article_family,
    _ensure_article_upc,
    _ensure_family,
    _ensure_upc,
    _get,
    _insert_evidence,
    _json_obj,
    _manual_article_family,
    _numeric_identifier,
    _numeric_key,
    _norm_header,
    _source_token,
    _text,
)

VERSION = "7.0.12-multitab-article-manual-repair"

COMMON_WORDS = {
    'ALL','NATURE','NATURAL','FRESH','FROZEN','RAW','COOKED','PREMIUM',
    'SEAFOOD','PACK','PACKS','PACKED','EA','EACH','LB','LBS','OZ','KG','G',
    'W','WITH','IN','OF','THE','NO','STYLE'
}


def _digits_identifier(value: Any) -> str | None:
    """UPC-like identifier parser for Article Manual cells.

    Accept pure digits or digits separated only by spaces/hyphens.
    Never invent or pad digits.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    s = str(value).strip()
    if not s:
        return None
    if re.fullmatch(r'\d+\.0+', s):
        return s.split('.', 1)[0]
    if re.fullmatch(r'[\d\s-]+', s):
        d = re.sub(r'\D', '', s)
        return d or None
    return None


def _norm_desc(value: Any) -> str:
    s = (_text(value) or '').upper().replace('&', ' AND ')
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _core_tokens(value: Any) -> set[str]:
    toks = set()
    for tok in _norm_desc(value).split():
        if tok in COMMON_WORDS:
            continue
        if re.fullmatch(r'\d+(?:\.\d+)?', tok):
            continue
        toks.add(tok)
    return toks


def _desc_score(a: Any, b: Any) -> float:
    na = _norm_desc(a)
    nb = _norm_desc(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = _core_tokens(na), _core_tokens(nb)
    jac = (len(ta & tb) / len(ta | tb)) if ta and tb else 0.0
    containment = 1.0 if (na in nb or nb in na) else 0.0
    return max(containment, 0.55 * jac + 0.45 * seq)


def _short_barcode_relation(pos_upc: str, source_upc: str) -> str | None:
    """Conservative shortened-barcode relations observed in POS vs Article Manual.

    Accepted:
      - exact/numeric-equivalent
      - source = POS + one trailing digit
      - source = 0 + POS + one trailing digit

    This intentionally rejects one-digit substitutions and generic fuzzy barcode
    matching. Those remain review candidates.
    """
    p = re.sub(r'\D', '', str(pos_upc or ''))
    s = re.sub(r'\D', '', str(source_upc or ''))
    if not p or not s:
        return None
    if p.lstrip('0') == s.lstrip('0'):
        return 'NUMERIC_EQUIVALENT'
    if s == p + s[-1] and len(s) == len(p) + 1:
        return 'POS_PLUS_CHECK_DIGIT'
    if len(s) == len(p) + 2 and s.startswith('0' + p):
        return 'LEADING_ZERO_POS_PLUS_CHECK_DIGIT'
    return None


def _latest_article_manual_files(cur, preferred_batch_id: int | None = None) -> list[dict[str, Any]]:
    if preferred_batch_id is not None:
        cur.execute(
            """SELECT file_id,batch_id,original_filename
               FROM ingest_file
               WHERE batch_id=%s AND source_type='article_manual'
               ORDER BY file_id DESC""",
            (preferred_batch_id,),
        )
        rows = cur.fetchall()
        if rows:
            return rows

    cur.execute(
        """SELECT file_id,batch_id,original_filename
           FROM ingest_file
           WHERE source_type='article_manual'
           ORDER BY file_id DESC"""
    )
    rows = cur.fetchall()
    if not rows:
        return []
    # Use the newest Article Manual file only unless several files share its batch.
    newest_batch = int(rows[0]['batch_id'])
    return [r for r in rows if int(r['batch_id']) == newest_batch]


def _canonical_main_for_anchor(cur, anchor_article: str, explicit_main: str | None) -> str | None:
    if explicit_main:
        return explicit_main

    manual = _manual_article_family(cur, anchor_article)
    if manual:
        return str(manual['main_article_number'])

    cur.execute(
        """SELECT pf.main_article_number
           FROM article a
           JOIN bridge_article_family baf
             ON baf.article_id=a.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           JOIN product_family pf ON pf.family_id=baf.family_id
           WHERE a.article_number=%s
           ORDER BY baf.article_family_id DESC
           LIMIT 1""",
        (anchor_article,),
    )
    row = cur.fetchone()
    if row:
        return str(row['main_article_number'])

    cur.execute(
        "SELECT main_article_number FROM product_family WHERE main_article_number=%s LIMIT 1",
        (anchor_article,),
    )
    row = cur.fetchone()
    return str(row['main_article_number']) if row else None


def _load_roster(cur, preferred_batch_id: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    files = _latest_article_manual_files(cur, preferred_batch_id)
    rows: list[dict[str, Any]] = []
    stats = {
        'article_manual_files': [r['original_filename'] for r in files],
        'sheets_scanned': 0,
        'roster_rows': 0,
        'formatted_upc_rows': 0,
        'rows_with_explicit_um': 0,
    }

    for f in files:
        cur.execute(
            """SELECT sheet_id,sheet_name,header_row_number,sheet_index
               FROM ingest_sheet
               WHERE file_id=%s
               ORDER BY sheet_index""",
            (f['file_id'],),
        )
        for sh in cur.fetchall():
            if not sh['header_row_number']:
                continue
            cur.execute(
                """SELECT raw_id,raw_payload
                   FROM raw_article_manual
                   WHERE sheet_id=%s AND source_row_number=%s
                   LIMIT 1""",
                (sh['sheet_id'], sh['header_row_number']),
            )
            h = cur.fetchone()
            if not h:
                continue
            colmap = _article_manual_column_map(
                sh['sheet_name'],
                _json_obj(h['raw_payload']),
            )
            if 'upc' not in colmap or ('article' not in colmap and 'main_article' not in colmap):
                continue
            stats['sheets_scanned'] += 1

            from raw_pages import iter_raw_rows
            for rr in iter_raw_rows(cur, 'raw_article_manual', sh['sheet_id'], sh['header_row_number']):
                payload = _json_obj(rr['raw_payload'])
                raw_upc = _get(payload, colmap, 'upc')
                source_upc = _digits_identifier(raw_upc)
                if not source_upc:
                    continue

                article = _numeric_identifier(_get(payload, colmap, 'article'))
                explicit_main = _numeric_identifier(_get(payload, colmap, 'main_article'))
                anchor = article or explicit_main
                if not anchor:
                    continue
                canonical_main = _canonical_main_for_anchor(cur, anchor, explicit_main)
                if not canonical_main:
                    continue

                description = _text(_get(payload, colmap, 'description'))
                pack = _text(_get(payload, colmap, 'pack'))
                sales_set = _numeric_identifier(_get(payload, colmap, 'sales_set'))
                selling_uom = _source_token(_get(payload, colmap, 'selling_uom'))
                selling_uom_rule = 'EXPLICIT_SOURCE_UOM' if selling_uom else None
                if (
                    _norm_header(sh['sheet_name']) in ARTICLE_MANUAL_RECEIVING_PACK_TABS
                    and source_upc
                    and sales_set
                ):
                    selling_uom = 'LB'
                    selling_uom_rule = 'ARTICLE_MANUAL_TOLEDO_EAN_LB'
                ctx = RowContext(
                    batch_id=int(f['batch_id']),
                    file_id=int(f['file_id']),
                    sheet_id=int(sh['sheet_id']),
                    raw_table='raw_article_manual',
                    raw_id=int(rr['raw_id']),
                    source_row_number=int(rr['source_row_number']),
                    source_type='article_manual',
                    sheet_name=str(sh['sheet_name']),
                )
                rows.append({
                    'source_upc': source_upc,
                    'raw_upc': raw_upc,
                    'article_number': article or canonical_main,
                    'canonical_main': canonical_main,
                    'description': description,
                    'pack': pack,
                    'sales_set': sales_set,
                    'selling_uom': selling_uom,
                    'selling_uom_rule': selling_uom_rule,
                    'ctx': ctx,
                    'sheet_name': str(sh['sheet_name']),
                })
                stats['roster_rows'] += 1
                if str(raw_upc).strip() != source_upc:
                    stats['formatted_upc_rows'] += 1
                if selling_uom:
                    stats['rows_with_explicit_um'] += 1

    return rows, stats


def _ensure_pos_identity(cur, pos_upc: str, candidate: dict[str, Any], issue_description: str | None) -> tuple[int, int]:
    canonical_main = str(candidate['canonical_main'])
    ctx: RowContext = candidate['ctx']
    description = issue_description or candidate.get('description')
    family_id = _ensure_family(cur, canonical_main, description, ctx)
    main_article_id = _ensure_article(cur, canonical_main, description, None, ctx)
    _ensure_article_family(cur, main_article_id, family_id, canonical_main, canonical_main, ctx)

    source_article = str(candidate.get('article_number') or canonical_main)
    source_article_id = _ensure_article(cur, source_article, candidate.get('description'), None, ctx)
    _ensure_article_family(cur, source_article_id, family_id, source_article, canonical_main, ctx)

    upc_id = _ensure_upc(cur, pos_upc, issue_description or candidate.get('description'), ctx)
    _, status = _ensure_article_upc(
        cur,
        main_article_id,
        upc_id,
        canonical_main,
        pos_upc,
        None,
        ctx,
    )
    if status != 'CONFIRMED':
        raise RuntimeError(f'Unable to confirm POS UPC {pos_upc} to Main Article {canonical_main}; status={status}')

    _insert_evidence(
        cur,
        'SELLING_UPC',
        upc_id,
        'ARTICLE_MANUAL_SHORT_BARCODE_ALIAS_V712',
        ctx,
        'upc',
        pos_upc,
        {
            'article_manual_source_upc': candidate['source_upc'],
            'article_manual_raw_upc': candidate.get('raw_upc'),
            'source_article': source_article,
            'canonical_main_article': canonical_main,
            'source_sheet': candidate['sheet_name'],
        },
    )
    return upc_id, family_id


def _has_current_uom(cur, upc_id: int) -> bool:
    cur.execute(
        """SELECT 1
           FROM selling_upc_uom_history
           WHERE upc_id=%s
             AND mapping_status='CONFIRMED'
             AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))
           LIMIT 1""",
        (upc_id,),
    )
    return bool(cur.fetchone())


def _apply_explicit_um(cur, upc_id: int, candidate: dict[str, Any]) -> str:
    token = _source_token(candidate.get('selling_uom'))
    if not token:
        return 'NO_EXPLICIT_UM'

    uom_id, canonical = _canonical_uom(cur, 'article_manual', token)
    if uom_id is None:
        return 'UOM_TOKEN_UNRESOLVED'

    rule = str(candidate.get('selling_uom_rule') or 'EXPLICIT_SOURCE_UOM')
    cur.execute(
        """SELECT h.upc_uom_id,du.uom_code
           FROM selling_upc_uom_history h
           JOIN dim_uom du ON du.uom_id=h.selling_uom_id
           WHERE h.upc_id=%s
             AND h.mapping_status='CONFIRMED'
             AND (h.effective_to IS NULL OR h.effective_to>CURRENT_TIMESTAMP(6))
           ORDER BY h.upc_uom_id DESC""",
        (upc_id,),
    )
    current = cur.fetchall()
    if any(str(x.get('uom_code') or '').upper() == str(token).upper() for x in current):
        return 'ALREADY_HAS_UOM'

    # Toledo+D is explicit tab semantics confirmed by the user. It supersedes a
    # stale automatically inferred active UOM. Ordinary source UOM rows remain
    # non-destructive when another active UOM already exists.
    if current and rule != 'ARTICLE_MANUAL_TOLEDO_EAN_LB':
        return 'ALREADY_HAS_UOM'
    if current and rule == 'ARTICLE_MANUAL_TOLEDO_EAN_LB':
        cur.execute(
            """UPDATE selling_upc_uom_history
               SET mapping_status='SUPERSEDED',
                   effective_to=COALESCE(effective_to,CURRENT_TIMESTAMP(6))
               WHERE upc_id=%s
                 AND mapping_status='CONFIRMED'
                 AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))""",
            (upc_id,),
        )

    cur.execute("SELECT uom_dimension FROM dim_uom WHERE uom_id=%s", (uom_id,))
    d = cur.fetchone()
    dimension = str(d['uom_dimension']).upper() if d and d.get('uom_dimension') else None
    base_uom_id = uom_id if dimension in {'WEIGHT','COUNT'} else None
    factor = 1 if base_uom_id is not None else None

    cur.execute(
        """INSERT INTO selling_upc_uom_history
           (upc_id,selling_uom_id,base_uom_id,base_qty_per_selling_unit,
            mapping_status,confidence,resolution_method)
           VALUES (%s,%s,%s,%s,'CONFIRMED',1.0,%s)""",
        (upc_id, uom_id, base_uom_id, factor, rule),
    )
    _insert_evidence(
        cur,
        'SELLING_UPC',
        upc_id,
        'SELLING_UOM_OBSERVED',
        candidate['ctx'],
        'C_TOLEDO_PLUS_D_EAN' if rule == 'ARTICLE_MANUAL_TOLEDO_EAN_LB' else 'selling_uom',
        token,
        {
            'canonical_exact_match': canonical,
            'source_sheet': candidate['sheet_name'],
            'article_manual_source_upc': candidate['source_upc'],
            'resolution_rule': rule,
            'toledo_number': candidate.get('sales_set'),
        },
    )
    return 'UOM_REPAIRED'

def _candidate_match(pos_upc: str, pos_desc: str | None, row: dict[str, Any]) -> tuple[float, str] | None:
    relation = _short_barcode_relation(pos_upc, row['source_upc'])
    if not relation:
        return None
    score = _desc_score(pos_desc, row.get('description'))
    if score < 0.58:
        return None

    # If structured pack text is available and appears in POS text, reward it.
    pack = _norm_desc(row.get('pack'))
    pdesc = _norm_desc(pos_desc)
    pack_bonus = 0.15 if pack and pack in pdesc else 0.0
    relation_bonus = {
        'NUMERIC_EQUIVALENT': 0.30,
        'POS_PLUS_CHECK_DIGIT': 0.25,
        'LEADING_ZERO_POS_PLUS_CHECK_DIGIT': 0.25,
    }[relation]
    return score + pack_bonus + relation_bonus, relation


def _description_review_candidates(pos_desc: str | None, roster: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    scored = []
    for row in roster:
        score = _desc_score(pos_desc, row.get('description'))
        if score < 0.62:
            continue
        pack = _norm_desc(row.get('pack'))
        pdesc = _norm_desc(pos_desc)
        if pack and pack in pdesc:
            score += 0.12
        scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)

    result = []
    seen = set()
    for score, row in scored:
        key = (row['canonical_main'], row['article_number'], row['source_upc'])
        if key in seen:
            continue
        seen.add(key)
        result.append({
            'score': round(float(score), 4),
            'main_article': row['canonical_main'],
            'article': row['article_number'],
            'source_upc': row['source_upc'],
            'description': row.get('description'),
            'pack': row.get('pack'),
            'explicit_um': row.get('selling_uom'),
            'sheet': row.get('sheet_name'),
        })
        if len(result) >= limit:
            break
    return result


def _active_unmapped(cur, batch_id: int) -> list[dict[str, Any]]:
    cur.execute(
        """SELECT issue_id,entity_key,detail_json
           FROM qa_phase3_issue
           WHERE batch_id=%s
             AND issue_status='OPEN'
             AND issue_code='SOLD_UPC_UNMAPPED'
           ORDER BY issue_id""",
        (batch_id,),
    )
    result = []
    for row in cur.fetchall():
        try:
            detail = json.loads(row.get('detail_json') or '{}')
        except Exception:
            detail = {}
        result.append({
            'issue_id': int(row['issue_id']),
            'upc': str(row['entity_key']),
            'description': detail.get('description'),
            'detail': detail,
        })
    return result


def _relink_sales_exact(cur) -> int:
    cur.execute(
        """UPDATE sales_period_observation s
           JOIN selling_upc u ON u.ean_upc=s.ean_upc
           SET s.upc_id=u.upc_id
           WHERE s.upc_id IS NULL"""
    )
    return int(cur.rowcount)


def _current_active_upcs(cur, batch_id: int) -> list[dict[str, Any]]:
    # Phase 3's current rule is POS-positive in latest up-to-28 valid data days.
    from data_coverage import source_data_days
    from datetime import date, timedelta

    completed_through = date.today() - timedelta(days=1)
    days = source_data_days(
        cur, 'sales_by_price_type', limit=28,
        include_batch_id=batch_id, up_to=completed_through
    )
    file_ids = [int(d['file_id']) for d in days]
    if not file_ids:
        return []
    placeholders = ','.join(['%s'] * len(file_ids))
    cur.execute(
        f"""SELECT su.upc_id,su.ean_upc,su.selling_description,
                   pf.family_id,pf.main_article_number
            FROM sales_period_observation s
            JOIN selling_upc su ON su.upc_id=s.upc_id
            JOIN bridge_article_upc bau
              ON bau.upc_id=su.upc_id
             AND bau.mapping_status='CONFIRMED'
             AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
            JOIN bridge_article_family baf
              ON baf.article_id=bau.article_id
             AND baf.mapping_status='CONFIRMED'
             AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
            JOIN product_family pf ON pf.family_id=baf.family_id
            WHERE s.temporal_grain='SINGLE_DATE'
              AND s.file_id IN ({placeholders})
            GROUP BY su.upc_id,su.ean_upc,su.selling_description,pf.family_id,pf.main_article_number
            HAVING COALESCE(SUM(s.sold_quantity),0)>0""",
        tuple(file_ids),
    )
    return cur.fetchall()


def repair_article_manual_multitab(
    cur,
    batch_id: int,
    preferred_identity_batch_id: int | None = 7,
) -> dict[str, Any]:
    roster, roster_stats = _load_roster(cur, preferred_identity_batch_id)
    result: dict[str, Any] = {
        'version': VERSION,
        'roster': roster_stats,
        'identity': {
            'active_unmapped_examined': 0,
            'auto_repaired': 0,
            'ambiguous_same_rule': 0,
            'no_safe_barcode_alias': 0,
            'uom_repaired_during_identity': 0,
            'uom_missing_on_source_row': 0,
            'remaining_review': [],
        },
        'uom': {
            'active_mapped_examined': 0,
            'already_has_uom': 0,
            'auto_repaired_from_alias_row': 0,
            'no_safe_alias_um': 0,
        },
        'sales_rows_relinked_exact': 0,
    }

    # A) Resolve current active sold UPC blockers only on conservative barcode alias + description agreement.
    for issue in _active_unmapped(cur, batch_id):
        result['identity']['active_unmapped_examined'] += 1
        candidates = []
        for row in roster:
            matched = _candidate_match(issue['upc'], issue['description'], row)
            if matched:
                score, relation = matched
                candidates.append((score, relation, row))
        candidates.sort(key=lambda x: x[0], reverse=True)

        if candidates:
            families = sorted({str(x[2]['canonical_main']) for x in candidates})
        else:
            families = []

        if candidates and len(families) == 1:
            best_score, relation, best = candidates[0]
            upc_id, _family_id = _ensure_pos_identity(cur, issue['upc'], best, issue['description'])
            um_status = _apply_explicit_um(cur, upc_id, best)
            result['identity']['auto_repaired'] += 1
            if um_status == 'UOM_REPAIRED':
                result['identity']['uom_repaired_during_identity'] += 1
            elif um_status == 'NO_EXPLICIT_UM':
                result['identity']['uom_missing_on_source_row'] += 1

            detail = issue['detail']
            detail['v712_multitab_repair'] = {
                'status': 'AUTO_REPAIRED',
                'relation': relation,
                'score': round(float(best_score), 4),
                'source_upc': best['source_upc'],
                'main_article': best['canonical_main'],
                'article': best['article_number'],
                'source_sheet': best['sheet_name'],
                'explicit_um': best.get('selling_uom'),
            }
            cur.execute(
                "UPDATE qa_phase3_issue SET detail_json=%s WHERE issue_id=%s",
                (json.dumps(detail, ensure_ascii=False, default=str), issue['issue_id']),
            )
        else:
            if candidates and len(families) > 1:
                result['identity']['ambiguous_same_rule'] += 1
            else:
                result['identity']['no_safe_barcode_alias'] += 1

            review = _description_review_candidates(issue['description'], roster, limit=5)
            detail = issue['detail']
            detail['v712_cross_tab_candidates'] = review
            cur.execute(
                "UPDATE qa_phase3_issue SET detail_json=%s WHERE issue_id=%s",
                (json.dumps(detail, ensure_ascii=False, default=str), issue['issue_id']),
            )
            result['identity']['remaining_review'].append({
                'upc': issue['upc'],
                'description': issue['description'],
                'candidates': review,
            })

    # Make newly created POS identities visible to sales history before UOM sweep.
    result['sales_rows_relinked_exact'] = _relink_sales_exact(cur)

    # B) Repair current-active mapped UPC UOM when the same conservative alias points to
    #    a roster row in the same canonical family and that row has explicit UM.
    for p in _current_active_upcs(cur, batch_id):
        result['uom']['active_mapped_examined'] += 1
        upc_id = int(p['upc_id'])
        if _has_current_uom(cur, upc_id):
            result['uom']['already_has_uom'] += 1
            continue

        candidates = []
        for row in roster:
            if str(row['canonical_main']) != str(p['main_article_number']):
                continue
            if not row.get('selling_uom'):
                continue
            matched = _candidate_match(str(p['ean_upc']), p.get('selling_description'), row)
            if matched:
                score, relation = matched
                candidates.append((score, relation, row))

        candidates.sort(key=lambda x: x[0], reverse=True)
        if candidates:
            # All candidates are same family by construction. Require one explicit UM token.
            tokens = {str(x[2]['selling_uom']).strip().upper() for x in candidates if x[2].get('selling_uom')}
            if len(tokens) == 1:
                status = _apply_explicit_um(cur, upc_id, candidates[0][2])
                if status == 'UOM_REPAIRED':
                    result['uom']['auto_repaired_from_alias_row'] += 1
                    continue
        result['uom']['no_safe_alias_um'] += 1

    return result


def alias_relation_self_test() -> dict[str, Any]:
    tests = {
        '4029549040->40295490407': _short_barcode_relation('4029549040','40295490407'),
        '6139190220->061391902205': _short_barcode_relation('6139190220','061391902205'),
        '70286869729->702968697292': _short_barcode_relation('70286869729','702968697292'),
        '75539372208->753393722089': _short_barcode_relation('75539372208','753393722089'),
    }
    expected = {
        '4029549040->40295490407': 'POS_PLUS_CHECK_DIGIT',
        '6139190220->061391902205': 'LEADING_ZERO_POS_PLUS_CHECK_DIGIT',
        '70286869729->702968697292': None,
        '75539372208->753393722089': None,
    }
    return {'pass': tests == expected, 'observed': tests, 'expected': expected}

