"""Exercise the rebuild ownership query against retained historical rows."""
import ast
import sqlite3
import unittest
from pathlib import Path

source = Path(__file__).resolve().parents[1] / 'server' / 'api.py'
func = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'web_upload_rebuild_phase3')
query = next(n.value for n in ast.walk(func) if isinstance(n, ast.Constant) and isinstance(n.value, str) and 'AS operational_mismatch_rows' in n.value)
condition = next(n.test for n in ast.walk(func) if isinstance(n, ast.If) and 'serving.get' in ast.unparse(n.test) and 'operational_mismatch_rows' in ast.unparse(n.test))

status_source = source.with_name('v7_ingest.py')
status_tree = ast.parse(status_source.read_text())
status_query = next(n.value for n in ast.walk(status_tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and 'AS operational_mismatch_rows' in n.value)
status_condition = next(n.value for n in ast.walk(status_tree) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='current_serving_bound' for t in n.targets))

class RebuildRevisionTests(unittest.TestCase):
    def blocked(self, rows, bid=71):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE quick_check_current(publish_batch_id INTEGER,quick_check_status TEXT)')
        db.executemany('INSERT INTO quick_check_current VALUES (?,?)', rows)
        serving = dict(db.execute(query.replace('%s','?'), (bid,)).fetchone())
        status_owner = dict(db.execute(status_query.replace('%s','?'), (bid,)).fetchone())
        db.close()
        blocked = eval(compile(ast.Expression(condition), str(source), 'eval'), {}, {'serving':serving,'bid':bid})
        allowed = eval(compile(ast.Expression(status_condition), str(status_source), 'eval'), {}, {'serving_owner':status_owner,'bid':bid})
        self.assertEqual(blocked, not allowed, 'Read-only UI status must match the rebuild guard')
        return blocked

    def test_retained_history_allows_latest_rebuild(self):
        self.assertFalse(self.blocked([(70,'HISTORICAL_ONLY'),(71,'READY'),(71,'QA_HOLD')]))
    def test_uniform_current_snapshot_allowed(self):
        self.assertFalse(self.blocked([(71,'READY')]))
    def test_newer_revision_rejects_old_rebuild(self):
        self.assertTrue(self.blocked([(70,'HISTORICAL_ONLY'),(72,'READY')]))
    def test_unpublished_requested_revision_rejected(self):
        self.assertTrue(self.blocked([(70,'READY')]))
    def test_old_operational_rows_rejected(self):
        self.assertTrue(self.blocked([(70,'READY'),(71,'READY')]))
    def test_empty_and_unowned_operational_rejected(self):
        self.assertTrue(self.blocked([]))
        self.assertTrue(self.blocked([(None,'READY'),(71,'READY')]))
        self.assertTrue(self.blocked([(70,None),(71,'READY')]))

if __name__=='__main__':unittest.main()
