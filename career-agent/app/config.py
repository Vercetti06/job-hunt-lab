"""Central configuration, loaded once from the environment / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root regardless of current working directory.
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DOCS_DIR = DATA_DIR / "generated_documents"
DOCS_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "career_agent.db"
GMAIL_CREDENTIALS_PATH = DATA_DIR / "gmail_credentials.json"
GMAIL_TOKEN_PATH = DATA_DIR / "gmail_token.json"
GMAIL_ALERT_SOURCES_PATH = DATA_DIR / "gmail_alert_sources.json"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model_quality: str
    model_fast: str

    adzuna_app_id: str
    adzuna_app_key: str
    adzuna_country: str

    usajobs_api_key: str
    usajobs_user_agent_email: str

    jsearch_api_key: str

    contact_email: str
    latex_bin_dir: str

    @property
    def adzuna_configured(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)

    @property
    def usajobs_configured(self) -> bool:
        return bool(self.usajobs_api_key and self.usajobs_user_agent_email)

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)


def load_settings() -> Settings:
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        model_quality=os.getenv("CAREER_AGENT_MODEL_QUALITY", "claude-sonnet-5").strip(),
        model_fast=os.getenv("CAREER_AGENT_MODEL_FAST", "claude-haiku-4-5-20251001").strip(),
        adzuna_app_id=os.getenv("ADZUNA_APP_ID", "").strip(),
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY", "").strip(),
        adzuna_country=os.getenv("ADZUNA_COUNTRY", "us").strip() or "us",
        usajobs_api_key=os.getenv("USAJOBS_API_KEY", "").strip(),
        usajobs_user_agent_email=os.getenv("USAJOBS_USER_AGENT_EMAIL", "").strip(),
        jsearch_api_key=os.getenv("JSEARCH_API_KEY", "").strip(),
        contact_email=os.getenv("CAREER_AGENT_CONTACT_EMAIL", "you@example.com").strip(),
        latex_bin_dir=os.getenv("LATEX_BIN_DIR", "").strip(),
    )


settings = load_settings()
