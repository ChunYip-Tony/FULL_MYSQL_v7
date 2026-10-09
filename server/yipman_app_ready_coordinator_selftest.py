from __future__ import annotations

"""Dependency-light regression checks for the App Ready rebuild coordinator.

Run from server/: python yipman_app_ready_coordinator_selftest.py
"""

import threading
import time

import yipman_app_ready_api as subject


def main() -> None:
    original_build = subject.build_app_ready_snapshot
    original_builders = subject.app_ready_builders
    original_completed = subject.completed_through_date
    calls: list[str] = []
    entered = threading.Event()
    release = threading.Event()

    def fake_build(_builders, *, source_batch_id=None, data_through=None):
        calls.append(str(source_batch_id))
        entered.set()
        if len(calls) == 1:
            assert release.wait(2), "first build was not released"
        return object()

    class FakeDate:
        def isoformat(self):
            return "2026-10-08"

    try:
        subject.build_app_ready_snapshot = fake_build
        subject.app_ready_builders = lambda: {}
        subject.completed_through_date = lambda: FakeDate()
        with subject._COORDINATOR_LOCK:
            subject._WORKER_RUNNING = False
            subject._PENDING_SOURCE = None

        assert subject.request_app_ready_rebuild(source_batch_id="FIRST") is True
        assert entered.wait(2), "worker did not start"

        # Multiple requests during the active build must not disappear. They
        # coalesce to the newest source because that rebuild reads current truth.
        assert subject.request_app_ready_rebuild(source_batch_id="SECOND") is True
        assert subject.request_app_ready_rebuild(source_batch_id="THIRD") is True
        running, pending = subject._coordinator_status()
        assert running is True
        assert pending == "THIRD", (running, pending)

        release.set()
        deadline = time.time() + 2
        while time.time() < deadline:
            running, pending = subject._coordinator_status()
            if not running:
                break
            time.sleep(0.01)
        assert running is False
        assert pending is None
        assert calls == ["FIRST", "THIRD"], calls

        # Direct invocation with None used to be a silent no-op.
        calls.clear()
        subject.rebuild_app_ready_snapshot(source_batch_id=None)
        assert calls == ["UNSPECIFIED"], calls

        print("rebuild request coalescing PASS")
        print("worker startup race guard PASS")
        print("direct rebuild normalization PASS")
    finally:
        subject.build_app_ready_snapshot = original_build
        subject.app_ready_builders = original_builders
        subject.completed_through_date = original_completed
        with subject._COORDINATOR_LOCK:
            subject._WORKER_RUNNING = False
            subject._PENDING_SOURCE = None


if __name__ == "__main__":
    main()
