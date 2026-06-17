from app.normalize import extract_salary_range, normalize_company_name, normalize_title


def test_normalize_company_name_removes_suffixes() -> None:
    assert normalize_company_name("The Acme Broadcasting Limited") == "acme broadcasting"


def test_normalize_title_cleans_gender_suffix() -> None:
    assert normalize_title("Senior Producer (m/f/d)") == "senior producer"


def test_extract_salary_range_handles_gbp_k_values() -> None:
    assert extract_salary_range("Salary: GBP 45k - GBP 55,000 per annum") == (45000, 55000, "GBP")
