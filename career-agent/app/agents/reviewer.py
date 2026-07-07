"""The reviewer: a second, independent pass that critiques the drafter's work
before it ever reaches the user. This is the second half of the
drafter -> reviewer -> (revise) loop."""
from __future__ import annotations

from typing import Any, Dict

from app.agents.llm_client import call_with_tool
from app.models import ApplicationPackage, FitEvaluation, JobPosting, Profile, ReviewFeedback

SYSTEM_PROMPT = """You are a skeptical, detail-obsessed editor reviewing a CV and cover letter \
that a colleague just drafted for a candidate applying to a specific job. You did not write \
these documents and have no attachment to them — your job is to find every real problem before \
the candidate sees this.

Check specifically for:
1. Fabrication or overreach: does anything in the CV/cover letter claim something not supported \
   by the candidate's profile? This is the most serious category of issue.
2. Genuine tailoring: does this actually read as written for THIS posting, or could it be sent \
   to any job in the field? Generic phrasing that ignores specifics of the posting is a problem.
3. Voice: does it sound like the candidate's own voice (per their writing_style_notes / \
   personality_notes), or like generic corporate cover-letter boilerplate ("I am excited to \
   apply...", "I believe I would be a great fit...")? Flag cliché phrases specifically.
4. Clarity and impact: are CV bullets specific and achievement-oriented, or vague duty lists? \
   Is the cover letter concise (not bloated) and does it open with something concrete rather \
   than a throat-clearing opener?
5. Basic correctness: obvious typos, inconsistent dates, missing required fields.

Set approved=true only if the documents are genuinely strong and ready to send with no more than \
minor, optional polish. If you set approved=false, `issues` must be a concrete, actionable list \
— each one specific enough that a writer could fix it without guessing what you meant. Always \
call submit_review — never respond in plain text."""

REVIEW_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "overall_comment": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific, actionable issues the drafter should fix. Empty if approved with no notes.",
        },
    },
    "required": ["approved", "overall_comment"],
}


def review(profile: Profile, job: JobPosting, fit: FitEvaluation, package: ApplicationPackage) -> ReviewFeedback:
    user_content = (
        f"CANDIDATE PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB POSTING:\nTitle: {job.title}\nCompany: {job.company}\n"
        f"Full posting text:\n{job.full_text or job.snippet}\n\n"
        f"FIT EVALUATION:\n{fit.model_dump_json(indent=2)}\n\n"
        f"DRAFT CV:\n{package.cv.model_dump_json(indent=2)}\n\n"
        f"DRAFT COVER LETTER:\n{package.cover_letter.model_dump_json(indent=2)}"
    )
    result = call_with_tool(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        tool_name="submit_review",
        tool_description="Submit the structured review.",
        tool_schema=REVIEW_SCHEMA,
        force_tool=True,
        max_tokens=2048,
    )
    if not result.called_tool:
        raise RuntimeError("Reviewer did not return a structured result.")
    return ReviewFeedback.model_validate(result.tool_input)
