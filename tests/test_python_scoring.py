from app.config import UserProfile
from app.models import Decision
from app.scoring import score_job


def profile() -> UserProfile:
    return UserProfile(
        minimum_salary_general=41700,
        preferred_lanes=[
            "creative producer",
            "content strategy",
            "partnerships",
            "customer success",
            "account manager",
            "media communications",
        ],
        seniority_keywords=[
            "producer",
            "customer success manager",
            "account manager",
            "content strategist",
        ],
        hard_reject_phrases=[
            "no visa sponsorship",
            "we are unable to sponsor",
            "must have the right to work in the UK",
        ],
        strong_sponsorship_phrases=[
            "sponsorship available",
            "skilled worker",
            "certificate of sponsorship",
        ],
    )


def row(**overrides):
    base = {
        "id": 1,
        "company_name": "Braze Limited",
        "title": "Senior Customer Success Manager",
        "location": "London",
        "description": "Customer success role with enterprise clients and communications across campaigns.",
        "salary_text": "",
        "min_salary": None,
        "max_salary": None,
        "source": "greenhouse",
        "ats_type": "greenhouse",
        "sponsor_status": "matched",
        "sponsor_rating": "Worker (A rating)",
        "sponsor_routes": "Skilled Worker",
    }
    base.update(overrides)
    return base


def test_rejects_non_uk_location_even_with_good_fit():
    scored = score_job(row(location="Sydney, New South Wales, Australia"), profile())
    assert scored.decision == Decision.REJECT
    assert scored.rejection_reason == "Role location is outside the UK"


def test_sales_development_representative_does_not_pass_as_development_role():
    scored = score_job(
        row(
            title="Sales Development Representative",
            description="Outbound sales development role for pipeline generation.",
            company_name="Contentful Ltd",
        ),
        profile(),
    )
    assert scored.decision == Decision.REJECT


def test_soc_backed_hold_surfaces_plausible_customer_success_role():
    scored = score_job(row(), profile())
    assert scored.decision == Decision.HOLD
    assert "SOC-backed HOLD" in (scored.rejection_reason or "") or "title/CV fit" in (scored.rejection_reason or "")
    assert scored.evidence_json["has_soc_backed_signal"] is True


def test_gbm_only_route_is_not_apply_even_if_role_fit_is_good():
    scored = score_job(
        row(
            sponsor_routes="Global Business Mobility: Senior or Specialist Worker",
            title="Senior Customer Success Manager",
            location="London",
        ),
        profile(),
    )
    assert scored.decision != Decision.APPLY
