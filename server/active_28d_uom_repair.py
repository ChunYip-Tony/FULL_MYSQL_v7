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
    _article_manual_column_map,
    _get,
    _json_obj,
    _monthly_pi_column_map,
    _numeric_identifier,
    _numeric_key,
    _norm_header,
    _selling_factor_from_frozen_pack,
    _source_token,
)

VERSION = "7.0.303-active-28d-uom-repair"

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

# Exact user-confirmed non-prefix Seafood Selling UOM authorities.
# These do not infer identity; they apply only after the UPC already exists in
# current active Seafood product identity.
USER_CONFIRMED_EXACT_SEAFOOD_UOM = {
    "75339325301": "PACK",
    "4029549384": "PACK",
    "4029550430": "PACK",
}


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
            colmap = _article_manual_column_map(
                sh["sheet_name"],
                _json_obj(h["raw_payload"]),
            )
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
                            "pack": pack,
                            "selling_uom": _source_token(_get(payload, colmap, "selling_uom")),
                            "batch_id": int(f["batch_id"]),
                            "file_id": int(f["file_id"]),
                            "sheet_id": int(sh["sheet_id"]),
                            "raw_id": int(rr["raw_id"]),
                            "source_row_number": int(rr["source_row_number"]),
                        })
                        stats["upc_rows"] += 1

    return upc_rows, article_units, stats


