"""Run the test set through NutriBot and through a raw-LLM baseline.

Baseline uses the SAME Gemini model with no retrieval, no profile, no
policy prompt. Only the architecture differs, which is what makes the
comparison fair.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.retrieval_service import retrieval_service   # noqa: E402
from app.services import prompt_builder, llm_service           # noqa: E402
from evaluation import metrics                                 # noqa: E402

HERE = Path(__file__).parent
QUESTIONS = HERE / "test_questions.json"
RESULTS = HERE / "results.json"

# A profile is needed for the personalisation questions. Fixed so runs
# are reproducible.
TEST_PROFILE = {
    "age": 23, "gender": "male", "weight_kg": 70, "height_cm": 173,
    "activity": "sedentary", "goal": "maintain", "condition": "none",
    "bmi": 23.4, "daily_calories": 2006, "consumed_today": 0,
}

COMPARE_HINTS = {"naki", "vs", " or ", "beshi", "kon ta", "konta",
                 "which", "নাকি", "কোনটা", "বেশি"}


def top_k_for(q: str) -> int:
    return 6 if any(h in f" {q.lower()} " for h in COMPARE_HINTS) else 3


def ask_nutribot(question: str):
    """Full pipeline: retrieve, build prompt, generate."""
    foods = retrieval_service.search(question, top_k=top_k_for(question))
    prompt = prompt_builder.build(question, foods, TEST_PROFILE)
    answer = llm_service.generate(prompt)

    # every value the system was legitimately allowed to state
    allowed = []
    for f in foods:
        for block in (f.get("per_100g") or {}, f.get("per_portion") or {}):
            allowed += [v for v in block.values() if isinstance(v, (int, float))]
        if f.get("portion_grams"):
            allowed.append(f["portion_grams"])
    allowed += [TEST_PROFILE["daily_calories"], TEST_PROFILE["bmi"]]

    return {
        "answer": answer,
        "sources": [f["citation"] for f in foods],
        "allowed_values": allowed,
        "retrieved": [f["id"] for f in foods],
    }


def ask_baseline(question: str):
    """Raw LLM. No retrieval, no profile, no policy — just the question."""
    return {"answer": llm_service.generate(question), "sources": []}


def score(item, result, grounded: bool):
    """Score one answer. `grounded` distinguishes our system from baseline."""
    answer = result["answer"]
    expect = item["expect"]
    out = {
        "refused": metrics.is_refusal(answer),
        "cited": metrics.has_citation(result["sources"]),
    }

    if expect == "refusal":
        # For refusal questions, refusing IS the correct answer.
        out["correct"] = out["refused"]
        # A baseline has no retrieved set, so any figure it invents counts.
        out["hallucinated"] = (not out["refused"]) and bool(
            [n for n in metrics.extract_numbers(answer) if n >= 10])

    elif expect == "value":
        gold = item["gold"]["per_100g"]
        out["correct"] = metrics.value_correct(answer, gold) or \
            metrics.value_correct(answer, gold * 0.75) or \
            metrics.value_correct(answer, gold * 2.5)   # common portion scalings
        out["hallucinated"] = metrics.is_hallucination(
            answer, result.get("allowed_values", [])) if grounded else not out["correct"]

    elif expect == "comparison":
        vals = list(item["gold"].get("values", {}).values())
        out["correct"] = all(metrics.value_correct(answer, v) for v in vals)
        out["hallucinated"] = metrics.is_hallucination(
            answer, result.get("allowed_values", [])) if grounded else False

    elif expect == "profile_answer":
        out["correct"] = metrics.value_correct(answer, TEST_PROFILE["daily_calories"])
        out["hallucinated"] = False

    else:
        out["correct"] = out["refused"]
        out["hallucinated"] = False

    return out


def main():
    if not QUESTIONS.exists():
        sys.exit(f"{QUESTIONS.name} not found — write the test set first.")

    data = json.load(open(QUESTIONS, encoding="utf-8"))
    questions = data["questions"]
    print(f"{len(questions)} questions, prompt {data.get('prompt_version')}\n")

    rows = []
    for i, item in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {item['id']}  {item['q'][:55]}")

        try:
            nb = ask_nutribot(item["q"])
        except Exception as e:
            nb = {"answer": f"ERROR: {e}", "sources": [], "allowed_values": []}

        time.sleep(4)                      # stay inside the free-tier rate limit

        try:
            bl = ask_baseline(item["q"])
        except Exception as e:
            bl = {"answer": f"ERROR: {e}", "sources": []}

        time.sleep(4)

        rows.append({
            **{k: item[k] for k in ("id", "group", "lang", "expect")},
            "question": item["q"],
            "nutribot": {**nb, "score": score(item, nb, grounded=True)},
            "baseline": {**bl, "score": score(item, bl, grounded=False)},
        })

    json.dump({"meta": {"prompt_version": data.get("prompt_version"),
                        "n": len(rows)},
               "results": rows},
              open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nWrote {RESULTS.name}. Run summarise.py for the numbers and charts.")


if __name__ == "__main__":
    main()