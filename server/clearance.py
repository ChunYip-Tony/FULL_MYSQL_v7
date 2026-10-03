from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from business_clock import business_today
from db import db_conn
from phase3 import _current_price as _live_current_price
from quick_check_app import get_quick_check_detail


STORE_PRICE_ENDINGS = (
    Decimal("0.29"),
    Decimal("0.49"),
    Decimal("0.59"),
    Decimal("0.69"),
    Decimal("0.79"),
    Decimal("0.99"),
)


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _positive(value: Any) -> Decimal | None:
    if value is None:
        return None
    v = _d(value)
    return v if v > 0 else None


def _ensure_clearance_table(cur) -> None:
    cur.execute(
        """CREATE TABLE IF NOT EXISTS yipman_clearance_plan (
             clearance_plan_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
             ean_upc VARCHAR(32) NOT NULL,
             expiry_date DATE NOT NULL,
             expiring_quantity DECIMAL(18,4) NOT NULL,
             uom_code VARCHAR(16) NOT NULL,
             plan_status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
             note VARCHAR(500) NULL,
             created_by VARCHAR(128) NULL,
             updated_by VARCHAR(128) NULL,
             created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
             updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
               ON UPDATE CURRENT_TIMESTAMP(6),
             UNIQUE KEY uq_yipman_clearance_upc_expiry (ean_upc,expiry_date),
             KEY idx_yipman_clearance_status_expiry (plan_status,expiry_date)
           )"""
    )


def _retail_clearance_price(
    current_price: Decimal,
    markdown_pct: Decimal,
    *,
    floor_price: Decimal | None,
) -> Decimal | None:
    if current_price <= 0:
        return None
    raw = current_price * (Decimal("1") - markdown_pct)
    floor = max(Decimal("0.01"), floor_price or Decimal("0.01"))
    candidates: list[Decimal] = []
    top = int(current_price.to_integral_value(rounding=ROUND_HALF_UP)) + 2
    for whole in range(0, max(2, top + 1)):
        for ending in STORE_PRICE_ENDINGS:
            p = Decimal(whole) + ending
            if p >= floor and p < current_price - Decimal("0.01"):
                candidates.append(p)
    if not candidates:
        return None
    under = [p for p in candidates if p <= raw]
    if under:
        return max(under)
    return min(candidates)


def _price_gp_pct(price: Decimal | None, cost: Decimal | None) -> Decimal | None:
    if price is None or cost is None or price <= 0:
        return None
    return (price - cost) / price


def _item_context(upc: str) -> dict[str, Any]:
    detail = get_quick_check_detail(upc)
    if not detail:
        raise KeyError("CLEARANCE_UPC_NOT_FOUND")
    item = dict(detail.get("item") or {})
    ean = str(item.get("ean_upc") or upc or "").strip()
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        live = _live_current_price(cur, int(item["upc_id"]), ean)
        cur.close()
    effective = dict(detail.get("effective_oh") or {})
    system_oh = dict(detail.get("system_oh") or {})
    true_input = dict(detail.get("true_stock_input") or {})
    return {
        "upc": ean,
        "upc_id": item.get("upc_id"),
        "name": item.get("selling_description"),
        "family_id": item.get("family_id"),
        "family_article_number": item.get("main_article_number"),
        "family_name": item.get("family_description"),
        "category": item.get("product_class"),
        "selling_uom": item.get("selling_uom"),
        "current_price": live.get("price") if live else None,
        "current_price_type": live.get("type") if live else None,
        "current_price_source": live.get("source") if live else None,
        "current_price_asof_date": live.get("date") if live else None,
        "current_cost": item.get("current_cost_per_selling_unit"),
        "cost_source": item.get("cost_source"),
        "cost_date": item.get("cost_date"),
        "velocity_7d": item.get("upc_velocity_7d"),
        "qty_7d": item.get("pos_qty_7d"),
        "effective_oh": effective.get("quantity"),
        "effective_oh_uom": effective.get("uom"),
        "effective_oh_source": effective.get("source"),
        "system_oh": system_oh.get("quantity"),
        "system_oh_uom": system_oh.get("uom"),
        "active_true_stock": detail.get("active_true_stock"),
        "required_true_stock_uom": true_input.get("required_uom"),
    }


