import base64
import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

import digitalocean_finder_diagnose as subject
from digitalocean_finder_rollout import SEAFOOD_SIZE, DEPARTMENT_SERVICE, SCHEMA_JOB, DB_KEYS
from digitalocean_health_policy import POLICY
from test_digitalocean_health_policy import app


def fixture():
    value = app()
    value['spec']['services'][0].update(copy.deepcopy(POLICY))
    value['spec']['services'][0]['instance_size_slug'] = SEAFOOD_SIZE
    value['spec']['envs'].append({'key': 'FULLMYSQL_DB_CA_CERT', 'value': 'PRIVATE_CA', 'type': 'SECRET'})
    return value


class DiagnoseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        cls.public = base64.b64encode(cls.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def test_variants_preserve_original_and_only_substitute_new_db_values(self):
        value = fixture(); saved = copy.deepcopy(value)
        original, full, stub = [x[1] for x in subject.variants(value)]
        self.assertEqual(value, saved)
        self.assertEqual(original, saved['spec'])
        self.assertEqual(stub['services'][0], full['services'][0])
        self.assertEqual(stub['envs'], full['envs'])
        for left, right in zip(stub['services'] + stub['jobs'], full['services'] + full['jobs']):
            if left['name'] not in (DEPARTMENT_SERVICE, SCHEMA_JOB):
                continue
            for a, b in zip(left['envs'], right['envs']):
                if a['key'] in DB_KEYS:
                    self.assertEqual(a['value'], 'DIAGNOSTIC_ONLY_NEVER_DEPLOY')
                    a['value'] = b['value']
        self.assertEqual(stub, full)

    def test_only_get_inspections_and_validator_calls_without_secret_logs(self):
        methods=[]; proposed=[]; value=fixture()
        def inspect(method, token): methods.append(method); return copy.deepcopy(value)
        def validate(token, spec, key): proposed.append(spec); return {'http_status': 200, 'accepted': True}
        out=io.StringIO()
        with redirect_stdout(out): subject.run('SECRET', self.public, inspect, validate)
        self.assertEqual(methods, ['GET','GET']); self.assertEqual(len(proposed), 3)
        self.assertNotIn('PRIVATE', out.getvalue()); self.assertNotIn('SECRET', out.getvalue())
        self.assertIn('"configuration_unchanged": true', out.getvalue())

    def test_pending_deployment_rejected_before_proposing(self):
        value=fixture(); value['pending_deployment']={'id':'pending'}
        with self.assertRaises(RuntimeError):
            subject.run('SECRET', self.public, lambda *args:value,
                        lambda *args:self.fail('must not propose while pending'))

    def test_http_error_encrypted_and_only_nonmutating_endpoint_called(self):
        body=b'{"id":"forbidden","message":"TOKEN private details"}'
        def open_request(req, timeout):
            self.assertEqual(req.method, 'POST')
            self.assertEqual(req.full_url, subject.PROPOSE_URL)
            self.assertEqual(json.loads(req.data)['app_id'], subject.APP_ID)
            raise HTTPError(req.full_url,403,'Forbidden',{},io.BytesIO(body))
        with patch.object(subject, 'build_opener') as opener:
            opener.return_value.open.side_effect=open_request
            result=subject.propose('TOKEN', fixture()['spec'], self.public)
        self.assertFalse(result['accepted']); self.assertEqual(result['http_status'],403)
        self.assertNotIn('private details',json.dumps(result))
        plain=self.key.decrypt(base64.b64decode(result['encrypted_error']),padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None)).decode()
        self.assertNotIn('TOKEN',plain);self.assertIn('[REDACTED]',plain)

    def test_invalid_key_fails_before_any_network_call(self):
        with patch.object(subject, 'build_opener') as opener, self.assertRaises(Exception):
            subject.propose('TOKEN',{},'bad-key')
        opener.assert_not_called()


if __name__ == '__main__': unittest.main()
