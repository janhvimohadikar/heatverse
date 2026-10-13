from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_executor, settings_dep
from app.core.config import Settings
from app.db.executor import SAExecutor
from app.db.session import get_session
from app.ml.registry import model_status

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session), db: SAExecutor = Depends(get_executor),
           settings: Settings = Depends(settings_dep)):
    """Application health: database connection, historical data, ML mode and external-service configuration."""
    out = {"status": "ok", "database": "ok", "historical_data": None, "model": model_status(settings.model_path),
           "live_weather_enabled": settings.live_weather_enabled, "hospital_lookup_enabled": settings.hospitals_enabled}
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        return {**out, "status": "degraded", "database": f"error: {type(exc).__name__}"}
    try:
        r = db.rows("SELECT COUNT(*) AS n, MIN(obs_date) AS first_date, MAX(obs_date) AS last_date FROM weather_observation")[0]
        out["historical_data"] = {"observations": r["n"], "first_date": r["first_date"], "last_date": r["last_date"]}
    except Exception:
        out["status"] = "degraded"
        out["historical_data"] = "not imported - run scripts/import_excel.py"
    return out
