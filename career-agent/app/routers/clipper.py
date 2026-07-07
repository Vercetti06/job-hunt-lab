from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import storage
from app.models import JobPosting

router = APIRouter(prefix="/api/clipper", tags=["clipper"])


class ClippedPosting(BaseModel):
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    snippet: str = ""
    source: str = "clipper"


class IngestRequest(BaseModel):
    postings: List[ClippedPosting]
    page_url: Optional[str] = None


@router.post("/ingest")
def ingest(body: IngestRequest) -> dict:
    postings = [
        JobPosting(
            url=p.url, title=p.title, company=p.company,
            location=p.location, snippet=p.snippet, source=p.source,
        )
        for p in body.postings
    ]
    fresh = storage.record_discovered_links(postings)
    return {"received": len(postings), "new_count": len(fresh)}


@router.get("/recent")
def recent(limit: int = 100) -> List[dict]:
    return storage.list_discovered_links(limit=limit)
