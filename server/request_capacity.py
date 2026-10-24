"""Reject excess work before reading bodies or entering database/model code."""
import json
import os

_state = None


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
        self.state = {
            'enabled': True,
            'limit': max_requests if max_requests is not None else _limit('FULLMYSQL_API_MAX_INFLIGHT', 8),
            'ai_limit': max_ai if max_ai is not None else _limit('FULLMYSQL_AI_MAX_INFLIGHT', 2),
            'active': 0, 'ai_active': 0, 'peak': 0, 'rejected': 0,
        }
        _state = self.state

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if (scope['type'] != 'http' or not path.startswith('/v1/')
                or path == '/v1/yipman/ai/status'):
            return await self.app(scope, receive, send)
        state = self.state
        is_ai = path == '/v1/yipman/ai/chat'
        # These counters are changed without an await on one ASGI event loop.
        if state['active'] >= state['limit'] or is_ai and state['ai_active'] >= state['ai_limit']:
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
        state['ai_active'] += int(is_ai)
        state['peak'] = max(state['peak'], state['active'])
        try:
            return await self.app(scope, receive, send)
        finally:
            state['active'] -= 1
            state['ai_active'] -= int(is_ai)
