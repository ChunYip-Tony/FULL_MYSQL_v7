from __future__ import annotations

import argparse
import json
import traceback
from collections import Counter

from db import db_conn, test_database
from current_active_cost_repair import repair_current_active_cost
from phase3 import rebuild_quick_check

VERSION = "7.0.20-fast-cost-lineage-repair"


def _compact_repair(r: dict) -> dict:
    reasons = Counter()
    for item in r.get("remaining") or []:
        d = item.get("diagnostics") or {}
        reasons[str(d.get("reason") or "UNKNOWN")] += 1

    return {
        "scope": r.get("scope"),
        "active_upcs_examined": r.get("active_upcs_examined"),
        "initial_missing_cost_upcs": r.get("initial_missing_cost_upcs"),
        "initial_missing_cost_families": r.get("initial_missing_cost_families"),
        "company_rows_relinked": r.get("company_rows_relinked"),
        "existing_cost_observations_relinked": r.get("existing_cost_observations_relinked"),
        "receipt_cost_rows_backfilled": r.get("receipt_cost_rows_backfilled"),
        "official_cost_rows_backfilled": r.get("official_cost_rows_backfilled"),
        "oh_rows_backfilled": (r.get("oh_fallback") or {}).get("rows_backfilled"),
        "resolved_cost_upcs": r.get("resolved_cost_upcs"),
        "remaining_missing_cost_upcs": r.get("remaining_missing_cost_upcs"),
        "remaining_missing_cost_families": r.get("remaining_missing_cost_families"),
        "remaining_reason_counts": dict(sorted(reasons.items())),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FULL MYSQL v7.0.20 fast current-active cost-lineage repair."
    )
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    try:
        print(json.dumps({
            "version": VERSION,
            "database": test_database(),
            "mode": "FAST_NARROW_REPAIR",
        }, indent=2, default=str), flush=True)

        with db_conn() as conn:
            cur = conn.cursor(dictionary=True)
            try:
                print("[1/3] Relinking current-active cost evidence...", flush=True)
                repair = repair_current_active_cost(cur, args.batch)

                # Only current serving QA is recomputed. Do not touch identity,
                # RAW, Phase2C, sales history, movement history, or historical rows.
                cur.execute(
                    """UPDATE qa_phase3_issue
                       SET issue_status='RESOLVED',
                           detail_json=JSON_SET(
                               COALESCE(detail_json,JSON_OBJECT()),
                               '$.resolution',
                               'Superseded by v7.0.20 fast current-serving refresh'
                           )
                       WHERE batch_id=%s
                         AND issue_status='OPEN'
                         AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
                    (args.batch,),
                )

                print("[2/3] Refreshing Quick Check serving snapshot only...", flush=True)
                qc = rebuild_quick_check(cur, args.batch)

                cur.execute(
                    """SELECT COUNT(*) AS c
                       FROM qa_phase3_issue
                       WHERE batch_id=%s
                         AND issue_status='OPEN'
                         AND UPPER(severity) IN ('HIGH','CRITICAL')
                         AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'""",
                    (args.batch,),
                )
                blocking = int((cur.fetchone() or {}).get("c") or 0)

                if blocking > 0 or qc["rows"] == 0:
                    status = "PHASE3_QA_HOLD"
                elif qc["hold"] > 0:
                    status = "QUICK_CHECK_READY_WITH_HOLDS"
                else:
                    status = "QUICK_CHECK_READY"

                # Preserve prior Phase3 details and add this narrow repair.
                cur.execute(
                    """SELECT detail_json
                       FROM phase3_batch_result
                       WHERE batch_id=%s""",
                    (args.batch,),
                )
                row = cur.fetchone()
                old_detail = {}
                if row:
                    try:
                        old_detail = json.loads(row.get("detail_json") or "{}")
                    except Exception:
                        old_detail = {}
                old_detail["current_active_cost_repair"] = repair
                old_detail["v720_fast_refresh"] = {
                    "mode": "FAST_NARROW_REPAIR",
                    "quick_check": qc,
                }

                cur.execute(
                    """UPDATE phase3_batch_result
                       SET quick_check_rows=%s,
                           quick_check_ready_rows=%s,
                           quick_check_hold_rows=%s,
                           blocking_issue_count=%s,
                           result_status=%s,
                           detail_json=%s,
                           updated_at=CURRENT_TIMESTAMP(6)
                       WHERE batch_id=%s""",
                    (
                        qc["rows"], qc["ready"], qc["hold"], blocking,
                        status, json.dumps(old_detail, default=str), args.batch,
                    ),
                )
                cur.execute(
                    """UPDATE ingest_batch
                       SET processing_status=%s,
                           completed_at=CURRENT_TIMESTAMP(6)
                       WHERE batch_id=%s""",
                    (status, args.batch),
                )

                conn.commit()

                print("[3/3] Done.", flush=True)
                out = {
                    "version": VERSION,
                    "status": status,
                    "blocking_issue_count": blocking,
                    "quick_check": {
                        "current_active_rows": qc["rows"],
                        "ready": qc["ready"],
                        "hold": qc["hold"],
                        "historical_rows": qc.get("historical_rows"),
                        "serving_rows_total": qc.get("serving_rows_total"),
                    },
                    "cost_repair": _compact_repair(repair),
                }
                print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
                return 0
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

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
