from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[Literal["user", "admin"]] = None


class AlertIn(BaseModel):
    city_id: Optional[int] = None
    level: Literal["info", "advisory", "warning"] = "info"
    title: str = Field(min_length=3, max_length=150)
    message: str = Field(min_length=3, max_length=2000)
    is_active: bool = True
    starts_on: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    ends_on: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class SafetyResourceIn(BaseModel):
    city_id: Optional[int] = None
    name: str = Field(min_length=2, max_length=200)
    resource_type: str = Field(default="hospital", max_length=50)
    phone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=300)
    source_note: str = Field(min_length=3, max_length=300, description="Where this information came from")
