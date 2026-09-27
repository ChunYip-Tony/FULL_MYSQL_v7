from __future__ import annotations

from collections import defaultdict
from typing import Any

from article_manual_multitab_repair import _load_roster
from current_active_cost_repair import (
    RECEIPT_MOVEMENTS,
    _article_family,
    _best_cost,
    _date,
    _header_map,
    _id,
    _j,
    _num,
    _pick,
    _uom_id,
    _upc_family,
)
from normalize import _numeric_key


COST_HOLD_REASONS = {
    "CURRENT_COST_MISSING",
    "COST_TO_SELLING_UOM_UNRESOLVED",
}


def _norm_uom(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    return "PACK" if s in {"PAC", "PACK"} else s


def _reason_list(v: Any) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x and x.strip()]


def _family_articles(cur, family_id: int) -> list[dict[str, Any]]:
    cur.execute(
        """SELECT a.article_id,a.article_number
           FROM article a
           JOIN bridge_article_family baf
             ON baf.article_id=a.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE baf.family_id=%s
           ORDER BY a.article_id""",
        (family_id,),
    )
    return cur.fetchall()


def _receipt_evidence(
    cur,
    family_id: int,
    article_ids: list[int],
) -> dict[str, Any]:
    if article_ids:
        ph = ",".join(["%s"] * len(article_ids))
        where = f"(m.family_id=%s OR m.article_id IN ({ph}))"
        params: tuple[Any, ...] = tuple([family_id] + article_ids)
    else:
        where = "m.family_id=%s"
        params = (family_id,)

    cur.execute(
        f"""SELECT
               COUNT(*) AS receipt_rows,
               SUM(CASE
                     WHEN m.amount_local_currency IS NOT NULL
                      AND m.amount_local_currency<>0
                      AND m.base_quantity IS NOT NULL
                      AND m.base_quantity<>0
                      AND m.base_uom_code IS NOT NULL
                     THEN 1 ELSE 0 END) AS valid_valuation_rows,
               MAX(m.posting_date) AS latest_receipt_date
            FROM movement_history m
            WHERE {where}
              AND m.movement_type IN ('101','107','109')""",
        params,
    )
    summary = cur.fetchone() or {}

    cur.execute(
        f"""SELECT m.article_number,m.article_id,m.family_id,m.description,
                   m.movement_type,m.posting_date,
                   m.entry_quantity,m.entry_uom_code,
                   m.base_quantity,m.base_uom_code,
                   m.amount_local_currency,
                   CASE
                     WHEN m.amount_local_currency IS NOT NULL
                      AND m.amount_local_currency<>0
                      AND m.base_quantity IS NOT NULL
                      AND m.base_quantity<>0
                     THEN ABS(m.amount_local_currency/m.base_quantity)
                     ELSE NULL
                   END AS derived_unit_cost,
                   m.article_document,m.purchase_order,m.vendor_code,
                   m.file_id,m.sheet_id,m.raw_id,m.source_row_number
            FROM movement_history m
            WHERE {where}
              AND m.movement_type IN ('101','107','109')
            ORDER BY m.posting_date DESC,m.raw_id DESC
            LIMIT 12""",
        params,
    )
    rows = cur.fetchall()

    return {
        "receipt_rows": int(summary.get("receipt_rows") or 0),
        "valid_valuation_rows": int(summary.get("valid_valuation_rows") or 0),
        "latest_receipt_date": summary.get("latest_receipt_date"),
        "recent_rows": rows,
    }


