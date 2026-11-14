"""End-to-end run: load -> clean -> extract -> score -> report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import gap, report
from .clean import clean_postings
from .extract import SkillMatcher
from .io import HISTORY, ROOT, load_curriculum, load_postings

OUTPUTS = ROOT / "outputs"


def run(out_dir: Path = OUTPUTS, cfg: gap.GapConfig = gap.GapConfig(), max_share: float = 0.10) -> dict:
    figs = out_dir / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    matcher = SkillMatcher()

    postings = clean_postings(load_postings(), max_share=max_share)
    analyzed = postings[postings.excluded == ""].copy()
    analyzed["skills"] = [matcher.skills_in(d) for d in analyzed.description]
    cur = gap.curriculum_skills(load_curriculum(), matcher)

    scores_all = gap.score(analyzed, cur, early_career=False, cfg=cfg)
    scores_early = gap.score(analyzed, cur, early_career=True, cfg=cfg)
    ready_all, ready_early = gap.readiness(scores_all), gap.readiness(scores_early)

    scores_all.to_csv(out_dir / "gap_scores_all_levels.csv", index=False)
    scores_early.to_csv(out_dir / "gap_scores_entry_mid.csv", index=False)
    ready_all.merge(ready_early, on="program", suffixes=("_all", "_entry_mid")).to_csv(
        out_dir / "readiness.csv", index=False)
    cols = ["first_seen", "role_family", "level", "company", "title", "location", "url"]
    export = analyzed[cols].copy()
    export["skills"] = analyzed.skills.map(lambda x: "; ".join(sorted(x)))
    export.sort_values(["first_seen", "company"], ascending=[False, True]).to_csv(
        out_dir / "analyzed_postings.csv", index=False)
    (postings.excluded.replace("", "analyzed").groupby(postings.role_family).value_counts()
     .rename("postings").reset_index().to_csv(out_dir / "cleaning_summary.csv", index=False))

    for prog, short in report.SHORT.items():
        report.gap_dumbbell(scores_all, prog, figs / f"gaps_{short.split()[-1].lower()}.png")
    report.quadrant_grid(scores_all, figs / "quadrants.png", cfg.high_demand, cfg.well_taught)
    report.readiness_bars(ready_all, ready_early, figs / "readiness.png")
    report.demand_only_bars(scores_all, figs / "tools_demand.png")
    report.category_heatmap(analyzed, figs / "category_heatmap.png")
    report.postings_over_time(pd.read_csv(HISTORY / "daily_counts.csv"), figs / "postings_over_time.png")

    fam = analyzed.role_family.value_counts()
    meta = {"as_of": analyzed.last_seen.max(), "n_open": len(postings), "n_analyzed": len(analyzed),
            "n_ds": int(fam.get("data_science", 0)), "n_sw": int(fam.get("software", 0)),
            "n_rob": int(fam.get("robotics", 0)), "n_companies": analyzed.company.nunique(),
            "n_courses": cur.course_code.nunique()}
    report.write_markdown(out_dir / "report.md", scores_all, scores_early, ready_all, ready_early, meta)
    return meta
