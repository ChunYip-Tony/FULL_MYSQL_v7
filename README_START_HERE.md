# FULL MYSQL v7.0.1 — Single-Service Edition

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

## Safe migration

1. Update the private GitHub repository with this edition.
2. In DigitalOcean App Platform create **one Web Service only** from `server/`.
3. Run command: `python single_service.py`.
4. Select `basic-xs`, one instance, HTTP port 8080, health check `/healthz`.
5. Attach the existing Managed MySQL and configure runtime secrets/variables.
6. Confirm `/healthz` returns version `7.0.1-single-service`.
7. Install/configure the v7 client beside v6 and test one known spreadsheet.
8. Stop v6 production upload only after the v7 end-to-end path is verified.

Do not run v6 and v7 production uploaders on the same new files during cutover.
