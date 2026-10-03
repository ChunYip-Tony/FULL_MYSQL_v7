from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from typing import Any

from db import db_conn
from data_coverage import source_data_days
from business_clock import business_today, completed_through_date
from inventory_position import latest_canonical_movement_day, rollforward_position, UNRESTRICTED_APPLY_AS_SIGNED, UNRESTRICTED_NO_EFFECT
from upc_aliases import source_ean_predicate


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


def ensure_ordering_policy_table(cur) -> None:
    if not _table_exists(cur, "ordering_policy"):
        cur.execute(
            """
            CREATE TABLE ordering_policy (
                ordering_policy_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                scope_type VARCHAR(24) NOT NULL,
                scope_key VARCHAR(64) NOT NULL,
                order_weekday TINYINT UNSIGNED NOT NULL,
                delivery_weekday TINYINT UNSIGNED NOT NULL,
                coverage_days_after_delivery DECIMAL(10,2) NOT NULL,
                safety_days DECIMAL(10,2) NOT NULL DEFAULT 0,
                min_order_qty DECIMAL(24,8) NULL,
                order_multiple DECIMAL(24,8) NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                notes VARCHAR(255) NULL,
                updated_by VARCHAR(128) NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                           ON UPDATE CURRENT_TIMESTAMP(6),
                PRIMARY KEY (ordering_policy_id),
                UNIQUE KEY uq_ordering_policy_scope (scope_type,scope_key),
                KEY ix_ordering_policy_enabled (enabled,scope_type,scope_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )


def _ordering_scope_candidates(row: dict[str, Any]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for scope_type, value in (
        ("UPC", row.get("ean_upc")),
        ("ARTICLE", row.get("article_number")),
        ("FAMILY", row.get("main_article_number") or row.get("family_id")),
        ("PRODUCT_CLASS", row.get("product_class")),
    ):
        key = str(value or "").strip()
        if key:
            candidates.append((scope_type, key.upper() if scope_type == "PRODUCT_CLASS" else key))
    candidates.append(("GLOBAL", "*"))
    return candidates


def _resolve_ordering_policy(cur, row: dict[str, Any]) -> dict[str, Any] | None:
    for scope_type, scope_key in _ordering_scope_candidates(row):
        cur.execute(
            """SELECT ordering_policy_id,scope_type,scope_key,order_weekday,
                      delivery_weekday,coverage_days_after_delivery,safety_days,
                      min_order_qty,order_multiple,enabled,notes,updated_by,updated_at
               FROM ordering_policy
               WHERE scope_type=%s AND scope_key=%s AND enabled=TRUE
               LIMIT 1""",
            (scope_type, scope_key),
        )
        policy = cur.fetchone()
        if policy:
            return policy
    return None


def list_ordering_policies() -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_ordering_policy_table(cur)
        conn.commit()
        cur.execute(
            """SELECT ordering_policy_id,scope_type,scope_key,order_weekday,
                      delivery_weekday,coverage_days_after_delivery,safety_days,
                      min_order_qty,order_multiple,enabled,notes,updated_by,updated_at
               FROM ordering_policy
               ORDER BY
                 FIELD(scope_type,'UPC','ARTICLE','FAMILY','PRODUCT_CLASS','GLOBAL'),
                 scope_key"""
        )
        rows = cur.fetchall()
        cur.close()
    return {"count": len(rows), "rows": rows, "contract_version": "ORDERING_POLICY_V1"}


def upsert_ordering_policy(
    *,
    scope_type: str,
    scope_key: str,
    order_weekday: int,
    delivery_weekday: int,
    coverage_days_after_delivery: Decimal,
    safety_days: Decimal = Decimal("0"),
    min_order_qty: Decimal | None = None,
    order_multiple: Decimal | None = None,
    enabled: bool = True,
    notes: str | None = None,
    device: str,
) -> dict[str, Any]:
    scope = str(scope_type or "").strip().upper()
    if scope not in {"GLOBAL","PRODUCT_CLASS","FAMILY","ARTICLE","UPC"}:
        raise ValueError("ORDERING_POLICY_SCOPE_INVALID")
    key = "*" if scope == "GLOBAL" else str(scope_key or "").strip()
    if not key:
        raise ValueError("ORDERING_POLICY_SCOPE_KEY_REQUIRED")
    if scope == "PRODUCT_CLASS":
        key = key.upper()
    ow = int(order_weekday)
    dw = int(delivery_weekday)
    if ow < 0 or ow > 6 or dw < 0 or dw > 6:
        raise ValueError("ORDERING_POLICY_WEEKDAY_INVALID")
    coverage = Decimal(str(coverage_days_after_delivery))
    safety = Decimal(str(safety_days))
    if coverage <= 0:
        raise ValueError("ORDERING_POLICY_COVERAGE_MUST_BE_POSITIVE")
    if safety < 0:
        raise ValueError("ORDERING_POLICY_SAFETY_NEGATIVE")
    minimum = Decimal(str(min_order_qty)) if min_order_qty is not None else None
    multiple = Decimal(str(order_multiple)) if order_multiple is not None else None
    if minimum is not None and minimum < 0:
        raise ValueError("ORDERING_POLICY_MIN_QTY_NEGATIVE")
    if multiple is not None and multiple <= 0:
        raise ValueError("ORDERING_POLICY_MULTIPLE_MUST_BE_POSITIVE")
    clean_notes = str(notes or "").strip()[:255] or None

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_ordering_policy_table(cur)
        conn.commit()
        cur.execute(
            """INSERT INTO ordering_policy
               (scope_type,scope_key,order_weekday,delivery_weekday,
                coverage_days_after_delivery,safety_days,min_order_qty,
                order_multiple,enabled,notes,updated_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 order_weekday=VALUES(order_weekday),
                 delivery_weekday=VALUES(delivery_weekday),
                 coverage_days_after_delivery=VALUES(coverage_days_after_delivery),
                 safety_days=VALUES(safety_days),
                 min_order_qty=VALUES(min_order_qty),
                 order_multiple=VALUES(order_multiple),
                 enabled=VALUES(enabled),
                 notes=VALUES(notes),
                 updated_by=VALUES(updated_by),
                 updated_at=CURRENT_TIMESTAMP(6)""",
            (
                scope,key,ow,dw,coverage,safety,minimum,multiple,
                bool(enabled),clean_notes,device,
            ),
        )
        conn.commit()
        cur.execute(
            """SELECT ordering_policy_id,scope_type,scope_key,order_weekday,
                      delivery_weekday,coverage_days_after_delivery,safety_days,
                      min_order_qty,order_multiple,enabled,notes,updated_by,updated_at
               FROM ordering_policy
               WHERE scope_type=%s AND scope_key=%s""",
            (scope,key),
        )
        row = cur.fetchone()
        cur.close()
    return {"status":"SAVED","policy":row}


def _next_weekday_on_or_after(start: date, weekday: int) -> date:
    return start + timedelta(days=(int(weekday)-start.weekday()) % 7)


def _ordering_plan_from_policy(
    row: dict[str, Any],
    effective_oh: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    dos = _quick_check_effective_dos(row, effective_oh)
    selling_oh = _qc_decimal(dos.get("selling_equivalent_oh"))
    velocity = _qc_decimal(row.get("upc_velocity_7d"))
    if selling_oh is None or velocity is None or velocity <= 0:
        return {
            "status": dos.get("status") or "ORDER_QTY_BLOCKED",
            "action": "MONITOR",
            "suggested_order_qty": None,
            "reason": "Suggested quantity requires compatible OH-to-selling-UOM conversion and positive 7D velocity.",
            "ordering_calendar_required_for_quantity": False,
            "policy": policy,
            "effective_dos": dos,
        }

    today = business_today()
    order_date = _next_weekday_on_or_after(today, int(policy["order_weekday"]))
    delivery_delta = (int(policy["delivery_weekday"]) - int(policy["order_weekday"])) % 7
    if delivery_delta == 0:
        delivery_delta = 7
    delivery_date = order_date + timedelta(days=delivery_delta)

    days_to_delivery = Decimal((delivery_date - today).days)
    coverage = _qc_decimal(policy.get("coverage_days_after_delivery")) or Decimal("0")
    safety = _qc_decimal(policy.get("safety_days")) or Decimal("0")
    demand_days = days_to_delivery + coverage + safety
    target_units = velocity * demand_days
    raw_needed = max(Decimal("0"), target_units - selling_oh)

    suggested = raw_needed
    multiple = _qc_decimal(policy.get("order_multiple"))
    minimum = _qc_decimal(policy.get("min_order_qty"))
    if suggested > 0 and multiple is not None and multiple > 0:
        suggested = (suggested / multiple).to_integral_value(rounding=ROUND_CEILING) * multiple
    if suggested > 0 and minimum is not None and minimum > suggested:
        suggested = minimum

    return {
        "status": "ORDER_RECOMMENDATION_READY",
        "action": "ORDER" if suggested > 0 else "NO_ORDER",
        "suggested_order_qty": suggested,
        "suggested_order_uom": row.get("selling_uom"),
        "raw_required_qty": raw_needed,
        "target_inventory_qty": target_units,
        "effective_selling_oh": selling_oh,
        "velocity_7d": velocity,
        "days_supply": dos.get("days_supply"),
        "next_order_date": order_date,
        "next_delivery_date": delivery_date,
        "days_to_delivery": days_to_delivery,
        "coverage_days_after_delivery": coverage,
        "safety_days": safety,
        "demand_horizon_days": demand_days,
        "ordering_calendar_required_for_quantity": False,
        "policy": policy,
        "reason": (
            "Suggested quantity = demand through next delivery and configured coverage horizon "
            "minus effective selling-unit OH, rounded by configured order multiple/minimum."
        ),
    }


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
                count_note VARCHAR(255) NULL,
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

    if not _column_exists(cur, "dumping_discrepancy_queue", "resolved_by"):
        cur.execute(
            """ALTER TABLE dumping_discrepancy_queue
               ADD COLUMN resolved_by VARCHAR(128) NULL
               AFTER resolved_at"""
        )
    if not _column_exists(cur, "dumping_discrepancy_queue", "resolution_note"):
        cur.execute(
            """ALTER TABLE dumping_discrepancy_queue
               ADD COLUMN resolution_note VARCHAR(255) NULL
               AFTER resolved_by"""
        )

    if not _column_exists(cur, "manual_true_stock", "count_note"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN count_note VARCHAR(255) NULL
               AFTER override_status"""
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

    # v7.0.435: desktop Inventory worklist acknowledgement is separate from
    # True Stock authority. Clearing this worklist must never delete/supersede
    # the physical-count baseline used by Effective OH.
    if not _column_exists(cur, "manual_true_stock", "adjustment_list_cleared_at"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN adjustment_list_cleared_at DATETIME(6) NULL
               AFTER cancel_reason"""
        )
    if not _column_exists(cur, "manual_true_stock", "adjustment_list_cleared_by"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN adjustment_list_cleared_by VARCHAR(128) NULL
               AFTER adjustment_list_cleared_at"""
        )
    if not _column_exists(cur, "manual_true_stock", "adjustment_list_clear_note"):
        cur.execute(
            """ALTER TABLE manual_true_stock
               ADD COLUMN adjustment_list_clear_note VARCHAR(255) NULL
               AFTER adjustment_list_cleared_by"""
        )


def true_stock_adjustment_log(
    limit: int = 300,
    *,
    include_cleared: bool = False,
) -> dict[str, Any]:
    """Return physical True Stock count events for the desktop Inventory worklist.

    The worklist acknowledgement fields are display/workflow metadata only.
    override_status remains the inventory authority and is not changed here.
    """
    lim=max(1,min(int(limit or 300),1000))
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        ensure_true_stock_tables(cur)
        conn.commit()
        where="" if include_cleared else "WHERE mts.adjustment_list_cleared_at IS NULL"
        cur.execute(
            f"""SELECT mts.true_stock_id,
                       mts.family_id,
                       mts.main_article_number,
                       pf.family_description AS family_name,
                       mts.scope_type,
                       mts.article_number,
                       mts.ean_upc,
                       mts.true_stock_quantity,
                       mts.uom_code,
                       mts.system_oh_quantity,
                       mts.system_oh_uom_code,
                       mts.discrepancy_quantity,
                       mts.override_status,
                       mts.anchor_on_hand_file_id,
                       mts.anchor_movement_date,
                       mts.anchor_movement_file_id,
                       mts.count_note,
                       mts.submitted_by,
                       mts.submitted_at,
                       mts.superseded_at,
                       mts.superseded_by_oh_file_id,
                       mts.adjustment_list_cleared_at,
                       mts.adjustment_list_cleared_by,
                       mts.adjustment_list_clear_note,
                       (
                         SELECT dq.queue_status
                         FROM dumping_discrepancy_queue dq
                         WHERE dq.source_true_stock_id=mts.true_stock_id
                         ORDER BY dq.discrepancy_id DESC
                         LIMIT 1
                       ) AS dumping_status
                FROM manual_true_stock mts
                LEFT JOIN product_family pf ON pf.family_id=mts.family_id
                {where}
                ORDER BY mts.true_stock_id DESC
                LIMIT %s""",
            (lim,),
        )
        rows=cur.fetchall()
        cur.execute(
            """SELECT COUNT(*) AS n
               FROM manual_true_stock
               WHERE adjustment_list_cleared_at IS NULL"""
        )
        pending=int((cur.fetchone() or {}).get("n") or 0)
        cur.execute(
            """SELECT MAX(adjustment_list_cleared_at) AS cleared_at,
                      MAX(adjustment_list_cleared_by) AS cleared_by
               FROM manual_true_stock
               WHERE adjustment_list_cleared_at IS NOT NULL"""
        )
        last_clear=cur.fetchone() or {}
        cur.close()
    return {
        "contract_version":"TRUE_STOCK_ADJUSTMENT_LOG_V1",
        "count":len(rows),
        "uncleared_count":pending,
        "include_cleared":bool(include_cleared),
        "last_clear_at":last_clear.get("cleared_at"),
        "last_clear_by":last_clear.get("cleared_by"),
        "rows":rows,
        "rules":{
            "clear_action":"ACKNOWLEDGE_WORKLIST_ONLY",
            "clear_deletes_true_stock":False,
            "clear_changes_override_status":False,
            "clear_changes_effective_oh":False,
            "true_stock_rollforward":"ACTIVE_TRUE_STOCK_PLUS_VALID_MOVEMENTS_AFTER_ANCHOR",
        },
    }


def clear_true_stock_adjustment_log(
    actor: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Acknowledge the desktop adjustment worklist without touching True Stock."""
    who=str(actor or "UNKNOWN").strip()[:128] or "UNKNOWN"
    clear_note=str(note or "DUMPING_WORKLIST_CLEARED").strip()[:255] or None
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            ensure_true_stock_tables(cur)
            conn.commit()
            conn.start_transaction()
            cur.execute(
                """UPDATE manual_true_stock
                   SET adjustment_list_cleared_at=CURRENT_TIMESTAMP(6),
                       adjustment_list_cleared_by=%s,
                       adjustment_list_clear_note=%s
                   WHERE adjustment_list_cleared_at IS NULL""",
                (who,clear_note),
            )
            cleared=int(cur.rowcount or 0)
            cur.execute(
                """SELECT MAX(true_stock_id) AS last_true_stock_id
                   FROM manual_true_stock
                   WHERE adjustment_list_cleared_at IS NOT NULL"""
            )
            last_id=(cur.fetchone() or {}).get("last_true_stock_id")
            conn.commit()
            return {
                "status":"CLEARED",
                "cleared_count":cleared,
                "last_true_stock_id":last_id,
                "actor":who,
                "note":clear_note,
                "true_stock_baselines_unchanged":True,
                "effective_oh_unchanged":True,
                "dumping_queue_unchanged":True,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


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


def _stock_state(quantity: Any) -> dict[str, Any]:
    """Return an explicit inventory state without mutating the quantity."""
    if quantity is None:
        return {"negative_stock": False, "stock_status": "UNKNOWN"}
    try:
        q = Decimal(str(quantity))
    except Exception:
        return {"negative_stock": False, "stock_status": "UNKNOWN"}
    if q < 0:
        return {"negative_stock": True, "stock_status": "NEGATIVE"}
    if q == 0:
        return {"negative_stock": False, "stock_status": "ZERO"}
    return {"negative_stock": False, "stock_status": "POSITIVE"}


def _annotate_stock_state(row: dict[str, Any] | None, quantity_key: str = "current_oh") -> None:
    if row is not None:
        row.update(_stock_state(row.get(quantity_key)))


def _numeric_key(value: str) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return ""
    return digits.lstrip("0") or "0"


def _sales_lineage_pred(
    cur,
    upc_id: int,
    *,
    column_upc_id: str = "upc_id",
    column_ean: str = "ean_upc",
) -> tuple[str, tuple[Any, ...]]:
    """Read sales by canonical UPC id OR every safe raw EAN/UPC alias."""
    cur.execute("SELECT ean_upc FROM selling_upc WHERE upc_id=%s LIMIT 1",(int(upc_id),))
    row=cur.fetchone()
    ean=str((row or {}).get("ean_upc") or "").strip()
    if not ean:
        return f"{column_upc_id}=%s",(int(upc_id),)
    ean_pred,ean_args=source_ean_predicate(column_ean,ean)
    return (
        f"({column_upc_id}=%s OR {ean_pred})",
        (int(upc_id),*ean_args),
    )

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
                       current_price_source,current_price_asof_date,
                       sales_dollars_7d,pos_qty_7d,sales_days_7d,
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
                       current_price_source,current_price_asof_date,
                       sales_dollars_7d,pos_qty_7d,sales_days_7d,
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
        for row in rows:
            _annotate_stock_state(row)
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
            _annotate_stock_state(row)
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



def _qc_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None



def _quick_check_daily_sales(
    cur,
    row: dict[str, Any],
    limit: int = 28,
) -> list[dict[str, Any]]:
    """Canonical completed POS data-day series for GP$ + average selling price.

    Direct single-day files and approved one-gap residual backfills use the same
    canonical data-day rules as Quick Check velocity. Multi-gap period reports
    remain source-period evidence and are not expanded into invented daily rows.
    """
    upc_id = int(row["upc_id"])
    family_id = int(row["family_id"])
    data_days = source_data_days(
        cur,
        "sales_by_price_type",
        limit=max(1, min(int(limit or 28), 60)),
        up_to=completed_through_date(),
    )
    if not data_days:
        return []

    daily: dict[date, dict[str, Decimal]] = {}
    direct_days = [
        d for d in data_days
        if d.get("coverage_kind") != "DERIVED_PERIOD_RESIDUAL"
    ]
    if direct_days:
        clauses: list[str] = []
        args: list[Any] = []
        for d in direct_days:
            clauses.append("(file_id=%s AND period_start_date=%s AND period_end_date=%s)")
            args.extend([int(d["file_id"]), d["date"], d["date"]])
        sales_pred,sales_pred_args=_sales_lineage_pred(cur,upc_id)
        cur.execute(
            f"""SELECT period_end_date AS business_date,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                  AND {sales_pred}
                GROUP BY period_end_date""",
            tuple(args) + tuple(sales_pred_args),
        )
        for r in cur.fetchall():
            daily[r["business_date"]] = {
                "sales": Decimal(str(r.get("sales_amount") or 0)),
                "qty": Decimal(str(r.get("sold_quantity") or 0)),
            }

    derived_days = [
        d for d in data_days
        if d.get("coverage_kind") == "DERIVED_PERIOD_RESIDUAL"
    ]
    if derived_days and _table_exists(cur, "pos_daily_backfill_observation"):
        clauses = []
        args = []
        for d in derived_days:
            clauses.append("(source_file_id=%s AND business_date=%s)")
            args.extend([int(d["file_id"]), d["date"]])
        sales_pred,sales_pred_args=_sales_lineage_pred(cur,upc_id)
        cur.execute(
            f"""SELECT business_date,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM pos_daily_backfill_observation
                WHERE ({' OR '.join(clauses)})
                  AND {sales_pred}
                GROUP BY business_date""",
            tuple(args) + tuple(sales_pred_args),
        )
        for r in cur.fetchall():
            d = r["business_date"]
            prev = daily.get(d, {"sales": Decimal("0"), "qty": Decimal("0")})
            daily[d] = {
                "sales": prev["sales"] + Decimal(str(r.get("sales_amount") or 0)),
                "qty": prev["qty"] + Decimal(str(r.get("sold_quantity") or 0)),
            }

    factor = _qc_decimal(row.get("base_qty_per_selling_unit"))
    selling_uom = str(row.get("selling_uom") or "").strip().upper()
    base_uom = str(row.get("base_uom") or "").strip().upper()
    if factor is None and selling_uom and base_uom and selling_uom == base_uom:
        factor = Decimal("1")

    max_day = max(d["date"] for d in data_days)
    cur.execute(
        """SELECT business_date,cost_observation_id,source_type,
                  COALESCE(cost_per_base_uom,cost_amount) AS c,
                  CASE
                    WHEN source_type='MOVEMENT_RECEIPT_VALUATION' THEN 1
                    WHEN source_type='ON_HAND_EXPLICIT_COST_FALLBACK' THEN 2
                    WHEN source_type IN (
                        'FROZEN_INVENTORY_OFFICIAL_COST',
                        'LIVE_FRESH_SUGGESTION_OFFICIAL_COST'
                    ) THEN 3
                    WHEN source_type='USER_CONFIRMED_FAMILY_COST' THEN 4
                    ELSE 9
                  END AS source_priority
           FROM article_cost_observation
           WHERE family_id=%s
             AND business_date<=%s
             AND cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND COALESCE(cost_per_base_uom,cost_amount)>0
           ORDER BY source_priority ASC,business_date DESC,cost_observation_id DESC""",
        (family_id, max_day),
    )
    cost_rows = cur.fetchall()

    out: list[dict[str, Any]] = []
    for data_day in sorted(data_days, key=lambda x: x["date"]):
        d = data_day["date"]
        obs = daily.get(d, {"sales": Decimal("0"), "qty": Decimal("0")})
        sales = obs["sales"]
        qty = obs["qty"]
        avg_price = (sales / qty) if qty != 0 else None

        applicable_cost = None
        cost_source = None
        cost_date = None
        if factor is not None:
            for cr in cost_rows:
                if cr.get("business_date") is not None and cr["business_date"] <= d:
                    applicable_cost = Decimal(str(cr["c"])) * factor
                    cost_source = cr.get("source_type")
                    cost_date = cr.get("business_date")
                    break

        gp_dollars = (
            sales - (qty * applicable_cost)
            if applicable_cost is not None
            else None
        )
        out.append(
            {
                "business_date": d,
                "sales_amount": sales,
                "sold_quantity": qty,
                "avg_sold_price": avg_price,
                "applicable_cost_per_selling_unit": applicable_cost,
                "applicable_cost_source": cost_source,
                "applicable_cost_date": cost_date,
                "gp_dollars": gp_dollars,
                "selling_uom": row.get("selling_uom"),
                "coverage_kind": data_day.get("coverage_kind"),
            }
        )
    return out


def _quick_check_price_velocity_history(
    daily_sales: list[dict[str, Any]],
    max_points: int = 8,
) -> list[dict[str, Any]]:
    buckets: dict[Decimal, dict[str, Any]] = {}
    for r in daily_sales:
        qty = _qc_decimal(r.get("sold_quantity")) or Decimal("0")
        price = _qc_decimal(r.get("avg_sold_price"))
        if price is None or qty <= 0:
            continue
        price_key = price.quantize(Decimal("0.01"))
        bucket = buckets.setdefault(
            price_key,
            {
                "price": price_key,
                "sold_quantity": Decimal("0"),
                "data_days": 0,
                "gp_dollars": Decimal("0"),
                "gp_days": 0,
                "last_date": None,
            },
        )
        bucket["sold_quantity"] += qty
        bucket["data_days"] += 1
        gp = _qc_decimal(r.get("gp_dollars"))
        if gp is not None:
            bucket["gp_dollars"] += gp
            bucket["gp_days"] += 1
        d = r.get("business_date")
        if d is not None and (bucket["last_date"] is None or d > bucket["last_date"]):
            bucket["last_date"] = d

    rows: list[dict[str, Any]] = []
    for b in buckets.values():
        days = int(b["data_days"])
        rows.append(
            {
                "price": b["price"],
                "velocity": (b["sold_quantity"] / Decimal(days)) if days else None,
                "sold_quantity": b["sold_quantity"],
                "data_days": days,
                "gp_per_day": (
                    b["gp_dollars"] / Decimal(b["gp_days"])
                    if b["gp_days"] == days and days > 0
                    else None
                ),
                "last_date": b["last_date"],
            }
        )
    rows.sort(key=lambda x: (x.get("last_date") or date.min, x.get("price") or Decimal("0")), reverse=True)
    return rows[: max(1, min(int(max_points or 8), 20))]


def _quick_check_metric_trends(
    row: dict[str, Any],
    daily_sales: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(daily_sales, key=lambda x: x["business_date"])
    current = ordered[-7:]
    previous = ordered[-14:-7] if len(ordered) >= 14 else []

    def _sum(block: list[dict[str, Any]], key: str) -> Decimal | None:
        vals = [_qc_decimal(x.get(key)) for x in block]
        if not vals:
            return None
        return sum((v or Decimal("0") for v in vals), Decimal("0"))

    def _weighted_price(block: list[dict[str, Any]]) -> Decimal | None:
        sales = _sum(block, "sales_amount")
        qty = _sum(block, "sold_quantity")
        if sales is None or qty is None or qty == 0:
            return None
        return sales / qty

    def _gp_per_day(block: list[dict[str, Any]]) -> Decimal | None:
        if not block or any(_qc_decimal(x.get("gp_dollars")) is None for x in block):
            return None
        total = sum((_qc_decimal(x.get("gp_dollars")) or Decimal("0") for x in block), Decimal("0"))
        return total / Decimal(len(block))

    def _latest_cost(block: list[dict[str, Any]]) -> Decimal | None:
        for x in reversed(block):
            v = _qc_decimal(x.get("applicable_cost_per_selling_unit"))
            if v is not None:
                return v
        return None

    def _trend(current_value: Decimal | None, previous_value: Decimal | None, unit: str) -> dict[str, Any]:
        if current_value is None or previous_value is None:
            return {
                "direction": "NA",
                "current": current_value,
                "previous": previous_value,
                "delta": None,
                "unit": unit,
            }
        delta = current_value - previous_value
        return {
            "direction": "UP" if delta > 0 else ("DOWN" if delta < 0 else "FLAT"),
            "current": current_value,
            "previous": previous_value,
            "delta": delta,
            "unit": unit,
        }

    current_qty = _sum(current, "sold_quantity")
    previous_qty = _sum(previous, "sold_quantity")
    current_velocity = (
        current_qty / Decimal(len(current))
        if current_qty is not None and current
        else None
    )
    previous_velocity = (
        previous_qty / Decimal(len(previous))
        if previous_qty is not None and previous
        else None
    )
    current_avg_price = _weighted_price(current)
    previous_avg_price = _weighted_price(previous)

    configured_price = _qc_decimal(row.get("current_price"))
    previous_distinct_price = None
    if configured_price is not None:
        for x in reversed(ordered):
            p = _qc_decimal(x.get("avg_sold_price"))
            if p is not None and abs(p - configured_price) >= Decimal("0.005"):
                previous_distinct_price = p
                break
    if previous_distinct_price is None:
        previous_distinct_price = previous_avg_price

    current_cost = _qc_decimal(row.get("current_cost_per_selling_unit"))
    previous_cost = _latest_cost(previous)
    current_gp_pct = _qc_decimal(row.get("gp_pct_current"))
    previous_gp_pct = None
    if previous_avg_price is not None and previous_avg_price > 0 and previous_cost is not None:
        previous_gp_pct = (previous_avg_price - previous_cost) / previous_avg_price

    current_gp_day = _qc_decimal(row.get("gp_per_day_7d"))
    calculated_current_gp_day = _gp_per_day(current)
    if current_gp_day is None:
        current_gp_day = calculated_current_gp_day
    previous_gp_day = _gp_per_day(previous)

    current_gp_total = _qc_decimal(row.get("gp_dollars_7d"))
    if current_gp_total is None and current:
        current_gp_total = _sum(current, "gp_dollars")
    previous_gp_total = _sum(previous, "gp_dollars") if previous and all(
        _qc_decimal(x.get("gp_dollars")) is not None for x in previous
    ) else None

    selling_uom = str(row.get("selling_uom") or "").strip() or "unit"
    result = {
        "basis": "CURRENT_7_COMPLETED_POS_DATA_DAYS_VS_PREVIOUS_7_COMPLETED_POS_DATA_DAYS",
        "current_data_days": len(current),
        "previous_data_days": len(previous),
        "price": _trend(configured_price, previous_distinct_price, f"$/{selling_uom}"),
        "cost": _trend(current_cost, previous_cost, f"$/{selling_uom}"),
        "gp_pct": _trend(current_gp_pct, previous_gp_pct, "ratio"),
        "gp_dollars_7d": _trend(current_gp_total, previous_gp_total, "$/7D"),
        "gp_per_day": _trend(current_gp_day, previous_gp_day, "$/day"),
        "qty_7d": _trend(current_qty, previous_qty, f"{selling_uom}/7D"),
        "velocity": _trend(current_velocity, previous_velocity, f"{selling_uom}/day"),
    }
    return result


def _quick_check_sales_trend(
    cur,
    upc_id: int,
    limit: int = 40,
) -> list[dict[str, Any]]:
    """Return source-period sales observations without inventing daily grain."""
    sales_pred,sales_pred_args=_sales_lineage_pred(cur,upc_id)
    cur.execute(
        f"""SELECT period_start_date,period_end_date,temporal_grain,price_type,
                  sales_amount,sold_quantity,avg_sold_price,
                  batch_id,file_id,sheet_id,raw_id,source_row_number
           FROM sales_period_observation
           WHERE {sales_pred}
           ORDER BY period_end_date DESC,period_start_date DESC,
                    file_id DESC,raw_id DESC
           LIMIT %s""",
        (*sales_pred_args, max(1, min(int(limit or 40), 120))),
    )
    rows = cur.fetchall()
    for row in rows:
        start = row.get("period_start_date")
        end = row.get("period_end_date")
        row["period_days"] = (
            (end - start).days + 1
            if isinstance(start, date) and isinstance(end, date) and end >= start
            else None
        )
    return rows


def _quick_check_cost_trend(
    cur,
    family_id: int,
    limit: int = 40,
) -> list[dict[str, Any]]:
    """Return authoritative/observed family cost history with source lineage."""
    cur.execute(
        """SELECT co.cost_observation_id,co.business_date,
                  a.article_number,
                  co.source_type,co.movement_type,
                  co.cost_amount,co.cost_per_base_uom,
                  cu.uom_code AS cost_uom,
                  bu.uom_code AS base_uom,
                  co.currency_code,co.cost_status,co.confidence,
                  co.batch_id,co.file_id,co.sheet_id,
                  co.raw_table_name,co.raw_id,co.source_row_number
           FROM article_cost_observation co
           LEFT JOIN article a ON a.article_id=co.article_id
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
           WHERE co.family_id=%s
             AND (co.cost_per_base_uom IS NOT NULL OR co.cost_amount IS NOT NULL)
           ORDER BY co.business_date DESC,
                    co.cost_observation_id DESC
           LIMIT %s""",
        (family_id, max(1, min(int(limit or 40), 120))),
    )
    return cur.fetchall()


def _quick_check_family_relationships(
    cur,
    family_id: int,
    related_upcs: list[dict[str, Any]],
) -> dict[str, Any]:
    cur.execute(
        """SELECT pf.family_id,pf.main_article_number,pf.family_description
           FROM product_family pf
           WHERE pf.family_id=%s
           LIMIT 1""",
        (family_id,),
    )
    family = cur.fetchone() or {
        "family_id": family_id,
        "main_article_number": None,
        "family_description": None,
    }

    cur.execute(
        """SELECT a.article_id,a.article_number,a.article_description,
                  baf.relationship_type,baf.is_primary,
                  baf.mapping_status,baf.confidence
           FROM bridge_article_family baf
           JOIN article a ON a.article_id=baf.article_id
           WHERE baf.family_id=%s
             AND baf.mapping_status='CONFIRMED'
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           ORDER BY
             CASE baf.relationship_type WHEN 'MAIN' THEN 0 ELSE 1 END,
             a.article_number""",
        (family_id,),
    )
    articles = cur.fetchall()

    cur.execute(
        """SELECT article_number,
                  MAX(posting_date) AS latest_receipt_date,
                  GROUP_CONCAT(DISTINCT entry_uom_code ORDER BY entry_uom_code) AS receiving_uoms,
                  GROUP_CONCAT(DISTINCT base_uom_code ORDER BY base_uom_code) AS base_uoms
           FROM movement_history
           WHERE family_id=%s
             AND movement_type IN ('101','109')
             AND article_number IS NOT NULL
           GROUP BY article_number
           ORDER BY latest_receipt_date DESC,article_number""",
        (family_id,),
    )
    receiving_articles = cur.fetchall()

    return {
        "family": family,
        "articles": articles,
        "selling_upcs": related_upcs,
        "receiving_articles_observed": receiving_articles,
        "receiving_relationship_note": (
            "receiving_articles_observed is source history, not an inferred ordering master"
        ),
    }


def _quick_check_promotion(row: dict[str, Any]) -> dict[str, Any]:
    price_type = str(row.get("current_price_type") or "").strip().upper()
    active = price_type == "SALE"
    return {
        "is_on_promotion": active,
        "price_type": row.get("current_price_type"),
        "current_price": row.get("current_price"),
        "classification": "PROMOTION" if active else "REGULAR",
        "promotion_definition": "PRICE_TYPE_SALE_ONLY",
        "tpr_is_promotion": False,
    }


def _quick_check_effective_dos(
    row: dict[str, Any],
    effective_oh: dict[str, Any],
) -> dict[str, Any]:
    qty = _qc_decimal(effective_oh.get("quantity"))
    velocity = _qc_decimal(row.get("upc_velocity_7d"))
    if qty is None:
        return {
            "days_supply": None,
            "status": "OH_NOT_AVAILABLE",
            "calculation_uom": None,
        }
    if velocity is None or velocity <= 0:
        return {
            "days_supply": None,
            "status": "NO_POSITIVE_7D_VELOCITY",
            "calculation_uom": None,
        }

    oh_uom = str(effective_oh.get("uom") or "").strip().upper()
    selling_uom = str(row.get("selling_uom") or "").strip().upper()
    base_uom = str(row.get("base_uom") or "").strip().upper()
    factor = _qc_decimal(row.get("base_qty_per_selling_unit"))

    selling_qty = None
    calculation_uom = None
    if oh_uom and selling_uom and oh_uom == selling_uom:
        selling_qty = qty
        calculation_uom = selling_uom
    elif (
        oh_uom
        and base_uom
        and oh_uom == base_uom
        and factor is not None
        and factor > 0
    ):
        selling_qty = qty / factor
        calculation_uom = selling_uom or base_uom

    if selling_qty is None:
        return {
            "days_supply": None,
            "status": "OH_TO_SELLING_UOM_CONVERSION_UNRESOLVED",
            "calculation_uom": None,
        }

    return {
        "days_supply": selling_qty / velocity,
        "status": "CALCULATED",
        "calculation_uom": calculation_uom,
        "selling_equivalent_oh": selling_qty,
        "velocity_7d": velocity,
    }


def _quick_check_ordering(
    row: dict[str, Any],
    effective_oh: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not effective_oh.get("analysis_usable"):
        return {
            "status": "BLOCKED",
            "action": "VERIFY_INVENTORY_POSITION",
            "suggested_order_qty": None,
            "reason": "Effective OH roll-forward is not analysis-usable.",
            "ordering_calendar_required_for_quantity": policy is None,
            "policy": policy,
        }

    qty = _qc_decimal(effective_oh.get("quantity"))
    if qty is not None and qty < 0:
        return {
            "status": "COUNT_REQUIRED",
            "action": "SUBMIT_TRUE_STOCK",
            "suggested_order_qty": None,
            "reason": "Effective OH is negative; physical count takes precedence.",
            "ordering_calendar_required_for_quantity": policy is None,
            "policy": policy,
        }

    dos = _quick_check_effective_dos(row, effective_oh)
    days_supply = _qc_decimal(dos.get("days_supply"))
    if days_supply is None:
        return {
            "status": dos.get("status"),
            "action": "MONITOR",
            "suggested_order_qty": None,
            "reason": "A safe order quantity requires compatible OH/velocity UOM evidence.",
            "ordering_calendar_required_for_quantity": policy is None,
            "policy": policy,
            "effective_dos": dos,
        }

    if policy is None:
        return {
            "status": "POLICY_NOT_CONFIGURED",
            "action": "CONFIGURE_ORDERING_POLICY",
            "suggested_order_qty": None,
            "days_supply": days_supply,
            "effective_dos": dos,
            "ordering_calendar_required_for_quantity": True,
            "policy": None,
            "reason": (
                "Effective DOS is available, but no authoritative ordering policy matches this item. "
                "No order quantity is inferred."
            ),
        }

    return _ordering_plan_from_policy(row, effective_oh, policy)


def _quick_check_highlights(
    row: dict[str, Any],
    effective_oh: dict[str, Any],
    active_true_stock: dict[str, Any] | None,
    promotion: dict[str, Any],
    ordering: dict[str, Any],
) -> list[dict[str, Any]]:
    highlights: list[dict[str, Any]] = []

    if row.get("quick_check_status") == "QA_HOLD":
        highlights.append(
            {
                "code": "QA_HOLD",
                "severity": "HIGH",
                "text": str(row.get("blocking_reason") or "Quick Check row is on QA hold."),
            }
        )

    if active_true_stock:
        highlights.append(
            {
                "code": "TRUE_STOCK_ACTIVE",
                "severity": "INFO",
                "text": "Active True Stock is the effective inventory reference until the next OH upload.",
            }
        )

    stock = _stock_state(effective_oh.get("quantity"))
    if stock.get("negative_stock"):
        highlights.append(
            {
                "code": "NEGATIVE_EFFECTIVE_OH",
                "severity": "HIGH",
                "text": "Effective OH is negative; physical count is required.",
            }
        )

    if promotion.get("is_on_promotion"):
        highlights.append(
            {
                "code": "PROMOTION_ACTIVE",
                "severity": "INFO",
                "text": f'Current price type is {promotion.get("price_type")}.',
            }
        )

    v7 = _qc_decimal(row.get("upc_velocity_7d"))
    v30 = _qc_decimal(row.get("upc_velocity_30d"))
    if v7 is not None and v30 is not None:
        if v30 > 0:
            ratio = v7 / v30
            if ratio >= Decimal("1.20"):
                highlights.append(
                    {
                        "code": "VELOCITY_UP",
                        "severity": "INFO",
                        "text": "7D UPC velocity is at least 20% above 30D velocity.",
                    }
                )
            elif ratio <= Decimal("0.80"):
                highlights.append(
                    {
                        "code": "VELOCITY_DOWN",
                        "severity": "INFO",
                        "text": "7D UPC velocity is at least 20% below 30D velocity.",
                    }
                )
        elif v7 > 0:
            highlights.append(
                {
                    "code": "RECENT_VELOCITY_WITH_ZERO_30D_BASE",
                    "severity": "INFO",
                    "text": "Recent 7D velocity is positive while the 30D baseline is zero.",
                }
            )

    if ordering.get("status") in {"COUNT_REQUIRED", "BLOCKED"}:
        highlights.append(
            {
                "code": "ORDERING_ATTENTION",
                "severity": "HIGH",
                "text": str(ordering.get("reason") or ordering.get("action")),
            }
        )

    return highlights


def get_quick_check_detail(upc: str) -> dict[str, Any] | None:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        row = _lookup_qc_row(cur, upc)
        if not row:
            cur.close()
            return None

        latest_oh_file_id = _refresh_expired_true_stock(cur)
        ensure_ordering_policy_table(cur)
        family_id = int(row["family_id"])
        system_oh = _system_oh_context(cur, row)
        system_position = _system_position(cur, system_oh)
        true_stock = _active_true_stock(cur, system_oh)
        actual_position = _actual_position(cur, true_stock)
        true_stock_history = _true_stock_history(cur, system_oh)
        sales_trend = _quick_check_sales_trend(cur, int(row["upc_id"]))
        daily_sales_trend = _quick_check_daily_sales(cur, row, limit=28)
        price_velocity_history = _quick_check_price_velocity_history(daily_sales_trend)
        metric_trends = _quick_check_metric_trends(row, daily_sales_trend)
        cost_trend = _quick_check_cost_trend(cur, family_id)

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
        family_relationships = _quick_check_family_relationships(
            cur,
            family_id,
            related,
        )

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
            "movement_coverage_expected_through": effective_position.get("movement_coverage_expected_through") if effective_position else None,
            "movement_coverage_complete": effective_position.get("movement_coverage_complete") if effective_position else False,
            "missing_movement_day_count": effective_position.get("missing_movement_day_count") if effective_position else None,
            "missing_movement_days": effective_position.get("missing_movement_days") if effective_position else [],
            "latest_complete_movement_date": effective_position.get("latest_complete_movement_date") if effective_position else None,
            "submitted_by": true_stock.get("submitted_by") if true_stock else None,
            "scope_type": (true_stock.get("scope_type") if true_stock else system_oh.get("scope_type")) if (true_stock or system_oh) else None,
            "article_id": (true_stock.get("article_id") if true_stock else system_oh.get("article_id")) if (true_stock or system_oh) else None,
            "article_number": (true_stock.get("article_number") if true_stock else system_oh.get("article_number")) if (true_stock or system_oh) else None,
        }

        _annotate_stock_state(row)
        effective_oh.update(_stock_state(effective_oh.get("quantity")))

        promotion = _quick_check_promotion(row)
        ordering_policy = _resolve_ordering_policy(cur, row)
        ordering = _quick_check_ordering(row, effective_oh, ordering_policy)
        highlights = _quick_check_highlights(
            row,
            effective_oh,
            true_stock,
            promotion,
            ordering,
        )

        detail = {
            "contract_version": "QUICK_CHECK_APP_V1",
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
                "movement_coverage_expected_through": system_position.get("movement_coverage_expected_through") if system_position else None,
                "movement_coverage_complete": system_position.get("movement_coverage_complete") if system_position else False,
                "missing_movement_day_count": system_position.get("missing_movement_day_count") if system_position else None,
                "missing_movement_days": system_position.get("missing_movement_days") if system_position else [],
                "latest_complete_movement_date": system_position.get("latest_complete_movement_date") if system_position else None,
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
            "promotion": promotion,
            "sales_trend": sales_trend,
            "daily_sales_trend": daily_sales_trend,
            "price_velocity_history": price_velocity_history,
            "metric_trends": metric_trends,
            "sweet_spot": {
                "price": row.get("sweet_spot_price"),
                "basis": "HISTORICAL_MAX_AVG_GP_DOLLARS_PER_COMPLETED_POS_DATA_DAY",
                "window": "LATEST_30_COMPLETED_POS_DATA_DAYS",
                "selling_uom": row.get("selling_uom"),
            },
            "cost_trend": cost_trend,
            "highlights": highlights,
            "family_relationships": family_relationships,
            "related_upcs": related,
            "ordering": ordering,
            "inventory_policy": {
                "system_oh_quantity_basis": "UNRESTRICTED_ONLY",
                "oh_cost_derivation": "TOTAL_VALUE_DIV_UNRESTRICTED_WHEN_VALID",
                "ignored_source_fields": [
                    "Stock in Transit",
                    "Value in Transit",
                    "In Transfer (Site)",
                    "Value in Stock Tfr",
                ],
                "ignored_fields_must_not_affect": [
                    "OH",
                    "OH_COST",
                    "INVENTORY_VALUATION",
                    "DOS",
                    "COST_CONVERSION",
                ],
            },
        }
        _annotate_stock_state(detail["system_oh"], "quantity")
        if detail["actual_oh"] is not None:
            _annotate_stock_state(detail["actual_oh"], "quantity")
        conn.commit()
        cur.close()
        return detail


def submit_true_stock(
    upc: str,
    true_stock_quantity: Decimal,
    true_stock_uom: str,
    device: str,
    note: str | None = None,
) -> dict[str, Any]:
    qty = Decimal(str(true_stock_quantity))
    submitted_uom = str(true_stock_uom or "").strip().upper()
    count_note = str(note or "").strip()[:255] or None
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
                    override_status,count_note,submitted_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s,%s)""",
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
                    count_note,
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
                "count_note": count_note,
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
        movement_days = list((system_position or {}).get("movement_days") or [])
        canonical_movement_pairs = [
            {"file_id": int(fid), "posting_date": day}
            for fid, day in zip(movement_file_ids, movement_days)
        ]
        family_id = int(row["family_id"]) if row.get("family_id") is not None else None
        article_id = int(system_oh["article_id"]) if system_oh and system_oh.get("article_id") is not None else None

        family_movement_history = []
        exact_article_movement_history = []
        movement_summary_by_article = []
        if canonical_movement_pairs and family_id is not None:
            clauses = []
            pair_args = []
            for pair in canonical_movement_pairs:
                clauses.append("(file_id=%s AND posting_date=%s)")
                pair_args.extend([pair["file_id"], pair["posting_date"]])
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
                      AND ({' OR '.join(clauses)})
                    ORDER BY posting_date,file_id,article_number,movement_type,
                             raw_id,source_row_number""",
                (family_id, *pair_args),
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
                "canonical_post_anchor_file_date_pairs": canonical_movement_pairs,
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


def inventory_rollforward_candidates(
    movement_date: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Read-only candidate list for validating OH + signed movement roll-forward.

    Selects one canonical valid MVT file for the requested business date (or the
    latest valid MVT data day when omitted), aggregates source-signed base
    quantities by Article/UOM, and attaches a representative Quick Check UPC.
    No inventory data or authority is modified.
    """
    limit = max(1, min(int(limit or 20), 100))

    requested_date = None
    if movement_date:
        try:
            requested_date = datetime.fromisoformat(str(movement_date)).date()
        except Exception as exc:
            raise ValueError("INVALID_MOVEMENT_DATE") from exc

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        days = source_data_days(cur, "movement")
        if requested_date is not None:
            day = next((x for x in days if x["date"] == requested_date), None)
        else:
            day = days[0] if days else None

        if not day:
            cur.close()
            return {
                "requested_date": requested_date,
                "canonical_movement_day": None,
                "lineage_status": (
                    "REQUESTED_DAY_NOT_CANONICAL_COMPLETE"
                    if requested_date is not None
                    else "NO_CANONICAL_COMPLETE_MOVEMENT_DAY"
                ),
                "count": 0,
                "results": [],
                "diagnostic_note": (
                    "The requested movement business date has no canonical COMPLETE snapshot. "
                    "Same-day provisional MVT exports are intentionally excluded from daily authority."
                    if requested_date is not None
                    else "No canonical COMPLETE movement day is currently available."
                ),
            }

        file_id = int(day["file_id"])
        business_date = day["date"]

        # v7.0.61: expose the canonical MVT file's raw -> normalized lineage so a
        # zero candidate count is diagnosable instead of being mistaken for
        # proof that there were no posted movements.
        cur.execute(
            """SELECT file_id,batch_id,original_filename,source_type,
                      processing_status,source_row_count,error_count,
                      date_semantics_status,coverage_type,
                      coverage_start_date,coverage_end_date,
                      header_period_start_date,header_period_end_date,
                      upload_timestamp
               FROM ingest_file
               WHERE file_id=%s
               LIMIT 1""",
            (file_id,),
        )
        canonical_file = cur.fetchone()

        cur.execute(
            """SELECT COUNT(*) AS c
               FROM raw_movement r
               JOIN ingest_sheet s ON s.sheet_id=r.sheet_id
               WHERE s.file_id=%s""",
            (file_id,),
        )
        raw_movement_row_count = int((cur.fetchone() or {}).get("c") or 0)

        cur.execute(
            """SELECT COUNT(*) AS total_rows,
                      SUM(CASE WHEN posting_date=%s THEN 1 ELSE 0 END) AS canonical_date_rows,
                      SUM(CASE WHEN base_quantity IS NOT NULL THEN 1 ELSE 0 END) AS base_qty_present_rows,
                      SUM(CASE WHEN base_quantity IS NOT NULL
                                    AND base_quantity<>0 THEN 1 ELSE 0 END) AS nonzero_base_qty_rows,
                      SUM(CASE WHEN article_id IS NOT NULL THEN 1 ELSE 0 END) AS article_mapped_rows,
                      SUM(CASE WHEN family_id IS NOT NULL THEN 1 ELSE 0 END) AS family_mapped_rows,
                      COUNT(DISTINCT article_number) AS distinct_articles,
                      COUNT(DISTINCT family_id) AS distinct_families,
                      GROUP_CONCAT(DISTINCT DATE_FORMAT(posting_date,'%%Y-%%m-%%d')
                                   ORDER BY posting_date SEPARATOR ',') AS posting_dates,
                      GROUP_CONCAT(DISTINCT base_uom_code
                                   ORDER BY base_uom_code SEPARATOR ',') AS base_uoms,
                      GROUP_CONCAT(DISTINCT movement_type
                                   ORDER BY movement_type SEPARATOR ',') AS movement_types
               FROM movement_history
               WHERE file_id=%s""",
            (business_date, file_id),
        )
        mh = cur.fetchone() or {}
        movement_history_summary = {
            "total_rows": int(mh.get("total_rows") or 0),
            "canonical_date_rows": int(mh.get("canonical_date_rows") or 0),
            "base_qty_present_rows": int(mh.get("base_qty_present_rows") or 0),
            "nonzero_base_qty_rows": int(mh.get("nonzero_base_qty_rows") or 0),
            "article_mapped_rows": int(mh.get("article_mapped_rows") or 0),
            "family_mapped_rows": int(mh.get("family_mapped_rows") or 0),
            "distinct_articles": int(mh.get("distinct_articles") or 0),
            "distinct_families": int(mh.get("distinct_families") or 0),
            "posting_dates": (
                str(mh.get("posting_dates") or "").split(",")
                if mh.get("posting_dates")
                else []
            ),
            "base_uoms": (
                str(mh.get("base_uoms") or "").split(",")
                if mh.get("base_uoms")
                else []
            ),
            "movement_types": (
                str(mh.get("movement_types") or "").split(",")
                if mh.get("movement_types")
                else []
            ),
        }

        apply_types = sorted(UNRESTRICTED_APPLY_AS_SIGNED)
        apply_placeholders = ",".join(["%s"] * len(apply_types))
        cur.execute(
            f"""SELECT article_id,article_number,family_id,base_uom_code,
                      COUNT(*) AS movement_row_count,
                      COALESCE(SUM(base_quantity),0) AS movement_delta,
                      GROUP_CONCAT(DISTINCT movement_type
                                   ORDER BY movement_type SEPARATOR ',') AS movement_types
               FROM movement_history
               WHERE file_id=%s
                 AND posting_date=%s
                 AND base_quantity IS NOT NULL
                 AND movement_type IN ({apply_placeholders})
               GROUP BY article_id,article_number,family_id,base_uom_code
               HAVING COALESCE(SUM(base_quantity),0)<>0
               ORDER BY ABS(COALESCE(SUM(base_quantity),0)) DESC,
                        article_number
               LIMIT %s""",
            (file_id, business_date, *apply_types, limit * 4),
        )
        movement_groups = cur.fetchall()

        results = []
        seen = set()
        for g in movement_groups:
            article_id = g.get("article_id")
            family_id = g.get("family_id")
            if article_id is None and family_id is None:
                continue

            if article_id is not None:
                cur.execute(
                    """SELECT upc_id,ean_upc,article_id,article_number,family_id,
                              main_article_number,selling_description,selling_uom,
                              base_uom,current_oh,current_oh_uom,oh_date,
                              quick_check_status,blocking_reason
                       FROM quick_check_current
                       WHERE article_id=%s
                       ORDER BY CASE quick_check_status
                                  WHEN 'READY' THEN 1
                                  WHEN 'QA_HOLD' THEN 2
                                  ELSE 3
                                END,
                                CASE WHEN current_oh IS NOT NULL THEN 0 ELSE 1 END,
                                ean_upc
                       LIMIT 1""",
                    (article_id,),
                )
            else:
                cur.execute(
                    """SELECT upc_id,ean_upc,article_id,article_number,family_id,
                              main_article_number,selling_description,selling_uom,
                              base_uom,current_oh,current_oh_uom,oh_date,
                              quick_check_status,blocking_reason
                       FROM quick_check_current
                       WHERE family_id=%s
                       ORDER BY CASE quick_check_status
                                  WHEN 'READY' THEN 1
                                  WHEN 'QA_HOLD' THEN 2
                                  ELSE 3
                                END,
                                CASE WHEN current_oh IS NOT NULL THEN 0 ELSE 1 END,
                                ean_upc
                       LIMIT 1""",
                    (family_id,),
                )
            qc = cur.fetchone()
            if not qc:
                continue

            key = (qc.get("ean_upc"), g.get("article_number"), g.get("base_uom_code"))
            if key in seen:
                continue
            seen.add(key)

            system_oh = _system_oh_context(cur, qc)
            system_position = _system_position(cur, system_oh)
            results.append(
                {
                    "movement_business_date": business_date,
                    "movement_file_id": file_id,
                    "movement_article_id": article_id,
                    "movement_article_number": g.get("article_number"),
                    "movement_family_id": family_id,
                    "movement_delta": g.get("movement_delta"),
                    "movement_uom": g.get("base_uom_code"),
                    "movement_row_count": int(g.get("movement_row_count") or 0),
                    "movement_types": (
                        str(g.get("movement_types") or "").split(",")
                        if g.get("movement_types")
                        else []
                    ),
                    "sample_upc": qc.get("ean_upc"),
                    "sample_description": qc.get("selling_description"),
                    "sample_article_number": qc.get("article_number"),
                    "sample_main_article_number": qc.get("main_article_number"),
                    "quick_check_status": qc.get("quick_check_status"),
                    "system_anchor": system_oh,
                    "system_position": system_position,
                }
            )
            if len(results) >= limit:
                break

        if raw_movement_row_count == 0:
            lineage_status = "RAW_MOVEMENT_ROWS_MISSING"
        elif movement_history_summary["total_rows"] == 0:
            lineage_status = "RAW_PRESENT_BUT_MOVEMENT_HISTORY_MISSING"
        elif movement_history_summary["canonical_date_rows"] == 0:
            lineage_status = "MOVEMENT_HISTORY_PRESENT_BUT_CANONICAL_DATE_MISSING"
        elif movement_history_summary["base_qty_present_rows"] == 0:
            lineage_status = "CANONICAL_MOVEMENT_BASE_QTY_MISSING"
        elif movement_history_summary["nonzero_base_qty_rows"] == 0:
            lineage_status = "CANONICAL_MOVEMENT_ALL_ZERO_BASE_QTY"
        elif not movement_groups:
            lineage_status = "NONZERO_ROWS_PRESENT_BUT_NET_GROUPS_ZERO"
        elif not results:
            lineage_status = "MOVEMENT_GROUPS_PRESENT_BUT_NO_QUICK_CHECK_MATCH"
        else:
            lineage_status = "MOVEMENT_CANDIDATES_AVAILABLE"

        cur.close()
        return {
            "requested_date": requested_date,
            "canonical_movement_day": {
                "date": business_date,
                "file_id": file_id,
                "batch_id": day.get("batch_id"),
                "upload_timestamp": day.get("upload_timestamp"),
            },
            "lineage_status": lineage_status,
            "movement_file_lineage": {
                "canonical_file": canonical_file,
                "raw_movement_row_count": raw_movement_row_count,
                "movement_history": movement_history_summary,
                "nonzero_net_group_count": len(movement_groups),
            },
            "count": len(results),
            "results": results,
            "inventory_movement_policy": {
                "stock_basis": "SAP_UNRESTRICTED",
                "apply_signed": sorted(UNRESTRICTED_APPLY_AS_SIGNED),
                "no_unrestricted_effect": sorted(UNRESTRICTED_NO_EFFECT),
                "unknown_types_fail_closed": True,
            },
            "diagnostic_note": (
                "Candidates include only movement types with explicit Unrestricted-stock effect. "
                "Use rows where System OH anchor date is earlier than the movement business date "
                "and movement UOM matches the anchor UOM."
            ),
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



def negative_stock_queue(limit: int = 100) -> dict[str, Any]:
    """Return actionable negative-stock items at inventory-owner grain.

    Selling UPCs that resolve to the same System OH owner are grouped into one
    physical-count action. Effective OH still honors any active True Stock
    override. READY/QA_HOLD remains a data-quality status and is not rewritten
    by this business-exception queue.
    """
    limit = max(1, min(int(limit or 100), 500))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        latest_oh_file_id = _refresh_expired_true_stock(cur)
        cur.execute(
            """SELECT upc_id,ean_upc,article_id,article_number,family_id,main_article_number,
                      selling_description,family_description,selling_uom,
                      current_oh,current_oh_uom,oh_date,dos,
                      pos_qty_7d,upc_velocity_7d,
                      quick_check_status,blocking_reason,publish_batch_id,published_at
               FROM quick_check_current
               WHERE quick_check_status IN ('READY','QA_HOLD')
                 AND current_oh IS NOT NULL
                 AND current_oh < 0
               ORDER BY current_oh ASC,upc_velocity_7d DESC,ean_upc"""
        )
        candidates = cur.fetchall()

        owner_groups: dict[tuple[str, int], dict[str, Any]] = {}
        unresolved_owner_rows = 0
        for row in candidates:
            system_oh = _system_oh_context(cur, row)
            if not system_oh:
                unresolved_owner_rows += 1
                continue

            scope = str(system_oh.get("scope_type") or "").upper()
            if scope == "UPC":
                owner_id = system_oh.get("upc_id")
            elif scope == "ARTICLE":
                owner_id = system_oh.get("article_id")
            elif scope == "FAMILY":
                owner_id = system_oh.get("family_id")
            else:
                owner_id = None
            if owner_id is None:
                unresolved_owner_rows += 1
                continue

            key = (scope, int(owner_id))
            group = owner_groups.setdefault(
                key,
                {
                    "scope_type": scope,
                    "owner_id": int(owner_id),
                    "system_oh": system_oh,
                    "upc_rows": [],
                },
            )
            group["upc_rows"].append(row)

        actions: list[dict[str, Any]] = []
        suppressed_by_true_stock = 0
        blocked_owner_count = 0
        for group in owner_groups.values():
            system_oh = group["system_oh"]
            system_position = _system_position(cur, system_oh)
            if not system_position or not system_position.get("analysis_usable"):
                blocked_owner_count += 1
                continue

            true_stock = _active_true_stock(cur, system_oh)
            actual_position = _actual_position(cur, true_stock)
            effective_position = actual_position if true_stock else system_position
            if not effective_position or not effective_position.get("analysis_usable"):
                blocked_owner_count += 1
                continue

            quantity = effective_position.get("quantity")
            if quantity is None:
                blocked_owner_count += 1
                continue
            effective_qty = Decimal(str(quantity))
            if effective_qty >= 0:
                suppressed_by_true_stock += 1
                continue

            upc_rows = group["upc_rows"]
            representative = max(
                upc_rows,
                key=lambda r: (
                    Decimal(str(r.get("upc_velocity_7d") or 0)),
                    Decimal(str(r.get("pos_qty_7d") or 0)),
                    1 if str(r.get("quick_check_status") or "") == "READY" else 0,
                    str(r.get("ean_upc") or ""),
                ),
            )
            related_upcs = sorted({str(r.get("ean_upc")) for r in upc_rows if r.get("ean_upc")})
            related_statuses = sorted({str(r.get("quick_check_status")) for r in upc_rows if r.get("quick_check_status")})

            row = dict(representative)
            row.update(_stock_state(effective_qty))
            row["inventory_owner_scope"] = group["scope_type"]
            row["inventory_owner_id"] = group["owner_id"]
            row["inventory_owner_key"] = f"{group['scope_type']}:{group['owner_id']}"
            row["inventory_owner_upc_id"] = system_oh.get("upc_id")
            row["inventory_owner_article_id"] = system_oh.get("article_id")
            row["inventory_owner_article_number"] = system_oh.get("article_number")
            row["inventory_owner_family_id"] = system_oh.get("family_id")
            row["representative_upc"] = representative.get("ean_upc")
            row["related_upcs"] = related_upcs
            row["related_upc_count"] = len(related_upcs)
            row["related_quick_check_statuses"] = related_statuses
            row["system_oh"] = system_position.get("quantity")
            row["system_oh_uom"] = system_position.get("uom")
            row["effective_oh"] = effective_qty
            row["effective_oh_uom"] = effective_position.get("uom")
            row["effective_oh_source"] = "TRUE_STOCK" if true_stock else "SYSTEM_OH"
            row["active_true_stock"] = true_stock.get("true_stock_quantity") if true_stock else None
            row["active_true_stock_uom"] = true_stock.get("uom_code") if true_stock else None
            row["true_stock_required_uom"] = system_position.get("uom")
            row["action_upc"] = representative.get("ean_upc")
            row["action_code"] = "COUNT_AND_SUBMIT_TRUE_STOCK"
            row["action_reason"] = "EFFECTIVE_OH_NEGATIVE"
            row["action_endpoint"] = (
                f"/v1/app/inventory/negative-stock/"
                f"{group['scope_type']}/{group['owner_id']}/true-stock"
            )
            row["latest_on_hand_file_id"] = latest_oh_file_id
            actions.append(row)

        actions.sort(
            key=lambda r: (
                Decimal(str(r.get("effective_oh") or 0)),
                -Decimal(str(r.get("upc_velocity_7d") or 0)),
                str(r.get("representative_upc") or ""),
            )
        )
        for index, action in enumerate(actions, start=1):
            action["count_sequence"] = index
        rows = actions[:limit]

        conn.commit()
        cur.close()
        return {
            "count": len(rows),
            "queue_type": "NEGATIVE_STOCK_ACTION_QUEUE",
            "queue_grain": "INVENTORY_OWNER",
            "action_code": "COUNT_AND_SUBMIT_TRUE_STOCK",
            "candidate_upc_count": len(candidates),
            "inventory_owner_count": len(owner_groups),
            "actionable_owner_count": len(actions),
            "suppressed_by_true_stock_count": suppressed_by_true_stock,
            "blocked_owner_count": blocked_owner_count,
            "unresolved_owner_upc_count": unresolved_owner_rows,
            "rows": rows,
        }

def submit_negative_stock_true_stock(
    inventory_owner_scope: str,
    inventory_owner_id: int,
    true_stock_quantity: Decimal,
    true_stock_uom: str,
    device: str,
) -> dict[str, Any]:
    """Close one owner-level negative-stock action through the existing True Stock workflow."""

    scope = str(inventory_owner_scope or "").strip().upper()
    if scope not in {"UPC","ARTICLE","FAMILY"}:
        raise ValueError("NEGATIVE_STOCK_OWNER_SCOPE_INVALID")
    owner_id = int(inventory_owner_id)
    owner_key = f"{scope}:{owner_id}"

    before = negative_stock_queue(limit=500)
    action = next(
        (r for r in before.get("rows", []) if str(r.get("inventory_owner_key")) == owner_key),
        None,
    )
    if not action:
        raise KeyError("NEGATIVE_STOCK_ACTION_NOT_FOUND")

    action_upc = str(action.get("action_upc") or "").strip()
    if not action_upc:
        raise ValueError("NEGATIVE_STOCK_ACTION_UPC_MISSING")

    submitted = submit_true_stock(
        action_upc,
        true_stock_quantity,
        true_stock_uom,
        device,
    )

    after = negative_stock_queue(limit=500)
    still_present = any(
        str(r.get("inventory_owner_key")) == owner_key
        for r in after.get("rows", [])
    )

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT discrepancy_id,family_id,main_article_number,scope_type,
                      article_id,article_number,source_true_stock_id,ean_upc,
                      system_oh_quantity,true_stock_quantity,discrepancy_quantity,
                      uom_code,queue_status,created_at,updated_at
               FROM dumping_discrepancy_queue
               WHERE source_true_stock_id=%s
               ORDER BY discrepancy_id DESC
               LIMIT 1""",
            (submitted.get("true_stock_id"),),
        )
        dumping = cur.fetchone()
        cur.close()

    return {
        "status": "COMMITTED",
        "inventory_owner_scope": scope,
        "inventory_owner_id": owner_id,
        "inventory_owner_key": owner_key,
        "action_upc": action_upc,
        "representative_upc": action.get("representative_upc"),
        "related_upcs": action.get("related_upcs") or [],
        "queue_count_before": before.get("count"),
        "queue_count_after": after.get("count"),
        "queue_removed": not still_present,
        "submitted_true_stock": submitted,
        "dumping_record": dumping,
        "closed_loop_status": (
            "CLOSED"
            if not still_present
            else "STILL_NEGATIVE_AFTER_TRUE_STOCK"
        ),
    }



def ensure_order_workflow_tables(cur) -> None:
    if not _table_exists(cur, "order_draft"):
        cur.execute(
            """
            CREATE TABLE order_draft (
                order_draft_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                order_date DATE NOT NULL,
                delivery_date DATE NOT NULL,
                workflow_status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
                notes VARCHAR(255) NULL,
                external_order_reference VARCHAR(128) NULL,
                created_by VARCHAR(128) NOT NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                           ON UPDATE CURRENT_TIMESTAMP(6),
                confirmed_by VARCHAR(128) NULL,
                confirmed_at DATETIME(6) NULL,
                submitted_by VARCHAR(128) NULL,
                submitted_at DATETIME(6) NULL,
                cancelled_by VARCHAR(128) NULL,
                cancelled_at DATETIME(6) NULL,
                PRIMARY KEY (order_draft_id),
                KEY ix_order_draft_status_dates (workflow_status,order_date,delivery_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )
    if not _table_exists(cur, "order_draft_line"):
        cur.execute(
            """
            CREATE TABLE order_draft_line (
                order_draft_line_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                order_draft_id BIGINT UNSIGNED NOT NULL,
                upc_id BIGINT UNSIGNED NULL,
                ean_upc VARCHAR(32) NOT NULL,
                article_id BIGINT UNSIGNED NULL,
                article_number VARCHAR(64) NULL,
                family_id BIGINT UNSIGNED NULL,
                main_article_number VARCHAR(64) NULL,
                selling_description VARCHAR(255) NULL,
                selling_uom VARCHAR(32) NULL,
                base_uom VARCHAR(32) NULL,
                base_qty_per_selling_unit DECIMAL(24,8) NULL,
                suggested_qty DECIMAL(24,8) NOT NULL,
                final_qty DECIMAL(24,8) NOT NULL,
                effective_oh DECIMAL(24,8) NULL,
                effective_oh_uom VARCHAR(32) NULL,
                velocity_7d DECIMAL(24,8) NULL,
                days_supply DECIMAL(24,8) NULL,
                current_price DECIMAL(24,8) NULL,
                current_price_type VARCHAR(32) NULL,
                ordering_policy_id BIGINT UNSIGNED NULL,
                ordering_policy_scope_type VARCHAR(24) NULL,
                ordering_policy_scope_key VARCHAR(64) NULL,
                source_publish_batch_id BIGINT UNSIGNED NULL,
                source_published_at DATETIME(6) NULL,
                adjustment_note VARCHAR(255) NULL,
                created_by VARCHAR(128) NOT NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                updated_by VARCHAR(128) NULL,
                updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                           ON UPDATE CURRENT_TIMESTAMP(6),
                PRIMARY KEY (order_draft_line_id),
                UNIQUE KEY uq_order_draft_upc (order_draft_id,ean_upc),
                KEY ix_order_draft_line_upc (ean_upc),
                CONSTRAINT fk_order_draft_line_draft
                  FOREIGN KEY (order_draft_id) REFERENCES order_draft(order_draft_id)
                  ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )


    if not _column_exists(cur, "order_draft", "external_order_reference"):
        cur.execute(
            """ALTER TABLE order_draft
               ADD COLUMN external_order_reference VARCHAR(128) NULL
               AFTER notes"""
        )
    added_identity_column = False
    if not _column_exists(cur, "order_draft_line", "article_id"):
        cur.execute(
            """ALTER TABLE order_draft_line
               ADD COLUMN article_id BIGINT UNSIGNED NULL
               AFTER ean_upc"""
        )
        added_identity_column = True
    if not _column_exists(cur, "order_draft_line", "base_uom"):
        cur.execute(
            """ALTER TABLE order_draft_line
               ADD COLUMN base_uom VARCHAR(32) NULL
               AFTER selling_uom"""
        )
        added_identity_column = True
    if not _column_exists(cur, "order_draft_line", "base_qty_per_selling_unit"):
        cur.execute(
            """ALTER TABLE order_draft_line
               ADD COLUMN base_qty_per_selling_unit DECIMAL(24,8) NULL
               AFTER base_uom"""
        )
        added_identity_column = True
    if added_identity_column and _table_exists(cur, "quick_check_current"):
        cur.execute(
            """UPDATE order_draft_line l
               JOIN quick_check_current q ON q.ean_upc=l.ean_upc
               SET l.article_id=COALESCE(l.article_id,q.article_id),
                   l.base_uom=COALESCE(l.base_uom,q.base_uom),
                   l.base_qty_per_selling_unit=COALESCE(
                     l.base_qty_per_selling_unit,q.base_qty_per_selling_unit
                   )"""
        )


def _ordering_recommendation_for_upc(upc: str) -> dict[str, Any]:
    detail = get_quick_check_detail(upc)
    if not detail:
        raise KeyError("ORDERING_UPC_NOT_FOUND")
    item = detail.get("item") or {}
    ordering = detail.get("ordering") or {}
    effective = detail.get("effective_oh") or {}
    if ordering.get("status") != "ORDER_RECOMMENDATION_READY":
        raise ValueError("ORDER_RECOMMENDATION_NOT_READY")
    suggested = _qc_decimal(ordering.get("suggested_order_qty"))
    if suggested is None or suggested <= 0:
        raise ValueError("NO_POSITIVE_ORDER_RECOMMENDATION")
    if not ordering.get("next_order_date") or not ordering.get("next_delivery_date"):
        raise ValueError("ORDERING_DATES_NOT_AVAILABLE")
    return {
        "item": item,
        "ordering": ordering,
        "effective_oh": effective,
    }


def add_order_recommendation_to_draft(
    upc: str,
    *,
    device: str,
) -> dict[str, Any]:
    snap = _ordering_recommendation_for_upc(upc)
    item = snap["item"]
    ordering = snap["ordering"]
    effective = snap["effective_oh"]
    order_date = ordering["next_order_date"]
    delivery_date = ordering["next_delivery_date"]
    policy = ordering.get("policy") or {}
    suggested = Decimal(str(ordering["suggested_order_qty"]))

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_order_workflow_tables(cur)
        conn.commit()
        conn.start_transaction()
        try:
            cur.execute(
                """SELECT order_draft_id,workflow_status
                   FROM order_draft
                   WHERE order_date=%s
                     AND delivery_date=%s
                     AND workflow_status='DRAFT'
                   ORDER BY order_draft_id DESC
                   LIMIT 1
                   FOR UPDATE""",
                (order_date,delivery_date),
            )
            draft = cur.fetchone()
            if draft:
                draft_id = int(draft["order_draft_id"])
            else:
                cur.execute(
                    """INSERT INTO order_draft
                       (order_date,delivery_date,workflow_status,created_by)
                       VALUES (%s,%s,'DRAFT',%s)""",
                    (order_date,delivery_date,device),
                )
                draft_id = int(cur.lastrowid)

            cur.execute(
                """INSERT INTO order_draft_line
                   (order_draft_id,upc_id,ean_upc,article_id,article_number,family_id,
                    main_article_number,selling_description,selling_uom,base_uom,
                    base_qty_per_selling_unit,suggested_qty,final_qty,effective_oh,effective_oh_uom,
                    velocity_7d,days_supply,current_price,current_price_type,
                    ordering_policy_id,ordering_policy_scope_type,
                    ordering_policy_scope_key,source_publish_batch_id,
                    source_published_at,created_by,updated_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           %s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     suggested_qty=VALUES(suggested_qty),
                     effective_oh=VALUES(effective_oh),
                     effective_oh_uom=VALUES(effective_oh_uom),
                     velocity_7d=VALUES(velocity_7d),
                     days_supply=VALUES(days_supply),
                     current_price=VALUES(current_price),
                     current_price_type=VALUES(current_price_type),
                     ordering_policy_id=VALUES(ordering_policy_id),
                     ordering_policy_scope_type=VALUES(ordering_policy_scope_type),
                     ordering_policy_scope_key=VALUES(ordering_policy_scope_key),
                     source_publish_batch_id=VALUES(source_publish_batch_id),
                     source_published_at=VALUES(source_published_at),
                     updated_by=VALUES(updated_by),
                     updated_at=CURRENT_TIMESTAMP(6)""",
                (
                    draft_id,item.get("upc_id"),item.get("ean_upc"),
                    item.get("article_id"),item.get("article_number"),item.get("family_id"),
                    item.get("main_article_number"),item.get("selling_description"),
                    item.get("selling_uom"),item.get("base_uom"),
                    item.get("base_qty_per_selling_unit"),suggested,suggested,
                    effective.get("quantity"),effective.get("uom"),
                    ordering.get("velocity_7d"),ordering.get("days_supply"),
                    item.get("current_price"),item.get("current_price_type"),
                    policy.get("ordering_policy_id"),policy.get("scope_type"),
                    policy.get("scope_key"),item.get("publish_batch_id"),
                    item.get("published_at"),device,device,
                ),
            )
            conn.commit()
            return {
                "status":"ADDED_TO_DRAFT",
                "order_draft_id":draft_id,
                "ean_upc":item.get("ean_upc"),
                "suggested_qty":suggested,
                "final_qty":suggested,
                "order_date":order_date,
                "delivery_date":delivery_date,
                "live_order_submitted":False,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def update_order_draft_line(
    order_draft_line_id: int,
    *,
    final_qty: Decimal,
    adjustment_note: str | None,
    device: str,
) -> dict[str, Any]:
    qty = Decimal(str(final_qty))
    if qty < 0:
        raise ValueError("FINAL_ORDER_QTY_NEGATIVE")
    note = str(adjustment_note or "").strip()[:255] or None
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_order_workflow_tables(cur)
        conn.commit()
        conn.start_transaction()
        try:
            cur.execute(
                """SELECT l.order_draft_line_id,l.order_draft_id,d.workflow_status
                   FROM order_draft_line l
                   JOIN order_draft d ON d.order_draft_id=l.order_draft_id
                   WHERE l.order_draft_line_id=%s
                   FOR UPDATE""",
                (int(order_draft_line_id),),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError("ORDER_DRAFT_LINE_NOT_FOUND")
            if row.get("workflow_status") != "DRAFT":
                raise ValueError("ORDER_DRAFT_NOT_EDITABLE")
            cur.execute(
                """UPDATE order_draft_line
                   SET final_qty=%s,adjustment_note=%s,updated_by=%s,
                       updated_at=CURRENT_TIMESTAMP(6)
                   WHERE order_draft_line_id=%s""",
                (qty,note,device,int(order_draft_line_id)),
            )
            conn.commit()
            return {
                "status":"UPDATED",
                "order_draft_line_id":int(order_draft_line_id),
                "final_qty":qty,
                "adjustment_note":note,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def order_draft_history(
    status: str | None = None,
    limit: int = 60,
) -> dict[str, Any]:
    limit = max(1,min(int(limit or 60),200))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_order_workflow_tables(cur)
        conn.commit()
        params: list[Any] = []
        where = ""
        if status:
            where = "WHERE d.workflow_status=%s"
            params.append(str(status).strip().upper())
        params.append(limit)
        cur.execute(
            f"""SELECT d.order_draft_id,d.order_date,d.delivery_date,d.workflow_status,
                       d.notes,d.external_order_reference,d.created_by,d.created_at,d.updated_at,
                       d.confirmed_by,d.confirmed_at,d.submitted_by,d.submitted_at,
                       d.cancelled_by,d.cancelled_at,
                       COUNT(l.order_draft_line_id) AS line_count,
                       COALESCE(SUM(l.final_qty),0) AS total_final_qty
                FROM order_draft d
                LEFT JOIN order_draft_line l
                  ON l.order_draft_id=d.order_draft_id
                {where}
                GROUP BY d.order_draft_id
                ORDER BY d.order_date DESC,d.order_draft_id DESC
                LIMIT %s""",
            tuple(params),
        )
        drafts = cur.fetchall()
        for draft in drafts:
            cur.execute(
                """SELECT order_draft_line_id,ean_upc,article_id,article_number,family_id,
                          main_article_number,selling_description,selling_uom,
                          base_uom,base_qty_per_selling_unit,
                          suggested_qty,final_qty,effective_oh,effective_oh_uom,
                          velocity_7d,days_supply,current_price,current_price_type,
                          ordering_policy_id,ordering_policy_scope_type,
                          ordering_policy_scope_key,source_publish_batch_id,
                          source_published_at,adjustment_note,created_by,created_at,
                          updated_by,updated_at
                   FROM order_draft_line
                   WHERE order_draft_id=%s
                   ORDER BY selling_description,ean_upc""",
                (draft["order_draft_id"],),
            )
            draft["lines"] = cur.fetchall()
        cur.close()
    return {
        "count":len(drafts),
        "rows":drafts,
        "contract_version":"ORDER_WORKFLOW_V1",
    }


def _norm_external_reference(value: Any) -> str | None:
    raw = str(value or "").strip().upper()
    if not raw:
        return None
    compact = "".join(ch for ch in raw if ch.isalnum())
    if compact.isdigit():
        compact = compact.lstrip("0") or "0"
    return compact or None


def _norm_order_uom(value: Any) -> str | None:
    raw = str(value or "").strip().upper()
    aliases = {
        "PAC":"PACK",
        "PK":"PACK",
        "PKG":"PACK",
        "EACH":"EA",
        "EACHES":"EA",
        "PCS":"EA",
        "PC":"EA",
        "LBS":"LB",
    }
    return aliases.get(raw, raw or None)


def _receipt_qty_in_selling_uom(
    row: dict[str, Any],
    line: dict[str, Any],
) -> tuple[Decimal | None,str|None,str|None]:
    selling_uom = _norm_order_uom(line.get("selling_uom"))
    base_uom = _norm_order_uom(line.get("base_uom"))
    row_base_uom = _norm_order_uom(row.get("base_uom_code"))
    row_entry_uom = _norm_order_uom(row.get("entry_uom_code"))
    base_qty = _qc_decimal(row.get("base_quantity"))
    entry_qty = _qc_decimal(row.get("entry_quantity"))
    factor = _qc_decimal(line.get("base_qty_per_selling_unit"))

    if selling_uom and row_entry_uom == selling_uom and entry_qty is not None:
        return entry_qty, selling_uom, "ENTRY_UOM_DIRECT"
    if selling_uom and row_base_uom == selling_uom and base_qty is not None:
        return base_qty, selling_uom, "BASE_UOM_DIRECT"
    if (
        selling_uom and base_uom and row_base_uom == base_uom
        and base_qty is not None and factor is not None and factor > 0
    ):
        return base_qty / factor, selling_uom, "BASE_TO_SELLING_FACTOR"
    return None, selling_uom, "UOM_CONVERSION_UNRESOLVED"


def _canonical_receipt_rows_for_line(
    cur,
    *,
    line: dict[str, Any],
    order_date: date,
    end_exclusive: date,
    external_reference: str | None,
) -> dict[str, Any]:
    days = source_data_days(cur,"movement",up_to=end_exclusive-timedelta(days=1))
    canonical_by_date = {
        d["date"]: int(d["file_id"])
        for d in days
        if d["date"] >= order_date and d["date"] < end_exclusive
    }
    if not canonical_by_date:
        return {
            "rows":[],
            "all_identity_rows":[],
            "data_through":None,
            "match_basis":"NO_CANONICAL_MOVEMENT_DAYS",
            "identity_basis":None,
        }

    article_id = line.get("article_id")
    family_id = line.get("family_id")
    if article_id is not None:
        identity_sql = "article_id=%s"
        identity_arg = int(article_id)
        identity_basis = "ARTICLE"
    elif family_id is not None:
        identity_sql = "family_id=%s"
        identity_arg = int(family_id)
        identity_basis = "FAMILY_FALLBACK"
    else:
        return {
            "rows":[],
            "all_identity_rows":[],
            "data_through":max(canonical_by_date),
            "match_basis":"IDENTITY_UNRESOLVED",
            "identity_basis":None,
        }

    file_ids=sorted(set(canonical_by_date.values()))
    placeholders=",".join(["%s"]*len(file_ids))
    cur.execute(
        f"""SELECT file_id,raw_id,source_row_number,article_id,article_number,family_id,
                   movement_type,posting_date,entry_quantity,entry_uom_code,
                   base_quantity,base_uom_code,amount_local_currency,
                   article_document,purchase_order,vendor_code
            FROM movement_history
            WHERE file_id IN ({placeholders})
              AND {identity_sql}
              AND movement_type IN ('101','102','109','110')
              AND posting_date>=%s AND posting_date<%s
            ORDER BY posting_date,file_id,raw_id,source_row_number""",
        (*file_ids,identity_arg,order_date,end_exclusive),
    )
    identity_rows=[]
    for row in cur.fetchall():
        posting=row.get("posting_date")
        fid=int(row.get("file_id"))
        if posting is None or canonical_by_date.get(posting)!=fid:
            continue
        identity_rows.append(row)

    normalized_ref=_norm_external_reference(external_reference)
    if normalized_ref:
        matched=[]
        for row in identity_rows:
            po=_norm_external_reference(row.get("purchase_order"))
            doc=_norm_external_reference(row.get("article_document"))
            if normalized_ref in {po,doc}:
                row=dict(row)
                row["reference_match_field"]=(
                    "PURCHASE_ORDER" if normalized_ref==po else "ARTICLE_DOCUMENT"
                )
                matched.append(row)
        match_basis="EXTERNAL_REFERENCE_EXACT"
    else:
        matched=[dict(x) for x in identity_rows]
        match_basis="ORDER_WINDOW_FALLBACK"

    return {
        "rows":matched,
        "all_identity_rows":identity_rows,
        "data_through":max(canonical_by_date),
        "match_basis":match_basis,
        "identity_basis":identity_basis,
    }


def order_delivery_reconciliation(order_draft_id: int) -> dict[str, Any]:
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        ensure_order_workflow_tables(cur)
        conn.commit()
        cur.execute(
            """SELECT order_draft_id,order_date,delivery_date,workflow_status,
                      external_order_reference,created_by,created_at,
                      confirmed_at,submitted_at
               FROM order_draft
               WHERE order_draft_id=%s""",
            (int(order_draft_id),),
        )
        draft=cur.fetchone()
        if not draft:
            cur.close()
            raise KeyError("ORDER_DRAFT_NOT_FOUND")

        cur.execute(
            """SELECT order_draft_line_id,ean_upc,article_id,article_number,
                      family_id,main_article_number,selling_description,
                      selling_uom,base_uom,base_qty_per_selling_unit,
                      suggested_qty,final_qty,effective_oh,effective_oh_uom,
                      velocity_7d,days_supply,current_price,current_price_type
               FROM order_draft_line
               WHERE order_draft_id=%s
               ORDER BY selling_description,ean_upc""",
            (int(order_draft_id),),
        )
        lines=cur.fetchall()
        today=business_today()
        output_lines=[]

        for line in lines:
            cur.execute(
                """SELECT MIN(d2.order_date) AS next_order_date
                   FROM order_draft_line l2
                   JOIN order_draft d2 ON d2.order_draft_id=l2.order_draft_id
                   WHERE l2.ean_upc=%s
                     AND d2.order_date>%s
                     AND d2.workflow_status IN ('CONFIRMED','MARKED_SUBMITTED')""",
                (line.get("ean_upc"),draft["order_date"]),
            )
            next_row=cur.fetchone() or {}
            next_order_date=next_row.get("next_order_date")
            natural_end=today+timedelta(days=1)
            end_exclusive=(
                min(natural_end,next_order_date)
                if next_order_date else natural_end
            )
            evidence=_canonical_receipt_rows_for_line(
                cur,
                line=line,
                order_date=draft["order_date"],
                end_exclusive=end_exclusive,
                external_reference=draft.get("external_order_reference"),
            )
            rows=evidence["rows"]
            compatible=[]
            incompatible=[]
            for row in rows:
                qty,uom,conversion=_receipt_qty_in_selling_uom(row,line)
                enriched=dict(row)
                enriched["selling_equivalent_quantity"]=qty
                enriched["selling_equivalent_uom"]=uom
                enriched["conversion_basis"]=conversion
                if qty is None:
                    incompatible.append(enriched)
                else:
                    compatible.append(enriched)

            # Physical delivery quantity is 101/109 only. 107/108 are
            # valuation stages and never enter this reconciliation.
            physical_rows=[
                r for r in compatible
                if str(r.get("movement_type")) in {"101","102","109","110"}
            ]

            def _sum(rows_: list[dict[str,Any]]) -> Decimal:
                return sum(
                    (Decimal(str(r["selling_equivalent_quantity"])) for r in rows_),
                    Decimal("0"),
                )

            if physical_rows:
                received=_sum(physical_rows)
                receipt_basis="PHYSICAL_RECEIPT_101_109_NET_REVERSALS"
            else:
                received=Decimal("0")
                receipt_basis="NO_COMPATIBLE_PHYSICAL_RECEIPT_EVIDENCE"
            ignored_cost_stage_count=0

            ordered=_qc_decimal(line.get("final_qty")) or Decimal("0")
            variance=received-ordered
            has_reversal=any(str(r.get("movement_type")) in {"102","110"} for r in physical_rows)
            family_fallback=evidence.get("identity_basis")=="FAMILY_FALLBACK"
            reference_unmatched=bool(
                draft.get("external_order_reference")
                and not rows
                and evidence.get("all_identity_rows")
            )

            if draft.get("workflow_status") not in {"CONFIRMED","MARKED_SUBMITTED"}:
                status="ORDER_NOT_READY_FOR_RECONCILIATION"
            elif reference_unmatched:
                status="REVIEW_REFERENCE_NOT_MATCHED"
            elif incompatible:
                status="REVIEW_UOM_CONVERSION"
            elif family_fallback and rows:
                status="REVIEW_FAMILY_IDENTITY"
            elif has_reversal:
                status="REVIEW_REVERSAL_PRESENT"
            elif received == ordered:
                status="MATCHED_COMPLETE"
            elif received <= 0:
                status=(
                    "AWAITING_RECEIPT"
                    if today <= draft["delivery_date"] else "NO_RECEIPT_MATCHED"
                )
            elif received < ordered:
                status="PARTIAL_RECEIPT"
            else:
                status="OVER_RECEIVED"

            output_lines.append({
                **line,
                "ordered_qty":ordered,
                "received_qty":received,
                "variance_qty":variance,
                "reconciliation_status":status,
                "receipt_basis":receipt_basis,
                "match_basis":evidence.get("match_basis"),
                "identity_basis":evidence.get("identity_basis"),
                "window_start":draft["order_date"],
                "window_end_exclusive":end_exclusive,
                "next_order_date":next_order_date,
                "movement_data_through":evidence.get("data_through"),
                "receipt_row_count":len(rows),
                "compatible_receipt_row_count":len(compatible),
                "incompatible_receipt_row_count":len(incompatible),
                "ignored_cost_stage_107_108_row_count":ignored_cost_stage_count,
                "receipt_evidence":physical_rows,
                "uom_blocked_evidence":incompatible,
            })

        statuses=[str(x.get("reconciliation_status") or "") for x in output_lines]
        if not output_lines:
            overall="NO_LINES"
        elif any(s.startswith("REVIEW_") for s in statuses):
            overall="REVIEW_REQUIRED"
        elif all(s=="MATCHED_COMPLETE" for s in statuses):
            overall="COMPLETE"
        elif any(s in {"PARTIAL_RECEIPT","OVER_RECEIVED","NO_RECEIPT_MATCHED"} for s in statuses):
            overall="EXCEPTION"
        else:
            overall="OPEN"

        cur.close()
    return {
        "contract_version":"DELIVERY_RECONCILIATION_V1",
        "order_draft_id":int(order_draft_id),
        "order_date":draft.get("order_date"),
        "delivery_date":draft.get("delivery_date"),
        "workflow_status":draft.get("workflow_status"),
        "external_order_reference":draft.get("external_order_reference"),
        "overall_status":overall,
        "line_count":len(output_lines),
        "lines":output_lines,
        "receipt_policy":{
            "canonical_movement_files_only":True,
            "physical_receipt_types":["101","109"],
            "receipt_reversal_types":["102","110"],
            "cost_stage_types":["107","108"],
            "rule_107_109":"107 is valuation/cost-stage evidence only; 109 is the physical GR quantity/date for the same blocked-stock delivery.",
            "movement_107_inventory_effect":"NO_UNRESTRICTED_EFFECT; excluded from received quantity and delivery cadence.",
        },
    }


def update_order_external_reference(
    order_draft_id: int,
    *,
    external_order_reference: str | None,
    device: str,
) -> dict[str, Any]:
    ref=str(external_order_reference or "").strip()[:128] or None
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        ensure_order_workflow_tables(cur)
        conn.commit()
        cur.execute(
            """SELECT workflow_status
               FROM order_draft
               WHERE order_draft_id=%s""",
            (int(order_draft_id),),
        )
        existing=cur.fetchone()
        if not existing or existing.get("workflow_status") not in {
            "DRAFT","CONFIRMED","MARKED_SUBMITTED"
        }:
            cur.close()
            raise ValueError("ORDER_DRAFT_REFERENCE_UPDATE_BLOCKED")
        cur.execute(
            """UPDATE order_draft
               SET external_order_reference=%s,updated_at=CURRENT_TIMESTAMP(6)
               WHERE order_draft_id=%s""",
            (ref,int(order_draft_id)),
        )
        conn.commit()
        cur.close()
    return {
        "status":"UPDATED",
        "order_draft_id":int(order_draft_id),
        "external_order_reference":ref,
        "updated_by":device,
    }


def transition_order_draft(
    order_draft_id: int,
    *,
    action: str,
    note: str | None,
    external_order_reference: str | None = None,
    device: str,
) -> dict[str, Any]:
    action_key = str(action or "").strip().upper()
    transitions = {
        "CONFIRM":("DRAFT","CONFIRMED"),
        "MARK_SUBMITTED":("CONFIRMED","MARKED_SUBMITTED"),
        "CANCEL_DRAFT":("DRAFT","CANCELLED"),
        "CANCEL_CONFIRMED":("CONFIRMED","CANCELLED"),
    }
    if action_key not in transitions:
        raise ValueError("ORDER_WORKFLOW_ACTION_INVALID")
    expected,next_status = transitions[action_key]
    clean_note = str(note or "").strip()[:255] or None

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_order_workflow_tables(cur)
        conn.commit()
        conn.start_transaction()
        try:
            cur.execute(
                """SELECT order_draft_id,workflow_status
                   FROM order_draft
                   WHERE order_draft_id=%s
                   FOR UPDATE""",
                (int(order_draft_id),),
            )
            draft = cur.fetchone()
            if not draft:
                raise KeyError("ORDER_DRAFT_NOT_FOUND")
            if draft.get("workflow_status") != expected:
                raise ValueError("ORDER_WORKFLOW_STATUS_CONFLICT")

            if action_key == "CONFIRM":
                cur.execute(
                    """SELECT COUNT(*) AS cnt
                       FROM order_draft_line
                       WHERE order_draft_id=%s AND final_qty>0""",
                    (int(order_draft_id),),
                )
                if int((cur.fetchone() or {}).get("cnt") or 0) <= 0:
                    raise ValueError("ORDER_DRAFT_HAS_NO_POSITIVE_LINES")
                cur.execute(
                    """UPDATE order_draft
                       SET workflow_status='CONFIRMED',notes=COALESCE(%s,notes),
                           confirmed_by=%s,confirmed_at=CURRENT_TIMESTAMP(6)
                       WHERE order_draft_id=%s AND workflow_status='DRAFT'""",
                    (clean_note,device,int(order_draft_id)),
                )
            elif action_key == "MARK_SUBMITTED":
                ref=str(external_order_reference or "").strip()[:128] or None
                cur.execute(
                    """UPDATE order_draft
                       SET workflow_status='MARKED_SUBMITTED',
                           notes=COALESCE(%s,notes),
                           external_order_reference=COALESCE(%s,external_order_reference),
                           submitted_by=%s,submitted_at=CURRENT_TIMESTAMP(6)
                       WHERE order_draft_id=%s AND workflow_status='CONFIRMED'""",
                    (clean_note,ref,device,int(order_draft_id)),
                )
            else:
                cur.execute(
                    """UPDATE order_draft
                       SET workflow_status='CANCELLED',notes=COALESCE(%s,notes),
                           cancelled_by=%s,cancelled_at=CURRENT_TIMESTAMP(6)
                       WHERE order_draft_id=%s AND workflow_status=%s""",
                    (clean_note,device,int(order_draft_id),expected),
                )
            if int(cur.rowcount or 0) != 1:
                raise RuntimeError("ORDER_WORKFLOW_TRANSITION_CONFLICT")
            conn.commit()
            return {
                "status":next_status,
                "order_draft_id":int(order_draft_id),
                "live_order_submitted":False,
                "submission_mark_is_audit_only": next_status=="MARKED_SUBMITTED",
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def ordering_queue(limit: int = 80) -> dict[str, Any]:
    """Operational ordering review queue for the public Web App.

    Uses the same effective-OH and DOS logic as Quick Check. It intentionally
    does not invent an order quantity until an authoritative order calendar and
    target-coverage policy are configured.
    """
    limit = max(1, min(int(limit or 80), 200))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        _refresh_expired_true_stock(cur)
        ensure_ordering_policy_table(cur)
        cur.execute(
            """SELECT upc_id,ean_upc,article_id,article_number,family_id,main_article_number,
                      selling_description,family_description,product_class,selling_uom,
                      base_uom,base_qty_per_selling_unit,
                      current_price,current_price_type,current_cost_per_selling_unit,
                      current_oh,current_oh_uom,oh_date,dos,doh,
                      pos_qty_7d,pos_qty_30d,upc_velocity_7d,upc_velocity_30d,
                      gp_pct_current,gp_dollars_7d,gp_per_day_7d,
                      quick_check_status,blocking_reason,publish_batch_id,published_at
               FROM quick_check_current
               WHERE quick_check_status IN ('READY','QA_HOLD')
                 AND current_oh IS NOT NULL
               ORDER BY
                 CASE WHEN dos IS NULL THEN 1 ELSE 0 END,
                 dos ASC,
                 upc_velocity_7d DESC,
                 selling_description,
                 ean_upc
               LIMIT %s""",
            (limit,),
        )
        base_rows = cur.fetchall()
        rows: list[dict[str, Any]] = []
        for row in base_rows:
            system_oh = _system_oh_context(cur, row)
            system_position = _system_position(cur, system_oh)
            true_stock = _active_true_stock(cur, system_oh)
            actual_position = _actual_position(cur, true_stock)
            effective_position = actual_position if true_stock else system_position
            effective_oh = {
                "quantity": effective_position.get("quantity") if effective_position else None,
                "uom": effective_position.get("uom") if effective_position else None,
                "source": "TRUE_STOCK" if true_stock else "SYSTEM_OH",
                "analysis_usable": effective_position.get("analysis_usable") if effective_position else False,
                "rollforward_status": effective_position.get("rollforward_status") if effective_position else "BLOCKED",
                "blockers": effective_position.get("blockers") if effective_position else ["OH_POSITION_NOT_AVAILABLE"],
                "movement_through_date": effective_position.get("movement_through_date") if effective_position else None,
            }
            ordering_policy = _resolve_ordering_policy(cur, row)
            ordering = _quick_check_ordering(row, effective_oh, ordering_policy)
            out = dict(row)
            out["effective_oh"] = effective_oh.get("quantity")
            out["effective_oh_uom"] = effective_oh.get("uom")
            out["effective_oh_source"] = effective_oh.get("source")
            out["effective_oh_through"] = effective_oh.get("movement_through_date")
            out["ordering"] = ordering
            rows.append(out)
        conn.commit()
        cur.close()
    return {
        "count": len(rows),
        "contract_version": "ORDERING_APP_V2",
        "quantity_policy": "CONFIG_DRIVEN_ORDER_RECOMMENDATION",
        "rows": rows,
    }


def ensure_price_change_tables(cur) -> None:
    if not _table_exists(cur, "price_change_proposal"):
        cur.execute(
            """
            CREATE TABLE price_change_proposal (
                proposal_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                upc_id BIGINT UNSIGNED NOT NULL,
                ean_upc VARCHAR(32) NOT NULL,
                article_number VARCHAR(64) NULL,
                family_id BIGINT UNSIGNED NULL,
                main_article_number VARCHAR(64) NULL,
                selling_description VARCHAR(255) NULL,
                selling_uom VARCHAR(32) NULL,
                current_price DECIMAL(24,8) NOT NULL,
                proposed_price DECIMAL(24,8) NOT NULL,
                proposed_price_type VARCHAR(32) NULL,
                proposal_basis VARCHAR(32) NOT NULL,
                basis_reference_price DECIMAL(24,8) NULL,
                current_cost_per_selling_unit DECIMAL(24,8) NULL,
                current_gp_pct DECIMAL(24,8) NULL,
                proposed_gp_pct DECIMAL(24,8) NULL,
                current_gp_per_day_7d DECIMAL(24,8) NULL,
                projected_gp_per_day_7d DECIMAL(24,8) NULL,
                projected_gp_per_day_delta DECIMAL(24,8) NULL,
                upc_velocity_7d DECIMAL(24,8) NULL,
                sweet_spot_price DECIMAL(24,8) NULL,
                wgpm_price DECIMAL(24,8) NULL,
                company_price_a DECIMAL(24,8) NULL,
                company_price_b DECIMAL(24,8) NULL,
                company_price_c DECIMAL(24,8) NULL,
                current_price_source VARCHAR(64) NULL,
                current_price_asof_date DATE NULL,
                cost_source VARCHAR(64) NULL,
                cost_date DATE NULL,
                reason VARCHAR(255) NULL,
                proposal_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW',
                proposed_by VARCHAR(128) NOT NULL,
                proposed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                reviewed_by VARCHAR(128) NULL,
                reviewed_at DATETIME(6) NULL,
                review_note VARCHAR(255) NULL,
                execution_marked_by VARCHAR(128) NULL,
                execution_marked_at DATETIME(6) NULL,
                execution_note VARCHAR(255) NULL,
                PRIMARY KEY (proposal_id),
                KEY ix_price_change_status (proposal_status,proposed_at),
                KEY ix_price_change_upc (ean_upc,proposal_status),
                KEY ix_price_change_family (family_id,proposal_status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )


def _price_reference_from_basis(row: dict[str, Any], basis: str) -> Decimal | None:
    key = str(basis or "").strip().upper()
    mapping = {
        "SWEET_SPOT": "sweet_spot_price",
        "WGPM": "wgpm_price",
        "COMPANY_A": "company_price_a",
        "COMPANY_B": "company_price_b",
        "COMPANY_C": "company_price_c",
        "CURRENT": "current_price",
    }
    field = mapping.get(key)
    return _qc_decimal(row.get(field)) if field else None


def _price_change_impact(row: dict[str, Any], proposed_price: Decimal) -> dict[str, Any]:
    price = Decimal(str(proposed_price))
    if price <= 0:
        raise ValueError("PROPOSED_PRICE_MUST_BE_POSITIVE")
    cost = _qc_decimal(row.get("current_cost_per_selling_unit"))
    velocity = _qc_decimal(row.get("upc_velocity_7d"))
    current_gp_day = _qc_decimal(row.get("gp_per_day_7d"))
    proposed_gp_pct = None
    projected_gp_day = None
    projected_delta = None
    if cost is not None:
        proposed_gp_pct = (price - cost) / price
        if velocity is not None and velocity >= 0:
            projected_gp_day = (price - cost) * velocity
            if current_gp_day is not None:
                projected_delta = projected_gp_day - current_gp_day
    return {
        "proposed_price": price,
        "proposed_gp_pct": proposed_gp_pct,
        "projected_gp_per_day_7d": projected_gp_day,
        "projected_gp_per_day_delta": projected_delta,
        "calculation_basis": "CURRENT_COST_X_CURRENT_7D_UPC_VELOCITY",
        "volume_response_assumed": False,
        "caveat": (
            "Projected GP/day holds current 7D UPC velocity constant and does not predict "
            "price elasticity or future unit movement."
        ),
    }


def price_change_preview(upc: str, proposed_price: Decimal) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        row = _lookup_qc_row(cur, upc)
        if not row:
            cur.close()
            raise KeyError("PRICE_CHANGE_UPC_NOT_FOUND")
        impact = _price_change_impact(row, Decimal(str(proposed_price)))
        family_id = int(row["family_id"]) if row.get("family_id") is not None else None
        related = []
        if family_id is not None:
            cur.execute(
                """SELECT ean_upc,article_number,selling_description,selling_uom,
                          current_price,current_price_type,quick_check_status
                   FROM quick_check_current
                   WHERE family_id=%s
                   ORDER BY ean_upc""",
                (family_id,),
            )
            related = cur.fetchall()
        cur.close()
    return {
        "contract_version": "PRICE_CHANGE_PREVIEW_V1",
        "item": row,
        "impact": impact,
        "reference_prices": {
            "sweet_spot": row.get("sweet_spot_price"),
            "wgpm": row.get("wgpm_price"),
            "company_a": row.get("company_price_a"),
            "company_b": row.get("company_price_b"),
            "company_c": row.get("company_price_c"),
        },
        "related_upcs": related,
        "related_upc_sync_policy": "NOT_INFERRED",
        "retail_price_mutated": False,
    }


def create_price_change_proposal(
    *,
    upc: str,
    proposed_price: Decimal,
    proposal_basis: str,
    proposed_price_type: str | None,
    reason: str | None,
    device: str,
) -> dict[str, Any]:
    basis = str(proposal_basis or "").strip().upper()
    allowed = {"MANUAL","SWEET_SPOT","WGPM","COMPANY_A","COMPANY_B","COMPANY_C","CURRENT"}
    if basis not in allowed:
        raise ValueError("PRICE_CHANGE_BASIS_INVALID")
    price = Decimal(str(proposed_price))
    if price <= 0:
        raise ValueError("PROPOSED_PRICE_MUST_BE_POSITIVE")
    clean_type = str(proposed_price_type or "").strip().upper()[:32] or None
    clean_reason = str(reason or "").strip()[:255] or None

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_price_change_tables(cur)
        conn.commit()
        row = _lookup_qc_row(cur, upc)
        if not row:
            cur.close()
            raise KeyError("PRICE_CHANGE_UPC_NOT_FOUND")
        if row.get("current_price") is None:
            cur.close()
            raise ValueError("CURRENT_PRICE_NOT_AVAILABLE")
        reference = _price_reference_from_basis(row, basis)
        if basis != "MANUAL" and reference is None:
            cur.close()
            raise ValueError("PRICE_CHANGE_BASIS_REFERENCE_NOT_AVAILABLE")
        if basis != "MANUAL" and abs(price-reference) >= Decimal("0.01"):
            cur.close()
            raise ValueError("PROPOSED_PRICE_DOES_NOT_MATCH_SELECTED_BASIS")

        impact = _price_change_impact(row, price)
        cur.execute(
            """INSERT INTO price_change_proposal
               (upc_id,ean_upc,article_number,family_id,main_article_number,
                selling_description,selling_uom,current_price,proposed_price,
                proposed_price_type,proposal_basis,basis_reference_price,
                current_cost_per_selling_unit,current_gp_pct,proposed_gp_pct,
                current_gp_per_day_7d,projected_gp_per_day_7d,projected_gp_per_day_delta,
                upc_velocity_7d,sweet_spot_price,wgpm_price,
                company_price_a,company_price_b,company_price_c,
                current_price_source,current_price_asof_date,cost_source,cost_date,
                reason,proposal_status,proposed_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING_REVIEW',%s)""",
            (
                row.get("upc_id"),row.get("ean_upc"),row.get("article_number"),
                row.get("family_id"),row.get("main_article_number"),
                row.get("selling_description"),row.get("selling_uom"),
                row.get("current_price"),price,clean_type,basis,reference,
                row.get("current_cost_per_selling_unit"),row.get("gp_pct_current"),
                impact.get("proposed_gp_pct"),row.get("gp_per_day_7d"),
                impact.get("projected_gp_per_day_7d"),
                impact.get("projected_gp_per_day_delta"),
                row.get("upc_velocity_7d"),row.get("sweet_spot_price"),
                row.get("wgpm_price"),row.get("company_price_a"),
                row.get("company_price_b"),row.get("company_price_c"),
                row.get("current_price_source"),row.get("current_price_asof_date"),
                row.get("cost_source"),row.get("cost_date"),
                clean_reason,device,
            ),
        )
        proposal_id = int(cur.lastrowid)
        conn.commit()
        cur.execute("SELECT * FROM price_change_proposal WHERE proposal_id=%s",(proposal_id,))
        saved = cur.fetchone()
        cur.close()
    return {
        "status":"PENDING_REVIEW",
        "proposal":saved,
        "retail_price_mutated":False,
        "execution_required_externally":True,
    }


def list_price_change_proposals(
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    limit = max(1,min(int(limit or 100),300))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_price_change_tables(cur)
        conn.commit()
        if status:
            s = str(status).strip().upper()
            cur.execute(
                """SELECT * FROM price_change_proposal
                   WHERE proposal_status=%s
                   ORDER BY proposed_at DESC,proposal_id DESC
                   LIMIT %s""",
                (s,limit),
            )
        else:
            cur.execute(
                """SELECT * FROM price_change_proposal
                   ORDER BY proposed_at DESC,proposal_id DESC
                   LIMIT %s""",
                (limit,),
            )
        rows = cur.fetchall()
        cur.close()
    return {"count":len(rows),"rows":rows,"contract_version":"PRICE_CHANGE_PROPOSAL_V1"}


def review_price_change_proposal(
    proposal_id: int,
    *,
    decision: str,
    note: str | None,
    device: str,
) -> dict[str, Any]:
    decision_key = str(decision or "").strip().upper()
    if decision_key not in {"APPROVE","REJECT","CANCEL"}:
        raise ValueError("PRICE_CHANGE_REVIEW_DECISION_INVALID")
    next_status = {
        "APPROVE":"APPROVED_FOR_EXECUTION",
        "REJECT":"REJECTED",
        "CANCEL":"CANCELLED",
    }[decision_key]
    clean_note = str(note or "").strip()[:255] or None
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_price_change_tables(cur)
        conn.commit()
        conn.start_transaction()
        try:
            cur.execute(
                """SELECT * FROM price_change_proposal
                   WHERE proposal_id=%s FOR UPDATE""",
                (int(proposal_id),),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError("PRICE_CHANGE_PROPOSAL_NOT_FOUND")
            if str(row.get("proposal_status") or "").upper() != "PENDING_REVIEW":
                raise ValueError("PRICE_CHANGE_PROPOSAL_NOT_PENDING")
            cur.execute(
                """UPDATE price_change_proposal
                   SET proposal_status=%s,
                       reviewed_by=%s,
                       reviewed_at=CURRENT_TIMESTAMP(6),
                       review_note=%s
                   WHERE proposal_id=%s
                     AND proposal_status='PENDING_REVIEW'""",
                (next_status,device,clean_note,int(proposal_id)),
            )
            if int(cur.rowcount or 0) != 1:
                raise RuntimeError("PRICE_CHANGE_REVIEW_CONFLICT")
            conn.commit()
            return {
                "status":next_status,
                "proposal_id":int(proposal_id),
                "retail_price_mutated":False,
                "execution_required_externally": next_status=="APPROVED_FOR_EXECUTION",
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def mark_price_change_executed(
    proposal_id: int,
    *,
    note: str | None,
    device: str,
) -> dict[str, Any]:
    clean_note = str(note or "").strip()[:255] or None
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_price_change_tables(cur)
        conn.commit()
        conn.start_transaction()
        try:
            cur.execute(
                """SELECT * FROM price_change_proposal
                   WHERE proposal_id=%s FOR UPDATE""",
                (int(proposal_id),),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError("PRICE_CHANGE_PROPOSAL_NOT_FOUND")
            if str(row.get("proposal_status") or "").upper() != "APPROVED_FOR_EXECUTION":
                raise ValueError("PRICE_CHANGE_PROPOSAL_NOT_APPROVED")
            cur.execute(
                """UPDATE price_change_proposal
                   SET proposal_status='MARKED_EXECUTED',
                       execution_marked_by=%s,
                       execution_marked_at=CURRENT_TIMESTAMP(6),
                       execution_note=%s
                   WHERE proposal_id=%s
                     AND proposal_status='APPROVED_FOR_EXECUTION'""",
                (device,clean_note,int(proposal_id)),
            )
            if int(cur.rowcount or 0) != 1:
                raise RuntimeError("PRICE_CHANGE_EXECUTION_MARK_CONFLICT")
            conn.commit()
            return {
                "status":"MARKED_EXECUTED",
                "proposal_id":int(proposal_id),
                "database_price_mutated":False,
                "note":"Execution mark is audit-only; next authoritative price source must confirm the live retail price.",
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def price_change_queue(limit: int = 120) -> dict[str, Any]:
    """Price review queue using current precomputed Quick Check fields and proposal awareness."""
    limit = max(1, min(int(limit or 120), 300))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT ean_upc,article_number,family_id,main_article_number,
                      selling_description,family_description,product_class,selling_uom,
                      current_price,current_price_type,current_price_source,current_price_asof_date,
                      current_cost_per_selling_unit,cost_source,cost_date,
                      pos_qty_7d,pos_qty_30d,upc_velocity_7d,upc_velocity_30d,
                      current_oh,current_oh_uom,oh_date,dos,doh,
                      gp_pct_current,gp_dollars_7d,gp_per_day_7d,
                      sweet_spot_price,wgpm_price,
                      company_price_a,company_price_b,company_price_c,
                      quick_check_status,blocking_reason,publish_batch_id,published_at
               FROM quick_check_current
               WHERE quick_check_status IN ('READY','QA_HOLD')
                 AND current_price IS NOT NULL
               ORDER BY
                 CASE
                   WHEN sweet_spot_price IS NOT NULL
                    AND ABS(current_price-sweet_spot_price) >= 0.01 THEN 0
                   ELSE 1
                 END,
                 gp_per_day_7d ASC,
                 upc_velocity_7d ASC,
                 selling_description,
                 ean_upc
               LIMIT %s""",
            (limit,),
        )
        rows = cur.fetchall()
        for row in rows:
            current = _qc_decimal(row.get("current_price"))
            flags: list[str] = []
            refs = {
                "sweet_spot": row.get("sweet_spot_price"),
                "wgpm": row.get("wgpm_price"),
                "company_a": row.get("company_price_a"),
                "company_b": row.get("company_price_b"),
                "company_c": row.get("company_price_c"),
            }
            for key, value in refs.items():
                ref = _qc_decimal(value)
                if current is not None and ref is not None and abs(current-ref) >= Decimal("0.01"):
                    flags.append(f"{key.upper()}_DIFF")
            row["review_flags"] = flags
            row["reference_prices"] = refs
            row["price_review_only"] = True
        cur.close()
    return {
        "count": len(rows),
        "contract_version": "PRICE_CHANGE_APP_V2",
        "mode": "REVIEW_PLUS_AUDITED_PROPOSAL_WORKFLOW",
        "rows": rows,
    }


def resolve_dumping_discrepancy(
    discrepancy_id: int,
    device: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Mark a pending dumping discrepancy handled without mutating inventory."""
    did = int(discrepancy_id)
    clean_note = str(note or "").strip()[:255] or None
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            ensure_true_stock_tables(cur)
            conn.commit()
            conn.start_transaction()
            cur.execute(
                """SELECT discrepancy_id,queue_status,source_true_stock_id,
                          family_id,main_article_number,article_number,ean_upc,
                          system_oh_quantity,true_stock_quantity,discrepancy_quantity,uom_code
                   FROM dumping_discrepancy_queue
                   WHERE discrepancy_id=%s
                   FOR UPDATE""",
                (did,),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError("DUMPING_DISCREPANCY_NOT_FOUND")
            if str(row.get("queue_status") or "").upper() != "PENDING":
                raise ValueError("DUMPING_DISCREPANCY_NOT_PENDING")
            cur.execute(
                """UPDATE dumping_discrepancy_queue
                   SET queue_status='RESOLVED',
                       resolved_at=CURRENT_TIMESTAMP(6),
                       resolved_by=%s,
                       resolution_note=%s
                   WHERE discrepancy_id=%s
                     AND queue_status='PENDING'""",
                (device, clean_note, did),
            )
            if int(cur.rowcount or 0) != 1:
                raise RuntimeError("DUMPING_RESOLVE_CONFLICT")
            conn.commit()
            return {
                "status": "RESOLVED",
                "discrepancy_id": did,
                "resolved_by": device,
                "resolution_note": clean_note,
                "inventory_mutated": False,
                "true_stock_mutated": False,
                "queue_only_action": True,
                "row": row,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def dumping_discrepancy_history(
    limit: int = 100,
    status: str | None = None,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 100), 300))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        ensure_true_stock_tables(cur)
        conn.commit()
        if status:
            s = str(status).strip().upper()
            cur.execute(
                """SELECT discrepancy_id,family_id,main_article_number,scope_type,
                          article_id,article_number,source_true_stock_id,
                          ean_upc,system_oh_quantity,true_stock_quantity,
                          discrepancy_quantity,uom_code,queue_status,
                          created_at,updated_at,resolved_at,resolved_by,resolution_note
                   FROM dumping_discrepancy_queue
                   WHERE queue_status=%s
                   ORDER BY COALESCE(resolved_at,updated_at) DESC,discrepancy_id DESC
                   LIMIT %s""",
                (s,limit),
            )
        else:
            cur.execute(
                """SELECT discrepancy_id,family_id,main_article_number,scope_type,
                          article_id,article_number,source_true_stock_id,
                          ean_upc,system_oh_quantity,true_stock_quantity,
                          discrepancy_quantity,uom_code,queue_status,
                          created_at,updated_at,resolved_at,resolved_by,resolution_note
                   FROM dumping_discrepancy_queue
                   WHERE queue_status<>'PENDING'
                   ORDER BY COALESCE(resolved_at,updated_at) DESC,discrepancy_id DESC
                   LIMIT %s""",
                (limit,),
            )
        rows = cur.fetchall()
        cur.close()
    return {
        "count": len(rows),
        "rows": rows,
        "contract_version": "DUMPING_HISTORY_V1",
    }


def operational_dashboard() -> dict[str, Any]:
    """Compact operational counts for the four-module public Web App."""
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """SELECT
                 COUNT(*) AS total_rows,
                 SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS ready_rows,
                 SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS qa_hold_rows,
                 SUM(CASE WHEN quick_check_status='HISTORICAL_ONLY' THEN 1 ELSE 0 END) AS historical_rows,
                 MAX(published_at) AS latest_published_at,
                 MAX(publish_batch_id) AS latest_publish_batch_id
               FROM quick_check_current"""
        )
        quick = cur.fetchone() or {}

        ordering = {"configured_policy_count": 0}
        if _table_exists(cur, "ordering_policy"):
            cur.execute(
                """SELECT
                     COUNT(*) AS configured_policy_count,
                     SUM(CASE WHEN enabled=TRUE THEN 1 ELSE 0 END) AS enabled_policy_count
                   FROM ordering_policy"""
            )
            ordering.update(cur.fetchone() or {})

        dumping = {
            "pending": 0,
            "resolved": 0,
            "superseded": 0,
            "other": 0,
        }
        if _table_exists(cur, "dumping_discrepancy_queue"):
            cur.execute(
                """SELECT queue_status,COUNT(*) AS cnt
                   FROM dumping_discrepancy_queue
                   GROUP BY queue_status"""
            )
            for row in cur.fetchall():
                status = str(row.get("queue_status") or "").upper()
                n = int(row.get("cnt") or 0)
                if status == "PENDING":
                    dumping["pending"] = n
                elif status == "RESOLVED":
                    dumping["resolved"] = n
                elif status == "SUPERSEDED":
                    dumping["superseded"] = n
                else:
                    dumping["other"] += n

        order_workflow = {
            "draft": 0,
            "confirmed": 0,
            "marked_submitted": 0,
            "cancelled": 0,
            "other": 0,
        }
        if _table_exists(cur, "order_draft"):
            cur.execute(
                """SELECT workflow_status,COUNT(*) AS cnt
                   FROM order_draft
                   GROUP BY workflow_status"""
            )
            for row in cur.fetchall():
                status = str(row.get("workflow_status") or "").upper()
                n = int(row.get("cnt") or 0)
                key = {
                    "DRAFT":"draft",
                    "CONFIRMED":"confirmed",
                    "MARKED_SUBMITTED":"marked_submitted",
                    "CANCELLED":"cancelled",
                }.get(status)
                if key:
                    order_workflow[key] = n
                else:
                    order_workflow["other"] += n

        pricing = {
            "pending_review": 0,
            "approved_for_execution": 0,
            "marked_executed": 0,
            "rejected": 0,
            "cancelled": 0,
            "other": 0,
        }
        if _table_exists(cur, "price_change_proposal"):
            cur.execute(
                """SELECT proposal_status,COUNT(*) AS cnt
                   FROM price_change_proposal
                   GROUP BY proposal_status"""
            )
            for row in cur.fetchall():
                status = str(row.get("proposal_status") or "").upper()
                n = int(row.get("cnt") or 0)
                key = {
                    "PENDING_REVIEW":"pending_review",
                    "APPROVED_FOR_EXECUTION":"approved_for_execution",
                    "MARKED_EXECUTED":"marked_executed",
                    "REJECTED":"rejected",
                    "CANCELLED":"cancelled",
                }.get(status)
                if key:
                    pricing[key] = n
                else:
                    pricing["other"] += n

        true_stock = {"active_count": 0}
        if _table_exists(cur, "manual_true_stock"):
            cur.execute(
                """SELECT COUNT(*) AS active_count
                   FROM manual_true_stock
                   WHERE override_status='ACTIVE'"""
            )
            true_stock.update(cur.fetchone() or {})

        cur.close()

    negative = negative_stock_queue(limit=500)
    return {
        "contract_version": "OPERATIONS_DASHBOARD_V1",
        "quick_check": quick,
        "ordering": ordering,
        "order_workflow": order_workflow,
        "dumping": dumping,
        "price_change": pricing,
        "true_stock": true_stock,
        "inventory_attention": {
            "negative_stock_actionable_owner_count": negative.get("actionable_owner_count",0),
            "negative_stock_blocked_owner_count": negative.get("blocked_owner_count",0),
        },
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
