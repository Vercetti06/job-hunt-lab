"""Evaluates how well a specific job posting fits the user's profile."""
from __future__ import annotations

from typing import Any, Dict

from app.agents.llm_client import call_with_tool
from app.models import FitEvaluation, JobPosting, Profile

SYSTEM_PROMPT = """You are a blunt, experienced hiring-side recruiter who now works exclusively \
for the candidate. You will be shown a candidate's profile and a specific job posting. Give an \
honest, calibrated assessment of fit — you are not trying to be encouraging, you are trying to \
save the candidate time and help them apply where they actually have a shot, or where the role \
matters enough to be worth a stretch application.

Be specific: point to the actual language of the posting and the actual content of the profile. \
Avoid generic praise or generic concern. A score of 90+ should be rare and mean "this posting \
reads like it was written for this person." A score under 40 means don't bother unless there's \
a compelling reason. Always call the submit_fit_evaluation tool with your assessment — do not \
respond in plain text."""

FIT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "verdict": {"type": "string", "description": "One sentence, direct verdict."},
        "strengths": {"type": "array", "items": {"type": "string"}, "description": "Specific ways the profile matches this specific posting."},
        "gaps": {"type": "array", "items": {"type": "string"}, "description": "Specific gaps or risks relative to this posting."},
        "recommendation": {"type": "string", "enum": ["apply", "apply-with-caveats", "skip"]},
        "key_points_to_emphasize": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific experiences/skills from the profile that should be foregrounded when writing the CV and cover letter for this posting.",
        },
    },
    "required": ["fit_score", "verdict", "recommendation"],
}


def evaluate(profile: Profile, job: JobPosting) -> FitEvaluation:
    user_content = (
        f"CANDIDATE PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB POSTING:\nTitle: {job.title}\nCompany: {job.company}\nLocation: {job.location}\n"
        f"URL: {job.url}\n\nFull posting text:\n{job.full_text or job.snippet}"
    )
    result = call_with_tool(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        tool_name="submit_fit_evaluation",
        tool_description="Submit the structured fit evaluation.",
        tool_schema=FIT_SCHEMA,
        force_tool=True,
        max_tokens=2048,
    )
    if not result.called_tool:
        raise RuntimeError("Fit evaluator did not return a structured result.")
    return FitEvaluation.model_validate(result.tool_input)