def _stage_dates(today: date, expiry: date) -> list[tuple[date, date, str]]:
    if expiry < today:
        return [(today, today, "EXPIRED / DISPOSITION REVIEW")]
    days = (expiry - today).days + 1
    if days <= 1:
        return [(today, expiry, "FINAL DAY")]
    if days == 2:
        return [
            (today, today, "CLEARANCE NOW"),
            (expiry, expiry, "FINAL DAY"),
        ]
    if days <= 4:
        first_end = max(today, expiry - timedelta(days=2))
        return [
            (today, first_end, "CLEARANCE NOW"),
            (first_end + timedelta(days=1), expiry - timedelta(days=1), "ACCELERATE"),
            (expiry, expiry, "FINAL DAY"),
        ]
    return [
        (today, expiry - timedelta(days=3), "CLEARANCE NOW"),
        (expiry - timedelta(days=2), expiry - timedelta(days=1), "ACCELERATE"),
        (expiry, expiry, "FINAL DAY"),
    ]


def _analyze_plan(plan: dict[str, Any]) -> dict[str, Any]:
    ctx = _item_context(str(plan.get("ean_upc") or ""))
    today = business_today()
    expiry = plan.get("expiry_date")
    if not isinstance(expiry, date):
        expiry = date.fromisoformat(str(expiry)[:10])
    expiring_qty = _d(plan.get("expiring_quantity"))
    uom = str(plan.get("uom_code") or "").strip().upper()
    effective_uom = str(ctx.get("effective_oh_uom") or "").strip().upper()
    effective_qty = (
        _d(ctx.get("effective_oh"))
        if ctx.get("effective_oh") is not None and effective_uom == uom
        else None
    )
    clearance_qty = (
        min(expiring_qty, max(Decimal("0"), effective_qty))
        if effective_qty is not None
        else expiring_qty
    )
    days_to_expiry = (expiry - today).days
    sell_days = max(1, days_to_expiry + 1)
    velocity = (
        max(Decimal("0"), _d(ctx.get("velocity_7d")))
        if ctx.get("velocity_7d") is not None
        else Decimal("0")
    )
    required_velocity = (
        clearance_qty / Decimal(sell_days)
        if clearance_qty > 0
        else Decimal("0")
    )
    pressure = (
        required_velocity / velocity
        if velocity > 0
        else None
    )
    current_price = _positive(ctx.get("current_price"))
    current_cost = _positive(ctx.get("current_cost"))
    current_type = str(ctx.get("current_price_type") or "").strip().upper()

    warnings: list[str] = []
    if effective_qty is not None and expiring_qty > effective_qty:
        warnings.append(
            "EXPIRING_QTY_EXCEEDS_EFFECTIVE_OH; CLEARANCE TARGET CAPPED_TO_TRUE_EFFECTIVE_STOCK"
        )
    if effective_uom and uom and effective_uom != uom:
        warnings.append("EXPIRING_QTY_UOM_DOES_NOT_MATCH_EFFECTIVE_OH_UOM")
    if current_type == "SALE":
        warnings.append("SALE_IS_COMPANY_CONTROLLED; DO_NOT_OVERRIDE_PRICE_OR_PERIOD")
    if ctx.get("active_true_stock"):
        warnings.append("EFFECTIVE_OH_USES_ACTIVE_TRUE_STOCK")

    if days_to_expiry < 0:
        action = "EXPIRED_DISPOSITION_REVIEW"
        action_label = "EXPIRED · REVIEW DISPOSITION"
    elif clearance_qty <= 0:
        action = "CLOSE_CLEARANCE"
        action_label = "CLEAR / CLOSE"
    elif current_type == "SALE":
        action = "SALE_LOCKED"
        action_label = "SALE LOCKED"
    elif current_price is None:
        action = "REVIEW_PRICE_DATA"
        action_label = "REVIEW PRICE DATA"
    else:
        action = "START_CLEARANCE_NOW"
        action_label = "START CLEARANCE"
        if velocity > 0 and required_velocity <= velocity and sell_days >= 4:
            action = "LIGHT_CLEARANCE_MONITOR"
            action_label = "LIGHT CLEARANCE / MONITOR"

    if pressure is None:
        base_markdown = Decimal("0.30")
    elif pressure <= Decimal("1.00"):
        base_markdown = Decimal("0.08")
    elif pressure <= Decimal("1.50"):
        base_markdown = Decimal("0.12")
    elif pressure <= Decimal("2.00"):
        base_markdown = Decimal("0.18")
    elif pressure <= Decimal("3.00"):
        base_markdown = Decimal("0.24")
    else:
        base_markdown = Decimal("0.30")
    if sell_days <= 3:
        base_markdown = max(base_markdown, Decimal("0.20"))
    if sell_days <= 1:
        base_markdown = max(base_markdown, Decimal("0.30"))

    floor = (
        current_cost + Decimal("0.01")
        if current_cost is not None
        else Decimal("0.01")
    )
    stages: list[dict[str, Any]] = []
    schedule = _stage_dates(today, expiry)
    for idx, (start, end, label) in enumerate(schedule):
        markdown = min(
            Decimal("0.50"),
            base_markdown + Decimal("0.10") * Decimal(idx),
        )
        price = (
            _retail_clearance_price(
                current_price,
                markdown,
                floor_price=floor,
            )
            if current_price is not None and current_type != "SALE"
            else None
        )
        stages.append({
            "stage": idx + 1,
            "label": label,
            "start_date": start,
            "end_date": end,
            "markdown_pct": markdown,
            "suggested_price": price,
            "gp_pct_at_current_cost": _price_gp_pct(price, current_cost),
            "margin_floor_applied": bool(
                price is not None
                and current_cost is not None
                and price <= current_cost + Decimal("0.10")
            ),
            "required_daily_qty_reference": required_velocity,
        })

    if current_type == "SALE":
        stages = [{
            "stage": 1,
            "label": "COMPANY SALE ACTIVE",
            "start_date": today,
            "end_date": expiry,
            "markdown_pct": None,
            "suggested_price": None,
            "gp_pct_at_current_cost": None,
            "margin_floor_applied": False,
            "required_daily_qty_reference": required_velocity,
        }]

    return {
        **plan,
        **ctx,
        "price_policy_type": "CLEARANCE",
        "days_to_expiry": days_to_expiry,
        "sell_days_including_today": sell_days,
        "clearance_target_quantity": clearance_qty,
        "required_daily_velocity": required_velocity,
        "current_velocity_7d": velocity,
        "velocity_pressure_ratio": pressure,
        "projected_sell_days_at_current_velocity": (
            clearance_qty / velocity if velocity > 0 else None
        ),
        "action": action,
        "action_label": action_label,
        "warnings": warnings,
        "stages": stages,
        "clearance_rule": (
            "USER_ENTERED_EXPIRY_AND_EXPIRING_QTY; EFFECTIVE_OH_USES_TRUE_STOCK_WHEN_ACTIVE; "
            "PRICE_PLAN_STEPS_DOWN_AS_EXPIRY_APPROACHES; AUTOMATIC_SUGGESTIONS_DO_NOT_CROSS_CURRENT_COST; "
            "SALE_PRICE_AND_PERIOD_ARE_COMPANY_CONTROLLED"
        ),
    }


