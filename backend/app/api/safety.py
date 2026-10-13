from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_executor, settings_dep
from app.db.session import get_session
from app.models import Alert, SafetyResource
from app.services import cities as city_svc, hospitals, safety_content

router = APIRouter(prefix="/api", tags=["safety"])


@router.get("/safety/guidance")
def guidance():
    """Static educational heat-safety content."""
    return safety_content.full_guidance()


@router.get("/alerts/active")
def active_alerts(city_id: Optional[int] = None, session: Session = Depends(get_session)):
    """Administrator-written notices that are active today. These are project notices, not official warnings."""
    today = date.today().isoformat()
    q = select(Alert).where(Alert.is_active.is_(True))
    if city_id is not None:
        q = q.where(or_(Alert.city_id.is_(None), Alert.city_id == city_id))
    rows = [a for a in session.scalars(q.order_by(Alert.created_at.desc()))
            if (not a.starts_on or a.starts_on <= today) and (not a.ends_on or a.ends_on >= today)]
    return {"items": [{"alert_id": a.alert_id, "city_id": a.city_id, "level": a.level, "title": a.title,
                       "message": a.message, "starts_on": a.starts_on, "ends_on": a.ends_on} for a in rows],
            "note": "Notices entered by the HEATVERSE administrator. Not an official government warning."}


@router.get("/hospitals/nearby")
def nearby_hospitals(city_id: Optional[int] = None, lat: Optional[float] = Query(None, ge=-90, le=90),
                     lon: Optional[float] = Query(None, ge=-180, le=180), radius_km: float = Query(10, ge=1, le=50),
                     db=Depends(get_executor), session: Session = Depends(get_session), settings=Depends(settings_dep)):
    """Nearby hospitals: live OpenStreetMap lookup + any administrator-curated resources for the city."""
    curated, origin = [], None
    if lat is not None and lon is not None:
        origin = {"latitude": lat, "longitude": lon, "basis": "browser/device location"}
    elif city_id is not None:
        city = city_svc.get_city(db, city_id)
        if city["latitude"] is None:
            raise HTTPException(422, "This city has no coordinates.")
        origin = {"latitude": city["latitude"], "longitude": city["longitude"], "basis": f"{city['name']} city centre"}
    else:
        raise HTTPException(422, "Provide either city_id or both lat and lon.")
    if city_id is not None:
        curated = [{"resource_id": r.resource_id, "name": r.name, "resource_type": r.resource_type, "phone": r.phone,
                    "address": r.address, "source_note": r.source_note, "source": "Entered by administrator"}
                   for r in session.scalars(select(SafetyResource).where(or_(SafetyResource.city_id == city_id,
                                                                            SafetyResource.city_id.is_(None))))]
    osm = hospitals.fetch_nearby(settings, origin["latitude"], origin["longitude"], radius_km)
    return {"origin": origin, "radius_km": radius_km, "osm": osm, "curated": curated,
            "emergency_note": safety_content.DISCLAIMER}
