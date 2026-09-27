from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from data_coverage import source_data_days


def _upca_check_digit(first11: str) -> str | None:
    if len(first11) != 11 or not first11.isdigit():
        return None
    digits = [int(x) for x in first11]
    total = sum(digits[0::2]) * 3 + sum(digits[1::2])
    return str((10 - (total % 10)) % 10)


def audit_product_identity(cur) -> dict[str, Any]:
    """Read-only current product-identity audit for Quick Check publishing."""

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    serving_holds: list[dict[str, Any]] = []

    pos_days_28 = source_data_days(
        cur,
        "sales_by_price_type",
        limit=28,
        up_to=date.today() - timedelta(days=1),
    )
    pos_file_ids = [int(x["file_id"]) for x in pos_days_28]
    pos_dates = [x["date"].isoformat() for x in pos_days_28]

    cur.execute(
        """
        SELECT canonical_key,
               COUNT(DISTINCT upc_id) AS upc_count,
               GROUP_CONCAT(DISTINCT ean_upc ORDER BY ean_upc SEPARATOR ',') AS ean_upcs,
               GROUP_CONCAT(DISTINCT upc_id ORDER BY upc_id SEPARATOR ',') AS upc_ids
        FROM (
            SELECT DISTINCT
                   su.upc_id,
                   su.ean_upc,
                   CASE
                     WHEN su.ean_upc REGEXP '^[0-9]+$'
                     THEN COALESCE(NULLIF(TRIM(LEADING '0' FROM su.ean_upc),''),'0')
                     ELSE UPPER(TRIM(su.ean_upc))
                   END AS canonical_key
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
            LEFT JOIN manual_upc_retirement mur
              ON mur.ean_upc=su.ean_upc
             AND mur.retirement_status='CONFIRMED'
            WHERE su.record_status='ACTIVE'
              AND mur.retirement_id IS NULL
        ) x
        GROUP BY canonical_key
        HAVING COUNT(DISTINCT upc_id)>1
        """
    )
    duplicate_canonical_active_upc = cur.fetchall()
    for row in duplicate_canonical_active_upc:
        blockers.append(
            {
                "code": "DUPLICATE_CANONICAL_ACTIVE_UPC",
                "canonical_key": str(row["canonical_key"]),
                "ean_upcs": str(row.get("ean_upcs") or "").split(","),
                "upc_ids": str(row.get("upc_ids") or "").split(","),
                "count": int(row["upc_count"]),
            }
        )

    cur.execute(
        """
        SELECT su.upc_id,su.ean_upc,
               COUNT(DISTINCT bau.article_id) AS article_count,
               COUNT(DISTINCT baf.family_id) AS family_count,
               GROUP_CONCAT(DISTINCT a.article_number ORDER BY a.article_number SEPARATOR ',') AS articles,
               GROUP_CONCAT(DISTINCT pf.main_article_number ORDER BY pf.main_article_number SEPARATOR ',') AS families
        FROM selling_upc su
        JOIN bridge_article_upc bau
          ON bau.upc_id=su.upc_id
         AND bau.mapping_status='CONFIRMED'
         AND bau.is_primary=TRUE
         AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
        JOIN article a ON a.article_id=bau.article_id
        JOIN bridge_article_family baf
          ON baf.article_id=bau.article_id
         AND baf.mapping_status='CONFIRMED'
         AND baf.is_primary=TRUE
         AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
        JOIN product_family pf ON pf.family_id=baf.family_id
        LEFT JOIN manual_upc_retirement mur
          ON mur.ean_upc=su.ean_upc
         AND mur.retirement_status='CONFIRMED'
        WHERE su.record_status='ACTIVE'
          AND mur.retirement_id IS NULL
        GROUP BY su.upc_id,su.ean_upc
        HAVING COUNT(DISTINCT bau.article_id)>1
            OR COUNT(DISTINCT baf.family_id)>1
        """
    )
    multi_article_upc = cur.fetchall()
    for row in multi_article_upc:
        blockers.append(
            {
                "code": "UPC_MULTI_AUTHORITATIVE_IDENTITY",
                "upc_id": int(row["upc_id"]),
                "ean_upc": str(row["ean_upc"]),
                "article_count": int(row["article_count"]),
                "family_count": int(row["family_count"]),
                "articles": str(row.get("articles") or "").split(","),
                "families": str(row.get("families") or "").split(","),
            }
        )

    cur.execute(
        """
        SELECT mur.ean_upc,mur.retirement_reason,
               su.upc_id,su.record_status,
               COALESCE((
                 SELECT COUNT(*) FROM bridge_article_upc bau
                 WHERE bau.upc_id=su.upc_id
                   AND bau.mapping_status='CONFIRMED'
                   AND bau.is_primary=TRUE
                   AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
               ),0) AS active_article_links,
               COALESCE((
                 SELECT COUNT(*) FROM selling_upc_uom_history h
                 WHERE h.upc_id=su.upc_id
                   AND h.mapping_status='CONFIRMED'
                   AND (h.effective_to IS NULL OR h.effective_to>CURRENT_TIMESTAMP(6))
               ),0) AS active_uom_rows,
               COALESCE((
                 SELECT COUNT(*) FROM quick_check_current q
                 WHERE q.ean_upc=mur.ean_upc OR q.upc_id=su.upc_id
               ),0) AS quick_check_rows
        FROM manual_upc_retirement mur
        LEFT JOIN selling_upc su ON su.ean_upc=mur.ean_upc
        WHERE mur.retirement_status='CONFIRMED'
        ORDER BY mur.retirement_id
        """
    )
    retirement_checks = cur.fetchall()
    retirement_regressions: list[dict[str, Any]] = []
    for row in retirement_checks:
        regressed = (
            (row.get("record_status") is not None and str(row.get("record_status")).upper() != "RETIRED")
            or int(row.get("active_article_links") or 0) > 0
            or int(row.get("active_uom_rows") or 0) > 0
            or int(row.get("quick_check_rows") or 0) > 0
        )
        item = {
            "ean_upc": str(row["ean_upc"]),
            "retirement_reason": row.get("retirement_reason"),
            "upc_id": int(row["upc_id"]) if row.get("upc_id") is not None else None,
            "record_status": row.get("record_status"),
            "active_article_links": int(row.get("active_article_links") or 0),
            "active_uom_rows": int(row.get("active_uom_rows") or 0),
            "quick_check_rows": int(row.get("quick_check_rows") or 0),
            "pass": not regressed,
        }
        if regressed:
            retirement_regressions.append(item)
            blockers.append({"code": "RETIRED_UPC_RESURRECTED", **item})

    cur.execute(
        """
        SELECT su.upc_id,su.ean_upc,
               COUNT(
                 DISTINCT CONCAT(
                   CASE WHEN UPPER(du.uom_code) IN ('PAC','PACK') THEN 'PACK' ELSE UPPER(du.uom_code) END,'|',
                   COALESCE(CASE WHEN UPPER(bu.uom_code) IN ('PAC','PACK') THEN 'PACK' ELSE UPPER(bu.uom_code) END,'NULL'),'|',
                   COALESCE(CAST(h.base_qty_per_selling_unit AS CHAR),'NULL')
                 )
               ) AS variant_count,
               GROUP_CONCAT(
                 DISTINCT CONCAT(
                   du.uom_code,'/',
                   COALESCE(bu.uom_code,'NULL'),'/',
                   COALESCE(CAST(h.base_qty_per_selling_unit AS CHAR),'NULL')
                 )
                 ORDER BY du.uom_code SEPARATOR ','
               ) AS variants
        FROM selling_upc su
        JOIN bridge_article_upc bau
          ON bau.upc_id=su.upc_id
         AND bau.mapping_status='CONFIRMED'
         AND bau.is_primary=TRUE
         AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
        JOIN selling_upc_uom_history h
          ON h.upc_id=su.upc_id
         AND h.mapping_status='CONFIRMED'
         AND (h.effective_to IS NULL OR h.effective_to>CURRENT_TIMESTAMP(6))
        JOIN dim_uom du ON du.uom_id=h.selling_uom_id
        LEFT JOIN dim_uom bu ON bu.uom_id=h.base_uom_id
        LEFT JOIN manual_upc_retirement mur
          ON mur.ean_upc=su.ean_upc
         AND mur.retirement_status='CONFIRMED'
        WHERE su.record_status='ACTIVE'
          AND mur.retirement_id IS NULL
        GROUP BY su.upc_id,su.ean_upc
        HAVING COUNT(
          DISTINCT CONCAT(
            CASE WHEN UPPER(du.uom_code) IN ('PAC','PACK') THEN 'PACK' ELSE UPPER(du.uom_code) END,'|',
            COALESCE(CASE WHEN UPPER(bu.uom_code) IN ('PAC','PACK') THEN 'PACK' ELSE UPPER(bu.uom_code) END,'NULL'),'|',
            COALESCE(CAST(h.base_qty_per_selling_unit AS CHAR),'NULL')
          )
        )>1
        """
    )
    uom_conflicts = cur.fetchall()
    for row in uom_conflicts:
        blockers.append(
            {
                "code": "UPC_CURRENT_UOM_CONFLICT",
                "upc_id": int(row["upc_id"]),
                "ean_upc": str(row["ean_upc"]),
                "variant_count": int(row["variant_count"]),
                "variants": str(row.get("variants") or "").split(","),
            }
        )

    active_without_identity: list[dict[str, Any]] = []
    source_or_historical_without_identity: list[dict[str, Any]] = []
    if pos_file_ids:
        ph = ",".join(["%s"] * len(pos_file_ids))
        cur.execute(
            f"""
            SELECT su.upc_id,su.ean_upc,
                   COALESCE(SUM(CASE
                       WHEN spo.temporal_grain='SINGLE_DATE'
                        AND spo.file_id IN ({ph})
                       THEN spo.sold_quantity ELSE 0 END),0) AS recent_qty
            FROM selling_upc su
            LEFT JOIN bridge_article_upc bau
              ON bau.upc_id=su.upc_id
             AND bau.mapping_status='CONFIRMED'
             AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
            LEFT JOIN manual_upc_retirement mur
              ON mur.ean_upc=su.ean_upc
             AND mur.retirement_status='CONFIRMED'
            LEFT JOIN sales_period_observation spo
              ON spo.upc_id=su.upc_id
            WHERE su.record_status='ACTIVE'
              AND mur.retirement_id IS NULL
              AND bau.article_upc_id IS NULL
            GROUP BY su.upc_id,su.ean_upc
            ORDER BY su.upc_id
            """,
            tuple(pos_file_ids),
        )
    else:
        cur.execute(
            """
            SELECT su.upc_id,su.ean_upc,0 AS recent_qty
            FROM selling_upc su
            LEFT JOIN bridge_article_upc bau
              ON bau.upc_id=su.upc_id
             AND bau.mapping_status='CONFIRMED'
             AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
            LEFT JOIN manual_upc_retirement mur
              ON mur.ean_upc=su.ean_upc
             AND mur.retirement_status='CONFIRMED'
            WHERE su.record_status='ACTIVE'
              AND mur.retirement_id IS NULL
              AND bau.article_upc_id IS NULL
            ORDER BY su.upc_id
            """
        )
    for row in cur.fetchall():
        item = {
            "upc_id": int(row["upc_id"]),
            "ean_upc": str(row["ean_upc"]),
            "recent_pos_qty_28_valid_days": str(row.get("recent_qty") or 0),
        }
        if row.get("recent_qty") is not None and row["recent_qty"] > 0:
            active_without_identity.append(item)
            blockers.append({"code": "ACTIVE_UPC_WITHOUT_AUTHORITATIVE_IDENTITY", **item})
        else:
            source_or_historical_without_identity.append(item)
            warnings.append({"code": "SOURCE_OR_HISTORICAL_UPC_WITHOUT_IDENTITY", **item})

    cur.execute(
        """
        SELECT q.upc_id,q.ean_upc,q.article_id,q.article_number,q.family_id,q.main_article_number,
               q.quick_check_status,q.selling_uom,
               CASE WHEN mur.retirement_id IS NULL THEN 0 ELSE 1 END AS is_retired,
               COUNT(DISTINCT bau.article_id) AS current_article_count,
               COUNT(DISTINCT baf.family_id) AS current_family_count,
               SUM(CASE WHEN bau.article_id=q.article_id AND baf.family_id=q.family_id THEN 1 ELSE 0 END) AS exact_identity_matches
        FROM quick_check_current q
        LEFT JOIN manual_upc_retirement mur
          ON mur.ean_upc=q.ean_upc
         AND mur.retirement_status='CONFIRMED'
        LEFT JOIN bridge_article_upc bau
          ON bau.upc_id=q.upc_id
         AND bau.mapping_status='CONFIRMED'
         AND bau.is_primary=TRUE
         AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
        LEFT JOIN bridge_article_family baf
          ON baf.article_id=bau.article_id
         AND baf.mapping_status='CONFIRMED'
         AND baf.is_primary=TRUE
         AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
        GROUP BY q.upc_id,q.ean_upc,q.article_id,q.article_number,q.family_id,q.main_article_number,
                 q.quick_check_status,q.selling_uom,mur.retirement_id
        HAVING is_retired=1
            OR current_article_count<>1
            OR current_family_count<>1
            OR exact_identity_matches=0
        ORDER BY q.ean_upc
        """
    )
    serving_identity_regressions = cur.fetchall()
    for row in serving_identity_regressions:
        blockers.append(
            {
                "code": "SERVING_IDENTITY_NOT_AUTHORITATIVE",
                "upc_id": int(row["upc_id"]),
                "ean_upc": str(row["ean_upc"]),
                "article_number": row.get("article_number"),
                "family_id": int(row["family_id"]) if row.get("family_id") is not None else None,
                "main_article_number": row.get("main_article_number"),
                "quick_check_status": row.get("quick_check_status"),
                "is_retired": bool(row.get("is_retired")),
                "current_article_count": int(row.get("current_article_count") or 0),
                "current_family_count": int(row.get("current_family_count") or 0),
                "exact_identity_matches": int(row.get("exact_identity_matches") or 0),
            }
        )

    cur.execute(
        """
        SELECT ean_upc,article_number,family_id,main_article_number,
               quick_check_status,blocking_reason
        FROM quick_check_current
        WHERE quick_check_status IN ('READY','QA_HOLD')
          AND (selling_uom IS NULL OR TRIM(selling_uom)='')
        ORDER BY ean_upc
        """
    )
    current_active_missing_uom = cur.fetchall()
    for row in current_active_missing_uom:
        serving_holds.append(
            {
                "code": "CURRENT_ACTIVE_SELLING_UOM_MISSING",
                "ean_upc": str(row["ean_upc"]),
                "article_number": row.get("article_number"),
                "family_id": int(row["family_id"]) if row.get("family_id") is not None else None,
                "main_article_number": row.get("main_article_number"),
                "quick_check_status": row.get("quick_check_status"),
                "blocking_reason": row.get("blocking_reason"),
            }
        )

    cur.execute(
        """
        SELECT su.ean_upc,baf.family_id,a.article_number,
               q.selling_uom,q.quick_check_status
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
        LEFT JOIN quick_check_current q ON q.upc_id=su.upc_id
        LEFT JOIN manual_upc_retirement mur
          ON mur.ean_upc=su.ean_upc
         AND mur.retirement_status='CONFIRMED'
        WHERE su.record_status='ACTIVE'
          AND mur.retirement_id IS NULL
        ORDER BY baf.family_id,su.ean_upc
        """
    )
    serving = cur.fetchall()
    by_upc = {str(x["ean_upc"]): x for x in serving}
    safe_alias_candidates: list[dict[str, Any]] = []
    for short, row in by_upc.items():
        if len(short) != 11 or not short.isdigit():
            continue
        digit = _upca_check_digit(short)
        if digit is None:
            continue
        long_upc = short + digit
        other = by_upc.get(long_upc)
        if not other:
            continue
        same_family = row.get("family_id") == other.get("family_id")
        def _norm_uom(v):
            x = (v or "").upper()
            return "PACK" if x in {"PAC", "PACK"} else x
        same_uom = _norm_uom(row.get("selling_uom")) == _norm_uom(other.get("selling_uom"))
        short_status = row.get("quick_check_status")
        long_status = other.get("quick_check_status")
        short_current = short_status in {"READY", "QA_HOLD"}
        long_current = long_status in {"READY", "QA_HOLD"}
        both_current = short_current and long_current
        one_current_one_historical = (short_current != long_current)
        item = {
            "short_upc": short,
            "valid_upca": long_upc,
            "same_family": same_family,
            "same_selling_uom": same_uom,
            "merge_candidate": bool(same_family and same_uom),
            "family_id": int(row["family_id"]) if row.get("family_id") is not None else None,
            "short_selling_uom": row.get("selling_uom"),
            "long_selling_uom": other.get("selling_uom"),
            "short_quick_check_status": short_status,
            "long_quick_check_status": long_status,
            "short_current": short_current,
            "long_current": long_current,
            "both_current": both_current,
            "one_current_one_historical": one_current_one_historical,
        }
        safe_alias_candidates.append(item)
        if both_current:
            if item["merge_candidate"]:
                blockers.append({"code": "DUPLICATE_UPCA_SHORT_LONG_CURRENT", **item})
            else:
                blockers.append({"code": "UPCA_SHORT_LONG_CURRENT_IDENTITY_CONFLICT", **item})
        elif one_current_one_historical:
            warnings.append({"code": "UPCA_CURRENT_HISTORICAL_ALIAS_CANDIDATE", **item})
        else:
            warnings.append({"code": "HISTORICAL_UPCA_SHORT_LONG_PAIR", **item})

    cur.execute(
        """
        SELECT o.ean_upc,o.article_number,o.selling_uom_code,o.base_uom_code,
               o.base_qty_per_selling_unit,
               opf.main_article_number AS expected_main_article_number,
               q.article_number AS qc_article_number,
               q.main_article_number AS qc_main_article_number,
               q.selling_uom AS qc_selling_uom,
               q.base_uom AS qc_base_uom,
               q.base_qty_per_selling_unit AS qc_factor,
               q.quick_check_status
        FROM manual_upc_override o
        LEFT JOIN article oa ON oa.article_number=o.article_number
        LEFT JOIN bridge_article_family obaf
          ON obaf.article_id=oa.article_id
         AND obaf.mapping_status='CONFIRMED'
         AND obaf.is_primary=TRUE
         AND (obaf.valid_to IS NULL OR obaf.valid_to>CURRENT_TIMESTAMP(6))
        LEFT JOIN product_family opf ON opf.family_id=obaf.family_id
        LEFT JOIN quick_check_current q ON q.ean_upc=o.ean_upc
        WHERE o.override_status='CONFIRMED'
        ORDER BY o.override_id
        """
    )
    override_checks: list[dict[str, Any]] = []
    for row in cur.fetchall():
        pass_identity = (
            row.get("expected_main_article_number") is not None
            and row.get("qc_main_article_number") is not None
            and str(row.get("qc_main_article_number"))
                == str(row.get("expected_main_article_number"))
        )
        pass_selling_uom = (
            row.get("selling_uom_code") is None
            or (
                row.get("qc_selling_uom") is not None
                and ("PACK" if str(row.get("qc_selling_uom")).upper() in {"PAC","PACK"} else str(row.get("qc_selling_uom")).upper())
                == ("PACK" if str(row.get("selling_uom_code")).upper() in {"PAC","PACK"} else str(row.get("selling_uom_code")).upper())
            )
        )
        pass_base_uom = (
            row.get("base_uom_code") is None
            or (
                row.get("qc_base_uom") is not None
                and str(row.get("qc_base_uom")).upper()
                == str(row.get("base_uom_code")).upper()
            )
        )
        pass_factor = (
            row.get("base_qty_per_selling_unit") is None
            or (
                row.get("qc_factor") is not None
                and row.get("qc_factor") == row.get("base_qty_per_selling_unit")
            )
        )
        item = {
            "ean_upc": str(row["ean_upc"]),
            "source_article_number": row.get("article_number"),
            "expected_main_article_number": row.get("expected_main_article_number"),
            "expected_selling_uom": row.get("selling_uom_code"),
            "expected_base_uom": row.get("base_uom_code"),
            "expected_factor": str(row.get("base_qty_per_selling_unit"))
            if row.get("base_qty_per_selling_unit") is not None
            else None,
            "qc_article_number": row.get("qc_article_number"),
            "qc_main_article_number": row.get("qc_main_article_number"),
            "qc_selling_uom": row.get("qc_selling_uom"),
            "qc_base_uom": row.get("qc_base_uom"),
            "qc_factor": str(row.get("qc_factor")) if row.get("qc_factor") is not None else None,
            "quick_check_status": row.get("quick_check_status"),
            "pass": bool(pass_identity and pass_selling_uom and pass_base_uom and pass_factor),
        }
        override_checks.append(item)
        if not item["pass"]:
            blockers.append({"code": "MANUAL_UPC_OVERRIDE_NOT_ENFORCED", **item})

    return {
        "pass": len(blockers) == 0,
        "summary": {
            "blocking_count": len(blockers),
            "warning_count": len(warnings),
            "serving_hold_count": len(serving_holds),
            "duplicate_canonical_active_upc_count": len(duplicate_canonical_active_upc),
            "multi_article_upc_count": len(multi_article_upc),
            "retirement_regression_count": len(retirement_regressions),
            "uom_conflict_count": len(uom_conflicts),
            "active_without_identity_count": len(active_without_identity),
            "source_or_historical_without_identity_count": len(source_or_historical_without_identity),
            "serving_identity_regression_count": len(serving_identity_regressions),
            "current_active_missing_uom_count": len(current_active_missing_uom),
            "upca_short_long_pair_count": len(safe_alias_candidates),
            "upca_current_current_pair_count": sum(1 for x in safe_alias_candidates if x.get("both_current")),
            "upca_current_historical_pair_count": sum(1 for x in safe_alias_candidates if x.get("one_current_one_historical")),
            "upca_historical_historical_pair_count": sum(
                1 for x in safe_alias_candidates
                if not x.get("short_current") and not x.get("long_current")
            ),
            "manual_override_count": len(override_checks),
            "pos_28_valid_data_day_count": len(pos_days_28),
        },
        "pos_28_valid_data_days": pos_dates,
        "blockers": blockers,
        "warnings": warnings,
        "serving_holds": serving_holds,
        "duplicate_canonical_active_upc": duplicate_canonical_active_upc,
        "multi_article_upc": multi_article_upc,
        "retirement_checks": retirement_checks,
        "uom_conflicts": uom_conflicts,
        "active_without_identity": active_without_identity,
        "source_or_historical_without_identity": source_or_historical_without_identity,
        "serving_identity_regressions": serving_identity_regressions,
        "current_active_missing_uom": current_active_missing_uom,
        "safe_upca_alias_candidates": safe_alias_candidates,
        "manual_override_checks": override_checks,
    }
