from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_executor
from app.core.errors import ValidationFailed
from app.services import analytics as svc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/temperature-trends")
def temperature_trends(city_id: int = Query(..., ge=1), granularity: str = Query("annual", pattern="^(annual|monthly|seasonal)$"),
                       start: Optional[str] = None, end: Optional[str] = None, db=Depends(get_executor)):
    return svc.temperature_trends(db, city_id, granularity, start, end)


@router.get("/climatology")
def climatology(city_id: int = Query(..., ge=1), db=Depends(get_executor)):
    return svc.climatology(db, city_id)


@router.get("/dashboard-summary")
def dashboard_summary(city_id: int = Query(..., ge=1), month: Optional[int] = Query(None, ge=1, le=12), db=Depends(get_executor)):
    return svc.dashboard_summary(db, city_id, month)


@router.get("/city-comparison")
def city_comparison(city_ids: str = Query(..., description="Comma-separated city ids, e.g. 1,4,9"),
                    metric: str = "temp_max_c", start: Optional[str] = None, end: Optional[str] = None, db=Depends(get_executor)):
    try:
        ids = [int(x) for x in city_ids.split(",") if x.strip()]
    except ValueError:
        raise ValidationFailed("city_ids must be a comma-separated list of integers.")
    return svc.city_comparison(db, ids, metric, start, end)


@router.get("/period-comparison")
def period_comparison(city_id: int = Query(..., ge=1), a_start: str = Query(...), a_end: str = Query(...), b_start: str = Query(...), b_end: str = Query(...),
                      db=Depends(get_executor)):
    return svc.period_comparison(db, city_id, a_start, a_end, b_start, b_end)


@router.get("/heatwave-events")
def heatwave_events(city_id: int = Query(..., ge=1), start: Optional[str] = None, end: Optional[str] = None, db=Depends(get_executor)):
    return svc.heatwave_events(db, city_id, start, end)


@router.get("/data-quality")
def data_quality(db=Depends(get_executor)):
    return svc.data_quality(db)
