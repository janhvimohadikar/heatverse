from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class Prediction(Base):
    """One stored risk prediction (also serves as the user's prediction history)."""
    __tablename__ = "prediction"
    __table_args__ = (
        CheckConstraint("horizon_days >= 0 AND horizon_days <= 14", name="ck_pred_horizon"),
        CheckConstraint("risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)", name="ck_pred_score"),
        Index("idx_prediction_user_created", "user_id", "created_at"),
    )

    prediction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.user_id", ondelete="CASCADE"), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("city.city_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    target_date: Mapped[str] = mapped_column(String(10), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_category: Mapped[str | None] = mapped_column(String(20))
    personal_score: Mapped[int | None] = mapped_column(Integer)
    personal_category: Mapped[str | None] = mapped_column(String(20))
    expected_temp_max_c: Mapped[float | None] = mapped_column(Float)
    heatwave_probability: Mapped[float | None] = mapped_column(Float)   # only set by a real model
    confidence: Mapped[float | None] = mapped_column(Float)             # only set if a real model provides it
    details: Mapped[dict | None] = mapped_column(JSON)                  # full response payload
