from __future__ import annotations

from collections import defaultdict
import json
from decimal import Decimal
from typing import Any

from business_clock import completed_through_date
from data_coverage import source_data_days
from db import db_conn

PHYSICAL_POSITIVE={"101","109"}
PHYSICAL_REVERSAL={"102","110"}
COST_STAGE={"107","108"}

def _d(v: Any) -> Decimal | None:
    if v is None: return None
    try: return Decimal(str(v))
    except Exception: return None

def _qty_sig(row: dict[str,Any]) -> tuple[Decimal|None,str|None]:
    q=_d(row.get("base_quantity")); u=str(row.get("base_uom_code") or "").strip().upper() or None
    if q is not None and u: return abs(q),u
    q=_d(row.get("entry_quantity")); u=str(row.get("entry_uom_code") or "").strip().upper() or None
    return ((abs(q),u) if q is not None and u else (None,None))

def _same_qty(a: dict[str,Any], b: dict[str,Any]) -> bool:
    aq,au=_qty_sig(a); bq,bu=_qty_sig(b)
    if aq is None or bq is None or not au or au!=bu: return False
    tol=max(Decimal("0.0001"),max(aq,bq)*Decimal("0.000001"))
    return abs(aq-bq)<=tol

def _gr_5014_id(v: Any) -> str | None:
    if v is None: return None
    s=str(v).strip().replace(",","")
    if s.endswith(".0") and s[:-2].isdigit(): s=s[:-2]
    return s if s.isdigit() and s.startswith("5014") else None

def _row_gr(row: dict[str,Any]) -> tuple[str|None,str|None]:
    doc=_gr_5014_id(row.get("article_document"))
    if doc: return doc,"NORMALIZED_5014_DOCUMENT"
    payload=row.get("raw_payload")
    if isinstance(payload,(bytes,bytearray)):
        payload=payload.decode("utf-8",errors="replace")
    if isinstance(payload,str):
        try: payload=json.loads(payload)
        except Exception: payload={}
    if isinstance(payload,dict):
        q=_gr_5014_id(payload.get("Q"))
        if q: return q,"RAW_REFERENCE_Q_5014"
        for value in payload.values():
            gr=_gr_5014_id(value)
            if gr: return gr,"RAW_ROW_5014_SCAN"
    return None,None

