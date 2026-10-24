from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from health_watchdog import APIWatchdog, api_responds
from supervisor_health import SupervisorHealth
from db import db_conn
from v7_ingest import API_PIPELINE, API_VERSION

BASE = Path(__file__).resolve().parent
RESTART_DELAY = max(1, int(os.environ.get("FULLMYSQL_WORKER_RESTART_SECONDS", "5")))


def log(message: str) -> None:
    print(f"[single-service] {message}", flush=True)


def start_api() -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "production_bootstrap:app",
        "--host",
        "0.0.0.0",
        "--port",
        os.environ.get("PORT", "8080"),
        "--workers",
        "1",
    ]
    log("starting API: " + " ".join(cmd))
    return subprocess.Popen(cmd, cwd=BASE)


def start_worker() -> subprocess.Popen:
    # v482 keeps the stable worker implementation but patches Phase 2C ->
    # Phase 3 orphan convergence so stale Phase 3 result rows cannot strand a
    # PHASE2C_READY batch. Later worker patches are applied inside worker_v482.
    cmd = [sys.executable, "worker_v482.py"]
    log("starting background worker: " + " ".join(cmd))
    return subprocess.Popen(cmd, cwd=BASE)


def stop_process(proc: subprocess.Popen | None, name: str, timeout: int = 10) -> None:
    if proc is None or proc.poll() is not None:
        return
    log(f"stopping {name} pid={proc.pid}")
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        log(f"forcing {name} pid={proc.pid} to stop")
        proc.kill()
        proc.wait(timeout=5)


def requeue_interrupted_pipeline_runs(reason: str, worker_pid: int | None = None) -> int:
    """Persist a deployment-safe handoff after the worker process has stopped."""
    if worker_pid is None:
        return 0
    owner = f"{socket.gethostname()}:{worker_pid}"
    payload = json.dumps(
        {
            "auto_recovery": True,
            "recovery_reason": reason,
            "requeued_at": datetime.now(timezone.utc).isoformat(),
            "requeued_by_code_version": API_VERSION,
        },
        ensure_ascii=False,
    )
    try:
        with db_conn(connection_timeout=5, read_timeout=5) as conn:
            cur = conn.cursor()
            try:
                cur.execute('SET SESSION innodb_lock_wait_timeout=5')
                cur.execute(
                    """UPDATE pipeline_run
                       SET processing_status='QUEUED', completed_at=NULL, error_count=0,
                           detail_json=JSON_MERGE_PATCH(COALESCE(detail_json,JSON_OBJECT()),%s)
                       WHERE pipeline_name=%s
                         AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN','CHATGPT_SHEET_PUBLISH')
                         AND processing_status IN ('STARTED','PAUSE_REQUESTED')
                         AND code_version=%s
                         AND JSON_UNQUOTE(JSON_EXTRACT(detail_json,'$.worker'))=%s""",
                    (payload, API_PIPELINE, API_VERSION, owner),
                )
                count = int(cur.rowcount or 0)
                conn.commit()
                if count:
                    log(f"requeued {count} interrupted pipeline run(s) for automatic recovery")
                return count
            except Exception as exc:
                conn.rollback()
                log(f"failed to requeue interrupted pipeline run(s): {exc!r}")
                return 0
            finally:
                cur.close()
    except Exception as exc:
        # Connection acquisition, cursor setup and cleanup can fail outside
        # the transaction handler. Recovery bookkeeping must never prevent
        # the supervisor from restarting a stopped worker or stopping the API.
        log(f"requeue unavailable ({type(exc).__name__}); worker recovery continues")
        return 0


def main() -> int:
    api = start_api()
    worker = start_worker()
    stopping = False
    watchdog = APIWatchdog(time.monotonic())
    diagnostics = SupervisorHealth()

    def shutdown(signum, _frame):
        nonlocal stopping
        if not stopping:
            stopping = True
            log(f"received signal {signum}; shutting down")

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        while not stopping:
            api_rc = api.poll()
            if api_rc is not None:
                diagnostics.event('api', 'PROCESS_EXIT', api_rc)
                log(f"API exited with code {api_rc}; restarting API only, worker continues")
                # An OOM-killed API must not terminate a healthy importer or
                # publisher. Back off crash loops while keeping worker ownership.
                deadline = time.monotonic() + RESTART_DELAY
                while time.monotonic() < deadline and not stopping:
                    time.sleep(0.25)
                if stopping:
                    break
                api = start_api()
                watchdog.reset(time.monotonic())

            if watchdog.due(time.monotonic()):
                healthy = api_responds(os.environ.get("PORT", "8080"))
                if watchdog.observe(time.monotonic(), healthy):
                    diagnostics.event('api', 'LOCAL_HEALTH_TIMEOUT')
                    log(f"API health unresponsive after {watchdog.threshold} checks; restarting API only, worker continues")
                    stop_process(api, "unresponsive api")
                    if stopping:
                        break
                    api = start_api()
                    watchdog.reset(time.monotonic())
                elif not healthy:
                    log(f"API health check failed ({watchdog.failures}/{watchdog.threshold})")

            worker_rc = worker.poll()
            if worker_rc is not None:
                diagnostics.event('worker', 'PROCESS_EXIT', worker_rc)
                log(f"worker exited with code {worker_rc}; requeueing interrupted work before restart")
                requeue_interrupted_pipeline_runs("WORKER_PROCESS_EXIT", worker.pid)
                log(f"restarting worker in {RESTART_DELAY}s")
                deadline = time.time() + RESTART_DELAY
                while time.time() < deadline and not stopping:
                    if api.poll() is not None:
                        # The next supervisor pass restarts the API in place.
                        break
                    time.sleep(0.25)
                if not stopping:
                    worker = start_worker()
            diagnostics.heartbeat(api.pid, worker.pid, watchdog.failures)
            time.sleep(1)
    finally:
        stop_process(worker, "worker")
        requeue_interrupted_pipeline_runs("SERVICE_DEPLOYMENT_SHUTDOWN" if stopping else "SERVICE_PROCESS_EXIT", worker.pid)
        stop_process(api, "api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




