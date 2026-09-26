from __future__ import annotations

import argparse
import json
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Any

from db import db_conn, test_database
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3, relink_history
from manual_overrides import apply_manual_upc_overrides

VERSION = "7.0.7-central-identity-backfill-resume"
PATCH_VERSION = VERSION


def _issue_counts(cur, table: str, batch_id: int) -> list[dict[str, Any]]:
    # Use a derived table so ORDER BY references grouped aliases only.
    # This is compatible with MySQL ONLY_FULL_GROUP_BY.
    cur.execute(
        f"""SELECT g.issue_code,g.severity,g.issue_count
            FROM (
                SELECT issue_code,UPPER(severity) AS severity,COUNT(*) AS issue_count
                FROM {table}
                WHERE batch_id=%s AND issue_status='OPEN'
                GROUP BY issue_code,UPPER(severity)
            ) AS g
            ORDER BY FIELD(g.severity,'CRITICAL','HIGH','MEDIUM','LOW'),
                     g.issue_count DESC,g.issue_code""",
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


def migrate_legacy_same_family_upc_links() -> dict[str, Any]:
    """Canonicalize UPC->SUB active-primary links to UPC->MAIN when one family is unambiguous."""
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT bau.article_upc_id,bau.upc_id,bau.article_id,bau.sales_set_number,
                          baf.family_id,pf.main_article_number,amain.article_id AS main_article_id
                   FROM bridge_article_upc bau
                   JOIN bridge_article_family baf ON baf.article_id=bau.article_id
                     AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                     AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   JOIN article amain ON amain.article_number=pf.main_article_number
                   WHERE bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
                     AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
                   ORDER BY bau.upc_id,bau.article_upc_id"""
            )
            groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for row in cur.fetchall():
                groups[int(row['upc_id'])].append(row)

            result = {
                'upcs_examined': len(groups),
                'upcs_canonicalized': 0,
                'legacy_links_superseded': 0,
                'canonical_links_inserted': 0,
                'canonical_links_reactivated': 0,
                'cross_family_upcs_left_for_qa': 0,
            }

            for upc_id, rows in groups.items():
                families = {int(r['family_id']) for r in rows}
                if len(families) != 1:
                    result['cross_family_upcs_left_for_qa'] += 1
                    continue
                main_ids = {int(r['main_article_id']) for r in rows}
                if len(main_ids) != 1:
                    result['cross_family_upcs_left_for_qa'] += 1
                    continue

                main_id = next(iter(main_ids))
                non_main = [r for r in rows if int(r['article_id']) != main_id]
                if not non_main:
                    continue

                sales_set = next((r['sales_set_number'] for r in rows if r.get('sales_set_number')), None)
                cur.execute(
                    """SELECT article_upc_id
                       FROM bridge_article_upc
                       WHERE article_id=%s AND upc_id=%s AND relationship_type='SELLING'
                       ORDER BY article_upc_id DESC LIMIT 1""",
                    (main_id, upc_id),
                )
                canonical = cur.fetchone()
                if canonical:
                    canonical_id = int(canonical['article_upc_id'])
                    cur.execute(
                        """UPDATE bridge_article_upc
                           SET mapping_status='CONFIRMED',is_primary=TRUE,confidence=1.0,valid_to=NULL,
                               sales_set_number=COALESCE(sales_set_number,%s)
                           WHERE article_upc_id=%s""",
                        (sales_set, canonical_id),
                    )
                    result['canonical_links_reactivated'] += 1
                else:
                    cur.execute(
                        """INSERT INTO bridge_article_upc
                           (article_id,upc_id,relationship_type,sales_set_number,is_primary,mapping_status,confidence)
                           VALUES (%s,%s,'SELLING',%s,TRUE,'CONFIRMED',1.0)""",
                        (main_id, upc_id, sales_set),
                    )
                    canonical_id = int(cur.lastrowid)
                    result['canonical_links_inserted'] += 1

                retired_ids = []
                for r in non_main:
                    cur.execute(
                        """UPDATE bridge_article_upc
                           SET mapping_status='SUPERSEDED',is_primary=FALSE,
                               valid_to=COALESCE(valid_to,CURRENT_TIMESTAMP(6))
                           WHERE article_upc_id=%s""",
                        (r['article_upc_id'],),
                    )
                    if cur.rowcount:
                        retired_ids.append(int(r['article_upc_id']))
                        result['legacy_links_superseded'] += 1

                # Durable migration evidence, deduplicated by canonical link + role.
                cur.execute(
                    """SELECT evidence_id
                       FROM normalized_source_evidence
                       WHERE object_type='ARTICLE_UPC'
                         AND object_id=%s
                         AND evidence_role='V7_0_6_CANONICAL_MIGRATION'
                       LIMIT 1""",
                    (canonical_id,),
                )
                if not cur.fetchone():
                    cur.execute(
                        """INSERT INTO normalized_source_evidence
                           (object_type,object_id,evidence_role,evidence_json)
                           VALUES ('ARTICLE_UPC',%s,'V7_0_6_CANONICAL_MIGRATION',%s)""",
                        (
                            canonical_id,
                            json.dumps(
                                {
                                    'superseded_article_upc_ids': retired_ids,
                                    'reason': 'UPC_CANONICAL_TO_MAIN_FAMILY',
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    )
                result['upcs_canonicalized'] += 1

            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def reset_identity_batch(batch_id: int) -> dict[str, int]:
    """Reset only derived Phase2C state for re-evaluation; RAW stays immutable."""
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute('SELECT processing_status FROM ingest_batch WHERE batch_id=%s FOR UPDATE', (batch_id,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f'Identity batch {batch_id} does not exist.')

            cur.execute(
                """UPDATE qa_identity_uom_issue
                   SET issue_status='RESOLVED',resolved_at=CURRENT_TIMESTAMP(6),
                       resolution_note=CONCAT(COALESCE(resolution_note,''),
                         CASE WHEN COALESCE(resolution_note,'')='' THEN '' ELSE '\n' END,
                         'Superseded and re-evaluated by ',%s)
                   WHERE batch_id=%s AND issue_status='OPEN'""",
                (PATCH_VERSION, batch_id),
            )
            retired_qa = int(cur.rowcount)

            cur.execute('DELETE FROM phase2c_row_state WHERE batch_id=%s', (batch_id,))
            row_states = int(cur.rowcount)
            cur.execute('DELETE FROM phase2c_batch_result WHERE batch_id=%s', (batch_id,))
            batch_results = int(cur.rowcount)
            cur.execute('DELETE FROM normalized_source_evidence WHERE batch_id=%s', (batch_id,))
            evidence = int(cur.rowcount)

            cur.execute(
                """DELETE FROM uom_source_alias
                   WHERE source_system IN ('monthly_pi_form','article_manual')
                     AND UPPER(TRIM(source_uom_code)) IN ('#N/A','N/A','NA','NULL','NONE','-','--')"""
            )
            uom_aliases = int(cur.rowcount)

            cur.execute(
                "UPDATE ingest_batch SET processing_status='RAW_RELEASED',completed_at=NULL WHERE batch_id=%s",
                (batch_id,),
            )
            conn.commit()
            return {
                'retired_old_identity_qa': retired_qa,
                'deleted_phase2c_row_state': row_states,
                'deleted_phase2c_result': batch_results,
                'deleted_batch_evidence': evidence,
                'deleted_missing_uom_aliases': uom_aliases,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()



def report_only(identity_batch: int = 7, history_batches: list[int] | None = None) -> dict[str, Any]:
    """Read current repair/QA state without mutating the database."""
    history_batches = history_batches or [8]
    out: dict[str, Any] = {
        "version": VERSION,
        "mode": "REPORT_ONLY",
        "ran_at": datetime.now().isoformat(),
        "database": test_database(),
        "identity_batch": _status(identity_batch),
        "history_batches": {},
    }
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        out["identity_open_issue_counts"] = _issue_counts(
            cur, "qa_identity_uom_issue", identity_batch
        )

        cur.execute(
            """SELECT result_status,blocking_issue_count,source_row_count,
                      normalized_row_count,qa_hold_row_count,updated_at
               FROM phase2c_batch_result WHERE batch_id=%s""",
            (identity_batch,),
        )
        out["identity_phase2c_result"] = cur.fetchone()

        for batch_id in history_batches:
            cur.execute(
                """SELECT result_status,blocking_issue_count,quick_check_rows,
                          quick_check_ready_rows,quick_check_hold_rows,updated_at
                   FROM phase3_batch_result WHERE batch_id=%s""",
                (batch_id,),
            )
            p3 = cur.fetchone()
            out["history_batches"][str(batch_id)] = {
                "batch": _status(batch_id),
                "phase3_result": p3,
                "open_issue_counts": _issue_counts(cur, "qa_phase3_issue", batch_id),
            }

        cur.close()

    out["result"] = "REPORT_READY"
    return out


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

    print("[1/6] Canonicalizing same-family UPC links...", flush=True)
    report["legacy_upc_migration"] = migrate_legacy_same_family_upc_links()

    print(f"[2/6] Resetting and rebuilding identity Batch {identity_batch}...", flush=True)
    report["identity_reset"] = reset_identity_batch(identity_batch)
    report["identity_phase2c"] = normalize_batch(identity_batch)
    report["identity_phase2c_audit"] = audit_phase2c(identity_batch)

    if not report["identity_phase2c_audit"].get("pass"):
        report["result"] = "IDENTITY_STILL_QA_HOLD"
        return report

    print("[3/6] Applying persistent user-confirmed overrides...", flush=True)
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        report["manual_overrides"] = apply_manual_upc_overrides(cur)

        print("[4/6] Relinking already-ingested history to repaired identity...", flush=True)
        relink_history(cur)
        conn.commit()
        cur.close()

    print("[5/6] Re-evaluating selected Phase 3 batches...", flush=True)
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

    print("[6/6] Building final QA report...", flush=True)
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
    ap = argparse.ArgumentParser(description="FULL MYSQL v7.0.6 central identity/UOM backfill")
    ap.add_argument("--identity-batch", type=int, default=7)
    ap.add_argument(
        "--history-batches",
        default="8",
        help="Comma-separated Phase 3 batches to re-evaluate. Default: 8. Example: 8,6",
    )
    ap.add_argument(
        "--report-only",
        action="store_true",
        help="Read current Batch 7/8 repair and QA state without changing database data.",
    )
    args = ap.parse_args()
    batches = [int(x.strip()) for x in args.history_batches.split(",") if x.strip()]
    try:
        if args.report_only:
            report = report_only(args.identity_batch, batches)
        else:
            report = run(args.identity_batch, batches)
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        return 0 if report["result"] in {"READY", "COMPLETED_WITH_TRUE_QA_REMAINS", "REPORT_READY"} else 2
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
