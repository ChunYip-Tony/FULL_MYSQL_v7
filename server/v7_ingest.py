from __future__ import annotations
import hashlib, json, uuid
from datetime import date, datetime
from typing import Any

from db import db_conn
from ingest import parse_file, RAW_TABLE_BY_SOURCE, _excel_col, _jsonable, _cell_text

API_PIPELINE='FULLMYSQL_SECURE_API'
API_VERSION='7.0.138-single-service'
ACTIVE_UPLOAD='API_UPLOADING'


def _json_dump(v):
    return json.dumps(v, ensure_ascii=False, default=str)

def _wire_value(v):
    # datetime.isoformat accepts sep=; date.isoformat does not.
    # Keep SQL-style spacing for datetimes and ISO YYYY-MM-DD for dates.
    if isinstance(v, datetime):
        return v.isoformat(sep=' ')
    if isinstance(v, date):
        return v.isoformat()
    return v

def _notes(device_id: str, state: str, **extra):
    return _json_dump({'v7':True,'device_id':device_id,'state':state,**extra})

def _device_from_notes(text: str|None) -> str|None:
    if not text: return None
    try: return json.loads(text).get('device_id')
    except Exception: return None

def find_active_batch() -> dict[str,Any]|None:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("""
            SELECT ib.batch_id,ib.batch_key,ib.batch_label,ib.processing_status,ib.upload_started_at,ib.completed_at,ib.notes
            FROM ingest_batch ib
            WHERE ib.processing_status='API_UPLOADING'
               OR EXISTS (
                    SELECT 1 FROM pipeline_run pr
                    WHERE pr.batch_id=ib.batch_id AND pr.pipeline_name=%s
                      AND pr.stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                      AND pr.processing_status IN ('QUEUED','STARTED')
               )
            ORDER BY ib.batch_id DESC LIMIT 1
        """,(API_PIPELINE,))
        row=cur.fetchone(); cur.close()
    if row:
        row['device_id']=_device_from_notes(row.get('notes'))
        for k,v in list(row.items()):
            if isinstance(v,(date,datetime)): row[k]=_wire_value(v)
    return row

def begin_batch(device_id: str, label: str|None=None) -> dict[str,Any]:
    active=find_active_batch()
    if active:
        return {'created':False,'active':active}
    batch_key=str(uuid.uuid4())
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute("""INSERT INTO ingest_batch
                (batch_key,batch_label,processing_status,file_count,source_row_count,error_count,notes)
                VALUES (%s,%s,'API_UPLOADING',0,0,0,%s)""",
                (batch_key,label or f'Seafood API upload - {device_id}',_notes(device_id,'UPLOADING')))
            batch_id=int(cur.lastrowid)
            cur.execute("""INSERT INTO pipeline_run
                (batch_id,pipeline_name,stage_name,run_number,processing_status,code_version,detail_json)
                VALUES (%s,%s,'RAW_INGEST',1,'STARTED',%s,%s)""",
                (batch_id,API_PIPELINE,API_VERSION,_json_dump({'device_id':device_id,'transport':'HTTPS'})))
            conn.commit()
            return {'created':True,'batch_id':batch_id,'session_id':batch_key,'device_id':device_id}
        except Exception:
            conn.rollback(); raise
        finally: cur.close()

def _session(cur, session_id: str, lock: bool=False):
    sql="SELECT batch_id,batch_key,processing_status,notes FROM ingest_batch WHERE batch_key=%s"
    if lock: sql += ' FOR UPDATE'
    cur.execute(sql,(session_id,)); row=cur.fetchone()
    if not row: raise KeyError('Upload session not found')
    return row

