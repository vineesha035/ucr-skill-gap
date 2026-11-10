"""Build a multi-program curriculum table for three UCR M.S. programs.

Sources (2025-26 academic year):
  CDS      https://datascience.engr.ucr.edu/graduate/computational-data-science/coursework
  CS       https://www1.cs.ucr.edu/sites/default/files/2024-09/program-plan-ms-9.2024.pdf
  Robotics https://robotics.ucr.edu/about/overview  (focus areas)
           https://robotics.ucr.edu/academics/graduate-courses (core)
  Course descriptions and enrollment: UCR course catalog mirror
           https://www.cs.ucr.edu/~cshelton/catalog/2025-26/courses/<SUBJ>_<NUM>.html

Input : data/raw/2026-11-06-ucr-course-catalog-raw.json  (scraped course pages)
Output: data/raw/2026-11-06-ucr-ms-curriculum.csv        (one row per program x course)

requirement values
  core         every student in the program takes it
  core_choice  student picks one course from a small set (e.g. "CS 226 or CS 236")
  capstone     required culminating course
  elective       listed option (List A/B, breadth area, or focus area, see req_group)
  elective_open  allowed through a broad elective pool, not a named program list

Deliberately excluded (no stable skill content or not enumerable):
  colloquia / professional development (CS 287, EE 259, ME 250, GDIV 403, CS 298I)
  seminars and special topics (CS 260-269, CS 270), research units (CS 290, 297, 299)
  CS 119L lab, CS 179 (E-Z) project courses, CS 178A (multi-course or variable-topic entries)
  EE 278 Advanced VLSI Systems (in the ECE graduate manual but not in the 2025-26 catalog)
  CS/EE 279 for CS and Robotics (restricted capstone of the CDS program)

Additional sources:
  CS M.S. undergrad technical electives = CS B.S. technical elective list (2025-26 catalog)
  Robotics EE electives = ECE Graduate Student Manual SSMI and VCS course lists
           https://ece.ucr.edu/media/3525/download  plus 2025-26 catalog undergrad EE focus areas
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/2026-11-06-ucr-course-catalog-raw.json"
RAW_ADDITIONS = ROOT / "data/raw/2026-11-06-ucr-course-catalog-raw-additions.json"
RAW_ADDITIONS_2 = ROOT / "data/raw/2026-11-06-ucr-course-catalog-raw-additions-2.json"
OUT = ROOT / "data/raw/2026-11-06-ucr-ms-curriculum.csv"

# Cross-listed courses are stored once under a canonical code.
CANONICAL = {
    "EE 242A": "CS 224", "EE 242B": "CS 229", "EE 251A": "CS 252A", "EE 251B": "CS 252B",
    "EE 217": "CS 217", "EE 227": "CS 258", "EE 255": "CS 251", "EE 258": "CS 256",
    "ME 236": "EE 236", "ME 231": "CS 233", "STAT 212": "CS 212",
    "EE 142": "CS 171", "EE 168": "CS 168", "EE 147": "CS 147", "EE 120B": "CS 120B",
    # EE 28x are graduate sections of undergraduate courses (identical descriptions)
    "EE 281A": "EE 150", "EE 281B": "EE 152", "EE 283A": "EE 144", "EE 283B": "EE 151",
    "EE 284A": "ENGR 160", "EE 284B": "EE 146", "EE 282A": "CS 168", "EE 282B": "EE 118",
    "EE 282C": "EE 135", "EE 282D": "EE 165",
}

# Titles the scraper could not parse (taken from the program pages).
TITLE_FIX = {
    "CS 265A": "Foundations of Robotics: Planning and Control",
    "CS 265B": "Foundations of Robotics: Sensing and Navigation",
    "EE 267": "Introduction to Autonomous Driving Systems",
    "EE 268": "Trustworthy AI for Autonomy",
    "EE 269": "Foundation Models and Advances in AI",
}

# Late addition fetched separately.
EXTRA = [{
    "code": "ME 271", "title": "Therapeutic Biomedical Microdevices", "units": "4", "xl": "", "enr": "",
    "desc": "An introduction to the application of micro device technology towards biomedical therapeutics. "
            "Topics include emerging micro device fabrication techniques, bio compatibility requirements, and "
            "applications in areas such as cardiovascular intervention, minimally- invasive drug delivery, "
            "neuroprosthetic interfaces, and cellular engineering.",
}]


def _codes(s: str) -> list[str]:
    return [c.strip() for c in s.split(",") if c.strip()]


PROGRAMS: dict[str, list[tuple[str, str, list[str]]]] = {
    # (requirement, req_group, courses)
    "MS Computational Data Science": [
        ("core", "Core", _codes("CS 252A, CS 235, CS 212")),
        ("core_choice", "Core: CS 252B or CS 224", _codes("CS 252B, CS 224")),
        ("core_choice", "Core: CS 226 or CS 236", _codes("CS 226, CS 236")),
        ("capstone", "Capstone", _codes("CS 279")),
        ("elective", "Elective List A", _codes(
            "CS 205, CS 222, CS 225, CS 227, CS 228, CS 229, CS 242, CS 248, CS 258, "
            "EE 231, EE 236, EE 240, EE 244, EE 268, EE 269")),
        ("elective", "Elective List B", _codes(
            "CS 210, CS 211, CS 217, CS 234, EE 241, EE 243, EE 250, EE 267")),
    ],
    "MS Computer Science": [
        ("core_choice", "Core: Hardware design principles", _codes("CS 203, CS 220")),
        ("core_choice", "Core: Theoretical foundations", _codes("CS 215, CS 218")),
        ("core_choice", "Core: Software and systems", _codes("CS 201, CS 202")),
        # Breadth lists copied from the 2025-26 catalog (CS section, "Major Specialty Areas").
        ("elective", "Breadth A: Algorithms, Bioinformatics, Theory", _codes(
            "CS 214, CS 215, CS 218, CS 219, CS 234, CS 238")),
        ("elective", "Breadth B: Architecture, Embedded, CAD", _codes(
            "CS 203, CS 213, CS 220, CS 223, CS 217, EE 213, CS 251, EE 255")),
        ("elective", "Breadth C: Databases, Data Mining, ML", _codes(
            "CS 205, CS 222, CS 224, CS 225, CS 226, CS 227, CS 229, CS 235, CS 236, CS 242, "
            "CS 228, CS 248, CS 252A, CS 258, EE 243, EE 267, EE 268")),
        ("elective", "Breadth D: Operating and Distributed Systems", _codes(
            "CS 202, CS 211, CS 237, CS 253, CS 255")),
        ("elective", "Breadth E: Computer Networks", _codes(
            "CS 204, CS 208, CS 237, CS 239, CS 240, CS 241, CS 254, CS 255, CS 257")),
        ("elective", "Breadth F: Programming Languages, Software Eng.", _codes(
            "CS 201, CS 206, CS 207, CS 246, CS 249")),
        ("elective", "Breadth G: Graphics and HCI", _codes("CS 210, CS 230, CS 231, CS 233, ME 230, ME 231")),
        ("elective", "Breadth H: Cybersecurity", _codes("CS 216, CS 250, CS 254, CS 255")),
        ("elective_open", "Elective: other graduate CS lecture", _codes(
            "CS 212, CS 247, CS 252B, CS 256, CS 265A, CS 265B, CS 277")),
        ("elective_open", "Elective: approved undergrad technical electives (CS B.S. list)", _codes(
            "CS 105, CS 108, CS 110, CS 120B, CS 122A, CS 122B, CS 130, CS 131, CS 133, CS 135, CS 142, "
            "CS 144, CS 145, CS 147, CS 160, CS 162, CS 164, CS 165, CS 166, CS 167, CS 168, CS 169, "
            "CS 170, CS 171, CS 172, CS 173, CS 175, CS 177, CS 178B, CS 180, CS 181, CS 182, CS 183, "
            "CS 193, MATH 120, MATH 126, MATH 135A, MATH 135B, PHIL 124")),
    ],
    # Focus lists = union of the 2025-26 catalog and robotics.ucr.edu (the two differ slightly).
    "MS Robotics": [
        ("core", "Core", _codes("CS 224, CS 265A, CS 265B, ME 224, ME 225")),
        ("elective", "Focus 1: Embodied AI and Machine Learning", _codes(
            "CS 170, CS 171, CS 173, CS 205, CS 222, CS 277, CS 228, CS 229, CS 235, CS 248, CS 258, "
            "EE 146, EE 236, EE 241, EE 243, EE 244, EE 247, EE 250, EE 267, EE 268, EE 269, ME 202, ME 233")),
        ("elective", "Focus 2: Motion Planning and Autonomous Navigation", _codes(
            "CS 258, EE 132, ME 121, EE 144, EE 151, EE 231, EE 235, EE 236, EE 237, EE 238, EE 239, "
            "EE 246, EE 267, EE 268, ME 145, ME 220, ME 221, ME 223, ME 233")),
        ("elective", "Focus 3: Robot Design and System Integration", _codes(
            "CS 131, CS 135, CS 256, EE 128, CS 217, EE 246, EE 252, CS 251, EE 267, ME 174, ME 175B, "
            "ME 175C, ME 210, ME 230, ME 232, ME 233, ME 271")),
        ("elective_open", "Elective: ME list", _codes(
            "ME 114, ME 118, ME 120, ME 130, ME 133, ME 153, ME 176, ME 200, ME 201, ME 203, ME 210, "
            "CS 233, ME 233, ME 270, ME 274")),
        ("elective_open", "Elective: CS breadth C, D, E", _codes(
            "CS 226, CS 227, CS 236, CS 242, CS 252A, CS 225, CS 211, CS 237, CS 253, CS 255, "
            "CS 204, CS 208, CS 239, CS 240, CS 241, CS 254, CS 257")),
        ("elective_open", "Elective: EE Graduate Manual SSMI", _codes(
            "EE 215, EE 230, EE 231, EE 235, CS 224, EE 224, EE 226, CS 258, CS 228, EE 232, EE 234, "
            "EE 236, EE 240, EE 241, CS 229, EE 243, EE 244, EE 246, CS 248, EE 249, EE 250, EE 252, "
            "EE 253, CS 256, CS 265A, CS 265B, EE 267, EE 268, EE 269, EE 281A, EE 281B, EE 283A, "
            "EE 283B, EE 284A, EE 284B, EE 286A, EE 286B, EE 286C")),
        ("elective_open", "Elective: EE Graduate Manual VCS", _codes(
            "EE 213, CS 217, CS 251, CS 203, EE 201, EE 202, EE 203, EE 214, EE 221, CS 277, CS 202, "
            "CS 218, CS 220, EE 282A, EE 282B, EE 282C, EE 282D")),
        ("elective_open", "Elective: undergrad EE focus areas", _codes(
            # Communications, Signal Processing and Networking
            "EE 115, EE 141, EE 100B, EE 117, EE 118, EE 146, EE 150, EE 152, ENGR 160, "
            # Control and Robotics + Intelligent Systems
            "EE 105, EE 144, EE 106, ME 145, EE 151, EE 128, CS 147, "
            # Embedded Systems and VLSI
            "CS 168, EE 135, EE 165, CS 161, CS 162")),
        ("elective_open", "Elective: undergrad CS", _codes("CS 172")),
    ],
}

# Sentences that are enrollment rules, not course content.
_ADMIN = re.compile(r"online section|graduate standing|consent of instructor|may be taken concurrently|"
                    r"^Cross-listing:?$", re.I)


def clean_description(desc: str) -> str:
    desc = re.sub(r"\s+", " ", desc).strip().lstrip(";").strip()
    desc = re.sub(r"\s*Cross-listing:.*$", "", desc)
    desc = re.sub(r"(\w)- (\w)", r"\1-\2", desc)  # "real- world" -> "real-world"
    sentences = re.split(r"(?<=[.;])\s+(?=[A-Z])", desc)
    kept = [s for s in sentences if not _ADMIN.search(s)]
    return " ".join(kept).strip()


def load_courses() -> dict[str, dict]:
    rows = (json.loads(RAW.read_text()) + json.loads(RAW_ADDITIONS.read_text())
            + json.loads(RAW_ADDITIONS_2.read_text()) + EXTRA)
    courses: dict[str, dict] = {}
    for r in rows:
        if r.get("err"):
            continue
        code = CANONICAL.get(r["code"], r["code"])
        if code in courses:
            continue
        courses[code] = {
            "title": TITLE_FIX.get(r["code"], r["title"]).strip(),
            "credits": int(r["units"]) if str(r["units"]).isdigit() else 4,
            "cross_listed": r.get("xl", ""),
            "description": clean_description(r["desc"]),
            "enrollment_2025_26": _enrollment_total(r.get("enr", "")),
        }
    return courses


def _enrollment_total(enr: str) -> str:
    """The last 'filled/capacity' pair on the catalog's enrollment row is the year total."""
    pairs = re.findall(r"(\d+)\s*/\s*(\d+)", enr)
    return pairs[-1][0] if pairs else ""


def build() -> list[dict]:
    courses = load_courses()
    out, missing = [], []
    for program, groups in PROGRAMS.items():
        seen: set[str] = set()
        for requirement, group, codes in groups:
            for code in codes:
                code = CANONICAL.get(code, code)
                if code not in courses:
                    missing.append(f"{program}: {code}")
                    continue
                if code in seen:  # keep the strongest requirement level
                    continue
                seen.add(code)
                c = courses[code]
                out.append({"program": program, "course_code": code, "title": c["title"],
                            "credits": c["credits"], "requirement": requirement, "req_group": group,
                            "cross_listed": c["cross_listed"], "enrollment_2025_26": c["enrollment_2025_26"],
                            "description": c["description"]})
    if missing:
        raise SystemExit("Missing course data: " + ", ".join(missing))
    return out


def main() -> None:
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
