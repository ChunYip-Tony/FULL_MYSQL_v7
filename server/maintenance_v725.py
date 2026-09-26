from __future__ import annotations

import argparse
import json
import traceback
from decimal import Decimal

from db import db_conn, test_database
from manual_overrides import apply_manual_upc_overrides, apply_manual_upc_retirements
from phase3 import rebuild_quick_check

VERSION = "7.0.25-family291-authority-lock"
VALID_UPC = "81223402610"
RETIRED_UPC = "26510500000"
ARTICLE = "3461050"


def _latest_batch(cur) -> int:
    cur.execute(
        """SELECT ib.batch_id
           FROM ingest_batch ib
           LEFT JOIN phase3_batch_result p3 ON p3.batch_id=ib.batch_id
           WHERE p3.batch_id IS NOT NULL
              OR ib.processing_status IN ('PHASE2C_READY','PHASE3_QA_HOLD','QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS')
           ORDER BY ib.batch_id DESC
           LIMIT 1"""
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError('No Phase-3-capable batch found')
    return int(row['batch_id'])


def _verify_valid(cur):
    cur.execute(
        """SELECT ean_upc,article_number,main_article_number,family_id,
                  selling_uom,base_uom,base_qty_per_selling_unit,
                  current_cost_per_base_uom,current_cost_per_selling_unit,
                  cost_source,cost_date,quick_check_status,blocking_reason
           FROM quick_check_current
           WHERE ean_upc=%s
           LIMIT 1""",
        (VALID_UPC,),
    )
    return cur.fetchone()


def _verify_retired(cur):
    cur.execute(
        """SELECT su.upc_id,su.ean_upc,su.record_status,
                  (SELECT COUNT(*) FROM bridge_article_upc bau
                    WHERE bau.upc_id=su.upc_id
                      AND bau.mapping_status='CONFIRMED'
                      AND bau.is_primary=TRUE
                      AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))) AS active_article_links,
                  (SELECT COUNT(*) FROM selling_upc_uom_history h
                    WHERE h.upc_id=su.upc_id
                      AND h.mapping_status='CONFIRMED'
                      AND (h.effective_to IS NULL OR h.effective_to>CURRENT_TIMESTAMP(6))) AS active_uom_rows,
                  (SELECT COUNT(*) FROM quick_check_current q
                    WHERE q.upc_id=su.upc_id OR q.ean_upc=su.ean_upc) AS quick_check_rows
           FROM selling_upc su
           WHERE su.ean_upc=%s
           LIMIT 1""",
        (RETIRED_UPC,),
    )
    return cur.fetchone()


def _family_rows(cur):
    cur.execute(
        """SELECT q.ean_upc,q.article_number,q.main_article_number,
                  q.selling_uom,q.base_uom,q.base_qty_per_selling_unit,
                  q.current_cost_per_base_uom,q.current_cost_per_selling_unit,
                  q.quick_check_status,q.blocking_reason
           FROM quick_check_current q
           JOIN product_family pf ON pf.family_id=q.family_id
           WHERE pf.main_article_number=%s
           ORDER BY q.ean_upc""",
        (ARTICLE,),
    )
    return cur.fetchall()


def _assertions(valid, retired, family_rows):
    checks = {
        'valid_upc_present': bool(valid),
        'valid_article': bool(valid and str(valid.get('article_number')) == ARTICLE),
        'valid_main_article': bool(valid and str(valid.get('main_article_number')) == ARTICLE),
        'selling_uom_pack': bool(valid and str(valid.get('selling_uom') or '').upper() == 'PACK'),
        'base_uom_ea': bool(valid and str(valid.get('base_uom') or '').upper() == 'EA'),
        'factor_one': bool(valid and valid.get('base_qty_per_selling_unit') is not None and Decimal(str(valid['base_qty_per_selling_unit'])) == Decimal('1')),
        'selling_cost_matches_base_cost': bool(
            valid
            and valid.get('current_cost_per_base_uom') is not None
            and valid.get('current_cost_per_selling_unit') is not None
            and Decimal(str(valid['current_cost_per_base_uom'])) == Decimal(str(valid['current_cost_per_selling_unit']))
        ),
        'retired_upc_not_active': bool((retired is None) or str(retired.get('record_status') or '').upper() == 'RETIRED'),
        'retired_upc_no_active_links': bool((retired is None) or int(retired.get('active_article_links') or 0) == 0),
        'retired_upc_no_active_uom': bool((retired is None) or int(retired.get('active_uom_rows') or 0) == 0),
        'retired_upc_not_published': bool((retired is None) or int(retired.get('quick_check_rows') or 0) == 0),
        'family291_only_valid_upc_published': [str(x['ean_upc']) for x in family_rows] == [VALID_UPC],
    }
    return checks, all(checks.values())


def main() -> int:
    ap = argparse.ArgumentParser(description='FULL MYSQL v7.0.25 Family 291 final-authority repair')
    ap.add_argument('--batch', type=int, default=None, help='Phase 3 batch id; defaults to latest Phase-3-capable batch')
    args = ap.parse_args()
    try:
        print(json.dumps({'version': VERSION, 'database': test_database(), 'mode': 'FINAL_USER_AUTHORITY_LOCK'}, indent=2, default=str), flush=True)
        with db_conn() as conn:
            cur = conn.cursor(dictionary=True)
            try:
                batch_id = args.batch or _latest_batch(cur)
                print(f'[1/4] Batch {batch_id}: applying authoritative UPC/UOM override...', flush=True)
                override_result = apply_manual_upc_overrides(cur)
                print(f'[2/4] Retiring nonexistent UPC {RETIRED_UPC}...', flush=True)
                retirement_result = apply_manual_upc_retirements(cur)

                # Derived row-level serving QA is regenerated below.
                cur.execute(
                    """UPDATE qa_phase3_issue
                       SET issue_status='RESOLVED',
                           detail_json=JSON_SET(COALESCE(detail_json,JSON_OBJECT()),
                             '$.resolution','Superseded by v7.0.25 final user-authority refresh')
                       WHERE batch_id=%s
                         AND issue_status='OPEN'
                         AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
                    (batch_id,),
                )

                print('[3/4] Rebuilding Quick Check serving snapshot...', flush=True)
                qc = rebuild_quick_check(cur, batch_id)
                valid = _verify_valid(cur)
                retired = _verify_retired(cur)
                family_rows = _family_rows(cur)
                checks, passed = _assertions(valid, retired, family_rows)
                if not passed:
                    raise RuntimeError('v7.0.25 verification failed: ' + json.dumps(checks, default=str))

                cur.execute(
                    """SELECT COUNT(*) AS c
                       FROM qa_phase3_issue
                       WHERE batch_id=%s
                         AND issue_status='OPEN'
                         AND UPPER(severity) IN ('HIGH','CRITICAL')
                         AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'""",
                    (batch_id,),
                )
                blocking = int((cur.fetchone() or {}).get('c') or 0)
                if blocking > 0 or qc['rows'] == 0:
                    status = 'PHASE3_QA_HOLD'
                elif qc['hold'] > 0:
                    status = 'QUICK_CHECK_READY_WITH_HOLDS'
                else:
                    status = 'QUICK_CHECK_READY'

                cur.execute('SELECT detail_json FROM phase3_batch_result WHERE batch_id=%s', (batch_id,))
                row = cur.fetchone(); detail = {}
                if row:
                    try: detail = json.loads(row.get('detail_json') or '{}')
                    except Exception: detail = {}
                detail['v725_family291_authority_lock'] = {
                    'valid_upc': VALID_UPC,
                    'retired_nonexistent_upc': RETIRED_UPC,
                    'article': ARTICLE,
                    'authoritative_pack_config': '40 PACK/CASE; 150G/PACK; sold by PACK only',
                    'manual_overrides': override_result,
                    'manual_retirements': retirement_result,
                    'valid_verification': valid,
                    'retired_verification': retired,
                    'family_rows': family_rows,
                    'assertions': checks,
                }
                cur.execute(
                    """UPDATE phase3_batch_result
                       SET quick_check_rows=%s,quick_check_ready_rows=%s,quick_check_hold_rows=%s,
                           blocking_issue_count=%s,result_status=%s,detail_json=%s,
                           updated_at=CURRENT_TIMESTAMP(6)
                       WHERE batch_id=%s""",
                    (qc['rows'], qc['ready'], qc['hold'], blocking, status, json.dumps(detail, default=str), batch_id),
                )
                cur.execute(
                    """UPDATE ingest_batch
                       SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6)
                       WHERE batch_id=%s""",
                    (status, batch_id),
                )
                conn.commit()
                print('[4/4] PASS.', flush=True)
                print(json.dumps({
                    'version': VERSION,
                    'batch_id': batch_id,
                    'status': status,
                    'valid_upc': valid,
                    'retired_upc': retired,
                    'family_3461050_quick_check': family_rows,
                    'assertions': checks,
                    'quick_check': {
                        'current_active_rows': qc['rows'],
                        'ready': qc['ready'],
                        'hold': qc['hold'],
                        'historical_rows': qc.get('historical_rows'),
                        'serving_rows_total': qc.get('serving_rows_total'),
                    },
                }, indent=2, ensure_ascii=False, default=str))
                return 0
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
    except Exception as exc:
        print(json.dumps({'version': VERSION, 'result': 'FAILED', 'error': repr(exc), 'traceback': traceback.format_exc()}, indent=2, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
