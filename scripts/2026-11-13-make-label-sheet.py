"""Create the hand-labeling workbook used to measure extraction precision and recall.

Samples 30 analyzed postings (10 per role family, fixed seed) and writes
data/labels/2026-11-13-label-sheet.xlsx with three sheets:
  precision  one row per extracted skill: mark is_correct Y or N
  recall     one row per posting: list taxonomy skills the extractor MISSED
  taxonomy   reference list of every skill name and its category
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from skillgap.clean import clean_postings
from skillgap.extract import SkillMatcher
from skillgap.io import load_postings
from skillgap.taxonomy import SKILLS

OUT = Path(__file__).resolve().parents[1] / "data/labels/2026-11-13-label-sheet.xlsx"
SEED, PER_FAMILY = 13, 10


def main() -> None:
    df = clean_postings(load_postings())
    df = df[df.excluded == ""]
    sample = (df.groupby("role_family").sample(PER_FAMILY, random_state=SEED)
                .sort_values("role_family").reset_index(drop=True))
    m = SkillMatcher()
    wb = Workbook()
    head, fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="305496")
    wrap = Alignment(wrap_text=True, vertical="top")

    ws = wb.active
    ws.title = "precision"
    ws.append(["posting_no", "history_id", "role_family", "title", "skill", "matched_text", "context", "is_correct (Y/N)"])
    for i, r in sample.iterrows():
        seen = set()
        for mt in m.find(r.description):
            if mt.skill in seen:
                continue
            seen.add(mt.skill)
            ctx = r.description[max(0, mt.start - 90): mt.end + 90]
            ws.append([i + 1, r.history_id, r.role_family, r.title, mt.skill, mt.text, f"...{ctx}...", ""])
    dv = DataValidation(type="list", formula1='"Y,N"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"H2:H{ws.max_row}")

    wr = wb.create_sheet("recall")
    wr.append(["posting_no", "history_id", "role_family", "title", "skills_extracted", "description",
               "missed_skills (taxonomy names, separated by ;)"])
    for i, r in sample.iterrows():
        found = sorted(m.skills_in(r.description))
        wr.append([i + 1, r.history_id, r.role_family, r.title, "; ".join(found), r.description, ""])

    wt = wb.create_sheet("taxonomy")
    wt.append(["skill", "category", "example aliases"])
    for s in SKILLS:
        wt.append([s.name, s.category, ", ".join([a.lstrip("=") for a in s.aliases if not a.startswith("re")][:6])])

    widths = {"precision": [8, 22, 12, 30, 26, 18, 70, 12], "recall": [8, 22, 12, 30, 40, 100, 40],
              "taxonomy": [36, 30, 70]}
    for sheet in wb.worksheets:
        for c in sheet[1]:
            c.font, c.fill = head, fill
        for col, w in zip("ABCDEFGH", widths[sheet.title]):
            sheet.column_dimensions[col].width = w
        for row in sheet.iter_rows(min_row=2):
            for c in row:
                c.alignment = wrap
        sheet.freeze_panes = "A2"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"{len(sample)} postings, {wb['precision'].max_row - 1} extracted skills to check -> {OUT}")


if __name__ == "__main__":
    main()
