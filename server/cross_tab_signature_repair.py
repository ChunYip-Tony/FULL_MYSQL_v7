from __future__ import annotations
import json, re
from typing import Any
from article_manual_multitab_repair import _ensure_pos_identity, _load_roster

VERSION = "7.0.13-cross-tab-signature-repair"

def _norm(value: Any) -> str:
    s = str(value or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9./]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _compact(value: Any) -> str:
    return re.sub(r"[^A-Z0-9.]+", "", _norm(value))

def _product_without_exact_size(pos_description: str | None, manual_size: str | None) -> str | None:
    pos, size = _norm(pos_description), _norm(manual_size)
    if not pos or not size:
        return None
    if pos.endswith(size):
        return pos[:-len(size)].strip()
    pc, sc = _compact(pos), _compact(size)
    if sc and pc.endswith(sc):
        toks = pos.split()
        for cut in range(len(toks)):
            if _compact(" ".join(toks[cut:])) == sc:
                return " ".join(toks[:cut]).strip()
    return None

def _desc_agrees(pos_product: str, manual_description: str | None) -> bool:
    a, b = _norm(pos_product), _norm(manual_description)
    return bool(a and b and (a == b or b in a or a in b))

def _open_unmapped(cur, batch_id: int):
    cur.execute(
        """SELECT issue_id,entity_key,detail_json FROM qa_phase3_issue
           WHERE batch_id=%s AND issue_status='OPEN' AND issue_code='SOLD_UPC_UNMAPPED'
           ORDER BY issue_id""", (batch_id,)
    )
    out=[]
    for row in cur.fetchall():
        try: d=json.loads(row.get("detail_json") or "{}")
        except Exception: d={}
        out.append({"issue_id":int(row["issue_id"]),"upc":str(row["entity_key"]),
                    "description":d.get("description"),"detail":d})
    return out

def repair_cross_tab_signature(cur, batch_id: int, preferred_identity_batch_id: int | None = 7):
    roster, roster_stats = _load_roster(cur, preferred_identity_batch_id)
    result={"version":VERSION,"roster":roster_stats,"examined":0,"auto_repaired":0,
            "uom_repaired":0,"ambiguous_family":0,"no_exact_desc_size_signature":0,
            "repaired":[],"remaining_candidates":[]}

    for issue in _open_unmapped(cur,batch_id):
        result["examined"] += 1
        candidates=[]
        for row in roster:
            product=_product_without_exact_size(issue["description"],row.get("pack"))
            if product is None or not _desc_agrees(product,row.get("description")):
                continue
            candidates.append(row)

        families=sorted({str(r["canonical_main"]) for r in candidates if r.get("canonical_main")})
        if candidates and len(families)==1:
            candidates.sort(key=lambda r:(1 if r.get("selling_uom") else 0,
                                          1 if _norm(_product_without_exact_size(issue["description"],r.get("pack"))) == _norm(r.get("description")) else 0),
                            reverse=True)
            best=candidates[0]
            _upc_id,_=_ensure_pos_identity(cur,issue["upc"],best,issue["description"])
            # Identity-only repair.  Because this rule is triggered by a
            # description+size signature rather than an exact UPC alias, do not
            # propagate the Article Manual UM to the new POS UPC automatically.
            result["auto_repaired"] += 1
            repair={"upc":issue["upc"],"pos_description":issue["description"],
                    "main_article":best["canonical_main"],"article":best["article_number"],
                    "manual_description":best.get("description"),"manual_size":best.get("pack"),
                    "explicit_um_candidate":best.get("selling_uom"),"uom_auto_applied":False,"sheet":best.get("sheet_name"),
                    "rule":"EXACT_DESCRIPTION_PLUS_EXACT_SIZE_SIGNATURE"}
            result["repaired"].append(repair)
            d=issue["detail"]; d["v713_cross_tab_signature_repair"]=repair
            cur.execute("UPDATE qa_phase3_issue SET detail_json=%s WHERE issue_id=%s",
                        (json.dumps(d,ensure_ascii=False,default=str),issue["issue_id"]))
        else:
            if candidates and len(families)>1: result["ambiguous_family"] += 1
            else: result["no_exact_desc_size_signature"] += 1
            review=[{"main_article":r.get("canonical_main"),"article":r.get("article_number"),
                     "manual_description":r.get("description"),"manual_size":r.get("pack"),
                     "explicit_um":r.get("selling_uom"),"sheet":r.get("sheet_name")} for r in candidates[:10]]
            result["remaining_candidates"].append({"upc":issue["upc"],
                                                   "pos_description":issue["description"],
                                                   "candidates":review})
    return result
