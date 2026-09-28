from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from data_coverage import source_data_days
from business_clock import completed_through_date
from coverage_backfill import canonical_pos_qty_by_upc
from manual_overrides import confirmed_family_cost, confirmed_receipt_entry_cost_basis

VERSION = "7.0.80-current-active-cost-lineage-repair"

RECEIPT_MOVEMENTS = {"101", "107", "109"}
OFFICIAL_COST_SOURCE_TYPES = {
    "FROZEN_INVENTORY_OFFICIAL_COST",
    "LIVE_FRESH_SUGGESTION_OFFICIAL_COST",
}
OH_FALLBACK_SOURCE_TYPE = "ON_HAND_EXPLICIT_COST_FALLBACK"


def _text(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _num(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return Decimal(str(v))
        except Exception:
            return None
    s = str(v).strip().replace(",", "").replace("$", "")
    if not s or s in {"-", "--"}:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _id(v: Any) -> str | None:
    s = _text(v)
    if not s:
        return None
    s = s.replace(",", "")
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".", 1)[0]
    return s if re.fullmatch(r"\d+", s) else None


def _numeric_key(v: str | None) -> str | None:
    if not v or not re.fullmatch(r"\d+", v):
        return None
    k = v.lstrip("0")
    return k or "0"


def _date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = _text(v)
    if not s:
        return None
    s2 = s.replace("-", "/").replace(".", "/")
    for fmt in (
        "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"
    ):
        try:
            return datetime.strptime(s2[:19], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


def _j(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if v is None:
        return {}
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8", errors="replace")
    try:
        return json.loads(v)
    except Exception:
        return {}


def _norm_header(v: Any) -> str:
    s = (_text(v) or "").upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    return {_norm_header(v): k for k, v in payload.items() if _norm_header(v)}


def _pick(hmap: dict[str, str], aliases: list[str]) -> str | None:
    norm_aliases = [_norm_header(x) for x in aliases]
    for a in norm_aliases:
        if a in hmap:
            return hmap[a]
    for h, c in hmap.items():
        if any(a and a in h for a in norm_aliases):
            return c
    return None


def _uom_id(cur, token: str | None) -> int | None:
    t = (_text(token) or "").upper()
    if not t:
        return None
    cur.execute(
        "SELECT uom_id FROM dim_uom WHERE UPPER(uom_code)=UPPER(%s) LIMIT 1",
        (t,),
    )
    r = cur.fetchone()
    return int(r["uom_id"]) if r else None


def _source_type_supported(cur, value: str) -> bool:
    """Avoid breaking an ENUM deployment when introducing the OH fallback label."""
    cur.execute(
        """SELECT DATA_TYPE,COLUMN_TYPE
           FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA=DATABASE()
             AND TABLE_NAME='article_cost_observation'
             AND COLUMN_NAME='source_type'
           LIMIT 1"""
    )
    row = cur.fetchone()
    if not row:
        return False
    data_type = str(row.get("DATA_TYPE") or "").lower()
    column_type = str(row.get("COLUMN_TYPE") or "")
    if data_type != "enum":
        return True
    vals = set(re.findall(r"'((?:[^']|'')*)'", column_type))
    return value in vals


def _active_products(cur, batch_id: int) -> tuple[list[dict[str, Any]], int, str | None]:
    completed_through = completed_through_date()
    days = source_data_days(
        cur,
        "sales_by_price_type",
        limit=28,
        include_batch_id=batch_id,
        up_to=completed_through,
    )
    qty_by_upc = canonical_pos_qty_by_upc(cur, days)
    active_ids = sorted(
        upc_id for upc_id, qty in qty_by_upc.items()
        if Decimal(str(qty or 0)) > 0
    )
    latest = max((x["date"] for x in days), default=None)
    if not active_ids:
        return [], len(days), latest.isoformat() if latest else None

    placeholders = ",".join(["%s"] * len(active_ids))
    cur.execute(
        f"""SELECT su.upc_id,su.ean_upc,su.selling_description,
                   pf.family_id,pf.main_article_number,pf.family_description,
                   bau.article_id,a.article_number
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
            WHERE su.upc_id IN ({placeholders})
            ORDER BY su.upc_id""",
        tuple(active_ids),
    )
    rows = cur.fetchall()
    for row in rows:
        row["recent_qty"] = qty_by_upc.get(int(row["upc_id"]), Decimal("0"))
    return rows, len(days), latest.isoformat() if latest else None


def _best_cost(cur, family_id: int) -> dict[str, Any] | None:
    # 1) Receipt valuation authority.
    cur.execute(
        """SELECT co.cost_observation_id,co.cost_per_base_uom,co.cost_amount,
                  co.business_date,co.source_type,co.movement_type,
                  bu.uom_code AS base_uom,cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s
             AND co.source_type='MOVEMENT_RECEIPT_VALUATION'
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
           ORDER BY co.business_date DESC,co.cost_observation_id DESC
           LIMIT 1""",
        (family_id,),
    )
    row = cur.fetchone()
    if row:
        return {
            "source": row["source_type"],
            "date": row["business_date"],
            "uom": row["base_uom"] or row["cost_uom"],
            "amount": row["cost_per_base_uom"] or row["cost_amount"],
            "movement_type": row.get("movement_type"),
        }

    # 2) Live/Fresh/Frozen official report cost.
    placeholders = ",".join(["%s"] * len(OFFICIAL_COST_SOURCE_TYPES))
    cur.execute(
        f"""SELECT co.cost_observation_id,co.cost_amount,co.business_date,
                   co.source_type,cu.uom_code AS cost_uom
            FROM article_cost_observation co
            LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
            WHERE co.family_id=%s
              AND co.source_type IN ({placeholders})
              AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
              AND co.cost_amount>0
            ORDER BY co.business_date DESC,co.cost_observation_id DESC
            LIMIT 1""",
        (family_id, *sorted(OFFICIAL_COST_SOURCE_TYPES)),
    )
    row = cur.fetchone()
    if row:
        return {
            "source": row["source_type"],
            "date": row["business_date"],
            "uom": row["cost_uom"],
            "amount": row["cost_amount"],
        }

    # 3) Explicit OH cost fallback only.
    cur.execute(
        """SELECT co.cost_observation_id,co.cost_amount,co.business_date,
                  co.source_type,cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s
             AND co.source_type=%s
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND co.cost_amount>0
           ORDER BY co.business_date DESC,co.cost_observation_id DESC
           LIMIT 1""",
        (family_id, OH_FALLBACK_SOURCE_TYPE),
    )
    row = cur.fetchone()
    if row:
        return {
            "source": row["source_type"],
            "date": row["business_date"],
            "uom": row["cost_uom"],
            "amount": row["cost_amount"],
        }

    # 4) Explicit user-confirmed Family/Main-Article fallback.
    manual = confirmed_family_cost(cur, family_id)
    if manual:
        return {
            "source": "USER_CONFIRMED_FAMILY_COST",
            "date": manual.get("confirmed_date"),
            "uom": manual["cost_uom_code"],
            "amount": manual["cost_amount"],
        }

    return None


def _main_article_id(cur, family_id: int) -> int | None:
    cur.execute(
        """SELECT a.article_id
           FROM product_family pf
           JOIN article a ON a.article_number=pf.main_article_number
           WHERE pf.family_id=%s
           LIMIT 1""",
        (family_id,),
    )
    row = cur.fetchone()
    return int(row["article_id"]) if row else None


def _article_family(cur, article_number: str | None) -> tuple[int | None, int | None]:
    if not article_number:
        return None, None
    cur.execute(
        """SELECT a.article_id,baf.family_id
           FROM article a
           LEFT JOIN bridge_article_family baf
             ON baf.article_id=a.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE a.article_number=%s
           LIMIT 1""",
        (article_number,),
    )
    row = cur.fetchone()
    if not row:
        return None, None
    return int(row["article_id"]), int(row["family_id"]) if row.get("family_id") is not None else None


def _upc_family(cur, ean: str | None) -> tuple[int | None, int | None, int | None]:
    if not ean:
        return None, None, None
    key = _numeric_key(ean)
    cur.execute(
        """SELECT su.upc_id,bau.article_id,baf.family_id
           FROM selling_upc su
           JOIN bridge_article_upc bau
             ON bau.upc_id=su.upc_id
            AND bau.mapping_status='CONFIRMED'
            AND bau.is_primary=TRUE
            AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           JOIN bridge_article_family baf
             ON baf.article_id=bau.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE su.ean_upc=%s
              OR (su.ean_upc REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM su.ean_upc)=%s)
           ORDER BY CASE WHEN su.ean_upc=%s THEN 0 ELSE 1 END,su.upc_id
           LIMIT 1""",
        (ean, key or ean, ean),
    )
    row = cur.fetchone()
    if not row:
        return None, None, None
    return int(row["upc_id"]), int(row["article_id"]), int(row["family_id"])


def _relink_target_company_rows(cur, target_family_ids: list[int]) -> dict[str, int]:
    if not target_family_ids:
        return {
            "from_existing_article_id": 0,
            "from_upc": 0,
            "from_article": 0,
        }
    ph = ",".join(["%s"] * len(target_family_ids))

    # v7.0.38: the v7.0.36 global diagnostic deliberately treats an existing
    # confirmed Article identity as Family-authoritative evidence even when the
    # company row's family_id is NULL/stale. The repair path must use that same
    # identity. Otherwise a row can be classified SAFE by article_id but remain
    # invisible to _backfill_official_cost(), which filters by family_id.
    cur.execute(
        f"""UPDATE company_price_observation c
            JOIN bridge_article_family baf
              ON baf.article_id=c.article_id
             AND baf.mapping_status='CONFIRMED'
             AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
            SET c.family_id=baf.family_id
            WHERE c.article_id IS NOT NULL
              AND baf.family_id IN ({ph})
              AND (c.family_id IS NULL OR c.family_id<>baf.family_id)""",
        tuple(target_family_ids),
    )
    from_existing_article_id = int(cur.rowcount)

    # Exact current UPC identity can restore family/article on company rows.
    cur.execute(
        f"""UPDATE company_price_observation c
            JOIN bridge_article_upc bau
              ON bau.upc_id=c.upc_id
             AND bau.mapping_status='CONFIRMED'
             AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
            JOIN bridge_article_family baf
              ON baf.article_id=bau.article_id
             AND baf.mapping_status='CONFIRMED'
             AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
            SET c.article_id=COALESCE(c.article_id,bau.article_id),
                c.family_id=baf.family_id
            WHERE c.upc_id IS NOT NULL
              AND baf.family_id IN ({ph})
              AND (c.family_id IS NULL OR c.family_id<>baf.family_id OR c.article_id IS NULL)""",
        tuple(target_family_ids),
    )
    from_upc = int(cur.rowcount)

    # Exact Article identity can do the same.
    cur.execute(
        f"""UPDATE company_price_observation c
            JOIN article a ON a.article_number=c.article_number
            JOIN bridge_article_family baf
              ON baf.article_id=a.article_id
             AND baf.mapping_status='CONFIRMED'
             AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
            SET c.article_id=a.article_id,
                c.family_id=baf.family_id
            WHERE c.article_number IS NOT NULL
              AND baf.family_id IN ({ph})
              AND (c.family_id IS NULL OR c.family_id<>baf.family_id OR c.article_id IS NULL)""",
        tuple(target_family_ids),
    )
    from_article = int(cur.rowcount)

    return {
        "from_existing_article_id": from_existing_article_id,
        "from_upc": from_upc,
        "from_article": from_article,
    }



def _relink_existing_cost_observations(cur, target_family_ids: list[int]) -> dict[str, int]:
    """Repair DERIVED cost lineage after identity/family links became authoritative.

    RAW is never changed.

    This fixes the v7.0.19 failure mode where an article_cost_observation already
    existed for the same raw row with family_id NULL/stale. Because the raw row
    already existed, the later INSERT ... NOT EXISTS correctly refused to
    duplicate it, but _best_cost could not see it by Family.
    """
    if not target_family_ids:
        return {
            "from_article_identity": 0,
            "from_official_raw_lineage": 0,
            "from_movement_raw_lineage": 0,
        }

    ph = ",".join(["%s"] * len(target_family_ids))

    # A) Existing cost observation already has Article identity.
    cur.execute(
        f"""UPDATE article_cost_observation co
            JOIN bridge_article_family baf
              ON baf.article_id=co.article_id
             AND baf.mapping_status='CONFIRMED'
             AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
            SET co.family_id=baf.family_id
            WHERE baf.family_id IN ({ph})
              AND (co.family_id IS NULL OR co.family_id<>baf.family_id)""",
        tuple(target_family_ids),
    )
    from_article = int(cur.rowcount)

    # B) Existing official-report cost observation can be repaired from its
    # exact RAW lineage + the now-linked company_price_observation row.
    cur.execute(
        f"""UPDATE article_cost_observation co
            JOIN company_price_observation c
              ON c.raw_id=co.raw_id
             AND co.raw_table_name=
                 CASE c.source_type
                   WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                   WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                   ELSE '__NO_MATCH__'
                 END
            JOIN product_family pf ON pf.family_id=c.family_id
            JOIN article ma ON ma.article_number=pf.main_article_number
            SET co.family_id=c.family_id,
                co.article_id=ma.article_id
            WHERE c.family_id IN ({ph})
              AND c.source_type IN ('frozen_inventory','live_fresh_suggestion')
              AND (
                  co.family_id IS NULL
                  OR co.family_id<>c.family_id
                  OR co.article_id<>ma.article_id
              )""",
        tuple(target_family_ids),
    )
    from_official = int(cur.rowcount)

    # C) Existing receipt-derived cost observation can be repaired from the
    # exact raw_movement lineage after movement_history was relinked.
    cur.execute(
        f"""UPDATE article_cost_observation co
            JOIN movement_history m
              ON co.raw_table_name='raw_movement'
             AND co.raw_id=m.raw_id
            SET co.family_id=m.family_id,
                co.article_id=COALESCE(co.article_id,m.article_id)
            WHERE m.family_id IN ({ph})
              AND m.article_id IS NOT NULL
              AND m.movement_type IN ('101','107','109')
              AND (co.family_id IS NULL OR co.family_id<>m.family_id OR co.article_id IS NULL)""",
        tuple(target_family_ids),
    )
    from_movement = int(cur.rowcount)

    return {
        "from_article_identity": from_article,
        "from_official_raw_lineage": from_official,
        "from_movement_raw_lineage": from_movement,
    }


def _backfill_receipt_cost(cur, target_family_ids: list[int]) -> int:
    if not target_family_ids:
        return 0
    ph = ",".join(["%s"] * len(target_family_ids))
    cur.execute(
        f"""INSERT INTO article_cost_observation
            (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,movement_type,
             business_date,observed_at,cost_status,confidence,base_uom_id,cost_per_base_uom,
             batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
            SELECT m.article_id,m.family_id,
                   ABS(m.amount_local_currency/m.base_quantity),'USD',bu.uom_id,
                   'MOVEMENT_RECEIPT_VALUATION',m.movement_type,m.posting_date,
                   TIMESTAMP(m.posting_date),'OBSERVED',1.0,bu.uom_id,
                   ABS(m.amount_local_currency/m.base_quantity),
                   m.batch_id,m.file_id,m.sheet_id,'raw_movement',m.raw_id,m.source_row_number
            FROM movement_history m
            JOIN dim_uom bu ON UPPER(bu.uom_code)=UPPER(m.base_uom_code)
            WHERE m.family_id IN ({ph})
              AND m.article_id IS NOT NULL
              AND m.movement_type IN ('101','107','109')
              AND m.amount_local_currency IS NOT NULL
              AND m.amount_local_currency<>0
              AND m.base_quantity IS NOT NULL
              AND m.base_quantity<>0
              AND NOT EXISTS (
                SELECT 1 FROM article_cost_observation c
                WHERE c.raw_table_name='raw_movement'
                  AND c.raw_id=m.raw_id
              )""",
        tuple(target_family_ids),
    )
    inserted = int(cur.rowcount)

    # If the business explicitly confirms that Entry UOM is the true
    # receiving/cost basis for a family, repair DERIVED receipt-cost rows from
    # amount / entry_quantity. RAW movement_history remains untouched.
    for family_id in target_family_ids:
        basis = confirmed_receipt_entry_cost_basis(cur, family_id)
        if not basis:
            continue
        entry_uom_code = str(basis.get("entry_uom_code") or "").strip().upper()
        if not entry_uom_code:
            continue
        cur.execute(
            """UPDATE article_cost_observation co
               JOIN movement_history m
                 ON co.raw_table_name='raw_movement'
                AND co.raw_id=m.raw_id
               JOIN dim_uom eu
                 ON UPPER(eu.uom_code)=UPPER(m.entry_uom_code)
               SET co.cost_amount=ABS(m.amount_local_currency/m.entry_quantity),
                   co.cost_uom_id=eu.uom_id,
                   co.base_uom_id=eu.uom_id,
                   co.cost_per_base_uom=ABS(m.amount_local_currency/m.entry_quantity),
                   co.cost_status='OBSERVED',
                   co.confidence=1.0
               WHERE co.family_id=%s
                 AND co.source_type='MOVEMENT_RECEIPT_VALUATION'
                 AND m.movement_type IN ('101','107','109')
                 AND UPPER(m.entry_uom_code)=UPPER(%s)
                 AND m.entry_quantity IS NOT NULL
                 AND m.entry_quantity<>0
                 AND m.amount_local_currency IS NOT NULL
                 AND m.amount_local_currency<>0""",
            (int(family_id), entry_uom_code),
        )

    return inserted


def _backfill_official_cost(cur, target_family_ids: list[int]) -> int:
    if not target_family_ids:
        return 0
    ph = ",".join(["%s"] * len(target_family_ids))

    # Company report rows can be family-authoritative even if the source row
    # supplied Main Article but not a separate receiving Article. In that case
    # anchor the derived cost observation to the family's Main Article.
    cur.execute(
        f"""INSERT INTO article_cost_observation
            (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,business_date,
             cost_status,confidence,batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
            SELECT ma.article_id,c.family_id,c.official_cost,'USD',du.uom_id,
                   CONCAT(UPPER(c.source_type),'_OFFICIAL_COST'),c.observation_date,
                   'OBSERVED',1.0,c.batch_id,c.file_id,c.sheet_id,
                   CASE c.source_type
                     WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                     WHEN 'tx_seafood_abc_price' THEN 'raw_tx_seafood_abc_price'
                     WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                     ELSE NULL
                   END,
                   c.raw_id,c.source_row_number
            FROM company_price_observation c
            JOIN product_family pf ON pf.family_id=c.family_id
            JOIN article ma ON ma.article_number=pf.main_article_number
            JOIN dim_uom du ON UPPER(du.uom_code)=UPPER(c.cost_uom_code)
            WHERE c.family_id IN ({ph})
              AND c.source_type IN ('frozen_inventory','live_fresh_suggestion')
              AND c.official_cost IS NOT NULL
              AND c.official_cost>0
              AND c.cost_uom_code IS NOT NULL
              AND ma.article_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM article_cost_observation aco
                WHERE aco.raw_id=c.raw_id
                  AND aco.raw_table_name=
                    CASE c.source_type
                      WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                      WHEN 'tx_seafood_abc_price' THEN 'raw_tx_seafood_abc_price'
                      WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                    END
              )""",
        tuple(target_family_ids),
    )
    return int(cur.rowcount)


def _scan_and_backfill_oh_cost(
    cur,
    target_family_ids: list[int],
) -> dict[str, Any]:
    result = {
        "source_type_supported": _source_type_supported(cur, OH_FALLBACK_SOURCE_TYPE),
        "files_scanned": 0,
        "sheets_scanned": 0,
        "rows_scanned": 0,
        "positive_cost_candidates": 0,
        "candidates_missing_explicit_cost_uom": 0,
        "candidates_unsupported_cost_uom": 0,
        "family_conflicts": 0,
        "rows_backfilled": 0,
        "candidate_counts_by_family": defaultdict(lambda: {
            "positive": 0,
            "explicit_supported_uom": 0,
            "missing_uom": 0,
            "unsupported_uom": 0,
        }),
    }
    targets = set(int(x) for x in target_family_ids)
    if not targets:
        result["candidate_counts_by_family"] = {}
        return result

    cur.execute(
        """SELECT file_id,coverage_end_date,filename_date_candidate,upload_timestamp
           FROM ingest_file
           WHERE source_type='on_hand'
           ORDER BY file_id"""
    )
    files = cur.fetchall()
    result["files_scanned"] = len(files)

    for f in files:
        cur.execute(
            """SELECT sheet_id,header_row_number
               FROM ingest_sheet
               WHERE file_id=%s
               ORDER BY sheet_index""",
            (f["file_id"],),
        )
        for sh in cur.fetchall():
            header_row = sh.get("header_row_number")
            if not header_row:
                continue
            cur.execute(
                """SELECT raw_payload
                   FROM raw_on_hand
                   WHERE sheet_id=%s AND source_row_number=%s
                   LIMIT 1""",
                (sh["sheet_id"], header_row),
            )
            hr = cur.fetchone()
            if not hr:
                continue
            hmap = _header_map(_j(hr["raw_payload"]))

            c_article = _pick(hmap, ["Article", "Article Number", "Material", "Material Number"])
            c_upc = _pick(hmap, ["UPC", "EAN", "Barcode", "Sales Set"])
            c_cost = _pick(
                hmap,
                [
                    "Cost", "Unit Cost", "Current Cost", "Average Cost", "Avg Cost",
                    "Moving Average Price", "Moving Price", "MAP",
                ],
            )
            # Deliberately require a cost-specific UOM field. Generic inventory
            # UOM is NOT silently assumed to be cost UOM.
            c_cost_uom = _pick(
                hmap,
                ["Cost UOM", "Cost Unit", "Price UOM", "Price Unit", "Cost Base UOM"],
            )
            c_date = _pick(hmap, ["Date", "Inventory Date", "Count Date", "Snapshot Date"])

            if not c_cost or (not c_article and not c_upc):
                continue

            result["sheets_scanned"] += 1
            cur.execute(
                """SELECT raw_id,source_row_number,raw_payload
                   FROM raw_on_hand
                   WHERE sheet_id=%s AND source_row_number>%s
                   ORDER BY source_row_number""",
                (sh["sheet_id"], header_row),
            )
            for rr in cur.fetchall():
                result["rows_scanned"] += 1
                p = _j(rr["raw_payload"])
                cost = _num(p.get(c_cost))
                if cost is None or cost <= 0:
                    continue

                article_num = _id(p.get(c_article)) if c_article else None
                ean = _id(p.get(c_upc)) if c_upc else None
                article_id, article_family = _article_family(cur, article_num)
                _, upc_article_id, upc_family = _upc_family(cur, ean)

                family_candidates = {x for x in (article_family, upc_family) if x is not None}
                if len(family_candidates) > 1:
                    result["family_conflicts"] += 1
                    continue
                if not family_candidates:
                    continue

                family_id = next(iter(family_candidates))
                if family_id not in targets:
                    continue

                result["positive_cost_candidates"] += 1
                fam_stats = result["candidate_counts_by_family"][family_id]
                fam_stats["positive"] += 1

                cost_uom = (_text(p.get(c_cost_uom)) or "").upper() if c_cost_uom else ""
                if not cost_uom:
                    result["candidates_missing_explicit_cost_uom"] += 1
                    fam_stats["missing_uom"] += 1
                    continue

                uid = _uom_id(cur, cost_uom)
                if uid is None:
                    result["candidates_unsupported_cost_uom"] += 1
                    fam_stats["unsupported_uom"] += 1
                    continue

                fam_stats["explicit_supported_uom"] += 1
                if not result["source_type_supported"]:
                    continue

                anchor_article_id = article_id or upc_article_id or _main_article_id(cur, family_id)
                if anchor_article_id is None:
                    continue

                obs_date = (
                    _date(p.get(c_date)) if c_date else None
                ) or f.get("coverage_end_date") or f.get("filename_date_candidate")
                if obs_date is None and f.get("upload_timestamp"):
                    obs_date = f["upload_timestamp"].date()

                cur.execute(
                    """SELECT cost_observation_id
                       FROM article_cost_observation
                       WHERE raw_table_name='raw_on_hand' AND raw_id=%s
                       LIMIT 1""",
                    (rr["raw_id"],),
                )
                if cur.fetchone():
                    continue

                cur.execute(
                    """INSERT INTO article_cost_observation
                       (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,
                        business_date,cost_status,confidence,batch_id,file_id,sheet_id,
                        raw_table_name,raw_id,source_row_number)
                       VALUES (%s,%s,%s,'USD',%s,%s,%s,'OBSERVED',1.0,%s,%s,%s,
                               'raw_on_hand',%s,%s)""",
                    (
                        anchor_article_id, family_id, cost, uid, OH_FALLBACK_SOURCE_TYPE,
                        obs_date, None, f["file_id"], sh["sheet_id"],
                        rr["raw_id"], rr["source_row_number"],
                    ),
                )
                result["rows_backfilled"] += 1

    result["candidate_counts_by_family"] = {
        str(k): dict(v) for k, v in result["candidate_counts_by_family"].items()
    }
    return result


def _family_diagnostics(
    cur,
    family_id: int,
    oh_stats: dict[str, Any],
) -> dict[str, Any]:
    cur.execute(
        """SELECT COUNT(*) AS receipt_rows,
                  SUM(CASE WHEN amount_local_currency IS NOT NULL
                                AND amount_local_currency<>0
                                AND base_quantity IS NOT NULL
                                AND base_quantity<>0
                                AND base_uom_code IS NOT NULL
                           THEN 1 ELSE 0 END) AS valid_receipt_rows,
                  MAX(posting_date) AS latest_receipt_date
           FROM movement_history
           WHERE family_id=%s AND movement_type IN ('101','107','109')""",
        (family_id,),
    )
    receipt = cur.fetchone() or {}

    cur.execute(
        """SELECT COUNT(*) AS official_rows,
                  SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0 THEN 1 ELSE 0 END) AS positive_cost_rows,
                  SUM(CASE WHEN official_cost IS NOT NULL AND official_cost>0
                                AND cost_uom_code IS NOT NULL
                           THEN 1 ELSE 0 END) AS positive_with_uom_rows,
                  MAX(observation_date) AS latest_official_date
           FROM company_price_observation
           WHERE family_id=%s
             AND source_type IN ('frozen_inventory','live_fresh_suggestion')""",
        (family_id,),
    )
    official = cur.fetchone() or {}

    oh = (oh_stats.get("candidate_counts_by_family") or {}).get(str(family_id), {})
    receipt_rows = int(receipt.get("receipt_rows") or 0)
    valid_receipt_rows = int(receipt.get("valid_receipt_rows") or 0)
    positive_official = int(official.get("positive_cost_rows") or 0)
    positive_official_uom = int(official.get("positive_with_uom_rows") or 0)
    oh_positive = int(oh.get("positive") or 0)
    oh_supported = int(oh.get("explicit_supported_uom") or 0)

    if receipt_rows > 0 and valid_receipt_rows == 0:
        reason = "RECEIPT_ROWS_WITHOUT_VALID_VALUATION"
    elif positive_official > 0 and positive_official_uom == 0:
        reason = "OFFICIAL_COST_WITHOUT_EXPLICIT_UOM"
    elif oh_positive > 0 and oh_supported == 0:
        reason = "OH_COST_WITHOUT_EXPLICIT_SUPPORTED_UOM"
    elif receipt_rows == 0 and positive_official == 0 and oh_positive == 0:
        reason = "NO_RECEIVING_HISTORY_OR_AUTHORITATIVE_REPORT_COST"
    else:
        reason = "NO_AUTHORITATIVE_COST_EVIDENCE"

    return {
        "reason": reason,
        "receipt_rows": receipt_rows,
        "valid_receipt_rows": valid_receipt_rows,
        "latest_receipt_date": receipt.get("latest_receipt_date"),
        "official_rows": int(official.get("official_rows") or 0),
        "positive_official_cost_rows": positive_official,
        "positive_official_with_uom_rows": positive_official_uom,
        "latest_official_date": official.get("latest_official_date"),
        "oh_positive_cost_candidates": oh_positive,
        "oh_explicit_supported_uom_candidates": oh_supported,
        "oh_missing_uom_candidates": int(oh.get("missing_uom") or 0),
        "oh_unsupported_uom_candidates": int(oh.get("unsupported_uom") or 0),
    }


def repair_current_active_cost(cur, batch_id: int) -> dict[str, Any]:
    active, valid_day_count, latest_valid_date = _active_products(cur, batch_id)

    initial_missing = []
    target_families = set()
    for p in active:
        if _best_cost(cur, int(p["family_id"])) is None:
            initial_missing.append(p)
            target_families.add(int(p["family_id"]))

    target_family_ids = sorted(target_families)
    result: dict[str, Any] = {
        "version": VERSION,
        "scope": {
            "activity_rule": "POS_POSITIVE_LATEST_UP_TO_28_VALID_COMPLETED_DATA_DAYS",
            "valid_pos_day_count": valid_day_count,
            "latest_valid_pos_date": latest_valid_date,
            "historical_upcs_touched": 0,
        },
        "active_upcs_examined": len(active),
        "initial_missing_cost_upcs": len(initial_missing),
        "initial_missing_cost_families": len(target_family_ids),
        "company_rows_relinked": {},
        "existing_cost_observations_relinked": {},
        "receipt_cost_rows_backfilled": 0,
        "official_cost_rows_backfilled": 0,
        "oh_fallback": {},
        "resolved_cost_upcs": 0,
        "remaining_missing_cost_upcs": 0,
        "remaining_missing_cost_families": 0,
        "resolved": [],
        "remaining": [],
    }

    if not target_family_ids:
        return result

    result["company_rows_relinked"] = _relink_target_company_rows(cur, target_family_ids)

    # Critical v7.0.20 repair: fix already-existing derived cost rows BEFORE
    # attempting new inserts. This preserves one-row-per-RAW lineage and makes
    # existing official/receipt costs visible to Family-authoritative lookup.
    result["existing_cost_observations_relinked"] = _relink_existing_cost_observations(
        cur, target_family_ids
    )

    result["receipt_cost_rows_backfilled"] = _backfill_receipt_cost(cur, target_family_ids)
    result["official_cost_rows_backfilled"] = _backfill_official_cost(cur, target_family_ids)
    result["oh_fallback"] = _scan_and_backfill_oh_cost(cur, target_family_ids)

    remaining_families = set()
    for p in initial_missing:
        family_id = int(p["family_id"])
        cost = _best_cost(cur, family_id)
        item = {
            "upc": str(p["ean_upc"]),
            "description": p.get("selling_description"),
            "family_id": family_id,
            "main_article_number": str(p.get("main_article_number") or ""),
            "family_description": p.get("family_description"),
            "recent_pos_qty_28_valid_days": str(p.get("recent_qty") or 0),
        }
        if cost is not None:
            item["resolved_cost"] = cost
            result["resolved"].append(item)
        else:
            remaining_families.add(family_id)
            item["diagnostics"] = _family_diagnostics(
                cur, family_id, result["oh_fallback"]
            )
            result["remaining"].append(item)

    result["resolved_cost_upcs"] = len(result["resolved"])
    result["remaining_missing_cost_upcs"] = len(result["remaining"])
    result["remaining_missing_cost_families"] = len(remaining_families)
    return result
