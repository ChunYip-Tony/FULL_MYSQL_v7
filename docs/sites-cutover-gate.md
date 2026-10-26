# Deployment-controlled Seafood maintenance

`server/sites_cutover_mode.json` is committed as `NORMAL`. Installing this gate does not stop production, freeze SQL, alter Google, or activate Sites.

When all independent cutover prerequisites are ready, a reviewed commit can set `mode` to `ISOLATED_MIGRATION_READS` and `cutover_id` to a unique `seafood-sites-…` identifier. GitHub auto-deployment then uses the existing `python single_service.py` run command. The gate replaces that process with the isolated migration API before any operational imports or worker startup. Direct `production_bootstrap` and `worker_v482` entrypoints are guarded too. Invalid configuration stops startup rather than enabling business work.

Verify `/healthz` reports the exact cutover identifier, `business_api_enabled: false`, and `worker_enabled: false`. This confirms only the new deployment. Drain the old deployment and verify database sessions separately; an old container can finish shutdown bookkeeping. Independently fence all other SQL writers and Google publishers before the final consistent snapshot. This gate deliberately reports `freeze_established: false`.

Before native production accepts any writes, reverting the configuration to `NORMAL` and `cutover_id: null` restores normal startup through the same deployment path. After native writes begin, rollback also requires an explicit data reconciliation plan. A configuration revert alone is not a safe data rollback.

Tests execute the real supervisor, API bootstrap and worker entrypoint while trapping operational imports. They verify maintenance intercepts those imports, NORMAL preserves normal startup, malformed configuration fails closed, and reverting the configuration restores startup. No database connection is needed for these tests.
