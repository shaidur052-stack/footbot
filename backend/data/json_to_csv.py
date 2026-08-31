"""Export bd_foods.json -> a flat CSV humans can read and edit.

The CSV becomes the source of truth; csv_to_json.py regenerates the
runtime file.
"""
import csv
import json
from pathlib import Path

SRC = Path(__file__).parent / "bd_foods.json"
OUT = Path(__file__).parent / "bd_foods_master.csv"

COLUMNS = [
    "id", "fct_code", "name_en", "name_bn", "name_banglish",
    "category", "calories_100g", "protein_g_100g", "fat_g_100g",
    "carbs_g_100g", "fiber_g_100g", "portion_local", "portion_grams",
    "glycemic_class", "condition_flags", "verified",
    # review columns — filled in by the nutritionist, blank until then
    "review_portion_ok", "review_glycemic_ok", "review_flags_ok", "review_comment",
]


def main():
    doc = json.load(open(SRC, encoding="utf-8"))

    # utf-8-sig so Excel on Windows renders Bangla script correctly
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()

        for food in doc["foods"]:
            p = food["per_100g"]
            w.writerow({
                "id": food["id"],
                "fct_code": food["fct_code"],
                "name_en": food["name_en"],
                "name_bn": food["name_bn"],
                # pipe-joined; commas would break CSV parsing
                "name_banglish": "|".join(food.get("name_banglish", [])),
                "category": food["category"],
                "calories_100g": p["calories"],
                "protein_g_100g": p["protein_g"],
                "fat_g_100g": p["fat_g"],
                "carbs_g_100g": p["carbs_g"],
                "fiber_g_100g": p["fiber_g"],
                "portion_local": food["portion_local"],
                "portion_grams": food["portion_grams"],
                "glycemic_class": food.get("glycemic_class") or "",
                "condition_flags": "|".join(food.get("condition_flags", [])),
                "verified": "yes" if food.get("verified") else "no",
                "review_portion_ok": "",
                "review_glycemic_ok": "",
                "review_flags_ok": "",
                "review_comment": "",
            })

    print(f"Wrote {len(doc['foods'])} rows to {OUT.name}")


if __name__ == "__main__":
    main()