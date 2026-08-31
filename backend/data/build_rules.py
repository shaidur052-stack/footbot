"""Build condition_rules.json — dietary guidance, sourced like the food table.

WHY THIS EXISTS
---------------
The food table answers "how much energy is in bhat". It cannot answer "ami
diabetic, raate vat khaite pari" — the question users actually ask. That needs
guidance, not just figures.

A clinical Q&A corpus was evaluated for this and rejected. Its rows turned out
to be symptom consultations ("my son had an appendectomy", "my left knee has
been hurting"), the answers were diagnostic rather than dietary, each was
addressed to one specific patient, and none of it was Bangladeshi. Retrieving
"you may be having early osteoarthritis" as context for a food question is
worse than having nothing, and the provenance — an anonymous forum reply —
could not be cited or checked.

So: a small, sourced table instead. Every rule names a published guideline the
same way every food names an FCT code. Small enough to read end to end, small
enough for a nutritionist to sign off on, and specific to how people here eat.

WHAT A RULE IS AND IS NOT
-------------------------
A rule supplies FRAMING: what matters for a condition, what to pair with what,
what to watch. It never supplies a NUMBER — those still come only from the food
table. The generation constraint that keeps figures grounded is unchanged;
this adds context, not values.
"""

import json
from collections import Counter
from pathlib import Path

OUT = Path(__file__).parent / "condition_rules.json"

# ---------------------------------------------------------------------------
# sources — every rule points at one of these
# ---------------------------------------------------------------------------

SOURCES = {
    "dgb": {
        "name": "Dietary Guidelines for Bangladesh",
        "publisher": "BIRDEM Nutrition Research Team, Diabetic Association of Bangladesh",
        "status": "Approved as a National Guideline for Bangladesh through "
                  "inter-ministerial committee; launched 30 June 2016",
        "edition": "2nd edition",
        "support": "Ministry of Food, Ministry of Health and Family Welfare, "
                   "FAO, USAID, EU (NFPCSP)",
        "url": "https://openknowledge.fao.org/server/api/core/bitstreams/"
               "9fdfbe0e-c3f6-45e0-a45d-39a53b4fd5b5/content",
        "authority": "national",
    },
    "dgi": {
        "name": "Dietary Guidelines for Indians",
        "publisher": "ICMR-National Institute of Nutrition, Hyderabad",
        "edition": "2024",
        "url": "https://nin.res.in/dietaryguidelines/pdfjs/locale/DGI_2024.pdf",
        "authority": "regional",
        "note": "Used only where the guidance is regionally applicable and the "
                "Bangladesh guideline is not more specific. Marked distinctly "
                "so a user can see when advice is not from their own country.",
    },
    "who": {
        "name": "World Health Organization dietary recommendations",
        "publisher": "World Health Organization",
        "authority": "international",
        "note": "Used for sodium and BMI cut-offs, where WHO publishes "
                "South Asia-specific thresholds.",
    },
}

RULES = []


def rule(rid, condition, topic, guidance, source, foods=None, flags=None,
         keywords=None, note=""):
    RULES.append({
        "id": rid,
        "condition": condition,          # "diabetes" | ... | "general"
        "topic": topic,
        "guidance": guidance,
        "source": source,
        "applies_to_foods": foods or [],     # food ids, when specific
        "applies_to_flags": flags or [],     # condition_flags on food rows
        "keywords": keywords or [],          # retrieval terms, incl. Banglish
        "note": note,
        "verified": True,
    })


# ─────────────────────────────────────────────────── diabetes
rule("dia_rice_portion", "diabetes", "staples",
     "Rice is the staple of nearly every meal here, and cutting it out entirely "
     "is neither realistic nor necessary. What matters is the portion and what "
     "goes with it. A smaller serving of rice alongside dal, fish and a "
     "vegetable slows the rise in blood glucose compared with a large plate of "
     "rice eaten alone.",
     "dgb",
     foods=["bhat_boiled", "bhat_atop_boiled", "bhat_sugondhi_boiled", "pulao"],
     flags=["diabetes_caution"],
     keywords=["diabetes", "diabetic", "sugar", "rice", "bhat", "vat", "bhaat",
               "ভাত", "ডায়াবেটিস", "diabetis", "blood sugar"])

