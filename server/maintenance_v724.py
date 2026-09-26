from __future__ import annotations

import argparse
import json
import traceback

from db import db_conn, test_database
from manual_overrides import apply_manual_upc_overrides
from phase3 import rebuild_quick_check

VERSION = "7.0.24-fast-supported-uom-conversion"
TARGET_UPC = "81223402610"


def _verify(cur):
    cur.execute(
        """SELECT ean_upc,article_number,main_article_number,family_id,
                  selling_uom,base_uom,base_qty_per_selling_unit,
                  current_cost_per_base_uom,current_cost_per_selling_unit,
                  cost_source,cost_date,quick_check_status,blocking_reason
           FROM quick_check_current
           WHERE ean_upc=%s
           LIMIT 1""",
        (TARGET_UPC,),
    )
    return cur.fetchone()


def main() -> int:
    ap=argparse.ArgumentParser(description="FULL MYSQL v7.0.24 narrow supported UOM conversion repair")
    ap.add_argument("--batch",type=int,default=8)
    args=ap.parse_args()
    try:
        print(json.dumps({
            "version":VERSION,
            "database":test_database(),
            "mode":"FAST_SUPPORTED_UOM_CONVERSION",
            "target_upc":TARGET_UPC,
        },indent=2,default=str),flush=True)

        with db_conn() as conn:
            cur=conn.cursor(dictionary=True)
            try:
                print("[1/3] Applying supported conversion evidence...",flush=True)
                override_result=apply_manual_upc_overrides(cur)

                # Current Quick Check issue rows are derived serving QA; rebuild them.
                cur.execute(
                    """UPDATE qa_phase3_issue
                       SET issue_status='RESOLVED',
                           detail_json=JSON_SET(
                             COALESCE(detail_json,JSON_OBJECT()),
                             '$.resolution',
                             'Superseded by v7.0.24 supported UOM conversion refresh'
                           )
                       WHERE batch_id=%s
                         AND issue_status='OPEN'
                         AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'""",
                    (args.batch,),
                )

                print("[2/3] Refreshing Quick Check serving snapshot only...",flush=True)
                qc=rebuild_quick_check(cur,args.batch)
                verify=_verify(cur)

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

                cur.execute("SELECT detail_json FROM phase3_batch_result WHERE batch_id=%s",(args.batch,))
                row=cur.fetchone(); detail={}
                if row:
                    try: detail=json.loads(row.get('detail_json') or '{}')
                    except Exception: detail={}
                detail['v724_supported_uom_conversion']={
                    'mode':'FAST_SUPPORTED_UOM_CONVERSION',
                    'target_upc':TARGET_UPC,
                    'evidence':{
                        'user_confirmed_selling_uom':'PACK',
                        'user_confirmed_case_configuration':'40/150G',
                        'receipt_107_entry':'3 CV',
                        'receipt_107_base':'120 EA',
                        'receipt_107_amount':'330.00',
                        'derived_cost_per_ea':'2.75',
                        'conversion':'1 PACK = 1 EA',
                        'support':'3 CV x 40 selling packs = 120 PACK, exactly matching receipt base quantity 120 EA',
                    },
                    'manual_overrides':override_result,
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
                           completed_at=CURRENT_TIMESTAMP(6)
                       WHERE batch_id=%s""",
                    (status,args.batch),
                )

                conn.commit()
                print("[3/3] Done.",flush=True)
                print(json.dumps({
                    'version':VERSION,
                    'status':status,
                    'target':verify,
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
                conn.rollback()
                raise
            finally:
                cur.close()
    except Exception as exc:
        print(json.dumps({
            'version':VERSION,
            'result':'FAILED',
            'error':repr(exc),
            'traceback':traceback.format_exc(),
        },indent=2,ensure_ascii=False))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
