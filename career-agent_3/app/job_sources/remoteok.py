"""RemoteOK public API — no key required, but a real User-Agent is needed or
requests get blocked."""
from __future__ import annotations

from typing import List

import requests

from app.config import settings
from app.models import JobPosting

name = "remoteok"

_HEADERS = {"User-Agent": f"career-agent (personal use; contact {settings.contact_email})"}


def is_configured() -> bool:
    return True  # no key needed


def search(query: str, location: str = "", limit: int = 20) -> List[JobPosting]:
    try:
        resp = requests.get("https://remoteok.com/api", headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    query_lower = query.lower().strip()
    postings: List[JobPosting] = []
    for item in data:
        if not isinstance(item, dict) or "position" not in item:
            continue  # first element is a metadata blob, not a job
        title = item.get("position", "")
        tags = " ".join(item.get("tags", []))
        haystack = f"{title} {item.get('description', '')} {tags}".lower()
        if query_lower and query_lower not in haystack:
            continue
        postings.append(
            JobPosting(
                title=title,
                company=item.get("company", ""),
                location=item.get("location", "Remote"),
                url=item.get("url", "") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}",
                source="remoteok",
                salary=item.get("salary", "") or "",
                posted_date=item.get("date", ""),
                snippet=(item.get("description", "") or "")[:600],
            )
        )
        if len(postings) >= limit:
            break
    return postings
