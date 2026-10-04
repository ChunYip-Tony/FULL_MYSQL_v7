from __future__ import annotations

import csv
import io
import re
from difflib import SequenceMatcher
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import openpyxl
import xlrd

from business_clock import business_today, completed_through_date
from db import db_conn
from webapp_v2_runtime import bulk_ordering_suggestions


PROMO_TYPES={"WEEKLY","WEEKEND","CUSTOM"}


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _iso_date(value: Any) -> date | None:
    if value is None or value=="":
        return None
    if isinstance(value,datetime):
        return value.date()
    if isinstance(value,date):
        return value
    raw=str(value).strip()
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%m/%d/%y","%m-%d-%Y","%m-%d-%y"):
        try:
            return datetime.strptime(raw,fmt).date()
        except ValueError:
            pass
    return None


def _promo_type(value: Any) -> str | None:
    raw=str(value or "").strip().upper()
    if not raw:
        return None
    if "WEEKEND" in raw or "FRI" in raw and "SUN" in raw:
        return "WEEKEND"
    if "WEEKLY" in raw or "THU" in raw:
        return "WEEKLY"
    return raw if raw in PROMO_TYPES else None


def _validate_window(promo_type: str,start: date,end: date) -> None:
    p=str(promo_type or "").upper()
    if p=="WEEKLY":
        if start.weekday()!=3 or end.weekday()!=3 or (end-start).days!=7:
            raise ValueError("WEEKLY_PROMOTION_MUST_BE_THURSDAY_TO_FOLLOWING_THURSDAY")
        return
    if p=="WEEKEND":
        if start.weekday()!=4 or end.weekday()!=6 or (end-start).days!=2:
            raise ValueError("WEEKEND_PROMOTION_MUST_BE_FRIDAY_TO_SUNDAY")
        return
    if p=="CUSTOM":
        if end<start:
            raise ValueError("PROMOTION_END_BEFORE_START")
        return
    raise ValueError("PROMOTION_TYPE_MUST_BE_WEEKLY_WEEKEND_OR_CUSTOM")


def _normalize_item(
    item: dict[str,Any],
    *,
    weekly_start_date: date | None=None,
    weekend_start_date: date | None=None,
) -> dict[str,Any]:
    out=dict(item or {})
    promo_type=_promo_type(
        out.get("promotion_type")
        or out.get("promo_type")
        or out.get("type")
    )
    start=_iso_date(
        out.get("promotion_start_date")
        or out.get("start_date")
        or out.get("promo_start")
    )
    end=_iso_date(
        out.get("promotion_end_date")
        or out.get("end_date")
        or out.get("promo_end")
    )

    if promo_type=="WEEKLY" and start is None:
        start=weekly_start_date
    if promo_type=="WEEKEND" and start is None:
        start=weekend_start_date
    if promo_type=="WEEKLY" and start is not None and end is None:
        end=start+timedelta(days=7)
    if promo_type=="WEEKEND" and start is not None and end is None:
        end=start+timedelta(days=2)

    if promo_type is None and start is not None and end is not None:
        if start.weekday()==3 and end.weekday()==3 and (end-start).days==7:
            promo_type="WEEKLY"
        elif start.weekday()==4 and end.weekday()==6 and (end-start).days==2:
            promo_type="WEEKEND"
        else:
            promo_type="CUSTOM"

    raw_price=(
        out.get("promotion_price")
        if out.get("promotion_price") is not None
        else out.get("sale_price")
    )
    price=None
    if raw_price not in (None,""):
        cleaned=str(raw_price).strip().replace("$","").replace(",","")
        try:
            price=Decimal(cleaned)
        except Exception:
            price=None

    code=str(
        out.get("item_code")
        or out.get("raw_item_code")
        or out.get("upc")
        or out.get("ean")
        or out.get("article")
        or out.get("family_article_number")
        or ""
    ).strip()
    description=str(
        out.get("description")
        or out.get("item_description")
        or out.get("name")
        or ""
    ).strip()

    errors=[]
    if promo_type not in PROMO_TYPES:
        errors.append("PROMOTION_TYPE_MISSING_OR_INVALID")
    if start is None or end is None:
        errors.append("PROMOTION_DATES_MISSING")
    elif promo_type in PROMO_TYPES:
        try:
            _validate_window(promo_type,start,end)
        except ValueError as exc:
            errors.append(str(exc))
    if price is None or price<=0:
        errors.append("PROMOTION_PRICE_MISSING_OR_INVALID")
    if not code:
        errors.append("ITEM_CODE_MISSING")

    return {
        **out,
        "raw_item_code":code or None,
        "raw_description":description or None,
        "promotion_type":promo_type,
        "promotion_start_date":start,
        "promotion_end_date":end,
        "promotion_price":price,
        "validation_errors":errors,
    }


