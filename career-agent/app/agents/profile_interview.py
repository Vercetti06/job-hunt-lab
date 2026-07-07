"""The onboarding agent: interviews the user conversationally and produces a
structured Profile once it has enough to work with."""
from __future__ import annotations

from typing import Any, Dict, List

from app.agents.llm_client import call_with_tool
from app.models import Profile

SYSTEM_PROMPT = """You are an experienced career coach and executive recruiter conducting an \
intake interview with a new client. Your job is to build a rich, structured profile of them \
so that, later, a *different* writing process can produce genuinely tailored, specific CVs and \
cover letters on their behalf — so vague answers are much less useful to you than concrete ones.

Cover all of the following areas over the course of the conversation, roughly in this order, \
but adapt naturally to what they tell you (don't be a rigid form):
1. Basic contact info: full name, email, phone, location, and any relevant links (LinkedIn, \
   portfolio, GitHub, etc).
2. Work history: for each relevant role, get title, company, location, dates, and — most \
   importantly — 2-5 concrete achievements or responsibilities, ideally with numbers/impact, \
   not just duty lists. Push gently for specifics ("what changed because you did that?").
3. Skills: technical and soft skills that are actually relevant to what they want next, not an \
   undifferentiated list.
4. Education, certifications, notable projects.
5. Career goals: what roles/titles/industries they're targeting next and why, and any hard \
   constraints (remote/hybrid/onsite, relocation, salary expectations, visa status if relevant).
6. Personality and voice: how they'd describe their working style and personality (e.g. \
   direct and data-driven, warm and collaborative, scrappy generalist, deep specialist), and \
   how they write/talk — so future documents can sound like *them*, not like generic corporate \
   copy. A good trick: ask them to describe themselves in their own words, or paste a snippet \
   of something they've written.

Ask ONE focused question at a time — never a big multi-part questionnaire in one message. Keep \
each question short and conversational. Acknowledge what they just told you briefly before \
asking the next thing, so it feels like a conversation, not a form.

Once you have genuinely enough to write a strong, specific CV and cover letter later (at least \
one detailed role with real achievements, a skills list, education, and a clear sense of their \
goals and voice), call the submit_profile tool with the complete structured profile. Do not call \
it prematurely with thin, generic content — but also don't drag the interview out once you have \
enough; aim for a thorough but efficient interview (typically 10-20 exchanges). If the user says \
something like "that's everything" or "let's finish up", wrap up with what you have rather than \
insisting on more.

Never ask more than one question per message. Never call submit_profile and ask a question in \
the same turn — either ask the next question, or finalize."""

PROFILE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "location": {"type": "string"},
        "links": {"type": "array", "items": {"type": "string"}},
        "headline": {"type": "string", "description": "One-line professional headline, e.g. 'Senior Product Manager, B2B SaaS'"},
        "career_goals": {"type": "string"},
        "target_roles": {"type": "array", "items": {"type": "string"}},
        "target_industries": {"type": "array", "items": {"type": "string"}},
        "work_preferences": {"type": "string", "description": "Remote/hybrid/onsite, relocation willingness, salary range, visa constraints, etc."},
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
                    "achievements": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "company", "achievements"],
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
        "personality_notes": {"type": "string"},
        "writing_style_notes": {"type": "string"},
        "raw_notes": {"type": "string", "description": "Anything useful that doesn't fit elsewhere."},
    },
    "required": ["full_name", "skills", "experience"],
}


def step(history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Advance the interview by one turn.

    `history` is a list of {"role": "user"|"assistant", "content": str}.
    Returns either {"done": False, "question": str} or {"done": True, "profile": Profile}.
    """
    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    if not messages:
        messages = [{"role": "user", "content": "Hi, I'm ready to get started."}]

    result = call_with_tool(
        system=SYSTEM_PROMPT,
        messages=messages,
        tool_name="submit_profile",
        tool_description="Submit the final, structured profile once the interview has gathered enough detail.",
        tool_schema=PROFILE_SCHEMA,
        max_tokens=4096,
    )

    if result.called_tool:
        data = dict(result.tool_input)
        data["is_complete"] = True
        profile = Profile.model_validate(data)
        return {"done": True, "profile": profile}

    question = result.text.strip() or "Could you tell me more about your work history?"
    return {"done": False, "question": question}
