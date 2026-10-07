from __future__ import annotations

"""RC-only safety guard for Mobile V1 price rendering.

Prevents missing/blank/zero suggestion values from being rendered as $0.00 and
from being treated as actionable price recommendations.
"""


def guard_price_html(html: str) -> str:
    marker = "yipmanV1PriceGuardApplied"
    if marker in html:
        return html

    old_num = "const num=v=>{const x=Number(v);return Number.isFinite(x)?x:null};"
    new_num = (
        "const num=v=>{"
        "if(v===null||v===undefined)return null;"
        "if(typeof v==='string'&&!v.trim())return null;"
        "const x=Number(v);return Number.isFinite(x)?x:null};"
    )
    html = html.replace(old_num, new_num, 1)

    old_suggest = (
        "function priceReason(r){return String(r?.why||r?.reason||r?.suggestion_reason||r?.recommendation_reason||'Review current pricing evidence.')}"
        ";function suggestedPrice(r){return r?.final_tpr_price_suggestion??r?.tpr_suggestion_price??r?.testing_price??r?.suggested_price??r?.candidate_price??r?.suggested_reg_price??null}"
        "function currentPrice(r){return r?.current_price??r?.effective_price??null}"
    )
    new_suggest = (
        "function priceReason(r){return String(r?.why||r?.reason||r?.suggestion_reason||r?.recommendation_reason||'Review current pricing evidence.')}"
        ";function validPrice(v){const x=num(v);return x!==null&&x>0?x:null}"
        ";function suggestedPrice(r){"
        "const vals=[r?.final_tpr_price_suggestion,r?.tpr_suggestion_price,r?.testing_price,r?.suggested_price,r?.candidate_price,r?.suggested_reg_price];"
        "for(const v of vals){const x=validPrice(v);if(x!==null)return x}return null}"
        "function currentPrice(r){return validPrice(r?.current_price??r?.effective_price)}"
    )
    html = html.replace(old_suggest, new_suggest, 1)

    # Mark the generated HTML so the decorator is idempotent and diagnosable.
    html = html.replace(
        "</head>",
        '<meta name="yipmanV1PriceGuardApplied" content="1">\n</head>',
        1,
    )
    return html
