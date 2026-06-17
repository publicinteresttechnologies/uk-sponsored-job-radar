from __future__ import annotations

from pathlib import Path

import typer

from .config import DB_PATH, load_user_profile
from .db import fetch_application_cockpit, fetch_jobs_by_decision, fetch_jobs_for_scoring, get_companies, import_companies as import_companies_file
from .db import import_sponsors as import_sponsors_file
from .db import init_db as create_db
from .db import update_application_tracking, upsert_application_pack, upsert_jobs, upsert_score
from .fetchers import FETCHERS
from .generation import generate_application_pack
from .models import ApplicationStatus
from .report import generate_report
from .scoring import score_job


app = typer.Typer(help="Local-first UK Skilled Worker sponsored-job application cockpit.")


@app.command("init-db")
def init_db(db_path: Path = DB_PATH) -> None:
    create_db(db_path)
    typer.echo(f"Initialized database at {db_path}")


@app.command("import-sponsors")
def import_sponsors(path: Path, db_path: Path = DB_PATH) -> None:
    count = import_sponsors_file(path, db_path)
    typer.echo(f"Imported {count} sponsor register rows")


@app.command("import-companies")
def import_companies(path: Path, db_path: Path = DB_PATH) -> None:
    count = import_companies_file(path, db_path)
    typer.echo(f"Imported {count} companies")


@app.command("fetch-jobs")
def fetch_jobs(db_path: Path = DB_PATH) -> None:
    companies = get_companies(db_path)
    fetched = 0
    for company in companies:
        ats_type = (company.ats_type or "generic_careers").lower()
        fetcher = FETCHERS.get(ats_type)
        if not fetcher:
            typer.echo(f"Skipping {company.name}: unsupported ATS type {ats_type}")
            continue
        try:
            jobs = fetcher(company)
        except Exception as exc:
            typer.echo(f"Failed {company.name}: {exc}")
            continue
        fetched += upsert_jobs(jobs, db_path)
        typer.echo(f"Fetched {len(jobs)} jobs for {company.name}")
    typer.echo(f"Stored/updated {fetched} jobs")


@app.command("score-jobs")
def score_jobs(profile_path: Path = Path("app/data/user_profile.example.yaml"), db_path: Path = DB_PATH) -> None:
    profile = load_user_profile(profile_path)
    rows = fetch_jobs_for_scoring(db_path)
    for row in rows:
        upsert_score(score_job(dict(row), profile), db_path)
    typer.echo(f"Scored {len(rows)} jobs")


@app.command("generate-packs")
def generate_packs(
    profile_path: Path = Path("app/data/user_profile.example.yaml"),
    decision: str = "APPLY",
    db_path: Path = DB_PATH,
) -> None:
    requested = decision.upper()
    if requested not in {"APPLY", "HOLD"}:
        raise typer.BadParameter("decision must be APPLY or HOLD; rejected roles are not application-ready")
    profile = load_user_profile(profile_path)
    rows = fetch_jobs_by_decision([requested], db_path)
    for row in rows:
        upsert_application_pack(generate_application_pack(dict(row), profile), db_path)
    typer.echo(f"Generated {len(rows)} draft application packs for {requested} roles")
    typer.echo("No applications were submitted. Human review is required.")


@app.command("track-job")
def track_job(
    job_id: int,
    status: ApplicationStatus,
    priority: str | None = None,
    next_action: str | None = None,
    deadline: str | None = None,
    notes: str | None = None,
    db_path: Path = DB_PATH,
) -> None:
    update_application_tracking(job_id, status, priority, next_action, deadline, notes, db_path)
    typer.echo(f"Updated job {job_id} to {status.value}")


@app.command("applications")
def applications(db_path: Path = DB_PATH) -> None:
    rows = fetch_application_cockpit(db_path)
    if not rows:
        typer.echo("No tracked applications yet.")
        return
    for row in rows:
        status = row["status"] or "NOT_STARTED"
        pack = "pack generated" if row["pack_generated_at"] else "no pack"
        typer.echo(
            f"#{row['job_id']} {row['decision'] or 'UNSCORED'} {status} {row['company_name']} - "
            f"{row['title']} ({row['total_score'] or 0}) [{pack}]"
        )


@app.command("report")
def report(db_path: Path = DB_PATH) -> None:
    output = generate_report(db_path)
    typer.echo(f"Generated {output}")


if __name__ == "__main__":
    app()
