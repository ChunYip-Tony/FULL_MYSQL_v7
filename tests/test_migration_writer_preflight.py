import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'server'))
from migration_writer_audit import grant_evidence, classified_counts
from migration_writer_preflight import preflight_inventory, account_metadata


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
        elif 'GROUP BY department_code,analysis_status' in query:
            self.result = [{'department_code':'400', 'analysis_status':'READY', 'row_count':3, 'first_source_batch':82, 'last_source_batch':82}]
        elif 'FROM analysis_layer_status' in query:
            self.result = [{'department_code':'300', 'layer_status':'PENDING_PIPELINE_ENABLEMENT', 'source_publish_batch_id':82, 'item_rows':0, 'ready_rows':0, 'hold_rows':0, 'historical_rows':0, 'family_rows':0}]
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
        self.assertEqual(result['accounts']['current_login_matches'], [account['account_fingerprint']])
        self.assertEqual(account['connection_match_class'], 'HOST_PATTERN')
        self.assertEqual(account['grants']['scoped_grants'][1]['effect'], 'RESTRICTION')
        self.assertEqual([r['scope'] for r in result['tables']['tables']], ['SEAFOOD_EXPORT','SHARED_DEPARTMENT_STORE','NOT_CLASSIFIED'])
        self.assertEqual(result['tables']['tables'][1]['rows'], 2)
        self.assertTrue(result['sessions']['login_match_is_not_authenticated_identity'])
        self.assertFalse(result['effective_writer_inventory_complete'])
        self.assertFalse(result['database_controls_changed'])
        self.assertEqual(result['department_analysis']['analysis_item_current']['groups'][0]['department_code'], '400')
        self.assertEqual(result['department_analysis']['analysis_layer_status']['groups'][0]['layer_status'], 'PENDING_PIPELINE_ENABLEMENT')
        for secret in ['secret_user','secret_host','private_schema']:
            self.assertNotIn(secret, json.dumps(result))

    def test_denied_account_metadata_stays_unknown(self):
        cur, result = self.run_audit(True)
        self.assertFalse(result['accounts']['available'])
        self.assertFalse(result['effective_writer_inventory_complete'])
        self.assertNotIn('private errors', json.dumps(result))

    def test_account_classification_never_assumes_provider_ownership(self):
        for host, expected in [('localhost', 'LOCALHOST'), ('127.0.0.1', 'LOOPBACK_ADDRESS'), ('::1', 'LOOPBACK_ADDRESS'), ('10.0.0.1', 'EXACT_IP_ADDRESS'), ('%', 'HOST_PATTERN')]:
            result = account_metadata('root', host)
            self.assertEqual(result['connection_match_class'], expected)
            self.assertEqual(result['identity_name_class'], 'ROOT_ACCOUNT_NAME')
            self.assertFalse(result['provider_ownership_verified'])
            self.assertFalse(result['business_writer_classified'])
        self.assertEqual(account_metadata('mysql.session', 'localhost')['identity_name_class'], 'MYSQL_RESERVED_SYSTEM_NAME')


if __name__ == '__main__': unittest.main()
