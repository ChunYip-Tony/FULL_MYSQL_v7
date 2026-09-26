from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from manual_overrides import apply_manual_upc_overrides
from phase3 import relink_history, resolve_late_identity_issues, rebuild_quick_check

VERSION = "7.0.22-fast-user-confirmed-identity-repair"
TARGET_UPCS = ("75539372208", "81223402610")


def _verify(cur) -> list[dict]:
    out=[]
    for ean in TARGET_UPCS:
        cur.execute(
            """SELECT su.ean_upc,a.article_number,pf.main_article_number,pf.family_id,
                      du.uom_code AS selling_uom,bu.uom_code AS base_uom,
                      uh.base_qty_per_selling_unit,uh.resolution_method,
                      uh.mapping_status AS uom_status
               FROM selling_upc su
               LEFT JOIN bridge_article_upc bau
                 ON bau.upc_id=su.upc_id
                AND bau.relationship_type='SELLING'
                AND bau.mapping_status='CONFIRMED'
                AND bau.is_primary=TRUE
                AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
               LEFT JOIN article a ON a.article_id=bau.article_id
               LEFT JOIN bridge_article_family baf
                 ON baf.article_id=a.article_id
                AND baf.mapping_status='CONFIRMED'
                AND baf.is_primary=TRUE
                AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               LEFT JOIN product_family pf ON pf.family_id=baf.family_id
               LEFT JOIN selling_upc_uom_history uh
                 ON uh.upc_id=su.upc_id
                AND uh.mapping_status='CONFIRMED'
                AND (uh.effective_to IS NULL OR uh.effective_to>CURRENT_TIMESTAMP(6))
               LEFT JOIN dim_uom du ON du.uom_id=uh.selling_uom_id
               LEFT JOIN dim_uom bu ON bu.uom_id=uh.base_uom_id
               WHERE su.ean_upc=%s
               ORDER BY bau.article_upc_id DESC,uh.upc_uom_id DESC
               LIMIT 1""",
            (ean,),
        )
        row=cur.fetchone() or {"ean_upc":ean,"status":"NOT_FOUND"}
        out.append(row)
    return out


def main() -> int:
    ap=argparse.ArgumentParser(description="FULL MYSQL v7.0.22 narrow user-confirmed identity repair")
    ap.add_argument("--batch",type=int,default=8)
    args=ap.parse_args()
    try:
        print(json.dumps({"version":VERSION,"database":test_database(),"mode":"FAST_NARROW_IDENTITY_REPAIR"},indent=2,default=str),flush=True)
        with db_conn() as conn:
            cur=conn.cursor(dictionary=True)
            try:
                print("[1/3] Applying authoritative user confirmations...",flush=True)
                override_result=apply_manual_upc_overrides(cur)
                relink_history(cur)
                late_identity=resolve_late_identity_issues(cur,args.batch)

                # Recompute current serving QA only. Historical audit evidence is preserved.
                cur.execute(
                    """UPDATE qa_phase3_issue
                       SET issue_status='RESOLVED',
                           detail_json=JSON_SET(COALESCE(detail_json,JSON_OBJECT()),
                             '$.resolution','Superseded by v7.0.22 user-confirmed identity refresh')
                       WHERE batch_id=%s
                         AND issue_status='OPEN'
                         AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
                    (args.batch,),
                )

                print("[2/3] Refreshing Quick Check serving snapshot only...",flush=True)
                qc=rebuild_quick_check(cur,args.batch)

                cur.execute(
                    """SELECT COUNT(*) AS c
                       FROM qa_phase3_issue
                       WHERE batch_id=%s
                         AND issue_status='OPEN'
                         AND UPPER(severity) IN ('HIGH','CRITICAL')
                         AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'""",
                    (args.batch,),
                )
                blocking=int((cur.fetchone() or {}).get('c') or 0)
                if blocking>0 or qc['rows']==0:
                    status='PHASE3_QA_HOLD'
                elif qc['hold']>0:
                    status='QUICK_CHECK_READY_WITH_HOLDS'
                else:
                    status='QUICK_CHECK_READY'

                verify=_verify(cur)

                cur.execute("SELECT detail_json FROM phase3_batch_result WHERE batch_id=%s",(args.batch,))
                row=cur.fetchone(); detail={}
                if row:
                    try: detail=json.loads(row.get('detail_json') or '{}')
                    except Exception: detail={}
                detail['manual_overrides']=override_result
                detail['temporary_qa_waivers']={
                    'version':'7.0.22-retired',
                    'configured':0,
                    'retired_upcs':list(TARGET_UPCS),
                    'reason':'Authoritative user identity and Selling UOM confirmations received 2026-09-26',
                }
                detail['v722_identity_confirmation']={
                    'mode':'FAST_NARROW_IDENTITY_REPAIR',
                    'late_identity_resolution':late_identity,
                    'verification':verify,
                    'quick_check':qc,
                }

                cur.execute(
                    """UPDATE phase3_batch_result
                       SET quick_check_rows=%s,quick_check_ready_rows=%s,quick_check_hold_rows=%s,
                           blocking_issue_count=%s,result_status=%s,detail_json=%s,
                           updated_at=CURRENT_TIMESTAMP(6)
                       WHERE batch_id=%s""",
                    (qc['rows'],qc['ready'],qc['hold'],blocking,status,json.dumps(detail,default=str),args.batch),
                )
                cur.execute(
                    """UPDATE ingest_batch SET processing_status=%s,
                           completed_at=CURRENT_TIMESTAMP(6) WHERE batch_id=%s""",
                    (status,args.batch),
                )
                conn.commit()
                print("[3/3] Done.",flush=True)
                print(json.dumps({
                    'version':VERSION,
                    'status':status,
                    'blocking_issue_count':blocking,
                    'manual_overrides':{
                        'identity_applied':override_result.get('identity_applied'),
                        'uom_applied':override_result.get('uom_applied'),
                        'held':override_result.get('held'),
                    },
                    'late_identity_resolution':late_identity,
                    'verification':verify,
                    'quick_check':{
                        'current_active_rows':qc['rows'],
                        'ready':qc['ready'],
                        'hold':qc['hold'],
                        'historical_rows':qc.get('historical_rows'),
                        'serving_rows_total':qc.get('serving_rows_total'),
                    },
                },indent=2,ensure_ascii=False,default=str))
                return 0
            except Exception:
                conn.rollback(); raise
            finally:
                cur.close()
    except Exception as exc:
        print(json.dumps({'version':VERSION,'result':'FAILED','error':repr(exc),'traceback':traceback.format_exc()},indent=2,ensure_ascii=False))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
