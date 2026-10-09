from pathlib import Path


def run():
    text = Path(__file__).with_name('yipman_mobile_v1_pwa.py').read_text()
    assert 'V1_BASE = "/app/yipman-v1/"' in text
    assert '/app/yipman-v1-rc/' not in text
    assert 'scope:\'" not in text  # guard malformed generated JS fragments
    assert "navigator.serviceWorker.register('{V1_BASE}sw.js'" in text
    assert 'yipman-v1-standalone-v3' in text
    return {
        'official_v1_scope_only_contract': 'PASS',
        'rc_scope_not_injected_contract': 'PASS',
        'official_service_worker_contract': 'PASS',
    }


if __name__ == '__main__':
    print(run())
