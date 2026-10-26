import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('writer_audit_under_test', Path(__file__).parents[1] / 'server' / 'migration_writer_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Cursor:
    def __init__(self, fail=None):
        self.fail, self.queries, self.result, self.closed = fail, [], [], False

    def execute(self, query):
        query = ' '.join(query.split())
        self.queries.append(query)
        assert query.startswith(('SELECT ', 'SHOW ')), query
        if self.fail and self.fail in query:
            raise RuntimeError('database detail must not leak')
        if query.startswith('SELECT DATABASE()'):
            self.result = [{'schema_name': 'private_seafood', 'version': '8.4.8', 'account': 'private_user@private_host'}]
        elif query.startswith('SHOW GRANTS'):
            self.result = [{'grant': 'GRANT SELECT, PROCESS ON *.* TO `private_user`@`private_host` WITH GRANT OPTION'}, {'grant': 'GRANT `private_role`@`private_host` TO `private_user`@`private_host`'}]
        elif query.startswith('SELECT CURRENT_ROLE()'):
            self.result = [{'active_roles': '`private_role`@`private_host`', 'partial_revokes': 0, 'read_only': 0, 'super_read_only': 0}]
        elif 'PROCESSLIST WHERE DB=DATABASE()' in query:
            self.result = [{'COMMAND': 'Sleep', 'connection_count': 2}]
        elif 'information_schema.PROCESSLIST GROUP' in query:
            self.result = [{'schema_scope': 'OTHER_DATABASE', 'command': 'Query', 'connection_count': 1}, {'schema_scope': 'NO_DEFAULT_DATABASE', 'command': 'Sleep', 'connection_count': 3}]
        elif 'information_schema.INNODB_TRX' in query:
            self.result = [{'state': 'RUNNING', 'read_only': 0, 'transaction_count': 1}]
        elif 'information_schema.KEY_COLUMN_USAGE' in query:
            self.result = [{'boundary': 'REFERENCED_BY_OTHER_DATABASE', 'foreign_key_column_count': 2}]
        elif 'information_schema.TABLES' in query:
            self.result = [{'engine': 'InnoDB', 'table_count': 66}]
        elif 'FROM ingest_file ' in query:
            self.result = [{'status': 'UPLOADED', 'file_count': 1}]
        elif 'FROM pipeline_run ' in query:
            assert 'processing_status' in query and 'run_status' not in query
            self.result = [{'stage_name': 'CHATGPT_SHEET_PUBLISH', 'status': 'STARTED', 'run_count': 1}]
        else:
            self.result = []

    def fetchone(self):
        return self.result[0]

    def fetchall(self):
        return self.result

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, fail=None):
        self.cur, self.rolled_back, self.readonly = Cursor(fail), False, False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def start_transaction(self, readonly):
        self.readonly = readonly

    def cursor(self, **kwargs):
        return self.cur

    def rollback(self):
        self.rolled_back = True


class AuditBoundaryTests(unittest.TestCase):
    def test_qualified_sessions_roles_and_work_are_visible_without_secrets(self):
        conn = Connection()
        result = audit.writer_inventory(lambda **kwargs: conn)
        self.assertTrue(conn.readonly and conn.rolled_back and conn.cur.closed)
        self.assertEqual(result['connections']['counts'], {'Sleep': 2})
        self.assertEqual(len(result['all_visible_connections']['groups']), 2)
        self.assertTrue(result['all_visible_connections']['qualified_cross_schema_writes_not_excluded'])
        self.assertTrue(result['privileges']['grant_option_observed'])
        self.assertTrue(result['role_and_server_controls']['active_roles_present'])
        self.assertFalse(result['privileges']['effective_role_grants_expanded'])
        self.assertEqual(result['foreign_key_boundary']['groups'][0]['boundary'], 'REFERENCED_BY_OTHER_DATABASE')
        self.assertEqual(result['pipeline_work']['groups'][0]['stage_name'], 'CHATGPT_SHEET_PUBLISH')
        self.assertEqual(result['uploaded_work']['groups'][0]['file_count'], 1)
        self.assertEqual(result['freeze_state'], 'NOT_ESTABLISHED')
        self.assertFalse(result['external_writer_inventory_complete'])
        self.assertFalse(result['database_controls_changed'])
        for private in ('private_user', 'private_host', 'private_role', 'private_seafood'):
            self.assertNotIn(private, json.dumps(result))

    def test_missing_privilege_never_becomes_empty_complete_inventory(self):
        result = audit.writer_inventory(lambda **kwargs: Connection('INNODB_TRX'))
        self.assertFalse(result['visible_transactions']['available'])
        self.assertTrue(result['all_visible_connections']['available'])
        self.assertNotIn('database detail', json.dumps(result))
        self.assertFalse(result['external_writer_inventory_complete'])

    def test_bounds_and_grant_option_are_explicit(self):
        class Many:
            def execute(self, query): pass
            def fetchall(self): return [{'count': n} for n in range(101)]
        result = audit.classified_counts(Many(), 'SELECT 1', ('count',))
        self.assertEqual(len(result['groups']), 100)
        self.assertTrue(result['truncated'])
        grants = audit.grant_evidence(['GRANT SELECT ON `secret`.* TO `user`@`host`'], 'secret')
        self.assertFalse(grants['grant_option_observed'])
        self.assertEqual(grants['grants'][0]['scope'], 'CURRENT_DATABASE')


if __name__ == '__main__':
    unittest.main()
