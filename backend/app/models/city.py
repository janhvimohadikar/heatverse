from __future__ import annotations

from sqlalchemy import Integer, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class City(Base):
    """Mirrors the `city` table created by scripts/import_excel.py (the app never writes to it)."""
    __tablename__ = "city"
    city_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    state: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    is_coastal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coord_source: Mapped[str | None] = mapped_column(String)