def _official_evidence(
    cur,
    family_id: int,
    article_ids: list[int],
) -> dict[str, Any]:
    """Read-only official-cost evidence using the same identity/UOM gates as repair.

    v7.0.39 closes a false-SAFE gap: a non-null source cost UOM is not enough.
    For auto-repair eligibility the UOM must resolve to dim_uom and the source
    row must be linkable to the target Family through one of the repair routes.
    """

    # Mirror all authoritative relink routes used by current_active_cost_repair:
    #   1) existing family_id
    #   2) existing article_id -> confirmed Family
    #   3) source article_number -> confirmed Family
    #   4) existing upc_id -> confirmed Article -> Family
    match_sql = """(
        c.family_id=%s
        OR baf_ai.family_id=%s
        OR baf_an.family_id=%s
        OR baf_upc.family_id=%s
    )"""
    match_params: tuple[Any, ...] = (
        family_id,
        family_id,
        family_id,
        family_id,
    )

    joins = """
        LEFT JOIN bridge_article_family baf_ai
          ON baf_ai.article_id=c.article_id
         AND baf_ai.mapping_status='CONFIRMED'
         AND baf_ai.is_primary=TRUE
         AND (baf_ai.valid_to IS NULL OR baf_ai.valid_to>CURRENT_TIMESTAMP(6))
        LEFT JOIN article srca
          ON srca.article_number=c.article_number
        LEFT JOIN bridge_article_family baf_an
          ON baf_an.article_id=srca.article_id
         AND baf_an.mapping_status='CONFIRMED'
         AND baf_an.is_primary=TRUE
         AND (baf_an.valid_to IS NULL OR baf_an.valid_to>CURRENT_TIMESTAMP(6))
        LEFT JOIN bridge_article_upc bau_upc
          ON bau_upc.upc_id=c.upc_id
         AND bau_upc.mapping_status='CONFIRMED'
         AND bau_upc.is_primary=TRUE
         AND (bau_upc.valid_to IS NULL OR bau_upc.valid_to>CURRENT_TIMESTAMP(6))
        LEFT JOIN bridge_article_family baf_upc
          ON baf_upc.article_id=bau_upc.article_id
         AND baf_upc.mapping_status='CONFIRMED'
         AND baf_upc.is_primary=TRUE
         AND (baf_upc.valid_to IS NULL OR baf_upc.valid_to>CURRENT_TIMESTAMP(6))
        LEFT JOIN dim_uom du
          ON UPPER(du.uom_code)=UPPER(TRIM(c.cost_uom_code))
        LEFT JOIN product_family pf_target
          ON pf_target.family_id=%s
        LEFT JOIN article ma
          ON ma.article_number=pf_target.main_article_number
    """
    params = (family_id, *match_params)

    cur.execute(
        f"""SELECT
               COUNT(*) AS official_rows,
               SUM(CASE WHEN c.official_cost IS NOT NULL AND c.official_cost>0
                        THEN 1 ELSE 0 END) AS positive_cost_rows,
               SUM(CASE WHEN c.official_cost IS NOT NULL AND c.official_cost>0
                              AND NULLIF(TRIM(c.cost_uom_code),'') IS NOT NULL
                        THEN 1 ELSE 0 END) AS positive_with_uom_rows,
               SUM(CASE WHEN c.official_cost IS NOT NULL AND c.official_cost>0
                              AND du.uom_id IS NOT NULL
                        THEN 1 ELSE 0 END) AS positive_with_supported_uom_rows,
               SUM(CASE WHEN c.official_cost IS NOT NULL AND c.official_cost>0
                              AND NULLIF(TRIM(c.cost_uom_code),'') IS NOT NULL
                              AND du.uom_id IS NULL
                        THEN 1 ELSE 0 END) AS positive_with_unsupported_uom_rows,
               SUM(CASE WHEN c.official_cost IS NOT NULL AND c.official_cost>0
                              AND NULLIF(TRIM(c.cost_uom_code),'') IS NULL
                        THEN 1 ELSE 0 END) AS positive_missing_uom_rows,
               SUM(CASE WHEN c.official_cost IS NOT NULL AND c.official_cost>0
                              AND du.uom_id IS NOT NULL
                              AND COALESCE(c.article_id,srca.article_id,bau_upc.article_id,ma.article_id)
                                  IS NOT NULL
                        THEN 1 ELSE 0 END) AS repairable_official_rows,
               MAX(c.observation_date) AS latest_official_date
            FROM company_price_observation c
            {joins}
            WHERE {match_sql}
              AND c.source_type IN (
                'frozen_inventory',
                'tx_seafood_abc_price',
                'live_fresh_suggestion'
              )""",
        params,
    )
    summary = cur.fetchone() or {}

    cur.execute(
        f"""SELECT c.company_price_observation_id,c.source_type,
                   c.observation_date,c.article_number,c.article_id,
                   c.ean_upc,c.upc_id,c.family_id,
                   c.official_cost,c.cost_uom_code,
                   du.uom_code AS canonical_cost_uom,
                   CASE WHEN du.uom_id IS NOT NULL THEN TRUE ELSE FALSE END
                     AS cost_uom_supported,
                   CASE
                     WHEN c.family_id=%s THEN 'EXISTING_FAMILY'
                     WHEN baf_ai.family_id=%s THEN 'EXISTING_ARTICLE_ID'
                     WHEN baf_an.family_id=%s THEN 'SOURCE_ARTICLE_NUMBER'
                     WHEN baf_upc.family_id=%s THEN 'EXISTING_UPC_ID'
                     ELSE 'UNRESOLVED'
                   END AS family_match_route,
                   COALESCE(c.article_id,srca.article_id,bau_upc.article_id,ma.article_id)
                     AS projected_anchor_article_id,
                   CASE
                     WHEN c.official_cost IS NOT NULL AND c.official_cost>0
                      AND du.uom_id IS NOT NULL
                      AND COALESCE(c.article_id,srca.article_id,bau_upc.article_id,ma.article_id)
                          IS NOT NULL
                     THEN TRUE ELSE FALSE
                   END AS repairable_by_current_rule,
                   c.price_a,c.price_b,c.price_c,
                   c.file_id,c.sheet_id,c.raw_id,c.source_row_number
            FROM company_price_observation c
            {joins}
            WHERE {match_sql}
              AND c.source_type IN (
                'frozen_inventory',
                'tx_seafood_abc_price',
                'live_fresh_suggestion'
              )
            ORDER BY c.observation_date DESC,c.company_price_observation_id DESC
            LIMIT 12""",
        (*params[:1], family_id, family_id, family_id, family_id, *params[1:]),
    )
    rows = cur.fetchall()

    cur.execute(
        f"""SELECT COALESCE(NULLIF(TRIM(c.cost_uom_code),''),'__MISSING__') AS source_cost_uom,
                   COUNT(*) AS row_count,
                   SUM(CASE WHEN du.uom_id IS NOT NULL THEN 1 ELSE 0 END) AS supported_rows
            FROM company_price_observation c
            {joins}
            WHERE {match_sql}
              AND c.source_type IN (
                'frozen_inventory',
                'tx_seafood_abc_price',
                'live_fresh_suggestion'
              )
              AND c.official_cost IS NOT NULL
              AND c.official_cost>0
            GROUP BY COALESCE(NULLIF(TRIM(c.cost_uom_code),''),'__MISSING__')
            ORDER BY row_count DESC,source_cost_uom""",
        params,
    )
    uom_tokens = cur.fetchall()

    return {
        "official_rows": int(summary.get("official_rows") or 0),
        "positive_cost_rows": int(summary.get("positive_cost_rows") or 0),
        "positive_with_uom_rows": int(summary.get("positive_with_uom_rows") or 0),
        "positive_with_supported_uom_rows": int(
            summary.get("positive_with_supported_uom_rows") or 0
        ),
        "positive_with_unsupported_uom_rows": int(
            summary.get("positive_with_unsupported_uom_rows") or 0
        ),
        "positive_missing_uom_rows": int(summary.get("positive_missing_uom_rows") or 0),
        "repairable_official_rows": int(summary.get("repairable_official_rows") or 0),
        "latest_official_date": summary.get("latest_official_date"),
        "source_cost_uom_tokens": uom_tokens,
        "recent_rows": rows,
    }


