"""Canonical 50/50 historical price scoring for REG, TPR and progress consumers.

All UI surfaces must consume one server-produced recommendation; never recompute
or independently rank prices in the browser. This module does not infer exposure,
selling units, receipts, or price history.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping, Any

SCORING_VERSION = "FISHFINDER_PRICE_SCORE_50_50_V1"
MIN_CONFIDENT_DAYS = 7


def number(value: Any) -> Decimal | None:
    try:
        x = Decimal(str(value))
        return x if x.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def rank_price_candidates(candidates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rank comparable price observations by equal GP$/day and popularity weights.

    Required input: price, price_type, gp_per_day, positive_sale_days,
    eligible_exposure_days. GP/day must be calculated from valid completed POS
    days using verified selling-unit cost; exposure excludes confirmed stockouts.
    REG and TPR/SALE observations must be ranked in separate invocations.
    """
    verified = []
    for candidate in candidates:
        p = number(candidate.get("price"))
        gp = number(candidate.get("gp_per_day"))
        positive = number(candidate.get("positive_sale_days"))
        exposure = number(candidate.get("eligible_exposure_days"))
        if any(v is None for v in (p, gp, positive, exposure)):
            continue
        if p <= 0 or exposure <= 0 or positive < 0 or positive > exposure:
            continue
        popularity = positive / exposure
        verified.append({**dict(candidate), "price": p, "gp_per_day": gp,
                         "popularity": popularity, "eligible_exposure_days": exposure})
    # Negative GP is not considered a profitable historical optimum.
    max_gp = max((max(v["gp_per_day"], Decimal(0)) for v in verified), default=Decimal(0))
    for v in verified:
        gp_component = max(v["gp_per_day"], Decimal(0)) / max_gp if max_gp > 0 else Decimal(0)
        v["gp_score"] = gp_component
        v["popularity_score"] = v["popularity"]
        v["combined_score"] = (gp_component + v["popularity"]) / Decimal(2)
        v["confidence"] = "PROVEN" if v["eligible_exposure_days"] >= MIN_CONFIDENT_DAYS else "LIMITED"
        v["scoring_version"] = SCORING_VERSION
    return sorted(verified, key=lambda v: (
        -v["combined_score"], -v["popularity"], -v["gp_per_day"],
        -v["eligible_exposure_days"], v["price"]
    ))


def choose_price(candidates: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Prefer a seven-day proven observation; do not promote sparse evidence."""
    ranked = rank_price_candidates(candidates)
    proven = [r for r in ranked if r["confidence"] == "PROVEN"]
    return proven[0] if proven else None
