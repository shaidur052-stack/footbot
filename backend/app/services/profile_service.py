"""Deterministic personalization math, plus profile persistence.

The formulas are published clinical standards, not LLM output. That
distinction is the answer to "how do you know your advice is safe?"
"""

from sqlalchemy.orm import Session

from app.models.user import Profile

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "moderate": 1.55,
    "active": 1.725,
}

GOAL_ADJUSTMENT = {
    "lose": -400,
    "maintain": 0,
    "gain": 400,
}

# Widely used clinical minimums. A flat deficit can drive a small user to
# an unsafely low intake, so the target is clamped rather than allowed to
# fall wherever the arithmetic lands.
CALORIE_FLOOR = {"male": 1500, "female": 1200}


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor equation — the current clinical standard."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "male" else base - 161


# Plausible bounds for a daily target. The floor is clinical; the ceiling is
# a sanity check — nothing a normal adult profile produces comes near it, so
# exceeding it means the inputs are wrong rather than the person unusual.
CALORIE_FLOOR = {"male": 1500, "female": 1200}
CALORIE_CEILING = 5000


def calculate_daily_calories(profile: dict) -> int:
    bmr = calculate_bmr(
        profile["weight_kg"], profile["height_cm"], profile["age"], profile["gender"]
    )
    tdee = bmr * ACTIVITY_FACTORS.get(profile.get("activity", "sedentary"), 1.2)
    adjusted = tdee + GOAL_ADJUSTMENT.get(profile.get("goal", "maintain"), 0)

    floor = CALORIE_FLOOR.get(profile.get("gender"), 1200)
    target = max(round(adjusted), floor)

    if target > CALORIE_CEILING:
        # Reporting an implausible figure to a user is worse than refusing to
        # compute one. This should be unreachable once ProfileIn validates,
        # but a health figure is not something to leave to one layer.
        raise ValueError(
            f"computed target {target} kcal is implausible — check the "
            f"height and weight entered"
        )

    return target


def enrich(profile: dict) -> dict:
    """Raw inputs -> inputs plus computed values."""
    return {
        **profile,
        "bmi": calculate_bmi(profile["weight_kg"], profile["height_cm"]),
        "daily_calories": calculate_daily_calories(profile),
        "consumed_today": profile.get("consumed_today", 0),
    }


# ---------- persistence ----------

def get_for_user(db: Session, user_id: int) -> dict | None:
    """Fetch a profile and compute its derived values.

    Rejecting implausible input belongs at SAVE time. At read time a stored
    bad profile must not break the user's chat — one row written before
    validation existed would otherwise make every request fail. So the profile
    is returned without a target, and the assistant falls back to answering
    without personalisation.
    """
    row = db.query(Profile).filter(Profile.user_id == user_id).first()
    if row is None:
        return None

    raw = {
        "age": row.age,
        "gender": row.gender,
        "weight_kg": row.weight_kg,
        "height_cm": row.height_cm,
        "activity": row.activity,
        "goal": row.goal,
        "condition": row.condition,
    }

    try:
        return enrich(raw)
    except ValueError as exc:
        print(f"[profile] user {user_id}: {exc} — serving without a target")
        return {**raw, "bmi": None, "daily_calories": None, "consumed_today": 0}


def save_for_user(db: Session, user_id: int, data: dict) -> dict:
    """Create or update. One profile per user, so this is an upsert."""
    row = db.query(Profile).filter(Profile.user_id == user_id).first()

    if row is None:
        row = Profile(user_id=user_id)
        db.add(row)

    for field in ("age", "gender", "weight_kg", "height_cm",
                  "activity", "goal", "condition"):
        if field in data:
            setattr(row, field, data[field])

    db.commit()
    db.refresh(row)
    return get_for_user(db, user_id)