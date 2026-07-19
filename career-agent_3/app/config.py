"""Central configuration, loaded once from the environment / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

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
    groq_api_key: str
    # llama-3.3-70b-versatile: best quality on free tier
    model_quality: str
    # llama-3.1-8b-instant: faster / cheaper for simple calls
    model_fast: str

    adzuna_app_id: str
    adzuna_app_key: str
    adzuna_country: str

    usajobs_api_key: str
    usajobs_user_agent_email: str

    jsearch_api_key: str

    basic_auth_username: str
    basic_auth_password: str
    host: str
    port: int

    contact_email: str
    latex_bin_dir: str

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def basic_auth_enabled(self) -> bool:
        return bool(self.basic_auth_username and self.basic_auth_password)

    @property
    def adzuna_configured(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)

    @property
    def usajobs_configured(self) -> bool:
        return bool(self.usajobs_api_key and self.usajobs_user_agent_email)


def load_settings() -> Settings:
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        model_quality=os.getenv("CAREER_AGENT_MODEL_QUALITY", "llama-3.3-70b-versatile").strip(),
        model_fast=os.getenv("CAREER_AGENT_MODEL_FAST", "llama-3.1-8b-instant").strip(),
        adzuna_app_id=os.getenv("ADZUNA_APP_ID", "").strip(),
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY", "").strip(),
        adzuna_country=os.getenv("ADZUNA_COUNTRY", "us").strip() or "us",
        usajobs_api_key=os.getenv("USAJOBS_API_KEY", "").strip(),
        usajobs_user_agent_email=os.getenv("USAJOBS_USER_AGENT_EMAIL", "").strip(),
        jsearch_api_key=os.getenv("JSEARCH_API_KEY", "").strip(),
        basic_auth_username=os.getenv("BASIC_AUTH_USERNAME", "").strip(),
        basic_auth_password=os.getenv("BASIC_AUTH_PASSWORD", "").strip(),
        host=os.getenv("CAREER_AGENT_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=int(os.getenv("CAREER_AGENT_PORT", "8420").strip() or "8420"),
        contact_email=os.getenv("CAREER_AGENT_CONTACT_EMAIL", "you@example.com").strip(),
        latex_bin_dir=os.getenv("LATEX_BIN_DIR", "").strip(),
    )


settings = load_settings()
