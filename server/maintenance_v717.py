from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from phase3 import process_phase3, audit_phase3

VERSION = "7.0.17-active-28d-quick-check-scope"


def summary(batch_id: int) -> dict:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """SELECT result_status,blocking_issue_count,quick_check_rows,
                      quick_check_ready_rows,quick_check_hold_rows,detail_json,updated_at
               FROM phase3_batch_result
               WHERE batch_id=%s""",
            (batch_id,),
        )
        p3 = cur.fetchone()

        cur.execute(
            """SELECT
                 COUNT(*) AS serving_rows_total,
                 SUM(CASE WHEN quick_check_status='HISTORICAL_ONLY' THEN 1 ELSE 0 END) AS historical_rows,
                 SUM(CASE WHEN quick_check_status IN ('READY','QA_HOLD') THEN 1 ELSE 0 END) AS current_active_rows,
                 SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS current_ready_rows,
                 SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS current_hold_rows
               FROM quick_check_current"""
        )
        scope = cur.fetchone() or {}

        reasons = {}
        cur.execute(
            """SELECT detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s
                 AND issue_status='OPEN'
                 AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
            (batch_id,),
        )
        for row in cur.fetchall():
            try:
                d = json.loads(row.get("detail_json") or "{}")
            except Exception:
                d = {}
            for reason in d.get("reasons") or []:
                reasons[str(reason)] = reasons.get(str(reason), 0) + 1

        cur.close()

    return {
        "phase3": {k:v for k,v in (p3 or {}).items() if k != "detail_json"},
        "quick_check_scope": scope,
        "quick_check_reason_counts": reasons,
        "activity_rule": "POS_POSITIVE_LATEST_UP_TO_28_VALID_COMPLETED_DATA_DAYS",
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FULL MYSQL v7.0.17 current-active Quick Check scope normalization."
    )
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    try:
        print(json.dumps({
            "version": VERSION,
            "database": test_database(),
        }, indent=2, default=str), flush=True)

        if args.report_only:
            out = {
                "version": VERSION,
                "mode": "REPORT_ONLY",
                "summary": summary(args.batch),
            }
        else:
            print(
                f"[1/4] Re-running Phase 3 for Batch {args.batch} with ACTIVE-28D Quick Check scope...",
                flush=True,
            )
            phase3 = process_phase3(args.batch)

            print("[2/4] Auditing current readiness...", flush=True)
            audit = audit_phase3(args.batch)

            print("[3/4] Building active/historical serving summary...", flush=True)
            s = summary(args.batch)

            print("[4/4] Done.", flush=True)
            out = {
                "version": VERSION,
                "phase3_run": phase3,
                "audit_pass": audit.get("pass"),
                "summary": s,
            }

        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return 0

    except Exception as exc:
        print(json.dumps({
            "version": VERSION,
            "result": "FAILED",
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        }, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
