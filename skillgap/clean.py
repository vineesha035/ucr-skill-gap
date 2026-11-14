"""Text normalization and posting filters.

Filters come from the data profile of the Nov 13 snapshot:
  * non-engineering titles that matched "AI" or "robotics" keywords (writers, PMs, finance...)
  * student, contract-student, co-op, apprentice and fellowship roles (new-grad roles are KEPT)
  * roles explicitly scoped to EMEA / APAC
  * per-company cap so no single employer dominates a role family
"""

from __future__ import annotations

import hashlib
import html
import math
import re
import unicodedata

import pandas as pd

_TAGS = re.compile(r"<[^>]+>")
_BULLETS = re.compile(r"[•●▪‣⁃◦∙]")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize(text: str) -> str:
    """Plain, single-spaced text: HTML unescaped and stripped, Unicode NFKC, ASCII quotes and dashes."""
    if not text:
        return ""
    text = html.unescape(html.unescape(text))
    text = _TAGS.sub(" ", text)
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    text = _BULLETS.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


# Always excluded: the role itself is not an engineering/science job.
NON_ENGINEERING_ROLE = re.compile(
    r"technical writer|product manager|program manager|project manager|solutions? architect|"
    r"account (executive|manager)|recruit|counsel|evangelist|advocate|chief of staff|"
    r"\bdirector\b|\bvp\b|vice president|head of|partner (development|manager)", re.I)
# Domain words: excluded only when the title has no engineering/science role word
# ("Data Scientist, Finance" is kept, "Finance & Strategy Lead" is not).
NON_ENGINEERING_DOMAIN = re.compile(
    r"sales|customer|enablement|finance|financial|accounting|brand|marketing|legal|policy|"
    r"communications|business development|community|partnerships?", re.I)
ENGINEERING_ROLE = re.compile(r"engineer|scientist|developer|programmer|analyst|researcher|"
                              r"\bml\b|\bsre\b|devops", re.I)
STUDENT = re.compile(r"\bstudent\b|\bintern(ship)?\b|co-?op\b|apprentice|fellow(ship)?\b|"
                     r"contract (student )?worker", re.I)
NON_US_TITLE = re.compile(r"\b(EMEA|APAC|APJ|LATAM|EU|UK)\b")

LEVELS = [  # first match wins
    ("staff+", re.compile(r"\b(staff|principal|distinguished|fellow|architect)\b", re.I)),
    ("manager", re.compile(r"\bmanager\b", re.I)),
    ("senior", re.compile(r"\b(senior|sr\.?|lead|iii|iv)\b", re.I)),
    ("entry", re.compile(r"new grad|graduate|early career|entry|junior|\bjr\.?\b|associate|\bi\b(?!\w)|level 1", re.I)),
]


def seniority(title: str) -> str:
    for level, pat in LEVELS:
        if pat.search(title):
            return level
    return "mid"


def exclusion_reason(title: str) -> str | None:
    if STUDENT.search(title):
        return "student_or_contract"
    if NON_ENGINEERING_ROLE.search(title):
        return "non_engineering"
    if NON_ENGINEERING_DOMAIN.search(title) and not ENGINEERING_ROLE.search(title):
        return "non_engineering"
    if NON_US_TITLE.search(title):
        return "non_us"
    return None


def _stable_rank(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()


def cap_per_company(df: pd.DataFrame, max_share: float = 0.10, group: str = "role_family") -> pd.Series:
    """Boolean mask keeping at most ceil(max_share * group size) postings per company per group.

    Which postings are kept is decided by a hash of the posting id, so the sample is random
    but identical on every run.
    """
    keep = pd.Series(True, index=df.index)
    for _, g in df.groupby(group):
        limit = max(1, math.ceil(max_share * len(g)))
        for _, cg in g.groupby("company"):
            if len(cg) > limit:
                order = cg["history_id"].map(_stable_rank).sort_values()
                keep[order.index[limit:]] = False
    return keep


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])|\s+-\s+")


def split_sentences(text: str) -> list[str]:
    return [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]


def strip_company_boilerplate(df: pd.DataFrame, min_share: float = 0.3, min_count: int = 3) -> pd.Series:
    """Remove sentences that repeat across many postings of the same company.

    Company intros ("Waymo is an autonomous driving technology company...") and policy blocks
    ("Data Privacy: to view our candidate privacy policy...") are not job requirements but
    contain skill words. A sentence appearing in >= min_share of a company's postings
    (and in at least min_count of them) is treated as boilerplate.
    """
    out = df["description"].copy()
    for _, g in df.groupby("company"):
        sents = g["description"].map(split_sentences)
        counts: dict[str, int] = {}
        for ss in sents:
            for sent in set(ss):
                counts[sent] = counts.get(sent, 0) + 1
        limit = max(min_count, min_share * len(g))
        boiler = {sent for sent, c in counts.items() if c >= limit and len(sent) > 25}
        if boiler:
            out[g.index] = sents.map(lambda ss: " ".join(x for x in ss if x not in boiler))
    return out


def clean_postings(df: pd.DataFrame, max_share: float = 0.10) -> pd.DataFrame:
    """Return all postings with cleaned text and three new columns:

    excluded   reason string, or "" if the posting is analyzed
    level      entry / mid / senior / staff+ / manager
    capped     True if dropped only by the per-company cap
    Analyzed postings are those with excluded == "".
    """
    out = df.copy()
    out["title"] = out["title"].map(normalize)
    out["description"] = out["description"].map(normalize)
    out["description_full"] = out["description"]
    out["description"] = strip_company_boilerplate(out)
    out["level"] = out["title"].map(seniority)
    out["excluded"] = out["title"].map(exclusion_reason).fillna("")
    out.loc[(out["excluded"] == "") & (out["description"].str.len() < 300), "excluded"] = "too_short"
    kept = out["excluded"] == ""
    out["capped"] = False
    mask = cap_per_company(out[kept], max_share)
    out.loc[mask[~mask].index, ["excluded", "capped"]] = ["company_cap", True]
    return out


def summary(df: pd.DataFrame) -> pd.DataFrame:
    """Counts by role family: total, each exclusion reason, analyzed."""
    t = pd.crosstab(df["role_family"], df["excluded"].replace("", "analyzed"), margins=True, margins_name="total")
    return t
