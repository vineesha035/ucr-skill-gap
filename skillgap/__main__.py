"""Command line: python -m skillgap run [--high-demand 0.10] [--well-taught 0.5] [--company-cap 0.10]
                         python -m skillgap discover [--family robotics]
"""

from __future__ import annotations

import argparse

from . import gap
from .pipeline import OUTPUTS, run


def main() -> None:
    ap = argparse.ArgumentParser(prog="skillgap")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="clean, extract, score, and write outputs/report.md")
    r.add_argument("--high-demand", type=float, default=0.10, help="demand threshold for a critical gap")
    r.add_argument("--well-taught", type=float, default=0.50, help="exposure threshold for well covered")
    r.add_argument("--company-cap", type=float, default=0.10, help="max share of a role family per employer")
    d = sub.add_parser("discover", help="list frequent terms the taxonomy does not cover")
    d.add_argument("--family", choices=["data_science", "software", "robotics"])
    d.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    if args.cmd == "run":
        meta = run(OUTPUTS, gap.GapConfig(args.high_demand, args.well_taught), args.company_cap)
        print(f"Analyzed {meta['n_analyzed']:,} postings as of {meta['as_of']}. Report: {OUTPUTS / 'report.md'}")
    else:
        from .clean import clean_postings
        from .extract import discover_terms
        from .io import load_postings
        df = clean_postings(load_postings())
        df = df[df.excluded == ""]
        if args.family:
            df = df[df.role_family == args.family]
        for term, w in discover_terms(df.description.tolist(), top=args.top):
            print(f"{w:.5f}  {term}")


if __name__ == "__main__":
    main()
