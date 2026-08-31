"""Chat endpoints. HTTP only — all logic lives in services."""

import json
import re
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_optional_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.retrieval_service import retrieval_service
from app.services.classifier_service import classifier_service
from app.services.guidance_service import guidance_service
from app.services import prompt_builder, llm_service, profile_service, chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

# Per-stage timing and the retrieved rows, printed to the console. Cheap, and
# a hedged answer is ambiguous without it: you cannot tell whether retrieval
# missed the food or the prompt refused despite having it.
TIMING = True

# Minimum semantic similarity for a row to be shown as a citation.
#
# Applied ONLY to rows with no keyword match. A keyword hit is decisive
# regardless of its dense score — "vat" matched rice exactly while rice scored
# just 0.31 semantically, because the query was mostly Banglish function
# words. Gating citations on dense alone would have hidden the correct source.
CITATION_MIN_DENSE = 0.45

# A follow-up like "ok but koto calorie" or "and the protein?" carries the
# question but not the subject. Searching those words finds nothing, so the
# model sees an empty context and reports having no data — for a food it
# answered about one turn earlier.
_FOLLOWUP = re.compile(
    r"^\s*(ok|okay|and|but|also|then|ar|ebong|আর|আচ্ছা|thik ache)\b"
    r"|^\s*(koto|kototuku|how much|how many|what about|kemon|কত|কতটুকু)\b"
    r"|^\s*(in|give\s+.*in)\s+(bangla|bangali|bengali|english|banglish)\b",
    re.IGNORECASE,
)


def _search_text(message: str, history: list[dict]) -> str:
    """What to actually send to retrieval.

    Prepending the previous user turn restores the food name a follow-up
    omits, so retrieval can find the row the conversation is already about.
    """
    if not history or not _FOLLOWUP.match(message.strip()):
        return message

    prior = [t["content"] for t in history if t.get("role") == "user"]
    return f"{prior[-1]} {message}" if prior else message


def _to_sources(foods, guidance=None, answer=None):
    """Retrieved context -> the citation shape the frontend expects.

    Food rows and guidance rules are both cited, but tagged distinctly: one is
    a measured value from the national food table, the other is published
    advice. A user should be able to see which is which.
    """
    out = []

    for f in foods:
        # filter 1: weak match. A keyword hit is decisive on its own; only
        # rows retrieved purely on semantics must clear the dense floor.
        if f.get("_bm25", 0) <= 0 and f.get("_dense", 0) < CITATION_MIN_DENSE:
            continue

        # filter 2: retrieved but unused by the answer
        if answer:
            lowered = answer.lower()
            aliases = [
                f.get("name_en", ""),
                f.get("name_bn", ""),
                *f.get("name_banglish", []),
            ]
            # Aliases under 3 chars ("am", "ol") match inside unrelated words
            # now that there are ~13 per food, which reintroduces phantom
            # citations. Require a longer match.
            named = any(a and len(a) > 2 and a.lower() in lowered for a in aliases)

            per = f.get("per_portion") or {}
            calories = per.get("calories")
            quoted = calories is not None and str(calories) in lowered

            if not (named or quoted):
                continue

        grams = f.get("portion_grams")
        portion = f.get("portion_local", "")
        if grams:
            portion = f"{portion} ({grams}g)"

        out.append({
            "food": f["name_en"],
            "portion": portion,
            "ref": f.get("citation", "unknown"),     # FCT table + food code
            "kind": "food",
        })

    for r in guidance or []:
        out.append({
            "food": r.get("topic", "guidance"),
            "portion": r.get("condition", ""),
            "ref": r.get("citation", "unknown"),
            "kind": "guidance",
        })

    return out