def _article_manual_index(cur) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    roster, stats = _load_roster(cur, None)
    idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in roster:
        key = _numeric_key(str(row.get("source_upc") or ""))
        if not key:
            continue
        idx[key].append(
            {
                "source_upc": row.get("source_upc"),
                "article_number": row.get("article_number"),
                "canonical_main": row.get("canonical_main"),
                "description": row.get("description"),
                "pack": row.get("pack"),
                "explicit_um": row.get("selling_uom"),
                "sheet": row.get("sheet_name"),
            }
        )
    return dict(idx), stats


def _scan_oh_evidence(
    cur,
    target_family_ids: set[int],
) -> dict[int, dict[str, Any]]:
    """Read-only scan of explicit OH cost evidence for target families only."""

    result: dict[int, dict[str, Any]] = {
        int(fid): {
            "positive_cost_candidates": 0,
            "explicit_supported_uom_candidates": 0,
            "missing_explicit_cost_uom_candidates": 0,
            "unsupported_cost_uom_candidates": 0,
            "recent_candidates": [],
        }
        for fid in target_family_ids
    }
    if not target_family_ids:
        return result

    article_cache: dict[str, tuple[int | None, int | None]] = {}
    upc_cache: dict[str, tuple[int | None, int | None, int | None]] = {}

    cur.execute(
        """SELECT file_id,coverage_end_date,filename_date_candidate,upload_timestamp
           FROM ingest_file
           WHERE source_type='on_hand'
           ORDER BY file_id"""
    )
    files = cur.fetchall()

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
            c_article = _pick(
                hmap,
                ["Article", "Article Number", "Material", "Material Number"],
            )
            c_upc = _pick(hmap, ["UPC", "EAN", "Barcode", "Sales Set"])
            c_cost = _pick(
                hmap,
                [
                    "Cost", "Unit Cost", "Current Cost", "Average Cost", "Avg Cost",
                    "Moving Average Price", "Moving Price", "MAP",
                ],
            )
            c_cost_uom = _pick(
                hmap,
                ["Cost UOM", "Cost Unit", "Price UOM", "Price Unit", "Cost Base UOM"],
            )
            c_date = _pick(
                hmap,
                ["Date", "Inventory Date", "Count Date", "Snapshot Date"],
            )

            if not c_cost or (not c_article and not c_upc):
                continue

            cur.execute(
                """SELECT raw_id,source_row_number,raw_payload
                   FROM raw_on_hand
                   WHERE sheet_id=%s AND source_row_number>%s
                   ORDER BY source_row_number""",
                (sh["sheet_id"], header_row),
            )
            for rr in cur.fetchall():
                p = _j(rr["raw_payload"])
                cost = _num(p.get(c_cost))
                if cost is None or cost <= 0:
                    continue

                article_num = _id(p.get(c_article)) if c_article else None
                ean = _id(p.get(c_upc)) if c_upc else None

                if article_num not in article_cache:
                    article_cache[article_num or ""] = _article_family(cur, article_num)
                article_id, article_family = article_cache[article_num or ""]

                if ean not in upc_cache:
                    upc_cache[ean or ""] = _upc_family(cur, ean)
                _, upc_article_id, upc_family = upc_cache[ean or ""]

                family_candidates = {
                    int(x)
                    for x in (article_family, upc_family)
                    if x is not None
                }
                if len(family_candidates) != 1:
                    continue
                family_id = next(iter(family_candidates))
                if family_id not in target_family_ids:
                    continue

                item = result[family_id]
                item["positive_cost_candidates"] += 1

                cost_uom = (
                    str(p.get(c_cost_uom) or "").strip().upper()
                    if c_cost_uom else ""
                )
                supported = False
                if not cost_uom:
                    item["missing_explicit_cost_uom_candidates"] += 1
                else:
                    supported = _uom_id(cur, cost_uom) is not None
                    if supported:
                        item["explicit_supported_uom_candidates"] += 1
                    else:
                        item["unsupported_cost_uom_candidates"] += 1

                obs_date = (
                    _date(p.get(c_date)) if c_date else None
                ) or f.get("coverage_end_date") or f.get("filename_date_candidate")
                if obs_date is None and f.get("upload_timestamp"):
                    obs_date = f["upload_timestamp"].date()

                candidates = item["recent_candidates"]
                candidates.append(
                    {
                        "cost": cost,
                        "cost_uom": cost_uom or None,
                        "supported_cost_uom": supported,
                        "article_number": article_num,
                        "ean_upc": ean,
                        "observation_date": obs_date,
                        "file_id": f["file_id"],
                        "sheet_id": sh["sheet_id"],
                        "raw_id": rr["raw_id"],
                        "source_row_number": rr["source_row_number"],
                    }
                )
                candidates.sort(
                    key=lambda x: (
                        str(x.get("observation_date") or ""),
                        int(x.get("raw_id") or 0),
                    ),
                    reverse=True,
                )
                del candidates[8:]

    return result


