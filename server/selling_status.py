"""Reversible current-selling authority; never deletes source or sales history."""
from __future__ import annotations
import json
from db import db_conn


def selling_status_rows(cur):
    cur.execute("""SELECT 1 FROM information_schema.tables
                   WHERE table_schema=DATABASE() AND table_name='manual_upc_selling_status' LIMIT 1""")
    if not cur.fetchone():
        return []
    cur.execute("""SELECT ean_upc,selling_status,source_note,actor,updated_at
                   FROM manual_upc_selling_status ORDER BY ean_upc""")
    return cur.fetchall()


def confirmed_inactive_upcs(cur):
    return {str(r['ean_upc']) for r in selling_status_rows(cur)
            if r['selling_status'] == 'INACTIVE'}


def set_selling_status(*, ean_upc, selling_status, note, actor, confirm):
    if confirm != 'APPLY_SELLING_STATUS':
        raise ValueError('CONFIRM_MUST_BE_APPLY_SELLING_STATUS')
    ean = str(ean_upc or '').strip()
    status = str(selling_status or '').strip().upper()
    reason = str(note or '').strip()
    if not ean:
        raise ValueError('EAN_UPC_REQUIRED')
    if status not in {'ACTIVE', 'INACTIVE'}:
        raise ValueError('SELLING_STATUS_MUST_BE_ACTIVE_OR_INACTIVE')
    if not reason:
        raise ValueError('CONFIRMATION_NOTE_REQUIRED')
    # Imports are lazy: Phase 3 reads this module while qa_resolution imports Phase 3.
    from qa_resolution import _ensure_resolution_table, _latest_phase3_batch
    from phase3 import refresh_quick_check_subset
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("""CREATE TABLE IF NOT EXISTS manual_upc_selling_status (
            ean_upc VARCHAR(32) NOT NULL PRIMARY KEY,
            selling_status VARCHAR(24) NOT NULL,
            source_note VARCHAR(512) NOT NULL,
            actor VARCHAR(128) NOT NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ON UPDATE CURRENT_TIMESTAMP(6)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")
        _ensure_resolution_table(cur)
        conn.commit()
        cur.execute("""SELECT 1 FROM pipeline_run WHERE processing_status='STARTED'
                       AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN') LIMIT 1""")
        pipeline_busy = bool(cur.fetchone())
        if pipeline_busy and status == 'ACTIVE':
            raise RuntimeError('PIPELINE_BUSY_RETRY_AFTER_ACTIVE_BATCH_FINISHES')
        cur.execute('SELECT upc_id,ean_upc,record_status FROM selling_upc WHERE ean_upc=%s LIMIT 1', (ean,))
        identity = cur.fetchone()
        if not identity:
            raise ValueError('UPC_NOT_FOUND')
        if identity.get('record_status') == 'RETIRED':
            raise ValueError('RETIRED_IDENTIFIER_REQUIRES_IDENTITY_REVIEW')
        cur.execute('SELECT * FROM manual_upc_selling_status WHERE ean_upc=%s LIMIT 1', (ean,))
        before = cur.fetchone()
        batch_id = _latest_phase3_batch(cur)
        conn.commit()
        conn.start_transaction()
        try:
            cur.execute("""INSERT INTO manual_upc_selling_status (ean_upc,selling_status,source_note,actor)
                           VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE
                           selling_status=VALUES(selling_status),source_note=VALUES(source_note),actor=VALUES(actor)""",
                        (ean,status,reason[:512],str(actor)[:128]))
            if status == 'INACTIVE' and not pipeline_busy:
                # Keep every metric/identity/history field; only current readiness changes.
                cur.execute("""UPDATE quick_check_current SET quick_check_status='HISTORICAL_ONLY',
                               blocking_reason=NULL,published_at=CURRENT_TIMESTAMP(6) WHERE ean_upc=%s""", (ean,))
                cur.execute("""UPDATE qa_phase3_issue SET issue_status='RESOLVED',
                               detail_json=JSON_SET(COALESCE(detail_json,JSON_OBJECT()),
                                 '$.manual_selling_status',CAST(%s AS JSON))
                               WHERE entity_type='UPC' AND entity_key=%s AND issue_status='OPEN'""",
                            (json.dumps({'selling_status':status,'actor':actor,'note':reason[:512]}),ean))
            elif status == 'INACTIVE':
                # Save authority independently of the long rebuild transaction.
                # QA review respects it immediately; the rebuild reapplies it before analysis.
                pass
            elif batch_id is not None:
                refresh_quick_check_subset(cur,batch_id,upcs=[ean])
            else:
                raise RuntimeError('NO_PHASE3_BATCH_AVAILABLE_FOR_TARGETED_REFRESH')
            after = {'ean_upc':ean,'selling_status':status,'note':reason[:512]}
            cur.execute("""INSERT INTO qa_manual_resolution
                           (batch_id,issue_code,entity_type,entity_key,resolution_kind,actor,
                            resolution_note,before_json,applied_json,after_json)
                           VALUES (%s,'CURRENT_SELLING_STATUS','UPC',%s,'USER_CONFIRMED_SELLING_STATUS',
                                   %s,%s,%s,%s,%s)""",
                        (batch_id,ean,actor,reason[:512],json.dumps(before,default=str),
                         json.dumps(after),json.dumps(after)))
            resolution_id = int(cur.lastrowid)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    return {'status':'APPLIED','resolution_id':resolution_id,**after,
            'rules':{'raw_source_rows_modified':False,'historical_sales_preserved':True,
                     'identity_preserved':True,'reversible':True,
                     'readiness_refresh_pending':pipeline_busy}}


def apply_inactive_current_scope(cur):
    """Current-read writes apply confirmations saved during a long rebuild."""
    cur.execute("""SELECT 1 FROM information_schema.tables WHERE table_schema=DATABASE()
                   AND table_name='manual_upc_selling_status' LIMIT 1""")
    if not cur.fetchone():
        return
    cur.execute("""UPDATE quick_check_current q JOIN manual_upc_selling_status m
                   ON m.ean_upc=q.ean_upc AND m.selling_status='INACTIVE'
                   SET q.quick_check_status='HISTORICAL_ONLY',q.blocking_reason=NULL""")
    cur.execute("""UPDATE qa_phase3_issue q JOIN manual_upc_selling_status m
                   ON q.entity_type='UPC' AND m.ean_upc=q.entity_key AND m.selling_status='INACTIVE'
                   SET q.issue_status='RESOLVED',q.detail_json=JSON_SET(
                       COALESCE(q.detail_json,JSON_OBJECT()),'$.activity_basis','USER_CONFIRMED_NOT_CURRENTLY_SOLD')
                   WHERE q.issue_status='OPEN'""")
