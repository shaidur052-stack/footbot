"""Download the clinical Q&A corpus and report what is actually in it.

Downloads only. Nothing is filtered or indexed yet — the column names and row
shape differ between these datasets, and guessing at them wastes a run.

Cache goes outside the project so a few GB of dataset files are not synced by
OneDrive or picked up by git.
"""

import os
from pathlib import Path

# Keep the download off OneDrive and out of the repo.
CACHE = Path("C:/datasets/hf")
CACHE.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(CACHE)
os.environ["HF_DATASETS_CACHE"] = str(CACHE / "datasets")

# Loading must be able to reach Hugging Face, so the offline flags that
# retrieval_service sets at import time must not apply here.
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)

from datasets import load_dataset  # noqa: E402

# Apache-2.0. The larger MedDialog sets have clearer volume but their cards
# assign copyright to the platforms they were scraped from, which is a
# question we do not want asked about a submitted project.
DATASET = "avaliev/chat_doctor"


def main():
    print(f"downloading {DATASET} — this may take a few minutes\n")
    ds = load_dataset(DATASET)

    print("splits:")
    for name, split in ds.items():
        print(f"  {name}: {len(split):,} rows")

    split = ds["train"] if "train" in ds else next(iter(ds.values()))

    print(f"\ncolumns: {split.column_names}\n")
    print("first 3 rows, truncated:\n")
    for i in range(min(3, len(split))):
        row = split[i]
        print(f"--- row {i} ---")
        for k, v in row.items():
            text = str(v).replace("\n", " ")
            print(f"  {k}: {text[:220]}{'...' if len(text) > 220 else ''}")
        print()

    # How much of this is even about food? A rough keyword pass, so we know
    # the filter is worth writing before writing it.
    terms = ["diet", "food", "eat", "rice", "sugar", "diabet", "nutrition",
             "weight", "meal", "protein", "vitamin", "calorie", "fruit",
             "vegetable", "milk", "fat ", "cholesterol", "blood pressure"]

    field = next((c for c in ("input", "question", "instruction", "patient")
                  if c in split.column_names), split.column_names[0])
    print(f"scanning the '{field}' column for diet-related rows...")

    sample = split.select(range(min(20_000, len(split))))
    hits = sum(1 for r in sample
               if any(t in str(r[field]).lower() for t in terms))

    print(f"  {hits:,} of {len(sample):,} sampled rows mention food or diet "
          f"({100 * hits / len(sample):.1f}%)")
    print(f"  projected over the full split: ~{int(len(split) * hits / len(sample)):,} rows")


if __name__ == "__main__":
    main()