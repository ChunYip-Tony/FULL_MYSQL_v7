from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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
        "api_entry_production:app",
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
    cmd = [sys.executable, "worker.py"]
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


def requeue_interrupted_pipeline_runs(reason: str) -> int:
    """Persist a deployment-safe handoff after the worker process has stopped."""
    payload = json.dumps(
        {
            "auto_recovery": True,
            "recovery_reason": reason,
            "requeued_at": datetime.now(timezone.utc).isoformat(),
            "requeued_by_code_version": API_VERSION,
        },
        ensure_ascii=False,
    )
    with db_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """UPDATE pipeline_run
                   SET processing_status='QUEUED', completed_at=NULL, error_count=0,
                       detail_json=JSON_MERGE_PATCH(COALESCE(detail_json,JSON_OBJECT()),%s)
                   WHERE pipeline_name=%s
                     AND stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                     AND processing_status IN ('STARTED','PAUSE_REQUESTED')""",
                (payload, API_PIPELINE),
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


def main() -> int:
    api = start_api()
    worker = start_worker()
    stopping = False

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
                log(f"API exited with code {api_rc}; container will restart")
                return api_rc or 1

            worker_rc = worker.poll()
            if worker_rc is not None:
                log(f"worker exited with code {worker_rc}; requeueing interrupted work before restart")
                requeue_interrupted_pipeline_runs("WORKER_PROCESS_EXIT")
                log(f"restarting worker in {RESTART_DELAY}s")
                deadline = time.time() + RESTART_DELAY
                while time.time() < deadline and not stopping:
                    if api.poll() is not None:
                        return api.returncode or 1
                    time.sleep(0.25)
                if not stopping:
                    worker = start_worker()
            time.sleep(1)
    finally:
        stop_process(worker, "worker")
        requeue_interrupted_pipeline_runs("SERVICE_DEPLOYMENT_SHUTDOWN" if stopping else "SERVICE_PROCESS_EXIT")
        stop_process(api, "api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
