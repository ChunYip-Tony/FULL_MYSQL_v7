from __future__ import annotations

"""Client wiring for upload-time precomputed App Ready intelligence."""


def polish_app_ready_client_html(html: str) -> str:
    marker = "yipmanV1AppReadyClient"
    if marker in html:
        return html
    old = "const d=await api('/v1/yipman/current-tpr-review?category=ALL&limit=1000');"
    new = "let d=window.YIPMAN_APP_READY?.sections?.price_tpr_progress;if(!d){d=await api('/app/yipman-v1-rc/api/app-ready/tpr-progress?category=ALL&limit=1000');if(d?.status==='SNAPSHOT_MISS'||!d?.app_ready_snapshot)d=await api('/v1/yipman/current-tpr-review?category=ALL&limit=1000')}"
    if old in html:
        html = html.replace(old, new, 1)
    tag = r'''<script id="yipmanV1AppReadyClient">
window.YIPMAN_APP_READY_FASTPATH=true;
window.YIPMAN_APP_READY=null;
fetch('/api/yipman/app-ready/snapshot',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{if(d?.status==='APP_READY'){window.YIPMAN_APP_READY=d;document.dispatchEvent(new CustomEvent('yipman-app-ready-preloaded',{detail:{build_id:d.build_id,data_through:d.data_through}}))}}).catch(()=>{});
</script>'''
    return html.replace("</head>", tag + "\n</head>", 1)
