"""Direct-to-source integrations with the applicant tracking systems (ATS) that
actually host most company job postings. These are the same public, documented,
no-key-needed JSON endpoints each company's own careers page calls to render its
job list — meant to be embedded/read programmatically. Not scraping: reading a
public API a company deliberately exposes for this exact purpose. Often faster
than LinkedIn/Indeed too, since those sites syndicate from here with some lag.

There's no cross-company search on any of these APIs — you fetch one company's
board at a time — so this module works off a user-maintained "watch list"
(see storage.list_watched_companies) rather than a keyword query.
"""
from __future__ import annotations

from typing import List

import requests

from app.models import JobPosting, WatchedCompany

_TIMEOUT = 15


def _get_json(url: str, **kwargs):
    resp = requests.get(url, timeout=_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def fetch_greenhouse(company: WatchedCompany) -> List[JobPosting]:
    try:
        data = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{company.slug}/jobs")
    except Exception:
        return []
    postings = []
    for job in data.get("jobs", []):
        postings.append(
            JobPosting(
                title=job.get("title", ""),
                company=company.name,
                location=(job.get("location") or {}).get("name", ""),
                url=job.get("absolute_url", ""),
                source="greenhouse",
                posted_date=job.get("updated_at", ""),
                snippet=(job.get("content", "") or "")[:600],
            )
        )
    return postings


def fetch_lever(company: WatchedCompany) -> List[JobPosting]:
    try:
        data = _get_json(f"https://api.lever.co/v0/postings/{company.slug}?mode=json")
    except Exception:
        return []
    postings = []
    for job in data if isinstance(data, list) else []:
        categories = job.get("categories", {}) or {}
        postings.append(
            JobPosting(
                title=job.get("text", ""),
                company=company.name,
                location=categories.get("location", ""),
                url=job.get("hostedUrl", ""),
                source="lever",
                posted_date=str(job.get("createdAt", "")),
                snippet=(job.get("descriptionPlain", "") or "")[:600],
            )
        )
    return postings


def fetch_ashby(company: WatchedCompany) -> List[JobPosting]:
    try:
        data = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{company.slug}")
    except Exception:
        return []
    postings = []
    for job in data.get("jobs", []):
        postings.append(
            JobPosting(
                title=job.get("title", ""),
                company=company.name,
                location=job.get("location", "") or job.get("locationName", ""),
                url=job.get("jobUrl", "") or job.get("applyUrl", ""),
                source="ashby",
                posted_date=job.get("publishedAt", "") or job.get("publishedDate", ""),
                snippet=(job.get("descriptionPlain", "") or job.get("description", "") or "")[:600],
            )
        )
    return postings


def fetch_smartrecruiters(company: WatchedCompany) -> List[JobPosting]:
    try:
        data = _get_json(f"https://api.smartrecruiters.com/v1/companies/{company.slug}/postings")
    except Exception:
        return []
    postings = []
    for job in data.get("content", []):
        loc = job.get("location", {}) or {}
        loc_str = ", ".join(b for b in [loc.get("city", ""), loc.get("region", ""), loc.get("country", "")] if b)
        job_id = job.get("id", "")
        postings.append(
            JobPosting(
                title=job.get("name", ""),
                company=company.name,
                location=loc_str,
                url=job.get("postingUrl") or f"https://jobs.smartrecruiters.com/{company.slug}/{job_id}",
                source="smartrecruiters",
                posted_date=job.get("releasedDate", ""),
                snippet=(job.get("jobAd", {}) or {}).get("sections", {}).get("jobDescription", {}).get("text", "")[:600]
                if isinstance(job.get("jobAd"), dict) else "",
            )
        )
    return postings


_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
}

SUPPORTED_ATS_TYPES = list(_FETCHERS.keys())


def fetch_all_watched(companies: List[WatchedCompany]) -> List[JobPosting]:
    results: List[JobPosting] = []
    for company in companies:
        fetcher = _FETCHERS.get(company.ats_type)
        if not fetcher:
            continue
        try:
            results.extend(fetcher(company))
        except Exception:
            continue  # one bad/renamed company board shouldn't break the rest
    return results
