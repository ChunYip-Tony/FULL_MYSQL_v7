# Yipman product channels

Effective 2026-10-04, the production product surface is intentionally limited to two official channels.

| Channel | Official name | Production path | Development rule |
| --- | --- | --- | --- |
| Mobile | Yipman Mobile V1 | `/app/yipman-v1/` | All mobile UI/function work goes here. Do not create Mobile V2/V3 product branches or new public mobile routes. |
| Desktop | Yipman Back Office | `/app/backoffice` | All desktop UI/function work goes here. Do not create alternate desktop product routes. |

## Production launcher

`single_service.py` must always launch `api_entry_production:app`.

Versioned `api_entry_v*` modules are implementation layers and historical build composition only. They are not separate production apps and must not be used directly by the service launcher after this consolidation.

## Legacy compatibility

`/app/yipman` and its PWA assets are compatibility-only. Do not add new mobile product features specifically for that route. New mobile work belongs to `/app/yipman-v1/`. Desktop users should use `/app/backoffice`.

Versioned UI modules such as `yipman_desktop_v369.py` and `yipman_mobile_v2.py` are retained as source implementation/history. Their version numbers do not define product channels.

## Rollback snapshots

The pre-consolidation state is retained in Git branches:

- `rollback/mobile-last-stable-20261004`
- `rollback/desktop-last-stable-20261004`

Both point to commit `38404ca0019e61527fa5f8c0bf0dad7fe6f08a4c`, which contains the latest Mobile V1 Quick Check layout update and the already-unified desktop work available immediately before product-channel consolidation.

## Release policy

Internal backend/build versions may continue to increment for diagnostics and deployment tracking. Product names and production paths do not change with each build.

A normal release therefore changes implementation behind one of the two official channels rather than introducing a new app name or route.
