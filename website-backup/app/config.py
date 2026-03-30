"""
Mirai Portal — Configuration.

Single source of truth for all settings. Reads from environment / .env file.
"""

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

# Load .env from the website/ directory
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    """App settings derived from environment variables."""

    def __init__(self) -> None:
        self.google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
        self.google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.session_secret: str = os.getenv("MIRAI_SESSION_SECRET", "change-me-in-production")
        self.base_url: str = os.getenv("MIRAI_BASE_URL", "http://localhost:8000")
        self._admin_emails_raw: str = os.getenv("MIRAI_ADMIN_EMAILS", "")

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def admin_emails(self) -> set[str]:
        return {
            e.strip().lower()
            for e in self._admin_emails_raw.split(",")
            if e.strip()
        }

    def is_admin(self, email: str) -> bool:
        return email.lower().strip() in self.admin_emails


settings = Settings()
