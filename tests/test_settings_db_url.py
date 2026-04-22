from apps.api.settings import Settings, normalize_database_url


def test_normalize_postgres_scheme():
    out = normalize_database_url('postgres://user:pass@db.example.com:5432/mydb')
    assert out.startswith('postgresql+psycopg://')
    assert 'sslmode=require' in out


def test_normalize_postgresql_adds_psycopg_and_ssl():
    out = normalize_database_url('postgresql://user:pass@db.example.com:5432/mydb')
    assert out.startswith('postgresql+psycopg://')
    assert 'sslmode=require' in out


def test_localhost_untouched():
    out = normalize_database_url('postgresql+psycopg://windlab:windlab@localhost:5432/windlab')
    assert out == 'postgresql+psycopg://windlab:windlab@localhost:5432/windlab'


def test_settings_reads_database_url_env(monkeypatch):
    monkeypatch.setenv(
        'DATABASE_URL',
        'postgresql://u:p@remote.host/db',
    )
    s = Settings()
    assert s.database_url.startswith('postgresql+psycopg://')
    assert 'sslmode=require' in s.database_url
