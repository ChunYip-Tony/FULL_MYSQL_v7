import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'server'))
fake=types.ModuleType('db');fake.db_conn=lambda **kw:None
with patch.dict(sys.modules,{'db':fake}):
    sql=importlib.import_module('sites_sql_cutover')
from migration_writer_audit import grant_evidence

class Cursor:
    def __init__(self,grants):self.grants=grants;self.queries=[]
    def execute(self,q,args=()):self.queries.append((q,args))
    def fetchall(self):return [{'g':g} for g in self.grants]

class SQLCutoverTests(unittest.TestCase):
    def test_grant_sanitizer_allows_privilege_names_but_rejects_auth_clauses(self):
        safe='GRANT AUTHENTICATION_POLICY_ADMIN, PASSWORDLESS_USER_ADMIN ON *.* TO `root`@`%`'
        self.assertEqual(sql.grants(Cursor([safe]),'root','%'),[safe])
        for suffix in [" IDENTIFIED BY 'secret'"," IDENTIFIED WITH plugin AS 'hash'"]:
            with self.assertRaisesRegex(ValueError,'Credential-bearing'):sql.grants(Cursor([safe+suffix]),'root','%')
    def test_schema_partial_restriction_preserves_other_schema_grants_exactly(self):
        before=['GRANT SELECT, INSERT, UPDATE ON *.* TO `app`@`%`','REVOKE INSERT ON `mysql`.* FROM `app`@`%`']
        plan={'schema':'full_mysql','targets':[{'user':'app','host':'%','before':before,'privileges':['INSERT','UPDATE']}]}
        cur=Cursor(before+['REVOKE INSERT, UPDATE ON `full_mysql`.* FROM `app`@`%`'])
        sql.restriction_shape(cur,plan)
        sql.restriction_shape(Cursor(before+[r'REVOKE INSERT, UPDATE ON `full\_mysql`.* FROM `app`@`%`']),plan)
        for bad in [before, before+['REVOKE INSERT, UPDATE, SELECT ON `full_mysql`.* FROM `app`@`%`'],[before[0],'REVOKE INSERT, UPDATE ON `full_mysql`.* FROM `app`@`%`']]:
            with self.assertRaises(ValueError):sql.restriction_shape(Cursor(bad),plan)
        sql.restriction_shape(Cursor(before),plan,allow_partial=True)
    def test_controller_is_schema_only_with_complete_restore_capability(self):
        base=['GRANT USAGE ON *.* TO `control`@`%`']
        scoped='GRANT '+', '.join(sorted(sql.WRITE_PRIVILEGES|{'SELECT'}))+' ON `full_mysql`.* TO `control`@`%` WITH GRANT OPTION'
        sql.validate_controller_grants(grant_evidence(base+[scoped],'full_mysql'))
        for bad in [base,base+[scoped.replace(' WITH GRANT OPTION','')],base+[scoped,'GRANT INSERT ON *.* TO `control`@`%`']]:
            with self.assertRaises(ValueError):sql.validate_controller_grants(grant_evidence(bad,'full_mysql'))
    def test_gate_must_match_exact_frozen_deployment(self):
        for mode in [{'mode':'NORMAL','cutover_id':None},{'mode':'ISOLATED_MIGRATION_READS','cutover_id':'seafood-sites-other'}]:
            with patch.object(sql,'deployment_mode',return_value=mode),self.assertRaises(ValueError):sql.ensure_gate('seafood-sites-test')
        with patch.object(sql,'deployment_mode',return_value={'mode':'ISOLATED_MIGRATION_READS','cutover_id':'seafood-sites-test'}):sql.ensure_gate('seafood-sites-test')
    def test_no_freeze_without_verified_restore_probe(self):
        with patch.object(sql,'ensure_gate'),patch.object(sql,'read_control',return_value={'state':'PREPARED','restoreProbePassed':False,'plan':{}}),patch.object(sql,'controller_connection') as connect:
            with self.assertRaisesRegex(ValueError,'restore path'):sql.freeze(None,None,'seafood-sites-test','secret')
            connect.assert_not_called()
    def test_committed_native_write_boundary_blocks_automatic_rollback(self):
        with patch.object(sql,'ensure_gate'),patch.object(sql,'read_control',return_value={'state':'COMMITTED'}),patch.object(sql,'controller_connection') as connect:
            with self.assertRaisesRegex(ValueError,'closed'):sql.rollback(None,'seafood-sites-test','secret')
            connect.assert_not_called()
    def test_any_other_connection_blocks_freeze(self):
        with patch.object(sql,'rows',return_value=[{'ID':1,'USER':'app'},{'ID':9,'USER':'external'}]):
            with self.assertRaisesRegex(ValueError,'not drained'):sql.require_drained(None,{1})
    def test_invalid_identity_and_request_credentials_fail_closed(self):
        for value in ['bad',None,'seafood-sites-;DROP', 'seafood-sites-'+('a'*65)]:
            with self.assertRaises(ValueError):sql.identity(value)
        for value in [None,'Bearer '+sql.AUTH_SHA256,'Bearer wrong']:
            with self.assertRaises(Exception):sql.authorize(value)

if __name__=='__main__':unittest.main()