def _classify_missing_cost(
    receipt: dict[str, Any],
    official: dict[str, Any],
    oh: dict[str, Any],
) -> dict[str, Any]:
    if int(receipt.get("valid_valuation_rows") or 0) > 0:
        return {
            "classification": "SAFE_RECEIPT_VALUATION_REPAIR_CANDIDATE",
            "safe_to_auto_resolve": True,
            "proposed_action": "RELINK_OR_BACKFILL_RECEIPT_VALUATION",
        }

    if int(official.get("repairable_official_rows") or 0) > 0:
        return {
            "classification": "SAFE_OFFICIAL_COST_REPAIR_CANDIDATE",
            "safe_to_auto_resolve": True,
            "proposed_action": "RELINK_OR_BACKFILL_OFFICIAL_REPORT_COST",
        }

    if int(oh.get("explicit_supported_uom_candidates") or 0) > 0:
        return {
            "classification": "SAFE_OH_COST_FALLBACK_REPAIR_CANDIDATE",
            "safe_to_auto_resolve": True,
            "proposed_action": "BACKFILL_EXPLICIT_OH_COST_FALLBACK",
        }

    if int(receipt.get("receipt_rows") or 0) > 0:
        return {
            "classification": "RECEIPT_ROWS_WITHOUT_VALID_VALUATION",
            "safe_to_auto_resolve": False,
            "proposed_action": "REVIEW_RECEIPT_VALUATION_FIELDS",
        }

    if int(official.get("positive_cost_rows") or 0) > 0:
        if int(official.get("positive_with_uom_rows") or 0) == 0:
            return {
                "classification": "OFFICIAL_COST_WITHOUT_EXPLICIT_UOM",
                "safe_to_auto_resolve": False,
                "proposed_action": "REVIEW_OFFICIAL_COST_UOM",
            }
        if int(official.get("positive_with_supported_uom_rows") or 0) == 0:
            return {
                "classification": "OFFICIAL_COST_UOM_UNSUPPORTED",
                "safe_to_auto_resolve": False,
                "proposed_action": "REVIEW_AND_MAP_OFFICIAL_COST_UOM_TOKEN",
            }
        return {
            "classification": "OFFICIAL_COST_IDENTITY_ANCHOR_UNRESOLVED",
            "safe_to_auto_resolve": False,
            "proposed_action": "REVIEW_OFFICIAL_COST_IDENTITY_ANCHOR",
        }

    if int(oh.get("positive_cost_candidates") or 0) > 0:
        return {
            "classification": "OH_COST_WITHOUT_EXPLICIT_SUPPORTED_UOM",
            "safe_to_auto_resolve": False,
            "proposed_action": "REVIEW_OH_COST_UOM",
        }

    return {
        "classification": "NO_AUTHORITATIVE_COST_EVIDENCE",
        "safe_to_auto_resolve": False,
        "proposed_action": "REQUIRES_NEW_AUTHORITATIVE_COST_EVIDENCE",
    }