def _ensure_tables(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS yipman_promotion_list (
             list_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
             list_name VARCHAR(255) NOT NULL,
             source_filename VARCHAR(255) NULL,
             created_by VARCHAR(128) NULL,
             status VARCHAR(64) NOT NULL,
             item_count INT NOT NULL DEFAULT 0,
             ready_count INT NOT NULL DEFAULT 0,
             review_count INT NOT NULL DEFAULT 0,
             created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
           )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS yipman_promotion_list_item (
             item_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
             list_id BIGINT NOT NULL,
             raw_item_code VARCHAR(128) NULL,
             raw_description VARCHAR(500) NULL,
             family_id BIGINT NULL,
             family_article_number VARCHAR(64) NULL,
             family_name VARCHAR(255) NULL,
             promotion_type VARCHAR(16) NULL,
             promotion_start_date DATE NULL,
             promotion_end_date DATE NULL,
             promotion_price DECIMAL(18,4) NULL,
             mapping_status VARCHAR(64) NOT NULL,
             mapping_basis VARCHAR(128) NULL,
             validation_error VARCHAR(1000) NULL,
             created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
             INDEX idx_yipman_promo_list_item_list (list_id),
             INDEX idx_yipman_promo_list_item_family (family_id)
           )"""
    )


def _resolve_family(cur, code: str | None) -> dict[str,Any] | None:
    raw=str(code or "").strip()
    if not raw:
        return None
    numeric=re.sub(r"\D","",raw)
    cur.execute(
        """SELECT family_id,main_article_number,family_description,
                  ean_upc,article_number,quick_check_status,upc_velocity_7d
           FROM quick_check_current
           WHERE main_article_number=%s
              OR article_number=%s
              OR ean_upc=%s
              OR (
                   %s<>''
                   AND TRIM(LEADING '0' FROM ean_upc)=TRIM(LEADING '0' FROM %s)
                 )
           ORDER BY
             CASE
               WHEN main_article_number=%s THEN 0
               WHEN article_number=%s THEN 1
               WHEN ean_upc=%s THEN 2
               ELSE 3
             END,
             CASE quick_check_status WHEN 'READY' THEN 0 WHEN 'QA_HOLD' THEN 1 ELSE 2 END,
             COALESCE(upc_velocity_7d,0) DESC
           LIMIT 1""",
        (raw,raw,raw,numeric,numeric,raw,raw,raw),
    )
    row=cur.fetchone()
    if row:
        basis=(
            "FAMILY_ARTICLE"
            if str(row.get("main_article_number") or "")==raw
            else "SELLING_ARTICLE"
            if str(row.get("article_number") or "")==raw
            else "UPC"
        )
        return {
            "family_id":int(row["family_id"]),
            "family_article_number":str(row.get("main_article_number") or ""),
            "family_name":row.get("family_description"),
            "mapping_basis":basis,
        }

    # Receiving / ordering Articles may not be the selling Article published on
    # quick_check_current. Resolve those through the confirmed Article→Family bridge.
    cur.execute(
        """SELECT pf.family_id,pf.main_article_number,pf.family_description
           FROM article a
           JOIN bridge_article_family baf
             ON baf.article_id=a.article_id
            AND baf.mapping_status='CONFIRMED'
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           JOIN product_family pf ON pf.family_id=baf.family_id
           WHERE a.article_number=%s
           ORDER BY pf.family_id
           LIMIT 1""",
        (raw,),
    )
    bridged=cur.fetchone()
    if not bridged:
        return None
    return {
        "family_id":int(bridged["family_id"]),
        "family_article_number":str(bridged.get("main_article_number") or ""),
        "family_name":bridged.get("family_description"),
        "mapping_basis":"ARTICLE_FAMILY_BRIDGE",
    }



def _promo_search_norm(value: Any) -> str:
    return re.sub(r"\s+"," ",str(value or "").strip().upper())


def _promo_fuzzy_score(query: str, *values: Any) -> int:
    q=_promo_search_norm(query)
    if not q:
        return 0
    best=0
    q_tokens=[x for x in q.split(" ") if x]
    for value in values:
        text=_promo_search_norm(value)
        if not text:
            continue
        if text==q:
            best=max(best,1000)
            continue
        if text.startswith(q):
            best=max(best,900)
        elif q in text:
            best=max(best,820)
        text_tokens=set(text.split(" "))
        if q_tokens and all(any(t in candidate or candidate in t for candidate in text_tokens) for t in q_tokens):
            best=max(best,760)
        ratio=int(SequenceMatcher(None,q,text).ratio()*700)
        best=max(best,ratio)
    return best


def search_promotion_items(query: str, limit: int=20) -> dict[str,Any]:
    """Fast, promotion-specific item search without expensive KPI aggregation.

    Direct matches use quick_check_current + Article→Family aliases. A lightweight
    fuzzy fallback scans only identity/name columns, so mobile Manual Promotion
    search does not wait on 28-day metric calculations.
    """
    q=str(query or "").strip()
    if not q:
        return {"contract_version":"YIPMAN_PROMOTION_ITEM_SEARCH_V1","query":q,"count":0,"results":[]}
    n=max(1,min(int(limit or 20),50))
    numeric=q.isdigit()
    upper=_promo_search_norm(q)
    results:list[dict[str,Any]]=[]

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        if numeric:
            cur.execute(
                """SELECT family_id,main_article_number,family_description,
                          ean_upc,article_number,selling_description,selling_uom,
                          quick_check_status,current_price,current_price_type,
                          pos_qty_7d,sales_dollars_7d,
                          CASE
                            WHEN ean_upc=%s THEN 1000
                            WHEN ean_upc REGEXP '^[0-9]+    list_name: str,
    items: list[dict[str,Any]],
    *,
    weekly_start_date: date | None=None,
    weekend_start_date: date | None=None,
    source_filename: str | None=None,
    created_by: str | None=None,
) -> dict[str,Any]:
    name=str(list_name or "").strip() or "Promotion List"
    normalized=[
        _normalize_item(
            x,
            weekly_start_date=weekly_start_date,
            weekend_start_date=weekend_start_date,
        )
        for x in (items or [])
    ]
    if not normalized:
        raise ValueError("PROMOTION_LIST_ITEMS_REQUIRED")

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        cur.execute(
            """INSERT INTO yipman_promotion_list
                 (list_name,source_filename,created_by,status,item_count,ready_count,review_count)
               VALUES (%s,%s,%s,'PROCESSING',%s,0,0)""",
            (name,source_filename,created_by,len(normalized)),
        )
        list_id=int(cur.lastrowid)
        ready=0
        review=0
        seen_ready_families=set()
        for item in normalized:
            mapped=_resolve_family(cur,item.get("raw_item_code"))
            errors=list(item.get("validation_errors") or [])
            status="READY"
            basis=None
            family_id=None
            family_article=None
            family_name=None
            if mapped:
                family_id=int(mapped["family_id"])
                family_article=mapped.get("family_article_number")
                family_name=mapped.get("family_name")
                basis=mapped.get("mapping_basis")
            else:
                errors.append("ITEM_NOT_MAPPED_TO_FAMILY")
            if family_id is not None and family_id in seen_ready_families:
                errors.append("DUPLICATE_FAMILY_IN_PROMOTION_LIST")
            if errors:
                status="REVIEW"
                review+=1
            else:
                ready+=1
                seen_ready_families.add(family_id)
            cur.execute(
                """INSERT INTO yipman_promotion_list_item
                     (list_id,raw_item_code,raw_description,family_id,
                      family_article_number,family_name,promotion_type,
                      promotion_start_date,promotion_end_date,promotion_price,
                      mapping_status,mapping_basis,validation_error)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    list_id,
                    item.get("raw_item_code"),
                    item.get("raw_description"),
                    family_id,
                    family_article,
                    family_name,
                    item.get("promotion_type"),
                    item.get("promotion_start_date"),
                    item.get("promotion_end_date"),
                    item.get("promotion_price"),
                    status,
                    basis,
                    " | ".join(errors) if errors else None,
                ),
            )
        status="READY" if review==0 else ("READY_WITH_REVIEW" if ready else "REVIEW")
        cur.execute(
            """UPDATE yipman_promotion_list
               SET status=%s,ready_count=%s,review_count=%s
               WHERE list_id=%s""",
            (status,ready,review,list_id),
        )
        conn.commit()
        cur.close()
    return get_promotion_list(list_id)


def list_promotion_lists(limit: int=20) -> dict[str,Any]:
    n=max(1,min(int(limit or 20),100))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        conn.commit()
        cur.execute(
            """SELECT * FROM yipman_promotion_list
               ORDER BY list_id DESC
               LIMIT %s""",
            (n,),
        )
        rows=cur.fetchall()
        cur.close()
    return {
        "contract_version":"YIPMAN_PROMOTION_LISTS_V1",
        "count":len(rows),
        "rows":rows,
    }


def get_promotion_list(list_id: int) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        conn.commit()
        cur.execute(
            "SELECT * FROM yipman_promotion_list WHERE list_id=%s LIMIT 1",
            (int(list_id),),
        )
        head=cur.fetchone()
        if not head:
            cur.close()
            raise KeyError("PROMOTION_LIST_NOT_FOUND")
        cur.execute(
            """SELECT * FROM yipman_promotion_list_item
               WHERE list_id=%s
               ORDER BY CASE mapping_status WHEN 'READY' THEN 0 ELSE 1 END,
                        promotion_type,family_name,raw_description,item_id""",
            (int(list_id),),
        )
        items=cur.fetchall()
        cur.close()
    return {
        "contract_version":"YIPMAN_PROMOTION_LIST_V1",
        **head,
        "items":items,
    }



def remove_manual_promotion_list_item(list_id: int, item_id: int) -> dict[str,Any]:
    """Remove one item from a manually-created promotion list and refresh counts."""
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        conn.commit()
        cur.execute(
            "SELECT list_id,source_filename FROM yipman_promotion_list WHERE list_id=%s LIMIT 1",
            (int(list_id),),
        )
        head=cur.fetchone()
        if not head:
            cur.close()
            raise KeyError("PROMOTION_LIST_NOT_FOUND")
        if str(head.get("source_filename") or "").strip().upper()!="MANUAL_SEARCH_ENTRY":
            cur.close()
            raise ValueError("ONLY_MANUAL_PROMOTION_ITEMS_CAN_BE_REMOVED")
        cur.execute(
            """SELECT item_id FROM yipman_promotion_list_item
               WHERE list_id=%s AND item_id=%s LIMIT 1""",
            (int(list_id),int(item_id)),
        )
        if not cur.fetchone():
            cur.close()
            raise KeyError("PROMOTION_LIST_ITEM_NOT_FOUND")
        cur.execute(
            "DELETE FROM yipman_promotion_list_item WHERE list_id=%s AND item_id=%s",
            (int(list_id),int(item_id)),
        )
        cur.execute(
            """SELECT COUNT(*) AS item_count,
                      SUM(CASE WHEN mapping_status='READY' THEN 1 ELSE 0 END) AS ready_count,
                      SUM(CASE WHEN mapping_status<>'READY' THEN 1 ELSE 0 END) AS review_count
               FROM yipman_promotion_list_item
               WHERE list_id=%s""",
            (int(list_id),),
        )
        counts=cur.fetchone() or {}
        item_count=int(counts.get("item_count") or 0)
        ready=int(counts.get("ready_count") or 0)
        review=int(counts.get("review_count") or 0)
        status=(
            "EMPTY" if item_count==0
            else "READY" if review==0
            else ("READY_WITH_REVIEW" if ready else "REVIEW")
        )
        cur.execute(
            """UPDATE yipman_promotion_list
               SET status=%s,item_count=%s,ready_count=%s,review_count=%s
               WHERE list_id=%s""",
            (status,item_count,ready,review,int(list_id)),
        )
        conn.commit()
        cur.close()
    return get_promotion_list(int(list_id))


def calculate_promotion_order(
    list_id: int,
    delivery_date: date,
    next_delivery_date: date,
    *,
    temporary_oh_overrides: list[dict[str,Any]]|None=None,
) -> dict[str,Any]:
    if next_delivery_date<=delivery_date:
        raise ValueError("NEXT_DELIVERY_MUST_BE_AFTER_DELIVERY_DATE")
    if delivery_date<business_today():
        raise ValueError("PROMOTION_DELIVERY_DATE_CANNOT_BE_IN_THE_PAST")

    promo=get_promotion_list(int(list_id))
    ready=[x for x in promo.get("items",[]) if x.get("mapping_status")=="READY"]
    if not ready:
        raise ValueError("PROMOTION_LIST_HAS_NO_READY_ITEMS")

    promotion_items=[
        {
            "family_id":int(x["family_id"]),
            "family_article_number":x.get("family_article_number"),
            "promotion_type":x.get("promotion_type"),
            "promotion_start_date":x.get("promotion_start_date"),
            "promotion_end_date":x.get("promotion_end_date"),
            "promotion_price":x.get("promotion_price"),
            "source_item_id":x.get("item_id"),
        }
        for x in ready
    ]
    family_ids={int(x["family_id"]) for x in ready}
    temp=list(temporary_oh_overrides or [])

    results=[]
    skipped=[]
    category_payloads={}
    for kind in ("FRESH","FROZEN"):
        payload=bulk_ordering_suggestions(
            kind,
            ordering_date=business_today(),
            expected_delivery_date=delivery_date,
            next_delivery_date=next_delivery_date,
            include_sufficient_stock=True,
            family_ids=family_ids,
            promotion_involved=True,
            promotion_items=promotion_items,
            temporary_oh_overrides=temp,
        )
        category_payloads[kind]=payload
        results.extend(payload.get("suggestions") or [])
        skipped.extend(payload.get("skipped") or [])

    item_by_family={int(x["family_id"]):x for x in ready}
    for row in results:
        src=item_by_family.get(int(row["family_id"]))
        row["promotion_list_item"]=src
        # Preserve the shared Family inventory semantics explicitly for the UI:
        # Effective OH is the operational stock authority (including saved
        # Family True Stock); System OH remains the independent system position.
        row["current_effective_oh"]=row.get("effective_oh_raw")
        row["current_effective_oh_uom"]=row.get("effective_oh_uom")
        row["current_effective_oh_source"]=row.get("effective_oh_source")
        row["current_oh_system"]=row.get("system_oh_raw")
        row["current_oh_system_uom"]=row.get("system_oh_uom")
        row["current_oh_for_calculation"]=row.get("ordering_oh_used")
        row["coverage_start_date"]=delivery_date
        row["coverage_end_date"]=next_delivery_date-timedelta(days=1)
        row["order_needed"]=bool(_d(row.get("suggested_order_qty") or 0)>0)

    results.sort(
        key=lambda x:(
            0 if x.get("order_needed") else 1,
            -float(x.get("suggested_order_qty") or 0),
            str(x.get("family_article_name") or ""),
        )
    )

    ready_family_ids={int(x["family_id"]) for x in ready}
    returned_family_ids={int(x["family_id"]) for x in results}
    skipped_family_ids={
        int(x["family_id"]) for x in skipped if x.get("family_id") is not None
    }
    unresolved=sorted(ready_family_ids-returned_family_ids-skipped_family_ids)

    return {
        "contract_version":"YIPMAN_PROMOTION_ORDERING_V2_EFFECTIVE_OH",
        "list":{
            "list_id":promo.get("list_id"),
            "list_name":promo.get("list_name"),
            "status":promo.get("status"),
            "ready_count":promo.get("ready_count"),
            "review_count":promo.get("review_count"),
        },
        "calculated_on":business_today(),
        "completed_reference_date":completed_through_date(),
        "delivery_date":delivery_date,
        "next_delivery_date":next_delivery_date,
        "coverage_end_date":next_delivery_date-timedelta(days=1),
        "temporary_oh_override_count":len(temp),
        "suggestion_count":len(results),
        "order_count":sum(1 for x in results if x.get("order_needed")),
        "rows":results,
        "skipped":skipped,
        "unresolved_family_ids":unresolved,
        "rules":{
            "weekly_window":"THURSDAY_TO_FOLLOWING_THURSDAY_INCLUSIVE",
            "weekend_window":"FRIDAY_TO_SUNDAY_INCLUSIVE",
            "forecast_is_day_by_day":True,
            "promo_days_use_matching_promotion_history":True,
            "non_promo_days_use_regular_history":True,
            "family_effective_oh_authority":"SHARED_FAMILY_EFFECTIVE_OH_INCLUDING_ACTIVE_TRUE_STOCK",
            "system_oh_is_separate_reference":True,
            "temporary_oh_is_request_only":True,
            "temporary_oh_persisted":False,
            "regular_order_temporary_oh_enabled":False,
        },
    }


def _norm_header(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+"," ",str(value or "").strip().upper()).strip()


def _sheet_rows_from_upload(filename: str, content: bytes) -> list[list[Any]]:
    name=str(filename or "").lower()
    if name.endswith(".csv"):
        text=content.decode("utf-8-sig",errors="replace")
        return [list(r) for r in csv.reader(io.StringIO(text))]
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        wb=openpyxl.load_workbook(io.BytesIO(content),data_only=True,read_only=True)
        ws=wb.active
        return [list(r) for r in ws.iter_rows(values_only=True)]
    if name.endswith(".xls"):
        book=xlrd.open_workbook(file_contents=content)
        sh=book.sheet_by_index(0)
        rows=[]
        for r in range(sh.nrows):
            vals=[]
            for c in range(sh.ncols):
                cell=sh.cell(r,c)
                if cell.ctype==xlrd.XL_CELL_DATE:
                    vals.append(xlrd.xldate_as_datetime(cell.value,book.datemode))
                else:
                    vals.append(cell.value)
            rows.append(vals)
        return rows
    raise ValueError("PROMOTION_IMPORT_SUPPORTS_CSV_XLS_XLSX")


def parse_promotion_upload(filename: str, content: bytes) -> list[dict[str,Any]]:
    rows=_sheet_rows_from_upload(filename,content)
    if not rows:
        raise ValueError("PROMOTION_FILE_EMPTY")

    aliases={
        "code":{"UPC","EAN","EAN UPC","ITEM","ITEM CODE","SKU","ARTICLE","ARTICLE NUMBER","FAMILY ARTICLE","FAMILY ARTICLE NUMBER"},
        "description":{"DESCRIPTION","ITEM DESCRIPTION","NAME","ITEM NAME","PRODUCT","PRODUCT NAME"},
        "price":{"SALE PRICE","PROMO PRICE","PROMOTION PRICE","PROMOTIONAL PRICE","AD PRICE","PRICE"},
        "type":{"PROMOTION TYPE","PROMO TYPE","TYPE","PROMOTION"},
        "start":{"START","START DATE","PROMO START","PROMOTION START","SALE START"},
        "end":{"END","END DATE","PROMO END","PROMOTION END","SALE END"},
    }
    header_idx=None
    colmap={}
    for idx,row in enumerate(rows[:15]):
        headers=[_norm_header(x) for x in row]
        candidate={}
        for key,values in aliases.items():
            for col,h in enumerate(headers):
                if h in values:
                    candidate[key]=col
                    break
        if "code" in candidate and ("price" in candidate or "description" in candidate):
            header_idx=idx
            colmap=candidate
            break
    if header_idx is None:
        raise ValueError("PROMOTION_IMPORT_HEADER_NOT_RECOGNIZED")

    out=[]
    active_type=None
    for row in rows[header_idx+1:]:
        cells=list(row)
        combined=" ".join(_norm_header(x) for x in cells if x not in (None,""))
        if "WEEKEND" in combined and not any(
            str(cells[colmap.get(k,-1)] if 0<=colmap.get(k,-1)<len(cells) else "").strip()
            for k in ("code","price")
        ):
            active_type="WEEKEND"
            continue
        if "WEEKLY" in combined and not any(
            str(cells[colmap.get(k,-1)] if 0<=colmap.get(k,-1)<len(cells) else "").strip()
            for k in ("code","price")
        ):
            active_type="WEEKLY"
            continue

        def val(key):
            col=colmap.get(key)
            return cells[col] if col is not None and col<len(cells) else None

        code=val("code")
        desc=val("description")
        price=val("price")
        ptype=val("type") or active_type
        start=val("start")
        end=val("end")
        if all(x in (None,"") for x in (code,desc,price,ptype,start,end)):
            continue
        out.append({
            "item_code":code,
            "description":desc,
            "promotion_price":price,
            "promotion_type":ptype,
            "promotion_start_date":start,
            "promotion_end_date":end,
        })
    if not out:
        raise ValueError("PROMOTION_FILE_HAS_NO_ITEM_ROWS")
    return out

                                 AND TRIM(LEADING '0' FROM ean_upc)=TRIM(LEADING '0' FROM %s) THEN 990
                            WHEN article_number=%s THEN 970
                            WHEN main_article_number=%s THEN 960
                            WHEN article_number LIKE %s THEN 850
                            WHEN main_article_number LIKE %s THEN 840
                            WHEN ean_upc LIKE %s THEN 830
                            ELSE 0
                          END AS search_score
                   FROM quick_check_current
                   WHERE ean_upc=%s
                      OR (ean_upc REGEXP '^[0-9]+    list_name: str,
    items: list[dict[str,Any]],
    *,
    weekly_start_date: date | None=None,
    weekend_start_date: date | None=None,
    source_filename: str | None=None,
    created_by: str | None=None,
) -> dict[str,Any]:
    name=str(list_name or "").strip() or "Promotion List"
    normalized=[
        _normalize_item(
            x,
            weekly_start_date=weekly_start_date,
            weekend_start_date=weekend_start_date,
        )
        for x in (items or [])
    ]
    if not normalized:
        raise ValueError("PROMOTION_LIST_ITEMS_REQUIRED")

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        cur.execute(
            """INSERT INTO yipman_promotion_list
                 (list_name,source_filename,created_by,status,item_count,ready_count,review_count)
               VALUES (%s,%s,%s,'PROCESSING',%s,0,0)""",
            (name,source_filename,created_by,len(normalized)),
        )
        list_id=int(cur.lastrowid)
        ready=0
        review=0
        seen_ready_families=set()
        for item in normalized:
            mapped=_resolve_family(cur,item.get("raw_item_code"))
            errors=list(item.get("validation_errors") or [])
            status="READY"
            basis=None
            family_id=None
            family_article=None
            family_name=None
            if mapped:
                family_id=int(mapped["family_id"])
                family_article=mapped.get("family_article_number")
                family_name=mapped.get("family_name")
                basis=mapped.get("mapping_basis")
            else:
                errors.append("ITEM_NOT_MAPPED_TO_FAMILY")
            if family_id is not None and family_id in seen_ready_families:
                errors.append("DUPLICATE_FAMILY_IN_PROMOTION_LIST")
            if errors:
                status="REVIEW"
                review+=1
            else:
                ready+=1
                seen_ready_families.add(family_id)
            cur.execute(
                """INSERT INTO yipman_promotion_list_item
                     (list_id,raw_item_code,raw_description,family_id,
                      family_article_number,family_name,promotion_type,
                      promotion_start_date,promotion_end_date,promotion_price,
                      mapping_status,mapping_basis,validation_error)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    list_id,
                    item.get("raw_item_code"),
                    item.get("raw_description"),
                    family_id,
                    family_article,
                    family_name,
                    item.get("promotion_type"),
                    item.get("promotion_start_date"),
                    item.get("promotion_end_date"),
                    item.get("promotion_price"),
                    status,
                    basis,
                    " | ".join(errors) if errors else None,
                ),
            )
        status="READY" if review==0 else ("READY_WITH_REVIEW" if ready else "REVIEW")
        cur.execute(
            """UPDATE yipman_promotion_list
               SET status=%s,ready_count=%s,review_count=%s
               WHERE list_id=%s""",
            (status,ready,review,list_id),
        )
        conn.commit()
        cur.close()
    return get_promotion_list(list_id)


