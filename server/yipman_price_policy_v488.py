from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

from business_clock import completed_through_date
from data_coverage import source_data_days
from db import db_conn
from webapp_v2_runtime import _batch_daily_sales_by_price_type

OBSERVATION_DAYS = 7
FRESH_LIVE_THRESHOLD_DAYS = Decimal("10")
FRESH_LIVE_CONTROL_LEAD_DAYS = Decimal("4")
FROZEN_THRESHOLD_DAYS = Decimal("60")  # operational 2-month equivalent
FROZEN_CONTROL_LEAD_DAYS = Decimal("30")
PRICE_ENDINGS = (Decimal("0.29"), Decimal("0.49"), Decimal("0.69"), Decimal("0.79"), Decimal("0.99"))
PREFIX_RANK = {"240": 0, "249": 1, "245": 2, "247": 3}


def _d(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _prefix(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit()).lstrip("0")
    return digits[:3]


def _policy_for(category: Any) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    c = str(category or "").upper()
    if c in {"FRESH", "LIVE"}:
        threshold = FRESH_LIVE_THRESHOLD_DAYS
        lead = FRESH_LIVE_CONTROL_LEAD_DAYS
        return threshold, lead, threshold - lead
    if c == "FROZEN":
        threshold = FROZEN_THRESHOLD_DAYS
        lead = FROZEN_CONTROL_LEAD_DAYS
        return threshold, lead, threshold - lead
    return None, None, None


def _price_floor(cost: Decimal | None, company_low: Decimal | None) -> Decimal | None:
    vals = []
    if cost is not None:
        vals.append(cost + Decimal("0.01"))
    if company_low is not None:
        vals.append(company_low)
    return max(vals) if vals else None


def _retail_candidates(center: Decimal, span: int = 6) -> list[Decimal]:
    whole = int(center)
    out: list[Decimal] = []
    for dollars in range(max(0, whole - span), whole + span + 1):
        base = Decimal(dollars)
        for ending in PRICE_ENDINGS:
            p = base + ending
            if p > 0:
                out.append(p)
    return sorted(set(out))


def _soft_step_price(
    current: Decimal | None,
    *,
    direction: str,
    cost: Decimal | None,
    company_low: Decimal | None,
    company_high: Decimal | None,
    urgency: str = "SOFT",
) -> Decimal | None:
    if current is None or current <= 0:
        return None
    pct = Decimal("0.05")
    if urgency == "MEDIUM":
        pct = Decimal("0.08")
    elif urgency == "LAST_CHANCE":
        pct = Decimal("0.10")
    step = max(Decimal("0.45"), (current * pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    raw = current - step if direction == "DOWN" else current + step
    low = _price_floor(cost, company_low)
    high = company_high
    candidates = _retail_candidates(raw)
    if low is not None:
        candidates = [p for p in candidates if p >= low]
    if high is not None:
        candidates = [p for p in candidates if p <= high]
    if direction == "DOWN":
        candidates = [p for p in candidates if p < current - Decimal("0.01")]
        if not candidates:
            return None
        below_raw = [p for p in candidates if p <= raw]
        return max(below_raw) if below_raw else min(candidates)
    candidates = [p for p in candidates if p > current + Decimal("0.01")]
    if not candidates:
        return None
    above_raw = [p for p in candidates if p >= raw]
    return min(above_raw) if above_raw else max(candidates)


def _freshness_context(row: dict[str, Any]) -> dict[str, Any]:
    category = row.get("category") or row.get("product_class")
    threshold, lead, start = _policy_for(category)
    doh = _d(row.get("doh"))
    oh = _d(row.get("current_oh"))
    velocity = _d(row.get("velocity_7d"))
    if velocity is None:
        velocity = _d(row.get("upc_velocity_7d"))
    if velocity is None:
        velocity = Decimal("0")
    in_window = bool(
        threshold is not None and start is not None and doh is not None
        and doh >= start and doh <= threshold
    )
    days_remaining = (
        max(Decimal("0"), threshold - doh)
        if threshold is not None and doh is not None else None
    )
    sellthrough_days = (
        max(Decimal("1"), days_remaining + Decimal("1"))
        if days_remaining is not None else None
    )
    required_velocity = (
        oh / sellthrough_days
        if oh is not None and oh > 0 and sellthrough_days is not None else None
    )
    pace_ratio = (
        velocity / required_velocity
        if required_velocity is not None and required_velocity > 0 else None
    )
    return {
        "threshold": threshold,
        "lead": lead,
        "start": start,
        "doh": doh,
        "oh": oh,
        "velocity": velocity,
        "in_window": in_window,
        "days_remaining": days_remaining,
        "sellthrough_days": sellthrough_days,
        "required_velocity": required_velocity,
        "pace_ratio": pace_ratio,
    }


def _apply_common_fields(row: dict[str, Any]) -> None:
    pfx = _prefix(row.get("upc") or row.get("ean_upc"))
    threshold, lead, start = _policy_for(row.get("category") or row.get("product_class"))
    row["upc_role_rank"] = PREFIX_RANK.get(pfx, 9)
    row["upc_role"] = {
        "240": "MAIN",
        "249": "SECONDARY_SERVICE",
        "245": "THIRD",
        "247": "LAST",
    }.get(pfx, "OTHER")
    row["observation_days_required"] = OBSERVATION_DAYS
    row["freshness_threshold_days"] = threshold
    row["freshness_control_lead_days"] = lead
    row["freshness_control_start_doh"] = start
    row["freshness_policy"] = (
        "FRESH_LIVE_10D_START_4D_BEFORE_EXPIRY"
        if str(row.get("category") or row.get("product_class") or "").upper() in {"FRESH", "LIVE"}
        else (
            "FROZEN_60D_START_30D_BEFORE_EXPIRY"
            if str(row.get("category") or row.get("product_class") or "").upper() == "FROZEN"
            else None
        )
    )


def apply_pricing_review_policy(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload or {})
    rows = [dict(x) for x in (out.get("rows") or [])]
    for row in rows:
        _apply_common_fields(row)
        ctx = _freshness_context(row)
        current = _d(row.get("current_price"))
        cost = _d(row.get("current_cost"))
        company_low = _d(row.get("company_range_low"))
        company_high = _d(row.get("company_range_high"))
        price_type = str(row.get("current_price_type") or "").upper()
        ready = str(row.get("readiness") or "").upper() == "READY"
        stock_ok = ctx["oh"] is not None and ctx["oh"] > 0
        data_ok = current is not None and cost is not None and cost > 0

        row["freshness_control_active"] = ctx["in_window"]
        row["freshness_days_remaining"] = ctx["days_remaining"]
        row["required_velocity_to_clear"] = ctx["required_velocity"]
        row["freshness_velocity_pace_ratio"] = ctx["pace_ratio"]
        row["final_tpr_decision"] = "NO_TPR_ACTION"
        row["final_tpr_price_suggestion"] = None
        row["final_tpr_decision_reason"] = "No temporary price action is required from the current evidence."

        if price_type == "SALE":
            row["final_tpr_decision"] = "SALE_LOCKED"
            row["final_tpr_decision_reason"] = "Company SALE price/period is authoritative; store TPR is not changed."
            continue

        # Freshness control only starts inside the requested sell-through window.
        if ctx["in_window"] and ready and stock_ok and data_ok:
            pace = ctx["pace_ratio"]
            days_left = ctx["days_remaining"] or Decimal("0")
            urgency = "SOFT"
            if days_left <= Decimal("2"):
                urgency = "LAST_CHANCE"
            elif pace is not None and pace < Decimal("0.50"):
                urgency = "MEDIUM"
            candidate = _soft_step_price(
                current,
                direction="DOWN",
                cost=cost,
                company_low=company_low,
                company_high=company_high,
                urgency=urgency,
            )
            row["freshness_test_needed"] = True
            row["tpr_suggestion_purpose"] = "FRESHNESS_SELL_THROUGH"
            row["tpr_suggestion_actionable"] = candidate is not None and price_type != "TPR"
            row["testing_price"] = candidate
            row["tpr_suggestion_price"] = candidate
            row["suggested_price"] = candidate
            row["candidate_price"] = candidate
            row["suggestion_reason_code"] = "FRESHNESS_SELL_THROUGH"
            row["suggestion_reason"] = "FRESHNESS SELL-THROUGH TPR"
            row["primary_reason_text"] = (
                f"Freshness control is active: {ctx['days_remaining']} day(s) remain. "
                "Use one soft TPR step, observe 7 completed POS days, then decide the next step."
            )
            row["final_tpr_decision"] = "CONTINUE_TPR" if price_type == "TPR" else "START_TPR"
            row["final_tpr_price_suggestion"] = current if price_type == "TPR" else candidate
            row["final_tpr_decision_reason"] = row["primary_reason_text"]
        elif str(row.get("suggestion_reason_code") or "") == "VELOCITY_TEST":
            # Outside the freshness window, slow movement alone must not be
            # mislabeled as freshness. Keep only a genuine GP$/sweet-spot test.
            tested = _d(row.get("tested_price"))
            target = _d(row.get("target_sweet_spot_price"))
            if tested is not None or target is not None:
                row["tpr_suggestion_purpose"] = "SWEET_SPOT_TEST"
                row["suggestion_reason_code"] = "SWEET_SPOT_TEST"
                row["suggestion_reason"] = "7-DAY GP$/DAY SWEET-SPOT TEST"
                row["primary_reason_text"] = "Run a 7 completed-day TPR observation only to test a stronger GP$/day sweet spot."
                row["final_tpr_decision"] = "START_TPR" if row.get("testing_price") is not None else "NO_TPR_ACTION"
                row["final_tpr_price_suggestion"] = row.get("testing_price")
                row["final_tpr_decision_reason"] = row["primary_reason_text"]
            else:
                row["testing_price"] = None
                row["tpr_suggestion_price"] = None
                row["suggested_price"] = None
                row["candidate_price"] = None
                row["actionable"] = False
                row["tpr_suggestion_actionable"] = False
                row["final_tpr_decision"] = "NO_TPR_ACTION"
                row["final_tpr_decision_reason"] = "Freshness control has not started yet and no separate sweet-spot test is supported."
        elif row.get("testing_price") is not None:
            row["final_tpr_decision"] = "START_TPR"
            row["final_tpr_price_suggestion"] = row.get("testing_price")
            row["final_tpr_decision_reason"] = "Start this controlled TPR and hold the price for a 7 completed-day observation cycle."

    rows.sort(key=lambda r: (int(r.get("upc_role_rank") or 9), -int(bool(r.get("actionable"))), str(r.get("name") or r.get("upc") or "")))
    out["rows"] = rows
    rules = dict(out.get("rules") or {})
    rules.update({
        "upc_role_order": "240_MAIN_THEN_249_THEN_245_THEN_247",
        "price_observation_days": 7,
        "fresh_live_freshness_threshold_days": 10,
        "fresh_live_tpr_start_days_before_expiry": 4,
        "frozen_freshness_threshold_days": 60,
        "frozen_tpr_start_days_before_expiry": 30,
        "freshness_tpr_method": "SOFT_STEP_DOWN_TO_CLEAR_EFFECTIVE_OH_BY_THRESHOLD;REASSESS_EVERY_7_COMPLETED_POS_DAYS",
        "final_tpr_decision": "ONE_UPC_ONE_FINAL_DECISION_WITH_PRICE_WHEN_ACTIONABLE",
    })
    out["rules"] = rules
    out["contract_version"] = "YIPMAN_PRICING_V488_7D_FRESHNESS_POLICY"
    return out


def _load_tpr_7d_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not rows:
        return {}
    upcs = [str(r.get("upc") or "").strip() for r in rows if str(r.get("upc") or "").strip()]
    if not upcs:
        return {}
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        days = source_data_days(cur, "sales_by_price_type", limit=120, up_to=completed_through_date())
        ph = ",".join(["%s"] * len(upcs))
        cur.execute(f"SELECT upc_id,ean_upc FROM selling_upc WHERE ean_upc IN ({ph})", tuple(upcs))
        found = [dict(x) for x in cur.fetchall()]
        by_ean = {str(x.get("ean_upc") or ""): x for x in found}
        daily = _batch_daily_sales_by_price_type(cur, found, days) if found else {}
        cur.close()

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        upc = str(row.get("upc") or "")
        src = by_ean.get(upc)
        if not src:
            continue
        uid = int(src["upc_id"])
        step_start = _as_date(row.get("current_tpr_price_step_start_date")) or _as_date(row.get("tpr_start_date"))
        eligible = [x for x in days if step_start is None or x.get("date") >= step_start]
        cycle_complete = len(eligible) >= OBSERVATION_DAYS
        obs_days = eligible[-OBSERVATION_DAYS:]
        qty = Decimal("0")
        sales = Decimal("0")
        selling_days = 0
        for day_entry in obs_days:
            obs = (daily.get(uid) or {}).get(day_entry.get("date"), {})
            tpr = (obs.get("price_types") or {}).get("TPR") or {}
            q = _d(tpr.get("sold_quantity")) or Decimal("0")
            s = _d(tpr.get("sales_amount")) or Decimal("0")
            qty += q
            sales += s
            if q != 0:
                selling_days += 1
        n = len(obs_days)
        cost = _d(row.get("current_cost"))
        velocity = qty / Decimal(n) if n else None
        gp_day = ((sales - qty * cost) / Decimal(n)) if n and cost is not None else None
        out[upc] = {
            "supported_days": n,
            "cycle_complete": cycle_complete,
            "window_start": min((x.get("date") for x in obs_days), default=None),
            "window_end": max((x.get("date") for x in obs_days), default=None),
            "qty": qty,
            "sales": sales,
            "selling_days": selling_days,
            "velocity": velocity,
            "gp_per_day": gp_day,
        }
    return out


def apply_current_tpr_policy(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload or {})
    rows = [dict(x) for x in (out.get("rows") or [])]
    metrics = _load_tpr_7d_metrics(rows)

    for row in rows:
        _apply_common_fields(row)
        m = metrics.get(str(row.get("upc") or "")) or {}
        n = int(m.get("supported_days") or 0)
        row["observation_days_required"] = OBSERVATION_DAYS
        row["observation_supported_days"] = n
        row["observation_cycle_complete"] = bool(m.get("cycle_complete"))
        row["tpr_qty_7d_observation"] = m.get("qty")
        row["tpr_sales_7d_observation"] = m.get("sales")
        row["tpr_velocity_7d_observation"] = m.get("velocity")
        row["tpr_gp_per_day_7d_observation"] = m.get("gp_per_day")
        row["observation_window_start"] = m.get("window_start")
        row["observation_window_end"] = m.get("window_end")

        ctx = _freshness_context({**row, "velocity_7d": m.get("velocity") if m.get("velocity") is not None else row.get("velocity_7d")})
        row["freshness_control_active"] = ctx["in_window"]
        row["freshness_days_remaining"] = ctx["days_remaining"]
        row["required_velocity_to_clear"] = ctx["required_velocity"]
        row["freshness_velocity_pace_ratio"] = ctx["pace_ratio"]
        if ctx["in_window"]:
            row["tpr_purpose"] = "FRESHNESS_SELL_THROUGH"
            row["tpr_purpose_label"] = "FRESHNESS SELL-THROUGH"
            row["tpr_purpose_source"] = "V488_FRESHNESS_POLICY"

        current = _d(row.get("current_tpr_price"))
        cost = _d(row.get("current_cost"))
        company_low = _d(row.get("company_range_low"))
        company_high = _d(row.get("company_range_high"))
        baseline = row.get("previous_behavior") or {}
        baseline_v = _d(baseline.get("velocity"))
        baseline_gp = _d(baseline.get("gp_per_day_current_cost"))
        tpr_v = _d(m.get("velocity"))
        tpr_gp = _d(m.get("gp_per_day"))
        oh = _d(row.get("current_oh"))
        readiness = str(row.get("readiness") or "").upper()

        # Pair integrity remains the highest pricing rule.
        if row.get("price_240_249_equal") is False and row.get("related_240_current_price") is not None:
            target = _d(row.get("related_240_current_price"))
            if target is not None and current is not None:
                row["suggested_tpr_price"] = target
                row["recommendation_code"] = "LOWER_TPR_PRICE" if target < current else ("RAISE_TPR_PRICE" if target > current else "CONTINUE_TPR")
                row["recommendation_label"] = "MATCH 240"
                row["recommendation_reason"] = "249 must match the paired 240 authority price."
                row["recommendation_final"] = True
                row["final_tpr_decision"] = row["recommendation_code"]
                row["final_tpr_price_suggestion"] = target
                row["final_tpr_decision_reason"] = row["recommendation_reason"]
                continue

        if readiness != "READY" or current is None or cost is None or cost <= 0:
            row["recommendation_code"] = "CONTINUE_TPR"
            row["recommendation_label"] = "CONTINUE"
            row["recommendation_reason"] = "Keep the current TPR unchanged until price/cost/readiness data is resolved."
            row["recommendation_final"] = False
            row["final_tpr_decision"] = "CONTINUE_TPR"
            row["final_tpr_price_suggestion"] = current
            row["final_tpr_decision_reason"] = row["recommendation_reason"]
            continue

        if oh is not None and oh <= 0:
            row["recommendation_code"] = "CANCEL_TPR"
            row["recommendation_label"] = "CANCEL TPR"
            row["recommendation_reason"] = "No positive effective OH remains. End the temporary TPR."
            row["recommendation_final"] = True
            row["final_tpr_decision"] = "CANCEL_TPR"
            row["final_tpr_price_suggestion"] = None
            row["final_tpr_decision_reason"] = row["recommendation_reason"]
            continue

        if n < OBSERVATION_DAYS:
            row["recommendation_code"] = "CONTINUE_TPR"
            row["recommendation_label"] = "CONTINUE"
            row["recommendation_reason"] = f"Observation cycle is {n}/{OBSERVATION_DAYS} completed canonical POS days. Keep the current TPR unchanged until day 7."
            row["recommendation_final"] = False
            row["monitoring_phase"] = "7D_OBSERVATION"
            row["final_tpr_decision"] = "CONTINUE_TPR"
            row["final_tpr_price_suggestion"] = current
            row["final_tpr_decision_reason"] = row["recommendation_reason"]
            continue

        if ctx["in_window"] or str(row.get("tpr_purpose") or "").upper() == "FRESHNESS_SELL_THROUGH":
            required = ctx["required_velocity"]
            pace = ctx["pace_ratio"]
            days_left = ctx["days_remaining"] or Decimal("0")
            if required is not None and tpr_v is not None and tpr_v >= required:
                row["recommendation_code"] = "CONTINUE_TPR"
                row["recommendation_label"] = "CONTINUE"
                row["recommendation_reason"] = "The 7-day TPR velocity is on pace to clear the aging effective OH by the freshness threshold."
                row["suggested_tpr_price"] = None
            else:
                urgency = "LAST_CHANCE" if days_left <= Decimal("2") else ("MEDIUM" if pace is not None and pace < Decimal("0.50") else "SOFT")
                candidate = _soft_step_price(current, direction="DOWN", cost=cost, company_low=company_low, company_high=company_high, urgency=urgency)
                if candidate is None:
                    row["recommendation_code"] = "CONTINUE_TPR"
                    row["recommendation_label"] = "CONTINUE"
                    row["recommendation_reason"] = "Sell-through is behind pace, but no valid lower price exists inside current cost/company limits."
                else:
                    row["recommendation_code"] = "LOWER_TPR_PRICE"
                    row["recommendation_label"] = "LOWER TPR"
                    row["recommendation_reason"] = "The completed 7-day observation is below the velocity required to clear aging stock before the freshness threshold. Step down softly and begin a new 7-day observation cycle."
                    row["suggested_tpr_price"] = candidate
            row["recommendation_final"] = True
        else:
            def lift(now: Decimal | None, base: Decimal | None) -> Decimal | None:
                if now is None or base is None or base == 0:
                    return None
                return (now - base) / abs(base) * Decimal("100")
            v_lift = lift(tpr_v, baseline_v)
            g_lift = lift(tpr_gp, baseline_gp)
            if g_lift is not None and g_lift >= Decimal("5") and (v_lift is None or v_lift >= Decimal("-5")):
                row["recommendation_code"] = "CANCEL_TPR"
                row["recommendation_label"] = "CANCEL TPR · MAKE REG"
                row["recommendation_reason"] = "The full 7-day observation shows stronger GP$/day without materially weaker velocity. End the test and use this TPR price as the new REG sweet spot."
                row["suggested_regular_price"] = current
                row["suggested_regular_price_basis"] = "PROVEN_7D_TPR_SWEET_SPOT"
            elif v_lift is not None and v_lift <= Decimal("0") and (g_lift is None or g_lift <= Decimal("0")):
                row["recommendation_code"] = "CANCEL_TPR"
                row["recommendation_label"] = "CANCEL TPR"
                row["recommendation_reason"] = "The full 7-day observation did not improve velocity or GP$/day. End the test and return to the best REG evidence."
            elif g_lift is not None and g_lift < Decimal("-10"):
                candidate = _soft_step_price(current, direction="UP", cost=cost, company_low=company_low, company_high=company_high, urgency="SOFT")
                if candidate is not None:
                    row["recommendation_code"] = "RAISE_TPR_PRICE"
                    row["recommendation_label"] = "RAISE TPR"
                    row["recommendation_reason"] = "The 7-day observation is sacrificing too much GP$/day. Raise one soft step and start a new 7-day observation cycle."
                    row["suggested_tpr_price"] = candidate
                else:
                    row["recommendation_code"] = "CONTINUE_TPR"
                    row["recommendation_label"] = "CONTINUE"
                    row["recommendation_reason"] = "GP$/day is weak, but no valid higher TPR step is available inside current limits."
            else:
                row["recommendation_code"] = "CONTINUE_TPR"
                row["recommendation_label"] = "CONTINUE"
                row["recommendation_reason"] = "The 7-day result is acceptable but not conclusive. Continue the current TPR for the next 7-day observation cycle."
            row["recommendation_final"] = True

        row["final_tpr_decision"] = row.get("recommendation_code")
        row["final_tpr_price_suggestion"] = row.get("suggested_tpr_price")
        row["final_tpr_decision_reason"] = row.get("recommendation_reason")

    rows.sort(key=lambda r: (int(r.get("upc_role_rank") or 9), -int(r.get("recommendation_priority") or 0), str(r.get("name") or r.get("upc") or "")))
    out["rows"] = rows
    rules = dict(out.get("rules") or {})
    rules.update({
        "upc_role_order": "240_MAIN_THEN_249_THEN_245_THEN_247",
        "observation_cycle": "7_COMPLETED_CANONICAL_POS_DAYS_PER_TPR_PRICE_STEP",
        "fresh_live_freshness_threshold_days": 10,
        "fresh_live_tpr_start_doh": 6,
        "fresh_live_tpr_start_days_before_expiry": 4,
        "frozen_freshness_threshold_days": 60,
        "frozen_tpr_start_doh": 30,
        "frozen_tpr_start_days_before_expiry": 30,
        "freshness_step_down": "SOFT_PRICE_STEP_THEN_NEW_7D_OBSERVATION;TARGET_CLEAR_EFFECTIVE_AGING_OH_BY_THRESHOLD",
        "decision_contract": "ONE_FINAL_TPR_DECISION_PER_UPC",
    })
    out["rules"] = rules
    out["contract_version"] = "YIPMAN_CURRENT_TPR_V488_7D_FINAL_DECISION"
    return out


def wrap_pricing_review(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    def wrapped(*args, **kwargs):
        return apply_pricing_review_policy(fn(*args, **kwargs))
    return wrapped


def wrap_current_tpr_review(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    def wrapped(*args, **kwargs):
        return apply_current_tpr_policy(fn(*args, **kwargs))
    return wrapped
