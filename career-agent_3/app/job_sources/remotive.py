"""Remotive public API — no key required. https://remotive.com/api-documentation"""
from __future__ import annotations

from typing import List

import requests

from app.models import JobPosting

name = "remotive"


def is_configured() -> bool:
    return True


def search(query: str, location: str = "", limit: int = 20) -> List[JobPosting]:
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query} if query else {},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    postings: List[JobPosting] = []
    for item in data.get("jobs", [])[:limit]:
        postings.append(
            JobPosting(
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("candidate_required_location", "Remote"),
                url=item.get("url", ""),
                source="remotive",
                salary=item.get("salary", "") or "",
                posted_date=item.get("publication_date", ""),
                snippet=(item.get("description", "") or "")[:600],
            )
        )
    return postings
