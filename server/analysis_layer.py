from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

ANALYSIS_LAYER_VERSION = "1.3.0-all-department-oh"
SEAFOOD_DEPT_CODE = "400"

DEPARTMENT_REGISTRY = {
    "300": "MEAT",
    "400": "SEAFOOD",
    "500": "PRODUCE",
}


def ensure_analysis_layer_tables(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS article_department_observation (
            observation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            article_id BIGINT UNSIGNED NULL,
            article_number VARCHAR(64) NOT NULL,
            department_code VARCHAR(8) NOT NULL,
            department_name VARCHAR(32) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            business_date DATE NULL,
            batch_id BIGINT UNSIGNED NOT NULL,
            file_id BIGINT UNSIGNED NOT NULL,
            sheet_id BIGINT UNSIGNED NULL,
            source_row_number INT NULL,
            observed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (observation_id),
            UNIQUE KEY uq_article_department_source (
                article_number,department_code,source_type,file_id,source_row_number
            ),
            KEY ix_article_department_lookup (article_number,department_code,business_date),
            KEY ix_article_department_article (article_id,department_code,business_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS upc_department_observation (
            observation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            upc_id BIGINT UNSIGNED NULL,
            ean_upc VARCHAR(32) NOT NULL,
            department_code VARCHAR(8) NOT NULL,
            department_name VARCHAR(32) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            business_date DATE NULL,
            batch_id BIGINT UNSIGNED NOT NULL,
            file_id BIGINT UNSIGNED NOT NULL,
            sheet_id BIGINT UNSIGNED NULL,
            source_row_number INT NULL,
            observed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (observation_id),
            UNIQUE KEY uq_upc_department_source (
                ean_upc,department_code,source_type,file_id,source_row_number
            ),
            KEY ix_upc_department_lookup (ean_upc,department_code,business_date),
            KEY ix_upc_department_upc (upc_id,department_code,business_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_item_current (
            upc_id BIGINT UNSIGNED NOT NULL,
            ean_upc VARCHAR(32) NOT NULL,
            department_code VARCHAR(8) NOT NULL,
            department_name VARCHAR(32) NOT NULL,
            article_id BIGINT UNSIGNED NULL,
            article_number VARCHAR(64) NULL,
            family_id BIGINT UNSIGNED NULL,
            main_article_number VARCHAR(64) NULL,
            selling_description VARCHAR(255) NULL,
            family_description VARCHAR(255) NULL,
            product_class VARCHAR(32) NULL,
            selling_uom VARCHAR(32) NULL,
            base_uom VARCHAR(32) NULL,
            base_qty_per_selling_unit DECIMAL(24,8) NULL,
            current_cost_per_base_uom DECIMAL(24,8) NULL,
            current_cost_per_selling_unit DECIMAL(24,8) NULL,
            cost_source VARCHAR(64) NULL,
            cost_date DATE NULL,
            last_receipt_date DATE NULL,
            current_price DECIMAL(24,8) NULL,
            current_price_type VARCHAR(32) NULL,
            current_price_source VARCHAR(64) NULL,
            current_price_asof_date DATE NULL,
            sales_dollars_7d DECIMAL(24,8) NULL,
            pos_qty_7d DECIMAL(24,8) NULL,
            avg_selling_price_7d DECIMAL(24,8) NULL,
            upc_velocity_7d DECIMAL(24,8) NULL,
            sales_days_7d INT NULL,
            sales_dollars_30d DECIMAL(24,8) NULL,
            pos_qty_30d DECIMAL(24,8) NULL,
            avg_selling_price_30d DECIMAL(24,8) NULL,
            upc_velocity_30d DECIMAL(24,8) NULL,
            sales_days_30d INT NULL,
            family_pos_qty_7d DECIMAL(24,8) NULL,
            family_pos_velocity_7d DECIMAL(24,8) NULL,
            family_movement_7d DECIMAL(24,8) NULL,
            family_movement_uom VARCHAR(32) NULL,
            family_pos_movement_gap_7d DECIMAL(24,8) NULL,
            current_oh DECIMAL(24,8) NULL,
            current_oh_uom VARCHAR(32) NULL,
            oh_date DATE NULL,
            dos DECIMAL(24,8) NULL,
            doh DECIMAL(24,8) NULL,
            gp_pct_current DECIMAL(24,8) NULL,
            gp_dollars_7d DECIMAL(24,8) NULL,
            gp_per_day_7d DECIMAL(24,8) NULL,
            sweet_spot_price DECIMAL(24,8) NULL,
            sweet_spot_delta DECIMAL(24,8) NULL,
            wgpm_price DECIMAL(24,8) NULL,
            wgpm_delta DECIMAL(24,8) NULL,
            company_price_a DECIMAL(24,8) NULL,
            company_price_b DECIMAL(24,8) NULL,
            company_price_c DECIMAL(24,8) NULL,
            is_sale_promotion TINYINT(1) NOT NULL DEFAULT 0,
            fresh_live_age_status VARCHAR(32) NULL,
            frozen_velocity_status VARCHAR(32) NULL,
            analysis_status VARCHAR(32) NOT NULL,
            analysis_blocking_reason VARCHAR(255) NULL,
            source_quick_check_status VARCHAR(32) NULL,
            source_publish_batch_id BIGINT UNSIGNED NOT NULL,
            source_published_at DATETIME(6) NULL,
            analyzed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (upc_id),
            UNIQUE KEY uq_analysis_item_ean (ean_upc),
            KEY ix_analysis_item_department_status (department_code,analysis_status),
            KEY ix_analysis_item_family (family_id),
            KEY ix_analysis_item_class (department_code,product_class)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_family_current (
            family_id BIGINT UNSIGNED NOT NULL,
            department_code VARCHAR(8) NOT NULL,
            department_name VARCHAR(32) NOT NULL,
            main_article_number VARCHAR(64) NULL,
            family_description VARCHAR(255) NULL,
            product_class VARCHAR(32) NULL,
            upc_count INT NOT NULL,
            active_upc_count INT NOT NULL,
            ready_upc_count INT NOT NULL,
            hold_upc_count INT NOT NULL,
            historical_upc_count INT NOT NULL,
            sales_dollars_7d DECIMAL(24,8) NULL,
            pos_qty_7d DECIMAL(24,8) NULL,
            family_pos_velocity_7d DECIMAL(24,8) NULL,
            family_movement_7d DECIMAL(24,8) NULL,
            family_movement_uom VARCHAR(32) NULL,
            pos_movement_gap_7d DECIMAL(24,8) NULL,
            gp_dollars_7d DECIMAL(24,8) NULL,
            gp_per_day_7d DECIMAL(24,8) NULL,
            max_doh DECIMAL(24,8) NULL,
            min_dos DECIMAL(24,8) NULL,
            sale_promo_upc_count INT NOT NULL DEFAULT 0,
            frozen_velocity_status VARCHAR(32) NULL,
            analysis_status VARCHAR(32) NOT NULL,
            source_publish_batch_id BIGINT UNSIGNED NOT NULL,
            analyzed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (family_id),
            KEY ix_analysis_family_department_status (department_code,analysis_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_layer_status (
            department_code VARCHAR(8) NOT NULL,
            department_name VARCHAR(32) NOT NULL,
            layer_version VARCHAR(64) NOT NULL,
            layer_status VARCHAR(40) NOT NULL,
            source_publish_batch_id BIGINT UNSIGNED NULL,
            item_rows INT NOT NULL DEFAULT 0,
            ready_rows INT NOT NULL DEFAULT 0,
            hold_rows INT NOT NULL DEFAULT 0,
            historical_rows INT NOT NULL DEFAULT 0,
            family_rows INT NOT NULL DEFAULT 0,
            detail_json JSON NULL,
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                       ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (department_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def _mark_other_departments_pending(cur, batch_id: int, enabled_department_code: str) -> None:
    for code in DEPARTMENT_REGISTRY:
        if code in {SEAFOOD_DEPT_CODE, enabled_department_code}:
            continue
        cur.execute(
            """
            INSERT INTO analysis_layer_status
              (department_code,department_name,layer_version,layer_status,
               source_publish_batch_id,item_rows,ready_rows,hold_rows,historical_rows,
               family_rows,detail_json)
            VALUES (%s,%s,%s,'PENDING_PIPELINE_ENABLEMENT',%s,0,0,0,0,0,%s)
            ON DUPLICATE KEY UPDATE
              department_name=VALUES(department_name),
              layer_version=VALUES(layer_version),
              layer_status=VALUES(layer_status),
              source_publish_batch_id=VALUES(source_publish_batch_id),
              item_rows=0,ready_rows=0,hold_rows=0,historical_rows=0,family_rows=0,
              detail_json=VALUES(detail_json),
              updated_at=CURRENT_TIMESTAMP(6)
            """,
            (
                code,
                DEPARTMENT_REGISTRY[code],
                ANALYSIS_LAYER_VERSION,
                batch_id,
                json.dumps(
                    {
                        "reason": "SEAFOOD_FIRST_GATE",
                        "next_step": "Enable department-specific identity/price/cost authorities after Seafood analysis gate passes.",
                    }
                ),
            ),
        )


def refresh_analysis_layer(cur, batch_id: int, department_code: str = SEAFOOD_DEPT_CODE) -> dict[str, Any]:
    if department_code not in DEPARTMENT_REGISTRY:
        raise ValueError(f"Unsupported department {department_code}.")

    department_name = DEPARTMENT_REGISTRY[department_code]
    cur.execute("DELETE FROM analysis_item_current WHERE department_code=%s", (department_code,))
    cur.execute("DELETE FROM analysis_family_current WHERE department_code=%s", (department_code,))

    # Family POS quantity is derived only from UPC POS quantities. 251/252 remains
    # a separate whole-family movement metric and is never substituted for UPC qty.
    cur.execute(
        """
        SELECT family_id,
               SUM(COALESCE(pos_qty_7d,0)) AS family_pos_qty_7d,
               CASE
                 WHEN COUNT(DISTINCT NULLIF(UPPER(TRIM(selling_uom)),''))=1
                  AND MAX(COALESCE(sales_days_7d,0))>0
                 THEN SUM(COALESCE(pos_qty_7d,0))/MAX(sales_days_7d)
                 ELSE NULL
               END AS family_pos_velocity_7d,
               COUNT(DISTINCT NULLIF(UPPER(TRIM(selling_uom)),'')) AS selling_uom_count,
               CASE
                 WHEN COUNT(DISTINCT NULLIF(UPPER(TRIM(selling_uom)),''))=1
                 THEN MAX(UPPER(TRIM(selling_uom)))
                 ELSE NULL
               END AS family_pos_uom
        FROM quick_check_current q
        WHERE q.family_id IS NOT NULL
          AND (
              EXISTS (
                  SELECT 1
                  FROM upc_department_observation d
                  WHERE d.ean_upc=q.ean_upc
                    AND d.department_code=%s
                    AND NOT EXISTS (
                        SELECT 1
                        FROM upc_department_observation newer
                        WHERE newer.ean_upc=d.ean_upc
                          AND (
                              COALESCE(newer.business_date,'1000-01-01') > COALESCE(d.business_date,'1000-01-01')
                              OR (
                                  COALESCE(newer.business_date,'1000-01-01') = COALESCE(d.business_date,'1000-01-01')
                                  AND newer.observation_id > d.observation_id
                              )
                          )
                    )
              )
              OR EXISTS (
                  SELECT 1
                  FROM article_department_observation ad
                  WHERE ad.article_number=q.article_number
                    AND ad.department_code=%s
                    AND NOT EXISTS (
                        SELECT 1
                        FROM article_department_observation newer_ad
                        WHERE newer_ad.article_number=ad.article_number
                          AND (
                              COALESCE(newer_ad.business_date,'1000-01-01') > COALESCE(ad.business_date,'1000-01-01')
                              OR (
                                  COALESCE(newer_ad.business_date,'1000-01-01') = COALESCE(ad.business_date,'1000-01-01')
                                  AND newer_ad.observation_id > ad.observation_id
                              )
                          )
                    )
              )
          )
        GROUP BY family_id
        """,
        (department_code, department_code,),
    )
    family_pos = {
        int(r["family_id"]): r
        for r in cur.fetchall()
        if r.get("family_id") is not None
    }

    cur.execute(
        """
        SELECT q.*
        FROM quick_check_current q
        WHERE (
            EXISTS (
                SELECT 1
                FROM upc_department_observation d
                WHERE d.ean_upc=q.ean_upc
                  AND d.department_code=%s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM upc_department_observation newer
                      WHERE newer.ean_upc=d.ean_upc
                        AND (
                            COALESCE(newer.business_date,'1000-01-01') > COALESCE(d.business_date,'1000-01-01')
                            OR (
                                COALESCE(newer.business_date,'1000-01-01') = COALESCE(d.business_date,'1000-01-01')
                                AND newer.observation_id > d.observation_id
                            )
                        )
                  )
            )
            OR EXISTS (
                SELECT 1
                FROM article_department_observation ad
                WHERE ad.article_number=q.article_number
                  AND ad.department_code=%s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM article_department_observation newer_ad
                      WHERE newer_ad.article_number=ad.article_number
                        AND (
                            COALESCE(newer_ad.business_date,'1000-01-01') > COALESCE(ad.business_date,'1000-01-01')
                            OR (
                                COALESCE(newer_ad.business_date,'1000-01-01') = COALESCE(ad.business_date,'1000-01-01')
                                AND newer_ad.observation_id > ad.observation_id
                            )
                        )
                  )
            )
        )
        ORDER BY q.upc_id
        """,
        (department_code, department_code,),
    )
    qrows = cur.fetchall()
    item_rows = ready_rows = hold_rows = historical_rows = 0

    for q in qrows:
        family_id = int(q["family_id"]) if q.get("family_id") is not None else None
        fp = family_pos.get(family_id, {}) if family_id is not None else {}
        family_pos_qty_7d = fp.get("family_pos_qty_7d")
        family_pos_velocity_7d = fp.get("family_pos_velocity_7d")
        family_pos_uom = str(fp.get("family_pos_uom") or "").upper() or None
        family_movement_7d = q.get("family_movement_7d")
        family_movement_uom = str(q.get("family_movement_uom") or "").upper() or None
        gap = None
        if (
            family_pos_qty_7d is not None
            and family_movement_7d is not None
            and family_pos_uom is not None
            and family_movement_uom is not None
            and family_pos_uom == family_movement_uom
        ):
            gap = Decimal(str(family_pos_qty_7d)) - Decimal(str(family_movement_7d))

        avg7 = None
        if q.get("pos_qty_7d") not in (None, 0):
            avg7 = Decimal(str(q.get("sales_dollars_7d") or 0)) / Decimal(str(q["pos_qty_7d"]))
        avg30 = None
        if q.get("pos_qty_30d") not in (None, 0):
            avg30 = Decimal(str(q.get("sales_dollars_30d") or 0)) / Decimal(str(q["pos_qty_30d"]))

        current_price = Decimal(str(q["current_price"])) if q.get("current_price") is not None else None
        sweet = Decimal(str(q["sweet_spot_price"])) if q.get("sweet_spot_price") is not None else None
        wgpm = Decimal(str(q["wgpm_price"])) if q.get("wgpm_price") is not None else None

        pclass = str(q.get("product_class") or "").upper()
        doh = Decimal(str(q["doh"])) if q.get("doh") is not None else None
        fresh_age = None
        if pclass in {"FRESH", "LIVE"}:
            if doh is None:
                fresh_age = "DOH_MISSING"
            elif doh <= 4:
                fresh_age = "DOH_1_4"
            elif doh <= 7:
                fresh_age = "DOH_5_7"
            elif doh <= 10:
                fresh_age = "DOH_8_10"
            else:
                fresh_age = "DOH_GT_10"

        frozen_velocity = None
        if pclass == "FROZEN":
            if family_pos_velocity_7d is None:
                frozen_velocity = "FAMILY_POS_UOM_UNRESOLVED"
            else:
                fam7 = Decimal(str(family_pos_qty_7d or 0))
                frozen_velocity = "UNDER_3_UNITS_7D" if fam7 < Decimal("3") else "AT_LEAST_3_UNITS_7D"

        source_status = str(q.get("quick_check_status") or "")
        if source_status == "READY":
            status = "READY"
            ready_rows += 1
        elif source_status == "HISTORICAL_ONLY":
            status = "HISTORICAL_ONLY"
            historical_rows += 1
        else:
            status = "QA_HOLD"
            hold_rows += 1

        cur.execute(
            """
            INSERT INTO analysis_item_current (
                upc_id,ean_upc,department_code,department_name,article_id,article_number,
                family_id,main_article_number,selling_description,family_description,
                product_class,selling_uom,base_uom,base_qty_per_selling_unit,
                current_cost_per_base_uom,current_cost_per_selling_unit,cost_source,cost_date,
                last_receipt_date,current_price,current_price_type,current_price_source,
                current_price_asof_date,sales_dollars_7d,pos_qty_7d,avg_selling_price_7d,
                upc_velocity_7d,sales_days_7d,sales_dollars_30d,pos_qty_30d,
                avg_selling_price_30d,upc_velocity_30d,sales_days_30d,
                family_pos_qty_7d,family_pos_velocity_7d,family_movement_7d,
                family_movement_uom,family_pos_movement_gap_7d,current_oh,current_oh_uom,
                oh_date,dos,doh,gp_pct_current,gp_dollars_7d,gp_per_day_7d,
                sweet_spot_price,sweet_spot_delta,wgpm_price,wgpm_delta,
                company_price_a,company_price_b,company_price_c,is_sale_promotion,
                fresh_live_age_status,frozen_velocity_status,analysis_status,
                analysis_blocking_reason,source_quick_check_status,source_publish_batch_id,
                source_published_at,analyzed_at
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,CURRENT_TIMESTAMP(6)
            )
            """,
            (
                q["upc_id"], q["ean_upc"], department_code, department_name,
                q.get("article_id"), q.get("article_number"), q.get("family_id"),
                q.get("main_article_number"), q.get("selling_description"),
                q.get("family_description"), q.get("product_class"), q.get("selling_uom"),
                q.get("base_uom"), q.get("base_qty_per_selling_unit"),
                q.get("current_cost_per_base_uom"), q.get("current_cost_per_selling_unit"),
                q.get("cost_source"), q.get("cost_date"), q.get("last_receipt_date"),
                q.get("current_price"), q.get("current_price_type"), q.get("current_price_source"),
                q.get("current_price_asof_date"), q.get("sales_dollars_7d"), q.get("pos_qty_7d"),
                avg7, q.get("upc_velocity_7d"), q.get("sales_days_7d"),
                q.get("sales_dollars_30d"), q.get("pos_qty_30d"), avg30,
                q.get("upc_velocity_30d"), q.get("sales_days_30d"),
                family_pos_qty_7d, family_pos_velocity_7d, family_movement_7d,
                q.get("family_movement_uom"), gap, q.get("current_oh"), q.get("current_oh_uom"),
                q.get("oh_date"), q.get("dos"), q.get("doh"), q.get("gp_pct_current"),
                q.get("gp_dollars_7d"), q.get("gp_per_day_7d"), q.get("sweet_spot_price"),
                (sweet - current_price) if sweet is not None and current_price is not None else None,
                q.get("wgpm_price"),
                (wgpm - current_price) if wgpm is not None and current_price is not None else None,
                q.get("company_price_a"), q.get("company_price_b"), q.get("company_price_c"),
                1 if str(q.get("current_price_type") or "").upper() == "SALE" else 0,
                fresh_age, frozen_velocity, status, q.get("blocking_reason"),
                source_status, batch_id, q.get("published_at"),
            ),
        )
        item_rows += 1

    cur.execute(
        """
        INSERT INTO analysis_family_current (
            family_id,department_code,department_name,main_article_number,family_description,
            product_class,upc_count,active_upc_count,ready_upc_count,hold_upc_count,
            historical_upc_count,sales_dollars_7d,pos_qty_7d,family_pos_velocity_7d,
            family_movement_7d,family_movement_uom,pos_movement_gap_7d,gp_dollars_7d,
            gp_per_day_7d,max_doh,min_dos,sale_promo_upc_count,frozen_velocity_status,
            analysis_status,source_publish_batch_id,analyzed_at
        )
        SELECT
            family_id,%s,%s,MAX(main_article_number),MAX(family_description),
            CASE WHEN COUNT(DISTINCT NULLIF(product_class,''))=1 THEN MAX(product_class) ELSE 'MIXED' END,
            COUNT(*),
            SUM(analysis_status<>'HISTORICAL_ONLY'),
            SUM(analysis_status='READY'),
            SUM(analysis_status='QA_HOLD'),
            SUM(analysis_status='HISTORICAL_ONLY'),
            SUM(COALESCE(sales_dollars_7d,0)),
            SUM(COALESCE(pos_qty_7d,0)),
            MAX(family_pos_velocity_7d),
            MAX(family_movement_7d),
            CASE WHEN COUNT(DISTINCT NULLIF(family_movement_uom,''))=1 THEN MAX(family_movement_uom) ELSE NULL END,
            MAX(family_pos_movement_gap_7d),
            SUM(COALESCE(gp_dollars_7d,0)),
            SUM(COALESCE(gp_per_day_7d,0)),
            MAX(doh),
            MIN(dos),
            SUM(is_sale_promotion),
            CASE
              WHEN COUNT(DISTINCT NULLIF(product_class,''))=1
               AND MAX(product_class)='FROZEN'
               AND MAX(family_pos_velocity_7d) IS NULL THEN 'FAMILY_POS_UOM_UNRESOLVED'
              WHEN COUNT(DISTINCT NULLIF(product_class,''))=1
               AND MAX(product_class)='FROZEN'
               AND SUM(COALESCE(pos_qty_7d,0))<3 THEN 'UNDER_3_UNITS_7D'
              WHEN COUNT(DISTINCT NULLIF(product_class,''))=1
               AND MAX(product_class)='FROZEN' THEN 'AT_LEAST_3_UNITS_7D'
              ELSE NULL
            END,
            CASE
              WHEN SUM(analysis_status='QA_HOLD')>0 THEN 'QA_HOLD'
              WHEN SUM(analysis_status='READY')>0 THEN 'READY'
              ELSE 'HISTORICAL_ONLY'
            END,
            %s,CURRENT_TIMESTAMP(6)
        FROM analysis_item_current
        WHERE department_code=%s AND family_id IS NOT NULL
        GROUP BY family_id
        """,
        (department_code, department_name, batch_id, department_code),
    )
    family_rows = int(cur.rowcount or 0)

    layer_status = "READY_WITH_HOLDS" if hold_rows else "READY"
    if item_rows == 0:
        layer_status = "QA_HOLD"

    detail = {
        "contract": "ANALYSIS_LAYER_V1",
        "upc_quantity_authority": "POS_ONLY",
        "family_movement_authority": "MVT_251_252_SEPARATE",
        "cost_authority": [
            "MOVEMENT_RECEIPT_VALUATION_101_107_109",
            "LIVE_FRESH_FROZEN_OFFICIAL_REPORT",
            "ON_HAND_EXPLICIT_COST_FALLBACK",
            "USER_CONFIRMED_FAMILY_COST",
        ],
        "price_authority": "MOST_RECENT_PRICE_LIST_VS_POS; SAME_DATE_PRICE_LIST_WINS",
        "price_list_priority": ["IN STORE", "SALE", "TPR", "REG"],
        "department_contract": "SEAFOOD_MEAT_PRODUCE_ENABLED",
    }
    cur.execute(
        """
        INSERT INTO analysis_layer_status
          (department_code,department_name,layer_version,layer_status,
           source_publish_batch_id,item_rows,ready_rows,hold_rows,historical_rows,
           family_rows,detail_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
          department_name=VALUES(department_name),
          layer_version=VALUES(layer_version),
          layer_status=VALUES(layer_status),
          source_publish_batch_id=VALUES(source_publish_batch_id),
          item_rows=VALUES(item_rows),ready_rows=VALUES(ready_rows),
          hold_rows=VALUES(hold_rows),historical_rows=VALUES(historical_rows),
          family_rows=VALUES(family_rows),detail_json=VALUES(detail_json),
          updated_at=CURRENT_TIMESTAMP(6)
        """,
        (
            department_code, department_name, ANALYSIS_LAYER_VERSION, layer_status,
            batch_id, item_rows, ready_rows, hold_rows, historical_rows, family_rows,
            json.dumps(detail),
        ),
    )
    _mark_other_departments_pending(cur, batch_id, department_code)

    return {
        "department_code": department_code,
        "department_name": department_name,
        "layer_version": ANALYSIS_LAYER_VERSION,
        "status": layer_status,
        "item_rows": item_rows,
        "ready_rows": ready_rows,
        "hold_rows": hold_rows,
        "historical_rows": historical_rows,
        "family_rows": family_rows,
    }


def audit_analysis_layer(cur, batch_id: int, department_code: str = SEAFOOD_DEPT_CODE) -> dict[str, Any]:
    cur.execute(
        """
        SELECT layer_status,source_publish_batch_id,item_rows,ready_rows,hold_rows,
               historical_rows,family_rows
        FROM analysis_layer_status
        WHERE department_code=%s
        """,
        (department_code, department_code,),
    )
    status = cur.fetchone()

    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM quick_check_current q
        WHERE EXISTS (
            SELECT 1
            FROM upc_department_observation d
            WHERE d.ean_upc=q.ean_upc
              AND d.department_code=%s
              AND NOT EXISTS (
                  SELECT 1
                  FROM upc_department_observation newer
                  WHERE newer.ean_upc=d.ean_upc
                    AND (
                        COALESCE(newer.business_date,'1000-01-01') > COALESCE(d.business_date,'1000-01-01')
                        OR (
                            COALESCE(newer.business_date,'1000-01-01') = COALESCE(d.business_date,'1000-01-01')
                            AND newer.observation_id > d.observation_id
                        )
                    )
              )
        )
        """,
        (department_code, department_code,),
    )
    qc_count = int((cur.fetchone() or {}).get("c") or 0)
    cur.execute(
        "SELECT COUNT(*) AS c FROM analysis_item_current WHERE department_code=%s",
        (department_code, department_code,),
    )
    analysis_count = int((cur.fetchone() or {}).get("c") or 0)
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM analysis_item_current
        WHERE department_code=%s
          AND source_publish_batch_id<>%s
        """,
        (department_code, batch_id),
    )
    stale = int((cur.fetchone() or {}).get("c") or 0)

    checks = {
        "status_row_exists": bool(status),
        "batch_bound": bool(status and int(status.get("source_publish_batch_id") or 0) == int(batch_id)),
        "item_parity_with_quick_check": analysis_count == qc_count and analysis_count > 0,
        "no_stale_batch_rows": stale == 0,
        "layer_status_publishable": bool(status and status.get("layer_status") in {"READY", "READY_WITH_HOLDS"}),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "quick_check_rows": qc_count,
        "analysis_item_rows": analysis_count,
        "status": status,
    }
