from __future__ import annotations

import hashlib
import re
from html import unescape


COMPANY_SUFFIXES = {
    "limited",
    "ltd",
    "plc",
    "llp",
    "inc",
    "corp",
    "corporation",
    "company",
    "co",
    "the",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(value: str | None) -> str:
    text = clean_text(value).casefold()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_company_name(name: str | None) -> str:
    tokens = [token for token in normalize_text(name).split() if token not in COMPANY_SUFFIXES]
    return " ".join(tokens)


def normalize_title(title: str | None) -> str:
    text = normalize_text(title)
    text = re.sub(r"\b(m f d|f m d|m w d|all genders)\b", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_salary_range(text: str | None) -> tuple[int | None, int | None, str | None]:
    if not text:
        return None, None, None
    haystack = clean_text(text)
    currency = "GBP" if re.search(r"£|\bgbp\b", haystack, re.I) else None
    if not currency:
        return None, None, None

    values: list[int] = []
    for match in re.finditer(r"(?:£|GBP\s*)\s*([0-9]{2,3}(?:,[0-9]{3})?|[0-9]{2,3})\s*(k)?", haystack, re.I):
        raw, k_suffix = match.groups()
        value = int(raw.replace(",", ""))
        if k_suffix or value < 1000:
            value *= 1000
        if 10_000 <= value <= 250_000:
            values.append(value)
    if not values:
        return None, None, currency
    return min(values), max(values), currency


def make_dedupe_key(company_name: str, title: str, location: str | None, external_job_id: str | None, url: str | None) -> str:
    stable_id = normalize_text(external_job_id) or normalize_text(url)
    base = "|".join(
        [
            normalize_company_name(company_name),
            normalize_title(title),
            normalize_text(location),
            stable_id,
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