def add_file(session_id: str, device_id: str, filename: str, data: bytes) -> dict[str,Any]:
    p=parse_file(filename,data)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            b=_session(cur,session_id,lock=True)
            if b['processing_status']!='API_UPLOADING': raise RuntimeError(f"Session is not accepting files: {b['processing_status']}")
            owner=_device_from_notes(b.get('notes'))
            if owner and owner!=device_id: raise PermissionError('This upload session belongs to another device.')
            batch_id=int(b['batch_id'])
            cur.execute("SELECT file_id,processing_status,source_row_count FROM ingest_file WHERE batch_id=%s AND file_sha256=%s ORDER BY file_id LIMIT 1",(batch_id,p.sha256))
            same=cur.fetchone()
            if same:
                conn.commit(); return {'batch_id':batch_id,'session_id':session_id,'idempotent':True,'file_id':int(same['file_id']),
                                       'filename':filename,'sha256':p.sha256,'status':same['processing_status'],'raw_rows_inserted':int(same['source_row_count'] or 0)}
            cur.execute("SELECT file_id FROM ingest_file WHERE file_sha256=%s ORDER BY file_id LIMIT 1",(p.sha256,)); dup=cur.fetchone()
            duplicate_of=int(dup['file_id']) if dup else None
            cur.execute("""INSERT INTO ingest_file (
                batch_id,original_filename,declared_extension,detected_format,source_type,source_type_confidence,file_size_bytes,file_sha256,
                duplicate_of_file_id,sheet_count,source_row_count,coverage_type,coverage_start_date,coverage_end_date,header_period_start_date,
                header_period_end_date,header_period_text,filename_date_candidate,filename_time_candidate,report_generated_at,date_semantics_status,
                date_evidence_json,processing_status,error_count)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PARSING',0)""",
                (batch_id,p.filename,p.filename.rsplit('.',1)[-1].lower() if '.' in p.filename else None,p.detected_format,p.source_type,p.source_type_confidence,
                 p.size_bytes,p.sha256,duplicate_of,len(p.sheets),p.coverage_type,p.coverage_start,p.coverage_end,p.header_period_start,p.header_period_end,
                 p.header_period_text,p.filename_date_candidate,p.filename_time_candidate,p.report_generated_at,p.date_semantics_status,_json_dump(p.date_evidence)))
            file_id=int(cur.lastrowid); raw_count=0; total_rows=sum(len(sh.rows) for sh in p.sheets); raw_table=RAW_TABLE_BY_SOURCE[p.source_type]
            for sh in p.sheets:
                col_count=max((len(r) for r in sh.rows), default=0)
                cur.execute("""INSERT INTO ingest_sheet
                    (file_id,sheet_index,sheet_name,sheet_visibility,row_count,column_count,header_row_number,coverage_type,coverage_start_date,
                     coverage_end_date,date_semantics_status,date_evidence_json,processing_status,error_count)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'INGESTED',0)""",
                    (file_id,sh.index,sh.name,sh.visibility,len(sh.rows),col_count,sh.header_row_number,sh.coverage_type,sh.coverage_start,sh.coverage_end,
                     sh.date_semantics_status,_json_dump(sh.date_evidence)))
                sheet_id=int(cur.lastrowid); header_vals=sh.headers or []
                for c in range(1,col_count+1):
                    header=header_vals[c-1] if c-1<len(header_vals) else None; samples=[]
                    for row in sh.rows[:25]:
                        if c-1<len(row) and _cell_text(row[c-1]): samples.append(_jsonable(row[c-1]))
                        if len(samples)>=5: break
                    cur.execute("""INSERT INTO ingest_column
                        (sheet_id,column_position,source_column_ref,raw_header_text,normalized_header_candidate,detected_data_type,type_confidence,sample_values_json)
                        VALUES (%s,%s,%s,%s,%s,NULL,NULL,%s)""",
                        (sheet_id,c,_excel_col(c),header,header.strip().lower() if header else None,_json_dump(samples)))
                if duplicate_of is not None: continue
                for row_no,row in enumerate(sh.rows,1):
                    payload={_excel_col(i+1):_jsonable(v) for i,v in enumerate(row)}; raw_text='\t'.join(_cell_text(v) for v in row)
                    row_hash=hashlib.sha256(raw_text.encode('utf-8',errors='replace')).hexdigest(); observed_date=sh.row_dates.get(row_no)
                    observed_role='POSTING_DATE' if observed_date and p.source_type=='movement' else None
                    cur.execute(f"""INSERT INTO {raw_table}
                        (batch_id,file_id,sheet_id,source_row_number,source_row_kind,observed_business_date,observed_date_role,raw_payload,raw_text,row_sha256)
                        VALUES (%s,%s,%s,%s,'UNKNOWN',%s,%s,%s,%s,%s)""",
                        (batch_id,file_id,sheet_id,row_no,observed_date,observed_role,_json_dump(payload),raw_text,row_hash)); raw_count+=1
            status='QA_HOLD' if p.source_type=='unclassified' else 'INGESTED'; err_count=1 if p.source_type=='unclassified' else 0
            cur.execute("UPDATE ingest_file SET source_row_count=%s,processing_status=%s,error_count=%s,completed_at=CURRENT_TIMESTAMP(6) WHERE file_id=%s",
                        (raw_count,status,err_count,file_id))
            if p.source_type=='unclassified':
                cur.execute("""INSERT INTO ingest_error
                    (batch_id,file_id,pipeline_run_id,stage_name,severity,error_code,error_message,detail_json)
                    SELECT %s,%s,pipeline_run_id,'SOURCE_CLASSIFICATION','ERROR','SOURCE_TYPE_UNRESOLVED',%s,%s
                    FROM pipeline_run WHERE batch_id=%s AND pipeline_name=%s AND stage_name='RAW_INGEST' ORDER BY pipeline_run_id DESC LIMIT 1""",
                    (batch_id,file_id,f'Source type unresolved for {p.filename}',_json_dump({'warnings':p.warnings}),batch_id,API_PIPELINE))
            for warning in p.warnings:
                cur.execute("""INSERT INTO ingest_error
                    (batch_id,file_id,pipeline_run_id,stage_name,severity,error_code,error_message,detail_json)
                    SELECT %s,%s,pipeline_run_id,'DATE_OR_PARSE_SEMANTICS','WARN','SOURCE_WARNING',%s,%s
                    FROM pipeline_run WHERE batch_id=%s AND pipeline_name=%s AND stage_name='RAW_INGEST' ORDER BY pipeline_run_id DESC LIMIT 1""",
                    (batch_id,file_id,warning,_json_dump({'filename':p.filename}),batch_id,API_PIPELINE))
            cur.execute("""UPDATE ingest_batch SET file_count=file_count+1,source_row_count=source_row_count+%s,error_count=error_count+%s,
                notes=%s WHERE batch_id=%s""",(raw_count,err_count,_notes(device_id,'UPLOADING',last_file=filename),batch_id))
            conn.commit()
            return {'batch_id':batch_id,'session_id':session_id,'file_id':file_id,'filename':filename,'sha256':p.sha256,'source_type':p.source_type,
                    'raw_rows_inserted':raw_count,'rows_read':total_rows,'duplicate_of_file_id':duplicate_of,'status':status,'warnings':p.warnings}
        except Exception:
            conn.rollback(); raise
        finally: cur.close()

