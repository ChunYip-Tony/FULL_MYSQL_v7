from __future__ import annotations

"""Durable shared persistence for complete App Ready generations.

The in-process store remains the hot cache. MySQL is the cross-worker/restart
source for the last complete generation. Only complete generations are written,
and the active pointer flips in the same transaction as the generation insert.
"""

import json
from dataclasses import asdict
from typing import Any

from db import db_conn


def _json_default(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS yipman_app_ready_generation (
            build_id VARCHAR(64) PRIMARY KEY,
            source_batch_id VARCHAR(255) NULL,
            data_through VARCHAR(32) NULL,
            completed_at VARCHAR(64) NOT NULL,
            build_ms BIGINT NULL,
            snapshot_json LONGTEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_app_ready_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS yipman_app_ready_pointer (
            pointer_name VARCHAR(32) PRIMARY KEY,
            build_id VARCHAR(64) NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_app_ready_pointer_build
              FOREIGN KEY (build_id) REFERENCES yipman_app_ready_generation(build_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    cur.close()


def persist_complete_snapshot(snapshot) -> None:
    """Persist and atomically activate one already-complete generation."""
    payload = json.dumps(asdict(snapshot), default=_json_default, separators=(",", ":"))
    with db_conn() as conn:
        ensure_schema(conn)
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO yipman_app_ready_generation
                   (build_id,source_batch_id,data_through,completed_at,build_ms,snapshot_json)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     source_batch_id=VALUES(source_batch_id),
                     data_through=VALUES(data_through),
                     completed_at=VALUES(completed_at),
                     build_ms=VALUES(build_ms),
                     snapshot_json=VALUES(snapshot_json)""",
                (
                    snapshot.build_id,
                    snapshot.source_batch_id,
                    snapshot.data_through,
                    snapshot.completed_at,
                    snapshot.build_ms,
                    payload,
                ),
            )
            cur.execute(
                """INSERT INTO yipman_app_ready_pointer(pointer_name,build_id)
                   VALUES ('ACTIVE',%s)
                   ON DUPLICATE KEY UPDATE build_id=VALUES(build_id)""",
                (snapshot.build_id,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def load_active_snapshot(snapshot_cls):
    """Load the shared active generation; return None before first durable build."""
    with db_conn() as conn:
        ensure_schema(conn)
        conn.commit()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT g.snapshot_json
                   FROM yipman_app_ready_pointer p
                   JOIN yipman_app_ready_generation g ON g.build_id=p.build_id
                   WHERE p.pointer_name='ACTIVE'
                   LIMIT 1"""
            )
            row = cur.fetchone()
        finally:
            cur.close()
    if not row:
        return None
    raw = json.loads(row["snapshot_json"])
    return snapshot_cls(**raw)
