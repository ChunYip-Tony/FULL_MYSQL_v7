from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from config import APP_DIR
from db import db_conn, test_database
from normalize import normalize_batch, audit_phase2c
from phase3 import process_phase3, audit_phase3

PATCH_VERSION = '6.5.4-article-manual-upc-authority'
REPORT_PATH = APP_DIR / 'QA_REPAIR_REPORT.json'
BACKUP_DIR = APP_DIR / 'qa_repair_backups'


def _json_default(v: Any):
    return str(v)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _fetchall(cur, sql: str, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


SCHEMA_REQUIREMENTS = {
    'ingest_batch': {'batch_id','batch_key','batch_label','processing_status','upload_started_at','processing_started_at','completed_at'},
    'qa_identity_uom_issue': {'issue_id','issue_status','batch_id','resolved_at','resolution_note'},
    'phase2c_row_state': {'batch_id'},
    'phase2c_batch_result': {'batch_id'},
    'normalized_source_evidence': {'evidence_id','object_type','object_id','batch_id','raw_table_name'},
    'uom_source_alias': {'source_system','source_uom_code'},
    'bridge_article_family': {'article_family_id','article_id','family_id','mapping_status','is_primary','valid_to'},
    'bridge_article_upc': {'article_upc_id','article_id','upc_id','mapping_status','is_primary','valid_to','sales_set_number'},
    'product_family': {'family_id','main_article_number'},
    'article': {'article_id','article_number'},
    'qa_phase3_issue': {'issue_id','batch_id','issue_status','issue_code','entity_key'},
}


def schema_preflight() -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT TABLE_NAME,COLUMN_NAME
               FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA=DATABASE()
               ORDER BY TABLE_NAME,ORDINAL_POSITION"""
        )
        present: dict[str, set[str]] = {}
        for row in cur.fetchall():
            present.setdefault(row['TABLE_NAME'], set()).add(row['COLUMN_NAME'])
        cur.close()
    missing: dict[str, list[str]] = {}
    for table, cols in SCHEMA_REQUIREMENTS.items():
        absent = sorted(cols - present.get(table, set()))
        if absent:
            missing[table] = absent
    return {
        'pass': not missing,
        'missing_columns': missing,
        'ingest_batch_columns': sorted(present.get('ingest_batch', set())),
        'qa_identity_uom_issue_columns': sorted(present.get('qa_identity_uom_issue', set())),
    }


def backup_state(identity_batch: int, history_batch: int | None) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = BACKUP_DIR / f'pre_v653_identity_batch_{identity_batch}_{stamp}.json'
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        data: dict[str, Any] = {
            'report_generated_at': datetime.now().isoformat(),
            'patch_version': PATCH_VERSION,
            'identity_batch': identity_batch,
            'history_batch': history_batch,
        }
        ids = [identity_batch] + ([history_batch] if history_batch is not None else [])
        placeholders = ','.join(['%s'] * len(ids))
        data['batch_status'] = _fetchall(
            cur,
            f'''SELECT batch_id,batch_key,batch_label,processing_status,
                       upload_started_at,processing_started_at,completed_at
                FROM ingest_batch WHERE batch_id IN ({placeholders}) ORDER BY batch_id''',
            tuple(ids),
        )
        data['identity_qa_open'] = _fetchall(
            cur,
            "SELECT * FROM qa_identity_uom_issue WHERE batch_id=%s AND issue_status='OPEN' ORDER BY issue_id",
            (identity_batch,),
        )
        if history_batch is not None:
            data['phase3_qa_open'] = _fetchall(
                cur,
                "SELECT * FROM qa_phase3_issue WHERE batch_id=%s AND issue_status='OPEN' ORDER BY issue_id",
                (history_batch,),
            )
        data['active_article_family'] = _fetchall(
            cur,
            """SELECT baf.*,a.article_number,pf.main_article_number
               FROM bridge_article_family baf
               JOIN article a ON a.article_id=baf.article_id
               JOIN product_family pf ON pf.family_id=baf.family_id
               WHERE baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                 AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               ORDER BY a.article_number,baf.article_family_id""",
        )
        data['active_article_upc'] = _fetchall(
            cur,
            """SELECT bau.*,a.article_number,su.ean_upc,pf.main_article_number
               FROM bridge_article_upc bau
               JOIN article a ON a.article_id=bau.article_id
               JOIN selling_upc su ON su.upc_id=bau.upc_id
               LEFT JOIN bridge_article_family baf ON baf.article_id=bau.article_id
                 AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                 AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               LEFT JOIN product_family pf ON pf.family_id=baf.family_id
               WHERE bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
                 AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
               ORDER BY su.ean_upc,bau.article_upc_id""",
        )
        cur.close()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default), encoding='utf-8')
    return path


def migrate_legacy_same_family_upc_links() -> dict[str, Any]:
    """Collapse legacy UPC->SUB links to UPC->MAIN when all active links for the UPC resolve to one family.

    This implements the confirmed identity model: selling UPCs are canonical children of the Main/Family
    article; sub-articles are sibling ordering/receiving variants, not alternate UPC identities.
    Cross-family UPCs are deliberately left untouched for QA/manual authority to arbitrate.
    """
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
                    # Defensive: one family should resolve to exactly one main article record.
                    result['cross_family_upcs_left_for_qa'] += 1
                    continue
                main_id = next(iter(main_ids))
                non_main = [r for r in rows if int(r['article_id']) != main_id]
                if not non_main:
                    continue

                sales_set = next((r['sales_set_number'] for r in rows if r.get('sales_set_number')), None)
                cur.execute(
                    """SELECT article_upc_id,mapping_status,is_primary,valid_to
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

                cur.execute(
                    """INSERT INTO normalized_source_evidence
                       (object_type,object_id,evidence_role,evidence_json)
                       VALUES ('ARTICLE_UPC',%s,'V6_5_3_CANONICAL_MIGRATION',%s)""",
                    (canonical_id, json.dumps({'superseded_article_upc_ids': retired_ids, 'reason': 'UPC_CANONICAL_TO_MAIN_FAMILY'}, ensure_ascii=False)),
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
            retired_qa = cur.rowcount

            cur.execute('DELETE FROM phase2c_row_state WHERE batch_id=%s', (batch_id,))
            row_states = cur.rowcount
            cur.execute('DELETE FROM phase2c_batch_result WHERE batch_id=%s', (batch_id,))
            batch_results = cur.rowcount
            cur.execute('DELETE FROM normalized_source_evidence WHERE batch_id=%s', (batch_id,))
            evidence = cur.rowcount

            cur.execute(
                """DELETE FROM uom_source_alias
                   WHERE source_system IN ('monthly_pi_form','article_manual')
                     AND UPPER(TRIM(source_uom_code)) IN ('#N/A','N/A','NA','NULL','NONE','-','--')"""
            )
            uom_aliases = cur.rowcount

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


def run(identity_batch: int, history_batch: int | None) -> dict[str, Any]:
    stage = 'START'
    report: dict[str, Any] = {
        'patch_version': PATCH_VERSION,
        'runner_file': str(Path(__file__).resolve()),
        'runner_sha256': _sha256(Path(__file__).resolve()),
        'ran_at': datetime.now().isoformat(),
        'identity_batch': identity_batch,
        'history_batch': history_batch,
    }
    try:
        stage = 'TEST_DATABASE'
        db = test_database()
        report['database'] = db.get('database')
        if not all(db.get(k) for k in ('phase1_schema_ready','phase2a_schema_ready','phase2c_schema_ready','phase3_schema_ready')):
            raise RuntimeError('Database schema is not fully ready for the v6.5.4 repair.')

        stage = 'SCHEMA_PREFLIGHT'
        preflight = schema_preflight()
        report['schema_preflight'] = preflight
        if not preflight['pass']:
            raise RuntimeError(f"Schema preflight failed before any repair mutation: {preflight['missing_columns']}")

        stage = 'BACKUP_STATE'
        backup = backup_state(identity_batch, history_batch)
        report['backup_file'] = str(backup)

        stage = 'CANONICALIZE_LEGACY_UPC_LINKS'
        report['legacy_upc_migration'] = migrate_legacy_same_family_upc_links()

        stage = 'RESET_IDENTITY_BATCH'
        report['reset'] = reset_identity_batch(identity_batch)

        stage = 'NORMALIZE_IDENTITY_BATCH'
        report['phase2c'] = normalize_batch(identity_batch)

        stage = 'AUDIT_PHASE2C'
        phase2c_audit = audit_phase2c(identity_batch)
        report['phase2c_audit'] = phase2c_audit
        if not phase2c_audit.get('pass'):
            report['stage'] = stage
            report['result'] = 'PHASE2C_STILL_QA_HOLD'
            REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=_json_default), encoding='utf-8')
            return report

        if history_batch is not None:
            stage = 'CHECK_HISTORY_BATCH'
            with db_conn() as conn:
                cur = conn.cursor(dictionary=True)
                cur.execute('SELECT processing_status FROM ingest_batch WHERE batch_id=%s', (history_batch,))
                h = cur.fetchone()
                cur.close()
            if h and h['processing_status'] in {'PHASE2C_READY','PHASE3_QA_HOLD','QUICK_CHECK_READY'}:
                stage = 'PROCESS_HISTORY_PHASE3'
                report['history_batch_phase3'] = process_phase3(history_batch)
                stage = 'AUDIT_HISTORY_PHASE3'
                report['history_batch_audit'] = audit_phase3(history_batch)
            else:
                report['history_batch_skipped'] = f'Batch {history_batch} status is not eligible for Phase 3 rerun: {h}'

        stage = 'PROCESS_IDENTITY_BATCH_PHASE3'
        report['identity_batch_phase3'] = process_phase3(identity_batch)
        stage = 'AUDIT_IDENTITY_BATCH_PHASE3'
        identity_phase3_audit = audit_phase3(identity_batch)
        report['identity_batch_phase3_audit'] = identity_phase3_audit
        report['stage'] = stage
        report['result'] = 'QUICK_CHECK_READY' if identity_phase3_audit.get('pass') else 'PHASE3_TRUE_QA_REMAINS'
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=_json_default), encoding='utf-8')
        return report
    except Exception as exc:
        report['stage'] = stage
        report['result'] = 'REPAIR_FAILED'
        report['error_type'] = type(exc).__name__
        report['error'] = repr(exc)
        report['traceback'] = traceback.format_exc()
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=_json_default), encoding='utf-8')
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description='FULL MYSQL v6.5.4 consolidated Phase2C/late-identity repair')
    ap.add_argument('--identity-batch', type=int, default=7)
    ap.add_argument('--history-batch', type=int, default=6)
    ap.add_argument('--print-version', action='store_true')
    args = ap.parse_args()

    if args.print_version:
        p = Path(__file__).resolve()
        print(json.dumps({'patch_version': PATCH_VERSION, 'runner_file': str(p), 'runner_sha256': _sha256(p)}, indent=2))
        return 0

    try:
        report = run(args.identity_batch, args.history_batch)
        print(json.dumps(report, indent=2, ensure_ascii=False, default=_json_default))
        if report['result'] in {'QUICK_CHECK_READY','PHASE3_TRUE_QA_REMAINS'}:
            return 0
        return 2
    except Exception:
        try:
            print(REPORT_PATH.read_text(encoding='utf-8'), file=sys.stderr)
        except Exception:
            pass
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
