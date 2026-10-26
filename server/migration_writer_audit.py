"""Read-only capability evidence for migration; never changes grants or writers."""
from datetime import datetime, timezone
import hashlib
import re


def grant_target(target):
    """Parse complete SQL identifiers without collapsing embedded dots/quotes."""
    token = r'(?:`(?:[^`]|``)+`|"(?:[^"]|"")+"|[^.`"\s]+)'
    match = re.fullmatch('('+token+r')\s*\.\s*('+token+')', target.strip())
    if not match:raise ValueError('Invalid grant target')
    def identifier(value):
        if value[0] in ('`', '"'):
            quote=value[0];value=value[1:-1].replace(quote+quote,quote)
        return value.replace('\\_', '_').replace('\\%', '%')
    database,object_name=[identifier(value) for value in match.groups()]
    return database,object_name,match.groups()==('*','*'),match.group(2)=='*'


def grant_evidence(grants, schema):
    rows = []
    roles = False
    grant_option = False
    for raw in grants:
        # Never return raw grants: older servers may include authentication
        # clauses, account names or plugin-specific credential material.
        match = re.match(r'^(GRANT|REVOKE)\s+(.+?)\s+ON\s+(.+?)\s+(?:TO|FROM)\s', str(raw), re.I)
        if not match:
            roles = True
            continue
        effect, privileges, target = match.groups()
        option = effect.upper() == 'GRANT' and bool(re.search(r'\sWITH\s+GRANT\s+OPTION\s*$', str(raw), re.I))
        grant_option = grant_option or option
        # SHOW GRANTS uses ANSI double quotes when ANSI_QUOTES is active.
        # Parse complete identifiers so embedded quotes/dots cannot change scope.
        try:database,object_name,global_scope,database_scope=grant_target(target)
        except ValueError:
            roles = True
            continue
        scope = 'GLOBAL' if global_scope else 'CURRENT_DATABASE' if database == schema and database_scope else 'CURRENT_DATABASE_OBJECT' if database == schema else 'OTHER_SCOPE'
        names = [name.strip().upper() for name in privileges.split(',')]
        if any(not re.fullmatch(r'[A-Z_ ]{1,80}', name) for name in names):
            roles = True
            continue
        rows.append({'scope': scope, 'privileges': names, 'effect': 'GRANT' if effect.upper() == 'GRANT' else 'RESTRICTION', 'grant_option': option})
    return {'grants': [{'scope': row['scope'], 'privileges': row['privileges']} for row in rows if row['effect'] == 'GRANT'],
            'scoped_grants': rows, 'role_or_unparsed_grants_present': roles,
            'grant_option_observed': grant_option, 'effective_role_grants_expanded': False}


def classified_counts(cur, query, fields):
    """Return bounded aggregate metadata, never SQL text or account names."""
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return {'available': True, 'visibility': 'ACCOUNT_PRIVILEGES',
                'truncated': len(rows) > 100,
                'groups': [{field: row[field] for field in fields} for row in rows[:100]]}
    except Exception:
        return {'available': False, 'visibility': 'UNKNOWN'}


