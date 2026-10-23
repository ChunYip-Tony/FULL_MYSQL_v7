"""A complete but stale durable generation must not freeze Home indefinitely."""
from datetime import datetime
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock, patch

import yipman_app_ready_recovery as subject


class PublicationTests(TestCase):
    def setUp(self):
        self.snapshot = SimpleNamespace(source_batch_id="54", started_at="2026-10-16T17:28:04+00:00",
                                        completed_at="2026-10-16T17:29:31+00:00", data_through="2026-10-15")
        self.serving = {"batch_id": 73, "updated_at": datetime(2026, 10, 23, 7, 50),
                        "processing_status": "QUICK_CHECK_READY_WITH_HOLDS"}

    def test_october_15_snapshot_recovers_from_october_23_publication(self):
        self.assertTrue(subject.publication_needs_rebuild(self.snapshot, self.serving))

    def test_same_batch_republication_also_recovers(self):
        self.serving["batch_id"] = 54
        self.assertTrue(subject.publication_needs_rebuild(self.snapshot, self.serving))

    def test_publication_during_build_needs_next_pass(self):
        self.serving["updated_at"] = "2026-10-16T17:29:00Z"
        self.assertTrue(subject.publication_needs_rebuild(self.snapshot, self.serving))

    def test_unchanged_source_does_not_rebuild_for_old_business_date(self):
        self.serving["updated_at"] = "2026-10-16T17:28:04Z"
        self.assertFalse(subject.publication_needs_rebuild(self.snapshot, self.serving))

    def test_timezone_offsets_are_compared_as_instants(self):
        self.serving["updated_at"] = "2026-10-16T10:27:00-07:00"
        self.assertFalse(subject.publication_needs_rebuild(self.snapshot, self.serving))

    def test_missing_snapshot_recovers(self):
        self.assertTrue(subject.publication_needs_rebuild(None, self.serving))

    def test_incomplete_source_cannot_trigger_build(self):
        for state in ["PHASE2C_READY", "FAILED", None]:
            with self.subTest(state=state):
                self.serving["processing_status"] = state
                self.assertFalse(subject.publication_needs_rebuild(self.snapshot, self.serving))

    def test_missing_source_or_date_cannot_trigger_build(self):
        for serving in [{}, {**self.serving, "batch_id": None}, {**self.serving, "updated_at": "bad"}]:
            self.assertFalse(subject.publication_needs_rebuild(None, serving))


class ReconciliationTests(TestCase):
    def setUp(self):
        PublicationTests.setUp(self)
        self.request = Mock()
        self.running = Mock(return_value=(False, None))
        self.pending = Mock(return_value=False)
        self.refresh = Mock()
        self.active = Mock(return_value=self.snapshot)
        self.read = Mock(return_value=self.serving)
        modules = {
            "pipeline_priority": SimpleNamespace(pipeline_pending=self.pending),
            "yipman_app_ready_api": SimpleNamespace(_coordinator_status=self.running, request_app_ready_rebuild=self.request),
            "yipman_app_ready_readers": SimpleNamespace(refresh_hot_cache_if_stale=self.refresh),
            "yipman_app_ready_snapshot": SimpleNamespace(APP_READY_SNAPSHOTS=SimpleNamespace(active=self.active)),
        }
        self.addCleanup(patch.stopall)
        patch.dict("sys.modules", modules).start()
        patch.object(subject, "_serving_publication", self.read).start()

    def test_requests_existing_coordinator_and_keeps_active_generation(self):
        subject.reconcile_app_ready_source()
        self.request.assert_called_once_with(source_batch_id="73")
        self.assertEqual(subject.recovery_status()["state"], "REBUILD_REQUESTED")
        self.assertEqual(self.snapshot.source_batch_id, "54")

    def test_running_build_is_not_queued_repeatedly(self):
        self.running.return_value = (True, None)
        subject.reconcile_app_ready_source()
        self.request.assert_not_called()
        self.read.assert_not_called()

    def test_pipeline_has_priority(self):
        self.pending.return_value = True
        subject.reconcile_app_ready_source()
        self.request.assert_not_called()
        self.read.assert_not_called()
        self.assertEqual(subject.recovery_status()["state"], "WAITING_FOR_PIPELINE")

    def test_new_shared_generation_prevents_redundant_build(self):
        self.refresh.side_effect = lambda: setattr(self.snapshot, "started_at", "2026-10-23T08:00:00Z")
        subject.reconcile_app_ready_source()
        self.request.assert_not_called()

    def test_failed_check_retries_on_next_pass(self):
        self.read.side_effect = [RuntimeError("database unavailable"), self.serving]
        with self.assertLogs(subject._LOG, level="ERROR"):
            subject.reconcile_app_ready_source()
        self.assertEqual(subject.recovery_status()["state"], "CHECK_FAILED")
        subject.reconcile_app_ready_source()
        self.request.assert_called_once_with(source_batch_id="73")


if __name__ == "__main__":
    main()
