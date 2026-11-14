"""Gap scoring: market demand for each skill vs the chance a program's graduate studied it.

demand(skill, family)   share of analyzed postings in the role family that mention the skill
                        (optionally restricted to entry and mid level postings)
exposure(skill, prog)   probability a typical student takes at least one course whose catalog
                        description covers the skill:  1 - prod(1 - p_course)
                        p_course by requirement type:
                          core, capstone   1.0
                          core_choice      1 / number of courses in that choice group
                          elective         elective slots / size of the program's elective pool
                          elective_open    same pool rule (broad pools have many courses, so p is small)
gap = demand - exposure (positive = market asks for it more than the program reliably teaches it)

Only concept skills get a gap. Tools (languages, frameworks, products) and practices (debugging,
code review, testing) are reported as demand only, because catalog descriptions name concepts,
not the tools used or the practices built through project work.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .extract import SkillMatcher
from .taxonomy import SKILLS, kind

PROGRAM_FAMILY = {
    "MS Computational Data Science": "data_science",
    "MS Computer Science": "software",
    "MS Robotics": "robotics",
}
# Elective courses a student takes, from the 2025-26 catalog requirements.
ELECTIVE_SLOTS = {
    "MS Computational Data Science": 6,     # six electives from Lists A/B
    "MS Computer Science": 10,              # 2 breadth + 32 elective units (8 courses)
    "MS Robotics": 5,                       # 3 focus-area courses + 2 electives
}
EARLY_CAREER = {"entry", "mid"}


@dataclass(frozen=True)
class GapConfig:
    high_demand: float = 0.10        # skill in >= 10% of the family's postings
    well_taught: float = 0.50        # graduate has >= 50% chance of a course covering it


def course_probabilities(cur: pd.DataFrame) -> pd.Series:
    p = pd.Series(0.0, index=cur.index)
    for prog, g in cur.groupby("program"):
        p[g.index[g.requirement.isin(["core", "capstone"])]] = 1.0
        choice = g[g.requirement == "core_choice"]
        p[choice.index] = 1.0 / choice.groupby("req_group")["course_code"].transform("count")
        pool = g[g.requirement.isin(["elective", "elective_open"])]
        if len(pool):
            p[pool.index] = min(1.0, ELECTIVE_SLOTS[prog] / len(pool))
    return p


def curriculum_skills(cur: pd.DataFrame, matcher: SkillMatcher | None = None) -> pd.DataFrame:
    matcher = matcher or SkillMatcher()
    cur = cur.copy()
    cur["skills"] = [matcher.skills_in(f"{t}. {d}") for t, d in zip(cur.title, cur.description)]
    cur["p_take"] = course_probabilities(cur)
    return cur


def exposure(cur: pd.DataFrame) -> pd.DataFrame:
    """program x skill table of the probability a student meets the skill in coursework."""
    rows = []
    for prog, g in cur.groupby("program"):
        for s in SKILLS:
            covering = g[g.skills.map(lambda x: s.name in x)]
            miss = (1 - covering.p_take).prod() if len(covering) else 1.0
            rows.append({"program": prog, "skill": s.name, "exposure": 1 - miss,
                         "courses": ", ".join(covering.course_code)})
    return pd.DataFrame(rows)


def demand(postings: pd.DataFrame, early_career: bool = False) -> pd.DataFrame:
    """family x skill table of the share of postings that mention the skill."""
    df = postings[postings.level.isin(EARLY_CAREER)] if early_career else postings
    rows = []
    for fam, g in df.groupby("role_family"):
        n = len(g)
        for s in SKILLS:
            rows.append({"role_family": fam, "skill": s.name, "category": s.category,
                         "kind": kind(s),
                         "demand": g.skills.map(lambda x: s.name in x).sum() / n, "n_postings": n})
    return pd.DataFrame(rows)


def quadrant(row, cfg: GapConfig) -> str:
    if row.kind != "concept":
        return f"{row.kind} (demand only)"
    hi_d, hi_e = row.demand >= cfg.high_demand, row.exposure >= cfg.well_taught
    if hi_d and not hi_e:
        return "critical gap" if row.demand > row.exposure else "partially covered"
    if hi_d and hi_e:
        return "well covered"
    if not hi_d and hi_e:
        return "taught, low demand"
    return "low priority"


def score(postings: pd.DataFrame, cur: pd.DataFrame, early_career: bool = False,
          cfg: GapConfig = GapConfig()) -> pd.DataFrame:
    """One row per program x skill with demand, exposure, gap, quadrant, and covering courses."""
    d = demand(postings, early_career)
    e = exposure(cur)
    e["role_family"] = e.program.map(PROGRAM_FAMILY)
    out = e.merge(d, on=["role_family", "skill"])
    out["gap"] = out.demand - out.exposure
    out["quadrant"] = out.apply(quadrant, axis=1, cfg=cfg)
    return out.sort_values(["program", "gap"], ascending=[True, False]).reset_index(drop=True)


def readiness(scores: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Demand-weighted coverage of each program's top-N most demanded concept skills."""
    rows = []
    for prog, g in scores[scores.kind == "concept"].groupby("program"):
        top = g.nlargest(top_n, "demand")
        rows.append({"program": prog, "readiness": (top.demand * top.exposure).sum() / top.demand.sum(),
                     "top_skills_considered": top_n})
    return pd.DataFrame(rows)
