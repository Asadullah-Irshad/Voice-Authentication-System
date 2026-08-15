"""
config.py — Centralised, environment-driven configuration.

All settings are read from environment variables (or a local ``.env`` file)
via ``pydantic-settings``. Nothing sensitive is hard-coded — secrets such as
the JWT signing key and SMTP credentials must be supplied through the
environment. See ``.env.example`` for the full list.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Canonical paths (resolved relative to this file, CWD-independent) ─────────
APP_DIR = Path(__file__).resolve().parent  # backend/app
BACKEND_DIR = APP_DIR.parent  # backend
ROOT_DIR = BACKEND_DIR.parent  # repo root

FRONTEND_DIR = ROOT_DIR / "Frontend"
TEMPLATE_DIR = BACKEND_DIR / "template"


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "Voice Authentication System"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False)

    # ── Runtime data locations (override in tests / containers) ──────────
    data_dir: str = str(ROOT_DIR / "data")  # user records + login store
    workspaces_dir: str = str(ROOT_DIR / "workspaces")  # per-build scratch space

    # ── Security ─────────────────────────────────────────────────────────
    # MUST be overridden in production. A random default keeps dev usable but
    # invalidates tokens on restart, which is the safe failure mode.
    jwt_secret: str = Field(default="CHANGE_ME_IN_PRODUCTION_use_a_long_random_string")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # Comma-separated list of allowed browser origins for CORS.
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    # ── Uploads / pipeline limits ────────────────────────────────────────
    min_files: int = 5
    max_files: int = 20
    max_upload_mb: int = 25  # per-file cap

    # ── SMTP (optional — welcome email) ──────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Voice Authentication System"
    email_enabled: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()

# Resolved runtime paths (respect env overrides via Settings).
DATA_DIR = Path(settings.data_dir)
WORKSPACES_DIR = Path(settings.workspaces_dir)
