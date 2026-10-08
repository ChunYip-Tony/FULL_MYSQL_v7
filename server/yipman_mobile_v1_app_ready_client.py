from __future__ import annotations

"""Client wiring for upload-time precomputed App Ready intelligence."""


def polish_app_ready_client_html(html: str) -> str:
    marker = "yipmanV1AppReadyClient"
    if marker in html:
        return html
    # Preserve the full established TPR Progress UI; only change the data source.
    old = "const d=await api('/v1/yipman/current-tpr-review?category=ALL&limit=1000');"
    new = "let d=await api('/app/yipman-v1-rc/api/app-ready/tpr-progress?category=ALL&limit=1000');if(d?.status==='SNAPSHOT_MISS'||!d?.app_ready_snapshot)d=await api('/v1/yipman/current-tpr-review?category=ALL&limit=1000');"
    if old in html:
        html = html.replace(old, new, 1)
    tag = '<script id="yipmanV1AppReadyClient">window.YIPMAN_APP_READY_FASTPATH=true;</script>'
    return html.replace("</head>", tag + "\n</head>", 1)
