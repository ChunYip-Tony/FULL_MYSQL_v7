"""Standalone department service; no Seafood importer and one state request at a time."""
from finder_department_store import create_app
from request_capacity import RequestCapacityMiddleware
from finder_department_readiness import readiness
from fastapi.responses import JSONResponse

app = create_app()
app.add_api_route('/v1/departments/healthz', lambda: {'status': 'alive', 'service': 'finder-department-mysql'}, methods=['GET'])


@app.get('/readyz')
def ready():
    result = readiness()
    return JSONResponse(result, status_code=200 if result['status'] == 'ready' else 503,
                        headers={'Cache-Control': 'no-store'})


app.add_middleware(RequestCapacityMiddleware, max_requests=1, max_ai=0)
