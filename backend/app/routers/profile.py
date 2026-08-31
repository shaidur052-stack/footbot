"""Profile endpoints. One profile per authenticated user."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.profile import ProfileIn, ProfileOut
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.put("", response_model=ProfileOut)
def save_profile(
    payload: ProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create or replace this user's profile."""
    return profile_service.save_for_user(db, user.id, payload.model_dump())


@router.get("", response_model=ProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = profile_service.get_for_user(db, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile set yet")
    return profile