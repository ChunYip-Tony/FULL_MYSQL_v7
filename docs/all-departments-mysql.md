# All departments on MySQL — staged implementation

Latest owner direction: keep the existing DigitalOcean/MySQL setup and deploy
through GitHub. A provider migration is not required. No Railway service or
replacement database has been created.

## Authority

- Seafood retains its existing normalized MySQL tables and business engine.
- Meat and Produce move their complete saved state into MySQL with department
  keys, immutable revisions, exact-byte checksums and a transactional current
  pointer. They retain their current parser and calculation contracts.
- Original XLS/XLSX files remain in durable object storage. MySQL stores their
  metadata/provenance along with the department records. File storage is not a
  competing database authority.
- Sites remains the Base/Boat UI. Google remains a verified analysis publication.
- The prior proposal to make Seafood's copied D1 data authoritative is superseded.
  Those copies remain recovery evidence and must not be deleted during cutover.

## Implemented, not activated

`server/finder_department_store.py` supplies a bounded HTTP/MySQL state service.
It reuses `db.db_conn`, including the existing MySQL secrets and certificate
handling. No provider hostname or new database credentials are embedded.

`finder_department_schema.sql` is additive. The whole source document is retained
byte-for-byte, including unknown fields, history, overrides and source metadata.
Views expose current profiles, POS records and family movements independently.
These views do not allocate family movement quantities to UPCs or invent units.

`finder_mysql_client.mjs` is a server-only adapter for the two Sites. It verifies
read checksums, uses exact storage ETags, preserves concurrency conflicts, rejects
redirects for authenticated requests, and never reports a failed write as saved.
Its initial import requires an explicit create-only condition. The existing Sites now include this server-only adapter behind the explicit
`FINDER_STATE_BACKEND=mysql` switch; the default remains `r2` until verified cutover.
`FINDER_WRITES_PAUSED=1` blocks state mutations during the migration window.
`GET /api/storage-status` reports the active backend, pause flag, revision and
collection counts without credentials. Failed MySQL operations never fall back
to writing a separate R2 state.

The 14 API contract tests use an in-memory fixture; the 7 JavaScript adapter
tests mock HTTP. They cover full-state preservation, separate credentials,
conflicts, retry acknowledgements, corrupt/incomplete reads and failed writes.
They are not evidence of production database or signed-in UI behavior.

`test_finder_department_mysql.py` adds five integration tests against a disposable
MySQL 8.4 database: real DDL/views, byte-preserving reads, concurrent writers,
lost replies, department isolation, rollback and invalid JSON. The dedicated
GitHub workflow supplies that database without any DigitalOcean access or
production secrets. Local runs explicitly skip these tests without the test DB;
the integration gate is passed only when its GitHub job actually succeeds.

## Activation steps and acceptance gates

1. Keep the existing Sites operating while securing an up-to-date export of each
   complete department state and retained original file inventory.
2. Apply the additive schema to a staging MySQL database using a migration role.
   Test SQL views, concurrent writes, rollback and exact source readback there.
3. Configure separate `FINDER_STORE_TOKEN_MEAT` and `FINDER_STORE_TOKEN_PRODUCE`
   secrets (at least 40 characters) in the API runtime. Each Site receives only
   its own token as `FINDER_MYSQL_API_TOKEN` plus `FINDER_MYSQL_API_ORIGIN`.
   Neither token nor any database credential belongs in Git or browser code.
4. `production_bootstrap.py` can register the authenticated department routes
   only when `FINDER_DEPARTMENT_STORE_ENABLED=1`. This preserves the existing
   Seafood `/healthz` route and is disabled by default. No schema is applied by
   application startup. Plan resource isolation from heavy Seafood ingestion. The standalone command is
   `uvicorn finder_department_store:app --host 0.0.0.0 --port $PORT` in the server
   directory. Provision any new component through an authenticated management
   API, not the blocked control-panel browser. This PR does not create it.
   Configure `/healthz` for process liveness. A successful liveness
   check alone does not certify database readiness or upload completion.
5. Import Meat and Produce with create-only writes. Verify exact hashes, all
   collections/counts, null versus zero, UPC leading zeros, business revisions,
   source dates and latest corrections. Reject/troubleshoot states over 16 MiB;
   do not truncate them or drop history to fit.
6. Wire each Site's state read/conditional write through the adapter. Audit all
   direct state writes, including Google sync metadata, lineage repair and
   shared upload intake. Do not introduce unsynchronized dual writers.
7. Retain dated last-verified read snapshots for viewing during an outage, but
   require MySQL acknowledgement before reporting a save/upload or Google sync
   as complete. Recover retained uploads through durable, idempotent jobs.
