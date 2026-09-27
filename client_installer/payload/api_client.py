from __future__ import annotations
import requests
from pathlib import Path
from config import get_settings

def _cfg():
    s=get_settings(); url=s.api_url.rstrip('/'); token=s.token()
    if not url: raise RuntimeError('API URL is not configured.')
    if not token: raise RuntimeError('API token is not stored for this device.')
    return s,url,{'Authorization':f'Bearer {token}'}
def get(path,timeout=30):
    s,u,h=_cfg(); r=requests.get(u+path,headers=h,timeout=timeout); r.raise_for_status(); return r.json()
def post_json(path,payload=None,timeout=30):
    s,u,h=_cfg(); r=requests.post(u+path,headers=h,json=payload or {},timeout=timeout); r.raise_for_status(); return r.json()
def upload(session_id:str,p:Path):
    s,u,h=_cfg()
    with p.open('rb') as f:
        r=requests.post(u+f'/v1/batches/{session_id}/files',headers=h,files={'file':(p.name,f,'application/octet-stream')},timeout=600)
    r.raise_for_status(); return r.json()
def test_api(): return get('/v1/status',timeout=30)


def manual_authority_refresh():
    return post_json(
        '/v1/maintenance/manual-authority-refresh',
        {'confirm':'APPLY_CONFIRMED_USER_AUTHORITY'},
        timeout=120,
    )


def confirmed_uom_refresh():
    return post_json(
        '/v1/maintenance/confirmed-uom-refresh',
        {'confirm':'APPLY_CONFIRMED_UOM_AND_REBUILD'},
        timeout=180,
    )
