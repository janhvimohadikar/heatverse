from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_executor, settings_dep
from app.ml.registry import get_predictor, model_status
from app.services import map_service as svc

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/layers")
def layers(settings=Depends(settings_dep)):
    """Map layers, with `available=false` and a reason for any layer the data cannot support."""
    return {"items": svc.list_layers(model_status(settings.model_path))}


@router.get("/dates")
def dates(db=Depends(get_executor)):
    """Date range available for the timeline."""
    return svc.available_dates(db)


@router.get("/risk")
def risk(mode: str = Query("historical", pattern="^(historical|demo_prediction)$"), layer: str = "risk",
         date_: Optional[str] = Query(None, alias="date"), horizon_days: int = Query(1, ge=0, le=14),
         db=Depends(get_executor), settings=Depends(settings_dep)):
    """Per-city values and risk scores for one date (historical) or a labelled demo prediction."""
    predictor = get_predictor(settings.model_path) if mode == "demo_prediction" else None
    return svc.risk_map(db, mode, layer, date_, horizon_days, predictor, date.today())


@router.get("/surface")
def surface(layer: str = "temp_max", date_: Optional[str] = Query(None, alias="date"),
            max_km: float = Query(300, ge=50, le=600), step_deg: float = Query(0.75, ge=0.25, le=2.0), db=Depends(get_executor)):
    """Optional IDW-interpolated surface. Interpolated, not observed."""
    return svc.surface(db, layer, date_, max_km, step_deg)


@router.get("/city/{city_id}")
def city_detail(city_id: int, date_: Optional[str] = Query(None, alias="date"), db=Depends(get_executor)):
    return svc.city_detail(db, city_id, date_)
