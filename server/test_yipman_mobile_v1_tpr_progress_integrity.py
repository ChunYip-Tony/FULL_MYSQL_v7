from yipman_mobile_v1_tpr_progress import polish_price_progress_html
from yipman_mobile_v1_tpr_progress_guard import polish_tpr_progress_guard_html
from yipman_mobile_v1_tpr_progress_integrity import polish_tpr_progress_integrity_html


def test_missing_progress_evidence_never_becomes_zero_or_keep():
    base = '<html><head></head><body><script>async function loadPrice(){} function renderPrice(){const rows=priceRows.filter(x=>true);}</script></body></html>'
    html = polish_price_progress_html(base)
    html = polish_tpr_progress_guard_html(html)
    html = polish_tpr_progress_integrity_html(html)
    assert "if(v===null||v===undefined||v==='')return '—'" in html
    assert "state==='DATA NEEDED'?'DATA NEEDED':esc(decision)" in html
    assert "TPR PRICE NEEDED" in html
    assert "ENTER TRUE STOCK" in html
    assert "No keep/change decision until required evidence is available." in html
