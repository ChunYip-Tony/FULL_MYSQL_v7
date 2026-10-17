"""Durable user confirmations independent of a long Phase-3 write transaction."""
from __future__ import annotations
import json
from decimal import Decimal, InvalidOperation
from db import db_conn


def ensure_pending_table(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS qa_pending_confirmation (
        ean_upc VARCHAR(32) NOT NULL PRIMARY KEY,
        article_number VARCHAR(32) NOT NULL,
        selling_uom VARCHAR(32) NOT NULL,
        base_uom VARCHAR(32) NOT NULL,
        base_qty_per_selling_unit DECIMAL(24,12) NOT NULL,
        note VARCHAR(512) NOT NULL,
        actor VARCHAR(128) NOT NULL,
        status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        applied_at DATETIME(6) NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")


def pending_confirmations(cur, lock=False):
    cur.execute("""SELECT 1 FROM information_schema.tables WHERE table_schema=DATABASE()
                   AND table_name='qa_pending_confirmation' LIMIT 1""")
    if not cur.fetchone():
        return []
    cur.execute("SELECT * FROM qa_pending_confirmation WHERE status='PENDING' ORDER BY ean_upc" +
                (' FOR UPDATE' if lock else ''))
    return cur.fetchall()


def queue_confirmation(*, ean_upc, article_number, selling_uom, base_uom,
                       base_qty_per_selling_unit, note, actor, confirm):
    if confirm != 'QUEUE_CONFIRMED_QA_FIX':
        raise ValueError('CONFIRM_MUST_BE_QUEUE_CONFIRMED_QA_FIX')
    values=[str(x or '').strip() for x in (ean_upc,article_number,selling_uom,base_uom,note)]
    if not all(values):
        raise ValueError('UPC_ARTICLE_UNITS_AND_NOTE_REQUIRED')
    ean,article,sell,base,reason=values
    sell,base=sell.upper(),base.upper()
    try:
        factor=Decimal(str(base_qty_per_selling_unit))
    except (InvalidOperation,ValueError):
        raise ValueError('BASE_QUANTITY_INVALID')
    if not factor.is_finite() or factor<=0:
        raise ValueError('BASE_QUANTITY_MUST_BE_FINITE_AND_POSITIVE')
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        ensure_pending_table(cur)
        # Validate against retained reference records without locking business rows.
        for unit in (sell,base):
            cur.execute('SELECT uom_code FROM dim_uom WHERE UPPER(uom_code)=%s LIMIT 1',(unit,))
            if not cur.fetchone():raise ValueError('UOM_NOT_FOUND:'+unit)
        cur.execute('SELECT article_id FROM article WHERE article_number=%s LIMIT 1',(article,))
        if not cur.fetchone():raise ValueError('ARTICLE_NOT_FOUND')
        cur.execute('SELECT upc_id FROM selling_upc WHERE ean_upc=%s LIMIT 1',(ean,))
        if not cur.fetchone():raise ValueError('UPC_NOT_FOUND')
        cur.execute("""INSERT INTO qa_pending_confirmation
                       (ean_upc,article_number,selling_uom,base_uom,base_qty_per_selling_unit,note,actor,status)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDING') ON DUPLICATE KEY UPDATE
                       article_number=VALUES(article_number),selling_uom=VALUES(selling_uom),
                       base_uom=VALUES(base_uom),base_qty_per_selling_unit=VALUES(base_qty_per_selling_unit),
                       note=VALUES(note),actor=VALUES(actor),status='PENDING',applied_at=NULL""",
                    (ean,article,sell,base,factor,reason[:512],str(actor)[:128]))
        conn.commit();cur.close()
    return {'status':'QUEUED','ean_upc':ean,'article_number':article,'selling_uom':sell,
            'base_uom':base,'base_qty_per_selling_unit':str(factor),
            'application_stage':'PHASE3_FINAL_CONFIRMED_QA',
            'raw_source_rows_modified':False}


def apply_pending_confirmations(cur,batch_id):
    # A locking read sees confirmations committed after this rebuild began.
    rows=pending_confirmations(cur,lock=True)
    if not rows:return {'applied':0}
    from manual_overrides import apply_manual_upc_overrides
    from phase3 import relink_history,refresh_quick_check_subset
    from qa_resolution import _ensure_resolution_table
    # Tables are provisioned before the Phase-3 transaction, never DDL here.
    for r in rows:
        cur.execute("""INSERT INTO manual_upc_override
                       (ean_upc,article_number,selling_uom_code,base_uom_code,
                        base_qty_per_selling_unit,override_status,source_note)
                       VALUES (%s,%s,%s,%s,%s,'CONFIRMED',%s) ON DUPLICATE KEY UPDATE
                       article_number=VALUES(article_number),selling_uom_code=VALUES(selling_uom_code),
                       base_uom_code=VALUES(base_uom_code),base_qty_per_selling_unit=VALUES(base_qty_per_selling_unit),
                       override_status='CONFIRMED',source_note=VALUES(source_note)""",
                    (r['ean_upc'],r['article_number'],r['selling_uom'],r['base_uom'],
                     r['base_qty_per_selling_unit'],('BACKOFFICE_QA_USER_CONFIRMED: '+r['note'])[:512]))
    result=apply_manual_upc_overrides(cur)
    targets={str(r['ean_upc']) for r in rows}
    if any(str(r.get('ean_upc')) in targets for r in result.get('held',[])):
        raise RuntimeError('QUEUED_CONFIRMATION_FAILED_AUTHORITY_VALIDATION')
    relink_history(cur)
    refresh_quick_check_subset(cur,batch_id,upcs=sorted(targets))
    for r in rows:
        after={k:str(r[k]) for k in ['ean_upc','article_number','selling_uom','base_uom','base_qty_per_selling_unit']}
        cur.execute("""INSERT INTO qa_manual_resolution
                       (batch_id,issue_code,entity_type,entity_key,resolution_kind,actor,
                        resolution_note,applied_json,after_json)
                       VALUES (%s,'QUEUED_CONFIRMED_QA_FIX','UPC',%s,
                               'USER_CONFIRMED_IDENTITY_UOM_OVERRIDE',%s,%s,%s,%s)""",
                    (batch_id,r['ean_upc'],r['actor'],r['note'],json.dumps(after),json.dumps(after)))
        cur.execute("""UPDATE qa_pending_confirmation SET status='APPLIED',applied_at=CURRENT_TIMESTAMP(6)
                       WHERE ean_upc=%s""",(r['ean_upc'],))
    return {'applied':len(rows),'upcs':sorted(targets)}
