from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProfileIn(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    home_city_id: Optional[int] = None
    occupation: Optional[str] = Field(default=None, max_length=120)
    is_outdoor_worker: bool = False
    activity_level: Literal["low", "moderate", "high"] = "low"
    emergency_contact: Optional[str] = Field(default=None, max_length=200)
    theme: Literal["light", "dark", "system"] = "system"


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    email: Optional[str] = None
