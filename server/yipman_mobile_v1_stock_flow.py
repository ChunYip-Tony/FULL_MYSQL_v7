from __future__ import annotations

"""RC-only multi-window Stock Flow review for YipMan Mobile V1.

Family-level comparison of canonical 251-252 selling movement vs canonical
physical receipts on the exact same selected supported movement dates. Signals
are operational watch flags only; the Ordering engine remains the source of
final order qty.

True Stock refreshes may pass ``family_id`` to recalculate only the affected
Family instead of scanning every Family merely to update Effective OH.
"""

from decimal import Decimal
from typing import Any

from business_clock import completed_through_date
from data_coverage import source_data_days
from db import db_conn
from webapp_v2_runtime import (
    _delivery_pattern,
    _family_effective_oh,
    _family_receipt_events_bulk,
    _family_system_oh,
    _ordering_family_movement_metrics,
)


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _receipt_value(event: dict[str, Any], target_uom: str) -> tuple[Any, str | None]:
    base_uom = str(event.get("base_receipt_uom") or "").strip().upper()
    entry_uom = str(event.get("receipt_uom") or "").strip().upper()
    if target_uom and base_uom == target_uom and event.get("base_receipt_quantity") is not None:
        return event.get("base_receipt_quantity"), base_uom
    if target_uom and entry_uom == target_uom and event.get("receipt_quantity") is not None:
        return event.get("receipt_quantity"), entry_uom
    if event.get("base_receipt_quantity") is not None and base_uom:
        return event.get("base_receipt_quantity"), base_uom
    return event.get("receipt_quantity"), entry_uom or None


def _published_family_oh(children: list[dict[str, Any]]) -> dict[str, Any] | None:
    values: list[tuple[Decimal, str]] = []
    for child in children:
        qty = child.get("current_oh")
        uom = str(child.get("current_oh_uom") or "").strip().upper()
        if qty is None or not uom:
            continue
        values.append((_d(qty), uom))
    if not values:
        return None
    qtys = {x[0] for x in values}
    uoms = {x[1] for x in values}
    if len(qtys) != 1 or len(uoms) != 1:
        return None
    return {"status": "READY", "quantity": values[0][0], "uom": values[0][1], "source": "QUICK_CHECK_CURRENT_PUBLISHED_OH"}


