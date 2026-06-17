from __future__ import annotations

import requests

from app.models import Company, Job, utc_now_iso
from app.normalize import clean_text, extract_salary_range, make_dedupe_key, normalize_title


def _location(value: dict | None) -> str | None:
    if not value:
        return None
    return value.get("name")


def fetch_greenhouse_jobs(company: Company) -> list[Job]:
    if not company.id or not company.ats_identifier:
        return []
    url = f"https://boards-api.greenhouse.io/v1/boards/{company.ats_identifier}/jobs"
    response = requests.get(url, params={"content": "true"}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    jobs: list[Job] = []
    now = utc_now_iso()
    for item in payload.get("jobs", []):
        title = clean_text(item.get("title"))
        absolute_url = item.get("absolute_url") or item.get("url")
        description = clean_text(item.get("content"))
        salary_text = clean_text(" ".join([description[:2000], str(item.get("metadata") or "")]))
        min_salary, max_salary, currency = extract_salary_range(salary_text)
        location = _location(item.get("location"))
        jobs.append(
            Job(
                company_id=company.id,
                source="greenhouse",
                ats_type="greenhouse",
                external_job_id=str(item.get("id") or ""),
                title=title,
                normalized_title=normalize_title(title),
                location=location,
                salary_text=salary_text if currency else None,
                min_salary=min_salary,
                max_salary=max_salary,
                currency=currency or "GBP",
                employment_type=None,
                url=absolute_url,
                description=description,
                first_seen_at=now,
                last_seen_at=now,
                is_live=True,
                dedupe_key=make_dedupe_key(company.name, title, location, str(item.get("id") or ""), absolute_url),
            )
        )
    return jobs
