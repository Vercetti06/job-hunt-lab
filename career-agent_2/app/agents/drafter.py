"""The drafter: writes a tailored CV and cover letter for one specific job,
in the candidate's own voice. Also handles revisions based on reviewer feedback."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.agents.llm_client import call_with_tool
from app.models import ApplicationPackage, CoverLetterContent, CVContent, FitEvaluation, JobPosting, Profile

SYSTEM_PROMPT = """You are an elite CV and cover letter writer. You write exclusively in the \
candidate's own authentic voice — using their `personality_notes` and `writing_style_notes` as \
your style guide — and you tailor every document specifically to the one job posting you're \
given. You never write generic, template-sounding copy.

Hard rules:
- Never invent facts, employers, titles, dates, or achievements that aren't in the profile. \
  You may rephrase, reorder, quantify-if-already-implied, and choose emphasis, but the \
  underlying facts must come from the profile.
- Mirror the posting's own language for skills/requirements where the candidate genuinely has \
  that experience (this helps both human readers and applicant tracking systems), but never \
  claim a skill or requirement the candidate doesn't have.
- The CV should foreground whatever the fit evaluation flagged as key points to emphasize for \
  THIS posting — reorder and re-weight bullets accordingly rather than reusing one fixed CV \
  for every job.
- Cover letter: 3-5 short paragraphs, specific to the company and role, in the candidate's \
  voice, no cliché filler ("I am writing to express my interest..."). Open with something \
  concrete and specific, not a throat-clear.
- Keep CV bullets tight, achievement-oriented, and specific — quantify impact wherever the \
  profile supports it.

Always respond by calling the submit_application_package tool with the complete structured CV \
and cover letter — never respond in plain text."""

REVISE_SYSTEM_SUFFIX = """\n\nYou are now REVISING a previous draft based on a reviewer's \
feedback. Address every issue the reviewer raised concretely. Keep what already worked. Still \
never invent facts not present in the profile. Call submit_application_package with the full, \
revised package (not a diff)."""

APPLICATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "cv": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "location": {"type": "string"},
                "links": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string", "description": "2-3 sentence professional summary tailored to this role."},
                "skills": {"type": "array", "items": {"type": "string"}},
                "experience": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "company": {"type": "string"},
                            "location": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "bullets": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["title", "company", "bullets"],
                    },
                },
                "education": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "degree": {"type": "string"},
                            "institution": {"type": "string"},
                            "location": {"type": "string"},
                            "year": {"type": "string"},
                            "details": {"type": "string"},
                        },
                        "required": ["degree", "institution"],
                    },
                },
                "certifications": {"type": "array", "items": {"type": "string"}},
                "projects": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["full_name", "summary", "skills", "experience"],
        },
        "cover_letter": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "contact_line": {"type": "string"},
                "date": {"type": "string"},
                "recipient": {"type": "string"},
                "company": {"type": "string"},
                "salutation": {"type": "string"},
                "paragraphs": {"type": "array", "items": {"type": "string"}},
                "closing": {"type": "string"},
            },
            "required": ["full_name", "salutation", "paragraphs"],
        },
    },
    "required": ["cv", "cover_letter"],
}


def _base_user_content(profile: Profile, job: JobPosting, fit: Optional[FitEvaluation]) -> str:
    fit_block = f"\n\nFIT EVALUATION FOR THIS ROLE:\n{fit.model_dump_json(indent=2)}" if fit else ""
    return (
        f"CANDIDATE PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB POSTING:\nTitle: {job.title}\nCompany: {job.company}\nLocation: {job.location}\n"
        f"Full posting text:\n{job.full_text or job.snippet}"
        f"{fit_block}"
    )


def draft(profile: Profile, job: JobPosting, fit: Optional[FitEvaluation]) -> ApplicationPackage:
    result = call_with_tool(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _base_user_content(profile, job, fit)}],
        tool_name="submit_application_package",
        tool_description="Submit the complete tailored CV and cover letter.",
        tool_schema=APPLICATION_SCHEMA,
        force_tool=True,
        max_tokens=4096,
    )
    if not result.called_tool:
        raise RuntimeError("Drafter did not return a structured result.")
    data = result.tool_input
    return ApplicationPackage(
        cv=CVContent.model_validate(data["cv"]),
        cover_letter=CoverLetterContent.model_validate(data["cover_letter"]),
    )


def revise(
    profile: Profile,
    job: JobPosting,
    fit: Optional[FitEvaluation],
    previous: ApplicationPackage,
    feedback: str,
) -> ApplicationPackage:
    user_content = (
        f"{_base_user_content(profile, job, fit)}\n\n"
        f"PREVIOUS DRAFT:\nCV:\n{previous.cv.model_dump_json(indent=2)}\n\n"
        f"Cover letter:\n{previous.cover_letter.model_dump_json(indent=2)}\n\n"
        f"REVIEWER FEEDBACK TO ADDRESS:\n{feedback}"
    )
    result = call_with_tool(
        system=SYSTEM_PROMPT + REVISE_SYSTEM_SUFFIX,
        messages=[{"role": "user", "content": user_content}],
        tool_name="submit_application_package",
        tool_description="Submit the complete revised CV and cover letter.",
        tool_schema=APPLICATION_SCHEMA,
        force_tool=True,
        max_tokens=4096,
    )
    if not result.called_tool:
        raise RuntimeError("Drafter did not return a structured result during revision.")
    data = result.tool_input
    return ApplicationPackage(
        cv=CVContent.model_validate(data["cv"]),
        cover_letter=CoverLetterContent.model_validate(data["cover_letter"]),
    )
