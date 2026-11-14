"""Compute extraction precision and recall from the filled-in labeling workbook.

precision = extracted skills marked Y / extracted skills marked Y or N
recall    = correct extractions / (correct extractions + skills listed as missed)

Usage:  python scripts/2026-11-13-score-labels.py [path-to-filled-workbook]
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

DEFAULT = Path(__file__).resolve().parents[1] / "data/labels/2026-11-13-label-sheet.xlsx"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    wb = load_workbook(path, read_only=True)
    tp = fp = 0
    wrong: Counter = Counter()
    by_family: dict[str, list[int]] = {}
    for row in wb["precision"].iter_rows(min_row=2, values_only=True):
        family, skill, mark = row[2], row[4], str(row[7] or "").strip().upper()
        if mark not in ("Y", "N"):
            continue
        fam = by_family.setdefault(family, [0, 0, 0])
        if mark == "Y":
            tp += 1
            fam[0] += 1
        else:
            fp += 1
            fam[1] += 1
            wrong[skill] += 1
    missed: Counter = Counter()
    for row in wb["recall"].iter_rows(min_row=2, values_only=True):
        family, cell = row[2], row[6]
        for skill in [s.strip() for s in str(cell or "").split(";") if s.strip()]:
            missed[skill] += 1
            by_family.setdefault(family, [0, 0, 0])[2] += 1
    fn = sum(missed.values())
    if tp + fp == 0:
        sys.exit("No Y/N marks found in the precision sheet yet.")
    precision = tp / (tp + fp)
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * precision * recall / (precision + recall)
    print(f"labeled extractions: {tp + fp}   correct: {tp}   wrong: {fp}   missed: {fn}")
    print(f"precision {precision:.1%}   recall {recall:.1%}   F1 {f1:.1%}\n")
    for fam, (t, f, n) in sorted(by_family.items()):
        p = t / (t + f) if t + f else float("nan")
        r = t / (t + n) if t + n else float("nan")
        print(f"  {fam:<13} precision {p:.1%}   recall {r:.1%}")
    if wrong:
        print("\nmost frequent false positives:", ", ".join(f"{s} ({c})" for s, c in wrong.most_common(8)))
    if missed:
        print("most frequently missed:      ", ", ".join(f"{s} ({c})" for s, c in missed.most_common(8)))


if __name__ == "__main__":
    main()