def list_promotion_lists(limit: int=20) -> dict[str,Any]:
    n=max(1,min(int(limit or 20),100))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        conn.commit()
        cur.execute(
            """SELECT * FROM yipman_promotion_list
               ORDER BY list_id DESC
               LIMIT %s""",
            (n,),
        )
        rows=cur.fetchall()
        cur.close()
    return {
        "contract_version":"YIPMAN_PROMOTION_LISTS_V1",
        "count":len(rows),
        "rows":rows,
    }


def get_promotion_list(list_id: int) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        conn.commit()
        cur.execute(
            "SELECT * FROM yipman_promotion_list WHERE list_id=%s LIMIT 1",
            (int(list_id),),
        )
        head=cur.fetchone()
        if not head:
            cur.close()
            raise KeyError("PROMOTION_LIST_NOT_FOUND")
        cur.execute(
            """SELECT * FROM yipman_promotion_list_item
               WHERE list_id=%s
               ORDER BY CASE mapping_status WHEN 'READY' THEN 0 ELSE 1 END,
                        promotion_type,family_name,raw_description,item_id""",
            (int(list_id),),
        )
        items=cur.fetchall()
        cur.close()
    return {
        "contract_version":"YIPMAN_PROMOTION_LIST_V1",
        **head,
        "items":items,
    }


