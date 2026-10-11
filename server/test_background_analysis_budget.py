import threading
import unittest
from background_analysis_budget import serialized_background

class BackgroundBudgetTests(unittest.TestCase):
    def test_workers_do_not_overlap_and_failure_releases_budget(self):
        active = 0
        peak = 0
        entered = threading.Event()
        release = threading.Event()
        lock = threading.Lock()
        @serialized_background
        def worker(fail=False):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            entered.set()
            release.wait(1)
            with lock:
                active -= 1
            if fail:
                raise ValueError("expected")
        errors = []
        def invoke(fail=False):
            try:
                worker(fail)
            except ValueError:
                errors.append("expected")
        threads = [threading.Thread(target=invoke, args=(i == 0,)) for i in range(3)]
        for thread in threads:
            thread.start()
        self.assertTrue(entered.wait(1))
        release.set()
        for thread in threads:
            thread.join(2)
            self.assertFalse(thread.is_alive())
        self.assertEqual(peak, 1)
        self.assertEqual(active, 0)
        self.assertEqual(errors, ["expected"])

if __name__ == "__main__":
    unittest.main()
