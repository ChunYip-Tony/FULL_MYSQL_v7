"""Portable standalone entrypoint; honors the host's assigned HTTP port."""
import os


def port_from_environment():
    try:
        port = int(os.environ.get('PORT', '8080'))
    except ValueError:
        raise RuntimeError('PORT must be an integer') from None
    if not 1 <= port <= 65535:
        raise RuntimeError('PORT is outside the valid TCP port range')
    return port


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('finder_department_service:app', host='0.0.0.0', port=port_from_environment(),
                workers=1, proxy_headers=True, timeout_keep_alive=5)
