# HEATVERSE — AI-Enabled Climate Intelligence for Heat Wave Monitoring and Early Warning

A DBMS mini-project: a full-stack web application that turns 25 years of daily weather for ten Indian cities
(91,320 records, 2000–2024) into a heat-risk map, climate analytics, personalised risk checks and safety guidance.

> **Honesty box.** The *risk score* is an informational project metric — not an official warning. Predictions are labelled **DEMO**
> because no trained ML model exists yet. Safety text is educational, not medical advice. Live weather and hospital lookup use free
> public APIs and show "unavailable" if they cannot be reached.

## 1. Features

| Area | What you get |
|---|---|
| Landing, login, signup, logout | Local accounts, hashed passwords, JWT sessions |
| Dashboard | Live weather (Open-Meteo), latest dataset snapshot, monthly climatology, admin notices, guidance |
| **Heat-risk map** | City markers · 9 layers (unsupported ones are disabled with a reason) · optional state choropleth · optional IDW heat surface · date timeline with play/pause · A/B date comparison · filters (city, state, risk class, Tmax range) · live category counts · city detail panel with 30-day chart, score explanation and safety tips · full-screen · fit/reset view · accessible location table |
| Climate trends | Annual / monthly / seasonal charts, typical year, city comparison, period comparison, heatwave events (documented definition), data-quality report — all aggregated in SQL |
| Predictions | Per-city, 0–14 days ahead, personalised by profile, explanation, stored history |
| Safety | Heat-illness signs, hydration, vulnerable groups, outdoor work, hospitals from OpenStreetMap (browser location only on button press) |
| Profile | Age, home city, work, activity, emergency contact, theme |
| Admin | Users (activate/promote), dataset & import status, data quality, alerts, curated safety resources, audit log, health, charts |
| UI | Responsive, light/dark mode, navy/orange/red palette |

## 2. Technology stack

Frontend: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Leaflet + React-Leaflet, OpenStreetMap tiles.
Backend: Python, FastAPI, Pydantic v2, SQLAlchemy 2, PyJWT, httpx. Database: SQLite. Tests: pytest.

## 3. Architecture and 4. Database

See [`docs/architecture.md`](docs/architecture.md) (diagram, layering, security, ML hook-up) and [`docs/database-schema.md`](docs/database-schema.md)
(ER diagrams, keys, indexes, column mapping, findings about your dataset).

## 5. About the dataset (inspected, not assumed)

91,320 rows × 22 columns; 10 cities × 9,132 days; 2000-01-01 → 2024-12-31; no empty cells; no duplicate (city, date) pairs; no missing days.
**Humidity, pressure and coordinates are not in the dataset** (humidity/pressure appear only in live weather; coordinates come from `database/city_metadata.csv`).
`ppt_sum` and `rain_sum` are identical. Your Excel file is never modified.

## 6. Map explanation, scoring and limits

See [`docs/map-data-sources.md`](docs/map-data-sources.md). In short: the score (0–100) combines maximum temperature, apparent temperature,
night minimum and consecutive hot days with weights in `backend/app/core/heat_config.py`; categories are Low 0–24, Moderate 25–49, High 50–74, Extreme 75–100.
Heatwave events use a simplified IMD-style rule (≥40 °C, or ≥37 °C on the coast, **and** ≥4.5 °C above the monthly normal or ≥45 °C, for ≥2 days).

## 7. Folder structure

```
HEATVERSE/
├── frontend/            React app  (src/features/heat-risk-map = the map)
├── backend/
│   ├── app/             api · core · db · models · schemas · services · ml · main.py
│   ├── scripts/         import_excel.py · create_admin.py
│   └── tests/
├── database/            source/DBMS_Database.xlsx · city_metadata.csv · (generated) heatverse.db
├── docs/                architecture.md · database-schema.md · map-data-sources.md
├── README.md  LICENSE  .gitignore  .env.example
```

## 8. Setup on Windows (copy-paste into PowerShell)

### 8.1 Install the tools once

* **Python 3.11 or 3.12** from https://www.python.org/downloads/ — tick **"Add python.exe to PATH"** in the installer.
* **Node.js LTS** from https://nodejs.org/ . **Git** from https://git-scm.com/ .
* Close and reopen PowerShell, then check: `py --version`, `node --version`, `git --version`.

### 8.2 Backend

```powershell
cd path\to\HEATVERSE\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```
If PowerShell says scripts are disabled, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again. You should see `(.venv)` in the prompt.

```powershell
pip install -r requirements-dev.txt
copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Open `backend\.env` in Notepad, replace `change-me` after `SECRET_KEY=` with the long random text printed above, and save.

### 8.3 Import your database

```powershell
python scripts\import_excel.py --excel ..\database\source\DBMS_Database.xlsx
```
Expected ending: `rows_read: 91320`, `rows_inserted: 91320`. (Takes about a minute.) This creates `database\heatverse.db`.
Add `--replace` to rebuild the weather tables later.

### 8.4 Create the first administrator (optional, needed for the Admin page)

```powershell
python scripts\create_admin.py
```
Type an email and a password when asked (the password is hidden and is not saved anywhere except as a hash in the database).

### 8.5 Start the backend

```powershell
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs (interactive API documentation) and http://127.0.0.1:8000/api/health. Leave this window running.

### 8.6 Frontend (second PowerShell window)

```powershell
cd path\to\HEATVERSE\frontend
npm install
npm run dev
```
Open http://localhost:5173 . Sign up, or log in with the admin account.

