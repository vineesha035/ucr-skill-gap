"""Live dashboard for the UCR skill gap analysis.

Reads only the files the pipeline writes to outputs/ and the daily collection counts,
so it updates whenever the daily GitHub Actions run commits new results.
Run locally:  streamlit run streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
PROGRAMS = {"M.S. Computational Data Science": "MS Computational Data Science",
            "M.S. Computer Science": "MS Computer Science", "M.S. Robotics": "MS Robotics"}
FAMILY = {"data_science": "Data science", "software": "Software", "robotics": "Robotics"}
QUADRANT_ORDER = ["critical gap", "partially covered", "well covered", "taught, low demand", "low priority"]

st.set_page_config(page_title="UCR Skill Gap", layout="wide")


@st.cache_data(ttl=3600)
def load():
    return {
        "all": pd.read_csv(OUT / "gap_scores_all_levels.csv"),
        "early": pd.read_csv(OUT / "gap_scores_entry_mid.csv"),
        "ready": pd.read_csv(OUT / "readiness.csv"),
        "postings": pd.read_csv(OUT / "analyzed_postings.csv"),
        "counts": pd.read_csv(ROOT / "data/history/daily_counts.csv"),
    }


d = load()
posts = d["postings"]
as_of = posts.first_seen.max()

st.title("Do UCR's M.S. programs teach what employers hire for?")
st.caption(f"Job postings collected daily from company career boards. Data as of **{as_of}**. "
           "[Code and method on GitHub](https://github.com/vineesha035/ucr-skill-gap)")

with st.sidebar:
    st.header("Filters")
    program_label = st.selectbox("Program", list(PROGRAMS))
    program = PROGRAMS[program_label]
    level = st.radio("Postings", ["All levels", "Entry and mid level only"],
                     help="Entry and mid excludes senior, staff, principal, and manager titles.")
    scores = d["all"] if level == "All levels" else d["early"]
    scores = scores[scores.program == program]
    family = scores.role_family.iloc[0]
    st.markdown(f"Compared against **{FAMILY[family].lower()}** postings.")

ready = d["ready"].set_index("program").loc[program]
r_val = ready.readiness_all if level == "All levels" else ready.readiness_entry_mid
fam_posts = posts[posts.role_family == family]
concepts = scores[scores.kind == "concept"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Readiness", f"{r_val:.0%}", help="Demand-weighted coverage of the top 20 concept skills")
c2.metric("Critical gaps", int((concepts.quadrant == "critical gap").sum()))
c3.metric(f"{FAMILY[family]} postings", f"{len(fam_posts):,}")
c4.metric("Employers", fam_posts.company.nunique())

tab_gaps, tab_tools, tab_jobs, tab_trend, tab_method = st.tabs(
    ["Skill gaps", "Tools and practices", "Browse postings", "Collection over time", "Method"])

with tab_gaps:
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Demand vs curriculum exposure")
        chart = alt.Chart(concepts).mark_circle(size=90, opacity=0.9, stroke="white", strokeWidth=1).encode(
            x=alt.X("demand:Q", title="Market demand (share of postings)", axis=alt.Axis(format="%")),
            y=alt.Y("exposure:Q", title="Curriculum exposure", axis=alt.Axis(format="%"),
                    scale=alt.Scale(domain=[0, 1.05])),
            color=alt.Color("quadrant:N", sort=QUADRANT_ORDER, title=None,
                            scale=alt.Scale(domain=QUADRANT_ORDER, range=[ORANGE, AQUA, BLUE, "#9fc3ef", GRAY])),
            tooltip=[alt.Tooltip("skill:N", title="Skill"), alt.Tooltip("demand:Q", format=".0%", title="Demand"),
                     alt.Tooltip("exposure:Q", format=".0%", title="Exposure"),
                     alt.Tooltip("courses:N", title="Covering courses")],
        )
        rules = (alt.Chart(pd.DataFrame({"x": [0.10]})).mark_rule(strokeDash=[4, 4], color=GRAY).encode(x="x:Q")
                 + alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(strokeDash=[4, 4], color=GRAY).encode(y="y:Q"))
        st.altair_chart((rules + chart).properties(height=440), width="stretch")
    with right:
        st.subheader("Critical gaps")
        crit = concepts[concepts.quadrant == "critical gap"].sort_values("gap", ascending=False)
        st.dataframe(crit[["skill", "demand", "exposure"]].rename(columns=str.title), hide_index=True,
                     width="stretch", column_config={
                         "Demand": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                         "Exposure": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})
        st.caption("A critical gap is a concept in at least 10% of postings that fewer than half of "
                   "graduates are likely to have studied.")
    st.subheader("All concept skills")
    st.dataframe(concepts[["skill", "category", "demand", "exposure", "gap", "quadrant", "courses"]]
                 .sort_values("demand", ascending=False), hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="percent") for c in ["demand", "exposure", "gap"]})

with tab_tools:
    st.subheader(f"Tools and practices in {FAMILY[family].lower()} postings")
    st.caption("Reported as demand only. Catalog descriptions name concepts, not the tools a course uses or the "
               "practices built through projects, so absence from the catalog is not evidence a tool is untaught.")
    tools = scores[scores.kind != "concept"].nlargest(25, "demand")
    bar = alt.Chart(tools).mark_bar(color=AQUA, cornerRadiusEnd=3).encode(
        x=alt.X("demand:Q", title="Share of postings", axis=alt.Axis(format="%")),
        y=alt.Y("skill:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("skill:N"), alt.Tooltip("demand:Q", format=".0%"), alt.Tooltip("kind:N")])
    st.altair_chart(bar.properties(height=620), width="stretch")

with tab_jobs:
    st.subheader("Browse analyzed postings")
    f1, f2, f3 = st.columns([1, 1, 2])
    fams = f1.multiselect("Role family", list(FAMILY), default=[family], format_func=FAMILY.get)
    companies = f2.multiselect("Employer", sorted(posts.company.unique()))
    query = f3.text_input("Skill or title contains", placeholder="e.g. Kalman, LLM, Kubernetes")
    view = posts[posts.role_family.isin(fams)] if fams else posts
    if companies:
        view = view[view.company.isin(companies)]
    if query:
        q = query.lower()
        view = view[view.title.str.lower().str.contains(q, regex=False)
                    | view.skills.fillna("").str.lower().str.contains(q, regex=False)]
    st.caption(f"{len(view):,} postings")
    st.dataframe(view, hide_index=True, width="stretch",
                 column_config={"url": st.column_config.LinkColumn("Link", display_text="open")})

with tab_trend:
    st.subheader("Open company-board postings by collection date")
    c = d["counts"]
    c = c[c.source == "boards"].assign(date=lambda x: pd.to_datetime(x.date))
    line = alt.Chart(c).mark_line(color=BLUE, strokeWidth=2, point=alt.OverlayMarkDef(size=60, color=BLUE)).encode(
        x=alt.X("date:T", title=None), y=alt.Y("still_open:Q", title="Open postings"),
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("still_open:Q", title="Open"), alt.Tooltip("new:Q", title="New")])
    st.altair_chart(line.properties(height=320), width="stretch")
    st.caption("A posting that stops appearing on its company board has been filled or withdrawn. "
               "Skill-level trends become meaningful after a few weeks of daily collection.")

with tab_method:
    st.markdown(f"""
**Postings.** Full-text postings from the public Greenhouse, Lever, and Ashby job-board APIs of
{posts.company.nunique()} employers, collected daily by GitHub Actions. Non-engineering titles, student and
contract roles, and region-scoped roles are removed. Each employer is capped at 10% of a role family.
Sentences repeated across one employer's postings (intros, policies) are removed before extraction.

**Skills.** A 137-skill taxonomy with about 730 aliases, matched with word-boundary-aware,
longest-match-first rules and case-sensitive aliases for ambiguous words (Excel, Go, R, C).

**Curriculum.** 176 courses from the 2025-26 UCR catalog for the three programs.
*Exposure* is the chance a graduate took at least one course whose catalog description covers a skill:
core courses count 1.0, "pick one" courses 1/n, electives slots divided by pool size.

**Limitations.** Exposure is a lower bound because short catalog descriptions do not name everything
a course teaches. Electives are modeled as a uniform choice. Career boards over-represent tech companies.
""")
