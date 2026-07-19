from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app import storage
from app.job_sources import aggregator
from app.models import JobPosting

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/sources")
def sources() -> Dict[str, Any]:
    return {"configured": aggregator.configured_sources()}


@router.get("")
def search(query: str, location: str = "") -> List[JobPosting]:
    profile = storage.load_profile()
    return aggregator.search_all(query=query, location=location, profile=profile)
