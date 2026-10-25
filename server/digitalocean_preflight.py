"""Read-only App Platform diagnostic; never prints environment values or tokens."""
from __future__ import annotations

import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_ORIGIN = 'https://api.digitalocean.com'
EXISTING_APP_URL = 'https://seal-app-tkkkd.ondigitalocean.app'
MAX_BYTES = 8 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(path, token):
    if not path.startswith('/v2/apps') or any(x in path for x in ('://', '#', '\\', '\r', '\n')):
        raise ValueError('Unsupported diagnostic API path')
    request = Request(API_ORIGIN + path, method='GET',
                      headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise RuntimeError('DigitalOcean diagnostic response exceeded the size limit')
            return json.loads(raw)
    except HTTPError as error:
        raise RuntimeError(f'DigitalOcean API returned HTTP {error.code}; check token scope and app access') from None
    except (URLError, TimeoutError, ValueError):
        raise RuntimeError('DigitalOcean diagnostic request did not return valid JSON') from None


def pick(value, keys):
    value = value if isinstance(value, dict) else {}
    return {key: value[key] for key in keys if key in value}


def summarize(app):
    spec = app.get('spec') or {}
    components = []
    for kind in ('services', 'workers', 'jobs'):
        for component in spec.get(kind) or []:
            safe = pick(component, ('name', 'http_port', 'instance_size_slug', 'instance_count'))
            safe['type'] = kind
            safe['health_check'] = pick(component.get('health_check'),
                ('http_path', 'port', 'initial_delay_seconds', 'period_seconds', 'timeout_seconds',
                 'success_threshold', 'failure_threshold'))
            safe['source'] = pick(component.get('github'), ('repo', 'branch', 'deploy_on_push'))
            components.append(safe)
    return {'api_access_verified': True, 'read_only': True,
            **pick(app, ('id', 'live_url', 'updated_at')),
            'name': spec.get('name'), 'components': components,
            'active_deployment': pick(app.get('active_deployment'), ('id', 'phase', 'created_at', 'updated_at')),
            'pending_deployment': pick(app.get('pending_deployment'), ('id', 'phase', 'created_at', 'updated_at')),
            'limits': 'Read access does not verify update permission, runtime health or database readiness.'}


def run(token, app_id='', fetcher=fetch_json):
    if not token or any(x in token for x in ('\r', '\n')):
        raise RuntimeError('Configure DIGITALOCEAN_ACCESS_TOKEN as a repository secret before running this diagnostic')
    if app_id:
        try:
            app_id = str(uuid.UUID(app_id))
        except ValueError:
            raise RuntimeError('DigitalOcean app ID must be a UUID') from None
    else:
        payload = fetcher('/v2/apps?per_page=200', token)
        matches = [app for app in payload.get('apps', []) if app.get('live_url', '').rstrip('/') == EXISTING_APP_URL]
        if len(matches) != 1:
            raise RuntimeError('Existing Seafood app was not uniquely found; supply its app ID explicitly')
        try:
            app_id = str(uuid.UUID(matches[0]['id']))
        except (KeyError, ValueError):
            raise RuntimeError('DigitalOcean returned an invalid app ID') from None
    app = fetcher('/v2/apps/' + app_id, token).get('app')
    if not isinstance(app, dict) or app.get('live_url', '').rstrip('/') != EXISTING_APP_URL:
        raise RuntimeError('Selected app does not match the existing Seafood deployment')
    return summarize(app)


if __name__ == '__main__':
    try:
        result = run(os.environ.get('DIGITALOCEAN_ACCESS_TOKEN', ''), os.environ.get('DIGITALOCEAN_APP_ID', ''))
        print(json.dumps(result, indent=2))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
