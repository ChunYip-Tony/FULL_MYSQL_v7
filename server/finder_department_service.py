"""Standalone department service; no Seafood importer and one state request at a time."""
from finder_department_store import create_app
from request_capacity import RequestCapacityMiddleware

app = create_app()
app.add_api_route('/v1/departments/healthz', lambda: {'status': 'alive', 'service': 'finder-department-mysql'}, methods=['GET'])
app.add_middleware(RequestCapacityMiddleware, max_requests=1, max_ai=0)
