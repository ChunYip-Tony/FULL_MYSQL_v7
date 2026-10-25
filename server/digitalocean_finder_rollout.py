"""Owner-approved, bounded rollout: $10/mo Seafood plus $5/mo department API.

The management PAT and existing DB credentials never leave the runner/provider.
New department credentials are returned only as RSA-OAEP ciphertext for the owner.
"""
import argparse
import base64
import copy
import json
import os
import secrets
import sys
import time

from digitalocean_health_policy import APP_ID, POLICY, REPO, SERVICE, request_json, service

DEPARTMENT_SERVICE = 'finder-department-mysql'
SCHEMA_JOB = 'finder-schema-v1'
SEAFOOD_SIZE = 'apps-s-1vcpu-1gb-fixed'
DEPARTMENT_SIZE = 'apps-s-1vcpu-0.5gb'
SOURCE_KEYS = ('github', 'source_dir', 'dockerfile_path', 'build_command', 'environment_slug')
DB_KEYS = ('FULLMYSQL_DATABASE_URL', 'FULLMYSQL_DB_CA_CERT', 'FULLMYSQL_DB_HOST', 'FULLMYSQL_DB_PORT',
           'FULLMYSQL_DB_USER', 'FULLMYSQL_DB_PASSWORD', 'FULLMYSQL_DB_NAME')


def public_summary(app):
    service(app)
    return {'app_id': APP_ID, 'services': [{k: s.get(k) for k in ('name','instance_size_slug','instance_count','http_port')}
                                          for s in app['spec'].get('services', [])],
            'jobs': [j['name'] for j in app['spec'].get('jobs', [])],
            'active_deployment': {k: (app.get('active_deployment') or {}).get(k) for k in ('id','phase')},
            'pending_deployment': {k: (app.get('pending_deployment') or {}).get(k) for k in ('id','phase')}}


def validate_base(app):
    s = service(app)
    if s.get('instance_count', 1) != 1 or s.get('instance_size_slug') not in (DEPARTMENT_SIZE, SEAFOOD_SIZE):
        raise RuntimeError('Existing Seafood capacity differs from the approved plan')
    if any(s.get(k) != v for k, v in POLICY.items()):
        raise RuntimeError('Verified Seafood HTTP health policy must remain enabled')
    if any(x.get('name') not in (SERVICE, DEPARTMENT_SERVICE) for x in app['spec'].get('services', [])):
        raise RuntimeError('Unexpected extra service; review total cost first')
    return s


def new_department_credentials():
    return {department: secrets.token_urlsafe(48) for department in ('meat','produce')}


