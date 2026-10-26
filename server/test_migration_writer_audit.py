import json
from contextlib import contextmanager
from migration_writer_audit import grant_evidence, writer_inventory


def test_grant_summary_never_returns_accounts_or_authentication():
    result = grant_evidence(["GRANT SELECT, INSERT, UPDATE, TRIGGER ON `seafood`.* TO 'sensitive'@'host' IDENTIFIED BY PASSWORD 'secret-hash'",
                             "GRANT PROCESS ON *.* TO 'sensitive'@'host'", "GRANT `secret-role`@`host` TO 'sensitive'@'host'"], 'seafood')
    assert result['grants'][0] == {'scope': 'CURRENT_DATABASE', 'privileges': ['SELECT', 'INSERT', 'UPDATE', 'TRIGGER']}
    assert result['grants'][1]['scope'] == 'GLOBAL'
    assert result['role_or_unparsed_grants_present'] is True
    assert all(word not in json.dumps(result) for word in ['sensitive', 'secret', 'host'])


def test_read_only_inventory_and_visibility_limits():
    commands = []
    class Cursor:
        def execute(self, sql):
            assert sql.startswith(('SELECT ', 'SHOW ')); commands.append(sql)
            if sql.startswith('SELECT DATABASE'): self.rows = [{'schema_name': 'seafood', 'version': '8.0.fixture', 'account': 'sensitive@host'}]
            elif sql.startswith('SHOW GRANTS'): self.rows = [{'grant': "GRANT SELECT, INSERT ON `seafood`.* TO 'sensitive'@'host'"}]
            elif 'PROCESSLIST' in sql: self.rows = [{'COMMAND': 'Sleep', 'connection_count': 2}]
            elif 'EVENTS' in sql: raise RuntimeError('secret database error')
        def fetchone(self): return self.rows[0]
        def fetchall(self): return self.rows
        def close(self): commands.append('CLOSE')
    class Connection:
        def start_transaction(self, **options): assert options == {'readonly': True}
        def cursor(self, **options): return Cursor()
        def rollback(self): commands.append('ROLLBACK')
    @contextmanager
    def connect(**options): yield Connection()
    result = writer_inventory(connect)
    assert result['connections']['visibility'] == 'POTENTIALLY_ACCOUNT_ONLY'
    assert result['database_events']['available'] is False
    assert result['external_writer_inventory_complete'] is False
    assert result['freeze_state'] == 'NOT_ESTABLISHED'
    assert result['database_controls_changed'] is False
    assert commands[-2:] == ['CLOSE', 'ROLLBACK']
    assert all(word not in json.dumps(result) for word in ['sensitive', 'secret', 'host'])
