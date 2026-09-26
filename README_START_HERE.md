# FULL MYSQL v7.0.11 — Single-Service Edition

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


## v7.0.7 ONLY_FULL_GROUP_BY / resume hotfix

v7.0.6 completed the repair stages far enough to enter final QA reporting, but
the final grouped QA query was rejected by MySQL 8.4 `ONLY_FULL_GROUP_BY`.
The repair runner now groups in a derived table and orders only by grouped
aliases.  The `/qa-summary` API uses the same corrected query.

Because the v7.0.6 traceback occurred during final reporting, database repair
mutations may already have completed.  Therefore v7.0.7 adds a safe read-only
inspection mode:

    python maintenance_v707.py --report-only

Run report-only first.  It does not mutate the database.  If Batch 7 identity
and Batch 8 Phase 3 already reflect the repaired state, no full rerun is needed.

If a full rerun is still needed:

    python maintenance_v707.py

The full runner now prints [1/6] ... [6/6] progress markers.


## v7.0.8 QA-scope separation

A daily/backfill POS/MVT batch and the global Quick Check serving snapshot are
different QA scopes.

Before v7.0.8, a `QUICK_CHECK_CORE_FIELD_MISSING` row anywhere in the serving
snapshot was counted as a blocker for the batch that happened to trigger the
rebuild.  This made a valid backfill batch look worse when central identity
coverage expanded.

v7.0.8 changes the semantics:

- `SOLD_UPC_UNMAPPED` and other batch-specific HIGH/CRITICAL issues can keep the
  batch in `PHASE3_QA_HOLD`.
- `QUICK_CHECK_CORE_FIELD_MISSING` holds only the affected UPC serving row.
- If a batch has no batch-specific blockers but some UPCs are on serving hold,
  final status is `QUICK_CHECK_READY_WITH_HOLDS`.
- `/v1/batches/{session_id}/qa-summary` now returns:
  - batch blocker counts
  - serving hold counts
  - reason-level Quick Check counts
  - remaining SOLD_UPC_UNMAPPED UPC/description rows

After deploy, re-evaluate Batch 8 only:

    python maintenance_v708.py --batch 8

No Batch 7 rebuild is required for this patch.


## v7.0.9 Active-Selling Scope

Current production readiness now distinguishes CURRENT selling activity from
historical-only evidence.

For an unmapped sold UPC:

- Positive sales on the latest 7 VALID POS data days => ACTIVE_SELLING => blocking.
- Present with a positive configured price on the latest available Price List
  snapshot => ACTIVE_ZERO_SALES => blocking even if recent sales are zero.
- Neither current evidence source exists => HISTORICAL_ONLY => preserved as
  `HISTORICAL_SOLD_UPC_UNMAPPED`, MEDIUM, non-blocking.

Historical sales are never deleted or converted to zero.

For mapped Quick Check rows, core-field QA applies to:
- ACTIVE_SELLING
- ACTIVE_ZERO_SALES

Rows without current active evidence remain available in the serving snapshot
but do not block current readiness.

After deploy:

    python maintenance_v709.py --batch 8

No Batch 7 rebuild is required.
Do not re-upload Batch 8 files.

The Seafood Windows client can be upgraded later; this server patch is
backward-compatible with the current HTTPS client while Batch 8 remains in
PHASE3_QA_HOLD or standard READY states.


## v7.0.10 POS-28 Active-Selling Scope

Current production readiness uses one rule only:

- Positive POS sold quantity in the latest up-to-28 VALID POS data days
  => `ACTIVE_SELLING` => unresolved core QA can block CURRENT readiness.
- All other UPCs
  => `HISTORICAL_ONLY` => history and QA are retained, but they do not block
  CURRENT production readiness.

A current Price List entry by itself no longer makes a UPC active.

"28 days" means the 28 most recent valid uploaded POS data days, completed-day
only. It is not 28 calendar days. If fewer than 28 valid POS data days exist,
all currently available valid POS data days up to 28 are used.

Existing 7D and 30D metrics remain unchanged. The 28-day window is used only
for CURRENT active/inactive QA scope.

After deploy:

    python maintenance_v710.py --batch 8

No Batch 7 rebuild is required.
Do not re-upload Batch 8.
Windows Seafood Client can be upgraded later.


## v7.0.11 Active Product Master Repair

This release targets the remaining CURRENT-active product-master gaps without
guessing.

Identity repair order:
1. Existing confirmed/user override evidence.
2. Exact or leading-zero-equivalent UPC evidence in uploaded Article Manual
   worksheets. Auto-confirm only when the canonical family is unique.
3. Exact UPC observations in official Frozen / TX Seafood ABC / Live-Fresh
   company reports. Auto-confirm only when all confirmed observations resolve
   to one family.
4. Ambiguous or unsupported UPCs stay QA HOLD.

Selling UOM repair:
- User-confirmed overrides remain authoritative.
- A unique historical trusted UPC-specific UOM can be reactivated.
- A unique exact UPC-specific `SELLING_UOM_OBSERVED` source value can be
  restored.
- NO UOM inference from item descriptions, pack text, UPC prefixes, or nearby
  family items.

Cost repair:
- Relinks late article/family mappings into movement, receiving, cost, and
  company-price derived history.
- Backfills missing 101/107/109 receipt valuation mirrors from already-ingested
  `movement_history`.
- Backfills missing official company-report cost mirrors when explicit cost UOM
  is present.
- RAW remains immutable.

After deploy:

    python maintenance_v711.py --batch 8

No Batch 7 rebuild.
No Batch 8 re-upload.
Seafood Windows Client can still be upgraded later after server rules stabilize.
