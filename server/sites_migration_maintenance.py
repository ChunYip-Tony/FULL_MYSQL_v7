"""Isolated read-only API for a controlled Seafood deployment cutover.

Opt in by explicitly deploying ``uvicorn sites_migration_maintenance:app``.
This module never imports the operational API, worker, lazy cache builders or
startup recovery hooks. It does not freeze other SQL accounts or Google.
The existing authenticated, expiring migration read endpoints are preserved.
"""
from fastapi import FastAPI
from sites_migration_export import install_sites_migration_export
from sites_cutover_gate import deployment_mode

app = FastAPI(title='Seafood migration maintenance', docs_url=None,
              redoc_url=None, openapi_url=None)


@app.get('/healthz')
def health():
    return {'status': 'ok', 'mode': 'ISOLATED_MIGRATION_READS',
            'deployment_gate': deployment_mode(),
            'business_api_enabled': False, 'worker_enabled': False,
            'database_controls_changed': False, 'freeze_established': False}


install_sites_migration_export(app)
