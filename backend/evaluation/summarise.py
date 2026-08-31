"""Turn results.json into report numbers and charts.

Every figure here is measured. If a number looks disappointing, it goes in
the report as-is — a defensible 74% is worth more than an unverifiable 88%.
"""

import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                 # no display needed; write straight to file
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESULTS = HERE / "results.json"
CHARTS = HERE / "charts"
CHARTS.mkdir(exist_ok=True)

TEAL = "#0F766E"
AMBER = "#E8A32D"
RED = "#B0453A"
GREY = "#94A3B8"


def pct(numerator, denominator):
    return 100.0 * numerator / denominator if denominator else 0.0


def summarise(rows):
    """Overall and per-group rates for both systems."""
    out = {}
    for system in ("nutribot", "baseline"):
        scores = [r[system]["score"] for r in rows]
        out[system] = {
            "accuracy": pct(sum(s["correct"] for s in scores), len(scores)),
            "hallucination": pct(sum(s["hallucinated"] for s in scores), len(scores)),
            "citation": pct(sum(s["cited"] for s in scores), len(scores)),
        }

    # correct-refusal rate, measured only where refusal is the right answer
    refusal_rows = [r for r in rows if r["expect"] == "refusal"]
    for system in ("nutribot", "baseline"):
        out[system]["refusal"] = pct(
            sum(r[system]["score"]["refused"] for r in refusal_rows),
            len(refusal_rows),
        )
    return out


def by_key(rows, key):
    """Accuracy broken down by group or language."""
    buckets = defaultdict(lambda: {"nutribot": [], "baseline": []})
    for r in rows:
        for system in ("nutribot", "baseline"):
            buckets[r[key]][system].append(r[system]["score"]["correct"])
    return {
        k: {s: pct(sum(v[s]), len(v[s])) for s in ("nutribot", "baseline")}
        for k, v in buckets.items()
    }


def chart_headline(summary, n):
    metrics = ["accuracy", "citation", "refusal", "hallucination"]
    labels = ["Answer\naccuracy", "Citation\nrate",
              "Correct\nrefusal", "Hallucination\n(lower better)"]
    nb = [summary["nutribot"][m] for m in metrics]
    bl = [summary["baseline"][m] for m in metrics]

    x = range(len(metrics))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 4.6))

    b1 = ax.bar([i - w / 2 for i in x], nb, w, label="NutriBot BD", color=TEAL)
    b2 = ax.bar([i + w / 2 for i in x], bl, w, label="Raw LLM (same model)", color=GREY)

    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                    f"{bar.get_height():.0f}%", ha="center", fontsize=9)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("percent")
    ax.set_ylim(0, 108)
    ax.set_title(f"NutriBot BD vs ungrounded baseline  (n={n})", fontsize=12, pad=12)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(CHARTS / "headline_comparison.png", dpi=160)
    plt.close(fig)


def chart_by_group(groups):
    order = [g for g in ["in_db_fact", "not_in_db", "preparation",
                         "comparison", "profile", "out_of_scope"] if g in groups]
    nb = [groups[g]["nutribot"] for g in order]
    bl = [groups[g]["baseline"] for g in order]

    y = range(len(order))
    h = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 0.75 * len(order) + 2))

    ax.barh([i + h / 2 for i in y], nb, h, label="NutriBot BD", color=TEAL)
    ax.barh([i - h / 2 for i in y], bl, h, label="Raw LLM", color=GREY)

    ax.set_yticks(list(y))
    ax.set_yticklabels([g.replace("_", " ") for g in order])
    ax.set_xlabel("accuracy (%)")
    ax.set_xlim(0, 105)
    ax.set_title("Accuracy by question type", fontsize=12, pad=12)
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.25)

    fig.tight_layout()
    fig.savefig(CHARTS / "accuracy_by_group.png", dpi=160)
    plt.close(fig)


def chart_by_language(langs):
    order = [l for l in ["bn", "en", "banglish"] if l in langs]
    names = {"bn": "Bangla script", "en": "English", "banglish": "Banglish"}
    nb = [langs[l]["nutribot"] for l in order]
    bl = [langs[l]["baseline"] for l in order]

    x = range(len(order))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7, 4.2))

    ax.bar([i - w / 2 for i in x], nb, w, label="NutriBot BD", color=TEAL)
    ax.bar([i + w / 2 for i in x], bl, w, label="Raw LLM", color=GREY)

    ax.set_xticks(list(x))
    ax.set_xticklabels([names[l] for l in order])
    ax.set_ylabel("accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Accuracy by input language", fontsize=12, pad=12)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(CHARTS / "accuracy_by_language.png", dpi=160)
    plt.close(fig)


def main():
    if not RESULTS.exists():
        raise SystemExit("results.json not found — run run_eval.py first.")

    data = json.load(open(RESULTS, encoding="utf-8"))
    rows = data["results"]

    summary = summarise(rows)
    groups = by_key(rows, "group")
    langs = by_key(rows, "lang")

    print(f"\n{'':22}{'NutriBot':>10}{'Baseline':>10}")
    print("-" * 42)
    for metric in ("accuracy", "hallucination", "citation", "refusal"):
        print(f"{metric:22}{summary['nutribot'][metric]:>9.1f}%"
              f"{summary['baseline'][metric]:>9.1f}%")

    print("\nBy question type")
    for g, v in groups.items():
        print(f"  {g:16}{v['nutribot']:>7.1f}%{v['baseline']:>8.1f}%")

    print("\nBy language")
    for l, v in langs.items():
        print(f"  {l:16}{v['nutribot']:>7.1f}%{v['baseline']:>8.1f}%")

    chart_headline(summary, len(rows))
    chart_by_group(groups)
    chart_by_language(langs)

    json.dump({"summary": summary, "by_group": groups, "by_language": langs},
              open(HERE / "summary.json", "w"), indent=2)

    print(f"\nCharts written to {CHARTS}")

    # Errors are the most useful part of the output — read them.
    wrong = [r for r in rows if not r["nutribot"]["score"]["correct"]]
    if wrong:
        print(f"\n{len(wrong)} NutriBot errors — inspect these:")
        for r in wrong[:12]:
            print(f"  {r['id']}  {r['question'][:52]}")
            print(f"        -> {r['nutribot']['answer'][:80]}")


if __name__ == "__main__":
    main()