def stock_flow_review(days: int = 7, limit: int = 80, family_id: int | None = None) -> dict[str, Any]:
    window = int(days or 7)
    if window not in {7, 14, 28}:
        raise ValueError("DAYS_MUST_BE_7_14_OR_28")
    lim = max(1, min(int(limit or 80), 120))
    target_family = int(family_id) if family_id not in (None, "") else None

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        movement_days = source_data_days(cur, "movement", limit=window, up_to=completed_through_date())
        supported_dates = {x["date"] for x in movement_days}
        day_count = len(movement_days)
        where_family = " AND family_id=%s" if target_family is not None else ""
        args = (target_family,) if target_family is not None else ()
        cur.execute(
            """SELECT family_id, MAX(main_article_number) AS family_article,
                      MAX(family_description) AS family_name, MAX(product_class) AS category,
                      MAX(family_movement_uom) AS published_family_movement_uom
               FROM quick_check_current
               WHERE family_id IS NOT NULL
                 AND COALESCE(quick_check_status,'') <> 'HISTORICAL_ONLY'""" + where_family +
            " GROUP BY family_id ORDER BY family_id",
            args,
        )
        families = [dict(x) for x in cur.fetchall()]
        fids = [int(x["family_id"]) for x in families if x.get("family_id") is not None]
        receipt_events = _family_receipt_events_bulk(cur, fids, data_day_limit=180) if fids else {}
        rows: list[dict[str, Any]] = []
        for family in families:
            fid = int(family["family_id"])
            published_uom = str(family.get("published_family_movement_uom") or "").strip().upper()
            movement = _ordering_family_movement_metrics(cur, fid, movement_days)
            sold_qty = movement.get("quantity")
            sold_uom = str(movement.get("uom") or published_uom or "").strip().upper() or None
            movement_status = str(movement.get("status") or "UNAVAILABLE")
            movement_basis = movement.get("basis")
            if sold_qty is None and movement_status == "UNAVAILABLE" and sold_uom and day_count:
                sold_qty, movement_status = Decimal("0"), "READY_ZERO_MOVEMENT"
                movement_basis = movement_basis or "NO_251_252_ROWS_IN_SELECTED_WINDOW"
            if sold_qty is None or not sold_uom:
                continue
            sold_d = _d(sold_qty)
            if sold_d < 0:
                continue
            events = [x for x in receipt_events.get(fid, []) if x.get("posting_date") is not None and x.get("receipt_quantity") is not None and _d(x.get("receipt_quantity")) > 0]
            events_in_window = [x for x in events if x.get("posting_date") in supported_dates]
            normalized = [_receipt_value(x, sold_uom) for x in events_in_window]
            receipt_uoms = {u for _, u in normalized if u}
            missing_qty = any(q is None for q, _ in normalized)
            if normalized and len(receipt_uoms) == 1 and not missing_qty:
                receipt_qty = sum((_d(q) for q, _ in normalized), Decimal("0")); receipt_uom = next(iter(receipt_uoms)); receipt_status = "READY"
            elif not normalized:
                receipt_qty = Decimal("0"); receipt_uom = sold_uom; receipt_status = "READY_ZERO_RECEIPTS"
            else:
                continue
            if receipt_uom != sold_uom:
                continue
            receipt_d = _d(receipt_qty); ratio = receipt_d / sold_d if sold_d > 0 else None; gap = receipt_d - sold_d
            signal = "NO_ACTIVITY" if sold_d == 0 and receipt_d == 0 else "OVER_ORDER_WATCH" if (sold_d == 0 and receipt_d > 0) or (ratio is not None and ratio >= Decimal("1.50")) else "UNDER_ORDER_WATCH" if ratio is not None and ratio <= Decimal("0.67") else "BALANCED"
            difference_pct = (gap / sold_d) * Decimal("100") if sold_d > 0 else None
            difference_abs_pct = abs(difference_pct) if difference_pct is not None else (Decimal("999999") if receipt_d > 0 else Decimal("0"))
            history = []
            for event in events_in_window[:2]:
                qty, uom = _receipt_value(event, sold_uom)
                history.append({"date": event.get("posting_date"), "quantity": qty, "uom": uom, "article_number": event.get("article_number")})
            pattern = _delivery_pattern(events, lookback_days=180)
            rows.append({
                "family_id": fid, "family_article": family.get("family_article"), "family_name": family.get("family_name"), "category": family.get("category"),
                "window_days": window, "supported_movement_day_count": day_count,
                "window_start_date": min(supported_dates) if supported_dates else None, "window_end_date": max(supported_dates) if supported_dates else None,
                "family_group_movement_qty": sold_d, "family_group_movement_uom": sold_uom,
                "family_group_avg_qty_day": sold_d / Decimal(day_count) if day_count else None,
                "family_receipt_qty": receipt_d, "family_receipt_uom": receipt_uom,
                "family_receipt_day_count": len({x.get("posting_date") for x in events_in_window if x.get("posting_date") is not None}),
                "receipt_minus_selling": gap, "receipt_to_selling_ratio": ratio,
                "receipt_vs_selling_difference_pct": difference_pct, "receipt_vs_selling_abs_difference_pct": difference_abs_pct,
                "receipt_over_selling_pct": difference_pct, "flow_signal": signal, "movement_status": movement_status, "movement_basis": movement_basis,
                "receipt_status": receipt_status, "family_receipt_history": history, "last_receipt_date": history[0].get("date") if history else None,
                "delivery_pattern_frequency": pattern.get("frequency"),
            })
        rows.sort(key=lambda r: (-float(r.get("receipt_vs_selling_abs_difference_pct") or 0), -abs(float(r.get("receipt_minus_selling") or 0)), -float(r.get("family_group_movement_qty") or 0), str(r.get("family_name") or "")))
        rows = rows[:lim]
        selected_ids = [int(x["family_id"]) for x in rows]
        children_by_family: dict[int, list[dict[str, Any]]] = {}; active_true_stock_ids: set[int] = set()
        if selected_ids:
            ph = ",".join(["%s"] * len(selected_ids))
            cur.execute(f"SELECT * FROM quick_check_current WHERE family_id IN ({ph}) ORDER BY family_id,upc_id", tuple(selected_ids))
            for child in cur.fetchall():
                if child.get("family_id") is not None:
                    children_by_family.setdefault(int(child["family_id"]), []).append(dict(child))
            cur.execute(f"SELECT DISTINCT family_id FROM manual_true_stock WHERE family_id IN ({ph}) AND scope_type='FAMILY' AND override_status='ACTIVE'", tuple(selected_ids))
            active_true_stock_ids = {int(x["family_id"]) for x in cur.fetchall() if x.get("family_id") is not None}
        for row in rows:
            fid = int(row["family_id"]); children = children_by_family.get(fid, []); published = _published_family_oh(children)
            effective = _family_effective_oh(cur, children) if fid in active_true_stock_ids else published or _family_system_oh(cur, children)
            if effective.get("status") == "READY" and effective.get("quantity") is not None:
                row["effective_oh"] = effective.get("quantity"); row["effective_oh_uom"] = effective.get("uom"); row["effective_oh_source"] = effective.get("source")
            else:
                row["effective_oh"] = None; row["effective_oh_uom"] = row.get("family_group_movement_uom"); row["effective_oh_source"] = effective.get("source")
        cur.close()
    counts = {"OVER_ORDER_WATCH": 0, "UNDER_ORDER_WATCH": 0, "BALANCED": 0, "NO_ACTIVITY": 0}
    for row in rows:
        key = str(row.get("flow_signal") or "")
        if key in counts: counts[key] += 1
    return {
        "contract_version": "YIPMAN_MOBILE_STOCK_FLOW_MULTIWINDOW_V2_EXACT_WINDOW", "window_days": window, "movement_day_count": day_count,
        "window_start_date": min(supported_dates) if supported_dates else None, "window_end_date": max(supported_dates) if supported_dates else None,
        "returned_count": len(rows), "default_sort": "ABS_RECEIPT_VS_SELLING_DIFFERENCE_PCT_DESC", "signal_counts": counts, "rows": rows,
        "family_scope": target_family,
        "rules": {"selling_movement": "FAMILY_251_MINUS_252_ON_EXACT_SELECTED_CANONICAL_MVT_DATES", "receipts": "CANONICAL_PHYSICAL_101_OR_109_ON_THE_SAME_EXACT_SELECTED_MVT_DATES", "comparison": "SAME_WINDOW_AND_SAME_FAMILY_UOM_ONLY", "over_order_watch": "RECEIPT_TO_SELLING_RATIO_AT_LEAST_1_50_OR_POSITIVE_RECEIPT_WITH_ZERO_SELLING", "under_order_watch": "RECEIPT_TO_SELLING_RATIO_AT_MOST_0_67_WITH_POSITIVE_SELLING", "signal_role": "FLOW_WATCH_NOT_FINAL_ORDER_SUGGESTION", "missing_source_dates_zero_filled": False},
    }
