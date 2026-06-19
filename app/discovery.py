from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import DATA_DIR, DB_PATH, REPORTS_DIR
from .db import connect, import_companies
from .normalize import normalize_company_name


DISCOVERED_SOURCES_PATH = DATA_DIR / "discovered_target_companies.csv"
DISCOVERY_REPORT_PATH = REPORTS_DIR / "source_discovery.csv"
SUPPORTED_ATS = ("greenhouse", "lever", "ashby", "smartrecruiters")

ROLE_HINTS = (
    "producer",
    "content",
    "creative",
    "marketing",
    "communications",
    "partnership",
    "customer success",
    "account manager",
    "strategy",
    "growth",
)


@dataclass(frozen=True)
class DiscoveredSource:
    name: str
    careers_url: str
    ats_type: str
    ats_identifier: str
    job_count: int
    matched_hint_count: int


def _slug_base(name: str) -> str:
    lowered = name.lower()
    lowered = re.sub(r"\b(limited|ltd|plc|llp|uk|united kingdom|inc|inc\.|services|service|group|holdings|holding|operations|company|co)\b", " ", lowered)
    lowered = re.sub(r"[^a-z0-9]+", "", lowered)
    return lowered.strip()


def _slug_candidates(name: str) -> list[str]:
    base = _slug_base(name)
    if not base:
        return []
    candidates = [base]
    if base.endswith("uk"):
        candidates.append(base[:-2])
    candidates.extend([f"{base}uk", f"{base}careers", f"{base}jobs"])
    seen: set[str] = set()
    clean: list[str] = []
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            clean.append(item)
    return clean[:5]


def _has_relevant_job(payload: object) -> tuple[int, int]:
    text = str(payload).lower()
    count = 0
    if isinstance(payload, dict):
        if isinstance(payload.get("jobs"), list):
            count = len(payload["jobs"])
        elif isinstance(payload.get("postings"), list):
            count = len(payload["postings"])
    elif isinstance(payload, list):
        count = len(payload)
    hints = sum(1 for hint in ROLE_HINTS if hint in text)
    return count, hints


def _probe_greenhouse(client: httpx.Client, name: str, slug: str) -> DiscoveredSource | None:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    response = client.get(url, params={"content": "true"})
    if response.status_code != 200:
        return None
    payload = response.json()
    job_count, hints = _has_relevant_job(payload)
    if job_count <= 0:
        return None
    return DiscoveredSource(name, f"https://boards.greenhouse.io/{slug}", "greenhouse", slug, job_count, hints)


def _probe_lever(client: httpx.Client, name: str, slug: str) -> DiscoveredSource | None:
    url = f"https://api.lever.co/v0/postings/{slug}"
    response = client.get(url, params={"mode": "json"})
    if response.status_code != 200:
        return None
    payload = response.json()
    job_count, hints = _has_relevant_job(payload)
    if job_count <= 0:
        return None
    return DiscoveredSource(name, f"https://jobs.lever.co/{slug}", "lever", slug, job_count, hints)


def _probe_ashby(client: httpx.Client, name: str, slug: str) -> DiscoveredSource | None:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    response = client.get(url)
    if response.status_code != 200:
        return None
    payload = response.json()
    job_count, hints = _has_relevant_job(payload)
    if job_count <= 0:
        return None
    return DiscoveredSource(name, f"https://jobs.ashbyhq.com/{slug}", "ashby", slug, job_count, hints)


def _probe_smartrecruiters(client: httpx.Client, name: str, slug: str) -> DiscoveredSource | None:
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    response = client.get(url)
    if response.status_code != 200:
        return None
    payload = response.json()
    job_count, hints = _has_relevant_job(payload)
    if job_count <= 0:
        return None
    return DiscoveredSource(name, f"https://jobs.smartrecruiters.com/{slug}", "smartrecruiters", slug, job_count, hints)


def _probe_company(client: httpx.Client, name: str) -> DiscoveredSource | None:
    probes = (_probe_greenhouse, _probe_lever, _probe_ashby, _probe_smartrecruiters)
    for slug in _slug_candidates(name):
        for probe in probes:
            try:
                source = probe(client, name, slug)
            except Exception:
                source = None
            if source:
                return source
    return None


def _current_target_names(db_path: Path | str) -> set[str]:
    with connect(db_path) as conn:
        return {row["normalized_name"] for row in conn.execute("SELECT normalized_name FROM companies")}


def _sponsor_names(db_path: Path | str, limit: int) -> list[str]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT organisation_name
            FROM sponsor_register
            WHERE route LIKE '%Skilled Worker%'
            GROUP BY normalized_name
            ORDER BY organisation_name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row["organisation_name"] for row in rows]


def discover_sources(limit: int = 500, db_path: Path | str = DB_PATH) -> list[DiscoveredSource]:
    existing = _current_target_names(db_path)
    names = [name for name in _sponsor_names(db_path, limit) if normalize_company_name(name) not in existing]
    discovered: list[DiscoveredSource] = []
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=8.0, follow_redirects=True, headers={"User-Agent": "uk-sponsored-job-radar/1.0"}) as client:
        for name in names:
            source = _probe_company(client, name)
            if source:
                discovered.append(source)

    DISCOVERED_SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DISCOVERED_SOURCES_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "website", "careers_url", "ats_type", "ats_identifier"])
        writer.writeheader()
        for source in discovered:
            parsed = urlparse(source.careers_url)
            website = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
            writer.writerow(
                {
                    "name": source.name,
                    "website": website,
                    "careers_url": source.careers_url,
                    "ats_type": source.ats_type,
                    "ats_identifier": source.ats_identifier,
                }
            )

    with DISCOVERY_REPORT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "ats_type", "ats_identifier", "job_count", "matched_hint_count", "careers_url"])
        writer.writeheader()
        for source in discovered:
            writer.writerow(source.__dict__)
    return discovered


def import_discovered_sources(path: Path = DISCOVERED_SOURCES_PATH, db_path: Path | str = DB_PATH) -> int:
    if not path.exists():
        return 0
    return import_companies(path, db_path)