rule("dia_diet_pattern", "diabetes", "overall pattern",
     "The typical Bangladeshi diet is high in carbohydrate and fat and low in "
     "protein and fibre, which works against glycaemic control. Shifting the "
     "balance — more dal, more vegetables, more fish, less refined "
     "carbohydrate — matters more than removing any single food.",
     "dgb",
     keywords=["diabetes", "diabetic", "diet", "khabar", "খাবার", "control"])

rule("dia_familiar_foods", "diabetes", "practical",
     "Traditional dishes fit a diabetes-appropriate plan when the proportions "
     "are right. Dal, sabzi and fish curry are all suitable; the change is in "
     "how much rice sits beside them, not in abandoning familiar food.",
     "dgb",
     foods=["mosur_dal_boiled", "mung_dal_boiled", "rui", "telapia", "katla"],
     keywords=["diabetes", "diabetic", "dal", "fish", "mach", "sabzi", "curry"])

rule("dia_fibre", "diabetes", "fibre",
     "Fibre slows glucose absorption. Whole pulses, leafy greens and vegetables "
     "eaten with the main meal help more than the same foods eaten separately.",
     "dgi",
     foods=["chola_boiled", "palong_shak_boiled", "lal_shak_boiled",
            "begun_boiled", "korola_boiled"],
     keywords=["diabetes", "fibre", "fiber", "shak", "শাক", "vegetable", "dal"])

rule("dia_sugar", "diabetes", "sugar",
     "Added sugar should stay below ten per cent of daily energy. Honey and "
     "molasses are still sugar, though slightly preferable to refined sugar.",
     "dgb",
     keywords=["diabetes", "sugar", "chini", "চিনি", "misti", "মিষ্টি",
               "sweet", "honey", "mou", "gur"])

rule("dia_meal_timing", "diabetes", "timing",
     "Eating at regular times and avoiding very large single meals helps keep "
     "glucose steadier than the same total food eaten irregularly.",
     "dgb",
     keywords=["diabetes", "timing", "meal", "kokhon", "কখন", "when eat"])

# ─────────────────────────────────────────────────── hypertension
rule("htn_salt", "hypertension", "sodium",
     "Salt is the main dietary lever in high blood pressure. WHO recommends "
     "less than 5 g of salt a day for adults — roughly one level teaspoon, "
     "including what is already in cooking, pickles, dried fish and packaged "
     "snacks.",
     "who",
     keywords=["blood pressure", "hypertension", "salt", "lobon", "লবণ",
               "pressure", "bp", "উচ্চ রক্তচাপ"])

rule("htn_dried_fish", "hypertension", "sodium",
     "Dried and salted fish (shutki) carries a substantial salt load. It is "
     "worth counting alongside cooking salt rather than treated as separate.",
     "dgb",
     foods=["fesha_shutki", "vetkee_shutki", "rupchanda_shutki", "chela_shukna"],
     flags=["hypertension_caution"],
     keywords=["blood pressure", "hypertension", "shutki", "শুঁটকি", "salt",
               "dried fish", "salted"])

rule("htn_vegetables", "hypertension", "potassium",
     "Vegetables and fruit supply potassium, which works against sodium. "
     "Half the plate as vegetables and fruit is the general target.",
     "dgi",
     foods=["palong_shak_boiled", "lau", "kola_sagar", "peyara"],
     keywords=["blood pressure", "hypertension", "vegetable", "shak", "fruit",
               "potassium", "shobji", "সবজি"])

