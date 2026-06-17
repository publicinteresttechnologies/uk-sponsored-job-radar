from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .config import UserProfile
from .models import ApplicationPack
from .normalize import clean_text


def _bullet_list(items: list[str], fallback: str) -> str:
    source = items or [fallback]
    return "\n".join(f"- {item}" for item in source)


def _evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("evidence_json") or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return {}


def generate_application_pack(row: Mapping[str, Any], profile: UserProfile) -> ApplicationPack:
    """Create draft application materials using only the profile and posting evidence."""
    evidence = _evidence(row)
    company = clean_text(str(row.get("company_name") or "the company"))
    title = clean_text(str(row.get("title") or "this role"))
    location = clean_text(str(row.get("location") or "Location not specified"))
    salary = clean_text(str(row.get("salary_text") or "Salary not stated"))
    lane_hits = evidence.get("lane_hits", [])
    seniority_hits = evidence.get("seniority_hits", [])
    fit_terms = lane_hits + seniority_hits
    fit_sentence = ", ".join(fit_terms) if fit_terms else "the role's published requirements"

    cv_variant = f"""# {profile.name} - tailored CV notes for {title}

Target role: {title} at {company}
Location: {location}
Salary signal: {salary}
Visa context: {profile.visa_status or profile.visa_goal}; expiry {profile.visa_expiry or "not specified"}

## Positioning Summary
{profile.summary}

## Lead With
{_bullet_list(profile.proof_points, "Use only verified achievements from the master CV.")}

## Relevant Credits
{_bullet_list(profile.credits, "Add only verified programme or employer credits.")}

## Education and Recognition
{_bullet_list(profile.education + profile.awards, "Add only verified education or awards.")}

## Tailoring Notes
- Emphasise fit with: {fit_sentence}.
- Keep all claims evidence-backed; do not add unverified tools, clients, metrics, or UK work authorization claims.
- State that final submission requires human review and manual application.
"""

    cover_letter = f"""Dear hiring team,

I am applying for the {title} role at {company}. My background combines 7+ years in unscripted television and entertainment production in India with MA-level training from the National Film and Television School, and I am now focused on UK roles where creative development, audience judgement, production discipline, and stakeholder communication genuinely overlap.

For this role, I would foreground my experience across {", ".join(profile.credits[:5]) if profile.credits else "major unscripted and entertainment formats"}, along with my strengths in {fit_sentence}. I have worked across fast-moving development and production environments where ideas need to be shaped clearly, sold persuasively, and delivered with practical constraints in mind.

I am seeking Skilled Worker sponsorship before my Graduate Route visa expires on {profile.visa_expiry or "the stated visa expiry date"}. I would welcome the chance to discuss both the role fit and sponsorship feasibility transparently before investing time in later-stage processes.

Kind regards,
{profile.name}
"""

    recruiter_note = f"""Hi,

I found the {title} role at {company} and wanted to ask whether the team is open to Skilled Worker sponsorship for a strong-fit candidate. I am on a UK Graduate Route visa expiring {profile.visa_expiry or "soon"} and have 7+ years in unscripted TV / entertainment production, including {", ".join(profile.credits[:4]) if profile.credits else "major entertainment formats"}, plus an NFTS MA in Television Entertainment.

If sponsorship is feasible, I would be keen to share a tailored CV and discuss the role.

Best,
{profile.name}
"""

    screening_answers = f"""# Screening Answer Drafts

## Do you require visa sponsorship?
Yes. I am currently on a UK Graduate Route visa expiring {profile.visa_expiry or "on the date stated in my CV"} and would require Skilled Worker sponsorship to continue working in the UK after that point.

## Why are you interested in this role?
The role appears aligned with {fit_sentence}, and I can bring a mix of unscripted entertainment production experience, creative development judgement, and cross-functional communication.

## What relevant experience do you bring?
{profile.summary}

## Human Review Checklist
- Confirm the employer is on the sponsor register.
- Confirm salary/SOC viability has not changed.
- Confirm the posting is still live on the official company/ATS source.
- Review every generated sentence against the master CV before manual submission.
- Submit manually only; this tool must not auto-submit applications.
"""

    return ApplicationPack(
        job_id=int(row["id"]),
        cv_variant_markdown=cv_variant,
        cover_letter_markdown=cover_letter,
        recruiter_note_markdown=recruiter_note,
        screening_answers_markdown=screening_answers,
    )
