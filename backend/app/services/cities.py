from __future__ import annotations

from typing import Any

from app.core.errors import NotFoundError


def list_cities(db) -> list[dict[str, Any]]:
    return db.rows(
        """SELECT c.city_id, c.name, c.state, c.latitude, c.longitude, c.is_coastal,
                  MIN(o.obs_date) AS first_date, MAX(o.obs_date) AS last_date, COUNT(o.observation_id) AS observations
           FROM city c LEFT JOIN weather_observation o ON o.city_id = c.city_id
           GROUP BY c.city_id ORDER BY c.name"""
    )


def get_city(db, city_id: int) -> dict[str, Any]:
    rows = db.rows("SELECT * FROM city WHERE city_id = :id", {"id": city_id})
    if not rows:
        raise NotFoundError(f"City {city_id} was not found.")
    return rows[0]
