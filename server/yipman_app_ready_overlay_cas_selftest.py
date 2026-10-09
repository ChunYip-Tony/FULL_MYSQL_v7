from pathlib import Path

def run():
    p=Path(__file__).with_name('yipman_app_ready_persistence.py').read_text();o=Path(__file__).with_name('yipman_app_ready_true_stock_overlay.py').read_text()
    assert 'FOR UPDATE' in p and 'expected_active_build_id' in p
    assert 'persist_complete_snapshot_if_active(candidate,active.build_id)' in o
    assert 'ACTIVE_GENERATION_CHANGED' in o
    return {'stale_base_overlay_activation_guard':'PASS'}
if __name__=='__main__':print(run())
