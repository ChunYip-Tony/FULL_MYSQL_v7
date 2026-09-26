from __future__ import annotations
import json, os, tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, unquote

@dataclass(frozen=True)
class Settings:
    database_url: str
    ca_cert_text: str
    api_tokens: dict[str, str]
    admin_devices: set[str]
    upload_limit_mb: int = 96

    @classmethod
    def load(cls) -> 'Settings':
        url = os.environ.get('FULLMYSQL_DATABASE_URL','').strip()
        if not url:
            host = os.environ.get('FULLMYSQL_DB_HOST','').strip()
            port = os.environ.get('FULLMYSQL_DB_PORT','25060').strip()
            user = os.environ.get('FULLMYSQL_DB_USER','').strip()
            password = os.environ.get('FULLMYSQL_DB_PASSWORD','')
            db = os.environ.get('FULLMYSQL_DB_NAME','full_mysql').strip()
            if host and user:
                from urllib.parse import quote
                url = f"mysql://{quote(user,safe='')}:{quote(password,safe='')}@{host}:{port}/{db}"
        cert = os.environ.get('FULLMYSQL_DB_CA_CERT','')
        raw_tokens = os.environ.get('FULLMYSQL_API_TOKENS_JSON','{}')
        try:
            tokens = json.loads(raw_tokens)
        except Exception as exc:
            raise RuntimeError('FULLMYSQL_API_TOKENS_JSON must be valid JSON.') from exc
        if not isinstance(tokens, dict) or not tokens:
            raise RuntimeError('FULLMYSQL_API_TOKENS_JSON must contain at least one device token.')
        tokens = {str(k): str(v) for k,v in tokens.items() if str(v)}
        admins = {x.strip() for x in os.environ.get('FULLMYSQL_ADMIN_DEVICES','HOME-PC').split(',') if x.strip()}
        limit = int(os.environ.get('FULLMYSQL_UPLOAD_LIMIT_MB','96'))
        return cls(url, cert, tokens, admins, limit)

    def db_parts(self):
        if not self.database_url:
            raise RuntimeError('FULLMYSQL_DATABASE_URL is not configured.')
        u = urlsplit(self.database_url)
        if u.scheme not in {'mysql','mysqls'}:
            raise RuntimeError('FULLMYSQL_DATABASE_URL must be a mysql:// URL.')
        return {
            'host': u.hostname or '',
            'port': u.port or 25060,
            'user': unquote(u.username or ''),
            'password': unquote(u.password or ''),
            'database': (u.path or '/full_mysql').lstrip('/') or 'full_mysql',
        }

    def ca_path(self) -> Path | None:
        cert = self.ca_cert_text.strip()
        if not cert:
            return None
        p = Path(tempfile.gettempdir()) / 'fullmysql-v7-ca.crt'
        # Bindable vars may carry escaped newlines depending on deployment path.
        if '\\n' in cert and 'BEGIN CERTIFICATE' in cert:
            cert = cert.replace('\\n','\n')
        p.write_text(cert, encoding='utf-8')
        return p

def get_settings() -> Settings:
    return Settings.load()
