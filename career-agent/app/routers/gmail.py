from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import storage
from app.integrations import gmail_alerts

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status")
def status() -> dict:
    return {
        "configured": gmail_alerts.is_configured(),
        "authorized": gmail_alerts.is_authorized(),
    }


@router.post("/authorize")
def authorize() -> dict:
    try:
        gmail_alerts.authorize()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gmail authorization failed: {exc}")
    return {"status": "authorized"}


@router.post("/check")
def check() -> dict:
    try:
        postings = gmail_alerts.check_for_new_alerts()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gmail check failed: {exc}")
    fresh = storage.record_discovered_links(postings)
    return {"scanned": len(postings), "new_count": len(fresh)}