def writer_inventory(connect, seafood_tables=()):
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
                cur.execute('SELECT CURRENT_ROLE() AS active_roles, @@partial_revokes AS partial_revokes, @@read_only AS read_only, @@super_read_only AS super_read_only')
                controls = cur.fetchone()
                result['role_and_server_controls'] = {
                    'available': True, 'active_roles_present': str(controls['active_roles']).strip().upper() != 'NONE',
                    'active_roles_fingerprint': hashlib.sha256(str(controls['active_roles']).encode()).hexdigest()[:16],
                    'partial_revokes': bool(controls['partial_revokes']),
                    'server_read_only': bool(controls['read_only']), 'server_super_read_only': bool(controls['super_read_only']),
                    'effective_role_grants_expanded': False}
            except Exception:
                result['role_and_server_controls'] = {'available': False}
            try:
                cur.execute('SHOW GRANTS FOR CURRENT_USER')
                grants = [str(next(iter(row.values()))) for row in cur.fetchall()]
                result['privileges'] = {'available': True, **grant_evidence(grants, current['schema_name'])}
            except Exception:
                result['privileges'] = {'available': False}
            visible_all = any(row['effect'] == 'GRANT' and row['scope'] == 'GLOBAL' and any(name in ('PROCESS', 'ALL PRIVILEGES') for name in row['privileges'])
                              for row in result['privileges'].get('scoped_grants', []))
            try:
                # No SQL text, hostnames, credentials or session identifiers.
                cur.execute('SELECT COMMAND,COUNT(*) AS connection_count FROM information_schema.PROCESSLIST WHERE DB=DATABASE() GROUP BY COMMAND')
                result['connections'] = {'available': True, 'visibility': 'GLOBAL_PROCESS_GRANT_OBSERVED' if visible_all else 'POTENTIALLY_ACCOUNT_ONLY',
                                         'counts': {str(row['COMMAND']): int(row['connection_count']) for row in cur.fetchall()}}
            except Exception:
                result['connections'] = {'available': False, 'visibility': 'UNKNOWN'}
            # A session with another/no default DB can still write this schema
            # through qualified names. The earlier per-schema count is retained
            # for compatibility, but must not be treated as a writer inventory.
            result['all_visible_connections'] = classified_counts(cur, """
                SELECT CASE WHEN DB=DATABASE() THEN 'CURRENT_DATABASE'
                            WHEN DB IS NULL THEN 'NO_DEFAULT_DATABASE' ELSE 'OTHER_DATABASE' END AS schema_scope,
                       COMMAND AS command,COUNT(*) AS connection_count
                FROM information_schema.PROCESSLIST GROUP BY schema_scope,COMMAND LIMIT 101
            """, ('schema_scope', 'command', 'connection_count'))
            result['all_visible_connections']['qualified_cross_schema_writes_not_excluded'] = True
            result['visible_transactions'] = classified_counts(cur, """
                SELECT TRX_STATE AS state,TRX_IS_READ_ONLY AS read_only,COUNT(*) AS transaction_count
                FROM information_schema.INNODB_TRX GROUP BY TRX_STATE,TRX_IS_READ_ONLY LIMIT 101
            """, ('state', 'read_only', 'transaction_count'))
            result['table_engines'] = classified_counts(cur, """
                SELECT COALESCE(ENGINE,'NOT_A_BASE_TABLE') AS engine,COUNT(*) AS table_count
                FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() GROUP BY ENGINE LIMIT 101
            """, ('engine', 'table_count'))
            result['foreign_key_boundary'] = classified_counts(cur, """
                SELECT CASE WHEN TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_SCHEMA=DATABASE() THEN 'WITHIN_DATABASE'
                            WHEN TABLE_SCHEMA=DATABASE() THEN 'REFERENCES_OTHER_DATABASE' ELSE 'REFERENCED_BY_OTHER_DATABASE' END AS boundary,
                       COUNT(*) AS foreign_key_column_count
                FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_SCHEMA IS NOT NULL
                AND (TABLE_SCHEMA=DATABASE() OR REFERENCED_TABLE_SCHEMA=DATABASE()) GROUP BY boundary LIMIT 101
            """, ('boundary', 'foreign_key_column_count'))
            result['all_visible_events'] = classified_counts(cur, """
                SELECT CASE WHEN EVENT_SCHEMA=DATABASE() THEN 'CURRENT_DATABASE' ELSE 'OTHER_DATABASE' END AS schema_scope,
                       STATUS AS status,LEFT(SHA2(DEFINER,256),16) AS definer_fingerprint,COUNT(*) AS event_count
                FROM information_schema.EVENTS GROUP BY schema_scope,STATUS,definer_fingerprint LIMIT 101
            """, ('schema_scope', 'status', 'definer_fingerprint', 'event_count'))
            result['all_visible_routines'] = classified_counts(cur, """
                SELECT CASE WHEN ROUTINE_SCHEMA=DATABASE() THEN 'CURRENT_DATABASE' ELSE 'OTHER_DATABASE' END AS schema_scope,
                       ROUTINE_TYPE AS routine_type,SECURITY_TYPE AS security_type,
                       LEFT(SHA2(DEFINER,256),16) AS definer_fingerprint,COUNT(*) AS routine_count
                FROM information_schema.ROUTINES GROUP BY schema_scope,ROUTINE_TYPE,SECURITY_TYPE,definer_fingerprint LIMIT 101
            """, ('schema_scope', 'routine_type', 'security_type', 'definer_fingerprint', 'routine_count'))
            result['all_visible_triggers'] = classified_counts(cur, """
                SELECT CASE WHEN TRIGGER_SCHEMA=DATABASE() THEN 'CURRENT_DATABASE' ELSE 'OTHER_DATABASE' END AS schema_scope,
                       EVENT_MANIPULATION AS event_type,ACTION_TIMING AS timing,
                       LEFT(SHA2(DEFINER,256),16) AS definer_fingerprint,COUNT(*) AS trigger_count
                FROM information_schema.TRIGGERS GROUP BY schema_scope,EVENT_MANIPULATION,ACTION_TIMING,definer_fingerprint LIMIT 101
            """, ('schema_scope', 'event_type', 'timing', 'definer_fingerprint', 'trigger_count'))
            result['uploaded_work'] = classified_counts(cur, """
                SELECT processing_status AS status,COUNT(*) AS file_count
                FROM ingest_file WHERE duplicate_of_file_id IS NULL GROUP BY processing_status LIMIT 101
            """, ('status', 'file_count'))
            result['pipeline_work'] = classified_counts(cur, """
                SELECT stage_name,processing_status AS status,COUNT(*) AS run_count FROM pipeline_run
                WHERE processing_status IN ('STARTED','PAUSE_REQUESTED','QUEUED','PENDING')
                GROUP BY stage_name,processing_status LIMIT 101
            """, ('stage_name', 'status', 'run_count'))
            result['freeze_proof_missing'] = ['PERSISTENT_ADMISSION_AND_DRAIN', 'ALL_WRITER_IDENTITIES_AND_EFFECTIVE_ROLES',
                                              'EXTERNAL_SQL_AND_DEFINER_PATHS', 'ISOLATED_PERSISTENT_DATABASE_FENCE',
                                              'GOOGLE_WRITER_FENCE']
            try:
                cur.execute('SELECT STATUS,COUNT(*) AS event_count FROM information_schema.EVENTS WHERE EVENT_SCHEMA=DATABASE() GROUP BY STATUS')
                result['database_events'] = {'available': True, 'visibility': 'ACCOUNT_PRIVILEGES',
                                             'counts': {str(row['STATUS']): int(row['event_count']) for row in cur.fetchall()}}
            except Exception:
                result['database_events'] = {'available': False, 'visibility': 'UNKNOWN'}
            from migration_writer_preflight import preflight_inventory
            result['cutover_preflight'] = preflight_inventory(cur, current, seafood_tables, grant_evidence, classified_counts)
            return result
        finally:
            cur.close()
            conn.rollback()

