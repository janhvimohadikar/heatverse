# HEATVERSE backend

FastAPI + SQLAlchemy + Pydantic. See the root `README.md` for the full Windows setup.

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env          # then edit SECRET_KEY
python scripts\import_excel.py --excel ..\database\source\DBMS_Database.xlsx
python scripts\create_admin.py
uvicorn app.main:app --reload
```

* API docs (Swagger): http://127.0.0.1:8000/docs
* Tests: `pytest`
* Folders: `app/api` (routes) · `app/core` (config, scoring, security) · `app/db` (engine, executor) · `app/models` (ORM tables) · `app/schemas` (Pydantic) · `app/services` (logic) · `app/ml` (predictors) · `scripts/` (import, admin creation) · `tests/`
