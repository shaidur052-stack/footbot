"""Expand Banglish aliases in bd_foods_master.csv.

Romanised Bangla has no standard orthography. The same food is written a
dozen ways — ilish / ilsha / elish / hilsa — and BM25 needs an exact token
match, so a spelling we did not anticipate simply fails to retrieve. That
failure is invisible in testing (we type the spellings we entered) and
obvious to a real user (who does not).

Two sources of new aliases:
  1. Hand-written variants for high-traffic foods, where getting it wrong is
     most visible.
  2. Mechanical variants generated from existing aliases using the
     substitution patterns Bangla speakers actually use when romanising.
"""
import csv
import re
from pathlib import Path

CSV = Path("bd_foods_master.csv")

# Foods people ask about constantly. Worth writing by hand rather than
# trusting the generator.
MANUAL = {
    "ilish": "ilish|ilsha|elish|elisha|hilsa|hilsha|hilsah|ilish mach|ilsha mach|padma ilish",
    "rui": "rui|ruhi|rohu|rui mach|ruee|ruhee|rohu fish",
    "katla": "katla|catla|katol|katla mach|kaatla",
    "pangas": "pangas|pangash|pangus|pangasius|pangas mach",
    "telapia": "telapia|tilapia|tilapiya|telapia mach",
    "bhat_boiled": "bhat|vaat|bhaat|vat|sada bhat|shada bhat|rice|bath",
    "ruti": "ruti|roti|rooti|atta ruti|ata ruti|chapati",
    "mosur_dal_boiled": "dal|daal|dahl|mosur dal|musur dal|mosoor dal|lentil|masur dal",
    "muri": "muri|mudi|mury|puffed rice|moori",
    "chira": "chira|cheera|chirra|chida|flattened rice|flaked rice",
    "dim_placeholder": "",   # eggs not transcribed; kept as a reminder
    "alu_boiled": "alu|aloo|allu|potato|gol alu|golalu",
    "kola_sagar": "kola|kula|banana|sagar kola|shagor kola|kolaa",
    "aam_langra": "aam|am|amm|mango|langra aam|langra am|paka aam",
    "kathal": "kathal|kanthal|katal|jackfruit|kathaal",
    "peyara": "peyara|peara|piyara|guava|peyaraa",
    "chingri_golda": "chingri|chingdi|chingry|golda chingri|prawn|golda|icha",
    "shing": "shing|singh|shingi|shing mach|stinging catfish",
    "magur": "magur|magoor|maagur|magur mach|walking catfish",
    "koi_deshi": "koi|koy|kai|deshi koi|climbing perch",
    "tengra": "tengra|tangra|tengra mach|tengda",
    "pabda": "pabda|pabda mach|papda",
    "chola_boiled": "chola|chhola|cholla|cholabut|chickpea|chana",
    "mung_dal_boiled": "mung dal|moong dal|mug dal|mungdal|moog dal",
    "palong_shak_boiled": "palong shak|palong|palon shak|spinach|palongshak",
    "lal_shak_boiled": "lal shak|lal shaak|lalshak|red amaranth",
    "korola_boiled": "korola|korolla|karela|korela|bitter gourd|corolla",
    "begun_boiled": "begun|begoon|baigun|brinjal|eggplant|beguun",
    "pepe_paka": "pepe|pepay|papaya|paka pepe|pape",
    "tarmuz": "tarmuz|tormuj|tarmuj|watermelon|tormuz",
    "anaros": "anaros|annaros|ananas|pineapple|anarosh",
    "misti_alu_boiled": "misti alu|mishti alu|mistialu|sweet potato|mitha alu",
    "khichuri": "khichuri|khichudi|khichdi|kichuri|khichuree",
    "pulao": "pulao|polao|polau|pilaf|pulaw",
}

# How Bangla speakers vary romanisation. Each pair is bidirectional.
SWAPS = [
    ("bh", "v"), ("kh", "k"), ("gh", "g"), ("ch", "c"), ("sh", "s"),
    ("ee", "i"), ("oo", "u"), ("aa", "a"), ("y", "i"), ("z", "j"),
]


def variants(alias: str) -> set[str]:
    """Generate plausible respellings of one alias.

    Only single substitutions: two at once produces strings nobody types,
    and every false alias is a chance to retrieve the wrong food.
    """
    out = set()
    low = alias.lower().strip()
    if not low or len(low) < 3:
        return out

    for a, b in SWAPS:
        if a in low:
            out.add(low.replace(a, b, 1))
        if b in low:
            out.add(low.replace(b, a, 1))

    return {v for v in out if v != low and len(v) >= 3}


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    cols = list(rows[0].keys())

    manual_applied = 0
    generated = 0

    for r in rows:
        current = {a.strip().lower() for a in r["name_banglish"].split("|") if a.strip()}

        if r["id"] in MANUAL and MANUAL[r["id"]]:
            before = len(current)
            current |= {a.strip().lower()
                        for a in MANUAL[r["id"]].split("|") if a.strip()}
            if len(current) > before:
                manual_applied += 1

        # Mechanical variants from whatever aliases exist
        for alias in list(current):
            new = variants(alias)
            generated += len(new - current)
            current |= new

        # Longest first: a more specific alias should win a tie in BM25
        r["name_banglish"] = "|".join(sorted(current, key=lambda s: (-len(s), s)))

    with open(CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    total = sum(len(r["name_banglish"].split("|")) for r in rows)
    print(f"{len(rows)} foods")
    print(f"  hand-written aliases applied to {manual_applied} rows")
    print(f"  {generated} mechanical variants generated")
    print(f"  {total} aliases total, {total / len(rows):.1f} per food")
    print("\nNow run:  python data/csv_to_json.py")


if __name__ == "__main__":
    main()
