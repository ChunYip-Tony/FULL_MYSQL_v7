"""Time-limited authenticated, read-only export for the authorized Sites migration.

All tables are read in ONE repeatable-read snapshot. A reader must reject an
interrupted stream without its final complete record. Runtime credentials,
sessions, unknown tables and oversized rebuilt caches are never exported.
"""
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
import base64
import hashlib
import hmac
import json
import time
import zlib

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from db import db_conn

AUTH_SHA256 = "ba12f002c079d33ed65db2260b03d5854615edd871a54b4333903f8668b2d970"
EXPIRES_AT = "2026-10-27T00:00:00+00:00"
TABLES = frozenset('''ingest_batch ingest_file ingest_sheet ingest_column ingest_error
raw_movement raw_price_list raw_sales_by_price_type raw_on_hand raw_frozen_inventory
raw_tx_seafood_abc_price raw_live_fresh_suggestion raw_article_manual raw_monthly_pi_form raw_unclassified
dim_uom uom_source_alias product_family article selling_upc bridge_article_family bridge_article_upc
normalized_source_evidence article_uom_role_history selling_upc_uom_history uom_conversion_observation
article_uom_conversion article_department_observation upc_department_observation
sales_period_observation price_list_observation movement_history family_movement_observation
inventory_observation company_price_observation article_cost_observation receiving_observation
pos_daily_backfill_coverage pos_daily_backfill_observation pos_period_residual_observation
manual_upc_override manual_family_cost_authority manual_article_family_override manual_cost_selling_conversion
manual_upc_retirement manual_upc_selling_status manual_true_stock true_stock_record_clearance
dumping_discrepancy_queue qa_pending_confirmation qa_manual_resolution ordering_policy order_draft
order_draft_line price_change_proposal backoffice_price_suggestion_acceptance yipman_tpr_purpose
yipman_freshness_tpr_anchor yipman_clearance_plan yipman_promotion_list yipman_promotion_list_item
pipeline_run qa_identity_uom_issue qa_phase3_issue phase2c_row_state phase2c_batch_result
phase3_batch_result quick_check_current'''.split())

def authorize(header, now=None):
    now = now or datetime.now(timezone.utc)
    if now >= datetime.fromisoformat(EXPIRES_AT):
        raise HTTPException(410, 'Migration export window has ended')
    token = str(header or '')
    if not token.startswith('Bearer ') or len(token) > 256:
        raise HTTPException(401, 'Authorized migration access required')
    digest = hashlib.sha256(token[7:].encode()).hexdigest()
    if not hmac.compare_digest(digest, AUTH_SHA256):
        raise HTTPException(401, 'Authorized migration access required')

def scalar(value):
    if isinstance(value, Decimal):return {'$decimal': str(value)}
    if isinstance(value, (datetime, date)):return {'$datetime': value.isoformat()}
    if isinstance(value, timedelta):return {'$timedelta_seconds': str(value.total_seconds())}
    if isinstance(value, (bytes, bytearray)):return {'$binary': base64.b64encode(value).decode()}
    return value

def line(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False,default=scalar).encode()+b'\n'

