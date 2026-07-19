"""Combines all configured job sources and does a cheap, free keyword-overlap
ranking against the user's profile. (Full LLM fit evaluation is reserved for
the Apply flow on one specific posting — that's the expensive, high-value
step; running it on every search result would be slow and costly.)"""
from __future__ import annotations

import re
from typing import List

from app.job_sources import adzuna, remoteok, remotive, usajobs, jsearch
from app.models import JobPosting, Profile

_SOURCES = [adzuna, remoteok, remotive, usajobs, jsearch]

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#]{1,}")


def configured_sources() -> List[str]:
    return [s.name for s in _SOURCES if s.is_configured()]


def _tokenize(text: str) -> set:
    return {w.lower() for w in _WORD_RE.findall(text or "")}


def _keyword_score(job: JobPosting, profile_tokens: set) -> float:
    job_tokens = _tokenize(f"{job.title} {job.snippet}")
    if not job_tokens:
        return 0.0
    overlap = job_tokens & profile_tokens
    return round(100 * len(overlap) / max(len(job_tokens), 1), 1)


def search_all(query: str, location: str, profile: Profile, limit_per_source: int = 20) -> List[JobPosting]:
    profile_text = " ".join(
        [
            profile.headline,
            profile.career_goals,
            " ".join(profile.skills),
            " ".join(profile.target_roles),
            " ".join(profile.target_industries),
            " ".join(e.title for e in profile.experience),
        ]
    )
    profile_tokens = _tokenize(profile_text)

    results: List[JobPosting] = []
    for source in _SOURCES:
        if not source.is_configured():
            continue
        try:
            results.extend(source.search(query, location, limit_per_source))
        except Exception:
            # One flaky source shouldn't take down the whole search.
            continue

    seen_urls = set()
    deduped: List[JobPosting] = []
    for job in results:
        key = job.url or f"{job.title}|{job.company}"
        if key in seen_urls:
            continue
        seen_urls.add(key)
        job.keyword_score = _keyword_score(job, profile_tokens) if profile_tokens else None
        deduped.append(job)

    deduped.sort(key=lambda j: (j.keyword_score or 0), reverse=True)
    return deduped
