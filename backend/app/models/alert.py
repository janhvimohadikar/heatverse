from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class Alert(Base):
    """Administrator-written alert/notice shown to users. Never auto-generated or presented as an official warning."""
    __tablename__ = "alert"
    __table_args__ = (CheckConstraint("level IN ('info', 'advisory', 'warning')", name="ck_alert_level"),)

    alert_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("city.city_id"))  # NULL = applies to all cities
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_on: Mapped[str | None] = mapped_column(String(10))
    ends_on: Mapped[str | None] = mapped_column(String(10))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SafetyResource(Base):
    """Real emergency/hospital contacts entered by an administrator (the app ships with none)."""
    __tablename__ = "safety_resource"

    resource_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("city.city_id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, default="hospital")
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(300))
    source_note: Mapped[str] = mapped_column(String(300), nullable=False)  # where the admin got this information
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user_account.user_id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
