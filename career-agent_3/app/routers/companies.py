from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import storage
from app.job_sources import ats_watch
from app.job_sources.aggregator import _keyword_score, _tokenize
from app.models import JobPosting, WatchedCompany

router = APIRouter(prefix="/api/companies", tags=["companies"])


class AddCompanyRequest(BaseModel):
    name: str
    ats_type: str
    slug: str


@router.get("/ats-types")
def ats_types() -> List[str]:
    return ats_watch.SUPPORTED_ATS_TYPES


@router.get("")
def list_companies() -> List[WatchedCompany]:
    return storage.list_watched_companies()


@router.post("")
def add_company(body: AddCompanyRequest) -> WatchedCompany:
    if body.ats_type not in ats_watch.SUPPORTED_ATS_TYPES:
        raise HTTPException(status_code=400, detail=f"ats_type must be one of {ats_watch.SUPPORTED_ATS_TYPES}")
    company_id = storage.add_watched_company(body.name, body.ats_type, body.slug.strip())
    companies = storage.list_watched_companies()
    match = next((c for c in companies if c.id == company_id), None)
    if not match:
        raise HTTPException(status_code=500, detail="Failed to save company.")
    return match


@router.delete("/{company_id}")
def delete_company(company_id: int) -> dict:
    storage.delete_watched_company(company_id)
    return {"status": "deleted"}


@router.get("/postings")
def watched_postings() -> List[JobPosting]:
    companies = storage.list_watched_companies()
    if not companies:
        return []
    profile = storage.load_profile()
    profile_text = " ".join(
        [profile.headline, profile.career_goals, " ".join(profile.skills), " ".join(profile.target_roles)]
    )
    profile_tokens = _tokenize(profile_text)

    postings = ats_watch.fetch_all_watched(companies)
    for p in postings:
        p.keyword_score = _keyword_score(p, profile_tokens) if profile_tokens else None
    postings.sort(key=lambda p: (p.keyword_score or 0), reverse=True)
    return postings
