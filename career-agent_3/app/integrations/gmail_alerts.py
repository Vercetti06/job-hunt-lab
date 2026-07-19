"""Reads job-alert emails from your own Gmail inbox — the alerts YOU set up on
LinkedIn/Indeed/Naukri/etc. through their own "email me matching jobs" feature.
This is the platforms' own intended notification mechanism, read via Gmail's
official read-only API with your explicit OAuth consent. Nothing is scraped;
nothing is sent anywhere except to Google's API to read your own mailbox.

One-time setup (see README for exact steps): create a free Google Cloud OAuth
credential (Desktop app type) with the gmail.readonly scope, save it as
data/gmail_credentials.json, then hit "Authorize Gmail" once in the app.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from typing import List

from app.config import GMAIL_ALERT_SOURCES_PATH, GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH
from app.models import JobPosting

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def is_configured() -> bool:
    return GMAIL_CREDENTIALS_PATH.exists()


def is_authorized() -> bool:
    return GMAIL_TOKEN_PATH.exists()


def _load_platform_config() -> List[dict]:
    if not GMAIL_ALERT_SOURCES_PATH.exists():
        return []
    data = json.loads(GMAIL_ALERT_SOURCES_PATH.read_text(encoding="utf-8"))
    return data.get("platforms", [])


def authorize() -> None:
    """Runs the one-time interactive OAuth consent flow. Opens a browser tab;
    blocks until the user completes (or cancels) it."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not is_configured():
        raise RuntimeError(
            f"No Gmail OAuth credentials found at {GMAIL_CREDENTIALS_PATH}. "
            "Follow the Gmail setup steps in the README first."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(GMAIL_CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    GMAIL_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")


def _get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not is_authorized():
        raise RuntimeError("Gmail isn't authorized yet — click 'Authorize Gmail' first.")

    creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GMAIL_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def _decode_part(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8") + b"==").decode("utf-8", errors="ignore")


def _extract_body_html(payload: dict) -> str:
    """Walks the (possibly nested multipart) Gmail message payload and returns
    the best HTML body it can find, falling back to plain text only if no
    HTML part exists anywhere in the tree."""
    html_result = _find_mime_part(payload, "text/html")
    if html_result:
        return html_result
    return _find_mime_part(payload, "text/plain") or ""


def _find_mime_part(payload: dict, mime_type: str) -> str:
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return _decode_part(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        found = _find_mime_part(part, mime_type)
        if found:
            return found
    return ""


def _clean_html_snippet(html: str, max_len: int = 300) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def check_for_new_alerts(max_results: int = 50) -> List[JobPosting]:
    """Fetches recent job-alert emails (since the last check) and extracts
    job posting links from each, per the configured per-platform regex."""
    platforms = _load_platform_config()
    if not platforms:
        return []

    service = _get_service()

    all_senders = [s for p in platforms for s in p.get("senders", [])]
    if not all_senders:
        return []
    sender_query = " OR ".join(f"from:{s}" for s in all_senders)

    last_check = None
    from app import storage
    last_check_str = storage.get_state("gmail_last_check_epoch")
    if last_check_str:
        last_check = int(last_check_str)

    query = f"({sender_query})"
    if last_check:
        query += f" after:{last_check}"

    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    message_ids = [m["id"] for m in results.get("messages", [])]

    postings: List[JobPosting] = []
    for msg_id in message_ids:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = headers.get("from", "")

        platform = next((p for p in platforms if any(s in sender for s in p.get("senders", []))), None)
        if not platform:
            continue

        body_html = _extract_body_html(msg.get("payload", {}))
        if not body_html:
            continue

        pattern = platform.get("url_pattern", "")
        if not pattern:
            continue
        urls = sorted(set(re.findall(pattern, body_html)))

        for url in urls:
            postings.append(
                JobPosting(
                    url=url.rstrip(".,"),
                    title="",
                    company="",
                    snippet=_clean_html_snippet(body_html)[:300],
                    source=f"email:{platform['name']}",
                )
            )

    storage.set_state("gmail_last_check_epoch", str(int(datetime.now(timezone.utc).timestamp())))
    return postings
