"""Collect FULL-TEXT job postings from company career boards (Greenhouse, Lever, Ashby).

Why: the Adzuna free API truncates descriptions to 500 characters, which cuts off the
requirements section where most skills are listed. These three applicant-tracking
systems publish public job-board APIs that return the complete posting, no key needed.

Uses only the Python standard library.

Run (Windows PowerShell, from the project folder):
    python scripts\\2026-11-07-fetch-company-boards.py

Options:
    --out PATH        output file (default data/raw/2026-11-07-company-board-postings.jsonl)
    --all-titles      keep every posting, not only data science / software / robotics roles
    --only NAME       fetch a single board, e.g. --only greenhouse:databricks (for testing)

Board names that do not exist are reported and skipped. Edit BOARDS to add companies:
the token is the last part of the company's job-board URL, e.g.
    job-boards.greenhouse.io/databricks  ->  greenhouse: "databricks"
    jobs.lever.co/palantir               ->  lever: "palantir"
    jobs.ashbyhq.com/openai              ->  ashby: "openai"
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/raw/2026-11-07-company-board-postings.jsonl"
PAUSE_SECONDS = 1.0

# Mix of data/AI, software, and robotics/autonomy employers. Unknown tokens are skipped.
BOARDS: dict[str, list[str]] = {
    "greenhouse": [
        # data / AI / software
        "databricks", "stripe", "airbnb", "figma", "anthropic", "scaleai", "robinhood", "instacart",
        "pinterest", "dropbox", "lyft", "discord", "reddit", "coinbase", "cloudflare", "datadog",
        "mongodb", "gitlab", "samsara", "verkada", "affirm", "chime", "brex", "twilio", "asana",
        "airtable", "carta", "gusto", "okta", "snowflake", "doordashusa", "roblox", "duolingo",
        # robotics / autonomy / hardware
        "waymo", "nuro", "andurilindustries", "appliedintuition", "aurorainnovation", "motional",
        "agilityrobotics", "bostondynamics", "skydio", "flyzipline", "figureai", "anybotics",
        "intuitivesurgical", "relativity", "spacex", "saronic", "formicvc",
    ],
    "lever": [
        "palantir", "shieldai", "plaid", "kodiak", "matterport", "mistral", "zoox",
        "wisk", "outrider", "dexterity", "covariant", "vecna",
    ],
    "ashby": [
        "openai", "notion", "ramp", "linear", "cohere", "perplexity", "replit", "harvey",
        "modal", "anyscale", "physicalintelligence", "1x", "bear-robotics", "skild-ai",
    ],
}

# Title filters -> role family. A posting is kept if its title matches any pattern.
ROLE_PATTERNS: dict[str, re.Pattern] = {
    "robotics": re.compile(
        r"robot|autonom|perception|motion planning|\bslam\b|controls? engineer|computer vision|"
        r"embedded|firmware|localization|mechatronic|\bgnc\b|guidance", re.I),
    "data_science": re.compile(
        r"data scien|machine learning|\bml\b|\bai\b|artificial intelligence|data engineer|"
        r"data analy|analytics engineer|applied scien|research scien|deep learning|\bnlp\b|\bllm", re.I),
    "software": re.compile(
        r"software engineer|software developer|backend|back-end|full[ -]?stack|platform engineer|"
        r"infrastructure engineer|cloud engineer|site reliability|\bsre\b|devops|distributed systems", re.I),
}
EXCLUDE_TITLE = re.compile(r"\b(intern|internship|recruiter|sales|account executive|marketing|"
                           r"counsel|legal|designer|director of|vp\b|vice president|head of)\b", re.I)

US_HINT = re.compile(r"\b(united states|usa|u\.s\.|remote|[A-Z]{2}$)|"
                     r"\b(CA|NY|WA|TX|MA|CO|IL|PA|GA|VA|NC|OR|AZ|MI|FL|NJ|MD|UT|MN|OH|DC)\b|"
                     r"san francisco|new york|seattle|boston|austin|los angeles|mountain view|"
                     r"palo alto|pittsburgh|denver|chicago|san jose|sunnyvale|menlo park|"
                     r"redwood city|san mateo|irvine|san diego|atlanta|washington", re.I)
NON_US = re.compile(r"london|toronto|vancouver|montreal|dublin|berlin|munich|paris|amsterdam|"
                    r"bangalore|bengaluru|hyderabad|pune|india|singapore|tokyo|sydney|zurich|"
                    r"tel aviv|warsaw|madrid|barcelona|stockholm|mexico|brazil|são paulo|uk\b|"
                    r"canada|germany|ireland|japan|australia|israel|poland|switzerland", re.I)


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "skill-gap-research/1.0", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
            if e.code == 429 or e.code >= 500:
                time.sleep(15 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(5)
        except (ConnectionError, TimeoutError, OSError):  # e.g. WinError 10054 connection reset
            time.sleep(10)
    return None


def html_to_text(s: str) -> str:
    s = html.unescape(s or "")              # Greenhouse double-escapes HTML
    s = re.sub(r"<\s*(br|/p|/li|/h\d|/div)\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n- ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def iso_from_ms(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return ""


# ---- per-platform parsers -> common record ------------------------------------------

def fetch_greenhouse(token: str) -> list[dict] | None:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
    if not data or "jobs" not in data:
        return None
    return [{
        "id": f"gh-{token}-{j.get('id')}",
        "title": j.get("title", ""),
        "company": token,
        "location": (j.get("location") or {}).get("name", ""),
        "posted_date": j.get("first_published") or j.get("updated_at", ""),
        "description": html_to_text(j.get("content", "")),
        "url": j.get("absolute_url", ""),
        "source": "greenhouse",
    } for j in data["jobs"]]


def fetch_lever(token: str) -> list[dict] | None:
    data = get_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
    if not isinstance(data, list):
        return None
    out = []
    for j in data:
        parts = [j.get("descriptionPlain", "")]
        for block in j.get("lists", []) or []:
            parts.append(block.get("text", ""))
            parts.append(html_to_text(block.get("content", "")))
        parts.append(j.get("additionalPlain", ""))
        out.append({
            "id": f"lv-{token}-{j.get('id')}",
            "title": j.get("text", ""),
            "company": token,
            "location": (j.get("categories") or {}).get("location", ""),
            "posted_date": iso_from_ms(j.get("createdAt")),
            "description": "\n".join(p for p in parts if p).strip(),
            "url": j.get("hostedUrl", ""),
            "source": "lever",
        })
    return out


def fetch_ashby(token: str) -> list[dict] | None:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}")
    if not data or "jobs" not in data:
        return None
    return [{
        "id": f"ab-{token}-{j.get('id')}",
        "title": j.get("title", ""),
        "company": token,
        "location": j.get("location", "") or "",
        "posted_date": j.get("publishedAt", ""),
        "description": j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml", "")),
        "url": j.get("jobUrl", ""),
        "source": "ashby",
    } for j in data["jobs"] if j.get("isListed", True)]


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}


# ---- filtering ------------------------------------------------------------------------

def role_family(title: str) -> str | None:
    if EXCLUDE_TITLE.search(title):
        return None
    for family, pat in ROLE_PATTERNS.items():   # robotics checked first: "robotics ML engineer" -> robotics
        if pat.search(title):
            return family
    return None


def is_us(location: str) -> bool:
    if not location:
        return True                             # unknown kept, flagged by loader later
    if NON_US.search(location) and not re.search(r"united states|\busa\b|remote.*us", location, re.I):
        return False
    return bool(US_HINT.search(location)) or "remote" in location.lower()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--all-titles", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args()

    boards = [(p, t) for p, toks in BOARDS.items() for t in toks]
    if args.only:
        p, _, t = args.only.partition(":")
        boards = [(p, t)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if args.out.exists():
        seen = {json.loads(l)["id"] for l in args.out.read_text(encoding="utf-8").splitlines() if l.strip()}

    missing, kept_total = [], 0
    with args.out.open("a", encoding="utf-8") as f:
        for platform, token in boards:
            jobs = FETCHERS[platform](token)
            time.sleep(PAUSE_SECONDS)
            if jobs is None:
                missing.append(f"{platform}:{token}")
                print(f"miss  {platform}:{token}")
                continue
            kept = 0
            for r in jobs:
                fam = role_family(r["title"])
                if (fam is None and not args.all_titles) or not is_us(r["location"]) or r["id"] in seen:
                    continue
                r["role_family"] = fam or "other"
                r["fetched_at"] = datetime.now(timezone.utc).date().isoformat()
                seen.add(r["id"])
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                kept += 1
            f.flush()
            kept_total += kept
            print(f"ok    {platform}:{token:<22} {len(jobs):>5} postings, kept {kept:>4}")

    print(f"\nFinished. Kept {kept_total} new postings, {len(seen)} total in {args.out}")
    if missing:
        print(f"{len(missing)} boards not found (wrong token or no public board): {', '.join(missing)}")


if __name__ == "__main__":
    main()
