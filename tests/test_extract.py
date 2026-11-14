import pytest

from skillgap.extract import SkillMatcher, discover_terms
from skillgap.taxonomy import SKILLS, Skill, validate

M = SkillMatcher()


def skills(text):
    return M.skills_in(text)


@pytest.mark.parametrize("text", [
    "We value trust and transparency",          # rust inside trust
    "Build scalable services",                  # scala inside scalable
    "You will excel in a fast-paced team",      # Excel as a verb
    "A minimum of 3 years",                     # imu inside minimum
    "Do original research",                     # search inside research
    "Go above and beyond for customers",        # Go as a verb
])
def test_no_false_positives_from_substrings_and_english_words(text):
    assert skills(text) & {"Rust", "Scala", "Excel / spreadsheets", "Robot sensors (LiDAR, radar, IMU)",
                           "Search and ranking", "Go"} == set()


def test_languages_in_lists():
    found = skills("Proficiency in Python, Go, or Java and C/C++; Rust is a plus. Experience with R or Python.")
    assert {"Python", "Go", "Java", "C", "C++", "Rust", "R"} <= found


def test_java_not_javascript():
    assert skills("Strong JavaScript skills") == {"JavaScript"}


def test_symbol_terms():
    assert {"C#", "CI/CD", "C++"} <= skills("C# and .NET, CI/CD pipelines, modern C++")


def test_longest_match_claims_span_once():
    found = M.find("Experience with retrieval-augmented generation and large language models")
    assert [m.skill for m in found] == ["Retrieval-augmented generation", "Large language models"]


def test_separator_variants():
    assert "Time series and forecasting" in skills("time-series models")
    assert "Fine-tuning and post-training" in skills("fine tuning LLMs")


def test_robotics_terms():
    found = skills("ROS 2, SLAM, Kalman filters, MPC and LiDAR sensor fusion on an RTOS")
    assert {"ROS", "SLAM and localization", "State estimation", "Control systems",
            "Robot sensors (LiDAR, radar, IMU)", "Sensor fusion", "Real-time systems"} <= found


def test_case_sensitive_aliases():
    assert "AWS" in skills("Deploy on AWS")
    assert "AWS" not in skills("follow all laws")


def test_validate_rejects_shared_alias():
    with pytest.raises(ValueError):
        validate([Skill("A", "x", ("spark",)), Skill("B", "x", ("spark",))])


def test_taxonomy_is_valid_and_sized():
    validate(SKILLS)
    assert len(SKILLS) >= 120


def test_discovery_skips_covered_terms():
    texts = ["We use spark and widgetron daily"] * 5 + ["widgetron pipelines for spark"] * 5
    terms = [t for t, _ in discover_terms(texts, top=20, min_df=0.1, max_df=1.0)]
    assert "widgetron" in terms and "spark" not in terms
