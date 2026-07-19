from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app import storage
from app.agents import interview_prep as interview_prep_agent
from app.models import FitEvaluation, JobPosting

router = APIRouter(prefix="/api/applications", tags=["interview_prep"])


def _load_job_and_fit(app_id: int):
    app_ = storage.get_application(app_id)
    if not app_:
        raise HTTPException(status_code=404, detail="Application not found.")
    if not app_.fit_json:
        raise HTTPException(status_code=400, detail="No fit evaluation stored for this application.")
    job = JobPosting(
        title=app_.job_title,
        company=app_.company,
        url=app_.job_url,
        full_text=app_.job_full_text,
        source="direct_link",
    )
    fit = FitEvaluation.model_validate_json(app_.fit_json)
    return app_, job, fit


@router.get("/{app_id}/interview-prep")
def get_interview_prep(app_id: int) -> Dict[str, Any]:
    app_ = storage.get_application(app_id)
    if not app_:
        raise HTTPException(status_code=404, detail="Application not found.")
    existing = storage.get_latest_interview_prep(app_id)
    if not existing:
        raise HTTPException(status_code=404, detail="No interview prep generated yet for this application.")
    return existing


@router.post("/{app_id}/interview-prep")
def generate_interview_prep(app_id: int) -> Dict[str, Any]:
    profile = storage.load_profile()
    _, job, fit = _load_job_and_fit(app_id)
    prep = interview_prep_agent.generate(profile, job, fit)
    storage.save_interview_prep(app_id, prep)
    return prep
