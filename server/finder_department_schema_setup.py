"""Explicit additive schema job. Never runs from API startup; never logs credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

TABLES = {'finder_department_state', 'finder_department_head'}
VIEWS = {'finder_department_current', 'finder_upc_profiles', 'finder_pos_records', 'finder_family_movements'}


def statements():
    source = Path(__file__).with_name('finder_department_schema.sql').read_text()
    source = '\n'.join(x for x in source.splitlines() if not x.lstrip().startswith('--'))
    result = [x.strip() for x in source.split(';') if x.strip()]
    names = set()
    for statement in result:
        match = re.match(r'CREATE (?:TABLE IF NOT EXISTS|OR REPLACE VIEW) (finder_\w+)\b', statement)
        if not match or match[1] not in TABLES | VIEWS:
            raise RuntimeError('Schema contains an unexpected operation')
        names.add(match[1])
    if names != TABLES | VIEWS or len(result) != 6:
        raise RuntimeError('Schema object manifest does not match')
    return result


def apply_and_verify(connection):
    sql = statements()
    with connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute('SELECT VERSION()')
            version = cur.fetchone()[0]
            if not version.startswith('8.4.'):
                raise RuntimeError('This migration requires verified MySQL 8.4')
            for statement in sql:
                cur.execute(statement)
            conn.commit()
            # Verify write/read/rollback without modifying either department head.
            revision = 'migration-check-' + str(uuid.uuid4())
            payload = json.dumps({'revision': revision, 'probe': True}).encode()
            digest = hashlib.sha256(payload).hexdigest()
            cur.execute('SELECT department,sha256,generation FROM finder_department_head ORDER BY department')
            heads_before = cur.fetchall()
            conn.commit()
            conn.start_transaction()
            cur.execute('INSERT INTO finder_department_state (department,sha256,source_revision,payload,byte_count,record_counts) VALUES (%s,%s,%s,%s,%s,%s)',
                        ('meat', digest, revision, payload, len(payload), '{}'))
            cur.execute('SELECT SHA2(payload,256),OCTET_LENGTH(payload) FROM finder_department_state WHERE department=%s AND sha256=%s', ('meat', digest))
            if cur.fetchone() != (digest, len(payload)):
                raise RuntimeError('Schema write/readback verification failed')
            conn.rollback()
            cur.execute('SELECT COUNT(*) FROM finder_department_state WHERE department=%s AND sha256=%s', ('meat', digest))
            if cur.fetchone()[0] != 0:
                raise RuntimeError('Schema rollback verification failed')
            cur.execute('SELECT department,sha256,generation FROM finder_department_head ORDER BY department')
            if cur.fetchall() != heads_before:
                raise RuntimeError('A department head changed during schema verification')
            for view in sorted(VIEWS):
                cur.execute('SELECT * FROM ' + view + ' LIMIT 0')
                cur.fetchall()
            return {'schema_verified': True, 'mysql_version': version, 'objects': sorted(TABLES | VIEWS),
                    'write_readback_and_rollback_verified': True, 'existing_heads_preserved': True}
        finally:
            conn.rollback()
            cur.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    try:
        from db import db_conn
        print(json.dumps(apply_and_verify(lambda: db_conn(connection_timeout=10, read_timeout=30))))
    except Exception as error:
        print(json.dumps({'schema_verified': False, 'error_type': type(error).__name__,
                          'mysql_errno': getattr(error, 'errno', None)}), file=sys.stderr)
        sys.exit(1)