8. Test uploads, corrections, pricing, ordering, stock and Google readback on
   public desktop/mobile pages. The owner explicitly requires no visitor sign-in. Test DB/API outages and interrupted/lost replies.
9. Switch one department at a time only after comparison passes. The authority
   change must be explicit, with all later writes included in any rollback.

## Remaining platform work

The failed DigitalOcean control-panel page is not an activation step. Keep the
existing account, MySQL database and GitHub deployment integration. Code review
and test runs happen in GitHub; operational checks use the application endpoints.
Routine viewing, uploads, analysis and Google publication must not call the
control-panel site or require a control-panel session.

`digitalocean-preflight.yml` provides a manual, read-only API diagnostic using a
repository secret named `DIGITALOCEAN_ACCESS_TOKEN`. It matches only the existing
Seafood app URL (or validates an explicitly supplied app UUID), refuses redirects,
and prints selected deployment/health-check metadata without environment values.
Five local tests cover secret redaction, wrong-app rejection and safe failures.
It does not change hosting, create a database or establish update permission.

The existing smoke and snapshot workflows now run on pushes to `main` and on pull
requests, avoiding duplicate branch-push plus PR runs. Concurrency cancels obsolete
test runs for the same branch/PR. The test commands and production behavior are
preserved; snapshot tests also install the HTTP client needed by the new API tests.

The single-service Seafood supervisor currently runs Uvicorn and the importer
in one container. GitHub source access does not change service size, component
count, database privileges, secrets, health-check configuration or billing.
Those settings need an authorized DigitalOcean management API/CLI connection
when required. That connection has not been verified in this session. GitHub
source access alone is not equivalent to a DigitalOcean management credential;
do not claim that writing an app spec automatically applies platform settings.
Splitting API and worker isolates resource contention; it does not eliminate
the need for capacity, database monitoring and verified recovery.

References: [GitHub source deployment](https://docs.digitalocean.com/products/app-platform/how-to/create-apps/),
[API deployment logs and rollback](https://docs.digitalocean.com/products/app-platform/how-to/manage-deployments/),
and [App Platform API](https://docs.digitalocean.com/products/app-platform/reference/api/).

No live database, Site authority or hosting configuration is changed by this PR.

## Visitor access and current verification

The owner requires public Base/Boat/Finder access for all three departments;
visitor sign-in is not a migration gate. Server-to-server MySQL credentials
remain secret and separate from visitor access. Source exports must be validated
and saved privately; never commit department snapshots or source spreadsheets to
this public repository.

The smoke workflow was repaired to check current UI/data contracts: dynamic
company A/B/C labels, compact receiving and stock controls, current AI ordering
tools, and service-worker invalidation. It also initializes its missing UI source
variable. These changes preserve production behavior and fix stale test assumptions.


## Public access and AI research follow-up

The owner requires no visitor sign-in for Bases, Boats or Finders. All three
Sites now have public access. Meat v38 and Produce v96 publish the staged
storage adapter; no MySQL authority flag has been activated.

FisherMan adds a paginated research_item_catalog tool, including historical-only
and QA-held catalog rows, name/UPC/family/receiving aliases, explicit has_more and
next_cursor, and identity-only scope. Fast search now declares that it is not a
complete catalog/history scan. Natural conversational instructions preserve
all existing source, unit, stock and price-action rules. No model, provider key
or paid plan is changed. Three catalog contract tests plus 56 existing AI tests
pass locally; real production catalog queries still require deployment/readback.

On a7df643, MySQL candidate, snapshot resilience and supervisor CI passed.
Python smoke passed all offline assertions and reached its live mapping audit,
which failed because DigitalOcean returned HTTP504. This is retained as a
production availability failure, not bypassed or reported as a passing check.


## Posted price versus realized POS evidence

Live Fish v255 testing verified the current oyster UPC price against the Google
price-event source, then exposed a history-answer defect: the model described
POS weighted average prices as posted prices. The candidate adds a separate
`get_posted_price_history` read-only tool and labels POS type performance
explicitly. The new tool pages accepted parsed price-list observations without
the old 120-file history window, preserves exact UPC strings and file/row lineage,
uses store-business-date boundaries, and distinguishes an exhausted scan from
complete historical coverage. Unknown historical UOM stays unknown. It also
works for source UPCs absent from the current published catalog.

The 62 local AI tests pass. MySQL CI now also exercises 151 historical price
files, multiple pages, reversed file/date order, excluded failed/duplicate/pending
files, exact dates, and unlinked UPCs. This requires a passing new CI run before
claiming SQL verification. No AI provider, model or credential is changed.

Meat/Produce production readback still reports R2 with unchanged backup revision
and counts. Full MySQL activation and unrestricted historical completeness are
not established by these code changes.
