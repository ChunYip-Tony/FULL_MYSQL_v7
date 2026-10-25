"""Apply only HTTP probe settings to the existing Seafood app; never export secrets."""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from digitalocean_preflight import API_ORIGIN, EXISTING_APP_URL, MAX_BYTES, NoRedirect, summarize

APP_ID = '05680b68-0372-479c-b2b6-bae286537e31'
APP_PATH = '/v2/apps/' + APP_ID
SERVICE = 'full-mysql-v7-server'
REPO = 'ChunYip-Tony/FULL_MYSQL_v7'
POLICY = {
    'health_check': {'http_path': '/healthz', 'port': 8080,
                     'initial_delay_seconds': 30, 'period_seconds': 10,
                     'timeout_seconds': 5, 'success_threshold': 1, 'failure_threshold': 5},
    # The local supervisor gets time to restart only the API before the platform
    # restarts the whole container and its ingestion worker.
    'liveness_health_check': {'http_path': '/healthz', 'port': 8080,
                              'initial_delay_seconds': 180, 'period_seconds': 10,
                              'timeout_seconds': 5, 'success_threshold': 1, 'failure_threshold': 12},
}
ENV_KEYS = ('FULLMYSQL_DATABASE_URL', 'FULLMYSQL_DB_CA_CERT',
            'FINDER_DEPARTMENT_STORE_ENABLED', 'FINDER_STORE_TOKEN_MEAT', 'FINDER_STORE_TOKEN_PRODUCE')


