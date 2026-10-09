from pathlib import Path

src=Path(__file__).with_name('yipman_app_ready_true_stock_overlay.py').read_text()
assert '_STALE_DECISION_KEYS' in src
assert 'pre_true_stock_decision_audit' in src
assert 'row[key]=None' in src
assert 'INVENTORY_FAMILY_RECALC_PENDING' in src
assert 'operational_decision_code' in src and 'DATA_NEEDED' in src
print('PASS: True Stock overlay cannot expose stale operational recommendations')
