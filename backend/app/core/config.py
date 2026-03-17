from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """
    Small settings object for beginners.

    - Loads environment variables from `.env` (if present)
    - Provides defaults so the app runs out-of-the-box
    """

    APP_NAME: str = "AI Education Tutor (MVP)"
    APP_VERSION: str = "0.1.0"

    # Comma-separated list of origins. For MVP we default to "*" style behavior
    # by allowing localhost variants commonly used in dev.
    CORS_ALLOW_ORIGINS: list[str] = None  # type: ignore[assignment]


_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Lazy-load settings once, so imports are fast and consistent.
    """
    global _settings
    if _settings is not None:
        return _settings

    load_dotenv()

    origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8000")
    origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

    _settings = Settings(CORS_ALLOW_ORIGINS=origins)
    return _settings