def snapshot_lines(connect=db_conn, frozen_proof=None, verify_freeze=None):
    counts={};started=datetime.now(timezone.utc).isoformat()
    with connect(read_timeout=60,connection_timeout=10) as conn:
        conn.start_transaction(isolation_level='REPEATABLE READ',consistent_snapshot=True,readonly=True)
        cur=conn.cursor(dictionary=True,buffered=True)
        try:
            cur.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()')
            present={r['TABLE_NAME'] for r in cur.fetchall()} & TABLES
            freeze_metadata={'freeze_proof':frozen_proof} if frozen_proof else {}
            yield line({'kind':'begin','contract':'SEAFOOD_MYSQL_SNAPSHOT_V1','started_at':started,'tables':sorted(present),'missing_optional_tables':sorted(TABLES-present),'transaction':'REPEATABLE_READ_READ_ONLY',**freeze_metadata})
            for table in sorted(present):
                cur.execute('SELECT COLUMN_NAME,DATA_TYPE,COLUMN_TYPE,IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION',(table,))
                columns=cur.fetchall();names=[c['COLUMN_NAME'] for c in columns]
                cur.execute("SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND CONSTRAINT_NAME='PRIMARY' ORDER BY ORDINAL_POSITION",(table,))
                keys=[r['COLUMN_NAME'] for r in cur.fetchall()]
                if not keys:raise RuntimeError('Migration table has no primary key: '+table)
                cur.execute('SELECT COUNT(*) AS n FROM `'+table+'`');expected=int(cur.fetchone()['n'])
                yield line({'kind':'table','table':table,'columns':columns,'primary_key':keys,'expected_rows':expected})
                data=conn.cursor(buffered=False);count=0;digest=hashlib.sha256()
                try:
                    data.execute('SELECT * FROM `'+table+'` ORDER BY '+','.join('`'+k.replace('`','``')+'`' for k in keys))
                    while True:
                        rows=data.fetchmany(100)
                        if not rows:break
                        for row in rows:
                            encoded=line(list(row));digest.update(encoded);count+=1
                        yield line({'kind':'rows','table':table,'first':count-len(rows)+1,'rows':rows})
                finally:data.close()
                if count!=expected:raise RuntimeError('Snapshot count mismatch: '+table)
                counts[table]=count
                yield line({'kind':'table_complete','table':table,'rows':count,'sha256':digest.hexdigest()})
            if verify_freeze:
                after=verify_freeze()
                if any(after.get(k)!=frozen_proof.get(k) for k in ['cutoverId','backupSha256','frozenAt','businessWritesDenied','legacyConnectionsDrained']):raise RuntimeError('Freeze identity changed during export')
                freeze_metadata={'freeze_proof':after}
            yield line({'kind':'complete','contract':'SEAFOOD_MYSQL_SNAPSHOT_V1','started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'tables':len(counts),'rows':sum(counts.values()),'counts':counts,**freeze_metadata})
        finally:
            cur.close();conn.rollback()

def gzip_stream(lines):
    compressor=zlib.compressobj(level=3,wbits=31)
    for record in lines:
        yield compressor.compress(record)+compressor.flush(zlib.Z_SYNC_FLUSH)
    yield compressor.flush(zlib.Z_FINISH)

def install_sites_migration_export(app):
    @app.post('/v1/migration/sites/cutover')
    async def cutover(request:Request):
        from sites_sql_cutover import authorize as cutover_authorize, control_action, identity
        from fastapi.responses import JSONResponse
        from starlette.concurrency import run_in_threadpool
        authorization=request.headers.get('authorization')
        # Authenticate before reading the bounded body. Recheck the exact
        # parsed action so the grace window permits only read-only verification.
        cutover_authorize(authorization,action='verify')
        if len(await request.body())>2048:raise HTTPException(413,'Cutover request too large')
        try:
            body=await request.json();action=body.get('action');cutover_id=identity(body.get('cutoverId'))
            if set(body)-{'action','cutoverId','rollbackPassword','backupSha256'}:raise ValueError('Unknown cutover parameters')
            cutover_authorize(authorization,action=action)
            if action=='frozen-snapshot':
                proof=await run_in_threadpool(control_action,'verify',cutover_id)
                return StreamingResponse(gzip_stream(snapshot_lines(frozen_proof=proof,verify_freeze=lambda:control_action('verify',cutover_id))),media_type='application/gzip',headers={'Cache-Control':'no-store','X-Migration-Contract':'SEAFOOD_MYSQL_SNAPSHOT_V1'})
            result=await run_in_threadpool(control_action,action,cutover_id,body.get('rollbackPassword'),body.get('backupSha256'))
            return JSONResponse(result,headers={'Cache-Control':'no-store'})
        except ValueError as error:raise HTTPException(409,str(error)) from None
        except HTTPException:raise
        except Exception as error:raise HTTPException(503,{'message':'Cutover operation did not complete; inspect retained state before retry','databaseErrorCode':getattr(error,'errno',None)}) from None

    @app.get('/v1/migration/sites/writer-audit')
    def audit_writers(request:Request):
        authorize(request.headers.get('authorization'))
        from migration_writer_audit import writer_inventory
        from fastapi.responses import JSONResponse
        return JSONResponse(writer_inventory(db_conn, TABLES), headers={'Cache-Control':'no-store'})

    @app.get('/v1/migration/sites/snapshot')
    def export(request:Request):
        authorize(request.headers.get('authorization'))
        return StreamingResponse(gzip_stream(snapshot_lines()),media_type='application/gzip',headers={
            'Cache-Control':'no-store','Content-Disposition':'attachment; filename="seafood-mysql-snapshot.ndjson.gz"',
            'X-Migration-Contract':'SEAFOOD_MYSQL_SNAPSHOT_V1'})

