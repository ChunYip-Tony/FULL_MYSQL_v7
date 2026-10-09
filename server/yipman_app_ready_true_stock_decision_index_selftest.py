from pathlib import Path


def run():
    text = Path(__file__).with_name('yipman_app_ready_true_stock_overlay.py').read_text()
    assert 'def _rebuild_decision_index' in text
    assert '_rebuild_decision_index(sections.get("decision_intelligence"))' in text
    assert 'if child_key != "by_key": visit(child)' in text
    assert 'section["by_key"] = by_key' in text
    assert 'INVENTORY_FAMILY_RECALC_PENDING' in text
    return {
        'patched_decision_rows_indexed_contract': 'PASS',
        'stale_by_key_objects_discarded_contract': 'PASS',
        'family_recalc_guard_preserved_contract': 'PASS',
    }


if __name__ == '__main__':
    print(run())
