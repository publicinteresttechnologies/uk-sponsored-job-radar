from __future__ import annotations

import requests

from app.models import Company, Job, utc_now_iso
from app.normalize import clean_text, extract_salary_range, make_dedupe_key, normalize_title


def fetch_lever_jobs(company: Company) -> list[Job]:
    if not company.id or not company.ats_identifier:
        return []
    url = f"https://api.lever.co/v0/postings/{company.ats_identifier}"
    response = requests.get(url, params={"mode": "json"}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    jobs: list[Job] = []
    now = utc_now_iso()
    for item in payload:
        title = clean_text(item.get("text"))
        categories = item.get("categories") or {}
        location = clean_text(categories.get("location"))
        description = clean_text(" ".join([item.get("descriptionPlain") or "", item.get("additionalPlain") or ""]))
        salary_text = clean_text(" ".join([description, str(item.get("salaryDescription") or "")]))
        min_salary, max_salary, currency = extract_salary_range(salary_text)
        hosted_url = item.get("hostedUrl") or item.get("applyUrl")
        jobs.append(
            Job(
                company_id=company.id,
                source="lever",
                ats_type="lever",
                external_job_id=str(item.get("id") or ""),
                title=title,
                normalized_title=normalize_title(title),
                location=location,
                salary_text=salary_text if currency else None,
                min_salary=min_salary,
                max_salary=max_salary,
                currency=currency or "GBP",
                employment_type=categories.get("commitment"),
                url=hosted_url,
                description=description,
                first_seen_at=now,
                last_seen_at=now,
                is_live=True,
                dedupe_key=make_dedupe_key(company.name, title, location, str(item.get("id") or ""), hosted_url),
            )
        )
    return jobs
