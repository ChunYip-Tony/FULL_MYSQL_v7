from decimal import Decimal
from shared_price_scoring import rank_price_candidates, choose_price


def test_equal_weights_favor_consistent_demand():
    ranked = rank_price_candidates([
        dict(price="5.99", price_type="REG", gp_per_day="75", positive_sale_days=9, eligible_exposure_days=10),
        dict(price="6.99", price_type="REG", gp_per_day="90", positive_sale_days=5, eligible_exposure_days=10),
    ])
    assert ranked[0]["price"] == Decimal("5.99")
    assert ranked[0]["combined_score"] > ranked[1]["combined_score"]


def test_no_sales_and_sparse_exposure_do_not_win():
    rows = [
        dict(price="6.99", gp_per_day="100", positive_sale_days=1, eligible_exposure_days=1),
        dict(price="5.99", gp_per_day="80", positive_sale_days=8, eligible_exposure_days=10),
    ]
    assert choose_price(rows)["price"] == Decimal("5.99")


def test_unknown_exposure_never_looks_like_zero():
    assert rank_price_candidates([dict(price="5.99", gp_per_day="20", positive_sale_days=1)]) == []
    assert choose_price([]) is None


def test_stockout_adjusted_exposure():
    row = rank_price_candidates([dict(price="5.99", gp_per_day="20", positive_sale_days=4, eligible_exposure_days=4)])[0]
    assert row["popularity"] == Decimal(1)
    assert row["confidence"] == "LIMITED"


def test_company_and_gp36_references_are_independent():
    from shared_price_scoring import price_references
    refs = price_references("6.99", "7.49", None, "4.00")
    assert refs["company_a"] == Decimal("6.99")
    assert refs["company_b"] == Decimal("7.49")
    assert refs["company_c"] is None
    assert refs["gp36_reference_price"] == Decimal("6.25")
    assert refs["gp36_reference_only"] is True
    assert price_references(effective_cost=None)["gp36_reference_price"] is None
