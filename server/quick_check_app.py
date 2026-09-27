from __future__ import annotations

from decimal import Decimal
from typing import Any

from db import db_conn
from inventory_position import latest_canonical_movement_day, rollforward_position


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """SELECT 1
           FROM information_schema.TABLES
           WHERE TABLE_SCHEMA=DATABASE()
             AND TABLE_NAME=%s
           LIMIT 1""",
        (table_name,),
    )
    return bool(cur.fetchone())


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """SELECT 1
           FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA=DATABASE()
             AND TABLE_NAME=%s
             AND COLUMN_NAME=%s
           LIMIT 1""",
        (table_name, column_name),
    )
    return bool(cur.fetchone())


def ensure_true_stock_tables(cur) -> None:
    if not _table_exists(cur, "manual_true_stock"):
        cur.execute(
            """
            CREATE TABLE manual_true_stock (
                true_stock_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                family_id BIGINT UNSIGNED NOT NULL,
                main_article_number VARCHAR(64) NULL,
                scope_type VARCHAR(16) NOT NULL,
                article_id BIGINT UNSIGNED NULL,
                article_number VARCHAR(64) NULL,
                upc_id BIGINT UNSIGNED NULL,
                ean_upc VARCHAR(32) NULL,
                true_stock_quantity DECIMAL(24,8) NOT NULL,
                uom_code VARCHAR(32) NOT NULL,
                system_oh_quantity DECIMAL(24,8) NULL,
                system_oh_uom_code VARCHAR(32) NULL,
                discrepancy_quantity DECIMAL(24,8) NULL,
                anchor_on_hand_file_id BIGINT UNSIGNED NULL,
                anchor_movement_date DATE NULL,
                anchor_movement_file_id BIGINT UNSIGNED NULL,
                override_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
                submitted_by VARCHAR(128) NULL,
                submitted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                superseded_at DATETIME(6) NULL,
                superseded_by_oh_file_id BIGINT UNSIGNED NULL,
                PRIMARY KEY (true_stock_id),
                KEY ix_manual_true_stock_family_status (family_id,override_status),
                KEY ix_manual_true_stock_article_status (article_id,override_status),
                KEY ix_manual_true_stock_upc (ean_upc),
                KEY ix_manual_true_stock_anchor (anchor_on_hand_file_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )

    if not _table_exists(cur, "dumping_discrepancy_queue"):
        cur.execute(
            """
            CREATE TABLE dumping_discrepancy_queue (
                discrepancy_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                family_id BIGINT UNSIGNED NOT NULL,
                main_article_number VARCHAR(64) NULL,
                scope_type VARCHAR(16) NOT NULL,
                article_id BIGINT UNSIGNED NULL,
                article_number VARCHAR(64) NULL,
                source_true_stock_id BIGINT UNSIGNED NOT NULL,
                ean_upc VARCHAR(32) NULL,
                system_oh_quantity DECIMAL(24,8) NOT NULL,
                true_stock_quantity DECIMAL(24,8) NOT NULL,
                discrepancy_quantity DECIMAL(24,8) NOT NULL,
                uom_code VARCHAR(32) NOT NULL,
                queue_status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                           ON UPDATE CURRENT_TIMESTAMP(6),
                resolved_at DATETIME(6) NULL,
                PRIMARY KEY (discrepancy_id),
                KEY ix_dumping_family_status (family_id,queue_status),
                KEY ix_dumping_source_true_stock (source_true_stock_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )

    # v7.0.56: preserve cancellation audit without deleting historical counts.
    # DDL is intentionally performed by ensure_true_stock_tables before the
    # business transaction begins.
    # v7.0.57: capture movement lineage at the physical-count anchor.
    if not _column_exists(cur, "manual_true_stock", "anchor_movement_date"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN anchor_movement_date DATE NULL
               AFTER anchor_on_hand_file_id"""
        )
    if not _column_exists(cur, "manual_true_stock", "anchor_movement_file_id"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN anchor_movement_file_id BIGINT UNSIGNED NULL
               AFTER anchor_movement_date"""
        )

    if not _column_exists(cur, "manual_true_stock", "cancelled_at"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN cancelled_at DATETIME(6) NULL
               AFTER superseded_by_oh_file_id"""
        )
    if not _column_exists(cur, "manual_true_stock", "cancelled_by"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN cancelled_by VARCHAR(128) NULL
               AFTER cancelled_at"""
        )
    if not _column_exists(cur, "manual_true_stock", "cancel_reason"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN cancel_reason VARCHAR(255) NULL
               AFTER cancelled_by"""
        )


def _latest_on_hand_file_id(cur) -> int | None:
    cur.execute(
        """SELECT MAX(file_id) AS file_id
           FROM ingest_file
           WHERE source_type='on_hand'"""
    )
    row = cur.fetchone() or {}
    return int(row["file_id"]) if row.get("file_id") is not None else None


def expire_true_stock_for_new_oh(cur, new_oh_file_id: int) -> dict[str, int]:
    """Expire active physical-count overrides when a later OH source file is ingested.

    The user's operating rule is intentionally global: submitted True Stock is the
    active analytical OH reference only until the next ON_HAND upload.
    """
    if not _table_exists(cur, "manual_true_stock"):
        return {"true_stock_expired": 0, "dumping_rows_superseded": 0}

    cur.execute(
        """SELECT true_stock_id,family_id
           FROM manual_true_stock
           WHERE override_status='ACTIVE'
             AND (anchor_on_hand_file_id IS NULL OR anchor_on_hand_file_id<%s)""",
        (int(new_oh_file_id),),
    )
    rows = cur.fetchall()
    if not rows:
        return {"true_stock_expired": 0, "dumping_rows_superseded": 0}

    ids = [int(r["true_stock_id"]) for r in rows]
    placeholders = ",".join(["%s"] * len(ids))
    cur.execute(
        f"""UPDATE manual_true_stock
            SET override_status='SUPERSEDED_BY_OH_UPLOAD',
                superseded_at=CURRENT_TIMESTAMP(6),
                superseded_by_oh_file_id=%s
            WHERE true_stock_id IN ({placeholders})
              AND override_status='ACTIVE'""",
        (int(new_oh_file_id), *ids),
    )
    expired = int(cur.rowcount or 0)

    dumping = 0
    if _table_exists(cur, "dumping_discrepancy_queue"):
        cur.execute(
            f"""UPDATE dumping_discrepancy_queue
                SET queue_status='SUPERSEDED',
                    resolved_at=CURRENT_TIMESTAMP(6)
                WHERE source_true_stock_id IN ({placeholders})
                  AND queue_status='PENDING'""",
            tuple(ids),
        )
        dumping = int(cur.rowcount or 0)

    return {"true_stock_expired": expired, "dumping_rows_superseded": dumping}


def _numeric_key(value: str) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return ""
    return digits.lstrip("0") or "0"


def search_quick_check(query: str, limit: int = 20) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        return {"query": q, "count": 0, "results": []}

    limit = max(1, min(int(limit or 20), 50))
    numeric = q.isdigit()
    nk = _numeric_key(q) if numeric else ""
    like = f"%{q}%"
    prefix = f"{q}%"

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        if numeric:
            cur.execute(
                """
                SELECT ean_upc,article_number,family_id,main_article_number,
                       selling_description,family_description,selling_uom,
                       quick_check_status,blocking_reason,current_price,current_price_type,
                       current_oh,current_oh_uom,publish_batch_id,published_at,
                       CASE
                         WHEN ean_upc=%s THEN 1000
                         WHEN ean_upc REGEXP '^[0-9]+$'
                              AND TRIM(LEADING '0' FROM ean_upc)=%s THEN 990
                         WHEN article_number=%s THEN 960
                         WHEN main_article_number=%s THEN 950
                         WHEN article_number LIKE %s THEN 850
                         WHEN main_article_number LIKE %s THEN 840
                         WHEN ean_upc LIKE %s THEN 820
                         ELSE 0
                       END
                       + CASE quick_check_status
                           WHEN 'READY' THEN 30
                           WHEN 'QA_HOLD' THEN 20
                           WHEN 'HISTORICAL_ONLY' THEN 0
                           ELSE 0
                         END AS relevance_score
                FROM quick_check_current
                WHERE ean_upc=%s
                   OR (ean_upc REGEXP '^[0-9]+$'
                       AND TRIM(LEADING '0' FROM ean_upc)=%s)
                   OR article_number=%s
                   OR main_article_number=%s
                   OR article_number LIKE %s
                   OR main_article_number LIKE %s
                   OR ean_upc LIKE %s
                ORDER BY relevance_score DESC,
                         CASE quick_check_status
                           WHEN 'READY' THEN 1
                           WHEN 'QA_HOLD' THEN 2
                           ELSE 3
                         END,
                         selling_description,
                         ean_upc
                LIMIT %s
                """,
                (
                    q, nk, q, q, prefix, prefix, like,
                    q, nk, q, q, prefix, prefix, like, limit,
                ),
            )
        else:
            q_upper = q.upper()
            like_upper = f"%{q_upper}%"
            prefix_upper = f"{q_upper}%"
            cur.execute(
                """
                SELECT ean_upc,article_number,family_id,main_article_number,
                       selling_description,family_description,selling_uom,
                       quick_check_status,blocking_reason,current_price,current_price_type,
                       current_oh,current_oh_uom,publish_batch_id,published_at,
                       CASE
                         WHEN UPPER(COALESCE(selling_description,''))=%s THEN 950
                         WHEN UPPER(COALESCE(family_description,''))=%s THEN 940
                         WHEN UPPER(COALESCE(selling_description,'')) LIKE %s THEN 850
                         WHEN UPPER(COALESCE(family_description,'')) LIKE %s THEN 840
                         WHEN UPPER(COALESCE(selling_description,'')) LIKE %s THEN 740
                         WHEN UPPER(COALESCE(family_description,'')) LIKE %s THEN 730
                         ELSE 0
                       END
                       + CASE quick_check_status
                           WHEN 'READY' THEN 30
                           WHEN 'QA_HOLD' THEN 20
                           WHEN 'HISTORICAL_ONLY' THEN 0
                           ELSE 0
                         END AS relevance_score
                FROM quick_check_current
                WHERE UPPER(COALESCE(selling_description,'')) LIKE %s
                   OR UPPER(COALESCE(family_description,'')) LIKE %s
                ORDER BY relevance_score DESC,
                         CASE quick_check_status
                           WHEN 'READY' THEN 1
                           WHEN 'QA_HOLD' THEN 2
                           ELSE 3
                         END,
                         selling_description,
                         ean_upc
                LIMIT %s
                """,
                (
                    q_upper, q_upper,
                    prefix_upper, prefix_upper,
                    like_upper, like_upper,
                    like_upper, like_upper, limit,
                ),
            )
        rows = cur.fetchall()
        cur.close()

    return {"query": q, "count": len(rows), "results": rows}



def ready_quick_checks_with_system_oh(limit: int = 50) -> dict[str, Any]:
    """Return current READY Quick Check rows that have a usable System OH."""
    limit = max(1, min(int(limit or 50), 200))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT upc_id,ean_upc,article_id,article_number,family_id,main_article_number,
                      selling_description,family_description,selling_uom,
                      current_oh,current_oh_uom,oh_date,current_price,current_price_type,
                      current_cost_per_selling_unit,pos_qty_7d,pos_qty_30d,
                      upc_velocity_7d,upc_velocity_30d,publish_batch_id,published_at
               FROM quick_check_current
               WHERE quick_check_status='READY'
                 AND current_oh IS NOT NULL
                 AND current_oh_uom IS NOT NULL
               ORDER BY
                 CASE WHEN current_oh>0 THEN 0 ELSE 1 END,
                 oh_date DESC,
                 ABS(current_oh) DESC,
                 selling_description,
                 ean_upc
               LIMIT %s""",
            (limit,),
        )
        rows = cur.fetchall()
        for row in rows:
            ctx = _system_oh_context(cur, row)
            pos = _system_position(cur, ctx)
            row["system_oh_scope_type"] = ctx.get("scope_type") if ctx else None
            row["system_oh_article_number"] = ctx.get("article_number") if ctx else None
            row["system_oh_anchor_quantity"] = ctx.get("on_hand_quantity") if ctx else None
            row["system_oh_anchor_date"] = ctx.get("observation_date") if ctx else None
            row["system_oh_movement_delta"] = pos.get("movement_delta") if pos else None
            row["system_oh_rollforward_status"] = pos.get("rollforward_status") if pos else None
            row["system_oh_analysis_usable"] = pos.get("analysis_usable") if pos else False
            if pos and pos.get("analysis_usable"):
                row["current_oh"] = pos.get("quantity")
                row["current_oh_uom"] = pos.get("uom")
                row["oh_date"] = pos.get("movement_through_date")
            row["true_stock_required_uom"] = ctx.get("uom_code") if ctx else row.get("current_oh_uom")
        cur.close()
    return {"count": len(rows), "results": rows}



def _lookup_qc_row(cur, upc: str) -> dict[str, Any] | None:
    raw = str(upc or "").strip()
    key = _numeric_key(raw)
    cur.execute(
        """SELECT *
           FROM quick_check_current
           WHERE ean_upc=%s
              OR (ean_upc REGEXP '^[0-9]+$'
                  AND TRIM(LEADING '0' FROM ean_upc)=%s)
           ORDER BY CASE quick_check_status
                      WHEN 'READY' THEN 1
                      WHEN 'QA_HOLD' THEN 2
                      ELSE 3
                    END,
                    upc_id
           LIMIT 1""",
        (raw, key),
    )
    return cur.fetchone()


def _refresh_expired_true_stock(cur) -> int | None:
    latest_oh_file_id = _latest_on_hand_file_id(cur)
    if latest_oh_file_id is not None:
        expire_true_stock_for_new_oh(cur, latest_oh_file_id)
    return latest_oh_file_id


def _system_oh_context(cur, row: dict[str, Any]) -> dict[str, Any] | None:
    """Return the exact inventory owner that supplied System OH."""
    upc_id = int(row["upc_id"])
    article_id = int(row["article_id"]) if row.get("article_id") is not None else None
    family_id = int(row["family_id"]) if row.get("family_id") is not None else None

    cur.execute(
        """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                  observation_date,article_id,article_number,family_id,
                  ean_upc,upc_id,on_hand_quantity,uom_code,source_type
           FROM inventory_observation
           WHERE upc_id=%s AND on_hand_quantity IS NOT NULL
           ORDER BY observation_date DESC,file_id DESC,raw_id DESC
           LIMIT 1""",
        (upc_id,),
    )
    r = cur.fetchone()
    if r:
        r["scope_type"] = "UPC"
        return r

    if article_id is not None:
        cur.execute(
            """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                      observation_date,article_id,article_number,family_id,
                      ean_upc,upc_id,on_hand_quantity,uom_code,source_type
               FROM inventory_observation
               WHERE article_id=%s
                 AND upc_id IS NULL
                 AND on_hand_quantity IS NOT NULL
               ORDER BY observation_date DESC,file_id DESC,raw_id DESC
               LIMIT 1""",
            (article_id,),
        )
        r = cur.fetchone()
        if r:
            r["scope_type"] = "ARTICLE"
            return r

    if family_id is not None:
        cur.execute(
            """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                      observation_date,article_id,article_number,family_id,
                      ean_upc,upc_id,on_hand_quantity,uom_code,source_type
               FROM inventory_observation
               WHERE family_id=%s
                 AND article_id IS NULL
                 AND upc_id IS NULL
                 AND on_hand_quantity IS NOT NULL
               ORDER BY observation_date DESC,file_id DESC,raw_id DESC
               LIMIT 1""",
            (family_id,),
        )
        r = cur.fetchone()
        if r:
            r["scope_type"] = "FAMILY"
            return r
    return None


def _system_position(cur, system_oh: dict[str, Any] | None) -> dict[str, Any] | None:
    if not system_oh:
        return None
    return rollforward_position(
        cur,
        anchor_quantity=system_oh.get("on_hand_quantity"),
        anchor_uom=system_oh.get("uom_code"),
        anchor_date=system_oh.get("observation_date"),
        scope_type=system_oh.get("scope_type"),
        article_id=system_oh.get("article_id"),
        family_id=system_oh.get("family_id"),
        upc_id=system_oh.get("upc_id"),
    )


def _actual_position(cur, true_stock: dict[str, Any] | None) -> dict[str, Any] | None:
    if not true_stock:
        return None
    return rollforward_position(
        cur,
        anchor_quantity=true_stock.get("true_stock_quantity"),
        anchor_uom=true_stock.get("uom_code"),
        anchor_date=true_stock.get("submitted_at"),
        scope_type=true_stock.get("scope_type"),
        article_id=true_stock.get("article_id"),
        family_id=true_stock.get("family_id"),
        upc_id=true_stock.get("upc_id"),
    )


def _active_true_stock(cur, system_oh: dict[str, Any] | None) -> dict[str, Any] | None:
    if not system_oh or not _table_exists(cur, "manual_true_stock"):
        return None

    scope = str(system_oh.get("scope_type") or "").upper()
    if scope == "UPC" and system_oh.get("upc_id") is not None:
        where = "scope_type='UPC' AND upc_id=%s"
        args = (int(system_oh["upc_id"]),)
    elif scope == "ARTICLE" and system_oh.get("article_id") is not None:
        where = "scope_type='ARTICLE' AND article_id=%s"
        args = (int(system_oh["article_id"]),)
    elif scope == "FAMILY" and system_oh.get("family_id") is not None:
        where = "scope_type='FAMILY' AND family_id=%s"
        args = (int(system_oh["family_id"]),)
    else:
        return None

    cur.execute(
        f"""SELECT *
            FROM manual_true_stock
            WHERE {where}
              AND override_status='ACTIVE'
            ORDER BY true_stock_id DESC
            LIMIT 1""",
        args,
    )
    return cur.fetchone()


def _true_stock_history(
    cur,
    system_oh: dict[str, Any] | None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not system_oh or not _table_exists(cur, "manual_true_stock"):
        return []

    scope = str(system_oh.get("scope_type") or "").upper()
    if scope == "UPC" and system_oh.get("upc_id") is not None:
        where = "scope_type='UPC' AND upc_id=%s"
        args = (int(system_oh["upc_id"]),)
    elif scope == "ARTICLE" and system_oh.get("article_id") is not None:
        where = "scope_type='ARTICLE' AND article_id=%s"
        args = (int(system_oh["article_id"]),)
    elif scope == "FAMILY" and system_oh.get("family_id") is not None:
        where = "scope_type='FAMILY' AND family_id=%s"
        args = (int(system_oh["family_id"]),)
    else:
        return []

    cur.execute(
        f"""SELECT *
            FROM manual_true_stock
            WHERE {where}
            ORDER BY true_stock_id DESC
            LIMIT %s""",
        (*args, max(1, min(int(limit or 10), 50))),
    )
    return cur.fetchall()


def get_quick_check_detail(upc: str) -> dict[str, Any] | None:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        row = _lookup_qc_row(cur, upc)
        if not row:
            cur.close()
            return None

        latest_oh_file_id = _refresh_expired_true_stock(cur)
        family_id = int(row["family_id"])
        system_oh = _system_oh_context(cur, row)
        system_position = _system_position(cur, system_oh)
        true_stock = _active_true_stock(cur, system_oh)
        actual_position = _actual_position(cur, true_stock)
        true_stock_history = _true_stock_history(cur, system_oh)

        cur.execute(
            """SELECT ean_upc,article_number,selling_description,selling_uom,
                      current_price,current_price_type,current_cost_per_selling_unit,
                      pos_qty_7d,pos_qty_30d,upc_velocity_7d,upc_velocity_30d,
                      quick_check_status,blocking_reason
               FROM quick_check_current
               WHERE family_id=%s
               ORDER BY
                 CASE quick_check_status
                   WHEN 'READY' THEN 1
                   WHEN 'QA_HOLD' THEN 2
                   ELSE 3
                 END,
                 ean_upc""",
            (family_id,),
        )
        related = cur.fetchall()

        effective_source = "TRUE_STOCK" if true_stock else "SYSTEM_OH"
        effective_position = actual_position if true_stock else system_position
        effective_oh = {
            "quantity": effective_position.get("quantity") if effective_position else None,
            "uom": effective_position.get("uom") if effective_position else None,
            "source": effective_source,
            "date": effective_position.get("movement_through_date") if effective_position else None,
            "anchor_date": effective_position.get("anchor_date") if effective_position else None,
            "anchor_quantity": effective_position.get("anchor_quantity") if effective_position else None,
            "movement_delta": effective_position.get("movement_delta") if effective_position else None,
            "movement_through_date": effective_position.get("movement_through_date") if effective_position else None,
            "rollforward_status": effective_position.get("rollforward_status") if effective_position else "BLOCKED",
            "analysis_usable": effective_position.get("analysis_usable") if effective_position else False,
            "blockers": effective_position.get("blockers") if effective_position else ["OH_POSITION_NOT_AVAILABLE"],
            "same_day_policy": effective_position.get("same_day_policy") if effective_position else None,
            "submitted_by": true_stock.get("submitted_by") if true_stock else None,
            "scope_type": (true_stock.get("scope_type") if true_stock else system_oh.get("scope_type")) if (true_stock or system_oh) else None,
            "article_id": (true_stock.get("article_id") if true_stock else system_oh.get("article_id")) if (true_stock or system_oh) else None,
            "article_number": (true_stock.get("article_number") if true_stock else system_oh.get("article_number")) if (true_stock or system_oh) else None,
        }

        detail = {
            "item": row,
            "system_oh": {
                "quantity": system_position.get("quantity") if system_position else None,
                "uom": system_position.get("uom") if system_position else (system_oh.get("uom_code") if system_oh else None),
                "date": system_position.get("movement_through_date") if system_position else (system_oh.get("observation_date") if system_oh else None),
                "anchor_quantity": system_position.get("anchor_quantity") if system_position else (system_oh.get("on_hand_quantity") if system_oh else None),
                "anchor_date": system_position.get("anchor_date") if system_position else (system_oh.get("observation_date") if system_oh else None),
                "movement_delta": system_position.get("movement_delta") if system_position else None,
                "movement_through_date": system_position.get("movement_through_date") if system_position else None,
                "movement_days": system_position.get("movement_days") if system_position else [],
                "by_movement_type": system_position.get("by_movement_type") if system_position else [],
                "rollforward_status": system_position.get("rollforward_status") if system_position else "BLOCKED",
                "analysis_usable": system_position.get("analysis_usable") if system_position else False,
                "blockers": system_position.get("blockers") if system_position else ["SYSTEM_OH_NOT_AVAILABLE"],
                "same_day_policy": system_position.get("same_day_policy") if system_position else None,
                "scope_type": system_oh.get("scope_type") if system_oh else None,
                "article_id": system_oh.get("article_id") if system_oh else None,
                "article_number": system_oh.get("article_number") if system_oh else None,
                "source_file_id": system_oh.get("file_id") if system_oh else None,
                "source_raw_id": system_oh.get("raw_id") if system_oh else None,
            },
            "actual_oh": ({
                **actual_position,
                "source": "TRUE_STOCK",
                "submitted_by": true_stock.get("submitted_by"),
                "true_stock_id": true_stock.get("true_stock_id"),
                "scope_type": true_stock.get("scope_type"),
                "article_id": true_stock.get("article_id"),
                "article_number": true_stock.get("article_number"),
            } if true_stock and actual_position else None),
            "true_stock_input": {
                "required_uom": system_position.get("uom") if system_position else (system_oh.get("uom_code") if system_oh else None),
                "scope_type": system_oh.get("scope_type") if system_oh else None,
                "article_number": system_oh.get("article_number") if system_oh else None,
                "cross_uom_submission_allowed": False,
            },
            "active_true_stock": true_stock,
            "true_stock_history": true_stock_history,
            "effective_oh": effective_oh,
            "latest_on_hand_file_id": latest_oh_file_id,
            "related_upcs": related,
        }
        conn.commit()
        cur.close()
        return detail


def submit_true_stock(
    upc: str,
    true_stock_quantity: Decimal,
    true_stock_uom: str,
    device: str,
) -> dict[str, Any]:
    qty = Decimal(str(true_stock_quantity))
    submitted_uom = str(true_stock_uom or "").strip().upper()
    if qty < 0:
        raise ValueError("TRUE_STOCK_NEGATIVE")

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            ensure_true_stock_tables(cur)
            conn.commit()
            conn.start_transaction()

            row = _lookup_qc_row(cur, upc)
            if not row:
                raise KeyError("QUICK_CHECK_UPC_NOT_FOUND")
            if row.get("family_id") is None:
                raise ValueError("FAMILY_ID_NOT_AVAILABLE")

            family_id = int(row["family_id"])
            latest_oh_file_id = _refresh_expired_true_stock(cur)
            system_oh = _system_oh_context(cur, row)
            if not system_oh:
                raise ValueError("SYSTEM_OH_LINEAGE_NOT_AVAILABLE")
            system_position = _system_position(cur, system_oh)
            if not system_position or not system_position.get("analysis_usable"):
                raise ValueError("SYSTEM_OH_ROLLFORWARD_BLOCKED")
            if system_position.get("quantity") is None or not system_position.get("uom"):
                raise ValueError("SYSTEM_OH_NOT_AVAILABLE")

            system_qty = Decimal(str(system_position["quantity"]))
            system_uom = str(system_position["uom"]).strip().upper()
            if not submitted_uom:
                raise ValueError("TRUE_STOCK_UOM_REQUIRED")
            if submitted_uom != system_uom:
                raise ValueError(f"TRUE_STOCK_UOM_MISMATCH:{system_uom}")

            scope_type = str(system_oh["scope_type"]).upper()
            article_id = int(system_oh["article_id"]) if system_oh.get("article_id") is not None else None
            article_number = system_oh.get("article_number")

            if scope_type == "UPC":
                scope_where = "scope_type='UPC' AND upc_id=%s"
                scope_args = (int(row["upc_id"]),)
            elif scope_type == "ARTICLE":
                scope_where = "scope_type='ARTICLE' AND article_id=%s"
                scope_args = (article_id,)
            elif scope_type == "FAMILY":
                scope_where = "scope_type='FAMILY' AND family_id=%s"
                scope_args = (family_id,)
            else:
                raise ValueError("SYSTEM_OH_SCOPE_UNRESOLVED")

            cur.execute(
                f"""UPDATE manual_true_stock
                    SET override_status='SUPERSEDED_BY_NEW_TRUE_STOCK',
                        superseded_at=CURRENT_TIMESTAMP(6)
                    WHERE {scope_where}
                      AND override_status='ACTIVE'""",
                scope_args,
            )

            movement_anchor = latest_canonical_movement_day(cur)
            discrepancy = system_qty - qty
            cur.execute(
                """INSERT INTO manual_true_stock
                   (family_id,main_article_number,scope_type,article_id,article_number,
                    upc_id,ean_upc,true_stock_quantity,uom_code,
                    system_oh_quantity,system_oh_uom_code,
                    discrepancy_quantity,anchor_on_hand_file_id,
                    anchor_movement_date,anchor_movement_file_id,
                    override_status,submitted_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s)""",
                (
                    family_id,
                    row.get("main_article_number"),
                    scope_type,
                    article_id,
                    article_number,
                    row.get("upc_id"),
                    row.get("ean_upc"),
                    qty,
                    system_uom,
                    system_qty,
                    system_uom,
                    discrepancy,
                    system_oh.get("file_id"),
                    movement_anchor.get("date") if movement_anchor else None,
                    movement_anchor.get("file_id") if movement_anchor else None,
                    device,
                ),
            )
            true_stock_id = int(cur.lastrowid)

            queue_action = "NONE"
            if discrepancy > 0:
                cur.execute(
                    """SELECT discrepancy_id
                       FROM dumping_discrepancy_queue
                       WHERE family_id=%s
                         AND scope_type=%s
                         AND (
                              (%s='UPC' AND ean_upc=%s)
                           OR (%s='ARTICLE' AND article_id=%s)
                           OR (%s='FAMILY')
                         )
                         AND queue_status='PENDING'
                       ORDER BY discrepancy_id DESC
                       LIMIT 1""",
                    (
                        family_id,
                        scope_type,
                        scope_type,row.get("ean_upc"),
                        scope_type,article_id,
                        scope_type,
                    ),
                )
                pending = cur.fetchone()
                if pending:
                    cur.execute(
                        """UPDATE dumping_discrepancy_queue
                           SET source_true_stock_id=%s,
                               main_article_number=%s,
                               scope_type=%s,
                               article_id=%s,
                               article_number=%s,
                               ean_upc=%s,
                               system_oh_quantity=%s,
                               true_stock_quantity=%s,
                               discrepancy_quantity=%s,
                               uom_code=%s,
                               queue_status='PENDING',
                               resolved_at=NULL
                           WHERE discrepancy_id=%s""",
                        (
                            true_stock_id,
                            row.get("main_article_number"),
                            scope_type,
                            article_id,
                            article_number,
                            row.get("ean_upc"),
                            system_qty,
                            qty,
                            discrepancy,
                            system_uom,
                            pending["discrepancy_id"],
                        ),
                    )
                    queue_action = "UPDATED_PENDING"
                else:
                    cur.execute(
                        """INSERT INTO dumping_discrepancy_queue
                           (family_id,main_article_number,scope_type,article_id,article_number,
                            source_true_stock_id,ean_upc,system_oh_quantity,true_stock_quantity,
                            discrepancy_quantity,uom_code,queue_status)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')""",
                        (
                            family_id,
                            row.get("main_article_number"),
                            scope_type,
                            article_id,
                            article_number,
                            true_stock_id,
                            row.get("ean_upc"),
                            system_qty,
                            qty,
                            discrepancy,
                            system_uom,
                        ),
                    )
                    queue_action = "CREATED_PENDING"
            else:
                cur.execute(
                    """UPDATE dumping_discrepancy_queue
                       SET queue_status='RESOLVED',
                           resolved_at=CURRENT_TIMESTAMP(6)
                       WHERE family_id=%s
                         AND scope_type=%s
                         AND (
                              (%s='UPC' AND ean_upc=%s)
                           OR (%s='ARTICLE' AND article_id=%s)
                           OR (%s='FAMILY')
                         )
                         AND queue_status='PENDING'""",
                    (
                        family_id,
                        scope_type,
                        scope_type,row.get("ean_upc"),
                        scope_type,article_id,
                        scope_type,
                    ),
                )
                if int(cur.rowcount or 0) > 0:
                    queue_action = "RESOLVED_PENDING"

            conn.commit()
            return {
                "status": "COMMITTED",
                "family_id": family_id,
                "main_article_number": row.get("main_article_number"),
                "scope_type": scope_type,
                "article_id": article_id,
                "article_number": article_number,
                "ean_upc": row.get("ean_upc"),
                "system_oh": system_qty,
                "true_stock": qty,
                "uom": system_uom,
                "discrepancy": discrepancy,
                "true_stock_id": true_stock_id,
                "anchor_on_hand_file_id": system_oh.get("file_id"),
                "anchor_movement_date": movement_anchor.get("date") if movement_anchor else None,
                "anchor_movement_file_id": movement_anchor.get("file_id") if movement_anchor else None,
                "system_oh_anchor_quantity": system_position.get("anchor_quantity"),
                "system_oh_movement_delta": system_position.get("movement_delta"),
                "system_oh_movement_through_date": system_position.get("movement_through_date"),
                "dumping_queue_action": queue_action,
                "effective_oh_source": "TRUE_STOCK",
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def cancel_true_stock(
    upc: str,
    device: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Cancel the active True Stock override and revert Effective OH to System OH.

    The historical True Stock row is preserved for audit. Any PENDING dumping
    discrepancy sourced from that exact True Stock row is cancelled as part of
    the same transaction.
    """
    cancel_reason = str(reason or "USER_REVERT_TO_SYSTEM_OH").strip()[:255]

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            ensure_true_stock_tables(cur)
            conn.commit()
            conn.start_transaction()

            row = _lookup_qc_row(cur, upc)
            if not row:
                raise KeyError("QUICK_CHECK_UPC_NOT_FOUND")
            if row.get("family_id") is None:
                raise ValueError("FAMILY_ID_NOT_AVAILABLE")
            if row.get("current_oh") is None or not row.get("current_oh_uom"):
                raise ValueError("SYSTEM_OH_NOT_AVAILABLE")

            # If a newer OH upload already exists, this expires stale active
            # overrides before cancellation lookup.
            latest_oh_file_id = _refresh_expired_true_stock(cur)
            system_oh = _system_oh_context(cur, row)
            if not system_oh:
                raise ValueError("SYSTEM_OH_LINEAGE_NOT_AVAILABLE")

            active = _active_true_stock(cur, system_oh)
            if not active:
                raise ValueError("NO_ACTIVE_TRUE_STOCK")

            true_stock_id = int(active["true_stock_id"])
            cur.execute(
                """UPDATE manual_true_stock
                   SET override_status='CANCELLED_BY_USER',
                       superseded_at=COALESCE(superseded_at,CURRENT_TIMESTAMP(6)),
                       cancelled_at=CURRENT_TIMESTAMP(6),
                       cancelled_by=%s,
                       cancel_reason=%s
                   WHERE true_stock_id=%s
                     AND override_status='ACTIVE'""",
                (device, cancel_reason, true_stock_id),
            )
            cancelled = int(cur.rowcount or 0)
            if cancelled != 1:
                raise RuntimeError("TRUE_STOCK_CANCEL_RACE")

            dumping_cancelled = 0
            if _table_exists(cur, "dumping_discrepancy_queue"):
                cur.execute(
                    """UPDATE dumping_discrepancy_queue
                       SET queue_status='CANCELLED',
                           resolved_at=CURRENT_TIMESTAMP(6)
                       WHERE source_true_stock_id=%s
                         AND queue_status='PENDING'""",
                    (true_stock_id,),
                )
                dumping_cancelled = int(cur.rowcount or 0)

            system_position = _system_position(cur, system_oh)
            conn.commit()
            return {
                "status": "COMMITTED",
                "action": "TRUE_STOCK_CANCELLED",
                "true_stock_id": true_stock_id,
                "family_id": int(row["family_id"]),
                "main_article_number": row.get("main_article_number"),
                "scope_type": system_oh.get("scope_type"),
                "article_id": system_oh.get("article_id"),
                "article_number": system_oh.get("article_number"),
                "ean_upc": row.get("ean_upc"),
                "cancelled_by": device,
                "cancel_reason": cancel_reason,
                "dumping_rows_cancelled": dumping_cancelled,
                "effective_oh_source": "SYSTEM_OH",
                "system_oh": system_position.get("quantity") if system_position else None,
                "system_oh_uom": system_position.get("uom") if system_position else (system_oh.get("uom_code") if system_oh else None),
                "system_oh_anchor_quantity": system_position.get("anchor_quantity") if system_position else None,
                "system_oh_movement_delta": system_position.get("movement_delta") if system_position else None,
                "system_oh_movement_through_date": system_position.get("movement_through_date") if system_position else None,
                "system_oh_rollforward_status": system_position.get("rollforward_status") if system_position else "BLOCKED",
                "latest_on_hand_file_id": latest_oh_file_id,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()




def inventory_position_diagnostic(upc: str) -> dict[str, Any]:
    """Read-only OH anchor -> movement roll-forward diagnostic for one UPC.

    v7.0.58 also exposes the raw normalized movement_history evidence for every
    canonical post-anchor MVT file so an ARTICLE-vs-FAMILY pooling decision can
    be made from source evidence rather than from family sales-only rows.
    """
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        row = _lookup_qc_row(cur, upc)
        if not row:
            cur.close()
            raise KeyError("QUICK_CHECK_UPC_NOT_FOUND")

        _refresh_expired_true_stock(cur)
        system_oh = _system_oh_context(cur, row)
        system_position = _system_position(cur, system_oh)
        true_stock = _active_true_stock(cur, system_oh)
        actual_position = _actual_position(cur, true_stock)
        effective_position = actual_position if true_stock else system_position
        effective_source = "TRUE_STOCK" if true_stock else "SYSTEM_OH"

        movement_file_ids = list((system_position or {}).get("movement_file_ids") or [])
        family_id = int(row["family_id"]) if row.get("family_id") is not None else None
        article_id = int(system_oh["article_id"]) if system_oh and system_oh.get("article_id") is not None else None

        family_movement_history = []
        exact_article_movement_history = []
        movement_summary_by_article = []
        if movement_file_ids and family_id is not None:
            placeholders = ",".join(["%s"] * len(movement_file_ids))
            cur.execute(
                f"""SELECT file_id,raw_id,source_row_number,
                           article_number,article_id,family_id,description,
                           movement_type,posting_date,
                           entry_quantity,entry_uom_code,
                           base_quantity,base_uom_code,
                           amount_local_currency,sales_value,
                           article_document,purchase_order,vendor_code
                    FROM movement_history
                    WHERE family_id=%s
                      AND file_id IN ({placeholders})
                    ORDER BY posting_date,file_id,article_number,movement_type,
                             raw_id,source_row_number""",
                (family_id, *movement_file_ids),
            )
            family_movement_history = cur.fetchall()
            exact_article_movement_history = [
                x for x in family_movement_history
                if article_id is not None and x.get("article_id") == article_id
            ]

            grouped = {}
            for x in family_movement_history:
                key = (
                    x.get("article_id"),
                    x.get("article_number"),
                    x.get("base_uom_code"),
                )
                g = grouped.setdefault(
                    key,
                    {
                        "article_id": x.get("article_id"),
                        "article_number": x.get("article_number"),
                        "base_uom_code": x.get("base_uom_code"),
                        "row_count": 0,
                        "net_base_quantity": Decimal("0"),
                        "movement_types": set(),
                    },
                )
                g["row_count"] += 1
                if x.get("base_quantity") is not None:
                    g["net_base_quantity"] += Decimal(str(x["base_quantity"]))
                if x.get("movement_type") is not None:
                    g["movement_types"].add(str(x["movement_type"]))

            movement_summary_by_article = [
                {
                    "article_id": g["article_id"],
                    "article_number": g["article_number"],
                    "base_uom_code": g["base_uom_code"],
                    "row_count": g["row_count"],
                    "net_base_quantity": g["net_base_quantity"],
                    "movement_types": sorted(g["movement_types"]),
                }
                for g in grouped.values()
            ]
            movement_summary_by_article.sort(
                key=lambda x: (
                    str(x.get("article_number") or ""),
                    str(x.get("base_uom_code") or ""),
                )
            )

        conn.commit()
        cur.close()
        return {
            "ean_upc": row.get("ean_upc"),
            "family_id": row.get("family_id"),
            "main_article_number": row.get("main_article_number"),
            "article_id": row.get("article_id"),
            "article_number": row.get("article_number"),
            "system_anchor": system_oh,
            "system_position": system_position,
            "active_true_stock": true_stock,
            "actual_position": actual_position,
            "effective_position": effective_position,
            "effective_source": effective_source,
            "movement_evidence": {
                "canonical_post_anchor_file_ids": movement_file_ids,
                "exact_article_row_count": len(exact_article_movement_history),
                "family_row_count": len(family_movement_history),
                "exact_article_rows": exact_article_movement_history,
                "family_rows": family_movement_history,
                "summary_by_article": movement_summary_by_article,
                "diagnostic_note": (
                    "This evidence comes from movement_history and therefore includes "
                    "all normalized movement types, not only 251/252 family sale movement."
                ),
            },
        }


def diagnose_on_hand_lineage(limit: int = 50) -> dict[str, Any]:
    """Read-only diagnostic for OH ingest -> inventory_observation -> Quick Check propagation."""
    limit = max(1, min(int(limit or 50), 200))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """SELECT COUNT(*) AS c
               FROM ingest_file
               WHERE source_type='on_hand'"""
        )
        on_hand_file_count = int((cur.fetchone() or {}).get("c") or 0)

        cur.execute(
            """SELECT file_id,batch_id,original_filename,source_type,
                      source_type_confidence,processing_status,source_row_count,
                      error_count,duplicate_of_file_id,coverage_type,
                      coverage_start_date,coverage_end_date,
                      report_generated_at,upload_timestamp,filename_date_candidate
               FROM ingest_file
               WHERE source_type='on_hand'
               ORDER BY file_id DESC
               LIMIT %s""",
            (limit,),
        )
        on_hand_files = cur.fetchall()

        # Surface filename candidates that contain common OH tokens but were not
        # classified as on_hand. This is diagnostic evidence only and does not
        # reclassify or ingest them.
        cur.execute(
            """SELECT file_id,batch_id,original_filename,source_type,
                      source_type_confidence,processing_status,source_row_count,
                      error_count,upload_timestamp
               FROM ingest_file
               WHERE source_type<>'on_hand'
                 AND (
                      UPPER(original_filename) LIKE 'OH%%'
                   OR UPPER(original_filename) LIKE '%% OH%%'
                   OR UPPER(original_filename) LIKE '%%-OH%%'
                   OR UPPER(original_filename) LIKE '%%_OH%%'
                   OR UPPER(original_filename) LIKE '%%ON HAND%%'
                 )
               ORDER BY file_id DESC
               LIMIT %s""",
            (limit,),
        )
        filename_candidates = cur.fetchall()

        cur.execute("SELECT COUNT(*) AS c FROM raw_on_hand")
        raw_count = int((cur.fetchone() or {}).get("c") or 0)

        cur.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN family_id IS NOT NULL THEN 1 ELSE 0 END) AS family_mapped,
                      SUM(CASE WHEN upc_id IS NOT NULL THEN 1 ELSE 0 END) AS upc_mapped,
                      SUM(CASE WHEN uom_code IS NOT NULL AND TRIM(uom_code)<>'' THEN 1 ELSE 0 END) AS uom_present,
                      SUM(CASE WHEN on_hand_quantity IS NOT NULL THEN 1 ELSE 0 END) AS qty_present,
                      MAX(observation_date) AS latest_observation_date
               FROM inventory_observation"""
        )
        obs = cur.fetchone() or {}
        inventory_summary = {
            "total": int(obs.get("total") or 0),
            "family_mapped": int(obs.get("family_mapped") or 0),
            "upc_mapped": int(obs.get("upc_mapped") or 0),
            "uom_present": int(obs.get("uom_present") or 0),
            "qty_present": int(obs.get("qty_present") or 0),
            "latest_observation_date": obs.get("latest_observation_date"),
        }

        cur.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS ready_rows,
                      SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS hold_rows,
                      SUM(CASE WHEN current_oh IS NOT NULL THEN 1 ELSE 0 END) AS with_oh,
                      SUM(CASE WHEN current_oh IS NOT NULL
                                    AND current_oh_uom IS NOT NULL
                                    AND TRIM(current_oh_uom)<>''
                               THEN 1 ELSE 0 END) AS with_oh_and_uom,
                      SUM(CASE WHEN quick_check_status='READY'
                                    AND current_oh IS NOT NULL
                                    AND current_oh_uom IS NOT NULL
                                    AND TRIM(current_oh_uom)<>''
                               THEN 1 ELSE 0 END) AS ready_with_oh
               FROM quick_check_current"""
        )
        qc = cur.fetchone() or {}
        quick_check_summary = {
            "total": int(qc.get("total") or 0),
            "ready_rows": int(qc.get("ready_rows") or 0),
            "hold_rows": int(qc.get("hold_rows") or 0),
            "with_oh": int(qc.get("with_oh") or 0),
            "with_oh_and_uom": int(qc.get("with_oh_and_uom") or 0),
            "ready_with_oh": int(qc.get("ready_with_oh") or 0),
        }

        cur.execute(
            """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                      observation_date,article_number,article_id,family_id,
                      ean_upc,upc_id,on_hand_quantity,uom_code,source_type
               FROM inventory_observation
               ORDER BY observation_date DESC,file_id DESC,raw_id DESC
               LIMIT %s""",
            (limit,),
        )
        observation_sample = cur.fetchall()

        cur.execute(
            """SELECT i.batch_id,i.file_id,i.sheet_id,i.raw_id,i.source_row_number,
                      i.observation_date,i.article_number,i.article_id,i.family_id,
                      i.ean_upc,i.upc_id,i.on_hand_quantity,i.uom_code,i.source_type,
                      a.article_id AS catalog_article_id,
                      a.article_description AS catalog_article_description,
                      a.category_code AS catalog_category_code,
                      pf_main.family_id AS main_article_family_id,
                      pf_main.main_article_number AS main_article_family_number,
                      pf_main.family_description AS main_article_family_description,
                      baf.family_id AS confirmed_bridge_family_id,
                      pf_bridge.main_article_number AS confirmed_bridge_main_article,
                      pf_bridge.family_description AS confirmed_bridge_family_description,
                      baf.mapping_status AS confirmed_bridge_status,
                      baf.is_primary AS confirmed_bridge_is_primary
               FROM inventory_observation i
               LEFT JOIN article a
                 ON a.article_number=i.article_number
               LEFT JOIN product_family pf_main
                 ON pf_main.main_article_number=i.article_number
               LEFT JOIN bridge_article_family baf
                 ON baf.article_id=a.article_id
                AND baf.mapping_status='CONFIRMED'
                AND baf.is_primary=TRUE
                AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
               LEFT JOIN product_family pf_bridge
                 ON pf_bridge.family_id=baf.family_id
               WHERE i.family_id IS NULL OR i.article_id IS NULL
               ORDER BY i.observation_date DESC,i.file_id DESC,i.raw_id DESC
               LIMIT %s""",
            (limit,),
        )
        unmapped_inventory_rows = cur.fetchall()

        cur.execute(
            """SELECT ean_upc,article_number,family_id,main_article_number,
                      selling_description,selling_uom,current_oh,current_oh_uom,
                      oh_date,quick_check_status,blocking_reason
               FROM quick_check_current
               WHERE current_oh IS NOT NULL
               ORDER BY oh_date DESC,ean_upc
               LIMIT %s""",
            (limit,),
        )
        qc_oh_sample = cur.fetchall()
        cur.close()

    if on_hand_file_count == 0 and raw_count == 0 and inventory_summary["total"] == 0:
        stage = "NO_ON_HAND_SOURCE_INGESTED"
    elif raw_count == 0:
        stage = "ON_HAND_FILE_PRESENT_BUT_NO_RAW_ROWS"
    elif inventory_summary["total"] == 0:
        stage = "RAW_ON_HAND_PRESENT_BUT_NO_INVENTORY_OBSERVATIONS"
    elif quick_check_summary["with_oh"] == 0:
        stage = "INVENTORY_OBSERVATIONS_PRESENT_BUT_NOT_PROPAGATED_TO_QUICK_CHECK"
    elif quick_check_summary["ready_with_oh"] == 0:
        stage = "OH_PROPAGATED_BUT_NO_READY_ROWS_WITH_USABLE_UOM"
    else:
        stage = "OH_PIPELINE_HAS_USABLE_ROWS"

    return {
        "stage": stage,
        "on_hand_file_count": on_hand_file_count,
        "raw_on_hand_row_count": raw_count,
        "inventory_summary": inventory_summary,
        "quick_check_summary": quick_check_summary,
        "on_hand_files": on_hand_files,
        "possible_misclassified_oh_filenames": filename_candidates,
        "inventory_observation_sample": observation_sample,
        "unmapped_inventory_observations": unmapped_inventory_rows,
        "quick_check_oh_sample": qc_oh_sample,
    }



def quick_check_lineage(upc: str) -> dict[str, Any] | None:
    """Read-only lineage for one Quick Check UPC.

    This intentionally exposes source observations instead of guessing whether a
    configured price, POS quantity, or inventory quantity is expressed in the
    same unit as the currently resolved Selling UOM.
    """
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        row = _lookup_qc_row(cur, upc)
        if not row:
            cur.close()
            return None

        upc_id = int(row["upc_id"])
        family_id = int(row["family_id"])

        cur.execute(
            """SELECT h.upc_uom_id,
                      su.uom_code AS selling_uom,
                      bu.uom_code AS base_uom,
                      h.base_qty_per_selling_unit,
                      h.mapping_status,h.confidence,h.resolution_method,
                      h.effective_from,h.effective_to
               FROM selling_upc_uom_history h
               JOIN dim_uom su ON su.uom_id=h.selling_uom_id
               LEFT JOIN dim_uom bu ON bu.uom_id=h.base_uom_id
               WHERE h.upc_id=%s
               ORDER BY
                 CASE WHEN h.mapping_status='CONFIRMED'
                           AND (h.effective_to IS NULL OR h.effective_to>CURRENT_TIMESTAMP(6))
                      THEN 0 ELSE 1 END,
                 h.upc_uom_id DESC
               LIMIT 25""",
            (upc_id,),
        )
        uom_history = cur.fetchall()

        cur.execute(
            """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                      ean_upc,description,configured_price,price_quantity,
                      price_type,source_since_date,snapshot_at
               FROM price_list_observation
               WHERE upc_id=%s
               ORDER BY snapshot_at DESC,file_id DESC,raw_id DESC
               LIMIT 50""",
            (upc_id,),
        )
        price_rows = cur.fetchall()

        cur.execute(
            """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                      ean_upc,description,period_start_date,period_end_date,
                      temporal_grain,price_type,sales_amount,sold_quantity,
                      avg_sold_price
               FROM sales_period_observation
               WHERE upc_id=%s
               ORDER BY period_end_date DESC,period_start_date DESC,
                        file_id DESC,raw_id DESC
               LIMIT 100""",
            (upc_id,),
        )
        sales_rows = cur.fetchall()

        cur.execute(
            """SELECT batch_id,file_id,sheet_id,raw_id,article_id,movement_type,
                      posting_date,base_quantity_signed,net_sold_quantity,
                      base_uom_code
               FROM family_movement_observation
               WHERE family_id=%s
               ORDER BY posting_date DESC,file_id DESC,raw_id DESC
               LIMIT 100""",
            (family_id,),
        )
        movement_rows = cur.fetchall()

        cur.execute(
            """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                      observation_date,article_number,ean_upc,upc_id,
                      on_hand_quantity,uom_code,source_type
               FROM inventory_observation
               WHERE upc_id=%s OR family_id=%s
               ORDER BY observation_date DESC,file_id DESC,raw_id DESC
               LIMIT 50""",
            (upc_id,family_id),
        )
        inventory_rows = cur.fetchall()

        return {
            "quick_check": row,
            "uom_history": uom_history,
            "price_list_observations": price_rows,
            "sales_period_observations": sales_rows,
            "family_movement_observations": movement_rows,
            "inventory_observations": inventory_rows,
            "diagnostic_note": (
                "price_quantity and source quantities are returned verbatim; "
                "no cross-UOM interpretation is inferred by this diagnostic"
            ),
        }



def pending_dumping_discrepancies() -> list[dict[str, Any]]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        if not _table_exists(cur, "dumping_discrepancy_queue"):
            cur.close()
            return []
        _refresh_expired_true_stock(cur)
        cur.execute(
            """SELECT discrepancy_id,family_id,main_article_number,scope_type,
                      article_id,article_number,source_true_stock_id,
                      ean_upc,system_oh_quantity,true_stock_quantity,
                      discrepancy_quantity,uom_code,queue_status,created_at,updated_at
               FROM dumping_discrepancy_queue
               WHERE queue_status='PENDING'
               ORDER BY updated_at DESC,discrepancy_id DESC"""
        )
        rows = cur.fetchall()
        conn.commit()
        cur.close()
        return rows
