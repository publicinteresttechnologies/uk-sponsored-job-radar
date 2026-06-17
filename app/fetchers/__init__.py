from __future__ import annotations

from collections.abc import Callable

from app.models import Company, Job

from .ashby import fetch_ashby_jobs
from .generic_careers import fetch_generic_careers_jobs
from .greenhouse import fetch_greenhouse_jobs
from .lever import fetch_lever_jobs
from .smartrecruiters import fetch_smartrecruiters_jobs


Fetcher = Callable[[Company], list[Job]]

FETCHERS: dict[str, Fetcher] = {
    "greenhouse": fetch_greenhouse_jobs,
    "lever": fetch_lever_jobs,
    "ashby": fetch_ashby_jobs,
    "smartrecruiters": fetch_smartrecruiters_jobs,
    "generic_careers": fetch_generic_careers_jobs,
}
