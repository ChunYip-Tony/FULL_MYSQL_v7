from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

USER_CONFIRMED_UOM_REVIEW_20260926 = (
    # Group A: user confirmed these exact UPCs are sold by LB.
    {"ean_upc":"24596200000","article_number":"1345962","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: SEASONED BABY OCTOPUS; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"24595700000","article_number":"1345957","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: CHUKA IKA SANSAI; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"24599600000","article_number":"1345996","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: ESCOLAR LOIN SPR WHT TUNA; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"24513600000","article_number":"1400136","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: GREEN MUSSEL HALF SHELL; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},

    # Group B: user confirmed POS Selling UOM=PACK only.
    # Base/cost conversion remains intentionally unresolved unless separately evidenced.
    {"ean_upc":"8231817551","article_number":"1351625","selling_uom_code":"PACK","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: 26/30 H/L SHRIMP 10/4LB; POS Selling UOM=PACK only; no base conversion inferred."},
    {"ean_upc":"4029551780","article_number":"1366580","selling_uom_code":"PACK","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: OYSTER IN SHELL 60EA; POS Selling UOM=PACK only; no base conversion inferred."},
    {"ean_upc":"70286869729","article_number":"3480411","selling_uom_code":"PACK","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: FROZEN KUNG FU SNAKEHEAD FISH FILLETS 40/8.8OZ; POS Selling UOM=PACK only; no base conversion inferred."},
    {"ean_upc":"81223402832","article_number":"3468360","selling_uom_code":"PACK","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: 26-30 IQF WHT P&D T-OFF CF SEACHEF SA/CN 20/1LB; POS Selling UOM=PACK only; no base conversion inferred."},

    # Group C: user confirmed the remaining 14 reviewed UPCs are sold by LB.
    # These are exact per-UPC confirmations, not a new prefix-wide rule.
    {"ean_upc":"4841","article_number":"3400841","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: 30/40 H/O BLUE DIAMOND WHITE SHRIMP; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26570500000","article_number":"3467050","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: FUZHOU FISH BALL; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26210000000","article_number":"3461000","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: SOUTHERN BLUEFIN TUNA O-TORO CUT (BELLY); POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26082100000","article_number":"3468210","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: 20/30 H/O SHRIMP; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26517800000","article_number":"3461780","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: DRIED BABY SHRIMP; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26571300000","article_number":"3467130","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: CHEESE FISH SAUSAGE; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26572100000","article_number":"3467210","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: FLOWER CHEESE TOFU; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26572200000","article_number":"3467220","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: SILVER CARP FISH BALL; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26018000000","article_number":"3461800","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: THREAD FIN; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26217000000","article_number":"3461700","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: POLLOCK ROE; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26513000000","article_number":"3461300","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: CALAMARI OCTOPUS SALES; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"4883","article_number":"3400883","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: COLD WATER SHRIMP (COOKED); POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26083500000","article_number":"3468350","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: BLUE RIVER 21/25 IQF EZP SHRIMP; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
    {"ean_upc":"26022200000","article_number":"3462220","selling_uom_code":"LB","base_uom_code":None,"base_qty_per_selling_unit":None,
     "source_note":"USER_CONFIRMED_UOM_REVIEW_20260926: BASS HYBD STRP; POS Selling UOM=LB only; no Base/Inventory UOM or conversion factor inferred."},
)

SEED_OVERRIDES = (
    {
        "ean_upc": "4918",
        "article_number": "3401602",
        "selling_uom_code": "LB",
        "base_uom_code": "LB",
        "base_qty_per_selling_unit": 1,
        "source_note": "User confirmed: UPC 4918 belongs to Article 3401602 and is sold by LB.",
    },
    {
        "ean_upc": "75539372208",
        "article_number": "3480452",
        "selling_uom_code": "PACK",
        "base_uom_code": None,
        "base_qty_per_selling_unit": None,
        "source_note": "User confirmed 2026-09-26: UPC 75539372208 belongs to Main/Family Article 3480452; POS Selling UOM=PACK; source pack specification=24/12OZ. Pack specification is preserved as evidence only and is not used to infer base/cost conversion.",
    },
    {
        "ean_upc": "81223402610",
        "article_number": "3461050",
        "selling_uom_code": "PACK",
        "base_uom_code": "EA",
        "base_qty_per_selling_unit": 1,
        "source_note": "Resolved 2026-09-26 from combined authoritative evidence: user confirmed POS Selling UOM=PACK and case configuration=40/150G; receipt 107 for Article 3461050 shows 3 CV = 120 EA with $330 valuation, exactly matching 3 cases x 40 selling packs = 120. Therefore 1 selling PACK = 1 base EA and authoritative receipt cost is $2.75 per PACK.",
    },
 ) + USER_CONFIRMED_UOM_REVIEW_20260926


USER_CONFIRMED_COST_SELLING_CONVERSIONS_20260926 = (
    {
        "ean_upc": "402954957",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "BX",
        "cost_qty": Decimal("3"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 BX = 3 LB.",
    },
    {
        "ean_upc": "75339379281",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "EA",
        "cost_qty": Decimal("2"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 EA = 2 LB.",
    },
    {
        "ean_upc": "4816",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "EA",
        "cost_qty": Decimal("4"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 EA = 4 LB.",
    },
    {
        "ean_upc": "8231817551",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "PACK",
        "cost_qty": Decimal("2"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 PACK = 2 LB.",
    },
    {
        "ean_upc": "4029551288",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "PAC",
        "cost_qty": Decimal("2"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 PAC = 2 LB.",
    },
    {
        "ean_upc": "7441092018",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "EA",
        "cost_qty": Decimal("1.2"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 EA = 1.2 LB.",
    },
    {
        "ean_upc": "4883",
        "selling_qty": Decimal("2.2"),
        "selling_uom_code": "LB",
        "cost_qty": Decimal("1"),
        "cost_uom_code": "PAC",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 PAC = 2.2 LB; equivalently 2.2 selling LB = 1 cost PAC.",
    },
    {
        "ean_upc": "81223402632",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "PACK",
        "cost_qty": Decimal("1"),
        "cost_uom_code": "BAG",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 PACK = 1 BAG.",
    },
    {
        "ean_upc": "4843",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "EA",
        "cost_qty": Decimal("2"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 EA = 2 LB.",
    },
    {
        "ean_upc": "82995307020",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "EA",
        "cost_qty": Decimal("4.4"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 EA = 4.4 LB.",
    },
    {
        "ean_upc": "81223402832",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "PACK",
        "cost_qty": Decimal("1"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 PACK = 1 LB.",
    },
    {
        "ean_upc": "4029550743",
        "selling_qty": Decimal("1"),
        "selling_uom_code": "EA",
        "cost_qty": Decimal("1"),
        "cost_uom_code": "LB",
        "source_note": "USER_CONFIRMED_COST_CONVERSION_20260926: 1 EA = 1 LB.",
    },
)


USER_CONFIRMED_FAMILY_COSTS_20260926 = (
    {"main_article_number":"1341156","cost_amount":Decimal("3.82"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Pony Fish = $3.82/LB."},
    {"main_article_number":"1341521","cost_amount":Decimal("2.19"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Sierra 2-4 = $2.19/LB."},
    {"main_article_number":"1342316","cost_amount":Decimal("4.26"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Fish Tofu = $4.26/LB."},
    {"main_article_number":"1351700","cost_amount":Decimal("4.36"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: 41/50 H/L Shrimp = $4.36/LB."},
    {"main_article_number":"1354803","cost_amount":Decimal("5.09"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: 41/50 PUD White Shrimp = $5.09/LB."},
    {"main_article_number":"1361120","cost_amount":Decimal("9.00"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Fresh/Live Maine Lobster family = $9.00/LB."},
    {"main_article_number":"1361660","cost_amount":Decimal("5.09"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Live Manila Clam = $5.09/LB."},
    {"main_article_number":"1361689","cost_amount":Decimal("1.79"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Big Head Carp = $1.79/LB."},
    {"main_article_number":"1361697","cost_amount":Decimal("1.99"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Fresh Ocean Perch = $1.99/LB."},
    {"main_article_number":"1361760","cost_amount":Decimal("2.69"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Fresh Catfish family = $2.69/LB."},
    {"main_article_number":"1361999","cost_amount":Decimal("2.09"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Mullet = $2.09/LB."},
    {"main_article_number":"1363514","cost_amount":Decimal("6.59"),"cost_uom_code":"LB","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Sea Bream - New Zealand = $6.59/LB."},
    {"main_article_number":"1366580","cost_amount":Decimal("0.82"),"cost_uom_code":"EA","confirmed_date":"2026-09-26",
     "source_note":"USER_CONFIRMED_FAMILY_COST_20260926: Oyster in Shell family = $0.82/EA."},
)

USER_CONFIRMED_FAMILY_SUBARTICLES_20260926 = (
    {"main_article_number":"1361120","sub_article_number":"2011726","ean_upc":"24063300000",
     "description":"LIVE MAINE LOBSTER-S",
     "source_note":"USER_CONFIRMED_FAMILY_SUBARTICLE_20260926: UPC 24063300000 / Article 2011726 is a sub-article under Main/Family 1361120."},
    {"main_article_number":"1361120","sub_article_number":"2011727","ean_upc":"24063400000",
     "description":"LIVE MAINE LOBSTER-M",
     "source_note":"USER_CONFIRMED_FAMILY_SUBARTICLE_20260926: UPC 24063400000 / Article 2011727 is a sub-article under Main/Family 1361120."},
)


SEED_RETIREMENTS = (
    {
        "ean_upc": "26510500000",
        "retirement_reason": "USER_CONFIRMED_NONEXISTENT_UPC",
        "source_note": "User confirmed 2026-09-26: UPC 26510500000 does not exist. Preserve raw-source provenance, but exclude it from resolved/current product identity, active mappings, UOM resolution, Quick Check, related UPCs, and future publishing.",
    },
)


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


def ensure_override_table(cur) -> None:
    if _table_exists(cur, 'manual_upc_override'):
        return
    cur.execute(
        """
        CREATE TABLE manual_upc_override (
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



def ensure_family_cost_table(cur) -> None:
    if _table_exists(cur, 'manual_family_cost_authority'):
        return
    cur.execute(
        """
        CREATE TABLE manual_family_cost_authority (
            authority_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            main_article_number VARCHAR(64) NOT NULL,
            cost_amount DECIMAL(24,8) NOT NULL,
            cost_uom_code VARCHAR(32) NOT NULL,
            confirmed_date DATE NOT NULL,
            authority_status VARCHAR(24) NOT NULL DEFAULT 'CONFIRMED',
            source_note VARCHAR(512) NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                       ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (authority_id),
            UNIQUE KEY uq_manual_family_cost_authority (main_article_number),
            KEY ix_manual_family_cost_status (authority_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def seed_confirmed_family_costs(cur) -> int:
    changed = 0
    for row in USER_CONFIRMED_FAMILY_COSTS_20260926:
        cur.execute(
            """
            INSERT INTO manual_family_cost_authority
              (main_article_number,cost_amount,cost_uom_code,confirmed_date,authority_status,source_note)
            VALUES (%s,%s,%s,%s,'CONFIRMED',%s)
            ON DUPLICATE KEY UPDATE
              cost_amount=VALUES(cost_amount),
              cost_uom_code=VALUES(cost_uom_code),
              confirmed_date=VALUES(confirmed_date),
              authority_status='CONFIRMED',
              source_note=VALUES(source_note)
            """,
            (
                row["main_article_number"],
                row["cost_amount"],
                row["cost_uom_code"],
                row["confirmed_date"],
                row["source_note"],
            ),
        )
        changed += 1
    return changed


def apply_manual_family_costs(cur) -> dict[str, Any]:
    seeded = seed_confirmed_family_costs(cur)
    cur.execute(
        """
        SELECT m.main_article_number,m.cost_amount,m.cost_uom_code,m.confirmed_date,
               pf.family_id,a.article_id
        FROM manual_family_cost_authority m
        LEFT JOIN product_family pf
          ON pf.main_article_number=m.main_article_number
        LEFT JOIN article a
          ON a.article_number=m.main_article_number
        WHERE m.authority_status='CONFIRMED'
        ORDER BY m.authority_id
        """
    )
    rows = cur.fetchall()
    held = []
    verified = 0
    for row in rows:
        if row.get("family_id") is None or row.get("article_id") is None:
            held.append({
                "main_article_number": row["main_article_number"],
                "reason": "MAIN_FAMILY_IDENTITY_NOT_READY",
            })
            continue
        if _uom_id(cur, row["cost_uom_code"]) is None:
            held.append({
                "main_article_number": row["main_article_number"],
                "reason": "COST_UOM_CODE_NOT_IN_DIM_UOM",
            })
            continue
        if row.get("cost_amount") is None or Decimal(str(row["cost_amount"])) <= 0:
            held.append({
                "main_article_number": row["main_article_number"],
                "reason": "NONPOSITIVE_COST",
            })
            continue
        verified += 1
    return {
        "seeded_or_refreshed": seeded,
        "authorities_examined": len(rows),
        "verified": verified,
        "held": held,
    }


def confirmed_family_cost(cur, family_id: int) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT m.main_article_number,m.cost_amount,m.cost_uom_code,m.confirmed_date,m.source_note
        FROM product_family pf
        JOIN manual_family_cost_authority m
          ON m.main_article_number=pf.main_article_number
         AND m.authority_status='CONFIRMED'
        WHERE pf.family_id=%s
        LIMIT 1
        """,
        (family_id,),
    )
    return cur.fetchone()


def apply_manual_family_subarticles(cur) -> dict[str, Any]:
    result = {"examined":0,"family_links":0,"upc_links":0,"upc_not_present":[],"held":[]}
    for row in USER_CONFIRMED_FAMILY_SUBARTICLES_20260926:
        result["examined"] += 1
        cur.execute(
            """SELECT pf.family_id,ma.article_id AS main_article_id
               FROM product_family pf
               JOIN article ma ON ma.article_number=pf.main_article_number
               WHERE pf.main_article_number=%s
               LIMIT 1""",
            (row["main_article_number"],),
        )
        fam = cur.fetchone()
        if not fam:
            result["held"].append({"sub_article_number":row["sub_article_number"],"reason":"MAIN_FAMILY_NOT_READY"})
            continue
        family_id = int(fam["family_id"])

        cur.execute("SELECT article_id FROM article WHERE article_number=%s LIMIT 1",(row["sub_article_number"],))
        ar = cur.fetchone()
        if ar:
            sub_article_id = int(ar["article_id"])
            cur.execute(
                "UPDATE article SET article_description=COALESCE(article_description,%s),record_status='ACTIVE' WHERE article_id=%s",
                (row["description"],sub_article_id),
            )
        else:
            cur.execute(
                "INSERT INTO article (article_number,article_description,record_status) VALUES (%s,%s,'ACTIVE')",
                (row["sub_article_number"],row["description"]),
            )
            sub_article_id = int(cur.lastrowid)

        cur.execute(
            """SELECT baf.article_family_id,baf.family_id
               FROM bridge_article_family baf
               WHERE baf.article_id=%s
                 AND baf.mapping_status='CONFIRMED'
                 AND baf.is_primary=TRUE
                 AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))""",
            (sub_article_id,),
        )
        active = cur.fetchall()
        conflicts = [x for x in active if int(x["family_id"]) != family_id]
        if conflicts:
            result["held"].append({
                "sub_article_number":row["sub_article_number"],
                "reason":"EXISTING_CONFIRMED_CROSS_FAMILY_LINK",
                "existing_family_ids":[int(x["family_id"]) for x in conflicts],
            })
            continue

        cur.execute(
            """SELECT article_family_id FROM bridge_article_family
               WHERE article_id=%s AND family_id=%s AND relationship_type='SUB'
               ORDER BY article_family_id DESC LIMIT 1""",
            (sub_article_id,family_id),
        )
        link=cur.fetchone()
        if link:
            article_family_id=int(link["article_family_id"])
            cur.execute(
                """UPDATE bridge_article_family
                   SET mapping_status='CONFIRMED',is_primary=TRUE,confidence=1.0,valid_to=NULL
                   WHERE article_family_id=%s""",
                (article_family_id,),
            )
        else:
            cur.execute(
                """INSERT INTO bridge_article_family
                   (article_id,family_id,relationship_type,is_primary,mapping_status,confidence)
                   VALUES (%s,%s,'SUB',TRUE,'CONFIRMED',1.0)""",
                (sub_article_id,family_id),
            )
            article_family_id=int(cur.lastrowid)
        result["family_links"] += 1

        cur.execute("SELECT upc_id FROM selling_upc WHERE ean_upc=%s LIMIT 1",(row["ean_upc"],))
        upc=cur.fetchone()
        if not upc:
            # Do not manufacture a current selling identity from a mapping-only
            # confirmation. The SUB Article->Family authority is persisted now;
            # the UPC->SUB evidence will be attached automatically if/when the
            # UPC appears from a real source.
            result["upc_not_present"].append(row["ean_upc"])
            continue

        upc_id=int(upc["upc_id"])
        cur.execute(
            "UPDATE selling_upc SET selling_description=COALESCE(selling_description,%s) WHERE upc_id=%s",
            (row["description"],upc_id),
        )

        cur.execute(
            """SELECT article_upc_id FROM bridge_article_upc
               WHERE article_id=%s AND upc_id=%s AND relationship_type='SELLING'
               ORDER BY article_upc_id DESC LIMIT 1""",
            (sub_article_id,upc_id),
        )
        ul=cur.fetchone()
        if ul:
            cur.execute(
                """UPDATE bridge_article_upc
                   SET mapping_status='CONFIRMED',is_primary=FALSE,confidence=1.0,valid_to=NULL
                   WHERE article_upc_id=%s""",
                (ul["article_upc_id"],),
            )
            article_upc_id=int(ul["article_upc_id"])
        else:
            cur.execute(
                """INSERT INTO bridge_article_upc
                   (article_id,upc_id,relationship_type,is_primary,mapping_status,confidence)
                   VALUES (%s,%s,'SELLING',FALSE,'CONFIRMED',1.0)""",
                (sub_article_id,upc_id),
            )
            article_upc_id=int(cur.lastrowid)
        result["upc_links"] += 1

        for object_type, object_id, role in (
            ("ARTICLE_FAMILY",article_family_id,"USER_CONFIRMED_FAMILY_SUBARTICLE_20260926"),
            ("ARTICLE_UPC",article_upc_id,"USER_CONFIRMED_FAMILY_SUBARTICLE_20260926"),
        ):
            cur.execute(
                """SELECT evidence_id FROM normalized_source_evidence
                   WHERE object_type=%s AND object_id=%s AND evidence_role=%s LIMIT 1""",
                (object_type,object_id,role),
            )
            if not cur.fetchone():
                cur.execute(
                    """INSERT INTO normalized_source_evidence
                       (object_type,object_id,evidence_role,source_field_name,source_value_text,evidence_json)
                       VALUES (%s,%s,%s,'user_confirmation',%s,%s)""",
                    (
                        object_type,object_id,role,row["ean_upc"],
                        json.dumps({
                            "main_article_number":row["main_article_number"],
                            "sub_article_number":row["sub_article_number"],
                            "ean_upc":row["ean_upc"],
                            "description":row["description"],
                            "source_note":row["source_note"],
                        },ensure_ascii=False,default=str),
                    ),
                )
    return result



def ensure_cost_conversion_table(cur) -> None:
    if _table_exists(cur, 'manual_cost_selling_conversion'):
        return
    cur.execute(
        """
        CREATE TABLE manual_cost_selling_conversion (
            conversion_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            ean_upc VARCHAR(32) NOT NULL,
            selling_qty DECIMAL(24,12) NOT NULL,
            selling_uom_code VARCHAR(32) NOT NULL,
            cost_qty DECIMAL(24,12) NOT NULL,
            cost_uom_code VARCHAR(32) NOT NULL,
            conversion_status VARCHAR(24) NOT NULL DEFAULT 'CONFIRMED',
            source_note VARCHAR(512) NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                       ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (conversion_id),
            UNIQUE KEY uq_manual_cost_selling_conversion (ean_upc),
            KEY ix_manual_cost_selling_conversion_status (conversion_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def seed_confirmed_cost_conversions(cur) -> int:
    changed = 0
    for row in USER_CONFIRMED_COST_SELLING_CONVERSIONS_20260926:
        cur.execute(
            """
            INSERT INTO manual_cost_selling_conversion
              (ean_upc,selling_qty,selling_uom_code,cost_qty,cost_uom_code,
               conversion_status,source_note)
            VALUES (%s,%s,%s,%s,%s,'CONFIRMED',%s)
            ON DUPLICATE KEY UPDATE
              selling_qty=VALUES(selling_qty),
              selling_uom_code=VALUES(selling_uom_code),
              cost_qty=VALUES(cost_qty),
              cost_uom_code=VALUES(cost_uom_code),
              conversion_status='CONFIRMED',
              source_note=VALUES(source_note)
            """,
            (
                row["ean_upc"],
                row["selling_qty"],
                row["selling_uom_code"],
                row["cost_qty"],
                row["cost_uom_code"],
                row["source_note"],
            ),
        )
        changed += 1
    return changed


def apply_manual_cost_conversions(cur) -> dict[str, Any]:
    """Seed/refresh explicit cost-to-selling conversions without touching Base UOM."""
    seeded = seed_confirmed_cost_conversions(cur)
    cur.execute(
        """
        SELECT conversion_id,ean_upc,selling_qty,selling_uom_code,
               cost_qty,cost_uom_code,source_note
        FROM manual_cost_selling_conversion
        WHERE conversion_status='CONFIRMED'
        ORDER BY conversion_id
        """
    )
    rows = cur.fetchall()
    held = []
    verified = 0
    for row in rows:
        if (
            row.get("selling_qty") is None
            or Decimal(str(row["selling_qty"])) <= 0
            or row.get("cost_qty") is None
            or Decimal(str(row["cost_qty"])) <= 0
        ):
            held.append({"ean_upc": row["ean_upc"], "reason": "NONPOSITIVE_CONVERSION_QUANTITY"})
            continue
        if _uom_id(cur, row["selling_uom_code"]) is None:
            held.append({"ean_upc": row["ean_upc"], "reason": "SELLING_UOM_CODE_NOT_IN_DIM_UOM"})
            continue
        if _uom_id(cur, row["cost_uom_code"]) is None:
            held.append({"ean_upc": row["ean_upc"], "reason": "COST_UOM_CODE_NOT_IN_DIM_UOM"})
            continue
        verified += 1
    return {
        "seeded_or_refreshed": seeded,
        "conversions_examined": len(rows),
        "verified": verified,
        "held": held,
    }


def confirmed_cost_conversion(cur, ean_upc: str) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT ean_upc,selling_qty,selling_uom_code,cost_qty,cost_uom_code,
               source_note
        FROM manual_cost_selling_conversion
        WHERE ean_upc=%s
          AND conversion_status='CONFIRMED'
        LIMIT 1
        """,
        (str(ean_upc),),
    )
    return cur.fetchone()



def ensure_retirement_table(cur) -> None:
    if _table_exists(cur, 'manual_upc_retirement'):
        return
    cur.execute(
        """
        CREATE TABLE manual_upc_retirement (
            retirement_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            ean_upc VARCHAR(32) NOT NULL,
            retirement_reason VARCHAR(64) NOT NULL,
            retirement_status VARCHAR(24) NOT NULL DEFAULT 'CONFIRMED',
            source_note VARCHAR(512) NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                       ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (retirement_id),
            UNIQUE KEY uq_manual_upc_retirement (ean_upc),
            KEY ix_manual_upc_retirement_status (retirement_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def seed_confirmed_retirements(cur) -> int:
    ensure_retirement_table(cur)
    changed = 0
    for row in SEED_RETIREMENTS:
        cur.execute(
            """
            INSERT INTO manual_upc_retirement
              (ean_upc,retirement_reason,retirement_status,source_note)
            VALUES (%s,%s,'CONFIRMED',%s)
            ON DUPLICATE KEY UPDATE
              retirement_reason=VALUES(retirement_reason),
              retirement_status='CONFIRMED',
              source_note=VALUES(source_note)
            """,
            (row['ean_upc'], row['retirement_reason'], row['source_note']),
        )
        changed += 1
    return changed


def apply_manual_upc_retirements(cur) -> dict[str, Any]:
    """Final authority for UPCs that the user has confirmed do not exist.

    RAW/source evidence is intentionally preserved. Only the resolved/current layer
    is retired so automatic repair cannot publish the identifier again.
    """
    seeded = seed_confirmed_retirements(cur)
    cur.execute(
        """
        SELECT ean_upc,retirement_reason,source_note
        FROM manual_upc_retirement
        WHERE retirement_status='CONFIRMED'
        ORDER BY retirement_id
        """
    )
    rows = cur.fetchall()
    result = {
        'seeded_or_refreshed': seeded,
        'retirements_examined': len(rows),
        'upcs_retired': 0,
        'article_links_superseded': 0,
        'uom_rows_superseded': 0,
        'quick_check_rows_removed': 0,
    }
    for row in rows:
        ean = str(row['ean_upc']).strip()
        cur.execute("SELECT upc_id FROM selling_upc WHERE ean_upc=%s LIMIT 1", (ean,))
        hit = cur.fetchone()
        if not hit:
            # Keep the retirement seed even if a bad source identifier is not present
            # in this database yet. This makes future publishing fail closed.
            continue
        upc_id = int(hit['upc_id'])
        cur.execute("UPDATE selling_upc SET record_status='RETIRED' WHERE upc_id=%s", (upc_id,))
        result['upcs_retired'] += int(cur.rowcount or 0)

        cur.execute(
            """
            UPDATE bridge_article_upc
            SET mapping_status='SUPERSEDED',is_primary=FALSE,
                valid_to=COALESCE(valid_to,CURRENT_TIMESTAMP(6))
            WHERE upc_id=%s
              AND mapping_status='CONFIRMED'
              AND (valid_to IS NULL OR valid_to>CURRENT_TIMESTAMP(6))
            """,
            (upc_id,),
        )
        result['article_links_superseded'] += int(cur.rowcount or 0)

        cur.execute(
            """
            UPDATE selling_upc_uom_history
            SET mapping_status='SUPERSEDED',
                effective_to=COALESCE(effective_to,CURRENT_TIMESTAMP(6))
            WHERE upc_id=%s
              AND mapping_status='CONFIRMED'
              AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))
            """,
            (upc_id,),
        )
        result['uom_rows_superseded'] += int(cur.rowcount or 0)

        cur.execute("DELETE FROM quick_check_current WHERE upc_id=%s OR ean_upc=%s", (upc_id, ean))
        result['quick_check_rows_removed'] += int(cur.rowcount or 0)

        cur.execute(
            """
            SELECT evidence_id
            FROM normalized_source_evidence
            WHERE object_type='SELLING_UPC'
              AND object_id=%s
              AND evidence_role='USER_CONFIRMED_NONEXISTENT_UPC_V725'
            LIMIT 1
            """,
            (upc_id,),
        )
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO normalized_source_evidence
                  (object_type,object_id,evidence_role,source_field_name,source_value_text,evidence_json)
                VALUES ('SELLING_UPC',%s,'USER_CONFIRMED_NONEXISTENT_UPC_V725','ean_upc',%s,%s)
                """,
                (
                    upc_id,
                    ean,
                    json.dumps({
                        'retirement_reason': row['retirement_reason'],
                        'source_note': row['source_note'],
                        'raw_provenance_preserved': True,
                    }, ensure_ascii=False, default=str),
                ),
            )
    return result

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
        # Never infer Base/Inventory UOM from Selling UOM. A user confirmation of
        # PACK means the POS selling unit is PACK only. Base/cost conversion stays
        # unresolved unless separately confirmed by authoritative evidence.
        base_id = _uom_id(cur, ov["base_uom_code"]) if ov["base_uom_code"] else None
        factor = ov["base_qty_per_selling_unit"]
        if sell_id is None:
            result["held"].append({"ean_upc": ean, "reason": "SELLING_UOM_CODE_NOT_IN_DIM_UOM"})
            continue

        # A user-confirmed override is the final authority. Retire every
        # currently-confirmed UOM row first, then reactivate exactly one row
        # matching the authoritative tuple below. This is deliberately simpler
        # than SQL NOT/NULL comparisons, which can leave stale NULL variants
        # active because NOT UNKNOWN is still UNKNOWN in MySQL.
        cur.execute(
            """
            UPDATE selling_upc_uom_history
            SET mapping_status='SUPERSEDED',
                effective_to=COALESCE(effective_to,CURRENT_TIMESTAMP(6))
            WHERE upc_id=%s
              AND mapping_status='CONFIRMED'
              AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))
            """,
            (upc_id,),
        )

        cur.execute(
            """
            SELECT upc_uom_id
            FROM selling_upc_uom_history
            WHERE upc_id=%s
              AND selling_uom_id=%s
              AND ((base_uom_id IS NULL AND %s IS NULL) OR base_uom_id=%s)
              AND ((base_qty_per_selling_unit IS NULL AND %s IS NULL)
                   OR base_qty_per_selling_unit=%s)
            ORDER BY upc_uom_id DESC LIMIT 1
            """,
            (upc_id, sell_id, base_id, base_id, factor, factor),
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
                (base_id, factor, urow["upc_uom_id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO selling_upc_uom_history
                  (upc_id,selling_uom_id,base_uom_id,base_qty_per_selling_unit,
                   mapping_status,confidence,resolution_method)
                VALUES (%s,%s,%s,%s,'CONFIRMED',1.0,'USER_CONFIRMED_OVERRIDE')
                """,
                (upc_id, sell_id, base_id, factor),
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
