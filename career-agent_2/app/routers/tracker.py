from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import storage
from app.models import Application

router = APIRouter(prefix="/api/applications", tags=["applications"])

VALID_STATUSES = {"drafted", "applied", "interviewing", "offer", "rejected", "withdrawn"}

DOC_FIELD_MAP = {
    "cv_docx": "cv_docx_path",
    "cv_pdf": "cv_pdf_path",
    "cv_tex": "cv_tex_path",
    "cover_letter_docx": "cover_letter_docx_path",
    "cover_letter_pdf": "cover_letter_pdf_path",
    "cover_letter_tex": "cover_letter_tex_path",
}


class StatusUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
def list_applications() -> List[Application]:
    return storage.list_applications()


@router.get("/{app_id}")
def get_application(app_id: int) -> Application:
    app_ = storage.get_application(app_id)
    if not app_:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app_


@router.patch("/{app_id}")
def update_application(app_id: int, body: StatusUpdate) -> Application:
    app_ = storage.get_application(app_id)
    if not app_:
        raise HTTPException(status_code=404, detail="Application not found.")
    fields = {}
    if body.status is not None:
        if body.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUSES)}")
        fields["status"] = body.status
    if body.notes is not None:
        fields["notes"] = body.notes
    if fields:
        storage.update_application(app_id, **fields)
    return storage.get_application(app_id)


@router.delete("/{app_id}")
def delete_application(app_id: int) -> dict:
    app_ = storage.get_application(app_id)
    if not app_:
        raise HTTPException(status_code=404, detail="Application not found.")
    storage.delete_application(app_id)
    return {"status": "deleted"}


@router.get("/{app_id}/download/{doc_key}")
def download_document(app_id: int, doc_key: str):
    if doc_key not in DOC_FIELD_MAP:
        raise HTTPException(status_code=400, detail=f"doc_key must be one of {list(DOC_FIELD_MAP)}")
    app_ = storage.get_application(app_id)
    if not app_:
        raise HTTPException(status_code=404, detail="Application not found.")
    path_str = getattr(app_, DOC_FIELD_MAP[doc_key])
    if not path_str:
        raise HTTPException(status_code=404, detail="That document wasn't generated for this application "
                                                       "(PDF requires a local LaTeX install).")
    path = Path(path_str)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File is missing on disk.")
    return FileResponse(str(path), filename=path.name)
