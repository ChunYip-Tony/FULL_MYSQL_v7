from __future__ import annotations
from db import db_conn
from phase3 import _process_movement, relink_history, rebuild_quick_check
from product_identity_audit import audit_product_identity

def repair_movement_history(device: str):
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT COUNT(*) c FROM pipeline_run WHERE stage_name='POST_RAW_PIPELINE' AND processing_status='STARTED'")
            if int((cur.fetchone() or {}).get('c') or 0):
                raise RuntimeError('Server pipeline is currently processing')
            cur.execute("SELECT publish_batch_id FROM quick_check_current WHERE publish_batch_id IS NOT NULL GROUP BY publish_batch_id ORDER BY COUNT(*) DESC,publish_batch_id DESC LIMIT 1")
            r=cur.fetchone()
            if not r:
                raise RuntimeError('No published Quick Check batch')
            publish_batch_id=int(r['publish_batch_id'])
            cur.execute("SELECT COUNT(*) c FROM movement_history")
            before=int((cur.fetchone() or {}).get('c') or 0)
            cur.execute("""SELECT file_id,batch_id,original_filename,coverage_start_date,coverage_end_date,
                                  header_period_start_date,header_period_end_date,report_generated_at,
                                  upload_timestamp,filename_date_candidate
                           FROM ingest_file
                           WHERE source_type='movement' AND processing_status='INGESTED'
                             AND error_count=0 AND duplicate_of_file_id IS NULL
                           ORDER BY file_id""")
            files=cur.fetchall()
            conn.commit(); conn.start_transaction()
            results=[]
            failed_files=[]
            for f in files:
                cur.execute(
                    """SELECT COUNT(*) c FROM raw_movement
                       WHERE file_id=%s AND observed_business_date IS NOT NULL""",
                    (f['file_id'],),
                )
                dated_raw=int((cur.fetchone() or {}).get('c') or 0)
                cur.execute("SELECT COUNT(*) c FROM movement_history WHERE file_id=%s",(f['file_id'],))
                b=int((cur.fetchone() or {}).get('c') or 0)
                n=int(_process_movement(cur,int(f['batch_id']),f) or 0)
                cur.execute("SELECT COUNT(*) c FROM movement_history WHERE file_id=%s",(f['file_id'],))
                a=int((cur.fetchone() or {}).get('c') or 0)
                item={
                    'file_id':int(f['file_id']),
                    'filename':f['original_filename'],
                    'dated_raw_rows':dated_raw,
                    'before':b,
                    'after':a,
                    'processed':n,
                }
                results.append(item)
                if dated_raw>0 and a<=0:
                    failed_files.append(item)
            if failed_files:
                raise RuntimeError(
                    'Movement history repair left dated RAW files without normalized history: '
                    + str(failed_files)
                )
            relink_history(cur)
            qc=rebuild_quick_check(cur,publish_batch_id)
            audit=audit_product_identity(cur)
            if not bool(audit.get('pass')):
                raise RuntimeError('Product identity audit blocked movement history repair')
            cur.execute("SELECT COUNT(*) c FROM movement_history")
            after=int((cur.fetchone() or {}).get('c') or 0)
            if after<=0:
                raise RuntimeError('Movement history remains empty')
            conn.commit()
            return {'status':'COMMITTED','device':device,'publish_batch_id':publish_batch_id,
                    'rows_before':before,'rows_after':after,'rows_added':after-before,
                    'files':results,'quick_check':qc,'identity_summary':audit.get('summary')}
        except Exception:
            conn.rollback(); raise
        finally:
            cur.close()