rule("htn_fried", "hypertension", "fat",
     "Deep-fried food and reused frying oil both work against cardiovascular "
     "health. Boiling, steaming and light stir-frying are the preferred "
     "methods.",
     "dgb",
     foods=["korola_fried", "kachki_vaja"],
     keywords=["blood pressure", "hypertension", "fried", "vaja", "ভাজা",
               "oil", "tel", "তেল", "heart"])

# ─────────────────────────────────────────────────── kidney
rule("kid_potassium_greens", "kidney", "potassium",
     "Some leafy greens are high in potassium and oxalate, which can be a "
     "problem in kidney disease. Spinach and taro leaves in particular are "
     "worth raising with a doctor before eating regularly.",
     "dgb",
     foods=["palong_shak_boiled", "palong_shak_raw", "kochu_shak",
            "kalo_kochu_shak"],
     flags=["kidney_caution"],
     keywords=["kidney", "kidni", "কিডনি", "shak", "শাক", "potassium",
               "spinach", "palong", "kochu"])

rule("kid_taro", "kidney", "potassium",
     "Taro and its relatives — kochur mukhi, ole kochu, mann kochu — are "
     "starchy roots that carry a caution in kidney disease for the same reason "
     "as the leaves.",
     "dgb",
     foods=["kochur_mukhi_boiled", "ole_kochu_boiled", "mann_kochu_boiled",
            "dudh_kochu_boiled"],
     flags=["kidney_caution"],
     keywords=["kidney", "kochu", "কচু", "taro", "mukhi", "ole"])

rule("kid_individual", "kidney", "general",
     "Dietary limits in kidney disease depend on the stage and on blood test "
     "results, so general advice is a poor substitute for a plan from the "
     "treating doctor or a renal dietitian.",
     "dgb",
     keywords=["kidney", "kidni", "কিডনি", "diet", "restriction"])

# ─────────────────────────────────────────────────── weight
rule("wt_bmi_range", "weight", "targets",
     "A body mass index between 18.5 and 23.0 is the healthy range used in "
     "Bangladesh, and a waist-hip ratio below 0.9 for men and 0.8 for women. "
     "These are lower than the European thresholds because metabolic risk "
     "appears at a lower body mass in South Asian populations.",
     "dgb",
     keywords=["weight", "ojon", "ওজন", "bmi", "obesity", "mota", "মোটা",
               "lose weight", "kombe"])

rule("wt_vegetables_half", "weight", "composition",
     "Filling half the plate with vegetables, fruit and greens lowers the "
     "energy density of a meal without lowering its volume, which makes a "
     "smaller portion of rice easier to sustain.",
     "dgi",
     keywords=["weight", "ojon", "ওজন", "lose", "kombe", "diet", "vegetable"])

rule("wt_meal_frequency", "weight", "pattern",
     "Two to three structured meals a day, with light activity after eating, "
     "is the pattern the guidelines recommend — rather than frequent grazing.",
     "dgi",
     keywords=["weight", "meal", "frequency", "koybar", "কয়বার", "snack"])

rule("wt_protein", "weight", "satiety",
     "Protein at each meal — fish, dal, egg — keeps people fuller than the "
     "same energy taken as rice alone, which is the practical reason a "
     "protein-light Bangladeshi meal can leave someone hungry soon after.",
     "dgb",
     foods=["mosur_dal_boiled", "rui", "telapia", "chola_boiled"],
     keywords=["weight", "protein", "hungry", "khide", "খিদে", "full", "pet"])

# ─────────────────────────────────────────────────── general
rule("gen_food_variety", "general", "variety",
     "No single food supplies everything. The guidelines recommend eating "
     "across at least eight food groups, with vegetables, fruit, greens and "
     "roots making up roughly half the plate.",
     "dgi",
     keywords=["healthy", "balanced", "diet", "variety", "shustho", "সুস্থ"])

