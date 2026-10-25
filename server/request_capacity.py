"""Reject excess work before reading bodies or entering database/model code."""
import json
import os
import re

_state = None
_STOCK_WRITE = re.compile(r'^/v1/app/(?:v2/pi/[^/]+|quick-check/[^/]+|inventory/negative-stock/[^/]+/[^/]+)/true-stock(?:/cancel)?$')


def request_lane(scope):
    path = scope.get('path', '')
    if path == '/v1/yipman/ai/chat':
        return 'ai'
    if scope.get('method', 'GET') in {'POST', 'PUT', 'PATCH', 'DELETE'} and (
        _STOCK_WRITE.fullmatch(path) or path.startswith('/v1/backoffice/qa-')
        or path.startswith('/v1/admin/price-change/proposals')
    ):
        return 'write'
    return 'general'


def _limit(name, default):
    try:
        return max(1, min(64, int(os.environ.get(name, default))))
    except (TypeError, ValueError):
        return default


def capacity_status():
    return dict(_state) if _state is not None else {'enabled': False}


class RequestCapacityMiddleware:
    def __init__(self, app, max_requests=None, max_ai=None):
        global _state
        self.app = app
        limit = max_requests if max_requests is not None else _limit('FULLMYSQL_API_MAX_INFLIGHT', 8)
        ai_limit = min(limit, max_ai if max_ai is not None else _limit('FULLMYSQL_AI_MAX_INFLIGHT', 2))
        # Ordinary reads and bulk uploads cannot occupy every slot. Preserve
        # headroom for AI and short, interactive stock/QA/price saves without
        # increasing total concurrency or consuming an overloaded request body.
        ai_reserved = min(ai_limit, max(0, limit - 2))
        write_reserved = 1 if limit >= 4 else 0
        self.state = {
            'enabled': True,
            'admission_revision': 'reserved-interactive-v1',
            'limit': limit,
            'ai_limit': ai_limit,
            'general_limit': max(1, limit - ai_reserved - write_reserved),
            'write_limit': max(1, write_reserved),
            'general_active': 0, 'write_active': 0,
            'department_limit': 1, 'department_active': 0,
            'active': 0, 'ai_active': 0, 'peak': 0, 'rejected': 0,
        }
        _state = self.state

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        # Stock flow and App Ready use /app/.../api/ and /api/, not /v1/.
        # Share one capacity budget across every business API namespace.
        business_api = (path.startswith(('/v1/', '/api/'))
                        or path.startswith('/app/') and '/api/' in path)
        if (scope['type'] != 'http' or not business_api
                or path == '/v1/yipman/ai/status'):
            return await self.app(scope, receive, send)
        state = self.state
        lane = request_lane(scope)
        is_department = path.startswith('/v1/departments/')
        # These counters are changed without an await on one ASGI event loop.
        if (state['active'] >= state['limit']
                or state[lane + '_active'] >= state[lane + '_limit']
                or is_department and state['department_active'] >= state['department_limit']):
            state['rejected'] += 1
            payload = json.dumps({'detail': {
                'code': 'SERVICE_BUSY', 'request_started': False,
                'reason': 'Seafood service is busy. Please retry shortly.',
                'retry_after_seconds': 3,
            }}).encode()
            await send({'type': 'http.response.start', 'status': 503, 'headers': [
                (b'content-type', b'application/json'), (b'cache-control', b'no-store'),
                (b'retry-after', b'3'), (b'content-length', str(len(payload)).encode()),
            ]})
            await send({'type': 'http.response.body', 'body': payload})
            return
        state['active'] += 1
        state[lane + '_active'] += 1
        state['department_active'] += int(is_department)
        state['peak'] = max(state['peak'], state['active'])
        try:
            return await self.app(scope, receive, send)
        finally:
            state['active'] -= 1
            state[lane + '_active'] -= 1
            state['department_active'] -= int(is_department)
