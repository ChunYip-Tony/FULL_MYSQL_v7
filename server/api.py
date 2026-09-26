from __future__ import annotations
import hmac, json
from datetime import date, datetime
from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from pydantic import BaseModel
from config import get_settings
from db import db_conn, test_database
from data_coverage import required_daily_coverage
from ingest import recent_batches
from v7_ingest import begin_batch, add_file, commit_batch, session_status, find_active_batch, abort_batch

VERSION='7.0.22-single-service'
app=FastAPI(title='FULL MYSQL Secure API',version=VERSION,docs_url=None,redoc_url=None)

def j(v):
    if isinstance(v,(date,datetime)): return v.isoformat()
    return str(v)

def device_from_auth(authorization: str|None):
    if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'Bearer token required')
    token=authorization.split(' ',1)[1].strip(); s=get_settings()
    for device,expected in s.api_tokens.items():
        if hmac.compare_digest(token,expected): return device
    raise HTTPException(401,'Invalid API token')

class BatchCreate(BaseModel):
    label: str|None=None

@app.get('/healthz')
def healthz(): return {'ok':True,'version':VERSION}

@app.get('/v1/status')
def status(authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization)
    try: db=test_database(); cov=required_daily_coverage(lookback_days=35) if db.get('phase3_schema_ready') else None
    except Exception as exc: raise HTTPException(503,f'Database unavailable: {exc}')
    return json.loads(json.dumps({'version':VERSION,'device':device,'database':db,'active_batch':find_active_batch(),'coverage':cov,'recent_batches':recent_batches(12)},default=j))

@app.get('/v1/active')
def active(authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization); return {'active_batch':find_active_batch()}

@app.post('/v1/batches')
def create_batch(body:BatchCreate,authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization); r=begin_batch(device,body.label)
    if not r.get('created'): raise HTTPException(409,detail={'message':'Another ingest batch is active','active':r.get('active')})
    return r

@app.post('/v1/batches/{session_id}/files')
async def upload_file(session_id:str, file:UploadFile=File(...), authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization); s=get_settings(); data=await file.read()
    if len(data)>s.upload_limit_mb*1024*1024: raise HTTPException(413,f'File exceeds {s.upload_limit_mb} MB limit')
    try: return add_file(session_id,device,file.filename or 'upload.bin',data)
    except KeyError as exc: raise HTTPException(404,str(exc))
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post('/v1/batches/{session_id}/commit')
def commit(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization)
    try: return commit_batch(session_id,device)
    except KeyError as exc: raise HTTPException(404,str(exc))
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except Exception as exc: raise HTTPException(400,str(exc))


