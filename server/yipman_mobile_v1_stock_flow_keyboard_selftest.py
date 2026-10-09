from pathlib import Path


def run():
    text = Path(__file__).with_name('yipman_mobile_v1_stock_flow_actions.py').read_text()
    script = text.split("_SCRIPT =", 1)[1]
    assert 'input.focus();' not in script
    assert "input.dispatchEvent(new Event('input',{bubbles:true}))" in script
    return {
        'stock_flow_quick_check_does_not_force_keyboard': 'PASS',
        'stock_flow_quick_check_still_triggers_search': 'PASS',
    }


if __name__ == '__main__':
    print(run())