def receipt_double_count_audit(lookback_days:int=365) -> dict[str,Any]:
    days_requested=max(1,min(int(lookback_days),365))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        days=source_data_days(cur,"movement",limit=days_requested,up_to=completed_through_date())
        canonical={x["date"]:int(x["file_id"]) for x in days}
        cur.execute("SELECT COUNT(*) AS n FROM product_family")
        total_families=int((cur.fetchone() or {}).get("n") or 0)
        if not canonical:
            cur.close()
            return {"contract_version":"RECEIPT_DOUBLE_COUNT_AUDIT_V1","status":"NO_CANONICAL_MOVEMENT_DATA","lookback_days":days_requested,"product_families_total":total_families,"families_with_receipt_evidence":0,"current_physical_receipt_types":["101","109"],"current_physical_reversal_types":["102","110"],"cost_stage_types":["107","108"],"families":[]}
        file_ids=sorted(set(canonical.values())); ph=",".join(["%s"]*len(file_ids))
        cur.execute(f"""SELECT m.family_id,pf.main_article_number,pf.family_description,
                              m.file_id,m.raw_id,m.source_row_number,m.article_id,m.article_number,
                              m.movement_type,m.posting_date,m.entry_quantity,m.entry_uom_code,
                              m.base_quantity,m.base_uom_code,m.article_document,m.purchase_order
                       ,rm.raw_payload
                       FROM movement_history m
                       LEFT JOIN product_family pf ON pf.family_id=m.family_id
                       LEFT JOIN raw_movement rm ON rm.raw_id=m.raw_id
                       WHERE m.family_id IS NOT NULL
                         AND m.file_id IN ({ph})
                         AND m.movement_type IN ('101','102','107','108','109','110')
                       ORDER BY m.family_id,m.posting_date,m.file_id,m.raw_id,m.source_row_number""",tuple(file_ids))
        raw=[r for r in cur.fetchall() if r.get("posting_date") in canonical and canonical[r["posting_date"]]==int(r["file_id"])]
        cur.close()

    by_family=defaultdict(list)
    for row in raw: by_family[int(row["family_id"])].append(row)
    family_results=[]; legacy_family_count=0; dup_total=0; missing_101_gr_total=0
    for fid,rows in sorted(by_family.items()):
        positives=[r for r in rows if str(r.get("movement_type")) in {"101","107","109"}]
        s101=[r for r in positives if str(r.get("movement_type"))=="101"]
        s107=[r for r in positives if str(r.get("movement_type"))=="107"]
        s109=[r for r in positives if str(r.get("movement_type"))=="109"]
        missing_101=[]
        for r in s101:
            gr,src=_row_gr(r)
            r["resolved_gr_number"]=gr
            r["resolved_gr_source"]=src
            if not gr:
                q,u=_qty_sig(r)
                missing_101.append({
                    "article_number":r.get("article_number"),
                    "purchase_order":r.get("purchase_order"),
                    "posting_date":r.get("posting_date"),
                    "quantity":q,
                    "uom":u,
                    "article_document":r.get("article_document"),
                    "raw_id":r.get("raw_id"),
                    "source_row_number":r.get("source_row_number"),
                })
        pairs=[]; used=set()
        for a in s107:
            best=None
            for idx,b in enumerate(s109):
                if idx in used: continue
                if a.get("article_id") is not None and b.get("article_id") is not None and int(a["article_id"])!=int(b["article_id"]): continue
                apo=str(a.get("purchase_order") or "").strip(); bpo=str(b.get("purchase_order") or "").strip()
                if apo and bpo and apo!=bpo: continue
                if not _same_qty(a,b): continue
                ad=a.get("posting_date"); bd=b.get("posting_date")
                if ad is None or bd is None or abs((bd-ad).days)>14: continue
                dist=abs((bd-ad).days)
                if best is None or dist<best[0]: best=(dist,idx,b)
            if best:
                _,idx,b=best; used.add(idx); q,u=_qty_sig(b)
                pairs.append({"article_number":a.get("article_number") or b.get("article_number"),"purchase_order":a.get("purchase_order") or b.get("purchase_order"),"cost_stage_107_date":a.get("posting_date"),"physical_gr_109_date":b.get("posting_date"),"quantity":q,"uom":u})
        physical=[r for r in positives if str(r.get("movement_type")) in PHYSICAL_POSITIVE]
        groups=defaultdict(list)
        for r in physical:
            q,u=_qty_sig(r)
            key=(r.get("article_id"),r.get("article_number"),str(r.get("purchase_order") or "").strip() or None,str(r.get("article_document") or "").strip() or None,r.get("posting_date"),q,u)
            groups[key].append(r)
        dups=[]
        for key,grp in groups.items():
            if len(grp)>1:
                dups.append({"article_number":key[1],"purchase_order":key[2],"article_document":key[3],"posting_date":key[4],"quantity":key[5],"uom":key[6],"movement_types":sorted(str(x.get("movement_type")) for x in grp),"row_count":len(grp)})
        if pairs: legacy_family_count+=1
        dup_total+=len(dups)
        missing_101_gr_total+=len(missing_101)
        sample=rows[0]
        family_results.append({"family_id":fid,"family_article_number":sample.get("main_article_number"),"family_name":sample.get("family_description"),"canonical_receipt_rows":len(rows),"physical_positive_rows":len(physical),"direct_101_rows":len(s101),"direct_101_missing_gr_count":len(missing_101),"direct_101_missing_gr_examples":missing_101[:8],"cost_stage_107_rows":len(s107),"physical_109_rows":len(s109),"paired_107_109_events":len(pairs),"legacy_pair_examples":pairs[:8],"physical_duplicate_candidate_count":len(dups),"physical_duplicate_candidates":dups[:8]})
    status=("REVIEW_101_GR_MISSING" if missing_101_gr_total else ("PASS" if dup_total==0 else "REVIEW_PHYSICAL_DUPLICATE_CANDIDATES"))
    return {"contract_version":"RECEIPT_DOUBLE_COUNT_AUDIT_V2_GR_REQUIRED","status":status,"data_through":max(canonical),"lookback_days":days_requested,"product_families_total":total_families,"families_with_receipt_evidence":len(family_results),"current_physical_receipt_types":["101","109"],"current_physical_reversal_types":["102","110"],"cost_stage_types":["107","108"],"rule":"Every positive 101 physical receipt must have a 5014... GR/material-document number. 107/108 never contributes physical delivery quantity or cadence; 109/110 is the physical GR/reversal for blocked-stock flow.","direct_101_missing_gr_count":missing_101_gr_total,"families_with_direct_101_missing_gr":[x for x in family_results if x["direct_101_missing_gr_count"]>0],"legacy_107_109_exposure_family_count":legacy_family_count,"physical_duplicate_candidate_count":dup_total,"families_with_legacy_107_109_pairs":[x for x in family_results if x["paired_107_109_events"]>0],"families_with_physical_duplicate_candidates":[x for x in family_results if x["physical_duplicate_candidate_count"]>0],"families":family_results}