def _latest_monthly_pi_frozen_base_source(
    cur,
    preferred_batch_id: int | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Return Article -> explicit Frozen-tab Base UOM observations.

    Monthly PI authority confirmed by the user:
      Frozen Column E = Base Unit.

    Prefer the current ingest batch when it contains a non-duplicate Monthly PI
    file; otherwise use the newest successfully ingested non-duplicate Monthly
    PI batch. No UOM alias or conversion is invented here.
    """
    files: list[dict[str, Any]] = []
    if preferred_batch_id is not None:
        cur.execute(
            """SELECT file_id,batch_id,original_filename
               FROM ingest_file
               WHERE batch_id=%s
                 AND source_type='monthly_pi_form'
                 AND processing_status='INGESTED'
                 AND COALESCE(error_count,0)=0
                 AND duplicate_of_file_id IS NULL
               ORDER BY file_id DESC""",
            (preferred_batch_id,),
        )
        files = cur.fetchall()

    if not files:
        cur.execute(
            """SELECT file_id,batch_id,original_filename
               FROM ingest_file
               WHERE source_type='monthly_pi_form'
                 AND processing_status='INGESTED'
                 AND COALESCE(error_count,0)=0
                 AND duplicate_of_file_id IS NULL
               ORDER BY file_id DESC"""
        )
        all_files = cur.fetchall()
        if all_files:
            newest_batch = int(all_files[0]["batch_id"])
            files = [x for x in all_files if int(x["batch_id"]) == newest_batch]

    article_base_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stats = {
        "files": [x["original_filename"] for x in files],
        "sheets_scanned": 0,
        "rows_scanned": 0,
        "explicit_base_rows": 0,
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
            tab = _norm_header(sh.get("sheet_name"))
            if not (tab == "frozen" or tab.startswith("frozen ")):
                continue
            if not sh.get("header_row_number"):
                continue

            cur.execute(
                """SELECT raw_payload
                   FROM raw_monthly_pi_form
                   WHERE sheet_id=%s AND source_row_number=%s
                   LIMIT 1""",
                (sh["sheet_id"], sh["header_row_number"]),
            )
            h = cur.fetchone()
            if not h:
                continue
            colmap = _monthly_pi_column_map(
                sh["sheet_name"],
                _json_obj(h["raw_payload"]),
            )
            if "base_uom" not in colmap:
                continue
            if "article" not in colmap and "main_article" not in colmap:
                continue

            stats["sheets_scanned"] += 1
            cur.execute(
                """SELECT raw_id,source_row_number,raw_payload
                   FROM raw_monthly_pi_form
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
                base_uom = _source_token(_get(payload, colmap, "base_uom"))
                if not article or not base_uom:
                    continue
                article_base_rows[str(article)].append({
                    "article": str(article),
                    "base_uom": str(base_uom).upper().strip(),
                    "sheet_name": str(sh["sheet_name"]),
                    "batch_id": int(f["batch_id"]),
                    "file_id": int(f["file_id"]),
                    "sheet_id": int(sh["sheet_id"]),
                    "raw_id": int(rr["raw_id"]),
                    "source_row_number": int(rr["source_row_number"]),
                })
                stats["explicit_base_rows"] += 1

    return article_base_rows, stats


def _parse_frozen_pack_selling_declaration(
    selling_uom: Any,
    pack: Any,
) -> dict[str, Any] | None:
    """Interpret Article Manual Frozen Pack Column G conservatively.

    Column G is the Selling Unit. In the source it may be a pure UOM (EA/PAC/
    PACK/BX/CV) or an explicit composite declaration such as 2LB/PACK or
    2.5LB/PACK. Composite declarations are stronger than pack-text inference:
    they directly state the base quantity per selling unit.

    No cross-dimension conversion is performed.
    """
    raw = (_source_token(selling_uom) or '').upper().strip()
    if not raw:
        return None
    token = re.sub(r'\s+', '', raw).replace('LBS', 'LB')

    m = re.fullmatch(r'(\d+(?:\.\d+)?)([A-Z]+)/([A-Z]+)', token)
    if m:
        qty = Decimal(m.group(1))
        base = m.group(2)
        sell = m.group(3)
        if qty <= 0:
            return None
        return {
            'selling_uom': sell,
            'declared_base_uom': base,
            'base_qty_per_selling_unit': qty,
            'conversion_basis': 'ARTICLE_MANUAL_G_EXPLICIT_BASE_PER_SELLING',
            'raw_selling_declaration': raw,
        }

    # Pure unit: derive a weight factor only from the same row's structured
    # Column E pack text, using the already-conservative parser.
    inferred = _selling_factor_from_frozen_pack(raw, pack)
    if inferred:
        return {
            'selling_uom': raw,
            'declared_base_uom': inferred.get('base_uom'),
            'base_qty_per_selling_unit': Decimal(str(inferred['base_qty_per_selling_unit'])),
            'conversion_basis': inferred.get('conversion_basis'),
            'raw_selling_declaration': raw,
        }

    # Pure canonical unit may still be useful when Monthly PI says Base equals
    # Selling; factor 1 will be assigned only after the cross-source check.
    if re.fullmatch(r'[A-Z]+', token):
        return {
            'selling_uom': raw,
            'declared_base_uom': None,
            'base_qty_per_selling_unit': None,
            'conversion_basis': 'PURE_SELLING_UOM_NO_FACTOR_YET',
            'raw_selling_declaration': raw,
        }

    return None


def _safe_frozen_pack_cross_source_mapping(
    cur,
    target: dict[str, Any],
    upc_rows: dict[str, list[dict[str, Any]]],
    monthly_pi_base_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Resolve Selling UOM + Base UOM + factor from two explicit sources.

    Article Manual Frozen Pack:
      D = UPC, E = pack size, G = Selling Unit.
    Monthly PI Frozen:
      E = Base Unit.

    Pack text is used for a conversion only when Monthly PI explicitly confirms
    the same printed base UOM. Conflicts or ambiguity remain unresolved.
    """
    key = _numeric_key(str(target.get("ean_upc") or ""))
    if not key:
        return None

    candidates: list[dict[str, Any]] = []
    for row in upc_rows.get(key, []):
        if _norm_header(row.get("sheet_name")) != "frozen pack":
            continue
        article = str(row.get("article") or "")
        if not article or not _article_is_in_family(cur, article, int(target["family_id"])):
            continue
        selling_decl = _parse_frozen_pack_selling_declaration(
            row.get("selling_uom"),
            row.get("pack"),
        )
        if not selling_decl:
            continue
        selling = str(selling_decl["selling_uom"]).upper().strip()

        base_rows = monthly_pi_base_rows.get(article, [])
        if not base_rows and article != str(target.get("main_article_number") or ""):
            base_rows = monthly_pi_base_rows.get(str(target.get("main_article_number") or ""), [])
        base_units = {
            str(x.get("base_uom") or "").upper().strip()
            for x in base_rows
            if str(x.get("base_uom") or "").strip()
        }
        if len(base_units) != 1:
            continue
        base = next(iter(base_units))

        sell_uom_row = _uom_by_code(cur, selling)
        base_uom_row = _uom_by_code(cur, base)
        if not sell_uom_row or not base_uom_row:
            continue

        declared_base = str(selling_decl.get("declared_base_uom") or "").upper().strip()
        declared_factor = selling_decl.get("base_qty_per_selling_unit")

        if selling == base:
            # Same-unit selling/base always means factor 1; package size remains
            # descriptive and must not multiply POS quantity.
            factor = Decimal("1")
            conversion_basis = "SELLING_EQUALS_MONTHLY_PI_BASE"
            pack_detail = selling_decl
        elif declared_base and declared_factor is not None:
            if declared_base != base:
                continue
            factor = Decimal(str(declared_factor))
            conversion_basis = str(selling_decl.get("conversion_basis") or "ARTICLE_MANUAL_DECLARED")
            pack_detail = selling_decl
        else:
            # Pure non-base selling unit without an explicit Column G
            # conversion may use the same-row structured Column E pack text.
            pack_detail = _selling_factor_from_frozen_pack(selling, row.get("pack"))
            if not pack_detail:
                continue
            parsed_base = str(pack_detail.get("base_uom") or "").upper().strip()
            if parsed_base != base:
                continue
            factor = Decimal(str(pack_detail["base_qty_per_selling_unit"]))
            conversion_basis = str(pack_detail["conversion_basis"])

        candidates.append({
            "selling_uom": str(sell_uom_row["uom_code"]),
            "selling_uom_id": int(sell_uom_row["uom_id"]),
            "base_uom": str(base_uom_row["uom_code"]),
            "base_uom_id": int(base_uom_row["uom_id"]),
            "factor": factor,
            "conversion_basis": conversion_basis,
            "article_manual_row": row,
            "monthly_pi_rows": base_rows,
            "pack_detail": pack_detail,
        })

    signatures = {
        (
            x["selling_uom"].upper(),
            x["base_uom"].upper(),
            str(x["factor"]),
        )
        for x in candidates
    }
    if len(signatures) != 1 or not candidates:
        return None

    chosen = candidates[0]
    chosen["rule"] = "ARTICLE_MANUAL_FROZEN_PACK_PLUS_MONTHLY_PI_BASE_V7303"
    return chosen


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
    monthly_pi_base_rows, monthly_pi_stats = _latest_monthly_pi_frozen_base_source(
        cur,
        preferred_batch_id=batch_id,
    )

    result: dict[str, Any] = {
        "version": VERSION,
        "scope": {
            "activity_rule": "POS_POSITIVE_LATEST_UP_TO_28_VALID_COMPLETED_DATA_DAYS",
            "valid_pos_day_count": valid_day_count,
            "latest_valid_pos_date": latest_valid_date,
            "historical_upcs_touched": 0,
        },
        "article_manual": manual_stats,
        "monthly_pi": monthly_pi_stats,
        "active_upcs_examined": len(active),
        "already_has_current_uom": 0,
        "repaired_authoritative_prefix_lb": 0,
        "repaired_source_supported": 0,
        "repaired_frozen_pack_cross_source": 0,
        "held_historical_uom_conflict": 0,
        "held_cross_source_conflict": 0,
        "held_no_safe_evidence": 0,
        "repaired": [],
        "held_conflicts": [],
    }

    for target in active:
        upc_id = int(target["upc_id"])
        upc = str(target["ean_upc"])

        # 0a) Latest user-confirmed Seafood prefix authority. Prefix items are
        # sold by LB; this remains stronger than packaged-item inference.
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
                    "base_uom": "LB",
                    "base_qty_per_selling_unit": "1",
                    "method": "USER_CONFIRMED_SEAFOOD_PREFIX_LB_V7175",
                    "authority": "SEAFOOD_PREFIX_RULE",
                })
                continue

        # 0b) Strong two-source packaged-item authority:
        #   Article Manual Frozen Pack D/E/G = UPC / pack / Selling Unit
        #   Monthly PI Frozen E = Base Unit
        # Run BEFORE the "already has UOM" short-circuit so an existing
        # selling-only PACK/BX/PAC mapping can be enriched with Base + factor.
        cross = _safe_frozen_pack_cross_source_mapping(
            cur,
            target,
            upc_rows,
            monthly_pi_base_rows,
        )
        if cross:
            exact_uom = USER_CONFIRMED_EXACT_SEAFOOD_UOM.get(upc)
            if exact_uom and str(cross["selling_uom"]).upper() != str(exact_uom).upper():
                result["held_cross_source_conflict"] += 1
                result["held_conflicts"].append({
                    "upc": upc,
                    "rule": cross["rule"],
                    "reason": "ARTICLE_MANUAL_SELLING_UOM_CONFLICTS_WITH_EXACT_USER_AUTHORITY",
                    "article_manual_selling_uom": cross["selling_uom"],
                    "user_confirmed_selling_uom": exact_uom,
                })
                continue

            _insert_uom_mapping(
                cur,
                upc_id,
                int(cross["selling_uom_id"]),
                int(cross["base_uom_id"]),
                Decimal(str(cross["factor"])),
                cross["rule"],
            )
            result["repaired_source_supported"] += 1
            result["repaired_frozen_pack_cross_source"] += 1
            result["repaired"].append({
                "upc": upc,
                "uom": cross["selling_uom"],
                "base_uom": cross["base_uom"],
                "base_qty_per_selling_unit": str(cross["factor"]),
                "method": cross["rule"],
                "conversion_basis": cross["conversion_basis"],
                "article_manual_pack": cross["article_manual_row"].get("pack"),
                "article_manual_article": cross["article_manual_row"].get("article"),
                "monthly_pi_base_evidence": cross["monthly_pi_rows"],
            })
            continue

        # 0c) Exact user-confirmed non-prefix Seafood Selling-UOM fallback.
        # It remains useful when the cross-source base conversion is not yet
        # available, but it intentionally does not invent a Base UOM/factor.
        exact_uom = USER_CONFIRMED_EXACT_SEAFOOD_UOM.get(upc)
        if exact_uom and _is_current_seafood_upc(cur, upc_id):
            if _apply_uom(
                cur,
                upc_id,
                exact_uom,
                "USER_CONFIRMED_EXACT_SEAFOOD_UOM_V7182",
            ):
                result["repaired_source_supported"] += 1
                result["repaired"].append({
                    "upc": upc,
                    "uom": exact_uom,
                    "method": "USER_CONFIRMED_EXACT_SEAFOOD_UOM_V7182",
                    "authority": "EXACT_USER_CONFIRMATION",
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