def _classify_conversion(
    row: dict[str, Any],
    best_cost: dict[str, Any] | None,
) -> dict[str, Any]:
    selling = _norm_uom(row.get("selling_uom"))
    base = _norm_uom(row.get("base_uom"))
    factor = row.get("base_qty_per_selling_unit")
    cost_uom = _norm_uom(best_cost.get("uom")) if best_cost else None

    if not best_cost:
        return {
            "classification": "AUTHORITATIVE_COST_NOT_FOUND_DURING_CONVERSION_CHECK",
            "safe_to_auto_resolve": False,
            "proposed_action": "DIAGNOSE_COST_LINEAGE_FIRST",
            "selling_uom": selling,
            "cost_uom": cost_uom,
        }

    if selling and cost_uom and selling == cost_uom:
        return {
            "classification": "DIRECT_COST_UOM_EQUALS_SELLING_UOM",
            "safe_to_auto_resolve": True,
            "proposed_action": (
                "CALCULATE_COST_PER_SELLING_UNIT_DIRECTLY_WITH_FACTOR_1_"
                "WITHOUT_ASSERTING_BASE_INVENTORY_UOM"
            ),
            "selling_uom": selling,
            "cost_uom": cost_uom,
        }

    if base and factor is not None and cost_uom and base == cost_uom:
        return {
            "classification": "SERVING_CONVERSION_REBUILD_CANDIDATE",
            "safe_to_auto_resolve": True,
            "proposed_action": "REBUILD_COST_TO_SELLING_FROM_EXISTING_BASE_CONVERSION",
            "selling_uom": selling,
            "cost_uom": cost_uom,
            "base_uom": base,
            "factor": factor,
        }

    if selling == "PACK":
        return {
            "classification": "PACK_CONVERSION_EVIDENCE_NEEDED",
            "safe_to_auto_resolve": False,
            "proposed_action": "REQUIRE_EXPLICIT_PACK_TO_COST_UOM_CONVERSION",
            "selling_uom": selling,
            "cost_uom": cost_uom,
            "base_uom": base,
            "factor": factor,
        }

    if not cost_uom:
        return {
            "classification": "AUTHORITATIVE_COST_UOM_MISSING",
            "safe_to_auto_resolve": False,
            "proposed_action": "REQUIRE_EXPLICIT_COST_UOM",
            "selling_uom": selling,
            "cost_uom": None,
            "base_uom": base,
            "factor": factor,
        }

    return {
        "classification": "COST_UOM_SELLING_UOM_MISMATCH",
        "safe_to_auto_resolve": False,
        "proposed_action": "REQUIRE_EXPLICIT_CONVERSION_EVIDENCE",
        "selling_uom": selling,
        "cost_uom": cost_uom,
        "base_uom": base,
        "factor": factor,
    }


