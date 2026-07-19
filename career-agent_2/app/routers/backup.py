"""Manual backup/restore — the persistence strategy for running on an
ephemeral EC2 instance (fresh each session). Export before you shut down,
restore right after you launch the next one. Bundles the SQLite DB (profile,
applications, tracker, watched companies, discovered links), the actual
generated CV/cover-letter files, and your Gmail token (so you don't have to
re-authorize every fresh instance). Deliberately excludes .env — that holds
API keys, and shouldn't ride along inside a backup file you might store
somewhere less locked-down than your secrets manager.
"""
from __future__ import annotations

import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import (
    DATA_DIR,
    DB_PATH,
    DOCS_DIR,
    GMAIL_ALERT_SOURCES_PATH,
    GMAIL_CREDENTIALS_PATH,
    GMAIL_TOKEN_PATH,
)

router = APIRouter(prefix="/api/backup", tags=["backup"])

_TOP_LEVEL_FILES = [DB_PATH, GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_ALERT_SOURCES_PATH]


@router.get("/export")
def export_backup():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    tmp_path = Path(tmp.name)

    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in _TOP_LEVEL_FILES:
            if p.exists():
                zf.write(p, arcname=p.name)
        if DOCS_DIR.exists():
            for f in DOCS_DIR.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=str(Path("generated_documents") / f.relative_to(DOCS_DIR)))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return FileResponse(
        str(tmp_path),
        filename=f"career-agent-backup-{stamp}.zip",
        media_type="application/zip",
    )


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...)):
    if not (file.filename or "").endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload the .zip file produced by Export.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.write(await file.read())
    tmp.close()
    tmp_path = Path(tmp.name)

    try:
        with zipfile.ZipFile(tmp_path) as zf:
            names = zf.namelist()
            for name in names:
                # Reject path traversal / absolute paths before extracting anything.
                if name.startswith("/") or ".." in Path(name).parts:
                    raise HTTPException(status_code=400, detail=f"Unsafe path in backup file: {name}")
            zf.extractall(DATA_DIR)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="That doesn't look like a valid backup .zip.")
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"status": "restored", "files": names}
