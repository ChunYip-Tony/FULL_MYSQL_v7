from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from active_product_repair import _insert_uom_mapping
from article_manual_multitab_repair import (
    _digits_identifier,
    _has_current_uom,
    _latest_article_manual_files,
)
from data_coverage import source_data_days
from coverage_backfill import canonical_pos_qty_by_upc
from normalize import (
    RowContext,
    _build_column_map,
    _get,
    _json_obj,
    _numeric_identifier,
    _numeric_key,
    _source_token,
)

VERSION = "7.0.175-active-28d-uom-repair"

# Latest user-confirmed FULL MYSQL Seafood Selling-UOM authority.
# Applies only to CURRENT-ACTIVE Seafood UPCs. Historical rows remain untouched.
# Prefix ranges:
#   230-239, 240, 242, 245, 247, 249, 250-259, 260-269 => LB
# Non-prefix UPCs still require explicit Article Manual/user authority.
def _authoritative_seafood_lb_prefix(upc: str) -> bool:
    s = re.sub(r"\D", "", str(upc or ""))
    if len(s) < 3:
        return False
    try:
        p = int(s[:3])
    except Exception:
        return False
    return (
        230 <= p <= 239
        or p in {240, 242, 245, 247, 249}
        or 250 <= p <= 259
        or 260 <= p <= 269
    )


def _is_current_seafood_upc(cur, upc_id: int) -> bool:
    cur.execute(
        """SELECT 1
           FROM upc_department_observation
           WHERE upc_id=%s
             AND source_type='POS'
             AND department_code='400'
           ORDER BY business_date DESC,file_id DESC,source_row_number DESC
           LIMIT 1""",
        (upc_id,),
    )
    return bool(cur.fetchone())

# Structured Article Manual article-level unit declarations considered safe.
# PAC is intentionally NOT treated as PACK.
PURE_ARTICLE_UOMS = {"LB", "EA", "PACK"}


def _active_selling_upcs(cur, batch_id: int) -> tuple[list[dict[str, Any]], int, str | None]:
    completed_through = date.today() - timedelta(days=1)
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
    if not active_ids:
        return [], len(days), (max((x["date"] for x in days), default=None).isoformat() if days else None)

    placeholders = ",".join(["%s"] * len(active_ids))
    cur.execute(
        f"""SELECT su.upc_id,su.ean_upc,su.selling_description,
                   pf.family_id,pf.main_article_number
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
            JOIN product_family pf ON pf.family_id=baf.family_id
            WHERE su.upc_id IN ({placeholders})
            ORDER BY su.upc_id""",
        tuple(active_ids),
    )
    rows = cur.fetchall()
    for row in rows:
        row["recent_qty"] = qty_by_upc.get(int(row["upc_id"]), Decimal("0"))
    latest = max((x["date"] for x in days), default=None)
    return rows, len(days), latest.isoformat() if latest else None


def _uom_by_code(cur, code: str) -> dict[str, Any] | None:
    cur.execute(
        """SELECT uom_id,uom_code,uom_dimension
           FROM dim_uom
           WHERE UPPER(uom_code)=UPPER(%s)
           LIMIT 1""",
        (code,),
    )
    return cur.fetchone()


def _historical_uom_conflict(cur, upc_id: int, desired_code: str) -> dict[str, Any] | None:
    """Do not silently overwrite a prior non-matching configured UOM."""
    cur.execute(
        """SELECT DISTINCT UPPER(du.uom_code) AS uom_code
           FROM selling_upc_uom_history h
           JOIN dim_uom du ON du.uom_id=h.selling_uom_id
           WHERE h.upc_id=%s
             AND h.selling_uom_id IS NOT NULL""",
        (upc_id,),
    )
    codes = sorted({str(r["uom_code"]).upper() for r in cur.fetchall() if r.get("uom_code")})
    conflicting = [x for x in codes if x != desired_code.upper()]
    if conflicting:
        return {"desired": desired_code.upper(), "historical_codes": codes}
    return None


def _apply_uom(cur, upc_id: int, code: str, method: str) -> bool:
    uom = _uom_by_code(cur, code)
    if not uom:
        return False
    sell_id = int(uom["uom_id"])
    dimension = str(uom.get("uom_dimension") or "").upper()
    base_id = sell_id if dimension in {"WEIGHT", "COUNT"} else None
    factor = Decimal("1") if base_id is not None else None
    _insert_uom_mapping(cur, upc_id, sell_id, base_id, factor, method)
    return True


