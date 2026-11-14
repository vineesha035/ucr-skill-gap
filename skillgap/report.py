"""Charts and the markdown report."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Reference palette (dataviz skill, light mode): categorical slots 1-3, text and surface tokens.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
SEQ = ["#eef4fc", "#cfe0f6", "#a6c6ef", "#73a5e4", "#2a78d6", "#1d5aa6", "#123d73"]
SHORT = {"MS Computational Data Science": "M.S. CDS", "MS Computer Science": "M.S. CS",
         "MS Robotics": "M.S. Robotics"}
FAMILY = {"data_science": "Data science", "software": "Software", "robotics": "Robotics"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "legend.frameon": False,
})


def _pct(ax, axis="x"):
    fmt = matplotlib.ticker.PercentFormatter(1.0, decimals=0)
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


def gap_dumbbell(scores: pd.DataFrame, program: str, path: Path, n: int = 14) -> None:
    g = scores[(scores.program == program) & (scores.kind == "concept")].nlargest(n, "demand").iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.42 * n + 1.4))
    y = range(len(g))
    ax.hlines(y, g.exposure, g.demand, color=GRID, linewidth=2, zorder=1)
    ax.scatter(g.exposure, y, s=64, color=ORANGE, edgecolor=SURFACE, linewidth=2, zorder=3,
               label="Curriculum exposure (chance a graduate took a covering course)")
    ax.scatter(g.demand, y, s=64, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3,
               label="Market demand (share of postings)")
    ax.set_yticks(list(y), g.skill)
    for yi, r in zip(y, g.itertuples()):
        if r.quadrant == "critical gap":
            ax.text(max(r.demand, r.exposure) + 0.02, yi, "gap", va="center", fontsize=8, color=INK2)
    ax.set_xlim(0, 1.05)
    _pct(ax)
    ax.grid(axis="y", visible=False)
    fam = FAMILY[g.role_family.iloc[0]]
    ax.set_title(f"{SHORT[program]}: top {n} concept skills in {fam.lower()} postings", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.08), ncol=1, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def quadrant_grid(scores: pd.DataFrame, path: Path, high_demand: float, well_taught: float) -> None:
    progs = list(SHORT)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    for ax, prog in zip(axes, progs):
        g = scores[(scores.program == prog) & (scores.kind == "concept")]
        ax.axvline(high_demand, color=MUTED, linewidth=1, linestyle="--")
        ax.axhline(well_taught, color=MUTED, linewidth=1, linestyle="--")
        crit = g.quadrant == "critical gap"
        ax.scatter(g.demand[~crit], g.exposure[~crit], s=36, color=BLUE, edgecolor=SURFACE, linewidth=1.5,
                   label="other concept skills")
        ax.scatter(g.demand[crit], g.exposure[crit], s=48, color=ORANGE, edgecolor=SURFACE, linewidth=1.5,
                   label=f"critical gap ({int(crit.sum())})")
        ax.legend(loc="center right", fontsize=8)
        ax.set_ylim(-0.04, 1.14)
        ax.set_title(SHORT[prog], loc="left")
        ax.set_xlabel("Market demand")
        _pct(ax)
        _pct(ax, "y")
        ax.text(0.99, 0.985, "well covered", transform=ax.transAxes, ha="right", va="top", fontsize=8, color=MUTED)
        ax.text(0.01, 0.985, "taught, low demand", transform=ax.transAxes, va="top", fontsize=8, color=MUTED)
    axes[0].set_ylabel("Curriculum exposure")
    fig.suptitle("Concept skills: market demand vs curriculum exposure", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def readiness_bars(ready_all: pd.DataFrame, ready_early: pd.DataFrame, path: Path) -> None:
    m = ready_all.merge(ready_early, on="program", suffixes=("_all", "_early"))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = range(len(m))
    w = 0.36
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], m.readiness_all, w, color=BLUE, label="All postings")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], m.readiness_early, w, color=ORANGE, label="Entry and mid level only")
    for bars in (b1, b2):
        ax.bar_label(bars, labels=[f"{v:.0%}" for v in bars.datavalues], padding=3, fontsize=9, color=INK2)
    ax.set_xticks(list(x), [SHORT[p] for p in m.program])
    ax.set_ylim(0, max(m.readiness_all.max(), m.readiness_early.max()) * 1.5)
    _pct(ax, "y")
    ax.grid(axis="x", visible=False)
    ax.set_title("Readiness: demand-weighted coverage of the top 20 concept skills", loc="left")
    ax.legend(loc="upper left", fontsize=9, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def demand_only_bars(scores: pd.DataFrame, path: Path, n: int = 12) -> None:
    fams = ["data_science", "software", "robotics"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 0.36 * n + 1.6))
    d = scores.drop_duplicates(["role_family", "skill"])
    for ax, fam in zip(axes, fams):
        g = d[(d.role_family == fam) & (d.kind != "concept")].nlargest(n, "demand").iloc[::-1]
        bars = ax.barh(g.skill, g.demand, color=AQUA, height=0.62)
        ax.bar_label(bars, labels=[f"{v:.0%}" for v in g.demand], padding=3, fontsize=8, color=INK2)
        ax.set_title(f"{FAMILY[fam]} postings", loc="left")
        ax.set_xlim(0, 1)
        _pct(ax)
        ax.grid(axis="y", visible=False)
    fig.suptitle("Tools and practices employers ask for (demand only: catalogs cannot show whether these are taught)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def category_heatmap(postings: pd.DataFrame, path: Path) -> None:
    from .taxonomy import SKILLS
    cat_of = {s.name: s.category for s in SKILLS}
    rows = []
    for fam, g in postings.groupby("role_family"):
        cats = g.skills.map(lambda ss: {cat_of[s] for s in ss})
        for c in dict.fromkeys(cat_of.values()):
            rows.append((FAMILY[fam], c, cats.map(lambda x: c in x).mean()))
    t = pd.DataFrame(rows, columns=["family", "category", "share"]).pivot(index="category", columns="family",
                                                                         values="share")
    t = t[["Data science", "Software", "Robotics"]].sort_values("Data science")
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", SEQ)
    im = ax.imshow(t.values, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(t.shape[1]), t.columns)
    ax.set_yticks(range(t.shape[0]), t.index)
    ax.grid(False)
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.values[i, j]
            ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=9, color="white" if v > 0.55 else INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Share of postings asking for at least one skill in each category", loc="left")
    fig.colorbar(im, ax=ax, format=matplotlib.ticker.PercentFormatter(1.0, decimals=0), shrink=0.7)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def postings_over_time(counts: pd.DataFrame, path: Path) -> None:
    b = counts[counts.source == "boards"].copy()
    b["date"] = pd.to_datetime(b.date)
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.plot(b.date, b.still_open, color=BLUE, linewidth=2, marker="o", markersize=6,
            markeredgecolor=SURFACE, markeredgewidth=2)
    for r in b.itertuples():
        ax.annotate(f"{r.still_open:,}", (r.date, r.still_open), xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=8, color=INK2)
    ax.set_title("Open company-board postings by collection date", loc="left")
    ax.set_ylim(0, b.still_open.max() * 1.2)
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(lines)


def write_markdown(path: Path, scores_all: pd.DataFrame, scores_early: pd.DataFrame, ready_all: pd.DataFrame,
                   ready_early: pd.DataFrame, meta: dict) -> None:
    out = [f"# Skill gap report ({meta['as_of']})", "",
           f"Postings analyzed: **{meta['n_analyzed']:,}** open company-board postings "
           f"({meta['n_ds']:,} data science, {meta['n_sw']:,} software, {meta['n_rob']:,} robotics) "
           f"from {meta['n_companies']} employers, after cleaning {meta['n_open']:,} open postings. "
           f"Curriculum: {meta['n_courses']} courses from the 2025-26 UCR catalog.", "",
           "**How to read this.** *Demand* is the share of a role family's postings that mention a skill. "
           "*Exposure* is the chance a typical graduate took at least one course whose catalog description "
           "covers it. A **critical gap** is a concept in at least 10% of postings that fewer than half of "
           "graduates are likely to have studied. Tools and practices are reported as demand only, because "
           "catalog descriptions do not list the tools a course uses.", "",
           "## Readiness", "", "![readiness](figures/readiness.png)", ""]
    r = ready_all.merge(ready_early, on="program", suffixes=("_all", "_early"))
    out.append(_table(pd.DataFrame({"Program": r.program.map(SHORT),
                                    "All postings": r.readiness_all.map("{:.0%}".format),
                                    "Entry and mid level": r.readiness_early.map("{:.0%}".format)})))
    out += ["", "## Critical gaps by program", "", "![quadrants](figures/quadrants.png)", ""]
    for prog in SHORT:
        out += [f"### {SHORT[prog]}", "", f"![{prog}](figures/gaps_{SHORT[prog].split()[-1].lower()}.png)", ""]
        for label, sc in (("All postings", scores_all), ("Entry and mid level", scores_early)):
            g = sc[(sc.program == prog) & (sc.quadrant == "critical gap")].head(8)
            out += [f"**{label}**", "", _table(pd.DataFrame({
                "Skill": g.skill, "Demand": g.demand.map("{:.0%}".format),
                "Exposure": g.exposure.map("{:.0%}".format), "Covering courses": g.courses.replace("", "none")})), ""]
        wc = scores_all[(scores_all.program == prog) & (scores_all.quadrant == "well covered")].skill
        out += [f"Well covered: {', '.join(wc) or 'none'}.", ""]
    out += ["## Tools and practices in demand", "", "![tools](figures/tools_demand.png)", "",
            "## Skill categories by role family", "", "![categories](figures/category_heatmap.png)", "",
            "## Collection over time", "", "![time](figures/postings_over_time.png)", "",
            "## Limitations", "",
            "- Exposure comes from catalog descriptions, which are short. A course can teach a concept its "
            "description does not name, so exposure is a lower bound.",
            "- Electives use a uniform-choice model (slots / pool size). Real students cluster in popular "
            "electives.",
            "- Postings come from ~55 employers on Greenhouse, Lever, and Ashby, which over-represents tech "
            "companies and well-funded startups. Each employer is capped at 10% of a role family.",
            "- Robotics has the smallest sample, so its percentages move more between collection days.", ""]
    path.write_text("\n".join(out), encoding="utf-8")
