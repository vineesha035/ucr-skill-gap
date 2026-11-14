import pandas as pd
import pytest

from skillgap import gap


def _cur():
    rows = [
        ("MS Robotics", "R1", "core", "Core", {"Motion planning"}),
        ("MS Robotics", "R2", "core_choice", "pick", {"Computer vision"}),
        ("MS Robotics", "R3", "core_choice", "pick", set()),
    ] + [("MS Robotics", f"E{i}", "elective", "Focus", {"Embedded systems"} if i == 0 else set()) for i in range(10)]
    df = pd.DataFrame(rows, columns=["program", "course_code", "requirement", "req_group", "skills"])
    df["p_take"] = gap.course_probabilities(df)
    return df


def test_course_probabilities():
    cur = _cur()
    p = dict(zip(cur.course_code, cur.p_take))
    assert p["R1"] == 1.0
    assert p["R2"] == p["R3"] == 0.5
    assert p["E0"] == pytest.approx(gap.ELECTIVE_SLOTS["MS Robotics"] / 10)


def test_exposure_is_probability_of_at_least_one_course():
    e = gap.exposure(_cur()).set_index("skill").exposure
    assert e["Motion planning"] == 1.0
    assert e["Computer vision"] == 0.5
    assert e["Embedded systems"] == pytest.approx(0.5)
    assert e["Kafka and streaming"] == 0.0


@pytest.mark.parametrize("demand,exposure,kind,expected", [
    (0.30, 0.00, "concept", "critical gap"),
    (0.30, 0.80, "concept", "well covered"),
    (0.20, 0.30, "concept", "partially covered"),      # under 50% but above demand: not a gap
    (0.02, 0.90, "concept", "taught, low demand"),
    (0.02, 0.00, "concept", "low priority"),
    (0.60, 0.00, "tool", "tool (demand only)"),
    (0.50, 0.00, "practice", "practice (demand only)"),
])
def test_quadrants(demand, exposure, kind, expected):
    row = pd.Series({"demand": demand, "exposure": exposure, "kind": kind})
    assert gap.quadrant(row, gap.GapConfig()) == expected


def test_demand_share_and_early_career_filter():
    postings = pd.DataFrame({"role_family": ["robotics"] * 4, "level": ["mid", "entry", "staff+", "senior"],
                             "skills": [{"Embedded systems"}, set(), {"Embedded systems"}, {"Embedded systems"}]})
    all_lv = gap.demand(postings).set_index("skill").demand
    early = gap.demand(postings, early_career=True).set_index("skill").demand
    assert all_lv["Embedded systems"] == 0.75
    assert early["Embedded systems"] == 0.5