def commit_batch(session_id: str, device_id: str) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            b=_session(cur,session_id,lock=True); batch_id=int(b['batch_id'])
            owner=_device_from_notes(b.get('notes'))
            if owner and owner!=device_id: raise PermissionError('This upload session belongs to another device.')
            if b['processing_status']!='API_UPLOADING':
                cur.execute("SELECT processing_status FROM ingest_batch WHERE batch_id=%s",(batch_id,)); st=cur.fetchone()['processing_status']
                return {'batch_id':batch_id,'session_id':session_id,'queued':st!='API_UPLOADING','status':st,'idempotent':True}
            cur.execute("SELECT COUNT(*) c,COALESCE(SUM(source_row_count),0) r,COALESCE(SUM(error_count),0) e FROM ingest_file WHERE batch_id=%s",(batch_id,)); agg=cur.fetchone()
            if int(agg['c'])==0: raise RuntimeError('Cannot commit an empty upload batch.')
            ec=int(agg['e']); batch_status='QA_HOLD' if ec else 'INGESTED_PENDING_QA'
            cur.execute("UPDATE ingest_batch SET file_count=%s,source_row_count=%s,error_count=%s,processing_status=%s,completed_at=CURRENT_TIMESTAMP(6),notes=%s WHERE batch_id=%s",
                        (int(agg['c']),int(agg['r']),ec,batch_status,_notes(device_id,'COMMITTED'),batch_id))
            cur.execute("""UPDATE pipeline_run SET processing_status='COMPLETED',completed_at=CURRENT_TIMESTAMP(6),rows_inserted=%s,error_count=%s,
                detail_json=%s WHERE batch_id=%s AND pipeline_name=%s AND stage_name='RAW_INGEST' AND processing_status='STARTED'""",
                (int(agg['r']),ec,_json_dump({'file_count':int(agg['c']),'device_id':device_id}),batch_id,API_PIPELINE))
            if not ec:
                cur.execute("SELECT COUNT(*) c FROM pipeline_run WHERE batch_id=%s AND pipeline_name=%s AND stage_name='POST_RAW_PIPELINE'",(batch_id,API_PIPELINE))
                if int(cur.fetchone()['c'])==0:
                    cur.execute("""INSERT INTO pipeline_run
                        (batch_id,pipeline_name,stage_name,run_number,processing_status,code_version,detail_json)
                        VALUES (%s,%s,'POST_RAW_PIPELINE',1,'QUEUED',%s,%s)""",
                        (batch_id,API_PIPELINE,API_VERSION,_json_dump({'device_id':device_id})))
            conn.commit(); return {'batch_id':batch_id,'session_id':session_id,'queued':not ec,'status':batch_status,'error_count':ec}
        except Exception:
            conn.rollback(); raise
        finally: cur.close()

