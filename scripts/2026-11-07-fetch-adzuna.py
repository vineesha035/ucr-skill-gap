"""Fetch real US job postings from the Adzuna API for the skill-gap analysis.

Uses only the Python standard library (no pip install needed).

Setup (Windows PowerShell):
    $env:ADZUNA_APP_ID  = "your_app_id"
    $env:ADZUNA_APP_KEY = "your_app_key"
    python scripts\\2026-11-07-fetch-adzuna.py

Options:
    --pages N     max result pages per search term (50 postings per page, default 6)
    --out PATH    output file (default data/raw/2026-11-07-adzuna-postings.jsonl)
    --dry-run     fetch only page 1 of the first search term, to test your keys

Free-tier limits are about 25 requests/minute and 250/day. The defaults use at most
19 terms x 6 pages = 114 requests, paced at one request every 3 seconds (~6 minutes).
The script is resumable: rerunning skips search terms already completed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/raw/2026-11-07-adzuna-postings.jsonl"
API = "https://api.adzuna.com/v1/api/jobs/us/search/{page}"
PER_PAGE = 50
PAUSE_SECONDS = 3.0

# role family -> search terms (matched against the job title only)
SEARCHES: dict[str, list[str]] = {
    "data_science": [
        "data scientist", "machine learning engineer", "data engineer", "data analyst",
        "AI engineer", "applied scientist", "analytics engineer",
    ],
    "software": [
        "software engineer", "backend engineer", "full stack developer", "cloud engineer",
        "platform engineer",
    ],
    "robotics": [
        "robotics engineer", "autonomy engineer", "perception engineer", "controls engineer",
        "computer vision engineer", "embedded software engineer", "motion planning engineer",
    ],
}


def fetch_page(app_id: str, app_key: str, term: str, page: int) -> dict:
    params = urllib.parse.urlencode({
        "app_id": app_id, "app_key": app_key, "results_per_page": PER_PAGE,
        "title_only": term, "content-type": "application/json", "sort_by": "date",
    })
    url = API.format(page=page) + "?" + params
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                sys.exit("Adzuna rejected the keys (HTTP %d). Check ADZUNA_APP_ID and ADZUNA_APP_KEY." % e.code)
            if e.code == 429 or e.code >= 500:
                wait = 30 * (attempt + 1)
                print(f"    HTTP {e.code}, waiting {wait}s and retrying")
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as e:
            print(f"    network error ({e.reason}), retrying in 15s")
            time.sleep(15)
        except (ConnectionError, TimeoutError, OSError) as e:  # e.g. WinError 10054 connection reset
            print(f"    connection dropped ({type(e).__name__}), retrying in 15s")
            time.sleep(15)
    raise RuntimeError(f"giving up on '{term}' page {page}. Rerun the script to resume.")


def to_record(job: dict, family: str, term: str) -> dict:
    return {
        "id": str(job.get("id", "")),
        "title": job.get("title", ""),
        "company": (job.get("company") or {}).get("display_name", ""),
        "location": (job.get("location") or {}).get("display_name", ""),
        "posted_date": job.get("created", ""),
        "description": job.get("description", ""),
        "category": (job.get("category") or {}).get("label", ""),
        "contract_time": job.get("contract_time", ""),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "url": job.get("redirect_url", ""),
        "role_family": family,
        "search_term": term,
    }


def load_existing(out: Path) -> tuple[set[str], set[tuple[str, str]], set[str]]:
    ids, title_company, done_terms = set(), set(), set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("_term_done"):
                done_terms.add(r["_term_done"])
                continue
            ids.add(r["id"])
            title_company.add((r["title"].lower().strip(), r["company"].lower().strip()))
    return ids, title_company, done_terms


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=6)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        sys.exit("Set ADZUNA_APP_ID and ADZUNA_APP_KEY first (see the top of this file).")

    if args.dry_run:
        data = fetch_page(app_id, app_key, "data scientist", 1)
        jobs = data.get("results", [])
        print(f"Keys work. {data.get('count', 0)} matching postings, page 1 returned {len(jobs)}.")
        if jobs:
            r = to_record(jobs[0], "data_science", "data scientist")
            print(f"Example: {r['title']} at {r['company']} ({r['location']})")
            print(f"Description length: {len(r['description'])} characters")
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    ids, title_company, done_terms = load_existing(args.out)
    total_new = 0

    with args.out.open("a", encoding="utf-8") as f:
        for family, terms in SEARCHES.items():
            for term in terms:
                key = f"{family}:{term}"
                if key in done_terms:
                    print(f"skip  {term} (already fetched)")
                    continue
                new_for_term = 0
                for page in range(1, args.pages + 1):
                    data = fetch_page(app_id, app_key, term, page)
                    jobs = data.get("results", [])
                    for job in jobs:
                        r = to_record(job, family, term)
                        tc = (r["title"].lower().strip(), r["company"].lower().strip())
                        if not r["id"] or r["id"] in ids or tc in title_company:
                            continue
                        ids.add(r["id"])
                        title_company.add(tc)
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        new_for_term += 1
                    f.flush()
                    time.sleep(PAUSE_SECONDS)
                    if len(jobs) < PER_PAGE:
                        break
                f.write(json.dumps({"_term_done": key}) + "\n")
                f.flush()
                total_new += new_for_term
                print(f"done  {term:<28} +{new_for_term:>4} new  (total {len(ids)})")

    print(f"\nFinished. {total_new} new postings this run, {len(ids)} total in {args.out}")


if __name__ == "__main__":
    main()
