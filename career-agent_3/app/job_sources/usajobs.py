"""USAJobs (US federal jobs) API. Free key: https://developer.usajobs.gov/"""
from __future__ import annotations

from typing import List

import requests

from app.config import settings
from app.models import JobPosting

name = "usajobs"


def is_configured() -> bool:
    return settings.usajobs_configured


def search(query: str, location: str = "", limit: int = 20) -> List[JobPosting]:
    if not is_configured():
        return []
    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": settings.usajobs_user_agent_email,
        "Authorization-Key": settings.usajobs_api_key,
    }
    params = {"Keyword": query, "ResultsPerPage": min(limit, 25)}
    if location:
        params["LocationName"] = location

    resp = requests.get("https://data.usajobs.gov/api/search", headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    postings: List[JobPosting] = []
    for item in data.get("SearchResult", {}).get("SearchResultItems", []):
        d = item.get("MatchedObjectDescriptor", {})
        locations = d.get("PositionLocation", [])
        loc_str = ", ".join(l.get("LocationName", "") for l in locations) if locations else ""
        remuneration = d.get("PositionRemuneration", [{}])
        salary = ""
        if remuneration:
            r = remuneration[0]
            salary = f"{r.get('MinimumRange', '')}-{r.get('MaximumRange', '')} {r.get('RateIntervalCode', '')}".strip()
        postings.append(
            JobPosting(
                title=d.get("PositionTitle", ""),
                company=d.get("OrganizationName", ""),
                location=loc_str,
                url=d.get("PositionURI", ""),
                source="usajobs",
                salary=salary,
                posted_date=d.get("PublicationStartDate", ""),
                snippet=(d.get("UserArea", {}).get("Details", {}).get("JobSummary", "") or "")[:600],
            )
        )
    return postings