def _prepare(req: ChatRequest, db: Session, user: User | None):
    """Classify, then gather the context this question needs.

    The profile is loaded for EVERY intent when a user is signed in, not only
    when the classifier predicts an advice question. It is one indexed read
    (measured under 1 ms), and gating it behind classification meant a single
    misroute silently disabled personalisation: "ami kototuku vat khabo" was
    classified food_fact, so the model never saw the user's calorie target and
    could not answer a question that was pure arithmetic on data it held.

    Cheap context should not depend on a model being right.
    """
    t0 = time.perf_counter()

    history = chat_service.recent_turns(
        db, user.id if user else None, req.conversation_id
    )
    t1 = time.perf_counter()

    route = classifier_service.classify(req.message)
    t2 = time.perf_counter()

    profile = profile_service.get_for_user(db, user.id) if user else None
    condition = profile["condition"] if profile else "none"
    t3 = time.perf_counter()

    foods = []
    if route["retrieve"]:
        foods = retrieval_service.search(
            _search_text(req.message, history),
            top_k=route["top_k"],
            condition=condition,
        )
    t4 = time.perf_counter()

    # Guidance runs on every intent. It is keyword scoring over 26 rules —
    # microseconds — and a condition question can arrive under any label.
    guidance = guidance_service.search(
        req.message,
        condition=condition,
        food_ids=[f["id"] for f in foods],
    )
    t5 = time.perf_counter()

    if TIMING:
        print(f"[timing] history={1000*(t1-t0):.0f}ms  "
              f"classify={1000*(t2-t1):.0f}ms  "
              f"profile={1000*(t3-t2):.0f}ms  "
              f"retrieval={1000*(t4-t3):.0f}ms  "
              f"guidance={1000*(t5-t4):.0f}ms  "
              f"intent={route['intent']}  profile_loaded={profile is not None}")

        # Which rows the model actually received. Without this, a hedged
        # answer is ambiguous: we cannot tell whether retrieval missed the
        # food or the prompt refused despite having it.
        if foods:
            print("[retrieved] " + " | ".join(
                f"{f['name_en'][:32]} "
                f"{(f.get('per_portion') or {}).get('calories')}kcal "
                f"({f.get('_mode')} bm25={f.get('_bm25')} dense={f.get('_dense')})"
                for f in foods))
        elif route["retrieve"]:
            print("[retrieved] (nothing cleared the relevance gate)")

        if guidance:
            print("[guidance]  " + " | ".join(
                f"{g['id']} ({g['condition']}, {g['_score']})" for g in guidance))

    return route, foods, profile, history, guidance


def _build_prompt(req: ChatRequest, route, foods, profile, history, guidance):
    """Assemble the prompt.

    retrieval_ran distinguishes "we searched and found nothing" — which needs
    an explanatory refusal — from "this question needed no lookup", where the
    database must not be mentioned at all.

    language comes from the UI toggle and overrides the language the question
    was written in.
    """
    return prompt_builder.build(
        req.message,
        foods,
        profile,
        intent=route.get("intent"),
        retrieval_ran=route.get("retrieve", False),
        history=history,
        language=req.language,
        guidance=guidance,
    )


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Non-streaming. Simpler to debug; the frontend uses /stream.

    Auth is OPTIONAL — anonymous visitors get grounded answers, just without
    personalisation or saved history.
    """
    route, foods, user_profile, history, guidance = _prepare(req, db, user)

    built = _build_prompt(req, route, foods, user_profile, history, guidance)
    if built.warnings:
        print(f"[prompt] {route['intent']}: {built.warnings}")

    tg = time.perf_counter()
    answer = llm_service.generate(built.text)
    gen = time.perf_counter() - tg

    if TIMING:
        print(f"[timing] generation={gen:.1f}s  "
              f"prompt_chars={len(built.text)}  answer_chars={len(answer)}  "
              f"foods={built.foods_included}  rules={built.guidance_included}  "
              f"turns={built.turns_included}")

    sources = _to_sources(foods, guidance, answer)      # answer-aware filtering

    # Saved only for signed-in users. Written AFTER generation, so a failed
    # LLM call leaves no orphaned half-exchange in the database.
    conv_id, msg_id = chat_service.save_exchange(
        db, user.id if user else None, req.conversation_id,
        req.message, answer, sources,
    )

    return {
        "answer": answer,
        "language": req.language,
        "sources": sources,
        "message_id": msg_id or int(time.time() * 1000),
        "conversation_id": conv_id,
    }


@router.post("/stream")
def chat_stream(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Streams the answer, then a metadata block after a delimiter."""
    route, foods, user_profile, history, guidance = _prepare(req, db, user)
    user_id = user.id if user else None

    built = _build_prompt(req, route, foods, user_profile, history, guidance)
    if built.warnings:
        print(f"[prompt] {route['intent']}: {built.warnings}")

    def generate():
        collected = []
        t_start = time.perf_counter()
        t_first = None

        for chunk in llm_service.generate_stream(built.text):
            if t_first is None:
                t_first = time.perf_counter() - t_start
                # Time to first token decides whether the UI feels fast.
                # Total time matters much less.
                if TIMING:
                    print(f"[timing] first_token={t_first:.1f}s")
            collected.append(chunk)
            yield chunk

        answer = "".join(collected)

        if TIMING:
            print(f"[timing] stream_total={time.perf_counter()-t_start:.1f}s  "
                  f"prompt_chars={len(built.text)}  answer_chars={len(answer)}  "
                  f"foods={built.foods_included}  rules={built.guidance_included}  "
                  f"turns={built.turns_included}")

        # The full answer exists by now, so citations can be filtered against
        # it exactly as in /chat — no asymmetry between the two endpoints.
        sources = _to_sources(foods, guidance, answer)

        # Persist once the stream has finished, so a broken stream doesn't
        # store a truncated answer as if it were complete.
        conv_id, msg_id = chat_service.save_exchange(
            db, user_id, req.conversation_id, req.message, answer, sources,
        )

        yield "\n---META---\n" + json.dumps({
            "sources": sources,
            "message_id": msg_id or int(time.time() * 1000),
            "conversation_id": conv_id,
        })

    return StreamingResponse(generate(), media_type="text/plain")