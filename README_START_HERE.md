# FULL MYSQL v7.0.5 — Single-Service Edition

This edition keeps the v7 HTTPS architecture but runs the **API and background processing worker inside one DigitalOcean App Platform service/container**. It is designed for the current single-store Seafood workload and avoids paying for a second always-on Worker component.

## Architecture

Work/Home Client → HTTPS 443 → **one App Platform service** → DigitalOcean Managed MySQL → server-side Phase 1/2C/3 → Quick Check/AppSheet.

Inside the one container, `single_service.py` supervises two processes:

- `uvicorn api:app` — HTTPS/API traffic
- `python worker.py` — queued RAW → Phase2C → Phase3 processing

If the worker exits, the supervisor restarts it. If the API exits, the service exits so App Platform can restart the container.

## App Platform size

Use **one `basic-xs` instance (1 shared vCPU / 1 GiB RAM)** for the initial rollout. Do **not** add a separate Worker component. If batch processing later proves memory-constrained, scale the single component up rather than adding a second always-on component by default.

## Existing behavior retained

- Existing `full_mysql` schema and history are reused; no database rebuild.
- Article Manual verified Main/Sub hierarchy remains authoritative over Monthly PI hierarchy errors.
- UPC canonical identity resolves to Main/Family.
- POS and MVT daily-data coverage rules from v6.6 remain in force.
- POS 7D/30D uses the latest 7/30 valid POS data days, not calendar days.
- A valid POS data day with no sale for an UPC is a true zero; a missing/invalid POS day is NULL/MISSING and excluded.
- Work/Home Windows clients use HTTPS 443 only and do not store MySQL credentials.

## v7.0.2 token configuration change

DigitalOcean App Platform may parse raw `{...}` values in its environment-variable editor, so this release no longer requires JSON for the normal token setup. Configure two encrypted runtime secrets instead:

- `FULLMYSQL_WORK_TOKEN` — the existing Work-PC token you already generated
- `FULLMYSQL_HOME_TOKEN` — the existing Home-PC token you already generated

Keep `FULLMYSQL_ADMIN_DEVICES=HOME-PC`. `FULLMYSQL_API_TOKENS_JSON` is retained only as a backward-compatible fallback. Do not regenerate your existing tokens.

## Safe migration

1. Update the private GitHub repository with this edition.
2. In DigitalOcean App Platform create **one Web Service only** from `server/`.
3. Run command: `python single_service.py`.
4. Select `basic-xs`, one instance, HTTP port 8080, health check `/healthz`.
5. Attach the existing Managed MySQL and configure runtime secrets/variables.
6. Confirm `/healthz` returns version `7.0.2-single-service`.
7. Install/configure the v7 client beside v6 and test one known spreadsheet.
8. Stop v6 production upload only after the v7 end-to-end path is verified.

Do not run v6 and v7 production uploaders on the same new files during cutover.


## v7.0.3 worker fix

v7.0.3 fixes `mysql.connector.errors.InternalError: Unread result found` in
`worker.py::claim_job()`.  The worker now uses a buffered dictionary cursor,
releases the MySQL named lock in one place, and consumes the
`SELECT RELEASE_LOCK(...)` result before closing the cursor.

This error occurring after startup is also evidence that the App Platform
service has successfully reached the MySQL server; it is no longer the earlier
network/TLS connection problem.


## v7.0.4 batch polling fix

v7.0.4 fixes `TypeError: date.isoformat() takes no keyword arguments` in
`v7_ingest.py::session_status()`.

MySQL returns DATE columns such as `coverage_start_date` and
`coverage_end_date` as Python `date` objects, while timestamp columns are
`datetime` objects.  Only `datetime.isoformat()` accepts `sep=`.
The server now serializes both types correctly.

The same latent date/datetime conversion issue in `ingest.py::recent_batches()`
is fixed at the same time.

No environment-variable changes and no database migration are required.


## v7.0.5 central identity backfill

This release repairs the central identity/UOM foundation before re-evaluating
daily POS/MVT Phase 3 QA.

Key changes:
- Re-evaluate Batch 7 with current Article Manual authority logic.
- Re-link already-ingested sales/movement history to repaired identity.
- Retire stale derivation QA before a Phase 3 rerun; only current blockers are recreated.
- Add a persistent manual_upc_override registry.
- Seed the explicitly confirmed FULL MYSQL rule: UPC 4918 -> Article 3401602 -> LB.
- Add /v1/batches/{session_id}/qa-summary.

One-time repair after deploying v7.0.5:

    cd /app
    python maintenance_v705.py

Defaults: identity Batch 7, history Batch 8.

Later, to include the much larger Batch 6:

    python maintenance_v705.py --history-batches 8,6

On the $5 / 512 MB plan, repair Batch 8 first. Consider 1 GB before rerunning Batch 6.


## v7.0.6 maintenance hotfix

The v7.0.5 one-time maintenance runner imported a legacy v6.5.4 helper that
expected `config.APP_DIR`, which does not exist in the cloud v7 config.  The
failed import occurred before any database repair mutation.

v7.0.6 makes the maintenance runner self-contained.  It no longer imports the
legacy module.

After deploy:

    cd /app
    python maintenance_v706.py

The old command also works through a compatibility wrapper:

    python maintenance_v705.py
