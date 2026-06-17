from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = BASE_DIR / "sponsor_jobs.sqlite3"
REPORTS_DIR = BASE_DIR / "reports"


class UserProfile(BaseModel):
    name: str = "Karan Dhar"
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    target_country: str = "UK"
    visa_goal: str = "Skilled Worker sponsorship"
    visa_status: str | None = None
    visa_expiry: str | None = None
    minimum_salary_general: int = 41700
    summary: str = ""
    proof_points: list[str] = Field(default_factory=list)
    credits: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    preferred_lanes: list[str] = Field(default_factory=list)
    hard_reject_phrases: list[str] = Field(default_factory=list)
    strong_sponsorship_phrases: list[str] = Field(default_factory=list)
    seniority_keywords: list[str] = Field(default_factory=list)


def load_user_profile(path: Path | str | None = None) -> UserProfile:
    profile_path = Path(path) if path else DATA_DIR / "user_profile.example.yaml"
    with profile_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    return UserProfile(**raw)
