"""Compatibility entry points for the unified Fish Finder website and mobile app.

Only browser entry pages move. Existing ingestion, QA and operational API
routes remain on this backend, including uploads from the unified website.
"""
from starlette.responses import RedirectResponse, JSONResponse

SITE = "https://seafood-stock-watch.bronzedove3.chatgpt.site"
ENTRY_POINTS = {
    "/app/data-center": "/?section=data",
    "/app/stock-records": "/?section=data&records=1",
    "/app/backoffice": "/",
    "/yipman": "/",
    "/yipman-v1": "/",
    "/app/yipman": "/",
    "/app/yipman-v1": "/",
    "/app/yipman-v1/install": "/install",
    "/app/yipman-v1/exit": "/",
}

def install_fish_finder_entrypoints(app, health_loader):
    async def data_center_worker_status():
        return await health_loader()

    app.add_api_route("/v1/app/data-center/worker-status", data_center_worker_status, methods=["GET"])

    @app.middleware("http")
    async def unified_entrypoints(request, call_next):
        path = request.url.path.rstrip("/")
        if request.method in ("GET", "HEAD") and path in ENTRY_POINTS:
            return RedirectResponse(SITE + ENTRY_POINTS[path], status_code=307,
                                    headers={"Cache-Control": "no-store"})
        if request.method == "GET" and path in (
            "/app/yipman/manifest.webmanifest", "/app/yipman-v1/manifest.webmanifest"
        ):
            scope = path.rsplit("/", 1)[0] + "/"
            return JSONResponse({"id": scope, "name": "Fish Boat", "short_name": "Fish Boat",
                                 "description": "The Fish Finder mobile app",
                                 "start_url": scope, "scope": scope, "display": "standalone",
                                 "background_color": "#f3f7fa", "theme_color": "#f3f7fa",
                                 "icons": [{"src": scope + "icon.svg", "sizes": "any", "type": "image/svg+xml"}]},
                                headers={"Cache-Control": "no-store"})
        return await call_next(request)
