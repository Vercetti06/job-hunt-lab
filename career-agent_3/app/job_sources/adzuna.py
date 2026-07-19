"""Adzuna job search API. Free key: https://developer.adzuna.com/"""
from __future__ import annotations

from typing import List

import requests

from app.config import settings
from app.models import JobPosting

name = "adzuna"


def is_configured() -> bool:
    return settings.adzuna_configured


def search(query: str, location: str = "", limit: int = 20) -> List[JobPosting]:
    if not is_configured():
        return []
    url = f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": min(limit, 50),
        "what": query,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    postings: List[JobPosting] = []
    for item in data.get("results", []):
        salary_bits = []
        if item.get("salary_min"):
            salary_bits.append(f"{item['salary_min']:.0f}")
        if item.get("salary_max"):
            salary_bits.append(f"{item['salary_max']:.0f}")
        postings.append(
            JobPosting(
                title=item.get("title", ""),
                company=(item.get("company") or {}).get("display_name", ""),
                location=(item.get("location") or {}).get("display_name", ""),
                url=item.get("redirect_url", ""),
                source="adzuna",
                salary="-".join(salary_bits),
                posted_date=item.get("created", ""),
                snippet=item.get("description", ""),
            )
        )
    return postings
