import copy
import json
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from digitalocean_health_policy import APP_ID, EXISTING_APP_URL, POLICY, REPO, SERVICE, metadata, planned_spec, request_json, run


def app():
    return {'id': APP_ID, 'live_url': EXISTING_APP_URL,
            'spec': {'name': 'seal-app', 'envs': [{'key': 'FULLMYSQL_DATABASE_URL', 'type': 'SECRET', 'value': 'PRIVATE_DB'}],
                     'services': [{'name': SERVICE, 'http_port': 8080, 'instance_size_slug': 'apps-s-1vcpu-0.5gb',
                                   'instance_count': 1, 'github': {'repo': REPO, 'branch': 'main'},
                                   'envs': [{'key': 'EXTRA', 'value': 'PRIVATE_EXTRA'}]}]},
            'active_deployment': {'id': 'old', 'phase': 'ACTIVE'}}


class HealthPolicyTests(unittest.TestCase):
    def test_denied_update_reports_only_method_status_and_scope_identifiers(self):
        body = b'{"message":"missing app:update and database:update PRIVATE_PASSWORD"}'
        with patch('digitalocean_health_policy.build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError('https://private', 403, 'PRIVATE', {}, io.BytesIO(body))
            with self.assertRaisesRegex(RuntimeError, 'PUT returned HTTP 403') as error:
                request_json('PUT', 'PRIVATE_TOKEN', {'spec': {'secret': 'PRIVATE_SPEC'}})
        self.assertIn('app:update', str(error.exception))
        self.assertIn('database:update', str(error.exception))
        self.assertNotIn('PRIVATE', str(error.exception))

    def test_only_probes_change_without_mutating_input_or_exposing_secrets(self):
        before = app()
        saved = copy.deepcopy(before)
        proposed = planned_spec(before)
        self.assertEqual(before, saved)
        self.assertEqual(proposed['envs'], before['spec']['envs'])
        target = proposed['services'][0]
        for key, value in before['spec']['services'][0].items():
            self.assertEqual(target[key], value)
        self.assertNotIn('PRIVATE_', json.dumps(metadata(before)))

    def test_unexpected_app_or_source_is_rejected(self):
        for key, value in [('id', 'wrong'), ('live_url', 'https://other.example')]:
            before = app(); before[key] = value
            with self.assertRaises(RuntimeError): planned_spec(before)
        before = app(); before['spec']['services'][0]['github']['repo'] = 'other/repo'
        with self.assertRaises(RuntimeError): planned_spec(before)

    def test_inspection_never_writes(self):
        calls = []
        def client(method, token, payload=None):
            calls.append(method); return app()
        self.assertFalse(run('PRIVATE', client=client)['applied'])
        self.assertEqual(calls, ['GET'])

    def test_pending_or_concurrent_configuration_change_aborts_before_put(self):
        first = app(); pending = copy.deepcopy(first); pending['pending_deployment'] = {'id': 'busy'}
        with self.assertRaises(RuntimeError): run('PRIVATE', True, lambda *args: pending)
        changed = app(); changed['spec']['services'][0]['instance_count'] = 2
        responses = iter([first, changed])
        with self.assertRaises(RuntimeError): run('PRIVATE', True, lambda *args: next(responses))

    def test_one_put_and_active_spec_readback(self):
        before = app(); after = app(); after['spec'] = planned_spec(before)
        after['active_deployment'] = {'id': 'new', 'phase': 'ACTIVE', 'spec': copy.deepcopy(after['spec'])}
        calls = []; responses = iter([before, before, after, after])
        def client(method, token, payload=None):
            calls.append(method)
            if method == 'PUT': self.assertEqual(payload, {'spec': after['spec']})
            return next(responses)
        result = run('PRIVATE', True, client)
        self.assertEqual(calls, ['GET', 'GET', 'PUT', 'GET'])
        self.assertTrue(result['deployment_verified'])
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_idempotent_policy_does_not_redeploy(self):
        current = app(); current['spec'] = planned_spec(current)
        calls = []
        def client(method, token, payload=None):
            calls.append(method); return current
        self.assertTrue(run('PRIVATE', True, client)['already_configured'])
        self.assertEqual(calls, ['GET'])


if __name__ == '__main__': unittest.main()
