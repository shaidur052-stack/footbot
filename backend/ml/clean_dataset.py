"""Clean the generated training set before fine-tuning.

Two problems found by inspection:
  1. Wrong-script contamination — Gemini occasionally emitted Devanagari
     (Hindi) or Arabic/Urdu instead of Bangla. Those characters never appear
     in real user input for this product, so they teach noise.
  2. Language imbalance — the prompt asked for a third each of Bangla,
     English, and Banglish; actual output is ~18% Bangla script.

Only (1) is fixed here. (2) is reported and belongs in the limitations
section, since fixing it needs targeted regeneration.
"""

import csv
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "labeled_queries.csv"
OUT = HERE / "labeled_queries_clean.csv"

# U+0964 (danda ।) and U+0965 live in the Devanagari block but are standard
# punctuation in Bengali writing, so they must NOT count as contamination.
DEVANAGARI = re.compile(r"[\u0900-\u0963\u0966-\u097F]")   # Hindi, minus danda
OTHER_SCRIPTS = re.compile(r"[\u0600-\u06FF\u4E00-\u9FFF\u0E00-\u0E7F]")  # Arabic, CJK, Thai
BENGALI = re.compile(r"[\u0980-\u09FF]")


def language_of(query: str) -> str:
    """Bangla script, or Latin (English/Banglish — not separable by script)."""
    return "bn" if BENGALI.search(query) else "latin"


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    print(f"input: {len(rows)} rows")

    kept, dropped = [], []
    for r in rows:
        q = r["query"]
        if DEVANAGARI.search(q) or OTHER_SCRIPTS.search(q):
            dropped.append(r)
        else:
            kept.append(r)

    print(f"dropped {len(dropped)} rows with non-Bangla, non-Latin script:")
    for r in dropped:
        print(f"   {r['label']:18} {r['query'][:55]}")

    # de-duplicate defensively; generation already avoids repeats
    seen, unique = set(), []
    for r in kept:
        if r["query"] not in seen:
            seen.add(r["query"])
            unique.append(r)

    print(f"\nkept: {len(unique)} rows")
    print("per label:", dict(Counter(r["label"] for r in unique)))

    langs = Counter(language_of(r["query"]) for r in unique)
    total = len(unique)
    print(f"\nscript balance:")
    for k, v in langs.items():
        print(f"   {k:8} {v:5}  ({100 * v / total:.0f}%)")
    print("   NOTE: Bangla script is under-represented against the 1/3 target.")
    print("   Expect weaker classifier performance on Bangla-script input —")
    print("   report it rather than hiding it.")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["query", "label"])
        w.writeheader()
        w.writerows([{"query": r["query"], "label": r["label"]} for r in unique])

    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()