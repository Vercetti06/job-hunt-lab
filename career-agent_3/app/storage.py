"""Lightweight SQLite storage. No ORM — this app has a small, stable schema
and stdlib sqlite3 keeps the dependency list (and setup steps) short."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, List, Optional

from app.config import DB_PATH
from app.models import Application, Profile, WatchedCompany

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_interview_history (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title TEXT DEFAULT '',
    company TEXT DEFAULT '',
    job_url TEXT DEFAULT '',
    job_full_text TEXT DEFAULT '',
    status TEXT DEFAULT 'drafted',
    fit_score INTEGER,
    fit_json TEXT DEFAULT '',
    cv_docx_path TEXT DEFAULT '',
    cv_tex_path TEXT DEFAULT '',
    cv_pdf_path TEXT DEFAULT '',
    cover_letter_docx_path TEXT DEFAULT '',
    cover_letter_tex_path TEXT DEFAULT '',
    cover_letter_pdf_path TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interview_prep (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE TABLE IF NOT EXISTS watched_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ats_type TEXT NOT NULL,
    slug TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(ats_type, slug)
);

CREATE TABLE IF NOT EXISTS discovered_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    source TEXT DEFAULT '',
    title TEXT DEFAULT '',
    company TEXT DEFAULT '',
    location TEXT DEFAULT '',
    snippet TEXT DEFAULT '',
    discovered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def load_profile() -> Profile:
    with get_conn() as conn:
        row = conn.execute("SELECT data FROM profile WHERE id = 1").fetchone()
        if not row:
            return Profile()
        return Profile.model_validate_json(row["data"])


def save_profile(profile: Profile) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO profile (id, data, updated_at) VALUES (1, ?, ?)
               ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at""",
            (profile.model_dump_json(), _now()),
        )


def load_interview_history() -> List[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT data FROM profile_interview_history WHERE id = 1").fetchone()
        if not row:
            return []
        return json.loads(row["data"])


def save_interview_history(history: List[dict]) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO profile_interview_history (id, data) VALUES (1, ?)
               ON CONFLICT(id) DO UPDATE SET data = excluded.data""",
            (json.dumps(history),),
        )


def reset_interview_history() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM profile_interview_history WHERE id = 1")


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

def create_application(app_: Application) -> int:
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO applications
               (job_title, company, job_url, job_full_text, status, fit_score, fit_json,
                cv_docx_path, cv_tex_path, cv_pdf_path,
                cover_letter_docx_path, cover_letter_tex_path, cover_letter_pdf_path,
                notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                app_.job_title, app_.company, app_.job_url, app_.job_full_text, app_.status, app_.fit_score,
                app_.fit_json, app_.cv_docx_path, app_.cv_tex_path, app_.cv_pdf_path,
                app_.cover_letter_docx_path, app_.cover_letter_tex_path, app_.cover_letter_pdf_path,
                app_.notes, now, now,
            ),
        )
        return cur.lastrowid


def update_application(app_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE applications SET {set_clause} WHERE id = ?",
            (*fields.values(), app_id),
        )


def get_application(app_id: int) -> Optional[Application]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        if not row:
            return None
        return Application(**dict(row))


def list_applications() -> List[Application]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()
        return [Application(**dict(r)) for r in rows]


def delete_application(app_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.execute("DELETE FROM interview_prep WHERE application_id = ?", (app_id,))


# ---------------------------------------------------------------------------
# Interview prep
# ---------------------------------------------------------------------------

def save_interview_prep(application_id: int, content: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO interview_prep (application_id, content, created_at) VALUES (?,?,?)",
            (application_id, json.dumps(content), _now()),
        )
        return cur.lastrowid


def get_latest_interview_prep(application_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content FROM interview_prep WHERE application_id = ? ORDER BY id DESC LIMIT 1",
            (application_id,),
        ).fetchone()
        return json.loads(row["content"]) if row else None


# ---------------------------------------------------------------------------
# Watched companies (direct ATS integrations)
# ---------------------------------------------------------------------------

def add_watched_company(name: str, ats_type: str, slug: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO watched_companies (name, ats_type, slug, created_at) VALUES (?,?,?,?)",
            (name, ats_type, slug, _now()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM watched_companies WHERE ats_type = ? AND slug = ?", (ats_type, slug)
        ).fetchone()
        return row["id"]


def list_watched_companies() -> List[WatchedCompany]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM watched_companies ORDER BY created_at DESC").fetchall()
        return [WatchedCompany(**dict(r)) for r in rows]


def delete_watched_company(company_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM watched_companies WHERE id = ?", (company_id,))


# ---------------------------------------------------------------------------
# Discovered links (bookmarklet clipper + email alert ingestion dedup log)
# ---------------------------------------------------------------------------

def record_discovered_links(postings: List["JobPosting"]) -> List["JobPosting"]:
    """Insert postings not seen before; returns only the newly-seen ones."""
    fresh: List["JobPosting"] = []
    with get_conn() as conn:
        for p in postings:
            if not p.url:
                continue
            try:
                conn.execute(
                    """INSERT INTO discovered_links (url, source, title, company, location, snippet, discovered_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (p.url, p.source, p.title, p.company, p.location, p.snippet, _now()),
                )
                fresh.append(p)
            except sqlite3.IntegrityError:
                continue  # already seen this exact URL before
    return fresh


def list_discovered_links(limit: int = 200) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM discovered_links ORDER BY discovered_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Generic small key-value state (e.g. last Gmail alert check timestamp)
# ---------------------------------------------------------------------------

def get_state(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_state(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO app_state (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
