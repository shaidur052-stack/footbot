"""Generate labelled intent queries for classifier fine-tuning.

Method: synthetic generation via LLM, then manual spot-validation.
Queries are produced in Bangla, English, and Banglish because the
deployed system receives all three.

The free Gemini tier allows 15 requests per minute, so calls are throttled
and a 429 is treated as "too fast" rather than fatal. Progress is written
after every label, and rerunning resumes from what already exists.
"""

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import llm_service  # noqa: E402

OUT_PATH = Path(__file__).parent / "labeled_queries.csv"
FOOD_DB = Path(__file__).resolve().parents[1] / "data" / "bd_foods.json"

# Each label carries a definition and seed examples. The definition matters
# more than the examples — it keeps generation on-distribution.
LABELS = {
    "food_fact": {
        "definition": "Asks for a nutrition value of one specific food.",
        "seeds": ["bhat e koto calorie?", "পালং শাকে কত প্রোটিন?", "calories in one ruti"],
    },
    "food_compare": {
        "definition": "Compares two or more foods, or two preparations of one food.",
        "seeds": ["korola vaji vs korola siddha koto calorie?",
                  "dal or ruti, which has more protein?",
                  "ভাত নাকি রুটি কোনটায় কম ক্যালরি?"],
    },
    "food_advice": {
        "definition": "Asks whether they should eat something, or what to eat, given their situation.",
        "seeds": ["should I eat rice tonight?", "ওজন কমাতে কী খাবো?", "raate ki khabo"],
    },
    "profile_question": {
        "definition": "Asks about the user's own body or targets: calories needed, BMI, weight goal.",
        "seeds": ["how many calories do I need?", "আমার বিএমআই কত?", "amar daily target koto"],
    },
    "greeting_meta": {
        "definition": "Greeting, thanks, or a question about the assistant itself.",
        "seeds": ["hello", "আপনি কে?", "what can you do?", "thanks"],
    },
    "out_of_scope": {
        "definition": "Unrelated to food, nutrition, or the user's health profile.",
        "seeds": ["who won the match?", "fix my laptop", "translate this to French"],
    },
}

PER_LABEL = 350          # ~2100 rows total
BATCH_SIZE = 50          # smaller batches = better variety, fewer truncations

RPM_LIMIT = 15                     # free tier: requests per minute per model
MIN_GAP = 60.0 / RPM_LIMIT + 0.5   # ~4.5s between calls, with headroom

_last_call = 0.0


def _throttle():
    """Space calls so we never exceed the per-minute quota."""
    global _last_call
    wait = MIN_GAP - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()


def load_food_names():
    """Real food names keep generated queries on-domain.

    name_fct_bn is deliberately excluded — it is the table's own
    transliteration, not something a user would type.
    """
    with open(FOOD_DB, encoding="utf-8") as f:
        foods = json.load(f)["foods"]
    names = []
    for food in foods:
        names.append(food["name_en"])
        names.append(food["name_bn"])
        names.extend(food.get("name_banglish", []))
    return names


def build_prompt(label, spec, food_names, batch_size, existing):
    """Ask for one batch. Passing back existing queries reduces repetition."""
    avoid = "\n".join(f"- {q}" for q in list(existing)[-25:])
    return f"""Generate {batch_size} realistic user queries for a Bangladeshi nutrition chatbot.

INTENT LABEL: {label}
DEFINITION: {spec['definition']}

EXAMPLES OF THIS INTENT:
{chr(10).join('- ' + s for s in spec['seeds'])}

FOODS AVAILABLE IN THE DATABASE (use these where a food is needed):
{', '.join(food_names[:60])}

REQUIREMENTS:
- Roughly one third Bangla script, one third English, one third Banglish
  (romanised Bangla, e.g. "bhat e koto calorie").
- Vary length: some two words, some full sentences.
- Include realistic typos and casual phrasing in about one in ten.
- Every query must genuinely belong to the label "{label}".

DO NOT REPEAT THESE:
{avoid}

Output ONLY the queries, one per line, no numbering, no quotes, no commentary."""


def generate_for_label(label, spec, food_names, existing=None):
    collected = set(existing or [])
    stalls = 0

    while len(collected) < PER_LABEL:
        need = min(BATCH_SIZE, PER_LABEL - len(collected))
        prompt = build_prompt(label, spec, food_names, need, collected)

        _throttle()
        try:
            raw = llm_service.generate(prompt)
        except Exception as e:
            # A 429 means we are ahead of the quota WINDOW, not out of quota
            # for the day. Wait it out and continue rather than abandoning
            # the label — the previous version lost four labels to this.
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                print("  quota window hit — waiting 65s")
                time.sleep(65)
                continue
            print(f"  batch failed ({type(e).__name__}); stopping at {len(collected)}")
            break

        before = len(collected)
        for line in raw.splitlines():
            q = line.strip().lstrip("-•0123456789. ").strip()
            if 2 < len(q) < 200:
                collected.add(q)

        print(f"  {label}: {len(collected)}/{PER_LABEL} (+{len(collected) - before})")

        if len(collected) == before:
            stalls += 1
            if stalls >= 2:            # two dry batches = variety exhausted
                print("  no new variety; moving on")
                break
        else:
            stalls = 0

    return collected


def main():
    food_names = load_food_names()

    # Resume: keep whatever a previous run produced.
    existing = {}
    if OUT_PATH.exists():
        with open(OUT_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing.setdefault(row["label"], set()).add(row["query"])
        print(f"resuming — already have {({k: len(v) for k, v in existing.items()})}\n")

    rows = []
    for label, spec in LABELS.items():
        have = existing.get(label, set())

        if len(have) >= PER_LABEL:
            print(f"\n{label}: already complete ({len(have)})")
            queries = have
        else:
            print(f"\nGenerating: {label}")
            queries = generate_for_label(label, spec, food_names, have)

        rows += [{"query": q, "label": label} for q in queries]

        # Write after every label, so a crash costs one label, not the run.
        with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["query", "label"])
            w.writeheader()
            w.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUT_PATH}")
    print("NEXT: open the CSV and spot-check ~50 rows before training.")


if __name__ == "__main__":
    main()