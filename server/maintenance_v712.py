from __future__ import annotations

import argparse
import json
import traceback

from article_manual_multitab_repair import alias_relation_self_test
from db import db_conn, test_database
from phase3 import process_phase3, audit_phase3

VERSION = "7.0.12-multitab-article-manual-repair"


def summary(batch_id: int) -> dict:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT processing_status FROM ingest_batch WHERE batch_id=%s""",
            (batch_id,),
        )
        b = cur.fetchone()

        cur.execute(
            """SELECT result_status,blocking_issue_count,quick_check_rows,
                      quick_check_ready_rows,quick_check_hold_rows,detail_json,updated_at
               FROM phase3_batch_result WHERE batch_id=%s""",
            (batch_id,),
        )
        p3 = cur.fetchone()

        detail = {}
        if p3:
            try:
                detail = json.loads(p3.get('detail_json') or '{}')
            except Exception:
                detail = {}

        cur.execute(
            """SELECT issue_code,UPPER(severity) AS severity,COUNT(*) AS issue_count
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
               GROUP BY issue_code,UPPER(severity)""",
            (batch_id,),
        )
        counts = cur.fetchall()

        reasons = {}
        cur.execute(
            """SELECT detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
            (batch_id,),
        )
        for row in cur.fetchall():
            try:
                d = json.loads(row.get('detail_json') or '{}')
            except Exception:
                d = {}
            for reason in d.get('reasons') or []:
                reasons[str(reason)] = reasons.get(str(reason), 0) + 1

        cur.execute(
            """SELECT entity_key,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='SOLD_UPC_UNMAPPED'
               ORDER BY issue_id""",
            (batch_id,),
        )
        remaining = []
        for row in cur.fetchall():
            try:
                d = json.loads(row.get('detail_json') or '{}')
            except Exception:
                d = {}
            remaining.append({
                'upc': str(row['entity_key']),
                'description': d.get('description'),
                'multitab_candidates': d.get('v712_cross_tab_candidates'),
            })

        cur.close()

    return {
        'processing_status': b['processing_status'] if b else None,
        'phase3': {k:v for k,v in (p3 or {}).items() if k != 'detail_json'},
        'issue_counts': counts,
        'quick_check_reason_counts': reasons,
        'article_manual_multitab_repair': detail.get('article_manual_multitab_repair'),
        'remaining_active_unmapped': remaining,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='FULL MYSQL v7.0.12 multi-tab Article Manual repair.'
    )
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--report-only', action='store_true')
    args = ap.parse_args()

    try:
        self_test = alias_relation_self_test()
        if not self_test['pass']:
            raise RuntimeError(f'Alias relation self-test failed: {self_test}')

        print(json.dumps({
            'version': VERSION,
            'database': test_database(),
            'alias_relation_self_test': self_test,
        }, indent=2, default=str), flush=True)

        if args.report_only:
            out = {'version': VERSION, 'mode': 'REPORT_ONLY', 'summary': summary(args.batch)}
        else:
            print(f"[1/4] Re-running Phase 3 for Batch {args.batch} with multi-tab Article Manual repair...", flush=True)
            phase3 = process_phase3(args.batch)
            print("[2/4] Auditing repaired serving state...", flush=True)
            audit = audit_phase3(args.batch)
            print("[3/4] Building remaining blocker/UOM summary...", flush=True)
            s = summary(args.batch)
            print("[4/4] Done.", flush=True)
            out = {
                'version': VERSION,
                'phase3_run': phase3,
                'audit_pass': audit.get('pass'),
                'summary': s,
            }

        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({
            'version': VERSION,
            'result': 'FAILED',
            'error': repr(exc),
            'traceback': traceback.format_exc(),
        }, indent=2, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
