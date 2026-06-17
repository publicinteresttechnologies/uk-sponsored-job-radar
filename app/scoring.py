from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import UserProfile
from .models import Decision, JobScore
from .normalize import normalize_text


OFFICIAL_ATS = {"greenhouse", "lever", "ashby", "smartrecruiters", "generic_careers"}

TITLE_FIT_TERMS = [
    "producer",
    "development producer",
    "content",
    "creative",
    "partnership",
    "communications",
    "public relations",
    "marketing",
    "editorial",
    "strategy",
    "customer success",
    "account manager",
    "commercial",
    "growth",
    "gtm",
]

EXTRA_FIT_TERMS = [
    "producer",
    "senior producer",
    "development producer",
    "creative producer",
    "content producer",
    "branded content",
    "content strategy",
    "creative strategy",
    "editorial",
    "communications",
    "public relations",
    "campaign",
    "account manager",
    "customer success",
    "entertainment",
    "television",
    "factual",
    "unscripted",
]

LOW_FIT_TERMS = [
    "software engineer",
    "frontend engineer",
    "backend engineer",
    "full stack engineer",
    "machine learning engineer",
    "data engineer",
    "legal counsel",
    "lawyer",
    "retail",
    "store",
    "genius bar",
    "warehouse",
    "driver",
    "internship",
    "apprenticeship",
    "risk management",
    "controls",
    "compliance",
    "financial crime",
    "audit",
    "sales development representative",
]

SOC_BACKED_EMPLOYER_TERMS: dict[str, list[str]] = {
    "braze limited": [
        "customer success",
        "account manager",
        "technical account manager",
        "client",
        "commercial",
        "growth",
        "marketing",
        "partnership",
        "communications",
    ],
    "contentful ltd": [
        "customer success",
        "account executive",
        "account manager",
        "commercial",
        "content",
        "marketing",
        "partnership",
        "growth",
    ],
    "monzo bank limited": [
        "content",
        "marketing",
        "communications",
        "customer success",
        "growth",
        "partnership",
    ],
    "synthesia limited": [
        "content",
        "creative",
        "customer success",
        "marketing",
        "partnership",
        "account manager",
    ],
    "canva uk operations limited": [
        "content",
        "creative",
        "marketing",
        "partnership",
        "customer success",
    ],
    "paddle.com market limited": [
        "customer success",
        "account manager",
        "commercial",
        "growth",
        "marketing",
        "partnership",
    ],
}

UK_LOCATION_TERMS = [
    "uk",
    "united kingdom",
    "london",
    "cardiff",
    "manchester",
    "bristol",
    "birmingham",
    "leeds",
    "edinburgh",
    "glasgow",
    "cambridge",
    "oxford",
    "reading",
    "remote uk",
    "remote (uk)",
    "england",
    "scotland",
    "northern ireland",
]

STRONG_UK_LOCATION_TERMS = UK_LOCATION_TERMS

NON_UK_LOCATION_TERMS = [
    "australia",
    "new south wales",
    "new wales",
    "sydney",
    "singapore",
    "berlin",
    "madrid",
    "paris",
    "chicago",
    "austin",
    "san francisco",
    "new york",
    "sao paulo",
    "são paulo",
    "latam",
    "india",
    "bengaluru",
    "bangalore",
    "dublin",
    "amsterdam",
    "germany",
    "france",
    "spain",
    "united states",
    "usa",
    "canada",
]


def contains_any(text: str, phrases: list[str]) -> list[str]:
    normalized = normalize_text(text)
    return [phrase for phrase in phrases if normalize_text(phrase) in normalized]


