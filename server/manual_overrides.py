from __future__ import annotations

import json
from typing import Any

SEED_OVERRIDES = (
    {
        "ean_upc": "4918",
        "article_number": "3401602",
        "selling_uom_code": "LB",
        "base_uom_code": "LB",
        "base_qty_per_selling_unit": 1,
        "source_note": "User confirmed: UPC 4918 belongs to Article 3401602 and is sold by LB.",
    },
)


def ensure_override_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS manual_upc_override (
            override_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            ean_upc VARCHAR(32) NOT NULL,
            article_number VARCHAR(64) NULL,
            selling_uom_code VARCHAR(32) NULL,
            base_uom_code VARCHAR(32) NULL,
            base_qty_per_selling_unit DECIMAL(24,12) NULL,
            override_status VARCHAR(24) NOT NULL DEFAULT 'CONFIRMED',
            source_note VARCHAR(512) NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                       ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (override_id),
            UNIQUE KEY uq_manual_upc_override (ean_upc),
            KEY ix_manual_upc_override_status (override_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def seed_confirmed_overrides(cur) -> int:
    ensure_override_table(cur)
    changed = 0
    for row in SEED_OVERRIDES:
        cur.execute(
            """
            INSERT INTO manual_upc_override
              (ean_upc,article_number,selling_uom_code,base_uom_code,
               base_qty_per_selling_unit,override_status,source_note)
            VALUES (%s,%s,%s,%s,%s,'CONFIRMED',%s)
            ON DUPLICATE KEY UPDATE
              article_number=VALUES(article_number),
              selling_uom_code=VALUES(selling_uom_code),
              base_uom_code=VALUES(base_uom_code),
              base_qty_per_selling_unit=VALUES(base_qty_per_selling_unit),
              override_status='CONFIRMED',
              source_note=VALUES(source_note)
            """,
            (
                row["ean_upc"], row["article_number"], row["selling_uom_code"],
                row["base_uom_code"], row["base_qty_per_selling_unit"], row["source_note"],
            ),
        )
        changed += 1
    return changed


def _uom_id(cur, code: str | None) -> int | None:
    if not code:
        return None
    cur.execute("SELECT uom_id FROM dim_uom WHERE UPPER(uom_code)=UPPER(%s) LIMIT 1", (code,))
    row = cur.fetchone()
    return int(row["uom_id"]) if row else None


def _canonical_article(cur, article_number: str) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT a.article_id,a.article_number,baf.family_id,pf.main_article_number,
               amain.article_id AS main_article_id
        FROM article a
        JOIN bridge_article_family baf
          ON baf.article_id=a.article_id
         AND baf.mapping_status='CONFIRMED'
         AND baf.is_primary=TRUE
         AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
        JOIN product_family pf ON pf.family_id=baf.family_id
        JOIN article amain ON amain.article_number=pf.main_article_number
        WHERE a.article_number=%s
        ORDER BY baf.article_family_id DESC
        LIMIT 1
        """,
        (article_number,),
    )
    return cur.fetchone()


def apply_manual_upc_overrides(cur) -> dict[str, Any]:
    seeded = seed_confirmed_overrides(cur)
    cur.execute(
        """
        SELECT ean_upc,article_number,selling_uom_code,base_uom_code,
               base_qty_per_selling_unit,source_note
        FROM manual_upc_override
        WHERE override_status='CONFIRMED'
        ORDER BY override_id
        """
    )
    rows = cur.fetchall()
    result = {
        "seeded_or_refreshed": seeded,
        "overrides_examined": len(rows),
        "identity_applied": 0,
        "uom_applied": 0,
        "held": [],
    }

    for ov in rows:
        ean = str(ov["ean_upc"]).strip()
        article_number = str(ov["article_number"] or "").strip()
        if not ean or not article_number:
            result["held"].append({"ean_upc": ean, "reason": "MISSING_OVERRIDE_IDENTITY"})
            continue

        anchor = _canonical_article(cur, article_number)
        if not anchor:
            result["held"].append(
                {"ean_upc": ean, "article_number": article_number, "reason": "ARTICLE_FAMILY_NOT_READY"}
            )
            continue

        cur.execute(
            """
            INSERT INTO selling_upc (ean_upc,selling_description,record_status)
            VALUES (%s,NULL,'ACTIVE')
            ON DUPLICATE KEY UPDATE record_status='ACTIVE'
            """,
            (ean,),
        )
        cur.execute("SELECT upc_id FROM selling_upc WHERE ean_upc=%s", (ean,))
        upc_id = int(cur.fetchone()["upc_id"])
        main_article_id = int(anchor["main_article_id"])

        cur.execute(
            """
            UPDATE bridge_article_upc
            SET mapping_status='SUPERSEDED',is_primary=FALSE,
                valid_to=COALESCE(valid_to,CURRENT_TIMESTAMP(6))
            WHERE upc_id=%s
              AND mapping_status='CONFIRMED'
              AND is_primary=TRUE
              AND (valid_to IS NULL OR valid_to>CURRENT_TIMESTAMP(6))
              AND article_id<>%s
            """,
            (upc_id, main_article_id),
        )

        cur.execute(
            """
            SELECT article_upc_id
            FROM bridge_article_upc
            WHERE article_id=%s AND upc_id=%s AND relationship_type='SELLING'
            ORDER BY article_upc_id DESC LIMIT 1
            """,
            (main_article_id, upc_id),
        )
        link = cur.fetchone()
        if link:
            cur.execute(
                """
                UPDATE bridge_article_upc
                SET mapping_status='CONFIRMED',is_primary=TRUE,confidence=1.0,valid_to=NULL
                WHERE article_upc_id=%s
                """,
                (link["article_upc_id"],),
            )
            article_upc_id = int(link["article_upc_id"])
        else:
            cur.execute(
                """
                INSERT INTO bridge_article_upc
                  (article_id,upc_id,relationship_type,is_primary,mapping_status,confidence)
                VALUES (%s,%s,'SELLING',TRUE,'CONFIRMED',1.0)
                """,
                (main_article_id, upc_id),
            )
            article_upc_id = int(cur.lastrowid)
        result["identity_applied"] += 1

        sell_id = _uom_id(cur, ov["selling_uom_code"])
        base_id = _uom_id(cur, ov["base_uom_code"]) if ov["base_uom_code"] else sell_id
        if sell_id is None:
            result["held"].append({"ean_upc": ean, "reason": "SELLING_UOM_CODE_NOT_IN_DIM_UOM"})
            continue

        cur.execute(
            """
            UPDATE selling_upc_uom_history
            SET mapping_status='SUPERSEDED',
                effective_to=COALESCE(effective_to,CURRENT_TIMESTAMP(6))
            WHERE upc_id=%s
              AND mapping_status='CONFIRMED'
              AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))
              AND NOT (
                  selling_uom_id=%s
                  AND COALESCE(base_uom_id,%s)=COALESCE(%s,%s)
                  AND COALESCE(base_qty_per_selling_unit,1)=COALESCE(%s,1)
              )
            """,
            (upc_id, sell_id, sell_id, base_id, sell_id, ov["base_qty_per_selling_unit"]),
        )

        cur.execute(
            """
            SELECT upc_uom_id
            FROM selling_upc_uom_history
            WHERE upc_id=%s
              AND selling_uom_id=%s
              AND COALESCE(base_uom_id,%s)=COALESCE(%s,%s)
            ORDER BY upc_uom_id DESC LIMIT 1
            """,
            (upc_id, sell_id, sell_id, base_id, sell_id),
        )
        urow = cur.fetchone()
        if urow:
            cur.execute(
                """
                UPDATE selling_upc_uom_history
                SET base_uom_id=%s,
                    base_qty_per_selling_unit=%s,
                    mapping_status='CONFIRMED',
                    confidence=1.0,
                    resolution_method='USER_CONFIRMED_OVERRIDE',
                    effective_to=NULL
                WHERE upc_uom_id=%s
                """,
                (base_id, ov["base_qty_per_selling_unit"], urow["upc_uom_id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO selling_upc_uom_history
                  (upc_id,selling_uom_id,base_uom_id,base_qty_per_selling_unit,
                   mapping_status,confidence,resolution_method)
                VALUES (%s,%s,%s,%s,'CONFIRMED',1.0,'USER_CONFIRMED_OVERRIDE')
                """,
                (upc_id, sell_id, base_id, ov["base_qty_per_selling_unit"]),
            )
        result["uom_applied"] += 1

        cur.execute(
            """
            SELECT evidence_id FROM normalized_source_evidence
            WHERE object_type='ARTICLE_UPC'
              AND object_id=%s
              AND evidence_role='USER_CONFIRMED_OVERRIDE_V705'
            LIMIT 1
            """,
            (article_upc_id,),
        )
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO normalized_source_evidence
                  (object_type,object_id,evidence_role,source_field_name,source_value_text,evidence_json)
                VALUES ('ARTICLE_UPC',%s,'USER_CONFIRMED_OVERRIDE_V705','ean_upc',%s,%s)
                """,
                (
                    article_upc_id,
                    ean,
                    json.dumps(
                        {
                            "article_number": article_number,
                            "canonical_main_article": anchor["main_article_number"],
                            "selling_uom": ov["selling_uom_code"],
                            "base_uom": ov["base_uom_code"],
                            "base_qty_per_selling_unit": str(ov["base_qty_per_selling_unit"]),
                            "source_note": ov["source_note"],
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                ),
            )

    return result
