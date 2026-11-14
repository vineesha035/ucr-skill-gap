"""Daily collection step: fetch postings, then update the posting history.

Runs both collectors into temporary files, then updates data/history/:

  new/<date>-<source>.jsonl.gz   postings first seen on <date> (full record, stored once).
                                 Full posting text belongs to the employers, so these shards
                                 live in a PRIVATE data repo: set SKILLGAP_RAW_DIR to its
                                 folder (default data/history/new for local use).
  seen.csv.gz                    one row per posting: id, source, role_family, company,
                                 first_seen, last_seen
  daily_counts.csv               one row per run and source: fetched, new, still_open
  latest_new_postings.csv        readable list of postings first seen on the latest run
  open_board_postings.csv        readable list of company-board postings still open
                                 (GitHub renders both CSVs as searchable tables)

A company-board posting whose last_seen is older than the latest run has closed.
(Adzuna only returns the newest pages per search, so absence from Adzuna does NOT
mean the job closed. Closure analysis uses company boards only.)

Usage:
  python scripts/2026-11-09-collect-daily.py                       # normal daily run
  python scripts/2026-11-09-collect-daily.py --seed FILE --source boards --date 2026-11-07
                                                                   # import an existing snapshot
  python scripts/2026-11-09-collect-daily.py --views-only        # rebuild the two CSVs only
Adzuna is skipped when ADZUNA_APP_ID / ADZUNA_APP_KEY are not set.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "data/history"
SEEN = HIST / "seen.csv.gz"
COUNTS = HIST / "daily_counts.csv"
RAW_DIR = Path(os.environ.get("SKILLGAP_RAW_DIR", HIST / "new"))
SEEN_FIELDS = ["id", "source", "role_family", "company", "first_seen", "last_seen"]

FETCHERS = {
    "boards": ROOT / "scripts/2026-11-07-fetch-company-boards.py",
    "adzuna": ROOT / "scripts/2026-11-07-fetch-adzuna.py",
}


def write_gz(path: Path, text: str) -> None:
    """gzip with a fixed timestamp so identical content gives identical bytes (clean git diffs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        gz.write(text.encode("utf-8"))


def load_seen() -> dict[str, dict]:
    if not SEEN.exists():
        return {}
    with gzip.open(SEEN, "rt", encoding="utf-8", newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def save_seen(seen: dict[str, dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SEEN_FIELDS, lineterminator="\n")
    w.writeheader()
    for key in sorted(seen):
        w.writerow({k: seen[key].get(k, "") for k in SEEN_FIELDS})
    write_gz(SEEN, buf.getvalue())


def read_records(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if "id" in r:                     # skip resume markers
                out.append(r)
    return out


def fetch(source: str, tmpdir: Path) -> list[dict] | None:
    if source == "adzuna" and not (os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY")):
        print("adzuna: keys not set, skipping")
        return None
    out = tmpdir / f"{source}.jsonl"
    result = subprocess.run([sys.executable, str(FETCHERS[source]), "--out", str(out)])
    if result.returncode != 0 or not out.exists():
        print(f"{source}: fetch failed (exit {result.returncode}), skipping this source today")
        return None
    return read_records(out)


def update(source: str, records: list[dict], date: str, seen: dict[str, dict]) -> dict:
    prefix = "az-" if source == "adzuna" else ""     # Adzuna ids are bare numbers
    new_rows, fetched_ids = [], set()
    for r in records:
        key = prefix + str(r["id"])
        if key in fetched_ids:
            continue
        fetched_ids.add(key)
        if key in seen:
            seen[key]["last_seen"] = max(seen[key]["last_seen"], date)
        else:
            seen[key] = {"id": key, "source": source, "role_family": r.get("role_family", ""),
                         "company": r.get("company", ""), "first_seen": date, "last_seen": date}
            new_rows.append({**r, "history_id": key, "first_seen": date})
    if new_rows:
        shard = RAW_DIR / f"{date}-{source}.jsonl.gz"
        existing = gzip.open(shard, "rt", encoding="utf-8").read() if shard.exists() else ""
        # a same-day rerun appends to the day's shard instead of replacing it
        write_gz(shard, existing + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_rows))
    still_open = sum(1 for s in seen.values() if s["source"] == source and s["last_seen"] == date)
    return {"date": date, "source": source, "fetched": len(fetched_ids), "new": len(new_rows),
            "still_open": still_open}


VIEW_FIELDS = ["first_seen", "source", "role_family", "company", "title", "location", "url"]


def _shard_rows(pattern: str) -> list[dict]:
    rows = []
    for shard in sorted(RAW_DIR.glob(pattern)):
        with gzip.open(shard, "rt", encoding="utf-8") as f:
            rows += [json.loads(line) for line in f if line.strip()]
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=VIEW_FIELDS, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_views(seen: dict[str, dict]) -> None:
    """Human-readable CSVs for browsing on GitHub (no descriptions, to stay small)."""
    if not seen:
        return
    latest = max(s["last_seen"] for s in seen.values())
    for r in (rows := _shard_rows(f"{latest}-*.jsonl.gz")):
        r["source"] = seen.get(r.get("history_id", ""), {}).get("source", "")
    rows.sort(key=lambda r: (r["source"], r.get("role_family", ""), r.get("company", "")))
    _write_csv(HIST / "latest_new_postings.csv", rows)

    open_ids = {k for k, s in seen.items() if s["source"] == "boards" and s["last_seen"] == latest}
    board = [r for r in _shard_rows("*-boards.jsonl.gz") if r.get("history_id") in open_ids]
    for r in board:
        r["source"] = "boards"
    board.sort(key=lambda r: (r["first_seen"], r.get("company", "")), reverse=True)
    _write_csv(HIST / "open_board_postings.csv", board)
    print(f"views: {len(rows)} new on {latest}, {len(board)} open company-board postings")


def append_counts(rows: list[dict]) -> None:
    """Add today's rows. A same-day rerun replaces that day's row and adds the new count."""
    fields = ["date", "source", "fetched", "new", "still_open"]
    old = list(csv.DictReader(COUNTS.open(encoding="utf-8"))) if COUNTS.exists() else []
    index = {(r["date"], r["source"]): r for r in old}
    for r in rows:
        prev = index.get((r["date"], r["source"]))
        if prev:
            r = {**r, "new": int(prev["new"]) + int(r["new"])}
        index[(r["date"], r["source"])] = r
    COUNTS.parent.mkdir(parents=True, exist_ok=True)
    with COUNTS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(index.values(), key=lambda r: (r["date"], r["source"])))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    ap.add_argument("--seed", type=Path, help="import an existing snapshot file instead of fetching")
    ap.add_argument("--source", choices=sorted(FETCHERS), help="source of the --seed file")
    ap.add_argument("--views-only", action="store_true", help="only rebuild the readable CSVs")
    args = ap.parse_args()

    seen = load_seen()
    if args.views_only:
        write_views(seen)
        return
    counts = []
    if args.seed:
        if not args.source:
            sys.exit("--seed needs --source")
        counts.append(update(args.source, read_records(args.seed), args.date, seen))
    else:
        with tempfile.TemporaryDirectory() as td:
            for source in FETCHERS:
                records = fetch(source, Path(td))
                if records:
                    counts.append(update(source, records, args.date, seen))
    if not counts:
        sys.exit("No source produced data. Nothing written.")
    save_seen(seen)
    append_counts(counts)
    write_views(seen)
    for c in counts:
        print(f"{c['date']} {c['source']:<7} fetched {c['fetched']:>5}  new {c['new']:>5}  open {c['still_open']:>5}")


if __name__ == "__main__":
    main()
