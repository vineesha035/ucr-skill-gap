"""Check that every course code named in the official 2025-26 catalog program text
appears in the curriculum CSV for that program.

The catalog text lives in tests/2026-11-07-catalog-text.json (copied from the
UCR catalog program sections). Run:  python -m pytest tests/
"""

import importlib.util
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("build", ROOT / "scripts/2026-11-06-build-curriculum.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

CANON = dict(build.CANONICAL) | {
    "EE 228": "CS 228", "EE 248": "CS 248", "EE 252A": "CS 252A", "EE 265A": "CS 265A",
    "EE 265B": "CS 265B", "EE 131": "CS 131", "EE 145": "ME 145", "EE 279": "CS 279",
}
TEXT = json.loads((ROOT / "tests/2026-11-07-catalog-text.json").read_text())
CURRICULUM = pd.read_csv(ROOT / "data/raw/2026-11-06-ucr-ms-curriculum.csv")


def catalog_codes(text: str) -> set[str]:
    text = re.sub(r"\b([A-Z]+)/([A-Z]+) (\d+\w?)", r"\1 \3/\2 \3", text)  # "CS/EE 228" -> both codes
    found = re.findall(r"\b(?:CS|EE|ME|STAT|MATH|PHIL|ENGR) \d+[A-Z]?\b", text)
    return {CANON.get(c, c) for c in found}


def _missing(program: str, *keys: str) -> set[str]:
    need = set().union(*(catalog_codes(TEXT[k]) for k in keys))
    have = set(CURRICULUM.loc[CURRICULUM.program == program, "course_code"])
    return need - have


def test_cds_complete():
    assert _missing("MS Computational Data Science", "CDS") == set()


def test_cs_complete():
    assert _missing("MS Computer Science", "CS_core", "CS_areas", "CS_TE") == set()


def test_robotics_complete():
    assert _missing("MS Robotics", "ROB") == set()


def test_robotics_includes_cs_areas_cde():
    cde = re.search(r"C\. (.*) F\. ", TEXT["CS_areas"]).group(1)
    have = set(CURRICULUM.loc[CURRICULUM.program == "MS Robotics", "course_code"])
    assert catalog_codes(cde) - have == set()


def test_no_duplicate_rows():
    assert not CURRICULUM.duplicated(["program", "course_code"]).any()
