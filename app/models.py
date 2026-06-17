from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Decision(StrEnum):
    APPLY = "APPLY"
    HOLD = "HOLD"
    REJECT = "REJECT"


class ApplicationStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    PACK_GENERATED = "PACK_GENERATED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    READY_TO_SUBMIT = "READY_TO_SUBMIT"
    SUBMITTED_MANUALLY = "SUBMITTED_MANUALLY"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class Company(BaseModel):
    id: int | None = None
    name: str
    normalized_name: str
    website: str | None = None
    careers_url: str | None = None
    ats_type: str | None = None
    ats_identifier: str | None = None
    sponsor_status: str | None = None
    sponsor_rating: str | None = None
    sponsor_routes: str | None = None
    last_checked_at: str | None = None


class Job(BaseModel):
    id: int | None = None
    company_id: int
    source: str
    ats_type: str | None = None
    external_job_id: str | None = None
    title: str
    normalized_title: str
    location: str | None = None
    remote_policy: str | None = None
    salary_text: str | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    currency: str | None = "GBP"
    employment_type: str | None = None
    url: HttpUrl | str
    description: str | None = None
    first_seen_at: str = Field(default_factory=utc_now_iso)
    last_seen_at: str = Field(default_factory=utc_now_iso)
    is_live: bool = True
    dedupe_key: str


class JobScore(BaseModel):
    job_id: int
    official_posting_score: int
    sponsor_score: int
    salary_score: int
    soc_score: int
    cv_fit_score: int
    sponsorship_language_score: int
    total_score: int
    decision: Decision
    rejection_reason: str | None = None
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    scored_at: str = Field(default_factory=utc_now_iso)


class ApplicationPack(BaseModel):
    job_id: int
    generated_at: str = Field(default_factory=utc_now_iso)
    cv_variant_markdown: str
    cover_letter_markdown: str
    recruiter_note_markdown: str
    screening_answers_markdown: str


class ApplicationTracker(BaseModel):
    job_id: int
    status: ApplicationStatus = ApplicationStatus.NOT_STARTED
    priority: str | None = None
    next_action: str | None = None
    deadline: str | None = None
    notes: str | None = None
    last_updated_at: str = Field(default_factory=utc_now_iso)
