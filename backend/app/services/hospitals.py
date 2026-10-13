"""Nearby hospitals from OpenStreetMap (Overpass API) plus admin-curated resources. Nothing is invented."""
from __future__ import annotations

from typing import Any

from app.core import cache
from app.services.geo import haversine_km

ATTRIBUTION = "Hospital data (c) OpenStreetMap contributors (Overpass API). It may be incomplete or out of date - verify before relying on it."


def fetch_nearby(settings, lat: float, lon: float, radius_km: float, limit: int = 15) -> dict[str, Any]:
    if not settings.hospitals_enabled:
        return {"status": "disabled", "reason": "Hospital search is disabled (HOSPITALS_ENABLED=false).", "items": []}
    radius_m = int(radius_km * 1000)
    query = (f'[out:json][timeout:20];(node["amenity"="hospital"](around:{radius_m},{lat},{lon});'
             f'way["amenity"="hospital"](around:{radius_m},{lat},{lon}););out center 60;')

    def call() -> dict[str, Any]:
        import httpx

        try:
            r = httpx.post(settings.overpass_url, data={"data": query}, timeout=max(settings.external_timeout_seconds, 20))
            r.raise_for_status()
            items = []
            for el in r.json().get("elements", []):
                tags = el.get("tags", {})
                plat = el.get("lat") or (el.get("center") or {}).get("lat")
                plon = el.get("lon") or (el.get("center") or {}).get("lon")
                if plat is None or plon is None:
                    continue
                address = ", ".join(x for x in [tags.get("addr:housenumber"), tags.get("addr:street"),
                                                tags.get("addr:suburb"), tags.get("addr:city")] if x) or None
                items.append({
                    "name": tags.get("name") or "Hospital (name not recorded in OpenStreetMap)",
                    "phone": tags.get("phone") or tags.get("contact:phone"), "address": address,
                    "emergency": tags.get("emergency"), "latitude": plat, "longitude": plon,
                    "distance_km": round(haversine_km(lat, lon, plat, plon), 2),
                    "source": "OpenStreetMap", "osm_id": f'{el.get("type")}/{el.get("id")}',
                })
            items.sort(key=lambda x: x["distance_km"])
            return {"status": "ok", "attribution": ATTRIBUTION, "items": items[:limit]}
        except Exception as exc:
            return {"status": "unavailable", "reason": f"Hospital lookup service could not be reached ({type(exc).__name__}).", "items": []}

    key = f"hosp:{round(lat, 2)}:{round(lon, 2)}:{radius_m}:{limit}"
    result = cache.cached(key, 1800, call)
    if result["status"] != "ok":
        cache._store.pop(key, None)
    return result
