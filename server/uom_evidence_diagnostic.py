from __future__ import annotations

import re
from typing import Any

from article_manual_multitab_repair import _load_roster
from active_28d_uom_repair import PURE_ARTICLE_UOMS, RELATED_LB_PREFIXES, _related_prefix_evidence
from normalize import _numeric_key


def _norm_uom(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    return s or None


def _safe_error(stage: str, exc: Exception, **extra: Any) -> dict[str, Any]:
    return {
        "stage": stage,
        "error_type": type(exc).__name__,
        "error": str(exc),
        **extra,
    }


def _table_columns(cur, table: str) -> set[str]:
    cur.execute(f"SHOW COLUMNS FROM {table}")
    rows = cur.fetchall()
    result = set()
    for row in rows:
        field = row.get("Field") if isinstance(row, dict) else None
        if field:
            result.add(str(field))
    return result


def _known_uom(cur, code: str | None) -> bool:
    if not code:
        return False
    cur.execute(
        "SELECT 1 FROM dim_uom WHERE UPPER(uom_code)=UPPER(%s) LIMIT 1",
        (code,),
    )
    return bool(cur.fetchone())


def _historical_uom_rows(cur, upc_id: int) -> list[dict[str, Any]]:
    cols = _table_columns(cur, "selling_upc_uom_history")
    id_col = "upc_uom_id" if "upc_uom_id" in cols else None

    select_parts = []
    if id_col:
        select_parts.append(f"h.{id_col} AS upc_uom_id")
    select_parts.extend(
        [
            "su.uom_code AS selling_uom",
            "bu.uom_code AS base_uom",
            "h.base_qty_per_selling_unit" if "base_qty_per_selling_unit" in cols else "NULL AS base_qty_per_selling_unit",
            "h.mapping_status" if "mapping_status" in cols else "NULL AS mapping_status",
            "h.confidence" if "confidence" in cols else "NULL AS confidence",
            "h.resolution_method" if "resolution_method" in cols else "NULL AS resolution_method",
            "h.effective_to" if "effective_to" in cols else "NULL AS effective_to",
        ]
    )

    base_join = (
        "LEFT JOIN dim_uom bu ON bu.uom_id=h.base_uom_id"
        if "base_uom_id" in cols
        else "LEFT JOIN dim_uom bu ON 1=0"
    )
    order_by = f"h.{id_col} DESC" if id_col else "h.upc_id"

    cur.execute(
        f"""SELECT {", ".join(select_parts)}
            FROM selling_upc_uom_history h
            LEFT JOIN dim_uom su ON su.uom_id=h.selling_uom_id
            {base_join}
            WHERE h.upc_id=%s
            ORDER BY {order_by}""",
        (upc_id,),
    )
    return cur.fetchall()


def _manual_override(cur, ean_upc: str) -> dict[str, Any] | None:
    cur.execute(
        """SELECT ean_upc,article_number,selling_uom_code,base_uom_code,
                  base_qty_per_selling_unit,override_status,source_note
           FROM manual_upc_override
           WHERE ean_upc=%s
           ORDER BY override_id DESC
           LIMIT 1""",
        (ean_upc,),
    )
    return cur.fetchone()


def _family_peers(cur, family_id: int, ean_upc: str) -> list[dict[str, Any]]:
    cur.execute(
        """SELECT ean_upc,article_number,main_article_number,selling_uom,
                  base_uom,base_qty_per_selling_unit,quick_check_status,
                  blocking_reason
           FROM quick_check_current
           WHERE family_id=%s AND ean_upc<>%s
           ORDER BY
             CASE quick_check_status
               WHEN 'READY' THEN 0
               WHEN 'QA_HOLD' THEN 1
               WHEN 'HISTORICAL_ONLY' THEN 2
               ELSE 3
             END,
             ean_upc""",
        (family_id, ean_upc),
    )
    return cur.fetchall()


def _candidate_article_manual_rows(
    target: dict[str, Any],
    roster: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    key = _numeric_key(str(target["ean_upc"]))
    main = str(target["main_article_number"])
    result = []
    for row in roster:
        source_key = _numeric_key(str(row.get("source_upc") or ""))
        if not key or source_key != key:
            continue
        canonical_main = str(row.get("canonical_main") or "")
        result.append(
            {
                "source_upc": row.get("source_upc"),
                "article_number": row.get("article_number"),
                "canonical_main": row.get("canonical_main"),
                "family_match": canonical_main == main,
                "description": row.get("description"),
                "pack": row.get("pack"),
                "explicit_um": _norm_uom(row.get("selling_uom")),
                "sheet": row.get("sheet_name"),
            }
        )
    return result


def _classify(
    cur,
    target: dict[str, Any],
    manual_rows: list[dict[str, Any]],
    historical: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        override = _manual_override(cur, str(target["ean_upc"]))
    except Exception as exc:
        errors.append(_safe_error("manual_override", exc, ean_upc=str(target["ean_upc"])))
        override = None

    if override and str(override.get("override_status") or "").upper() == "CONFIRMED":
        uom = _norm_uom(override.get("selling_uom_code"))
        if uom:
            return {
                "classification": "CONFIRMED_MANUAL_OVERRIDE",
                "proposed_selling_uom": uom,
                "safe_to_auto_apply": True,
                "evidence": override,
            }

    same_family = [r for r in manual_rows if r.get("family_match")]
    explicit_candidates = sorted(
        {
            _norm_uom(r.get("explicit_um"))
            for r in same_family
            if _norm_uom(r.get("explicit_um"))
        }
    )
    explicit: list[str] = []
    for code in explicit_candidates:
        try:
            if code and _known_uom(cur, code):
                explicit.append(code)
        except Exception as exc:
            errors.append(_safe_error("known_uom", exc, ean_upc=str(target["ean_upc"]), uom=code))

    hist_codes = sorted(
        {
            _norm_uom(r.get("selling_uom"))
            for r in historical
            if _norm_uom(r.get("selling_uom"))
        }
    )

    if len(explicit) == 1:
        desired = explicit[0]
        conflicts = [x for x in hist_codes if x != desired]
        if not conflicts:
            return {
                "classification": "ARTICLE_MANUAL_EXACT_UPC_EXPLICIT_UM",
                "proposed_selling_uom": desired,
                "safe_to_auto_apply": True,
                "evidence_rows": same_family,
            }
        return {
            "classification": "HISTORICAL_UOM_CONFLICT",
            "proposed_selling_uom": desired,
            "safe_to_auto_apply": False,
            "historical_codes": hist_codes,
            "evidence_rows": same_family,
        }

    pure_pack_units = sorted(
        {
            re.sub(r"\s+", "", str(r.get("pack") or "").upper())
            for r in same_family
            if re.sub(r"\s+", "", str(r.get("pack") or "").upper()) in PURE_ARTICLE_UOMS
        }
    )
    if len(pure_pack_units) == 1:
        desired = pure_pack_units[0]
        conflicts = [x for x in hist_codes if x != desired]
        if not conflicts:
            return {
                "classification": "ARTICLE_MANUAL_EXACT_UPC_PURE_UNIT",
                "proposed_selling_uom": desired,
                "safe_to_auto_apply": True,
                "evidence_rows": same_family,
            }
        return {
            "classification": "HISTORICAL_UOM_CONFLICT",
            "proposed_selling_uom": desired,
            "safe_to_auto_apply": False,
            "historical_codes": hist_codes,
            "evidence_rows": same_family,
        }

    try:
        related = _related_prefix_evidence(cur, target)
    except Exception as exc:
        errors.append(_safe_error("related_prefix_evidence", exc, ean_upc=str(target["ean_upc"])))
        related = None

    if related:
        desired = str(related["uom"]).upper()
        conflicts = [x for x in hist_codes if x != desired]
        if not conflicts:
            return {
                "classification": "CONFIRMED_FAMILY_RELATED_PREFIX_LB",
                "proposed_selling_uom": desired,
                "safe_to_auto_apply": True,
                "evidence": related,
            }
        return {
            "classification": "HISTORICAL_UOM_CONFLICT",
            "proposed_selling_uom": desired,
            "safe_to_auto_apply": False,
            "historical_codes": hist_codes,
            "evidence": related,
        }

    return {
        "classification": "NEEDS_USER_CONFIRMATION",
        "proposed_selling_uom": None,
        "safe_to_auto_apply": False,
        "reason": (
            "No unique current Article Manual UOM evidence, no safe related-prefix "
            "LB evidence, and no confirmed manual override."
        ),
    }


def diagnose_uom_lineage(
    cur,
    upc: str | None = None,
    only_holds: bool = True,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []

    try:
        roster, roster_stats = _load_roster(cur, None)
    except Exception as exc:
        roster = []
        roster_stats = {"status": "UNAVAILABLE"}
        errors.append(_safe_error("article_manual_roster", exc))

    where = []
    params: list[Any] = []
    if upc:
        where.append("q.ean_upc=%s")
        params.append(str(upc))
    if only_holds:
        where.append("q.quick_check_status='QA_HOLD'")
        where.append("COALESCE(q.blocking_reason,'') LIKE '%SELLING_UOM_MISSING%'")

    sql = """SELECT q.upc_id,q.ean_upc,q.selling_description,q.article_number,
                    q.family_id,q.main_article_number,q.quick_check_status,
                    q.blocking_reason,q.selling_uom,q.base_uom,
                    q.base_qty_per_selling_unit,q.current_cost_per_base_uom,
                    q.current_cost_per_selling_unit,q.cost_source,q.cost_date,
                    q.pos_qty_7d,q.pos_qty_30d
             FROM quick_check_current q"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY q.family_id,q.ean_upc"

    cur.execute(sql, tuple(params))
    targets = cur.fetchall()

    items = []
    for raw_target in targets:
        target = dict(raw_target)
        target["upc_id"] = int(target["upc_id"])
        target["family_id"] = int(target["family_id"])
        item_errors: list[dict[str, Any]] = []

        try:
            historical = _historical_uom_rows(cur, target["upc_id"])
        except Exception as exc:
            historical = []
            err = _safe_error("historical_uom_rows", exc, ean_upc=str(target["ean_upc"]))
            errors.append(err)
            item_errors.append(err)

        try:
            manual_rows = _candidate_article_manual_rows(target, roster)
        except Exception as exc:
            manual_rows = []
            err = _safe_error("article_manual_exact_upc", exc, ean_upc=str(target["ean_upc"]))
            errors.append(err)
            item_errors.append(err)

        classification = _classify(cur, target, manual_rows, historical, errors)

        try:
            peers = _family_peers(cur, target["family_id"], str(target["ean_upc"]))
        except Exception as exc:
            peers = []
            err = _safe_error("family_peers", exc, ean_upc=str(target["ean_upc"]))
            errors.append(err)
            item_errors.append(err)

        items.append(
            {
                "ean_upc": str(target["ean_upc"]),
                "article_number": target.get("article_number"),
                "family_id": target["family_id"],
                "main_article_number": target.get("main_article_number"),
                "selling_description": target.get("selling_description"),
                "quick_check_status": target.get("quick_check_status"),
                "blocking_reason": target.get("blocking_reason"),
                "current_selling_uom": target.get("selling_uom"),
                "current_base_uom": target.get("base_uom"),
                "current_factor": target.get("base_qty_per_selling_unit"),
                "current_cost_per_base_uom": target.get("current_cost_per_base_uom"),
                "current_cost_per_selling_unit": target.get("current_cost_per_selling_unit"),
                "cost_source": target.get("cost_source"),
                "cost_date": target.get("cost_date"),
                "pos_qty_7d": target.get("pos_qty_7d"),
                "pos_qty_30d": target.get("pos_qty_30d"),
                "classification": classification,
                "article_manual_exact_upc_rows": manual_rows,
                "historical_uom_rows": historical,
                "family_peers": peers,
                "eligible_related_lb_prefix": str(target["ean_upc"])[:3] in RELATED_LB_PREFIXES,
                "diagnostic_errors": item_errors,
            }
        )

    counts: dict[str, int] = {}
    safe_count = 0
    for item in items:
        code = item["classification"]["classification"]
        counts[code] = counts.get(code, 0) + 1
        if item["classification"].get("safe_to_auto_apply"):
            safe_count += 1

    return {
        "status": "OK" if not errors else "PARTIAL_WITH_DIAGNOSTIC_ERRORS",
        "scope": {
            "upc": upc,
            "only_holds": only_holds,
            "row_count": len(items),
        },
        "article_manual": roster_stats,
        "summary": {
            "row_count": len(items),
            "safe_to_auto_apply_count": safe_count,
            "needs_review_count": len(items) - safe_count,
            "classification_counts": counts,
            "diagnostic_error_count": len(errors),
        },
        "diagnostic_errors": errors,
        "items": items,
    }
