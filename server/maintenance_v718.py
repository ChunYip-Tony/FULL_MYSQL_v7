from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database

VERSION = "7.0.18-qa-summary-serving-parity"


def summary(batch_id: int) -> dict:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """SELECT result_status,blocking_issue_count,quick_check_rows,
                      quick_check_ready_rows,quick_check_hold_rows,updated_at
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

        cur.execute(
            """SELECT ean_upc,blocking_reason
               FROM quick_check_current
               WHERE quick_check_status='QA_HOLD'
               ORDER BY ean_upc"""
        )
        rows = cur.fetchall()
        reasons = {}
        holds = []
        for row in rows:
            rs = [
                x.strip()
                for x in str(row.get("blocking_reason") or "").split(",")
                if x and x.strip()
            ]
            for reason in rs:
                reasons[reason] = reasons.get(reason, 0) + 1
            holds.append({"upc": str(row["ean_upc"]), "reasons": rs})

        scope["hold_upc_list_count"] = len(holds)
        scope["hold_reason_row_parity"] = (
            int(scope.get("current_hold_rows") or 0) == len(holds)
        )

        cur.close()

    return {
        "phase3": p3,
        "quick_check_scope": scope,
        "quick_check_reason_counts": reasons,
        "quick_check_hold_upcs": holds,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FULL MYSQL v7.0.18 Quick Check serving/parity audit."
    )
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    try:
        out = {
            "version": VERSION,
            "database": test_database(),
            "summary": summary(args.batch),
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