def save_clearance_plan(
    *,
    ean_upc: str,
    expiry_date: date,
    expiring_quantity: Decimal,
    uom: str,
    actor: str | None,
    note: str | None = None,
    clearance_plan_id: int | None = None,
) -> dict[str, Any]:
    upc = str(ean_upc or "").strip()
    qty = _d(expiring_quantity)
    unit = str(uom or "").strip().upper()
    if not upc:
        raise ValueError("CLEARANCE_UPC_REQUIRED")
    if qty <= 0:
        raise ValueError("CLEARANCE_EXPIRING_QTY_MUST_BE_POSITIVE")
    if not unit:
        raise ValueError("CLEARANCE_UOM_REQUIRED")

    ctx = _item_context(upc)
    required_uom = str(
        ctx.get("required_true_stock_uom")
        or ctx.get("effective_oh_uom")
        or ctx.get("selling_uom")
        or ""
    ).strip().upper()
    if required_uom and required_uom != unit:
        raise ValueError(f"CLEARANCE_UOM_MISMATCH:{required_uom}")

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        _ensure_clearance_table(cur)
        if clearance_plan_id is not None:
            cur.execute(
                """UPDATE yipman_clearance_plan
                   SET ean_upc=%s,expiry_date=%s,expiring_quantity=%s,uom_code=%s,
                       plan_status='ACTIVE',note=%s,updated_by=%s,
                       updated_at=CURRENT_TIMESTAMP(6)
                   WHERE clearance_plan_id=%s""",
                (
                    upc,
                    expiry_date,
                    qty,
                    unit,
                    (str(note)[:500] if note else None),
                    actor,
                    int(clearance_plan_id),
                ),
            )
            if int(cur.rowcount or 0) <= 0:
                conn.rollback()
                cur.close()
                raise KeyError("CLEARANCE_PLAN_NOT_FOUND")
            lookup_sql = "SELECT * FROM yipman_clearance_plan WHERE clearance_plan_id=%s LIMIT 1"
            lookup_args = (int(clearance_plan_id),)
        else:
            cur.execute(
                """INSERT INTO yipman_clearance_plan
                     (ean_upc,expiry_date,expiring_quantity,uom_code,plan_status,note,created_by,updated_by)
                   VALUES (%s,%s,%s,%s,'ACTIVE',%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     expiring_quantity=VALUES(expiring_quantity),
                     uom_code=VALUES(uom_code),
                     plan_status='ACTIVE',
                     note=VALUES(note),
                     updated_by=VALUES(updated_by),
                     updated_at=CURRENT_TIMESTAMP(6)""",
                (
                    upc,
                    expiry_date,
                    qty,
                    unit,
                    (str(note)[:500] if note else None),
                    actor,
                    actor,
                ),
            )
            lookup_sql = """SELECT *
                            FROM yipman_clearance_plan
                            WHERE ean_upc=%s AND expiry_date=%s
                            LIMIT 1"""
            lookup_args = (upc, expiry_date)
        conn.commit()
        cur.execute(lookup_sql, lookup_args)
        row = dict(cur.fetchone())
        cur.close()
    return _analyze_plan(row)


