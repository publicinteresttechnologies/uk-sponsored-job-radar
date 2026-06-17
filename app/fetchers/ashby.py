from __future__ import annotations

import requests

from app.models import Company, Job, utc_now_iso
from app.normalize import clean_text, extract_salary_range, make_dedupe_key, normalize_title


def fetch_ashby_jobs(company: Company) -> list[Job]:
    if not company.id or not company.ats_identifier:
        return []
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company.ats_identifier}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    jobs: list[Job] = []
    now = utc_now_iso()
    for item in payload.get("jobs", []):
        title = clean_text(item.get("title"))
        location_payload = item.get("location")
        location = clean_text(location_payload.get("name") if isinstance(location_payload, dict) else location_payload)
        description = clean_text(item.get("descriptionHtml") or item.get("descriptionPlain"))
        salary_text = clean_text(" ".join([description, str(item.get("compensation") or "")]))
        min_salary, max_salary, currency = extract_salary_range(salary_text)
        hosted_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{company.ats_identifier}/{item.get('id')}"
        jobs.append(
            Job(
                company_id=company.id,
                source="ashby",
                ats_type="ashby",
                external_job_id=str(item.get("id") or ""),
                title=title,
                normalized_title=normalize_title(title),
                location=location,
                salary_text=salary_text if currency else None,
                min_salary=min_salary,
                max_salary=max_salary,
                currency=currency or "GBP",
                employment_type=item.get("employmentType"),
                url=hosted_url,
                description=description,
                first_seen_at=now,
                last_seen_at=now,
                is_live=True,
                dedupe_key=make_dedupe_key(company.name, title, location, str(item.get("id") or ""), hosted_url),
            )
        )
    return jobs
