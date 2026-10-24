from __future__ import annotations

"""Durable shared persistence for complete App Ready generations."""
import json
import os
from dataclasses import fields, is_dataclass
from typing import Any
from db import db_conn

def _json_default(value: Any):
    if is_dataclass(value) and not isinstance(value,type):
        return {field.name:getattr(value,field.name) for field in fields(value)}
    if hasattr(value,"isoformat"): return value.isoformat()
    return str(value)

def snapshot_json(snapshot)->str:
    # asdict recursively copies the complete graph, duplicating the shared
    # ordering/pricing sections and decision indexes before JSON encoding.
    # Let the encoder traverse the original graph instead. This preserves the
    # durable JSON contract without a second, potentially huge object graph.
    return json.dumps(snapshot,default=_json_default,separators=(",",":"))

def ensure_schema(conn)->None:
    cur=conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS yipman_app_ready_generation (build_id VARCHAR(64) PRIMARY KEY,source_batch_id VARCHAR(255) NULL,data_through VARCHAR(32) NULL,completed_at VARCHAR(64) NOT NULL,build_ms BIGINT NULL,snapshot_json LONGTEXT NOT NULL,created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,KEY idx_app_ready_created (created_at)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    cur.execute("""CREATE TABLE IF NOT EXISTS yipman_app_ready_pointer (pointer_name VARCHAR(32) PRIMARY KEY,build_id VARCHAR(64) NOT NULL,updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,CONSTRAINT fk_app_ready_pointer_build FOREIGN KEY (build_id) REFERENCES yipman_app_ready_generation(build_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    cur.close()

def _insert_generation(cur,snapshot,payload):
    cur.execute("""INSERT INTO yipman_app_ready_generation (build_id,source_batch_id,data_through,completed_at,build_ms,snapshot_json) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE source_batch_id=VALUES(source_batch_id),data_through=VALUES(data_through),completed_at=VALUES(completed_at),build_ms=VALUES(build_ms),snapshot_json=VALUES(snapshot_json)""",(snapshot.build_id,snapshot.source_batch_id,snapshot.data_through,snapshot.completed_at,int(round(snapshot.build_ms or 0)),payload))

def persist_complete_snapshot(snapshot)->None:
    from snapshot_graph import dumps
    payload=dumps(snapshot)
    with db_conn() as conn:
        ensure_schema(conn);cur=conn.cursor()
        try:
            _insert_generation(cur,snapshot,payload)
            cur.execute("""INSERT INTO yipman_app_ready_pointer(pointer_name,build_id) VALUES ('ACTIVE',%s) ON DUPLICATE KEY UPDATE build_id=VALUES(build_id)""",(snapshot.build_id,));conn.commit()
        except Exception: conn.rollback();raise
        finally: cur.close()

def persist_complete_snapshot_if_active(snapshot,expected_active_build_id:str)->bool:
    """Activate snapshot only if ACTIVE still equals the generation it was derived from."""
    from snapshot_graph import dumps
    payload=dumps(snapshot)
    with db_conn() as conn:
        ensure_schema(conn);cur=conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT build_id FROM yipman_app_ready_pointer WHERE pointer_name='ACTIVE' FOR UPDATE")
            row=cur.fetchone();current=str(row.get('build_id')) if row and row.get('build_id') else None
            if current!=str(expected_active_build_id):
                conn.rollback();return False
            _insert_generation(cur,snapshot,payload)
            cur.execute("UPDATE yipman_app_ready_pointer SET build_id=%s WHERE pointer_name='ACTIVE' AND build_id=%s",(snapshot.build_id,expected_active_build_id))
            if cur.rowcount!=1:
                conn.rollback();return False
            conn.commit();return True
        except Exception: conn.rollback();raise
        finally: cur.close()

def active_build_id()->str|None:
    with db_conn() as conn:
        ensure_schema(conn);conn.commit();cur=conn.cursor(dictionary=True)
        try: cur.execute("SELECT build_id FROM yipman_app_ready_pointer WHERE pointer_name='ACTIVE' LIMIT 1");row=cur.fetchone()
        finally: cur.close()
    return str(row['build_id']) if row and row.get('build_id') else None

def load_active_snapshot(snapshot_cls):
    from snapshot_graph import loads
    with db_conn() as conn:
        ensure_schema(conn);conn.commit();cur=conn.cursor(dictionary=True)
        try:
            # Inspect the size without transferring the LONGTEXT. Legacy JSON
            # expands aliases and can exhaust the entire API container on load.
            cur.execute("SELECT g.build_id,OCTET_LENGTH(g.snapshot_json) AS payload_bytes FROM yipman_app_ready_pointer p JOIN yipman_app_ready_generation g ON g.build_id=p.build_id WHERE p.pointer_name='ACTIVE' LIMIT 1")
            meta=cur.fetchone()
            if not meta:return None
            limit=max(1,int(os.environ.get('FULLMYSQL_SNAPSHOT_LOAD_MAX_MB','16')))*1048576
            if int(meta.get('payload_bytes') or 0)>limit:
                raise RuntimeError('APP_READY_SNAPSHOT_EXCEEDS_SAFE_LOAD_LIMIT')
            # Pin the generation inspected above even if ACTIVE changes.
            cur.execute("SELECT snapshot_json FROM yipman_app_ready_generation WHERE build_id=%s LIMIT 1",(meta['build_id'],))
            row=cur.fetchone()
        finally: cur.close()
    if not row:return None
    return snapshot_cls(**loads(row['snapshot_json']))

