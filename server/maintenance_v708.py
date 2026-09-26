from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from phase3 import process_phase3, audit_phase3

VERSION = "7.0.8-phase3-scope-reclassification"


def reason_summary(batch_id: int) -> dict:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(
            """SELECT issue_code,entity_key,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
               ORDER BY issue_id""",
            (batch_id,),
        )
        rows=cur.fetchall()
        reason_counts={}
        issue_counts={}
        sold_unmapped=[]
        for row in rows:
            code=str(row['issue_code'])
            issue_counts[code]=issue_counts.get(code,0)+1
            try:
                detail=json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail={}
            if code=='QUICK_CHECK_CORE_FIELD_MISSING':
                for reason in detail.get('reasons') or []:
                    reason_counts[str(reason)]=reason_counts.get(str(reason),0)+1
            elif code=='SOLD_UPC_UNMAPPED':
                sold_unmapped.append({
                    'upc':str(row['entity_key']),
                    'description':detail.get('description'),
                })
        cur.close()
    return {
        'issue_counts':issue_counts,
        'quick_check_reason_counts':reason_counts,
        'sold_upc_unmapped':sold_unmapped,
    }


def main() -> int:
    ap=argparse.ArgumentParser(description='Re-run one Phase 3 batch under v7.0.8 QA scope semantics.')
    ap.add_argument('--batch',type=int,default=8)
    ap.add_argument('--report-only',action='store_true')
    args=ap.parse_args()
    try:
        print(json.dumps({'version':VERSION,'database':test_database()},indent=2,default=str),flush=True)
        if args.report_only:
            print(json.dumps(reason_summary(args.batch),indent=2,ensure_ascii=False,default=str))
            return 0

        print(f"[1/3] Re-running Phase 3 for Batch {args.batch}...",flush=True)
        result=process_phase3(args.batch)
        print("[2/3] Auditing batch-vs-serving QA scopes...",flush=True)
        audit=audit_phase3(args.batch)
        print("[3/3] Building concise remaining-QA report...",flush=True)
        report={
            'version':VERSION,
            'phase3':result,
            'audit_pass':audit.get('pass'),
            'batch_blocking_issues':len(audit.get('blocking_issues') or []),
            'serving_issues':len(audit.get('serving_issues') or []),
            'remaining':reason_summary(args.batch),
        }
        print(json.dumps(report,indent=2,ensure_ascii=False,default=str))
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
