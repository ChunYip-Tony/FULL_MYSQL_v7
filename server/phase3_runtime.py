"""Connection-scoped Phase 3 ownership and read-only worker diagnostics."""
from contextlib import contextmanager

PHASE3_LOCK = 'fullmysql_phase3_transaction'


@contextmanager
def phase3_lease(conn):
    # The claim lock only protects queue selection. This lock remains on the
    # business connection until commit/rollback, including deployment overlap.
    cur = conn.cursor(dictionary=True)
    acquired = False
    try:
        cur.execute('SELECT GET_LOCK(%s,0) AS acquired', (PHASE3_LOCK,))
        acquired = int((cur.fetchone() or {}).get('acquired') or 0) == 1
        if not acquired:
            raise RuntimeError('PHASE3_TRANSACTION_ALREADY_OWNED')
        yield
    finally:
        if acquired:
            try:
                cur.execute('SELECT RELEASE_LOCK(%s) AS released', (PHASE3_LOCK,))
                cur.fetchone()
            except Exception:
                pass  # Closing the connection also releases its named lock.
        cur.close()


def connection_diagnostics(cur, connection_id):
    """Only metadata for this run's connection; never SQL values or credentials."""
    result = {'db_connection_id': int(connection_id)}
    queries = (
        ('process', '''SELECT PROCESSLIST_COMMAND AS db_command,
                          PROCESSLIST_STATE AS db_state,
                          PROCESSLIST_TIME AS db_query_age_seconds
                       FROM performance_schema.threads WHERE PROCESSLIST_ID=%s'''),
        ('transaction', '''SELECT trx_state AS db_trx_state,
                              trx_rows_locked AS db_rows_locked,
                              trx_rows_modified AS db_rows_modified
                           FROM information_schema.innodb_trx
                           WHERE trx_mysql_thread_id=%s'''),
        ('statement', '''SELECT e.DIGEST_TEXT AS db_statement_digest,
                            e.ROWS_EXAMINED AS db_rows_examined,
                            e.ROWS_AFFECTED AS db_rows_affected
                         FROM performance_schema.threads t
                         JOIN performance_schema.events_statements_current e
                           ON e.THREAD_ID=t.THREAD_ID
                         WHERE t.PROCESSLIST_ID=%s'''),
    )
    errors = {}
    for name, sql in queries:
        try:
            cur.execute(sql, (connection_id,))
            result.update(cur.fetchone() or {})
        except Exception as exc:
            errors[name] = getattr(exc, 'errno', type(exc).__name__)
    try:
        cur.execute('''SELECT b.PROCESSLIST_ID AS blocking_connection_id,
                             b.PROCESSLIST_COMMAND AS blocking_command,
                             b.PROCESSLIST_STATE AS blocking_state,
                             b.PROCESSLIST_TIME AS blocking_age_seconds,
                             l.OBJECT_NAME AS table_name,l.INDEX_NAME AS index_name,
                             l.LOCK_TYPE AS lock_type,l.LOCK_MODE AS lock_mode
                      FROM performance_schema.data_lock_waits w
                      JOIN performance_schema.threads r ON r.THREAD_ID=w.REQUESTING_THREAD_ID
                      LEFT JOIN performance_schema.threads b ON b.THREAD_ID=w.BLOCKING_THREAD_ID
                      LEFT JOIN performance_schema.data_locks l
                        ON l.ENGINE=w.ENGINE AND l.ENGINE_LOCK_ID=w.REQUESTING_ENGINE_LOCK_ID
                      WHERE r.PROCESSLIST_ID=%s LIMIT 10''', (connection_id,))
        result['db_lock_waits'] = cur.fetchall()
    except Exception as exc:
        errors['locks'] = getattr(exc, 'errno', type(exc).__name__)
    result['db_diagnostic_errors'] = errors
    return result
