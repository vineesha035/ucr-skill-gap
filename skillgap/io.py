"""Loaders for posting history and the curriculum table."""

from __future__ import annotations

import gzip
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data/history"
CURRICULUM = ROOT / "data/raw/2026-11-06-ucr-ms-curriculum.csv"


def raw_dir() -> Path:
    """Folder with the full-text shards. Locally this is your clone of the private data repo."""
    env = os.environ.get("SKILLGAP_RAW_DIR")
    if env:
        return Path(env)
    sibling = ROOT.parent / "ucr-skill-gap-data" / "new"
    return sibling if sibling.exists() else HISTORY / "new"


def load_seen(path: Path = HISTORY / "seen.csv.gz") -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def load_postings(source: str = "boards", open_only: bool = True,
                  shards: Path | None = None, seen_path: Path = HISTORY / "seen.csv.gz") -> pd.DataFrame:
    """Full posting records joined to their first/last seen dates.

    open_only=True keeps postings seen on the latest collection date (still open).
    """
    shards = shards or raw_dir()
    rows = []
    for f in sorted(shards.glob(f"*-{source}.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            rows += [json.loads(line) for line in fh if line.strip()]
    if not rows:
        raise FileNotFoundError(f"No {source} shards in {shards}. Clone ucr-skill-gap-data next to this repo "
                                "or set SKILLGAP_RAW_DIR.")
    df = pd.DataFrame(rows)
    seen = load_seen(seen_path)[["id", "first_seen", "last_seen"]]
    df = df.drop(columns=[c for c in ("first_seen",) if c in df]).merge(
        seen, left_on="history_id", right_on="id", how="left", suffixes=("", "_seen")).drop(columns="id_seen")
    if open_only:
        df = df[df["last_seen"] == seen["last_seen"].max()]
    for col in ("title", "description", "company", "location"):
        df[col] = df[col].fillna("")
    return df.reset_index(drop=True)


def load_curriculum(path: Path = CURRICULUM) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"enrollment_2025_26": "Int64"})
    df["description"] = df["description"].fillna("")
    return df
