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
            row["system_oh_scope_type"] = ctx.get("scope_type") if ctx else None
            row["system_oh_article_number"] = ctx.get("article_number") if ctx else None
            row["true_stock_required_uom"] = row.get("current_oh_uom")
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
        true_stock = _active_true_stock(cur, system_oh)

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

        effective_oh = {
            "quantity": row.get("current_oh"),
            "uom": row.get("current_oh_uom"),
            "source": "SYSTEM_OH",
            "date": row.get("oh_date"),
            "scope_type": system_oh.get("scope_type") if system_oh else None,
            "article_id": system_oh.get("article_id") if system_oh else None,
            "article_number": system_oh.get("article_number") if system_oh else None,
        }
        if true_stock:
            effective_oh = {
                "quantity": true_stock.get("true_stock_quantity"),
                "uom": true_stock.get("uom_code"),
                "source": "TRUE_STOCK",
                "date": true_stock.get("submitted_at"),
                "submitted_by": true_stock.get("submitted_by"),
                "scope_type": true_stock.get("scope_type"),
                "article_id": true_stock.get("article_id"),
                "article_number": true_stock.get("article_number"),
            }

        detail = {
            "item": row,
            "system_oh": {
                "quantity": row.get("current_oh"),
                "uom": row.get("current_oh_uom"),
                "date": row.get("oh_date"),
                "scope_type": system_oh.get("scope_type") if system_oh else None,
                "article_id": system_oh.get("article_id") if system_oh else None,
                "article_number": system_oh.get("article_number") if system_oh else None,
                "source_file_id": system_oh.get("file_id") if system_oh else None,
                "source_raw_id": system_oh.get("raw_id") if system_oh else None,
            },
            "true_stock_input": {
                "required_uom": row.get("current_oh_uom"),
                "scope_type": system_oh.get("scope_type") if system_oh else None,
                "article_number": system_oh.get("article_number") if system_oh else None,
                "cross_uom_submission_allowed": False,
            },
            "active_true_stock": true_stock,
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
            if row.get("current_oh") is None or not row.get("current_oh_uom"):
                raise ValueError("SYSTEM_OH_NOT_AVAILABLE")

            family_id = int(row["family_id"])
            system_qty = Decimal(str(row["current_oh"]))
            system_uom = str(row["current_oh_uom"]).strip().upper()
            if not submitted_uom:
                raise ValueError("TRUE_STOCK_UOM_REQUIRED")
            if submitted_uom != system_uom:
                raise ValueError(f"TRUE_STOCK_UOM_MISMATCH:{system_uom}")

            system_oh = _system_oh_context(cur, row)
            if not system_oh:
                raise ValueError("SYSTEM_OH_LINEAGE_NOT_AVAILABLE")
            scope_type = str(system_oh["scope_type"]).upper()
            article_id = int(system_oh["article_id"]) if system_oh.get("article_id") is not None else None
            article_number = system_oh.get("article_number")
            latest_oh_file_id = _refresh_expired_true_stock(cur)

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

            discrepancy = system_qty - qty
            cur.execute(
                """INSERT INTO manual_true_stock
                   (family_id,main_article_number,scope_type,article_id,article_number,
                    upc_id,ean_upc,true_stock_quantity,uom_code,
                    system_oh_quantity,system_oh_uom_code,
                    discrepancy_quantity,anchor_on_hand_file_id,
                    override_status,submitted_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s)""",
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
                "anchor_on_hand_file_id": latest_oh_file_id,
                "dumping_queue_action": queue_action,
                "effective_oh_source": "TRUE_STOCK",
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()




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
            """SELECT batch_id,file_id,sheet_id,raw_id,source_row_number,
                      observation_date,article_number,article_id,family_id,
                      ean_upc,upc_id,on_hand_quantity,uom_code,source_type
               FROM inventory_observation
               WHERE family_id IS NULL OR article_id IS NULL
               ORDER BY observation_date DESC,file_id DESC,raw_id DESC
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