def encrypted_credentials(credentials, public_key_der_b64):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    key = serialization.load_der_public_key(base64.b64decode(public_key_der_b64, validate=True))
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 4096:
        raise RuntimeError('An RSA public key of at least 4096 bits is required')
    payload = json.dumps({'app_id': APP_ID, 'service': DEPARTMENT_SERVICE, 'tokens': credentials}).encode()
    ciphertext = key.encrypt(payload, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return base64.b64encode(ciphertext).decode()


def plan(app, action, credentials=None):
    old = validate_base(app)
    spec = copy.deepcopy(app['spec'])
    target = next(s for s in spec['services'] if s['name'] == SERVICE)
    if action == 'resize':
        target['instance_size_slug'] = SEAFOOD_SIZE
        return spec
    if action == 'finalize':
        if not any(s['name'] == DEPARTMENT_SERVICE for s in spec['services']):
            raise RuntimeError('Department service is absent')
        jobs = spec.get('jobs', [])
        job = next((j for j in jobs if j['name'] == SCHEMA_JOB), None)
        if job and job.get('run_command') != 'python finder_department_schema_setup.py --apply':
            raise RuntimeError('Refusing to remove an unexpected job')
        if job:
            spec['jobs'] = [j for j in jobs if j['name'] != SCHEMA_JOB]
        return spec
    if action not in ('provision', 'provision-public-git'):
        raise RuntimeError('Unknown rollout action')
    if old['instance_size_slug'] != SEAFOOD_SIZE:
        raise RuntimeError('Complete and verify the Seafood resize first')
    if any(s['name'] == DEPARTMENT_SERVICE for s in spec['services']):
        raise RuntimeError('Department service already exists; never rotate its credentials implicitly')
    if any(j['name'] == SCHEMA_JOB for j in spec.get('jobs', [])):
        raise RuntimeError('Schema job already exists; inspect its deployment before retrying')
    if not credentials or set(credentials) != {'meat','produce'} or any(len(v) < 40 for v in credentials.values()):
        raise RuntimeError('Separate department credentials are required')
    if credentials['meat'] == credentials['produce']:
        raise RuntimeError('Department credentials must differ')
    env = {x['key']: x for x in spec.get('envs', []) + old.get('envs', [])}
    if not env.get('FULLMYSQL_DATABASE_URL', {}).get('value') or not env.get('FULLMYSQL_DB_CA_CERT', {}).get('value'):
        raise RuntimeError('Existing MySQL URL and CA configuration are required')
    db_env = [copy.deepcopy(env[k]) for k in DB_KEYS if k in env]
    # Settings requires a work token, but this isolated app exposes none of the
    # Seafood work/admin routes. Do not copy the existing Seafood admin token.
    work_env = {'key':'FULLMYSQL_WORK_TOKEN','value':secrets.token_urlsafe(48),'type':'SECRET','scope':'RUN_TIME'}
    source = {k: copy.deepcopy(old[k]) for k in SOURCE_KEYS if k in old}
    if action == 'provision-public-git':
        # The owner made this repository public. New components can use the
        # documented HTTPS Git source without adding a GitHub integration grant.
        # Leave Seafood's source, automatic deployments, and runtime untouched.
        source.pop('github', None)
        source['git'] = {'repo_clone_url': 'https://github.com/' + REPO + '.git', 'branch': 'main'}
    component = dict(source, name=DEPARTMENT_SERVICE, http_port=8080, instance_size_slug=DEPARTMENT_SIZE,
                     instance_count=1, run_command='python -m uvicorn finder_department_service:app --host 0.0.0.0 --port 8080 --workers 1',
                     envs=db_env + [work_env] + [{'key':'FINDER_STORE_TOKEN_'+d.upper(),'value':v,'type':'SECRET','scope':'RUN_TIME'} for d,v in credentials.items()],
                     **copy.deepcopy(POLICY))
    prefix = '/v1/departments'
    if spec.get('ingress') is not None:
        rules = spec['ingress'].get('rules', [])
        if any((r.get('match',{}).get('path',{}).get('prefix') or '').startswith(prefix) for r in rules):
            raise RuntimeError('Department route already exists')
        spec['ingress']['rules'] = [{'match':{'path':{'prefix':prefix}},'component':{'name':DEPARTMENT_SERVICE,'preserve_path_prefix':True}}] + rules
    else:
        if any(r.get('path','').startswith(prefix) for s in spec['services'] for r in s.get('routes', [])):
            raise RuntimeError('Department route already exists')
        component['routes'] = [{'path':prefix,'preserve_path_prefix':True}]
    spec['services'].append(component)
    job = dict(source, name=SCHEMA_JOB, kind='PRE_DEPLOY', instance_size_slug=DEPARTMENT_SIZE, instance_count=1,
               run_command='python finder_department_schema_setup.py --apply', envs=copy.deepcopy(db_env + [work_env]))
    spec.setdefault('jobs', []).append(job)
    return spec


def deployed_matches(app, action):
    active = app.get('active_deployment') or {}
    if app.get('pending_deployment') or active.get('phase') != 'ACTIVE':
        return False
    for spec in (app['spec'], active.get('spec') or {}):
        services = {s['name']:s for s in spec.get('services', [])}
        if services.get(SERVICE, {}).get('instance_size_slug') != SEAFOOD_SIZE:
            return False
        if action in ('provision','provision-public-git','finalize'):
            target = services.get(DEPARTMENT_SERVICE, {})
            if target.get('instance_size_slug') != DEPARTMENT_SIZE or target.get('instance_count') != 1:
                return False
            if action == 'finalize' and any(j['name'] == SCHEMA_JOB for j in spec.get('jobs', [])):
                return False
    return True


def run(token, action, public_key='', client=request_json, pause=time.sleep, deadline_seconds=780):
    before = client('GET', token)
    validate_base(before)
    print(json.dumps({'inspection':public_summary(before),'action':action}), flush=True)
    if action == 'inspect':
        return {'read_only':True, 'inspection':public_summary(before)}
    if before.get('pending_deployment'):
        raise RuntimeError('A deployment is pending; wait before changing capacity')
    credentials = new_department_credentials() if action in ('provision','provision-public-git') else None
    ciphertext = encrypted_credentials(credentials, public_key) if credentials else None
    proposed = plan(before, action, credentials)
    if before['spec'] == proposed:
        if not deployed_matches(before, action):
            raise RuntimeError('Desired settings exist but are not active; inspect deployment')
        return {'already_configured':True,'deployment_verified':True,'after':public_summary(before)}
    fresh = client('GET', token)
    if fresh['spec'] != before['spec'] or fresh.get('pending_deployment'):
        raise RuntimeError('Configuration changed; inspect before retrying')
    # Print only ciphertext before mutation, allowing recovery after a lost reply.
    if ciphertext:
        print('FINDER_PROVISION_ENCRYPTED_V1='+ciphertext, flush=True)
    client('PUT', token, {'spec':proposed})
    print(json.dumps({'update_accepted':True,'action':action}), flush=True)
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        current = client('GET', token)
        validate_base(current)
        if deployed_matches(current, action):
            return {'deployment_verified':True,'action':action,'after':public_summary(current)}
        pending = current.get('pending_deployment') or {}
        if pending.get('phase') in ('ERROR','CANCELED','SUPERSEDED'):
            raise RuntimeError('Provider deployment did not finish; inspect before retrying')
        pause(10)
    raise RuntimeError('Deployment not yet verified; inspect before retrying')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('inspect','resize','provision','provision-public-git','finalize'))
    args = parser.parse_args()
    try:
        print(json.dumps(run(os.environ.get('DIGITALOCEAN_ACCESS_TOKEN',''), args.action,
                             os.environ.get('FINDER_PUBLIC_KEY_DER_BASE64','')), indent=2))
    except Exception as error:
        message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(message, file=sys.stderr)
        sys.exit(1)
