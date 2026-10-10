"""Stock-count review and compact, verified publication evidence for Data Center."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from decimal import Decimal

from db import db_conn
from quick_check_app import _table_exists, _refresh_expired_true_stock, _actual_position

_schema_ready = False
_schema_lock = threading.Lock()


def _ensure_clearance_table(cur):
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        cur.execute("""CREATE TABLE IF NOT EXISTS true_stock_record_clearance (
            true_stock_id BIGINT UNSIGNED NOT NULL,
            cleared_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            cleared_by VARCHAR(128) NOT NULL,
            clear_note VARCHAR(255) NULL,
            PRIMARY KEY (true_stock_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")
        _schema_ready = True


def record_state(row):
    status = row.get('override_status')
    if status == 'SUPERSEDED_BY_OH_UPLOAD':
        return 'REPLACED_BY_OH'
    if status != 'ACTIVE':
        return 'CANCELLED' if str(status or '').startswith('CANCELLED') else 'REPLACED_BY_COUNT'
    if row.get('cleared_at') or row.get('queue_status') == 'RESOLVED':
        return 'CLEARED'
    return 'PENDING_DUMPING' if row.get('queue_status') == 'PENDING' else 'RECORDED'


_JOINS = """FROM manual_true_stock m
    LEFT JOIN product_family pf ON pf.family_id=m.family_id
    LEFT JOIN true_stock_record_clearance c ON c.true_stock_id=m.true_stock_id
    LEFT JOIN dumping_discrepancy_queue d ON d.discrepancy_id=(
        SELECT MAX(q.discrepancy_id) FROM dumping_discrepancy_queue q
        WHERE q.source_true_stock_id=m.true_stock_id)
"""
_PENDING = "(m.override_status='ACTIVE' AND c.true_stock_id IS NULL AND COALESCE(d.queue_status,'')<>'RESOLVED')"


def list_stock_records(view='pending', limit=100, before=None, query='', kind='all'):
    if view not in {'pending', 'history', 'all'} or kind not in {'all', 'zero', 'count'}:
        raise ValueError('INVALID_RECORD_FILTER')
    limit = max(1, min(int(limit), 200))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            _ensure_clearance_table(cur)
            conn.commit()
            if not _table_exists(cur, 'manual_true_stock'):
                return {'rows': [], 'counts': {}, 'total': 0, 'next_before': None, 'latest_oh': None}
            latest = _refresh_expired_true_stock(cur)
            cur.execute("SELECT file_id,original_filename,upload_timestamp,coverage_end_date FROM ingest_file WHERE file_id=%s", (latest,))
            latest_oh = cur.fetchone() if latest else None
            cur.execute(f"""SELECT COUNT(*) AS total,
                COALESCE(SUM({_PENDING}),0) AS pending,
                COALESCE(SUM({_PENDING} AND m.true_stock_quantity=0),0) AS zero_pending,
                COALESCE(SUM({_PENDING} AND d.queue_status='PENDING'),0) AS dumping_pending
                {_JOINS}""")
            counts = {k: int(v or 0) for k, v in (cur.fetchone() or {}).items()}
            counts['history'] = counts.get('total', 0) - counts.get('pending', 0)
            filters, params = [], []
            if view == 'pending': filters.append(_PENDING)
            elif view == 'history': filters.append('NOT '+_PENDING)
            if kind == 'zero': filters.append('m.true_stock_quantity=0')
            elif kind == 'count': filters.append('m.true_stock_quantity<>0')
            if query.strip():
                pattern = '%'+query.strip()[:100]+'%'
                filters.append("(pf.family_description LIKE %s OR m.main_article_number LIKE %s OR m.article_number LIKE %s OR m.ean_upc LIKE %s)")
                params.extend([pattern]*4)
            where = ' AND '.join(filters) or '1=1'
            cur.execute(f'SELECT COUNT(*) AS total {_JOINS} WHERE {where}', tuple(params))
            total = int((cur.fetchone() or {}).get('total') or 0)
            if before is not None:
                where += ' AND m.true_stock_id<%s'
                params.append(int(before))
            cur.execute(f"""SELECT m.true_stock_id,m.family_id,m.main_article_number,
                pf.family_description AS item_name,m.scope_type,m.article_id,m.upc_id,m.article_number,m.ean_upc,
                m.true_stock_quantity,m.uom_code,m.system_oh_quantity,m.discrepancy_quantity,
                m.override_status,m.submitted_at,m.count_note,m.submitted_by,
                m.superseded_at,m.superseded_by_oh_file_id,
                c.cleared_at,c.cleared_by,c.clear_note,
                d.discrepancy_id,d.queue_status,d.resolved_at,d.resolution_note
                {_JOINS} WHERE {where}
                ORDER BY m.true_stock_id DESC LIMIT %s""", (*params, limit+1))
            fetched = cur.fetchall()
            rows = fetched[:limit]
            for row in rows:
                row['record_status'] = record_state(row)
                row['is_zero'] = Decimal(str(row['true_stock_quantity'])) == 0
                row['dumping_quantity'] = max(Decimal('0'), Decimal(str(row.get('discrepancy_quantity') or 0)))
                row['can_clear'] = row['record_status'] in {'PENDING_DUMPING', 'RECORDED'}
                row['cleared_at'] = row.get('cleared_at') or (row.get('resolved_at') if row.get('queue_status') == 'RESOLVED' else None)
                # Use the same canonical-MVT rollforward as Quick Check and item
                # cards. Cleared review tasks retain their ACTIVE stock anchor;
                # replaced/cancelled anchors must never look like current stock.
                row['effective_stock'] = (
                    _actual_position(cur, row) if row['override_status'] == 'ACTIVE' else None
                )
            conn.commit()
            return {'rows': rows, 'counts': counts, 'total': total, 'latest_oh': latest_oh,
                    'next_before': rows[-1]['true_stock_id'] if len(fetched)>limit else None,
                    'checked_at': datetime.now(timezone.utc).isoformat()}
        finally:
            cur.close()


def clear_stock_record(true_stock_id, actor, note=None):
    """Clear only the review record and its dumping task; retain stock authority."""
    rid = int(true_stock_id)
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            _ensure_clearance_table(cur)
            conn.commit()
            conn.start_transaction()
            _refresh_expired_true_stock(cur)
            cur.execute('SELECT true_stock_id,override_status FROM manual_true_stock WHERE true_stock_id=%s FOR UPDATE', (rid,))
            row = cur.fetchone()
            if not row:
                raise KeyError('STOCK_RECORD_NOT_FOUND')
            if row['override_status'] != 'ACTIVE':
                raise ValueError('STOCK_RECORD_ALREADY_REPLACED')
            cur.execute('SELECT true_stock_id FROM true_stock_record_clearance WHERE true_stock_id=%s', (rid,))
            if cur.fetchone():
                conn.commit()
                return {'status': 'ALREADY_CLEARED', 'true_stock_id': rid, 'inventory_mutated': False}
            clean_note = str(note or '').strip()[:255] or None
            cur.execute("""UPDATE dumping_discrepancy_queue SET queue_status='RESOLVED',
                resolved_at=CURRENT_TIMESTAMP(6),resolved_by=%s,resolution_note=%s
                WHERE source_true_stock_id=%s AND queue_status='PENDING'""", (actor, clean_note, rid))
            cur.execute('INSERT INTO true_stock_record_clearance (true_stock_id,cleared_by,clear_note) VALUES (%s,%s,%s)', (rid, actor, clean_note))
            conn.commit()
            return {'status': 'CLEARED', 'true_stock_id': rid, 'inventory_mutated': False,
                    'true_stock_mutated': False, 'effective_oh_retained': True}
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def _publish_summary(row):
    if not row:
        return None
    detail = row.get('detail_json') or {}
    if isinstance(detail, str):
        try: detail = json.loads(detail)
        except (TypeError, ValueError): detail = {}
    result = detail.get('publish_result') or {}
    readback = result.get('readback') or {}
    source = readback.get('source_status') or {}
    verified = row['processing_status']=='COMPLETED' and result.get('status')=='PASS' and readback.get('pass') is True
    return {'batch_id': row['batch_id'], 'publish_run_id': row['pipeline_run_id'],
            'status': row['processing_status'], 'verified': verified, 'completed_at': row.get('completed_at'),
            'ready_rows': result.get('analysis_ready_row_count'), 'held_rows': result.get('excluded_hold_row_count'),
            'pos_through': source.get('POS_Data_Through'), 'mvt_through': source.get('Movement_Data_Through'),
            'pos_file': source.get('POS_Canonical_Source'), 'mvt_file': source.get('Canonical_Movement_Source')}


def latest_verified_publish(pipeline_name):
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            columns = 'pipeline_run_id,batch_id,processing_status,completed_at,detail_json'
            base = "FROM pipeline_run WHERE pipeline_name=%s AND stage_name='CHATGPT_SHEET_PUBLISH'"
            cur.execute(f"SELECT {columns} {base} ORDER BY pipeline_run_id DESC LIMIT 1", (pipeline_name,))
            attempt = _publish_summary(cur.fetchone())
            cur.execute(f"""SELECT {columns} {base} AND processing_status='COMPLETED'
                AND JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.publish_result.status'))='PASS'
                AND JSON_EXTRACT(detail_json,'$.publish_result.readback.pass')=true
                ORDER BY completed_at DESC,pipeline_run_id DESC LIMIT 1""", (pipeline_name,))
            published = _publish_summary(cur.fetchone())
            if published and published['verified']:
                cur.execute("""SELECT original_filename,source_type,coverage_start_date,coverage_end_date
                    FROM ingest_file WHERE batch_id=%s AND processing_status='INGESTED'
                    AND COALESCE(error_count,0)=0 AND duplicate_of_file_id IS NULL ORDER BY file_id""", (published['batch_id'],))
                published['files'] = cur.fetchall()
            else:
                published = None
            return {'published': published, 'latest_attempt': attempt, 'checked_at': datetime.now(timezone.utc).isoformat()}
        finally:
            cur.close()
