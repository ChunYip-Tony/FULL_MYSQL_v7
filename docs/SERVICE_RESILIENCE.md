# Seafood service recovery and overload protection

Version 7.0.556 adds these guards to the existing single-service deployment.

- The supervisor probes local `/healthz` immediately. Cold startup retains a 180-second grace, but the first successful probe ends that grace. After startup, three failed probes at 10-second intervals restart only the API; the upload/publish worker keeps running.
- Recovery of a stopped worker uses 5-second database connect/read timeouts and a 5-second row-lock wait. Only runs owned by that stopped worker, for the matching code version, are requeued. Raw files are not reimported by this recovery step.
- The API admits at most 8 simultaneous `/v1/` business requests and 2 AI chat requests per process. `/healthz`, AI status, and static shells bypass admission. Excess requests receive HTTP 503 with `Retry-After: 3` and an explicit `SERVICE_BUSY`, `request_started: false` response before body parsing or business work.
- `FULLMYSQL_API_MAX_INFLIGHT` and `FULLMYSQL_AI_MAX_INFLIGHT` override those defaults. Values are bounded to 1–64; invalid values use the defaults. The supported deployment has one API process. Review memory and request durations before increasing limits.
- AI status includes `ready`, which requires a configured model and free request/AI capacity. Fish Base v246 waits for readiness before retrying an explicit pre-execution rejection. It does not replay ambiguous model timeouts or quota failures.

## Diagnostic evidence

`/healthz` keeps its existing `ok`, API/worker version and heartbeat fields. Its `runtime` object now includes:

- Process-based uptime and its source, rather than time since the first health request.
- Memory usage, a finite limit when exposed by the host, and available OOM counters. Unlimited kernel sentinel values appear as null. Missing OOM counters are not evidence that no OOM occurred.
- `request_capacity`: current active requests, AI requests, limits, peak active requests and rejected count.
- `supervisor`: process IDs, restart counts, last heartbeat and up to eight restart events, including process exit codes or local health timeouts. Exit code -9 indicates SIGKILL; it does not by itself prove an OOM.

Supervisor evidence is stored atomically in `/tmp/fullmysql_supervisor_health.json` (override with `FULLMYSQL_SUPERVISOR_HEALTH_PATH`). It survives an API-only restart in the same container. A whole-container replacement resets this local history; DigitalOcean runtime/platform logs are still needed for host failures or container eviction.

## Verification

Run the supervisor, publisher, service-resilience, watchdog, compact-snapshot and read-reliability suites. A production smoke check must verify the new API and worker versions, healthy supervisor heartbeat, enabled capacity limits, a successful real AI answer, and healthy state afterward. Do not stress the live service to trigger its limits; overload/cancellation tests use local controlled requests.


## Reserved interactive request capacity

Runtime 7.0.560 keeps the existing total limit of eight active business requests.
Five slots admit ordinary reads and bulk uploads, two are available for AI, and
one is reserved for short interactive stock/QA/price saves. Health and AI status
remain outside the business budget. A rejected request returns HTTP503 with
`request_started=false` before the request body or handler is consumed. This
reduces read-burst interference; it is not extra server capacity or a promise
that a database/provider outage cannot interrupt a request.

The opt-in Meat/Produce state endpoints additionally share a single active
request slot because each state can be several megabytes. This bounds their
contribution before JSON is read or parsed. The service remains disabled until
its existing schema, secret, migration parity and authority gates are satisfied.
Do not activate it merely because its admission controls pass.

Twenty-four supervisor/recovery/capacity tests pass locally. The new concurrency
cases saturate ordinary reads, verify two AI calls and one stock save can still
enter, keep health responsive, reject the next mutation without reading its
body, and check all counters return to zero. Another case holds a department
state request and confirms Seafood lookup, AI and stock-save admission remain
available. These are isolated admission tests, not production stress tests.

DigitalOcean management access is a separate prerequisite for inspecting or
changing component sizes, replication, worker placement, platform health checks
or environment secrets. The repository's `DigitalOcean read-only preflight`
workflow uses the existing app URL and the `DIGITALOCEAN_ACCESS_TOKEN` GitHub
Actions secret. It neither creates a new app nor applies hosting changes.

## Provider HTTP probe policy

On 2026-10-25 UTC the owner configured the Actions credential and the read-only
preflight succeeded for the existing `seal-app`. It reported one
`apps-s-1vcpu-0.5gb` instance and no explicit HTTP readiness probe. API access
is now verified; the earlier missing-credential prerequisite is resolved.

`DigitalOcean HTTP health policy` can inspect or explicitly apply the reviewed
`/healthz` probes on port 8080. Readiness waits 30 seconds, then checks every
10 seconds with a 5-second timeout and 5-failure threshold. Liveness waits
180 seconds and uses a 12-failure threshold, allowing the local supervisor
to recover the API before the platform restarts its container and worker.
Neither probe requires MySQL or a completed upload to answer.

The manager verifies the exact app ID, URL, service, repo, branch and port;
preserves all other spec fields including encrypted secrets; refuses a pending
deployment or detected concurrent spec edit; and verifies the policy in the
active deployment. It does not resize the service, create replicas, activate
department storage, apply database DDL or change billing. Public logs contain
only selected operational metadata and configuration-presence flags. Eleven
tests cover identity guards, secret redaction, preservation of unrelated
settings, concurrent-change rejection, dry runs and idempotent updates.
