from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app import storage
from app.auth import BasicAuthMiddleware
from app.config import settings
from app.integrations import gmail_alerts
from app.job_sources import aggregator
from app.routers import apply, interview_prep, profile, search, tracker, companies, clipper, gmail, backup

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Career Agent", version="1.0.0")

# The bookmarklet clipper runs in the context of whatever job-site page you're
# viewing (linkedin.com, indeed.com, etc.) and POSTs back to this local server —
# that's a cross-origin request, so it needs CORS enabled. This server only ever
# binds to 127.0.0.1, so it isn't reachable over the network regardless.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Only enforces anything if BASIC_AUTH_USERNAME/PASSWORD are set in .env —
# see app/auth.py. Added last so it runs first (Starlette applies middleware
# in reverse registration order), rejecting unauthenticated requests before
# they reach CORS or any route/static handling.
app.add_middleware(BasicAuthMiddleware)


@app.exception_handler(RuntimeError)
def runtime_error_handler(request: Request, exc: RuntimeError):
    # Agents raise RuntimeError with clear, user-facing messages (bad API key,
    # network issues, malformed model output, etc.) — surface those as-is
    # instead of a generic 500.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.on_event("startup")
def on_startup() -> None:
    storage.init_db()


@app.get("/api/status")
def status() -> dict:
    return {
        "anthropic_configured": settings.anthropic_configured,
        "job_sources_configured": aggregator.configured_sources(),
        "latex_available": bool(settings.latex_bin_dir) or _latex_on_path(),
        "gmail_authorized": gmail_alerts.is_authorized(),
    }


def _latex_on_path() -> bool:
    import shutil
    return bool(shutil.which("pdflatex") or shutil.which("xelatex"))


app.include_router(profile.router)
app.include_router(search.router)
app.include_router(apply.router)
app.include_router(tracker.router)
app.include_router(interview_prep.router)
app.include_router(companies.router)
app.include_router(clipper.router)
app.include_router(gmail.router)
app.include_router(backup.router)

# Serve the frontend as static files, with index.html as the SPA entrypoint.
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