def calculate_promotion_order(
    list_id: int,
    delivery_date: date,
    next_delivery_date: date,
    *,
    temporary_oh_overrides: list[dict[str,Any]]|None=None,
) -> dict[str,Any]:
    if next_delivery_date<=delivery_date:
        raise ValueError("NEXT_DELIVERY_MUST_BE_AFTER_DELIVERY_DATE")
    if delivery_date<business_today():
        raise ValueError("PROMOTION_DELIVERY_DATE_CANNOT_BE_IN_THE_PAST")

    promo=get_promotion_list(int(list_id))
    ready=[x for x in promo.get("items",[]) if x.get("mapping_status")=="READY"]
    if not ready:
        raise ValueError("PROMOTION_LIST_HAS_NO_READY_ITEMS")

    promotion_items=[
        {
            "family_id":int(x["family_id"]),
            "family_article_number":x.get("family_article_number"),
            "promotion_type":x.get("promotion_type"),
            "promotion_start_date":x.get("promotion_start_date"),
            "promotion_end_date":x.get("promotion_end_date"),
            "promotion_price":x.get("promotion_price"),
            "source_item_id":x.get("item_id"),
        }
        for x in ready
    ]
    family_ids={int(x["family_id"]) for x in ready}
    temp=list(temporary_oh_overrides or [])

    results=[]
    skipped=[]
    category_payloads={}
    for kind in ("FRESH","FROZEN"):
        payload=bulk_ordering_suggestions(
            kind,
            ordering_date=business_today(),
            expected_delivery_date=delivery_date,
            next_delivery_date=next_delivery_date,
            include_sufficient_stock=True,
            family_ids=family_ids,
            promotion_involved=True,
            promotion_items=promotion_items,
            temporary_oh_overrides=temp,
        )
        category_payloads[kind]=payload
        results.extend(payload.get("suggestions") or [])
        skipped.extend(payload.get("skipped") or [])

    item_by_family={int(x["family_id"]):x for x in ready}
    for row in results:
        src=item_by_family.get(int(row["family_id"]))
        row["promotion_list_item"]=src
        # Preserve the shared Family inventory semantics explicitly for the UI:
        # Effective OH is the operational stock authority (including saved
        # Family True Stock); System OH remains the independent system position.
        row["current_effective_oh"]=row.get("effective_oh_raw")
        row["current_effective_oh_uom"]=row.get("effective_oh_uom")
        row["current_effective_oh_source"]=row.get("effective_oh_source")
        row["current_oh_system"]=row.get("system_oh_raw")
        row["current_oh_system_uom"]=row.get("system_oh_uom")
        row["current_oh_for_calculation"]=row.get("ordering_oh_used")
        row["coverage_start_date"]=delivery_date
        row["coverage_end_date"]=next_delivery_date-timedelta(days=1)
        row["order_needed"]=bool(_d(row.get("suggested_order_qty") or 0)>0)

    results.sort(
        key=lambda x:(
            0 if x.get("order_needed") else 1,
            -float(x.get("suggested_order_qty") or 0),
            str(x.get("family_article_name") or ""),
        )
    )

    ready_family_ids={int(x["family_id"]) for x in ready}
    returned_family_ids={int(x["family_id"]) for x in results}
    skipped_family_ids={
        int(x["family_id"]) for x in skipped if x.get("family_id") is not None
    }
    unresolved=sorted(ready_family_ids-returned_family_ids-skipped_family_ids)

    return {
        "contract_version":"YIPMAN_PROMOTION_ORDERING_V2_EFFECTIVE_OH",
        "list":{
            "list_id":promo.get("list_id"),
            "list_name":promo.get("list_name"),
            "status":promo.get("status"),
            "ready_count":promo.get("ready_count"),
            "review_count":promo.get("review_count"),
        },
        "calculated_on":business_today(),
        "completed_reference_date":completed_through_date(),
        "delivery_date":delivery_date,
        "next_delivery_date":next_delivery_date,
        "coverage_end_date":next_delivery_date-timedelta(days=1),
        "temporary_oh_override_count":len(temp),
        "suggestion_count":len(results),
        "order_count":sum(1 for x in results if x.get("order_needed")),
        "rows":results,
        "skipped":skipped,
        "unresolved_family_ids":unresolved,
        "rules":{
            "weekly_window":"THURSDAY_TO_FOLLOWING_THURSDAY_INCLUSIVE",
            "weekend_window":"FRIDAY_TO_SUNDAY_INCLUSIVE",
            "forecast_is_day_by_day":True,
            "promo_days_use_matching_promotion_history":True,
            "non_promo_days_use_regular_history":True,
            "family_effective_oh_authority":"SHARED_FAMILY_EFFECTIVE_OH_INCLUDING_ACTIVE_TRUE_STOCK",
            "system_oh_is_separate_reference":True,
            "temporary_oh_is_request_only":True,
            "temporary_oh_persisted":False,
            "regular_order_temporary_oh_enabled":False,
        },
    }


