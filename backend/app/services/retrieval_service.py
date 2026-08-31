"""Retrieval over the Bangladeshi food database.

Hybrid: BM25 (exact keyword) + dense embeddings (semantic).

RANKING DESIGN
--------------
Keyword-first, not weighted-sum.

The original design combined the two signals by weighted sum after min-max
normalising each. That failed in a way worth recording, because it is not
obvious from the formula: min-max normalisation awards 1.0 to whichever row
leads a signal, regardless of whether that row is a good match at all.

Observed case — the query "ami kototuku vat khabo akdin a?" (how much rice
should I eat in a day):

    Rice, BR-28, boiled     BM25 6.32   dense 0.31
    Sponge gourd, raw       BM25 0.00   dense 0.51

Dense scores across 274 short food records cluster tightly, roughly 0.44-0.51
for everything, so being "best" semantically is nearly meaningless — sponge
gourd led that cluster by 0.002 and was normalised to 1.0. Rice, an exact
keyword match, sat below the band because the query is mostly Banglish
function words. Result: 0.4x0 + 0.6x1.0 = 0.60 for gourd, beating rice, and
the model received three unrelated foods and correctly reported that it had
no rice data.

The fix is a ranking rule rather than a reweighting. When any row matches by
keyword, those rows ARE the candidate set; semantic similarity only orders
them. Dense retrieval leads only when no keyword matches at all — which is
exactly the case it exists for ("ami raate ki khabo", no food named).

This reflects the domain: in a food lookup, a user who types a food name
wants that food. A semantic neighbour is never a better answer than an exact
name match.
"""
import os

# Use the locally cached model without contacting Hugging Face. Without this,
# startup fails on a flaky connection even though the weights are on disk.
#
# NOTE: on a machine that has never run this project, comment these two lines
# out for the first start so the ~470 MB model can download, then restore them.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "bd_foods.json"

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Weights for reciprocal rank fusion. Keyword rank counts for more than
# semantic rank, because BM25 is sparse and decisive where it fires, while
# dense similarity is dense and nearly flat across this corpus.
W_SPARSE = 0.6
W_DENSE = 0.4

# Standard RRF damping constant. Large enough that the difference between
# rank 1 and rank 2 is small, so a near-tie does not become a landslide.
RRF_K = 60

# Absolute floor on raw cosine similarity, used only when NO row matches by
# keyword. Out-of-domain queries ("quantum physics") score below this against
# every row, so nothing survives and the model is handed an empty context.
MIN_DENSE = 0.25

# Word characters only. A plain .split() leaves punctuation glued to tokens,
# so "ilish," never matches the corpus token "ilish" — the food silently
# scores zero in BM25 and drops out of a comparison query. \w is Unicode-aware
# in Python 3, so Bangla script is preserved.
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Set True to print the query, its tokens, and the ranking decision.
DEBUG_SEARCH = False


def tokenize(text: str) -> list[str]:
    """Lowercase and split on word boundaries, discarding punctuation."""
    return _TOKEN_RE.findall(text.lower())


