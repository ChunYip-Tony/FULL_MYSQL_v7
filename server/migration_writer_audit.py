"""Read-only capability evidence for migration; never changes grants or writers."""
from datetime import datetime, timezone
import hashlib
import re


def grant_evidence(grants, schema):
    rows = []
    roles = False
    for raw in grants:
        # Never return raw grants: older servers may include authentication
        # clauses, account names or plugin-specific credential material.
        match = re.match(r'^GRANT\s+(.+?)\s+ON\s+(.+?)\s+TO\s', str(raw), re.I)
        if not match:
            roles = True
            continue
        privileges, target = match.groups()
        target = target.replace('`', '').strip()
        scope = 'GLOBAL' if target == '*.*' else 'CURRENT_DATABASE' if target == schema + '.*' else 'OTHER_SCOPE'
        names = [name.strip().upper() for name in privileges.split(',')]
        if any(not re.fullmatch(r'[A-Z_ ]{1,80}', name) for name in names):
            roles = True
            continue
        rows.append({'scope': scope, 'privileges': names})
    return {'grants': rows, 'role_or_unparsed_grants_present': roles}


def writer_inventory(connect):
    result = {'contract': 'SEAFOOD_WRITER_AUDIT_V1', 'checked_at': datetime.now(timezone.utc).isoformat(),
              'read_only': True, 'freeze_state': 'NOT_ESTABLISHED', 'external_writer_inventory_complete': False,
              'database_controls_changed': False}
    with connect(read_timeout=20, connection_timeout=10) as conn:
        conn.start_transaction(readonly=True)
        cur = conn.cursor(dictionary=True, buffered=True)
        try:
            cur.execute('SELECT DATABASE() AS schema_name, VERSION() AS version, CURRENT_USER() AS account')
            current = cur.fetchone()
            result['server_version'] = current['version']
            result['account_fingerprint'] = hashlib.sha256(str(current['account']).encode()).hexdigest()[:16]
            result['schema_fingerprint'] = hashlib.sha256(str(current['schema_name']).encode()).hexdigest()[:16]
            try:
                cur.execute('SHOW GRANTS FOR CURRENT_USER')
                grants = [str(next(iter(row.values()))) for row in cur.fetchall()]
                result['privileges'] = {'available': True, **grant_evidence(grants, current['schema_name'])}
            except Exception:
                result['privileges'] = {'available': False}
            visible_all = any(row['scope'] == 'GLOBAL' and any(name in ('PROCESS', 'ALL PRIVILEGES') for name in row['privileges'])
                              for row in result['privileges'].get('grants', []))
            try:
                # No SQL text, hostnames, credentials or session identifiers.
                cur.execute('SELECT COMMAND,COUNT(*) AS connection_count FROM information_schema.PROCESSLIST WHERE DB=DATABASE() GROUP BY COMMAND')
                result['connections'] = {'available': True, 'visibility': 'GLOBAL_PROCESS_GRANT_OBSERVED' if visible_all else 'POTENTIALLY_ACCOUNT_ONLY',
                                         'counts': {str(row['COMMAND']): int(row['connection_count']) for row in cur.fetchall()}}
            except Exception:
                result['connections'] = {'available': False, 'visibility': 'UNKNOWN'}
            try:
                cur.execute('SELECT STATUS,COUNT(*) AS event_count FROM information_schema.EVENTS WHERE EVENT_SCHEMA=DATABASE() GROUP BY STATUS')
                result['database_events'] = {'available': True, 'visibility': 'ACCOUNT_PRIVILEGES',
                                             'counts': {str(row['STATUS']): int(row['event_count']) for row in cur.fetchall()}}
            except Exception:
                result['database_events'] = {'available': False, 'visibility': 'UNKNOWN'}
            return result
        finally:
            cur.close()
            conn.rollback()
