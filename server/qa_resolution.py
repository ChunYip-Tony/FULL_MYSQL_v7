from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from db import db_conn
from manual_overrides import (
    ensure_override_table,
    apply_manual_upc_overrides,
    ensure_cost_conversion_table,
    apply_manual_cost_conversions,
    ensure_article_family_override_table,
    apply_manual_article_family_overrides,
)
from phase3 import relink_history, refresh_quick_check_subset


FIXABLE_IDENTITY_CODES = {
    "SOLD_UPC_UNMAPPED",
    "SOLD_UPC_UNMAPPED_EVIDENCE",
    "CURRENT_ACTIVE_SOLD_UPC_UNMAPPED",
    "ACTIVE_UPC_WITHOUT_AUTHORITATIVE_IDENTITY",
    "SERVING_IDENTITY_NOT_AUTHORITATIVE",
    "MANUAL_UPC_OVERRIDE_NOT_ENFORCED",
}

UOM_TOKENS = (
    "SELLING_UOM_MISSING",
    "CURRENT_ACTIVE_SELLING_UOM_MISSING",
    "UOM_MISSING",
)


def _json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        obj = json.loads(value)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _ensure_resolution_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS qa_manual_resolution (
            resolution_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            issue_id BIGINT UNSIGNED NULL,
            batch_id BIGINT UNSIGNED NULL,
            issue_code VARCHAR(96) NULL,
            entity_type VARCHAR(64) NULL,
            entity_key VARCHAR(128) NULL,
            resolution_kind VARCHAR(64) NOT NULL,
            actor VARCHAR(128) NOT NULL,
            resolution_note VARCHAR(512) NULL,
            before_json JSON NULL,
            applied_json JSON NULL,
            after_json JSON NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (resolution_id),
            KEY ix_qa_manual_resolution_issue (issue_id),
            KEY ix_qa_manual_resolution_entity (entity_type,entity_key),
            KEY ix_qa_manual_resolution_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def _latest_phase3_batch(cur) -> int | None:
    cur.execute("SELECT MAX(batch_id) AS batch_id FROM phase3_batch_result")
    row = cur.fetchone() or {}
    return int(row["batch_id"]) if row.get("batch_id") is not None else None


def _pipeline_busy(cur) -> bool:
    cur.execute(
        """SELECT 1
           FROM pipeline_run
           WHERE stage_name='POST_RAW_PIPELINE'
             AND processing_status='STARTED'
           LIMIT 1"""
    )
    return bool(cur.fetchone())


def _serving_row(cur, ean_upc: str) -> dict[str, Any] | None:
    cur.execute(
        """SELECT ean_upc,selling_description,article_number,main_article_number,
                  family_id,quick_check_status,blocking_reason,selling_uom,
                  base_uom,base_qty_per_selling_unit,current_cost_per_selling_unit,
                  current_price,pos_qty_7d,pos_qty_30d
           FROM quick_check_current
           WHERE ean_upc=%s
           LIMIT 1""",
        (str(ean_upc),),
    )
    return cur.fetchone()


def _active_identity(cur, ean_upc: str) -> dict[str, Any] | None:
    cur.execute(
        """SELECT su.ean_upc,a.article_number,pf.family_id,pf.main_article_number,
                  du.uom_code AS selling_uom,bu.uom_code AS base_uom,
                  uh.base_qty_per_selling_unit
           FROM selling_upc su
           LEFT JOIN bridge_article_upc bau
             ON bau.upc_id=su.upc_id
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
        (str(ean_upc),),
    )
    return cur.fetchone()


def _fix_kind(issue_code: str, summary: str, detail: dict[str, Any]) -> str:
    code = str(issue_code or "").upper()
    detail = detail or {}
    explicit_reasons = {
        str(x or "").strip().upper()
        for x in (detail.get("reasons") or [])
        if str(x or "").strip()
    }
    blob = " ".join(
        [
            code,
            str(summary or ""),
            json.dumps(detail, ensure_ascii=False, default=str),
        ]
    ).upper()

    # Selling UOM is always the first fix when it is missing. Do not let the
    # simultaneous cost-conversion blocker downgrade the row to a disabled
    # conversion workflow.
    if (
        "SELLING_UOM_MISSING" in explicit_reasons
        or "CURRENT_ACTIVE_SELLING_UOM_MISSING" in explicit_reasons
        or any(token in blob for token in UOM_TOKENS)
    ):
        return "UOM_OR_IDENTITY"

    if (
        "COST_TO_SELLING_UOM_UNRESOLVED" in explicit_reasons
        or "COST_TO_SELLING_UOM_UNRESOLVED" in blob
    ):
        return "COST_CONVERSION"

    if code == "SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED":
        return "ARTICLE_FAMILY_MAPPING"

    if code in FIXABLE_IDENTITY_CODES:
        return "IDENTITY_AND_UOM"
    return "VIEW_ONLY"


def qa_review(limit: int = 250) -> dict[str, Any]:
    limit = max(1, min(int(limit or 250), 500))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        batch_id = _latest_phase3_batch(cur)
        issues: list[dict[str, Any]] = []

        if batch_id is not None:
            cur.execute(
                """SELECT issue_id,batch_id,severity,issue_code,entity_type,entity_key,
                          issue_summary,detail_json,issue_status,file_id,sheet_id,
                          raw_table_name,raw_id
                   FROM qa_phase3_issue
                   WHERE batch_id=%s
                     AND issue_status='OPEN'
                   ORDER BY FIELD(UPPER(severity),'CRITICAL','HIGH','MEDIUM','LOW'),
                            issue_id
                   LIMIT %s""",
                (batch_id, limit),
            )
            for row in cur.fetchall():
                detail = _json(row.get("detail_json"))
                entity_key = str(row.get("entity_key") or "")
                serving = _serving_row(cur, entity_key) if row.get("entity_type") == "UPC" else None
                active = _active_identity(cur, entity_key) if row.get("entity_type") == "UPC" else None
                kind = _fix_kind(row.get("issue_code"), row.get("issue_summary"), detail)
                issues.append(
                    {
                        "issue_id": int(row["issue_id"]),
                        "batch_id": int(row["batch_id"]),
                        "severity": row.get("severity"),
                        "issue_code": row.get("issue_code"),
                        "entity_type": row.get("entity_type"),
                        "entity_key": entity_key,
                        "issue_summary": row.get("issue_summary"),
                        "detail": detail,
                        "fix_kind": kind,
                        "can_fix": kind != "VIEW_ONLY",
                        "current": serving or active,
                    }
                )

        # Serving QA_HOLD rows can exist without a one-to-one current Phase-3 issue.
        cur.execute(
            """SELECT ean_upc,selling_description,article_number,main_article_number,
                      family_id,quick_check_status,blocking_reason,selling_uom,
                      base_uom,base_qty_per_selling_unit
               FROM quick_check_current
               WHERE quick_check_status='QA_HOLD'
               ORDER BY COALESCE(pos_qty_7d,0) DESC,ean_upc
               LIMIT %s""",
            (limit,),
        )
        existing_upc_issue_keys = {
            str(x["entity_key"])
            for x in issues
            if x.get("entity_type") == "UPC"
        }
        for row in cur.fetchall():
            ean = str(row["ean_upc"])
            if ean in existing_upc_issue_keys:
                continue
            reason = str(row.get("blocking_reason") or "QUICK_CHECK_QA_HOLD")
            kind = _fix_kind(reason, reason, {})
            issues.append(
                {
                    "issue_id": None,
                    "batch_id": batch_id,
                    "severity": "MEDIUM",
                    "issue_code": reason.split("|", 1)[0][:96],
                    "entity_type": "UPC",
                    "entity_key": ean,
                    "issue_summary": reason,
                    "detail": {"source": "quick_check_current"},
                    "fix_kind": kind,
                    "can_fix": kind != "VIEW_ONLY",
                    "current": row,
                }
            )

        history = []
        if _table_exists(cur, "qa_manual_resolution"):
            cur.execute(
                """SELECT resolution_id,issue_id,batch_id,issue_code,entity_type,entity_key,
                          resolution_kind,actor,resolution_note,created_at
                   FROM qa_manual_resolution
                   ORDER BY resolution_id DESC
                   LIMIT 50"""
            )
            history = cur.fetchall()
        cur.close()

    return {
        "contract_version": "BACKOFFICE_QA_REVIEW_V1",
        "batch_id": batch_id,
        "issue_count": len(issues),
        "fixable_count": sum(1 for x in issues if x.get("can_fix")),
        "issues": issues,
        "resolution_history": history,
        "rules": {
            "raw_source_rows_editable": False,
            "allowed_resolution_write": "USER_CONFIRMED_UPC_IDENTITY_UOM_OVERRIDE_ONLY",
            "price_cost_sales_receipts_editable": False,
            "requires_confirmation": "APPLY_QA_FIX",
        },
    }


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        """SELECT 1
           FROM information_schema.tables
           WHERE table_schema=DATABASE() AND table_name=%s
           LIMIT 1""",
        (table,),
    )
    return bool(cur.fetchone())


def resolve_qa_issue(
    *,
    issue_id: int | None,
    ean_upc: str,
    article_number: str | None,
    selling_uom: str,
    base_uom: str | None,
    base_qty_per_selling_unit: Any,
    note: str | None,
    actor: str,
    confirm: str,
) -> dict[str, Any]:
    if confirm != "APPLY_QA_FIX":
        raise ValueError("CONFIRM_MUST_BE_APPLY_QA_FIX")

    ean = str(ean_upc or "").strip()
    article = str(article_number or "").strip()
    sell = str(selling_uom or "").strip().upper()
    base = str(base_uom or "").strip().upper() or None
    if not ean:
        raise ValueError("EAN_UPC_REQUIRED")
    if not sell:
        raise ValueError("SELLING_UOM_REQUIRED")

    factor = None
    if base_qty_per_selling_unit not in (None, ""):
        try:
            factor = Decimal(str(base_qty_per_selling_unit))
        except (InvalidOperation, ValueError):
            raise ValueError("BASE_QTY_PER_SELLING_UNIT_INVALID")
        if factor <= 0:
            raise ValueError("BASE_QTY_PER_SELLING_UNIT_MUST_BE_POSITIVE")
    if base and factor is None:
        raise ValueError("BASE_UOM_REQUIRES_BASE_QTY_PER_SELLING_UNIT")
    if factor is not None and not base:
        raise ValueError("BASE_QTY_PER_SELLING_UNIT_REQUIRES_BASE_UOM")

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_override_table(cur)
        _ensure_resolution_table(cur)
        conn.commit()

        if _pipeline_busy(cur):
            cur.close()
            raise RuntimeError("PIPELINE_BUSY_RETRY_AFTER_ACTIVE_BATCH_FINISHES")

        current = _serving_row(cur, ean) or _active_identity(cur, ean) or {}
        if not article:
            article = str(
                current.get("article_number")
                or current.get("main_article_number")
                or ""
            ).strip()
        if not article:
            cur.close()
            raise ValueError("ARTICLE_NUMBER_REQUIRED_FOR_UNMAPPED_UPC")

        issue_row = None
        if issue_id is not None:
            cur.execute(
                """SELECT issue_id,batch_id,severity,issue_code,entity_type,entity_key,
                          issue_summary,detail_json,issue_status
                   FROM qa_phase3_issue
                   WHERE issue_id=%s
                   LIMIT 1""",
                (int(issue_id),),
            )
            issue_row = cur.fetchone()
            if not issue_row:
                cur.close()
                raise ValueError("QA_ISSUE_NOT_FOUND")
            if str(issue_row.get("issue_status") or "").upper() != "OPEN":
                cur.close()
                raise ValueError("QA_ISSUE_NOT_OPEN")
            if str(issue_row.get("entity_type") or "").upper() == "UPC":
                if str(issue_row.get("entity_key") or "") != ean:
                    cur.close()
                    raise ValueError("QA_ISSUE_ENTITY_MISMATCH")

        # Validate UOM codes before any business write.
        cur.execute("SELECT uom_code FROM dim_uom WHERE UPPER(uom_code)=UPPER(%s) LIMIT 1", (sell,))
        if not cur.fetchone():
            cur.close()
            raise ValueError("SELLING_UOM_NOT_IN_DIM_UOM")
        if base:
            cur.execute("SELECT uom_code FROM dim_uom WHERE UPPER(uom_code)=UPPER(%s) LIMIT 1", (base,))
            if not cur.fetchone():
                cur.close()
                raise ValueError("BASE_UOM_NOT_IN_DIM_UOM")

        batch_id = _latest_phase3_batch(cur)
        if batch_id is None:
            cur.close()
            raise RuntimeError("NO_PHASE3_BATCH_AVAILABLE_FOR_TARGETED_REFRESH")

        before = {
            "serving": current,
            "issue": issue_row,
        }
        source_note = (
            "BACKOFFICE_QA_USER_CONFIRMED: "
            + (str(note or "").strip() or "User confirmed QA resolution")
        )[:512]

        conn.start_transaction()
        try:
            cur.execute(
                """INSERT INTO manual_upc_override
                     (ean_upc,article_number,selling_uom_code,base_uom_code,
                      base_qty_per_selling_unit,override_status,source_note)
                   VALUES (%s,%s,%s,%s,%s,'CONFIRMED',%s)
                   ON DUPLICATE KEY UPDATE
                     article_number=VALUES(article_number),
                     selling_uom_code=VALUES(selling_uom_code),
                     base_uom_code=VALUES(base_uom_code),
                     base_qty_per_selling_unit=VALUES(base_qty_per_selling_unit),
                     override_status='CONFIRMED',
                     source_note=VALUES(source_note)""",
                (ean, article, sell, base, factor, source_note),
            )

            applied = apply_manual_upc_overrides(cur)
            target_holds = [
                x for x in (applied.get("held") or [])
                if str(x.get("ean_upc") or "") == ean
            ]
            if target_holds:
                raise RuntimeError("TARGET_OVERRIDE_HELD: " + json.dumps(target_holds, default=str))

            relink_history(cur)

            cur.execute(
                """SELECT pf.family_id
                   FROM selling_upc su
                   JOIN bridge_article_upc bau
                     ON bau.upc_id=su.upc_id
                    AND bau.mapping_status='CONFIRMED'
                    AND bau.is_primary=TRUE
                    AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN article a ON a.article_id=bau.article_id
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND baf.is_primary=TRUE
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   WHERE su.ean_upc=%s
                   LIMIT 1""",
                (ean,),
            )
            family_row = cur.fetchone()
            family_id = int(family_row["family_id"]) if family_row else None

            refreshed = refresh_quick_check_subset(
                cur,
                batch_id,
                family_ids=[family_id] if family_id is not None else None,
                upcs=[ean],
            )

            after = _serving_row(cur, ean) or _active_identity(cur, ean) or {}

            if issue_id is not None:
                cur.execute(
                    """UPDATE qa_phase3_issue
                       SET issue_status='RESOLVED',
                           detail_json=JSON_SET(
                             COALESCE(detail_json,JSON_OBJECT()),
                             '$.manual_resolution',
                             CAST(%s AS JSON)
                           )
                       WHERE issue_id=%s
                         AND issue_status='OPEN'""",
                    (
                        json.dumps(
                            {
                                "actor": actor,
                                "note": note,
                                "resolution_kind": "USER_CONFIRMED_IDENTITY_UOM_OVERRIDE",
                                "ean_upc": ean,
                                "article_number": article,
                                "selling_uom": sell,
                                "base_uom": base,
                                "base_qty_per_selling_unit": str(factor) if factor is not None else None,
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                        int(issue_id),
                    ),
                )

            cur.execute(
                """INSERT INTO qa_manual_resolution
                     (issue_id,batch_id,issue_code,entity_type,entity_key,
                      resolution_kind,actor,resolution_note,before_json,applied_json,after_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    int(issue_id) if issue_id is not None else None,
                    int(issue_row["batch_id"]) if issue_row and issue_row.get("batch_id") is not None else batch_id,
                    issue_row.get("issue_code") if issue_row else "QUICK_CHECK_QA_HOLD",
                    issue_row.get("entity_type") if issue_row else "UPC",
                    issue_row.get("entity_key") if issue_row else ean,
                    "USER_CONFIRMED_IDENTITY_UOM_OVERRIDE",
                    actor,
                    str(note or "")[:512] or None,
                    json.dumps(before, ensure_ascii=False, default=str),
                    json.dumps(
                        {
                            "ean_upc": ean,
                            "article_number": article,
                            "selling_uom": sell,
                            "base_uom": base,
                            "base_qty_per_selling_unit": str(factor) if factor is not None else None,
                            "targeted_refresh": refreshed,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                    json.dumps(after, ensure_ascii=False, default=str),
                ),
            )
            resolution_id = int(cur.lastrowid)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    return {
        "status": "APPLIED",
        "resolution_id": resolution_id,
        "ean_upc": ean,
        "article_number": article,
        "selling_uom": sell,
        "base_uom": base,
        "base_qty_per_selling_unit": str(factor) if factor is not None else None,
        "after": after,
        "rules": {
            "raw_source_rows_modified": False,
            "write_scope": "USER_CONFIRMED_UPC_IDENTITY_UOM_OVERRIDE",
            "targeted_quick_check_refreshed": True,
        },
    }


def resolve_cost_conversion_issue(
    *,
    issue_id: int | None,
    ean_upc: str,
    selling_qty: Any,
    selling_uom: str,
    cost_qty: Any,
    cost_uom: str,
    note: str | None,
    actor: str,
    confirm: str,
) -> dict[str, Any]:
    """Store an exact user-confirmed cost-to-selling conversion.

    This never edits source cost, sales, receipts, or RAW rows. It only records
    the conversion authority needed to express an already-authoritative cost in
    the UPC's selling unit, then refreshes the affected Quick Check row.
    """
    if confirm != "APPLY_COST_CONVERSION_FIX":
        raise ValueError("CONFIRM_MUST_BE_APPLY_COST_CONVERSION_FIX")

    ean = str(ean_upc or "").strip()
    sell = str(selling_uom or "").strip().upper()
    cuom = str(cost_uom or "").strip().upper()
    if not ean:
        raise ValueError("EAN_UPC_REQUIRED")
    if not sell:
        raise ValueError("SELLING_UOM_REQUIRED")
    if not cuom:
        raise ValueError("COST_UOM_REQUIRED")
    try:
        sq = Decimal(str(selling_qty))
        cq = Decimal(str(cost_qty))
    except (InvalidOperation, ValueError):
        raise ValueError("CONVERSION_QUANTITY_INVALID")
    if sq <= 0 or cq <= 0:
        raise ValueError("CONVERSION_QUANTITIES_MUST_BE_POSITIVE")

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_cost_conversion_table(cur)
        _ensure_resolution_table(cur)
        conn.commit()

        if _pipeline_busy(cur):
            cur.close()
            raise RuntimeError("PIPELINE_BUSY_RETRY_AFTER_ACTIVE_BATCH_FINISHES")

        current = _serving_row(cur, ean) or _active_identity(cur, ean) or {}
        current_sell = str(current.get("selling_uom") or "").strip().upper()
        if current_sell and current_sell in {"PAC","PACK"}:
            current_sell = "PACK"
        input_sell = "PACK" if sell in {"PAC","PACK"} else sell
        if current_sell and current_sell != input_sell:
            cur.close()
            raise ValueError(
                f"SELLING_UOM_MISMATCH_CURRENT:{current.get('selling_uom')}"
            )

        cur.execute("SELECT uom_code FROM dim_uom WHERE UPPER(uom_code)=UPPER(%s) LIMIT 1", (sell,))
        if not cur.fetchone():
            cur.close()
            raise ValueError("SELLING_UOM_NOT_IN_DIM_UOM")
        cur.execute("SELECT uom_code FROM dim_uom WHERE UPPER(uom_code)=UPPER(%s) LIMIT 1", (cuom,))
        if not cur.fetchone():
            cur.close()
            raise ValueError("COST_UOM_NOT_IN_DIM_UOM")

        issue_row = None
        if issue_id is not None:
            cur.execute(
                """SELECT issue_id,batch_id,issue_code,entity_type,entity_key,
                          issue_summary,detail_json,issue_status
                   FROM qa_phase3_issue
                   WHERE issue_id=%s
                   LIMIT 1""",
                (int(issue_id),),
            )
            issue_row = cur.fetchone()
            if not issue_row:
                cur.close()
                raise ValueError("QA_ISSUE_NOT_FOUND")
            if str(issue_row.get("issue_status") or "").upper() != "OPEN":
                cur.close()
                raise ValueError("QA_ISSUE_NOT_OPEN")
            if str(issue_row.get("entity_type") or "").upper() == "UPC" and str(issue_row.get("entity_key") or "") != ean:
                cur.close()
                raise ValueError("QA_ISSUE_ENTITY_MISMATCH")

        batch_id = _latest_phase3_batch(cur)
        if batch_id is None:
            cur.close()
            raise RuntimeError("NO_PHASE3_BATCH_AVAILABLE_FOR_TARGETED_REFRESH")

        before = {"serving": current, "issue": issue_row}
        source_note = (
            "BACKOFFICE_QA_USER_CONFIRMED_COST_CONVERSION: "
            + (str(note or "").strip() or "User confirmed cost-to-selling conversion")
        )[:512]

        conn.start_transaction()
        try:
            cur.execute(
                """INSERT INTO manual_cost_selling_conversion
                     (ean_upc,selling_qty,selling_uom_code,cost_qty,cost_uom_code,
                      conversion_status,source_note)
                   VALUES (%s,%s,%s,%s,%s,'CONFIRMED',%s)
                   ON DUPLICATE KEY UPDATE
                     selling_qty=VALUES(selling_qty),
                     selling_uom_code=VALUES(selling_uom_code),
                     cost_qty=VALUES(cost_qty),
                     cost_uom_code=VALUES(cost_uom_code),
                     conversion_status='CONFIRMED',
                     source_note=VALUES(source_note)""",
                (ean, sq, sell, cq, cuom, source_note),
            )

            checked = apply_manual_cost_conversions(cur)
            target_holds = [
                x for x in (checked.get("held") or [])
                if str(x.get("ean_upc") or "") == ean
            ]
            if target_holds:
                raise RuntimeError("TARGET_COST_CONVERSION_HELD: " + json.dumps(target_holds, default=str))

            cur.execute(
                """SELECT pf.family_id
                   FROM selling_upc su
                   JOIN bridge_article_upc bau
                     ON bau.upc_id=su.upc_id
                    AND bau.mapping_status='CONFIRMED'
                    AND bau.is_primary=TRUE
                    AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN article a ON a.article_id=bau.article_id
                   JOIN bridge_article_family baf
                     ON baf.article_id=a.article_id
                    AND baf.mapping_status='CONFIRMED'
                    AND baf.is_primary=TRUE
                    AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   JOIN product_family pf ON pf.family_id=baf.family_id
                   WHERE su.ean_upc=%s
                   LIMIT 1""",
                (ean,),
            )
            family_row = cur.fetchone()
            family_id = int(family_row["family_id"]) if family_row else None

            refreshed = refresh_quick_check_subset(
                cur,
                batch_id,
                family_ids=[family_id] if family_id is not None else None,
                upcs=[ean],
            )
            after = _serving_row(cur, ean) or _active_identity(cur, ean) or {}

            if issue_id is not None:
                cur.execute(
                    """UPDATE qa_phase3_issue
                       SET issue_status='RESOLVED',
                           detail_json=JSON_SET(
                             COALESCE(detail_json,JSON_OBJECT()),
                             '$.manual_resolution',
                             CAST(%s AS JSON)
                           )
                       WHERE issue_id=%s
                         AND issue_status='OPEN'""",
                    (
                        json.dumps({
                            "actor": actor,
                            "note": note,
                            "resolution_kind": "USER_CONFIRMED_COST_CONVERSION",
                            "ean_upc": ean,
                            "selling_qty": str(sq),
                            "selling_uom": sell,
                            "cost_qty": str(cq),
                            "cost_uom": cuom,
                        }, ensure_ascii=False, default=str),
                        int(issue_id),
                    ),
                )

            cur.execute(
                """INSERT INTO qa_manual_resolution
                     (issue_id,batch_id,issue_code,entity_type,entity_key,
                      resolution_kind,actor,resolution_note,before_json,applied_json,after_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    int(issue_id) if issue_id is not None else None,
                    int(issue_row["batch_id"]) if issue_row and issue_row.get("batch_id") is not None else batch_id,
                    issue_row.get("issue_code") if issue_row else "COST_TO_SELLING_UOM_UNRESOLVED",
                    issue_row.get("entity_type") if issue_row else "UPC",
                    issue_row.get("entity_key") if issue_row else ean,
                    "USER_CONFIRMED_COST_CONVERSION",
                    actor,
                    str(note or "")[:512] or None,
                    json.dumps(before, ensure_ascii=False, default=str),
                    json.dumps({
                        "ean_upc": ean,
                        "selling_qty": str(sq),
                        "selling_uom": sell,
                        "cost_qty": str(cq),
                        "cost_uom": cuom,
                        "targeted_refresh": refreshed,
                    }, ensure_ascii=False, default=str),
                    json.dumps(after, ensure_ascii=False, default=str),
                ),
            )
            resolution_id = int(cur.lastrowid)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    return {
        "status": "APPLIED",
        "resolution_id": resolution_id,
        "ean_upc": ean,
        "selling_qty": str(sq),
        "selling_uom": sell,
        "cost_qty": str(cq),
        "cost_uom": cuom,
        "after": after,
        "rules": {
            "raw_source_rows_modified": False,
            "authoritative_cost_value_modified": False,
            "write_scope": "USER_CONFIRMED_COST_TO_SELLING_CONVERSION_ONLY",
            "targeted_quick_check_refreshed": True,
        },
    }


def resolve_article_family_issue(
    *,
    issue_id: int,
    article_number: str,
    main_article_number: str,
    note: str | None,
    actor: str,
    confirm: str,
) -> dict[str, Any]:
    """Persist an explicit Article -> Family mapping authority.

    This is deliberately user-confirmed. It never infers the family from the
    article number, description, or movement quantity. A full Phase 3 rebuild is
    required afterward so family movement and downstream aggregates are
    regenerated under the new mapping.
    """
    if confirm != "APPLY_ARTICLE_FAMILY_FIX":
        raise ValueError("CONFIRM_MUST_BE_APPLY_ARTICLE_FAMILY_FIX")

    article = str(article_number or "").strip()
    main = str(main_article_number or "").strip()
    if not article:
        raise ValueError("ARTICLE_NUMBER_REQUIRED")
    if not main:
        raise ValueError("MAIN_ARTICLE_NUMBER_REQUIRED")

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_article_family_override_table(cur)
        _ensure_resolution_table(cur)
        conn.commit()

        if _pipeline_busy(cur):
            cur.close()
            raise RuntimeError("PIPELINE_BUSY_RETRY_AFTER_ACTIVE_BATCH_FINISHES")

        cur.execute(
            """SELECT issue_id,batch_id,issue_code,entity_type,entity_key,
                      issue_summary,detail_json,issue_status
               FROM qa_phase3_issue
               WHERE issue_id=%s
               LIMIT 1""",
            (int(issue_id),),
        )
        issue = cur.fetchone()
        if not issue:
            cur.close()
            raise ValueError("QA_ISSUE_NOT_FOUND")
        if str(issue.get("issue_status") or "").upper() != "OPEN":
            cur.close()
            raise ValueError("QA_ISSUE_NOT_OPEN")
        if str(issue.get("issue_code") or "").upper() != "SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED":
            cur.close()
            raise ValueError("QA_ISSUE_NOT_ARTICLE_FAMILY_MAPPING")
        if str(issue.get("entity_type") or "").upper() != "ARTICLE":
            cur.close()
            raise ValueError("QA_ISSUE_ENTITY_TYPE_NOT_ARTICLE")
        if str(issue.get("entity_key") or "") != article:
            cur.close()
            raise ValueError("QA_ISSUE_ENTITY_MISMATCH")

        cur.execute(
            "SELECT article_id,article_description FROM article WHERE article_number=%s LIMIT 1",
            (article,),
        )
        ar = cur.fetchone()
        if not ar:
            cur.close()
            raise ValueError("ARTICLE_NOT_PRESENT")

        cur.execute(
            """SELECT family_id,family_description
               FROM product_family
               WHERE main_article_number=%s
               LIMIT 1""",
            (main,),
        )
        fam = cur.fetchone()
        if not fam:
            cur.close()
            raise ValueError("TARGET_MAIN_ARTICLE_FAMILY_NOT_FOUND")

        cur.execute(
            """SELECT pf.main_article_number
               FROM bridge_article_family baf
               JOIN product_family pf ON pf.family_id=baf.family_id
               WHERE baf.article_id=%s
                 AND baf.mapping_status='CONFIRMED'
                 AND baf.is_primary=TRUE
                 AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               LIMIT 1""",
            (int(ar["article_id"]),),
        )
        existing = cur.fetchone()
        if existing and str(existing.get("main_article_number") or "") != main:
            cur.close()
            raise RuntimeError(
                "ARTICLE_ALREADY_HAS_CONFIRMED_DIFFERENT_FAMILY:"
                + str(existing.get("main_article_number") or "")
            )

        before = {
            "issue": issue,
            "article": {
                "article_number": article,
                "article_description": ar.get("article_description"),
            },
            "existing_family": existing,
        }
        source_note = (
            "BACKOFFICE_QA_USER_CONFIRMED_ARTICLE_FAMILY: "
            + (str(note or "").strip() or "User confirmed Article to Family mapping")
        )[:512]

        conn.start_transaction()
        try:
            cur.execute(
                """INSERT INTO manual_article_family_override
                     (article_number,main_article_number,authority_status,source_note)
                   VALUES (%s,%s,'CONFIRMED',%s)
                   ON DUPLICATE KEY UPDATE
                     main_article_number=VALUES(main_article_number),
                     authority_status='CONFIRMED',
                     source_note=VALUES(source_note)""",
                (article, main, source_note),
            )

            applied = apply_manual_article_family_overrides(cur)
            target_holds = [
                x for x in (applied.get("held") or [])
                if str(x.get("article_number") or "") == article
            ]
            if target_holds:
                raise RuntimeError(
                    "TARGET_ARTICLE_FAMILY_OVERRIDE_HELD:"
                    + json.dumps(target_holds, default=str)
                )

            relink_history(cur)

            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_status='RESOLVED',
                       detail_json=JSON_SET(
                         COALESCE(detail_json,JSON_OBJECT()),
                         '$.manual_resolution',
                         CAST(%s AS JSON)
                       )
                   WHERE issue_id=%s
                     AND issue_status='OPEN'""",
                (
                    json.dumps({
                        "actor": actor,
                        "note": note,
                        "resolution_kind": "USER_CONFIRMED_ARTICLE_FAMILY_OVERRIDE",
                        "article_number": article,
                        "main_article_number": main,
                        "requires_phase3_rebuild": True,
                    }, ensure_ascii=False, default=str),
                    int(issue_id),
                ),
            )

            cur.execute(
                """INSERT INTO qa_manual_resolution
                     (issue_id,batch_id,issue_code,entity_type,entity_key,
                      resolution_kind,actor,resolution_note,before_json,applied_json,after_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    int(issue_id),
                    int(issue["batch_id"]),
                    issue.get("issue_code"),
                    "ARTICLE",
                    article,
                    "USER_CONFIRMED_ARTICLE_FAMILY_OVERRIDE",
                    actor,
                    str(note or "")[:512] or None,
                    json.dumps(before, ensure_ascii=False, default=str),
                    json.dumps({
                        "article_number": article,
                        "main_article_number": main,
                        "manual_authority": applied,
                        "requires_phase3_rebuild": True,
                    }, ensure_ascii=False, default=str),
                    json.dumps({
                        "article_number": article,
                        "main_article_number": main,
                        "family_id": fam.get("family_id"),
                        "family_description": fam.get("family_description"),
                    }, ensure_ascii=False, default=str),
                ),
            )
            resolution_id = int(cur.lastrowid)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    return {
        "status": "APPLIED",
        "resolution_id": resolution_id,
        "article_number": article,
        "main_article_number": main,
        "requires_phase3_rebuild": True,
        "rules": {
            "raw_source_rows_modified": False,
            "movement_history_values_modified": False,
            "write_scope": "USER_CONFIRMED_ARTICLE_TO_FAMILY_AUTHORITY_ONLY",
        },
    }