def session_status(session_id: str) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT batch_id,batch_key,batch_label,processing_status,upload_started_at,completed_at,file_count,source_row_count,error_count,notes FROM ingest_batch WHERE batch_key=%s",(session_id,)); b=cur.fetchone()
        if not b: raise KeyError('Upload session not found')
        bid=int(b['batch_id'])
        cur.execute("SELECT file_id,original_filename,source_type,processing_status,source_row_count,error_count,duplicate_of_file_id,coverage_start_date,coverage_end_date FROM ingest_file WHERE batch_id=%s",(bid,)); files=cur.fetchall()
        files.sort(key=lambda x: int(x.get('file_id') or 0))
        cur.execute(
            """SELECT pipeline_run_id,stage_name,processing_status,started_at,completed_at,
                      error_count
               FROM pipeline_run
               WHERE batch_id=%s AND pipeline_name=%s""",
            (bid,API_PIPELINE),
        ); runs=cur.fetchall()
        runs.sort(key=lambda x: int(x.get('pipeline_run_id') or 0))
        cur.execute("SELECT result_status,blocking_issue_count,updated_at FROM phase2c_batch_result WHERE batch_id=%s",(bid,)); p2=cur.fetchone()
        cur.execute("SELECT result_status,blocking_issue_count,quick_check_rows,quick_check_ready_rows,quick_check_hold_rows,updated_at FROM phase3_batch_result WHERE batch_id=%s",(bid,)); p3=cur.fetchone()
        cur.close()
    def conv(o):
        if not o: return o
        for k,v in list(o.items()):
            if isinstance(v,(date,datetime)):
                o[k]=_wire_value(v)
        return o
    return {'batch':conv(b),'files':[conv(x) for x in files],'api_runs':[conv(x) for x in runs],'phase2c':conv(p2),'phase3':conv(p3)}


def abort_batch(session_id: str, device_id: str, is_admin: bool=False) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            b=_session(cur,session_id,lock=True); batch_id=int(b['batch_id']); owner=_device_from_notes(b.get('notes'))
            if owner and owner!=device_id and not is_admin: raise PermissionError('Only the owner or an admin device can abort this upload session.')
            if b['processing_status']!='API_UPLOADING': raise RuntimeError(f"Only an API_UPLOADING session can be aborted; current status={b['processing_status']}")
            cur.execute("UPDATE ingest_batch SET processing_status='API_ABORTED',completed_at=CURRENT_TIMESTAMP(6),notes=%s WHERE batch_id=%s",
                        (_notes(device_id,'ABORTED',original_owner=owner),batch_id))
            cur.execute("UPDATE pipeline_run SET processing_status='FAILED',completed_at=CURRENT_TIMESTAMP(6),error_count=1,detail_json=%s WHERE batch_id=%s AND pipeline_name=%s AND stage_name='RAW_INGEST' AND processing_status='STARTED'",
                        (_json_dump({'aborted_by':device_id}),batch_id,API_PIPELINE))
            conn.commit(); return {'batch_id':batch_id,'session_id':session_id,'status':'API_ABORTED'}
        except Exception:
            conn.rollback(); raise
        finally: cur.close()
