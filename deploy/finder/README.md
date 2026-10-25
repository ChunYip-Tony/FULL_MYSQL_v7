# Independent department MySQL API deployment

This is a deployable API for the existing Meat and Produce state contracts. It
does not run Seafood ingestion, AI, a background worker, or administrative
routes. It can be hosted independently using a standard Docker runtime. It
does not require the DigitalOcean management API at runtime or during builds.

The current production department sites remain on their existing storage until
the migration gates below pass. A successful container build or health response
is not evidence that production data has been migrated.

## Deployable image

Build from the repository root:

```sh
docker build -f server/Dockerfile.finder -t finder-department-api server
```

The image runs as UID 10001 and needs only writable `/tmp` for the MySQL CA file.
It supports a read-only root filesystem. Its entrypoint honors `PORT` (default
8080), binds to `0.0.0.0`, and uses one Uvicorn process. There are no databases,
uploads, secrets, or persistent business records inside the image.

Configure these secret runtime variables through the selected host:

| Variable | Requirement |
| --- | --- |
| `FULLMYSQL_DATABASE_URL` | MySQL 8.4 database URL, using a dedicated service account |
| `FULLMYSQL_DB_CA_CERT` | Correct CA certificate; certificate and hostname verification remain enabled |
| `FULLMYSQL_WORK_TOKEN` | New independent random token for the shared settings loader; never copy the Seafood administration token |
| `FINDER_STORE_TOKEN_MEAT` | Independent random bearer token of at least 40 characters |
| `FINDER_STORE_TOKEN_PRODUCE` | Different independent random bearer token of at least 40 characters |

The two department tokens belong only in server-side Site secrets. Visitors do
not sign in and must never receive these tokens. Use HTTPS between Sites and
this API. Database network access must be explicitly permitted for the new host;
do not disable trusted-source restrictions or TLS to make a connection succeed.

Use a separate schema migration identity for the explicit pre-deployment command:

```sh
python finder_department_schema_setup.py --apply
```

This creates only the six named Finder tables/views and verifies write,
readback and rollback without changing either department's current revision.
The API itself does not run migrations during startup. A failed schema check
must stop deployment. Configure the runtime database account with only the
permissions required by these Finder records and views, excluding Seafood data.

Use `/readyz` as the deployment admission check. It verifies independent tokens,
TLS configuration, MySQL 8.4, the required tables and usable views. It returns
503 when a dependency is unavailable and never exposes credentials or exception
details. Use `/healthz` for process liveness. A database outage should not cause
an endless container restart cycle.

Readiness does not assert that department records have been imported or that
their source dates are current. Those require the separate migration gates.

## Capacity and permanent architecture

This service has a bounded admission limit of one department request at a time,
16 MiB maximum state payloads, finite database timeouts, checksum verification,
and optimistic concurrency. A rejected request cannot claim a successful save.
Keep uploads and processing on the department sites and their separate processing
paths; do not redirect them into the Seafood importer.

The permanent arrangement is: public department sites and durable raw uploads;
independent processing capacity; MySQL authority; dated, verified site snapshots;
and Google/AI publication from the same verified revision. Saved views remain
available during API outages. Writes require a verified database response and
must not silently create a competing authoritative copy in a cache.

Retaining the current DigitalOcean MySQL database removes the app-creation
blocker only if database credentials and permitted network access are verified.
It does not remove DigitalOcean as a database dependency. If independence from
that account is required, migrate the database to another managed MySQL service
after a full backup, restore test and record comparison. The independent API
image remains the same.

## Cutover gates, one department at a time

1. Verify the selected hosting account, billing status, deployment authorization,
   database credentials, TLS and network access. Review actual monthly costs
   before starting additional paid capacity.
2. Take a durable backup of the source state and all original uploads; retain
   hashes, source dates, revision and counts for every record collection.
3. Apply and verify the schema on the target. Test backup restoration into a
   separate target before enabling production writes.
4. Import with `If-None-Match: *` and `X-Content-SHA256`. Read back the full bytes,
   verify SHA-256, compare every collection and historical record, and preserve
   nulls, zeros, leading-zero identifiers, units and source lineage.
5. Check atomic saves, concurrent stale-writer rejection, a lost commit reply,
   database outage behavior and recovery. Confirm cached data remains dated and
   unavailable writes never report success.
6. Briefly pause that department's writes, copy the final revision, verify again,
   then switch its Site secrets/backend and resume writes. Keep the other
   departments operating. Verify anonymous desktop/mobile use, uploads, edits,
   ordering/pricing analysis, Google publication and AI evidence.
7. Observe production and keep the old storage and backup for rollback. If new
   MySQL writes have occurred, do not flip back to an older source snapshot:
   pause writes and export/verify the latest MySQL revision before rollback.
8. Remove unused paid infrastructure only after successful recovery testing and
   a verified inventory of its remaining dependencies.

CI builds this exact image, boots it with a read-only filesystem and no secrets,
checks that liveness succeeds while database readiness and state access fail
closed, and runs schema/atomicity/concurrency tests against disposable MySQL 8.4.
Production credentials, network access, data parity and restore tests still need
to pass on the selected hosting account.
