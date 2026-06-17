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
    .meta { color: #5f6368; font-size: 14px; }
    .score { font-weight: 700; }
    .reason { color: #9a3412; }
    a { color: #0b57d0; }
    pre { white-space: pre-wrap; background: #f6f8fa; padding: 10px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>UK Sponsored Job Radar Report</h1>
  <p class="meta">Generated locally from official company and ATS sources. No application has been submitted by this tool.</p>

  {% for decision, heading in [("APPLY", "APPLY NOW"), ("HOLD", "HOLD")] %}
  <section>
    <h2>{{ heading }}</h2>
    {% for job in grouped.get(decision, []) %}
      <article>
        <h3>{{ job.company_name }} - {{ job.title }}</h3>
        <p class="meta">{{ job.location or "Location unclear" }} | {{ job.salary_text or "Salary unclear" }} | <span class="score">Score {{ job.total_score }}</span></p>
        <p><a href="{{ job.url }}">{{ job.url }}</a></p>
        <p><strong>Why it fits:</strong> {{ job.why_it_fits }}</p>
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
    hits = evidence.get("lane_hits", []) + evidence.get("seniority_hits", [])
    return ", ".join(hits) if hits else "Fit evidence is limited; inspect the posting before applying."


def _rejection_risk(row: dict, evidence: dict) -> str:
    risks = []
    if not row.get("salary_text"):
        risks.append("salary unclear")
    if not evidence.get("strong_sponsorship_hits"):
        risks.append("sponsorship language unclear")
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

    output.write_text(REPORT_TEMPLATE.render(grouped=grouped, rejected=rejected), encoding="utf-8")
    return output
