import unittest
from unittest.mock import patch
from decimal import Decimal
import manual_overrides as overrides
from phase3_runtime import phase3_lease, connection_diagnostics, clear_terminal_phase3_owner


class Cursor:
    def __init__(self, acquired=1, existing=None):
        self.acquired, self.existing = acquired, existing
        self.calls, self.closed = [], False
    def execute(self, sql, args=()):
        self.calls.append((sql, args))
    def fetchone(self):
        sql = self.calls[-1][0]
        if 'GET_LOCK' in sql:
            return {'acquired': self.acquired}
        if 'RELEASE_LOCK' in sql:
            return {'released': 1}
        return self.existing
    def close(self):
        self.closed = True


class Connection:
    def __init__(self, cur): self.cur = cur
    def cursor(self, **kwargs): return self.cur


class TransactionGuardTests(unittest.TestCase):
    def test_cleanup_cancels_only_terminal_matching_owner(self):
        class Owner(Cursor):
            def __init__(self, status):
                super().__init__(); self.status = status
            def fetchone(self):
                if 'IS_USED_LOCK' in self.calls[-1][0]: return {'owner':42}
                return {'pipeline_run_id':100,'processing_status':self.status} if self.status else {}
        for status in ('STARTED','QUEUED','COMPLETED',None):
            cur=Owner(status)
            self.assertFalse(clear_terminal_phase3_owner(cur,'FULLMYSQL_SECURE_API'))
            self.assertFalse(any(q.startswith('KILL') for q,_ in cur.calls))
        cur=Owner('FAILED')
        self.assertFalse(clear_terminal_phase3_owner(cur,'FULLMYSQL_SECURE_API'))
        self.assertEqual(cur.calls[-1],('KILL CONNECTION 42',()))
        self.assertEqual(cur.calls[1][1],('FULLMYSQL_SECURE_API','42'))

    def test_cleanup_requires_rechecked_owner(self):
        class Changed(Cursor):
            def fetchone(self):
                if len(self.calls)==1:return {'owner':42}
                if len(self.calls)==2:return {'pipeline_run_id':100,'processing_status':'FAILED'}
                return {'owner':43}
        cur=Changed()
        self.assertFalse(clear_terminal_phase3_owner(cur,'FULLMYSQL_SECURE_API'))
        self.assertFalse(any(q.startswith('KILL') for q,_ in cur.calls))

    def test_lease_released_on_business_failure(self):
        cur = Cursor()
        with self.assertRaisesRegex(ValueError, 'business failure'):
            with phase3_lease(Connection(cur)):
                raise ValueError('business failure')
        self.assertIn('RELEASE_LOCK', cur.calls[-1][0])
        self.assertTrue(cur.closed)

    def test_second_owner_cannot_enter_or_release_first_owner(self):
        cur = Cursor(acquired=0)
        with self.assertRaisesRegex(RuntimeError, 'ALREADY_OWNED'):
            with phase3_lease(Connection(cur)):
                self.fail('entered another owner transaction')
        self.assertFalse(any('RELEASE_LOCK' in q for q, _ in cur.calls))
        self.assertTrue(cur.closed)

    def test_seed_replay_avoids_write_but_updates_changed_authority(self):
        seed = dict(ean_upc='012345',article_number='123',selling_uom_code='PACK',
                    base_uom_code='LB',base_qty_per_selling_unit=Decimal('2'),source_note='confirmed')
        existing = {**seed, 'override_status':'CONFIRMED'}
        with patch.object(overrides, 'SEED_OVERRIDES', (seed,)), patch.object(overrides, 'ensure_override_table'):
            cur = Cursor(existing=existing)
            self.assertEqual(overrides.seed_confirmed_overrides(cur), 0)
            self.assertFalse(any('INSERT' in q for q, _ in cur.calls))
            for changed in (None, {**existing,'base_qty_per_selling_unit':None},
                            {**existing,'override_status':'RETIRED'}):
                cur = Cursor(existing=changed)
                self.assertEqual(overrides.seed_confirmed_overrides(cur), 1)
                self.assertTrue(any('ON DUPLICATE KEY UPDATE' in q for q, _ in cur.calls))

    def test_missing_diagnostic_permission_does_not_stop_heartbeat(self):
        class Denied(Cursor):
            def execute(self, sql, args=()): raise PermissionError('denied')
        result = connection_diagnostics(Denied(), 42)
        self.assertEqual(result['db_connection_id'],42)
        self.assertEqual(set(result['db_diagnostic_errors']),{'process','transaction','statement','locks'})

    def test_diagnostics_are_scoped_to_owned_connection(self):
        class Metadata(Cursor):
            def fetchone(self): return {'db_state':'executing'}
            def fetchall(self): return []
        cur = Metadata()
        result = connection_diagnostics(cur, 42)
        self.assertEqual(result['db_lock_waits'],[])
        self.assertTrue(all(args == (42,) for _,args in cur.calls))
        self.assertFalse(any('SQL_TEXT' in q or 'PROCESSLIST_INFO' in q for q,_ in cur.calls))


if __name__ == '__main__': unittest.main()
