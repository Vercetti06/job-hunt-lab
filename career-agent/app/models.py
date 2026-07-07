"""Shared data models."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class WorkExperience(BaseModel):
    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    achievements: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str
    institution: str
    location: str = ""
    year: str = ""
    details: str = ""


class Profile(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List[str] = Field(default_factory=list)

    headline: str = ""
    career_goals: str = ""
    target_roles: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    work_preferences: str = ""  # remote/hybrid/onsite, relocation, salary range, etc.

    skills: List[str] = Field(default_factory=list)
    experience: List[WorkExperience] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)

    personality_notes: str = ""      # how they come across, values, work style
    writing_style_notes: str = ""    # tone/voice to use when writing on their behalf
    raw_notes: str = ""              # anything else captured during the interview

    is_complete: bool = False


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class JobPosting(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    source: str = ""
    salary: str = ""
    posted_date: str = ""
    snippet: str = ""
    full_text: str = ""
    keyword_score: Optional[float] = None


class WatchedCompany(BaseModel):
    id: Optional[int] = None
    name: str = ""
    ats_type: str = ""  # greenhouse / lever / ashby / smartrecruiters
    slug: str = ""       # the company's board token/slug on that ATS
    created_at: str = ""


class FitEvaluation(BaseModel):
    fit_score: int  # 0-100
    verdict: str    # one-line verdict
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendation: str  # apply / apply-with-caveats / skip
    key_points_to_emphasize: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class CVExperienceEntry(BaseModel):
    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    bullets: List[str] = Field(default_factory=list)


class CVEducationEntry(BaseModel):
    degree: str
    institution: str
    location: str = ""
    year: str = ""
    details: str = ""


class CVContent(BaseModel):
    full_name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List[str] = Field(default_factory=list)
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[CVExperienceEntry] = Field(default_factory=list)
    education: List[CVEducationEntry] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)


class CoverLetterContent(BaseModel):
    full_name: str
    contact_line: str = ""
    date: str = ""
    recipient: str = ""
    company: str = ""
    salutation: str = "Dear Hiring Manager,"
    paragraphs: List[str] = Field(default_factory=list)
    closing: str = "Sincerely,"


class ReviewFeedback(BaseModel):
    approved: bool
    overall_comment: str
    issues: List[str] = Field(default_factory=list)


class ApplicationPackage(BaseModel):
    cv: CVContent
    cover_letter: CoverLetterContent
    review_rounds: int = 0
    final_review_comment: str = ""


# ---------------------------------------------------------------------------
# Application tracker
# ---------------------------------------------------------------------------

class Application(BaseModel):
    id: Optional[int] = None
    job_title: str = ""
    company: str = ""
    job_url: str = ""
    job_full_text: str = ""
    status: str = "drafted"  # drafted / applied / interviewing / offer / rejected / withdrawn
    fit_score: Optional[int] = None
    fit_json: str = ""
    cv_docx_path: str = ""
    cv_tex_path: str = ""
    cv_pdf_path: str = ""
    cover_letter_docx_path: str = ""
    cover_letter_tex_path: str = ""
    cover_letter_pdf_path: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
