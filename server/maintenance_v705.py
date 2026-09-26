from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime
from typing import Any

from db import db_conn, test_database
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3, relink_history
from manual_overrides import apply_manual_upc_overrides
from maintenance_repair_phase2c_v654 import migrate_legacy_same_family_upc_links, reset_identity_batch

VERSION = "7.0.5-central-identity-backfill"


def _issue_counts(cur, table: str, batch_id: int) -> list[dict[str, Any]]:
    cur.execute(
        f"""SELECT issue_code,UPPER(severity) AS severity,COUNT(*) AS issue_count
            FROM {table}
            WHERE batch_id=%s AND issue_status='OPEN'
            GROUP BY issue_code,UPPER(severity)
            ORDER BY FIELD(UPPER(severity),'CRITICAL','HIGH','MEDIUM','LOW'),
                     issue_count DESC,issue_code""",
        (batch_id,),
    )
    return cur.fetchall()


def _status(batch_id: int) -> dict[str, Any] | None:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT batch_id,batch_label,processing_status,file_count,source_row_count,
                      error_count,upload_started_at,completed_at
               FROM ingest_batch WHERE batch_id=%s""",
            (batch_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row


def run(identity_batch: int = 7, history_batches: list[int] | None = None) -> dict[str, Any]:
    history_batches = history_batches or [8]
    report: dict[str, Any] = {
        "version": VERSION,
        "ran_at": datetime.now().isoformat(),
        "identity_batch": identity_batch,
        "history_batches": history_batches,
        "database": test_database(),
        "before": {
            "identity": _status(identity_batch),
            "history": {str(b): _status(b) for b in history_batches},
        },
    }

    report["legacy_upc_migration"] = migrate_legacy_same_family_upc_links()
    report["identity_reset"] = reset_identity_batch(identity_batch)
    report["identity_phase2c"] = normalize_batch(identity_batch)
    report["identity_phase2c_audit"] = audit_phase2c(identity_batch)

    if not report["identity_phase2c_audit"].get("pass"):
        report["result"] = "IDENTITY_STILL_QA_HOLD"
        return report

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        report["manual_overrides"] = apply_manual_upc_overrides(cur)
        relink_history(cur)
        conn.commit()
        cur.close()

    report["history_results"] = {}
    for batch_id in history_batches:
        st = _status(batch_id)
        entry: dict[str, Any] = {"before": st}
        if not st or st["processing_status"] not in {"PHASE2C_READY", "PHASE3_QA_HOLD", "QUICK_CHECK_READY"}:
            entry["skipped"] = f"Batch status is not eligible for Phase 3 rerun: {st}"
            report["history_results"][str(batch_id)] = entry
            continue
        entry["phase3"] = process_phase3(batch_id)
        entry["audit"] = audit_phase3(batch_id)
        with db_conn() as conn:
            cur = conn.cursor(dictionary=True)
            entry["open_issue_counts"] = _issue_counts(cur, "qa_phase3_issue", batch_id)
            cur.close()
        entry["after"] = _status(batch_id)
        report["history_results"][str(batch_id)] = entry

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        report["identity_open_issue_counts"] = _issue_counts(cur, "qa_identity_uom_issue", identity_batch)
        cur.close()

    report["after"] = {
        "identity": _status(identity_batch),
        "history": {str(b): _status(b) for b in history_batches},
    }
    report["result"] = "COMPLETED_WITH_TRUE_QA_REMAINS" if any(
        (v.get("audit") or {}).get("pass") is False for v in report["history_results"].values()
    ) else "READY"
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="FULL MYSQL v7.0.5 central identity/UOM backfill")
    ap.add_argument("--identity-batch", type=int, default=7)
    ap.add_argument("--history-batches", default="8",
                    help="Comma-separated Phase 3 batches to re-evaluate. Default: 8. Example: 8,6")
    args = ap.parse_args()
    batches = [int(x.strip()) for x in args.history_batches.split(",") if x.strip()]
    try:
        report = run(args.identity_batch, batches)
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        return 0 if report["result"] in {"READY", "COMPLETED_WITH_TRUE_QA_REMAINS"} else 2
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
