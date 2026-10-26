import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'server'))
from migration_writer_audit import grant_evidence, classified_counts
from migration_writer_preflight import preflight_inventory


class Cursor:
    def __init__(self, denied=False):
        self.queries, self.result, self.denied = [], [], denied

    def execute(self, query):
        query = ' '.join(query.split())
        self.queries.append(query)
        assert query.startswith(('SELECT ', 'SHOW ')), query
        assert not any(word in query.lower() for word in ('authentication_string', 'password', 'user_attributes', 'host,plugin')), query
        if 'FROM mysql.user' in query:
            if self.denied:
                raise RuntimeError('do not expose private errors')
            self.result = [{'User':'secret_user', 'Host':'secret_host', 'account_locked':'N'}]
        elif query.startswith('SHOW GRANTS'):
            self.result = [{'grant': 'GRANT SELECT, INSERT ON *.* TO `secret_user`@`secret_host` WITH GRANT OPTION'}, {'grant':'REVOKE INSERT ON `private_schema`.* FROM `secret_user`@`secret_host`'}]
        elif 'SELECT TABLE_NAME,TABLE_TYPE,ENGINE' in query:
            self.result = [{'TABLE_NAME':'ingest_file','TABLE_TYPE':'BASE TABLE','ENGINE':'InnoDB'}, {'TABLE_NAME':'finder_department_head','TABLE_TYPE':'BASE TABLE','ENGINE':'InnoDB'}, {'TABLE_NAME':'unclassified','TABLE_TYPE':'VIEW','ENGINE':None}]
        elif 'COUNT(*) AS row_count' in query:
            self.result = [{'row_count':2}]
        elif 'information_schema.PROCESSLIST p' in query:
            self.result = [{'session_fingerprint':'session-hash','audit_self':False,'same_login_name':True,'schema_scope':'CURRENT_DATABASE','command':'Sleep','age_seconds':3,'transaction_state':None,'transaction_read_only':None,'rows_modified':None,'rows_locked':None}]
        else:
            self.result = []

    def fetchall(self): return self.result
    def fetchone(self): return self.result[0]


class PreflightTests(unittest.TestCase):
    def run_audit(self, denied=False):
        cur = Cursor(denied)
        result = preflight_inventory(cur, {'schema_name':'private_schema','account':'secret_user@secret_host'}, {'ingest_file'}, grant_evidence, classified_counts)
        return cur, result

    def test_account_scope_table_classification_and_session_owner_are_read_only(self):
        cur, result = self.run_audit()
        account = result['accounts']['accounts'][0]
        self.assertTrue(account['current_account'])
        self.assertEqual(account['grants']['scoped_grants'][1]['effect'], 'RESTRICTION')
        self.assertEqual([r['scope'] for r in result['tables']['tables']], ['SEAFOOD_EXPORT','SHARED_DEPARTMENT_STORE','NOT_CLASSIFIED'])
        self.assertEqual(result['tables']['tables'][1]['rows'], 2)
        self.assertTrue(result['sessions']['login_match_is_not_authenticated_identity'])
        self.assertFalse(result['effective_writer_inventory_complete'])
        self.assertFalse(result['database_controls_changed'])
        for secret in ['secret_user','secret_host','private_schema']:
            self.assertNotIn(secret, json.dumps(result))

    def test_denied_account_metadata_stays_unknown(self):
        cur, result = self.run_audit(True)
        self.assertFalse(result['accounts']['available'])
        self.assertFalse(result['effective_writer_inventory_complete'])
        self.assertNotIn('private errors', json.dumps(result))


if __name__ == '__main__': unittest.main()
