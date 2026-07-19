"""JSearch (via RapidAPI) — aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter and
more through Google for Jobs' indexed, structured-data listings (i.e. postings those
sites already publish for search-engine indexing — this is not scraping them).
Optional: only activates if you set JSEARCH_API_KEY. Has a free tier.
Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"""
from __future__ import annotations

from typing import List

import requests

from app.config import settings
from app.models import JobPosting

name = "jsearch"


def is_configured() -> bool:
    return bool(settings.jsearch_api_key)


def search(query: str, location: str = "", limit: int = 20) -> List[JobPosting]:
    if not is_configured():
        return []
    q = f"{query} in {location}" if location else query
    headers = {
        "X-RapidAPI-Key": settings.jsearch_api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    params = {"query": q, "page": "1", "num_pages": "1"}

    try:
        resp = requests.get(
            "https://jsearch.p.rapidapi.com/search", headers=headers, params=params, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    postings: List[JobPosting] = []
    for item in data.get("data", [])[:limit]:
        salary = ""
        if item.get("job_min_salary") or item.get("job_max_salary"):
            salary = f"{item.get('job_min_salary', '')}-{item.get('job_max_salary', '')} {item.get('job_salary_currency', '')}".strip()
        loc_bits = [item.get("job_city", ""), item.get("job_state", ""), item.get("job_country", "")]
        location_str = ", ".join(b for b in loc_bits if b)
        postings.append(
            JobPosting(
                title=item.get("job_title", ""),
                company=item.get("employer_name", ""),
                location=location_str or ("Remote" if item.get("job_is_remote") else ""),
                url=item.get("job_apply_link", "") or item.get("job_google_link", ""),
                source=f"jsearch:{item.get('job_publisher', 'web')}",
                salary=salary,
                posted_date=item.get("job_posted_at_datetime_utc", ""),
                snippet=(item.get("job_description", "") or "")[:600],
            )
        )
    return postings
