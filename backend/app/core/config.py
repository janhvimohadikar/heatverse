"""Application settings, read from environment variables / backend/.env (never hard-code secrets)."""
from __future__ import annotations

import secrets
import warnings
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "heatverse.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HEATVERSE API"
    database_path: str = str(DEFAULT_DB_PATH)
    secret_key: str = Field(default="", validate_default=True)
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Live weather (Open-Meteo works without a key for non-commercial use)
    live_weather_enabled: bool = True
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    external_timeout_seconds: float = 8.0

    # Hospitals (OpenStreetMap Overpass API, no key)
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    hospitals_enabled: bool = True

    # Optional trained ML model (see docs/architecture.md)
    model_path: str = ""

    @field_validator("secret_key")
    @classmethod
    def _ensure_secret(cls, v: str) -> str:
        if not v or v.startswith("change-me"):
            warnings.warn(
                "SECRET_KEY is not set: using a random key for this run. Logins will be invalidated on restart. "
                "Set SECRET_KEY in backend/.env (see README).",
                stacklevel=2,
            )
            return secrets.token_urlsafe(48)
        return v

    @property
    def database_url(self) -> str:
        return f"sqlite:///{Path(self.database_path).resolve().as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
