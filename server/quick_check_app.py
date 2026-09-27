from __future__ import annotations

from decimal import Decimal
from typing import Any

from db import db_conn


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


def ensure_true_stock_tables(cur) -> None:
    if not _table_exists(cur, "manual_true_stock"):
        cur.execute(
            """
            CREATE TABLE manual_true_stock (
                true_stock_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                family_id BIGINT UNSIGNED NOT NULL,
                main_article_number VARCHAR(64) NULL,
                upc_id BIGINT UNSIGNED NULL,
                ean_upc VARCHAR(32) NULL,
                true_stock_quantity DECIMAL(24,8) NOT NULL,
                uom_code VARCHAR(32) NOT NULL,
                system_oh_quantity DECIMAL(24,8) NULL,
                system_oh_uom_code VARCHAR(32) NULL,
                discrepancy_quantity DECIMAL(24,8) NULL,
                anchor_on_hand_file_id BIGINT UNSIGNED NULL,
                override_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
                submitted_by VARCHAR(128) NULL,
                submitted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                superseded_at DATETIME(6) NULL,
                superseded_by_oh_file_id BIGINT UNSIGNED NULL,
                PRIMARY KEY (true_stock_id),
                KEY ix_manual_true_stock_family_status (family_id,override_status),
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
            """SELECT ean_upc,article_number,family_id,main_article_number,
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


def _active_true_stock(cur, family_id: int) -> dict[str, Any] | None:
    if not _table_exists(cur, "manual_true_stock"):
        return None
    cur.execute(
        """SELECT *
           FROM manual_true_stock
           WHERE family_id=%s
             AND override_status='ACTIVE'
           ORDER BY true_stock_id DESC
           LIMIT 1""",
        (int(family_id),),
    )
    return cur.fetchone()


def get_quick_check_detail(upc: str) -> dict[str, Any] | None:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        row = _lookup_qc_row(cur, upc)
        if not row:
            cur.close()
            return None

        latest_oh_file_id = _refresh_expired_true_stock(cur)
        family_id = int(row["family_id"])
        true_stock = _active_true_stock(cur, family_id)

        cur.execute(
            """SELECT ean_upc,article_number,selling_description,selling_uom,
                      current_price,current_price_type,current_cost_per_selling_unit,
                      pos_qty_7d,pos_qty_30d,upc_velocity_7d,upc_velocity_30d,
                      current_oh,current_oh_uom,oh_date,quick_check_status,blocking_reason
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

        effective_oh = {
            "quantity": row.get("current_oh"),
            "uom": row.get("current_oh_uom"),
            "source": "SYSTEM_OH",
            "date": row.get("oh_date"),
        }
        if true_stock:
            effective_oh = {
                "quantity": true_stock.get("true_stock_quantity"),
                "uom": true_stock.get("uom_code"),
                "source": "TRUE_STOCK",
                "date": true_stock.get("submitted_at"),
                "submitted_by": true_stock.get("submitted_by"),
            }

        detail = {
            "item": row,
            "system_oh": {
                "quantity": row.get("current_oh"),
                "uom": row.get("current_oh_uom"),
                "date": row.get("oh_date"),
            },
            "active_true_stock": true_stock,
            "effective_oh": effective_oh,
            "latest_on_hand_file_id": latest_oh_file_id,
            "related_upcs": related,
        }
        conn.commit()
        cur.close()
        return detail


def submit_true_stock(upc: str, true_stock_quantity: Decimal, device: str) -> dict[str, Any]:
    qty = Decimal(str(true_stock_quantity))
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
            if row.get("current_oh") is None or not row.get("current_oh_uom"):
                raise ValueError("SYSTEM_OH_NOT_AVAILABLE")

            family_id = int(row["family_id"])
            system_qty = Decimal(str(row["current_oh"]))
            system_uom = str(row["current_oh_uom"]).strip().upper()
            latest_oh_file_id = _refresh_expired_true_stock(cur)

            cur.execute(
                """UPDATE manual_true_stock
                   SET override_status='SUPERSEDED_BY_NEW_TRUE_STOCK',
                       superseded_at=CURRENT_TIMESTAMP(6)
                   WHERE family_id=%s
                     AND override_status='ACTIVE'""",
                (family_id,),
            )

            discrepancy = system_qty - qty
            cur.execute(
                """INSERT INTO manual_true_stock
                   (family_id,main_article_number,upc_id,ean_upc,
                    true_stock_quantity,uom_code,
                    system_oh_quantity,system_oh_uom_code,
                    discrepancy_quantity,anchor_on_hand_file_id,
                    override_status,submitted_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s)""",
                (
                    family_id,
                    row.get("main_article_number"),
                    row.get("upc_id"),
                    row.get("ean_upc"),
                    qty,
                    system_uom,
                    system_qty,
                    system_uom,
                    discrepancy,
                    latest_oh_file_id,
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
                         AND queue_status='PENDING'
                       ORDER BY discrepancy_id DESC
                       LIMIT 1""",
                    (family_id,),
                )
                pending = cur.fetchone()
                if pending:
                    cur.execute(
                        """UPDATE dumping_discrepancy_queue
                           SET source_true_stock_id=%s,
                               main_article_number=%s,
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
                           (family_id,main_article_number,source_true_stock_id,ean_upc,
                            system_oh_quantity,true_stock_quantity,discrepancy_quantity,
                            uom_code,queue_status)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')""",
                        (
                            family_id,
                            row.get("main_article_number"),
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
                         AND queue_status='PENDING'""",
                    (family_id,),
                )
                if int(cur.rowcount or 0) > 0:
                    queue_action = "RESOLVED_PENDING"

            conn.commit()
            return {
                "status": "COMMITTED",
                "family_id": family_id,
                "main_article_number": row.get("main_article_number"),
                "ean_upc": row.get("ean_upc"),
                "system_oh": system_qty,
                "true_stock": qty,
                "uom": system_uom,
                "discrepancy": discrepancy,
                "true_stock_id": true_stock_id,
                "anchor_on_hand_file_id": latest_oh_file_id,
                "dumping_queue_action": queue_action,
                "effective_oh_source": "TRUE_STOCK",
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()



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
            """SELECT discrepancy_id,family_id,main_article_number,source_true_stock_id,
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
