# UCR Skill Gap

**Do UC Riverside's M.S. programs teach what employers are hiring for?**

This project compares the skills requested in real, current job postings against the
course catalogs of three UCR graduate programs, and measures where each curriculum
matches the market and where it falls short.

| Program | Compared against |
|---|---|
| M.S. Computational Data Science | data scientist, ML engineer, data engineer, AI engineer roles |
| M.S. Computer Science | software, backend, platform, distributed systems roles |
| M.S. Robotics | robotics, autonomy, perception, controls, embedded roles |

> **Status:** in progress. Data collection, cleaning, and skill extraction are built and tested.
> Gap scoring, the report, and a live dashboard are next.

## Data

**Job postings, collected daily by GitHub Actions** ([`daily-collect`](.github/workflows/daily-collect.yml))
- **Company career boards** (Greenhouse, Lever, Ashby public APIs): full posting text from ~55 employers
  including Waymo, Zoox, Nuro, Anduril, OpenAI, Anthropic, Databricks, and Stripe. Used for skill extraction.
- **Adzuna API**: market-wide postings for 19 job titles. Adzuna returns only the first 500 characters of
  each description, so it is used for role volume and salary context, not for skills.
- Each posting is stored once, on the day it first appears. `last_seen` dates track when postings close.
  Browse what is open right now in [`data/history/open_board_postings.csv`](data/history/open_board_postings.csv).

**Curriculum** ([`data/raw/2026-11-06-ucr-ms-curriculum.csv`](data/raw/2026-11-06-ucr-ms-curriculum.csv))
- 176 courses across the three programs, scraped from the 2025-26 UCR General Catalog, with official
  descriptions, credits, core/elective status, and 2025-26 enrollment.
- A test checks every course code named in the catalog's program requirements is present.

## Method so far

1. **Cleaning** ([`skillgap/clean.py`](skillgap/clean.py)). Drops non-engineering roles that matched on
   keywords (product managers, technical writers), student and contract roles, and caps each employer at
   10% of a role family so a few large employers cannot dominate. Removes company boilerplate by deleting
   sentences repeated across a company's postings (43% of all text was boilerplate).
2. **Skill taxonomy** ([`skillgap/taxonomy.py`](skillgap/taxonomy.py)). 137 skills in 10 categories with
   ~700 aliases, built by measuring candidate terms against the cleaned postings.
3. **Extraction** ([`skillgap/extract.py`](skillgap/extract.py)). Boundary-aware, longest-match-first
   matching with case-sensitive aliases for ambiguous words. Naive substring matching would report Rust in
   53% of postings (it matches "trust") and Scala in 42% ("scalable").

## Run it

```bash
pip install pandas scikit-learn openpyxl pytest
python -m pytest            # 41 tests
```
