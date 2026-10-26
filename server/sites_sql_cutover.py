"""Bounded Seafood SQL cutover. No caller SQL, URLs, accounts or schema names.

Preparing a restore controller does not freeze production. Freeze additionally
requires the committed isolated startup gate and an empty legacy connection set.
Schema-level partial revokes leave all other databases and SELECT access intact.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re

from fastapi import HTTPException
from db import db_conn
from migration_writer_audit import grant_evidence
from sites_cutover_gate import deployment_mode

AUTH_SHA256 = '25501ff1d2758cbbe1d05c06a620ca59e5552f0067cd8a8664cf21c52712ef72'
EXPIRES_AT = '2026-10-27T00:00:00+00:00'
SCHEMA_FINGERPRINT = '4f44bd4b1375fc76'
CURRENT_ACCOUNT = '55f6368ffeffc6f0'
WRITERS = frozenset({'55f6368ffeffc6f0','4392eae40074b71f','bd716f2b3ab40459','d571f78aad03ed5d'})
ROOT_ACCOUNT = '0b7ce8002dc7fa01'
WRITE_PRIVILEGES = frozenset('INSERT|UPDATE|DELETE|CREATE|DROP|REFERENCES|INDEX|ALTER|CREATE TEMPORARY TABLES|LOCK TABLES|EXECUTE|CREATE VIEW|CREATE ROUTINE|ALTER ROUTINE|EVENT|TRIGGER'.split('|'))
CONTROL_TABLE = '_sites_cutover_control'
PROVIDER_POLICY = 'https://docs.digitalocean.com/products/databases/mysql/details/limits/'

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()[:16]

def identifier(value):
    return '`' + str(value).replace('`', '``') + '`'

def account(user, host='%'):
    return identifier(user) + '@' + identifier(host)

def identity(value):
    if not isinstance(value,str) or not re.fullmatch(r'seafood-sites-[a-z0-9-]{1,64}',value):
        raise ValueError('Invalid cutover identity')
    return value

def controller_user(cutover_id):
    return 'sites_rb_' + hashlib.sha256(identity(cutover_id).encode()).hexdigest()[:16]

def authorize(header):
    if datetime.now(timezone.utc) >= datetime.fromisoformat(EXPIRES_AT):
        raise HTTPException(410, 'Cutover control window ended')
    value = str(header or '')
    if not value.startswith('Bearer ') or len(value)>256 or not hmac.compare_digest(hashlib.sha256(value[7:].encode()).hexdigest(),AUTH_SHA256):
        raise HTTPException(401, 'Authorized cutover control required')

def rows(cur, query, args=()):
    cur.execute(query,args)
    return cur.fetchall()

def grants(cur, user, host):
    result = sorted(str(next(iter(r.values()))) for r in rows(cur,'SHOW GRANTS FOR '+account(user,host)))
    # This endpoint is MySQL 8 only. Never archive credential-bearing old syntax.
    if any(re.search(r'\bIDENTIFIED\s+(?:BY|WITH)|\bPASSWORD\s*[=\(]|\bAS\s+[\x27\x22]',r,re.I) for r in result):
        raise ValueError('Credential-bearing grant output is not supported')
    return result

def provider_evidence(cur):
    from config import get_settings
    settings=get_settings();parts=settings.db_parts();host=str(parts['host']).lower()
    cipher=rows(cur,"SHOW SESSION STATUS LIKE 'Ssl_cipher'")[0]
    tls=bool(cipher.get('Value'))
    verified=host.endswith('.db.ondigitalocean.com') and bool(settings.ca_path()) and tls
    if not verified:raise ValueError('Managed provider identity and verified TLS are required')
    return {'provider':'DIGITALOCEAN_MANAGED_MYSQL','verifiedHostnameAndCA':True,'tls':True,
            'reservedRootPolicy':PROVIDER_POLICY,'rootAccountFingerprint':ROOT_ACCOUNT,
            'rootHandling':'PROVIDER_ADMIN_UNCHANGED'}

def inspect_plan(cur,cutover_id,previous=None):
    identity(cutover_id)
    info=rows(cur,'SELECT DATABASE() AS db,CURRENT_USER() AS account,@@version AS version,@@partial_revokes AS partial_revokes')[0]
    schema=info['db']
    if fingerprint(schema)!=SCHEMA_FINGERPRINT or fingerprint(info['account'])!=CURRENT_ACCOUNT or not str(info['version']).startswith('8.4.') or not info['partial_revokes']:
        raise ValueError('Source database identity or partial-revoke capability differs')
    provider=provider_evidence(cur)
    for table in ['role_edges','default_roles','proxies_priv']:
        if rows(cur,'SELECT COUNT(*) AS n FROM mysql.'+identifier(table))[0]['n']:
            raise ValueError('Role or proxy paths require separate classification')
    if rows(cur,"SELECT @@mandatory_roles AS roles")[0]['roles']:
        raise ValueError('Mandatory roles require separate classification')
    if rows(cur,'SELECT COUNT(*) AS n FROM information_schema.EVENTS')[0]['n']:
        raise ValueError('Database events require separate retirement')
    if rows(cur,"SELECT COUNT(*) AS n FROM information_schema.ROUTINES WHERE SECURITY_TYPE='DEFINER'")[0]['n'] or rows(cur,'SELECT COUNT(*) AS n FROM information_schema.TRIGGERS')[0]['n']:
        raise ValueError('Definer routines or triggers require separate classification')
    if rows(cur,"SELECT COUNT(*) AS n FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_SCHEMA IS NOT NULL AND ((TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_SCHEMA<>DATABASE()) OR (TABLE_SCHEMA<>DATABASE() AND REFERENCED_TABLE_SCHEMA=DATABASE()))")[0]['n']:
        raise ValueError('Cross-database foreign keys require separate classification')
    users=rows(cur,'SELECT User,Host,account_locked FROM mysql.user ORDER BY User,Host LIMIT 101')
    if len(users)>100:raise ValueError('Account inventory is truncated')
    targets=[];root_seen=False;inventory=[]
    for row in users:
        fp=fingerprint(str(row['User'])+'@'+str(row['Host']))
        raw=grants(cur,row['User'],row['Host']);evidence=grant_evidence(raw,schema)
        if row['User']==controller_user(cutover_id) and row['Host']=='%':
            try:validate_controller_grants(evidence)
            except ValueError:
                # Grant targets contain identifiers only; authentication clauses
                # were rejected by grants(). Never include accounts/passwords.
                targets=[re.search(r'\sON\s+(.+?)\s+(?:TO|FROM)\s',g,re.I).group(1) for g in raw if re.search(r'\sON\s+(.+?)\s+(?:TO|FROM)\s',g,re.I)]
                raise ValueError('Controller scope readback v3: '+canonical({'schema':schema,'targets':targets,'scopes':evidence['scoped_grants']})) from None
            continue
        inventory.append({'fingerprint':fp,'locked':row['account_locked'],'before':raw})
        if evidence['role_or_unparsed_grants_present']:raise ValueError('An account has unparsed grants')
        scoped=evidence['scoped_grants'];global_names={p for g in scoped if g['scope']=='GLOBAL' and g['effect']=='GRANT' for p in g['privileges']}
        local_grants=[g for g in scoped if g['scope'].startswith('CURRENT_DATABASE') and g['effect']=='GRANT']
        if fp==ROOT_ACCOUNT:
            if row['User']!='root' or 'SYSTEM_USER' not in global_names:raise ValueError('Provider root classification differs')
            root_seen=True;continue
        if row['account_locked']=='Y' and str(row['User']) in {'mysql.sys','mysql.session','mysql.infoschema'}:continue
        has_write=bool(global_names&WRITE_PRIVILEGES or any(set(g['privileges'])&WRITE_PRIVILEGES for g in local_grants))
        if has_write and fp not in WRITERS:raise ValueError('An additional SQL writer must be classified')
        if fp not in WRITERS:continue
        if row['account_locked']!='N' or local_grants or 'SYSTEM_USER' in global_names:
            raise ValueError('Writer account shape differs from the reviewed global-grant plan')
        restrictions=[g for g in scoped if g['scope']=='CURRENT_DATABASE' and g['effect']=='RESTRICTION']
        if restrictions and previous is None:raise ValueError('A new plan cannot replace an existing database restriction')
        before=next((t['before'] for t in previous['targets'] if t['fingerprint']==fp),None) if previous else raw
        targets.append({'fingerprint':fp,'user':row['User'],'host':row['Host'],'before':before,'privileges':sorted(global_names&WRITE_PRIVILEGES)})
    if not root_seen or {t['fingerprint'] for t in targets}!=WRITERS:raise ValueError('Writer inventory differs')
    if previous:
        original={r['fingerprint']:r for r in previous['inventory']}
        if set(original)!={r['fingerprint'] for r in inventory}:raise ValueError('SQL account inventory changed')
        for row in inventory:
            if row['fingerprint'] in WRITERS:
                row['before']=original[row['fingerprint']]['before']
            if row!=original[row['fingerprint']]:raise ValueError('SQL account privileges or locks changed')
    return {'contract':'SEAFOOD_SQL_CUTOVER_PLAN_V1','cutoverId':cutover_id,'schema':schema,'schemaFingerprint':SCHEMA_FINGERPRINT,'inventory':inventory,
            'provider':provider,'controllerUser':controller_user(cutover_id),'targets':sorted(targets,key=lambda t:t['fingerprint']),
            'rollbackMode':'EXACT_ORIGINAL_GRANTS','otherDatabasesChanged':False,'productionFrozen':False}

def validate_controller_grants(evidence):
    if evidence['role_or_unparsed_grants_present']:raise ValueError('Unparsed controller privileges')
    local=[]
    for g in evidence['scoped_grants']:
        if g['effect']!='GRANT' or g['scope'] not in ['GLOBAL','CURRENT_DATABASE'] or (g['scope']=='GLOBAL' and set(g['privileges'])!={'USAGE'}):raise ValueError('Controller has unexpected privileges')
        if g['scope']=='CURRENT_DATABASE':local.append(g)
    if len(local)!=1 or set(local[0]['privileges'])!=WRITE_PRIVILEGES|{'SELECT'} or not local[0]['grant_option']:raise ValueError('Controller restore privileges differ')

def ensure_gate(cutover_id):
    if deployment_mode()!={'mode':'ISOLATED_MIGRATION_READS','cutover_id':cutover_id}:
        raise ValueError('The exact isolated startup gate must be live before freezing')

@contextmanager
def controller_connection(user,password,database=True):
    if not isinstance(password,str) or not re.fullmatch(r'[A-Za-z0-9_-]{40,128}',password):raise ValueError('Invalid private controller credential')
    from config import get_settings
    import mysql.connector
    s=get_settings();d=s.db_parts();ca=s.ca_path()
    if not ca or not str(d['host']).endswith('.db.ondigitalocean.com'):raise ValueError('Verified source transport required')
    options=dict(host=d['host'],port=d['port'],user=user,password=password,autocommit=True,connection_timeout=10,read_timeout=30,
                 ssl_ca=str(ca),ssl_verify_cert=True,ssl_verify_identity=True,charset='utf8mb4',use_unicode=True)
    if database:options['database']=d['database']
    conn=mysql.connector.connect(**options)
    try:yield conn
    finally:conn.close()

def read_control(cur,cutover_id):
    result=rows(cur,'SELECT document FROM '+identifier(CONTROL_TABLE)+' WHERE cutover_id=%s',(identity(cutover_id),))
    if not result:raise ValueError('No prepared rollback controller')
    return json.loads(result[0]['document'])

def save_control(cur,record):
    cur.execute('INSERT INTO '+identifier(CONTROL_TABLE)+'(cutover_id,document) VALUES(%s,%s) ON DUPLICATE KEY UPDATE document=VALUES(document)',(record['plan']['cutoverId'],canonical(record)))

def restriction_shape(cur,plan,allow_partial=False):
    for target in plan['targets']:
        raw=grants(cur,target['user'],target['host']);summary=grant_evidence(raw,plan['schema'])
        if summary['role_or_unparsed_grants_present']:raise ValueError('Unparsed current writer grants')
        restrictions=[g for g in summary['scoped_grants'] if g['effect']=='RESTRICTION' and g['scope']=='CURRENT_DATABASE']
        denied={p for r in restrictions for p in r['privileges']}
        retained=[]
        for grant in raw:
            parsed=grant_evidence([grant],plan['schema'])['scoped_grants']
            if not any(g['scope']=='CURRENT_DATABASE' and g['effect']=='RESTRICTION' for g in parsed):retained.append(grant)
        if retained!=target['before'] or not denied.issubset(set(target['privileges'])) or (not allow_partial and denied!=set(target['privileges'])):
            raise ValueError('Writer privilege readback differs from the exact cutover plan')

def require_drained(cur,allowed):
    others=rows(cur,"SELECT ID,USER FROM information_schema.PROCESSLIST WHERE USER NOT IN ('event_scheduler','system user')")
    if any(int(r['ID']) not in allowed for r in others):raise ValueError('Legacy SQL connections have not drained')

def prepare(cur,plan,password,backup_hash):
    if backup_hash!=digest(plan):raise ValueError('Retained rollback manifest hash differs')
    schema=plan['schema'];user=plan['controllerUser'];cutover_id=plan['cutoverId']
    cur.execute('CREATE TABLE IF NOT EXISTS '+identifier(CONTROL_TABLE)+'(cutover_id VARCHAR(100) PRIMARY KEY,document JSON NOT NULL) ENGINE=InnoDB')
    existing=rows(cur,'SELECT document FROM '+identifier(CONTROL_TABLE)+' WHERE cutover_id=%s',(cutover_id,))
    if existing:
        record=json.loads(existing[0]['document'])
        if record['backupSha256']!=backup_hash or record['plan']!=plan:raise ValueError('Prepared cutover identity conflicts')
        if record['state'] not in ['PREPARING','PREPARED']:raise ValueError('Preparation is closed')
    else:
        if rows(cur,'SELECT User FROM mysql.user WHERE User=%s AND Host=%s',(user,'%')):raise ValueError('Controller identity already belongs to another account')
        record={'plan':plan,'backupSha256':backup_hash,'state':'PREPARING','restoreProbePassed':False};save_control(cur,record)
    exists=rows(cur,'SELECT User FROM mysql.user WHERE User=%s AND Host=%s',(user,'%'))
    if not exists:cur.execute('CREATE USER '+account(user)+' IDENTIFIED BY %s REQUIRE SSL',(password,))
    # Existing credentials are never rotated. A retry must authenticate the same account.
    with controller_connection(user,password,database=False):pass
    cur.execute('GRANT '+','.join(sorted(WRITE_PRIVILEGES|{'SELECT'}))+' ON '+identifier(schema)+'.* TO '+account(user)+' WITH GRANT OPTION')
    controller_grants=grant_evidence(grants(cur,user,'%'),schema)
    validate_controller_grants(controller_grants)
    # Exercise partial revoke and exact restore on a new locked, disposable login.
    # It cannot authenticate and never receives any business data.
    probe='sites_probe_'+hashlib.sha256(cutover_id.encode()).hexdigest()[:16]
    if rows(cur,'SELECT User FROM mysql.user WHERE User=%s AND Host=%s',(probe,'%')):raise ValueError('A prior probe needs review before retry')
    cur.execute('CREATE USER '+account(probe)+' IDENTIFIED BY %s ACCOUNT LOCK',(password,))
    try:
        cur.execute('GRANT INSERT ON *.* TO '+account(probe));before=grants(cur,probe,'%')
        with controller_connection(user,password) as conn:
            c=conn.cursor(dictionary=True,buffered=True)
            try:
                c.execute('REVOKE INSERT ON '+identifier(schema)+'.* FROM '+account(probe))
                after=grant_evidence(grants(cur,probe,'%'),schema)
                if not any(g['effect']=='RESTRICTION' and g['scope']=='CURRENT_DATABASE' and g['privileges']==['INSERT'] for g in after['scoped_grants']):raise ValueError('Partial revoke probe failed')
                c.execute('GRANT INSERT ON '+identifier(schema)+'.* TO '+account(probe))
                if grants(cur,probe,'%')!=before:raise ValueError('Exact grant restore probe failed')
            finally:c.close()
    finally:cur.execute('DROP USER '+account(probe))
    record.update(state='PREPARED',restoreProbePassed=True,preparedAt=datetime.now(timezone.utc).isoformat());save_control(cur,record)
    return {'contract':'SEAFOOD_SQL_PREPARED_V1','cutoverId':cutover_id,'backupSha256':backup_hash,'restoreProbePassed':True,'productionFrozen':False}

def freeze(conn,cur,cutover_id,password):
    ensure_gate(cutover_id);record=read_control(cur,cutover_id);plan=record['plan']
    if record['state'] not in ['PREPARED','FENCING','FROZEN'] or not record['restoreProbePassed']:raise ValueError('A verified independent restore path is required')
    if inspect_plan(cur,cutover_id,plan)!=plan:raise ValueError('The retained plan changed')
    restriction_shape(cur,plan,allow_partial=True)
    with controller_connection(plan['controllerUser'],password) as control:
        c=control.cursor(dictionary=True,buffered=True)
        try:
            allowed={int(rows(cur,'SELECT CONNECTION_ID() AS id')[0]['id']),int(rows(c,'SELECT CONNECTION_ID() AS id')[0]['id'])}
            require_drained(cur,allowed)
            record['state']='FENCING';save_control(c,record)
            for target in plan['targets']:
                current=grant_evidence(grants(cur,target['user'],target['host']),plan['schema'])
                denied={p for g in current['scoped_grants'] if g['scope']=='CURRENT_DATABASE' and g['effect']=='RESTRICTION' for p in g['privileges']}
                missing=set(target['privileges'])-denied
                if missing:c.execute('REVOKE '+','.join(sorted(missing))+' ON '+identifier(plan['schema'])+'.* FROM '+account(target['user'],target['host']))
            restriction_shape(cur,plan)
            require_drained(cur,allowed)
            # A new application connection must deny even zero-row business writes.
            with db_conn(read_timeout=15) as fresh:
                f=fresh.cursor()
                try:
                    for statement in ['UPDATE ingest_file SET file_id=file_id WHERE 1=0','DELETE FROM ingest_file WHERE 1=0']:
                        try:f.execute(statement)
                        except Exception as error:
                            if getattr(error,'errno',None)!=1142:raise ValueError('Unexpected write-denial proof') from None
                        else:raise ValueError('Fresh application connection still has business write access')
                finally:f.close();fresh.rollback()
            require_drained(cur,allowed)
            now=datetime.now(timezone.utc).isoformat()
            proof={'contract':'SEAFOOD_SQL_FREEZE_V1','cutoverId':cutover_id,'schemaFingerprint':SCHEMA_FINGERPRINT,
                   'backupSha256':record['backupSha256'],'businessWriterFingerprints':sorted(WRITERS),'provider':plan['provider'],
                   'controllerFingerprint':fingerprint(plan['controllerUser']+'@%'),'deploymentGate':deployment_mode(),
                   'businessWritesDenied':True,'legacyConnectionsDrained':True,'restoreProbePassed':True,'frozenAt':record.get('proof',{}).get('frozenAt',now)}
            record.update(state='FROZEN',proof=proof);save_control(c,record);return proof
        finally:c.close()

def verify(cur,cutover_id):
    ensure_gate(cutover_id);record=read_control(cur,cutover_id)
    if record['state'] not in ['FROZEN','COMMITTED']:raise ValueError('SQL freeze is not established')
    if inspect_plan(cur,cutover_id,record['plan'])!=record['plan']:raise ValueError('SQL account plan changed')
    restriction_shape(cur,record['plan'])
    if rows(cur,'SELECT COUNT(*) AS n FROM information_schema.INNODB_TRX WHERE TRX_ROWS_MODIFIED>0')[0]['n']:raise ValueError('A writer transaction is visible')
    return {**record['proof'],'state':record['state'],'verifiedAt':datetime.now(timezone.utc).isoformat()}

def rollback(cur,cutover_id,password):
    ensure_gate(cutover_id);record=read_control(cur,cutover_id)
    if record['state'] not in ['PREPARED','FENCING','FROZEN']:raise ValueError('Automatic restore is closed after native cutover commitment')
    plan=record['plan'];restriction_shape(cur,plan,allow_partial=True)
    with controller_connection(plan['controllerUser'],password) as conn:
        c=conn.cursor(dictionary=True,buffered=True)
        try:
            for target in plan['targets']:
                c.execute('GRANT '+','.join(target['privileges'])+' ON '+identifier(plan['schema'])+'.* TO '+account(target['user'],target['host']))
            for target in plan['targets']:
                if grants(cur,target['user'],target['host'])!=target['before']:raise ValueError('Restored grants differ from the original manifest')
            record['state']='ROLLED_BACK';record['restoredAt']=datetime.now(timezone.utc).isoformat();save_control(c,record)
        finally:c.close()
    return {'contract':'SEAFOOD_SQL_ROLLBACK_V1','cutoverId':cutover_id,'exactOriginalGrantsRestored':True,'applicationStartupStillIsolated':True}

def control_action(action,cutover_id,password=None,backup_hash=None):
    identity(cutover_id)
    with db_conn(read_timeout=30) as conn:
        conn.autocommit=True;cur=conn.cursor(dictionary=True,buffered=True)
        try:
            lock_name='sites-cutover:'+hashlib.sha256(cutover_id.encode()).hexdigest()[:40]
            cur.execute('SELECT GET_LOCK(%s,0) AS locked',(lock_name,))
            if not cur.fetchone()['locked']:raise ValueError('Another cutover operation is running')
            if action=='plan':
                plan=inspect_plan(cur,cutover_id);return {'plan':plan,'backupSha256':digest(plan),'readOnly':True,'controlVersion':'schema-scope-v3'}
            if action=='prepare':return prepare(cur,inspect_plan(cur,cutover_id),password,backup_hash)
            if action=='freeze':return freeze(conn,cur,cutover_id,password)
            if action=='verify':return verify(cur,cutover_id)
            if action=='rollback':return rollback(cur,cutover_id,password)
            if action=='commit':
                proof=verify(cur,cutover_id);record=read_control(cur,cutover_id)
                with controller_connection(record['plan']['controllerUser'],password) as controller:
                    c=controller.cursor(dictionary=True,buffered=True)
                    try:record['state']='COMMITTED';save_control(c,record)
                    finally:c.close()
                return {**proof,'state':'COMMITTED','automaticRollbackAllowed':False}
            raise ValueError('Unsupported bounded cutover operation')
        finally:
            try:cur.execute('SELECT RELEASE_LOCK(%s)',(lock_name,));cur.fetchall()
            finally:cur.close()
