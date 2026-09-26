from __future__ import annotations
import json
from dataclasses import dataclass,asdict
from pathlib import Path
APP_DIR=Path(__file__).resolve().parent
CONFIG_PATH=APP_DIR/'settings.json'
KEYRING_SERVICE='FULL_MYSQL_Seafood_v7_API'
@dataclass(frozen=True)
class Settings:
    api_url:str=''
    device_id:str='WORK-PC'
    incoming_dir:str='incoming'
    archive_dir:str='archive'
    failed_dir:str='failed'
    scan_seconds:int=3
    stable_seconds:int=10
    batch_quiet_seconds:int=20
    poll_seconds:int=8
    @classmethod
    def load(cls):
        if not CONFIG_PATH.exists(): return cls()
        raw=json.loads(CONFIG_PATH.read_text(encoding='utf-8')); allowed={k:raw[k] for k in asdict(cls()).keys() if k in raw}; return cls(**allowed)
    def path(self,v):
        p=Path(v); return p if p.is_absolute() else APP_DIR/p
    def token(self):
        import keyring; return keyring.get_password(KEYRING_SERVICE,self.device_id) or ''
def get_settings(): return Settings.load()
def save_settings(s,token=None):
    CONFIG_PATH.write_text(json.dumps(asdict(s),indent=2),encoding='utf-8')
    for p in [s.path(s.incoming_dir),s.path(s.archive_dir),s.path(s.failed_dir),APP_DIR/'logs']: p.mkdir(parents=True,exist_ok=True)
    if token is not None:
        import keyring; keyring.set_password(KEYRING_SERVICE,s.device_id,token)