### 8.7 Run the tests

```powershell
cd path\to\HEATVERSE\backend
.\.venv\Scripts\Activate.ps1
pytest
```
Frontend build check: `cd frontend; npm run build`.

## 9. Configuration

| Setting (`backend/.env`) | Meaning |
|---|---|
| `SECRET_KEY` | Signs login tokens. Required in practice. |
| `CORS_ORIGINS` | Allowed frontend addresses (default: localhost:5173) |
| `LIVE_WEATHER_ENABLED` | `true` uses Open-Meteo (no key). `false` turns live weather off. |
| `HOSPITALS_ENABLED` | `true` uses OpenStreetMap Overpass (no key) |
| `MODEL_PATH` | Optional trained model file (see `docs/architecture.md`) |
| `DATABASE_PATH` | Override database location |

No API keys are needed. If you later switch to a keyed weather/places provider, add its key to `backend/.env` only — never to frontend code.

## 10. Main API endpoints (full list at `/docs`)

`GET /api/health` · `GET /api/cities` · `GET /api/weather/current` · `GET /api/weather/historical` · `GET /api/analytics/{temperature-trends|climatology|city-comparison|period-comparison|heatwave-events|data-quality|dashboard-summary}` ·
`GET /api/map/{layers|dates|risk|surface|city/{id}}` · `POST /api/predictions` · `GET|DELETE /api/predictions/history` · `GET /api/predictions/model-status` ·
`GET /api/hospitals/nearby` · `GET /api/safety/guidance` · `GET /api/alerts/active` · `POST /api/auth/{signup|login|logout}` · `GET /api/auth/me` · `GET|PUT /api/profile` · `/api/admin/*` (admin only).

## 11. Upload to GitHub

1. Create an empty repository on https://github.com/new (no README, no .gitignore).
2. In PowerShell:
```powershell
cd path\to\HEATVERSE
git init
git add .
git status
```
Check the list: there must be **no** `.env`, `.venv`, `node_modules` or `heatverse.db`.
```powershell
git commit -m "HEATVERSE: initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```
* **Include:** all source, `database/city_metadata.csv`, `frontend/package-lock.json` (created by `npm install`), and `database/source/DBMS_Database.xlsx` if you may share the data.
* **Keep private:** `backend/.env`, `database/heatverse.db` (contains accounts), any trained-model file you do not want to share.
* Also run `pytest tests/test_repo_hygiene.py` before pushing — it scans for leaked secrets.

## 12. Verification status — read this before submitting

The project was generated in an environment **without internet access**, so packages could not be installed there. What was and was not verified:

| Item | Status |
|---|---|
| Excel import (91,320/91,320 rows, values compared with the Excel file) | ✅ Run and verified |
| SQL analytics, heatwave detection, scoring, map data, IDW surface, demo predictions, data-quality checks against your real data | ✅ Run; 27 tests pass (`test_core_logic`, `test_data_services`, `test_repo_hygiene`) |
| Password hashing, JWT creation/validation | ✅ Run |
| All Python files parse; all 33 TypeScript/TSX files parse | ✅ Syntax only |
| **FastAPI app start-up, HTTP routes, SQLAlchemy models, auth/admin endpoints (`tests/test_api.py`)** | ⚠️ **Written but never executed** (FastAPI/SQLAlchemy not installable there) |
| **`npm install`, `npm run build`, TypeScript type-check, the map in a browser (desktop/mobile), frontend↔backend calls** | ⚠️ **Never executed** |
| Live weather (Open-Meteo) and hospitals (Overpass) | ⚠️ Not called — no network. Failures are handled and shown as "unavailable". |
| Real ML model | ❌ None supplied; adapter untested |
| `package-lock.json` | ❌ Not generated (needs network). Created by your first `npm install`. |

**Expect to fix a few small issues on first run** (a typing error or a wrong import is possible in code that has never been compiled). Work through it in this order:
`pytest` → `uvicorn` → open `/docs` → `npm run build` → open the site. Send me any error text and it can be fixed quickly.

## 13. Known limitations

* Historical data ends on 2024-12-31. "Latest snapshot" is the latest dataset day, **not today**; only the live-weather card shows current conditions.
* Only 10 cities, so state choropleth and the interpolated surface are coarse. Boundary GeoJSON is not bundled (`docs/map-data-sources.md`).
* City coordinates were entered by hand and must be verified.
* Demo predictions are a seasonal average; they cannot anticipate an actual heatwave.
* Score weights are project choices, not medically calibrated. Heatwave rule is simplified IMD-style, with in-sample normals.
* No login rate-limiting; no server-side logout; JWT in `localStorage`.
* OSM tiles are for light use only.

## 14. Troubleshooting

| Problem | Fix |
|---|---|
| `py` not recognised | Reinstall Python with "Add to PATH", reopen PowerShell |
| Activate.ps1 blocked | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `/api/health` says "not imported" | Run step 8.3 |
| Frontend shows "Cannot reach the HEATVERSE API" | Start the backend (8.5); it must be on port 8000 |
| Port 8000 busy | `uvicorn app.main:app --reload --port 8001` and change the proxy target in `frontend/vite.config.ts` |
| Map is blank grey | Check internet access (tiles are loaded online) |
| "State boundary file not installed" | Expected until you add the GeoJSON (see docs) |
| Everyone logged out after restart | `SECRET_KEY` is not set in `backend\.env` |
