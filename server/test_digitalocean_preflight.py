import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from digitalocean_preflight import EXISTING_APP_URL, NoRedirect, fetch_json, run

APP_ID = '11111111-1111-4111-8111-111111111111'


class PreflightTests(unittest.TestCase):
    def test_only_existing_app_is_selected_and_secrets_never_enter_summary(self):
        calls = []
        app = {'id': APP_ID, 'live_url': EXISTING_APP_URL, 'spec': {'name': 'seafood',
               'envs': [{'key': 'DB_PASSWORD', 'value': 'PRIVATE_DB_SECRET'}],
               'services': [{'name': 'api', 'http_port': 8080,
                 'envs': [{'key': 'WORK_TOKEN', 'value': 'PRIVATE_WORK_SECRET'}],
                 'health_check': {'http_path': '/healthz'},
                 'github': {'repo': 'owner/repo', 'branch': 'main', 'deploy_on_push': True}}]},
               'active_deployment': {'id': 'deployment', 'phase': 'ACTIVE',
                 'spec': {'envs': [{'value': 'PRIVATE_DEPLOY_SECRET'}]}}}
        def fake(path, token):
            calls.append(path)
            self.assertEqual(token, 'PRIVATE_API_TOKEN')
            return {'apps': [app]} if '?' in path else {'app': app}
        result = run('PRIVATE_API_TOKEN', fetcher=fake)
        self.assertTrue(result['api_access_verified'])
        self.assertEqual(result['components'][0]['http_port'], 8080)
        self.assertEqual(calls, ['/v2/apps?per_page=200', '/v2/apps/' + APP_ID])
        self.assertNotIn('PRIVATE_', json.dumps(result))
        self.assertNotIn('envs', json.dumps(result))

    def test_missing_token_and_invalid_id_make_no_request(self):
        for token, app_id in [('', ''), ('token', 'https://other.example'), ('token\nunsafe', '')]:
            with self.subTest(app_id=app_id), self.assertRaises(RuntimeError):
                run(token, app_id, fetcher=lambda *args: self.fail('Unexpected network request'))

    def test_wrong_or_ambiguous_app_is_rejected(self):
        wrong = {'id': APP_ID, 'live_url': 'https://another.example'}
        with self.assertRaises(RuntimeError):
            run('token', APP_ID, lambda *args: {'app': wrong})
        with self.assertRaises(RuntimeError):
            run('token', fetcher=lambda *args: {'apps': []})

    def test_error_response_does_not_print_body_or_credentials(self):
        with patch('digitalocean_preflight.build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError('https://example/?secret=PRIVATE', 403, 'PRIVATE', {}, None)
            with self.assertRaisesRegex(RuntimeError, 'HTTP 403') as result:
                fetch_json('/v2/apps/' + APP_ID, 'PRIVATE_API_TOKEN')
            self.assertNotIn('PRIVATE', str(result.exception))

    def test_redirects_are_refused(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://another.example'))


if __name__ == '__main__':
    unittest.main()
