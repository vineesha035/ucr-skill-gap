"""Skill extraction: boundary-aware, longest-match-first matching against the taxonomy,
plus TF-IDF n-gram discovery of frequent terms the taxonomy does not cover yet.

Why not plain substring search: on the Nov 13 snapshot, naive matching reported "rust" in 53%
of postings (it matched "trust"), "scala" in 42% ("scalable"), "excel" in 37% ("excellent").
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .taxonomy import SKILLS, Skill

_WORD = r"A-Za-z0-9"


def _phrase_to_regex(phrase: str) -> str:
    """Escape a phrase, make space/hyphen/slash interchangeable, add word boundaries.

    Boundaries are custom lookarounds instead of \\b so that terms ending in symbols
    ("c++", "c#", ".net", "ci/cd") still match correctly.
    """
    parts = re.split(r"[\s\-/]+", phrase.strip())
    body = r"[\s\-/]*".join(re.escape(p) for p in parts if p)
    left = rf"(?<![{_WORD}])" if re.match(rf"[{_WORD}]", phrase) else rf"(?<![{_WORD}.])"
    right = rf"(?![{_WORD}+#])"
    return left + body + right


@dataclass(frozen=True)
class Match:
    skill: str
    start: int
    end: int
    text: str


_TOKEN = re.compile(r"[A-Za-z0-9.#+&]+")


def _first_token(phrase: str) -> str:
    return re.split(r"[\s\-/]+", phrase.strip())[0]


class SkillMatcher:
    """Compile every alias once, then find non-overlapping skill mentions in text.

    Plain aliases are indexed by their first word, so each word in a posting is only
    checked against the aliases that could start there (fast on long descriptions).
    Regex aliases (re: / re=) are few and are run as two small combined regexes.
    """

    def __init__(self, skills: list[Skill] = SKILLS):
        self.skills = {s.name: s for s in skills}
        self._ci: dict[str, list[tuple[re.Pattern, str, int]]] = {}    # lowercased first word
        self._cs: dict[str, list[tuple[re.Pattern, str, int]]] = {}    # exact-case first word
        regex_items: dict[bool, list[tuple[str, str]]] = {True: [], False: []}
        for s in skills:
            for alias in s.aliases:
                if alias.startswith(("re=", "re:")):
                    regex_items[alias[2] == "="].append((alias[3:], s.name))
                    continue
                cs = alias.startswith("=")
                phrase = alias[1:] if cs else alias
                pat = re.compile(_phrase_to_regex(phrase), 0 if cs else re.IGNORECASE)
                key = _first_token(phrase)
                index = self._cs if cs else self._ci
                index.setdefault(key if cs else key.lower(), []).append((pat, s.name, len(phrase)))
        for index in (self._ci, self._cs):
            for lst in index.values():
                lst.sort(key=lambda t: -t[2])                               # longest first
        self._regex = []
        for cs, items in regex_items.items():
            if items:
                alt = "|".join(f"(?P<g{i}>{p})" for i, (p, _) in enumerate(items))
                self._regex.append((re.compile(alt, 0 if cs else re.IGNORECASE), [n for _, n in items]))

    def _candidates(self, text: str):
        for tok in _TOKEN.finditer(text):
            word = tok.group()
            keys = {word, word.rstrip(".,")}
            for key in keys:
                for index, k in ((self._cs, key), (self._ci, key.lower())):
                    for pat, name, _ in index.get(k, ()):
                        m = pat.match(text, tok.start())
                        if m:
                            yield Match(name, m.start(), m.end(), m.group())
                            break                                            # longest alias for this index
        for regex, names in self._regex:
            for m in regex.finditer(text):
                if m.end() > m.start():
                    yield Match(names[int(m.lastgroup[1:])], m.start(), m.end(), m.group())

    def find(self, text: str) -> list[Match]:
        candidates = sorted(set(self._candidates(text)), key=lambda m: (m.start, -(m.end - m.start)))
        chosen, last_end = [], -1
        for m in candidates:                       # earliest start, then longest span wins
            if m.start >= last_end:
                chosen.append(m)
                last_end = m.end
        return chosen

    def skills_in(self, text: str) -> set[str]:
        return {m.skill for m in self.find(text)}


_STOP = set("""a an and are as at be by can for from has have in into is it its of on or our that the their this
to we will with you your who what when where which while within without across all also any about more most
other such than these those through using use used work working team teams experience years strong ability
including include new build building help join role company product products customer customers world
""".split())


def discover_terms(texts: list[str], matcher: SkillMatcher | None = None, top: int = 60,
                   min_df: float = 0.02, max_df: float = 0.6) -> list[tuple[str, float]]:
    """Frequent 1-3 word phrases NOT covered by the taxonomy, ranked by TF-IDF weight.

    Output is a review queue: a person decides which entries are real skills worth adding.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    matcher = matcher or SkillMatcher()
    vec = TfidfVectorizer(ngram_range=(1, 3), min_df=min_df, max_df=max_df, lowercase=True,
                          token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9+#.\-]{1,}\b", stop_words=sorted(_STOP))
    X = vec.fit_transform(texts)
    weights = X.mean(axis=0).A1
    terms = vec.get_feature_names_out()
    ranked = sorted(zip(terms, weights), key=lambda t: -t[1])
    out = []
    for term, w in ranked:
        if matcher.find(term):                      # already covered by an alias
            continue
        out.append((term, round(float(w), 5)))
        if len(out) >= top:
            break
    return out


def skill_frequencies(texts: list[str], matcher: SkillMatcher | None = None) -> Counter:
    matcher = matcher or SkillMatcher()
    c: Counter = Counter()
    for t in texts:
        c.update(matcher.skills_in(t))
    return c
