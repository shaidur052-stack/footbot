from pydantic import BaseModel, Field, field_validator


class ProfileIn(BaseModel):
    """Raw inputs. Bounds are deliberately wide — they exist to catch typos
    and unit errors, not to police unusual bodies.

    A profile of age 2324 and weight 7064 kg reached the database and produced
    a 72,105 kcal daily target, which the assistant then reported to the user.
    Browser min/max attributes are advisory and do not apply to direct API
    calls, so validation has to live here.
    """
    age: int = Field(ge=2, le=120)
    gender: str
    weight_kg: float = Field(gt=2, le=400)
    height_cm: float = Field(gt=50, le=260)
    activity: str = "sedentary"
    goal: str = "maintain"
    condition: str = "none"

    @field_validator("gender")
    @classmethod
    def _gender(cls, v):
        if v not in ("male", "female"):
            raise ValueError("gender must be male or female")
        return v

    @field_validator("activity")
    @classmethod
    def _activity(cls, v):
        if v not in ("sedentary", "moderate", "active"):
            raise ValueError("unknown activity level")
        return v

    @field_validator("goal")
    @classmethod
    def _goal(cls, v):
        if v not in ("lose", "maintain", "gain"):
            raise ValueError("unknown goal")
        return v

    @field_validator("condition")
    @classmethod
    def _condition(cls, v):
        if v not in ("none", "diabetes", "hypertension", "kidney"):
            raise ValueError("unknown condition")
        return v


class ProfileOut(ProfileIn):
    bmi: float
    daily_calories: int
    consumed_today: int = 0