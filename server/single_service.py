from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESTART_DELAY = max(1, int(os.environ.get("FULLMYSQL_WORKER_RESTART_SECONDS", "5")))


def log(message: str) -> None:
    print(f"[single-service] {message}", flush=True)


def start_api() -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api:app",
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


def main() -> int:
    # Start the HTTP service immediately so App Platform can reach /healthz.
    # Syntax is already checked at image build with compileall; uvicorn itself
    # provides the authoritative import-time traceback if api:app cannot load.
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
                log(f"worker exited with code {worker_rc}; restarting in {RESTART_DELAY}s")
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
        stop_process(api, "api")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