def request_json(method, token, payload=None):
    if method not in ('GET', 'PUT'):
        raise ValueError('Unsupported management method')
    if not token or any(c in token for c in '\r\n'):
        raise RuntimeError('DigitalOcean repository secret is missing or invalid')
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(API_ORIGIN + APP_PATH, data=body, method=method,
                      headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json',
                               'Content-Type': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise RuntimeError('DigitalOcean response exceeded the size limit')
            result = json.loads(raw)
            if not isinstance(result.get('app'), dict):
                raise RuntimeError('DigitalOcean did not return an app')
            return result['app']
    except HTTPError as error:
        # Provider errors can mention the exact missing scope. Extract only scope
        # identifiers; never log raw error bodies, spec values or credentials.
        mentioned = []
        if error.code == 403:
            try:
                raw_error = error.read(8192).decode('utf-8', errors='replace')
                mentioned = sorted(set(re.findall(r'\b[a-z_]+:(?:read|update|create|delete|access_console)\b', raw_error)))
                # A provider rejection without a named scope needs private
                # diagnosis. Encrypt a bounded error excerpt to the owner's
                # supplied public key; never print the response or credentials.
                public_key = os.environ.get('FINDER_PUBLIC_KEY_DER_BASE64')
                if public_key:
                    import base64
                    from cryptography.hazmat.primitives import serialization, hashes
                    from cryptography.hazmat.primitives.asymmetric import rsa, padding
                    key = serialization.load_der_public_key(base64.b64decode(public_key, validate=True))
                    if isinstance(key, rsa.RSAPublicKey) and key.key_size >= 4096:
                        excerpt = raw_error.replace(token, '[REDACTED]').encode()[:400]
                        encrypted = key.encrypt(excerpt, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
                        print('FINDER_PROVIDER_DIAGNOSTIC_V1=' + base64.b64encode(encrypted).decode(), flush=True)
            except Exception:
                pass
        detail = ('; provider-mentioned scopes: ' + ', '.join(mentioned)) if mentioned else ''
        raise RuntimeError(f'DigitalOcean management {method} returned HTTP {error.code}' + detail) from None
    except (URLError, TimeoutError, ValueError):
        raise RuntimeError('DigitalOcean management response unavailable; inspect before retrying an update') from None


def service(app):
    if app.get('id') != APP_ID or app.get('live_url', '').rstrip('/') != EXISTING_APP_URL:
        raise RuntimeError('Refusing to change an unexpected app')
    services = (app.get('spec') or {}).get('services') or []
    selected = [s for s in services if s.get('name') == SERVICE]
    if len(selected) != 1:
        raise RuntimeError('Existing service was not uniquely found')
    s = selected[0]
    if s.get('github', {}).get('repo') != REPO or s.get('github', {}).get('branch') != 'main' or s.get('http_port') != 8080:
        raise RuntimeError('Existing service source or port has changed; review first')
    return s


def planned_spec(app):
    service(app)
    proposed = copy.deepcopy(app['spec'])
    target = next(s for s in proposed['services'] if s['name'] == SERVICE)
    target.update(copy.deepcopy(POLICY))
    # Guard against accidentally changing sizes, replicas, sources, secrets or routes.
    restored = copy.deepcopy(proposed)
    check = next(s for s in restored['services'] if s['name'] == SERVICE)
    original = service(app)
    for key in POLICY:
        if key in original:
            check[key] = copy.deepcopy(original[key])
        else:
            check.pop(key, None)
    if restored != app['spec']:
        raise RuntimeError('Health policy attempted an unrelated configuration change')
    return proposed


def metadata(app):
    s = service(app)
    env = {v.get('key'): v for v in (app['spec'].get('envs') or []) + (s.get('envs') or [])}
    safe = summarize(app)
    safe.pop('read_only', None)
    safe['configured_health_policy'] = {key: s.get(key, {}) for key in POLICY}
    safe['configuration_presence'] = {key: {'present': key in env, 'type': env.get(key, {}).get('type')}
                                      for key in ENV_KEYS}
    safe['database_bindings'] = [{key: db[key] for key in ('name', 'engine', 'version', 'production') if key in db}
                                 for db in app['spec'].get('databases') or []]
    return safe


def run(token, apply=False, client=request_json, pause=time.sleep, deadline_seconds=600):
    before = client('GET', token)
    proposed = planned_spec(before)
    output = {'before': metadata(before), 'proposed_health_policy': POLICY, 'applied': False,
              'capacity_or_billing_change': False}
    if not apply:
        return output
    if proposed == before['spec']:
        output['already_configured'] = True
        return output
    if before.get('pending_deployment'):
        raise RuntimeError('An app deployment is already pending; wait for it before applying probe settings')
    # Re-read immediately before PUT so a known concurrent spec change is never overwritten.
    fresh = client('GET', token)
    service(fresh)
    if fresh.get('spec') != before['spec'] or fresh.get('pending_deployment'):
        raise RuntimeError('App configuration changed during inspection; re-plan the health policy')
    print(json.dumps({'read_access_verified': True, 'before': metadata(before),
                      'operation': 'PUT reviewed health probes only'}), flush=True)
    updated = client('PUT', token, {'spec': proposed})
    service(updated)
    output['applied'] = True
    output['update_permission_verified'] = True
    print(json.dumps({'update_accepted': True, 'app_id': APP_ID}), flush=True)
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        current = client('GET', token)
        s = service(current)
        active = current.get('active_deployment') or {}
        pending = current.get('pending_deployment') or {}
        if pending.get('phase') in ('ERROR', 'CANCELED', 'SUPERSEDED'):
            raise RuntimeError('Health policy deployment did not finish; review the provider deployment status')
        active_services = (active.get('spec') or {}).get('services') or []
        active_target = next((x for x in active_services if x.get('name') == SERVICE), {})
        matched = all(s.get(k) == v and active_target.get(k) == v for k, v in POLICY.items())
        if active.get('phase') == 'ACTIVE' and not pending and matched:
            output['deployment_verified'] = True
            output['after'] = metadata(current)
            return output
        pause(10)
    raise RuntimeError('Health policy deployment is not yet verified; inspect before retrying')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(os.environ.get('DIGITALOCEAN_ACCESS_TOKEN', ''), args.apply), indent=2))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
