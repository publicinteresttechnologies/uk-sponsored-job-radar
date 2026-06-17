from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.models import Company, Job, utc_now_iso
from app.normalize import clean_text, extract_salary_range, make_dedupe_key, normalize_text, normalize_title


JOB_HINTS = ("job", "career", "vacancy", "role", "opening", "position")


def fetch_generic_careers_jobs(company: Company) -> list[Job]:
    if not company.id or not company.careers_url:
        return []
    response = requests.get(company.careers_url, timeout=20, headers={"User-Agent": "uk-sponsored-job-radar/0.1"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for noisy in soup(["script", "style", "noscript"]):
        noisy.decompose()

    jobs: list[Job] = []
    seen: set[str] = set()
    now = utc_now_iso()
    for link in soup.find_all("a", href=True):
        visible = clean_text(link.get_text(" "))
        href = urljoin(company.careers_url, link["href"])
        haystack = normalize_text(" ".join([visible, href]))
        if not visible or not any(hint in haystack for hint in JOB_HINTS):
            continue
        if href in seen:
            continue
        seen.add(href)
        context = clean_text(link.parent.get_text(" ") if link.parent else visible)
        min_salary, max_salary, currency = extract_salary_range(context)
        jobs.append(
            Job(
                company_id=company.id,
                source="generic_careers",
                ats_type="generic_careers",
                external_job_id=href,
                title=visible[:180],
                normalized_title=normalize_title(visible),
                location=None,
                salary_text=context if currency else None,
                min_salary=min_salary,
                max_salary=max_salary,
                currency=currency or "GBP",
                employment_type=None,
                url=href,
                description=context,
                first_seen_at=now,
                last_seen_at=now,
                is_live=True,
                dedupe_key=make_dedupe_key(company.name, visible, None, href, href),
            )
        )
    return jobs