def _latest_article_manual_source(cur, preferred_batch_id: int | None = 7) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, set[str]],
    dict[str, Any],
]:
    """Build:
    - exact/numeric-equivalent UPC -> Article Manual source rows
    - Article -> unique pure Size/dimensions unit declarations
    """
    files = _latest_article_manual_files(cur, preferred_batch_id)
    upc_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    article_units: dict[str, set[str]] = defaultdict(set)
    stats = {
        "files": [r["original_filename"] for r in files],
        "sheets_scanned": 0,
        "rows_scanned": 0,
        "pure_article_unit_rows": 0,
        "upc_rows": 0,
    }

    for f in files:
        cur.execute(
            """SELECT sheet_id,sheet_name,header_row_number,sheet_index
               FROM ingest_sheet
               WHERE file_id=%s
               ORDER BY sheet_index""",
            (f["file_id"],),
        )
        for sh in cur.fetchall():
            if not sh.get("header_row_number"):
                continue
            cur.execute(
                """SELECT raw_id,raw_payload
                   FROM raw_article_manual
                   WHERE sheet_id=%s AND source_row_number=%s
                   LIMIT 1""",
                (sh["sheet_id"], sh["header_row_number"]),
            )
            h = cur.fetchone()
            if not h:
                continue
            colmap = _build_column_map(_json_obj(h["raw_payload"]))
            if "pack" not in colmap:
                continue
            if "article" not in colmap and "main_article" not in colmap:
                continue

            stats["sheets_scanned"] += 1
            cur.execute(
                """SELECT raw_id,source_row_number,raw_payload
                   FROM raw_article_manual
                   WHERE sheet_id=%s AND source_row_number>%s
                   ORDER BY source_row_number""",
                (sh["sheet_id"], sh["header_row_number"]),
            )
            for rr in cur.fetchall():
                stats["rows_scanned"] += 1
                payload = _json_obj(rr["raw_payload"])
                article = (
                    _numeric_identifier(_get(payload, colmap, "article"))
                    or _numeric_identifier(_get(payload, colmap, "main_article"))
                )
                if not article:
                    continue

                pack = _source_token(_get(payload, colmap, "pack"))
                pack_token = re.sub(r"\s+", "", str(pack or "").upper())
                if pack_token in PURE_ARTICLE_UOMS:
                    article_units[article].add(pack_token)
                    stats["pure_article_unit_rows"] += 1

                source_upc = _digits_identifier(_get(payload, colmap, "upc"))
                if source_upc:
                    key = _numeric_key(source_upc)
                    if key:
                        upc_rows[key].append({
                            "article": article,
                            "source_upc": source_upc,
                            "sheet_name": str(sh["sheet_name"]),
                            "batch_id": int(f["batch_id"]),
                            "file_id": int(f["file_id"]),
                            "sheet_id": int(sh["sheet_id"]),
                            "raw_id": int(rr["raw_id"]),
                            "source_row_number": int(rr["source_row_number"]),
                        })
                        stats["upc_rows"] += 1

    return upc_rows, article_units, stats


def _article_is_in_family(cur, article_number: str, family_id: int) -> bool:
    cur.execute(
        """SELECT 1
           FROM article a
           JOIN bridge_article_family baf
             ON baf.article_id=a.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE a.article_number=%s
             AND baf.family_id=%s
           LIMIT 1""",
        (article_number, family_id),
    )
    return bool(cur.fetchone())


def _safe_article_manual_unit(
    cur,
    target: dict[str, Any],
    upc_rows: dict[str, list[dict[str, Any]]],
    article_units: dict[str, set[str]],
) -> dict[str, Any] | None:
    key = _numeric_key(str(target["ean_upc"]))
    if not key:
        return None
    rows = upc_rows.get(key, [])
    if not rows:
        return None

    candidates = []
    for row in rows:
        article = str(row["article"])
        if not _article_is_in_family(cur, article, int(target["family_id"])):
            continue
        units = article_units.get(article, set())
        if len(units) != 1:
            continue
        unit = next(iter(units))
        candidates.append((unit, row))

    units = {x[0] for x in candidates}
    if len(units) != 1:
        return None

    unit = next(iter(units))
    evidence_rows = [r for u, r in candidates if u == unit]
    return {
        "uom": unit,
        "evidence_rows": evidence_rows,
        "rule": "EXACT_UPC_PLUS_SAME_ARTICLE_PURE_SIZE_DIMENSIONS",
    }


