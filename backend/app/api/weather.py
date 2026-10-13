from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_executor, settings_dep
from app.services import cities as city_svc, historical, live_weather

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/current")
def current_weather(city_id: int = Query(..., ge=1), db=Depends(get_executor), settings=Depends(settings_dep)):
    """LIVE conditions from Open-Meteo. Never returns old historical rows as 'current'."""
    city = city_svc.get_city(db, city_id)
    return live_weather.fetch_current(settings, city)


@router.get("/historical")
def historical_weather(city_id: int = Query(..., ge=1), start: Optional[str] = None, end: Optional[str] = None,
                       page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db=Depends(get_executor)):
    """Paginated daily observations from the supplied historical dataset."""
    city_svc.get_city(db, city_id)
    return historical.get_observations(db, city_id, start, end, page, page_size)
