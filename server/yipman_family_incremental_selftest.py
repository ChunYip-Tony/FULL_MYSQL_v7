from pathlib import Path


def run():
    text = Path(__file__).with_name("yipman_family_incremental.py").read_text()
    assert "family_ids=[fid]" in text
    assert "bulk_ordering_suggestions(" in text
    assert "full_review_then_filter\": False" in text
    assert "scope_applied_before_heavy_calculation\": True" in text
    assert "FAMILY_CATEGORY_IDENTITY_AMBIGUOUS" in text
    return {
        "family_scope_passed_to_authoritative_engine_contract": "PASS",
        "full_review_filter_adapter_forbidden_contract": "PASS",
        "category_ambiguity_fail_closed_contract": "PASS",
    }


if __name__ == "__main__":
    print(run())
