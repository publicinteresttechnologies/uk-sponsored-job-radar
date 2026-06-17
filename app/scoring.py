from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import UserProfile
from .models import Decision, JobScore
from .normalize import normalize_text


OFFICIAL_ATS = {"greenhouse", "lever", "ashby", "smartrecruiters", "generic_careers"}


def contains_any(text: str, phrases: list[str]) -> list[str]:
    normalized = normalize_text(text)
    return [phrase for phrase in phrases if normalize_text(phrase) in normalized]


def score_job(row: Mapping[str, Any], profile: UserProfile) -> JobScore:
    title = str(row.get("title") or "")
    description = str(row.get("description") or "")
    salary_text = str(row.get("salary_text") or "")
    combined = " ".join([title, description, salary_text])

    ats_type = str(row.get("ats_type") or "").lower()
    source = str(row.get("source") or "").lower()
    official_posting_score = 10 if ats_type in OFFICIAL_ATS and source in OFFICIAL_ATS else 0

    sponsor_status = str(row.get("sponsor_status") or "")
    sponsor_rating = str(row.get("sponsor_rating") or "")
    sponsor_routes = str(row.get("sponsor_routes") or "")
    sponsor_score = 0
    if sponsor_status == "matched":
        sponsor_score = 8
        if "a" in sponsor_rating.casefold():
            sponsor_score = 10
        if "skilled worker" in sponsor_routes.casefold():
            sponsor_score = min(10, sponsor_score + 1)

    min_salary = row.get("min_salary")
    max_salary = row.get("max_salary")
    salary_score = 5
    if min_salary is not None or max_salary is not None:
        best_salary = int(max_salary or min_salary or 0)
        floor_salary = int(min_salary or max_salary or 0)
        if best_salary < profile.minimum_salary_general:
            salary_score = 0
        elif floor_salary >= profile.minimum_salary_general:
            salary_score = 10
        else:
            salary_score = 7

    lane_hits = contains_any(combined, profile.preferred_lanes)
    seniority_hits = contains_any(combined, profile.seniority_keywords)
    cv_fit_score = min(10, len(lane_hits) * 3 + len(seniority_hits) * 2)

    soc_terms = [
        "producer",
        "communications manager",
        "marketing manager",
        "public relations",
        "research",
        "creative director",
        "content strategist",
        "partnerships manager",
    ]
    soc_hits = contains_any(combined, soc_terms)
    soc_score = min(10, 4 + len(soc_hits) * 2) if soc_hits else 3

    hard_reject_hits = contains_any(combined, profile.hard_reject_phrases)
    strong_sponsorship_hits = contains_any(combined, profile.strong_sponsorship_phrases)
    sponsorship_language_score = 9 if strong_sponsorship_hits else 5
    if hard_reject_hits:
        sponsorship_language_score = 0

    total_score = (
        official_posting_score
        + sponsor_score
        + salary_score
        + soc_score
        + cv_fit_score
        + sponsorship_language_score
    )

    decision = Decision.REJECT
    rejection_reason: str | None = "Insufficient match"
    if sponsor_score == 0:
        rejection_reason = "Company not matched to licensed sponsor register"
    elif official_posting_score < 8:
        rejection_reason = "Not verified as an official company or ATS posting"
    elif salary_score == 0:
        rejection_reason = f"Salary appears below GBP {profile.minimum_salary_general}"
    elif hard_reject_hits:
        rejection_reason = "Posting contains hard visa sponsorship rejection language"
    elif sponsor_score >= 7 and salary_score >= 6 and cv_fit_score >= 7 and official_posting_score >= 8:
        decision = Decision.APPLY
        rejection_reason = None
    elif cv_fit_score >= 7 and (salary_score == 5 or sponsorship_language_score == 5):
        decision = Decision.HOLD
        rejection_reason = "Strong CV fit but salary or sponsorship language is unclear"

    return JobScore(
        job_id=int(row["id"]),
        official_posting_score=official_posting_score,
        sponsor_score=sponsor_score,
        salary_score=salary_score,
        soc_score=soc_score,
        cv_fit_score=cv_fit_score,
        sponsorship_language_score=sponsorship_language_score,
        total_score=total_score,
        decision=decision,
        rejection_reason=rejection_reason,
        evidence_json={
            "lane_hits": lane_hits,
            "seniority_hits": seniority_hits,
            "soc_hits": soc_hits,
            "hard_reject_hits": hard_reject_hits,
            "strong_sponsorship_hits": strong_sponsorship_hits,
            "salary_text": salary_text,
            "sponsor_rating": sponsor_rating,
            "sponsor_routes": sponsor_routes,
        },
    )
