"""Readiness for the standalone API: configuration and MySQL, never data writes."""
import os

from finder_department_store import mysql_connection
from finder_department_schema_setup import TABLES, VIEWS


def configuration_ready():
    tokens = [os.environ.get('FINDER_STORE_TOKEN_' + name, '') for name in ('MEAT', 'PRODUCE')]
    if any(len(token) < 40 for token in tokens) or tokens[0] == tokens[1]:
        return False
    # Reuse the verified TLS settings. This isolated image exposes none of the
    # Seafood admin routes: give it a new independent work token, not Seafood's.
    try:
        from config import Settings
        settings = Settings.load()
        parts = settings.db_parts()
        return bool(parts['host'] and parts['user'] and parts['password'] and settings.ca_path())
    except Exception:
        return False


def database_ready(connection=mysql_connection):
    """Validate the required objects without reading business rows or migrating."""
    with connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute('SELECT VERSION()')
            if not str(cur.fetchone()[0]).startswith('8.4.'):
                return False
            cur.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()')
            if not (TABLES | VIEWS) <= {row[0] for row in cur.fetchall()}:
                return False
            for view in sorted(VIEWS):
                cur.execute('SELECT * FROM ' + view + ' LIMIT 0')
                cur.fetchall()
            return True
        finally:
            cur.close()
            conn.rollback()


def readiness(config_check=configuration_ready, database_check=database_ready):
    # Provider health responses are public. Never return exceptions, hostnames,
    # usernames, passwords, connection strings, or customer records.
    try:
        ready = config_check() and database_check()
    except Exception:
        ready = False
    return {'status': 'ready' if ready else 'not_ready', 'service': 'finder-department-mysql'}