rule("gen_cooking_method", "general", "cooking",
     "Boiling, steaming and stir-frying preserve nutrients better than deep "
     "frying. Steamed rice and vegetables cooked without discarding the water "
     "retain more of what was in them.",
     "dgb",
     keywords=["cooking", "randha", "রান্না", "boil", "fry", "vaja", "steam",
               "healthy cooking"])

rule("gen_reused_oil", "general", "oil",
     "Reusing frying oil produces peroxides and free radicals associated with "
     "cancer risk. Oil should not be reused for repeated frying.",
     "dgb",
     keywords=["oil", "tel", "তেল", "fry", "vaja", "reuse", "cooking"])

rule("gen_vegetable_prep", "general", "preparation",
     "Wash vegetables before cutting, and cut into larger pieces. Cutting "
     "small and washing afterwards loses water-soluble vitamins.",
     "dgb",
     keywords=["vegetable", "shobji", "সবজি", "cutting", "washing", "prepare"])

rule("gen_activity", "general", "activity",
     "Light activity after a meal — a short walk, ordinary household work — "
     "is part of the guidance, not separate from it.",
     "dgb",
     keywords=["exercise", "activity", "walk", "hata", "হাঁটা", "after meal"])

rule("gen_sugar_limit", "general", "sugar",
     "Added sugar is recommended to stay under ten per cent of daily energy "
     "for everyone, not only people with diabetes.",
     "dgb",
     keywords=["sugar", "chini", "চিনি", "sweet", "misti", "মিষ্টি", "limit"])

rule("gen_water", "general", "hydration",
     "Water is counted as an essential nutrient in the guidelines, not an "
     "afterthought.",
     "dgb",
     keywords=["water", "pani", "পানি", "drink", "hydration"])

# ─────────────────────────────────────────────────── life stage
rule("life_pregnancy", "pregnancy", "general",
     "Requirements rise in pregnancy and lactation across energy, protein, "
     "iron and folate. This is a case where a personalised plan from a doctor "
     "or nutritionist matters more than general guidance.",
     "dgb",
     keywords=["pregnant", "pregnancy", "gorbhoboti", "গর্ভবতী", "baby",
               "lactation", "breastfeeding"])

rule("life_children", "children", "general",
     "Children who eat sugary foods often have a lower appetite for meals and "
     "are prone to tooth decay. Feeding guidance for under-twos is specific "
     "enough that it should come from a health worker rather than a general "
     "rule.",
     "dgb",
     keywords=["child", "baccha", "বাচ্চা", "kid", "children", "shishu",
               "শিশু", "baby"])


# ---------------------------------------------------------------------------
# validate and write
# ---------------------------------------------------------------------------

def main():
    ids = [r["id"] for r in RULES]
    assert len(ids) == len(set(ids)), "duplicate rule id"
    for r in RULES:
        assert r["source"] in SOURCES, f"{r['id']}: unknown source {r['source']}"
        assert r["keywords"], f"{r['id']}: no retrieval keywords"

    doc = {
        "schema_version": 1,
        "sources": SOURCES,
        "notes": {
            "purpose": "Dietary guidance retrieved alongside food rows. Supplies "
                       "framing and considerations, never nutrient values.",
            "hard_rule": "A rule may inform how advice is phrased. Every NUMBER "
                         "in an answer still comes from the food table.",
            "authority": "Rules sourced to 'dgb' are from the Bangladesh national "
                         "guideline. Rules sourced to 'dgi' or 'who' are regional "
                         "or international and are marked distinctly so a user can "
                         "see when guidance is not from their own country.",
            "review": "Intended for review and sign-off by a qualified "
                      "nutritionist before the system is used by anyone.",
        },
        "rules": RULES,
    }

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(RULES)} rules\n")
    for cond, n in Counter(r["condition"] for r in RULES).most_common():
        print(f"  {cond:14} {n}")
    print()
    for src, n in Counter(r["source"] for r in RULES).most_common():
        print(f"  {src:14} {n}  ({SOURCES[src]['authority']})")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()