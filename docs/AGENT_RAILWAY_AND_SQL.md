# Listă pentru agent (Railway) + ce faci tu (SQL)

## Partea A — Dă acest bloc unui agent (configurare Railway, fără SQL în UI)

**Obiectiv:** proiect Railway cu Postgres + API din acest repo, variabile corecte, domeniu public, deploy verde; **nu** rula migrări SQL în numele utilizatorului (utilizatorul le rulează el).

1. Deschide proiectul Railway utilizatorului (ex. [proiect](https://railway.com/project/08f007ae-4d91-4a3d-b546-9fc52528bf37)) sau creează un proiect nou.
2. Adaugă serviciul **PostgreSQL** (template Postgres). Așteaptă până e „Ready”.
3. Adaugă serviciul **API**: **New → GitHub Repo**, selectează repo-ul **WIND FORECASTER**. Setează **Root Directory** la rădăcina repo-ului unde există [Dockerfile](../Dockerfile) (același nivel cu `apps/`, `services/`, `db/`).
4. **Nu** seta un custom **Start Command** pe API: [Dockerfile](../Dockerfile) pornește deja `uvicorn apps.api.main:app` pe `${PORT:-8000}`.
5. **Nu** defini manual `PORT` pe API (Railway îl injectează). Dacă există o variabilă `PORT` conflictuală, elimin-o de pe serviciul API.
6. Pe serviciul **API**, în **Variables**: adaugă **`DATABASE_URL`** ca **Variable Reference** către serviciul Postgres (ex. referință la `DATABASE_URL` / connection string expus de plugin). Nu modifica conținutul string-ului în afara UI-ului Railway; aplicația normalizează în [apps/api/settings.py](../apps/api/settings.py).
7. Opțional: dacă utilizatorul folosește OpenWeather, adaugă **`OPENWEATHER_API_KEY`** pe API (valoare secretă), vezi [.env.example](../.env.example).
8. Pe serviciul API: **Settings → Networking → Generate Domain** (sau atașează domeniu custom). Notează URL-ul final `https://…`.
9. Declanșează **Deploy** (sau așteaptă redeploy după variabile). Verifică **Build logs** și **Deploy logs** fără erori.
10. Verificare automată/manuală: `GET https://<domeniu>/health` trebuie să returneze `{"status":"ok"}` ([apps/api/main.py](../apps/api/main.py)). Dacă nu, citește logurile API (binding port, import errors, crash la startup).
11. Confirmă în UI că serviciul Postgres și API sunt în același proiect și că API are acces la variabila referită (fără placeholder gol).
12. **Stop:** nu rula scripturi SQL în Query editor în numele utilizatorului; utilizatorul le aplică el (Partea B).

---

## Partea B — Tu (utilizator): ce SQL rulezi și în ce ordine

**Atenție:** [db/sql/001_experiment_tracking_v2.sql](../db/sql/001_experiment_tracking_v2.sql) face `ALTER TABLE model_predictions_15m` și `ALTER TABLE labels_15m`. Dacă aceste tabele **nu există**, migrarea va eșua. În repo există **doar** acest fișier sub `db/sql/`; schema de bază (zone, prețuri, labels, predictions, features etc.) trebuie să vină din **alt** SQL pe care îl ai local (ex. `001_init.sql` vechi).

Ordine recomandată:

1. Rulezi **schema inițială completă** care creează cel puțin: `labels_15m`, `model_predictions_15m`, `intraday_prices_15m`, `market_zones`, `weather_points`, `features_15m`, etc. (conform setup-ului tău real). Fără acest pas, API-urile `/research/...` și `/models/...` vor da erori la DB.
2. Abia apoi rulezi **[db/sql/001_experiment_tracking_v2.sql](../db/sql/001_experiment_tracking_v2.sql)** în același Postgres (Query tab sau `psql` cu `DATABASE_URL` din Railway).
3. Dacă ai seed-uri (zone pilot), le rulezi **după** tabelele părinte există.

**Notă TimescaleDB:** Postgres Railway e vanilla; `001` nu cere `timescaledb`, dar nici nu îl instalează. Hypertables rămân opționale pe alt host.

---

## Fișiere de referință în repo

- Checklist detaliat: [README.md](../README.md) secțiunea **Railway (checklist)**.
- Docker: [Dockerfile](../Dockerfile).
- Conexiune: [apps/api/settings.py](../apps/api/settings.py).