def diagnose_global_cost_holds(
    cur,
    upc: str | None = None,
    family_id: int | None = None,
) -> dict[str, Any]:
    where = ["q.quick_check_status='QA_HOLD'"]
    params: list[Any] = []
    if upc:
        where.append("q.ean_upc=%s")
        params.append(str(upc))
    if family_id is not None:
        where.append("q.family_id=%s")
        params.append(int(family_id))

    cur.execute(
        f"""SELECT q.upc_id,q.ean_upc,q.selling_description,
                   q.article_id,q.article_number,
                   q.family_id,q.main_article_number,q.family_description,
                   q.product_class,q.selling_uom,q.base_uom,
                   q.base_qty_per_selling_unit,
                   q.current_cost_per_base_uom,
                   q.current_cost_per_selling_unit,
                   q.cost_source,q.cost_date,
                   q.current_price,q.current_price_type,
                   q.pos_qty_7d,q.pos_qty_30d,
                   q.quick_check_status,q.blocking_reason,
                   q.publish_batch_id
            FROM quick_check_current q
            WHERE {" AND ".join(where)}
            ORDER BY q.family_id,q.ean_upc""",
        tuple(params),
    )
    all_holds = [dict(x) for x in cur.fetchall()]

    reason_counts: dict[str, int] = {}
    cost_rows: list[dict[str, Any]] = []
    other_hold_rows = 0
    for row in all_holds:
        reasons = _reason_list(row.get("blocking_reason"))
        row["reasons"] = reasons
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if any(r in COST_HOLD_REASONS for r in reasons):
            cost_rows.append(row)
        else:
            other_hold_rows += 1

    target_families = {int(x["family_id"]) for x in cost_rows}
    family_articles: dict[int, list[dict[str, Any]]] = {}
    receipt_cache: dict[int, dict[str, Any]] = {}
    official_cache: dict[int, dict[str, Any]] = {}
    best_cost_cache: dict[int, dict[str, Any] | None] = {}

    for fid in sorted(target_families):
        arts = _family_articles(cur, fid)
        family_articles[fid] = arts
        article_ids = [int(x["article_id"]) for x in arts]
        receipt_cache[fid] = _receipt_evidence(cur, fid, article_ids)
        official_cache[fid] = _official_evidence(cur, fid, article_ids)
        best_cost_cache[fid] = _best_cost(cur, fid)

    oh_cache = _scan_oh_evidence(cur, target_families)
    manual_index, manual_stats = _article_manual_index(cur)

    items: list[dict[str, Any]] = []
    classification_counts: dict[str, int] = {}
    safe_count = 0

    for row in cost_rows:
        fid = int(row["family_id"])
        reasons = row["reasons"]
        best_cost = best_cost_cache.get(fid)
        receipt = receipt_cache[fid]
        official = official_cache[fid]
        oh = oh_cache.get(fid, {})

        missing_cost_class = None
        conversion_class = None

        if "CURRENT_COST_MISSING" in reasons:
            missing_cost_class = _classify_missing_cost(receipt, official, oh)

        if "COST_TO_SELLING_UOM_UNRESOLVED" in reasons:
            conversion_class = _classify_conversion(row, best_cost)

        classifications = [
            x for x in (missing_cost_class, conversion_class)
            if x is not None
        ]
        safe = bool(classifications) and all(
            bool(x.get("safe_to_auto_resolve")) for x in classifications
        )

        for cls in classifications:
            code = str(cls["classification"])
            classification_counts[code] = classification_counts.get(code, 0) + 1

        if safe:
            safe_count += 1

        manual_key = _numeric_key(str(row.get("ean_upc") or ""))
        manual_rows = list(manual_index.get(manual_key or "", []))

        items.append(
            {
                "ean_upc": str(row["ean_upc"]),
                "article_number": row.get("article_number"),
                "family_id": fid,
                "main_article_number": row.get("main_article_number"),
                "selling_description": row.get("selling_description"),
                "product_class": row.get("product_class"),
                "selling_uom": row.get("selling_uom"),
                "base_uom": row.get("base_uom"),
                "base_qty_per_selling_unit": row.get("base_qty_per_selling_unit"),
                "current_cost_per_base_uom": row.get("current_cost_per_base_uom"),
                "current_cost_per_selling_unit": row.get("current_cost_per_selling_unit"),
                "cost_source": row.get("cost_source"),
                "cost_date": row.get("cost_date"),
                "current_price": row.get("current_price"),
                "current_price_type": row.get("current_price_type"),
                "pos_qty_7d": row.get("pos_qty_7d"),
                "pos_qty_30d": row.get("pos_qty_30d"),
                "blocking_reason": row.get("blocking_reason"),
                "reasons": reasons,
                "safe_to_auto_resolve_cost_hold": safe,
                "missing_cost_classification": missing_cost_class,
                "conversion_classification": conversion_class,
                "best_authoritative_cost": best_cost,
                "receipt_evidence": receipt,
                "official_cost_evidence": official,
                "oh_cost_evidence": oh,
                "confirmed_family_articles": family_articles[fid],
                "article_manual_exact_upc_rows": manual_rows,
                "publish_batch_id": row.get("publish_batch_id"),
            }
        )

    return {
        "status": "OK",
        "scope": {
            "upc": upc,
            "family_id": family_id,
            "source": "CURRENT_QUICK_CHECK_QA_HOLD",
        },
        "summary": {
            "all_current_hold_rows": len(all_holds),
            "cost_related_hold_rows": len(cost_rows),
            "other_hold_rows": other_hold_rows,
            "unique_cost_hold_families": len(target_families),
            "current_cost_missing_count": reason_counts.get("CURRENT_COST_MISSING", 0),
            "cost_to_selling_uom_unresolved_count": reason_counts.get(
                "COST_TO_SELLING_UOM_UNRESOLVED", 0
            ),
            "safe_to_auto_resolve_cost_hold_count": safe_count,
            "needs_review_cost_hold_count": len(cost_rows) - safe_count,
            "classification_counts": classification_counts,
            "all_hold_reason_counts": reason_counts,
        },
        "article_manual": manual_stats,
        "items": items,
    }
