"""Intent classification — the routing layer.

A fine-tuned XLM-RoBERTa encoder decides what CONTEXT a question needs, so the
pipeline can skip work that does not apply. It classifies behaviour, never
facts: nutritional values stay in retrieval where they can be checked.

DESIGN PRINCIPLE
----------------
Routing selects context. It does not grant or withhold answers.

An earlier version let `out_of_scope` refuse without ever calling the model.
That put a hard rejection behind a classifier that is 98.4% accurate on
synthetic data and less on real phrasing, so legitimate questions were silently
dropped. The genuine hazard in this system is an invented NUMBER, and that is
prevented by the prompt constraints on every path. Routing has no part in it.

Consequence: a misroute costs a slightly worse answer, never a rejected
question. Thresholds remain, because skipping retrieval is still a small cost
worth guarding, but nothing is unrecoverable.

STARTUP COST
------------
Loading is triggered explicitly by warmup() at application startup rather than
lazily on first use. Lazy loading kept boot fast but moved a ~10 second cost
onto whoever asked the first question — measured in production as
classify=10358ms on a cold process. Paying it during boot is the right trade:
nobody is waiting then.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml" / "saved_model"

# Queries are short; anything past this is padding or an attack.
MAX_TOKENS = 64


# ---------------------------------------------------------------------------
# routing policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentSpec:
    """What context an intent needs, and what it costs to get it wrong.

    Attributes:
        retrieve:   run database search
        top_k:      rows to fetch (comparisons need every food named)
        profile:    advisory only — chat.py now loads the profile for every
                    intent, because gating a sub-millisecond database read
                    behind a model prediction meant one misroute silently
                    disabled personalisation
        llm:        call the generative model. True for every intent.
        min_conf:   confidence required to act on this prediction
        degrade_to: where to route when min_conf is not met
        rationale:  why min_conf sits where it does — kept in code because a
                    threshold without a reason becomes a magic number the next
                    person is afraid to touch
    """
    retrieve: bool
    top_k: int
    profile: bool
    llm: bool
    min_conf: float
    degrade_to: str | None
    rationale: str


SAFE_INTENT = "food_fact"

INTENTS: Mapping[str, IntentSpec] = {

    "food_fact": IntentSpec(
        retrieve=True, top_k=3, profile=False, llm=True,
        min_conf=0.0, degrade_to=None,
        rationale="The safe harbour itself. Never degrades; always answers.",
    ),

    "food_compare": IntentSpec(
        retrieve=True, top_k=6, profile=False, llm=True,
        min_conf=0.45, degrade_to=SAFE_INTENT,
        rationale=(
            "Cheap to be wrong — a comparison read as a fact still answers, "
            "just with fewer rows. The reverse error is worse (top_k=3 can "
            "drop one of the named foods), so over-predicting this label is "
            "safer than under-predicting it."
        ),
    ),

    "food_advice": IntentSpec(
        retrieve=True, top_k=4, profile=True, llm=True,
        min_conf=0.50, degrade_to=SAFE_INTENT,
        rationale=(
            "Differs from the safe harbour only in how many rows it fetches. "
            "Being wrong costs one extra row."
        ),
    ),

    "profile_question": IntentSpec(
        retrieve=False, top_k=0, profile=True, llm=True,
        min_conf=0.70, degrade_to="food_advice",
        rationale=(
            "Skips retrieval. If wrong about a food question, the model gets "
            "no rows. Degrades to food_advice, which retrieves — covering "
            "both readings of an ambiguous query."
        ),
    ),

    "greeting_meta": IntentSpec(
        retrieve=False, top_k=0, profile=False, llm=True,
        min_conf=0.75, degrade_to=SAFE_INTENT,
        rationale=(
            "Skips retrieval entirely, so a food question landing here gets "
            "no data. Greetings are short and unambiguous, so genuine ones "
            "clear a high bar easily."
        ),
    ),

    "out_of_scope": IntentSpec(
        retrieve=False, top_k=0, profile=False, llm=True,
        min_conf=0.97, degrade_to=SAFE_INTENT,
        rationale=(
            "Skips retrieval but STILL generates. It previously refused "
            "without calling the model, which rejected food questions that "
            "were not nutrition questions. The real boundary is numeric and "
            "is enforced by the prompt, so this label now only means 'no "
            "database lookup needed'."
        ),
    ),
}


# ---------------------------------------------------------------------------
# keyword fallback
# ---------------------------------------------------------------------------

_FALLBACK_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("greeting_meta", re.compile(
        r"^\s*(hi|hey|hello|salam|assalamu\s*alaikum|আসসালামু|হ্যালো|নমস্কার|thanks?|"
        r"thank you|ধন্যবাদ)\b|^\s*(who|what)\s+are\s+you\b", re.IGNORECASE)),
    ("profile_question", re.compile(
        r"\b(my|amar|আমার)\b.*\b(bmi|calorie|target|weight|goal|ওজন|ক্যালরি)\b|"
        r"\bhow many calories do i\b", re.IGNORECASE)),
    ("food_compare", re.compile(
        r"\b(vs|versus|naki|নাকি|কোনটা|compare)\b|\bwhich (one )?(has|is)\b|"
        r"\b(beshi|বেশি|kom|কম)\b.*\b(naki|নাকি|or)\b", re.IGNORECASE)),
    ("food_advice", re.compile(
        r"\b(should i|can i eat|khete pari|খাওয়া|ki khabo|কী খাব|kototuku|"
        r"কতটুকু|diet plan|meal plan|healthy)\b", re.IGNORECASE)),
)


# ---------------------------------------------------------------------------
# decision record
# ---------------------------------------------------------------------------

@dataclass
class Route:
    """A routing decision, with enough detail to explain it afterwards."""
    intent: str
    predicted: str
    confidence: float | None
    degraded: bool
    source: str                      # "model" | "fallback" | "error"
    retrieve: bool
    top_k: int
    profile: bool
    llm: bool
    scores: dict[str, float] = field(default_factory=dict)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "predicted": self.predicted,
            "confidence": self.confidence,
            "degraded": self.degraded,
            "source": self.source,
            "note": self.note,
        }

    # dict-style access so existing call sites keep working
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


def _route_from(intent: str, **kw: Any) -> Route:
    spec = INTENTS[intent]
    return Route(
        intent=intent,
        retrieve=spec.retrieve,
        top_k=spec.top_k,
        profile=spec.profile,
        llm=spec.llm,
        **kw,
    )


# ---------------------------------------------------------------------------
# the service
# ---------------------------------------------------------------------------

class ClassifierService:
    """Thread-safe, degrades rather than failing, warmed at startup."""

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._torch = None
        self._id2label: dict[int, str] = {}
        self._info: dict[str, Any] = {}
        self._load_attempted = False
        self._lock = threading.Lock()

    # ---- loading ----

    @property
    def ready(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    @property
    def info(self) -> dict[str, Any]:
        self._ensure_loaded()
        return dict(self._info)

    def warmup(self) -> None:
        """Load the model and run one inference, at startup.

        The dummy inference matters as much as the load: the first forward
        pass allocates buffers and is several times slower than the rest.
        """
        self._ensure_loaded()
        if self._model is not None:
            self.classify("warmup query about rice")

    def _ensure_loaded(self) -> None:
        if self._load_attempted:
            return
        with self._lock:
            if self._load_attempted:          # another thread won the race
                return
            self._load_attempted = True
            self._load()

    def _load(self) -> None:
        if not (MODEL_DIR / "config.json").exists():
            print(f"[classifier] no model at {MODEL_DIR} — keyword fallback active")
            return

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._torch = torch
            self._tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
            self._model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
            self._model.eval()                # disable dropout for inference

            self._id2label = {int(k): v for k, v in self._model.config.id2label.items()}

            unknown = set(self._id2label.values()) - set(INTENTS)
            if unknown:
                print(f"[classifier] WARNING: model emits unknown labels {unknown}; "
                      f"they will degrade to {SAFE_INTENT}")

            info_path = MODEL_DIR / "training_info.json"
            if info_path.exists():
                self._info = json.loads(info_path.read_text())

            acc = self._info.get("test_accuracy")
            suffix = f", test accuracy {acc:.3f}" if isinstance(acc, (int, float)) else ""
            print(f"[classifier] ready: {len(self._id2label)} intents{suffix}")

        except Exception as exc:              # noqa: BLE001 — availability over accuracy
            print(f"[classifier] load failed ({type(exc).__name__}: {exc}) — "
                  f"keyword fallback active")
            self._model = None

    # ---- classification ----

    def _fallback(self, message: str) -> Route:
        for label, pattern in _FALLBACK_PATTERNS:
            if pattern.search(message):
                return _route_from(
                    label, predicted=label, confidence=None, degraded=False,
                    source="fallback", note="keyword match; model unavailable",
                )
        return _route_from(
            SAFE_INTENT, predicted=SAFE_INTENT, confidence=None, degraded=False,
            source="fallback", note="no keyword match; safe default",
        )

    def classify(self, message: str) -> Route:
        """Decide what context one message needs. Never raises."""
        text = (message or "").strip()
        if not text:
            return _route_from(
                SAFE_INTENT, predicted=SAFE_INTENT, confidence=None,
                degraded=False, source="fallback", note="empty message",
            )

        self._ensure_loaded()
        if self._model is None:
            return self._fallback(text)

        try:
            inputs = self._tokenizer(
                text, return_tensors="pt", truncation=True, max_length=MAX_TOKENS
            )
            with self._torch.no_grad():       # inference only; no gradient graph
                logits = self._model(**inputs).logits

            probs = self._torch.softmax(logits, dim=-1)[0]
            scores = {self._id2label[i]: round(float(p), 4)
                      for i, p in enumerate(probs)}

            predicted = max(scores, key=scores.get)
            confidence = scores[predicted]

        except Exception as exc:              # noqa: BLE001
            print(f"[classifier] inference failed ({type(exc).__name__}) — fallback")
            route = self._fallback(text)
            route.source = "error"
            route.note = f"inference error: {type(exc).__name__}"
            return route

        spec = INTENTS.get(predicted)
        if spec is None:
            return _route_from(
                SAFE_INTENT, predicted=predicted, confidence=confidence,
                degraded=True, source="model", scores=scores,
                note=f"no policy for label {predicted!r}",
            )

        if confidence < spec.min_conf and spec.degrade_to:
            return _route_from(
                spec.degrade_to, predicted=predicted, confidence=confidence,
                degraded=True, source="model", scores=scores,
                note=(f"{confidence:.2f} below {spec.min_conf:.2f} floor for "
                      f"{predicted}; degraded to {spec.degrade_to}"),
            )

        return _route_from(
            predicted, predicted=predicted, confidence=confidence,
            degraded=False, source="model", scores=scores,
        )

    def explain(self, message: str) -> str:
        """Human-readable trace, for debugging and for the report."""
        r = self.classify(message)
        lines = [
            f"message   : {message}",
            f"source    : {r.source}",
            f"predicted : {r.predicted}"
            + (f" ({r.confidence:.3f})" if r.confidence is not None else ""),
            f"routed to : {r.intent}" + ("  [DEGRADED]" if r.degraded else ""),
            f"plan      : retrieve={r.retrieve} top_k={r.top_k} "
            f"profile={r.profile} llm={r.llm}",
        ]
        if r.note:
            lines.append(f"note      : {r.note}")
        if r.scores:
            ranked = sorted(r.scores.items(), key=lambda kv: -kv[1])
            lines.append("scores    : " +
                         "  ".join(f"{k}={v:.3f}" for k, v in ranked))
        return "\n".join(lines)


classifier_service = ClassifierService()


if __name__ == "__main__":
    # python -m app.services.classifier_service
    for probe in [
        "bhat e koto calorie?",
        "ami kototuku vat khabo akdin a?",
        "can you give me a diet plan",
        "what about rice consumption in a day",
        "rui naki ilish, kon ta beshi calorie?",
        "hello",
    ]:
        print(classifier_service.explain(probe), end="\n\n")