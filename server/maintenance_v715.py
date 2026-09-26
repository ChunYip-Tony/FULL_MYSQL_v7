from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from phase3 import process_phase3, audit_phase3

VERSION = "7.0.15-article-manual-size-dimensions-header-fix"


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
                detail = json.loads(p3.get("detail_json") or "{}")
            except Exception:
                detail = {}

        cur.execute(
            """SELECT issue_code,UPPER(severity) severity,COUNT(*) issue_count
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
               GROUP BY issue_code,UPPER(severity)
               ORDER BY FIELD(UPPER(severity),'CRITICAL','HIGH','MEDIUM','LOW'),
                        issue_code""",
            (batch_id,),
        )
        counts = cur.fetchall()

        cur.execute(
            """SELECT entity_key,severity,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s
                 AND issue_status='OPEN'
                 AND issue_code='SOLD_UPC_UNMAPPED'
               ORDER BY issue_id""",
            (batch_id,),
        )
        blocking = []
        waived = []
        for row in cur.fetchall():
            try:
                d = json.loads(row.get("detail_json") or "{}")
            except Exception:
                d = {}

            item = {
                "upc": str(row["entity_key"]),
                "description": d.get("description"),
                "severity": row.get("severity"),
                "signature_repair": d.get("v713_cross_tab_signature_repair"),
            }
            waiver = d.get("temporary_qa_waiver") or {}
            if (
                isinstance(waiver, dict)
                and waiver.get("waiver_type") == "IDENTITY_PENDING"
                and waiver.get("non_blocking_current_readiness") is True
            ):
                item["waiver"] = waiver
                waived.append(item)
            elif str(row.get("severity") or "").upper() in {"HIGH", "CRITICAL"}:
                blocking.append(item)

        cur.close()

    return {
        "processing_status": b["processing_status"] if b else None,
        "phase3": {k:v for k,v in (p3 or {}).items() if k != "detail_json"},
        "issue_counts": counts,
        "cross_tab_signature_repair": detail.get("cross_tab_signature_repair"),
        "blocking_active_unmapped": blocking,
        "temporarily_waived_active_unmapped": waived,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FULL MYSQL v7.0.15 Article Manual Size/dimensions header fix."
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
                f"[1/4] Re-running Phase 3 for Batch {args.batch} with Size/dimensions header fix...",
                flush=True,
            )
            phase3 = process_phase3(args.batch)

            print("[2/4] Auditing current readiness...", flush=True)
            audit = audit_phase3(args.batch)

            print("[3/4] Building concise repair summary...", flush=True)
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
