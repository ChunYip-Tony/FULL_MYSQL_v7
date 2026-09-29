from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from data_coverage import source_data_days
from business_clock import completed_through_date
from coverage_backfill import canonical_pos_qty_by_upc
from manual_overrides import apply_manual_upc_overrides
from normalize import (
    RowContext,
    _build_column_map,
    _ensure_article,
    _ensure_article_family,
    _ensure_article_upc,
    _ensure_family,
    _ensure_upc,
    _get,
    _json_obj,
    _manual_article_family,
    _numeric_identifier,
    _numeric_key,
    _source_token,
    _text,
)

RECEIPT_MOVEMENTS = {'101', '107', '109'}
OFFICIAL_REPORT_RAW_TABLE = {
    'frozen_inventory': 'raw_frozen_inventory',
    'tx_seafood_abc_price': 'raw_tx_seafood_abc_price',
    'live_fresh_suggestion': 'raw_live_fresh_suggestion',
}
TRUSTED_UOM_RESOLUTION_METHODS = {
    'EXPLICIT_SOURCE_UOM',
    'USER_CONFIRMED_OVERRIDE',
    'EXPLICIT_SOURCE_EVIDENCE_REPAIR_V711',
    'REACTIVATED_UNIQUE_HISTORICAL_UOM_V711',
}


def _upca_check_digit(body11: str) -> str | None:
    if not re.fullmatch(r'\d{11}', str(body11 or '')):
        return None
    digits=[int(x) for x in body11]
    total=sum(digits[0::2])*3 + sum(digits[1::2])
    return str((10-(total % 10)) % 10)


def _upca_alias_candidates(raw: str | None) -> list[str]:
    s=str(raw or '').strip()
    out=[]
    if re.fullmatch(r'\d{11}',s):
        cd=_upca_check_digit(s)
        if cd is not None:
            out.append(s+cd)
    elif re.fullmatch(r'\d{10}',s):
        body='0'+s
        cd=_upca_check_digit(body)
        if cd is not None:
            out.append(body+cd)
    return out


def _numeric_equiv_pred(column: str, value: str) -> tuple[str, tuple[Any, ...]]:
    key = _numeric_key(value)
    if key is None:
        return f"{column}=%s", (value,)
    return (
        f"({column}=%s OR "
        f"({column} REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM {column})=%s))",
        (value, key),
    )


def _find_upc(cur, ean: str) -> dict[str, Any] | None:
    pred, params = _numeric_equiv_pred('ean_upc', ean)
    cur.execute(
        f"""SELECT upc_id,ean_upc,selling_description,record_status
            FROM selling_upc
            WHERE {pred}
            ORDER BY
              CASE WHEN ean_upc=%s THEN 0 ELSE 1 END,
              CHAR_LENGTH(ean_upc),upc_id
            LIMIT 1""",
        (*params, ean),
    )
    hit=cur.fetchone()
    if hit:
        return hit
    for candidate in _upca_alias_candidates(ean):
        cur.execute(
            """SELECT upc_id,ean_upc,selling_description,record_status
               FROM selling_upc
               WHERE ean_upc=%s
                 AND record_status='ACTIVE'
               LIMIT 1""",
            (candidate,),
        )
        hit=cur.fetchone()
        if hit:
            return hit
    return None


def _is_manual_retired_upc(cur, ean: str) -> bool:
    # The table is seeded by Phase 3 before automatic repair in v7.0.25.
    # Fail open only for legacy maintenance paths where the table does not exist yet;
    # the final publish guard still excludes confirmed retirements.
    try:
        cur.execute(
            """SELECT 1 FROM manual_upc_retirement
               WHERE ean_upc=%s AND retirement_status='CONFIRMED' LIMIT 1""",
            (ean,),
        )
        return bool(cur.fetchone())
    except Exception:
        return False


def _family_main(cur, family_id: int) -> dict[str, Any] | None:
    cur.execute(
        """SELECT pf.family_id,pf.main_article_number,a.article_id AS main_article_id
           FROM product_family pf
           JOIN article a ON a.article_number=pf.main_article_number
           WHERE pf.family_id=%s
           LIMIT 1""",
        (family_id,),
    )
    return cur.fetchone()


def _active_family_for_upc(cur, upc_id: int) -> int | None:
    cur.execute(
        """SELECT baf.family_id
           FROM bridge_article_upc bau
           JOIN bridge_article_family baf
             ON baf.article_id=bau.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE bau.upc_id=%s
             AND bau.mapping_status='CONFIRMED'
             AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           ORDER BY bau.article_upc_id DESC
           LIMIT 1""",
        (upc_id,),
    )
    row = cur.fetchone()
    return int(row['family_id']) if row else None


