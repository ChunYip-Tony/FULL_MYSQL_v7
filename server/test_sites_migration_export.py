import gzip
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from contextlib import contextmanager
from fastapi import HTTPException
import sites_migration_export as export

def test_auth_rejects_missing_wrong_and_expired(monkeypatch):
    monkeypatch.setattr(export,'AUTH_SHA256',hashlib.sha256(b'test-only').hexdigest())
    now=datetime(2026,10,24,tzinfo=timezone.utc)
    for header in [None,'test-only','Bearer wrong']:
        with pytest.raises(HTTPException) as exc:export.authorize(header,now)
        assert exc.value.status_code==401
    export.authorize('Bearer test-only',now)
    with pytest.raises(HTTPException) as exc:export.authorize('Bearer test-only',datetime(2026,10,28,tzinfo=timezone.utc))
    assert exc.value.status_code==410

def test_exact_financial_and_binary_values():
    value=json.loads(export.line([Decimal('123456789012345678.123456'),None,0,'001234',b'\xff']))
    assert value==[{'$decimal':'123456789012345678.123456'},None,0,'001234',{'$binary':'/w=='}]

def test_stream_roundtrip_and_no_false_completion():
    records=[export.line({'kind':'begin'}),export.line({'kind':'complete'})]
    assert gzip.decompress(b''.join(export.gzip_stream(records)))==b''.join(records)
    def broken():
        yield records[0]
        raise RuntimeError('database interrupted')
    with pytest.raises(RuntimeError):b''.join(export.gzip_stream(broken()))

def test_export_scope_excludes_runtime_caches_and_credentials():
    assert 'manual_true_stock' in export.TABLES
    assert 'raw_on_hand' in export.TABLES
    assert not export.TABLES.intersection({'users','sessions','api_tokens','yipman_app_ready_generation','yipman_app_ready_pointer'})

@pytest.mark.parametrize('expected',[2,3])
def test_one_readonly_transaction_count_fence_and_cleanup(monkeypatch,expected):
    monkeypatch.setattr(export,'TABLES',frozenset({'inventory_observation'}))
    class Cursor:
        def execute(self,sql,args=()):
            assert sql.startswith('SELECT ')
            if 'information_schema.TABLES' in sql:self.rows=[{'TABLE_NAME':'inventory_observation'},{'TABLE_NAME':'sessions'}]
            elif 'information_schema.COLUMNS' in sql:self.rows=[{'COLUMN_NAME':'id','DATA_TYPE':'int','COLUMN_TYPE':'int','IS_NULLABLE':'NO'},{'COLUMN_NAME':'amount','DATA_TYPE':'decimal','COLUMN_TYPE':'decimal','IS_NULLABLE':'YES'}]
            elif 'KEY_COLUMN_USAGE' in sql:self.rows=[{'COLUMN_NAME':'id'}]
            elif 'COUNT(*)' in sql:self.rows=[{'n':expected}]
            else:self.rows=[(1,Decimal('1.2500')),(2,None)]
        def fetchall(self):out=self.rows;self.rows=[];return out
        def fetchone(self):return self.rows.pop(0)
        def fetchmany(self,n):out=self.rows[:n];self.rows=self.rows[n:];return out
        def close(self):pass
    class Connection:
        rolled_back=False
        def start_transaction(self,**kwargs):assert kwargs=={'isolation_level':'REPEATABLE READ','consistent_snapshot':True,'readonly':True}
        def cursor(self,**kwargs):return Cursor()
        def rollback(self):self.rolled_back=True
    conn=Connection()
    @contextmanager
    def connect(**kwargs):yield conn
    records=[]
    if expected==3:
        with pytest.raises(RuntimeError,match='count mismatch'):
            for raw in export.snapshot_lines(connect):records.append(json.loads(raw))
        assert all(r['kind']!='complete' for r in records)
    else:
        records=[json.loads(raw) for raw in export.snapshot_lines(connect)]
        assert records[-1]['kind']=='complete' and records[-1]['rows']==2
        assert records[0]['tables']==['inventory_observation']
        assert next(r for r in records if r['kind']=='rows')['rows'][0][1]=={'$decimal':'1.2500'}
    assert conn.rolled_back
