import importlib.abc
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

SERVER = Path(__file__).parents[1] / 'server'
sys.path.insert(0, str(SERVER))
import sites_cutover_gate as gate


class ProcessReplaced(BaseException):
    pass


class BusinessImportReached(BaseException):
    pass


class RejectBusinessImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname in {'api', 'api_entry_v504', 'worker', 'db', 'v7_ingest', 'health_watchdog'}:
            raise BusinessImportReached(fullname)


class CutoverGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'mode.json'
        self.patch_path = patch.object(gate, 'MODE_PATH', self.path)
        self.patch_path.start()
        self.addCleanup(self.patch_path.stop)
        self.addCleanup(self.temp.cleanup)
        self.guard = RejectBusinessImports()
        sys.meta_path.insert(0, self.guard)
        self.addCleanup(lambda: sys.meta_path.remove(self.guard))

    def mode(self, mode='NORMAL', identity=None):
        self.path.write_text(json.dumps({'mode': mode, 'cutover_id': identity}))

    def run_entrypoint(self, name):
        # Importing an already-cached business module must not hide an import.
        with patch.dict(sys.modules):
            for name_ in ('api', 'api_entry_v504', 'worker', 'db', 'v7_ingest', 'health_watchdog'):
                sys.modules.pop(name_, None)
            return runpy.run_path(str(SERVER / name), run_name='__main__')

    def test_committed_mode_is_valid_and_normal_mode_preserves_startup(self):
        with patch.object(gate, 'MODE_PATH', SERVER / 'sites_cutover_mode.json'):
            committed = gate.deployment_mode()
            self.assertIn(committed['mode'], ['NORMAL', 'ISOLATED_MIGRATION_READS'])
        self.mode()
        with patch.object(gate.os, 'execv') as execute:
            for entrypoint in ('single_service.py', 'production_bootstrap.py', 'worker_v482.py'):
                with self.subTest(entrypoint=entrypoint), self.assertRaises(BusinessImportReached):
                    self.run_entrypoint(entrypoint)
            execute.assert_not_called()

    def test_maintenance_replaces_actual_api_entrypoints_before_business_imports(self):
        self.mode('ISOLATED_MIGRATION_READS', 'seafood-sites-test')
        with patch.dict('os.environ', {'PORT': '9123'}), patch.object(gate.os, 'execv', side_effect=ProcessReplaced) as execute:
            for entrypoint in ('single_service.py', 'production_bootstrap.py'):
                with self.subTest(entrypoint=entrypoint), self.assertRaises(ProcessReplaced):
                    self.run_entrypoint(entrypoint)
                self.assertEqual(execute.call_args.args, (sys.executable, [sys.executable, '-m', 'uvicorn', 'sites_migration_maintenance:app', '--host', '0.0.0.0', '--port', '9123', '--workers', '1']))

    def test_maintenance_stops_direct_worker_without_importing_worker_or_db(self):
        self.mode('ISOLATED_MIGRATION_READS', 'seafood-sites-test')
        with self.assertRaisesRegex(SystemExit, 'worker startup disabled'):
            self.run_entrypoint('worker_v482.py')

    def test_unreadable_or_invalid_mode_stops_before_business_imports(self):
        for content in (None, '', '{}', '[]', '{"mode":"NORMAL","cutover_id":"unexpected"}', '{"mode":"ISOLATED_MIGRATION_READS","cutover_id":null}'):
            if content is None:
                self.path.unlink(missing_ok=True)
            else:
                self.path.write_text(content)
            for entrypoint in ('single_service.py', 'production_bootstrap.py', 'worker_v482.py'):
                with self.subTest(content=content, entrypoint=entrypoint), self.assertRaises(RuntimeError):
                    self.run_entrypoint(entrypoint)

    def test_reverting_mode_restores_startup_without_credentials_or_database_changes(self):
        self.mode('ISOLATED_MIGRATION_READS', 'seafood-sites-test')
        with self.assertRaises(SystemExit):
            gate.require_worker_enabled()
        self.mode()
        gate.require_worker_enabled()
        with patch.object(gate.os, 'execv') as execute:
            gate.launch_maintenance_if_requested()
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
