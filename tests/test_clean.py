import pandas as pd
import pytest

from skillgap.clean import cap_per_company, clean_postings, exclusion_reason, normalize, seniority


def test_normalize_strips_html_entities_and_quotes():
    raw = "&lt;p&gt;We use “PyTorch” &amp;amp; SQL• &lt;/p&gt;   now"
    assert normalize(raw) == 'We use "PyTorch" & SQL now'


@pytest.mark.parametrize("title,reason", [
    ("Technical Writer, Autonomous Airpower", "non_engineering"),
    ("Staff Product Manager, AI", "non_engineering"),
    ("Director, Machine Learning Engineering", "non_engineering"),
    ("Strategic Finance, AI & Business Partnership", "non_engineering"),
    ("Contract Student Worker - Machine Learning Engineer", "student_or_contract"),
    ("Software Engineering Intern", "student_or_contract"),
    ("Lead Solutions Architect - Generative AI (EMEA)", "non_engineering"),
    ("Senior Robotics Engineer (EMEA)", "non_us"),
])
def test_exclusions(title, reason):
    assert exclusion_reason(title) == reason


@pytest.mark.parametrize("title", [
    "Data Scientist, Finance",                       # domain word, real role
    "Senior Data Scientist, Monetary Policy",
    "Staff Machine Learning Engineer, CustomerLake",
    "Software Engineer, New Grad",                   # new grad roles are kept
    "Perception Engineer",
])
def test_real_roles_are_kept(title):
    assert exclusion_reason(title) is None


@pytest.mark.parametrize("title,level", [
    ("Staff Software Engineer", "staff+"),
    ("Principal ML Engineer", "staff+"),
    ("Engineering Manager, Perception", "manager"),
    ("Senior Data Scientist", "senior"),
    ("Sr. Robotics Engineer", "senior"),
    ("Software Engineer, New Grad", "entry"),
    ("Software Engineer I", "entry"),
    ("Machine Learning Engineer", "mid"),
    ("AI Engineer", "mid"),                          # "AI" must not read as level "I"
])
def test_seniority(title, level):
    assert seniority(title) == level


def _postings(counts):
    rows = []
    for company, n in counts.items():
        rows += [{"history_id": f"{company}-{i}", "company": company, "role_family": "robotics"} for i in range(n)]
    return pd.DataFrame(rows)


def test_cap_limits_each_company_and_is_deterministic():
    df = _postings({"big": 60, "mid": 25, "small": 15})       # 100 postings, cap = 10
    keep = cap_per_company(df, max_share=0.10)
    kept = df[keep].company.value_counts()
    assert kept.max() == 10
    assert keep.equals(cap_per_company(df, max_share=0.10))   # same sample every run


def test_clean_postings_columns():
    df = pd.DataFrame([
        {"history_id": "a", "company": "x", "role_family": "software", "title": "Software Engineer",
         "description": "Python " * 100},
        {"history_id": "b", "company": "x", "role_family": "software", "title": "Product Manager",
         "description": "Roadmaps " * 100},
        {"history_id": "c", "company": "y", "role_family": "software", "title": "Backend Engineer",
         "description": "too short"},
    ])
    out = clean_postings(df, max_share=1.0)
    assert list(out.excluded) == ["", "non_engineering", "too_short"]
    assert {"level", "capped"} <= set(out.columns)
