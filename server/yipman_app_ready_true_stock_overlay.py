from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
import uuid
from yipman_app_ready_snapshot import APP_READY_SNAPSHOTS
_OH_KEYS=("effective_oh","current_oh","ordering_oh_used","actual_position")
_STALE_DECISION_KEYS=("recommendation_code","recommendation","suggested_order_qty","suggested_delivery_qty","suggested_price","suggested_reg_price","testing_price","target_price")
def _norm(value:Any)->str:return str(value or "").strip()
def _same_family(row:dict[str,Any],family_id:str,main_article:str)->bool:
    fid=_norm(family_id);article=_norm(main_article);row_family_ids={_norm(row.get("family_id")),_norm(row.get("family"))}-{""};row_articles={_norm(row.get("main_article_number")),_norm(row.get("family_article"))}-{""};return bool((fid and fid in row_family_ids) or (article and article in row_articles))
def _patch_row(row,family_id,main_article,qty,uom,source):
    if not _same_family(row,family_id,main_article):return False
    for key in _OH_KEYS:
        if key in row:row[key]=qty
    if "effective_oh_uom" in row:row["effective_oh_uom"]=uom
    if "current_oh_uom" in row:row["current_oh_uom"]=uom
    if "oh_source" in row:row["oh_source"]=source
    if "effective_oh_source" in row:row["effective_oh_source"]=source
    if any(k in row for k in ("recommendation_code","operational_decision_code","suggested_order_qty","suggested_price")):
        # Inventory changed, so any recommendation derived from the old OH is unsafe.
        # Keep the old values only in an audit envelope; operational fields fail closed.
        stale={k:row.get(k) for k in _STALE_DECISION_KEYS if k in row and row.get(k) is not None}
        if stale:row["pre_true_stock_decision_audit"]=stale
        for key in _STALE_DECISION_KEYS:
            if key in row:row[key]=None
        row["decision_evidence_ready"]=False;missing=list(row.get("decision_missing_evidence")) if isinstance(row.get("decision_missing_evidence"),list) else [];marker="INVENTORY_FAMILY_RECALC_PENDING"
        if marker not in missing:missing.append(marker)
        row["decision_missing_evidence"]=missing;row["operational_decision_code"]="DATA_NEEDED";row["operational_decision_label"]="DATA NEEDED"
    row["true_stock_incremental_overlay"]=True;row["inventory_overlay_source"]=source;return True
def _walk(value,family_id,main_article,qty,uom,source="TRUE_STOCK"):
    count=0
    if isinstance(value,dict):
        if _patch_row(value,family_id,main_article,qty,uom,source):count+=1
        for child in value.values():count+=_walk(child,family_id,main_article,qty,uom,source)
    elif isinstance(value,list):
        for child in value:count+=_walk(child,family_id,main_article,qty,uom,source)
    return count
def _digits(value):return "".join(c for c in str(value or "") if c.isdigit()).lstrip("0")
def _decision_keys(row):
    family=str(row.get("family") or row.get("family_article") or row.get("family_id") or row.get("main_article_number") or "").strip();upc=_digits(row.get("upc") or row.get("ean_upc") or row.get("ean"));action=str(row.get("action_type") or row.get("suggestion_type") or row.get("price_suggestion_type") or row.get("recommendation_type") or row.get("target_price_type") or row.get("price_type") or "").strip().upper().replace("-","_").replace(" ","_");keys=set()
    if upc:keys.add("UPC:"+upc);action and keys.add("UPC:"+upc+":"+action)
    if family:keys.add("FAMILY:"+family);action and keys.add("FAMILY:"+family+":"+action)
    return keys
def _rebuild_decision_index(section):
    if not isinstance(section,dict) or "by_key" not in section:return
    by_key={}
    def visit(value):
        if isinstance(value,dict):
            if value is section.get("by_key"):return
            for key in _decision_keys(value):by_key.setdefault(key,value)
            for child_key,child in value.items():
                if child_key!="by_key":visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    for key,value in section.items():
        if key!="by_key":visit(value)
    section["by_key"]=by_key
def apply_true_stock_family_overlay(result:dict[str,Any])->dict[str,Any]:
    active=APP_READY_SNAPSHOTS.active()
    if active is None:return {"status":"NO_ACTIVE_SNAPSHOT","patched_rows":0}
    family_id=str(result.get("family_id") or "").strip();main_article=str(result.get("main_article_number") or "").strip();cancelled=str(result.get("action") or "").upper()=="TRUE_STOCK_CANCELLED";qty=result.get("system_oh") if cancelled else result.get("true_stock");uom_raw=result.get("system_oh_uom") if cancelled else result.get("uom");uom=str(uom_raw or "").strip().upper() or None;source="SYSTEM_OH" if cancelled else "TRUE_STOCK"
    if qty is None or not (family_id or main_article):return {"status":"IDENTITY_OR_QUANTITY_MISSING","patched_rows":0}
    sections=deepcopy(active.sections);patched=_walk(sections,family_id,main_article,qty,uom,source)
    if patched==0:return {"status":"FAMILY_NOT_IN_ACTIVE_SNAPSHOT","patched_rows":0}
    _rebuild_decision_index(sections.get("decision_intelligence"));now=datetime.now(timezone.utc).isoformat();candidate=replace(active,build_id=str(uuid.uuid4()),source_batch_id=f"INVENTORY_INCREMENTAL:{source}:{family_id or main_article}",started_at=now,completed_at=now,sections=sections,error=None,build_ms=0.0);candidate.stage="APP_READY";candidate.section_status=dict(active.section_status)
    from yipman_app_ready_persistence import persist_complete_snapshot_if_active
    if not persist_complete_snapshot_if_active(candidate,active.build_id):
        return {"status":"ACTIVE_GENERATION_CHANGED","patched_rows":0,"retryable":True}
    APP_READY_SNAPSHOTS.hydrate(candidate);return {"status":"APP_READY","build_id":candidate.build_id,"patched_rows":patched,"source":source}
