from __future__ import annotations

"""Dependency-light contract checks for the App Ready serving layer."""

from yipman_app_ready_snapshot import AppReadySnapshotStore, SNAPSHOT_SECTIONS


def run_app_ready_contract_selftest() -> dict[str, str]:
    store = AppReadySnapshotStore()
    store.begin(source_batch_id="TEST-A", data_through="2026-10-08")
    for name in SNAPSHOT_SECTIONS:
        store.put_section(name, {"generation": "A", "section": name})
    first = store.promote()
    assert store.active() is first
    assert store.status()["app_ready"] is True

    # A replacement build must never leak partial sections to readers.
    store.begin(source_batch_id="TEST-B", data_through="2026-10-09")
    store.put_section(SNAPSHOT_SECTIONS[0], {"generation": "B"})
    assert store.active() is first
    assert store.active().source_batch_id == "TEST-A"
    try:
        store.promote()
    except RuntimeError:
        pass
    else:
        raise AssertionError("partial snapshot was promoted")
    assert store.active() is first

    return {
        "snapshot_build": "PASS",
        "atomic_activation": "PASS",
        "previous_snapshot_during_build": "PASS",
        "partial_snapshot_rejected": "PASS",
    }


if __name__ == "__main__":
    print(run_app_ready_contract_selftest())
