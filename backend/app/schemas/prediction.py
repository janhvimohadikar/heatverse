from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    city_id: int = Field(ge=1)
    horizon_days: int = Field(default=1, ge=0, le=14, description="Days ahead of today (0-14)")
