# Wind Price Lab

API de research pentru **direcția prețului** la nivel de **zonă de piață** (hub), cu rezoluție **15 minute**, integrare **features** (preț + vânt agregat) și **backtest** comparativ (persistence vs model logistic). Stack: **FastAPI**, **PostgreSQL**, **SQLAlchemy**, **scikit-learn**.

Repository: [github.com/boctavian2014-ux/WIND-FORECASTER](https://github.com/boctavian2014-ux/WIND-FORECASTER)

---

## Ce face proiectul

- **Modele**: regresie logistică multinomială pe clase `{-1, 0, 1}` (down / flat / up), cu split temporal train/test la antrenare și salvare artefacte `joblib` sub `artifacts/models/`.
- **Predicții**: scriere în `model_predictions_15m` (probabilități, `confidence`, `no_trade`).
- **Backtest**:
  - **v1** — `POST /research/backtest/compare`: compară baseline **persistence** (semn din `return_15m`) cu predicțiile persistate, pe **aceleași** `target_time`-uri.
  - **v2** — `POST /research/backtest/compare-v2`: runner de experiment (policy, mod evaluare), metrici extinse (balanced accuracy, macro F1, profit factor, etc.) și opțional persistare în `ml_experiments` / `ml_experiment_metrics` / `ml_experiment_artifacts` (după migrarea SQL).

Health check fără DB: `GET /health`.

---

## Cerințe

| Componentă | Versiune / notă |
|-------------|------------------|
| Python | 3.11+ |
| PostgreSQL | accesibil prin `DATABASE_URL` |
| Dependențe Python | vezi [pyproject.toml](pyproject.toml) |

**Notă:** codul presupune tabele precum `features_15m`, `labels_15m`, `intraday_prices_15m`, `model_predictions_15m` (vezi secțiunea [Baza de date](#bază-de-date)). În repo există migrarea experiment tracking v2; **schema inițială completă** (CREATE TABLE pentru fluxul tău) trebuie să fie aplicată separat dacă nu o ai deja.

---

## Structură repository

```
apps/api/          # FastAPI: main, routers, schemas, settings, deps
services/          # Logica: backtest, models, features, research, experiments
db/sql/            # Migrări SQL (ex. experiment tracking v2)
docs/              # Ghid agent Railway + SQL (Partea A / B)
tests/             # Pytest
Dockerfile         # Imagine pentru producție / Railway
```

---

## Variabile de mediu

Copiază [.env.example](.env.example) în `.env` și completează.

| Variabilă | Rol |
|-----------|-----|
| `DATABASE_URL` | Conexiune Postgres. Acceptă `postgres://` sau `postgresql://`; aplicația normalizează la `postgresql+psycopg://` și adaugă `sslmode=require` pentru host non-local ([apps/api/settings.py](apps/api/settings.py)). |
| `OPENWEATHER_API_KEY` | Opțional, pentru colectori weather (dacă îi expui în API). |

---

## Rulare locală

### Instalare

```bash
cd "WIND FORECASTER"
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -e ".[dev]"
```

### Teste

```bash
set PYTHONPATH=.                 # Windows
# export PYTHONPATH=.           # Linux / macOS
pytest
```

### Pornire API

**Variantă recomandată (din rădăcina repo-ului):**

```bash
set PYTHONPATH=.
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Variantă alternativă:**

```bash
cd apps/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Documentație interactivă: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Bază de date

### Ordinea recomandată (Partea B)

1. Aplică **schema inițială** care creează tabelele folosite de API (minim: `features_15m`, `labels_15m`, `intraday_prices_15m`, `model_predictions_15m`, plus zone / weather / prețuri, conform setup-ului tău).
2. Aplică [db/sql/001_experiment_tracking_v2.sql](db/sql/001_experiment_tracking_v2.sql) — adaugă tabelele de experiment tracking și **ALTER** pe `model_predictions_15m` / `labels_15m` (trebuie să existe deja).
3. Rulează **seed-uri** dacă le ai, după ce tabelele părinte există.

Detaliu pas cu pas (inclusiv pentru **Railway**): [docs/AGENT_RAILWAY_AND_SQL.md](docs/AGENT_RAILWAY_AND_SQL.md).

### Tabelul `features_15m`

Dataset-ul pentru train/predict citește coloanele definite în [services/models/logreg_model.py](services/models/logreg_model.py) (`FEATURE_COLUMNS`) din tabelul `features_15m`.

---

## API — endpoint-uri principale

Prefixele de mai jos sunt relative la baza URL-ului serviciului (ex. `https://<domeniu>`).

| Metodă | Cale | Scurtă descriere |
|--------|------|-------------------|
| GET | `/health` | Verificare serviciu (fără DB). |
| GET | `/docs` | OpenAPI (Swagger UI). |
| POST | `/models/train-baseline` | Antrenare logistic regression cu split temporal; salvează model; returnează `model_version`. |
| POST | `/models/predict` | Predicții + UPSERT în `model_predictions_15m`. |
| POST | `/research/backtest/compare` | Backtest v1: persistence vs model persistat, aceleași timestamp-uri. |
| POST | `/research/backtest/compare-v2` | Backtest v2 + metrici extinse; opțional persistă experiment (necesită tabele `ml_*` din migrare). |

**Exemplu `POST /models/train-baseline` (corp JSON):**

```json
{
  "zone_id": "DE_LU",
  "start": "2024-01-01T00:00:00Z",
  "end": "2024-03-01T00:00:00Z",
  "model_name": "logreg_direction",
  "test_holdout_ratio": 0.2,
  "confidence_threshold": 0.58
}
```

**Exemplu `POST /models/predict`:**

```json
{
  "zone_id": "DE_LU",
  "start": "2024-02-01T00:00:00Z",
  "end": "2024-02-15T00:00:00Z",
  "model_name": "logreg_direction",
  "model_version": "20260122T120000Z",
  "confidence_threshold": 0.58
}
```

**Exemplu `POST /research/backtest/compare`:**

```json
{
  "zone_id": "DE_LU",
  "start": "2024-02-01T00:00:00Z",
  "end": "2024-02-15T00:00:00Z",
  "model_name": "logreg_direction",
  "model_version": "20260122T120000Z",
  "confidence_threshold": 0.58
}
```

Parametrii completi pentru **compare-v2** sunt descriși în schema Pydantic [apps/api/schemas/research_v2.py](apps/api/schemas/research_v2.py); în Swagger le vezi direct sub `/docs`.

---

## Cum îl folosești (flux research tipic)

1. **Date în DB**: zone, puncte meteo, forecasturi, prețuri 15m, `features_15m`, `labels_15m` (conform pipeline-ului tău de ETL; unele piese pot fi încă stub-uri în alte branch-uri).
2. **`POST /models/train-baseline`** pe un interval cu etichete și features — notezi `model_version` din răspuns.
3. **`POST /models/predict`** cu același `model_name` / `model_version` pe fereastra dorită — umpli `model_predictions_15m`.
4. **`POST /research/backtest/compare`** (sau **compare-v2**) pentru măsurători și comparație cu persistence.

Fără pașii 1–2, train/predict returnează 404 sau erori SQL.

---

## Docker și Railway

- **Build local:** `docker build -t windlab-api .`
- **Start în container:** Railway (sau Docker) setează `PORT`; imaginea pornește `uvicorn apps.api.main:app` pe `0.0.0.0:${PORT}` ([Dockerfile](Dockerfile)).

**Checklist deploy Railway** (servicii, variabile, domeniu, ordine SQL): vezi secțiunea **Railway** de mai jos și [docs/AGENT_RAILWAY_AND_SQL.md](docs/AGENT_RAILWAY_AND_SQL.md).

### Railway (rezumat)

1. Proiect Railway + serviciu **PostgreSQL** + serviciu **API** din repo-ul GitHub `boctavian2014-ux/WIND-FORECASTER`, branch `main`, **root** `.` (unde e `Dockerfile`).
2. Pe API: **`DATABASE_URL`** = referință la Postgres; fără Start Command custom; fără `PORT` setat manual (Railway injectează `PORT`).
3. **Generate Domain**; verifici `GET /health` și `/docs`.
4. Aplici **SQL** pe Postgres (schema de bază, apoi `001_experiment_tracking_v2.sql`) — vezi [docs/AGENT_RAILWAY_AND_SQL.md](docs/AGENT_RAILWAY_AND_SQL.md) Partea B.

**TimescaleDB:** Postgres-ul standard din Railway este **vanilla**; acest repo nu presupune extensia Timescale pentru migrarea `001_experiment_tracking_v2.sql`. Hypertables rămân opționale pe alt host.

---

## Limitări și așteptări realiste

- **Prețuri bootstrap** (Ember / proiecții): utile pentru infrastructură și teste de join; nu înlocuiesc feed-ul intraday EPEX pentru evaluări de trading reale.
- **Compare v2 + persist**: necesită tabelele `ml_experiments`, `ml_experiment_metrics`, `ml_experiment_artifacts` din migrare; dacă lipesc, vei primi 503 cu mesaj explicativ.

---

## Dezvoltare

- Lint / stil: configurare de bază **Ruff** în [pyproject.toml](pyproject.toml).
- Teste: `pytest` din rădăcină, cu `PYTHONPATH=.` (vezi [pytest.ini](pytest.ini)).

---

## Licență

Dacă adaugi o licență în repo (ex. MIT), menționeaz-o aici; în absența unui fișier `LICENSE`, drepturile rămân la autor.
