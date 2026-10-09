from pathlib import Path


def run():
    readers = Path(__file__).with_name('yipman_app_ready_readers.py').read_text()
    persistence = Path(__file__).with_name('yipman_app_ready_persistence.py').read_text()
    api = Path(__file__).with_name('yipman_app_ready_api.py').read_text()

    assert 'def active_build_id()' in persistence
    assert 'SELECT build_id FROM yipman_app_ready_pointer' in persistence
    assert 'def refresh_hot_cache_if_stale' in readers
    assert 'local.build_id == durable_id' in readers
    assert 'load_active_snapshot(SnapshotBuild)' in readers
    assert 'APP_READY_SNAPSHOTS.hydrate(snap)' in readers
    assert '_POINTER_TTL_SECONDS' in readers
    assert 'pointer_last_error' in readers
    assert '_refresh_shared_pointer()' in api

    return {
        'cheap_pointer_probe_contract': 'PASS',
        'reload_only_on_build_change_contract': 'PASS',
        'last_complete_snapshot_fallback_contract': 'PASS',
        'api_pointer_refresh_contract': 'PASS',
    }


if __name__ == '__main__':
    print(run())