def list_clearance_plans(
    *,
    status: str = "ACTIVE",
    limit: int = 100,
) -> dict[str, Any]:
    st = str(status or "ACTIVE").strip().upper()
    lim = max(1, min(int(limit or 100), 500))
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        _ensure_clearance_table(cur)
        conn.commit()
        if st == "ALL":
            cur.execute(
                """SELECT * FROM yipman_clearance_plan
                   ORDER BY CASE plan_status WHEN 'ACTIVE' THEN 0 ELSE 1 END,
                            expiry_date,updated_at DESC
                   LIMIT %s""",
                (lim,),
            )
        else:
            cur.execute(
                """SELECT * FROM yipman_clearance_plan
                   WHERE plan_status=%s
                   ORDER BY expiry_date,updated_at DESC
                   LIMIT %s""",
                (st, lim),
            )
        rows = [dict(x) for x in cur.fetchall()]
        cur.close()

    analyzed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for row in rows:
        try:
            analyzed.append(_analyze_plan(row))
        except Exception as exc:
            errors.append({
                "clearance_plan_id": row.get("clearance_plan_id"),
                "ean_upc": row.get("ean_upc"),
                "error": f"{type(exc).__name__}: {exc}"[:500],
            })
    analyzed.sort(
        key=lambda x: (
            int(x.get("days_to_expiry") if x.get("days_to_expiry") is not None else 9999),
            -float(x.get("velocity_pressure_ratio") or 0),
            str(x.get("name") or x.get("upc") or ""),
        )
    )
    return {
        "contract_version": "YIPMAN_CLEARANCE_V1",
        "count": len(analyzed),
        "rows": analyzed,
        "errors": errors,
        "rules": {
            "purpose": "SELL_USER_IDENTIFIED_EXPIRING_QUANTITY_BEFORE_EXPIRATION_TO_REDUCE_DUMPING",
            "true_stock": "SAVED_THROUGH_EXISTING_QUICK_CHECK_TRUE_STOCK_WORKFLOW_AND_TREATED_AS_EFFECTIVE_OH",
            "sale": "COMPANY_CONTROLLED_PRICE_AND_PERIOD; CLEARANCE_MUST_NOT_OVERRIDE_ACTIVE_SALE",
            "price_floor": "AUTOMATIC_CLEARANCE_SUGGESTIONS_DO_NOT_CROSS_CURRENT_COST; MANAGER_DISPOSITION_REVIEW_IF STILL BEHIND",
            "price_endings": "29_49_59_69_79_99",
        },
    }


def get_clearance_plan(clearance_plan_id: int) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        _ensure_clearance_table(cur)
        conn.commit()
        cur.execute(
            "SELECT * FROM yipman_clearance_plan WHERE clearance_plan_id=%s LIMIT 1",
            (int(clearance_plan_id),),
        )
        row = cur.fetchone()
        cur.close()
    if not row:
        raise KeyError("CLEARANCE_PLAN_NOT_FOUND")
    return _analyze_plan(dict(row))


def close_clearance_plan(
    clearance_plan_id: int,
    *,
    actor: str | None,
    status: str = "CLOSED",
) -> dict[str, Any]:
    final_status = str(status or "CLOSED").strip().upper()
    if final_status not in {"CLOSED", "CANCELLED"}:
        raise ValueError("CLEARANCE_CLOSE_STATUS_INVALID")
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        _ensure_clearance_table(cur)
        conn.commit()
        cur.execute(
            """UPDATE yipman_clearance_plan
               SET plan_status=%s,updated_by=%s,updated_at=CURRENT_TIMESTAMP(6)
               WHERE clearance_plan_id=%s""",
            (final_status, actor, int(clearance_plan_id)),
        )
        if int(cur.rowcount or 0) <= 0:
            conn.rollback()
            cur.close()
            raise KeyError("CLEARANCE_PLAN_NOT_FOUND")
        conn.commit()
        cur.execute(
            "SELECT * FROM yipman_clearance_plan WHERE clearance_plan_id=%s LIMIT 1",
            (int(clearance_plan_id),),
        )
        row = dict(cur.fetchone())
        cur.close()
    return _analyze_plan(row)
