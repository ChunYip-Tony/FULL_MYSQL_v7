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
