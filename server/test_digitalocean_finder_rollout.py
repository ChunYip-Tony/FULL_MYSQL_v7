import asyncio
import base64
import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from digitalocean_finder_rollout import (DEPARTMENT_SERVICE, DEPARTMENT_SIZE, SCHEMA_JOB, SEAFOOD_SIZE,
    encrypted_credentials, plan, public_summary, run)
from digitalocean_health_policy import POLICY
from finder_department_schema_setup import statements
from test_digitalocean_health_policy import app


def fixture(resized=False):
    value = app()
    value['spec']['services'][0].update(copy.deepcopy(POLICY))
    value['spec']['services'][0]['dockerfile_path'] = 'server/Dockerfile'
    value['spec']['services'][0]['source_dir'] = 'server'
    value['spec']['envs'].append({'key':'FULLMYSQL_DB_CA_CERT','value':'PRIVATE_CA','type':'SECRET'})
    if resized:
        value['spec']['services'][0]['instance_size_slug'] = SEAFOOD_SIZE
    return value


class RolloutTests(unittest.TestCase):
    def test_resize_changes_exactly_one_approved_size_field(self):
        before = fixture(); saved = copy.deepcopy(before)
        proposed = plan(before, 'resize')
        self.assertEqual(before, saved)
        self.assertEqual(proposed['services'][0]['instance_size_slug'], SEAFOOD_SIZE)
        proposed['services'][0]['instance_size_slug'] = DEPARTMENT_SIZE
        self.assertEqual(proposed, before['spec'])

    def test_provision_preserves_existing_service_and_separates_tokens(self):
        before = fixture(True); original = copy.deepcopy(before)
        proposed = plan(before, 'provision', {'meat':'M'*64,'produce':'P'*64})
        self.assertEqual(before, original)
        self.assertEqual(proposed['services'][0], before['spec']['services'][0])
        self.assertEqual(proposed['envs'], before['spec']['envs'])
        component = proposed['services'][1]
        self.assertEqual(component['instance_size_slug'], DEPARTMENT_SIZE)
        self.assertEqual(component['instance_count'], 1)
        env = {x['key']:x for x in component['envs']}
        self.assertEqual(env['FULLMYSQL_DATABASE_URL']['value'], 'PRIVATE_DB')
        self.assertNotIn('EXTRA', env)
        for d,letter in [('MEAT','M'),('PRODUCE','P')]:
            self.assertEqual(env['FINDER_STORE_TOKEN_'+d]['value'], letter*64)
            self.assertEqual(env['FINDER_STORE_TOKEN_'+d]['type'], 'SECRET')
        self.assertEqual(component['routes'], [{'path':'/v1/departments','preserve_path_prefix':True}])
        self.assertEqual(proposed['jobs'][0]['kind'], 'PRE_DEPLOY')
        self.assertEqual(proposed['jobs'][0]['name'], SCHEMA_JOB)
        safe = fixture(True); safe['spec'] = proposed
        self.assertNotIn('PRIVATE', json.dumps(public_summary(safe)))
        self.assertNotIn('M'*64, json.dumps(public_summary(safe)))

    def test_modern_ingress_preserves_existing_routes_and_uses_exact_prefix(self):
        before = fixture(True)
        before['spec']['ingress'] = {'rules':[{'match':{'path':{'prefix':'/'}},'component':{'name':'full-mysql-v7-server'}}]}
        result = plan(before,'provision',{'meat':'M'*64,'produce':'P'*64})
        self.assertEqual(result['ingress']['rules'][1:],before['spec']['ingress']['rules'])
        self.assertEqual(result['ingress']['rules'][0]['component'],{'name':DEPARTMENT_SERVICE,'preserve_path_prefix':True})
        self.assertNotIn('routes',result['services'][1])

    def test_refuses_duplicate_service_collision_missing_ca_or_unapproved_capacity(self):
        tokens={'meat':'M'*64,'produce':'P'*64}
        before=fixture(True); before['spec']['services'].append({'name':DEPARTMENT_SERVICE})
        with self.assertRaises(RuntimeError): plan(before,'provision',tokens)
        before=fixture(True); before['spec']['envs']=before['spec']['envs'][:1]
        with self.assertRaises(RuntimeError): plan(before,'provision',tokens)
        before=fixture(); before['spec']['services'][0]['instance_count']=2
        with self.assertRaises(RuntimeError): plan(before,'resize')
        before=fixture(True); before['spec']['services'][0]['routes']=[{'path':'/v1/departments'}]
        with self.assertRaises(RuntimeError): plan(before,'provision',tokens)

    def test_ciphertext_is_decryptable_only_by_recipient_and_never_contains_tokens(self):
        private = rsa.generate_private_key(public_exponent=65537,key_size=4096)
        public = base64.b64encode(private.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
        tokens={'meat':'M'*64,'produce':'P'*64}
        encoded=encrypted_credentials(tokens,public)
        self.assertNotIn('M'*64,encoded)
        decoded=private.decrypt(base64.b64decode(encoded),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
        self.assertEqual(json.loads(decoded)['tokens'],tokens)

    def test_pending_and_concurrent_changes_abort_without_put(self):
        pending=fixture(); pending['pending_deployment']={'id':'pending'}
        with redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            run('PRIVATE','resize',client=lambda *a:pending)
        before=fixture(); changed=fixture(); changed['spec']['name']='other'
        responses=iter([before,changed]); calls=[]
        def client(method,*args): calls.append(method); return next(responses)
        with redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            run('PRIVATE','resize',client=client)
        self.assertEqual(calls,['GET','GET'])

    def test_resize_requires_active_deployment_and_one_put(self):
        before=fixture(); after=fixture(True)
        after['active_deployment']={'id':'new','phase':'ACTIVE','spec':copy.deepcopy(after['spec'])}
        responses=iter([before,before,after,after]); calls=[]
        def client(method,*args): calls.append(method); return next(responses)
        with redirect_stdout(io.StringIO()): result=run('PRIVATE','resize',client=client)
        self.assertTrue(result['deployment_verified']); self.assertEqual(calls,['GET','GET','PUT','GET'])

    def test_finalize_removes_only_the_known_temporary_job(self):
        value=fixture(True); value['spec']=plan(value,'provision',{'meat':'M'*64,'produce':'P'*64})
        result=plan(value,'finalize')
        self.assertEqual(result['services'],value['spec']['services'])
        self.assertEqual(result['jobs'],[])

    def test_schema_manifest_is_additive_and_known(self):
        self.assertEqual(len(statements()),6)
        self.assertTrue(all(x.startswith('CREATE ') for x in statements()))

    def test_standalone_health_does_not_require_database_or_tokens(self):
        from fastapi.testclient import TestClient
        from finder_department_service import app as service_app
        with TestClient(service_app) as client:
            self.assertEqual(client.get('/healthz').status_code,200)
            self.assertEqual(client.get('/v1/departments/healthz').json()['service'],'finder-department-mysql')
            self.assertEqual(client.get('/v1/departments/meat/state').status_code,503)


if __name__ == '__main__': unittest.main()
