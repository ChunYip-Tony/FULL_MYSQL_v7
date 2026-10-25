"""Read-only provider validation; no deployment, SQL, or configuration writes.

POST /apps/propose is DigitalOcean's documented non-mutating app-spec check.
Compare the current spec, the proposed rollout, and a non-deployable diagnostic
copy whose new DB environment values are placeholders. Never apply that copy.
"""
import base64
import copy
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from digitalocean_finder_rollout import DB_KEYS, DEPARTMENT_SERVICE, SCHEMA_JOB, plan, validate_base
from digitalocean_health_policy import APP_ID, request_json
from digitalocean_preflight import API_ORIGIN, MAX_BYTES, NoRedirect

PROPOSE_URL = API_ORIGIN + '/v2/apps/propose'


def encrypt_error(raw, token, public_key):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    key = serialization.load_der_public_key(base64.b64decode(public_key, validate=True))
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 4096:
        raise RuntimeError('RSA-4096 public key required')
    clean = raw.decode('utf-8', errors='replace').replace(token, '[REDACTED]').encode()[:400]
    return base64.b64encode(key.encrypt(clean, padding.OAEP(
        mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))).decode()


def propose(token, spec, public_key):
    if not token or any(c in token for c in '\r\n'):
        raise RuntimeError('DigitalOcean repository secret missing or invalid')
    # Validate the key before any request; errors must never fall back to plaintext.
    encrypt_error(b'key-check', token, public_key)
    req = Request(PROPOSE_URL, method='POST',
                  data=json.dumps({'app_id': APP_ID, 'spec': spec}).encode(),
                  headers={'Authorization': 'Bearer ' + token,
                           'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(req, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise RuntimeError('Validation response exceeds size limit')
            json.loads(raw)  # Discard normalized specs and any credential material.
            return {'http_status': response.status, 'accepted': True}
    except HTTPError as error:
        raw = error.read(8192)
        return {'http_status': error.code, 'accepted': False,
                'encrypted_error': encrypt_error(raw, token, public_key)}
    except (URLError, TimeoutError, ValueError):
        return {'accepted': False, 'transport_or_response_error': True}


def variants(app):
    validate_base(app)
    full = plan(app, 'provision', {'meat': 'diagnostic-not-a-credential-meat-' * 2,
                                  'produce': 'diagnostic-not-a-credential-produce-' * 2})
    placeholders = copy.deepcopy(full)
    for component in placeholders.get('services', []) + placeholders.get('jobs', []):
        if component.get('name') not in (DEPARTMENT_SERVICE, SCHEMA_JOB):
            continue
        for env in component.get('envs', []):
            if env['key'] in DB_KEYS:
                env['value'] = 'DIAGNOSTIC_ONLY_NEVER_DEPLOY'
    return [('current_spec', copy.deepcopy(app['spec'])),
            ('proposed_rollout', full),
            ('proposed_with_new_db_placeholders', placeholders)]


def run(token, public_key, inspect=request_json, validator=propose):
    before = inspect('GET', token)
    if before.get('pending_deployment'):
        raise RuntimeError('Wait for the pending deployment before diagnosis')
    checks = []
    for name, spec in variants(before):
        result = {'check': name, **validator(token, spec, public_key)}
        checks.append(result)
        print(json.dumps(result), flush=True)
    after = inspect('GET', token)
    unchanged = before['spec'] == after['spec']
    print(json.dumps({'read_only': True, 'configuration_unchanged': unchanged}), flush=True)
    if not unchanged:
        raise RuntimeError('Configuration changed concurrently; inspect current state')
    return checks


if __name__ == '__main__':
    try:
        run(os.environ.get('DIGITALOCEAN_ACCESS_TOKEN', ''),
            os.environ.get('FINDER_PUBLIC_KEY_DER_BASE64', ''))
    except Exception as error:
        print(str(error) if isinstance(error, RuntimeError) else type(error).__name__, file=sys.stderr)
        sys.exit(1)
