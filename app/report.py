from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from .config import DB_PATH, REPORTS_DIR
from .db import connect


REPORT_TEMPLATE = Template(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>UK Sponsored Job Radar Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 32px; color: #202124; }
    h1, h2 { margin-bottom: 8px; }
    section { margin: 28px 0; }
    article { border: 1px solid #d9dce1; border-radius: 6px; padding: 14px 16px; margin: 12px 0; }
    table { border-collapse: collapse; width: 100%; margin-top: 12px; }
    th, td { border: 1px solid #d9dce1; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #f6f8fa; }
    .meta { color: #5f6368; font-size: 14px; }
    .score { font-weight: 700; }
    .reason { color: #9a3412; }
    .warning { background: #fff7ed; border: 1px solid #fed7aa; padding: 12px; border-radius: 6px; }
    a { color: #0b57d0; }
    pre { white-space: pre-wrap; background: #f6f8fa; padding: 10px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>UK Sponsored Job Radar Report</h1>
  <p class="meta">Generated locally from the configured target companies and official ATS/company sources. No application has been submitted by this tool.</p>

  <section class="warning">
    <h2>Coverage disclosure</h2>
    <p><strong>This is not an exhaustive scan of every sponsor-register employer.</strong></p>
    <p>The database currently contains {{ coverage.sponsor_rows }} sponsor-register rows and {{ coverage.target_companies }} configured target companies. The radar only fetches vacancies for configured target companies with usable careers/ATS sources.</p>
    <p>Matched target companies: {{ coverage.matched_companies }}. Skilled Worker target companies: {{ coverage.skilled_worker_companies }}. Target companies with live fetched jobs: {{ coverage.companies_with_jobs }}.</p>
    <p>Use this report as a screened target-source radar. Exhaustive sponsor-wide coverage requires a separate source-discovery pass to find each employer's official careers URL/ATS before jobs can be fetched.</p>
  </section>

  <section>
    <h2>Source audit</h2>
    <table>
      <thead>
        <tr>
          <th>Company</th>
          <th>ATS</th>
          <th>Sponsor status</th>
          <th>Routes</th>
          <th>Live jobs fetched</th>
          <th>APPLY</th>
          <th>HOLD</th>
          <th>REJECT</th>
        </tr>
      </thead>
      <tbody>
        {% for row in source_audit %}
          <tr>
            <td>{{ row.name }}</td>
            <td>{{ row.ats_type or "-" }}</td>
            <td>{{ row.sponsor_status or "-" }}</td>
            <td>{{ row.sponsor_routes or "-" }}</td>
            <td>{{ row.live_jobs }}</td>
            <td>{{ row.apply_count }}</td>
            <td>{{ row.hold_count }}</td>
            <td>{{ row.reject_count }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>

  {% for decision, heading in [("APPLY", "APPLY NOW"), ("HOLD", "HOLD")] %}
  <section>
    <h2>{{ heading }}</h2>
    {% for job in grouped.get(decision, []) %}
      <article>
        <h3>{{ job.company_name }} - {{ job.title }}</h3>
        <p class="meta">{{ job.location or "Location unclear" }} | {{ job.salary_text or "Salary unclear" }} | <span class="score">Score {{ job.total_score }}</span></p>
        <p><a href="{{ job.url }}">{{ job.url }}</a></p>
        <p><strong>Why it fits:</strong> {{ job.why_it_fits }}</p>
        <p><strong>Decision basis:</strong> {{ job.rejection_reason or "Strict APPLY filters passed" }}</p>
        <p><strong>Rejection risk:</strong> {{ job.rejection_risk }}</p>
        <p><strong>Application status:</strong> {{ job.tracking_status }} | <strong>Pack:</strong> {{ job.pack_status }}</p>
        <p><strong>Next action:</strong> {{ job.next_action or "Generate/review pack, then submit manually if still live and viable." }}</p>
        <pre>{{ job.evidence }}</pre>
      </article>
    {% else %}
      <p>No roles in this section.</p>
    {% endfor %}
  </section>
  {% endfor %}

  <section>
    <h2>REJECTED</h2>
    {% for reason, jobs in rejected.items() %}
      <h3 class="reason">{{ reason }}</h3>
      {% for job in jobs %}
        <article>
          <strong>{{ job.company_name }} - {{ job.title }}</strong>
          <p class="meta">{{ job.location or "Location unclear" }} | {{ job.salary_text or "Salary unclear" }} | Score {{ job.total_score }}</p>
          <p><a href="{{ job.url }}">{{ job.url }}</a></p>
        </article>
      {% endfor %}
    {% else %}
      <p>No rejected roles.</p>
    {% endfor %}
  </section>
</body>
</html>
"""
)


def _why_it_fits(evidence: dict) -> str:
    hits = evidence.get("lane_hits", []) + evidence.get("seniority_hits", []) + evidence.get("soc_backed_hits", [])
    return ", ".join(dict.fromkeys(hits)) if hits else "Fit evidence is limited; inspect the posting before applying."


def _rejection_risk(row: dict, evidence: dict) -> str:
    risks = []
    if not row.get("salary_text"):
        risks.append("salary unclear")
    if not evidence.get("strong_sponsorship_hits"):
        risks.append("sponsorship language unclear")
    if evidence.get("has_soc_backed_signal"):
        risks.append("SOC-backed only; manual verification required")
    if not risks:
        return "Low based on deterministic filters."
    return "Medium: " + ", ".join(risks) + "."


def generate_report(db_path: Path | str = DB_PATH, output_path: Path | str | None = None) -> Path:
    output = Path(output_path) if output_path else REPORTS_DIR / "latest.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT jobs.*, companies.name AS company_name, job_scores.*,
                   tracking.status, tracking.next_action, tracking.deadline,
                   packs.generated_at AS pack_generated_at
            FROM jobs
            JOIN companies ON companies.id = jobs.company_id
            JOIN job_scores ON job_scores.job_id = jobs.id
            LEFT JOIN application_tracking AS tracking ON tracking.job_id = jobs.id
            LEFT JOIN application_packs AS packs ON packs.job_id = jobs.id
            ORDER BY job_scores.total_score DESC, companies.name, jobs.title
            """
        ).fetchall()
        source_audit = conn.execute(
            """
            SELECT companies.name, companies.ats_type, companies.sponsor_status, companies.sponsor_routes,
                   COUNT(jobs.id) AS live_jobs,
                   SUM(CASE WHEN job_scores.decision = 'APPLY' THEN 1 ELSE 0 END) AS apply_count,
                   SUM(CASE WHEN job_scores.decision = 'HOLD' THEN 1 ELSE 0 END) AS hold_count,
                   SUM(CASE WHEN job_scores.decision = 'REJECT' THEN 1 ELSE 0 END) AS reject_count
            FROM companies
            LEFT JOIN jobs ON jobs.company_id = companies.id AND jobs.is_live = 1
            LEFT JOIN job_scores ON job_scores.job_id = jobs.id
            GROUP BY companies.id
            ORDER BY hold_count DESC, apply_count DESC, live_jobs DESC, companies.name
            """
        ).fetchall()
        coverage = dict(
            sponsor_rows=conn.execute("SELECT COUNT(*) FROM sponsor_register").fetchone()[0],
            target_companies=conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
            matched_companies=conn.execute("SELECT COUNT(*) FROM companies WHERE sponsor_status = 'matched'").fetchone()[0],
            skilled_worker_companies=conn.execute("SELECT COUNT(*) FROM companies WHERE sponsor_routes LIKE '%Skilled Worker%'").fetchone()[0],
            companies_with_jobs=conn.execute("SELECT COUNT(DISTINCT company_id) FROM jobs WHERE is_live = 1").fetchone()[0],
        )

    grouped: dict[str, list[dict]] = {"APPLY": [], "HOLD": []}
    rejected: dict[str, list[dict]] = {}
    for row in rows:
        item = dict(row)
        evidence = json.loads(item.get("evidence_json") or "{}")
        item["evidence"] = json.dumps(evidence, indent=2, ensure_ascii=False)
        item["why_it_fits"] = _why_it_fits(evidence)
        item["rejection_risk"] = _rejection_risk(item, evidence)
        item["tracking_status"] = item.get("status") or "NOT_STARTED"
        item["pack_status"] = "Generated; human review required" if item.get("pack_generated_at") else "Not generated"
        if item["decision"] in grouped:
            grouped[item["decision"]].append(item)
        else:
            rejected.setdefault(item.get("rejection_reason") or "Rejected", []).append(item)

    audit_rows = [dict(row) for row in source_audit]
    output.write_text(
        REPORT_TEMPLATE.render(grouped=grouped, rejected=rejected, source_audit=audit_rows, coverage=coverage),
        encoding="utf-8",
    )
    return output
