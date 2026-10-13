from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "user_account"
    __table_args__ = (CheckConstraint("role IN ('user', 'admin')", name="ck_user_role"),)

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(10), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profile"
    __table_args__ = (
        CheckConstraint("age IS NULL OR (age >= 0 AND age <= 120)", name="ck_profile_age"),
        CheckConstraint("activity_level IN ('low', 'moderate', 'high')", name="ck_profile_activity"),
        CheckConstraint("theme IN ('light', 'dark', 'system')", name="ck_profile_theme"),
    )

    profile_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120))
    age: Mapped[int | None] = mapped_column(Integer)
    home_city_id: Mapped[int | None] = mapped_column(ForeignKey("city.city_id"))
    occupation: Mapped[str | None] = mapped_column(String(120))
    is_outdoor_worker: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activity_level: Mapped[str] = mapped_column(String(10), default="low", nullable=False)
    emergency_contact: Mapped[str | None] = mapped_column(String(200))
    theme: Mapped[str] = mapped_column(String(10), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")
