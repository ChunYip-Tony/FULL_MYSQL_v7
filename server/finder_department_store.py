"""Portable MySQL authority for existing Meat/Produce state contracts.

Seafood keeps its existing relational tables. This service reuses the configured MySQL connection on DigitalOcean or another
host. Department persistence has no dependency on Seafood ingestion jobs.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import threading
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

DEPARTMENTS = {"meat", "produce"}
MAX_STATE_BYTES = 16 * 1024 * 1024
REQUIRED_LISTS = ("items", "files", "movements", "posEvents", "priceEvents", "ohSnapshots")
DB_CAPACITY = threading.BoundedSemaphore(4)
HASH = re.compile(r"^[a-f0-9]{64}$")


def validate_state(raw: bytes, department: str) -> dict:
    if not raw or len(raw) > MAX_STATE_BYTES:
        raise HTTPException(413, "Department state exceeds the supported size.")
    def invalid_constant(value):
        raise ValueError("Non-finite JSON number")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    try:
        data = json.loads(raw.decode("utf-8"), parse_constant=invalid_constant, parse_float=finite_float,
                          object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(422, "A complete, valid UTF-8 JSON state is required.") from None
    if not isinstance(data, dict) or any(not isinstance(data.get(k), list) for k in REQUIRED_LISTS):
        raise HTTPException(422, "Required department records are missing.")
    revision = data.get("revision")
    if not isinstance(revision, str) or not 1 <= len(revision) <= 128:
        raise HTTPException(422, "A source revision is required.")
    if data.get("department", department) != department:
        raise HTTPException(422, "Department does not match this service scope.")
    return data


def authorize(request: Request, department: str):
    if department not in DEPARTMENTS:
        raise HTTPException(404, "Unknown department.")
    expected = os.environ.get("FINDER_STORE_TOKEN_" + department.upper(), "")
    if len(expected) < 40:
        raise HTTPException(503, "Department service is not configured.")
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied.encode(), ("Bearer " + expected).encode()):
        raise HTTPException(401, "Department authorization required.")


def precondition(request: Request) -> str | None:
    match, absent = request.headers.get("If-Match"), request.headers.get("If-None-Match")
    if absent == "*" and match is None:
        return None
    if absent is None and match and re.fullmatch(r'"[a-f0-9]{64}"', match):
        return match[1:-1]
    raise HTTPException(428, 'Use the exact If-Match ETag, or If-None-Match: * for initial import.')


@contextmanager
def mysql_connection():
    # Reuse the existing, working MySQL settings and CA handling. Database
    # credentials remain in deployment secrets, never in Sites/browser code.
    from db import db_conn
    if not DB_CAPACITY.acquire(timeout=1):
        raise HTTPException(503, "Database is busy. Retry this save after reading the current version.")
    try:
        with db_conn(connection_timeout=5, read_timeout=15) as conn:
            yield conn
    finally:
        DB_CAPACITY.release()


class MySQLStateStore:
    def __init__(self, connection=mysql_connection):
        self.connection = connection

    def get(self, department: str):
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT s.payload,s.sha256 FROM finder_department_head h "
                            "JOIN finder_department_state s ON s.department=h.department "
                            "AND s.sha256=h.sha256 WHERE h.department=%s", (department,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, "Department has not been imported and verified.")
                raw, digest = bytes(row[0]), row[1]
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise HTTPException(503, "Stored state verification failed.")
                return raw, digest
            finally:
                cur.close()

    def put(self, department: str, raw: bytes, data: dict, expected: str | None):
        digest = hashlib.sha256(raw).hexdigest()
        counts = json.dumps({k: len(v) for k, v in data.items() if isinstance(v, list)}, sort_keys=True)
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                conn.start_transaction()
                cur.execute("SET innodb_lock_wait_timeout=5")
                # Take an exclusive row lock even when the head already exists.
                # INSERT IGNORE can leave concurrent writers with shared locks
                # that deadlock when both subsequently request FOR UPDATE.
                cur.execute("INSERT INTO finder_department_head(department) VALUES(%s) "
                            "ON DUPLICATE KEY UPDATE generation=generation", (department,))
                cur.execute("SELECT sha256 FROM finder_department_head WHERE department=%s FOR UPDATE", (department,))
                current = cur.fetchone()[0]
                # A reply lost after commit can be retried without a second write.
                if current == digest:
                    conn.rollback()
                    return digest, True
                if current != expected:
                    raise HTTPException(409, "A newer department version is saved. Reload and reapply this change.")
                cur.execute("SELECT JSON_VALID(CONVERT(%s USING utf8mb4))", (raw,))
                if cur.fetchone()[0] != 1:
                    raise HTTPException(422, "State must also be valid MySQL JSON for analysis views.")
                cur.execute("INSERT IGNORE INTO finder_department_state "
                            "(department,sha256,source_revision,payload,byte_count,record_counts) "
                            "VALUES(%s,%s,%s,%s,%s,%s)",
                            (department, digest, data["revision"], raw, len(raw), counts))
                cur.execute("SELECT SHA2(payload,256),OCTET_LENGTH(payload) FROM finder_department_state "
                            "WHERE department=%s AND sha256=%s", (department, digest))
                stored_hash, stored_bytes = cur.fetchone()
                if stored_hash != digest or stored_bytes != len(raw):
                    raise HTTPException(503, "MySQL readback verification failed; previous version remains active.")
                cur.execute("UPDATE finder_department_head SET sha256=%s,generation=generation+1 "
                            "WHERE department=%s", (digest, department))
                conn.commit()
                return digest, False
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()


def create_app(store=None, *, include_health=True):
    app = FastAPI(title="Finder department MySQL service", docs_url=None, redoc_url=None, openapi_url=None)
    repository = store or MySQLStateStore()

    def health():
        # Liveness is independent of long imports and database availability.
        return {"status": "alive", "service": "finder-department-mysql"}

    if include_health:
        app.add_api_route("/healthz", health, methods=["GET"])

    @app.get("/v1/departments/{department}/state")
    def read_state(department: str, request: Request):
        authorize(request, department)
        try:
            raw, digest = repository.get(department)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, "MySQL read unavailable. Retry; do not replace saved data.") from None
        return Response(raw, media_type="application/json", headers={
            "ETag": '"' + digest + '"', "X-Content-SHA256": digest,
            "Cache-Control": "no-store", "X-Finder-Storage": "mysql",
        })

    @app.put("/v1/departments/{department}/state")
    async def write_state(department: str, request: Request):
        authorize(request, department)
        expected = precondition(request)
        if request.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise HTTPException(415, "JSON content type is required.")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_STATE_BYTES:
                raise HTTPException(413, "Department state exceeds the supported size.")
        raw = bytes(raw)
        data = validate_state(raw, department)
        claimed = request.headers.get("X-Content-SHA256", "")
        if not HASH.fullmatch(claimed) or claimed != hashlib.sha256(raw).hexdigest():
            raise HTTPException(422, "Source checksum does not match the submitted bytes.")
        try:
            digest, duplicate = await run_in_threadpool(repository.put, department, raw, data, expected)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, "MySQL save response unavailable. Read the current version before retrying.") from None
        return Response(json.dumps({"saved": True, "sha256": digest, "duplicate": duplicate,
                                    "revision": data["revision"], "storage": "mysql"}),
                        media_type="application/json", headers={"ETag": '"' + digest + '"', "Cache-Control": "no-store"})

    return app


def install_department_store(parent, store=None):
    """Opt-in server routes; visitor access does not reveal department secrets."""
    if os.environ.get("FINDER_DEPARTMENT_STORE_ENABLED") != "1":
        return False
    if getattr(parent.state, "finder_department_store_installed", False):
        return True
    # Keep the existing Seafood liveness route and startup behavior intact.
    parent.include_router(create_app(store, include_health=False).router)
    parent.state.finder_department_store_installed = True
    return True


app = create_app()
