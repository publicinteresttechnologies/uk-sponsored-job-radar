# UK Sponsored Job Radar

Local-first MVP for Karan Dhar's UK Skilled Worker sponsored-job search. It discovers jobs from official company and ATS sources, stores them in SQLite, deduplicates postings, applies deterministic sponsorship/salary/CV-fit filters, generates draft application materials, and tracks applications through a human-in-the-loop cockpit.

It does not auto-apply, auto-submit, automate LinkedIn logins, bypass CAPTCHA/2FA, evade rate limits, create fake applications, hallucinate experience, or treat speculative job-board roles as apply-ready.

## Setup

Run these commands from the repo directory:

```bash
python -m venv .venv
pip install -r requirements.txt
python -m app.cli init-db
python -m app.cli import-sponsors app/data/sponsor_register.example.csv
python -m app.cli import-companies app/data/target_companies.example.csv
python -m app.cli fetch-jobs
python -m app.cli score-jobs
python -m app.cli generate-packs
python -m app.cli applications
python -m app.cli report
```

Open `reports/latest.html` after the report command completes.

## Inputs

`app/data/target_companies.example.csv` has:

```text
name,website,careers_url,ats_type,ats_identifier
```

Supported `ats_type` values are `greenhouse`, `lever`, `ashby`, `smartrecruiters`, and `generic_careers`.

`app/data/sponsor_register.example.csv` matches the UK sponsor-register export shape:

```text
Organisation Name,Town/City,County,Type & Rating,Route
```

`app/data/user_profile.example.yaml` contains Karan's Skilled Worker salary floor, target lanes, sponsorship rejection phrases, and fit evidence.

## CLI

```bash
python -m app.cli init-db
python -m app.cli import-sponsors path/to/sponsor_register.csv
python -m app.cli import-companies path/to/target_companies.csv
python -m app.cli fetch-jobs
python -m app.cli score-jobs
python -m app.cli generate-packs
python -m app.cli generate-packs --decision HOLD
python -m app.cli applications
python -m app.cli track-job 1 HUMAN_REVIEW --next-action "Review pack against master CV"
python -m app.cli report
```

`generate-packs` only works for `APPLY` or `HOLD` roles. It creates draft CV notes, cover letters, recruiter notes, and screening answers, then marks the job as pack-generated. It never submits an application.

## Scoring

The first version is intentionally deterministic:

- `REJECT` if the employer is not matched to the sponsor register.
- `REJECT` if the job is not from an official company/ATS source.
- `REJECT` if salary is clearly below GBP 41,700.
- `REJECT` if the posting includes hard sponsorship rejection language.
- `APPLY` only when sponsor, salary, CV fit, and official-source scores meet the configured thresholds.
- `HOLD` for strong CV-fit roles where salary or sponsorship language is unclear.

## Application Cockpit

The cockpit keeps final submission manual:

- `application_packs` stores draft CV tailoring notes, cover letters, recruiter notes, and screening answers.
- `application_tracking` stores status, priority, next action, deadlines, notes, and last update time.
- Valid statuses include `NOT_STARTED`, `PACK_GENERATED`, `HUMAN_REVIEW`, `READY_TO_SUBMIT`, `SUBMITTED_MANUALLY`, `INTERVIEWING`, `REJECTED`, and `WITHDRAWN`.
- Generated materials are grounded in `user_profile.example.yaml` and job evidence. They intentionally include human review reminders and do not invent experience.

## Tests

```bash
pytest
```