def score_job(row: Mapping[str, Any], profile: UserProfile) -> JobScore:
    company_name = str(row.get("company_name") or "")
    normalized_company_name = normalize_text(company_name)
    title = str(row.get("title") or "")
    location = str(row.get("location") or "")
    description = str(row.get("description") or "")
    salary_text = str(row.get("salary_text") or "")
    combined = " ".join([title, location, description, salary_text])

    title_hits = contains_any(title, TITLE_FIT_TERMS)
    uk_location_hits = contains_any(location, UK_LOCATION_TERMS)
    strong_uk_location_hits = contains_any(location, STRONG_UK_LOCATION_TERMS)
    non_uk_location_hits = contains_any(location, NON_UK_LOCATION_TERMS)
    is_clearly_non_uk = bool(non_uk_location_hits and not strong_uk_location_hits)
    is_uk_or_unclear = bool(strong_uk_location_hits) or not location.strip()

    soc_backed_terms = SOC_BACKED_EMPLOYER_TERMS.get(normalized_company_name, [])
    soc_backed_hits = contains_any(" ".join([title, description]), soc_backed_terms)
    has_soc_backed_signal = bool(soc_backed_hits)

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
    extra_fit_hits = contains_any(combined, EXTRA_FIT_TERMS)
    low_fit_hits = contains_any(combined, LOW_FIT_TERMS)
    cv_fit_score = min(10, len(lane_hits) * 3 + len(seniority_hits) * 2 + len(extra_fit_hits) + len(title_hits) * 2)
    if has_soc_backed_signal:
        cv_fit_score = min(10, cv_fit_score + 2)
    if low_fit_hits:
        cv_fit_score = max(0, cv_fit_score - 7)
    if not title_hits and not has_soc_backed_signal:
        cv_fit_score = min(cv_fit_score, 5)

    soc_terms = [
        "producer",
        "communications manager",
        "marketing manager",
        "public relations",
        "creative director",
        "content strategist",
        "partnerships manager",
        "account manager",
        "customer success",
        "commercial manager",
    ]
    soc_hits = contains_any(combined, soc_terms)
    soc_score = min(10, 4 + len(soc_hits) * 2) if soc_hits else 3
    if has_soc_backed_signal:
        soc_score = max(soc_score, 7)

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
    if is_clearly_non_uk:
        rejection_reason = "Role location is outside the UK"
    elif sponsor_score == 0:
        rejection_reason = "Company not matched to licensed sponsor register"
    elif official_posting_score < 8:
        rejection_reason = "Not verified as an official company or ATS posting"
    elif salary_score == 0:
        rejection_reason = f"Salary appears below GBP {profile.minimum_salary_general}"
    elif hard_reject_hits:
        rejection_reason = "Posting contains hard visa sponsorship rejection language"
    elif low_fit_hits and cv_fit_score < 6:
        rejection_reason = "Role appears outside target lanes"
    elif sponsor_score >= 7 and salary_score >= 6 and cv_fit_score >= 8 and official_posting_score >= 8 and title_hits and is_uk_or_unclear:
        decision = Decision.APPLY
        rejection_reason = None
    elif sponsor_score >= 7 and official_posting_score >= 8 and cv_fit_score >= 6 and salary_score >= 5 and title_hits and is_uk_or_unclear:
        decision = Decision.HOLD
        rejection_reason = "Sponsor matched and title/CV fit is plausible, but salary or sponsorship language needs human verification"
    elif sponsor_score >= 7 and official_posting_score >= 8 and salary_score >= 5 and has_soc_backed_signal and is_uk_or_unclear:
        decision = Decision.HOLD
        rejection_reason = "SOC-backed HOLD: employer pattern and role family justify manual sponsorship check"

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
            "company_name": company_name,
            "title_hits": title_hits,
            "soc_backed_hits": soc_backed_hits,
            "has_soc_backed_signal": has_soc_backed_signal,
            "uk_location_hits": uk_location_hits,
            "strong_uk_location_hits": strong_uk_location_hits,
            "non_uk_location_hits": non_uk_location_hits,
            "lane_hits": lane_hits,
            "seniority_hits": seniority_hits,
            "extra_fit_hits": extra_fit_hits,
            "low_fit_hits": low_fit_hits,
            "soc_hits": soc_hits,
            "hard_reject_hits": hard_reject_hits,
            "strong_sponsorship_hits": strong_sponsorship_hits,
            "salary_text": salary_text,
            "sponsor_rating": sponsor_rating,
            "sponsor_routes": sponsor_routes,
        },
    )
