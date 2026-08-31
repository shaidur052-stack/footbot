"""Retrieval over the condition rules.

A second, much smaller index alongside the food table. Kept separate rather
than merged because the two answer different questions and carry different
authority: the food table supplies measured values, this supplies dietary
framing. Blurring them in one index would blur them in the citation.

Small enough (26 rules) that keyword scoring is sufficient — no embeddings,
no model, nothing to load. Retrieval here costs microseconds.
"""

import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "condition_rules.json"

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


class GuidanceService:
    """Loads the rules and matches them by condition and by query terms."""

    def __init__(self):
        self.rules = []
        self.sources = {}
        self._load()

    def _load(self):
        if not DATA_PATH.exists():
            print(f"[guidance] no rules at {DATA_PATH} — guidance disabled")
            return

        try:
            data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except Exception as exc:                  # noqa: BLE001
            print(f"[guidance] could not read rules ({type(exc).__name__}) — disabled")
            return

        self.rules = data.get("rules", [])
        self.sources = data.get("sources", {})

        # Pre-tokenise once. The set is tiny, but doing it per request would
        # be pointless work on every message.
        for r in self.rules:
            terms = set()
            for kw in r.get("keywords", []):
                terms.update(tokenize(kw))
            r["_terms"] = terms

        national = sum(1 for r in self.rules
                       if self.sources.get(r["source"], {}).get("authority") == "national")
        print(f"[guidance] ready: {len(self.rules)} rules "
              f"({national} from the Bangladesh national guideline)")

    def citation_for(self, rule) -> str:
        """Citation string. Names the authority level, so a user can see when
        guidance comes from outside Bangladesh."""
        src = self.sources.get(rule.get("source"), {})
        name = src.get("name", "unknown source")
        authority = src.get("authority")
        return f"{name} (regional guidance)" if authority == "regional" else name

    def search(self, query: str, condition: str = "none",
               food_ids: list[str] | None = None, top_k: int = 3) -> list[dict]:
        """Rules relevant to this question.

        Three ways a rule earns its place, in descending weight:
          * it is about the user's stated condition
          * it applies to a food that retrieval just returned
          * its keywords appear in the question

        A rule for a condition the user does not have is only included when
        the question itself raises it — someone with no condition asking
        "is rice ok for diabetes" should still get the diabetes rule.
        """
        if not self.rules:
            return []

        q_terms = set(tokenize(query))
        food_ids = set(food_ids or [])

        scored = []
        for r in self.rules:
            score = 0.0

            if condition != "none" and r["condition"] == condition:
                score += 3.0                      # their own condition

            if food_ids & set(r.get("applies_to_foods", [])):
                score += 2.0                      # about a food just retrieved

            overlap = len(q_terms & r["_terms"])
            if overlap:
                score += min(overlap, 3) * 1.0    # capped: one strong term is
                                                  # enough, ten is not ten times
                                                  # better

            # General advice is a weak default — useful when nothing else
            # matches, never a reason to displace something specific.
            if r["condition"] == "general" and score == 0:
                score += 0.2

            if score > 0:
                scored.append((score, r))

        scored.sort(key=lambda t: -t[0])

        out = []
        for score, r in scored[:top_k]:
            # A bare "general" default is noise unless the question gave us
            # nothing else to go on.
            if score <= 0.2 and len(out) >= 1:
                break
            out.append({
                "id": r["id"],
                "condition": r["condition"],
                "topic": r["topic"],
                "guidance": r["guidance"],
                "citation": self.citation_for(r),
                "_score": round(score, 2),
            })
        return out


guidance_service = GuidanceService()