def _confirm_unique_family_link(
    cur,
    ean: str,
    family_id: int,
    source_role: str,
    evidence: dict[str, Any],
) -> tuple[bool, str]:
    """Confirm UPC -> canonical Main Article only when it cannot create a cross-family conflict."""
    fam = _family_main(cur, family_id)
    if not fam:
        return False, 'FAMILY_MAIN_ARTICLE_NOT_READY'

    if _is_manual_retired_upc(cur, ean):
        return False, 'USER_CONFIRMED_NONEXISTENT_UPC'

    upc = _find_upc(cur, ean)
    if upc:
        upc_id = int(upc['upc_id'])
        cur.execute("UPDATE selling_upc SET record_status='ACTIVE' WHERE upc_id=%s", (upc_id,))
    else:
        cur.execute(
            "INSERT INTO selling_upc (ean_upc,selling_description,record_status) VALUES (%s,NULL,'ACTIVE')",
            (ean,),
        )
        upc_id = int(cur.lastrowid)

    current_family = _active_family_for_upc(cur, upc_id)
    if current_family is not None and current_family != family_id:
        return False, 'EXISTING_CONFIRMED_CROSS_FAMILY_LINK'

    main_article_id = int(fam['main_article_id'])

    # Supersede legacy same-family direct-to-sub links, never cross-family links.
    cur.execute(
        """SELECT bau.article_upc_id,bau.article_id,baf.family_id
           FROM bridge_article_upc bau
           LEFT JOIN bridge_article_family baf
             ON baf.article_id=bau.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE bau.upc_id=%s
             AND bau.mapping_status='CONFIRMED'
             AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))""",
        (upc_id,),
    )
    for row in cur.fetchall():
        if int(row['article_id']) == main_article_id:
            continue
        if row['family_id'] is not None and int(row['family_id']) == family_id:
            cur.execute(
                """UPDATE bridge_article_upc
                   SET mapping_status='SUPERSEDED',is_primary=FALSE,
                       valid_to=COALESCE(valid_to,CURRENT_TIMESTAMP(6))
                   WHERE article_upc_id=%s""",
                (row['article_upc_id'],),
            )

    cur.execute(
        """SELECT article_upc_id
           FROM bridge_article_upc
           WHERE article_id=%s AND upc_id=%s AND relationship_type='SELLING'
           ORDER BY article_upc_id DESC LIMIT 1""",
        (main_article_id, upc_id),
    )
    link = cur.fetchone()
    if link:
        article_upc_id = int(link['article_upc_id'])
        cur.execute(
            """UPDATE bridge_article_upc
               SET mapping_status='CONFIRMED',is_primary=TRUE,confidence=1.0,valid_to=NULL
               WHERE article_upc_id=%s""",
            (article_upc_id,),
        )
    else:
        cur.execute(
            """INSERT INTO bridge_article_upc
               (article_id,upc_id,relationship_type,is_primary,mapping_status,confidence)
               VALUES (%s,%s,'SELLING',TRUE,'CONFIRMED',1.0)""",
            (main_article_id, upc_id),
        )
        article_upc_id = int(cur.lastrowid)

    cur.execute(
        """SELECT evidence_id
           FROM normalized_source_evidence
           WHERE object_type='ARTICLE_UPC'
             AND object_id=%s
             AND evidence_role=%s
           LIMIT 1""",
        (article_upc_id, source_role),
    )
    if not cur.fetchone():
        cur.execute(
            """INSERT INTO normalized_source_evidence
               (object_type,object_id,evidence_role,source_field_name,source_value_text,evidence_json)
               VALUES ('ARTICLE_UPC',%s,%s,'ean_upc',%s,%s)""",
            (
                article_upc_id,
                source_role,
                ean,
                json.dumps(
                    {
                        **evidence,
                        'canonical_main_article': fam['main_article_number'],
                        'family_id': family_id,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            ),
        )

    return True, 'CONFIRMED'


def _open_active_unmapped(cur, batch_id: int) -> list[dict[str, Any]]:
    cur.execute(
        """SELECT issue_id,entity_key,detail_json
           FROM qa_phase3_issue
           WHERE batch_id=%s
             AND issue_status='OPEN'
             AND issue_code='SOLD_UPC_UNMAPPED'
           ORDER BY issue_id""",
        (batch_id,),
    )
    rows = []
    for row in cur.fetchall():
        try:
            detail = json.loads(row.get('detail_json') or '{}')
        except Exception:
            detail = {}
        if detail.get('activity_scope') in (None, 'ACTIVE_SELLING'):
            rows.append({
                'issue_id': int(row['issue_id']),
                'ean_upc': str(row['entity_key']),
                'detail': detail,
            })
    return rows


def _canonical_recent_pos_qty_for_ean(
    cur,
    ean: str,
    pos_days: list[dict[str, Any]],
) -> Decimal:
    """Canonical current POS quantity for a raw UPC across selected valid data days.

    Mirrors the Phase 3 current-active guard semantics for both direct single-date
    POS and derived residual daily coverage. Exact/numeric-equivalent UPC matches
    are allowed; no product identity inference is performed here.
    """
    total = Decimal('0')
    direct_days = [
        d for d in pos_days
        if d.get('coverage_kind') != 'DERIVED_PERIOD_RESIDUAL'
    ]
    if direct_days:
        clauses: list[str] = []
        args: list[Any] = []
        for d in direct_days:
            clauses.append(
                '(file_id=%s AND period_start_date=%s AND period_end_date=%s)'
            )
            args.extend([int(d['file_id']), d['date'], d['date']])
        pred, pred_args = _numeric_equiv_pred('ean_upc', ean)
        cur.execute(
            f"""SELECT COALESCE(SUM(sold_quantity),0) AS q
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                  AND {pred}""",
            tuple(args) + tuple(pred_args),
        )
        total += Decimal(str((cur.fetchone() or {}).get('q') or 0))

    derived_days = [
        d for d in pos_days
        if d.get('coverage_kind') == 'DERIVED_PERIOD_RESIDUAL'
    ]
    if derived_days:
        clauses = []
        args = []
        for d in derived_days:
            clauses.append('(source_file_id=%s AND business_date=%s)')
            args.extend([int(d['file_id']), d['date']])
        pred, pred_args = _numeric_equiv_pred('ean_upc', ean)
        cur.execute(
            f"""SELECT COALESCE(SUM(sold_quantity),0) AS q
                FROM pos_daily_backfill_observation
                WHERE ({' OR '.join(clauses)})
                  AND {pred}""",
            tuple(args) + tuple(pred_args),
        )
        total += Decimal(str((cur.fetchone() or {}).get('q') or 0))

    return total


def _global_current_active_unmapped(
    cur,
    batch_id: int,
) -> list[dict[str, Any]]:
    """Return current-active Seafood UPCs missing confirmed product identity.

    This intentionally matches the global current-state readiness gate rather
    than looking only at SOLD_UPC_UNMAPPED issues created by files in the current
    ingest batch. It allows evidence-only repair to examine the same population
    that can block publication.
    """
    pos_days = source_data_days(
        cur,
        'sales_by_price_type',
        limit=28,
        include_batch_id=batch_id,
        up_to=completed_through_date(),
    )
    cur.execute(
        """SELECT DISTINCT ean_upc
           FROM upc_department_observation
           WHERE source_type='POS'
             AND department_code='400'
             AND ean_upc IS NOT NULL
             AND TRIM(ean_upc)<>''
           ORDER BY ean_upc"""
    )
    rows: list[dict[str, Any]] = []
    for r in cur.fetchall():
        ean = str(r['ean_upc'])
        existing = _find_upc(cur, ean)
        if existing and _active_family_for_upc(cur, int(existing['upc_id'])) is not None:
            continue
        qty = _canonical_recent_pos_qty_for_ean(cur, ean, pos_days)
        if qty <= 0:
            continue
        rows.append({
            'issue_id': None,
            'ean_upc': ean,
            'detail': {
                'activity_scope': 'ACTIVE_SELLING',
                'activity_basis': 'POS_LATEST_28_VALID_DATA_DAYS_GLOBAL_CURRENT',
                'recent_pos_qty_28_valid_days': str(qty),
                'recent_pos_valid_day_count': len(pos_days),
            },
        })
    return rows


def _article_manual_candidates(cur, target_keys: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Find exact/numeric-equivalent UPC evidence across all uploaded Article Manual worksheets."""
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not target_keys:
        return out

    cur.execute(
        """SELECT f.batch_id,f.file_id,f.source_type,s.sheet_id,s.sheet_name,
                  s.header_row_number,s.sheet_index
           FROM ingest_file f
           JOIN ingest_sheet s ON s.file_id=f.file_id
           WHERE f.source_type='article_manual'
             AND s.header_row_number IS NOT NULL
           ORDER BY f.file_id,s.sheet_index"""
    )
    sheets = cur.fetchall()

    for sh in sheets:
        cur.execute(
            """SELECT raw_payload
               FROM raw_article_manual
               WHERE sheet_id=%s AND source_row_number=%s
               LIMIT 1""",
            (sh['sheet_id'], sh['header_row_number']),
        )
        h = cur.fetchone()
        if not h:
            continue
        colmap = _build_column_map(_json_obj(h['raw_payload']))
        if 'upc' not in colmap or ('article' not in colmap and 'main_article' not in colmap):
            continue

        cur.execute(
            """SELECT raw_id,source_row_number,raw_payload
               FROM raw_article_manual
               WHERE sheet_id=%s AND source_row_number>%s
               ORDER BY source_row_number""",
            (sh['sheet_id'], sh['header_row_number']),
        )
        for rr in cur.fetchall():
            payload = _json_obj(rr['raw_payload'])
            ean = _numeric_identifier(_get(payload, colmap, 'upc'))
            key = _numeric_key(ean)
            if not ean or key not in target_keys:
                continue

            article = _numeric_identifier(_get(payload, colmap, 'article'))
            source_main = _numeric_identifier(_get(payload, colmap, 'main_article'))
            anchor = article or source_main
            if not anchor:
                continue

            manual_family = _manual_article_family(cur, anchor)
            canonical_main = (
                str(manual_family['main_article_number'])
                if manual_family
                else (source_main or anchor)
            )
            ctx = RowContext(
                batch_id=int(sh['batch_id']),
                file_id=int(sh['file_id']),
                sheet_id=int(sh['sheet_id']),
                raw_table='raw_article_manual',
                raw_id=int(rr['raw_id']),
                source_row_number=int(rr['source_row_number']),
                source_type='article_manual',
                sheet_name=str(sh['sheet_name']),
            )
            out[key].append({
                'ean_upc': ean,
                'article_number': article or anchor,
                'source_main_article': source_main,
                'canonical_main': canonical_main,
                'description': _text(_get(payload, colmap, 'description')),
                'category': _text(_get(payload, colmap, 'category')),
                'sales_set': _numeric_identifier(_get(payload, colmap, 'sales_set')),
                'ctx': ctx,
            })
    return out


def _apply_article_manual_candidate(
    cur, requested_ean: str, candidates: list[dict[str, Any]]
) -> tuple[bool, dict[str, Any]]:
    families = sorted({str(c['canonical_main']) for c in candidates if c.get('canonical_main')})
    if len(families) != 1:
        return False, {
            'source': 'ARTICLE_MANUAL',
            'reason': 'AMBIGUOUS_OR_NO_CANONICAL_FAMILY',
            'candidate_main_articles': families,
        }

    canonical_main = families[0]
    first = candidates[0]
    family_id = _ensure_family(cur, canonical_main, first.get('description'), first['ctx'])
    main_article_id = _ensure_article(
        cur, canonical_main, first.get('description'), first.get('category'), first['ctx']
    )
    _ensure_article_family(
        cur, main_article_id, family_id, canonical_main, canonical_main, first['ctx']
    )

    # Preserve legitimate sub-article/size/pack relationships represented in Article Manual.
    for c in candidates:
        article_number = str(c.get('article_number') or canonical_main)
        article_id = _ensure_article(
            cur, article_number, c.get('description'), c.get('category'), c['ctx']
        )
        _ensure_article_family(
            cur, article_id, family_id, article_number, canonical_main, c['ctx']
        )

    upc_id = _ensure_upc(cur, requested_ean, first.get('description'), first['ctx'])
    _, status = _ensure_article_upc(
        cur,
        main_article_id,
        upc_id,
        canonical_main,
        requested_ean,
        first.get('sales_set'),
        first['ctx'],
    )
    return status == 'CONFIRMED', {
        'source': 'ARTICLE_MANUAL',
        'canonical_main_article': canonical_main,
        'candidate_rows': len(candidates),
        'result': status,
    }


def _official_report_candidates(cur, ean: str) -> list[dict[str, Any]]:
    pred, params = _numeric_equiv_pred('ean_upc', ean)
    cur.execute(
        f"""SELECT company_price_observation_id,family_id,article_id,article_number,
                   source_type,file_id,sheet_id,raw_id,observation_date
            FROM company_price_observation
            WHERE ean_upc IS NOT NULL
              AND family_id IS NOT NULL
              AND {pred}
            ORDER BY observation_date DESC,company_price_observation_id DESC""",
        params,
    )
    return cur.fetchall()


def _repair_active_identity(cur, batch_id: int) -> dict[str, Any]:
    source_batch_issues = _open_active_unmapped(cur, batch_id)
    global_current = _global_current_active_unmapped(cur, batch_id)

    # De-duplicate leading-zero-equivalent spellings while preferring the
    # current global raw UPC spelling. The later global gate will independently
    # re-evaluate every raw POS spelling after repairs complete.
    by_key: dict[str, dict[str, Any]] = {}
    for item in source_batch_issues:
        key = _numeric_key(item['ean_upc']) or str(item['ean_upc'])
        by_key[key] = item
    for item in global_current:
        key = _numeric_key(item['ean_upc']) or str(item['ean_upc'])
        prior = by_key.get(key)
        if prior and prior.get('issue_id') is not None:
            merged = dict(item)
            merged['issue_id'] = prior.get('issue_id')
            merged['detail'] = {**(prior.get('detail') or {}), **(item.get('detail') or {})}
            by_key[key] = merged
        else:
            by_key[key] = item
    issues = list(by_key.values())

    target_keys = {_numeric_key(x['ean_upc']) for x in issues}
    for item in issues:
        for candidate in _upca_alias_candidates(item['ean_upc']):
            key=_numeric_key(candidate)
            if key:
                target_keys.add(key)
    target_keys.discard(None)
    manual = _article_manual_candidates(cur, target_keys)

    result = {
        'examined': len(issues),
        'source_batch_issue_count': len(source_batch_issues),
        'global_current_candidate_count': len(global_current),
        'repaired_article_manual': 0,
        'repaired_official_report': 0,
        'already_repaired': 0,
        'unresolved': [],
    }

    for item in issues:
        ean = item['ean_upc']
        existing = _find_upc(cur, ean)
        if existing and _active_family_for_upc(cur, int(existing['upc_id'])) is not None:
            result['already_repaired'] += 1
            continue

        key = _numeric_key(ean)
        candidate_keys=[key] if key else []
        candidate_keys.extend(
            _numeric_key(x) for x in _upca_alias_candidates(ean)
            if _numeric_key(x)
        )
        mcands=[]
        for ckey in dict.fromkeys(candidate_keys):
            mcands.extend(manual.get(ckey or '', []))
        if mcands:
            ok, detail = _apply_article_manual_candidate(cur, ean, mcands)
            if ok:
                result['repaired_article_manual'] += 1
                continue
            candidate_detail = detail
        else:
            candidate_detail = {'source': 'ARTICLE_MANUAL', 'reason': 'NO_EXACT_UPC_EVIDENCE'}

        ocands = _official_report_candidates(cur, ean)
        families = sorted({int(x['family_id']) for x in ocands if x.get('family_id') is not None})
        if len(families) == 1:
            ok, why = _confirm_unique_family_link(
                cur,
                ean,
                families[0],
                'ACTIVE_IDENTITY_REPAIR_OFFICIAL_REPORT_UNIQUE_FAMILY_V711',
                {
                    'source': 'OFFICIAL_COMPANY_REPORT',
                    'observation_ids': [int(x['company_price_observation_id']) for x in ocands[:50]],
                    'source_types': sorted({str(x['source_type']) for x in ocands}),
                },
            )
            if ok:
                result['repaired_official_report'] += 1
                continue
            official_detail = {'source': 'OFFICIAL_COMPANY_REPORT', 'reason': why, 'family_ids': families}
        elif len(families) > 1:
            official_detail = {
                'source': 'OFFICIAL_COMPANY_REPORT',
                'reason': 'AMBIGUOUS_FAMILY',
                'family_ids': families,
            }
        else:
            official_detail = {'source': 'OFFICIAL_COMPANY_REPORT', 'reason': 'NO_UNIQUE_FAMILY_EVIDENCE'}

        unresolved = {
            'upc': ean,
            'article_manual': candidate_detail,
            'official_report': official_detail,
        }
        result['unresolved'].append(unresolved)

        # Attach candidate diagnostics to the existing blocker; do not change severity/status.
        detail = item['detail']
        detail['v711_repair_candidates'] = unresolved
        if item.get('issue_id') is not None:
            cur.execute(
                "UPDATE qa_phase3_issue SET detail_json=%s WHERE issue_id=%s",
                (json.dumps(detail, ensure_ascii=False, default=str), item['issue_id']),
            )

    return result


def _uom_row_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row['selling_uom_id']),
        int(row['base_uom_id']) if row.get('base_uom_id') is not None else None,
        str(row['base_qty_per_selling_unit']) if row.get('base_qty_per_selling_unit') is not None else None,
    )


def _active_selling_upc_ids(cur, batch_id: int) -> tuple[list[int], int]:
    completed_through = date.today() - timedelta(days=1)
    pos_days = source_data_days(
        cur,
        'sales_by_price_type',
        limit=28,
        include_batch_id=batch_id,
        up_to=completed_through,
    )
    qty_by_upc = canonical_pos_qty_by_upc(cur, pos_days)
    active_ids = sorted(
        upc_id for upc_id, qty in qty_by_upc.items()
        if Decimal(str(qty or 0)) > 0
    )
    return active_ids, len(pos_days)


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


def _insert_uom_mapping(
    cur,
    upc_id: int,
    selling_uom_id: int,
    base_uom_id: int | None,
    factor: Any,
    method: str,
) -> None:
    cur.execute(
        """UPDATE selling_upc_uom_history
           SET mapping_status='SUPERSEDED',
               effective_to=COALESCE(effective_to,CURRENT_TIMESTAMP(6))
           WHERE upc_id=%s
             AND mapping_status='CONFIRMED'
             AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))
             AND NOT (
               selling_uom_id=%s
               AND COALESCE(base_uom_id,0)=COALESCE(%s,0)
               AND COALESCE(base_qty_per_selling_unit,-1)=COALESCE(%s,-1)
             )""",
        (upc_id, selling_uom_id, base_uom_id, factor),
    )

    cur.execute(
        """SELECT upc_uom_id
           FROM selling_upc_uom_history
           WHERE upc_id=%s
             AND selling_uom_id=%s
             AND COALESCE(base_uom_id,0)=COALESCE(%s,0)
             AND COALESCE(base_qty_per_selling_unit,-1)=COALESCE(%s,-1)
           ORDER BY upc_uom_id DESC
           LIMIT 1""",
        (upc_id, selling_uom_id, base_uom_id, factor),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """UPDATE selling_upc_uom_history
               SET mapping_status='CONFIRMED',confidence=1.0,resolution_method=%s,effective_to=NULL
               WHERE upc_uom_id=%s""",
            (method, row['upc_uom_id']),
        )
    else:
        cur.execute(
            """INSERT INTO selling_upc_uom_history
               (upc_id,selling_uom_id,base_uom_id,base_qty_per_selling_unit,
                mapping_status,confidence,resolution_method)
               VALUES (%s,%s,%s,%s,'CONFIRMED',1.0,%s)""",
            (upc_id, selling_uom_id, base_uom_id, factor, method),
        )


def _repair_active_uom(cur, batch_id: int) -> dict[str, Any]:
    active_ids, pos_day_count = _active_selling_upc_ids(cur, batch_id)
    result = {
        'active_upcs_examined': len(active_ids),
        'pos_valid_day_count': pos_day_count,
        'already_current': 0,
        'reactivated_unique_history': 0,
        'repaired_explicit_evidence': 0,
        'unresolved_no_exact_evidence': 0,
        'unresolved_conflict': 0,
    }

    for upc_id in active_ids:
        if _has_current_uom(cur, upc_id):
            result['already_current'] += 1
            continue

        # First: unique trusted historical UPC-specific UOM configuration.
        cur.execute(
            """SELECT upc_uom_id,selling_uom_id,base_uom_id,base_qty_per_selling_unit,
                      mapping_status,resolution_method
               FROM selling_upc_uom_history
               WHERE upc_id=%s
                 AND selling_uom_id IS NOT NULL
                 AND (
                   resolution_method IN (
                     'EXPLICIT_SOURCE_UOM',
                     'USER_CONFIRMED_OVERRIDE',
                     'EXPLICIT_SOURCE_EVIDENCE_REPAIR_V711',
                     'REACTIVATED_UNIQUE_HISTORICAL_UOM_V711'
                   )
                   OR resolution_method IS NULL
                 )
               ORDER BY upc_uom_id DESC""",
            (upc_id,),
        )
        history = cur.fetchall()
        unique_history = {_uom_row_tuple(r) for r in history}
        if len(unique_history) == 1 and history:
            sell_id, base_id, factor = next(iter(unique_history))
            _insert_uom_mapping(
                cur, upc_id, sell_id, base_id, factor,
                'REACTIVATED_UNIQUE_HISTORICAL_UOM_V711',
            )
            result['reactivated_unique_history'] += 1
            continue
        if len(unique_history) > 1:
            # Exact historical conflict: never choose silently.
            result['unresolved_conflict'] += 1
            continue

        # Second: exact UPC-specific normalized source evidence.
        cur.execute(
            """SELECT DISTINCT source_value_text
               FROM normalized_source_evidence
               WHERE object_type='SELLING_UPC'
                 AND object_id=%s
                 AND evidence_role='SELLING_UOM_OBSERVED'
                 AND source_value_text IS NOT NULL""",
            (upc_id,),
        )
        tokens = [_source_token(x['source_value_text']) for x in cur.fetchall()]
        tokens = [x for x in tokens if x]
        uoms: dict[int, dict[str, Any]] = {}
        for token in tokens:
            cur.execute(
                """SELECT uom_id,uom_code,uom_dimension
                   FROM dim_uom
                   WHERE UPPER(uom_code)=UPPER(%s)
                   LIMIT 1""",
                (token,),
            )
            row = cur.fetchone()
            if row:
                uoms[int(row['uom_id'])] = row

        if len(uoms) == 1:
            row = next(iter(uoms.values()))
            sell_id = int(row['uom_id'])
            if str(row.get('uom_dimension') or '').upper() in {'WEIGHT', 'COUNT'}:
                base_id = sell_id
                factor = Decimal('1')
            else:
                base_id = None
                factor = None
            _insert_uom_mapping(
                cur, upc_id, sell_id, base_id, factor,
                'EXPLICIT_SOURCE_EVIDENCE_REPAIR_V711',
            )
            result['repaired_explicit_evidence'] += 1
        elif len(uoms) > 1:
            result['unresolved_conflict'] += 1
        else:
            result['unresolved_no_exact_evidence'] += 1

    return result


def _relink_family_and_derive_cost(cur) -> dict[str, int]:
    """Repair derived family/cost mirrors from already-ingested authoritative history."""
    result = {
        'movement_family_relinked': 0,
        'receiving_family_relinked': 0,
        'cost_family_relinked': 0,
        'company_family_relinked': 0,
        'receiving_rows_backfilled': 0,
        'receipt_cost_rows_backfilled': 0,
        'official_cost_rows_backfilled': 0,
    }

    cur.execute(
        """UPDATE movement_history m
           JOIN bridge_article_family baf
             ON baf.article_id=m.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           SET m.family_id=baf.family_id
           WHERE m.article_id IS NOT NULL
             AND (m.family_id IS NULL OR m.family_id<>baf.family_id)"""
    )
    result['movement_family_relinked'] = int(cur.rowcount)

    cur.execute(
        """UPDATE receiving_observation r
           JOIN bridge_article_family baf
             ON baf.article_id=r.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           SET r.family_id=baf.family_id
           WHERE r.article_id IS NOT NULL
             AND (r.family_id IS NULL OR r.family_id<>baf.family_id)"""
    )
    result['receiving_family_relinked'] = int(cur.rowcount)

    cur.execute(
        """UPDATE article_cost_observation c
           JOIN bridge_article_family baf
             ON baf.article_id=c.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           SET c.family_id=baf.family_id
           WHERE c.article_id IS NOT NULL
             AND (c.family_id IS NULL OR c.family_id<>baf.family_id)"""
    )
    result['cost_family_relinked'] = int(cur.rowcount)

    cur.execute(
        """UPDATE company_price_observation c
           JOIN bridge_article_family baf
             ON baf.article_id=c.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           SET c.family_id=baf.family_id
           WHERE c.article_id IS NOT NULL
             AND (c.family_id IS NULL OR c.family_id<>baf.family_id)"""
    )
    result['company_family_relinked'] = int(cur.rowcount)

    # Backfill missing receipt mirror rows from movement_history after late identity repair.
    cur.execute(
        """INSERT INTO receiving_observation
           (article_id,family_id,movement_type,posting_date,article_document,purchase_order,vendor_code,
            entry_quantity,entry_uom_id,base_quantity,base_uom_id,amount_local_currency,currency_code,
            batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
           SELECT m.article_id,m.family_id,m.movement_type,m.posting_date,m.article_document,
                  m.purchase_order,m.vendor_code,m.entry_quantity,eu.uom_id,m.base_quantity,bu.uom_id,
                  m.amount_local_currency,'USD',m.batch_id,m.file_id,m.sheet_id,'raw_movement',
                  m.raw_id,m.source_row_number
           FROM movement_history m
           LEFT JOIN dim_uom eu ON UPPER(eu.uom_code)=UPPER(m.entry_uom_code)
           LEFT JOIN dim_uom bu ON UPPER(bu.uom_code)=UPPER(m.base_uom_code)
           WHERE m.article_id IS NOT NULL
             AND m.family_id IS NOT NULL
             AND m.movement_type IN ('101','107','109')
             AND NOT EXISTS (
               SELECT 1 FROM receiving_observation r
               WHERE r.raw_table_name='raw_movement' AND r.raw_id=m.raw_id
             )"""
    )
    result['receiving_rows_backfilled'] = int(cur.rowcount)

    # Receipt valuation authority: amount/base quantity with a canonical base UOM.
    cur.execute(
        """INSERT INTO article_cost_observation
           (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,movement_type,
            business_date,observed_at,cost_status,confidence,base_uom_id,cost_per_base_uom,
            batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
           SELECT m.article_id,m.family_id,
                  ABS(m.amount_local_currency / m.base_quantity),'USD',bu.uom_id,
                  'MOVEMENT_RECEIPT_VALUATION',m.movement_type,m.posting_date,
                  TIMESTAMP(m.posting_date),'OBSERVED',1.0,bu.uom_id,
                  ABS(m.amount_local_currency / m.base_quantity),
                  m.batch_id,m.file_id,m.sheet_id,'raw_movement',m.raw_id,m.source_row_number
           FROM movement_history m
           JOIN dim_uom bu ON UPPER(bu.uom_code)=UPPER(m.base_uom_code)
           WHERE m.article_id IS NOT NULL
             AND m.family_id IS NOT NULL
             AND m.movement_type IN ('101','107','109')
             AND m.amount_local_currency IS NOT NULL
             AND m.amount_local_currency<>0
             AND m.base_quantity IS NOT NULL
             AND m.base_quantity<>0
             AND NOT EXISTS (
               SELECT 1 FROM article_cost_observation c
               WHERE c.raw_table_name='raw_movement' AND c.raw_id=m.raw_id
             )"""
    )
    result['receipt_cost_rows_backfilled'] = int(cur.rowcount)

    # Backfill official report cost rows that were parsed before their article/family became linkable.
    cur.execute(
        """INSERT INTO article_cost_observation
           (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,business_date,
            cost_status,confidence,batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
           SELECT c.article_id,c.family_id,c.official_cost,'USD',du.uom_id,
                  CONCAT(UPPER(c.source_type),'_OFFICIAL_COST'),c.observation_date,
                  'OBSERVED',1.0,c.batch_id,c.file_id,c.sheet_id,
                  CASE c.source_type
                    WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                    WHEN 'tx_seafood_abc_price' THEN 'raw_tx_seafood_abc_price'
                    WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                    ELSE NULL
                  END,
                  c.raw_id,c.source_row_number
           FROM company_price_observation c
           JOIN dim_uom du ON UPPER(du.uom_code)=UPPER(c.cost_uom_code)
           WHERE c.article_id IS NOT NULL
             AND c.family_id IS NOT NULL
             AND c.official_cost IS NOT NULL
             AND c.official_cost>0
             AND c.cost_uom_code IS NOT NULL
             AND c.source_type IN ('frozen_inventory','tx_seafood_abc_price','live_fresh_suggestion')
             AND NOT EXISTS (
               SELECT 1 FROM article_cost_observation aco
               WHERE aco.raw_id=c.raw_id
                 AND aco.raw_table_name=
                   CASE c.source_type
                     WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                     WHEN 'tx_seafood_abc_price' THEN 'raw_tx_seafood_abc_price'
                     WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                   END
             )"""
    )
    result['official_cost_rows_backfilled'] = int(cur.rowcount)

    return result


def repair_active_product_master(cur, batch_id: int) -> dict[str, Any]:
    """Targeted, evidence-only repair for current-active Seafood product master gaps.

    This routine NEVER infers Selling UOM from description text, package text,
    UPC prefixes, or neighboring family members. Ambiguous evidence stays QA HOLD.
    """
    manual = apply_manual_upc_overrides(cur)
    identity = _repair_active_identity(cur, batch_id)
    uom = _repair_active_uom(cur, batch_id)
    cost = _relink_family_and_derive_cost(cur)
    return {
        'manual_overrides': manual,
        'identity': identity,
        'uom': uom,
        'cost_backfill': cost,
    }
