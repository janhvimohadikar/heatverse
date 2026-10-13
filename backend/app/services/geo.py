"""Geographic helpers: distance and inverse-distance-weighted (IDW) interpolation."""
from __future__ import annotations

import math
from typing import Sequence

EARTH_RADIUS_KM = 6371.0088

# Bounding box that covers mainland India (used only to limit the interpolation grid).
INDIA_BBOX = {"south": 6.5, "north": 35.5, "west": 68.0, "east": 97.5}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def idw_grid(points: Sequence[tuple[float, float, float]], step_deg: float = 0.75, max_km: float = 300.0,
             power: float = 2.0, bbox: dict | None = None) -> list[dict]:
    """
    Inverse-distance-weighted interpolation of (lat, lon, value) points onto a regular grid.

    * Only grid cells within `max_km` of at least one real point are returned (no extrapolation over
      areas that have no nearby data).
    * Only points within `max_km` contribute to a cell.
    * The output is a MODEL OF A SURFACE, not new measurements.
    """
    bbox = bbox or INDIA_BBOX
    cells = []
    lat = bbox["south"]
    while lat <= bbox["north"] + 1e-9:
        lon = bbox["west"]
        while lon <= bbox["east"] + 1e-9:
            num = den = 0.0
            exact = None
            near = False
            for plat, plon, val in points:
                d = haversine_km(lat, lon, plat, plon)
                if d > max_km:
                    continue
                near = True
                if d < 1e-6:
                    exact = val
                    break
                w = 1.0 / (d ** power)
                num += w * val
                den += w
            if near:
                value = exact if exact is not None else num / den
                cells.append({"lat": round(lat, 4), "lon": round(lon, 4), "value": round(value, 2)})
            lon += step_deg
        lat += step_deg
    return cells
