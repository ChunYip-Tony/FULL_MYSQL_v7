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
    _oh_cost_columns,
    _oh_cost_candidate,
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
    """Read-only scan of explicit or derived OH cost evidence for target families."""

    result: dict[int, dict[str, Any]] = {
        int(fid): {
            "positive_cost_candidates": 0,
            "supported_cost_candidates": 0,
            "explicit_supported_uom_candidates": 0,
            "derived_total_value_candidates": 0,
            "derived_supported_uom_candidates": 0,
            "missing_explicit_cost_uom_candidates": 0,
            "unsupported_cost_uom_candidates": 0,
            "unsupported_currency_candidates": 0,
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

            cols = _oh_cost_columns(_header_map(_j(hr["raw_payload"])))
            identity_ok = bool(cols.get("article") or cols.get("upc"))
            explicit_mode_available = bool(cols.get("explicit_cost"))
            derived_mode_available = bool(
                cols.get("total_value")
                and cols.get("unrestricted_qty")
                and cols.get("base_uom")
            )
            if not identity_ok or not (explicit_mode_available or derived_mode_available):
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
                candidate = _oh_cost_candidate(p, cols)
                if not candidate.get("candidate_present"):
                    continue

                article_num = _id(p.get(cols["article"])) if cols.get("article") else None
                ean = _id(p.get(cols["upc"])) if cols.get("upc") else None

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
                cost = candidate.get("cost")
                cost_uom = str(candidate.get("cost_uom") or "").upper()
                currency = str(candidate.get("currency") or "USD").upper()
                mode = candidate.get("derivation_mode")

                if cost is None:
                    if candidate.get("candidate_present") and not cost_uom:
                        item["missing_explicit_cost_uom_candidates"] += 1
                    continue

                item["positive_cost_candidates"] += 1
                if mode == "TOTAL_VALUE_DIV_UNRESTRICTED":
                    item["derived_total_value_candidates"] += 1

                supported = False
                if currency != "USD":
                    item["unsupported_currency_candidates"] += 1
                elif not cost_uom:
                    item["missing_explicit_cost_uom_candidates"] += 1
                else:
                    supported = _uom_id(cur, cost_uom) is not None
                    if supported:
                        item["supported_cost_candidates"] += 1
                        if mode == "EXPLICIT_UNIT_COST":
                            item["explicit_supported_uom_candidates"] += 1
                        elif mode == "TOTAL_VALUE_DIV_UNRESTRICTED":
                            item["derived_supported_uom_candidates"] += 1
                    else:
                        item["unsupported_cost_uom_candidates"] += 1

                obs_date = (
                    _date(p.get(cols["date"])) if cols.get("date") else None
                ) or f.get("coverage_end_date") or f.get("filename_date_candidate")
                if obs_date is None and f.get("upload_timestamp"):
                    obs_date = f["upload_timestamp"].date()

                candidates = item["recent_candidates"]
                candidates.append(
                    {
                        "cost": cost,
                        "cost_uom": cost_uom or None,
                        "currency": currency,
                        "supported_cost_uom": supported,
                        "derivation_mode": mode,
                        "unrestricted_qty": candidate.get("unrestricted_qty"),
                        "total_value": candidate.get("total_value"),
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


def diagnose_oh_cost_schema(cur, *, candidate_row_limit: int = 20) -> dict[str, Any]:
    """Read-only explanation of OH cost schema and supported derivation modes."""

    candidate_row_limit = max(5, min(int(candidate_row_limit or 20), 100))
    cur.execute(
        """SELECT *
           FROM ingest_file
           WHERE source_type='on_hand'
           ORDER BY file_id"""
    )
    files = cur.fetchall()

    file_results: list[dict[str, Any]] = []
    total_sheets = 0
    scannable_sheets = 0
    skip_reason_counts: dict[str, int] = {}

    for file_row in files:
        file_id = int(file_row["file_id"])
        cur.execute(
            """SELECT *
               FROM ingest_sheet
               WHERE file_id=%s
               ORDER BY sheet_index,sheet_id""",
            (file_id,),
        )
        sheets = cur.fetchall()
        sheet_results: list[dict[str, Any]] = []

        for sh in sheets:
            total_sheets += 1
            sheet_id = int(sh["sheet_id"])
            header_row = sh.get("header_row_number")

            cur.execute(
                """SELECT COUNT(*) AS c,
                          MIN(source_row_number) AS first_row,
                          MAX(source_row_number) AS last_row
                   FROM raw_on_hand
                   WHERE sheet_id=%s""",
                (sheet_id,),
            )
            row_stats = cur.fetchone() or {}

            configured_header_payload = None
            configured_header_values: list[str] = []
            configured_matches: dict[str, Any] = {}
            supported_modes: list[str] = []

            if header_row:
                cur.execute(
                    """SELECT raw_payload
                       FROM raw_on_hand
                       WHERE sheet_id=%s AND source_row_number=%s
                       LIMIT 1""",
                    (sheet_id, header_row),
                )
                hr = cur.fetchone()
                if hr:
                    configured_header_payload = _j(hr["raw_payload"])
                    cols = _oh_cost_columns(
                        _header_map(configured_header_payload)
                    )
                    configured_header_values = [
                        str(v)
                        for v in configured_header_payload.values()
                        if v is not None and str(v).strip()
                    ][:40]
                    configured_matches = {
                        "article_column": cols.get("article"),
                        "upc_column": cols.get("upc"),
                        "cost_column": cols.get("explicit_cost"),
                        "cost_uom_column": cols.get("explicit_cost_uom"),
                        "unrestricted_qty_column": cols.get("unrestricted_qty"),
                        "base_uom_column": cols.get("base_uom"),
                        "total_value_column": cols.get("total_value"),
                        "currency_column": cols.get("currency"),
                        "date_column": cols.get("date"),
                    }
                    if cols.get("explicit_cost"):
                        supported_modes.append("EXPLICIT_UNIT_COST")
                    if (
                        cols.get("total_value")
                        and cols.get("unrestricted_qty")
                        and cols.get("base_uom")
                    ):
                        supported_modes.append(
                            "TOTAL_VALUE_DIV_UNRESTRICTED"
                        )

            identity_ok = bool(
                configured_matches.get("article_column")
                or configured_matches.get("upc_column")
            )
            if not header_row:
                skip_reason = "HEADER_ROW_NUMBER_MISSING"
            elif configured_header_payload is None:
                skip_reason = "CONFIGURED_HEADER_RAW_ROW_MISSING"
            elif not identity_ok:
                skip_reason = "ARTICLE_OR_UPC_COLUMN_NOT_MATCHED"
            elif not supported_modes:
                skip_reason = "NO_SUPPORTED_OH_COST_MODE_MATCHED"
            else:
                skip_reason = None
                scannable_sheets += 1

            if skip_reason:
                skip_reason_counts[skip_reason] = (
                    skip_reason_counts.get(skip_reason, 0) + 1
                )

            cur.execute(
                """SELECT source_row_number,raw_payload
                   FROM raw_on_hand
                   WHERE sheet_id=%s
                   ORDER BY source_row_number
                   LIMIT %s""",
                (sheet_id, candidate_row_limit),
            )
            candidate_headers: list[dict[str, Any]] = []
            for rr in cur.fetchall():
                payload = _j(rr["raw_payload"])
                cols = _oh_cost_columns(_header_map(payload))
                modes: list[str] = []
                if cols.get("explicit_cost"):
                    modes.append("EXPLICIT_UNIT_COST")
                if (
                    cols.get("total_value")
                    and cols.get("unrestricted_qty")
                    and cols.get("base_uom")
                ):
                    modes.append("TOTAL_VALUE_DIV_UNRESTRICTED")
                identity = bool(cols.get("article") or cols.get("upc"))
                score = (
                    (2 if identity else 0)
                    + len(modes) * 2
                    + (1 if cols.get("currency") else 0)
                    + (1 if cols.get("date") else 0)
                )
                if score >= 1:
                    candidate_headers.append(
                        {
                            "source_row_number": rr["source_row_number"],
                            "score": score,
                            "supported_modes": modes,
                            "article_column": cols.get("article"),
                            "upc_column": cols.get("upc"),
                            "cost_column": cols.get("explicit_cost"),
                            "cost_uom_column": cols.get("explicit_cost_uom"),
                            "unrestricted_qty_column": cols.get("unrestricted_qty"),
                            "base_uom_column": cols.get("base_uom"),
                            "total_value_column": cols.get("total_value"),
                            "currency_column": cols.get("currency"),
                            "date_column": cols.get("date"),
                            "values": [
                                str(v)
                                for v in payload.values()
                                if v is not None and str(v).strip()
                            ][:40],
                        }
                    )
            candidate_headers.sort(
                key=lambda x: (
                    int(x["score"]),
                    -int(x["source_row_number"]),
                ),
                reverse=True,
            )

            sheet_results.append(
                {
                    "sheet_id": sheet_id,
                    "sheet_index": sh.get("sheet_index"),
                    "sheet_name": sh.get("sheet_name"),
                    "configured_header_row_number": header_row,
                    "raw_row_count": int(row_stats.get("c") or 0),
                    "first_raw_row": row_stats.get("first_row"),
                    "last_raw_row": row_stats.get("last_row"),
                    "scannable_by_current_oh_cost_rule":
                        skip_reason is None,
                    "skip_reason": skip_reason,
                    "supported_cost_modes": supported_modes,
                    "configured_header_values":
                        configured_header_values,
                    "configured_matches": configured_matches,
                    "candidate_headers": candidate_headers[:8],
                }
            )

        file_results.append(
            {
                "file_id": file_id,
                "coverage_start_date":
                    file_row.get("coverage_start_date"),
                "coverage_end_date":
                    file_row.get("coverage_end_date"),
                "filename_date_candidate":
                    file_row.get("filename_date_candidate"),
                "upload_timestamp":
                    file_row.get("upload_timestamp"),
                "sheet_count": len(sheets),
                "sheets": sheet_results,
            }
        )

    return {
        "status": "OK",
        "source_type": "on_hand",
        "file_count": len(files),
        "sheet_count": total_sheets,
        "scannable_sheet_count": scannable_sheets,
        "skipped_sheet_count": total_sheets - scannable_sheets,
        "skip_reason_counts": skip_reason_counts,
        "files": file_results,
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

    official_uom_token_counts: dict[str, dict[str, int]] = {}
    official_repairable_family_count = 0
    official_unsupported_uom_family_count = 0
    for fid, evidence in official_cache.items():
        if int(evidence.get("repairable_official_rows") or 0) > 0:
            official_repairable_family_count += 1
        elif int(evidence.get("positive_with_unsupported_uom_rows") or 0) > 0:
            official_unsupported_uom_family_count += 1
        for token_row in evidence.get("source_cost_uom_tokens") or []:
            token = str(token_row.get("source_cost_uom") or "__MISSING__")
            slot = official_uom_token_counts.setdefault(
                token,
                {"row_count": 0, "supported_rows": 0},
            )
            slot["row_count"] += int(token_row.get("row_count") or 0)
            slot["supported_rows"] += int(token_row.get("supported_rows") or 0)

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
            "official_repairable_family_count": official_repairable_family_count,
            "official_unsupported_uom_family_count": official_unsupported_uom_family_count,
            "official_cost_uom_token_counts": official_uom_token_counts,
        },
        "article_manual": manual_stats,
        "items": items,
    }
