from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from phase3 import process_phase3, audit_phase3

VERSION = "7.0.10-pos28-active-selling-scope"


def concise_report(batch_id: int) -> dict:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)

        cur.execute("SELECT processing_status FROM ingest_batch WHERE batch_id=%s", (batch_id,))
        batch=cur.fetchone()

        cur.execute(
            """SELECT result_status,blocking_issue_count,quick_check_rows,
                      quick_check_ready_rows,quick_check_hold_rows,updated_at
               FROM phase3_batch_result WHERE batch_id=%s""",
            (batch_id,),
        )
        p3=cur.fetchone()

        cur.execute(
            """SELECT issue_code,UPPER(severity) severity,COUNT(*) issue_count
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
               GROUP BY issue_code,UPPER(severity)""",
            (batch_id,),
        )
        raw_counts=cur.fetchall()
        issue_counts={str(r['issue_code']):int(r['issue_count']) for r in raw_counts}

        cur.execute(
            """SELECT issue_code,entity_key,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code IN ('SOLD_UPC_UNMAPPED','HISTORICAL_SOLD_UPC_UNMAPPED')
               ORDER BY issue_code,issue_id""",
            (batch_id,),
        )
        active=[]
        historical=[]
        for row in cur.fetchall():
            try:
                d=json.loads(row.get('detail_json') or '{}')
            except Exception:
                d={}
            item={
                'upc':str(row['entity_key']),
                'description':d.get('description'),
                'activity_scope':d.get('activity_scope'),
                'activity_basis':d.get('activity_basis'),
                'recent_pos_qty_28_valid_days':d.get('recent_pos_qty_28_valid_days'),
                'recent_pos_valid_day_count':d.get('recent_pos_valid_day_count'),
            }
            if row['issue_code']=='HISTORICAL_SOLD_UPC_UNMAPPED':
                historical.append(item)
            else:
                active.append(item)

        cur.close()

    return {
        'batch_id':batch_id,
        'processing_status':batch['processing_status'] if batch else None,
        'phase3':p3,
        'issue_counts':issue_counts,
        'active_blocking_unmapped':active,
        'historical_nonblocking_unmapped':historical,
    }


def main() -> int:
    ap=argparse.ArgumentParser(
        description='FULL MYSQL v7.0.10: only positive POS sales in latest 28 valid data days define CURRENT active.'
    )
    ap.add_argument('--batch',type=int,default=8)
    ap.add_argument('--report-only',action='store_true')
    args=ap.parse_args()

    try:
        print(json.dumps({'version':VERSION,'database':test_database()},indent=2,default=str),flush=True)

        if not args.report_only:
            print(f"[1/3] Re-running Phase 3 for Batch {args.batch} with POS-28 active scope...",flush=True)
            result=process_phase3(args.batch)
            print("[2/3] Auditing current-vs-historical QA scope...",flush=True)
            audit=audit_phase3(args.batch)
            print("[3/3] Building concise POS-28 activity report...",flush=True)
            out={
                'version':VERSION,
                'phase3_run':result,
                'audit_pass':audit.get('pass'),
                'current_batch_blockers':len(audit.get('blocking_issues') or []),
                'serving_holds':len(audit.get('serving_issues') or []),
                'summary':concise_report(args.batch),
            }
        else:
            out={
                'version':VERSION,
                'mode':'REPORT_ONLY',
                'summary':concise_report(args.batch),
            }

        print(json.dumps(out,indent=2,ensure_ascii=False,default=str))
        return 0

    except Exception as exc:
        print(json.dumps({
            'version':VERSION,
            'result':'FAILED',
            'error':repr(exc),
            'traceback':traceback.format_exc(),
        },indent=2,ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
