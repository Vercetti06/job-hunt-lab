"""Orchestrates the full apply pipeline: fit evaluation -> drafter -> reviewer
-> revise (repeat up to max_rounds) -> final package."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.agents import drafter, reviewer
from app.agents.fit_evaluator import evaluate as evaluate_fit
from app.models import ApplicationPackage, FitEvaluation, JobPosting, Profile

MAX_REVIEW_ROUNDS = 3


@dataclass
class PipelineResult:
    fit: FitEvaluation
    package: ApplicationPackage
    rounds: int
    approved: bool
    review_log: List[str] = field(default_factory=list)


def run_apply_pipeline(profile: Profile, job: JobPosting) -> PipelineResult:
    fit = evaluate_fit(profile, job)

    package = drafter.draft(profile, job, fit)
    review_log: List[str] = []
    approved = False

    for round_num in range(1, MAX_REVIEW_ROUNDS + 1):
        feedback = reviewer.review(profile, job, fit, package)
        review_log.append(
            f"Round {round_num}: {'APPROVED' if feedback.approved else 'NEEDS REVISION'} — "
            f"{feedback.overall_comment}"
        )
        if feedback.approved:
            approved = True
            break
        if round_num == MAX_REVIEW_ROUNDS:
            # Out of rounds — ship the last draft, but be honest about it below.
            break
        issues_text = "\n".join(f"- {i}" for i in feedback.issues) or feedback.overall_comment
        package = drafter.revise(profile, job, fit, package, issues_text)

    return PipelineResult(
        fit=fit,
        package=package,
        rounds=len(review_log),
        approved=approved,
        review_log=review_log,
    )