def _norm_header(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+"," ",str(value or "").strip().upper()).strip()


def _sheet_rows_from_upload(filename: str, content: bytes) -> list[list[Any]]:
    name=str(filename or "").lower()
    if name.endswith(".csv"):
        text=content.decode("utf-8-sig",errors="replace")
        return [list(r) for r in csv.reader(io.StringIO(text))]
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        wb=openpyxl.load_workbook(io.BytesIO(content),data_only=True,read_only=True)
        ws=wb.active
        return [list(r) for r in ws.iter_rows(values_only=True)]
    if name.endswith(".xls"):
        book=xlrd.open_workbook(file_contents=content)
        sh=book.sheet_by_index(0)
        rows=[]
        for r in range(sh.nrows):
            vals=[]
            for c in range(sh.ncols):
                cell=sh.cell(r,c)
                if cell.ctype==xlrd.XL_CELL_DATE:
                    vals.append(xlrd.xldate_as_datetime(cell.value,book.datemode))
                else:
                    vals.append(cell.value)
            rows.append(vals)
        return rows
    raise ValueError("PROMOTION_IMPORT_SUPPORTS_CSV_XLS_XLSX")


def parse_promotion_upload(filename: str, content: bytes) -> list[dict[str,Any]]:
    rows=_sheet_rows_from_upload(filename,content)
    if not rows:
        raise ValueError("PROMOTION_FILE_EMPTY")

    aliases={
        "code":{"UPC","EAN","EAN UPC","ITEM","ITEM CODE","SKU","ARTICLE","ARTICLE NUMBER","FAMILY ARTICLE","FAMILY ARTICLE NUMBER"},
        "description":{"DESCRIPTION","ITEM DESCRIPTION","NAME","ITEM NAME","PRODUCT","PRODUCT NAME"},
        "price":{"SALE PRICE","PROMO PRICE","PROMOTION PRICE","PROMOTIONAL PRICE","AD PRICE","PRICE"},
        "type":{"PROMOTION TYPE","PROMO TYPE","TYPE","PROMOTION"},
        "start":{"START","START DATE","PROMO START","PROMOTION START","SALE START"},
        "end":{"END","END DATE","PROMO END","PROMOTION END","SALE END"},
    }
    header_idx=None
    colmap={}
    for idx,row in enumerate(rows[:15]):
        headers=[_norm_header(x) for x in row]
        candidate={}
        for key,values in aliases.items():
            for col,h in enumerate(headers):
                if h in values:
                    candidate[key]=col
                    break
        if "code" in candidate and ("price" in candidate or "description" in candidate):
            header_idx=idx
            colmap=candidate
            break
    if header_idx is None:
        raise ValueError("PROMOTION_IMPORT_HEADER_NOT_RECOGNIZED")

    out=[]
    active_type=None
    for row in rows[header_idx+1:]:
        cells=list(row)
        combined=" ".join(_norm_header(x) for x in cells if x not in (None,""))
        if "WEEKEND" in combined and not any(
            str(cells[colmap.get(k,-1)] if 0<=colmap.get(k,-1)<len(cells) else "").strip()
            for k in ("code","price")
        ):
            active_type="WEEKEND"
            continue
        if "WEEKLY" in combined and not any(
            str(cells[colmap.get(k,-1)] if 0<=colmap.get(k,-1)<len(cells) else "").strip()
            for k in ("code","price")
        ):
            active_type="WEEKLY"
            continue

        def val(key):
            col=colmap.get(key)
            return cells[col] if col is not None and col<len(cells) else None

        code=val("code")
        desc=val("description")
        price=val("price")
        ptype=val("type") or active_type
        start=val("start")
        end=val("end")
        if all(x in (None,"") for x in (code,desc,price,ptype,start,end)):
            continue
        out.append({
            "item_code":code,
            "description":desc,
            "promotion_price":price,
            "promotion_type":ptype,
            "promotion_start_date":start,
            "promotion_end_date":end,
        })
    if not out:
        raise ValueError("PROMOTION_FILE_HAS_NO_ITEM_ROWS")
    return out

                          AND TRIM(LEADING '0' FROM ean_upc)=TRIM(LEADING '0' FROM %s))
                      OR article_number=%s
                      OR main_article_number=%s
                      OR article_number LIKE %s
                      OR main_article_number LIKE %s
                      OR ean_upc LIKE %s
                   ORDER BY search_score DESC,COALESCE(pos_qty_7d,0) DESC,selling_description
                   LIMIT %s""",
                (q,q,q,q,f"{q}%",f"{q}%",f"{q}%",q,q,q,q,f"{q}%",f"{q}%",f"{q}%",max(n*3,30)),
            )
        else:
            like=f"%{upper}%"
            prefix=f"{upper}%"
            cur.execute(
                """SELECT family_id,main_article_number,family_description,
                          ean_upc,article_number,selling_description,selling_uom,
                          quick_check_status,current_price,current_price_type,
                          pos_qty_7d,sales_dollars_7d,
                          CASE
                            WHEN UPPER(COALESCE(selling_description,''))=%s THEN 950
                            WHEN UPPER(COALESCE(family_description,''))=%s THEN 940
                            WHEN UPPER(COALESCE(selling_description,'')) LIKE %s THEN 880
                            WHEN UPPER(COALESCE(family_description,'')) LIKE %s THEN 870
                            ELSE 800
                          END AS search_score
                   FROM quick_check_current
                   WHERE UPPER(COALESCE(selling_description,'')) LIKE %s
                      OR UPPER(COALESCE(family_description,'')) LIKE %s
                   ORDER BY search_score DESC,COALESCE(pos_qty_7d,0) DESC,selling_description
                   LIMIT %s""",
                (upper,upper,prefix,prefix,like,like,max(n*3,30)),
            )
        quick_rows=cur.fetchall()

        for row in quick_rows:
            results.append({
                "result_type":"UPC",
                "number":row.get("ean_upc"),
                "article_number":row.get("article_number"),
                "name":row.get("selling_description") or row.get("family_description"),
                "family_id":row.get("family_id"),
                "family_article_number":row.get("main_article_number"),
                "family_name":row.get("family_description"),
                "selling_uom":row.get("selling_uom"),
                "readiness":row.get("quick_check_status"),
                "current_price":row.get("current_price"),
                "current_price_type":row.get("current_price_type"),
                "pos_qty_7d":row.get("pos_qty_7d"),
                "sales_dollars_7d":row.get("sales_dollars_7d"),
                "matched_as":"SELLING_UPC",
                "search_score":int(row.get("search_score") or 0),
            })

        if numeric:
            cur.execute(
                """SELECT DISTINCT pf.family_id,pf.main_article_number,pf.family_description,
                                  a.article_number,a.article_description
                   FROM article a
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   WHERE a.article_number=%s OR a.article_number LIKE %s
                   ORDER BY CASE WHEN a.article_number=%s THEN 0 ELSE 1 END,
                            a.article_number,pf.family_id
                   LIMIT %s""",
                (q,f"{q}%",q,max(n*2,20)),
            )
        else:
            like=f"%{upper}%"
            cur.execute(
                """SELECT DISTINCT pf.family_id,pf.main_article_number,pf.family_description,
                                  a.article_number,a.article_description
                   FROM article a
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   WHERE UPPER(COALESCE(a.article_description,'')) LIKE %s
                      OR UPPER(COALESCE(pf.family_description,'')) LIKE %s
                   ORDER BY a.article_number,pf.family_id
                   LIMIT %s""",
                (like,like,max(n*2,20)),
            )
        article_rows=cur.fetchall()
        for row in article_rows:
            score=_promo_fuzzy_score(q,row.get("article_number"),row.get("article_description"),row.get("family_description"))
            results.append({
                "result_type":"ARTICLE",
                "number":row.get("article_number"),
                "name":row.get("article_description") or row.get("family_description"),
                "family_id":row.get("family_id"),
                "family_article_number":row.get("main_article_number"),
                "family_name":row.get("family_description"),
                "selling_uom":None,
                "readiness":"READY",
                "current_price":None,
                "current_price_type":None,
                "pos_qty_7d":None,
                "sales_dollars_7d":None,
                "matched_as":"ARTICLE_FAMILY_BRIDGE",
                "search_score":score or 780,
            })

        if not results and not numeric:
            # Typo-tolerant fallback: identity/name columns only. Avoid the generic
            # v2 search's per-result 28D sales aggregation on this mobile workflow.
            cur.execute(
                """SELECT family_id,main_article_number,family_description,
                          ean_upc,article_number,selling_description,selling_uom,
                          quick_check_status,current_price,current_price_type,
                          pos_qty_7d,sales_dollars_7d
                   FROM quick_check_current
                   ORDER BY COALESCE(pos_qty_7d,0) DESC
                   LIMIT 1200"""
            )
            for row in cur.fetchall():
                score=_promo_fuzzy_score(q,row.get("ean_upc"),row.get("article_number"),row.get("selling_description"),row.get("family_description"))
                if score<420:
                    continue
                results.append({
                    "result_type":"UPC",
                    "number":row.get("ean_upc"),
                    "article_number":row.get("article_number"),
                    "name":row.get("selling_description") or row.get("family_description"),
                    "family_id":row.get("family_id"),
                    "family_article_number":row.get("main_article_number"),
                    "family_name":row.get("family_description"),
                    "selling_uom":row.get("selling_uom"),
                    "readiness":row.get("quick_check_status"),
                    "current_price":row.get("current_price"),
                    "current_price_type":row.get("current_price_type"),
                    "pos_qty_7d":row.get("pos_qty_7d"),
                    "sales_dollars_7d":row.get("sales_dollars_7d"),
                    "matched_as":"FUZZY_SELLING_UPC",
                    "search_score":score,
                })
            cur.execute(
                """SELECT DISTINCT pf.family_id,pf.main_article_number,pf.family_description,
                                  a.article_number,a.article_description
                   FROM article a
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   ORDER BY a.article_number
                   LIMIT 2000"""
            )
            for row in cur.fetchall():
                score=_promo_fuzzy_score(q,row.get("article_number"),row.get("article_description"),row.get("family_description"))
                if score<420:
                    continue
                results.append({
                    "result_type":"ARTICLE",
                    "number":row.get("article_number"),
                    "name":row.get("article_description") or row.get("family_description"),
                    "family_id":row.get("family_id"),
                    "family_article_number":row.get("main_article_number"),
                    "family_name":row.get("family_description"),
                    "selling_uom":None,
                    "readiness":"READY",
                    "current_price":None,
                    "current_price_type":None,
                    "pos_qty_7d":None,
                    "sales_dollars_7d":None,
                    "matched_as":"FUZZY_ARTICLE_FAMILY_BRIDGE",
                    "search_score":score,
                })
        cur.close()

    dedup:dict[tuple[str,str,int|None],dict[str,Any]]={}
    for row in results:
        key=(str(row.get("result_type") or ""),str(row.get("number") or ""),int(row["family_id"]) if row.get("family_id") is not None else None)
        current=dedup.get(key)
        if current is None or int(row.get("search_score") or 0)>int(current.get("search_score") or 0):
            dedup[key]=row
    ranked=list(dedup.values())
    ranked.sort(
        key=lambda x:(
            -int(x.get("search_score") or 0),
            -float(x.get("pos_qty_7d") or 0),
            0 if str(x.get("result_type") or "").upper()=="UPC" else 1,
            str(x.get("name") or ""),
        )
    )
    ranked=ranked[:n]
    return {
        "contract_version":"YIPMAN_PROMOTION_ITEM_SEARCH_V1",
        "query":q,
        "count":len(ranked),
        "results":ranked,
        "search_basis":"DIRECT_IDENTITY_NAME_THEN_LIGHTWEIGHT_FUZZY",
    }


def create_promotion_list(
    list_name: str,
    items: list[dict[str,Any]],
    *,
    weekly_start_date: date | None=None,
    weekend_start_date: date | None=None,
    source_filename: str | None=None,
    created_by: str | None=None,
) -> dict[str,Any]:
    name=str(list_name or "").strip() or "Promotion List"
    normalized=[
        _normalize_item(
            x,
            weekly_start_date=weekly_start_date,
            weekend_start_date=weekend_start_date,
        )
        for x in (items or [])
    ]
    if not normalized:
        raise ValueError("PROMOTION_LIST_ITEMS_REQUIRED")

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        cur.execute(
            """INSERT INTO yipman_promotion_list
                 (list_name,source_filename,created_by,status,item_count,ready_count,review_count)
               VALUES (%s,%s,%s,'PROCESSING',%s,0,0)""",
            (name,source_filename,created_by,len(normalized)),
        )
        list_id=int(cur.lastrowid)
        ready=0
        review=0
        seen_ready_families=set()
        for item in normalized:
            mapped=_resolve_family(cur,item.get("raw_item_code"))
            errors=list(item.get("validation_errors") or [])
            status="READY"
            basis=None
            family_id=None
            family_article=None
            family_name=None
            if mapped:
                family_id=int(mapped["family_id"])
                family_article=mapped.get("family_article_number")
                family_name=mapped.get("family_name")
                basis=mapped.get("mapping_basis")
            else:
                errors.append("ITEM_NOT_MAPPED_TO_FAMILY")
            if family_id is not None and family_id in seen_ready_families:
                errors.append("DUPLICATE_FAMILY_IN_PROMOTION_LIST")
            if errors:
                status="REVIEW"
                review+=1
            else:
                ready+=1
                seen_ready_families.add(family_id)
            cur.execute(
                """INSERT INTO yipman_promotion_list_item
                     (list_id,raw_item_code,raw_description,family_id,
                      family_article_number,family_name,promotion_type,
                      promotion_start_date,promotion_end_date,promotion_price,
                      mapping_status,mapping_basis,validation_error)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    list_id,
                    item.get("raw_item_code"),
                    item.get("raw_description"),
                    family_id,
                    family_article,
                    family_name,
                    item.get("promotion_type"),
                    item.get("promotion_start_date"),
                    item.get("promotion_end_date"),
                    item.get("promotion_price"),
                    status,
                    basis,
                    " | ".join(errors) if errors else None,
                ),
            )
        status="READY" if review==0 else ("READY_WITH_REVIEW" if ready else "REVIEW")
        cur.execute(
            """UPDATE yipman_promotion_list
               SET status=%s,ready_count=%s,review_count=%s
               WHERE list_id=%s""",
            (status,ready,review,list_id),
        )
        conn.commit()
        cur.close()
    return get_promotion_list(list_id)


