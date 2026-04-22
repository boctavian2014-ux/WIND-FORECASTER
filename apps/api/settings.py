from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """
    Railway/Neon often expose postgres:// or postgresql:// without the SQLAlchemy driver segment.
    For remote hosts, enforce sslmode=require unless already specified.
    """
    raw = url.strip()
    if not raw:
        return raw

    if raw.startswith('postgres://'):
        raw = 'postgresql://' + raw[len('postgres://') :]

    if raw.startswith('postgresql://') and not raw.startswith('postgresql+psycopg://'):
        raw = 'postgresql+psycopg://' + raw[len('postgresql://') :]

    parsed = urlparse(raw)
    host = (parsed.hostname or '').lower()
    if host in ('localhost', '127.0.0.1', ''):
        return raw

    qs = parse_qs(parsed.query, keep_blank_values=True)
    lowered = {k.lower() for k in qs}
    if 'sslmode' not in lowered:
        qs['sslmode'] = ['require']
    new_query = urlencode(qs, doseq=True)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment),
    )


class Settings(BaseSettings):
    app_env: str = 'local'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    database_url: str = 'postgresql+psycopg://windlab:windlab@localhost:5432/windlab'

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    @field_validator('database_url', mode='after')
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        return normalize_database_url(v)


settings = Settings()
