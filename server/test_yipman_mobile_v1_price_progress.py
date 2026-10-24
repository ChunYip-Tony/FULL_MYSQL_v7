from yipman_mobile_v1_exact_shell import yipman_mobile_v1_exact_html
from yipman_mobile_v1_price_upc_only import polish_price_upc_only_html
from yipman_mobile_v1_price_progress import polish_price_progress_html


def test_all_price_filters_are_upc_direct_cards_and_progress_is_wired():
    html = yipman_mobile_v1_exact_html("test")
    html = polish_price_upc_only_html(html)
    html = polish_price_progress_html(html)

    assert "const direct=true;" in html
    assert "r=>upcOf(r)&&actionablePrice(r)" in html
    assert "/v1/yipman/current-tpr-review?category=ALL&limit=1000" in html
    assert "priceProgressHtml(r)" in html
    assert "TEST ACTIVE" in html
    assert "GP$/DAY Δ" in html
    assert "VELOCITY Δ" in html
    assert "Backend lifecycle tracking" in html

