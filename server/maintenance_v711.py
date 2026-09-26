from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from phase3 import process_phase3, audit_phase3


VERSION = "7.0.11-active-product-master-repair"


def _summary(batch_id: int) -> dict:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT processing_status
               FROM ingest_batch WHERE batch_id=%s""",
            (batch_id,),
        )
        batch = cur.fetchone()

        cur.execute(
            """SELECT result_status,blocking_issue_count,quick_check_rows,
                      quick_check_ready_rows,quick_check_hold_rows,detail_json,updated_at
               FROM phase3_batch_result WHERE batch_id=%s""",
            (batch_id,),
        )
        p3 = cur.fetchone()

        cur.execute(
            """SELECT issue_code,UPPER(severity) severity,COUNT(*) issue_count
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
               GROUP BY issue_code,UPPER(severity)""",
            (batch_id,),
        )
        issue_counts = {
            str(r['issue_code']): int(r['issue_count'])
            for r in cur.fetchall()
        }

        reason_counts = {}
        cur.execute(
            """SELECT detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
            (batch_id,),
        )
        for row in cur.fetchall():
            try:
                detail = json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail = {}
            for reason in detail.get('reasons') or []:
                reason_counts[str(reason)] = reason_counts.get(str(reason), 0) + 1

        cur.execute(
            """SELECT entity_key,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='SOLD_UPC_UNMAPPED'
               ORDER BY issue_id""",
            (batch_id,),
        )
        active_unmapped = []
        for row in cur.fetchall():
            try:
                detail = json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail = {}
            active_unmapped.append({
                'upc': str(row['entity_key']),
                'description': detail.get('description'),
                'repair_candidates': detail.get('v711_repair_candidates'),
            })

        detail_json = {}
        if p3:
            try:
                detail_json = json.loads(p3.get('detail_json') or '{}')
            except Exception:
                detail_json = {}

        cur.close()

    return {
        'batch_id': batch_id,
        'processing_status': batch['processing_status'] if batch else None,
        'phase3': {
            k: v for k, v in (p3 or {}).items()
            if k != 'detail_json'
        },
        'issue_counts': issue_counts,
        'quick_check_reason_counts': reason_counts,
        'active_unmapped_remaining': active_unmapped,
        'active_product_master_repair': detail_json.get('active_product_master_repair'),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description='FULL MYSQL v7.0.11 evidence-only active product master repair.'
    )
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--report-only', action='store_true')
    args = ap.parse_args()

    try:
        print(json.dumps({
            'version': VERSION,
            'database': test_database(),
        }, indent=2, default=str), flush=True)

        if args.report_only:
            out = {
                'version': VERSION,
                'mode': 'REPORT_ONLY',
                'summary': _summary(args.batch),
            }
        else:
            print(f"[1/4] Repairing exact-evidence UPC identity/UOM/cost for Batch {args.batch}...", flush=True)
            phase3 = process_phase3(args.batch)
            print("[2/4] Auditing Phase 3...", flush=True)
            audit = audit_phase3(args.batch)
            print("[3/4] Counting remaining Quick Check reasons...", flush=True)
            summary = _summary(args.batch)
            print("[4/4] Done.", flush=True)
            out = {
                'version': VERSION,
                'phase3_run': phase3,
                'audit_pass': audit.get('pass'),
                'summary': summary,
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