@app.post('/v1/batches/{session_id}/abort')
def abort(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device=device_from_auth(authorization); s=get_settings()
    try: return abort_batch(session_id,device,device in s.admin_devices)
    except KeyError as exc: raise HTTPException(404,str(exc))
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except Exception as exc: raise HTTPException(400,str(exc))

@app.get('/v1/batches/{session_id}')
def batch(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    try: return json.loads(json.dumps(session_status(session_id),default=j))
    except KeyError as exc: raise HTTPException(404,str(exc))


@app.get('/v1/batches/{session_id}/qa-summary')
def batch_qa_summary(session_id:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT batch_id,processing_status FROM ingest_batch WHERE batch_key=%s LIMIT 1",(session_id,))
        b=cur.fetchone()
        if not b:
            cur.close()
            raise HTTPException(404,'Batch session not found')
        bid=int(b['batch_id'])

        def grouped(table, extra_where=''):
            cur.execute(
                f"""SELECT g.issue_code,g.severity,g.issue_count
                    FROM (
                        SELECT issue_code,UPPER(severity) AS severity,COUNT(*) AS issue_count
                        FROM {table}
                        WHERE batch_id=%s AND issue_status='OPEN' {extra_where}
                        GROUP BY issue_code,UPPER(severity)
                    ) AS g
                    ORDER BY FIELD(g.severity,'CRITICAL','HIGH','MEDIUM','LOW'),
                             g.issue_count DESC,g.issue_code""",
                (bid,),
            )
            return cur.fetchall()

        cur.execute(
            """SELECT result_status,blocking_issue_count,quick_check_rows,quick_check_ready_rows,
                      quick_check_hold_rows,detail_json,updated_at
               FROM phase3_batch_result WHERE batch_id=%s""",
            (bid,),
        )
        p3=cur.fetchone()
        p3_detail={}
        if p3:
            try:
                p3_detail=json.loads(p3.get('detail_json') or '{}')
            except Exception:
                p3_detail={}
            p3.pop('detail_json',None)

        # Reason-level CURRENT serving QA counts.
        # Source of truth is the serving snapshot itself so the returned
        # reason counts and UPC list always reconcile to current_hold_rows.
        cur.execute(
            """SELECT ean_upc,blocking_reason
               FROM quick_check_current
               WHERE quick_check_status='QA_HOLD'
               ORDER BY ean_upc"""
        )
        reason_counts={}
        hold_upcs=[]
        for row in cur.fetchall():
            raw_reason=str(row.get('blocking_reason') or '')
            reasons=[x.strip() for x in raw_reason.split(',') if x and x.strip()]
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason,0) + 1
            hold_upcs.append({'upc':str(row['ean_upc']),'reasons':reasons})

        # Remaining active sold-UPC identity issues.
        # HIGH/CRITICAL = real batch blockers.
        # MEDIUM + temporary_qa_waiver = explicitly waived, still unresolved.
        cur.execute(
            """SELECT entity_key,severity,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='SOLD_UPC_UNMAPPED'
               ORDER BY issue_id""",
            (bid,),
        )
        sold_unmapped=[]
        temporarily_waived_sold_unmapped=[]
        for row in cur.fetchall():
            try:
                detail=json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail={}
            item={
                'upc':str(row['entity_key']),
                'description':detail.get('description'),
                'activity_scope':detail.get('activity_scope'),
                'activity_basis':detail.get('activity_basis'),
                'repair_candidates':detail.get('v711_repair_candidates'),
                'multitab_repair':detail.get('v712_multitab_repair'),
                'multitab_candidates':detail.get('v712_cross_tab_candidates'),
                'cross_tab_signature_repair':detail.get('v713_cross_tab_signature_repair'),
                'temporary_qa_waiver':detail.get('temporary_qa_waiver'),
            }
            waiver=detail.get('temporary_qa_waiver') or {}
            is_waived=(
                isinstance(waiver,dict)
                and waiver.get('waiver_type')=='IDENTITY_PENDING'
                and waiver.get('non_blocking_current_readiness') is True
            )
            if is_waived:
                temporarily_waived_sold_unmapped.append(item)
            elif str(row.get('severity') or '').upper() in {'HIGH','CRITICAL'}:
                sold_unmapped.append(item)

        cur.execute(
            """SELECT entity_key,detail_json
               FROM qa_phase3_issue
               WHERE batch_id=%s AND issue_status='OPEN'
                 AND issue_code='HISTORICAL_SOLD_UPC_UNMAPPED'
               ORDER BY issue_id""",
            (bid,),
        )
        historical_unmapped=[]
        for row in cur.fetchall():
            try:
                detail=json.loads(row.get('detail_json') or '{}')
            except Exception:
                detail={}
            historical_unmapped.append({
                'upc':str(row['entity_key']),
                'description':detail.get('description'),
                'activity_scope':detail.get('activity_scope'),
                'activity_basis':detail.get('activity_basis'),
            })

        cur.execute(
            """SELECT
                   COUNT(*) AS serving_rows_total,
                   SUM(CASE WHEN quick_check_status='HISTORICAL_ONLY' THEN 1 ELSE 0 END) AS historical_rows,
                   SUM(CASE WHEN quick_check_status IN ('READY','QA_HOLD') THEN 1 ELSE 0 END) AS current_active_rows,
                   SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS current_ready_rows,
                   SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS current_hold_rows
               FROM quick_check_current"""
        )
        qc_scope=cur.fetchone() or {}
        qc_scope['hold_upc_list_count']=len(hold_upcs)
        qc_scope['hold_reason_row_parity']=(
            int(qc_scope.get('current_hold_rows') or 0) == len(hold_upcs)
        )

        result={
            'batch_id':bid,
            'processing_status':b['processing_status'],
            'phase2c_issue_counts':grouped('qa_identity_uom_issue'),
            'phase3_issue_counts':grouped('qa_phase3_issue'),
            'batch_blocking_issue_counts':grouped(
                'qa_phase3_issue',
                "AND UPPER(severity) IN ('HIGH','CRITICAL') AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'"
            ),
            'serving_issue_counts':grouped(
                'qa_phase3_issue',
                "AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'"
            ),
            'quick_check_reason_counts':reason_counts,
            'quick_check_scope':qc_scope,
            'current_active_cost_repair':p3_detail.get('current_active_cost_repair'),
            'sold_upc_unmapped':sold_unmapped,
            'temporarily_waived_sold_upc_unmapped':temporarily_waived_sold_unmapped,
            'historical_sold_upc_unmapped':historical_unmapped,
            'historical_nonblocking_issue_counts':grouped(
                'qa_phase3_issue',
                "AND issue_code='HISTORICAL_SOLD_UPC_UNMAPPED'"
            ),
            'quick_check_hold_upcs':hold_upcs,
            'phase3':p3,
        }
        cur.close()
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/diagnostics/cost-lineage')
def cost_lineage_diagnostic(
    family_id:int,
    authorization: Annotated[str|None,Header()]=None,
):
    """Read-only diagnostic endpoint for current cost lineage.

    Intended for PowerShell/API diagnostics so routine troubleshooting never
    requires an interactive MySQL/DigitalOcean console session.
    """
    device_from_auth(authorization)

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)

        cur.execute(
            """SELECT family_id,main_article_number,family_description
               FROM product_family
               WHERE family_id=%s
               LIMIT 1""",
            (family_id,),
        )
        family=cur.fetchone()
        if not family:
            cur.close()
            raise HTTPException(404,'Family not found')

        cur.execute(
            """SELECT q.ean_upc,q.selling_description,q.activity_scope,
                      q.quick_check_status,q.blocking_reason,
                      q.current_cost_per_base,q.current_cost_date,
                      q.current_cost_source,q.cost_base_uom,
                      q.selling_uom_code,q.cost_per_selling_unit
               FROM quick_check_current q
               WHERE q.family_id=%s
               ORDER BY
                 CASE q.quick_check_status
                   WHEN 'QA_HOLD' THEN 0
                   WHEN 'READY' THEN 1
                   ELSE 2
                 END,
                 q.ean_upc""",
            (family_id,),
        )
        quick_check=cur.fetchall()

        cur.execute(
            """SELECT company_price_observation_id,source_type,observation_date,
                      article_number,article_id,ean_upc,upc_id,family_id,
                      official_cost,cost_uom_code,
                      price_a,price_b,price_c,
                      batch_id,file_id,sheet_id,raw_id,source_row_number
               FROM company_price_observation
               WHERE family_id=%s
               ORDER BY observation_date DESC,company_price_observation_id DESC
               LIMIT 25""",
            (family_id,),
        )
        company_cost=cur.fetchall()

        cur.execute(
            """SELECT co.cost_observation_id,co.article_id,a.article_number,
                      co.family_id,co.cost_amount,co.cost_per_base_uom,
                      co.currency_code,
                      cu.uom_code AS cost_uom,
                      bu.uom_code AS base_uom,
                      co.source_type,co.movement_type,co.business_date,
                      co.cost_status,co.confidence,
                      co.batch_id,co.file_id,co.sheet_id,
                      co.raw_table_name,co.raw_id,co.source_row_number
               FROM article_cost_observation co
               LEFT JOIN article a ON a.article_id=co.article_id
               LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
               LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
               WHERE co.family_id=%s
                  OR co.article_id IN (
                       SELECT a2.article_id
                       FROM article a2
                       JOIN bridge_article_family baf
                         ON baf.article_id=a2.article_id
                        AND baf.mapping_status='CONFIRMED'
                        AND baf.is_primary=TRUE
                        AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                       WHERE baf.family_id=%s
                  )
               ORDER BY co.business_date DESC,co.cost_observation_id DESC
               LIMIT 50""",
            (family_id,family_id),
        )
        cost_observations=cur.fetchall()

        cur.execute(
            """SELECT article_number,article_id,family_id,description,
                      movement_type,posting_date,
                      entry_quantity,entry_uom_code,
                      base_quantity,base_uom_code,
                      amount_local_currency,
                      CASE
                        WHEN amount_local_currency IS NOT NULL
                         AND amount_local_currency<>0
                         AND base_quantity IS NOT NULL
                         AND base_quantity<>0
                        THEN ABS(amount_local_currency/base_quantity)
                        ELSE NULL
                      END AS derived_unit_cost,
                      article_document,purchase_order,vendor_code,
                      batch_id,file_id,sheet_id,raw_id,source_row_number
               FROM movement_history
               WHERE family_id=%s
                 AND movement_type IN ('101','107','109')
               ORDER BY posting_date DESC,raw_id DESC
               LIMIT 50""",
            (family_id,),
        )
        receipts=cur.fetchall()

        cur.execute(
            """SELECT
                 SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0 THEN 1 ELSE 0 END)
                   AS positive_official_cost_rows,
                 SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0
                               AND cost_uom_code IS NOT NULL
                          THEN 1 ELSE 0 END)
                   AS positive_official_with_uom_rows,
                 COUNT(*) AS company_rows
               FROM company_price_observation
               WHERE family_id=%s""",
            (family_id,),
        )
        company_summary=cur.fetchone() or {}

        cur.execute(
            """SELECT
                 COUNT(*) AS cost_observation_rows,
                 SUM(CASE WHEN source_type='MOVEMENT_RECEIPT_VALUATION' THEN 1 ELSE 0 END)
                   AS receipt_cost_rows,
                 SUM(CASE WHEN source_type IN (
                              'FROZEN_INVENTORY_OFFICIAL_COST',
                              'TX_SEAFOOD_ABC_PRICE_OFFICIAL_COST',
                              'LIVE_FRESH_SUGGESTION_OFFICIAL_COST'
                            ) THEN 1 ELSE 0 END)
                   AS official_cost_observation_rows,
                 SUM(CASE WHEN family_id=%s THEN 1 ELSE 0 END)
                   AS rows_linked_to_requested_family
               FROM article_cost_observation
               WHERE family_id=%s
                  OR article_id IN (
                       SELECT a2.article_id
                       FROM article a2
                       JOIN bridge_article_family baf
                         ON baf.article_id=a2.article_id
                        AND baf.mapping_status='CONFIRMED'
                        AND baf.is_primary=TRUE
                        AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                       WHERE baf.family_id=%s
                  )""",
            (family_id,family_id,family_id),
        )
        cost_summary=cur.fetchone() or {}

        cur.close()

    result={
        'family':family,
        'summary':{
            'company':company_summary,
            'derived_cost':cost_summary,
            'quick_check_rows':len(quick_check),
            'receipt_rows':len(receipts),
        },
        'quick_check':quick_check,
        'company_price_cost_evidence':company_cost,
        'article_cost_observations':cost_observations,
        'receipt_101_107_109_evidence':receipts,
    }
    return json.loads(json.dumps(result,default=j))


@app.get('/v1/quick-check/{upc}')
def quick_check(upc:str,authorization: Annotated[str|None,Header()]=None):
    device_from_auth(authorization); q=''.join(ch for ch in upc if ch.isdigit()).lstrip('0') or '0'
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM quick_check_current WHERE ean_upc=%s OR TRIM(LEADING '0' FROM ean_upc)=%s LIMIT 1",(upc,q))
        row=cur.fetchone()
        if not row:
            cur.execute(
                """SELECT entity_key,severity,detail_json
                   FROM qa_phase3_issue
                   WHERE issue_status='OPEN'
                     AND issue_code='SOLD_UPC_UNMAPPED'
                     AND (entity_key=%s OR TRIM(LEADING '0' FROM entity_key)=%s)
                   ORDER BY batch_id DESC,issue_id DESC
                   LIMIT 1""",
                (upc,q),
            )
            unresolved=cur.fetchone()
            cur.close()
            if unresolved:
                try:
                    detail=json.loads(unresolved.get('detail_json') or '{}')
                except Exception:
                    detail={}
                waiver=detail.get('temporary_qa_waiver') or {}
                raise HTTPException(
                    409,
                    detail={
                        'status':'BLOCKED',
                        'reason':'IDENTITY_PENDING_TEMP_WAIVER' if waiver else 'SOLD_UPC_UNMAPPED',
                        'upc':str(unresolved['entity_key']),
                        'description':detail.get('description'),
                        'temporary_qa_waiver':waiver or None,
                    },
                )
            raise HTTPException(404,'Quick Check UPC not found')
        cur.close()
    return json.loads(json.dumps(row,default=j))
