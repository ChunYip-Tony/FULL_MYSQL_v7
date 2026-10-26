"""Bounded read-only cutover metadata. Never reads authentication material."""
import hashlib
import os
import ipaddress


def fingerprint(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def identifier(value):
    return '`' + str(value).replace('`', '``') + '`'


def account_metadata(user, host):
    user, host = str(user), str(host)
    kind = 'MYSQL_RESERVED_SYSTEM_NAME' if user in {'mysql.sys', 'mysql.session', 'mysql.infoschema'} else 'ROOT_ACCOUNT_NAME' if user == 'root' else 'OTHER_ACCOUNT_NAME'
    if host == 'localhost':
        reachability = 'LOCALHOST'
    elif '%' in host or '_' in host:
        reachability = 'HOST_PATTERN'
    else:
        try:
            address = ipaddress.ip_address(host)
            reachability = 'LOOPBACK_ADDRESS' if address.is_loopback else 'EXACT_IP_ADDRESS'
        except ValueError:
            reachability = 'HOSTNAME_OR_NETWORK_SPECIFICATION'
    return {'identity_name_class': kind, 'connection_match_class': reachability,
            'provider_ownership_verified': False, 'business_writer_classified': False}


def preflight_inventory(cur, current, seafood_tables, grants, query):
    result = {'contract': 'SEAFOOD_WRITER_PREFLIGHT_V1', 'read_only': True,
              'database_controls_changed': False, 'effective_writer_inventory_complete': False,
              'shared_department_store_enabled': os.getenv('FINDER_DEPARTMENT_STORE_ENABLED', '').strip() == '1'}
    try:
        # Only account identity and lock metadata. No password/hash/plugin/
        # authentication column or complete User_attributes document is read.
        cur.execute('SELECT User,Host,account_locked FROM mysql.user ORDER BY User,Host LIMIT 101')
        accounts = cur.fetchall()
        output = []
        for account in accounts[:100]:
            name = str(account['User']) + '@' + str(account['Host'])
            record = {'account_fingerprint': fingerprint(name), 'current_account': name == current['account'],
                      'account_locked': account['account_locked'] == 'Y',
                      **account_metadata(account['User'], account['Host'])}
            try:
                cur.execute('SHOW GRANTS FOR ' + identifier(account['User']) + '@' + identifier(account['Host']))
                raw = [str(next(iter(row.values()))) for row in cur.fetchall()]
                record['grants'] = {'available': True, **grants(raw, current['schema_name'])}
            except Exception:
                record['grants'] = {'available': False, 'visibility': 'UNKNOWN'}
            output.append(record)
        result['accounts'] = {'available': True, 'truncated': len(accounts) > 100, 'accounts': output,
                              'effective_roles_expanded': False,
                              'current_login_matches': [fingerprint(str(a['User']) + '@' + str(a['Host'])) for a in accounts[:100]
                                                        if str(a['User']) == current['account'].rsplit('@', 1)[0]]}
    except Exception:
        result['accounts'] = {'available': False, 'visibility': 'UNKNOWN'}
    result['role_edges'] = query(cur, """
        SELECT LEFT(SHA2(CONCAT(FROM_USER,'@',FROM_HOST),256),16) AS role_fingerprint,
               LEFT(SHA2(CONCAT(TO_USER,'@',TO_HOST),256),16) AS grantee_fingerprint,
               WITH_ADMIN_OPTION AS admin_option FROM mysql.role_edges LIMIT 101
    """, ('role_fingerprint', 'grantee_fingerprint', 'admin_option'))
    result['default_roles'] = query(cur, """
        SELECT LEFT(SHA2(CONCAT(DEFAULT_ROLE_USER,'@',DEFAULT_ROLE_HOST),256),16) AS role_fingerprint,
               LEFT(SHA2(CONCAT(USER,'@',HOST),256),16) AS grantee_fingerprint
        FROM mysql.default_roles LIMIT 101
    """, ('role_fingerprint', 'grantee_fingerprint'))
    result['mandatory_roles'] = query(cur, """
        SELECT (@@mandatory_roles<>'') AS present,
               LEFT(SHA2(@@mandatory_roles,256),16) AS roles_fingerprint,
               @@activate_all_roles_on_login AS activate_all_roles_on_login
    """, ('present', 'roles_fingerprint', 'activate_all_roles_on_login'))
    result['proxy_paths'] = query(cur, """
        SELECT LEFT(SHA2(CONCAT(User,'@',Host),256),16) AS grantee_fingerprint,
               LEFT(SHA2(CONCAT(Proxied_user,'@',Proxied_host),256),16) AS proxied_fingerprint,
               With_grant AS grant_option FROM mysql.proxies_priv LIMIT 101
    """, ('grantee_fingerprint', 'proxied_fingerprint', 'grant_option'))
    result['sessions'] = query(cur, """
        SELECT LEFT(SHA2(CONCAT(p.USER,':',p.ID),256),16) AS session_fingerprint,
               p.ID=CONNECTION_ID() AS audit_self,
               p.USER=SUBSTRING_INDEX(CURRENT_USER(),'@',1) AS same_login_name,
               CASE WHEN p.DB=DATABASE() THEN 'CURRENT_DATABASE'
                    WHEN p.DB IS NULL THEN 'NO_DEFAULT_DATABASE' ELSE 'OTHER_DATABASE' END AS schema_scope,
               p.COMMAND AS command,p.TIME AS command_duration_seconds,
               CASE WHEN p.USER='event_scheduler' THEN 'MYSQL_EVENT_SCHEDULER_NAME'
                    WHEN p.USER='system user' THEN 'MYSQL_SYSTEM_THREAD_NAME'
                    ELSE 'OTHER_LOGIN_NAME' END AS login_name_class,
               t.TRX_STATE AS transaction_state,t.TRX_IS_READ_ONLY AS transaction_read_only,
               t.TRX_ROWS_MODIFIED AS rows_modified,t.TRX_ROWS_LOCKED AS rows_locked
        FROM information_schema.PROCESSLIST p LEFT JOIN information_schema.INNODB_TRX t ON t.TRX_MYSQL_THREAD_ID=p.ID
        ORDER BY p.ID LIMIT 101
    """, ('session_fingerprint', 'audit_self', 'same_login_name', 'schema_scope', 'command', 'command_duration_seconds', 'login_name_class',
          'transaction_state', 'transaction_read_only', 'rows_modified', 'rows_locked'))
    result['sessions']['login_match_is_not_authenticated_identity'] = True
    try:
        cur.execute('SELECT TABLE_NAME,TABLE_TYPE,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME LIMIT 201')
        tables = cur.fetchall()
        shared = {'finder_department_head', 'finder_department_state'}
        output = []
        for row in tables[:200]:
            name = row['TABLE_NAME']
            item = {'table': name, 'type': row['TABLE_TYPE'], 'engine': row['ENGINE'],
                    'scope': 'SEAFOOD_EXPORT' if name in seafood_tables else 'SHARED_DEPARTMENT_STORE' if name in shared else 'NOT_CLASSIFIED'}
            if name in shared:
                cur.execute('SELECT COUNT(*) AS row_count FROM ' + identifier(name))
                item['rows'] = int(cur.fetchone()['row_count'])
            output.append(item)
        result['tables'] = {'available': True, 'truncated': len(tables) > 200, 'tables': output}
    except Exception:
        result['tables'] = {'available': False, 'visibility': 'UNKNOWN'}
    # These three derived tables support multiple departments. Report their
    # actual populations, rather than assuming a Seafood-only deployment.
    result['department_analysis'] = {}
    for table in ('analysis_item_current', 'analysis_family_current'):
        result['department_analysis'][table] = query(cur,
            'SELECT department_code,analysis_status,COUNT(*) AS row_count,'
            'MIN(source_publish_batch_id) AS first_source_batch,MAX(source_publish_batch_id) AS last_source_batch '
            'FROM ' + identifier(table) + ' GROUP BY department_code,analysis_status LIMIT 101',
            ('department_code', 'analysis_status', 'row_count', 'first_source_batch', 'last_source_batch'))
    result['department_analysis']['analysis_layer_status'] = query(cur, """
        SELECT department_code,layer_status,source_publish_batch_id,item_rows,
               ready_rows,hold_rows,historical_rows,family_rows
        FROM analysis_layer_status ORDER BY department_code LIMIT 101
    """, ('department_code', 'layer_status', 'source_publish_batch_id', 'item_rows',
          'ready_rows', 'hold_rows', 'historical_rows', 'family_rows'))
    result['views'] = query(cur, """
        SELECT v.TABLE_NAME AS name,
               CASE WHEN v.TABLE_SCHEMA=DATABASE() THEN 'CURRENT_DATABASE' ELSE 'OTHER_DATABASE' END AS schema_scope,
               v.SECURITY_TYPE AS security_type,v.IS_UPDATABLE AS is_updatable,
               LEFT(SHA2(v.DEFINER,256),16) AS definer_fingerprint
        FROM information_schema.VIEWS v
        WHERE v.TABLE_SCHEMA=DATABASE() OR EXISTS(
          SELECT 1 FROM information_schema.VIEW_TABLE_USAGE u WHERE u.VIEW_SCHEMA=v.TABLE_SCHEMA
          AND u.VIEW_NAME=v.TABLE_NAME AND u.TABLE_SCHEMA=DATABASE())
        ORDER BY v.TABLE_SCHEMA,v.TABLE_NAME LIMIT 101
    """, ('name', 'schema_scope', 'security_type', 'is_updatable', 'definer_fingerprint'))
    result['view_dependencies'] = query(cur, """
        SELECT VIEW_NAME AS view_name,TABLE_NAME AS table_name,
               CASE WHEN VIEW_SCHEMA=DATABASE() AND TABLE_SCHEMA=DATABASE() THEN 'WITHIN_DATABASE'
                    WHEN VIEW_SCHEMA=DATABASE() THEN 'REFERENCES_OTHER_DATABASE' ELSE 'REFERENCED_BY_OTHER_DATABASE' END AS boundary
        FROM information_schema.VIEW_TABLE_USAGE WHERE VIEW_SCHEMA=DATABASE() OR TABLE_SCHEMA=DATABASE()
        ORDER BY VIEW_SCHEMA,VIEW_NAME,TABLE_SCHEMA,TABLE_NAME LIMIT 101
    """, ('view_name', 'table_name', 'boundary'))
    return result
