"""Health-only stage to isolate provider service-creation restrictions.

No database imports, startup migrations, business routes, or credentials.
Inherited app-level settings cannot enable department reads or writes here.
"""
from fastapi import FastAPI

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get('/healthz')
@app.get('/v1/departments/healthz')
def health():
    return {'status': 'alive', 'service': 'finder-department-mysql',
            'stage': 'health-only', 'migration_ready': False}