class RetrievalService:
    def __init__(self):
        self.foods = []
        self.source_meta = {}
        self.bm25 = None
        self.model = None
        self.embeddings = None
        self._load()

    def _load(self):
        with open(DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)

        self.foods = data.get("foods", [])
        self.source_meta = data.get("source", {})      # citation for the whole table

        if not self.foods:
            print("WARNING: bd_foods.json has no entries — retrieval will return nothing.")
            return

        corpus = [self._searchable_text(food) for food in self.foods]

        # --- sparse index ---
        # Index and query MUST use the same tokenizer, or matches are lost.
        self.bm25 = BM25Okapi([tokenize(doc) for doc in corpus])

        # --- dense index (computed once at startup, not per request) ---
        print(f"Loading embedding model ({MODEL_NAME})...")
        self.model = SentenceTransformer(MODEL_NAME)
        self.embeddings = self.model.encode(
            corpus,
            normalize_embeddings=True,   # lets us use dot product as cosine similarity
        )

        verified = sum(1 for f in self.foods if f.get("verified"))
        aliases = sum(len(f.get("name_banglish", [])) for f in self.foods)
        print(f"Retrieval ready: {len(self.foods)} foods ({verified} verified), "
              f"{aliases} aliases, keyword-first hybrid index built.")

    def _searchable_text(self, food):
        """Everything a user might type to mean this food."""
        parts = [
            food.get("name_en", ""),
            food.get("name_bn", ""),
            food.get("name_fct_bn", ""),
            food.get("category", ""),
            *food.get("name_banglish", []),
        ]
        return " ".join(p for p in parts if p)

    @staticmethod
    def _compute_portion(food):
        """Scale verified per-100g values to the assumed household portion.

        Computed rather than stored, so the FCT values stay pristine and the
        portion assumption stays visible and changeable.
        """
        per_100g = food.get("per_100g") or {}
        grams = food.get("portion_grams")

        if not grams:
            return {key: None for key in per_100g}

        factor = grams / 100.0
        out = {}
        for key, value in per_100g.items():
            if value is None:
                out[key] = None
            elif key == "calories":
                out[key] = round(value * factor)          # whole kcal
            else:
                out[key] = round(value * factor, 1)       # 1dp for gram values
        return out

    def citation_for(self, food):
        """Citation string: FCT food code plus the table it came from."""
        code = food.get("fct_code")
        table = self.source_meta.get("name", "unknown source")
        return f"{table} ({code})" if code else table

    @staticmethod
    def _ranks(scores):
        """Position of each row when sorted best-first. Rank 0 is the best."""
        order = np.argsort(-np.asarray(scores, dtype=float))
        ranks = np.empty(len(order), dtype=int)
        ranks[order] = np.arange(len(order))
        return ranks

    def _rank_candidates(self, bm25_raw, dense_raw):
        """Return row indices, best first, plus how the set was chosen.

        Keyword-first. If any row has real keyword overlap, only those rows
        compete — a semantic neighbour must not outrank an exact name match.
        Within that set, both signals order the results by reciprocal rank,
        so a near-miss on one signal cannot swamp a clear win on the other.
        """
        bm25_raw = np.asarray(bm25_raw, dtype=float)
        dense_raw = np.asarray(dense_raw, dtype=float)

        keyword_hits = np.flatnonzero(bm25_raw > 0)

        if keyword_hits.size:
            candidates, mode = keyword_hits, "keyword"
        else:
            # No food name recognised. Semantic search leads, and the absolute
            # floor decides whether anything is relevant at all.
            candidates = np.flatnonzero(dense_raw >= MIN_DENSE)
            mode = "semantic"

        if candidates.size == 0:
            return [], mode

        bm_rank = self._ranks(bm25_raw)
        dn_rank = self._ranks(dense_raw)

        def rrf(i):
            sparse = W_SPARSE / (RRF_K + bm_rank[i] + 1) if bm25_raw[i] > 0 else 0.0
            return sparse + W_DENSE / (RRF_K + dn_rank[i] + 1)

        return sorted(candidates, key=rrf, reverse=True), mode

    def search(self, query: str, top_k: int = 3, condition: str = "none"):
        if not self.bm25:
            return []

        # Tokenize once and reuse, so what is logged is exactly what is scored.
        tokens = tokenize(query)

        bm25_raw = self.bm25.get_scores(tokens)

        # dense — dot product of normalized vectors == cosine similarity
        q_vec = self.model.encode([query], normalize_embeddings=True)[0]
        dense_raw = self.embeddings @ q_vec

        ordered, mode = self._rank_candidates(bm25_raw, dense_raw)

        if DEBUG_SEARCH:
            print(f"[search] {query!r} tokens={tokens} mode={mode} "
                  f"candidates={len(ordered)} max_bm25={float(np.max(bm25_raw)):.2f}")

        results = []
        for i in ordered[:top_k]:
            food = self.foods[i]
            results.append({
                **food,
                "per_portion": self._compute_portion(food),   # derived at query time
                "citation": self.citation_for(food),
                "_mode": mode,
                "_bm25": round(float(bm25_raw[i]), 3),
                "_dense": round(float(dense_raw[i]), 3),
                "_score": round(float(bm25_raw[i]), 3),       # kept for compatibility
            })

        return self._apply_condition_filter(results, condition)

    def _apply_condition_filter(self, results, condition):
        """Annotate conflicts rather than hiding them.

        Removing a food the user explicitly asked about would look like a
        retrieval failure; flagging it lets the answer explain the caution.
        """
        if condition == "none":
            return results

        flag = f"{condition}_caution"
        for r in results:
            r["_caution"] = flag in r.get("condition_flags", [])
        return results


retrieval_service = RetrievalService()