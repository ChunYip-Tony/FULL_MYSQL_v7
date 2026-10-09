from pathlib import Path


def run():
    text = Path(__file__).with_name('yipman_mobile_v1_stock_flow_home.py').read_text()
    assert '/app/yipman-v1-rc/api/stock-flow' not in text
    assert "/api/yipman/app-ready/section/stock_flow" in text
    assert "credentials:'same-origin'" in text
    return {
        'rc_stock_flow_dependency_removed': 'PASS',
        'app_ready_stock_flow_read_path_contract': 'PASS',
    }


if __name__ == '__main__':
    print(run())
