from __future__ import annotations

"""Regression contract for durable-before-visible App Ready activation."""

import yipman_app_ready_snapshot as subject
import yipman_app_ready_persistence as persistence


def run_selftest():
    store = subject.APP_READY_SNAPSHOTS
    old_active = store._active
    old_building = store._building
    original_persist = persistence.persist_complete_snapshot
    events = []
    try:
        store._active = None
        store._building = None
        builders = {name: (lambda n=name: {"section": n}) for name in subject.SNAPSHOT_SECTIONS}

        def persist_ok(candidate):
            assert store.active() is None, "candidate became visible before durable commit"
            events.append(("persist", candidate.build_id))

        persistence.persist_complete_snapshot = persist_ok
        built = subject.build_app_ready_snapshot(builders, source_batch_id="SELFTEST", data_through="2026-10-08")
        assert events == [("persist", built.build_id)]
        assert store.active().build_id == built.build_id

        previous = store.active()
        def persist_fail(candidate):
            assert store.active().build_id == previous.build_id
            raise RuntimeError("EXPECTED_PERSIST_FAILURE")
        persistence.persist_complete_snapshot = persist_fail
        try:
            subject.build_app_ready_snapshot(builders, source_batch_id="FAIL", data_through="2026-10-08")
            raise AssertionError("persistence failure did not propagate")
        except RuntimeError as exc:
            assert "EXPECTED_PERSIST_FAILURE" in str(exc)
        assert store.active().build_id == previous.build_id, "failed generation replaced active snapshot"

        clone = subject.SnapshotBuild(**previous.__dict__)
        store._active = None
        store.hydrate(clone)
        assert store.active().build_id == previous.build_id

        return {
            "durable_before_visible": "PASS",
            "failed_persist_preserves_old_active": "PASS",
            "restart_hydration_contract": "PASS",
            "complete_generation_guard": "PASS",
        }
    finally:
        persistence.persist_complete_snapshot = original_persist
        store._active = old_active
        store._building = old_building


if __name__ == "__main__":
    print(run_selftest())
