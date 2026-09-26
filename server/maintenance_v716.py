from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from phase3 import process_phase3, audit_phase3

VERSION = "7.0.16-active-28d-uom-repair"


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
        detail = {}
        if p3:
            try:
                detail = json.loads(p3.get("detail_json") or "{}")
            except Exception:
                detail = {}

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

        cur.execute(
            """SELECT COUNT(*) AS c
               FROM qa_phase3_issue
               WHERE batch_id=%s
                 AND issue_status='OPEN'
                 AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'
                 AND JSON_CONTAINS(detail_json, JSON_QUOTE('SELLING_UOM_MISSING'), '$.reasons')""",
            (batch_id,),
        )
        uom_missing = int((cur.fetchone() or {}).get("c") or 0)

        cur.close()

    return {
        "phase3": {k:v for k,v in (p3 or {}).items() if k != "detail_json"},
        "quick_check_reason_counts": reasons,
        "selling_uom_missing_count": uom_missing,
        "active_28d_uom_repair": detail.get("active_28d_uom_repair"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FULL MYSQL v7.0.16 active-28-data-day UOM repair."
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
                f"[1/4] Re-running Phase 3 for Batch {args.batch} with ACTIVE-28D UOM repair...",
                flush=True,
            )
            phase3 = process_phase3(args.batch)

            print("[2/4] Auditing current readiness...", flush=True)
            audit = audit_phase3(args.batch)

            print("[3/4] Building UOM repair summary...", flush=True)
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
