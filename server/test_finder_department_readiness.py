import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient
from finder_department_readiness import configuration_ready, database_ready, readiness, TABLES, VIEWS
from finder_department_start import port_from_environment
from finder_department_service import app


class Cursor:
    def __init__(self, objects=None, version='8.4.8'):
        self.objects = TABLES | VIEWS if objects is None else objects
        self.version = version
        self.queries = []
        self.closed = False

    def execute(self, sql): self.queries.append(sql)
    def fetchone(self): return (self.version,)
    def fetchall(self):
        return [(name,) for name in self.objects] if 'information_schema' in self.queries[-1] else []
    def close(self): self.closed = True


class ReadinessTests(unittest.TestCase):
    def test_liveness_is_independent_but_readiness_refuses_missing_configuration(self):
        with patch.dict(os.environ, {}, clear=True), TestClient(app) as client:
            self.assertEqual(client.get('/healthz').status_code, 200)
            response = client.get('/readyz')
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()['status'], 'not_ready')
            self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_readiness_never_leaks_database_errors_and_does_not_contact_db_without_config(self):
        def fail(): raise RuntimeError('mysql://private-user:private-password@private-host')
        self.assertEqual(readiness(lambda: True, fail)['status'], 'not_ready')
        calls = []
        self.assertEqual(readiness(lambda: False, lambda: calls.append(1))['status'], 'not_ready')
        self.assertEqual(calls, [])
        self.assertEqual(readiness(lambda: True, lambda: True)['status'], 'ready')

    def test_distinct_department_credentials_and_verified_tls_are_required(self):
        base = {'FINDER_STORE_TOKEN_MEAT':'M'*64, 'FINDER_STORE_TOKEN_PRODUCE':'P'*64,
                'FULLMYSQL_WORK_TOKEN':'separate-service-token',
                'FULLMYSQL_DATABASE_URL':'mysql://test:password@db.example:25060/full_mysql',
                'FULLMYSQL_DB_CA_CERT':'test-certificate'}
        with patch.dict(os.environ, base, clear=True), patch('config.Settings.ca_path', return_value='/tmp/test-ca'):
            self.assertTrue(configuration_ready())
            with patch.dict(os.environ, {'FINDER_STORE_TOKEN_PRODUCE':'M'*64}):
                self.assertFalse(configuration_ready())
            with patch('config.Settings.ca_path', return_value=None):
                self.assertFalse(configuration_ready())

    def test_database_checks_are_read_only_and_require_all_objects_and_mysql84(self):
        for objects, version, expected in ((TABLES|VIEWS,'8.4.8',True), (TABLES,'8.4.8',False), (TABLES|VIEWS,'8.0.42',False)):
            cursor = Cursor(objects, version)
            class Connection:
                rolled_back = False
                def cursor(self): return cursor
                def rollback(self): self.rolled_back = True
            connection = Connection()
            @contextmanager
            def connect(): yield connection
            self.assertEqual(database_ready(connect), expected)
            self.assertTrue(connection.rolled_back)
            self.assertTrue(cursor.closed)
            self.assertTrue(all(query.startswith('SELECT ') for query in cursor.queries))

    def test_host_port_is_respected_and_invalid_values_fail(self):
        with patch.dict(os.environ, {'PORT':'9123'}): self.assertEqual(port_from_environment(), 9123)
        for value in ('0', '65536', 'not-a-port'):
            with patch.dict(os.environ, {'PORT':value}), self.assertRaises(RuntimeError): port_from_environment()


if __name__ == '__main__': unittest.main()