def _prefix(upc: str) -> str | None:
    s = re.sub(r"\D", "", str(upc or ""))
    return s[:3] if len(s) >= 3 else None


def _related_prefix_evidence(cur, target: dict[str, Any]) -> dict[str, Any] | None:
    target_upc = str(target["ean_upc"])
    target_prefix = _prefix(target_upc)
    if not _authoritative_seafood_lb_prefix(target_upc):
        return None

    cur.execute(
        """SELECT DISTINCT su.ean_upc
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
           WHERE baf.family_id=%s
             AND su.record_status='ACTIVE'
             AND su.upc_id<>%s
           ORDER BY su.ean_upc""",
        (target["family_id"], target["upc_id"]),
    )
    peers = [str(r["ean_upc"]) for r in cur.fetchall()]
    qualifying = [
        p for p in peers
        if _authoritative_seafood_lb_prefix(p)
        and _prefix(p) != target_prefix
    ]
    if not qualifying:
        return None

    return {
        "uom": "LB",
        "target_prefix": target_prefix,
        "related_upcs": qualifying,
        "related_prefixes": sorted({_prefix(p) for p in qualifying}),
        "family_id": int(target["family_id"]),
        "main_article_number": str(target["main_article_number"]),
        "rule": "SAME_CONFIRMED_FAMILY_DIFFERENT_ELIGIBLE_PREFIX",
    }


def repair_active_28d_uom(cur, batch_id: int) -> dict[str, Any]:
    active, valid_day_count, latest_valid_date = _active_selling_upcs(cur, batch_id)
    upc_rows, article_units, manual_stats = _latest_article_manual_source(cur, 7)

    result: dict[str, Any] = {
        "version": VERSION,
        "scope": {
            "activity_rule": "POS_POSITIVE_LATEST_UP_TO_28_VALID_COMPLETED_DATA_DAYS",
            "valid_pos_day_count": valid_day_count,
            "latest_valid_pos_date": latest_valid_date,
            "historical_upcs_touched": 0,
        },
        "article_manual": manual_stats,
        "active_upcs_examined": len(active),
        "already_has_current_uom": 0,
        "repaired_authoritative_prefix_lb": 0,
        "repaired_source_supported": 0,
        "held_historical_uom_conflict": 0,
        "held_no_safe_evidence": 0,
        "repaired": [],
        "held_conflicts": [],
    }

    for target in active:
        upc_id = int(target["upc_id"])
        upc = str(target["ean_upc"])

        # 0) Latest user-confirmed Seafood prefix authority. This outranks stale
        # historical/current UOM observations for CURRENT-ACTIVE Seafood UPCs.
        if _authoritative_seafood_lb_prefix(upc) and _is_current_seafood_upc(cur, upc_id):
            if _apply_uom(
                cur,
                upc_id,
                "LB",
                "USER_CONFIRMED_SEAFOOD_PREFIX_LB_V7175",
            ):
                result["repaired_authoritative_prefix_lb"] += 1
                result["repaired"].append({
                    "upc": upc,
                    "uom": "LB",
                    "method": "USER_CONFIRMED_SEAFOOD_PREFIX_LB_V7175",
                    "authority": "SEAFOOD_PREFIX_RULE",
                })
                continue

        if _has_current_uom(cur, upc_id):
            result["already_has_current_uom"] += 1
            continue

        # 1) Exact/numeric-equivalent UPC + same Article + pure structured
        #    Size/dimensions unit declaration from Article Manual.
        source = _safe_article_manual_unit(cur, target, upc_rows, article_units)
        if source:
            conflict = _historical_uom_conflict(cur, upc_id, source["uom"])
            if conflict:
                result["held_historical_uom_conflict"] += 1
                result["held_conflicts"].append({
                    "upc": upc,
                    "rule": source["rule"],
                    "conflict": conflict,
                })
                continue
            if _apply_uom(
                cur,
                upc_id,
                source["uom"],
                "ARTICLE_MANUAL_EXACT_UPC_SAME_ARTICLE_PURE_UNIT_V716",
            ):
                result["repaired_source_supported"] += 1
                result["repaired"].append({
                    "upc": upc,
                    "uom": source["uom"],
                    "method": "ARTICLE_MANUAL_EXACT_UPC_SAME_ARTICLE_PURE_UNIT_V716",
                    "evidence": source["evidence_rows"],
                })
                continue

        # Non-prefix UPCs require explicit Article Manual/user evidence.
        result["held_no_safe_evidence"] += 1

    return result
