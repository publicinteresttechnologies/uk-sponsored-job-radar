from __future__ import annotations

import requests

from app.models import Company, Job, utc_now_iso
from app.normalize import clean_text, extract_salary_range, make_dedupe_key, normalize_title


def fetch_smartrecruiters_jobs(company: Company) -> list[Job]:
    if not company.id or not company.ats_identifier:
        return []
    url = f"https://api.smartrecruiters.com/v1/companies/{company.ats_identifier}/postings"
    response = requests.get(url, params={"limit": 100}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    jobs: list[Job] = []
    now = utc_now_iso()
    for item in payload.get("content", []):
        posting_id = str(item.get("id") or "")
        detail = item
        if posting_id:
            detail_response = requests.get(
                f"https://api.smartrecruiters.com/v1/companies/{company.ats_identifier}/postings/{posting_id}",
                timeout=20,
            )
            if detail_response.ok:
                detail = detail_response.json()
        title = clean_text(detail.get("name") or item.get("name"))
        location_payload = detail.get("location") or {}
        location = clean_text(", ".join(filter(None, [location_payload.get("city"), location_payload.get("country")])))
        description = clean_text((detail.get("jobAd") or {}).get("sections", {}).get("jobDescription", {}).get("text"))
        salary_text = clean_text(" ".join([description, str(detail.get("compensation") or "")]))
        min_salary, max_salary, currency = extract_salary_range(salary_text)
        posting_url = detail.get("ref") or detail.get("applyUrl") or item.get("ref")
        jobs.append(
            Job(
                company_id=company.id,
                source="smartrecruiters",
                ats_type="smartrecruiters",
                external_job_id=posting_id,
                title=title,
                normalized_title=normalize_title(title),
                location=location,
                salary_text=salary_text if currency else None,
                min_salary=min_salary,
                max_salary=max_salary,
                currency=currency or "GBP",
                employment_type=detail.get("typeOfEmployment", {}).get("label") if isinstance(detail.get("typeOfEmployment"), dict) else None,
                url=posting_url,
                description=description,
                first_seen_at=now,
                last_seen_at=now,
                is_live=True,
                dedupe_key=make_dedupe_key(company.name, title, location, posting_id, posting_url),
            )
        )
    return jobs
