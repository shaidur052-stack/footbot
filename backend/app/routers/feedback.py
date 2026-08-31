"""Thumbs up/down on an answer. Becomes an evaluation metric later."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import Conversation, Feedback, Message, User

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    message_id: int
    is_positive: bool


@router.post("", status_code=201)
def submit(payload: FeedbackIn, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    # Confirm the message belongs to this user before recording anything.
    msg = (db.query(Message)
             .join(Conversation)
             .filter(Message.id == payload.message_id,
                     Conversation.user_id == user.id)
             .first())
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")

    existing = db.query(Feedback).filter(
        Feedback.message_id == payload.message_id).first()

    if existing:
        existing.is_positive = payload.is_positive      # allow changing a vote
    else:
        db.add(Feedback(message_id=payload.message_id,
                        is_positive=payload.is_positive))

    db.commit()
    return {"ok": True}