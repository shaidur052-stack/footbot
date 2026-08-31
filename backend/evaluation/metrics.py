"""Scoring for the evaluation harness.

Every metric is computed against bd_foods.json, so scoring is objective —
no human judgement, no room to flatter our own system.
"""

import re

# Phrases that signal a refusal, in all three languages the system handles.
_REFUSAL_MARKERS = [
    "not in my", "not in the database", "won't guess", "will not guess",
    "do not have", "don't have", "cannot find", "no data",
    "could not retrieve", "not retrieve",
    "database-e nei", "database e nei", "guess korbo na", "nei",
    "নেই", "অনুমান করব না", "ডেটাবেসে নেই",
    "খুঁজে পাওয়া যায়নি", "খুঁজে পাইনি",
]

def is_refusal(answer: str) -> bool:
    """Did the system decline rather than produce a number?"""
    low = answer.lower()
    return any(m in low for m in _REFUSAL_MARKERS)


def extract_numbers(answer: str) -> list[float]:
    """Every number in the answer, for hallucination checking.

    Bengali numerals are transliterated first, since the model replies in
    Bangla script when asked in Bangla.
    """
    bn_digits = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    text = answer.translate(bn_digits)
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]


def value_correct(answer: str, expected: float, tolerance: float = 0.10) -> bool:
    """Does the answer contain the expected value, within tolerance?

    Tolerance covers legitimate rounding and portion scaling — 272 vs 273
    for a plate of rice should not count as an error.
    """
    for n in extract_numbers(answer):
        if expected == 0:
            if n == 0:
                return True
        elif abs(n - expected) / expected <= tolerance:
            return True
    return False


def is_hallucination(answer: str, allowed_values: list[float],
                     tolerance: float = 0.10) -> bool:
    """Does the answer state a nutrition figure not present in the retrieved data?

    Small integers are ignored — they are usually portion counts ("1 piece",
    "2 tbsp") rather than nutritional claims. Checking every number would
    flag legitimate phrasing as invention.
    """
    for n in extract_numbers(answer):
        if n < 10:
            continue
        ok = any(
            abs(n - a) / a <= tolerance if a else n == 0
            for a in allowed_values
        )
        if not ok:
            return True
    return False


def has_citation(sources: list) -> bool:
    return bool(sources)