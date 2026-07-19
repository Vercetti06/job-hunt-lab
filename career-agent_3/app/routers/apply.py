from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import storage
from app.agents.pipeline import run_apply_pipeline
from app.config import DOCS_DIR
from app.documents import docx_writer, latex_writer
from app.fetchers import job_page_fetcher
from app.models import Application

router = APIRouter(prefix="/api/apply", tags=["apply"])


class ApplyRequest(BaseModel):
    job_url: str


@router.post("")
def apply(body: ApplyRequest) -> Dict[str, Any]:
    profile = storage.load_profile()
    if not profile.full_name or not profile.experience:
        raise HTTPException(
            status_code=400,
            detail="Your profile isn't set up yet. Finish the profile interview first.",
        )

    try:
        job = job_page_fetcher.fetch(body.job_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Couldn't fetch that job posting: {exc}")

    if not (job.full_text or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Fetched the page but couldn't find readable job content on it. "
                   "Some sites render postings via JavaScript this app can't execute — "
                   "try pasting the posting text directly instead.",
        )

    result = run_apply_pipeline(profile, job)

    app_record = Application(
        job_title=job.title,
        company=job.company,
        job_url=job.url,
        job_full_text=job.full_text,
        status="drafted",
        fit_score=result.fit.fit_score,
        fit_json=result.fit.model_dump_json(),
        notes="\n".join(result.review_log),
    )
    app_id = storage.create_application(app_record)

    out_dir = DOCS_DIR / f"app_{app_id}"
    cv_docx = docx_writer.render_cv_docx(result.package.cv, out_dir / "cv.docx")
    cl_docx = docx_writer.render_cover_letter_docx(result.package.cover_letter, out_dir / "cover_letter.docx")
    cv_latex = latex_writer.render_cv_latex(result.package.cv, out_dir, basename="cv")
    cl_latex = latex_writer.render_cover_letter_latex(result.package.cover_letter, out_dir, basename="cover_letter")

    storage.update_application(
        app_id,
        cv_docx_path=str(cv_docx),
        cover_letter_docx_path=str(cl_docx),
        cv_tex_path=str(cv_latex["tex_path"]),
        cv_pdf_path=str(cv_latex["pdf_path"]) if cv_latex["pdf_path"] else "",
        cover_letter_tex_path=str(cl_latex["tex_path"]),
        cover_letter_pdf_path=str(cl_latex["pdf_path"]) if cl_latex["pdf_path"] else "",
    )

    return {
        "application_id": app_id,
        "job": job.model_dump(),
        "fit": result.fit.model_dump(),
        "package": {
            "cv": result.package.cv.model_dump(),
            "cover_letter": result.package.cover_letter.model_dump(),
        },
        "review": {
            "rounds": result.rounds,
            "approved": result.approved,
            "log": result.review_log,
        },
        "documents": {
            "cv_docx": bool(cv_docx),
            "cv_pdf": bool(cv_latex["pdf_path"]),
            "cover_letter_docx": bool(cl_docx),
            "cover_letter_pdf": bool(cl_latex["pdf_path"]),
            "latex_available": bool(cv_latex["pdf_path"] or cl_latex["pdf_path"]),
        },
    }
