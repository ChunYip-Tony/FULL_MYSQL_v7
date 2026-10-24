"""Exercise the shared workload budget and failure paths without live data."""
import threading
import unittest
from unittest.mock import patch

import background_analysis_budget as budget
import yipman_app_ready_snapshot as snapshots
import yipman_app_ready_persistence as persistence
import yipman_app_ready_api as coordinator
import yipman_app_ready_recovery as recovery


class SnapshotFailureTests(unittest.TestCase):
    def setUp(self):
        self.store = snapshots.AppReadySnapshotStore()
        self.patch = patch.object(snapshots, 'APP_READY_SNAPSHOTS', self.store)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.builders = {n: lambda: {'rows': [{'upc': '24057500000'}]}
                         for n in snapshots.SNAPSHOT_SECTIONS}

    def build(self):
        return snapshots.build_app_ready_snapshot(self.builders, source_batch_id='test')

    def test_snapshot_waits_for_heavy_cache_and_health_diagnostics_do_not_wait(self):
        entered, release, snapshot_entered, finished = (threading.Event() for _ in range(4))
        errors = []
        @budget.serialized_background
        def cache():
            entered.set()
            if not release.wait(3):
                raise AssertionError('test cache was not released')
        def section():
            snapshot_entered.set()
            return {'rows': []}
        self.builders['stock_flow'] = section
        def rebuild():
            try:
                self.build()
            except Exception as exc:
                errors.append(exc)
            finally:
                finished.set()
        with patch.object(persistence, 'persist_complete_snapshot'):
            worker = threading.Thread(target=cache)
            snapshot = threading.Thread(target=rebuild)
            worker.start()
            self.assertTrue(entered.wait(1))
            snapshot.start()
            try:
                self.assertFalse(snapshot_entered.wait(.05))
                self.assertEqual(budget.background_analysis_status()['active'], 'cache')
                self.assertIsNone(self.store.active())
            finally:
                release.set()
                worker.join(3)
                snapshot.join(3)
            self.assertTrue(finished.is_set())
            self.assertEqual(errors, [])
            self.assertEqual(self.store.status()['status'], 'APP_READY')
            self.assertIsNone(budget.background_analysis_status()['active'])

    def test_failed_builder_releases_candidate_and_keeps_active(self):
        with patch.object(persistence, 'persist_complete_snapshot'):
            old = self.build()
        def fail():
            raise RuntimeError('builder unavailable')
        self.builders['inventory'] = fail
        with self.assertRaisesRegex(RuntimeError, 'builder unavailable'):
            self.build()
        self.assertIs(self.store.active(), old)
        self.assertEqual(self.store._building.sections, {})
        self.assertEqual(self.store.status()['status'], 'FAILED')
        self.assertTrue(self.store.status()['serving_app_ready'])
        self.assertIsNone(budget.background_analysis_status()['active'])

    def test_failed_persist_never_promotes_or_retains_large_candidate(self):
        with patch.object(persistence, 'persist_complete_snapshot'):
            old = self.build()
        with patch.object(persistence, 'persist_complete_snapshot', side_effect=RuntimeError('save failed')):
            with self.assertRaisesRegex(RuntimeError, 'save failed'):
                self.build()
        self.assertIs(self.store.active(), old)
        self.assertEqual(self.store._building.sections, {})
        self.assertEqual(self.store.status()['status'], 'FAILED')

    def test_oversized_generation_cannot_replace_active_through_either_writer(self):
        with patch.object(persistence, 'snapshot_size_limit', return_value=100), \
             patch.object(persistence, 'db_conn') as db:
            for save in (lambda: persistence.persist_complete_snapshot({'text': '魚' * 100}),
                         lambda: persistence.persist_complete_snapshot_if_active({'text': 'x' * 1000}, 'old')):
                with self.assertRaisesRegex(RuntimeError, 'SAFE_LOAD_LIMIT'):
                    save()
            db.assert_not_called()

    def test_allowed_generation_roundtrips_with_same_size_limit(self):
        from snapshot_graph import loads
        payload = {'rows': [{'name': '魚', 'quantity': 12.5}]}
        encoded = persistence._persistable_payload(payload)
        self.assertLessEqual(len(encoded.encode('utf-8')), persistence.snapshot_size_limit())
        self.assertEqual(loads(encoded), payload)


class RebuildBackoffTests(unittest.TestCase):
    def setUp(self):
        for name, value in (('_WORKER_RUNNING', False), ('_PENDING_SOURCE', None),
                            ('_REBUILD_FAILURES', 0), ('_RETRY_NOT_BEFORE', 0.0)):
            patcher = patch.object(coordinator, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_backoff_preserves_latest_request_and_success_resets_it(self):
        with patch.object(coordinator.time, 'monotonic', return_value=100):
            coordinator._finish_failed_worker('failed')
            with patch.object(coordinator.threading, 'Thread') as thread:
                self.assertFalse(coordinator.request_app_ready_rebuild(source_batch_id='newer'))
                self.assertFalse(coordinator.request_app_ready_rebuild(source_batch_id='latest'))
                thread.assert_not_called()
            self.assertEqual(coordinator._coordinator_status(), (False, 'latest'))
            self.assertEqual(coordinator.rebuild_retry_status()['rebuild_retry_after_seconds'], 60)
        # Run the real worker body deterministically after the cooldown.
        with patch.object(coordinator.time, 'monotonic', return_value=161), \
             patch.object(coordinator.threading, 'Thread') as thread, \
             patch.object(coordinator, 'app_ready_builders', return_value={}), \
             patch.object(coordinator, 'build_app_ready_snapshot') as build, \
             patch('pipeline_priority.wait_for_pipeline_idle'):
            self.assertTrue(coordinator.request_app_ready_rebuild(source_batch_id='latest'))
            thread.call_args.kwargs['target']()
            self.assertEqual(build.call_args.kwargs['source_batch_id'], 'latest')
        self.assertEqual(coordinator._coordinator_status(), (False, None))
        self.assertEqual(coordinator.rebuild_retry_status()['rebuild_consecutive_failures'], 0)

    def test_repeated_failures_have_bounded_backoff(self):
        with patch.object(coordinator.time, 'monotonic', return_value=100):
            for _ in range(25):
                coordinator._finish_failed_worker('failed')
            self.assertEqual(coordinator.rebuild_retry_status()['rebuild_retry_after_seconds'], 900)

    def test_queued_true_stock_refresh_is_retried_even_without_new_publication(self):
        with (patch.object(coordinator, '_coordinator_status', return_value=(False, 'TRUE_STOCK:new')),
              patch.object(coordinator, 'request_app_ready_rebuild', return_value=False) as request,
              patch('pipeline_priority.pipeline_pending', return_value=False),
              patch('yipman_app_ready_readers.refresh_hot_cache_if_stale'),
              patch.object(recovery, '_serving_publication', return_value={}),
              patch.object(recovery, '_STATUS', {})):
            recovery.reconcile_app_ready_source()
            request.assert_called_once_with(source_batch_id='TRUE_STOCK:new')
            self.assertEqual(recovery.recovery_status()['state'], 'REBUILD_BACKOFF')


if __name__ == '__main__':
    unittest.main()
