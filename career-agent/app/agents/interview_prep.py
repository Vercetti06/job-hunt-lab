"""Generates interview prep material for a specific application."""
from __future__ import annotations

from typing import Any, Dict

from app.agents.llm_client import call_with_tool
from app.models import FitEvaluation, JobPosting, Profile

SYSTEM_PROMPT = """You are an experienced interview coach preparing a candidate for a specific \
interview. Use their profile and the job posting to produce genuinely useful, specific prep — \
not generic interview advice. Base likely questions on what this specific posting emphasizes and \
on any gaps identified in the fit evaluation (interviewers probe gaps). Suggested talking points \
should reference the candidate's actual real experience from their profile, not invented \
anecdotes. Always call submit_interview_prep."""

PREP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "likely_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "why_theyll_ask_this": {"type": "string"},
                    "suggested_talking_points": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["question", "suggested_talking_points"],
            },
        },
        "questions_to_ask_them": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Smart questions the candidate should ask the interviewer, specific to this role/company.",
        },
        "gaps_to_address_proactively": {
            "type": "array",
            "items": {"type": "string"},
            "description": "How to frame any gaps from the fit evaluation if they come up.",
        },
        "company_specific_notes": {"type": "string"},
    },
    "required": ["likely_questions", "questions_to_ask_them"],
}


def generate(profile: Profile, job: JobPosting, fit: FitEvaluation) -> Dict[str, Any]:
    user_content = (
        f"CANDIDATE PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB POSTING:\nTitle: {job.title}\nCompany: {job.company}\n"
        f"Full posting text:\n{job.full_text or job.snippet}\n\n"
        f"FIT EVALUATION:\n{fit.model_dump_json(indent=2)}"
    )
    result = call_with_tool(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        tool_name="submit_interview_prep",
        tool_description="Submit the structured interview prep material.",
        tool_schema=PREP_SCHEMA,
        force_tool=True,
        max_tokens=3000,
    )
    if not result.called_tool:
        raise RuntimeError("Interview prep agent did not return a structured result.")
    return result.tool_input