def list_promotion_lists(limit: int=20) -> dict[str,Any]:
    n=max(1,min(int(limit or 20),100))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        conn.commit()
        cur.execute(
            """SELECT * FROM yipman_promotion_list
               ORDER BY list_id DESC
               LIMIT %s""",
            (n,),
        )
        rows=cur.fetchall()
        cur.close()
    return {
        "contract_version":"YIPMAN_PROMOTION_LISTS_V1",
        "count":len(rows),
        "rows":rows,
    }


def get_promotion_list(list_id: int) -> dict[str,Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        _ensure_tables(cur)
        conn.commit()
        cur.execute(
            "SELECT * FROM yipman_promotion_list WHERE list_id=%s LIMIT 1",
            (int(list_id),),
        )
        head=cur.fetchone()
        if not head:
            cur.close()
            raise KeyError("PROMOTION_LIST_NOT_FOUND")
        cur.execute(
            """SELECT * FROM yipman_promotion_list_item
               WHERE list_id=%s
               ORDER BY CASE mapping_status WHEN 'READY' THEN 0 ELSE 1 END,
                        promotion_type,family_name,raw_description,item_id""",
            (int(list_id),),
        )
        items=cur.fetchall()
        cur.close()
    return {
        "contract_version":"YIPMAN_PROMOTION_LIST_V1",
        **head,
        "items":items,
    }


def calculate_promotion_order(
    list_id: int,
    delivery_date: date,
    next_delivery_date: date,
    *,
    temporary_oh_overrides: list[dict[str,Any]]|None=None,
) -> dict[str,Any]:
    if next_delivery_date<=delivery_date:
        raise ValueError("NEXT_DELIVERY_MUST_BE_AFTER_DELIVERY_DATE")
    if delivery_date<business_today():
        raise ValueError("PROMOTION_DELIVERY_DATE_CANNOT_BE_IN_THE_PAST")

    promo=get_promotion_list(int(list_id))
    ready=[x for x in promo.get("items",[]) if x.get("mapping_status")=="READY"]
    if not ready:
        raise ValueError("PROMOTION_LIST_HAS_NO_READY_ITEMS")

    promotion_items=[
        {
            "family_id":int(x["family_id"]),
            "family_article_number":x.get("family_article_number"),
            "promotion_type":x.get("promotion_type"),
            "promotion_start_date":x.get("promotion_start_date"),
            "promotion_end_date":x.get("promotion_end_date"),
            "promotion_price":x.get("promotion_price"),
            "source_item_id":x.get("item_id"),
        }
        for x in ready
    ]
    family_ids={int(x["family_id"]) for x in ready}
    temp=list(temporary_oh_overrides or [])

    results=[]
    skipped=[]
    category_payloads={}
    for kind in ("FRESH","FROZEN"):
        payload=bulk_ordering_suggestions(
            kind,
            ordering_date=business_today(),
            expected_delivery_date=delivery_date,
            next_delivery_date=next_delivery_date,
            include_sufficient_stock=True,
            family_ids=family_ids,
            promotion_involved=True,
            promotion_items=promotion_items,
            temporary_oh_overrides=temp,
        )
        category_payloads[kind]=payload
        results.extend(payload.get("suggestions") or [])
        skipped.extend(payload.get("skipped") or [])

    item_by_family={int(x["family_id"]):x for x in ready}
    for row in results:
        src=item_by_family.get(int(row["family_id"]))
        row["promotion_list_item"]=src
        # Preserve the shared Family inventory semantics explicitly for the UI:
        # Effective OH is the operational stock authority (including saved
        # Family True Stock); System OH remains the independent system position.
        row["current_effective_oh"]=row.get("effective_oh_raw")
        row["current_effective_oh_uom"]=row.get("effective_oh_uom")
        row["current_effective_oh_source"]=row.get("effective_oh_source")
        row["current_oh_system"]=row.get("system_oh_raw")
        row["current_oh_system_uom"]=row.get("system_oh_uom")
        row["current_oh_for_calculation"]=row.get("ordering_oh_used")
        row["coverage_start_date"]=delivery_date
        row["coverage_end_date"]=next_delivery_date-timedelta(days=1)
        row["order_needed"]=bool(_d(row.get("suggested_order_qty") or 0)>0)

    results.sort(
        key=lambda x:(
            0 if x.get("order_needed") else 1,
            -float(x.get("suggested_order_qty") or 0),
            str(x.get("family_article_name") or ""),
        )
    )

    ready_family_ids={int(x["family_id"]) for x in ready}
    returned_family_ids={int(x["family_id"]) for x in results}
    skipped_family_ids={
        int(x["family_id"]) for x in skipped if x.get("family_id") is not None
    }
    unresolved=sorted(ready_family_ids-returned_family_ids-skipped_family_ids)

    return {
        "contract_version":"YIPMAN_PROMOTION_ORDERING_V2_EFFECTIVE_OH",
        "list":{
            "list_id":promo.get("list_id"),
            "list_name":promo.get("list_name"),
            "status":promo.get("status"),
            "ready_count":promo.get("ready_count"),
            "review_count":promo.get("review_count"),
        },
        "calculated_on":business_today(),
        "completed_reference_date":completed_through_date(),
        "delivery_date":delivery_date,
        "next_delivery_date":next_delivery_date,
        "coverage_end_date":next_delivery_date-timedelta(days=1),
        "temporary_oh_override_count":len(temp),
        "suggestion_count":len(results),
        "order_count":sum(1 for x in results if x.get("order_needed")),
        "rows":results,
        "skipped":skipped,
        "unresolved_family_ids":unresolved,
        "rules":{
            "weekly_window":"THURSDAY_TO_FOLLOWING_THURSDAY_INCLUSIVE",
            "weekend_window":"FRIDAY_TO_SUNDAY_INCLUSIVE",
            "forecast_is_day_by_day":True,
            "promo_days_use_matching_promotion_history":True,
            "non_promo_days_use_regular_history":True,
            "family_effective_oh_authority":"SHARED_FAMILY_EFFECTIVE_OH_INCLUDING_ACTIVE_TRUE_STOCK",
            "system_oh_is_separate_reference":True,
            "temporary_oh_is_request_only":True,
            "temporary_oh_persisted":False,
            "regular_order_temporary_oh_enabled":False,
        },
    }


def _norm_header(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+"," ",str(value or "").strip().upper()).strip()


def _sheet_rows_from_upload(filename: str, content: bytes) -> list[list[Any]]:
    name=str(filename or "").lower()
    if name.endswith(".csv"):
        text=content.decode("utf-8-sig",errors="replace")
        return [list(r) for r in csv.reader(io.StringIO(text))]
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        wb=openpyxl.load_workbook(io.BytesIO(content),data_only=True,read_only=True)
        ws=wb.active
        return [list(r) for r in ws.iter_rows(values_only=True)]
    if name.endswith(".xls"):
        book=xlrd.open_workbook(file_contents=content)
        sh=book.sheet_by_index(0)
        rows=[]
        for r in range(sh.nrows):
            vals=[]
            for c in range(sh.ncols):
                cell=sh.cell(r,c)
                if cell.ctype==xlrd.XL_CELL_DATE:
                    vals.append(xlrd.xldate_as_datetime(cell.value,book.datemode))
                else:
                    vals.append(cell.value)
            rows.append(vals)
        return rows
    raise ValueError("PROMOTION_IMPORT_SUPPORTS_CSV_XLS_XLSX")


def parse_promotion_upload(filename: str, content: bytes) -> list[dict[str,Any]]:
    rows=_sheet_rows_from_upload(filename,content)
    if not rows:
        raise ValueError("PROMOTION_FILE_EMPTY")

    aliases={
        "code":{"UPC","EAN","EAN UPC","ITEM","ITEM CODE","SKU","ARTICLE","ARTICLE NUMBER","FAMILY ARTICLE","FAMILY ARTICLE NUMBER"},
        "description":{"DESCRIPTION","ITEM DESCRIPTION","NAME","ITEM NAME","PRODUCT","PRODUCT NAME"},
        "price":{"SALE PRICE","PROMO PRICE","PROMOTION PRICE","PROMOTIONAL PRICE","AD PRICE","PRICE"},
        "type":{"PROMOTION TYPE","PROMO TYPE","TYPE","PROMOTION"},
        "start":{"START","START DATE","PROMO START","PROMOTION START","SALE START"},
        "end":{"END","END DATE","PROMO END","PROMOTION END","SALE END"},
    }
    header_idx=None
    colmap={}
    for idx,row in enumerate(rows[:15]):
        headers=[_norm_header(x) for x in row]
        candidate={}
        for key,values in aliases.items():
            for col,h in enumerate(headers):
                if h in values:
                    candidate[key]=col
                    break
        if "code" in candidate and ("price" in candidate or "description" in candidate):
            header_idx=idx
            colmap=candidate
            break
    if header_idx is None:
        raise ValueError("PROMOTION_IMPORT_HEADER_NOT_RECOGNIZED")

    out=[]
    active_type=None
    for row in rows[header_idx+1:]:
        cells=list(row)
        combined=" ".join(_norm_header(x) for x in cells if x not in (None,""))
        if "WEEKEND" in combined and not any(
            str(cells[colmap.get(k,-1)] if 0<=colmap.get(k,-1)<len(cells) else "").strip()
            for k in ("code","price")
        ):
            active_type="WEEKEND"
            continue
        if "WEEKLY" in combined and not any(
            str(cells[colmap.get(k,-1)] if 0<=colmap.get(k,-1)<len(cells) else "").strip()
            for k in ("code","price")
        ):
            active_type="WEEKLY"
            continue

        def val(key):
            col=colmap.get(key)
            return cells[col] if col is not None and col<len(cells) else None

        code=val("code")
        desc=val("description")
        price=val("price")
        ptype=val("type") or active_type
        start=val("start")
        end=val("end")
        if all(x in (None,"") for x in (code,desc,price,ptype,start,end)):
            continue
        out.append({
            "item_code":code,
            "description":desc,
            "promotion_price":price,
            "promotion_type":ptype,
            "promotion_start_date":start,
            "promotion_end_date":end,
        })
    if not out:
        raise ValueError("PROMOTION_FILE_HAS_NO_ITEM_ROWS")
    return out
