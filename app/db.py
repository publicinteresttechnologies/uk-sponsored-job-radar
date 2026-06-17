from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .config import DB_PATH
from .models import ApplicationPack, ApplicationStatus, Company, Job, JobScore, utc_now_iso
from .normalize import normalize_company_name


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL UNIQUE,
                website TEXT,
                careers_url TEXT,
                ats_type TEXT,
                ats_identifier TEXT,
                sponsor_status TEXT,
                sponsor_rating TEXT,
                sponsor_routes TEXT,
                last_checked_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sponsor_register (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organisation_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                town_city TEXT,
                county TEXT,
                type_rating TEXT,
                route TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_sponsor_normalized_name
            ON sponsor_register(normalized_name);

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                source TEXT NOT NULL,
                ats_type TEXT,
                external_job_id TEXT,
                title TEXT NOT NULL,
                normalized_title TEXT NOT NULL,
                location TEXT,
                remote_policy TEXT,
                salary_text TEXT,
                min_salary INTEGER,
                max_salary INTEGER,
                currency TEXT,
                employment_type TEXT,
                url TEXT NOT NULL,
                description TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                is_live INTEGER NOT NULL DEFAULT 1,
                dedupe_key TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS job_scores (
                job_id INTEGER PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                official_posting_score INTEGER NOT NULL,
                sponsor_score INTEGER NOT NULL,
                salary_score INTEGER NOT NULL,
                soc_score INTEGER NOT NULL,
                cv_fit_score INTEGER NOT NULL,
                sponsorship_language_score INTEGER NOT NULL,
                total_score INTEGER NOT NULL,
                decision TEXT NOT NULL,
                rejection_reason TEXT,
                evidence_json TEXT NOT NULL,
                scored_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS application_packs (
                job_id INTEGER PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                generated_at TEXT NOT NULL,
                cv_variant_markdown TEXT NOT NULL,
                cover_letter_markdown TEXT NOT NULL,
                recruiter_note_markdown TEXT NOT NULL,
                screening_answers_markdown TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS application_tracking (
                job_id INTEGER PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                priority TEXT,
                next_action TEXT,
                deadline TEXT,
                notes TEXT,
                last_updated_at TEXT NOT NULL
            );
            """
        )


def import_sponsors(path: Path | str, db_path: Path | str = DB_PATH) -> int:
    init_db(db_path)
    rows = 0
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle, connect(db_path) as conn:
        reader = csv.DictReader(handle)
        conn.execute("DELETE FROM sponsor_register")
        for row in reader:
            name = (row.get("Organisation Name") or "").strip()
            if not name:
                continue
            conn.execute(
                """
                INSERT INTO sponsor_register
                (organisation_name, normalized_name, town_city, county, type_rating, route)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    normalize_company_name(name),
                    row.get("Town/City"),
                    row.get("County"),
                    row.get("Type & Rating"),
                    row.get("Route"),
                ),
            )
            rows += 1
        match_sponsors(conn)
    return rows


def import_companies(path: Path | str, db_path: Path | str = DB_PATH) -> int:
    init_db(db_path)
    rows = 0
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle, connect(db_path) as conn:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            conn.execute(
                """
                INSERT INTO companies
                (name, normalized_name, website, careers_url, ats_type, ats_identifier, last_checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(normalized_name) DO UPDATE SET
                    name=excluded.name,
                    website=excluded.website,
                    careers_url=excluded.careers_url,
                    ats_type=excluded.ats_type,
                    ats_identifier=excluded.ats_identifier,
                    last_checked_at=excluded.last_checked_at
                """,
                (
                    name,
                    normalize_company_name(name),
                    row.get("website"),
                    row.get("careers_url"),
                    (row.get("ats_type") or "").strip().lower() or None,
                    row.get("ats_identifier"),
                    utc_now_iso(),
                ),
            )
            rows += 1
        match_sponsors(conn)
    return rows


def match_sponsors(conn: sqlite3.Connection) -> None:
    companies = conn.execute("SELECT id, normalized_name FROM companies").fetchall()
    for company in companies:
        sponsor = conn.execute(
            """
            SELECT * FROM sponsor_register
            WHERE normalized_name = ?
               OR normalized_name LIKE ?
               OR ? LIKE '%' || normalized_name || '%'
            ORDER BY LENGTH(normalized_name) DESC
            LIMIT 1
            """,
            (company["normalized_name"], f"%{company['normalized_name']}%", company["normalized_name"]),
        ).fetchone()
        if sponsor:
            conn.execute(
                """
                UPDATE companies
                SET sponsor_status = 'matched', sponsor_rating = ?, sponsor_routes = ?, last_checked_at = ?
                WHERE id = ?
                """,
                (sponsor["type_rating"], sponsor["route"], utc_now_iso(), company["id"]),
            )
        else:
            conn.execute(
                """
                UPDATE companies
                SET sponsor_status = 'not_matched', sponsor_rating = NULL, sponsor_routes = NULL, last_checked_at = ?
                WHERE id = ?
                """,
                (utc_now_iso(), company["id"]),
            )


def get_companies(db_path: Path | str = DB_PATH) -> list[Company]:
    with connect(db_path) as conn:
        return [Company(**dict(row)) for row in conn.execute("SELECT * FROM companies ORDER BY name")]


def upsert_jobs(jobs: Iterable[Job], db_path: Path | str = DB_PATH) -> int:
    init_db(db_path)
    count = 0
    with connect(db_path) as conn:
        for job in jobs:
            conn.execute(
                """
                INSERT INTO jobs
                (company_id, source, ats_type, external_job_id, title, normalized_title, location,
                 remote_policy, salary_text, min_salary, max_salary, currency, employment_type,
                 url, description, first_seen_at, last_seen_at, is_live, dedupe_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    is_live=excluded.is_live,
                    title=excluded.title,
                    location=excluded.location,
                    salary_text=excluded.salary_text,
                    min_salary=excluded.min_salary,
                    max_salary=excluded.max_salary,
                    description=excluded.description,
                    url=excluded.url
                """,
                (
                    job.company_id, job.source, job.ats_type, job.external_job_id, job.title,
                    job.normalized_title, job.location, job.remote_policy, job.salary_text,
                    job.min_salary, job.max_salary, job.currency, job.employment_type,
                    str(job.url), job.description, job.first_seen_at, job.last_seen_at,
                    int(job.is_live), job.dedupe_key,
                ),
            )
            count += 1
    return count


def fetch_jobs_for_scoring(db_path: Path | str = DB_PATH) -> list[sqlite3.Row]:
    init_db(db_path)
    with connect(db_path) as conn:
        return conn.execute(
            """
            SELECT jobs.*, companies.name AS company_name, companies.sponsor_status,
                   companies.sponsor_rating, companies.sponsor_routes, companies.website
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            WHERE jobs.is_live = 1
            ORDER BY companies.name, jobs.title
            """
        ).fetchall()


def fetch_jobs_by_decision(decisions: list[str], db_path: Path | str = DB_PATH) -> list[sqlite3.Row]:
    init_db(db_path)
    placeholders = ",".join("?" for _ in decisions)
    with connect(db_path) as conn:
        return conn.execute(
            f"""
            SELECT jobs.*, companies.name AS company_name, companies.website,
                   job_scores.total_score, job_scores.decision, job_scores.rejection_reason,
                   job_scores.evidence_json
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            JOIN job_scores ON job_scores.job_id = jobs.id
            WHERE job_scores.decision IN ({placeholders})
            ORDER BY job_scores.total_score DESC, companies.name, jobs.title
            """,
            decisions,
        ).fetchall()


def upsert_score(score: JobScore, db_path: Path | str = DB_PATH) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO job_scores
            (job_id, official_posting_score, sponsor_score, salary_score, soc_score,
             cv_fit_score, sponsorship_language_score, total_score, decision,
             rejection_reason, evidence_json, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                official_posting_score=excluded.official_posting_score,
                sponsor_score=excluded.sponsor_score,
                salary_score=excluded.salary_score,
                soc_score=excluded.soc_score,
                cv_fit_score=excluded.cv_fit_score,
                sponsorship_language_score=excluded.sponsorship_language_score,
                total_score=excluded.total_score,
                decision=excluded.decision,
                rejection_reason=excluded.rejection_reason,
                evidence_json=excluded.evidence_json,
                scored_at=excluded.scored_at
            """,
            (
                score.job_id, score.official_posting_score, score.sponsor_score,
                score.salary_score, score.soc_score, score.cv_fit_score,
                score.sponsorship_language_score, score.total_score, score.decision.value,
                score.rejection_reason, json.dumps(score.evidence_json, ensure_ascii=False),
                score.scored_at,
            ),
        )


def upsert_application_pack(pack: ApplicationPack, db_path: Path | str = DB_PATH) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO application_packs
            (job_id, generated_at, cv_variant_markdown, cover_letter_markdown,
             recruiter_note_markdown, screening_answers_markdown)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                generated_at=excluded.generated_at,
                cv_variant_markdown=excluded.cv_variant_markdown,
                cover_letter_markdown=excluded.cover_letter_markdown,
                recruiter_note_markdown=excluded.recruiter_note_markdown,
                screening_answers_markdown=excluded.screening_answers_markdown
            """,
            (
                pack.job_id, pack.generated_at, pack.cv_variant_markdown,
                pack.cover_letter_markdown, pack.recruiter_note_markdown,
                pack.screening_answers_markdown,
            ),
        )
        conn.execute(
            """
            INSERT INTO application_tracking
            (job_id, status, priority, next_action, deadline, notes, last_updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status=CASE
                    WHEN application_tracking.status = 'NOT_STARTED' THEN excluded.status
                    ELSE application_tracking.status
                END,
                next_action=COALESCE(application_tracking.next_action, excluded.next_action),
                last_updated_at=excluded.last_updated_at
            """,
            (
                pack.job_id, ApplicationStatus.PACK_GENERATED.value, None,
                "Human review required before manual submission", None,
                "Generated pack is draft-only; no application has been submitted.",
                utc_now_iso(),
            ),
        )


def update_application_tracking(
    job_id: int,
    status: ApplicationStatus,
    priority: str | None = None,
    next_action: str | None = None,
    deadline: str | None = None,
    notes: str | None = None,
    db_path: Path | str = DB_PATH,
) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO application_tracking
            (job_id, status, priority, next_action, deadline, notes, last_updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status,
                priority=excluded.priority,
                next_action=excluded.next_action,
                deadline=excluded.deadline,
                notes=excluded.notes,
                last_updated_at=excluded.last_updated_at
            """,
            (job_id, status.value, priority, next_action, deadline, notes, utc_now_iso()),
        )


def fetch_application_cockpit(db_path: Path | str = DB_PATH) -> list[sqlite3.Row]:
    init_db(db_path)
    with connect(db_path) as conn:
        return conn.execute(
            """
            SELECT jobs.id AS job_id, companies.name AS company_name, jobs.title, jobs.location,
                   jobs.url, jobs.salary_text, job_scores.decision, job_scores.total_score,
                   tracking.status, tracking.priority, tracking.next_action, tracking.deadline,
                   tracking.notes, tracking.last_updated_at,
                   packs.generated_at AS pack_generated_at
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            LEFT JOIN job_scores ON job_scores.job_id = jobs.id
            LEFT JOIN application_tracking AS tracking ON tracking.job_id = jobs.id
            LEFT JOIN application_packs AS packs ON packs.job_id = jobs.id
            ORDER BY
                CASE job_scores.decision WHEN 'APPLY' THEN 0 WHEN 'HOLD' THEN 1 ELSE 2 END,
                job_scores.total_score DESC,
                companies.name
            """
        ).fetchall()
