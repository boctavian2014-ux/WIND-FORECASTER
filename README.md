# Wind Price Lab

Research API for zone-level wind/price features, models, and backtests.

## Run locally

```bash
pip install -e ".[dev]"
pytest
# Option A (from repo root)
set PYTHONPATH=.
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
# Option B (from apps/api)
cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Railway (checklist)

**Pentru un agent (copy-paste) + pașii SQL pe care îi faci tu:** vezi [docs/AGENT_RAILWAY_AND_SQL.md](docs/AGENT_RAILWAY_AND_SQL.md).

Proiect exemplu: [Railway project](https://railway.com/project/08f007ae-4d91-4a3d-b546-9fc52528bf37). Cod: [Dockerfile](Dockerfile), [apps/api/settings.py](apps/api/settings.py), [.env.example](.env.example).

### 1. Proiect și servicii

1. Deschide proiectul Railway (link de mai sus sau creează unul nou).
2. Adaugă serviciul **PostgreSQL** (template „Postgres”).
3. Adaugă serviciul **API**: **New → GitHub Repo** (sau Empty service + conectare repo). **Root directory** = rădăcina repo-ului unde există [Dockerfile](Dockerfile) (nu un subfolder fără Dockerfile).

### 2. Build și start

4. Railway folosește [Dockerfile](Dockerfile) de la root; **nu** seta un start command custom în UI: imaginea rulează `uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
5. Railway injectează **`PORT`** automat pe serviciul web; nu îl suprascrie decât dacă ai un motiv clar.

### 3. Variabile de mediu (serviciul API)

6. **`DATABASE_URL`**: în **Variables** la serviciul API, folosește **Variable Reference** către serviciul Postgres (variabila `DATABASE_URL` sau echivalentul din tab-ul Postgres). Aplicația acceptă `postgres://` / `postgresql://` și normalizează la `postgresql+psycopg://` și adaugă `sslmode=require` pentru host non-local ([apps/api/settings.py](apps/api/settings.py)).
7. **Opțional**: `OPENWEATHER_API_KEY` dacă folosești colectori weather (vezi [.env.example](.env.example)).
8. Alte variabile doar dacă sunt folosite explicit în cod; nu sunt obligatorii pentru boot-ul API.

### 4. Rețea și acces

9. La serviciul API: **Settings → Networking → Generate Domain** (sau domeniu custom) pentru `https://….railway.app`.
10. Verificare: `GET https://<domeniu>/health` → `{"status":"ok"}` ([apps/api/main.py](apps/api/main.py)).

### 5. Baza de date (migrări)

11. Postgres-ul din Railway **nu** creează tabelele aplicației automat; rulezi SQL pe instanță (Query tab la Postgres, sau `psql` cu connection string din UI).
12. În acest repo, sub `db/sql/` există cel puțin [`db/sql/001_experiment_tracking_v2.sql`](db/sql/001_experiment_tracking_v2.sql) — aplică-l pe Railway. Dacă ai și alte fișiere SQL locale (zone, seeds, schema inițială), aplică-le **în ordinea corectă** înainte de endpoint-uri care depind de ele.
13. **TimescaleDB**: Postgres-ul standard din Railway este **vanilla**; extensia `timescaledb` nu este asumată. Pentru hypertables Timescale folosește Timescale Cloud sau alt host care expune extensia.

### 6. Ordine recomandată la primul deploy

14. Pornește **Postgres** și așteaptă provisioning.
15. Conectează **`DATABASE_URL`** la API (referință din Postgres).
16. Deploy **API**; verifică build logs, apoi `/health`.
17. Rulează **migrările SQL** pe Postgres.
18. Testează endpoint-uri care lovesc DB (ex. `/docs`, `/research/...`) doar după ce schema există.
