"""Add foods to bd_foods_master.csv by typing values from the FCT.

Run:  python data/add_food.py

Reads the five proximate columns straight off the PDF page, validates
them, and appends a row. Catches transcription slips before they reach
the database.
"""

import csv
import sys
from pathlib import Path

CSV_PATH = Path(__file__).parent / "bd_foods_master.csv"

COLUMNS = [
    "id", "fct_code", "name_en", "name_bn", "name_banglish",
    "category", "calories_100g", "protein_g_100g", "fat_g_100g",
    "carbs_g_100g", "fiber_g_100g", "portion_local", "portion_grams",
    "glycemic_class", "condition_flags", "verified",
    "review_portion_ok", "review_glycemic_ok", "review_flags_ok", "review_comment",
]

# Group code -> (category label, default portion, default grams)
GROUPS = {
    "01": ("cereal", "1 plate", 250),
    "02": ("pulse", "1 bowl", 150),
    "03": ("vegetable", "1 bowl", 100),
    "04": ("leafy vegetable", "1 bowl", 100),
    "05": ("starchy root", "1 medium", 120),
    "06": ("nut/seed", "1 handful", 30),
    "07": ("spice", "1 tsp", 5),
    "08": ("fruit", "1 medium", 100),
    "09": ("fish", "1 piece", 75),
    "10": ("meat", "1 bowl", 100),
    "11": ("egg", "1 piece", 50),
    "12": ("milk", "1 glass", 250),
    "13": ("fat/oil", "1 tbsp", 15),
    "14": ("beverage", "1 glass", 250),
    "15": ("miscellaneous", "1 serving", 100),
}


def ask(prompt, default=None, required=True):
    hint = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{prompt}{hint}: ").strip()
        if not value and default is not None:
            return str(default)
        if value or not required:
            return value
        print("  required")


def ask_num(prompt, allow_blank=True):
    """FCT prints uncertain values in brackets — strip them and warn."""
    while True:
        raw = input(f"{prompt}: ").strip()
        if not raw and allow_blank:
            return ""
        bracketed = raw.startswith("[") and raw.endswith("]")
        if bracketed:
            raw = raw[1:-1]
            print("  note: bracketed value — lower quality per FCT")
        # energy is printed as (109) in the table
        raw = raw.strip("()")
        try:
            return str(float(raw))
        except ValueError:
            print("  not a number — try again")


def existing_ids():
    if not CSV_PATH.exists():
        return set(), set()
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return ({r["id"] for r in rows}, {r["fct_code"] for r in rows})


def check_energy(kcal, prot, fat, carb, fib):
    """Recompute energy from macros using the FCT's own factors.

    Protein 4, fat 9, available carbohydrate 4, fibre 2 kcal/g.
    A big gap almost always means a digit was mistyped.
    """
    try:
        est = 4 * float(prot or 0) + 9 * float(fat or 0) + \
              4 * float(carb or 0) + 2 * float(fib or 0)
        stated = float(kcal)
    except ValueError:
        return
    if stated <= 0:
        return
    gap = abs(est - stated) / stated
    if gap > 0.15:
        print(f"\n  ⚠ energy check: table says {stated:.0f} kcal, "
              f"macros give {est:.0f} kcal ({gap*100:.0f}% off)")
        print("    re-read the row — a digit is probably wrong")
    else:
        print(f"  ✓ energy check passes ({est:.0f} vs {stated:.0f})")


def main():
    ids, codes = existing_ids()
    print(f"\n{len(ids)} foods currently in the file.\n")
    print("Enter values exactly as printed in the FCT. Blank = missing.")
    print("Ctrl+C to stop.\n")

    added = 0
    while True:
        print("-" * 58)
        code = ask("FCT code (e.g. 09_0060)")
        if code in codes:
            print("  already in the file — skipping")
            continue

        group = code.split("_")[0]
        cat_default, portion_default, grams_default = GROUPS.get(
            group, ("unknown", "1 serving", 100))

        name_en = ask("English name (as in the table)")
        name_bn = ask("Bangla name (script, or blank)", required=False)
        banglish = ask("Banglish spellings, pipe-separated (rui|rohu|rui mach)")

        food_id = ask("short id", banglish.split("|")[0].replace(" ", "_").lower())
        if food_id in ids:
            print("  id already used — pick another")
            continue

        print(f"\n  proximates per 100 g — group {group} ({cat_default})")
        kcal = ask_num("  Energy (kcal)")
        prot = ask_num("  Protein (g)")
        fat = ask_num("  Fat (g)")
        carb = ask_num("  Carbohydrate available (g)")
        fib = ask_num("  Total dietary fibre (g)")

        check_energy(kcal, prot, fat, carb, fib)

        print()
        category = ask("category", cat_default)
        portion_local = ask("portion name", portion_default)
        portion_grams = ask("portion grams (your assumption)", grams_default)
        glycemic = ask("glycemic class (high/medium/low, blank if n/a)", "", required=False)
        flags = ask("condition flags, pipe-separated "
                    "(diabetes_caution|kidney_caution|hypertension_caution)",
                    "", required=False)

        row = {c: "" for c in COLUMNS}
        row.update({
            "id": food_id, "fct_code": code,
            "name_en": name_en, "name_bn": name_bn, "name_banglish": banglish,
            "category": category,
            "calories_100g": kcal, "protein_g_100g": prot, "fat_g_100g": fat,
            "carbs_g_100g": carb, "fiber_g_100g": fib,
            "portion_local": portion_local, "portion_grams": portion_grams,
            "glycemic_class": glycemic, "condition_flags": flags,
            "verified": "yes",
        })

        new_file = not CSV_PATH.exists()
        with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            if new_file:
                w.writeheader()
            w.writerow(row)

        ids.add(food_id)
        codes.add(code)
        added += 1
        print(f"\n  added: {name_en}  (total {len(ids)})\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nStopped. Run  python data/csv_to_json.py  to rebuild the database.")
        sys.exit(0)