# FULL MYSQL v7.0.3 — Single-Service Edition

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
