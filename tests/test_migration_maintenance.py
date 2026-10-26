import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'server'))


class MaintenanceTests(unittest.TestCase):
    def test_isolated_app_only_exposes_health_and_existing_migration_reads(self):
        fake = types.ModuleType('db')
        fake.db_conn = lambda **kwargs: self.fail('No SQL connection at import or health')
        for name in ('sites_migration_maintenance', 'sites_migration_export'):
            sys.modules.pop(name, None)
        operational = ('api', 'api_entry_v504', 'worker', 'worker_v482',
                       'backoffice_runtime', 'yipman_app_ready_api')
        before = {name for name in operational if name in sys.modules}
        with patch.dict(sys.modules, {'db': fake}):
            module = importlib.import_module('sites_migration_maintenance')
            paths = {route.path: route for route in module.app.routes}
            self.assertEqual(set(paths), {'/healthz', '/v1/migration/sites/writer-audit',
                                         '/v1/migration/sites/snapshot'})
            self.assertTrue(all(route.methods == {'GET'} for route in paths.values()))
            health = paths['/healthz'].endpoint()
            self.assertFalse(health['business_api_enabled'])
            self.assertFalse(health['worker_enabled'])
            self.assertFalse(health['freeze_established'])
            self.assertEqual(before, {name for name in operational if name in sys.modules})
        for name in ('sites_migration_maintenance', 'sites_migration_export'):
            sys.modules.pop(name, None)


if __name__ == '__main__':
    unittest.main()
